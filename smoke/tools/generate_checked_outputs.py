from __future__ import annotations

import sys
from pathlib import Path

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from protocyte.plugin import generate_response  # noqa: E402

F = descriptor_pb2.FieldDescriptorProto


def main() -> int:
    out_dir = Path(__file__).resolve().parents[1] / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    requests: list[plugin_pb2.CodeGeneratorRequest] = []

    example_request = plugin_pb2.CodeGeneratorRequest()
    example_request.file_to_generate.append("example.proto")
    example_request.parameter = "runtime=emit"
    example_request.proto_file.extend([options_file(), example_file()])
    requests.append(example_request)

    compat_request = plugin_pb2.CodeGeneratorRequest()
    compat_request.file_to_generate.append("compat.proto")
    compat_request.parameter = "namespace_prefix=protocyte_smoke"
    compat_request.proto_file.append(compat_file())
    requests.append(compat_request)

    for request in requests:
        response = generate_response(request)
        if response.error:
            print(response.error, file=sys.stderr)
            return 1

        for item in response.file:
            path = out_dir / item.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item.content, encoding="utf-8", newline="\n")

    compat_cases_path = out_dir / "compat_cases.hpp"
    compat_cases_path.write_text(compat_cases_header(), encoding="utf-8", newline="\n")

    return 0


def add_field(
    message: descriptor_pb2.DescriptorProto,
    name: str,
    number: int,
    kind: int,
    *,
    label: int = F.LABEL_OPTIONAL,
    type_name: str = "",
    packed: bool | None = None,
    oneof_index: int | None = None,
    proto3_optional: bool = False,
) -> descriptor_pb2.FieldDescriptorProto:
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = label
    field.type = kind
    if type_name:
        field.type_name = type_name
    if packed is not None:
        field.options.packed = packed
    if oneof_index is not None:
        field.oneof_index = oneof_index
    if proto3_optional:
        field.proto3_optional = True
    return field


def add_map_entry(
    parent: descriptor_pb2.DescriptorProto,
    name: str,
    key_type: int,
    value_type: int,
    *,
    value_type_name: str = "",
    parent_type_name: str = ".test.ultimate.UltimateComplexMessage",
) -> str:
    entry = parent.nested_type.add()
    entry.name = name
    entry.options.map_entry = True
    add_field(entry, "key", 1, key_type)
    add_field(entry, "value", 2, value_type, type_name=value_type_name)
    return f"{parent_type_name}.{name}"


def example_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "example.proto"
    file.package = "test.ultimate"
    file.syntax = "proto3"
    file.options.optimize_for = descriptor_pb2.FileOptions.SPEED
    file.dependency.append("protocyte/options.proto")
    file.options.ParseFromString(
        package_constant_options_bytes(
            [
                ("BASE_COUNT", 2, "5", None),
                ("PREFIX", 8, None, 'substr("protocyte", 0, 5)'),
                ("BYTE_ARRAY_CAP", 4, None, "len(PREFIX) - 1"),
            ]
        )
    )

    msg = file.message_type.add()
    msg.name = "UltimateComplexMessage"
    msg.options.ParseFromString(
        constant_options_bytes(
            [
                ("SHIFTED_COUNT", 3, None, "BASE_COUNT * 1000000000"),
                ("MASK_BITS", 5, "1234567890123456789", None),
                ("FLOAT_SCALE", 6, "1.25", None),
                ("DOUBLE_SCALE", 7, None, "FLOAT_SCALE + 2.5"),
                ("FLAG_LITERAL", 1, "true", None),
                ("HEX_LITERAL", 4, "0x20", None),
                ("HEX_SUM", 4, None, "0x10 + 0x8"),
                ("INTEGER_ARRAY_CAP", 4, None, "(BASE_COUNT * 2) - 2"),
                ("LABEL", 8, None, 'PREFIX + "-demo"'),
                ("UNICODE_LABEL", 8, chr(0x0100) + chr(0x00E9), None),
                ("FIXED_INTEGER_ARRAY_CAP", 4, None, "BASE_COUNT - 2"),
                ("FLOATISH_BOUND", 4, None, "4 / 2.0"),
                ("GT_CHECK", 1, None, "BASE_COUNT > 4"),
                ("LE_CHECK", 1, None, "BYTE_ARRAY_CAP <= INTEGER_ARRAY_CAP"),
                ("EQ_CHECK", 1, None, 'PREFIX == "proto"'),
                ("NE_CHECK", 1, None, 'LABEL != "proto"'),
                ("HAS_PREFIX", 1, None, 'starts_with(LABEL, PREFIX) && !starts_with(LABEL, "zzz")'),
                ("MOD_CHECK", 2, None, "BASE_COUNT % 2"),
                ("OR_CHECK", 1, None, "HAS_PREFIX || false"),
            ]
        )
    )
    msg.reserved_range.add(start=3, end=4)
    msg.reserved_range.add(start=5, end=8)
    msg.reserved_range.add(start=20, end=21)
    msg.reserved_name.extend(["old_name", "legacy_field"])

    add_field(msg, "f_double", 1, F.TYPE_DOUBLE)
    add_field(msg, "f_float", 2, F.TYPE_FLOAT)
    add_field(msg, "f_int32", 4, F.TYPE_INT32)
    add_field(msg, "f_int64", 8, F.TYPE_INT64)
    add_field(msg, "f_uint32", 9, F.TYPE_UINT32)
    add_field(msg, "f_uint64", 10, F.TYPE_UINT64)
    add_field(msg, "f_sint32", 11, F.TYPE_SINT32)
    add_field(msg, "f_sint64", 12, F.TYPE_SINT64)
    add_field(msg, "f_fixed32", 13, F.TYPE_FIXED32)
    add_field(msg, "f_fixed64", 14, F.TYPE_FIXED64)
    add_field(msg, "f_sfixed32", 15, F.TYPE_SFIXED32)
    add_field(msg, "f_sfixed64", 16, F.TYPE_SFIXED64)
    add_field(msg, "f_bool", 17, F.TYPE_BOOL)
    add_field(msg, "f_string", 18, F.TYPE_STRING)
    add_field(msg, "f_bytes", 19, F.TYPE_BYTES)
    add_field(msg, "r_int32_unpacked", 21, F.TYPE_INT32, label=F.LABEL_REPEATED, packed=False)
    add_field(msg, "r_int32_packed", 22, F.TYPE_INT32, label=F.LABEL_REPEATED, packed=True)
    add_field(msg, "r_double", 23, F.TYPE_DOUBLE, label=F.LABEL_REPEATED, packed=True)

    color = msg.enum_type.add()
    color.name = "Color"
    for name, number in [
        ("COLOR_UNSPECIFIED", 0),
        ("RED", 1),
        ("GREEN", 2),
        ("BLUE", 3),
    ]:
        value = color.value.add()
        value.name = name
        value.number = number
    add_field(msg, "color", 24, F.TYPE_ENUM, type_name=".test.ultimate.UltimateComplexMessage.Color")

    nested1 = msg.nested_type.add()
    nested1.name = "NestedLevel1"
    add_field(nested1, "name", 1, F.TYPE_STRING)
    add_field(nested1, "id", 2, F.TYPE_INT32)

    nested2 = nested1.nested_type.add()
    nested2.name = "NestedLevel2"
    add_field(nested2, "description", 1, F.TYPE_STRING)
    add_field(nested2, "values", 2, F.TYPE_FLOAT, label=F.LABEL_REPEATED, packed=True)
    inner = nested2.enum_type.add()
    inner.name = "InnerEnum"
    for name, number in [
        ("INNER_UNSPECIFIED", 0),
        ("A", 1),
        ("B", 2),
        ("C", 3),
    ]:
        value = inner.value.add()
        value.name = name
        value.number = number
    add_field(
        nested2,
        "mode",
        3,
        F.TYPE_ENUM,
        type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1.NestedLevel2.InnerEnum",
    )
    add_field(
        nested1,
        "inner",
        3,
        F.TYPE_MESSAGE,
        type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1.NestedLevel2",
    )
    add_field(msg, "nested1", 25, F.TYPE_MESSAGE, type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1")

    msg.oneof_decl.add().name = "special_oneof"
    add_field(msg, "oneof_string", 26, F.TYPE_STRING, oneof_index=0)
    add_field(msg, "oneof_int32", 27, F.TYPE_INT32, oneof_index=0)
    add_field(
        msg,
        "oneof_msg",
        28,
        F.TYPE_MESSAGE,
        type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1",
        oneof_index=0,
    )
    oneof_bytes = add_field(msg, "oneof_bytes", 29, F.TYPE_BYTES, oneof_index=0)
    oneof_bytes.options.ParseFromString(array_option_bytes(expr="BYTE_ARRAY_CAP"))

    repeated_bytes_holder = msg.nested_type.add()
    repeated_bytes_holder.name = "RepeatedBytesHolder"
    add_field(repeated_bytes_holder, "values", 1, F.TYPE_BYTES, label=F.LABEL_REPEATED)

    bounded_repeated_bytes_holder = msg.nested_type.add()
    bounded_repeated_bytes_holder.name = "BoundedRepeatedBytesHolder"
    bounded_values = add_field(bounded_repeated_bytes_holder, "values", 1, F.TYPE_BYTES, label=F.LABEL_REPEATED)
    bounded_values.options.ParseFromString(array_option_bytes(max_value=3))

    fixed_repeated_bytes_holder = msg.nested_type.add()
    fixed_repeated_bytes_holder.name = "FixedRepeatedBytesHolder"
    fixed_values = add_field(fixed_repeated_bytes_holder, "values", 1, F.TYPE_BYTES, label=F.LABEL_REPEATED)
    fixed_values.options.ParseFromString(array_option_bytes(max_value=3, fixed=True))

    msg.oneof_decl.add().name = "crazy_bytes_oneof"
    add_field(msg, "crazy_plain_bytes", 49, F.TYPE_BYTES, oneof_index=1)
    crazy_bounded_bytes = add_field(msg, "crazy_bounded_bytes", 50, F.TYPE_BYTES, oneof_index=1)
    crazy_bounded_bytes.options.ParseFromString(array_option_bytes(expr="BYTE_ARRAY_CAP"))
    crazy_fixed_bytes = add_field(msg, "crazy_fixed_bytes", 51, F.TYPE_BYTES, oneof_index=1)
    crazy_fixed_bytes.options.ParseFromString(array_option_bytes(expr="BYTE_ARRAY_CAP", fixed=True))
    add_field(
        msg,
        "crazy_repeated_bytes",
        52,
        F.TYPE_MESSAGE,
        type_name=".test.ultimate.UltimateComplexMessage.RepeatedBytesHolder",
        oneof_index=1,
    )
    add_field(
        msg,
        "crazy_bounded_repeated_bytes",
        53,
        F.TYPE_MESSAGE,
        type_name=".test.ultimate.UltimateComplexMessage.BoundedRepeatedBytesHolder",
        oneof_index=1,
    )
    add_field(
        msg,
        "crazy_fixed_repeated_bytes",
        54,
        F.TYPE_MESSAGE,
        type_name=".test.ultimate.UltimateComplexMessage.FixedRepeatedBytesHolder",
        oneof_index=1,
    )

    map_str_int32 = add_map_entry(msg, "MapStrInt32Entry", F.TYPE_STRING, F.TYPE_INT32)
    map_int32_str = add_map_entry(msg, "MapInt32StrEntry", F.TYPE_INT32, F.TYPE_STRING)
    map_bool_bytes = add_map_entry(msg, "MapBoolBytesEntry", F.TYPE_BOOL, F.TYPE_BYTES)
    map_uint64_msg = add_map_entry(
        msg,
        "MapUint64MsgEntry",
        F.TYPE_UINT64,
        F.TYPE_MESSAGE,
        value_type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1",
    )
    very_nested_map = add_map_entry(
        msg,
        "VeryNestedMapEntry",
        F.TYPE_STRING,
        F.TYPE_MESSAGE,
        value_type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1.NestedLevel2",
    )

    add_field(msg, "map_str_int32", 30, F.TYPE_MESSAGE, label=F.LABEL_REPEATED, type_name=map_str_int32)
    add_field(msg, "map_int32_str", 31, F.TYPE_MESSAGE, label=F.LABEL_REPEATED, type_name=map_int32_str)
    add_field(msg, "map_bool_bytes", 32, F.TYPE_MESSAGE, label=F.LABEL_REPEATED, type_name=map_bool_bytes)
    add_field(msg, "map_uint64_msg", 33, F.TYPE_MESSAGE, label=F.LABEL_REPEATED, type_name=map_uint64_msg)
    add_field(msg, "very_nested_map", 34, F.TYPE_MESSAGE, label=F.LABEL_REPEATED, type_name=very_nested_map)
    add_field(msg, "recursive_self", 35, F.TYPE_MESSAGE, type_name=".test.ultimate.UltimateComplexMessage")
    add_field(
        msg,
        "lots_of_nested",
        36,
        F.TYPE_MESSAGE,
        label=F.LABEL_REPEATED,
        type_name=".test.ultimate.UltimateComplexMessage.NestedLevel1.NestedLevel2",
    )
    add_field(
        msg,
        "colors",
        37,
        F.TYPE_ENUM,
        label=F.LABEL_REPEATED,
        type_name=".test.ultimate.UltimateComplexMessage.Color",
        packed=True,
    )

    msg.oneof_decl.add().name = "_opt_int32"
    msg.oneof_decl.add().name = "_opt_string"
    add_field(msg, "opt_int32", 38, F.TYPE_INT32, oneof_index=1, proto3_optional=True)
    add_field(msg, "opt_string", 39, F.TYPE_STRING, oneof_index=2, proto3_optional=True)

    level_a = msg.nested_type.add()
    level_a.name = "LevelA"
    level_b = level_a.nested_type.add()
    level_b.name = "LevelB"
    level_c = level_b.nested_type.add()
    level_c.name = "LevelC"
    level_d = level_c.nested_type.add()
    level_d.name = "LevelD"
    level_e = level_d.nested_type.add()
    level_e.name = "LevelE"
    add_field(level_e, "extreme", 1, F.TYPE_STRING)
    weird_map = add_map_entry(
        level_e,
        "WeirdMapEntry",
        F.TYPE_INT32,
        F.TYPE_STRING,
        parent_type_name=".test.ultimate.UltimateComplexMessage.LevelA.LevelB.LevelC.LevelD.LevelE",
    )
    add_field(level_e, "weird_map", 2, F.TYPE_MESSAGE, label=F.LABEL_REPEATED, type_name=weird_map)
    level_e.oneof_decl.add().name = "deep_oneof"
    add_field(level_e, "val", 3, F.TYPE_INT64, oneof_index=0)
    add_field(level_e, "text", 4, F.TYPE_STRING, oneof_index=0)

    add_field(
        msg,
        "extreme_nesting",
        40,
        F.TYPE_MESSAGE,
        type_name=".test.ultimate.UltimateComplexMessage.LevelA.LevelB.LevelC.LevelD.LevelE",
    )
    sha256 = add_field(msg, "sha256", 41, F.TYPE_BYTES)
    sha256.options.ParseFromString(array_option_bytes(expr="INTEGER_ARRAY_CAP * 4", fixed=True))
    integer_array = add_field(msg, "integer_array", 42, F.TYPE_INT32, label=F.LABEL_REPEATED)
    integer_array.options.ParseFromString(array_option_bytes(expr="INTEGER_ARRAY_CAP"))
    byte_array = add_field(msg, "byte_array", 43, F.TYPE_BYTES)
    byte_array.options.ParseFromString(array_option_bytes(expr="BYTE_ARRAY_CAP"))
    fixed_integer_array = add_field(msg, "fixed_integer_array", 44, F.TYPE_UINT32, label=F.LABEL_REPEATED)
    fixed_integer_array.options.ParseFromString(array_option_bytes(expr="FIXED_INTEGER_ARRAY_CAP", fixed=True))
    float_expr_array = add_field(msg, "float_expr_array", 45, F.TYPE_BYTES)
    float_expr_array.options.ParseFromString(array_option_bytes(expr="FLOATISH_BOUND"))
    add_field(msg, "repeated_byte_array", 46, F.TYPE_BYTES, label=F.LABEL_REPEATED)
    bounded_repeated_byte_array = add_field(msg, "bounded_repeated_byte_array", 47, F.TYPE_BYTES,
                                            label=F.LABEL_REPEATED)
    bounded_repeated_byte_array.options.ParseFromString(array_option_bytes(max_value=3))
    fixed_repeated_byte_array = add_field(msg, "fixed_repeated_byte_array", 48, F.TYPE_BYTES, label=F.LABEL_REPEATED)
    fixed_repeated_byte_array.options.ParseFromString(array_option_bytes(max_value=3, fixed=True))

    extra = file.message_type.add()
    extra.name = "ExtraMessage"
    add_field(extra, "tag", 1, F.TYPE_STRING)
    add_field(extra, "ref", 2, F.TYPE_MESSAGE, type_name=".test.ultimate.UltimateComplexMessage")

    cross = file.message_type.add()
    cross.name = "CrossMessageConstants"
    cross.options.ParseFromString(
        constant_options_bytes(
            [
                ("ROOT_MIRROR", 4, None, "UltimateComplexMessage.INTEGER_ARRAY_CAP + 2"),
                ("LABEL_COPY", 8, None, 'PREFIX + "-cross"'),
                ("READY", 1, None, "UltimateComplexMessage.HAS_PREFIX && (ROOT_MIRROR == 10)"),
            ]
        )
    )
    external_bytes = add_field(cross, "external_bytes", 1, F.TYPE_BYTES)
    external_bytes.options.ParseFromString(array_option_bytes(expr="BYTE_ARRAY_CAP + 2"))
    mirrored_values = add_field(cross, "mirrored_values", 2, F.TYPE_INT32, label=F.LABEL_REPEATED)
    mirrored_values.options.ParseFromString(array_option_bytes(expr="ROOT_MIRROR"))

    nested_cross = cross.nested_type.add()
    nested_cross.name = "Nested"
    nested_cross.options.ParseFromString(
        constant_options_bytes(
            [
                ("EXTERNAL_CAP", 4, None, "BASE_COUNT + 3"),
            ]
        )
    )
    nested_bytes = add_field(nested_cross, "nested_bytes", 1, F.TYPE_BYTES)
    nested_bytes.options.ParseFromString(array_option_bytes(expr="EXTERNAL_CAP"))

    add_field(cross, "nested", 3, F.TYPE_MESSAGE, type_name=".test.ultimate.CrossMessageConstants.Nested")

    return file


def compat_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "compat.proto"
    file.package = "test.compat"
    file.syntax = "proto3"
    file.options.optimize_for = descriptor_pb2.FileOptions.LITE_RUNTIME

    msg = file.message_type.add()
    msg.name = "EncodingMatrix"

    mode = msg.enum_type.add()
    mode.name = "Mode"
    for name, number in [
        ("MODE_UNSPECIFIED", 0),
        ("FIRST", 1),
        ("SECOND", 2),
    ]:
        value = mode.value.add()
        value.name = name
        value.number = number

    inner = msg.nested_type.add()
    inner.name = "Inner"
    add_field(inner, "value", 1, F.TYPE_INT32)
    add_field(inner, "label", 2, F.TYPE_STRING)

    add_field(msg, "f_int32", 1, F.TYPE_INT32)
    add_field(msg, "f_int64", 2, F.TYPE_INT64)
    add_field(msg, "f_uint32", 3, F.TYPE_UINT32)
    add_field(msg, "f_uint64", 4, F.TYPE_UINT64)
    add_field(msg, "f_sint32", 5, F.TYPE_SINT32)
    add_field(msg, "f_sint64", 6, F.TYPE_SINT64)
    add_field(msg, "f_bool", 7, F.TYPE_BOOL)
    add_field(msg, "mode", 8, F.TYPE_ENUM, type_name=".test.compat.EncodingMatrix.Mode")
    add_field(msg, "f_fixed32", 9, F.TYPE_FIXED32)
    add_field(msg, "f_fixed64", 10, F.TYPE_FIXED64)
    add_field(msg, "f_sfixed32", 11, F.TYPE_SFIXED32)
    add_field(msg, "f_sfixed64", 12, F.TYPE_SFIXED64)
    add_field(msg, "f_float", 13, F.TYPE_FLOAT)
    add_field(msg, "f_double", 14, F.TYPE_DOUBLE)
    add_field(msg, "f_string", 15, F.TYPE_STRING)
    add_field(msg, "f_bytes", 16, F.TYPE_BYTES)
    add_field(msg, "nested", 17, F.TYPE_MESSAGE, type_name=".test.compat.EncodingMatrix.Inner")
    add_field(msg, "r_int32_unpacked", 18, F.TYPE_INT32, label=F.LABEL_REPEATED, packed=False)
    add_field(msg, "r_int32_packed", 19, F.TYPE_INT32, label=F.LABEL_REPEATED, packed=True)
    add_field(msg, "r_double", 20, F.TYPE_DOUBLE, label=F.LABEL_REPEATED, packed=True)

    msg.oneof_decl.add().name = "special_oneof"
    add_field(msg, "oneof_string", 21, F.TYPE_STRING, oneof_index=0)
    add_field(msg, "oneof_int32", 22, F.TYPE_INT32, oneof_index=0)
    add_field(msg, "oneof_nested", 23, F.TYPE_MESSAGE, type_name=".test.compat.EncodingMatrix.Inner", oneof_index=0)
    add_field(msg, "oneof_bytes", 24, F.TYPE_BYTES, oneof_index=0)

    msg.oneof_decl.add().name = "_opt_int32"
    msg.oneof_decl.add().name = "_opt_string"
    add_field(msg, "opt_int32", 25, F.TYPE_INT32, oneof_index=1, proto3_optional=True)
    add_field(msg, "opt_string", 26, F.TYPE_STRING, oneof_index=2, proto3_optional=True)

    return file


def compat_cases_header() -> str:
    file = compat_file()
    pool = descriptor_pool.DescriptorPool()
    pool.Add(file)
    message_desc = pool.FindMessageTypeByName("test.compat.EncodingMatrix")
    message_cls = message_factory.GetMessageClass(message_desc)

    cases: list[tuple[str, bytes]] = []

    cases.append(("kEmpty", message_cls().SerializeToString()))

    message = message_cls()
    message.f_int32 = -(2**31)
    message.f_int64 = -(2**63)
    message.f_uint32 = (2**32) - 1
    message.f_uint64 = (2**64) - 1
    message.f_sint32 = -17
    message.f_sint64 = -17000000000
    message.f_bool = True
    message.mode = 2
    cases.append(("kVarint", message.SerializeToString()))

    message = message_cls()
    message.f_fixed32 = 0x11223344
    message.f_fixed64 = 0x1122334455667788
    message.f_sfixed32 = -1234567
    message.f_sfixed64 = -1234567890123
    message.f_float = -0.0
    message.f_double = 123.5
    cases.append(("kFixed", message.SerializeToString()))

    message = message_cls()
    message.f_string = "smoke"
    message.f_bytes = bytes([0x00, 0x01, 0x7F, 0x80, 0xFF])
    message.nested.value = 417
    message.nested.label = "nested"
    cases.append(("kLengthDelimited", message.SerializeToString()))

    message = message_cls()
    message.r_int32_unpacked.extend([-1, 0, 150])
    message.r_int32_packed.extend([-1, 0, 150])
    message.r_double.extend([23.5, -0.0])
    cases.append(("kRepeated", message.SerializeToString()))

    message = message_cls()
    message.oneof_string = "oneof-str"
    cases.append(("kOneofString", message.SerializeToString()))

    message = message_cls()
    message.oneof_int32 = -2701
    cases.append(("kOneofInt32", message.SerializeToString()))

    message = message_cls()
    message.oneof_nested.value = 90210
    message.oneof_nested.label = "inner"
    cases.append(("kOneofNested", message.SerializeToString()))

    message = message_cls()
    message.oneof_bytes = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    cases.append(("kOneofBytes", message.SerializeToString()))

    message = message_cls()
    message.opt_int32 = -99
    message.opt_string = "opt"
    cases.append(("kOptional", message.SerializeToString()))

    lines = [
        "#pragma once",
        "",
        "#include <array>",
        "#include <cstddef>",
        "",
        "namespace compat_cases {",
        "",
    ]
    for name, payload in cases:
        lines.append(f"inline constexpr ::std::array<unsigned char, {len(payload)}> {name} {{")
        if payload:
            row = ", ".join(f"0x{byte:02x}" for byte in payload)
            lines.append(f"    {row},")
        lines.append("};")
        lines.append("")
    lines.append("} // namespace compat_cases")
    lines.append("")
    return "\n".join(lines)


def options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "protocyte/options.proto"
    file.package = "protocyte"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    enum = file.enum_type.add()
    enum.name = "ConstantKind"
    for number, name in [
        (0, "KIND_UNSPECIFIED"),
        (1, "BOOL"),
        (2, "INT32"),
        (3, "INT64"),
        (4, "UINT32"),
        (5, "UINT64"),
        (6, "FLOAT"),
        (7, "DOUBLE"),
        (8, "STRING"),
    ]:
        value = enum.value.add()
        value.name = name
        value.number = number

    struct_constant = file.message_type.add()
    struct_constant.name = "StructConstant"
    field = struct_constant.field.add()
    field.name = "name"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field = struct_constant.field.add()
    field.name = "kind"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_ENUM
    field.type_name = ".protocyte.ConstantKind"
    add_oneof_field(struct_constant, "value", "literal", 3, F.TYPE_STRING)
    add_oneof_field(struct_constant, "value", "expr", 4, F.TYPE_STRING)

    array_options = file.message_type.add()
    array_options.name = "ArrayOptions"
    add_oneof_field(array_options, "bound", "max", 1, F.TYPE_UINT32)
    add_oneof_field(array_options, "bound", "expr", 2, F.TYPE_STRING)

    ext = file.extension.add()
    ext.name = "constant"
    ext.number = 50000
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.StructConstant"
    ext.extendee = ".google.protobuf.MessageOptions"

    ext = file.extension.add()
    ext.name = "package_constant"
    ext.number = 50002
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.StructConstant"
    ext.extendee = ".google.protobuf.FileOptions"

    ext = file.extension.add()
    ext.name = "array"
    ext.number = 50000
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.ArrayOptions"
    ext.extendee = ".google.protobuf.FieldOptions"

    ext = file.extension.add()
    ext.name = "fixed"
    ext.number = 50001
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_BOOL
    ext.extendee = ".google.protobuf.FieldOptions"

    return file


def add_oneof_field(
    message: descriptor_pb2.DescriptorProto,
    oneof_name: str,
    name: str,
    number: int,
    field_type: int,
) -> None:
    oneof_index: int | None = None
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


def array_option_bytes(*, max_value: int | None = None, expr: str | None = None, fixed: bool = False) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(options_file())
    field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    field_options_cls = message_factory.GetMessageClass(field_options_desc)
    array_ext = pool.FindExtensionByName("protocyte.array")
    fixed_ext = pool.FindExtensionByName("protocyte.fixed")

    options = field_options_cls()
    array_options = options.Extensions[array_ext]
    if max_value is not None:
        array_options.max = max_value
    if expr is not None:
        array_options.expr = expr
    if fixed:
        options.Extensions[fixed_ext] = True
    return options.SerializeToString()


def constant_options_bytes(constants: list[tuple[str, int, str | None, str | None]]) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(options_file())
    message_options_desc = pool.FindMessageTypeByName("google.protobuf.MessageOptions")
    message_options_cls = message_factory.GetMessageClass(message_options_desc)
    constant_ext = pool.FindExtensionByName("protocyte.constant")

    options = message_options_cls()
    for name, kind, literal, expr in constants:
        item = options.Extensions[constant_ext].add()
        item.name = name
        item.kind = kind
        if literal is not None:
            item.literal = literal
        if expr is not None:
            item.expr = expr
    return options.SerializeToString()


def package_constant_options_bytes(constants: list[tuple[str, int, str | None, str | None]]) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(options_file())
    file_options_desc = pool.FindMessageTypeByName("google.protobuf.FileOptions")
    file_options_cls = message_factory.GetMessageClass(file_options_desc)
    constant_ext = pool.FindExtensionByName("protocyte.package_constant")

    options = file_options_cls()
    for name, kind, literal, expr in constants:
        item = options.Extensions[constant_ext].add()
        item.name = name
        item.kind = kind
        if literal is not None:
            item.literal = literal
        if expr is not None:
            item.expr = expr
    return options.SerializeToString()


if __name__ == "__main__":
    raise SystemExit(main())
