import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _fenced_blocks(document: str, language: str) -> list[str]:
    return re.findall(rf"```{re.escape(language)}\n(.*?)\n```", document, re.DOTALL)


def _marked_fenced_block(document: str, marker: str, language: str) -> str:
    marked = document.split(f"<!-- {marker}-start -->", maxsplit=1)[1]
    block = marked.split(f"<!-- {marker}-end -->", maxsplit=1)[0].strip()
    assert block.startswith(f"```{language}\n")
    assert block.endswith("\n```")
    return block.removeprefix(f"```{language}\n").removesuffix("\n```")


def test_readme_quickstart_matches_compiled_example() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    documented_source = _marked_fenced_block(readme, "quickstart-main", "cpp")
    compiled_source = (ROOT / "examples/quickstart/main.cpp").read_text(
        encoding="utf-8"
    )

    assert documented_source == compiled_source.rstrip("\n")
    assert "size.error()" in compiled_source
    assert "written.error()" in compiled_source
    assert "parsed.error()" in compiled_source


def test_readme_quickstart_has_parallel_windows_and_posix_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    powershell = _marked_fenced_block(readme, "quickstart-powershell", "powershell")
    posix = _marked_fenced_block(readme, "quickstart-posix", "bash")

    for fragment in (
        "uv build --wheel",
        "uv venv",
        "uv pip install --python",
        "cmake -S examples/quickstart -B build/quickstart",
        "cmake --build build/quickstart",
        "ctest --test-dir build/quickstart",
    ):
        assert fragment in powershell
        assert fragment in posix

    assert "build\\quickstart-venv\\Scripts\\python.exe" in powershell
    assert "build/quickstart-venv/bin/python" in posix
    assert "$(command -v protoc)" in posix
    assert "Scripts" not in posix

    linux_ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for fragment in (
        "uv build --wheel",
        "uv venv build/quickstart-venv --python 3.12",
        "uv pip install --python",
        "cmake -S examples/quickstart -B build/quickstart",
        "cmake --build build/quickstart",
        "ctest --test-dir build/quickstart",
    ):
        assert fragment in linux_ci


def test_smoke_regeneration_uses_managed_python_and_documents_portability_ci() -> None:
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")

    assert (
        "uv run python .github/scripts/install_protoc.py "
        "--dest build/canonical-protoc"
    ) in guide
    assert "\npython .github/scripts/install_protoc.py" not in guide
    assert "complete wheel\nand quick-start path on Linux, Windows, and macOS" in guide


@pytest.mark.skipif(shutil.which("bash") is None, reason="Bash is not available")
def test_documented_posix_blocks_parse_as_bash() -> None:
    for relative_path in ("README.md", "tests/smoke/README.md"):
        document = (ROOT / relative_path).read_text(encoding="utf-8")
        blocks = _fenced_blocks(document, "bash")
        assert blocks
        for block in blocks:
            result = subprocess.run(
                ["bash", "-n"],
                input=block,
                check=False,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"{relative_path}: {result.stderr}"


def test_ground_zero_guide_has_complete_prerequisites_and_examples() -> None:
    guide = (ROOT / "tests/smoke/README.md").read_text(encoding="utf-8")
    prerequisites = guide.split("## 1. Install `protoc`", maxsplit=1)[0]
    descriptor_powershell = next(
        block
        for block in _fenced_blocks(guide, "powershell")
        if "--descriptor_set_out" in block
    )
    descriptor_posix = next(
        block
        for block in _fenced_blocks(guide, "bash")
        if "--descriptor_set_out" in block
    )
    cmake_example = _marked_fenced_block(guide, "ground-zero-cmake", "cmake")

    assert (
        "[uv](https://docs.astral.sh/uv/getting-started/installation/)" in prerequisites
    )
    assert "uv --version" in prerequisites
    assert "${" not in descriptor_powershell
    assert "$protoRoot" in descriptor_powershell
    assert "$protocyteProtoDir" in descriptor_powershell
    assert "$descriptorSet" in descriptor_powershell
    assert 'mkdir -p "$(dirname "$descriptor_set")"' in descriptor_posix
    assert '"--descriptor_set_out=$descriptor_set"' in descriptor_posix
    assert "find_package(protocyte CONFIG REQUIRED)" in cmake_example
    assert "protocyte_add_proto_library(" in cmake_example
    assert "ALIAS demo::sensor_proto" in cmake_example
    assert "target_link_libraries(app PRIVATE demo::sensor_proto)" in cmake_example
    assert "add_custom_command" not in cmake_example
    assert "protocyte_generate(" not in cmake_example
    assert "sample.mutable_values().push_back(42u)" in guide
    assert "(*parsed).values()[0] != 42u" in guide


def test_direct_generation_examples_create_output_directories() -> None:
    for relative_path in ("README.md", "tests/smoke/README.md"):
        document = (ROOT / relative_path).read_text(encoding="utf-8")
        powershell_blocks = [
            block
            for block in _fenced_blocks(document, "powershell")
            if "--protocyte_out" in block
        ]
        posix_blocks = [
            block
            for block in _fenced_blocks(document, "bash")
            if "--protocyte_out" in block
        ]
        assert powershell_blocks
        assert posix_blocks
        assert all(
            "New-Item -ItemType Directory -Force" in block
            for block in powershell_blocks
        )
        assert all("mkdir -p" in block for block in posix_blocks)
        assert all(
            "--protocyte_out=runtime=emit:" in block
            or (
                "--protocyte_out=out" in block
                and "--protocyte_opt=runtime=emit:" in block
            )
            for block in powershell_blocks
        )
        assert all(
            "--protocyte_out=runtime=emit:" in block
            or (
                "--protocyte_out=out" in block
                and "--protocyte_opt=runtime=emit:" in block
            )
            for block in posix_blocks
        )


def test_colon_valued_plugin_options_are_separate_from_protoc_output() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    plugin_parameters = readme.split("## Plugin Parameters", maxsplit=1)[1].split(
        "### Generator trust boundary", maxsplit=1
    )[0]

    for language in ("powershell", "bash"):
        example = next(
            block
            for block in _fenced_blocks(plugin_parameters, language)
            if "namespace_prefix=mycorp::wire" in block
        )
        assert "--protocyte_out=out" in example
        assert (
            "--protocyte_opt=runtime=emit:vendor/protocyte,"
            "namespace_prefix=mycorp::wire,include_prefix=generated"
        ) in example
        assert "--protocyte_out=runtime=emit:vendor/protocyte" not in example

    assert "treats the first `:`" in plugin_parameters


def test_ground_zero_python_commands_use_uv_managed_environments() -> None:
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")
    prerequisites = guide.split("## 1. Install `protoc`", maxsplit=1)[0]
    checkout_install = guide.split(
        "### Option A: Use This Repository Checkout Directly", maxsplit=1
    )[1].split("### Option B: Build A Wheel And Install It Somewhere Else", maxsplit=1)[
        0
    ]
    wheel_install = guide.split(
        "### Option B: Build A Wheel And Install It Somewhere Else", maxsplit=1
    )[1].split("### Option C: Install The CMake Package", maxsplit=1)[0]

    assert "uv python find 3.12" in prerequisites
    assert "python --version" not in prerequisites
    assert '$python = "$PWD\\.venv\\Scripts\\python.exe"' in checkout_install
    assert 'python="$PWD/.venv/bin/python"' in checkout_install
    assert "uv venv build\\plugin-venv --python 3.12" in wheel_install
    assert "uv venv build/plugin-venv --python 3.12" in wheel_install
    assert "uv pip install --python $python $wheel" in wheel_install
    assert 'uv pip install --python "$python" "$wheel"' in wheel_install
    assert "python -m pip" not in wheel_install
    assert "uv run python -c" not in guide
    assert '& $python -c "from pathlib import Path; import protocyte;' in guide
    assert '$("$python" -c "from pathlib import Path; import protocyte;' in guide


def test_installed_cmake_python_requirements_are_explicit() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")

    for document in (readme, guide):
        assert "`venv`" in document
        assert "`ensurepip`" in document
        assert "python3-venv" in document
        assert 'python3.12 -c "import ensurepip, venv"' in document


def test_documented_proto_locator_runs_from_separate_consumer_directory(
    tmp_path: Path,
) -> None:
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")
    descriptor_blocks = [
        block
        for language in ("powershell", "bash")
        for block in _fenced_blocks(guide, language)
        if "--descriptor_set_out" in block
    ]

    locator_commands = set()
    for block in descriptor_blocks:
        match = re.search(r'-c "([^"\n]+)"', block)
        assert match is not None
        locator_commands.add(match.group(1))
    assert len(locator_commands) == 1

    consumer = tmp_path / "separate-consumer"
    consumer.mkdir()
    completed = subprocess.run(
        [sys.executable, "-c", locator_commands.pop()],
        cwd=consumer,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    proto_directory = Path(completed.stdout.strip())
    assert (proto_directory / "protocyte" / "options.proto").is_file()


def test_descriptor_set_cmake_example_uses_a_defined_output_directory() -> None:
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")
    descriptor_example = next(
        block
        for block in _fenced_blocks(guide, "cmake")
        if "protocyte_add_descriptor_set_library(" in block
    )

    assert 'OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"' in descriptor_example
    assert "${GENERATED_DIR}" not in descriptor_example


def test_readme_propagates_public_string_view_configuration() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    string_views = readme.split("### String Views", maxsplit=1)[1].split(
        "### Parse Atomicity", maxsplit=1
    )[0]

    assert (
        "target_compile_definitions(demo_proto PUBLIC "
        "PROTOCYTE_ENABLE_STD_STRING_VIEW=1)"
    ) in string_views
    assert "PRIVATE PROTOCYTE_ENABLE_STD_STRING_VIEW" not in string_views
    assert "all translation units in that target graph" in string_views


def test_readme_requires_public_reflection_configuration_for_generated_libraries() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    reflection = readme.split("Reflection tables are emitted", maxsplit=1)[1].split(
        "`ReflectionFieldInfo::label`", maxsplit=1
    )[0]

    assert (
        "target_compile_definitions(demo_proto PUBLIC "
        "PROTOCYTE_ENABLE_REFLECTION=1)"
    ) in reflection
    assert "PUBLIC visibility is required" in reflection
    assert "TYPE SHARED" in reflection
    assert "target-unique import/export macro" in reflection


def test_documented_protobuf_fallback_defaults_match_cmake_modes() -> None:
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")
    source_cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    installed_config = (ROOT / "cmake" / "protocyteConfig.cmake.in").read_text(
        encoding="utf-8"
    )

    source_option = source_cmake.split(
        "option(\n    PROTOCYTE_FETCH_PROTOBUF", maxsplit=1
    )[1].split("\n)", maxsplit=1)[0]
    installed_default = installed_config.split(
        "if(NOT DEFINED PROTOCYTE_FETCH_PROTOBUF)", maxsplit=1
    )[1].split("endif()", maxsplit=1)[0]

    assert "\n    ON" in source_option
    assert "\n        OFF" in installed_default
    assert (
        "CMake source consumers using `FetchContent` or `add_subdirectory` default"
        in guide
    )
    assert (
        "Installed\n`find_package(protocyte CONFIG REQUIRED)` consumers default "
        "that option to\n`OFF`"
    ) in guide
    assert (
        "A host-runnable `protoc` and required protobuf import\n"
        "sources are caller-supplied by default"
    ) in guide
    assert "for native builds, a missing host `protoc`" in guide
    assert "Cross-compiling consumers must always supply the host-runnable" in guide
    assert "Protobuf C++ files" not in guide
    assert "Fetch protobuf tools or import sources" in source_option
    assert "Fetch protobuf tools or import sources" in installed_default


def test_readme_documents_descriptor_name_portability_rejections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    descriptor_paths = readme.split("Protobuf virtual descriptor names", maxsplit=1)[
        1
    ].split("Generate from a descriptor set", maxsplit=1)[0]

    assert "Descriptor names beginning with `-` are rejected" in descriptor_paths
    assert "differ only by letter case" in descriptor_paths
    assert "case-insensitive filesystems" in descriptor_paths


def test_release_guidance_does_not_claim_unpublished_assets_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")

    for document in (readme, guide):
        assert "has not published its first tag or" in document
        assert "https://github.com/anthonyprintup/protocyte/releases" in document
    assert "GIT_TAG vX.Y.Z" not in readme
    assert "GIT_TAG <full-commit-sha>" in readme


def test_readme_documents_managed_tool_path_contracts() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Relative values are normalized against\n`CMAKE_BINARY_DIR`" in readme
    assert "published back to the\nconsumer scope and CMake cache" in readme
    assert "The environment root must not contain a semicolon" in readme
    assert "provide a wrapper from a\nsemicolon-free location" in readme


def test_readme_cmake_reference_covers_every_public_helper_argument() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    cmake = (ROOT / "cmake" / "ProtocyteFunctions.cmake").read_text(encoding="utf-8")
    reference = readme.split("### CMake API Reference", maxsplit=1)[1].split(
        "## Debugging", maxsplit=1
    )[0]

    assert "#### `protocyte_setup_codegen`" in reference

    for helper in (
        "protocyte_generate",
        "protocyte_add_proto_library",
        "protocyte_add_descriptor_set_library",
    ):
        function_body = cmake.split(f"function({helper})", maxsplit=1)[1].split(
            "endfunction()", maxsplit=1
        )[0]
        helper_reference = reference.split(f"#### `{helper}`", maxsplit=1)[1]
        helper_reference = helper_reference.split("#### `", maxsplit=1)[0]

        declared_arguments: set[str] = set()
        for group in ("options", "oneValueArgs", "multiValueArgs"):
            match = re.search(rf"set\(\s*{group}\s+(.*?)\)", function_body, re.DOTALL)
            assert match is not None
            declared_arguments.update(
                re.findall(r"\b[A-Z][A-Z0-9_]+\b", match.group(1))
            )

        missing = sorted(
            argument
            for argument in declared_arguments
            if re.search(rf"\b{re.escape(argument)}\b", helper_reference) is None
        )
        assert not missing, f"{helper} arguments missing from README: {missing}"


def test_debugger_guide_documents_python_enabled_lldb_requirement() -> None:
    guide = (ROOT / "docs" / "debugger.md").read_text(encoding="utf-8")
    plain_lldb = guide.split("## Plain LLDB", maxsplit=1)[1].split(
        "## CLion", maxsplit=1
    )[0]

    assert "require an LLDB build with\nPython scripting enabled" in plain_lldb
    assert '(lldb) script print("LLDB Python scripting is available")' in plain_lldb
    assert "CLion's bundled LLDB is one suitable option" in plain_lldb
    assert "not in repository files shared with other users" in plain_lldb
