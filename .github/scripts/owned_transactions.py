from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Iterator


_MARKER_SCHEMA = 1
_STATE_DIRECTORY_ENV = "PROTOCYTE_TRANSACTION_STATE_DIR"
_STATE_DIRECTORY_NAME = "protocyte-owned-transactions-v1"


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


def _state_directory() -> Path:
    configured = os.environ.get(_STATE_DIRECTORY_ENV)
    state = (
        Path(configured)
        if configured
        else Path(tempfile.gettempdir()) / _STATE_DIRECTORY_NAME
    )
    state.mkdir(parents=True, exist_ok=True)
    return state


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
    file = lock_path.open("a+b", buffering=0)
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


def _marker_payload(destination: Path, kind: str, token: str) -> dict[str, object]:
    return {
        "schema": _MARKER_SCHEMA,
        "destination": _normalized_destination(destination),
        "kind": kind,
        "token": token,
    }


def _marker_matches(
    content: bytes,
    destination: Path,
    kind: str,
    token: str,
) -> bool:
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return payload == _marker_payload(destination, kind, token)


@dataclass
class OwnedSibling:
    path: Path
    marker_path: Path
    _lease: _KernelFileLock

    def cleanup(self, remove_path: Callable[[Path], None]) -> None:
        try:
            remove_path(self.path)
        except BaseException:
            self._lease.close()
            raise
        self._lease.close()
        try:
            self.marker_path.unlink()
        except FileNotFoundError:
            pass


def create_owned_sibling(destination: Path, kind: str) -> OwnedSibling:
    _validate_kind(kind)
    while True:
        token = uuid.uuid4().hex
        marker_path = _marker_path(destination, kind, token)
        try:
            marker_file = marker_path.open("x+b", buffering=0)
        except FileExistsError:
            continue

        lease = _KernelFileLock(marker_file)
        path = destination.with_name(f".{destination.name}.protocyte-{kind}-{token}")
        try:
            marker_file.write(
                json.dumps(
                    _marker_payload(destination, kind, token),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
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
        return OwnedSibling(path, marker_path, lease)


def _claim_dead_owner(
    destination: Path,
    kind: str,
    token: str,
) -> tuple[_KernelFileLock, Path] | None:
    marker_path = _marker_path(destination, kind, token)
    try:
        marker_file = marker_path.open("r+b", buffering=0)
    except FileNotFoundError:
        return None
    lease = _KernelFileLock(marker_file)
    try:
        if not lease.acquire(blocking=False):
            lease.close()
            return None
        marker_file.seek(0)
        if not _marker_matches(marker_file.read(), destination, kind, token):
            lease.close()
            return None
        return lease, marker_path
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
        lease, marker_path = claimed
        observed_markers.add(marker_path)
        try:
            remove_path(candidate)
        except BaseException:
            lease.close()
            raise
        lease.close()
        try:
            marker_path.unlink()
        except FileNotFoundError:
            pass

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
        lease, claimed_marker = claimed
        lease.close()
        try:
            claimed_marker.unlink()
        except FileNotFoundError:
            pass
