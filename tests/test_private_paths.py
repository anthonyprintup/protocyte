from __future__ import annotations

import codecs
import hashlib
import runpy
import shutil
import struct
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".github" / "scripts" / "check_private_paths.py"
HOOKS = ROOT / ".githooks"
LEGAL_WINDOWS_PROFILE_COMPONENTS = (
    "'alice",
    "#alice",
    "+alice",
    "a@corp",
    "a[b",
    "a]b",
    "a{b",
    "a}b",
    "a=b",
    "a,b",
    "a;b",
)
LEGAL_POSIX_PROFILE_COMPONENTS = ("a:b", "a|b", "a*b")


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
    repository: Path, *arguments: str, timeout: float | None = None
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
        timeout=timeout,
    )


def _private_path(style: str) -> str:
    account = "synthetic-account"
    project = "synthetic-project"
    if style == "windows-parenthesized-account":
        account = "synthetic " + "(" + "work" + ")"
        return "/".join(("C:", "Users", account, project))
    if style == "mounted-ampersand-account":
        account = "synthetic" + "&" + "peer"
        return "/" + "/".join(("mnt", "c", "Users", account, project))
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
    if style == "windows-extended-unc":
        return "\\".join(
            ("", "", "?", "UNC", "synthetic-server", "Users", account, project)
        )
    if style == "windows-admin-share":
        return "\\".join(
            ("", "", "synthetic-server", "C$", "Users", account, project)
        )
    if style == "wsl-mount":
        return "/" + "/".join(("mnt", "c", "Users", account, project))
    if style == "msys-mount":
        return "/" + "/".join(("c", "Users", account, project))
    if style == "cygwin-mount":
        return "/" + "/".join(("cygdrive", "c", "Users", account, project))
    raise AssertionError(f"unknown path style: {style}")


def _private_path_for_account(form: str, account: str) -> str:
    project = "synthetic-project"
    if form == "drive":
        return "/".join(("C:", "Users", account, project))
    if form == "extended-unc":
        return "\\".join(
            ("", "", "?", "UNC", "synthetic-server", "Users", account, project)
        )
    if form == "admin-share":
        return "\\".join(
            ("", "", "synthetic-server", "C$", "Users", account, project)
        )
    raise AssertionError(f"unknown path form: {form}")


def _private_posix_path(account: str) -> str:
    return "/" + "/".join(("home", account, "synthetic-project"))


def _assert_redacted(
    result: subprocess.CompletedProcess[str], *additional_secrets: str
) -> None:
    output = result.stdout + result.stderr
    assert "matched path text is redacted" in result.stderr
    assert "synthetic-account" not in output
    assert "synthetic-project" not in output
    for secret in additional_secrets:
        assert secret not in output


def _assert_hook_redacted(
    result: subprocess.CompletedProcess[str], repository: Path
) -> None:
    output = result.stdout + result.stderr
    assert "private-path guard blocked this Git operation" in result.stderr
    assert "all failure details are redacted" in result.stderr
    assert "synthetic-account" not in output
    assert "synthetic-project" not in output
    assert str(repository) not in output


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


def _private_tree_for_account(
    repository: Path, form: str, account_name: str
) -> str:
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(
        repository, [(b"100644", account_name.encode("utf-8"), blob)]
    )
    users = _store_tree(repository, [(b"40000", b"Users", account)])
    if form == "drive":
        return _store_tree(repository, [(b"40000", b"C:", users)])
    if form == "extended-unc":
        server = "\\".join(("", "", "?", "UNC", "synthetic-server"))
        return _store_tree(
            repository, [(b"40000", server.encode("utf-8"), users)]
        )
    if form == "admin-share":
        admin = _store_tree(repository, [(b"40000", b"C$", users)])
        server = "\\".join(("", "", "synthetic-server"))
        return _store_tree(
            repository, [(b"40000", server.encode("utf-8"), admin)]
        )
    raise AssertionError(f"unknown tree path form: {form}")


def _private_posix_tree(repository: Path, account_name: str) -> str:
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(
        repository, [(b"100644", account_name.encode("utf-8"), blob)]
    )
    return _store_tree(repository, [(b"40000", b"/home", account)])


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


def _install_tracked_hooks(repository: Path, *, copy_guard: bool = True) -> None:
    scripts = repository / ".github" / "scripts"
    scripts.mkdir(parents=True)
    if copy_guard:
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
    for hook_name in ("pre-commit", "commit-msg", "pre-push"):
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
        "windows-extended-unc",
        "windows-admin-share",
        "windows-parenthesized-account",
        "mounted-ampersand-account",
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


@pytest.mark.parametrize("account_name", LEGAL_WINDOWS_PROFILE_COMPONENTS)
@pytest.mark.parametrize("form", ["drive", "extended-unc", "admin-share"])
def test_guard_rejects_every_legal_profile_component_in_blob_paths(
    tmp_path: Path, form: str, account_name: str
) -> None:
    repository = _repository(tmp_path / "repository")
    private_path = _private_path_for_account(form, account_name)
    (repository / "fixture.txt").write_text(private_path, encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result, account_name)


@pytest.mark.parametrize("account_name", LEGAL_POSIX_PROFILE_COMPONENTS)
def test_guard_rejects_posix_profile_punctuation_in_blob_paths(
    tmp_path: Path, account_name: str
) -> None:
    repository = _repository(tmp_path / "repository")
    private_path = _private_posix_path(account_name)
    (repository / "fixture.txt").write_text(private_path, encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result, account_name)


def test_guard_accepts_placeholder_accounts_at_text_boundaries(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    windows_users = "/".join(("C:", "Users"))
    posix_home = "/" + "home"
    content = "\n".join(
        (
            '"' + windows_users + "/{account}" + '"',
            windows_users + "/[account])",
            '"' + posix_home + "/${USER}" + '"',
            posix_home + "/<account>,",
            posix_home + "/[account]`",
            posix_home + "/$USER/project",
            windows_users + "/$USERNAME/project",
            windows_users + "/.../project",
            posix_home + "/…/project",
            windows_users + "/{account}.",
            posix_home + "/$USER.",
            '"' + windows_users + "/{account}." + '"',
            '"' + posix_home + "/$USER." + '"',
            windows_users + "/{account}), prose",
        )
    )
    (repository / "fixture.txt").write_text(content, encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path_style", "account", "suffix"),
    [
        ("windows", "{alice}", ")/repo"),
        ("windows", "{alice}", ")evil"),
        ("windows", "$alice", ","),
        ("windows", "[alice]", ";suffix"),
        ("posix", "$alice", ")/repo"),
        ("posix", "{alice}", ",suffix"),
        ("posix", "[alice]", "`suffix"),
    ],
)
def test_guard_rejects_concrete_accounts_with_placeholder_prefixes(
    tmp_path: Path, path_style: str, account: str, suffix: str
) -> None:
    repository = _repository(tmp_path / "repository")
    if path_style == "windows":
        home = "/".join(("C:", "Users"))
    else:
        home = "/" + "home"
    private_path = home + "/" + account + suffix
    (repository / "fixture.txt").write_text(private_path, encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result, "alice")


def test_guard_does_not_treat_invalid_windows_components_as_posix_accounts(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    content = "\n".join(
        (
            "/".join(("C:", "Users", "a|b", "repo")),
            "/".join(("C:", "Users", "*", "repo")),
            "\\".join(("C:", "Users", "a|b", "repo")),
            "\\".join(("C:", "Users", "*", "repo")),
        )
    )
    (repository / "fixture.txt").write_text(content, encoding="utf-8")
    _git(repository, "add", "fixture.txt")

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr


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


@pytest.mark.parametrize("byte_phase", [0, 1])
@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_guard_rejects_bomless_utf16_at_each_byte_phase(
    tmp_path: Path, encoding: str, byte_phase: int
) -> None:
    repository = _repository(tmp_path / "repository")
    content = b"x" * byte_phase + _private_path("windows-forward").encode(
        encoding
    )
    (repository / "fixture.bin").write_bytes(content)
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize("byte_phase", [0, 1])
@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_guard_rejects_bomless_utf16_across_scan_chunk_boundaries(
    tmp_path: Path, encoding: str, byte_phase: int
) -> None:
    repository = _repository(tmp_path / "repository")
    chunk_bytes = 1024 * 1024
    path_start = chunk_bytes - 4 + byte_phase
    padding_units = (path_start - byte_phase) // 2
    padding = ("a" * (padding_units - 1) + " ").encode(encoding)
    content = (
        b"x" * byte_phase
        + padding
        + _private_path("windows-forward").encode(encoding)
    )
    assert len(b"x" * byte_phase + padding) == path_start
    (repository / "fixture.bin").write_bytes(content)
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


@pytest.mark.parametrize(
    ("first_mark", "first_encoding", "second_mark", "second_encoding"),
    [
        (codecs.BOM_UTF16_LE, "utf-16-le", codecs.BOM_UTF16_BE, "utf-16-be"),
        (codecs.BOM_UTF16_BE, "utf-16-be", codecs.BOM_UTF16_LE, "utf-16-le"),
    ],
)
def test_guard_switches_endianness_between_utf16_bom_segments(
    tmp_path: Path,
    first_mark: bytes,
    first_encoding: str,
    second_mark: bytes,
    second_encoding: str,
) -> None:
    repository = _repository(tmp_path / "repository")
    decoy = "portable segment".encode(first_encoding)
    private = _private_path("windows-forward").encode(second_encoding)
    (repository / "fixture.bin").write_bytes(
        first_mark + decoy + second_mark + private
    )
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


def test_guard_switches_utf16_endianness_across_a_scan_chunk_boundary(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    chunk_bytes = 1024 * 1024
    padding = "a" * ((chunk_bytes - 4) // 2)
    content = (
        b"x"
        + codecs.BOM_UTF16_LE
        + padding.encode("utf-16-le")
        + codecs.BOM_UTF16_BE
        + _private_path("windows-forward").encode("utf-16-be")
    )
    assert content[chunk_bytes - 1 : chunk_bytes + 1] == codecs.BOM_UTF16_BE
    (repository / "fixture.bin").write_bytes(content)
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize(
    ("byte_order_mark", "encoding", "unaligned_marker_text"),
    [
        (codecs.BOM_UTF16_LE, "utf-16-le", "\uff12\u34fe"),
        (codecs.BOM_UTF16_BE, "utf-16-be", "\u12fe\uff34"),
    ],
)
def test_guard_ignores_unaligned_bom_like_bytes_inside_utf16_text(
    tmp_path: Path,
    byte_order_mark: bytes,
    encoding: str,
    unaligned_marker_text: str,
) -> None:
    repository = _repository(tmp_path / "repository")
    content = (
        byte_order_mark
        + unaligned_marker_text.encode(encoding)
        + _private_path("windows-forward").encode(encoding)
    )
    (repository / "fixture.bin").write_bytes(content)
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize(
    ("byte_order_mark", "encoding"),
    [
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ],
)
def test_guard_preserves_utf16_content_across_aligned_opposite_bom_bytes(
    tmp_path: Path, byte_order_mark: bytes, encoding: str
) -> None:
    repository = _repository(tmp_path / "repository")
    content = (
        byte_order_mark
        + "\ufffe".encode(encoding)
        + _private_path("windows-forward").encode(encoding)
    )
    (repository / "fixture.bin").write_bytes(content)
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize(
    ("byte_order_mark", "encoding"),
    [
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ],
)
def test_guard_starts_same_endian_utf16_segments_at_the_opposite_byte_phase(
    tmp_path: Path, byte_order_mark: bytes, encoding: str
) -> None:
    repository = _repository(tmp_path / "repository")
    content = (
        byte_order_mark
        + "portable".encode(encoding)
        + b"x"
        + byte_order_mark
        + _private_path("windows-forward").encode(encoding)
    )
    (repository / "fixture.bin").write_bytes(content)
    _git(repository, "add", "fixture.bin")

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "tracked index blob" in result.stderr
    _assert_redacted(result)


@pytest.mark.parametrize(
    ("byte_order_mark", "encoding"),
    [
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ],
)
def test_guard_finds_opposite_phase_utf16_boms_split_across_scan_chunks(
    tmp_path: Path, byte_order_mark: bytes, encoding: str
) -> None:
    repository = _repository(tmp_path / "repository")
    chunk_bytes = 1024 * 1024
    padding = "a" * ((chunk_bytes - 4) // 2)
    content = (
        byte_order_mark
        + padding.encode(encoding)
        + b"x"
        + byte_order_mark
        + _private_path("windows-forward").encode(encoding)
    )
    assert content[chunk_bytes - 1 : chunk_bytes + 1] == byte_order_mark
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


def test_guard_streams_large_commits_with_bounded_python_memory(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    root_tree = _git_output(repository, "mktree", input_bytes=b"").decode("ascii")
    payload = (
        b"tree "
        + root_tree.encode("ascii")
        + b"\n\n"
        + b"x" * (16 * 1024 * 1024)
    )
    commit = _git_output(
        repository,
        "hash-object",
        "--literally",
        "-t",
        "commit",
        "-w",
        "--stdin",
        input_bytes=payload,
    ).decode("ascii")
    del payload
    guard_module = runpy.run_path(str(GUARD))

    tracemalloc.start()
    try:
        violations, trees, commit_trees = guard_module["_scan_stored_objects"](
            repository
        )
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert commit not in violations
    assert root_tree in trees
    assert root_tree in commit_trees
    assert peak_bytes < 24 * 1024 * 1024


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


@pytest.mark.parametrize("account_name", LEGAL_WINDOWS_PROFILE_COMPONENTS)
@pytest.mark.parametrize("form", ["drive", "extended-unc", "admin-share"])
def test_guard_rejects_every_legal_profile_component_in_stored_tree_paths(
    tmp_path: Path, form: str, account_name: str
) -> None:
    repository = _repository(tmp_path / "repository")
    _private_tree_for_account(repository, form, account_name)

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git tree path" in result.stderr
    _assert_redacted(result, account_name)


@pytest.mark.parametrize("account_name", LEGAL_POSIX_PROFILE_COMPONENTS)
def test_guard_rejects_posix_profile_punctuation_in_stored_tree_paths(
    tmp_path: Path, account_name: str
) -> None:
    repository = _repository(tmp_path / "repository")
    _private_posix_tree(repository, account_name)

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git tree path" in result.stderr
    _assert_redacted(result, account_name)


def test_guard_does_not_reinterpret_windows_drive_tails_in_stored_trees(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(repository, [(b"100644", b"a|b", blob)])
    users = _store_tree(repository, [(b"40000", b"Users", account)])
    drive = _store_tree(repository, [(b"40000", b"c", users)])
    _store_tree(repository, [(b"40000", b"C$", drive)])

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr


def test_guard_preserves_mounted_account_separator_rules_in_stored_trees(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(
        repository, [(b"100644", b"\\" + b"server", blob)]
    )
    users = _store_tree(repository, [(b"40000", b"Users", account)])
    drive = _store_tree(repository, [(b"40000", b"c", users)])
    placeholder = b"{" + b"account" + b"}"
    _store_tree(repository, [(b"40000", placeholder, drive)])

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr


def test_guard_scans_shared_tree_dags_in_polynomial_time(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    blob = _store_blob(repository, b"portable content\n")
    shared_tree = _store_tree(repository, [(b"100644", b"leaf", blob)])
    for _ in range(23):
        shared_tree = _store_tree(
            repository,
            [
                (b"40000", b"left", shared_tree),
                (b"40000", b"right", shared_tree),
            ],
        )

    started = time.perf_counter()
    result = _run_guard(repository, timeout=8.0)
    elapsed = time.perf_counter() - started

    assert result.returncode == 0, result.stderr
    assert elapsed < 8.0


def test_guard_keeps_distinct_path_states_for_a_shared_subtree(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(
        repository, [(b"100644", b"synthetic-account", blob)]
    )
    shared = _store_tree(repository, [(b"40000", b"Users", account)])
    _store_tree(
        repository,
        [
            (b"40000", b"C:", shared),
            (b"40000", b"portable", shared),
        ],
    )

    result = _run_guard(repository)

    assert result.returncode == 1
    assert "stored Git tree path" in result.stderr
    _assert_redacted(result)


def test_guard_does_not_promote_a_nested_unc_like_tree_name_to_a_root(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    blob = _store_blob(repository, b"portable content\n")
    account = _store_tree(repository, [(b"100644", b"alice", blob)])
    users = _store_tree(repository, [(b"40000", b"Users", account)])
    unc_like_name = "\\".join(("", "", "server")).encode("utf-8")
    unc_like = _store_tree(
        repository, [(b"40000", unc_like_name, users)]
    )
    _store_tree(repository, [(b"40000", b"ordinary", unc_like)])

    result = _run_guard(repository)

    assert result.returncode == 0, result.stderr


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
    _assert_hook_redacted(result, repository)


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
    assert _stored_commit_count(repository) == 0
    _assert_hook_redacted(result, repository)


def test_commit_hook_rejects_a_private_commit_encoding_header(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "repository")
    _install_tracked_hooks(repository)
    _git(repository, "config", "i18n.commitEncoding", _private_path("linux"))
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    message_file = repository / "message.txt"
    message_file.write_text("portable message\n", encoding="utf-8")

    direct_result = _run_guard(
        repository, "--commit-message", str(message_file)
    )
    commit_result = _run_commit(repository, "portable message")

    assert direct_result.returncode == 1
    assert "pending commit encoding header" in direct_result.stderr
    _assert_redacted(direct_result)
    assert commit_result.returncode == 1
    assert _stored_commit_count(repository) == 0
    _assert_hook_redacted(commit_result, repository)


@pytest.mark.parametrize("failure", ["missing", "syntax"])
def test_commit_hooks_fail_closed_without_raw_python_diagnostics(
    tmp_path: Path, failure: str
) -> None:
    repository = _repository(tmp_path / "repository")
    _install_tracked_hooks(repository, copy_guard=failure != "missing")
    guard = repository / ".github" / "scripts" / GUARD.name
    if failure == "syntax":
        guard.write_text("def broken(:\n", encoding="utf-8")
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "--all")

    result = _run_commit(repository, "portable message")

    assert result.returncode == 1
    assert _stored_commit_count(repository) == 0
    _assert_hook_redacted(result, repository)
    assert GUARD.name not in result.stdout + result.stderr


def test_pre_push_hook_rejects_a_finalized_signer_header(tmp_path: Path) -> None:
    repository = _repository(tmp_path / "repository")
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(remote)],
        check=True,
        capture_output=True,
    )
    _install_tracked_hooks(repository)
    (repository / "fixture.txt").write_text("portable content\n", encoding="utf-8")
    _git(repository, "add", "fixture.txt")
    assert _run_commit(repository, "portable message").returncode == 0
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "-q", "origin", "HEAD:refs/heads/main")

    parent = _git_output(repository, "rev-parse", "HEAD").decode("ascii")
    tree = _git_output(repository, "rev-parse", "HEAD^{tree}").decode("ascii")
    identity = b"Synthetic <tests@example.invalid> 0 +0000"
    commit_payload = b"\n".join(
        (
            f"tree {tree}".encode("ascii"),
            f"parent {parent}".encode("ascii"),
            b"author " + identity,
            b"committer " + identity,
            b"gpgsig -----BEGIN SYNTHETIC SIGNATURE-----",
            b" " + _private_path("linux").encode("utf-8"),
            b" -----END SYNTHETIC SIGNATURE-----",
            b"",
            b"portable message",
            b"",
        )
    )
    finalized = _git_output(
        repository,
        "hash-object",
        "--literally",
        "-t",
        "commit",
        "-w",
        "--stdin",
        input_bytes=commit_payload,
    ).decode("ascii")
    _git(repository, "update-ref", "HEAD", finalized, parent)

    result = subprocess.run(
        ["git", "push", "-q", "origin", "HEAD:refs/heads/main"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert _git_output(remote, "rev-parse", "refs/heads/main") == parent.encode(
        "ascii"
    )
    _assert_hook_redacted(result, repository)


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
                "/home/[account]/project",
                "/home/${USER}/project",
                "C:/Users/{account}/project",
                "/mnt/c/Users/{account}/project",
                "/c/Users/%USERNAME%/project",
                "/cygdrive/c/Users/<account>/project",
                r"\\synthetic-server\Users\%USERNAME%\project",
                "\\".join(
                    (
                        "",
                        "",
                        "?",
                        "UNC",
                        "synthetic-server",
                        "Users",
                        "%USERNAME%",
                        "project",
                    )
                ),
                "\\".join(
                    (
                        "",
                        "",
                        "synthetic-server",
                        "C$",
                        "Users",
                        "{account}",
                        "project",
                    )
                ),
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
