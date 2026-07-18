from __future__ import annotations

import os
from pathlib import Path, PurePath

from google.protobuf import descriptor_pb2

from protocyte.descriptor_set import index_files
from protocyte.errors import ProtocyteError


def write_dependency_file(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
    *,
    protoc_argument_file: str | Path,
    output: str | Path,
    target: str | Path,
    working_directory: str | Path | None = None,
    msbuild: bool = False,
    ninja: bool = False,
) -> None:
    """Write a CMake-compatible GCC depfile for an include-complete descriptor set."""
    roots, direct_input = _protoc_scan_context(
        protoc_argument_file,
        working_directory=working_directory,
    )
    dependencies = _resolve_descriptor_files(descriptor_set, roots)
    if msbuild or ninja:
        backend = "Visual Studio" if msbuild else "Ninja"
        direct_input_key = os.path.normcase(str(direct_input))
        tracked_dependencies: list[Path] = []
        for dependency in dependencies:
            if ";" not in str(dependency):
                tracked_dependencies.append(dependency)
                continue
            if os.path.normcase(str(dependency)) == direct_input_key:
                # The direct input is already represented by a safe proxy in
                # the build graph for generators that cannot encode it.
                continue
            raise ProtocyteError(
                f"{backend} cannot track an imported protobuf dependency "
                f"whose path contains ';': {dependency}. Use a generator that can "
                "track this path or rename the imported file."
            )
        dependencies = tracked_dependencies
    escaped_target = _escape_depfile_path(
        Path(target), msbuild=msbuild, ninja=ninja
    )
    escaped_dependencies = [
        _escape_depfile_path(dependency, msbuild=msbuild, ninja=ninja)
        for dependency in dependencies
    ]
    content = escaped_target + ":"
    for dependency in escaped_dependencies:
        content += f" \\\n {dependency}"
    content += "\n"

    output_path = Path(output)
    try:
        output_path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise ProtocyteError(
            f"failed to write dependency file {output}: {exc}"
        ) from exc


def _protoc_scan_context(
    argument_file: str | Path,
    *,
    working_directory: str | Path | None,
) -> tuple[list[Path], Path]:
    try:
        arguments = Path(argument_file).read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeError) as exc:
        raise ProtocyteError(
            f"failed to read protoc argument file {argument_file}: {exc}"
        ) from exc

    base = Path.cwd() if working_directory is None else Path(working_directory)
    roots: list[Path] = []
    inputs: list[Path] = []
    seen: set[str] = set()
    for argument in arguments:
        if not argument:
            continue
        if not argument.startswith("-"):
            input_path = Path(argument)
            if not input_path.is_absolute():
                input_path = base / input_path
            inputs.append(Path(os.path.abspath(input_path)))
            continue
        if not argument.startswith("--proto_path="):
            continue
        raw_root = argument.removeprefix("--proto_path=")
        if not raw_root:
            raise ProtocyteError(
                f"protoc argument file {argument_file} contains an empty --proto_path"
            )
        root = Path(raw_root)
        if not root.is_absolute():
            root = base / root
        root = Path(os.path.abspath(root))
        key = os.path.normcase(str(root))
        if key not in seen:
            seen.add(key)
            roots.append(root)

    if not roots:
        raise ProtocyteError(
            f"protoc argument file {argument_file} does not contain --proto_path"
        )
    if len(inputs) != 1:
        raise ProtocyteError(
            f"protoc argument file {argument_file} must contain exactly one input file"
        )
    return roots, inputs[0]


def _resolve_descriptor_files(
    descriptor_set: descriptor_pb2.FileDescriptorSet,
    roots: list[Path],
) -> list[Path]:
    files = index_files(descriptor_set)
    resolved: dict[str, Path] = {}
    for name in files:
        dependency = next(
            (
                candidate
                for root in roots
                if (candidate := root.joinpath(*name.split("/"))).is_file()
            ),
            None,
        )
        if dependency is None:
            roots_text = ", ".join(str(root) for root in roots)
            raise ProtocyteError(
                f"descriptor dependency {name!r} was not found under protoc import roots: "
                f"{roots_text}"
            )
        dependency = Path(os.path.abspath(dependency))
        resolved.setdefault(os.path.normcase(str(dependency)), dependency)
    return sorted(resolved.values(), key=lambda path: path.as_posix().casefold())


def _escape_depfile_path(
    path: PurePath,
    *,
    msbuild: bool = False,
    ninja: bool = False,
) -> str:
    if msbuild and ninja:
        raise ProtocyteError("dependency file format cannot be both MSBuild and Ninja")
    value = path.as_posix()
    if any(character in value for character in "\r\n\t"):
        raise ProtocyteError(
            f"dependency path contains whitespace that CMake depfiles cannot represent: {value!r}"
        )
    if "\\" in value:
        raise ProtocyteError(
            f"dependency path contains a backslash that CMake depfiles cannot represent: {value!r}"
        )
    drive = path.drive
    has_absolute_windows_drive = (
        len(drive) == 2
        and drive[0].isalpha()
        and drive[1] == ":"
        and value.startswith(f"{drive}/")
    )
    colon_search_start = len(drive) if has_absolute_windows_drive else 0
    if ":" in value[colon_search_start:]:
        raise ProtocyteError(
            f"dependency path contains a colon that CMake depfiles cannot represent safely: {value!r}"
        )
    value = (
        value.replace("$", "$$")
        .replace("#", "\\#")
        .replace(" ", "\\ ")
    )
    if ninja:
        return value
    return value.replace(";", "%25253B" if msbuild else "\\;")
