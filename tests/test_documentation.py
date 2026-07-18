import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_quickstart_matches_compiled_example() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marked = readme.split("<!-- quickstart-main-start -->", maxsplit=1)[1]
    block = marked.split("<!-- quickstart-main-end -->", maxsplit=1)[0].strip()

    assert block.startswith("```cpp\n")
    assert block.endswith("\n```")
    documented_source = block.removeprefix("```cpp\n").removesuffix("\n```")
    compiled_source = (ROOT / "examples/quickstart/main.cpp").read_text(
        encoding="utf-8"
    )

    assert documented_source == compiled_source.rstrip("\n")


def test_ground_zero_guide_has_complete_prerequisites_and_examples() -> None:
    guide = (ROOT / "tests/smoke/README.md").read_text(encoding="utf-8")
    prerequisites = guide.split("## 1. Install `protoc`", maxsplit=1)[0]
    descriptor_block = next(
        block
        for block in re.findall(r"```powershell\n(.*?)\n```", guide, re.DOTALL)
        if "--descriptor_set_out" in block
    )

    assert (
        "[uv](https://docs.astral.sh/uv/getting-started/installation/)" in prerequisites
    )
    assert "uv --version" in prerequisites
    assert "${" not in descriptor_block
    assert "$protoRoot" in descriptor_block
    assert "$protocyteProtoDir" in descriptor_block
    assert "$descriptorSet" in descriptor_block
    assert "sample.mutable_values().push_back(42u)" in guide
    assert "(*parsed).values()[0] != 42u" in guide


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
