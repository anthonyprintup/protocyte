from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.cmake_integration

_test_cmake_path = Path(__file__).with_name("test_cmake.py")
_test_cmake_spec = importlib.util.spec_from_file_location(
    "protocyte_test_cmake_helpers", _test_cmake_path
)
assert _test_cmake_spec is not None and _test_cmake_spec.loader is not None
_test_cmake = importlib.util.module_from_spec(_test_cmake_spec)
sys.modules[_test_cmake_spec.name] = _test_cmake
_test_cmake_spec.loader.exec_module(_test_cmake)
_build_out_dir_owner_project = _test_cmake._build_out_dir_owner_project
_configure_out_dir_owner_project = _test_cmake._configure_out_dir_owner_project
_write_out_dir_owner_project = _test_cmake._write_out_dir_owner_project


def _configure(source: Path, build: Path) -> subprocess.CompletedProcess[str]:
    return _configure_out_dir_owner_project(source, build, "-G", "Ninja")


def test_coordinator_recovers_default_output_after_build_tree_recreation(
    tmp_path: Path,
) -> None:
    source = tmp_path / "project"
    build = tmp_path / "build"
    output = build / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(source, output, output_lock_root=locks)
    assert _configure(source, build).returncode == 0
    assert _build_out_dir_owner_project(build).returncode == 0

    shutil.rmtree(build)
    recreated = _configure(source, build)
    rebuilt = _build_out_dir_owner_project(build)

    assert recreated.returncode == 0, recreated.stdout + recreated.stderr
    assert rebuilt.returncode == 0, rebuilt.stdout + rebuilt.stderr
    assert (output / "demo_0.protocyte.hpp").is_file()
    assert (output / "demo_0.protocyte.cpp").is_file()


@pytest.mark.skipif(os.name != "nt", reason="requires a case-insensitive filesystem")
def test_coordinator_case_only_transfer_keeps_published_outputs(tmp_path: Path) -> None:
    source = tmp_path / "project"
    build = tmp_path / "build"
    output = tmp_path / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(
        source,
        output,
        proto_names=("API/foo.proto", "old/bar.proto"),
        output_lock_root=locks,
    )
    assert _configure(source, build).returncode == 0
    assert _build_out_dir_owner_project(build, "generated_0").returncode == 0
    assert _build_out_dir_owner_project(build, "generated_1").returncode == 0

    _write_out_dir_owner_project(
        source,
        output,
        proto_names=("new/demo.proto", "api/foo.proto"),
        output_lock_root=locks,
    )
    assert _configure(source, build).returncode == 0
    transferred = _build_out_dir_owner_project(build, "generated_1")

    assert transferred.returncode == 0, transferred.stdout + transferred.stderr
    assert (output / "api/foo.protocyte.hpp").is_file()
    assert (output / "api/foo.protocyte.cpp").is_file()
    assert not (output / "old/bar.protocyte.hpp").exists()
    assert not (output / "old/bar.protocyte.cpp").exists()


def test_coordinator_recovers_real_build_after_publication_crash(
    tmp_path: Path,
) -> None:
    source = tmp_path / "project"
    build = tmp_path / "build"
    output = tmp_path / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(source, output, output_lock_root=locks)
    configured = _configure(source, build)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    environment = os.environ.copy()
    environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = "after-output-1"

    crashed = subprocess.run(
        ["cmake", "--build", str(build), "--target", "generated_0"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert crashed.returncode != 0
    state_roots = list((locks / "roots").iterdir())
    assert len(state_roots) == 1
    transaction_directories = list((state_roots[0] / "transactions").iterdir())
    assert len(transaction_directories) == 1
    shutil.rmtree(next(tmp_path.glob(".protocyte-generation-staging-*")))

    recovered = _build_out_dir_owner_project(build)

    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert (output / "demo_0.protocyte.hpp").is_file()
    assert (output / "demo_0.protocyte.cpp").is_file()
    snapshot = json.loads((state_roots[0] / "snapshot.json").read_text())
    assert set(snapshot["entries"]) == {
        "demo_0.protocyte.cpp",
        "demo_0.protocyte.hpp",
    }
    assert not list((state_roots[0] / "transactions").iterdir())


def test_coordinator_rejects_a_second_build_before_generation(tmp_path: Path) -> None:
    source = tmp_path / "project"
    output = tmp_path / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(source, output, output_lock_root=locks)
    first = _configure(source, tmp_path / "first-build")
    second = _configure(source, tmp_path / "second-build")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode != 0
    diagnostic = " ".join((second.stdout + second.stderr).split())
    assert "different CMake build tree" in diagnostic


def test_generation_inventory_is_literal_under_glob_metacharacter_build_path(
    tmp_path: Path,
) -> None:
    source = tmp_path / "project"
    build = tmp_path / "build[1]"
    output = build / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(source, output, output_lock_root=locks)

    configured = _configure(source, build)
    generated = _build_out_dir_owner_project(build)

    assert configured.returncode == 0, configured.stdout + configured.stderr
    assert generated.returncode == 0, generated.stdout + generated.stderr
    assert (output / "demo_0.protocyte.hpp").is_file()

    _write_out_dir_owner_project(
        source,
        output,
        proto_names=(),
        output_lock_root=locks,
    )
    retired = _configure(source, build)

    assert retired.returncode == 0, retired.stdout + retired.stderr
    assert not list(output.rglob("*.protocyte.*"))


def test_build_root_is_physical_when_configured_through_a_directory_link(
    tmp_path: Path,
) -> None:
    source = tmp_path / "project"
    real_build = tmp_path / "real-build"
    build_alias = tmp_path / "build-alias"
    output = tmp_path / "generated"
    locks = tmp_path / "locks"
    real_build.mkdir()
    try:
        build_alias.symlink_to(real_build, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"directory links are unavailable: {error}")
        junction = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(build_alias), str(real_build)],
            check=False,
            capture_output=True,
            text=True,
        )
        if junction.returncode != 0:
            pytest.skip(f"directory links are unavailable: {junction.stderr}")
    _write_out_dir_owner_project(source, output, output_lock_root=locks)

    configured = _configure(source, build_alias)
    generated = _build_out_dir_owner_project(build_alias)

    assert configured.returncode == 0, configured.stdout + configured.stderr
    assert generated.returncode == 0, generated.stdout + generated.stderr
    plan = next(
        (real_build / "CMakeFiles" / "protocyte-output-plans").glob("*.plan")
    )
    encoded_build_root = plan.read_text(encoding="ascii").splitlines()[2].split("=", 1)[1]
    assert Path(bytes.fromhex(encoded_build_root).decode("utf-8")) == real_build.resolve()


def test_public_reset_requires_token_and_releases_claim(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = tmp_path / "project"
    build = tmp_path / "build"
    output = tmp_path / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(source, output, output_lock_root=locks)
    assert _configure(source, build).returncode == 0
    assert _build_out_dir_owner_project(build).returncode == 0
    token_files = list(
        (build / "CMakeFiles" / "protocyte-output-plans").glob("*.claim-token")
    )
    assert len(token_files) == 1
    token = token_files[0].read_text(encoding="utf-8").strip()
    reset_source = tmp_path / "reset-project"
    reset_source.mkdir()
    (reset_source / "CMakeLists.txt").write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                "project(reset_claim LANGUAGES NONE)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                f'set(PROTOCYTE_OUTPUT_LOCK_ROOT "{locks.as_posix()}")',
                "protocyte_reset_output_directory(",
                f'    OUT_DIR "{output.as_posix()}"',
                f'    EXPECTED_CLAIM "{token}"',
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )

    reset = subprocess.run(
        ["cmake", "-S", str(reset_source), "-B", str(tmp_path / "reset-build")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset.returncode == 0, reset.stdout + reset.stderr
    assert not list(output.rglob("*.protocyte.*"))
    transferred = _configure(source, tmp_path / "replacement-build")
    assert transferred.returncode == 0, transferred.stdout + transferred.stderr
    replacement_build = tmp_path / "replacement-build"
    replacement = _build_out_dir_owner_project(replacement_build)
    assert replacement.returncode == 0, replacement.stdout + replacement.stderr

    stale = _build_out_dir_owner_project(build)

    assert stale.returncode != 0
    diagnostic = " ".join((stale.stdout + stale.stderr).split())
    assert "different CMake build tree" in diagnostic


def test_generation_timeout_publishes_no_snapshot_entries_and_retry_succeeds(
    tmp_path: Path,
) -> None:
    source = tmp_path / "project"
    build = tmp_path / "build"
    output = tmp_path / "generated"
    locks = tmp_path / "locks"
    _write_out_dir_owner_project(source, output, output_lock_root=locks)
    configured = _configure_out_dir_owner_project(
        source,
        build,
        "-G",
        "Ninja",
        "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=0.5",
    )
    assert configured.returncode == 0, configured.stdout + configured.stderr
    fake_protoc = source / "fake-protoc.py"
    original = fake_protoc.read_text(encoding="utf-8")
    fake_protoc.write_text(
        original.replace("import sys\n", "import sys\nimport time\ntime.sleep(60)\n"),
        encoding="utf-8",
    )

    timed_out = _build_out_dir_owner_project(build)

    assert timed_out.returncode != 0
    diagnostic = " ".join((timed_out.stdout + timed_out.stderr).split())
    assert "generation timed out before publication" in diagnostic
    state = next((locks / "roots").iterdir())
    snapshot = json.loads((state / "snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["entries"] == {}
    assert not list(output.rglob("*.protocyte.*"))
    fake_protoc.write_text(original, encoding="utf-8")

    retried = _build_out_dir_owner_project(build)

    assert retried.returncode == 0, retried.stdout + retried.stderr
    assert (output / "demo_0.protocyte.hpp").is_file()
