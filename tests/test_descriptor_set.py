import json
import os
from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte import __version__
from protocyte.descriptor_set import (
    discover_files,
    load_descriptor_set,
    main as descriptor_set_main,
    validate_descriptor_set,
    validate_virtual_file_name,
)
from protocyte.errors import ProtocyteError
from protocyte.main import _enter_cmake_working_directory, main as plugin_main
from protocyte.plugin import generate_response


def _file(name: str, *dependencies: str) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = name
    file.syntax = "proto3"
    file.dependency.extend(dependencies)
    file.message_type.add().name = "Sample"
    return file


def test_cmake_transport_restores_unicode_consumer_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    consumer_directory = tmp_path / "consumer café"
    consumer_directory.mkdir()
    monkeypatch.setenv(
        "PROTOCYTE_CMAKE_WORKING_DIRECTORY_HEX",
        str(consumer_directory).encode().hex(),
    )

    previous_directory, error = _enter_cmake_working_directory()
    try:
        assert error is None
        assert previous_directory is not None
        assert Path.cwd() == consumer_directory
    finally:
        if previous_directory is not None:
            os.chdir(previous_directory)


def _timestamp_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "google/protobuf/timestamp.proto"
    file.package = "google.protobuf"
    file.syntax = "proto3"
    message = file.message_type.add()
    message.name = "Timestamp"
    seconds = message.field.add()
    seconds.name = "seconds"
    seconds.number = 1
    seconds.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    seconds.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
    nanos = message.field.add()
    nanos.name = "nanos"
    nanos.number = 2
    nanos.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    nanos.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    return file


def _file_with_timestamp_field(name: str) -> descriptor_pb2.FileDescriptorProto:
    file = _file(name, "google/protobuf/timestamp.proto")
    field = file.message_type[0].field.add()
    field.name = "created_at"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    field.type_name = ".google.protobuf.Timestamp"
    return file


def _custom_options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/options.proto"
    file.package = "custom"
    file.syntax = "proto2"
    file.dependency.append("google/protobuf/descriptor.proto")
    message = file.message_type.add()
    message.name = "Marker"
    value = message.field.add()
    value.name = "value"
    value.number = 1
    value.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    value.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    extension = file.extension.add()
    extension.name = "marker"
    extension.number = 50001
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    extension.type_name = ".custom.Marker"
    extension.extendee = ".google.protobuf.MessageOptions"
    return file


def _extension_range_options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/extension_range_options.proto"
    file.package = "custom"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")
    extension = file.extension.add()
    extension.name = "range_label"
    extension.number = 50001
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    extension.extendee = ".google.protobuf.ExtensionRangeOptions"
    return file


def _custom_options_file_with_transitive_helper_enum() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/policy_options.proto"
    file.package = "custom"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    policy = file.message_type.add()
    policy.name = "Policy"
    level = policy.field.add()
    level.name = "level"
    level.number = 1
    level.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    level.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    level.type_name = ".custom.Severity"

    severity = file.enum_type.add()
    severity.name = "Severity"
    value = severity.value.add()
    value.name = "SEVERITY_UNSPECIFIED"
    value.number = 0
    value = severity.value.add()
    value.name = "SEVERITY_HIGH"
    value.number = 1

    extension = file.extension.add()
    extension.name = "policy"
    extension.number = 50000
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    extension.type_name = ".custom.Policy"
    extension.extendee = ".google.protobuf.MethodOptions"
    return file


def _nested_namespace_custom_options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/nested_method_options.proto"
    file.package = "custom"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    namespace = file.message_type.add()
    namespace.name = "Opts"
    extension = namespace.extension.add()
    extension.name = "tag"
    extension.number = 50000
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    extension.extendee = ".google.protobuf.MethodOptions"
    return file


def _nested_namespace_custom_options_file_with_public_field() -> descriptor_pb2.FileDescriptorProto:
    file = _nested_namespace_custom_options_file()
    file.name = "custom/nested_public_field_options.proto"
    field = file.message_type[0].field.add()
    field.name = "public_id"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    return file


def _nested_namespace_custom_options_file_with_public_nested_message() -> descriptor_pb2.FileDescriptorProto:
    file = _nested_namespace_custom_options_file()
    file.name = "custom/nested_public_message_options.proto"
    message = file.message_type[0].nested_type.add()
    message.name = "PublicPayload"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    return file


def _mixed_custom_options_file() -> descriptor_pb2.FileDescriptorProto:
    file = _custom_options_file()
    message = file.message_type.add()
    message.name = "PublicPayload"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    return file


def _file_with_nested_extension() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/nested_options.proto"
    file.package = "custom"
    file.syntax = "proto2"
    message = file.message_type.add()
    message.name = "Owner"
    extension_range = message.extension_range.add()
    extension_range.start = 100
    extension_range.end = 101
    extension = message.extension.add()
    extension.name = "legacy_marker"
    extension.number = 100
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    extension.extendee = ".custom.Owner"
    return file


def _file_with_nested_extension_and_public_types() -> descriptor_pb2.FileDescriptorProto:
    file = _file_with_nested_extension()
    payload = file.message_type.add()
    payload.name = "PublicPayload"
    identifier = payload.field.add()
    identifier.name = "id"
    identifier.number = 1
    identifier.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    identifier.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    state = file.enum_type.add()
    state.name = "PublicState"
    unknown = state.value.add()
    unknown.name = "PUBLIC_STATE_UNKNOWN"
    unknown.number = 0
    ready = state.value.add()
    ready.name = "PUBLIC_STATE_READY"
    ready.number = 1
    return file


def _file_with_type_reference(
    name: str,
    dependency: str,
    *,
    field_name: str,
    field_type: int,
    type_name: str,
) -> descriptor_pb2.FileDescriptorProto:
    file = _file(name, dependency)
    file.package = "api"
    field = file.message_type[0].field.add()
    field.name = field_name
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = field_type
    field.type_name = type_name
    return file


def _file_with_top_level_extension() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "legacy.proto"
    file.package = "legacy"
    file.syntax = "proto2"
    message = file.message_type.add()
    message.name = "Legacy"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    extension = file.extension.add()
    extension.name = "legacy_extension"
    extension.number = 100
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    extension.extendee = ".legacy.Legacy"
    return file


def _proto3_file_with_google_protobuf_non_option_extension() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/timestamp_extension.proto"
    file.package = "custom"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/timestamp.proto")
    extension = file.extension.add()
    extension.name = "timestamp_marker"
    extension.number = 50000
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    extension.extendee = ".google.protobuf.Timestamp"
    return file


def _file_with_custom_marker_field(name: str) -> descriptor_pb2.FileDescriptorProto:
    file = _file(name, "custom/options.proto")
    field = file.message_type[0].field.add()
    field.name = "marker"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    field.type_name = ".custom.Marker"
    return file


def _write_descriptor_set(path: Path, *files: descriptor_pb2.FileDescriptorProto) -> None:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.extend(files)
    path.write_bytes(descriptor_set.SerializeToString())


def test_plugin_entrypoint_reports_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert plugin_main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


@pytest.mark.parametrize("option", ["-h", "--help"])
def test_plugin_entrypoint_reports_help(
    option: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert plugin_main([option]) == 0

    captured = capsys.readouterr()
    assert "usage: protoc-gen-protocyte" in captured.out
    assert "Most users generate code by running protoc" in captured.out
    assert (
        "protoc --proto_path=. --protocyte_out=runtime=emit:. schema.proto"
        in captured.out
    )
    assert "descriptor-set" in captured.out
    assert "--version" in captured.out
    assert captured.err == ""


def test_plugin_entrypoint_unknown_arguments_show_help_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert plugin_main(["unknown-command"]) == 2

    captured = capsys.readouterr()
    assert "usage: protoc-gen-protocyte" in captured.err
    assert "unsupported arguments: unknown-command" in captured.err
    assert "protoc-gen-protocyte --help" in captured.err
    assert captured.out == ""


def test_plugin_entrypoint_descriptor_set_help_uses_canonical_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        plugin_main(["descriptor-set", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: protoc-gen-protocyte descriptor-set" in captured.out
    assert "binary protobuf FileDescriptorSet" in captured.out
    assert "--include_imports" in captured.out
    assert "descriptor-set list descriptor_set.pb" in captured.out
    assert captured.err == ""


def test_plugin_entrypoint_descriptor_set_list_help_explains_io(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        plugin_main(["descriptor-set", "list", "--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage: protoc-gen-protocyte descriptor-set list" in captured.out
    assert "sorted JSON array of virtual .proto file names" in captured.out
    assert "path to a binary protobuf FileDescriptorSet" in captured.out
    assert captured.err == ""


def test_plugin_entrypoint_dispatches_descriptor_set_commands(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    descriptor_set = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(descriptor_set, _file("api/demo.proto"))

    assert plugin_main(["descriptor-set", "list", str(descriptor_set)]) == 0
    assert json.loads(capsys.readouterr().out) == ["api/demo.proto"]


def test_plugin_entrypoint_reports_blocked_discovered_type_dependency(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    descriptor_set = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        descriptor_set,
        _file_with_nested_extension_and_public_types(),
        _file_with_type_reference(
            "api/request.proto",
            "custom/nested_options.proto",
            field_name="payload",
            field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
            type_name=".custom.PublicPayload",
        ),
    )

    with pytest.raises(SystemExit) as exc_info:
        plugin_main(["descriptor-set", "list", str(descriptor_set)])

    assert exc_info.value.code == 1
    assert capsys.readouterr().err.strip() == (
        "protocyte: api/request.proto: field api.Sample.payload references type "
        ".custom.PublicPayload from custom/nested_options.proto, but "
        "custom/nested_options.proto cannot be generated because message custom.Owner "
        "declares unsupported extension legacy_marker"
    )


def test_load_descriptor_set_reports_invalid_bytes(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    path.write_bytes(b"not a descriptor set")

    with pytest.raises(ProtocyteError, match="failed to parse FileDescriptorSet"):
        load_descriptor_set(path)


def test_validate_descriptor_set_rejects_duplicate_file_names(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file("demo.proto"), _file("demo.proto"))

    with pytest.raises(ProtocyteError, match="duplicate descriptor file name: demo.proto"):
        validate_descriptor_set(load_descriptor_set(path), ["demo.proto"])


def test_validate_descriptor_set_rejects_missing_selected_file(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file("present.proto"))

    with pytest.raises(ProtocyteError, match="selected descriptor file is not present: missing.proto"):
        validate_descriptor_set(load_descriptor_set(path), ["missing.proto"])


def test_validate_descriptor_set_rejects_missing_import(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file("user.proto", "missing.proto"))

    with pytest.raises(ProtocyteError, match="user.proto imports missing descriptor missing.proto"):
        validate_descriptor_set(load_descriptor_set(path), ["user.proto"])


@pytest.mark.parametrize(
    "name",
    [
        "",
        "../demo.proto",
        "nested/../demo.proto",
        ".",
        "./demo.proto",
        "nested/./demo.proto",
        "demo.proto/",
        "a//b.proto",
        "/demo.proto",
        "C:/demo.proto",
        r"C:\demo.proto",
        r"nested\demo.proto",
    ],
)
def test_validate_virtual_file_name_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(ProtocyteError):
        validate_virtual_file_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "-legacy.proto",
        "--descriptor_set_out=escaped.proto",
        "--plugin=protoc-gen-protocyte=other-plugin",
    ],
)
def test_validate_virtual_file_name_rejects_protoc_option_names(name: str) -> None:
    with pytest.raises(ProtocyteError, match="must not begin with '-'"):
        validate_virtual_file_name(name)


def test_discover_files_rejects_protoc_option_names() -> None:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.extend(
        [_file("--descriptor_set_out=escaped.proto"), _file("api/demo.proto")]
    )

    with pytest.raises(ProtocyteError, match="must not begin with '-'"):
        discover_files(descriptor_set)


@pytest.mark.parametrize("codepoint", [*range(1, 0x20), *range(0x7F, 0xA0)])
def test_validate_virtual_file_name_accepts_protobuf_control_characters(codepoint: int) -> None:
    validate_virtual_file_name(f"api/control-{chr(codepoint)}.proto")


def test_validate_virtual_file_name_rejects_null_character() -> None:
    with pytest.raises(ProtocyteError, match="null character"):
        validate_virtual_file_name("api/nul\0.proto")


def test_validate_virtual_file_name_accepts_semicolon() -> None:
    validate_virtual_file_name("api/one.proto;api/two.proto")


def test_validate_virtual_file_name_accepts_relative_colon_name() -> None:
    validate_virtual_file_name("a:b.proto")


def test_descriptor_set_list_encodes_transport_sensitive_names_as_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "descriptor_set.pb"
    names = [
        "api/one.proto\napi/two.proto",
        "api/one.proto;api/two.proto",
        "api/c1\x85.proto",
    ]
    _write_descriptor_set(path, *(_file(name) for name in names))

    assert descriptor_set_main(["list", str(path)]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out) == sorted(names)
    assert captured.out.count("\n") == 1
    assert captured.err == ""


def test_discover_files_skips_google_protobuf_runtime_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _file("protocyte/options.proto", "google/protobuf/descriptor.proto"),
        _file("nested/user.proto", "google/protobuf/descriptor.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["nested/user.proto"]


def test_discover_files_includes_referenced_google_protobuf_message_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _timestamp_file(),
        _file_with_timestamp_field("api/event.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == [
        "api/event.proto",
        "google/protobuf/timestamp.proto",
    ]


def test_discover_files_skips_imported_custom_option_extension_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _custom_options_file(),
        _file("api/request.proto", "custom/options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["api/request.proto"]


def test_discover_files_skips_imported_extension_range_option_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _extension_range_options_file(),
        _file("api/request.proto", "custom/extension_range_options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["api/request.proto"]


def test_discover_files_skips_transitive_custom_option_helper_types(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _custom_options_file_with_transitive_helper_enum(),
        _file("api/request.proto", "custom/policy_options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["api/request.proto"]


def test_discover_files_skips_nested_scalar_custom_option_namespaces(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _nested_namespace_custom_options_file(),
        _file("api/request.proto", "custom/nested_method_options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["api/request.proto"]


def test_discover_files_includes_nested_custom_option_namespaces_with_public_fields(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _nested_namespace_custom_options_file_with_public_field(),
        _file("api/request.proto", "custom/nested_public_field_options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == [
        "api/request.proto",
        "custom/nested_public_field_options.proto",
    ]


def test_discover_files_includes_nested_custom_option_namespaces_with_public_nested_messages(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _nested_namespace_custom_options_file_with_public_nested_message(),
        _file("api/request.proto", "custom/nested_public_message_options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == [
        "api/request.proto",
        "custom/nested_public_message_options.proto",
    ]


def test_discover_files_includes_custom_option_files_with_public_messages(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _mixed_custom_options_file(),
    )

    assert discover_files(load_descriptor_set(path)) == ["custom/options.proto"]


def test_discover_files_includes_user_files_with_top_level_extension_declarations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file_with_top_level_extension())

    assert discover_files(load_descriptor_set(path)) == ["legacy.proto"]


def test_discover_files_includes_non_option_google_protobuf_extension_descriptors(
    tmp_path: Path,
) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _timestamp_file(),
        _proto3_file_with_google_protobuf_non_option_extension(),
    )

    assert discover_files(load_descriptor_set(path)) == ["custom/timestamp_extension.proto"]


def test_discover_files_includes_extension_descriptors_referenced_by_message_fields(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _custom_options_file(),
        _file_with_custom_marker_field("api/request.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["api/request.proto", "custom/options.proto"]


def test_discovered_extension_descriptor_type_files_can_generate_referenced_messages(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.extend(
        [
            descriptor_pb2.FileDescriptorProto.FromString(descriptor_pb2.DESCRIPTOR.serialized_pb),
            _custom_options_file(),
            _file_with_custom_marker_field("api/request.proto"),
        ]
    )
    path.write_bytes(descriptor_set.SerializeToString())

    loaded = load_descriptor_set(path)
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.extend(discover_files(loaded))
    request.proto_file.extend(loaded.file)

    response = generate_response(request)

    assert not response.error
    assert {item.name for item in response.file} == {
        "api/request.protocyte.cpp",
        "api/request.protocyte.hpp",
        "custom/options.protocyte.cpp",
        "custom/options.protocyte.hpp",
    }


def test_discover_files_skips_message_scoped_extension_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file_with_nested_extension(),
        _file("api/request.proto", "custom/nested_options.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["api/request.proto"]


@pytest.mark.parametrize(
    ("field_name", "field_type", "type_name"),
    [
        (
            "payload",
            descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
            ".custom.PublicPayload",
        ),
        (
            "state",
            descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
            ".custom.PublicState",
        ),
    ],
)
def test_discover_files_rejects_referenced_types_from_message_scoped_extension_descriptors(
    tmp_path: Path,
    field_name: str,
    field_type: int,
    type_name: str,
) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file_with_nested_extension_and_public_types(),
        _file_with_type_reference(
            "api/request.proto",
            "custom/nested_options.proto",
            field_name=field_name,
            field_type=field_type,
            type_name=type_name,
        ),
    )

    with pytest.raises(ProtocyteError) as exc_info:
        discover_files(load_descriptor_set(path))

    assert str(exc_info.value) == (
        f"api/request.proto: field api.Sample.{field_name} references type {type_name} "
        "from custom/nested_options.proto, but custom/nested_options.proto cannot be generated "
        "because message custom.Owner declares unsupported extension legacy_marker"
    )


def test_discover_files_rejects_referenced_types_from_internal_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    internal = _file("protocyte/options.proto")
    internal.package = "protocyte"
    _write_descriptor_set(
        path,
        internal,
        _file_with_type_reference(
            "api/request.proto",
            "protocyte/options.proto",
            field_name="options",
            field_type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
            type_name=".protocyte.Sample",
        ),
    )

    with pytest.raises(ProtocyteError) as exc_info:
        discover_files(load_descriptor_set(path))

    assert str(exc_info.value) == (
        "api/request.proto: field api.Sample.options references type .protocyte.Sample "
        "from protocyte/options.proto, but protocyte/options.proto cannot be generated because "
        "it is reserved for Protocyte generator internals"
    )
