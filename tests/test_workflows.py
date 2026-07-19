from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _step_containing(job: str, needle: str) -> str:
    before, after = job.split(needle, maxsplit=1)
    step_start = before.rfind("\n      - name:")
    step_end = after.find("\n      - name:")
    assert step_start >= 0
    if step_end < 0:
        return before[step_start:] + needle + after
    return before[step_start:] + needle + after[:step_end]


def test_protobuf_fallback_is_reusable_and_required_by_ci_and_release() -> None:
    fallback = (
        REPO_ROOT / ".github" / "workflows" / "protobuf-fallback.yml"
    ).read_text(encoding="utf-8")
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    release = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    fallback_triggers = fallback.split("permissions:", maxsplit=1)[0]
    assert "workflow_call:" in fallback_triggers
    assert "workflow_dispatch:" in fallback_triggers
    assert "  protobuf-fallback:\n" in ci
    assert "    uses: ./.github/workflows/protobuf-fallback.yml\n" in ci
    assert "    uses: ./.github/workflows/ci.yml\n" in release


def test_protobuf_fallback_gates_linux_and_windows_source_builds() -> None:
    fallback = (
        REPO_ROOT / ".github" / "workflows" / "protobuf-fallback.yml"
    ).read_text(encoding="utf-8")

    assert "  find-package-fallback-linux:\n" in fallback
    assert "  find-package-fallback-windows:\n" in fallback
    assert "    runs-on: ubuntu-latest\n" in fallback
    assert "    runs-on: windows-latest\n" in fallback
    assert fallback.count("-DPROTOCYTE_FETCH_PROTOBUF=ON") == 2
    assert "Install prebuilt protoc" not in fallback


def test_generated_library_relocation_is_required_on_linux_and_windows() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    test_node = (
        "tests/test_cmake.py::"
        "test_proto_library_installs_exports_and_reconsumes_from_relocated_prefix"
    )
    linux_job = ci.split("\n  quickstart-linux:\n", maxsplit=1)[1].split(
        "\n  smoke-host:\n", maxsplit=1
    )[0]
    windows_job = ci.split("\n  smoke-host:\n", maxsplit=1)[1].split(
        "\n  smoke-host-msvc:\n", maxsplit=1
    )[0]
    required_env = 'PROTOCYTE_CI_REQUIRE_INSTALL_EXPORT_TEST: "1"'

    assert ci.count(test_node) == 2
    linux_step = _step_containing(linux_job, test_node)
    windows_step = _step_containing(windows_job, test_node)
    assert required_env in linux_step
    assert "${{ steps.protoc.outputs.protoc }}" in linux_step
    assert required_env in windows_step
    assert "${{ steps.windows-protoc.outputs.protoc }}" in windows_step


def test_ci_requires_real_protoc_integrations_without_tripling_the_matrix() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    plugin_job = ci.split("  plugin:\n", maxsplit=1)[1].split(
        "  quickstart-linux:\n", maxsplit=1
    )[0]

    assert "Install prebuilt protoc for required CMake integrations" in plugin_job
    assert "if: matrix.python-version == '3.12'" in plugin_job
    assert "id: integration-protoc" in plugin_job
    assert (
        "PROTOCYTE_CI_PROTOC_EXECUTABLE: "
        "${{ steps.integration-protoc.outputs.protoc }}"
    ) in plugin_job
    assert "PROTOCYTE_CI_REQUIRE_REAL_PROTOC_TESTS:" in plugin_job


def test_checked_smoke_gate_detects_untracked_tree_membership_drift() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    smoke_job = ci.split("  smoke-host:\n", maxsplit=1)[1].split(
        "  smoke-host-msvc:\n", maxsplit=1
    )[0]

    assert "PROTOCYTE_SMOKE_PROTOC:" in smoke_job
    assert "PROTOCYTE_SMOKE_PROTOBUF_IMPORT_DIR:" in smoke_job
    assert "PROTOCYTE_SMOKE_PLUGIN:" in smoke_job
    assert "PROTOCYTE_SMOKE_CLANG_FORMAT:" in smoke_job
    assert "git diff --exit-code -- tests/smoke/generated" in smoke_job
    assert ".github/scripts/verify_tracked_tree.py tests/smoke/generated" in smoke_job
    assert "--exclude-standard" not in smoke_job


def test_ci_requires_real_visual_studio_incremental_codegen() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    visual_studio_job = ci.split(
        "  visual-studio-incremental:\n", maxsplit=1
    )[1].split("  smoke-host-linux:\n", maxsplit=1)[0]

    assert "runs-on: windows-latest" in visual_studio_job
    assert "PROTOCYTE_CI_REQUIRE_REAL_PROTOC_TESTS: \"1\"" in visual_studio_job
    assert "PROTOCYTE_CI_REQUIRE_VISUAL_STUDIO_TEST: \"1\"" in visual_studio_job
    assert "PROTOCYTE_CI_VISUAL_STUDIO_TEST_ROOT:" in visual_studio_job
    assert (
        "test_visual_studio_codegen_builds_noop_and_rebuilds_transitive_import"
        in visual_studio_job
    )
