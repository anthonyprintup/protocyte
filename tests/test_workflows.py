import re
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


def _job_named(workflow: str, name: str) -> str:
    job = workflow.split(f"\n  {name}:\n", maxsplit=1)[1]
    next_job = re.search(r"\n  [a-z0-9][a-z0-9-]*:\n", job)
    return job if next_job is None else job[: next_job.start()]


def _steps_by_name(job: str) -> dict[str, str]:
    steps = job.split("\n    steps:\n", maxsplit=1)[1]
    blocks = re.split(r"(?=^      - name: )", steps, flags=re.MULTILINE)
    return {
        block.splitlines()[0].removeprefix("      - name: "): block
        for block in blocks
        if block.startswith("      - name: ")
    }


def test_protobuf_fallback_is_reusable_and_required_by_ci_and_release() -> None:
    fallback = (
        REPO_ROOT / ".github" / "workflows" / "protobuf-fallback.yml"
    ).read_text(encoding="utf-8")
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )

    fallback_triggers = fallback.split("permissions:", maxsplit=1)[0]
    assert "workflow_call:" in fallback_triggers
    assert "workflow_dispatch:" in fallback_triggers
    assert "  protobuf-fallback:\n" in ci
    assert "    uses: ./.github/workflows/protobuf-fallback.yml\n" in ci
    assert "    uses: ./.github/workflows/ci.yml\n" in release


def test_ci_generates_with_the_public_protobuf_dependency_floor() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    floor = _job_named(ci, "protobuf-floor")
    floor_steps = _steps_by_name(floor)
    install = floor_steps["Install the public protobuf floor outside the lockfile"]

    assert "runs-on: ubuntu-latest" in floor
    assert "uv venv build/protobuf-floor-venv --python 3.12" in install
    assert (
        "uv pip install --python build/protobuf-floor-venv/bin/python --no-deps ."
        in install
    )
    assert '"protobuf==6.30.0"' in install
    assert 'google.protobuf.__version__ == "6.30.0"' in install
    upb = floor_steps["Generate with the protobuf floor (upb)"]
    assert "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: upb" in upb
    assert 'PROTOCYTE_EXPECTED_PROTOBUF_VERSION: "6.30.0"' in upb
    assert "tests/test_protobuf_floor.py" in upb
    pure_python = floor_steps["Generate with the protobuf floor (pure Python)"]
    assert "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: python" in pure_python
    assert 'PROTOCYTE_EXPECTED_PROTOBUF_VERSION: "6.30.0"' in pure_python
    assert "tests/test_protobuf_floor.py" in pure_python


def test_ci_private_path_guard_scans_the_complete_checkout_object_database() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    guard = _job_named(ci, "private-path-guard")

    assert "fetch-depth: 0" in guard
    assert "python .github/scripts/check_private_paths.py" in guard
    assert "Reject private absolute paths" in guard


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
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
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
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    plugin_job = ci.split("  plugin:\n", maxsplit=1)[1].split(
        "  quickstart-linux:\n", maxsplit=1
    )[0]

    assert "Install prebuilt protoc for required CMake integrations" in plugin_job
    assert "if: matrix.python-version == '3.12'" in plugin_job
    assert "id: integration-protoc" in plugin_job
    assert (
        "PROTOCYTE_CI_PROTOC_EXECUTABLE: ${{ steps.integration-protoc.outputs.protoc }}"
    ) in plugin_job
    assert "PROTOCYTE_CI_REQUIRE_REAL_PROTOC_TESTS:" in plugin_job


def test_quickstart_wheel_is_exercised_on_linux_windows_and_macos() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pinned_actions = (
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e",
    )

    for job_name, runner in (
        ("quickstart-linux", "ubuntu-latest"),
        ("quickstart-windows", "windows-latest"),
        ("quickstart-macos", "macos-latest"),
    ):
        job = _job_named(ci, job_name)
        assert f"runs-on: {runner}" in job
        for action in pinned_actions:
            assert f"uses: {action}" in job
        for fragment in (
            "python .github/scripts/install_protoc.py",
            "uv build --wheel",
            "uv venv build/quickstart-venv --python 3.12",
            "uv pip install --python",
            "-m protocyte --help",
            "-m protocyte --version",
            "cmake -S examples/quickstart -B build/quickstart",
            "cmake --build build/quickstart",
            "ctest --test-dir build/quickstart",
        ):
            assert fragment in job
        assert "${{ steps.protoc.outputs.protoc }}" in job

    windows_job = _job_named(ci, "quickstart-windows")
    assert "protoc-gen-protocyte.exe --help" in windows_job
    assert "protoc-gen-protocyte.exe --version" in windows_job
    assert "uses: ilammy/msvc-dev-cmd@0b201ec74fa43914dc39ae48a89fd1d8cb592756" in (
        windows_job
    )
    assert "cmake --build build/quickstart --config Release" in windows_job
    assert "ctest --test-dir build/quickstart -C Release" in windows_job

    for job_name in ("quickstart-linux", "quickstart-macos"):
        job = _job_named(ci, job_name)
        assert "build/quickstart-venv/bin/protoc-gen-protocyte --help" in job
        assert "build/quickstart-venv/bin/protoc-gen-protocyte --version" in job


def test_macos_find_package_uses_a_read_only_installed_prefix_and_managed_plugin() -> (
    None
):
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = _job_named(ci, "find-package-macos")
    steps = _steps_by_name(job)

    assert "runs-on: macos-latest" in job
    checkout = steps["Check out repository"]
    assert "ref: ${{ inputs.checkout_ref || github.sha }}" in checkout
    protoc = steps["Install prebuilt protoc"]
    assert "id: protoc" in protoc
    assert (
        'python .github/scripts/install_protoc.py --dest "${{ runner.temp }}/protoc"'
        in protoc
    )
    install = steps["Configure protocyte install tree"]
    assert "cmake -S . -B build/protocyte-install" in install
    assert "-DCMAKE_BUILD_TYPE=Release" in install
    assert (
        "chmod -R a-w build/protocyte-prefix"
        in steps["Make installed prefix read-only"]
    )
    configure = steps["Configure find_package integration test"]
    assert "cmake -S tests/find_package -B tests/find_package/build" in configure
    assert (
        "-DCMAKE_PREFIX_PATH=${{ github.workspace }}/build/protocyte-prefix"
        in configure
    )
    assert (
        "-DProtobuf_PROTOC_EXECUTABLE=${{ steps.protoc.outputs.protoc }}" in configure
    )
    assert "PROTOCYTE_PLUGIN_EXECUTABLE" not in configure
    assert (
        "cmake --build tests/find_package/build"
        in steps["Build find_package integration test"]
    )
    assert (
        "ctest --test-dir tests/find_package/build --output-on-failure"
        in steps["Run find_package integration test"]
    )
    prefix_guard = steps["Verify provisioning did not modify the installed prefix"]
    assert "share/protocyte/python/build" in prefix_guard
    assert "share/protocyte/python/src/protocyte.egg-info" in prefix_guard


def test_checked_smoke_gate_detects_untracked_tree_membership_drift() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
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
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    visual_studio_job = ci.split("  visual-studio-incremental:\n", maxsplit=1)[1].split(
        "  smoke-host-linux:\n", maxsplit=1
    )[0]

    assert "runs-on: windows-latest" in visual_studio_job
    assert 'PROTOCYTE_CI_REQUIRE_REAL_PROTOC_TESTS: "1"' in visual_studio_job
    assert 'PROTOCYTE_CI_REQUIRE_VISUAL_STUDIO_TEST: "1"' in visual_studio_job
    assert "PROTOCYTE_CI_VISUAL_STUDIO_TEST_ROOT:" in visual_studio_job
    assert (
        "test_visual_studio_codegen_builds_noop_and_rebuilds_transitive_import"
        in visual_studio_job
    )


def test_release_artifacts_are_rebuilt_normalized_and_compared() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    build = _job_named(release, "build-release")

    assert 'version: "0.11.7"' in build
    assert 'python-version: "3.12.9"' in build
    assert 'CMAKE_VERSION: "4.3.2"' in build
    assert 'PYTHONHASHSEED: "0"' in build
    assert "TZ: UTC" in build
    assert 'UV_PYTHON: "3.12.9"' in build
    assert "SOURCE_DATE_EPOCH=$(git show -s --format=%ct HEAD)" in build
    assert "for build in first second; do" in build
    assert 'git archive HEAD | tar -x -C "$source_dir"' in build
    assert build.count("reproducible_archive.py") == 3
    assert build.count("cmp \\") == 3
    assert 'uv build "$source_dir" --out-dir "$output_dir"' in build
    assert '-S "$source_dir" -B "${build_root}/cmake-build"' in build
    assert 'uvx --from "cmake==$CMAKE_VERSION" cmake \\' in build

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires = ["setuptools==80.9.0"]' in pyproject


def test_release_tests_each_exact_artifact_before_exact_upload() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    build = _job_named(release, "build-release")
    build_steps = _steps_by_name(build)
    publish = _job_named(release, "publish")
    publication = _steps_by_name(publish)[
        "Create, verify, and publish immutable GitHub release"
    ]
    upload = build_steps["Upload exact publication handoff"]

    test_step_names = {
        "wheel_name": "Test exact wheel artifact",
        "sdist_name": "Test exact source artifact",
        "archive_name": "Test exact CMake prefix artifact",
    }
    for output, test_step_name in test_step_names.items():
        artifact = f"${{{{ needs.validate-tag.outputs.{output} }}}}"
        assert artifact in build_steps[test_step_name]
        assert f"staging/release-handoff/{artifact}" in upload
        assert f"$RUNNER_TEMP/release-handoff/{artifact}" in publication
        assert build.index(test_step_name) < build.index(
            "Stage exact publication handoff"
        )

    assert build.index("Stage exact publication handoff") < build.index(
        "Upload exact publication handoff"
    )
    assert "dist/*.whl" not in upload
    assert "dist/*.tar.gz" not in upload
    assert "staging/release-handoff/SHA256SUMS" in upload
    assert "if-no-files-found: error" in upload
    assert "python -m tarfile -e" in build
    assert "-S tests/release_cmake_consumer" in build
    assert build.count("-m protocyte --help") == 2
    assert build.count('protoc-gen-protocyte" --help') == 2


def test_release_checkout_credentials_are_not_persisted_or_needed_for_refetch() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    validate_tag = _job_named(release, "validate-tag")
    build = _job_named(release, "build-release")
    publish = _job_named(release, "publish")
    publish_steps = _steps_by_name(publish)

    assert "permissions:\n  contents: none" in release
    assert "permissions:\n      contents: read" in build
    assert "permissions:\n      actions: read\n      contents: write" in publish
    assert (
        "persist-credentials: false"
        in _steps_by_name(validate_tag)["Check out repository"]
    )
    assert "persist-credentials: false" in _steps_by_name(build)["Check out repository"]
    trusted_checkout = publish_steps["Check out trusted publication code"]
    assert "clean: true" in trusted_checkout
    assert "persist-credentials: false" in trusted_checkout
    assert "ref: ${{ github.sha }}" in trusted_checkout

    trusted_revision = _steps_by_name(validate_tag)[
        "Require the live default-branch workflow revision"
    ]
    validation = _steps_by_name(validate_tag)["Compare tag and package version"]
    assert '"$GITHUB_REF" != "refs/heads/main"' in trusted_revision
    assert '"$fetched_main" != "$GITHUB_SHA"' in trusted_revision
    assert 'tag_ref="refs/tags/$tag"' in validation
    assert 'git merge-base --is-ancestor "$target" "$main_ref"' in validation
    assert 'git show "${target}:src/protocyte/__init__.py"' in validation
    assert "ref: ${{ needs.validate-tag.outputs.target }}" in build
    assert "git fetch" not in validate_tag


def test_release_policy_preflight_uses_trusted_code_and_gates_expensive_work() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    policy = _job_named(release, "release-policy")
    gate = _job_named(release, "release-gate")
    build = _job_named(release, "build-release")
    policy_steps = _steps_by_name(policy)
    preflight = policy_steps[
        "Require trusted single-writer release policy before build"
    ]
    checkout = policy_steps["Check out trusted policy code"]

    assert "needs: validate-tag" in policy
    assert "environment: release" in policy
    assert "permissions:\n      contents: read" in policy
    assert "clean: true" in checkout
    assert "persist-credentials: false" in checkout
    assert "ref: ${{ github.sha }}" in checkout
    assert "RELEASE_POLICY_AUDIT_TOKEN" in preflight
    assert "RELEASE_IMMUTABILITY_TOKEN" not in preflight
    assert "RELEASE_TAG_RULESET_ID" in preflight
    assert "LEGACY_RELEASE_WORKFLOW_ID" in preflight
    assert "python .github/scripts/check_release_policy.py" in preflight
    assert '--workflow-ref "$GITHUB_REF"' in preflight
    assert '--workflow-target "$GITHUB_SHA"' in preflight
    assert "--default-branch main" in preflight
    assert '--repository-root "$GITHUB_WORKSPACE"' in preflight
    assert "- release-policy" in gate
    assert "- release-gate" in build


def test_release_publication_uses_isolated_least_privilege_credentials() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    policy = _job_named(release, "release-policy")
    build = _job_named(release, "build-release")
    publish = _job_named(release, "publish")
    publish_steps = _steps_by_name(publish)
    publication = publish_steps["Create, verify, and publish immutable GitHub release"]

    assert "environment: release" in policy
    assert "environment: release" in publish
    assert "RELEASE_POLICY_AUDIT_TOKEN" in policy
    assert "RELEASE_POLICY_AUDIT_TOKEN" not in publish
    assert "contents: write" not in build
    assert "RELEASE_IMMUTABILITY_TOKEN" not in build
    assert "RELEASE_POLICY_AUDIT_TOKEN" not in build
    assert "PROTOCYTE_RELEASE_POLICY_TOKEN" not in build
    assert "python .github/scripts/publish_release.py" not in build
    assert "uv sync" not in publish
    assert "uv build" not in publish
    assert "Test exact wheel artifact" not in publish
    assert "GH_TOKEN: ${{ github.token }}" in publication
    assert (
        "PROTOCYTE_RELEASE_POLICY_TOKEN: ${{ secrets.RELEASE_IMMUTABILITY_TOKEN }}"
    ) in publication
    assert "python .github/scripts/publish_release.py" in publication
    assert '"$GITHUB_REPOSITORY"' in publication
    assert '"${{ needs.validate-tag.outputs.tag }}"' in publication
    assert '"${{ needs.validate-tag.outputs.target }}"' in publication
    assert "--trusted-branch main" in publication
    assert '--trusted-target "$GITHUB_SHA"' in publication
    assert publish.index("Check out trusted publication code") < publish.index(
        "Bind and download immutable release handoff"
    )
    assert publish.index("Extract and verify exact release handoff") < publish.index(
        "Create, verify, and publish immutable GitHub release"
    )
    assert "softprops/action-gh-release@" not in publish
    assert "gh release upload" not in publish
    assert "gh release edit" not in publish


def test_release_handoff_is_id_run_and_digest_bound_before_publication() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    build = _job_named(release, "build-release")
    publish = _job_named(release, "publish")
    build_steps = _steps_by_name(build)
    publish_steps = _steps_by_name(publish)
    stage = build_steps["Stage exact publication handoff"]
    upload = build_steps["Upload exact publication handoff"]
    binding = publish_steps["Bind and download immutable release handoff"]
    extraction = publish_steps["Extract and verify exact release handoff"]

    assert "artifact_id: ${{ steps.release-handoff.outputs.artifact-id }}" in build
    assert (
        "artifact_digest: ${{ steps.release-handoff.outputs.artifact-digest }}" in build
    )
    assert "sha256sum \\" in stage
    assert "sha256sum --check --strict SHA256SUMS" in stage
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in upload
    assert "name: protocyte-release-${{ github.run_id }}-${{ github.sha }}" in upload
    assert "compression-level: 0" in upload
    assert "retention-days: 1" in upload

    assert "- build-release" in publish
    assert "ARTIFACT_ID: ${{ needs.build-release.outputs.artifact_id }}" in binding
    assert (
        "EXPECTED_ARTIFACT_DIGEST: "
        "${{ needs.build-release.outputs.artifact_digest }}" in binding
    )
    for fragment in (
        '"$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID"',
        ".workflow_run.id",
        ".workflow_run.head_sha",
        ".digest",
        '"$GITHUB_RUN_ID"',
        '"$GITHUB_SHA"',
        "/actions/artifacts/$ARTIFACT_ID/zip",
        'sha256sum "$archive"',
        '"$downloaded_digest" != "$expected_digest"',
    ):
        assert fragment in binding

    assert "$RUNNER_TEMP/release-handoff" in extraction
    assert "python -I -" in extraction
    assert "release handoff contains an unexpected file set" in extraction
    assert "stat.S_ISLNK(mode)" in extraction
    assert 'cmp SHA256SUMS "$RUNNER_TEMP/recomputed-SHA256SUMS"' in extraction
    assert "sha256sum --check --strict SHA256SUMS" in extraction
    assert ".github/scripts" not in upload
    assert "$GITHUB_WORKSPACE" not in extraction


def test_authenticated_release_http_requests_reject_redirects() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    policy = _job_named(release, "release-policy")
    publish = _job_named(release, "publish")
    binding = _steps_by_name(publish)["Bind and download immutable release handoff"]

    assert "gh api" not in policy
    assert "gh api" not in binding
    assert "curl --disable --silent --show-error --max-redirs 0" in binding
    assert '-H "Authorization: Bearer $GH_TOKEN"' in binding
    policy_script = (
        REPO_ROOT / ".github" / "scripts" / "check_release_policy.py"
    ).read_text(encoding="utf-8")
    assert "_GitHubClient" in policy_script
    artifact_probe = binding.split('archive="$RUNNER_TEMP/release-handoff.zip"', 1)[1]
    artifact_probe = artifact_probe.split(
        'redirect_url="$(python -I .github/scripts/parse_release_redirect.py', 1
    )[0]
    assert artifact_probe.count("Authorization: Bearer $GH_TOKEN") == 1
    assert "_GitHubClient(contents_token, api_url)" in policy_script
    assert "_GitHubClient(policy_token, api_url)" in policy_script
    assert "Authenticated GitHub API requests must not follow redirects." in binding
    assert '--dump-header "$redirect_headers"' in binding
    assert '[[ ! "$status" =~ ^30(1|2|3|7|8)$ ]]' in binding
    assert "python -I .github/scripts/parse_release_redirect.py" in binding
    assert "--location --max-redirs 3" in binding
    assert "--proto '=https' --proto-redir '=https'" in binding
    signed_download = binding.split(
        'redirect_url="$(python -I .github/scripts/parse_release_redirect.py',
        maxsplit=1,
    )[1]
    assert "Authorization: Bearer $GH_TOKEN" not in signed_download


def test_release_transaction_is_create_only_id_bound_and_immutable() -> None:
    transaction = (REPO_ROOT / ".github" / "scripts" / "publish_release.py").read_text(
        encoding="utf-8"
    )

    assert '"POST",\n            f"{self._repository_path}/releases"' in transaction
    assert 'payload={"draft": False}' in transaction
    assert 'f"{self._repository_path}/releases/{release_id}"' in transaction
    assert 'f"/{self._repository_path}/releases/{release_id}/assets"' in transaction
    assert "api.immutable_releases_enabled()" in transaction
    assert "api.resolve_tag_target(spec.tag)" in transaction
    assert transaction.count("_require_tag_target(api, spec)") >= 5
    assert transaction.count("_require_trusted_source(api, spec)") >= 5
    assert "this workflow never mutates existing" in transaction
    assert "release creation lost an existence race" in transaction
    assert '"DELETE"' not in transaction
    assert "overwrite_files" not in transaction


def test_release_transaction_order_is_build_test_then_serialized_publication() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    gate = _job_named(release, "release-gate")
    build = _job_named(release, "build-release")
    publish = _job_named(release, "publish")
    publication_name = "Create, verify, and publish immutable GitHub release"

    assert "- release-policy" in gate
    assert "- release-gate" in build
    assert "- build-release" in publish
    for test_step_name in (
        "Test exact wheel artifact",
        "Test exact source artifact",
        "Test exact CMake prefix artifact",
    ):
        assert build.index(test_step_name) < build.index(
            "Upload exact publication handoff"
        )
    assert publish.index("Bind and download immutable release handoff") < publish.index(
        publication_name
    )
    assert publish.rstrip().endswith(
        '"$RUNNER_TEMP/release-handoff/${{ needs.validate-tag.outputs.archive_name }}"'
    )


def test_release_publication_is_the_repository_single_writer() -> None:
    workflow_directory = REPO_ROOT / ".github" / "workflows"
    workflows = {
        path.name: path.read_text(encoding="utf-8")
        for pattern in ("*.yml", "*.yaml")
        for path in workflow_directory.glob(pattern)
    }
    legacy = workflows["release.yml"]
    release = workflows["publish-release.yml"]
    publish = _job_named(release, "publish")

    assert "workflow_call:" in legacy
    assert "workflow_dispatch:" not in legacy
    assert "push:" not in legacy
    assert "contents: none" in legacy
    assert "contents: write" not in legacy
    assert "if: ${{ false }}" in legacy
    assert "run: exit 1" in legacy
    assert "group: protocyte-release-publication-${{ github.repository }}" in release
    assert "cancel-in-progress: false" in release
    assert "queue: max" in release
    assert "workflow_dispatch:" in release
    assert "push:\n    tags:" not in release
    assert '"$GITHUB_REF" != "refs/heads/main"' in release
    assert "check_release_policy.py" in release
    assert "RELEASE_TAG_RULESET_ID" in release
    assert "LEGACY_RELEASE_WORKFLOW_ID" in release
    assert release.count("contents: write") == 1
    assert "contents: write" in publish
    assert "environment: release" in publish
    for name, workflow in workflows.items():
        assert "write-all" not in workflow
        if name != "publish-release.yml":
            assert "contents: write" not in workflow

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "single-writer boundary" in readme
    assert "cannot make separate GitHub" in readme
    assert "API calls atomic" in readme
    assert "prohibit tag updates and deletions" in readme
    assert "disable administrator bypass" in readme
    assert "Source changes cannot retroactively disable copies" in readme
    assert "actions/workflows/release.yml --jq .id" in readme
    assert "actions/workflows/$legacy_id/disable" in readme
    assert "deliberately keeps `.github/workflows/release.yml`" in readme
    assert "always-skipped retirement job" in readme
    assert "instead of `disabled_manually`" in readme
    assert "`disabled_manually`" in readme
    assert "publish-release.yml" in readme


def test_release_gate_tests_the_requested_tag_with_trusted_workflow_code() -> None:
    release = (REPO_ROOT / ".github" / "workflows" / "publish-release.yml").read_text(
        encoding="utf-8"
    )
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    fallback = (
        REPO_ROOT / ".github" / "workflows" / "protobuf-fallback.yml"
    ).read_text(encoding="utf-8")

    gate = _job_named(release, "release-gate")
    assert "uses: ./.github/workflows/ci.yml" in gate
    assert "checkout_ref: ${{ needs.validate-tag.outputs.target }}" in gate
    assert "workflow_call:" in ci
    assert "checkout_ref:" in ci
    checkout_action = "uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5"
    exact_ref = "\n          ref: ${{ inputs.checkout_ref || github.sha }}"
    assert ci.count(checkout_action) == ci.count(exact_ref)
    assert fallback.count(checkout_action) == fallback.count(exact_ref)
    assert "checkout_ref: ${{ inputs.checkout_ref || github.sha }}" in ci
