import importlib.util
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest


def _load_managed_environment_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteManagedEnvironment.py"
    )
    spec = importlib.util.spec_from_file_location(
        "protocyte_managed_environment",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


managed_environment = _load_managed_environment_module()
_FINGERPRINT = "managed-environment-test-fingerprint"


@pytest.fixture(autouse=True)
def _private_transaction_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        managed_environment.transactions._STATE_DIRECTORY_ENV,
        str(tmp_path / "transaction-state"),
    )


def _write_ready_environment(path: Path) -> None:
    path.mkdir(parents=True)
    (path / ".protocyte-ready").write_text(
        f"{_FINGERPRINT}\n",
        encoding="utf-8",
    )
    (path / "owned.txt").write_text("owned\n", encoding="utf-8")


def _new_transaction(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = managed_environment._new_transaction(destination, _FINGERPRINT)
    (transaction / "owned.txt").write_text("owned\n", encoding="utf-8")
    return transaction


def _prepare_replacement(destination: Path, transaction: Path) -> Path:
    staging = transaction / "staging"
    _write_ready_environment(staging)
    managed_environment._prepare_candidate(
        destination,
        transaction,
        _FINGERPRINT,
    )
    return staging


def _prepare_promoted_replacement(
    destination: Path,
    transaction: Path,
) -> None:
    _prepare_replacement(destination, transaction)
    managed_environment._promote(destination, transaction, _FINGERPRINT)


def _cleanup_action(destination: Path, transaction: Path) -> None:
    owner = managed_environment._claim_transaction(
        destination,
        transaction,
        _FINGERPRINT,
    )
    cleaned = False
    try:
        managed_environment._cleanup_owner(owner)
        cleaned = True
    finally:
        if not cleaned:
            owner.close(remove_marker=False)


def _phase_fixture(
    phase: str,
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Callable[[], None]]:
    destination = tmp_path / "environment"
    if phase in {
        "backup",
        "promote",
        "rollback_discard",
        "rollback_restore",
        "recovery_discard",
        "recovery_restore",
    }:
        _write_ready_environment(destination)
    transaction = _new_transaction(destination)

    if phase == "backup":
        return (
            destination,
            transaction,
            destination,
            transaction / "previous",
            lambda: managed_environment._backup(
                destination,
                transaction,
                _FINGERPRINT,
            ),
        )

    if phase in {
        "promote",
        "rollback_discard",
        "rollback_restore",
        "recovery_discard",
        "recovery_restore",
    }:
        managed_environment._backup(destination, transaction, _FINGERPRINT)

    if phase == "promote":
        staging = _prepare_replacement(destination, transaction)
        return (
            destination,
            transaction,
            staging,
            destination,
            lambda: managed_environment._promote(
                destination,
                transaction,
                _FINGERPRINT,
            ),
        )

    if phase in {
        "rollback_discard",
        "rollback_restore",
        "recovery_discard",
    }:
        _prepare_promoted_replacement(destination, transaction)

    if phase == "rollback_discard":
        return (
            destination,
            transaction,
            destination,
            transaction / "discarded",
            lambda: managed_environment._restore(
                destination,
                transaction,
                _FINGERPRINT,
            ),
        )
    if phase == "rollback_restore":
        return (
            destination,
            transaction,
            transaction / "previous",
            destination,
            lambda: managed_environment._restore(
                destination,
                transaction,
                _FINGERPRINT,
            ),
        )
    if phase == "recovery_discard":
        return (
            destination,
            transaction,
            destination,
            transaction / "discarded",
            lambda: managed_environment._recover(destination, _FINGERPRINT),
        )
    if phase == "recovery_restore":
        return (
            destination,
            transaction,
            transaction / "previous",
            destination,
            lambda: managed_environment._recover(destination, _FINGERPRINT),
        )
    if phase == "cleanup":
        return (
            destination,
            transaction,
            transaction,
            transaction.with_name(transaction.name + ".unused"),
            lambda: _cleanup_action(destination, transaction),
        )
    if phase == "recovery_cleanup":
        return (
            destination,
            transaction,
            transaction,
            transaction.with_name(transaction.name + ".unused"),
            lambda: managed_environment._recover(destination, _FINGERPRINT),
        )
    raise AssertionError(f"unknown mutation phase: {phase}")


@pytest.mark.parametrize(
    "phase",
    [
        "backup",
        "promote",
        "rollback_discard",
        "rollback_restore",
        "recovery_discard",
        "recovery_restore",
        "cleanup",
        "recovery_cleanup",
    ],
)
def test_managed_environment_mutations_block_or_taint_late_source_swaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    destination, transaction, source, target, action = _phase_fixture(
        phase,
        tmp_path,
    )
    preserved = source.with_name(f"{source.name}.preserved-{phase}")
    attempted = False
    blocked = False
    replacement_created = False

    def replace_source(observed_phase: str, observed_source: Path) -> None:
        nonlocal attempted, blocked, replacement_created
        if observed_phase != phase or attempted:
            return
        attempted = True
        assert observed_source == source
        try:
            source.replace(preserved)
        except OSError:
            blocked = True
            return
        source.mkdir()
        (source / "unowned.txt").write_text("unowned\n", encoding="utf-8")
        replacement_created = True

    monkeypatch.setattr(
        managed_environment,
        "_managed_environment_mutation_phase",
        replace_source,
    )

    error: BaseException | None = None
    try:
        action()
    except (OSError, RuntimeError) as caught:
        error = caught

    assert attempted
    if blocked:
        assert error is None
        assert not replacement_created
        assert not preserved.exists()
        return

    assert error is not None
    assert replacement_created
    assert (preserved / "owned.txt").read_text(encoding="utf-8") == "owned\n"
    replacement_sentinels = [source / "unowned.txt", target / "unowned.txt"]
    assert any(
        sentinel.is_file() and sentinel.read_text(encoding="utf-8") == "unowned\n"
        for sentinel in replacement_sentinels
    )
    assert transaction.exists() or preserved == transaction

    with pytest.raises(RuntimeError):
        managed_environment._recover(destination, _FINGERPRINT)


def test_managed_environment_promotion_never_replaces_a_late_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "environment"
    destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = _new_transaction(destination)
    staging = _prepare_replacement(destination, transaction)

    def occupy_target(phase: str, _source: Path) -> None:
        if phase != "promote":
            return
        destination.mkdir()
        (destination / "unowned.txt").write_text("unowned\n", encoding="utf-8")

    monkeypatch.setattr(
        managed_environment,
        "_managed_environment_mutation_phase",
        occupy_target,
    )

    with pytest.raises(OSError):
        managed_environment._promote(destination, transaction, _FINGERPRINT)

    assert (destination / "unowned.txt").read_text(encoding="utf-8") == "unowned\n"
    assert (staging / "owned.txt").read_text(encoding="utf-8") == "owned\n"


def test_managed_environment_backup_binds_the_ready_marker_to_its_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "environment"
    _write_ready_environment(destination)
    transaction = _new_transaction(destination)
    preserved = tmp_path / "preserved-environment"
    original_read = managed_environment._PinnedDirectory.read_regular_file
    raced = False

    def replace_after_marker_read(
        pinned,
        name: str,
        maximum_bytes: int,
    ) -> bytes:
        nonlocal raced
        content = original_read(pinned, name, maximum_bytes)
        if not raced and pinned.path == destination:
            raced = True
            destination.replace(preserved)
            _write_ready_environment(destination)
            (destination / "unowned.txt").write_text(
                "unowned\n",
                encoding="utf-8",
            )
        return content

    monkeypatch.setattr(
        managed_environment._PinnedDirectory,
        "read_regular_file",
        replace_after_marker_read,
    )

    with pytest.raises(RuntimeError, match="changed identity"):
        managed_environment._backup(destination, transaction, _FINGERPRINT)

    assert raced
    assert (preserved / "owned.txt").read_text(encoding="utf-8") == "owned\n"
    assert (destination / "unowned.txt").read_text(encoding="utf-8") == "unowned\n"
    with pytest.raises(RuntimeError):
        managed_environment._recover(destination, _FINGERPRINT)


def test_managed_environment_private_journal_binds_the_fingerprint(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "environment"
    destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = _new_transaction(destination)

    with pytest.raises(RuntimeError, match="another installation"):
        managed_environment._recover(destination, "different-fingerprint")

    assert transaction.is_dir()
    managed_environment._recover(destination, _FINGERPRINT)
    assert not transaction.exists()


def _crash_test_environment(state_directory: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment[managed_environment.transactions._STATE_DIRECTORY_ENV] = str(
        state_directory
    )
    return environment


def _only_transaction_journal(
    state_directory: Path,
    destination: Path,
) -> tuple[Path, dict[str, object], Path, Path]:
    marker_paths = list(state_directory.rglob("*.owner"))
    assert len(marker_paths) == 1
    marker_path = marker_paths[0]
    kind, token, suffix = marker_path.name.split(".")
    assert suffix == "owner"
    payload = managed_environment.transactions._read_latest_journal_payload(
        marker_path,
        destination,
        kind,
        token,
    )
    transaction = managed_environment.transactions._owned_sibling_path(
        destination,
        kind,
        token,
    )
    cleanup = managed_environment.transactions._owned_sibling_cleanup_path(
        destination,
        kind,
        token,
    )
    return marker_path, payload, transaction, cleanup


@pytest.mark.parametrize(
    ("interrupted_phase", "expected_location", "exit_code"),
    [
        ("after_detach", "detaching", 91),
        ("after_remove", "cleanup", 92),
    ],
)
def test_managed_environment_recovery_resumes_hard_exit_cleanup(
    tmp_path: Path,
    interrupted_phase: str,
    expected_location: str,
    exit_code: int,
) -> None:
    state_directory = tmp_path / "transaction-state"
    destination = tmp_path / "environment"
    script_path = Path(managed_environment.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
fingerprint = sys.argv[3]
interrupted_phase = sys.argv[4]
exit_code = int(sys.argv[5])
spec = importlib.util.spec_from_file_location("managed_cleanup_crash", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

destination.mkdir(parents=True)
(destination / ".protocyte-ready").write_text(fingerprint + "\n", encoding="utf-8")
(destination / "old.txt").write_text("old\n", encoding="utf-8")
transaction = module._new_transaction(destination, fingerprint)
module._backup(destination, transaction, fingerprint)
staging = transaction / "staging"
staging.mkdir()
(staging / ".protocyte-ready").write_text(fingerprint + "\n", encoding="utf-8")
(staging / "new.txt").write_text("new\n", encoding="utf-8")
module._prepare_candidate(destination, transaction, fingerprint)
module._promote(destination, transaction, fingerprint)
module._commit(destination, transaction, fingerprint)

def hard_exit(phase: str, _path: Path) -> None:
    if phase == interrupted_phase:
        os._exit(exit_code)

module.transactions._owned_sibling_cleanup_phase = hard_exit
owner = module._claim_transaction(destination, transaction, fingerprint)
module._cleanup_owner(owner)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            _FINGERPRINT,
            interrupted_phase,
            str(exit_code),
        ],
        cwd=script_path.parents[1],
        env=_crash_test_environment(state_directory),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == exit_code, result.stdout + result.stderr

    marker, payload, transaction, cleanup = _only_transaction_journal(
        state_directory,
        destination,
    )
    assert payload["sibling_location"] == expected_location
    assert not transaction.exists()
    assert cleanup.exists() is (interrupted_phase == "after_detach")
    assert (destination / "new.txt").read_text(encoding="utf-8") == "new\n"

    managed_environment._recover(destination, _FINGERPRINT)

    assert (destination / "new.txt").read_text(encoding="utf-8") == "new\n"
    assert not (destination / "old.txt").exists()
    assert not transaction.exists()
    assert not cleanup.exists()
    assert not marker.exists()


@pytest.mark.parametrize(
    "interrupted_phase",
    ["after_create", "during_bind", "after_bind"],
)
def test_managed_environment_recovery_resumes_hard_exit_fingerprint_binding(
    tmp_path: Path,
    interrupted_phase: str,
) -> None:
    state_directory = tmp_path / "transaction-state"
    destination = tmp_path / "environment"
    script_path = Path(managed_environment.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
fingerprint = sys.argv[3]
interrupted_phase = sys.argv[4]
spec = importlib.util.spec_from_file_location("fingerprint_binding_crash", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

destination.mkdir(parents=True)
(destination / "keep.txt").write_text("unowned\n", encoding="utf-8")
binding_started = False

def hard_exit(phase: str, _path: Path) -> None:
    global binding_started
    if phase == "after_create":
        binding_started = True
    if phase == interrupted_phase:
        os._exit(93)

def hard_exit_during_journal(phase: str, _path: Path) -> None:
    if (
        interrupted_phase == "during_bind"
        and binding_started
        and phase == "after_temporary_fsync"
    ):
        os._exit(93)

module._managed_environment_fingerprint_phase = hard_exit
module.transactions._owned_journal_phase = hard_exit_during_journal
module._new_transaction(destination, fingerprint)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            _FINGERPRINT,
            interrupted_phase,
        ],
        cwd=script_path.parents[1],
        env=_crash_test_environment(state_directory),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 93, result.stdout + result.stderr

    marker, payload, transaction, cleanup = _only_transaction_journal(
        state_directory,
        destination,
    )
    assert payload["sibling_location"] == "original"
    assert ("fingerprint" in payload["owned_paths"]) is (
        interrupted_phase == "after_bind"
    )
    assert transaction.is_dir()
    assert not cleanup.exists()

    managed_environment._recover(destination, _FINGERPRINT)

    assert (destination / "keep.txt").read_text(encoding="utf-8") == "unowned\n"
    assert not transaction.exists()
    assert not marker.exists()


def test_incomplete_fingerprint_recovery_refuses_a_replaced_transaction(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "transaction-state"
    destination = tmp_path / "environment"
    script_path = Path(managed_environment.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
fingerprint = sys.argv[3]
spec = importlib.util.spec_from_file_location("fingerprint_replacement_crash", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def hard_exit(phase: str, _path: Path) -> None:
    if phase == "after_create":
        os._exit(94)

module._managed_environment_fingerprint_phase = hard_exit
module._new_transaction(destination, fingerprint)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            _FINGERPRINT,
        ],
        cwd=script_path.parents[1],
        env=_crash_test_environment(state_directory),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 94, result.stdout + result.stderr
    marker, _payload, transaction, _cleanup = _only_transaction_journal(
        state_directory,
        destination,
    )
    preserved = transaction.with_name(transaction.name + ".preserved")
    transaction.replace(preserved)
    transaction.mkdir()
    replacement = transaction / "unowned.txt"
    replacement.write_text("unowned\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unowned, replaced, or linked"):
        managed_environment._recover(destination, _FINGERPRINT)

    assert replacement.read_text(encoding="utf-8") == "unowned\n"
    assert preserved.is_dir()
    assert marker.is_file()

    replacement.unlink()
    transaction.rmdir()
    preserved.replace(transaction)
    managed_environment._recover(destination, _FINGERPRINT)
    assert not marker.exists()


def test_managed_environment_recovery_never_cleans_a_tainted_transaction(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "environment"
    destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = _new_transaction(destination)
    owner = managed_environment._claim_transaction(
        destination,
        transaction,
        _FINGERPRINT,
    )
    try:
        managed_environment._mark_tainted(owner)
    finally:
        owner.close(remove_marker=False)

    with pytest.raises(RuntimeError, match="requires manual inspection"):
        managed_environment._recover(destination, _FINGERPRINT)

    assert transaction.is_dir()


def _create_junction(link: Path, target: Path) -> None:
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


def _remove_junction(link: Path) -> None:
    if link.is_junction():
        os.rmdir(link)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction validation")
def test_managed_environment_rejects_a_destination_ancestor_junction(
    tmp_path: Path,
) -> None:
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    keep = real_parent / "keep.txt"
    keep.write_text("unowned\n", encoding="utf-8")
    junction = tmp_path / "linked-parent"
    _create_junction(junction, real_parent)

    try:
        with pytest.raises(RuntimeError, match="link or junction|linked"):
            managed_environment._new_transaction(
                junction / "environment",
                _FINGERPRINT,
            )
        assert keep.read_text(encoding="utf-8") == "unowned\n"
    finally:
        _remove_junction(junction)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction validation")
def test_managed_environment_rejects_a_junction_destination(
    tmp_path: Path,
) -> None:
    target = tmp_path / "destination-target"
    _write_ready_environment(target)
    keep = target / "keep.txt"
    keep.write_text("unowned\n", encoding="utf-8")
    destination = tmp_path / "environment"
    _create_junction(destination, target)
    transaction = _new_transaction(destination)

    try:
        with pytest.raises(RuntimeError, match="link or junction|linked"):
            managed_environment._backup(destination, transaction, _FINGERPRINT)
        assert keep.read_text(encoding="utf-8") == "unowned\n"
        assert destination.is_junction()
    finally:
        _remove_junction(destination)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction validation")
def test_managed_environment_rejects_a_junction_staging_directory(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "environment"
    destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = _new_transaction(destination)
    target = tmp_path / "staging-target"
    _write_ready_environment(target)
    keep = target / "keep.txt"
    keep.write_text("unowned\n", encoding="utf-8")
    staging = transaction / "staging"
    _create_junction(staging, target)

    try:
        with pytest.raises(RuntimeError, match="link or junction|linked"):
            managed_environment._prepare_candidate(
                destination,
                transaction,
                _FINGERPRINT,
            )
        assert keep.read_text(encoding="utf-8") == "unowned\n"
        assert staging.is_junction()
    finally:
        _remove_junction(staging)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction validation")
def test_managed_environment_recovery_rejects_a_junction_backup(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "environment"
    _write_ready_environment(destination)
    transaction = _new_transaction(destination)
    managed_environment._backup(destination, transaction, _FINGERPRINT)
    previous = transaction / "previous"
    preserved = transaction / "preserved-previous"
    previous.replace(preserved)
    target = tmp_path / "backup-target"
    _write_ready_environment(target)
    keep = target / "keep.txt"
    keep.write_text("unowned\n", encoding="utf-8")
    _create_junction(previous, target)

    try:
        with pytest.raises(RuntimeError, match="link or junction|linked"):
            managed_environment._recover(destination, _FINGERPRINT)
        assert keep.read_text(encoding="utf-8") == "unowned\n"
        assert (preserved / "owned.txt").read_text(encoding="utf-8") == "owned\n"
        assert previous.is_junction()
    finally:
        _remove_junction(previous)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction validation")
def test_managed_environment_recovery_rejects_a_junction_transaction_root(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "environment"
    destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = _new_transaction(destination)
    preserved = transaction.with_name(transaction.name + ".preserved")
    transaction.replace(preserved)
    target = tmp_path / "transaction-target"
    target.mkdir()
    keep = target / "keep.txt"
    keep.write_text("unowned\n", encoding="utf-8")
    _create_junction(transaction, target)

    try:
        with pytest.raises(RuntimeError, match="link or junction|linked|replaced"):
            managed_environment._recover(destination, _FINGERPRINT)
        assert keep.read_text(encoding="utf-8") == "unowned\n"
        assert (preserved / "owned.txt").read_text(encoding="utf-8") == "owned\n"
        assert transaction.is_junction()
    finally:
        _remove_junction(transaction)
