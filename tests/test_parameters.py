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

