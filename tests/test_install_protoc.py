import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest


def _load_install_protoc_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "scripts"
        / "install_protoc.py"
    )
    spec = importlib.util.spec_from_file_location("install_protoc", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install_protoc = _load_install_protoc_module()
owned_transactions = sys.modules[install_protoc.locked_destination.__module__]


def test_windows_child_open_access_mask_is_lazy() -> None:
    assert owned_transactions._windows_open_child_handle.__kwdefaults__ == {
        "access": None
    }


def _owner_journal_payload(owner: object) -> dict[str, object]:
    return owned_transactions._read_latest_journal_payload(
        owner.marker_path,
        owner.destination,
        owner.kind,
        owner.token,
    )


def _marker_journal_payload(
    marker_path: Path,
    destination: Path,
) -> dict[str, object]:
    match = re.fullmatch(r"([a-z][a-z0-9-]*)\.([0-9a-f]{32})\.owner", marker_path.name)
    assert match is not None
    return owned_transactions._read_latest_journal_payload(
        marker_path,
        destination,
        match.group(1),
        match.group(2),
    )


def test_default_transaction_state_directory_is_per_user_and_private(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )

    state_directory = owned_transactions._state_directory()

    assert state_directory.parent == tmp_path
    assert state_directory.name.startswith(
        owned_transactions._STATE_DIRECTORY_NAME + "-"
    )
    assert state_directory.name != owned_transactions._STATE_DIRECTORY_NAME
    if os.name != "nt":
        assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700


def test_default_state_root_uses_canonical_trusted_temp_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_alias = tmp_path / "platform-temp-alias"
    canonical_temp = tmp_path / "canonical-platform-temp"
    canonical_temp.mkdir()
    original_resolve = Path.resolve

    def resolve_temp_alias(path: Path, *, strict: bool = False) -> Path:
        if path == temp_alias:
            assert strict
            return canonical_temp
        return original_resolve(path, strict=strict)

    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(temp_alias),
    )
    monkeypatch.setattr(Path, "resolve", resolve_temp_alias)

    state_directory = owned_transactions._absolute_state_directory(None)

    assert state_directory.parent == canonical_temp
    assert not temp_alias.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX platform temp symlink check")
def test_default_state_root_accepts_symlinked_platform_temp_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_temp = tmp_path / "canonical-platform-temp"
    canonical_temp.mkdir()
    temp_alias = tmp_path / "platform-temp-alias"
    temp_alias.symlink_to(canonical_temp, target_is_directory=True)
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(temp_alias),
    )

    state_directory = owned_transactions._state_directory()

    assert state_directory.parent == canonical_temp
    assert state_directory.is_dir()
    assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700


def test_transaction_state_metadata_is_private_and_redacts_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "home" / "account" / "repo" / "generated"
    destination.parent.mkdir(parents=True)
    rollback = destination.with_name(".generated.protocyte-rollback")
    rollback.mkdir()

    with install_protoc.locked_destination(destination):
        owner = install_protoc._create_install_transaction(
            destination,
            "transaction",
        )
        try:
            owner.bind_path("rollback", rollback)
            marker_paths = list(state_directory.rglob("*.owner"))
            assert len(marker_paths) == 1
            marker_path = marker_paths[0]
            payload = _owner_journal_payload(owner)
            marker_mode = stat.S_IMODE(marker_path.stat().st_mode)
            owner._lease._file.seek(0)
            assert owner._lease._file.read() == b"\0"
            if os.name != "nt":
                journal_paths = list(state_directory.rglob("*.state"))
                assert journal_paths
                assert all(
                    stat.S_IMODE(path.stat().st_mode) == 0o600
                    for path in journal_paths
                )
                lock_paths = list(state_directory.rglob("*.lock"))
                assert lock_paths
                assert all(
                    stat.S_IMODE(path.stat().st_mode) == 0o600 for path in lock_paths
                )
        finally:
            owner.cleanup(install_protoc._remove_path)

    assert set(payload) == {
        "schema",
        "destination_key",
        "kind",
        "token",
        "sibling_location",
        "owned_paths",
    }
    assert payload["sibling_location"] == "original"
    assert payload["destination_key"] == owned_transactions._destination_key(
        destination
    )
    rollback_identity = payload["owned_paths"]["rollback"]
    assert set(rollback_identity) == {
        "path_key",
        "device",
        "inode",
        "type",
        "reparse_tag",
    }
    assert rollback_identity["path_key"] == owned_transactions._destination_key(
        rollback
    )
    sibling_identity = payload["owned_paths"]["sibling"]
    assert set(sibling_identity) == {
        "path_key",
        "device",
        "inode",
        "type",
        "reparse_tag",
    }
    assert sibling_identity["path_key"] == owned_transactions._destination_key(
        owner.path
    )
    assert sibling_identity["inode"] > 0
    assert sibling_identity["type"] == stat.S_IFDIR
    assert sibling_identity["reparse_tag"] == 0
    serialized_payload = json.dumps(payload, sort_keys=True)
    assert (
        owned_transactions._normalized_destination(destination)
        not in serialized_payload
    )
    assert (
        owned_transactions._normalized_destination(rollback) not in serialized_payload
    )
    assert (
        owned_transactions._normalized_destination(owner.path) not in serialized_payload
    )

    if os.name != "nt":
        assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700
        assert marker_mode == 0o600


def test_transaction_state_directory_rejects_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    state_directory = tmp_path / "state"
    try:
        state_directory.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    with pytest.raises(RuntimeError, match="linked transaction state directory"):
        owned_transactions._state_directory()


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink check")
def test_transaction_state_directory_rejects_linked_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    linked_ancestor = tmp_path / "linked-ancestor"
    linked_ancestor.symlink_to(target, target_is_directory=True)
    state_directory = linked_ancestor / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    with pytest.raises(RuntimeError, match="linked transaction state ancestor"):
        owned_transactions._state_directory()
    assert not (target / "state").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junction check")
def test_windows_transaction_state_directory_rejects_junctions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "junction-target"
    target.mkdir()
    state_directory = tmp_path / "state-junction"
    result = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            state_directory.name,
            target.name,
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    try:
        with pytest.raises(RuntimeError, match="linked transaction state directory"):
            owned_transactions._state_directory()
    finally:
        state_directory.rmdir()


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junction check")
def test_windows_transaction_state_directory_rejects_junction_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "junction-target"
    target.mkdir()
    linked_ancestor = tmp_path / "junction-ancestor"
    result = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            linked_ancestor.name,
            target.name,
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(linked_ancestor / "state"),
    )

    try:
        with pytest.raises(RuntimeError, match="linked transaction state ancestor"):
            owned_transactions._state_directory()
        assert not (target / "state").exists()
    finally:
        linked_ancestor.rmdir()


@pytest.mark.skipif(os.name != "nt", reason="Windows directory junction check")
def test_windows_registry_open_keeps_validated_state_root_pinned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    detached_state = tmp_path / "detached-state"
    redirect_target = tmp_path / "redirect-target"
    redirect_target.mkdir()
    destination = tmp_path / "protoc"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    original_open_state_file = owned_transactions._open_state_file
    swap_attempted = False
    swap_blocked = False

    def attempt_swap_before_registry_open(path: Path, flags: int):
        nonlocal swap_attempted, swap_blocked
        if (
            not swap_attempted
            and path == state_directory / owned_transactions._REGISTRY_LOCK_NAME
        ):
            swap_attempted = True
            try:
                state_directory.rename(detached_state)
            except OSError:
                swap_blocked = True
            else:
                result = subprocess.run(
                    [
                        "cmd.exe",
                        "/d",
                        "/c",
                        "mklink",
                        "/J",
                        state_directory.name,
                        redirect_target.name,
                    ],
                    cwd=tmp_path,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0, result.stdout + result.stderr
        return original_open_state_file(path, flags)

    monkeypatch.setattr(
        owned_transactions,
        "_open_state_file",
        attempt_swap_before_registry_open,
    )
    try:
        with install_protoc.locked_destination(destination):
            pass

        assert swap_attempted
        assert swap_blocked
        assert not (redirect_target / owned_transactions._REGISTRY_LOCK_NAME).exists()
    finally:
        if detached_state.exists():
            state_directory.rmdir()
            detached_state.rename(state_directory)


def test_relative_transaction_state_directory_reports_each_legacy_absolute_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_temporary_root = tmp_path / "first-temporary-root"
    second_temporary_root = tmp_path / "second-temporary-root"
    first_working_directory = tmp_path / "first-working-directory"
    second_working_directory = tmp_path / "second-working-directory"
    first_working_directory.mkdir()
    second_working_directory.mkdir()
    monkeypatch.setenv(owned_transactions._STATE_DIRECTORY_ENV, "shared-state")

    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(first_temporary_root),
    )
    monkeypatch.chdir(first_working_directory)
    with pytest.raises(RuntimeError, match="must be an absolute path") as first_error:
        owned_transactions._state_directory()

    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(second_temporary_root),
    )
    with pytest.raises(RuntimeError, match="must be an absolute path") as second_error:
        owned_transactions._state_directory()

    monkeypatch.chdir(second_working_directory)
    with pytest.raises(RuntimeError, match="must be an absolute path") as third_error:
        owned_transactions._state_directory()

    first_legacy_root = first_working_directory / "shared-state"
    second_legacy_root = second_working_directory / "shared-state"
    assert str(first_error.value) == str(second_error.value)
    assert str(first_legacy_root) in str(first_error.value)
    assert str(second_legacy_root) in str(third_error.value)
    assert "existing v7 state" in str(first_error.value)
    assert not (first_working_directory / "shared-state").exists()
    assert not (second_working_directory / "shared-state").exists()
    assert not first_temporary_root.exists()
    assert not second_temporary_root.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX legacy-state symlink check")
def test_relative_state_migration_reports_canonical_posix_symlink_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    working_directory = tmp_path / "working-directory"
    working_directory.mkdir()
    canonical_parent = tmp_path / "canonical-parent"
    canonical_parent.mkdir()
    linked_parent = working_directory / "linked-parent"
    linked_parent.symlink_to(canonical_parent, target_is_directory=True)
    canonical_state = canonical_parent / "state"
    monkeypatch.chdir(working_directory)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(Path("linked-parent") / "state"),
    )

    with pytest.raises(RuntimeError, match="must be an absolute path") as error:
        owned_transactions._state_directory()

    assert str(canonical_state) in str(error.value)
    assert "canonical absolute target" in str(error.value)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(canonical_state),
    )
    assert owned_transactions._state_directory() == canonical_state


@pytest.mark.skipif(os.name != "nt", reason="Windows legacy-state junction check")
def test_relative_state_migration_reports_canonical_windows_junction_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    working_directory = tmp_path / "working-directory"
    working_directory.mkdir()
    canonical_parent = tmp_path / "canonical-parent"
    canonical_parent.mkdir()
    linked_parent = working_directory / "linked-parent"
    result = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            linked_parent.name,
            str(canonical_parent),
        ],
        cwd=working_directory,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    canonical_state = canonical_parent / "state"
    monkeypatch.chdir(working_directory)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(Path("linked-parent") / "state"),
    )

    try:
        with pytest.raises(RuntimeError, match="must be an absolute path") as error:
            owned_transactions._state_directory()

        assert str(canonical_state) in str(error.value)
        assert "canonical absolute target" in str(error.value)
        monkeypatch.setenv(
            owned_transactions._STATE_DIRECTORY_ENV,
            str(canonical_state),
        )
        assert owned_transactions._state_directory() == canonical_state
    finally:
        linked_parent.rmdir()


def test_default_state_root_namespace_distinguishes_users(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )
    monkeypatch.setattr(owned_transactions, "_effective_user_id", lambda: 1001)
    first_user_state = owned_transactions._absolute_state_directory(None)
    monkeypatch.setattr(owned_transactions, "_effective_user_id", lambda: 1002)
    second_user_state = owned_transactions._absolute_state_directory(None)

    assert first_user_state.parent == tmp_path
    assert second_user_state.parent == tmp_path
    assert first_user_state.name.endswith("-uid-1001")
    assert second_user_state.name.endswith("-uid-1002")
    assert first_user_state != second_user_state


def test_relative_v7_state_can_be_recovered_after_explicit_absolute_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    working_directory = tmp_path / "working-directory"
    working_directory.mkdir()
    legacy_state = working_directory / "shared-state"
    destination = tmp_path / "protoc"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(legacy_state),
    )
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "legacy").write_text("legacy\n", encoding="utf-8")
    marker_path = owner.marker_path
    owned_path = owner.path
    owner.close(remove_marker=False)

    monkeypatch.chdir(working_directory)
    monkeypatch.setenv(owned_transactions._STATE_DIRECTORY_ENV, "shared-state")
    with pytest.raises(RuntimeError, match="must be an absolute path") as error:
        with install_protoc.locked_destination(destination):
            pass

    assert str(legacy_state) in str(error.value)
    assert marker_path.is_file()
    assert (owned_path / "legacy").read_text(encoding="utf-8") == "legacy\n"

    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(legacy_state),
    )
    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not marker_path.exists()
    assert not owned_path.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership check")
def test_transaction_state_directory_rejects_wrong_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    state_directory.mkdir(mode=0o700)
    state_directory.chmod(0o700)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    owner_id = state_directory.stat().st_uid
    monkeypatch.setattr(
        owned_transactions,
        "_effective_user_id",
        lambda: owner_id + 1,
    )

    descriptor = os.open(
        state_directory,
        owned_transactions._posix_directory_open_flags(),
    )
    try:
        with pytest.raises(RuntimeError, match="not owned by the current user"):
            owned_transactions._posix_validate_private_state_directory(
                descriptor,
                state_directory,
            )
    finally:
        os.close(descriptor)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission check")
def test_transaction_state_directory_rejects_insecure_permissions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    state_directory.mkdir()
    state_directory.chmod(0o755)
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    with pytest.raises(RuntimeError, match="private 0700 permissions"):
        owned_transactions._state_directory()


def _grant_windows_everyone_read(path: Path) -> None:
    result = subprocess.run(
        ["icacls", str(path), "/grant", "*S-1-1-0:R"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"could not prepare an insecure Windows ACL: {result.stderr}")


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL check")
@pytest.mark.parametrize("entry_kind", ("root", "registry", "destination"))
def test_windows_transaction_state_rejects_insecure_acls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry_kind: str,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owned_transactions._state_directory()

    if entry_kind == "root":
        insecure_path = state_directory
    elif entry_kind == "registry":
        with install_protoc.locked_destination(destination):
            pass
        insecure_path = state_directory / owned_transactions._REGISTRY_LOCK_NAME
    else:
        destination_state = owned_transactions._ensure_destination_state_directory(
            destination,
            state_directory,
        )
        insecure_path = destination_state / owned_transactions._DESTINATION_LOCK_NAME
        owned_transactions._open_state_file(
            insecure_path,
            os.O_RDWR | os.O_CREAT,
        ).close()

    _grant_windows_everyone_read(insecure_path)

    with pytest.raises(RuntimeError, match="private Windows ACL"):
        with install_protoc.locked_destination(destination):
            pass


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse-point check")
@pytest.mark.parametrize("entry_kind", ("registry", "destination"))
def test_windows_transaction_locks_reject_file_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry_kind: str,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owned_transactions._state_directory()
    target = tmp_path / "target.lock"
    target.write_bytes(b"\0")

    if entry_kind == "registry":
        lock_path = state_directory / owned_transactions._REGISTRY_LOCK_NAME
    else:
        destination_state = owned_transactions._ensure_destination_state_directory(
            destination,
            state_directory,
        )
        lock_path = destination_state / owned_transactions._DESTINATION_LOCK_NAME
    try:
        lock_path.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="linked transaction state entry"):
        with install_protoc.locked_destination(destination):
            pass


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-length path check")
def test_windows_long_transaction_state_path_supports_lock_and_marker_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path.joinpath(
        *(f"private-state-segment-{index:02d}" for index in range(16))
    )
    assert len(os.fspath(state_directory)) >= 450
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"

    with install_protoc.locked_destination(destination):
        owner = install_protoc._create_install_transaction(
            destination,
            "transaction",
        )
        (owner.path / "dead").write_text("dead\n", encoding="utf-8")
        marker_path = owner.marker_path
        owned_path = owner.path
        owner.close(remove_marker=False)

        assert marker_path.is_file()
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not marker_path.exists()
    assert not owned_path.exists()
    assert _transaction_state_entries(state_directory) == {"registry.lock"}


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-length path check")
def test_windows_extended_path_conversion_handles_local_and_unc_paths() -> None:
    local = owned_transactions._windows_extended_path(Path("C:/state"))
    unc = owned_transactions._windows_extended_path(Path("//server/share/state"))

    assert local == r"\\?\C:\state"
    assert unc == r"\\?\UNC\server\share\state"


def _transaction_state_entries(state_directory: Path) -> set[str]:
    return {
        path.relative_to(state_directory).as_posix()
        for path in state_directory.rglob("*")
    }


def _create_owned_sibling_lookalike(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            pytest.skip("Windows junction creation is unavailable: " + result.stderr)
        return
    link.symlink_to(target, target_is_directory=True)


def _remove_owned_sibling_lookalike(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()


def _release_owned_directory_handle(owner) -> None:
    if owner._directory is not None:
        owner._directory.close()
        owner._directory = None


@pytest.mark.parametrize("dead_owner", [False, True], ids=["live", "dead-owner"])
@pytest.mark.parametrize("replacement_kind", ["directory", "link"])
def test_owned_sibling_cleanup_refuses_renamed_replacements_and_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dead_owner: bool,
    replacement_kind: str,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "owned").write_text("owned\n", encoding="utf-8")
    _release_owned_directory_handle(owner)
    original = tmp_path / "renamed-owned-sibling"
    owner.path.rename(original)
    lookalike_target = tmp_path / "lookalike-target"
    if replacement_kind == "link":
        lookalike_target.mkdir()
        replacement_file = lookalike_target / "keep"
        _create_owned_sibling_lookalike(owner.path, lookalike_target)
    else:
        owner.path.mkdir()
        replacement_file = owner.path / "keep"
    replacement_file.write_text("unowned\n", encoding="utf-8")
    marker_path = owner.marker_path

    try:
        if dead_owner:
            owner.close(remove_marker=False)

        def cleanup() -> None:
            if not dead_owner:
                owner.cleanup(install_protoc._remove_path)
                return
            install_protoc.recover_owned_siblings(
                destination,
                ("transaction",),
                install_protoc._remove_path,
            )

        with pytest.raises(RuntimeError, match="unowned, replaced, or linked"):
            with install_protoc.locked_destination(destination):
                cleanup()

        assert replacement_file.read_text(encoding="utf-8") == "unowned\n"
        assert (original / "owned").read_text(encoding="utf-8") == "owned\n"
        assert marker_path.is_file()
    finally:
        if replacement_kind == "link" and owner.path.exists():
            _remove_owned_sibling_lookalike(owner.path)
        elif replacement_kind == "directory":
            install_protoc._remove_path(owner.path)
        if original.exists():
            install_protoc._remove_path(original)
        owner.close(remove_marker=True)


@pytest.mark.parametrize("dead_owner", [False, True], ids=["live", "dead-owner"])
def test_owned_sibling_cleanup_never_delegates_recursive_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dead_owner: bool,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    nested = owner.path / "nested"
    nested.mkdir()
    (nested / "owned").write_text("owned\n", encoding="utf-8")
    marker_path = owner.marker_path
    callback_called = False

    def unsafe_path_callback(_candidate: Path) -> None:
        nonlocal callback_called
        callback_called = True
        raise AssertionError("verified cleanup delegated to a pathname callback")

    if dead_owner:
        owner.close(remove_marker=False)
        with install_protoc.locked_destination(destination):
            install_protoc.recover_owned_siblings(
                destination,
                ("transaction",),
                unsafe_path_callback,
            )
    else:
        owner.cleanup(unsafe_path_callback)

    assert not callback_called
    assert not owner.path.exists()
    assert not owner.cleanup_path.exists()
    assert not marker_path.exists()


def test_owned_sibling_cleanup_does_not_follow_linked_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    linked_target = tmp_path / "linked-target"
    linked_target.mkdir()
    keep = linked_target / "keep"
    keep.write_text("unowned\n", encoding="utf-8")
    _create_owned_sibling_lookalike(owner.path / "linked", linked_target)

    owner.cleanup(install_protoc._remove_path)

    assert keep.read_text(encoding="utf-8") == "unowned\n"
    assert not owner.path.exists()
    assert not owner.cleanup_path.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-relative cleanup race")
def test_windows_owned_cleanup_rejects_child_replacement_after_enumeration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    nested = owner.path / "nested"
    nested.mkdir()
    (nested / "owned").write_text("owned\n", encoding="utf-8")
    raced = tmp_path / "raced-child"
    replacement_keep: Path | None = None
    replaced = False

    def replace_child(phase: str, path: Path) -> None:
        nonlocal replacement_keep, replaced
        if phase != "after_enumerate" or path.name != "nested" or replaced:
            return
        replaced = True
        path.rename(raced)
        path.mkdir()
        replacement_keep = path / "keep"
        replacement_keep.write_text("unowned\n", encoding="utf-8")

    monkeypatch.setattr(
        owned_transactions,
        "_owned_windows_entry_phase",
        replace_child,
    )

    with pytest.raises(RuntimeError, match="child changed identity"):
        owner.cleanup(install_protoc._remove_path)

    assert replaced
    assert replacement_keep is not None
    assert replacement_keep.read_text(encoding="utf-8") == "unowned\n"
    assert (raced / "owned").read_text(encoding="utf-8") == "owned\n"
    assert owner.marker_path.is_file()
    install_protoc._remove_path(owner.cleanup_path)
    install_protoc._remove_path(raced)
    owner.close(remove_marker=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows missing-child lookup gap")
def test_windows_owned_cleanup_rejects_disappearance_before_reenumeration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    nested = owner.path / "nested"
    nested.mkdir()
    (nested / "owned").write_text("owned\n", encoding="utf-8")
    moved = tmp_path / "moved-enumerated-child"
    replacement_keep: Path | None = None
    moved_once = False

    def replace_after_missing(phase: str, path: Path) -> None:
        nonlocal moved_once, replacement_keep
        if path.name != "nested":
            return
        if phase == "after_enumerate" and not moved_once:
            moved_once = True
            path.rename(moved)
        elif phase == "after_missing":
            path.mkdir()
            replacement_keep = path / "keep"
            replacement_keep.write_text("unowned\n", encoding="utf-8")

    monkeypatch.setattr(
        owned_transactions,
        "_owned_windows_entry_phase",
        replace_after_missing,
    )

    with pytest.raises(RuntimeError, match="disappeared after enumeration"):
        owner.cleanup(install_protoc._remove_path)

    assert moved_once
    assert replacement_keep is not None
    assert replacement_keep.read_text(encoding="utf-8") == "unowned\n"
    assert (moved / "owned").read_text(encoding="utf-8") == "owned\n"
    assert owner.marker_path.is_file()
    install_protoc._remove_path(owner.cleanup_path)
    install_protoc._remove_path(moved)
    owner.close(remove_marker=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows directory entry metadata")
def test_windows_normal_entries_report_a_zero_reparse_tag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "normal").write_text("owned\n", encoding="utf-8")
    assert owner._directory is not None

    entries = owned_transactions._windows_directory_entries(owner._directory._handle)
    normal = next(entry for entry in entries if entry[0] == "normal")

    assert not normal[2] & owned_transactions._FILE_ATTRIBUTE_REPARSE_POINT
    assert normal[3] == 0
    owner.cleanup(install_protoc._remove_path)


@pytest.mark.skipif(os.name != "nt", reason="Windows ancestor handle pinning")
def test_windows_owned_cleanup_blocks_ancestor_junction_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    nested = owner.path / "nested"
    inner = nested / "inner"
    inner.mkdir(parents=True)
    (inner / "owned").write_text("owned\n", encoding="utf-8")
    junction_target = tmp_path / "junction-target"
    junction_target.mkdir()
    keep = junction_target / "keep"
    keep.write_text("unowned\n", encoding="utf-8")
    raced = tmp_path / "raced-ancestor"
    attempted = False
    blocked = False

    def swap_ancestor(phase: str, path: Path) -> None:
        nonlocal attempted, blocked
        if phase != "after_enumerate" or path.name != "inner" or attempted:
            return
        attempted = True
        ancestor = path.parent
        try:
            ancestor.rename(raced)
        except OSError:
            blocked = True
            return
        _create_owned_sibling_lookalike(ancestor, junction_target)

    monkeypatch.setattr(
        owned_transactions,
        "_owned_windows_entry_phase",
        swap_ancestor,
    )

    owner.cleanup(install_protoc._remove_path)

    assert attempted
    assert blocked
    assert not raced.exists()
    assert keep.read_text(encoding="utf-8") == "unowned\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows durable parent pinning")
def test_windows_root_removal_flushes_the_pinned_parent_after_swap_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    destination = parent / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "owned").write_text("owned\n", encoding="utf-8")
    moved_parent = tmp_path / "moved-owned-parent"
    junction_target = tmp_path / "junction-target"
    junction_target.mkdir()
    keep = junction_target / "keep"
    keep.write_text("unowned\n", encoding="utf-8")
    original_path_sync = owned_transactions._sync_directory
    original_handle_sync = owned_transactions._windows_sync_directory_handle
    attempted = False
    blocked = False
    replacement_created = False
    pinned_identity_preserved = False

    def forbid_post_delete_path_reopen(path: Path) -> None:
        if path == parent and not owner.cleanup_path.exists():
            raise AssertionError("removed root parent was reopened by pathname")
        original_path_sync(path)

    def swap_during_pinned_flush(handle: object) -> None:
        nonlocal attempted, blocked, replacement_created, pinned_identity_preserved
        if attempted or owner.cleanup_path.exists():
            original_handle_sync(handle)
            return
        attempted = True
        before = owned_transactions._windows_handle_identity(handle, parent)
        try:
            parent.rename(moved_parent)
        except OSError:
            blocked = True
        else:
            _create_owned_sibling_lookalike(parent, junction_target)
            replacement_created = True
        after = owned_transactions._windows_handle_identity(handle, parent)
        pinned_identity_preserved = owned_transactions._same_filesystem_object(
            before,
            after,
        )
        original_handle_sync(handle)

    monkeypatch.setattr(
        owned_transactions,
        "_sync_directory",
        forbid_post_delete_path_reopen,
    )
    monkeypatch.setattr(
        owned_transactions,
        "_windows_sync_directory_handle",
        swap_during_pinned_flush,
    )

    try:
        owner.cleanup(install_protoc._remove_path)
        assert attempted
        assert pinned_identity_preserved
        assert blocked or replacement_created
        assert keep.read_text(encoding="utf-8") == "unowned\n"
    finally:
        if replacement_created and parent.exists():
            _remove_owned_sibling_lookalike(parent)
        if moved_parent.exists():
            install_protoc._remove_path(moved_parent)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mount-boundary cleanup")
def test_posix_owned_cleanup_fails_closed_when_mount_guard_refuses_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    nested = owner.path / "nested"
    nested.mkdir()
    keep = nested / "keep"
    keep.write_text("owned\n", encoding="utf-8")
    original_open = owned_transactions._posix_open_child_directory

    def refuse_child(parent: int, name: str, root_device: int) -> int:
        if name == "nested":
            raise owned_transactions._mount_boundary_error(name)
        return original_open(parent, name, root_device)

    monkeypatch.setattr(
        owned_transactions,
        "_posix_open_child_directory",
        refuse_child,
    )

    with pytest.raises(RuntimeError, match="mount boundary"):
        owner.cleanup(install_protoc._remove_path)

    assert (owner.cleanup_path / "nested" / "keep").read_text(
        encoding="utf-8"
    ) == "owned\n"
    assert owner.marker_path.is_file()
    monkeypatch.setattr(
        owned_transactions,
        "_posix_open_child_directory",
        original_open,
    )
    owner.cleanup(install_protoc._remove_path)


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or getattr(os, "geteuid", lambda: -1)() != 0,
    reason="privileged Linux bind-mount check",
)
def test_linux_owned_cleanup_refuses_a_same_device_bind_mount(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mount_command = shutil.which("mount")
    unmount_command = shutil.which("umount")
    if mount_command is None or unmount_command is None:
        pytest.skip("mount utilities are unavailable")
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    nested = owner.path / "nested"
    nested.mkdir()
    target = tmp_path / "mount-target"
    target.mkdir()
    keep = target / "keep"
    keep.write_text("unowned\n", encoding="utf-8")
    result = subprocess.run(
        [mount_command, "--bind", str(target), str(nested)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        owner.cleanup(install_protoc._remove_path)
        pytest.skip("bind mounts are unavailable: " + result.stderr)

    try:
        with pytest.raises(RuntimeError, match="mount boundary"):
            owner.cleanup(install_protoc._remove_path)
    finally:
        subprocess.run(
            [unmount_command, str(owner.cleanup_path / "nested")],
            check=True,
            capture_output=True,
            text=True,
        )

    assert keep.read_text(encoding="utf-8") == "unowned\n"
    assert owner.marker_path.is_file()
    owner.cleanup(install_protoc._remove_path)


@pytest.mark.parametrize("dead_owner", [False, True], ids=["live", "dead-owner"])
def test_owned_sibling_cleanup_stays_anchored_after_detached_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dead_owner: bool,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "owned").write_text("owned\n", encoding="utf-8")
    raced_owned_path = tmp_path / "detached-owned-sibling"
    replacement_file = owner.cleanup_path / "keep"
    attempted = False
    blocked = False
    callback_called = False

    def replace_after_verification(phase: str, path: Path) -> None:
        nonlocal attempted, blocked
        if phase != "after_verify":
            return
        attempted = True
        try:
            path.rename(raced_owned_path)
        except OSError:
            blocked = True
            return
        path.mkdir()
        replacement_file.write_text("unowned\n", encoding="utf-8")

    def unsafe_path_callback(_candidate: Path) -> None:
        nonlocal callback_called
        callback_called = True
        raise AssertionError("cleanup delegated to an unverified pathname")

    monkeypatch.setattr(
        owned_transactions,
        "_owned_sibling_cleanup_phase",
        replace_after_verification,
    )
    if dead_owner:
        owner.close(remove_marker=False)

    if os.name == "nt":
        if dead_owner:
            with install_protoc.locked_destination(destination):
                install_protoc.recover_owned_siblings(
                    destination,
                    ("transaction",),
                    unsafe_path_callback,
                )
        else:
            owner.cleanup(unsafe_path_callback)
        assert blocked
        assert not raced_owned_path.exists()
        assert not owner.cleanup_path.exists()
        assert not owner.marker_path.exists()
    else:
        with pytest.raises(RuntimeError, match="unowned, replaced, or linked"):
            if dead_owner:
                with install_protoc.locked_destination(destination):
                    install_protoc.recover_owned_siblings(
                        destination,
                        ("transaction",),
                        unsafe_path_callback,
                    )
            else:
                owner.cleanup(unsafe_path_callback)
        assert replacement_file.read_text(encoding="utf-8") == "unowned\n"
        assert raced_owned_path.is_dir()
        assert owner.marker_path.is_file()
        install_protoc._remove_path(owner.cleanup_path)
        install_protoc._remove_path(raced_owned_path)
        owner.close(remove_marker=True)

    assert attempted
    assert not callback_called


@pytest.mark.parametrize(
    ("interrupted_phase", "journal_location", "detached"),
    [
        ("before_detach", "detaching", False),
        ("after_detach", "detaching", True),
        ("before_remove", "cleanup", True),
    ],
)
def test_dead_owner_recovery_resumes_a_persisted_cleanup_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupted_phase: str,
    journal_location: str,
    detached: bool,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "owned").write_text("owned\n", encoding="utf-8")

    def interrupt(phase: str, _path: Path) -> None:
        if phase == interrupted_phase:
            raise KeyboardInterrupt(phase)

    monkeypatch.setattr(
        owned_transactions,
        "_owned_sibling_cleanup_phase",
        interrupt,
    )
    with pytest.raises(KeyboardInterrupt, match=interrupted_phase):
        owner.cleanup(install_protoc._remove_path)

    marker_path = owner.marker_path
    marker_payload = _owner_journal_payload(owner)
    assert marker_payload["sibling_location"] == journal_location
    interrupted_path = owner.cleanup_path if detached else owner.path
    assert (interrupted_path / "owned").read_text(encoding="utf-8") == "owned\n"
    assert not (owner.path if detached else owner.cleanup_path).exists()

    monkeypatch.setattr(
        owned_transactions,
        "_owned_sibling_cleanup_phase",
        lambda _phase, _path: None,
    )
    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not owner.cleanup_path.exists()
    assert not marker_path.exists()


def test_dead_owner_recovery_resumes_a_hard_exit_after_sibling_detach(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("detach_crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
transactions = sys.modules[module.locked_destination.__module__]

def hard_exit(phase: str, _path: Path) -> None:
    if phase == "after_detach":
        os._exit(91)

transactions._owned_sibling_cleanup_phase = hard_exit
owner = module._create_install_transaction(destination, "transaction")
(owner.path / "owned").write_text("owned\n", encoding="utf-8")
owner.cleanup(module._remove_path)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(script_path), str(destination)],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 91, result.stdout + result.stderr

    marker_paths = list(state_directory.rglob("*.owner"))
    assert len(marker_paths) == 1
    payload = _marker_journal_payload(marker_paths[0], destination)
    cleanup_path = owned_transactions._owned_sibling_cleanup_path(
        destination,
        payload["kind"],
        payload["token"],
    )
    assert payload["sibling_location"] == "detaching"
    assert (cleanup_path / "owned").read_text(encoding="utf-8") == "owned\n"

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not cleanup_path.exists()
    assert not marker_paths[0].exists()


def test_owner_lease_identity_is_stable_across_journal_transitions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    rollback = tmp_path / "rollback"
    rollback.mkdir()
    before = owner.marker_path.stat()

    owner.bind_path("rollback", rollback)

    after = owner.marker_path.stat()
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    owner._lease._file.seek(0)
    assert owner._lease._file.read() == b"\0"
    journals = owned_transactions._journal_paths(owner.marker_path)
    assert 1 <= len(journals) <= owned_transactions._JOURNAL_RETAINED_GENERATIONS
    install_protoc._remove_path(rollback)
    owner.cleanup(install_protoc._remove_path)


def test_dead_owner_recovery_ignores_a_torn_temporary_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    keep = owner.path / "owned"
    keep.write_text("owned\n", encoding="utf-8")
    temporary = owned_transactions._journal_temporary_path(
        owner.marker_path,
        owner._generation + 1,
    )
    file = owned_transactions._open_state_file(
        temporary,
        os.O_RDWR | os.O_CREAT | os.O_EXCL,
    )
    file.write(b'{"torn":')
    file.flush()
    os.fsync(file.fileno())
    file.close()
    owner.close(remove_marker=False)

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not temporary.exists()
    assert not owner.path.exists()
    assert not owner.marker_path.exists()


def test_dead_owner_recovery_fails_closed_on_a_torn_published_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    keep = owner.path / "keep"
    keep.write_text("owned\n", encoding="utf-8")
    invalid = owned_transactions._journal_path(
        owner.marker_path,
        owner._generation + 1,
    )
    file = owned_transactions._open_state_file(
        invalid,
        os.O_RDWR | os.O_CREAT | os.O_EXCL,
    )
    file.write(b'{"torn":')
    file.flush()
    os.fsync(file.fileno())
    file.close()
    owned_transactions._sync_directory(invalid.parent)
    owner.close(remove_marker=False)

    with pytest.raises(RuntimeError, match="journal is incomplete or invalid"):
        with install_protoc.locked_destination(destination):
            install_protoc.recover_owned_siblings(
                destination,
                ("transaction",),
                install_protoc._remove_path,
            )

    assert keep.read_text(encoding="utf-8") == "owned\n"
    assert owner.marker_path.is_file()
    invalid.unlink()
    owned_transactions._sync_directory(invalid.parent)
    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )


@pytest.mark.parametrize("candidate_location", ["original", "cleanup"])
def test_dead_owner_recovery_fails_closed_when_a_lease_has_no_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_location: str,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    keep = owner.path / "keep"
    keep.write_text("owned\n", encoding="utf-8")
    candidate = owner.path
    if candidate_location == "cleanup":
        _release_owned_directory_handle(owner)
        owner.path.rename(owner.cleanup_path)
        candidate = owner.cleanup_path
        keep = candidate / "keep"
    for _generation, journal in owned_transactions._journal_paths(owner.marker_path):
        journal.unlink()
    owned_transactions._sync_directory(owner.marker_path.parent)
    owner.close(remove_marker=False)

    with pytest.raises(RuntimeError, match="no committed state journal"):
        with install_protoc.locked_destination(destination):
            install_protoc.recover_owned_siblings(
                destination,
                ("transaction",),
                install_protoc._remove_path,
            )

    assert keep.read_text(encoding="utf-8") == "owned\n"
    install_protoc._remove_path(candidate)
    owner.close(remove_marker=True)


def test_recovery_prunes_a_pre_generation_lease_when_no_candidates_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    token = "a" * 32
    with owned_transactions._locked_registry() as registry:
        owned_transactions._ensure_destination_state_directory(destination, registry)
        marker_path = owned_transactions._marker_path(
            destination,
            "transaction",
            token,
            registry,
        )
        owned_transactions._open_state_file(
            marker_path,
            os.O_RDWR | os.O_CREAT | os.O_EXCL,
        ).close()

    assert marker_path.read_bytes() == b""
    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not marker_path.exists()
    assert _transaction_state_entries(state_directory) == {"registry.lock"}


@pytest.mark.parametrize(
    ("journal_phase", "expected_location"),
    [
        ("after_temporary_fsync", "detaching"),
        ("after_publish", "cleanup"),
        ("after_directory_fsync", "cleanup"),
    ],
)
def test_dead_owner_recovery_survives_hard_exit_during_post_detach_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    journal_phase: str,
    expected_location: str,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
journal_phase = sys.argv[3]
spec = importlib.util.spec_from_file_location("journal_crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
transactions = sys.modules[module.locked_destination.__module__]
owner = module._create_install_transaction(destination, "transaction")
(owner.path / "owned").write_text("owned\n", encoding="utf-8")
observed = 0

def hard_exit(phase: str, _path: Path) -> None:
    global observed
    if phase != journal_phase:
        return
    observed += 1
    if observed == 2:
        if phase == "after_temporary_fsync":
            with open(_path, "r+b", buffering=0) as journal:
                journal.truncate(7)
                journal.flush()
                os.fsync(journal.fileno())
        os._exit(92)

transactions._owned_journal_phase = hard_exit
owner.cleanup(module._remove_path)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            journal_phase,
        ],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 92, result.stdout + result.stderr

    marker_paths = list(state_directory.rglob("*.owner"))
    assert len(marker_paths) == 1
    payload = _marker_journal_payload(marker_paths[0], destination)
    assert payload["sibling_location"] == expected_location
    cleanup_path = owned_transactions._owned_sibling_cleanup_path(
        destination,
        payload["kind"],
        payload["token"],
    )
    assert (cleanup_path / "owned").read_text(encoding="utf-8") == "owned\n"

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not cleanup_path.exists()
    assert not marker_paths[0].exists()


def test_recovery_prunes_journals_after_hard_exit_during_state_retirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("retirement_crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
transactions = sys.modules[module.locked_destination.__module__]
owner = module._create_install_transaction(destination, "transaction")
(owner.path / "owned").write_text("owned\n", encoding="utf-8")

def hard_exit(phase: str, _path: Path) -> None:
    if phase == "after_lease_unlink":
        if _path.exists() or not list(_path.parent.glob("*.state")):
            os._exit(96)
        os._exit(95)

transactions._owned_retirement_phase = hard_exit
owner.cleanup(module._remove_path)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(script_path), str(destination)],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 95, result.stdout + result.stderr
    assert not list(state_directory.rglob("*.owner"))
    assert list(state_directory.rglob("*.state"))

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


@pytest.mark.parametrize(
    "journal_phase", ["after_temporary_fsync", "after_publish", "after_directory_fsync"]
)
@pytest.mark.parametrize(
    ("transition", "expect_recovery_refusal"),
    [
        ("creating", False),
        ("original", True),
        ("detaching", False),
    ],
)
def test_journal_hard_exit_is_safe_at_each_pre_detach_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    journal_phase: str,
    transition: str,
    expect_recovery_refusal: bool,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
transition = sys.argv[3]
journal_phase = sys.argv[4]
spec = importlib.util.spec_from_file_location("transition_crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
transactions = sys.modules[module.locked_destination.__module__]
observed = 0
target_occurrence = 2 if transition == "original" else 1

def hard_exit(phase: str, path: Path) -> None:
    global observed
    if phase != journal_phase:
        return
    observed += 1
    if observed != target_occurrence:
        return
    if phase == "after_temporary_fsync":
        with open(path, "r+b", buffering=0) as journal:
            journal.truncate(7)
            journal.flush()
            os.fsync(journal.fileno())
    os._exit(93)

if transition in {"creating", "original"}:
    transactions._owned_journal_phase = hard_exit
owner = module._create_install_transaction(destination, "transaction")
(owner.path / "owned").write_text("owned\n", encoding="utf-8")
if transition == "detaching":
    transactions._owned_journal_phase = hard_exit
    owner.cleanup(module._remove_path)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            transition,
            journal_phase,
        ],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 93, result.stdout + result.stderr

    marker_paths = list(state_directory.rglob("*.owner"))
    assert len(marker_paths) == 1
    marker_path = marker_paths[0]
    match = re.fullmatch(
        r"([a-z][a-z0-9-]*)\.([0-9a-f]{32})\.owner",
        marker_path.name,
    )
    assert match is not None
    sibling = owned_transactions._owned_sibling_path(
        destination,
        match.group(1),
        match.group(2),
    )

    should_refuse = expect_recovery_refusal and journal_phase == "after_temporary_fsync"
    if should_refuse:
        with pytest.raises(RuntimeError, match="no committed|unowned"):
            with install_protoc.locked_destination(destination):
                install_protoc.recover_owned_siblings(
                    destination,
                    ("transaction",),
                    install_protoc._remove_path,
                )
        if transition == "original":
            assert sibling.is_dir()
            install_protoc._remove_path(sibling)
        else:
            assert not sibling.exists()
        owned_transactions._remove_journal_artifacts(marker_path)
        marker_path.unlink()
    else:
        with install_protoc.locked_destination(destination):
            install_protoc.recover_owned_siblings(
                destination,
                ("transaction",),
                install_protoc._remove_path,
            )
        assert not sibling.exists()
        assert not marker_path.exists()


def test_owned_sibling_creation_binds_the_handle_created_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    raced_owned_path = tmp_path / "created-owned-sibling"
    replacement_path: Path | None = None
    replacement_blocked = False

    def replace_after_create(_phase: str, path: Path) -> None:
        nonlocal replacement_path, replacement_blocked
        replacement_path = path
        try:
            path.rename(raced_owned_path)
        except OSError:
            replacement_blocked = True
            return
        path.mkdir()
        (path / "keep").write_text("unowned\n", encoding="utf-8")

    monkeypatch.setattr(
        owned_transactions,
        "_owned_sibling_creation_phase",
        replace_after_create,
    )
    if os.name == "nt":
        owner = install_protoc._create_install_transaction(destination, "transaction")
        assert replacement_blocked
        assert replacement_path == owner.path
        assert not raced_owned_path.exists()
        owner.cleanup(install_protoc._remove_path)
    else:
        with pytest.raises(RuntimeError, match="unowned, replaced, or linked"):
            install_protoc._create_install_transaction(destination, "transaction")
        assert replacement_path is not None
        assert (replacement_path / "keep").read_text(encoding="utf-8") == "unowned\n"
        assert raced_owned_path.is_dir()
        install_protoc._remove_path(replacement_path)
        install_protoc._remove_path(raced_owned_path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX staged creation race")
def test_posix_owned_sibling_rejects_replacement_between_mkdir_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    staged_child: Path | None = None
    moved_child: Path | None = None

    def replace_staged_child(phase: str, path: Path) -> None:
        nonlocal staged_child, moved_child
        if phase != "after_staging_child_mkdir":
            return
        staged_child = path
        moved_child = path.with_name("moved-owned")
        path.rename(moved_child)
        path.mkdir(mode=0o700)
        (path / "keep").write_text("unowned\n", encoding="utf-8")

    monkeypatch.setattr(
        owned_transactions,
        "_owned_sibling_creation_phase",
        replace_staged_child,
    )

    with pytest.raises(RuntimeError, match="staged child changed identity"):
        install_protoc._create_install_transaction(destination, "transaction")

    assert staged_child is not None
    assert moved_child is not None
    assert (staged_child / "keep").read_text(encoding="utf-8") == "unowned\n"
    assert moved_child.is_dir()
    marker_paths = list(state_directory.rglob("*.owner"))
    assert len(marker_paths) == 1
    install_protoc._remove_path(staged_child.parent)
    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )
    assert not marker_paths[0].exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent trust boundary")
def test_posix_owned_sibling_rejects_an_unsafe_writable_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    parent = tmp_path / "unsafe-parent"
    parent.mkdir(mode=0o777)
    parent.chmod(0o777)

    with pytest.raises(RuntimeError, match="untrusted or replaced parent"):
        install_protoc._create_install_transaction(
            parent / "protoc",
            "transaction",
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX ancestor trust boundary")
def test_posix_owned_sibling_rejects_a_private_parent_under_unsafe_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    unsafe_ancestor = tmp_path / "unsafe-ancestor"
    unsafe_ancestor.mkdir(mode=0o777)
    unsafe_ancestor.chmod(0o777)
    private_parent = unsafe_ancestor / "private-parent"
    private_parent.mkdir(mode=0o700)

    with pytest.raises(RuntimeError, match="untrusted writable ancestor"):
        install_protoc._create_install_transaction(
            private_parent / "protoc",
            "transaction",
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX sticky ancestor boundary")
def test_posix_owned_sibling_accepts_a_private_parent_under_sticky_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    sticky_ancestor = tmp_path / "sticky-ancestor"
    sticky_ancestor.mkdir(mode=0o700)
    sticky_ancestor.chmod(0o1777)
    private_parent = sticky_ancestor / "private-parent"
    private_parent.mkdir(mode=0o700)

    owner = install_protoc._create_install_transaction(
        private_parent / "protoc",
        "transaction",
    )
    owner.cleanup(install_protoc._remove_path)


def test_namespace_mutations_are_durable_before_their_journal_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    events: list[str] = []
    original_publish = owned_transactions._publish_journal

    def record_publish(
        marker_path: Path,
        recorded_destination: Path,
        kind: str,
        token: str,
        owned_paths: dict[str, dict[str, object]],
        sibling_location: str,
        previous_generation: int,
    ) -> int:
        events.append(f"journal:{sibling_location}")
        return original_publish(
            marker_path,
            recorded_destination,
            kind,
            token,
            owned_paths,
            sibling_location,
            previous_generation,
        )

    monkeypatch.setattr(owned_transactions, "_publish_journal", record_publish)
    monkeypatch.setattr(
        owned_transactions,
        "_owned_namespace_phase",
        lambda phase, _path: events.append(phase),
    )

    owner = install_protoc._create_install_transaction(destination, "transaction")

    assert events.index("after_create_parent_fsync") < events.index("journal:original")
    events.clear()
    owner.cleanup(install_protoc._remove_path)
    assert events == [
        "journal:detaching",
        "after_detach_parent_fsync",
        "journal:cleanup",
        "before_remove_parent_fsync",
        "after_remove_parent_fsync",
    ]


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent descriptor race")
def test_posix_owned_sibling_rejects_a_replaced_parent_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    parent = tmp_path / "parent"
    parent.mkdir()
    moved_parent = tmp_path / "moved-parent"
    replacement_keep = parent / "keep"

    def replace_parent(phase: str, _path: Path) -> None:
        if phase != "after_staging_mkdir":
            return
        parent.rename(moved_parent)
        parent.mkdir()
        replacement_keep.write_text("unowned\n", encoding="utf-8")

    monkeypatch.setattr(
        owned_transactions,
        "_owned_sibling_creation_phase",
        replace_parent,
    )

    with pytest.raises(RuntimeError, match="untrusted or replaced parent"):
        install_protoc._create_install_transaction(
            parent / "protoc",
            "transaction",
        )

    assert replacement_keep.read_text(encoding="utf-8") == "unowned\n"
    assert moved_parent.is_dir()
    install_protoc._remove_path(moved_parent)


@pytest.mark.parametrize("candidate_exists", [False, True])
def test_interrupted_owned_sibling_creation_requires_persisted_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_exists: bool,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    _release_owned_directory_handle(owner)
    owner._owned_paths = {}
    owner._sibling_location = "creating"
    owner._replace_marker()
    if not candidate_exists:
        owner.path.rmdir()
    marker_path = owner.marker_path
    owner.close(remove_marker=False)

    if candidate_exists:
        with pytest.raises(RuntimeError, match="unowned, replaced, or linked"):
            with install_protoc.locked_destination(destination):
                install_protoc.recover_owned_siblings(
                    destination,
                    ("transaction",),
                    install_protoc._remove_path,
                )
        assert owner.path.is_dir()
        assert marker_path.is_file()
        owner.path.rmdir()
        owner.close(remove_marker=True)
    else:
        with install_protoc.locked_destination(destination):
            install_protoc.recover_owned_siblings(
                destination,
                ("transaction",),
                install_protoc._remove_path,
            )
        assert not marker_path.exists()


def test_destination_lock_state_is_bounded_across_distinct_destinations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )

    for index in range(64):
        with install_protoc.locked_destination(tmp_path / f"destination-{index}"):
            pass

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def test_nested_transaction_state_is_isolated_from_unreleased_flat_v2_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )
    destination = tmp_path / "protoc"
    key = owned_transactions._destination_key(destination)
    token = "a" * 32
    v2_state = tmp_path / (
        "protocyte-owned-transactions-v2-" + owned_transactions._user_namespace()
    )
    v2_state.mkdir(mode=0o700)
    v2_state.chmod(0o700)
    legacy_lock = v2_state / f"{key}.destination.lock"
    legacy_marker = v2_state / f"{key}.transaction.{token}.owner"
    legacy_sibling = tmp_path / f".protoc.protocyte-transaction-{token}"
    legacy_lock.write_bytes(b"\0")
    legacy_marker.write_text("unreleased-v2-state\n", encoding="utf-8")
    legacy_sibling.mkdir()

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    current_state = owned_transactions._state_directory()
    assert current_state != v2_state
    assert _transaction_state_entries(current_state) == {"registry.lock"}
    assert legacy_lock.read_bytes() == b"\0"
    assert legacy_marker.read_text(encoding="utf-8") == "unreleased-v2-state\n"
    assert legacy_sibling.is_dir()


def test_private_acl_namespace_is_isolated_from_pre_hardening_v3_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )
    v3_state = tmp_path / (
        "protocyte-owned-transactions-v3-" + owned_transactions._user_namespace()
    )
    v3_state.mkdir(mode=0o700)
    v3_state.chmod(0o700)
    sentinel = v3_state / "untrusted-state"
    sentinel.write_text("preserve\n", encoding="utf-8")

    current_state = owned_transactions._state_directory()

    assert current_state != v3_state
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"


def test_identity_bound_namespace_does_not_recover_unbound_v4_siblings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(owned_transactions._STATE_DIRECTORY_ENV, raising=False)
    monkeypatch.setattr(
        owned_transactions.tempfile,
        "gettempdir",
        lambda: str(tmp_path),
    )
    destination = tmp_path / "protoc"
    token = "a" * 32
    v4_state = tmp_path / (
        "protocyte-owned-transactions-v4-" + owned_transactions._user_namespace()
    )
    destination_state = v4_state / (
        owned_transactions._destination_key(destination) + ".destination"
    )
    destination_state.mkdir(mode=0o700, parents=True)
    destination_state.chmod(0o700)
    legacy_marker = destination_state / f"transaction.{token}.owner"
    legacy_marker.write_text("unbound-v4-marker\n", encoding="utf-8")
    legacy_marker.chmod(0o600)
    legacy_sibling = tmp_path / f".protoc.protocyte-transaction-{token}"
    legacy_sibling.mkdir()
    (legacy_sibling / "keep").write_text("preserve\n", encoding="utf-8")

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert owned_transactions._state_directory() != v4_state
    assert legacy_marker.read_text(encoding="utf-8") == "unbound-v4-marker\n"
    assert (legacy_sibling / "keep").read_text(encoding="utf-8") == "preserve\n"


def test_destination_lock_pruning_preserves_a_live_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    monkeypatch.setenv(
        owned_transactions._STATE_DIRECTORY_ENV,
        str(state_directory),
    )
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "live").write_text("live\n", encoding="utf-8")

    try:
        with install_protoc.locked_destination(destination):
            pass

        assert owner.marker_path.is_file()
        assert (owner.path / "live").read_text(encoding="utf-8") == "live\n"
    finally:
        owner.cleanup(install_protoc._remove_path)

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def _write_archive(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, "content")


class _Response(io.BytesIO):
    def __init__(self, content: bytes, content_length: str | None = None) -> None:
        super().__init__(content)
        self.headers = (
            {} if content_length is None else {"Content-Length": content_length}
        )


class _SlowResponse(_Response):
    def __init__(
        self,
        content: bytes,
        read_started: threading.Event,
        release_read: threading.Event,
    ) -> None:
        super().__init__(content)
        self.read_started = read_started
        self.release_read = release_read

    def read(self, size: int = -1) -> bytes:
        self.read_started.set()
        self.release_read.wait(timeout=1.0)
        return super().read(size)


def test_extract_archive_safely_preserves_normal_archive_layout(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(
        archive_path,
        [
            "bin/protoc",
            "include/google/protobuf/descriptor.proto",
        ],
    )

    with zipfile.ZipFile(archive_path) as archive:
        install_protoc.extract_archive_safely(archive, destination)

    assert (destination / "bin" / "protoc").read_text(encoding="utf-8") == "content"
    assert (
        destination / "include" / "google" / "protobuf" / "descriptor.proto"
    ).is_file()


def test_download_archive_hashes_content_and_applies_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"trusted archive bytes"
    observed: dict[str, object] = {}

    def fake_urlopen(url: str, *, timeout: float) -> _Response:
        observed.update(url=url, timeout=timeout)
        return _Response(content, str(len(content)))

    monkeypatch.setattr(install_protoc, "urlopen", fake_urlopen)
    archive_path = tmp_path / "protoc.zip"

    actual_sha256 = install_protoc.download_archive(
        "https://example.invalid/protoc.zip",
        archive_path,
        timeout=7.5,
    )

    assert observed == {"url": "https://example.invalid/protoc.zip", "timeout": 7.5}
    assert archive_path.read_bytes() == content
    assert actual_sha256 == hashlib.sha256(content).hexdigest()


def test_download_archive_enforces_wall_clock_deadline_against_slow_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_started = threading.Event()
    release_read = threading.Event()
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _SlowResponse(
            b"slow bytes",
            read_started,
            release_read,
        ),
    )
    archive_path = tmp_path / "protoc.zip"

    try:
        with pytest.raises(RuntimeError, match="wall-clock deadline"):
            install_protoc.download_archive(
                "https://example.invalid/protoc.zip",
                archive_path,
                timeout=0.02,
            )
    finally:
        release_read.set()

    assert read_started.is_set()
    assert not archive_path.exists()


@pytest.mark.parametrize("declared_size", ["not-a-number", "9"])
def test_download_archive_rejects_invalid_or_oversized_content_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declared_size: str,
) -> None:
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _Response(b"content", declared_size),
    )
    archive_path = tmp_path / "protoc.zip"

    with pytest.raises(RuntimeError, match="Content-Length|too large"):
        install_protoc.download_archive(
            "https://example.invalid/protoc.zip", archive_path, max_bytes=8
        )

    assert not archive_path.exists()


def test_download_archive_rejects_stream_that_exceeds_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _Response(b"ninebytes"),
    )
    archive_path = tmp_path / "protoc.zip"

    with pytest.raises(RuntimeError, match="exceeds"):
        install_protoc.download_archive(
            "https://example.invalid/protoc.zip", archive_path, max_bytes=8
        )

    assert not archive_path.exists()


def test_verify_archive_sha256_rejects_mismatch() -> None:
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        install_protoc.verify_archive_sha256("0" * 64, "1" * 64, "protoc.zip")


def test_main_rejects_digest_mismatch_before_extraction_or_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )
    monkeypatch.setattr(
        install_protoc,
        "download_archive",
        lambda _url, _archive_path: "0" * 64,
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unverified archive was extracted or executed")

    monkeypatch.setattr(install_protoc.zipfile, "ZipFile", forbidden)
    monkeypatch.setattr(install_protoc.subprocess, "run", forbidden)

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        install_protoc.main()

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_main_preserves_existing_destination_when_staged_protoc_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = install_protoc.resolve_platform_asset()
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")

    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )

    def fake_download(_url: str, archive_path: Path) -> str:
        _write_archive(
            archive_path,
            [
                f"bin/{asset.executable_name}",
                "include/google/protobuf/descriptor.proto",
            ],
        )
        return install_protoc.load_default_sha256(asset)

    monkeypatch.setattr(install_protoc, "download_archive", fake_download)
    monkeypatch.setattr(
        install_protoc.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, "protoc --version")
        ),
    )

    with pytest.raises(subprocess.CalledProcessError):
        install_protoc.main()

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_replace_destination_installs_staging_and_removes_previous(
    tmp_path: Path,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old", encoding="utf-8")

    install_protoc.replace_destination(staging, destination)

    assert (destination / "new").read_text(encoding="utf-8") == "new"
    assert not (destination / "old").exists()
    assert not (transaction / "previous-install").exists()


def test_replace_destination_restores_previous_if_staging_rename_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    original_replace = Path.replace

    def fail_staging_replace(source: Path, target: Path) -> Path:
        if source == staging:
            raise OSError("injected staging rename failure")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_staging_replace)

    with pytest.raises(OSError, match="injected staging rename failure"):
        install_protoc.replace_destination(staging, destination)

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_replace_destination_retries_transient_windows_promotion_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old", encoding="utf-8")
    original_replace = Path.replace
    promotion_attempts = 0
    retry_delays: list[float] = []

    def transient_windows_failure() -> PermissionError:
        error = PermissionError(13, "Access is denied")
        error.winerror = 5
        return error

    def retry_promotion(source: Path, target: Path) -> Path:
        nonlocal promotion_attempts
        if source == staging:
            promotion_attempts += 1
            if promotion_attempts < 3:
                raise transient_windows_failure()
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", retry_promotion)
    monkeypatch.setattr(
        install_protoc,
        "_is_transient_windows_promotion_error",
        lambda error: getattr(error, "winerror", None) == 5,
    )
    monkeypatch.setattr(install_protoc.time, "sleep", retry_delays.append)

    install_protoc.replace_destination(staging, destination)

    assert promotion_attempts == 3
    assert retry_delays == [0.05, 0.1]
    assert (destination / "new").read_text(encoding="utf-8") == "new"
    assert not (destination / "old").exists()


def test_replace_destination_reports_exhausted_windows_promotion_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    original_replace = Path.replace
    promotion_attempts = 0
    retry_delays: list[float] = []

    def exhausted_windows_failure() -> PermissionError:
        error = PermissionError(13, "Access is denied")
        error.winerror = 5
        return error

    def fail_every_promotion(source: Path, target: Path) -> Path:
        nonlocal promotion_attempts
        if source == staging:
            promotion_attempts += 1
            raise exhausted_windows_failure()
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_every_promotion)
    monkeypatch.setattr(
        install_protoc,
        "_is_transient_windows_promotion_error",
        lambda error: getattr(error, "winerror", None) == 5,
    )
    monkeypatch.setattr(install_protoc.time, "sleep", retry_delays.append)

    with pytest.raises(PermissionError, match="Access is denied") as raised:
        install_protoc.replace_destination(staging, destination)

    assert promotion_attempts == install_protoc._WINDOWS_PROMOTION_RETRY_ATTEMPTS
    assert retry_delays == [0.05, 0.1, 0.2, 0.4]
    assert "retried the Windows protoc promotion" in "\n".join(raised.value.__notes__)
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert (staging / "new").read_text(encoding="utf-8") == "new"


@pytest.mark.parametrize("promoted_new_install", [False, True])
def test_next_install_recovers_an_interrupted_swap(
    tmp_path: Path,
    promoted_new_install: bool,
) -> None:
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "known-good").write_text("preserve", encoding="utf-8")
    rollback = _leave_owned_install_rollback(destination)
    if promoted_new_install:
        destination.mkdir()
        (destination / "partial").write_text("discard", encoding="utf-8")

    install_protoc._recover_interrupted_install_state(destination)

    assert (destination / "known-good").read_text(encoding="utf-8") == "preserve"
    assert not (destination / "partial").exists()
    assert not rollback.exists()


def _leave_owned_install_rollback(destination: Path) -> Path:
    owner = install_protoc._create_install_transaction(destination, "transaction")
    rollback = install_protoc._installation_rollback_path(destination)
    destination.replace(rollback)
    owner.bind_path("rollback", rollback)
    owner.close(remove_marker=False)
    return rollback


def _install_crash_test_environment(
    monkeypatch: pytest.MonkeyPatch,
    state_directory: Path,
) -> dict[str, str]:
    monkeypatch.setenv("PROTOCYTE_TRANSACTION_STATE_DIR", str(state_directory))
    environment = os.environ.copy()
    source_root = Path(__file__).resolve().parents[1] / "src"
    python_path = [str(source_root)]
    if existing := environment.get("PYTHONPATH"):
        python_path.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    return environment


def test_destination_lock_recovers_state_left_by_a_hard_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("lock_crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module.locked_destination(destination):
    os._exit(86)
"""

    result = subprocess.run(
        [sys.executable, "-c", script, str(script_path), str(destination)],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 86, result.stdout + result.stderr
    assert any(path.is_dir() for path in state_directory.iterdir())

    with install_protoc.locked_destination(destination):
        pass

    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def test_destination_lock_prune_and_reopen_never_split_the_lock_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    environment = _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    start = tmp_path / "start"
    violation = tmp_path / "mutual-exclusion-violation"
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import sys
import time
from pathlib import Path

script_path, destination, start, violation = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location("lock_race_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
critical = destination.with_name(".protocyte-lock-critical")
while not start.exists():
    time.sleep(0.005)
for _ in range(12):
    with module.locked_destination(destination):
        try:
            critical.mkdir()
        except FileExistsError:
            violation.touch()
            raise
        try:
            time.sleep(0.003)
        finally:
            critical.rmdir()
"""
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(script_path),
                str(destination),
                str(start),
                str(violation),
            ],
            cwd=script_path.parents[2],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for _ in range(4)
    ]
    outputs: list[tuple[str, str]] = []
    try:
        start.touch()
        outputs = [process.communicate(timeout=20.0) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    for process, (stdout, stderr) in zip(processes, outputs, strict=True):
        assert process.returncode == 0, stdout + stderr
    assert not violation.exists()
    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def test_owned_recovery_does_not_scan_the_global_state_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state"
    _install_crash_test_environment(monkeypatch, state_directory)
    destination = tmp_path / "protoc"
    owner = install_protoc._create_install_transaction(destination, "transaction")
    (owner.path / "dead").write_text("dead\n", encoding="utf-8")
    owner.close(remove_marker=False)
    original_iterdir = Path.iterdir

    def reject_global_scan(path: Path):
        if path == state_directory:
            raise AssertionError("recovery scanned the global transaction state")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", reject_global_scan)

    with install_protoc.locked_destination(destination):
        install_protoc.recover_owned_siblings(
            destination,
            ("transaction",),
            install_protoc._remove_path,
        )

    assert not owner.path.exists()
    assert _transaction_state_entries(state_directory) == {"registry.lock"}


def _run_install_hard_exit(
    destination: Path,
    phase: str,
    environment: dict[str, str],
    *,
    recovery_only: bool = False,
) -> None:
    script_path = Path(install_protoc.__file__).resolve()
    script = r"""
import importlib.util
import os
import sys
from pathlib import Path

script_path = Path(sys.argv[1])
destination = Path(sys.argv[2])
interrupted_phase = sys.argv[3]
recovery_only = sys.argv[4] == "recovery"
spec = importlib.util.spec_from_file_location("crash_install_protoc", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def hard_exit(phase: str) -> None:
    if phase == interrupted_phase:
        os._exit(89)

module._install_swap_phase = hard_exit
with module.locked_destination(destination):
    module._recover_interrupted_install_state(destination)
    if not recovery_only:
        owner = module._create_install_transaction(destination, "transaction")
        staging = owner.path / "install"
        staging.mkdir()
        (staging / "new").write_text("new\n", encoding="utf-8")
        try:
            module.replace_destination(staging, destination, owner)
        finally:
            module._cleanup_install_transaction(owner)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(script_path),
            str(destination),
            phase,
            "recovery" if recovery_only else "install",
        ],
        cwd=script_path.parents[2],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 89, result.stdout + result.stderr


def _owned_install_siblings(destination: Path) -> set[Path]:
    pattern = re.compile(
        rf"\.{re.escape(destination.name)}\.protocyte-"
        r"(?:transaction|recovery)-[0-9a-f]{32}"
    )
    return {
        path for path in destination.parent.iterdir() if pattern.fullmatch(path.name)
    }


@pytest.mark.parametrize(
    ("interrupted_phase", "expected_file"),
    [
        ("before_backup", "old"),
        ("after_backup", "old"),
        ("before_cleanup", "new"),
    ],
)
def test_install_recovery_cleans_owned_hard_exit_transactions_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupted_phase: str,
    expected_file: str,
) -> None:
    environment = _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old\n", encoding="utf-8")
    unowned = tmp_path / (".protoc.protocyte-transaction-" + "e" * 32)
    unowned.mkdir()
    (unowned / "keep").write_text("unowned\n", encoding="utf-8")

    _run_install_hard_exit(destination, interrupted_phase, environment)

    with install_protoc.locked_destination(destination):
        install_protoc._recover_interrupted_install_state(destination)

    assert {path.name for path in destination.iterdir()} == {expected_file}
    assert (unowned / "keep").read_text(encoding="utf-8") == "unowned\n"
    assert _owned_install_siblings(destination) == {unowned}
    assert not install_protoc._installation_rollback_path(destination).exists()


def test_install_recovery_survives_a_hard_exit_mid_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old\n", encoding="utf-8")
    rollback = _leave_owned_install_rollback(destination)
    destination.mkdir()
    (destination / "new").write_text("new\n", encoding="utf-8")

    _run_install_hard_exit(
        destination,
        "recovery_after_displace",
        environment,
        recovery_only=True,
    )

    with install_protoc.locked_destination(destination):
        install_protoc._recover_interrupted_install_state(destination)

    assert (destination / "old").read_text(encoding="utf-8") == "old\n"
    assert not (destination / "new").exists()
    assert not rollback.exists()
    assert not _owned_install_siblings(destination)


def test_unowned_install_rollback_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "live").write_text("live\n", encoding="utf-8")
    rollback = install_protoc._installation_rollback_path(destination)
    rollback.mkdir()
    (rollback / "unowned").write_text("unowned\n", encoding="utf-8")

    with install_protoc.locked_destination(destination):
        with pytest.raises(RuntimeError, match="unowned or replaced.*left unchanged"):
            install_protoc._recover_interrupted_install_state(destination)

    assert (destination / "live").read_text(encoding="utf-8") == "live\n"
    assert (rollback / "unowned").read_text(encoding="utf-8") == "unowned\n"


def _create_install_rollback_lookalike(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            pytest.skip("Windows junction creation is unavailable: " + result.stderr)
        return
    link.symlink_to(target, target_is_directory=True)


def test_replaced_install_rollback_lookalike_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_crash_test_environment(monkeypatch, tmp_path / "state")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old\n", encoding="utf-8")
    rollback = _leave_owned_install_rollback(destination)
    original_rollback = tmp_path / "owned-rollback"
    rollback.replace(original_rollback)
    lookalike_target = tmp_path / "lookalike-target"
    lookalike_target.mkdir()
    (lookalike_target / "keep").write_text("keep\n", encoding="utf-8")
    _create_install_rollback_lookalike(rollback, lookalike_target)
    destination.mkdir()
    (destination / "live").write_text("live\n", encoding="utf-8")

    try:
        with install_protoc.locked_destination(destination):
            with pytest.raises(
                RuntimeError, match="unowned or replaced.*left unchanged"
            ):
                install_protoc._recover_interrupted_install_state(destination)

        assert (destination / "live").read_text(encoding="utf-8") == "live\n"
        assert (lookalike_target / "keep").read_text(encoding="utf-8") == "keep\n"
        assert (original_rollback / "old").read_text(encoding="utf-8") == "old\n"
        assert rollback.exists()
    finally:
        if os.name == "nt" and rollback.exists():
            os.rmdir(rollback)


def test_resolve_release_requires_digest_for_version_override() -> None:
    asset = install_protoc.resolve_platform_asset("Linux", "x86_64")
    with pytest.raises(RuntimeError, match="--sha256 is required"):
        install_protoc.resolve_release("999.0", None, asset)


@pytest.mark.parametrize(
    ("system", "machine", "archive_suffix", "checksum_variable", "executable_name"),
    [
        (
            "Linux",
            "AMD64",
            "linux-x86_64",
            "PROTOCYTE_PROTOBUF_LINUX_X86_64_SHA256",
            "protoc",
        ),
        (
            "Windows",
            "x86_64",
            "win64",
            "PROTOCYTE_PROTOBUF_WINDOWS_X86_64_SHA256",
            "protoc.exe",
        ),
        (
            "Darwin",
            "x86_64",
            "osx-universal_binary",
            "PROTOCYTE_PROTOBUF_MACOS_UNIVERSAL_SHA256",
            "protoc",
        ),
        (
            "Darwin",
            "arm64",
            "osx-universal_binary",
            "PROTOCYTE_PROTOBUF_MACOS_UNIVERSAL_SHA256",
            "protoc",
        ),
        (
            "Darwin",
            "aarch64",
            "osx-universal_binary",
            "PROTOCYTE_PROTOBUF_MACOS_UNIVERSAL_SHA256",
            "protoc",
        ),
    ],
)
def test_resolve_platform_asset_selects_supported_archive(
    system: str,
    machine: str,
    archive_suffix: str,
    checksum_variable: str,
    executable_name: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)

    assert asset == install_protoc.ProtocAsset(
        archive_suffix=archive_suffix,
        checksum_variable=checksum_variable,
        executable_name=executable_name,
    )


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Darwin", "i386"),
        ("Linux", "aarch64"),
        ("Windows", "x86"),
    ],
)
def test_resolve_platform_asset_rejects_unsupported_host(
    system: str,
    machine: str,
) -> None:
    with pytest.raises(RuntimeError, match="unsupported protoc prebuilt platform"):
        install_protoc.resolve_platform_asset(system, machine)


@pytest.mark.parametrize(
    ("system", "machine", "expected_sha256"),
    [
        (
            "Linux",
            "x86_64",
            "af27ea66cd26938fe48587804ca7d4817457a08350021a1c6e23a27ccc8c6904",
        ),
        (
            "Windows",
            "AMD64",
            "6d7ebdc75e9c1f0026d4fb28f17ef1d0aae77d36744d83a9e052d79ba493724f",
        ),
        (
            "Darwin",
            "x86_64",
            "5c6057638aa382542e75f1c5a0802893e2311ad0c8b689e635dd4ac3c9eb8169",
        ),
        (
            "Darwin",
            "arm64",
            "5c6057638aa382542e75f1c5a0802893e2311ad0c8b689e635dd4ac3c9eb8169",
        ),
    ],
)
def test_configured_release_digests_match_upstream_assets(
    system: str,
    machine: str,
    expected_sha256: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)
    version, sha256 = install_protoc.resolve_release(None, None, asset)

    assert version == "34.1"
    assert sha256 == expected_sha256


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Linux", "x86_64"),
        ("Windows", "AMD64"),
        ("Darwin", "arm64"),
    ],
)
def test_main_installs_selected_platform_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    machine: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)
    destination = tmp_path / "protoc"
    github_output = tmp_path / "github-output"
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )
    monkeypatch.setattr(install_protoc, "resolve_platform_asset", lambda: asset)

    def fake_download(url: str, archive_path: Path) -> str:
        observed["url"] = url
        _write_archive(
            archive_path,
            [
                f"bin/{asset.executable_name}",
                "include/google/protobuf/descriptor.proto",
            ],
        )
        return install_protoc.load_default_sha256(asset)

    def fake_run(command: list[str], *, check: bool) -> None:
        observed["command"] = command
        observed["check"] = check

    monkeypatch.setattr(install_protoc, "download_archive", fake_download)
    monkeypatch.setattr(install_protoc.subprocess, "run", fake_run)
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    assert install_protoc.main() == 0

    archive_name = f"protoc-34.1-{asset.archive_suffix}.zip"
    assert observed["url"] == (
        "https://github.com/protocolbuffers/protobuf/releases/download/"
        f"v34.1/{archive_name}"
    )
    command = observed["command"]
    assert isinstance(command, list)
    assert Path(command[0]).name == asset.executable_name
    assert command[1:] == ["--version"]
    assert observed["check"] is True
    assert (destination / "bin" / asset.executable_name).is_file()
    assert (
        destination / "include" / "google" / "protobuf" / "descriptor.proto"
    ).is_file()
    assert (destination / install_protoc.VERSION_MARKER).read_text(
        encoding="utf-8"
    ) == "34.1\n"
    outputs = github_output.read_text(encoding="utf-8").splitlines()
    assert "version=34.1" in outputs
    assert f"root={destination.as_posix()}" in outputs
    assert (
        f"protoc={(destination / 'bin' / asset.executable_name).as_posix()}" in outputs
    )
    assert f"include={(destination / 'include').as_posix()}" in outputs


@pytest.mark.parametrize(
    "member",
    [
        "/tmp/protoc",
        r"C:\tmp\protoc.exe",
        r"\tmp\protoc.exe",
        "../protoc",
        "bin/../../protoc",
        r"bin\..\protoc.exe",
    ],
)
def test_extract_archive_safely_rejects_absolute_or_parent_traversal_members(
    tmp_path: Path,
    member: str,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, [member, "bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="unsafe"):
            install_protoc.extract_archive_safely(archive, destination)

    assert not destination.exists()


def test_extract_archive_safely_rejects_too_many_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc", "include/descriptor.proto"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="more than 1 members"):
            install_protoc.extract_archive_safely(archive, destination, max_members=1)

    assert not destination.exists()


def test_extract_archive_safely_rejects_oversized_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="member exceeds"):
            install_protoc.extract_archive_safely(
                archive, destination, max_member_bytes=6
            )

    assert not destination.exists()


def test_extract_archive_safely_rejects_oversized_uncompressed_total(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc", "include/descriptor.proto"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="uncompressed-size limit"):
            install_protoc.extract_archive_safely(
                archive, destination, max_uncompressed_bytes=13
            )

    assert not destination.exists()
