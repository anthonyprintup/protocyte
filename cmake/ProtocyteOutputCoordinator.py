"""Durable ownership and publication coordinator for Protocyte outputs.

CMake deliberately delegates mutable output state to this process.  Each
physical output root has one immutable claim, one committed snapshot, and at
most one write-ahead transaction.  Transactions carry durable replacement
payloads, so recovery always rolls forward and never has to infer intent from
partially published outputs.
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
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _load_json(path: Path, description: str) -> dict[str, Any]:
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
        expected_parent.mkdir(parents=True, exist_ok=True)
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
class Plan:
    root: Path
    build_root: Path
    build_id: str
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
        outputs: list[PlanOutput] = []
        for line in lines[1:]:
            key, separator, value = line.partition("=")
            if not separator:
                _fail(f"output plan contains a malformed line: {path}")
            if key == "output":
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
        return cls(root, build_root, build_id, ordered)

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
                "version",
            }
            or payload["version"] != PROTOCOL_VERSION
            or not isinstance(payload["outputs"], list)
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
        plan = cls(
            root,
            build_root,
            _path_key(build_root),
            tuple(sorted(outputs, key=lambda output: (output.relative, output.target))),
        )
        if payload["build_id"] != plan.build_id or payload["sha256"] != plan.digest:
            _fail(f"configured output plan identity is malformed: {source}")
        return plan


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
            snapshot = self._load_snapshot(state, claim)
            snapshot = self._retire_unplanned(state, plan, claim, snapshot)
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
            payload_directory.mkdir(parents=True)
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
                        }
                    )
                _sync_directory(payload_directory)
                _sync_directory(transaction_directory)
                _sync_directory(transaction_directory.parent)
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
                    shutil.rmtree(transaction_directory, ignore_errors=True)
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
                self._recover(state, plan, claim)
                snapshot = self._load_snapshot(state, claim)
                known_paths = set(snapshot["entries"])
                for relative, entry in snapshot["entries"].items():
                    output = _output_path(plan.root, relative)
                    self._require_observed_state(
                        output, entry["sha256"], allow_absent=True
                    )
                if plan.root.exists():
                    for candidate in plan.root.rglob("*"):
                        if not candidate.is_file() or _is_link(candidate):
                            continue
                        relative = candidate.relative_to(plan.root).as_posix()
                        if (
                            relative.casefold().endswith(GENERATED_SUFFIXES)
                            and relative not in known_paths
                        ):
                            _fail(
                                f"reset found an unowned generated-looking output: {candidate}"
                            )
                for relative, entry in snapshot["entries"].items():
                    output = _output_path(plan.root, relative)
                    self._require_observed_state(
                        output, entry["sha256"], allow_absent=True
                    )
                    with contextlib.suppress(FileNotFoundError):
                        output.unlink()
                shutil.rmtree(state)

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
        return Plan(claim_root, build_root, str(claim["build_id"]), ())

    def _claim(self, plan: Plan) -> Path:
        self.lock_root.mkdir(parents=True, exist_ok=True)
        state = self._state_directory(plan.root)
        with FileLock(self.lock_root / "registry.lock"):
            self._validate_registry(plan)
            state.mkdir(parents=True, exist_ok=True)
            claim_path = state / "claim.json"
            if claim_path.exists():
                self._load_claim(state, plan)
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
        if not roots.exists():
            return
        for claim_path in roots.glob("*/claim.json"):
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
        if claim["build_id"] != plan.build_id:
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
        return snapshot

    def _require_current_plan(self, state: Path, plan: Plan) -> None:
        current = _load_json(state / "plan.json", "configured output plan")
        if (
            current.get("sha256") != plan.digest
            or current.get("build_id") != plan.build_id
        ):
            _fail(
                "build-time output plan does not match the plan committed during configuration"
            )

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
                }
            )
            new_entries.pop(relative)
            if relative in hard_link_moves:
                new_entries[hard_link_moves[relative]] = snapshot["entries"][relative]
        if not pending_entries:
            return snapshot
        transaction_id = secrets.token_hex(32)
        transaction_directory = state / "transactions" / transaction_id
        transaction_directory.mkdir(parents=True)
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
        if not transaction_root.exists():
            return
        pending_directories = [
            directory
            for directory in transaction_root.iterdir()
            if directory.is_dir() and (directory / "pending.json").exists()
        ]
        if len(pending_directories) > 1:
            _fail(f"output root contains multiple pending transactions: {plan.root}")
        if pending_directories:
            directory = pending_directories[0]
            pending = _load_json(
                directory / "pending.json", "pending output transaction"
            )
            self._apply_pending(state, plan, claim, pending, directory)
        for directory in transaction_root.iterdir():
            if directory.is_dir():
                shutil.rmtree(directory)

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
        ):
            _fail(f"pending output transaction is malformed: {transaction_directory}")
        snapshot = self._load_snapshot(state, claim)
        new_snapshot = pending["new_snapshot"]
        if snapshot["generation"] == new_snapshot.get("generation"):
            if snapshot != new_snapshot:
                _fail(
                    "committed snapshot conflicts with a pending transaction generation"
                )
            shutil.rmtree(transaction_directory)
            return
        if snapshot["generation"] != pending["base_generation"]:
            _fail(
                "pending transaction does not follow the committed snapshot generation"
            )
        for index, entry in enumerate(pending["entries"]):
            if not isinstance(entry, dict) or set(entry) != {
                "after",
                "before",
                "path",
                "payload",
                "target",
            }:
                _fail(
                    f"pending output transaction contains a malformed entry: {transaction_directory}"
                )
            relative = _validate_relative_path(str(entry["path"]))
            destination = _output_path(plan.root, relative)
            before = entry["before"]
            after = entry["after"]
            target = entry["target"]
            if before is not None and not _is_sha256(str(before)):
                _fail("pending transaction contains an invalid prior hash")
            if not _is_sha256(str(target)):
                _fail("pending transaction contains an invalid target identity")
            if after is None:
                if entry["payload"] is not None:
                    _fail("retirement transaction unexpectedly contains a payload")
                self._delete_if_state(destination, before)
            else:
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
                    _fail(
                        f"pending transaction payload is missing or changed: {payload}"
                    )
                self._publish_one(
                    destination, payload, before, after, pending["id"], index
                )
            self._inject(f"after-output-{index + 1}")
        _atomic_write(state / "snapshot.json", _canonical_json(new_snapshot))
        self._inject("after-snapshot")
        shutil.rmtree(transaction_directory)

    @staticmethod
    def _publish_one(
        destination: Path,
        payload: Path,
        before: str | None,
        after: str,
        transaction_id: str,
        index: int,
    ) -> None:
        if destination.exists():
            observed = (
                _sha256_file(destination)
                if destination.is_file() and not _is_link(destination)
                else None
            )
            if observed == after:
                return
            if observed != before:
                _fail(
                    f"generated output changed outside Protocyte before publication: {destination}"
                )
        elif before is not None:
            # Missing previously committed output is repairable from the
            # durable roll-forward payload.
            pass
        destination.parent.mkdir(parents=True, exist_ok=True)
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
        "command", choices=("reconcile", "validate", "publish", "reset")
    )
    parser.add_argument("--lock-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--target")
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--expected-claim")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = _parse_arguments(sys.argv[1:] if arguments is None else arguments)
    try:
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
