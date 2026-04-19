from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import google.protobuf

GATE_URI_ENV = "PROTOCYTE_HELL_GATE_URI"


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"+ ({cwd}) {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def get_cmake_generator() -> tuple[str, str | None]:
    if os.name == "nt":
        return "Visual Studio 17 2022", "Release"
    return "Unix Makefiles", None


def prepend_env_path(env: dict[str, str], key: str, value: Path) -> None:
    current = env.get(key)
    if current:
        env[key] = f"{value}{os.pathsep}{current}"
    else:
        env[key] = str(value)


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
    if sys.prefix != sys.base_prefix:
        roots.append(Path(sys.prefix))
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


def get_python_package_root() -> Path:
    return Path(google.protobuf.__file__).resolve().parents[2]


def get_hell_command() -> str:
    candidates: list[str | Path] = ["hell"]
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        candidates = ["hell.cmd", "hell"]
        if appdata:
            candidates.insert(0, Path(appdata) / "npm" / "hell.cmd")
    for candidate in candidates:
        path = shutil.which(candidate)
        if path is not None:
            return path
        if isinstance(candidate, Path) and candidate.is_file():
            return str(candidate.resolve())
    raise RuntimeError("required tool 'hell' was not found on PATH")


def get_node_executable() -> Path:
    path = shutil.which("node")
    if path is not None:
        return Path(path).resolve()

    if os.name == "nt":
        candidates: list[Path] = []
        for env_name in ("NVM_SYMLINK", "ProgramFiles", "ProgramFiles(x86)"):
            root = os.environ.get(env_name)
            if root:
                candidates.append(Path(root) / "nodejs" / "node.exe")
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidates.append(Path(local_appdata) / "Programs" / "nodejs" / "node.exe")
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()

    raise RuntimeError("required tool 'node' was not found on PATH")


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required tool '{name}' was not found on PATH")
    return path


def get_rewriter_script(fixture_root: Path) -> Path:
    rewriter_script = fixture_root / "rewrite_gate_source.js"
    if not rewriter_script.is_file():
        raise RuntimeError(f"required rewriter script was not found at {rewriter_script}")
    return rewriter_script.resolve()


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
    rewriter_script = get_rewriter_script(fixture_root)

    require_tool("git")
    require_tool("cmake")
    require_tool("ctest")
    hell_command = get_hell_command()
    node_executable = get_node_executable()

    hell_env = os.environ.copy()
    python_executable = get_repo_python(repo_root)
    python_package_root = get_python_package_root()
    cmake_generator, build_config = get_cmake_generator()
    prepend_env_path(hell_env, "PATH", node_executable.parent)
    print(f"Using hell config rewriter: {rewriter_script}", flush=True)
    print(f"Using Node executable for hell: {node_executable}", flush=True)
    print(f"Using Python interpreter for CMake: {python_executable}", flush=True)
    print(f"Using Python package root for CMake: {python_package_root}", flush=True)

    build_env = os.environ.copy()
    prepend_env_path(build_env, "PYTHONPATH", python_package_root)

    with tempfile.TemporaryDirectory(prefix="protocyte-hell-") as temp_dir:
        temp_root = Path(temp_dir)
        gate_dir = temp_root / "gate"
        project_dir = temp_root / "project"
        build_dir = temp_root / "build"

        shutil.copytree(gate_template, gate_dir)
        shutil.copytree(project_template, project_dir)

        initialize_gate_repo(gate_dir)
        hell_env[GATE_URI_ENV] = gate_dir.resolve().as_uri()

        run(
            [
                hell_command,
                "--install",
                "--required",
                "=",
                "--cmakeGenerator",
                cmake_generator,
                "--no-publish",
                "--rewriteConfig",
                str(rewriter_script),
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
            env=build_env,
        )
        build_command = ["cmake", "--build", str(build_dir)]
        if build_config is not None:
            build_command.extend(["--config", build_config])
        run(build_command, cwd=repo_root, env=build_env)

        ctest_command = ["ctest", "--test-dir", str(build_dir), "--output-on-failure"]
        if build_config is not None:
            ctest_command.extend(["-C", build_config])
        run(ctest_command, cwd=repo_root, env=build_env)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
