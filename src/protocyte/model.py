from __future__ import annotations

import ast
import math
import struct
import warnings
from dataclasses import dataclass, field
from typing import Callable, Iterable

from google.protobuf import (
    descriptor_pb2,
    descriptor_pool,
    message_factory,
    text_encoding,
)
from google.protobuf.message import DecodeError

from protocyte._deterministic_math import (
    DeterministicMathDomainError,
    DeterministicMathNonFiniteError,
    evaluate_pow as evaluate_deterministic_pow,
    evaluate_unary,
)
from protocyte.descriptor_set import validate_virtual_file_name
from protocyte.errors import ProtocyteError
from protocyte.extensions import CUSTOM_OPTION_EXTENDEES, is_custom_option_extension

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
CONSTANT_OPTION_NAME = "protocyte.constant"
PACKAGE_CONSTANT_OPTION_NAME = "protocyte.package_constant"
PROTOCYTE_OPTIONS_FILE_NAME = "protocyte/options.proto"
_PROTOCYTE_OPTION_NAMES = frozenset(
    {ARRAY_OPTION_NAME, CONSTANT_OPTION_NAME, PACKAGE_CONSTANT_OPTION_NAME}
)
_CUSTOM_OPTION_EXTENDEES = CUSTOM_OPTION_EXTENDEES
CONSTANT_KIND_BOOL = "bool"
CONSTANT_KIND_INT32 = "int32"
CONSTANT_KIND_INT64 = "int64"
CONSTANT_KIND_UINT32 = "uint32"
CONSTANT_KIND_UINT64 = "uint64"
CONSTANT_KIND_FLOAT = "float"
CONSTANT_KIND_DOUBLE = "double"
CONSTANT_KIND_STRING = "string"

_INTEGER_EXPRESSION_KINDS = frozenset(
    {
        CONSTANT_KIND_INT32,
        CONSTANT_KIND_UINT32,
        CONSTANT_KIND_INT64,
        CONSTANT_KIND_UINT64,
    }
)
_INTEGER_KIND_INFO = {
    CONSTANT_KIND_INT32: (32, True),
    CONSTANT_KIND_UINT32: (32, False),
    CONSTANT_KIND_INT64: (64, True),
    CONSTANT_KIND_UINT64: (64, False),
}
_NUMERIC_EXPRESSION_KINDS = _INTEGER_EXPRESSION_KINDS | frozenset(
    {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}
)
_SCALAR_CAST_KINDS = {
    "bool": CONSTANT_KIND_BOOL,
    "i32": CONSTANT_KIND_INT32,
    "u32": CONSTANT_KIND_UINT32,
    "i64": CONSTANT_KIND_INT64,
    "u64": CONSTANT_KIND_UINT64,
    "f32": CONSTANT_KIND_FLOAT,
    "f64": CONSTANT_KIND_DOUBLE,
    "str": CONSTANT_KIND_STRING,
}
_MAX_EXPRESSION_NESTING = 32
_MAX_CONSTANT_DEPENDENCY_DEPTH = 32

INTEGER_CONSTANT_KINDS = {
    FieldDescriptorProto.TYPE_INT32: CONSTANT_KIND_INT32,
    FieldDescriptorProto.TYPE_SINT32: CONSTANT_KIND_INT32,
    FieldDescriptorProto.TYPE_SFIXED32: CONSTANT_KIND_INT32,
    FieldDescriptorProto.TYPE_INT64: CONSTANT_KIND_INT64,
    FieldDescriptorProto.TYPE_SINT64: CONSTANT_KIND_INT64,
    FieldDescriptorProto.TYPE_SFIXED64: CONSTANT_KIND_INT64,
    FieldDescriptorProto.TYPE_UINT32: CONSTANT_KIND_UINT32,
    FieldDescriptorProto.TYPE_FIXED32: CONSTANT_KIND_UINT32,
    FieldDescriptorProto.TYPE_UINT64: CONSTANT_KIND_UINT64,
    FieldDescriptorProto.TYPE_FIXED64: CONSTANT_KIND_UINT64,
}

_CONSTANT_OPTION_VALUE_FIELDS = {
    "boolean": (CONSTANT_KIND_BOOL, False),
    "boolean_expr": (CONSTANT_KIND_BOOL, True),
    "i32": (CONSTANT_KIND_INT32, False),
    "i32_expr": (CONSTANT_KIND_INT32, True),
    "u32": (CONSTANT_KIND_UINT32, False),
    "u32_expr": (CONSTANT_KIND_UINT32, True),
    "i64": (CONSTANT_KIND_INT64, False),
    "i64_expr": (CONSTANT_KIND_INT64, True),
    "u64": (CONSTANT_KIND_UINT64, False),
    "u64_expr": (CONSTANT_KIND_UINT64, True),
    "f32": (CONSTANT_KIND_FLOAT, False),
    "f32_expr": (CONSTANT_KIND_FLOAT, True),
    "f64": (CONSTANT_KIND_DOUBLE, False),
    "f64_expr": (CONSTANT_KIND_DOUBLE, True),
    "str": (CONSTANT_KIND_STRING, False),
    "str_expr": (CONSTANT_KIND_STRING, True),
}

_PROTOCYTE_OPTION_MESSAGE_SCHEMA = (
    (
        "Constant",
        ("value",),
        (
            (
                "name",
                1,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                None,
            ),
            (
                "boolean",
                2,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_BOOL,
                "",
                0,
            ),
            (
                "boolean_expr",
                3,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "i32",
                4,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_INT32,
                "",
                0,
            ),
            (
                "i32_expr",
                5,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "u32",
                6,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_UINT32,
                "",
                0,
            ),
            (
                "u32_expr",
                7,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "i64",
                8,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_INT64,
                "",
                0,
            ),
            (
                "i64_expr",
                9,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "u64",
                10,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_UINT64,
                "",
                0,
            ),
            (
                "u64_expr",
                11,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "f32",
                12,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_FLOAT,
                "",
                0,
            ),
            (
                "f32_expr",
                13,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "f64",
                14,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_DOUBLE,
                "",
                0,
            ),
            (
                "f64_expr",
                15,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "str",
                16,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "str_expr",
                17,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
        ),
    ),
    (
        "ArrayOptions",
        ("bound",),
        (
            (
                "max",
                1,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_UINT32,
                "",
                0,
            ),
            (
                "expr",
                2,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_STRING,
                "",
                0,
            ),
            (
                "fixed",
                3,
                FieldDescriptorProto.LABEL_OPTIONAL,
                FieldDescriptorProto.TYPE_BOOL,
                "",
                None,
            ),
        ),
    ),
)

_PROTOCYTE_OPTION_EXTENSION_SCHEMA = (
    (
        "constant",
        50000,
        FieldDescriptorProto.LABEL_REPEATED,
        FieldDescriptorProto.TYPE_MESSAGE,
        ".protocyte.Constant",
        ".google.protobuf.MessageOptions",
    ),
    (
        "package_constant",
        50002,
        FieldDescriptorProto.LABEL_REPEATED,
        FieldDescriptorProto.TYPE_MESSAGE,
        ".protocyte.Constant",
        ".google.protobuf.FileOptions",
    ),
    (
        "array",
        50000,
        FieldDescriptorProto.LABEL_OPTIONAL,
        FieldDescriptorProto.TYPE_MESSAGE,
        ".protocyte.ArrayOptions",
        ".google.protobuf.FieldOptions",
    ),
)


@dataclass(slots=True)
class _RawConstantOption:
    name: str
    kind: str | None
    literal: object | None
    expr: str | None


@dataclass(slots=True)
class _CustomOptions:
    field_options_cls: type[object] | None = None
    file_options_cls: type[object] | None = None
    message_options_cls: type[object] | None = None
    array_extension: object | None = None
    constant_extension: object | None = None
    package_constant_extension: object | None = None

    def field_array(
        self,
        options: descriptor_pb2.FieldOptions,
        *,
        label: str,
    ) -> tuple[int | None, str | None, bool]:
        if self.field_options_cls is None or self.array_extension is None:
            return None, None, False
        parsed = self.field_options_cls()
        try:
            parsed.ParseFromString(options.SerializeToString())
        except DecodeError as exc:
            raise ProtocyteError(
                f"{label}: malformed {ARRAY_OPTION_NAME} option payload: {exc}"
            ) from exc
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
                fixed = bool(array_options.fixed)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProtocyteError(
                f"{label}: invalid {ARRAY_OPTION_NAME} option: {exc}"
            ) from exc
        return max_value, max_expr, fixed

    def message_constants(
        self,
        options: descriptor_pb2.MessageOptions,
        *,
        label: str,
    ) -> list[_RawConstantOption]:
        return self._constant_options(
            options,
            self.message_options_cls,
            self.constant_extension,
            label=label,
            option_name=CONSTANT_OPTION_NAME,
        )

    def file_constants(
        self,
        options: descriptor_pb2.FileOptions,
        *,
        label: str,
    ) -> list[_RawConstantOption]:
        return self._constant_options(
            options,
            self.file_options_cls,
            self.package_constant_extension,
            label=label,
            option_name=PACKAGE_CONSTANT_OPTION_NAME,
        )

    def _constant_options(
        self,
        options: object,
        options_cls: type[object] | None,
        extension: object | None,
        *,
        label: str,
        option_name: str,
    ) -> list[_RawConstantOption]:
        if options_cls is None or extension is None:
            return []
        parsed = options_cls()
        try:
            parsed.ParseFromString(options.SerializeToString())
        except DecodeError as exc:
            raise ProtocyteError(
                f"{label}: malformed {option_name} option payload: {exc}"
            ) from exc
        out: list[_RawConstantOption] = []
        try:
            for item in parsed.Extensions[extension]:
                value_field = item.WhichOneof("value")
                kind: str | None = None
                literal: object | None = None
                expr: str | None = None
                if value_field is not None:
                    kind_info = _CONSTANT_OPTION_VALUE_FIELDS.get(value_field)
                    if kind_info is None:
                        raise ProtocyteError(
                            f"unsupported typed constant value field {value_field!r}"
                        )
                    kind, is_expr = kind_info
                    value = getattr(item, value_field)
                    if is_expr:
                        expr = str(value)
                    else:
                        literal = value
                out.append(
                    _RawConstantOption(
                        name=str(item.name),
                        kind=kind,
                        literal=literal,
                        expr=expr,
                    )
                )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise ProtocyteError(
                f"{label}: invalid {option_name} option: {exc}"
            ) from exc
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
    full_name: str
    kind: str
    literal: object | None
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
    explicit_presence: bool = False
    required: bool = False
    default_cpp: str | None = None
    default_byte_size: int | None = None
    enum_closed: bool = False

    @property
    def has_explicit_presence(self) -> bool:
        return (
            self.explicit_presence
            or self.oneof_name is not None
            or self.kind == "message"
        )

    @property
    def array_enabled(self) -> bool:
        return self.array_max is not None or self.array_expr is not None

    @property
    def fixed_bytes(self) -> bool:
        return (
            self.kind == "bytes"
            and not self.repeated
            and self.array_enabled
            and self.array_fixed
        )

    @property
    def dynamic_bytes(self) -> bool:
        return (
            self.kind == "bytes"
            and not self.repeated
            and self.array_enabled
            and not self.array_fixed
        )

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
    constants: list[ConstantModel] = field(default_factory=list)
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
    cpp_precedence: int = 120
    numeric_kind: str | None = None


class _ExprParser:
    def __init__(
        self,
        text: str,
        resolve_name: Callable[[str], _TypedValue],
        label: str,
    ) -> None:
        self._tokens = _tokenize(text, label)
        self._index = 0
        self._resolve_name = resolve_name
        self._label = label
        self._evaluate_values = True
        self._nesting_depth = 0

    def parse(self) -> _TypedValue:
        try:
            value = self._parse_or()
            if self._peek()[0] != "EOF":
                raise ProtocyteError(
                    f"{self._label}: unexpected token {self._peek()[1]!r}"
                )
            return value
        except RecursionError as exc:
            raise ProtocyteError(
                f"{self._label}: expression evaluation exceeds safe recursion depth"
            ) from exc

    def _parse_with_evaluation(
        self, evaluate: bool, parser: Callable[[], _TypedValue]
    ) -> _TypedValue:
        previous = self._evaluate_values
        self._evaluate_values = evaluate
        try:
            return parser()
        finally:
            self._evaluate_values = previous

    def _parse_nested(self, parser: Callable[[], _TypedValue]) -> _TypedValue:
        if self._nesting_depth >= _MAX_EXPRESSION_NESTING:
            raise ProtocyteError(
                f"{self._label}: expression nesting exceeds maximum depth of "
                f"{_MAX_EXPRESSION_NESTING}"
            )
        self._nesting_depth += 1
        try:
            return parser()
        finally:
            self._nesting_depth -= 1

    def _parse_or(self) -> _TypedValue:
        value = self._parse_and()
        while self._match("||"):
            lhs_bool = _expect_bool(value, self._label)
            rhs = self._parse_with_evaluation(
                self._evaluate_values and not lhs_bool, self._parse_and
            )
            rhs_bool = _expect_bool(rhs, self._label)
            result = False if not self._evaluate_values else lhs_bool or rhs_bool
            value = _bool_value(
                result,
                cpp_expr=_binary_cpp(value, rhs, "||", 10),
                cpp_precedence=10,
            )
        return value

    def _parse_and(self) -> _TypedValue:
        value = self._parse_bitwise_or()
        while self._match("&&"):
            lhs_bool = _expect_bool(value, self._label)
            rhs = self._parse_with_evaluation(
                self._evaluate_values and lhs_bool, self._parse_bitwise_or
            )
            rhs_bool = _expect_bool(rhs, self._label)
            result = False if not self._evaluate_values else lhs_bool and rhs_bool
            value = _bool_value(
                result,
                cpp_expr=_binary_cpp(value, rhs, "&&", 20),
                cpp_precedence=20,
            )
        return value

    def _parse_bitwise_or(self) -> _TypedValue:
        value = self._parse_bitwise_xor()
        while self._match("|"):
            rhs = self._parse_bitwise_xor()
            value = _bitwise_binary(
                value,
                rhs,
                self._label,
                lambda lhs, rhs: lhs | rhs,
                symbol="|",
                precedence=30,
            )
        return value

    def _parse_bitwise_xor(self) -> _TypedValue:
        value = self._parse_bitwise_and()
        while self._match("^"):
            rhs = self._parse_bitwise_and()
            value = _bitwise_binary(
                value,
                rhs,
                self._label,
                lambda lhs, rhs: lhs ^ rhs,
                symbol="^",
                precedence=40,
            )
        return value

    def _parse_bitwise_and(self) -> _TypedValue:
        value = self._parse_equality()
        while self._match("&"):
            rhs = self._parse_equality()
            value = _bitwise_binary(
                value,
                rhs,
                self._label,
                lambda lhs, rhs: lhs & rhs,
                symbol="&",
                precedence=50,
            )
        return value

    def _parse_equality(self) -> _TypedValue:
        value = self._parse_compare()
        while True:
            if self._match("=="):
                rhs = self._parse_compare()
                value = _bool_value(
                    _compare_equal(value, rhs, self._label),
                    cpp_expr=_binary_cpp(value, rhs, "==", 60),
                    cpp_precedence=60,
                )
                continue
            if self._match("!="):
                rhs = self._parse_compare()
                value = _bool_value(
                    not _compare_equal(value, rhs, self._label),
                    cpp_expr=_binary_cpp(value, rhs, "!=", 60),
                    cpp_precedence=60,
                )
                continue
            return value

    def _parse_compare(self) -> _TypedValue:
        value = self._parse_shift()
        while True:
            if self._match("<"):
                rhs = self._parse_shift()
                value = _bool_value(
                    _numeric_compare(
                        value, rhs, self._label, lambda lhs, rhs: lhs < rhs
                    ),
                    cpp_expr=_binary_cpp(value, rhs, "<", 70),
                    cpp_precedence=70,
                )
                continue
            if self._match("<="):
                rhs = self._parse_shift()
                value = _bool_value(
                    _numeric_compare(
                        value, rhs, self._label, lambda lhs, rhs: lhs <= rhs
                    ),
                    cpp_expr=_binary_cpp(value, rhs, "<=", 70),
                    cpp_precedence=70,
                )
                continue
            if self._match(">"):
                rhs = self._parse_shift()
                value = _bool_value(
                    _numeric_compare(
                        value, rhs, self._label, lambda lhs, rhs: lhs > rhs
                    ),
                    cpp_expr=_binary_cpp(value, rhs, ">", 70),
                    cpp_precedence=70,
                )
                continue
            if self._match(">="):
                rhs = self._parse_shift()
                value = _bool_value(
                    _numeric_compare(
                        value, rhs, self._label, lambda lhs, rhs: lhs >= rhs
                    ),
                    cpp_expr=_binary_cpp(value, rhs, ">=", 70),
                    cpp_precedence=70,
                )
                continue
            return value

    def _parse_shift(self) -> _TypedValue:
        value = self._parse_add()
        while True:
            if self._match("<<"):
                rhs = self._parse_add()
                value = _shift_value(value, rhs, self._label, left=True)
                continue
            if self._match(">>"):
                rhs = self._parse_add()
                value = _shift_value(value, rhs, self._label, left=False)
                continue
            return value

    def _parse_add(self) -> _TypedValue:
        value = self._parse_mul()
        while True:
            if self._match("+"):
                rhs = self._parse_mul()
                if (
                    value.family == CONSTANT_KIND_STRING
                    or rhs.family == CONSTANT_KIND_STRING
                ):
                    if (
                        value.family != CONSTANT_KIND_STRING
                        or rhs.family != CONSTANT_KIND_STRING
                    ):
                        raise ProtocyteError(
                            f"{self._label}: '+' requires both operands to be numeric or string"
                        )
                    value = _string_value(
                        str(value.value) + str(rhs.value),
                        cpp_expr=_binary_cpp(value, rhs, "+", 90),
                        cpp_precedence=90,
                    )
                else:
                    value = _numeric_binary(
                        value,
                        rhs,
                        self._label,
                        lambda lhs, rhs: lhs + rhs,
                        symbol="+",
                        precedence=90,
                    )
                continue
            if self._match("-"):
                rhs = self._parse_mul()
                value = _numeric_binary(
                    value,
                    rhs,
                    self._label,
                    lambda lhs, rhs: lhs - rhs,
                    symbol="-",
                    precedence=90,
                )
                continue
            return value

    def _parse_mul(self) -> _TypedValue:
        value = self._parse_unary()
        while True:
            if self._match("*"):
                rhs = self._parse_unary()
                value = _numeric_binary(
                    value,
                    rhs,
                    self._label,
                    lambda lhs, rhs: lhs * rhs,
                    symbol="*",
                    precedence=100,
                )
                continue
            if self._match("/"):
                rhs = self._parse_unary()
                lhs_value, rhs_value, result_kind = _numeric_operands(
                    value, rhs, self._label
                )
                if not self._evaluate_values:
                    value = _numeric_value(
                        0.0
                        if result_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}
                        else 0,
                        cpp_expr=_binary_cpp(value, rhs, "/", 100),
                        cpp_precedence=100,
                        numeric_kind=result_kind,
                    )
                elif rhs_value == 0:
                    raise ProtocyteError(f"{self._label}: division by zero")
                elif result_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
                    value = _numeric_value(
                        lhs_value / rhs_value,
                        cpp_expr=_binary_cpp(value, rhs, "/", 100),
                        cpp_precedence=100,
                        numeric_kind=result_kind,
                    )
                else:
                    left_integer = int(lhs_value)
                    right_integer = int(rhs_value)
                    _, signed = _INTEGER_KIND_INFO[result_kind]
                    if signed and _signed_division_overflows(
                        left_integer, right_integer, result_kind
                    ):
                        raise ProtocyteError(
                            f"{self._label}: integer result is out of range for {result_kind}"
                        )
                    result = (
                        _truncating_integer_divide(left_integer, right_integer)
                        if signed
                        else left_integer // right_integer
                    )
                    value = _numeric_value(
                        _normalize_numeric_result(result, result_kind, self._label),
                        cpp_expr=_binary_cpp(value, rhs, "/", 100),
                        cpp_precedence=100,
                        numeric_kind=result_kind,
                    )
                continue
            if self._match("%"):
                rhs = self._parse_unary()
                lhs_value, rhs_value, result_kind = _numeric_operands(
                    value, rhs, self._label
                )
                if result_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
                    raise ProtocyteError(
                        f"{self._label}: '%' only supports integer operands"
                    )
                if not self._evaluate_values:
                    value = _numeric_value(
                        0,
                        cpp_expr=_binary_cpp(value, rhs, "%", 100),
                        cpp_precedence=100,
                        numeric_kind=result_kind,
                    )
                    continue
                if rhs_value == 0:
                    raise ProtocyteError(f"{self._label}: modulo by zero")
                left_integer = int(lhs_value)
                right_integer = int(rhs_value)
                _, signed = _INTEGER_KIND_INFO[result_kind]
                if signed and _signed_division_overflows(
                    left_integer, right_integer, result_kind
                ):
                    raise ProtocyteError(
                        f"{self._label}: integer result is out of range for {result_kind}"
                    )
                result = (
                    left_integer
                    - _truncating_integer_divide(left_integer, right_integer)
                    * right_integer
                    if signed
                    else left_integer % right_integer
                )
                value = _numeric_value(
                    _normalize_numeric_result(result, result_kind, self._label),
                    cpp_expr=_binary_cpp(value, rhs, "%", 100),
                    cpp_precedence=100,
                    numeric_kind=result_kind,
                )
                continue
            return value

    def _parse_unary(self) -> _TypedValue:
        if self._match("!"):
            value = self._parse_nested(self._parse_unary)
            return _bool_value(
                not _expect_bool(value, self._label),
                cpp_expr="!" + _wrap_cpp(value, 110),
                cpp_precedence=110,
            )
        if self._match("~"):
            value = self._parse_nested(self._parse_unary)
            return _bitwise_complement(value, self._label)
        if self._match("+"):
            value = self._parse_nested(self._parse_unary)
            result = _expect_numeric(value, self._label)
            numeric_kind = _typed_numeric_kind(value, self._label)
            result = _normalize_numeric_result(result, numeric_kind, self._label)
            return _numeric_value(
                result,
                cpp_expr="+" + _wrap_cpp(value, 110),
                cpp_precedence=110,
                numeric_kind=numeric_kind,
            )
        if self._match("-"):
            value = self._parse_nested(self._parse_unary)
            operand = _expect_numeric(value, self._label)
            numeric_kind = _typed_numeric_kind(value, self._label)
            result = _normalize_numeric_result(-operand, numeric_kind, self._label)
            return _numeric_value(
                result,
                cpp_expr="-" + _wrap_cpp(value, 110),
                cpp_precedence=110,
                numeric_kind=numeric_kind,
            )
        return self._parse_primary()

    def _parse_primary(self) -> _TypedValue:
        token_type, token_value = self._peek()
        if token_type == "NUMBER":
            self._index += 1
            numeric = _parse_number_token(token_value, self._label)
            numeric_kind = (
                _literal_integer_kind(
                    numeric,
                    hexadecimal=token_value.lower().startswith("0x"),
                )
                if isinstance(numeric, int)
                else CONSTANT_KIND_DOUBLE
            )
            if isinstance(numeric, int) and numeric_kind is None:
                raise ProtocyteError(
                    f"{self._label}: integer literal {token_value!r} is outside "
                    "the standard C++ 64-bit range"
                )
            result = _numeric_value(
                numeric,
                cpp_expr=token_value,
                numeric_kind=numeric_kind,
            )
            return result if self._evaluate_values else _type_only_value(result)
        if token_type == "STRING":
            self._index += 1
            result = _string_value(
                _parse_string_token(token_value, self._label), cpp_expr=token_value
            )
            return result if self._evaluate_values else _type_only_value(result)
        if token_type == "IDENT":
            self._index += 1
            if token_value == "true":
                result = _bool_value(True, cpp_expr="true")
                return result if self._evaluate_values else _type_only_value(result)
            if token_value == "false":
                return _bool_value(False, cpp_expr="false")
            if self._match("("):
                args: list[_TypedValue] = []
                if not self._match(")"):
                    while True:
                        args.append(self._parse_nested(self._parse_or))
                        if self._match(")"):
                            break
                        self._expect(",")
                return _evaluate_function(
                    token_value, args, self._label, evaluate=self._evaluate_values
                )
            result = self._resolve_name(token_value)
            return result if self._evaluate_values else _type_only_value(result)
        if self._match("("):
            value = self._parse_nested(self._parse_or)
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
            raise ProtocyteError(
                f"{self._label}: expected {token!r}, got {self._peek()[1]!r}"
            )


def build_model(request: descriptor_pb2.FileDescriptorSet | object) -> DescriptorModel:
    """Build a resolved model from a CodeGeneratorRequest-like object."""
    files_by_name = _index_request_files(request.proto_file)
    file_to_generate = list(request.file_to_generate)
    custom_options = _custom_options(request.proto_file)

    missing = [name for name in file_to_generate if name not in files_by_name]
    if missing:
        raise ProtocyteError(
            f"protoc request is missing file descriptors for: {', '.join(missing)}"
        )

    for name in file_to_generate:
        validate_virtual_file_name(name)
        file = files_by_name[name]
        _reject_unsupported_file_features(file, f"target file {name}")

    selected_files = set(file_to_generate)
    reachable_files = _validate_import_graph(files_by_name, file_to_generate)
    for name in reachable_files:
        _validate_extension_declarations(
            files_by_name[name], selected_for_generation=name in selected_files
        )

    files: dict[str, FileModel] = {}
    messages: dict[str, MessageModel] = {}
    enums: dict[str, EnumModel] = {}

    for file in files_by_name.values():
        files[file.name] = FileModel(
            name=file.name,
            package=file.package,
            syntax=_file_syntax(file),
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
        file_model.constants = _build_file_constants(file_model, custom_options)
        _validate_package_constant_collisions(file_model)

    _validate_enum_value_collisions(enums.values())
    _validate_type_cpp_name_collisions(files)

    for file_model in files.values():
        for message in _walk_messages(file_model.messages):
            _fill_message_details(message, files, messages, enums, custom_options)

    _validate_package_constant_namespace(files)
    _resolve_constants_and_arrays(files, messages)
    _compute_file_dependencies(file_to_generate, files)
    _mark_recursive_boxes(messages)

    return DescriptorModel(
        files=files,
        file_to_generate=file_to_generate,
        messages=messages,
        enums=enums,
    )


def _index_request_files(
    proto_files: Iterable[descriptor_pb2.FileDescriptorProto],
) -> dict[str, descriptor_pb2.FileDescriptorProto]:
    files: dict[str, descriptor_pb2.FileDescriptorProto] = {}
    for file in proto_files:
        validate_virtual_file_name(file.name)
        if file.name in files:
            raise ProtocyteError(f"duplicate descriptor file name: {file.name}")
        files[file.name] = file
    return files


def _validate_import_graph(
    files: dict[str, descriptor_pb2.FileDescriptorProto],
    roots: Iterable[str],
) -> set[str]:
    stack = list(roots)
    seen: set[str] = set()
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        file = files[name]
        for dependency in file.dependency:
            validate_virtual_file_name(dependency)
            if dependency == descriptor_pb2.DESCRIPTOR.name and dependency not in files:
                continue
            if dependency not in files:
                raise ProtocyteError(f"{name} imports missing descriptor {dependency}")
            stack.append(dependency)
    return seen


def _custom_options(
    proto_files: Iterable[descriptor_pb2.FileDescriptorProto],
) -> _CustomOptions:
    proto_files = list(proto_files)
    _validate_protocyte_option_extension_sources(proto_files)
    protocyte_options_file = next(
        (file for file in proto_files if file.name == PROTOCYTE_OPTIONS_FILE_NAME),
        None,
    )
    if protocyte_options_file is not None:
        _validate_protocyte_options_schema(protocyte_options_file)

    pool = descriptor_pool.DescriptorPool()
    try:
        pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    except Exception:
        if protocyte_options_file is not None:
            _raise_obsolete_protocyte_options_schema()
        return _CustomOptions()

    pending = [
        file for file in proto_files if file.name != descriptor_pb2.DESCRIPTOR.name
    ]
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
        file_options_desc = pool.FindMessageTypeByName("google.protobuf.FileOptions")
        field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
        message_options_desc = pool.FindMessageTypeByName(
            "google.protobuf.MessageOptions"
        )
        file_options_cls = message_factory.GetMessageClass(file_options_desc)
        field_options_cls = message_factory.GetMessageClass(field_options_desc)
        message_options_cls = message_factory.GetMessageClass(message_options_desc)
    except Exception:
        if protocyte_options_file is not None:
            _raise_obsolete_protocyte_options_schema()
        return _CustomOptions()

    custom_options = _CustomOptions(
        file_options_cls=file_options_cls,
        field_options_cls=field_options_cls,
        message_options_cls=message_options_cls,
        array_extension=_find_extension(pool, ARRAY_OPTION_NAME),
        constant_extension=_find_extension(pool, CONSTANT_OPTION_NAME),
        package_constant_extension=_find_extension(pool, PACKAGE_CONSTANT_OPTION_NAME),
    )
    if protocyte_options_file is not None and (
        custom_options.array_extension is None
        or custom_options.constant_extension is None
        or custom_options.package_constant_extension is None
    ):
        _raise_obsolete_protocyte_options_schema()
    _validate_loaded_protocyte_option_extensions(custom_options)
    return custom_options


def _validate_protocyte_option_extension_sources(
    proto_files: Iterable[descriptor_pb2.FileDescriptorProto],
) -> None:
    for file in proto_files:
        for extension in file.extension:
            extension_name = _extension_full_name(file, None, extension)
            if (
                extension_name in _PROTOCYTE_OPTION_NAMES
                and file.name != PROTOCYTE_OPTIONS_FILE_NAME
            ):
                raise ProtocyteError(
                    f"{file.name}: Protocyte option extension {extension_name} must be declared "
                    f"by {PROTOCYTE_OPTIONS_FILE_NAME}"
                )


def _validate_loaded_protocyte_option_extensions(
    custom_options: _CustomOptions,
) -> None:
    for extension_name, extension in (
        (ARRAY_OPTION_NAME, custom_options.array_extension),
        (CONSTANT_OPTION_NAME, custom_options.constant_extension),
        (PACKAGE_CONSTANT_OPTION_NAME, custom_options.package_constant_extension),
    ):
        if extension is None:
            continue
        source_name = extension.file.name
        if source_name != PROTOCYTE_OPTIONS_FILE_NAME:
            raise ProtocyteError(
                f"{source_name}: Protocyte option extension {extension_name} must be declared "
                f"by {PROTOCYTE_OPTIONS_FILE_NAME}"
            )


def _validate_protocyte_options_schema(
    file: descriptor_pb2.FileDescriptorProto,
) -> None:
    message_schema = tuple(
        (
            message.name,
            tuple(oneof.name for oneof in message.oneof_decl),
            tuple(_option_field_schema(field) for field in message.field),
        )
        for message in file.message_type
    )
    extension_schema = tuple(
        _option_extension_schema(extension) for extension in file.extension
    )
    if (
        file.package != "protocyte"
        or file.syntax != "proto3"
        or tuple(file.dependency) != (descriptor_pb2.DESCRIPTOR.name,)
        or file.public_dependency
        or file.weak_dependency
        or message_schema != _PROTOCYTE_OPTION_MESSAGE_SCHEMA
        or extension_schema != _PROTOCYTE_OPTION_EXTENSION_SCHEMA
        or file.enum_type
        or file.service
        or any(
            message.nested_type
            or message.enum_type
            or message.extension
            or message.extension_range
            or message.reserved_range
            or message.reserved_name
            for message in file.message_type
        )
    ):
        _raise_obsolete_protocyte_options_schema()


def _option_field_schema(
    field: descriptor_pb2.FieldDescriptorProto,
) -> tuple[object, ...]:
    oneof_index = field.oneof_index if field.HasField("oneof_index") else None
    return (
        field.name,
        field.number,
        field.label,
        field.type,
        field.type_name,
        oneof_index,
    )


def _option_extension_schema(
    extension: descriptor_pb2.FieldDescriptorProto,
) -> tuple[object, ...]:
    return (
        extension.name,
        extension.number,
        extension.label,
        extension.type,
        extension.type_name,
        extension.extendee,
    )


def _raise_obsolete_protocyte_options_schema() -> None:
    raise ProtocyteError(
        "protocyte/options.proto uses an obsolete or unsupported Protocyte options schema; "
        "regenerate descriptors with the current Protocyte options.proto"
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


def _file_syntax(file: descriptor_pb2.FileDescriptorProto) -> str:
    return file.syntax or "proto2"


def _reject_unsupported_file_features(
    file: descriptor_pb2.FileDescriptorProto, label: str
) -> None:
    if file.edition:
        raise ProtocyteError(f"{label}: protobuf Editions are not supported in v1")


def _is_custom_option_extension(field: descriptor_pb2.FieldDescriptorProto) -> bool:
    return is_custom_option_extension(field)


def _validate_extension_declarations(
    file: descriptor_pb2.FileDescriptorProto,
    *,
    selected_for_generation: bool,
) -> None:
    syntax = _file_syntax(file)

    def validate_extension(
        extension: descriptor_pb2.FieldDescriptorProto,
        path: str | None,
    ) -> None:
        if _is_custom_option_extension(extension):
            return
        if syntax == "proto3":
            raise ProtocyteError(
                f"{file.name}: extension {_extension_full_name(file, path, extension)} "
                f"extends unsupported proto3 target {extension.extendee}"
            )
        if selected_for_generation and path is not None:
            raise ProtocyteError(
                f"{file.name}: message {proto_full_name(file, path)}: extension declarations are not supported"
            )

    def validate_message_extensions(
        message: descriptor_pb2.DescriptorProto, path: str
    ) -> None:
        for extension in message.extension:
            validate_extension(extension, path)
        for nested in message.nested_type:
            validate_message_extensions(nested, f"{path}.{nested.name}")

    for extension in file.extension:
        validate_extension(extension, None)
    for message in file.message_type:
        validate_message_extensions(message, message.name)


def _extension_full_name(
    file: descriptor_pb2.FileDescriptorProto,
    path: str | None,
    extension: descriptor_pb2.FieldDescriptorProto,
) -> str:
    extension_path = f"{path}.{extension.name}" if path is not None else extension.name
    return proto_full_name(file, extension_path)


def _build_enum(
    file: descriptor_pb2.FileDescriptorProto,
    enum: descriptor_pb2.EnumDescriptorProto,
    parent: MessageModel | None,
    path: str,
) -> EnumModel:
    cpp_prefix = f"{parent.cpp_name}_" if parent else ""
    values = [
        EnumValueModel(
            name=value.name, cpp_name=cpp_identifier(value.name), number=value.number
        )
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

    oneof_fields: dict[int, OneofModel] = {}
    for index, oneof in enumerate(message.descriptor.oneof_decl):
        oneof_fields[index] = OneofModel(
            name=oneof.name,
            cpp_name=cpp_pascal_identifier(oneof.name),
        )

    for field_proto in message.descriptor.field:
        field_model = _build_field(
            message,
            files[message.file_name],
            field_proto,
            messages,
            enums,
            custom_options,
        )
        message.fields.append(field_model)
        if field_model.oneof_index is not None and field_model.oneof_name is not None:
            oneof_fields[field_model.oneof_index].fields.append(field_model)

    message.oneofs = [
        oneof for _, oneof in sorted(oneof_fields.items()) if oneof.fields
    ]
    _validate_oneof_collisions(message)
    _validate_nested_alias_collisions(message)
    _validate_constant_collisions(message)
    _validate_field_collisions(message)


def _build_file_constants(
    file_model: FileModel, custom_options: _CustomOptions
) -> list[ConstantModel]:
    owner = file_model.package or file_model.name
    return _build_raw_constants(
        owner,
        custom_options.file_constants(file_model.descriptor.options, label=owner),
    )


def _build_constants(
    message: MessageModel, custom_options: _CustomOptions
) -> list[ConstantModel]:
    return _build_raw_constants(
        message.full_name,
        custom_options.message_constants(
            message.descriptor.options, label=message.full_name
        ),
    )


def _build_raw_constants(
    owner: str, raw_constants: list[_RawConstantOption]
) -> list[ConstantModel]:
    constants: list[ConstantModel] = []
    for raw in raw_constants:
        if not raw.name:
            raise ProtocyteError(f"{owner}: constant name must not be empty")
        if raw.kind is None or (raw.literal is None) == (raw.expr is None):
            raise ProtocyteError(
                f"{owner}.{raw.name}: exactly one typed constant value must be set"
            )
        constants.append(
            ConstantModel(
                name=raw.name,
                cpp_name=cpp_identifier(raw.name),
                full_name=f"{owner}.{raw.name}" if owner else raw.name,
                kind=raw.kind,
                literal=raw.literal,
                expr=raw.expr,
            )
        )
    return constants


def _validate_constant_collisions(message: MessageModel) -> None:
    seen_names: set[str] = set()
    seen_cpp_names: set[str] = set()

    for constant in message.constants:
        if constant.name in seen_names:
            raise ProtocyteError(
                f"{message.full_name}.{constant.name}: constant cannot be redefined"
            )
        seen_names.add(constant.name)
        if not constant.cpp_name or constant.cpp_name == "_":
            raise ProtocyteError(
                f"{message.full_name}.{constant.name}: constant name is not a valid C++ identifier"
            )
        if constant.cpp_name in seen_cpp_names:
            raise ProtocyteError(
                f"{message.full_name}.{constant.name}: constant collides after C++ identifier normalization"
            )
        seen_cpp_names.add(constant.cpp_name)


def _validate_package_constant_collisions(file_model: FileModel) -> None:
    seen_names: set[str] = set()
    seen_cpp_names: set[str] = set()
    for constant in file_model.constants:
        if constant.name in seen_names:
            raise ProtocyteError(f"{constant.full_name}: constant cannot be redefined")
        seen_names.add(constant.name)
        if not constant.cpp_name or constant.cpp_name == "_":
            raise ProtocyteError(
                f"{constant.full_name}: constant name is not a valid C++ identifier"
            )
        if constant.cpp_name in seen_cpp_names:
            raise ProtocyteError(
                f"{constant.full_name}: constant collides after C++ identifier normalization"
            )
        seen_cpp_names.add(constant.cpp_name)


def _validate_package_constant_namespace(files: dict[str, FileModel]) -> None:
    top_level_cpp_names: dict[tuple[str, ...], set[str]] = {}
    for file_model in files.values():
        package_key = _cpp_package_key(file_model.package)
        reserved = top_level_cpp_names.setdefault(package_key, {"protocyte_reflection"})
        reserved.update(_file_type_cpp_names(file_model))

    seen_names: dict[tuple[str, ...], set[str]] = {}
    seen_cpp_names: dict[tuple[str, ...], set[str]] = {}
    for file_model in files.values():
        package_key = _cpp_package_key(file_model.package)
        names = seen_names.setdefault(package_key, set())
        cpp_names = seen_cpp_names.setdefault(package_key, set())
        reserved = top_level_cpp_names[package_key]
        for constant in file_model.constants:
            if constant.name in names:
                raise ProtocyteError(
                    f"{constant.full_name}: constant cannot be redefined"
                )
            names.add(constant.name)
            if constant.cpp_name in cpp_names:
                raise ProtocyteError(
                    f"{constant.full_name}: constant collides after C++ identifier normalization"
                )
            if constant.cpp_name in reserved:
                raise ProtocyteError(
                    f"{constant.full_name}: constant collides with generated API"
                )
            cpp_names.add(constant.cpp_name)


def _validate_enum_value_collisions(enums: Iterable[EnumModel]) -> None:
    for enum in enums:
        seen_cpp_names: dict[str, str] = {}
        for value in enum.values:
            if not value.cpp_name or value.cpp_name == "_":
                raise ProtocyteError(
                    f"{enum.full_name}.{value.name}: enum value name is not a valid C++ identifier"
                )
            if value.cpp_name in seen_cpp_names:
                first = seen_cpp_names[value.cpp_name]
                raise ProtocyteError(
                    f"{enum.full_name}.{value.name}: enum value collides with {first!r} after C++ identifier normalization"
                )
            seen_cpp_names[value.cpp_name] = value.name


def _validate_type_cpp_name_collisions(files: dict[str, FileModel]) -> None:
    seen_cpp_names: dict[tuple[str, ...], dict[str, str]] = {}
    for file_model in files.values():
        package_names = seen_cpp_names.setdefault(
            _cpp_package_key(file_model.package), {}
        )
        for full_name, cpp_name in _file_type_cpp_items(file_model):
            _reserve_type_cpp_name(package_names, full_name, cpp_name)


def _file_type_cpp_names(file_model: FileModel) -> set[str]:
    return {cpp_name for _, cpp_name in _file_type_cpp_items(file_model)}


def _file_type_cpp_items(file_model: FileModel) -> Iterable[tuple[str, str]]:
    for enum in file_model.enums:
        yield enum.full_name, enum.cpp_name
    for message in _walk_messages(file_model.messages):
        if not message.is_map_entry:
            yield message.full_name, message.cpp_name
        for enum in message.nested_enums:
            yield enum.full_name, enum.cpp_name


def _reserve_type_cpp_name(
    seen_cpp_names: dict[str, str], full_name: str, cpp_name: str
) -> None:
    if not cpp_name or cpp_name == "_":
        raise ProtocyteError(f"{full_name}: type name is not a valid C++ identifier")
    if cpp_name in seen_cpp_names:
        first = seen_cpp_names[cpp_name]
        raise ProtocyteError(
            f"{full_name}: type collides with {first!r} after C++ identifier normalization"
        )
    seen_cpp_names[cpp_name] = full_name


def _validate_nested_alias_collisions(message: MessageModel) -> None:
    seen_cpp_names: dict[str, str] = {}
    for name, cpp_name in _nested_alias_cpp_items(message):
        if not cpp_name or cpp_name == "_":
            raise ProtocyteError(
                f"{message.full_name}.{name}: nested type alias is not a valid C++ identifier"
            )
        if cpp_name in seen_cpp_names:
            first = seen_cpp_names[cpp_name]
            raise ProtocyteError(
                f"{message.full_name}.{name}: nested type alias collides with {first!r} after C++ identifier normalization"
            )
        seen_cpp_names[cpp_name] = name


def _validate_oneof_collisions(message: MessageModel) -> None:
    if message.is_map_entry:
        return
    seen_cpp_names: dict[str, str] = {}

    for oneof in message.oneofs:
        lower = cpp_identifier(oneof.name)
        if not lower or lower == "_":
            raise ProtocyteError(
                f"{message.full_name}.{oneof.name}: oneof name is not a valid C++ identifier"
            )
        if lower in seen_cpp_names:
            first = seen_cpp_names[lower]
            raise ProtocyteError(
                f"{message.full_name}.{oneof.name}: oneof collides with {first!r} after C++ identifier normalization"
            )
        seen_cpp_names[lower] = oneof.name


def _nested_alias_cpp_items(message: MessageModel) -> Iterable[tuple[str, str]]:
    for enum in message.nested_enums:
        yield enum.name, cpp_identifier(enum.name)
    for nested in message.nested_messages:
        if not nested.is_map_entry:
            yield nested.name, cpp_identifier(nested.name)


def _validate_field_collisions(message: MessageModel) -> None:
    if message.is_map_entry:
        return
    seen_cpp_names: dict[str, str] = {}

    for field_model in message.fields:
        if not field_model.cpp_name or field_model.cpp_name == "_":
            raise ProtocyteError(
                f"{message.full_name}.{field_model.name}: field name is not a valid C++ identifier"
            )
        if field_model.cpp_name in seen_cpp_names:
            first = seen_cpp_names[field_model.cpp_name]
            raise ProtocyteError(
                f"{message.full_name}.{field_model.name}: field collides with {first!r} after C++ identifier normalization"
            )
        seen_cpp_names[field_model.cpp_name] = field_model.name


def _cpp_package_key(package: str) -> tuple[str, ...]:
    if not package:
        return ()
    return tuple(cpp_identifier(part) for part in package.split("."))


def _build_field(
    owner: MessageModel,
    file_model: FileModel,
    proto: descriptor_pb2.FieldDescriptorProto,
    messages: dict[str, MessageModel],
    enums: dict[str, EnumModel],
    custom_options: _CustomOptions,
) -> FieldModel:
    if proto.extendee:
        raise ProtocyteError(
            f"{owner.full_name}.{proto.name}: extension fields are not supported for codec generation"
        )
    if proto.type == FieldDescriptorProto.TYPE_GROUP:
        raise ProtocyteError(
            f"{owner.full_name}.{proto.name}: groups are not supported"
        )

    oneof_index = proto.oneof_index if proto.HasField("oneof_index") else None
    oneof_name = None
    if oneof_index is not None:
        oneof_count = len(owner.descriptor.oneof_decl)
        if oneof_index < 0 or oneof_index >= oneof_count:
            raise ProtocyteError(
                f"{owner.full_name}.{proto.name}: oneof_index {oneof_index} is outside "
                f"the message's {oneof_count} oneof declaration(s)"
            )
        if not proto.proto3_optional:
            oneof_name = owner.descriptor.oneof_decl[oneof_index].name

    repeated = proto.label == FieldDescriptorProto.LABEL_REPEATED
    required = proto.label == FieldDescriptorProto.LABEL_REQUIRED
    explicit_presence = (
        proto.proto3_optional
        or required
        or (
            file_model.syntax == "proto2"
            and proto.label == FieldDescriptorProto.LABEL_OPTIONAL
            and oneof_index is None
        )
    )
    packed = _is_packed(proto, file_model.syntax)
    kind = "scalar"
    cpp_type = SCALAR_CPP_TYPES.get(proto.type, "")
    message_type = None
    enum_type = None
    map_key = None
    map_value = None
    type_name = strip_type_name(proto.type_name)
    array_max, array_expr, array_fixed = custom_options.field_array(
        proto.options, label=f"{owner.full_name}.{proto.name}"
    )

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
            map_key = _build_field(
                message_type, file_model, key_proto, messages, enums, custom_options
            )
            map_value = _build_field(
                message_type, file_model, value_proto, messages, enums, custom_options
            )
            cpp_type = f"typename Config::template Map<{map_key.cpp_type}, {map_value.cpp_type}>"
        else:
            kind = "message"
            cpp_type = ""
    elif proto.type not in SCALAR_CPP_TYPES:
        raise ProtocyteError(
            f"{owner.full_name}.{proto.name}: unsupported field type {proto.type}"
        )

    default_cpp = _field_default_cpp(
        file_model.syntax, owner.full_name, proto, kind, enum_type
    )
    default_byte_size = _field_default_byte_size(owner.full_name, proto, kind)

    if array_fixed and array_max is None and array_expr is None:
        raise ProtocyteError(
            f"{owner.full_name}.{proto.name}: protocyte.array.fixed requires protocyte.array.max or protocyte.array.expr"
        )
    if array_max is not None and array_expr is not None:
        raise ProtocyteError(
            f"{owner.full_name}.{proto.name}: protocyte.array requires exactly one of max or expr"
        )
    if array_max is not None or array_expr is not None:
        if kind == "map":
            raise ProtocyteError(
                f"{owner.full_name}.{proto.name}: protocyte.array is not supported on map fields"
            )
        if kind != "bytes" and not repeated:
            raise ProtocyteError(
                f"{owner.full_name}.{proto.name}: protocyte.array is only supported on bytes or repeated fields"
            )
        if array_max is not None and array_max <= 0:
            raise ProtocyteError(
                f"{owner.full_name}.{proto.name}: protocyte.array.max must be greater than zero"
            )
        if array_expr is not None and not array_expr.strip():
            raise ProtocyteError(
                f"{owner.full_name}.{proto.name}: protocyte.array.expr must not be empty"
            )
        if array_max is not None and default_byte_size is not None:
            _validate_array_default_byte_size(
                owner.full_name, proto.name, default_byte_size, array_max, array_fixed
            )

    return FieldModel(
        name=proto.name,
        cpp_name=cpp_identifier(proto.name),
        number=proto.number,
        proto_type=proto.type,
        label=proto.label,
        file_name=owner.file_name,
        repeated=repeated,
        proto3_optional=explicit_presence,
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
        explicit_presence=explicit_presence,
        required=required,
        default_cpp=default_cpp,
        default_byte_size=default_byte_size,
        enum_closed=kind == "enum" and file_model.syntax == "proto2",
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


def _field_default_cpp(
    file_syntax: str,
    owner_full_name: str,
    proto: descriptor_pb2.FieldDescriptorProto,
    kind: str,
    enum_type: EnumModel | None,
) -> str | None:
    if not proto.HasField("default_value"):
        if (
            file_syntax == "proto2"
            and kind == "enum"
            and enum_type is not None
            and enum_type.values
            and proto.label != FieldDescriptorProto.LABEL_REPEATED
        ):
            return str(enum_type.values[0].number)
        return None
    if file_syntax == "proto3":
        raise ProtocyteError(
            f"{owner_full_name}.{proto.name}: explicit default values are not allowed in proto3"
        )
    if proto.label == FieldDescriptorProto.LABEL_REPEATED:
        raise ProtocyteError(
            f"{owner_full_name}.{proto.name}: repeated fields cannot have default values"
        )
    if kind in {"message", "map"}:
        raise ProtocyteError(
            f"{owner_full_name}.{proto.name}: message fields cannot have default values"
        )
    value = proto.default_value
    if kind == "enum":
        if enum_type is None:
            return None
        for enum_value in enum_type.values:
            if enum_value.name == value:
                return str(enum_value.number)
        raise ProtocyteError(
            f"{owner_full_name}.{proto.name}: unknown enum default value {value!r}"
        )
    if kind == "string":
        return f"::protocyte::StringView {{{_cpp_constant_value(CONSTANT_KIND_STRING, value)}}}"
    if kind == "bytes":
        encoded = _decode_bytes_default(owner_full_name, proto)
        return f"::protocyte::Span<const ::protocyte::u8> {{reinterpret_cast<const ::protocyte::u8*>({_cpp_string_literal(encoded)}), {len(encoded)}u}}"
    if proto.type == FieldDescriptorProto.TYPE_BOOL:
        if value not in {"true", "false"}:
            raise ProtocyteError(
                f"{owner_full_name}.{proto.name}: invalid bool default value {value!r}"
            )
        return value
    if proto.type == FieldDescriptorProto.TYPE_FLOAT:
        return _floating_default_cpp(
            value, "::protocyte::f32", f"{owner_full_name}.{proto.name}"
        )
    if proto.type == FieldDescriptorProto.TYPE_DOUBLE:
        return _floating_default_cpp(
            value, "::protocyte::f64", f"{owner_full_name}.{proto.name}"
        )
    if proto.type in INTEGER_CONSTANT_KINDS:
        return _integer_default_cpp(
            value, INTEGER_CONSTANT_KINDS[proto.type], f"{owner_full_name}.{proto.name}"
        )
    if proto.type in SCALAR_CPP_TYPES:
        return value
    return None


def _field_default_byte_size(
    owner_full_name: str,
    proto: descriptor_pb2.FieldDescriptorProto,
    kind: str,
) -> int | None:
    if kind != "bytes" or not proto.HasField("default_value"):
        return None
    return len(_decode_bytes_default(owner_full_name, proto))


def _decode_bytes_default(
    owner_full_name: str, proto: descriptor_pb2.FieldDescriptorProto
) -> bytes:
    try:
        return text_encoding.CUnescape(proto.default_value)
    except ValueError as exc:
        raise ProtocyteError(
            f"{owner_full_name}.{proto.name}: invalid bytes default value {proto.default_value!r}"
        ) from exc


def _validate_array_default_byte_size(
    owner_full_name: str,
    field_name: str,
    default_size: int,
    array_max: int,
    array_fixed: bool,
) -> None:
    label = f"{owner_full_name}.{field_name}"
    if array_fixed and default_size != array_max:
        raise ProtocyteError(
            f"{label}: default value size must match fixed protocyte.array max"
        )
    if not array_fixed and default_size > array_max:
        raise ProtocyteError(f"{label}: default value size exceeds protocyte.array max")


def _integer_default_cpp(value: str, kind: str, label: str) -> str:
    try:
        numeric = int(value, 10)
    except ValueError as exc:
        raise ProtocyteError(
            f"{label}: invalid integer default value {value!r}"
        ) from exc
    return _cpp_constant_value(kind, _coerce_integer(kind, numeric, label))


def _floating_default_cpp(value: str, cpp_type: str, label: str) -> str:
    if value == "inf":
        return f"::std::numeric_limits<{cpp_type}>::infinity()"
    if value == "-inf":
        return f"-::std::numeric_limits<{cpp_type}>::infinity()"
    if value == "nan":
        return f"::std::numeric_limits<{cpp_type}>::quiet_NaN()"
    try:
        numeric = float(value)
    except ValueError as exc:
        raise ProtocyteError(
            f"{label}: invalid floating-point default value {value!r}"
        ) from exc
    if cpp_type == "::protocyte::f32":
        return _cpp_constant_value(CONSTANT_KIND_FLOAT, numeric)
    return _cpp_constant_value(CONSTANT_KIND_DOUBLE, numeric)


def _is_packed(proto: descriptor_pb2.FieldDescriptorProto, file_syntax: str) -> bool:
    if proto.label != FieldDescriptorProto.LABEL_REPEATED:
        return False
    if proto.type not in PACKABLE_TYPES:
        return False
    if proto.options.HasField("packed"):
        return proto.options.packed
    return file_syntax == "proto3"


def _resolve_constants_and_arrays(
    files: dict[str, FileModel], messages: dict[str, MessageModel]
) -> None:
    constants_by_message = {
        message.full_name: {constant.name: constant for constant in message.constants}
        for message in messages.values()
    }
    constants_by_package: dict[str, dict[str, ConstantModel]] = {}
    for file_model in files.values():
        package_constants = constants_by_package.setdefault(file_model.package, {})
        for constant in file_model.constants:
            package_constants[constant.name] = constant
    states: dict[int, str] = {}
    resolved_dependency_depths: dict[int, int] = {}
    dependency_child_depths: list[int] = []
    active_dependency_depth = 0

    def enter_constant_dependency(constant: ConstantModel) -> None:
        nonlocal active_dependency_depth
        if active_dependency_depth >= _MAX_CONSTANT_DEPENDENCY_DEPTH:
            raise ProtocyteError(
                f"{constant.full_name}: constant dependency nesting exceeds "
                f"maximum depth of {_MAX_CONSTANT_DEPENDENCY_DEPTH}"
            )
        active_dependency_depth += 1

    def leave_constant_dependency() -> None:
        nonlocal active_dependency_depth
        active_dependency_depth -= 1

    def record_constant_dependency(constant: ConstantModel) -> None:
        if dependency_child_depths:
            dependency_child_depths[-1] = max(
                dependency_child_depths[-1],
                resolved_dependency_depths[id(constant)],
            )

    def resolved_constant_dependency_depth(constant: ConstantModel) -> int:
        depth = dependency_child_depths[-1] + 1
        if depth > _MAX_CONSTANT_DEPENDENCY_DEPTH:
            raise ProtocyteError(
                f"{constant.full_name}: constant dependency nesting exceeds "
                f"maximum depth of {_MAX_CONSTANT_DEPENDENCY_DEPTH}"
            )
        return depth

    def find_message_constant(
        owner: MessageModel, scope: str, constant_name: str
    ) -> tuple[MessageModel | None, ConstantModel | None]:
        target_message = messages.get(scope)
        if target_message is not None:
            return target_message, constants_by_message.get(
                target_message.full_name, {}
            ).get(constant_name)
        relative_scope = f"{owner.package}.{scope}" if owner.package else scope
        if relative_scope != scope:
            target_message = messages.get(relative_scope)
            if target_message is not None:
                return target_message, constants_by_message.get(
                    target_message.full_name, {}
                ).get(constant_name)
        return None, None

    def find_constant(
        owner: MessageModel, name: str
    ) -> tuple[MessageModel | None, ConstantModel]:
        if "." in name:
            parts = name.split(".")
            if len(parts) < 2:
                raise ProtocyteError(
                    f"{owner.full_name}: invalid constant reference {name!r}"
                )
            package_name = ".".join(parts[:-1])
            target_constant = constants_by_package.get(package_name, {}).get(parts[-1])
            if target_constant is not None:
                return None, target_constant
            message_path = ".".join(parts[:-1])
            target_message, target_constant = find_message_constant(
                owner, message_path, parts[-1]
            )
            if target_message is None:
                raise ProtocyteError(
                    f"{owner.full_name}: unknown constant scope {message_path!r}"
                )
            if target_constant is None:
                raise ProtocyteError(f"{owner.full_name}: unknown constant {name!r}")
            return target_message, target_constant

        current: MessageModel | None = owner
        while current is not None:
            target_constant = constants_by_message.get(current.full_name, {}).get(name)
            if target_constant is not None:
                return current, target_constant
            current = current.parent
        target_constant = constants_by_package.get(owner.package, {}).get(name)
        if target_constant is not None:
            return None, target_constant
        raise ProtocyteError(f"{owner.full_name}: unknown constant {name!r}")

    def resolve_constant(
        target: MessageModel, constant: ConstantModel, owner: MessageModel
    ) -> _TypedValue:
        key = id(constant)
        state = states.get(key)
        if state == "visiting":
            raise ProtocyteError(
                f"{constant.full_name}: constant expression cycle detected"
            )
        if state == "done":
            return _TypedValue(
                constant.family,
                constant.value,
                cpp_expr=_reference_cpp_expr(owner, target, constant),
                numeric_kind=_constant_numeric_kind(constant.kind),
            )
        enter_constant_dependency(constant)
        dependency_child_depths.append(0)
        states[key] = "visiting"
        try:
            if constant.literal is not None:
                value = _coerce_literal(
                    constant.kind, constant.literal, constant.full_name
                )
            else:
                assert constant.expr is not None
                parsed = _ExprParser(
                    constant.expr,
                    lambda name: lookup_constant(target, name),
                    constant.full_name,
                ).parse()
                value = _coerce_expression_value(
                    constant.kind, parsed, constant.full_name
                )
            resolved_depth = resolved_constant_dependency_depth(constant)
            constant.family = _constant_family(constant.kind)
            constant.value = value
            constant.cpp_type = _cpp_constant_type(constant.kind)
            constant.cpp_value = _cpp_constant_value(constant.kind, value)
            resolved_dependency_depths[key] = resolved_depth
            states[key] = "done"
        except Exception:
            states.pop(key, None)
            resolved_dependency_depths.pop(key, None)
            raise
        finally:
            dependency_child_depths.pop()
            leave_constant_dependency()
        return _TypedValue(
            constant.family,
            constant.value,
            cpp_expr=_reference_cpp_expr(owner, target, constant),
            numeric_kind=_constant_numeric_kind(constant.kind),
        )

    def lookup_constant(owner: MessageModel, name: str) -> _TypedValue:
        target_message, target_constant = find_constant(owner, name)
        if target_message is None:
            return lookup_package_constant(owner.package, name)
        value = resolve_constant(target_message, target_constant, owner)
        record_constant_dependency(target_constant)
        return value

    def lookup_constant_for_array(owner: MessageModel, name: str) -> _TypedValue:
        return lookup_constant(owner, name)

    def resolve_package_constant(package: str, constant: ConstantModel) -> None:
        key = id(constant)
        state = states.get(key)
        if state == "visiting":
            raise ProtocyteError(
                f"{constant.full_name}: constant expression cycle detected"
            )
        if state == "done":
            return
        enter_constant_dependency(constant)
        dependency_child_depths.append(0)
        states[key] = "visiting"
        try:
            if constant.literal is not None:
                value = _coerce_literal(
                    constant.kind, constant.literal, constant.full_name
                )
            else:
                assert constant.expr is not None
                parsed = _ExprParser(
                    constant.expr,
                    lambda name: lookup_package_constant(package, name),
                    constant.full_name,
                ).parse()
                value = _coerce_expression_value(
                    constant.kind, parsed, constant.full_name
                )
            resolved_depth = resolved_constant_dependency_depth(constant)
            constant.family = _constant_family(constant.kind)
            constant.value = value
            constant.cpp_type = _cpp_constant_type(constant.kind)
            constant.cpp_value = _cpp_constant_value(constant.kind, value)
            resolved_dependency_depths[key] = resolved_depth
            states[key] = "done"
        except Exception:
            states.pop(key, None)
            resolved_dependency_depths.pop(key, None)
            raise
        finally:
            dependency_child_depths.pop()
            leave_constant_dependency()

    def lookup_package_constant(package: str, name: str) -> _TypedValue:
        if "." in name:
            parts = name.split(".")
            target_package = ".".join(parts[:-1])
            target_constant = constants_by_package.get(target_package, {}).get(
                parts[-1]
            )
        else:
            target_package = package
            target_constant = constants_by_package.get(package, {}).get(name)
        if target_constant is None:
            raise ProtocyteError(
                f"{package or '<root>'}: unknown package constant {name!r}"
            )
        resolve_package_constant(target_package, target_constant)
        record_constant_dependency(target_constant)
        return _TypedValue(
            target_constant.family,
            target_constant.value,
            cpp_expr=_constant_cpp_expr(package, target_constant),
            numeric_kind=_constant_numeric_kind(target_constant.kind),
        )

    for package, package_constants in constants_by_package.items():
        for constant in package_constants.values():
            resolve_package_constant(package, constant)

    for message in messages.values():
        if message.is_map_entry:
            continue
        for constant in message.constants:
            resolve_constant(message, constant, message)
        for field_model in message.fields:
            if field_model.array_expr is None:
                continue
            value = _ExprParser(
                field_model.array_expr,
                lambda name, owner=message: lookup_constant_for_array(owner, name),
                f"{message.full_name}.{field_model.name}",
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
            field_model.array_cpp_max = _cpp_constant_value(
                CONSTANT_KIND_UINT32, numeric
            )
            if field_model.default_byte_size is not None:
                _validate_array_default_byte_size(
                    message.full_name,
                    field_model.name,
                    field_model.default_byte_size,
                    numeric,
                    field_model.array_fixed,
                )


def _compute_file_dependencies(
    file_to_generate: list[str], files: dict[str, FileModel]
) -> None:
    for file_name in file_to_generate:
        file_model = files[file_name]
        for message in _walk_messages(file_model.messages):
            for field_model in message.fields:
                for dependency in _field_dependencies(field_model):
                    if dependency != file_name:
                        file_model.dependencies.add(dependency)


def _field_dependencies(field_model: FieldModel) -> Iterable[str]:
    if (
        field_model.message_type is not None
        and not field_model.message_type.is_map_entry
    ):
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
            if (
                field_model.kind == "message"
                and not field_model.repeated
                and field_model.message_type
            ):
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
    multi_ops = ("&&", "||", "==", "!=", "<=", ">=", "<<", ">>")
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
        if char in "+-*/%()!,<>&|^~":
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
                while end < len(text) and (
                    text[end].isdigit()
                    or text[end].lower() in {"a", "b", "c", "d", "e", "f"}
                ):
                    end += 1
                if end == hex_start:
                    raise ProtocyteError(
                        f"{label}: invalid numeric literal {text[index:end]!r}"
                    )
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
        if _number_token_is_floating(token):
            value = float(token)
            if not math.isfinite(value):
                raise ProtocyteError(f"{label}: numeric literal must be finite")
            return value
        return int(token, 0)
    except ValueError as exc:
        raise ProtocyteError(f"{label}: invalid numeric literal {token!r}") from exc


def _parse_string_token(token: str, label: str) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            value = ast.literal_eval(token)
    except (SyntaxError, SyntaxWarning, ValueError) as exc:
        raise ProtocyteError(f"{label}: invalid string literal") from exc
    if not isinstance(value, str):
        raise ProtocyteError(f"{label}: invalid string literal")
    _validate_utf8_string(value, label)
    return value


def _validate_utf8_string(value: str, label: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ProtocyteError(f"{label}: string value must be valid UTF-8") from exc


def _number_token_is_floating(token: str) -> bool:
    return not token.lower().startswith("0x") and (
        "." in token or "e" in token or "E" in token
    )


def _constant_family(kind: str) -> str:
    if kind == CONSTANT_KIND_BOOL:
        return CONSTANT_KIND_BOOL
    if kind == CONSTANT_KIND_STRING:
        return CONSTANT_KIND_STRING
    return "numeric"


def _constant_numeric_kind(kind: str) -> str | None:
    return kind if kind in _NUMERIC_EXPRESSION_KINDS else None


def _literal_integer_kind(value: int, *, hexadecimal: bool = False) -> str | None:
    if hexadecimal:
        if 0 <= value <= 2**31 - 1:
            return CONSTANT_KIND_INT32
        if value <= 2**32 - 1:
            return CONSTANT_KIND_UINT32
        if value <= 2**63 - 1:
            return CONSTANT_KIND_INT64
        if value <= 2**64 - 1:
            return CONSTANT_KIND_UINT64
        return None
    if -(2**31) <= value <= 2**31 - 1:
        return CONSTANT_KIND_INT32
    if -(2**63) <= value <= 2**63 - 1:
        return CONSTANT_KIND_INT64
    return None


def _wrap_cpp(value: _TypedValue, precedence: int) -> str:
    if not value.cpp_expr:
        return ""
    if value.cpp_precedence < precedence:
        return f"({value.cpp_expr})"
    return value.cpp_expr


def _binary_cpp(
    lhs: _TypedValue, rhs: _TypedValue, symbol: str, precedence: int
) -> str:
    return f"{_wrap_cpp(lhs, precedence)} {symbol} {_wrap_cpp(rhs, precedence + 1)}"


def _bool_value(
    value: bool, *, cpp_expr: str | None = None, cpp_precedence: int = 120
) -> _TypedValue:
    return _TypedValue(
        CONSTANT_KIND_BOOL,
        value,
        cpp_expr or ("true" if value else "false"),
        cpp_precedence,
    )


def _string_value(
    value: str, *, cpp_expr: str | None = None, cpp_precedence: int = 120
) -> _TypedValue:
    if cpp_expr is None:
        cpp_expr = f'"{_cpp_escape_string(value)}"'
    return _TypedValue(CONSTANT_KIND_STRING, value, cpp_expr, cpp_precedence)


def _numeric_value(
    value: int | float,
    *,
    cpp_expr: str | None = None,
    cpp_precedence: int = 120,
    numeric_kind: str | None = None,
) -> _TypedValue:
    if numeric_kind is None:
        numeric_kind = (
            CONSTANT_KIND_DOUBLE
            if isinstance(value, float)
            else _literal_integer_kind(value)
        )
    if numeric_kind == CONSTANT_KIND_FLOAT:
        value = _round_f32(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ProtocyteError("numeric expression must be finite")
    if cpp_expr is None:
        cpp_expr = str(value)
    return _TypedValue("numeric", value, cpp_expr, cpp_precedence, numeric_kind)


def _type_only_value(value: _TypedValue) -> _TypedValue:
    if value.family == CONSTANT_KIND_BOOL:
        return _bool_value(False, cpp_expr=value.cpp_expr)
    if value.family == CONSTANT_KIND_STRING:
        return _string_value("", cpp_expr=value.cpp_expr)
    if value.family == "numeric":
        kind = value.numeric_kind
        placeholder = (
            value.value
            if kind is None
            else (0.0 if kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE} else 0)
        )
        return _numeric_value(
            placeholder,  # type: ignore[arg-type]
            cpp_expr=value.cpp_expr,
            cpp_precedence=value.cpp_precedence,
            numeric_kind=kind,
        )
    raise AssertionError(f"unsupported expression family {value.family!r}")


def _round_f32(
    value: int | float, error: str = "numeric expression must be finite"
) -> float:
    try:
        numeric = (
            _round_integer_to_f32_input(value)
            if isinstance(value, int)
            else float(value)
        )
    except OverflowError as exc:
        raise ProtocyteError(error) from exc
    if not math.isfinite(numeric):
        raise ProtocyteError(error)
    try:
        rounded = struct.unpack("<f", struct.pack("<f", numeric))[0]
    except OverflowError as exc:
        raise ProtocyteError(error) from exc
    if not math.isfinite(rounded):
        raise ProtocyteError(error)
    return rounded


def _round_integer_to_f32_input(value: int) -> float:
    magnitude = abs(value)
    shift = magnitude.bit_length() - 24
    if shift <= 0:
        return float(value)
    truncated = magnitude >> shift
    remainder = magnitude & (2**shift - 1)
    halfway = 2 ** (shift - 1)
    if remainder > halfway or (remainder == halfway and truncated & 1):
        truncated += 1
    if truncated == 2**24:
        truncated >>= 1
        shift += 1
    rounded = truncated << shift
    return -float(rounded) if value < 0 else float(rounded)


def _cpp_escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _expect_bool(value: _TypedValue, label: str) -> bool:
    if value.family == CONSTANT_KIND_BOOL:
        return bool(value.value)
    if value.family == "numeric" and isinstance(value.value, int | float):
        kind = _typed_numeric_kind(value, label)
        normalized = _convert_numeric_value(value.value, kind, kind, label)
        return normalized != 0
    raise ProtocyteError(f"{label}: expected bool or numeric expression")


def _expect_numeric(value: _TypedValue, label: str) -> int | float:
    if value.family == CONSTANT_KIND_BOOL:
        return 1 if bool(value.value) else 0
    if value.family != "numeric":
        raise ProtocyteError(f"{label}: expected numeric expression")
    return value.value  # type: ignore[return-value]


def _truncating_integer_divide(lhs: int, rhs: int) -> int:
    quotient = abs(lhs) // abs(rhs)
    return -quotient if (lhs < 0) != (rhs < 0) else quotient


def _signed_division_overflows(lhs: int, rhs: int, kind: str) -> bool:
    lower, _ = _integer_range(kind)
    return lhs == lower and rhs == -1


def _numeric_operands(
    lhs: _TypedValue, rhs: _TypedValue, label: str
) -> tuple[int | float, int | float, str]:
    left = _expect_numeric(lhs, label)
    right = _expect_numeric(rhs, label)
    result_kind = _common_value_numeric_kind(lhs, rhs)
    left = _convert_numeric_value(
        left, _typed_numeric_kind(lhs, label), result_kind, label
    )
    right = _convert_numeric_value(
        right, _typed_numeric_kind(rhs, label), result_kind, label
    )
    return left, right, result_kind


def _numeric_binary(
    lhs: _TypedValue,
    rhs: _TypedValue,
    label: str,
    op: Callable[[int | float, int | float], int | float],
    *,
    symbol: str,
    precedence: int,
) -> _TypedValue:
    left, right, result_kind = _numeric_operands(lhs, rhs, label)
    result = _normalize_numeric_result(op(left, right), result_kind, label)
    return _numeric_value(
        result,
        cpp_expr=_binary_cpp(lhs, rhs, symbol, precedence),
        cpp_precedence=precedence,
        numeric_kind=result_kind,
    )


def _typed_numeric_kind(value: _TypedValue, label: str) -> str:
    if value.family == CONSTANT_KIND_BOOL:
        return CONSTANT_KIND_INT32
    if value.family != "numeric":
        raise ProtocyteError(f"{label}: expected numeric expression")
    if value.numeric_kind in _NUMERIC_EXPRESSION_KINDS:
        return value.numeric_kind
    if isinstance(value.value, int):
        inferred = _literal_integer_kind(value.value)
        if inferred is not None:
            return inferred
    raise ProtocyteError(f"{label}: numeric expression is outside the supported range")


def _common_value_numeric_kind(lhs: _TypedValue, rhs: _TypedValue) -> str:
    return _common_numeric_kind(
        [
            _typed_numeric_kind(lhs, "numeric expression"),
            _typed_numeric_kind(rhs, "numeric expression"),
        ]
    )


def _common_numeric_kind(kinds: Iterable[str]) -> str:
    kind_list = list(kinds)
    if CONSTANT_KIND_DOUBLE in kind_list:
        return CONSTANT_KIND_DOUBLE
    if CONSTANT_KIND_FLOAT in kind_list:
        return CONSTANT_KIND_FLOAT
    result = kind_list[0]
    for kind in kind_list[1:]:
        result = _common_integer_kind(result, kind)
    return result


def _convert_numeric_value(
    value: int | float,
    source_kind: str,
    target_kind: str,
    label: str = "numeric expression",
) -> int | float:
    if source_kind in _INTEGER_EXPRESSION_KINDS:
        if not isinstance(value, int):
            raise ProtocyteError(
                "numeric expression cannot be converted from an integer kind"
            )
        source_bits, source_signed = _INTEGER_KIND_INFO[source_kind]
        if source_signed:
            lower, upper = _integer_range(source_kind)
            if value < lower or value > upper:
                raise ProtocyteError(
                    f"{label}: integer operand {value} is out of range for {source_kind}"
                )
        else:
            value &= 2**source_bits - 1
    if target_kind == CONSTANT_KIND_DOUBLE:
        return float(value)
    if target_kind == CONSTANT_KIND_FLOAT:
        return _round_f32(value)
    if source_kind not in _INTEGER_EXPRESSION_KINDS or not isinstance(value, int):
        raise ProtocyteError(
            "numeric expression cannot be converted to an integer kind"
        )
    bits, signed = _INTEGER_KIND_INFO[target_kind]
    if not signed:
        return value & (2**bits - 1)
    lower, upper = _integer_range(target_kind)
    if value < lower or value > upper:
        raise ProtocyteError(
            f"{label}: integer operand {value} is out of range for {target_kind}"
        )
    return value


def _normalize_numeric_result(value: int | float, kind: str, label: str) -> int | float:
    if kind not in _INTEGER_EXPRESSION_KINDS or not isinstance(value, int):
        return value
    bits, signed = _INTEGER_KIND_INFO[kind]
    if not signed:
        return value & (2**bits - 1)
    lower, upper = _integer_range(kind)
    if value < lower or value > upper:
        raise ProtocyteError(
            f"{label}: integer result {value} is out of range for {kind}"
        )
    return value


def _expect_integral(value: _TypedValue, label: str) -> tuple[int, str]:
    if value.family == CONSTANT_KIND_BOOL:
        return (1 if bool(value.value) else 0), CONSTANT_KIND_INT32
    if value.family != "numeric" or not isinstance(value.value, int):
        raise ProtocyteError(
            f"{label}: bitwise operators require integer or bool operands"
        )
    kind = value.numeric_kind or _literal_integer_kind(value.value)
    if kind is None:
        raise ProtocyteError(
            f"{label}: bitwise integer operand is outside the supported 64-bit range"
        )
    return value.value, kind


def _common_integer_kind(lhs: str, rhs: str) -> str:
    lhs_bits, lhs_signed = _INTEGER_KIND_INFO[lhs]
    rhs_bits, rhs_signed = _INTEGER_KIND_INFO[rhs]
    if lhs == rhs:
        return lhs
    if lhs_signed == rhs_signed:
        return _integer_kind(max(lhs_bits, rhs_bits), lhs_signed)
    unsigned_kind = lhs if not lhs_signed else rhs
    signed_kind = rhs if not lhs_signed else lhs
    unsigned_bits, _ = _INTEGER_KIND_INFO[unsigned_kind]
    signed_bits, _ = _INTEGER_KIND_INFO[signed_kind]
    if unsigned_bits >= signed_bits:
        return _integer_kind(unsigned_bits, False)
    return _integer_kind(signed_bits, True)


def _integer_kind(bits: int, signed: bool) -> str:
    return {
        (32, True): CONSTANT_KIND_INT32,
        (32, False): CONSTANT_KIND_UINT32,
        (64, True): CONSTANT_KIND_INT64,
        (64, False): CONSTANT_KIND_UINT64,
    }[(bits, signed)]


def _integer_range(kind: str) -> tuple[int, int]:
    bits, signed = _INTEGER_KIND_INFO[kind]
    if signed:
        return -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    return 0, 2**bits - 1


def _integer_bits(value: int, kind: str, label: str) -> int:
    bits, signed = _INTEGER_KIND_INFO[kind]
    if signed:
        lower, upper = _integer_range(kind)
        if value < lower or value > upper:
            raise ProtocyteError(
                f"{label}: integer operand {value} is out of range for {kind}"
            )
    return value & (2**bits - 1)


def _integer_from_bits(value: int, kind: str) -> int:
    bits, signed = _INTEGER_KIND_INFO[kind]
    value &= 2**bits - 1
    if signed and value >= 2 ** (bits - 1):
        return value - 2**bits
    return value


def _bitwise_binary(
    lhs: _TypedValue,
    rhs: _TypedValue,
    label: str,
    op: Callable[[int, int], int],
    *,
    symbol: str,
    precedence: int,
) -> _TypedValue:
    lhs_value, lhs_kind = _expect_integral(lhs, label)
    rhs_value, rhs_kind = _expect_integral(rhs, label)
    result_kind = _common_integer_kind(lhs_kind, rhs_kind)
    lhs_value = int(_convert_numeric_value(lhs_value, lhs_kind, result_kind, label))
    rhs_value = int(_convert_numeric_value(rhs_value, rhs_kind, result_kind, label))
    bits, _ = _INTEGER_KIND_INFO[result_kind]
    result_bits = op(
        _integer_bits(lhs_value, result_kind, label),
        _integer_bits(rhs_value, result_kind, label),
    ) & (2**bits - 1)
    return _numeric_value(
        _integer_from_bits(result_bits, result_kind),
        cpp_expr=_binary_cpp(lhs, rhs, symbol, precedence),
        cpp_precedence=precedence,
        numeric_kind=result_kind,
    )


def _bitwise_complement(value: _TypedValue, label: str) -> _TypedValue:
    operand, kind = _expect_integral(value, label)
    bits, _ = _INTEGER_KIND_INFO[kind]
    result_bits = (~_integer_bits(operand, kind, label)) & (2**bits - 1)
    return _numeric_value(
        _integer_from_bits(result_bits, kind),
        cpp_expr="~" + _wrap_cpp(value, 110),
        cpp_precedence=110,
        numeric_kind=kind,
    )


def _shift_value(
    lhs: _TypedValue, rhs: _TypedValue, label: str, *, left: bool
) -> _TypedValue:
    lhs_value, lhs_kind = _expect_integral(lhs, label)
    rhs_value, rhs_kind = _expect_integral(rhs, label)
    lhs_value = int(_convert_numeric_value(lhs_value, lhs_kind, lhs_kind, label))
    rhs_value = int(_convert_numeric_value(rhs_value, rhs_kind, rhs_kind, label))
    bits, signed = _INTEGER_KIND_INFO[lhs_kind]
    if rhs_value < 0:
        raise ProtocyteError(f"{label}: shift count must not be negative")
    if rhs_value >= bits:
        raise ProtocyteError(
            f"{label}: shift count {rhs_value} must be less than {bits}"
        )

    symbol = "<<" if left else ">>"
    mask = 2**bits - 1
    if left:
        result = _integer_from_bits((lhs_value & mask) << rhs_value, lhs_kind)
    elif signed:
        result = lhs_value >> rhs_value
    else:
        result = (lhs_value & mask) >> rhs_value

    return _numeric_value(
        result,
        cpp_expr=_binary_cpp(lhs, rhs, symbol, 80),
        cpp_precedence=80,
        numeric_kind=lhs_kind,
    )


def _numeric_compare(
    lhs: _TypedValue,
    rhs: _TypedValue,
    label: str,
    op: Callable[[int | float, int | float], bool],
) -> bool:
    left, right, _ = _numeric_operands(lhs, rhs, label)
    return op(left, right)


def _compare_equal(lhs: _TypedValue, rhs: _TypedValue, label: str) -> bool:
    numeric_families = {"numeric", CONSTANT_KIND_BOOL}
    if lhs.family in numeric_families and rhs.family in numeric_families:
        left, right, _ = _numeric_operands(lhs, rhs, label)
        return left == right
    if lhs.family != rhs.family:
        raise ProtocyteError(f"{label}: equality requires operands of the same type")
    return lhs.value == rhs.value


def _function_numeric_argument(
    name: str, value: _TypedValue, label: str
) -> tuple[int | float, str]:
    if value.family == CONSTANT_KIND_BOOL:
        return (1 if bool(value.value) else 0), CONSTANT_KIND_INT32
    if value.family != "numeric" or not isinstance(value.value, int | float):
        raise ProtocyteError(f"{label}: {name}() expects numeric arguments")
    kind = value.numeric_kind
    if kind not in _NUMERIC_EXPRESSION_KINDS:
        if isinstance(value.value, int):
            kind = _literal_integer_kind(value.value)
    if kind not in _NUMERIC_EXPRESSION_KINDS:
        raise ProtocyteError(
            f"{label}: {name}() argument is outside the supported numeric range"
        )
    numeric = value.value
    if kind in _INTEGER_EXPRESSION_KINDS:
        assert isinstance(numeric, int)
        bits, signed = _INTEGER_KIND_INFO[kind]
        if signed:
            lower, upper = _integer_range(kind)
            if numeric < lower or numeric > upper:
                raise ProtocyteError(
                    f"{label}: {name}() argument is out of range for {kind}"
                )
        else:
            numeric &= 2**bits - 1
    return numeric, kind


def _function_numeric_result(
    name: str, value: int | float, kind: str, label: str
) -> _TypedValue:
    error = f"{label}: {name}() result is not finite"
    if kind == CONSTANT_KIND_FLOAT:
        value = _round_f32(value, error)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ProtocyteError(error)
    return _numeric_value(
        value,
        cpp_expr=_cpp_constant_value(kind, value),
        numeric_kind=kind,
    )


def _evaluate_real_function(
    name: str,
    value: int | float,
    source_kind: str,
    label: str,
) -> _TypedValue:
    result_kind = (
        CONSTANT_KIND_FLOAT
        if source_kind == CONSTANT_KIND_FLOAT
        else CONSTANT_KIND_DOUBLE
    )
    operand = _convert_numeric_value(value, source_kind, result_kind)
    try:
        result = evaluate_unary(
            name,
            operand,
            32 if result_kind == CONSTANT_KIND_FLOAT else 64,
        )
    except DeterministicMathDomainError as exc:
        raise ProtocyteError(f"{label}: {name}() domain error") from exc
    except DeterministicMathNonFiniteError as exc:
        raise ProtocyteError(f"{label}: {name}() result is not finite") from exc
    return _function_numeric_result(name, result, result_kind, label)


def _evaluate_rounding_function(
    name: str,
    value: int | float,
    source_kind: str,
    label: str,
) -> _TypedValue:
    result_kind = (
        CONSTANT_KIND_FLOAT
        if source_kind == CONSTANT_KIND_FLOAT
        else CONSTANT_KIND_DOUBLE
    )
    operand = float(_convert_numeric_value(value, source_kind, result_kind))
    if name == "ceil":
        result = float(math.ceil(operand))
    elif name == "floor":
        result = float(math.floor(operand))
    elif name == "trunc":
        result = float(math.trunc(operand))
    elif operand.is_integer():
        result = operand
    else:
        fractional, integral = math.modf(abs(operand))
        magnitude = integral + (1.0 if fractional >= 0.5 else 0.0)
        result = math.copysign(magnitude, operand)
    if result == 0.0:
        result = math.copysign(0.0, operand)
    return _function_numeric_result(name, result, result_kind, label)


def _evaluate_pow(args: list[_TypedValue], label: str) -> _TypedValue:
    if len(args) != 2:
        raise ProtocyteError(f"{label}: pow() expects two numeric arguments")
    base, base_kind = _function_numeric_argument("pow", args[0], label)
    exponent, exponent_kind = _function_numeric_argument("pow", args[1], label)
    float_base = float(
        _convert_numeric_value(base, base_kind, CONSTANT_KIND_DOUBLE, label)
    )
    float_exponent = float(
        _convert_numeric_value(
            exponent,
            exponent_kind,
            CONSTANT_KIND_DOUBLE,
            label,
        )
    )
    try:
        result = evaluate_deterministic_pow(float_base, float_exponent)
    except DeterministicMathDomainError as exc:
        raise ProtocyteError(f"{label}: pow() domain error") from exc
    except DeterministicMathNonFiniteError as exc:
        raise ProtocyteError(f"{label}: pow() result is not finite") from exc
    return _function_numeric_result("pow", result, CONSTANT_KIND_DOUBLE, label)


def _evaluate_abs(args: list[_TypedValue], label: str) -> _TypedValue:
    if len(args) != 1:
        raise ProtocyteError(f"{label}: abs() expects one numeric argument")
    value, kind = _function_numeric_argument("abs", args[0], label)
    if kind in _INTEGER_EXPRESSION_KINDS:
        assert isinstance(value, int)
        lower, _ = _integer_range(kind)
        if _INTEGER_KIND_INFO[kind][1] and value == lower:
            raise ProtocyteError(f"{label}: abs() result is out of range for {kind}")
    return _function_numeric_result("abs", abs(value), kind, label)


def _evaluate_min_max(name: str, args: list[_TypedValue], label: str) -> _TypedValue:
    if len(args) < 2:
        raise ProtocyteError(
            f"{label}: {name}() expects at least two numeric arguments"
        )
    values = [_function_numeric_argument(name, arg, label) for arg in args]
    result_kind = _common_numeric_kind(kind for _, kind in values)
    converted = [
        _convert_numeric_value(value, kind, result_kind) for value, kind in values
    ]
    result = converted[0]
    for candidate in converted[1:]:
        if (name == "min" and candidate < result) or (
            name == "max" and candidate > result
        ):
            result = candidate
    return _function_numeric_result(name, result, result_kind, label)


def _cast_string_value(value: _TypedValue, label: str) -> str:
    if value.family == CONSTANT_KIND_STRING:
        return str(value.value)
    if value.family == CONSTANT_KIND_BOOL:
        return "true" if bool(value.value) else "false"
    if value.family != "numeric":
        raise ProtocyteError(f"{label}: str() expects one scalar argument")
    kind = _typed_numeric_kind(value, label)
    numeric = _convert_numeric_value(value.value, kind, kind, label)  # type: ignore[arg-type]
    if kind in _INTEGER_EXPRESSION_KINDS:
        return str(int(numeric))
    precision = ".9g" if kind == CONSTANT_KIND_FLOAT else ".17g"
    text = format(float(numeric), precision)
    if "e" not in text and "E" not in text and "." not in text:
        text += ".0"
    return text


def _evaluate_scalar_cast(
    name: str, args: list[_TypedValue], label: str
) -> _TypedValue:
    if len(args) != 1:
        raise ProtocyteError(f"{label}: {name}() expects one scalar argument")
    value = args[0]
    target_kind = _SCALAR_CAST_KINDS[name]
    if target_kind == CONSTANT_KIND_STRING:
        return _string_value(_cast_string_value(value, label))
    if value.family == CONSTANT_KIND_STRING:
        raise ProtocyteError(f"{label}: {name}() expects one bool or numeric argument")
    if target_kind == CONSTANT_KIND_BOOL:
        if value.family == CONSTANT_KIND_BOOL:
            result = bool(value.value)
        elif value.family == "numeric":
            source_kind = _typed_numeric_kind(value, label)
            normalized = _convert_numeric_value(
                value.value,
                source_kind,
                source_kind,
                label,  # type: ignore[arg-type]
            )
            result = normalized != 0
        else:
            raise ProtocyteError(
                f"{label}: bool() expects one bool or numeric argument"
            )
        return _bool_value(result, cpp_expr=_cpp_constant_value(target_kind, result))

    if value.family == CONSTANT_KIND_BOOL:
        source_kind = CONSTANT_KIND_INT32
        numeric: int | float = 1 if bool(value.value) else 0
    elif value.family == "numeric":
        source_kind = _typed_numeric_kind(value, label)
        numeric = value.value  # type: ignore[assignment]
    else:
        raise ProtocyteError(f"{label}: {name}() expects one bool or numeric argument")

    normalized = _convert_numeric_value(numeric, source_kind, source_kind, label)
    if target_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
        result = (
            _round_f32(
                normalized,
                f"{label}: {name}() result is not finite",
            )
            if target_kind == CONSTANT_KIND_FLOAT
            else float(normalized)
        )
        return _function_numeric_result(name, result, target_kind, label)

    if source_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
        result = math.trunc(float(normalized))
        lower, upper = _integer_range(target_kind)
        if result < lower or result > upper:
            raise ProtocyteError(
                f"{label}: {name}() result is out of range for {target_kind}"
            )
    else:
        result = _integer_from_bits(int(normalized), target_kind)
    return _function_numeric_result(name, result, target_kind, label)


def _evaluate_function_type(
    name: str, args: list[_TypedValue], label: str
) -> _TypedValue:
    if name in _SCALAR_CAST_KINDS:
        return _type_only_value(_evaluate_scalar_cast(name, args, label))
    if name == "len":
        if len(args) != 1 or args[0].family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: len() expects one string argument")
        return _numeric_value(0, numeric_kind=CONSTANT_KIND_UINT32)
    if name == "substr":
        if len(args) != 3 or args[0].family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: substr() expects string, start, count")
        _coerce_expression_value(CONSTANT_KIND_UINT32, args[1], label)
        _coerce_expression_value(CONSTANT_KIND_UINT32, args[2], label)
        return _string_value("")
    if name == "starts_with":
        if (
            len(args) != 2
            or args[0].family != CONSTANT_KIND_STRING
            or args[1].family != CONSTANT_KIND_STRING
        ):
            raise ProtocyteError(f"{label}: starts_with() expects two string arguments")
        return _bool_value(False)
    if name == "pow":
        if len(args) != 2:
            raise ProtocyteError(f"{label}: pow() expects two numeric arguments")
        for arg in args:
            _function_numeric_argument(name, arg, label)
        return _numeric_value(0.0, numeric_kind=CONSTANT_KIND_DOUBLE)
    if name == "abs":
        if len(args) != 1:
            raise ProtocyteError(f"{label}: abs() expects one numeric argument")
        _, result_kind = _function_numeric_argument(name, args[0], label)
        return _numeric_value(
            0.0 if result_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE} else 0,
            numeric_kind=result_kind,
        )
    if name in {"min", "max"}:
        if len(args) < 2:
            raise ProtocyteError(
                f"{label}: {name}() expects at least two numeric arguments"
            )
        values = [_function_numeric_argument(name, arg, label) for arg in args]
        result_kind = _common_numeric_kind(kind for _, kind in values)
        return _numeric_value(
            0.0 if result_kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE} else 0,
            numeric_kind=result_kind,
        )
    if name in {
        "sqrt",
        "exp",
        "log",
        "log2",
        "log10",
        "ceil",
        "floor",
        "trunc",
        "round",
    }:
        if len(args) != 1:
            raise ProtocyteError(f"{label}: {name}() expects one numeric argument")
        _, source_kind = _function_numeric_argument(name, args[0], label)
        result_kind = (
            CONSTANT_KIND_FLOAT
            if source_kind == CONSTANT_KIND_FLOAT
            else CONSTANT_KIND_DOUBLE
        )
        return _numeric_value(0.0, numeric_kind=result_kind)
    raise ProtocyteError(f"{label}: unsupported function {name}()")


def _evaluate_function(
    name: str,
    args: list[_TypedValue],
    label: str,
    *,
    evaluate: bool = True,
) -> _TypedValue:
    if not evaluate:
        return _evaluate_function_type(name, args, label)
    if name in _SCALAR_CAST_KINDS:
        return _evaluate_scalar_cast(name, args, label)
    if name == "len":
        if len(args) != 1 or args[0].family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: len() expects one string argument")
        size = len(str(args[0].value))
        return _numeric_value(
            size,
            cpp_expr=_cpp_constant_value(CONSTANT_KIND_UINT32, size),
            numeric_kind=CONSTANT_KIND_UINT32,
        )
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
        if (
            len(args) != 2
            or args[0].family != CONSTANT_KIND_STRING
            or args[1].family != CONSTANT_KIND_STRING
        ):
            raise ProtocyteError(f"{label}: starts_with() expects two string arguments")
        return _bool_value(
            str(args[0].value).startswith(str(args[1].value)),
            cpp_expr=f"{_wrap_cpp(args[0], 100)}.starts_with({_wrap_cpp(args[1], 0)})",
        )
    if name == "pow":
        return _evaluate_pow(args, label)
    if name == "abs":
        return _evaluate_abs(args, label)
    if name in {"min", "max"}:
        return _evaluate_min_max(name, args, label)
    if name in {"sqrt", "exp", "log", "log2", "log10"}:
        if len(args) != 1:
            raise ProtocyteError(f"{label}: {name}() expects one numeric argument")
        value, kind = _function_numeric_argument(name, args[0], label)
        return _evaluate_real_function(name, value, kind, label)
    if name in {"ceil", "floor", "trunc", "round"}:
        if len(args) != 1:
            raise ProtocyteError(f"{label}: {name}() expects one numeric argument")
        value, kind = _function_numeric_argument(name, args[0], label)
        return _evaluate_rounding_function(name, value, kind, label)
    raise ProtocyteError(f"{label}: unsupported function {name}()")


def _coerce_literal(kind: str, literal: object, label: str) -> object:
    family = _constant_family(kind)
    if family == CONSTANT_KIND_STRING:
        if not isinstance(literal, str):
            raise ProtocyteError(f"{label}: invalid string literal {literal!r}")
        _validate_utf8_string(literal, label)
        return literal
    if family == CONSTANT_KIND_BOOL:
        if not isinstance(literal, bool):
            raise ProtocyteError(f"{label}: invalid bool literal {literal!r}")
        return literal
    if kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
        if isinstance(literal, bool) or not isinstance(literal, int | float):
            raise ProtocyteError(f"{label}: invalid numeric literal {literal!r}")
        finite_error = f"{label}: numeric literal must be finite"
        if kind == CONSTANT_KIND_FLOAT:
            return _round_f32(literal, finite_error)
        try:
            value = float(literal)
        except OverflowError as exc:
            raise ProtocyteError(finite_error) from exc
        except (TypeError, ValueError) as exc:
            raise ProtocyteError(
                f"{label}: invalid numeric literal {literal!r}"
            ) from exc
        if not math.isfinite(value):
            raise ProtocyteError(finite_error)
        return value
    if isinstance(literal, bool) or not isinstance(literal, int):
        raise ProtocyteError(f"{label}: invalid numeric literal {literal!r}")
    try:
        value = int(literal)
    except (TypeError, ValueError) as exc:
        raise ProtocyteError(f"{label}: invalid numeric literal {literal!r}") from exc
    return _coerce_integer(kind, value, label)


def _coerce_expression_value(kind: str, value: _TypedValue, label: str) -> object:
    family = _constant_family(kind)
    if family == CONSTANT_KIND_STRING:
        if value.family != CONSTANT_KIND_STRING:
            raise ProtocyteError(f"{label}: expression must evaluate to string")
        string_value = str(value.value)
        _validate_utf8_string(string_value, label)
        return string_value
    if family == CONSTANT_KIND_BOOL:
        if value.family == CONSTANT_KIND_BOOL:
            return bool(value.value)
        if value.family == "numeric" and isinstance(value.value, int):
            source_kind = _typed_numeric_kind(value, label)
            normalized = _convert_numeric_value(
                value.value, source_kind, source_kind, label
            )
            return normalized != 0
        raise ProtocyteError(f"{label}: expression must evaluate to bool or integer")
    if value.family != "numeric":
        raise ProtocyteError(f"{label}: expression must evaluate to numeric")
    numeric_value = value.value
    source_kind = _typed_numeric_kind(value, label)
    if kind in {CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE}:
        out = float(_convert_numeric_value(numeric_value, source_kind, kind, label))
        if not math.isfinite(out):
            raise ProtocyteError(f"{label}: numeric expression must be finite")
        return out
    if isinstance(numeric_value, float):
        numeric_value = int(numeric_value)
    else:
        numeric_value = int(
            _convert_numeric_value(numeric_value, source_kind, source_kind, label)
        )
    return _coerce_integer(kind, int(numeric_value), label)


def _coerce_integer(kind: str, value: int, label: str) -> int:
    ranges = {
        CONSTANT_KIND_INT32: (-(2**31), 2**31 - 1),
        CONSTANT_KIND_INT64: (-(2**63), 2**63 - 1),
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
        CONSTANT_KIND_STRING: "::protocyte::StringView",
    }[kind]


def _cpp_constant_value(kind: str, value: object) -> str:
    if kind == CONSTANT_KIND_BOOL:
        return "true" if value else "false"
    if kind == CONSTANT_KIND_INT32:
        return str(value)
    if kind == CONSTANT_KIND_INT64:
        numeric = int(value)
        if numeric == -(2**63):
            return "(-9223372036854775807ll - 1ll)"
        return f"{numeric}ll"
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
    try:
        encoded = str(value).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ProtocyteError("string constant must be valid UTF-8") from exc
    return f"{_cpp_string_literal(encoded)}, {len(encoded)}u"


def _inline_constant_cpp_expr(constant: ConstantModel) -> str:
    if constant.kind == CONSTANT_KIND_STRING:
        return f"::protocyte::StringView {{{constant.cpp_value}}}"
    return constant.cpp_value


def _constant_cpp_expr(owner_package: str, constant: ConstantModel) -> str:
    local_name = f"{owner_package}.{constant.name}" if owner_package else constant.name
    if constant.full_name == local_name:
        return constant.cpp_name
    return _inline_constant_cpp_expr(constant)


def _reference_cpp_expr(
    owner: MessageModel, target: MessageModel, constant: ConstantModel
) -> str:
    if target.full_name == owner.full_name:
        return constant.cpp_name
    return _inline_constant_cpp_expr(constant)


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
