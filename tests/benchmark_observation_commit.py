"""Read-only committed candidate benchmark; never reconciliation authority.

Seeds real claims in a new private registry, takes the ordinary coordinator
locks, validates all current plans and runs the entire provisional read-set
commit (record authentication, comparisons, inventories, versions, witnesses,
and handle release). No tokens, claims, or outputs are produced after seeding.
The optional reference oracle is timed separately. Even a verified native
certificate does not make this experimental algorithm an authorized validator.
Only results.json is suitable for sharing; fixtures contain private paths.
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


def sample(module, work: Path, args) -> dict:
    expected = _implementation_fingerprint(module)
    engine, current, setup_wall, setup_cpu = _prepare_fixture(
        module,
        work,
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
        progress.phase("waiting for read-only commit locks", "lock_wait")
        locks.enter_context(module.FileLock(engine.lock_root / "registry.lock"))
        roots = {module._path_key(plan.root): plan.root for plan in current}
        for root in sorted(roots.values(), key=module._portable_identity):
            locks.enter_context(module.FileLock(engine._generation_lock(root)))
        for root in sorted(roots.values(), key=module._portable_identity):
            locks.enter_context(module.FileLock(engine._publication_lock(root)))
        lock_seconds = time.perf_counter() - started
        progress.phase("checking all current plans", "validation")
        total_started, total_cpu = time.perf_counter(), time.process_time()
        started = time.perf_counter()
        engine._validate_plan_set(current)
        current_seconds = time.perf_counter() - started
        engine.validation_metrics = {
            "mode": "commit-candidate-only",
            "authoritative": "none",
        }
        progress.phase("read-only provisional observation commit", "validation")
        started, cpu = time.perf_counter(), time.process_time()
        if not args.no_profile:
            profile.enable()
        try:
            accepted = engine._preview_committed_index(
                current, set(), progress=progress
            )
        finally:
            if not args.no_profile:
                profile.disable()
            committed_seconds = time.perf_counter() - started
            committed_cpu = time.process_time() - cpu
        if not args.no_profile:
            profile.dump_stats(work / "candidate.prof")
        total_seconds = time.perf_counter() - total_started
        total_cpu_seconds = time.process_time() - total_cpu
        assert accepted
        metrics = engine.validation_metrics
        assert metrics["commit_certificate"] == "verified"
        assert metrics["commit_claims_checked"] == args.claims
        assert metrics["commit_records_read"] == 2 * args.claims
        assert metrics["commit_state"] == "closed"
        assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]
        oracle_wall = oracle_cpu = None
        if args.reference_oracle:
            progress.phase("fresh reference oracle (separate timing)", "validation")
            started, cpu = time.perf_counter(), time.process_time()
            engine._validate_registry_reference(current, set(), progress=progress)
            oracle_wall = time.perf_counter() - started
            oracle_cpu = time.process_time() - cpu
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == args.claims
    if _implementation_fingerprint(module) != expected:
        raise RuntimeError(
            "coordinator sources changed during the sample; discard its timings"
        )
    return {
        "scope": "complete read-only committed candidate; no reconciliation authority",
        "cprofile_enabled": not args.no_profile,
        "reference_validation_performed": args.reference_oracle,
        "reference_result": "accepted" if args.reference_oracle else None,
        "reconciliation_authorized": False,
        "tokens_produced": 0,
        "implementation_files": expected,
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
        "committed_candidate_wall_seconds": committed_seconds,
        "committed_candidate_cpu_seconds": committed_cpu,
        "all_candidate_validation_wall_seconds": total_seconds,
        "all_candidate_validation_cpu_seconds": total_cpu_seconds,
        "reference_oracle_wall_seconds": oracle_wall,
        "reference_oracle_cpu_seconds": oracle_cpu,
        "candidate_filesystem_calls": _filesystem_counts(profile)
        if not args.no_profile
        else None,
        "index_experiment": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=int, default=64)
    parser.add_argument("--plans", type=int, default=11)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--large", action="store_true")
    parser.add_argument("--work", type=Path)
    parser.add_argument("--targets-per-plan", type=int, default=1)
    parser.add_argument("--shared-build-root", action="store_true")
    parser.add_argument("--existing-directories", action="store_true")
    parser.add_argument("--reference-oracle", action="store_true")
    parser.add_argument(
        "--no-profile",
        action="store_true",
        help="use wall/CPU timers and native counters without cProfile overhead",
    )
    args = parser.parse_args()
    if not 0 <= args.claims <= 4096 or not 1 <= args.plans <= 32:
        parser.error("expected 0..4096 claims and 1..32 plans")
    if args.claims > 128 and not args.large:
        parser.error("more than 128 claims requires explicit --large opt-in")
    if not 1 <= args.repeat <= 20 or not 1 <= args.targets_per_plan <= 8:
        parser.error("expected 1..20 repetitions and 1..8 targets per plan")
    if args.work:
        work = args.work.absolute()
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="protocyte-observation-commit-"))
    module = _load(Path(__file__).resolve().parents[1], "commit_candidate_only")
    results = {
        "platform": platform.system(),
        "python": platform.python_version(),
        "timings_include_instrumentation": True,
        "implementation_files": _implementation_fingerprint(module),
        "samples": [],
    }
    print(f"Private synthetic work and path-free results: {work}", flush=True)
    for repetition in range(args.repeat):
        measured = {
            "repetition": repetition,
            **sample(module, work / f"r{repetition}", args),
        }
        results["samples"].append(measured)
        (work / "results.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(measured), flush=True)


if __name__ == "__main__":
    main()
