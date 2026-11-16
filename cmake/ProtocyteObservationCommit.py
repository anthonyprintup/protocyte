"""Experimental optimistic read-set commit; never standalone mutation authority.

Positive objects use root-anchored short opens and exact ID/version witnesses.
Only volume roots retain handles; foreign build directories are not pinned.
Negative namespace observations are refreshed at every comparison and commit.
The coordinator still performs its ordinary reference validation afterward.
"""

from __future__ import annotations

import ctypes
import contextlib
import json
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class CommitUnavailable(RuntimeError):
    pass


class CapabilityUnavailable(CommitUnavailable):
    pass


class ObservationChanged(RuntimeError):
    pass


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


class WindowsObservationCommit:
    """One bounded read set; instances and facts are never shared across phases."""

    MAX_OBJECTS = 32768
    MAX_JOURNAL_BYTES = 64 * 1024 * 1024
    MAX_RECORD_BYTES = 16 * 1024 * 1024

    def __init__(self, native: Any, model: Any) -> None:
        if os.name != "nt":
            raise CapabilityUnavailable("commit observations require Windows")
        self.native, self.model = native, model
        self.reader = native.FreshPathObserver()
        self.w = self.reader._w
        self._state = "active"
        self._objects: dict[tuple[int, int], _Guard] = {}
        self._volumes: dict[int, _Volume] = {}
        self._roots: dict[str, _View] = {}
        self._views: dict[str, _View] = {}
        self._bindings: list[tuple[_Guard, str, tuple[int, int] | None, Any]] = []
        self._inventories: list[
            tuple[_Guard, tuple[str, ...], frozenset[str] | None]
        ] = []
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

    def _active(self) -> None:
        if self._state != "active":
            raise ObservationChanged("read set used outside its observation phase")

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
        if not self.reader._close(handle):
            raise CommitUnavailable("native handle release failed")
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
        result = self.reader._open(
            ctypes.byref(handle),
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
        self._active()
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
        self._state = "closed"
        error = None
        for guard in reversed(tuple(self._objects.values())):
            if guard.handle is None:
                continue
            try:
                self._release(guard.handle)
            except Exception as failure:
                error = failure
        self._objects.clear()
        self._views.clear()
        self._roots.clear()
        self._bindings.clear()
        self._inventories.clear()
        self._volumes.clear()
        self.reader.close()
        if error is not None:
            raise error

    def metrics(self) -> dict[str, Any]:
        return {
            **self._counts,
            "commit_info_calls": self._counts["commit_info_calls"]
            + self.reader.information_calls,
            "commit_state": self._state,
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
