"""Fresh Windows path operations, never an operation-wide lease.

Each projection opens the entire existing path with OBJ_DONT_REPARSE, reads that
handle and closes it before returning. No filesystem facts are cached. Missing
components are searched again on every call. This module grants no ownership or
mutation authority; the coordinator verifies the observation scope separately.
"""

from __future__ import annotations

import ctypes
import os
from pathlib import Path


class ObservationUnavailable(RuntimeError):
    """The native observation contract is unavailable; use the reference path."""


class UnsafeObservation(RuntimeError):
    """An observed path is unsafe or changed during observation."""


class FreshPathObserver:
    """Own native call bindings, not observations, for one validation phase."""

    def __init__(self) -> None:
        contract = globals().get("PATH_CONTRACT_VERSION")
        if type(contract) is not int or contract != 1:
            raise ObservationUnavailable("incomplete path helper installation")
        if os.name != "nt":
            raise ObservationUnavailable("native path observation requires Windows")
        from ctypes import wintypes as w

        class UnicodeString(ctypes.Structure):
            _fields_ = [
                ("Length", w.USHORT),
                ("MaximumLength", w.USHORT),
                ("Buffer", w.LPWSTR),
            ]

        class ObjectAttributes(ctypes.Structure):
            _fields_ = [
                ("Length", w.ULONG),
                ("RootDirectory", w.HANDLE),
                ("ObjectName", ctypes.POINTER(UnicodeString)),
                ("Attributes", w.ULONG),
                ("SecurityDescriptor", w.LPVOID),
                ("SecurityQualityOfService", w.LPVOID),
            ]

        class IoStatusBlock(ctypes.Structure):
            _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]

        class AttributeTagInfo(ctypes.Structure):
            _fields_ = [("Attributes", w.DWORD), ("ReparseTag", w.DWORD)]

        self._w = w
        self._unicode = UnicodeString
        self._attributes = ObjectAttributes
        self._status = IoStatusBlock
        self._tag = AttributeTagInfo
        self._nt = ctypes.WinDLL("ntdll", use_last_error=True)
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._open = self._nt.NtCreateFile
        self._open.argtypes = (
            ctypes.POINTER(w.HANDLE),
            w.DWORD,
            ctypes.POINTER(ObjectAttributes),
            ctypes.POINTER(IoStatusBlock),
            w.LPVOID,
            w.ULONG,
            w.ULONG,
            w.ULONG,
            w.ULONG,
            w.LPVOID,
            w.ULONG,
        )
        self._open.restype = w.LONG
        self._dos_error = self._nt.RtlNtStatusToDosError
        self._dos_error.argtypes = (w.LONG,)
        self._dos_error.restype = w.ULONG
        self._info = self._kernel.GetFileInformationByHandleEx
        self._info.argtypes = (w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD)
        self._info.restype = w.BOOL
        self._final = self._kernel.GetFinalPathNameByHandleW
        self._final.argtypes = (w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD)
        self._final.restype = w.DWORD
        self._close = self._kernel.CloseHandle
        self._close.argtypes = (w.HANDLE,)
        self._close.restype = w.BOOL
        self._closed = False
        self.projections = 0
        self.open_calls = 0
        self.information_calls = 0
        self.final_path_calls = 0
        self.handles_opened = 0
        self.handles_closed = 0

    def close(self) -> None:
        self._closed = True
        if self.handles_opened != self.handles_closed:
            raise UnsafeObservation("native observation leaked a handle")

    @staticmethod
    def _native_name(path: Path) -> str:
        text = os.fspath(path)
        if text.startswith("\\\\?\\"):
            # Path.resolve preserves an explicitly supplied namespace prefix.
            # Stripping it would alter the existing ownership-key spelling.
            raise ObservationUnavailable("explicit namespaces use reference validation")
        # Deliberately narrow capability boundary. Device names, UNC shares and
        # alternate data streams use reference validation, without new user flags.
        if (
            not path.is_absolute()
            or len(text) < 3
            or not text[0].isascii()
            or not text[0].isalpha()
            or text[1:3] != ":\\"
            or ":" in text[2:]
            or any(character in text for character in ("\x00", "\r", "\n"))
        ):
            raise ObservationUnavailable("path needs the portable reference reader")
        return "\\??\\" + text

    def _invoke_open(self, handle, *arguments):
        try:
            return self._open(ctypes.byref(handle), *arguments)
        except BaseException:
            # A foreign call can raise after the OS wrote its output handle.
            # It has not been published to any caller yet; retire it exactly
            # once before propagating the error or permitting reference work.
            if handle.value:
                try:
                    self.handles_opened += 1
                finally:
                    if not self._close(handle):
                        raise UnsafeObservation("interrupted open could not release its handle")
                    self.handles_closed += 1
            raise

    def _open_existing(self, path: Path):
        text = self._native_name(path)
        encoded_length = len(text.encode("utf-16-le"))
        if encoded_length > 65532:
            raise ObservationUnavailable("path exceeds the native Unicode name limit")
        storage = ctypes.create_unicode_buffer(text)
        name = self._unicode(
            encoded_length,
            encoded_length + 2,
            ctypes.cast(storage, self._w.LPWSTR),
        )
        attributes = self._attributes(
            ctypes.sizeof(self._attributes),
            None,
            ctypes.pointer(name),
            0x1040,  # OBJ_DONT_REPARSE | OBJ_CASE_INSENSITIVE
            None,
            None,
        )
        status = self._status()
        handle = self._w.HANDLE()
        self.open_calls += 1
        result = self._invoke_open(
            handle,
            0x100080,  # SYNCHRONIZE | FILE_READ_ATTRIBUTES
            ctypes.byref(attributes),
            ctypes.byref(status),
            None,
            0,
            7,  # share read/write/delete; no claim of a topology freeze
            1,  # FILE_OPEN, never create anything
            0x20,  # FILE_SYNCHRONOUS_IO_NONALERT; no incompatible DIRECTORY flags
            None,
            0,
        )
        code = result & 0xFFFFFFFF
        if code in (0xC0000034, 0xC000003A):  # name/path not found
            return None
        if code in (0xC000050B, 0xC0000279, 0xC0000280):
            raise UnsafeObservation("filesystem path contains a reparse point")
        if result < 0:
            # Do not reinterpret permission/sharing/invalid-name failures as
            # missing components. The caller can only fall back to reference.
            raise ctypes.WinError(self._dos_error(result))
        if not handle.value:
            raise UnsafeObservation("native open returned an unsupported result")
        self.handles_opened += 1
        if code != 0:
            if not self._close(handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handles_closed += 1
            raise UnsafeObservation("native open returned an unsupported result")
        return handle

    def _describe(self, handle, *, leaf_may_be_file: bool) -> Path:
        tag = self._tag()
        self.information_calls += 1
        if not self._info(handle, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
            raise ctypes.WinError(ctypes.get_last_error())
        if tag.Attributes & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT, any tag
            raise UnsafeObservation("filesystem path contains a reparse point")
        if not tag.Attributes & 0x10 and not leaf_may_be_file:
            raise UnsafeObservation("filesystem path has a non-directory ancestor")
        capacity = 512
        for _ in range(3):
            buffer = ctypes.create_unicode_buffer(capacity)
            self.final_path_calls += 1
            size = self._final(handle, buffer, capacity, 0)
            if not size:
                raise ctypes.WinError(ctypes.get_last_error())
            if size < capacity:
                value = buffer.value
                if not value.startswith("\\\\?\\") or value.startswith("\\\\?\\UNC\\"):
                    raise ObservationUnavailable("unsupported final path namespace")
                return Path(os.path.normpath(value[4:]))
            capacity = size + 1
        raise UnsafeObservation("native final path changed repeatedly")

    def project(self, path: Path, *, leaf_may_be_file: bool = False) -> Path:
        if self._closed:
            raise UnsafeObservation("filesystem observation used outside its scope")
        self.projections += 1
        path = Path(os.path.normpath(path))
        self._native_name(path)
        # Fresh on every call. In particular, there is no negative lookup cache
        # and no retained ancestor handle that could lose its name binding.
        for _ in range(8):
            current = path
            missing: list[str] = []
            while True:
                handle = self._open_existing(current)
                if handle is not None:
                    break
                if current.parent == current:
                    raise UnsafeObservation("could not observe an existing ancestor")
                missing.append(current.name)
                current = current.parent
            try:
                projected = self._describe(
                    handle, leaf_may_be_file=leaf_may_be_file and not missing
                )
            except FileNotFoundError:
                continue
            finally:
                if not self._close(handle):
                    raise ctypes.WinError(ctypes.get_last_error())
                self.handles_closed += 1
            for component in reversed(missing):
                if component in ("", ".", ".."):
                    raise UnsafeObservation("unsafe missing path component")
                projected /= component
            return projected
        raise UnsafeObservation("filesystem path changed repeatedly while observing")

    def metrics(self) -> dict[str, int]:
        return {
            "native_projections": self.projections,
            "native_open_calls": self.open_calls,
            "native_information_calls": self.information_calls,
            "native_final_path_calls": self.final_path_calls,
            "native_handles_opened": self.handles_opened,
            "native_handles_closed": self.handles_closed,
        }


# EOF capability marker; an incomplete installed source cannot advertise it.
PATH_CONTRACT_VERSION = 1
