from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Never

import pytest
from google.protobuf import descriptor_pb2

from protocyte import __version__
from protocyte.paths import (
    MIN_HASHED_GENERATED_FILE_PATH_BYTES,
    generated_file_base,
)


_CI_PROTOC_ENV = "PROTOCYTE_CI_PROTOC_EXECUTABLE"
_CI_REQUIRE_INCREMENTAL_TEST_ENV = "PROTOCYTE_CI_REQUIRE_INCREMENTAL_TEST"
_CI_REQUIRE_MULTICONFIG_LOCKING_TEST_ENV = (
    "PROTOCYTE_CI_REQUIRE_MULTICONFIG_LOCKING_TEST"
)
_CI_REQUIRE_WINDOWS_TRANSPORT_TEST_ENV = "PROTOCYTE_CI_REQUIRE_WINDOWS_TRANSPORT_TEST"


def _incremental_requirement_unavailable(message: str) -> Never:
    if os.environ.get(_CI_REQUIRE_INCREMENTAL_TEST_ENV) == "1":
        pytest.fail(message)
    pytest.skip(message)


def _multiconfig_locking_requirement_unavailable(message: str) -> Never:
    if os.environ.get(_CI_REQUIRE_MULTICONFIG_LOCKING_TEST_ENV) == "1":
        pytest.fail(message)
    pytest.skip(message)


def _windows_transport_requirement_unavailable(message: str) -> Never:
    if os.environ.get(_CI_REQUIRE_WINDOWS_TRANSPORT_TEST_ENV) == "1":
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


def _configure_runtime_ownership_project(
    tmp_path: Path,
    *,
    api: str,
    first_out_dir: str,
    second_out_dir: str,
    first_prefix: str | None = None,
    second_prefix: str | None = None,
    first_options: tuple[str, ...] = ("format=off",),
    second_options: tuple[str, ...] = ("format=off",),
) -> tuple[subprocess.CompletedProcess[str], Path]:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required for runtime output ownership coverage")

    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "descriptor_set.pb").write_bytes(b"placeholder")

    if api == "generate":
        project_languages = "NONE"
        function_name = "protocyte_generate"
        file_keyword = "PROTOS"
        first_target = "first_codegen"
        second_target = "second_codegen"
    elif api == "proto_library":
        project_languages = "CXX"
        function_name = "protocyte_add_proto_library"
        file_keyword = "PROTOS"
        first_target = "first_library"
        second_target = "second_library"
    elif api == "descriptor_library":
        project_languages = "CXX"
        function_name = "protocyte_add_descriptor_set_library"
        file_keyword = "FILES"
        first_target = "first_library"
        second_target = "second_library"
    else:
        raise AssertionError(f"unsupported runtime ownership API: {api}")

    def render_invocation(
        target: str,
        descriptor_name: str,
        out_dir: str,
        prefix: str | None,
        options: tuple[str, ...],
        headers_var: str,
    ) -> list[str]:
        lines = [
            f"{function_name}(",
            f"    TARGET {target}",
            '    DESCRIPTOR_SET "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb"',
            f'    OUT_DIR "${{CMAKE_CURRENT_BINARY_DIR}}/{out_dir}"',
            f"    {file_keyword} {descriptor_name}",
            "    EMIT_RUNTIME",
        ]
        if prefix is not None:
            lines.append(f"    RUNTIME_PREFIX {prefix}")
        if options:
            lines.append("    OPTIONS")
            lines.extend(f"        {option}" for option in options)
        lines.extend([f"    GENERATED_HEADERS_VAR {headers_var}", ")"])
        return lines

    cmake_lines = [
        "cmake_minimum_required(VERSION 3.24)",
        f"project(runtime_output_ownership LANGUAGES {project_languages})",
        f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
        "function(_protocyte_setup_codegen_internal fetch_missing_import_sources)",
        "endfunction()",
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}")',
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_OPTIONS_PROTO "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb")',
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES "")',
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${CMAKE_COMMAND}")',
        'set(PROTOCYTE_PROTOC_EXECUTABLE "${CMAKE_COMMAND}")',
        'set(PROTOCYTE_PROTOC_DEPENDENCY "${CMAKE_COMMAND}")',
    ]
    if api != "generate":
        cmake_lines.extend(
            [
                "add_library(protocyte_codegen INTERFACE)",
                "add_library(protocyte::codegen ALIAS protocyte_codegen)",
            ]
        )
    cmake_lines.extend(
        render_invocation(
            first_target,
            "first.proto",
            first_out_dir,
            first_prefix,
            first_options,
            "first_headers",
        )
    )
    cmake_lines.extend(
        render_invocation(
            second_target,
            "second.proto",
            second_out_dir,
            second_prefix,
            second_options,
            "second_headers",
        )
    )
    headers_output = build_dir / "headers.txt"
    cmake_lines.extend(
        [
            f'file(WRITE "{headers_output.as_posix()}" "first=${{first_headers}}\nsecond=${{second_headers}}\n")',
            "",
        ]
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(cmake_lines), encoding="utf-8"
    )

    result = subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result, headers_output


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


def _write_overlap_detecting_protoc_wrapper(
    path: Path, protoc: Path, state_dir: Path
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    script = path.with_suffix(".py")
    script.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import os",
                "import subprocess",
                "import sys",
                "import time",
                "from pathlib import Path",
                "",
                f"REAL_PROTOC = Path({str(protoc)!r})",
                f"STATE_DIR = Path({str(state_dir)!r})",
                "",
                "",
                "def response_kind(argument: str) -> str | None:",
                '    if not argument.startswith("@"):',
                "        return None",
                "    argument_file = Path(argument[1:])",
                "    if not argument_file.is_absolute():",
                "        argument_file = Path.cwd() / argument_file",
                '    content = argument_file.read_text(encoding="utf-8")',
                '    if "--protocyte_out=" in content:',
                '        return "generation"',
                '    if "--dependency_out=" in content or "--include_imports" in content:',
                '        return "dependency"',
                "    return None",
                "",
                "",
                "kind = response_kind(sys.argv[1]) if len(sys.argv) == 2 else None",
                "if kind is None:",
                "    raise SystemExit(",
                "        subprocess.run([str(REAL_PROTOC), *sys.argv[1:]], check=False).returncode",
                "    )",
                "",
                "pid = os.getpid()",
                '(STATE_DIR / f"attempt-{kind}-{pid}").write_text("attempt\\n", encoding="utf-8")',
                'active = STATE_DIR / f"active-{kind}"',
                "try:",
                "    active_fd = os.open(",
                "        active, os.O_CREAT | os.O_EXCL | os.O_WRONLY",
                "    )",
                "except FileExistsError:",
                '    (STATE_DIR / f"overlap-{kind}-{pid}").write_text(',
                '        "overlap\\n", encoding="utf-8"',
                "    )",
                '    sys.stderr.write(f"overlapping {kind} protoc invocation\\n")',
                "    raise SystemExit(91)",
                "",
                "try:",
                "    time.sleep(1.0)",
                "    result = subprocess.run(",
                "        [str(REAL_PROTOC), *sys.argv[1:]], check=False",
                "    )",
                "finally:",
                "    os.close(active_fd)",
                "    active.unlink(missing_ok=True)",
                "",
                '(STATE_DIR / f"complete-{kind}-{pid}").write_text(',
                '    f"{result.returncode}\\n", encoding="utf-8"',
                ")",
                "raise SystemExit(result.returncode)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    if os.name == "nt":
        wrapper = path.with_suffix(".cmd")
        wrapper.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    f'"{sys.executable}" "{script}" %*',
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
                    f'exec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "$@"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
    return wrapper


def _write_synchronized_build_runner(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import subprocess",
                "import sys",
                "import time",
                "from pathlib import Path",
                "",
                "ready = Path(sys.argv[1])",
                "gate = Path(sys.argv[2])",
                'ready.write_text("ready\\n", encoding="utf-8")',
                "deadline = time.monotonic() + 30.0",
                "while not gate.exists():",
                "    if time.monotonic() >= deadline:",
                "        raise SystemExit(92)",
                "    time.sleep(0.01)",
                "raise SystemExit(subprocess.run(sys.argv[3:], check=False).returncode)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _touch_newer_than(path: Path, output: Path) -> None:
    changed_mtime_ns = (
        max(path.stat().st_mtime_ns, output.stat().st_mtime_ns) + 2_000_000_000
    )
    os.utime(path, ns=(changed_mtime_ns, changed_mtime_ns))


def _write_protobuf_toolchain(root: Path) -> Path:
    protoc = root / "bin" / "protoc"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    descriptor = root / "include" / "google" / "protobuf" / "descriptor.proto"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    return protoc


def _installed_protocyte_plugin() -> Path:
    executable_name = (
        "protoc-gen-protocyte.exe" if os.name == "nt" else "protoc-gen-protocyte"
    )
    plugin = Path(sys.executable).with_name(executable_name)
    assert plugin.is_file(), f"installed Protocyte plugin is missing: {plugin}"
    return plugin


def _managed_environment_executables(environment: Path) -> tuple[Path, Path]:
    if os.name == "nt":
        return (
            environment / "Scripts" / "python.exe",
            environment / "Scripts" / "protoc-gen-protocyte.exe",
        )
    return (
        environment / "bin" / "python",
        environment / "bin" / "protoc-gen-protocyte",
    )


def _write_managed_environment_consumer(
    source_dir: Path,
    environment_root: Path,
    *,
    barrier_marker: Path | None = None,
    peer_marker: Path | None = None,
) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    build_dir = source_dir.with_name(f"{source_dir.name}-build")
    source_dir.mkdir(parents=True)
    lines = [
        "cmake_minimum_required(VERSION 3.24)",
        "project(protocyte_managed_environment LANGUAGES NONE)",
        f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
        f'set(PROTOCYTE_PYTHON_ENV_ROOT "{environment_root.as_posix()}")',
        f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
    ]
    if barrier_marker is not None and peer_marker is not None:
        lines.extend(
            [
                f'file(MAKE_DIRECTORY "{barrier_marker.parent.as_posix()}")',
                f'file(TOUCH "{barrier_marker.as_posix()}")',
                "set(peer_reached_barrier FALSE)",
                "foreach(attempt RANGE 300)",
                f'    if(EXISTS "{peer_marker.as_posix()}")',
                "        set(peer_reached_barrier TRUE)",
                "        break()",
                "    endif()",
                '    execute_process(COMMAND "${CMAKE_COMMAND}" -E sleep 0.1)',
                "endforeach()",
                "if(NOT peer_reached_barrier)",
                '    message(FATAL_ERROR "peer configure did not reach the provisioning barrier")',
                "endif()",
            ]
        )
    lines.extend(
        [
            "_protocyte_prepare_plugin()",
            "_protocyte_get_internal(managed_plugin PLUGIN_EXECUTABLE)",
            'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/managed-plugin.txt" "${managed_plugin}")',
            "",
        ]
    )
    (source_dir / "CMakeLists.txt").write_text("\n".join(lines), encoding="utf-8")
    return build_dir


def _configure_managed_environment(
    source_dir: Path,
    build_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=900,
    )


def _published_managed_environment(environment_root: Path) -> Path:
    environments = [
        candidate
        for candidate in environment_root.iterdir()
        if candidate.is_dir() and (candidate / ".protocyte-ready").is_file()
    ]
    assert len(environments) == 1, environments
    return environments[0]


def _assert_no_managed_environment_transaction_leftovers(
    environment_root: Path,
) -> None:
    leftovers = [
        candidate
        for candidate in environment_root.iterdir()
        if candidate.is_dir()
        and (candidate.name.endswith(".staging") or candidate.name.endswith(".previous"))
    ]
    assert not leftovers, leftovers


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


def test_cmake_generation_uses_utf8_response_file_and_preserves_style_root() -> None:
    functions = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteFunctions.cmake"
    ).read_text(encoding="utf-8")
    generation_command = functions.split("add_custom_command(", 1)[1].split(
        "add_custom_target", 1
    )[0]
    generation_script = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteGenerate.cmake"
    ).read_text(encoding="utf-8")

    assert '"-DARGUMENT_FILE=${protocyte_response_file_relative}"' in generation_command
    assert '"@${ARGUMENT_FILE}"' in generation_script
    assert 'WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"' in generation_command
    assert '"-DSOURCE_DIRECTORY_HEX=${protocyte_source_directory_hex}"' in generation_command
    assert "PROTOCYTE_CMAKE_WORKING_DIRECTORY_HEX=${SOURCE_DIRECTORY_HEX}" in generation_script
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
    assert '"@${PROTOC_RESPONSE_FILE_RELATIVE}"' in quickstart
    assert 'WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"' in quickstart


def test_cmake_protoc_response_file_preserves_utf8_and_literal_arguments(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "write_response.cmake"
    copied_response = tmp_path / "response.txt"
    argument = 'api/café name;literal"quote.proto'
    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                'set(response_content "")',
                f"_protocyte_append_protoc_response_argument(response_content [==[{argument}]==])",
                "_protocyte_write_protoc_response_file(response_file response_relative unit-test \"${response_content}\")",
                f'file(COPY_FILE "${{response_file}}" "{copied_response.as_posix()}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], cwd=tmp_path, check=True)

    assert copied_response.read_text(encoding="utf-8").splitlines() == [argument]


def test_cmake_protoc_response_file_rejects_multiline_arguments(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        '_protocyte_append_protoc_response_argument(content [==[first\nsecond]==])',
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "protoc response files define one literal argument per line" in output


def test_quickstart_generates_with_source_relative_tool_paths(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required to verify quick-start generation")
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "examples" / "quickstart"
    build_dir = tmp_path / "build"
    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    relative_protoc = Path(os.path.relpath(protoc, source_dir)).as_posix()
    relative_plugin = Path(os.path.relpath(plugin, source_dir)).as_posix()

    subprocess.run(
        [
            "cmake",
            "-G",
            "Ninja",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            f"-DPROTOC_EXECUTABLE:FILEPATH={relative_protoc}",
            f"-DPROTOCYTE_PLUGIN_EXECUTABLE:FILEPATH={relative_plugin}",
        ],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            "generated/quickstart.protocyte.hpp",
        ],
        check=True,
    )

    assert (build_dir / "generated" / "quickstart.protocyte.hpp").is_file()


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
    "path_budget",
    [MIN_HASHED_GENERATED_FILE_PATH_BYTES, 120, 510, 511],
)
def test_cmake_complete_generated_path_budget_matches_the_plugin(
    tmp_path: Path, path_budget: int
) -> None:
    long_segment = "é" * 50
    descriptor_name = f"{long_segment}/{long_segment}.proto"
    expected = generated_file_base(
        descriptor_name, max_output_path_bytes=path_budget
    )
    output = tmp_path / "normalized.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "_protocyte_normalize_generated_path(",
                "    normalized",
                f"    [==[{descriptor_name}]==]",
                f"    {path_budget}",
                ")",
                f'file(WRITE "{output.as_posix()}" "${{normalized}}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == expected
    assert len(f"{expected}.hpp".encode("ascii")) <= path_budget


@pytest.mark.parametrize("directory_budget_adjustment", [0, -1])
def test_cmake_generated_directory_budget_matches_the_plugin(
    tmp_path: Path, directory_budget_adjustment: int
) -> None:
    descriptor_name = f"{'readable/' * 12}leaf.proto"
    ordinary_base = generated_file_base(descriptor_name)
    directory_budget = (
        len(ordinary_base.rpartition("/")[0]) + directory_budget_adjustment
    )
    expected = generated_file_base(
        descriptor_name,
        max_output_path_bytes=255,
        max_output_directory_bytes=directory_budget,
    )
    output = tmp_path / "normalized.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "_protocyte_normalize_generated_path(",
                "    normalized",
                f"    [==[{descriptor_name}]==]",
                "    255",
                f"    {directory_budget}",
                ")",
                f'file(WRITE "{output.as_posix()}" "${{normalized}}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == expected


def test_visual_studio_generated_path_budget_accepts_exact_minimum(
    tmp_path: Path,
) -> None:
    output = tmp_path / "budget.txt"
    out_dir_length = 259 - 1 - MIN_HASHED_GENERATED_FILE_PATH_BYTES
    out_dir = "/" + "x" * (out_dir_length - 1)
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                'set(CMAKE_GENERATOR "Visual Studio 17 2022")',
                f'_protocyte_generated_path_budget(path_budget directory_budget "{out_dir}")',
                f'file(WRITE "{output.as_posix()}" "${{path_budget}};${{directory_budget}}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == (
        f"{MIN_HASHED_GENERATED_FILE_PATH_BYTES};"
        f"{MIN_HASHED_GENERATED_FILE_PATH_BYTES - 12}"
    )


def test_visual_studio_generated_path_budget_rejects_impossible_out_dir(
    tmp_path: Path,
) -> None:
    out_dir_length = 259 - MIN_HASHED_GENERATED_FILE_PATH_BYTES
    out_dir = "/" + "x" * (out_dir_length - 1)
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                'set(CMAKE_GENERATOR "Visual Studio 17 2022")',
                f'_protocyte_generated_path_budget(path_budget directory_budget "{out_dir}")',
            ]
        ),
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "OUT_DIR is too long for Visual Studio/MSBuild" in output
    assert "Choose a shorter OUT_DIR or build directory" in output


def test_visual_studio_generated_path_budget_counts_utf16_code_units(
    tmp_path: Path,
) -> None:
    output = tmp_path / "budget.txt"
    out_dir = "/" + "é" * 90
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                'set(CMAKE_GENERATOR "Visual Studio 17 2022")',
                f'_protocyte_generated_path_budget(path_budget directory_budget [==[{out_dir}]==])',
                f'file(WRITE "{output.as_posix()}" "${{path_budget}};${{directory_budget}}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == "167;155"


def test_non_visual_studio_generator_keeps_unbounded_generated_paths(
    tmp_path: Path,
) -> None:
    output = tmp_path / "budget.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                'set(CMAKE_GENERATOR "Ninja")',
                '_protocyte_generated_path_budget(path_budget directory_budget "/very/long/out")',
                f'file(WRITE "{output.as_posix()}" "[${{path_budget}}][${{directory_budget}}]")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text(encoding="utf-8") == "[][]"


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


def test_generate_rejects_generator_expression_out_dir(tmp_path: Path) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        " ".join(
            [
                "protocyte_generate(",
                "TARGET demo_codegen",
                "DESCRIPTOR_SET descriptor.pb",
                'OUT_DIR "$<CONFIG>"',
                "PROTOS api/demo.proto",
                ")",
            ]
        ),
        files={"descriptor.pb": "placeholder"},
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert (
        "OUT_DIR must be a configure-time path, not a generator expression" in output
    )


@pytest.mark.parametrize(
    ("install_include_dir", "expected_error"),
    [
        (
            '"$<IF:$<BOOL:1>,include,other>"',
            "INSTALL_INCLUDE_DIR must be a configure-time relative path, not a generator expression",
        ),
        (
            '"/absolute/include"',
            "INSTALL_INCLUDE_DIR must be a relative install path using '/'",
        ),
        (
            '"C:/absolute/include"',
            "INSTALL_INCLUDE_DIR must be a relative install path using '/'",
        ),
        (
            '"include/../escape"',
            "INSTALL_INCLUDE_DIR contains an unsafe or non-normalized path segment",
        ),
        (
            '"include//nested"',
            "INSTALL_INCLUDE_DIR contains an unsafe or non-normalized path segment",
        ),
    ],
)
def test_proto_library_rejects_non_relocatable_install_include_dir(
    tmp_path: Path,
    install_include_dir: str,
    expected_error: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        " ".join(
            [
                "protocyte_add_proto_library(",
                "TARGET demo",
                "PROTO_ROOT .",
                f"INSTALL_INCLUDE_DIR {install_include_dir}",
                ")",
            ]
        ),
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert expected_error in output


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
    "false_like_value", ["OFF", "NO", "FALSE", "0", "tool-NOTFOUND"]
)
def test_proto_library_rejects_false_like_type_instead_of_defaulting(
    tmp_path: Path,
    false_like_value: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        " ".join(
            [
                "protocyte_add_proto_library(",
                "TARGET demo",
                "PROTO_ROOT .",
                f"TYPE {false_like_value}",
                ")",
            ]
        ),
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert (
        "protocyte_add_proto_library TYPE must be one of: "
        "STATIC, SHARED, MODULE, OBJECT"
    ) in output


def test_generate_preserves_false_like_scalar_and_list_arguments(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "function(_protocyte_setup_codegen_internal fetch_missing_import_sources)",
                "endfunction()",
                "function(_protocyte_encode_generator_parameter out_var value)",
                '    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/options.txt" "${value}")',
                '    set(${out_var} "" PARENT_SCOPE)',
                "endfunction()",
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_OPTIONS_PROTO "${CMAKE_CURRENT_SOURCE_DIR}/FALSE")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES "")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${CMAKE_COMMAND}")',
                'set(PROTOCYTE_PROTOC_EXECUTABLE "${CMAKE_COMMAND}")',
                'set(PROTOCYTE_PROTOC_DEPENDENCY "${CMAKE_COMMAND}")',
                "protocyte_generate(",
                "    TARGET OFF",
                "    DESCRIPTOR_SET FALSE",
                "    OUT_DIR NO",
                "    PROTOS 0",
                "    EMIT_RUNTIME",
                "    RUNTIME_PREFIX OFF",
                "    NAMESPACE_PREFIX NO",
                "    INCLUDE_PREFIX FALSE",
                "    GENERATED_HEADERS_VAR 0",
                "    GENERATED_SOURCES_VAR generated-NOTFOUND",
                "    GENERATED_TARGET_VAR FALSE",
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/outputs.txt"',
                '    "headers=${0}\nsources=${generated-NOTFOUND}\ntarget=${FALSE}\n"',
                ")",
            ]
        ),
        files={"FALSE": "descriptor set placeholder\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    options = (tmp_path / "build" / "options.txt").read_text(encoding="utf-8")
    assert options.split(",")[:3] == [
        "namespace_prefix=NO",
        "include_prefix=FALSE",
        "runtime=emit:OFF",
    ]

    outputs = (tmp_path / "build" / "outputs.txt").read_text(encoding="utf-8")
    normalized_outputs = outputs.replace("\\", "/")
    assert "/build/NO/0.protocyte.hpp" in normalized_outputs
    assert "/build/NO/OFF/runtime.hpp" in normalized_outputs
    assert "/build/NO/0.protocyte.cpp" in normalized_outputs
    assert "target=OFF" in normalized_outputs


def test_proto_library_forwards_false_like_scalar_and_list_arguments(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "enable_language(CXX)",
                "add_library(protocyte_codegen INTERFACE)",
                "add_library(protocyte::codegen ALIAS protocyte_codegen)",
                "add_library(FALSE INTERFACE)",
                "function(protocyte_generate)",
                "    cmake_parse_arguments(",
                "        CAP",
                '        ""',
                '        "TARGET;DESCRIPTOR_SET;PROTO_ROOT;OUT_DIR;GENERATED_HEADERS_VAR;GENERATED_SOURCES_VAR;GENERATED_TARGET_VAR;RUNTIME_PREFIX;NAMESPACE_PREFIX;INCLUDE_PREFIX"',
                '        "PROTOS;IMPORT_DIRS;DEPENDS;OPTIONS"',
                "        ${ARGN}",
                "    )",
                '    file(MAKE_DIRECTORY "${CAP_OUT_DIR}")',
                '    set(stub_header "${CAP_OUT_DIR}/stub.hpp")',
                '    set(stub_source "${CMAKE_CURRENT_BINARY_DIR}/stub.cpp")',
                '    file(WRITE "${stub_header}" "#pragma once\n")',
                '    file(WRITE "${stub_source}" "int protocyte_stub = 0;\n")',
                '    add_custom_target("${CAP_TARGET}")',
                '    set(${CAP_GENERATED_HEADERS_VAR} "${stub_header}" PARENT_SCOPE)',
                '    set(${CAP_GENERATED_SOURCES_VAR} "${stub_source}" PARENT_SCOPE)',
                '    set(${CAP_GENERATED_TARGET_VAR} "${CAP_TARGET}" PARENT_SCOPE)',
                '    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/forwarded.txt"',
                '        "TARGET=${CAP_TARGET}\nPROTO_ROOT=${CAP_PROTO_ROOT}\nOUT_DIR=${CAP_OUT_DIR}\n"',
                '        "PROTOS=${CAP_PROTOS}\nIMPORT_DIRS=${CAP_IMPORT_DIRS}\n"',
                '        "DEPENDS=${CAP_DEPENDS}\nOPTIONS=${CAP_OPTIONS}\n"',
                '        "RUNTIME_PREFIX=${CAP_RUNTIME_PREFIX}\n"',
                '        "NAMESPACE_PREFIX=${CAP_NAMESPACE_PREFIX}\n"',
                '        "INCLUDE_PREFIX=${CAP_INCLUDE_PREFIX}\n"',
                "    )",
                "endfunction()",
                "protocyte_add_proto_library(",
                "    TARGET NO",
                "    ALIAS alias-NOTFOUND",
                "    TYPE STATIC",
                "    PROTO_ROOT FALSE",
                "    OUT_DIR OFF",
                "    PROTOS OFF",
                "    IMPORT_DIRS NO",
                "    DEPENDS FALSE",
                "    OPTIONS comments=off",
                "    RUNTIME_TARGET FALSE",
                "    RUNTIME_PREFIX 0",
                "    NAMESPACE_PREFIX NO",
                "    INCLUDE_PREFIX OFF",
                "    INSTALL_INCLUDE_DIR OFF",
                "    GENERATED_HEADERS_VAR OFF",
                "    GENERATED_SOURCES_VAR NO",
                "    GENERATED_TARGET_VAR target-NOTFOUND",
                ")",
                "get_target_property(alias_target alias-NOTFOUND ALIASED_TARGET)",
                "get_target_property(link_libraries NO LINK_LIBRARIES)",
                "get_target_property(include_directories NO INTERFACE_INCLUDE_DIRECTORIES)",
                "get_target_property(header_sets NO HEADER_SETS)",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/library.txt"',
                '    "alias=${alias_target}\nlinks=${link_libraries}\n"',
                '    "includes=${include_directories}\nheader_sets=${header_sets}\n"',
                '    "headers=${OFF}\nsources=${NO}\ntarget=${target-NOTFOUND}\n"',
                ")",
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    forwarded = (tmp_path / "build" / "forwarded.txt").read_text(encoding="utf-8")
    normalized_forwarded = forwarded.replace("\\", "/")
    assert "TARGET=NO" in forwarded
    assert "PROTO_ROOT=FALSE" in forwarded
    assert "/build/OFF" in normalized_forwarded
    assert "PROTOS=OFF" in forwarded
    assert "IMPORT_DIRS=NO" in forwarded
    assert "DEPENDS=FALSE" in forwarded
    assert "OPTIONS=comments=off" in forwarded
    assert "RUNTIME_PREFIX=0" in forwarded
    assert "NAMESPACE_PREFIX=NO" in forwarded
    assert "INCLUDE_PREFIX=OFF" in forwarded

    library = (tmp_path / "build" / "library.txt").read_text(encoding="utf-8")
    normalized_library = library.replace("\\", "/")
    assert "alias=NO" in library
    assert "links=protocyte::codegen;FALSE" in library
    assert "$<BUILD_INTERFACE:" in normalized_library
    assert "/build/OFF>" in normalized_library
    assert "$<INSTALL_INTERFACE:OFF>" in library
    assert "header_sets=protocyte_generated_headers" in library
    assert "stub.hpp" in library
    assert "stub.cpp" in library
    assert "target=NO__protocyte_codegen" in library


def test_proto_library_default_build_only_target_can_be_exported(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "enable_language(CXX)",
                "add_library(protocyte::codegen INTERFACE IMPORTED)",
                "add_library(protocyte::runtime INTERFACE IMPORTED)",
                "function(protocyte_generate)",
                "    cmake_parse_arguments(",
                "        CAP",
                '        ""',
                '        "TARGET;OUT_DIR;GENERATED_HEADERS_VAR;GENERATED_SOURCES_VAR;GENERATED_TARGET_VAR"',
                '        ""',
                "        ${ARGN}",
                "    )",
                '    file(MAKE_DIRECTORY "${CAP_OUT_DIR}")',
                '    set(stub_header "${CAP_OUT_DIR}/stub.hpp")',
                '    set(stub_source "${CAP_OUT_DIR}/stub.cpp")',
                '    file(WRITE "${stub_header}" "#pragma once\n")',
                '    file(WRITE "${stub_source}" "int protocyte_stub = 0;\n")',
                '    add_custom_target("${CAP_TARGET}")',
                '    set(${CAP_GENERATED_HEADERS_VAR} "${stub_header}" PARENT_SCOPE)',
                '    set(${CAP_GENERATED_SOURCES_VAR} "${stub_source}" PARENT_SCOPE)',
                '    set(${CAP_GENERATED_TARGET_VAR} "${CAP_TARGET}" PARENT_SCOPE)',
                "endfunction()",
                "protocyte_add_proto_library(",
                "    TARGET demo_proto",
                "    PROTO_ROOT .",
                "    DISCOVER",
                ")",
                "get_target_property(include_directories demo_proto INTERFACE_INCLUDE_DIRECTORIES)",
                "get_target_property(header_sets demo_proto HEADER_SETS)",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/target.txt"',
                '    "includes=${include_directories}\nheader_sets=${header_sets}\n"',
                ")",
                "install(TARGETS demo_proto EXPORT demoTargets)",
                "install(EXPORT demoTargets DESTINATION lib/cmake/demo)",
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    target = (tmp_path / "build" / "target.txt").read_text(encoding="utf-8")
    normalized_target = target.replace("\\", "/")
    assert "$<BUILD_INTERFACE:" in normalized_target
    assert "/build/demo_proto_protocyte>" in normalized_target
    assert "$<INSTALL_INTERFACE:" not in target
    assert "header_sets=\n" in target


def test_descriptor_library_forwards_false_like_scalar_and_list_arguments(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "function(protocyte_add_proto_library)",
                "    cmake_parse_arguments(",
                "        CAP",
                '        "DISCOVER;EMIT_RUNTIME;HOSTED_ALLOCATOR"',
                '        "TARGET;ALIAS;TYPE;DESCRIPTOR_SET;OUT_DIR;GENERATED_HEADERS_VAR;GENERATED_SOURCES_VAR;GENERATED_TARGET_VAR;RUNTIME_TARGET;RUNTIME_PREFIX;NAMESPACE_PREFIX;INCLUDE_PREFIX;INSTALL_INCLUDE_DIR"',
                '        "PROTOS;DEPENDS;OPTIONS"',
                "        ${ARGN}",
                "    )",
                '    set(${CAP_GENERATED_HEADERS_VAR} "headers" PARENT_SCOPE)',
                '    set(${CAP_GENERATED_SOURCES_VAR} "sources" PARENT_SCOPE)',
                '    set(${CAP_GENERATED_TARGET_VAR} "codegen" PARENT_SCOPE)',
                '    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/forwarded.txt"',
                '        "TARGET=${CAP_TARGET}\nALIAS=${CAP_ALIAS}\nTYPE=${CAP_TYPE}\n"',
                '        "DESCRIPTOR_SET=${CAP_DESCRIPTOR_SET}\nOUT_DIR=${CAP_OUT_DIR}\n"',
                '        "PROTOS=${CAP_PROTOS}\nDEPENDS=${CAP_DEPENDS}\nOPTIONS=${CAP_OPTIONS}\n"',
                '        "RUNTIME_TARGET=${CAP_RUNTIME_TARGET}\n"',
                '        "RUNTIME_PREFIX=${CAP_RUNTIME_PREFIX}\n"',
                '        "NAMESPACE_PREFIX=${CAP_NAMESPACE_PREFIX}\n"',
                '        "INCLUDE_PREFIX=${CAP_INCLUDE_PREFIX}\n"',
                '        "INSTALL_INCLUDE_DIR=${CAP_INSTALL_INCLUDE_DIR}\n"',
                "    )",
                "endfunction()",
                "protocyte_add_descriptor_set_library(",
                "    TARGET OFF",
                "    ALIAS NO",
                "    TYPE STATIC",
                "    DESCRIPTOR_SET FALSE",
                "    OUT_DIR 0",
                "    FILES OFF",
                "    DEPENDS NO",
                "    OPTIONS comments=off",
                "    RUNTIME_TARGET OFF",
                "    RUNTIME_PREFIX NO",
                "    NAMESPACE_PREFIX FALSE",
                "    INCLUDE_PREFIX 0",
                "    INSTALL_INCLUDE_DIR OFF",
                "    GENERATED_HEADERS_VAR output-NOTFOUND",
                "    GENERATED_SOURCES_VAR OFF",
                "    GENERATED_TARGET_VAR NO",
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/outputs.txt"',
                '    "headers=${output-NOTFOUND}\nsources=${OFF}\ntarget=${NO}\n"',
                ")",
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    forwarded = (tmp_path / "build" / "forwarded.txt").read_text(encoding="utf-8")
    assert "TARGET=OFF" in forwarded
    assert "ALIAS=NO" in forwarded
    assert "TYPE=STATIC" in forwarded
    assert "DESCRIPTOR_SET=FALSE" in forwarded
    assert "OUT_DIR=0" in forwarded
    assert "PROTOS=OFF" in forwarded
    assert "DEPENDS=NO" in forwarded
    assert "OPTIONS=comments=off" in forwarded
    assert "RUNTIME_TARGET=OFF" in forwarded
    assert "RUNTIME_PREFIX=NO" in forwarded
    assert "NAMESPACE_PREFIX=FALSE" in forwarded
    assert "INCLUDE_PREFIX=0" in forwarded
    assert "INSTALL_INCLUDE_DIR=OFF" in forwarded
    assert (tmp_path / "build" / "outputs.txt").read_text(encoding="utf-8") == (
        "headers=headers\nsources=sources\ntarget=codegen\n"
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
            "protocyte_add_proto_library(TARGET demo PROTO_ROOT proto DISCOVER PROTOS OFF)",
            "protocyte_add_proto_library accepts either DISCOVER or PROTOS, not both",
        ),
        (
            "protocyte_add_descriptor_set_library(TARGET demo DESCRIPTOR_SET descriptor_set.pb DISCOVER FILES OFF)",
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
            "protocyte_generate(TARGET demo OUT_DIR generated DISCOVER)",
            "protocyte_generate requires either PROTO_ROOT or DESCRIPTOR_SET",
        ),
        (
            "protocyte_generate(TARGET demo PROTO_ROOT proto OUT_DIR generated)",
            "protocyte_generate requires either DISCOVER or PROTOS",
        ),
        (
            "protocyte_add_proto_library(TARGET demo DISCOVER)",
            "protocyte_add_proto_library requires either PROTO_ROOT or DESCRIPTOR_SET",
        ),
        (
            "protocyte_add_proto_library(TARGET demo PROTO_ROOT proto)",
            "protocyte_add_proto_library requires either DISCOVER or PROTOS",
        ),
        (
            "protocyte_add_descriptor_set_library(DESCRIPTOR_SET descriptor_set.pb FILES demo.proto)",
            "protocyte_add_descriptor_set_library requires TARGET",
        ),
        (
            "protocyte_add_descriptor_set_library(TARGET demo DESCRIPTOR_SET descriptor_set.pb)",
            "protocyte_add_descriptor_set_library requires either DISCOVER or FILES",
        ),
    ],
)
def test_public_cmake_functions_report_missing_input_modes_from_called_helper(
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
    ("api", "first_owner", "second_owner"),
    [
        ("generate", "first_codegen", "second_codegen"),
        (
            "proto_library",
            "first_library__protocyte_codegen",
            "second_library__protocyte_codegen",
        ),
        (
            "descriptor_library",
            "first_library__protocyte_codegen",
            "second_library__protocyte_codegen",
        ),
    ],
)
@pytest.mark.parametrize(
    "second_options",
    [
        pytest.param(("format=off",), id="same-options"),
        pytest.param(("comments=off",), id="different-options"),
    ],
)
def test_cmake_rejects_multiple_owners_for_one_emitted_runtime(
    tmp_path: Path,
    api: str,
    first_owner: str,
    second_owner: str,
    second_options: tuple[str, ...],
) -> None:
    result, _ = _configure_runtime_ownership_project(
        tmp_path,
        api=api,
        first_out_dir="shared",
        second_out_dir="shared",
        second_options=second_options,
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "runtime output" in output
    assert "shared/protocyte/runtime/runtime.hpp" in output.replace("\\", "/")
    assert f"already owned by code generation target '{first_owner}'" in output
    assert f"target '{second_owner}' cannot also use EMIT_RUNTIME" in output
    assert "RUNTIME_TARGET" in output


@pytest.mark.parametrize("api", ["generate", "proto_library", "descriptor_library"])
@pytest.mark.parametrize(
    (
        "first_out_dir",
        "second_out_dir",
        "first_prefix",
        "second_prefix",
        "expected_first_runtime",
        "expected_second_runtime",
    ),
    [
        pytest.param(
            "shared",
            "shared",
            "runtime/first",
            "runtime/second",
            "shared/runtime/first/runtime.hpp",
            "shared/runtime/second/runtime.hpp",
            id="different-prefixes",
        ),
        pytest.param(
            "first-output",
            "second-output",
            None,
            None,
            "first-output/protocyte/runtime/runtime.hpp",
            "second-output/protocyte/runtime/runtime.hpp",
            id="different-output-directories",
        ),
    ],
)
def test_cmake_allows_distinct_emitted_runtime_outputs(
    tmp_path: Path,
    api: str,
    first_out_dir: str,
    second_out_dir: str,
    first_prefix: str | None,
    second_prefix: str | None,
    expected_first_runtime: str,
    expected_second_runtime: str,
) -> None:
    result, headers_output = _configure_runtime_ownership_project(
        tmp_path,
        api=api,
        first_out_dir=first_out_dir,
        second_out_dir=second_out_dir,
        first_prefix=first_prefix,
        second_prefix=second_prefix,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    headers = headers_output.read_text(encoding="utf-8").replace("\\", "/")
    first_headers, second_headers = headers.splitlines()
    assert expected_first_runtime in first_headers
    assert expected_second_runtime in second_headers


@pytest.mark.parametrize(
    ("function_name", "one_value_keywords"),
    [
        (
            "protocyte_generate",
            (
                "TARGET",
                "DESCRIPTOR_SET",
                "PROTO_ROOT",
                "OUT_DIR",
                "GENERATED_HEADERS_VAR",
                "GENERATED_SOURCES_VAR",
                "GENERATED_TARGET_VAR",
                "RUNTIME_PREFIX",
                "NAMESPACE_PREFIX",
                "INCLUDE_PREFIX",
            ),
        ),
        (
            "protocyte_add_proto_library",
            (
                "TARGET",
                "ALIAS",
                "TYPE",
                "DESCRIPTOR_SET",
                "PROTO_ROOT",
                "OUT_DIR",
                "GENERATED_HEADERS_VAR",
                "GENERATED_SOURCES_VAR",
                "GENERATED_TARGET_VAR",
                "RUNTIME_TARGET",
                "RUNTIME_PREFIX",
                "NAMESPACE_PREFIX",
                "INCLUDE_PREFIX",
                "INSTALL_INCLUDE_DIR",
            ),
        ),
        (
            "protocyte_add_descriptor_set_library",
            (
                "TARGET",
                "ALIAS",
                "TYPE",
                "DESCRIPTOR_SET",
                "OUT_DIR",
                "GENERATED_HEADERS_VAR",
                "GENERATED_SOURCES_VAR",
                "GENERATED_TARGET_VAR",
                "RUNTIME_TARGET",
                "RUNTIME_PREFIX",
                "NAMESPACE_PREFIX",
                "INCLUDE_PREFIX",
                "INSTALL_INCLUDE_DIR",
            ),
        ),
    ],
)
def test_public_cmake_functions_reject_duplicate_single_value_keywords(
    tmp_path: Path,
    function_name: str,
    one_value_keywords: tuple[str, ...],
) -> None:
    duplicate_arguments = " ".join(
        f"{keyword} first {keyword} second" for keyword in one_value_keywords
    )
    result = _configure_cmake_snippet(
        tmp_path,
        f"{function_name}({duplicate_arguments})",
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    expected_keywords = ", ".join(one_value_keywords)
    assert (
        f"{function_name} received duplicate single-value keyword(s): "
        f"{expected_keywords}"
    ) in output


@pytest.mark.parametrize(
    "snippet",
    [
        """
function(_protocyte_setup_codegen_internal fetch_missing_import_sources)
    message(FATAL_ERROR "reached protocyte_generate downstream validation")
endfunction()
protocyte_generate(
    TARGET demo
    PROTO_ROOT proto
    OUT_DIR generated
    PROTOS proto/simple.proto proto/simple.proto
    PROTOS proto/simple.proto
)
""",
        """
function(protocyte_generate)
    message(FATAL_ERROR "reached protocyte_add_proto_library downstream validation")
endfunction()
protocyte_add_proto_library(
    TARGET demo
    PROTO_ROOT proto
    PROTOS proto/simple.proto proto/simple.proto
    PROTOS proto/simple.proto
)
""",
        """
function(protocyte_add_proto_library)
    message(FATAL_ERROR "reached protocyte_add_descriptor_set_library downstream validation")
endfunction()
protocyte_add_descriptor_set_library(
    TARGET demo
    DESCRIPTOR_SET descriptors.pb
    FILES simple.proto simple.proto
    FILES simple.proto
)
""",
    ],
)
def test_duplicate_keyword_validation_allows_repeated_multi_value_lists(
    tmp_path: Path,
    snippet: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        snippet,
        files={"proto/simple.proto": 'syntax = "proto3"; message Demo {}\n'},
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "reached protocyte_" in output
    assert "duplicate single-value keyword" not in output


@pytest.mark.parametrize(
    "function_name",
    [
        "protocyte_generate",
        "protocyte_add_proto_library",
        "protocyte_add_descriptor_set_library",
    ],
)
def test_public_cmake_functions_reject_options_without_values(
    tmp_path: Path,
    function_name: str,
) -> None:
    result = _configure_cmake_snippet(tmp_path, f"{function_name}(OPTIONS)")

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert (
        f"{function_name} requires a value for the following keyword(s): OPTIONS"
        in output
    )


@pytest.mark.parametrize(
    ("function_name", "forwarded_option"),
    [
        (function_name, forwarded_option)
        for function_name in (
            "protocyte_generate",
            "protocyte_add_proto_library",
            "protocyte_add_descriptor_set_library",
        )
        for forwarded_option in (
            "HOSTED_ALOCATOR",
            "comments=off,HOSTED_ALOCATOR",
        )
    ],
)
def test_public_cmake_functions_reject_bare_forwarded_options(
    tmp_path: Path,
    function_name: str,
    forwarded_option: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        f"{function_name}(OPTIONS {forwarded_option})",
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert (
        f"{function_name} OPTIONS entry 'HOSTED_ALOCATOR' must use key=value"
        in output
    )


@pytest.mark.parametrize(
    "function_name",
    [
        "protocyte_generate",
        "protocyte_add_proto_library",
        "protocyte_add_descriptor_set_library",
    ],
)
def test_public_cmake_functions_accept_forwarded_key_value_syntax(
    tmp_path: Path,
    function_name: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        f'{function_name}(OPTIONS "comments=off" "clang_format=")',
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "OPTIONS entry" not in output
    if function_name == "protocyte_add_descriptor_set_library":
        assert f"{function_name} requires DESCRIPTOR_SET" in output
    else:
        assert f"{function_name} requires TARGET" in output


def test_duplicate_keyword_validation_preserves_semicolon_descriptor_value(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        """
function(protocyte_add_proto_library)
    message(FATAL_ERROR "reached descriptor wrapper downstream validation")
endfunction()
protocyte_add_descriptor_set_library(
    TARGET demo
    DESCRIPTOR_SET descriptors.pb
    FILES "api/demo;TARGET;legacy.proto"
)
""",
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "reached descriptor wrapper downstream validation" in output
    assert "duplicate single-value keyword" not in output


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
    assert any(prefix.rglob("ProtocyteGenerate.cmake"))
    assert (prefix / "share/protocyte/python/pyproject.toml").is_file()


@pytest.mark.parametrize("library_mode", ["source", "descriptor-set"])
def test_proto_library_installs_exports_and_reconsumes_from_relocated_prefix(
    tmp_path: Path,
    library_mode: str,
) -> None:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required for the install/export integration test")

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    (tmp_path / "tools").mkdir()
    plugin = _write_python_plugin_wrapper(
        tmp_path / "tools" / "protoc-gen-protocyte", repo_root
    )
    core_build_dir = tmp_path / "protocyte-build"
    provider_source_dir = tmp_path / "provider"
    provider_build_dir = tmp_path / "provider-build"
    install_prefix = tmp_path / "install"
    relocated_prefix = tmp_path / "relocated-install"
    consumer_source_dir = tmp_path / "consumer"
    consumer_build_dir = tmp_path / "consumer-build"

    proto_dir = provider_source_dir / "proto"
    proto_file = proto_dir / "api" / "demo.proto"
    proto_file.parent.mkdir(parents=True)
    proto_file.write_text(
        'syntax = "proto3"; package api; message Demo { int32 id = 1; }\n',
        encoding="utf-8",
    )
    descriptor_set = provider_source_dir / "descriptor-set.pb"
    if library_mode == "descriptor-set":
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

    subprocess.run(
        [
            "cmake",
            "-G",
            "Ninja",
            "-S",
            str(repo_root),
            "-B",
            str(core_build_dir),
            "-DPROTOCYTE_INSTALL=ON",
            "-DPROTOCYTE_FETCH_PROTOBUF=OFF",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--install", str(core_build_dir)], check=True)

    if library_mode == "source":
        helper_invocation = "\n".join(
            [
                "protocyte_add_proto_library(",
                "    TARGET installable_proto",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                "    DISCOVER",
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                '    INSTALL_INCLUDE_DIR "${CMAKE_INSTALL_INCLUDEDIR}"',
                "    OPTIONS format=off",
                ")",
            ]
        )
        installed_runtime = install_prefix / "include/protocyte/runtime/runtime.hpp"
        runtime_include = "protocyte/runtime/runtime.hpp"
    else:
        helper_invocation = "\n".join(
            [
                "protocyte_add_descriptor_set_library(",
                "    TARGET installable_proto",
                '    DESCRIPTOR_SET "${CMAKE_CURRENT_SOURCE_DIR}/descriptor-set.pb"',
                "    FILES api/demo.proto",
                "    EMIT_RUNTIME",
                "    RUNTIME_PREFIX vendor/runtime",
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                '    INSTALL_INCLUDE_DIR "${CMAKE_INSTALL_INCLUDEDIR}"',
                "    OPTIONS format=off",
                ")",
            ]
        )
        installed_runtime = install_prefix / "include/vendor/runtime/runtime.hpp"
        runtime_include = "vendor/runtime/runtime.hpp"

    (provider_source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(installable_proto_provider LANGUAGES CXX)",
                "include(GNUInstallDirs)",
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "find_package(protocyte CONFIG REQUIRED)",
                helper_invocation,
                "set_target_properties(installable_proto PROPERTIES EXPORT_NAME proto)",
                "install(",
                "    TARGETS installable_proto",
                "    EXPORT installable_protoTargets",
                '    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"',
                '    LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"',
                '    RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"',
                "    FILE_SET protocyte_generated_headers",
                '        DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"',
                ")",
                "install(",
                "    EXPORT installable_protoTargets",
                "    NAMESPACE installable::",
                '    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/installable_proto"',
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/installable_protoConfig.cmake" [=[',
                "include(CMakeFindDependencyMacro)",
                "find_dependency(protocyte CONFIG)",
                'include("${CMAKE_CURRENT_LIST_DIR}/installable_protoTargets.cmake")',
                "]=])",
                "install(",
                '    FILES "${CMAKE_CURRENT_BINARY_DIR}/installable_protoConfig.cmake"',
                '    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/installable_proto"',
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "cmake",
            "-G",
            "Ninja",
            "-S",
            str(provider_source_dir),
            "-B",
            str(provider_build_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_PREFIX_PATH={install_prefix}",
            f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(provider_build_dir)], check=True)
    subprocess.run(["cmake", "--install", str(provider_build_dir)], check=True)

    installed_header = install_prefix / "include/api/demo.protocyte.hpp"
    installed_targets = (
        install_prefix / "lib/cmake/installable_proto/installable_protoTargets.cmake"
    )
    assert installed_header.is_file()
    assert installed_runtime.is_file()
    normalized_targets = installed_targets.read_text(encoding="utf-8").replace(
        "\\", "/"
    )
    assert provider_build_dir.as_posix() not in normalized_targets
    assert "protocyte_generated_headers" in normalized_targets

    shutil.rmtree(provider_build_dir)
    shutil.rmtree(provider_source_dir)
    install_prefix.rename(relocated_prefix)

    consumer_source_dir.mkdir()
    (consumer_source_dir / "main.cpp").write_text(
        "\n".join(
            [
                "#include <type_traits>",
                f'#include "{runtime_include}"',
                '#include "api/demo.protocyte.hpp"',
                "static_assert(std::is_class_v<::api::Demo<>>);",
                "int main() { return 0; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (consumer_source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(installable_proto_consumer LANGUAGES CXX)",
                "find_package(installable_proto CONFIG REQUIRED)",
                "add_executable(consumer main.cpp)",
                "target_link_libraries(consumer PRIVATE installable::proto)",
                "enable_testing()",
                "add_test(NAME consumer COMMAND consumer)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "cmake",
            "-G",
            "Ninja",
            "-S",
            str(consumer_source_dir),
            "-B",
            str(consumer_build_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_PREFIX_PATH={relocated_prefix}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(consumer_build_dir)], check=True)
    subprocess.run(
        ["ctest", "--test-dir", str(consumer_build_dir), "--output-on-failure"],
        check=True,
    )


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
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "_protocyte_ensure_protobuf(TRUE)",
                f'file(WRITE "{resolved_output.as_posix()}" "${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}")',
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
                "_protocyte_ensure_protobuf(FALSE)",
            ]
        ),
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "Protobuf_PROTOC_EXECUTABLE 'tools/missing-protoc' resolves to" in output
    assert "does not name an existing file" in output


def test_protoc_target_preserves_generator_expression_and_target_dependency(
    tmp_path: Path,
) -> None:
    target_name = "protobuf::protoc"
    selected = tmp_path / "build" / "selected.txt"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f"add_executable({target_name} IMPORTED)",
                f'set_target_properties({target_name} PROPERTIES IMPORTED_LOCATION "${{CMAKE_CURRENT_SOURCE_DIR}}/tools/protoc")',
                'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/protobuf")',
                "_protocyte_ensure_protobuf(FALSE)",
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


def test_explicit_host_protoc_overrides_target_when_cross_compiling(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    host_protoc = _write_protobuf_toolchain(source_dir / "host-toolchain")
    target_protoc = source_dir / "target-toolchain" / "bin" / "protoc"
    target_protoc.parent.mkdir(parents=True)
    target_protoc.write_text("", encoding="utf-8")
    selected = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_host_protoc LANGUAGES NONE)",
                'if(NOT CMAKE_CROSSCOMPILING)',
                '    message(FATAL_ERROR "fixture did not configure as a cross build")',
                "endif()",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "add_executable(protobuf::protoc IMPORTED)",
                f'set_target_properties(protobuf::protoc PROPERTIES IMPORTED_LOCATION "{target_protoc.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{host_protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(source_dir / "host-toolchain" / "include").as_posix()}")',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "_protocyte_ensure_protobuf(FALSE)",
                f'file(WRITE "{selected.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            "-DCMAKE_SYSTEM_NAME=Generic",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert selected.read_text(encoding="utf-8").splitlines() == [
        host_protoc.as_posix(),
        host_protoc.as_posix(),
    ]


def test_path_protoc_precedes_fetch_and_ignores_generic_target(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    path_protoc = source_dir / "host-toolchain" / "bin" / executable_name
    path_protoc.parent.mkdir(parents=True)
    path_protoc.write_text("", encoding="utf-8")
    if os.name != "nt":
        path_protoc.chmod(0o755)
    descriptor = (
        source_dir
        / "host-toolchain"
        / "include"
        / "google"
        / "protobuf"
        / "descriptor.proto"
    )
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    ambient_protoc = source_dir / "ambient" / "protoc"
    ambient_protoc.parent.mkdir()
    ambient_protoc.write_text("", encoding="utf-8")
    selected = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(path_host_protoc LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF ON)",
                "set(FETCHCONTENT_FULLY_DISCONNECTED ON)",
                "add_executable(protoc IMPORTED)",
                f'set_target_properties(protoc PROPERTIES IMPORTED_LOCATION "{ambient_protoc.as_posix()}")',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "_protocyte_ensure_protobuf(TRUE)",
                'if(TARGET protobuf::protoc)',
                '    message(FATAL_ERROR "PATH protoc unexpectedly triggered the full protobuf fallback")',
                "endif()",
                f'file(WRITE "{selected.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}\n")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(path_protoc.parent), env.get("PATH", "")])

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert selected.read_text(encoding="utf-8").splitlines() == [
        path_protoc.as_posix(),
        path_protoc.as_posix(),
        (source_dir / "host-toolchain" / "include").as_posix(),
    ]


@pytest.mark.parametrize("protoc_selection", ["external_path", "imported_target"])
def test_fetch_fallback_provisions_imports_for_an_existing_protoc(
    tmp_path: Path, protoc_selection: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; message Demo {}\n', encoding="utf-8"
    )
    protoc = source_dir / "tools" / "protoc"
    protoc.parent.mkdir()
    protoc.write_text("", encoding="utf-8")
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    fetched_source = source_dir / "fetched-protobuf"
    descriptor = fetched_source / "src" / "google" / "protobuf" / "descriptor.proto"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    resolved_output = build_dir / "resolved-import.txt"
    if protoc_selection == "external_path":
        protoc_setup = [f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")']
    else:
        protoc_setup = [
            "add_executable(protobuf::protoc IMPORTED)",
            f'set_target_properties(protobuf::protoc PROPERTIES IMPORTED_LOCATION "{protoc.as_posix()}")',
        ]

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(fetch_missing_imports LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF ON)",
                'set(PROTOCYTE_PROTOBUF_GIT_TAG "test-fixture")',
                f'set(FETCHCONTENT_SOURCE_DIR_PROTOCYTE_PROTOBUF_IMPORTS "{fetched_source.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                *protoc_setup,
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/demo.proto",
                ")",
                "if(TARGET protobuf::libprotobuf OR TARGET libprotobuf)",
                '    message(FATAL_ERROR "import-only fallback unexpectedly added protobuf libraries")',
                "endif()",
                f'file(WRITE "{resolved_output.as_posix()}" "${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    assert resolved_output.read_text(encoding="utf-8") == (fetched_source / "src").as_posix()


def test_fetch_fallback_import_sources_build_with_real_protoc(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required to verify fetched import source generation")
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    real_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; message Demo {}\n', encoding="utf-8"
    )
    invocation_log = source_dir / "protoc-invocations.txt"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    fetched_source = source_dir / "fetched-protobuf"
    fetched_descriptor = (
        fetched_source / "src" / "google" / "protobuf" / "descriptor.proto"
    )
    fetched_descriptor.parent.mkdir(parents=True)
    shutil.copy2(
        real_import_dir / "google" / "protobuf" / "descriptor.proto",
        fetched_descriptor,
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(fetch_import_build LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF ON)",
                'set(PROTOCYTE_PROTOBUF_GIT_TAG "test-fixture")',
                f'set(FETCHCONTENT_SOURCE_DIR_PROTOCYTE_PROTOBUF_IMPORTS "{fetched_source.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
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
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
    )

    assert (build_dir / "generated" / "demo.protocyte.hpp").is_file()
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
    ]


def test_eager_setup_fetches_missing_import_sources_for_an_existing_protoc(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    protoc = source_dir / "tools" / "protoc"
    protoc.parent.mkdir()
    protoc.write_text("", encoding="utf-8")
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    fetched_source = source_dir / "fetched-protobuf"
    descriptor = fetched_source / "src" / "google" / "protobuf" / "descriptor.proto"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    resolved_output = build_dir / "resolved-import.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(eager_fetch_missing_imports LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF ON)",
                'set(PROTOCYTE_PROTOBUF_GIT_TAG "test-fixture")',
                f'set(FETCHCONTENT_SOURCE_DIR_PROTOCYTE_PROTOBUF_IMPORTS "{fetched_source.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_setup_codegen()",
                f'file(WRITE "{resolved_output.as_posix()}" "${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    assert resolved_output.read_text(encoding="utf-8") == (fetched_source / "src").as_posix()


def test_eager_setup_keeps_an_inherited_relative_protoc_stable(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    child_dir = source_dir / "child"
    sibling_dir = source_dir / "sibling"
    for directory in (child_dir, sibling_dir):
        directory.mkdir(parents=True)
        (directory / "demo.proto").write_text(
            'syntax = "proto3"; message Demo {}\n', encoding="utf-8"
        )
    protoc = _write_protobuf_toolchain(source_dir / "toolchain")
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    selected_outputs = [
        build_dir / "child" / "selected.txt",
        build_dir / "sibling" / "selected.txt",
    ]

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(eager_relative_protoc LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                'set(Protobuf_PROTOC_EXECUTABLE "toolchain/bin/protoc")',
                "protocyte_setup_codegen()",
                "add_subdirectory(child)",
                "add_subdirectory(sibling)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for directory, selected_output in zip(
        (child_dir, sibling_dir), selected_outputs, strict=True
    ):
        (directory / "CMakeLists.txt").write_text(
            "\n".join(
                [
                    f"protocyte_generate(TARGET {directory.name}_codegen",
                    '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"',
                    '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                    "    PROTOS demo.proto",
                    ")",
                    f'file(WRITE "{selected_output.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}\n")',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    expected_selection = [
        protoc.as_posix(),
        protoc.as_posix(),
        (source_dir / "toolchain" / "include").as_posix(),
    ]
    for selected_output in selected_outputs:
        assert selected_output.read_text(encoding="utf-8").splitlines() == expected_selection


def test_siblings_reuse_the_first_relative_protoc_resolution(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    first_dir = source_dir / "first"
    second_dir = source_dir / "second"
    first_dir.mkdir(parents=True)
    second_dir.mkdir()
    protoc = _write_protobuf_toolchain(first_dir / "toolchain")
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(sibling_relative_protoc LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                'set(Protobuf_PROTOC_EXECUTABLE "toolchain/bin/protoc")',
                "add_subdirectory(first)",
                "add_subdirectory(second)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    selected_outputs = []
    for directory in (first_dir, second_dir):
        selected_output = build_dir / directory.name / "selected.txt"
        selected_outputs.append(selected_output)
        (directory / "CMakeLists.txt").write_text(
            "\n".join(
                [
                    "protocyte_setup_codegen()",
                    f'file(WRITE "{selected_output.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}\n")',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    expected_selection = [
        protoc.as_posix(),
        (first_dir / "toolchain" / "include").as_posix(),
    ]
    for selected_output in selected_outputs:
        assert selected_output.read_text(encoding="utf-8").splitlines() == expected_selection


def test_switching_protoc_toolchains_refreshes_the_automatic_import_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    child_dir = source_dir / "child"
    child_dir.mkdir(parents=True)
    first_protoc = _write_protobuf_toolchain(source_dir / "toolchain-a")
    second_protoc = _write_protobuf_toolchain(source_dir / "toolchain-b")
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    selected_output = build_dir / "child" / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(switched_protoc_toolchain LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{first_protoc.as_posix()}")',
                "protocyte_setup_codegen()",
                "add_subdirectory(child)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (child_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                f'set(Protobuf_PROTOC_EXECUTABLE "{second_protoc.as_posix()}")',
                "protocyte_setup_codegen()",
                'if(DEFINED PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR)',
                '    message(FATAL_ERROR "successful toolchain switch retained stale import metadata")',
                "endif()",
                f'file(WRITE "{selected_output.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}\n")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-S", str(source_dir), "-B", str(build_dir)], check=True)

    second_import_dir = (source_dir / "toolchain-b" / "include").as_posix()
    assert selected_output.read_text(encoding="utf-8").splitlines() == [
        second_protoc.as_posix(),
        second_import_dir,
    ]


def test_reconfigure_migrates_automatic_import_cache_and_honors_explicit_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    first_protoc = _write_protobuf_toolchain(source_dir / "toolchain-a")
    second_protoc = _write_protobuf_toolchain(source_dir / "toolchain-b")
    first_import_dir = source_dir / "toolchain-a" / "include"
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )
    selected_output = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(import_cache_migration LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                "if(SELECT_SECOND_TOOLCHAIN)",
                f'    set(Protobuf_PROTOC_EXECUTABLE "{second_protoc.as_posix()}")',
                "else()",
                f'    set(Protobuf_PROTOC_EXECUTABLE "{first_protoc.as_posix()}")',
                "endif()",
                "protocyte_setup_codegen()",
                "get_property(public_import_type CACHE PROTOCYTE_PROTOBUF_IMPORT_DIR PROPERTY TYPE)",
                f'file(WRITE "{selected_output.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}}\n${{PROTOCYTE_PROTOBUF_IMPORT_DIR}}\n${{public_import_type}}\n")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    old_toolchain_identity = f"{first_protoc.as_posix()}|{first_protoc.as_posix()}"

    first_result = subprocess.run(
        [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            f"-DPROTOCYTE_PROTOBUF_IMPORT_DIR:INTERNAL={first_import_dir.as_posix()}",
            f"-DPROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR:INTERNAL={first_import_dir.as_posix()}",
            f"-DPROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN:INTERNAL={old_toolchain_identity}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    assert selected_output.read_text(encoding="utf-8").splitlines() == [
        first_protoc.as_posix(),
        first_import_dir.as_posix(),
        "",
        "",
    ]
    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert "\nPROTOCYTE_PROTOBUF_IMPORT_DIR:" not in f"\n{cache}"

    second_result = subprocess.run(
        [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            "-DSELECT_SECOND_TOOLCHAIN=ON",
            f"-DPROTOCYTE_PROTOBUF_IMPORT_DIR:PATH={first_import_dir.as_posix()}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    assert selected_output.read_text(encoding="utf-8").splitlines() == [
        second_protoc.as_posix(),
        first_import_dir.as_posix(),
        first_import_dir.as_posix(),
        "PATH",
    ]


def test_switching_protoc_rejects_stale_automatic_source_variables(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    child_dir = source_dir / "child"
    child_dir.mkdir(parents=True)
    (child_dir / "demo.proto").write_text(
        'syntax = "proto3"; message Demo {}\n', encoding="utf-8"
    )
    first_protoc = _write_protobuf_toolchain(source_dir / "toolchain-a")
    second_protoc = source_dir / "toolchain-b" / "bin" / "protoc"
    second_protoc.parent.mkdir(parents=True)
    second_protoc.write_text("", encoding="utf-8")
    stale_source = source_dir / "stale-protobuf-source"
    stale_source_descriptor = (
        stale_source / "src" / "google" / "protobuf" / "descriptor.proto"
    )
    stale_source_descriptor.parent.mkdir(parents=True)
    stale_source_descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    stale_include = source_dir / "stale-protobuf-include"
    stale_include_descriptor = stale_include / "google" / "protobuf" / "descriptor.proto"
    stale_include_descriptor.parent.mkdir(parents=True)
    stale_include_descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    plugin = _write_version_only_plugin(
        source_dir / "tools" / "protoc-gen-protocyte", __version__
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(stale_protobuf_sources LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{first_protoc.as_posix()}")',
                f'set(protobuf_SOURCE_DIR "{stale_source.as_posix()}")',
                f'set(Protobuf_INCLUDE_DIRS "{stale_include.as_posix()}")',
                "protocyte_setup_codegen()",
                "add_subdirectory(child)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (child_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                f'set(Protobuf_PROTOC_EXECUTABLE "{second_protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET child_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS demo.proto",
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

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "selected a different protoc toolchain" in output
    assert "Set PROTOCYTE_PROTOBUF_IMPORT_DIR or IMPORT_DIRS explicitly" in output
    assert (source_dir / "toolchain-a" / "include").as_posix() in output
    assert stale_source.as_posix() not in output
    assert stale_include.as_posix() not in output


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


def test_source_codegen_normalizes_equivalent_proto_paths_before_deduplication(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    (proto_dir / "nested").mkdir(parents=True)
    proto_file = proto_dir / "demo.proto"
    proto_file.write_text(
        'syntax = "proto3"; package demo; message Demo {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(normalized_source_paths LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/demo.proto proto/nested/../demo.proto",
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

    assert (build_dir / "generated" / "demo.protocyte.hpp").is_file()
    response_texts = [
        path.read_text(encoding="utf-8")
        for path in (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
    ]
    generation_responses = [
        text
        for text in response_texts
        if "--plugin=protoc-gen-protocyte=" in text
    ]
    dependency_responses = [
        text for text in response_texts if "--include_imports" in text
    ]
    normalized_proto = proto_file.resolve().as_posix()
    assert len(generation_responses) == 1
    assert generation_responses[0].splitlines().count(normalized_proto) == 1
    assert len(dependency_responses) == 1
    assert dependency_responses[0].splitlines().count(normalized_proto) == 1
    assert "/nested/../" not in "\n".join(response_texts).replace("\\", "/")


@pytest.mark.parametrize(
    "generator",
    [
        pytest.param(None, id="default-generator"),
        pytest.param("Ninja", id="ninja"),
    ],
)
def test_source_codegen_preserves_semicolon_proto_path_end_to_end(
    tmp_path: Path,
    generator: str | None,
) -> None:
    if generator == "Ninja" and shutil.which("ninja") is None:
        pytest.skip("Ninja is required for the Ninja semicolon-path regression")
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    proto_file = proto_dir / "demo;legacy.proto"
    proto_file.write_text(
        'syntax = "proto3"; package demo; message Legacy {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(semicolon_source_path LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS [==[proto/demo;legacy.proto]==]",
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
    first_build = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "MSB8064" not in first_build.stdout + first_build.stderr
    generated_header = build_dir / "generated" / "demo~3Blegacy.protocyte.hpp"
    assert generated_header.is_file()
    response_texts = [
        path.read_text(encoding="utf-8")
        for path in (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
    ]
    generation_responses = [
        text
        for text in response_texts
        if "--plugin=protoc-gen-protocyte=" in text
    ]
    dependency_responses = [
        text for text in response_texts if "--include_imports" in text
    ]
    normalized_proto = proto_file.resolve().as_posix()
    assert len(generation_responses) == 1
    assert generation_responses[0].splitlines().count(normalized_proto) == 1
    assert len(dependency_responses) == 1
    assert dependency_responses[0].splitlines().count(normalized_proto) == 1

    no_op_build = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
        capture_output=True,
        text=True,
    )
    no_op_output = no_op_build.stdout + no_op_build.stderr
    assert "Scanning protobuf imports" not in no_op_output
    assert "Generating generated/" not in no_op_output

    proto_file.write_text(
        'syntax = "proto3"; package demo; message LegacyUpdated {}\n',
        encoding="utf-8",
    )
    rebuilt = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
        capture_output=True,
        text=True,
    )
    rebuilt_output = rebuilt.stdout + rebuilt.stderr
    assert "Scanning protobuf imports" in rebuilt_output
    assert "Generating generated/" in rebuilt_output
    assert "LegacyUpdated" in generated_header.read_text(encoding="utf-8")

    final_no_op = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
        capture_output=True,
        text=True,
    )
    final_no_op_output = final_no_op.stdout + final_no_op.stderr
    assert "Scanning protobuf imports" not in final_no_op_output
    assert "Generating generated/" not in final_no_op_output


def test_ninja_reuses_semicolon_source_proxy_between_codegen_targets(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify shared semicolon source proxies"
        )
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    proto_file = proto_dir / "shared;legacy.proto"
    proto_file.write_text(
        'syntax = "proto3"; package demo; message Shared {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()

    generation_blocks: list[str] = []
    for target, output_directory in (
        ("first_codegen", "first-generated"),
        ("second_codegen", "second-generated"),
    ):
        generation_blocks.extend(
            [
                "protocyte_generate(",
                f"    TARGET {target}",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                f'    OUT_DIR "${{CMAKE_CURRENT_BINARY_DIR}}/{output_directory}"',
                "    PROTOS [==[proto/shared;legacy.proto]==]",
                "    OPTIONS format=off",
                ")",
            ]
        )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(shared_semicolon_source LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                *generation_blocks,
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
    )
    build_command = [
        "cmake",
        "--build",
        str(build_dir),
        "--target",
        "first_codegen",
        "second_codegen",
    ]
    subprocess.run(build_command, check=True)

    headers = [
        build_dir / output_directory / "shared~3Blegacy.protocyte.hpp"
        for output_directory in ("first-generated", "second-generated")
    ]
    assert all(header.is_file() for header in headers)
    proxy_dir = build_dir / "CMakeFiles" / "protocyte-source-dependencies"
    assert len(list(proxy_dir.glob("*.proto"))) == 1

    no_op = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    no_op_output = no_op.stdout + no_op.stderr
    assert "Scanning protobuf imports" not in no_op_output
    assert "Generating " not in no_op_output

    proto_file.write_text(
        'syntax = "proto3"; package demo; message SharedUpdated {}\n',
        encoding="utf-8",
    )
    latest_output = max(headers, key=lambda path: path.stat().st_mtime_ns)
    _touch_newer_than(proto_file, latest_output)
    rebuilt = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    rebuilt_output = rebuilt.stdout + rebuilt.stderr
    assert rebuilt_output.count("Scanning protobuf imports") == 2
    assert rebuilt_output.count("Generating ") == 2
    assert all(
        "SharedUpdated" in header.read_text(encoding="utf-8")
        for header in headers
    )

    final_no_op = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    final_no_op_output = final_no_op.stdout + final_no_op.stderr
    assert "Scanning protobuf imports" not in final_no_op_output
    assert "Generating " not in final_no_op_output


def test_source_codegen_accepts_in_root_dotdot_prefixed_filename(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "..hidden.proto").write_text(
        'syntax = "proto3"; package demo; message Hidden {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(dotdot_prefixed_source LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/..hidden.proto",
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

    assert (build_dir / "generated" / "..hidden.protocyte.hpp").is_file()


def test_generate_rejects_existing_source_outside_proto_root(tmp_path: Path) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        " ".join(
            [
                "protocyte_generate(",
                "TARGET demo_codegen",
                "PROTO_ROOT proto",
                "OUT_DIR generated",
                "PROTOS outside.proto",
                ")",
            ]
        ),
        files={
            "proto/inside.proto": 'syntax = "proto3"; message Inside {}\n',
            "outside.proto": 'syntax = "proto3"; message Outside {}\n',
        },
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "is outside PROTO_ROOT" in output


def test_proto_libraries_build_with_distinct_emitted_runtime_outputs(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required for emitted runtime ownership build coverage")

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    for name in ("first", "second", "separate"):
        (proto_dir / f"{name}.proto").write_text(
            f'syntax = "proto3"; package demo; message {name.title()} {{}}\n',
            encoding="utf-8",
        )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(distinct_runtime_outputs LANGUAGES CXX)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                "add_library(protocyte_codegen INTERFACE)",
                "add_library(protocyte::codegen ALIAS protocyte_codegen)",
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_add_proto_library(",
                "    TARGET first_library",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/shared"',
                "    PROTOS proto/first.proto",
                "    EMIT_RUNTIME",
                "    RUNTIME_PREFIX runtime/first",
                "    OPTIONS format=off",
                ")",
                "protocyte_add_proto_library(",
                "    TARGET second_library",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/shared"',
                "    PROTOS proto/second.proto",
                "    EMIT_RUNTIME",
                "    RUNTIME_PREFIX runtime/second",
                "    OPTIONS format=off",
                ")",
                "protocyte_add_proto_library(",
                "    TARGET separate_library",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/separate"',
                "    PROTOS proto/separate.proto",
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
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            "first_library",
            "second_library",
            "separate_library",
        ],
        check=True,
    )

    assert (build_dir / "shared" / "runtime" / "first" / "runtime.hpp").is_file()
    assert (build_dir / "shared" / "runtime" / "second" / "runtime.hpp").is_file()
    assert (
        build_dir / "separate" / "protocyte" / "runtime" / "runtime.hpp"
    ).is_file()


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

    no_change = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    assert "no work to do" in no_change.stdout.lower()


def test_source_codegen_tracks_special_character_paths_incrementally(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify an incremental build"
        )

    source_dir = tmp_path / "source space #$"
    build_dir = tmp_path / "build space #$"
    proto_dir = source_dir / "proto space #$"
    import_dir = source_dir / "imports space #$"
    proto_dir.mkdir(parents=True)
    import_dir.mkdir()

    imported_proto = import_dir / "base value #$.proto"

    def write_imported(capacity: int) -> None:
        imported_proto.write_text(
            "\n".join(
                [
                    'syntax = "proto3";',
                    "package demo;",
                    'import "protocyte/options.proto";',
                    "option (protocyte.package_constant) = "
                    f'{{ name: "CAPACITY" u32: {capacity} }};',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    write_imported(2)
    source_proto = proto_dir / "consumer #$.proto"
    source_proto.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "base value #$.proto";',
                'import "protocyte/options.proto";',
                "option (protocyte.package_constant) = "
                '{ name: "DERIVED" u32_expr: "demo.CAPACITY + 1" };',
                "message Consumer {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    plugin = _installed_protocyte_plugin()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(special_path_incremental LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto space #$"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS [==[proto space #$/consumer #$.proto]==]",
                '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports space #$"',
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

    generated_header = (
        build_dir / "generated" / f"{generated_file_base('consumer #$.proto')}.hpp"
    )
    assert "DERIVED {3u}" in generated_header.read_text(encoding="utf-8")
    no_change = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    assert "no work to do" in no_change.stdout.lower()

    write_imported(7)
    subprocess.run(build_command, check=True)
    assert "DERIVED {8u}" in generated_header.read_text(encoding="utf-8")

    no_change = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    assert "no work to do" in no_change.stdout.lower()


def test_source_discover_removes_only_outputs_owned_by_a_renamed_proto(
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
    proto_dir.mkdir(parents=True)
    old_proto = proto_dir / "old.proto"
    old_proto.write_text(
        'syntax = "proto3"; package demo; message Old {}\n',
        encoding="utf-8",
    )
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(source_discover_cleanup LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
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

    generated_dir = build_dir / "generated"
    old_header = generated_dir / "old.protocyte.hpp"
    old_source = generated_dir / "old.protocyte.cpp"
    unrelated = generated_dir / "consumer-owned.protocyte.hpp"
    unrelated.write_text("keep\n", encoding="utf-8")
    assert old_header.is_file()
    assert old_source.is_file()

    new_proto = old_proto.with_name("new.proto")
    old_proto.rename(new_proto)
    new_proto.write_text(
        'syntax = "proto3"; package demo; message New {}\n',
        encoding="utf-8",
    )
    subprocess.run(build_command, check=True)

    assert not old_header.exists()
    assert not old_source.exists()
    assert (generated_dir / "new.protocyte.hpp").is_file()
    assert (generated_dir / "new.protocyte.cpp").is_file()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_descriptor_discover_removes_only_outputs_owned_by_a_deleted_file(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify an incremental build"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"

    def write_descriptor_set(*file_names: str) -> None:
        file_set = descriptor_pb2.FileDescriptorSet()
        for index, file_name in enumerate(file_names):
            descriptor = file_set.file.add()
            descriptor.name = file_name
            descriptor.package = "demo"
            descriptor.syntax = "proto3"
            descriptor.message_type.add().name = f"Message{index}"
        descriptor_set.write_bytes(file_set.SerializeToString())

    write_descriptor_set("keep.proto", "removed.proto")
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_discover_cleanup LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    DISCOVER",
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

    generated_dir = build_dir / "generated"
    removed_header = generated_dir / "removed.protocyte.hpp"
    removed_source = generated_dir / "removed.protocyte.cpp"
    unrelated = generated_dir / "consumer-owned.protocyte.hpp"
    unrelated.write_text("keep\n", encoding="utf-8")
    assert removed_header.is_file()
    assert removed_source.is_file()

    write_descriptor_set("keep.proto")
    _touch_newer_than(descriptor_set, removed_header)
    subprocess.run(build_command, check=True)

    assert (generated_dir / "keep.protocyte.hpp").is_file()
    assert (generated_dir / "keep.protocyte.cpp").is_file()
    assert not removed_header.exists()
    assert not removed_source.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_owned_output_cleanup_preserves_files_transferred_between_targets(
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
    proto_dir.mkdir(parents=True)
    for proto_name in ("first.proto", "second.proto", "shared.proto"):
        message_name = proto_name.removesuffix(".proto").title()
        (proto_dir / proto_name).write_text(
            f'syntax = "proto3"; package demo; message {message_name} {{}}\n',
            encoding="utf-8",
        )
    plugin = _installed_protocyte_plugin()

    def write_project(first_proto: str, second_proto: str) -> None:
        (source_dir / "CMakeLists.txt").write_text(
            "\n".join(
                [
                    "cmake_minimum_required(VERSION 3.24)",
                    "project(output_ownership_transfer LANGUAGES NONE)",
                    f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                    f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                    f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                    f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                    "protocyte_generate(",
                    "    TARGET first_codegen",
                    '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                    '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                    f"    PROTOS proto/{first_proto}",
                    "    OPTIONS format=off",
                    ")",
                    "protocyte_generate(",
                    "    TARGET second_codegen",
                    '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                    '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                    f"    PROTOS proto/{second_proto}",
                    "    OPTIONS format=off",
                    ")",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    write_project("shared.proto", "second.proto")
    configure_command = [
        "cmake",
        "-G",
        "Ninja",
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
    ]
    subprocess.run(configure_command, check=True)
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            "first_codegen",
            "second_codegen",
        ],
        check=True,
    )
    shared_header = build_dir / "generated" / "shared.protocyte.hpp"
    assert shared_header.is_file()

    write_project("first.proto", "shared.proto")
    subprocess.run(configure_command, check=True)

    assert shared_header.is_file()
    assert not (build_dir / "generated" / "second.protocyte.hpp").exists()


def test_removed_source_codegen_target_cleans_only_unchanged_owned_outputs(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify removed-target output cleanup"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    first_dir = source_dir / "first"
    second_dir = source_dir / "second"
    first_proto_dir = first_dir / "proto"
    second_proto_dir = second_dir / "proto"
    first_proto_dir.mkdir(parents=True)
    second_proto_dir.mkdir(parents=True)
    (first_proto_dir / "removed.proto").write_text(
        'syntax = "proto3"; package demo; message Removed {}\n',
        encoding="utf-8",
    )
    (second_proto_dir / "kept.proto").write_text(
        'syntax = "proto3"; package demo; message Kept {}\n',
        encoding="utf-8",
    )
    plugin = _installed_protocyte_plugin()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(removed_source_target LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "add_subdirectory(first)",
                "add_subdirectory(second)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def write_codegen(directory: Path, target: str, proto_name: str) -> None:
        (directory / "CMakeLists.txt").write_text(
            "\n".join(
                [
                    "protocyte_generate(",
                    f"    TARGET {target}",
                    '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                    '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                    f"    PROTOS proto/{proto_name}",
                    "    OPTIONS format=off",
                    ")",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    write_codegen(first_dir, "removed_codegen", "removed.proto")
    write_codegen(second_dir, "kept_codegen", "kept.proto")
    configure_command = [
        "cmake",
        "-G",
        "Ninja",
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
    ]
    subprocess.run(configure_command, check=True)
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            "removed_codegen",
            "kept_codegen",
        ],
        check=True,
    )

    first_generated = build_dir / "first" / "generated"
    second_generated = build_dir / "second" / "generated"
    removed_header = first_generated / "removed.protocyte.hpp"
    removed_source = first_generated / "removed.protocyte.cpp"
    kept_header = second_generated / "kept.protocyte.hpp"
    unrelated = first_generated / "consumer-owned.protocyte.hpp"
    kept_contents = kept_header.read_bytes()
    removed_header.write_text("consumer modification\n", encoding="utf-8")
    unrelated.write_text("keep\n", encoding="utf-8")

    manifest_root = build_dir / "CMakeFiles" / "protocyte-owned-outputs"
    assert len(list(manifest_root.glob("*/*.sha256"))) == 4

    (first_dir / "CMakeLists.txt").write_text(
        "# The first code generation target was removed.\n",
        encoding="utf-8",
    )
    subprocess.run(configure_command, check=True)

    assert removed_header.read_text(encoding="utf-8") == "consumer modification\n"
    assert not removed_source.exists()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert kept_header.read_bytes() == kept_contents
    assert (second_generated / "kept.protocyte.cpp").is_file()
    assert len([path for path in manifest_root.iterdir() if path.is_dir()]) == 1

    (second_dir / "CMakeLists.txt").write_text(
        "# The final code generation target was removed.\n",
        encoding="utf-8",
    )
    subprocess.run(configure_command, check=True)

    assert not kept_header.exists()
    assert not (second_generated / "kept.protocyte.cpp").exists()
    assert removed_header.read_text(encoding="utf-8") == "consumer modification\n"
    assert not [path for path in manifest_root.iterdir() if path.is_dir()]


def test_renamed_descriptor_codegen_target_retires_its_obsolete_manifest(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify renamed-target output cleanup"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    plugin = _installed_protocyte_plugin()

    def write_descriptor_set(*file_names: str) -> None:
        file_set = descriptor_pb2.FileDescriptorSet()
        for index, file_name in enumerate(file_names):
            descriptor = file_set.file.add()
            descriptor.name = file_name
            descriptor.package = "demo"
            descriptor.syntax = "proto3"
            descriptor.message_type.add().name = f"Message{index}"
        descriptor_set.write_bytes(file_set.SerializeToString())

    def write_project(target: str) -> None:
        (source_dir / "CMakeLists.txt").write_text(
            "\n".join(
                [
                    "cmake_minimum_required(VERSION 3.24)",
                    "project(renamed_descriptor_target LANGUAGES NONE)",
                    f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                    f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                    f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                    "protocyte_generate(",
                    f"    TARGET {target}",
                    f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                    '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                    "    DISCOVER",
                    "    OPTIONS format=off",
                    ")",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    write_descriptor_set("shared.proto", "removed.proto")
    write_project("old_codegen")
    configure_command = [
        "cmake",
        "-G",
        "Ninja",
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
    ]
    subprocess.run(configure_command, check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "old_codegen"],
        check=True,
    )

    generated_dir = build_dir / "generated"
    shared_header = generated_dir / "shared.protocyte.hpp"
    shared_contents = shared_header.read_bytes()
    unrelated = generated_dir / "consumer-owned.protocyte.hpp"
    unrelated.write_text("keep\n", encoding="utf-8")

    write_descriptor_set("shared.proto", "added.proto")
    write_project("new_codegen")
    subprocess.run(configure_command, check=True)

    assert shared_header.read_bytes() == shared_contents
    assert not (generated_dir / "removed.protocyte.hpp").exists()
    assert not (generated_dir / "removed.protocyte.cpp").exists()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    manifest_root = build_dir / "CMakeFiles" / "protocyte-owned-outputs"
    assert len([path for path in manifest_root.iterdir() if path.is_dir()]) == 1

    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "new_codegen"],
        check=True,
    )
    assert (generated_dir / "added.protocyte.hpp").is_file()
    assert (generated_dir / "added.protocyte.cpp").is_file()


def test_multiconfig_codegen_serializes_shared_outputs_between_build_processes(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    if shutil.which("ninja") is None:
        _multiconfig_locking_requirement_unavailable(
            "Ninja is required to verify concurrent multi-config builds"
        )
    cmake_help = subprocess.run(
        ["cmake", "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if "Ninja Multi-Config" not in cmake_help:
        _multiconfig_locking_requirement_unavailable(
            "CMake does not provide the Ninja Multi-Config generator"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    state_dir = source_dir / "protoc-state"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package demo; message Demo { string value = 1; }\n',
        encoding="utf-8",
    )
    protoc = _write_overlap_detecting_protoc_wrapper(
        tools_dir / "protoc", real_protoc, state_dir
    )
    plugin = _write_python_plugin_wrapper(
        tools_dir / "protoc-gen-protocyte", repo_root
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(multiconfig_codegen_locking LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
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
        [
            "cmake",
            "-G",
            "Ninja Multi-Config",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
        ],
        check=True,
    )

    runner = _write_synchronized_build_runner(source_dir / "build_runner.py")
    gate = source_dir / "start-builds"
    processes: list[subprocess.Popen[str]] = []
    for config in ("Debug", "Release"):
        ready = source_dir / f"{config}.ready"
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    str(runner),
                    str(ready),
                    str(gate),
                    "cmake",
                    "--build",
                    str(build_dir),
                    "--config",
                    config,
                    "--target",
                    "demo_codegen",
                    "--parallel",
                    "1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    ready_paths = [source_dir / "Debug.ready", source_dir / "Release.ready"]
    deadline = time.monotonic() + 30.0
    while not all(path.is_file() for path in ready_paths):
        if any(process.poll() is not None for process in processes):
            pytest.fail("a synchronized build runner exited before reaching the gate")
        if time.monotonic() >= deadline:
            pytest.fail("timed out waiting for the synchronized build runners")
        time.sleep(0.01)
    gate.write_text("start\n", encoding="utf-8")

    build_outputs: list[str] = []
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=120)
            build_outputs.append(stdout + stderr)
            assert process.returncode == 0, stdout + stderr
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    assert not list(state_dir.glob("overlap-*")), "\n".join(build_outputs)
    assert len(list(state_dir.glob("attempt-dependency-*"))) == 2
    assert len(list(state_dir.glob("complete-dependency-*"))) == 2
    assert len(list(state_dir.glob("attempt-generation-*"))) == 2
    assert len(list(state_dir.glob("complete-generation-*"))) == 2
    assert not list(state_dir.glob("active-*"))

    dependency_descriptors = list(
        (build_dir / "CMakeFiles" / "protocyte-dependencies").glob("*.pb")
    )
    assert len(dependency_descriptors) == 1
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(dependency_descriptors[0].read_bytes())
    assert [descriptor.name for descriptor in descriptor_set.file] == ["demo.proto"]
    ninja_dependencies = subprocess.run(
        ["ninja", "-C", str(build_dir), "-t", "deps"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "demo.proto" in ninja_dependencies

    generated_header = build_dir / "generated" / "demo.protocyte.hpp"
    generated_source = build_dir / "generated" / "demo.protocyte.cpp"
    assert "struct Demo" in generated_header.read_text(encoding="utf-8")
    assert '"demo.protocyte.hpp"' in generated_source.read_text(encoding="utf-8")


def test_generation_lock_wrapper_preserves_protoc_failure_diagnostics(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if os.name == "nt":
        failing_protoc = tmp_path / "failing-protoc.cmd"
        failing_protoc.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    "echo captured generation output",
                    "echo captured generation error 1>&2",
                    "exit /b 23",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    else:
        failing_protoc = tmp_path / "failing-protoc"
        failing_protoc.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env sh",
                    "echo 'captured generation output'",
                    "echo 'captured generation error' >&2",
                    "exit 23",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        failing_protoc.chmod(0o755)

    argument_file = tmp_path / "arguments.rsp"
    argument_file.write_text("", encoding="utf-8")
    lock_manifest = tmp_path / "locks.list"
    lock_manifest.write_text(f"{'0' * 64}\n", encoding="utf-8")
    result = subprocess.run(
        [
            "cmake",
            f"-DPROTOC_EXECUTABLE={failing_protoc}",
            f"-DARGUMENT_FILE={argument_file}",
            "-DGENERATION_TARGET=failing_codegen",
            f"-DGENERATION_WORKING_DIRECTORY={tmp_path}",
            f"-DLOCK_DIRECTORY={tmp_path / 'locks'}",
            f"-DLOCK_MANIFEST={lock_manifest}",
            "-DSOURCE_DIRECTORY_HEX=00",
            "-P",
            str(repo_root / "cmake" / "ProtocyteGenerate.cmake"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Failed to generate Protocyte sources for target 'failing_codegen'" in output
    assert "Exit code: 23" in output
    assert "captured generation output" in output
    assert "captured generation error" in output


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
    protobuf_import = _find_protobuf_import_dir(repo_root, protoc)
    plugin = _installed_protocyte_plugin()
    if shutil.which("ninja") is None:
        _windows_transport_requirement_unavailable(
            "Ninja is required for source response-file integration coverage"
        )
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
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"], check=True
    )

    assert (build_dir / "generated" / "caf~C3~A9.protocyte.hpp").is_file()
    assert (build_dir / "generated" / "caf~C3~A9.protocyte.cpp").is_file()
    response_files = list(
        (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
    )
    assert any(
        f"{(proto_dir / 'café.proto').as_posix()}\n"
        in response.read_text(encoding="utf-8")
        and "--include_imports\n" in response.read_text(encoding="utf-8")
        and "--dependency_out=" not in response.read_text(encoding="utf-8")
        for response in response_files
    )


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


@pytest.mark.parametrize("selection_mode", ["discover", "explicit"])
def test_descriptor_set_rejects_protoc_option_name_without_mutating_files(
    tmp_path: Path,
    selection_mode: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    escaped_dir = tmp_path / "escaped"
    source_dir.mkdir()
    escaped_dir.mkdir()
    victim = escaped_dir / "victim.proto"
    victim.write_text("sentinel\n", encoding="utf-8")
    injected_name = f"--descriptor_set_out={victim.as_posix()}"

    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    injected = file_set.file.add()
    injected.name = injected_name
    injected.syntax = "proto3"
    injected.message_type.add().name = "Injected"
    api = file_set.file.add()
    api.name = "api.proto"
    api.syntax = "proto3"
    api.message_type.add().name = "Api"
    descriptor_set.write_bytes(file_set.SerializeToString())

    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    selection = (
        "    DISCOVER"
        if selection_mode == "discover"
        else f"    PROTOS [==[{injected_name}]==] api.proto"
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_option_injection LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET generated",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                selection,
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "descriptor file name must not begin with '-'" in (
        result.stdout + result.stderr
    )
    assert victim.read_text(encoding="utf-8") == "sentinel\n"
    assert not (build_dir / "generated").exists()


def test_descriptor_set_rejects_casefolded_generated_output_collision(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    for name, message_name in (
        ("api/demo.proto", "LowerDemo"),
        ("API/DEMO.proto", "UpperDemo"),
    ):
        file = file_set.file.add()
        file.name = name
        file.syntax = "proto3"
        file.message_type.add().name = message_name
    descriptor_set.write_bytes(file_set.SerializeToString())

    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_output_collision LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET generated",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS api/demo.proto API/DEMO.proto",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "generated file name collision" in output
    assert "api/demo.proto" in output
    assert "API/DEMO.proto" in output


def test_source_codegen_rejects_casefolded_generated_output_collision(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    lower_proto = source_dir / "api" / "demo.proto"
    lower_proto.parent.mkdir(parents=True)
    lower_proto.write_text(
        'syntax = "proto3"; package lower; message Demo {}\n', encoding="utf-8"
    )
    if os.name != "nt":
        upper_proto = source_dir / "API" / "DEMO.proto"
        upper_proto.parent.mkdir(parents=True)
        upper_proto.write_text(
            'syntax = "proto3"; package upper; message Demo {}\n', encoding="utf-8"
        )

    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(source_output_collision LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET generated",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS api/demo.proto API/DEMO.proto",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "generated file name collision" in output
    assert "api/demo.proto" in output
    assert "API/DEMO.proto" in output


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
                "arguments = []",
                "for argument in sys.argv[1:]:",
                "    if argument.startswith('@'):",
                "        arguments.extend(Path(argument[1:]).read_text(encoding='utf-8').splitlines())",
                "    else:",
                "        arguments.append(argument)",
                f"Path({str(args_path)!r}).parent.mkdir(parents=True, exist_ok=True)",
                f"Path({str(args_path)!r}).write_text('\\n'.join(arguments), encoding='utf-8')",
                "out_dir = None",
                "for arg in arguments:",
                "    if arg.startswith('--protocyte_out='):",
                "        out_value = arg.split('=', 1)[1]",
                "        if out_value.startswith('_protocyte_options_hex='):",
                "            out_value = out_value.split(':', 1)[1]",
                "        out_dir = Path(out_value)",
                "if out_dir is None:",
                "    raise SystemExit('missing --protocyte_out')",
                "for name in arguments:",
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
                "    FILES nested/demo.proto nested/other.proto",
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
                'if(NOT generated_headers MATCHES "nested/other[.]protocyte[.]hpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper dropped a generated header")',
                "endif()",
                'if(NOT generated_sources MATCHES "nested/demo[.]protocyte[.]cpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper did not propagate generated sources")',
                "endif()",
                'if(NOT generated_sources MATCHES "nested/other[.]protocyte[.]cpp")',
                '    message(FATAL_ERROR "descriptor-set wrapper dropped a generated source")',
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
    ("descriptor_name", "message_name", "generator", "selection"),
    [
        pytest.param(
            "api/demo;legacy.proto",
            "SemicolonName",
            None,
            "DISCOVER",
            id="semicolon-discover",
        ),
        pytest.param(
            "api/demo;legacy.proto",
            "SemicolonName",
            None,
            'FILES "api/demo;legacy.proto"',
            id="semicolon-files",
        ),
        pytest.param(
            "é" * 50 + "/unicode.proto",
            "LongUnicodePath",
            "Ninja",
            "DISCOVER",
            id="long-unicode-discover",
        ),
        pytest.param(
            "x" * 255 + "/portable.proto",
            "LongPortablePath",
            None,
            "DISCOVER",
            id="msbuild-long-directory",
        ),
    ],
)
def test_descriptor_set_library_builds_portable_descriptor_name(
    tmp_path: Path,
    descriptor_name: str,
    message_name: str,
    generator: str | None,
    selection: str,
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
                f"    {selection}",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_environment = os.environ.copy()
    configure_environment.pop("CMAKE_GENERATOR", None)
    configure_command = ["cmake", "-S", str(source_dir), "-B", str(build_dir)]
    if generator is not None:
        configure_command.extend(["-G", generator])
    subprocess.run(configure_command, check=True, env=configure_environment)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "portable_proto"],
        check=True,
    )

    generated_dir = build_dir / "portable_proto_protocyte"
    path_budget = None
    directory_budget = None
    cache = (build_dir / "CMakeCache.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    uses_visual_studio = "CMAKE_GENERATOR:INTERNAL=Visual Studio " in cache
    if os.name == "nt" and generator is None:
        assert uses_visual_studio
    if uses_visual_studio:
        path_budget = min(255, 259 - len(str(generated_dir.resolve())) - 1)
        directory_budget = 247 - len(str(generated_dir.resolve())) - 1
    generated_base = generated_file_base(
        descriptor_name,
        max_output_path_bytes=path_budget,
        max_output_directory_bytes=directory_budget,
    )
    generated_header = generated_dir / f"{generated_base}.hpp"
    generated_source = generated_dir / f"{generated_base}.cpp"
    assert generated_header.is_file()
    assert generated_source.is_file()
    if ";" in descriptor_name:
        assert generated_base == "api/demo~3Blegacy.protocyte"
    elif uses_visual_studio:
        assert len(str(generated_header.resolve())) < 260
        assert len(str(generated_header.resolve().parent)) < 248
        assert "/" not in generated_base
    else:
        long_generated_directory = generated_base.split("/", 1)[0]
        assert len(long_generated_directory.encode("ascii")) == 255


@pytest.mark.skipif(os.name != "nt", reason="Windows protoc argv encoding regression")
def test_prebuilt_windows_protoc_receives_utf8_descriptor_arguments(
    tmp_path: Path,
) -> None:
    configured_protoc = os.environ.get(_CI_PROTOC_ENV)
    if not configured_protoc:
        _windows_transport_requirement_unavailable(
            f"{_CI_PROTOC_ENV} is not configured with the prebuilt protoc"
        )
    if shutil.which("ninja") is None:
        _windows_transport_requirement_unavailable(
            "Ninja is required for Windows response-file integration coverage"
        )

    repo_root = Path(__file__).resolve().parents[1]
    protoc = Path(configured_protoc).resolve()
    version = subprocess.run(
        [str(protoc), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert version.startswith("libprotoc ")

    source_dir = tmp_path / "café source"
    build_dir = tmp_path / "bûild output"
    tools_dir = source_dir / "plugin café"
    tools_dir.mkdir(parents=True)
    plugin = tools_dir / "protoc-gen-protocyte.exe"
    shutil.copy2(_installed_protocyte_plugin(), plugin)

    descriptor_names = [
        "api/café name.proto",
        "api/semi;colon.proto",
        'api/literal"quote.proto',
    ]
    descriptor_set = source_dir / "descriptor sét.pb"
    file_set = descriptor_pb2.FileDescriptorSet()
    for index, descriptor_name in enumerate(descriptor_names):
        descriptor = file_set.file.add()
        descriptor.name = descriptor_name
        descriptor.package = "demo"
        descriptor.syntax = "proto3"
        descriptor.message_type.add().name = f"Message{index}"
    descriptor_set.write_bytes(file_set.SerializeToString())

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(windows_utf8_protoc_transport LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET utf8_discover_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated discover café"',
                "    DISCOVER",
                "    OPTIONS format=off",
                ")",
                "protocyte_generate(",
                "    TARGET utf8_explicit_codegen",
                f'    DESCRIPTOR_SET "{descriptor_set.as_posix()}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated explicit café"',
                "    PROTOS",
                *(f"        [==[{name}]==]" for name in descriptor_names),
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
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--target",
            "utf8_discover_codegen",
            "utf8_explicit_codegen",
        ],
        check=True,
    )

    for generated_dir in (
        build_dir / "generated discover café",
        build_dir / "generated explicit café",
    ):
        for descriptor_name in descriptor_names:
            generated_base = generated_file_base(descriptor_name)
            assert (generated_dir / f"{generated_base}.hpp").is_file()
            assert (generated_dir / f"{generated_base}.cpp").is_file()

    response_files = list(
        (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
    )
    generation_responses = [
        response.read_text(encoding="utf-8")
        for response in response_files
        if "--protocyte_out=" in response.read_text(encoding="utf-8")
    ]
    assert len(generation_responses) == 2
    for generation_response in generation_responses:
        response_lines = generation_response.splitlines()
        assert f"--descriptor_set_in={descriptor_set.as_posix()}" in response_lines
        assert f"--plugin=protoc-gen-protocyte={plugin.as_posix()}" in response_lines
        assert sorted(descriptor_names) == sorted(
            response_lines[-len(descriptor_names) :]
        )


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


def test_shared_managed_environment_serializes_concurrent_configures(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "shared-environments"
    barrier_dir = tmp_path / "barrier"
    source_a = tmp_path / "project-a"
    source_b = tmp_path / "project-b"
    build_a = _write_managed_environment_consumer(
        source_a,
        environment_root,
        barrier_marker=barrier_dir / "a",
        peer_marker=barrier_dir / "b",
    )
    build_b = _write_managed_environment_consumer(
        source_b,
        environment_root,
        barrier_marker=barrier_dir / "b",
        peer_marker=barrier_dir / "a",
    )

    processes = [
        subprocess.Popen(
            ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for source_dir, build_dir in ((source_a, build_a), (source_b, build_b))
    ]
    completed: list[tuple[int, str]] = []
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=900)
            completed.append((process.returncode, stdout + stderr))
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    assert all(returncode == 0 for returncode, _output in completed), "\n\n".join(
        output for _returncode, output in completed
    )
    assert (
        sum(
            output.count("Provisioning Protocyte Python environment:")
            for _returncode, output in completed
        )
        == 1
    )

    environment = _published_managed_environment(environment_root)
    assert (environment_root / f".{environment.name}.lock").is_file()
    _python, plugin = _managed_environment_executables(environment)
    assert plugin.is_file()
    assert subprocess.run(
        [str(plugin), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == __version__
    assert Path((build_a / "managed-plugin.txt").read_text(encoding="utf-8")) == plugin
    assert Path((build_b / "managed-plugin.txt").read_text(encoding="utf-8")) == plugin
    _assert_no_managed_environment_transaction_leftovers(environment_root)


def test_managed_environment_reuses_valid_install_and_repairs_mutated_version(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "managed-environments"
    source_dir = tmp_path / "project"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)

    initial = _configure_managed_environment(source_dir, build_dir)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    assert "Provisioning Protocyte Python environment:" in initial.stdout + initial.stderr

    environment = _published_managed_environment(environment_root)
    ready_marker = environment / ".protocyte-ready"
    ready_contents = ready_marker.read_text(encoding="utf-8")
    ready_mtime_ns = ready_marker.stat().st_mtime_ns
    incremental = _configure_managed_environment(source_dir, build_dir)
    assert incremental.returncode == 0, incremental.stdout + incremental.stderr
    assert "Provisioning Protocyte Python environment:" not in (
        incremental.stdout + incremental.stderr
    )
    assert ready_marker.stat().st_mtime_ns == ready_mtime_ns

    python, plugin = _managed_environment_executables(environment)
    package_init = Path(
        subprocess.run(
            [
                str(python),
                "-c",
                "from pathlib import Path; import protocyte; print(Path(protocyte.__file__).resolve())",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    original_package_init = package_init.read_text(encoding="utf-8")
    expected_literal = f'__version__ = "{__version__}"'
    assert expected_literal in original_package_init
    package_init.write_text(
        original_package_init.replace(expected_literal, '__version__ = "99.0.0"'),
        encoding="utf-8",
    )
    shutil.rmtree(package_init.parent / "__pycache__", ignore_errors=True)
    assert subprocess.run(
        [str(plugin), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "99.0.0"

    empty_pip_cache = tmp_path / "empty-pip-cache"
    empty_pip_cache.mkdir()
    offline_env = os.environ.copy()
    offline_env.update(
        PIP_CACHE_DIR=str(empty_pip_cache),
        PIP_CONFIG_FILE=os.devnull,
        PIP_NO_INDEX="1",
    )
    failed_repair = _configure_managed_environment(
        source_dir,
        build_dir,
        env=offline_env,
    )
    assert failed_repair.returncode != 0
    assert "Failed to install Protocyte's pinned Python build tools" in (
        failed_repair.stdout + failed_repair.stderr
    )
    assert ready_marker.read_text(encoding="utf-8") == ready_contents
    assert package_init.read_text(encoding="utf-8").count("99.0.0") == 1
    assert subprocess.run(
        [str(plugin), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "99.0.0"
    _assert_no_managed_environment_transaction_leftovers(environment_root)

    repaired = _configure_managed_environment(source_dir, build_dir)
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert "Provisioning Protocyte Python environment:" in repaired.stdout + repaired.stderr
    repaired_environment = _published_managed_environment(environment_root)
    assert repaired_environment == environment
    _repaired_python, repaired_plugin = _managed_environment_executables(
        repaired_environment
    )
    assert subprocess.run(
        [str(repaired_plugin), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == __version__
    _assert_no_managed_environment_transaction_leftovers(environment_root)


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

    version_block = version_block.split("\n        )", maxsplit=1)[0]

    assert "COMPATIBILITY ExactVersion" in version_block
    assert "COMPATIBILITY SameMajorVersion" not in version_block
    assert "ARCH_INDEPENDENT" in version_block


def test_release_cmake_version_file_accepts_pointer_size_mismatch(
    tmp_path: Path,
) -> None:
    cmake_lists = (Path(__file__).resolve().parents[1] / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )
    version_block = cmake_lists.split("write_basic_package_version_file(", maxsplit=1)[
        1
    ].split("\n    )", maxsplit=1)[0]
    version_block = version_block.split("\n        )", maxsplit=1)[0]
    generate_script = tmp_path / "generate-version.cmake"
    generate_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "include(CMakePackageConfigHelpers)",
                'set(PROJECT_VERSION "0.1.0")',
                'set(CMAKE_SIZEOF_VOID_P "8")',
                'file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/cmake")',
                f"write_basic_package_version_file({version_block}",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(
        ["cmake", "-P", str(generate_script)],
        cwd=tmp_path,
        check=True,
    )

    generated_version = tmp_path / "cmake" / "protocyteConfigVersion.cmake"
    assert generated_version.is_file()
    probe_script = tmp_path / "probe-version.cmake"
    probe_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                'set(CMAKE_SIZEOF_VOID_P "4")',
                'set(PACKAGE_FIND_VERSION "0.1.0")',
                f'include("{generated_version.as_posix()}")',
                "if(PACKAGE_VERSION_UNSUITABLE)",
                '    message(FATAL_ERROR "architecture-independent package was rejected")',
                "endif()",
                "if(NOT PACKAGE_VERSION_COMPATIBLE OR NOT PACKAGE_VERSION_EXACT)",
                '    message(FATAL_ERROR "exact package version did not match")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(["cmake", "-P", str(probe_script)], check=True)
