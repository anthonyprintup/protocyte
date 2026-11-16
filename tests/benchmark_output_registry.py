"""Offline registry scaling benchmark; Python 3.12+, standard library only.

Each sample seeds real claims into a fresh, explicitly isolated registry. No
generated payloads, shared registry, compiler, network, or source edits are used.
Seed/validation/total reconciliation wall and CPU times are reported separately.
Counters delegate every operation unchanged. Timings include instrumentation.

Example (run from the repository root):
  python tests/benchmark_output_registry.py --claims 0 8 16 --plans 1 4 --repeat 3

Pass --baseline-source PATH to compare another checkout (or a directory holding
only cmake/ProtocyteOutputCoordinator.py). Baseline/candidate samples alternate
order, use the same path depth, and never run concurrently. Results and synthetic
state are retained under a fresh temporary directory, or --work NEW_DIRECTORY.
Wall times are descriptive; operation counts are the portable regression gate.
"""

from __future__ import annotations

import argparse
import cProfile
import contextlib
import hashlib
import importlib.util
import json
import os
import platform
import pstats
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import Any


def _load(source: Path, label: str) -> ModuleType:
    script = source / "cmake" / "ProtocyteOutputCoordinator.py"
    spec = importlib.util.spec_from_file_location(f"registry_benchmark_{label}", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module._benchmark_implementation_files = _implementation_fingerprint(module)
    return module


def _plan(
    module: ModuleType,
    work: Path,
    name: str,
    *,
    targets_per_plan: int = 1,
    shared_build_root: bool = False,
) -> Any:
    directory = work / name
    build = work / "shared-build" if shared_build_root else directory / "build"
    directory.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=shared_build_root)
    path = directory / "outputs.plan"

    def encode(value: Path | str) -> str:
        return os.fspath(value).encode("utf-8").hex()

    lines = [
        module.PLAN_HEADER,
        "root-hex=" + encode(directory / "generated"),
        "build-root-hex=" + encode(build),
    ]
    for number in range(targets_per_plan):
        target_name = name if number == 0 else f"{name}/target-{number}"
        target = hashlib.sha256(target_name.encode()).hexdigest()
        staging = directory / f".protocyte-generation-staging-{target}"
        relative = (
            "sample.protocyte.hpp" if number == 0 else f"sample-{number}.protocyte.hpp"
        )
        lines.extend(
            [
                "target=" + target + "|" + encode(staging),
                "output=" + target + "|" + encode(relative),
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return module.Plan.read(path)


def _implementation_fingerprint(module: ModuleType) -> dict[str, str]:
    paths = [Path(module.__file__)]
    for name in ("ProtocyteOwnershipIndex.py", "ProtocytePathObservation.py"):
        helper = paths[0].with_name(name)
        if helper.is_file():
            paths.append(helper)
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _filesystem_counts(profile: cProfile.Profile) -> dict[str, int]:
    filesystem_calls = {}
    for (_, _, name), (_, calls, _, _, _) in pstats.Stats(profile).stats.items():
        for operation in (
            "nt.stat",
            "nt.lstat",
            "nt._getfinalpathname",
            "nt._path_lexists",
            "posix.stat",
            "posix.lstat",
        ):
            if name == f"<built-in method {operation}>":
                filesystem_calls[operation] = calls
        if name == "_windows_file_attributes":
            # ctypes native calls are opaque to cProfile. Include their probe
            # helper; replacing lstat does not eliminate filesystem queries.
            filesystem_calls["windows_attribute_probes"] = calls
    return filesystem_calls


def _prepare_fixture(
    module: ModuleType,
    work: Path,
    claims: int,
    plans: int,
    *,
    registry_validation: str = "reference",
    targets_per_plan: int = 1,
    shared_build_root: bool = False,
    existing_directories: bool = False,
) -> tuple[Any, list[Any], float, float]:
    wall, cpu = time.perf_counter(), time.process_time()
    work.mkdir(parents=True, exist_ok=False)
    engine = (
        module.OutputCoordinator(work / "isolated-registry")
        if registry_validation == "reference"
        else module.OutputCoordinator(
            work / "isolated-registry", registry_validation=registry_validation
        )
    )
    layout = {
        "targets_per_plan": targets_per_plan,
        "shared_build_root": shared_build_root,
    }
    retained = [
        _plan(module, work, f"retained-{i:04}", **layout) for i in range(claims)
    ]
    current = [_plan(module, work, f"current-{i:04}", **layout) for i in range(plans)]
    if existing_directories:
        for plan in (*retained, *current):
            plan.root.mkdir()
            for target in plan.targets:
                target.staging.mkdir()
    # Setup only, as in issue #54's POC. Seed disjoint synthetic fixtures through
    # the real private locked helpers, avoiding all-pairs fixture validation.
    # The measured reconcile_set below is unchanged and skips no checks.
    module._durable_mkdir(engine.lock_root)
    reporter = (
        module._ReconcileProgress(plans, 0)
        if hasattr(module, "_ReconcileProgress")
        else contextlib.nullcontext(None)
    )
    with reporter as progress, module.FileLock(engine.lock_root / "registry.lock"):
        if progress is not None:
            progress.phase(
                f"fixture setup (0/{claims} claims seeded)", "reconciliation"
            )
        for number, plan in enumerate(retained, start=1):
            with (
                module.FileLock(engine._generation_lock(plan.root)),
                module.FileLock(engine._publication_lock(plan.root)),
            ):
                state = engine._state_directory(plan.root)
                engine._initialize_claim_locked(state, plan)
                engine._reconcile_locked(state, plan)
            if progress is not None:
                progress.phase(
                    f"fixture setup ({number}/{claims} claims seeded)", "reconciliation"
                )
    seed_wall = time.perf_counter() - wall
    seed_cpu = time.process_time() - cpu
    return engine, current, seed_wall, seed_cpu


def _sample(
    module: ModuleType,
    work: Path,
    claims: int,
    plans: int,
    *,
    registry_validation: str = "reference",
    targets_per_plan: int = 1,
    shared_build_root: bool = False,
    existing_directories: bool = False,
) -> dict[str, Any]:
    expected_sources = getattr(module, "_benchmark_implementation_files", None)
    if expected_sources is None:
        expected_sources = _implementation_fingerprint(module)
    engine, current, seed_wall, seed_cpu = _prepare_fixture(
        module,
        work,
        claims,
        plans,
        registry_validation=registry_validation,
        targets_per_plan=targets_per_plan,
        shared_build_root=shared_build_root,
        existing_directories=existing_directories,
    )
    counts = {
        "registry_validations": 0,
        "registry_scans": 0,
        "recorded_plan_loads_in_validation": 0,
        "path_projections_in_validation": 0,
        "path_projections_total": 0,
    }
    active = False
    profile = cProfile.Profile()
    validation_wall = validation_cpu = 0.0
    original_validate = engine._validate_registry
    original_load = engine._load_recorded_plan
    original_project = module.project_path
    original_scandir = module.os.scandir
    original_lock = module.FileLock
    original_current_validate = engine._validate_plan_set
    lock_wait = registry_held = current_validation = 0.0

    class TimedLock(original_lock):
        def __enter__(self) -> Any:
            nonlocal lock_wait
            started = time.perf_counter()
            result = super().__enter__()
            self._acquired = time.perf_counter()
            lock_wait += self._acquired - started
            return result

        def __exit__(self, *args: Any) -> None:
            nonlocal registry_held
            try:
                super().__exit__(*args)
            finally:
                if self.path == engine.lock_root / "registry.lock":
                    registry_held += time.perf_counter() - self._acquired

    def validate_current(*args: Any, **kwargs: Any) -> Any:
        nonlocal current_validation
        started = time.perf_counter()
        try:
            return original_current_validate(*args, **kwargs)
        finally:
            current_validation += time.perf_counter() - started

    def validate(*args: Any, **kwargs: Any) -> Any:
        nonlocal active, validation_wall, validation_cpu
        counts["registry_validations"] += 1
        active = True
        start_wall, start_cpu = time.perf_counter(), time.process_time()
        profile.enable()
        try:
            return original_validate(*args, **kwargs)
        finally:
            profile.disable()
            validation_wall += time.perf_counter() - start_wall
            validation_cpu += time.process_time() - start_cpu
            active = False

    def load(*args: Any, **kwargs: Any) -> Any:
        if active:
            counts["recorded_plan_loads_in_validation"] += 1
        return original_load(*args, **kwargs)

    def project(*args: Any, **kwargs: Any) -> Any:
        counts["path_projections_total"] += 1
        if active:
            counts["path_projections_in_validation"] += 1
        return original_project(*args, **kwargs)

    def scandir(path: Any) -> Any:
        if active and path == engine.lock_root / "roots":
            counts["registry_scans"] += 1
        return original_scandir(path)

    engine._validate_registry = validate
    engine._load_recorded_plan = load
    module.project_path = project
    module.os.scandir = scandir
    module.FileLock = TimedLock
    engine._validate_plan_set = validate_current
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        tokens = engine.reconcile_set((), current)
        reconcile_wall = time.perf_counter() - wall
        reconcile_cpu = time.process_time() - cpu
    finally:
        engine._validate_registry = original_validate
        engine._load_recorded_plan = original_load
        engine._validate_plan_set = original_current_validate
        module.FileLock = original_lock
        module.project_path = original_project
        module.os.scandir = original_scandir
    assert len(tokens) == plans and all(tokens)
    if _implementation_fingerprint(module) != expected_sources:
        raise RuntimeError(
            "coordinator sources changed during the sample; discard its timings"
        )
    filesystem_calls = _filesystem_counts(profile)
    return {
        "retained_claims": claims,
        "current_plans": plans,
        "layout": {
            "targets_per_plan": targets_per_plan,
            "shared_build_root": shared_build_root,
            "existing_directories": existing_directories,
        },
        "seed_wall_seconds": seed_wall,
        "seed_cpu_seconds": seed_cpu,
        "validation_wall_seconds": validation_wall,
        "validation_cpu_seconds": validation_cpu,
        "reconcile_wall_seconds": reconcile_wall,
        "reconcile_cpu_seconds": reconcile_cpu,
        "lock_wait_wall_seconds": lock_wait,
        "registry_lock_held_wall_seconds": registry_held,
        "current_plan_validation_wall_seconds": current_validation,
        "validation_engine": registry_validation,
        "index_experiment": getattr(engine, "validation_metrics", {}),
        "shadow_candidate_wall_seconds": getattr(engine, "validation_metrics", {}).get(
            "preview_wall_seconds", 0.0
        ),
        "reference_validation_wall_seconds": getattr(
            engine, "validation_metrics", {}
        ).get("reference_wall_seconds", validation_wall),
        **counts,
        "validation_filesystem_calls": filesystem_calls,
        "completed_plans": len(tokens),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--baseline-source", type=Path)
    parser.add_argument("--claims", type=int, nargs="+", default=[0, 8, 16])
    parser.add_argument("--plans", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--targets-per-plan", type=int, default=1)
    parser.add_argument("--shared-build-root", action="store_true")
    parser.add_argument("--existing-directories", action="store_true")
    parser.add_argument(
        "--registry-validation",
        choices=("reference", "shadow", "native-shadow"),
        default="reference",
    )
    parser.add_argument(
        "--large",
        action="store_true",
        help="opt into 129..4096 retained claims (setup and validation may take minutes)",
    )
    args = parser.parse_args()
    if (
        any(not 0 <= value <= 4096 for value in args.claims)
        or any(not 1 <= value <= 32 for value in args.plans)
        or not 1 <= args.repeat <= 20
    ):
        parser.error("expected 0..4096 claims, 1..32 plans, and 1..20 repetitions")
    if max(args.claims) > 128 and not args.large:
        parser.error("more than 128 claims requires explicit --large opt-in")
    if not 1 <= args.targets_per_plan <= 8:
        parser.error("expected 1..8 targets per plan")
    sources = {"candidate": args.source.resolve()}
    if args.baseline_source:
        sources = {"baseline": args.baseline_source.resolve(), **sources}
    for source in sources.values():
        if not (source / "cmake" / "ProtocyteOutputCoordinator.py").is_file():
            parser.error("source must contain cmake/ProtocyteOutputCoordinator.py")
    if args.work:
        work = args.work.absolute()
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="protocyte-registry-benchmark-"))
    modules = {label: _load(source, label) for label, source in sources.items()}
    result: dict[str, Any] = {
        "platform": platform.system(),
        "python": platform.python_version(),
        "timings_include_instrumentation": True,
        "setup_method": "private locked initialization/reconciliation (issue #54 POC)",
        "coordinator_sha256": {
            label: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for label, module in modules.items()
        },
        "implementation_files": {
            label: _implementation_fingerprint(module)
            for label, module in modules.items()
        },
        "samples": [],
        "medians": [],
    }
    print(f"Synthetic work and results: {work}", flush=True)
    labels = list(modules)
    for repetition in range(args.repeat):
        for claims in args.claims:
            for plans in args.plans:
                for label in labels if repetition % 2 == 0 else reversed(labels):
                    sample_work = work / f"r{repetition}-c{claims}-p{plans}" / label
                    print(
                        json.dumps(
                            {
                                "phase": "seed",
                                "revision": label,
                                "claims": claims,
                                "plans": plans,
                                "repetition": repetition,
                            }
                        ),
                        flush=True,
                    )
                    sample = {
                        "revision": label,
                        "repetition": repetition,
                        **_sample(
                            modules[label],
                            sample_work,
                            claims,
                            plans,
                            registry_validation=args.registry_validation
                            if label == "candidate"
                            else "reference",
                            targets_per_plan=args.targets_per_plan,
                            shared_build_root=args.shared_build_root,
                            existing_directories=args.existing_directories,
                        ),
                    }
                    result["samples"].append(sample)
                    print(json.dumps(sample), flush=True)
                    (work / "results.json").write_text(
                        json.dumps(result, indent=2) + "\n", encoding="utf-8"
                    )
    for claims in args.claims:
        for plans in args.plans:
            medians = {}
            for label in labels:
                samples = [
                    sample
                    for sample in result["samples"]
                    if sample["revision"] == label
                    and sample["retained_claims"] == claims
                    and sample["current_plans"] == plans
                ]
                medians[label] = {
                    key: statistics.median(sample[key] for sample in samples)
                    for key in samples[0]
                    if key.endswith("_seconds")
                    or key.startswith(("registry_", "path_", "recorded_"))
                }
            summary = {"retained_claims": claims, "current_plans": plans, **medians}
            if "baseline" in medians:
                summary["wall_time_reduction_percent"] = 100 * (
                    1
                    - medians["candidate"]["reconcile_wall_seconds"]
                    / medians["baseline"]["reconcile_wall_seconds"]
                )
            result["medians"].append(summary)
            print(json.dumps(summary), flush=True)
    (work / "results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
