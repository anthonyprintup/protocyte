import re
import shutil
import subprocess
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
    powershell = _marked_fenced_block(
        readme, "quickstart-powershell", "powershell"
    )
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

    linux_ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    for fragment in (
        "uv build --wheel",
        "uv venv build/quickstart-venv --python 3.12",
        "uv pip install --python",
        "cmake -S examples/quickstart -B build/quickstart",
        "cmake --build build/quickstart",
        "ctest --test-dir build/quickstart",
    ):
        assert fragment in linux_ci


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
        assert all("New-Item -ItemType Directory -Force" in block for block in powershell_blocks)
        assert all("mkdir -p" in block for block in posix_blocks)


def test_release_guidance_does_not_claim_unpublished_assets_exist() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "tests" / "smoke" / "README.md").read_text(encoding="utf-8")

    for document in (readme, guide):
        assert "has not published its first tag or" in document
        assert "https://github.com/anthonyprintup/protocyte/releases" in document
    assert "GIT_TAG vX.Y.Z" not in readme
    assert "GIT_TAG <full-commit-sha>" in readme


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
