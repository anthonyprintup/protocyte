import builtins
import importlib.util
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest


_HELPER = Path(__file__).resolve().parents[1] / "cmake/ProtocyteCreateEnvironment.py"
_SPEC = importlib.util.spec_from_file_location("protocyte_create_environment", _HELPER)
assert _SPEC is not None and _SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bootstrap)


@pytest.mark.parametrize("as_bytes", [False, True])
def test_bootstrap_diagnostics_are_sanitized_and_bounded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], as_bytes: bool
) -> None:
    output = (
        "first diagnostic\n"
        "https://user:password@example.invalid/private-token?key=query-secret\n"
        "https://user:quoted'password@example.invalid/index\n"
        "https://example.invalid/"
        + "token" * 5000
        + "\n"
        + "noise\n" * 5000
        + "last diagnostic\n"
    )
    error_output = "stderr detail\nHTTPS://other:secret@example.invalid/index\n\x1b\x00"

    def fail() -> None:
        raise subprocess.CalledProcessError(
            17,
            ["command-must-not-leak"],
            output=output.encode() if as_bytes else output,
            stderr=error_output.encode() + b"\xff" if as_bytes else error_output,
        )

    monkeypatch.setattr(venv, "main", fail)
    assert bootstrap.main() == 17
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "exit code 17" in captured.err
    assert "first diagnostic" in captured.err
    assert "last diagnostic" in captured.err
    assert "stderr detail" in captured.err
    assert "bootstrap diagnostic truncated" in captured.err
    assert "<redacted URL>" in captured.err
    assert len(captured.err) < 17 * 1024
    for private in (
        "password",
        "quoted",
        "private-token",
        "query-secret",
        "token",
        "other:secret",
        "example.invalid",
        "command-must-not-leak",
        "\x1b",
        "\x00",
    ):
        assert private not in captured.err


def test_missing_venv_is_reported_separately(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original_import = builtins.__import__

    def without_venv(name, *args, **kwargs):
        if name == "venv":
            raise ModuleNotFoundError("No module named 'venv'", name="venv")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_venv)
    assert bootstrap.main() == 1
    captured = capsys.readouterr()
    assert "ModuleNotFoundError: No module named 'venv'" in captured.err
    assert "bootstrap subprocess failed" not in captured.err


def test_create_environment_preserves_venv_defaults(tmp_path: Path) -> None:
    destination = tmp_path / "environment with spaces"
    environment = os.environ.copy()
    environment.update(
        PIP_NO_INDEX="1",
        PIP_CONFIG_FILE=os.devnull,
        PYTHONHOME=str(tmp_path / "invalid-home"),
        PYTHONPATH=str(tmp_path / "invalid-import-path"),
    )
    result = subprocess.run(
        [sys.executable, "-I", str(_HELPER), str(destination)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    python = destination / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    probe = subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import pip, sys; print(sys.prefix); print(sys.base_prefix); print(pip.__file__)",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
    )
    prefix, base, pip_path = probe.stdout.splitlines()
    assert Path(prefix).resolve() == destination.resolve()
    assert Path(base).resolve() == Path(sys.base_prefix).resolve()
    assert Path(pip_path).is_relative_to(destination)
    assert "include-system-site-packages = false" in (
        destination / "pyvenv.cfg"
    ).read_text(encoding="utf-8")
    assert python.is_symlink() == (os.name != "nt")
    assert (python.parent / "activate").is_file()
    if sys.version_info >= (3, 13):
        assert (destination / ".gitignore").is_file()
