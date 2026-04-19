from __future__ import annotations

from dataclasses import dataclass

from protocyte.errors import ProtocyteError


@dataclass(frozen=True)
class GeneratorOptions:
    emit_runtime: bool = False
    runtime_prefix: str = "protocyte/runtime"
    include_prefix: str = ""
    namespace_prefix: str = ""


def parse_parameter(parameter: str) -> GeneratorOptions:
    """Parse protoc's comma-separated plugin parameter string."""
    values: dict[str, str] = {}
    flags: set[str] = set()

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
                values[key] = value
            else:
                flags.add(part.replace("-", "_"))

    unknown = (set(values) | flags) - {
        "runtime",
        "runtime_prefix",
        "include_prefix",
        "namespace",
        "namespace_prefix",
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

    namespace_prefix = values.get("namespace_prefix", values.get("namespace", "")).strip(":")
    include_prefix = values.get("include_prefix", "").strip("/")

    return GeneratorOptions(
        emit_runtime=emit_runtime,
        runtime_prefix=runtime_prefix or "protocyte/runtime",
        include_prefix=include_prefix,
        namespace_prefix=namespace_prefix,
    )


def _parse_bool(value: str, name: str) -> bool:
    lowered = value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ProtocyteError(f"{name} must be a boolean value")
