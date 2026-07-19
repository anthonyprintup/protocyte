from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".github" / "scripts" / "check_private_paths.py"


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True)


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "tests@example.invalid")
    _git(path, "config", "user.name", "Privacy Guard Tests")
    return path


def _run_guard(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GUARD), "--repository", str(repository)],
        check=False,
        capture_output=True,
        text=True,
    )


def _private_path(style: str) -> str:
    account = "synthetic-account"
    project = "synthetic-project"
    if style == "windows-forward":
        return "/".join(("C:", "Users", account, "Desktop", project, ".venv"))
    if style == "windows-backward":
        return "\\".join(("C:", "Users", account, "Desktop", project, ".venv"))
    if style == "linux":
        return "/" + "/".join(("home", account, "work", project, ".venv"))
    if style == "macos":
        return "/" + "/".join(("Users", account, "work", project, ".venv"))
    raise AssertionError(f"unknown path style: {style}")


@pytest.mark.parametrize(
    "style", ["windows-forward", "windows-backward", "linux", "macos"]
)
def test_guard_rejects_private_paths_in_the_tracked_index(
    tmp_path: Path, style: str
) -> None:
    repository = _repository(tmp_path / "repository")
    (repository / "fixture.txt").write_text(_private_path(style), encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index" in result.stderr
    assert "matched path text is redacted" in result.stderr
    assert "synthetic-account" not in result.stdout + result.stderr


def test_guard_rejects_a_removed_private_path_still_reachable_in_history(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    fixture = repository / "fixture.txt"
    fixture.write_text(_private_path("windows-forward"), encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    _git(repository, "commit", "-qm", "add fixture")
    fixture.write_text("portable content\n", encoding="utf-8")
    _git(repository, "commit", "-qam", "remove private path")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "reachable Git history" in result.stderr
    assert "synthetic-account" not in result.stdout + result.stderr


def test_guard_scans_binary_blobs_without_disclosing_the_match(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    private_path = _private_path("linux").encode()
    (repository / "fixture.bin").write_bytes(
        b"\x00\xffbinary\x00" + private_path + b"\x00"
    )
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index" in result.stderr
    assert "matched path text is redacted" in result.stderr
    assert "synthetic-account" not in result.stdout + result.stderr


def test_guard_accepts_portable_tracked_content_and_history(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    (repository / "fixture.txt").write_text(
        "relative/path\nC:/Program Files/tool\n${HOME}/project\n", encoding="utf-8"
    )
    _git(repository, "add", "fixture.txt")
    _git(repository, "commit", "-qm", "add portable fixture")

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr
    assert "tracked index and reachable history are clean" in result.stdout
