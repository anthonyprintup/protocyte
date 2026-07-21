from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import stat
import sys
from pathlib import Path
from typing import Any


_SCRIPT_DIRECTORY = Path(__file__).resolve().parent
_SOURCE_TRANSACTION_DIRECTORY = _SCRIPT_DIRECTORY.parent / ".github" / "scripts"
if (_SOURCE_TRANSACTION_DIRECTORY / "owned_transactions.py").is_file():
    sys.path.insert(0, str(_SOURCE_TRANSACTION_DIRECTORY))
elif str(_SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIRECTORY))

import owned_transactions as transactions  # noqa: E402


_TRANSACTION_KIND = "managed-environment"
_OWNER_LABEL = transactions._OWNED_SIBLING_LABEL
_WINDOWS_FILE_RENAME_INFORMATION_CLASS = 10
_WINDOWS_FILE_NON_DIRECTORY_FILE = 0x00000040

if os.name == "nt":
    transactions._ntdll.NtSetInformationFile.argtypes = (
        transactions.wintypes.HANDLE,
        ctypes.POINTER(transactions._WindowsIoStatusBlock),
        ctypes.c_void_p,
        transactions.wintypes.ULONG,
        ctypes.c_int,
    )
    transactions._ntdll.NtSetInformationFile.restype = ctypes.c_long


class OwnershipError(RuntimeError):
    pass


def _managed_environment_mutation_phase(_phase: str, _path: Path) -> None:
    """Test seam immediately before each pathname mutation."""


def _managed_environment_fingerprint_phase(_phase: str, _path: Path) -> None:
    """Test seam around managed-environment fingerprint publication."""


def _path_exists_without_following(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _path_is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    path_is_junction = getattr(path, "is_junction", None)
    if path_is_junction is not None and path_is_junction():
        return True
    os_path_is_junction = getattr(os.path, "isjunction", None)
    return os_path_is_junction is not None and os_path_is_junction(path)


def _reject_link_or_junction(path: Path) -> None:
    if _path_is_link_or_junction(path):
        raise OwnershipError(
            f"managed-environment path contains a link or junction: {path}"
        )


def _windows_open_root_directory(path: Path, *, writable: bool) -> object:
    desired_access = (
        transactions._READ_CONTROL
        | transactions._SYNCHRONIZE
        | transactions._FILE_LIST_DIRECTORY
        | transactions._FILE_READ_ATTRIBUTES
    )
    if writable:
        desired_access |= (
            transactions._GENERIC_READ
            | transactions._GENERIC_WRITE
            | transactions._DELETE
        )
    handle = transactions._kernel32.CreateFileW(
        transactions._windows_extended_path(path),
        desired_access,
        transactions._FILE_SHARE_READ
        | transactions._FILE_SHARE_WRITE
        | transactions._FILE_SHARE_DELETE,
        None,
        transactions._OPEN_EXISTING,
        transactions._FILE_FLAG_OPEN_REPARSE_POINT
        | transactions._FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle == transactions.wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


def _windows_open_relative_directory(
    parent: object,
    name: str,
    recorded_path: Path,
    *,
    delete_access: bool = False,
    writable: bool = False,
    create: bool = False,
) -> object:
    name_buffer = ctypes.create_unicode_buffer(name)
    object_name = transactions._WindowsUnicodeString(
        len(name.encode("utf-16-le")),
        len(name_buffer) * ctypes.sizeof(transactions.wintypes.WCHAR),
        ctypes.cast(name_buffer, transactions.wintypes.LPWSTR),
    )
    attributes = transactions._WindowsObjectAttributes(
        ctypes.sizeof(transactions._WindowsObjectAttributes),
        parent,
        ctypes.pointer(object_name),
        transactions._OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    io_status = transactions._WindowsIoStatusBlock()
    child = transactions.wintypes.HANDLE()
    desired_access = (
        transactions._READ_CONTROL
        | transactions._SYNCHRONIZE
        | transactions._FILE_LIST_DIRECTORY
        | transactions._FILE_READ_ATTRIBUTES
    )
    if delete_access:
        desired_access |= transactions._DELETE
    if writable:
        desired_access |= (
            transactions._GENERIC_READ
            | transactions._GENERIC_WRITE
            | transactions._DELETE
        )
    share_access = transactions._FILE_SHARE_READ | transactions._FILE_SHARE_WRITE
    if not delete_access:
        share_access |= transactions._FILE_SHARE_DELETE
    status = transactions._ntdll.NtCreateFile(
        ctypes.byref(child),
        desired_access,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        transactions._FILE_ATTRIBUTE_NORMAL,
        share_access,
        transactions._NT_FILE_CREATE if create else transactions._NT_FILE_OPEN,
        transactions._FILE_DIRECTORY_FILE
        | transactions._FILE_SYNCHRONOUS_IO_NONALERT
        | transactions._NT_FILE_OPEN_REPARSE_POINT,
        None,
        0,
    )
    if status < 0:
        error = int(transactions._ntdll.RtlNtStatusToDosError(status))
        if error in {
            transactions._ERROR_FILE_NOT_FOUND,
            transactions._ERROR_PATH_NOT_FOUND,
        }:
            raise FileNotFoundError(error, os.strerror(error), recorded_path)
        if create and error in {80, transactions._ERROR_ALREADY_EXISTS}:
            raise FileExistsError(error, os.strerror(error), recorded_path)
        raise OSError(error, os.strerror(error), recorded_path)
    return child


def _windows_open_relative_file(
    parent: object,
    name: str,
    recorded_path: Path,
) -> object:
    name_buffer = ctypes.create_unicode_buffer(name)
    object_name = transactions._WindowsUnicodeString(
        len(name.encode("utf-16-le")),
        len(name_buffer) * ctypes.sizeof(transactions.wintypes.WCHAR),
        ctypes.cast(name_buffer, transactions.wintypes.LPWSTR),
    )
    attributes = transactions._WindowsObjectAttributes(
        ctypes.sizeof(transactions._WindowsObjectAttributes),
        parent,
        ctypes.pointer(object_name),
        transactions._OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    io_status = transactions._WindowsIoStatusBlock()
    child = transactions.wintypes.HANDLE()
    status = transactions._ntdll.NtCreateFile(
        ctypes.byref(child),
        transactions._GENERIC_READ
        | transactions._READ_CONTROL
        | transactions._SYNCHRONIZE
        | transactions._FILE_READ_ATTRIBUTES,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        transactions._FILE_ATTRIBUTE_NORMAL,
        transactions._FILE_SHARE_READ
        | transactions._FILE_SHARE_WRITE
        | transactions._FILE_SHARE_DELETE,
        transactions._NT_FILE_OPEN,
        _WINDOWS_FILE_NON_DIRECTORY_FILE
        | transactions._FILE_SYNCHRONOUS_IO_NONALERT
        | transactions._NT_FILE_OPEN_REPARSE_POINT,
        None,
        0,
    )
    if status < 0:
        error = int(transactions._ntdll.RtlNtStatusToDosError(status))
        if error in {
            transactions._ERROR_FILE_NOT_FOUND,
            transactions._ERROR_PATH_NOT_FOUND,
        }:
            raise FileNotFoundError(error, os.strerror(error), recorded_path)
        raise OSError(error, os.strerror(error), recorded_path)
    return child


def _windows_rename_handle_relative(
    source: object,
    target_parent: object,
    target_name: str,
) -> None:
    encoded_name = target_name.encode("utf-16-le")
    size = (
        transactions._WindowsFileRenameInfo.FileName.offset
        + len(encoded_name)
        + ctypes.sizeof(transactions.wintypes.WCHAR)
    )
    buffer = ctypes.create_string_buffer(size)
    information = ctypes.cast(
        buffer,
        ctypes.POINTER(transactions._WindowsFileRenameInfo),
    ).contents
    information.Flags = 0
    information.RootDirectory = target_parent
    information.FileNameLength = len(encoded_name)
    ctypes.memmove(
        ctypes.addressof(buffer) + transactions._WindowsFileRenameInfo.FileName.offset,
        encoded_name,
        len(encoded_name),
    )
    io_status = transactions._WindowsIoStatusBlock()
    status = transactions._ntdll.NtSetInformationFile(
        source,
        ctypes.byref(io_status),
        buffer,
        size,
        _WINDOWS_FILE_RENAME_INFORMATION_CLASS,
    )
    if status < 0:
        error = int(transactions._ntdll.RtlNtStatusToDosError(status))
        raise OSError(error, os.strerror(error), target_name)


class _PinnedDirectory:
    def __init__(self, path: Path, handle: object) -> None:
        self.path = path
        self.handle = handle

    @classmethod
    def open(cls, path: Path, *, writable: bool = False) -> _PinnedDirectory:
        absolute = Path(os.path.abspath(os.fspath(path)))
        if not absolute.anchor:
            raise OwnershipError(f"cannot anchor managed-environment directory: {path}")
        parts = absolute.parts
        current_path = Path(parts[0])
        _reject_link_or_junction(current_path)

        if os.name == "nt":
            handle = _windows_open_root_directory(
                current_path,
                writable=writable and len(parts) == 1,
            )
            try:
                identity = transactions._windows_handle_identity(handle, current_path)
                if identity["type"] != stat.S_IFDIR or identity["reparse_tag"] != 0:
                    raise OwnershipError(
                        "managed-environment ancestor is linked or not a directory: "
                        f"{current_path}"
                    )
                for index, name in enumerate(parts[1:], start=1):
                    current_path /= name
                    _reject_link_or_junction(current_path)
                    child = _windows_open_relative_directory(
                        handle,
                        name,
                        current_path,
                        writable=writable and index == len(parts) - 1,
                    )
                    transactions._kernel32.CloseHandle(handle)
                    handle = child
                    identity = transactions._windows_handle_identity(
                        handle, current_path
                    )
                    if identity["type"] != stat.S_IFDIR or identity["reparse_tag"] != 0:
                        raise OwnershipError(
                            "managed-environment ancestor is linked or not a "
                            f"directory: {current_path}"
                        )
                return cls(absolute, handle)
            except BaseException:
                transactions._kernel32.CloseHandle(handle)
                raise

        descriptor = os.open(current_path, transactions._posix_directory_open_flags())
        try:
            for name in parts[1:]:
                current_path /= name
                _reject_link_or_junction(current_path)
                child = os.open(
                    name,
                    transactions._posix_directory_open_flags(),
                    dir_fd=descriptor,
                )
                os.close(descriptor)
                descriptor = child
                observed = os.fstat(descriptor)
                if not stat.S_ISDIR(observed.st_mode):
                    raise OwnershipError(
                        "managed-environment ancestor is not a directory: "
                        f"{current_path}"
                    )
            return cls(absolute, descriptor)
        except BaseException:
            os.close(descriptor)
            raise

    def open_child(
        self,
        name: str,
        recorded_path: Path,
        *,
        delete_access: bool = False,
    ) -> object:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise OwnershipError(f"invalid managed-environment entry name: {name}")
        _reject_link_or_junction(recorded_path)
        if os.name == "nt":
            child = _windows_open_relative_directory(
                self.handle,
                name,
                recorded_path,
                delete_access=delete_access,
            )
            identity = transactions._windows_handle_identity(child, recorded_path)
            if identity["type"] != stat.S_IFDIR or identity["reparse_tag"] != 0:
                transactions._kernel32.CloseHandle(child)
                raise OwnershipError(
                    "managed-environment entry is linked or not a directory: "
                    f"{recorded_path}"
                )
            return child
        return os.open(
            name,
            transactions._posix_directory_open_flags(),
            dir_fd=self.handle,
        )

    def target_is_absent(self, name: str) -> bool:
        if os.name == "nt":
            return not any(
                os.path.normcase(entry_name) == os.path.normcase(name)
                for entry_name, _file_id, _attributes, _reparse_tag in (
                    transactions._windows_directory_entries(self.handle)
                )
            )
        try:
            os.stat(name, dir_fd=self.handle, follow_symlinks=False)
        except FileNotFoundError:
            return True
        return False

    def create_child(self, name: str, recorded_path: Path) -> dict[str, object]:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise OwnershipError(f"invalid managed-environment entry name: {name}")
        if os.name == "nt":
            child = _windows_open_relative_directory(
                self.handle,
                name,
                recorded_path,
                delete_access=True,
                create=True,
            )
            try:
                identity = transactions._windows_handle_identity(child, recorded_path)
                if identity["type"] != stat.S_IFDIR or identity["reparse_tag"] != 0:
                    raise OwnershipError(
                        "managed-environment entry is linked or not a directory: "
                        f"{recorded_path}"
                    )
            finally:
                transactions._kernel32.CloseHandle(child)
            self.sync()
            return identity

        os.mkdir(name, 0o700, dir_fd=self.handle)
        child = self.open_child(name, recorded_path)
        try:
            identity = self.identity(child, recorded_path)
        finally:
            self.close_child(child)
        self.sync()
        return identity

    def read_regular_file(self, name: str, maximum_bytes: int) -> bytes:
        recorded_path = self.path / name
        if os.name == "nt":
            handle = _windows_open_relative_file(
                self.handle,
                name,
                recorded_path,
            )
            descriptor: int | None = None
            try:
                identity = transactions._windows_handle_identity(
                    handle,
                    recorded_path,
                )
                if identity["type"] != stat.S_IFREG or identity["reparse_tag"] != 0:
                    raise OwnershipError(
                        "managed-environment marker is linked or not a regular "
                        f"file: {recorded_path}"
                    )
                descriptor = transactions.msvcrt.open_osfhandle(
                    int(handle.value),
                    os.O_RDONLY | getattr(os, "O_BINARY", 0),
                )
                handle = None
                return _read_bounded_descriptor(descriptor, maximum_bytes)
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                elif handle is not None:
                    transactions._kernel32.CloseHandle(handle)

        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=self.handle,
        )
        try:
            observed = os.fstat(descriptor)
            if not stat.S_ISREG(observed.st_mode):
                raise OwnershipError(
                    f"managed-environment marker is not a regular file: {recorded_path}"
                )
            return _read_bounded_descriptor(descriptor, maximum_bytes)
        finally:
            os.close(descriptor)

    def identity(self, handle: object, recorded_path: Path) -> dict[str, object]:
        if os.name == "nt":
            return transactions._windows_handle_identity(handle, recorded_path)
        return transactions._directory_identity_from_stat(
            os.fstat(handle), recorded_path
        )

    def sync(self) -> None:
        if os.name == "nt":
            transactions._windows_sync_directory_handle(self.handle)
        else:
            os.fsync(self.handle)

    def close_child(self, handle: object) -> None:
        if os.name == "nt":
            transactions._kernel32.CloseHandle(handle)
        else:
            os.close(handle)

    def close(self) -> None:
        if self.handle is None:
            return
        handle = self.handle
        self.handle = None
        if os.name == "nt":
            transactions._kernel32.CloseHandle(handle)
        else:
            os.close(handle)


def _same_identity(
    expected: dict[str, object],
    observed: dict[str, object],
) -> bool:
    return transactions._same_filesystem_object(expected, observed)


def _read_bounded_descriptor(descriptor: int, maximum_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = maximum_bytes + 1
    while remaining > 0:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    content = b"".join(chunks)
    if len(content) > maximum_bytes:
        raise OwnershipError("managed-environment marker is too large")
    return content


def _identity_at(path: Path, recorded_path: Path) -> dict[str, object]:
    parent = _PinnedDirectory.open(path.parent)
    try:
        child = parent.open_child(path.name, path)
        try:
            return parent.identity(child, recorded_path)
        finally:
            parent.close_child(child)
    finally:
        parent.close()


def _identity_matches_path(expected: dict[str, object], path: Path) -> bool:
    if not _path_exists_without_following(path):
        return False
    observed = _identity_at(path, path)
    return _same_identity(expected, observed)


def _move_owned_directory(
    source: Path,
    target: Path,
    expected: dict[str, object],
    phase: str,
    owner: Any,
) -> None:
    source_parent = _PinnedDirectory.open(source.parent, writable=True)
    target_parent = _PinnedDirectory.open(target.parent, writable=True)
    child: object | None = None
    observed_target: object | None = None
    try:
        child = source_parent.open_child(
            source.name,
            source,
            delete_access=True,
        )
        observed_source_identity = source_parent.identity(child, target)
        if not _same_identity(expected, observed_source_identity):
            raise OwnershipError(
                f"managed-environment source changed identity before mutation: {source}"
            )
        if not target_parent.target_is_absent(target.name):
            raise OwnershipError(
                f"managed-environment target is already occupied: {target}"
            )
        _managed_environment_mutation_phase(phase, source)
        if os.name == "nt":
            _windows_rename_handle_relative(child, target_parent.handle, target.name)
        else:
            transactions._posix_renameat_no_replace(
                source_parent.handle,
                source.name,
                target_parent.handle,
                target.name,
            )
        observed_target = target_parent.open_child(target.name, target)
        observed_target_identity = target_parent.identity(observed_target, target)
        if not _same_identity(expected, observed_target_identity):
            _mark_tainted(owner)
            raise OwnershipError(
                f"managed-environment target changed identity during mutation: {target}"
            )
        if not source_parent.target_is_absent(source.name):
            _mark_tainted(owner)
            raise OwnershipError(
                f"managed-environment source was replaced during mutation: {source}"
            )
        source_parent.sync()
        if source.parent != target.parent:
            target_parent.sync()
    finally:
        if observed_target is not None:
            target_parent.close_child(observed_target)
        if child is not None:
            source_parent.close_child(child)
        target_parent.close()
        source_parent.close()


def _ready_environment_identity(
    environment: Path,
    fingerprint: str,
) -> dict[str, object] | None:
    pinned = _PinnedDirectory.open(environment)
    try:
        identity = pinned.identity(pinned.handle, environment)
        try:
            marker = pinned.read_regular_file(".protocyte-ready", 512)
            marker_text = marker.decode("utf-8").strip()
        except (OSError, OwnershipError, UnicodeDecodeError):
            return None
        return identity if marker_text == fingerprint else None
    finally:
        pinned.close()


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
        os.path.abspath(right)
    )


def _fingerprint_path(transaction: Path, fingerprint: str) -> Path:
    fingerprint_key = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return transaction / f"fingerprint-{fingerprint_key}"


def _fingerprint_matches(owner: Any, fingerprint: str) -> bool:
    fingerprint_path = _fingerprint_path(owner.path, fingerprint)
    fingerprint_identity = owner._owned_paths.get("fingerprint")
    try:
        return (
            fingerprint_identity is not None
            and transactions._valid_owned_sibling_identity(
                fingerprint_identity,
                fingerprint_path,
            )
            and _identity_matches_path(fingerprint_identity, fingerprint_path)
        )
    except (KeyError, OSError, TypeError):
        return False


def _claim_transaction(
    destination: Path,
    transaction: Path,
    fingerprint: str,
) -> Any:
    matched_path = False
    for kind, token in transactions._owned_marker_identities(
        destination, (_TRANSACTION_KIND,)
    ):
        claimed = transactions._claim_dead_owner(destination, kind, token)
        if claimed is None:
            continue
        if not _same_path(claimed.path, transaction):
            claimed.close(remove_marker=False)
            continue
        matched_path = True
        if not claimed.owns_path(_OWNER_LABEL, transaction):
            claimed.close(remove_marker=False)
            raise OwnershipError(
                f"managed-environment transaction was replaced: {transaction}"
            )
        if not _fingerprint_matches(claimed, fingerprint):
            claimed.close(remove_marker=False)
            raise OwnershipError(
                "managed-environment transaction belongs to another "
                f"installation: {transaction}"
            )
        return claimed
    if matched_path:
        raise OwnershipError(
            f"managed-environment transaction is still active: {transaction}"
        )
    raise OwnershipError(
        f"managed-environment transaction has no trusted owner: {transaction}"
    )


def _owned_identity(owner: Any, label: str, path: Path) -> dict[str, object] | None:
    identity = owner._owned_paths.get(label)
    if identity is None:
        return None
    if not transactions._valid_owned_sibling_identity(identity, path):
        raise OwnershipError(
            f"managed-environment ownership record is invalid for {path}"
        )
    return identity


def _mark_tainted(owner: Any) -> None:
    transaction = owner.path
    transaction_identity = _owned_identity(owner, _OWNER_LABEL, transaction)
    if transaction_identity is None:
        raise OwnershipError(
            f"managed-environment transaction has no trusted identity: {transaction}"
        )
    owner.bind_identity("tainted", transaction, transaction_identity)


def _reject_tainted(owner: Any) -> None:
    if _owned_identity(owner, "tainted", owner.path) is not None:
        raise OwnershipError(
            "managed-environment transaction encountered a namespace race and "
            f"requires manual inspection: {owner.path}"
        )


def _cleanup_owner(owner: Any, phase: str = "cleanup") -> None:
    _reject_tainted(owner)
    transaction = owner.path
    expected = _owned_identity(owner, _OWNER_LABEL, transaction)
    if expected is None or not _identity_matches_path(expected, transaction):
        raise OwnershipError(
            f"managed-environment transaction was replaced before cleanup: {transaction}"
        )
    _managed_environment_mutation_phase(phase, transaction)
    owner.cleanup(lambda _path: None)


def _resume_incomplete_owner_cleanup(owner: Any) -> bool:
    _reject_tainted(owner)
    location = owner._sibling_location
    fingerprint_bound = "fingerprint" in owner._owned_paths
    if location == "original" and fingerprint_bound:
        return False
    if location == "original" and any(
        label in owner._owned_paths for label in ("previous", "candidate", "committed")
    ):
        raise OwnershipError(
            "managed-environment transaction lost its fingerprint after "
            f"filesystem changes: {owner.path}"
        )
    if location not in {"creating", "original", "detaching", "cleanup"}:
        raise OwnershipError(
            f"managed-environment transaction has an invalid location: {owner.path}"
        )

    cleanup_source = owner.path
    if location in {"detaching", "cleanup"} and _path_exists_without_following(
        owner.cleanup_path
    ):
        cleanup_source = owner.cleanup_path
    _managed_environment_mutation_phase("recovery_cleanup", cleanup_source)
    owner.cleanup(lambda _path: None)
    return True


def _new_transaction(destination: Path, fingerprint: str) -> Path:
    parent = _PinnedDirectory.open(destination.parent, writable=True)
    owner: Any | None = None
    try:
        owner = transactions.create_owned_sibling(destination, _TRANSACTION_KIND)
        expected = _owned_identity(owner, _OWNER_LABEL, owner.path)
        if expected is None:
            raise OwnershipError(
                f"could not verify managed-environment transaction: {owner.path}"
            )
        child = parent.open_child(owner.path.name, owner.path)
        try:
            parent_identity = parent.identity(child, owner.path)
        finally:
            parent.close_child(child)
        current = _PinnedDirectory.open(owner.path)
        try:
            current_identity = current.identity(current.handle, owner.path)
        finally:
            current.close()
        if not _same_identity(expected, parent_identity) or not _same_identity(
            expected,
            current_identity,
        ):
            raise OwnershipError(
                f"could not anchor managed-environment transaction: {owner.path}"
            )
        if owner._directory is not None:
            owner._directory.close()
            owner._directory = None
        fingerprint_path = _fingerprint_path(owner.path, fingerprint)
        transaction_directory = _PinnedDirectory.open(owner.path, writable=True)
        try:
            transaction_identity = transaction_directory.identity(
                transaction_directory.handle,
                owner.path,
            )
            if not _same_identity(expected, transaction_identity):
                raise OwnershipError(
                    "managed-environment transaction changed identity before "
                    f"fingerprint binding: {owner.path}"
                )
            fingerprint_identity = transaction_directory.create_child(
                fingerprint_path.name,
                fingerprint_path,
            )
        finally:
            transaction_directory.close()
        _managed_environment_fingerprint_phase("after_create", fingerprint_path)
        owner.bind_identity(
            "fingerprint",
            fingerprint_path,
            fingerprint_identity,
        )
        _managed_environment_fingerprint_phase("after_bind", fingerprint_path)
        return owner.path
    except BaseException as error:
        if owner is not None:
            try:
                owner.cleanup(lambda _path: None)
            except BaseException as cleanup_error:
                error.add_note(
                    "managed-environment transaction cleanup also failed: "
                    f"{cleanup_error}"
                )
                owner.close(remove_marker=False)
        raise
    finally:
        if owner is not None:
            owner.close(remove_marker=False)
        parent.close()


def _backup(destination: Path, transaction: Path, fingerprint: str) -> None:
    owner = _claim_transaction(destination, transaction, fingerprint)
    try:
        _reject_tainted(owner)
        identity = _ready_environment_identity(destination, fingerprint)
        if identity is None:
            raise OwnershipError(
                "refusing to retire a managed Python environment without a "
                f"matching ready marker: {destination}"
            )
        previous = transaction / "previous"
        identity = dict(identity)
        identity["path_key"] = transactions._destination_key(previous)
        owner.bind_identity("previous", previous, identity)
        _move_owned_directory(destination, previous, identity, "backup", owner)
    finally:
        owner.close(remove_marker=False)


def _prepare_candidate(
    destination: Path,
    transaction: Path,
    fingerprint: str,
) -> None:
    owner = _claim_transaction(destination, transaction, fingerprint)
    try:
        _reject_tainted(owner)
        staging = transaction / "staging"
        staging_identity = _ready_environment_identity(staging, fingerprint)
        if staging_identity is None:
            raise OwnershipError(
                f"managed-environment staging directory is not ready: {staging}"
            )
        owner.bind_identity("candidate", staging, staging_identity)
    finally:
        owner.close(remove_marker=False)


def _promote(destination: Path, transaction: Path, fingerprint: str) -> None:
    owner = _claim_transaction(destination, transaction, fingerprint)
    try:
        _reject_tainted(owner)
        staging = transaction / "staging"
        candidate = _owned_identity(owner, "candidate", staging)
        if candidate is None:
            raise OwnershipError(
                f"managed-environment transaction has no prepared replacement: {transaction}"
            )
        _move_owned_directory(staging, destination, candidate, "promote", owner)
    finally:
        owner.close(remove_marker=False)


def _commit(
    destination: Path,
    transaction: Path,
    fingerprint: str,
) -> None:
    owner = _claim_transaction(destination, transaction, fingerprint)
    try:
        _reject_tainted(owner)
        observed = _ready_environment_identity(destination, fingerprint)
        if observed is None:
            raise OwnershipError(
                "refusing to commit a managed Python environment without a "
                f"ready marker: {destination}"
            )
        candidate = _owned_identity(owner, "candidate", transaction / "staging")
        if candidate is None:
            raise OwnershipError(
                f"managed-environment transaction has no promoted replacement: {transaction}"
            )
        if not _same_identity(candidate, observed):
            raise OwnershipError(
                "refusing to commit a replaced managed Python environment: "
                f"{destination}"
            )
        owner.bind_identity("committed", destination, observed)
    finally:
        owner.close(remove_marker=False)


def _restore(destination: Path, transaction: Path, fingerprint: str) -> None:
    owner = _claim_transaction(destination, transaction, fingerprint)
    cleaned = False
    try:
        _reject_tainted(owner)
        candidate = _owned_identity(owner, "candidate", transaction / "staging")
        if _path_exists_without_following(destination):
            if candidate is None:
                raise OwnershipError(
                    "refusing to restore over an unverified managed Python "
                    f"environment: {destination}"
                )
            _move_owned_directory(
                destination,
                transaction / "discarded",
                candidate,
                "rollback_discard",
                owner,
            )
        previous = transaction / "previous"
        previous_identity = _owned_identity(owner, "previous", previous)
        if previous_identity is not None:
            _move_owned_directory(
                previous,
                destination,
                previous_identity,
                "rollback_restore",
                owner,
            )
        _cleanup_owner(owner)
        cleaned = True
    finally:
        if not cleaned:
            owner.close(remove_marker=False)


def _recover_owner(destination: Path, owner: Any) -> None:
    _reject_tainted(owner)
    transaction = owner.path
    previous = transaction / "previous"
    previous_identity = _owned_identity(owner, "previous", previous)
    candidate = _owned_identity(owner, "candidate", transaction / "staging")
    committed = _owned_identity(owner, "committed", destination)

    if previous_identity is None:
        if _path_exists_without_following(destination) and candidate is not None:
            if committed is None:
                _move_owned_directory(
                    destination,
                    transaction / "discarded",
                    candidate,
                    "recovery_discard",
                    owner,
                )
            elif not _identity_matches_path(committed, destination):
                raise OwnershipError(
                    "managed-environment committed replacement changed identity: "
                    f"{destination}"
                )
        _cleanup_owner(owner, "recovery_cleanup")
        return

    previous_exists = _path_exists_without_following(previous)
    destination_exists = _path_exists_without_following(destination)
    if previous_exists:
        if not destination_exists:
            _move_owned_directory(
                previous,
                destination,
                previous_identity,
                "recovery_restore",
                owner,
            )
        elif candidate is not None and _identity_matches_path(candidate, destination):
            if committed is None:
                _move_owned_directory(
                    destination,
                    transaction / "discarded",
                    candidate,
                    "recovery_discard",
                    owner,
                )
                _move_owned_directory(
                    previous,
                    destination,
                    previous_identity,
                    "recovery_restore",
                    owner,
                )
            elif not _identity_matches_path(committed, destination):
                raise OwnershipError(
                    "managed-environment committed replacement changed identity: "
                    f"{destination}"
                )
        else:
            raise OwnershipError(
                "refusing recovery because the live managed Python environment "
                f"does not match its transaction: {destination}"
            )
    elif not destination_exists or not _identity_matches_path(
        previous_identity, destination
    ):
        raise OwnershipError(
            f"managed-environment backup disappeared or changed identity: {previous}"
        )
    _cleanup_owner(owner, "recovery_cleanup")


def _recover(destination: Path, fingerprint: str) -> None:
    for kind, token in transactions._owned_marker_identities(
        destination, (_TRANSACTION_KIND,)
    ):
        owner = transactions._claim_dead_owner(destination, kind, token)
        if owner is None:
            continue
        cleaned = False
        try:
            if _resume_incomplete_owner_cleanup(owner):
                cleaned = True
                continue
            if not owner.owns_path(_OWNER_LABEL, owner.path):
                raise OwnershipError(
                    f"managed-environment transaction was replaced: {owner.path}"
                )
            if not _fingerprint_matches(owner, fingerprint):
                raise OwnershipError(
                    "managed-environment transaction belongs to another "
                    f"installation: {owner.path}"
                )
            _recover_owner(destination, owner)
            cleaned = True
        finally:
            if not cleaned:
                owner.close(remove_marker=False)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "create",
            "backup",
            "prepare",
            "promote",
            "restore",
            "commit",
            "cleanup",
            "recover",
        ),
    )
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--transaction", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.action == "create":
            print(_new_transaction(args.destination, args.fingerprint).as_posix())
            return 0
        if args.action == "recover":
            _recover(args.destination, args.fingerprint)
            return 0
        if args.transaction is None:
            raise OwnershipError(f"--transaction is required for {args.action}")
        if args.action == "backup":
            _backup(args.destination, args.transaction, args.fingerprint)
        elif args.action == "prepare":
            _prepare_candidate(args.destination, args.transaction, args.fingerprint)
        elif args.action == "promote":
            _promote(args.destination, args.transaction, args.fingerprint)
        elif args.action == "restore":
            _restore(args.destination, args.transaction, args.fingerprint)
        elif args.action == "commit":
            _commit(args.destination, args.transaction, args.fingerprint)
        elif args.action == "cleanup":
            owner = _claim_transaction(
                args.destination,
                args.transaction,
                args.fingerprint,
            )
            cleaned = False
            try:
                _cleanup_owner(owner)
                cleaned = True
            finally:
                if not cleaned:
                    owner.close(remove_marker=False)
        return 0
    except (OSError, OwnershipError, RuntimeError) as error:
        print(
            f"Protocyte managed-environment transaction error: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
