from __future__ import annotations

import hashlib


_SAFE_GENERATED_PATH_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)
_MAX_GENERATED_PATH_COMPONENT_BYTES = 255
_GENERATED_FILE_SUFFIX = ".protocyte.hpp"
_GENERATED_PATH_DIGEST_BYTES = 64
_GENERATED_PATH_DIGEST_SEPARATOR_BYTES = 1
_MAX_GENERATED_FILE_STEM_BYTES = (
    _MAX_GENERATED_PATH_COMPONENT_BYTES - len(_GENERATED_FILE_SUFFIX)
)
MIN_HASHED_GENERATED_FILE_PATH_BYTES = (
    _GENERATED_PATH_DIGEST_SEPARATOR_BYTES
    + _GENERATED_PATH_DIGEST_BYTES
    + len(_GENERATED_FILE_SUFFIX)
)
_STABLE_BUDGETED_GENERATED_DIRECTORY_BYTES = (
    MIN_HASHED_GENERATED_FILE_PATH_BYTES - 12
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


def generated_file_base(
    proto_name: str,
    *,
    max_output_path_bytes: int | None = None,
    max_output_directory_bytes: int | None = None,
) -> str:
    """Return the portable generated-file base for a descriptor name.

    Supplying either budget selects a canonical compact mapping that fits the
    smallest output-root budgets accepted by the Visual Studio integration.
    Larger local budgets never lengthen that spelling, so separately generated
    dependencies and consumers agree on imported header names. Smaller explicit
    budgets remain authoritative. When the normal component-bounded mapping
    cannot fit, the directory hierarchy is folded into a SHA-256 digest of the
    complete descriptor name.
    """
    normalized = normalize_generated_path(proto_name.removesuffix(".proto"))
    generated_base = normalized + ".protocyte"
    generated_directory = generated_base.rpartition("/")[0]
    budgeted = (
        max_output_path_bytes is not None
        or max_output_directory_bytes is not None
    )
    if not budgeted:
        return generated_base
    effective_path_budget = MIN_HASHED_GENERATED_FILE_PATH_BYTES
    if max_output_path_bytes is not None:
        effective_path_budget = min(
            effective_path_budget,
            max_output_path_bytes,
        )
    effective_directory_budget = _STABLE_BUDGETED_GENERATED_DIRECTORY_BYTES
    if max_output_directory_bytes is not None:
        effective_directory_budget = min(
            effective_directory_budget,
            max_output_directory_bytes,
        )
    path_fits = len(generated_base + ".hpp") <= effective_path_budget
    directory_fits = (
        not generated_directory
        or len(generated_directory) <= effective_directory_budget
    )
    if path_fits and directory_fits:
        return generated_base
    if (
        max_output_path_bytes is not None
        and max_output_path_bytes < MIN_HASHED_GENERATED_FILE_PATH_BYTES
    ):
        raise ValueError(
            "generated output path budget must be at least "
            f"{MIN_HASHED_GENERATED_FILE_PATH_BYTES} bytes"
        )

    digest = hashlib.sha256(proto_name.encode("utf-8")).hexdigest().upper()
    readable = normalized.replace("/", "_")
    prefix_bytes = (
        effective_path_budget
        - len(_GENERATED_FILE_SUFFIX)
        - _GENERATED_PATH_DIGEST_SEPARATOR_BYTES
        - len(digest)
    )
    return f"{readable[:prefix_bytes]}~{digest}.protocyte"


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
