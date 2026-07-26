from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
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
        self.output = ""

    def Succeeded(self) -> bool:
        return self._succeeded

    def GetError(self) -> str:
        return self._error

    def GetOutput(self) -> str:
        return self.output

    def SetError(self, error: str) -> None:
        self.fail(error)

    def PutCString(self, value: str) -> None:
        self.output = value

    def fail(self, error: str) -> None:
        self._succeeded = False
        self._error = error


class _FakeCommandInterpreter:
    def __init__(
        self,
        *,
        fail_at: int | None = None,
        fail_command_contains: str | None = None,
        error: str = "boom",
    ) -> None:
        self.fail_at = fail_at
        self.fail_command_contains = fail_command_contains
        self.error = error
        self.commands: list[str] = []

    def HandleCommand(self, command: str, result: _FakeSBCommandReturnObject) -> None:
        self.commands.append(command)
        if command == "target stop-hook list" and any(
            previous.startswith("target stop-hook add")
            for previous in self.commands[:-1]
        ):
            result.PutCString(
                "Hook: 1\n"
                "  State: enabled\n"
                "  Commands:\n"
                "      protocyte-register-frame-types\n"
            )
        if (
            self.fail_at is not None
            and len(self.commands) == self.fail_at
            or self.fail_command_contains is not None
            and self.fail_command_contains in command
        ):
            result.fail(self.error)


class _FakeDebugger:
    def __init__(
        self,
        *,
        fail_at: int | None = None,
        fail_command_contains: str | None = None,
        error: str = "boom",
    ) -> None:
        self.interpreter = _FakeCommandInterpreter(
            fail_at=fail_at,
            fail_command_contains=fail_command_contains,
            error=error,
        )
        self.target = _FakeTarget()

    def GetCommandInterpreter(self) -> _FakeCommandInterpreter:
        return self.interpreter


class _FakeTarget:
    def __init__(self) -> None:
        self.values: dict[str, _FakeLLDBValue] = {}

    def EvaluateExpression(self, expression: str):
        return self.values.get(expression, _InvalidLLDBValue())


class _FakeExecutionContext:
    def __init__(self, target: _FakeTarget, frame=None) -> None:
        self.target = target
        self.frame = frame

    def GetTarget(self) -> _FakeTarget:
        return self.target

    def GetFrame(self):
        return self.frame or _InvalidFrame()


class _FakeVariableList:
    def __init__(self, values: list["_FakeLLDBValue"]) -> None:
        self.values = values

    def GetSize(self) -> int:
        return len(self.values)

    def GetValueAtIndex(self, index: int):
        return self.values[index]


class _FakeFrame:
    def __init__(self, values: list["_FakeLLDBValue"]) -> None:
        self.values = values

    def IsValid(self) -> bool:
        return True

    def GetVariables(self, _arguments: bool, _locals: bool, _statics: bool, _in_scope_only: bool):
        return _FakeVariableList(self.values)


class _InvalidFrame:
    def IsValid(self) -> bool:
        return False


class _FakeLLDBType:
    def __init__(
        self,
        name: str = "int",
        *,
        pointee: "_FakeLLDBType | None" = None,
        reference: bool = False,
        template_args: list["_FakeLLDBType"] | None = None,
        canonical: "_FakeLLDBType | None" = None,
        unqualified: "_FakeLLDBType | None" = None,
        valid: bool = True,
        byte_size: int = 16,
    ) -> None:
        self.name = name
        self.pointee = pointee
        self.reference = reference
        self.template_args = template_args or []
        self.canonical = canonical
        self.unqualified = unqualified
        self.valid = valid
        self.byte_size = byte_size

    def IsValid(self) -> bool:
        return self.valid

    def GetByteSize(self) -> int:
        return self.byte_size

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

    def GetCanonicalType(self):
        return self.canonical or self

    def GetUnqualifiedType(self):
        return self.unqualified or self

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
        summary: str | None = None,
    ) -> None:
        self._name = name
        self.children = children or {}
        self.type = type_ or _FakeLLDBType()
        self.unsigned = unsigned
        self.address = address
        self.value = value
        self.summary = summary
        self.prefer_synthetic = True
        self.synthetic_children_generated = True
        self.parent: _FakeLLDBValue | None = None
        for child in self.children.values():
            child.parent = self

    def GetNonSyntheticValue(self):
        return self

    def Clone(self, name: str):
        cloned = _FakeLLDBValue(
            name,
            children=self.children,
            type_=self.type,
            unsigned=self.unsigned,
            address=self.address,
            value=self.value,
            summary=self.summary,
        )
        cloned.prefer_synthetic = self.prefer_synthetic
        cloned.synthetic_children_generated = self.synthetic_children_generated
        return cloned

    def CreateValueFromAddress(self, name: str, address: int, value_type):
        if name in self.children:
            return self.children[name]
        for child in self.children.values():
            if child.GetAddress() == address and child.GetType() is value_type:
                return _FakeLLDBValue(
                    name,
                    children=child.children,
                    type_=child.type,
                    unsigned=child.unsigned,
                    address=child.address,
                    value=child.value,
                    summary=child.summary,
                )
        return _FakeLLDBValue(name, type_=value_type, address=address)

    def CreateValueFromData(self, name: str, _data, value_type):
        if name in self.children:
            return self.children[name]
        if isinstance(_data, _FakeLLDBValue):
            return _FakeLLDBValue(
                name,
                children=_data.children,
                type_=_data.type,
                unsigned=_data.unsigned,
                address=_data.address,
                value=_data.value,
                summary=_data.summary,
            )
        return _FakeLLDBValue(name, type_=value_type)

    def GetChildMemberWithName(self, name: str):
        return self.children.get(name, _InvalidLLDBValue())

    def GetType(self):
        return self.type

    def GetData(self):
        return self

    def GetTypeName(self) -> str:
        return self.type.GetName()

    def GetValueAsUnsigned(self, _default: int = 0) -> int:
        return self.unsigned

    def GetValue(self) -> str | None:
        return self.value

    def GetSummary(self) -> str | None:
        return self.summary

    def GetAddress(self) -> int:
        return self.address

    def GetLoadAddress(self) -> int:
        return self.address

    def GetNumChildren(self) -> int:
        return len(self.children)

    def GetChildAtIndex(self, index: int):
        return list(self.children.values())[index]

    def IsValid(self) -> bool:
        return True

    def GetName(self) -> str:
        return self._name

    def GetParent(self):
        return self.parent or _InvalidLLDBValue()

    def SetPreferSyntheticValue(self, value: bool) -> None:
        self.prefer_synthetic = value

    def SetSyntheticChildrenGenerated(self, value: bool) -> None:
        self.synthetic_children_generated = value


class _InvalidLLDBValue(_FakeLLDBValue):
    def __init__(self) -> None:
        super().__init__("<invalid>")

    def IsValid(self) -> bool:
        return False


@pytest.fixture
def protocyte_lldb_module(monkeypatch: pytest.MonkeyPatch):
    module_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "protocyte"
        / "debugger"
        / "protocyte_lldb.py"
    )
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
    debugger = _FakeDebugger(fail_at=5, error="bad synthetic provider")

    error = protocyte_lldb_module.register_oneof_formatters(debugger, "^demo::Msg$")

    assert error == (
        "Protocyte oneof formatter registration failed while running "
        '"type synthetic add -w protocyte-oneof -x -l '
        "protocyte_lldb.GeneratedMessageOneofSyntheticProvider '^demo::Msg$'\": "
        "bad synthetic provider"
    )


def test_lldb_init_module_raises_on_registration_failure(protocyte_lldb_module) -> None:
    debugger = _FakeDebugger(fail_at=3, error="type category define failed")

    with pytest.raises(
        RuntimeError,
        match=r"Protocyte formatter registration failed while running 'type category define protocyte': "
        r"type category define failed",
    ):
        protocyte_lldb_module.__lldb_init_module(debugger, {})


def test_lldb_init_module_disables_category_before_deleting(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger()

    protocyte_lldb_module.__lldb_init_module(debugger, {})

    assert debugger.interpreter.commands[:3] == [
        "type category disable protocyte",
        "type category delete protocyte",
        "type category define protocyte",
    ]


def test_lldb_init_module_keeps_loading_when_recognizers_are_unsupported(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger(
        fail_command_contains="--recognizer-function",
        error="error: unknown or ambiguous option",
    )

    protocyte_lldb_module.__lldb_init_module(debugger, {})

    commands = debugger.interpreter.commands
    assert any("protocyte-oneof" in command for command in commands)
    assert any("protocyte-register-frame-types" in command for command in commands)
    assert any(command.startswith("target stop-hook add") for command in commands)


def test_lldb_init_module_registers_frame_stop_hook_once(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger()

    protocyte_lldb_module.__lldb_init_module(debugger, {})
    protocyte_lldb_module.__lldb_init_module(debugger, {})

    commands = debugger.interpreter.commands
    assert commands.count("target stop-hook list") == 2
    assert (
        commands.count(
            'target stop-hook add -o "protocyte-register-frame-types"'
        )
        == 1
    )


def test_real_lldb_reimport_registers_frame_stop_hook_once() -> None:
    lldb = os.environ.get("PROTOCYTE_TEST_LLDB") or shutil.which("lldb")
    if lldb is None:
        pytest.skip("LLDB is not installed")

    module_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "protocyte"
        / "debugger"
        / "protocyte_lldb.py"
    )
    import_command = f'command script import "{module_path.as_posix()}"'
    try:
        probe = subprocess.run(
            [
                lldb,
                "--no-lldbinit",
                "--batch",
                "-o",
                'script print("protocyte-lldb-python-ready")',
                "-o",
                "quit",
            ],
            cwd=module_path.parents[3],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            check=False,
        )
        if probe.returncode != 0 or "protocyte-lldb-python-ready" not in (
            probe.stdout + probe.stderr
        ):
            pytest.skip("LLDB Python scripting is unavailable")
        completed = subprocess.run(
            [
                lldb,
                "--no-lldbinit",
                "--batch",
                "-o",
                import_command,
                "-o",
                import_command,
                "-o",
                "target stop-hook list",
                "-o",
                "quit",
            ],
            cwd=module_path.parents[3],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"LLDB could not be launched: {exc}")

    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    hook_commands = [
        line.strip()
        for line in output.splitlines()
        if line.strip() == "protocyte-register-frame-types"
    ]
    assert hook_commands == ["protocyte-register-frame-types"], output


def test_real_lldb_result_summaries_distinguish_structured_error_type(
    tmp_path: Path,
) -> None:
    lldb = os.environ.get("PROTOCYTE_TEST_LLDB") or shutil.which("lldb")
    compiler = shutil.which("clang++") or shutil.which("c++")
    if lldb is None or compiler is None:
        pytest.skip("LLDB and a C++ compiler are required")

    root = Path(__file__).resolve().parents[1]
    module_path = root / "src" / "protocyte" / "debugger" / "protocyte_lldb.py"
    try:
        probe = subprocess.run(
            [
                lldb,
                "--no-lldbinit",
                "--batch",
                "-o",
                'script print("protocyte-lldb-python-ready")',
                "-o",
                "quit",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"LLDB could not be launched: {exc}")
    if probe.returncode != 0 or "protocyte-lldb-python-ready" not in (
        probe.stdout + probe.stderr
    ):
        pytest.skip("LLDB Python scripting is unavailable")

    source = tmp_path / "result_formatter.cpp"
    source_text = """\
#include <protocyte/runtime/runtime.hpp>

namespace demo {
    struct CollidingError {
        protocyte::ErrorCode code {};
        protocyte::usize offset {};
        protocyte::u32 field_number {};
        int detail {};
    };

    using ErrorAlias = protocyte::Error;
} // namespace demo

int main() {
    auto direct = protocyte::Result<int, demo::CollidingError> {
        protocyte::unexpected(demo::CollidingError {
            protocyte::ErrorCode::unsupported,
            901u,
            12u,
            91,
        }),
    };
    auto nested = protocyte::Result<void, demo::CollidingError> {
        protocyte::unexpected(demo::CollidingError {
            protocyte::ErrorCode::count_limit,
            902u,
            13u,
            92,
        }),
    };
    auto canonical = protocyte::Result<int> {
        protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 23u, 5u),
    };
    auto alias_nested = protocyte::Result<void, demo::ErrorAlias> {
        protocyte::unexpected(protocyte::Error {
            protocyte::ErrorCode::size_limit,
            24u,
            6u,
        }),
    };
    volatile int inspect_here = 0;
    return inspect_here + direct.error().detail + nested.error().detail +
           static_cast<int>(canonical.error().field_number) +
           static_cast<int>(alias_nested.error().field_number);
}
"""
    source.write_text(source_text, encoding="utf-8")
    breakpoint_line = next(
        index
        for index, line in enumerate(source_text.splitlines(), start=1)
        if "volatile int inspect_here" in line
    )
    executable = tmp_path / (
        "result_formatter.exe" if os.name == "nt" else "result_formatter"
    )
    compile_result = subprocess.run(
        [
            compiler,
            "-std=c++20",
            "-O0",
            "-g",
            "-fstandalone-debug",
            "-I",
            str(root / "src"),
            str(source),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=60,
        check=False,
    )
    assert compile_result.returncode == 0, (
        compile_result.stdout + compile_result.stderr
    )

    import_command = f'command script import "{module_path.as_posix()}"'
    result_commands = {
        "DIRECT": "direct",
        "NESTED": "nested",
        "CANONICAL": "canonical",
        "ALIAS": "alias_nested",
    }
    commands = [
        f'target create "{executable.as_posix()}"',
        import_command,
        (
            'type summary add --summary-string "collision(detail=${var.detail})" '
            "demo::CollidingError"
        ),
        f'breakpoint set --file "{source.name}" --line {breakpoint_line}',
        "run",
    ]
    for label, variable in result_commands.items():
        commands.append(
            "script import lldb, protocyte_lldb; "
            "frame=lldb.debugger.GetSelectedTarget().GetProcess()"
            ".GetSelectedThread().GetFrameAtIndex(0); "
            f'print("{label}=" + protocyte_lldb.result_summary('
            f'frame.FindVariable("{variable}"), {{}}))'
        )
    arguments = [lldb, "--no-lldbinit", "--batch"]
    for command in commands:
        arguments.extend(("-o", command))
    try:
        completed = subprocess.run(
            arguments,
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"LLDB could not be launched: {exc}")

    output = completed.stdout + completed.stderr
    if "Python scripting is not available" in output:
        pytest.skip("LLDB Python scripting is unavailable")
    assert completed.returncode == 0, output
    assert "DIRECT=err, error=collision(detail=91)" in output
    assert "NESTED=err, error=collision(detail=92)" in output
    assert "CANONICAL=err, code=" in output
    assert "offset=23, field=5" in output
    assert "ALIAS=err, code=" in output
    assert "offset=24, field=6" in output


def test_lldb_init_module_ignores_fresh_session_script_delete_errors(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger(
        fail_command_contains="command script delete",
        error="error: can only delete user defined commands, but no user defined commands found",
    )

    protocyte_lldb_module.__lldb_init_module(debugger, {})

    commands = debugger.interpreter.commands
    assert "command script add -f protocyte_lldb.protocyte_oneof protocyte-oneof" in commands
    assert (
        "command script add -f protocyte_lldb.protocyte_register_frame_types "
        "protocyte-register-frame-types"
    ) in commands


@pytest.mark.parametrize(
    ("type_name", "recognizer_name"),
    [
        ("protocyte::Bytes<protocyte::DefaultConfig>", "is_bytes_type"),
        ("class protocyte::Bytes<protocyte::DefaultConfig>", "is_bytes_type"),
        ("struct protocyte::String<protocyte::DefaultConfig>", "is_string_type"),
        ("protocyte::Span<int>", "is_span_type"),
        ("class protocyte::Vector<int, protocyte::DefaultConfig>", "is_vector_type"),
        (
            "struct protocyte::HashMap<int, int, protocyte::DefaultConfig>",
            "is_hash_map_type",
        ),
    ],
)
def test_runtime_type_recognizers_match_clion_lldb_type_names(
    protocyte_lldb_module, type_name: str, recognizer_name: str
) -> None:
    recognizer = getattr(protocyte_lldb_module, recognizer_name)

    assert recognizer(_FakeLLDBType(type_name), {})


def test_bytes_runtime_type_recognizer_rejects_other_templates(
    protocyte_lldb_module,
) -> None:
    assert not protocyte_lldb_module.is_bytes_type(
        _FakeLLDBType("protocyte::Vector<unsigned char, protocyte::DefaultConfig>"),
        {},
    )


def test_write_smoke_lldbinit_uses_smoke_project_relative_import(
    protocyte_lldb_module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_path = tmp_path / "repo" / "src" / "protocyte" / "debugger"
    module_path.mkdir(parents=True)
    smoke_path = tmp_path / "repo" / "tests" / "smoke"
    smoke_path.mkdir(parents=True)
    monkeypatch.setattr(
        protocyte_lldb_module, "__file__", str(module_path / "protocyte_lldb.py")
    )

    protocyte_lldb_module.write_smoke_lldbinit()

    assert (smoke_path / ".lldbinit").read_text(encoding="utf-8") == (
        "command script import ../../src/protocyte/debugger/protocyte_lldb.py\n"
        "protocyte-oneof '^.*test::ultimate::.*<.*>$'\n"
    )


def _child_names(provider) -> list[str]:
    return [
        provider.get_child_at_index(index).GetName()
        for index in range(provider.num_children())
    ]


def test_vector_provider_uses_stl_style_metadata_elements_and_raw_view(
    protocyte_lldb_module,
) -> None:
    int_type = _FakeLLDBType("int", byte_size=4)
    data = _FakeLLDBValue("data_", type_=_FakeLLDBType("int *", pointee=int_type), unsigned=0x1000)
    vector = _FakeLLDBValue(
        "values",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x2000, unsigned=0x2000),
            "data_": data,
            "size_": _FakeLLDBValue("size_", unsigned=2),
            "capacity_": _FakeLLDBValue("capacity_", unsigned=4),
        },
    )

    provider = protocyte_lldb_module.VectorSyntheticProvider(vector, {})

    assert protocyte_lldb_module.vector_summary(vector, {}) == "size=2 [0x2]"
    assert _child_names(provider) == ["context", "capacity", "[0]", "[1]", "Raw View"]
    raw_view = provider.get_child_at_index(4)
    assert [raw_view.GetChildAtIndex(index).GetName() for index in range(4)] == [
        "ctx_",
        "data_",
        "size_",
        "capacity_",
    ]
    assert raw_view.GetTypeName() == "int"
    assert not raw_view.prefer_synthetic
    assert not raw_view.synthetic_children_generated


def test_string_provider_uses_string_summary_metadata_elements_and_raw_view(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    char_type = _FakeLLDBType("char", byte_size=1)
    data = _FakeLLDBValue(
        "data_", type_=_FakeLLDBType("char *", pointee=char_type), unsigned=0x3000
    )
    storage = _FakeLLDBValue(
        "bytes_",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x4000, unsigned=0x4000),
            "data_": data,
            "size_": _FakeLLDBValue("size_", unsigned=2),
            "capacity_": _FakeLLDBValue("capacity_", unsigned=8),
        },
    )
    string_bytes = _FakeLLDBValue(
        "bytes_",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x4000, unsigned=0x4000),
            "bytes_": storage,
        },
    )
    string_value = _FakeLLDBValue(
        "name",
        children={"bytes_": string_bytes},
        type_=_FakeLLDBType("protocyte::String<Config>"),
    )
    monkeypatch.setattr(
        protocyte_lldb_module,
        "_read_byte_span",
        lambda value, data_value, size_value, limit=64: (b"Hi", 2, 0x3000),
    )

    provider = protocyte_lldb_module.ByteSpanSyntheticProvider(string_value, {})

    assert (
        protocyte_lldb_module.string_summary(string_value, {})
        == 'size=2 [0x2], value="Hi", hex=[48 69]'
    )
    assert _child_names(provider) == ["context", "capacity", "[0]", "[1]", "Raw View"]
    raw_view = provider.get_child_at_index(4)
    assert raw_view.GetTypeName() == "protocyte::String<Config>"
    assert not raw_view.prefer_synthetic
    assert not raw_view.synthetic_children_generated
    assert raw_view.GetNumChildren() == 1
    assert raw_view.GetChildAtIndex(0).GetName() == "bytes_"

    raw_provider = protocyte_lldb_module.ByteSpanSyntheticProvider(raw_view, {})
    assert protocyte_lldb_module.string_summary(raw_view, {}) is None
    assert _child_names(raw_provider) == ["bytes_"]


def test_nested_raw_view_child_keeps_recursive_raw_mode(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    char_type = _FakeLLDBType("char", byte_size=1)
    storage = _FakeLLDBValue(
        "bytes_",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x4100, unsigned=0x4100),
            "data_": _FakeLLDBValue(
                "data_",
                type_=_FakeLLDBType("char *", pointee=char_type),
                unsigned=0x3100,
            ),
            "size_": _FakeLLDBValue("size_", unsigned=2),
            "capacity_": _FakeLLDBValue("capacity_", unsigned=8),
        },
        type_=_FakeLLDBType(
            "protocyte::Vector<unsigned char, protocyte::DefaultConfig>"
        ),
    )
    string_bytes = _FakeLLDBValue(
        "bytes_",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x4000, unsigned=0x4000),
            "bytes_": storage,
        },
        type_=_FakeLLDBType("protocyte::Bytes<protocyte::DefaultConfig>"),
    )
    string_value = _FakeLLDBValue(
        "name",
        children={"bytes_": string_bytes},
        type_=_FakeLLDBType("protocyte::String<protocyte::DefaultConfig>"),
    )
    monkeypatch.setattr(
        protocyte_lldb_module,
        "_read_byte_span",
        lambda value, data_value, size_value, limit=64: (b"Hi", 2, 0x3100),
    )

    provider = protocyte_lldb_module.ByteSpanSyntheticProvider(string_value, {})
    raw_string = provider.get_child_at_index(4)
    raw_bytes = raw_string.GetChildAtIndex(0)

    raw_bytes_provider = protocyte_lldb_module.ByteSpanSyntheticProvider(raw_bytes, {})

    assert protocyte_lldb_module.bytes_summary(raw_bytes, {}) is None
    assert _child_names(raw_bytes_provider) == ["ctx_", "bytes_"]


@pytest.mark.parametrize(
    "type_name",
    [
        "class protocyte::String<Config>",
        "struct protocyte::String<Config>",
    ],
)
def test_string_provider_normalizes_tagged_lldb_type_names(
    protocyte_lldb_module, type_name: str
) -> None:
    char_type = _FakeLLDBType("char", byte_size=1)
    storage = _FakeLLDBValue(
        "bytes_",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x4000),
            "data_": _FakeLLDBValue(
                "data_",
                type_=_FakeLLDBType("char *", pointee=char_type),
                unsigned=0x3000,
            ),
            "size_": _FakeLLDBValue("size_", unsigned=2),
            "capacity_": _FakeLLDBValue("capacity_", unsigned=8),
        },
    )
    string_value = _FakeLLDBValue(
        "name",
        children={
            "bytes_": _FakeLLDBValue(
                "bytes_",
                children={
                    "ctx_": _FakeLLDBValue("ctx_", address=0x4000),
                    "bytes_": storage,
                },
            )
        },
        type_=_FakeLLDBType(type_name),
    )

    provider = protocyte_lldb_module.ByteSpanSyntheticProvider(string_value, {})

    assert provider.size == 2
    assert _child_names(provider) == [
        "context",
        "capacity",
        "[0]",
        "[1]",
        "Raw View",
    ]


@pytest.mark.parametrize(
    "type_name",
    [
        "class protocyte::Bytes<Config>",
        "struct protocyte::Bytes<Config>",
    ],
)
def test_bytes_provider_normalizes_tagged_lldb_type_names(
    protocyte_lldb_module, type_name: str
) -> None:
    byte_type = _FakeLLDBType("unsigned char", byte_size=1)
    bytes_value = _FakeLLDBValue(
        "bytes",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x4000),
            "bytes_": _FakeLLDBValue(
                "bytes_",
                children={
                    "data_": _FakeLLDBValue(
                        "data_",
                        type_=_FakeLLDBType("unsigned char *", pointee=byte_type),
                        unsigned=0x3000,
                    ),
                    "size_": _FakeLLDBValue("size_", unsigned=2),
                    "capacity_": _FakeLLDBValue("capacity_", unsigned=8),
                },
            )
        },
        type_=_FakeLLDBType(type_name),
    )

    provider = protocyte_lldb_module.ByteSpanSyntheticProvider(bytes_value, {})

    assert provider.size == 2
    assert _child_names(provider) == [
        "context",
        "capacity",
        "[0]",
        "[1]",
        "Raw View",
    ]


def test_vector_raw_view_does_not_recurse_into_another_raw_view(
    protocyte_lldb_module,
) -> None:
    int_type = _FakeLLDBType("int", byte_size=4)
    vector = _FakeLLDBValue(
        "values",
        children={
            "ctx_": _FakeLLDBValue("ctx_", address=0x2000, unsigned=0x2000),
            "data_": _FakeLLDBValue(
                "data_",
                type_=_FakeLLDBType("int *", pointee=int_type),
                unsigned=0x1000,
            ),
            "size_": _FakeLLDBValue("size_", unsigned=2),
            "capacity_": _FakeLLDBValue("capacity_", unsigned=4),
        },
        type_=_FakeLLDBType("protocyte::Vector<int, protocyte::DefaultConfig>"),
    )

    provider = protocyte_lldb_module.VectorSyntheticProvider(vector, {})
    raw_view = provider.get_child_at_index(4)
    raw_provider = protocyte_lldb_module.VectorSyntheticProvider(raw_view, {})

    assert protocyte_lldb_module.vector_summary(raw_view, {}) is None
    assert _child_names(raw_provider) == ["ctx_", "data_", "size_", "capacity_"]


def test_span_provider_registers_and_displays_indexed_children_with_raw_view(
    protocyte_lldb_module,
) -> None:
    int_type = _FakeLLDBType("int", byte_size=4)
    span = _FakeLLDBValue(
        "view",
        children={
            "data_": _FakeLLDBValue(
                "data_", type_=_FakeLLDBType("int *", pointee=int_type), unsigned=0x5000
            ),
            "size_": _FakeLLDBValue("size_", unsigned=2),
        },
        type_=_FakeLLDBType("protocyte::Span<int>"),
    )

    provider = protocyte_lldb_module.ByteSpanSyntheticProvider(span, {})

    assert protocyte_lldb_module.span_summary(span, {}) == "size=2 [0x2]"
    assert _child_names(provider) == ["[0]", "[1]", "Raw View"]


def test_reader_and_writer_summaries_use_absolute_slice_positions(
    protocyte_lldb_module,
) -> None:
    reader = _FakeLLDBValue(
        children={
            "pos_": _FakeLLDBValue("pos_", unsigned=2),
            "base_offset_": _FakeLLDBValue("base_offset_", unsigned=40),
            "size_": _FakeLLDBValue("size_", unsigned=10),
        }
    )
    writer = _FakeLLDBValue(
        children={
            "pos_": _FakeLLDBValue("pos_", unsigned=3),
            "base_offset_": _FakeLLDBValue("base_offset_", unsigned=70),
            "capacity_": _FakeLLDBValue("capacity_", unsigned=12),
        }
    )
    limited = _FakeLLDBValue(
        children={
            "pos_": _FakeLLDBValue("pos_", unsigned=4),
            "remaining_": _FakeLLDBValue("remaining_", unsigned=6),
        }
    )

    assert protocyte_lldb_module.slice_reader_summary(reader, {}) == (
        "pos=42, size=10, remaining=8"
    )
    assert protocyte_lldb_module.slice_writer_summary(writer, {}) == (
        "pos=73, capacity=12, remaining=9"
    )
    assert protocyte_lldb_module.limited_reader_summary(limited, {}) == (
        "consumed=4, remaining=6"
    )


def test_oneof_provider_reads_suffixed_union_storage(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])
    payload = _FakeLLDBValue("text_", address=-1, value='"hello"')
    message = _FakeLLDBValue(
        "message",
        children={
            "choice_case_": _FakeLLDBValue(
                "choice_case_",
                address=-1,
                value="demo::Carrier::ChoiceCase::text",
            ),
            "choice_": _FakeLLDBValue("choice_", children={"text_": payload}),
        },
    )

    provider = protocyte_lldb_module.GeneratedMessageOneofSyntheticProvider(
        message, {}
    )

    assert _child_names(provider) == ["choice_case_", "choice_", "choice: text"]
    assert provider.get_child_at_index(2).GetValue() == '"hello"'


def test_oneof_provider_does_not_read_legacy_unsuffixed_union_storage(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])
    message = _FakeLLDBValue(
        "message",
        children={
            "choice_case_": _FakeLLDBValue(
                "choice_case_",
                address=-1,
                value="demo::Carrier::ChoiceCase::text",
            ),
            "choice": _FakeLLDBValue(
                "choice",
                children={"text_": _FakeLLDBValue("text_", address=-1, value='"hello"')},
            ),
        },
    )

    provider = protocyte_lldb_module.GeneratedMessageOneofSyntheticProvider(
        message, {}
    )

    assert _child_names(provider) == ["choice_case_", "choice", "choice: text"]
    assert provider.get_child_at_index(2).GetValue() == "demo::Carrier::ChoiceCase::text"


def test_oneof_provider_does_not_read_legacy_top_level_payload(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])
    message = _FakeLLDBValue(
        "message",
        children={
            "choice_case_": _FakeLLDBValue(
                "choice_case_",
                address=-1,
                value="demo::Carrier::ChoiceCase::text",
            ),
            "text_": _FakeLLDBValue("text_", address=-1, value='"hello"'),
        },
    )

    provider = protocyte_lldb_module.GeneratedMessageOneofSyntheticProvider(message, {})

    assert _child_names(provider) == ["choice_case_", "text_", "choice: text"]
    assert (
        provider.get_child_at_index(2).GetValue() == "demo::Carrier::ChoiceCase::text"
    )


def test_lldb_init_module_registers_span_formatter(protocyte_lldb_module) -> None:
    debugger = _FakeDebugger()

    protocyte_lldb_module.__lldb_init_module(debugger, {})

    commands = debugger.interpreter.commands
    assert any(
        "span_summary --recognizer-function protocyte_lldb.is_span_type" in command
        for command in commands
    )
    assert any(
        "ByteSpanSyntheticProvider --recognizer-function protocyte_lldb.is_span_type"
        in command
        for command in commands
    )


def test_lldb_init_module_registers_broad_bytes_formatter(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger()

    protocyte_lldb_module.__lldb_init_module(debugger, {})

    commands = debugger.interpreter.commands
    assert any(
        "bytes_summary --recognizer-function protocyte_lldb.is_bytes_type" in command
        for command in commands
    )
    assert any(
        "bytes_summary 'protocyte::Bytes<protocyte::DefaultConfig>'" in command
        for command in commands
    )
    assert any(
        "ByteSpanSyntheticProvider --recognizer-function protocyte_lldb.is_bytes_type"
        in command
        for command in commands
    )
    assert any("protocyte-formatters" in command for command in commands)
    assert any("protocyte-register-type" in command for command in commands)


def test_lldb_init_module_does_not_register_removed_byte_views(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger()

    protocyte_lldb_module.__lldb_init_module(debugger, {})

    assert all("ByteView" not in command for command in debugger.interpreter.commands)
    assert not hasattr(protocyte_lldb_module, "byte_view_summary")
    assert not hasattr(protocyte_lldb_module, "mutable_byte_view_summary")


def test_register_type_command_adds_exact_bytes_formatter(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger()
    value = _FakeLLDBValue(
        "overflow", type_=_FakeLLDBType("protocyte::Bytes<protocyte::DefaultConfig>")
    )
    debugger.target.values["overflow"] = value
    result = _FakeSBCommandReturnObject()

    protocyte_lldb_module.protocyte_register_type(
        debugger, "overflow", _FakeExecutionContext(debugger.target), result, {}
    )

    assert result.Succeeded()
    assert debugger.interpreter.commands == [
        "type summary add -w protocyte -p -F protocyte_lldb.bytes_summary "
        "'protocyte::Bytes<protocyte::DefaultConfig>'",
        "type synthetic add -w protocyte -l protocyte_lldb.ByteSpanSyntheticProvider "
        "'protocyte::Bytes<protocyte::DefaultConfig>'",
        "type category enable protocyte",
    ]


def test_register_frame_types_adds_exact_formatter_for_visible_bytes(
    protocyte_lldb_module,
) -> None:
    debugger = _FakeDebugger()
    value = _FakeLLDBValue(
        "overflow",
        type_=_FakeLLDBType("class protocyte::Bytes<protocyte::DefaultConfig>"),
    )
    frame = _FakeFrame([value])
    result = _FakeSBCommandReturnObject()

    protocyte_lldb_module.protocyte_register_frame_types(
        debugger, "verbose", _FakeExecutionContext(debugger.target, frame), result, {}
    )

    assert result.Succeeded()
    assert debugger.interpreter.commands == [
        "type summary add -w protocyte -p -F protocyte_lldb.bytes_summary "
        "'protocyte::Bytes<protocyte::DefaultConfig>'",
        "type synthetic add -w protocyte -l protocyte_lldb.ByteSpanSyntheticProvider "
        "'protocyte::Bytes<protocyte::DefaultConfig>'",
        "type category enable protocyte",
    ]
    assert result.output == (
        "registered Protocyte formatter types: "
        "protocyte::Bytes<protocyte::DefaultConfig>"
    )


def test_hash_map_provider_reads_optional_entry_bucket_layout(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = _FakeLLDBValue("key")
    value = _FakeLLDBValue("value")
    renamed = _FakeLLDBValue("alpha =>")
    entry = _FakeLLDBValue("entry", children={"key": key, "value": value})
    bucket = _FakeLLDBValue("bucket[0]")
    root = _FakeLLDBValue("map", children={"bucket[0]": bucket})

    monkeypatch.setattr(
        protocyte_lldb_module, "_raw_children", lambda value: [_FakeLLDBValue("Raw View")]
    )
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
        protocyte_lldb_module,
        "_renamed_value",
        lambda parent, source, name: renamed
        if name == "alpha =>"
        else _FakeLLDBValue(name),
    )

    provider = protocyte_lldb_module.HashMapSyntheticProvider(root, {})

    assert protocyte_lldb_module.hash_map_summary(root, {}) == "size=0 [0x0], buckets=1 [0x1]"
    assert provider.num_children() == 3
    assert provider.get_child_at_index(0) is renamed
    assert provider.get_child_index("alpha =>") == 0
    assert provider.get_child_at_index(1).GetName() == "buckets"
    assert provider.get_child_at_index(2).GetName() == "Raw View"


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


def test_status_and_void_result_summaries_use_nested_error_storage(
    protocyte_lldb_module,
) -> None:
    error = _FakeLLDBValue(
        "error_",
        type_=_FakeLLDBType("protocyte::Error"),
        children={
            "code": _FakeLLDBValue(
                "code", value="protocyte::ErrorCode::invalid_argument"
            ),
            "offset": _FakeLLDBValue("offset", unsigned=17),
            "field_number": _FakeLLDBValue("field_number", unsigned=3),
        },
    )
    success = _FakeLLDBValue(
        "status",
        children={
            "storage_": _FakeLLDBValue("storage_"),
            "ok_": _FakeLLDBValue("ok_", unsigned=1),
        },
    )
    failure = _FakeLLDBValue(
        "status",
        children={
            "storage_": _FakeLLDBValue(
                "storage_", children={"error_": error}
            ),
            "ok_": _FakeLLDBValue("ok_", unsigned=0),
        },
    )

    assert protocyte_lldb_module.status_summary(success, {}) == "ok"
    assert protocyte_lldb_module.status_summary(failure, {}) == (
        "code=protocyte::ErrorCode::invalid_argument, offset=17, field=3"
    )
    assert protocyte_lldb_module.result_summary(success, {}) == "ok"
    assert protocyte_lldb_module.result_summary(failure, {}) == (
        "err, code=protocyte::ErrorCode::invalid_argument, offset=17, field=3"
    )


@pytest.mark.parametrize("nested", [False, True], ids=["direct", "nested"])
def test_result_summary_preserves_error_shaped_custom_aggregate(
    protocyte_lldb_module, nested: bool
) -> None:
    error = _FakeLLDBValue(
        "error_",
        type_=_FakeLLDBType("demo::CollidingError"),
        summary="collision(detail=91)",
        children={
            "code": _FakeLLDBValue("code", value="demo::Failure::timeout"),
            "offset": _FakeLLDBValue("offset", unsigned=900),
            "field_number": _FakeLLDBValue("field_number", unsigned=12),
            "detail": _FakeLLDBValue("detail", unsigned=91),
        },
    )
    error_children = (
        {"storage_": _FakeLLDBValue("storage_", children={"error_": error})}
        if nested
        else {"error_": error}
    )
    failure = _FakeLLDBValue(
        "result",
        type_=_FakeLLDBType(
            "protocyte::Result<void, demo::CollidingError>"
            if nested
            else "protocyte::Result<int, demo::CollidingError>"
        ),
        children={**error_children, "ok_": _FakeLLDBValue("ok_", unsigned=0)},
    )

    assert protocyte_lldb_module.result_summary(failure, {}) == (
        "err, error=collision(detail=91)"
    )


@pytest.mark.parametrize("nested", [False, True], ids=["direct", "nested"])
def test_result_summary_recognizes_canonicalized_error_alias(
    protocyte_lldb_module, nested: bool
) -> None:
    canonical_error = _FakeLLDBType("struct protocyte::Error")
    error = _FakeLLDBValue(
        "error_",
        type_=_FakeLLDBType("demo::ErrorAlias", canonical=canonical_error),
        children={
            "code": _FakeLLDBValue(
                "code", value="protocyte::ErrorCode::invalid_argument"
            ),
            "offset": _FakeLLDBValue("offset", unsigned=23),
            "field_number": _FakeLLDBValue("field_number", unsigned=5),
        },
    )
    error_children = (
        {"storage_": _FakeLLDBValue("storage_", children={"error_": error})}
        if nested
        else {"error_": error}
    )
    failure = _FakeLLDBValue(
        "result",
        children={**error_children, "ok_": _FakeLLDBValue("ok_", unsigned=0)},
    )

    assert protocyte_lldb_module.result_summary(failure, {}) == (
        "err, code=protocyte::ErrorCode::invalid_argument, offset=23, field=5"
    )


@pytest.mark.parametrize(
    ("error_value", "expected"),
    [
        (_FakeLLDBValue("error_", value="47", unsigned=47), "err, error=47"),
        (
            _FakeLLDBValue(
                "error_",
                value="demo::Failure::unavailable",
                type_=_FakeLLDBType("demo::Failure"),
            ),
            "err, error=demo::Failure::unavailable",
        ),
        (
            _FakeLLDBValue(
                "error_",
                summary='"connection refused"',
                type_=_FakeLLDBType("demo::Failure"),
            ),
            'err, error="connection refused"',
        ),
    ],
)
def test_void_result_summary_preserves_arbitrary_error_values(
    protocyte_lldb_module, error_value: _FakeLLDBValue, expected: str
) -> None:
    failure = _FakeLLDBValue(
        "result",
        type_=_FakeLLDBType("protocyte::Result<void, demo::Failure>"),
        children={
            "storage_": _FakeLLDBValue(
                "storage_", children={"error_": error_value}
            ),
            "ok_": _FakeLLDBValue("ok_", unsigned=0),
        },
    )

    assert protocyte_lldb_module.result_summary(failure, {}) == expected


def test_value_result_summary_preserves_arbitrary_error_value(
    protocyte_lldb_module,
) -> None:
    failure = _FakeLLDBValue(
        "result",
        type_=_FakeLLDBType("protocyte::Result<int, unsigned int>"),
        children={
            "error_": _FakeLLDBValue("error_", value="91", unsigned=91),
            "ok_": _FakeLLDBValue("ok_", unsigned=0),
        },
    )

    assert protocyte_lldb_module.result_summary(failure, {}) == "err, error=91"


def test_void_result_provider_uses_nested_error_and_omits_success_value(
    protocyte_lldb_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    void_result_type = _FakeLLDBType(
        "protocyte::Result<void, protocyte::Error>",
        template_args=[_FakeLLDBType("void")],
    )
    success = _FakeLLDBValue(
        "result",
        type_=void_result_type,
        children={
            "storage_": _FakeLLDBValue("storage_"),
            "ok_": _FakeLLDBValue("ok_", unsigned=1),
        },
    )
    error = _FakeLLDBValue("error_", address=0x2000)
    failure = _FakeLLDBValue(
        "result",
        type_=void_result_type,
        children={
            "storage_": _FakeLLDBValue(
                "storage_", children={"error_": error}
            ),
            "ok_": _FakeLLDBValue("ok_", unsigned=0),
        },
    )
    renamed_error = _FakeLLDBValue("error")
    monkeypatch.setattr(protocyte_lldb_module, "_raw_children", lambda value: [])
    monkeypatch.setattr(
        protocyte_lldb_module,
        "_renamed_value",
        lambda parent, source, name: renamed_error
        if parent is failure and source is error and name == "error"
        else _InvalidLLDBValue(),
    )

    success_provider = protocyte_lldb_module.ResultSyntheticProvider(success, {})
    failure_provider = protocyte_lldb_module.ResultSyntheticProvider(failure, {})

    assert success_provider.num_children() == 0
    assert success_provider.get_child_index("value") == -1
    assert success_provider.get_child_index("error") == -1
    assert not success_provider.get_child_at_index(0).IsValid()
    assert failure_provider.num_children() == 1
    assert failure_provider.get_child_index("value") == -1
    assert failure_provider.get_child_index("error") == 0
    assert failure_provider.get_child_at_index(0) is renamed_error


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
