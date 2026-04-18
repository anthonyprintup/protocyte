from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Callable, Iterable

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
ARRAY_OPTION_NAME = "protocyte.array"
FIXED_OPTION_NAME = "protocyte.fixed"
CONSTANT_OPTION_NAME = "protocyte.constant"
CONSTANT_KIND_BOOL = "bool"
CONSTANT_KIND_INT32 = "int32"
CONSTANT_KIND_INT64 = "int64"
CONSTANT_KIND_UINT32 = "uint32"
CONSTANT_KIND_UINT64 = "uint64"
CONSTANT_KIND_FLOAT = "float"
CONSTANT_KIND_DOUBLE = "double"
CONSTANT_KIND_STRING = "string"

_CONSTANT_KIND_MAP = {
    1: CONSTANT_KIND_BOOL,
    2: CONSTANT_KIND_INT32,
    3: CONSTANT_KIND_INT64,
    4: CONSTANT_KIND_UINT32,
    5: CONSTANT_KIND_UINT64,
    6: CONSTANT_KIND_FLOAT,
    7: CONSTANT_KIND_DOUBLE,
    8: CONSTANT_KIND_STRING,
}


@dataclass(slots=True)
class _RawConstantOption:
    name: str
    kind: int
    literal: str | None
    expr: str | None


@dataclass(slots=True)
class _CustomOptions:
    field_options_cls: type[object] | None = None
    message_options_cls: type[object] | None = None
    array_extension: object | None = None
    fixed_extension: object | None = None
    constant_extension: object | None = None

    def field_array(
        self,
        options: descriptor_pb2.FieldOptions,
    ) -> tuple[int | None, str | None, bool]:
        if (
            self.field_options_cls is None
            or self.array_extension is None
            or self.fixed_extension is None
        ):
            return None, None, False
        parsed = self.field_options_cls()
        parsed.ParseFromString(options.SerializeToString())
        max_value: int | None = None
        max_expr: str | None = None
        fixed = False
        try:
            if parsed.HasExtension(self.array_extension):
                array_options = parsed.Extensions[self.array_extension]
                if array_options.HasField("max"):
                    max_value = int(array_options.max)
                if array_options.HasField("expr"):
                    max_expr = str(array_options.expr)
            if parsed.HasExtension(self.fixed_extension):
                fixed = bool(parsed.Extensions[self.fixed_extension])
        except (AttributeError, KeyError, TypeError, ValueError):
            return None, None, False
        return max_value, max_expr, fixed

    def message_constants(
        self,
        options: descriptor_pb2.MessageOptions,
    ) -> list[_RawConstantOption]:
        if self.message_options_cls is None or self.constant_extension is None:
            return []
        parsed = self.message_options_cls()
        parsed.ParseFromString(options.SerializeToString())
        out: list[_RawConstantOption] = []
        try:
            for item in parsed.Extensions[self.constant_extension]:
                literal = str(item.literal) if item.HasField("literal") else None
                expr = str(item.expr) if item.HasField("expr") else None
                out.append(
                    _RawConstantOption(
                        name=str(item.name),
                        kind=int(item.kind),
                        literal=literal,
                        expr=expr,
                    )
                )
        except (AttributeError, KeyError, TypeError, ValueError):
            return []
        return out


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
class ConstantModel:
    name: str
    cpp_name: str
    kind: str
    literal: str | None
    expr: str | None
    value: object | None = None
    family: str = ""
    cpp_type: str = ""
    cpp_value: str = ""


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
    array_max: int | None = None
    array_expr: str | None = None
    array_cpp_max: str | None = None
    array_fixed: bool = False

    @property
    def has_explicit_presence(self) -> bool:
        return self.proto3_optional or self.oneof_name is not None or self.kind == "message"

    @property
    def array_enabled(self) -> bool:
        return self.array_max is not None or self.array_expr is not None

    @property
    def fixed_bytes(self) -> bool:
        return self.kind == "bytes" and self.array_enabled and self.array_fixed

    @property
    def dynamic_bytes(self) -> bool:
        return self.kind == "bytes" and self.array_enabled and not self.array_fixed

    @property
    def repeated_array(self) -> bool:
        return self.repeated and self.array_enabled and not self.repeated_map

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
    constants: list[ConstantModel] = field(default_factory=list)


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


@dataclass(slots=True)
class _TypedValue:
    family: str
    value: object
    cpp_expr: str = ""
    cpp_precedence: int = 100


class _ExprParser:
    def __init__(
        self,
        text: str,
        resolve_name: Callable[[str], _TypedValue],
        label: str,
        *,
        unsigned_integer_literals: bool = False,
    ) -> None:
        self._tokens = _tokenize(text, label)
        self._index = 0
        self._resolve_name = resolve_name
        self._label = label
        self._unsigned_integer_literals = unsigned_integer_literals

    def parse(self) -> _TypedValue:
        value = self._parse_or()
        if self._peek()[0] != "EOF":
            raise ProtocyteError(f"{self._label}: unexpected token {self._peek()[1]!r}")
        return value

    def _parse_or(self) -> _TypedValue:
        value = self._parse_and()
        while self._match("||"):
            rhs = self._parse_and()
            value = _bool_value(
                _expect_bool(value, self._label) or _expect_bool(rhs, self._label),
                cpp_expr=_binary_cpp(value, rhs, "||", 10),
                cpp_precedence=10,
            )
        return value

    def _parse_and(self) -> _TypedValue:
        value = self._parse_equality()
        while self._match("&&"):
            rhs = self._parse_equality()
            value = _bool_value(
                _expect_bool(value, self._label) and _expect_bool(rhs, self._label),
                cpp_expr=_binary_cpp(value, rhs, "&&", 20),
                cpp_precedence=20,
            )
        return value

    def _parse_equality(self) -> _TypedValue:
        value = self._parse_compare()
        while True:
            if self._match("=="):
                rhs = self._parse_compare()
                value = _bool_value(
                    _compare_equal(value, rhs, self._label),
                    cpp_expr=_binary_cpp(value, rhs, "==", 30),
                    cpp_precedence=30,
                )
                continue
            if self._match("!="):
                rhs = self._parse_compare()
                value = _bool_value(
                    not _compare_equal(value, rhs, self._label),
                    cpp_expr=_binary_cpp(value, rhs, "!=", 30),
                    cpp_precedence=30,
                )
                continue
            return value

    def _parse_compare(self) -> _TypedValue:
        value = self._parse_add()
        while True:
            if self._match("<"):
                rhs = self._parse_add()
                value = _bool_value(
                    _numeric_compare(value, rhs, self._label, lambda lhs, rhs: lhs < rhs),
                    cpp_expr=_binary_cpp(value, rhs, "<", 40),
                    cpp_precedence=40,
                )
                continue
            if self._match("<="):
                rhs = self._parse_add()
                value = _bool_value(
                    _numeric_compare(value, rhs, self._label, lambda lhs, rhs: lhs <= rhs),
                    cpp_expr=_binary_cpp(value, rhs, "<=", 40),
                    cpp_precedence=40,
                )
                continue
            if self._match(">"):
                rhs = self._parse_add()
                value = _bool_value(
                    _numeric_compare(value, rhs, self._label, lambda lhs, rhs: lhs > rhs),
                    cpp_expr=_binary_cpp(value, rhs, ">", 40),
                    cpp_precedence=40,
                )
                continue
            if self._match(">="):
                rhs = self._parse_add()
                value = _bool_value(
                    _numeric_compare(value, rhs, self._label, lambda lhs, rhs: lhs >= rhs),
                    cpp_expr=_binary_cpp(value, rhs, ">=", 40),
                    cpp_precedence=40,
                )
                continue
            return value

    def _parse_add(self) -> _TypedValue:
        value = self._parse_mul()
        while True:
            if self._match("+"):
                rhs = self._parse_mul()
                if value.family == CONSTANT_KIND_STRING or rhs.family == CONSTANT_KIND_STRING:
                    if value.family != CONSTANT_KIND_STRING or rhs.family != CONSTANT_KIND_STRING:
                        raise ProtocyteError(f"{self._label}: '+' requires both operands to be numeric or string")
                    value = _string_value(
                        str(value.value) + str(rhs.value),
                        cpp_expr=_binary_cpp(value, rhs, "+", 50),
                        cpp_precedence=50,
                    )
                else:
                    value = _numeric_binary(value, rhs, self._label, lambda lhs, rhs: lhs + rhs, symbol="+", precedence=50)
                continue
            if self._match("-"):
                rhs = self._parse_mul()
                value = _numeric_binary(value, rhs, self._label, lambda lhs, rhs: lhs - rhs, symbol="-", precedence=50)
                continue
            return value

    def _parse_mul(self) -> _TypedValue:
        value = self._parse_unary()
        while True:
            if self._match("*"):
                rhs = self._parse_unary()
                value = _numeric_binary(value, rhs, self._label, lambda lhs, rhs: lhs * rhs, symbol="*", precedence=60)
                continue
            if self._match("/"):
                rhs = self._parse_unary()
                lhs_value, rhs_value, result_family = _numeric_operands(value, rhs, self._label)
                if rhs_value == 0:
                    raise ProtocyteError(f"{self._label}: division by zero")
                if result_family == "float":
                    value = _numeric_value(
                        lhs_value / rhs_value,
                        cpp_expr=_binary_cpp(value, rhs, "/", 60),
                        cpp_precedence=60,
                    )
                else:
                    value = _numeric_value(
                        int(lhs_value / rhs_value),
                        cpp_expr=_binary_cpp(value, rhs, "/", 60),
                        cpp_precedence=60,
                    )
                continue
            if self._match("%"):
                rhs = self._parse_unary()
                lhs_value, rhs_value, result_family = _numeric_operands(value, rhs, self._label)
                if rhs_value == 0:
                    raise ProtocyteError(f"{self._label}: modulo by zero")
                if result_family == "float":
                    raise ProtocyteError(f"{self._label}: '%' only supports integer operands")
                value = _numeric_value(
                    lhs_value % rhs_value,
                    cpp_expr=_binary_cpp(value, rhs, "%", 60),
                    cpp_precedence=60,
                )
                continue
            return value

    def _parse_unary(self) -> _TypedValue:
        if self._match("!"):
            value = self._parse_unary()
            return _bool_value(
                not _expect_bool(value, self._label),
                cpp_expr="!" + _wrap_cpp(value, 90),
                cpp_precedence=90,
            )
        if self._match("+"):
            value = self._parse_unary()
            _expect_numeric(value, self._label)
            return _numeric_value(_expect_numeric(value, self._label), cpp_expr="+" + _wrap_cpp(value, 90), cpp_precedence=90)
        if self._match("-"):
            value = self._parse_unary()
            return _numeric_value(
                -_expect_numeric(value, self._label),
                cpp_expr="-" + _wrap_cpp(value, 90),
                cpp_precedence=90,
            )
        return self._parse_primary()

    def _parse_primary(self) -> _TypedValue:
        token_type, token_value = self._peek()
        if token_type == "NUMBER":
            self._index += 1
            return _numeric_value(
                _parse_number_token(token_value, self._label),
                cpp_expr=_cpp_number_token(token_value, unsigned_integer=self._unsigned_integer_literals),
            )
        if token_type == "STRING":
            self._index += 1
            return _string_value(ast.literal_eval(token_value), cpp_expr=token_value)
        if token_type == "IDENT":
            self._index += 1
            if token_value == "true":
                return _bool_value(True, cpp_expr="true")
            if token_value == "false":
                return _bool_value(False, cpp_expr="false")
            if self._match("("):
                args: list[_TypedValue] = []
                if not self._match(")"):
                    while True:
                        args.append(self._parse_or())
                        if self._match(")"):
                            break
                        self._expect(",")
                return _evaluate_function(token_value, args, self._label)
            return self._resolve_name(token_value)
        if self._match("("):
            value = self._parse_or()
            self._expect(")")
            return value
        raise ProtocyteError(f"{self._label}: unexpected token {token_value!r}")

    def _peek(self) -> tuple[str, str]:
        return self._tokens[self._index]

    def _match(self, token: str) -> bool:
        if self._peek()[1] == token:
            self._index += 1
            return True
        return False

    def _expect(self, token: str) -> None:
        if not self._match(token):
            raise ProtocyteError(f"{self._label}: expected {token!r}, got {self._peek()[1]!r}")


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
            _fill_message_details(message, files, messages, enums, custom_options)

    _resolve_constants_and_arrays(messages)
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
        message_options_desc = pool.FindMessageTypeByName("google.protobuf.MessageOptions")
        field_options_cls = message_factory.GetMessageClass(field_options_desc)
        message_options_cls = message_factory.GetMessageClass(message_options_desc)
    except Exception:
        return _CustomOptions()

    return _CustomOptions(
        field_options_cls=field_options_cls,
        message_options_cls=message_options_cls,
        array_extension=_find_extension(pool, ARRAY_OPTION_NAME),
        fixed_extension=_find_extension(pool, FIXED_OPTION_NAME),
        constant_extension=_find_extension(pool, CONSTANT_OPTION_NAME),
    )


def _find_extension(pool: descriptor_pool.DescriptorPool, name: str) -> object | None:
    try:
        return pool.FindExtensionByName(name)
    except Exception:
        return None


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
        raise ProtocyteError(f'{label}: expected syntax = "proto3", got {syntax!r}')
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


def _fill_message_details(
    message: MessageModel,
    files: dict[str, FileModel],
    messages: dict[str, MessageModel],
    enums: dict[str, EnumModel],
    custom_options: _CustomOptions,
) -> None:
    message.constants = _build_constants(message, custom_options)
    _validate_constant_collisions(message)

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


def _build_constants(message: MessageModel, custom_options: _CustomOptions) -> list[ConstantModel]:
    constants: list[ConstantModel] = []
    for raw in custom_options.message_constants(message.descriptor.options):
        kind = _CONSTANT_KIND_MAP.get(raw.kind)
        if kind is None:
            raise ProtocyteError(f"{message.full_name}: unsupported constant kind {raw.kind}")
        if not raw.name:
            raise ProtocyteError(f"{message.full_name}: constant name must not be empty")
        if raw.literal is not None and raw.expr is not None:
            raise ProtocyteError(f"{message.full_name}.{raw.name}: exactly one of literal or expr must be set")
        if raw.literal is None and raw.expr is None:
            raise ProtocyteError(f"{message.full_name}.{raw.name}: exactly one of literal or expr must be set")
        constants.append(
            ConstantModel(
                name=raw.name,
                cpp_name=cpp_identifier(raw.name),
                kind=kind,
                literal=raw.literal,
                expr=raw.expr,
            )
        )
    return constants


def _validate_constant_collisions(message: MessageModel) -> None:
    seen_names: set[str] = set()
    seen_cpp_names: set[str] = set()
    reserved = {
        "Context",
        "RuntimeStatus",
        "FieldNumber",
        "create",
        "clone",
        "copy_from",
        "parse",
        "merge_from",
        "serialize",
        "encoded_size",
    }
    reserved.update(enum.name for enum in message.nested_enums)
    reserved.update(nested.name for nested in message.nested_messages if not nested.is_map_entry)
    reserved.update(cpp_identifier(oneof.name) for oneof in message.oneofs)
    reserved.update(cpp_pascal_identifier(oneof.name) + "Case" for oneof in message.oneofs)
    for proto_field in message.descriptor.field:
        cpp_name = cpp_identifier(proto_field.name)
        reserved.add(cpp_name)
        reserved.add(f"clear_{cpp_name}")
        reserved.add(f"set_{cpp_name}")
        reserved.add(f"mutable_{cpp_name}")
        reserved.add(f"has_{cpp_name}")
        reserved.add(f"ensure_{cpp_name}")
        reserved.add(f"{cpp_name}_raw")
        reserved.add(f"set_{cpp_name}_raw")

    for constant in message.constants:
        if constant.name in seen_names:
            raise ProtocyteError(f"{message.full_name}.{constant.name}: constant cannot be redefined")
        seen_names.add(constant.name)
        if not constant.cpp_name or constant.cpp_name == "_":
            raise ProtocyteError(f"{message.full_name}.{constant.name}: constant name is not a valid C++ identifier")
        if constant.cpp_name in seen_cpp_names:
            raise ProtocyteError(
                f"{message.full_name}.{constant.name}: constant collides after C++ identifier normalization"
            )
        if constant.cpp_name in reserved:
            raise ProtocyteError(f"{message.full_name}.{constant.name}: constant collides with generated API")
        seen_cpp_names.add(constant.cpp_name)


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
    array_max, array_expr, array_fixed = custom_options.field_array(proto.options)

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

    if array_fixed and array_max is None and array_expr is None:
        raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.fixed requires protocyte.array")
    if array_max is not None and array_expr is not None:
        raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.array requires exactly one of max or expr")
    if array_max is not None or array_expr is not None:
        if kind == "map":
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.array is not supported on map fields")
        if kind != "bytes" and not repeated:
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.array is only supported on bytes or repeated fields")
        if array_max is not None and array_max <= 0:
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.array.max must be greater than zero")
        if array_expr is not None and not array_expr.strip():
            raise ProtocyteError(f"{owner.full_name}.{proto.name}: protocyte.array.expr must not be empty")

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
        array_max=array_max,
        array_expr=array_expr,
        array_cpp_max=None,
        array_fixed=array_fixed,
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


def _resolve_constants_and_arrays(messages: dict[str, MessageModel]) -> None:
    constants_by_message = {
        message.full_name: {constant.name: constant for constant in message.constants}
        for message in messages.values()
    }
    states: dict[tuple[str, str], str] = {}

    def find_constant(owner: MessageModel, name: str) -> tuple[MessageModel, ConstantModel]:
        if "." in name:
            parts = name.split(".")
            if len(parts) < 2:
                raise ProtocyteError(f"{owner.full_name}: invalid constant reference {name!r}")
            message_path = ".".join(parts[:-1])
            message_name = f"{owner.package}.{message_path}" if owner.package else message_path
            target_message = messages.get(message_name)
            if target_message is None:
                raise ProtocyteError(f"{owner.full_name}: unknown constant scope {message_path!r}")
            target_constant = constants_by_message.get(target_message.full_name, {}).get(parts[-1])
            if target_constant is None:
                raise ProtocyteError(f"{owner.full_name}: unknown constant {name!r}")
            return target_message, target_constant

        current: MessageModel | None = owner
        while current is not None:
            target_constant = constants_by_message.get(current.full_name, {}).get(name)
            if target_constant is not None:
                return current, target_constant
            current = current.parent
        raise ProtocyteError(f"{owner.full_name}: unknown constant {name!r}")

    def resolve_constant(owner: MessageModel, constant: ConstantModel) -> _TypedValue:
        key = (owner.full_name, constant.name)
        state = states.get(key)
        if state == "visiting":
            raise ProtocyteError(f"{owner.full_name}.{constant.name}: constant expression cycle detected")
        if state == "done":
            return _TypedValue(constant.family, constant.value, cpp_expr=_inline_constant_cpp_expr(constant))
        states[key] = "visiting"
        if constant.literal is not None:
            value = _coerce_literal(constant.kind, constant.literal, f"{owner.full_name}.{constant.name}")
        else:
            assert constant.expr is not None
            parsed = _ExprParser(
                constant.expr,
                lambda name: lookup_constant(owner, name),
                f"{owner.full_name}.{constant.name}",
            ).parse()
            value = _coerce_expression_value(constant.kind, parsed, f"{owner.full_name}.{constant.name}")
        constant.family = _constant_family(constant.kind)
        constant.value = value
        constant.cpp_type = _cpp_constant_type(constant.kind)
        constant.cpp_value = _cpp_constant_value(constant.kind, value)
        states[key] = "done"
        return _TypedValue(constant.family, constant.value, cpp_expr=_inline_constant_cpp_expr(constant))

    def lookup_constant(owner: MessageModel, name: str) -> _TypedValue:
        target_message, target_constant = find_constant(owner, name)
        return resolve_constant(target_message, target_constant)

    def lookup_constant_for_array(owner: MessageModel, name: str) -> _TypedValue:
        target_message, target_constant = find_constant(owner, name)
        resolved = resolve_constant(target_message, target_constant)
        cpp_expr = target_constant.cpp_name if target_message.full_name == owner.full_name else _inline_constant_cpp_expr(target_constant)
        return _TypedValue(resolved.family, resolved.value, cpp_expr=cpp_expr)

    for message in messages.values():
        if message.is_map_entry:
            continue
        for constant in message.constants:
            resolve_constant(message, constant)
        for field_model in message.fields:
            if field_model.array_expr is None:
                continue
            value = _ExprParser(
                field_model.array_expr,
                lambda name, owner=message: lookup_constant_for_array(owner, name),
                f"{message.full_name}.{field_model.name}",
                unsigned_integer_literals=True,
            ).parse()
            numeric = _coerce_expression_value(
                CONSTANT_KIND_UINT32,
                value,
                f"{message.full_name}.{field_model.name}",
            )
            if not isinstance(numeric, int) or numeric <= 0:
                raise ProtocyteError(
                    f"{message.full_name}.{field_model.name}: protocyte.array.expr must resolve to a positive integer"
                )
            field_model.array_max = numeric
            if type(value.value) is int:
                field_model.array_cpp_max = value.cpp_expr
            else:
                field_model.array_cpp_max = _cpp_constant_value(CONSTANT_KIND_UINT32, numeric)


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


def _tokenize(text: str, label: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    index = 0
    multi_ops = ("&&", "||", "==", "!=", "<=", ">=")
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        matched = next((op for op in multi_ops if text.startswith(op, index)), None)
        if matched is not None:
            tokens.append(("OP", matched))
            index += len(matched)
            continue
        if char in "+-*/%()!,<>":
            tokens.append(("OP", char))
            index += 1
            continue
        if char in {'"', "'"}:
            end = index + 1
            escaped = False
            while end < len(text):
                next_char = text[end]
                if escaped:
                    escaped = False
                elif next_char == "\\":
                    escaped = True
                elif next_char == char:
                    end += 1
                    break
                end += 1
            else:
                raise ProtocyteError(f"{label}: unterminated string literal")
            tokens.append(("STRING", text[index:end]))
            index = end
            continue
        if char.isdigit():
            end = index
            if char == "0" and end + 1 < len(text) and text[end + 1] in {"x", "X"}:
                end += 2
                hex_start = end
                while end < len(text) and (text[end].isdigit() or text[end].lower() in {"a", "b", "c", "d", "e", "f"}):
                    end += 1
                if end == hex_start:
                    raise ProtocyteError(f"{label}: invalid numeric literal {text[index:end]!r}")
            else:
                while end < len(text) and text[end].isdigit():
                    end += 1
                if end < len(text) and text[end] == ".":
                    end += 1
                    while end < len(text) and text[end].isdigit():
                        end += 1
                if end < len(text) and text[end] in {"e", "E"}:
                    exp = end + 1
                    if exp < len(text) and text[exp] in {"+", "-"}:
                        exp += 1
                    while exp < len(text) and text[exp].isdigit():
                        exp += 1
                    end = exp
            tokens.append(("NUMBER", text[index:end]))
            index = end
            continue
        if char.isalpha() or char == "_":
            end = index + 1
            while end < len(text) and (text[end].isalnum() or text[end] in {"_", "."}):
                end += 1
            tokens.append(("IDENT", text[index:end]))
            index = end
            continue
        raise ProtocyteError(f"{label}: unexpected character {char!r}")
    tokens.append(("EOF", "EOF"))
    return tokens


def _parse_number_token(token: str, label: str) -> int | float:
    try:
        if "." in token or "e" in token or "E" in token:
            value = float(token)
            if not math.isfinite(value):
                raise ProtocyteError(f"{label}: numeric literal must be finite")
            return value
        return int(token, 0)
    except ValueError as exc:
        raise ProtocyteError(f"{label}: invalid numeric literal {token!r}") from exc


def _constant_family(kind: str) -> str:
    if kind == CONSTANT_KIND_BOOL:
        return CONSTANT_KIND_BOOL
    if kind == CONSTANT_KIND_STRING:
        return CONSTANT_KIND_STRING
    return "numeric"


def _wrap_cpp(value: _TypedValue, precedence: int) -> str:
    if not value.cpp_expr:
        return ""
    if value.cpp_precedence < precedence:
        return f"({value.cpp_expr})"
    return value.cpp_expr


def _binary_cpp(lhs: _TypedValue, rhs: _TypedValue, symbol: str, precedence: int) -> str:
    return f"{_wrap_cpp(lhs, precedence)} {symbol} {_wrap_cpp(rhs, precedence + 1)}"


def _cpp_number_token(token: str, *, unsigned_integer: bool) -> str:
    if unsigned_integer and "." not in token and "e" not in token and "E" not in token:
        return f"{token}u"
    return token


def _bool_value(value: bool, *, cpp_expr: str | None = None, cpp_precedence: int = 100) -> _TypedValue:
    return _TypedValue(CONSTANT_KIND_BOOL, value, cpp_expr or ("true" if value else "false"), cpp_precedence)


def _string_value(value: str, *, cpp_expr: str | None = None, cpp_precedence: int = 100) -> _TypedValue:
    if cpp_expr is None:
        cpp_expr = f'"{_cpp_escape_string(value)}"'
    return _TypedValue(CONSTANT_KIND_STRING, value, cpp_expr, cpp_precedence)


def _numeric_value(
    value: int | float,
    *,
    cpp_expr: str | None = None,
    cpp_precedence: int = 100,
) -> _TypedValue:
    if isinstance(value, float) and not math.isfinite(value):
        raise ProtocyteError("numeric expression must be finite")
    if cpp_expr is None:
        cpp_expr = str(value)
    return _TypedValue("numeric", value, cpp_expr, cpp_precedence)


def _cpp_escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _expect_bool(value: _TypedValue, label: str) -> bool:
    if value.family != CONSTANT_KIND_BOOL:
        raise ProtocyteError(f"{label}: expected bool expression")
    return bool(value.value)


def _expect_numeric(value: _TypedValue, label: str) -> int | float:
    if value.family != "numeric":
        raise ProtocyteError(f"{label}: expected numeric expression")
    return value.value  # type: ignore[return-value]


def _numeric_operands(lhs: _TypedValue, rhs: _TypedValue, label: str) -> tuple[int | float, int | float, str]:
    left = _expect_numeric(lhs, label)
    right = _expect_numeric(rhs, label)
    result_family = "float" if isinstance(left, float) or isinstance(right, float) else "int"
    return left, right, result_family


def _numeric_binary(
    lhs: _TypedValue,
    rhs: _TypedValue,
    label: str,
    op: Callable[[int | float, int | float], int | float],
    *,
    symbol: str,
    precedence: int,
) -> _TypedValue:
    left, right, _ = _numeric_operands(lhs, rhs, label)
    return _numeric_value(op(left, right), cpp_expr=_binary_cpp(lhs, rhs, symbol, precedence), cpp_precedence=precedence)


def _numeric_compare(
    lhs: _TypedValue,
    rhs: _TypedValue,
    label: str,
    op: Callable[[int | float, int | float], bool],
) -> bool:
    left, right, _ = _numeric_operands(lhs, rhs, label)
    return op(left, right)


def _compare_equal(lhs: _TypedValue, rhs: _TypedValue, label: str) -> bool:
    if lhs.family != rhs.family:
        raise ProtocyteError(f"{label}: equality requires operands of the same type")
    return lhs.value == rhs.value


def _evaluate_function(name: str, args: list[_TypedValue], label: str) -> _TypedValue:
    if name == "len":
        if len(args) != 1 or args[0].family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: len() expects one string argument")
        return _numeric_value(len(str(args[0].value)), cpp_expr=f"{_wrap_cpp(args[0], 100)}.size()")
    if name == "substr":
        if len(args) != 3 or args[0].family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: substr() expects string, start, count")
        start = _coerce_expression_value(CONSTANT_KIND_UINT32, args[1], label)
        count = _coerce_expression_value(CONSTANT_KIND_UINT32, args[2], label)
        value = str(args[0].value)
        return _string_value(
            value[start : start + count],
            cpp_expr=f"{_wrap_cpp(args[0], 100)}.substr({_wrap_cpp(args[1], 0)}, {_wrap_cpp(args[2], 0)})",
        )
    if name == "starts_with":
        if len(args) != 2 or args[0].family != CONSTANT_KIND_STRING or args[1].family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: starts_with() expects two string arguments")
        return _bool_value(
            str(args[0].value).startswith(str(args[1].value)),
            cpp_expr=f"{_wrap_cpp(args[0], 100)}.starts_with({_wrap_cpp(args[1], 0)})",
        )
    raise ProtocyteError(f"{label}: unsupported function {name}()")


def _coerce_literal(kind: str, literal: str, label: str) -> object:
    family = _constant_family(kind)
    if family == CONSTANT_KIND_STRING:
        return literal
    if family == CONSTANT_KIND_BOOL:
        lowered = literal.lower()
        if lowered in {"true", "1"}:
            return True
        if lowered in {"false", "0"}:
            return False
        raise ProtocyteError(f"{label}: invalid bool literal {literal!r}")
    if kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
        try:
            value = float(literal)
        except ValueError as exc:
            raise ProtocyteError(f"{label}: invalid numeric literal {literal!r}") from exc
        if not math.isfinite(value):
            raise ProtocyteError(f"{label}: numeric literal must be finite")
        return value
    try:
        value = int(literal, 0)
    except ValueError as exc:
        raise ProtocyteError(f"{label}: invalid numeric literal {literal!r}") from exc
    return _coerce_integer(kind, value, label)


def _coerce_expression_value(kind: str, value: _TypedValue, label: str) -> object:
    family = _constant_family(kind)
    if family == CONSTANT_KIND_STRING:
        if value.family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: expression must evaluate to string")
        return str(value.value)
    if family == CONSTANT_KIND_BOOL:
        if value.family != CONSTANT_KIND_BOOL:
            raise ProtocyteError(f"{label}: expression must evaluate to bool")
        return bool(value.value)
    if value.family != "numeric":
        raise ProtocyteError(f"{label}: expression must evaluate to numeric")
    numeric_value = value.value
    if kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
        out = float(numeric_value)
        if not math.isfinite(out):
            raise ProtocyteError(f"{label}: numeric expression must be finite")
        return out
    if isinstance(numeric_value, float):
        if not numeric_value.is_integer():
            raise ProtocyteError(f"{label}: integer expression must evaluate to an integral value")
        numeric_value = int(numeric_value)
    return _coerce_integer(kind, int(numeric_value), label)


def _coerce_integer(kind: str, value: int, label: str) -> int:
    ranges = {
        CONSTANT_KIND_INT32: (-2**31, 2**31 - 1),
        CONSTANT_KIND_INT64: (-2**63, 2**63 - 1),
        CONSTANT_KIND_UINT32: (0, 2**32 - 1),
        CONSTANT_KIND_UINT64: (0, 2**64 - 1),
    }
    lower, upper = ranges[kind]
    if value < lower or value > upper:
        raise ProtocyteError(f"{label}: value {value} is out of range for {kind}")
    return value


def _cpp_constant_type(kind: str) -> str:
    return {
        CONSTANT_KIND_BOOL: "bool",
        CONSTANT_KIND_INT32: "::protocyte::i32",
        CONSTANT_KIND_INT64: "::protocyte::i64",
        CONSTANT_KIND_UINT32: "::protocyte::u32",
        CONSTANT_KIND_UINT64: "::protocyte::u64",
        CONSTANT_KIND_FLOAT: "::protocyte::f32",
        CONSTANT_KIND_DOUBLE: "::protocyte::f64",
        CONSTANT_KIND_STRING: "::std::string_view",
    }[kind]


def _cpp_constant_value(kind: str, value: object) -> str:
    if kind == CONSTANT_KIND_BOOL:
        return "true" if value else "false"
    if kind in {CONSTANT_KIND_INT32, CONSTANT_KIND_INT64}:
        return str(value)
    if kind == CONSTANT_KIND_UINT32:
        return f"{value}u"
    if kind == CONSTANT_KIND_UINT64:
        return f"{value}ull"
    if kind == CONSTANT_KIND_FLOAT:
        text = format(float(value), ".9g")
        if "e" not in text and "E" not in text and "." not in text:
            text += ".0"
        return text + "f"
    if kind == CONSTANT_KIND_DOUBLE:
        text = format(float(value), ".17g")
        if "e" not in text and "E" not in text and "." not in text:
            text += ".0"
        return text
    encoded = str(value).encode("utf-8")
    return f"{_cpp_string_literal(encoded)}, {len(encoded)}u"


def _inline_constant_cpp_expr(constant: ConstantModel) -> str:
    if constant.kind == CONSTANT_KIND_STRING:
        return f"::std::string_view {{{constant.cpp_value}}}"
    return constant.cpp_value


def _cpp_string_literal(value: bytes) -> str:
    parts: list[str] = []
    ascii_chunk: list[str] = []

    def flush_ascii() -> None:
        if ascii_chunk:
            parts.append('"' + "".join(ascii_chunk) + '"')
            ascii_chunk.clear()

    for byte in value:
        if byte == 0x5C:
            ascii_chunk.append("\\\\")
            continue
        if byte == 0x22:
            ascii_chunk.append('\\"')
            continue
        if byte == 0x0A:
            ascii_chunk.append("\\n")
            continue
        if byte == 0x0D:
            ascii_chunk.append("\\r")
            continue
        if byte == 0x09:
            ascii_chunk.append("\\t")
            continue
        if 32 <= byte < 127:
            ascii_chunk.append(chr(byte))
            continue
        flush_ascii()
        parts.append(f'"\\x{byte:02x}"')

    flush_ascii()
    if not parts:
        return '""'
    return "".join(parts)
