"""Durable ownership and publication coordinator for Protocyte outputs.

CMake deliberately delegates mutable output state to this process.  Each
physical output root has one immutable claim, one committed snapshot, and at
most one write-ahead transaction.  Transactions carry durable replacement
payloads, so recovery always rolls forward and never has to infer intent from
partially published outputs.

The persistence order is part of the protocol: directory topology and the
initial snapshot precede claim visibility; transaction topology and payloads
precede pending intent; published outputs and their ancestor topology precede
the new snapshot; and reset persists output absence before removing the claim.
Every topology operation is idempotently synchronized so a retry after a crash
also completes a parent fsync that the interrupted invocation may have missed.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, NoReturn, Sequence


PROTOCOL_VERSION = 1
PLAN_HEADER = "protocyte-output-plan-v1"
GENERATED_SUFFIXES = (".protocyte.cpp", ".protocyte.hpp", "/runtime.hpp")


class CoordinatorError(RuntimeError):
    """A fail-closed coordinator error suitable for a CMake diagnostic."""


def _fail(message: str) -> NoReturn:
    raise CoordinatorError(message)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _is_link(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        return bool(is_junction and is_junction())
    except OSError:
        return True


def _require_absolute(path: Path, description: str) -> Path:
    text = os.fspath(path)
    if not path.is_absolute() or any(
        character in text for character in ("\x00", "\r", "\n")
    ):
        _fail(
            f"{description} must be an absolute path without control characters: {path}"
        )
    return Path(os.path.normpath(text))


def _existing_chain(path: Path) -> list[Path]:
    current = path
    missing: list[Path] = []
    while not os.path.lexists(current):
        parent = current.parent
        if parent == current:
            _fail(f"could not find an existing ancestor for {path}")
        missing.append(current)
        current = parent
    chain: list[Path] = []
    cursor = current
    while True:
        chain.append(cursor)
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent
    chain.reverse()
    return chain


def project_path(path: Path, *, leaf_may_be_file: bool = False) -> Path:
    """Resolve existing components and append a normalized missing suffix.

    Every existing component must be an ordinary directory, except for an
    explicitly permitted regular-file leaf.  Links and junctions are rejected
    instead of followed.
    """

    path = _require_absolute(path, "filesystem path")
    existing = path
    suffix: list[str] = []
    while not os.path.lexists(existing):
        if existing.parent == existing:
            _fail(f"could not project filesystem path: {path}")
        suffix.append(existing.name)
        existing = existing.parent
    for component in _existing_chain(existing):
        if _is_link(component):
            _fail(f"filesystem path contains a symbolic link or junction: {path}")
    try:
        mode = existing.stat().st_mode
    except OSError as error:
        _fail(f"could not inspect filesystem path {existing}: {error}")
    if not stat.S_ISDIR(mode) and not (
        leaf_may_be_file and existing == path and stat.S_ISREG(mode)
    ):
        _fail(f"filesystem path has a non-directory ancestor: {existing}")
    try:
        projected = existing.resolve(strict=True)
    except OSError as error:
        _fail(f"could not resolve filesystem path {existing}: {error}")
    for name in reversed(suffix):
        if name in ("", ".", ".."):
            _fail(f"filesystem path contains an unsafe component: {path}")
        projected /= name
    return Path(os.path.normpath(projected))


def canonical_build_root(path: Path) -> Path:
    """Resolve a valid CMake build directory to its stable physical path."""

    path = _require_absolute(path, "CMake build root")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        _fail(f"could not resolve CMake build root {path}: {error}")
    if not resolved.is_dir():
        _fail(f"CMake build root is not a directory: {path}")
    return project_path(resolved)


def _portable_identity(path: Path, *, leaf_may_be_file: bool = False) -> str:
    projected = project_path(path, leaf_may_be_file=leaf_may_be_file)
    return os.fspath(projected).replace("\\", "/").casefold()


def _path_key(path: Path) -> str:
    return hashlib.sha256(_portable_identity(path).encode("utf-8")).hexdigest()


def _contains(parent: Path, child: Path) -> bool:
    parent_identity = _portable_identity(parent).rstrip("/")
    child_identity = _portable_identity(child, leaf_may_be_file=True).rstrip("/")
    return child_identity == parent_identity or child_identity.startswith(
        parent_identity + "/"
    )


def _validate_relative_path(value: str) -> str:
    if "\\" in value:
        value = value.replace("\\", "/")
    relative = PurePosixPath(value)
    if (
        not value
        or relative.is_absolute()
        or any(part in ("", ".", "..") for part in relative.parts)
        or relative.parts[0].casefold() == ".protocyte"
        or not value.casefold().endswith(GENERATED_SUFFIXES)
    ):
        _fail(f"output plan contains an unsafe generated path: {value!r}")
    return relative.as_posix()


def _output_path(root: Path, relative: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    projected_root = project_path(root)
    projected_candidate = project_path(candidate, leaf_may_be_file=True)
    if (
        not _contains(projected_root, projected_candidate)
        or projected_candidate == projected_root
    ):
        _fail(f"generated output escapes its claimed root: {relative}")
    return candidate


def _atomic_write(path: Path, content: bytes) -> None:
    _durable_mkdir(path.parent)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        from ctypes import wintypes

        absolute = os.path.abspath(path)
        if absolute.startswith("\\\\"):
            extended = "\\\\?\\UNC\\" + absolute[2:]
        else:
            extended = "\\\\?\\" + absolute
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            extended,
            0x80000000 | 0x40000000,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not kernel32.FlushFileBuffers(handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(handle)
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _durable_mkdir(path: Path, *, anchor: Path | None = None) -> None:
    """Create a directory chain and persist every entry below its anchor."""

    path = _require_absolute(path, "directory path")
    expected = project_path(path)
    if anchor is None:
        anchor = path.parent
        while not os.path.lexists(anchor):
            if anchor.parent == anchor:
                _fail(f"could not find an existing parent for directory: {path}")
            anchor = anchor.parent
    anchor = project_path(_require_absolute(anchor, "directory anchor"))
    try:
        relative = path.relative_to(anchor)
    except ValueError:
        _fail(f"directory path is outside its durability anchor: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if project_path(path) != expected:
        _fail(f"directory changed while it was being created: {path}")
    parent = anchor
    for part in relative.parts:
        directory = parent / part
        if project_path(directory) != directory:
            _fail(f"directory changed before its parent was synchronized: {directory}")
        _sync_directory(parent)
        parent = directory


def _sync_absence(path: Path) -> None:
    """Persist that a path is absent, including after a pre-fsync crash retry."""

    existing = path.parent
    while not os.path.lexists(existing):
        if existing.parent == existing:
            _fail(f"could not find an existing ancestor for absent path: {path}")
        existing = existing.parent
    existing = project_path(existing)
    _sync_directory(existing)


def _durable_rmtree(path: Path) -> None:
    """Remove a directory tree and persist removal of its root entry."""

    if not os.path.lexists(path):
        _sync_absence(path)
        return
    expected = project_path(_require_absolute(path, "directory tree"))
    if expected != path:
        _fail(f"directory tree changed before removal: {path}")
    parent = path.parent
    shutil.rmtree(path)
    if project_path(parent) != parent:
        _fail(f"directory tree parent changed during removal: {parent}")
    _sync_directory(parent)


def _walk_tree(root: Path) -> list[Path]:
    """Enumerate a tree without suppressing any directory-read failure."""

    paths: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            with os.scandir(directory) as stream:
                entries = sorted(stream, key=lambda entry: entry.name)
        except OSError as error:
            _fail(f"could not enumerate directory {directory}: {error}")
        for entry in entries:
            path = directory / entry.name
            paths.append(path)
            if _is_link(path):
                continue
            try:
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError as error:
                _fail(f"could not inspect directory entry {path}: {error}")
            if is_directory:
                visit(path)

    visit(root)
    return paths


def _load_json(path: Path, description: str) -> dict[str, Any]:
    expected = project_path(path, leaf_may_be_file=True)
    if expected != path or _is_link(path):
        _fail(f"{description} path is unsafe or was replaced: {path}")
    try:
        content = path.read_bytes()
        value = json.loads(content)
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"could not read {description} {path}: {error}")
    if not isinstance(value, dict) or _canonical_json(value) != content:
        _fail(f"{description} is malformed or not canonically encoded: {path}")
    return value


class FileLock:
    """One-byte advisory lock compatible with ordinary OS file locks."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._stream: Any = None
        self._overlapped: Any = None

    def __enter__(self) -> FileLock:
        expected_path = project_path(self.path, leaf_may_be_file=True)
        expected_parent = expected_path.parent
        _durable_mkdir(expected_parent)
        observed_parent = project_path(expected_parent)
        if observed_parent != expected_parent:
            _fail(f"lock directory changed while it was being prepared: {self.path}")
        observed_path = project_path(expected_path, leaf_may_be_file=True)
        if observed_path != expected_path or _is_link(expected_path):
            _fail(f"lock path is unsafe or was replaced: {self.path}")
        self.path = expected_path
        self._stream = self.path.open("a+b")
        if os.name == "nt":
            self._lock_windows()
        else:
            import fcntl

            fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX)
        return self

    def _lock_windows(self) -> None:
        import msvcrt

        class Overlapped(ctypes.Structure):
            _fields_ = [
                ("Internal", ctypes.c_void_p),
                ("InternalHigh", ctypes.c_void_p),
                ("Offset", ctypes.c_uint32),
                ("OffsetHigh", ctypes.c_uint32),
                ("hEvent", ctypes.c_void_p),
            ]

        self._overlapped = Overlapped()
        handle = msvcrt.get_osfhandle(self._stream.fileno())
        lock_file_ex = ctypes.windll.kernel32.LockFileEx
        lock_file_ex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(Overlapped),
        ]
        if not lock_file_ex(
            handle, 0x00000002, 0, 1, 0, ctypes.byref(self._overlapped)
        ):
            raise ctypes.WinError()

    def __exit__(self, *_: object) -> None:
        if self._stream is None:
            return
        if os.name == "nt":
            import msvcrt

            handle = msvcrt.get_osfhandle(self._stream.fileno())
            unlock_file_ex = ctypes.windll.kernel32.UnlockFileEx
            unlock_file_ex(
                handle,
                0,
                1,
                0,
                ctypes.byref(self._overlapped),
            )
        else:
            import fcntl

            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        self._stream.close()
        self._stream = None


@dataclass(frozen=True)
class PlanOutput:
    target: str
    relative: str


@dataclass(frozen=True)
class PlanTarget:
    identity: str
    staging: Path


@dataclass(frozen=True)
class Plan:
    root: Path
    build_root: Path
    build_id: str
    targets: tuple[PlanTarget, ...]
    outputs: tuple[PlanOutput, ...]

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "build_id": self.build_id,
            "build_root": os.fspath(self.build_root),
            "outputs": [
                {"path": output.relative, "target": output.target}
                for output in self.outputs
            ],
            "root": os.fspath(self.root),
            "targets": [
                {"id": target.identity, "staging": os.fspath(target.staging)}
                for target in self.targets
            ],
            "version": PROTOCOL_VERSION,
        }

    @property
    def digest(self) -> str:
        return _sha256_bytes(_canonical_json(self.payload))

    @classmethod
    def read(cls, path: Path) -> Plan:
        try:
            lines = path.read_text(encoding="ascii").splitlines()
        except (OSError, UnicodeError) as error:
            _fail(f"could not read output plan {path}: {error}")
        if not lines or lines[0] != PLAN_HEADER:
            _fail(f"output plan has an unsupported header: {path}")
        scalar: dict[str, str] = {}
        targets: list[PlanTarget] = []
        outputs: list[PlanOutput] = []
        for line in lines[1:]:
            key, separator, value = line.partition("=")
            if not separator:
                _fail(f"output plan contains a malformed line: {path}")
            if key == "target":
                identity, target_separator, encoded_staging = value.partition("|")
                if not target_separator or not _is_sha256(identity):
                    _fail(f"output plan contains invalid target metadata: {path}")
                targets.append(
                    PlanTarget(
                        identity,
                        _validate_staging_path(
                            root=None,
                            identity=identity,
                            path=Path(_decode_hex(encoded_staging)),
                        ),
                    )
                )
            elif key == "output":
                target, output_separator, encoded_relative = value.partition("|")
                if not output_separator or not _is_sha256(target):
                    _fail(f"output plan contains an invalid target identity: {path}")
                outputs.append(
                    PlanOutput(
                        target, _validate_relative_path(_decode_hex(encoded_relative))
                    )
                )
            elif key in scalar:
                _fail(f"output plan repeats {key!r}: {path}")
            else:
                scalar[key] = value
        if set(scalar) != {"root-hex", "build-root-hex"}:
            _fail(f"output plan is missing required identity fields: {path}")
        root = project_path(Path(_decode_hex(scalar["root-hex"])))
        build_root = project_path(Path(_decode_hex(scalar["build-root-hex"])))
        build_id = _path_key(build_root)
        validated_targets = tuple(
            PlanTarget(
                target.identity,
                _validate_staging_path(root, target.identity, target.staging),
            )
            for target in targets
        )
        _validate_plan_targets(validated_targets, outputs, path)
        unique: dict[str, PlanOutput] = {}
        portable: dict[str, PlanOutput] = {}
        for output in outputs:
            if output.relative in unique:
                _fail(f"output plan repeats generated path: {output.relative}")
            portable_key = output.relative.casefold()
            if portable_key in portable:
                _fail(
                    "output plan contains portable-equivalent generated paths: "
                    f"{portable[portable_key].relative!r} and {output.relative!r}"
                )
            unique[output.relative] = output
            portable[portable_key] = output
        ordered = tuple(
            sorted(outputs, key=lambda output: (output.relative, output.target))
        )
        return cls(
            root,
            build_root,
            build_id,
            tuple(sorted(validated_targets, key=lambda target: target.identity)),
            ordered,
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], source: Path) -> Plan:
        if (
            set(payload)
            != {
                "build_id",
                "build_root",
                "outputs",
                "root",
                "sha256",
                "targets",
                "version",
            }
            or payload["version"] != PROTOCOL_VERSION
            or not isinstance(payload["outputs"], list)
            or not isinstance(payload["targets"], list)
        ):
            _fail(f"configured output plan is malformed: {source}")
        root = project_path(Path(str(payload["root"])))
        build_root = project_path(Path(str(payload["build_root"])))
        outputs: list[PlanOutput] = []
        for value in payload["outputs"]:
            if (
                not isinstance(value, dict)
                or set(value) != {"path", "target"}
                or not _is_sha256(str(value["target"]))
            ):
                _fail(f"configured output plan contains a malformed output: {source}")
            outputs.append(
                PlanOutput(
                    str(value["target"]), _validate_relative_path(str(value["path"]))
                )
            )
        targets: list[PlanTarget] = []
        for value in payload["targets"]:
            if (
                not isinstance(value, dict)
                or set(value) != {"id", "staging"}
                or not _is_sha256(str(value["id"]))
            ):
                _fail(f"configured output plan contains malformed target metadata: {source}")
            identity = str(value["id"])
            targets.append(
                PlanTarget(
                    identity,
                    _validate_staging_path(
                        root, identity, Path(str(value["staging"]))
                    ),
                )
            )
        _validate_plan_targets(targets, outputs, source)
        plan = cls(
            root,
            build_root,
            _path_key(build_root),
            tuple(sorted(targets, key=lambda target: target.identity)),
            tuple(sorted(outputs, key=lambda output: (output.relative, output.target))),
        )
        if payload["build_id"] != plan.build_id or payload["sha256"] != plan.digest:
            _fail(f"configured output plan identity is malformed: {source}")
        return plan

    def staging_for_target(self, identity: str) -> Path:
        for target in self.targets:
            if target.identity == identity:
                return target.staging
        _fail(f"output plan contains no metadata for target {identity}")


def _validate_staging_path(
    root: Path | None, identity: str, path: Path
) -> Path:
    path = project_path(_require_absolute(path, "generation staging directory"))
    if root is not None:
        expected = project_path(
            root.parent / f".protocyte-generation-staging-{identity}"
        )
        if path != expected:
            _fail(
                "output plan target metadata contains an unexpected staging directory: "
                f"{path}"
            )
    return path


def _validate_plan_targets(
    targets: Sequence[PlanTarget], outputs: Sequence[PlanOutput], source: Path
) -> None:
    identities = [target.identity for target in targets]
    staging_paths = [os.fspath(target.staging).casefold() for target in targets]
    if len(set(identities)) != len(identities) or len(set(staging_paths)) != len(
        staging_paths
    ):
        _fail(f"output plan repeats target metadata: {source}")
    if set(identities) != {output.target for output in outputs}:
        _fail(f"output plan target metadata does not match its outputs: {source}")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _decode_hex(value: str) -> str:
    try:
        decoded = bytes.fromhex(value).decode("utf-8")
    except (ValueError, UnicodeError) as error:
        _fail(f"output plan contains invalid UTF-8 hex data: {error}")
    if any(character in decoded for character in ("\x00", "\r", "\n")):
        _fail("output plan contains a path with forbidden control characters")
    return decoded


class OutputCoordinator:
    def __init__(self, lock_root: Path) -> None:
        self.lock_root = project_path(_require_absolute(lock_root, "output lock root"))

    def reconcile(self, plan: Plan) -> str:
        state = self._claim(plan)
        with FileLock(self._publication_lock(plan.root)):
            claim = self._load_claim(state, plan)
            self._recover(state, plan, claim)
            previous_plan = self._load_recorded_plan(state)
            snapshot = self._load_snapshot(state, claim)
            snapshot = self._retire_unplanned(state, plan, claim, snapshot)
            self._retire_staging(previous_plan, plan)
            _atomic_write(
                state / "plan.json",
                _canonical_json({**plan.payload, "sha256": plan.digest}),
            )
            return str(claim["token"])

    def validate(self, plan: Plan) -> None:
        state = self._state_directory(plan.root)
        with FileLock(self._publication_lock(plan.root)):
            claim = self._load_claim(state, plan)
            self._recover(state, plan, claim)
            self._require_current_plan(state, plan)

    def publish(self, plan: Plan, target: str, staging_root: Path) -> None:
        if not _is_sha256(target):
            _fail("publish target identity is invalid")
        state = self._state_directory(plan.root)
        with FileLock(self._publication_lock(plan.root)):
            claim = self._load_claim(state, plan)
            self._recover(state, plan, claim)
            self._require_current_plan(state, plan)
            expected_staging_root = plan.staging_for_target(target) / "generated"
            if project_path(staging_root) != project_path(expected_staging_root):
                _fail(
                    "publish staging root does not match the configured target metadata"
                )
            snapshot = self._load_snapshot(state, claim)
            target_outputs = [
                output for output in plan.outputs if output.target == target
            ]
            if not target_outputs:
                _fail(f"output plan contains no outputs for target {target}")
            transaction_entries: list[dict[str, Any]] = []
            new_entries = dict(snapshot["entries"])
            transaction_id = secrets.token_hex(32)
            transaction_directory = state / "transactions" / transaction_id
            payload_directory = transaction_directory / "payloads"
            _durable_mkdir(payload_directory, anchor=state)
            try:
                for index, output in enumerate(target_outputs):
                    destination = _output_path(plan.root, output.relative)
                    source = _output_path(staging_root, output.relative)
                    if not source.is_file() or _is_link(source):
                        _fail(
                            f"staged generation output is missing or unsafe: {source}"
                        )
                    after_hash = _sha256_file(source)
                    previous_path, previous = self._snapshot_entry_for_path(
                        plan.root, snapshot["entries"], output.relative
                    )
                    before_hash = previous.get("sha256") if previous else None
                    self._require_observed_state(
                        destination, before_hash, allow_absent=True
                    )
                    payload = payload_directory / f"{index:08d}.payload"
                    with (
                        source.open("rb") as source_stream,
                        payload.open("xb") as payload_stream,
                    ):
                        shutil.copyfileobj(source_stream, payload_stream)
                        payload_stream.flush()
                        os.fsync(payload_stream.fileno())
                    if _sha256_file(payload) != after_hash:
                        _fail(
                            f"durable transaction payload changed while copying: {source}"
                        )
                    if previous_path is not None and previous_path != output.relative:
                        new_entries.pop(previous_path, None)
                    new_entries[output.relative] = {
                        "sha256": after_hash,
                        "target": target,
                    }
                    transaction_entries.append(
                        {
                            "after": after_hash,
                            "before": before_hash,
                            "path": output.relative,
                            "payload": payload.name,
                            "target": target,
                            "transfer": None,
                        }
                    )
                _sync_directory(payload_directory)
                new_snapshot = {
                    "claim_token": claim["token"],
                    "entries": dict(sorted(new_entries.items())),
                    "generation": int(snapshot["generation"]) + 1,
                    "version": PROTOCOL_VERSION,
                }
                pending = {
                    "base_generation": snapshot["generation"],
                    "entries": transaction_entries,
                    "id": transaction_id,
                    "new_snapshot": new_snapshot,
                    "version": PROTOCOL_VERSION,
                }
                _atomic_write(
                    transaction_directory / "pending.json", _canonical_json(pending)
                )
                self._inject("after-pending")
                self._apply_pending(state, plan, claim, pending, transaction_directory)
            except BaseException:
                if not (transaction_directory / "pending.json").exists():
                    with contextlib.suppress(OSError):
                        _durable_rmtree(transaction_directory)
                raise
            for output in target_outputs:
                expected = new_entries[output.relative]["sha256"]
                destination = _output_path(plan.root, output.relative)
                self._require_observed_state(destination, expected, allow_absent=False)

    def reset(self, plan: Plan, expected_token: str) -> None:
        state = self._state_directory(plan.root)
        with FileLock(self.lock_root / "registry.lock"):
            with FileLock(self._publication_lock(plan.root)):
                claim = self._load_claim(state, plan)
                if claim["token"] != expected_token:
                    _fail("reset claim token does not match the live immutable claim")
                reset_path = state / "reset.json"
                if reset_path.exists():
                    intent = self._load_reset_intent(reset_path, plan.root, claim)
                else:
                    self._recover(state, plan, claim)
                    snapshot = self._load_snapshot(state, claim)
                    self._validate_reset_inventory(plan.root, snapshot["entries"])
                    recorded_plan = self._load_recorded_plan(state)
                    staging = [
                        {"id": target.identity, "path": os.fspath(target.staging)}
                        for target in (recorded_plan.targets if recorded_plan else ())
                    ]
                    intent = {
                        "claim_token": claim["token"],
                        "entries": snapshot["entries"],
                        "staging": staging,
                        "version": PROTOCOL_VERSION,
                    }
                    _atomic_write(reset_path, _canonical_json(intent))
                    self._inject("after-reset-intent")
                for index, (relative, entry) in enumerate(intent["entries"].items()):
                    output = _output_path(plan.root, relative)
                    self._delete_if_state(output, entry["sha256"])
                    self._inject(f"after-reset-output-{index + 1}")
                for target in intent["staging"]:
                    _durable_rmtree(Path(target["path"]))
                self._release_claim(state)

    def _validate_reset_inventory(
        self, root: Path, entries: Mapping[str, Any]
    ) -> None:
        for relative, entry in entries.items():
            self._require_observed_state(
                _output_path(root, relative), entry["sha256"], allow_absent=True
            )
        if not root.exists():
            return
        for candidate in _walk_tree(root):
            relative = candidate.relative_to(root).as_posix()
            if not relative.casefold().endswith(GENERATED_SUFFIXES):
                continue
            if _is_link(candidate):
                _fail(f"reset found an unowned generated-looking output: {candidate}")
            if not candidate.is_file():
                if candidate.is_dir() and self._is_snapshot_ancestor(
                    root, entries, relative
                ):
                    continue
                _fail(f"reset found an unowned generated-looking output: {candidate}")
            known_relative, _ = self._snapshot_entry_for_path(root, entries, relative)
            if known_relative is None:
                _fail(f"reset found an unowned generated-looking output: {candidate}")

    @staticmethod
    def _load_reset_intent(
        path: Path, root: Path, claim: Mapping[str, Any]
    ) -> dict[str, Any]:
        intent = _load_json(path, "pending output reset")
        if (
            set(intent) != {"claim_token", "entries", "staging", "version"}
            or intent["version"] != PROTOCOL_VERSION
            or intent["claim_token"] != claim["token"]
            or not isinstance(intent["entries"], dict)
            or not isinstance(intent["staging"], list)
        ):
            _fail(f"pending output reset is malformed: {path}")
        for relative, entry in intent["entries"].items():
            _validate_relative_path(relative)
            if (
                not isinstance(entry, dict)
                or set(entry) != {"sha256", "target"}
                or not _is_sha256(str(entry["sha256"]))
                or not _is_sha256(str(entry["target"]))
            ):
                _fail(f"pending output reset contains a malformed entry: {path}")
        seen: set[str] = set()
        for target in intent["staging"]:
            if (
                not isinstance(target, dict)
                or set(target) != {"id", "path"}
                or not _is_sha256(str(target["id"]))
                or str(target["id"]) in seen
            ):
                _fail(f"pending output reset contains malformed staging: {path}")
            seen.add(str(target["id"]))
            target["path"] = os.fspath(
                _validate_staging_path(root, str(target["id"]), Path(str(target["path"])))
            )
        return intent

    @staticmethod
    def _release_claim(state: Path) -> None:
        preserved = {"claim.json", "reset.json"}
        for entry in _walk_tree(state):
            if entry.parent != state or entry.name in preserved:
                continue
            if _is_link(entry):
                _fail(f"claim state contains an unsafe entry during reset: {entry}")
            if entry.is_dir():
                _durable_rmtree(entry)
            else:
                entry.unlink()
                _sync_directory(state)
        OutputCoordinator._inject("after-reset-disposable")
        claim_path = state / "claim.json"
        claim_path.unlink()
        _sync_directory(state)
        OutputCoordinator._inject("after-reset-claim")
        reset_path = state / "reset.json"
        reset_path.unlink()
        _sync_directory(state)
        state.rmdir()
        _sync_directory(state.parent)

    def plan_for_root(self, root: Path) -> Plan:
        root = project_path(_require_absolute(root, "output root"))
        state = self._state_directory(root)
        plan_path = state / "plan.json"
        if plan_path.exists():
            plan = Plan.from_payload(
                _load_json(plan_path, "configured output plan"), plan_path
            )
            self._require_requested_root(root, plan.root)
            return plan
        claim_path = state / "claim.json"
        claim = _load_json(claim_path, "output claim")
        self._validate_claim_shape(claim, claim_path)
        claim_root = project_path(Path(claim["root"]))
        self._require_requested_root(root, claim_root)
        build_root = project_path(Path(claim["build_root"]))
        return Plan(claim_root, build_root, str(claim["build_id"]), (), ())

    def _claim(self, plan: Plan) -> Path:
        _durable_mkdir(self.lock_root)
        state = self._state_directory(plan.root)
        with FileLock(self.lock_root / "registry.lock"):
            self._validate_registry(plan)
            _durable_mkdir(state, anchor=self.lock_root)
            claim_path = state / "claim.json"
            if claim_path.exists():
                self._load_claim(state, plan)
                _sync_directory(state)
                return state
            token = secrets.token_hex(32)
            claim = {
                "build_id": plan.build_id,
                "build_root": os.fspath(plan.build_root),
                "root": os.fspath(plan.root),
                "root_key": _path_key(plan.root),
                "token": token,
                "version": PROTOCOL_VERSION,
            }
            snapshot = {
                "claim_token": token,
                "entries": {},
                "generation": 0,
                "version": PROTOCOL_VERSION,
            }
            _atomic_write(state / "snapshot.json", _canonical_json(snapshot))
            self._inject("after-initial-snapshot")
            # Publish the immutable claim last.  A crash before this rename
            # leaves only unclaimed initialization data, which a retry may
            # safely replace.  Once the claim is visible, its initial snapshot
            # is already durable.
            _atomic_write(claim_path, _canonical_json(claim))
            self._inject("after-claim")
        return state

    def _validate_registry(self, plan: Plan) -> None:
        roots = self.lock_root / "roots"
        if not os.path.lexists(roots):
            return
        if project_path(roots) != roots:
            _fail(f"output registry is unsafe or was replaced: {roots}")
        try:
            with os.scandir(roots) as stream:
                states = sorted(stream, key=lambda entry: entry.name)
        except OSError as error:
            _fail(f"could not enumerate output registry {roots}: {error}")
        for entry in states:
            state = roots / entry.name
            try:
                is_directory = entry.is_dir(follow_symlinks=False)
            except OSError as error:
                _fail(f"could not inspect output registry entry {state}: {error}")
            if _is_link(state) or not is_directory or not _is_sha256(entry.name):
                _fail(f"output registry contains an unsafe entry: {state}")
            try:
                with os.scandir(state) as stream:
                    names = {child.name for child in stream}
            except OSError as error:
                _fail(f"could not enumerate output claim state {state}: {error}")
            claim_path = state / "claim.json"
            if "claim.json" not in names:
                _durable_rmtree(state)
                continue
            claim = _load_json(claim_path, "output claim")
            self._validate_claim_shape(claim, claim_path)
            claimed_root = project_path(Path(claim["root"]))
            if _contains(claimed_root, plan.root) or _contains(plan.root, claimed_root):
                if _path_key(claimed_root) != _path_key(plan.root):
                    _fail(
                        "output root overlaps a root claimed by another build: "
                        f"{plan.root} and {claimed_root}"
                    )

    def _state_directory(self, root: Path) -> Path:
        return self.lock_root / "roots" / _path_key(root)

    def _publication_lock(self, root: Path) -> Path:
        return self.lock_root / "publication" / f"{_path_key(root)}.lock"

    def _load_claim(self, state: Path, plan: Plan) -> dict[str, Any]:
        claim_path = state / "claim.json"
        claim = _load_json(claim_path, "output claim")
        self._validate_claim_shape(claim, claim_path)
        if claim["root_key"] != _path_key(plan.root) or project_path(
            Path(claim["root"])
        ) != project_path(plan.root):
            _fail(
                f"output claim does not identify the requested physical root: {claim_path}"
            )
        recorded_build = Path(claim["build_root"])
        same_build = recorded_build == plan.build_root
        if not same_build:
            try:
                same_build = os.path.samefile(recorded_build, plan.build_root)
            except OSError:
                same_build = False
        if claim["build_id"] != plan.build_id or not same_build:
            _fail(
                "output root is claimed by a different CMake build tree; use the owning build or reset "
                f"the claim explicitly: {plan.root}"
            )
        return claim

    @staticmethod
    def _validate_claim_shape(claim: Mapping[str, Any], path: Path) -> None:
        if (
            set(claim)
            != {
                "build_id",
                "build_root",
                "root",
                "root_key",
                "token",
                "version",
            }
            or claim["version"] != PROTOCOL_VERSION
            or not _is_sha256(str(claim["build_id"]))
            or not _is_sha256(str(claim["root_key"]))
            or not _is_sha256(str(claim["token"]))
        ):
            _fail(f"output claim is malformed: {path}")

    def _load_snapshot(self, state: Path, claim: Mapping[str, Any]) -> dict[str, Any]:
        path = state / "snapshot.json"
        snapshot = _load_json(path, "committed output snapshot")
        self._validate_snapshot(snapshot, claim, path)
        return snapshot

    @staticmethod
    def _validate_snapshot(
        snapshot: Mapping[str, Any], claim: Mapping[str, Any], path: Path
    ) -> None:
        if (
            set(snapshot) != {"claim_token", "entries", "generation", "version"}
            or snapshot["version"] != PROTOCOL_VERSION
            or snapshot["claim_token"] != claim["token"]
            or not isinstance(snapshot["generation"], int)
            or snapshot["generation"] < 0
            or not isinstance(snapshot["entries"], dict)
        ):
            _fail(f"committed output snapshot is malformed: {path}")
        for relative, entry in snapshot["entries"].items():
            _validate_relative_path(relative)
            if (
                not isinstance(entry, dict)
                or set(entry) != {"sha256", "target"}
                or not _is_sha256(str(entry["sha256"]))
                or not _is_sha256(str(entry["target"]))
            ):
                _fail(f"committed output snapshot contains a malformed entry: {path}")

    def _require_current_plan(self, state: Path, plan: Plan) -> None:
        current = _load_json(state / "plan.json", "configured output plan")
        if (
            current.get("sha256") != plan.digest
            or current.get("build_id") != plan.build_id
        ):
            _fail(
                "build-time output plan does not match the plan committed during configuration"
            )

    @staticmethod
    def _load_recorded_plan(state: Path) -> Plan | None:
        path = state / "plan.json"
        if not path.exists():
            return None
        return Plan.from_payload(_load_json(path, "configured output plan"), path)

    @staticmethod
    def _retire_staging(previous: Plan | None, current: Plan) -> None:
        if previous is None:
            return
        current_targets = {target.identity for target in current.targets}
        for target in previous.targets:
            if target.identity not in current_targets:
                _durable_rmtree(target.staging)

    def _retire_unplanned(
        self,
        state: Path,
        plan: Plan,
        claim: Mapping[str, Any],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        desired = {output.relative for output in plan.outputs}
        removals: list[str] = []
        hard_link_moves: dict[str, str] = {}
        for relative in snapshot["entries"]:
            if relative in desired:
                continue
            aliased = any(
                self._case_spelling_alias(plan.root, relative, item) for item in desired
            )
            if not aliased:
                removals.append(relative)
                linked_desired = [
                    item
                    for item in desired
                    if self._same_existing_file(
                        _output_path(plan.root, relative),
                        _output_path(plan.root, item),
                    )
                ]
                if len(linked_desired) > 1:
                    _fail(
                        "retired generated output has multiple desired hard-link destinations: "
                        f"{relative}"
                    )
                if linked_desired:
                    hard_link_moves[relative] = linked_desired[0]
        if not removals:
            return snapshot
        new_entries = dict(snapshot["entries"])
        pending_entries: list[dict[str, Any]] = []
        for relative in removals:
            before = snapshot["entries"][relative]["sha256"]
            output = _output_path(plan.root, relative)
            if os.path.lexists(output):
                if (
                    _is_link(output)
                    or not output.is_file()
                    or _sha256_file(output) != before
                ):
                    # Modified or structurally unsafe retired outputs remain
                    # in the authoritative snapshot.  This preserves user
                    # bytes and keeps reset fail-closed without preventing an
                    # otherwise valid reconfiguration.
                    continue
            pending_entries.append(
                {
                    "after": None,
                    "before": before,
                    "path": relative,
                    "payload": None,
                    "target": snapshot["entries"][relative]["target"],
                    "transfer": hard_link_moves.get(relative),
                }
            )
            new_entries.pop(relative)
            if relative in hard_link_moves:
                new_entries[hard_link_moves[relative]] = snapshot["entries"][relative]
        if not pending_entries:
            return snapshot
        transaction_id = secrets.token_hex(32)
        transaction_directory = state / "transactions" / transaction_id
        _durable_mkdir(transaction_directory, anchor=state)
        new_snapshot = {
            "claim_token": claim["token"],
            "entries": dict(sorted(new_entries.items())),
            "generation": int(snapshot["generation"]) + 1,
            "version": PROTOCOL_VERSION,
        }
        pending = {
            "base_generation": snapshot["generation"],
            "entries": pending_entries,
            "id": transaction_id,
            "new_snapshot": new_snapshot,
            "version": PROTOCOL_VERSION,
        }
        _atomic_write(transaction_directory / "pending.json", _canonical_json(pending))
        self._apply_pending(state, plan, claim, pending, transaction_directory)
        return new_snapshot

    def _recover(self, state: Path, plan: Plan, claim: Mapping[str, Any]) -> None:
        transaction_root = state / "transactions"
        if not os.path.lexists(transaction_root):
            return
        if project_path(transaction_root) != transaction_root:
            _fail(f"transaction directory is unsafe or was replaced: {transaction_root}")
        transaction_directories: list[Path] = []
        for directory in transaction_root.iterdir():
            if not directory.is_dir():
                continue
            if _is_link(directory) or not _is_sha256(directory.name):
                _fail(f"transaction directory contains an unsafe entry: {directory}")
            transaction_directories.append(directory)
        pending_directories = [
            directory
            for directory in transaction_directories
            if (directory / "pending.json").exists()
        ]
        if len(pending_directories) > 1:
            _fail(f"output root contains multiple pending transactions: {plan.root}")
        if pending_directories:
            directory = pending_directories[0]
            _durable_mkdir(directory, anchor=state)
            _sync_directory(directory)
            pending = _load_json(
                directory / "pending.json", "pending output transaction"
            )
            self._apply_pending(state, plan, claim, pending, directory)
        for directory in transaction_directories:
            if directory.exists():
                _durable_rmtree(directory)

    def _apply_pending(
        self,
        state: Path,
        plan: Plan,
        claim: Mapping[str, Any],
        pending: Mapping[str, Any],
        transaction_directory: Path,
    ) -> None:
        if (
            set(pending)
            != {"base_generation", "entries", "id", "new_snapshot", "version"}
            or pending["version"] != PROTOCOL_VERSION
            or pending["id"] != transaction_directory.name
            or not isinstance(pending["entries"], list)
            or not isinstance(pending["base_generation"], int)
            or pending["base_generation"] < 0
        ):
            _fail(f"pending output transaction is malformed: {transaction_directory}")
        snapshot = self._load_snapshot(state, claim)
        new_snapshot = pending["new_snapshot"]
        if not isinstance(new_snapshot, dict):
            _fail("pending output transaction has no valid replacement snapshot")
        self._validate_snapshot(new_snapshot, claim, transaction_directory / "pending.json")
        if new_snapshot["generation"] != pending["base_generation"] + 1:
            _fail("pending replacement snapshot has an invalid generation")
        if snapshot["generation"] == new_snapshot["generation"]:
            if snapshot != new_snapshot:
                _fail(
                    "committed snapshot conflicts with a pending transaction generation"
                )
            _sync_directory(state)
            _durable_rmtree(transaction_directory)
            return
        expected_entries = dict(snapshot["entries"])
        validated_entries: list[tuple[Path, str | None, str | None, Path | None]] = []
        seen_paths: set[str] = set()
        for index, entry in enumerate(pending["entries"]):
            if not isinstance(entry, dict) or set(entry) != {
                "after",
                "before",
                "path",
                "payload",
                "target",
                "transfer",
            }:
                _fail(
                    f"pending output transaction contains a malformed entry: {transaction_directory}"
                )
            relative = _validate_relative_path(str(entry["path"]))
            portable_relative = relative.casefold()
            if portable_relative in seen_paths:
                _fail("pending transaction repeats a generated path")
            seen_paths.add(portable_relative)
            destination = _output_path(plan.root, relative)
            before = entry["before"]
            after = entry["after"]
            target = entry["target"]
            transfer = entry["transfer"]
            if before is not None and not _is_sha256(str(before)):
                _fail("pending transaction contains an invalid prior hash")
            if not _is_sha256(str(target)):
                _fail("pending transaction contains an invalid target identity")
            previous_paths = [
                path for path in expected_entries if path.casefold() == portable_relative
            ]
            if before is None:
                if previous_paths:
                    _fail("pending transaction omits the committed prior state")
            elif (
                len(previous_paths) != 1
                or expected_entries[previous_paths[0]]["sha256"] != before
            ):
                _fail("pending transaction conflicts with the committed prior state")
            previous_entry = (
                expected_entries.pop(previous_paths[0]) if previous_paths else None
            )
            payload: Path | None = None
            if after is None:
                if entry["payload"] is not None:
                    _fail("retirement transaction unexpectedly contains a payload")
                if transfer is not None:
                    transfer = _validate_relative_path(str(transfer))
                    if previous_entry is None or transfer in expected_entries:
                        _fail("retirement transaction contains an invalid ownership transfer")
                    expected_entries[transfer] = previous_entry
            else:
                if transfer is not None:
                    _fail("publication transaction unexpectedly contains a transfer")
                if not _is_sha256(str(after)) or not isinstance(entry["payload"], str):
                    _fail("pending transaction contains an invalid replacement hash")
                if entry["payload"] != f"{index:08d}.payload":
                    _fail("pending transaction contains an invalid payload name")
                payload = transaction_directory / "payloads" / entry["payload"]
                if (
                    not payload.is_file()
                    or _is_link(payload)
                    or _sha256_file(payload) != after
                ):
                    _fail(f"pending transaction payload is missing or changed: {payload}")
                expected_entries[relative] = {"sha256": after, "target": target}
            validated_entries.append((destination, before, after, payload))
        if new_snapshot["entries"] != dict(sorted(expected_entries.items())):
            _fail("pending replacement snapshot does not match its transaction entries")
        if snapshot["generation"] != pending["base_generation"]:
            _fail(
                "pending transaction does not follow the committed snapshot generation"
            )
        for index, (destination, before, after, payload) in enumerate(validated_entries):
            if after is None:
                self._delete_if_state(destination, before)
            else:
                assert payload is not None
                self._publish_one(
                    plan.root,
                    destination,
                    payload,
                    before,
                    after,
                    pending["id"],
                    index,
                )
            self._inject(f"after-output-{index + 1}")
        _atomic_write(state / "snapshot.json", _canonical_json(new_snapshot))
        self._inject("after-snapshot")
        _durable_rmtree(transaction_directory)

    @staticmethod
    def _publish_one(
        output_root: Path,
        destination: Path,
        payload: Path,
        before: str | None,
        after: str,
        transaction_id: str,
        index: int,
    ) -> None:
        _durable_mkdir(destination.parent, anchor=output_root.parent)
        if destination.exists():
            observed = (
                _sha256_file(destination)
                if destination.is_file() and not _is_link(destination)
                else None
            )
            if observed == after:
                _sync_directory(destination.parent)
                return
            if observed != before:
                _fail(
                    f"generated output changed outside Protocyte before publication: {destination}"
                )
        elif before is not None:
            # Missing previously committed output is repairable from the
            # durable roll-forward payload.
            pass
        temporary = destination.with_name(
            f".{destination.name}.protocyte-{transaction_id}-{index}.tmp"
        )
        if os.path.lexists(temporary):
            if _is_link(temporary) or not temporary.is_file():
                _fail(f"publication temporary path is unsafe: {temporary}")
            temporary.unlink()
        with payload.open("rb") as source, temporary.open("xb") as target:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        if _sha256_file(temporary) != after:
            _fail(
                f"publication temporary bytes do not match the transaction: {temporary}"
            )
        os.replace(temporary, destination)
        _sync_directory(destination.parent)

    @staticmethod
    def _delete_if_state(destination: Path, before: str | None) -> None:
        if not os.path.lexists(destination):
            _sync_absence(destination)
            return
        if _is_link(destination) or not destination.is_file():
            _fail(f"retired generated output became unsafe: {destination}")
        if before is None or _sha256_file(destination) != before:
            _fail(
                f"retired generated output was modified and was preserved: {destination}"
            )
        destination.unlink()
        _sync_directory(destination.parent)

    @staticmethod
    def _require_observed_state(
        path: Path, expected: str | None, *, allow_absent: bool
    ) -> None:
        if not os.path.lexists(path):
            if allow_absent:
                return
            _fail(f"expected generated output is absent: {path}")
        if _is_link(path) or not path.is_file():
            _fail(f"generated output is not a safe regular file: {path}")
        if expected is None or _sha256_file(path) != expected:
            _fail(
                f"generated output bytes are not owned by the committed snapshot: {path}"
            )

    @staticmethod
    def _same_existing_file(first: Path, second: Path) -> bool:
        try:
            return (
                first.exists() and second.exists() and os.path.samefile(first, second)
            )
        except OSError:
            return False

    @staticmethod
    def _case_spelling_alias(root: Path, first: str, second: str) -> bool:
        first_parts = PurePosixPath(first).parts
        second_parts = PurePosixPath(second).parts
        if first_parts == second_parts or tuple(
            part.casefold() for part in first_parts
        ) != tuple(part.casefold() for part in second_parts):
            return False
        current = root
        try:
            for first_part, second_part in zip(first_parts, second_parts, strict=True):
                matches = [
                    entry.name
                    for entry in os.scandir(current)
                    if entry.name.casefold() == first_part.casefold()
                ]
                if len(matches) != 1:
                    return False
                current /= matches[0]
            return os.path.samefile(
                _output_path(root, first), _output_path(root, second)
            )
        except OSError:
            return False

    def _snapshot_entry_for_path(
        self,
        root: Path,
        entries: Mapping[str, Any],
        relative: str,
    ) -> tuple[str | None, Mapping[str, Any] | None]:
        if relative in entries:
            return relative, entries[relative]
        for previous_relative, entry in entries.items():
            if self._case_spelling_alias(root, relative, previous_relative):
                return previous_relative, entry
        return None, None

    @staticmethod
    def _is_snapshot_ancestor(
        root: Path, entries: Mapping[str, Any], relative: str
    ) -> bool:
        candidate = root.joinpath(*PurePosixPath(relative).parts)
        candidate_parts = PurePosixPath(relative).parts
        for snapshot_relative in entries:
            snapshot_parts = PurePosixPath(snapshot_relative).parts
            if len(candidate_parts) >= len(snapshot_parts):
                continue
            planned_ancestor = root.joinpath(
                *snapshot_parts[: len(candidate_parts)]
            )
            try:
                if planned_ancestor.is_dir() and os.path.samefile(
                    candidate, planned_ancestor
                ):
                    return True
            except OSError:
                continue
        return False

    @staticmethod
    def _require_requested_root(requested: Path, recorded: Path) -> None:
        if project_path(requested) != project_path(recorded):
            _fail(
                "requested output root does not match the physical root recorded by the claim: "
                f"{requested}"
            )

    @staticmethod
    def _inject(phase: str) -> None:
        if os.environ.get("PROTOCYTE_COORDINATOR_CRASH_AFTER") == phase:
            os._exit(86)


def _parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "encode-build-root",
            "reconcile",
            "validate",
            "publish",
            "reset",
        ),
    )
    parser.add_argument("--lock-root", type=Path)
    parser.add_argument("--build-root", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--target")
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--expected-claim")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = _parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
        if options.command == "encode-build-root":
            if options.build_root is None:
                _fail("encode-build-root requires --build-root")
            encoded = os.fspath(canonical_build_root(options.build_root)).encode("utf-8")
            print(encoded.hex())
            return 0
        if options.lock_root is None:
            _fail(f"{options.command} requires --lock-root")
        coordinator = OutputCoordinator(options.lock_root)
        if options.plan is not None:
            plan = Plan.read(options.plan)
        elif options.command == "reset" and options.output_root is not None:
            plan = coordinator.plan_for_root(options.output_root)
        else:
            _fail(f"{options.command} requires --plan")
        if options.command == "reconcile":
            print(coordinator.reconcile(plan))
        elif options.command == "validate":
            coordinator.validate(plan)
        elif options.command == "publish":
            if options.target is None or options.staging_root is None:
                _fail("publish requires --target and --staging-root")
            coordinator.publish(plan, options.target, options.staging_root)
        else:
            if options.expected_claim is None:
                _fail("reset requires --expected-claim")
            coordinator.reset(plan, options.expected_claim)
    except CoordinatorError as error:
        print(f"Protocyte output coordinator: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
