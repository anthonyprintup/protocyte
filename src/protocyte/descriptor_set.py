from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath

from google.protobuf import descriptor_pb2
from google.protobuf.message import DecodeError

from protocyte.errors import ProtocyteError
from protocyte.extensions import is_custom_option_extension


_RUNTIME_PREFIX = "google/protobuf/"
_INTERNAL_DESCRIPTOR_FILES = {"protocyte/options.proto"}


def load_descriptor_set(path: str | Path) -> descriptor_pb2.FileDescriptorSet:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    try:
        descriptor_set.ParseFromString(Path(path).read_bytes())
    except OSError as exc:
        raise ProtocyteError(f"failed to read descriptor set {path}: {exc}") from exc
    except DecodeError as exc:
        raise ProtocyteError(f"failed to parse FileDescriptorSet {path}: {exc}") from exc
    return descriptor_set


def validate_virtual_file_name(name: str) -> None:
    if not name:
        raise ProtocyteError("descriptor file name must not be empty")
    if "\\" in name:
        raise ProtocyteError(f"descriptor file name must use '/' separators: {name}")

    windows = PureWindowsPath(name)
    if name.startswith("/") or windows.drive or windows.root:
        raise ProtocyteError(f"descriptor file name must be relative: {name}")
    if any(part in {"", ".", ".."} for part in name.split("/")):
        raise ProtocyteError(f"descriptor file name contains an unsafe path segment: {name}")


def index_files(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
) -> dict[str, descriptor_pb2.FileDescriptorProto]:
    files: dict[str, descriptor_pb2.FileDescriptorProto] = {}
    for file in descriptor_set.file:
        validate_virtual_file_name(file.name)
        if file.name in files:
            raise ProtocyteError(f"duplicate descriptor file name: {file.name}")
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
            raise ProtocyteError(f"selected descriptor file is not present: {name}")

    _validate_import_graph(files, selected)
    return selected


def discover_files(descriptor_set: descriptor_pb2.FileDescriptorSet) -> list[str]:
    files = index_files(descriptor_set)
    selected = {
        name
        for name, file in files.items()
        if not name.startswith(_RUNTIME_PREFIX) and _is_initial_discoverable_target(file)
    }
    type_files = _index_declared_types(files.values())
    stack = list(selected)
    while stack:
        file = files[stack.pop()]
        for type_name in _referenced_type_names(file):
            referenced = type_files.get(_normalize_type_name(type_name))
            if (
                referenced is None
                or referenced in selected
                or not _is_referenced_type_discoverable(files[referenced])
            ):
                continue
            selected.add(referenced)
            stack.append(referenced)

    selected_list = sorted(selected)
    _validate_import_graph(files, selected_list)
    return selected_list


def _is_initial_discoverable_target(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return (
        _is_referenced_type_discoverable(file)
        and not _is_pure_custom_option_definition(file)
    )


def _is_referenced_type_discoverable(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return file.name not in _INTERNAL_DESCRIPTOR_FILES and not _declares_unsupported_message_scoped_extensions(file)


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


def _declares_unsupported_message_scoped_extensions(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return any(_message_declares_unsupported_extensions(message) for message in file.message_type)


def _message_declares_unsupported_extensions(message: descriptor_pb2.DescriptorProto) -> bool:
    if any(not is_custom_option_extension(extension) for extension in message.extension):
        return True
    return any(_message_declares_unsupported_extensions(nested) for nested in message.nested_type)


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


def _referenced_type_names(file: descriptor_pb2.FileDescriptorProto) -> Iterable[str]:
    for message in file.message_type:
        yield from _message_referenced_type_names(message)


def _message_referenced_type_names(
    message: descriptor_pb2.DescriptorProto,
) -> Iterable[str]:
    yield from _message_direct_referenced_type_names(message)
    for nested in message.nested_type:
        yield from _message_referenced_type_names(nested)


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
                raise ProtocyteError(f"{name} imports missing descriptor {dependency}")
            stack.append(dependency)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a protobuf FileDescriptorSet.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list generated descriptor files")
    list_parser.add_argument("descriptor_set", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for name in discover_files(load_descriptor_set(args.descriptor_set)):
                print(name)
            return 0
    except ProtocyteError as exc:
        parser.exit(1, f"protocyte: {exc}\n")
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
