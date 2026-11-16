from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "consumer_qualification_helpers",
    Path(__file__).with_name("test_output_coordinator.py"),
)
assert _spec is not None and _spec.loader is not None
helpers = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = helpers
_spec.loader.exec_module(helpers)
_spec = importlib.util.spec_from_file_location(
    "consumer_qualification_driver",
    Path(__file__).with_name("verify_consumer_registry.py"),
)
assert _spec is not None and _spec.loader is not None
driver = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = driver
_spec.loader.exec_module(driver)
_modules = itertools.count()


def seeded(tmp_path: Path):
    module = driver.load(
        Path(__file__).resolve().parents[1] / "cmake/ProtocyteOutputCoordinator.py",
        f"consumer_qualification_fixture_{next(_modules)}",
    )
    input_file = tmp_path / "consumer.plan"
    root, build = tmp_path / "generated", tmp_path / "build"
    target = helpers._target("consumer-qualification")
    helpers._write_plan(input_file, root, build, ((target, "sample.protocyte.hpp"),))
    plan = module.Plan.read(input_file)
    engine = module.OutputCoordinator(
        tmp_path / "registry", registry_validation="reference"
    )
    token = engine.reconcile(plan)
    stage = plan.staging_for_target(target) / "generated"
    helpers._stage(stage, "sample.protocyte.hpp", b"// original generated file\n")
    engine.publish(plan, target, stage)
    manifest = {
        "registry": str(engine.lock_root),
        "current_plans": [str(input_file)],
        "retired_plans": [],
    }
    work = tmp_path / "qualification"
    work.mkdir()
    return module, engine, plan, target, token, manifest, work


def test_capture_and_reference_keep_original_data_and_redact_receipt(
    tmp_path: Path,
) -> None:
    module, engine, plan, _, token, manifest, work = seeded(tmp_path)
    original = driver.ledger(engine.lock_root)
    output = plan.root / "sample.protocyte.hpp"
    before = output.read_bytes(), output.stat().st_mtime_ns
    receipt = driver.capture(module, manifest, work)
    checked = driver.reference(module, manifest, work)
    assert checked["result"] == "accepted" and checked["claims_checked"] == 1
    assert receipt["committed_output_files_checked"] == 1
    assert receipt["claims_plans_snapshots_and_outputs_unchanged"]
    assert driver.ledger(engine.lock_root) == original
    assert (output.read_bytes(), output.stat().st_mtime_ns) == before
    serialized = json.dumps({"capture": receipt, "reference": checked})
    assert str(tmp_path) not in serialized and token not in serialized
    with pytest.raises(RuntimeError, match="ownership/output mutation"):
        module._atomic_write(output, b"forbidden")
    with pytest.raises(RuntimeError, match="ownership/output mutation"):
        engine.reconcile(plan)
    assert output.read_bytes() == before[0]


def test_frozen_reference_preserves_original_lock_namespace_rejection(
    tmp_path: Path,
) -> None:
    module, engine, _, _, _, manifest, work = seeded(tmp_path)
    driver.capture(module, manifest, work)
    dangerous = work / "inputs/000.plan"
    helpers._write_plan(
        dangerous,
        engine.lock_root / "unsafe-generated",
        tmp_path / "other-build",
        ((helpers._target("unsafe-namespace"), "sample.protocyte.hpp"),),
    )
    with pytest.raises(module.CoordinatorError, match="lock namespace"):
        driver.reference(module, manifest, work)


def test_frozen_reference_checks_foreign_staging_reservations(tmp_path: Path) -> None:
    module, _, plan, target, _, manifest, work = seeded(tmp_path)
    driver.capture(module, manifest, work)
    helpers._write_plan(
        work / "inputs/000.plan",
        plan.staging_for_target(target) / "intruder",
        tmp_path / "intruder-build",
        ((helpers._target("intruder"), "sample.protocyte.hpp"),),
    )
    with pytest.raises(module.CoordinatorError, match="staging reserved"):
        driver.reference(module, manifest, work)


def test_capture_rejects_output_corruption_without_repairing_it(tmp_path: Path) -> None:
    module, engine, plan, _, _, manifest, work = seeded(tmp_path)
    output = plan.root / "sample.protocyte.hpp"
    output.write_bytes(b"// externally changed\n")
    before = driver.ledger(engine.lock_root)
    with pytest.raises(AssertionError, match="differs from committed snapshot"):
        driver.capture(module, manifest, work)
    assert output.read_bytes() == b"// externally changed\n"
    assert driver.ledger(engine.lock_root) == before


def test_capture_rejects_foreign_state_link_before_copying_ledger(
    tmp_path: Path,
) -> None:
    module, engine, _, _, _, manifest, work = seeded(tmp_path)
    path = tmp_path / "foreign.plan"
    helpers._write_plan(
        path,
        tmp_path / "foreign-generated",
        tmp_path / "foreign-build",
        ((helpers._target("foreign"), "foreign.protocyte.hpp"),),
    )
    foreign = module.Plan.read(path)
    engine.reconcile(foreign)
    state = engine._state_directory(foreign.root)
    preserved = tmp_path / "preserved-foreign-state"
    assert state.resolve().is_relative_to(tmp_path.resolve())
    assert preserved.resolve().is_relative_to(tmp_path.resolve())
    claim = (state / "claim.json").read_bytes()
    state.rename(preserved)
    helpers._directory_link(state, preserved)
    with pytest.raises(AssertionError, match="unsafe source registry state"):
        driver.capture(module, manifest, work)
    assert (preserved / "claim.json").read_bytes() == claim
    assert not (work / "ledger/roots").exists()


@pytest.mark.parametrize("failed_certificate", [False, True])
def test_indexed_qualification_requires_mutation_guard_and_restores_promotion_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_certificate: bool
) -> None:
    module, engine, _, _, _, manifest, work = seeded(tmp_path)
    before = driver.ledger(engine.lock_root)
    qualified = module._COMMITTED_INDEX_QUALIFIED

    def certificate(self, *args, **kwargs):
        assert module._COMMITTED_INDEX_QUALIFIED is True
        with pytest.raises(RuntimeError, match="ownership/output mutation"):
            module._atomic_write(tmp_path / "forbidden", b"forbidden")
        if failed_certificate:
            raise RuntimeError("test certificate could not be verified")
        self.validation_metrics.update(
            commit_certificate="verified",
            commit_state="closed",
            commit_handles_opened=1,
            commit_handles_closed=1,
            commit_claims_checked=1,
            commit_probe_state="closed",
            commit_probe_native_retired=True,
            commit_probe_active=0,
            commit_probe_pending=0,
            commit_probe_comparisons=0,
            commit_fresh_comparisons=0,
            commit_probe_workers=4,
            commit_probe_peak_active=0,
            commit_probe_peak_pending=0,
        )
        return True

    monkeypatch.setattr(
        module.OutputCoordinator, "_preview_committed_index", certificate
    )
    if failed_certificate:
        with pytest.raises(RuntimeError, match="required reference fallback"):
            driver.candidate(module, manifest, work, integrated=True)
    else:
        receipt = driver.candidate(module, manifest, work, integrated=True)
        assert receipt["native_metrics"]["authoritative"] == "index"
    assert module._COMMITTED_INDEX_QUALIFIED is qualified
    assert driver.ledger(engine.lock_root) == before
    assert not (tmp_path / "forbidden").exists()
