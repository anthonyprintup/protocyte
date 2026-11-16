"""Transient native read-set commit; never standalone mutation authority.

Positive objects use root-anchored short opens and exact ID/version witnesses.
Only volume roots retain handles; foreign build directories are not pinned.
Negative namespace observations are refreshed at every comparison and commit.
The coordinator decides authority only after seal and complete handle release;
no observations may cross into reconciliation or publication mutations.
"""

from __future__ import annotations

import ctypes
import contextlib
import concurrent.futures
import json
import os
import struct
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping


class CommitUnavailable(RuntimeError):
    pass


class CapabilityUnavailable(CommitUnavailable):
    pass


class ObservationChanged(RuntimeError):
    pass


class ProbeCleanupFailed(RuntimeError):
    """Native work or handle cleanup failed; fallback must not authorize mutation."""


class ProbeSession:
    """Bounded independent comparisons; no query can outlive close, even on error.

    The admission gate also covers a task queued by a submit call that raises
    before returning its Future. Shutdown closes admission first, then joins
    the executor and independently drains all admitted native work.
    """

    BATCH_SIZE = 32

    def __init__(self, compare, *, workers: int = 4) -> None:
        if type(workers) is not int or not 1 <= workers <= 4:
            raise CapabilityUnavailable("unsupported probe worker bound")
        self.workers = workers
        self._owner = threading.get_ident()
        self._compare = compare
        self._condition = threading.Condition()
        self._accepting = True
        self._native_retired = False
        self._finished = False
        self._close_error: BaseException | None = None
        self._active = self._peak = 0
        self._started = self._completed = self._comparisons = 0
        self._submitted = self._peak_pending = 0
        self._threads: set[int] = set()
        self._futures: set[Any] = set()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="protocyte-probes"
        )

    def _run(self, batch):
        admitted = False
        completed = 0
        result = []
        try:
            with self._condition:
                if not self._accepting:
                    raise ObservationChanged("probe work admitted after retirement")
                self._active += 1
                admitted = True
                # Bookkeeping can allocate and raise. It belongs inside the
                # same retirement finally as the native comparison itself.
                self._peak = max(self._peak, self._active)
                self._started += 1
                self._threads.add(threading.get_ident())
            for reservation, prepared in batch:
                if self._compare(prepared):
                    result.append(reservation)
                completed += 1
            return result
        finally:
            if admitted:
                with self._condition:
                    # Retire first: even a later accounting failure cannot
                    # leave close() waiting for a batch that already exited.
                    self._active -= 1
                    self._condition.notify_all()
                    self._comparisons += completed
                    self._completed += 1

    def compare(self, prepared):
        self._require_owner()
        with self._condition:
            if not self._accepting:
                raise ObservationChanged("probe session used after retirement")
        rows = iter(prepared)
        pending = deque()
        result = []

        def submit() -> bool:
            batch = []
            for _ in range(self.BATCH_SIZE):
                try:
                    batch.append(next(rows))
                except StopIteration:
                    break
            if not batch:
                return False
            future = self._executor.submit(self._run, tuple(batch))
            self._futures.add(future)
            pending.append(future)
            self._submitted += 1
            self._peak_pending = max(self._peak_pending, len(pending))
            return True

        try:
            for _ in range(self.workers * 2):
                if not submit():
                    break
            while pending:
                future = pending.popleft()
                result.extend(future.result())
                self._futures.remove(future)
                submit()
            return result
        except BaseException:
            # This finishes every admitted query before the exception can
            # reach the read set's handle-release/fallback boundary.
            self.close()
            raise

    def close(self) -> None:
        self._require_owner()
        if not self._finished:
            # Close admission and drain *before* touching the executor. Catch
            # interruption at lock acquisition as well as inside wait(). This
            # monotonic fence is independently checked before root release.
            while True:
                try:
                    with self._condition:
                        self._accepting = False
                        if not self._active:
                            self._native_retired = True
                            break
                        # A worker may fail while notifying its retirement.
                        # Recheck the fence even if that notification is lost.
                        self._condition.wait(timeout=0.1)
                except BaseException as error:
                    if self._close_error is None:
                        self._close_error = error
            for future in self._futures:
                try:
                    future.cancel()
                except BaseException as error:
                    if self._close_error is None:
                        self._close_error = error
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
            except BaseException as error:
                if self._close_error is None:
                    self._close_error = error
            self._futures.clear()
            self._compare = None
            self._finished = True
        if self._close_error is not None:
            if isinstance(self._close_error, Exception):
                raise ProbeCleanupFailed(
                    "probe worker retirement failed"
                ) from self._close_error
            raise self._close_error

    def _require_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise ObservationChanged("probe session control used by a worker")

    @property
    def native_retired(self) -> bool:
        return self._native_retired

    def metrics(self) -> dict[str, Any]:
        with self._condition:
            return {
                "commit_probe_state": "failed"
                if self._close_error is not None
                else "closed"
                if self._finished
                else "active",
                "commit_probe_workers": self.workers,
                "commit_probe_native_retired": self._native_retired,
                "commit_probe_threads": len(self._threads),
                "commit_probe_active": self._active,
                "commit_probe_peak_active": self._peak,
                "commit_probe_pending": len(self._futures),
                "commit_probe_peak_pending": self._peak_pending,
                "commit_probe_batches_submitted": self._submitted,
                "commit_probe_batches_started": self._started,
                "commit_probe_batches_finished": self._completed,
                "commit_probe_comparisons": self._comparisons,
            }


CLOSE_REASON = 0x80000000


@dataclass(frozen=True)
class JournalRecord:
    usn: int
    file_id: int
    reason: int


def parse_journal_page(data: bytes) -> tuple[int, tuple[JournalRecord, ...]]:
    """Decode headers only; never retain names or unrelated filesystem paths."""
    if len(data) < 8:
        raise CommitUnavailable("short journal cursor")
    cursor = struct.unpack_from("<q", data)[0]
    if cursor < 0:
        raise CommitUnavailable("negative journal cursor")
    records = []
    offset = 8
    previous = -1
    while offset < len(data):
        if len(data) - offset < 8:
            raise CommitUnavailable("truncated journal header")
        length, major, minor = struct.unpack_from("<IHH", data, offset)
        if major not in (2, 3) or minor != 0:
            raise CommitUnavailable("unsupported journal record version")
        minimum = 60 if major == 2 else 76
        if length < minimum or length % 8 or offset + length > len(data):
            raise CommitUnavailable("invalid journal record length")
        width = 8 if major == 2 else 16
        file_id = int.from_bytes(data[offset + 8 : offset + 8 + width], "little")
        usn_offset = offset + (24 if major == 2 else 40)
        usn = struct.unpack_from("<q", data, usn_offset)[0]
        reason = struct.unpack_from("<I", data, usn_offset + 16)[0]
        name_length, name_offset = struct.unpack_from("<HH", data, offset + minimum - 4)
        if (
            usn < 0
            or usn <= previous
            or usn >= cursor
            or name_length % 2
            or (
                name_length
                and (
                    name_offset < minimum
                    or name_offset % 2
                    or name_offset + name_length > length
                )
            )
        ):
            raise CommitUnavailable("invalid journal record fields")
        records.append(JournalRecord(usn, file_id, reason))
        previous = usn
        offset += length
    return cursor, tuple(records)


def verify_witnesses(
    expected: Mapping[int, int], records: Iterable[JournalRecord]
) -> None:
    """Require positive evidence for every requested USN; absence never succeeds."""
    found: set[int] = set()
    for record in records:
        if record.usn not in expected:
            continue
        if record.usn in found or record.file_id != expected[record.usn]:
            raise CommitUnavailable("duplicate or misbound close witness")
        if record.reason != CLOSE_REASON:
            raise ObservationChanged("close witness contains accumulated changes")
        found.add(record.usn)
    if found != set(expected):
        raise CommitUnavailable("incomplete close witnesses")


@dataclass
class _Guard:
    handle: Any
    volume: int
    file_id: int
    start_usn: int
    is_directory: bool
    request: Any = None


@dataclass(frozen=True)
class _View:
    path: Path
    facts: Any
    guard: _Guard
    missing: tuple[str, ...] = ()
    probe: Any = None
    relative: str = ""


@dataclass
class _Volume:
    handle: Any
    epoch: int
    first: int


class _FrozenComparisons:
    """Workers see prepared immutable views, never the mutable observation maps."""

    def __init__(self, scope, workers: int) -> None:
        self._scope = scope
        self._views = MappingProxyType(dict(scope._views))
        self._closed = False
        self.probe_session = ProbeSession(self._compare, workers=workers)

    def _get(self, path: Path) -> _View:
        if self._closed:
            raise ObservationChanged("frozen comparisons used after retirement")
        self._scope._require_owner()
        if self._scope._state != "comparing":
            raise ObservationChanged("comparisons used outside their phase")
        view = self._views.get(str(path))
        if view is None:
            raise CommitUnavailable("comparison path was not observed before freezing")
        if not view.missing and not view.guard.is_directory:
            raise ObservationChanged("non-directory comparison endpoint")
        return view

    def is_stable(self, path: Path) -> bool:
        return not self._get(path).missing

    def facts(self, path: Path):
        return self._get(path).facts

    def prepare_overlap(self, first: Path, second: Path):
        return self._get(first), self._get(second)

    def _compare(self, prepared) -> bool:
        if self._closed or self._scope._state != "comparing":
            raise ObservationChanged("prepared comparison used after retirement")
        return self._scope._overlaps_views(*prepared)

    def close(self) -> None:
        try:
            self.probe_session.close()
        finally:
            if not self.probe_session.native_retired:
                # Preserve views and root bindings if an interruption happens
                # before close() can enter its draining loop. Scope cleanup can
                # retry, but must never release handles on an unproved fence.
                raise ProbeCleanupFailed("native probe retirement is unproved")
            self._closed = True
            self._views = MappingProxyType({})
            self._scope = None


class WindowsObservationCommit:
    """One bounded read set; instances and facts are never shared across phases."""

    MAX_OBJECTS = 32768
    MAX_JOURNAL_BYTES = 64 * 1024 * 1024
    MAX_RECORD_BYTES = 16 * 1024 * 1024

    def __init__(self, native: Any, model: Any) -> None:
        # Keep old coordinators safe too: they predate the caller-side version
        # checks and can import an in-progress or mixed helper installation.
        contracts = (
            (globals().get("COMMIT_CONTRACT_VERSION"), 2),
            (getattr(native, "PATH_CONTRACT_VERSION", None), 1),
            (getattr(model, "OWNERSHIP_CONTRACT_VERSION", None), 1),
        )
        if any(type(value) is not int or value != expected for value, expected in contracts):
            raise CapabilityUnavailable("incomplete observation helper installation")
        if os.name != "nt":
            raise CapabilityUnavailable("commit observations require Windows")
        self.native, self.model = native, model
        self.reader = native.FreshPathObserver()
        self.w = self.reader._w
        self._state = "active"
        self._owner = threading.get_ident()
        self._negative_lock = threading.Lock()
        self._comparison_reader: _FrozenComparisons | None = None
        self._objects: dict[tuple[int, int], _Guard] = {}
        self._volumes: dict[int, _Volume] = {}
        self._roots: dict[str, _View] = {}
        self._views: dict[str, _View] = {}
        self._bindings: list[tuple[_Guard, str, tuple[int, int] | None, Any]] = []
        self._inventories: list[
            tuple[_Guard, tuple[str, ...], frozenset[str] | None]
        ] = []
        self._cleanup_error: BaseException | None = None
        self._counts = {
            name: 0
            for name in (
                "commit_open_calls",
                "commit_info_calls",
                "commit_negative_probes",
                "commit_close_posts",
                "commit_version_reads",
                "commit_epoch_queries",
                "commit_journal_reads",
                "commit_journal_bytes",
                "commit_witnesses",
                "commit_records_read",
                "commit_binding_checks",
                "commit_record_read_calls",
                "commit_record_seek_calls",
                "commit_directory_enumerations",
                "commit_full_inventory_scans",
                "commit_worker_context_checks",
            )
        }

        class FileId(ctypes.Structure):
            _fields_ = [("Volume", ctypes.c_ulonglong), ("Id", ctypes.c_ubyte * 16)]

        class Basic(ctypes.Structure):
            _fields_ = [("Times", ctypes.c_longlong * 4), ("Attributes", self.w.ULONG)]

        self._id_type, self._basic_type = FileId, Basic
        self._control = self.reader._kernel.DeviceIoControl
        self._control.argtypes = (
            self.w.HANDLE,
            self.w.DWORD,
            self.w.LPVOID,
            self.w.DWORD,
            self.w.LPVOID,
            self.w.DWORD,
            ctypes.POINTER(self.w.DWORD),
            self.w.LPVOID,
        )
        self._control.restype = self.w.BOOL
        self._query = self.reader._nt.NtQueryAttributesFile
        self._query.argtypes = (
            ctypes.POINTER(self.reader._attributes),
            ctypes.POINTER(Basic),
        )
        self._query.restype = self.w.LONG
        self._read = self.reader._kernel.ReadFile
        self._read.argtypes = (
            self.w.HANDLE,
            self.w.LPVOID,
            self.w.DWORD,
            ctypes.POINTER(self.w.DWORD),
            self.w.LPVOID,
        )
        self._read.restype = self.w.BOOL
        self._seek = self.reader._kernel.SetFilePointerEx
        self._seek.argtypes = (
            self.w.HANDLE,
            ctypes.c_longlong,
            ctypes.POINTER(ctypes.c_longlong),
            self.w.DWORD,
        )
        self._seek.restype = self.w.BOOL
        self._fs_info = self.reader._kernel.GetVolumeInformationByHandleW
        self._fs_info.argtypes = (
            self.w.HANDLE,
            self.w.LPWSTR,
            self.w.DWORD,
            ctypes.POINTER(self.w.DWORD),
            ctypes.POINTER(self.w.DWORD),
            ctypes.POINTER(self.w.DWORD),
            self.w.LPWSTR,
            self.w.DWORD,
        )
        self._fs_info.restype = self.w.BOOL
        self._check_worker_context()

    def _check_worker_context(self) -> None:
        self._counts["commit_worker_context_checks"] += 1
        if ctypes.sizeof(ctypes.c_void_p) != 8:
            raise CapabilityUnavailable(
                "parallel probes require a native 64-bit process"
            )
        kernel = self.reader._kernel
        current_process = kernel.GetCurrentProcess
        current_process.argtypes = ()
        current_process.restype = self.w.HANDLE
        machine = getattr(kernel, "IsWow64Process2", None)
        if machine is None:
            raise CapabilityUnavailable("native process context cannot be established")
        machine.argtypes = (
            self.w.HANDLE,
            ctypes.POINTER(self.w.WORD),
            ctypes.POINTER(self.w.WORD),
        )
        machine.restype = self.w.BOOL
        process_machine, native_machine = self.w.WORD(), self.w.WORD()
        if (
            not machine(
                current_process(),
                ctypes.byref(process_machine),
                ctypes.byref(native_machine),
            )
            or process_machine.value
            or native_machine.value not in (0x8664, 0xAA64)
        ):
            raise CapabilityUnavailable(
                "emulated filesystem context needs reference validation"
            )
        current_thread = kernel.GetCurrentThread
        current_thread.argtypes = ()
        current_thread.restype = self.w.HANDLE
        open_token = ctypes.WinDLL("advapi32", use_last_error=True).OpenThreadToken
        open_token.argtypes = (
            self.w.HANDLE,
            self.w.DWORD,
            self.w.BOOL,
            ctypes.POINTER(self.w.HANDLE),
        )
        open_token.restype = self.w.BOOL
        token = self.w.HANDLE()
        if open_token(current_thread(), 0x8, True, ctypes.byref(token)):
            if not self.reader._close(token):
                raise ProbeCleanupFailed("thread token handle could not be retired")
            raise CapabilityUnavailable(
                "impersonating caller needs reference validation"
            )
        if ctypes.get_last_error() != 1008:  # ERROR_NO_TOKEN is the required result.
            raise CapabilityUnavailable("ordinary thread context cannot be established")

    def _active(self) -> None:
        self._require_owner()
        if self._state != "active":
            raise ObservationChanged("read set used outside its observation phase")

    def _require_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise ObservationChanged("mutable observations used by a worker")

    @contextlib.contextmanager
    def comparisons(self, *, workers: int = 4):
        self._active()
        if self._comparison_reader is not None:
            raise ObservationChanged("read set comparisons already retired")
        self._check_worker_context()
        self._state = "comparing"
        try:
            reader = _FrozenComparisons(self, workers)
        except BaseException:
            self._state = "active"
            raise
        self._comparison_reader = reader
        try:
            yield reader
        finally:
            try:
                reader.close()
            finally:
                if reader.probe_session.native_retired:
                    self._state = "observed"

    def _io(
        self, handle: Any, code: int, request: bytes | None, capacity: int
    ) -> bytes:
        incoming = ctypes.create_string_buffer(request) if request is not None else None
        output = ctypes.create_string_buffer(capacity)
        size = self.w.DWORD()
        if not self._control(
            handle,
            code,
            incoming,
            len(request) if request else 0,
            output,
            capacity,
            ctypes.byref(size),
            None,
        ):
            raise CapabilityUnavailable(
                f"journal operation unavailable ({ctypes.get_last_error()})"
            )
        if size.value > capacity:
            raise CommitUnavailable("oversized journal reply")
        return output.raw[: size.value]

    def _epoch(self, handle: Any) -> tuple[int, int, int]:
        self._counts["commit_epoch_queries"] += 1
        data = self._io(handle, 0x900F4, None, 128)
        if len(data) < 56:
            raise CommitUnavailable("short journal information")
        epoch, first, next_usn, lowest = struct.unpack_from("<Qqqq", data)
        if (
            not epoch
            or min(first, next_usn, lowest) < 0
            or first > next_usn
            or lowest > next_usn
        ):
            raise CommitUnavailable("invalid journal information")
        return epoch, max(first, lowest), next_usn

    def _post_close(self, handle: Any) -> int:
        self._counts["commit_close_posts"] += 1
        data = self._io(handle, 0x900EF, None, 8)
        if len(data) != 8:
            raise CommitUnavailable("short close marker")
        usn = struct.unpack("<q", data)[0]
        if usn <= 0:
            raise CommitUnavailable("invalid close marker")
        return usn

    def _version(self, handle: Any) -> int:
        self._counts["commit_version_reads"] += 1
        data = self._io(handle, 0x900EB, struct.pack("<HH", 2, 3), 1024)
        if len(data) < 8:
            raise CommitUnavailable("short file version")
        length, major, minor = struct.unpack_from("<IHH", data)
        minimum = 60 if major == 2 else 76 if major == 3 else 0
        if not minimum or minor or length < minimum or length > len(data):
            raise CommitUnavailable("unsupported file version")
        return struct.unpack_from("<q", data, 24 if major == 2 else 40)[0]

    def _identity(self, handle: Any) -> tuple[int, int]:
        self._counts["commit_info_calls"] += 1
        value = self._id_type()
        if not self.reader._info(handle, 18, ctypes.byref(value), ctypes.sizeof(value)):
            raise CapabilityUnavailable("128-bit object identity unavailable")
        key = value.Volume, int.from_bytes(bytes(value.Id), "little")
        if not key[0] or not key[1]:
            raise CommitUnavailable("empty object identity")
        return key

    def _release(self, handle: Any) -> None:
        try:
            closed = self.reader._close(handle)
        except BaseException as error:
            self._cleanup_error = error
            if isinstance(error, Exception):
                raise ProbeCleanupFailed("native handle release failed") from error
            raise
        if not closed:
            error = ProbeCleanupFailed("native handle release failed")
            self._cleanup_error = error
            raise error
        self.reader.handles_closed += 1

    def _adopt(
        self, handle: Any, *, request: Any = None, retain_root: bool = False
    ) -> tuple[_Guard, Path]:
        retained = False
        try:
            key = self._identity(handle)
            known = self._objects.get(key)
            if known is None:
                if len(self._objects) >= self.MAX_OBJECTS:
                    raise CommitUnavailable("read set object budget exceeded")
                if key[0] not in self._volumes:
                    if not retain_root:
                        raise CommitUnavailable(
                            "relative lookup crossed a volume boundary"
                        )
                    filesystem = ctypes.create_unicode_buffer(32)
                    self._counts["commit_info_calls"] += 1
                    if (
                        not self._fs_info(
                            handle,
                            None,
                            0,
                            None,
                            None,
                            None,
                            filesystem,
                            len(filesystem),
                        )
                        or filesystem.value != "NTFS"
                    ):
                        raise CapabilityUnavailable(
                            "only local NTFS supports this prototype"
                        )
                    epoch, first, _ = self._epoch(handle)
                    self._volumes[key[0]] = _Volume(handle, epoch, first)
                start = self._post_close(handle)
                # Facts are collected only after the initial close marker.
                tag = self.reader._tag()
                self._counts["commit_info_calls"] += 1
                if not self.reader._info(
                    handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)
                ):
                    raise CommitUnavailable("attribute information unavailable")
                if tag.Attributes & 0x400:
                    raise ObservationChanged("observed reparse point")
                is_directory = bool(tag.Attributes & 0x10)
                if is_directory:
                    # This is a capability gate, not a versioned fact. NTFS can
                    # change this flag without changing the file USN. Reuse is
                    # restricted to exact canonical names below, whose binding
                    # does not depend on case-insensitive alias lookup.
                    case = self.w.DWORD()
                    self._counts["commit_info_calls"] += 1
                    if (
                        not self.reader._info(
                            handle, 23, ctypes.byref(case), ctypes.sizeof(case)
                        )
                        or case.value
                    ):
                        raise CapabilityUnavailable(
                            "case-sensitive directory needs reference validation"
                        )
                known = _Guard(
                    handle if retain_root else None,
                    key[0],
                    key[1],
                    start,
                    is_directory,
                    request,
                )
                self._objects[key] = known
                retained = retain_root
            canonical = self.reader._describe(handle, leaf_may_be_file=True)
            return known, canonical
        finally:
            if not retained:
                self._release(handle)

    def _request(self, parent: _View, component: str):
        if (
            not component
            or component in (".", "..")
            or any(c in component for c in ("\\", "/", ":", "\x00"))
        ):
            raise CommitUnavailable("unsupported relative component")
        relative = parent.relative + ("\\" if parent.relative else "") + component
        length = len(relative.encode("utf-16-le"))
        if length > 65532:
            raise CommitUnavailable("relative component too long")
        storage = ctypes.create_unicode_buffer(relative)
        name = self.reader._unicode(
            length, length + 2, ctypes.cast(storage, self.w.LPWSTR)
        )
        attributes = self.reader._attributes(
            ctypes.sizeof(self.reader._attributes),
            self._volumes[parent.guard.volume].handle,
            ctypes.pointer(name),
            0x1040,
            None,
            None,
        )
        return storage, name, attributes

    def _open_child(self, request: Any):
        self._counts["commit_open_calls"] += 1
        handle, status = self.w.HANDLE(), self.reader._status()
        result = self.reader._invoke_open(
            handle,
            0x100081,
            ctypes.byref(request[2]),
            ctypes.byref(status),
            None,
            0,
            7,
            1,
            0x20,
            None,
            0,
        )
        code = result & 0xFFFFFFFF
        if code in (0xC0000034, 0xC000003A):
            return None
        if result < 0:
            raise ObservationChanged(
                f"relative open changed or unavailable ({code:08x})"
            )
        if not handle.value:
            raise CommitUnavailable("relative open returned no handle")
        self.reader.handles_opened += 1
        if code:
            self._release(handle)
            raise CommitUnavailable("unexpected relative-open status")
        return handle

    def _probe_absence(self, request: Any) -> None:
        if self._state not in ("active", "comparing", "sealing"):
            raise ObservationChanged("negative probe used after its phase")
        with self._negative_lock:
            self._counts["commit_negative_probes"] += 1
        value = self._basic_type()
        code = self._query(ctypes.byref(request[2]), ctypes.byref(value)) & 0xFFFFFFFF
        if code not in (0xC0000034, 0xC000003A):
            raise ObservationChanged("missing component changed during comparison")

    def _root(self, path: Path) -> _View:
        self.reader._native_name(path)
        root = Path(path.anchor)
        key = str(root).casefold()
        if key not in self._roots:
            self._counts["commit_open_calls"] += 1
            handle = self.reader._open_existing(root)
            if handle is None:
                raise CommitUnavailable("drive root unavailable")
            guard, canonical = self._adopt(handle, retain_root=True)
            if canonical != root:
                raise CommitUnavailable("drive aliases need reference validation")
            if any(view.guard.volume == guard.volume for view in self._roots.values()):
                # A serial is not a license to route a second drive's relative
                # lookups through the first root handle (for example, cloned
                # volumes or an additional DOS binding). Refuse ambiguity.
                raise CapabilityUnavailable(
                    "duplicate volume binding needs reference validation"
                )
            location = (guard.volume, guard.file_id, ())
            view = _View(
                canonical,
                self.model.DirectoryObservation(
                    str(canonical).replace("\\", "/").casefold().rstrip("/"),
                    location,
                    (location,),
                ),
                guard,
            )
            self._roots[key] = view
            self._views[str(root)] = view
        return self._roots[key]

    def _view(self, path: Path, *, leaf_may_be_file: bool = False) -> _View:
        self._active()
        key = str(path)
        known = self._views.get(key)
        if known is not None:
            if known.missing:
                self._probe_absence(known.probe)
            elif not known.guard.is_directory and not leaf_may_be_file:
                raise ObservationChanged("non-directory path component")
            return known
        path = Path(os.path.normpath(path))
        self.reader._native_name(path)
        key = str(path)
        parent = self._root(path)
        parts = path.parts[1:]
        input_path = Path(path.anchor)
        for number, component in enumerate(parts):
            input_path /= component
            cached = self._views.get(str(input_path))
            if cached is not None and not cached.missing:
                parent = cached
                if number < len(parts) - 1 and not parent.guard.is_directory:
                    raise ObservationChanged("non-directory ancestor")
                continue
            if not parent.guard.is_directory:
                raise ObservationChanged("non-directory ancestor")
            request = self._request(parent, component)
            handle = self._open_child(request)
            if handle is None:
                missing = tuple(parts[number:])
                suffix = tuple(part.casefold() for part in missing)
                location = (parent.guard.volume, parent.guard.file_id, suffix)
                ancestors = (
                    tuple(
                        (parent.guard.volume, parent.guard.file_id, suffix[:n])
                        for n in range(len(suffix), 0, -1)
                    )
                    + parent.facts.ancestors
                )
                canonical = parent.path.joinpath(*missing)
                facts = self.model.DirectoryObservation(
                    str(canonical).replace("\\", "/").casefold().rstrip("/"),
                    location,
                    ancestors,
                )
                view = _View(canonical, facts, parent.guard, missing, request)
                self._views[key] = view
                self._bindings.append((parent.guard, component, None, request))
                return view
            guard, canonical = self._adopt(handle, request=request)
            if str(canonical) != str(input_path):
                # A case-mode ABA need not post a USN change. In particular, a
                # differently cased alias can disappear without changing its
                # original object's ID or USN. Exact spellings still identify
                # that object in either case mode; all aliases use reference.
                raise CapabilityUnavailable(
                    "noncanonical spelling needs reference validation"
                )
            self._bindings.append(
                (parent.guard, component, (guard.volume, guard.file_id), request)
            )
            location = (guard.volume, guard.file_id, ())
            facts = self.model.DirectoryObservation(
                str(canonical).replace("\\", "/").casefold().rstrip("/"),
                location,
                (location, *parent.facts.ancestors),
            )
            relative = parent.relative + ("\\" if parent.relative else "") + component
            parent = _View(canonical, facts, guard, relative=relative)
            self._views[str(input_path)] = parent
            self._views.setdefault(str(canonical), parent)
        if not parent.guard.is_directory and not leaf_may_be_file:
            raise ObservationChanged("non-directory path component")
        return parent

    def project(self, path: Path, *, leaf_may_be_file: bool = False) -> Path:
        return self._view(path, leaf_may_be_file=leaf_may_be_file).path

    def facts(self, path: Path):
        return self._view(path).facts

    def _descriptor(self, path: Path) -> _View:
        self._active()
        view = self._views.get(str(path))
        if view is None:
            return self._view(path)
        if not view.missing and not view.guard.is_directory:
            raise ObservationChanged("non-directory path component")
        return view

    def is_stable(self, path: Path) -> bool:
        # A conservative classification hint, never a negative lookup result.
        # Every actual comparison below refreshes its negative inputs.
        return not self._descriptor(path).missing

    def path_key(self, path: Path) -> str:
        import hashlib

        value = str(self.project(path)).replace("\\", "/").casefold()
        return hashlib.sha256(value.encode()).hexdigest()

    def same_path(self, first: Path, second: Path) -> bool:
        self._active()
        if first == second:
            return True
        left, right = self._view(first), self._view(second)
        return (
            not left.missing
            and not right.missing
            and left.facts.location == right.facts.location
        )

    def overlaps(self, first: Path, second: Path) -> bool:
        left, right = self._descriptor(first), self._descriptor(second)
        return self._overlaps_views(left, right)

    def _overlaps_views(self, left: _View, right: _View) -> bool:
        if self._state not in ("active", "comparing"):
            raise ObservationChanged("comparison used after its phase")

        def refresh(view: _View) -> None:
            if view.missing:
                self._probe_absence(view.probe)

        # Canonical positive prefixes are provisional under their version fence.
        # Native negative checks combine projection and endpoint observation;
        # there is no separate stale projection reused by the physical check.
        refresh(left)
        refresh(right)
        if (
            left.facts.portable == right.facts.portable
            or left.facts.portable.startswith(right.facts.portable + "/")
            or right.facts.portable.startswith(left.facts.portable + "/")
        ):
            return True
        if left.facts.location in right.facts.ancestors:
            return True
        refresh(right)
        refresh(left)
        return right.facts.location in left.facts.ancestors

    def contains(self, parent: Path, child: Path) -> bool:
        first, second = self._view(parent), self._view(child, leaf_may_be_file=True)
        return (
            second.facts.portable == first.facts.portable
            or second.facts.portable.startswith(first.facts.portable + "/")
        )

    def physically_contains(self, parent: Path, child: Path) -> bool:
        return self._view(parent).facts.location in self._view(child).facts.ancestors

    @contextlib.contextmanager
    def _lease(self, guard: _Guard):
        if guard.handle is not None:
            yield guard.handle
            return
        handle = self._open_child(guard.request)
        if handle is None:
            raise ObservationChanged("observed object disappeared")
        try:
            if self._identity(handle) != (guard.volume, guard.file_id):
                raise ObservationChanged("observed object identity changed")
            yield handle
        finally:
            self._release(handle)

    def _list_handle(self, guard: _Guard) -> tuple[str, ...]:
        with self._lease(guard) as handle:
            return self._list_open_directory(handle)

    def _list_open_directory(self, handle: Any) -> tuple[str, ...]:
        names = []
        restart = True
        while True:
            buffer = ctypes.create_string_buffer(65536)
            self._counts["commit_info_calls"] += 1
            self._counts["commit_directory_enumerations"] += 1
            if not self.reader._info(
                handle, 11 if restart else 10, buffer, len(buffer)
            ):
                error = ctypes.get_last_error()
                if error == 18:
                    break
                raise CommitUnavailable(f"directory enumeration unavailable ({error})")
            restart = False
            data = buffer.raw
            offset = 0
            while True:
                if offset + 104 > len(buffer):
                    raise CommitUnavailable("invalid directory enumeration")
                (next_offset,) = struct.unpack_from("<I", data, offset)
                (length,) = struct.unpack_from("<I", data, offset + 60)
                if length % 2 or offset + 104 + length > len(buffer):
                    raise CommitUnavailable("invalid directory name")
                name = data[offset + 104 : offset + 104 + length].decode("utf-16-le")
                if name not in (".", ".."):
                    names.append(name)
                if not next_offset:
                    break
                if next_offset < 104 or next_offset % 8:
                    raise CommitUnavailable("invalid directory enumeration offset")
                offset += next_offset
        return tuple(sorted(names))

    def list_names(
        self, path: Path, *, relevant: frozenset[str] | None = None
    ) -> tuple[str, ...]:
        view = self._view(path)
        if view.missing or not view.guard.is_directory:
            raise ObservationChanged("registry directory disappeared")
        names = self._list_handle(view.guard)
        if relevant is None:
            self._counts["commit_full_inventory_scans"] += 1
        observed = (
            names
            if relevant is None
            else tuple(name for name in names if name in relevant)
        )
        self._inventories.append((view.guard, observed, relevant))
        return names

    def read_json(self, path: Path, description: str) -> dict[str, Any]:
        view = self._view(path, leaf_may_be_file=True)
        if view.missing or view.guard.is_directory:
            raise ObservationChanged("registry record disappeared or changed type")
        if view.path != path:
            raise ObservationChanged("registry record path changed canonical spelling")
        with self._lease(view.guard) as handle:
            if self._version(handle) != view.guard.start_usn:
                raise ObservationChanged("registry record changed before reading")
            data = self._read_open_record(handle)
        value = json.loads(data)
        canonical = (
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        if not isinstance(value, dict) or canonical != data:
            raise ObservationChanged(f"{description} is not canonical JSON")
        self._counts["commit_records_read"] += 1
        return value

    def _read_open_record(self, handle: Any) -> bytes:
        self._counts["commit_record_seek_calls"] += 1
        if not self._seek(handle, 0, None, 0):
            raise CommitUnavailable("record seek unavailable")
        parts = []
        total = 0
        while True:
            buffer = ctypes.create_string_buffer(65536)
            size = self.w.DWORD()
            self._counts["commit_record_read_calls"] += 1
            if not self._read(handle, buffer, len(buffer), ctypes.byref(size), None):
                raise CommitUnavailable("record read unavailable")
            if not size.value:
                break
            total += size.value
            if total > self.MAX_RECORD_BYTES:
                raise CommitUnavailable("record exceeds observation budget")
            parts.append(buffer.raw[: size.value])
        return b"".join(parts)

    def record_exists(self, path: Path) -> bool:
        return not self._view(path, leaf_may_be_file=True).missing

    def _collect_witnesses(self, volume: _Volume, expected: dict[int, int]) -> None:
        if not expected:
            return
        epoch, first, next_usn = self._epoch(volume.handle)
        if epoch != volume.epoch or first > min(expected) or next_usn <= max(expected):
            raise ObservationChanged("journal epoch or witness range changed")
        cursor = min(expected)
        records = []
        remaining = set(expected)
        consumed = 0
        while remaining:
            request = struct.pack(
                "<qIIQQQHH4x", cursor, 0xFFFFFFFF, 0, 0, 0, epoch, 2, 3
            )
            self._counts["commit_journal_reads"] += 1
            data = self._io(volume.handle, 0x903AB, request, 1024 * 1024)
            consumed += len(data)
            self._counts["commit_journal_bytes"] += len(data)
            if consumed > self.MAX_JOURNAL_BYTES:
                raise CommitUnavailable("journal witness budget exceeded")
            following, batch = parse_journal_page(data)
            if following <= cursor:
                raise CommitUnavailable("journal witness cursor made no progress")
            for record in batch:
                if record.usn < cursor:
                    raise CommitUnavailable("journal witness cursor moved backward")
                if record.usn in expected:
                    records.append(record)
                    remaining.discard(record.usn)
            if following > max(expected) and remaining:
                raise CommitUnavailable("journal omitted required witnesses")
            cursor = following
        verify_witnesses(expected, records)
        epoch_after, _, next_after = self._epoch(volume.handle)
        if epoch_after != epoch or next_after < next_usn:
            raise ObservationChanged("journal changed while reading witnesses")
        self._counts["commit_witnesses"] += len(expected)

    def seal(self) -> None:
        self._require_owner()
        if self._state not in ("active", "observed"):
            raise ObservationChanged("read set sealed outside its phase")
        if self._comparison_reader is not None:
            probes = self._comparison_reader.probe_session.metrics()
            if (
                probes["commit_probe_state"] != "closed"
                or probes["commit_probe_active"]
                or probes["commit_probe_pending"]
            ):
                raise ProbeCleanupFailed("probe workers were not retired before seal")
        self._state = "sealing"
        for guard, names, relevant in self._inventories:
            current = self._list_handle(guard)
            if relevant is None:
                self._counts["commit_full_inventory_scans"] += 1
            current = (
                current
                if relevant is None
                else tuple(name for name in current if name in relevant)
            )
            if current != names:
                raise ObservationChanged("registry inventory changed")
        for root, view in self._roots.items():
            self._counts["commit_open_calls"] += 1
            handle = self.reader._open_existing(Path(root))
            if handle is None:
                raise ObservationChanged("drive binding disappeared")
            try:
                if self._identity(handle) != (view.guard.volume, view.guard.file_id):
                    raise ObservationChanged("drive binding changed")
            finally:
                self._release(handle)
        expected: dict[int, dict[int, int]] = {volume: {} for volume in self._volumes}
        certified: set[tuple[int, int]] = set()

        def certify(guard: _Guard, handle: Any) -> None:
            key = guard.volume, guard.file_id
            if key in certified:
                return
            if self._version(handle) != guard.start_usn:
                raise ObservationChanged("observed object version changed")
            witness = self._post_close(handle)
            if witness <= guard.start_usn or witness in expected[guard.volume]:
                raise CommitUnavailable("non-monotonic close witness")
            expected[guard.volume][witness] = guard.file_id
            certified.add(key)

        for parent, component, identity, request in self._bindings:
            self._counts["commit_binding_checks"] += 1
            if identity is None:
                self._probe_absence(request)
                continue
            handle = self._open_child(request)
            if handle is None:
                raise ObservationChanged("positive name binding disappeared")
            try:
                if self._identity(handle) != identity:
                    raise ObservationChanged("positive name binding changed")
                certify(self._objects[identity], handle)
            finally:
                self._release(handle)
        for guard in self._objects.values():
            if (guard.volume, guard.file_id) not in certified:
                with self._lease(guard) as handle:
                    certify(guard, handle)
        for volume, witnesses in expected.items():
            self._collect_witnesses(self._volumes[volume], witnesses)
        self._state = "sealed"

    def close(self) -> None:
        self._require_owner()
        error = self._cleanup_error
        if self._comparison_reader is not None:
            try:
                self._comparison_reader.close()
            except BaseException as failure:
                if error is None:
                    error = failure
            if not self._comparison_reader.probe_session.native_retired:
                raise ProbeCleanupFailed(
                    "root handles cannot close before native probe retirement"
                ) from error
        self._state = "closed"
        for guard in reversed(tuple(self._objects.values())):
            if guard.handle is None:
                continue
            # Never retry an uncertain close: the OS may already have consumed
            # the value and reused it for an unrelated process/thread handle.
            handle, guard.handle = guard.handle, None
            try:
                self._release(handle)
            except BaseException as failure:
                if error is None:
                    error = failure
        self._objects.clear()
        self._views.clear()
        self._roots.clear()
        self._bindings.clear()
        self._inventories.clear()
        self._volumes.clear()
        try:
            self.reader.close()
        except BaseException as failure:
            if error is None:
                error = failure
        if error is not None:
            self._state = "failed"
            self._cleanup_error = error
            if isinstance(error, Exception) and not isinstance(error, ProbeCleanupFailed):
                raise ProbeCleanupFailed("native observation cleanup failed") from error
            raise error

    def metrics(self) -> dict[str, Any]:
        probes = (
            {}
            if self._comparison_reader is None
            else self._comparison_reader.probe_session.metrics()
        )
        return {
            **self._counts,
            **probes,
            "commit_info_calls": self._counts["commit_info_calls"]
            + self.reader.information_calls,
            "commit_state": self._state,
            "commit_cleanup_failed": self._cleanup_error is not None,
            "commit_handles_opened": self.reader.handles_opened,
            "commit_handles_closed": self.reader.handles_closed,
            "commit_final_path_calls": self.reader.final_path_calls,
        }


class ProvisionalOwnershipIndex:
    """Index positives; compare every unstable endpoint with fresh negatives.

    No result is usable until the associated read set supplies all close
    witnesses. This object and its observations do not cross that boundary.
    """

    def __init__(self, model: Any, filesystem: WindowsObservationCommit, entries):
        self.model, self.filesystem = model, filesystem
        self.entries = tuple(entries)
        self.positive = model.OwnershipIndex(
            reservation for reservation, _, stable in self.entries if stable
        )
        self.negative = tuple(
            (reservation, path)
            for reservation, path, stable in self.entries
            if not stable
        )
        self.queries = 0
        self.fresh_comparisons = 0

    def _overlapping(self, path: Path):
        self.queries += 1
        if self.filesystem.is_stable(path):
            yield from self.positive.overlapping(self.filesystem.facts(path))
            remaining = self.negative
        else:
            remaining = tuple(
                (reservation, reserved) for reservation, reserved, _ in self.entries
            )
        probes = getattr(self.filesystem, "probe_session", None)
        if probes is not None:
            prepared = tuple(
                (reservation, self.filesystem.prepare_overlap(reserved, path))
                for reservation, reserved in remaining
            )
            self.fresh_comparisons += len(prepared)
            yield from probes.compare(prepared)
            return
        for reservation, reserved in remaining:
            self.fresh_comparisons += 1
            if self.filesystem.overlaps(reserved, path):
                yield reservation

    def conflict(
        self,
        *,
        root: Path,
        root_key: str,
        build_id: str,
        staging,
        retiring_root_keys: set[str],
    ):
        for reservation in self._overlapping(root):
            if reservation.kind == "root":
                if reservation.root_key != root_key:
                    return "root-root"
            else:
                return "root-staging"
        for target, path in staging:
            for reservation in self._overlapping(path):
                if reservation.kind == "root":
                    return "staging-root"
                if target == reservation.target and (
                    root_key == reservation.root_key
                    or (
                        reservation.root_key in retiring_root_keys
                        and build_id == reservation.build_id
                    )
                ):
                    continue
                return "staging-staging"
        return None


# Publish only after the complete helper has loaded. A syntactically valid
# truncated install must not advertise its contract. This is not a disk format.
COMMIT_CONTRACT_VERSION = 2
