from __future__ import annotations

import subprocess
from pathlib import Path


def test_posix_wrapper_shell_quotes_single_quotes(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "quote_test.cmake"
    quoted_output = tmp_path / "quoted.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_shell_single_quote(quoted "alpha\'beta")',
                f'file(WRITE "{quoted_output.as_posix()}" "${{quoted}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert quoted_output.read_text(encoding="utf-8") == "'alpha'\"'\"'beta'"


def test_resolve_protobuf_import_dir_from_protoc_layout(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "resolve_protoc_import_dir.cmake"
    resolved_output = tmp_path / "resolved.txt"
    protoc = tmp_path / "toolchain" / "bin" / "protoc"
    descriptor = tmp_path / "toolchain" / "include" / "google" / "protobuf" / "descriptor.proto"

    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    descriptor.parent.mkdir(parents=True, exist_ok=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "_protocyte_resolve_protobuf_import_dir()",
                f'file(WRITE "{resolved_output.as_posix()}" "${{PROTOCYTE_PROTOBUF_IMPORT_DIR}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert resolved_output.read_text(encoding="utf-8") == (tmp_path / "toolchain" / "include").as_posix()


def test_generator_parameter_encoding_uses_hex_transport(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "encode_test.cmake"
    encoded_output = tmp_path / "encoded.txt"
    raw = "runtime=emit:C:/toolchain/runtime,clang_format=C:/Program Files/LLVM/bin/clang-format.exe"
    expected = "_protocyte_options_hex=" + raw.encode("utf-8").hex()

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'_protocyte_encode_generator_parameter(encoded "{raw}")',
                f'file(WRITE "{encoded_output.as_posix()}" "${{encoded}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert encoded_output.read_text(encoding="utf-8") == expected


def test_generate_accepts_relative_proto_root_at_configure_time(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    descriptor = source_dir / "protobuf" / "google" / "protobuf" / "descriptor.proto"
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"

    proto_dir.mkdir(parents=True)
    (proto_dir / "demo.proto").write_text('syntax = "proto3"; message Demo {}\n', encoding="utf-8")
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(relative_proto_root LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(source_dir / "protobuf").as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                "    PROTO_ROOT proto",
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)


def test_cmake_requires_python_314_for_codegen_wrapper() -> None:
    functions = (Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteFunctions.cmake").read_text(
        encoding="utf-8"
    )

    assert "find_package(Python3 3.14 COMPONENTS Interpreter REQUIRED)" in functions


def test_prerelease_cmake_version_file_marks_versioned_requests_unsuitable() -> None:
    template = (
        Path(__file__).resolve().parents[1] / "cmake" / "protocyteConfigVersionPrerelease.cmake.in"
    ).read_text(encoding="utf-8")

    assert 'set(PACKAGE_VERSION "@PROTOCYTE_VERSION@")' in template
    assert "if(PACKAGE_FIND_VERSION)" in template
    assert "set(PACKAGE_VERSION_UNSUITABLE TRUE)" in template
