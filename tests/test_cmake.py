from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from pathlib import Path
from typing import Never

import pytest
from google.protobuf import descriptor_pb2

from protocyte import __version__
from protocyte.import_scanner import (
    UNSAFE_VIRTUAL_IMPORT_PATH_ERROR,
    UnsafeVirtualImportPathError,
    _scan_source_closure,
    source_closure_requires_protobuf_imports,
)
from protocyte.paths import (
    MIN_HASHED_GENERATED_FILE_PATH_BYTES,
    generated_file_base,
)


_CI_PROTOC_ENV = "PROTOCYTE_CI_PROTOC_EXECUTABLE"
_CI_REQUIRE_REAL_PROTOC_TEST_ENV = "PROTOCYTE_CI_REQUIRE_REAL_PROTOC_TESTS"
_CI_REQUIRE_INCREMENTAL_TEST_ENV = "PROTOCYTE_CI_REQUIRE_INCREMENTAL_TEST"
_CI_REQUIRE_INSTALL_EXPORT_TEST_ENV = "PROTOCYTE_CI_REQUIRE_INSTALL_EXPORT_TEST"
_CI_REQUIRE_MULTICONFIG_LOCKING_TEST_ENV = (
    "PROTOCYTE_CI_REQUIRE_MULTICONFIG_LOCKING_TEST"
)
_CI_REQUIRE_WINDOWS_TRANSPORT_TEST_ENV = "PROTOCYTE_CI_REQUIRE_WINDOWS_TRANSPORT_TEST"
_CI_REQUIRE_WINDOWS_SHARED_REFLECTION_TEST_ENV = (
    "PROTOCYTE_CI_REQUIRE_WINDOWS_SHARED_REFLECTION_TEST"
)
_CI_REQUIRE_VISUAL_STUDIO_TEST_ENV = "PROTOCYTE_CI_REQUIRE_VISUAL_STUDIO_TEST"
_PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR = (
    'Backslashes, consecutive slashes, ".", or ".." are not allowed in the virtual path'
)


def _real_protoc_requirement_unavailable(
    message: str, *, additional_required_env: str | None = None
) -> Never:
    if (
        os.environ.get(_CI_REQUIRE_REAL_PROTOC_TEST_ENV) == "1"
        or os.environ.get(_CI_REQUIRE_INCREMENTAL_TEST_ENV) == "1"
        or (
            additional_required_env is not None
            and os.environ.get(additional_required_env) == "1"
        )
    ):
        pytest.fail(message)
    pytest.skip(message)


def _incremental_requirement_unavailable(
    message: str, *, additional_required_env: str | None = None
) -> Never:
    if os.environ.get(_CI_REQUIRE_INCREMENTAL_TEST_ENV) == "1" or (
        additional_required_env is not None
        and os.environ.get(additional_required_env) == "1"
    ):
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


def _windows_shared_reflection_requirement_unavailable(message: str) -> Never:
    if os.environ.get(_CI_REQUIRE_WINDOWS_SHARED_REFLECTION_TEST_ENV) == "1":
        pytest.fail(message)
    pytest.skip(message)


def _visual_studio_requirement_unavailable(message: str) -> Never:
    if os.environ.get(_CI_REQUIRE_VISUAL_STUDIO_TEST_ENV) == "1":
        pytest.fail(message)
    pytest.skip(message)


def _create_visual_studio_test_directory(parent: Path) -> Path:
    parent = parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    while True:
        test_directory = parent / f"protocyte-vs-incremental-{uuid.uuid4().hex}"
        try:
            test_directory.mkdir()
        except FileExistsError:
            continue
        return test_directory


def _create_configured_visual_studio_test_directory() -> Path:
    configured_test_root = os.environ.get("PROTOCYTE_CI_VISUAL_STUDIO_TEST_ROOT")
    if not configured_test_root:
        _visual_studio_requirement_unavailable(
            "PROTOCYTE_CI_VISUAL_STUDIO_TEST_ROOT is not configured outside "
            "the Windows temporary directory"
        )
    return _create_visual_studio_test_directory(Path(configured_test_root))


def _find_real_protoc(
    repo_root: Path, *, additional_required_env: str | None = None
) -> Path:
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

    _real_protoc_requirement_unavailable(
        "real protoc executable is not available",
        additional_required_env=additional_required_env,
    )


def _find_pinned_protoc_34_1(repo_root: Path) -> Path:
    protoc = _find_real_protoc(repo_root)
    version = subprocess.run(
        [str(protoc), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if version != "libprotoc 34.1":
        _real_protoc_requirement_unavailable(
            f"pinned protoc 34.1 is unavailable (found {version!r})"
        )
    return protoc


def _find_visual_studio_generator() -> str:
    if os.name != "nt":
        pytest.skip("Visual Studio generator coverage is Windows-only")

    cmake_help = subprocess.run(
        ["cmake", "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for line in cmake_help.splitlines():
        generator = line.split("=", maxsplit=1)[0].strip().removeprefix("* ").strip()
        if generator.startswith("Visual Studio "):
            return generator

    pytest.skip("CMake does not provide a Visual Studio generator")


def _find_protobuf_import_root(repo_root: Path) -> Path:
    for root in (repo_root / "build", repo_root / "tests"):
        for descriptor in root.glob(
            "**/protobuf-src/src/google/protobuf/descriptor.proto"
        ):
            return descriptor.parents[2]
    pytest.skip("protobuf source import tree is not available")


def _find_protobuf_import_dir(
    repo_root: Path,
    protoc: Path,
    *,
    additional_required_env: str | None = None,
) -> Path:
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

    _real_protoc_requirement_unavailable(
        "protobuf import directory is not available",
        additional_required_env=additional_required_env,
    )


def _configure_cmake_snippet(
    tmp_path: Path,
    snippet: str,
    *,
    files: dict[str, str] | None = None,
    timeout: float | None = None,
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
        timeout=timeout,
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
    (source_dir / "CMakeLists.txt").write_text("\n".join(cmake_lines), encoding="utf-8")

    result = subprocess.run(
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result, headers_output


def _write_python_plugin_wrapper(path: Path, repo_root: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _write_inherited_pythonpath_plugin_wrapper(
    path: Path,
    module_dir: Path,
    repo_root: Path,
    *,
    import_scan_log: Path | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    module_dir.mkdir(parents=True, exist_ok=True)
    module_lines = ["import sys"]
    if import_scan_log is not None:
        module_lines.extend(
            [
                "from pathlib import Path",
                'if sys.argv[1:2] == ["_cmake-import-scan-v1"]:',
                f"    with Path({str(import_scan_log)!r}).open('a', encoding='utf-8') as log:",
                '        log.write("invoked\\n")',
            ]
        )
    module_lines.extend(
        [
            f"sys.path.insert(0, {str(repo_root / 'src')!r})",
            "from protocyte.main import main",
            "raise SystemExit(main())",
            "",
        ]
    )
    (module_dir / "protocyte_external_plugin.py").write_text(
        "\n".join(module_lines),
        encoding="utf-8",
    )
    if os.name == "nt":
        wrapper = path.with_suffix(".cmd")
        wrapper.write_text(
            f'@echo off\r\n"{sys.executable}" -m protocyte_external_plugin %*\r\n',
            encoding="utf-8",
        )
    else:
        wrapper = path
        wrapper.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env sh",
                    f'exec {shlex.quote(sys.executable)} -m protocyte_external_plugin "$@"',
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


def _write_parallel_protoc_wrapper(
    path: Path, protoc: Path, invocation_directory: Path
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    invocation_directory.mkdir(parents=True, exist_ok=True)
    script = path.with_suffix(".py")
    script.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import subprocess",
                "import sys",
                "import uuid",
                "from pathlib import Path",
                "",
                f"REAL_PROTOC = Path({str(protoc)!r})",
                f"INVOCATION_DIRECTORY = Path({str(invocation_directory)!r})",
                "",
                '(INVOCATION_DIRECTORY / uuid.uuid4().hex).write_text("invoked\\n", encoding="utf-8")',
                "raise SystemExit(subprocess.call([str(REAL_PROTOC), *sys.argv[1:]]))",
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
                'if kind == "dependency" and (',
                '    STATE_DIR / "active-dependency-reader"',
                ").exists():",
                '    (STATE_DIR / f"overlap-{kind}-reader-{pid}").write_text(',
                '        "overlap\\n", encoding="utf-8"',
                "    )",
                '    sys.stderr.write("dependency protoc overlapped its descriptor reader\\n")',
                "    os.close(active_fd)",
                "    active.unlink(missing_ok=True)",
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


def _write_overlap_detecting_dependency_reader_wrapper(
    path: Path, reader: Path, state_dir: Path
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
                f"REAL_READER = Path({str(reader)!r})",
                f"STATE_DIR = Path({str(state_dir)!r})",
                "",
                "",
                'if sys.argv[1:3] != ["descriptor-set", "dependency-file"]:',
                "    raise SystemExit(",
                "        subprocess.run([str(REAL_READER), *sys.argv[1:]], check=False).returncode",
                "    )",
                "",
                "pid = os.getpid()",
                '(STATE_DIR / f"attempt-reader-{pid}").write_text(',
                '    "attempt\\n", encoding="utf-8"',
                ")",
                'active = STATE_DIR / "active-dependency-reader"',
                "try:",
                "    active_fd = os.open(",
                "        active, os.O_CREAT | os.O_EXCL | os.O_WRONLY",
                "    )",
                "except FileExistsError:",
                '    (STATE_DIR / f"overlap-reader-{pid}").write_text(',
                '        "overlap\\n", encoding="utf-8"',
                "    )",
                '    sys.stderr.write("overlapping dependency descriptor readers\\n")',
                "    raise SystemExit(91)",
                "",
                "try:",
                '    if (STATE_DIR / "active-dependency").exists():',
                '        (STATE_DIR / f"overlap-reader-writer-{pid}").write_text(',
                '            "overlap\\n", encoding="utf-8"',
                "        )",
                '        sys.stderr.write("dependency descriptor reader overlapped protoc\\n")',
                "        raise SystemExit(91)",
                "    time.sleep(1.0)",
                "    result = subprocess.run(",
                "        [str(REAL_READER), *sys.argv[1:]], check=False",
                "    )",
                "finally:",
                "    os.close(active_fd)",
                "    active.unlink(missing_ok=True)",
                "",
                '(STATE_DIR / f"complete-reader-{pid}").write_text(',
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


def _write_python_command_wrapper(path: Path, script: Path) -> Path:
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


def test_dependency_scan_serializes_descriptor_reader_with_writer(
    tmp_path: Path,
) -> None:
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("CMake is required for dependency-scan locking coverage")

    repo_root = Path(__file__).resolve().parents[1]
    scan_script = repo_root / "cmake" / "ProtocyteDependencyScan.cmake"
    working_directory = tmp_path / "working"
    tools_directory = tmp_path / "tools"
    state_directory = tmp_path / "state"
    working_directory.mkdir()
    tools_directory.mkdir()
    argument_file = working_directory / "arguments.rsp"
    descriptor = working_directory / "CMakeFiles" / "dependency.pb"
    depfile = working_directory / "CMakeFiles" / "dependency.d"
    argument_file.write_text(
        "--include_imports\n--descriptor_set_out=CMakeFiles/dependency.pb\n",
        encoding="utf-8",
    )

    fake_protoc_script = tools_directory / "fake-protoc.py"
    fake_protoc_script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "",
                "argument_file = Path(sys.argv[1].removeprefix('@'))",
                "if not argument_file.is_absolute():",
                "    argument_file = Path.cwd() / argument_file",
                "for line in argument_file.read_text(encoding='utf-8').splitlines():",
                "    if line.startswith('--descriptor_set_out='):",
                "        descriptor = Path(line.removeprefix('--descriptor_set_out='))",
                "        if not descriptor.is_absolute():",
                "            descriptor = Path.cwd() / descriptor",
                "        descriptor.parent.mkdir(parents=True, exist_ok=True)",
                "        descriptor.write_bytes(b'descriptor')",
                "        break",
                "else:",
                "    raise SystemExit('missing descriptor output')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    real_protoc = _write_python_command_wrapper(
        tools_directory / "real-protoc", fake_protoc_script
    )
    protoc = _write_overlap_detecting_protoc_wrapper(
        tools_directory / "protoc", real_protoc, state_directory
    )

    fake_reader_script = tools_directory / "fake-reader.py"
    fake_reader_script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "",
                "arguments = sys.argv[1:]",
                "assert arguments[:2] == ['descriptor-set', 'dependency-file']",
                "while arguments[2].startswith('--'):",
                "    arguments.pop(2)",
                "descriptor = Path(arguments[2])",
                "if not descriptor.is_absolute():",
                "    descriptor = Path.cwd() / descriptor",
                "assert descriptor.read_bytes() == b'descriptor'",
                "depfile = Path(arguments[4])",
                "if not depfile.is_absolute():",
                "    depfile = Path.cwd() / depfile",
                "depfile.parent.mkdir(parents=True, exist_ok=True)",
                "depfile.write_text('dependency.pb: input.proto\\n', encoding='utf-8')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    real_reader = _write_python_command_wrapper(
        tools_directory / "real-reader", fake_reader_script
    )
    reader = _write_overlap_detecting_dependency_reader_wrapper(
        tools_directory / "reader", real_reader, state_directory
    )

    runner = _write_synchronized_build_runner(tmp_path / "build_runner.py")
    gate = tmp_path / "start-scans"
    processes: list[subprocess.Popen[str]] = []
    for worker in range(2):
        ready = tmp_path / f"worker-{worker}.ready"
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    str(runner),
                    str(ready),
                    str(gate),
                    cmake,
                    f"-DPROTOC_EXECUTABLE={protoc}",
                    "-DARGUMENT_FILE=arguments.rsp",
                    f"-DLOCK_FILE={tmp_path / 'locks' / 'dependency.lock'}",
                    "-DPROTO_FILE=demo.proto",
                    f"-DSCAN_WORKING_DIRECTORY={working_directory}",
                    f"-DDEPENDENCY_READER={reader}",
                    "-DDEPENDENCY_DESCRIPTOR=CMakeFiles/dependency.pb",
                    "-DDEPENDENCY_DEPFILE=CMakeFiles/dependency.d",
                    "-DDEPENDENCY_DEPFILE_TARGET=CMakeFiles/dependency.pb",
                    "-DDEPENDENCY_FILE_FORMAT=--ninja",
                    "-P",
                    str(scan_script),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    ready_paths = [tmp_path / f"worker-{worker}.ready" for worker in range(2)]
    deadline = time.monotonic() + 30.0
    while not all(path.is_file() for path in ready_paths):
        if any(process.poll() is not None for process in processes):
            pytest.fail(
                "a synchronized dependency scan exited before reaching the gate"
            )
        if time.monotonic() >= deadline:
            pytest.fail("timed out waiting for synchronized dependency scans")
        time.sleep(0.01)
    gate.write_text("start\n", encoding="utf-8")

    outputs: list[str] = []
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=60)
            outputs.append(stdout + stderr)
            assert process.returncode == 0, stdout + stderr
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    assert not list(state_directory.glob("overlap-*")), "\n".join(outputs)
    assert len(list(state_directory.glob("attempt-dependency-*"))) == 2
    assert len(list(state_directory.glob("complete-dependency-*"))) == 2
    assert len(list(state_directory.glob("attempt-reader-*"))) == 2
    assert len(list(state_directory.glob("complete-reader-*"))) == 2
    assert not list(state_directory.glob("active-*"))
    assert descriptor.read_bytes() == b"descriptor"
    assert depfile.read_text(encoding="utf-8") == "dependency.pb: input.proto\n"


def _touch_newer_than(path: Path, output: Path) -> None:
    changed_mtime_ns = (
        max(path.stat().st_mtime_ns, output.stat().st_mtime_ns) + 2_000_000_000
    )
    os.utime(path, ns=(changed_mtime_ns, changed_mtime_ns))


def _owned_output_key(path: Path) -> str:
    identity = path.resolve().as_posix()
    if os.name == "nt":
        identity = identity.lower()
    return hashlib.sha256(identity.encode()).hexdigest()


def _write_legacy_owned_output_manifest(
    binary_dir: Path,
    target: str,
    output_root: Path,
    *outputs: Path,
) -> Path:
    target_identity = f"{binary_dir.resolve().as_posix()}|{target}"
    target_key = hashlib.sha256(target_identity.encode()).hexdigest()
    manifest_dir = binary_dir / "CMakeFiles" / "protocyte-owned-outputs" / target_key
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "output-root.path").write_text(
        output_root.resolve().as_posix(), encoding="utf-8"
    )
    for output in outputs:
        (manifest_dir / f"{_owned_output_key(output)}.path").write_text(
            output.resolve().as_posix(), encoding="utf-8"
        )
    return manifest_dir


def _write_protobuf_toolchain(root: Path) -> Path:
    protoc = root / "bin" / "protoc"
    protoc.parent.mkdir(parents=True)
    protoc.write_text("", encoding="utf-8")
    descriptor = root / "include" / "google" / "protobuf" / "descriptor.proto"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    return protoc


def _write_runnable_host_protoc(root: Path) -> Path:
    executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    protoc = root / "bin" / executable_name
    protoc.parent.mkdir(parents=True)
    cmake = shutil.which("cmake")
    assert cmake is not None
    shutil.copy2(cmake, protoc)
    descriptor = root / "include" / "google" / "protobuf" / "descriptor.proto"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    return protoc


def _write_target_protobuf_package(package_dir: Path, target_protoc: Path) -> None:
    package_dir.mkdir(parents=True)
    (package_dir / "ProtobufConfig.cmake").write_text(
        "\n".join(
            [
                "add_executable(protobuf::protoc IMPORTED)",
                "set_target_properties(",
                "    protobuf::protoc",
                "    PROPERTIES",
                f'        IMPORTED_LOCATION "{target_protoc.as_posix()}"',
                '        CROSSCOMPILING_EMULATOR "${CMAKE_COMMAND};-E;env"',
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )


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
            "_protocyte_get_internal(managed_root PYTHON_ENV_ROOT)",
            'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/managed-plugin.txt" "${managed_plugin}")',
            'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/managed-root.txt" "${PROTOCYTE_PYTHON_ENV_ROOT}\n${managed_root}\n")',
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
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
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
        if (
            candidate.name.endswith(".staging")
            or candidate.name.endswith(".previous")
            or ".protocyte-managed-environment-" in candidate.name
            or ".protocyte-cleanup-managed-environment-" in candidate.name
        )
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
    functions = (repo_root / "cmake" / "ProtocyteFunctions.cmake").read_text(
        encoding="utf-8"
    )
    import_topology = (repo_root / "cmake" / "ProtocyteImportTopology.cmake").read_text(
        encoding="utf-8"
    )
    process_launcher = (repo_root / "cmake" / "ProtocyteProcess.cmake").read_text(
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
    assert (
        'set(PROTOCYTE_IMPORT_SCANNER "${PROTOCYTE_PACKAGE_ROOT}/import_scanner.py")'
        in source_config
    )
    assert (
        'set_and_check(PROTOCYTE_IMPORT_SCANNER "${PROTOCYTE_PACKAGE_ROOT}/import_scanner.py")'
        in installed_config
    )
    assert "PROTOCYTE_INTERNAL_IMPORT_SCANNER" in source_config
    assert "PROTOCYTE_INTERNAL_IMPORT_SCANNER" in installed_config
    assert (
        'PROTOCYTE_INTERNAL_IMPORT_SCAN_COMMAND "_cmake-import-scan-v1"'
        in source_config
    )
    assert (
        'PROTOCYTE_INTERNAL_IMPORT_SCAN_COMMAND "_cmake-import-scan-v1"'
        in installed_config
    )
    assert "PROTOCYTE_INTERNAL_PYTHON_PROJECT_ROOT" in source_config
    assert "PROTOCYTE_INTERNAL_PYTHON_PROJECT_ROOT" in installed_config
    assert "PROTOCYTE_INTERNAL_PYTHON_CONSTRAINTS" in source_config
    assert "PROTOCYTE_INTERNAL_PYTHON_CONSTRAINTS" in installed_config
    assert "_protocyte_configure_python_environment_root()" in source_config
    assert "_protocyte_configure_python_environment_root()" in installed_config
    assert "PROTOCYTE_INTERNAL_PYTHON_ENV_ROOT" in functions
    assert "PROTOCYTE_INTERNAL_VERSION" in source_config
    assert "PROTOCYTE_INTERNAL_VERSION" in installed_config
    assert '"${PROTOCYTE_PYTHON_PROJECT_ROOT}/src"' in installed_config
    assert "_protocyte_execute_bounded(" in import_topology
    assert "PROTOCYTE_TOOL_TIMEOUT_SECONDS" in process_launcher
    assert '_PROTOCYTE_DEFAULT_TOOL_TIMEOUT_SECONDS "300"' in process_launcher


def test_tool_timeout_zero_explicitly_disables_cmake_process_limit(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = tmp_path / "disable-timeout.cmake"
    script.write_text(
        "\n".join(
            [
                f'include("{(repo_root / "cmake" / "ProtocyteProcess.cmake").as_posix()}")',
                "set(PROTOCYTE_TOOL_TIMEOUT_SECONDS 0)",
                "_protocyte_resolve_tool_timeout(timeout)",
                "_protocyte_execute_bounded(result output error timed_out",
                '    TIMEOUT_SECONDS "${timeout}"',
                '    COMMAND "${CMAKE_COMMAND}" -E sleep 0.2',
                ")",
                'if(NOT "${result}" STREQUAL "0" OR timed_out)',
                '    message(FATAL_ERROR "zero timeout did not disable the process limit")',
                "endif()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["cmake", "-P", str(script)], check=False, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stdout + result.stderr


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


def test_explicit_plugin_override_rejects_semicolon_path_before_execution(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    plugin = _write_version_only_plugin(
        tmp_path / "tools;legacy" / "protoc-gen-protocyte", __version__
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
    assert "PROTOCYTE_PLUGIN_EXECUTABLE must not contain ';'" in output
    assert "semicolon-free path" in output
    assert "failed its required --version check" not in output


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


def test_prepared_plugin_without_environment_mode_defaults_to_explicit(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${CMAKE_COMMAND}")',
                "_protocyte_prepare_plugin()",
                "get_property(plugin_is_managed GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_IS_MANAGED)",
                'if(NOT plugin_is_managed STREQUAL "FALSE")',
                '    message(FATAL_ERROR "pre-seeded plugin did not default to explicit mode")',
                "endif()",
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_source_codegen_with_explicit_plugin_does_not_discover_python(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        _real_protoc_requirement_unavailable(
            "Ninja is required to verify external-plugin source generation"
        )
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    plugin_module_dir = tmp_path / "plugin-module"
    import_scan_log = tmp_path / "external-import-scan-invocations.txt"
    plugin = _write_inherited_pythonpath_plugin_wrapper(
        tmp_path / "tools" / "protoc-gen-protocyte",
        plugin_module_dir,
        repo_root,
        import_scan_log=import_scan_log,
    )
    plugin_environment = os.environ.copy()
    plugin_environment["PYTHONPATH"] = str(plugin_module_dir)
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package demo; message Demo {}\n',
        encoding="utf-8",
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(external_plugin_without_python_discovery LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Python3 TRUE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                "_protocyte_prepare_plugin()",
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_MANAGED_PLUGIN_EXECUTABLE "${PROTOCYTE_PLUGIN_EXECUTABLE}")',
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
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
        env=plugin_environment,
    )
    configure_scan_count = len(import_scan_log.read_text(encoding="utf-8").splitlines())
    assert configure_scan_count > 0
    build_graph = (build_dir / "build.ninja").read_text(encoding="utf-8")
    assert "MANAGED_DEPENDENCY_READER=FALSE" in build_graph
    assert "PROTOCYTE_MANAGED_PLUGIN=FALSE" in build_graph
    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    subprocess.run(build_command, check=True, env=plugin_environment)
    first_build_scan_count = len(
        import_scan_log.read_text(encoding="utf-8").splitlines()
    )
    assert first_build_scan_count > configure_scan_count
    generated_header = build_dir / "generated" / "demo.protocyte.hpp"
    assert generated_header.is_file()
    no_op = subprocess.run(
        build_command,
        check=True,
        capture_output=True,
        text=True,
        env=plugin_environment,
    )
    no_op_scan_count = len(import_scan_log.read_text(encoding="utf-8").splitlines())
    assert no_op_scan_count > first_build_scan_count
    no_op_output = no_op.stdout + no_op.stderr
    assert "Scanning protobuf imports" not in no_op_output
    assert "Generating generated/" not in no_op_output
    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert "Python3_EXECUTABLE" not in cache


def test_source_codegen_reports_plugin_without_private_import_scan(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    (tmp_path / "tools").mkdir()
    plugin = _write_incompatible_protocyte_plugin(
        tmp_path / "tools" / "protoc-gen-protocyte"
    )
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_file = source_dir / "proto" / "demo.proto"
    proto_file.parent.mkdir(parents=True)
    proto_file.write_text('syntax = "proto3"; message Demo {}\n', encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(incompatible_import_scan_plugin LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Python3 TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/demo.proto",
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
    assert "old plugin cannot discover" in output
    assert "actual version-matched Protocyte plugin" in output
    assert "_cmake-import-scan-v1 support" in output
    assert "Could NOT find Python" not in output


def test_managed_import_scan_sanitizes_python_environment(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        _real_protoc_requirement_unavailable(
            "Ninja is required to verify managed import-scan isolation"
        )
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    managed_environment_root = tmp_path / "managed-environments"
    poison_path = tmp_path / "poison-path"
    poison_home = tmp_path / "poison-home"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    poison_package = poison_path / "protocyte"
    poison_package.mkdir(parents=True)
    poison_home.mkdir()
    (poison_package / "__init__.py").write_text(
        'raise RuntimeError("poisoned Protocyte import")\n',
        encoding="utf-8",
    )
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package demo; message Demo {}\n',
        encoding="utf-8",
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(managed_import_scan_isolation LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'set(PROTOCYTE_PYTHON_ENV_ROOT "{managed_environment_root.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_setup_codegen()",
                f'set(ENV{{PYTHONPATH}} "{poison_path.as_posix()}")',
                f'set(ENV{{PYTHONHOME}} "{poison_home.as_posix()}")',
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
    guard_manifests = list(
        (build_dir / "CMakeFiles" / "protocyte-prebuild").glob("*.list")
    )
    assert len(guard_manifests) == 1
    poisoned_environment = os.environ.copy()
    poisoned_environment["PYTHONPATH"] = str(poison_path)
    poisoned_environment["PYTHONHOME"] = str(poison_home)
    subprocess.run(
        [
            "cmake",
            f"-DMANIFEST_FILE={guard_manifests[0]}",
            "-DFAIL_ON_CHANGE=TRUE",
            "-P",
            str(repo_root / "cmake" / "ProtocytePreBuildGuard.cmake"),
        ],
        check=True,
        env=poisoned_environment,
    )


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
    assert (
        '"-DLOCK_DIRECTORY_IDENTITY_SHA256=${protocyte_lock_directory_identity_hash}"'
        in generation_command
    )
    assert '"@${ARGUMENT_FILE}"' in generation_script
    assert (
        generation_script.count("_protocyte_validate_generation_lock_namespace()") == 2
    )
    assert 'WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"' in generation_command
    assert (
        '"-DSOURCE_DIRECTORY_HEX=${protocyte_source_directory_hex}"'
        in generation_command
    )
    assert (
        "PROTOCYTE_CMAKE_WORKING_DIRECTORY_HEX=${SOURCE_DIRECTORY_HEX}"
        in generation_script
    )
    assert (
        '"${protocyte_plugin_executable}"' in generation_command.split("DEPENDS", 1)[1]
    )


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
                '_protocyte_write_protoc_response_file(response_file response_relative unit-test "${response_content}")',
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
        "_protocyte_append_protoc_response_argument(content [==[first\nsecond]==])",
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "protoc response files define one literal argument per line" in output


def test_quickstart_generates_with_source_relative_tool_paths(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        _real_protoc_requirement_unavailable(
            "Ninja is required to verify quick-start generation"
        )
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
    expected = generated_file_base(descriptor_name, max_output_path_bytes=path_budget)
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
                f"_protocyte_generated_path_budget(path_budget directory_budget [==[{out_dir}]==])",
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
    assert "OUT_DIR must be a configure-time path, not a generator expression" in output


@pytest.mark.parametrize(
    ("install_include_dir", "expected_error"),
    [
        (
            '"$<IF:$<BOOL:1>,include,other>"',
            "INSTALL_INCLUDE_DIR must be a configure-time relative path, not a generator expression",
        ),
        (
            '"/absolute/include"',
            "INSTALL_INCLUDE_DIR must be a relative virtual directory using '/'",
        ),
        (
            '"C:/absolute/include"',
            "INSTALL_INCLUDE_DIR must be a relative virtual directory using '/'",
        ),
        (
            '"include/../escape"',
            "INSTALL_INCLUDE_DIR contains an unsafe or non-normalized path segment",
        ),
        (
            '"include//nested"',
            "INSTALL_INCLUDE_DIR contains an unsafe or non-normalized path segment",
        ),
        pytest.param(
            '"include;private"',
            "INSTALL_INCLUDE_DIR contains characters that are unsafe in generated includes",
            id="semicolon",
        ),
        pytest.param(
            '"include\x1fprivate"',
            "INSTALL_INCLUDE_DIR must not contain control characters",
            id="control-character",
        ),
        pytest.param(
            '" include/private"',
            "INSTALL_INCLUDE_DIR must not have leading or trailing segment whitespace",
            id="leading-whitespace",
        ),
        pytest.param(
            '"include/private "',
            "INSTALL_INCLUDE_DIR must not have leading or trailing segment whitespace",
            id="trailing-whitespace",
        ),
        pytest.param(
            '"include/private."',
            "INSTALL_INCLUDE_DIR contains a path segment ending in '.'",
            id="trailing-dot",
        ),
        pytest.param(
            '"include/CON"',
            "INSTALL_INCLUDE_DIR contains a Windows-reserved device name",
            id="reserved-device-name",
        ),
        pytest.param(
            '"include:private"',
            "INSTALL_INCLUDE_DIR must be a relative virtual directory using '/'",
            id="colon",
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


@pytest.mark.parametrize(
    "injected_assignment",
    [
        pytest.param(
            "set(protocyte_source_check_targets caller_scope_injected_dependency)",
            id="normal-variable",
        ),
        pytest.param(
            'set(protocyte_source_check_targets cache_injected_dependency CACHE STRING "" FORCE)',
            id="cache-variable",
        ),
    ],
)
def test_generate_does_not_inherit_source_check_targets_from_caller_scope(
    tmp_path: Path,
    injected_assignment: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "function(_protocyte_setup_codegen_internal fetch_missing_import_sources)",
                "endfunction()",
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_OPTIONS_PROTO "${CMAKE_CURRENT_SOURCE_DIR}/descriptor-set.pb")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES "")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${CMAKE_COMMAND}")',
                'set(PROTOCYTE_PROTOC_EXECUTABLE "${CMAKE_COMMAND}")',
                'set(PROTOCYTE_PROTOC_DEPENDENCY "${CMAKE_COMMAND}")',
                injected_assignment,
                "protocyte_generate(",
                "    TARGET demo_codegen",
                "    DESCRIPTOR_SET descriptor-set.pb",
                "    OUT_DIR generated",
                "    PROTOS api/demo.proto",
                "    OPTIONS format=off",
                ")",
            ]
        ),
        files={"descriptor-set.pb": "descriptor set placeholder\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr


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
    ("first_descriptor", "second_descriptor"),
    [
        pytest.param("api/demo.proto", "api/demo.proto", id="exact-path"),
        pytest.param("api/demo.proto", "API/DEMO.proto", id="casefolded-path"),
    ],
)
def test_cmake_rejects_generated_outputs_owned_by_multiple_current_targets(
    tmp_path: Path,
    first_descriptor: str,
    second_descriptor: str,
) -> None:
    snippet = "\n".join(
        [
            "function(_protocyte_setup_codegen_internal fetch_missing_import_sources)",
            "endfunction()",
            'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}")',
            'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_OPTIONS_PROTO "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb")',
            'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES "")',
            'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${CMAKE_COMMAND}")',
            'set(PROTOCYTE_PROTOC_EXECUTABLE "${CMAKE_COMMAND}")',
            'set(PROTOCYTE_PROTOC_DEPENDENCY "${CMAKE_COMMAND}")',
            "protocyte_generate(",
            "    TARGET first_codegen",
            '    DESCRIPTOR_SET "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb"',
            '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
            f"    PROTOS {first_descriptor}",
            "    OPTIONS format=off",
            ")",
            "protocyte_generate(",
            "    TARGET second_codegen",
            '    DESCRIPTOR_SET "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb"',
            '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
            f"    PROTOS {second_descriptor}",
            "    OPTIONS format=off",
            ")",
        ]
    )

    result = _configure_cmake_snippet(
        tmp_path,
        snippet,
        files={"descriptor_set.pb": "placeholder"},
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split()).replace("\\", "/")
    assert "generated output" in output
    assert "portable-equivalent output" in output
    assert "first_codegen" in output
    assert "second_codegen" in output
    assert "api/demo.protocyte.hpp" in output.lower()


@pytest.mark.parametrize(
    ("lock_root", "expected_diagnostic"),
    [
        pytest.param(
            "relative/locks",
            "must be absolute so all build processes use a stable lock namespace",
            id="relative",
        ),
        pytest.param(
            "$<IF:$<BOOL:1>,locks,other>",
            "must be a configure-time absolute path, not a generator expression",
            id="generator-expression",
        ),
    ],
)
def test_cmake_rejects_unsafe_output_lock_root(
    tmp_path: Path,
    lock_root: str,
    expected_diagnostic: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{lock_root}")',
                "_protocyte_shared_output_lock_directory(lock_directory)",
            ]
        ),
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert expected_diagnostic in output


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
function(_protocyte_run_source_import_scan)
    message(FATAL_ERROR "reached protocyte_generate downstream validation")
endfunction()
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
        f"{function_name} OPTIONS entry 'HOSTED_ALOCATOR' must use key=value" in output
    )


@pytest.mark.parametrize(
    "function_name",
    [
        "protocyte_generate",
        "protocyte_add_proto_library",
        "protocyte_add_descriptor_set_library",
    ],
)
def test_public_cmake_functions_require_named_include_prefix_keyword(
    tmp_path: Path,
    function_name: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        f"{function_name}(OPTIONS include_prefix=vendor/wire)",
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert f"{function_name} OPTIONS must not set include_prefix" in output
    assert "use INCLUDE_PREFIX" in output


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


def test_descriptor_discover_requires_a_configure_time_descriptor_set(
    tmp_path: Path,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "add_custom_target(descriptor_producer)",
                "protocyte_generate(",
                "    TARGET demo",
                "    DESCRIPTOR_SET generated.pb",
                "    OUT_DIR generated",
                "    DISCOVER",
                "    DEPENDS descriptor_producer",
                ")",
            ]
        ),
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "must exist during configuration when using DISCOVER" in output
    assert "use explicit PROTOS/FILES with DEPENDS" in output


@pytest.mark.parametrize(
    "generator",
    [
        pytest.param(None, id="visual-studio-default"),
        pytest.param("Ninja", id="ninja"),
        pytest.param("Ninja Multi-Config", id="ninja-multi-config"),
    ],
)
def test_descriptor_set_rejects_generator_expression_path(
    tmp_path: Path,
    generator: str | None,
) -> None:
    if generator is None and os.name != "nt":
        pytest.skip("the default Visual Studio generator is only available on Windows")
    if generator is not None and shutil.which("ninja") is None:
        pytest.skip(f"{generator} requires Ninja")

    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_generator_expression LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "add_custom_target(descriptor_producer)",
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    DESCRIPTOR_SET "${CMAKE_CURRENT_BINARY_DIR}/$<CONFIG>/descriptor-set.pb"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS api/demo.proto",
                "    DEPENDS descriptor_producer",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_command = [
        "cmake",
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
    ]
    environment = os.environ.copy()
    if generator is None:
        environment.pop("CMAKE_GENERATOR", None)
    else:
        configure_command[1:1] = ["-G", generator]

    result = subprocess.run(
        configure_command,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    if generator is None:
        assert "Building for: Visual Studio" in output
    assert "DESCRIPTOR_SET must be a configure-time path" in output
    assert "not a generator expression" in output
    assert "concrete, config-independent descriptor-set output" in output
    assert "explicit PROTOS/FILES" in output
    assert "DEPENDS" in output


def test_cmake_install_tree_contains_installable_python_project() -> None:
    cmake = (Path(__file__).resolve().parents[1] / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )

    assert 'DESTINATION "${PROTOCYTE_INSTALL_PYTHONDIR}/src"' in cmake
    assert '"${CMAKE_CURRENT_LIST_DIR}/pyproject.toml"' in cmake
    assert '"${CMAKE_CURRENT_LIST_DIR}/protocyte-cmake-constraints.txt"' in cmake
    assert 'DESTINATION "${PROTOCYTE_INSTALL_PYTHONDIR}"' in cmake


@pytest.mark.parametrize(
    "manifest",
    ["cmake/Protocyte.cmake", "cmake/protocyteConfig.cmake.in"],
)
def test_cmake_generator_source_manifests_track_python_helpers(
    manifest: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    content = (repo_root / manifest).read_text(encoding="utf-8")

    assert '"${PROTOCYTE_PACKAGE_ROOT}/dependency_file.py"' in content
    assert '"${PROTOCYTE_IMPORT_SCANNER}"' in content


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
    installed_files = [Path(line).resolve() for line in manifest.splitlines() if line]
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
    assert any(prefix.rglob("ProtocyteProcess.cmake"))
    assert any(prefix.rglob("ProtocyteManagedEnvironment.py"))
    assert any(prefix.rglob("owned_transactions.py"))
    assert (prefix / "share/protocyte/python/pyproject.toml").is_file()


@pytest.mark.parametrize("imports_protobuf", [False, True])
def test_installed_package_only_requires_protobuf_imports_for_selected_sources(
    tmp_path: Path, imports_protobuf: bool
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    core_build_dir = tmp_path / "protocyte-build"
    install_prefix = tmp_path / "install"
    provider_source_dir = tmp_path / "provider"
    provider_build_dir = tmp_path / "provider-build"
    plugin = _write_python_plugin_wrapper(
        tmp_path / "tools" / "protoc-gen-protocyte", repo_root
    )
    protoc = tmp_path / "tools" / "protoc"
    protoc.write_text("", encoding="utf-8")

    subprocess.run(
        [
            "cmake",
            "-S",
            str(repo_root),
            "-B",
            str(core_build_dir),
            "-DPROTOCYTE_INSTALL=ON",
            "-DPROTOCYTE_FETCH_PROTOBUF=OFF",
            f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--install", str(core_build_dir)], check=True)

    proto_dir = provider_source_dir / "proto"
    proto_dir.mkdir(parents=True)
    imports = 'import\n    "protocyte/options.proto"\n;\n' if imports_protobuf else ""
    (proto_dir / "demo.proto").write_text(
        f'syntax = "proto3";\n{imports}message Demo {{}}\n', encoding="utf-8"
    )
    (provider_source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(installed_import_preflight LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "find_package(protocyte CONFIG REQUIRED)",
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

    result = subprocess.run(
        [
            "cmake",
            "-S",
            str(provider_source_dir),
            "-B",
            str(provider_build_dir),
            f"-DCMAKE_PREFIX_PATH={install_prefix}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if imports_protobuf:
        output = " ".join((result.stdout + result.stderr).split())
        assert result.returncode != 0
        assert "could not locate google/protobuf/descriptor.proto" in output
    else:
        assert result.returncode == 0, result.stdout + result.stderr


def _configure_source_import_preflight(
    tmp_path: Path,
    source: str,
    *,
    proto_name: str = "demo.proto",
    extra_files: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    plugin = _write_python_plugin_wrapper(
        tmp_path / "tools" / "protoc-gen-protocyte", repo_root
    )
    protoc = tmp_path / "tools" / "protoc"
    protoc.write_text("", encoding="utf-8")
    files = {f"proto/{proto_name}": source, **(extra_files or {})}
    return _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_VERSION "{__version__}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                "    PROTO_ROOT proto",
                "    OUT_DIR generated",
                f"    PROTOS [==[proto/{proto_name}]==]",
                "    OPTIONS format=off",
                ")",
            ]
        ),
        files=files,
        timeout=timeout,
    )


@pytest.mark.parametrize(
    ("source", "requires_protobuf_imports"),
    [
        pytest.param(
            """
syntax = "proto3";
/* import "protocyte/options.proto"; */
message Demo {}
""",
            False,
            id="block-comment-fake-import",
        ),
        pytest.param(
            'syntax = "proto3"; im/**/port "protocyte/options.proto";\n',
            False,
            id="comment-does-not-join-identifiers",
        ),
        pytest.param(
            (
                'syntax = "proto3"; // comment\r import '
                '"google/protobuf/any.proto";\nmessage Demo {}\n'
            ),
            False,
            id="carriage-return-does-not-end-line-comment",
        ),
        pytest.param(
            'syntax = "proto3"; import/**/"protocyte/options.proto";\n',
            True,
            id="comment-preserves-token-boundary-after-import",
        ),
        pytest.param(
            'syntax = "proto3"; import\v"google/protobuf/any.proto";\n',
            True,
            id="vertical-tab-whitespace",
        ),
        pytest.param(
            'syntax = "proto3"; import\f"google/protobuf/any.proto";\n',
            True,
            id="form-feed-whitespace",
        ),
        pytest.param(
            """
syntax = "proto3";
option java_package = "https://example.invalid//wire";
import "protocyte/options.proto";
message Demo {}
""",
            True,
            id="double-slash-in-string-before-import",
        ),
        pytest.param(
            """
syntax = "proto3";
import "fake\\\"name.proto";
import "protocyte/options.proto";
message Demo {}
""",
            True,
            id="escaped-quote-import-before-real-import",
        ),
        pytest.param(
            'syntax = "proto3"; import public "protocyte/options.proto"; message Demo {}\n',
            True,
            id="public-import",
        ),
        pytest.param(
            'syntax = "proto3"; import weak "google/protobuf/descriptor.proto"; message Demo {}\n',
            True,
            id="weak-import",
        ),
        pytest.param(
            (
                'edition = "2024"; import option '
                '"google/protobuf/cpp_features.proto"; message Demo {}\n'
            ),
            True,
            id="edition-2024-option-import",
        ),
        pytest.param(
            r'syntax = "proto3"; import "\x67oogle/protobuf/any.proto"; message Demo {}'
            + "\n",
            True,
            id="hex-escaped-import",
        ),
        pytest.param(
            r'syntax = "proto3"; import "\u0067oogle/protobuf/any.proto"; message Demo {}'
            + "\n",
            True,
            id="unicode-short-escaped-import",
        ),
        pytest.param(
            r'syntax = "proto3"; import "\U00000067oogle/protobuf/any.proto"; message Demo {}'
            + "\n",
            True,
            id="unicode-long-escaped-import",
        ),
        pytest.param(
            r'syntax = "proto3"; import "\147oogle/protobuf/any.proto"; message Demo {}'
            + "\n",
            True,
            id="octal-escaped-leading-character",
        ),
        pytest.param(
            r'syntax = "proto3"; import "google\057protobuf/any.proto"; message Demo {}'
            + "\n",
            True,
            id="octal-escaped-separator",
        ),
        pytest.param(
            'syntax = "proto3"; import "google/" "protobuf/any.proto"; message Demo {}\n',
            True,
            id="adjacent-import-literals",
        ),
        pytest.param(
            r'syntax = "proto2"; message Demo { optional bytes payload = 1 [default = "\000"]; }'
            + "\n",
            False,
            id="non-import-nul-bytes-default",
        ),
        pytest.param(
            r'syntax = "proto2"; message Demo { optional bytes payload = 1 [default = "\777"]; }'
            + "\n",
            False,
            id="non-import-wrapped-octal-bytes-default",
        ),
        pytest.param(
            r'syntax = "proto3"; import "\000.proto"; message Demo {}' + "\n",
            False,
            id="nul-byte-import-does-not-crash-preflight",
        ),
        pytest.param(
            r'syntax = "proto3"; import "\777.proto"; message Demo {}' + "\n",
            False,
            id="wrapped-octal-import-does-not-crash-preflight",
        ),
    ],
)
def test_source_import_preflight_tokenizes_comments_strings_and_qualifiers(
    tmp_path: Path, source: str, requires_protobuf_imports: bool
) -> None:
    result = _configure_source_import_preflight(tmp_path, source)

    output = " ".join((result.stdout + result.stderr).split())
    if requires_protobuf_imports:
        assert result.returncode != 0
        assert "could not locate google/protobuf/descriptor.proto" in output
    else:
        assert result.returncode == 0, result.stdout + result.stderr


def test_source_import_preflight_follows_transitive_edition_2024_option_import(
    tmp_path: Path,
) -> None:
    result = _configure_source_import_preflight(
        tmp_path,
        'edition = "2024"; import "dependency.proto"; message Demo {}\n',
        extra_files={
            "proto/dependency.proto": (
                'edition = "2024"; import option '
                '"google/protobuf/cpp_features.proto"; message Dependency {}\n'
            )
        },
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "could not locate google/protobuf/descriptor.proto" in output


@pytest.mark.parametrize(
    ("import_literal", "expected_protoc_error", "windows_only"),
    [
        pytest.param(
            '"../outside.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            False,
            id="parent-component",
        ),
        pytest.param(
            r'"..\\outside.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            True,
            id="backslash",
        ),
        pytest.param(
            '"' + "\\" * 2 + 'server/child.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            True,
            id="windows-one-leading-backslash",
        ),
        pytest.param(
            '"' + "\\" * 6 + 'server/child.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            True,
            id="windows-three-leading-backslashes",
        ),
        pytest.param(
            '"' + "\\" * 4 + "server" + "\\" * 2 + 'child.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            True,
            id="windows-preserved-leading-with-interior-backslash",
        ),
        pytest.param(
            '"C:' + "\\" * 2 + 'x.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            True,
            id="windows-drive-backslash-absolute",
        ),
        pytest.param('"/outside.proto"', "File not found.", False, id="absolute"),
        pytest.param(
            '"//outside.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            False,
            id="leading-double-slash",
        ),
        pytest.param(
            '"nested//outside.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            False,
            id="empty-component",
        ),
        pytest.param(
            '"./outside.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            False,
            id="dot-component",
        ),
        pytest.param(
            '"google/protobuf/../any.proto"',
            _PROTOC_NONCANONICAL_VIRTUAL_PATH_ERROR,
            False,
            id="protobuf-prefix-parent-component",
        ),
        pytest.param(
            '"nested/"', "File not found.", False, id="trailing-empty-component"
        ),
        pytest.param('""', "File not found.", False, id="empty"),
        pytest.param(
            '"C:/x.proto"', "File not found.", True, id="windows-drive-absolute"
        ),
    ],
)
def test_import_scanner_matches_pinned_protoc_noncanonical_path_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    import_literal: str,
    expected_protoc_error: str,
    windows_only: bool,
) -> None:
    if windows_only and os.name != "nt":
        pytest.skip("Windows drive-path semantics are Windows-only")

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        f'syntax = "proto3"; import {import_literal}; message Demo {{}}\n',
        encoding="utf-8",
    )

    lookup_attempts: list[str] = []
    with monkeypatch.context() as scanner_patch:
        scanner_patch.setattr(
            os.path,
            "exists",
            lambda candidate: lookup_attempts.append(candidate) or False,
        )
        assert not source_closure_requires_protobuf_imports(
            [str(source_file)], [str(proto_root)]
        )
    assert lookup_attempts == []

    protoc_result = subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_root}",
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert protoc_result.returncode != 0
    assert expected_protoc_error in protoc_result.stderr, protoc_result.stderr


@pytest.mark.parametrize(
    ("import_name", "import_literal", "platform"),
    [
        pytest.param(
            "C:x.proto",
            '"C:x.proto"',
            "windows",
            id="windows-drive-relative",
        ),
        pytest.param(
            "server/child.proto",
            r'"\\\\server/child.proto"',
            "windows",
            id="windows-preserved-leading-backslashes",
        ),
        pytest.param(
            "C:/x.proto",
            '"C:/x.proto"',
            "posix",
            id="posix-drive-like-directory",
        ),
        pytest.param(
            r"..\outside.proto",
            r'"..\\outside.proto"',
            "posix",
            id="posix-literal-backslash",
        ),
    ],
)
def test_import_scanner_matches_pinned_protoc_platform_relative_paths(
    tmp_path: Path,
    import_name: str,
    import_literal: str,
    platform: str,
) -> None:
    if platform == "windows" and os.name != "nt":
        pytest.skip("Windows drive-relative semantics are Windows-only")
    if platform == "posix" and (os.name == "nt" or sys.platform == "cygwin"):
        pytest.skip("POSIX filename semantics are POSIX-only")

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    protocyte_proto_dir = repo_root / "src" / "protocyte" / "proto"
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        f'syntax = "proto3"; import {import_literal}; message Demo {{}}\n',
        encoding="utf-8",
    )
    if platform == "windows" and import_name == "C:x.proto":
        (proto_root / "C").write_text("", encoding="utf-8")
        dependency_file = Path(str(proto_root) + "/" + import_name)
    else:
        dependency_file = proto_root / import_name
        dependency_file.parent.mkdir(parents=True, exist_ok=True)
    dependency_file.write_text(
        (
            'syntax = "proto3"; import "protocyte/options.proto"; '
            "message Dependency {}\n"
        ),
        encoding="utf-8",
    )

    import_roots = [
        str(proto_root),
        str(protocyte_proto_dir),
        str(protobuf_import_dir),
    ]
    assert source_closure_requires_protobuf_imports([str(source_file)], import_roots)
    subprocess.run(
        [
            str(protoc),
            *(f"--proto_path={root}" for root in import_roots),
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows path masking is Windows-only")
@pytest.mark.parametrize("masked_component", [".", ".."])
def test_import_scanner_rejects_masked_windows_dot_components_without_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    masked_component: str,
) -> None:
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    import_literal = '"' + "\\" * 4 + masked_component + '/outside.proto"'
    source_file.write_text(
        f'syntax = "proto3"; import {import_literal}; message Demo {{}}\n',
        encoding="utf-8",
    )
    sentinel = (
        proto_root / "outside.proto"
        if masked_component == "."
        else tmp_path / "outside.proto"
    )
    sentinel.write_text(
        'syntax = "proto3"; import "protocyte/options.proto";\n',
        encoding="utf-8",
    )

    read_files: list[Path] = []
    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(path: Path) -> bytes:
        read_files.append(path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    with pytest.raises(UnsafeVirtualImportPathError) as error:
        source_closure_requires_protobuf_imports([str(source_file)], [str(proto_root)])
    assert str(error.value) == UNSAFE_VIRTUAL_IMPORT_PATH_ERROR
    assert UNSAFE_VIRTUAL_IMPORT_PATH_ERROR.isascii()
    assert read_files == [source_file]


@pytest.mark.skipif(os.name != "nt", reason="Windows path masking is Windows-only")
@pytest.mark.parametrize("masked_component", [".", ".."])
def test_source_import_preflight_rejects_masked_windows_dot_components(
    tmp_path: Path, masked_component: str
) -> None:
    import_literal = '"' + "\\" * 4 + masked_component + '/outside.proto"'
    sentinel_path = (
        "proto/outside.proto" if masked_component == "." else "outside.proto"
    )
    result = _configure_source_import_preflight(
        tmp_path,
        f'syntax = "proto3"; import {import_literal}; message Demo {{}}\n',
        extra_files={
            sentinel_path: ('syntax = "proto3"; import "protocyte/options.proto";\n')
        },
    )

    output = result.stdout + result.stderr
    normalized_output = " ".join(output.split())
    assert result.returncode != 0
    assert UNSAFE_VIRTUAL_IMPORT_PATH_ERROR in normalized_output
    assert "Traceback" not in output
    assert "outside.proto" not in UNSAFE_VIRTUAL_IMPORT_PATH_ERROR
    assert not (tmp_path / "build" / "CMakeFiles" / "protocyte-arguments").exists()
    assert not (tmp_path / "build" / "generated").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows drive syntax is Windows-only")
@pytest.mark.parametrize(
    "import_name",
    [
        pytest.param("C:/x:y.proto", id="later-colon"),
        pytest.param("1:/x.proto", id="non-alpha-drive"),
    ],
)
def test_import_scanner_maps_windows_non_absolute_drive_like_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, import_name: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        f'syntax = "proto3"; import "{import_name}"; message Demo {{}}\n',
        encoding="utf-8",
    )

    lookup_attempts: list[str] = []
    with monkeypatch.context() as scanner_patch:
        scanner_patch.setattr(
            os.path,
            "exists",
            lambda candidate: lookup_attempts.append(candidate) or False,
        )
        assert not source_closure_requires_protobuf_imports(
            [str(source_file)], [str(proto_root)]
        )
    assert lookup_attempts == [proto_root.as_posix() + "/" + import_name]

    protoc_result = subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_root}",
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert protoc_result.returncode != 0
    assert f"{import_name}: File not found." in protoc_result.stderr


@pytest.mark.skipif(
    os.name == "nt" or sys.platform == "cygwin",
    reason="literal trailing-backslash directories require a POSIX filesystem",
)
def test_import_scanner_preserves_posix_trailing_backslash_import_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    protocyte_proto_dir = repo_root / "src" / "protocyte" / "proto"
    proto_root = tmp_path / "proto"
    import_root = tmp_path / "imports\\"
    proto_root.mkdir()
    import_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        'syntax = "proto3"; import "dependency.proto"; message Demo {}\n',
        encoding="utf-8",
    )
    (import_root / "dependency.proto").write_text(
        (
            'syntax = "proto3"; import "protocyte/options.proto"; '
            "message Dependency {}\n"
        ),
        encoding="utf-8",
    )

    import_roots = [
        str(proto_root),
        str(import_root),
        str(protocyte_proto_dir),
        str(protobuf_import_dir),
    ]
    assert source_closure_requires_protobuf_imports([str(source_file)], import_roots)
    subprocess.run(
        [
            str(protoc),
            *(f"--proto_path={root}" for root in import_roots),
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


def test_import_scanner_does_not_expand_noncanonical_lexical_alias_cycles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proto_root = tmp_path / "proto"
    alias_directory = proto_root / "alias"
    alias_directory.mkdir(parents=True)
    aliases = ["alias/../" * depth + "cycle.proto" for depth in range(1, 33)]
    imports = "\n".join(f'import "{alias}";' for alias in aliases)
    source_file = proto_root / "demo.proto"
    source_file.write_text(f'syntax = "proto3";\n{imports}\n', encoding="utf-8")
    (proto_root / "cycle.proto").write_text(
        f'syntax = "proto3";\n{imports}\n', encoding="utf-8"
    )

    read_files: list[Path] = []
    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(path: Path) -> bytes:
        read_files.append(path)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    assert not source_closure_requires_protobuf_imports(
        [str(source_file)], [str(proto_root)]
    )
    assert read_files == [source_file]


def test_import_scanner_completes_resolved_closure_after_protobuf_import(
    tmp_path: Path,
) -> None:
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    dependency_file = proto_root / "dependency.proto"
    source_file.write_text(
        (
            'syntax = "proto3"; import "google/protobuf/any.proto"; '
            'import "dependency.proto"; message Demo {}\n'
        ),
        encoding="utf-8",
    )
    dependency_file.write_text(
        'syntax = "proto3"; message Dependency {}\n', encoding="utf-8"
    )

    requires_protobuf_imports, closure = _scan_source_closure(
        [str(source_file)], [str(proto_root)]
    )
    assert requires_protobuf_imports
    assert closure == [str(source_file), dependency_file.as_posix()]


def test_import_scanner_preserves_pinned_protoc_directory_link_traversal(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    protocyte_proto_dir = repo_root / "src" / "protocyte" / "proto"
    proto_root = tmp_path / "proto"
    outside_root = tmp_path / "outside"
    proto_root.mkdir()
    outside_root.mkdir()
    (proto_root / "demo.proto").write_text(
        'syntax = "proto3"; import "linked/dep.proto"; message Demo {}\n',
        encoding="utf-8",
    )
    (outside_root / "dep.proto").write_text(
        (
            'syntax = "proto3"; import "protocyte/options.proto"; '
            "message Dependency {}\n"
        ),
        encoding="utf-8",
    )
    _create_generated_output_directory_link(proto_root / "linked", outside_root)

    import_roots = [
        str(proto_root),
        str(protocyte_proto_dir),
        str(protobuf_import_dir),
    ]
    assert source_closure_requires_protobuf_imports(
        [str(proto_root / "demo.proto")], import_roots
    )

    subprocess.run(
        [
            str(protoc),
            *(f"--proto_path={root}" for root in import_roots),
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


@pytest.mark.parametrize(
    "comment",
    [
        pytest.param("//x\n", id="line-comments"),
        pytest.param("/**/", id="block-comments"),
    ],
)
def test_source_import_preflight_dense_comment_scanning_is_bounded(
    tmp_path: Path, comment: str
) -> None:
    timings: list[float] = []
    for label, source_size in (("small", 64 * 1024), ("large", 512 * 1024)):
        source = (
            comment * (source_size // len(comment))
            + 'import "protocyte/options.proto";\n'
        )
        started_at = time.monotonic()
        result = _configure_source_import_preflight(
            tmp_path / label,
            source,
            timeout=10,
        )
        timings.append(time.monotonic() - started_at)
        output = " ".join((result.stdout + result.stderr).split())
        assert result.returncode != 0
        assert "could not locate google/protobuf/descriptor.proto" in output

    small_elapsed, large_elapsed = timings
    assert large_elapsed < 8.0
    assert large_elapsed < small_elapsed * 12.0 + 1.0


@pytest.mark.parametrize(
    "import_literals",
    [
        r'"\x67oogle/protobuf/any.proto"',
        r'"\u0067oogle/protobuf/any.proto"',
        r'"\U00000067oogle/protobuf/any.proto"',
        r'"\147oogle/protobuf/any.proto"',
        r'"google\057protobuf/any.proto"',
        '"google/" "protobuf/any.proto"',
    ],
)
def test_real_protoc_accepts_preflight_import_literal_forms(
    tmp_path: Path, import_literals: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    proto_dir = tmp_path / "proto"
    proto_dir.mkdir()
    (proto_dir / "demo.proto").write_text(
        f'syntax = "proto3"; import {import_literals}; message Demo {{}}\n',
        encoding="utf-8",
    )

    subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_dir}",
            f"--proto_path={protobuf_import_dir}",
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        check=True,
    )


@pytest.mark.parametrize(
    "separator",
    [pytest.param("\v", id="vertical-tab"), pytest.param("\f", id="form-feed")],
)
def test_import_scanner_matches_pinned_protoc_extended_import_whitespace(
    tmp_path: Path, separator: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        (
            f'syntax = "proto3"; import{separator}'
            '"google/protobuf/any.proto"; message Demo {}\n'
        ),
        encoding="utf-8",
    )

    import_roots = [str(proto_root), str(protobuf_import_dir)]
    assert source_closure_requires_protobuf_imports([str(source_file)], import_roots)
    subprocess.run(
        [
            str(protoc),
            *(f"--proto_path={root}" for root in import_roots),
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


def test_import_scanner_matches_pinned_protoc_line_comment_cr_handling(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_bytes(
        b'syntax = "proto3"; // comment\r import "google/protobuf/any.proto";\n'
        b"message Demo {}\n"
    )

    assert not source_closure_requires_protobuf_imports(
        [str(source_file)], [str(proto_root)]
    )
    subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_root}",
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


@pytest.mark.parametrize("transitive", [False, True], ids=["direct", "transitive"])
def test_import_scanner_matches_pinned_protoc_edition_2024_option_imports(
    tmp_path: Path, transitive: bool
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    option_import = (
        'edition = "2024";\n'
        'import option "google/protobuf/cpp_features.proto";\n'
        "message Dependency {}\n"
    )
    source_file = proto_root / "demo.proto"
    if transitive:
        source_file.write_text(
            'edition = "2024"; import "dependency.proto"; message Demo {}\n',
            encoding="utf-8",
        )
        (proto_root / "dependency.proto").write_text(option_import, encoding="utf-8")
    else:
        source_file.write_text(option_import, encoding="utf-8")

    import_roots = [str(proto_root), str(protobuf_import_dir)]
    assert source_closure_requires_protobuf_imports([str(source_file)], import_roots)
    subprocess.run(
        [
            str(protoc),
            *(f"--proto_path={root}" for root in import_roots),
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


@pytest.mark.parametrize(
    ("dependency_name", "import_literal"),
    [
        pytest.param("café.proto", r'"caf\u00e9.proto"', id="bmp"),
        pytest.param(
            "emoji\U0001f600.proto",
            r'"emoji\U0001f600.proto"',
            id="non-bmp",
        ),
        pytest.param(
            "emoji\U0001f600.proto",
            r'"emoji\ud83d\ude00.proto"',
            id="utf16-surrogate-pair",
        ),
    ],
)
def test_import_scanner_matches_pinned_protoc_unicode_import_escapes(
    tmp_path: Path, dependency_name: str, import_literal: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    protocyte_proto_dir = repo_root / "src" / "protocyte" / "proto"
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        f'syntax = "proto3"; import {import_literal}; message Demo {{}}\n',
        encoding="utf-8",
    )
    (proto_root / dependency_name).write_text(
        (
            'syntax = "proto3"; import "protocyte/options.proto"; '
            "message Dependency {}\n"
        ),
        encoding="utf-8",
    )

    import_roots = [
        str(proto_root),
        str(protocyte_proto_dir),
        str(protobuf_import_dir),
    ]
    assert source_closure_requires_protobuf_imports([str(source_file)], import_roots)
    subprocess.run(
        [
            str(protoc),
            *(f"--proto_path={root}" for root in import_roots),
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=True,
    )


@pytest.mark.parametrize(
    "import_literal",
    [
        pytest.param(r'"\u0google/protobuf/any.proto"', id="short-u"),
        pytest.param(r'"\u006Zoogle/protobuf/any.proto"', id="non-hex-u"),
        pytest.param(r'"\U00110000google/protobuf/any.proto"', id="out-of-range-U"),
        pytest.param(r'"\ud800google/protobuf/any.proto"', id="lone-surrogate"),
    ],
)
def test_import_scanner_delegates_malformed_unicode_escapes_to_pinned_protoc(
    tmp_path: Path, import_literal: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_pinned_protoc_34_1(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    proto_root = tmp_path / "proto"
    proto_root.mkdir()
    source_file = proto_root / "demo.proto"
    source_file.write_text(
        f'syntax = "proto3"; import {import_literal}; message Demo {{}}\n',
        encoding="utf-8",
    )

    assert not source_closure_requires_protobuf_imports(
        [str(source_file)], [str(proto_root), str(protobuf_import_dir)]
    )
    protoc_result = subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_root}",
            f"--proto_path={protobuf_import_dir}",
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        cwd=proto_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert protoc_result.returncode != 0


@pytest.mark.parametrize("escaped_default", [r"\000", r"\777"])
def test_real_protoc_accepts_non_import_octal_bytes_defaults(
    tmp_path: Path, escaped_default: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    proto_dir = tmp_path / "proto"
    proto_dir.mkdir()
    (proto_dir / "demo.proto").write_text(
        (
            'syntax = "proto2"; message Demo { '
            f'optional bytes payload = 1 [default = "{escaped_default}"]; }}\n'
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            str(protoc),
            f"--proto_path={proto_dir}",
            f"--descriptor_set_out={tmp_path / 'descriptor-set.pb'}",
            "demo.proto",
        ],
        check=True,
    )


def test_source_import_preflight_preserves_semicolon_paths_in_closure(
    tmp_path: Path,
) -> None:
    result = _configure_source_import_preflight(
        tmp_path,
        'syntax = "proto3"; import "dep;legacy.proto"; message Demo {}\n',
        proto_name="entry;point.proto",
        extra_files={
            "proto/dep;legacy.proto": (
                'syntax = "proto3"; /* import "protocyte/options.proto"; */ message Legacy {}\n'
            )
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_relocated_install_provisions_managed_python_environment(
    tmp_path: Path,
) -> None:
    _build_dir, prefix = _configure_fetchcontent_install_fixture(
        tmp_path,
        protocyte_install=True,
    )
    relocated_prefix = tmp_path / "relocated-prefix"
    prefix.replace(relocated_prefix)
    source_dir = tmp_path / "installed-consumer"
    build_dir = tmp_path / "installed-consumer-build"
    environment_root = tmp_path / "installed-managed-environments"
    source_dir.mkdir()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(protocyte_installed_managed_environment LANGUAGES NONE)",
                f'set(Python3_EXECUTABLE "{Path(sys.executable).as_posix()}")',
                f'set(PROTOCYTE_PYTHON_ENV_ROOT "{environment_root.as_posix()}")',
                "find_package(protocyte CONFIG REQUIRED)",
                "_protocyte_prepare_plugin()",
                "_protocyte_get_internal(managed_plugin PLUGIN_EXECUTABLE)",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/managed-plugin.txt" "${managed_plugin}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    configured = subprocess.run(
        [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            f"-DCMAKE_PREFIX_PATH={relocated_prefix}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=900,
    )

    assert configured.returncode == 0, configured.stdout + configured.stderr
    plugin = Path(
        (build_dir / "managed-plugin.txt").read_text(encoding="utf-8").strip()
    )
    assert plugin.is_file()
    assert (
        subprocess.run(
            [str(plugin), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == __version__
    )
    _assert_no_managed_environment_transaction_leftovers(environment_root)


@pytest.mark.parametrize("library_mode", ["source", "descriptor-set"])
def test_proto_library_installs_exports_and_reconsumes_from_relocated_prefix(
    tmp_path: Path,
    library_mode: str,
) -> None:
    if shutil.which("ninja") is None:
        _real_protoc_requirement_unavailable(
            "Ninja is required for the install/export integration test",
            additional_required_env=_CI_REQUIRE_INSTALL_EXPORT_TEST_ENV,
        )

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(
        repo_root,
        additional_required_env=_CI_REQUIRE_INSTALL_EXPORT_TEST_ENV,
    )
    protobuf_import_dir = _find_protobuf_import_dir(
        repo_root,
        protoc,
        additional_required_env=_CI_REQUIRE_INSTALL_EXPORT_TEST_ENV,
    )
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
                "set(CMAKE_DISABLE_FIND_PACKAGE_Python3 TRUE)",
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


def test_include_prefix_library_builds_installs_and_relocates_transitive_headers(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required for the include-prefix integration test")

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    (tmp_path / "tools").mkdir()
    plugin = _write_python_plugin_wrapper(
        tmp_path / "tools" / "protoc-gen-protocyte", repo_root
    )
    provider_source_dir = tmp_path / "provider"
    provider_build_dir = tmp_path / "provider-build"
    install_prefix = tmp_path / "install"
    relocated_prefix = tmp_path / "relocated-install"
    consumer_source_dir = tmp_path / "consumer"
    consumer_build_dir = tmp_path / "consumer-build"

    proto_dir = provider_source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "common.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package include_contract.common;",
                "message Header { uint32 version = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (proto_dir / "demo.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package include_contract.demo;",
                'import "common.proto";',
                "message Envelope { include_contract.common.Header header = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (provider_source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(include_prefix_provider LANGUAGES CXX)",
                "include(GNUInstallDirs)",
                "set(PROTOCYTE_INSTALL ON)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                f'add_subdirectory("{repo_root.as_posix()}" protocyte-core)',
                "protocyte_add_proto_library(",
                "    TARGET include_prefix_proto",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    INCLUDE_PREFIX vendor/wire",
                "    DISCOVER",
                "    EMIT_RUNTIME",
                "    HOSTED_ALLOCATOR",
                '    INSTALL_INCLUDE_DIR "${CMAKE_INSTALL_INCLUDEDIR}"',
                "    OPTIONS format=off",
                ")",
                "set_target_properties(include_prefix_proto PROPERTIES EXPORT_NAME proto)",
                "install(",
                "    TARGETS include_prefix_proto",
                "    EXPORT includePrefixTargets",
                '    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"',
                "    FILE_SET protocyte_generated_headers",
                '        DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"',
                ")",
                "install(",
                "    EXPORT includePrefixTargets",
                "    NAMESPACE include_prefix::",
                '    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/include_prefix"',
                ")",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/include_prefixConfig.cmake" [=[',
                "include(CMakeFindDependencyMacro)",
                "find_dependency(protocyte CONFIG)",
                'include("${CMAKE_CURRENT_LIST_DIR}/includePrefixTargets.cmake")',
                "]=])",
                "install(",
                '    FILES "${CMAKE_CURRENT_BINARY_DIR}/include_prefixConfig.cmake"',
                '    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/include_prefix"',
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
            f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(provider_build_dir)], check=True)
    subprocess.run(["cmake", "--install", str(provider_build_dir)], check=True)

    generated_root = provider_build_dir / "generated" / "vendor" / "wire"
    assert (generated_root / "common.protocyte.hpp").is_file()
    assert (generated_root / "demo.protocyte.hpp").is_file()
    installed_header = install_prefix / "include/vendor/wire/demo.protocyte.hpp"
    installed_common = install_prefix / "include/vendor/wire/common.protocyte.hpp"
    installed_runtime = (
        install_prefix / "include/vendor/wire/protocyte/runtime/runtime.hpp"
    )
    assert installed_header.is_file()
    assert installed_common.is_file()
    assert installed_runtime.is_file()
    assert '#include "vendor/wire/common.protocyte.hpp"' in installed_header.read_text(
        encoding="utf-8"
    )
    exported_targets = (
        (install_prefix / "lib/cmake/include_prefix/includePrefixTargets.cmake")
        .read_text(encoding="utf-8")
        .replace("\\", "/")
    )
    assert provider_build_dir.as_posix() not in exported_targets

    shutil.rmtree(provider_build_dir)
    shutil.rmtree(provider_source_dir)
    install_prefix.rename(relocated_prefix)

    consumer_source_dir.mkdir()
    (consumer_source_dir / "main.cpp").write_text(
        "\n".join(
            [
                "#include <type_traits>",
                '#include "vendor/wire/demo.protocyte.hpp"',
                "static_assert(std::is_class_v<::include_contract::demo::Envelope<>>);",
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
                "project(include_prefix_consumer LANGUAGES CXX)",
                "find_package(include_prefix CONFIG REQUIRED)",
                "add_executable(consumer main.cpp)",
                "target_link_libraries(consumer PRIVATE include_prefix::proto)",
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


@pytest.mark.parametrize(
    ("files", "expected_error"),
    [
        ({}, "which is not an existing directory"),
        (
            {"protobuf/README.txt": "not a protobuf import tree\n"},
            "does not contain google/protobuf/descriptor.proto",
        ),
        (
            {
                "protobuf/google/protobuf/descriptor.proto/marker.txt": (
                    "descriptor.proto is a directory\n"
                )
            },
            "google/protobuf/descriptor.proto' is a directory; an existing file is required",
        ),
    ],
)
def test_explicit_protobuf_import_root_reports_invalid_path_immediately(
    tmp_path: Path,
    files: dict[str, str],
    expected_error: str,
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "protobuf")',
                '_protocyte_resolve_protobuf_import_dir(is_explicit "test-toolchain")',
            ]
        ),
        files=files,
    )

    output = " ".join((result.stdout + result.stderr).split())
    resolved = (tmp_path / "project" / "protobuf").as_posix()
    assert result.returncode != 0
    assert "PROTOCYTE_PROTOBUF_IMPORT_DIR 'protobuf' resolves to" in output
    assert resolved in output.replace("\\", "/")
    assert expected_error in output


@pytest.mark.parametrize(
    "namespace_prefix",
    [
        "::vendor::wire",
        "vendor::wire::",
        "vendor::::wire",
        "vendor:wire",
        "vendor:: wire",
        "vendor::_wire",
        "vendor::wire__detail",
        "vendor::class",
        "vendor::naïve",
    ],
)
def test_cmake_preflights_invalid_namespace_prefixes(
    tmp_path: Path, namespace_prefix: str
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "protocyte_generate(",
                "    TARGET demo_codegen",
                "    PROTO_ROOT proto",
                "    OUT_DIR generated",
                "    PROTOS proto/demo.proto",
                f'    NAMESPACE_PREFIX "{namespace_prefix}"',
                ")",
            ]
        ),
        files={"proto/demo.proto": 'syntax = "proto3"; message Demo {}\n'},
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "NAMESPACE_PREFIX must be a normalized '::'-separated namespace" in output
    assert "portable, non-reserved C++ identifiers" in output


def test_cmake_accepts_portable_namespace_prefix_before_codegen(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    plugin = _write_python_plugin_wrapper(
        tmp_path / "tools" / "protoc-gen-protocyte", repo_root
    )
    protoc = tmp_path / "tools" / "protoc"
    protoc.write_text("", encoding="utf-8")

    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_VERSION "{__version__}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                "    PROTO_ROOT proto",
                "    OUT_DIR generated",
                "    PROTOS proto/demo.proto",
                "    NAMESPACE_PREFIX vendor::wire_2",
                "    OPTIONS format=off",
                ")",
            ]
        ),
        files={"proto/demo.proto": 'syntax = "proto3"; message Demo {}\n'},
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "function_name",
    [
        "protocyte_generate",
        "protocyte_add_proto_library",
        "protocyte_add_descriptor_set_library",
    ],
)
def test_cmake_rejects_namespace_prefix_in_forwarded_options(
    tmp_path: Path, function_name: str
) -> None:
    result = _configure_cmake_snippet(
        tmp_path,
        f'{function_name}(OPTIONS "format=off,namespace_prefix=vendor::::wire")',
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "OPTIONS must not set namespace_prefix; use NAMESPACE_PREFIX" in output
    assert "validate the generated C++ namespace during configuration" in output


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


@pytest.mark.parametrize("variable_storage", ["normal", "cache"])
def test_explicit_host_protoc_overrides_target_when_cross_compiling(
    tmp_path: Path,
    variable_storage: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    host_protoc = _write_runnable_host_protoc(source_dir / "host-toolchain")
    target_protoc = source_dir / "target-toolchain" / "bin" / "protoc"
    target_protoc.parent.mkdir(parents=True)
    target_protoc.write_text("", encoding="utf-8")
    selected = build_dir / "selected.txt"
    if variable_storage == "cache":
        protoc_setting = (
            f'set(Protobuf_PROTOC_EXECUTABLE "{host_protoc.as_posix()}" '
            'CACHE FILEPATH "")'
        )
    else:
        protoc_setting = f'set(Protobuf_PROTOC_EXECUTABLE "{host_protoc.as_posix()}")'

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_host_protoc LANGUAGES NONE)",
                "if(NOT CMAKE_CROSSCOMPILING)",
                '    message(FATAL_ERROR "fixture did not configure as a cross build")',
                "endif()",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "add_executable(protobuf::protoc IMPORTED)",
                f'set_target_properties(protobuf::protoc PROPERTIES IMPORTED_LOCATION "{target_protoc.as_posix()}")',
                protoc_setting,
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


@pytest.mark.parametrize("variable_storage", ["normal", "cache"])
def test_cross_compile_rejects_non_runnable_explicit_protoc(
    tmp_path: Path,
    variable_storage: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    target_protoc = _write_protobuf_toolchain(source_dir / "target-toolchain")
    if variable_storage == "cache":
        protoc_setting = (
            f'set(Protobuf_PROTOC_EXECUTABLE "{target_protoc.as_posix()}" '
            'CACHE FILEPATH "")'
        )
    else:
        protoc_setting = f'set(Protobuf_PROTOC_EXECUTABLE "{target_protoc.as_posix()}")'

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_explicit_protoc_probe LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                protoc_setting,
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(source_dir / "target-toolchain" / "include").as_posix()}")',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "_protocyte_ensure_protobuf(FALSE)",
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
    output = " ".join((result.stdout + result.stderr).split())

    assert result.returncode != 0
    assert (
        "requires Protobuf_PROTOC_EXECUTABLE to name a host-runnable compiler" in output
    )
    assert "Protobuf_PROTOC_EXECUTABLE is not host-runnable" in output
    assert target_protoc.as_posix() in output


@pytest.mark.parametrize("host_runnable", [True, False])
def test_cross_compile_probes_protoc_inherited_from_prior_find_package(
    tmp_path: Path,
    host_runnable: bool,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    toolchain_root = source_dir / "protobuf-package"
    if host_runnable:
        package_protoc = _write_runnable_host_protoc(toolchain_root)
    else:
        package_protoc = _write_protobuf_toolchain(toolchain_root)
    package_dir = toolchain_root / "lib" / "cmake" / "protobuf"
    package_dir.mkdir(parents=True)
    (package_dir / "ProtobufConfig.cmake").write_text(
        f'set(Protobuf_PROTOC_EXECUTABLE "{package_protoc.as_posix()}")\n',
        encoding="utf-8",
    )
    selected = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_inherited_protoc_probe LANGUAGES NONE)",
                f'find_package(Protobuf CONFIG REQUIRED PATHS "{package_dir.as_posix()}" NO_DEFAULT_PATH)',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(toolchain_root / "include").as_posix()}")',
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

    if host_runnable:
        assert result.returncode == 0, result.stdout + result.stderr
        assert selected.read_text(encoding="utf-8").splitlines() == [
            package_protoc.as_posix(),
            package_protoc.as_posix(),
        ]
    else:
        output = " ".join((result.stdout + result.stderr).split())
        assert result.returncode != 0
        assert "Protobuf_PROTOC_EXECUTABLE is not host-runnable" in output
        assert package_protoc.as_posix() in output


@pytest.mark.parametrize("shadow_variable", ["CMAKE_PROGRAM_PATH", "CMAKE_PREFIX_PATH"])
def test_cross_compile_host_lookup_ignores_cmake_target_search_paths(
    tmp_path: Path,
    shadow_variable: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    host_protoc = _write_runnable_host_protoc(source_dir / "host-toolchain")
    executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    if shadow_variable == "CMAKE_PROGRAM_PATH":
        shadow_root = source_dir / "target-programs"
        target_protoc = shadow_root / executable_name
    else:
        shadow_root = source_dir / "target-prefix"
        target_protoc = shadow_root / "bin" / executable_name
    target_protoc.parent.mkdir(parents=True)
    target_protoc.write_text("target-architecture executable\n", encoding="utf-8")
    if os.name != "nt":
        target_protoc.chmod(0o755)
    selected = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_path_only_protoc LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'set({shadow_variable} "{shadow_root.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(source_dir / "host-toolchain" / "include").as_posix()}")',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "_protocyte_ensure_protobuf(FALSE)",
                f'file(WRITE "{selected.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(host_protoc.parent), env.get("PATH", "")])

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
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert selected.read_text(encoding="utf-8").splitlines() == [
        host_protoc.as_posix(),
        host_protoc.as_posix(),
    ]


def test_cross_compile_host_path_precedes_target_protobuf_package(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    host_protoc = _write_runnable_host_protoc(source_dir / "host-toolchain")
    target_executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    target_protoc = source_dir / "target-sysroot" / "bin" / target_executable_name
    target_protoc.parent.mkdir(parents=True)
    target_protoc.write_text("target-architecture executable\n", encoding="utf-8")
    protobuf_package = source_dir / "target-sysroot" / "lib" / "cmake" / "protobuf"
    _write_target_protobuf_package(protobuf_package, target_protoc)
    selected = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_path_host_protoc LANGUAGES NONE)",
                "if(NOT CMAKE_CROSSCOMPILING)",
                '    message(FATAL_ERROR "fixture did not configure as a cross build")',
                "endif()",
                f'find_package(Protobuf CONFIG REQUIRED PATHS "{protobuf_package.as_posix()}" NO_DEFAULT_PATH)',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "_protocyte_ensure_protobuf(FALSE)",
                f'file(WRITE "{selected.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([str(host_protoc.parent), env.get("PATH", "")])

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
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert selected.read_text(encoding="utf-8").splitlines() == [
        host_protoc.as_posix(),
        host_protoc.as_posix(),
    ]


def test_cross_compile_rejects_target_protoc_and_its_emulator(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    target_executable_name = "protoc.exe" if os.name == "nt" else "protoc"
    target_protoc = source_dir / "target-sysroot" / "bin" / target_executable_name
    target_protoc.parent.mkdir(parents=True)
    target_protoc.write_text("target-architecture executable\n", encoding="utf-8")
    protobuf_package = source_dir / "target-sysroot" / "lib" / "cmake" / "protobuf"
    _write_target_protobuf_package(protobuf_package, target_protoc)

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_target_protoc_rejection LANGUAGES NONE)",
                f'find_package(Protobuf CONFIG REQUIRED PATHS "{protobuf_package.as_posix()}" NO_DEFAULT_PATH)',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "set(CMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH FALSE)",
                "set(CMAKE_FIND_USE_CMAKE_PATH FALSE)",
                "set(CMAKE_FIND_USE_CMAKE_SYSTEM_PATH FALSE)",
                "set(CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH FALSE)",
                'set(ENV{PATH} "")',
                "_protocyte_ensure_protobuf(FALSE)",
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
    output = " ".join((result.stdout + result.stderr).split())

    assert result.returncode != 0
    assert "could not find a host-runnable protoc while cross-compiling" in output
    assert "target 'protobuf::protoc'" in output
    assert "is not host-runnable" in output
    assert target_protoc.as_posix() in output
    assert "target emulators are not propagated" in output


def test_cross_compile_accepts_host_runnable_imported_protoc_target(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    host_protoc = _write_runnable_host_protoc(source_dir / "host-toolchain")
    protobuf_package = source_dir / "host-toolchain" / "lib" / "cmake" / "protobuf"
    _write_target_protobuf_package(protobuf_package, host_protoc)
    selected = build_dir / "selected.txt"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_imported_host_protoc LANGUAGES NONE)",
                f'find_package(Protobuf CONFIG REQUIRED PATHS "{protobuf_package.as_posix()}" NO_DEFAULT_PATH)',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "set(CMAKE_FIND_USE_CMAKE_ENVIRONMENT_PATH FALSE)",
                "set(CMAKE_FIND_USE_CMAKE_PATH FALSE)",
                "set(CMAKE_FIND_USE_CMAKE_SYSTEM_PATH FALSE)",
                "set(CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH FALSE)",
                'set(ENV{PATH} "")',
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


def test_cross_compile_imported_multiconfig_mapping_tracks_selected_file(
    tmp_path: Path,
) -> None:
    cmake = shutil.which("cmake")
    ninja = shutil.which("ninja")
    if cmake is None or ninja is None:
        pytest.skip("CMake and Ninja are required for the multi-config mapping test")
    cmake_help = subprocess.run(
        [cmake, "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if "Ninja Multi-Config" not in cmake_help:
        pytest.skip("CMake does not provide the Ninja Multi-Config generator")

    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    empty_path = source_dir / "empty-path"
    empty_path.mkdir()
    debug_protoc = _write_runnable_host_protoc(source_dir / "debug-toolchain")
    release_protoc = _write_runnable_host_protoc(source_dir / "release-toolchain")
    selected = build_dir / "selected.txt"
    generated_stamp = build_dir / "generated.stamp"

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(cross_imported_multiconfig LANGUAGES NONE)",
                "add_executable(protobuf::protoc IMPORTED)",
                "set_target_properties(",
                "    protobuf::protoc",
                "    PROPERTIES",
                '        IMPORTED_CONFIGURATIONS "Debug;Release"',
                f'        IMPORTED_LOCATION_DEBUG "{debug_protoc.as_posix()}"',
                f'        IMPORTED_LOCATION_RELEASE "{release_protoc.as_posix()}"',
                '        MAP_IMPORTED_CONFIG_DEBUG "Missing;Release"',
                ")",
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{(source_dir / "release-toolchain" / "include").as_posix()}")',
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "_protocyte_ensure_protobuf(FALSE)",
                f'file(WRITE "{selected.as_posix()}" "${{PROTOCYTE_PROTOC_EXECUTABLE}}\n${{PROTOCYTE_PROTOC_DEPENDENCY}}\n")',
                "add_custom_command(",
                f'    OUTPUT "{generated_stamp.as_posix()}"',
                f'    COMMAND "${{PROTOCYTE_PROTOC_EXECUTABLE}}" -E touch "{generated_stamp.as_posix()}"',
                '    DEPENDS "${PROTOCYTE_PROTOC_DEPENDENCY}"',
                "    VERBATIM",
                ")",
                f'add_custom_target(generate ALL DEPENDS "{generated_stamp.as_posix()}")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = str(empty_path)
    subprocess.run(
        [
            cmake,
            "-G",
            "Ninja Multi-Config",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            "-DCMAKE_SYSTEM_NAME=Generic",
            "-DCMAKE_CONFIGURATION_TYPES=Debug",
            f"-DCMAKE_MAKE_PROGRAM={Path(ninja).as_posix()}",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert selected.read_text(encoding="utf-8").splitlines() == [
        release_protoc.as_posix(),
        release_protoc.as_posix(),
    ]
    build_command = [cmake, "--build", str(build_dir), "--config", "Debug"]
    subprocess.run(build_command, check=True, env=env)
    initial_stamp_mtime = generated_stamp.stat().st_mtime_ns

    _touch_newer_than(debug_protoc, generated_stamp)
    subprocess.run(build_command, check=True, env=env)
    assert generated_stamp.stat().st_mtime_ns == initial_stamp_mtime

    _touch_newer_than(release_protoc, generated_stamp)
    subprocess.run(build_command, check=True, env=env)
    assert generated_stamp.stat().st_mtime_ns > initial_stamp_mtime


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
                "if(TARGET protobuf::protoc)",
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
        'syntax = "proto3"; import "base.proto"; message Demo {}\n',
        encoding="utf-8",
    )
    (proto_dir / "base.proto").write_text(
        'syntax = "proto3"; import "protocyte/options.proto"; message Base {}\n',
        encoding="utf-8",
    )
    protoc = source_dir / "tools" / "protoc"
    protoc.parent.mkdir()
    protoc.write_text("", encoding="utf-8")
    plugin = _write_python_plugin_wrapper(
        source_dir / "tools" / "protoc-gen-protocyte", repo_root
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

    assert (
        resolved_output.read_text(encoding="utf-8")
        == (fetched_source / "src").as_posix()
    )


def test_fetch_fallback_import_sources_build_with_real_protoc(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        _real_protoc_requirement_unavailable(
            "Ninja is required to verify fetched import source generation"
        )
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
        'syntax = "proto3"; import "protocyte/options.proto"; message Demo {}\n',
        encoding="utf-8",
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

    assert (
        resolved_output.read_text(encoding="utf-8")
        == (fetched_source / "src").as_posix()
    )


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
    plugin = _write_python_plugin_wrapper(
        source_dir / "tools" / "protoc-gen-protocyte", repo_root
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
        assert (
            selected_output.read_text(encoding="utf-8").splitlines()
            == expected_selection
        )


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
        assert (
            selected_output.read_text(encoding="utf-8").splitlines()
            == expected_selection
        )


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
                "if(DEFINED PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR)",
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
        'syntax = "proto3"; import "protocyte/options.proto"; message Demo {}\n',
        encoding="utf-8",
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
    stale_include_descriptor = (
        stale_include / "google" / "protobuf" / "descriptor.proto"
    )
    stale_include_descriptor.parent.mkdir(parents=True)
    stale_include_descriptor.write_text('syntax = "proto3";\n', encoding="utf-8")
    plugin = _write_python_plugin_wrapper(
        source_dir / "tools" / "protoc-gen-protocyte", repo_root
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


def test_cmake_discovery_json_preserves_semicolon_descriptor_name(
    tmp_path: Path,
) -> None:
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


@pytest.mark.parametrize("name", ["a:b.proto", "C:foo.proto"])
def test_cmake_descriptor_name_validator_accepts_relative_colon_names(
    tmp_path: Path, name: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "descriptor_name_validator.cmake"
    output = tmp_path / "unsafe.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'_protocyte_descriptor_name_is_unsafe(unsafe "{name}")',
                f'file(WRITE "{output.as_posix()}" "${{unsafe}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert output.read_text(encoding="utf-8") == "FALSE"


def test_cmake_descriptor_name_validator_rejects_rooted_drive_path(
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
                '_protocyte_descriptor_name_is_unsafe(unsafe "C:/foo.proto")',
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
    plugin = _write_python_plugin_wrapper(
        source_dir / "tools" / "protoc-gen-protocyte", repo_root
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
        text for text in response_texts if "--plugin=protoc-gen-protocyte=" in text
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
    ("proto_name", "use_explicit_import_root"),
    [
        pytest.param("demo.proto", False, id="normal-unset-root"),
        pytest.param("demo;legacy.proto", False, id="semicolon-unset-root"),
        pytest.param("demo.proto", True, id="normal-explicit-root"),
    ],
)
def test_import_free_source_codegen_handles_unset_and_explicit_proto_paths(
    tmp_path: Path, proto_name: str, use_explicit_import_root: bool
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = (
        _find_protobuf_import_dir(repo_root, real_protoc)
        if use_explicit_import_root
        else None
    )
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    (proto_dir / proto_name).write_text(
        'syntax = "proto3"; package demo; message ImportFree {}\n',
        encoding="utf-8",
    )
    invocation_log = source_dir / "protoc-invocations.txt"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    protobuf_import_setting = (
        [f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")']
        if protobuf_import_dir is not None
        else []
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(import_free_source LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                *protobuf_import_setting,
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                f"    PROTOS [==[proto/{proto_name}]==]",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
    )

    generated_header = (
        build_dir / "generated" / f"{generated_file_base(proto_name)}.hpp"
    )
    assert generated_header.is_file()
    response_texts = [
        path.read_text(encoding="utf-8")
        for path in (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
    ]
    assert response_texts
    assert all(
        "--proto_path=" not in response.splitlines() for response in response_texts
    )
    if protobuf_import_dir is not None:
        expected_import_argument = f"--proto_path={protobuf_import_dir.as_posix()}"
        assert any(
            expected_import_argument in response.splitlines()
            for response in response_texts
        )
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
    ]


def _protoc_response_lines_for_source(
    build_dir: Path, source_file: Path
) -> list[list[str]]:
    source_argument = source_file.resolve().as_posix()
    responses = []
    for response_file in (build_dir / "CMakeFiles" / "protocyte-arguments").glob(
        "*.rsp"
    ):
        lines = response_file.read_text(encoding="utf-8").splitlines()
        if source_argument in lines:
            responses.append(lines)
    return responses


def test_automatic_protobuf_import_root_is_removed_after_true_to_false_reconfigure(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify protobuf-root reconfiguration"
        )
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    source_file = proto_dir / "demo.proto"
    source_file.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "google/protobuf/any.proto";',
                "message UsesAny { google.protobuf.Any value = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(protobuf_root_true_to_false LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
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
    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    subprocess.run(build_command, check=True)
    protobuf_argument = f"--proto_path={protobuf_import_dir.resolve().as_posix()}"
    initial_responses = _protoc_response_lines_for_source(build_dir, source_file)
    assert len(initial_responses) == 2
    assert all(protobuf_argument in response for response in initial_responses)

    source_file.write_text(
        'syntax = "proto3"; package demo; message ImportFree {}\n',
        encoding="utf-8",
    )
    rebuilt = subprocess.run(build_command, check=False, capture_output=True, text=True)
    assert rebuilt.returncode == 0, rebuilt.stdout + rebuilt.stderr
    assert "Re-running CMake" in rebuilt.stdout + rebuilt.stderr
    final_responses = _protoc_response_lines_for_source(build_dir, source_file)
    assert len(final_responses) == 2
    assert all(protobuf_argument not in response for response in final_responses)
    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert "PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR:INTERNAL=" in cache

    no_op = subprocess.run(build_command, check=True, capture_output=True, text=True)
    assert "Scanning protobuf imports" not in no_op.stdout + no_op.stderr


@pytest.mark.parametrize(
    "target_order",
    [("uses_any", "import_free"), ("import_free", "uses_any")],
    ids=["true-then-false", "false-then-true"],
)
def test_mixed_source_targets_select_automatic_protobuf_root_per_call(
    tmp_path: Path, target_order: tuple[str, str]
) -> None:
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify mixed protobuf-root targets"
        )
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    source_files = {
        "uses_any": proto_dir / "uses_any.proto",
        "import_free": proto_dir / "import_free.proto",
    }
    source_files["uses_any"].write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "google/protobuf/any.proto";',
                "message UsesAny { google.protobuf.Any value = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    source_files["import_free"].write_text(
        'syntax = "proto3"; package demo; message ImportFree {}\n',
        encoding="utf-8",
    )
    cmake_lines = [
        "cmake_minimum_required(VERSION 3.24)",
        "project(mixed_protobuf_roots LANGUAGES NONE)",
        "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
        "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
        f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
        f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
        f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
    ]
    for name in target_order:
        cmake_lines.extend(
            [
                "protocyte_generate(",
                f"    TARGET {name}_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                f'    OUT_DIR "${{CMAKE_CURRENT_BINARY_DIR}}/generated-{name}"',
                f"    PROTOS proto/{name}.proto",
                "    OPTIONS format=off",
                ")",
            ]
        )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join([*cmake_lines, ""]), encoding="utf-8"
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
            "uses_any_codegen",
            "import_free_codegen",
        ],
        check=True,
    )
    protobuf_argument = f"--proto_path={protobuf_import_dir.resolve().as_posix()}"
    uses_any_responses = _protoc_response_lines_for_source(
        build_dir, source_files["uses_any"]
    )
    import_free_responses = _protoc_response_lines_for_source(
        build_dir, source_files["import_free"]
    )
    assert len(uses_any_responses) == 2
    assert len(import_free_responses) == 2
    assert all(protobuf_argument in response for response in uses_any_responses)
    assert all(protobuf_argument not in response for response in import_free_responses)


@pytest.mark.parametrize("transition", ["direct", "transitive"])
def test_source_closure_false_to_true_edit_reconfigures_before_dependency_scan(
    tmp_path: Path, transition: str
) -> None:
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify source-closure preflight reconfiguration"
        )
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    invocation_log = source_dir / "protoc-invocations.log"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    import_arguments: list[str] = []
    entry_name = "entry;point.proto" if transition == "direct" else "entry.proto"
    entry_file = proto_dir / entry_name
    if transition == "direct":
        edited_file = entry_file
        entry_file.write_text(
            'syntax = "proto3"; package demo; message ImportFree {}\n',
            encoding="utf-8",
        )
    else:
        import_dir = source_dir / "imports;external"
        import_dir.mkdir()
        edited_file = import_dir / "dependency.schema"
        edited_file.write_text(
            'syntax = "proto3"; package demo; message Dependency {}\n',
            encoding="utf-8",
        )
        entry_file.write_text(
            "\n".join(
                [
                    'syntax = "proto3";',
                    "package demo;",
                    'import "dependency.schema";',
                    "message Entry { Dependency value = 1; }",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        import_arguments.append(
            '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports;external"'
        )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(source_closure_false_to_true LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                f"    PROTOS [==[proto/{entry_name}]==]",
                *import_arguments,
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
    if transition == "direct":
        subprocess.run(build_command, check=True)

    edited_file.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "google/protobuf/any.proto";',
                "message UsesAny { google.protobuf.Any value = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rebuilt = subprocess.run(build_command, check=False, capture_output=True, text=True)
    output = rebuilt.stdout + rebuilt.stderr
    assert rebuilt.returncode != 0
    assert "Re-running CMake" in output
    assert (
        "protocyte_generate could not locate google/protobuf/descriptor.proto" in output
    )
    assert "google/protobuf/any.proto: File not found" not in output
    assert "Scanning protobuf imports" not in output


def test_missing_non_proto_import_addition_reconfigures_into_preflight(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify missing-import topology reconfiguration"
        )
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    entry_file = proto_dir / "entry.proto"
    entry_file.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "dependency.schema";',
                "message Entry { Dependency value = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    invocation_log = source_dir / "protoc-invocations.log"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(missing_non_proto_import LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/entry.proto",
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
    (proto_dir / "dependency.schema").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "google/protobuf/any.proto";',
                "message Dependency { google.protobuf.Any value = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rebuilt = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = rebuilt.stdout + rebuilt.stderr
    assert rebuilt.returncode != 0
    assert "Re-running CMake" in output
    assert (
        "protocyte_generate could not locate google/protobuf/descriptor.proto" in output
    )
    assert "dependency.schema: File not found" not in output
    assert "Scanning protobuf imports" not in output


@pytest.mark.parametrize("descriptor_root", ["proto-root", "import-dirs"])
def test_declared_import_root_descriptor_suppresses_automatic_protobuf_fetch(
    tmp_path: Path, descriptor_root: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    fetched_source = source_dir / "unexpected-fetch"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    fetched_source.mkdir()
    (fetched_source / "CMakeLists.txt").write_text(
        'message(FATAL_ERROR "unexpected protobuf import fetch")\n', encoding="utf-8"
    )
    if descriptor_root == "proto-root":
        descriptor = proto_dir / "google" / "protobuf" / "descriptor.proto"
        import_arguments: list[str] = []
    else:
        import_dir = source_dir / "imports"
        descriptor = import_dir / "google" / "protobuf" / "descriptor.proto"
        import_arguments = ['    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports"']
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text(
        'syntax = "proto3"; package google.protobuf; message FileDescriptorProto {}\n',
        encoding="utf-8",
    )
    (proto_dir / "entry.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "google/protobuf/descriptor.proto";',
                "message Entry { google.protobuf.FileDescriptorProto value = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    protoc = tools_dir / ("protoc.exe" if os.name == "nt" else "protoc")
    protoc.write_text("", encoding="utf-8")
    if os.name != "nt":
        protoc.chmod(0o755)
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(caller_descriptor_root LANGUAGES NONE)",
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
                "    PROTOS proto/entry.proto",
                *import_arguments,
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )
    configured = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert configured.returncode == 0, configured.stdout + configured.stderr
    assert (
        "unexpected protobuf import fetch" not in configured.stdout + configured.stderr
    )
    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert "PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR" not in cache
    assert "PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR" not in cache


@pytest.mark.parametrize(
    "root_source",
    [
        pytest.param("proto-root", id="proto-root"),
        pytest.param("import-dirs", id="import-dirs"),
        pytest.param("explicit-protobuf", id="explicit-protobuf-root"),
    ],
)
def test_source_codegen_preserves_semicolon_import_roots_end_to_end(
    tmp_path: Path, root_source: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    tools_dir = source_dir / "tools"
    proto_dir_name = "proto;root" if root_source == "proto-root" else "proto"
    proto_dir = source_dir / proto_dir_name
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    cmake_settings: list[str] = []
    generate_arguments: list[str] = []

    if root_source == "import-dirs":
        import_dir = source_dir / "imports;external"
        import_dir.mkdir()
        (import_dir / "shared.proto").write_text(
            'syntax = "proto3"; package demo; message Shared {}\n',
            encoding="utf-8",
        )
        source = (
            'syntax = "proto3"; package demo; import "shared.proto"; '
            "message Demo { Shared value = 1; }\n"
        )
        generate_arguments.append(
            '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports;external"'
        )
        expected_semicolon_root = import_dir
    elif root_source == "explicit-protobuf":
        canonical_import_dir = _find_protobuf_import_dir(repo_root, protoc)
        explicit_import_dir = source_dir / "protobuf;imports"
        descriptor_dir = explicit_import_dir / "google" / "protobuf"
        descriptor_dir.mkdir(parents=True)
        shutil.copy2(
            canonical_import_dir / "google" / "protobuf" / "descriptor.proto",
            descriptor_dir / "descriptor.proto",
        )
        source = (
            'syntax = "proto3"; package demo; '
            'import "google/protobuf/descriptor.proto"; '
            "message Demo { google.protobuf.FileDescriptorProto value = 1; }\n"
        )
        cmake_settings.append(
            'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/protobuf;imports")'
        )
        expected_semicolon_root = explicit_import_dir
    else:
        source = 'syntax = "proto3"; package demo; message Demo {}\n'
        expected_semicolon_root = proto_dir

    proto_file = proto_dir / "demo.proto"
    proto_file.write_text(source, encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(semicolon_import_roots LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                *cmake_settings,
                "protocyte_generate(",
                "    TARGET demo_codegen",
                f'    PROTO_ROOT "${{CMAKE_CURRENT_SOURCE_DIR}}/{proto_dir_name}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                f"    PROTOS [==[{proto_dir_name}/demo.proto]==]",
                *generate_arguments,
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_command = ["cmake", "-S", str(source_dir), "-B", str(build_dir)]
    subprocess.run(configure_command, check=True)
    build = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "MSB8064" not in build.stdout + build.stderr
    assert (build_dir / "generated" / "demo.protocyte.hpp").is_file()
    response_texts = [
        path.read_text(encoding="utf-8")
        for path in (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
    ]
    assert response_texts
    expected_argument = f"--proto_path={expected_semicolon_root.resolve().as_posix()}"
    if os.name == "nt":
        proxy_marker = "/CMakeFiles/protocyte-protoc-import-roots/"
        assert all(
            expected_argument not in response.splitlines()
            for response in response_texts
        )
        assert all(
            any(
                proxy_marker in line.replace("\\", "/")
                for line in response.splitlines()
                if line.startswith("--proto_path=")
            )
            for response in response_texts
        )
        assert all(
            ";" not in line
            for response in response_texts
            for line in response.splitlines()
            if line.startswith("--proto_path=")
        )
    else:
        assert all(
            expected_argument in response.splitlines() for response in response_texts
        )

    subprocess.run(configure_command, check=True)
    reconfigured_build = subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "MSB8064" not in reconfigured_build.stdout + reconfigured_build.stderr


def _protoc_safe_import_root_alias(build_dir: Path, import_root: Path) -> Path:
    import_root_key = hashlib.sha256(
        import_root.resolve().as_posix().encode()
    ).hexdigest()
    return build_dir / "CMakeFiles" / "protocyte-protoc-import-roots" / import_root_key


def _write_protoc_safe_import_root_project(
    source_dir: Path,
    *,
    protoc: Path,
    plugin: Path,
    between_generate_calls: tuple[str, ...] = (),
) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    proto_dir = source_dir / "proto;root"
    proto_dir.mkdir(parents=True, exist_ok=True)
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package demo; message Expected {}\n',
        encoding="utf-8",
    )
    cmake_lines = [
        "cmake_minimum_required(VERSION 3.24)",
        "project(protoc_safe_import_root LANGUAGES NONE)",
        "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
        "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
        f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
        f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
        f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
        "protocyte_generate(",
        "    TARGET first_codegen",
        '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto;root"',
        '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated-first"',
        "    PROTOS [==[proto;root/demo.proto]==]",
        "    OPTIONS format=off",
        ")",
        *between_generate_calls,
    ]
    if between_generate_calls:
        cmake_lines.extend(
            [
                "protocyte_generate(",
                "    TARGET second_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto;root"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated-second"',
                "    PROTOS [==[proto;root/demo.proto]==]",
                "    OPTIONS format=off",
                ")",
            ]
        )
    cmake_lines.append("")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(cmake_lines),
        encoding="utf-8",
    )
    return proto_dir


@pytest.mark.skipif(os.name != "nt", reason="Windows protoc import-root alias")
def test_protoc_safe_import_root_rejects_preexisting_directory_without_modifying_it(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto;root"
    alias = _protoc_safe_import_root_alias(build_dir, proto_dir)
    alias.mkdir(parents=True)
    malicious_proto = alias / "demo.proto"
    malicious_content = 'syntax = "proto3"; message Hijacked {}\n'
    malicious_proto.write_text(malicious_content, encoding="utf-8")
    _write_protoc_safe_import_root_project(
        source_dir,
        protoc=protoc,
        plugin=plugin,
    )

    result = subprocess.run(
        ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    normalized_output = " ".join(output.split())
    assert result.returncode != 0
    assert "Protocyte refuses to reuse protoc-safe alias" in output
    assert "status: wrong-type" in output
    assert "Protocyte did not modify the existing entry" in normalized_output
    assert malicious_proto.read_text(encoding="utf-8") == malicious_content
    assert not alias.is_symlink()


@pytest.mark.skipif(os.name != "nt", reason="Windows protoc import-root alias")
def test_protoc_safe_import_root_rejects_wrong_target_without_modifying_it(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto;root"
    wrong_target = tmp_path / "wrong-target"
    wrong_target.mkdir()
    sentinel = wrong_target / "keep.txt"
    sentinel.write_text("keep\n", encoding="utf-8")
    alias = _protoc_safe_import_root_alias(build_dir, proto_dir)
    alias.parent.mkdir(parents=True)
    _create_generated_output_directory_link(alias, wrong_target)
    try:
        _write_protoc_safe_import_root_project(
            source_dir,
            protoc=protoc,
            plugin=plugin,
        )

        result = subprocess.run(
            ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
            check=False,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr
        normalized_output = " ".join(output.split())
        assert result.returncode != 0
        assert "Protocyte refuses to reuse protoc-safe alias" in output
        assert "status: wrong-target" in output
        assert "Protocyte did not modify the existing entry" in normalized_output
        assert alias.resolve() == wrong_target.resolve()
        assert sentinel.read_text(encoding="utf-8") == "keep\n"
    finally:
        if alias.exists():
            os.rmdir(alias)


@pytest.mark.skipif(os.name != "nt", reason="Windows protoc import-root alias")
def test_protoc_safe_import_root_rechecks_registered_alias_after_swap(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    plugin = _installed_protocyte_plugin()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto;root"
    alias = _protoc_safe_import_root_alias(build_dir, proto_dir)
    wrong_target = tmp_path / "swapped-target"
    wrong_target.mkdir()
    sentinel = wrong_target / "keep.txt"
    sentinel.write_text("keep\n", encoding="utf-8")
    swap_script = source_dir / "swap-alias.py"
    swap_script.parent.mkdir(parents=True)
    swap_script.write_text(
        "\n".join(
            [
                "import os",
                "import subprocess",
                "import sys",
                "from pathlib import Path",
                "alias, target = map(Path, sys.argv[1:])",
                "os.rmdir(alias)",
                "subprocess.run(",
                '    ["cmd.exe", "/d", "/c", "mklink", "/J", str(alias), str(target)],',
                "    check=True,",
                "    capture_output=True,",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_protoc_safe_import_root_project(
        source_dir,
        protoc=protoc,
        plugin=plugin,
        between_generate_calls=(
            "execute_process(",
            f'    COMMAND "{Path(sys.executable).as_posix()}" "{swap_script.as_posix()}"',
            f'        "{alias.as_posix()}" "{wrong_target.as_posix()}"',
            "    COMMAND_ERROR_IS_FATAL ANY",
            ")",
        ),
    )
    try:
        result = subprocess.run(
            ["cmake", "-S", str(source_dir), "-B", str(build_dir)],
            check=False,
            capture_output=True,
            text=True,
        )

        output = result.stdout + result.stderr
        normalized_output = " ".join(output.split())
        assert result.returncode != 0
        assert "Protocyte refuses to reuse protoc-safe alias" in output
        assert "status: wrong-target" in output
        assert "Protocyte did not modify the existing entry" in normalized_output
        assert alias.resolve() == wrong_target.resolve()
        assert sentinel.read_text(encoding="utf-8") == "keep\n"
    finally:
        if alias.exists():
            os.rmdir(alias)


@pytest.mark.skipif(os.name != "nt", reason="Windows protoc import-root alias")
def test_protoc_safe_import_root_creation_is_concurrent_and_deterministic(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    import_root = tmp_path / "proto;root"
    import_root.mkdir()
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    script = tmp_path / "create-alias.cmake"
    script.write_text(
        "\n".join(
            [
                'include("${FUNCTIONS}")',
                '_protocyte_protoc_safe_import_root(alias "${IMPORT_ROOT}")',
                'file(WRITE "${RESULT_FILE}" "${alias}")',
                "",
            ]
        ),
        encoding="utf-8",
    )
    process_count = 4
    processes = [
        subprocess.Popen(
            [
                "cmake",
                f"-DFUNCTIONS={(repo_root / 'cmake' / 'ProtocyteFunctions.cmake').as_posix()}",
                f"-DIMPORT_ROOT={import_root.as_posix()}",
                f"-DRESULT_FILE={(tmp_path / f'result-{index}.txt').as_posix()}",
                "-P",
                str(script),
            ],
            cwd=build_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(process_count)
    ]
    process_outputs = [process.communicate(timeout=60) for process in processes]
    failures = [
        f"stdout:\n{stdout}\nstderr:\n{stderr}"
        for process, (stdout, stderr) in zip(processes, process_outputs, strict=True)
        if process.returncode != 0
    ]
    assert not failures, "\n\n".join(failures)

    alias = _protoc_safe_import_root_alias(build_dir, import_root)
    try:
        assert alias.resolve() == import_root.resolve()
        expected_alias = alias.as_posix()
        for index in range(process_count):
            assert (tmp_path / f"result-{index}.txt").read_text(
                encoding="utf-8"
            ) == expected_alias
    finally:
        if alias.exists():
            os.rmdir(alias)


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
        _real_protoc_requirement_unavailable(
            "Ninja is required for the Ninja semicolon-path regression"
        )
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
        text for text in response_texts if "--plugin=protoc-gen-protocyte=" in text
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

    no_op = subprocess.run(build_command, check=True, capture_output=True, text=True)
    no_op_output = no_op.stdout + no_op.stderr
    assert "Scanning protobuf imports" not in no_op_output
    assert "Generating " not in no_op_output

    proto_file.write_text(
        'syntax = "proto3"; package demo; message SharedUpdated {}\n',
        encoding="utf-8",
    )
    latest_output = max(headers, key=lambda path: path.stat().st_mtime_ns)
    _touch_newer_than(proto_file, latest_output)
    rebuilt = subprocess.run(build_command, check=True, capture_output=True, text=True)
    rebuilt_output = rebuilt.stdout + rebuilt.stderr
    assert rebuilt_output.count("Scanning protobuf imports") == 2
    assert rebuilt_output.count("] Generating ") == 2
    assert all(
        "SharedUpdated" in header.read_text(encoding="utf-8") for header in headers
    )

    final_no_op = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    final_no_op_output = final_no_op.stdout + final_no_op.stderr
    assert "Scanning protobuf imports" not in final_no_op_output
    assert "Generating " not in final_no_op_output


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_windows_semicolon_source_proxy_reuses_case_aliases(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify case-insensitive source proxy reuse"
        )
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "shared;legacy.proto").write_text(
        'syntax = "proto3"; package demo; message Shared {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(case_alias_source_proxy LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET lower_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/lower-generated"',
                "    PROTOS [==[proto/shared;legacy.proto]==]",
                "    OPTIONS format=off",
                ")",
                "protocyte_generate(",
                "    TARGET upper_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/PROTO"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/upper-generated"',
                "    PROTOS [==[PROTO/SHARED;LEGACY.proto]==]",
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
            "lower_codegen",
            "upper_codegen",
        ],
        check=True,
    )

    proxy_dir = build_dir / "CMakeFiles" / "protocyte-source-dependencies"
    assert len(list(proxy_dir.glob("*.proto"))) == 1
    assert list((build_dir / "lower-generated").glob("*.protocyte.hpp"))
    assert list((build_dir / "upper-generated").glob("*.protocyte.hpp"))


def test_multiconfig_serializes_shared_semicolon_source_proxy_updates(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _multiconfig_locking_requirement_unavailable(
            "Ninja is required to verify concurrent source proxy updates"
        )
    cmake_help = subprocess.run(
        ["cmake", "--help"], check=True, capture_output=True, text=True
    ).stdout
    if "Ninja Multi-Config" not in cmake_help:
        _multiconfig_locking_requirement_unavailable(
            "CMake does not provide the Ninja Multi-Config generator"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    proto_file = proto_dir / "shared;legacy.proto"
    padding = "x" * 2_000_000

    def write_proto(iteration: int) -> str:
        message_name = f"SharedUpdate{iteration}"
        proto_file.write_text(
            f'syntax = "proto3"; package demo; message {message_name} {{}}\n'
            f"/* {padding} */\n",
            encoding="utf-8",
        )
        return message_name

    write_proto(0)
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
                "project(multiconfig_semicolon_proxy LANGUAGES NONE)",
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
    targets = ["first_codegen", "second_codegen"]
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
            "--config",
            "Debug",
            "--target",
            *targets,
        ],
        check=True,
    )
    proxy_dir = build_dir / "CMakeFiles" / "protocyte-source-dependencies"
    assert len(list(proxy_dir.glob("*.proto"))) == 1
    ninja_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in build_dir.rglob("*.ninja")
    )
    assert "-DLOCK_FILE=" in ninja_text

    source_argument_file = next(proxy_dir.glob("*.path"))
    proxy_file = next(proxy_dir.glob("*.proto"))
    lock_file = proxy_file.with_suffix(".lock")
    source_checker = repo_root / "cmake" / "ProtocyteSourceDependency.cmake"
    runner = _write_synchronized_build_runner(source_dir / "build_runner.py")
    for iteration in range(1, 7):
        write_proto(iteration)
        gate = source_dir / f"start-builds-{iteration}"
        processes: list[subprocess.Popen[str]] = []
        ready_paths: list[Path] = []
        for worker in range(8):
            ready = source_dir / f"worker-{worker}-{iteration}.ready"
            ready_paths.append(ready)
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        str(runner),
                        str(ready),
                        str(gate),
                        "cmake",
                        f"-DSOURCE_ARGUMENT_FILE={source_argument_file}",
                        f"-DPROXY_FILE={proxy_file}",
                        f"-DLOCK_FILE={lock_file}",
                        "-P",
                        str(source_checker),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            )

        deadline = time.monotonic() + 30.0
        while not all(path.is_file() for path in ready_paths):
            if any(process.poll() is not None for process in processes):
                pytest.fail(
                    "a synchronized build runner exited before reaching the gate"
                )
            if time.monotonic() >= deadline:
                pytest.fail("timed out waiting for synchronized multi-config builds")
            time.sleep(0.01)
        gate.write_text("start\n", encoding="utf-8")

        try:
            for process in processes:
                stdout, stderr = process.communicate(timeout=180)
                assert process.returncode == 0, stdout + stderr
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        assert proxy_file.read_bytes() == proto_file.read_bytes()


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
        _real_protoc_requirement_unavailable(
            "Ninja is required for emitted runtime ownership build coverage"
        )

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
    assert (build_dir / "separate" / "protocyte" / "runtime" / "runtime.hpp").is_file()


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
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)

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
    assert (build_dir / "generated" / "protocyte" / "runtime" / "runtime.hpp").is_file()

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
    no_change_output = no_change.stdout + no_change.stderr
    assert "Scanning protobuf imports" not in no_change_output
    assert "Generating generated/" not in no_change_output


@pytest.mark.parametrize("generator_kind", ["ninja", "visual-studio"])
def test_source_codegen_tracks_import_shadow_addition_and_removal(
    tmp_path: Path,
    generator_kind: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    if generator_kind == "ninja":
        if shutil.which("ninja") is None:
            _incremental_requirement_unavailable(
                "Ninja is required to verify import-shadow topology changes"
            )
        generator = "Ninja"
    else:
        generator = _find_visual_studio_generator()

    test_root = (
        _create_configured_visual_studio_test_directory()
        if generator_kind == "visual-studio"
        else tmp_path
    )
    source_dir = test_root / "project"
    build_dir = test_root / "build"
    proto_dir = source_dir / "proto"
    high_priority_import_dir = source_dir / "imports-high"
    low_priority_import_dir = source_dir / "imports-low"
    tools_dir = source_dir / "tools"
    for directory in (
        proto_dir,
        high_priority_import_dir,
        low_priority_import_dir,
        tools_dir,
    ):
        directory.mkdir(parents=True)

    def write_common(path: Path, capacity: int) -> None:
        path.write_text(
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

    low_priority_common = low_priority_import_dir / "common.schema"
    high_priority_common = high_priority_import_dir / "common.schema"
    write_common(low_priority_common, 2)
    (proto_dir / "consumer.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "common.schema";',
                'import "protocyte/options.proto";',
                "option (protocyte.package_constant) = "
                '{ name: "DERIVED" u32_expr: "demo.CAPACITY + 1" };',
                "message Consumer {}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    invocation_log = source_dir / "protoc-invocations.log"
    protoc = _write_protoc_wrapper(tools_dir / "protoc", real_protoc, invocation_log)
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(import_shadow_topology LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/consumer.proto",
                "    IMPORT_DIRS",
                '        "${CMAKE_CURRENT_SOURCE_DIR}/imports-high"',
                '        "${CMAKE_CURRENT_SOURCE_DIR}/imports-low"',
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_environment = os.environ.copy()
    cache_root = test_root / "cache"
    cache_root.mkdir()
    if os.name == "nt":
        configure_environment["LOCALAPPDATA"] = str(cache_root)
    else:
        configure_environment["XDG_CACHE_HOME"] = str(cache_root)
    subprocess.run(
        [
            "cmake",
            "-G",
            generator,
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
        ],
        check=True,
        env=configure_environment,
    )
    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    generated_header = build_dir / "generated" / "consumer.protocyte.hpp"

    def invocation_count() -> int:
        if not invocation_log.exists():
            return 0
        return len(invocation_log.read_text(encoding="utf-8").splitlines())

    subprocess.run(build_command, check=True, env=configure_environment)
    assert "DERIVED {3u}" in generated_header.read_text(encoding="utf-8")
    initial_invocations = invocation_count()
    assert initial_invocations == 2

    if generator_kind == "ninja":
        subprocess.run(build_command, check=True, env=configure_environment)
        assert invocation_count() == initial_invocations

    write_common(high_priority_common, 5)
    if generator_kind == "visual-studio":
        guarded_addition = subprocess.run(
            build_command,
            check=False,
            capture_output=True,
            text=True,
            env=configure_environment,
        )
        if guarded_addition.returncode != 0:
            assert "Protocyte import topology changed before code generation" in (
                guarded_addition.stdout + guarded_addition.stderr
            )
            assert "DERIVED {3u}" in generated_header.read_text(encoding="utf-8")
            assert invocation_count() == initial_invocations
            subprocess.run(build_command, check=True, env=configure_environment)
    else:
        subprocess.run(build_command, check=True, env=configure_environment)
    assert "DERIVED {6u}" in generated_header.read_text(encoding="utf-8")
    after_addition_invocations = invocation_count()
    assert after_addition_invocations == initial_invocations + 2

    subprocess.run(build_command, check=True, env=configure_environment)
    assert invocation_count() == after_addition_invocations

    high_priority_common.unlink()
    if generator_kind == "visual-studio":
        guarded_removal = subprocess.run(
            build_command,
            check=False,
            capture_output=True,
            text=True,
            env=configure_environment,
        )
        if guarded_removal.returncode != 0:
            assert "Protocyte import topology changed before code generation" in (
                guarded_removal.stdout + guarded_removal.stderr
            )
            assert "DERIVED {6u}" in generated_header.read_text(encoding="utf-8")
            assert invocation_count() == after_addition_invocations
            subprocess.run(build_command, check=True, env=configure_environment)
    else:
        subprocess.run(build_command, check=True, env=configure_environment)
    assert "DERIVED {3u}" in generated_header.read_text(encoding="utf-8")
    after_removal_invocations = invocation_count()
    assert after_removal_invocations == after_addition_invocations + 2

    subprocess.run(build_command, check=True, env=configure_environment)
    assert invocation_count() == after_removal_invocations


@pytest.mark.parametrize(
    "generator_kind",
    ["ninja", "visual-studio", "nmake"],
)
def test_source_codegen_tracks_import_directory_identity_changes(
    tmp_path: Path,
    generator_kind: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    if generator_kind == "ninja":
        if shutil.which("ninja") is None:
            _incremental_requirement_unavailable(
                "Ninja is required to verify import-directory identity changes"
            )
        generator = "Ninja"
    elif generator_kind == "visual-studio":
        generator = _find_visual_studio_generator()
    else:
        if shutil.which("nmake") is None:
            _incremental_requirement_unavailable(
                "NMake is required to verify import-directory identity changes",
                additional_required_env=_CI_REQUIRE_VISUAL_STUDIO_TEST_ENV,
            )
        generator = "NMake Makefiles"

    test_root = (
        _create_configured_visual_studio_test_directory()
        if generator_kind == "visual-studio"
        else tmp_path
    )
    source_dir = test_root / "project"
    build_dir = test_root / "build"
    proto_dir = source_dir / "proto"
    import_alias = source_dir / "imports"
    first_target = source_dir / "first-import-target"
    second_target = source_dir / "second-import-target"
    tools_dir = source_dir / "tools"
    for directory in (
        proto_dir,
        import_alias,
        first_target,
        second_target,
        tools_dir,
    ):
        directory.mkdir(parents=True)

    def write_common(path: Path, capacity: int) -> None:
        path.write_text(
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

    initial_common = import_alias / "common.schema"
    first_common = first_target / "common.schema"
    second_common = second_target / "common.schema"
    write_common(initial_common, 2)
    write_common(first_common, 5)
    write_common(second_common, 8)
    stable_timestamp_ns = initial_common.stat().st_mtime_ns
    os.utime(first_common, ns=(stable_timestamp_ns, stable_timestamp_ns))
    os.utime(second_common, ns=(stable_timestamp_ns, stable_timestamp_ns))
    assert initial_common.stat().st_size == first_common.stat().st_size
    assert initial_common.stat().st_size == second_common.stat().st_size

    (proto_dir / "consumer.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "common.schema";',
                'import "protocyte/options.proto";',
                "option (protocyte.package_constant) = "
                '{ name: "DERIVED" u32_expr: "demo.CAPACITY + 1" };',
                "message Consumer {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    invocation_directory = source_dir / "protoc-invocations"
    protoc = _write_parallel_protoc_wrapper(
        tools_dir / "protoc", real_protoc, invocation_directory
    )
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(import_directory_identity LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET first_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/first-generated"',
                "    PROTOS proto/consumer.proto",
                '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports"',
                "    OPTIONS format=off",
                ")",
                "protocyte_generate(",
                "    TARGET second_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/second-generated"',
                "    PROTOS proto/consumer.proto",
                '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports"',
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    configure_environment = os.environ.copy()
    cache_root = test_root / "cache"
    cache_root.mkdir()
    if os.name == "nt":
        configure_environment["LOCALAPPDATA"] = str(cache_root)
    else:
        configure_environment["XDG_CACHE_HOME"] = str(cache_root)
    subprocess.run(
        ["cmake", "-G", generator, "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
        env=configure_environment,
    )
    build_command = [
        "cmake",
        "--build",
        str(build_dir),
        "--target",
        "first_codegen",
        "second_codegen",
    ]
    if generator_kind != "nmake":
        build_command.extend(["--parallel", "2"])
    generated_headers = [
        build_dir / output_directory / "consumer.protocyte.hpp"
        for output_directory in ("first-generated", "second-generated")
    ]

    def all_headers_contain(value: int) -> bool:
        expected = f"DERIVED {{{value}u}}"
        return all(
            expected in generated_header.read_text(encoding="utf-8")
            for generated_header in generated_headers
        )

    def invocation_count() -> int:
        return len(list(invocation_directory.iterdir()))

    def build_after_identity_change(
        before_value: int,
        after_value: int,
        before_invocations: int,
    ) -> int:
        changed_build = subprocess.run(
            build_command,
            check=False,
            capture_output=True,
            text=True,
            env=configure_environment,
        )
        if generator_kind == "nmake":
            assert changed_build.returncode == 0, (
                changed_build.stdout + changed_build.stderr
            )
        else:
            assert changed_build.returncode != 0
            assert "Protocyte import topology changed before code generation" in (
                changed_build.stdout + changed_build.stderr
            )
            assert all_headers_contain(before_value)
            assert invocation_count() == before_invocations
            subprocess.run(build_command, check=True, env=configure_environment)

        assert all_headers_contain(after_value)
        after_invocations = invocation_count()
        assert after_invocations == before_invocations + 4
        subprocess.run(build_command, check=True, env=configure_environment)
        assert invocation_count() == after_invocations
        return after_invocations

    subprocess.run(build_command, check=True, env=configure_environment)
    assert all_headers_contain(3)
    initial_invocations = invocation_count()
    assert initial_invocations == 4
    subprocess.run(build_command, check=True, env=configure_environment)
    assert invocation_count() == initial_invocations

    shutil.rmtree(import_alias)
    _create_generated_output_directory_link(import_alias, first_target)
    after_directory_link = build_after_identity_change(3, 6, initial_invocations)

    _remove_generated_output_directory_link(import_alias)
    _create_generated_output_directory_link(import_alias, second_target)
    build_after_identity_change(6, 9, after_directory_link)


def test_visual_studio_test_directory_is_unique_between_runs(tmp_path: Path) -> None:
    first = _create_visual_studio_test_directory(tmp_path)
    second = _create_visual_studio_test_directory(tmp_path)

    assert first != second
    assert first.parent == tmp_path.resolve()
    assert second.parent == tmp_path.resolve()


@pytest.mark.skipif(os.name != "nt", reason="Visual Studio generator regression")
def test_visual_studio_codegen_builds_noop_and_rebuilds_transitive_import() -> None:
    configured_protoc = os.environ.get(_CI_PROTOC_ENV)
    if not configured_protoc:
        _visual_studio_requirement_unavailable(
            f"{_CI_PROTOC_ENV} is not configured with the prebuilt protoc"
        )

    cmake_help = subprocess.run(
        ["cmake", "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if "Visual Studio 17 2022" not in cmake_help:
        _visual_studio_requirement_unavailable(
            "CMake does not provide the Visual Studio 17 2022 generator"
        )

    repo_root = Path(__file__).resolve().parents[1]
    test_root = _create_configured_visual_studio_test_directory()
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    source_dir = test_root / "project"
    build_dir = test_root / "build"
    proto_dir = source_dir / "proto"
    import_dir = source_dir / "imports"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    import_dir.mkdir()
    tools_dir.mkdir()

    imported_proto = import_dir / "base.proto"

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
    (proto_dir / "consumer.proto").write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package demo;",
                'import "base.proto";',
                'import "protocyte/options.proto";',
                "option (protocyte.package_constant) = "
                '{ name: "DERIVED" u32_expr: "demo.CAPACITY + 1" };',
                "message Consumer {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    invocation_log = source_dir / "protoc-invocations.txt"
    protoc = _write_protoc_wrapper(
        tools_dir / "protoc",
        real_protoc,
        invocation_log,
    )
    plugin = _write_python_plugin_wrapper(
        tools_dir / "protoc-gen-protocyte",
        repo_root,
    )

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(visual_studio_incremental LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/consumer.proto",
                '    IMPORT_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/imports"',
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
            "Visual Studio 17 2022",
            "-A",
            "x64",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
        ],
        check=True,
    )
    build_command = [
        "cmake",
        "--build",
        str(build_dir),
        "--config",
        "Release",
        "--target",
        "demo_codegen",
        "--parallel",
        "1",
    ]
    subprocess.run(build_command, check=True)
    generated_header = build_dir / "generated" / "consumer.protocyte.hpp"
    assert "DERIVED {3u}" in generated_header.read_text(encoding="utf-8")
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
    ]

    subprocess.run(build_command, check=True)
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
    ]

    write_imported(5)
    _touch_newer_than(imported_proto, generated_header)
    subprocess.run(build_command, check=True)
    assert "DERIVED {6u}" in generated_header.read_text(encoding="utf-8")
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "invoked",
        "invoked",
        "invoked",
        "invoked",
    ]


def test_dependency_scan_reruns_when_generator_implementation_changes(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify dependency-scan invalidation"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    proto_dir.mkdir(parents=True)
    tools_dir.mkdir()
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package scan_inputs; message Demo {}\n',
        encoding="utf-8",
    )
    scan_implementation = source_dir / "scan-implementation.py"
    scan_implementation.write_text(
        "# dependency scan implementation v1\n", encoding="utf-8"
    )
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(dependency_scan_inputs LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                "get_property(generator_sources GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES)",
                'list(APPEND generator_sources "${CMAKE_CURRENT_SOURCE_DIR}/scan-implementation.py")',
                'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES "${generator_sources}")',
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
        ["cmake", "-G", "Ninja", "-S", str(source_dir), "-B", str(build_dir)],
        check=True,
    )
    build_command = ["cmake", "--build", str(build_dir), "--target", "demo_codegen"]
    subprocess.run(build_command, check=True)
    dependency_descriptors = list(
        (build_dir / "CMakeFiles" / "protocyte-dependencies").glob("*.pb")
    )
    assert len(dependency_descriptors) == 1
    dependency_descriptor = dependency_descriptors[0]
    initial_mtime_ns = dependency_descriptor.stat().st_mtime_ns

    scan_implementation.write_text(
        "# dependency scan implementation v2\n", encoding="utf-8"
    )
    _touch_newer_than(scan_implementation, dependency_descriptor)
    subprocess.run(build_command, check=True)

    assert dependency_descriptor.stat().st_mtime_ns > initial_mtime_ns


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
    no_change_output = no_change.stdout + no_change.stderr
    assert "Scanning protobuf imports" not in no_change_output
    assert "Generating generated/" not in no_change_output

    write_imported(7)
    subprocess.run(build_command, check=True)
    assert "DERIVED {8u}" in generated_header.read_text(encoding="utf-8")

    no_change = subprocess.run(
        build_command, check=True, capture_output=True, text=True
    )
    no_change_output = no_change.stdout + no_change.stderr
    assert "Scanning protobuf imports" not in no_change_output
    assert "Generating generated/" not in no_change_output


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


def test_legacy_owned_output_manifests_are_migrated_conservatively(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    child_source_dir = source_dir / "child"
    build_dir = tmp_path / "build"
    child_build_dir = build_dir / "child"
    child_source_dir.mkdir(parents=True)
    (child_source_dir / "CMakeLists.txt").write_text(
        "# Legacy target removed.\n", encoding="utf-8"
    )

    def write_project(*, with_child: bool) -> None:
        lines = [
            "cmake_minimum_required(VERSION 3.24)",
            "project(legacy_output_migration LANGUAGES NONE)",
            f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
        ]
        if with_child:
            lines.append("add_subdirectory(child)")
        lines.append("")
        (source_dir / "CMakeLists.txt").write_text("\n".join(lines), encoding="utf-8")

    configure_command = ["cmake", "-S", str(source_dir), "-B", str(build_dir)]
    write_project(with_child=True)
    subprocess.run(configure_command, check=True)

    top_output_root = build_dir / "top-generated"
    child_output_root = child_build_dir / "child-generated"
    top_output = top_output_root / "top.protocyte.hpp"
    child_output = child_output_root / "child.protocyte.cpp"
    top_output.parent.mkdir(parents=True)
    child_output.parent.mkdir(parents=True)
    top_output.write_text("legacy generated bytes\n", encoding="utf-8")
    child_output.write_text("consumer modification\n", encoding="utf-8")
    top_manifest = _write_legacy_owned_output_manifest(
        build_dir, "removed_top_codegen", top_output_root, top_output
    )
    child_manifest = _write_legacy_owned_output_manifest(
        child_build_dir, "removed_child_codegen", child_output_root, child_output
    )
    decoy_manifest = (
        build_dir / "unrelated" / "CMakeFiles" / "protocyte-owned-outputs" / ("f" * 64)
    )
    decoy_manifest.mkdir(parents=True)
    (decoy_manifest / "output-root.path").write_text(
        top_output_root.resolve().as_posix(), encoding="utf-8"
    )
    (decoy_manifest / "not-a-key.path").write_text(
        top_output.resolve().as_posix(), encoding="utf-8"
    )

    write_project(with_child=False)
    first = subprocess.run(
        configure_command, check=True, capture_output=True, text=True
    )
    first_output = first.stdout + first.stderr
    normalized_first_output = " ".join(first_output.split())

    assert first_output.count("build tree predates content fingerprints") == 2
    assert "Remove obsolete files manually" in first_output
    assert (
        "temporarily restore a code-generation target that declares these outputs"
        in normalized_first_output
    )
    assert top_output.read_text(encoding="utf-8") == "legacy generated bytes\n"
    assert child_output.read_text(encoding="utf-8") == "consumer modification\n"
    manifest_root = build_dir / "CMakeFiles" / "protocyte-owned-outputs"
    migrated_manifests = [path for path in manifest_root.iterdir() if path.is_dir()]
    assert len(migrated_manifests) == 2
    assert all(list(path.glob("*.pending")) for path in migrated_manifests)
    assert all(list(path.glob("*.pending-notified")) for path in migrated_manifests)
    assert not top_manifest.exists()
    assert not child_manifest.exists()
    assert decoy_manifest.is_dir()

    second = subprocess.run(
        configure_command, check=True, capture_output=True, text=True
    )
    second_output = second.stdout + second.stderr
    assert "build tree predates content fingerprints" not in second_output
    assert top_output.is_file()
    assert child_output.is_file()
    assert len([path for path in manifest_root.iterdir() if path.is_dir()]) == 2


def test_active_legacy_target_preserves_dropped_unfingerprinted_outputs(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify an active legacy ownership migration"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "kept.proto").write_text(
        'syntax = "proto3"; package demo; message Kept {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(active_legacy_output_migration LANGUAGES NONE)",
                "set(CMAKE_DISABLE_FIND_PACKAGE_Protobuf TRUE)",
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                "protocyte_generate(",
                "    TARGET demo_codegen",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                "    PROTOS proto/kept.proto",
                "    OPTIONS format=off",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    generated_dir = build_dir / "generated"
    generated_dir.mkdir(parents=True)
    kept_outputs = [
        generated_dir / "kept.protocyte.hpp",
        generated_dir / "kept.protocyte.cpp",
    ]
    dropped_outputs = [
        generated_dir / "dropped.protocyte.hpp",
        generated_dir / "dropped.protocyte.cpp",
    ]
    for output in kept_outputs:
        output.write_text("legacy retained output\n", encoding="utf-8")
    for output in dropped_outputs:
        output.write_text("legacy dropped output with edits\n", encoding="utf-8")
    current_manifest = _write_legacy_owned_output_manifest(
        build_dir,
        "demo_codegen",
        generated_dir,
        *kept_outputs,
        *dropped_outputs,
    )

    configure_command = [
        "cmake",
        "-G",
        "Ninja",
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
    ]
    first = subprocess.run(
        configure_command, check=True, capture_output=True, text=True
    )
    first_output = first.stdout + first.stderr
    normalized_first_output = " ".join(first_output.split())

    assert first_output.count("build tree predates content fingerprints") == 1
    assert all(
        output.resolve().as_posix() in normalized_first_output
        for output in dropped_outputs
    )
    assert all(
        output.read_text(encoding="utf-8") == "legacy retained output\n"
        for output in kept_outputs
    )
    assert all(
        output.read_text(encoding="utf-8") == "legacy dropped output with edits\n"
        for output in dropped_outputs
    )
    current_markers = [
        path
        for path in current_manifest.glob("*.path")
        if path.name != "output-root.path"
    ]
    assert len(current_markers) == len(kept_outputs)

    manifest_root = build_dir / "CMakeFiles" / "protocyte-owned-outputs"
    pending_manifests = [
        path
        for path in manifest_root.iterdir()
        if path.is_dir() and path != current_manifest
    ]
    assert len(pending_manifests) == len(dropped_outputs)
    pending_outputs = {
        Path(marker.read_text(encoding="utf-8")).resolve()
        for manifest in pending_manifests
        for marker in manifest.glob("*.path")
        if marker.name != "output-root.path"
    }
    assert pending_outputs == {output.resolve() for output in dropped_outputs}
    assert all(list(path.glob("*.pending")) for path in pending_manifests)
    assert all(list(path.glob("*.pending-notified")) for path in pending_manifests)

    second = subprocess.run(
        configure_command, check=True, capture_output=True, text=True
    )
    second_output = second.stdout + second.stderr
    assert "build tree predates content fingerprints" not in second_output
    assert all(output.is_file() for output in dropped_outputs)
    assert len([path for path in manifest_root.iterdir() if path.is_dir()]) == 3


def test_legacy_manifest_becomes_cleanable_after_regeneration(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    if shutil.which("ninja") is None:
        _incremental_requirement_unavailable(
            "Ninja is required to verify legacy ownership regeneration"
        )

    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    proto_file = proto_dir / "demo.proto"
    proto_file.write_text(
        'syntax = "proto3"; package demo; message Demo {}\n', encoding="utf-8"
    )
    plugin = _installed_protocyte_plugin()

    def write_project(with_target: bool) -> None:
        lines = [
            "cmake_minimum_required(VERSION 3.24)",
            "project(legacy_output_regeneration LANGUAGES NONE)",
            f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
            f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
            f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
            f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
        ]
        if with_target:
            lines.extend(
                [
                    "protocyte_generate(",
                    "    TARGET demo_codegen",
                    '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                    '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                    "    PROTOS proto/demo.proto",
                    "    OPTIONS format=off",
                    ")",
                ]
            )
        lines.append("")
        (source_dir / "CMakeLists.txt").write_text("\n".join(lines), encoding="utf-8")

    write_project(with_target=True)
    generated_dir = build_dir / "generated"
    generated_header = generated_dir / "demo.protocyte.hpp"
    generated_source = generated_dir / "demo.protocyte.cpp"
    generated_dir.mkdir(parents=True)
    generated_header.write_text("legacy header\n", encoding="utf-8")
    generated_source.write_text("legacy source\n", encoding="utf-8")
    manifest_dir = _write_legacy_owned_output_manifest(
        build_dir,
        "demo_codegen",
        generated_dir,
        generated_header,
        generated_source,
    )

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
        ["cmake", "--build", str(build_dir), "--target", "demo_codegen"],
        check=True,
    )
    assert len(list(manifest_dir.glob("*.sha256"))) == 2
    assert "struct Demo" in generated_header.read_text(encoding="utf-8")

    write_project(with_target=False)
    subprocess.run(configure_command, check=True)
    assert not generated_header.exists()
    assert not generated_source.exists()
    assert not manifest_dir.exists()


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
    plugin = _write_overlap_detecting_dependency_reader_wrapper(
        tools_dir / "protoc-gen-protocyte",
        _write_python_plugin_wrapper(
            tools_dir / "real-protoc-gen-protocyte", repo_root
        ),
        state_dir,
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
    assert len(list(state_dir.glob("attempt-reader-*"))) == 2
    assert len(list(state_dir.glob("complete-reader-*"))) == 2
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


def _out_dir_owner_record_paths(output_directory: Path) -> tuple[Path, Path]:
    output_key = _filesystem_identity_hash(output_directory)
    prefix = output_directory.resolve().parent / f".protocyte-out-dir-{output_key}"
    return prefix.with_suffix(".owner"), prefix.with_suffix(".lock")


def _filesystem_identity_hash(path: Path) -> str:
    identity = path.resolve().as_posix()
    if os.name == "nt":
        identity = identity.lower()
    return hashlib.sha256(identity.encode()).hexdigest()


def _build_tree_owner_hash(build_directory: Path) -> str:
    return _filesystem_identity_hash(build_directory)


def _owner_transaction_record(
    root_owner_record: Path, transaction_id: str, state: str
) -> Path:
    return root_owner_record.parent / (
        f"{root_owner_record.name}.{transaction_id}.{state}"
    )


def _committed_owner_build_hash(owner_record: Path, root_owner_record: Path) -> str:
    owner_fields = dict(
        line.split("=", maxsplit=1)
        for line in owner_record.read_text(encoding="utf-8").splitlines()
    )
    assert len(owner_fields["build-tree-sha256"]) == 64
    if owner_fields["version"] == "1":
        assert set(owner_fields) == {"version", "build-tree-sha256"}
        return owner_fields["build-tree-sha256"]

    assert owner_fields["version"] == "2"
    assert set(owner_fields) == {
        "version",
        "build-tree-sha256",
        "transaction-sha256",
    }
    transaction_id = owner_fields["transaction-sha256"]
    assert len(transaction_id) == 64
    committed = _owner_transaction_record(
        root_owner_record, transaction_id, "committed"
    )
    committed_bytes = committed.read_bytes()
    assert hashlib.sha256(committed_bytes).hexdigest() == transaction_id
    manifest_lines = committed_bytes.decode("utf-8").splitlines()
    manifest_fields = dict(line.split("=", maxsplit=1) for line in manifest_lines[:4])
    assert list(manifest_fields) == [
        "version",
        "nonce",
        "build-tree-sha256",
        "claims-sha256",
    ]
    assert manifest_fields["version"] == "1"
    assert len(manifest_fields["nonce"]) == 64
    assert len(manifest_fields["claims-sha256"]) == 64
    assert manifest_fields["build-tree-sha256"] == owner_fields["build-tree-sha256"]
    claim_ids = [line.removeprefix("claim-sha256=") for line in manifest_lines[4:]]
    assert claim_ids
    assert all(
        line == f"claim-sha256={claim_id}"
        for line, claim_id in zip(manifest_lines[4:], claim_ids, strict=True)
    )
    assert claim_ids == sorted(set(claim_ids))
    assert (
        hashlib.sha256(";".join(claim_ids).encode()).hexdigest()
        == manifest_fields["claims-sha256"]
    )
    owner_identity = owner_record.resolve().as_posix()
    if os.name == "nt":
        owner_identity = owner_identity.lower()
    assert hashlib.sha256(owner_identity.encode()).hexdigest() in claim_ids
    return owner_fields["build-tree-sha256"]


def _output_owner_record_path(source_dir: Path, output_path: Path) -> Path:
    return (
        source_dir.parent
        / "output-locks"
        / (f"{_filesystem_identity_hash(output_path)}.owner")
    )


def _create_generated_output_directory_link(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            pytest.skip("Windows junction creation is unavailable: " + result.stderr)
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")


def _remove_generated_output_directory_link(link: Path) -> None:
    if os.name == "nt":
        link.rmdir()
    else:
        link.unlink()


def _write_out_dir_owner_project(
    source_dir: Path,
    output_directory: Path,
    *,
    target_count: int = 1,
    proto_names: tuple[str, ...] | None = None,
    runtime_prefix: str | None = None,
    output_lock_root: Path | None = None,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "descriptor_set.pb").write_bytes(b"placeholder")
    if proto_names is None:
        proto_names = tuple(f"demo_{index}.proto" for index in range(target_count))
    else:
        target_count = len(proto_names)
    generated_outputs = {
        proto_name: tuple(
            (
                output_directory
                / f"{proto_name.removesuffix('.proto')}.protocyte{extension}"
            ).as_posix()
            for extension in (".hpp", ".cpp")
        )
        for proto_name in proto_names
    }
    runtime_outputs = (
        ()
        if runtime_prefix is None
        else ((output_directory / runtime_prefix / "runtime.hpp").as_posix(),)
    )
    fake_protoc_script = source_dir / "fake-protoc.py"
    fake_protoc_script.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import sys",
                "from pathlib import Path",
                "",
                f"outputs = {generated_outputs!r}",
                f"runtime_outputs = {runtime_outputs!r}",
                "argument_file = Path(sys.argv[1].removeprefix('@'))",
                "arguments = [",
                "    line.strip().removeprefix(chr(34)).removesuffix(chr(34))",
                "    for line in argument_file.read_text(encoding='utf-8').splitlines()",
                "]",
                "for proto_name, paths in outputs.items():",
                "    if proto_name not in arguments:",
                "        continue",
                "    for raw_path in paths:",
                "        output = Path(raw_path)",
                "        output.parent.mkdir(parents=True, exist_ok=True)",
                "        output.write_text('// generated by ownership test\\n', encoding='utf-8')",
                "if any(proto_name in arguments for proto_name in outputs):",
                "    for raw_path in runtime_outputs:",
                "        output = Path(raw_path)",
                "        output.parent.mkdir(parents=True, exist_ok=True)",
                "        output.write_text('// generated runtime by ownership test\\n', encoding='utf-8')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    if os.name == "nt":
        fake_protoc = source_dir / "fake-protoc.cmd"
        fake_protoc.write_text(
            f'@echo off\r\n"{sys.executable}" "{fake_protoc_script}" %*\r\n',
            encoding="utf-8",
        )
    else:
        fake_protoc = source_dir / "fake-protoc"
        fake_protoc.write_text(
            "#!/usr/bin/env sh\n"
            f'exec {shlex.quote(sys.executable)} {shlex.quote(str(fake_protoc_script))} "$@"\n',
            encoding="utf-8",
        )
        fake_protoc.chmod(0o755)
    resolved_output_lock_root = output_lock_root or source_dir.parent / "output-locks"
    lines = [
        "cmake_minimum_required(VERSION 3.24)",
        "project(out_dir_ownership LANGUAGES NONE)",
        f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
        f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{resolved_output_lock_root.as_posix()}")',
        "function(_protocyte_setup_codegen_internal fetch_missing_import_sources)",
        "endfunction()",
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}")',
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_OPTIONS_PROTO "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb")',
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_GENERATOR_SOURCES "")',
        'set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${CMAKE_COMMAND}")',
        f'set(PROTOCYTE_PROTOC_EXECUTABLE "{fake_protoc.as_posix()}")',
        f'set(PROTOCYTE_PROTOC_DEPENDENCY "{fake_protoc.as_posix()}")',
    ]
    for index, proto_name in enumerate(proto_names):
        lines.extend(
            [
                "protocyte_generate(",
                f"    TARGET generated_{index}",
                '    DESCRIPTOR_SET "${CMAKE_CURRENT_SOURCE_DIR}/descriptor_set.pb"',
                f'    OUT_DIR "{output_directory.as_posix()}"',
                f"    PROTOS {proto_name}",
                "    OPTIONS format=off",
            ]
        )
        if runtime_prefix is not None:
            lines.extend(
                [
                    "    EMIT_RUNTIME",
                    f"    RUNTIME_PREFIX {runtime_prefix}",
                ]
            )
        lines.append(")")
    lines.append("")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _configure_out_dir_owner_project(
    source_dir: Path,
    build_dir: Path,
    *extra_arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(build_dir),
            *extra_arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _build_out_dir_owner_project(
    build_dir: Path,
    target: str = "generated_0",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", target],
        check=False,
        capture_output=True,
        text=True,
    )


def _make_fake_protoc_fail_in_build(
    source_dir: Path,
    build_dir: Path,
    *,
    ready_path: Path | None = None,
    release_path: Path | None = None,
) -> None:
    fake_protoc_script = source_dir / "fake-protoc.py"
    failure_lines = [
        f"if Path.cwd().resolve() == Path({str(build_dir)!r}).resolve():",
    ]
    if ready_path is not None:
        assert release_path is not None
        failure_lines.extend(
            [
                f"    Path({str(ready_path)!r}).write_text('ready\\n', encoding='utf-8')",
                "    deadline = time.monotonic() + 30.0",
                f"    while not Path({str(release_path)!r}).exists():",
                "        if time.monotonic() >= deadline:",
                "            raise SystemExit(92)",
                "        time.sleep(0.01)",
            ]
        )
    else:
        assert release_path is None
    failure_lines.extend(
        [
            "    print('simulated protoc failure', file=sys.stderr)",
            "    raise SystemExit(23)",
            "",
        ]
    )
    original = fake_protoc_script.read_text(encoding="utf-8")
    instrumented = original.replace("import sys\n", "import sys\nimport time\n")
    instrumented = instrumented.replace(
        "for proto_name, paths in outputs.items():",
        "\n".join(failure_lines) + "for proto_name, paths in outputs.items():",
    )
    fake_protoc_script.write_text(instrumented, encoding="utf-8")


def _make_fake_protoc_hang_in_build(
    source_dir: Path,
    build_dir: Path,
    grandchild_ready: Path,
    child_survived: Path,
) -> None:
    fake_protoc_script = source_dir / "fake-protoc.py"
    original = fake_protoc_script.read_text(encoding="utf-8")
    grandchild = (
        "from pathlib import Path; import time; "
        f"Path({str(grandchild_ready)!r}).touch(); time.sleep(1); "
        f"Path({str(child_survived)!r}).touch()"
    )
    child = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"
    )
    hanging_protoc = "\n".join(
        [
            f"if Path.cwd().resolve() == Path({str(build_dir)!r}).resolve():",
            f"    subprocess.Popen([sys.executable, '-c', {child!r}])",
            "    time.sleep(30)",
        ]
    )
    instrumented = original.replace(
        "import sys\n", "import sys\nimport subprocess\nimport time\n"
    )
    instrumented = instrumented.replace(
        "for proto_name, paths in outputs.items():",
        hanging_protoc + "\nfor proto_name, paths in outputs.items():",
    )
    fake_protoc_script.write_text(instrumented, encoding="utf-8")


def _write_fault_instrumented_generation_script(script_dir: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    script_dir.mkdir()
    shutil.copy2(
        repo_root / "cmake" / "ProtocyteOutputSafety.cmake",
        script_dir / "ProtocyteOutputSafety.cmake",
    )
    shutil.copy2(
        repo_root / "cmake" / "ProtocyteProcess.cmake",
        script_dir / "ProtocyteProcess.cmake",
    )
    generation_source = (repo_root / "cmake" / "ProtocyteGenerate.cmake").read_text(
        encoding="utf-8"
    )
    staging_anchor = '        file(WRITE "${owner_staging}" "${transaction_owner}")\n'
    staging_instrumentation = (
        "        if(\n"
        "            DEFINED PROTOCYTE_TEST_FAIL_OWNER_STAGING_INDEX\n"
        "            AND owner_stage_index EQUAL PROTOCYTE_TEST_FAIL_OWNER_STAGING_INDEX\n"
        "        )\n"
        '            file(MAKE_DIRECTORY "${owner_staging}")\n'
        "        endif()\n" + staging_anchor
    )
    assert generation_source.count(staging_anchor) == 1
    generation_source = generation_source.replace(
        staging_anchor, staging_instrumentation
    )

    publication_anchor = (
        '        list(APPEND published_owner_markers "${owner_marker}")\n'
    )
    publication_instrumentation = (
        publication_anchor
        + '        math(EXPR published_owner_count "${owner_marker_index} + 1")\n'
        + "        if(\n"
        + "            DEFINED PROTOCYTE_TEST_ABORT_AFTER_OWNER_PUBLICATIONS\n"
        + "            AND published_owner_count EQUAL PROTOCYTE_TEST_ABORT_AFTER_OWNER_PUBLICATIONS\n"
        + "        )\n"
        + '            message(FATAL_ERROR "injected ownership publication termination")\n'
        + "        endif()\n"
    )
    assert generation_source.count(publication_anchor) == 1
    generation_source = generation_source.replace(
        publication_anchor, publication_instrumentation
    )
    instrumented_script = script_dir / "ProtocyteGenerate.cmake"
    instrumented_script.write_text(generation_source, encoding="utf-8")
    return instrumented_script


def _run_direct_owner_generation(
    source_dir: Path,
    build_dir: Path,
    output_directory: Path,
    generation_script: Path,
    *extra_arguments: str,
) -> subprocess.CompletedProcess[str]:
    build_dir.mkdir()
    argument_file = build_dir / "arguments.rsp"
    argument_file.write_text("", encoding="utf-8")
    generated_outputs = (
        output_directory / "demo_0.protocyte.hpp",
        output_directory / "demo_0.protocyte.cpp",
    )
    output_keys = sorted(_filesystem_identity_hash(path) for path in generated_outputs)
    lock_manifest = build_dir / "locks.list"
    lock_manifest.write_text("\n".join(output_keys) + "\n", encoding="utf-8")
    ownership_manifest = build_dir / "ownership-manifest"
    ownership_manifest.mkdir()
    (ownership_manifest / "output-root.path").write_text(
        output_directory.as_posix(), encoding="utf-8"
    )
    for output_path in generated_outputs:
        output_key = _filesystem_identity_hash(output_path)
        (ownership_manifest / f"{output_key}.path").write_text(
            output_path.as_posix(), encoding="utf-8"
        )
    owner_marker, owner_lock = _out_dir_owner_record_paths(output_directory)
    fake_protoc = source_dir / ("fake-protoc.cmd" if os.name == "nt" else "fake-protoc")
    return subprocess.run(
        [
            "cmake",
            f"-DPROTOC_EXECUTABLE={fake_protoc}",
            f"-DARGUMENT_FILE={argument_file}",
            "-DGENERATION_TARGET=interrupted_codegen",
            f"-DGENERATION_WORKING_DIRECTORY={build_dir}",
            f"-DLOCK_DIRECTORY={source_dir.parent / 'output-locks'}",
            "-DLOCK_DIRECTORY_IDENTITY_SHA256="
            f"{_filesystem_identity_hash(source_dir.parent / 'output-locks')}",
            f"-DLOCK_MANIFEST={lock_manifest}",
            f"-DOUTPUT_DIRECTORY={output_directory}",
            f"-DOUT_DIR_OWNER_MARKER={owner_marker}",
            f"-DOUT_DIR_OWNER_LOCK={owner_lock}",
            f"-DBUILD_OWNER_HASH={_build_tree_owner_hash(build_dir)}",
            f"-DOWNERSHIP_MANIFEST_DIR={ownership_manifest}",
            "-DSOURCE_DIRECTORY_HEX=00",
            *extra_arguments,
            "-P",
            str(generation_script),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _out_dir_snapshot(output_directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(output_directory).as_posix(): path.read_bytes()
        for path in output_directory.rglob("*")
        if path.is_file()
    }


def test_out_dir_owner_allows_same_build_tree_targets_and_configurations(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory, target_count=2)

    first = _configure_out_dir_owner_project(
        source_dir, build_dir, "-DCMAKE_BUILD_TYPE=Debug"
    )
    second = _configure_out_dir_owner_project(
        source_dir, build_dir, "-DCMAKE_BUILD_TYPE=Release"
    )

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    marker, lock = _out_dir_owner_record_paths(output_directory)
    assert not marker.exists()
    for target in ("generated_0", "generated_1"):
        built = _build_out_dir_owner_project(build_dir, target)
        assert built.returncode == 0, built.stdout + built.stderr
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(build_dir)
    )
    assert lock.is_file()


def test_second_build_tree_rejects_shared_out_dir_without_mutation(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    first_build_dir = tmp_path / "build-first"
    second_build_dir = tmp_path / "build-second"
    output_directory = tmp_path / "generated"
    output_directory.mkdir()
    (output_directory / "consumer-owned.txt").write_text("preserve\n", encoding="utf-8")
    _write_out_dir_owner_project(source_dir, output_directory)

    first = _configure_out_dir_owner_project(source_dir, first_build_dir)
    second = _configure_out_dir_owner_project(source_dir, second_build_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    first_build = _build_out_dir_owner_project(first_build_dir)
    assert first_build.returncode == 0, first_build.stdout + first_build.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    marker_before = marker.read_bytes()
    outputs_before = _out_dir_snapshot(output_directory)

    second_build = _build_out_dir_owner_project(second_build_dir)

    assert second_build.returncode != 0
    output = " ".join((second_build.stdout + second_build.stderr).split())
    assert "ownership belongs to a different build tree" in output
    assert "No generated output was changed" in output
    assert marker.read_bytes() == marker_before
    assert _out_dir_snapshot(output_directory) == outputs_before


def test_alternate_lock_root_after_cache_deletion_cannot_reclaim_out_dir_owner(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    first_build_dir = tmp_path / "build-first"
    second_build_dir = tmp_path / "build-second"
    output_directory = tmp_path / "generated"
    first_lock_root = tmp_path / "output-locks-first"
    second_lock_root = tmp_path / "output-locks-second"
    _write_out_dir_owner_project(
        source_dir,
        output_directory,
        output_lock_root=first_lock_root,
    )

    configured = _configure_out_dir_owner_project(source_dir, first_build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    built = _build_out_dir_owner_project(first_build_dir)
    assert built.returncode == 0, built.stdout + built.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    owner_fields = dict(
        line.split("=", maxsplit=1)
        for line in marker.read_text(encoding="utf-8").splitlines()
    )
    witness = _owner_transaction_record(
        marker, owner_fields["transaction-sha256"], "committed"
    )
    marker_before = marker.read_bytes()
    witness_before = witness.read_bytes()
    outputs_before = _out_dir_snapshot(output_directory)
    shutil.rmtree(first_lock_root)

    _write_out_dir_owner_project(
        source_dir,
        output_directory,
        output_lock_root=second_lock_root,
    )
    contender = _configure_out_dir_owner_project(source_dir, second_build_dir)

    assert contender.returncode != 0
    output = " ".join((contender.stdout + contender.stderr).split())
    assert "owned by a different or deleted CMake build tree" in output
    assert marker.read_bytes() == marker_before
    assert witness.read_bytes() == witness_before
    assert _out_dir_snapshot(output_directory) == outputs_before
    assert not first_lock_root.exists()
    assert not list(second_lock_root.glob("*.owner"))


def test_missing_transaction_witness_is_not_treated_as_interrupted_publication(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    first_build_dir = tmp_path / "build-first"
    contender_build_dir = tmp_path / "build-contender"
    output_directory = tmp_path / "generated"
    lock_root = tmp_path / "output-locks"
    _write_out_dir_owner_project(source_dir, output_directory)

    configured = _configure_out_dir_owner_project(source_dir, first_build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    built = _build_out_dir_owner_project(first_build_dir)
    assert built.returncode == 0, built.stdout + built.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    owner_fields = dict(
        line.split("=", maxsplit=1)
        for line in marker.read_text(encoding="utf-8").splitlines()
    )
    witness = _owner_transaction_record(
        marker, owner_fields["transaction-sha256"], "committed"
    )
    owner_records = [marker, *lock_root.glob("*.owner")]
    owner_records_before = {path: path.read_bytes() for path in owner_records}
    outputs_before = _out_dir_snapshot(output_directory)
    witness.unlink()

    contender = _configure_out_dir_owner_project(source_dir, contender_build_dir)

    assert contender.returncode != 0
    output = " ".join((contender.stdout + contender.stderr).split()).replace("\\", "/")
    assert "missing or unverifiable transaction witness" in output
    assert any(path.as_posix() in output for path in owner_records if path != marker)
    assert witness.as_posix() in output
    assert "Choose disjoint generated outputs" in output
    assert "after confirming no build uses the output" in output
    assert {path: path.read_bytes() for path in owner_records} == owner_records_before
    assert _out_dir_snapshot(output_directory) == outputs_before


def test_output_lock_root_rejects_symbolic_link_or_junction_alias(
    tmp_path: Path,
) -> None:
    physical_lock_root = tmp_path / "physical-output-locks"
    linked_lock_root = tmp_path / "linked-output-locks"
    physical_lock_root.mkdir()
    _create_generated_output_directory_link(linked_lock_root, physical_lock_root)
    try:
        result = _configure_cmake_snippet(
            tmp_path,
            "\n".join(
                [
                    f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{linked_lock_root.as_posix()}")',
                    "_protocyte_shared_output_lock_directory(lock_directory)",
                ]
            ),
        )

        assert result.returncode != 0
        output = " ".join((result.stdout + result.stderr).split())
        assert "must not contain symbolic-link or junction components" in output
    finally:
        if linked_lock_root.exists():
            linked_lock_root.unlink()


def test_build_rejects_output_lock_root_replaced_by_junction_after_configure(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    lock_root = tmp_path / "output-locks"
    displaced_lock_root = tmp_path / "configured-output-locks"
    redirected_lock_root = tmp_path / "redirected-output-locks"
    _write_out_dir_owner_project(
        source_dir,
        output_directory,
        output_lock_root=lock_root,
    )
    configured = _configure_out_dir_owner_project(source_dir, build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr

    lock_root.rename(displaced_lock_root)
    redirected_lock_root.mkdir()
    _create_generated_output_directory_link(lock_root, redirected_lock_root)
    try:
        built = _build_out_dir_owner_project(build_dir)

        assert built.returncode != 0
        output = " ".join((built.stdout + built.stderr).split()).replace("\\", "/")
        assert "now contains a symbolic-link or junction component" in output
        assert lock_root.as_posix() in output
        assert "reconfigure before building" in output
        marker, _ = _out_dir_owner_record_paths(output_directory)
        assert not marker.exists()
        assert not list(redirected_lock_root.iterdir())
        assert not list(displaced_lock_root.glob("*.owner"))
        assert not any(output_directory.rglob("*"))
    finally:
        if lock_root.exists():
            lock_root.unlink()


def test_nested_configure_graph_rejects_split_output_lock_namespaces(
    tmp_path: Path,
) -> None:
    first_lock_root = tmp_path / "output-locks-first"
    second_lock_root = tmp_path / "output-locks-second"
    first_lock_root.mkdir()
    second_lock_root.mkdir()

    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{first_lock_root.as_posix()}")',
                "_protocyte_shared_output_lock_directory(parent_lock_directory)",
                "add_subdirectory(child)",
            ]
        ),
        files={
            "child/CMakeLists.txt": "\n".join(
                [
                    f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{second_lock_root.as_posix()}")',
                    "_protocyte_shared_output_lock_directory(child_lock_directory)",
                    "",
                ]
            )
        },
    )

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split()).replace("\\", "/")
    assert "same canonical output-lock namespace" in output
    assert first_lock_root.as_posix() in output
    assert second_lock_root.as_posix() in output
    assert "Set PROTOCYTE_OUTPUT_LOCK_ROOT once" in output


def test_deleted_build_tree_does_not_release_out_dir_ownership(tmp_path: Path) -> None:
    source_dir = tmp_path / "project"
    first_build_dir = tmp_path / "build-first"
    second_build_dir = tmp_path / "build-second"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)

    first = _configure_out_dir_owner_project(source_dir, first_build_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    first_build = _build_out_dir_owner_project(first_build_dir)
    assert first_build.returncode == 0, first_build.stdout + first_build.stderr
    shutil.rmtree(first_build_dir)

    second = _configure_out_dir_owner_project(source_dir, second_build_dir)

    assert second.returncode != 0
    output = " ".join((second.stdout + second.stderr).split())
    assert "owned by a different or deleted CMake build tree" in output
    assert "remove" in output and "manually" in output


def test_manual_owner_cleanup_allows_deliberate_out_dir_transfer(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    first_build_dir = tmp_path / "build-first"
    second_build_dir = tmp_path / "build-second"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)

    first = _configure_out_dir_owner_project(source_dir, first_build_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    first_build = _build_out_dir_owner_project(first_build_dir)
    assert first_build.returncode == 0, first_build.stdout + first_build.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    first_owner = marker.read_text(encoding="utf-8")
    shutil.rmtree(first_build_dir)
    marker.unlink()
    for output_owner in (tmp_path / "output-locks").glob("*.owner"):
        output_owner.unlink()

    second = _configure_out_dir_owner_project(source_dir, second_build_dir)

    assert second.returncode == 0, second.stdout + second.stderr
    second_build = _build_out_dir_owner_project(second_build_dir)
    assert second_build.returncode == 0, second_build.stdout + second_build.stderr
    second_owner = marker.read_text(encoding="utf-8")
    assert second_owner != first_owner
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(second_build_dir)
    )


def test_recreated_same_canonical_build_path_retains_out_dir_ownership(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)

    first = _configure_out_dir_owner_project(source_dir, build_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    first_build = _build_out_dir_owner_project(build_dir)
    assert first_build.returncode == 0, first_build.stdout + first_build.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    owner_before = marker.read_bytes()
    shutil.rmtree(build_dir)

    recreated = _configure_out_dir_owner_project(source_dir, build_dir)

    assert recreated.returncode == 0, recreated.stdout + recreated.stderr
    (output_directory / "demo_0.protocyte.hpp").unlink()
    recreated_build = _build_out_dir_owner_project(build_dir)
    assert recreated_build.returncode == 0, (
        recreated_build.stdout + recreated_build.stderr
    )
    assert marker.read_bytes() == owner_before


def test_malformed_out_dir_owner_record_rejects_without_mutation(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    output_directory.mkdir()
    sentinel = output_directory / "consumer-owned.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    _write_out_dir_owner_project(source_dir, output_directory)
    marker, _ = _out_dir_owner_record_paths(output_directory)
    marker.write_text("version=1\nbuild-tree-sha256=invalid\n", encoding="utf-8")
    before = _out_dir_snapshot(output_directory)

    result = _configure_out_dir_owner_project(source_dir, build_dir)

    assert result.returncode != 0
    output = " ".join((result.stdout + result.stderr).split())
    assert "ownership record" in output and "is malformed" in output
    assert "will not reclaim" in output
    assert _out_dir_snapshot(output_directory) == before
    assert marker.read_text(encoding="utf-8") == (
        "version=1\nbuild-tree-sha256=invalid\n"
    )


def test_out_dir_owner_record_contains_no_private_path(tmp_path: Path) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "private-build-name"
    output_directory = tmp_path / "private-output-name"
    _write_out_dir_owner_project(source_dir, output_directory)

    result = _configure_out_dir_owner_project(source_dir, build_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    built = _build_out_dir_owner_project(build_dir)
    assert built.returncode == 0, built.stdout + built.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    owner_records = [marker, *(tmp_path / "output-locks").glob("*.owner")]
    assert len(owner_records) == 3
    for owner_record in owner_records:
        payload = owner_record.read_text(encoding="utf-8")
        assert _committed_owner_build_hash(owner_record, marker) == (
            _build_tree_owner_hash(build_dir)
        )
        assert str(tmp_path).lower() not in payload.lower()
        assert build_dir.name not in payload
        assert output_directory.name not in payload
    transaction_records = list(marker.parent.glob(f"{marker.name}.*.committed"))
    assert len(transaction_records) == 1
    transaction_payload = transaction_records[0].read_text(encoding="utf-8")
    assert str(tmp_path).lower() not in transaction_payload.lower()
    assert build_dir.name not in transaction_payload
    assert output_directory.name not in transaction_payload


def test_failed_validation_does_not_poison_out_dir_ownership(tmp_path: Path) -> None:
    source_dir = tmp_path / "project"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(
        source_dir,
        output_directory,
    )
    with (source_dir / "CMakeLists.txt").open("a", encoding="utf-8") as project:
        project.write('message(FATAL_ERROR "later unrelated configure failure")\n')

    invalid = _configure_out_dir_owner_project(source_dir, tmp_path / "bad-build")

    assert invalid.returncode != 0
    assert "later unrelated configure failure" in invalid.stdout + invalid.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    assert not marker.exists()
    assert not list((tmp_path / "output-locks").glob("*.owner"))

    _write_out_dir_owner_project(source_dir, output_directory)
    corrected = _configure_out_dir_owner_project(source_dir, tmp_path / "good-build")
    assert corrected.returncode == 0, corrected.stdout + corrected.stderr


def test_failed_first_generation_does_not_block_fresh_out_dir_owner(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    failed_build_dir = tmp_path / "failed-build"
    fresh_build_dir = tmp_path / "fresh-build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)
    for build_dir in (failed_build_dir, fresh_build_dir):
        configured = _configure_out_dir_owner_project(source_dir, build_dir)
        assert configured.returncode == 0, configured.stdout + configured.stderr
    _make_fake_protoc_fail_in_build(source_dir, failed_build_dir)

    failed = _build_out_dir_owner_project(failed_build_dir)

    assert failed.returncode != 0
    assert "simulated protoc failure" in failed.stdout + failed.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    assert not marker.exists()
    assert not list((tmp_path / "output-locks").glob("*.owner"))

    recovered = _build_out_dir_owner_project(fresh_build_dir)

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(fresh_build_dir)
    )
    assert (output_directory / "demo_0.protocyte.hpp").is_file()
    assert (output_directory / "demo_0.protocyte.cpp").is_file()


@pytest.mark.parametrize("published_owner_count", [1, 2, 3])
def test_incomplete_owner_publication_is_recovered_after_each_step(
    tmp_path: Path,
    published_owner_count: int,
) -> None:
    source_dir = tmp_path / "project"
    interrupted_build_dir = tmp_path / "interrupted-build"
    fresh_build_dir = tmp_path / "fresh-build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)
    instrumented_script = _write_fault_instrumented_generation_script(
        tmp_path / "instrumented-cmake"
    )

    interrupted = _run_direct_owner_generation(
        source_dir,
        interrupted_build_dir,
        output_directory,
        instrumented_script,
        f"-DPROTOCYTE_TEST_ABORT_AFTER_OWNER_PUBLICATIONS={published_owner_count}",
    )

    assert interrupted.returncode != 0
    assert "injected ownership publication termination" in (
        interrupted.stdout + interrupted.stderr
    )
    marker, _ = _out_dir_owner_record_paths(output_directory)
    assert marker.is_file()
    output_owners = list((tmp_path / "output-locks").glob("*.owner"))
    assert len(output_owners) == published_owner_count - 1
    assert not list(marker.parent.glob(f"{marker.name}.*.committed"))

    configured = _configure_out_dir_owner_project(source_dir, fresh_build_dir)

    assert configured.returncode == 0, configured.stdout + configured.stderr
    assert not marker.exists()
    assert not list((tmp_path / "output-locks").glob("*.owner"))
    recovered = _build_out_dir_owner_project(fresh_build_dir)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(fresh_build_dir)
    )


def test_later_owner_staging_write_failure_publishes_no_durable_claim(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    failed_build_dir = tmp_path / "failed-build"
    fresh_build_dir = tmp_path / "fresh-build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)
    instrumented_script = _write_fault_instrumented_generation_script(
        tmp_path / "instrumented-cmake"
    )

    failed = _run_direct_owner_generation(
        source_dir,
        failed_build_dir,
        output_directory,
        instrumented_script,
        "-DPROTOCYTE_TEST_FAIL_OWNER_STAGING_INDEX=3",
    )

    assert failed.returncode != 0
    marker, _ = _out_dir_owner_record_paths(output_directory)
    assert not marker.exists()
    assert not list((tmp_path / "output-locks").glob("*.owner"))
    assert not list(marker.parent.glob(f"{marker.name}.*.committed"))

    configured = _configure_out_dir_owner_project(source_dir, fresh_build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    recovered = _build_out_dir_owner_project(fresh_build_dir)
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(fresh_build_dir)
    )


def test_nested_out_dirs_cannot_claim_the_same_generated_output(
    tmp_path: Path,
) -> None:
    output_directory = tmp_path / "generated"
    first_source = tmp_path / "project-first"
    second_source = tmp_path / "project-second"
    _write_out_dir_owner_project(
        first_source,
        output_directory,
        proto_names=("nested/demo.proto",),
    )
    _write_out_dir_owner_project(
        second_source,
        output_directory / "nested",
        proto_names=("demo.proto",),
    )

    first_build_dir = tmp_path / "build-first"
    second_build_dir = tmp_path / "build-second"
    first = _configure_out_dir_owner_project(first_source, first_build_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    second = _configure_out_dir_owner_project(second_source, second_build_dir)
    assert second.returncode == 0, second.stdout + second.stderr
    first_build = _build_out_dir_owner_project(first_build_dir)
    assert first_build.returncode == 0, first_build.stdout + first_build.stderr
    before = _out_dir_snapshot(output_directory)
    output_owner_records = list((tmp_path / "output-locks").glob("*.owner"))
    assert len(output_owner_records) == 2
    output_owner_payload = output_owner_records[0].read_text(encoding="utf-8")
    output_owner_fields = dict(
        line.split("=", maxsplit=1) for line in output_owner_payload.splitlines()
    )
    second_root_marker, _ = _out_dir_owner_record_paths(output_directory / "nested")
    expected_witness = _owner_transaction_record(
        second_root_marker,
        output_owner_fields["transaction-sha256"],
        "committed",
    )

    second_build = _build_out_dir_owner_project(second_build_dir)

    assert second_build.returncode != 0
    output = " ".join((second_build.stdout + second_build.stderr).split()).replace(
        "\\", "/"
    )
    assert "missing or unverifiable transaction witness" in output
    assert any(owner.as_posix() in output for owner in output_owner_records)
    assert expected_witness.as_posix() in output
    assert "will not reclaim the output automatically" in output
    assert "Choose disjoint generated outputs" in output
    assert "after confirming no build uses the output" in output
    assert _out_dir_snapshot(output_directory) == before


def test_build_time_missing_root_witness_diagnostic_is_actionable(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    lock_root = tmp_path / "output-locks"
    _write_out_dir_owner_project(source_dir, output_directory)
    configured = _configure_out_dir_owner_project(source_dir, build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    built = _build_out_dir_owner_project(build_dir)
    assert built.returncode == 0, built.stdout + built.stderr

    marker, _ = _out_dir_owner_record_paths(output_directory)
    marker_before = marker.read_bytes()
    owner_fields = dict(
        line.split("=", maxsplit=1)
        for line in marker.read_text(encoding="utf-8").splitlines()
    )
    witness = _owner_transaction_record(
        marker, owner_fields["transaction-sha256"], "committed"
    )
    witness.unlink()
    for output_owner in lock_root.glob("*.owner"):
        output_owner.unlink()
    (output_directory / "demo_0.protocyte.hpp").unlink()
    outputs_before = _out_dir_snapshot(output_directory)

    failed = _build_out_dir_owner_project(build_dir)

    assert failed.returncode != 0
    output = " ".join((failed.stdout + failed.stderr).split()).replace("\\", "/")
    assert "OUT_DIR ownership record" in output
    assert marker.as_posix() in output
    assert witness.as_posix() in output
    assert "will not reclaim the OUT_DIR automatically" in output
    assert "choose a different OUT_DIR" in output
    assert "after confirming no build uses the OUT_DIR" in output
    assert marker.read_bytes() == marker_before
    assert _out_dir_snapshot(output_directory) == outputs_before


def test_transferred_out_dir_revokes_an_already_configured_build(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    first_build_dir = tmp_path / "build-first"
    second_build_dir = tmp_path / "build-second"
    output_directory = tmp_path / "generated"
    output_directory.mkdir()
    sentinel = output_directory / "consumer-owned.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    _write_out_dir_owner_project(source_dir, output_directory)

    first = _configure_out_dir_owner_project(source_dir, first_build_dir)
    assert first.returncode == 0, first.stdout + first.stderr
    first_build = _build_out_dir_owner_project(first_build_dir)
    assert first_build.returncode == 0, first_build.stdout + first_build.stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    marker.unlink()
    for output_owner in (tmp_path / "output-locks").glob("*.owner"):
        output_owner.unlink()
    second = _configure_out_dir_owner_project(source_dir, second_build_dir)
    assert second.returncode == 0, second.stdout + second.stderr
    second_build = _build_out_dir_owner_project(second_build_dir)
    assert second_build.returncode == 0, second_build.stdout + second_build.stderr
    generated_header = output_directory / "demo_0.protocyte.hpp"
    generated_header.unlink()
    before = _out_dir_snapshot(output_directory)

    stale_build = _build_out_dir_owner_project(first_build_dir)

    assert stale_build.returncode != 0
    output = " ".join((stale_build.stdout + stale_build.stderr).split())
    assert "ownership belongs to a different build tree" in output
    assert _out_dir_snapshot(output_directory) == before


def test_generation_rejects_nested_output_directory_links(tmp_path: Path) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(
        source_dir,
        output_directory,
        proto_names=("api/demo.proto",),
        runtime_prefix="api",
    )
    configured = _configure_out_dir_owner_project(source_dir, build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    initial_build = _build_out_dir_owner_project(build_dir)
    assert initial_build.returncode == 0, initial_build.stdout + initial_build.stderr

    linked_directory = output_directory / "api"
    shutil.rmtree(linked_directory)
    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()
    outside_outputs = {
        outside_directory / "demo.protocyte.hpp": b"outside header\n",
        outside_directory / "demo.protocyte.cpp": b"outside source\n",
        outside_directory / "runtime.hpp": b"outside runtime\n",
    }
    for output, content in outside_outputs.items():
        output.write_bytes(content)
    _create_generated_output_directory_link(linked_directory, outside_directory)
    descriptor_set = source_dir / "descriptor_set.pb"
    future_time = time.time() + 2.0
    os.utime(descriptor_set, (future_time, future_time))

    try:
        rebuilt = _build_out_dir_owner_project(build_dir)
        assert rebuilt.returncode != 0
        output = " ".join((rebuilt.stdout + rebuilt.stderr).split())
        assert "canonical containment check failed" in output
        for outside_output, content in outside_outputs.items():
            assert outside_output.read_bytes() == content
    finally:
        linked_directory.unlink()


def test_retirement_rejects_nested_output_directory_links(tmp_path: Path) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(
        source_dir,
        output_directory,
        proto_names=("api/demo.proto",),
        runtime_prefix="api",
    )
    configured = _configure_out_dir_owner_project(source_dir, build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    initial_build = _build_out_dir_owner_project(build_dir)
    assert initial_build.returncode == 0, initial_build.stdout + initial_build.stderr

    linked_directory = output_directory / "api"
    generated_contents = {
        path.name: path.read_bytes()
        for path in linked_directory.iterdir()
        if path.is_file()
    }
    assert set(generated_contents) == {
        "demo.protocyte.cpp",
        "demo.protocyte.hpp",
        "runtime.hpp",
    }
    shutil.rmtree(linked_directory)
    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()
    for name, content in generated_contents.items():
        (outside_directory / name).write_bytes(content)
    _create_generated_output_directory_link(linked_directory, outside_directory)
    repo_root = Path(__file__).resolve().parents[1]
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(retired_output_containment LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{(tmp_path / "output-locks").as_posix()}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        retired = _configure_out_dir_owner_project(source_dir, build_dir)
        assert retired.returncode == 0, retired.stdout + retired.stderr
        output = " ".join((retired.stdout + retired.stderr).split())
        assert "canonical containment under the recorded OUT_DIR" in output
        for name, content in generated_contents.items():
            assert (outside_directory / name).read_bytes() == content
        pending_manifests = [
            path
            for path in (build_dir / "CMakeFiles/protocyte-owned-outputs").iterdir()
            if list(path.glob("*.pending"))
        ]
        assert len(pending_manifests) == len(generated_contents)
        assert all(list(path.glob("*.sha256")) for path in pending_manifests)
    finally:
        linked_directory.unlink()


def test_retirement_rechecks_containment_immediately_before_removal(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "generated" / "demo.protocyte.hpp"
    output_path.parent.mkdir()
    output_path.write_text("generated\n", encoding="utf-8")
    output_key = _filesystem_identity_hash(output_path)
    output_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    lock_directory = tmp_path / "output-locks"
    lock_directory.mkdir()
    owner_marker = lock_directory / f"{output_key}.owner"
    owner_payload = (
        f"version=1\nbuild-tree-sha256={_build_tree_owner_hash(tmp_path / 'build')}\n"
    )
    owner_marker.write_text(owner_payload, encoding="utf-8")
    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()
    outside_output = outside_directory / output_path.name
    outside_output.write_text("outside\n", encoding="utf-8")
    displaced_directory = tmp_path / "displaced-generated"
    swap_script = tmp_path / "swap-output-directory.py"
    swap_script.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import os",
                "import subprocess",
                "import sys",
                "from pathlib import Path",
                "",
                "generated, displaced, outside = map(Path, sys.argv[1:])",
                "generated.rename(displaced)",
                'if os.name == "nt":',
                "    subprocess.run(",
                '        ["cmd.exe", "/d", "/c", "mklink", "/J", str(generated), str(outside)],',
                "        check=True,",
                "        capture_output=True,",
                "    )",
                "else:",
                "    generated.symlink_to(outside, target_is_directory=True)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{lock_directory.as_posix()}")',
                "function(_protocyte_generated_output_path_is_safe out_var output_path output_root)",
                "    get_property(safety_call_count GLOBAL PROPERTY PROTOCYTE_TEST_SAFETY_CALL_COUNT)",
                '    if(safety_call_count STREQUAL "")',
                "        set(safety_call_count 0)",
                "    endif()",
                "    if(safety_call_count EQUAL 1)",
                "        execute_process(",
                f'            COMMAND "{Path(sys.executable).as_posix()}" "{swap_script.as_posix()}"',
                f'                "{output_path.parent.as_posix()}"',
                f'                "{displaced_directory.as_posix()}"',
                f'                "{outside_directory.as_posix()}"',
                "            COMMAND_ERROR_IS_FATAL ANY",
                "        )",
                "    endif()",
                '    math(EXPR safety_call_count "${safety_call_count} + 1")',
                "    set_property(GLOBAL PROPERTY PROTOCYTE_TEST_SAFETY_CALL_COUNT ${safety_call_count})",
                "    _protocyte_generated_output_path_is_canonically_safe(",
                "        canonical_result",
                '        "${output_path}"',
                '        "${output_root}"',
                "    )",
                '    set(${out_var} "${canonical_result}" PARENT_SCOPE)',
                "endfunction()",
                "_protocyte_retire_owned_output(",
                "    retire_result",
                f'    "{output_path.as_posix()}"',
                f"    {output_key}",
                f"    {output_hash}",
                f'    "{output_path.parent.as_posix()}"',
                ")",
                'file(WRITE "${CMAKE_BINARY_DIR}/retire-result.txt" "${retire_result}")',
            ]
        ),
    )

    try:
        assert result.returncode == 0, result.stdout + result.stderr
        assert (tmp_path / "build" / "retire-result.txt").read_text(
            encoding="utf-8"
        ) == "unsafe"
        assert outside_output.read_text(encoding="utf-8") == "outside\n"
        assert (displaced_directory / output_path.name).read_text(
            encoding="utf-8"
        ) == "generated\n"
        assert owner_marker.read_text(encoding="utf-8") == owner_payload
    finally:
        if displaced_directory.exists():
            output_path.parent.unlink()


def test_unsafe_current_output_reconfigure_preserves_cleanup_fingerprints(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(
        source_dir,
        output_directory,
        proto_names=("api/demo.proto",),
        runtime_prefix="api",
    )
    configured = _configure_out_dir_owner_project(source_dir, build_dir)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    initial_build = _build_out_dir_owner_project(build_dir)
    assert initial_build.returncode == 0, initial_build.stdout + initial_build.stderr

    linked_directory = output_directory / "api"
    generated_contents = {
        path.name: path.read_bytes()
        for path in linked_directory.iterdir()
        if path.is_file()
    }
    shutil.rmtree(linked_directory)
    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()
    for name, content in generated_contents.items():
        (outside_directory / name).write_bytes(content)
    _create_generated_output_directory_link(linked_directory, outside_directory)
    try:
        reconfigured = _configure_out_dir_owner_project(source_dir, build_dir)
        assert reconfigured.returncode == 0, reconfigured.stdout + reconfigured.stderr
        current_manifests = list(
            (build_dir / "CMakeFiles/protocyte-owned-outputs").iterdir()
        )
        assert len(current_manifests) == 1
        assert len(list(current_manifests[0].glob("*.sha256"))) == len(
            generated_contents
        )
    finally:
        linked_directory.unlink()

    linked_directory.mkdir()
    for name, content in generated_contents.items():
        (linked_directory / name).write_bytes(content)
    repo_root = Path(__file__).resolve().parents[1]
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(retired_output_recovery LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{(tmp_path / "output-locks").as_posix()}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    retired = _configure_out_dir_owner_project(source_dir, build_dir)

    assert retired.returncode == 0, retired.stdout + retired.stderr
    assert not any(linked_directory.iterdir())
    for name, content in generated_contents.items():
        assert (outside_directory / name).read_bytes() == content
    pending_manifests = [
        path
        for path in (build_dir / "CMakeFiles/protocyte-owned-outputs").iterdir()
        if list(path.glob("*.pending"))
    ]
    assert not pending_manifests


def test_retired_output_cleanup_releases_matching_owner_record(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "demo.protocyte.hpp"
    output_path.parent.mkdir()
    output_path.write_text("generated\n", encoding="utf-8")
    output_key = _filesystem_identity_hash(output_path)
    output_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    lock_directory = tmp_path / "output-locks"
    lock_directory.mkdir()
    owner_marker = lock_directory / f"{output_key}.owner"
    owner_marker.write_text(
        f"version=1\nbuild-tree-sha256={_build_tree_owner_hash(tmp_path / 'build')}\n",
        encoding="utf-8",
    )

    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{lock_directory.as_posix()}")',
                "_protocyte_retire_owned_output(",
                "    retire_result",
                f'    "{output_path.as_posix()}"',
                f"    {output_key}",
                f"    {output_hash}",
                f'    "{output_path.parent.as_posix()}"',
                ")",
                'file(WRITE "${CMAKE_BINARY_DIR}/retire-result.txt" "${retire_result}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not output_path.exists()
    assert not owner_marker.exists()
    assert (lock_directory / f"{output_key}.lock").is_file()
    assert (tmp_path / "build" / "retire-result.txt").read_text(
        encoding="utf-8"
    ) == "released"


def test_retired_edited_output_keeps_its_owner_record(tmp_path: Path) -> None:
    output_path = tmp_path / "generated" / "demo.protocyte.hpp"
    output_path.parent.mkdir()
    output_path.write_text("edited\n", encoding="utf-8")
    output_key = _filesystem_identity_hash(output_path)
    lock_directory = tmp_path / "output-locks"
    lock_directory.mkdir()
    owner_marker = lock_directory / f"{output_key}.owner"
    owner_payload = (
        f"version=1\nbuild-tree-sha256={_build_tree_owner_hash(tmp_path / 'build')}\n"
    )
    owner_marker.write_text(owner_payload, encoding="utf-8")

    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{lock_directory.as_posix()}")',
                "_protocyte_retire_owned_output(",
                "    retire_result",
                f'    "{output_path.as_posix()}"',
                f"    {output_key}",
                f"    {'0' * 64}",
                f'    "{output_path.parent.as_posix()}"',
                ")",
                'file(WRITE "${CMAKE_BINARY_DIR}/retire-result.txt" "${retire_result}")',
            ]
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output_path.read_text(encoding="utf-8") == "edited\n"
    assert owner_marker.read_text(encoding="utf-8") == owner_payload
    assert (tmp_path / "build" / "retire-result.txt").read_text(
        encoding="utf-8"
    ) == "preserved"


def test_concurrent_build_trees_atomically_race_for_out_dir_ownership(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    build_directories = (tmp_path / "build-first", tmp_path / "build-second")
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)
    for build_dir in build_directories:
        configured = _configure_out_dir_owner_project(source_dir, build_dir)
        assert configured.returncode == 0, configured.stdout + configured.stderr
    runner = _write_synchronized_build_runner(source_dir / "build_runner.py")
    gate = tmp_path / "start-builds"
    processes: list[subprocess.Popen[str]] = []
    ready_paths: list[Path] = []
    for index, build_dir in enumerate(build_directories):
        ready = tmp_path / f"build-{index}.ready"
        ready_paths.append(ready)
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
                    "--target",
                    "generated_0",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

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
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()

    return_codes = [process.returncode for process in processes]
    assert return_codes.count(0) == 1, "\n".join(build_outputs)
    assert sum(code != 0 for code in return_codes) == 1
    loser = return_codes.index(next(code for code in return_codes if code != 0))
    normalized_failure = " ".join(build_outputs[loser].split())
    assert "ownership belongs to a different build tree" in normalized_failure

    marker, lock = _out_dir_owner_record_paths(output_directory)
    winner = return_codes.index(0)
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(build_directories[winner])
    )
    assert lock.is_file()


def test_failed_generation_releases_waiting_out_dir_owner_contender(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    failed_build_dir = tmp_path / "failed-build"
    fresh_build_dir = tmp_path / "fresh-build"
    output_directory = tmp_path / "generated"
    _write_out_dir_owner_project(source_dir, output_directory)
    for build_dir in (failed_build_dir, fresh_build_dir):
        configured = _configure_out_dir_owner_project(source_dir, build_dir)
        assert configured.returncode == 0, configured.stdout + configured.stderr

    ready = tmp_path / "failing-protoc-ready"
    release = tmp_path / "release-failing-protoc"
    _make_fake_protoc_fail_in_build(
        source_dir,
        failed_build_dir,
        ready_path=ready,
        release_path=release,
    )
    failed_process = subprocess.Popen(
        ["cmake", "--build", str(failed_build_dir), "--target", "generated_0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    fresh_process: subprocess.Popen[str] | None = None
    try:
        deadline = time.monotonic() + 30.0
        while not ready.is_file():
            if failed_process.poll() is not None:
                stdout, stderr = failed_process.communicate()
                pytest.fail(
                    "the failing generation exited before acquiring ownership locks:\n"
                    + stdout
                    + stderr
                )
            if time.monotonic() >= deadline:
                pytest.fail("timed out waiting for the failing generation")
            time.sleep(0.01)

        fresh_process = subprocess.Popen(
            ["cmake", "--build", str(fresh_build_dir), "--target", "generated_0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.1)
        assert fresh_process.poll() is None
        release.write_text("release\n", encoding="utf-8")

        failed_stdout, failed_stderr = failed_process.communicate(timeout=120)
        fresh_stdout, fresh_stderr = fresh_process.communicate(timeout=120)
    finally:
        for process in (failed_process, fresh_process):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()

    assert failed_process.returncode != 0
    assert "simulated protoc failure" in failed_stdout + failed_stderr
    assert fresh_process.returncode == 0, fresh_stdout + fresh_stderr
    marker, _ = _out_dir_owner_record_paths(output_directory)
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(fresh_build_dir)
    )


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
    output_directory = tmp_path / "generated"
    generated_output = output_directory / "demo.protocyte.hpp"
    output_key = _filesystem_identity_hash(generated_output)
    lock_manifest.write_text(f"{output_key}\n", encoding="utf-8")
    owner_hash = "a" * 64
    owner_payload = f"version=1\nbuild-tree-sha256={owner_hash}\n"
    ownership_manifest = tmp_path / "ownership-manifest"
    ownership_manifest.mkdir()
    (ownership_manifest / "output-root.path").write_text(
        output_directory.as_posix(), encoding="utf-8"
    )
    (ownership_manifest / f"{output_key}.path").write_text(
        generated_output.as_posix(), encoding="utf-8"
    )
    out_dir_owner_marker = tmp_path / "out-dir.owner"
    out_dir_owner_lock = tmp_path / "out-dir.lock"
    out_dir_owner_marker.write_text(owner_payload, encoding="utf-8")
    lock_directory = tmp_path / "locks"
    lock_directory.mkdir()
    (lock_directory / f"{output_key}.owner").write_text(owner_payload, encoding="utf-8")
    result = subprocess.run(
        [
            "cmake",
            f"-DPROTOC_EXECUTABLE={failing_protoc}",
            f"-DARGUMENT_FILE={argument_file}",
            "-DGENERATION_TARGET=failing_codegen",
            f"-DGENERATION_WORKING_DIRECTORY={tmp_path}",
            f"-DLOCK_DIRECTORY={lock_directory}",
            "-DLOCK_DIRECTORY_IDENTITY_SHA256="
            f"{_filesystem_identity_hash(lock_directory)}",
            f"-DLOCK_MANIFEST={lock_manifest}",
            f"-DOUTPUT_DIRECTORY={output_directory}",
            f"-DOUT_DIR_OWNER_MARKER={out_dir_owner_marker}",
            f"-DOUT_DIR_OWNER_LOCK={out_dir_owner_lock}",
            f"-DBUILD_OWNER_HASH={owner_hash}",
            f"-DOWNERSHIP_MANIFEST_DIR={ownership_manifest}",
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


def test_generation_timeout_kills_wrapper_descendants_without_publishing_outputs(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "project"
    timed_out_build_dir = tmp_path / "timed-out-build"
    retry_build_dir = tmp_path / "retry-build"
    output_directory = tmp_path / "generated"
    grandchild_ready = tmp_path / "protoc-grandchild-ready"
    child_survived = tmp_path / "protoc-child-survived"
    _write_out_dir_owner_project(source_dir, output_directory)

    configured = _configure_out_dir_owner_project(
        source_dir,
        timed_out_build_dir,
        "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=0.5",
    )
    assert configured.returncode == 0, configured.stdout + configured.stderr
    _make_fake_protoc_hang_in_build(
        source_dir, timed_out_build_dir, grandchild_ready, child_survived
    )

    timed_out = _build_out_dir_owner_project(timed_out_build_dir)

    assert timed_out.returncode != 0
    output = " ".join((timed_out.stdout + timed_out.stderr).split())
    assert "timed out after 0.5 seconds" in output
    assert "before generation ownership was published" in output
    marker, _ = _out_dir_owner_record_paths(output_directory)
    assert not marker.exists()
    assert not any(output_directory.rglob("*"))
    assert grandchild_ready.is_file()
    time.sleep(1.25)
    assert not child_survived.exists()

    retry_configured = _configure_out_dir_owner_project(
        source_dir, retry_build_dir, "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=0.5"
    )
    assert retry_configured.returncode == 0, (
        retry_configured.stdout + retry_configured.stderr
    )
    retried = _build_out_dir_owner_project(retry_build_dir)
    assert retried.returncode == 0, retried.stdout + retried.stderr
    assert _committed_owner_build_hash(marker, marker) == (
        _build_tree_owner_hash(retry_build_dir)
    )


def test_dependency_scan_timeout_removes_partial_outputs_and_kills_descendants(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    descriptor = tmp_path / "dependency.pb"
    depfile = tmp_path / "dependency.d"
    argument_file = tmp_path / "arguments.rsp"
    argument_file.write_text("", encoding="utf-8")
    grandchild_ready = tmp_path / "dependency-reader-grandchild-ready"
    child_survived = tmp_path / "dependency-reader-child-survived"
    release_reader = tmp_path / "release-reader"
    protoc_script = tmp_path / "fake-protoc.py"
    protoc_script.write_text(
        f"from pathlib import Path\nPath({str(descriptor)!r}).write_bytes(b'partial descriptor')\n",
        encoding="utf-8",
    )
    reader_script = tmp_path / "reader.py"
    grandchild = (
        "from pathlib import Path; import time; "
        f"Path({str(grandchild_ready)!r}).touch(); time.sleep(1); "
        f"Path({str(child_survived)!r}).touch()"
    )
    child = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"
    )
    reader_script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import subprocess",
                "import sys",
                "import time",
                f"depfile = Path({str(depfile)!r})",
                "if Path(sys.argv[-1]).with_name('release-reader').exists():",
                "    depfile.write_text('complete: input.proto\\n', encoding='utf-8')",
                "    raise SystemExit(0)",
                "depfile.write_text('partial', encoding='utf-8')",
                f"subprocess.Popen([sys.executable, '-c', {child!r}])",
                "time.sleep(30)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def write_wrapper(path: Path, script: Path) -> Path:
        if os.name == "nt":
            wrapper = path.with_suffix(".cmd")
            wrapper.write_text(
                f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n',
                encoding="utf-8",
            )
        else:
            wrapper = path
            wrapper.write_text(
                "#!/usr/bin/env sh\n"
                f'exec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "$@"\n',
                encoding="utf-8",
            )
            wrapper.chmod(0o755)
        return wrapper

    protoc = write_wrapper(tmp_path / "fake-protoc", protoc_script)
    reader = write_wrapper(tmp_path / "hanging-reader", reader_script)
    command = [
        "cmake",
        f"-DPROTOC_EXECUTABLE={protoc}",
        f"-DARGUMENT_FILE={argument_file}",
        f"-DLOCK_FILE={tmp_path / 'dependency.lock'}",
        "-DPROTO_FILE=input.proto",
        f"-DSCAN_WORKING_DIRECTORY={tmp_path}",
        f"-DDEPENDENCY_READER={reader}",
        f"-DDEPENDENCY_DESCRIPTOR={descriptor}",
        f"-DDEPENDENCY_DEPFILE={depfile}",
        "-DDEPENDENCY_DEPFILE_TARGET=dependency.pb",
        "-DMANAGED_DEPENDENCY_READER=FALSE",
        "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=0.5",
        "-P",
        str(repo_root / "cmake" / "ProtocyteDependencyScan.cmake"),
    ]

    timed_out = subprocess.run(command, check=False, capture_output=True, text=True)

    assert timed_out.returncode != 0
    output = " ".join((timed_out.stdout + timed_out.stderr).split())
    assert "timed out while reading its descriptor after 0.5 seconds" in output
    assert "Partial dependency outputs were removed" in output
    assert not descriptor.exists()
    assert not depfile.exists()
    assert grandchild_ready.is_file()
    time.sleep(1.25)
    assert not child_survived.exists()

    release_reader.write_text("release\n", encoding="utf-8")
    retried = subprocess.run(command, check=False, capture_output=True, text=True)
    assert retried.returncode == 0, retried.stdout + retried.stderr
    assert descriptor.is_file()
    assert depfile.read_text(encoding="utf-8") == "complete: input.proto\n"


@pytest.mark.parametrize("protoc_selection", ["relative_path", "imported_target"])
def test_source_codegen_accepts_relative_protoc_and_tracks_tool_changes(
    tmp_path: Path, protoc_selection: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    real_protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, real_protoc)
    if shutil.which("ninja") is None:
        _real_protoc_requirement_unavailable(
            "Ninja is required to verify an incremental build"
        )

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
        _real_protoc_requirement_unavailable(
            "Ninja is required to verify an incremental build"
        )

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
    generation_responses = [
        response.read_text(encoding="utf-8").splitlines()
        for response in (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
        if "--descriptor_set_in=" in response.read_text(encoding="utf-8")
    ]
    assert len(generation_responses) == 1
    assert generation_responses[0][-1:] == ["nested/demo.proto"]
    assert "" not in generation_responses[0]


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


def test_source_mode_codegen_declares_normalized_generated_paths(
    tmp_path: Path,
) -> None:
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
    ("capability", "expected_error"),
    [
        (
            "group",
            'field "google.protobuf.Unsupported.Payload" uses unsupported groups',
        ),
        ("edition", "protobuf Editions are not supported in v1"),
        (
            "proto3-extension",
            'extension "google.protobuf.marker" extends unsupported proto3 target '
            '".google.protobuf.Unsupported"',
        ),
        (
            "internal-header",
            '"protocyte/options.proto" cannot have a generated header because it '
            "is reserved for Protocyte generator internals",
        ),
    ],
)
def test_descriptor_set_discover_reports_non_generatable_headers_at_configure_time(
    tmp_path: Path,
    capability: str,
    expected_error: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    descriptor_set = source_dir / "descriptor_set.pb"
    file_set = descriptor_pb2.FileDescriptorSet()

    if capability != "internal-header":
        dependency = file_set.file.add()
        dependency.name = "google/protobuf/unsupported.proto"
        dependency.package = "google.protobuf"
        dependency.syntax = "proto3"
        unsupported = dependency.message_type.add()
        unsupported.name = "Unsupported"
        if capability == "group":
            dependency.syntax = "proto2"
            group = unsupported.field.add()
            group.name = "Payload"
            group.number = 1
            group.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
            group.type = descriptor_pb2.FieldDescriptorProto.TYPE_GROUP
        elif capability == "edition":
            dependency.syntax = "editions"
            dependency.edition = descriptor_pb2.EDITION_2023
        else:
            extension = dependency.extension.add()
            extension.name = "marker"
            extension.number = 1000
            extension.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
            extension.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
            extension.extendee = ".google.protobuf.Unsupported"
        bridge = file_set.file.add()
        bridge.name = "google/protobuf/bridge.proto"
        bridge.package = "google.protobuf"
        bridge.syntax = "proto3"
        bridge.dependency.append(dependency.name)
        bridge.message_type.add().name = "Bridge"
        root = file_set.file.add()
        root.name = "api/request.proto"
        root.package = "api"
        root.syntax = "proto3"
        root.dependency.append(bridge.name)
        root.message_type.add().name = "Request"
    else:
        options = file_set.file.add()
        options.name = "protocyte/options.proto"
        options.package = "protocyte"
        options.syntax = "proto3"
        options.message_type.add().name = "ArrayOptions"
        consumer = file_set.file.add()
        consumer.name = "consumer.proto"
        consumer.package = "demo"
        consumer.syntax = "proto3"
        consumer.dependency.append(options.name)
        message = consumer.message_type.add()
        message.name = "Consumer"
        field = message.field.add()
        field.name = "options"
        field.number = 1
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        field.type_name = ".protocyte.ArrayOptions"
    descriptor_set.write_bytes(file_set.SerializeToString())

    protoc = source_dir / "tools" / "protoc"
    plugin = _installed_protocyte_plugin()
    protoc.parent.mkdir(parents=True, exist_ok=True)
    protoc.write_text("", encoding="utf-8")
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(descriptor_set_capability_preflight LANGUAGES NONE)",
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
    normalized_output = " ".join(output.split())
    assert result.returncode != 0
    assert "Failed to inspect descriptor set" in normalized_output
    assert expected_error in normalized_output


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
    plugin = _write_version_only_plugin(tools_dir / "protoc-gen-protocyte", __version__)
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
    assert args[-1:] == ["nested/demo.proto"]
    assert "" not in args


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
    generation_responses = [
        response.read_text(encoding="utf-8").splitlines()
        for response in (build_dir / "CMakeFiles" / "protocyte-arguments").glob("*.rsp")
        if "--descriptor_set_in=" in response.read_text(encoding="utf-8")
    ]
    assert len(generation_responses) == 1
    assert generation_responses[0][-1:] == ["api/demo.proto"]
    assert "" not in generation_responses[0]


def test_descriptor_set_library_accepts_build_generated_input_with_files(
    tmp_path: Path,
) -> None:
    if shutil.which("ninja") is None:
        pytest.skip("Ninja is required for the build-generated descriptor-set test")

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(repo_root)
    protobuf_import_dir = _find_protobuf_import_dir(repo_root, protoc)
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    tools_dir = source_dir / "tools"
    (proto_dir / "api").mkdir(parents=True)
    tools_dir.mkdir()
    common_proto = proto_dir / "common.proto"
    demo_proto = proto_dir / "api" / "demo.proto"
    common_proto.write_text(
        'syntax = "proto3"; package generated_input; message Common {}\n',
        encoding="utf-8",
    )
    demo_proto.write_text(
        "\n".join(
            [
                'syntax = "proto3";',
                "package generated_input;",
                'import "common.proto";',
                "message Demo { Common common = 1; }",
                "",
            ]
        ),
        encoding="utf-8",
    )
    plugin = _write_python_plugin_wrapper(tools_dir / "protoc-gen-protocyte", repo_root)

    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(build_generated_descriptor_set LANGUAGES CXX)",
                "set(PROTOCYTE_INSTALL OFF)",
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                f'add_subdirectory("{repo_root.as_posix()}" protocyte-core)',
                'set(descriptor_set "${CMAKE_CURRENT_BINARY_DIR}/generated/descriptor_set.pb")',
                "add_custom_command(",
                '    OUTPUT "${descriptor_set}"',
                '    COMMAND "${CMAKE_COMMAND}" -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/generated"',
                f'    COMMAND "{protoc.as_posix()}"',
                '        "--proto_path=${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '        "--descriptor_set_out=${descriptor_set}"',
                "        --include_imports",
                "        common.proto",
                "        api/demo.proto",
                f'    DEPENDS "{common_proto.as_posix()}" "{demo_proto.as_posix()}"',
                '    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                "    VERBATIM",
                ")",
                'add_custom_target(descriptor_set_input DEPENDS "${descriptor_set}")',
                "protocyte_add_descriptor_set_library(",
                "    TARGET generated_proto",
                '    DESCRIPTOR_SET "${descriptor_set}"',
                '    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated/cpp"',
                "    FILES common.proto api/demo.proto",
                "    DEPENDS descriptor_set_input",
                "    HOSTED_ALLOCATOR",
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
    descriptor_set = build_dir / "generated" / "descriptor_set.pb"
    assert not descriptor_set.exists()

    build_command = [
        "cmake",
        "--build",
        str(build_dir),
        "--target",
        "generated_proto",
    ]
    subprocess.run(build_command, check=True)

    assert descriptor_set.is_file()
    common_header = build_dir / "generated/cpp/common.protocyte.hpp"
    assert common_header.is_file()
    assert (build_dir / "generated/cpp/api/demo.protocyte.hpp").is_file()
    assert (build_dir / "generated/cpp/api/demo.protocyte.cpp").is_file()
    initial_descriptor_mtime_ns = descriptor_set.stat().st_mtime_ns
    initial_header_mtime_ns = common_header.stat().st_mtime_ns
    initial_header = common_header.read_text(encoding="utf-8")

    no_change = subprocess.run(
        build_command,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "no work to do" in no_change.stdout.lower()

    common_proto.write_text(
        'syntax = "proto3"; package generated_input; message Common { uint32 version = 1; }\n',
        encoding="utf-8",
    )
    _touch_newer_than(common_proto, descriptor_set)
    _touch_newer_than(common_proto, common_header)
    subprocess.run(build_command, check=True)

    assert descriptor_set.stat().st_mtime_ns > initial_descriptor_mtime_ns
    assert common_header.stat().st_mtime_ns > initial_header_mtime_ns
    assert common_header.read_text(encoding="utf-8") != initial_header


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
        _real_protoc_requirement_unavailable(
            "Ninja is required for portable long-path integration coverage"
        )

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
    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8", errors="replace")
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


@pytest.mark.skipif(os.name != "nt", reason="Windows shared-library regression")
def test_msvc_shared_library_exports_reflection_to_consumer(tmp_path: Path) -> None:
    if shutil.which("ninja") is None:
        _windows_shared_reflection_requirement_unavailable(
            "Ninja is required for the MSVC shared reflection integration test"
        )
    msvc_compiler = shutil.which("cl")
    if msvc_compiler is None:
        _windows_shared_reflection_requirement_unavailable(
            "an MSVC developer environment is required for the shared reflection integration test"
        )
    msvc_compiler = Path(msvc_compiler).resolve()

    repo_root = Path(__file__).resolve().parents[1]
    protoc = _find_real_protoc(
        repo_root,
        additional_required_env=_CI_REQUIRE_WINDOWS_SHARED_REFLECTION_TEST_ENV,
    )
    protobuf_import_dir = _find_protobuf_import_dir(
        repo_root,
        protoc,
        additional_required_env=_CI_REQUIRE_WINDOWS_SHARED_REFLECTION_TEST_ENV,
    )
    plugin = _installed_protocyte_plugin().resolve()
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    proto_dir = source_dir / "proto"
    proto_dir.mkdir(parents=True)
    (proto_dir / "demo.proto").write_text(
        'syntax = "proto3"; package api; message Demo { int32 id = 1; }\n',
        encoding="utf-8",
    )
    (proto_dir / "other.proto").write_text(
        'syntax = "proto3"; package other; message Other {}\n',
        encoding="utf-8",
    )
    (source_dir / "main.cpp").write_text(
        "\n".join(
            [
                '#include "demo.protocyte.hpp"',
                "",
                "int main() {",
                "  const auto& fields = ::api::protocyte_reflection::Demo_fields;",
                "  return fields.size() == 1u && fields[0].number == 1u ? 0 : 1;",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(protocyte_shared_reflection LANGUAGES CXX)",
                "if(NOT MSVC)",
                '    message(FATAL_ERROR "the test must compile with MSVC")',
                "endif()",
                f'set(PROTOCYTE_PLUGIN_EXECUTABLE "{plugin.as_posix()}")',
                f'set(Protobuf_PROTOC_EXECUTABLE "{protoc.as_posix()}")',
                f'set(PROTOCYTE_PROTOBUF_IMPORT_DIR "{protobuf_import_dir.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                "add_library(protocyte_codegen INTERFACE)",
                "add_library(protocyte::codegen ALIAS protocyte_codegen)",
                "protocyte_add_proto_library(",
                "    TARGET reflection_proto",
                "    TYPE SHARED",
                "    EMIT_RUNTIME",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    PROTOS "${CMAKE_CURRENT_SOURCE_DIR}/proto/demo.proto"',
                "    OPTIONS format=off",
                ")",
                "target_compile_definitions(",
                "    reflection_proto PUBLIC PROTOCYTE_ENABLE_REFLECTION=1",
                ")",
                "protocyte_add_proto_library(",
                "    TARGET other_reflection_proto",
                "    TYPE SHARED",
                "    EMIT_RUNTIME",
                '    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
                '    PROTOS "${CMAKE_CURRENT_SOURCE_DIR}/proto/other.proto"',
                "    OPTIONS format=off",
                ")",
                "set_target_properties(other_reflection_proto PROPERTIES EXCLUDE_FROM_ALL TRUE)",
                "foreach(target IN ITEMS reflection_proto other_reflection_proto)",
                "    get_target_property(definitions ${target} COMPILE_DEFINITIONS)",
                "    set(reflection_exports ${definitions})",
                "    list(",
                "        FILTER reflection_exports INCLUDE",
                '        REGEX "^PROTOCYTE_REFLECTION_API_[0-9A-F]+_EXPORTS=1$"',
                "    )",
                "    list(LENGTH reflection_exports export_count)",
                "    if(NOT export_count EQUAL 1)",
                '        message(FATAL_ERROR "${target} must have one private reflection export definition")',
                "    endif()",
                "    get_target_property(interface_definitions ${target} INTERFACE_COMPILE_DEFINITIONS)",
                '    if("${interface_definitions}" MATCHES "_EXPORTS")',
                '        message(FATAL_ERROR "${target} leaked its reflection export definition")',
                "    endif()",
                '    string(REGEX REPLACE "_EXPORTS=1$" "" ${target}_api "${reflection_exports}")',
                "endforeach()",
                'if("${reflection_proto_api}" STREQUAL "${other_reflection_proto_api}")',
                '    message(FATAL_ERROR "reflection API macros must be target-unique")',
                "endif()",
                'file(WRITE "${CMAKE_BINARY_DIR}/reflection-api-macro.txt" "${reflection_proto_api}")',
                "add_executable(reflection_consumer main.cpp)",
                "target_link_libraries(reflection_consumer PRIVATE reflection_proto)",
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
            str(source_dir),
            "-B",
            str(build_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_CXX_COMPILER={msvc_compiler}",
        ],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "reflection_consumer"],
        check=True,
    )

    macro = (build_dir / "reflection-api-macro.txt").read_text(encoding="utf-8")
    prefix = "PROTOCYTE_REFLECTION_API_"
    assert macro.startswith(prefix)
    digest = macro.removeprefix(prefix)
    assert len(digest) == 64
    assert set(digest) <= set("0123456789ABCDEF")
    generated_header = (
        build_dir / "reflection_proto_protocyte" / "demo.protocyte.hpp"
    ).read_text(encoding="utf-8")
    generated_source = (
        build_dir / "reflection_proto_protocyte" / "demo.protocyte.cpp"
    ).read_text(encoding="utf-8")
    assert f"#if !defined({macro})" in generated_header
    assert f"#if defined({macro}_EXPORTS)" in generated_header
    assert f"#define {macro} __declspec(dllexport)" in generated_header
    assert f"#define {macro} __declspec(dllimport)" in generated_header
    assert f"extern {macro} const " in generated_header
    assert f"extern {macro} const " in generated_source
    subprocess.run([str(build_dir / "reflection_consumer.exe")], check=True)


def test_cmake_constraints_pin_the_private_environment() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    constraints_path = repo_root / "protocyte-cmake-constraints.txt"
    constraint_lines = []
    hashes: dict[str, list[str]] = {}
    current_package: str | None = None
    for raw_line in constraints_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--hash="):
            assert current_package is not None
            hashes.setdefault(current_package, []).append(
                line.removesuffix("\\").rstrip()
            )
            continue
        package, version = line.removesuffix("\\").rstrip().split("==", 1)
        constraint_lines.append((package, version))
        current_package = package
    constraints = dict(constraint_lines)

    assert set(constraints) == {"pip", "protobuf", "setuptools", "wheel"}
    assert set(hashes) == set(constraints)
    assert all(package_hashes for package_hashes in hashes.values())
    assert all(
        package_hash.startswith("--hash=sha256:") and len(package_hash) == 78
        for package_hashes in hashes.values()
        for package_hash in package_hashes
    )
    locked_packages = tomllib.loads(
        (repo_root / "uv.lock").read_text(encoding="utf-8")
    )["package"]
    locked_protobuf = next(
        package["version"]
        for package in locked_packages
        if package["name"] == "protobuf"
    )
    assert constraints["protobuf"] == locked_protobuf

    functions = (repo_root / "cmake" / "ProtocyteFunctions.cmake").read_text(
        encoding="utf-8"
    )
    assert "--unset=PIP_TARGET" in functions
    assert "--unset=PIP_PREFIX" in functions
    assert "--unset=PIP_ROOT" in functions
    assert "--unset=PIP_USER" in functions
    assert "--unset=PIP_PYTHON" in functions
    assert "--unset=PIP_QUIET" in functions
    assert "--unset=PIP_REQUIREMENT" in functions
    assert "--unset=PIP_EDITABLE" in functions
    assert "--unset=PIP_GROUP" in functions
    assert "--unset=PIP_REQUIREMENTS_FROM_SCRIPT" in functions
    assert "--unset=PYTHONUSERBASE" in functions
    assert "--unset=PYTHONPATH" in functions
    assert "--unset=PYTHONHOME" in functions
    assert "PIP_ISOLATED=0" in functions
    assert '"${python_executable}" -I -m pip install' in functions
    assert 'for option in ("target", "prefix", "root"):' in functions
    assert (
        'for option in ("requirement", "editable", "group", "requirements-from-script"):'
        in functions
    )
    assert 'configuration.get_value("global.python")' in functions
    assert "--no-user" in functions
    assert functions.count("_protocyte_run_managed_pip(") == 3
    assert functions.count("_protocyte_check_managed_pip_configuration(") == 2
    assert "--only-binary=:all:\n            --require-hashes" in functions
    assert "--require-hashes\n            --requirement" in functions
    assert '--no-deps\n            "${protocyte_staged_project}"' in functions
    generation = (repo_root / "cmake" / "ProtocyteGenerate.cmake").read_text(
        encoding="utf-8"
    )
    assert "if(PROTOCYTE_MANAGED_PLUGIN)" in generation
    assert '"--unset=PYTHONPATH" "--unset=PYTHONHOME"' in generation


def test_hash_locked_requirements_reject_same_version_different_bytes(
    tmp_path: Path,
) -> None:
    package_name = "managed-hash-fixture"
    package_version = "1.0"
    wheel = tmp_path / "managed_hash_fixture-1.0-py3-none-any.whl"
    wheel.write_bytes(b"same-version-but-untrusted-bytes")
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        f"{package_name}=={package_version} --hash=sha256:{'0' * 64}\n",
        encoding="utf-8",
    )
    environment = tmp_path / "environment"
    subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    result = subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "download",
            "--no-deps",
            "--no-index",
            "--find-links",
            str(tmp_path),
            "--require-hashes",
            "--requirement",
            str(requirements),
            "--dest",
            str(tmp_path / "download"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "hashes" in output.casefold()
    assert f"{'0' * 64}" in output
    assert "got" in output.casefold()


def test_managed_environment_rejects_wrong_hash_from_configured_index(
    tmp_path: Path,
) -> None:
    index_root = tmp_path / "package-index"
    package_directory = index_root / "pip"
    package_directory.mkdir(parents=True)
    wheel_name = "pip-26.0.1-py3-none-any.whl"
    (package_directory / wheel_name).write_bytes(b"malicious-same-version-pip-wheel")
    (package_directory / "index.html").write_text(
        f'<a href="{wheel_name}">{wheel_name}</a>\n', encoding="utf-8"
    )
    source_dir = tmp_path / "consumer"
    environment_root = tmp_path / "managed-environments"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    environment = os.environ.copy()
    environment.update(
        {
            "PIP_INDEX_URL": index_root.as_uri(),
            "PIP_EXTRA_INDEX_URL": "",
            "PIP_NO_CACHE_DIR": "1",
        }
    )

    configured = _configure_managed_environment(source_dir, build_dir, env=environment)

    output = configured.stdout + configured.stderr
    assert configured.returncode != 0
    assert "hashes from the requirements file" in output.casefold()
    assert "pip-26.0.1-py3-none-any.whl" in output
    assert not environment_root.exists() or not any(
        child.is_dir() and (child / ".protocyte-ready").is_file()
        for child in environment_root.iterdir()
    )


def _write_pip_requirement_injection_project(project: Path, sentinel: Path) -> None:
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["setuptools"]\n'
        'build-backend = "setuptools.build_meta"\n',
        encoding="utf-8",
    )
    (project / "setup.py").write_text(
        "from pathlib import Path\n"
        "import os\n"
        "from setuptools import setup\n"
        "Path(os.environ['PROTOCYTE_TEST_INJECTION_SENTINEL']).write_text(\n"
        "    'source-build-ran\\n', encoding='utf-8'\n"
        ")\n"
        "setup(name='protocyte-pip-injection', version='1.0', py_modules=['injected'])\n",
        encoding="utf-8",
    )
    (project / "injected.py").write_text("value = 1\n", encoding="utf-8")


@pytest.mark.parametrize("settings_source", ["environment", "config-file"])
@pytest.mark.parametrize("input_kind", ["requirement", "editable"])
def test_managed_environment_rejects_additive_pip_install_inputs(
    tmp_path: Path,
    settings_source: str,
    input_kind: str,
) -> None:
    injection_project = tmp_path / "injected-project"
    sentinel = tmp_path / "injected-source-build.txt"
    _write_pip_requirement_injection_project(injection_project, sentinel)
    if input_kind == "requirement":
        injection_input = tmp_path / "injected-requirements.txt"
        injection_input.write_text(f"{injection_project}\n", encoding="utf-8")
    else:
        injection_input = injection_project
    source_dir = tmp_path / "consumer"
    environment_root = tmp_path / "managed-environments"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    environment = os.environ.copy()
    environment["PROTOCYTE_TEST_INJECTION_SENTINEL"] = str(sentinel)
    if settings_source == "environment":
        environment[f"PIP_{input_kind.upper()}"] = str(injection_input)
    else:
        config_file = tmp_path / "pip.ini"
        config_file.write_text(
            f"[install]\n{input_kind} = {injection_input}\n",
            encoding="utf-8",
        )
        environment["PIP_CONFIG_FILE"] = str(config_file)

    configured = _configure_managed_environment(source_dir, build_dir, env=environment)

    if settings_source == "environment":
        assert configured.returncode == 0, configured.stdout + configured.stderr
        environment_directory = _published_managed_environment(environment_root)
        python, _plugin = _managed_environment_executables(environment_directory)
        installed = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.util; print(importlib.util.find_spec('injected'))",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert installed.stdout.strip() == "None"
    else:
        assert configured.returncode != 0
        assert f"install.{input_kind}" in (configured.stdout + configured.stderr)
        assert not environment_root.exists() or not any(
            child.is_dir() and (child / ".protocyte-ready").is_file()
            for child in environment_root.iterdir()
        )
    assert not sentinel.exists()


def test_managed_environment_ignores_pip26_script_requirements_from_environment(
    tmp_path: Path,
) -> None:
    injection_project = tmp_path / "injected-project"
    sentinel = tmp_path / "injected-source-build.txt"
    _write_pip_requirement_injection_project(injection_project, sentinel)
    script = tmp_path / "injected-requirements.py"
    script.write_text(
        "# /// script\n"
        "# dependencies = [\n"
        f'#   "protocyte-pip-injection @ {injection_project.as_uri()}",\n'
        "# ]\n"
        "# ///\n",
        encoding="utf-8",
    )
    source_dir = tmp_path / "consumer"
    environment_root = tmp_path / "managed-environments"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    environment = os.environ.copy()
    environment.update(
        {
            "PIP_REQUIREMENTS_FROM_SCRIPT": str(script),
            "PROTOCYTE_TEST_INJECTION_SENTINEL": str(sentinel),
        }
    )

    configured = _configure_managed_environment(source_dir, build_dir, env=environment)

    assert configured.returncode == 0, configured.stdout + configured.stderr
    environment_directory = _published_managed_environment(environment_root)
    python, _plugin = _managed_environment_executables(environment_directory)
    installed = subprocess.run(
        [
            str(python),
            "-c",
            "import importlib.util; print(importlib.util.find_spec('injected'))",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert installed.stdout.strip() == "None"
    assert not sentinel.exists()

    # This pip 26 control proves the inline script is a real additive input:
    # pip prepares the injected local source even with --dry-run. The managed
    # configure above must never reach it.
    control_environment = environment.copy()
    control_environment.pop("PIP_REQUIREMENTS_FROM_SCRIPT")
    control = subprocess.run(
        [
            str(python),
            "-I",
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--no-deps",
            "--no-build-isolation",
            "--requirements-from-script",
            str(script),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=control_environment,
    )
    assert control.returncode == 0, control.stdout + control.stderr
    assert sentinel.read_text(encoding="utf-8") == "source-build-ran\n"


@pytest.mark.parametrize("settings_source", ["environment", "config-file"])
def test_managed_environment_confines_pip_destination_settings(
    tmp_path: Path,
    settings_source: str,
) -> None:
    destination_names = ("target", "prefix", "root", "user")
    destinations = {
        name: tmp_path / "outside-managed-environment" / name
        for name in destination_names
    }
    sentinels = {}
    for name, destination in destinations.items():
        destination.mkdir(parents=True)
        sentinel = destination / "keep.txt"
        sentinel.write_text("user-owned\n", encoding="utf-8")
        sentinels[name] = sentinel

    source_dir = tmp_path / "consumer"
    environment_root = tmp_path / "managed-environments"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    shadow_modules = tmp_path / "shadow-modules"
    shadow_package = shadow_modules / "protocyte"
    shadow_package.mkdir(parents=True)
    (shadow_package / "__init__.py").write_text("\n", encoding="utf-8")
    (shadow_package / "main.py").write_text(
        "raise RuntimeError('ambient PYTHONPATH was imported')\n",
        encoding="utf-8",
    )
    configure_cwd = tmp_path / "configure-cwd"
    configure_cwd.mkdir()
    environment = os.environ.copy()
    if settings_source == "environment":
        environment.update(
            {
                "PIP_TARGET": str(destinations["target"]),
                "PIP_PREFIX": str(destinations["prefix"]),
                "PIP_ROOT": str(destinations["root"]),
                "PIP_USER": "1",
                "PIP_PYTHON": str(destinations["user"] / "python.exe"),
                "PIP_ISOLATED": "1",
                "PYTHONUSERBASE": str(destinations["user"]),
                "PYTHONPATH": str(shadow_modules),
            }
        )
    else:
        config_file = tmp_path / "pip.ini"
        config_file.write_text(
            "[global]\n"
            f"target = {destinations['target']}\n"
            f"prefix = {destinations['prefix']}\n"
            f"root = {destinations['root']}\n"
            f"python = {destinations['user'] / 'python.exe'}\n"
            "user = true\n",
            encoding="utf-8",
        )
        environment["PIP_CONFIG_FILE"] = str(config_file)
        environment["PYTHONUSERBASE"] = str(destinations["user"])

    configured = _configure_managed_environment(
        source_dir,
        build_dir,
        env=environment,
        cwd=configure_cwd,
    )

    if settings_source == "environment":
        assert configured.returncode == 0, configured.stdout + configured.stderr
        _published_managed_environment(environment_root)
    else:
        assert configured.returncode != 0
        output = configured.stdout + configured.stderr
        assert "effective pip configuration" in output
        assert "global.python" in output
        assert str(destinations["target"]) not in output
        assert not environment_root.exists() or not any(
            child.is_dir() and (child / ".protocyte-ready").is_file()
            for child in environment_root.iterdir()
        )
    for name, destination in destinations.items():
        assert list(destination.iterdir()) == [sentinels[name]], name
    assert not (configure_cwd / "Lib").exists()
    assert not (configure_cwd / "Scripts").exists()


def test_relative_managed_environment_root_is_canonical_and_confined(
    tmp_path: Path,
) -> None:
    relative_root = Path("relative-environments")
    expected_root = tmp_path / "project-build" / relative_root
    source_dir = tmp_path / "project"
    launch_dir = tmp_path / "launcher"
    launch_dir.mkdir()
    build_dir = _write_managed_environment_consumer(
        source_dir,
        relative_root,
    )

    result = _configure_managed_environment(
        source_dir,
        build_dir,
        cwd=launch_dir,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    configured_roots = (
        (build_dir / "managed-root.txt").read_text(encoding="utf-8").splitlines()
    )
    assert [Path(root) for root in configured_roots] == [expected_root, expected_root]
    environment = _published_managed_environment(expected_root)
    _python, plugin = _managed_environment_executables(environment)
    assert (
        Path((build_dir / "managed-plugin.txt").read_text(encoding="utf-8")) == plugin
    )
    assert plugin.is_file()
    assert not (source_dir / relative_root).exists()
    assert not (launch_dir / relative_root).exists()
    _assert_no_managed_environment_transaction_leftovers(expected_root)


def test_add_subdirectory_publishes_normal_parent_environment_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "consumer"
    build_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(parent_environment_root LANGUAGES NONE)",
                'set(PROTOCYTE_PYTHON_ENV_ROOT "parent-managed-python")',
                "set(PROTOCYTE_FETCH_PROTOBUF OFF)",
                "set(PROTOCYTE_INSTALL OFF)",
                f'add_subdirectory("{repo_root.as_posix()}" "${{CMAKE_CURRENT_BINARY_DIR}}/protocyte" EXCLUDE_FROM_ALL)',
                "_protocyte_get_internal(managed_root PYTHON_ENV_ROOT)",
                "get_property(cached_root CACHE PROTOCYTE_PYTHON_ENV_ROOT PROPERTY VALUE)",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/roots.txt" "${PROTOCYTE_PYTHON_ENV_ROOT}\n${managed_root}\n${cached_root}\n")',
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

    assert result.returncode == 0, result.stdout + result.stderr
    expected_root = build_dir / "parent-managed-python"
    configured_roots = (
        (build_dir / "roots.txt").read_text(encoding="utf-8").splitlines()
    )
    assert [Path(root) for root in configured_roots] == [expected_root] * 3


def test_relative_managed_environment_root_cache_is_canonical(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = tmp_path / "project"
    build_dir = tmp_path / "build"
    launch_dir = tmp_path / "launcher"
    source_dir.mkdir()
    launch_dir.mkdir()
    (source_dir / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(relative_environment_cache LANGUAGES NONE)",
                'set(PROTOCYTE_PYTHON_ENV_ROOT "cached-environments" CACHE PATH "" FORCE)',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
                "_protocyte_get_internal(managed_root PYTHON_ENV_ROOT)",
                'file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/roots.txt" "${PROTOCYTE_PYTHON_ENV_ROOT}\n${managed_root}\n")',
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
        cwd=launch_dir,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    expected_root = build_dir / "cached-environments"
    configured_roots = (
        (build_dir / "roots.txt").read_text(encoding="utf-8").splitlines()
    )
    assert [Path(root) for root in configured_roots] == [expected_root, expected_root]
    cache = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
    assert f"PROTOCYTE_PYTHON_ENV_ROOT:PATH={expected_root.as_posix()}" in cache
    assert not (source_dir / "cached-environments").exists()
    assert not (launch_dir / "cached-environments").exists()


def test_managed_environment_root_rejects_semicolon_before_provisioning(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    environment_root = tmp_path / "managed;environments"
    result = _configure_cmake_snippet(
        tmp_path,
        "\n".join(
            [
                f'set(PROTOCYTE_PYTHON_ENV_ROOT "{environment_root.as_posix()}")',
                f'include("{(repo_root / "cmake" / "Protocyte.cmake").as_posix()}")',
            ]
        ),
    )

    output = " ".join((result.stdout + result.stderr).split())
    assert result.returncode != 0
    assert "PROTOCYTE_PYTHON_ENV_ROOT must not contain ';'" in output
    assert "Choose an environment root without semicolons" in output
    assert "Provisioning Protocyte Python environment" not in output
    assert not environment_root.exists()
    assert not (tmp_path / "managed").exists()


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
    assert (
        subprocess.run(
            [str(plugin), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == __version__
    )
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
    assert (
        "Provisioning Protocyte Python environment:" in initial.stdout + initial.stderr
    )

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
    assert (
        subprocess.run(
            [str(plugin), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "99.0.0"
    )

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
    assert (
        subprocess.run(
            [str(plugin), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "99.0.0"
    )
    _assert_no_managed_environment_transaction_leftovers(environment_root)

    repaired = _configure_managed_environment(source_dir, build_dir)
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert (
        "Provisioning Protocyte Python environment:"
        in repaired.stdout + repaired.stderr
    )
    repaired_environment = _published_managed_environment(environment_root)
    assert repaired_environment == environment
    _repaired_python, repaired_plugin = _managed_environment_executables(
        repaired_environment
    )
    assert (
        subprocess.run(
            [str(repaired_plugin), "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == __version__
    )
    _assert_no_managed_environment_transaction_leftovers(environment_root)


def _run_managed_environment_transaction(
    action: str,
    destination: Path,
    fingerprint: str,
    transaction: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    helper = (
        Path(__file__).resolve().parents[1] / "cmake" / "ProtocyteManagedEnvironment.py"
    )
    command = [
        sys.executable,
        str(helper),
        action,
        "--destination",
        str(destination),
        "--fingerprint",
        fingerprint,
    ]
    if transaction is not None:
        command.extend(("--transaction", str(transaction)))
    return subprocess.run(command, check=False, capture_output=True, text=True)


def test_managed_environment_leaves_legacy_previous_lookalike_untouched(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "managed-environments"
    source_dir = tmp_path / "project"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    initial = _configure_managed_environment(source_dir, build_dir)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    environment = _published_managed_environment(environment_root)
    lookalike = environment_root / f".{environment.name}.previous"
    lookalike.mkdir()
    sentinel = lookalike / "keep.txt"
    sentinel.write_text("user-owned\n", encoding="utf-8")

    incremental = _configure_managed_environment(source_dir, build_dir)

    assert incremental.returncode == 0, incremental.stdout + incremental.stderr
    assert sentinel.read_text(encoding="utf-8") == "user-owned\n"


def test_managed_environment_ignores_unowned_predictable_transaction_lookalike(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "managed-environments"
    source_dir = tmp_path / "project"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    initial = _configure_managed_environment(source_dir, build_dir)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    environment = _published_managed_environment(environment_root)
    lookalike = environment_root / (
        f".{environment.name}.protocyte-transaction-{'f' * 32}"
    )
    lookalike.mkdir()
    owner = lookalike / ".protocyte-managed-environment.owner"
    owner.write_text("not an ownership record\n", encoding="utf-8")

    retry = _configure_managed_environment(source_dir, build_dir)

    assert retry.returncode == 0, retry.stdout + retry.stderr
    assert owner.read_text(encoding="utf-8") == "not an ownership record\n"
    assert (environment / ".protocyte-ready").is_file()


def test_managed_environment_recovers_an_identity_bound_interrupted_repair(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "managed-environments"
    source_dir = tmp_path / "project"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    initial = _configure_managed_environment(source_dir, build_dir)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    environment = _published_managed_environment(environment_root)
    fingerprint = (environment / ".protocyte-ready").read_text(encoding="utf-8").strip()
    created = _run_managed_environment_transaction("create", environment, fingerprint)
    assert created.returncode == 0, created.stdout + created.stderr
    transaction = Path(created.stdout.strip())
    backed_up = _run_managed_environment_transaction(
        "backup", environment, fingerprint, transaction
    )
    assert backed_up.returncode == 0, backed_up.stdout + backed_up.stderr
    assert not environment.exists()

    recovered = _configure_managed_environment(source_dir, build_dir)

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert (environment / ".protocyte-ready").read_text(encoding="utf-8").strip() == (
        fingerprint
    )
    assert not transaction.exists()
    _assert_no_managed_environment_transaction_leftovers(environment_root)


def test_managed_environment_refuses_a_replaced_identity_bound_backup(
    tmp_path: Path,
) -> None:
    environment_root = tmp_path / "managed-environments"
    source_dir = tmp_path / "project"
    build_dir = _write_managed_environment_consumer(source_dir, environment_root)
    initial = _configure_managed_environment(source_dir, build_dir)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    environment = _published_managed_environment(environment_root)
    fingerprint = (environment / ".protocyte-ready").read_text(encoding="utf-8").strip()
    created = _run_managed_environment_transaction("create", environment, fingerprint)
    assert created.returncode == 0, created.stdout + created.stderr
    transaction = Path(created.stdout.strip())
    backed_up = _run_managed_environment_transaction(
        "backup", environment, fingerprint, transaction
    )
    assert backed_up.returncode == 0, backed_up.stdout + backed_up.stderr
    previous = transaction / "previous"
    preserved_backup = tmp_path / "preserved-backup"
    previous.replace(preserved_backup)
    previous.mkdir()
    (previous / ".protocyte-ready").write_text(f"{fingerprint}\n", encoding="utf-8")

    recovered = _configure_managed_environment(source_dir, build_dir)

    assert recovered.returncode != 0
    assert "Failed to recover Protocyte's managed Python environment transaction" in (
        recovered.stdout + recovered.stderr
    )
    assert (preserved_backup / ".protocyte-ready").read_text(
        encoding="utf-8"
    ).strip() == fingerprint
    assert (previous / ".protocyte-ready").read_text(encoding="utf-8").strip() == (
        fingerprint
    )


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
