from __future__ import annotations

from protocyte.names import (
    CppNameKind,
    EmittedNameMember,
    EmittedNameRequest,
    EmittedNameScope,
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
