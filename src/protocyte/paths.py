from __future__ import annotations


_SAFE_GENERATED_PATH_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-;"
)
_WINDOWS_RESERVED_PATH_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


def normalize_generated_path(path: str) -> str:
    """Map a Protobuf virtual path to a portable generated-file path.

    Protobuf virtual file names are broader than host file-system names. Hex
    escaping keeps every accepted descriptor name representable without making
    ordinary ``api/example.proto`` paths less readable.
    """
    return "/".join(_normalize_generated_segment(segment) for segment in path.split("/"))


def generated_file_base(proto_name: str) -> str:
    return normalize_generated_path(proto_name.removesuffix(".proto")) + ".protocyte"


def _normalize_generated_segment(segment: str) -> str:
    encoded = segment.encode("utf-8")
    device_stem = segment.split(".", 1)[0].upper()
    escape_first = device_stem in _WINDOWS_RESERVED_PATH_NAMES
    escape_last_dot = segment.endswith(".")
    parts: list[str] = []
    for index, byte in enumerate(encoded):
        safe = byte in _SAFE_GENERATED_PATH_BYTES
        if index == 0 and escape_first:
            safe = False
        if index == len(encoded) - 1 and escape_last_dot:
            safe = False
        parts.append(chr(byte) if safe else f"~{byte:02X}")
    return "".join(parts)
