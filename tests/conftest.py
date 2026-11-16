"""Keep integration fixtures out of the user's shared ownership registry."""

from __future__ import annotations

import os
import importlib.util
import sys
from pathlib import Path

import pytest


_lock_module = None


@pytest.fixture(autouse=True)
def quiet_registry_observers(request: pytest.FixtureRequest):
    # Quiet certificate tests and default-enabled CLI subprocesses share volume
    # ancestors. Serialize *test cases*, while preserving each case's deliberate
    # worker/process concurrency. This does not alter production lock selection.
    files = {
        "test_output_coordinator.py",
        "test_ownership_index.py",
        "test_observation_commit.py",
        "test_parallel_probes.py",
        "test_path_observation.py",
        "test_consumer_registry_qualification.py",
    }
    if (
        request.node.path.name not in files
        and request.node.get_closest_marker("cmake_integration") is None
    ):
        yield
        return
    global _lock_module
    if _lock_module is None:
        source = (
            Path(__file__).resolve().parents[1] / "cmake/ProtocyteOutputCoordinator.py"
        )
        spec = importlib.util.spec_from_file_location(
            "protocyte_test_observer_lock", source
        )
        assert spec and spec.loader
        _lock_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = _lock_module
        exec(compile(source.read_bytes(), str(source), "exec"), _lock_module.__dict__)
    base = request.getfixturevalue("tmp_path_factory").getbasetemp()
    if getattr(request.config, "workerinput", None) is not None:
        base = base.parent
    with _lock_module.FileLock(base / "observation-commit-tests.lock"):
        yield


@pytest.fixture(autouse=True)
def isolated_cmake_registry_cache(
    request: pytest.FixtureRequest,
) -> None:
    if request.node.get_closest_marker("cmake_integration") is None:
        return
    # Ownership fixtures already supply explicit lock roots. Older configure
    # fixtures exercise the default selector; give that selector a private base
    # too. All subprocesses/build trees in one test still share one namespace.
    tmp_path: Path = request.getfixturevalue("tmp_path")
    monkeypatch: pytest.MonkeyPatch = request.getfixturevalue("monkeypatch")
    cache = tmp_path / "isolated-user-cache"
    cache.mkdir()
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_CACHE_HOME", str(cache)
    )
