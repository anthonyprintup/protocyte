import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

from protocyte.plugin import generate_response


F = descriptor_pb2.FieldDescriptorProto


def test_proto2_array_backed_bytes_accessors_apply_default_values() -> None:
    response = generate_response(_proto2_array_defaults_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["array_defaults.protocyte.hpp"]
    compact_header = _without_whitespace(header)
    assert "autoset_bounded_bytes" not in compact_header
    assert "autoset_fixed_bytes" not in compact_header
    assert "autoset_oneof_bytes" not in compact_header
    assert (
        _without_whitespace(
            '::protocyte::Span<const ::protocyte::u8> bounded_bytes() const noexcept { return has_bounded_bytes_ ? bounded_bytes_.view() : ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8*>("abc"), 3u}; }'
        )
        in compact_header
    )
    assert (
        _without_whitespace(
            "::protocyte::usize bounded_bytes_size() const noexcept { return bounded_bytes().size(); }"
        )
        in compact_header
    )
    assert (
        _without_whitespace(
            '::protocyte::Span<const ::protocyte::u8> fixed_bytes() const noexcept { return has_fixed_bytes() ? fixed_bytes_.view() : ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8*>("xyz"), 3u}; }'
        )
        in compact_header
    )
    assert "bool has_fixed_bytes_" not in header
    assert "has_fixed_bytes_ = true" not in header
    assert (
        _without_whitespace(
            '::protocyte::Span<const ::protocyte::u8> oneof_bytes() const noexcept { return has_oneof_bytes() ? choice_.oneof_bytes_.view() : ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8*>("\\x01""\\xfe"), 2u}; }'
        )
        in compact_header
    )


@pytest.mark.parametrize(
    ("default_value", "max_value", "fixed", "expected_error"),
    [
        ("abcd", 3, False, "default value size exceeds protocyte.array max"),
        ("xy", 3, True, "default value size must match fixed protocyte.array max"),
        ("wxyz", 3, True, "default value size must match fixed protocyte.array max"),
    ],
)
def test_proto2_array_backed_bytes_defaults_must_fit_declared_array_bounds(
    default_value: str,
    max_value: int,
    fixed: bool,
    expected_error: str,
) -> None:
    request = _proto2_array_default_bound_request(
        default_value=default_value,
        max_value=max_value,
        fixed=fixed,
    )

    response = generate_response(request)

    assert expected_error in response.error


@pytest.mark.parametrize(
    ("default_value", "fixed", "expected_error"),
    [
        ("abcd", False, "default value size exceeds protocyte.array max"),
        ("xy", True, "default value size must match fixed protocyte.array max"),
        ("wxyz", True, "default value size must match fixed protocyte.array max"),
    ],
)
def test_proto2_array_backed_bytes_defaults_must_fit_resolved_expression_bounds(
    default_value: str,
    fixed: bool,
    expected_error: str,
) -> None:
    request = _proto2_array_default_bound_request(
        default_value=default_value,
        expr="3",
        fixed=fixed,
    )

    response = generate_response(request)

    assert expected_error in response.error


def _without_whitespace(value: str) -> str:
    return "".join(value.split())


def _proto2_array_defaults_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("array_defaults.proto")
    request.proto_file.extend([_options_file(), _proto2_array_defaults_file()])
    return request


def _proto2_array_defaults_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "array_defaults.proto"
    file.package = "defaults"
    file.syntax = "proto2"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "ArrayDefaults"

    field = message.field.add()
    field.name = "bounded_bytes"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.default_value = "abc"
    field.options.ParseFromString(_array_option_bytes(max_value=8))

    field = message.field.add()
    field.name = "fixed_bytes"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.default_value = "xyz"
    field.options.ParseFromString(_array_option_bytes(max_value=3, fixed=True))

    oneof = message.oneof_decl.add()
    oneof.name = "choice"

    field = message.field.add()
    field.name = "oneof_bytes"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.oneof_index = 0
    field.default_value = r"\001\376"
    field.options.ParseFromString(_array_option_bytes(max_value=8))

    return file


def _proto2_array_default_bound_request(
    *,
    default_value: str,
    max_value: int | None = None,
    expr: str | None = None,
    fixed: bool = False,
) -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("bad_array_default.proto")
    request.proto_file.extend(
        [
            _options_file(),
            _proto2_array_default_bound_file(
                default_value=default_value,
                max_value=max_value,
                expr=expr,
                fixed=fixed,
            ),
        ]
    )
    return request


def _proto2_array_default_bound_file(
    *,
    default_value: str,
    max_value: int | None,
    expr: str | None,
    fixed: bool,
) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "bad_array_default.proto"
    file.package = "defaults"
    file.syntax = "proto2"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "BadArrayDefault"
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.default_value = default_value
    field.options.ParseFromString(_array_option_bytes(max_value=max_value, expr=expr, fixed=fixed))
    return file


def _options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "protocyte/options.proto"
    file.package = "protocyte"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    constant = file.message_type.add()
    constant.name = "Constant"
    field = constant.field.add()
    field.name = "name"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    for number, (field_name, field_type) in enumerate(
        [
            ("boolean", F.TYPE_BOOL),
            ("boolean_expr", F.TYPE_STRING),
            ("i32", F.TYPE_INT32),
            ("i32_expr", F.TYPE_STRING),
            ("u32", F.TYPE_UINT32),
            ("u32_expr", F.TYPE_STRING),
            ("i64", F.TYPE_INT64),
            ("i64_expr", F.TYPE_STRING),
            ("u64", F.TYPE_UINT64),
            ("u64_expr", F.TYPE_STRING),
            ("f32", F.TYPE_FLOAT),
            ("f32_expr", F.TYPE_STRING),
            ("f64", F.TYPE_DOUBLE),
            ("f64_expr", F.TYPE_STRING),
            ("str", F.TYPE_STRING),
            ("str_expr", F.TYPE_STRING),
        ],
        start=2,
    ):
        _add_oneof_field(constant, "value", field_name, number, field_type)

    array_options = file.message_type.add()
    array_options.name = "ArrayOptions"
    _add_oneof_field(array_options, "bound", "max", 1, F.TYPE_UINT32)
    _add_oneof_field(array_options, "bound", "expr", 2, F.TYPE_STRING)
    field = array_options.field.add()
    field.name = "fixed"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BOOL

    ext = file.extension.add()
    ext.name = "constant"
    ext.number = 50000
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.Constant"
    ext.extendee = ".google.protobuf.MessageOptions"

    ext = file.extension.add()
    ext.name = "package_constant"
    ext.number = 50002
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.Constant"
    ext.extendee = ".google.protobuf.FileOptions"

    ext = file.extension.add()
    ext.name = "array"
    ext.number = 50000
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.ArrayOptions"
    ext.extendee = ".google.protobuf.FieldOptions"

    return file


def _add_oneof_field(
    message: descriptor_pb2.DescriptorProto,
    oneof_name: str,
    name: str,
    number: int,
    field_type: int,
) -> None:
    oneof_index = None
    for index, oneof in enumerate(message.oneof_decl):
        if oneof.name == oneof_name:
            oneof_index = index
            break
    if oneof_index is None:
        oneof = message.oneof_decl.add()
        oneof.name = oneof_name
        oneof_index = len(message.oneof_decl) - 1

    field = message.field.add()
    field.name = name
    field.number = number
    field.label = F.LABEL_OPTIONAL
    field.type = field_type
    field.oneof_index = oneof_index


def _array_option_bytes(
    *,
    max_value: int | None = None,
    expr: str | None = None,
    fixed: bool = False,
) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_options_file())
    field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    field_options_cls = message_factory.GetMessageClass(field_options_desc)
    array_ext = pool.FindExtensionByName("protocyte.array")

    options = field_options_cls()
    array_options = options.Extensions[array_ext]
    if max_value is not None:
        array_options.max = max_value
    if expr is not None:
        array_options.expr = expr
    if fixed:
        array_options.fixed = True
    return options.SerializeToString()
