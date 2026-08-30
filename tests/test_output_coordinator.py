from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_coordinator() -> ModuleType:
    script = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteOutputCoordinator.py"
    )
    specification = importlib.util.spec_from_file_location(
        "protocyte_output_coordinator", script
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


coordinator = _load_coordinator()


def _identity(path: Path) -> str:
    return coordinator._path_key(path)


def _write_plan(
    path: Path,
    root: Path,
    build: Path,
    outputs: tuple[tuple[str, str], ...],
) -> object:
    root.parent.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)
    lines = [
        coordinator.PLAN_HEADER,
        f"root-hex={os.fspath(root).encode().hex()}",
        f"build-root-hex={os.fspath(build).encode().hex()}",
    ]
    for target in sorted({target for target, _ in outputs}):
        staging = root.parent / f".protocyte-generation-staging-{target}"
        lines.append(f"target={target}|{os.fspath(staging).encode().hex()}")
    lines.extend(
        f"output={target}|{relative.encode().hex()}" for target, relative in outputs
    )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return coordinator.Plan.read(path)


def _target(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


def _staging(plan: object, target: str) -> Path:
    return plan.staging_for_target(target) / "generated"


def _stage(staging: Path, relative: str, content: bytes) -> None:
    output = staging / Path(relative)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)


def _snapshot(lock_root: Path, root: Path) -> dict[str, object]:
    path = lock_root / "roots" / _identity(root) / "snapshot.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_committed_invariants(lock_root: Path, root: Path) -> None:
    snapshot = _snapshot(lock_root, root)
    for relative, entry in snapshot["entries"].items():
        output = root / Path(relative)
        assert output.is_file()
        assert hashlib.sha256(output.read_bytes()).hexdigest() == entry["sha256"]
    transaction_root = lock_root / "roots" / _identity(root) / "transactions"
    pending = list(transaction_root.glob("*/pending.json"))
    assert len(pending) <= 1


def test_durable_directory_creation_resyncs_a_preexisting_retry_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "state" / "transactions" / "transaction"
    directory.mkdir(parents=True)
    synced: list[Path] = []
    original_sync = coordinator._sync_directory

    def record_sync(path: Path) -> None:
        synced.append(path)
        original_sync(path)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)

    coordinator._durable_mkdir(directory, anchor=tmp_path)

    assert synced == [
        tmp_path,
        tmp_path / "state",
        tmp_path / "state" / "transactions",
    ]


def test_publish_commits_one_authoritative_snapshot(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "api/demo.protocyte.hpp"), (target, "api/demo.protocyte.cpp")),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    claim = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "api/demo.protocyte.hpp", b"// header v1\n")
    _stage(staging, "api/demo.protocyte.cpp", b"// source v1\n")

    engine.publish(plan, target, staging)

    assert (root / "api/demo.protocyte.hpp").read_bytes() == b"// header v1\n"
    assert (root / "api/demo.protocyte.cpp").read_bytes() == b"// source v1\n"
    snapshot = _snapshot(lock_root, root)
    assert snapshot["generation"] == 1
    assert set(snapshot["entries"]) == {
        "api/demo.protocyte.cpp",
        "api/demo.protocyte.hpp",
    }
    claim_record = json.loads(
        (lock_root / "roots" / _identity(root) / "claim.json").read_text(
            encoding="utf-8"
        )
    )
    assert claim_record["token"] == claim


def test_claim_parent_chain_is_synced_before_claim_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    events: list[tuple[str, Path]] = []
    original_sync = coordinator._sync_directory
    original_atomic_write = coordinator._atomic_write

    def record_sync(path: Path) -> None:
        events.append(("sync", path))
        original_sync(path)

    def record_atomic_write(path: Path, content: bytes) -> None:
        if path.name == "claim.json":
            events.append(("claim", path))
        original_atomic_write(path, content)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)
    monkeypatch.setattr(coordinator, "_atomic_write", record_atomic_write)

    coordinator.OutputCoordinator(lock_root).reconcile(plan)

    claim_index = next(index for index, event in enumerate(events) if event[0] == "claim")
    synced_before_claim = {
        path for event, path in events[:claim_index] if event == "sync"
    }
    assert lock_root in synced_before_claim
    assert lock_root / "roots" in synced_before_claim


def test_payload_tree_is_synced_before_pending_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    events: list[tuple[str, Path]] = []
    original_sync = coordinator._sync_directory
    original_atomic_write = coordinator._atomic_write

    def record_sync(path: Path) -> None:
        events.append(("sync", path))
        original_sync(path)

    def record_atomic_write(path: Path, content: bytes) -> None:
        if path.name == "pending.json":
            events.append(("pending", path))
        original_atomic_write(path, content)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)
    monkeypatch.setattr(coordinator, "_atomic_write", record_atomic_write)

    engine.publish(plan, target, staging)

    pending_index = next(
        index for index, event in enumerate(events) if event[0] == "pending"
    )
    synced_before_pending = {
        path for event, path in events[:pending_index] if event == "sync"
    }
    state = engine._state_directory(root)
    assert any(path.name == "payloads" for path in synced_before_pending)
    assert state / "transactions" in synced_before_pending
    assert state in synced_before_pending


def test_new_output_ancestor_chain_is_synced_before_snapshot_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "api/v1/demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "api/v1/demo.protocyte.hpp", b"// generated\n")
    events: list[tuple[str, Path]] = []
    original_sync = coordinator._sync_directory
    original_atomic_write = coordinator._atomic_write

    def record_sync(path: Path) -> None:
        events.append(("sync", path))
        original_sync(path)

    def record_atomic_write(path: Path, content: bytes) -> None:
        if path.name == "snapshot.json":
            events.append(("snapshot", path))
        original_atomic_write(path, content)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)
    monkeypatch.setattr(coordinator, "_atomic_write", record_atomic_write)

    engine.publish(plan, target, staging)

    snapshot_index = next(
        index for index, event in enumerate(events) if event[0] == "snapshot"
    )
    synced_before_snapshot = {
        path for event, path in events[:snapshot_index] if event == "sync"
    }
    assert root.parent in synced_before_snapshot
    assert root in synced_before_snapshot
    assert root / "api" in synced_before_snapshot
    assert root / "api" / "v1" in synced_before_snapshot


def test_retry_resyncs_an_already_replaced_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    destination = root / "api" / "v1" / "demo.protocyte.hpp"
    destination.parent.mkdir(parents=True)
    content = b"// generated\n"
    destination.write_bytes(content)
    synced: list[Path] = []
    original_sync = coordinator._sync_directory

    def record_sync(path: Path) -> None:
        synced.append(path)
        original_sync(path)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)

    coordinator.OutputCoordinator._publish_one(
        root,
        destination,
        tmp_path / "unused-payload",
        None,
        hashlib.sha256(content).hexdigest(),
        "0" * 64,
        0,
    )

    assert root.parent in synced
    assert root in synced
    assert root / "api" in synced
    assert root / "api" / "v1" in synced


@pytest.mark.parametrize("crash_phase", ("after-initial-snapshot", "after-claim"))
def test_initial_claim_crash_cuts_are_retryable(
    tmp_path: Path, crash_phase: str
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = crash_phase
    crashed = subprocess.run(
        [
            sys.executable,
            str(coordinator.__file__),
            "reconcile",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan_path),
        ],
        check=False,
        env=environment,
    )
    assert crashed.returncode == 86

    claim = coordinator.OutputCoordinator(lock_root).reconcile(plan)

    assert len(claim) == 64
    _assert_committed_invariants(lock_root, root)


@pytest.mark.parametrize(
    "crash_phase",
    ("after-pending", "after-output-1", "after-output-2", "after-snapshot"),
)
def test_every_publication_crash_cut_rolls_forward_from_durable_payloads(
    tmp_path: Path, crash_phase: str
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.cpp"), (target, "demo.protocyte.hpp")),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    first_staging = _staging(plan, target)
    _stage(first_staging, "demo.protocyte.cpp", b"// source v1\n")
    _stage(first_staging, "demo.protocyte.hpp", b"// header v1\n")
    engine.publish(plan, target, first_staging)
    second_staging = _staging(plan, target)
    _stage(second_staging, "demo.protocyte.cpp", b"// source v2\n")
    _stage(second_staging, "demo.protocyte.hpp", b"// header v2\n")
    script = Path(coordinator.__file__)
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = crash_phase

    crashed = subprocess.run(
        [
            sys.executable,
            str(script),
            "publish",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan_path),
            "--target",
            target,
            "--staging-root",
            str(second_staging),
        ],
        check=False,
        env=environment,
    )
    assert crashed.returncode == 86
    expected_interrupted_generation = 2 if crash_phase == "after-snapshot" else 1
    assert _snapshot(lock_root, root)["generation"] == expected_interrupted_generation

    # Recovery does not use the original build-tree staging directory.
    for output in second_staging.rglob("*"):
        if output.is_file():
            output.unlink()
    engine.reconcile(plan)

    assert (root / "demo.protocyte.cpp").read_bytes() == b"// source v2\n"
    assert (root / "demo.protocyte.hpp").read_bytes() == b"// header v2\n"
    assert _snapshot(lock_root, root)["generation"] == 2
    transaction_root = lock_root / "roots" / _identity(root) / "transactions"
    assert not list(transaction_root.iterdir())
    _assert_committed_invariants(lock_root, root)


def test_recovery_rejects_a_semantically_modified_replacement_snapshot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path, root, build, ((target, "demo.protocyte.hpp"),)
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = "after-pending"
    crashed = subprocess.run(
        [
            sys.executable,
            str(coordinator.__file__),
            "publish",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan_path),
            "--target",
            target,
            "--staging-root",
            str(staging),
        ],
        check=False,
        env=environment,
    )
    assert crashed.returncode == 86
    pending_path = next(
        engine._state_directory(root).glob("transactions/*/pending.json")
    )
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    pending["new_snapshot"]["entries"] = {}
    pending_path.write_bytes(coordinator._canonical_json(pending))

    with pytest.raises(coordinator.CoordinatorError, match="does not match"):
        engine.reconcile(plan)

    assert not (root / "demo.protocyte.hpp").exists()


def test_reconcile_retires_only_snapshot_authenticated_outputs(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    empty_plan = _write_plan(plan_path, root, build, ())

    engine.reconcile(empty_plan)

    assert not (root / "demo.protocyte.hpp").exists()
    assert _snapshot(lock_root, root)["entries"] == {}


def test_reconcile_durably_retires_removed_target_staging_before_plan_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path, root, build, ((target, "demo.protocyte.hpp"),)
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = first.staging_for_target(target)
    _stage(staging / "generated", "demo.protocyte.hpp", b"// interrupted\n")
    second = _write_plan(plan_path, root, build, ())
    state = engine._state_directory(root)
    events: list[tuple[str, Path]] = []
    original_rmtree = coordinator.shutil.rmtree
    original_atomic_write = coordinator._atomic_write

    def record_rmtree(path: Path, *args: object, **kwargs: object) -> None:
        events.append(("rmtree", Path(path)))
        original_rmtree(path, *args, **kwargs)

    def record_atomic_write(path: Path, content: bytes) -> None:
        if path == state / "plan.json":
            events.append(("plan", path))
        original_atomic_write(path, content)

    monkeypatch.setattr(coordinator.shutil, "rmtree", record_rmtree)
    monkeypatch.setattr(coordinator, "_atomic_write", record_atomic_write)

    engine.reconcile(second)

    assert not staging.exists()
    assert events.index(("rmtree", staging)) < events.index(
        ("plan", state / "plan.json")
    )


def test_reconcile_resyncs_absent_retired_staging_before_plan_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path, root, build, ((target, "demo.protocyte.hpp"),)
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    second = _write_plan(plan_path, root, build, ())
    state = engine._state_directory(root)
    events: list[tuple[str, Path]] = []
    original_sync = coordinator._sync_directory
    original_atomic_write = coordinator._atomic_write

    def record_sync(path: Path) -> None:
        events.append(("sync", path))
        original_sync(path)

    def record_atomic_write(path: Path, content: bytes) -> None:
        if path == state / "plan.json":
            events.append(("plan", path))
        original_atomic_write(path, content)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)
    monkeypatch.setattr(coordinator, "_atomic_write", record_atomic_write)

    engine.reconcile(second)

    plan_index = events.index(("plan", state / "plan.json"))
    assert ("sync", root.parent) in events[:plan_index]


def test_reconcile_preserves_modified_retired_output_and_snapshot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    output = root / "demo.protocyte.hpp"
    output.write_bytes(b"// user modification\n")
    empty_plan = _write_plan(plan_path, root, build, ())

    engine.reconcile(empty_plan)

    assert output.read_bytes() == b"// user modification\n"
    assert set(_snapshot(lock_root, root)["entries"]) == {"demo.protocyte.hpp"}


def test_same_build_path_recovers_after_complete_build_tree_deletion(
    tmp_path: Path,
) -> None:
    root = tmp_path / "build/generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// first\n")
    engine.publish(plan, target, staging)
    import shutil

    shutil.rmtree(build)
    build.mkdir()
    recreated = _write_plan(plan_path, root, build, ((target, "demo.protocyte.hpp"),))
    replacement = _staging(recreated, target)
    _stage(replacement, "demo.protocyte.hpp", b"// regenerated\n")

    engine.reconcile(recreated)
    engine.publish(recreated, target, replacement)

    assert (root / "demo.protocyte.hpp").read_bytes() == b"// regenerated\n"


def test_different_build_cannot_adopt_claim(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    first = _write_plan(
        tmp_path / "first-plan",
        root,
        tmp_path / "first-build",
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    second = _write_plan(
        tmp_path / "second-plan",
        root,
        tmp_path / "second-build",
        ((target, "demo.protocyte.hpp"),),
    )

    with pytest.raises(coordinator.CoordinatorError, match="different CMake build"):
        engine.reconcile(second)


def test_overlapping_output_roots_are_rejected(tmp_path: Path) -> None:
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    parent = _write_plan(
        tmp_path / "parent-plan",
        tmp_path / "generated",
        tmp_path / "parent-build",
        ((target, "demo.protocyte.hpp"),),
    )
    nested = _write_plan(
        tmp_path / "nested-plan",
        tmp_path / "generated/nested",
        tmp_path / "nested-build",
        ((target, "nested.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(parent)

    with pytest.raises(coordinator.CoordinatorError, match="overlaps a root"):
        engine.reconcile(nested)


def test_link_inserted_below_output_root_cannot_redirect_publication(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "api/demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "api").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"directory links are unavailable: {error}")
        junction = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(root / "api"), str(outside)],
            check=False,
            capture_output=True,
            text=True,
        )
        if junction.returncode != 0:
            pytest.skip(f"directory links are unavailable: {junction.stderr}")
    staging = _staging(plan, target)
    _stage(staging, "api/demo.protocyte.hpp", b"// generated\n")

    with pytest.raises(coordinator.CoordinatorError, match="symbolic link or junction"):
        engine.publish(plan, target, staging)

    assert not (outside / "demo.protocyte.hpp").exists()


def test_replaced_nested_lock_directory_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    publication = lock_root / "publication"
    redirected = tmp_path / "redirected-publication"
    publication.rename(redirected)
    try:
        publication.symlink_to(redirected, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"directory links are unavailable: {error}")
        junction = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(publication), str(redirected)],
            check=False,
            capture_output=True,
            text=True,
        )
        if junction.returncode != 0:
            pytest.skip(f"directory links are unavailable: {junction.stderr}")

    with pytest.raises(coordinator.CoordinatorError, match="symbolic link or junction"):
        engine.validate(plan)


def test_hard_link_is_transferred_as_a_distinct_snapshot_entry(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    old_target = _target("old")
    new_target = _target("new")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path,
        root,
        build,
        ((old_target, "old.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = _staging(first, old_target)
    _stage(staging, "old.protocyte.hpp", b"// first\n")
    engine.publish(first, old_target, staging)
    old_output = root / "old.protocyte.hpp"
    new_output = root / "new.protocyte.hpp"
    os.link(old_output, new_output)
    second = _write_plan(
        plan_path,
        root,
        build,
        ((new_target, "new.protocyte.hpp"),),
    )

    engine.reconcile(second)

    assert not old_output.exists()
    assert new_output.read_bytes() == b"// first\n"
    snapshot = _snapshot(lock_root, root)
    assert set(snapshot["entries"]) == {"new.protocyte.hpp"}
    assert snapshot["entries"]["new.protocyte.hpp"]["target"] == new_target
    replacement = _staging(second, new_target)
    _stage(replacement, "new.protocyte.hpp", b"// second\n")
    engine.publish(second, new_target, replacement)
    assert new_output.read_bytes() == b"// second\n"


@pytest.mark.parametrize(
    ("replacement_mode", "failure"),
    (
        ("replace", "ownership transfer destination changed physical identity"),
        ("rewrite", "generated output bytes are not owned"),
    ),
)
def test_hard_link_transfer_revalidates_destination_before_retirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_mode: str,
    failure: str,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(plan_path, root, build, ((target, "old.protocyte.hpp"),))
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = _staging(first, target)
    _stage(staging, "old.protocyte.hpp", b"// generated\n")
    engine.publish(first, target, staging)
    old_output = root / "old.protocyte.hpp"
    new_output = root / "new.protocyte.hpp"
    os.link(old_output, new_output)
    second = _write_plan(plan_path, root, build, ((target, "new.protocyte.hpp"),))
    original_atomic_write = coordinator._atomic_write
    replaced = False

    def replace_destination_before_pending(path: Path, payload: bytes) -> None:
        nonlocal replaced
        if path.name == "pending.json" and not replaced:
            replaced = True
            if replacement_mode == "replace":
                new_output.unlink()
            new_output.write_bytes(b"// external replacement\n")
        original_atomic_write(path, payload)

    monkeypatch.setattr(
        coordinator, "_atomic_write", replace_destination_before_pending
    )

    with pytest.raises(coordinator.CoordinatorError, match=failure):
        engine.reconcile(second)

    expected_old = (
        b"// generated\n"
        if replacement_mode == "replace"
        else b"// external replacement\n"
    )
    assert old_output.read_bytes() == expected_old
    assert new_output.read_bytes() == b"// external replacement\n"
    assert set(_snapshot(lock_root, root)["entries"]) == {"old.protocyte.hpp"}


def test_multiple_retired_hard_links_transfer_ownership_once(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path,
        root,
        build,
        (
            (target, "old-a.protocyte.hpp"),
            (target, "old-b.protocyte.hpp"),
        ),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = _staging(first, target)
    _stage(staging, "old-a.protocyte.hpp", b"// generated\n")
    _stage(staging, "old-b.protocyte.hpp", b"// generated\n")
    engine.publish(first, target, staging)
    old_a = root / "old-a.protocyte.hpp"
    old_b = root / "old-b.protocyte.hpp"
    new_output = root / "new.protocyte.hpp"
    old_b.unlink()
    os.link(old_a, old_b)
    os.link(old_a, new_output)
    second = _write_plan(plan_path, root, build, ((target, "new.protocyte.hpp"),))

    engine.reconcile(second)

    assert not old_a.exists()
    assert not old_b.exists()
    assert new_output.read_bytes() == b"// generated\n"
    assert set(_snapshot(lock_root, root)["entries"]) == {"new.protocyte.hpp"}


def test_retirement_does_not_transfer_into_an_already_owned_hard_link(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path,
        root,
        build,
        ((target, "kept.protocyte.hpp"), (target, "old.protocyte.hpp")),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = _staging(first, target)
    _stage(staging, "kept.protocyte.hpp", b"// same\n")
    _stage(staging, "old.protocyte.hpp", b"// same\n")
    engine.publish(first, target, staging)
    kept = root / "kept.protocyte.hpp"
    old = root / "old.protocyte.hpp"
    kept.unlink()
    os.link(old, kept)
    second = _write_plan(
        plan_path, root, build, ((target, "kept.protocyte.hpp"),)
    )

    engine.reconcile(second)

    assert kept.read_bytes() == b"// same\n"
    assert not old.exists()
    assert set(_snapshot(lock_root, root)["entries"]) == {"kept.protocyte.hpp"}


def test_case_distinct_modified_retirement_does_not_block_publication(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    root.mkdir()
    upper = root / "Foo.protocyte.hpp"
    lower = root / "foo.protocyte.hpp"
    upper.write_bytes(b"probe\n")
    if lower.exists():
        pytest.skip("filesystem does not support case-distinct output paths")
    upper.unlink()
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path, root, build, ((target, "Foo.protocyte.hpp"),)
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = _staging(first, target)
    _stage(staging, "Foo.protocyte.hpp", b"// generated\n")
    engine.publish(first, target, staging)
    upper.write_bytes(b"// modified\n")
    second = _write_plan(
        plan_path, root, build, ((target, "foo.protocyte.hpp"),)
    )
    engine.reconcile(second)
    replacement = _staging(second, target)
    _stage(replacement, "foo.protocyte.hpp", b"// replacement\n")

    engine.publish(second, target, replacement)

    assert upper.read_bytes() == b"// modified\n"
    assert lower.read_bytes() == b"// replacement\n"
    assert set(_snapshot(lock_root, root)["entries"]) == {
        "Foo.protocyte.hpp",
        "foo.protocyte.hpp",
    }
    upper.write_bytes(b"// generated\n")
    retired = _write_plan(plan_path, root, build, ())

    engine.reconcile(retired)

    assert not upper.exists()
    assert not lower.exists()
    assert _snapshot(lock_root, root)["entries"] == {}


def test_retirement_indexes_desired_files_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    output_count = 40
    first = _write_plan(
        plan_path,
        root,
        build,
        tuple((target, f"old-{index}.protocyte.hpp") for index in range(output_count)),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging = _staging(first, target)
    for index in range(output_count):
        _stage(staging, f"old-{index}.protocyte.hpp", f"// {index}\n".encode())
    engine.publish(first, target, staging)
    second = _write_plan(
        plan_path,
        root,
        build,
        tuple((target, f"new-{index}.protocyte.hpp") for index in range(output_count)),
    )
    identity_calls = 0
    original_identity = coordinator._existing_file_identity

    def count_identity(path: Path) -> tuple[int, int] | None:
        nonlocal identity_calls
        identity_calls += 1
        return original_identity(path)

    monkeypatch.setattr(coordinator, "_existing_file_identity", count_identity)

    engine.reconcile(second)

    assert identity_calls == output_count * 2


@pytest.mark.skipif(os.name == "nt", reason="PosixPath equality is case-sensitive")
def test_claim_accepts_a_case_only_alias_on_a_case_insensitive_filesystem(
    tmp_path: Path,
) -> None:
    upper_root = tmp_path / "Generated"
    upper_root.mkdir()
    lower_root = tmp_path / "generated"
    if not lower_root.exists():
        pytest.skip("filesystem is case-sensitive")
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path,
        upper_root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(first)
    second = _write_plan(
        plan_path,
        lower_root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )

    assert engine.reconcile(second) == token


def test_staging_cannot_contain_the_coordinator_lock_root(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    lock_root = plan.staging_for_target(target) / "locks-v1"
    engine = coordinator.OutputCoordinator(lock_root)

    with pytest.raises(coordinator.CoordinatorError, match="staging contains"):
        engine.reconcile(plan)


def test_output_root_cannot_contain_its_derived_staging_directory(
    tmp_path: Path,
) -> None:
    filesystem_root = Path(tmp_path.anchor)
    target = _target("demo")

    with pytest.raises(coordinator.CoordinatorError, match="overlaps its own"):
        _write_plan(
            tmp_path / "plan",
            filesystem_root,
            tmp_path / "build",
            ((target, "demo.protocyte.hpp"),),
        )


def test_output_root_cannot_overlap_the_coordinator_registry(tmp_path: Path) -> None:
    lock_root = tmp_path / "locks-v1"
    root = lock_root / "roots" / "generated"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        tmp_path / "build",
        ((target, "demo.protocyte.hpp"),),
    )

    with pytest.raises(coordinator.CoordinatorError, match="lock namespace"):
        coordinator.OutputCoordinator(lock_root).reconcile(plan)


def test_retired_plan_ignores_a_case_distinct_physical_build_owner(
    tmp_path: Path,
) -> None:
    upper_build = tmp_path / "Build"
    lower_build = tmp_path / "build"
    upper_build.mkdir()
    if lower_build.exists():
        pytest.skip("filesystem does not support case-distinct build paths")
    lower_build.mkdir()
    root = tmp_path / "generated"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    old_plan_path = tmp_path / "old-plan"
    old_plan = _write_plan(
        old_plan_path,
        root,
        upper_build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(old_plan)
    engine.reset(old_plan, token)
    adopted = _write_plan(
        tmp_path / "adopted-plan",
        root,
        lower_build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine.reconcile(adopted)
    retired = _write_plan(old_plan_path, root, upper_build, ())

    results = engine.reconcile_set((retired,), ())

    assert results == [None]


def test_run_generation_locks_the_requested_root_before_reading_the_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    events: list[str] = []
    original_lock = coordinator.FileLock
    original_read = coordinator.Plan.read

    class RecordingLock(original_lock):
        def __enter__(self) -> object:
            events.append("lock")
            return super().__enter__()

    def recording_read(path: Path) -> object:
        events.append("read")
        return original_read(path)

    monkeypatch.setattr(coordinator, "FileLock", RecordingLock)
    monkeypatch.setattr(coordinator.Plan, "read", recording_read)

    result = coordinator.main(
        [
            "run-generation",
            "--lock-root",
            str(lock_root),
            "--output-root",
            str(root),
            "--plan",
            str(plan_path),
            "--exec",
            sys.executable,
            "-c",
            "pass",
        ]
    )

    assert result == 0
    assert events == ["lock", "read"]


def test_tampered_durable_payload_fails_closed_without_publication(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path,
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = "after-pending"
    crashed = subprocess.run(
        [
            sys.executable,
            str(coordinator.__file__),
            "publish",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan_path),
            "--target",
            target,
            "--staging-root",
            str(staging),
        ],
        check=False,
        env=environment,
    )
    assert crashed.returncode == 86
    payload = next(
        (lock_root / "roots" / _identity(root) / "transactions").glob(
            "*/payloads/*.payload"
        )
    )
    payload.write_bytes(b"tampered\n")

    with pytest.raises(coordinator.CoordinatorError, match="missing or changed"):
        engine.reconcile(plan)

    assert not (root / "demo.protocyte.hpp").exists()


def test_two_builds_racing_for_one_root_have_exactly_one_winner(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plans = [
        tmp_path / "first-plan",
        tmp_path / "second-plan",
    ]
    _write_plan(
        plans[0], root, tmp_path / "first-build", ((target, "demo.protocyte.hpp"),)
    )
    _write_plan(
        plans[1], root, tmp_path / "second-build", ((target, "demo.protocyte.hpp"),)
    )
    commands = [
        [
            sys.executable,
            str(coordinator.__file__),
            "reconcile",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan),
        ]
        for plan in plans
    ]
    processes = [
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for command in commands
    ]
    results = [process.communicate(timeout=30) for process in processes]

    assert sorted(process.returncode for process in processes) == [0, 1]
    loser = processes.index(
        next(process for process in processes if process.returncode)
    )
    assert b"different CMake build tree" in results[loser][1]
    claims = list((lock_root / "roots").glob("*/claim.json"))
    assert len(claims) == 1


@pytest.mark.skipif(os.name == "nt", reason="requires case-sensitive paths")
def test_case_distinct_build_roots_cannot_share_a_claim(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    first = _write_plan(
        tmp_path / "first-plan",
        root,
        tmp_path / "Build",
        ((target, "demo.protocyte.hpp"),),
    )
    second = _write_plan(
        tmp_path / "second-plan",
        root,
        tmp_path / "build",
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)

    with pytest.raises(coordinator.CoordinatorError, match="different CMake build tree"):
        engine.reconcile(second)


def test_registry_enumeration_fails_closed_when_claim_state_is_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_root = tmp_path / "first-output"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    first = _write_plan(
        tmp_path / "first-plan",
        first_root,
        tmp_path / "first-build",
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    unreadable = engine._state_directory(first_root)
    second = _write_plan(
        tmp_path / "second-plan",
        tmp_path / "second-output",
        tmp_path / "second-build",
        ((target, "demo.protocyte.hpp"),),
    )
    original_scandir = coordinator.os.scandir

    def reject_state(path: Path) -> object:
        if Path(path) == unreadable:
            raise PermissionError("denied by test")
        return original_scandir(path)

    monkeypatch.setattr(coordinator.os, "scandir", reject_state)

    with pytest.raises(coordinator.CoordinatorError, match="could not enumerate output claim"):
        engine.reconcile(second)


def test_output_claim_cannot_overlap_reserved_generation_staging(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    first = _write_plan(
        tmp_path / "first-plan",
        root,
        tmp_path / "first-build",
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(first)
    staging_root = first.staging_for_target(target)
    second = _write_plan(
        tmp_path / "second-plan",
        staging_root,
        tmp_path / "second-build",
        ((_target("second"), "second.protocyte.hpp"),),
    )

    with pytest.raises(coordinator.CoordinatorError, match="overlaps staging reserved"):
        engine.reconcile(second)


def test_reset_releases_claim(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)

    engine.reset(plan, token)

    assert not (root / "demo.protocyte.hpp").exists()
    assert not staging.parent.exists()
    assert not (lock_root / "roots" / _identity(root)).exists()


@pytest.mark.parametrize(
    "crash_phase",
    ("after-reset-intent", "after-reset-output-1", "after-reset-disposable"),
)
def test_reset_crash_cuts_resume_from_durable_intent(
    tmp_path: Path, crash_phase: str
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    plan_path = tmp_path / "plan"
    target = _target("demo")
    plan = _write_plan(
        plan_path, root, build, ((target, "demo.protocyte.hpp"),)
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = crash_phase
    crashed = subprocess.run(
        [
            sys.executable,
            str(coordinator.__file__),
            "reset",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan_path),
            "--expected-claim",
            token,
        ],
        check=False,
        env=environment,
    )
    assert crashed.returncode == 86
    state = engine._state_directory(root)
    assert (state / "claim.json").exists()
    assert (state / "reset.json").exists()

    engine.reset(plan, token)

    assert not (root / "demo.protocyte.hpp").exists()
    assert not state.exists()


def test_reset_crash_after_claim_release_allows_a_replacement_owner(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    plan = _write_plan(
        plan_path,
        root,
        tmp_path / "build",
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = "after-reset-claim"
    crashed = subprocess.run(
        [
            sys.executable,
            str(coordinator.__file__),
            "reset",
            "--lock-root",
            str(lock_root),
            "--plan",
            str(plan_path),
            "--expected-claim",
            token,
        ],
        check=False,
        env=environment,
    )
    assert crashed.returncode == 86
    state = engine._state_directory(root)
    assert not (state / "claim.json").exists()
    replacement = _write_plan(
        tmp_path / "replacement-plan",
        root,
        tmp_path / "replacement-build",
        ((target, "demo.protocyte.hpp"),),
    )

    replacement_token = engine.reconcile(replacement)

    assert len(replacement_token) == 64


def test_reset_rejects_an_unowned_generated_looking_directory(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    blocked = root / "blocked.protocyte.hpp"
    blocked.mkdir()

    with pytest.raises(coordinator.CoordinatorError, match="unowned generated-looking"):
        engine.reset(plan, token)

    assert blocked.is_dir()
    assert engine._state_directory(root).exists()


def test_reset_fails_closed_when_output_traversal_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan", root, build, ((target, "demo.protocyte.hpp"),)
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    unreadable = root / "private"
    unreadable.mkdir()
    _stage(unreadable, "unknown.protocyte.hpp", b"// unknown\n")
    original_scandir = coordinator.os.scandir

    def reject_directory(path: Path) -> object:
        if Path(path) == unreadable:
            raise PermissionError("denied by test")
        return original_scandir(path)

    monkeypatch.setattr(coordinator.os, "scandir", reject_directory)

    with pytest.raises(coordinator.CoordinatorError, match="could not enumerate directory"):
        engine.reset(plan, token)

    assert (root / "demo.protocyte.hpp").exists()
    assert engine._state_directory(root).exists()


def test_reset_allows_a_generated_looking_authenticated_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    relative = "namespace.protocyte.hpp/demo.protocyte.hpp"
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, relative),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, relative, b"// generated\n")
    engine.publish(plan, target, staging)

    engine.reset(plan, token)

    assert not (root / relative).exists()
    assert not engine._state_directory(root).exists()


def test_reset_persists_output_removal_before_claim_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "api/demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "api/demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    state = engine._state_directory(root)
    events: list[tuple[str, Path]] = []
    original_sync = coordinator._sync_directory

    def record_sync(path: Path) -> None:
        events.append(("sync", path))
        original_sync(path)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)

    engine.reset(plan, token)

    release_index = max(
        index for index, event in enumerate(events) if event == ("sync", state.parent)
    )
    assert ("sync", root / "api") in events[:release_index]


def test_reset_resyncs_an_already_absent_output_before_claim_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    output = root / "demo.protocyte.hpp"
    output.unlink()
    state = engine._state_directory(root)
    events: list[tuple[str, Path]] = []
    original_sync = coordinator._sync_directory

    def record_sync(path: Path) -> None:
        events.append(("sync", path))
        original_sync(path)

    monkeypatch.setattr(coordinator, "_sync_directory", record_sync)

    engine.reset(plan, token)

    release_index = max(
        index for index, event in enumerate(events) if event == ("sync", state.parent)
    )
    assert ("sync", root) in events[:release_index]


def test_reset_matches_snapshot_entries_by_case_insensitive_filesystem_identity(
    tmp_path: Path,
) -> None:
    case_probe = tmp_path / "case-probe"
    case_probe.mkdir()
    if not (tmp_path / "CASE-PROBE").exists():
        pytest.skip("requires a case-insensitive filesystem")
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan_path = tmp_path / "plan"
    first = _write_plan(
        plan_path,
        root,
        build,
        ((target, "API/foo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(first)
    first_staging = _staging(first, target)
    _stage(first_staging, "API/foo.protocyte.hpp", b"// first\n")
    engine.publish(first, target, first_staging)
    second = _write_plan(
        plan_path,
        root,
        build,
        ((target, "api/foo.protocyte.hpp"),),
    )
    engine.reconcile(second)
    second_staging = _staging(second, target)
    _stage(second_staging, "api/foo.protocyte.hpp", b"// second\n")
    engine.publish(second, target, second_staging)

    engine.reset(second, token)

    assert not (root / "API/foo.protocyte.hpp").exists()
    assert not engine._state_directory(root).exists()


def test_reset_can_load_durable_plan_after_build_tree_deletion(tmp_path: Path) -> None:
    root = tmp_path / "build/generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    staging = _staging(plan, target)
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    import shutil

    shutil.rmtree(build)

    durable_plan = engine.plan_for_root(root)
    engine.reset(durable_plan, token)

    assert not (lock_root / "roots" / _identity(root)).exists()


def test_reset_rejects_an_unowned_generated_symlink(tmp_path: Path) -> None:
    root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    token = engine.reconcile(plan)
    outside = tmp_path / "outside.hpp"
    outside.write_text("// outside\n", encoding="utf-8")
    unexpected = root / "stale.protocyte.hpp"
    try:
        unexpected.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"file symlinks are unavailable: {error}")

    with pytest.raises(coordinator.CoordinatorError, match="unowned generated-looking"):
        engine.reset(plan, token)

    assert unexpected.is_symlink()
    assert (lock_root / "roots" / _identity(root)).is_dir()


@pytest.mark.skipif(os.name == "nt", reason="requires distinct case-sensitive roots")
def test_reset_plan_lookup_is_bound_to_the_requested_case_sensitive_root(
    tmp_path: Path,
) -> None:
    claimed_root = tmp_path / "Generated"
    wrong_root = tmp_path / "generated"
    build = tmp_path / "build"
    lock_root = tmp_path / "locks-v1"
    target = _target("demo")
    plan = _write_plan(
        tmp_path / "plan",
        claimed_root,
        build,
        ((target, "demo.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(lock_root)
    engine.reconcile(plan)

    with pytest.raises(coordinator.CoordinatorError, match="does not match"):
        engine.plan_for_root(wrong_root)
