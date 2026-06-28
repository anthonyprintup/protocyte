from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte.descriptor_set import (
    discover_files,
    load_descriptor_set,
    validate_descriptor_set,
    validate_virtual_file_name,
)
from protocyte.errors import ProtocyteError
from protocyte.plugin import generate_response


def _file(name: str, *dependencies: str) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = name
    file.syntax = "proto3"
    file.dependency.extend(dependencies)
    file.message_type.add().name = "Sample"
    return file


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


def _file_with_nested_extension() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "custom/nested_options.proto"
    file.package = "custom"
    file.syntax = "proto2"
    message = file.message_type.add()
    message.name = "Owner"
    extension = message.extension.add()
    extension.name = "legacy_marker"
    extension.number = 100
    extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    extension.extendee = ".custom.Owner"
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
        r"C:\demo.proto",
        r"nested\demo.proto",
    ],
)
def test_validate_virtual_file_name_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(ProtocyteError):
        validate_virtual_file_name(name)


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


def test_discover_files_includes_user_files_with_top_level_extension_declarations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file_with_top_level_extension())

    assert discover_files(load_descriptor_set(path)) == ["legacy.proto"]


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
