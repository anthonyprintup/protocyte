"""Standalone output-registry scaling/progress POC; Python 3.12+, stdlib only.

Run from a Protocyte checkout. All state lives in a NEW synthetic workspace;
the default/shared registry and source checkout are never modified.
Fixtures are retained locally. Publish only this script and results.json,
not the synthetic claim files (which necessarily contain local paths).

From issue #54. The measured sample method is unchanged. Progress metadata
supports a reporter without a lifetime cap; the encoding lambda is spelled as
a function for repository lint. The original issue remains the baseline source.
Counters also include optional Windows attribute probes and native existence
queries so cheaper metadata cannot masquerade as eliminating FS observations.
"""

from __future__ import annotations

import argparse
import contextlib
import cProfile
import hashlib
import importlib.util
import io
import json
import os
import platform
import pstats
import re
import sys
import tempfile
import time
from pathlib import Path


def load(path):
    spec = importlib.util.spec_from_file_location("coordinator_poc", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def plan(module, work, name):
    directory = work / name
    build = directory / "build"
    build.mkdir(parents=True)
    root = directory / "generated"
    target = hashlib.sha256(name.encode()).hexdigest()
    staging = directory / (".protocyte-generation-staging-" + target)

    def encoded(value):
        return os.fspath(value).encode("utf-8").hex()

    path = directory / "outputs.plan"
    path.write_text(
        "\n".join(
            [
                module.PLAN_HEADER,
                "root-hex=" + encoded(root),
                "build-root-hex=" + encoded(build),
                "target=" + target + "|" + encoded(staging),
                "output=" + target + "|" + encoded("sample.protocyte.hpp"),
            ]
        )
        + "\n",
        encoding="ascii",
    )
    return module.Plan.read(path)


def sample(
    module, work, retained_count, current_count, registry_validation="reference"
):
    setup_start = time.perf_counter()
    retained = [plan(module, work, "retained-%04d" % i) for i in range(retained_count)]
    current = [plan(module, work, "current-%04d" % i) for i in range(current_count)]
    engine = (
        module.OutputCoordinator(work / "isolated-registry")
        if registry_validation == "reference"
        else module.OutputCoordinator(
            work / "isolated-registry", registry_validation=registry_validation
        )
    )

    # Fixture seeding only: avoid quadratic conflict comparisons during setup.
    # Use real initialization/reconciliation helpers under PRIVATE locks.
    # No method is replaced during seeding; all roots/targets are disjoint.
    module._durable_mkdir(engine.lock_root)
    with module.FileLock(engine.lock_root / "registry.lock"):
        for item in retained:
            with (
                module.FileLock(engine._generation_lock(item.root)),
                module.FileLock(engine._publication_lock(item.root)),
            ):
                state = engine._state_directory(item.root)
                engine._initialize_claim_locked(state, item)
                engine._reconcile_locked(state, item)
    setup_seconds = time.perf_counter() - setup_start

    active = False
    counts = {}
    originals = {}
    profile = cProfile.Profile()
    validation_wall = validation_cpu = 0.0
    original_validate = engine._validate_registry

    def validate(*args, **kwargs):
        nonlocal active, validation_wall, validation_cpu
        counts["registry_validations"] = counts.get("registry_validations", 0) + 1
        active = True
        wall, cpu = time.perf_counter(), time.process_time()
        profile.enable()
        try:
            return original_validate(*args, **kwargs)
        finally:
            profile.disable()
            validation_wall += time.perf_counter() - wall
            validation_cpu += time.process_time() - cpu
            active = False

    names = (
        "project_path",
        "_paths_overlap",
        "_path_key",
        "_physical_location_key",
        "_same_physical_path",
        "_windows_file_attributes",
    )
    for name in names:
        if not hasattr(module, name):
            continue
        original = getattr(module, name)
        originals[name] = original

        def counted(*args, _name=name, _original=original, **kwargs):
            if active:
                counts[_name] = counts.get(_name, 0) + 1
            return _original(*args, **kwargs)

        setattr(module, name, counted)
    engine._validate_registry = validate
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        # This is the measured production operation, with every check,
        # filesystem call, and lock delegated unchanged.
        tokens = engine.reconcile_set((), current)
    finally:
        reconcile_wall = time.perf_counter() - wall
        reconcile_cpu = time.process_time() - cpu
        engine._validate_registry = original_validate
        for name, original in originals.items():
            setattr(module, name, original)
    assert len(tokens) == current_count and all(tokens)

    filesystem = {}
    for (_, _, name), (_, calls, own, _, _) in pstats.Stats(profile).stats.items():
        for operation in (
            "nt.stat",
            "nt.lstat",
            "nt._getfinalpathname",
            "nt._path_lexists",
        ):
            if name == "<built-in method %s>" % operation:
                filesystem[operation] = {
                    "calls": calls,
                    "own_seconds": round(own, 6),
                }
        if name == "_windows_file_attributes":
            filesystem["windows_attribute_probes"] = {
                "calls": calls,
                "own_seconds": round(own, 6),
            }
    return {
        "retained_claims": retained_count,
        "current_plans": current_count,
        "setup_seconds": round(setup_seconds, 6),
        "validation_wall_seconds": round(validation_wall, 6),
        "validation_cpu_seconds": round(validation_cpu, 6),
        "reconcile_wall_seconds": round(reconcile_wall, 6),
        "reconcile_cpu_seconds": round(reconcile_cpu, 6),
        "validation_operation_counts": counts,
        "validation_filesystem_calls": filesystem,
        "completed_plans": len(tokens),
        "validation_engine": registry_validation,
        "index_experiment": getattr(engine, "validation_metrics", {}),
    }


def progress_demo(module):
    """Demonstrate the cutoff quickly; only the reporting interval is scaled."""
    original_interval = module._ReconcileProgress.INTERVAL_SECONDS
    max_reports = getattr(module._ReconcileProgress, "MAX_REPORTS", None)
    stream = io.StringIO()
    try:
        module._ReconcileProgress.INTERVAL_SECONDS = 0.01
        with contextlib.redirect_stderr(stream):
            with module._ReconcileProgress(1, 0) as progress:
                progress.phase("validating registry", "validation")
                progress.registry(states=100)
                for _ in range(40):
                    progress.registry(claim=True)
                    time.sleep(0.01)
    finally:
        module._ReconcileProgress.INTERVAL_SECONDS = original_interval
    lines = stream.getvalue().splitlines()
    periodic = [line for line in lines if ": complete;" not in line]
    last = periodic[-1] if periodic else ""
    match = re.search(r"claims_checked=(\d+)", last)
    return {
        "production_interval_seconds": original_interval,
        "production_max_periodic_reports": max_reports,
        "nominal_production_cutoff_seconds": (
            original_interval * max_reports if max_reports is not None else None
        ),
        "demo_interval_seconds": 0.01,
        "periodic_reports": len(periodic),
        "claims_at_last_periodic_report": int(match[1]) if match else None,
        "claims_at_completion": progress._claims,
        "suppression_message_seen": "further progress suppressed" in last,
        "completion_message_seen": any(": complete;" in line for line in lines),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coordinator",
        type=Path,
        default=Path("cmake/ProtocyteOutputCoordinator.py"),
    )
    parser.add_argument("--claims", type=int, nargs="+", default=[0, 8, 16])
    parser.add_argument("--plans", type=int, nargs="+", default=[1, 11])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--work", type=Path)
    parser.add_argument(
        "--registry-validation",
        choices=("reference", "shadow", "native-shadow"),
        default="reference",
    )
    args = parser.parse_args()
    if (
        any(not 0 <= n <= 4096 for n in args.claims)
        or any(not 1 <= n <= 32 for n in args.plans)
        or not 1 <= args.repeat <= 10
    ):
        parser.error("expected 0..4096 claims, 1..32 plans, 1..10 repetitions")
    source = args.coordinator.resolve(strict=True)
    module = load(source)
    if args.work:
        root = args.work.absolute()
        root.mkdir(parents=True, exist_ok=False)
    else:
        root = Path(tempfile.mkdtemp(prefix="protocyte-registry-poc-"))
    root = root.resolve(strict=True)
    result = {
        "os": platform.system(),
        "python": platform.python_version(),
        "coordinator_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "implementation_files": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                source,
                source.with_name("ProtocyteOwnershipIndex.py"),
                source.with_name("ProtocytePathObservation.py"),
            )
            if path.is_file()
        },
        "timings_include_instrumentation": True,
        "samples": [],
    }
    for repetition in range(args.repeat):
        for claims in args.claims:
            for plans in args.plans:
                work = root / ("r%d-c%d-p%d" % (repetition, claims, plans))
                row = {
                    "repetition": repetition,
                    **sample(module, work, claims, plans, args.registry_validation),
                }
                observed_files = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (
                        source,
                        source.with_name("ProtocyteOwnershipIndex.py"),
                        source.with_name("ProtocytePathObservation.py"),
                    )
                    if path.is_file()
                }
                if observed_files != result["implementation_files"]:
                    raise RuntimeError(
                        "coordinator sources changed during the POC; discard timings"
                    )
                result["samples"].append(row)
                print(json.dumps(row), flush=True)
    result["progress_demo"] = progress_demo(module)
    (root / "results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["progress_demo"]), flush=True)


if __name__ == "__main__":
    main()
