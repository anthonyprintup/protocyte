from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from protocyte.errors import ProtocyteError

FieldDescriptorProto = descriptor_pb2.FieldDescriptorProto


CPP_KEYWORDS = {
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "atomic_cancel",
    "atomic_commit",
    "atomic_noexcept",
    "auto",
    "bitand",
    "bitor",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "char8_t",
    "char16_t",
    "char32_t",
    "class",
    "compl",
    "concept",
    "const",
    "consteval",
    "constexpr",
    "constinit",
    "const_cast",
    "continue",
    "co_await",
    "co_return",
    "co_yield",
    "decltype",
    "default",
    "delete",
    "do",
    "double",
    "dynamic_cast",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "false",
    "float",
    "for",
    "friend",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "nullptr",
    "operator",
    "or",
    "or_eq",
    "private",
    "protected",
    "public",
    "reflexpr",
    "register",
    "reinterpret_cast",
    "requires",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_assert",
    "static_cast",
    "struct",
    "switch",
    "synchronized",
    "template",
    "this",
    "thread_local",
    "throw",
    "true",
    "try",
    "typedef",
    "typeid",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "wchar_t",
    "while",
    "xor",
    "xor_eq",
}


SCALAR_CPP_TYPES = {
    FieldDescriptorProto.TYPE_DOUBLE: "double",
    FieldDescriptorProto.TYPE_FLOAT: "float",
    FieldDescriptorProto.TYPE_INT32: "int32_t",
    FieldDescriptorProto.TYPE_INT64: "int64_t",
    FieldDescriptorProto.TYPE_UINT32: "uint32_t",
    FieldDescriptorProto.TYPE_UINT64: "uint64_t",
    FieldDescriptorProto.TYPE_SINT32: "int32_t",
    FieldDescriptorProto.TYPE_SINT64: "int64_t",
    FieldDescriptorProto.TYPE_FIXED32: "uint32_t",
    FieldDescriptorProto.TYPE_FIXED64: "uint64_t",
    FieldDescriptorProto.TYPE_SFIXED32: "int32_t",
    FieldDescriptorProto.TYPE_SFIXED64: "int64_t",
    FieldDescriptorProto.TYPE_BOOL: "bool",
}

SCALAR_DEFAULTS = {
    FieldDescriptorProto.TYPE_DOUBLE: "0.0",
    FieldDescriptorProto.TYPE_FLOAT: "0.0f",
    FieldDescriptorProto.TYPE_INT32: "0",
    FieldDescriptorProto.TYPE_INT64: "0",
    FieldDescriptorProto.TYPE_UINT32: "0u",
    FieldDescriptorProto.TYPE_UINT64: "0u",
    FieldDescriptorProto.TYPE_SINT32: "0",
    FieldDescriptorProto.TYPE_SINT64: "0",
    FieldDescriptorProto.TYPE_FIXED32: "0u",
    FieldDescriptorProto.TYPE_FIXED64: "0u",
    FieldDescriptorProto.TYPE_SFIXED32: "0",
    FieldDescriptorProto.TYPE_SFIXED64: "0",
    FieldDescriptorProto.TYPE_BOOL: "false",
}

PACKABLE_TYPES = set(SCALAR_CPP_TYPES) | {FieldDescriptorProto.TYPE_ENUM}
FIXED_SIZE_OPTION_NAME = "protocyte.fixed_size"


@dataclass(slots=True)
class _CustomOptions:
    field_options_cls: type[object] | None = None
    fixed_size_extension: object | None = None

    def fixed_size(
        self,
        options: descriptor_pb2.FieldOptions,
    ) -> int | None:
        if self.field_options_cls is None or self.fixed_size_extension is None:
            return None
        parsed = self.field_options_cls()
        parsed.ParseFromString(options.SerializeToString())
        try:
            if parsed.HasExtension(self.fixed_size_extension):
                return int(parsed.Extensions[self.fixed_size_extension])
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        return None


@dataclass(slots=True)
class EnumValueModel:
    name: str
    cpp_name: str
    number: int


@dataclass(slots=True)
class EnumModel:
    name: str
    cpp_name: str
    full_name: str
    file_name: str
    package: str
    values: list[EnumValueModel]
    parent: "MessageModel | None" = None


@dataclass(slots=True)
class OneofModel:
    name: str
    cpp_name: str
    fields: list["FieldModel"] = field(default_factory=list)


@dataclass(slots=True)
class FieldModel:
    name: str
    cpp_name: str
    number: int
    proto_type: int
    label: int
    file_name: str
    repeated: bool
    proto3_optional: bool
    oneof_index: int | None
    oneof_name: str | None
    packed: bool
    deprecated: bool
    type_name: str
    kind: str
    cpp_type: str
    message_type: "MessageModel | None" = None
    enum_type: EnumModel | None = None
    map_key: "FieldModel | None" = None
    map_value: "FieldModel | None" = None
    recursive_box: bool = False
    fixed_size: int | None = None

    @property
    def has_explicit_presence(self) -> bool:
        return self.proto3_optional or self.oneof_name is not None or self.kind == "message"

    @property
    def fixed_bytes(self) -> bool:
        return self.kind == "bytes" and self.fixed_size is not None

    @property
    def packable(self) -> bool:
        return self.proto_type in PACKABLE_TYPES and not self.repeated_map

    @property
    def repeated_map(self) -> bool:
        return self.kind == "map"


@dataclass(slots=True)
class MessageModel:
    name: str
    cpp_name: str
    full_name: str
    file_name: str
    package: str
    parent: "MessageModel | None"
    descriptor: descriptor_pb2.DescriptorProto
    is_map_entry: bool = False
    fields: list[FieldModel] = field(default_factory=list)
    oneofs: list[OneofModel] = field(default_factory=list)
    nested_messages: list["MessageModel"] = field(default_factory=list)
    nested_enums: list[EnumModel] = field(default_factory=list)


@dataclass(slots=True)
class FileModel:
    name: str
    package: str
    syntax: str
    descriptor: descriptor_pb2.FileDescriptorProto
    messages: list[MessageModel] = field(default_factory=list)
    enums: list[EnumModel] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)


@dataclass(slots=True)
class DescriptorModel:
    files: dict[str, FileModel]
    file_to_generate: list[str]
    messages: dict[str, MessageModel]
    enums: dict[str, EnumModel]

    def generated_files(self) -> Iterable[FileModel]:
        for name in self.file_to_generate:
            yield self.files[name]


def build_model(request: descriptor_pb2.FileDescriptorSet | object) -> DescriptorModel:
    """Build a resolved model from a CodeGeneratorRequest-like object."""
    files_by_name = {file.name: file for file in request.proto_file}
    file_to_generate = list(request.file_to_generate)
    custom_options = _custom_options(request.proto_file)

    missing = [name for name in file_to_generate if name not in files_by_name]
    if missing:
        raise ProtocyteError(f"protoc request is missing file descriptors for: {', '.join(missing)}")

    for name in file_to_generate:
        _require_proto3(files_by_name[name], f"target file {name}")
        if files_by_name[name].extension:
            raise ProtocyteError(f"{name}: proto3 extensions are not supported")

    files: dict[str, FileModel] = {}
    messages: dict[str, MessageModel] = {}
    enums: dict[str, EnumModel] = {}

    for file in files_by_name.values():
        files[file.name] = FileModel(
            name=file.name,
            package=file.package,
            syntax=file.syntax,
            descriptor=file,
        )

    for file in files_by_name.values():
        file_model = files[file.name]
        for enum in file.enum_type:
            enum_model = _build_enum(file, enum, None, enum.name)
            file_model.enums.append(enum_model)
            enums[enum_model.full_name] = enum_model
        for message in file.message_type:
            message_model = _build_message_skeleton(file, message, None, message.name)
            file_model.messages.append(message_model)
            _register_message_tree(message_model, messages, enums)

    for file_model in files.values():
        for message in _walk_messages(file_model.messages):
            _fill_message_fields(message, files, messages, enums, custom_options)

    _validate_references(file_to_generate, files, messages, enums)
    _compute_file_dependencies(file_to_generate, files)
    _mark_recursive_boxes(messages)

    return DescriptorModel(
        files=files,
        file_to_generate=file_to_generate,
        messages=messages,
        enums=enums,
    )


def _custom_options(proto_files: Iterable[descriptor_pb2.FileDescriptorProto]) -> _CustomOptions:
    pool = descriptor_pool.DescriptorPool()
    try:
        pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    except Exception:
        return _CustomOptions()

    pending = [file for file in proto_files if file.name != descriptor_pb2.DESCRIPTOR.name]
    while pending:
        next_pending: list[descriptor_pb2.FileDescriptorProto] = []
        progressed = False
        for file in pending:
            try:
                pool.Add(file)
                progressed = True
            except Exception:
                next_pending.append(file)
        if not progressed:
            break
        pending = next_pending

    try:
        field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
        return _CustomOptions(
            field_options_cls=message_factory.GetMessageClass(field_options_desc),
            fixed_size_extension=pool.FindExtensionByName(FIXED_SIZE_OPTION_NAME),
        )
    except Exception:
        return _CustomOptions()


def cpp_identifier(name: str) -> str:
    if not name:
        return "_"
    out = []
    for index, char in enumerate(name):
        valid = char == "_" or char.isalpha() or (char.isdigit() and index > 0)
        out.append(char if valid and ord(char) < 128 else "_")
    ident = "".join(out)
    if ident in CPP_KEYWORDS:
        return f"{ident}_"
    return ident


def cpp_pascal_identifier(name: str) -> str:
    ident = cpp_identifier(name)
    if not ident:
        return "_"
    return ident[0].upper() + ident[1:]


def proto_full_name(file: descriptor_pb2.FileDescriptorProto, path: str) -> str:
    return f"{file.package}.{path}" if file.package else path


def strip_type_name(type_name: str) -> str:
    return type_name[1:] if type_name.startswith(".") else type_name


def _require_proto3(file: descriptor_pb2.FileDescriptorProto, label: str) -> None:
    if file.syntax != "proto3":
        syntax = file.syntax or "<unspecified>"
        raise ProtocyteError(f"{label}: expected syntax = \"proto3\", got {syntax!r}")
    if hasattr(file, "edition") and getattr(file, "edition"):
        raise ProtocyteError(f"{label}: protobuf Editions are not supported in v1")


def _build_enum(
    file: descriptor_pb2.FileDescriptorProto,
    enum: descriptor_pb2.EnumDescriptorProto,
    parent: MessageModel | None,
    path: str,
) -> EnumModel:
    cpp_prefix = f"{parent.cpp_name}_" if parent else ""
    values = [
        EnumValueModel(name=value.name, cpp_name=cpp_identifier(value.name), number=value.number)
        for value in enum.value
    ]
    return EnumModel(
        name=enum.name,
        cpp_name=f"{cpp_prefix}{cpp_pascal_identifier(enum.name)}",
        full_name=proto_full_name(file, path),
        file_name=file.name,
        package=file.package,
        values=values,
        parent=parent,
    )


def _build_message_skeleton(
    file: descriptor_pb2.FileDescriptorProto,
    message: descriptor_pb2.DescriptorProto,
    parent: MessageModel | None,
    path: str,
) -> MessageModel:
    cpp_prefix = f"{parent.cpp_name}_" if parent else ""
    model = MessageModel(
        name=message.name,
        cpp_name=f"{cpp_prefix}{cpp_pascal_identifier(message.name)}",
        full_name=proto_full_name(file, path),
        file_name=file.name,
        package=file.package,
        parent=parent,
        descriptor=message,
        is_map_entry=message.options.map_entry,
    )
    for enum in message.enum_type:
        model.nested_enums.append(_build_enum(file, enum, model, f"{path}.{enum.name}"))
    for nested in message.nested_type:
        child = _build_message_skeleton(file, nested, model, f"{path}.{nested.name}")
        model.nested_messages.append(child)
    return model


def _register_message_tree(
    message: MessageModel,
    messages: dict[str, MessageModel],
    enums: dict[str, EnumModel],
) -> None:
    messages[message.full_name] = message
    for enum in message.nested_enums:
        enums[enum.full_name] = enum
    for nested in message.nested_messages:
        _register_message_tree(nested, messages, enums)


def _walk_messages(messages: Iterable[MessageModel]) -> Iterable[MessageModel]:
    for message in messages:
        yield message
        yield from _walk_messages(message.nested_messages)


def _fill_message_fields(
    message: MessageModel,
    files: dict[str, FileModel],
    messages: dict[str, MessageModel],
    enums: dict[str, EnumModel],
    custom_options: _CustomOptions,
) -> None:
    oneof_fields: dict[int, OneofModel] = {}
    for index, oneof in enumerate(message.descriptor.oneof_decl):
        oneof_fields[index] = OneofModel(
            name=oneof.name,
            cpp_name=cpp_pascal_identifier(oneof.name),
        )

    for field_proto in message.descriptor.field:
        field_model = _build_field(message, field_proto, messages, enums, custom_options)
        message.fields.append(field_model)
        if field_model.oneof_index is not None and field_model.oneof_name is not None:
            oneof_fields[field_model.oneof_index].fields.append(field_model)

    message.oneofs = [oneof for _, oneof in sorted(oneof_fields.items()) if oneof.fields]
    if files[message.file_name].syntax == "proto3":
        for field_model in message.fields:
            if field_model.kind in {"message", "enum"}:
                referenced_file = (
                    field_model.message_type.file_name
                    if field_model.message_type is not None
                    else field_model.enum_type.file_name
                )
                _require_proto3(files[referenced_file].descriptor, f"{message.full_name}.{field_model.name}")


def _build_field(
    owner: MessageModel,
    proto: descriptor_pb2.FieldDescriptorProto,
    messages: dict[str, MessageModel],
    enums: dict[str, EnumModel],
    custom_options: _CustomOptions,
) -> FieldModel:
    if proto.type == FieldDescriptorProto.TYPE_GROUP:
        raise ProtocyteError(f"{owner.full_name}.{proto.name}: groups are not supported by proto3")

    oneof_index = proto.oneof_index if proto.HasField("oneof_index") else None
    oneof_name = None
    if oneof_index is not None and not proto.proto3_optional:
        oneof_name = owner.descriptor.oneof_decl[oneof_index].name

    repeated = proto.label == FieldDescriptorProto.LABEL_REPEATED
    packed = _is_packed(proto)
    kind = "scalar"
    cpp_type = SCALAR_CPP_TYPES.get(proto.type, "")
    message_type = None
    enum_type = None
    map_key = None
    map_value = None
    type_name = strip_type_name(proto.type_name)
    fixed_size = custom_options.fixed_size(proto.options)

    if proto.type == FieldDescriptorProto.TYPE_STRING:
        kind = "string"
        cpp_type = "typename Config::String"
    elif proto.type == FieldDescriptorProto.TYPE_BYTES:
        kind = "bytes"
        cpp_type = "typename Config::Bytes"
    elif proto.type == FieldDescriptorProto.TYPE_ENUM:
        kind = "enum"
        enum_type = _resolve(enums, type_name, owner, proto.name, "enum")
        cpp_type = "int32_t"
    elif proto.type == FieldDescriptorProto.TYPE_MESSAGE:
        message_type = _resolve(messages, type_name, owner, proto.name, "message")
        if repeated and message_type.is_map_entry:
            kind = "map"
            key_proto = message_type.descriptor.field[0]
            value_proto = message_type.descriptor.field[1]
            map_key = _build_field(message_type, key_proto, messages, enums, custom_options)
            map_value = _build_field(message_type, value_proto, messages, enums, custom_options)
            cpp_type = f"typename Config::template Map<{map_key.cpp_type}, {map_value.cpp_type}>"
        else:
            kind = "message"
            cpp_type = ""
    elif proto.type not in SCALAR_CPP_TYPES:
        raise ProtocyteError(f"{owner.full_name}.{proto.name}: unsupported field type {proto.type}")

    if fixed_size is not None:
        if proto.type != FieldDescriptorProto.TYPE_BYTES:
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.fixed_size is only supported on bytes fields")
        if repeated:
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.fixed_size does not support repeated fields")
        if proto.proto3_optional or oneof_index is not None:
            raise ProtocyteError(
                f"{owner.full_name}.{proto.name}: protocyte.fixed_size does not support optional or oneof fields"
            )
        if fixed_size <= 0:
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.fixed_size must be greater than zero")

    return FieldModel(
        name=proto.name,
        cpp_name=cpp_identifier(proto.name),
        number=proto.number,
        proto_type=proto.type,
        label=proto.label,
        file_name=owner.file_name,
        repeated=repeated,
        proto3_optional=proto.proto3_optional,
        oneof_index=oneof_index,
        oneof_name=oneof_name,
        packed=packed,
        deprecated=proto.options.deprecated,
        type_name=type_name,
        kind=kind,
        cpp_type=cpp_type,
        message_type=message_type,
        enum_type=enum_type,
        map_key=map_key,
        map_value=map_value,
        fixed_size=fixed_size,
    )


def _resolve(
    table: dict[str, object],
    type_name: str,
    owner: MessageModel,
    field_name: str,
    expected: str,
):
    try:
        return table[type_name]
    except KeyError as exc:
        raise ProtocyteError(
            f"{owner.full_name}.{field_name}: unresolved {expected} type {type_name!r}"
        ) from exc


def _is_packed(proto: descriptor_pb2.FieldDescriptorProto) -> bool:
    if proto.label != FieldDescriptorProto.LABEL_REPEATED:
        return False
    if proto.type not in PACKABLE_TYPES:
        return False
    try:
        if proto.options.HasField("packed"):
            return proto.options.packed
    except ValueError:
        pass
    return True


def _validate_references(
    file_to_generate: list[str],
    files: dict[str, FileModel],
    messages: dict[str, MessageModel],
    enums: dict[str, EnumModel],
) -> None:
    generated = set(file_to_generate)
    for file_name in generated:
        file_model = files[file_name]
        for message in _walk_messages(file_model.messages):
            for field_model in message.fields:
                targets: list[str] = []
                if field_model.message_type is not None:
                    targets.append(field_model.message_type.file_name)
                if field_model.enum_type is not None:
                    targets.append(field_model.enum_type.file_name)
                if field_model.map_value and field_model.map_value.message_type is not None:
                    targets.append(field_model.map_value.message_type.file_name)
                if field_model.map_value and field_model.map_value.enum_type is not None:
                    targets.append(field_model.map_value.enum_type.file_name)
                for target in targets:
                    _require_proto3(
                        files[target].descriptor,
                        f"{message.full_name}.{field_model.name} referenced type file {target}",
                    )


def _compute_file_dependencies(file_to_generate: list[str], files: dict[str, FileModel]) -> None:
    for file_name in file_to_generate:
        file_model = files[file_name]
        for message in _walk_messages(file_model.messages):
            for field_model in message.fields:
                for dependency in _field_dependencies(field_model):
                    if dependency != file_name:
                        file_model.dependencies.add(dependency)


def _field_dependencies(field_model: FieldModel) -> Iterable[str]:
    if field_model.message_type is not None and not field_model.message_type.is_map_entry:
        yield field_model.message_type.file_name
    if field_model.enum_type is not None:
        yield field_model.enum_type.file_name
    if field_model.map_key is not None:
        yield from _field_dependencies(field_model.map_key)
    if field_model.map_value is not None:
        yield from _field_dependencies(field_model.map_value)


def _mark_recursive_boxes(messages: dict[str, MessageModel]) -> None:
    graph: dict[str, set[str]] = {name: set() for name in messages}
    direct_fields: list[tuple[MessageModel, FieldModel, MessageModel]] = []

    for message in messages.values():
        if message.is_map_entry:
            continue
        for field_model in message.fields:
            if field_model.kind == "message" and not field_model.repeated and field_model.message_type:
                graph[message.full_name].add(field_model.message_type.full_name)
                direct_fields.append((message, field_model, field_model.message_type))

    for owner, field_model, target in direct_fields:
        if _can_reach(graph, target.full_name, owner.full_name):
            field_model.recursive_box = True


def _can_reach(graph: dict[str, set[str]], start: str, goal: str) -> bool:
    stack = [start]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current == goal:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, ()))
    return False
