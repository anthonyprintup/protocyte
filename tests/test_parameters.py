import pytest

from protocyte.errors import ProtocyteError
from protocyte.parameters import GeneratorOptions, parse_parameter


def test_parse_runtime_emit_with_prefix() -> None:
    options = parse_parameter(
        "runtime=emit:kernel/protocyte,namespace_prefix=drv::wire,include_prefix=generated"
    )

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


def test_parse_decodes_hex_transport_parameter() -> None:
    raw = "runtime=emit:toolchain/runtime,namespace_prefix=drv::wire,clang_format=C:/Program Files/LLVM/bin/clang-format.exe"
    encoded = raw.encode("utf-8").hex()

    options = parse_parameter(f"_protocyte_options_hex={encoded}")

    assert options.emit_runtime is True
    assert options.runtime_prefix == "toolchain/runtime"
    assert options.namespace_prefix == "drv::wire"
    assert options.clang_format == "C:/Program Files/LLVM/bin/clang-format.exe"


def test_rejects_removed_base64_transport_parameter() -> None:
    with pytest.raises(
        ProtocyteError,
        match=r"unknown protocyte parameter\(s\): _protocyte_options_b64",
    ):
        parse_parameter("_protocyte_options_b64=cnVudGltZT1lbWl0")


def test_rejects_mixed_encoded_transport_parameter() -> None:
    encoded = b"runtime=emit".hex()

    with pytest.raises(ProtocyteError, match="encoded protocyte transport parameter must be the only protocyte parameter"):
        parse_parameter(f"_protocyte_options_hex={encoded},include_prefix=generated")


def test_rejects_bare_encoded_transport_parameter() -> None:
    with pytest.raises(ProtocyteError, match=r"invalid protocyte parameter '_protocyte_options_hex'; expected key=value"):
        parse_parameter("_protocyte_options_hex")


def test_rejects_duplicate_parameters() -> None:
    with pytest.raises(ProtocyteError, match="duplicate protocyte parameter: runtime"):
        parse_parameter("runtime=emit,runtime=omit")


@pytest.mark.parametrize(
    "parameter",
    [
        "namespace=drv::wire",
        "namespace-prefix=drv::wire",
        "runtime-prefix=protocyte/runtime",
        "include-prefix=generated",
        "clang-format=clang-format",
        "clang-format-config=.clang-format",
    ],
)
def test_rejects_legacy_parameter_aliases(parameter: str) -> None:
    with pytest.raises(ProtocyteError, match="unknown protocyte parameter"):
        parse_parameter(parameter)


@pytest.mark.parametrize(
    "parameter",
    [
        "namespace_prefix=::drv::wire",
        "namespace_prefix=drv::wire::",
        "namespace_prefix=drv::::wire",
        "namespace_prefix=drv:wire",
        "namespace_prefix=drv:: wire",
        "namespace_prefix= drv::wire",
    ],
)
def test_rejects_noncanonical_namespace_prefixes(parameter: str) -> None:
    with pytest.raises(ProtocyteError, match="namespace prefix"):
        parse_parameter(parameter)


def test_generator_options_rejects_noncanonical_namespace_prefix() -> None:
    with pytest.raises(ProtocyteError, match="namespace prefix"):
        GeneratorOptions(namespace_prefix="drv::::wire")


@pytest.mark.parametrize(
    ("field", "prefix", "error"),
    [
        ("runtime_prefix", "../runtime", "runtime prefix"),
        ("runtime_prefix", "C:/runtime", "runtime prefix"),
        ("runtime_prefix", "runtime\ninjected", "runtime prefix"),
        ("include_prefix", "../generated", "include prefix"),
        ("include_prefix", r"generated\wire", "include prefix"),
        ("include_prefix", "generated\ninjected", "include prefix"),
    ],
)
def test_generator_options_rejects_unsafe_virtual_directory_prefixes(
    field: str, prefix: str, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        GeneratorOptions(**{field: prefix})


@pytest.mark.parametrize("parameter", ["runtime=none", "runtime="])
def test_rejects_runtime_omit_aliases(parameter: str) -> None:
    with pytest.raises(
        ProtocyteError,
        match="runtime must be one of: emit, omit, emit:<prefix>",
    ):
        parse_parameter(parameter)


def test_rejects_bare_tokens_without_equals() -> None:
    with pytest.raises(ProtocyteError, match=r"invalid protocyte parameter 'runtime'; expected key=value"):
        parse_parameter("runtime")


def test_rejects_unknown_parameters() -> None:
    with pytest.raises(ProtocyteError, match=r"unknown protocyte parameter\(s\): debug"):
        parse_parameter("debug=true")


@pytest.mark.parametrize(
    "prefix",
    [
        "../escaped",
        "nested/../escaped",
        "nested/./runtime",
        "/absolute/runtime",
        "C:/absolute/runtime",
        "C:drive-relative/runtime",
        "nested/runtime:stream",
        "nested\\runtime",
        "nested//runtime",
        "nested/runtime/",
        "nested/\x00runtime",
        "nested/\nruntime",
    ],
)
def test_rejects_unsafe_runtime_prefixes(prefix: str) -> None:
    with pytest.raises(ProtocyteError, match="runtime prefix"):
        parse_parameter(f"runtime=emit:{prefix}")


@pytest.mark.parametrize(
    "parameter",
    [
        "runtime=emit:",
        "runtime_prefix=",
        "include_prefix=",
    ],
)
def test_rejects_explicit_empty_prefixes(parameter: str) -> None:
    with pytest.raises(ProtocyteError, match="prefix must not be empty"):
        parse_parameter(parameter)


@pytest.mark.parametrize(
    "parameter",
    [
        "runtime=emit: vendor/runtime",
        "runtime=emit:vendor/runtime ",
        "runtime=emit:vendor/runtime\t",
        "runtime_prefix=vendor/runtime\n",
        "include_prefix= generated/wire",
    ],
)
def test_rejects_prefix_whitespace_and_terminal_controls(parameter: str) -> None:
    with pytest.raises(ProtocyteError, match="prefix must not"):
        parse_parameter(parameter)


@pytest.mark.parametrize(
    "prefix", ["../generated", "/generated", "C:/generated", "nested\\generated", "nested//generated"]
)
def test_rejects_unsafe_include_prefixes(prefix: str) -> None:
    with pytest.raises(ProtocyteError, match="include prefix"):
        parse_parameter(f"include_prefix={prefix}")


def test_accepts_normalized_nested_virtual_directory_prefixes() -> None:
    options = parse_parameter(
        "runtime=emit:vendor/protocyte/runtime,include_prefix=generated/wire"
    )

    assert options.runtime_prefix == "vendor/protocyte/runtime"
    assert options.include_prefix == "generated/wire"
