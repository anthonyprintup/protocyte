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

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("example.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend([options_file(), example_file()])

    response = generate_response(request)
    if response.error:
        print(response.error, file=sys.stderr)
        return 1

    for item in response.file:
        path = out_dir / item.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item.content, encoding="utf-8", newline="\n")

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

    msg = file.message_type.add()
    msg.name = "UltimateComplexMessage"
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
    add_field(msg, "oneof_bytes", 29, F.TYPE_BYTES, oneof_index=0)

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
    sha256.options.ParseFromString(fixed_size_option_bytes(32))

    extra = file.message_type.add()
    extra.name = "ExtraMessage"
    add_field(extra, "tag", 1, F.TYPE_STRING)
    add_field(extra, "ref", 2, F.TYPE_MESSAGE, type_name=".test.ultimate.UltimateComplexMessage")

    return file


def options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "protocyte/options.proto"
    file.package = "protocyte"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    ext = file.extension.add()
    ext.name = "fixed_size"
    ext.number = 50000
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_UINT32
    ext.extendee = ".google.protobuf.FieldOptions"

    return file


def fixed_size_option_bytes(size: int) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(options_file())
    field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    field_options_cls = message_factory.GetMessageClass(field_options_desc)
    fixed_size = pool.FindExtensionByName("protocyte.fixed_size")

    options = field_options_cls()
    options.Extensions[fixed_size] = size
    return options.SerializeToString()


if __name__ == "__main__":
    raise SystemExit(main())
