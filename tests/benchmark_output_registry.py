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
import hashlib
import importlib.util
import json
import os
import platform
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
    return module


def _plan(module: ModuleType, work: Path, name: str) -> Any:
    directory = work / name
    build = directory / "build"
    build.mkdir(parents=True)
    target = hashlib.sha256(name.encode()).hexdigest()
    staging = directory / f".protocyte-generation-staging-{target}"
    path = directory / "outputs.plan"

    def encode(value: Path | str) -> str:
        return os.fspath(value).encode("utf-8").hex()

    path.write_text(
        "\n".join(
            [
                module.PLAN_HEADER,
                "root-hex=" + encode(directory / "generated"),
                "build-root-hex=" + encode(build),
                "target=" + target + "|" + encode(staging),
                "output=" + target + "|" + encode("sample.protocyte.hpp"),
            ]
        )
        + "\n",
        encoding="ascii",
    )
    return module.Plan.read(path)


def _sample(module: ModuleType, work: Path, claims: int, plans: int) -> dict[str, Any]:
    engine = module.OutputCoordinator(work / "isolated-registry")
    retained = [_plan(module, work, f"retained-{i:04}") for i in range(claims)]
    current = [_plan(module, work, f"current-{i:04}") for i in range(plans)]
    wall, cpu = time.perf_counter(), time.process_time()
    if retained:
        engine.reconcile_set((), retained)
    seed_wall = time.perf_counter() - wall
    seed_cpu = time.process_time() - cpu
    counts = {
        "registry_validations": 0,
        "registry_scans": 0,
        "recorded_plan_loads_in_validation": 0,
        "path_projections_in_validation": 0,
        "path_projections_total": 0,
    }
    active = False
    validation_wall = validation_cpu = 0.0
    original_validate = engine._validate_registry
    original_load = engine._load_recorded_plan
    original_project = module.project_path
    original_scandir = module.os.scandir

    def validate(*args: Any, **kwargs: Any) -> Any:
        nonlocal active, validation_wall, validation_cpu
        counts["registry_validations"] += 1
        active = True
        start_wall, start_cpu = time.perf_counter(), time.process_time()
        try:
            return original_validate(*args, **kwargs)
        finally:
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
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        tokens = engine.reconcile_set((), current)
        reconcile_wall = time.perf_counter() - wall
        reconcile_cpu = time.process_time() - cpu
    finally:
        module.project_path = original_project
        module.os.scandir = original_scandir
    assert len(tokens) == plans and all(tokens)
    return {
        "retained_claims": claims,
        "current_plans": plans,
        "seed_wall_seconds": seed_wall,
        "seed_cpu_seconds": seed_cpu,
        "validation_wall_seconds": validation_wall,
        "validation_cpu_seconds": validation_cpu,
        "reconcile_wall_seconds": reconcile_wall,
        "reconcile_cpu_seconds": reconcile_cpu,
        **counts,
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
    args = parser.parse_args()
    if (
        any(not 0 <= value <= 500 for value in args.claims)
        or any(not 1 <= value <= 16 for value in args.plans)
        or not 1 <= args.repeat <= 20
    ):
        parser.error("expected 0..500 claims, 1..16 plans, and 1..20 repetitions")
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
        "platform": platform.platform(),
        "python": platform.python_version(),
        "coordinator_sha256": {
            label: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
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
                        **_sample(modules[label], sample_work, claims, plans),
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
