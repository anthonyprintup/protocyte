from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from google.protobuf import descriptor_pb2
from google.protobuf.message import DecodeError, Message

from protocyte.errors import ProtocyteError
from protocyte.extensions import is_custom_option_extension


_RUNTIME_PREFIX = "google/protobuf/"
_INTERNAL_DESCRIPTOR_FILES = {"protocyte/options.proto"}
_MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS = 4_096
_MAX_DIAGNOSTIC_NAME_CODEPOINTS = 512
_MAX_DIAGNOSTIC_BYTES = 512
_MAX_DIAGNOSTIC_CHAIN_ENTRIES = 32


@dataclass(frozen=True)
class _TypeReference:
    type_name: str
    field_path: str


@dataclass(frozen=True)
class _FileTypeDependency:
    source_file: str
    target_file: str
    reference: _TypeReference


def load_descriptor_set(path: str | Path) -> descriptor_pb2.FileDescriptorSet:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    try:
        descriptor_set.ParseFromString(Path(path).read_bytes())
    except OSError as exc:
        raise ProtocyteError(
            "failed to read descriptor set "
            f"{render_diagnostic_context(str(path))}: "
            f"{render_diagnostic_context(str(exc))}"
        ) from exc
    except DecodeError as exc:
        raise ProtocyteError(
            "failed to parse FileDescriptorSet "
            f"{render_diagnostic_context(str(path))}: "
            f"{render_diagnostic_context(str(exc))}"
        ) from exc
    validate_descriptor_string_fields(descriptor_set, root="FileDescriptorSet")
    return descriptor_set


def render_diagnostic_context(value: str) -> str:
    """Make descriptor-controlled text safe to include in a terminal diagnostic."""
    truncated = len(value) - _MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS
    preview = value[:_MAX_DIAGNOSTIC_CONTEXT_CODEPOINTS]
    rendered = "".join(
        char
        if char.isprintable()
        else (f"\\u{ord(char):04x}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08x}")
        for char in preview
    )
    if truncated > 0:
        rendered += f"... [truncated {truncated} characters]"
    return rendered


def _render_descriptor_bytes(value: bytes) -> str:
    truncated = len(value) - _MAX_DIAGNOSTIC_BYTES
    rendered = ascii(value[:_MAX_DIAGNOSTIC_BYTES])
    if truncated > 0:
        rendered += f"... [truncated {truncated} bytes]"
    return rendered


def validate_descriptor_string_fields(message: Message, *, root: str) -> None:
    """Reject malformed UTF-8 returned as bytes for protobuf string fields."""

    def validate_value(value: object, path: str) -> None:
        if isinstance(value, str):
            return
        if isinstance(value, bytes):
            raise ProtocyteError(
                "invalid UTF-8 in descriptor string field "
                f"{path}: {_render_descriptor_bytes(value)}"
            )
        raise ProtocyteError(
            f"descriptor string field {path} has invalid runtime type "
            f"{type(value).__name__}"
        )

    stack = [(message, root)]
    while stack:
        current, path = stack.pop()
        nested_messages: list[tuple[Message, str]] = []
        for field, value in current.ListFields():
            field_path = f"{path}.{field.name}"
            if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_STRING:
                if field.is_repeated:
                    for index, item in enumerate(value):
                        validate_value(item, f"{field_path}[{index}]")
                else:
                    validate_value(value, field_path)
                continue
            if field.type != descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
                continue
            if field.is_repeated:
                for index, item in enumerate(value):
                    nested_messages.append((item, f"{field_path}[{index}]"))
            else:
                nested_messages.append((value, field_path))
        stack.extend(reversed(nested_messages))


def validate_virtual_file_name(name: str) -> None:
    if not name:
        raise ProtocyteError("descriptor file name must not be empty")
    if name.startswith("-"):
        raise ProtocyteError(
            "descriptor file name must not begin with '-' because protoc "
            f"interprets it as an option: {render_diagnostic_context(name)}"
        )
    if "\0" in name:
        raise ProtocyteError(
            "descriptor file name contains a null character: "
            f"{render_diagnostic_context(name)}"
        )
    if "\\" in name:
        raise ProtocyteError(
            "descriptor file name must use '/' separators: "
            f"{render_diagnostic_context(name)}"
        )

    windows = PureWindowsPath(name)
    if name.startswith("/") or windows.root:
        raise ProtocyteError(
            "descriptor file name must be relative: "
            f"{render_diagnostic_context(name)}"
        )
    if any(part in {"", ".", ".."} for part in name.split("/")):
        raise ProtocyteError(
            "descriptor file name contains an unsafe path segment: "
            f"{render_diagnostic_context(name)}"
        )


def index_files(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
) -> dict[str, descriptor_pb2.FileDescriptorProto]:
    files: dict[str, descriptor_pb2.FileDescriptorProto] = {}
    for file in descriptor_set.file:
        validate_virtual_file_name(file.name)
        if file.name in files:
            raise ProtocyteError(
                "duplicate descriptor file name: "
                f"{render_diagnostic_context(file.name)}"
            )
        files[file.name] = file
    return files


def validate_descriptor_set(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
    selected_files: Iterable[str],
) -> list[str]:
    files = index_files(descriptor_set)
    selected = list(selected_files)
    for name in selected:
        validate_virtual_file_name(name)
        if name not in files:
            raise ProtocyteError(
                "selected descriptor file is not present: "
                f"{render_diagnostic_context(name)}"
            )

    _validate_import_graph(files, selected)
    return selected


def validate_generation_capabilities(
    files: dict[str, descriptor_pb2.FileDescriptorProto],
    selected_files: Iterable[str],
) -> None:
    """Reject capabilities that cannot participate in generated Protocyte headers.

    Protobuf permits a generator request to select only a consumer while a
    separately built library supplies an ordinary imported generated header.
    Keep that composition model intact while validating the full import closure
    with the same feature rules as model construction.  Also reject selected
    type references whose headers can never exist and cross-file type cycles
    which cannot be represented by the current include-based headers.
    """
    selected_list = list(selected_files)
    selected = set(selected_list)
    type_files = _index_declared_types(files.values())
    import_predecessors = _import_closure_predecessors(files, selected_list)

    for name in selected_list:
        blocker = _descriptor_capability_blocker(
            files[name], selected_for_generation=True
        )
        if blocker is not None:
            raise ProtocyteError(
                f"target file {_diagnostic_name(name)}: {blocker}"
            )

    for name in selected_list:
        if name in _INTERNAL_DESCRIPTOR_FILES:
            raise ProtocyteError(
                f"target file {_diagnostic_name(name)}: it is reserved for "
                "Protocyte generator internals"
            )

    for name in selected_list:
        file = files[name]
        for reference in _referenced_types(file):
            referenced = type_files.get(_normalize_type_name(reference.type_name))
            if referenced is None or referenced in selected:
                continue
            blocker = _generated_header_blocker(files[referenced])
            if blocker is not None:
                raise _non_generatable_reference_error(
                    file.name, reference, referenced, blocker
                )

    for name in import_predecessors:
        if name in selected:
            continue
        blocker = _descriptor_capability_blocker(
            files[name], selected_for_generation=False
        )
        if blocker is None:
            continue
        formatted_path = _format_import_path(name, import_predecessors)
        raise ProtocyteError(
            f"target file {_diagnostic_name(_import_root(name, import_predecessors))} "
            "imports unsupported "
            f"descriptor {_diagnostic_name(name)} through {formatted_path}: {blocker}"
        )

    _validate_no_cross_file_type_cycles(files, selected_list)


def discover_files(descriptor_set: descriptor_pb2.FileDescriptorSet) -> list[str]:
    files = index_files(descriptor_set)
    selected = {
        name
        for name, file in files.items()
        if not name.startswith(_RUNTIME_PREFIX) and _is_initial_discoverable_target(file)
    }
    type_files = _index_declared_types(files.values())
    stack = sorted(selected, reverse=True)
    while stack:
        file = files[stack.pop()]
        for reference in _referenced_types(file):
            referenced = type_files.get(_normalize_type_name(reference.type_name))
            if referenced is None or referenced in selected:
                continue
            blocker = _generated_header_blocker(files[referenced])
            if blocker is not None:
                raise _non_generatable_reference_error(
                    file.name, reference, referenced, blocker
                )
            selected.add(referenced)
            stack.append(referenced)

    selected_list = sorted(selected)
    _validate_import_graph(files, selected_list)
    validate_generation_capabilities(files, selected_list)
    return selected_list


def _is_initial_discoverable_target(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return (
        _is_referenced_type_discoverable(file)
        and not _is_pure_custom_option_definition(file)
    )


def _is_referenced_type_discoverable(file: descriptor_pb2.FileDescriptorProto) -> bool:
    if file.name in _INTERNAL_DESCRIPTOR_FILES:
        return False
    for extension, scope in _extension_declarations(file):
        if scope is not None and not is_custom_option_extension(extension):
            return False
    return True


def _generated_header_blocker(
    file: descriptor_pb2.FileDescriptorProto,
) -> str | None:
    if file.name in _INTERNAL_DESCRIPTOR_FILES:
        return "it is reserved for Protocyte generator internals"
    return _descriptor_capability_blocker(file, selected_for_generation=True)


def _descriptor_capability_blocker(
    file: descriptor_pb2.FileDescriptorProto,
    *,
    selected_for_generation: bool,
) -> str | None:
    if file.syntax == "editions" or file.edition:
        return "protobuf Editions are not supported in v1"

    for extension, scope in _extension_declarations(file):
        if is_custom_option_extension(extension):
            continue
        extension_name = _extension_name(file, extension, scope)
        if file.syntax == "proto3":
            return (
                f"extension {_diagnostic_name(extension_name)} extends unsupported "
                f"proto3 target {_diagnostic_name(extension.extendee)}"
            )
        if scope is not None and selected_for_generation:
            return (
                f"message {_diagnostic_name(scope.removeprefix('.'))}: extension "
                "declarations are not supported"
            )

    return _group_field_generation_blocker(file)


def _extension_name(
    file: descriptor_pb2.FileDescriptorProto,
    extension: descriptor_pb2.FieldDescriptorProto,
    scope: str | None,
) -> str:
    if scope is not None:
        return f"{scope.removeprefix('.')}.{extension.name}"
    package = tuple(part for part in file.package.split(".") if part)
    return _fully_qualified_name((*package, extension.name)).removeprefix(".")


def _group_field_generation_blocker(
    file: descriptor_pb2.FileDescriptorProto,
) -> str | None:
    package = tuple(part for part in file.package.split(".") if part)
    for message in file.message_type:
        blocker = _message_group_field_generation_blocker(
            message, (*package, message.name)
        )
        if blocker is not None:
            return blocker
    return None


def _message_group_field_generation_blocker(
    message: descriptor_pb2.DescriptorProto,
    path: tuple[str, ...],
) -> str | None:
    for field in message.field:
        if field.type == descriptor_pb2.FieldDescriptorProto.TYPE_GROUP:
            field_path = ".".join((*path, field.name))
            return f"field {_diagnostic_name(field_path)} uses unsupported groups"
    for nested in message.nested_type:
        blocker = _message_group_field_generation_blocker(nested, (*path, nested.name))
        if blocker is not None:
            return blocker
    return None


def _diagnostic_name(value: str) -> str:
    truncated = len(value) - _MAX_DIAGNOSTIC_NAME_CODEPOINTS
    escaped: list[str] = []
    for char in value[:_MAX_DIAGNOSTIC_NAME_CODEPOINTS]:
        if char == "\\":
            escaped.append("\\\\")
        elif char == '"':
            escaped.append('\\"')
        elif char.isprintable():
            escaped.append(char)
        else:
            codepoint = ord(char)
            width = 4 if codepoint <= 0xFFFF else 8
            prefix = "u" if width == 4 else "U"
            escaped.append(f"\\{prefix}{codepoint:0{width}x}")
    if truncated > 0:
        escaped.append(f"... [truncated {truncated} characters]")
    return f'"{"".join(escaped)}"'


def _non_generatable_reference_error(
    source_file: str,
    reference: _TypeReference,
    target_file: str,
    blocker: str,
) -> ProtocyteError:
    return ProtocyteError(
        f"descriptor {_diagnostic_name(source_file)}: field "
        f"{_diagnostic_name(reference.field_path)} references type "
        f"{_diagnostic_name(reference.type_name)} from "
        f"{_diagnostic_name(target_file)}, but {_diagnostic_name(target_file)} "
        f"cannot have a generated header because {blocker}"
    )


def _import_closure_predecessors(
    files: dict[str, descriptor_pb2.FileDescriptorProto],
    roots: Iterable[str],
) -> dict[str, str | None]:
    """Return one breadth-first predecessor per reachable import.

    Keep a single link for each file while scanning the closure.  Constructing
    and retaining a full path tuple for every dependency makes a linear import
    chain consume quadratic memory before a useful diagnostic is needed.
    """
    predecessors = {name: None for name in roots}
    queue = list(predecessors)
    index = 0
    while index < len(queue):
        name = queue[index]
        index += 1
        for dependency in files[name].dependency:
            if dependency not in files or dependency in predecessors:
                continue
            predecessors[dependency] = name
            queue.append(dependency)
    return predecessors


def _import_root(name: str, predecessors: dict[str, str | None]) -> str:
    current: str | None = name
    while current is not None:
        parent = predecessors[current]
        if parent is None:
            return current
        current = parent
    raise AssertionError("reachable import has no root")


def _format_import_path(name: str, predecessors: dict[str, str | None]) -> str:
    """Format a bounded suffix of an import chain only on a failing path."""
    suffix: list[str] = []
    current: str | None = name
    omitted = 0
    while current is not None:
        if len(suffix) < _MAX_DIAGNOSTIC_CHAIN_ENTRIES:
            suffix.append(current)
        else:
            omitted += 1
        current = predecessors[current]
    suffix.reverse()
    rendered = [_diagnostic_name(item) for item in suffix]
    if omitted:
        rendered.insert(0, f"... [{omitted} imports omitted]")
    return " -> ".join(rendered)


def _file_type_dependencies(
    files: dict[str, descriptor_pb2.FileDescriptorProto],
) -> dict[str, list[_FileTypeDependency]]:
    type_files = _index_declared_types(files.values())
    dependencies: dict[str, list[_FileTypeDependency]] = {}
    for source_name, file in files.items():
        for reference in _referenced_types(file):
            target_name = type_files.get(_normalize_type_name(reference.type_name))
            if target_name is None or target_name == source_name:
                continue
            dependencies.setdefault(source_name, []).append(
                _FileTypeDependency(source_name, target_name, reference)
            )
    for edges in dependencies.values():
        edges.sort(
            key=lambda edge: (
                edge.target_file,
                edge.reference.field_path,
                edge.reference.type_name,
            )
        )
    return dependencies


def _validate_no_cross_file_type_cycles(
    files: dict[str, descriptor_pb2.FileDescriptorProto],
    roots: Iterable[str],
) -> None:
    dependencies = _file_type_dependencies(files)
    visited: set[str] = set()

    for root in roots:
        if root in visited:
            continue

        active_indices = {root: 0}
        path_edges: list[_FileTypeDependency] = []
        # Each frame stores its next unexamined edge, so every reachable vertex
        # and edge is processed once without consuming Python's call stack.
        stack: list[tuple[str, int]] = [(root, 0)]
        while stack:
            name, edge_index = stack[-1]
            edges = dependencies.get(name, ())
            if edge_index == len(edges):
                stack.pop()
                active_indices.pop(name)
                visited.add(name)
                if path_edges:
                    path_edges.pop()
                continue

            edge = edges[edge_index]
            stack[-1] = (name, edge_index + 1)
            cycle_start = active_indices.get(edge.target_file)
            if cycle_start is not None:
                _raise_cross_file_type_cycle(path_edges, cycle_start, edge)
            if edge.target_file in visited:
                continue

            active_indices[edge.target_file] = len(stack)
            path_edges.append(edge)
            stack.append((edge.target_file, 0))


def _raise_cross_file_type_cycle(
    path_edges: list[_FileTypeDependency],
    cycle_start: int,
    closing_edge: _FileTypeDependency,
) -> None:
    cycle_edge_count = len(path_edges) - cycle_start + 1
    visible_path_count = min(cycle_edge_count - 1, _MAX_DIAGNOSTIC_CHAIN_ENTRIES - 1)
    edges = [
        *path_edges[cycle_start : cycle_start + visible_path_count],
        closing_edge,
    ]
    details = [
        f"{_diagnostic_name(edge.source_file)} field "
        f"{_diagnostic_name(edge.reference.field_path)} references type "
        f"{_diagnostic_name(edge.reference.type_name)} from "
        f"{_diagnostic_name(edge.target_file)}"
        for edge in edges
    ]
    if cycle_edge_count > len(edges):
        details.append(
            f"... [{cycle_edge_count - len(edges)} dependency edges omitted]"
        )
    raise ProtocyteError(f"generated header dependency cycle: {'; '.join(details)}")


def _is_pure_custom_option_definition(file: descriptor_pb2.FileDescriptorProto) -> bool:
    declarations = list(_extension_declarations(file))
    extensions = [extension for extension, _ in declarations]
    if (
        not extensions
        or any(not is_custom_option_extension(extension) for extension in extensions)
        or file.service
    ):
        return False
    declared_type_names = set(_declared_type_names(file))
    helper_roots = _custom_option_helper_roots(file, declarations, declared_type_names)
    return all(_is_extension_helper_type(type_name, helper_roots) for type_name in declared_type_names)


def _extension_declarations(
    file: descriptor_pb2.FileDescriptorProto,
) -> Iterable[tuple[descriptor_pb2.FieldDescriptorProto, str | None]]:
    for extension in file.extension:
        yield extension, None
    package = tuple(part for part in file.package.split(".") if part)
    for message in file.message_type:
        yield from _message_extension_declarations(message, (*package, message.name))


def _message_extension_declarations(
    message: descriptor_pb2.DescriptorProto,
    path: tuple[str, ...],
) -> Iterable[tuple[descriptor_pb2.FieldDescriptorProto, str]]:
    scope = _fully_qualified_name(path)
    for extension in message.extension:
        yield extension, scope
    for nested in message.nested_type:
        yield from _message_extension_declarations(nested, (*path, nested.name))


def _custom_option_helper_roots(
    file: descriptor_pb2.FileDescriptorProto,
    declarations: Iterable[tuple[descriptor_pb2.FieldDescriptorProto, str | None]],
    declared_type_names: set[str],
) -> set[str]:
    helper_roots = set[str]()
    for extension, _ in declarations:
        if extension.type_name:
            helper_roots.add(_normalize_type_name(extension.type_name))

    declared_messages = _index_declared_message_types(file)
    _expand_custom_option_helper_roots(declared_messages, declared_type_names, helper_roots)
    _add_namespace_container_roots(declared_messages, helper_roots)
    return helper_roots


def _expand_custom_option_helper_roots(
    declared_messages: dict[str, descriptor_pb2.DescriptorProto],
    declared_type_names: set[str],
    helper_roots: set[str],
) -> None:
    stack = list(helper_roots)
    while stack:
        root = stack.pop()
        for type_name, message in declared_messages.items():
            if not _is_extension_helper_type(type_name, {root}):
                continue
            for referenced in _message_direct_referenced_type_names(message):
                normalized = _normalize_type_name(referenced)
                if normalized in declared_type_names and not _is_extension_helper_type(normalized, helper_roots):
                    helper_roots.add(normalized)
                    stack.append(normalized)


def _add_namespace_container_roots(
    declared_messages: dict[str, descriptor_pb2.DescriptorProto],
    helper_roots: set[str],
) -> None:
    namespace_roots = set[str]()
    changed = True
    while changed:
        changed = False
        for type_name, message in declared_messages.items():
            if type_name in namespace_roots or _is_extension_helper_type(type_name, helper_roots):
                continue
            if _is_namespace_only_custom_option_scope(type_name, message, helper_roots, namespace_roots):
                namespace_roots.add(type_name)
                changed = True
    helper_roots.update(namespace_roots)


def _is_namespace_only_custom_option_scope(
    type_name: str,
    message: descriptor_pb2.DescriptorProto,
    helper_roots: set[str],
    namespace_roots: set[str],
) -> bool:
    if message.field or message.oneof_decl or message.extension_range or message.reserved_range or message.reserved_name:
        return False
    child_type_names = [
        *(f"{type_name}.{nested.name}" for nested in message.nested_type),
        *(f"{type_name}.{enum.name}" for enum in message.enum_type),
    ]
    if any(
        not _is_extension_helper_type(child_type_name, helper_roots) and child_type_name not in namespace_roots
        for child_type_name in child_type_names
    ):
        return False
    return bool(message.extension or child_type_names)


def _is_extension_helper_type(type_name: str, helper_roots: set[str]) -> bool:
    return any(type_name == root or type_name.startswith(f"{root}.") for root in helper_roots)


def _declared_type_names(file: descriptor_pb2.FileDescriptorProto) -> Iterable[str]:
    package = tuple(part for part in file.package.split(".") if part)
    for message in file.message_type:
        yield from _message_type_names(package, message)
    for enum in file.enum_type:
        yield _fully_qualified_name((*package, enum.name))


def _index_declared_message_types(
    file: descriptor_pb2.FileDescriptorProto,
) -> dict[str, descriptor_pb2.DescriptorProto]:
    declared: dict[str, descriptor_pb2.DescriptorProto] = {}
    package = tuple(part for part in file.package.split(".") if part)
    for message in file.message_type:
        _index_message_type(declared, package, message)
    return declared


def _index_message_type(
    declared: dict[str, descriptor_pb2.DescriptorProto],
    prefix: tuple[str, ...],
    message: descriptor_pb2.DescriptorProto,
) -> None:
    path = (*prefix, message.name)
    declared[_fully_qualified_name(path)] = message
    for nested in message.nested_type:
        _index_message_type(declared, path, nested)


def _index_declared_types(
    files: Iterable[descriptor_pb2.FileDescriptorProto],
) -> dict[str, str]:
    declared: dict[str, str] = {}
    for file in files:
        package = tuple(part for part in file.package.split(".") if part)
        for message in file.message_type:
            for type_name in _message_type_names(package, message):
                declared[type_name] = file.name
        for enum in file.enum_type:
            declared[_fully_qualified_name((*package, enum.name))] = file.name
    return declared


def _message_type_names(
    prefix: tuple[str, ...],
    message: descriptor_pb2.DescriptorProto,
) -> Iterable[str]:
    path = (*prefix, message.name)
    yield _fully_qualified_name(path)
    for nested in message.nested_type:
        yield from _message_type_names(path, nested)
    for enum in message.enum_type:
        yield _fully_qualified_name((*path, enum.name))


def _referenced_types(file: descriptor_pb2.FileDescriptorProto) -> Iterable[_TypeReference]:
    package = tuple(part for part in file.package.split(".") if part)
    for message in file.message_type:
        yield from _message_referenced_types(message, (*package, message.name))


def _message_referenced_types(
    message: descriptor_pb2.DescriptorProto,
    path: tuple[str, ...],
) -> Iterable[_TypeReference]:
    for field in message.field:
        if field.type_name:
            yield _TypeReference(field.type_name, ".".join((*path, field.name)))
    for nested in message.nested_type:
        yield from _message_referenced_types(nested, (*path, nested.name))


def _message_direct_referenced_type_names(
    message: descriptor_pb2.DescriptorProto,
) -> Iterable[str]:
    for field in message.field:
        if field.type_name:
            yield field.type_name


def _fully_qualified_name(parts: Iterable[str]) -> str:
    return "." + ".".join(part for part in parts if part)


def _normalize_type_name(type_name: str) -> str:
    if type_name.startswith("."):
        return type_name
    return f".{type_name}"


def _validate_import_graph(
    files: dict[str, descriptor_pb2.FileDescriptorProto],
    roots: Iterable[str],
) -> None:
    stack = list(roots)
    seen: set[str] = set()
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        file = files[name]
        for dependency in file.dependency:
            validate_virtual_file_name(dependency)
            if dependency not in files:
                raise ProtocyteError(
                    f"{render_diagnostic_context(name)} imports missing descriptor "
                    f"{render_diagnostic_context(dependency)}"
                )
            stack.append(dependency)


def main(
    argv: list[str] | None = None,
    *,
    prog: str = "protoc-gen-protocyte descriptor-set",
) -> int:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Inspect a binary protobuf FileDescriptorSet and determine which files "
            "Protocyte would generate."
        ),
        epilog=(
            "Create a descriptor set with protoc, including imported descriptors:\n"
            "  protoc --proto_path=. --include_imports "
            "--descriptor_set_out=descriptor_set.pb schema.proto\n\n"
            "Then inspect it with:\n"
            "  protoc-gen-protocyte descriptor-set list descriptor_set.pb"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="commands",
    )

    list_parser = subparsers.add_parser(
        "list",
        help="list the descriptor files Protocyte would generate",
        description=(
            "List the descriptor files Protocyte would generate. The result is written "
            "to standard output as a sorted JSON array of virtual .proto file names."
        ),
    )
    list_parser.add_argument(
        "descriptor_set",
        metavar="FILE",
        type=Path,
        help="path to a binary protobuf FileDescriptorSet",
    )

    dependency_parser = subparsers.add_parser(
        "dependency-file",
        help="write an escaped CMake depfile for an include-complete descriptor set",
    )
    dependency_parser.add_argument("descriptor_set", type=Path)
    dependency_parser.add_argument("protoc_argument_file", type=Path)
    dependency_parser.add_argument("output", type=Path)
    dependency_parser.add_argument("target", type=Path)
    dependency_parser.add_argument(
        "--msbuild",
        action="store_true",
        help="encode semicolons using MSBuild's percent escape",
    )
    dependency_parser.add_argument(
        "--ninja",
        action="store_true",
        help="emit Ninja-native dependency path syntax",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            print(json.dumps(discover_files(load_descriptor_set(args.descriptor_set))))
            return 0
        if args.command == "dependency-file":
            from protocyte.dependency_file import write_dependency_file

            write_dependency_file(
                load_descriptor_set(args.descriptor_set),
                protoc_argument_file=args.protoc_argument_file,
                output=args.output,
                target=args.target,
                msbuild=args.msbuild,
                ninja=args.ninja,
            )
            return 0
    except ProtocyteError as exc:
        parser.exit(1, f"protocyte: {render_diagnostic_context(str(exc))}\n")
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
