from __future__ import annotations

import codecs
import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".github" / "scripts" / "check_private_paths.py"
HOOKS = ROOT / ".githooks"


def _git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        input=input_bytes,
        check=True,
        capture_output=True,
    )


def _git_output(
    repository: Path, *arguments: str, input_bytes: bytes | None = None
) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        input=input_bytes,
        check=True,
        capture_output=True,
    ).stdout.strip()


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q", "--object-format=sha1")
    _git(path, "config", "user.email", "tests@example.invalid")
    _git(path, "config", "user.name", "Privacy Guard Tests")
    return path


def _run_guard(
    repository: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GUARD),
            "--repository",
            str(repository),
            *arguments,
        ],
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
    if style == "windows-forward-home":
        return "/".join(("C:", "Users", account))
    if style == "windows-backward-home":
        return "\\".join(("C:", "Users", account))
    if style == "linux-home":
        return "/" + "/".join(("home", account))
    if style == "macos-home":
        return "/" + "/".join(("Users", account))
    if style == "linux-root":
        return "/" + "/".join(("root", project, ".venv"))
    if style == "linux-root-home":
        return "/" + "root"
    if style == "windows-unc":
        return "\\".join(("", "", "synthetic-server", "Users", account, project))
    if style == "windows-unc-home":
        return "\\".join(("", "", "synthetic-server", "Users", account))
    if style == "wsl-mount":
        return "/" + "/".join(("mnt", "c", "Users", account, project))
    if style == "msys-mount":
        return "/" + "/".join(("c", "Users", account, project))
    if style == "cygwin-mount":
        return "/" + "/".join(("cygdrive", "c", "Users", account, project))
    raise AssertionError(f"unknown path style: {style}")


def _assert_redacted(result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    assert "matched path text is redacted" in result.stderr
    assert "synthetic-account" not in output
    assert "synthetic-project" not in output


def _store_blob(repository: Path, content: bytes) -> str:
    return _git_output(repository, "hash-object", "-w", "--stdin", input_bytes=content).decode(
        "ascii"
    )


def _store_tree(
    repository: Path, entries: list[tuple[bytes, bytes, str]]
) -> str:
    payload = b"".join(
        mode + b" " + name + b"\0" + bytes.fromhex(object_id)
        for mode, name, object_id in entries
    )
    return _git_output(
        repository,
        "hash-object",
        "--literally",
        "-t",
        "tree",
        "-w",
        "--stdin",
        input_bytes=payload,
    ).decode("ascii")


def _private_tree(repository: Path) -> str:
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(
        repository, [(b"100644", b"synthetic-account", blob)]
    )
    users = _store_tree(repository, [(b"40000", b"Users", account)])
    return _store_tree(repository, [(b"40000", b"C:", users)])


def _write_raw_sha1_index(repository: Path, object_id: str, path: bytes) -> None:
    header = struct.pack(">4sLL", b"DIRC", 2, 1)
    stat = struct.pack(
        ">LLLLLLLLLL", 0, 0, 0, 0, 0, 0, 0o100644, 0, 0, 0
    )
    flags = struct.pack(">H", min(len(path), 0xFFF))
    entry = stat + bytes.fromhex(object_id) + flags + path + b"\0"
    entry += b"\0" * (-len(entry) % 8)
    body = header + entry
    (repository / ".git" / "index").write_bytes(body + hashlib.sha1(body).digest())


def _install_tracked_hooks(repository: Path) -> None:
    scripts = repository / ".github" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(GUARD, scripts / GUARD.name)
    shutil.copytree(HOOKS, repository / HOOKS.name)
    _git(repository, "config", "core.hooksPath", HOOKS.name)


def _run_commit(repository: Path, message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "commit", "-qm", message],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def _stored_commit_count(repository: Path) -> int:
    object_types = _git_output(
        repository,
        "cat-file",
        "--batch-check=%(objecttype)",
        "--batch-all-objects",
        "--unordered",
    ).splitlines()
    return object_types.count(b"commit")


def test_tracked_hooks_use_portable_shell_files() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert ".githooks/* text eol=lf" in attributes
    for hook_name in ("pre-commit", "commit-msg"):
        hook = (HOOKS / hook_name).read_bytes()
        assert hook.startswith(b"#!/bin/sh\n")
        assert b"\r\n" not in hook


def test_tracked_hooks_allow_a_portable_commit(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    _install_tracked_hooks(repository)
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_commit(repository, "portable message")

    assert result.returncode == 0, result.stderr
    assert _stored_commit_count(repository) == 1


@pytest.mark.parametrize(
    "style",
    [
        "windows-forward",
        "windows-backward",
        "linux",
        "macos",
        "windows-forward-home",
        "windows-backward-home",
        "linux-home",
        "macos-home",
        "linux-root",
        "linux-root-home",
        "windows-unc",
        "windows-unc-home",
        "wsl-mount",
        "msys-mount",
        "cygwin-mount",
    ],
)
def test_guard_rejects_private_paths_in_the_tracked_index(
    tmp_path: Path, style: str
) -> None:
    repository = _repository(tmp_path / "repository")
    (repository / "fixture.txt").write_text(_private_path(style), encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_private_paths_in_raw_index_names(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    blob = _store_blob(repository, b"portable content\n")
    _write_raw_sha1_index(
        repository, blob, _private_path("windows-forward-home").encode("utf-8")
    )

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index path" in result.stderr
    _assert_redacted(result)


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
    assert "stored Git blob object" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_an_unreachable_blob_in_the_object_database(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    _store_blob(repository, _private_path("linux").encode("utf-8"))

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git blob object" in result.stderr
    _assert_redacted(result)


def test_guard_scans_binary_blobs_without_disclosing_the_match(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    private_path = _private_path("linux").encode()
    (repository / "fixture.bin").write_bytes(
        b"\x00\xffbinary\x00" + private_path + b"\x00"
    )
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize(
    ("byte_order_mark", "encoding", "prefix"),
    [
        (codecs.BOM_UTF16_LE, "utf-16-le", b""),
        (codecs.BOM_UTF16_BE, "utf-16-be", b""),
        (codecs.BOM_UTF16_LE, "utf-16-le", b"binary-prefix\x00"),
        (codecs.BOM_UTF16_BE, "utf-16-be", b"binary-prefix\x00"),
    ],
)
def test_guard_rejects_bom_marked_utf16_blobs(
    tmp_path: Path, byte_order_mark: bytes, encoding: str, prefix: bytes
) -> None:
    repository = _repository(tmp_path / "repository")
    content = prefix + byte_order_mark + _private_path("windows-forward").encode(
        encoding
    )
    (repository / "fixture.bin").write_bytes(content)
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_private_paths_in_reachable_commit_messages(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    _git(repository, "commit", "-qm", f"generated by {_private_path('linux')}")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git commit object" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_an_unreachable_commit_object(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    tree = _git_output(repository, "mktree", input_bytes=b"").decode("ascii")
    _git_output(
        repository,
        "commit-tree",
        tree,
        "-m",
        f"generated by {_private_path('linux')}",
    )

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git commit object" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_private_paths_in_reachable_annotated_tag_messages(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    _git(repository, "commit", "-qm", "add portable fixture")
    _git(repository, "tag", "-am", f"built at {_private_path('macos')}", "v1")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git tag object" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_an_unreachable_annotated_tag_object(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    target = _store_blob(repository, b"portable content\n")
    tag = b"\n".join(
        (
            f"object {target}".encode("ascii"),
            b"type blob",
            b"tag synthetic",
            b"tagger Synthetic <tests@example.invalid> 0 +0000",
            b"",
            _private_path("macos").encode("utf-8"),
            b"",
        )
    )
    _git_output(repository, "mktag", input_bytes=tag)

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git tag object" in result.stderr
    _assert_redacted(result)


def test_guard_rejects_private_paths_in_commit_or_tag_headers(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    private_identity = f"Builder {_private_path('windows-forward')}"
    _git(repository, "config", "user.name", private_identity)
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    _git(repository, "commit", "-qm", "portable commit message")
    _git(repository, "tag", "-am", "portable tag message", "v1")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git commit object" in result.stderr
    assert "stored Git tag object" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize("reachable", [False, True])
def test_guard_reconstructs_private_paths_from_stored_tree_entries(
    tmp_path: Path, reachable: bool
) -> None:
    repository = _repository(tmp_path / "repository")
    tree = _private_tree(repository)
    if reachable:
        commit = _git_output(
            repository, "commit-tree", tree, "-m", "portable commit"
        ).decode("ascii")
        _git(repository, "update-ref", "refs/heads/main", commit)

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git tree path" in result.stderr
    _assert_redacted(result)


def test_tracked_hooks_block_staged_content_before_creating_a_commit(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    _install_tracked_hooks(repository)
    fixture = repository / "fixture.txt"
    fixture.write_text(_private_path("windows-forward"), encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_commit(repository, "portable message")

    assert result.returncode == 1
    assert _git_output(repository, "rev-list", "--all", "--count") == b"0"
    assert _stored_commit_count(repository) == 0
    _assert_redacted(result)


@pytest.mark.parametrize("private_input", ["message", "identity"])
def test_tracked_hooks_block_pending_commit_metadata_before_object_creation(
    tmp_path: Path, private_input: str
) -> None:
    repository = _repository(tmp_path / "repository")
    _install_tracked_hooks(repository)
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    message = "portable message"
    if private_input == "message":
        message = f"generated by {_private_path('linux')}"
    else:
        _git(
            repository,
            "config",
            "user.name",
            f"Builder {_private_path('windows-forward')}",
        )

    result = _run_commit(repository, message)

    assert result.returncode == 1
    assert _git_output(repository, "rev-list", "--all", "--count") == b"0"
    expected_source = "message" if private_input == "message" else "metadata"
    assert f"pending commit {expected_source}" in result.stderr
    assert _stored_commit_count(repository) == 0
    _assert_redacted(result)


def test_guard_redacts_git_failures() -> None:
    missing_repository = Path(_private_path("windows-forward"))

    result = _run_guard(missing_repository)

    assert result.returncode == 2
    assert "all error details are redacted" in result.stderr
    assert "synthetic-account" not in result.stdout + result.stderr


def test_guard_accepts_portable_tracked_content_and_history(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    (repository / "fixture.txt").write_text(
        "\n".join(
            (
                "relative/path",
                "C:/Program Files/tool",
                "${HOME}/project",
                "/home",
                "C:/Users",
                r"\\synthetic-server\share\synthetic-account",
                "https://example.invalid/Users/synthetic-account",
                "https://example.invalid/mnt/c/Users/synthetic-account",
                "/home/<account>/project",
                "C:/Users/{account}/project",
                "/mnt/c/Users/{account}/project",
                "/c/Users/%USERNAME%/project",
                "/cygdrive/c/Users/<account>/project",
                r"\\synthetic-server\Users\%USERNAME%\project",
                "/rooted/project",
                "",
            )
        ),
        encoding="utf-8",
    )
    _git(repository, "add", "fixture.txt")
    _git(repository, "commit", "-qm", "add portable fixture")

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr
    assert "tracked index, stored Git objects" in result.stdout
