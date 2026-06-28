from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2


def _find_real_protoc(repo_root: Path) -> Path:
    candidates: list[Path] = []
    if found := shutil.which("protoc"):
        candidates.append(Path(found))

    executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    for root in (repo_root / "build", repo_root / "tests"):
        if root.exists():
            candidates.extend(root.glob(f"**/{executable_name}"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    pytest.skip("real protoc executable is not available")


def test_installed_cmake_config_tracks_descriptor_set_helper() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_config = (repo_root / "cmake" / "Protocyte.cmake").read_text(encoding="utf-8")
    installed_config = (repo_root / "cmake" / "protocyteConfig.cmake.in").read_text(encoding="utf-8")

    assert '"${PROTOCYTE_PACKAGE_ROOT}/descriptor_set.py"' in source_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/descriptor_set.py"' in installed_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/extensions.py"' in source_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/extensions.py"' in installed_config


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


def test_cmake_discovery_split_normalizes_crlf_descriptor_names(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "split_discovered_names.cmake"
    output = tmp_path / "names.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_split_discovered_descriptor_names(names "api/one.proto\r\napi/two.proto")',
                'foreach(name IN LISTS names)',
                '    string(APPEND encoded "${name}|")',
                "endforeach()",
                f'file(WRITE "{output.as_posix()}" "${{encoded}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert output.read_text(encoding="utf-8") == "api/one.proto|api/two.proto|"


def test_cmake_descriptor_name_validator_rejects_drive_relative_paths(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "descriptor_name_validator.cmake"
    output = tmp_path / "unsafe.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_descriptor_name_is_unsafe(unsafe "C:foo.proto")',
                f'file(WRITE "{output.as_posix()}" "${{unsafe}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert output.read_text(encoding="utf-8") == "TRUE"


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


def test_generate_accepts_descriptor_set_protos_without_proto_root(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_codegen LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS nested/demo.proto",
                "    GENERATED_HEADERS_VAR generated_headers",
                "    GENERATED_SOURCES_VAR generated_sources",
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/headers.txt" "${generated_headers}")',
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/sources.txt" "${generated_sources}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    assert (build_dir / "headers.txt").read_text(encoding="utf-8").endswith(
        "generated/nested/demo.protocyte.hpp"
    )
    assert (build_dir / "sources.txt").read_text(encoding="utf-8").endswith(
        "generated/nested/demo.protocyte.cpp"
    )


def test_generate_descriptor_set_discover_skips_google_protobuf_files(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    runtime = file_set.file.add()
    runtime.name = "google/protobuf/descriptor.proto"
    runtime.syntax = "proto2"
    timestamp = file_set.file.add()
    timestamp.name = "google/protobuf/timestamp.proto"
    timestamp.package = "google.protobuf"
    timestamp.syntax = "proto3"
    timestamp_message = timestamp.message_type.add()
    timestamp_message.name = "Timestamp"
    seconds = timestamp_message.field.add()
    seconds.name = "seconds"
    seconds.number = 1
    seconds.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    seconds.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
    options = file_set.file.add()
    options.name = "protocyte/options.proto"
    options.syntax = "proto2"
    options.dependency.append("google/protobuf/descriptor.proto")
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.dependency.append("protocyte/options.proto")
    user.dependency.append("google/protobuf/timestamp.proto")
    user_message = user.message_type.add()
    user_message.name = "Demo"
    created_at = user_message.field.add()
    created_at.name = "created_at"
    created_at.number = 1
    created_at.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    created_at.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    created_at.type_name = ".google.protobuf.Timestamp"
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                "    GENERATED_HEADERS_VAR generated_headers",
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/headers.txt" "${generated_headers}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    headers = (build_dir / "headers.txt").read_text(encoding="utf-8")
    assert "generated/api/demo.protocyte.hpp" in headers
    assert "generated/google/protobuf/timestamp.protocyte.hpp" in headers


def test_descriptor_set_discover_tracks_descriptor_set_as_configure_input(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover_configure_depends LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "get_property(configure_depends DIRECTORY PROPERTY CMAKE_CONFIGURE_DEPENDS)",
                f'if(NOT "{descriptor_set.as_posix()}" IN_LIST configure_depends)',
                '    message(FATAL_ERROR "descriptor-set DISCOVER did not track descriptor set as a configure input")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)


def test_descriptor_set_discover_preserves_existing_pythonpath(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    pythonpath_dir = source_dir / "pythonpath"
    pythonpath_dir.mkdir()
    marker = build_dir / "pythonpath_seen.txt"
    (pythonpath_dir / "sitecustomize.py").write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                f"protocyte_source_root = Path({str(repo_root / 'src')!r}).resolve()",
                "has_protocyte_source = any(Path(entry).resolve() == protocyte_source_root for entry in sys.path if entry)",
                "is_descriptor_set_discovery = any('descriptor_set' in arg for arg in sys.argv)",
                "if has_protocyte_source and is_descriptor_set_discovery:",
                f"    Path({str(marker)!r}).parent.mkdir(parents=True, exist_ok=True)",
                f"    Path({str(marker)!r}).write_text('seen', encoding='utf-8')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover_pythonpath LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(pythonpath_dir)
    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True, env=env)

    assert marker.read_text(encoding="utf-8") == "seen"


def test_descriptor_set_rejects_unsafe_descriptor_name_at_configure_time(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_unsafe_name LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS nested/./demo.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "descriptor file name contains an unsafe path segment: nested/./demo.proto" in (
        result.stdout + result.stderr
    )


def test_descriptor_set_codegen_target_uses_descriptor_set_in_without_proto_paths(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    tools_dir = source_dir / "tools"
    tools_dir.mkdir()
    args_path = build_dir / "protoc_args.txt"
    fake_protoc_py = tools_dir / "fake_protoc.py"
    fake_protoc_py.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                f"Path({str(args_path)!r}).parent.mkdir(parents=True, exist_ok=True)",
                f"Path({str(args_path)!r}).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')",
                "out_dir = None",
                "for arg in sys.argv[1:]:",
                "    if arg.startswith('--protocyte_out='):",
                "        out_dir = Path(arg.split('=', 1)[1])",
                "if out_dir is None:",
                "    raise SystemExit('missing --protocyte_out')",
                "for name in sys.argv[1:]:",
                "    if not name.endswith('.proto'):",
                "        continue",
                "    base = out_dir / name.removesuffix('.proto')",
                "    base.parent.mkdir(parents=True, exist_ok=True)",
                "    base.with_suffix('.protocyte.hpp').write_text('// h\\n', encoding='utf-8')",
                "    base.with_suffix('.protocyte.cpp').write_text('// cc\\n', encoding='utf-8')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if os.name == "nt":
        protoc = tools_dir / "protoc.cmd"
        protoc.write_text(f'@echo off\r\n"{Path(sys.executable)}" "{fake_protoc_py}" %*\r\n', encoding="utf-8")
    else:
        protoc = tools_dir / "protoc"
        protoc.write_text(f'#!/usr/bin/env sh\nexec "{Path(sys.executable)}" "{fake_protoc_py}" "$@"\n', encoding="utf-8")
        protoc.chmod(0o755)
    plugin = tools_dir / "protoc-gen-protocyte"
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_build LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS nested/demo.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True)

    args = args_path.read_text(encoding="utf-8").splitlines()
    assert f"--descriptor_set_in={descriptor_set.as_posix()}" in args
    assert not any(arg.startswith("--proto_path=") for arg in args)
    assert "nested/demo.proto" in args


def test_descriptor_set_codegen_builds_with_real_protoc_descriptor_set_in(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    descriptor_set = source_dir / "descriptor_set.pb"
    demo_proto = proto_dir / "api" / "demo.proto"
    demo_proto.parent.mkdir()
    demo_proto.write_text(
        'syntax = "proto3"; package api; message Demo { int32 id = 1; }\n',
        encoding="utf-8",
    )

    subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_dir}",
            f"--descriptor_set_out={descriptor_set}",
            "--include_imports",
            "api/demo.proto",
        ],
        cwd=proto_dir,
        check=True,
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(real_descriptor_set_build LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS api/demo.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True)

    header = build_dir / "generated" / "api" / "demo.protocyte.hpp"
    source = build_dir / "generated" / "api" / "demo.protocyte.cpp"
    assert header.is_file()
    assert source.is_file()
    assert "struct Demo" in header.read_text(encoding="utf-8")


def test_descriptor_set_library_wrapper_configures_alias_target(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    protoc = source_dir / "tools" / "protoc"
    plugin = source_dir / "tools" / "protoc-gen-protocyte"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    plugin.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_library LANGUAGES CXX)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'add_subdirectory("{repo_root.as_posix()}" "${{CMAKE_CURRENT_BINARY_DIR}}/protocyte")',
                "protocyte_add_descriptor_set_library(",
                "    TARGET demo_proto",
                "    ALIAS demo::proto",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                "    FILES nested/demo.proto",
                "    GENERATED_HEADERS_VAR generated_headers",
                "    GENERATED_SOURCES_VAR generated_sources",
                "    GENERATED_TARGET_VAR generated_target",
                ")",
                "if(NOT TARGET demo::proto)",
                '    message(FATAL_ERROR "descriptor-set alias target was not created")',
                "endif()",
                'if(NOT generated_headers MATCHES "nested/demo[.]protocyte[.]hpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated headers")',
                "endif()",
                'if(NOT generated_sources MATCHES "nested/demo[.]protocyte[.]cpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated sources")',
                "endif()",
                'if(NOT generated_target STREQUAL "demo_proto__protocyte_codegen")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated target")',
                "endif()",
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


def test_smoke_cmake_gates_std_format_opt_in_on_compile_probe() -> None:
    smoke_cmake = (
        Path(__file__).resolve().parents[1] / "tests" / "smoke" / "CMakeLists.txt"
    ).read_text(encoding="utf-8")

    assert "include(CheckCXXSourceCompiles)" in smoke_cmake
    assert "check_cxx_source_compiles(" in smoke_cmake
    assert "#include <version>" in smoke_cmake
    assert "#if !defined(__cpp_lib_format) || __cpp_lib_format < 201907L" in smoke_cmake
    assert '#error "std::format is unavailable"' in smoke_cmake
    assert "#include <format>" in smoke_cmake
    assert "#include <string_view>" in smoke_cmake
    assert "::std::formatter<::std::string_view, char>" in smoke_cmake
    assert "::std::format(\"{}\", ::std::string_view {\"ok\"})" in smoke_cmake
    assert "PROTOCYTE_SMOKE_HAS_STD_FORMAT" in smoke_cmake
    assert "if(PROTOCYTE_SMOKE_HAS_STD_FORMAT)" in smoke_cmake
    assert "target_compile_definitions(\"${target_name}\" PRIVATE PROTOCYTE_ENABLE_STD_FORMAT=1)" in smoke_cmake
    assert "\n        PROTOCYTE_ENABLE_STD_FORMAT=1" not in smoke_cmake
    assert "\n            PROTOCYTE_ENABLE_STD_FORMAT=1" not in smoke_cmake


def test_prerelease_cmake_version_file_marks_versioned_requests_unsuitable() -> None:
    template = (
        Path(__file__).resolve().parents[1] / "cmake" / "protocyteConfigVersionPrerelease.cmake.in"
    ).read_text(encoding="utf-8")

    assert 'set(PACKAGE_VERSION "@PROTOCYTE_VERSION@")' in template
    assert "if(PACKAGE_FIND_VERSION)" in template
    assert "set(PACKAGE_VERSION_UNSUITABLE TRUE)" in template
