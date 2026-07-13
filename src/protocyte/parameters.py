from __future__ import annotations

from dataclasses import dataclass

from protocyte.errors import ProtocyteError


def _validate_namespace_prefix(value: str) -> str:
    if not value:
        return value
    components = value.split("::")
    if any(
        not component or component != component.strip() or ":" in component
        for component in components
    ):
        raise ProtocyteError(
            "namespace prefix must be a normalized '::'-separated namespace"
        )
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise ProtocyteError("namespace prefix must not contain control characters")
    return value


@dataclass(frozen=True)
class GeneratorOptions:
    emit_runtime: bool = False
    runtime_prefix: str = "protocyte/runtime"
    include_prefix: str = ""
    namespace_prefix: str = ""
    clang_format: str | None = None
    clang_format_config: str | None = None

    def __post_init__(self) -> None:
        _validate_namespace_prefix(self.namespace_prefix)


def validate_virtual_directory_prefix(value: str, *, parameter: str) -> str:
    """Validate a portable relative directory used in generated file names."""
    if not value:
        raise ProtocyteError(f"{parameter} must not be empty")
    if value.startswith("/") or ":" in value:
        raise ProtocyteError(
            f"{parameter} must be a relative virtual directory using '/'"
        )
    if "\\" in value:
        raise ProtocyteError(
            f"{parameter} must be a relative virtual directory using '/'"
        )
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise ProtocyteError(f"{parameter} must not contain control characters")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ProtocyteError(
            f"{parameter} contains an unsafe or non-normalized path segment"
        )
    if any(segment != segment.strip() for segment in segments):
        raise ProtocyteError(
            f"{parameter} must not have leading or trailing segment whitespace"
        )
    return value


def parse_parameter(parameter: str) -> GeneratorOptions:
    """Parse protoc's comma-separated plugin parameter string."""
    parameter = _decode_transport_parameter(parameter)
    values: dict[str, str] = {}

    if parameter:
        for raw_part in parameter.split(","):
            part = raw_part.strip()
            if not part:
                continue
            if "=" in part:
                raw_key, raw_value = raw_part.split("=", 1)
                key = raw_key.strip()
                value = raw_value.strip()
                if not key:
                    raise ProtocyteError(f"invalid empty parameter name in {parameter!r}")
                if key in values:
                    raise ProtocyteError(f"duplicate protocyte parameter: {key}")
                prefix_parameter = None
                if key == "runtime" and value.startswith("emit:"):
                    prefix_parameter = "runtime prefix"
                elif key == "runtime_prefix":
                    prefix_parameter = "runtime prefix"
                elif key == "include_prefix":
                    prefix_parameter = "include prefix"
                elif key == "namespace_prefix":
                    prefix_parameter = "namespace prefix"
                if prefix_parameter is not None:
                    if any(
                        ord(char) < 0x20 or ord(char) == 0x7F
                        for char in raw_value
                    ):
                        raise ProtocyteError(
                            f"{prefix_parameter} must not contain control characters"
                        )
                    if raw_value != value:
                        raise ProtocyteError(
                            f"{prefix_parameter} must not have leading or trailing whitespace"
                        )
                values[key] = value
            else:
                raise ProtocyteError(f"invalid protocyte parameter {part!r}; expected key=value")

    unknown = set(values) - {
        "runtime",
        "runtime_prefix",
        "include_prefix",
        "namespace_prefix",
        "clang_format",
        "clang_format_config",
    }
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise ProtocyteError(f"unknown protocyte parameter(s): {joined}")

    runtime = values.get("runtime", "omit")
    runtime_prefix = values.get("runtime_prefix", "protocyte/runtime")
    if runtime.startswith("emit:"):
        emit_runtime = True
        suffix = runtime.split(":", 1)[1]
        if not suffix:
            raise ProtocyteError("runtime prefix must not be empty")
        runtime_prefix = suffix
    elif runtime == "emit":
        emit_runtime = True
    elif runtime == "omit":
        emit_runtime = False
    else:
        raise ProtocyteError("runtime must be one of: emit, omit, emit:<prefix>")

    namespace_prefix = values.get("namespace_prefix", "")
    runtime_prefix = validate_virtual_directory_prefix(
        runtime_prefix, parameter="runtime prefix"
    )
    include_prefix = values.get("include_prefix", "")
    if "include_prefix" in values:
        include_prefix = validate_virtual_directory_prefix(
            include_prefix, parameter="include prefix"
        )
    clang_format = values.get("clang_format")
    clang_format_config = values.get("clang_format_config")

    return GeneratorOptions(
        emit_runtime=emit_runtime,
        runtime_prefix=runtime_prefix,
        include_prefix=include_prefix,
        namespace_prefix=namespace_prefix,
        clang_format=clang_format,
        clang_format_config=clang_format_config,
    )


def _decode_transport_parameter(parameter: str) -> str:
    parts = [raw_part.strip() for raw_part in parameter.split(",") if raw_part.strip()]
    if not parts:
        return parameter

    transport_decoders = {
        "_protocyte_options_hex": _decode_hex_transport_parameter,
    }
    transport_parts = [part for part in parts if part.split("=", 1)[0] in transport_decoders]
    if not transport_parts:
        return parameter
    if len(transport_parts) != 1 or len(parts) != 1:
        raise ProtocyteError("encoded protocyte transport parameter must be the only protocyte parameter")
    if "=" not in transport_parts[0]:
        name = transport_parts[0]
        raise ProtocyteError(f"invalid protocyte parameter {name!r}; expected key=value")

    name, encoded = transport_parts[0].split("=", 1)
    return transport_decoders[name](encoded)


def _decode_hex_transport_parameter(encoded: str) -> str:
    try:
        decoded = bytes.fromhex(encoded)
    except ValueError as exc:
        raise ProtocyteError("invalid _protocyte_options_hex payload") from exc
    return _decode_transport_bytes("_protocyte_options_hex", decoded)


def _decode_transport_bytes(name: str, decoded: bytes) -> str:
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocyteError(f"{name} payload must decode as UTF-8") from exc
