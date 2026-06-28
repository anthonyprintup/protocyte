from types import SimpleNamespace

import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

from protocyte.descriptor_set import load_descriptor_set, validate_descriptor_set
from protocyte.errors import ProtocyteError
from protocyte.model import build_model
from protocyte.plugin import generate_response


F = descriptor_pb2.FieldDescriptorProto


@pytest.mark.parametrize(
    "extendee",
    [
        ".google.protobuf.FileOptions",
        ".google.protobuf.MessageOptions",
        ".google.protobuf.FieldOptions",
        ".google.protobuf.OneofOptions",
        ".google.protobuf.EnumOptions",
        ".google.protobuf.EnumValueOptions",
        ".google.protobuf.ExtensionRangeOptions",
        ".google.protobuf.ServiceOptions",
        ".google.protobuf.MethodOptions",
    ],
)
def test_accepts_each_supported_proto3_custom_option_extendee(extendee: str) -> None:
    file = _proto3_file_with_single_custom_option_extension(extendee)

    build_model(_request(file, selected=["single_option.proto"]))


def test_accepts_proto3_custom_option_extensions_selected_for_generation() -> None:
    file = _custom_options_file()

    model = build_model(_request(file, selected=["example/options.proto"]))

    assert model.files["example/options.proto"].messages[0].full_name == "example.options.AccessPolicy"
    assert model.files["example/options.proto"].enums[0].full_name == "example.options.RpcKind"

    response = generate_response(_plugin_request(file, selected=["example/options.proto"]))

    assert not response.error
    files = {item.name: item.content for item in response.file}
    assert "example/options.protocyte.hpp" in files
    assert "service_name" not in files["example/options.protocyte.hpp"]
    assert "method_kind" not in files["example/options.protocyte.hpp"]
    assert "access_policy" not in files["example/options.protocyte.hpp"]


def test_rejects_proto3_non_option_top_level_extensions() -> None:
    file = _proto3_file_with_top_level_extension(".example.options.AccessPolicy")

    with pytest.raises(
        ProtocyteError,
        match=(
            r"example/options\.proto: extension example\.options\.ordinary_extension "
            r"extends unsupported proto3 target \.example\.options\.AccessPolicy"
        ),
    ):
        build_model(_request(file, selected=["example/options.proto"]))


def test_rejects_unselected_proto3_non_option_extension_dependency() -> None:
    options_file = _proto3_file_with_top_level_extension(".example.options.AccessPolicy")
    consumer_file = _consumer_file_without_custom_options()

    with pytest.raises(
        ProtocyteError,
        match=(
            r"example/options\.proto: extension example\.options\.ordinary_extension "
            r"extends unsupported proto3 target \.example\.options\.AccessPolicy"
        ),
    ):
        build_model(_request(options_file, consumer_file, selected=["example/api.proto"]))


def test_rejects_proto3_nested_non_option_extensions() -> None:
    file = _proto3_file_with_nested_extension(".example.options.AccessPolicy")

    with pytest.raises(
        ProtocyteError,
        match=(
            r"nested_options\.proto: extension example\.options\.Holder\.nested_extension "
            r"extends unsupported proto3 target \.example\.options\.AccessPolicy"
        ),
    ):
        build_model(_request(file, selected=["nested_options.proto"]))


def test_accepts_proto3_nested_custom_option_extensions() -> None:
    file = _proto3_file_with_nested_extension(".google.protobuf.MethodOptions")

    model = build_model(_request(file, selected=["nested_options.proto"]))

    assert model.files["nested_options.proto"].messages[0].full_name == "example.options.Holder"


def test_descriptor_set_selected_option_definition_file_generates_helpers(
    tmp_path,
) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        descriptor_pb2.FileDescriptorProto.FromString(descriptor_pb2.DESCRIPTOR.serialized_pb),
        _custom_options_file(),
    )
    loaded = load_descriptor_set(path)
    validate_descriptor_set(loaded, ["example/options.proto"])
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("example/options.proto")
    request.proto_file.extend(loaded.file)

    response = generate_response(request)

    assert not response.error
    assert {item.name for item in response.file} == {
        "example/options.protocyte.cpp",
        "example/options.protocyte.hpp",
    }


def test_descriptor_set_custom_options_remain_decodable_from_input(
    tmp_path,
) -> None:
    options_file = _custom_options_file()
    consumer_file = _consumer_file_with_custom_options(options_file)
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        descriptor_pb2.FileDescriptorProto.FromString(descriptor_pb2.DESCRIPTOR.serialized_pb),
        options_file,
        consumer_file,
    )
    loaded = load_descriptor_set(path)
    validate_descriptor_set(loaded, ["example/api.proto"])
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("example/api.proto")
    request.proto_file.extend(loaded.file)

    response = generate_response(request)

    assert not response.error
    decoded = _decode_consumer_custom_options(options_file, consumer_file)
    assert decoded == {
        "file": "api-file",
        "message": "request-message",
        "field": "request-id",
        "service": "example",
        "method_kind": 0,
        "method_roles": ["user", "admin"],
    }


def _request(
    *files: descriptor_pb2.FileDescriptorProto, selected: list[str]
) -> SimpleNamespace:
    return SimpleNamespace(proto_file=list(files), file_to_generate=selected)


def _plugin_request(
    *files: descriptor_pb2.FileDescriptorProto, selected: list[str]
) -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.extend(selected)
    request.proto_file.extend(files)
    return request


def _write_descriptor_set(path, *files: descriptor_pb2.FileDescriptorProto) -> None:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.extend(files)
    path.write_bytes(descriptor_set.SerializeToString())


def _custom_options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "example/options.proto"
    file.package = "example.options"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    access_policy = file.message_type.add()
    access_policy.name = "AccessPolicy"
    roles = access_policy.field.add()
    roles.name = "roles"
    roles.number = 1
    roles.label = F.LABEL_REPEATED
    roles.type = F.TYPE_STRING

    enum = file.enum_type.add()
    enum.name = "RpcKind"
    value = enum.value.add()
    value.name = "RPC_KIND_REQUEST_RESPONSE"
    value.number = 0
    value = enum.value.add()
    value.name = "RPC_KIND_EVENT"
    value.number = 1

    _add_extension(file.extension.add(), "file_label", 50000, F.TYPE_STRING, ".google.protobuf.FileOptions")
    _add_extension(
        file.extension.add(), "message_label", 50001, F.TYPE_STRING, ".google.protobuf.MessageOptions"
    )
    _add_extension(file.extension.add(), "field_label", 50002, F.TYPE_STRING, ".google.protobuf.FieldOptions")
    _add_extension(file.extension.add(), "service_name", 50003, F.TYPE_STRING, ".google.protobuf.ServiceOptions")
    _add_extension(
        file.extension.add(),
        "method_kind",
        50004,
        F.TYPE_ENUM,
        ".google.protobuf.MethodOptions",
        type_name=".example.options.RpcKind",
    )
    _add_extension(
        file.extension.add(),
        "access_policy",
        50005,
        F.TYPE_MESSAGE,
        ".google.protobuf.MethodOptions",
        type_name=".example.options.AccessPolicy",
    )
    return file


def _proto3_file_with_top_level_extension(extendee: str) -> descriptor_pb2.FileDescriptorProto:
    file = _custom_options_file()
    extension = file.extension.add()
    _add_extension(extension, "ordinary_extension", 50100, F.TYPE_INT32, extendee)
    return file


def _proto3_file_with_nested_extension(extendee: str) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "nested_options.proto"
    file.package = "example.options"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")
    message = file.message_type.add()
    message.name = "Holder"
    extension = message.extension.add()
    _add_extension(extension, "nested_extension", 50000, F.TYPE_STRING, extendee)
    return file


def _proto3_file_with_single_custom_option_extension(
    extendee: str,
) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "single_option.proto"
    file.package = "example.options"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")
    extension = file.extension.add()
    _add_extension(extension, "custom_option", 50000, F.TYPE_STRING, extendee)
    return file


def _consumer_file_with_custom_options(
    options_file: descriptor_pb2.FileDescriptorProto,
) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "example/api.proto"
    file.package = "example.api"
    file.syntax = "proto3"
    file.dependency.append("example/options.proto")
    file.options.ParseFromString(_option_bytes(options_file, "FileOptions", "file_label", "api-file"))

    message = file.message_type.add()
    message.name = "Request"
    message.options.ParseFromString(
        _option_bytes(options_file, "MessageOptions", "message_label", "request-message")
    )
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field.options.ParseFromString(_option_bytes(options_file, "FieldOptions", "field_label", "request-id"))

    response = file.message_type.add()
    response.name = "Response"

    service = file.service.add()
    service.name = "ExampleService"
    service.options.ParseFromString(
        _option_bytes(options_file, "ServiceOptions", "service_name", "example")
    )
    method = service.method.add()
    method.name = "Ping"
    method.input_type = ".example.api.Request"
    method.output_type = ".example.api.Response"
    method.options.ParseFromString(_method_options_bytes(options_file))
    return file


def _consumer_file_without_custom_options() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "example/api.proto"
    file.package = "example.api"
    file.syntax = "proto3"
    file.dependency.append("example/options.proto")
    message = file.message_type.add()
    message.name = "Request"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    return file


def _add_extension(
    extension: descriptor_pb2.FieldDescriptorProto,
    name: str,
    number: int,
    field_type: int,
    extendee: str,
    *,
    type_name: str = "",
) -> None:
    extension.name = name
    extension.number = number
    extension.label = F.LABEL_OPTIONAL
    extension.type = field_type
    extension.extendee = extendee
    if type_name:
        extension.type_name = type_name


def _option_bytes(
    options_file: descriptor_pb2.FileDescriptorProto,
    option_type: str,
    extension_name: str,
    value: str,
) -> bytes:
    pool = _pool_with_options(options_file)
    options_desc = pool.FindMessageTypeByName(f"google.protobuf.{option_type}")
    options_cls = message_factory.GetMessageClass(options_desc)
    extension = pool.FindExtensionByName(f"example.options.{extension_name}")
    options = options_cls()
    options.Extensions[extension] = value
    return options.SerializeToString()


def _method_options_bytes(options_file: descriptor_pb2.FileDescriptorProto) -> bytes:
    pool = _pool_with_options(options_file)
    options_desc = pool.FindMessageTypeByName("google.protobuf.MethodOptions")
    options_cls = message_factory.GetMessageClass(options_desc)
    method_kind = pool.FindExtensionByName("example.options.method_kind")
    access_policy = pool.FindExtensionByName("example.options.access_policy")
    options = options_cls()
    options.Extensions[method_kind] = 0
    options.Extensions[access_policy].roles.extend(["user", "admin"])
    return options.SerializeToString()


def _decode_consumer_custom_options(
    options_file: descriptor_pb2.FileDescriptorProto,
    consumer_file: descriptor_pb2.FileDescriptorProto,
) -> dict[str, object]:
    pool = _pool_with_options(options_file)
    pool.Add(consumer_file)
    file_options_cls = message_factory.GetMessageClass(pool.FindMessageTypeByName("google.protobuf.FileOptions"))
    message_options_cls = message_factory.GetMessageClass(pool.FindMessageTypeByName("google.protobuf.MessageOptions"))
    field_options_cls = message_factory.GetMessageClass(pool.FindMessageTypeByName("google.protobuf.FieldOptions"))
    service_options_cls = message_factory.GetMessageClass(pool.FindMessageTypeByName("google.protobuf.ServiceOptions"))
    method_options_cls = message_factory.GetMessageClass(pool.FindMessageTypeByName("google.protobuf.MethodOptions"))

    file_options = file_options_cls()
    file_options.ParseFromString(consumer_file.options.SerializeToString())
    message_options = message_options_cls()
    message_options.ParseFromString(consumer_file.message_type[0].options.SerializeToString())
    field_options = field_options_cls()
    field_options.ParseFromString(consumer_file.message_type[0].field[0].options.SerializeToString())
    service_options = service_options_cls()
    service_options.ParseFromString(consumer_file.service[0].options.SerializeToString())
    method_options = method_options_cls()
    method_options.ParseFromString(consumer_file.service[0].method[0].options.SerializeToString())

    file_label = pool.FindExtensionByName("example.options.file_label")
    message_label = pool.FindExtensionByName("example.options.message_label")
    field_label = pool.FindExtensionByName("example.options.field_label")
    service_name = pool.FindExtensionByName("example.options.service_name")
    method_kind = pool.FindExtensionByName("example.options.method_kind")
    access_policy = pool.FindExtensionByName("example.options.access_policy")
    return {
        "file": file_options.Extensions[file_label],
        "message": message_options.Extensions[message_label],
        "field": field_options.Extensions[field_label],
        "service": service_options.Extensions[service_name],
        "method_kind": method_options.Extensions[method_kind],
        "method_roles": list(method_options.Extensions[access_policy].roles),
    }


def _pool_with_options(options_file: descriptor_pb2.FileDescriptorProto) -> descriptor_pool.DescriptorPool:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(options_file)
    return pool
