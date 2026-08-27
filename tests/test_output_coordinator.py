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
    lines.extend(
        f"output={target}|{relative.encode().hex()}" for target, relative in outputs
    )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return coordinator.Plan.read(path)


def _target(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


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
    staging = tmp_path / "staging"
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
    first_staging = tmp_path / "first-staging"
    _stage(first_staging, "demo.protocyte.cpp", b"// source v1\n")
    _stage(first_staging, "demo.protocyte.hpp", b"// header v1\n")
    engine.publish(plan, target, first_staging)
    second_staging = tmp_path / "second-staging"
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
    staging = tmp_path / "staging"
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    empty_plan = _write_plan(plan_path, root, build, ())

    engine.reconcile(empty_plan)

    assert not (root / "demo.protocyte.hpp").exists()
    assert _snapshot(lock_root, root)["entries"] == {}


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
    staging = tmp_path / "staging"
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
    staging = tmp_path / "staging"
    _stage(staging, "demo.protocyte.hpp", b"// first\n")
    engine.publish(plan, target, staging)
    import shutil

    shutil.rmtree(build)
    build.mkdir()
    recreated = _write_plan(plan_path, root, build, ((target, "demo.protocyte.hpp"),))
    replacement = tmp_path / "replacement"
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
    staging = tmp_path / "staging"
    _stage(staging, "api/demo.protocyte.hpp", b"// generated\n")

    with pytest.raises(coordinator.CoordinatorError, match="symbolic link or junction"):
        engine.publish(plan, target, staging)

    assert not (outside / "demo.protocyte.hpp").exists()


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
    staging = tmp_path / "staging"
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
    staging = tmp_path / "staging"
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)

    engine.reset(plan, token)

    assert not (root / "demo.protocyte.hpp").exists()
    assert not (lock_root / "roots" / _identity(root)).exists()


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
    staging = tmp_path / "staging"
    _stage(staging, "demo.protocyte.hpp", b"// generated\n")
    engine.publish(plan, target, staging)
    import shutil

    shutil.rmtree(build)

    durable_plan = engine.plan_for_root(root)
    engine.reset(durable_plan, token)

    assert not (lock_root / "roots" / _identity(root)).exists()
