from pathlib import Path, PurePosixPath

import pytest
from google.protobuf import descriptor_pb2

from protocyte.dependency_file import _escape_depfile_path, write_dependency_file
from protocyte.errors import ProtocyteError


def _escape(path: Path) -> str:
    return (
        path.as_posix()
        .replace("$", "$$")
        .replace("#", "\\#")
        .replace(" ", "\\ ")
        .replace(";", "\\;")
    )


def test_write_dependency_file_escapes_cmake_special_paths(tmp_path: Path) -> None:
    import_root = tmp_path / "import root #$;"
    source = import_root / "api" / "consumer #$;.proto"
    imported = import_root / "shared value #$;.proto"
    source.parent.mkdir(parents=True)
    source.write_text('syntax = "proto3";\n', encoding="utf-8")
    imported.write_text('syntax = "proto3";\n', encoding="utf-8")

    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.add().name = "api/consumer #$;.proto"
    descriptor_set.file.add().name = "shared value #$;.proto"
    argument_file = tmp_path / "arguments.rsp"
    argument_file.write_text(
        f"--proto_path={import_root.as_posix()}\n--include_imports\n{source.as_posix()}\n",
        encoding="utf-8",
        newline="\n",
    )
    output = tmp_path / "dependencies.d"
    target = Path("CMakeFiles/generated output #$;.pb")

    write_dependency_file(
        descriptor_set,
        protoc_argument_file=argument_file,
        output=output,
        target=target,
    )

    dependencies = sorted(
        (source.resolve(), imported.resolve()),
        key=lambda path: path.as_posix().casefold(),
    )
    expected = _escape(target) + ":"
    for dependency in dependencies:
        expected += f" \\\n {_escape(dependency)}"
    expected += "\n"
    assert output.read_text(encoding="utf-8") == expected


def test_write_dependency_file_rejects_unresolved_descriptor(tmp_path: Path) -> None:
    import_root = tmp_path / "imports"
    import_root.mkdir()
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.add().name = "missing.proto"
    argument_file = tmp_path / "arguments.rsp"
    argument_file.write_text(
        f"--proto_path={import_root.as_posix()}\nmissing.proto\n", encoding="utf-8"
    )

    with pytest.raises(ProtocyteError, match="missing.proto.*was not found"):
        write_dependency_file(
            descriptor_set,
            protoc_argument_file=argument_file,
            output=tmp_path / "dependencies.d",
            target="generated.pb",
        )


def test_dependency_file_uses_msbuild_semicolon_escape() -> None:
    assert (
        _escape_depfile_path(PurePosixPath("generated;legacy.pb"), msbuild=True)
        == "generated%25253Blegacy.pb"
    )


def test_msbuild_depfile_omits_direct_semicolon_input(tmp_path: Path) -> None:
    import_root = tmp_path / "imports"
    source = import_root / "demo;legacy.proto"
    imported = import_root / "shared.proto"
    import_root.mkdir()
    source.write_text('syntax = "proto3";\n', encoding="utf-8")
    imported.write_text('syntax = "proto3";\n', encoding="utf-8")

    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.add().name = source.name
    descriptor_set.file.add().name = imported.name
    argument_file = tmp_path / "arguments.rsp"
    argument_file.write_text(
        f"--proto_path={import_root.as_posix()}\n{source.as_posix()}\n",
        encoding="utf-8",
    )
    output = tmp_path / "dependencies.d"

    write_dependency_file(
        descriptor_set,
        protoc_argument_file=argument_file,
        output=output,
        target="generated.pb",
        msbuild=True,
    )

    content = output.read_text(encoding="utf-8")
    assert source.as_posix() not in content
    assert imported.as_posix() in content


def test_msbuild_depfile_rejects_imported_semicolon_path(tmp_path: Path) -> None:
    import_root = tmp_path / "imports"
    source = import_root / "demo.proto"
    imported = import_root / "shared;legacy.proto"
    import_root.mkdir()
    source.write_text('syntax = "proto3";\n', encoding="utf-8")
    imported.write_text('syntax = "proto3";\n', encoding="utf-8")

    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.add().name = source.name
    descriptor_set.file.add().name = imported.name
    argument_file = tmp_path / "arguments.rsp"
    argument_file.write_text(
        f"--proto_path={import_root.as_posix()}\n{source.as_posix()}\n",
        encoding="utf-8",
    )

    with pytest.raises(ProtocyteError, match="Visual Studio.*imported.*contains ';'"):
        write_dependency_file(
            descriptor_set,
            protoc_argument_file=argument_file,
            output=tmp_path / "dependencies.d",
            target="generated.pb",
            msbuild=True,
        )


@pytest.mark.parametrize(
    ("path", "character"),
    [
        (PurePosixPath("generated:unsafe.pb"), "colon"),
        (PurePosixPath("C:drive-relative.pb"), "colon"),
        (PurePosixPath(r"generated\unsafe.pb"), "backslash"),
    ],
)
def test_dependency_file_rejects_unrepresentable_paths(
    path: PurePosixPath, character: str
) -> None:
    with pytest.raises(ProtocyteError, match=character):
        _escape_depfile_path(path)
