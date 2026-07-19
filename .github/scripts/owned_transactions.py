from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Iterator


_MARKER_SCHEMA = 3
_STATE_DIRECTORY_ENV = "PROTOCYTE_TRANSACTION_STATE_DIR"
_STATE_DIRECTORY_NAME = "protocyte-owned-transactions-v2"


class _KernelFileLock:
    def __init__(self, file: BinaryIO) -> None:
        self._file = file
        self._locked = False

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

    def replace_content(self, content: bytes) -> None:
        if not self._locked:
            raise RuntimeError("cannot update an unlocked ownership marker")
        self._file.seek(0)
        self._file.truncate()
        self._file.write(content)
        self._file.flush()
        os.fsync(self._file.fileno())


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


def _state_directory() -> Path:
    configured = os.environ.get(_STATE_DIRECTORY_ENV)
    state = (
        Path(configured)
        if configured
        else Path(tempfile.gettempdir())
        / f"{_STATE_DIRECTORY_NAME}-{_user_namespace()}"
    )
    try:
        state.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError:
        pass
    _validate_state_directory(state)
    return state


def _open_state_file(path: Path, flags: int) -> BinaryIO:
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


@contextmanager
def locked_destination(destination: Path) -> Iterator[None]:
    lock_path = _state_directory() / f"{_destination_key(destination)}.destination.lock"
    file = _open_state_file(lock_path, os.O_RDWR | os.O_CREAT)
    lock = _KernelFileLock(file)
    try:
        _ensure_lock_byte(file)
        lock.acquire(blocking=True)
        yield
    finally:
        lock.close()


def _validate_kind(kind: str) -> None:
    if re.fullmatch(r"[a-z][a-z0-9-]*", kind) is None:
        raise ValueError(f"invalid owned transaction kind: {kind!r}")


def _marker_path(destination: Path, kind: str, token: str) -> Path:
    return _state_directory() / (
        f"{_destination_key(destination)}.{kind}.{token}.owner"
    )


def _marker_payload(
    destination: Path,
    kind: str,
    token: str,
    owned_paths: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": _MARKER_SCHEMA,
        "destination_key": _destination_key(destination),
        "kind": kind,
        "token": token,
        "owned_paths": owned_paths,
    }


def _encode_marker(
    destination: Path,
    kind: str,
    token: str,
    owned_paths: dict[str, dict[str, object]],
) -> bytes:
    return json.dumps(
        _marker_payload(destination, kind, token, owned_paths),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


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


def _read_owned_paths(
    content: bytes,
    destination: Path,
    kind: str,
    token: str,
) -> dict[str, dict[str, object]] | None:
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    owned_paths = payload.get("owned_paths")
    if not isinstance(owned_paths, dict):
        return None
    expected = _marker_payload(destination, kind, token, owned_paths)
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
            isinstance(identity[field], int)
            for field in ("device", "inode", "type", "reparse_tag")
        )
        for label, identity in owned_paths.items()
    ):
        return None
    return owned_paths


@dataclass
class OwnedSibling:
    destination: Path
    kind: str
    token: str
    path: Path
    marker_path: Path
    _lease: _KernelFileLock
    _owned_paths: dict[str, dict[str, object]]

    def bind_path(
        self,
        label: str,
        path: Path,
        *,
        identity_source: Path | None = None,
    ) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]*", label) is None:
            raise ValueError(f"invalid owned path label: {label!r}")
        owned_paths = dict(self._owned_paths)
        owned_paths[label] = _owned_path_identity(
            identity_source or path,
            recorded_path=path,
        )
        # Keep the in-process identity even if persisting it fails, so the
        # process that performed the rename can still put the path back. A
        # subsequent process will fail closed unless the marker was durable.
        self._owned_paths = owned_paths
        self._lease.replace_content(
            _encode_marker(self.destination, self.kind, self.token, owned_paths)
        )

    def owns_path(self, label: str, path: Path) -> bool:
        expected = self._owned_paths.get(label)
        if expected is None:
            return False
        try:
            return expected == _owned_path_identity(path)
        except OSError:
            return False

    def close(self, *, remove_marker: bool) -> None:
        self._lease.close()
        if not remove_marker:
            return
        try:
            self.marker_path.unlink()
        except FileNotFoundError:
            pass

    def cleanup(self, remove_path: Callable[[Path], None]) -> None:
        try:
            remove_path(self.path)
        except BaseException:
            self.close(remove_marker=False)
            raise
        self.close(remove_marker=True)


def create_owned_sibling(destination: Path, kind: str) -> OwnedSibling:
    _validate_kind(kind)
    while True:
        token = uuid.uuid4().hex
        marker_path = _marker_path(destination, kind, token)
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

        lease = _KernelFileLock(marker_file)
        path = destination.with_name(f".{destination.name}.protocyte-{kind}-{token}")
        owned_paths: dict[str, dict[str, object]] = {}
        try:
            marker_file.write(_encode_marker(destination, kind, token, owned_paths))
            marker_file.flush()
            os.fsync(marker_file.fileno())
            lease.acquire(blocking=True)
            path.mkdir()
        except BaseException:
            lease.close()
            try:
                marker_path.unlink()
            except FileNotFoundError:
                pass
            raise
        return OwnedSibling(
            destination,
            kind,
            token,
            path,
            marker_path,
            lease,
            owned_paths,
        )


def _claim_dead_owner(
    destination: Path,
    kind: str,
    token: str,
) -> OwnedSibling | None:
    marker_path = _marker_path(destination, kind, token)
    try:
        marker_file = _open_state_file(marker_path, os.O_RDWR)
    except FileNotFoundError:
        return None
    lease = _KernelFileLock(marker_file)
    try:
        if not lease.acquire(blocking=False):
            lease.close()
            return None
        marker_file.seek(0)
        owned_paths = _read_owned_paths(marker_file.read(), destination, kind, token)
        if owned_paths is None:
            lease.close()
            return None
        path = destination.with_name(f".{destination.name}.protocyte-{kind}-{token}")
        return OwnedSibling(
            destination,
            kind,
            token,
            path,
            marker_path,
            lease,
            owned_paths,
        )
    except BaseException:
        lease.close()
        raise


def _owned_sibling_identity(
    destination: Path,
    path: Path,
    kinds: tuple[str, ...],
) -> tuple[str, str] | None:
    kind_pattern = "|".join(re.escape(kind) for kind in kinds)
    match = re.fullmatch(
        rf"\.{re.escape(destination.name)}\.protocyte-({kind_pattern})-([0-9a-f]{{32}})",
        path.name,
        flags=re.IGNORECASE if os.name == "nt" else 0,
    )
    if match is None:
        return None
    return match.group(1), match.group(2)


def recover_owned_siblings(
    destination: Path,
    kinds: tuple[str, ...],
    remove_path: Callable[[Path], None],
) -> None:
    for kind in kinds:
        _validate_kind(kind)

    observed_markers: set[Path] = set()
    for candidate in tuple(destination.parent.iterdir()):
        identity = _owned_sibling_identity(destination, candidate, kinds)
        if identity is None:
            continue
        kind, token = identity
        claimed = _claim_dead_owner(destination, kind, token)
        if claimed is None:
            continue
        observed_markers.add(claimed.marker_path)
        try:
            remove_path(candidate)
        except BaseException:
            claimed.close(remove_marker=False)
            raise
        claimed.close(remove_marker=True)

    key = _destination_key(destination)
    marker_pattern = re.compile(
        rf"{key}\.({'|'.join(re.escape(kind) for kind in kinds)})\.([0-9a-f]{{32}})\.owner"
    )
    for marker_path in tuple(_state_directory().iterdir()):
        if marker_path in observed_markers:
            continue
        match = marker_pattern.fullmatch(marker_path.name)
        if match is None:
            continue
        kind, token = match.groups()
        candidate = destination.with_name(
            f".{destination.name}.protocyte-{kind}-{token}"
        )
        if candidate.exists() or candidate.is_symlink():
            continue
        claimed = _claim_dead_owner(destination, kind, token)
        if claimed is None:
            continue
        claimed.close(remove_marker=True)


def claim_dead_owner_for_path(
    destination: Path,
    kinds: tuple[str, ...],
    label: str,
    owned_path: Path,
) -> OwnedSibling | None:
    match: OwnedSibling | None = None
    for candidate in tuple(destination.parent.iterdir()):
        identity = _owned_sibling_identity(destination, candidate, kinds)
        if identity is None:
            continue
        kind, token = identity
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
