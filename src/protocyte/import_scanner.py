from __future__ import annotations

import argparse
import ctypes
import os
import stat
import sys
from collections import deque
from pathlib import Path


_PROTOC_OPTIONS_IMPORT = b"protocyte/options.proto"
_PROTOBUF_IMPORT_PREFIX = b"google/protobuf/"
_HEX_DIGITS = b"0123456789abcdefABCDEF"
UNSAFE_VIRTUAL_IMPORT_PATH_ERROR = (
    "Protocyte import scanner rejected a Windows virtual import path that could "
    "escape its import root."
)
_SIMPLE_ESCAPES = {
    ord("a"): 7,
    ord("b"): 8,
    ord("f"): 12,
    ord("n"): 10,
    ord("r"): 13,
    ord("t"): 9,
    ord("v"): 11,
}


class UnsafeVirtualImportPathError(ValueError):
    pass


def _is_identifier_start(value: int) -> bool:
    return (
        value == ord("_")
        or ord("A") <= value <= ord("Z")
        or ord("a") <= value <= ord("z")
    )


def _is_identifier_continue(value: int) -> bool:
    return _is_identifier_start(value) or ord("0") <= value <= ord("9")


def _encode_unicode_point(code_point: int) -> bytes:
    if code_point <= 0x7F:
        return bytes((code_point,))
    if code_point <= 0x7FF:
        return bytes((0xC0 | code_point >> 6, 0x80 | code_point & 0x3F))
    if code_point <= 0xFFFF:
        return bytes(
            (
                0xE0 | code_point >> 12,
                0x80 | code_point >> 6 & 0x3F,
                0x80 | code_point & 0x3F,
            )
        )
    if code_point <= 0x10FFFF:
        return bytes(
            (
                0xF0 | code_point >> 18,
                0x80 | code_point >> 12 & 0x3F,
                0x80 | code_point >> 6 & 0x3F,
                0x80 | code_point & 0x3F,
            )
        )
    return f"\\U{code_point:08x}".encode("ascii")


def _decode_unicode_escape(data: bytes, start: int) -> tuple[int, bytes] | None:
    width = 4 if data[start] == ord("u") else 8
    end = start + 1 + width
    if end > len(data) or any(
        value not in _HEX_DIGITS for value in data[start + 1 : end]
    ):
        return None
    code_point = int(data[start + 1 : end], 16)
    if 0xD800 <= code_point < 0xDC00 and data[end : end + 2] == b"\\u":
        trail_end = end + 6
        trail_digits = data[end + 2 : trail_end]
        if len(trail_digits) == 4 and all(
            value in _HEX_DIGITS for value in trail_digits
        ):
            trail = int(trail_digits, 16)
            if 0xDC00 <= trail < 0xE000:
                code_point = 0x10000 + ((code_point - 0xD800) << 10) + trail - 0xDC00
                end = trail_end
    return end, _encode_unicode_point(code_point)


def _decode_string(
    data: bytes, start: int, *, capture: bool
) -> tuple[int, bytes | None]:
    quote = data[start]
    index = start + 1
    value = bytearray()
    while index < len(data):
        current = data[index]
        if current == ord("\\"):
            if index + 1 >= len(data):
                return len(data), None
            escaped = data[index + 1]
            if not capture:
                index += 2
                continue
            if escaped in (ord("x"), ord("X")):
                escape_end = index + 2
                while escape_end < len(data) and escape_end < index + 4:
                    if data[escape_end] not in b"0123456789abcdefABCDEF":
                        break
                    escape_end += 1
                if escape_end == index + 2:
                    value.append(escaped)
                    index += 2
                else:
                    value.append(int(data[index + 2 : escape_end], 16) & 0xFF)
                    index = escape_end
                continue
            if escaped in (ord("u"), ord("U")):
                decoded_unicode = _decode_unicode_escape(data, index + 1)
                if decoded_unicode is None:
                    value.append(escaped)
                    index += 2
                else:
                    index, encoded_unicode = decoded_unicode
                    value.extend(encoded_unicode)
                continue
            if ord("0") <= escaped <= ord("7"):
                escape_end = index + 2
                while escape_end < len(data) and escape_end < index + 4:
                    if not ord("0") <= data[escape_end] <= ord("7"):
                        break
                    escape_end += 1
                value.append(int(data[index + 1 : escape_end], 8) & 0xFF)
                index = escape_end
                continue
            value.append(_SIMPLE_ESCAPES.get(escaped, escaped))
            index += 2
            continue
        if current == quote:
            return index + 1, bytes(value)
        if capture:
            value.append(current)
        index += 1
    return len(data), None


def _import_names(data: bytes) -> list[bytes]:
    imports: list[bytes] = []
    index = 0
    expectation: str | None = None
    import_name = bytearray()
    while index < len(data):
        current = data[index]
        if current == ord("/") and index + 1 < len(data):
            following = data[index + 1]
            if following == ord("/"):
                index += 2
                while index < len(data) and data[index] != ord("\n"):
                    index += 1
                continue
            if following == ord("*"):
                comment_end = data.find(b"*/", index + 2)
                index = comment_end + 2 if comment_end >= 0 else len(data)
                continue

        if _is_identifier_start(current):
            identifier_end = index + 1
            while identifier_end < len(data) and _is_identifier_continue(
                data[identifier_end]
            ):
                identifier_end += 1
            identifier = data[index:identifier_end]
            if expectation is None and identifier == b"import":
                expectation = "qualifier_or_string"
                import_name.clear()
            elif expectation == "qualifier_or_string" and identifier in (
                b"option",
                b"public",
                b"weak",
            ):
                expectation = "string"
            else:
                expectation = None
                import_name.clear()
            index = identifier_end
            continue

        if current in (ord('"'), ord("'")):
            capture = expectation in {
                "qualifier_or_string",
                "string",
                "adjacent_string_or_end",
            }
            index, string_value = _decode_string(data, index, capture=capture)
            if capture and string_value is not None:
                import_name.extend(string_value)
                expectation = "adjacent_string_or_end"
            else:
                expectation = None
                import_name.clear()
            continue

        if current in b" \t\r\n\v\f":
            index += 1
            continue
        if current == ord(";"):
            if expectation == "adjacent_string_or_end":
                imports.append(bytes(import_name))
            expectation = None
            import_name.clear()
            index += 1
            continue

        expectation = None
        import_name.clear()
        index += 1

    return imports


def _decode_path(encoded_path: str) -> str:
    return bytes.fromhex(encoded_path).decode("utf-8")


def _canonicalize_virtual_path(path: bytes) -> bytes:
    if os.name == "nt":
        if path.startswith(b"\\\\"):
            path = b"\\\\" + path[2:].replace(b"\\", b"/")
        else:
            path = path.replace(b"\\", b"/")
    parts = [b""] if path.startswith(b"/") else []
    parts.extend(part for part in path.split(b"/") if part and part != b".")
    if path.endswith(b"/"):
        parts.append(b"")
    return b"/".join(parts)


def _is_windows_absolute_path(path: bytes) -> bool:
    return (
        (os.name == "nt" or sys.platform == "cygwin")
        and len(path) >= 3
        and path[1] == ord(":")
        and (ord("A") <= path[0] <= ord("Z") or ord("a") <= path[0] <= ord("z"))
        and path[2] in (ord("/"), ord("\\"))
        and path.rfind(b":") == 1
    )


def _is_canonical_virtual_path(path: bytes) -> bool:
    # Match protoc's lexical virtual-path gate without resolving the disk target;
    # a canonical import may legitimately pass through a symlink below a root.
    return (
        bool(path)
        and not path.endswith(b"/")
        and path == _canonicalize_virtual_path(path)
        and b".." not in path.split(b"/")
        and not path.startswith(b"/")
        and not _is_windows_absolute_path(path)
    )


def _is_masked_windows_parent_path(path: bytes) -> bool:
    if os.name != "nt" or not path.startswith(b"\\\\"):
        return False
    first_component = path[2:].split(b"/", 1)[0]
    return first_component in (b".", b"..")


def _map_virtual_path(import_root: str, virtual_path: str) -> str:
    has_separator = import_root.endswith("/") or (
        os.name == "nt" and import_root.endswith("\\")
    )
    candidate = import_root + ("" if has_separator else "/") + virtual_path
    if os.name == "nt":
        # CMake and protoc receive lexical host paths with forward slashes. Do
        # not resolve links or change casing: import shadowing is lexical, but
        # mixed separators in protoc's accepted Windows spellings must not turn
        # into unsafe or ineffective CMake watch patterns.
        candidate = os.path.normpath(candidate).replace("\\", "/")
    return candidate


def _cmake_glob_pattern(path: str) -> str | None:
    # CMake writes CONFIGURE_DEPENDS expressions and their matches into a
    # generated CMake script. A quote, backslash, or control byte cannot be
    # serialized there safely. All other metacharacters are encoded character
    # by character; sequential replacement would corrupt inserted bracket
    # classes.
    if any(
        value in {'"', "\\"} or ord(value) < 32 or ord(value) == 127 for value in path
    ):
        return None

    replacements = {
        "[": "[[]",
        "]": "[]]",
        "*": "[*]",
        "?": "[?]",
        "$": "[$]",
    }
    pattern: list[str] = []
    for value in path:
        pattern.append(replacements.get(value, value))
    return "".join(pattern)


def _configure_dependency_path(path: str) -> str | None:
    has_unsafe_spelling = _cmake_glob_pattern(path) is None
    if os.name != "nt":
        return None if has_unsafe_spelling else path
    if ";" not in path and not has_unsafe_spelling:
        return path

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_short_path_name = kernel32.GetShortPathNameW
    get_short_path_name.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    get_short_path_name.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_short_path_name(path, buffer, len(buffer))
    if length == 0 or length >= len(buffer):
        return None
    dependency_path = os.path.normpath(buffer.value).replace("\\", "/")
    return None if ";" in dependency_path else dependency_path


def _path_identity(path: str) -> str:
    normalized = os.path.normpath(path)
    if os.name == "nt":
        normalized = os.path.normcase(normalized).replace("\\", "/")
    return normalized


def _path_prefixes(path: str) -> list[str]:
    candidate = Path(path)
    return [str(prefix) for prefix in reversed((candidate, *candidate.parents))]


def _is_link_or_junction(path: str) -> bool:
    is_junction = getattr(os.path, "isjunction", None)
    return os.path.islink(path) or bool(is_junction is not None and is_junction(path))


def _immediate_link_target(path: str) -> str | None:
    try:
        target = os.readlink(path)
    except OSError:
        return None
    if not os.path.isabs(target):
        target = os.path.join(os.path.dirname(path), target)
    return os.path.normpath(target)


def _topology_paths(
    source_files: list[str], candidates: list[str]
) -> list[tuple[str, bool]]:
    initial_paths: list[tuple[str, bool]] = []
    for source_file in source_files:
        source_prefixes = _path_prefixes(source_file)
        initial_paths.extend(
            (prefix, prefix == source_prefixes[-1]) for prefix in source_prefixes
        )
    for candidate in candidates:
        candidate_prefixes = _path_prefixes(candidate)
        initial_paths.extend((prefix, False) for prefix in candidate_prefixes[:-1])
        if (
            os.path.lexists(candidate)
            or _is_link_or_junction(candidate)
            or _cmake_glob_pattern(candidate) is None
        ):
            initial_paths.append((candidate, False))

    pending = deque(initial_paths)
    traversal_bound = max(4096, len(initial_paths) * 8)
    topology_paths: dict[str, tuple[str, bool]] = {}
    while pending:
        candidate, content_sensitive = pending.popleft()
        candidate_identity = _path_identity(candidate)
        previous = topology_paths.get(candidate_identity)
        if previous is not None:
            if content_sensitive and not previous[1]:
                topology_paths[candidate_identity] = (previous[0], True)
            continue
        topology_paths[candidate_identity] = (candidate, content_sensitive)
        if _is_link_or_junction(candidate):
            target = _immediate_link_target(candidate)
            if target is not None:
                pending.extend((prefix, False) for prefix in _path_prefixes(target))
        if len(topology_paths) > traversal_bound:
            raise ValueError(
                "Protocyte import scan exceeded its topology traversal bound"
            )
    return list(topology_paths.values())


def _topology_identity(path: str, *, content_sensitive: bool = False) -> str:
    try:
        stat_result = os.stat(path, follow_symlinks=False)
        object_identity = f"{stat_result.st_dev:x}:{stat_result.st_ino:x}"
    except OSError:
        object_identity = "-"
    try:
        followed_stat = os.stat(path)
        if content_sensitive and stat.S_ISREG(followed_stat.st_mode):
            file_identity = (
                f"{followed_stat.st_dev:x}:{followed_stat.st_ino:x}:"
                f"{followed_stat.st_size:x}:{followed_stat.st_mtime_ns:x}"
            )
        else:
            file_identity = "-"
    except OSError:
        file_identity = "-"
    resolved = os.path.realpath(path)
    if os.name == "nt":
        resolved = os.path.normcase(os.path.normpath(resolved)).replace("\\", "/")
    if os.path.isfile(resolved):
        kind = "file"
    elif os.path.isdir(resolved):
        kind = "directory"
    elif os.path.lexists(resolved):
        kind = "other"
    else:
        kind = "missing"
    target = _immediate_link_target(path) if _is_link_or_junction(path) else None
    if target is not None:
        if os.name == "nt":
            target = os.path.normcase(target).replace("\\", "/")
        return f"link\0{target}\0{kind}\0{resolved}\0{object_identity}\0{file_identity}"
    return f"{kind}\0{resolved}\0{object_identity}\0{file_identity}"


def _topology_witness_lines(
    source_files: list[str], candidates: list[str]
) -> list[str]:
    lines: list[str] = []
    for watched_path, content_sensitive in _topology_paths(source_files, candidates):
        kind = "watch-source" if content_sensitive else "watch"
        identity = (
            _topology_identity(watched_path, content_sensitive=content_sensitive)
            .encode("utf-8")
            .hex()
        )
        lines.append(f"{kind} {watched_path.encode('utf-8').hex()} {identity}")
    return lines


def _scan_topology_witness(request_path: Path, output_path: Path) -> None:
    roots, sources = _read_request(request_path)
    _, closure, import_edges = _scan_source_closure_trace(sources, roots)
    candidates = [
        candidate
        for _, _, edge_candidates in import_edges
        for candidate in edge_candidates
    ]
    content = "version=1\n" + "\n".join(_topology_witness_lines(closure, candidates))
    if not content.endswith("\n"):
        content += "\n"
    if output_path.exists() and output_path.read_text(encoding="ascii") == content:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="ascii")


def _read_request(request_path: Path) -> tuple[list[str], list[str]]:
    roots: list[str] = []
    sources: list[str] = []
    lines = request_path.read_text(encoding="ascii").splitlines()
    if not lines or lines[0] != "version=1":
        raise ValueError("unsupported Protocyte import-scan request")
    for line in lines[1:]:
        kind, separator, encoded_path = line.partition(" ")
        if not separator or kind not in {"root", "source"}:
            raise ValueError("malformed Protocyte import-scan request")
        destination = roots if kind == "root" else sources
        destination.append(_decode_path(encoded_path))
    if not roots or not sources:
        raise ValueError("Protocyte import-scan request requires roots and sources")
    return roots, sources


def _scan_source_closure_trace(
    source_files: list[str], import_roots: list[str]
) -> tuple[bool, list[str], list[tuple[bytes, str | None, list[str]]]]:
    pending = deque(source_files)
    seen: set[str] = set()
    closure: list[str] = []
    import_edges: list[tuple[bytes, str | None, list[str]]] = []
    requires_protobuf_imports = False
    while pending:
        source_file = pending.popleft()
        if source_file in seen:
            continue
        seen.add(source_file)
        closure.append(source_file)
        for import_name in _import_names(Path(source_file).read_bytes()):
            if _is_masked_windows_parent_path(import_name):
                raise UnsafeVirtualImportPathError(UNSAFE_VIRTUAL_IMPORT_PATH_ERROR)
            if not _is_canonical_virtual_path(import_name):
                continue
            is_protobuf_import = (
                import_name == _PROTOC_OPTIONS_IMPORT
                or import_name.startswith(_PROTOBUF_IMPORT_PREFIX)
            )
            if is_protobuf_import:
                requires_protobuf_imports = True
            if b"\0" in import_name:
                continue
            try:
                decoded_import = import_name.decode("utf-8")
            except UnicodeDecodeError:
                continue
            candidates: list[str] = []
            selected_candidate: str | None = None
            for import_root in import_roots:
                candidate = _map_virtual_path(import_root, decoded_import)
                candidates.append(candidate)
                if (
                    selected_candidate is None
                    and os.path.exists(candidate)
                    and not os.path.isdir(candidate)
                ):
                    selected_candidate = candidate
            import_edges.append((import_name, selected_candidate, candidates))
            if selected_candidate is not None:
                pending.append(selected_candidate)
    return requires_protobuf_imports, closure, import_edges


def _scan_source_closure(
    source_files: list[str], import_roots: list[str]
) -> tuple[bool, list[str]]:
    requires_protobuf_imports, closure, _ = _scan_source_closure_trace(
        source_files, import_roots
    )
    return requires_protobuf_imports, closure


def source_closure_requires_protobuf_imports(
    source_files: list[str], import_roots: list[str]
) -> bool:
    return _scan_source_closure(source_files, import_roots)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-topology-witness", action="store_true")
    parser.add_argument("request", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    arguments = parser.parse_args(argv)
    if arguments.scan_topology_witness:
        if arguments.output is None:
            parser.error("--scan-topology-witness requires an output path")
        try:
            _scan_topology_witness(arguments.request, arguments.output)
        except UnsafeVirtualImportPathError:
            print(UNSAFE_VIRTUAL_IMPORT_PATH_ERROR, file=sys.stderr)
            return 2
        return 0
    if arguments.output is not None:
        parser.error("unexpected output path")
    roots, sources = _read_request(arguments.request)
    try:
        requires_protobuf_imports, closure, import_edges = _scan_source_closure_trace(
            sources, roots
        )
    except UnsafeVirtualImportPathError:
        print(UNSAFE_VIRTUAL_IMPORT_PATH_ERROR, file=sys.stderr)
        return 2
    print("result " + ("TRUE" if requires_protobuf_imports else "FALSE"))
    for source_file in closure:
        dependency_path = _configure_dependency_path(source_file)
        dependency_hex = (
            "-" if dependency_path is None else dependency_path.encode("utf-8").hex()
        )
        print(f"source {source_file.encode('utf-8').hex()} {dependency_hex}")
    for import_name, selected_candidate, candidates in import_edges:
        selected_hex = (
            "-"
            if selected_candidate is None
            else selected_candidate.encode("utf-8").hex()
        )
        print(f"edge {import_name.hex()} {selected_hex}")
        for candidate in candidates:
            pattern = _cmake_glob_pattern(candidate)
            pattern_hex = "-" if pattern is None else pattern.encode("utf-8").hex()
            dependency_path = _configure_dependency_path(candidate)
            dependency_hex = (
                "-"
                if dependency_path is None
                else dependency_path.encode("utf-8").hex()
            )
            print(
                f"candidate {candidate.encode('utf-8').hex()} "
                f"{pattern_hex} {dependency_hex}"
            )
    candidates = [
        candidate
        for _, _, edge_candidates in import_edges
        for candidate in edge_candidates
    ]
    for topology_line in _topology_witness_lines(closure, candidates):
        print(topology_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
