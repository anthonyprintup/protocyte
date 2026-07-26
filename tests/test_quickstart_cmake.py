from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = ROOT / "examples" / "quickstart"


def _fake_tool(directory: Path, name: str, *, output: str, exit_code: int = 0) -> Path:
    if os.name == "nt":
        path = directory / f"{name}.cmd"
        path.write_text(
            f"@echo off\r\necho {output}\r\nexit /b {exit_code}\r\n",
            encoding="utf-8",
        )
    else:
        path = directory / name
        path.write_text(
            f"#!/bin/sh\nprintf '%s\\n' '{output}'\nexit {exit_code}\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
    return path


def _configure(
    tmp_path: Path,
    *,
    protoc_output: str = "libprotoc 33.0",
    protoc_exit: int = 0,
    plugin_output: str = "0.1.0",
    plugin_exit: int = 0,
) -> subprocess.CompletedProcess[str]:
    tools = tmp_path / "tools"
    tools.mkdir()
    protoc = _fake_tool(tools, "protoc", output=protoc_output, exit_code=protoc_exit)
    plugin = _fake_tool(
        tools,
        "protoc-gen-protocyte",
        output=plugin_output,
        exit_code=plugin_exit,
    )

    return subprocess.run(
        [
            "cmake",
            "-S",
            str(QUICKSTART),
            "-B",
            str(tmp_path / "build"),
            f"-DPROTOC_EXECUTABLE={protoc}",
            f"-DPROTOCYTE_PLUGIN_EXECUTABLE={plugin}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.skipif(shutil.which("cmake") is None, reason="CMake is not available")
def test_quickstart_probes_both_tool_versions_during_configure(tmp_path: Path) -> None:
    result = _configure(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "Using protoc:" in output
    assert "libprotoc 33.0" in output
    assert "Using protoc-gen-protocyte:" in output
    assert "0.1.0" in output


@pytest.mark.skipif(shutil.which("cmake") is None, reason="CMake is not available")
@pytest.mark.parametrize(
    ("arguments", "tool_name", "variable", "reported"),
    [
        ({"protoc_output": "not protoc"}, "protoc", "PROTOC_EXECUTABLE", "not protoc"),
        (
            {"plugin_output": "not protocyte"},
            "protoc-gen-protocyte",
            "PROTOCYTE_PLUGIN_EXECUTABLE",
            "not protocyte",
        ),
    ],
)
def test_quickstart_rejects_unrecognized_tool_versions(
    tmp_path: Path,
    arguments: dict[str, str],
    tool_name: str,
    variable: str,
    reported: str,
) -> None:
    result = _configure(tmp_path, **arguments)

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert f"selected {tool_name} executable returned an unrecognized version" in output
    assert variable in output
    assert reported in output


@pytest.mark.skipif(shutil.which("cmake") is None, reason="CMake is not available")
@pytest.mark.parametrize(
    ("arguments", "tool_name", "variable", "exit_code"),
    [
        ({"protoc_exit": 17}, "protoc", "PROTOC_EXECUTABLE", 17),
        (
            {"plugin_exit": 23},
            "protoc-gen-protocyte",
            "PROTOCYTE_PLUGIN_EXECUTABLE",
            23,
        ),
    ],
)
def test_quickstart_reports_non_runnable_tools_at_configure_time(
    tmp_path: Path,
    arguments: dict[str, int],
    tool_name: str,
    variable: str,
    exit_code: int,
) -> None:
    result = _configure(tmp_path, **arguments)

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert f"could not run '{tool_name} --version'" in output
    assert variable in output
    assert f"Result: {exit_code}" in output
