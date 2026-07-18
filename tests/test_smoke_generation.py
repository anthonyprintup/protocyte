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
        lambda _protoc, _plugin: None,
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
