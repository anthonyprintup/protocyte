from __future__ import annotations

import hashlib


_SAFE_GENERATED_PATH_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)
_MAX_GENERATED_PATH_COMPONENT_BYTES = 255
_GENERATED_FILE_SUFFIX = ".protocyte.hpp"
_MAX_GENERATED_FILE_STEM_BYTES = (
    _MAX_GENERATED_PATH_COMPONENT_BYTES - len(_GENERATED_FILE_SUFFIX)
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
    ordinary ``api/example.proto`` paths less readable. Overlong escaped
    components retain a readable prefix and a SHA-256 digest; the final
    component reserves room for the generated-file suffix.
    """
    segments = path.split("/")
    return "/".join(
        _normalize_generated_segment(
            segment,
            max_bytes=(
                _MAX_GENERATED_FILE_STEM_BYTES
                if index == len(segments) - 1
                else _MAX_GENERATED_PATH_COMPONENT_BYTES
            ),
        )
        for index, segment in enumerate(segments)
    )


def generated_file_base(proto_name: str) -> str:
    return normalize_generated_path(proto_name.removesuffix(".proto")) + ".protocyte"


def _normalize_generated_segment(segment: str, *, max_bytes: int) -> str:
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
    normalized = "".join(parts)
    if len(normalized) <= max_bytes:
        return normalized

    digest = hashlib.sha256(encoded).hexdigest().upper()
    prefix_bytes = max_bytes - len(digest) - 1
    return f"{normalized[:prefix_bytes]}~{digest}"
