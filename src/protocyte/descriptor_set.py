from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath

from google.protobuf import descriptor_pb2
from google.protobuf.message import DecodeError

from protocyte.errors import ProtocyteError


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
        and not _declares_google_protobuf_option_extension(file)
    )


def _is_referenced_type_discoverable(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return file.name not in _INTERNAL_DESCRIPTOR_FILES and not _declares_message_scoped_extensions(file)


def _declares_google_protobuf_option_extension(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return any(extension.extendee.startswith(".google.protobuf.") for extension in file.extension)


def _declares_message_scoped_extensions(file: descriptor_pb2.FileDescriptorProto) -> bool:
    return any(_message_declares_extensions(message) for message in file.message_type)


def _message_declares_extensions(message: descriptor_pb2.DescriptorProto) -> bool:
    if message.extension:
        return True
    return any(_message_declares_extensions(nested) for nested in message.nested_type)


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
    for field in message.field:
        if field.type_name:
            yield field.type_name
    for nested in message.nested_type:
        yield from _message_referenced_type_names(nested)


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
