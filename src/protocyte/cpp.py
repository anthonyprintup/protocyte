from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import BinaryIO

from protocyte.errors import ProtocyteError
from protocyte.model import (
    SCALAR_CPP_TYPES,
    SCALAR_DEFAULTS,
    DescriptorModel,
    EnumModel,
    FieldDescriptorProto,
    FieldModel,
    FileModel,
    MessageModel,
    OneofModel,
    SourceDocumentation,
    _cpp_string_literal,
    cpp_identifier,
    cpp_derivable_identifier,
    cpp_pascal_identifier,
)
from protocyte.names import CppNameKind, EmittedNameScope
from protocyte.parameters import GeneratorOptions
from protocyte.paths import generated_file_base
from protocyte.runtime import runtime_files


_RUNTIME_SCALAR_TYPES = {
    "int32_t": "::protocyte::i32",
    "int64_t": "::protocyte::i64",
    "uint32_t": "::protocyte::u32",
    "uint64_t": "::protocyte::u64",
    "float": "::protocyte::f32",
    "double": "::protocyte::f64",
}

_SCALAR_READ_HELPERS = {
    FieldDescriptorProto.TYPE_INT32: "read_int32",
    FieldDescriptorProto.TYPE_INT64: "read_int64",
    FieldDescriptorProto.TYPE_UINT32: "read_uint32",
    FieldDescriptorProto.TYPE_UINT64: "read_uint64",
    FieldDescriptorProto.TYPE_SINT32: "read_sint32",
    FieldDescriptorProto.TYPE_SINT64: "read_sint64",
    FieldDescriptorProto.TYPE_FIXED32: "read_fixed32_value",
    FieldDescriptorProto.TYPE_FIXED64: "read_fixed64_value",
    FieldDescriptorProto.TYPE_SFIXED32: "read_sfixed32",
    FieldDescriptorProto.TYPE_SFIXED64: "read_sfixed64",
    FieldDescriptorProto.TYPE_FLOAT: "read_float",
    FieldDescriptorProto.TYPE_DOUBLE: "read_double",
    FieldDescriptorProto.TYPE_BOOL: "read_bool",
    FieldDescriptorProto.TYPE_ENUM: "read_enum",
}

_SCALAR_WRITE_HELPERS = {
    FieldDescriptorProto.TYPE_INT32: "write_int32",
    FieldDescriptorProto.TYPE_INT64: "write_int64",
    FieldDescriptorProto.TYPE_UINT32: "write_uint32",
    FieldDescriptorProto.TYPE_UINT64: "write_uint64",
    FieldDescriptorProto.TYPE_SINT32: "write_sint32",
    FieldDescriptorProto.TYPE_SINT64: "write_sint64",
    FieldDescriptorProto.TYPE_FIXED32: "write_fixed32_value",
    FieldDescriptorProto.TYPE_FIXED64: "write_fixed64_value",
    FieldDescriptorProto.TYPE_SFIXED32: "write_sfixed32",
    FieldDescriptorProto.TYPE_SFIXED64: "write_sfixed64",
    FieldDescriptorProto.TYPE_FLOAT: "write_float",
    FieldDescriptorProto.TYPE_DOUBLE: "write_double",
    FieldDescriptorProto.TYPE_BOOL: "write_bool",
    FieldDescriptorProto.TYPE_ENUM: "write_enum",
}


@dataclass
class _OutputBudget:
    max_bytes: int | None
    used_bytes: int = 0

    def consume(self, content: str) -> None:
        content_bytes = len(content.encode("utf-8"))
        next_total = self.used_bytes + content_bytes
        if self.max_bytes is not None and next_total > self.max_bytes:
            raise ProtocyteError(
                "generator policy limit exceeded for generated output bytes: "
                f"{next_total} > {self.max_bytes}"
            )
        self.used_bytes = next_total

    def remaining(self) -> int | None:
        if self.max_bytes is None:
            return None
        return self.max_bytes - self.used_bytes


@dataclass
class _FormatterResult:
    returncode: int
    stdout: str
    stderr: str


def _decode_formatter_result(
    returncode: int,
    stdout: bytes,
    stderr: bytes,
) -> _FormatterResult:
    return _FormatterResult(
        returncode=returncode,
        stdout=stdout.decode("utf-8")
        if returncode == 0
        else stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )


class _FormatterOutputLimit(Exception):
    pass


_FORMATTER_TEARDOWN_TIMEOUT_SECONDS = 0.5
_FORMATTER_SUPERVISOR_STATUS_MAX_BYTES = 4096
_FORMATTER_SUPERVISOR_PATH = Path(__file__).with_name("_formatter_supervisor.py")
_WINDOWS_CREATE_SUSPENDED = 0x00000004
_WINDOWS_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_WINDOWS_JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
_WINDOWS_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


class _WindowsJobBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", wintypes.LARGE_INTEGER),
        ("per_job_user_time_limit", wintypes.LARGE_INTEGER),
        ("limit_flags", wintypes.DWORD),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority_class", wintypes.DWORD),
        ("scheduling_class", wintypes.DWORD),
    ]


class _WindowsIoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]


class _WindowsJobExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _WindowsJobBasicLimitInformation),
        ("io_info", _WindowsIoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


class _WindowsJobBasicAccountingInformation(ctypes.Structure):
    _fields_ = [
        ("total_user_time", wintypes.LARGE_INTEGER),
        ("total_kernel_time", wintypes.LARGE_INTEGER),
        ("this_period_total_user_time", wintypes.LARGE_INTEGER),
        ("this_period_total_kernel_time", wintypes.LARGE_INTEGER),
        ("total_page_fault_count", wintypes.DWORD),
        ("total_processes", wintypes.DWORD),
        ("active_processes", wintypes.DWORD),
        ("total_terminated_processes", wintypes.DWORD),
    ]


def _windows_kernel32():
    return ctypes.WinDLL("kernel32", use_last_error=True)


def _raise_windows_error() -> None:
    raise ctypes.WinError(ctypes.get_last_error())


class _WindowsFormatterJob:
    def __init__(self, handle: int) -> None:
        self._handle: int | None = handle

    @classmethod
    def create(cls) -> _WindowsFormatterJob:
        kernel32 = _windows_kernel32()
        create_job = kernel32.CreateJobObjectW
        create_job.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        create_job.restype = wintypes.HANDLE
        handle = create_job(None, None)
        if not handle:
            _raise_windows_error()

        information = _WindowsJobExtendedLimitInformation()
        information.basic_limit_information.limit_flags = (
            _WINDOWS_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        set_information = kernel32.SetInformationJobObject
        set_information.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        set_information.restype = wintypes.BOOL
        if not set_information(
            handle,
            _WINDOWS_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(information),
            ctypes.sizeof(information),
        ):
            error = ctypes.WinError(ctypes.get_last_error())
            kernel32.CloseHandle(handle)
            raise error
        return cls(handle)

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        if self._handle is None:
            raise OSError("formatter job is already closed")
        process_handle = getattr(process, "_handle", None)
        if process_handle is None:
            raise OSError("formatter process handle is unavailable")

        kernel32 = _windows_kernel32()
        assign_process = kernel32.AssignProcessToJobObject
        assign_process.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        assign_process.restype = wintypes.BOOL
        if not assign_process(self._handle, int(process_handle)):
            _raise_windows_error()

    def has_active_processes(self) -> bool:
        if self._handle is None:
            return False
        information = _WindowsJobBasicAccountingInformation()
        kernel32 = _windows_kernel32()
        query_information = kernel32.QueryInformationJobObject
        query_information.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        )
        query_information.restype = wintypes.BOOL
        if not query_information(
            self._handle,
            _WINDOWS_JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
            ctypes.byref(information),
            ctypes.sizeof(information),
            None,
        ):
            _raise_windows_error()
        return information.active_processes != 0

    def close(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        kernel32 = _windows_kernel32()
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        if not close_handle(handle):
            _raise_windows_error()


# POSIX has no portable Job Object equivalent. A retained supervisor pins the
# fresh formatter process-group identity until its status is reported and every
# grouped process is killed. A trusted formatter that deliberately creates
# another session or process group is outside this containment contract.
@dataclass(frozen=True)
class _PosixFormatterGroup:
    process_group_id: int
    status_stream: BinaryIO

    def wait_for_formatter_exit(
        self,
        command: list[str],
        timeout_seconds: float | None,
    ) -> int:
        deadline = (
            None if timeout_seconds is None else time.monotonic() + timeout_seconds
        )
        content = bytearray()
        while b"\n" not in content:
            remaining = (
                None if deadline is None else max(0.0, deadline - time.monotonic())
            )
            if remaining == 0:
                raise subprocess.TimeoutExpired(command, timeout_seconds)
            try:
                readable, _, _ = select.select(
                    (self.status_stream,),
                    (),
                    (),
                    remaining,
                )
            except InterruptedError:
                continue
            if not readable:
                raise subprocess.TimeoutExpired(command, timeout_seconds)
            try:
                chunk = os.read(self.status_stream.fileno(), 1024)
            except InterruptedError:
                continue
            if not chunk:
                raise OSError("formatter supervisor exited without reporting status")
            content.extend(chunk)
            if len(content) > _FORMATTER_SUPERVISOR_STATUS_MAX_BYTES:
                raise OSError("formatter supervisor reported an oversized status")

        line, _, remainder = content.partition(b"\n")
        if remainder:
            raise OSError("formatter supervisor reported trailing status data")
        try:
            payload = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OSError("formatter supervisor reported an invalid status") from exc

        if isinstance(payload, dict) and set(payload) == {"returncode"}:
            returncode = payload["returncode"]
            if isinstance(returncode, int) and not isinstance(returncode, bool):
                return returncode
            raise OSError("formatter supervisor reported an invalid return code")

        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            raise OSError("formatter supervisor reported an invalid status")
        error_number = error.get("errno")
        message = error.get("message")
        filename = error.get("filename")
        if not isinstance(message, str):
            raise OSError("formatter supervisor reported an invalid launch error")
        if error_number is None:
            raise OSError(message)
        if not isinstance(error_number, int) or isinstance(error_number, bool):
            raise OSError("formatter supervisor reported an invalid launch errno")
        if filename is not None and not isinstance(filename, str):
            raise OSError("formatter supervisor reported an invalid launch filename")
        raise OSError(error_number, message, filename)

    def close(self) -> None:
        self.status_stream.close()


def _resume_windows_formatter_process(process: subprocess.Popen[bytes]) -> None:
    process_handle = getattr(process, "_handle", None)
    if process_handle is None:
        raise OSError("formatter process handle is unavailable")

    # Popen closes the primary thread handle, so resume via its retained process
    # handle instead of rediscovering a thread by a potentially reused PID.
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    resume_process = ntdll.NtResumeProcess
    resume_process.argtypes = (wintypes.HANDLE,)
    resume_process.restype = wintypes.LONG
    status = resume_process(int(process_handle))
    if status < 0:
        raise OSError(
            f"could not resume the suspended formatter process: NTSTATUS 0x{status & 0xFFFFFFFF:08X}"
        )


def _formatter_popen_kwargs(
    status_write_fd: int | None = None,
) -> dict[str, object]:
    if os.name == "nt":
        return {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | _WINDOWS_CREATE_SUSPENDED
        }
    kwargs: dict[str, object] = {"start_new_session": True}
    if status_write_fd is not None:
        kwargs["pass_fds"] = (status_write_fd,)
    return kwargs


def _formatter_supervisor_command(
    command: list[str],
    status_write_fd: int,
) -> list[str]:
    return [
        sys.executable,
        str(_FORMATTER_SUPERVISOR_PATH),
        str(status_write_fd),
        *command,
    ]


def _start_formatter_process(
    command: list[str],
) -> tuple[
    subprocess.Popen[bytes],
    _WindowsFormatterJob | _PosixFormatterGroup,
]:
    containment: _WindowsFormatterJob | _PosixFormatterGroup
    windows_job = _WindowsFormatterJob.create() if os.name == "nt" else None
    status_read_fd: int | None = None
    status_write_fd: int | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        launch_command = command
        if windows_job is None:
            status_read_fd, status_write_fd = os.pipe()
            launch_command = _formatter_supervisor_command(command, status_write_fd)
        process = subprocess.Popen(
            launch_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_formatter_popen_kwargs(status_write_fd),
        )
        if windows_job is not None:
            windows_job.assign(process)
            _resume_windows_formatter_process(process)
            containment = windows_job
        else:
            assert status_read_fd is not None
            assert status_write_fd is not None
            os.close(status_write_fd)
            status_write_fd = None
            status_stream = os.fdopen(status_read_fd, "rb", buffering=0)
            status_read_fd = None
            containment = _PosixFormatterGroup(process.pid, status_stream)
        return process, containment
    except BaseException:
        for descriptor in (status_read_fd, status_write_fd):
            if descriptor is None:
                continue
            try:
                os.close(descriptor)
            except OSError:
                pass
        if windows_job is not None:
            try:
                windows_job.close()
            except OSError:
                pass
        if process is not None:
            if windows_job is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
            try:
                process.kill()
            except OSError:
                pass
            _wait_for_formatter_termination(process)
        raise


def _terminate_formatter_process_tree(
    process: subprocess.Popen[bytes],
    containment: _WindowsFormatterJob | _PosixFormatterGroup,
) -> None:
    if isinstance(containment, _WindowsFormatterJob):
        try:
            containment.close()
        except OSError:
            pass
    else:
        try:
            os.killpg(containment.process_group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            pass

    try:
        process.kill()
    except (OSError, ProcessLookupError):
        pass


def _wait_for_formatter_termination(process: subprocess.Popen[bytes]) -> None:
    try:
        process.wait(timeout=_FORMATTER_TEARDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except (OSError, ProcessLookupError):
            pass
        try:
            process.wait(timeout=_FORMATTER_TEARDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            pass


def _join_formatter_threads(threads: tuple[threading.Thread, ...]) -> bool:
    deadline = time.monotonic() + _FORMATTER_TEARDOWN_TIMEOUT_SECONDS
    for thread in threads:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        thread.join(timeout=remaining)
    return any(thread.is_alive() for thread in threads)


def _close_formatter_streams(streams: Iterable[BinaryIO | None]) -> None:
    for stream in streams:
        if stream is None:
            continue
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _cleanup_formatter_setup_failure(
    process: subprocess.Popen[bytes],
    job: _WindowsFormatterJob | _PosixFormatterGroup,
    started_threads: list[threading.Thread],
    worker_streams: list[tuple[threading.Thread, BinaryIO]],
) -> None:
    _terminate_formatter_process_tree(process, job)
    _wait_for_formatter_termination(process)

    started_ids = {id(thread) for thread in started_threads}
    started_stream_ids = {
        id(stream) for thread, stream in worker_streams if id(thread) in started_ids
    }
    process_streams = (process.stdin, process.stdout, process.stderr)
    _close_formatter_streams(
        stream
        for stream in process_streams
        if stream is not None and id(stream) not in started_stream_ids
    )
    _join_formatter_threads(tuple(started_threads))
    _close_formatter_streams(process_streams)
    if job is not None:
        try:
            job.close()
        except OSError:
            pass


def _run_formatter_bounded(
    command: list[str],
    content: str,
    *,
    timeout_seconds: float | None,
    max_output_bytes: int | None,
) -> _FormatterResult:
    input_bytes = content.encode("utf-8")
    process, job = _start_formatter_process(command)
    started_threads: list[threading.Thread] = []
    worker_streams: list[tuple[threading.Thread, BinaryIO]] = []
    try:
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None

        output_lock = threading.Lock()
        output_size = 0
        output_limit_reached = threading.Event()
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        io_errors: list[OSError] = []
        termination_lock = threading.Lock()
        termination_requested = False

        def terminate_process_tree() -> None:
            nonlocal termination_requested
            with termination_lock:
                if termination_requested:
                    return
                termination_requested = True
            _terminate_formatter_process_tree(process, job)

        def read_stream(stream, chunks: list[bytes]) -> None:
            nonlocal output_size
            try:
                while chunk := stream.read(64 * 1024):
                    with output_lock:
                        if (
                            max_output_bytes is not None
                            and output_size + len(chunk) > max_output_bytes
                        ):
                            output_limit_reached.set()
                        else:
                            output_size += len(chunk)
                            chunks.append(chunk)
                    if output_limit_reached.is_set():
                        terminate_process_tree()
                        return
            except OSError as exc:
                if not output_limit_reached.is_set():
                    io_errors.append(exc)
            finally:
                stream.close()

        def write_input() -> None:
            try:
                process.stdin.write(input_bytes)
            except (BrokenPipeError, OSError, ValueError):
                pass
            finally:
                try:
                    process.stdin.close()
                except OSError:
                    pass

        worker_streams = [
            (
                threading.Thread(
                    target=read_stream,
                    args=(process.stdout, stdout_chunks),
                    name="protocyte-formatter-stdout",
                    daemon=True,
                ),
                process.stdout,
            ),
            (
                threading.Thread(
                    target=read_stream,
                    args=(process.stderr, stderr_chunks),
                    name="protocyte-formatter-stderr",
                    daemon=True,
                ),
                process.stderr,
            ),
            (
                threading.Thread(
                    target=write_input,
                    name="protocyte-formatter-stdin",
                    daemon=True,
                ),
                process.stdin,
            ),
        ]
        for thread, _stream in worker_streams:
            thread.start()
            started_threads.append(thread)
    except BaseException:
        _cleanup_formatter_setup_failure(process, job, started_threads, worker_streams)
        raise

    stdout_reader, stderr_reader, stdin_writer = (
        thread for thread, _stream in worker_streams
    )

    timeout: subprocess.TimeoutExpired | None = None
    formatter_error: OSError | None = None
    descendant_error: str | None = None
    returncode = 0
    try:
        if isinstance(job, _PosixFormatterGroup):
            try:
                returncode = job.wait_for_formatter_exit(command, timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                timeout = exc
            except OSError as exc:
                if not output_limit_reached.is_set():
                    formatter_error = exc
            finally:
                # The live supervisor still owns the original PGID here, so it
                # cannot be reused between status receipt and group teardown.
                terminate_process_tree()
                _wait_for_formatter_termination(process)
        else:
            try:
                returncode = process.wait(timeout=timeout_seconds)
                try:
                    if job.has_active_processes():
                        descendant_error = "formatter exited while descendant processes remained active"
                except OSError as exc:
                    descendant_error = (
                        f"failed to verify formatter containment state: {exc}"
                    )
            except subprocess.TimeoutExpired as exc:
                timeout = exc
                terminate_process_tree()
                _wait_for_formatter_termination(process)
    finally:
        threads = (stdin_writer, stdout_reader, stderr_reader)
        if descendant_error is not None:
            terminate_process_tree()
            _wait_for_formatter_termination(process)
        if _join_formatter_threads(threads):
            if timeout is None and not output_limit_reached.is_set():
                descendant_error = (
                    descendant_error
                    or "formatter exited while descendants kept its output pipes open"
                )
            terminate_process_tree()
            _wait_for_formatter_termination(process)
            _join_formatter_threads(threads)
        job.close()

    if timeout is not None:
        timeout.output = b"".join(stdout_chunks)
        timeout.stderr = b"".join(stderr_chunks)
        raise timeout

    if output_limit_reached.is_set():
        raise _FormatterOutputLimit
    if formatter_error is not None:
        raise formatter_error
    if descendant_error is not None:
        detail = b"".join(stderr_chunks).decode("utf-8", errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise OSError(f"{descendant_error}{suffix}")
    if io_errors:
        raise io_errors[0]
    return _decode_formatter_result(
        returncode,
        b"".join(stdout_chunks),
        b"".join(stderr_chunks),
    )


@dataclass
class CppWriter:
    indent_level: int = 0
    lines: list[str] = field(default_factory=list)
    declared_names: list[set[str]] = field(default_factory=lambda: [set()])
    output_budget: _OutputBudget | None = None

    def line(self, text: str = "") -> None:
        rendered = ("  " * self.indent_level + text) if text else ""
        if self.output_budget is not None:
            self.output_budget.consume(rendered + "\n")
        self.lines.append(rendered)

    def push(self, level: int = 1) -> None:
        if level < 0:
            raise ValueError("indent level increment must be non-negative")
        self.indent_level += level

    def pop(self, level: int = 1) -> None:
        if level < 0:
            raise ValueError("indent level decrement must be non-negative")
        if level > self.indent_level:
            raise ValueError("indent level cannot be negative")
        self.indent_level -= level

    @contextmanager
    def indent(self, level: int = 1) -> Iterator[None]:
        self.push(level)
        try:
            yield
        finally:
            self.pop(level)

    @contextmanager
    def cpp_scope(self) -> Iterator[None]:
        self.declared_names.append(set())
        try:
            yield
        finally:
            self.declared_names.pop()

    @contextmanager
    def local_decl(self, name: str, *, force_scope: bool = False) -> Iterator[None]:
        if force_scope or name in self.declared_names[-1]:
            self.line("{")
            self.push()
            self.declared_names.append({name})
            try:
                yield
            finally:
                self.declared_names.pop()
                self.pop()
                self.line("}")
            return
        self.declared_names[-1].add(name)
        yield

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


def _emit_documentation(
    w: CppWriter, documentation: SourceDocumentation, options: GeneratorOptions
) -> None:
    if not options.emit_comments or not documentation.text:
        return
    w.line("/**")
    for source_line in documentation.text.split("\n"):
        safe_line = _sanitize_documentation_line(source_line)
        w.line(f" * {safe_line}" if safe_line else " *")
    w.line(" */")


def _sanitize_documentation_line(value: str) -> str:
    escaped = value.replace("*/", "* /")
    return "".join(
        char
        if char == "\t" or ord(char) >= 0x20 and ord(char) != 0x7F
        else f"\\x{ord(char):02X}"
        for char in escaped
    )


def _emit_field_api_annotations(
    w: CppWriter, item: FieldModel, options: GeneratorOptions
) -> None:
    _emit_documentation(w, item.documentation, options)
    if item.deprecated:
        w.line("[[deprecated]]")


@dataclass
class _CppNameScope:
    label: str
    names: dict[str, str] = field(default_factory=dict)
    emitted: EmittedNameScope = field(init=False)

    def __post_init__(self) -> None:
        self.emitted = EmittedNameScope(self.label)

    def owner(self, name: str) -> str | None:
        return self.names.get(name)

    def reserve(self, name: str, owner: str, *, error: str | None = None) -> None:
        existing = self.names.get(name)
        if existing is not None and existing != owner:
            raise ProtocyteError(
                error
                or f"{self.label}: generated C++ name {name!r} from {owner} collides with {existing}"
            )
        try:
            self.emitted.reserve(
                name,
                owner=owner,
                kind=CppNameKind.IMPLEMENTATION,
            )
        except ValueError as exc:
            raise ProtocyteError(error or str(exc)) from exc
        self.names[name] = owner


@dataclass
class _CppNameRegistry:
    scopes: dict[str, _CppNameScope] = field(default_factory=dict)

    def scope(self, label: str) -> _CppNameScope:
        scope = self.scopes.get(label)
        if scope is None:
            scope = _CppNameScope(label)
            self.scopes[label] = scope
        return scope


@dataclass
class _CppFunctionScope:
    label: str
    visible_storage: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)

    def parameter(self, name: str) -> None:
        self._reserve(name, "parameter")

    def local(self, name: str) -> None:
        self._reserve(name, "local")

    def _reserve(self, name: str, kind: str) -> None:
        if name in self.visible_storage:
            raise ProtocyteError(
                f"{self.label}: {kind} {name!r} shadows visible generated storage"
            )
        if name in self.names:
            raise ProtocyteError(f"{self.label}: {kind} {name!r} is already declared")
        self.names.add(name)


def generate_outputs(
    model: DescriptorModel,
    options: GeneratorOptions,
    *,
    format_outputs: bool = True,
    formatter_timeout_seconds: float | None = None,
    max_output_bytes: int | None = None,
) -> dict[str, str]:
    _validate_generated_cpp_names(model, options)
    output_budget = _OutputBudget(max_output_bytes)
    outputs: dict[str, str] = {}
    output_owners: dict[str, tuple[str, str]] = {}
    if options.emit_runtime:
        for name, content in runtime_files(options.runtime_prefix).items():
            output_budget.consume(content)
            outputs[name] = content
            output_owners[name.casefold()] = ("generated runtime", name)
    for file_model in model.generated_files():
        header_name = _header_name(file_model.name, options)
        source_name = _source_name(file_model.name, options)
        for name in (header_name, source_name):
            collision = output_owners.get(name.casefold())
            if collision is not None:
                collision_owner, collision_name = collision
                raise ProtocyteError(
                    "generated file name collision after portable path normalization: "
                    f"{collision_owner} produces {collision_name!r}, while descriptor file "
                    f"{file_model.name!r} produces {name!r}; these paths collide on "
                    "case-insensitive filesystems"
                )
            output_owners[name.casefold()] = (
                f"descriptor file {file_model.name!r}",
                name,
            )
        outputs[header_name] = generate_header(
            file_model, options, output_budget=output_budget
        )
        outputs[source_name] = generate_source(
            file_model, options, output_budget=output_budget
        )
    if not format_outputs:
        if options.formatting_required:
            raise ProtocyteError(
                "output formatting is required but disabled by the generator policy"
            )
        return outputs
    if options.format_mode == "off":
        return outputs
    return _format_cpp_outputs(
        outputs,
        options,
        timeout_seconds=formatter_timeout_seconds,
        max_output_bytes=max_output_bytes,
    )


def _format_cpp_outputs(
    outputs: dict[str, str],
    options: GeneratorOptions,
    *,
    timeout_seconds: float | None = None,
    max_output_bytes: int | None = None,
) -> dict[str, str]:
    style_args = _clang_format_style_args(options)
    clang_format = _resolve_clang_format_executable(options)
    if clang_format is None:
        if options.formatting_required:
            raise ProtocyteError(
                "clang-format is required but was not found on PATH; "
                "set clang_format=<executable-or-path> or use format=auto or format=off"
            )
        return outputs

    formatted: dict[str, str] = {}
    formatted_budget = _OutputBudget(max_output_bytes)
    style_root = Path.cwd().resolve()
    for name, content in outputs.items():
        if not name.endswith((".h", ".hh", ".hpp", ".c", ".cc", ".cpp", ".cxx")):
            formatted_budget.consume(content)
            formatted[name] = content
            continue
        try:
            assume_filename = (style_root / name).resolve()
            command = [
                clang_format,
                *style_args,
                f"--assume-filename={assume_filename}",
            ]
            remaining = formatted_budget.remaining()
            if remaining is None and timeout_seconds is None:
                completed = subprocess.run(
                    command,
                    input=content.encode("utf-8"),
                    capture_output=True,
                    check=False,
                )
                result = _decode_formatter_result(
                    completed.returncode,
                    completed.stdout,
                    completed.stderr,
                )
            else:
                result = _run_formatter_bounded(
                    command,
                    content,
                    timeout_seconds=timeout_seconds,
                    max_output_bytes=remaining,
                )
        except subprocess.TimeoutExpired as exc:
            stderr = exc.stderr
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            detail = stderr.strip() if isinstance(stderr, str) else ""
            suffix = f": {detail}" if detail else ""
            raise ProtocyteError(
                f"clang-format timed out for {name} after {timeout_seconds} seconds{suffix}"
            ) from exc
        except _FormatterOutputLimit as exc:
            raise ProtocyteError(
                "generator policy limit exceeded for generated output bytes while "
                f"formatting {name}: more than {max_output_bytes} bytes"
            ) from exc
        except UnicodeEncodeError as exc:
            raise ProtocyteError(
                f"clang-format input for {name} is not valid UTF-8"
            ) from exc
        except UnicodeDecodeError as exc:
            raise ProtocyteError(
                f"clang-format produced invalid UTF-8 output for {name}"
            ) from exc
        except OSError as exc:
            raise ProtocyteError(f"failed to run clang-format: {exc}") from exc
        if result.returncode != 0:
            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or f"exit code {result.returncode}"
            )
            raise ProtocyteError(f"clang-format failed for {name}: {detail}")
        formatted_budget.consume(result.stdout)
        formatted[name] = result.stdout
    return formatted


def _resolve_clang_format_executable(options: GeneratorOptions) -> str | None:
    if options.clang_format:
        return options.clang_format
    return shutil.which("clang-format")


def _clang_format_style_args(options: GeneratorOptions) -> list[str]:
    config = _resolve_clang_format_config(options)
    if config is None:
        return ["--style=file"]
    return [f"--style=file:{config}"]


def _resolve_clang_format_config(options: GeneratorOptions) -> str | None:
    if options.clang_format_config is None:
        return None
    config = Path(options.clang_format_config)
    if not config.is_file():
        raise ProtocyteError(
            f"clang-format config was not found: {options.clang_format_config}"
        )
    return options.clang_format_config


def _validate_generated_cpp_names(
    model: DescriptorModel, options: GeneratorOptions
) -> None:
    _validate_generated_reflection_symbols(model, options)
    _validate_generated_namespace_scopes(model, options)
    for file_model in model.generated_files():
        namespace_parts = _namespace_parts(file_model, options)
        if namespace_parts[:1] == ["protocyte"]:
            namespace = "::".join(namespace_parts)
            raise ProtocyteError(
                f"{file_model.name}: generated namespace ::{namespace} enters "
                "Protocyte's runtime-owned ::protocyte namespace; set "
                "namespace_prefix to an application-owned namespace such as "
                "my_project::wire"
            )
        for message in _walk_generated_messages(file_model.messages):
            if not message.is_map_entry:
                _build_message_cpp_name_registry(message, options)


@dataclass(slots=True)
class _GeneratedCppSymbol:
    kind: str
    owner: str


@dataclass(slots=True)
class _GeneratedCppNamespace:
    parts: tuple[str, ...]
    owner: str | None = None
    children: dict[str, "_GeneratedCppNamespace"] = field(default_factory=dict)
    symbols: dict[str, _GeneratedCppSymbol] = field(default_factory=dict)

    def namespace(self, parts: list[str], *, owner: str) -> "_GeneratedCppNamespace":
        current = self
        for part in parts:
            symbol = current.symbols.get(part)
            if symbol is not None:
                full_name = (*current.parts, part)
                raise ProtocyteError(
                    f"{owner}: generated namespace {_cpp_namespace_name(full_name)} "
                    f"collides with generated {symbol.kind} {symbol.owner!r} "
                    f"in namespace {_cpp_namespace_name(current.parts)}"
                )
            child = current.children.get(part)
            if child is None:
                child = _GeneratedCppNamespace((*current.parts, part), owner)
                current.children[part] = child
            current = child
        return current

    def symbol(self, name: str, *, kind: str, owner: str) -> None:
        namespace = self.children.get(name)
        if namespace is not None:
            raise ProtocyteError(
                f"{owner}: generated {kind} {name!r} collides with generated "
                f"namespace {_cpp_namespace_name(namespace.parts)} introduced by "
                f"{namespace.owner}"
            )
        existing = self.symbols.get(name)
        if existing is not None:
            raise ProtocyteError(
                f"{owner}: generated {kind} {name!r} collides with generated "
                f"{existing.kind} {existing.owner!r} in namespace "
                f"{_cpp_namespace_name(self.parts)}"
            )
        self.symbols[name] = _GeneratedCppSymbol(kind, owner)


def _cpp_namespace_name(parts: tuple[str, ...]) -> str:
    return "::" + "::".join(parts) if parts else "::"


def _generated_namespace_owner(file_model: FileModel) -> str:
    return f"descriptor file {file_model.name!r} package {file_model.package!r}"


def _validate_generated_namespace_scopes(
    model: DescriptorModel, options: GeneratorOptions
) -> None:
    namespaces = _GeneratedCppNamespace(())
    scope_files = _generated_cpp_scope_files(model)

    for file_model in scope_files:
        namespaces.namespace(
            _namespace_parts(file_model, options),
            owner=_generated_namespace_owner(file_model),
        )

    for file_model in scope_files:
        namespace = namespaces.namespace(
            _namespace_parts(file_model, options),
            owner=_generated_namespace_owner(file_model),
        )
        for full_name, cpp_name in _file_generated_cpp_symbols(file_model):
            namespace.symbol(cpp_name, kind="type", owner=full_name)
        for constant in file_model.constants:
            namespace.symbol(
                constant.cpp_name,
                kind="package constant",
                owner=constant.full_name,
            )

    for file_model in scope_files:
        messages = [
            message
            for message in _walk_generated_messages(file_model.messages)
            if not message.is_map_entry
        ]
        if not messages:
            continue
        reflection_namespace = namespaces.namespace(
            [*_namespace_parts(file_model, options), "protocyte_reflection"],
            owner=f"descriptor file {file_model.name!r} generated reflection API",
        )
        for message in messages:
            reflection_namespace.symbol(
                _reflection_name(message),
                kind="reflection symbol",
                owner=message.full_name,
            )


def _file_generated_cpp_symbols(file_model: FileModel) -> Iterator[tuple[str, str]]:
    for enum in file_model.enums:
        yield enum.full_name, enum.cpp_name
    for message in _walk_generated_messages(file_model.messages):
        if message.is_map_entry:
            continue
        yield message.full_name, message.cpp_name
        for enum in message.nested_enums:
            yield enum.full_name, enum.cpp_name


def _generated_cpp_scope_files(model: DescriptorModel) -> list[FileModel]:
    """Return generated headers and every generated header they include.

    A CodeGeneratorRequest carries descriptors for imports used only to decode
    custom options.  Those descriptors do not become C++ declarations unless a
    generated header actually includes them, so namespace validation must not
    treat the whole request as one translation unit.
    """

    included: set[str] = set()
    pending = list(model.file_to_generate)
    while pending:
        file_name = pending.pop()
        if file_name in included:
            continue
        included.add(file_name)
        file_model = model.files[file_name]
        for dependency in _generated_header_dependencies(file_model):
            if dependency != file_name:
                pending.append(dependency)

    return [
        file_model
        for file_name, file_model in model.files.items()
        if file_name in included
    ]


def _generated_header_dependencies(file_model: FileModel) -> Iterator[str]:
    for message in _walk_generated_messages(file_model.messages):
        for field_model in message.fields:
            yield from _field_generated_header_dependencies(field_model)


def _field_generated_header_dependencies(field_model: FieldModel) -> Iterator[str]:
    if (
        field_model.message_type is not None
        and not field_model.message_type.is_map_entry
    ):
        yield field_model.message_type.file_name
    if field_model.enum_type is not None:
        yield field_model.enum_type.file_name
    if field_model.map_key is not None:
        yield from _field_generated_header_dependencies(field_model.map_key)
    if field_model.map_value is not None:
        yield from _field_generated_header_dependencies(field_model.map_value)


def _validate_generated_reflection_symbols(
    model: DescriptorModel, options: GeneratorOptions
) -> None:
    reflection_symbols: dict[tuple[str, ...], dict[str, str]] = {}
    type_owners: dict[tuple[str, ...], dict[str, str]] = {}
    constant_owners: dict[tuple[str, ...], dict[str, str]] = {}

    scope_files = _generated_cpp_scope_files(model)
    for file_model in scope_files:
        namespace = tuple(_namespace_parts(file_model, options))
        owners = type_owners.setdefault(namespace, {})
        constants = constant_owners.setdefault(namespace, {})
        for constant in file_model.constants:
            constants[constant.cpp_name] = constant.full_name
        for enum in file_model.enums:
            owners[enum.cpp_name] = enum.full_name
        for message in _walk_generated_messages(file_model.messages):
            if not message.is_map_entry:
                owners[message.cpp_name] = message.full_name

    for file_model in scope_files:
        messages = [
            message
            for message in _walk_generated_messages(file_model.messages)
            if not message.is_map_entry
        ]
        if not messages:
            continue

        namespace = (*_namespace_parts(file_model, options), "protocyte_reflection")
        symbols = reflection_symbols.setdefault(namespace, {})
        for message in messages:
            symbol = _reflection_name(message)
            first = symbols.get(symbol)
            if first is not None:
                raise ProtocyteError(
                    f"{message.full_name}: generated reflection symbol {symbol!r} "
                    f"collides with {first!r}"
                )
            type_owner = type_owners.get(namespace, {}).get(symbol)
            if type_owner is not None:
                raise ProtocyteError(
                    f"{message.full_name}: generated reflection symbol {symbol!r} "
                    f"collides with generated type {type_owner!r}"
                )
            constant_owner = constant_owners.get(namespace, {}).get(symbol)
            if constant_owner is not None:
                raise ProtocyteError(
                    f"{message.full_name}: generated reflection symbol {symbol!r} "
                    f"collides with generated package constant {constant_owner!r}"
                )
            symbols[symbol] = message.full_name

    for reflection_namespace in reflection_symbols:
        namespace = reflection_namespace[:-1]
        owner = type_owners.get(namespace, {}).get("protocyte_reflection")
        if owner is not None:
            raise ProtocyteError(
                f"{owner}: type collides with generated reflection namespace"
            )


def _walk_generated_messages(messages: list[MessageModel]) -> Iterator[MessageModel]:
    for message in messages:
        yield message
        yield from _walk_generated_messages(message.nested_messages)


def _build_message_cpp_name_registry(
    message: MessageModel, options: GeneratorOptions
) -> _CppNameRegistry:
    registry = _CppNameRegistry()
    class_scope = registry.scope(message.full_name)

    class_scope.reserve(
        message.cpp_name,
        "enclosing message injected-class-name",
    )
    class_scope.reserve("Context", "generated context alias")
    class_scope.reserve("ctx_", "generated context storage")
    class_scope.reserve("unknown_fields_", "generated unknown field storage")
    for enum in message.nested_enums:
        alias_name = cpp_identifier(enum.name)
        if alias_name == message.cpp_name:
            raise ProtocyteError(
                f"{message.full_name}.{enum.name}: nested enum alias collides with "
                f"enclosing message injected-class-name {message.cpp_name!r}"
            )
        class_scope.reserve(
            alias_name,
            f"nested enum {enum.name} alias",
            error=f"{message.full_name}.{enum.name}: nested type alias collides with generated API",
        )
    for nested in message.nested_messages:
        if nested.is_map_entry:
            continue
        alias_name = cpp_identifier(nested.name)
        if alias_name == message.cpp_name:
            raise ProtocyteError(
                f"{message.full_name}.{nested.name}: nested message alias collides with "
                f"enclosing message injected-class-name {message.cpp_name!r}"
            )
        class_scope.reserve(
            alias_name,
            f"nested message {nested.name} alias",
            error=f"{message.full_name}.{nested.name}: nested type alias collides with generated API",
        )

    for constant in message.constants:
        class_scope.reserve(
            constant.cpp_name,
            f"constant {constant.name}",
            error=f"{message.full_name}.{constant.name}: constant collides with generated API",
        )

    for oneof in message.oneofs:
        _reserve_oneof_case_enum_cpp_names(registry, class_scope, message, oneof)
    _reserve_field_number_enum_cpp_names(registry, class_scope, message)

    _reserve_message_function_cpp_names(class_scope, message)

    visible_storage = _message_visible_storage_names(message)
    _reserve_message_function_parameter_cpp_names(message, visible_storage)

    for oneof in message.oneofs:
        _reserve_oneof_cpp_names(registry, class_scope, message, oneof, options)
    for item in message.fields:
        _reserve_field_cpp_names(class_scope, message, item)

    message.config_cpp_name = _allocate_internal_cpp_identifier(
        "Config", set(class_scope.names)
    )
    member_template_unavailable = set(class_scope.names)
    member_template_unavailable.add(message.config_cpp_name)
    message.reader_cpp_name = _allocate_internal_cpp_identifier(
        "Reader", member_template_unavailable
    )
    message.writer_cpp_name = _allocate_internal_cpp_identifier(
        "Writer", member_template_unavailable
    )
    message.value_cpp_name = _allocate_internal_cpp_identifier(
        "Value", member_template_unavailable
    )
    message.generic_cpp_name = _allocate_internal_cpp_identifier(
        "T", member_template_unavailable
    )
    for item in message.fields:
        _assign_field_internal_cpp_names(item, message)

    return registry


def _allocate_internal_cpp_identifier(preferred: str, unavailable: set[str]) -> str:
    if preferred not in unavailable:
        return preferred
    base = f"Protocyte{preferred}"
    candidate = base
    suffix = 2
    while candidate in unavailable:
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _assign_field_internal_cpp_names(item: FieldModel, message: MessageModel) -> None:
    item.config_cpp_name = message.config_cpp_name
    item.reader_cpp_name = message.reader_cpp_name
    item.writer_cpp_name = message.writer_cpp_name
    item.value_cpp_name = message.value_cpp_name
    item.generic_cpp_name = message.generic_cpp_name
    if item.map_key is not None:
        _assign_field_internal_cpp_names(item.map_key, message)
    if item.map_value is not None:
        _assign_field_internal_cpp_names(item.map_value, message)


def _reserve_message_function_cpp_names(
    class_scope: _CppNameScope, message: MessageModel
) -> None:
    for name, owner in (
        ("create", "generated create function"),
        ("context", "generated context accessor"),
        ("unknown_fields", "generated unknown field accessor"),
        ("unknown_field_count", "generated unknown field count accessor"),
        ("unknown_field_bytes", "generated unknown field bytes accessor"),
        ("clear_unknown_fields", "generated unknown field clear function"),
        ("mutable_unknown_fields", "generated mutable unknown field accessor"),
        ("copy_from", "generated copy function"),
        ("copy_from_in_place_", "generated in-place copy helper"),
        ("reset_for_reuse_", "generated message reset helper"),
        ("clone", "generated clone function"),
        ("parse", "generated parse function"),
        ("merge_from", "generated merge function"),
        ("merge_field_from_", "generated merge field helper"),
        ("merge_fields_from", "generated merge fields helper"),
        ("serialize", "generated serialize function"),
        ("encoded_size", "generated size function"),
        ("validate", "generated validate function"),
    ):
        _reserve_generated_class_name(class_scope, message, name, owner)
    if message.oneofs:
        _reserve_generated_class_name(
            class_scope, message, "destroy_at_", "generated oneof destroy helper"
        )


def _reserve_generated_class_name(
    class_scope: _CppNameScope, message: MessageModel, name: str, owner: str
) -> None:
    existing = class_scope.owner(name)
    if existing is not None and existing != owner:
        if existing.startswith("constant "):
            constant_name = existing.removeprefix("constant ")
            raise ProtocyteError(
                f"{message.full_name}.{constant_name}: constant collides with generated API"
            )
        if existing.startswith("nested enum ") or existing.startswith(
            "nested message "
        ):
            nested_name = existing.split(" ", 2)[2].removesuffix(" alias")
            raise ProtocyteError(
                f"{message.full_name}.{nested_name}: nested type alias collides with generated API"
            )
        if existing.startswith("field "):
            field_name = existing.split(" ", 2)[1]
            raise ProtocyteError(
                f"{message.full_name}.{field_name}: field collides with generated API"
            )
        if existing.startswith("oneof "):
            oneof_name = existing.split(" ", 2)[1]
            raise ProtocyteError(
                f"{message.full_name}.{oneof_name}: oneof collides with generated API"
            )
    class_scope.reserve(name, owner)


def _reserve_message_function_parameter_cpp_names(
    message: MessageModel, visible_storage: set[str]
) -> None:
    def function(name: str, *parameters: str) -> None:
        scope = _CppFunctionScope(f"{message.full_name}::{name}", visible_storage)
        for parameter in parameters:
            scope.parameter(parameter)

    function(message.cpp_name, "ctx")
    function("create", "ctx")
    if message.oneofs:
        function(f"{message.cpp_name} move constructor", "other")
        function("operator= move", "other")
        function("destroy_at_", "value")
    function("copy_from", "source")
    function("copy_from with staging", "source", "staging_message")
    function("copy_from_in_place_", "source")
    function("reset_for_reuse_", "value", "ctx")
    function("clone with output", "output")
    function("parse", "ctx", "reader")
    function("parse with output", "reader", "output")
    function("merge_from", "reader")
    if message.fields:
        function("serialize", "writer")
    function("serialize span overload", "output")

    for item in message.fields:
        _reserve_field_function_parameter_cpp_names(message, item, visible_storage)


def _reserve_field_function_parameter_cpp_names(
    message: MessageModel, item: FieldModel, visible_storage: set[str]
) -> None:
    def function(name: str, *parameters: str) -> None:
        scope = _CppFunctionScope(f"{message.full_name}::{name}", visible_storage)
        for parameter in parameters:
            scope.parameter(parameter)

    if item.repeated and item.kind != "map":
        return
    if item.kind == "map":
        return
    if item.kind == "message":
        return
    if item.fixed_bytes:
        function(f"resize_{item.cpp_name}_for_overwrite", "size")
        function(f"set_{item.cpp_name}", "value")
        return
    if item.kind == "bytes" and item.array_enabled:
        function(f"resize_{item.cpp_name}", "size")
        function(f"resize_{item.cpp_name}_for_overwrite", "size")
        function(f"set_{item.cpp_name}", "value")
        return
    if item.kind in {"string", "bytes"}:
        function(f"set_{item.cpp_name}", "value")
        return
    if item.kind == "enum":
        function(f"set_{item.cpp_name}_raw", "value")
        function(f"set_{item.cpp_name}", "value")
        return
    function(f"set_{item.cpp_name}", "value")


def _reserve_oneof_case_enum_cpp_names(
    registry: _CppNameRegistry,
    class_scope: _CppNameScope,
    message: MessageModel,
    oneof: OneofModel,
) -> None:
    class_scope.reserve(
        _oneof_case_type(oneof.name),
        f"oneof {oneof.name} case type",
        error=f"{message.full_name}.{oneof.name}: oneof collides with generated API",
    )
    enum_scope = registry.scope(f"{message.full_name}::{_oneof_case_type(oneof.name)}")
    enum_scope.reserve("none", f"oneof {oneof.name} empty case")
    for item in oneof.fields:
        enum_scope.reserve(
            item.cpp_name,
            f"oneof field {item.name} case",
            error=f"{message.full_name}.{item.name}: field collides with generated API",
        )


def _reserve_field_number_enum_cpp_names(
    registry: _CppNameRegistry, class_scope: _CppNameScope, message: MessageModel
) -> None:
    if not message.fields:
        return
    class_scope.reserve("FieldNumber", "generated field number enum")
    enum_scope = registry.scope(f"{message.full_name}::FieldNumber")
    for item in sorted(message.fields, key=lambda field: field.number):
        enum_scope.reserve(
            _field_number_name(item),
            f"field {item.name} number",
            error=f"{message.full_name}.{item.name}: field collides with generated API",
        )


def _reserve_oneof_cpp_names(
    registry: _CppNameRegistry,
    class_scope: _CppNameScope,
    message: MessageModel,
    oneof: OneofModel,
    options: GeneratorOptions,
) -> None:
    del options
    lower = cpp_derivable_identifier(oneof.name)
    if class_scope.owner(lower) is not None:
        raise ProtocyteError(
            f"{message.full_name}.{oneof.name}: oneof collides with generated API"
        )
    for name, owner in (
        (f"{lower}_case", f"oneof {oneof.name} case accessor"),
        (f"clear_{lower}", f"oneof {oneof.name} clear function"),
        (_oneof_case_member(oneof.name), f"oneof {oneof.name} case storage"),
        (_oneof_storage_type(oneof), f"oneof {oneof.name} storage type"),
        (_oneof_storage_member(oneof.name), f"oneof {oneof.name} storage"),
    ):
        class_scope.reserve(
            name,
            owner,
            error=f"{message.full_name}.{oneof.name}: oneof collides with generated API",
        )

    union_scope = registry.scope(f"{message.full_name}::{_oneof_storage_type(oneof)}")
    for item in oneof.fields:
        union_scope.reserve(
            _oneof_member_name(item),
            f"oneof field {item.name} storage",
            error=f"{message.full_name}.{item.name}: field collides with generated API",
        )


def _reserve_field_cpp_names(
    class_scope: _CppNameScope, message: MessageModel, item: FieldModel
) -> None:
    if item.cpp_name == message.cpp_name:
        raise ProtocyteError(
            f"{message.full_name}.{item.name}: field accessor collides with enclosing "
            f"message injected-class-name {message.cpp_name!r}"
        )
    for name, owner in _field_class_cpp_name_items(item):
        class_scope.reserve(
            name,
            owner,
            error=f"{message.full_name}.{item.name}: field collides with generated API",
        )


def _field_class_cpp_name_items(item: FieldModel) -> Iterator[tuple[str, str]]:
    cpp_name = item.cpp_name
    yield cpp_name, f"field {item.name} accessor"
    if item.oneof_name is not None:
        yield f"has_{cpp_name}", f"oneof field {item.name} presence accessor"
        if item.kind == "message":
            yield f"ensure_{cpp_name}", f"oneof field {item.name} ensure accessor"
        elif item.kind == "enum":
            yield f"{cpp_name}_raw", f"oneof field {item.name} raw accessor"
            yield f"set_{cpp_name}_raw", f"oneof field {item.name} raw setter"
            yield f"set_{cpp_name}", f"oneof field {item.name} setter"
        else:
            yield f"set_{cpp_name}", f"oneof field {item.name} setter"
        return

    yield _member(item), f"field {item.name} storage"
    if _has_presence_flag(item):
        yield f"has_{cpp_name}_", f"field {item.name} presence storage"

    yield f"clear_{cpp_name}", f"field {item.name} clear function"
    if item.repeated and item.kind != "map":
        yield f"mutable_{cpp_name}", f"field {item.name} mutable accessor"
    elif item.kind == "map":
        yield f"mutable_{cpp_name}", f"field {item.name} mutable accessor"
    elif item.kind == "message":
        yield f"has_{cpp_name}", f"field {item.name} presence accessor"
        yield f"ensure_{cpp_name}", f"field {item.name} ensure accessor"
    elif item.fixed_bytes:
        yield f"has_{cpp_name}", f"field {item.name} presence accessor"
        yield f"mutable_{cpp_name}", f"field {item.name} mutable accessor"
        yield (
            f"resize_{cpp_name}_for_overwrite",
            f"field {item.name} overwrite resize function",
        )
        yield f"set_{cpp_name}", f"field {item.name} setter"
    elif item.kind == "bytes" and item.array_enabled:
        yield f"{cpp_name}_size", f"field {item.name} size accessor"
        yield f"{cpp_name}_max_size", f"field {item.name} max size accessor"
        yield f"resize_{cpp_name}", f"field {item.name} resize function"
        yield (
            f"resize_{cpp_name}_for_overwrite",
            f"field {item.name} overwrite resize function",
        )
        yield f"mutable_{cpp_name}", f"field {item.name} mutable accessor"
        yield f"set_{cpp_name}", f"field {item.name} setter"
        if item.proto3_optional:
            yield f"has_{cpp_name}", f"field {item.name} presence accessor"
    elif item.kind in {"string", "bytes"}:
        yield f"mutable_{cpp_name}", f"field {item.name} mutable accessor"
        yield f"set_{cpp_name}", f"field {item.name} setter"
        if item.proto3_optional:
            yield f"has_{cpp_name}", f"field {item.name} presence accessor"
    elif item.kind == "enum":
        yield f"{cpp_name}_raw", f"field {item.name} raw accessor"
        yield f"set_{cpp_name}_raw", f"field {item.name} raw setter"
        yield f"set_{cpp_name}", f"field {item.name} setter"
        if item.proto3_optional:
            yield f"has_{cpp_name}", f"field {item.name} presence accessor"
    else:
        yield f"set_{cpp_name}", f"field {item.name} setter"
        if item.proto3_optional:
            yield f"has_{cpp_name}", f"field {item.name} presence accessor"


def _message_visible_storage_names(message: MessageModel) -> set[str]:
    names = {"ctx_", "unknown_fields_"}
    for oneof in message.oneofs:
        names.add(_oneof_case_member(oneof.name))
        names.add(_oneof_storage_member(oneof.name))
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        names.add(_member(item))
        if _has_presence_flag(item):
            names.add(f"has_{item.cpp_name}_")
    return names


def _reflection_name(message: MessageModel) -> str:
    return _cpp_suffix_identifier(message.cpp_name, "fields")


def _reflection_label(item: FieldModel) -> str:
    if item.label == FieldDescriptorProto.LABEL_REQUIRED:
        return "required"
    if item.label == FieldDescriptorProto.LABEL_REPEATED:
        return "repeated"
    return "optional"


def _emit_reflection_api_macro(w: CppWriter, macro: str) -> None:
    w.line(f"#if !defined({macro})")
    w.line("#if defined(_WIN32)")
    w.line(f"#if defined({macro}_EXPORTS)")
    w.line(f"#define {macro} __declspec(dllexport)")
    w.line("#else")
    w.line(f"#define {macro} __declspec(dllimport)")
    w.line("#endif")
    w.line("#else")
    w.line(f"#define {macro}")
    w.line("#endif")
    w.line("#endif")
    w.line()


def _emit_reflection_declarations(
    w: CppWriter, file_model: FileModel, options: GeneratorOptions
) -> None:
    messages = _ordered_messages(file_model)
    if not messages:
        return
    w.line("#if PROTOCYTE_ENABLE_REFLECTION")
    if options.reflection_api_macro is not None:
        _emit_reflection_api_macro(w, options.reflection_api_macro)
    w.line("namespace protocyte_reflection {")
    with w.indent():
        for message in messages:
            api_macro = (
                f"{options.reflection_api_macro} "
                if options.reflection_api_macro is not None
                else ""
            )
            w.line(
                f"extern {api_macro}const "
                f"::std::array<::protocyte::ReflectionFieldInfo, {len(message.fields)}> "
                f"{_reflection_name(message)};"
            )
    w.line("}  // namespace protocyte_reflection")
    w.line("#endif  // PROTOCYTE_ENABLE_REFLECTION")
    w.line()


def generate_header(
    file_model: FileModel,
    options: GeneratorOptions,
    *,
    output_budget: _OutputBudget | None = None,
) -> str:
    w = CppWriter(output_budget=output_budget)
    guard = _include_guard(file_model.name)
    w.line("#pragma once")
    w.line()
    w.line(f"#ifndef {guard}")
    w.line(f"#define {guard}")
    w.line()
    w.line(f"#include <{options.runtime_prefix}/runtime.hpp>")
    w.line()
    w.line("#if PROTOCYTE_ENABLE_REFLECTION")
    w.line("#include <array>")
    w.line("#endif")
    extra_includes: list[str] = []
    if _file_uses_numeric_limits(file_model):
        extra_includes.append("#include <limits>")
    for dependency in sorted(file_model.dependencies):
        extra_includes.append(f'#include "{_include_path(dependency, options)}"')
    if extra_includes:
        w.line()
        for include in extra_includes:
            w.line(include)
    w.line()
    _open_namespace(w, _namespace_parts(file_model, options))
    _emit_reflection_declarations(w, file_model, options)
    _emit_enums(w, file_model, options)
    _emit_file_constants(w, file_model)
    ordered_messages = _ordered_messages(file_model)
    for message in ordered_messages:
        w.line(
            f"template <typename {message.config_cpp_name} = ::protocyte::DefaultConfig>"
        )
        deprecated = " [[deprecated]]" if message.deprecated else ""
        w.line(f"struct{deprecated} {message.cpp_name};")
    w.line()
    for index, message in enumerate(ordered_messages):
        _emit_message(w, message, options)
        if index + 1 != len(ordered_messages):
            w.line()
    _close_namespace(w, _namespace_parts(file_model, options))
    w.line()
    w.line(f"#endif  // {guard}")
    return w.render()


def generate_source(
    file_model: FileModel,
    options: GeneratorOptions,
    *,
    output_budget: _OutputBudget | None = None,
) -> str:
    w = CppWriter(output_budget=output_budget)
    w.line(f'#include "{_header_name(file_model.name, options)}"')
    w.line()
    w.line("#if PROTOCYTE_ENABLE_REFLECTION")
    _open_namespace(w, _namespace_parts(file_model, options))
    w.line("namespace protocyte_reflection {")
    with w.indent():
        for message in _ordered_messages(file_model):
            reflection_name = _reflection_name(message)
            api_macro = (
                f"{options.reflection_api_macro} "
                if options.reflection_api_macro is not None
                else ""
            )
            w.line(
                f"extern {api_macro}const "
                f"::std::array<::protocyte::ReflectionFieldInfo, {len(message.fields)}> "
                f"{reflection_name} {{{{"
            )
            with w.indent():
                for item in message.fields:
                    w.line(
                        f"{{{_cpp_string_literal(item.name.encode('utf-8'))}, {item.number}u, "
                        f'"{item.kind}", '
                        f"::protocyte::ReflectionFieldLabel::{_reflection_label(item)}, "
                        f"{_cpp_bool(item.has_explicit_presence)}, {_cpp_bool(item.packed)}}},"
                    )
            w.line("}};")
            w.line()
    w.line("}  // namespace protocyte_reflection")
    _close_namespace(w, _namespace_parts(file_model, options))
    w.line("#endif  // PROTOCYTE_ENABLE_REFLECTION")
    return w.render()


def _emit_enums(w: CppWriter, file_model: FileModel, options: GeneratorOptions) -> None:
    enums = list(file_model.enums)
    for message in _walk_messages(file_model.messages):
        enums.extend(message.nested_enums)
    for enum in enums:
        _emit_documentation(w, enum.documentation, options)
        deprecated = " [[deprecated]]" if enum.deprecated else ""
        w.line(f"enum struct{deprecated} {enum.cpp_name} : ::protocyte::i32 {{")
        with w.indent():
            for value in enum.values:
                _emit_documentation(w, value.documentation, options)
                deprecated = " [[deprecated]]" if value.deprecated else ""
                w.line(f"{value.cpp_name}{deprecated} = {value.number},")
        w.line("};")
        w.line()


def _message_uses_deprecated_declarations(message: MessageModel) -> bool:
    return (
        message.deprecated
        or any(enum.deprecated for enum in message.nested_enums)
        or any(nested.deprecated for nested in message.nested_messages)
        or any(
            item.deprecated or _field_uses_deprecated_type(item)
            for item in message.fields
        )
    )


def _field_uses_deprecated_type(item: FieldModel) -> bool:
    return (
        (item.enum_type is not None and item.enum_type.deprecated)
        or (item.message_type is not None and item.message_type.deprecated)
        or (item.map_key is not None and _field_uses_deprecated_type(item.map_key))
        or (item.map_value is not None and _field_uses_deprecated_type(item.map_value))
    )


def _emit_constants(w: CppWriter, message: MessageModel) -> None:
    if not message.constants:
        return
    for constant in message.constants:
        w.line(
            f"static constexpr {constant.cpp_type} {constant.cpp_name} {{{constant.cpp_value}}};"
        )
    w.line()


def _emit_file_constants(w: CppWriter, file_model: FileModel) -> None:
    if not file_model.constants:
        return
    for constant in file_model.constants:
        w.line(
            f"inline constexpr {constant.cpp_type} {constant.cpp_name} {{{constant.cpp_value}}};"
        )
    w.line()


def _emit_message(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    suppress_internal_deprecation = _message_uses_deprecated_declarations(message)
    if suppress_internal_deprecation:
        _emit_deprecated_diagnostic_push(w)
    _emit_documentation(w, message.documentation, options)
    config_cpp_name = message.config_cpp_name
    w.line(f"template <typename {config_cpp_name}>")
    deprecated = " [[deprecated]]" if message.deprecated else ""
    w.line(f"struct{deprecated} {message.cpp_name} {{")
    with w.indent():
        w.line(f"using Context = typename {config_cpp_name}::Context;")
        for enum in message.nested_enums:
            _emit_documentation(w, enum.documentation, options)
            alias_deprecated = " [[deprecated]]" if enum.deprecated else ""
            w.line(
                f"using {cpp_identifier(enum.name)}{alias_deprecated} = {enum.cpp_name};"
            )
        for nested in message.nested_messages:
            if not nested.is_map_entry:
                _emit_documentation(w, nested.documentation, options)
                alias_name = cpp_identifier(nested.name)
                nested_config_name = _allocate_internal_cpp_identifier(
                    "NestedConfig", {alias_name}
                )
                w.line(f"template <typename {nested_config_name} = {config_cpp_name}>")
                alias_deprecated = " [[deprecated]]" if nested.deprecated else ""
                w.line(
                    f"using {alias_name}{alias_deprecated} = "
                    f"{nested.cpp_name}<{nested_config_name}>;"
                )
        if message.nested_enums or message.nested_messages:
            w.line()
        _emit_constants(w, message)
        _emit_oneof_case_enums(w, message, options)
        _emit_field_number_enum(w, message, options)
        w.line(f"explicit {message.cpp_name}(Context& ctx) noexcept")
        _emit_constructor_initializers(w, message)
        _emit_constructor_body(w, message)
        w.line()
        w.line(f"static {message.cpp_name} create(Context& ctx) noexcept {{")
        with w.indent():
            w.line(f"return {message.cpp_name}{{ctx}};")
        w.line("}")
        w.line("Context* context() const noexcept { return ctx_; }")
        _emit_special_members(w, message, options)
        w.line(f"{message.cpp_name}(const {message.cpp_name}&) = delete;")
        w.line(f"{message.cpp_name}& operator=(const {message.cpp_name}&) = delete;")
        w.line()
        if message.oneofs:
            generic_cpp_name = message.generic_cpp_name
            w.line(f"template <typename {generic_cpp_name}>")
            w.line(
                f"static void destroy_at_({generic_cpp_name}* value) noexcept {{ value->~{generic_cpp_name}(); }}"
            )
            w.line()
        _emit_clone_api(w, message, options)
        w.line(
            "::protocyte::UnknownFieldRange unknown_fields() const noexcept { return ::protocyte::UnknownFieldRange{unknown_fields_.bytes(), ctx_->limits.max_recursion_depth}; }"
        )
        w.line(
            "::protocyte::usize unknown_field_count() const noexcept { return unknown_fields().field_count(); }"
        )
        w.line(
            "::protocyte::Span<const ::protocyte::u8> unknown_field_bytes() const noexcept { return unknown_fields_.bytes(); }"
        )
        w.line("void clear_unknown_fields() noexcept { unknown_fields_.clear(); }")
        w.line(
            f"::protocyte::MutableUnknownFieldSet<{config_cpp_name}> mutable_unknown_fields() noexcept"
        )
        w.line(
            f"    requires(::protocyte::preserve_unknown_fields_v<{config_cpp_name}>)"
        )
        w.line("{")
        with w.indent():
            w.line(
                f"return ::protocyte::MutableUnknownFieldSet<{config_cpp_name}>{{*ctx_, unknown_fields_}};"
            )
        w.line("}")
        w.line()
        for oneof in message.oneofs:
            lower = cpp_derivable_identifier(oneof.name)
            _emit_documentation(w, oneof.documentation, options)
            w.line(
                f"constexpr {oneof.cpp_name}Case {lower}_case() const noexcept {{ return {lower}_case_; }}"
            )
            _emit_documentation(w, oneof.documentation, options)
            w.line(f"void clear_{lower}() noexcept {{")
            with w.indent():
                w.line(f"switch ({lower}_case_) {{")
                with w.indent():
                    for item in oneof.fields:
                        w.line(f"case {oneof.cpp_name}Case::{item.cpp_name}: {{")
                        with w.indent():
                            _emit_destroy_oneof_member(w, item)
                            w.line("break;")
                        w.line("}")
                    w.line(f"case {oneof.cpp_name}Case::none:")
                    w.line("default: {")
                    with w.indent():
                        w.line("break;")
                    w.line("}")
                w.line("}")
                w.line(f"{lower}_case_ = {oneof.cpp_name}Case::none;")
            w.line("}")
            w.line()
        for item in message.fields:
            _emit_accessors(w, item, options)
            w.line()
        _emit_wire_api(w, message, options)
        w.line("protected:")
        with w.indent():
            w.line("Context* ctx_;")
            w.line(
                f"PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<{config_cpp_name}> unknown_fields_;"
            )
            oneofs_by_name = {oneof.name: oneof for oneof in message.oneofs}
            emitted_oneofs: set[str] = set()
            for item in message.fields:
                if item.oneof_name is not None:
                    if item.oneof_name in emitted_oneofs:
                        continue
                    oneof = oneofs_by_name[item.oneof_name]
                    w.line(
                        f"{oneof.cpp_name}Case {_oneof_case_member(oneof.name)} {{{oneof.cpp_name}Case::none}};"
                    )
                    _emit_oneof_storage(w, oneof, options)
                    emitted_oneofs.add(item.oneof_name)
                    continue
                _emit_member(w, item, options)
    w.line("};")
    if suppress_internal_deprecation:
        _emit_deprecated_diagnostic_pop(w)


def _emit_deprecated_diagnostic_push(w: CppWriter) -> None:
    w.line("#if defined(__clang__)")
    w.line("#pragma clang diagnostic push")
    w.line('#pragma clang diagnostic ignored "-Wdeprecated-declarations"')
    w.line("#elif defined(__GNUC__)")
    w.line("#pragma GCC diagnostic push")
    w.line('#pragma GCC diagnostic ignored "-Wdeprecated-declarations"')
    w.line("#elif defined(_MSC_VER)")
    w.line("#pragma warning(push)")
    w.line("#pragma warning(disable : 4996)")
    w.line("#endif")


def _emit_deprecated_diagnostic_pop(w: CppWriter) -> None:
    w.line("#if defined(__clang__)")
    w.line("#pragma clang diagnostic pop")
    w.line("#elif defined(__GNUC__)")
    w.line("#pragma GCC diagnostic pop")
    w.line("#elif defined(_MSC_VER)")
    w.line("#pragma warning(pop)")
    w.line("#endif")


def _emit_oneof_case_enums(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    for oneof in message.oneofs:
        _emit_documentation(w, oneof.documentation, options)
        w.line(f"enum struct {oneof.cpp_name}Case : ::protocyte::u32 {{")
        with w.indent():
            w.line("none = 0u,")
            for item in oneof.fields:
                _emit_documentation(w, item.documentation, options)
                w.line(f"{item.cpp_name} = {item.number}u,")
        w.line("};")
        w.line()


def _emit_field_number_enum(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    if not message.fields:
        return
    w.line("enum struct FieldNumber : ::protocyte::u32 {")
    with w.indent():
        for item in sorted(message.fields, key=lambda field: field.number):
            _emit_documentation(w, item.documentation, options)
            w.line(f"{_field_number_name(item)} = {item.number}u,")
    w.line("};")
    w.line()


def _emit_constructor_initializers(w: CppWriter, message: MessageModel) -> None:
    initializers = ["ctx_{&ctx}", "unknown_fields_{&ctx}"]
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        member = _member(item)
        if item.repeated_array:
            initializers.append(f"{member}{{&ctx}}")
            continue
        if item.array_enabled:
            continue
        if item.repeated and item.kind != "map":
            initializers.append(f"{member}{{&ctx}}")
        elif item.kind in {"string", "bytes", "map"}:
            initializers.append(f"{member}{{&ctx}}")
        elif item.kind == "message" and item.recursive_box:
            initializers.append(f"{member}{{&ctx}}")
    with w.indent():
        for index, initializer in enumerate(initializers):
            prefix = ": " if index == 0 else ", "
            w.line(f"{prefix}{initializer}")


def _emit_constructor_body(w: CppWriter, message: MessageModel) -> None:
    del message
    w.line("{}")


def _emit_special_members(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    if not message.oneofs:
        w.line(f"{message.cpp_name}({message.cpp_name}&&) noexcept = default;")
        w.line(
            f"{message.cpp_name}& operator=({message.cpp_name}&&) noexcept = default;"
        )
        return
    w.line(f"{message.cpp_name}({message.cpp_name}&& other) noexcept")
    _emit_move_constructor_initializers(w, message)
    w.line("{")
    with w.indent():
        _emit_move_state_setup(w, message)
        for oneof in message.oneofs:
            _emit_move_oneof_from_other(w, oneof, options, source="other")
    w.line("}")
    w.line(f"{message.cpp_name}& operator=({message.cpp_name}&& other) noexcept {{")
    with w.indent():
        w.line("if (this == &other) { return *this; }")
        for oneof in message.oneofs:
            w.line(f"clear_{cpp_derivable_identifier(oneof.name)}();")
        w.line("ctx_ = other.ctx_;")
        w.line("unknown_fields_ = ::protocyte::move(other.unknown_fields_);")
        for item in message.fields:
            if item.oneof_name is not None:
                continue
            _emit_move_assignment_for_field(w, item)
        for oneof in message.oneofs:
            _emit_move_oneof_from_other(w, oneof, options, source="other")
        w.line("return *this;")
    w.line("}")
    w.line(f"~{message.cpp_name}() noexcept {{")
    with w.indent():
        for oneof in message.oneofs:
            w.line(f"clear_{cpp_derivable_identifier(oneof.name)}();")
    w.line("}")


def _emit_move_constructor_initializers(w: CppWriter, message: MessageModel) -> None:
    initializers = [
        "ctx_{other.ctx_}",
        "unknown_fields_{::protocyte::move(other.unknown_fields_)}",
    ]
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        member = _member(item)
        if (
            item.repeated
            or item.kind == "map"
            or item.kind in {"string", "bytes", "message"}
        ):
            initializers.append(f"{member}{{::protocyte::move(other.{member})}}")
        else:
            initializers.append(f"{member}{{other.{member}}}")
    with w.indent():
        for index, initializer in enumerate(initializers):
            prefix = ": " if index == 0 else ", "
            w.line(f"{prefix}{initializer}")


def _emit_move_state_setup(w: CppWriter, message: MessageModel) -> None:
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        if _has_presence_flag(item):
            w.line(f"has_{item.cpp_name}_ = other.has_{item.cpp_name}_;")


def _emit_move_assignment_for_field(w: CppWriter, item: FieldModel) -> None:
    member = _member(item)
    if (
        item.repeated
        or item.kind == "map"
        or item.kind in {"string", "bytes", "message"}
    ):
        w.line(f"{member} = ::protocyte::move(other.{member});")
    else:
        w.line(f"{member} = other.{member};")
    if _has_presence_flag(item):
        w.line(f"has_{item.cpp_name}_ = other.has_{item.cpp_name}_;")


def _emit_move_oneof_from_other(
    w: CppWriter, oneof: OneofModel, options: GeneratorOptions, *, source: str
) -> None:
    lower = cpp_derivable_identifier(oneof.name)
    case_type = oneof.cpp_name + "Case"
    w.line(f"switch ({source}.{lower}_case_) {{")
    with w.indent():
        for item in oneof.fields:
            storage_type = _storage_type(item, options)
            value = (
                f"::protocyte::move({source}.{_member(item)})"
                if item.kind in {"string", "bytes", "message"}
                else f"{source}.{_member(item)}"
            )
            w.line(f"case {case_type}::{item.cpp_name}: {{")
            with w.indent():
                w.line(f"new (&{_member(item)}) {storage_type} {{{value}}};")
                w.line(f"{lower}_case_ = {case_type}::{item.cpp_name};")
                w.line("break;")
            w.line("}")
        w.line(f"case {case_type}::none:")
        w.line("default: {")
        with w.indent():
            w.line("break;")
        w.line("}")
    w.line("}")
    w.line(f"{source}.clear_{lower}();")


def _emit_clone_api(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    non_oneof_fields = [item for item in message.fields if item.oneof_name is None]
    map_only = bool(non_oneof_fields) and all(
        item.kind == "map" for item in non_oneof_fields
    )
    w.line(
        f"::protocyte::Status copy_from(const {message.cpp_name}& source) noexcept {{"
    )
    with w.indent():
        w.line("if (this == &source) { return {}; }")
        w.line(f"{message.cpp_name} staging_message{{*ctx_}};")
        w.line("return copy_from(source, staging_message);")
    w.line("}")
    w.line()
    w.line(
        f"::protocyte::Status copy_from(const {message.cpp_name}& source, {message.cpp_name}& staging_message) noexcept {{"
    )
    with w.indent():
        w.line("if (this == &source) { return {}; }")
        w.line("if (this == &staging_message || &source == &staging_message) {")
        with w.indent():
            w.line(
                "return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {});"
            )
        w.line("}")
        w.line("reset_for_reuse_(staging_message, *ctx_);")
        w.line(
            "if (const auto st = staging_message.copy_from_in_place_(source); !st) {"
        )
        with w.indent():
            w.line("reset_for_reuse_(staging_message, *ctx_);")
            w.line("return st;")
        w.line("}")
        w.line("*this = ::protocyte::move(staging_message);")
        w.line("return {};")
    w.line("}")
    w.line()
    w.line(f"::protocyte::Result<{message.cpp_name}> clone() const noexcept {{")
    with w.indent():
        w.line(f"auto output = {message.cpp_name}::create(*ctx_);")
        w.line(
            "if (const auto st = clone(output); !st) { return ::protocyte::unexpected(st.error()); }"
        )
        w.line("return ::protocyte::move(output);")
    w.line("}")
    w.line()
    w.line(f"::protocyte::Status clone({message.cpp_name}& output) const noexcept {{")
    with w.indent():
        w.line("if (this == &output) { return {}; }")
        w.line("Context* const output_ctx = output.context();")
        w.line("reset_for_reuse_(output, *output_ctx);")
        w.line("if (const auto st = output.copy_from_in_place_(*this); !st) {")
        with w.indent():
            w.line("reset_for_reuse_(output, *output_ctx);")
            w.line("return st;")
        w.line("}")
        w.line("return {};")
    w.line("}")
    w.line()
    w.line("protected:")
    w.line(
        f"static void reset_for_reuse_({message.cpp_name}& value, Context& ctx) noexcept {{"
    )
    with w.indent():
        w.line(f"value.~{message.cpp_name}();")
        w.line(f"new (&value) {message.cpp_name}{{ctx}};")
    w.line("}")
    w.line()
    in_place_source = "source"
    w.line(
        f"::protocyte::Status copy_from_in_place_(const {message.cpp_name}& {in_place_source}) noexcept {{"
    )
    w.push()
    if map_only:
        w.line("const auto& map_source = source;")
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        if item.fixed_bytes:
            w.line(f"if (source.has_{item.cpp_name}()) {{")
            w.push()
            w.line(
                f"if (const auto st = set_{item.cpp_name}(source.{item.cpp_name}()); !st) {{ return st; }}"
            )
            w.pop()
            w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            continue
        if item.kind == "map":
            _emit_copy_map_field(
                w, item, options, source="map_source" if map_only else "source"
            )
            continue
        if item.repeated_array:
            _emit_copy_repeated_field(w, item, options)
            continue
        if item.repeated:
            _emit_copy_repeated_field(w, item, options)
            continue
        if item.kind in {"string", "bytes"}:
            if _has_presence_flag(item):
                w.line(f"if (source.has_{item.cpp_name}()) {{")
                w.push()
                w.line(
                    f"if (const auto st = set_{item.cpp_name}(source.{item.cpp_name}()); !st) {{ return st; }}"
                )
                w.pop()
                w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            else:
                w.line(
                    f"if (const auto st = set_{item.cpp_name}(source.{item.cpp_name}()); !st) {{ return st; }}"
                )
        elif item.kind == "message":
            w.line(f"if (source.has_{item.cpp_name}()) {{")
            w.push()
            _emit_copy_message_from_pointer(w, item, f"source.{item.cpp_name}()")
            w.pop()
            w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
        elif item.kind == "enum":
            if _has_presence_flag(item):
                w.line(f"if (source.has_{item.cpp_name}()) {{")
                w.push()
                w.line(
                    f"if (const auto st = set_{item.cpp_name}_raw(source.{item.cpp_name}_raw()); !st) {{ return st; }}"
                )
                w.pop()
                w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            else:
                w.line(
                    f"if (const auto st = set_{item.cpp_name}_raw(source.{item.cpp_name}_raw()); !st) {{ return st; }}"
                )
        elif not item.repeated and item.kind != "map":
            if _has_presence_flag(item):
                w.line(f"if (source.has_{item.cpp_name}()) {{")
                w.push()
                w.line(f"set_{item.cpp_name}(source.{item.cpp_name}());")
                w.pop()
                w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            else:
                w.line(f"set_{item.cpp_name}(source.{item.cpp_name}());")
    for oneof in message.oneofs:
        _emit_copy_oneof_from_other(w, oneof, options, source="source")
    w.line(
        f"if constexpr (::protocyte::preserve_unknown_fields_v<{message.config_cpp_name}>) {{"
    )
    with w.indent():
        w.line(
            "if (const auto st = unknown_fields_.copy_from(source.unknown_fields_, ctx_->limits.max_unknown_field_bytes); !st) { return st; }"
        )
    w.line("}")
    w.line("return {};")
    w.pop()
    w.line("}")
    w.line()
    w.line("public:")
    w.line()


def _emit_copy_repeated_field(
    w: CppWriter, item: FieldModel, options: GeneratorOptions
) -> None:
    del options
    source = f"source.{item.cpp_name}()"
    w.line(
        f"if (const auto st = mutable_{item.cpp_name}().copy_from({source}); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
    )


def _emit_copy_map_field(
    w: CppWriter, item: FieldModel, options: GeneratorOptions, *, source: str = "other"
) -> None:
    del options
    w.line(
        f"if (const auto st = mutable_{item.cpp_name}().copy_from({source}.{item.cpp_name}()); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
    )


def _emit_copy_message_from_pointer(
    w: CppWriter, item: FieldModel, source_ptr: str
) -> None:
    result_name = f"ensured_{item.cpp_name}"
    w.line(f"const auto {result_name} = ensure_{item.cpp_name}();")
    w.line(
        f"if (!{result_name}) {{ return ::protocyte::with_field({result_name}.status(), {_field_number_u32(item)}); }}"
    )
    w.line(f"if (const auto st = {result_name}->copy_from(*{source_ptr}); !st) {{")
    w.push()
    w.line(f"return ::protocyte::with_field(st, {_field_number_u32(item)});")
    w.pop()
    w.line("}")


def _emit_copy_oneof_from_other(
    w: CppWriter, oneof: OneofModel, options: GeneratorOptions, *, source: str
) -> None:
    lower = cpp_derivable_identifier(oneof.name)
    case_type = oneof.cpp_name + "Case"
    case_member = _oneof_case_member(oneof.name)
    w.line(f"switch ({source}.{case_member}) {{")
    w.push()
    for item in oneof.fields:
        w.line(f"case {case_type}::{item.cpp_name}: {{")
        w.push()
        if item.kind in {"string", "bytes"}:
            w.line(
                f"if (const auto st = set_{item.cpp_name}({source}.{item.cpp_name}()); !st) {{ return st; }}"
            )
        elif item.kind == "message":
            _emit_copy_message_from_pointer(w, item, f"{source}.{item.cpp_name}()")
        elif item.kind == "enum":
            w.line(
                f"if (const auto st = set_{item.cpp_name}_raw({source}.{item.cpp_name}_raw()); !st) {{ return st; }}"
            )
        else:
            w.line(f"set_{item.cpp_name}({source}.{item.cpp_name}());")
        w.line("break;")
        w.pop()
        w.line("}")
    w.line(f"case {case_type}::none:")
    w.line("default: {")
    w.push()
    w.line(f"clear_{lower}();")
    w.line("break;")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")


def _emit_byte_range_setter_family(
    w: CppWriter,
    item: FieldModel,
    options: GeneratorOptions,
    emit_body,
) -> None:
    value_cpp_name = item.value_cpp_name

    def emit_setter_start(
        signature: str,
        view_expr: str,
        *,
        requires_expr: str | None = None,
        template_prefix: bool = False,
    ) -> None:
        _emit_documentation(w, item.documentation, options)
        if template_prefix:
            w.line(f"template<class {value_cpp_name}>")
        if item.deprecated:
            w.line("[[deprecated]]")
        w.line(signature)
        if requires_expr is not None:
            w.line(f"    requires({requires_expr})")
        w.line("{")
        w.push()
        w.line(f"const auto view = {view_expr};")
        w.line(
            f"if (!view) {{ return ::protocyte::with_field(view.status(), {_field_number_u32(item)}); }}"
        )
        emit_body()
        w.pop()
        w.line("}")

    byte_source_requires = f"::protocyte::ByteSpanSource<{value_cpp_name}>"
    if item.kind == "string":
        byte_source_requires += f" && !::protocyte::TextSource<{value_cpp_name}>"
    emit_setter_start(
        f"::protocyte::Status set_{item.cpp_name}(const {value_cpp_name} &value) noexcept",
        "::protocyte::byte_span_of(value)",
        requires_expr=byte_source_requires,
        template_prefix=True,
    )
    if item.kind == "string":
        emit_setter_start(
            f"::protocyte::Status set_{item.cpp_name}(const {value_cpp_name} &value) noexcept",
            "::protocyte::text_byte_span_of(value)",
            requires_expr=f"::protocyte::TextSource<{value_cpp_name}>",
            template_prefix=True,
        )


def _emit_accessors(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.oneof_name is not None:
        _emit_oneof_accessors(w, item, options)
        return
    if item.repeated and item.kind != "map":
        typ = _storage_type(item, options)
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"const {typ}& {item.cpp_name}() const noexcept {{ return {_member(item)}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"{typ}& mutable_{item.cpp_name}() noexcept {{ return {_member(item)}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear(); }}")
        return
    if item.kind == "map":
        assert item.map_key is not None and item.map_value is not None
        typ = f"typename {item.config_cpp_name}::template Map<{_field_type(item.map_key, options)}, {_field_type(item.map_value, options)}>"
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"const {typ}& {item.cpp_name}() const noexcept {{ return {_member(item)}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"{typ}& mutable_{item.cpp_name}() noexcept {{ return {_member(item)}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear(); }}")
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"bool has_{item.cpp_name}() const noexcept {{ return {_member(item)}.has_value(); }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"const {typ}* {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)}.operator->() : nullptr; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(f"::protocyte::Result<{typ}&> ensure_{item.cpp_name}() noexcept {{")
        w.push()
        if item.recursive_box:
            w.line(
                f"return ::protocyte::with_field({_member(item)}.ensure(), {_field_number_u32(item)});"
            )
        else:
            w.line(f"if ({_member(item)}.has_value()) {{")
            w.push()
            w.line(f"return *{_member(item)};")
            w.pop()
            w.line("}")
            w.line(f"if (const auto st = {_member(item)}.emplace(*ctx_); !st) {{")
            w.push()
            w.line(
                f"return ::protocyte::unexpected(::protocyte::with_field(st.error(), {_field_number_u32(item)}));"
            )
            w.pop()
            w.line("}")
            w.line(f"return *{_member(item)};")
        w.pop()
        w.line("}")
        _emit_field_api_annotations(w, item, options)
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.reset(); }}")
        return
    if item.fixed_bytes:
        bound = _array_max_literal(item)
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"bool has_{item.cpp_name}() const noexcept {{ return {_member(item)}.has_value(); }}"
        )
        expr = f"{_member(item)}.view()"
        if item.default_cpp is not None:
            expr = (
                f"has_{item.cpp_name}() ? {_member(item)}.view() : {item.default_cpp}"
            )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Span<const ::protocyte::u8> {item.cpp_name}() const noexcept {{ return {expr}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Span<::protocyte::u8> mutable_{item.cpp_name}() noexcept {{"
        )
        w.push()
        if item.default_cpp is not None:
            w.line(f"if (!has_{item.cpp_name}()) {{")
            w.push()
            w.line(f"const auto default_value = {item.default_cpp};")
            w.line(
                f"if (const auto st = {_member(item)}.assign(default_value); !st) {{ return ::protocyte::Span<::protocyte::u8>{{}}; }}"
            )
            w.pop()
            w.line("}")
        w.line(f"return {_member(item)}.mutable_view();")
        w.pop()
        w.line("}")
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status resize_{item.cpp_name}_for_overwrite(const ::protocyte::usize size) noexcept {{"
        )
        w.push()
        w.line(
            f"return ::protocyte::with_field({_member(item)}.resize_for_overwrite(size), {_field_number_u32(item)});"
        )
        w.pop()
        w.line("}")

        def emit_setter_body() -> None:
            w.line(
                f"return ::protocyte::with_field({_member(item)}.assign(*view), {_field_number_u32(item)});"
            )

        _emit_byte_range_setter_family(w, item, options, emit_setter_body)
        _emit_field_api_annotations(w, item, options)
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear(); }}")
        return
    if item.kind == "bytes" and item.array_enabled:
        bound = _array_max_literal(item)
        expr = f"{_member(item)}.view()"
        if _has_presence_flag(item) and item.default_cpp is not None:
            expr = f"has_{item.cpp_name}_ ? {_member(item)}.view() : {item.default_cpp}"
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Span<const ::protocyte::u8> {item.cpp_name}() const noexcept {{ return {expr}; }}"
        )
        if item.proto3_optional:
            _emit_field_api_annotations(w, item, options)
            w.line(
                f"bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}"
            )
        size_expr = f"{_member(item)}.size()"
        if _has_presence_flag(item) and item.default_cpp is not None:
            size_expr = f"{item.cpp_name}().size()"
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::usize {item.cpp_name}_size() const noexcept {{ return {size_expr}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"static constexpr ::protocyte::usize {item.cpp_name}_max_size() noexcept {{ return {bound}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status resize_{item.cpp_name}(const ::protocyte::usize size) noexcept {{"
        )
        w.push()
        w.line(
            f"if (size > {bound}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, {{}}, {_field_number_u32(item)}); }}"
        )
        if item.array_fixed:
            w.line(
                f"if (size != {bound}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)}); }}"
            )
        if _has_presence_flag(item) and item.default_cpp is not None:
            w.line(f"if (!has_{item.cpp_name}_) {{")
            w.push()
            w.line(f"const auto default_value = {item.default_cpp};")
            w.line(
                f"if (const auto st = {_member(item)}.assign(default_value); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
            )
            w.pop()
            w.line("}")
        w.line(
            f"if (const auto st = {_member(item)}.resize(size); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
        )
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return {};")
        w.pop()
        w.line("}")
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status resize_{item.cpp_name}_for_overwrite(const ::protocyte::usize size) noexcept {{"
        )
        w.push()
        if item.array_fixed:
            w.line(
                f"if (size != {bound}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)}); }}"
            )
        w.line(
            f"if (const auto st = {_member(item)}.resize_for_overwrite(size); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
        )
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return {};")
        w.pop()
        w.line("}")
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Span<::protocyte::u8> mutable_{item.cpp_name}() noexcept {{"
        )
        w.push()
        if item.array_fixed:
            w.line(f"if ({_member(item)}.size() != {bound}) {{")
            w.push()
            w.line(f"static_cast<void>({_member(item)}.resize({bound}));")
            w.pop()
            w.line("}")
        if _has_presence_flag(item) and item.default_cpp is not None:
            w.line(f"if (!has_{item.cpp_name}_) {{")
            w.push()
            w.line(f"const auto default_value = {item.default_cpp};")
            w.line(
                f"if (const auto st = {_member(item)}.assign(default_value); !st) {{ return ::protocyte::Span<::protocyte::u8>{{}}; }}"
            )
            w.pop()
            w.line("}")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line(f"return {_member(item)}.mutable_view();")
        w.pop()
        w.line("}")

        def emit_setter_body() -> None:
            if item.array_fixed:
                w.line(
                    f"if (view->size() != {bound}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)}); }}"
                )
            w.line(
                f"if (const auto st = {_member(item)}.assign(*view); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
            )
            if item.proto3_optional:
                w.line(f"has_{item.cpp_name}_ = true;")
            w.line("return {};")

        _emit_byte_range_setter_family(w, item, options, emit_setter_body)
        _emit_field_api_annotations(w, item, options)
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear();")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    if item.kind in {"string", "bytes"}:
        typ = _field_type(item, options)
        if item.kind == "string":
            expr = f"{_member(item)}.view()"
            if _has_presence_flag(item) and item.default_cpp is not None:
                expr = f"has_{item.cpp_name}_ ? {_member(item)}.view() : {item.default_cpp}"
            _emit_string_view_accessor(w, item, options, expr)
        else:
            expr = f"{_member(item)}.view()"
            if _has_presence_flag(item) and item.default_cpp is not None:
                expr = f"has_{item.cpp_name}_ ? {_member(item)}.view() : {item.default_cpp}"
            _emit_field_api_annotations(w, item, options)
            w.line(
                f"::protocyte::Span<const ::protocyte::u8> {item.cpp_name}() const noexcept {{ return {expr}; }}"
            )
        if item.proto3_optional:
            _emit_field_api_annotations(w, item, options)
            w.line(
                f"bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}"
            )
        _emit_field_api_annotations(w, item, options)
        w.line(f"{typ}& mutable_{item.cpp_name}() noexcept {{")
        w.push()
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line(f"return {_member(item)};")
        w.pop()
        w.line("}")

        def emit_setter_body() -> None:
            w.line(f"{typ} temp{{ctx_}};")
            w.line(
                f"if (const auto st = temp.assign(*view); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
            )
            w.line(f"{_member(item)} = ::protocyte::move(temp);")
            if item.proto3_optional:
                w.line(f"has_{item.cpp_name}_ = true;")
            w.line("return {};")

        _emit_byte_range_setter_family(w, item, options, emit_setter_body)
        _emit_field_api_annotations(w, item, options)
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear();")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    if item.kind == "enum":
        enum_typ = _enum_type(item.enum_type, options)
        raw_expr = _member(item)
        enum_expr = f"static_cast<{enum_typ}>({_member(item)})"
        if _has_presence_flag(item) and item.default_cpp is not None:
            raw_expr = f"has_{item.cpp_name}_ ? {_member(item)} : {_default(item)}"
            enum_expr = f"static_cast<{enum_typ}>({raw_expr})"
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"constexpr ::protocyte::i32 {item.cpp_name}_raw() const noexcept {{ return {raw_expr}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"constexpr {enum_typ} {item.cpp_name}() const noexcept {{ return {enum_expr}; }}"
        )
        if item.proto3_optional:
            _emit_field_api_annotations(w, item, options)
            w.line(
                f"constexpr bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}"
            )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status set_{item.cpp_name}_raw(const ::protocyte::i32 value) noexcept {{"
        )
        w.push()
        _emit_closed_enum_reject(
            w,
            item,
            _closed_enum_invalid_condition(item, "value"),
            field_number=_field_number_u32(item),
        )
        w.line(f"{_member(item)} = value;")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return {};")
        w.pop()
        w.line("}")
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status set_{item.cpp_name}(const {enum_typ} value) noexcept {{ return set_{item.cpp_name}_raw(static_cast<::protocyte::i32>(value)); }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"constexpr void clear_{item.cpp_name}() noexcept {{ {_member(item)} = {{}};"
        )
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    typ = _field_type(item, options)
    value_expr = _member(item)
    if _has_presence_flag(item) and item.default_cpp is not None:
        value_expr = f"has_{item.cpp_name}_ ? {_member(item)} : {_default(item)}"
    _emit_field_api_annotations(w, item, options)
    w.line(
        f"constexpr {typ} {item.cpp_name}() const noexcept {{ return {value_expr}; }}"
    )
    if item.proto3_optional:
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"constexpr bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}"
        )
    _emit_field_api_annotations(w, item, options)
    w.line(
        f"void set_{item.cpp_name}(const {typ} value) noexcept {{ {_member(item)} = value;"
    )
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = true;")
    w.line("}")
    _emit_field_api_annotations(w, item, options)
    w.line(
        f"constexpr void clear_{item.cpp_name}() noexcept {{ {_member(item)} = {{}};"
    )
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = false;")
    w.line("}")


def _emit_oneof_accessors(
    w: CppWriter, item: FieldModel, options: GeneratorOptions
) -> None:
    assert item.oneof_name is not None
    case_type = _oneof_case_type(item.oneof_name)
    case_member = _oneof_case_member(item.oneof_name)
    typ = _field_type(item, options)
    _emit_field_api_annotations(w, item, options)
    w.line(
        f"constexpr bool has_{item.cpp_name}() const noexcept {{ return {case_member} == {case_type}::{item.cpp_name}; }}"
    )
    if item.kind in {"string", "bytes"}:
        if item.kind == "string":
            fallback = item.default_cpp or "::protocyte::StringView{}"
            _emit_string_view_accessor(
                w,
                item,
                options,
                f"has_{item.cpp_name}() ? {_member(item)}.view() : {fallback}",
            )
        else:
            view_type = "::protocyte::Span<const ::protocyte::u8>"
            fallback = item.default_cpp or f"{view_type}{{}}"
            _emit_field_api_annotations(w, item, options)
            w.line(
                f"{view_type} {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)}.view() : {fallback}; }}"
            )

        def emit_setter_body() -> None:
            if item.kind == "bytes" and item.array_enabled:
                w.line(f"{_storage_type(item, options)} temp{{}};")
            else:
                w.line(f"{typ} temp{{ctx_}};")
            w.line(
                f"if (const auto st = temp.assign(*view); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
            )
            w.line(f"clear_{cpp_derivable_identifier(item.oneof_name)}();")
            w.line(
                f"new (&{_member(item)}) {_storage_type(item, options)} {{::protocyte::move(temp)}};"
            )
            w.line(f"{case_member} = {case_type}::{item.cpp_name};")
            w.line("return {};")

        _emit_byte_range_setter_family(w, item, options, emit_setter_body)
        return
    if item.kind == "message":
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"const {typ}* {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() && {_member(item)}.has_value() ? {_member(item)}.operator->() : nullptr; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(f"::protocyte::Result<{typ}&> ensure_{item.cpp_name}() noexcept {{")
        w.push()
        if item.recursive_box:
            w.line(f"if (has_{item.cpp_name}()) {{")
            w.push()
            w.line(f"return *{_member(item)};")
            w.pop()
            w.line("}")
            w.line(f"clear_{cpp_derivable_identifier(item.oneof_name)}();")
            w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{ctx_}};")
            w.line(f"auto ensured = {_member(item)}.ensure();")
            w.line("if (!ensured) {")
            w.push()
            w.line(f"destroy_at_(&{_member(item)});")
            w.line(
                f"return ::protocyte::with_field(ensured, {_field_number_u32(item)});"
            )
            w.pop()
            w.line("}")
            w.line(f"{case_member} = {case_type}::{item.cpp_name};")
            w.line("return ensured;")
            w.pop()
            w.line("}")
            return
        w.line(f"if (!has_{item.cpp_name}()) {{")
        w.push()
        w.line(f"clear_{cpp_derivable_identifier(item.oneof_name)}();")
        w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{}};")
        w.pop()
        w.line("}")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line(f"if ({_member(item)}.has_value()) {{")
        w.push()
        w.line(f"return *{_member(item)};")
        w.pop()
        w.line("}")
        w.line(f"if (const auto st = {_member(item)}.emplace(*ctx_); !st) {{")
        w.push()
        w.line(
            f"return ::protocyte::unexpected(::protocyte::with_field(st.error(), {_field_number_u32(item)}));"
        )
        w.pop()
        w.line("}")
        w.line(f"return *{_member(item)};")
        w.pop()
        w.line("}")
        return
    if item.kind == "enum":
        enum_typ = _enum_type(item.enum_type, options)
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"constexpr ::protocyte::i32 {item.cpp_name}_raw() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)} : {_default(item)}; }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"constexpr {enum_typ} {item.cpp_name}() const noexcept {{ return static_cast<{enum_typ}>({item.cpp_name}_raw()); }}"
        )
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status set_{item.cpp_name}_raw(const ::protocyte::i32 value) noexcept {{"
        )
        w.push()
        _emit_closed_enum_reject(
            w,
            item,
            _closed_enum_invalid_condition(item, "value"),
            field_number=_field_number_u32(item),
        )
        w.line(f"clear_{cpp_derivable_identifier(item.oneof_name)}();")
        w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{value}};")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line("return {};")
        w.pop()
        w.line("}")
        _emit_field_api_annotations(w, item, options)
        w.line(
            f"::protocyte::Status set_{item.cpp_name}(const {enum_typ} value) noexcept {{ return set_{item.cpp_name}_raw(static_cast<::protocyte::i32>(value)); }}"
        )
        return
    _emit_field_api_annotations(w, item, options)
    w.line(
        f"constexpr {typ} {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)} : {_default(item)}; }}"
    )
    _emit_field_api_annotations(w, item, options)
    w.line(f"void set_{item.cpp_name}(const {typ} value) noexcept {{")
    w.push()
    w.line(f"clear_{cpp_derivable_identifier(item.oneof_name)}();")
    w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{value}};")
    w.line(f"{case_member} = {case_type}::{item.cpp_name};")
    w.pop()
    w.line("}")


def _emit_wire_api(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    reader_cpp_name = message.reader_cpp_name
    writer_cpp_name = message.writer_cpp_name
    config_cpp_name = message.config_cpp_name
    w.line(f"template <::protocyte::ReaderLike {reader_cpp_name}>")
    w.line(
        f"static ::protocyte::Result<{message.cpp_name}> parse(Context& ctx, {reader_cpp_name}& reader) noexcept {{"
    )
    with w.indent():
        w.line(f"auto output = {message.cpp_name}::create(ctx);")
        w.line(
            "if (const auto st = parse(reader, output); !st) { return ::protocyte::unexpected(st.error()); }"
        )
        w.line("return ::protocyte::move(output);")
    w.line("}")
    w.line()
    w.line(
        f"static ::protocyte::Result<{message.cpp_name}> parse(Context& ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {{"
    )
    with w.indent():
        w.line("const auto checked_input = ::protocyte::checked_span_of(input);")
        w.line(
            "if (!checked_input) { return ::protocyte::unexpected(checked_input.error()); }"
        )
        w.line(
            "::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};"
        )
        w.line("return parse(ctx, reader);")
    w.line("}")
    w.line()
    w.line(f"template <::protocyte::ReaderLike {reader_cpp_name}>")
    w.line(
        f"static ::protocyte::Status parse({reader_cpp_name}& reader, {message.cpp_name}& output) noexcept {{"
    )
    with w.indent():
        w.line("Context* const output_ctx = output.context();")
        w.line("reset_for_reuse_(output, *output_ctx);")
        w.line("if (const auto st = output.merge_from(reader); !st) {")
        with w.indent():
            w.line("reset_for_reuse_(output, *output_ctx);")
            w.line("return st;")
        w.line("}")
        w.line("return {};")
    w.line("}")
    w.line()
    w.line(f"template <::protocyte::ReaderLike {reader_cpp_name}>")
    w.line(f"::protocyte::Status merge_from({reader_cpp_name}& reader) noexcept {{")
    with w.indent():
        w.line(
            f"::protocyte::ParseBudgetReader<{reader_cpp_name}> budget_reader{{reader, ctx_->limits.max_total_bytes, ctx_->limits.max_repeated_elements, ctx_->limits.max_map_entries}};"
        )
        w.line(
            "if (const auto st = merge_fields_from(budget_reader); !st) { return st; }"
        )
        w.line(
            "if (budget_reader.limit_reached()) { return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, budget_reader.position()); }"
        )
        w.line("return validate();")
    w.line("}")
    w.line()
    w.line("private:")
    w.line(f"template <typename {reader_cpp_name}>")
    w.line(
        f"::protocyte::Status merge_field_from_({reader_cpp_name}& reader, const ::protocyte::u32 field_number, const ::protocyte::WireType wire_type) noexcept {{"
    )
    with w.indent():
        _emit_merge_field_body(w, message, options)
    w.line("}")
    w.line()
    w.line("protected:")
    w.line("friend class ::protocyte::MessageParseAccess;")
    w.line()
    w.line(f"template <typename {reader_cpp_name}>")
    w.line(
        f"::protocyte::Status merge_fields_from({reader_cpp_name}& reader) noexcept {{"
    )
    with w.indent():
        _emit_merge_fields_body(w, message, options)
    w.line("}")
    w.line()
    w.line("public:")
    w.line(f"template <::protocyte::WriterLike {writer_cpp_name}>")
    w.line(
        f"::protocyte::Status serialize({writer_cpp_name}& writer) const noexcept {{"
    )
    with w.indent():
        w.line("if (const auto st = validate(); !st) { return st; }")
        for item in sorted(message.fields, key=lambda f: f.number):
            _emit_serialize_statement(w, item, options)
        w.line(
            f"if constexpr (::protocyte::preserve_unknown_fields_v<{config_cpp_name}>) {{"
        )
        with w.indent():
            w.line("const auto unknown_bytes = unknown_fields_.bytes();")
            w.line("if (!unknown_bytes.empty()) {")
            with w.indent():
                w.line(
                    "if (const auto st = writer.write(unknown_bytes.data(), unknown_bytes.size()); !st) { return st; }"
                )
            w.line("}")
        w.line("}")
        w.line("return {};")
    w.line("}")
    w.line()
    w.line(
        "::protocyte::Result<::protocyte::usize> serialize(const ::protocyte::Span<::protocyte::u8> output) const noexcept {"
    )
    with w.indent():
        w.line("return ::protocyte::serialize(*this, output);")
    w.line("}")
    w.line()
    w.line("::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {")
    with w.indent():
        w.line(
            "if (const auto st = validate(); !st) { return ::protocyte::unexpected(st.error()); }"
        )
        w.line("::protocyte::usize total {};")
        if message.fields:
            for item in sorted(message.fields, key=lambda f: f.number):
                _emit_size_statement(w, item, options)
        w.line(
            "const auto total_with_unknown = ::protocyte::checked_add(total, unknown_fields_.size());"
        )
        w.line(
            "if (!total_with_unknown) { return ::protocyte::unexpected(total_with_unknown.error()); }"
        )
        w.line("return *total_with_unknown;")
    w.line("}")
    w.line()
    w.line("::protocyte::Status validate() const noexcept {")
    with w.indent():
        _emit_fixed_array_validation(w, message)
        _emit_closed_enum_validation(w, message)
        _emit_required_validation(w, message)
        _emit_string_validation(w, message)
        _emit_nested_validation(w, message)
        w.line("return {};")
    w.line("}")


def _emit_unknown_field_handling(w: CppWriter, config_cpp_name: str) -> None:
    w.line(
        f"if constexpr (::protocyte::preserve_unknown_fields_v<{config_cpp_name}>) {{"
    )
    with w.indent():
        w.line(
            f"if (const auto st = ::protocyte::read_unknown_field<{config_cpp_name}>(*ctx_, reader, wire_type, field_number, unknown_fields_); !st) {{ return st; }}"
        )
    w.line("} else {")
    with w.indent():
        w.line(
            f"if (const auto st = ::protocyte::skip_field<{config_cpp_name}>(*ctx_, reader, wire_type, field_number); !st) {{ return st; }}"
        )
    w.line("}")


def _emit_merge_fields_body(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    w.line("while (!reader.eof()) {")
    with w.indent():
        w.line("const auto tag = ::protocyte::read_tag(reader);")
        w.line("if (!tag) { return tag.status(); }")
        w.line("const auto [field_number, wire_type] = *tag;")
        w.line(
            "if (const auto st = merge_field_from_(reader, field_number, wire_type); !st) {"
        )
        with w.indent():
            w.line("return ::protocyte::with_field(st, field_number);")
        w.line("}")
    w.line("}")
    w.line("return {};")


def _emit_merge_field_body(
    w: CppWriter, message: MessageModel, options: GeneratorOptions
) -> None:
    if message.fields:
        w.line("switch (static_cast<FieldNumber>(field_number)) {")
        with w.indent():
            for item in sorted(message.fields, key=lambda f: f.number):
                w.line(f"case FieldNumber::{_field_number_name(item)}: {{")
                with w.indent():
                    _emit_parse_case(w, item, options)
                    w.line("break;")
                w.line("}")
            w.line("default: {")
            with w.indent():
                _emit_unknown_field_handling(w, message.config_cpp_name)
                w.line("break;")
            w.line("}")
        w.line("}")
    else:
        _emit_unknown_field_handling(w, message.config_cpp_name)
    w.line("return {};")


def _emit_fixed_array_validation(
    w: CppWriter, message: MessageModel, *, for_size: bool = False
) -> None:
    for item in sorted(message.fields, key=lambda f: f.number):
        if not item.array_fixed or item.array_max is None:
            continue
        if item.repeated:
            condition = (
                f"!{_member(item)}.empty() && "
                f"{_member(item)}.size() != {_array_max_literal(item)}"
            )
        else:
            continue
        error = f"::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)})"
        w.line(f"if ({condition}) {{")
        with w.indent():
            if for_size:
                w.line(f"return {error};")
            else:
                w.line(
                    f"return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)});"
                )
        w.line("}")


def _emit_required_validation(
    w: CppWriter, message: MessageModel, *, for_size: bool = False
) -> None:
    for item in sorted(message.fields, key=lambda f: f.number):
        if not item.required:
            continue
        w.line(f"if (!has_{item.cpp_name}()) {{")
        with w.indent():
            error = f"::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)})"
            if for_size:
                w.line(f"return {error};")
            else:
                w.line(f"return {error};")
        w.line("}")


def _emit_closed_enum_validation(
    w: CppWriter, message: MessageModel, *, for_size: bool = False
) -> None:
    del for_size
    for item in sorted(message.fields, key=lambda f: f.number):
        if item.kind == "map":
            assert item.map_key is not None and item.map_value is not None
            for map_item, value_expr in (
                (item.map_key, f"{item.cpp_name}_entry.key"),
                (item.map_value, f"{item.cpp_name}_entry.value"),
            ):
                condition = _closed_enum_invalid_condition(map_item, value_expr)
                if condition is None:
                    continue
                w.line(f"for (const auto &{item.cpp_name}_entry : {_member(item)}) {{")
                with w.indent():
                    _emit_closed_enum_reject(w, item, condition)
                w.line("}")
            continue

        condition = _closed_enum_invalid_condition(item, _member(item))
        if condition is None:
            continue
        if item.repeated:
            value_name = f"{item.cpp_name}_value"
            w.line(f"for (const auto {value_name} : {_member(item)}) {{")
            with w.indent():
                _emit_closed_enum_reject(
                    w, item, _closed_enum_invalid_condition(item, value_name)
                )
            w.line("}")
            continue
        if item.oneof_name is not None:
            case_member = _oneof_case_member(item.oneof_name)
            case_type = _oneof_case_type(item.oneof_name)
            w.line(f"if ({case_member} == {case_type}::{item.cpp_name}) {{")
            with w.indent():
                _emit_closed_enum_reject(w, item, condition)
            w.line("}")
            continue
        if _has_presence_flag(item):
            w.line(f"if (has_{item.cpp_name}_) {{")
            with w.indent():
                _emit_closed_enum_reject(w, item, condition)
            w.line("}")
            continue
        _emit_closed_enum_reject(w, item, condition)


def _emit_string_validation_reject(
    w: CppWriter, item: FieldModel, value_expr: str
) -> None:
    w.line(f"if (const auto st = {value_expr}.validate(); !st) {{")
    with w.indent():
        w.line(
            "return ::protocyte::unexpected("
            f"st.error().code, {{}}, {_field_number_u32(item)});"
        )
    w.line("}")


def _emit_string_validation(w: CppWriter, message: MessageModel) -> None:
    for item in sorted(message.fields, key=lambda f: f.number):
        if item.kind == "map":
            assert item.map_key is not None and item.map_value is not None
            string_members = [
                member
                for member in (item.map_key, item.map_value)
                if member.kind == "string"
            ]
            if not string_members:
                continue
            entry_name = f"{item.cpp_name}_entry"
            w.line(f"for (const auto &{entry_name} : {_member(item)}) {{")
            with w.indent():
                for member in string_members:
                    _emit_string_validation_reject(
                        w, item, f"{entry_name}.{member.cpp_name}"
                    )
            w.line("}")
            continue

        if item.kind != "string":
            continue
        if item.repeated:
            value_name = f"{item.cpp_name}_value"
            w.line(f"for (const auto &{value_name} : {_member(item)}) {{")
            with w.indent():
                _emit_string_validation_reject(w, item, value_name)
            w.line("}")
            continue
        if item.oneof_name is not None:
            case_member = _oneof_case_member(item.oneof_name)
            case_type = _oneof_case_type(item.oneof_name)
            w.line(f"if ({case_member} == {case_type}::{item.cpp_name}) {{")
            with w.indent():
                _emit_string_validation_reject(w, item, _member(item))
            w.line("}")
            continue
        _emit_string_validation_reject(w, item, _member(item))


def _emit_nested_validation(w: CppWriter, message: MessageModel) -> None:
    for item in sorted(message.fields, key=lambda f: f.number):
        if item.kind == "map":
            assert item.map_value is not None
            if item.map_value.kind != "message":
                continue
            value_name = f"{item.cpp_name}_value"
            w.line(f"for (const auto &{value_name} : {_member(item)}) {{")
            with w.indent():
                w.line(
                    f"if (const auto st = {value_name}.value.validate(); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
                )
            w.line("}")
            continue
        if item.kind != "message":
            continue
        if item.repeated:
            value_name = f"{item.cpp_name}_value"
            w.line(f"for (const auto &{value_name} : {_member(item)}) {{")
            with w.indent():
                w.line(
                    f"if (const auto st = {value_name}.validate(); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
                )
            w.line("}")
            continue
        if item.oneof_name is not None:
            condition = f"{_oneof_case_member(item.oneof_name)} == {_oneof_case_type(item.oneof_name)}::{item.cpp_name}"
            w.line(f"if ({condition} && {_member(item)}.has_value()) {{")
        else:
            w.line(f"if ({_member(item)}.has_value()) {{")
        with w.indent():
            w.line(
                f"if (const auto st = {_member(item)}->validate(); !st) {{ return ::protocyte::with_field(st, {_field_number_u32(item)}); }}"
            )
        w.line("}")


def _packed_fixed_width_size(item: FieldModel) -> str | None:
    widths = {
        FieldDescriptorProto.TYPE_FIXED32: "4u",
        FieldDescriptorProto.TYPE_SFIXED32: "4u",
        FieldDescriptorProto.TYPE_FLOAT: "4u",
        FieldDescriptorProto.TYPE_FIXED64: "8u",
        FieldDescriptorProto.TYPE_SFIXED64: "8u",
        FieldDescriptorProto.TYPE_DOUBLE: "8u",
    }
    return widths.get(item.proto_type)


def _packed_bulk_fixed_width_size(item: FieldModel) -> str | None:
    widths = {
        FieldDescriptorProto.TYPE_FIXED32: "4u",
        FieldDescriptorProto.TYPE_FLOAT: "4u",
        FieldDescriptorProto.TYPE_FIXED64: "8u",
        FieldDescriptorProto.TYPE_DOUBLE: "8u",
    }
    return widths.get(item.proto_type)


def _emit_parse_case(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    allowed_wire_types = [_wire(item)]
    if item.repeated and item.packable:
        allowed_wire_types.append("::protocyte::WireType::LEN")
    mismatch = " && ".join(
        f"wire_type != {wire_type}" for wire_type in dict.fromkeys(allowed_wire_types)
    )
    w.line(f"if ({mismatch}) {{")
    with w.indent():
        _emit_unknown_field_handling(w, item.config_cpp_name)
        w.line("break;")
    w.line("}")
    if item.repeated and item.kind != "map":
        if item.packable:
            w.line("if (wire_type == ::protocyte::WireType::LEN) {")
            with w.indent():
                w.line("auto len = ::protocyte::read_length_delimited_size(reader);")
                w.line("if (!len) { return len.status(); }")
                packed_values_name = f"packed_{item.cpp_name}_values"
                width = _packed_fixed_width_size(item)
                bulk_width = _packed_bulk_fixed_width_size(item)
                if not item.repeated_array and bulk_width is not None:
                    w.line(
                        f"if (const auto st = ::protocyte::read_fixed_width_packed_values(reader, *len, field_number, {_member(item)}); !st) {{ return st; }}"
                    )
                    w.line("break;")
                else:
                    w.line(
                        "if (const auto st = reader.can_read(*len); !st) { return st; }"
                    )
                    if width is not None:
                        w.line(f"if (*len % {width} != 0u) {{")
                        with w.indent():
                            w.line(
                                "return ::protocyte::unexpected(::protocyte::ErrorCode::unexpected_eof, reader.position(), field_number);"
                            )
                        w.line("}")
                        w.line(
                            f"if (const auto st = reader.consume_repeated_elements(*len / {width}, field_number); !st) {{ return st; }}"
                        )
                    _emit_repeated_storage_decl(w, item, packed_values_name, options)
                    packed_unknown_name = None
                    if item.enum_closed:
                        packed_unknown_name = f"packed_{item.cpp_name}_unknown_fields"
                        w.line(
                            f"::protocyte::UnknownFieldStorage<{item.config_cpp_name}> {packed_unknown_name}{{ctx_}};"
                        )
                    if not item.repeated_array and width is not None:
                        reserve_name = f"packed_reserve_{item.cpp_name}"
                        w.line(f"const auto {reserve_name} = *len / {width};")
                        w.line(
                            f"if (const auto st = {packed_values_name}.reserve({reserve_name}); !st) {{ return st; }}"
                        )
                    w.line(
                        f"::protocyte::LimitedReader<{item.reader_cpp_name}> packed{{reader, *len}};"
                    )
                    w.line("while (!packed.eof()) {")
                    with w.indent():
                        _emit_read_repeated_value(
                            w,
                            item,
                            "packed",
                            options,
                            target=packed_values_name,
                            consume_budget=width is None,
                            unknown_storage=packed_unknown_name,
                        )
                    w.line("}")
                    if packed_unknown_name is not None:
                        _emit_prepare_repeated_values_commit(
                            w, item, packed_values_name
                        )
                        merged_unknown_name = f"merged_{item.cpp_name}_unknown_fields"
                        w.line(
                            f"::protocyte::UnknownFieldStorage<{item.config_cpp_name}> {merged_unknown_name}{{ctx_}};"
                        )
                        w.line(
                            f"if constexpr (::protocyte::preserve_unknown_fields_v<{item.config_cpp_name}>) {{"
                        )
                        with w.indent():
                            w.line(f"if (!{packed_unknown_name}.empty()) {{")
                            with w.indent():
                                w.line(
                                    f"if (const auto st = ::protocyte::prepare_unknown_field_merge<{item.config_cpp_name}>(*ctx_, unknown_fields_, {packed_unknown_name}, {merged_unknown_name}); !st) {{ return st; }}"
                                )
                            w.line("}")
                        w.line("}")
                    _emit_commit_repeated_values(w, item, packed_values_name)
                    if packed_unknown_name is not None:
                        w.line(
                            f"if constexpr (::protocyte::preserve_unknown_fields_v<{item.config_cpp_name}>) {{"
                        )
                        with w.indent():
                            w.line(f"if (!{packed_unknown_name}.empty()) {{")
                            with w.indent():
                                w.line(
                                    f"unknown_fields_ = ::protocyte::move({merged_unknown_name});"
                                )
                            w.line("}")
                        w.line("}")
                    w.line("break;")
            w.line("}")
        if _is_scalar_field(item) or _uses_runtime_len_field_helper(item):
            _emit_read_repeated_value(w, item, "reader", options, checked=True)
        else:
            w.line(
                f"if (wire_type != {_wire(item)}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }}"
            )
            _emit_read_repeated_value(w, item, "reader", options)
        return
    if item.kind == "map":
        _emit_read_map(w, item, options)
        return
    if _is_scalar_field(item) or _uses_runtime_len_field_helper(item):
        _emit_read_single_value(w, item, "reader", options)
        return
    w.line(
        f"if (wire_type != {_wire(item)}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }}"
    )
    _emit_read_single_value(w, item, "reader", options)


def _emit_read_repeated_value(
    w: CppWriter,
    item: FieldModel,
    reader: str,
    options: GeneratorOptions,
    *,
    checked: bool = False,
    target: str | None = None,
    consume_budget: bool = True,
    unknown_storage: str | None = None,
) -> None:
    target = _member(item) if target is None else target
    if consume_budget:
        w.line(
            f"if (const auto st = {reader}.consume_repeated_elements(1u, field_number); !st) {{ return st; }}"
        )
    if item.kind in {"string", "bytes"}:
        typ = _field_type(item, options)
        w.line(f"{typ} value{{ctx_}};")
        helper = _length_delimited_read_helper(item, checked=checked)
        args = (
            f"*ctx_, {reader}, wire_type, field_number, value"
            if checked
            else f"*ctx_, {reader}, value"
        )
        w.line(
            f"if (const auto st = ::protocyte::{helper}<{item.config_cpp_name}>({args}); !st) {{ return st; }}"
        )
        w.line(
            f"if (const auto st = {target}.push_back(::protocyte::move(value)); !st) {{ return st; }}"
        )
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        w.line(f"{typ} value{{*ctx_}};")
        w.line(
            f"if (const auto st = ::protocyte::read_message_partial<{item.config_cpp_name}>(*ctx_, {reader}, field_number, value); !st) {{ return st; }}"
        )
        w.line(
            f"if (const auto st = {target}.push_back(::protocyte::move(value)); !st) {{ return st; }}"
        )
        return
    w.line(f"{_element_type(item, options)} value{{}};")
    accepted = _emit_read_scalar(
        w,
        item,
        reader,
        "value",
        options,
        checked=checked,
        unknown_storage=unknown_storage,
    )
    if accepted is not None:
        action = "continue" if reader == "packed" else "break"
        w.line(f"if (!{accepted}) {{ {action}; }}")
    w.line(f"if (const auto st = {target}.push_back(value); !st) {{ return st; }}")


def _emit_repeated_storage_decl(
    w: CppWriter, item: FieldModel, name: str, options: GeneratorOptions
) -> None:
    typ = _storage_type(item, options)
    if item.repeated_array:
        w.line(f"{typ} {name}{{}};")
    else:
        w.line(f"{typ} {name}{{ctx_}};")


def _emit_prepare_repeated_values_commit(
    w: CppWriter, item: FieldModel, source: str
) -> None:
    prepared_size_name = f"{source}_prepared_size"
    w.line(
        f"const auto {prepared_size_name} = ::protocyte::checked_add({_member(item)}.size(), {source}.size());"
    )
    w.line(f"if (!{prepared_size_name}) {{ return {prepared_size_name}.status(); }}")
    if item.repeated_array:
        w.line(f"if (*{prepared_size_name} > {_array_max_literal(item)}) {{")
        with w.indent():
            w.line(
                "return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(), field_number);"
            )
        w.line("}")
        return
    w.line(
        f"if (const auto st = {_member(item)}.reserve(*{prepared_size_name}); !st) {{ return st; }}"
    )


def _emit_commit_repeated_values(w: CppWriter, item: FieldModel, source: str) -> None:
    if not item.repeated_array and _is_scalar_field(item):
        w.line(
            f"if (const auto st = {_member(item)}.append_trivial_range({source}.data(), {source}.size()); !st) {{ return st; }}"
        )
        return

    commit_size_name = f"{source}_commit_size"
    w.line(
        f"const auto {commit_size_name} = ::protocyte::checked_add({_member(item)}.size(), {source}.size());"
    )
    w.line(f"if (!{commit_size_name}) {{ return {commit_size_name}.status(); }}")
    if item.repeated_array:
        w.line(f"if (*{commit_size_name} > {_array_max_literal(item)}) {{")
        with w.indent():
            w.line(
                "return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(), field_number);"
            )
        w.line("}")
        w.line(f"for (const auto &value : {source}) {{")
        with w.indent():
            w.line(
                f"if (const auto st = {_member(item)}.push_back(value); !st) {{ return st; }}"
            )
        w.line("}")
        return
    w.line(
        f"if (const auto st = {_member(item)}.reserve(*{commit_size_name}); !st) {{ return st; }}"
    )
    w.line(f"for (const auto &value : {source}) {{")
    with w.indent():
        w.line(
            f"if (const auto st = {_member(item)}.push_back(value); !st) {{ return st; }}"
        )
    w.line("}")


def _emit_read_bounded_bytes(
    w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions
) -> None:
    bound = _array_max_literal(item)
    w.line(f"auto len = ::protocyte::read_length_delimited_size({reader});")
    w.line("if (!len) { return len.status(); }")
    if item.array_fixed:
        w.line(
            f"if (*len != {bound}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {reader}.position(), field_number); }}"
        )
    else:
        w.line(
            f"if (*len > {bound}) {{ return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, {reader}.position(), field_number); }}"
        )
    w.line(f"if (const auto st = {reader}.can_read(*len); !st) {{ return st; }}")
    value_name = f"{item.cpp_name}_value"
    w.line(f"{_storage_type(item, options)} {value_name}{{}};")
    w.line(
        f"if (const auto st = {value_name}.resize_for_overwrite(*len); !st) {{ return st; }}"
    )
    w.line(f"const auto view = {value_name}.mutable_view();")
    w.line(
        f"if (const auto st = {reader}.read(view.data(), view.size()); !st) {{ return st; }}"
    )
    if item.oneof_name:
        w.line(f"clear_{cpp_derivable_identifier(item.oneof_name)}();")
        w.line(
            f"new (&{_member(item)}) {_storage_type(item, options)} {{::protocyte::move({value_name})}};"
        )
        w.line(
            f"{_oneof_case_member(item.oneof_name)} = {_oneof_case_type(item.oneof_name)}::{item.cpp_name};"
        )
        return
    w.line(f"{_member(item)} = ::protocyte::move({value_name});")
    if _has_presence_flag(item):
        w.line(f"has_{item.cpp_name}_ = true;")


def _emit_read_staged_message(
    w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions
) -> None:
    value_name = f"{item.cpp_name}_value"
    typ = _field_type(item, options)
    w.line(f"{typ} {value_name}{{*ctx_}};")
    if item.oneof_name:
        w.line(f"if (has_{item.cpp_name}() && {_member(item)}.has_value()) {{")
        with w.indent():
            w.line(
                f"if (const auto st = {value_name}.copy_from(*{_member(item)}); !st) {{ return st; }}"
            )
        w.line("}")
    else:
        w.line(f"if ({_member(item)}.has_value()) {{")
        with w.indent():
            w.line(
                f"if (const auto st = {value_name}.copy_from(*{_member(item)}); !st) {{ return st; }}"
            )
        w.line("}")
    w.line(
        f"if (const auto st = ::protocyte::read_message_partial<{item.config_cpp_name}>(*ctx_, {reader}, field_number, {value_name}); !st) {{ return st; }}"
    )
    if item.oneof_name:
        _emit_commit_oneof_value(w, item, value_name, options)
    elif item.recursive_box:
        w.line(
            f"if (const auto st = {_member(item)}.assign(::protocyte::move({value_name})); !st) {{ return st; }}"
        )
    else:
        w.line(
            f"if (const auto st = {_member(item)}.emplace(::protocyte::move({value_name})); !st) {{ return st; }}"
        )


def _emit_commit_oneof_value(
    w: CppWriter, item: FieldModel, value: str, options: GeneratorOptions
) -> None:
    assert item.oneof_name is not None
    oneof_name = cpp_derivable_identifier(item.oneof_name)
    case_type = _oneof_case_type(item.oneof_name)
    case_member = _oneof_case_member(item.oneof_name)
    if item.kind == "message":
        committed_name = f"{item.cpp_name}_committed"
        if item.recursive_box:
            w.line(f"{_storage_type(item, options)} {committed_name}{{ctx_}};")
            w.line(
                f"if (const auto st = {committed_name}.assign(::protocyte::move({value})); !st) {{ return st; }}"
            )
        else:
            w.line(f"{_storage_type(item, options)} {committed_name}{{}};")
            w.line(
                f"if (const auto st = {committed_name}.emplace(::protocyte::move({value})); !st) {{ return st; }}"
            )
        value = committed_name
    w.line(f"clear_{oneof_name}();")
    w.line(
        f"new (&{_member(item)}) {_storage_type(item, options)} {{::protocyte::move({value})}};"
    )
    w.line(f"{case_member} = {case_type}::{item.cpp_name};")


def _emit_read_single_value(
    w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions
) -> None:
    if item.oneof_name and item.kind in {"string", "bytes"}:
        if item.kind == "bytes" and item.array_enabled:
            _emit_read_bounded_bytes(w, item, reader, options)
        else:
            typ = _field_type(item, options)
            value_name = f"{item.cpp_name}_value"
            w.line(f"{typ} {value_name}{{ctx_}};")
            helper = _length_delimited_read_helper(item, checked=True)
            w.line(
                f"if (const auto st = ::protocyte::{helper}<{item.config_cpp_name}>(*ctx_, {reader}, wire_type, field_number, {value_name}); !st) {{ return st; }}"
            )
            _emit_commit_oneof_value(w, item, value_name, options)
        return
    if item.kind == "bytes" and item.array_enabled:
        _emit_read_bounded_bytes(w, item, reader, options)
        return
    if item.kind in {"string", "bytes"}:
        helper = _length_delimited_read_helper(item, checked=True)
        w.line(
            f"if (const auto st = ::protocyte::{helper}<{item.config_cpp_name}>(*ctx_, {reader}, wire_type, field_number, {_member(item)}); !st) {{ return st; }}"
        )
        if _has_presence_flag(item):
            w.line(f"has_{item.cpp_name}_ = true;")
        return
    if item.kind == "message":
        _emit_read_staged_message(w, item, reader, options)
        return
    if item.oneof_name:
        value_name = f"{item.cpp_name}_value"
        w.line(f"{_field_type(item, options)} {value_name}{{}};")
        accepted = _emit_read_scalar(w, item, reader, value_name, options, checked=True)
        if accepted is not None:
            w.line(f"if (!{accepted}) {{ break; }}")
        _emit_commit_oneof_value(w, item, value_name, options)
        return
    accepted = _emit_read_scalar(w, item, reader, _member(item), options, checked=True)
    if accepted is not None:
        w.line(f"if (!{accepted}) {{ break; }}")
    if _has_presence_flag(item):
        w.line(f"has_{item.cpp_name}_ = true;")


def _emit_read_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    key = item.map_key
    value = item.map_value
    w.line(
        "if (wire_type != ::protocyte::WireType::LEN) { return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }"
    )
    w.line(
        "if (const auto st = reader.consume_map_entries(1u, field_number); !st) { return st; }"
    )
    _emit_temp_decl(w, key, "key", options)
    _emit_temp_decl(w, value, "value", options)
    w.line("bool entry_is_unknown{};")
    parse_name = f"parse_{item.cpp_name}_entry"
    w.line(
        f"const auto {parse_name} = [&](auto& entry_reader) noexcept -> ::protocyte::Status {{"
    )
    with w.indent():
        w.line("while (!entry_reader.eof()) {")
        with w.indent():
            w.line("const auto entry_tag = ::protocyte::read_tag(entry_reader);")
            w.line("if (!entry_tag) { return entry_tag.status(); }")
            w.line("const auto [entry_field, entry_wire] = *entry_tag;")
            w.line("switch (entry_field) {")
            with w.indent():
                w.line("case 1u: {")
                with w.indent():
                    w.line(f"if (entry_wire != {_wire(key)}) {{")
                    with w.indent():
                        w.line(
                            f"if (const auto st = ::protocyte::skip_field<{item.config_cpp_name}>(*ctx_, entry_reader, entry_wire, entry_field); !st) {{ return st; }}"
                        )
                        w.line("break;")
                    w.line("}")
                    _emit_read_map_member(
                        w,
                        key,
                        "entry_reader",
                        "key",
                        options,
                        "1u",
                    )
                    w.line("break;")
                w.line("}")
                w.line("case 2u: {")
                with w.indent():
                    w.line(f"if (entry_wire != {_wire(value)}) {{")
                    with w.indent():
                        w.line(
                            f"if (const auto st = ::protocyte::skip_field<{item.config_cpp_name}>(*ctx_, entry_reader, entry_wire, entry_field); !st) {{ return st; }}"
                        )
                        w.line("break;")
                    w.line("}")
                    _emit_read_map_member(
                        w,
                        value,
                        "entry_reader",
                        "value",
                        options,
                        "2u",
                    )
                    w.line("break;")
                w.line("}")
                w.line("default: {")
                with w.indent():
                    w.line(
                        f"if (const auto st = ::protocyte::skip_field<{item.config_cpp_name}>(*ctx_, entry_reader, entry_wire, entry_field); !st) {{ return st; }}"
                    )
                    w.line("break;")
                w.line("}")
            w.line("}")
        w.line("}")
        w.line("return {};")
    w.line("};")

    def emit_normal_entry_parse() -> None:
        w.line(
            f"auto entry = ::protocyte::open_nested_message<{item.config_cpp_name}>(*ctx_, reader, field_number);"
        )
        w.line("if (!entry) { return entry.status(); }")
        w.line("auto& entry_reader = entry->reader();")
        w.line(f"if (const auto st = {parse_name}(entry_reader); !st) {{ return st; }}")
        w.line("if (const auto st = entry->finish(); !st) { return st; }")
        w.line("if (!entry_is_unknown) {")
        with w.indent():
            w.line(
                f"if (const auto insert = {_member(item)}.insert_or_assign(::protocyte::move(key), ::protocyte::move(value)); !insert) {{ return insert; }}"
            )
        w.line("}")

    if value.enum_closed:
        w.line(
            f"if constexpr (::protocyte::preserve_unknown_fields_v<{item.config_cpp_name}>) {{"
        )
        with w.indent():
            staged_name = f"staged_{item.cpp_name}_entry"
            w.line(
                "const auto entry_size = ::protocyte::read_length_delimited_size(reader);"
            )
            w.line("if (!entry_size) { return entry_size.status(); }")
            w.line("if (*entry_size > ctx_->limits.max_message_bytes) {")
            with w.indent():
                w.line(
                    "return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, reader.position(), field_number);"
                )
            w.line("}")
            w.line(
                "if (const auto st = reader.can_read(*entry_size); !st) { return st; }"
            )
            w.line(
                f"if (const auto st = ::protocyte::push_recursion<{item.config_cpp_name}>(*ctx_, reader.position(), field_number); !st) {{ return st; }}"
            )
            w.line("const auto entry_offset = reader.position();")
            w.line(
                f"typename {item.config_cpp_name}::template Vector<::protocyte::u8> {staged_name}{{ctx_}};"
            )
            w.line(
                f"if (const auto st = {staged_name}.resize_for_overwrite(*entry_size); !st) {{ ::protocyte::pop_recursion<{item.config_cpp_name}>(*ctx_); return st; }}"
            )
            w.line(
                f"if (const auto st = reader.read({staged_name}.data(), {staged_name}.size()); !st) {{ ::protocyte::pop_recursion<{item.config_cpp_name}>(*ctx_); return st; }}"
            )
            w.line(
                f"::protocyte::StagedReader<{item.reader_cpp_name}> entry_reader{{::protocyte::Span<const ::protocyte::u8>{{{staged_name}.data(), {staged_name}.size()}}, reader, entry_offset}};"
            )
            w.line(f"const auto entry_status = {parse_name}(entry_reader);")
            w.line(f"::protocyte::pop_recursion<{item.config_cpp_name}>(*ctx_);")
            w.line("if (!entry_status) { return entry_status; }")
            w.line("if (entry_is_unknown) {")
            with w.indent():
                w.line("auto unknown = mutable_unknown_fields();")
                w.line(
                    f"if (const auto st = unknown.add_length_delimited(field_number, ::protocyte::Span<const ::protocyte::u8>{{{staged_name}.data(), {staged_name}.size()}}); !st) {{ return st; }}"
                )
            w.line("} else {")
            with w.indent():
                w.line(
                    f"if (const auto insert = {_member(item)}.insert_or_assign(::protocyte::move(key), ::protocyte::move(value)); !insert) {{ return insert; }}"
                )
            w.line("}")
        w.line("} else {")
        with w.indent():
            emit_normal_entry_parse()
        w.line("}")
    else:
        emit_normal_entry_parse()


def _emit_read_map_member(
    w: CppWriter,
    item: FieldModel,
    reader: str,
    target: str,
    options: GeneratorOptions,
    field_number: str,
) -> None:
    if item.enum_closed:
        result_name = f"decoded_{target}_enum"
        value_name = f"{target}_enum_value"
        w.line(f"const auto {result_name} = ::protocyte::read_enum({reader});")
        w.line(f"if (!{result_name}) {{ return {result_name}.status(); }}")
        w.line(f"const auto {value_name} = *{result_name};")
        condition = _closed_enum_invalid_condition(item, value_name)
        assert condition is not None
        w.line(f"if ({condition}) {{")
        with w.indent():
            w.line("entry_is_unknown = true;")
        w.line("} else {")
        with w.indent():
            w.line("entry_is_unknown = false;")
            w.line(f"{target} = {value_name};")
        w.line("}")
        return
    _emit_read_named_value(w, item, reader, target, options, field_number)


def _emit_temp_decl(
    w: CppWriter, item: FieldModel, name: str, options: GeneratorOptions
) -> None:
    typ = _field_type(item, options)
    if item.kind in {"string", "bytes"}:
        w.line(f"{typ} {name}{{ctx_}};")
    elif item.kind == "message":
        w.line(f"{typ} {name}{{*ctx_}};")
    else:
        w.line(f"{typ} {name}{{}};")


def _emit_read_named_value(
    w: CppWriter,
    item: FieldModel,
    reader: str,
    target: str,
    options: GeneratorOptions,
    field_number: str,
) -> None:
    if item.kind in {"string", "bytes"}:
        helper = _length_delimited_read_helper(item, checked=False)
        w.line(
            f"if (const auto st = ::protocyte::{helper}<{item.config_cpp_name}>(*ctx_, {reader}, {target}); !st) {{ return st; }}"
        )
    elif item.kind == "message":
        w.line(
            f"if (const auto st = ::protocyte::read_message_partial<{item.config_cpp_name}>(*ctx_, {reader}, {field_number}, {target}); !st) {{ return st; }}"
        )
    else:
        _emit_read_scalar(
            w, item, reader, target, options, field_number_expr=field_number
        )


def _emit_read_scalar(
    w: CppWriter,
    item: FieldModel,
    reader: str,
    target: str,
    options: GeneratorOptions,
    *,
    checked: bool = False,
    field_number_expr: str | None = None,
    unknown_storage: str | None = None,
) -> str | None:
    del options
    helper = _scalar_read_helper(item, checked=checked)
    args = f"{reader}, wire_type, field_number" if checked else reader
    error_field_number = "field_number" if checked else field_number_expr
    if item.enum_closed and field_number_expr is None:
        raw_name = f"decoded_{item.cpp_name}_raw"
        result_name = f"decoded_{item.cpp_name}"
        value_name = f"{item.cpp_name}_value"
        accepted_name = f"{item.cpp_name}_accepted"
        w.line(f"const auto {raw_name} = ::protocyte::read_varint({reader});")
        w.line(f"if (!{raw_name}) {{ return {raw_name}.status(); }}")
        w.line(f"const auto {value_name} = static_cast<::protocyte::i32>(*{raw_name});")
        w.line(f"bool {accepted_name}{{true}};")
        condition = _closed_enum_invalid_condition(item, value_name)
        assert condition is not None
        w.line(f"if ({condition}) {{")
        with w.indent():
            w.line(
                f"if constexpr (::protocyte::preserve_unknown_fields_v<{item.config_cpp_name}>) {{"
            )
            with w.indent():
                if unknown_storage is None:
                    w.line("auto unknown = mutable_unknown_fields();")
                else:
                    w.line(
                        f"::protocyte::MutableUnknownFieldSet<{item.config_cpp_name}> unknown{{*ctx_, {unknown_storage}}};"
                    )
                w.line(
                    f"if (const auto st = unknown.add_varint(field_number, *{raw_name}); !st) {{ return st; }}"
                )
            w.line("}")
            w.line(f"{accepted_name} = false;")
        w.line("} else {")
        with w.indent():
            w.line(f"{target} = {value_name};")
        w.line("}")
        return accepted_name
    if item.enum_closed:
        result_name = f"decoded_{item.cpp_name}"
        value_name = f"{item.cpp_name}_value"
        w.line(f"const auto {result_name} = ::protocyte::{helper}({args});")
        w.line(f"if (!{result_name}) {{ return {result_name}.status(); }}")
        w.line(f"const auto {value_name} = *{result_name};")
        _emit_closed_enum_reject(
            w,
            item,
            _closed_enum_invalid_condition(item, value_name),
            field_number=error_field_number,
        )
        w.line(f"{target} = {value_name};")
        return None
    result_name = f"decoded_{item.cpp_name}"
    with w.local_decl(result_name):
        w.line(f"const auto {result_name} = ::protocyte::{helper}({args});")
        w.line(f"if (!{result_name}) {{ return {result_name}.status(); }}")
        w.line(f"{target} = *{result_name};")
    return None


def _emit_serialize_statement(
    w: CppWriter, item: FieldModel, options: GeneratorOptions
) -> None:
    condition = _presence(item)
    if item.oneof_name:
        condition = f"{_oneof_case_member(item.oneof_name)} == {_oneof_case_type(item.oneof_name)}::{item.cpp_name}"
    if item.repeated and item.kind != "map":
        value_name = f"{item.cpp_name}_value"
        if item.packed:
            w.line(f"if (!{_member(item)}.empty()) {{")
            w.push()
            _emit_write_packed_field(w, item, _member(item), options)
            w.pop()
            w.line("}")
            return
        w.line(f"for (const auto &{value_name} : {_member(item)}) {{")
        w.push()
        _emit_write_field(w, item, value_name, options)
        w.pop()
        w.line("}")
        return
    if item.kind == "map":
        _emit_write_map(w, item, options)
        return
    w.line(f"if ({condition}) {{")
    w.push()
    _emit_write_field(w, item, _member(item), options)
    w.pop()
    w.line("}")


def _emit_write_field(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    *,
    enum_type: str | None = "FieldNumber",
    error_field_number: str | None = None,
) -> None:
    del options
    field_number = _field_number_u32(item, enum_type)
    error_field_number = error_field_number or field_number
    if _is_scalar_field(item):
        helper = _scalar_write_helper(item, field=True)
        w.line(
            f"if (const auto st = ::protocyte::{helper}(writer, {field_number}, {value}); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
        return
    if item.kind in {"string", "bytes"}:
        helper = _length_delimited_write_helper(item)
        w.line(
            f"if (const auto st = ::protocyte::{helper}(writer, {field_number}, {value}.view()); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
        return
    if item.kind == "message":
        expr = f"*{value}" if value == _member(item) else value
        w.line(
            f"if (const auto st = ::protocyte::write_message_field(writer, {field_number}, {expr}); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
    else:
        w.line(
            f"if (const auto st = ::protocyte::write_tag(writer, {field_number}, {_wire(item)}); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
        _emit_write_scalar(w, item, value, error_field_number)


def _emit_write_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    error_field_number = _field_number_u32(item)
    w.line(f"for (const auto &entry : {_member(item)}) {{")
    with w.indent(), w.cpp_scope():
        w.line("::protocyte::usize entry_payload {};")
        _emit_add_size_status(
            w,
            _field_with_number(item.map_key, 1),
            "entry.key",
            options,
            "entry_payload",
            enum_type=None,
            force_scope=True,
            error_field_number=error_field_number,
        )
        _emit_add_size_status(
            w,
            _field_with_number(item.map_value, 2),
            "entry.value",
            options,
            "entry_payload",
            enum_type=None,
            force_scope=True,
            error_field_number=error_field_number,
        )
        w.line(
            f"if (const auto st = ::protocyte::write_tag(writer, {error_field_number}, ::protocyte::WireType::LEN); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
        w.line(
            f"if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload)); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
        _emit_write_field(
            w,
            _field_with_number(item.map_key, 1),
            "entry.key",
            options,
            enum_type=None,
            error_field_number=error_field_number,
        )
        _emit_write_field(
            w,
            _field_with_number(item.map_value, 2),
            "entry.value",
            options,
            enum_type=None,
            error_field_number=error_field_number,
        )
    w.line("}")


def _emit_write_packed_field(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    *,
    enum_type: str = "FieldNumber",
) -> None:
    del options
    error_field_number = _field_number_u32(item, enum_type)
    packed_name = f"packed_size_{item.cpp_name}"
    w.line(f"::protocyte::usize {packed_name} {{}};")
    width = _fixed_scalar_width(item)
    if width is not None:
        w.line(
            f"const auto {packed_name}_result = ::protocyte::checked_mul({value}.size(), {width});"
        )
        w.line(
            f"if (!{packed_name}_result) {{ return ::protocyte::with_field({packed_name}_result.status(), {error_field_number}); }}"
        )
        w.line(f"{packed_name} = *{packed_name}_result;")
    else:
        packed_value = f"packed_value_{item.cpp_name}"
        w.line(f"for (const auto &{packed_value} : {value}) {{")
        with w.indent(), w.cpp_scope():
            _emit_add_packed_size(
                w,
                item,
                packed_value,
                packed_name,
                result=False,
                error_field_number=error_field_number,
            )
        w.line("}")
    w.line(
        f"if (const auto st = ::protocyte::write_tag(writer, {error_field_number}, ::protocyte::WireType::LEN); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
    )
    w.line(
        f"if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>({packed_name})); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
    )
    if _packed_bulk_fixed_width_size(item) is not None:
        w.line(
            f"if (const auto st = ::protocyte::write_fixed_width_packed_values(writer, {value}.data(), {value}.size()); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
        )
        return
    packed_value = f"packed_value_{item.cpp_name}"
    w.line(f"for (const auto &{packed_value} : {value}) {{")
    with w.indent(), w.cpp_scope():
        _emit_write_scalar(w, item, packed_value, error_field_number)
    w.line("}")


def _emit_write_scalar(
    w: CppWriter, item: FieldModel, value: str, error_field_number: str
) -> None:
    helper = _scalar_write_helper(item, field=False)
    w.line(
        f"if (const auto st = ::protocyte::{helper}(writer, {value}); !st) {{ return ::protocyte::with_field(st, {error_field_number}); }}"
    )


def _emit_size_statement(
    w: CppWriter, item: FieldModel, options: GeneratorOptions
) -> None:
    condition = _presence(item)
    if item.oneof_name:
        condition = f"{_oneof_case_member(item.oneof_name)} == {_oneof_case_type(item.oneof_name)}::{item.cpp_name}"
    if item.repeated and item.kind != "map":
        value_name = f"{item.cpp_name}_value"
        if item.packed:
            packed_name = f"packed_size_{item.cpp_name}"
            w.line(f"if (!{_member(item)}.empty()) {{")
            with w.indent(), w.cpp_scope():
                w.line(f"::protocyte::usize {packed_name} {{}};")
                width = _fixed_scalar_width(item)
                if width is not None:
                    w.line(
                        f"const auto {packed_name}_result = ::protocyte::checked_mul({_member(item)}.size(), {width});"
                    )
                    w.line(
                        f"if (!{packed_name}_result) {{ return ::protocyte::unexpected(::protocyte::with_field({packed_name}_result.error(), {_field_number_u32(item)})); }}"
                    )
                    w.line(f"{packed_name} = *{packed_name}_result;")
                else:
                    w.line(f"for (const auto &{value_name} : {_member(item)}) {{")
                    with w.indent(), w.cpp_scope():
                        _emit_add_packed_size(
                            w,
                            item,
                            value_name,
                            packed_name,
                            result=True,
                            error_field_number=_field_number_u32(item),
                        )
                    w.line("}")
                _emit_size_result_update(
                    w,
                    "total",
                    f"::protocyte::length_delimited_field_size({_field_number_u32(item)}, {packed_name})",
                    result=True,
                    size_name=f"field_size_{item.cpp_name}",
                    error_field_number=_field_number_u32(item),
                )
            w.line("}")
            return
        w.line(f"for (const auto &{value_name} : {_member(item)}) {{")
        with w.indent(), w.cpp_scope():
            _emit_add_size(w, item, value_name, options)
        w.line("}")
        return
    if item.kind == "map":
        _emit_size_map(w, item, options)
        return
    w.line(f"if ({condition}) {{")
    with w.indent(), w.cpp_scope():
        _emit_add_size(w, item, _member(item), options)
    w.line("}")


def _emit_size_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    error_field_number = _field_number_u32(item)
    w.line(f"for (const auto &entry : {_member(item)}) {{")
    with w.indent(), w.cpp_scope():
        w.line("::protocyte::usize entry_payload {};")
        _emit_add_size_status(
            w,
            _field_with_number(item.map_key, 1),
            "entry.key",
            options,
            "entry_payload",
            enum_type=None,
            result=True,
            force_scope=True,
            error_field_number=error_field_number,
        )
        _emit_add_size_status(
            w,
            _field_with_number(item.map_value, 2),
            "entry.value",
            options,
            "entry_payload",
            enum_type=None,
            result=True,
            force_scope=True,
            error_field_number=error_field_number,
        )
        _emit_size_result_update(
            w,
            "total",
            f"::protocyte::length_delimited_field_size({_field_number_u32(item)}, entry_payload)",
            result=True,
            size_name=f"field_size_{item.cpp_name}",
            error_field_number=error_field_number,
        )
    w.line("}")


def _emit_size_result_update(
    w: CppWriter,
    total_name: str,
    result_expr: str,
    *,
    error_return: str | None = None,
    result: bool = False,
    size_name: str | None = None,
    force_scope: bool = False,
    error_field_number: str | None = None,
) -> None:
    if size_name is not None:
        with w.local_decl(size_name, force_scope=force_scope):
            w.line(f"const auto {size_name} = {result_expr};")
            w.line(
                f"if (!{size_name}) {{ return {_size_error_return(size_name, result, error_field_number)}; }}"
            )
            _emit_size_result_update(
                w,
                total_name,
                f"::protocyte::add_size({total_name}, *{size_name})",
                error_return=_size_error_return("st_size", result, error_field_number),
                error_field_number=error_field_number,
            )
        return
    assert error_return is not None
    with w.local_decl("st_size", force_scope=force_scope):
        w.line(f"const auto st_size = {result_expr};")
        w.line(f"if (!st_size) {{ return {error_return}; }}")
        w.line(f"{total_name} = *st_size;")


def _size_error_return(
    result_name: str, result: bool, error_field_number: str | None = None
) -> str:
    if result:
        error = f"{result_name}.error()"
        if error_field_number is not None:
            error = f"::protocyte::with_field({error}, {error_field_number})"
        return f"::protocyte::unexpected({error})"
    status = f"{result_name}.status()"
    if error_field_number is not None:
        status = f"::protocyte::with_field({status}, {error_field_number})"
    return status


def _emit_add_size(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    *,
    enum_type: str | None = "FieldNumber",
    error_field_number: str | None = None,
) -> None:
    del options
    error_field_number = error_field_number or _field_number_u32(item, enum_type)
    if item.kind in {"string", "bytes"}:
        _emit_size_result_update(
            w,
            "total",
            f"::protocyte::length_delimited_field_size({_field_number_u32(item, enum_type)}, {value}.size())",
            result=True,
            size_name=f"field_size_{item.cpp_name}",
            error_field_number=error_field_number,
        )
        return
    elif item.kind == "message":
        expr = f"*{value}" if value == _member(item) else value
        _emit_size_result_update(
            w,
            "total",
            f"::protocyte::message_field_size({_field_number_u32(item, enum_type)}, {expr})",
            result=True,
            size_name=f"field_size_{item.cpp_name}",
            error_field_number=error_field_number,
        )
        return
    else:
        value_size = f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + {_scalar_size(item, value)}"
        _emit_size_result_update(
            w,
            "total",
            f"::protocyte::add_size(total, {value_size})",
            error_return=f"::protocyte::unexpected(::protocyte::with_field(st_size.error(), {error_field_number}))",
            error_field_number=error_field_number,
        )


def _emit_add_size_status(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    total_name: str,
    *,
    enum_type: str | None = "FieldNumber",
    result: bool = False,
    force_scope: bool = False,
    error_field_number: str | None = None,
) -> None:
    error_field_number = error_field_number or _field_number_u32(item, enum_type)
    if item.kind in {"string", "bytes"}:
        _emit_size_result_update(
            w,
            total_name,
            f"::protocyte::length_delimited_field_size({_field_number_u32(item, enum_type)}, {value}.size())",
            result=result,
            size_name=f"field_size_{item.cpp_name}",
            force_scope=force_scope,
            error_field_number=error_field_number,
        )
        return
    if item.kind == "message":
        _emit_size_result_update(
            w,
            total_name,
            f"::protocyte::message_field_size({_field_number_u32(item, enum_type)}, {value})",
            result=result,
            size_name=f"field_size_{item.cpp_name}",
            force_scope=force_scope,
            error_field_number=error_field_number,
        )
        return
    value_size = f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + {_scalar_size(item, value)}"
    _emit_size_result_update(
        w,
        total_name,
        f"::protocyte::add_size({total_name}, {value_size})",
        error_return=_size_error_return("st_size", result, error_field_number),
        force_scope=force_scope,
        error_field_number=error_field_number,
    )


def _emit_add_packed_size(
    w: CppWriter,
    item: FieldModel,
    value: str,
    total_name: str,
    *,
    result: bool,
    error_field_number: str,
) -> None:
    w.line(
        f"const auto st_size = ::protocyte::add_size({total_name}, {_scalar_size(item, value)});"
    )
    w.line(
        f"if (!st_size) {{ return {_size_error_return('st_size', result, error_field_number)}; }}"
    )
    w.line(f"{total_name} = *st_size;")


def _emit_member(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    _emit_documentation(w, item.documentation, options)
    if item.repeated and item.kind != "map":
        w.line(f"{_storage_type(item, options)} {_member(item)};")
        return
    if item.kind == "map":
        assert item.map_key is not None and item.map_value is not None
        w.line(
            f"typename {item.config_cpp_name}::template Map<{_field_type(item.map_key, options)}, {_field_type(item.map_value, options)}> {_member(item)};"
        )
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        if item.recursive_box:
            w.line(
                f"typename {item.config_cpp_name}::template Box<{typ}> {_member(item)};"
            )
        else:
            w.line(
                f"typename {item.config_cpp_name}::template Optional<{typ}> {_member(item)};"
            )
        return
    if item.kind == "bytes" and item.array_enabled:
        w.line(f"{_storage_type(item, options)} {_member(item)};")
        if _has_presence_flag(item):
            w.line(f"bool has_{item.cpp_name}_ {{}};")
        return
    if item.kind in {"string", "bytes"}:
        w.line(f"{_field_type(item, options)} {_member(item)};")
        if _has_presence_flag(item):
            w.line(f"bool has_{item.cpp_name}_ {{}};")
        return
    w.line(f"{_field_type(item, options)} {_member(item)}{{}};")
    if _has_presence_flag(item):
        w.line(f"bool has_{item.cpp_name}_ {{}};")


def _emit_oneof_member(
    w: CppWriter, item: FieldModel, options: GeneratorOptions
) -> None:
    _emit_documentation(w, item.documentation, options)
    w.line(f"{_storage_type(item, options)} {_oneof_member_name(item)};")


def _emit_destroy_oneof_member(w: CppWriter, item: FieldModel) -> None:
    if item.kind in {"string", "bytes", "message"}:
        w.line(f"destroy_at_(&{_member(item)});")


def _emit_oneof_storage(
    w: CppWriter, oneof: OneofModel, options: GeneratorOptions
) -> None:
    storage_type = _oneof_storage_type(oneof)
    w.line(f"union {storage_type} {{")
    with w.indent():
        w.line(f"{storage_type}() noexcept {{}}")
        w.line(f"~{storage_type}() noexcept {{}}")
        for item in oneof.fields:
            _emit_oneof_member(w, item, options)
    w.line(f"}} {_oneof_storage_member(oneof.name)};")


def _storage_type(item: FieldModel, options: GeneratorOptions) -> str:
    if item.repeated and item.kind != "map":
        if item.repeated_array and item.array_max is not None:
            return f"::protocyte::Array<{_element_type(item, options)}, {_array_max_literal(item)}>"
        return f"typename {item.config_cpp_name}::template Vector<{_element_type(item, options)}>"
    if item.kind == "map":
        assert item.map_key is not None and item.map_value is not None
        return f"typename {item.config_cpp_name}::template Map<{_field_type(item.map_key, options)}, {_field_type(item.map_value, options)}>"
    if item.kind == "message":
        typ = _field_type(item, options)
        if item.recursive_box:
            return f"typename {item.config_cpp_name}::template Box<{typ}>"
        return f"typename {item.config_cpp_name}::template Optional<{typ}>"
    if item.fixed_bytes and item.array_max is not None:
        return f"::protocyte::FixedByteArray<{_array_max_literal(item)}>"
    if item.kind == "bytes" and item.array_enabled and item.array_max is not None:
        return f"::protocyte::ByteArray<{_array_max_literal(item)}>"
    return _field_type(item, options)


def _has_presence_flag(item: FieldModel) -> bool:
    return item.proto3_optional and item.kind != "message" and not item.fixed_bytes


def _field_with_number(item: FieldModel, number: int) -> FieldModel:
    return FieldModel(
        name=item.name,
        cpp_name=item.cpp_name,
        number=number,
        proto_type=item.proto_type,
        label=item.label,
        file_name=item.file_name,
        repeated=False,
        proto3_optional=False,
        oneof_index=None,
        oneof_name=None,
        packed=False,
        deprecated=item.deprecated,
        type_name=item.type_name,
        kind=item.kind,
        cpp_type=item.cpp_type,
        message_type=item.message_type,
        enum_type=item.enum_type,
        map_key=item.map_key,
        map_value=item.map_value,
        recursive_box=item.recursive_box,
        array_max=item.array_max,
        array_expr=item.array_expr,
        array_cpp_max=item.array_cpp_max,
        array_fixed=item.array_fixed,
        explicit_presence=False,
        required=False,
        default_cpp=item.default_cpp,
        default_byte_size=item.default_byte_size,
        config_cpp_name=item.config_cpp_name,
        reader_cpp_name=item.reader_cpp_name,
        writer_cpp_name=item.writer_cpp_name,
        value_cpp_name=item.value_cpp_name,
        generic_cpp_name=item.generic_cpp_name,
    )


def _field_type(item: FieldModel, options: GeneratorOptions) -> str:
    if item.kind == "message":
        assert item.message_type is not None
        return f"{_qualified_name(item.message_type.package, item.message_type.cpp_name, options)}<{item.config_cpp_name}>"
    if item.kind == "string":
        return f"typename {item.config_cpp_name}::String"
    if item.kind == "bytes":
        return f"typename {item.config_cpp_name}::Bytes"
    if item.kind == "enum":
        return "::protocyte::i32"
    return _runtime_scalar_type(SCALAR_CPP_TYPES[item.proto_type])


def _enum_type(enum: EnumModel | None, options: GeneratorOptions) -> str:
    if enum is None:
        return "::protocyte::i32"
    return _qualified_name(enum.package, enum.cpp_name, options)


def _element_type(item: FieldModel, options: GeneratorOptions) -> str:
    return _field_type(item, options)


def _default(item: FieldModel) -> str:
    if item.default_cpp is not None:
        return item.default_cpp
    if item.kind == "enum":
        return "0"
    return SCALAR_DEFAULTS.get(item.proto_type, "{}")


def _closed_enum_invalid_condition(item: FieldModel, value_expr: str) -> str | None:
    if not item.enum_closed or item.enum_type is None:
        return None
    if not item.enum_type.values:
        return "true"
    return " && ".join(
        f"{value_expr} != {value.number}" for value in item.enum_type.values
    )


def _emit_closed_enum_reject(
    w: CppWriter,
    item: FieldModel,
    condition: str | None,
    *,
    field_number: str | None = None,
) -> None:
    if condition is None:
        return
    field_arg = field_number or _field_number_u32(item)
    w.line(f"if ({condition}) {{")
    with w.indent():
        w.line(
            f"return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {{}}, {field_arg});"
        )
    w.line("}")


def _field_number_name(item: FieldModel) -> str:
    return item.cpp_name


def _field_number_u32(item: FieldModel, enum_type: str | None = "FieldNumber") -> str:
    if enum_type is None:
        return f"{item.number}u"
    return f"static_cast<::protocyte::u32>({enum_type}::{_field_number_name(item)})"


def _member(item: FieldModel) -> str:
    if item.oneof_name is not None:
        return f"{_oneof_storage_member(item.oneof_name)}.{_oneof_member_name(item)}"
    return f"{item.cpp_name}_"


def _oneof_case_type(oneof_name: str) -> str:
    return f"{cpp_pascal_identifier(oneof_name)}Case"


def _oneof_case_member(oneof_name: str) -> str:
    return f"{cpp_derivable_identifier(oneof_name)}_case_"


def _oneof_storage_type(oneof: OneofModel) -> str:
    return f"{oneof.cpp_name}Storage"


def _oneof_storage_member(oneof_name: str) -> str:
    return f"{cpp_derivable_identifier(oneof_name)}_"


def _oneof_member_name(item: FieldModel) -> str:
    return f"{item.cpp_name}_"


def _array_max_literal(item: FieldModel) -> str:
    if item.array_cpp_max:
        return item.array_cpp_max
    assert item.array_max is not None
    return f"{item.array_max}u"


def _wire(item: FieldModel) -> str:
    if item.kind in {"string", "bytes", "message", "map"}:
        return "::protocyte::WireType::LEN"
    if item.proto_type in {
        FieldDescriptorProto.TYPE_DOUBLE,
        FieldDescriptorProto.TYPE_FIXED64,
        FieldDescriptorProto.TYPE_SFIXED64,
    }:
        return "::protocyte::WireType::I64"
    if item.proto_type in {
        FieldDescriptorProto.TYPE_FLOAT,
        FieldDescriptorProto.TYPE_FIXED32,
        FieldDescriptorProto.TYPE_SFIXED32,
    }:
        return "::protocyte::WireType::I32"
    return "::protocyte::WireType::VARINT"


def _presence(item: FieldModel) -> str:
    if item.fixed_bytes:
        return f"{_member(item)}.has_value()"
    if item.kind == "message":
        return f"{_member(item)}.has_value()"
    if _has_presence_flag(item):
        return f"has_{item.cpp_name}_"
    if item.kind in {"string", "bytes"}:
        return f"!{_member(item)}.empty()"
    if item.kind == "enum":
        return f"{_member(item)} != 0"
    if item.proto_type == FieldDescriptorProto.TYPE_BOOL:
        return _member(item)
    if item.proto_type == FieldDescriptorProto.TYPE_FLOAT:
        return f"::std::bit_cast<::protocyte::u32>({_member(item)}) != 0u"
    if item.proto_type == FieldDescriptorProto.TYPE_DOUBLE:
        return f"::std::bit_cast<::protocyte::u64>({_member(item)}) != 0u"
    return f"{_member(item)} != {_default(item)}"


def _scalar_size(item: FieldModel, value: str) -> str:
    width = _fixed_scalar_width(item)
    if width is not None:
        return width
    return _varint_size_expr(item, value)


def _varint_size_expr(item: FieldModel, value: str) -> str:
    if item.proto_type == FieldDescriptorProto.TYPE_SINT32:
        return f"::protocyte::varint_size(::protocyte::encode_zigzag32({value}))"
    if item.proto_type == FieldDescriptorProto.TYPE_SINT64:
        return f"::protocyte::varint_size(::protocyte::encode_zigzag64({value}))"
    if item.proto_type == FieldDescriptorProto.TYPE_UINT64:
        return f"::protocyte::varint_size({value})"
    return f"::protocyte::varint_size(static_cast<::protocyte::u64>({value}))"


def _fixed_scalar_width(item: FieldModel) -> str | None:
    if item.proto_type in {
        FieldDescriptorProto.TYPE_DOUBLE,
        FieldDescriptorProto.TYPE_FIXED64,
        FieldDescriptorProto.TYPE_SFIXED64,
    }:
        return "8u"
    if item.proto_type in {
        FieldDescriptorProto.TYPE_FLOAT,
        FieldDescriptorProto.TYPE_FIXED32,
        FieldDescriptorProto.TYPE_SFIXED32,
    }:
        return "4u"
    return None


def _is_scalar_field(item: FieldModel) -> bool:
    return item.kind not in {"string", "bytes", "message", "map"}


def _uses_runtime_len_field_helper(item: FieldModel) -> bool:
    return item.kind in {"string", "bytes"} and not (
        item.kind == "bytes" and item.array_enabled
    )


def _length_delimited_read_helper(item: FieldModel, *, checked: bool) -> str:
    base = "read_string" if item.kind == "string" else "read_bytes"
    return f"{base}_field" if checked else base


def _length_delimited_write_helper(item: FieldModel) -> str:
    return "write_string_field" if item.kind == "string" else "write_bytes_field"


def _scalar_read_helper(item: FieldModel, *, checked: bool) -> str:
    helper = _SCALAR_READ_HELPERS[item.proto_type]
    return f"{helper}_field" if checked else helper


def _scalar_write_helper(item: FieldModel, *, field: bool) -> str:
    helper = _SCALAR_WRITE_HELPERS[item.proto_type]
    return f"{helper}_field" if field else helper


def _runtime_scalar_type(cpp_type: str) -> str:
    return _RUNTIME_SCALAR_TYPES.get(cpp_type, cpp_type)


def _emit_string_view_accessor(
    w: CppWriter,
    item: FieldModel,
    options: GeneratorOptions,
    expr: str,
) -> None:
    _emit_field_api_annotations(w, item, options)
    w.line(
        f"::protocyte::StringView {item.cpp_name}() const noexcept {{ return {expr}; }}"
    )


def _file_uses_numeric_limits(file_model: FileModel) -> bool:
    for message in _walk_messages(file_model.messages):
        if any(
            field.default_cpp is not None
            and "::std::numeric_limits" in field.default_cpp
            for field in message.fields
        ):
            return True
    return False


def _ordered_messages(file_model: FileModel) -> list[MessageModel]:
    all_messages = [
        item for item in _walk_messages(file_model.messages) if not item.is_map_entry
    ]
    by_name = {item.full_name: item for item in all_messages}
    ordered: list[MessageModel] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(message: MessageModel) -> None:
        if message.full_name in visited or message.full_name in visiting:
            return
        visiting.add(message.full_name)
        for item in message.fields:
            if (
                item.message_type is not None
                and item.message_type.full_name in by_name
                and not item.recursive_box
            ):
                visit(item.message_type)
            if item.map_value is not None and item.map_value.message_type is not None:
                target = item.map_value.message_type
                if target.full_name in by_name:
                    visit(target)
        visiting.remove(message.full_name)
        visited.add(message.full_name)
        ordered.append(message)

    for item in all_messages:
        visit(item)
    return ordered


def _walk_messages(messages: list[MessageModel]):
    for message in messages:
        if not message.is_map_entry:
            yield message
        yield from _walk_messages(message.nested_messages)


def _header_name(proto_name: str, options: GeneratorOptions) -> str:
    return (
        generated_file_base(
            proto_name,
            max_output_path_bytes=options.generated_path_max_bytes,
            max_output_directory_bytes=options.generated_directory_max_bytes,
        )
        + ".hpp"
    )


def _source_name(proto_name: str, options: GeneratorOptions) -> str:
    return (
        generated_file_base(
            proto_name,
            max_output_path_bytes=options.generated_path_max_bytes,
            max_output_directory_bytes=options.generated_directory_max_bytes,
        )
        + ".cpp"
    )


def _include_path(proto_name: str, options: GeneratorOptions) -> str:
    path = _header_name(proto_name, options)
    return f"{options.include_prefix}/{path}" if options.include_prefix else path


def _include_guard(proto_name: str) -> str:
    raw_sanitized = "".join(
        ch if ch.isascii() and ch.isalnum() else "_" for ch in proto_name.upper()
    )
    sanitized = "_".join(part for part in raw_sanitized.split("_") if part) or "FILE"
    digest = hashlib.sha1(proto_name.encode("utf-8")).hexdigest().upper()[:12]
    return f"PROTOCYTE_GENERATED_{sanitized}_{digest}_HPP"


def _cpp_suffix_identifier(identifier: str, suffix: str) -> str:
    if identifier.endswith("_"):
        # A second underscore would be reserved to the implementation, while
        # omitting it makes Foo and Foo_ collide.  Moving the separator after
        # the suffix is portable and makes the two output domains disjoint:
        # ordinary identifiers end in ``_{suffix}``, escaped ones in
        # ``_{suffix}_``.
        return f"{identifier}{suffix}_"
    return f"{identifier}_{suffix}"


def _namespace_parts(file_model: FileModel, options: GeneratorOptions) -> list[str]:
    parts: list[str] = []
    if options.namespace_prefix:
        parts.extend(options.namespace_prefix.split("::"))
    if file_model.package:
        parts.extend(cpp_identifier(part) for part in file_model.package.split("."))
    return parts


def _qualified_name(package: str, cpp_name: str, options: GeneratorOptions) -> str:
    parts: list[str] = []
    if options.namespace_prefix:
        parts.extend(options.namespace_prefix.split("::"))
    if package:
        parts.extend(cpp_identifier(part) for part in package.split("."))
    parts.append(cpp_name)
    return "::" + "::".join(parts)


def _open_namespace(w: CppWriter, parts: list[str]) -> None:
    if parts:
        w.line(f"namespace {'::'.join(parts)} {{")
        w.line()


def _close_namespace(w: CppWriter, parts: list[str]) -> None:
    if parts:
        w.line()
        w.line(f"}}  // namespace {'::'.join(parts)}")


def _cpp_bool(value: bool) -> str:
    return "true" if value else "false"
