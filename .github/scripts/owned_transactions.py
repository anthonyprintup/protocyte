from __future__ import annotations

import errno
import ctypes
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Iterator


_MARKER_SCHEMA = 6
_JOURNAL_SCHEMA = 1
_STATE_DIRECTORY_ENV = "PROTOCYTE_TRANSACTION_STATE_DIR"
# v7 separates the stable owner lease from an atomic, checksummed state journal.
_STATE_DIRECTORY_NAME = "protocyte-owned-transactions-v7"
_REGISTRY_LOCK_NAME = "registry.lock"
_DESTINATION_STATE_SUFFIX = ".destination"
_DESTINATION_LOCK_NAME = "destination.lock"
_OWNED_SIBLING_LABEL = "sibling"
_JOURNAL_GENERATION_WIDTH = 20
_JOURNAL_RETAINED_GENERATIONS = 2


if os.name == "nt":
    import msvcrt
    from ctypes import wintypes

    _ERROR_ALREADY_EXISTS = 183
    _ERROR_FILE_NOT_FOUND = 2
    _ERROR_PATH_NOT_FOUND = 3
    _ERROR_NO_MORE_FILES = 18
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _DELETE = 0x00010000
    _READ_CONTROL = 0x00020000
    _SYNCHRONIZE = 0x00100000
    _FILE_LIST_DIRECTORY = 0x00000001
    _FILE_READ_ATTRIBUTES = 0x00000080
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _CREATE_NEW = 1
    _OPEN_EXISTING = 3
    _OPEN_ALWAYS = 4
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
    _FILE_ID_INFO_CLASS = 18
    _FILE_ID_EXTD_DIRECTORY_INFO_CLASS = 19
    _FILE_ID_EXTD_DIRECTORY_RESTART_INFO_CLASS = 20
    _FILE_RENAME_INFO_CLASS = 3
    _FILE_DISPOSITION_INFO_CLASS = 4
    _FILE_DISPOSITION_INFO_EX_CLASS = 21
    _FILE_DISPOSITION_FLAG_DELETE = 0x00000001
    _FILE_DISPOSITION_FLAG_POSIX_SEMANTICS = 0x00000002
    _FILE_DISPOSITION_FLAG_IGNORE_READONLY_ATTRIBUTE = 0x00000010
    _NT_FILE_CREATE = 2
    _NT_FILE_OPEN = 1
    _FILE_DIRECTORY_FILE = 0x00000001
    _FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
    _NT_FILE_OPEN_REPARSE_POINT = 0x00200000
    _OBJ_CASE_INSENSITIVE = 0x00000040
    _MOVEFILE_WRITE_THROUGH = 0x00000008
    _SE_FILE_OBJECT = 1
    _OWNER_SECURITY_INFORMATION = 0x00000001
    _DACL_SECURITY_INFORMATION = 0x00000004
    _ACL_SIZE_INFORMATION_CLASS = 2
    _TOKEN_QUERY = 0x0008
    _TOKEN_USER_CLASS = 1
    _SDDL_REVISION_1 = 1
    _ACCESS_ALLOWED_ACE_TYPES = frozenset({0, 4, 5, 9, 11})
    _ACCESS_ALLOWED_COMPOUND_ACE_TYPE = 4
    _OBJECT_ACE_TYPES = frozenset({5, 6, 7, 8, 11, 12, 13, 15})
    _ACE_OBJECT_TYPE_PRESENT = 0x00000001
    _ACE_INHERITED_OBJECT_TYPE_PRESENT = 0x00000002

    class _WindowsSecurityAttributes(ctypes.Structure):
        _fields_ = (
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", wintypes.LPVOID),
            ("bInheritHandle", wintypes.BOOL),
        )

    class _WindowsFileAttributeTagInfo(ctypes.Structure):
        _fields_ = (
            ("FileAttributes", wintypes.DWORD),
            ("ReparseTag", wintypes.DWORD),
        )

    class _WindowsFileId128(ctypes.Structure):
        _fields_ = (("Identifier", ctypes.c_ubyte * 16),)

    class _WindowsFileIdInfo(ctypes.Structure):
        _fields_ = (
            ("VolumeSerialNumber", ctypes.c_uint64),
            ("FileId", _WindowsFileId128),
        )

    class _WindowsUnicodeString(ctypes.Structure):
        _fields_ = (
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        )

    class _WindowsObjectAttributes(ctypes.Structure):
        _fields_ = (
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(_WindowsUnicodeString)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", wintypes.LPVOID),
            ("SecurityQualityOfService", wintypes.LPVOID),
        )

    class _WindowsIoStatusBlock(ctypes.Structure):
        _fields_ = (("Status", wintypes.LPVOID), ("Information", ctypes.c_size_t))

    class _WindowsFileRenameInfo(ctypes.Structure):
        _fields_ = (
            ("Flags", wintypes.DWORD),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        )

    class _WindowsFileDispositionInfo(ctypes.Structure):
        _fields_ = (("DeleteFile", wintypes.BOOL),)

    class _WindowsFileDispositionInfoEx(ctypes.Structure):
        _fields_ = (("Flags", wintypes.DWORD),)

    class _WindowsFileIdExtdDirectoryInfo(ctypes.Structure):
        _fields_ = (
            ("NextEntryOffset", wintypes.DWORD),
            ("FileIndex", wintypes.DWORD),
            ("CreationTime", ctypes.c_int64),
            ("LastAccessTime", ctypes.c_int64),
            ("LastWriteTime", ctypes.c_int64),
            ("ChangeTime", ctypes.c_int64),
            ("EndOfFile", ctypes.c_int64),
            ("AllocationSize", ctypes.c_int64),
            ("FileAttributes", wintypes.DWORD),
            ("FileNameLength", wintypes.DWORD),
            ("EaSize", wintypes.DWORD),
            ("ReparsePointTag", wintypes.DWORD),
            ("FileId", _WindowsFileId128),
            ("FileName", wintypes.WCHAR * 1),
        )

    class _WindowsAclSizeInformation(ctypes.Structure):
        _fields_ = (
            ("AceCount", wintypes.DWORD),
            ("AclBytesInUse", wintypes.DWORD),
            ("AclBytesFree", wintypes.DWORD),
        )

    class _WindowsAceHeader(ctypes.Structure):
        _fields_ = (
            ("AceType", ctypes.c_ubyte),
            ("AceFlags", ctypes.c_ubyte),
            ("AceSize", wintypes.WORD),
        )

    class _WindowsTokenUser(ctypes.Structure):
        _fields_ = (("Sid", wintypes.LPVOID), ("Attributes", wintypes.DWORD))

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CreateDirectoryW.argtypes = (
        wintypes.LPCWSTR,
        ctypes.POINTER(_WindowsSecurityAttributes),
    )
    _kernel32.CreateDirectoryW.restype = wintypes.BOOL
    _kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_WindowsSecurityAttributes),
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    _kernel32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
    _kernel32.LocalFree.restype = wintypes.HLOCAL
    _kernel32.MoveFileExW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
    )
    _kernel32.MoveFileExW.restype = wintypes.BOOL
    _kernel32.SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.SetFileInformationByHandle.restype = wintypes.BOOL

    _ntdll.NtCreateFile.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_WindowsObjectAttributes),
        ctypes.POINTER(_WindowsIoStatusBlock),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    )
    _ntdll.NtCreateFile.restype = ctypes.c_long
    _ntdll.RtlNtStatusToDosError.argtypes = (ctypes.c_long,)
    _ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG

    _advapi32.ConvertSidToStringSidW.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.LPWSTR),
    )
    _advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.DWORD),
    )
    _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = (
        wintypes.BOOL
    )
    _advapi32.EqualSid.argtypes = (wintypes.LPVOID, wintypes.LPVOID)
    _advapi32.EqualSid.restype = wintypes.BOOL
    _advapi32.GetAce.argtypes = (
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
    )
    _advapi32.GetAce.restype = wintypes.BOOL
    _advapi32.GetAclInformation.argtypes = (
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.c_int,
    )
    _advapi32.GetAclInformation.restype = wintypes.BOOL
    _advapi32.GetLengthSid.argtypes = (wintypes.LPVOID,)
    _advapi32.GetLengthSid.restype = wintypes.DWORD
    _advapi32.GetSecurityInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.LPVOID),
    )
    _advapi32.GetSecurityInfo.restype = wintypes.DWORD
    _advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _advapi32.GetTokenInformation.restype = wintypes.BOOL
    _advapi32.IsValidSid.argtypes = (wintypes.LPVOID,)
    _advapi32.IsValidSid.restype = wintypes.BOOL
    _advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    _advapi32.OpenProcessToken.restype = wintypes.BOOL


@contextmanager
def _windows_private_security_attributes() -> Iterator[object]:
    if os.name != "nt":
        raise RuntimeError("Windows security attributes requested on another platform")

    token = wintypes.HANDLE()
    if not _advapi32.OpenProcessToken(
        _kernel32.GetCurrentProcess(), _TOKEN_QUERY, ctypes.byref(token)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        required = wintypes.DWORD()
        _advapi32.GetTokenInformation(
            token, _TOKEN_USER_CLASS, None, 0, ctypes.byref(required)
        )
        buffer = ctypes.create_string_buffer(required.value)
        if not _advapi32.GetTokenInformation(
            token,
            _TOKEN_USER_CLASS,
            buffer,
            required,
            ctypes.byref(required),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        user_sid = ctypes.cast(buffer, ctypes.POINTER(_WindowsTokenUser)).contents.Sid
        sid_string = wintypes.LPWSTR()
        if not _advapi32.ConvertSidToStringSidW(user_sid, ctypes.byref(sid_string)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            sddl = (
                f"O:{sid_string.value}D:P"
                "(A;;FA;;;SY)(A;;FA;;;BA)"
                f"(A;;FA;;;{sid_string.value})"
            )
        finally:
            _kernel32.LocalFree(sid_string)

        descriptor = wintypes.LPVOID()
        if not _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl,
            _SDDL_REVISION_1,
            ctypes.byref(descriptor),
            None,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            attributes = _WindowsSecurityAttributes(
                ctypes.sizeof(_WindowsSecurityAttributes), descriptor, False
            )
            yield attributes
        finally:
            _kernel32.LocalFree(descriptor)
    finally:
        _kernel32.CloseHandle(token)


def _windows_current_user_sid() -> bytes:
    token = wintypes.HANDLE()
    if not _advapi32.OpenProcessToken(
        _kernel32.GetCurrentProcess(), _TOKEN_QUERY, ctypes.byref(token)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        required = wintypes.DWORD()
        _advapi32.GetTokenInformation(
            token, _TOKEN_USER_CLASS, None, 0, ctypes.byref(required)
        )
        buffer = ctypes.create_string_buffer(required.value)
        if not _advapi32.GetTokenInformation(
            token,
            _TOKEN_USER_CLASS,
            buffer,
            required,
            ctypes.byref(required),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(_WindowsTokenUser)).contents.Sid
        return ctypes.string_at(sid, _advapi32.GetLengthSid(sid))
    finally:
        _kernel32.CloseHandle(token)


def _windows_sid_from_string(value: str) -> bytes:
    sid = wintypes.LPVOID()
    convert = _advapi32.ConvertStringSidToSidW
    convert.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPVOID))
    convert.restype = wintypes.BOOL
    if not convert(value, ctypes.byref(sid)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(sid, _advapi32.GetLengthSid(sid))
    finally:
        _kernel32.LocalFree(sid)


def _windows_validate_private_handle(
    handle: object,
    path: Path,
    *,
    directory: bool,
) -> None:
    info = _WindowsFileAttributeTagInfo()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    if info.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        if directory:
            raise RuntimeError(
                f"refusing to use a linked transaction state directory: {path}"
            )
        raise RuntimeError(f"refusing to use a linked transaction state entry: {path}")
    is_directory = bool(info.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY)
    if is_directory != directory:
        expected = "directory" if directory else "regular file"
        raise RuntimeError(f"transaction state entry is not a {expected}: {path}")

    owner = wintypes.LPVOID()
    dacl = wintypes.LPVOID()
    descriptor = wintypes.LPVOID()
    result = _advapi32.GetSecurityInfo(
        handle,
        _SE_FILE_OBJECT,
        _OWNER_SECURITY_INFORMATION | _DACL_SECURITY_INFORMATION,
        ctypes.byref(owner),
        None,
        ctypes.byref(dacl),
        None,
        ctypes.byref(descriptor),
    )
    if result:
        raise ctypes.WinError(result)
    try:
        current_user = _windows_current_user_sid()
        if (
            not owner
            or ctypes.string_at(owner, _advapi32.GetLengthSid(owner)) != current_user
        ):
            raise RuntimeError(
                f"transaction state entry is not owned by the current user: {path}"
            )
        if not dacl:
            raise RuntimeError(
                f"transaction state entry must have a private Windows ACL: {path}"
            )

        # SYSTEM and administrators are trusted machine principals; Windows grants
        # them recovery access while excluding other users and broad groups.
        allowed_sids = {
            current_user,
            _windows_sid_from_string("S-1-5-18"),
            _windows_sid_from_string("S-1-5-32-544"),
        }
        acl_info = _WindowsAclSizeInformation()
        if not _advapi32.GetAclInformation(
            dacl,
            ctypes.byref(acl_info),
            ctypes.sizeof(acl_info),
            _ACL_SIZE_INFORMATION_CLASS,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        for index in range(acl_info.AceCount):
            ace = wintypes.LPVOID()
            if not _advapi32.GetAce(dacl, index, ctypes.byref(ace)):
                raise ctypes.WinError(ctypes.get_last_error())
            header = ctypes.cast(ace, ctypes.POINTER(_WindowsAceHeader)).contents
            if header.AceType not in _ACCESS_ALLOWED_ACE_TYPES:
                continue
            sid_offset = 8
            if header.AceType == _ACCESS_ALLOWED_COMPOUND_ACE_TYPE:
                sid_offset = 12
            elif header.AceType in _OBJECT_ACE_TYPES:
                object_flags = ctypes.c_uint32.from_address(ace.value + 8).value
                sid_offset = 12
                if object_flags & _ACE_OBJECT_TYPE_PRESENT:
                    sid_offset += 16
                if object_flags & _ACE_INHERITED_OBJECT_TYPE_PRESENT:
                    sid_offset += 16
            sid = wintypes.LPVOID(ace.value + sid_offset)
            if not _advapi32.IsValidSid(sid):
                raise RuntimeError(
                    f"transaction state entry has an invalid Windows ACL: {path}"
                )
            sid_value = ctypes.string_at(sid, _advapi32.GetLengthSid(sid))
            if sid_value not in allowed_sids:
                raise RuntimeError(
                    f"transaction state entry must have a private Windows ACL: {path}"
                )
    finally:
        _kernel32.LocalFree(descriptor)


def _windows_extended_path(path: Path) -> str:
    absolute = os.path.normpath(os.path.abspath(os.fspath(path)))
    if absolute.startswith("\\\\?\\"):
        return absolute
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute[2:]
    return "\\\\?\\" + absolute


def _windows_nt_path(path: Path) -> str:
    extended = _windows_extended_path(path)
    if extended.startswith("\\\\?\\UNC\\"):
        return "\\??\\UNC\\" + extended[8:]
    return "\\??\\" + extended[4:]


def _windows_owned_directory_handle(path: Path, *, create: bool) -> object:
    if create:
        nt_path = _windows_nt_path(path)
        path_buffer = ctypes.create_unicode_buffer(nt_path)
        path_name = _WindowsUnicodeString(
            len(nt_path.encode("utf-16-le")),
            len(path_buffer) * ctypes.sizeof(wintypes.WCHAR),
            ctypes.cast(path_buffer, wintypes.LPWSTR),
        )
        attributes = _WindowsObjectAttributes(
            ctypes.sizeof(_WindowsObjectAttributes),
            None,
            ctypes.pointer(path_name),
            _OBJ_CASE_INSENSITIVE,
            None,
            None,
        )
        io_status = _WindowsIoStatusBlock()
        handle = wintypes.HANDLE()
        status = _ntdll.NtCreateFile(
            ctypes.byref(handle),
            _DELETE
            | _READ_CONTROL
            | _SYNCHRONIZE
            | _FILE_LIST_DIRECTORY
            | _FILE_READ_ATTRIBUTES,
            ctypes.byref(attributes),
            ctypes.byref(io_status),
            None,
            _FILE_ATTRIBUTE_NORMAL,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE,
            _NT_FILE_CREATE,
            _FILE_DIRECTORY_FILE
            | _FILE_SYNCHRONOUS_IO_NONALERT
            | _NT_FILE_OPEN_REPARSE_POINT,
            None,
            0,
        )
        if status < 0:
            error = int(_ntdll.RtlNtStatusToDosError(status))
            if error in {80, _ERROR_ALREADY_EXISTS}:
                raise FileExistsError(error, os.strerror(error), path)
            if error in {2, 3}:
                raise FileNotFoundError(error, os.strerror(error), path)
            raise OSError(error, os.strerror(error), path)
        return handle

    handle = _kernel32.CreateFileW(
        _windows_extended_path(path),
        _DELETE
        | _READ_CONTROL
        | _SYNCHRONIZE
        | _FILE_LIST_DIRECTORY
        | _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_OPEN_REPARSE_POINT | _FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        error = ctypes.get_last_error()
        if error in {2, 3}:
            raise FileNotFoundError(error, os.strerror(error), path)
        raise OSError(error, os.strerror(error), path)
    return handle


def _windows_observe_directory_handle(path: Path) -> object:
    handle = _kernel32.CreateFileW(
        _windows_extended_path(path),
        _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_OPEN_REPARSE_POINT | _FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        error = ctypes.get_last_error()
        if error in {2, 3}:
            raise FileNotFoundError(error, os.strerror(error), path)
        raise OSError(error, os.strerror(error), path)
    return handle


def _windows_handle_identity(handle: object, recorded_path: Path) -> dict[str, object]:
    file_id = _WindowsFileIdInfo()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        _FILE_ID_INFO_CLASS,
        ctypes.byref(file_id),
        ctypes.sizeof(file_id),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    tag = _WindowsFileAttributeTagInfo()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(tag),
        ctypes.sizeof(tag),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "path_key": _destination_key(recorded_path),
        "device": int(file_id.VolumeSerialNumber),
        "inode": int.from_bytes(bytes(file_id.FileId.Identifier), "little"),
        "type": stat.S_IFDIR
        if tag.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY
        else stat.S_IFREG,
        "reparse_tag": int(tag.ReparseTag)
        if tag.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT
        else 0,
    }


def _windows_rename_handle(handle: object, target: Path) -> None:
    target_name = _windows_nt_path(target).encode("utf-16-le")
    size = (
        _WindowsFileRenameInfo.FileName.offset
        + len(target_name)
        + ctypes.sizeof(wintypes.WCHAR)
    )
    buffer = ctypes.create_string_buffer(size)
    information = ctypes.cast(
        buffer,
        ctypes.POINTER(_WindowsFileRenameInfo),
    ).contents
    information.Flags = 0
    information.RootDirectory = None
    information.FileNameLength = len(target_name)
    ctypes.memmove(
        ctypes.addressof(buffer) + _WindowsFileRenameInfo.FileName.offset,
        target_name,
        len(target_name),
    )
    if not _kernel32.SetFileInformationByHandle(
        handle,
        _FILE_RENAME_INFO_CLASS,
        buffer,
        size,
    ):
        raise ctypes.WinError(ctypes.get_last_error())


def _windows_delete_handle(handle: object) -> None:
    extended = _WindowsFileDispositionInfoEx(
        _FILE_DISPOSITION_FLAG_DELETE
        | _FILE_DISPOSITION_FLAG_POSIX_SEMANTICS
        | _FILE_DISPOSITION_FLAG_IGNORE_READONLY_ATTRIBUTE
    )
    if _kernel32.SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_EX_CLASS,
        ctypes.byref(extended),
        ctypes.sizeof(extended),
    ):
        return
    extended_error = ctypes.get_last_error()
    legacy = _WindowsFileDispositionInfo(True)
    if _kernel32.SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(legacy),
        ctypes.sizeof(legacy),
    ):
        return
    error = ctypes.get_last_error()
    if error == 0:
        error = extended_error
    raise ctypes.WinError(error)


def _windows_open_path(path: Path, *, directory: bool) -> object:
    flags = _FILE_FLAG_OPEN_REPARSE_POINT
    if directory:
        flags |= _FILE_FLAG_BACKUP_SEMANTICS
    handle = _kernel32.CreateFileW(
        _windows_extended_path(path),
        _READ_CONTROL,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        flags,
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


def _windows_durable_parent_handle(
    path: Path,
    child_identity: dict[str, object],
) -> object:
    parent_path = path.parent
    handle = _kernel32.CreateFileW(
        _windows_extended_path(parent_path),
        _GENERIC_READ
        | _GENERIC_WRITE
        | _READ_CONTROL
        | _SYNCHRONIZE
        | _FILE_LIST_DIRECTORY
        | _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_OPEN_REPARSE_POINT | _FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        parent_identity = _windows_handle_identity(handle, parent_path)
        if (
            parent_identity["type"] != stat.S_IFDIR
            or parent_identity["reparse_tag"] != 0
            or parent_identity["device"] != child_identity["device"]
        ):
            raise RuntimeError(
                "refusing an unowned or linked Windows parent during cleanup: "
                f"{parent_path}"
            )
        child_entries = [
            entry
            for entry in _windows_directory_entries(handle)
            if entry[1] == child_identity["inode"]
            and os.path.normcase(entry[0]) == os.path.normcase(path.name)
        ]
        if len(child_entries) != 1:
            raise RuntimeError(
                "owned Windows sibling is not attached to the pinned parent; "
                f"refusing removal: {path}"
            )
        _name, _file_id, attributes, reparse_tag = child_entries[0]
        if (
            not attributes & _FILE_ATTRIBUTE_DIRECTORY
            or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or reparse_tag != 0
        ):
            raise RuntimeError(
                "owned Windows sibling changed type beneath its pinned parent; "
                f"refusing removal: {path}"
            )
        return handle
    except BaseException:
        _kernel32.CloseHandle(handle)
        raise


def _windows_sync_directory_handle(handle: object) -> None:
    if not _kernel32.FlushFileBuffers(handle):
        raise ctypes.WinError(ctypes.get_last_error())


def _windows_create_private_directory(path: Path) -> None:
    with _windows_private_security_attributes() as attributes:
        if _kernel32.CreateDirectoryW(
            _windows_extended_path(path), ctypes.byref(attributes)
        ):
            return
        error = ctypes.get_last_error()
    if error != _ERROR_ALREADY_EXISTS:
        raise ctypes.WinError(error)


def _windows_create_private_child_directory(
    parent: object,
    name: str,
    recorded_path: Path,
) -> object:
    name_buffer = ctypes.create_unicode_buffer(name)
    object_name = _WindowsUnicodeString(
        len(name.encode("utf-16-le")),
        len(name_buffer) * ctypes.sizeof(wintypes.WCHAR),
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    io_status = _WindowsIoStatusBlock()
    handle = wintypes.HANDLE()
    with _windows_private_security_attributes() as security:
        attributes = _WindowsObjectAttributes(
            ctypes.sizeof(_WindowsObjectAttributes),
            parent,
            ctypes.pointer(object_name),
            _OBJ_CASE_INSENSITIVE,
            security.lpSecurityDescriptor,
            None,
        )
        status = _ntdll.NtCreateFile(
            ctypes.byref(handle),
            _DELETE
            | _READ_CONTROL
            | _SYNCHRONIZE
            | _FILE_LIST_DIRECTORY
            | _FILE_READ_ATTRIBUTES,
            ctypes.byref(attributes),
            ctypes.byref(io_status),
            None,
            _FILE_ATTRIBUTE_NORMAL,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE,
            _NT_FILE_CREATE,
            _FILE_DIRECTORY_FILE
            | _FILE_SYNCHRONOUS_IO_NONALERT
            | _NT_FILE_OPEN_REPARSE_POINT,
            None,
            0,
        )
    if status < 0:
        error = int(_ntdll.RtlNtStatusToDosError(status))
        if error in {80, _ERROR_ALREADY_EXISTS}:
            raise FileExistsError(error, os.strerror(error), recorded_path)
        raise OSError(error, os.strerror(error), recorded_path)
    return handle


def _windows_validate_state_directory_handle(
    handle: object,
    path: Path,
    *,
    ancestor: bool,
) -> None:
    identity = _windows_handle_identity(handle, path)
    if identity["reparse_tag"] != 0:
        location = "ancestor" if ancestor else "directory"
        raise RuntimeError(
            f"refusing to use a linked transaction state {location}: {path}"
        )
    if identity["type"] != stat.S_IFDIR:
        if ancestor:
            raise RuntimeError(f"transaction state ancestor is not a directory: {path}")
        raise RuntimeError(f"transaction state path is not a directory: {path}")


def _windows_ensure_private_directory(path: Path) -> tuple[object, ...]:
    absolute = Path(os.path.normpath(os.path.abspath(os.fspath(path))))
    if not absolute.anchor:
        raise RuntimeError(f"cannot anchor Windows transaction state directory: {path}")

    current_path = Path(absolute.anchor)
    inspection_access = _READ_CONTROL | _SYNCHRONIZE | _FILE_READ_ATTRIBUTES
    handles = [_windows_open_path(current_path, directory=True)]
    try:
        _windows_validate_state_directory_handle(
            handles[-1],
            current_path,
            ancestor=True,
        )
        for name in absolute.parts[1:]:
            child_path = current_path / name
            for attempt in range(100):
                try:
                    child = _windows_open_child_handle(
                        handles[-1],
                        name,
                        child_path,
                        access=inspection_access,
                    )
                    break
                except FileNotFoundError:
                    try:
                        child = _windows_create_private_child_directory(
                            handles[-1],
                            name,
                            child_path,
                        )
                        break
                    except FileExistsError:
                        pass
                except OSError as exc:
                    if exc.errno != errno.EPIPE:
                        raise
                time.sleep(0.01)
            else:
                raise RuntimeError(
                    "transaction state directory remained unavailable while opening "
                    f"it: {child_path}"
                )
            try:
                _windows_validate_state_directory_handle(
                    child,
                    child_path,
                    ancestor=child_path != absolute,
                )
            except BaseException:
                _kernel32.CloseHandle(child)
                raise
            handles.append(child)
            current_path = child_path
        if current_path == absolute:
            _windows_validate_private_handle(
                handles[-1],
                current_path,
                directory=True,
            )
        return tuple(handles)
    except BaseException:
        for handle in reversed(handles):
            _kernel32.CloseHandle(handle)
        raise


class _KernelFileLock:
    def __init__(self, file: BinaryIO) -> None:
        self._file = file
        self._locked = False
        file_stat = os.fstat(file.fileno())
        self._identity = (
            int(file_stat.st_dev),
            int(file_stat.st_ino),
            int(stat.S_IFMT(file_stat.st_mode)),
            int(getattr(file_stat, "st_reparse_tag", 0)),
        )

    def acquire(self, *, blocking: bool) -> bool:
        while True:
            try:
                self._acquire_once()
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if not blocking:
                    return False
                time.sleep(0.05)
                continue
            self._locked = True
            return True

    def _acquire_once(self) -> None:
        self._file.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def close(self) -> None:
        if self._locked:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._locked = False
        self._file.close()

    def matches_path(self, path: Path) -> bool:
        try:
            path_stat = path.lstat()
        except OSError:
            return False
        return self._identity == (
            int(path_stat.st_dev),
            int(path_stat.st_ino),
            int(stat.S_IFMT(path_stat.st_mode)),
            int(getattr(path_stat, "st_reparse_tag", 0)),
        )


def _effective_user_id() -> int | None:
    get_effective_user_id = getattr(os, "geteuid", None)
    if get_effective_user_id is None:
        return None
    return int(get_effective_user_id())


def _user_namespace() -> str:
    effective_user_id = _effective_user_id()
    if effective_user_id is not None:
        return f"uid-{effective_user_id}"

    identity = "\0".join(
        (
            os.environ.get("USERDOMAIN", ""),
            os.environ.get("USERNAME", ""),
            os.fspath(Path.home()),
            tempfile.gettempdir(),
        )
    )
    return "user-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _validate_state_directory(state: Path) -> None:
    if os.name == "nt":
        handle = _windows_open_path(state, directory=True)
        try:
            _windows_validate_private_handle(handle, state, directory=True)
        finally:
            _kernel32.CloseHandle(handle)
        return

    try:
        state_stat = state.lstat()
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"transaction state directory disappeared while opening it: {state}"
        ) from exc

    if stat.S_ISLNK(state_stat.st_mode) or int(
        getattr(state_stat, "st_reparse_tag", 0)
    ):
        raise RuntimeError(
            f"refusing to use a linked transaction state directory: {state}"
        )
    if not stat.S_ISDIR(state_stat.st_mode):
        raise RuntimeError(f"transaction state path is not a directory: {state}")

    if os.name != "nt":
        effective_user_id = _effective_user_id()
        if effective_user_id is None:
            raise RuntimeError(
                "cannot verify transaction state directory ownership on this platform"
            )
        if state_stat.st_uid != effective_user_id:
            raise RuntimeError(
                f"transaction state directory is not owned by the current user: {state}"
            )
        if stat.S_IMODE(state_stat.st_mode) != stat.S_IRWXU:
            raise RuntimeError(
                "transaction state directory must have private 0700 permissions: "
                f"{state}"
            )


def _absolute_state_directory(configured: str | None) -> Path:
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            legacy_path = candidate.resolve(strict=False)
            raise RuntimeError(
                f"{_STATE_DIRECTORY_ENV} must be an absolute path; relative state "
                "roots historically resolve from each process working directory "
                "and can split transaction locks. To preserve this working "
                "directory's existing v7 state, set the variable to this canonical "
                f"absolute target before retrying: {legacy_path}"
            )
    else:
        trusted_temp_directory = Path(tempfile.gettempdir()).resolve(strict=True)
        candidate = trusted_temp_directory / (
            f"{_STATE_DIRECTORY_NAME}-{_user_namespace()}"
        )
    return Path(os.path.normpath(os.path.abspath(os.fspath(candidate))))


@contextmanager
def _pinned_state_directory() -> Iterator[Path]:
    configured = os.environ.get(_STATE_DIRECTORY_ENV)
    state = _absolute_state_directory(configured)
    if os.name == "nt":
        handles = _windows_ensure_private_directory(state)
        try:
            yield state
        finally:
            for handle in reversed(handles):
                _kernel32.CloseHandle(handle)
        return

    _posix_ensure_private_state_directory(state)
    yield state


def _state_directory() -> Path:
    with _pinned_state_directory() as state:
        return state


def _open_state_file(path: Path, flags: int) -> BinaryIO:
    if os.name == "nt":
        if flags & os.O_EXCL:
            disposition = _CREATE_NEW
        elif flags & os.O_CREAT:
            disposition = _OPEN_ALWAYS
        else:
            disposition = _OPEN_EXISTING
        with _windows_private_security_attributes() as attributes:
            handle = _kernel32.CreateFileW(
                _windows_extended_path(path),
                _GENERIC_READ | _GENERIC_WRITE | _READ_CONTROL,
                _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
                ctypes.byref(attributes),
                disposition,
                _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
                None,
            )
            if handle == wintypes.HANDLE(-1).value:
                error = ctypes.get_last_error()
                if error in {80, _ERROR_ALREADY_EXISTS} and flags & os.O_EXCL:
                    raise FileExistsError(error, os.strerror(error), path)
                if error in {2, 3}:
                    raise FileNotFoundError(error, os.strerror(error), path)
                raise ctypes.WinError(error)
        try:
            _windows_validate_private_handle(handle, path, directory=False)
            descriptor = msvcrt.open_osfhandle(
                handle,
                os.O_RDWR | getattr(os, "O_BINARY", 0),
            )
        except BaseException:
            _kernel32.CloseHandle(handle)
            raise
        try:
            return os.fdopen(descriptor, "r+b", buffering=0)
        except BaseException:
            os.close(descriptor)
            raise

    open_flags = flags | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, open_flags, 0o600)
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise RuntimeError(f"transaction state entry is not a regular file: {path}")
        if os.name != "nt":
            effective_user_id = _effective_user_id()
            if effective_user_id is None or file_stat.st_uid != effective_user_id:
                raise RuntimeError(
                    f"transaction state entry is not owned by the current user: {path}"
                )
            mode = stat.S_IMODE(file_stat.st_mode)
            if (mode & (stat.S_IRWXG | stat.S_IRWXO)) or (mode & 0o600) != 0o600:
                raise RuntimeError(
                    f"transaction state entry must have private 0600 permissions: {path}"
                )
        return os.fdopen(descriptor, "r+b", buffering=0)
    except BaseException:
        os.close(descriptor)
        raise


def _normalized_destination(destination: Path) -> str:
    # The transaction renames the destination itself, so its identity must be
    # lexical and remain stable if that destination happens to be a symlink.
    return os.path.normcase(os.path.abspath(os.fspath(destination)))


def _destination_key(destination: Path) -> str:
    return hashlib.sha256(
        _normalized_destination(destination).encode("utf-8")
    ).hexdigest()


def _ensure_lock_byte(file: BinaryIO) -> None:
    file.seek(0, os.SEEK_END)
    if file.tell() == 0:
        file.write(b"\0")
        file.flush()
        os.fsync(file.fileno())


def _validate_lock_byte(file: BinaryIO, path: Path) -> None:
    file.seek(0)
    if file.read() != b"\0":
        raise RuntimeError(f"ownership lease is invalid; refusing recovery: {path}")


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        handle = _kernel32.CreateFileW(
            _windows_extended_path(path),
            _GENERIC_READ | _GENERIC_WRITE,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
            None,
            _OPEN_EXISTING,
            _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            _windows_sync_directory_handle(handle)
        finally:
            _kernel32.CloseHandle(handle)
        return

    descriptor = os.open(path, _posix_directory_open_flags())
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_state_file(source: Path, target: Path) -> None:
    if os.name == "nt":
        if _kernel32.MoveFileExW(
            _windows_extended_path(source),
            _windows_extended_path(target),
            _MOVEFILE_WRITE_THROUGH,
        ):
            return
        error = ctypes.get_last_error()
        if error in {80, _ERROR_ALREADY_EXISTS}:
            raise FileExistsError(error, os.strerror(error), target)
        raise ctypes.WinError(error)
    _posix_rename_no_replace(source, target)


def _journal_temporary_artifact(path: Path, marker_path: Path) -> bool:
    stem = re.escape(marker_path.name.removesuffix(".owner"))
    return (
        re.fullmatch(
            rf"{stem}\.[0-9]{{{_JOURNAL_GENERATION_WIDTH}}}\."
            r"[0-9a-f]{32}\.state\.tmp",
            path.name,
        )
        is not None
    )


def _remove_journal_artifacts(marker_path: Path) -> None:
    removed = False
    for path in tuple(marker_path.parent.iterdir()):
        if _journal_generation(
            path, marker_path
        ) is None and not _journal_temporary_artifact(path, marker_path):
            continue
        try:
            path.unlink()
            removed = True
        except FileNotFoundError:
            pass
    if removed:
        _sync_directory(marker_path.parent)


def _publish_journal(
    marker_path: Path,
    destination: Path,
    kind: str,
    token: str,
    owned_paths: dict[str, dict[str, object]],
    sibling_location: str,
    previous_generation: int,
) -> int:
    generation = previous_generation + 1
    target = _journal_path(marker_path, generation)
    temporary = _journal_temporary_path(marker_path, generation)
    file = _open_state_file(temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL)
    published = False
    try:
        file.write(
            _encode_journal(
                destination,
                kind,
                token,
                owned_paths,
                sibling_location,
                generation,
            )
        )
        file.flush()
        os.fsync(file.fileno())
        _owned_journal_phase("after_temporary_fsync", temporary)
        file.close()
        _publish_state_file(temporary, target)
        published = True
        _owned_journal_phase("after_publish", target)
        _sync_directory(marker_path.parent)
        _owned_journal_phase("after_directory_fsync", target)
    finally:
        if not file.closed:
            file.close()
        if not published:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    journals = _journal_paths(marker_path)
    obsolete = journals[:-_JOURNAL_RETAINED_GENERATIONS]
    if obsolete:
        for _old_generation, old_path in obsolete:
            try:
                old_path.unlink()
            except FileNotFoundError:
                pass
        _sync_directory(marker_path.parent)
    return generation


def _destination_state_directory(
    destination: Path,
    state_directory: Path | None = None,
) -> Path:
    state = state_directory or _state_directory()
    return state / f"{_destination_key(destination)}{_DESTINATION_STATE_SUFFIX}"


def _ensure_destination_state_directory(
    destination: Path,
    state_directory: Path,
) -> Path:
    destination_state = _destination_state_directory(destination, state_directory)
    if os.name == "nt":
        _windows_create_private_directory(destination_state)
    else:
        try:
            destination_state.mkdir(mode=0o700, exist_ok=False)
        except FileExistsError:
            pass
    _validate_state_directory(destination_state)
    return destination_state


def _existing_destination_state_directory(
    destination: Path,
    state_directory: Path,
) -> Path | None:
    destination_state = _destination_state_directory(destination, state_directory)
    try:
        destination_state.lstat()
    except FileNotFoundError:
        return None
    _validate_state_directory(destination_state)
    return destination_state


@contextmanager
def _locked_registry(
    pinned_state_directory: Path | None = None,
) -> Iterator[Path]:
    if pinned_state_directory is None:
        with _pinned_state_directory() as state_directory:
            with _locked_registry(state_directory) as locked_state_directory:
                yield locked_state_directory
        return

    state_directory = pinned_state_directory
    registry_path = state_directory / _REGISTRY_LOCK_NAME
    file = _open_state_file(registry_path, os.O_RDWR | os.O_CREAT)
    lock = _KernelFileLock(file)
    try:
        _ensure_lock_byte(file)
        lock.acquire(blocking=True)
        yield state_directory
    finally:
        lock.close()


def _try_destination_lock(
    destination: Path,
    state_directory: Path,
) -> _KernelFileLock | None:
    destination_state = _ensure_destination_state_directory(
        destination,
        state_directory,
    )
    lock_path = destination_state / _DESTINATION_LOCK_NAME
    file = _open_state_file(lock_path, os.O_RDWR | os.O_CREAT)
    lock = _KernelFileLock(file)
    try:
        _ensure_lock_byte(file)
        if not lock.acquire(blocking=False):
            lock.close()
            return None
        return lock
    except BaseException:
        lock.close()
        raise


def _prune_destination_state(
    destination: Path,
    state_directory: Path,
    held_lock: _KernelFileLock | None = None,
) -> None:
    destination_state = _existing_destination_state_directory(
        destination,
        state_directory,
    )
    if destination_state is None:
        if held_lock is not None:
            held_lock.close()
        return

    _prune_abandoned_owner_state(destination, destination_state)
    lock_path = destination_state / _DESTINATION_LOCK_NAME
    entries = tuple(destination_state.iterdir())
    if any(entry != lock_path for entry in entries):
        if held_lock is not None:
            held_lock.close()
        return

    lock = held_lock
    if lock is None and lock_path in entries:
        try:
            file = _open_state_file(lock_path, os.O_RDWR)
        except FileNotFoundError:
            return
        lock = _KernelFileLock(file)
        try:
            _ensure_lock_byte(file)
            if not lock.acquire(blocking=False):
                lock.close()
                return
        except BaseException:
            lock.close()
            raise

    if lock is not None:
        if lock_path in entries and not lock.matches_path(lock_path):
            lock.close()
            return
        lock.close()

    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    try:
        destination_state.rmdir()
    except FileNotFoundError:
        pass


def _release_destination_lock(
    destination: Path,
    lock: _KernelFileLock,
    state_directory: Path,
) -> None:
    try:
        with _locked_registry(state_directory):
            _prune_destination_state(destination, state_directory, lock)
    finally:
        lock.close()


@contextmanager
def locked_destination(destination: Path) -> Iterator[None]:
    with _pinned_state_directory() as state_directory:
        lock: _KernelFileLock | None = None
        while lock is None:
            with _locked_registry(state_directory):
                lock = _try_destination_lock(destination, state_directory)
            if lock is None:
                time.sleep(0.05)
        try:
            yield
        finally:
            _release_destination_lock(destination, lock, state_directory)


def _validate_kind(kind: str) -> None:
    if re.fullmatch(r"[a-z][a-z0-9-]*", kind) is None:
        raise ValueError(f"invalid owned transaction kind: {kind!r}")


def _marker_path(
    destination: Path,
    kind: str,
    token: str,
    state_directory: Path | None = None,
) -> Path:
    # The historical .owner name is now a stable one-byte liveness lease. State
    # is never written into or atomically replaced over this inode.
    return _destination_state_directory(destination, state_directory) / (
        f"{kind}.{token}.owner"
    )


def _journal_path(marker_path: Path, generation: int) -> Path:
    stem = marker_path.name.removesuffix(".owner")
    return marker_path.with_name(
        f"{stem}.{generation:0{_JOURNAL_GENERATION_WIDTH}d}.state"
    )


def _journal_temporary_path(marker_path: Path, generation: int) -> Path:
    stem = marker_path.name.removesuffix(".owner")
    return marker_path.with_name(
        f"{stem}.{generation:0{_JOURNAL_GENERATION_WIDTH}d}."
        f"{uuid.uuid4().hex}.state.tmp"
    )


def _journal_generation(path: Path, marker_path: Path) -> int | None:
    stem = re.escape(marker_path.name.removesuffix(".owner"))
    match = re.fullmatch(
        rf"{stem}\.([0-9]{{{_JOURNAL_GENERATION_WIDTH}}})\.state",
        path.name,
    )
    if match is None:
        return None
    generation = int(match.group(1))
    return generation if generation > 0 else None


def _journal_paths(marker_path: Path) -> tuple[tuple[int, Path], ...]:
    journals = (
        (generation, path)
        for path in tuple(marker_path.parent.iterdir())
        if (generation := _journal_generation(path, marker_path)) is not None
    )
    return tuple(sorted(journals))


def _marker_owner_identity(path: Path) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"([a-z][a-z0-9-]*)\.([0-9a-f]{32})\.owner",
        path.name,
    )
    if match is None:
        return None
    return match.group(1), match.group(2)


def _journal_owner_identity(path: Path) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"([a-z][a-z0-9-]*)\.([0-9a-f]{32})\."
        rf"[0-9]{{{_JOURNAL_GENERATION_WIDTH}}}(?:\.[0-9a-f]{{32}})?\."
        r"state(?:\.tmp)?",
        path.name,
    )
    if match is None:
        return None
    return match.group(1), match.group(2)


def _owned_sibling_candidates_absent(
    destination: Path,
    kind: str,
    token: str,
) -> bool:
    sibling = _owned_sibling_path(destination, kind, token)
    candidates = [
        sibling,
        _owned_sibling_cleanup_path(destination, kind, token),
    ]
    if os.name != "nt":
        candidates.append(_posix_staging_path(sibling))
    return not any(_path_exists_without_following(path) for path in candidates)


def _prune_abandoned_owner_state(
    destination: Path,
    destination_state: Path,
) -> None:
    changed = False
    for marker_path in tuple(destination_state.iterdir()):
        identity = _marker_owner_identity(marker_path)
        if identity is None or _journal_paths(marker_path):
            continue
        kind, token = identity
        if not _owned_sibling_candidates_absent(destination, kind, token):
            continue
        try:
            marker_file = _open_state_file(marker_path, os.O_RDWR)
        except FileNotFoundError:
            continue
        lease = _KernelFileLock(marker_file)
        try:
            marker_file.seek(0)
            lease_content = marker_file.read()
            if lease_content not in {b"", b"\0"}:
                continue
            if not lease_content:
                _ensure_lock_byte(marker_file)
            if not lease.acquire(blocking=False):
                continue
            if not lease.matches_path(marker_path):
                continue
        finally:
            lease.close()
        try:
            marker_path.unlink()
            changed = True
        except FileNotFoundError:
            pass
        _remove_journal_artifacts(marker_path)

    live_owners = {
        identity
        for path in tuple(destination_state.iterdir())
        if (identity := _marker_owner_identity(path)) is not None
    }
    for path in tuple(destination_state.iterdir()):
        identity = _journal_owner_identity(path)
        if identity is None or identity in live_owners:
            continue
        try:
            path.unlink()
            changed = True
        except FileNotFoundError:
            pass
    if changed:
        _sync_directory(destination_state)


def _marker_payload(
    destination: Path,
    kind: str,
    token: str,
    owned_paths: dict[str, dict[str, object]],
    sibling_location: str,
) -> dict[str, object]:
    return {
        "schema": _MARKER_SCHEMA,
        "destination_key": _destination_key(destination),
        "kind": kind,
        "token": token,
        "sibling_location": sibling_location,
        "owned_paths": owned_paths,
    }


def _journal_checksum(generation: int, payload: dict[str, object]) -> str:
    protected = {
        "journal_schema": _JOURNAL_SCHEMA,
        "generation": generation,
        "payload": payload,
    }
    return hashlib.sha256(
        json.dumps(protected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _encode_journal(
    destination: Path,
    kind: str,
    token: str,
    owned_paths: dict[str, dict[str, object]],
    sibling_location: str,
    generation: int,
) -> bytes:
    payload = _marker_payload(
        destination,
        kind,
        token,
        owned_paths,
        sibling_location,
    )
    envelope = {
        "journal_schema": _JOURNAL_SCHEMA,
        "generation": generation,
        "payload": payload,
        "checksum": _journal_checksum(generation, payload),
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _owned_path_identity(
    path: Path,
    *,
    recorded_path: Path | None = None,
) -> dict[str, object]:
    path_stat = path.lstat()
    return {
        "path_key": _destination_key(recorded_path or path),
        "device": int(path_stat.st_dev),
        "inode": int(path_stat.st_ino),
        "type": int(stat.S_IFMT(path_stat.st_mode)),
        "reparse_tag": int(getattr(path_stat, "st_reparse_tag", 0)),
    }


def _path_exists_without_following(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _owned_path_matches(
    expected: dict[str, object],
    path: Path,
    *,
    recorded_path: Path | None = None,
) -> bool:
    try:
        return expected == _owned_path_identity(
            path,
            recorded_path=recorded_path,
        )
    except OSError:
        return False


def _owned_sibling_path(destination: Path, kind: str, token: str) -> Path:
    return destination.with_name(f".{destination.name}.protocyte-{kind}-{token}")


def _owned_sibling_cleanup_path(destination: Path, kind: str, token: str) -> Path:
    return destination.with_name(
        f".{destination.name}.protocyte-cleanup-{kind}-{token}"
    )


def _valid_owned_sibling_identity(
    identity: dict[str, object],
    path: Path,
) -> bool:
    return (
        identity["path_key"] == _destination_key(path)
        and identity["device"] >= 0
        and identity["inode"] > 0
        and identity["type"] == stat.S_IFDIR
        and identity["reparse_tag"] == 0
    )


def _validate_marker_payload(
    payload: object,
    destination: Path,
    kind: str,
    token: str,
) -> tuple[dict[str, dict[str, object]], str] | None:
    if not isinstance(payload, dict):
        return None
    owned_paths = payload.get("owned_paths")
    if not isinstance(owned_paths, dict):
        return None
    sibling_location = payload.get("sibling_location")
    if sibling_location not in {"creating", "original", "detaching", "cleanup"}:
        return None
    expected = _marker_payload(
        destination,
        kind,
        token,
        owned_paths,
        sibling_location,
    )
    if payload != expected:
        return None
    if not all(
        isinstance(label, str)
        and re.fullmatch(r"[a-z][a-z0-9_]*", label) is not None
        and isinstance(identity, dict)
        and set(identity) == {"path_key", "device", "inode", "type", "reparse_tag"}
        and isinstance(identity["path_key"], str)
        and re.fullmatch(r"[0-9a-f]{64}", identity["path_key"]) is not None
        and all(
            isinstance(identity[field], int) and not isinstance(identity[field], bool)
            for field in ("device", "inode", "type", "reparse_tag")
        )
        for label, identity in owned_paths.items()
    ):
        return None
    sibling_identity = owned_paths.get(_OWNED_SIBLING_LABEL)
    sibling_path = _owned_sibling_path(destination, kind, token)
    if sibling_location == "creating":
        if sibling_identity is not None:
            return None
    elif sibling_identity is None or not _valid_owned_sibling_identity(
        sibling_identity, sibling_path
    ):
        return None
    return owned_paths, sibling_location


def _decode_journal(
    content: bytes,
    destination: Path,
    kind: str,
    token: str,
    expected_generation: int,
) -> tuple[dict[str, dict[str, object]], str] | None:
    try:
        envelope = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(envelope, dict):
        return None
    if set(envelope) != {"journal_schema", "generation", "payload", "checksum"}:
        return None
    if envelope["journal_schema"] != _JOURNAL_SCHEMA:
        return None
    generation = envelope["generation"]
    if (
        not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation != expected_generation
    ):
        return None
    payload = envelope["payload"]
    checksum = envelope["checksum"]
    if (
        not isinstance(payload, dict)
        or not isinstance(checksum, str)
        or re.fullmatch(r"[0-9a-f]{64}", checksum) is None
        or checksum != _journal_checksum(generation, payload)
    ):
        return None
    return _validate_marker_payload(payload, destination, kind, token)


def _read_latest_journal(
    marker_path: Path,
    destination: Path,
    kind: str,
    token: str,
) -> tuple[dict[str, dict[str, object]], str, int]:
    journals = _journal_paths(marker_path)
    if not journals:
        raise RuntimeError(
            "ownership lease has no committed state journal; refusing recovery: "
            f"{marker_path}"
        )
    latest: tuple[dict[str, dict[str, object]], str, int] | None = None
    for generation, path in journals:
        try:
            file = _open_state_file(path, os.O_RDWR)
        except FileNotFoundError:
            continue
        try:
            file.seek(0)
            decoded = _decode_journal(
                file.read(),
                destination,
                kind,
                token,
                generation,
            )
        finally:
            file.close()
        if decoded is None:
            raise RuntimeError(
                "ownership state journal is incomplete or invalid; refusing "
                f"recovery: {path}"
            )
        owned_paths, sibling_location = decoded
        latest = owned_paths, sibling_location, generation
    if latest is None:
        raise RuntimeError(
            "ownership lease has no readable committed state journal; refusing "
            f"recovery: {marker_path}"
        )
    return latest


def _read_latest_journal_payload(
    marker_path: Path,
    destination: Path,
    kind: str,
    token: str,
) -> dict[str, object]:
    owned_paths, sibling_location, _generation = _read_latest_journal(
        marker_path,
        destination,
        kind,
        token,
    )
    return _marker_payload(
        destination,
        kind,
        token,
        owned_paths,
        sibling_location,
    )


def _unowned_sibling_error(path: Path) -> RuntimeError:
    return RuntimeError(
        "refusing to remove an unowned, replaced, or linked transaction sibling at "
        f"{path}. No unverified path was deleted, and the ownership marker was "
        "retained for manual inspection."
    )


def _owned_sibling_creation_phase(_phase: str, _path: Path) -> None:
    """Test seam for races immediately after handle-backed directory creation."""


def _owned_sibling_cleanup_phase(_phase: str, _path: Path) -> None:
    """Test seam for crashes and races during journaled sibling cleanup."""


def _owned_journal_phase(_phase: str, _path: Path) -> None:
    """Test seam for crashes and torn writes around journal publication."""


def _owned_windows_entry_phase(_phase: str, _path: Path) -> None:
    """Test seam for child replacement during handle-relative cleanup."""


def _owned_namespace_phase(_phase: str, _path: Path) -> None:
    """Test seam after an owned sibling namespace mutation is durable."""


def _owned_retirement_phase(_phase: str, _path: Path) -> None:
    """Test seam while retiring lease and journal state under the registry."""


def _directory_identity_from_stat(
    path_stat: os.stat_result,
    recorded_path: Path,
) -> dict[str, object]:
    return {
        "path_key": _destination_key(recorded_path),
        "device": int(path_stat.st_dev),
        "inode": int(path_stat.st_ino),
        "type": int(stat.S_IFMT(path_stat.st_mode)),
        "reparse_tag": int(getattr(path_stat, "st_reparse_tag", 0)),
    }


def _same_filesystem_object(
    left: dict[str, object],
    right: dict[str, object],
) -> bool:
    return all(
        left[field] == right[field]
        for field in ("device", "inode", "type", "reparse_tag")
    )


def _posix_directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _posix_validate_state_ancestor(
    descriptor: int,
    path: Path,
) -> None:
    path_stat = os.fstat(descriptor)
    effective_user_id = _effective_user_id()
    if effective_user_id is None:
        raise RuntimeError(
            "cannot verify transaction state directory ownership on this platform"
        )
    mode = stat.S_IMODE(path_stat.st_mode)
    if (
        not stat.S_ISDIR(path_stat.st_mode)
        or int(path_stat.st_uid) not in {0, effective_user_id}
        or (mode & 0o022 and not path_stat.st_mode & stat.S_ISVTX)
    ):
        raise RuntimeError(
            f"refusing an untrusted transaction state ancestor directory: {path}"
        )


def _posix_validate_private_state_directory(
    descriptor: int,
    path: Path,
) -> None:
    path_stat = os.fstat(descriptor)
    effective_user_id = _effective_user_id()
    if effective_user_id is None:
        raise RuntimeError(
            "cannot verify transaction state directory ownership on this platform"
        )
    if not stat.S_ISDIR(path_stat.st_mode):
        raise RuntimeError(f"transaction state path is not a directory: {path}")
    if int(path_stat.st_uid) != effective_user_id:
        raise RuntimeError(
            f"transaction state directory is not owned by the current user: {path}"
        )
    if stat.S_IMODE(path_stat.st_mode) != stat.S_IRWXU:
        raise RuntimeError(
            f"transaction state directory must have private 0700 permissions: {path}"
        )


def _posix_open_state_child_directory(
    parent: int,
    name: str,
    path: Path,
    *,
    final: bool,
) -> int:
    try:
        entry_stat = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
        except FileExistsError:
            pass
        else:
            os.chmod(name, 0o700, dir_fd=parent, follow_symlinks=False)
        try:
            entry_stat = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"transaction state directory disappeared while opening it: {path}"
            ) from exc

    if stat.S_ISLNK(entry_stat.st_mode) or int(
        getattr(entry_stat, "st_reparse_tag", 0)
    ):
        location = "directory" if final else "ancestor"
        raise RuntimeError(
            f"refusing to use a linked transaction state {location}: {path}"
        )
    if not stat.S_ISDIR(entry_stat.st_mode):
        if final:
            raise RuntimeError(f"transaction state path is not a directory: {path}")
        raise RuntimeError(f"transaction state ancestor is not a directory: {path}")
    try:
        descriptor = os.open(name, _posix_directory_open_flags(), dir_fd=parent)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            location = "directory" if final else "ancestor"
            raise RuntimeError(
                f"refusing to use a linked transaction state {location}: {path}"
            ) from exc
        raise
    opened_stat = os.fstat(descriptor)
    if not _same_posix_identity(entry_stat, opened_stat):
        os.close(descriptor)
        raise RuntimeError(
            f"transaction state path changed identity while opening it: {path}"
        )
    return descriptor


def _posix_ensure_private_state_directory(path: Path) -> None:
    if not path.is_absolute() or not path.anchor:
        raise RuntimeError(f"cannot anchor POSIX transaction state directory: {path}")
    if not getattr(os, "O_NOFOLLOW", 0):
        raise RuntimeError(
            "O_NOFOLLOW is unavailable; refusing transaction state directory creation"
        )

    current_path = Path(path.anchor)
    descriptor = os.open(current_path, _posix_directory_open_flags())
    try:
        _posix_validate_state_ancestor(descriptor, current_path)
        for name in path.parts[1:]:
            child_path = current_path / name
            child = _posix_open_state_child_directory(
                descriptor,
                name,
                child_path,
                final=child_path == path,
            )
            try:
                if child_path == path:
                    _posix_validate_private_state_directory(child, child_path)
                else:
                    _posix_validate_state_ancestor(child, child_path)
            except BaseException:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
            current_path = child_path
        if current_path == path:
            _posix_validate_private_state_directory(descriptor, current_path)
    finally:
        os.close(descriptor)


class _PosixOpenHow(ctypes.Structure):
    _fields_ = (
        ("flags", ctypes.c_uint64),
        ("mode", ctypes.c_uint64),
        ("resolve", ctypes.c_uint64),
    )


def _mount_boundary_error(path: Path | str) -> RuntimeError:
    return RuntimeError(
        "refusing to cross a filesystem mount boundary while removing an owned "
        f"transaction sibling: {path}"
    )


def _posix_open_child_directory(
    parent: int,
    name: str,
    root_device: int,
) -> int:
    if sys.platform.startswith("linux"):
        # openat2(RESOLVE_NO_XDEV) rejects bind mounts as well as differing
        # devices. A plain st_dev comparison cannot detect a same-device bind.
        machine = os.uname().machine.lower()
        if machine not in {"aarch64", "arm64", "x86_64", "amd64"}:
            raise RuntimeError(
                "openat2 syscall number is not verified for this architecture; "
                f"refusing owned directory cleanup on {machine}"
            )
        library = ctypes.CDLL(None, use_errno=True)
        syscall = library.syscall
        syscall.restype = ctypes.c_long
        how = _PosixOpenHow(
            _posix_directory_open_flags(),
            0,
            0x01 | 0x02 | 0x04 | 0x08,
            # NO_XDEV | NO_MAGICLINKS | NO_SYMLINKS | BENEATH
        )
        descriptor = int(
            syscall(
                437,  # __NR_openat2 on supported Linux architectures
                parent,
                ctypes.c_char_p(os.fsencode(name)),
                ctypes.byref(how),
                ctypes.sizeof(how),
            )
        )
        if descriptor >= 0:
            opened_stat = os.fstat(descriptor)
            if int(opened_stat.st_dev) != root_device:
                os.close(descriptor)
                raise _mount_boundary_error(name)
            return descriptor
        error = ctypes.get_errno()
        if error == errno.EXDEV:
            raise _mount_boundary_error(name)
        if error != errno.ENOSYS:
            raise OSError(error, os.strerror(error), name)
        raise RuntimeError(
            "openat2 with RESOLVE_NO_XDEV is unavailable; refusing unsafe owned "
            f"directory cleanup beneath {name}"
        )

    descriptor = os.open(name, _posix_directory_open_flags(), dir_fd=parent)
    opened_stat = os.fstat(descriptor)
    if int(opened_stat.st_dev) != root_device:
        os.close(descriptor)
        raise _mount_boundary_error(name)
    return descriptor


def _same_posix_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        int(left.st_dev),
        int(left.st_ino),
        int(stat.S_IFMT(left.st_mode)),
    ) == (
        int(right.st_dev),
        int(right.st_ino),
        int(stat.S_IFMT(right.st_mode)),
    )


def _remove_posix_directory_contents(
    descriptor: int,
    root_device: int,
) -> None:
    while True:
        names = os.listdir(descriptor)
        if not names:
            return
        for name in names:
            try:
                entry_stat = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                continue
            is_directory = stat.S_ISDIR(entry_stat.st_mode) and not int(
                getattr(entry_stat, "st_reparse_tag", 0)
            )
            if not is_directory:
                try:
                    os.unlink(name, dir_fd=descriptor)
                except FileNotFoundError:
                    pass
                continue

            if int(entry_stat.st_dev) != root_device:
                raise _mount_boundary_error(name)

            try:
                child = _posix_open_child_directory(
                    descriptor,
                    name,
                    root_device,
                )
            except FileNotFoundError:
                continue
            except OSError as exc:
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                    raise RuntimeError(
                        "owned transaction child changed identity during cleanup; "
                        f"refusing removal: {name}"
                    ) from exc
                raise
            try:
                opened_stat = os.fstat(child)
                if not _same_posix_identity(opened_stat, entry_stat):
                    raise RuntimeError(
                        "owned transaction child changed identity during cleanup; "
                        f"refusing removal: {name}"
                    )
                _remove_posix_directory_contents(child, root_device)
                try:
                    current_stat = os.stat(
                        name,
                        dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    continue
                if not _same_posix_identity(current_stat, opened_stat):
                    raise RuntimeError(
                        "owned transaction child changed identity during cleanup; "
                        f"refusing removal: {name}"
                    )
                try:
                    os.rmdir(name, dir_fd=descriptor)
                except FileNotFoundError:
                    pass
            finally:
                os.close(child)


def _posix_renameat_no_replace(
    source_directory: int,
    source_name: str | bytes,
    target_directory: int,
    target_name: str | bytes,
) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source_name)
    target_bytes = os.fsencode(target_name)
    if sys.platform.startswith("linux"):
        rename = getattr(library, "renameat2", None)
        if rename is not None:
            rename.argtypes = (
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            )
            rename.restype = ctypes.c_int
            result = rename(
                source_directory,
                source_bytes,
                target_directory,
                target_bytes,
                1,
            )
            if result == 0:
                return
            error = ctypes.get_errno()
            if error in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(error, os.strerror(error), target_name)
            raise OSError(error, os.strerror(error), source_name, target_name)
    elif sys.platform == "darwin":
        rename = getattr(library, "renameatx_np", None)
        if rename is not None:
            rename.argtypes = (
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            )
            rename.restype = ctypes.c_int
            result = rename(
                source_directory,
                source_bytes,
                target_directory,
                target_bytes,
                0x00000004,
            )
            if result == 0:
                return
            error = ctypes.get_errno()
            if error in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(error, os.strerror(error), target_name)
            raise OSError(error, os.strerror(error), source_name, target_name)
    raise RuntimeError(
        "cannot atomically detach an owned sibling without replacing another path "
        f"on this platform: {source_name}"
    )


def _posix_rename_no_replace(source: Path, target: Path) -> None:
    _posix_renameat_no_replace(-100, os.fspath(source), -100, os.fspath(target))


def _validate_posix_staging_directory(
    descriptor: int,
    path: Path,
    parent_device: int,
) -> os.stat_result:
    # The current effective UID is the explicit trust principal. Mode 0700
    # excludes other UIDs while the descriptor-relative child is established.
    path_stat = os.fstat(descriptor)
    effective_user_id = _effective_user_id()
    if (
        not stat.S_ISDIR(path_stat.st_mode)
        or effective_user_id is None
        or int(path_stat.st_uid) != effective_user_id
        or stat.S_IMODE(path_stat.st_mode) != 0o700
        or int(path_stat.st_dev) != parent_device
    ):
        raise RuntimeError(
            "refusing an untrusted POSIX staging directory for an owned sibling: "
            f"{path}"
        )
    if os.listdir(descriptor):
        raise RuntimeError(
            f"refusing a non-empty POSIX staging directory for an owned sibling: {path}"
        )
    return path_stat


def _validate_posix_ancestor_chain(
    path: Path,
    expected: os.stat_result,
) -> None:
    # Every pathname component must be controlled by root/current-euid. A
    # sticky writable directory protects a trusted-owned child entry; an
    # ordinary group/other-writable directory does not. This keeps later
    # caller pathname I/O inside the same explicit UID trust boundary.
    effective_user_id = _effective_user_id()
    if effective_user_id is None:
        raise RuntimeError("cannot verify POSIX ancestor ownership on this platform")
    trusted_owners = {0, effective_user_id}
    absolute = Path(os.path.abspath(os.fspath(path)))
    parts = absolute.parts
    if not absolute.anchor or not parts:
        raise RuntimeError(f"cannot anchor POSIX ancestor validation for: {path}")

    descriptor = os.open(absolute.anchor, _posix_directory_open_flags())
    try:
        for name in parts[1:]:
            parent_stat = os.fstat(descriptor)
            parent_mode = stat.S_IMODE(parent_stat.st_mode)
            if (
                not stat.S_ISDIR(parent_stat.st_mode)
                or int(parent_stat.st_uid) not in trusted_owners
                or (parent_mode & 0o022 and not parent_stat.st_mode & stat.S_ISVTX)
            ):
                raise RuntimeError(
                    "refusing a POSIX owned sibling beneath an untrusted writable "
                    f"ancestor: {absolute}"
                )
            entry_stat = os.stat(
                name,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISDIR(entry_stat.st_mode)
                or stat.S_ISLNK(entry_stat.st_mode)
                or int(entry_stat.st_uid) not in trusted_owners
            ):
                raise RuntimeError(
                    "refusing a POSIX owned sibling beneath an untrusted ancestor "
                    f"entry: {absolute}"
                )
            child = os.open(name, _posix_directory_open_flags(), dir_fd=descriptor)
            opened_stat = os.fstat(child)
            if not _same_posix_identity(entry_stat, opened_stat):
                os.close(child)
                raise RuntimeError(
                    "POSIX ancestor changed identity during validation; refusing "
                    f"owned sibling creation: {absolute}"
                )
            os.close(descriptor)
            descriptor = child

        final_stat = os.fstat(descriptor)
        final_mode = stat.S_IMODE(final_stat.st_mode)
        if (
            int(final_stat.st_uid) not in trusted_owners
            or (final_mode & 0o022 and not final_stat.st_mode & stat.S_ISVTX)
            or not _same_posix_identity(final_stat, expected)
        ):
            raise RuntimeError(
                "refusing an untrusted or replaced POSIX ancestor chain for owned "
                f"sibling creation: {absolute}"
            )
    finally:
        os.close(descriptor)


def _validate_posix_creation_parent(
    descriptor: int,
    path: Path,
    expected: os.stat_result | None = None,
) -> os.stat_result:
    opened = os.fstat(descriptor)
    try:
        observed = path.lstat()
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"owned sibling parent disappeared during creation: {path}"
        ) from exc
    effective_user_id = _effective_user_id()
    group_or_other_writable = bool(stat.S_IMODE(opened.st_mode) & 0o022)
    sticky = bool(opened.st_mode & stat.S_ISVTX)
    if (
        not stat.S_ISDIR(opened.st_mode)
        or stat.S_ISLNK(observed.st_mode)
        or not _same_posix_identity(opened, observed)
        or effective_user_id is None
        or int(opened.st_uid) not in {0, effective_user_id}
        or (group_or_other_writable and not sticky)
        or (expected is not None and not _same_posix_identity(opened, expected))
    ):
        raise RuntimeError(
            "refusing an untrusted or replaced parent directory for POSIX owned "
            f"sibling creation: {path}"
        )
    _validate_posix_ancestor_chain(path, opened)
    return opened


def _remove_empty_posix_directory_if_same(
    parent: int,
    name: str,
    expected: os.stat_result,
) -> None:
    try:
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not _same_posix_identity(current, expected):
        return
    try:
        os.rmdir(name, dir_fd=parent)
    except (FileNotFoundError, OSError):
        # A non-empty or concurrently changed staging directory is untrusted and
        # must be preserved. It is never recursively removed.
        return


def _posix_staging_path(path: Path) -> Path:
    return path.parent / (
        ".protocyte-stage-" + hashlib.sha256(os.fsencode(path.name)).hexdigest()[:32]
    )


def _posix_create_owned_directory(path: Path) -> int:
    parent = os.open(path.parent, _posix_directory_open_flags())
    try:
        parent_identity = _validate_posix_creation_parent(parent, path.parent)
    except BaseException:
        os.close(parent)
        raise
    parent_device = int(parent_identity.st_dev)
    stage_path = _posix_staging_path(path)
    stage_name = stage_path.name
    child_name = "owned"
    stage: int | None = None
    child: int | None = None
    stage_identity: os.stat_result | None = None
    child_identity: os.stat_result | None = None
    published = False
    returned = False
    try:
        os.mkdir(stage_name, 0o700, dir_fd=parent)
        stage_identity = os.stat(
            stage_name,
            dir_fd=parent,
            follow_symlinks=False,
        )
        _owned_sibling_creation_phase("after_staging_mkdir", stage_path)
        stage = _posix_open_child_directory(parent, stage_name, parent_device)
        opened_stage = _validate_posix_staging_directory(
            stage,
            stage_path,
            parent_device,
        )
        if not _same_posix_identity(stage_identity, opened_stage):
            raise RuntimeError(
                "POSIX staging directory changed identity before it was opened; "
                f"refusing owned sibling creation: {stage_path}"
            )

        os.mkdir(child_name, 0o700, dir_fd=stage)
        child_identity = os.stat(
            child_name,
            dir_fd=stage,
            follow_symlinks=False,
        )
        _owned_sibling_creation_phase(
            "after_staging_child_mkdir",
            stage_path / child_name,
        )
        child = _posix_open_child_directory(stage, child_name, parent_device)
        opened_child = _validate_posix_staging_directory(
            child,
            stage_path / child_name,
            parent_device,
        )
        if not _same_posix_identity(child_identity, opened_child):
            raise RuntimeError(
                "POSIX staged child changed identity before it was opened; "
                f"refusing owned sibling creation: {stage_path / child_name}"
            )

        _validate_posix_creation_parent(parent, path.parent, parent_identity)
        _posix_renameat_no_replace(stage, child_name, parent, path.name)
        published = True
        observed = _posix_open_child_directory(parent, path.name, parent_device)
        try:
            if not _same_posix_identity(os.fstat(child), os.fstat(observed)):
                raise _unowned_sibling_error(path)
        finally:
            os.close(observed)
        _validate_posix_creation_parent(parent, path.parent, parent_identity)

        current_stage = os.stat(
            stage_name,
            dir_fd=parent,
            follow_symlinks=False,
        )
        if not _same_posix_identity(current_stage, opened_stage):
            raise RuntimeError(
                "POSIX staging namespace changed identity during publication; "
                f"refusing to remove it: {stage_path}"
            )
        if os.listdir(stage):
            raise RuntimeError(
                "POSIX staging namespace gained unexpected entries during "
                f"publication; refusing to remove it: {stage_path}"
            )
        os.rmdir(stage_name, dir_fd=parent)
        os.fsync(parent)
        _owned_namespace_phase("after_create_parent_fsync", path.parent)
        returned = True
        return child
    finally:
        if child is not None and not returned:
            os.close(child)
        if not published and child_identity is not None and stage is not None:
            _remove_empty_posix_directory_if_same(
                stage,
                child_name,
                child_identity,
            )
        if stage is not None:
            os.close(stage)
        if stage_identity is not None:
            _remove_empty_posix_directory_if_same(
                parent,
                stage_name,
                stage_identity,
            )
        os.close(parent)


def _windows_directory_entries(
    handle: object,
) -> tuple[tuple[str, int, int, int], ...]:
    entries: list[tuple[str, int, int, int]] = []
    restart = True
    while True:
        buffer = ctypes.create_string_buffer(64 * 1024)
        information_class = (
            _FILE_ID_EXTD_DIRECTORY_RESTART_INFO_CLASS
            if restart
            else _FILE_ID_EXTD_DIRECTORY_INFO_CLASS
        )
        restart = False
        if not _kernel32.GetFileInformationByHandleEx(
            handle,
            information_class,
            buffer,
            ctypes.sizeof(buffer),
        ):
            error = ctypes.get_last_error()
            if error == _ERROR_NO_MORE_FILES:
                break
            raise ctypes.WinError(error)

        offset = 0
        while True:
            address = ctypes.addressof(buffer) + offset
            information = ctypes.cast(
                address,
                ctypes.POINTER(_WindowsFileIdExtdDirectoryInfo),
            ).contents
            name_length = int(information.FileNameLength)
            if name_length % ctypes.sizeof(wintypes.WCHAR):
                raise RuntimeError("Windows returned a malformed directory entry")
            name = ctypes.wstring_at(
                address + _WindowsFileIdExtdDirectoryInfo.FileName.offset,
                name_length // ctypes.sizeof(wintypes.WCHAR),
            )
            if name not in {".", ".."}:
                entries.append(
                    (
                        name,
                        int.from_bytes(
                            bytes(information.FileId.Identifier),
                            "little",
                        ),
                        int(information.FileAttributes),
                        int(information.ReparsePointTag)
                        if information.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT
                        else 0,
                    )
                )
            next_offset = int(information.NextEntryOffset)
            if next_offset == 0:
                break
            if next_offset < _WindowsFileIdExtdDirectoryInfo.FileName.offset:
                raise RuntimeError("Windows returned a malformed directory entry")
            offset += next_offset
            if offset >= ctypes.sizeof(buffer):
                raise RuntimeError("Windows returned a malformed directory entry")
    return tuple(entries)


def _windows_open_child_handle(
    parent: object,
    name: str,
    recorded_path: Path,
    *,
    access: int | None = None,
) -> object:
    if access is None:
        access = (
            _DELETE
            | _READ_CONTROL
            | _SYNCHRONIZE
            | _FILE_LIST_DIRECTORY
            | _FILE_READ_ATTRIBUTES
        )
    name_buffer = ctypes.create_unicode_buffer(name)
    object_name = _WindowsUnicodeString(
        len(name.encode("utf-16-le")),
        len(name_buffer) * ctypes.sizeof(wintypes.WCHAR),
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _WindowsObjectAttributes(
        ctypes.sizeof(_WindowsObjectAttributes),
        parent,
        ctypes.pointer(object_name),
        _OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    io_status = _WindowsIoStatusBlock()
    child = wintypes.HANDLE()
    status = _ntdll.NtCreateFile(
        ctypes.byref(child),
        access,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        _FILE_ATTRIBUTE_NORMAL,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE,
        _NT_FILE_OPEN,
        _FILE_SYNCHRONOUS_IO_NONALERT | _NT_FILE_OPEN_REPARSE_POINT,
        None,
        0,
    )
    if status < 0:
        error = int(_ntdll.RtlNtStatusToDosError(status))
        if error in {_ERROR_FILE_NOT_FOUND, _ERROR_PATH_NOT_FOUND}:
            raise FileNotFoundError(error, os.strerror(error), recorded_path)
        raise OSError(error, os.strerror(error), recorded_path)
    return child


def _remove_windows_directory_contents(
    handle: object,
    path: Path,
    root_device: int,
) -> None:
    while True:
        entries = _windows_directory_entries(handle)
        if not entries:
            return
        for name, file_id, attributes, reparse_tag in entries:
            child_path = path / name
            _owned_windows_entry_phase("after_enumerate", child_path)
            try:
                child = _windows_open_child_handle(handle, name, child_path)
            except FileNotFoundError as exc:
                _owned_windows_entry_phase("after_missing", child_path)
                raise RuntimeError(
                    "owned transaction child disappeared after enumeration; "
                    f"refusing removal: {child_path}"
                ) from exc
            try:
                identity = _windows_handle_identity(child, child_path)
                expected_type = (
                    stat.S_IFDIR
                    if attributes & _FILE_ATTRIBUTE_DIRECTORY
                    else stat.S_IFREG
                )
                if (
                    identity["device"] != root_device
                    or identity["inode"] != file_id
                    or identity["type"] != expected_type
                    or identity["reparse_tag"] != reparse_tag
                ):
                    raise RuntimeError(
                        "owned transaction child changed identity during cleanup; "
                        f"refusing removal: {child_path}"
                    )
                if identity["type"] == stat.S_IFDIR and identity["reparse_tag"] == 0:
                    _remove_windows_directory_contents(
                        child,
                        child_path,
                        root_device,
                    )
                _windows_delete_handle(child)
            finally:
                _kernel32.CloseHandle(child)


class _OwnedDirectoryHandle:
    def __init__(self, handle: object) -> None:
        self._handle = handle

    @classmethod
    def create(cls, path: Path) -> _OwnedDirectoryHandle:
        if os.name == "nt":
            return cls(_windows_owned_directory_handle(path, create=True))
        return cls(_posix_create_owned_directory(path))

    @classmethod
    def open(cls, path: Path) -> _OwnedDirectoryHandle:
        if os.name == "nt":
            return cls(_windows_owned_directory_handle(path, create=False))
        return cls(os.open(path, _posix_directory_open_flags()))

    def identity(self, recorded_path: Path) -> dict[str, object]:
        if self._handle is None:
            raise RuntimeError("owned directory handle is closed")
        if os.name == "nt":
            return _windows_handle_identity(self._handle, recorded_path)
        return _directory_identity_from_stat(os.fstat(self._handle), recorded_path)

    def matches_path(self, path: Path, recorded_path: Path) -> bool:
        if self._handle is None:
            return False
        try:
            if os.name == "nt":
                observed = _windows_observe_directory_handle(path)
                try:
                    identity = _windows_handle_identity(observed, recorded_path)
                finally:
                    _kernel32.CloseHandle(observed)
            else:
                observed = os.open(path, _posix_directory_open_flags())
                try:
                    identity = _directory_identity_from_stat(
                        os.fstat(observed), recorded_path
                    )
                finally:
                    os.close(observed)
        except OSError:
            return False
        return _same_filesystem_object(self.identity(recorded_path), identity)

    def rename(self, source: Path, target: Path, recorded_path: Path) -> None:
        if self._handle is None:
            raise RuntimeError("owned directory handle is closed")
        if os.name == "nt":
            _windows_rename_handle(self._handle, target)
        else:
            if source.parent != target.parent:
                raise RuntimeError(
                    "owned sibling detach must remain in one parent directory"
                )
            parent = os.open(source.parent, _posix_directory_open_flags())
            try:
                _validate_posix_creation_parent(parent, source.parent)
                observed = os.open(
                    source.name,
                    _posix_directory_open_flags(),
                    dir_fd=parent,
                )
                try:
                    observed_identity = _directory_identity_from_stat(
                        os.fstat(observed), recorded_path
                    )
                finally:
                    os.close(observed)
                if not _same_filesystem_object(
                    self.identity(recorded_path), observed_identity
                ):
                    raise _unowned_sibling_error(source)
                _posix_renameat_no_replace(
                    parent,
                    source.name,
                    parent,
                    target.name,
                )
                observed = os.open(
                    target.name,
                    _posix_directory_open_flags(),
                    dir_fd=parent,
                )
                try:
                    observed_identity = _directory_identity_from_stat(
                        os.fstat(observed), recorded_path
                    )
                finally:
                    os.close(observed)
                if not _same_filesystem_object(
                    self.identity(recorded_path), observed_identity
                ):
                    raise _unowned_sibling_error(target)
            finally:
                os.close(parent)
        if not self.matches_path(target, recorded_path):
            raise _unowned_sibling_error(target)
        _sync_directory(target.parent)
        _owned_namespace_phase("after_detach_parent_fsync", target.parent)

    def remove_tree(self, path: Path, recorded_path: Path) -> None:
        if self._handle is None:
            raise RuntimeError("owned directory handle is closed")
        if not self.matches_path(path, recorded_path):
            raise _unowned_sibling_error(path)
        _owned_sibling_cleanup_phase("after_verify", path)
        if os.name == "nt":
            root_identity = self.identity(recorded_path)
            root_device = int(root_identity["device"])
            parent = _windows_durable_parent_handle(path, root_identity)
            try:
                _remove_windows_directory_contents(self._handle, path, root_device)
                _windows_delete_handle(self._handle)
                self.close()
                _owned_namespace_phase("before_remove_parent_fsync", path.parent)
                _windows_sync_directory_handle(parent)
                _owned_namespace_phase("after_remove_parent_fsync", path.parent)
            finally:
                _kernel32.CloseHandle(parent)
            return
        root_device = int(os.fstat(self._handle).st_dev)
        _remove_posix_directory_contents(self._handle, root_device)
        if not self.matches_path(path, recorded_path):
            raise _unowned_sibling_error(path)
        parent = os.open(path.parent, _posix_directory_open_flags())
        try:
            _validate_posix_creation_parent(parent, path.parent)
            observed = os.open(
                path.name,
                _posix_directory_open_flags(),
                dir_fd=parent,
            )
            try:
                observed_identity = _directory_identity_from_stat(
                    os.fstat(observed), recorded_path
                )
            finally:
                os.close(observed)
            if not _same_filesystem_object(
                self.identity(recorded_path), observed_identity
            ):
                raise _unowned_sibling_error(path)
            os.rmdir(path.name, dir_fd=parent)
            os.fsync(parent)
            _owned_namespace_phase("after_remove_parent_fsync", path.parent)
        finally:
            os.close(parent)
        self.close()

    def close(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        if os.name == "nt":
            _kernel32.CloseHandle(handle)
        else:
            os.close(handle)


@dataclass
class OwnedSibling:
    destination: Path
    kind: str
    token: str
    path: Path
    marker_path: Path
    _lease: _KernelFileLock
    _owned_paths: dict[str, dict[str, object]]
    _sibling_location: str
    _generation: int
    _directory: _OwnedDirectoryHandle | None = None

    @property
    def cleanup_path(self) -> Path:
        return _owned_sibling_cleanup_path(self.destination, self.kind, self.token)

    def _replace_marker(self) -> None:
        self._generation = _publish_journal(
            self.marker_path,
            self.destination,
            self.kind,
            self.token,
            self._owned_paths,
            self._sibling_location,
            self._generation,
        )

    def bind_path(
        self,
        label: str,
        path: Path,
        *,
        identity_source: Path | None = None,
    ) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]*", label) is None:
            raise ValueError(f"invalid owned path label: {label!r}")
        if label == _OWNED_SIBLING_LABEL:
            raise ValueError(f"reserved owned path label: {label!r}")
        self._bind_path(label, path, identity_source=identity_source)

    def bind_identity(
        self,
        label: str,
        path: Path,
        identity: dict[str, object],
    ) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]*", label) is None:
            raise ValueError(f"invalid owned path label: {label!r}")
        if label == _OWNED_SIBLING_LABEL:
            raise ValueError(f"reserved owned path label: {label!r}")
        if not _valid_owned_sibling_identity(identity, path):
            raise RuntimeError(
                f"cannot establish a durable identity for owned path: {path}"
            )
        owned_paths = dict(self._owned_paths)
        owned_paths[label] = dict(identity)
        self._owned_paths = owned_paths
        self._replace_marker()

    def _bind_path(
        self,
        label: str,
        path: Path,
        *,
        identity_source: Path | None = None,
    ) -> None:
        owned_paths = dict(self._owned_paths)
        identity = _owned_path_identity(
            identity_source or path,
            recorded_path=path,
        )
        owned_paths[label] = identity
        # Keep the in-process identity even if persisting it fails, so the
        # process that performed the rename can still put the path back. A
        # subsequent process will fail closed unless the marker was durable.
        self._owned_paths = owned_paths
        self._replace_marker()

    def _persist_sibling_identity(self, identity: dict[str, object]) -> None:
        if not _valid_owned_sibling_identity(identity, self.path):
            raise RuntimeError(
                f"cannot establish a durable identity for owned sibling: {self.path}"
            )
        owned_paths = dict(self._owned_paths)
        owned_paths[_OWNED_SIBLING_LABEL] = identity
        self._owned_paths = owned_paths
        self._sibling_location = "original"
        self._replace_marker()

    def _set_sibling_location(self, location: str) -> None:
        self._sibling_location = location
        self._replace_marker()

    def owns_path(self, label: str, path: Path) -> bool:
        expected = self._owned_paths.get(label)
        if expected is None:
            return False
        return _owned_path_matches(expected, path)

    def close(self, *, remove_marker: bool) -> None:
        if self._directory is not None:
            self._directory.close()
            self._directory = None
        if not remove_marker:
            self._lease.close()
            return
        try:
            with _locked_registry() as state_directory:
                # Windows cannot unlink the marker while its lease is open.
                # The registry prevents a recovery claimant from opening the
                # marker in the close-to-unlink window.
                if not self._lease.matches_path(self.marker_path):
                    raise RuntimeError(
                        "ownership lease was replaced; refusing to remove state: "
                        f"{self.marker_path}"
                    )
                self._lease.close()
                try:
                    self.marker_path.unlink()
                except FileNotFoundError:
                    pass
                _sync_directory(self.marker_path.parent)
                _owned_retirement_phase("after_lease_unlink", self.marker_path)
                _remove_journal_artifacts(self.marker_path)
                _prune_destination_state(self.destination, state_directory)
        finally:
            self._lease.close()

    def _open_matching_directory(
        self,
        candidate: Path,
        expected: dict[str, object],
    ) -> tuple[_OwnedDirectoryHandle | None, bool]:
        exists = _path_exists_without_following(candidate)
        if not exists:
            return None, False
        try:
            directory = _OwnedDirectoryHandle.open(candidate)
        except OSError:
            return None, True
        try:
            if directory.identity(self.path) != expected:
                directory.close()
                return None, True
            return directory, True
        except BaseException:
            directory.close()
            raise

    def _acquire_directory(
        self,
    ) -> tuple[_OwnedDirectoryHandle | None, str | None]:
        expected = self._owned_paths.get(_OWNED_SIBLING_LABEL)
        original_exists = _path_exists_without_following(self.path)
        cleanup_exists = _path_exists_without_following(self.cleanup_path)
        if expected is None:
            staging_exists = os.name != "nt" and _path_exists_without_following(
                _posix_staging_path(self.path)
            )
            if original_exists or cleanup_exists or staging_exists:
                raise _unowned_sibling_error(self.path)
            return None, None

        if self._directory is not None:
            original_matches = self._directory.matches_path(self.path, self.path)
            cleanup_matches = self._directory.matches_path(self.cleanup_path, self.path)
            original = self._directory if original_matches else None
            cleanup = self._directory if cleanup_matches else None
        else:
            original, original_exists = self._open_matching_directory(
                self.path, expected
            )
            cleanup, cleanup_exists = self._open_matching_directory(
                self.cleanup_path, expected
            )

        if original is not None and cleanup is not None:
            if original is not cleanup:
                original.close()
                cleanup.close()
            raise _unowned_sibling_error(self.path)

        if self._sibling_location == "original":
            if original is not None and not cleanup_exists:
                return original, "original"
        elif self._sibling_location == "detaching":
            if cleanup is not None:
                if original is not None and original is not cleanup:
                    original.close()
                return cleanup, "cleanup"
            if original is not None and not cleanup_exists:
                return original, "original"
        elif self._sibling_location == "cleanup":
            if cleanup is not None:
                if original is not None and original is not cleanup:
                    original.close()
                return cleanup, "cleanup"
            if not cleanup_exists and not original_exists:
                return None, None
        elif self._sibling_location == "creating":
            if not original_exists and not cleanup_exists:
                return None, None

        if original is not None and original is not self._directory:
            original.close()
        if cleanup is not None and cleanup is not self._directory:
            cleanup.close()
        raise _unowned_sibling_error(self.path)

    def _transition_to_cleanup(
        self,
        directory: _OwnedDirectoryHandle,
        actual_location: str,
    ) -> None:
        if actual_location == "cleanup":
            if self._sibling_location != "cleanup":
                self._set_sibling_location("cleanup")
            return

        if self._sibling_location == "original":
            self._set_sibling_location("detaching")
        if _path_exists_without_following(self.cleanup_path):
            raise _unowned_sibling_error(self.cleanup_path)
        _owned_sibling_cleanup_phase("before_detach", self.path)
        directory.rename(self.path, self.cleanup_path, self.path)
        _owned_sibling_cleanup_phase("after_detach", self.cleanup_path)
        self._set_sibling_location("cleanup")

    def cleanup(self, remove_path: Callable[[Path], None]) -> None:
        # Callers retain the historical callback parameter, but recursive removal
        # is intentionally internal so it can stay anchored to the verified object.
        del remove_path
        try:
            directory, actual_location = self._acquire_directory()
            if directory is None or actual_location is None:
                self.close(remove_marker=True)
                return
            self._directory = directory
            self._transition_to_cleanup(directory, actual_location)
            _owned_sibling_cleanup_phase("before_remove", self.cleanup_path)
            directory.remove_tree(self.cleanup_path, self.path)
            self._directory = None
            _owned_sibling_cleanup_phase("after_remove", self.cleanup_path)
        except BaseException:
            self.close(remove_marker=False)
            raise
        self.close(remove_marker=True)


def create_owned_sibling(destination: Path, kind: str) -> OwnedSibling:
    _validate_kind(kind)
    with _locked_registry() as state_directory:
        _ensure_destination_state_directory(destination, state_directory)
        while True:
            token = uuid.uuid4().hex
            marker_path = _marker_path(
                destination,
                kind,
                token,
                state_directory,
            )
            try:
                marker_file = _open_state_file(
                    marker_path,
                    os.O_RDWR | os.O_CREAT | os.O_EXCL,
                )
            except FileExistsError:
                continue
            except BaseException:
                try:
                    marker_path.unlink()
                except FileNotFoundError:
                    pass
                raise
            break

        lease = _KernelFileLock(marker_file)
        owned_paths: dict[str, dict[str, object]] = {}
        try:
            _ensure_lock_byte(marker_file)
            lease.acquire(blocking=True)
            _sync_directory(marker_path.parent)
            generation = _publish_journal(
                marker_path,
                destination,
                kind,
                token,
                owned_paths,
                "creating",
                0,
            )
        except BaseException:
            lease.close()
            try:
                marker_path.unlink()
            except FileNotFoundError:
                pass
            _sync_directory(marker_path.parent)
            _remove_journal_artifacts(marker_path)
            _prune_destination_state(destination, state_directory)
            raise

    path = _owned_sibling_path(destination, kind, token)
    owner = OwnedSibling(
        destination,
        kind,
        token,
        path,
        marker_path,
        lease,
        owned_paths,
        "creating",
        generation,
    )
    try:
        directory = _OwnedDirectoryHandle.create(path)
        owner._directory = directory
        if os.name == "nt":
            _sync_directory(path.parent)
            _owned_namespace_phase("after_create_parent_fsync", path.parent)
        identity = directory.identity(path)
        owner._owned_paths = {_OWNED_SIBLING_LABEL: identity}
        owner._sibling_location = "original"
        _owned_sibling_creation_phase("after_create", path)
        if not directory.matches_path(path, path):
            raise _unowned_sibling_error(path)
        owner._persist_sibling_identity(identity)
    except BaseException as exc:
        try:
            owner.cleanup(lambda _candidate: None)
        except BaseException as cleanup_error:
            exc.add_note(f"owned sibling cleanup also failed: {cleanup_error}")
            owner.close(remove_marker=False)
        raise
    return owner


def _claim_dead_owner(
    destination: Path,
    kind: str,
    token: str,
) -> OwnedSibling | None:
    with _locked_registry() as state_directory:
        if _existing_destination_state_directory(destination, state_directory) is None:
            return None
        marker_path = _marker_path(destination, kind, token, state_directory)
        try:
            marker_file = _open_state_file(marker_path, os.O_RDWR)
        except FileNotFoundError:
            return None
        lease = _KernelFileLock(marker_file)
        try:
            if not lease.acquire(blocking=False):
                lease.close()
                return None
            _validate_lock_byte(marker_file, marker_path)
            owned_paths, sibling_location, generation = _read_latest_journal(
                marker_path,
                destination,
                kind,
                token,
            )
        except BaseException:
            lease.close()
            raise

    path = _owned_sibling_path(destination, kind, token)
    return OwnedSibling(
        destination,
        kind,
        token,
        path,
        marker_path,
        lease,
        owned_paths,
        sibling_location,
        generation,
    )


def _owned_marker_identities(
    destination: Path,
    kinds: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    for kind in kinds:
        _validate_kind(kind)
    marker_pattern = re.compile(
        rf"({'|'.join(re.escape(kind) for kind in kinds)})\.([0-9a-f]{{32}})\.owner"
    )
    with _locked_registry() as state_directory:
        destination_state = _existing_destination_state_directory(
            destination,
            state_directory,
        )
        if destination_state is None:
            return ()
        _prune_abandoned_owner_state(destination, destination_state)
        identities: list[tuple[str, str]] = []
        for marker_path in tuple(destination_state.iterdir()):
            match = marker_pattern.fullmatch(marker_path.name)
            if match is not None:
                identities.append((match.group(1), match.group(2)))
        return tuple(identities)


def recover_owned_siblings(
    destination: Path,
    kinds: tuple[str, ...],
    remove_path: Callable[[Path], None],
) -> None:
    for kind, token in _owned_marker_identities(destination, kinds):
        claimed = _claim_dead_owner(destination, kind, token)
        if claimed is None:
            continue
        claimed.cleanup(remove_path)


def claim_dead_owner_for_path(
    destination: Path,
    kinds: tuple[str, ...],
    label: str,
    owned_path: Path,
) -> OwnedSibling | None:
    match: OwnedSibling | None = None
    for kind, token in _owned_marker_identities(destination, kinds):
        claimed = _claim_dead_owner(destination, kind, token)
        if claimed is None:
            continue
        if not claimed.owns_path(label, owned_path):
            claimed.close(remove_marker=False)
            continue
        if match is not None:
            match.close(remove_marker=False)
            claimed.close(remove_marker=False)
            return None
        match = claimed
    return match
