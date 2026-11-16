"""Non-authorizing qualification against private, real consumer inputs.

The private manifest supplies registry/current_plans/legacy_coordinator paths.
Capture copies immutable ledger bytes under the original locks; references run
against those frozen bytes and the original output/build/staging paths. Live
candidate/indexed runs always use the original registry and lock namespace.
Indexed exercises the production validation entry point, without proceeding to
reconciliation. No command resets, publishes, or changes defaults. Publish only
the sanitized result receipts; the preservation manifest stays private.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import inspect
import json
import os
import platform
import stat
import sys
import time
from pathlib import Path
from types import ModuleType

LEGACY_SHA256 = "2ff54b69242d46eb8e35a52d30b32bc9afd815c00b6c0abeb8765d6fe7ddbb85"
IMPLEMENTATION = (
    "ProtocyteOutputCoordinator.py",
    "ProtocyteOwnershipIndex.py",
    "ProtocytePathObservation.py",
    "ProtocyteObservationCommit.py",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path, name: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def forbid_mutations(module: ModuleType) -> None:
    def forbidden(*args, **kwargs):
        raise RuntimeError("qualification attempted an ownership/output mutation")

    for name in (
        "_atomic_write",
        "_durable_rmtree",
        "_durable_unlink",
        "_durable_rename",
    ):
        if hasattr(module, name):
            setattr(module, name, forbidden)
    for name in (
        "reconcile",
        "reconcile_set",
        "_reconcile_locked",
        "publish",
        "reset",
        "_recover",
        "_apply_pending",
        "_publish_one",
        "_initialize_claim_locked",
        "_release_claim",
        "_retire_unplanned",
        "_retire_staging",
    ):
        if hasattr(module.OutputCoordinator, name):
            setattr(module.OutputCoordinator, name, forbidden)


def ledger(registry: Path) -> dict[str, dict[str, str]]:
    def plain(info, expected_type) -> bool:
        return (
            expected_type(info.st_mode)
            and not stat.S_ISLNK(info.st_mode)
            and not getattr(info, "st_file_attributes", 0) & 0x400
        )

    result = {}
    roots = registry / "roots"
    assert plain(roots.lstat(), stat.S_ISDIR), "unsafe source registry directory"
    for state in sorted(roots.iterdir()):
        assert len(state.name) == 64 and all(
            c in "0123456789abcdef" for c in state.name
        )
        assert plain(state.lstat(), stat.S_ISDIR), "unsafe source registry state"
        values = {}
        for name in ("claim.json", "plan.json"):
            record = state / name
            try:
                info = record.lstat()
            except FileNotFoundError:
                continue
            assert plain(info, stat.S_ISREG), "unsafe source registry record"
            data = record.read_bytes()
            values[name] = digest(data)
        result[state.name] = values
    return result


@contextlib.contextmanager
def original_locks(module, engine, plans, *, progress=None):
    with contextlib.ExitStack() as stack:
        if progress is not None:
            progress.phase("waiting for original registry lock", "lock_wait")
        stack.enter_context(module.FileLock(engine.lock_root / "registry.lock"))
        roots = {module._path_key(plan.root): plan.root for plan in plans}
        ordered = sorted(roots.values(), key=module._portable_identity)
        if progress is not None:
            progress.phase("waiting for original generation locks", "lock_wait")
        for root in ordered:
            stack.enter_context(module.FileLock(engine._generation_lock(root)))
        if progress is not None:
            progress.phase("waiting for original publication locks", "lock_wait")
        for root in ordered:
            stack.enter_context(module.FileLock(engine._publication_lock(root)))
        yield


def output_fingerprints(module, engine, plans) -> dict:
    result = {}
    for number, plan in enumerate(plans):
        state = engine._state_directory(plan.root)
        claim = engine._load_claim(state, plan)
        engine._require_current_plan(state, plan, claim)
        snapshot = engine._load_snapshot(state, claim)
        for relative, entry in snapshot["entries"].items():
            path = plan.root / relative
            assert module.project_path(path, leaf_may_be_file=True) == path
            assert not module._is_link(path), "consumer output is a link"
            data = path.read_bytes()
            assert digest(data) == entry["sha256"], (
                "consumer output differs from committed snapshot"
            )
            # File names and tokens stay in the private in-memory audit only.
            result[str(path)] = (digest(data), path.stat().st_mtime_ns)
        assert not list((state / "transactions").iterdir()), (
            "consumer has pending recovery"
        )
        result[f"claim-{number}"] = digest((state / "claim.json").read_bytes())
        result[f"snapshot-{number}"] = digest((state / "snapshot.json").read_bytes())
    return result


def capture(module, manifest: dict, work: Path) -> dict:
    registry = Path(manifest["registry"])
    engine = module.OutputCoordinator(registry)
    paths = [Path(path) for path in manifest["current_plans"]]
    assert paths and not manifest.get("retired_plans"), (
        "this qualification requires a stable current plan set"
    )
    plans = [module.Plan.read(path) for path in paths]
    destination = work / "ledger"
    destination.mkdir()
    with (
        module._ReconcileProgress(len(plans), 0) as progress,
        original_locks(module, engine, plans, progress=progress),
    ):
        progress.phase("capturing read-only consumer ledger", "validation")
        forbid_mutations(module)
        before = ledger(registry)
        assert all("claim.json" in files for files in before.values())
        outputs_before = output_fingerprints(module, engine, plans)
        (destination / "roots").mkdir()
        for state, files in before.items():
            copied = destination / "roots" / state
            copied.mkdir()
            for name, expected in files.items():
                data = (registry / "roots" / state / name).read_bytes()
                assert digest(data) == expected
                (copied / name).write_bytes(data)
        inputs = work / "inputs"
        inputs.mkdir()
        for number, path in enumerate(paths):
            (inputs / f"{number:03}.plan").write_bytes(path.read_bytes())
        assert ledger(registry) == before
        assert ledger(destination) == before
        assert output_fingerprints(module, engine, plans) == outputs_before
        (work / "preservation.private.json").write_text(
            json.dumps({"ledger": before, "outputs": outputs_before}) + "\n"
        )
    receipt = {
        "registry_entries": len(before),
        "ledger_records": sum(map(len, before.values())),
        "current_plans": len(plans),
        "targets_per_plan": [len(plan.targets) for plan in plans],
        "declared_outputs": sum(len(plan.outputs) for plan in plans),
        "committed_output_files_checked": len(outputs_before) - 2 * len(plans),
        "claims_plans_snapshots_and_outputs_unchanged": True,
        "snapshot_byte_identical": True,
        "tokens_produced": 0,
        "reconciliation_authorized": False,
    }
    (work / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def reference(module, manifest: dict, work: Path) -> dict:
    # The namespace-only pass executes the actual reference checks with its
    # original registry location. Only its root listing is empty; the separate
    # full pass below validates every copied foreign record without filtering.
    original = module.OutputCoordinator(Path(manifest["registry"]))
    plans = [
        module.Plan.read(path) for path in sorted((work / "inputs").glob("*.plan"))
    ]
    call_name = (
        "_validate_registry_reference"
        if hasattr(original, "_validate_registry_reference")
        else "_validate_registry"
    )
    forbid_mutations(module)
    real_scandir = module.os.scandir

    class EmptyListing:
        def __enter__(self):
            return iter(())

        def __exit__(self, *args):
            pass

    def namespace_listing(path):
        if Path(path) == original.lock_root / "roots":
            return EmptyListing()
        return real_scandir(path)

    module.os.scandir = namespace_listing
    try:
        getattr(original, call_name)(plans, set())
    finally:
        module.os.scandir = real_scandir
    engine = module.OutputCoordinator(work / "ledger")
    before = ledger(engine.lock_root)
    start, cpu = time.perf_counter(), time.process_time()
    with module._ReconcileProgress(len(plans), 0) as progress:
        progress.phase("read-only frozen consumer reference", "validation")
        module.OutputCoordinator._validate_plan_set(plans)
        function = getattr(engine, call_name)
        kwargs = (
            {"progress": progress}
            if "progress" in inspect.signature(function).parameters
            else {}
        )
        function(plans, set(), **kwargs)
        checked = progress._claims
    seconds = time.perf_counter() - start
    cpu_seconds = time.process_time() - cpu
    assert ledger(engine.lock_root) == before
    return {
        "result": "accepted",
        "registry_entries": len(before),
        "claims_checked": checked,
        "validation_seconds": seconds,
        "validation_cpu_seconds": cpu_seconds,
        "frozen_ledger": True,
        "original_output_paths": True,
        "original_namespace_checked_separately": True,
        "live_shared_lock_held": False,
        "ownership_or_output_mutations": 0,
    }


def candidate(
    module,
    manifest: dict,
    work: Path,
    *,
    integrated: bool = False,
    default_mode: bool = False,
) -> dict:
    engine = module.OutputCoordinator(
        Path(manifest["registry"]),
        **(
            {}
            if default_mode
            else {"registry_validation": "indexed" if integrated else "reference"}
        ),
    )
    if default_mode:
        assert module._COMMITTED_INDEX_QUALIFIED is True
        assert engine.registry_validation == "indexed"
    if integrated:
        # A failed timing gate must not hold the live shared lock for a slow
        # reference pass. The full reference oracles are qualified separately;
        # successful production entry-point execution must never call this.
        def unexpected_reference(*args, **kwargs):
            raise RuntimeError("live indexed qualification required reference fallback")

        engine._validate_registry_reference = unexpected_reference
    start = time.perf_counter()
    plans = [module.Plan.read(Path(path)) for path in manifest["current_plans"]]
    parse_seconds = time.perf_counter() - start
    start = time.perf_counter()
    with (
        module._ReconcileProgress(len(plans), 0) as progress,
        original_locks(module, engine, plans, progress=progress),
    ):
        lock_seconds = time.perf_counter() - start
        forbid_mutations(module)
        progress.phase("read-only live consumer candidate", "validation")
        start, cpu = time.perf_counter(), time.process_time()
        engine.validation_metrics = {
            "mode": "consumer-candidate-only",
            "authoritative": "none",
        }
        module.OutputCoordinator._validate_plan_set(plans)
        if integrated:
            qualified = module._COMMITTED_INDEX_QUALIFIED
            try:
                # The ownership/output mutation guard above is already active.
                # Override only this import, never a consumer process or file.
                module._COMMITTED_INDEX_QUALIFIED = True
                engine._validate_registry(plans, set(), progress=progress)
            finally:
                module._COMMITTED_INDEX_QUALIFIED = qualified
            accepted = True
        else:
            accepted = engine._preview_committed_index(plans, set(), progress=progress)
        seconds = time.perf_counter() - start + parse_seconds
        cpu_seconds = time.process_time() - cpu
        metrics = engine.validation_metrics
    assert metrics["commit_certificate"] == "verified"
    assert metrics["commit_state"] == "closed"
    assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]
    assert metrics["commit_cleanup_failed"] is False
    assert metrics["commit_probe_state"] == "closed"
    assert metrics["commit_probe_native_retired"] is True
    assert metrics["commit_probe_active"] == metrics["commit_probe_pending"] == 0
    assert metrics["commit_probe_comparisons"] == metrics["commit_fresh_comparisons"]
    assert metrics["commit_probe_peak_active"] <= metrics["commit_probe_workers"] <= 4
    assert metrics["commit_probe_peak_pending"] <= 2 * metrics["commit_probe_workers"]
    if integrated:
        assert metrics["authoritative"] == "index"
        assert metrics["reference_wall_seconds"] == 0
    return {
        "result": "accepted" if accepted else "conflict",
        "validation_seconds": seconds,
        "validation_cpu_seconds": cpu_seconds,
        "plan_parse_seconds": parse_seconds,
        "lock_wait_seconds": lock_seconds,
        "current_plans": len(plans),
        "registry_entries": metrics["commit_claims_checked"],
        "original_live_registry_and_locks": True,
        "native_metrics": metrics,
        "ownership_or_output_mutations": 0,
        "tokens_produced": 0,
    }


def audit(module, manifest: dict, work: Path) -> dict:
    engine = module.OutputCoordinator(
        Path(manifest["registry"]), registry_validation="reference"
    )
    plans = [module.Plan.read(Path(path)) for path in manifest["current_plans"]]
    expected = json.loads((work / "preservation.private.json").read_bytes())
    with original_locks(module, engine, plans):
        forbid_mutations(module)
        assert ledger(engine.lock_root) == expected["ledger"]
        outputs = output_fingerprints(module, engine, plans)
        assert json.loads(json.dumps(outputs)) == expected["outputs"]
    return {
        "registry_entries": len(expected["ledger"]),
        "committed_output_files_checked": len(outputs) - 2 * len(plans),
        "claims_plans_snapshots_outputs_and_mtimes_unchanged": True,
        "ownership_or_output_mutations": 0,
        "tokens_produced": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "capture",
            "candidate",
            "indexed",
            "default",
            "audit",
            "reference",
            "legacy-reference",
        ),
        required=True,
    )
    args = parser.parse_args()
    driver_fingerprint = digest(Path(__file__).read_bytes())
    args.work = args.work.absolute()
    sys.dont_write_bytecode = True
    os.environ.pop("PROTOCYTE_COORDINATOR_CRASH_AFTER", None)
    manifest = json.loads(args.manifest.read_bytes())
    if args.mode == "capture":
        args.work.mkdir(parents=True, exist_ok=False)
    else:
        assert args.work.is_dir()
    source = Path(__file__).resolve().parents[1] / "cmake/ProtocyteOutputCoordinator.py"
    if args.mode == "legacy-reference":
        source = Path(manifest["legacy_coordinator"])
        assert digest(source.read_bytes()) == LEGACY_SHA256
    fingerprints = {source.name: digest(source.read_bytes())}
    if args.mode != "legacy-reference":
        fingerprints = {
            name: digest(source.with_name(name).read_bytes()) for name in IMPLEMENTATION
        }
    module = load(source, "qualified_consumer_" + args.mode.replace("-", "_"))
    production_qualified = getattr(module, "_COMMITTED_INDEX_QUALIFIED", False)
    if args.mode == "capture":
        result = capture(module, manifest, args.work)
    elif args.mode in ("candidate", "indexed", "default"):
        result = candidate(
            module,
            manifest,
            args.work,
            integrated=args.mode != "candidate",
            default_mode=args.mode == "default",
        )
    elif args.mode == "audit":
        result = audit(module, manifest, args.work)
    else:
        result = reference(module, manifest, args.work)
    assert all(
        digest(source.with_name(name).read_bytes()) == expected
        for name, expected in fingerprints.items()
    )
    assert digest(Path(__file__).read_bytes()) == driver_fingerprint
    report = {
        "mode": args.mode,
        "platform": platform.system(),
        "python": platform.python_version(),
        "implementation_files": fingerprints,
        "qualification_driver_sha256": driver_fingerprint,
        "index_authorization_enabled": production_qualified,
        **result,
    }
    (args.work / f"{args.mode}-{time.time_ns()}-results.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
