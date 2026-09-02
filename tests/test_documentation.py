import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "docs" / "wiki"


def _page(name: str) -> str:
    return (WIKI / f"{name}.md").read_text(encoding="utf-8")


def _fenced_blocks(document: str, language: str) -> list[str]:
    return re.findall(rf"```{re.escape(language)}\n(.*?)\n```", document, re.DOTALL)


def test_wiki_navigation_is_complete_unique_and_title_aligned() -> None:
    sidebar = _page("_Sidebar")
    footer = _page("_Footer")
    links = re.findall(r"^- \[([^\]]+)\]\(([^)]+)\)$", sidebar, re.MULTILINE)
    names = [name for name, _ in links]
    targets = [target for _, target in links]
    published = sorted(
        path.stem
        for path in WIKI.glob("*.md")
        if not path.name.startswith("_")
    )

    assert len(targets) == len(set(targets))
    assert sorted(targets) == published
    for name, target in links:
        expected_title = "Protocyte" if target == "Home" else name
        assert _page(target).splitlines()[0] == f"# {expected_title}"
    assert names[0] == "Home"
    assert (
        "[Apache License 2.0]"
        "(https://github.com/anthonyprintup/protocyte/blob/main/LICENSE)"
        in footer
    )
    assert "MIT License" not in footer


def test_wiki_internal_links_resolve() -> None:
    published = {path.stem for path in WIKI.glob("*.md")}
    unresolved: list[str] = []
    for path in WIKI.glob("*.md"):
        document = path.read_text(encoding="utf-8")
        destinations = re.findall(r"\[[^\]]+\]\(([^)]+)\)", document)
        for destination in destinations:
            destination = destination.split("#", maxsplit=1)[0]
            wiki_prefix = "https://github.com/anthonyprintup/protocyte/wiki/"
            if destination.startswith(wiki_prefix):
                target = destination.removeprefix(wiki_prefix).rstrip("/")
            elif re.fullmatch(r"[A-Za-z0-9_-]+", destination):
                target = destination
            else:
                continue
            if target not in published:
                unresolved.append(f"{path.name}: {destination}")
    assert not unresolved


def test_getting_started_matches_the_checked_fetchcontent_example() -> None:
    guide = _page("Getting-Started")
    cmake_example = next(
        block
        for block in _fenced_blocks(guide, "cmake")
        if "FetchContent_Declare(" in block
    )
    documented_source = _fenced_blocks(guide, "cpp")[0]
    documented_schema = _fenced_blocks(guide, "proto")[0]
    compiled_source = (ROOT / "examples/quickstart/main.cpp").read_text(
        encoding="utf-8"
    )
    checked_schema = (
        ROOT / "examples/quickstart/proto/reading.proto"
    ).read_text(encoding="utf-8")
    checked_cmake = (ROOT / "examples/quickstart/CMakeLists.txt").read_text(
        encoding="utf-8"
    )

    assert documented_source == compiled_source.rstrip("\n")
    assert documented_schema == checked_schema.rstrip("\n")
    for fragment in (
        "include(FetchContent)",
        "FetchContent_Declare(",
        "9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14",
        "FetchContent_MakeAvailable(protocyte)",
        "protocyte_add_proto_library(",
        "HOSTED_ALLOCATOR",
        "target_link_libraries(protocyte_quickstart PRIVATE quickstart::proto)",
    ):
        assert fragment in cmake_example
        assert fragment in checked_cmake
    for error in ("size.error()", "written.error()", "parsed.error()"):
        assert error in compiled_source


def test_quickstart_ci_exercises_fetchcontent_from_the_current_checkout() -> None:
    workflow = (ROOT / ".github/workflows/quickstart.yml").read_text(
        encoding="utf-8"
    )
    for fragment in (
        "uv build --wheel",
        "uv venv build/quickstart-venv --python 3.12",
        "uv pip install --python",
        "cmake -S examples/quickstart -B build/quickstart",
        "-DFETCHCONTENT_SOURCE_DIR_PROTOCYTE=${{ github.workspace }}",
        "-DPROTOCYTE_FETCH_PROTOBUF=OFF",
        "-DProtobuf_PROTOC_EXECUTABLE=${{ steps.protoc.outputs.protoc }}",
        "cmake --build build/quickstart",
        "ctest --test-dir build/quickstart",
        "cmake -S examples/external-project-superbuild -B build/external-project",
        "-DPROTOCYTE_SOURCE_DIR=${{ github.workspace }}",
        "--target application_external",
        "ctest --test-dir build/external-project/application",
    ):
        assert fragment in workflow
    assert "-DPROTOC_EXECUTABLE=" not in workflow


def test_slim_readme_is_a_wiki_landing_page() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(readme.encode("utf-8")) < 15_000
    for destination in (
        "https://github.com/anthonyprintup/protocyte/wiki/Getting-Started",
        "https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration",
        "https://github.com/anthonyprintup/protocyte/wiki/Compatibility-and-Limitations",
        "https://github.com/anthonyprintup/protocyte/wiki/Contributing",
        "https://github.com/anthonyprintup/protocyte/wiki/AI-Disclosure",
        "(LICENSE)",
    ):
        assert destination in readme
    for fragment in (
        "include(FetchContent)",
        "FetchContent_Declare(",
        "9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14",
        "FetchContent_MakeAvailable(protocyte)",
        "protocyte_add_proto_library(",
        "HOSTED_ALLOCATOR",
        "target_link_libraries(application PRIVATE application::proto)",
    ):
        assert fragment in readme
    for legacy_heading in (
        "## CMake API Reference",
        "## Plugin Parameters",
        "## Runtime Notes",
        "## Maintainer Release Guide",
    ):
        assert legacy_heading not in readme
    assert "README.md#" not in readme
    assert "docs/debugger.md" not in readme


def test_platform_quickstart_and_superbuild_commands_are_documented() -> None:
    for page_name, build_target in (
        ("Getting-Started", None),
        ("ExternalProject-Superbuild", "application_external"),
    ):
        guide = _page(page_name)
        powershell = _fenced_blocks(guide, "powershell")
        posix = _fenced_blocks(guide, "bash")
        assert powershell
        assert posix
        combined_powershell = "\n".join(powershell)
        combined_posix = "\n".join(posix)
        for fragment in ("cmake -S", "cmake --build", "ctest --test-dir"):
            assert fragment in combined_powershell
            assert fragment in combined_posix
        if build_target is not None:
            assert f"--target {build_target}" in combined_powershell
            assert f"--target {build_target}" in combined_posix


@pytest.mark.skipif(shutil.which("bash") is None, reason="Bash is not available")
def test_documented_posix_blocks_parse_as_bash() -> None:
    paths = [*WIKI.glob("*.md"), ROOT / "tests/smoke/README.md"]
    block_count = 0
    for path in paths:
        document = path.read_text(encoding="utf-8")
        for block in _fenced_blocks(document, "bash"):
            block_count += 1
            result = subprocess.run(
                ["bash", "-n"],
                input=block,
                check=False,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"{path}: {result.stderr}"
    assert block_count


def test_direct_generation_examples_create_output_directories() -> None:
    guide = _page("Code-Generation")
    powershell = next(
        block
        for block in _fenced_blocks(guide, "powershell")
        if "--protocyte_out=runtime=emit:generated" in block
    )
    posix = next(
        block
        for block in _fenced_blocks(guide, "bash")
        if "--protocyte_out=runtime=emit:generated" in block
    )
    assert "New-Item -ItemType Directory -Force generated" in powershell
    assert "mkdir -p generated" in posix


def test_colon_valued_plugin_options_are_separate_from_protoc_output() -> None:
    parameters = _page("Plugin-Parameters")
    for language in ("powershell", "bash"):
        example = next(
            block
            for block in _fenced_blocks(parameters, language)
            if "namespace_prefix=mycorp::wire" in block
        )
        assert "--protocyte_out=out" in example
        assert (
            "--protocyte_opt=runtime=emit:vendor/protocyte,"
            "namespace_prefix=mycorp::wire,include_prefix=generated"
        ) in example
        assert "--protocyte_out=runtime=emit:vendor/protocyte" not in example
    assert "first `:`" in parameters


def test_installed_cmake_python_requirements_and_path_contracts_are_explicit() -> None:
    installed = _page("Installed-Package")
    fetchcontent = _page("FetchContent")
    troubleshooting = _page("Troubleshooting")
    combined = "\n".join((installed, fetchcontent, troubleshooting))

    for fragment in (
        "`venv`",
        "`ensurepip`",
        "`python3-venv`",
        'python3.12 -c "import ensurepip, venv"',
        "`CMAKE_BINARY_DIR`",
        "must not contain a semicolon",
        "wrapper from a semicolon-free",
    ):
        assert fragment in combined


def test_documented_protobuf_fallback_defaults_match_cmake_modes() -> None:
    integration = _page("CMake-Integration")
    fetchcontent = _page("FetchContent")
    installed = _page("Installed-Package")
    source_cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    installed_config = (ROOT / "cmake/protocyteConfig.cmake.in").read_text(
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
    assert "defaults to `ON`" in fetchcontent
    assert "defaults to `OFF`" in installed
    assert "host-runnable" in "\n".join((integration, fetchcontent, installed))
    assert "Fetch protobuf tools or import sources" in source_option
    assert "Fetch protobuf tools or import sources" in installed_default


def test_descriptor_name_portability_rejections_are_documented() -> None:
    generation = _page("Code-Generation")
    assert "descriptor names beginning with `-`" in generation
    assert "differ only by letter case" in generation
    assert "case-sensitive host" in generation
    assert "carriage returns or line feeds" in generation


def test_release_guidance_does_not_claim_unpublished_assets_exist() -> None:
    releases = _page("Releases-and-Versioning")
    compatibility = _page("Compatibility-and-Limitations")
    combined = releases + compatibility
    assert "No tag or GitHub release has been published yet" in releases
    assert "https://github.com/anthonyprintup/protocyte/releases" in combined
    assert "GIT_TAG vX.Y.Z" not in combined
    assert "9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14" in releases


def test_cmake_reference_documents_ownership_staging_and_safe_transfer() -> None:
    reference = _page("CMake-API-Reference")
    normalized = re.sub(r"\s+", " ", reference)
    for fragment in (
        "one immutable root claim",
        "one authoritative committed snapshot",
        "at most one write-ahead publication transaction",
        "durable replacement payloads",
        "Recovery therefore rolls forward",
        "retires only files whose bytes match the committed snapshot",
        "A compiler failure, timeout, or invalid staging result publishes no output transaction",
        "Modified retired outputs are preserved",
        "claim-token-authenticated reset",
        "Do not delete the output-lock namespace",
    ):
        assert fragment in normalized


def test_cmake_reference_covers_every_public_helper_argument() -> None:
    reference = _page("CMake-API-Reference")
    cmake = (ROOT / "cmake/ProtocyteFunctions.cmake").read_text(encoding="utf-8")
    assert "## `protocyte_setup_codegen`" in reference

    helpers = (
        "protocyte_get_host_tools",
        "protocyte_reset_output_directory",
        "protocyte_generate",
        "protocyte_add_proto_library",
        "protocyte_add_descriptor_set_library",
    )
    for index, helper in enumerate(helpers):
        function_body = cmake.split(f"function({helper})", maxsplit=1)[1].split(
            "endfunction()", maxsplit=1
        )[0]
        helper_reference = reference.split(f"## `{helper}`", maxsplit=1)[1]
        if index + 1 < len(helpers):
            helper_reference = helper_reference.split(
                f"## `{helpers[index + 1]}`", maxsplit=1
            )[0]

        declared_arguments: set[str] = set()
        argument_groups = (
            ("oneValueArgs",)
            if helper
            in {"protocyte_get_host_tools", "protocyte_reset_output_directory"}
            else ("options", "oneValueArgs", "multiValueArgs")
        )
        for group in argument_groups:
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
        assert not missing, f"{helper} arguments missing from wiki: {missing}"


def test_runtime_configuration_types_and_public_features_are_documented() -> None:
    embedded = _page("Embedded-and-Freestanding")
    runtime = _page("Runtime-Reference")
    for fragment in (
        "Config::Context",
        "Config::Vector<T>",
        "Config::Map<K, V>",
        "Config::Box<T>",
        "Config::Optional<T>",
        "Config::allocate",
        "Config::deallocate",
    ):
        assert fragment in embedded
    assert "PUBLIC PROTOCYTE_ENABLE_STD_STRING_VIEW=1" in runtime
    assert "All translation units" in runtime
    assert "PUBLIC PROTOCYTE_ENABLE_REFLECTION=1" in runtime
    assert "PUBLIC visibility is required" in runtime
    assert "TYPE SHARED" in runtime
    assert "target-unique import/export" in runtime


def test_debugger_guide_documents_python_enabled_lldb_requirement() -> None:
    guide = _page("Debugging")
    plain_lldb = guide.split("## Plain LLDB", maxsplit=1)[1].split(
        "## CLion", maxsplit=1
    )[0]
    assert "require an LLDB build with\nPython scripting enabled" in plain_lldb
    assert '(lldb) script print("LLDB Python scripting is available")' in plain_lldb
    assert "CLion's bundled LLDB is one suitable option" in plain_lldb
    assert "not in repository files shared with other users" in plain_lldb


def test_wiki_sync_helper_dry_run_apply_and_check(tmp_path: Path) -> None:
    source = tmp_path / "source"
    checkout = tmp_path / "protocyte.wiki"
    source.mkdir()
    checkout.mkdir()
    (checkout / ".git").mkdir()
    (source / "Home.md").write_bytes(b"# Home\r\n")
    (source / "Guide.md").write_bytes(b"# Guide\r")
    (checkout / "Home.md").write_bytes(b"# Old Home\n")
    (checkout / "Stale.md").write_bytes(b"# Stale\n")
    script = ROOT / ".github/scripts/sync_wiki.py"

    dry_run = subprocess.run(
        [sys.executable, str(script), str(checkout), "--source", str(source)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert dry_run.returncode == 0
    assert (checkout / "Home.md").read_bytes() == b"# Old Home\n"
    assert "Dry run only" in dry_run.stdout

    applied = subprocess.run(
        [
            sys.executable,
            str(script),
            str(checkout),
            "--source",
            str(source),
            "--apply",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert applied.returncode == 0
    assert (checkout / "Home.md").read_bytes() == b"# Home\n"
    assert (checkout / "Guide.md").read_bytes() == b"# Guide\n"
    assert not (checkout / "Stale.md").exists()

    (checkout / "Home.md").write_bytes(b"# Home\r\n")
    checked = subprocess.run(
        [
            sys.executable,
            str(script),
            str(checkout),
            "--source",
            str(source),
            "--check",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 0
    assert "already matches" in checked.stdout
    assert (checkout / "Home.md").read_bytes() == b"# Home\r\n"
