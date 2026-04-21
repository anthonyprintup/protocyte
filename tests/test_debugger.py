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


@pytest.fixture
def protocyte_lldb_module(monkeypatch: pytest.MonkeyPatch):
    module_path = Path(__file__).resolve().parents[1] / "debugger" / "protocyte_lldb.py"
    fake_lldb = types.SimpleNamespace(SBCommandReturnObject=_FakeSBCommandReturnObject)
    monkeypatch.setitem(sys.modules, "lldb", fake_lldb)

    spec = importlib.util.spec_from_file_location("protocyte_lldb_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_register_oneof_formatters_reports_the_failing_command(protocyte_lldb_module) -> None:
    debugger = _FakeDebugger(fail_at=3, error="bad synthetic provider")

    error = protocyte_lldb_module.register_oneof_formatters(debugger, "^demo::Msg$")

    assert error == (
        "Protocyte oneof formatter registration failed while running "
        "\"type synthetic add -w protocyte-oneof -x -l "
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
