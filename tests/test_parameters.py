import pytest

from protocyte.errors import ProtocyteError
from protocyte.parameters import parse_parameter


def test_parse_runtime_emit_with_prefix() -> None:
    options = parse_parameter("runtime=emit:kernel/protocyte,namespace=drv::wire,include_prefix=generated")

    assert options.emit_runtime is True
    assert options.runtime_prefix == "kernel/protocyte"
    assert options.namespace_prefix == "drv::wire"
    assert options.include_prefix == "generated"


def test_parse_defaults_to_no_runtime_emission() -> None:
    options = parse_parameter("")

    assert options.emit_runtime is False
    assert options.runtime_prefix == "protocyte/runtime"
    assert options.namespace_prefix == ""
    assert options.clang_format is None
    assert options.clang_format_config is None


def test_parse_accepts_clang_format_options() -> None:
    options = parse_parameter("clang_format=custom-format,clang_format_config=configs/protocyte.style")

    assert options.clang_format == "custom-format"
    assert options.clang_format_config == "configs/protocyte.style"


def test_rejects_duplicate_parameters() -> None:
    with pytest.raises(ProtocyteError, match="duplicate protocyte parameter: runtime"):
        parse_parameter("runtime=emit,runtime=omit")


def test_rejects_namespace_alias_conflicts() -> None:
    with pytest.raises(ProtocyteError, match="namespace and namespace_prefix are aliases; specify only one"):
        parse_parameter("namespace=left,namespace_prefix=right")


def test_rejects_bare_tokens_without_equals() -> None:
    with pytest.raises(ProtocyteError, match=r"invalid protocyte parameter 'runtime'; expected key=value"):
        parse_parameter("runtime")


def test_rejects_unknown_parameters() -> None:
    with pytest.raises(ProtocyteError, match=r"unknown protocyte parameter\(s\): debug"):
        parse_parameter("debug=true")
