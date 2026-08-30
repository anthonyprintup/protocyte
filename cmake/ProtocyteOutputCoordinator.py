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
import subprocess
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


def _physical_location_key(path: Path) -> tuple[int, int, tuple[str, ...]]:
    projected = project_path(path)
    suffix: list[str] = []
    current = projected
    while not os.path.lexists(current):
        suffix.append(current.name.casefold())
        parent = current.parent
        if parent == current:
            _fail(f"could not identify physical filesystem location: {path}")
        current = parent
    try:
        observed = current.stat()
    except OSError as error:
        _fail(f"could not identify physical filesystem location {path}: {error}")
    return observed.st_dev, observed.st_ino, tuple(reversed(suffix))


def _same_physical_location(first: Path, second: Path) -> bool:
    if first == second:
        return True
    try:
        if os.path.samefile(first, second):
            return True
    except OSError:
        pass
    return _physical_location_key(first) == _physical_location_key(second)


def _physically_contains(parent: Path, child: Path) -> bool:
    projected_parent = project_path(parent)
    current = project_path(child)
    while True:
        if _same_physical_location(projected_parent, current):
            return True
        next_parent = current.parent
        if next_parent == current:
            return False
        current = next_parent


def _paths_overlap(first: Path, second: Path) -> bool:
    return (
        _contains(first, second)
        or _contains(second, first)
        or _physically_contains(first, second)
        or _physically_contains(second, first)
    )


def _same_physical_path(first: Path, second: Path) -> bool:
    if first == second:
        return True
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def _existing_file_identity(path: Path) -> tuple[int, int] | None:
    try:
        if _is_link(path):
            return None
        observed = path.stat()
    except OSError:
        return None
    if not stat.S_ISREG(observed.st_mode):
        return None
    return observed.st_dev, observed.st_ino


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
        if _paths_overlap(root, path):
            _fail(
                "output plan generation staging overlaps its own output root: "
                f"{path} and {root}"
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


def _generation_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME"):
        encoded_name = f"PROTOCYTE_LOCKED_{name}_HEX"
        encoded = environment.pop(encoded_name, "")
        try:
            value = bytes.fromhex(encoded).decode("utf-8")
        except (ValueError, UnicodeError) as error:
            _fail(f"locked generation environment is malformed: {error}")
        if value:
            environment[name] = value
        else:
            environment.pop(name, None)
    return environment


class OutputCoordinator:
    def __init__(self, lock_root: Path) -> None:
        self.lock_root = project_path(_require_absolute(lock_root, "output lock root"))

    def reconcile(self, plan: Plan) -> str:
        state = self._claim(plan)
        with FileLock(self._generation_lock(plan.root)):
            with FileLock(self._publication_lock(plan.root)):
                return self._reconcile_locked(state, plan)

    def reconcile_set(
        self, retired: Sequence[Plan], current: Sequence[Plan]
    ) -> list[str | None]:
        if not current and not retired:
            _fail("reconcile-set requires at least one plan")
        plans = [*retired, *current]
        roots = {_path_key(plan.root): plan.root for plan in plans}
        retiring_root_keys = {_path_key(plan.root) for plan in retired}
        _durable_mkdir(self.lock_root)
        with contextlib.ExitStack() as locks:
            locks.enter_context(FileLock(self.lock_root / "registry.lock"))
            for root in sorted(roots.values(), key=_portable_identity):
                locks.enter_context(FileLock(self._generation_lock(root)))
            for root in sorted(roots.values(), key=_portable_identity):
                locks.enter_context(FileLock(self._publication_lock(root)))
            self._validate_plan_set(current)
            for plan in current:
                self._validate_registry(plan, retiring_root_keys)
            states: dict[str, Path] = {}
            existing_plans: list[Plan] = []
            active_retired: set[int] = set()
            for index, plan in enumerate(retired):
                state = self._state_directory(plan.root)
                claim_path = state / "claim.json"
                if not claim_path.exists():
                    continue
                claim = _load_json(claim_path, "output claim")
                self._validate_claim_shape(claim, claim_path)
                claim_root, claim_build_root = self._claim_paths(claim, claim_path)
                if (
                    str(claim["build_id"]) != plan.build_id
                    or not _same_physical_path(claim_root, plan.root)
                    or not _same_physical_path(claim_build_root, plan.build_root)
                ):
                    continue
                self._load_claim(state, plan)
                states[_path_key(plan.root)] = state
                existing_plans.append(plan)
                active_retired.add(index)
            for plan in current:
                state = self._state_directory(plan.root)
                claim_path = state / "claim.json"
                if claim_path.exists():
                    self._load_claim(state, plan)
                    existing_plans.append(plan)
                states[_path_key(plan.root)] = state
            for plan in existing_plans:
                state = states[_path_key(plan.root)]
                claim = self._load_claim(state, plan)
                self._recover(state, plan, claim)
                self._load_snapshot(state, claim)
                self._load_recorded_plan(state, claim)
            for plan in current:
                state = states[_path_key(plan.root)]
                if not (state / "claim.json").exists():
                    self._initialize_claim_locked(state, plan)
            results: list[str | None] = []
            for index, plan in enumerate(plans):
                if index < len(retired) and index not in active_retired:
                    results.append(None)
                else:
                    results.append(
                        self._reconcile_locked(states[_path_key(plan.root)], plan)
                    )
            return results

    def _reconcile_locked(self, state: Path, plan: Plan) -> str:
        claim = self._load_claim(state, plan)
        self._recover(state, plan, claim)
        previous_plan = self._load_recorded_plan(state, claim)
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
            self._require_current_plan(state, plan, claim)

    def publish(self, plan: Plan, target: str, staging_root: Path) -> None:
        if not _is_sha256(target):
            _fail("publish target identity is invalid")
        state = self._state_directory(plan.root)
        with FileLock(self._publication_lock(plan.root)):
            claim = self._load_claim(state, plan)
            self._recover(state, plan, claim)
            self._require_current_plan(state, plan, claim)
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
                    "plan": {**plan.payload, "sha256": plan.digest},
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
            with FileLock(self._generation_lock(plan.root)):
                with FileLock(self._publication_lock(plan.root)):
                    claim = self._load_claim(state, plan)
                    if claim["token"] != expected_token:
                        _fail("reset claim token does not match the live immutable claim")
                    reset_path = state / "reset.json"
                    if not reset_path.exists():
                        self._recover(state, plan, claim)
                    snapshot = self._load_snapshot(state, claim)
                    recorded_plan = self._load_recorded_plan(state, claim)
                    staging = [
                        {"id": target.identity, "path": os.fspath(target.staging)}
                        for target in (recorded_plan.targets if recorded_plan else ())
                    ]
                    if reset_path.exists():
                        intent = self._load_reset_intent(
                            reset_path,
                            plan.root,
                            claim,
                            snapshot["entries"],
                            staging,
                        )
                    else:
                        self._validate_reset_inventory(plan.root, snapshot["entries"])
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
        path: Path,
        root: Path,
        claim: Mapping[str, Any],
        snapshot_entries: Mapping[str, Any],
        recorded_staging: Sequence[Mapping[str, str]],
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
        if intent["entries"] != snapshot_entries or intent["staging"] != list(
            recorded_staging
        ):
            _fail("pending output reset does not match committed claim state")
        return intent

    @staticmethod
    def _release_claim(state: Path) -> None:
        preserved = {"claim.json", "plan.json", "reset.json", "snapshot.json"}
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
        for name in ("plan.json", "snapshot.json", "reset.json"):
            path = state / name
            if path.exists():
                path.unlink()
                _sync_directory(state)
        state.rmdir()
        _sync_directory(state.parent)

    def plan_for_root(self, root: Path) -> Plan:
        root = project_path(_require_absolute(root, "output root"))
        state = self._state_directory(root)
        claim_path = state / "claim.json"
        claim = _load_json(claim_path, "output claim")
        self._validate_claim_shape(claim, claim_path)
        claim_root, build_root = self._claim_paths(claim, claim_path)
        if claim["root_key"] != _path_key(root):
            _fail(
                "requested output root does not identify the recorded claim: "
                f"{root}"
            )
        self._require_requested_root(root, claim_root)
        plan_path = state / "plan.json"
        if plan_path.exists():
            plan = self._load_recorded_plan(state, claim)
            assert plan is not None
            return plan
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
            self._initialize_claim_locked(state, plan)
        return state

    def _initialize_claim_locked(self, state: Path, plan: Plan) -> None:
        _durable_mkdir(state, anchor=self.lock_root)
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
        # Publish the immutable claim last. A crash before this rename leaves
        # only unclaimed initialization data, which a retry may safely replace.
        _atomic_write(state / "claim.json", _canonical_json(claim))
        self._inject("after-claim")

    @staticmethod
    def _validate_plan_set(plans: Sequence[Plan]) -> None:
        for index, first in enumerate(plans):
            for second in plans[index + 1 :]:
                if _paths_overlap(first.root, second.root):
                    _fail(
                        "current output plans contain overlapping roots: "
                        f"{first.root} and {second.root}"
                    )
                for target in first.targets:
                    if _paths_overlap(target.staging, second.root):
                        _fail("current output plan staging overlaps another output root")
                    for other in second.targets:
                        if _paths_overlap(target.staging, other.staging):
                            _fail("current output plans contain overlapping staging")
                for target in second.targets:
                    if _paths_overlap(target.staging, first.root):
                        _fail("current output plan staging overlaps another output root")

    def _validate_registry(
        self, plan: Plan, retiring_root_keys: set[str] | None = None
    ) -> None:
        if retiring_root_keys is None:
            retiring_root_keys = set()
        for target in plan.targets:
            if _contains(target.staging, self.lock_root) or _physically_contains(
                target.staging, self.lock_root
            ):
                _fail(
                    "generation staging contains the output coordinator lock root: "
                    f"{target.staging} and {self.lock_root}"
                )
        internal_paths = (
            self.lock_root / "roots",
            self.lock_root / "generation",
            self.lock_root / "publication",
        )
        if _paths_overlap(plan.root, self.lock_root) or any(
            _paths_overlap(path, plan.root) for path in internal_paths
        ):
            _fail(
                "output root overlaps the output coordinator lock namespace: "
                f"{plan.root} and {self.lock_root}"
            )
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
            claimed_root, _ = self._claim_paths(claim, claim_path)
            if entry.name != claim["root_key"]:
                _fail(f"output claim is stored under the wrong registry key: {claim_path}")
            recorded_plan = self._load_recorded_plan(state, claim)
            if _paths_overlap(claimed_root, plan.root):
                if _path_key(claimed_root) != _path_key(plan.root):
                    _fail(
                        "output root overlaps a root claimed by another build: "
                        f"{plan.root} and {claimed_root}"
                    )
            recorded_targets = recorded_plan.targets if recorded_plan else ()
            for recorded_target in recorded_targets:
                if _paths_overlap(recorded_target.staging, plan.root):
                    _fail(
                        "output root overlaps staging reserved by another plan: "
                        f"{plan.root} and {recorded_target.staging}"
                    )
            for target in plan.targets:
                if _paths_overlap(claimed_root, target.staging):
                    _fail(
                        "generation staging overlaps a claimed output root: "
                        f"{target.staging} and {claimed_root}"
                    )
                for recorded_target in recorded_targets:
                    if (
                        _path_key(plan.root) == _path_key(claimed_root)
                        and target.identity == recorded_target.identity
                    ):
                        continue
                    if (
                        str(claim["root_key"]) in retiring_root_keys
                        and str(claim["build_id"]) == plan.build_id
                        and target.identity == recorded_target.identity
                    ):
                        continue
                    if _paths_overlap(recorded_target.staging, target.staging):
                        _fail(
                            "generation staging overlaps staging reserved by another plan: "
                            f"{target.staging} and {recorded_target.staging}"
                        )

    def _state_directory(self, root: Path) -> Path:
        return self.lock_root / "roots" / _path_key(root)

    def _publication_lock(self, root: Path) -> Path:
        return self.lock_root / "publication" / f"{_path_key(root)}.lock"

    def _generation_lock(self, root: Path) -> Path:
        return self.lock_root / "generation" / f"{_path_key(root)}.lock"

    def _load_claim(self, state: Path, plan: Plan) -> dict[str, Any]:
        claim_path = state / "claim.json"
        claim = _load_json(claim_path, "output claim")
        self._validate_claim_shape(claim, claim_path)
        recorded_root, recorded_build = self._claim_paths(claim, claim_path)
        requested_root = project_path(plan.root)
        if claim["root_key"] != _path_key(plan.root) or not _same_physical_path(
            recorded_root, requested_root
        ):
            _fail(
                f"output claim does not identify the requested physical root: {claim_path}"
            )
        same_build = _same_physical_path(recorded_build, plan.build_root)
        if claim["build_id"] != plan.build_id or not same_build:
            _fail(
                "output root is claimed by a different CMake build tree; use the owning build or reset "
                f"the claim explicitly: {plan.root}"
            )
        return claim

    @staticmethod
    def _require_plan_claim_binding(
        plan: Plan, claim: Mapping[str, Any], source: Path
    ) -> None:
        claim_root, claim_build_root = OutputCoordinator._claim_paths(claim, source)
        if (
            str(claim["root_key"]) != _path_key(plan.root)
            or str(claim["build_id"]) != plan.build_id
            or not _same_physical_path(claim_root, plan.root)
            or not _same_physical_path(claim_build_root, plan.build_root)
        ):
            _fail(f"configured output plan does not match its immutable claim: {source}")

    @staticmethod
    def _claim_paths(
        claim: Mapping[str, Any], source: Path
    ) -> tuple[Path, Path]:
        claim_root = project_path(Path(str(claim["root"])))
        claim_build_root = project_path(Path(str(claim["build_root"])))
        if (
            str(claim["root_key"]) != _path_key(claim_root)
            or str(claim["build_id"]) != _path_key(claim_build_root)
        ):
            _fail(f"output claim identity is inconsistent: {source}")
        return claim_root, claim_build_root

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

    def _require_current_plan(
        self, state: Path, plan: Plan, claim: Mapping[str, Any]
    ) -> None:
        current = self._load_recorded_plan(state, claim)
        if current is None or current.digest != plan.digest:
            _fail(
                "build-time output plan does not match the plan committed during configuration"
            )

    def _load_recorded_plan(
        self, state: Path, claim: Mapping[str, Any]
    ) -> Plan | None:
        path = state / "plan.json"
        if not path.exists():
            return None
        plan = Plan.from_payload(_load_json(path, "configured output plan"), path)
        self._require_plan_claim_binding(plan, claim, path)
        return plan

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
        desired_targets = {output.relative: output.target for output in plan.outputs}
        desired = set(desired_targets)
        desired_by_portable = {relative.casefold(): relative for relative in desired}
        desired_paths = {
            relative: _output_path(plan.root, relative) for relative in desired
        }
        desired_by_identity: dict[tuple[int, int], list[str]] = {}
        for relative, path in desired_paths.items():
            identity = _existing_file_identity(path)
            if identity is not None:
                desired_by_identity.setdefault(identity, []).append(relative)
        claimed_transfer_destinations: set[str] = set()
        new_entries = dict(snapshot["entries"])
        pending_entries: list[dict[str, Any]] = []
        for relative in snapshot["entries"]:
            if relative in desired:
                continue
            portable_match = desired_by_portable.get(relative.casefold())
            aliased = portable_match is not None and self._case_spelling_alias(
                plan.root, relative, portable_match
            )
            if aliased:
                continue
            before = snapshot["entries"][relative]["sha256"]
            output = _output_path(plan.root, relative)
            identity: tuple[int, int] | None = None
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
                identity = _existing_file_identity(output)
                if identity is None:
                    continue
            linked_desired = (
                desired_by_identity.get(identity, []) if identity is not None else []
            )
            transfer_candidates = [
                destination
                for destination in linked_desired
                if destination not in snapshot["entries"]
            ]
            if len(transfer_candidates) > 1:
                _fail(
                    "retired generated output has multiple desired hard-link destinations: "
                    f"{relative}"
                )
            transfer: dict[str, int | str] | None = None
            if transfer_candidates:
                destination = transfer_candidates[0]
                if destination not in claimed_transfer_destinations:
                    assert identity is not None
                    transfer = {
                        "device": identity[0],
                        "inode": identity[1],
                        "path": destination,
                    }
                    claimed_transfer_destinations.add(destination)
            transaction_target = snapshot["entries"][relative]["target"]
            if transfer is not None:
                transaction_target = desired_targets[str(transfer["path"])]
            pending_entries.append(
                {
                    "after": None,
                    "before": before,
                    "path": relative,
                    "payload": None,
                    "target": transaction_target,
                    "transfer": transfer,
                }
            )
            new_entries.pop(relative)
            if transfer is not None:
                new_entries[str(transfer["path"])] = {
                    "sha256": before,
                    "target": transaction_target,
                }
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
            "plan": {**plan.payload, "sha256": plan.digest},
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
            pending_plan = pending.get("plan")
            if not isinstance(pending_plan, dict):
                _fail("pending output transaction has no authorizing plan")
            recovery_plan = Plan.from_payload(
                pending_plan, directory / "pending.json"
            )
            self._require_plan_claim_binding(
                recovery_plan, claim, directory / "pending.json"
            )
            self._apply_pending(state, recovery_plan, claim, pending, directory)
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
            != {
                "base_generation",
                "entries",
                "id",
                "new_snapshot",
                "plan",
                "version",
            }
            or pending["version"] != PROTOCOL_VERSION
            or pending["id"] != transaction_directory.name
            or pending["plan"] != {**plan.payload, "sha256": plan.digest}
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
        validated_entries: list[
            tuple[
                Path,
                str | None,
                str | None,
                Path | None,
                tuple[Path, tuple[int, int], str] | None,
            ]
        ] = []
        planned_targets = {output.relative: output.target for output in plan.outputs}
        planned_by_portable = {
            relative.casefold(): relative for relative in planned_targets
        }
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
            if relative in seen_paths:
                _fail("pending transaction repeats a generated path")
            seen_paths.add(relative)
            destination = _output_path(plan.root, relative)
            before = entry["before"]
            after = entry["after"]
            target = entry["target"]
            transfer = entry["transfer"]
            if before is not None and not _is_sha256(str(before)):
                _fail("pending transaction contains an invalid prior hash")
            if not _is_sha256(str(target)):
                _fail("pending transaction contains an invalid target identity")
            previous_path, previous_entry = self._snapshot_entry_for_path(
                plan.root, expected_entries, relative
            )
            if before is None:
                if previous_path is not None:
                    _fail("pending transaction omits the committed prior state")
            elif (
                previous_path is None
                or previous_entry is None
                or previous_entry["sha256"] != before
            ):
                _fail("pending transaction conflicts with the committed prior state")
            if previous_path is not None:
                previous_entry = expected_entries.pop(previous_path)
            payload: Path | None = None
            validated_transfer: tuple[Path, tuple[int, int], str] | None = None
            if after is None:
                if entry["payload"] is not None:
                    _fail("retirement transaction unexpectedly contains a payload")
                planned_match = planned_by_portable.get(relative.casefold())
                if planned_match is not None and (
                    planned_match == relative
                    or self._case_spelling_alias(
                        plan.root, relative, planned_match
                    )
                ):
                    _fail("retirement transaction contains a planned output")
                if transfer is not None:
                    if not isinstance(transfer, dict) or set(transfer) != {
                        "device",
                        "inode",
                        "path",
                    }:
                        _fail(
                            "retirement transaction contains an invalid ownership transfer"
                        )
                    transfer_path = _validate_relative_path(str(transfer["path"]))
                    device = transfer["device"]
                    inode = transfer["inode"]
                    if (
                        previous_entry is None
                        or transfer_path in expected_entries
                        or not isinstance(device, int)
                        or isinstance(device, bool)
                        or device < 0
                        or not isinstance(inode, int)
                        or isinstance(inode, bool)
                        or inode < 0
                        or planned_targets.get(transfer_path) != target
                    ):
                        _fail(
                            "retirement transaction contains an invalid ownership transfer"
                        )
                    transfer_destination = _output_path(plan.root, transfer_path)
                    transfer_identity = (device, inode)
                    if (
                        _existing_file_identity(transfer_destination)
                        != transfer_identity
                    ):
                        _fail(
                            "ownership transfer destination changed physical identity"
                        )
                    self._require_observed_state(
                        transfer_destination, before, allow_absent=False
                    )
                    expected_entries[transfer_path] = {
                        "sha256": before,
                        "target": target,
                    }
                    validated_transfer = (
                        transfer_destination,
                        transfer_identity,
                        before,
                    )
                elif previous_entry is not None and previous_entry["target"] != target:
                    _fail("retirement transaction changes the prior target identity")
            else:
                if transfer is not None:
                    _fail("publication transaction unexpectedly contains a transfer")
                if planned_targets.get(relative) != target:
                    _fail(
                        "publication transaction does not match the current output plan"
                    )
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
            validated_entries.append(
                (destination, before, after, payload, validated_transfer)
            )
        if new_snapshot["entries"] != dict(sorted(expected_entries.items())):
            _fail("pending replacement snapshot does not match its transaction entries")
        if snapshot["generation"] != pending["base_generation"]:
            _fail(
                "pending transaction does not follow the committed snapshot generation"
            )
        for index, (destination, before, after, payload, transfer) in enumerate(
            validated_entries
        ):
            if after is None:
                if transfer is not None:
                    transfer_destination, transfer_identity, transfer_hash = transfer
                    if (
                        _existing_file_identity(transfer_destination)
                        != transfer_identity
                    ):
                        _fail(
                            "ownership transfer destination changed physical identity"
                        )
                    self._require_observed_state(
                        transfer_destination, transfer_hash, allow_absent=False
                    )
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
        if not _same_physical_path(project_path(requested), project_path(recorded)):
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
            "reconcile-set",
            "run-generation",
            "target-outputs",
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
    parser.add_argument("--exec", dest="execution", nargs=argparse.REMAINDER)
    parser.add_argument("--current-plan", type=Path, action="append", default=[])
    parser.add_argument("--retired-plan", type=Path, action="append", default=[])
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
        if options.command == "reconcile-set":
            current = [Plan.read(path) for path in options.current_plan]
            retired = [Plan.read(path) for path in options.retired_plan]
            for token in coordinator.reconcile_set(retired, current):
                print(token if token is not None else "released")
            return 0
        if options.command == "run-generation":
            if options.output_root is None or options.plan is None:
                _fail("run-generation requires --output-root and --plan")
            if not options.execution:
                _fail("run-generation requires --exec")
            requested_root = project_path(options.output_root)
            with FileLock(coordinator._generation_lock(requested_root)):
                plan = Plan.read(options.plan)
                coordinator._require_requested_root(requested_root, plan.root)
                return subprocess.run(
                    options.execution,
                    check=False,
                    env=_generation_environment(),
                ).returncode
        if options.plan is not None:
            plan = Plan.read(options.plan)
        elif options.command == "reset" and options.output_root is not None:
            plan = coordinator.plan_for_root(options.output_root)
        else:
            _fail(f"{options.command} requires --plan")
        if options.command == "target-outputs":
            if options.target is None or not _is_sha256(options.target):
                _fail("target-outputs requires a valid --target")
            outputs = [
                _output_path(plan.root, output.relative)
                for output in plan.outputs
                if output.target == options.target
            ]
            if not outputs:
                _fail(f"output plan contains no outputs for target {options.target}")
            for output in outputs:
                print(os.fspath(output).encode("utf-8").hex())
        elif options.command == "reconcile":
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
