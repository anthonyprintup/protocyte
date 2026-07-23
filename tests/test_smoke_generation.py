import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2

from tests.smoke.tools import generate_checked_outputs


def test_checked_smoke_cli_parses_arguments_before_resolving_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_resolved() -> str:
        pytest.fail(
            "smoke generation tools must not be resolved while parsing arguments"
        )

    monkeypatch.setattr(
        generate_checked_outputs,
        "_resolve_smoke_clang_format",
        fail_if_resolved,
    )

    with pytest.raises(SystemExit) as help_exit:
        generate_checked_outputs.main(["--help"])
    assert help_exit.value.code == 0

    with pytest.raises(SystemExit) as invalid_exit:
        generate_checked_outputs.main(["--definitely-invalid"])
    assert invalid_exit.value.code == 2


def test_checked_smoke_outputs_have_a_canonical_lf_checkout_policy() -> None:
    attributes = (generate_checked_outputs.ROOT / ".gitattributes").read_text(
        encoding="utf-8"
    )

    assert "tests/smoke/generated/** text eol=lf" in attributes.splitlines()


def test_canonical_smoke_specs_reference_repository_proto_sources() -> None:
    checked_sources = {
        path.name
        for path in generate_checked_outputs.SMOKE_PROTO_DIR.glob("*.proto")
        if path.name != "benchmark.proto"
    }

    assert {spec.source for spec in generate_checked_outputs.GENERATION_SPECS} == (
        checked_sources
    )
    assert not any(
        hasattr(generate_checked_outputs, mirror)
        for mirror in (
            "example_file",
            "compat_file",
            "cross_package_file",
            "proto2_required_file",
            "reserved_identifiers_file",
            "options_file",
        )
    )


def test_checked_smoke_generation_invokes_protoc_with_canonical_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run_protoc(
        protoc: Path,
        arguments: tuple[str, ...],
        *,
        response_file: Path,
    ) -> None:
        del protoc, response_file
        calls.append(arguments)
        descriptor_argument = next(
            (
                argument
                for argument in arguments
                if argument.startswith("--descriptor_set_out=")
            ),
            None,
        )
        if descriptor_argument is not None:
            descriptor_set = descriptor_pb2.FileDescriptorSet()
            descriptor_set.file.add().name = "compat.proto"
            Path(descriptor_argument.split("=", 1)[1]).write_bytes(
                descriptor_set.SerializeToString()
            )

    monkeypatch.setattr(
        generate_checked_outputs,
        "_resolve_smoke_protoc",
        lambda: Path("official-protoc"),
    )
    monkeypatch.setattr(
        generate_checked_outputs,
        "_resolve_smoke_plugin",
        lambda: Path("protoc-gen-protocyte"),
    )
    monkeypatch.setattr(
        generate_checked_outputs,
        "_resolve_protobuf_import_dir",
        lambda _protoc: Path("protobuf-imports"),
    )
    monkeypatch.setattr(
        generate_checked_outputs,
        "_verify_smoke_tools",
        lambda _protoc, _plugin, _clang_format: None,
    )
    monkeypatch.setattr(generate_checked_outputs, "_run_protoc", fake_run_protoc)
    monkeypatch.setattr(
        generate_checked_outputs,
        "compat_cases_header",
        lambda descriptor: f"// source: {descriptor.name}\n",
    )
    monkeypatch.setattr(
        generate_checked_outputs,
        "_clang_format_file",
        lambda *_args: None,
    )

    out_dir = tmp_path / "generated"
    out_dir.mkdir()
    error = generate_checked_outputs._write_checked_outputs(
        out_dir,
        "clang-format",
        tmp_path / ".clang-format",
    )

    assert error is None
    assert [call[-1] for call in calls[:-1]] == [
        spec.source for spec in generate_checked_outputs.GENERATION_SPECS
    ]
    assert calls[-1][-1] == "compat.proto"
    assert (out_dir / "compat_cases.hpp").read_text(encoding="utf-8") == (
        "// source: compat.proto\n"
    )


def test_canonical_smoke_tool_versions_are_repository_pinned() -> None:
    assert generate_checked_outputs.PINNED_PROTOC_VERSION == "34.1"
    assert generate_checked_outputs.PINNED_CLANG_FORMAT_VERSION == "22.1.4"


def test_canonical_smoke_tools_require_exact_pinned_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reported_versions = {
        "protoc": "libprotoc 34.0",
        "protoc-gen-protocyte": generate_checked_outputs.__version__,
        "clang-format": "clang-format version 22.1.4",
    }

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=f"{reported_versions[Path(command[0]).name]}\n",
            stderr="",
        )

    monkeypatch.setattr(generate_checked_outputs.subprocess, "run", fake_run)

    error = generate_checked_outputs._verify_smoke_tools(
        Path("protoc"),
        Path("protoc-gen-protocyte"),
        Path("clang-format"),
    )

    assert error is not None
    assert "libprotoc 34.1" in error
    assert "libprotoc 34.0" in error


def test_canonical_smoke_imports_must_match_repository_installed_protoc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_root = tmp_path / "protoc"
    protoc = install_root / "bin" / "protoc"
    descriptor = install_root / "include/google/protobuf/descriptor.proto"
    protoc.parent.mkdir(parents=True)
    descriptor.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    descriptor.write_text("", encoding="utf-8")
    (install_root / generate_checked_outputs.PROTOBUF_VERSION_MARKER).write_text(
        "34.1\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("PROTOCYTE_SMOKE_PROTOBUF_IMPORT_DIR", raising=False)

    assert (
        generate_checked_outputs._resolve_protobuf_import_dir(protoc)
        == (install_root / "include").resolve()
    )

    external_imports = tmp_path / "other-imports"
    (external_imports / "google/protobuf").mkdir(parents=True)
    (external_imports / "google/protobuf/descriptor.proto").write_text(
        "",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "PROTOCYTE_SMOKE_PROTOBUF_IMPORT_DIR",
        str(external_imports),
    )
    with pytest.raises(FileNotFoundError, match="import tree shipped"):
        generate_checked_outputs._resolve_protobuf_import_dir(protoc)


def test_checked_smoke_regeneration_replaces_the_owned_tree_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_out_dir = tmp_path / "generated"
    (checked_out_dir / "nested").mkdir(parents=True)
    (checked_out_dir / "kept-but-stale.hpp").write_text("stale\n", encoding="utf-8")
    (checked_out_dir / "nested" / "removed.cpp").write_text(
        "stale\n",
        encoding="utf-8",
    )

    def write_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> None:
        del clang_format, clang_format_config
        (out_dir / "nested").mkdir()
        (out_dir / "current.hpp").write_text("current\n", encoding="utf-8")
        (out_dir / "nested" / "current.cpp").write_text(
            "current\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        write_staged_outputs,
    )

    error = generate_checked_outputs._regenerate_checked_outputs(
        checked_out_dir,
        "unused-clang-format",
        tmp_path / ".clang-format",
    )

    assert error is None
    assert {
        path.relative_to(checked_out_dir).as_posix()
        for path in checked_out_dir.rglob("*")
        if path.is_file()
    } == {"current.hpp", "nested/current.cpp"}


def test_failed_smoke_regeneration_keeps_the_previous_checked_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    previous = checked_out_dir / "previous.hpp"
    previous.write_text("previous\n", encoding="utf-8")

    def fail_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> str:
        del clang_format, clang_format_config
        (out_dir / "partial.hpp").write_text("partial\n", encoding="utf-8")
        return "generation failed"

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        fail_staged_outputs,
    )

    error = generate_checked_outputs._regenerate_checked_outputs(
        checked_out_dir,
        "unused-clang-format",
        tmp_path / ".clang-format",
    )

    assert error == "generation failed"
    assert previous.read_text(encoding="utf-8") == "previous\n"
    assert not (checked_out_dir / "partial.hpp").exists()


@pytest.mark.parametrize(
    ("interrupted_phase", "expected_file"),
    [
        ("before_backup", "previous.hpp"),
        ("after_backup", "previous.hpp"),
        ("before_promote", "previous.hpp"),
        ("after_promote", "previous.hpp"),
        ("before_commit", "previous.hpp"),
        ("after_commit", "previous.hpp"),
        ("before_cleanup", "current.hpp"),
        ("after_cleanup", "current.hpp"),
    ],
)
def test_checked_smoke_swap_survives_interrupt_at_each_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupted_phase: str,
    expected_file: str,
) -> None:
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "previous.hpp").write_text("previous\n", encoding="utf-8")

    def write_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> None:
        del clang_format, clang_format_config
        (out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

    def interrupt(phase: str) -> None:
        if phase == interrupted_phase:
            raise KeyboardInterrupt(phase)

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        write_staged_outputs,
    )
    monkeypatch.setattr(
        generate_checked_outputs,
        "_checked_output_swap_phase",
        interrupt,
    )

    with pytest.raises(KeyboardInterrupt, match=interrupted_phase):
        generate_checked_outputs._regenerate_checked_outputs(
            checked_out_dir,
            "unused-clang-format",
            tmp_path / ".clang-format",
        )

    assert (checked_out_dir / expected_file).is_file()
    assert {path.name for path in checked_out_dir.iterdir()} == {expected_file}
    assert not generate_checked_outputs._checked_output_rollback_path(
        checked_out_dir
    ).exists()


@pytest.mark.parametrize(
    "interrupted_phase",
    [
        "before_backup",
        "after_backup",
        "before_promote",
        "after_promote",
        "before_commit",
        "after_commit",
    ],
)
def test_checked_smoke_swap_interrupt_without_previous_tree_leaves_no_partial_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupted_phase: str,
) -> None:
    checked_out_dir = tmp_path / "generated"

    def write_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> None:
        del clang_format, clang_format_config
        (out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

    def interrupt(phase: str) -> None:
        if phase == interrupted_phase:
            raise KeyboardInterrupt(phase)

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        write_staged_outputs,
    )
    monkeypatch.setattr(
        generate_checked_outputs,
        "_checked_output_swap_phase",
        interrupt,
    )

    with pytest.raises(KeyboardInterrupt, match=interrupted_phase):
        generate_checked_outputs._regenerate_checked_outputs(
            checked_out_dir,
            "unused-clang-format",
            tmp_path / ".clang-format",
        )

    assert not checked_out_dir.exists()
    assert not generate_checked_outputs._checked_output_rollback_path(
        checked_out_dir
    ).exists()


@pytest.mark.parametrize("promoted_new_tree", [False, True])
def test_next_regeneration_recovers_a_crash_before_commit(
    tmp_path: Path,
    promoted_new_tree: bool,
) -> None:
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "previous.hpp").write_text("previous\n", encoding="utf-8")
    rollback = _leave_owned_checked_output_rollback(checked_out_dir)
    if promoted_new_tree:
        checked_out_dir.mkdir()
        (checked_out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

    generate_checked_outputs._recover_interrupted_checked_output_state(checked_out_dir)

    assert (checked_out_dir / "previous.hpp").read_text(encoding="utf-8") == (
        "previous\n"
    )
    assert not (checked_out_dir / "current.hpp").exists()
    assert not rollback.exists()


def _leave_owned_checked_output_rollback(checked_out_dir: Path) -> Path:
    owner = generate_checked_outputs._create_checked_output_transaction(
        checked_out_dir, "transaction"
    )
    rollback = generate_checked_outputs._checked_output_rollback_path(checked_out_dir)
    checked_out_dir.replace(rollback)
    owner.bind_path("rollback", rollback)
    owner.close(remove_marker=False)
    return rollback


def _crash_test_environment(
    monkeypatch: pytest.MonkeyPatch,
    state_directory: Path,
) -> dict[str, str]:
    monkeypatch.setenv("PROTOCYTE_TRANSACTION_STATE_DIR", str(state_directory))
    environment = os.environ.copy()
    python_path = [
        str(generate_checked_outputs.ROOT),
        str(generate_checked_outputs.ROOT / "src"),
    ]
    if existing := environment.get("PYTHONPATH"):
        python_path.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    return environment


def _run_generator_hard_exit(
    checked_out_dir: Path,
    phase: str,
    environment: dict[str, str],
    *,
    recovery_only: bool = False,
) -> None:
    script = r"""
import os
import sys
from pathlib import Path
from tests.smoke.tools import generate_checked_outputs as generation

destination = Path(sys.argv[1])
interrupted_phase = sys.argv[2]
recovery_only = sys.argv[3] == "recovery"

def hard_exit(phase: str) -> None:
    if phase == interrupted_phase:
        os._exit(87)

def write_outputs(out_dir: Path, _clang_format: str, _config: Path) -> None:
    (out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

generation._checked_output_swap_phase = hard_exit
if recovery_only:
    with generation.locked_destination(destination):
        generation._recover_interrupted_checked_output_state(destination)
else:
    generation._write_checked_outputs = write_outputs
    generation._regenerate_checked_outputs(
        destination,
        "unused-clang-format",
        destination.parent / ".clang-format",
    )
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(checked_out_dir),
            phase,
            "recovery" if recovery_only else "regenerate",
        ],
        cwd=generate_checked_outputs.ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 87, result.stdout + result.stderr


def _owned_checked_output_siblings(checked_out_dir: Path) -> set[Path]:
    pattern = re.compile(
        rf"\.{re.escape(checked_out_dir.name)}\.protocyte-"
        r"(?:transaction|recovery)-[0-9a-f]{32}"
    )
    return {
        path
        for path in checked_out_dir.parent.iterdir()
        if pattern.fullmatch(path.name)
    }


@pytest.mark.parametrize(
    ("interrupted_phase", "expected_file"),
    [
        ("before_backup", "previous.hpp"),
        ("after_backup", "previous.hpp"),
        ("before_cleanup", "current.hpp"),
    ],
)
def test_checked_output_recovery_cleans_owned_hard_exit_transactions_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupted_phase: str,
    expected_file: str,
) -> None:
    environment = _crash_test_environment(monkeypatch, tmp_path / "state")
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "previous.hpp").write_text("previous\n", encoding="utf-8")
    unowned = tmp_path / (".generated.protocyte-transaction-" + "f" * 32)
    unowned.mkdir()
    (unowned / "keep").write_text("unowned\n", encoding="utf-8")

    _run_generator_hard_exit(
        checked_out_dir,
        interrupted_phase,
        environment,
    )

    with generate_checked_outputs.locked_destination(checked_out_dir):
        generate_checked_outputs._recover_interrupted_checked_output_state(
            checked_out_dir
        )

    assert {path.name for path in checked_out_dir.iterdir()} == {expected_file}
    assert (unowned / "keep").read_text(encoding="utf-8") == "unowned\n"
    assert _owned_checked_output_siblings(checked_out_dir) == {unowned}
    assert not generate_checked_outputs._checked_output_rollback_path(
        checked_out_dir
    ).exists()


def test_checked_output_recovery_survives_a_hard_exit_mid_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _crash_test_environment(monkeypatch, tmp_path / "state")
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "previous.hpp").write_text("previous\n", encoding="utf-8")
    rollback = _leave_owned_checked_output_rollback(checked_out_dir)
    checked_out_dir.mkdir()
    (checked_out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

    _run_generator_hard_exit(
        checked_out_dir,
        "recovery_after_displace",
        environment,
        recovery_only=True,
    )

    with generate_checked_outputs.locked_destination(checked_out_dir):
        generate_checked_outputs._recover_interrupted_checked_output_state(
            checked_out_dir
        )

    assert (checked_out_dir / "previous.hpp").read_text(encoding="utf-8") == (
        "previous\n"
    )
    assert not (checked_out_dir / "current.hpp").exists()
    assert not rollback.exists()
    assert not _owned_checked_output_siblings(checked_out_dir)


def test_unowned_checked_output_rollback_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _crash_test_environment(monkeypatch, tmp_path / "state")
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "live.hpp").write_text("live\n", encoding="utf-8")
    rollback = generate_checked_outputs._checked_output_rollback_path(checked_out_dir)
    rollback.mkdir()
    (rollback / "unowned.hpp").write_text("unowned\n", encoding="utf-8")

    with generate_checked_outputs.locked_destination(checked_out_dir):
        with pytest.raises(RuntimeError, match="unowned or replaced.*left unchanged"):
            generate_checked_outputs._recover_interrupted_checked_output_state(
                checked_out_dir
            )

    assert (checked_out_dir / "live.hpp").read_text(encoding="utf-8") == "live\n"
    assert (rollback / "unowned.hpp").read_text(encoding="utf-8") == "unowned\n"


def _create_directory_lookalike(link: Path, target: Path) -> None:
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


def test_replaced_checked_output_rollback_lookalike_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _crash_test_environment(monkeypatch, tmp_path / "state")
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "previous.hpp").write_text("previous\n", encoding="utf-8")
    rollback = _leave_owned_checked_output_rollback(checked_out_dir)
    original_rollback = tmp_path / "owned-rollback"
    rollback.replace(original_rollback)
    lookalike_target = tmp_path / "lookalike-target"
    lookalike_target.mkdir()
    (lookalike_target / "keep.hpp").write_text("keep\n", encoding="utf-8")
    _create_directory_lookalike(rollback, lookalike_target)
    checked_out_dir.mkdir()
    (checked_out_dir / "live.hpp").write_text("live\n", encoding="utf-8")

    try:
        with generate_checked_outputs.locked_destination(checked_out_dir):
            with pytest.raises(
                RuntimeError, match="unowned or replaced.*left unchanged"
            ):
                generate_checked_outputs._recover_interrupted_checked_output_state(
                    checked_out_dir
                )

        assert (checked_out_dir / "live.hpp").read_text(encoding="utf-8") == (
            "live\n"
        )
        assert (lookalike_target / "keep.hpp").read_text(encoding="utf-8") == (
            "keep\n"
        )
        assert (original_rollback / "previous.hpp").read_text(
            encoding="utf-8"
        ) == "previous\n"
        assert rollback.exists()
    finally:
        if os.name == "nt" and rollback.exists():
            os.rmdir(rollback)


def test_checked_output_recovery_skips_a_live_owned_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _crash_test_environment(monkeypatch, tmp_path / "state")
    checked_out_dir = tmp_path / "generated"
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    script = r"""
import sys
import time
from pathlib import Path
from tests.smoke.tools import generate_checked_outputs as generation

destination, ready, release = map(Path, sys.argv[1:])
owner = generation._create_checked_output_transaction(destination, "transaction")
(owner.path / "live").write_text("live\n", encoding="utf-8")
ready.write_text(str(owner.path), encoding="utf-8")
while not release.exists():
    time.sleep(0.01)
owner.cleanup(generation._remove_checked_output_path)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(checked_out_dir), str(ready), str(release)],
        cwd=generate_checked_outputs.ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        deadline = time.monotonic() + 5.0
        while not ready.exists() and process.poll() is None:
            if time.monotonic() >= deadline:
                pytest.fail("live transaction subprocess did not become ready")
            time.sleep(0.01)
        assert process.poll() is None
        live_transaction = Path(ready.read_text(encoding="utf-8"))

        generate_checked_outputs._recover_interrupted_checked_output_state(
            checked_out_dir
        )

        assert (live_transaction / "live").is_file()
    finally:
        release.touch()
        try:
            stdout, stderr = process.communicate(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            pytest.fail("live transaction subprocess did not exit:\n" + stdout + stderr)
    assert process.returncode == 0, stdout + stderr
    assert not _owned_checked_output_siblings(checked_out_dir)


def test_destination_kernel_lock_serializes_processes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _crash_test_environment(monkeypatch, tmp_path / "state")
    checked_out_dir = tmp_path / "generated"
    started = tmp_path / "started"
    acquired = tmp_path / "acquired"
    script = r"""
import sys
from pathlib import Path
from tests.smoke.tools import generate_checked_outputs as generation

destination, started, acquired = map(Path, sys.argv[1:])
started.touch()
with generation.locked_destination(destination):
    acquired.touch()
"""
    with generate_checked_outputs.locked_destination(checked_out_dir):
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(checked_out_dir),
                str(started),
                str(acquired),
            ],
            cwd=generate_checked_outputs.ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        deadline = time.monotonic() + 5.0
        while not started.exists() and process.poll() is None:
            if time.monotonic() >= deadline:
                process.kill()
                pytest.fail("lock contender subprocess did not become ready")
            time.sleep(0.01)
        time.sleep(0.1)
        assert process.poll() is None
        assert not acquired.exists()

    try:
        stdout, stderr = process.communicate(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        pytest.fail("lock contender did not acquire after release:\n" + stdout + stderr)
    assert process.returncode == 0, stdout + stderr
    assert acquired.is_file()


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL inheritance regression")
def test_checked_smoke_swap_preserves_parent_windows_acl_inheritance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    grant = subprocess.run(
        [
            "icacls.exe",
            str(workspace),
            "/grant",
            "*S-1-1-0:(OI)(CI)(RX)",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert grant.returncode == 0, grant.stdout + grant.stderr

    checked_out_dir = workspace / "generated"
    checked_out_dir.mkdir()
    (checked_out_dir / "previous.hpp").write_text("previous\n", encoding="utf-8")

    def write_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> None:
        del clang_format, clang_format_config
        (out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        write_staged_outputs,
    )

    assert (
        generate_checked_outputs._regenerate_checked_outputs(
            checked_out_dir,
            "unused-clang-format",
            tmp_path / ".clang-format",
        )
        is None
    )

    for index, path in enumerate((checked_out_dir, checked_out_dir / "current.hpp")):
        saved_acl = tmp_path / f"promoted-{index}.acl"
        save_result = subprocess.run(
            [
                "icacls.exe",
                str(path),
                "/save",
                str(saved_acl),
                "/c",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert save_result.returncode == 0, save_result.stdout + save_result.stderr
        acl = saved_acl.read_text(encoding="utf-16-le")
        assert re.search(r"\(A;[^;]*ID;[^;]+;;;WD\)", acl), (
            f"{path} did not inherit the workspace's Everyone ACL:\n{acl}"
        )
