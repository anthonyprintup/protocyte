from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import hashlib
import re
from typing import Iterable


CPP_KEYWORDS = frozenset(
    {
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
)

CPP_RESERVED_IDENTIFIER_PREFIX = "protocyte_escaped_"
CPP_DERIVABLE_IDENTIFIER_SUFFIX = "protocyte"
_CPP_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_KEYWORD_ESCAPED_IDENTIFIERS = frozenset(f"{keyword}_" for keyword in CPP_KEYWORDS)

# Names declared directly by the bundled runtime in ``::protocyte``.  Generated
# schemas may extend that namespace; only a concrete collision with one of these
# declarations needs remapping.
PROTOCYTE_RUNTIME_CPP_SYMBOLS = frozenset(
    """
    Allocator AlwaysFalse Array Box BulkFixedWidthPackedScalar ByteArray
    ByteAssignableCopyConstructible ByteSpanSource Bytes CheckedSpanSource
    CheckedSpanSourceElement CheckedSpanSourceView ContainerCompatibleSpanSource
    CopyFromConstructible CopyValueCompatible DataSizeSpanSource DecodedUnknownField
    DefaultConfig DefaultConstructible Error ErrorCode FixedByteArray HashMap
    InvokeResult LimitedReader Limits MessageParseAccess MutableUnknownFieldSet
    NestedMessageReader Optional OptionalType ParseBudgetReader
    PointerContextConstructible PointerSpanSource RangeElementCompatible ReaderLike
    ReaderRef ReferenceContextConstructible ReflectionEnumInfo
    ReflectionEnumValueInfo ReflectionFieldInfo ReflectionFieldLabel
    Result ResultErrorTag ResultType ResultValueTag ReverseIterator SliceReader
    SliceWriter Span SpanBeginPointer SpanDataPointer SpanEndPointer SpanSource
    StagedReader Status String StringView Tag TextArray TextChar TextPointer TextSource
    TransformErrorType TransformObjectValueType TransformReferenceValueType
    TransformValueType Unexpected UnexpectedType UnknownFieldRange UnknownFieldStorage
    UnknownFieldView UnknownFieldWriter ValueContext ValueContextStorage Vector WireType
    WrapperValue WrapperValueT WriterLike add_size as_bytes as_writable_bytes
    byte_span_of byte_span_size bytes_equal bytes_zero checked_add checked_mul
    checked_span_count checked_span_of config_preserves_unknown_fields copy_bytes
    copy_value cstring_byte_span_of cstring_size declval decode_tag
    decode_unknown_field_at decode_zigzag32 decode_zigzag64 dynamic_extent
    encode_zigzag32 encode_zigzag64 expect_wire_type f32 f64 fnv1a format_as forward
    hosted_allocate hosted_allocator hosted_deallocate i16 i32 i64 i8 invoke
    invoke_member iptr is_optional is_result is_span is_text_char_array is_unexpected
    isize length_delimited_field_size message_field_size move open_nested_message
    open_nested_message_sized pop_recursion prepare_unknown_field_merge
    preserve_unknown_fields_v ptr push_recursion read_bool read_bool_field read_bytes
    read_bytes_field read_bytes_sized read_double read_double_field read_enum
    read_enum_field read_fixed_width_packed_value read_fixed_width_packed_values
    read_fixed32 read_fixed32_scalar read_fixed32_value read_fixed32_value_field
    read_fixed64 read_fixed64_scalar read_fixed64_value read_fixed64_value_field
    read_float read_float_field read_int32 read_int32_field read_int64 read_int64_field
    read_length_delimited_size read_message read_message_partial read_sfixed32
    read_sfixed32_field read_sfixed64 read_sfixed64_field read_sint32 read_sint32_field
    read_sint64 read_sint64_field read_string read_string_field read_string_sized
    read_tag read_uint32 read_uint32_field read_uint64 read_uint64_field
    read_unknown_field read_varint read_varint_scalar read_zigzag32_scalar
    read_zigzag64_scalar serialize skip_field skip_group span_of span_storage_size
    string_view_equal tag_size text_byte_span_of u16 u32 u64 u8 unexpected uptr usize
    validate_unknown_field_bytes varint_size with_field write_bool write_bool_field
    write_bytes write_bytes_field write_canonical_unknown_fields write_double
    write_double_field write_enum write_enum_field write_fixed_width_packed_value
    write_fixed_width_packed_values write_fixed32 write_fixed32_value
    write_fixed32_value_field write_fixed64 write_fixed64_value
    write_fixed64_value_field write_float write_float_field write_int32
    write_int32_field write_int64 write_int64_field write_message_field write_sfixed32
    write_sfixed32_field write_sfixed64 write_sfixed64_field write_sint32
    write_sint32_field write_sint64 write_sint64_field write_string_field write_tag
    write_uint32 write_uint32_field write_uint64 write_uint64_field write_varint
    write_varint_scalar
    """.split()
)


def cpp_identifier(name: str) -> str:
    """Return an injective, portable C++ spelling for a raw schema name."""

    if _CPP_IDENTIFIER.fullmatch(name) is None:
        return _encoded_identifier(name)
    if name in CPP_KEYWORDS:
        return f"{name}_"
    if (
        name.startswith("_")
        or "__" in name
        or name.startswith(CPP_RESERVED_IDENTIFIER_PREFIX)
        or name in _KEYWORD_ESCAPED_IDENTIFIERS
    ):
        return _encoded_identifier(name)
    return name


def _encoded_identifier(name: str) -> str:
    return f"{CPP_RESERVED_IDENTIFIER_PREFIX}{name.encode('utf-8').hex()}"


def cpp_derivable_identifier(name: str) -> str:
    """Return a portable identifier that remains safe when suffixed."""

    return cpp_emitted_derivable_identifier(cpp_identifier(name))


def cpp_emitted_derivable_identifier(name: str) -> str:
    """Make an already allocated spelling safe for additional suffixes."""

    if name.endswith("_"):
        return f"{name}{CPP_DERIVABLE_IDENTIFIER_SUFFIX}"
    return name


def cpp_pascal_identifier(name: str) -> str:
    ident = cpp_identifier(name)
    return ident[:1].upper() + ident[1:]


class CppNameKind(Enum):
    NAMESPACE = auto()
    TYPE = auto()
    TYPE_ALIAS = auto()
    FIELD_ACCESSOR = auto()
    CONSTANT = auto()
    ENUM_VALUE = auto()
    ONEOF_CASE_TYPE = auto()
    ONEOF_CASE_VALUE = auto()
    PUBLIC_FUNCTION = auto()
    PRIVATE_STORAGE = auto()
    IMPLEMENTATION = auto()


@dataclass(frozen=True, slots=True)
class EmittedNameMember:
    template: str = "{name}"
    kind: CppNameKind = CppNameKind.IMPLEMENTATION
    signature: str | None = None
    suffix: str | None = None

    def render(self, stem: str) -> str:
        if self.suffix is not None:
            if self.template != "{name}":
                raise ValueError("suffix-based emitted names cannot also use a template")
            if stem.endswith("_"):
                return f"{stem}{self.suffix}_"
            return f"{stem}_{self.suffix}"
        return self.template.format(name=stem)


@dataclass(frozen=True, slots=True)
class EmittedNameRequest:
    owner: str
    preferred: str
    members: tuple[EmittedNameMember, ...]
    hash_fallback: bool = False
    priority: int = 100


@dataclass(frozen=True, slots=True)
class EmittedNameUse:
    owner: str
    kind: CppNameKind
    signature: str | None


@dataclass(slots=True)
class EmittedNameScope:
    label: str
    uses: dict[str, list[EmittedNameUse]] = field(default_factory=dict)

    def reserve(
        self,
        name: str,
        *,
        owner: str,
        kind: CppNameKind,
        signature: str | None = None,
    ) -> None:
        use = EmittedNameUse(owner, kind, signature)
        if use in self.uses.get(name, ()):
            return
        if not self._can_add(name, use):
            existing = self.uses[name][0]
            raise ValueError(
                f"{self.label}: emitted name {name!r} from {owner!r} conflicts "
                f"with {existing.owner!r}"
            )
        self.uses.setdefault(name, []).append(use)

    def allocate(self, requests: Iterable[EmittedNameRequest]) -> dict[str, str]:
        allocated: dict[str, str] = {}
        for request in sorted(
            requests,
            key=lambda item: (item.priority, item.preferred, item.owner),
        ):
            for candidate in _allocation_candidates(
                request.preferred,
                request.owner,
                hash_fallback=request.hash_fallback,
            ):
                rendered = [
                    (
                        member.render(candidate),
                        EmittedNameUse(request.owner, member.kind, member.signature),
                    )
                    for member in request.members
                ]
                if self._can_add_all(rendered):
                    for name, use in rendered:
                        self.uses.setdefault(name, []).append(use)
                    allocated[request.owner] = candidate
                    break
        return allocated

    def _can_add_all(self, rendered: list[tuple[str, EmittedNameUse]]) -> bool:
        staged: dict[str, list[EmittedNameUse]] = {}
        for name, use in rendered:
            if not self._can_add(name, use, staged.get(name, [])):
                return False
            staged.setdefault(name, []).append(use)
        return True

    def _can_add(
        self,
        name: str,
        use: EmittedNameUse,
        staged: list[EmittedNameUse] | None = None,
    ) -> bool:
        if not _is_portable_identifier(name):
            return False
        existing = [*self.uses.get(name, ()), *(staged or ())]
        if not existing:
            return True
        if use.signature is None:
            return False
        return all(
            item.signature is not None and item.signature != use.signature
            for item in existing
        )


@dataclass(slots=True)
class EmittedNameAllocator:
    scopes: dict[str, EmittedNameScope] = field(default_factory=dict)

    def scope(self, label: str) -> EmittedNameScope:
        return self.scopes.setdefault(label, EmittedNameScope(label))


def _allocation_candidates(
    preferred: str, owner: str, *, hash_fallback: bool
) -> Iterable[str]:
    yield preferred
    digest = hashlib.sha256(owner.encode("utf-8")).hexdigest()[:12]
    base = preferred.rstrip("_") or "protocyte_name"
    hashed = f"{base}_protocyte_{digest}"
    if hash_fallback:
        yield hashed
    elif preferred.endswith("_"):
        yield f"{preferred}{CPP_DERIVABLE_IDENTIFIER_SUFFIX}"
    else:
        yield f"{preferred}_"
    if not hash_fallback:
        yield hashed
    suffix = 2
    while True:
        yield f"{base}_protocyte_{digest}_{suffix}"
        suffix += 1


def _is_portable_identifier(name: str) -> bool:
    return (
        _CPP_IDENTIFIER.fullmatch(name) is not None
        and name not in CPP_KEYWORDS
        and not name.startswith("_")
        and "__" not in name
    )
