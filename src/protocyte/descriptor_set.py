from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath

from google.protobuf import descriptor_pb2
from google.protobuf.message import DecodeError

from protocyte.errors import ProtocyteError


_RUNTIME_PREFIX = "google/protobuf/"


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
    selected = sorted(name for name in files if not name.startswith(_RUNTIME_PREFIX))
    _validate_import_graph(files, selected)
    return selected


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
