from __future__ import annotations

import os
from pathlib import Path
from shutil import which
import subprocess

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte.model import build_model
from protocyte.plugin import generate_response


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = Path(__file__).with_name("fixtures") / "bad_identifiers"
CORPUS_FILES = (
    "types.proto",
    "bad_identifiers.proto",
    "consumer.proto",
    "std.proto",
    "protocyte.proto",
    "protocyte_user.proto",
    "prefix.proto",
    "prefix_root.proto",
)


def _protoc() -> str:
    executable = which("protoc")
    if executable is None:
        pytest.skip("protoc is required for the upstream bad-identifier corpus")
    return executable


def _descriptor_request(
    tmp_path: Path,
    *,
    files: tuple[str, ...] = CORPUS_FILES,
    parameter: str = "format=off,runtime=emit",
) -> plugin_pb2.CodeGeneratorRequest:
    descriptor_path = tmp_path / "bad-identifiers.pb"
    subprocess.run(
        [
            _protoc(),
            f"--proto_path={CORPUS_ROOT}",
            f"--proto_path={REPO_ROOT / 'src' / 'protocyte' / 'proto'}",
            f"--descriptor_set_out={descriptor_path}",
            "--include_imports",
            *files,
        ],
        check=True,
        cwd=CORPUS_ROOT,
    )
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(descriptor_path.read_bytes())
    return plugin_pb2.CodeGeneratorRequest(
        file_to_generate=list(files),
        parameter=parameter,
        proto_file=descriptor_set.file,
    )


def _generated_files(
    tmp_path: Path, request: plugin_pb2.CodeGeneratorRequest
) -> dict[str, str]:
    response = generate_response(request)
    assert not response.error
    files = {item.name: item.content for item in response.file}
    for name, content in files.items():
        output = tmp_path / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    return files


def _compile_and_run(tmp_path: Path, source: str) -> None:
    compiler = which("clang++") or which("g++") or which("c++")
    if compiler is None:
        pytest.skip("a C++20 compiler is required for bad-identifier validation")
    main = tmp_path / "main.cpp"
    main.write_text(source, encoding="utf-8")
    executable = tmp_path / (
        "bad-identifiers.exe" if os.name == "nt" else "bad-identifiers"
    )
    generated_sources = sorted(str(path) for path in tmp_path.rglob("*.protocyte.cpp"))
    warning_args = (
        ["-Werror", "-Wreserved-identifier"]
        if "clang" in Path(compiler).name.lower()
        else []
    )
    subprocess.run(
        [
            compiler,
            "-std=c++20",
            *warning_args,
            "-DPROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1",
            "-I",
            str(tmp_path),
            str(main),
            *generated_sources,
            "-o",
            str(executable),
        ],
        check=True,
        cwd=tmp_path,
    )
    subprocess.run([str(executable)], check=True, cwd=tmp_path)


def test_stock_cpp_generator_accepts_bad_identifier_corpus(tmp_path: Path) -> None:
    output = tmp_path / "upstream-cpp"
    output.mkdir()
    subprocess.run(
        [
            _protoc(),
            f"--proto_path={CORPUS_ROOT}",
            f"--proto_path={REPO_ROOT / 'src' / 'protocyte' / 'proto'}",
            f"--cpp_out={output}",
            *CORPUS_FILES,
        ],
        check=True,
        cwd=CORPUS_ROOT,
    )


def test_bad_identifier_corpus_builds_model_and_generates(tmp_path: Path) -> None:
    request = _descriptor_request(tmp_path)

    model = build_model(request)
    response = generate_response(request)

    assert model.messages["compat.bad.foo"].cpp_name == "foo"
    assert model.messages["compat.bad.Foo"].cpp_name == "Foo"
    assert model.enums["compat.bad.state"].cpp_name == "state"
    assert model.enums["compat.bad.State"].cpp_name == "State"
    assert model.messages["protocyte.Result"].cpp_name.startswith("Result_protocyte_")
    assert model.messages["protocyte.read_varint"].cpp_name.startswith(
        "read_varint_protocyte_"
    )
    assert not response.error
    assert response.file
    files = {item.name: item.content for item in response.file}
    types_header = files["types.protocyte.hpp"]
    assert "using Payload = payload<Config>;" in types_header
    assert "using Foo = foo<Config>;" not in types_header
    assert "using Serialize = Container_serialize<CompatibilityConfig>;" in types_header
    assert "using Config = config<Config_>;" in types_header
    assert "using NestedConfig = Container_NestedConfig<NestedConfig_>;" in types_header
    assert (
        "using CompatibilityConfig = "
        "Container_compatibilityConfig<CompatibilityConfig_>;"
    ) in types_header


def test_bad_identifier_corpus_compiles_and_runs(tmp_path: Path) -> None:
    request = _descriptor_request(tmp_path)
    files = _generated_files(tmp_path, request)

    assert "namespace std {" in files["std.protocyte.hpp"]
    assert "namespace protocyte {" in files["protocyte.protocyte.hpp"]
    _compile_and_run(
        tmp_path,
        r"""
#include "bad_identifiers.protocyte.hpp"
#include "consumer.protocyte.hpp"
#include "protocyte.protocyte.hpp"
#include "protocyte_user.protocyte.hpp"
#include "std.protocyte.hpp"

int main() {
    auto ctx = ::protocyte::DefaultConfig::Context{
        ::protocyte::hosted_allocator(), ::protocyte::Limits{}};
    auto value = ::compat::bad::HelperFields<>::create(ctx);
    value.set_serialize(1);
    value.set_parse(2);
    value.set_context_(3);
    value.set_unknown_fields_(4);
    value.set_validate_(5);
    value.set_copy_from(6);
    if (value.serialize() != 1 || value.parse() != 2 || value.context_() != 3 ||
        value.unknown_fields_() != 4 || value.validate_() != 5 ||
        value.copy_from() != 6) {
        return 1;
    }
    if (!value.validate()) {
        return 2;
    }
    auto copy = ::compat::bad::HelperFields<>::create(ctx);
    if (!copy.copy_from(value) || copy.serialize() != 1) {
        return 3;
    }
    auto lower = ::compat::bad::foo<>::create(ctx);
    auto upper = ::compat::bad::Foo<>::create(ctx);
    auto standard = ::std::Payload<>::create(ctx);
    auto runtime_namespace = ::protocyte::Payload<>::create(ctx);
    auto runtime_child_namespace = ::protocyte::user::Payload<>::create(ctx);
    (void)lower;
    (void)upper;
    (void)standard;
    (void)runtime_namespace;
    (void)runtime_child_namespace;
    return 0;
}
""",
    )


def test_std_namespace_prefix_generates_and_compiles(tmp_path: Path) -> None:
    request = _descriptor_request(
        tmp_path,
        files=("prefix.proto",),
        parameter="format=off,runtime=emit,namespace_prefix=std",
    )
    files = _generated_files(tmp_path, request)

    assert "namespace std::prefixed {" in files["prefix.protocyte.hpp"]
    _compile_and_run(
        tmp_path,
        r"""
#include "prefix.protocyte.hpp"

int main() {
    auto ctx = ::protocyte::DefaultConfig::Context{
        ::protocyte::hosted_allocator(), ::protocyte::Limits{}};
    auto value = ::std::prefixed::Payload<>::create(ctx);
    (void)value;
    return 0;
}
""",
    )


@pytest.mark.parametrize("prefix", ["protocyte", "protocyte::generated"])
def test_protocyte_namespace_prefix_generates(tmp_path: Path, prefix: str) -> None:
    request = _descriptor_request(
        tmp_path,
        files=("prefix.proto",),
        parameter=f"format=off,runtime=emit,namespace_prefix={prefix}",
    )

    files = _generated_files(tmp_path, request)

    assert f"namespace {prefix}::prefixed {{" in files["prefix.protocyte.hpp"]
    _compile_and_run(
        tmp_path,
        f"""#include "prefix.protocyte.hpp"
int main() {{
    auto ctx = ::protocyte::DefaultConfig::Context{{
        ::protocyte::hosted_allocator(), ::protocyte::Limits{{}}}};
    auto value = ::{prefix}::prefixed::Payload<>::create(ctx);
    (void)value;
    return 0;
}}
""",
    )


def test_protocyte_namespace_prefix_remaps_runtime_symbol_collisions(
    tmp_path: Path,
) -> None:
    request = _descriptor_request(
        tmp_path,
        files=("prefix_root.proto",),
        parameter="format=off,runtime=emit,namespace_prefix=protocyte",
    )

    model = build_model(request, namespace_prefix="protocyte")
    files = _generated_files(tmp_path, request)
    header = files["prefix_root.protocyte.hpp"]

    assert model.messages["Span"].cpp_name.startswith("Span_protocyte_")
    assert "namespace protocyte {" in header
    assert "struct Span_protocyte_" in header
    assert "struct Result_protocyte_" in header
    assert "struct read_varint_protocyte_" in header
    _compile_and_run(
        tmp_path,
        '#include "prefix_root.protocyte.hpp"\nint main() { return 0; }\n',
    )


def test_namespace_prefix_avoids_unnecessary_runtime_symbol_remapping(
    tmp_path: Path,
) -> None:
    request = _descriptor_request(
        tmp_path,
        files=("protocyte.proto",),
        parameter="format=off,runtime=emit,namespace_prefix=project",
    )

    files = _generated_files(tmp_path, request)
    header = files["protocyte.protocyte.hpp"]

    assert "namespace project::protocyte {" in header
    assert "struct Span;" in header
    assert "Span_protocyte_" not in header
    _compile_and_run(
        tmp_path,
        '#include "protocyte.protocyte.hpp"\nint main() { return 0; }\n',
    )


def test_runtime_type_package_component_is_remapped(tmp_path: Path) -> None:
    request = _descriptor_request(tmp_path, files=("runtime_child.proto",))

    files = _generated_files(tmp_path, request)

    header = files["runtime_child.protocyte.hpp"]
    assert "namespace protocyte::Span_protocyte_" in header
    _compile_and_run(
        tmp_path,
        '#include "runtime_child.protocyte.hpp"\nint main() { return 0; }\n',
    )
