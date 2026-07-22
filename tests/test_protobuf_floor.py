from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import google.protobuf
import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory, struct_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte.descriptor_set import (
    main as descriptor_set_main,
    validate_descriptor_string_fields,
)
from protocyte.errors import ProtocyteError
from protocyte.main import main as plugin_main
from protocyte.plugin import generate_response


F = descriptor_pb2.FieldDescriptorProto


def _add_string_field(
    message: descriptor_pb2.DescriptorProto,
    *,
    name: str,
    number: int,
    label: int,
) -> None:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = label
    field.type = F.TYPE_STRING


def _add_map_field(
    message: descriptor_pb2.DescriptorProto,
    *,
    name: str,
    number: int,
    key_type: int,
    value_type: int,
) -> None:
    entry = message.nested_type.add()
    entry.name = f"{name.title()}Entry"
    entry.options.map_entry = True
    key = entry.field.add()
    key.name = "key"
    key.number = 1
    key.label = F.LABEL_OPTIONAL
    key.type = key_type
    value = entry.field.add()
    value.name = "value"
    value.number = 2
    value.label = F.LABEL_OPTIONAL
    value.type = value_type

    field = message.field.add()
    field.name = name
    field.number = number
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_MESSAGE
    field.type_name = f".floor.MapHolder.{entry.name}"


def _map_holder_class() -> type[object]:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "floor/maps.proto"
    file.package = "floor"
    file.syntax = "proto3"
    holder = file.message_type.add()
    holder.name = "MapHolder"
    _add_map_field(
        holder,
        name="labels",
        number=1,
        key_type=F.TYPE_STRING,
        value_type=F.TYPE_STRING,
    )
    _add_map_field(
        holder,
        name="counts",
        number=2,
        key_type=F.TYPE_INT32,
        value_type=F.TYPE_INT32,
    )
    pool = descriptor_pool.DescriptorPool()
    pool.Add(file)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("floor.MapHolder"))


class _ListedFieldsMessage:
    def __init__(self, fields: list[tuple[object, object]]) -> None:
        self._fields = fields

    def ListFields(self) -> list[tuple[object, object]]:
        return self._fields


class _BinaryInput:
    def __init__(self, payload: bytes) -> None:
        self.buffer = io.BytesIO(payload)

    def isatty(self) -> bool:
        return False


class _BinaryOutput:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()


def _wire_length_delimited(field_number: int, payload: bytes) -> bytes:
    assert field_number < 16
    assert len(payload) < 128
    return bytes([(field_number << 3) | 2, len(payload)]) + payload


def _malformed_request_payload() -> bytes:
    malformed_file = _wire_length_delimited(1, b"api/invalid-\xff.proto")
    return _wire_length_delimited(1, b"api/input.proto") + _wire_length_delimited(
        15, malformed_file
    )


def _write_malformed_descriptor_set(path: Path) -> None:
    malformed_file = _wire_length_delimited(1, b"api/invalid-\xff.proto")
    path.write_bytes(_wire_length_delimited(1, malformed_file))


def test_repeated_descriptor_fields_generate_without_version_specific_apis() -> None:
    """Exercise repeated descriptor traversal at the public dependency floor."""
    if expected_version := os.environ.get("PROTOCYTE_EXPECTED_PROTOBUF_VERSION"):
        assert google.protobuf.__version__ == expected_version

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("api/floor.proto")
    request.parameter = "format=off"
    file = request.proto_file.add()
    file.name = "api/floor.proto"
    file.package = "api"
    file.syntax = "proto3"

    record = file.message_type.add()
    record.name = "Record"
    _add_string_field(
        record,
        name="summary",
        number=1,
        label=F.LABEL_OPTIONAL,
    )
    _add_string_field(
        record,
        name="labels",
        number=2,
        label=F.LABEL_REPEATED,
    )

    nested = record.nested_type.add()
    nested.name = "Nested"
    _add_string_field(
        nested,
        name="value",
        number=1,
        label=F.LABEL_OPTIONAL,
    )
    nested_items = record.field.add()
    nested_items.name = "nested_items"
    nested_items.number = 3
    nested_items.label = F.LABEL_REPEATED
    nested_items.type = F.TYPE_MESSAGE
    nested_items.type_name = ".api.Record.Nested"

    response = generate_response(request)

    assert response.error == ""
    assert {item.name for item in response.file} == {
        "api/floor.protocyte.hpp",
        "api/floor.protocyte.cpp",
    }


def test_string_and_scalar_map_fields_validate_without_iteration_as_entries() -> None:
    message = _map_holder_class()()
    message.labels["title"] = "Protocyte"
    message.counts[7] = 42

    validate_descriptor_string_fields(message, root="MapHolder")


def test_empty_and_non_string_scalar_maps_do_not_require_message_traversal() -> None:
    message = _map_holder_class()()
    validate_descriptor_string_fields(message, root="MapHolder")

    message.counts[7] = 42
    validate_descriptor_string_fields(message, root="MapHolder")


def test_map_message_values_recurse_into_descriptor_strings() -> None:
    message = struct_pb2.Struct()
    message.fields["payload"].string_value = "valid"

    validate_descriptor_string_fields(message, root="Struct")


def test_map_message_values_preserve_nested_string_diagnostic_paths() -> None:
    map_field = struct_pb2.Struct.DESCRIPTOR.fields_by_name["fields"]
    string_field = struct_pb2.Value.DESCRIPTOR.fields_by_name["string_value"]
    value = _ListedFieldsMessage([(string_field, b"bad-\xff")])
    message = _ListedFieldsMessage([(map_field, {"payload": value})])

    with pytest.raises(ProtocyteError) as exc_info:
        validate_descriptor_string_fields(message, root="Struct")

    assert str(exc_info.value) == (
        "invalid UTF-8 in descriptor string field "
        "Struct.fields['payload'].value.string_value: b'bad-\\xff'"
    )


@pytest.mark.parametrize(
    ("key", "value", "expected_path", "expected_bytes"),
    [
        (
            b"bad-\xff",
            b"valid",
            "MapHolder.labels[b'bad-\\xff'].key",
            b"bad-\xff",
        ),
        (
            "valid",
            b"bad-\xff",
            "MapHolder.labels['valid'].value",
            b"bad-\xff",
        ),
    ],
)
def test_map_string_key_and_value_utf8_diagnostics_are_safe(
    key: object,
    value: bytes,
    expected_path: str,
    expected_bytes: bytes,
) -> None:
    map_field = _map_holder_class().DESCRIPTOR.fields_by_name["labels"]
    message = _ListedFieldsMessage([(map_field, {key: value})])

    with pytest.raises(ProtocyteError) as exc_info:
        validate_descriptor_string_fields(message, root="MapHolder")

    assert str(exc_info.value) == (
        f"invalid UTF-8 in descriptor string field {expected_path}: "
        f"{expected_bytes!r}"
    )


def test_upb_plugin_keeps_malformed_descriptor_utf8_in_the_protocol_response(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if os.environ.get("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION") != "upb":
        pytest.skip("requires the explicitly requested upb backend")

    standard_input = _BinaryInput(_malformed_request_payload())
    standard_output = _BinaryOutput()
    with monkeypatch.context() as context:
        context.setattr(sys, "stdin", standard_input)
        context.setattr(sys, "stdout", standard_output)
        result = plugin_main([])

    response = plugin_pb2.CodeGeneratorResponse.FromString(
        standard_output.buffer.getvalue()
    )
    assert result == 0
    assert response.error == (
        "invalid UTF-8 in descriptor string field "
        "CodeGeneratorRequest.proto_file[0].name: b'api/invalid-\\xff.proto'"
    )
    assert capsys.readouterr().err == ""


def test_pure_python_plugin_rejects_malformed_descriptor_utf8_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if os.environ.get("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION") != "python":
        pytest.skip("requires the explicitly requested pure-Python backend")

    standard_input = _BinaryInput(_malformed_request_payload())
    standard_output = _BinaryOutput()
    with monkeypatch.context() as context:
        context.setattr(sys, "stdin", standard_input)
        context.setattr(sys, "stdout", standard_output)
        result = plugin_main([])

    assert result == 1
    assert standard_output.buffer.getvalue() == b""
    assert capsys.readouterr().err == "protocyte: failed to parse CodeGeneratorRequest\n"


def test_upb_descriptor_set_keeps_malformed_utf8_in_the_cli_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if os.environ.get("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION") != "upb":
        pytest.skip("requires the explicitly requested upb backend")

    descriptor_set = tmp_path / "descriptor_set.pb"
    _write_malformed_descriptor_set(descriptor_set)

    with pytest.raises(SystemExit) as exc_info:
        descriptor_set_main(["list", str(descriptor_set)])

    assert exc_info.value.code == 1
    assert capsys.readouterr().err.strip() == (
        "protocyte: invalid UTF-8 in descriptor string field "
        "FileDescriptorSet.file[0].name: b'api/invalid-\\xff.proto'"
    )


def test_pure_python_descriptor_set_rejects_malformed_utf8_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if os.environ.get("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION") != "python":
        pytest.skip("requires the explicitly requested pure-Python backend")

    descriptor_set = tmp_path / "descriptor_set.pb"
    _write_malformed_descriptor_set(descriptor_set)

    with pytest.raises(SystemExit) as exc_info:
        descriptor_set_main(["list", str(descriptor_set)])

    assert exc_info.value.code == 1
    error = capsys.readouterr().err.strip()
    assert error.startswith("protocyte: failed to parse FileDescriptorSet ")
    assert "api/invalid-" not in error
    assert "\\xff" not in error
    assert len(error) < 700
