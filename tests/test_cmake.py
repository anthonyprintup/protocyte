from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Never

import pytest
from google.protobuf import descriptor_pb2

from protocyte import __version__
from protocyte.paths import generated_file_base


_CI_PROTOC_ENV = "PROTOCYTE_CI_PROTOC_EXECUTABLE"
_CI_REQUIRE_INCREMENTAL_TEST_ENV = "PROTOCYTE_CI_REQUIRE_INCREMENTAL_TEST"


def _incremental_requirement_unavailable(message: str) -> Never:
    if os.environ.get(_CI_REQUIRE_INCREMENTAL_TEST_ENV) == "1":
        pytest.fail(message)
    pytest.skip(message)


def _find_real_protoc(repo_root: Path) -> Path:
    candidates: list[Path] = []
    if configured := os.environ.get(_CI_PROTOC_ENV):
        protoc = Path(configured)
        if not protoc.is_file():
            pytest.fail(f"{_CI_PROTOC_ENV} does not name a file: {protoc}")
        return protoc

    if found := shutil.which("protoc"):
        candidates.append(Path(found))

    executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    for root in (repo_root / "build", repo_root / "tests"):
        if root.exists():
            candidates.extend(root.glob(f"**/{executable_name}"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    _incremental_requirement_unavailable("real protoc executable is not available")


def _find_protobuf_import_root(repo_root: Path) -> Path:
    for root in (repo_root / "build", repo_root / "tests"):
        for descriptor in root.glob(
            "**/protobuf-src/src/google/protobuf/descriptor.proto"
        ):
            return descriptor.parents[2]
    pytest.skip("protobuf source import tree is not available")


def _find_protobuf_import_dir(repo_root: Path, protoc: Path) -> Path:
    candidates = [
        protoc.parent.parent / "include",
        protoc.parent.parent / "protobuf-src" / "src",
        protoc.parents[2] / "include",
    ]
    for root in (repo_root / "build", repo_root / "tests"):
        if not root.exists():
            continue
        candidates.extend(
            descriptor.parents[2]
            for descriptor in root.glob("**/google/protobuf/descriptor.proto")
        )

    for candidate in candidates:
        if (candidate / "google" / "protobuf" / "descriptor.proto").is_file():
            return candidate

    _incremental_requirement_unavailable(
        "protobuf import directory is not available"
    )


def _configure_cmake_snippet(
    tmp_path: Path,
    snippet: str,
    *,
    files: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    for relative_path, content in (files or {}).items():
        path = source_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(protocyte_argument_validation LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                snippet,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )


def _write_python_plugin_wrapper(path: Path, repo_root: Path) -> Path:
    if os.name == "nt":
        wrapper = path.with_suffix(".cmd")
        wrapper.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    f'set "PYTHONPATH={repo_root / "src"};%PYTHONPATH%"',
                    f'"{sys.executable}" -m protocyte.main %*',
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        wrapper = path
        wrapper.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env sh",
                    f'PYTHONPATH="{repo_root / "src"}:$PYTHONPATH" exec "{sys.executable}" -m protocyte.main "$@"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
    return wrapper


def _write_protoc_wrapper(path: Path, protoc: Path, invocation_log: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        wrapper = path.with_suffix(".cmd")
        wrapper.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    f'echo invoked>>"{invocation_log}"',
                    f'"{protoc}" %*',
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        wrapper = path
        wrapper.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env sh",
                    f"printf 'invoked\\n' >> {shlex.quote(str(invocation_log))}",
                    f'exec {shlex.quote(str(protoc))} "$@"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
    return wrapper


def _touch_newer_than(path: Path, output: Path) -> None:
    changed_mtime_ns = (
        max(path.stat().st_mtime_ns, output.stat().st_mtime_ns) + 2_000_000_000
    )
    os.utime(path, ns=(changed_mtime_ns, changed_mtime_ns))


def _installed_protocyte_plugin() -> Path:
    executable_name = (
        "protoc-gen-protocyte.exe" if os.name == "nt" else "protoc-gen-protocyte"
    )
    plugin = Path(sys.executable).with_name(executable_name)
    assert plugin.is_file(), f"installed Protocyte plugin is missing: {plugin}"
    return plugin


def _write_incompatible_protocyte_plugin(path: Path) -> Path:
    if os.name == "nt":
        plugin = path.with_suffix(".cmd")
        plugin.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    'if "%~1"=="--version" (',
                    f"  echo {__version__}",
                    "  exit /b 0",
                    ")",
                    "echo old plugin cannot discover 1>&2",
                    "exit /b 4",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        plugin = path
        plugin.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env sh",
                    f'[ "$1" = "--version" ] && echo "{__version__}" && exit 0',
                    "echo 'old plugin cannot discover' >&2",
                    "exit 4",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        plugin.chmod(0o755)
    return plugin


def _write_version_only_plugin(path: Path, version: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        plugin = path.with_suffix(".cmd")
        plugin.write_text(
            f"@echo off\r\necho {version}\r\n",
            encoding="utf-8",
        )
    else:
        plugin = path
        plugin.write_text(
            f"#!/usr/bin/env sh\necho '{version}'\n",
            encoding="utf-8",
        )
        plugin.chmod(0o755)
    return plugin


def test_installed_cmake_config_tracks_descriptor_set_helper() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_config = (repo_root / "cmake" / "Protocyte.cmake").read_text(
        encoding="utf-8"
    )
    installed_config = (repo_root / "cmake" / "protocyteConfig.cmake.in").read_text(
        encoding="utf-8"
    )

    assert '"${PROTOCYTE_PACKAGE_ROOT}/descriptor_set.py"' in source_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/descriptor_set.py"' in installed_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/extensions.py"' in source_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/extensions.py"' in installed_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/_deterministic_math.py"' in source_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/_deterministic_math.py"' in installed_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/paths.py"' in source_config
    assert '"${PROTOCYTE_PACKAGE_ROOT}/paths.py"' in installed_config
    assert "PROTOCYTE_INTERNAL_PYTHON_PROJECT_ROOT" in source_config
    assert "PROTOCYTE_INTERNAL_PYTHON_PROJECT_ROOT" in installed_config
    assert "PROTOCYTE_INTERNAL_PYTHON_CONSTRAINTS" in source_config
    assert "PROTOCYTE_INTERNAL_PYTHON_CONSTRAINTS" in installed_config
    assert "PROTOCYTE_INTERNAL_PYTHON_ENV_ROOT" in source_config
    assert "PROTOCYTE_INTERNAL_PYTHON_ENV_ROOT" in installed_config
    assert "PROTOCYTE_INTERNAL_VERSION" in source_config
    assert "PROTOCYTE_INTERNAL_VERSION" in installed_config
    assert '"${PROTOCYTE_PYTHON_PROJECT_ROOT}/src"' in installed_config


def test_explicit_plugin_override_must_exist(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    missing = tmp_path / "missing" / "protoc-gen-protocyte"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{missing.as_posix()}")',
                "_protocyte_prepare_plugin()",
            ]
        ),
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "does not name an existing file" in output


def test_explicit_plugin_override_must_match_package_version(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    plugin = _write_version_only_plugin(
        tmp_path / "tools" / "protoc-gen-protocyte", "99.0.0"
    )
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                "_protocyte_prepare_plugin()",
            ]
        ),
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert f"CMake package {__version__}" in output
    assert "plugin reported 99.0.0" in output


def test_explicit_plugin_change_rechecks_version_on_build(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(explicit_plugin_reconfigure LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                "_protocyte_prepare_plugin()",
                "add_custom_target(noop)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    original_mtime_ns = plugin.stat().st_mtime_ns
    _write_version_only_plugin(plugin.with_suffix(""), "99.0.0")
    changed_mtime_ns = max(plugin.stat().st_mtime_ns, original_mtime_ns + 2_000_000_000)
    os.utime(plugin, ns=(changed_mtime_ns, changed_mtime_ns))

    result = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "noop"],
        check=False,
        capture_output=True,
        text=True,
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert f"CMake package {__version__}" in output
    assert "plugin reported 99.0.0" in output


def test_cmake_generation_uses_consumer_source_directory_for_style_lookup() -> None:
    functions = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteFunctions.cmake"
    ).read_text(encoding="utf-8")
    generation_command = functions.split("add_custom_command(", 1)[1].split(
        "add_custom_target", 1
    )[0]

    assert 'WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"' in generation_command
    assert '"${protocyte_plugin_executable}"' in generation_command.split("DEPENDS", 1)[1]


def test_quickstart_tracks_protoc_as_a_generation_dependency() -> None:
    quickstart = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "quickstart"
        / "CMakeLists.txt"
    ).read_text(encoding="utf-8")
    generation_dependencies = quickstart.split("DEPENDS", 1)[1].split("COMMENT", 1)[0]

    assert '"${PROTOC_EXECUTABLE}"' in generation_dependencies


@pytest.mark.parametrize(
    ("descriptor_name", "expected"),
    [
        ('api/bad"name.proto', "api/bad~22name.protocyte"),
        ("api/café.proto", "api/caf~C3~A9.protocyte"),
        ("api/demo;legacy.proto", "api/demo~3Blegacy.protocyte"),
        ("CON.proto", "~43ON.protocyte"),
        ("api/literal~22.proto", "api/literal~7E22.protocyte"),
    ],
)
def test_cmake_normalizes_generated_paths_like_the_plugin(
    tmp_path: Path, descriptor_name: str, expected: str
) -> None:
    output = tmp_path / "normalized.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f"_protocyte_normalize_generated_path(normalized [==[{descriptor_name}]==])",
                f'file(WRITE "{output.as_posix()}" "${{normalized}}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == expected


def test_cmake_bounds_long_generated_components_like_the_plugin(
    tmp_path: Path,
) -> None:
    long_segment = "é" * 50
    descriptor_name = f"{long_segment}/{long_segment}.proto"
    expected = generated_file_base(descriptor_name)
    output = tmp_path / "normalized.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f"_protocyte_normalize_generated_path(normalized [==[{descriptor_name}]==])",
                f'file(WRITE "{output.as_posix()}" "${{normalized}}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == expected
    directory, filename_base = expected.split("/")
    assert len(directory.encode("ascii")) == 255
    assert len(f"{filename_base}.hpp".encode("ascii")) == 255


@pytest.mark.parametrize(
    ("function_name", "invocation"),
    [
        ("protocyte_generate", "protocyte_generate(HOSTED_ALOCATOR)"),
        (
            "protocyte_add_proto_library",
            "protocyte_add_proto_library(HOSTED_ALOCATOR)",
        ),
        (
            "protocyte_add_descriptor_set_library",
            "protocyte_add_descriptor_set_library(HOSTED_ALOCATOR)",
        ),
    ],
)
def test_public_cmake_functions_reject_unknown_arguments(
    tmp_path: Path,
    function_name: str,
    invocation: str,
) -> None:
    result = _configure_cmake_snippet(tmp_path, invocation)

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert f"{function_name} received unknown argument(s): HOSTED_ALOCATOR" in output


@pytest.mark.parametrize(
    ("arguments", "expected_arguments"),
    [
        ("TYPO_IS_SILENTLY_IGNORED", "TYPO_IS_SILENTLY_IGNORED"),
        (
            "PROTOC_EXECUTABLE fake-protoc",
            "PROTOC_EXECUTABLE, fake-protoc",
        ),
    ],
)
def test_setup_codegen_rejects_all_arguments_before_provisioning(
    tmp_path: Path,
    arguments: str,
    expected_arguments: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        f"protocyte_setup_codegen({arguments})",
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert (
        f"protocyte_setup_codegen received unknown argument(s): {expected_arguments}"
    ) in output


@pytest.mark.parametrize(
    ("function_name", "invocation"),
    [
        (
            "protocyte_generate",
            "protocyte_generate(TARGET demo OUT_DIR)",
        ),
        (
            "protocyte_add_proto_library",
            "protocyte_add_proto_library(TARGET demo OUT_DIR)",
        ),
        (
            "protocyte_add_descriptor_set_library",
            "protocyte_add_descriptor_set_library(TARGET demo OUT_DIR)",
        ),
    ],
)
def test_public_cmake_functions_reject_keywords_without_values(
    tmp_path: Path,
    function_name: str,
    invocation: str,
) -> None:
    result = _configure_cmake_snippet(tmp_path, invocation)

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert (
        f"{function_name} requires a value for the following keyword(s): OUT_DIR"
        in output
    )


@pytest.mark.parametrize(
    ("invocation", "expected_error"),
    [
        (
            "protocyte_generate(TARGET demo PROTO_ROOT proto OUT_DIR generated DISCOVER PROTOS proto/demo.proto)",
            "protocyte_generate accepts either DISCOVER or PROTOS, not both",
        ),
        (
            "protocyte_add_proto_library(TARGET demo PROTO_ROOT proto DISCOVER PROTOS proto/demo.proto)",
            "protocyte_add_proto_library accepts either DISCOVER or PROTOS, not both",
        ),
        (
            "protocyte_add_descriptor_set_library(TARGET demo DESCRIPTOR_SET descriptor_set.pb DISCOVER FILES demo.proto)",
            "protocyte_add_descriptor_set_library accepts either DISCOVER or FILES, not both",
        ),
        (
            "protocyte_add_proto_library(TARGET demo DESCRIPTOR_SET descriptor_set.pb PROTO_ROOT proto PROTOS proto/demo.proto)",
            "protocyte_add_proto_library accepts either DESCRIPTOR_SET or PROTO_ROOT, not both",
        ),
        (
            "protocyte_add_proto_library(TARGET demo PROTO_ROOT proto PROTOS proto/demo.proto EMIT_RUNTIME RUNTIME_TARGET protocyte::runtime)",
            "protocyte_add_proto_library accepts either EMIT_RUNTIME or RUNTIME_TARGET, not both",
        ),
    ],
)
def test_public_cmake_functions_reject_mutually_exclusive_arguments(
    tmp_path: Path,
    invocation: str,
    expected_error: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        invocation,
        files={
            "descriptor_set.pb": "placeholder",
            "proto/demo.proto": 'syntax = "proto3";\n',
        },
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert expected_error in output


@pytest.mark.parametrize(
    ("invocation", "expected_error"),
    [
        (
            "protocyte_generate(TARGET demo PROTO_ROOT missing OUT_DIR generated DISCOVER)",
            "protocyte_generate PROTO_ROOT must be an existing directory:",
        ),
        (
            "protocyte_generate(TARGET demo DESCRIPTOR_SET missing.pb OUT_DIR generated PROTOS api.proto)",
            "protocyte_generate DESCRIPTOR_SET must be an existing file:",
        ),
        (
            "protocyte_generate(TARGET demo PROTO_ROOT proto OUT_DIR generated PROTOS proto/missing.proto)",
            "protocyte_generate PROTOS entry must be an existing file:",
        ),
        (
            "protocyte_generate(TARGET demo PROTO_ROOT proto OUT_DIR generated PROTOS proto/present.proto IMPORT_DIRS missing-imports)",
            "protocyte_generate IMPORT_DIRS entry must be an existing directory:",
        ),
        (
            "protocyte_generate(TARGET demo PROTO_ROOT not-a-directory OUT_DIR generated DISCOVER)",
            "protocyte_generate PROTO_ROOT must be an existing directory:",
        ),
        (
            "protocyte_generate(TARGET demo DESCRIPTOR_SET descriptor-directory OUT_DIR generated PROTOS api.proto)",
            "protocyte_generate DESCRIPTOR_SET must be an existing file:",
        ),
        (
            "protocyte_generate(TARGET demo PROTO_ROOT proto OUT_DIR generated PROTOS proto/proto-directory)",
            "protocyte_generate PROTOS entry must be an existing file:",
        ),
        (
            "protocyte_generate(TARGET demo PROTO_ROOT proto OUT_DIR generated PROTOS proto/present.proto IMPORT_DIRS not-an-import-directory)",
            "protocyte_generate IMPORT_DIRS entry must be an existing directory:",
        ),
    ],
)
def test_protocyte_generate_rejects_missing_filesystem_inputs_at_configure_time(
    tmp_path: Path,
    invocation: str,
    expected_error: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        invocation,
        files={
            "proto/present.proto": 'syntax = "proto3";\n',
            "not-a-directory": "file\n",
            "descriptor-directory/marker": "directory\n",
            "proto/proto-directory/marker": "directory\n",
            "not-an-import-directory": "file\n",
        },
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert expected_error in output


def test_cmake_install_tree_contains_installable_python_project() -> None:
    cmake = (Path(__file__).resolve().parents[1] / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )

    assert 'DESTINATION "${PROTOCYTE_INSTALL_PYTHONDIR}/src"' in cmake
    assert '"${CMAKE_CURRENT_LIST_DIR}/pyproject.toml"' in cmake
    assert '"${CMAKE_CURRENT_LIST_DIR}/protocyte-cmake-constraints.txt"' in cmake
    assert 'DESTINATION "${PROTOCYTE_INSTALL_PYTHONDIR}"' in cmake


def _configure_fetchcontent_install_fixture(
    tmp_path: Path,
    *,
    protocyte_install: bool | None = None,
) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "consumer"
    build_dir = tmp_path / "build"
    prefix = tmp_path / "prefix"
    source_dir.mkdir()
    (source_dir / "consumer-marker.txt").write_text(
        "consumer-owned install artifact\n",
        encoding="utf-8",
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(protocyte_install_isolation LANGUAGES CXX)",
                "include(FetchContent)",
                "FetchContent_Declare(",
                "    protocyte",
                f'    SOURCE_DIR "{repo_root.as_posix()}"',
                ")",
                "FetchContent_MakeAvailable(protocyte)",
                "install(",
                '    FILES "${CMAKE_CURRENT_SOURCE_DIR}/consumer-marker.txt"',
                '    DESTINATION "share/consumer"',
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_command = ["cmake", "-S", str(source_dir), "-B", str(build_dir)]
    if protocyte_install is not None:
        configure_command.append(
            f"-DPROTOCYTE_INSTALL={'ON' if protocyte_install else 'OFF'}"
        )
    subprocess.run(configure_command, check=True)
    subprocess.run(
        ["cmake", "--install", str(build_dir), "--prefix", str(prefix)],
        check=True,
    )
    return build_dir, prefix


def test_fetchcontent_excludes_protocyte_from_parent_install_by_default(
    tmp_path: Path,
) -> None:
    build_dir, prefix = _configure_fetchcontent_install_fixture(tmp_path)

    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert "PROTOCYTE_INSTALL:BOOL=OFF" in cache
    manifest = (build_dir / "install_manifest.txt").read_text(encoding="utf-8")
    installed_files = [
        Path(line).resolve()
        for line in manifest.splitlines()
        if line
    ]
    expected_marker = (prefix / "share/consumer/consumer-marker.txt").resolve()
    assert installed_files == [expected_marker]
    assert not (prefix / "include/protocyte").exists()
    assert not any(prefix.rglob("protocyteConfig.cmake"))
    assert not (prefix / "share/protocyte").exists()
    generated_config = build_dir / "_deps/protocyte-build/cmake/protocyteConfig.cmake"
    assert not generated_config.exists()


def test_fetchcontent_can_explicitly_enable_protocyte_install(
    tmp_path: Path,
) -> None:
    build_dir, prefix = _configure_fetchcontent_install_fixture(
        tmp_path,
        protocyte_install=True,
    )

    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert "PROTOCYTE_INSTALL:BOOL=ON" in cache
    assert (prefix / "share/consumer/consumer-marker.txt").is_file()
    assert (prefix / "include/protocyte/runtime/runtime.hpp").is_file()
    assert any(prefix.rglob("protocyteConfig.cmake"))
    assert any(prefix.rglob("ProtocyteDependencyScan.cmake"))
    assert (prefix / "share/protocyte/python/pyproject.toml").is_file()


def test_protobuf_fallback_uses_parent_safe_function_scoped_defaults() -> None:
    functions = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteFunctions.cmake"
    ).read_text(encoding="utf-8")
    fallback = functions.split("elseif(PROTOCYTE_FETCH_PROTOBUF)", 1)[1].split(
        "FetchContent_MakeAvailable(protobuf)", 1
    )[0]

    assert "if(NOT DEFINED protobuf_INSTALL)" in fallback
    assert "set(protobuf_INSTALL OFF)" in fallback
    expected_defaults = {
        "protobuf_BUILD_TESTS": "OFF",
        "protobuf_BUILD_CONFORMANCE": "OFF",
        "protobuf_BUILD_EXAMPLES": "OFF",
        "protobuf_BUILD_PROTOBUF_BINARIES": "ON",
        "protobuf_INSTALL": "OFF",
    }
    for option, default in expected_defaults.items():
        assert f"if(NOT DEFINED {option})" in fallback
        assert f"set({option} {default})" in fallback
        assert f"set({option} {default} CACHE" not in fallback
    assert " FORCE)" not in fallback


def test_internal_cmake_settings_do_not_fall_back_to_variables(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "internal_settings.cmake"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                'set(PROTOCYTE_PYTHON_SOURCE_ROOT "legacy-variable")',
                "_protocyte_get_internal(value PYTHON_SOURCE_ROOT)",
                'if(NOT value STREQUAL "")',
                '    message(FATAL_ERROR "legacy variable unexpectedly populated internal setting")',
                "endif()",
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PYTHON_SOURCE_ROOT "internal-property")',
                "_protocyte_get_internal(value PYTHON_SOURCE_ROOT)",
                'if(NOT value STREQUAL "internal-property")',
                '    message(FATAL_ERROR "internal property was not returned")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)


def test_resolve_protobuf_import_dir_from_protoc_layout(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "resolve_protoc_import_dir.cmake"
    resolved_output = tmp_path / "resolved.txt"
    protoc = tmp_path / "toolchain" / "bin" / "protoc"
    descriptor = (
        tmp_path / "toolchain" / "include" / "google" / "protobuf" / "descriptor.proto"
    )

    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    descriptor.parent.mkdir(parents=True, exist_ok=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "_protocyte_resolve_protobuf_import_dir()",
                f'file(WRITE "{resolved_output.as_posix()}" "${{PROTOCYTE_PROTOBUF_IMPORT_DIR}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert (
        resolved_output.read_text(encoding="utf-8")
        == (tmp_path / "toolchain" / "include").as_posix()
    )


def test_relative_protoc_path_must_name_an_existing_file(tmp_path: Path) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                'set(Protobuf_PROTOC_EXECUTABLE "tools/missing-protoc")',
                "_protocyte_ensure_protobuf()",
            ]
        ),
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "Protobuf_PROTOC_EXECUTABLE 'tools/missing-protoc' resolves to" in output
    assert "does not name an existing file" in output


@pytest.mark.parametrize("target_name", ["protobuf::protoc", "protoc"])
def test_protoc_target_preserves_generator_expression_and_target_dependency(
    tmp_path: Path, target_name: str
) -> None:
    selected = tmp_path / "build" / "selected.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f"add_executable({target_name} IMPORTED)",
                f'set_target_properties({target_name} PROPERTIES IMPORTED_LOCATION "${{CMAKE_CURRENT_SOURCE_DIR}}/tools/protoc")',
                'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/protobuf")',
                "_protocyte_ensure_protobuf()",
                f'file(WRITE "{selected.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n")',
            ]
        ),
        files={
            "tools/protoc": "",
            "protobuf/google/protobuf/descriptor.proto": 'syntax = "proto3";\n',
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert selected.read_text(encoding="utf-8").splitlines() == [
        f"$<TARGET_FILE:{target_name}>",
        target_name,
    ]


def test_generator_parameter_encoding_uses_hex_transport(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "encode_test.cmake"
    encoded_output = tmp_path / "encoded.txt"
    raw = "runtime=emit:toolchain/runtime,clang_format=C:/Program Files/LLVM/bin/clang-format.exe"
    expected = "_protocyte_options_hex=" + raw.encode("utf-8").hex()

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'_protocyte_encode_generator_parameter(encoded "{raw}")',
                f'file(WRITE "{encoded_output.as_posix()}" "${{encoded}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert encoded_output.read_text(encoding="utf-8") == expected


def test_cmake_discovery_json_preserves_semicolon_descriptor_name(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "parse_discovered_names.cmake"
    output = tmp_path / "names.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_parse_discovered_descriptor_names(names [==[["api/one;legacy.proto","api/two.proto"]]==])',
                "foreach(name IN LISTS names)",
                '    string(APPEND encoded "${name}|")',
                "endforeach()",
                f'file(WRITE "{output.as_posix()}" "${{encoded}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert output.read_text(encoding="utf-8") == "api/one;legacy.proto|api/two.proto|"


def test_cmake_descriptor_name_validator_rejects_drive_relative_paths(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "descriptor_name_validator.cmake"
    output = tmp_path / "unsafe.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_descriptor_name_is_unsafe(unsafe "C:foo.proto")',
                f'file(WRITE "{output.as_posix()}" "${{unsafe}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert output.read_text(encoding="utf-8") == "TRUE"


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "../escaped",
        "nested/../escaped",
        "nested/./runtime",
        "/absolute/runtime",
        "C:/absolute/runtime",
        "C:drive-relative/runtime",
        "nested/runtime:stream",
        " nested/runtime",
        "nested /runtime",
        r"nested\runtime",
        "nested//runtime",
        "nested/runtime/",
        'nested/runtime"injected',
        "nested/runtime<injected",
        "nested/runtime>injected",
        "nested/runtime|injected",
        "nested/runtime?injected",
        "nested/runtime*injected",
        "nested/runtime;injected",
        "nested/trailing.",
        "nested/CON",
        "nested/nul.hpp",
        "nested/COM1",
        "nested/lpt9.generated",
    ],
)
def test_cmake_virtual_directory_prefix_validator_rejects_unsafe_paths(
    tmp_path: Path, prefix: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "prefix_validator.cmake"
    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'_protocyte_validate_virtual_directory_prefix("runtime prefix" [==[{prefix}]==])',
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-P", str(cmake_script)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "runtime prefix" in (result.stdout + result.stderr)


def test_cmake_virtual_directory_prefix_validator_accepts_nested_path(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "prefix_validator.cmake"
    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_validate_virtual_directory_prefix("runtime prefix" "vendor/protocyte/runtime")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)


@pytest.mark.parametrize(
    "forwarded_option",
    [
        "runtime=emit",
        "runtime=omit",
        "runtime=emit:vendor/protocyte",
        "runtime_prefix=vendor/protocyte",
        "clang_format=tool,runtime=emit:vendor/protocyte",
        " runtime=emit",
        "runtime =emit",
        "runtime_prefix =vendor/protocyte",
    ],
)
def test_cmake_rejects_runtime_state_forwarded_through_options(
    tmp_path: Path, forwarded_option: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(reject_forwarded_runtime LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS simple.proto",
                f"    OPTIONS [==[{forwarded_option}]==]",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "OPTIONS must not set runtime or runtime_prefix" in output
    assert "use EMIT_RUNTIME and RUNTIME_PREFIX" in output


def test_cmake_rejects_encoded_transport_forwarded_through_options(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    encoded_runtime = "runtime=emit:vendor/protocyte".encode().hex()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(reject_encoded_transport LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS simple.proto",
                f"    OPTIONS _protocyte_options_hex={encoded_runtime}",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "OPTIONS must not use reserved _protocyte_ transport parameters" in output


def test_real_protoc_rejects_runtime_prefix_escape_and_keeps_valid_response_names(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    proto_dir = tmp_path / "proto"
    proto_dir.mkdir()
    (proto_dir / "simple.proto").write_text(
        'syntax = "proto3"; package demo; message Simple { int32 value = 1; }\n',
        encoding="utf-8",
    )
    plugin = _write_python_plugin_wrapper(tmp_path / "protoc-gen-protocyte", repo_root)

    escaped_out = tmp_path / "unsafe-out"
    escaped_out.mkdir()
    escaped_parameter = "runtime=emit:../escaped".encode("utf-8").hex()
    escaped = subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_dir}",
            f"--plugin=protoc-gen-protocyte={plugin}",
            f"--protocyte_out=_protocyte_options_hex={escaped_parameter}:unsafe-out",
            "simple.proto",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert escaped.returncode != 0
    assert "runtime prefix" in (escaped.stdout + escaped.stderr)
    assert not (tmp_path / "escaped" / "runtime.hpp").exists()

    valid_out = tmp_path / "valid-out"
    valid_out.mkdir()
    valid_parameter = "runtime=emit:vendor/protocyte".encode("utf-8").hex()
    subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_dir}",
            f"--plugin=protoc-gen-protocyte={plugin}",
            f"--protocyte_out=_protocyte_options_hex={valid_parameter}:valid-out",
            "simple.proto",
        ],
        cwd=tmp_path,
        check=True,
    )

    assert (valid_out / "simple.protocyte.hpp").is_file()
    assert (valid_out / "simple.protocyte.cpp").is_file()
    assert (valid_out / "vendor" / "protocyte" / "runtime.hpp").is_file()


def test_generate_accepts_relative_proto_root_at_configure_time(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    descriptor = source_dir / "protobuf" / "google" / "protobuf" / "descriptor.proto"
    protoc = source_dir / "tools" / "protoc"
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )

    proto_dir.mkdir(parents=True)
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; message Demo {}\n', encoding="utf-8"
    )
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(relative_proto_root LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(source_dir / "protobuf").as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                "    PROTO_ROOT proto",
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)


def test_source_codegen_regenerates_when_transitive_import_changes(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify an incremental build"
        )
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    import_dir = source_dir / "imports"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    import_dir.mkdir()
    tools_dir.mkdir()

    imported_proto = import_dir / "base.proto"
    imported_proto.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "protocyte/options.proto";',
                'option (protocyte.package_constant) = { name: "CAPACITY" u32: 2 };',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (proto_dir / "consumer.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "base.proto";',
                'import "protocyte/options.proto";',
                'option (protocyte.package_constant) = { name: "DERIVED" u32_expr: "demo.CAPACITY + 1" };',
                "message Consumer {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (proto_dir / "standalone.proto").write_text(
        'syntax = "proto3"; package demo; message Standalone {}\n',
        encoding="utf-8",
    )
    plugin = _write_python_plugin_wrapper(
        tools_dir / "protoc-gen-protocyte", repo_root
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(transitive_import_regeneration LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/consumer.proto proto/standalone.proto",
                '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports"',
                "    EMIT_RUNTIME",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
    )
    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    subprocess.run(build_command, check=True)
    generated_header = build_dir / "generated" / "consumer.protocyte.hpp"
    initial_header = generated_header.read_text(encoding="utf-8")
    assert "DERIVED {3u}" in initial_header
    assert (
        build_dir / "generated" / "protocyte" / "runtime" / "runtime.hpp"
    ).is_file()

    imported_proto.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "protocyte/options.proto";',
                'option (protocyte.package_constant) = { name: "CAPACITY" u32: 5 };',
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(build_command, check=True)
    updated_header = generated_header.read_text(encoding="utf-8")
    assert "DERIVED {6u}" in updated_header
    assert updated_header != initial_header

    no_change = subprocess.run(build_command, check=True, capture_output=True, text=True)
    assert "no work to do" in no_change.stdout.lower()


@pytest.mark.parametrize("protoc_selection", ["relative_path", "imported_target"])
def test_source_codegen_accepts_relative_protoc_and_tracks_tool_changes(
    tmp_path: Path, protoc_selection: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required to verify an incremental build")

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package demo; message Demo {}\n', encoding="utf-8"
    )
    invocation_log = source_dir / "protoc-invocations.txt"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    relative_protoc = protoc.relative_to(source_dir).as_posix()
    if protoc_selection == "relative_path":
        protoc_setup = [f'set(Protobuf_PROTOC_EXECUTABLE "{relative_protoc}")']
    else:
        protoc_setup = [
            "add_executable(protobuf::protoc IMPORTED)",
            f'set_target_properties(protobuf::protoc PROPERTIES IMPORTED_LOCATION "{protoc.as_posix()}")',
        ]

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(relative_protoc_incremental LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                *protoc_setup,
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/demo.proto",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
    )
    if protoc_selection == "relative_path":
        cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
        assert f"PROTOCYTE_PROTOC_EXECUTABLE:INTERNAL={protoc.as_posix()}" in cache

    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    subprocess.run(build_command, check=True)
    generated_header = build_dir / "generated" / "demo.protocyte.hpp"
    assert generated_header.is_file()
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
    ]

    _touch_newer_than(protoc, generated_header)
    subprocess.run(build_command, check=True)
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
        "invoked",
        "invoked",
    ]


@pytest.mark.parametrize("protoc_selection", ["relative_path", "imported_target"])
def test_descriptor_set_codegen_tracks_protoc_tool_changes(
    tmp_path: Path, protoc_selection: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required to verify an incremental build")

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    tools_dir = source_dir / "tools"
    tools_dir.mkdir(parents=True)
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    demo = file_set.file.add()
    demo.name = "api/demo.proto"
    demo.package = "demo"
    demo.syntax = "proto3"
    demo.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    invocation_log = source_dir / "protoc-invocations.txt"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    relative_protoc = protoc.relative_to(source_dir).as_posix()
    if protoc_selection == "relative_path":
        protoc_setup = [f'set(Protobuf_PROTOC_EXECUTABLE "{relative_protoc}")']
    else:
        protoc_setup = [
            "add_executable(protobuf::protoc IMPORTED)",
            f'set_target_properties(protobuf::protoc PROPERTIES IMPORTED_LOCATION "{protoc.as_posix()}")',
        ]

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_protoc_incremental LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                *protoc_setup,
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    DESCRIPTOR_SET "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS api/demo.proto",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
    )
    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    subprocess.run(build_command, check=True)
    generated_header = build_dir / "generated" / "api" / "demo.protocyte.hpp"
    assert generated_header.is_file()
    assert invocation_log.read_text(encoding="utf-8").splitlines() == ["invoked"]

    _touch_newer_than(protoc, generated_header)
    subprocess.run(build_command, check=True)
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
    ]


def test_generate_accepts_descriptor_set_protos_without_proto_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    protoc = source_dir / "tools" / "protoc"
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_codegen LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS nested/demo.proto",
                "    GENERATED_HEADERS_VAR generated_headers",
                "    GENERATED_SOURCES_VAR generated_sources",
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/headers.txt" "${generated_headers}")',
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/sources.txt" "${generated_sources}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    assert (
        (build_dir / "headers.txt")
        .read_text(encoding="utf-8")
        .endswith("generated/nested/demo.protocyte.hpp")
    )
    assert (
        (build_dir / "sources.txt")
        .read_text(encoding="utf-8")
        .endswith("generated/nested/demo.protocyte.cpp")
    )


def test_generate_resolves_relative_out_dir_against_binary_directory(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(relative_codegen_out_dir LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                "    OUT_DIR generated",
                "    PROTOS api/demo.proto",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
    )

    assert (build_dir / "generated" / "api" / "demo.protocyte.hpp").is_file()
    assert (build_dir / "generated" / "api" / "demo.protocyte.cpp").is_file()
    assert not (source_dir / "generated").exists()


def test_source_mode_codegen_declares_normalized_generated_paths(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "café.proto").write_text(
        'syntax = "proto3"; message Demo {}\n', encoding="utf-8"
    )
    protoc = _find_real_protoc(repo_root)
    protobuf_import = _find_protobuf_import_root(repo_root)
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(source_mode_normalized_path LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/café.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True
    )

    assert (build_dir / "generated" / "caf~C3~A9.protocyte.hpp").is_file()
    assert (build_dir / "generated" / "caf~C3~A9.protocyte.cpp").is_file()


def test_generate_descriptor_set_discover_skips_google_protobuf_files(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    runtime = file_set.file.add()
    runtime.name = "google/protobuf/descriptor.proto"
    runtime.syntax = "proto2"
    timestamp = file_set.file.add()
    timestamp.name = "google/protobuf/timestamp.proto"
    timestamp.package = "google.protobuf"
    timestamp.syntax = "proto3"
    timestamp_message = timestamp.message_type.add()
    timestamp_message.name = "Timestamp"
    seconds = timestamp_message.field.add()
    seconds.name = "seconds"
    seconds.number = 1
    seconds.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    seconds.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
    options = file_set.file.add()
    options.name = "protocyte/options.proto"
    options.syntax = "proto2"
    options.dependency.append("google/protobuf/descriptor.proto")
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.dependency.append("protocyte/options.proto")
    user.dependency.append("google/protobuf/timestamp.proto")
    user_message = user.message_type.add()
    user_message.name = "Demo"
    created_at = user_message.field.add()
    created_at.name = "created_at"
    created_at.number = 1
    created_at.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    created_at.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    created_at.type_name = ".google.protobuf.Timestamp"
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = source_dir / "tools" / "protoc"
    plugin = _installed_protocyte_plugin()
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                "    GENERATED_HEADERS_VAR generated_headers",
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/headers.txt" "${generated_headers}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    headers = (build_dir / "headers.txt").read_text(encoding="utf-8")
    assert "generated/api/demo.protocyte.hpp" in headers
    assert "generated/google/protobuf/timestamp.protocyte.hpp" in headers


@pytest.mark.parametrize(
    ("descriptor_name", "generated_stem"),
    [
        ("api/demo;legacy.proto", "api/demo~3Blegacy.protocyte"),
        ('api/demo"legacy.proto', "api/demo~22legacy.protocyte"),
    ],
)
def test_descriptor_set_discover_generates_portable_file_names(
    tmp_path: Path, descriptor_name: str, generated_stem: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = descriptor_name
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())

    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_semicolon LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                "    GENERATED_HEADERS_VAR generated_headers",
                ")",
                "list(LENGTH generated_headers generated_header_count)",
                "if(NOT generated_header_count EQUAL 1)",
                '    message(FATAL_ERROR "expected one generated header, got ${generated_header_count}")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True
    )

    assert (build_dir / "generated" / f"{generated_stem}.hpp").is_file()
    assert (build_dir / "generated" / f"{generated_stem}.cpp").is_file()


def test_descriptor_set_discover_tracks_descriptor_set_as_configure_input(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = source_dir / "tools" / "protoc"
    plugin = _installed_protocyte_plugin()
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover_configure_depends LANGUAGES NONE)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "get_property(configure_depends DIRECTORY PROPERTY CMAKE_CONFIGURE_DEPENDS)",
                f'if(NOT "{descriptor_set.as_posix()}" IN_LIST configure_depends)',
                '    message(FATAL_ERROR "descriptor-set DISCOVER did not track descriptor set as a configure input")',
                "endif()",
                f'if(NOT "{plugin.as_posix()}" IN_LIST configure_depends)',
                '    message(FATAL_ERROR "descriptor-set DISCOVER did not track the plugin as a configure input")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)


def test_descriptor_set_discover_uses_explicit_plugin_environment(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    clean_environment = tmp_path / "clean-python"
    base_python = Path(getattr(sys, "_base_executable", sys.executable))
    subprocess.run([str(base_python), "-m", "venv", str(clean_environment)], check=True)
    clean_python = clean_environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    missing_protobuf = subprocess.run(
        [str(clean_python), "-c", "import google.protobuf"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing_protobuf.returncode != 0

    protoc = source_dir / "tools" / "protoc"
    plugin = _installed_protocyte_plugin()
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover_plugin_environment LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{clean_python.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)


def test_descriptor_set_discover_reports_incompatible_explicit_plugin(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = "api/demo.proto"
    user.syntax = "proto3"
    user.message_type.add().name = "Demo"
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = source_dir / "tools" / "protoc"
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    plugin = _write_incompatible_protocyte_plugin(
        source_dir / "tools" / "protoc-gen-protocyte"
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_discover_incompatible_plugin LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Exit code: 4" in output
    assert "old plugin cannot discover" in output
    assert "supports the 'descriptor-set list' command" in output


def test_descriptor_set_rejects_unsafe_descriptor_name_at_configure_time(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    protoc = source_dir / "tools" / "protoc"
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_unsafe_name LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS nested/./demo.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert (
        "descriptor file name contains an unsafe path segment: nested/./demo.proto"
        in (result.stdout + result.stderr)
    )


def test_descriptor_set_codegen_target_uses_descriptor_set_in_without_proto_paths(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    tools_dir = source_dir / "tools"
    tools_dir.mkdir()
    args_path = build_dir / "protoc_args.txt"
    fake_protoc_py = tools_dir / "fake_protoc.py"
    fake_protoc_py.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                f"Path({str(args_path)!r}).parent.mkdir(parents=True, exist_ok=True)",
                f"Path({str(args_path)!r}).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')",
                "out_dir = None",
                "for arg in sys.argv[1:]:",
                "    if arg.startswith('--protocyte_out='):",
                "        out_dir = Path(arg.split('=', 1)[1])",
                "if out_dir is None:",
                "    raise SystemExit('missing --protocyte_out')",
                "for name in sys.argv[1:]:",
                "    if not name.endswith('.proto'):",
                "        continue",
                "    base = out_dir / name.removesuffix('.proto')",
                "    base.parent.mkdir(parents=True, exist_ok=True)",
                "    base.with_suffix('.protocyte.hpp').write_text('// h\\n', encoding='utf-8')",
                "    base.with_suffix('.protocyte.cpp').write_text('// cc\\n', encoding='utf-8')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if os.name == "nt":
        protoc = tools_dir / "protoc.cmd"
        protoc.write_text(
            f'@echo off\r\n"{Path(sys.executable)}" "{fake_protoc_py}" %*\r\n',
            encoding="utf-8",
        )
    else:
        protoc = tools_dir / "protoc"
        protoc.write_text(
            f'#!/usr/bin/env sh\nexec "{Path(sys.executable)}" "{fake_protoc_py}" "$@"\n',
            encoding="utf-8",
        )
        protoc.chmod(0o755)
    plugin = _write_version_only_plugin(
        tools_dir / "protoc-gen-protocyte", __version__
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_build LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS nested/demo.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True
    )

    args = args_path.read_text(encoding="utf-8").splitlines()
    assert f"--descriptor_set_in={descriptor_set.as_posix()}" in args
    assert not any(arg.startswith("--proto_path=") for arg in args)
    assert "nested/demo.proto" in args


def test_descriptor_set_codegen_builds_with_real_protoc_descriptor_set_in(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    descriptor_set = source_dir / "descriptor_set.pb"
    demo_proto = proto_dir / "api" / "demo.proto"
    demo_proto.parent.mkdir()
    demo_proto.write_text(
        'syntax = "proto3"; package api; message Demo { int32 id = 1; }\n',
        encoding="utf-8",
    )

    subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_dir}",
            f"--descriptor_set_out={descriptor_set}",
            "--include_imports",
            "api/demo.proto",
        ],
        cwd=proto_dir,
        check=True,
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(real_descriptor_set_build LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS api/demo.proto",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True
    )

    header = build_dir / "generated" / "api" / "demo.protocyte.hpp"
    source = build_dir / "generated" / "api" / "demo.protocyte.cpp"
    assert header.is_file()
    assert source.is_file()
    assert "struct Demo" in header.read_text(encoding="utf-8")


def test_descriptor_set_library_wrapper_configures_alias_target(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    descriptor_set.write_bytes(b"placeholder")
    protoc = source_dir / "tools" / "protoc"
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_library LANGUAGES CXX)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'add_subdirectory("{repo_root.as_posix()}" "${{CMAKE_CURRENT_BINARY_DIR}}/protocyte")',
                "protocyte_add_descriptor_set_library(",
                "    TARGET demo_proto",
                "    ALIAS demo::proto",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                "    FILES nested/demo.proto",
                "    GENERATED_HEADERS_VAR generated_headers",
                "    GENERATED_SOURCES_VAR generated_sources",
                "    GENERATED_TARGET_VAR generated_target",
                ")",
                "if(NOT TARGET demo::proto)",
                '    message(FATAL_ERROR "descriptor-set alias target was not created")',
                "endif()",
                'if(NOT generated_headers MATCHES "nested/demo[.]protocyte[.]hpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated headers")',
                "endif()",
                'if(NOT generated_sources MATCHES "nested/demo[.]protocyte[.]cpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated sources")',
                "endif()",
                'if(NOT generated_target STREQUAL "demo_proto__protocyte_codegen")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated target")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)


@pytest.mark.parametrize(
    ("descriptor_name", "message_name", "generator"),
    [
        ("api/demo;legacy.proto", "SemicolonName", None),
        ("é" * 50 + "/unicode.proto", "LongUnicodePath", "Ninja"),
    ],
)
def test_descriptor_set_library_builds_portable_descriptor_name(
    tmp_path: Path,
    descriptor_name: str,
    message_name: str,
    generator: str | None,
) -> None:
    if generator == "Ninja" and shutil.which("ninja") is None:
        pytest.skip("Ninja is required for portable long-path integration coverage")

    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    user = file_set.file.add()
    user.name = descriptor_name
    user.package = "demo"
    user.syntax = "proto3"
    user.message_type.add().name = message_name
    descriptor_set.write_bytes(file_set.SerializeToString())
    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_portable_library LANGUAGES CXX)",
                f'set(Python3_ROOT_DIR "{Path(sys.prefix).as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'add_subdirectory("{repo_root.as_posix()}" "${{CMAKE_CURRENT_BINARY_DIR}}/protocyte")',
                "protocyte_add_descriptor_set_library(",
                "    TARGET portable_proto",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                "    DISCOVER",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_command = ["cmake", "-S", str(source_dir), "-B", str(build_dir)]
    if generator is not None:
        configure_command.extend(["-G", generator])
    subprocess.run(configure_command, check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "portable_proto"],
        check=True,
    )

    generated_base = generated_file_base(descriptor_name)
    assert (
        build_dir / "portable_proto_protocyte" / f"{generated_base}.hpp"
    ).is_file()
    assert (
        build_dir / "portable_proto_protocyte" / f"{generated_base}.cpp"
    ).is_file()
    if ";" in descriptor_name:
        assert generated_base == "api/demo~3Blegacy.protocyte"
    else:
        long_generated_directory = generated_base.split("/", 1)[0]
        assert len(long_generated_directory.encode("ascii")) == 255


def test_cmake_constraints_pin_the_private_environment() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    constraint_lines = [
        line.strip()
        for line in (repo_root / "protocyte-cmake-constraints.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    constraints = dict(line.split("==", 1) for line in constraint_lines)

    assert set(constraints) == {"pip", "protobuf", "setuptools", "wheel"}
    locked_packages = tomllib.loads(
        (repo_root / "uv.lock").read_text(encoding="utf-8")
    )["package"]
    locked_protobuf = next(
        package["version"]
        for package in locked_packages
        if package["name"] == "protobuf"
    )
    assert constraints["protobuf"] == locked_protobuf


def test_cmake_fingerprint_inputs_trigger_automatic_reconfiguration(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    python_project = tmp_path / "python-project"
    package_dir = python_project / "src" / "protocyte"
    package_dir.mkdir(parents=True)
    (python_project / "pyproject.toml").write_text(
        '[project]\nname = "fingerprint-test"\nversion = "1.0"\n',
        encoding="utf-8",
    )
    constraints = python_project / "protocyte-cmake-constraints.txt"
    shutil.copy2(repo_root / "protocyte-cmake-constraints.txt", constraints)
    package_file = package_dir / "main.py"
    package_file.write_text("VALUE = 1\n", encoding="utf-8")

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(protocyte_fingerprint_reconfigure LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "_protocyte_python_environment_fingerprint(",
                "    fingerprint",
                f'    "{python_project.as_posix()}"',
                f'    "{constraints.as_posix()}"',
                f'    "{Path(sys.executable).as_posix()}"',
                f'    "{python_version}"',
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/fingerprint.txt" "${fingerprint}")',
                "add_custom_target(fingerprint_noop ALL)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)
    initial_fingerprint = (build_dir / "fingerprint.txt").read_text(encoding="utf-8")

    package_file.write_text("VALUE = 2\n", encoding="utf-8")
    subprocess.run(["cmake", "--build", str(build_dir)], check=True)

    updated_fingerprint = (build_dir / "fingerprint.txt").read_text(encoding="utf-8")
    assert updated_fingerprint != initial_fingerprint


def test_cmake_provisioning_error_reports_the_failed_command(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "provisioning_error.cmake"
    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "_protocyte_python_provisioning_error(",
                '    "install the test package"',
                '    "python -m pip install test-package"',
                '    "17"',
                '    "captured standard output"',
                '    "captured standard error"',
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-P", str(cmake_script)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "python -m pip install test-package" in output
    assert "Exit code: 17" in output
    assert "captured standard output" in output
    assert "captured standard error" in output
    assert "PROTOCYTE_PLUGIN_EXECUTABLE" in output


def test_smoke_cmake_gates_std_format_opt_in_on_compile_probe() -> None:
    smoke_cmake = (
        Path(__file__).resolve().parents[1] / "tests" / "smoke" / "CMakeLists.txt"
    ).read_text(encoding="utf-8")

    assert "include(CheckCXXSourceCompiles)" in smoke_cmake
    assert "check_cxx_source_compiles(" in smoke_cmake
    assert "#include <version>" in smoke_cmake
    assert "#if !defined(__cpp_lib_format) || __cpp_lib_format < 201907L" in smoke_cmake
    assert '#error "std::format is unavailable"' in smoke_cmake
    assert "#include <format>" in smoke_cmake
    assert "#include <string_view>" in smoke_cmake
    assert "::std::formatter<::std::string_view, char>" in smoke_cmake
    assert '::std::format("{}", ::std::string_view {"ok"})' in smoke_cmake
    assert "PROTOCYTE_SMOKE_HAS_STD_FORMAT" in smoke_cmake
    assert "if(PROTOCYTE_SMOKE_HAS_STD_FORMAT)" in smoke_cmake
    assert (
        'target_compile_definitions("${target_name}" PRIVATE PROTOCYTE_ENABLE_STD_FORMAT=1)'
        in smoke_cmake
    )
    assert "\n        PROTOCYTE_ENABLE_STD_FORMAT=1" not in smoke_cmake
    assert "\n            PROTOCYTE_ENABLE_STD_FORMAT=1" not in smoke_cmake


def test_prerelease_cmake_version_file_marks_versioned_requests_unsuitable() -> None:
    template = (
        Path(__file__).resolve().parents[1]
        / "cmake"
        / "protocyteConfigVersionPrerelease.cmake.in"
    ).read_text(encoding="utf-8")

    assert 'set(PACKAGE_VERSION "@PROTOCYTE_VERSION@")' in template
    assert "if(PACKAGE_FIND_VERSION)" in template
    assert "set(PACKAGE_VERSION_UNSUITABLE TRUE)" in template


def test_release_cmake_version_file_requires_exact_version() -> None:
    cmake_lists = (Path(__file__).resolve().parents[1] / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )
    version_block = cmake_lists.split("write_basic_package_version_file(", maxsplit=1)[
        1
    ].split("\n    )", maxsplit=1)[0]

    assert "COMPATIBILITY ExactVersion" in version_block
    assert "COMPATIBILITY SameMajorVersion" not in version_block
