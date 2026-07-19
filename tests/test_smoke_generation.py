import os
import re
import subprocess
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2

from tests.smoke.tools import generate_checked_outputs


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

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
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

    assert generate_checked_outputs._resolve_protobuf_import_dir(protoc) == (
        install_root / "include"
    ).resolve()

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
    rollback = generate_checked_outputs._checked_output_rollback_path(
        checked_out_dir
    )
    checked_out_dir.replace(rollback)
    if promoted_new_tree:
        checked_out_dir.mkdir()
        (checked_out_dir / "current.hpp").write_text("current\n", encoding="utf-8")

    generate_checked_outputs._recover_interrupted_checked_output_swap(
        checked_out_dir
    )

    assert (checked_out_dir / "previous.hpp").read_text(encoding="utf-8") == (
        "previous\n"
    )
    assert not (checked_out_dir / "current.hpp").exists()
    assert not rollback.exists()


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
