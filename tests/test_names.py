from __future__ import annotations

from pathlib import Path
import re
from shutil import which
import subprocess

import pytest

from protocyte.names import (
    CppNameKind,
    EmittedNameMember,
    EmittedNameRequest,
    EmittedNameScope,
    PROTOCYTE_RUNTIME_CPP_SYMBOLS,
    cpp_emitted_derivable_identifier,
    cpp_identifier,
)


def test_allocator_is_independent_of_request_order() -> None:
    requests = [
        EmittedNameRequest(
            owner=owner,
            preferred="value",
            members=(EmittedNameMember(kind=CppNameKind.TYPE),),
        )
        for owner in ("demo.Z", "demo.A")
    ]

    forward = EmittedNameScope("demo").allocate(requests)
    reverse = EmittedNameScope("demo").allocate(reversed(requests))

    assert forward == reverse == {"demo.A": "value", "demo.Z": "value_"}


def test_allocator_understands_function_overloads() -> None:
    scope = EmittedNameScope("demo.Message")
    scope.reserve(
        "serialize",
        owner="generated serialize helper",
        kind=CppNameKind.PUBLIC_FUNCTION,
        signature="writer",
    )

    allocated = scope.allocate(
        [
            EmittedNameRequest(
                owner="demo.Message.serialize",
                preferred="serialize",
                members=(
                    EmittedNameMember(
                        kind=CppNameKind.FIELD_ACCESSOR,
                        signature="nullary-const",
                    ),
                ),
            )
        ]
    )

    assert allocated == {"demo.Message.serialize": "serialize"}


def test_allocator_moves_nullary_field_collision_as_a_group() -> None:
    scope = EmittedNameScope("demo.Message")
    scope.reserve(
        "context",
        owner="generated context helper",
        kind=CppNameKind.PUBLIC_FUNCTION,
        signature="nullary-const",
    )

    allocated = scope.allocate(
        [
            EmittedNameRequest(
                owner="demo.Message.context",
                preferred="context",
                members=(
                    EmittedNameMember(
                        kind=CppNameKind.FIELD_ACCESSOR,
                        signature="nullary-const",
                    ),
                    EmittedNameMember(
                        "set_{name}",
                        CppNameKind.FIELD_ACCESSOR,
                        "value",
                    ),
                ),
            )
        ]
    )

    assert allocated == {"demo.Message.context": "context_"}
    assert "set_context_" in scope.uses


def test_allocator_priority_applies_to_derived_name_collisions() -> None:
    scope = EmittedNameScope("message demo.Message")

    allocated = scope.allocate(
        (
            EmittedNameRequest(
                owner="nested:clear_value",
                preferred="clear_value",
                members=(EmittedNameMember(kind=CppNameKind.TYPE),),
                priority=20,
            ),
            EmittedNameRequest(
                owner="field:value",
                preferred="value",
                members=(
                    EmittedNameMember(kind=CppNameKind.FIELD_ACCESSOR),
                    EmittedNameMember(
                        template="clear_{name}", kind=CppNameKind.FIELD_ACCESSOR
                    ),
                ),
                priority=10,
            ),
        )
    )

    assert allocated == {
        "field:value": "value",
        "nested:clear_value": "clear_value_",
    }


@pytest.mark.parametrize(
    ("stem", "expected"),
    [("Mode", "Mode_ARRAYSIZE"), ("Mode_", "Mode_ARRAYSIZE_")],
)
def test_suffix_member_rendering_stays_portable_and_injective(
    stem: str, expected: str
) -> None:
    member = EmittedNameMember(
        kind=CppNameKind.CONSTANT,
        suffix="ARRAYSIZE",
    )

    assert member.render(stem) == expected


def test_cpp_identifier_encoding_is_injective() -> None:
    raw_names = (
        "class",
        "class_",
        "cap-value",
        "cap_value",
        "_Private",
        "proto__reserved",
        "protocyte_escaped_5f",
        "",
        "1",
    )

    emitted = [cpp_identifier(name) for name in raw_names]

    assert len(set(emitted)) == len(raw_names)
    assert emitted[0] == "class_"


def test_allocated_escape_prefix_is_not_encoded_again_for_derived_names() -> None:
    assert (
        cpp_emitted_derivable_identifier("protocyte_escaped_5f")
        == "protocyte_escaped_5f"
    )
    assert cpp_emitted_derivable_identifier("context_") == "context_protocyte"


def test_runtime_symbol_inventory_covers_root_types_and_aliases() -> None:
    runtime = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "protocyte"
        / "runtime"
        / "runtime.hpp"
    ).read_text(encoding="utf-8")
    runtime = runtime.split("namespace protocyte {", 1)[1].split(
        "} // namespace protocyte", 1
    )[0]
    declarations = re.findall(
        r"(?m)^ {4}(?! )(?:(?:template<[^\n]+> )?"
        r"(?:struct|class|enum(?: class| struct)?)|using) "
        r"([A-Za-z][A-Za-z0-9_]*)",
        runtime,
    )

    assert set(declarations) <= PROTOCYTE_RUNTIME_CPP_SYMBOLS
    assert "Span" in declarations


def test_runtime_symbol_inventory_matches_clang_ast() -> None:
    clang = which("clang++")
    if clang is None:
        pytest.skip("clang++ is required for the complete runtime-symbol drift check")
    runtime = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "protocyte"
        / "runtime"
        / "runtime.hpp"
    )

    result = subprocess.run(
        [
            clang,
            "-std=c++20",
            "-DPROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1",
            "-Xclang",
            "-ast-dump",
            "-Xclang",
            "-ast-dump-filter=protocyte::",
            "-fsyntax-only",
            str(runtime),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    declarations = set(
        re.findall(
            r"(?m)^Dumping protocyte::([A-Za-z_][A-Za-z0-9_]*):$",
            result.stdout,
        )
    )

    assert declarations <= PROTOCYTE_RUNTIME_CPP_SYMBOLS
    assert PROTOCYTE_RUNTIME_CPP_SYMBOLS - declarations <= {"format_as"}
