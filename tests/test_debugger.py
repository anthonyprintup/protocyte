from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


class _FakeSBCommandReturnObject:
    def __init__(self) -> None:
        self.Clear()

    def Clear(self) -> None:
        self._succeeded = True
        self._error = ""

    def Succeeded(self) -> bool:
        return self._succeeded

    def GetError(self) -> str:
        return self._error

    def fail(self, error: str) -> None:
        self._succeeded = False
        self._error = error


class _FakeCommandInterpreter:
    def __init__(self, *, fail_at: int | None = None, error: str = "boom") -> None:
        self.fail_at = fail_at
        self.error = error
        self.commands: list[str] = []

    def HandleCommand(self, command: str, result: _FakeSBCommandReturnObject) -> None:
        self.commands.append(command)
        if self.fail_at is not None and len(self.commands) == self.fail_at:
            result.fail(self.error)


class _FakeDebugger:
    def __init__(self, *, fail_at: int | None = None, error: str = "boom") -> None:
        self.interpreter = _FakeCommandInterpreter(fail_at=fail_at, error=error)

    def GetCommandInterpreter(self) -> _FakeCommandInterpreter:
        return self.interpreter


class _FakeLLDBType:
    def __init__(
        self,
        name: str = "int",
        *,
        pointee: "_FakeLLDBType | None" = None,
        reference: bool = False,
        template_args: list["_FakeLLDBType"] | None = None,
        valid: bool = True,
    ) -> None:
        self.name = name
        self.pointee = pointee
        self.reference = reference
        self.template_args = template_args or []
        self.valid = valid

    def IsValid(self) -> bool:
        return self.valid

    def GetByteSize(self) -> int:
        return 16

    def GetPointeeType(self):
        return self.pointee or _InvalidLLDBType()

    def GetTemplateArgumentType(self, index: int):
        return (
            self.template_args[index]
            if 0 <= index < len(self.template_args)
            else _InvalidLLDBType()
        )

    def GetName(self) -> str:
        return self.name

    def GetDisplayTypeName(self) -> str:
        return self.name

    def IsReferenceType(self) -> bool:
        return self.reference


class _InvalidLLDBType(_FakeLLDBType):
    def __init__(self) -> None:
        super().__init__("<invalid>", valid=False)


class _FakeLLDBValue:
    def __init__(
        self,
        name: str = "value",
        *,
        children: dict[str, "_FakeLLDBValue"] | None = None,
        type_: _FakeLLDBType | None = None,
        unsigned: int = 0,
        address: int = 0,
        value: str | None = None,
    ) -> None:
        self._name = name
        self.children = children or {}
        self.type = type_ or _FakeLLDBType()
        self.unsigned = unsigned
        self.address = address
        self.value = value

    def GetNonSyntheticValue(self):
        return self

    def CreateValueFromAddress(self, name: str, _address: int, _value_type):
        return self.children[name]

    def GetChildMemberWithName(self, name: str):
        return self.children.get(name, _InvalidLLDBValue())

    def GetType(self):
        return self.type

    def GetTypeName(self) -> str:
        return self.type.GetName()

    def GetValueAsUnsigned(self, _default: int = 0) -> int:
        return self.unsigned

    def GetValue(self) -> str | None:
        return self.value

    def GetAddress(self) -> int:
        return self.address

    def GetNumChildren(self) -> int:
        return len(self.children)

    def GetChildAtIndex(self, index: int):
        return list(self.children.values())[index]

    def IsValid(self) -> bool:
        return True

    def GetName(self) -> str:
        return self._name


class _InvalidLLDBValue(_FakeLLDBValue):
    def __init__(self) -> None:
        super().__init__("<invalid>")

    def IsValid(self) -> bool:
        return False


@pytest.fixture
def protocyte_lldb_module(monkeypatch: pytest.MonkeyPatch):
    module_path = Path(__file__).resolve().parents[1] / "debugger" / "protocyte_lldb.py"
    fake_lldb = types.SimpleNamespace(
        SBCommandReturnObject=_FakeSBCommandReturnObject,
        SBType=_InvalidLLDBType,
        SBValue=_InvalidLLDBValue,
        LLDB_INVALID_ADDRESS=-1,
    )
    monkeypatch.setitem(sys.modules, "lldb", fake_lldb)

    spec = importlib.util.spec_from_file_location(
        "protocyte_lldb_under_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_register_oneof_formatters_reports_the_failing_command(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger(fail_at=3, error="bad synthetic provider")

    error = protocyte_lldb_module.register_oneof_formatters(debugger, "^demo::Msg$")

    assert error == (
        "Protocyte oneof formatter registration failed while running "
        '"type synthetic add -w protocyte-oneof -x -l '
        "protocyte_lldb.GeneratedMessageOneofSyntheticProvider '^demo::Msg$'\": "
        "bad synthetic provider"
    )


def test_lldb_init_module_raises_on_registration_failure(protocyte_lldb_module) -> None:
    debugger = _FakeDebugger(fail_at=2, error="type category define failed")

    with pytest.raises(
        RuntimeError,
        match=r"Protocyte formatter registration failed while running 'type category define protocyte': "
        r"type category define failed",
    ):
        protocyte_lldb_module.__lldb_init_module(debugger, {})


def test_hash_map_provider_reads_optional_entry_bucket_layout(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = _FakeLLDBValue("key")
    value = _FakeLLDBValue("value")
    renamed = _FakeLLDBValue("alpha =>")
    entry = _FakeLLDBValue("entry", children={"key": key, "value": value})
    bucket = _FakeLLDBValue("bucket[0]")
    root = _FakeLLDBValue("map", children={"bucket[0]": bucket})

    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])
    monkeypatch.setattr(
        protocyte_lldb_module,
        "_child",
        lambda value, name: value.GetChildMemberWithName(name),
    )
    monkeypatch.setattr(
        protocyte_lldb_module,
        "_vector_storage",
        lambda value: ("data", "size", "capacity"),
    )
    monkeypatch.setattr(
        protocyte_lldb_module,
        "_unsigned",
        lambda value, default=0: 1 if value == "size" else default,
    )
    monkeypatch.setattr(
        protocyte_lldb_module, "_pointee_type", lambda value: _FakeLLDBType()
    )
    monkeypatch.setattr(protocyte_lldb_module, "_pointer_value", lambda value: 0x1000)
    monkeypatch.setattr(
        protocyte_lldb_module, "_optional_payload", lambda value, name="value": entry
    )
    monkeypatch.setattr(protocyte_lldb_module, "_value_label", lambda value: "alpha")
    monkeypatch.setattr(
        protocyte_lldb_module, "_renamed_value", lambda parent, source, name: renamed
    )

    provider = protocyte_lldb_module.HashMapSyntheticProvider(root, {})

    assert provider.num_children() == 1
    assert provider.get_child_at_index(0) is renamed
    assert provider.get_child_index("alpha =>") == 0


def test_result_provider_dereferences_reference_value(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    int_type = _FakeLLDBType("int")
    result_type = _FakeLLDBType(
        "protocyte::Result<int &, protocyte::Error>",
        template_args=[_FakeLLDBType("int &", reference=True)],
    )
    pointer_value = _FakeLLDBValue(
        "value_", type_=_FakeLLDBType("int *", pointee=int_type), unsigned=0x1000
    )
    dereferenced = _FakeLLDBValue("value", type_=int_type, value="42")
    result = _FakeLLDBValue(
        "result",
        type_=result_type,
        children={
            "ok_": _FakeLLDBValue("ok_", unsigned=1),
            "value_": pointer_value,
            "value": dereferenced,
        },
    )
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])

    provider = protocyte_lldb_module.ResultSyntheticProvider(result, {})

    assert provider.num_children() == 1
    assert provider.get_child_index("value") == 0
    assert provider.get_child_at_index(0) is dereferenced


def test_result_provider_preserves_pointer_payload(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    int_type = _FakeLLDBType("int")
    pointer_type = _FakeLLDBType("int *", pointee=int_type)
    result_type = _FakeLLDBType(
        "protocyte::Result<int *, protocyte::Error>", template_args=[pointer_type]
    )
    pointer_value = _FakeLLDBValue("value_", type_=pointer_type, unsigned=0x1000)
    result = _FakeLLDBValue(
        "result",
        type_=result_type,
        children={
            "ok_": _FakeLLDBValue("ok_", unsigned=1),
            "value_": pointer_value,
        },
    )
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])

    provider = protocyte_lldb_module.ResultSyntheticProvider(result, {})

    assert provider.num_children() == 1
    assert provider.get_child_index("value") == 0
    assert provider.get_child_at_index(0) is pointer_value


def test_optional_reference_summary_and_child_use_backing_pointer(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    int_type = _FakeLLDBType("int")
    optional_type = _FakeLLDBType(
        "protocyte::Optional<int &>",
        template_args=[_FakeLLDBType("int &", reference=True)],
    )
    pointer_value = _FakeLLDBValue(
        "ptr_", type_=_FakeLLDBType("int *", pointee=int_type), unsigned=0x2000
    )
    dereferenced = _FakeLLDBValue("value", type_=int_type, value="7")
    optional = _FakeLLDBValue(
        "optional",
        type_=optional_type,
        children={
            "ptr_": pointer_value,
            "value": dereferenced,
        },
    )
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])

    provider = protocyte_lldb_module.OptionalSyntheticProvider(optional, {})

    assert protocyte_lldb_module.optional_summary(optional, {}) == "some"
    assert provider.num_children() == 1
    assert provider.get_child_index("value") == 0
    assert provider.get_child_at_index(0) is dereferenced
