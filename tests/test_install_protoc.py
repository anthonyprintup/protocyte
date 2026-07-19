import hashlib
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest


def _load_install_protoc_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "scripts"
        / "install_protoc.py"
    )
    spec = importlib.util.spec_from_file_location("install_protoc", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install_protoc = _load_install_protoc_module()
owned_transactions = sys.modules[install_protoc.locked_destination.__module__]


def test_default_transaction_state_directory_is_per_user_and_private(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )

    state_directory = owned_transactions._state_directory()

    assert state_directory.parent == tmp_path
    assert state_directory.name.startswith(
        owned_transactions._STATE_DIRECTORY_NAME + "-"
    )
    assert state_directory.name != owned_transactions._STATE_DIRECTORY_NAME
    if os.name != "nt":
        assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700


def test_transaction_state_metadata_is_private_and_redacts_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "home" / "account" / "repo" / "generated"
    destination.parent.mkdir(parents=True)
    rollback = destination.with_name(".generated.protocyte-rollback")
    rollback.mkdir()

    with install_protoc.locked_destination(destination):
        owner = install_protoc._create_install_transaction(
            destination,
            "transaction",
        )
        try:
            owner.bind_path("rollback", rollback)
            marker_paths = list(state_directory.rglob("*.owner"))
            assert len(marker_paths) == 1
            marker_path = marker_paths[0]
            owner._lease._file.seek(0)
            payload = json.loads(owner._lease._file.read().decode("utf-8"))
            marker_mode = stat.S_IMODE(marker_path.stat().st_mode)
        finally:
            owner.cleanup(install_protoc._remove_path)

    assert set(payload) == {
        "schema",
        "destination_key",
        "kind",
        "token",
        "owned_paths",
    }
    assert payload["destination_key"] == owned_transactions._destination_key(
        destination
    )
    rollback_identity = payload["owned_paths"]["rollback"]
    assert set(rollback_identity) == {
        "path_key",
        "device",
        "inode",
        "type",
        "reparse_tag",
    }
    assert rollback_identity["path_key"] == owned_transactions._destination_key(
        rollback
    )
    serialized_payload = json.dumps(payload, sort_keys=True)
    assert (
        owned_transactions._normalized_destination(destination)
        not in serialized_payload
    )
    assert (
        owned_transactions._normalized_destination(rollback) not in serialized_payload
    )

    if os.name != "nt":
        assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700
        assert marker_mode == 0o600
        lock_paths = list(state_directory.rglob("*.lock"))
        assert lock_paths
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in lock_paths)


def test_transaction_state_directory_rejects_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    state_directory = tmp_path / "state"
    try:
        state_directory.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    with pytest.raises(RuntimeError, match="linked transaction state directory"):
        owned_transactions._state_directory()


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership check")
def test_transaction_state_directory_rejects_wrong_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    state_directory.mkdir(mode=0o700)
    state_directory.chmod(0o700)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    owner_id = state_directory.stat().st_uid
    monkeypatch.setattr(
        owned_transactions,
        "_effective_user_id",
        lambda: owner_id + 1,
    )

    with pytest.raises(RuntimeError, match="not owned by the current user"):
        owned_transactions._state_directory()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission check")
def test_transaction_state_directory_rejects_insecure_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    state_directory.mkdir()
    state_directory.chmod(0o755)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    with pytest.raises(RuntimeError, match="private 0700 permissions"):
        owned_transactions._state_directory()


def _transaction_state_entries(state_directory: Path) -> set[str]:
    return {
        path.relative_to(state_directory).as_posix()
        for path in state_directory.rglob("*")
    }


def test_destination_lock_state_is_bounded_across_distinct_destinations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    for index in range(64):
        with install_protoc.locked_destination(tmp_path / f"destination-{index}"):
            pass

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def test_nested_transaction_state_is_isolated_from_unreleased_flat_v2_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )
    destination = tmp_path / "protoc"
    key = owned_transactions._destination_key(destination)
    token = "a" * 32
    v2_state = tmp_path / (
        "protocyte-owned-transactions-v2-" + owned_transactions._user_namespace()
    )
    v2_state.mkdir(mode=0o700)
    v2_state.chmod(0o700)
    legacy_lock = v2_state / f"{key}.destination.lock"
    legacy_marker = v2_state / f"{key}.transaction.{token}.owner"
    legacy_sibling = tmp_path / f".protoc.protocyte-transaction-{token}"
    legacy_lock.write_bytes(b"\0")
    legacy_marker.write_text("unreleased-v2-state\n", encoding="utf-8")
    legacy_sibling.mkdir()

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    v3_state = owned_transactions._state_directory()
    assert v3_state != v2_state
    assert _transaction_state_entries(v3_state) == {"registry.lock"}
    assert legacy_lock.read_bytes() == b"\0"
    assert legacy_marker.read_text(encoding="utf-8") == "unreleased-v2-state\n"
    assert legacy_sibling.is_dir()


def test_destination_lock_pruning_preserves_a_live_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "live").write_text("live\n", encoding="utf-8")

    try:
        with install_protoc.locked_destination(destination):
            pass

        assert owner.marker_path.is_file()
        assert (owner.path / "live").read_text(encoding="utf-8") == "live\n"
    finally:
        owner.cleanup(install_protoc._remove_path)

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def _write_archive(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, "content")


class _Response(io.BytesIO):
    def __init__(self, content: bytes, content_length: str | None = None) -> None:
        super().__init__(content)
        self.headers = (
            {} if content_length is None else {"Content-Length": content_length}
        )


class _SlowResponse(_Response):
    def __init__(
        self,
        content: bytes,
        read_started: threading.Event,
        release_read: threading.Event,
    ) -> None:
        super().__init__(content)
        self.read_started = read_started
        self.release_read = release_read

    def read(self, size: int = -1) -> bytes:
        self.read_started.set()
        self.release_read.wait(timeout=1.0)
        return super().read(size)


def test_extract_archive_safely_preserves_normal_archive_layout(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(
        archive_path,
        [
            "bin/protoc",
            "include/google/protobuf/descriptor.proto",
        ],
    )

    with zipfile.ZipFile(archive_path) as archive:
        install_protoc.extract_archive_safely(archive, destination)

    assert (destination / "bin" / "protoc").read_text(encoding="utf-8") == "content"
    assert (
        destination / "include" / "google" / "protobuf" / "descriptor.proto"
    ).is_file()


def test_download_archive_hashes_content_and_applies_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"trusted archive bytes"
    observed: dict[str, object] = {}

    def fake_urlopen(url: str, *, timeout: float) -> _Response:
        observed.update(url=url, timeout=timeout)
        return _Response(content, str(len(content)))

    monkeypatch.setattr(install_protoc, "urlopen", fake_urlopen)
    archive_path = tmp_path / "protoc.zip"

    actual_sha256 = install_protoc.download_archive(
        "https://example.invalid/protoc.zip",
        archive_path,
        timeout=7.5,
    )

    assert observed == {"url": "https://example.invalid/protoc.zip", "timeout": 7.5}
    assert archive_path.read_bytes() == content
    assert actual_sha256 == hashlib.sha256(content).hexdigest()


def test_download_archive_enforces_wall_clock_deadline_against_slow_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_started = threading.Event()
    release_read = threading.Event()
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _SlowResponse(
            b"slow bytes",
            read_started,
            release_read,
        ),
    )
    archive_path = tmp_path / "protoc.zip"

    try:
        with pytest.raises(RuntimeError, match="wall-clock deadline"):
            install_protoc.download_archive(
                "https://example.invalid/protoc.zip",
                archive_path,
                timeout=0.02,
            )
    finally:
        release_read.set()

    assert read_started.is_set()
    assert not archive_path.exists()


@pytest.mark.parametrize("declared_size", ["not-a-number", "9"])
def test_download_archive_rejects_invalid_or_oversized_content_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declared_size: str,
) -> None:
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _Response(b"content", declared_size),
    )
    archive_path = tmp_path / "protoc.zip"

    with pytest.raises(RuntimeError, match="Content-Length|too large"):
        install_protoc.download_archive(
            "https://example.invalid/protoc.zip", archive_path, max_bytes=8
        )

    assert not archive_path.exists()


def test_download_archive_rejects_stream_that_exceeds_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _Response(b"ninebytes"),
    )
    archive_path = tmp_path / "protoc.zip"

    with pytest.raises(RuntimeError, match="exceeds"):
        install_protoc.download_archive(
            "https://example.invalid/protoc.zip", archive_path, max_bytes=8
        )

    assert not archive_path.exists()


def test_verify_archive_sha256_rejects_mismatch() -> None:
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        install_protoc.verify_archive_sha256("0" * 64, "1" * 64, "protoc.zip")


def test_main_rejects_digest_mismatch_before_extraction_or_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )
    monkeypatch.setattr(
        install_protoc,
        "download_archive",
        lambda _url, _archive_path: "0" * 64,
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unverified archive was extracted or executed")

    monkeypatch.setattr(install_protoc.zipfile, "ZipFile", forbidden)
    monkeypatch.setattr(install_protoc.subprocess, "run", forbidden)

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        install_protoc.main()

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_main_preserves_existing_destination_when_staged_protoc_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = install_protoc.resolve_platform_asset()
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")

    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )

    def fake_download(_url: str, archive_path: Path) -> str:
        _write_archive(
            archive_path,
            [
                f"bin/{asset.executable_name}",
                "include/google/protobuf/descriptor.proto",
            ],
        )
        return install_protoc.load_default_sha256(asset)

    monkeypatch.setattr(install_protoc, "download_archive", fake_download)
    monkeypatch.setattr(
        install_protoc.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, "protoc --version")
        ),
    )

    with pytest.raises(subprocess.CalledProcessError):
        install_protoc.main()

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_replace_destination_installs_staging_and_removes_previous(
    tmp_path: Path,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old", encoding="utf-8")

    install_protoc.replace_destination(staging, destination)

    assert (destination / "new").read_text(encoding="utf-8") == "new"
    assert not (destination / "old").exists()
    assert not (transaction / "previous-install").exists()


def test_replace_destination_restores_previous_if_staging_rename_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    original_replace = Path.replace

    def fail_staging_replace(source: Path, target: Path) -> Path:
        if source == staging:
            raise OSError("injected staging rename failure")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_staging_replace)

    with pytest.raises(OSError, match="injected staging rename failure"):
        install_protoc.replace_destination(staging, destination)

    assert marker.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("promoted_new_install", [False, True])
def test_next_install_recovers_an_interrupted_swap(
    tmp_path: Path,
    promoted_new_install: bool,
) -> None:
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "known-good").write_text("preserve", encoding="utf-8")
    rollback = _leave_owned_install_rollback(destination)
    if promoted_new_install:
        destination.mkdir()
        (destination / "partial").write_text("discard", encoding="utf-8")

    install_protoc._recover_interrupted_install_state(destination)

    assert (destination / "known-good").read_text(encoding="utf-8") == "preserve"
    assert not (destination / "partial").exists()
    assert not rollback.exists()


def _leave_owned_install_rollback(destination: Path) -> Path:
    owner = install_protoc._create_install_transaction(destination, "transaction")
    rollback = install_protoc._installation_rollback_path(destination)
    destination.replace(rollback)
    owner.bind_path("rollback", rollback)
    owner.close(remove_marker=False)
    return rollback


def _install_crash_test_environment(
    monkeypatch: pytest.MonkeyPatch,
    state_directory: Path,
) -> dict[str, str]:
    monkeypatch.setenv("PROTOCYTE_TRANSACTION_STATE_DIR", str(state_directory))
    environment = os.environ.copy()
    source_root = Path(__file__).resolve().parents[1] / "src"
    python_path = [str(source_root)]
    if existing := environment.get("PYTHONPATH"):
        python_path.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    return environment


def test_destination_lock_recovers_state_left_by_a_hard_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("lock_crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module.locked_destination(destination):
    os._exit(86)
"""

    result = subprocess.run(
        [sys.executable, "-c", script, str(script_path), str(destination)],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 86, result.stdout + result.stderr
    assert any(path.is_dir() for path in state_directory.iterdir())

    with install_protoc.locked_destination(destination):
        pass

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def test_destination_lock_prune_and_reopen_never_split_the_lock_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    start = tmp_path / "start"
    violation = tmp_path / "mutual-exclusion-violation"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import sys
import time
from pathlib import Path

script_path, destination, start, violation = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("lock_race_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
critical = destination.with_name(".protocyte-lock-critical")
while not start.exists():
    time.sleep(0.005)
for _ in range(12):
    with module.locked_destination(destination):
        try:
            critical.mkdir()
        except FileExistsError:
            violation.touch()
            raise
        try:
            time.sleep(0.003)
        finally:
            critical.rmdir()
"""
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(script_path),
                str(destination),
                str(start),
                str(violation),
            ],
            cwd=script_path.parents[2],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for _ in range(4)
    ]
    outputs: list[tuple[str, str]] = []
    try:
        start.touch()
        outputs = [process.communicate(timeout=20.0) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    for process, (stdout, stderr) in zip(processes, outputs, strict=True):
        assert process.returncode == 0, stdout + stderr
    assert not violation.exists()
    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def test_owned_recovery_does_not_scan_the_global_state_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "dead").write_text("dead\n", encoding="utf-8")
    owner.close(remove_marker=False)
    original_iterdir = Path.iterdir

    def reject_global_scan(path: Path):
        if path == state_directory:
            raise AssertionError("recovery scanned the global transaction state")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", reject_global_scan)

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not owner.path.exists()
    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def _run_install_hard_exit(
    destination: Path,
    phase: str,
    environment: dict[str, str],
    *,
    recovery_only: bool = False,
) -> None:
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
interrupted_phase = sys.argv[3]
recovery_only = sys.argv[4] == "recovery"
spec = importlib.util.spec_from_file_location("crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def hard_exit(phase: str) -> None:
    if phase == interrupted_phase:
        os._exit(89)

module._install_swap_phase = hard_exit
with module.locked_destination(destination):
    module._recover_interrupted_install_state(destination)
    if not recovery_only:
        owner = module._create_install_transaction(destination, "transaction")
        staging = owner.path / "install"
        staging.mkdir()
        (staging / "new").write_text("new\n", encoding="utf-8")
        try:
            module.replace_destination(staging, destination, owner)
        finally:
            module._cleanup_install_transaction(owner)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            phase,
            "recovery" if recovery_only else "install",
        ],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 89, result.stdout + result.stderr


def _owned_install_siblings(destination: Path) -> set[Path]:
    pattern = re.compile(
        rf"\.{re.escape(destination.name)}\.protocyte-"
        r"(?:transaction|recovery)-[0-9a-f]{32}"
    )
    return {
        path for path in destination.parent.iterdir() if pattern.fullmatch(path.name)
    }


@pytest.mark.parametrize(
    ("interrupted_phase", "expected_file"),
    [
        ("before_backup", "old"),
        ("after_backup", "old"),
        ("before_cleanup", "new"),
    ],
)
def test_install_recovery_cleans_owned_hard_exit_transactions_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupted_phase: str,
    expected_file: str,
) -> None:
    environment = _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old\n", encoding="utf-8")
    unowned = tmp_path / (".protoc.protocyte-transaction-" + "e" * 32)
    unowned.mkdir()
    (unowned / "keep").write_text("unowned\n", encoding="utf-8")

    _run_install_hard_exit(destination, interrupted_phase, environment)

    with install_protoc.locked_destination(destination):
        install_protoc._recover_interrupted_install_state(destination)

    assert {path.name for path in destination.iterdir()} == {expected_file}
    assert (unowned / "keep").read_text(encoding="utf-8") == "unowned\n"
    assert _owned_install_siblings(destination) == {unowned}
    assert not install_protoc._installation_rollback_path(destination).exists()


def test_install_recovery_survives_a_hard_exit_mid_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old\n", encoding="utf-8")
    rollback = _leave_owned_install_rollback(destination)
    destination.mkdir()
    (destination / "new").write_text("new\n", encoding="utf-8")

    _run_install_hard_exit(
        destination,
        "recovery_after_displace",
        environment,
        recovery_only=True,
    )

    with install_protoc.locked_destination(destination):
        install_protoc._recover_interrupted_install_state(destination)

    assert (destination / "old").read_text(encoding="utf-8") == "old\n"
    assert not (destination / "new").exists()
    assert not rollback.exists()
    assert not _owned_install_siblings(destination)


def test_unowned_install_rollback_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "live").write_text("live\n", encoding="utf-8")
    rollback = install_protoc._installation_rollback_path(destination)
    rollback.mkdir()
    (rollback / "unowned").write_text("unowned\n", encoding="utf-8")

    with install_protoc.locked_destination(destination):
        with pytest.raises(RuntimeError, match="unowned or replaced.*left unchanged"):
            install_protoc._recover_interrupted_install_state(destination)

    assert (destination / "live").read_text(encoding="utf-8") == "live\n"
    assert (rollback / "unowned").read_text(encoding="utf-8") == "unowned\n"


def _create_install_rollback_lookalike(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            pytest.skip("Windows junction creation is unavailable: " + result.stderr)
        return
    link.symlink_to(target, target_is_directory=True)


def test_replaced_install_rollback_lookalike_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old\n", encoding="utf-8")
    rollback = _leave_owned_install_rollback(destination)
    original_rollback = tmp_path / "owned-rollback"
    rollback.replace(original_rollback)
    lookalike_target = tmp_path / "lookalike-target"
    lookalike_target.mkdir()
    (lookalike_target / "keep").write_text("keep\n", encoding="utf-8")
    _create_install_rollback_lookalike(rollback, lookalike_target)
    destination.mkdir()
    (destination / "live").write_text("live\n", encoding="utf-8")

    try:
        with install_protoc.locked_destination(destination):
            with pytest.raises(
                RuntimeError, match="unowned or replaced.*left unchanged"
            ):
                install_protoc._recover_interrupted_install_state(destination)

        assert (destination / "live").read_text(encoding="utf-8") == "live\n"
        assert (lookalike_target / "keep").read_text(encoding="utf-8") == "keep\n"
        assert (original_rollback / "old").read_text(encoding="utf-8") == "old\n"
        assert rollback.exists()
    finally:
        if os.name == "nt" and rollback.exists():
            os.rmdir(rollback)


def test_resolve_release_requires_digest_for_version_override() -> None:
    asset = install_protoc.resolve_platform_asset("Linux", "x86_64")
    with pytest.raises(RuntimeError, match="--sha256 is required"):
        install_protoc.resolve_release("999.0", None, asset)


@pytest.mark.parametrize(
    ("system", "machine", "archive_suffix", "checksum_variable", "executable_name"),
    [
        (
            "Linux",
            "AMD64",
            "linux-x86_64",
            "PROTOCYTE_PROTOBUF_LINUX_X86_64_SHA256",
            "protoc",
        ),
        (
            "Windows",
            "x86_64",
            "win64",
            "PROTOCYTE_PROTOBUF_WINDOWS_X86_64_SHA256",
            "protoc.exe",
        ),
    ],
)
def test_resolve_platform_asset_selects_supported_x86_64_archive(
    system: str,
    machine: str,
    archive_suffix: str,
    checksum_variable: str,
    executable_name: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)

    assert asset == install_protoc.ProtocAsset(
        archive_suffix=archive_suffix,
        checksum_variable=checksum_variable,
        executable_name=executable_name,
    )


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Darwin", "arm64"),
        ("Linux", "aarch64"),
        ("Windows", "x86"),
    ],
)
def test_resolve_platform_asset_rejects_unsupported_host(
    system: str,
    machine: str,
) -> None:
    with pytest.raises(RuntimeError, match="unsupported protoc prebuilt platform"):
        install_protoc.resolve_platform_asset(system, machine)


@pytest.mark.parametrize(
    ("system", "machine", "expected_sha256"),
    [
        (
            "Linux",
            "x86_64",
            "af27ea66cd26938fe48587804ca7d4817457a08350021a1c6e23a27ccc8c6904",
        ),
        (
            "Windows",
            "AMD64",
            "6d7ebdc75e9c1f0026d4fb28f17ef1d0aae77d36744d83a9e052d79ba493724f",
        ),
    ],
)
def test_configured_release_digests_match_upstream_assets(
    system: str,
    machine: str,
    expected_sha256: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)
    version, sha256 = install_protoc.resolve_release(None, None, asset)

    assert version == "34.1"
    assert sha256 == expected_sha256


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Linux", "x86_64"),
        ("Windows", "AMD64"),
    ],
)
def test_main_installs_selected_platform_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    machine: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)
    destination = tmp_path / "protoc"
    github_output = tmp_path / "github-output"
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )
    monkeypatch.setattr(install_protoc, "resolve_platform_asset", lambda: asset)

    def fake_download(url: str, archive_path: Path) -> str:
        observed["url"] = url
        _write_archive(
            archive_path,
            [
                f"bin/{asset.executable_name}",
                "include/google/protobuf/descriptor.proto",
            ],
        )
        return install_protoc.load_default_sha256(asset)

    def fake_run(command: list[str], *, check: bool) -> None:
        observed["command"] = command
        observed["check"] = check

    monkeypatch.setattr(install_protoc, "download_archive", fake_download)
    monkeypatch.setattr(install_protoc.subprocess, "run", fake_run)
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    assert install_protoc.main() == 0

    archive_name = f"protoc-34.1-{asset.archive_suffix}.zip"
    assert observed["url"] == (
        "https://github.com/protocolbuffers/protobuf/releases/download/"
        f"v34.1/{archive_name}"
    )
    command = observed["command"]
    assert isinstance(command, list)
    assert Path(command[0]).name == asset.executable_name
    assert command[1:] == ["--version"]
    assert observed["check"] is True
    assert (destination / "bin" / asset.executable_name).is_file()
    assert (
        destination / "include" / "google" / "protobuf" / "descriptor.proto"
    ).is_file()
    assert (destination / install_protoc.VERSION_MARKER).read_text(
        encoding="utf-8"
    ) == "34.1\n"
    outputs = github_output.read_text(encoding="utf-8").splitlines()
    assert "version=34.1" in outputs
    assert f"root={destination.as_posix()}" in outputs
    assert (
        f"protoc={(destination / 'bin' / asset.executable_name).as_posix()}" in outputs
    )
    assert f"include={(destination / 'include').as_posix()}" in outputs


@pytest.mark.parametrize(
    "member",
    [
        "/tmp/protoc",
        r"C:\tmp\protoc.exe",
        r"\tmp\protoc.exe",
        "../protoc",
        "bin/../../protoc",
        r"bin\..\protoc.exe",
    ],
)
def test_extract_archive_safely_rejects_absolute_or_parent_traversal_members(
    tmp_path: Path,
    member: str,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, [member, "bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="unsafe"):
            install_protoc.extract_archive_safely(archive, destination)

    assert not destination.exists()


def test_extract_archive_safely_rejects_too_many_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc", "include/descriptor.proto"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="more than 1 members"):
            install_protoc.extract_archive_safely(archive, destination, max_members=1)

    assert not destination.exists()


def test_extract_archive_safely_rejects_oversized_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="member exceeds"):
            install_protoc.extract_archive_safely(
                archive, destination, max_member_bytes=6
            )

    assert not destination.exists()


def test_extract_archive_safely_rejects_oversized_uncompressed_total(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc", "include/descriptor.proto"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="uncompressed-size limit"):
            install_protoc.extract_archive_safely(
                archive, destination, max_uncompressed_bytes=13
            )

    assert not destination.exists()
