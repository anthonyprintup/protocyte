from types import SimpleNamespace

import pytest
from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte.descriptor_set import load_descriptor_set, validate_descriptor_set
from protocyte.errors import ProtocyteError
from protocyte.model import build_model
from protocyte.plugin import generate_response


F = descriptor_pb2.FieldDescriptorProto


def test_rejects_selected_message_scoped_extension_declaration() -> None:
    file = _proto2_file_with_nested_extension()

    with pytest.raises(
        ProtocyteError,
        match=r"nested_extensions\.proto: message demo\.Parent: extension declarations are not supported",
    ):
        build_model(_request(file, selected=["nested_extensions.proto"]))


def test_rejects_selected_deeply_nested_message_scoped_extension_declaration() -> None:
    file = _proto2_file_with_deeply_nested_extension()

    with pytest.raises(
        ProtocyteError,
        match=r"deep_extensions\.proto: message demo\.Outer\.Inner: extension declarations are not supported",
    ):
        build_model(_request(file, selected=["deep_extensions.proto"]))


def test_ignores_unselected_message_scoped_extension_declaration() -> None:
    selected = descriptor_pb2.FileDescriptorProto()
    selected.name = "selected.proto"
    selected.package = "demo"
    selected.syntax = "proto2"
    selected.message_type.add().name = "Selected"

    unselected = _proto2_file_with_nested_extension()

    build_model(_request(selected, unselected, selected=["selected.proto"]))


def test_descriptor_set_request_rejects_selected_message_scoped_extension_declaration(
    tmp_path,
) -> None:
    file = _proto2_file_with_nested_extension()
    request = _request_from_descriptor_set(tmp_path, file, selected=["nested_extensions.proto"])

    response = generate_response(request)

    assert (
        "nested_extensions.proto: message demo.Parent: extension declarations are not supported"
        in response.error
    )


def test_descriptor_set_request_ignores_unselected_message_scoped_extension_declaration(
    tmp_path,
) -> None:
    selected = descriptor_pb2.FileDescriptorProto()
    selected.name = "selected.proto"
    selected.package = "demo"
    selected.syntax = "proto2"
    selected.message_type.add().name = "Selected"

    unselected = _proto2_file_with_nested_extension()
    request = _request_from_descriptor_set(
        tmp_path, selected, unselected, selected=["selected.proto"]
    )

    response = generate_response(request)

    assert not response.error


def _request(
    *files: descriptor_pb2.FileDescriptorProto, selected: list[str]
) -> SimpleNamespace:
    return SimpleNamespace(proto_file=list(files), file_to_generate=selected)


def _request_from_descriptor_set(
    tmp_path,
    *files: descriptor_pb2.FileDescriptorProto,
    selected: list[str],
) -> plugin_pb2.CodeGeneratorRequest:
    path = tmp_path / "descriptor_set.pb"
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.extend(files)
    path.write_bytes(descriptor_set.SerializeToString())

    loaded = load_descriptor_set(path)
    validate_descriptor_set(loaded, selected)
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.extend(selected)
    request.proto_file.extend(loaded.file)
    return request


def _proto2_file_with_nested_extension() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "nested_extensions.proto"
    file.package = "demo"
    file.syntax = "proto2"

    message = file.message_type.add()
    message.name = "Parent"
    _add_message_scoped_extension(message, ".demo.Parent")

    return file


def _proto2_file_with_deeply_nested_extension() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "deep_extensions.proto"
    file.package = "demo"
    file.syntax = "proto2"

    outer = file.message_type.add()
    outer.name = "Outer"
    inner = outer.nested_type.add()
    inner.name = "Inner"
    _add_message_scoped_extension(inner, ".demo.Outer.Inner")

    return file


def _add_message_scoped_extension(
    message: descriptor_pb2.DescriptorProto, extendee: str
) -> None:
    extension = message.extension.add()
    extension.name = "legacy_extension"
    extension.number = 100
    extension.label = F.LABEL_OPTIONAL
    extension.type = F.TYPE_INT32
    extension.extendee = extendee
