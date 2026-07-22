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


def _continued_shell_commands(step: str) -> list[str]:
    commands: list[str] = []
    continued: list[str] = []
    for raw_line in step.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        continued.append(line.removesuffix("\\").rstrip())
        if not line.endswith("\\"):
            commands.append(" ".join(continued))
            continued = []
    assert not continued
    return commands


def test_protobuf_fallback_is_reusable_and_required_by_ci_and_release() -> None:
    fallback = (
        REPO_ROOT / ".github" / "workflows" / "protobuf-fallback.yml"
    ).read_text(encoding="utf-8")
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
        encoding="utf-8"
    )

    fallback_triggers = fallback.split("permissions:", maxsplit=1)[0]
    assert "workflow_call:" in fallback_triggers
    assert "workflow_dispatch:" in fallback_triggers
    assert "  protobuf-fallback:\n" in ci
    assert "    uses: ./.github/workflows/protobuf-fallback.yml\n" in ci
    assert "    uses: ./.github/workflows/ci.yml\n" in release


def test_ci_generates_with_the_public_protobuf_dependency_floor() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    floor = _job_named(ci, "protobuf-floor")
    floor_steps = _steps_by_name(floor)
    install = floor_steps["Install the public protobuf floor outside the lockfile"]

    assert "runs-on: ubuntu-latest" in floor
    assert "uv venv build/protobuf-floor-venv --python 3.12" in install
    assert "uv pip install --python build/protobuf-floor-venv/bin/python --no-deps ." in install
    assert '"protobuf==6.30.0"' in install
    assert "google.protobuf.__version__ == \"6.30.0\"" in install
    upb = floor_steps["Generate with the protobuf floor (upb)"]
    assert "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: upb" in upb
    assert 'PROTOCYTE_EXPECTED_PROTOBUF_VERSION: "6.30.0"' in upb
    assert "tests/test_protobuf_floor.py" in upb
    pure_python = floor_steps["Generate with the protobuf floor (pure Python)"]
    assert "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION: python" in pure_python
    assert 'PROTOCYTE_EXPECTED_PROTOBUF_VERSION: "6.30.0"' in pure_python
    assert "tests/test_protobuf_floor.py" in pure_python


def test_ci_private_path_guard_scans_the_complete_checkout_object_database() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
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


def test_quickstart_wheel_is_exercised_on_linux_windows_and_macos() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
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


def test_release_artifacts_are_rebuilt_normalized_and_compared() -> None:
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
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
    build_steps = _steps_by_name(build)
    plugin_build = build_steps["Build and normalize plugin packages twice"]
    cmake_build = build_steps["Build and normalize CMake prefix twice"]
    assert plugin_build.count("cmp \\") == 2
    assert cmake_build.count("cmp \\") == 1
    assert 'uv build "$source_dir" \\' in plugin_build
    assert '--out-dir "$output_dir"' in plugin_build
    assert '--python "$PWD/staging/release-tools/bootstrap-venv/bin/python"' in plugin_build
    assert "--no-build-isolation" in plugin_build
    assert "--no-index" in plugin_build
    assert "--offline" in plugin_build
    assert '-S "$source_dir" -B "${build_root}/cmake-build"' in cmake_build
    assert '"$RELEASE_CMAKE" \\' in cmake_build

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires = ["setuptools==80.9.0"]' in pyproject


def test_release_tests_each_exact_artifact_before_exact_upload() -> None:
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
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
        assert f'$RUNNER_TEMP/release-handoff/{artifact}' in publication
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
    assert "Install prebuilt protoc for release artifact tests" in build
    assert "id: release-protoc" in build
    assert build.index("Install prebuilt protoc for release artifact tests") < build.index(
        "Test exact wheel artifact"
    )
    for artifact, test_root in (
        ("wheel_name", "wheel"),
        ("sdist_name", "sdist"),
    ):
        test_step = build_steps[test_step_names[artifact]]
        assert "test_release_plugin_artifact.py" in test_step
        assert (
            f'"staging/release-tests/publication-artifacts/'
            f'${{{{ needs.validate-tag.outputs.{artifact} }}}}"'
        ) in test_step
        assert f"staging/release-tests/{test_root}" in test_step
        assert "steps.release-protoc.outputs.protoc" in test_step
        assert '"$RELEASE_CMAKE"' in test_step
        assert '"$RELEASE_CTEST"' in test_step

    cmake_prefix_test = build_steps["Test exact CMake prefix artifact"]
    assert "-S tests/find_package" in cmake_prefix_test
    assert "-DProtobuf_PROTOC_EXECUTABLE=${{ steps.release-protoc.outputs.protoc }}" in cmake_prefix_test
    assert "--build staging/release-tests/cmake-build" in cmake_prefix_test
    assert '"$RELEASE_CTEST" \\' in cmake_prefix_test
    assert "--test-dir staging/release-tests/cmake-build --output-on-failure" in cmake_prefix_test
    assert "PROTOCYTE_PLUGIN_EXECUTABLE" not in cmake_prefix_test

    find_package_consumer = (
        REPO_ROOT / "tests" / "find_package" / "CMakeLists.txt"
    ).read_text(encoding="utf-8")
    assert "protocyte_add_proto_library(" in find_package_consumer
    assert "PROTOCYTE_INTERNAL_MANAGED_PLUGIN_EXECUTABLE" in find_package_consumer
    assert "add_test(NAME find_package_demo COMMAND find_package_demo)" in find_package_consumer

    plugin_artifact_test = (
        REPO_ROOT / ".github" / "scripts" / "test_release_plugin_artifact.py"
    ).read_text(encoding="utf-8")
    assert 'repository_root / "examples" / "quickstart"' in plugin_artifact_test
    assert '"--build",\n        str(quickstart_build)' in plugin_artifact_test
    assert 'str(ctest),\n        "--test-dir"' in plugin_artifact_test
    assert '"-DPROTOC_EXECUTABLE={protoc}"' in plugin_artifact_test
    assert '"-DPROTOCYTE_PLUGIN_EXECUTABLE={plugin}"' in plugin_artifact_test


def test_release_artifact_smoke_is_hash_locked_offline_and_integrity_bound() -> None:
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(encoding="utf-8")
    build = _job_named(release, "build-release")
    steps = _steps_by_name(build)
    prepare_name = "Prepare hash-locked release smoke tools and environments"
    prepare = steps[prepare_name]
    freeze = steps["Freeze exact release artifacts for isolated smoke tests"]
    wheel_test = steps["Test exact wheel artifact"]
    source_test = steps["Test exact source artifact"]
    cmake_test = steps["Test exact CMake prefix artifact"]
    handoff = steps["Stage exact publication handoff"]

    assert build.index(prepare_name) < build.index(
        "Build and normalize plugin packages twice"
    )
    assert ".github/release-cmake-constraints.txt" in prepare
    assert 'locked_cmake_version="$(' in prepare
    assert '"$locked_cmake_version" != "$CMAKE_VERSION"' in prepare
    assert "protocyte-cmake-constraints.txt" in prepare
    assert prepare.count("--require-hashes") == 5
    assert prepare.count("--only-binary=:all:") == 5
    assert prepare.count("pip --isolated download") == 2
    assert "--no-deps" in prepare
    assert "--dest \"$wheelhouse\"" in prepare
    assert "--dest \"$tool_wheelhouse\"" in prepare
    assert '--find-links "$tool_wheelhouse"' in prepare
    assert '--requirement "$cmake_constraints"' in prepare
    assert "for artifact_kind in wheel sdist; do" in prepare
    assert "--no-index" in prepare
    assert '--find-links "$wheelhouse"' in prepare
    assert 'chmod -R a-w "$wheelhouse" "$tool_wheelhouse"' in prepare

    prepare_commands = _continued_shell_commands(prepare)
    resolver_commands = [
        command
        for command in prepare_commands
        if "uv pip install" in command or "pip --isolated download" in command
    ]
    assert len(resolver_commands) == 5
    assert all("--require-hashes" in command for command in resolver_commands)
    cmake_install = next(
        command
        for command in resolver_commands
        if '--requirement "$cmake_constraints"' in command
        and "uv pip install" in command
    )
    assert "--no-index" in cmake_install
    assert '--find-links "$tool_wheelhouse"' in cmake_install

    plugin_build = steps["Build and normalize plugin packages twice"]
    assert 'uv build "$source_dir" \\' in plugin_build
    assert '--python "$PWD/staging/release-tools/bootstrap-venv/bin/python"' in plugin_build
    assert "--no-build-isolation" in plugin_build
    assert "--no-index" in plugin_build
    assert "--offline" in plugin_build
    assert 'uv build "$source_dir" --out-dir' not in plugin_build
    build_commands = [
        command
        for command in _continued_shell_commands(plugin_build)
        if command.startswith('uv build "$source_dir"')
    ]
    assert len(build_commands) == 1
    release_build = build_commands[0]
    assert "--no-build-isolation" in release_build
    assert "--no-index" in release_build
    assert "--offline" in release_build
    assert '--python "$PWD/staging/release-tools/bootstrap-venv/bin/python"' in release_build
    artifact_build_boundary = build.index("Build and normalize plugin packages twice")
    post_bootstrap_build = build[artifact_build_boundary:]
    assert "uv pip install" not in post_bootstrap_build
    assert "pip --isolated download" not in post_bootstrap_build
    assert "uv run" not in post_bootstrap_build
    assert post_bootstrap_build.count('"$PWD/.venv/bin/python"') == 3

    cmake_lock = (
        REPO_ROOT / ".github" / "release-cmake-constraints.txt"
    ).read_text(encoding="utf-8")
    assert "cmake==4.3.2 \\" in cmake_lock
    cmake_hashes = [
        line.strip()
        for line in cmake_lock.splitlines()
        if line.strip().startswith("--hash=sha256:")
    ]
    assert cmake_hashes == [
        "--hash=sha256:339655b93289c1b03c6a72523d46d3b0d19dc51406d3a90f8eefcbec525cb271"
    ]

    assert build.index("Build and normalize CMake prefix twice") < build.index(
        "Freeze exact release artifacts for isolated smoke tests"
    )
    assert build.index("Freeze exact release artifacts for isolated smoke tests") < build.index(
        "Test exact wheel artifact"
    )
    assert freeze.count("cmp \\") == 3
    assert "sha256sum --check --strict SHA256SUMS" in freeze
    assert "chmod a-w" in freeze
    assert "publication-artifacts" in wheel_test
    assert "publication-artifacts" in source_test

    assert "PIP_CONFIG_FILE: /dev/null" in cmake_test
    assert "PIP_FIND_LINKS:" in cmake_test
    assert 'PIP_NO_INDEX: "1"' in cmake_test
    assert 'UV_NO_INDEX: "1"' in cmake_test
    assert 'UV_OFFLINE: "1"' in cmake_test
    assert "uvx" not in cmake_test

    assert handoff.index("sha256sum --check --strict SHA256SUMS") < handoff.index(
        "mkdir -p \"$handoff\""
    )
    assert handoff.count("cmp \\") == 3
    assert 'artifacts="staging/release-tests/publication-artifacts"' in handoff
    assert '"$artifacts/${{ needs.validate-tag.outputs.wheel_name }}"' in handoff
    assert '"$artifacts/${{ needs.validate-tag.outputs.sdist_name }}"' in handoff
    assert '"$artifacts/${{ needs.validate-tag.outputs.archive_name }}"' in handoff

    helper = (
        REPO_ROOT / ".github" / "scripts" / "test_release_plugin_artifact.py"
    ).read_text(encoding="utf-8")
    assert 'if not key.startswith(("PIP_", "UV_"))' in helper
    assert '"PIP_CONFIG_FILE": os.devnull' in helper
    assert '"PIP_NO_INDEX": "1"' in helper
    assert '"UV_NO_INDEX": "1"' in helper
    assert '"UV_OFFLINE": "1"' in helper
    assert '"--isolated"' in helper
    assert '"--no-cache-dir"' in helper
    assert '"--no-index"' in helper
    assert '"--no-deps"' in helper
    assert '"--no-build-isolation"' in helper
    assert '"uv", "pip"' not in helper
    assert "cwd=test_root" in helper


def test_release_checkout_credentials_are_not_persisted_or_needed_for_refetch() -> None:
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
        encoding="utf-8"
    )
    validate_tag = _job_named(release, "validate-tag")
    build = _job_named(release, "build-release")
    publish = _job_named(release, "publish")
    publish_steps = _steps_by_name(publish)

    assert "permissions:\n  contents: none" in release
    assert "permissions:\n      contents: read" in build
    assert "permissions:\n      actions: read\n      contents: write" in publish
    assert "persist-credentials: false" in _steps_by_name(validate_tag)[
        "Check out repository"
    ]
    assert "persist-credentials: false" in _steps_by_name(build)[
        "Check out repository"
    ]
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
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
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
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
        encoding="utf-8"
    )
    policy = _job_named(release, "release-policy")
    build = _job_named(release, "build-release")
    publish = _job_named(release, "publish")
    publish_steps = _steps_by_name(publish)
    publication = publish_steps[
        "Create, verify, and publish immutable GitHub release"
    ]

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
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
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
        "artifact_digest: ${{ steps.release-handoff.outputs.artifact-digest }}"
        in build
    )
    assert "sha256sum \\" in stage
    assert "sha256sum --check --strict SHA256SUMS" in stage
    assert (
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
        in upload
    )
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
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
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
    assert artifact_probe.count('Authorization: Bearer $GH_TOKEN') == 1
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
    transaction = (
        REPO_ROOT / ".github" / "scripts" / "publish_release.py"
    ).read_text(encoding="utf-8")

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
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
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
    release = (
        REPO_ROOT / ".github" / "workflows" / "publish-release.yml"
    ).read_text(
        encoding="utf-8"
    )
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    fallback = (
        REPO_ROOT / ".github" / "workflows" / "protobuf-fallback.yml"
    ).read_text(encoding="utf-8")

    gate = _job_named(release, "release-gate")
    assert "uses: ./.github/workflows/ci.yml" in gate
    assert "checkout_ref: ${{ needs.validate-tag.outputs.target }}" in gate
    assert "workflow_call:" in ci
    assert "checkout_ref:" in ci
    checkout_action = (
        "uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5"
    )
    exact_ref = "\n          ref: ${{ inputs.checkout_ref || github.sha }}"
    assert ci.count(checkout_action) == ci.count(exact_ref)
    assert fallback.count(checkout_action) == fallback.count(exact_ref)
    assert "checkout_ref: ${{ inputs.checkout_ref || github.sha }}" in ci
