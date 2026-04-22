from __future__ import annotations

from dataclasses import dataclass

from protocyte.errors import ProtocyteError


@dataclass(frozen=True)
class GeneratorOptions:
    emit_runtime: bool = False
    runtime_prefix: str = "protocyte/runtime"
    include_prefix: str = ""
    namespace_prefix: str = ""
    clang_format: str | None = None
    clang_format_config: str | None = None


def parse_parameter(parameter: str) -> GeneratorOptions:
    """Parse protoc's comma-separated plugin parameter string."""
    values: dict[str, str] = {}

    if parameter:
        for raw_part in parameter.split(","):
            part = raw_part.strip()
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip().replace("-", "_")
                value = value.strip()
                if not key:
                    raise ProtocyteError(f"invalid empty parameter name in {parameter!r}")
                if key in values:
                    raise ProtocyteError(f"duplicate protocyte parameter: {key}")
                values[key] = value
            else:
                raise ProtocyteError(f"invalid protocyte parameter {part!r}; expected key=value")

    unknown = set(values) - {
        "runtime",
        "runtime_prefix",
        "include_prefix",
        "namespace",
        "namespace_prefix",
        "clang_format",
        "clang_format_config",
    }
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise ProtocyteError(f"unknown protocyte parameter(s): {joined}")

    runtime = values.get("runtime", "omit")
    runtime_prefix = values.get("runtime_prefix", "protocyte/runtime").strip("/")
    if runtime.startswith("emit:"):
        emit_runtime = True
        suffix = runtime.split(":", 1)[1].strip("/")
        if suffix:
            runtime_prefix = suffix
    elif runtime == "emit":
        emit_runtime = True
    elif runtime in {"omit", "none", ""}:
        emit_runtime = False
    else:
        raise ProtocyteError("runtime must be one of: emit, omit, emit:<prefix>")

    if "namespace" in values and "namespace_prefix" in values:
        raise ProtocyteError("namespace and namespace_prefix are aliases; specify only one")

    namespace_prefix = values.get("namespace_prefix", values.get("namespace", "")).strip(":")
    include_prefix = values.get("include_prefix", "").strip("/")
    clang_format = values.get("clang_format")
    clang_format_config = values.get("clang_format_config")

    return GeneratorOptions(
        emit_runtime=emit_runtime,
        runtime_prefix=runtime_prefix or "protocyte/runtime",
        include_prefix=include_prefix,
        namespace_prefix=namespace_prefix,
        clang_format=clang_format,
        clang_format_config=clang_format_config,
    )


def _parse_bool(value: str, name: str) -> bool:
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ProtocyteError(f"{name} must be a boolean value")
