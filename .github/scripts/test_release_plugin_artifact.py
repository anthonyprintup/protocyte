"""Exercise a published Python artifact through the checked-in quickstart."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


_ALLOWED_ENVIRONMENT = {
    "COMSPEC",
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "TZ",
    "USER",
    "USERPROFILE",
    "WINDIR",
}


def _run(*command: str, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, check=True, cwd=cwd, env=env)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    parser.add_argument("--ctest", type=Path, required=True)
    parser.add_argument("--protoc", type=Path, required=True)
    parser.add_argument("--test-root", type=Path, required=True)
    arguments = parser.parse_args()

    repository_root = Path.cwd().resolve()
    artifact = arguments.artifact.resolve()
    cmake = arguments.cmake.resolve()
    ctest = arguments.ctest.resolve()
    protoc = arguments.protoc.resolve()
    test_root = arguments.test_root.resolve()
    python = test_root / "venv" / "bin" / "python"
    plugin = test_root / "venv" / "bin" / "protoc-gen-protocyte"
    quickstart_build = test_root / "quickstart-build"
    quickstart_source = repository_root / "examples" / "quickstart"
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in _ALLOWED_ENVIRONMENT or key.upper().startswith("LC_")
    }
    environment.update(
        {
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_NO_INDEX": "1",
            "UV_NO_INDEX": "1",
            "UV_OFFLINE": "1",
        }
    )

    # The workflow creates and hash-locks this environment before release
    # artifacts exist. A direct sdist is therefore built only by those locked
    # tools, while a wheel is installed without dependency resolution.
    _run(
        str(python),
        "-I",
        "-m",
        "pip",
        "--isolated",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--no-cache-dir",
        "--no-index",
        "--no-deps",
        "--no-build-isolation",
        str(artifact),
        cwd=test_root,
        env=environment,
    )
    _run(
        str(python),
        "-I",
        "-m",
        "pip",
        "--isolated",
        "check",
        cwd=test_root,
        env=environment,
    )
    _run(
        str(python),
        "-I",
        "-m",
        "protocyte",
        "--help",
        cwd=test_root,
        env=environment,
    )
    _run(
        str(python),
        "-I",
        "-m",
        "protocyte",
        "--version",
        cwd=test_root,
        env=environment,
    )
    _run(str(plugin), "--help", cwd=test_root, env=environment)
    _run(str(plugin), "--version", cwd=test_root, env=environment)
    _run(
        str(cmake),
        "-S",
        str(quickstart_source),
        "-B",
        str(quickstart_build),
        f"-DFETCHCONTENT_SOURCE_DIR_PROTOCYTE={repository_root}",
        "-DPROTOCYTE_FETCH_PROTOBUF=OFF",
        f"-DProtobuf_PROTOC_EXECUTABLE={protoc}",
        f"-DPROTOCYTE_PLUGIN_EXECUTABLE={plugin}",
        cwd=test_root,
        env=environment,
    )
    _run(
        str(cmake),
        "--build",
        str(quickstart_build),
        cwd=test_root,
        env=environment,
    )
    _run(
        str(ctest),
        "--test-dir",
        str(quickstart_build),
        "--output-on-failure",
        cwd=test_root,
        env=environment,
    )


if __name__ == "__main__":
    main()
