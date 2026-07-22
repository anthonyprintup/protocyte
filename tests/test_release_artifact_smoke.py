from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "test_release_plugin_artifact.py"
SPEC = importlib.util.spec_from_file_location(
    "test_release_plugin_artifact", SCRIPT_PATH
)
assert SPEC is not None and SPEC.loader is not None
test_release_plugin_artifact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(test_release_plugin_artifact)


def test_release_plugin_artifact_runner_enforces_offline_install(
    tmp_path: Path,
    monkeypatch,
) -> None:
    test_root = tmp_path / "smoke"
    artifact = tmp_path / "publication" / "protocyte.whl"
    cmake = tmp_path / "tools" / "cmake"
    ctest = tmp_path / "tools" / "ctest"
    protoc = tmp_path / "tools" / "protoc"
    calls: list[tuple[tuple[str, ...], Path, dict[str, str]]] = []

    def record_run(
        command: tuple[str, ...],
        *,
        check: bool,
        cwd: Path,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[tuple[str, ...]]:
        assert check is True
        calls.append((command, cwd, env))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("PIP_INDEX_URL", "https://mutable.invalid/simple")
    monkeypatch.setenv("PIP_REQUIREMENT", str(tmp_path / "injected.txt"))
    monkeypatch.setenv("UV_INDEX", "https://mutable.invalid/simple")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "injected-python"))
    monkeypatch.setattr(test_release_plugin_artifact.subprocess, "run", record_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--artifact",
            str(artifact),
            "--cmake",
            str(cmake),
            "--ctest",
            str(ctest),
            "--protoc",
            str(protoc),
            "--test-root",
            str(test_root),
        ],
    )

    test_release_plugin_artifact.main()

    install, install_cwd, install_env = calls[0]
    assert install[:6] == (
        str(test_root / "venv" / "bin" / "python"),
        "-I",
        "-m",
        "pip",
        "--isolated",
        "install",
    )
    assert {
        "--no-cache-dir",
        "--no-index",
        "--no-deps",
        "--no-build-isolation",
    } <= set(install)
    assert install[-1] == str(artifact)
    assert install_cwd == test_root
    assert install_env["PIP_CONFIG_FILE"] == os.devnull
    assert install_env["PIP_NO_INDEX"] == "1"
    assert install_env["UV_NO_INDEX"] == "1"
    assert install_env["UV_OFFLINE"] == "1"
    assert "PIP_INDEX_URL" not in install_env
    assert "PIP_REQUIREMENT" not in install_env
    assert "UV_INDEX" not in install_env
    assert "PYTHONPATH" not in install_env
    assert all(call_cwd == test_root for _, call_cwd, _ in calls)
    assert all(call_env == install_env for _, _, call_env in calls)
    assert all(command[0] != "uv" for command, _, _ in calls)
    assert any(
        command[0] == str(cmake) and "--build" in command for command, _, _ in calls
    )
    assert any(command[0] == str(ctest) for command, _, _ in calls)


def test_release_cmake_hash_lock_rejects_substituted_wheel(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "cmake-4.3.2-py3-none-any.whl").write_bytes(
        b"substituted release tool"
    )
    environment = tmp_path / "environment"
    subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    result = subprocess.run(
        [
            str(python),
            "-I",
            "-m",
            "pip",
            "--isolated",
            "download",
            "--disable-pip-version-check",
            "--no-input",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "--no-deps",
            "--only-binary=:all:",
            "--require-hashes",
            "--requirement",
            str(REPO_ROOT / ".github" / "release-cmake-constraints.txt"),
            "--dest",
            str(tmp_path / "download"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "do not match the hashes" in output.casefold()
    assert "339655b93289c1b03c6a72523d46d3b0d19dc51406d3a90f8eefcbec525cb271" in output
