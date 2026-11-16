"""Offline, disjoint registry phase timings using fresh synthetic fixtures.

Python 3.12+, stdlib only. This reuses benchmark_output_registry's real locked
fixture seeding and unchanged measured reconcile_set operation. Timers delegate
every check; nested calls belong only to their outermost measured phase.
Publish results.json only, never synthetic claim records or fixture directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import Any

from benchmark_output_registry import _load, _sample


def profile(module: ModuleType, work: Path, claims: int, plans: int) -> dict[str, Any]:
    phase: str | None = None
    partition: dict[str, dict[str, float | int]] = {}

    def measured(name: str, original: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal phase
        if phase != "registry":
            return original(*args, **kwargs)
        started = time.perf_counter()
        phase = name
        try:
            return original(*args, **kwargs)
        finally:
            row = partition.setdefault(name, {"calls": 0, "wall_seconds": 0.0})
            row["calls"] += 1
            row["wall_seconds"] += time.perf_counter() - started
            phase = "registry"

    original_engine = module.OutputCoordinator
    original_claim_paths = original_engine._claim_paths
    originals = {
        name: getattr(module, name)
        for name in ("_load_json", "_paths_overlap", "_path_key", "project_path")
    }

    class InstrumentedEngine(original_engine):
        def _validate_registry(self, *args: Any, **kwargs: Any) -> Any:
            nonlocal phase
            previous, phase = phase, "registry"
            try:
                return super()._validate_registry(*args, **kwargs)
            finally:
                phase = previous

        def _load_recorded_plan(self, *args: Any, **kwargs: Any) -> Any:
            return measured(
                "recorded_plan_authentication",
                super()._load_recorded_plan,
                *args,
                **kwargs,
            )

    def claim_paths(*args: Any, **kwargs: Any) -> Any:
        return measured(
            "claim_path_authentication", original_claim_paths, *args, **kwargs
        )

    original_engine._claim_paths = staticmethod(claim_paths)
    module.OutputCoordinator = InstrumentedEngine
    for name, original in originals.items():

        def wrapper(
            *args: Any, _name: str = name, _original: Any = original, **kwargs: Any
        ) -> Any:
            return measured(_name, _original, *args, **kwargs)

        setattr(module, name, wrapper)
    try:
        sample = _sample(module, work / "sample", claims, plans)
    finally:
        original_engine._claim_paths = staticmethod(original_claim_paths)
        module.OutputCoordinator = original_engine
        for name, original in originals.items():
            setattr(module, name, original)
    # These counters confirm that the post-#52 measured scan still authenticates
    # every retained claim/plan. Instrumentation never skips foreign records.
    for name in (
        "recorded_plan_authentication",
        "claim_path_authentication",
        "_load_json",
    ):
        assert partition.get(name, {}).get("calls", 0) == claims
    return {"sample": sample, "disjoint_direct_registry_phases": partition}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=int, default=64)
    parser.add_argument("--plans", type=int, default=11)
    parser.add_argument("--work", type=Path)
    args = parser.parse_args()
    if not 0 <= args.claims <= 128 or not 1 <= args.plans <= 32:
        parser.error(
            "expected 0..128 claims and 1..32 plans; use the scaling benchmark for larger runs"
        )
    if args.work:
        work = args.work.absolute()
        work.mkdir(parents=True, exist_ok=False)
    else:
        work = Path(tempfile.mkdtemp(prefix="protocyte-registry-phases-"))
    module = _load(Path(__file__).resolve().parents[1], "phases")
    result = {
        "platform": platform.system(),
        "python": platform.python_version(),
        "coordinator_sha256": hashlib.sha256(
            Path(module.__file__).read_bytes()
        ).hexdigest(),
        "timings_include_instrumentation": True,
        "measurement": "Disjoint outermost function timers; every check delegates unchanged",
        **profile(module, work, args.claims, args.plans),
    }
    (work / "results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
