from pathlib import Path

import pytest
from google.protobuf import descriptor_pb2

from protocyte.descriptor_set import (
    discover_files,
    load_descriptor_set,
    validate_descriptor_set,
    validate_virtual_file_name,
)
from protocyte.errors import ProtocyteError


def _file(name: str, *dependencies: str) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = name
    file.syntax = "proto3"
    file.dependency.extend(dependencies)
    file.message_type.add().name = "Sample"
    return file


def _write_descriptor_set(path: Path, *files: descriptor_pb2.FileDescriptorProto) -> None:
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.extend(files)
    path.write_bytes(descriptor_set.SerializeToString())


def test_load_descriptor_set_reports_invalid_bytes(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    path.write_bytes(b"not a descriptor set")

    with pytest.raises(ProtocyteError, match="failed to parse FileDescriptorSet"):
        load_descriptor_set(path)


def test_validate_descriptor_set_rejects_duplicate_file_names(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file("demo.proto"), _file("demo.proto"))

    with pytest.raises(ProtocyteError, match="duplicate descriptor file name: demo.proto"):
        validate_descriptor_set(load_descriptor_set(path), ["demo.proto"])


def test_validate_descriptor_set_rejects_missing_selected_file(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file("present.proto"))

    with pytest.raises(ProtocyteError, match="selected descriptor file is not present: missing.proto"):
        validate_descriptor_set(load_descriptor_set(path), ["missing.proto"])


def test_validate_descriptor_set_rejects_missing_import(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(path, _file("user.proto", "missing.proto"))

    with pytest.raises(ProtocyteError, match="user.proto imports missing descriptor missing.proto"):
        validate_descriptor_set(load_descriptor_set(path), ["user.proto"])


@pytest.mark.parametrize(
    "name",
    [
        "",
        "../demo.proto",
        "nested/../demo.proto",
        ".",
        "./demo.proto",
        "nested/./demo.proto",
        "demo.proto/",
        "a//b.proto",
        "/demo.proto",
        r"C:\demo.proto",
        r"nested\demo.proto",
    ],
)
def test_validate_virtual_file_name_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(ProtocyteError):
        validate_virtual_file_name(name)


def test_discover_files_skips_google_protobuf_runtime_descriptors(tmp_path: Path) -> None:
    path = tmp_path / "descriptor_set.pb"
    _write_descriptor_set(
        path,
        _file("google/protobuf/descriptor.proto"),
        _file("nested/user.proto", "google/protobuf/descriptor.proto"),
    )

    assert discover_files(load_descriptor_set(path)) == ["nested/user.proto"]
