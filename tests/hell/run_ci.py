from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"+ ({cwd}) {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def get_cmake_generator() -> tuple[str, str | None]:
    if os.name == "nt":
        return "Visual Studio 17 2022", "Release"
    return "Unix Makefiles", None


def find_python(roots: list[Path]) -> Path | None:
    suffixes = [
        Path("Scripts/python.exe"),
        Path("bin/python"),
        Path("bin/python3"),
    ]
    for root in roots:
        for suffix in suffixes:
            candidate = root / suffix
            if candidate.is_file():
                return candidate.resolve()
    return None


def get_repo_python(repo_root: Path) -> Path:
    roots: list[Path] = []
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        roots.append(Path(virtual_env))
    roots.append(repo_root / ".venv")

    python_path = find_python(roots)
    if python_path is not None:
        return python_path

    candidates = [
        repo_root / ".venv" / "Scripts" / "python.exe",
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "bin" / "python3",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return Path(sys.executable).resolve()


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required tool '{name}' was not found on PATH")
    return path


def write_hell_config(project_dir: Path, gate_dir: Path) -> None:
    config = {
        "=": [
            {
                "source": gate_dir.resolve().as_uri(),
                "version": "0.1.0",
                "required": ["="],
            }
        ]
    }
    (project_dir / ".hell.json").write_text(f"{json.dumps(config, indent=2)}\n", encoding="utf-8")


def initialize_gate_repo(gate_dir: Path) -> None:
    run(["git", "init"], cwd=gate_dir)
    run(["git", "add", "."], cwd=gate_dir)
    run(
        [
            "git",
            "-c",
            "user.name=Codex",
            "-c",
            "user.email=codex@example.com",
            "commit",
            "-m",
            "fixture gate",
        ],
        cwd=gate_dir,
    )
    run(["git", "tag", "0.1.0"], cwd=gate_dir)


def verify_install_prefix(install_prefix: Path) -> None:
    config_path = install_prefix / "lib" / "cmake" / "protocyte" / "protocyteConfig.cmake"
    if not config_path.is_file():
        raise RuntimeError(f"hell did not install protocyteConfig.cmake at {config_path}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    fixture_root = Path(__file__).resolve().parent
    gate_template = fixture_root / "gate"
    project_template = fixture_root / "project"

    require_tool("git")
    require_tool("cmake")
    require_tool("ctest")
    require_tool("hell")

    hell_env = os.environ.copy()
    python_executable = get_repo_python(repo_root)
    cmake_generator, build_config = get_cmake_generator()
    print(f"Using Python interpreter for CMake: {python_executable}", flush=True)

    with tempfile.TemporaryDirectory(prefix="protocyte-hell-") as temp_dir:
        temp_root = Path(temp_dir)
        gate_dir = temp_root / "gate"
        project_dir = temp_root / "project"
        build_dir = temp_root / "build"

        shutil.copytree(gate_template, gate_dir)
        shutil.copytree(project_template, project_dir)

        initialize_gate_repo(gate_dir)
        write_hell_config(project_dir, gate_dir)

        run(
            [
                "hell",
                "--install",
                "--required",
                "=",
                "--cmakeGenerator",
                cmake_generator,
                "--no-publish",
                "--inject",
                f"PROTOCYTE_SOURCE_DIR={repo_root}",
            ],
            cwd=project_dir,
            env=hell_env,
        )

        install_prefix = project_dir / ".hell" / "install"
        verify_install_prefix(install_prefix)

        run(
            [
                "cmake",
                "-S",
                str(project_dir),
                "-B",
                str(build_dir),
                "-G",
                cmake_generator,
                f"-DCMAKE_PREFIX_PATH={install_prefix}",
                f"-DPython3_EXECUTABLE={python_executable}",
                "-DPROTOCYTE_FETCH_PROTOBUF=ON",
            ],
            cwd=repo_root,
        )
        build_command = ["cmake", "--build", str(build_dir)]
        if build_config is not None:
            build_command.extend(["--config", build_config])
        run(build_command, cwd=repo_root)

        ctest_command = ["ctest", "--test-dir", str(build_dir), "--output-on-failure"]
        if build_config is not None:
            ctest_command.extend(["-C", build_config])
        run(ctest_command, cwd=repo_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
