"""Keep integration fixtures out of the user's shared ownership registry."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


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
