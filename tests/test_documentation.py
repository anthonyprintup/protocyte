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

    assert "[uv](https://docs.astral.sh/uv/getting-started/installation/)" in prerequisites
    assert "uv --version" in prerequisites
    assert "${" not in descriptor_block
    assert "$protoRoot" in descriptor_block
    assert "$protocyteProtoDir" in descriptor_block
    assert "$descriptorSet" in descriptor_block
    assert "sample.mutable_values().push_back(42u)" in guide
    assert "(*parsed).values()[0] != 42u" in guide
