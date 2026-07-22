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


def cpp_identifier(name: str) -> str:
    """Return the existing portable spelling while allocation is centralized."""

    ident = normalized_cpp_identifier(name)
    if ident in CPP_KEYWORDS:
        return f"{ident}_"
    if ident.startswith("_") or "__" in ident:
        return _encoded_identifier(ident)
    return ident


def normalized_cpp_identifier(name: str) -> str:
    if not name:
        return "_"
    out = []
    for index, char in enumerate(name):
        valid = char == "_" or char.isalpha() or (char.isdigit() and index > 0)
        out.append(char if valid and ord(char) < 128 else "_")
    return "".join(out)


def _encoded_identifier(name: str) -> str:
    return f"{CPP_RESERVED_IDENTIFIER_PREFIX}{name.encode('ascii').hex()}"


def cpp_derivable_identifier(name: str) -> str:
    """Return a portable identifier that remains safe when suffixed."""

    ident = cpp_identifier(name)
    if ident.endswith("_"):
        return f"{ident}{CPP_DERIVABLE_IDENTIFIER_SUFFIX}"
    return ident


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

    def render(self, stem: str) -> str:
        return self.template.format(name=stem)


@dataclass(frozen=True, slots=True)
class EmittedNameRequest:
    owner: str
    preferred: str
    members: tuple[EmittedNameMember, ...]


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
        for request in sorted(requests, key=lambda item: (item.preferred, item.owner)):
            for candidate in _allocation_candidates(request.preferred, request.owner):
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


def _allocation_candidates(preferred: str, owner: str) -> Iterable[str]:
    yield preferred
    if preferred.endswith("_"):
        yield f"{preferred}{CPP_DERIVABLE_IDENTIFIER_SUFFIX}"
    else:
        yield f"{preferred}_"
    digest = hashlib.sha256(owner.encode("utf-8")).hexdigest()[:12]
    base = preferred.rstrip("_") or "protocyte_name"
    yield f"{base}_protocyte_{digest}"
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
