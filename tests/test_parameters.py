import pytest

from protocyte.errors import ProtocyteError
from protocyte.parameters import GeneratorOptions, parse_parameter
from protocyte.paths import MIN_HASHED_GENERATED_FILE_PATH_BYTES


def test_parse_runtime_emit_with_prefix() -> None:
    options = parse_parameter(
        "runtime=emit:kernel/protocyte,namespace_prefix=drv::wire,include_prefix=generated"
    )

    assert options.emit_runtime is True
    assert options.runtime_prefix == "kernel/protocyte"
    assert options.namespace_prefix == "drv::wire"
    assert options.include_prefix == "generated"


def test_rejects_conflicting_runtime_prefix_parameters() -> None:
    with pytest.raises(ProtocyteError, match="conflicts"):
        parse_parameter("runtime=emit:first/runtime,runtime_prefix=second/runtime")


def test_accepts_matching_runtime_prefix_parameters() -> None:
    options = parse_parameter(
        "runtime=emit:vendor/runtime,runtime_prefix=vendor/runtime"
    )

    assert options.emit_runtime is True
    assert options.runtime_prefix == "vendor/runtime"


def test_parse_defaults_to_no_runtime_emission() -> None:
    options = parse_parameter("")

    assert options.emit_runtime is False
    assert options.runtime_prefix == "protocyte/runtime"
    assert options.namespace_prefix == ""
    assert options.reflection_api_macro is None
    assert options.emit_comments is True
    assert options.format_mode == "auto"
    assert options.clang_format is None
    assert options.clang_format_config is None


def test_accepts_internal_sha_based_reflection_api_macro() -> None:
    macro = f"PROTOCYTE_REFLECTION_API_{'A1' * 32}"

    options = parse_parameter(f"_protocyte_reflection_api_macro={macro}")

    assert options.reflection_api_macro == macro


@pytest.mark.parametrize(
    "macro",
    [
        "PROTOCYTE_REFLECTION_API_short",
        f"PROTOCYTE_REFLECTION_API_{'a1' * 32}",
        f"PROTOCYTE_REFLECTION_API_{'A1' * 31};INJECTED",
    ],
)
def test_rejects_invalid_internal_reflection_api_macro(macro: str) -> None:
    with pytest.raises(ProtocyteError, match="internal reflection API macro"):
        parse_parameter(f"_protocyte_reflection_api_macro={macro}")


def test_parse_accepts_clang_format_options() -> None:
    options = parse_parameter("clang_format=custom-format,clang_format_config=configs/protocyte.style")

    assert options.clang_format == "custom-format"
    assert options.clang_format_config == "configs/protocyte.style"
    assert options.format_mode == "required"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("on", True), ("off", False)],
)
def test_parse_accepts_comment_modes(value: str, expected: bool) -> None:
    assert parse_parameter(f"comments={value}").emit_comments is expected


def test_rejects_invalid_comment_mode() -> None:
    with pytest.raises(
        ProtocyteError, match="comments must be one of: on, off"
    ):
        parse_parameter("comments=sometimes")


@pytest.mark.parametrize("format_mode", ["auto", "off", "required"])
def test_parse_accepts_format_modes(format_mode: str) -> None:
    options = parse_parameter(f"format={format_mode}")

    assert options.format_mode == format_mode


def test_rejects_invalid_format_mode() -> None:
    with pytest.raises(
        ProtocyteError, match="format must be one of: auto, off, required"
    ):
        parse_parameter("format=sometimes")


def test_generator_options_rejects_invalid_format_mode() -> None:
    with pytest.raises(
        ProtocyteError, match="format must be one of: auto, off, required"
    ):
        GeneratorOptions(format_mode="sometimes")


@pytest.mark.parametrize("parameter", ["clang_format=", "clang_format_config="])
def test_rejects_empty_formatter_parameters(parameter: str) -> None:
    with pytest.raises(ProtocyteError, match="must not be empty"):
        parse_parameter(parameter)


@pytest.mark.parametrize(
    "parameter",
    [
        "format=off,clang_format=clang-format",
        "format=off,clang_format_config=.clang-format",
    ],
)
def test_rejects_explicit_formatter_settings_when_formatting_is_off(
    parameter: str,
) -> None:
    with pytest.raises(
        ProtocyteError,
        match="format=off cannot be combined with clang_format or clang_format_config",
    ):
        parse_parameter(parameter)


def test_generator_options_rejects_explicit_formatter_when_formatting_is_off() -> None:
    with pytest.raises(
        ProtocyteError,
        match="format=off cannot be combined with clang_format or clang_format_config",
    ):
        GeneratorOptions(format_mode="off", clang_format="clang-format")


def test_parse_decodes_hex_transport_parameter() -> None:
    raw = "runtime=emit:toolchain/runtime,namespace_prefix=drv::wire,clang_format=C:/Program Files/LLVM/bin/clang-format.exe"
    encoded = raw.encode("utf-8").hex()

    options = parse_parameter(f"_protocyte_options_hex={encoded}")

    assert options.emit_runtime is True
    assert options.runtime_prefix == "toolchain/runtime"
    assert options.namespace_prefix == "drv::wire"
    assert options.clang_format == "C:/Program Files/LLVM/bin/clang-format.exe"


def test_parse_decodes_internal_generated_path_budget() -> None:
    raw = (
        "format=off,_protocyte_generated_path_max_bytes="
        f"{MIN_HASHED_GENERATED_FILE_PATH_BYTES},"
        "_protocyte_generated_directory_max_bytes=67"
    )

    options = parse_parameter(f"_protocyte_options_hex={raw.encode('utf-8').hex()}")

    assert options.generated_path_max_bytes == MIN_HASHED_GENERATED_FILE_PATH_BYTES
    assert options.generated_directory_max_bytes == 67


@pytest.mark.parametrize(
    "value",
    ["", "not-a-number", str(MIN_HASHED_GENERATED_FILE_PATH_BYTES - 1)],
)
def test_rejects_invalid_internal_generated_path_budget(value: str) -> None:
    raw = f"_protocyte_generated_path_max_bytes={value}"

    with pytest.raises(ProtocyteError, match="internal generated path budget"):
        parse_parameter(f"_protocyte_options_hex={raw.encode('utf-8').hex()}")


@pytest.mark.parametrize("value", ["", "not-a-number", "-1"])
def test_rejects_invalid_internal_generated_directory_budget(value: str) -> None:
    raw = f"_protocyte_generated_directory_max_bytes={value}"

    with pytest.raises(ProtocyteError, match="internal generated directory budget"):
        parse_parameter(f"_protocyte_options_hex={raw.encode('utf-8').hex()}")


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


@pytest.mark.parametrize(
    "prefix",
    [
        "my-corp",
        "123corp",
        "class",
        "drv::alignas",
        "drv::_private",
        "drv::__private",
        "drv::naïve",
    ],
)
def test_rejects_namespace_prefixes_that_are_not_portable_cpp_identifiers(
    prefix: str,
) -> None:
    with pytest.raises(ProtocyteError, match=r"non-reserved C\+\+ identifiers"):
        parse_parameter(f"namespace_prefix={prefix}")


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


@pytest.mark.parametrize(
    "prefix",
    [
        'vendor/runtime"injected',
        "vendor/runtime<injected",
        "vendor/runtime>injected",
        "vendor/runtime|injected",
        "vendor/runtime?injected",
        "vendor/runtime*injected",
        "vendor/runtime;injected",
        "vendor/trailing.",
        "vendor/CON",
        "vendor/nul.hpp",
        "vendor/COM1",
        "vendor/lpt9.generated",
    ],
)
@pytest.mark.parametrize("parameter", ["runtime_prefix", "include_prefix"])
def test_rejects_virtual_prefixes_that_are_unsafe_in_generated_includes(
    prefix: str, parameter: str
) -> None:
    with pytest.raises(ProtocyteError, match="unsafe in generated includes"):
        parse_parameter(f"{parameter}={prefix}")


def test_accepts_normalized_nested_virtual_directory_prefixes() -> None:
    options = parse_parameter(
        "runtime=emit:vendor/protocyte/runtime,include_prefix=generated/wire"
    )

    assert options.runtime_prefix == "vendor/protocyte/runtime"
    assert options.include_prefix == "generated/wire"
