"""Exercise a published Python artifact through the checked-in quickstart."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _run(*command: str) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--cmake-version", required=True)
    parser.add_argument("--protoc", type=Path, required=True)
    parser.add_argument("--test-root", type=Path, required=True)
    arguments = parser.parse_args()

    artifact = arguments.artifact.resolve()
    protoc = arguments.protoc.resolve()
    test_root = arguments.test_root.resolve()
    python = test_root / "venv" / "bin" / "python"
    plugin = test_root / "venv" / "bin" / "protoc-gen-protocyte"
    quickstart_build = test_root / "quickstart-build"
    cmake = ("uvx", "--from", f"cmake=={arguments.cmake_version}", "cmake")

    _run("uv", "venv", str(test_root / "venv"), "--python", "3.12")
    # Installing a direct source-distribution path makes uv build its wheel before
    # the same quickstart exercise used for a published wheel.
    _run("uv", "pip", "install", "--python", str(python), str(artifact))
    _run(str(python), "-m", "protocyte", "--help")
    _run(str(python), "-m", "protocyte", "--version")
    _run(str(plugin), "--help")
    _run(str(plugin), "--version")
    _run(
        *cmake,
        "-S",
        "examples/quickstart",
        "-B",
        str(quickstart_build),
        f"-DPROTOC_EXECUTABLE={protoc}",
        f"-DPROTOCYTE_PLUGIN_EXECUTABLE={plugin}",
    )
    _run(*cmake, "--build", str(quickstart_build))
    _run("ctest", "--test-dir", str(quickstart_build), "--output-on-failure")


if __name__ == "__main__":
    main()
