import importlib.util
import zipfile
from pathlib import Path

import pytest


def _load_install_protoc_module():
    script_path = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "install_protoc.py"
    spec = importlib.util.spec_from_file_location("install_protoc", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install_protoc = _load_install_protoc_module()


def _write_archive(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, "content")


def test_extract_archive_safely_preserves_normal_archive_layout(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(
        archive_path,
        [
            "bin/protoc",
            "include/google/protobuf/descriptor.proto",
        ],
    )

    with zipfile.ZipFile(archive_path) as archive:
        install_protoc.extract_archive_safely(archive, destination)

    assert (destination / "bin" / "protoc").read_text(encoding="utf-8") == "content"
    assert (destination / "include" / "google" / "protobuf" / "descriptor.proto").is_file()


@pytest.mark.parametrize(
    "member",
    [
        "/tmp/protoc",
        r"C:\tmp\protoc.exe",
        r"\tmp\protoc.exe",
        "../protoc",
        "bin/../../protoc",
        r"bin\..\protoc.exe",
    ],
)
def test_extract_archive_safely_rejects_absolute_or_parent_traversal_members(
    tmp_path: Path,
    member: str,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, [member, "bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="unsafe"):
            install_protoc.extract_archive_safely(archive, destination)

    assert not destination.exists()
