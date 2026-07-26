from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = ROOT / "examples" / "quickstart"


def test_quickstart_uses_the_public_fetchcontent_flow() -> None:
    cmake = (QUICKSTART / "CMakeLists.txt").read_text(encoding="utf-8")

    for fragment in (
        "include(FetchContent)",
        "FetchContent_Declare(",
        "GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git",
        "GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14",
        "FetchContent_MakeAvailable(protocyte)",
        "protocyte_add_proto_library(",
        "ALIAS quickstart::proto",
        'PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"',
        "DISCOVER",
        "HOSTED_ALLOCATOR",
        "target_link_libraries(protocyte_quickstart PRIVATE quickstart::proto)",
    ):
        assert fragment in cmake

    assert "add_custom_command(" not in cmake
    assert "_quickstart_probe_tool" not in cmake
    assert "PROTOC_EXECUTABLE" not in cmake


def test_quickstart_ci_tests_the_checkout_through_fetchcontent() -> None:
    workflow = (ROOT / ".github/workflows/quickstart.yml").read_text(
        encoding="utf-8"
    )

    assert workflow.count("-DFETCHCONTENT_SOURCE_DIR_PROTOCYTE=${{ github.workspace }}") == 3
    assert workflow.count("-DPROTOCYTE_FETCH_PROTOBUF=OFF") == 6
    assert workflow.count(
        "-DProtobuf_PROTOC_EXECUTABLE=${{ steps.protoc.outputs.protoc }}"
    ) == 6
    assert "-DPROTOC_EXECUTABLE=" not in workflow


def test_external_project_rechecks_application_source_dependencies() -> None:
    superbuild = (
        ROOT / "examples/external-project-superbuild/CMakeLists.txt"
    ).read_text(encoding="utf-8")
    application = superbuild.split(
        "ExternalProject_Add(\n    application_external", maxsplit=1
    )[1]

    assert "BUILD_ALWAYS TRUE" in application
