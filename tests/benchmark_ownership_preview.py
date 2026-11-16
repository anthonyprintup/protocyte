"""Read-only sampled-index experiment, NOT an authoritative validation benchmark.

Uses the standard scaling benchmark's isolated fixture setup and ordinary locks.
Only the unverified preview algorithm is measured: no reference validation,
reconciliation or publication is performed after seeding. Preview timings cannot
be reported as a complete reconciler speedup. Publish only results.json, never
fixture directories or claim records containing local paths.
"""

from __future__ import annotations

import argparse
import cProfile
import contextlib
import json
import platform
import tempfile
import time
from pathlib import Path

from benchmark_output_registry import (
    _filesystem_counts,
    _implementation_fingerprint,
    _load,
    _prepare_fixture,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=int, default=64)
    parser.add_argument("--plans", type=int, default=11)
    parser.add_argument("--large", action="store_true")
    parser.add_argument("--work", type=Path)
    parser.add_argument("--targets-per-plan", type=int, default=1)
    parser.add_argument("--shared-build-root", action="store_true")
    parser.add_argument("--existing-directories", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.claims <= 4096 or not 1 <= args.plans <= 32:
        parser.error("expected 0..4096 claims and 1..32 plans")
    if args.claims > 128 and not args.large:
        parser.error("more than 128 claims requires explicit --large opt-in")
    if not 1 <= args.targets_per_plan <= 8:
        parser.error("expected 1..8 targets per plan")
    if args.work:
        work = args.work.absolute()
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="protocyte-index-preview-"))
    module = _load(Path(__file__).resolve().parents[1], "preview_only")
    implementation_files = _implementation_fingerprint(module)
    engine, current, setup_wall, setup_cpu = _prepare_fixture(
        module,
        work / "sample",
        args.claims,
        args.plans,
        targets_per_plan=args.targets_per_plan,
        shared_build_root=args.shared_build_root,
        existing_directories=args.existing_directories,
    )
    profile = cProfile.Profile()
    started = time.perf_counter()
    with (
        module._ReconcileProgress(len(current), 0) as progress,
        contextlib.ExitStack() as locks,
    ):
        progress.phase("waiting for preview locks", "lock_wait")
        locks.enter_context(module.FileLock(engine.lock_root / "registry.lock"))
        roots = {module._path_key(plan.root): plan.root for plan in current}
        for root in sorted(roots.values(), key=module._portable_identity):
            locks.enter_context(module.FileLock(engine._generation_lock(root)))
        for root in sorted(roots.values(), key=module._portable_identity):
            locks.enter_context(module.FileLock(engine._publication_lock(root)))
        lock_seconds = time.perf_counter() - started
        progress.phase("checking current plans for read-only preview", "validation")
        started = time.perf_counter()
        engine._validate_plan_set(current)
        current_seconds = time.perf_counter() - started
        engine.validation_metrics = {"mode": "preview-only", "authoritative": "none"}
        progress.phase("read-only experimental ownership preview", "validation")
        started, cpu = time.perf_counter(), time.process_time()
        profile.enable()
        try:
            accepted = engine._preview_registry_index(current, set(), progress=progress)
        finally:
            profile.disable()
            preview_seconds = time.perf_counter() - started
            preview_cpu = time.process_time() - cpu
    assert accepted and engine.validation_metrics["preview_claims"] == args.claims
    assert engine.validation_metrics["preview_records_read"] == 2 * args.claims
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == args.claims
    if _implementation_fingerprint(module) != implementation_files:
        raise RuntimeError(
            "coordinator sources changed during the preview; discard its timings"
        )
    result = {
        "scope": "read-only sampled algorithm; NOT reference verified or authorized",
        "reference_validation_performed": False,
        "reconciliation_authorized": False,
        "tokens_produced": 0,
        "platform": platform.system(),
        "python": platform.python_version(),
        "implementation_files": implementation_files,
        "timings_include_instrumentation": True,
        "retained_claims": args.claims,
        "current_plans": args.plans,
        "layout": {
            "targets_per_plan": args.targets_per_plan,
            "shared_build_root": args.shared_build_root,
            "existing_directories": args.existing_directories,
        },
        "setup_wall_seconds": setup_wall,
        "setup_cpu_seconds": setup_cpu,
        "lock_preparation_and_wait_seconds": lock_seconds,
        "current_plan_validation_seconds": current_seconds,
        "preview_wall_seconds": preview_seconds,
        "preview_cpu_seconds": preview_cpu,
        "preview_filesystem_calls": _filesystem_counts(profile),
        "index_experiment": engine.validation_metrics,
    }
    (work / "results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
