from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DESTINATION = REPO_ROOT / ".github" / ".cache" / "protoc"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and extract a prebuilt protobuf protoc archive.")
    parser.add_argument(
        "--version",
        help="protobuf release version (defaults to PROTOCYTE_PROTOBUF_VERSION in CMakeLists.txt)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DESTINATION,
        help="extraction directory",
    )
    return parser.parse_args()


def load_default_version() -> str:
    cmake_text = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    match = re.search(
        r"set\(\s*PROTOCYTE_PROTOBUF_VERSION\s*\"([^\"]+)\"",
        cmake_text,
        re.MULTILINE,
    )
    if match is None:
        raise RuntimeError("failed to read PROTOCYTE_PROTOBUF_VERSION from CMakeLists.txt")
    return match.group(1)


def download_archive(url: str, archive_path: Path) -> None:
    with urlopen(url) as response, archive_path.open("wb") as output:
        shutil.copyfileobj(response, output)


def _reject_unsafe_archive_member(member_name: str) -> None:
    posix_path = PurePosixPath(member_name)
    windows_path = PureWindowsPath(member_name)
    if posix_path.is_absolute() or windows_path.root or windows_path.drive:
        raise RuntimeError(f"downloaded archive contains unsafe absolute path: {member_name}")
    if ".." in posix_path.parts or ".." in windows_path.parts:
        raise RuntimeError(f"downloaded archive contains unsafe parent traversal path: {member_name}")


def extract_archive_safely(archive: zipfile.ZipFile, destination: Path) -> None:
    for member in archive.infolist():
        _reject_unsafe_archive_member(member.filename)
    archive.extractall(destination)


def main() -> int:
    args = parse_args()
    version = args.version or load_default_version()
    destination = args.dest.resolve()
    archive_name = f"protoc-{version}-linux-x86_64.zip"
    url = f"https://github.com/protocolbuffers/protobuf/releases/download/v{version}/{archive_name}"

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="protocyte-protoc-") as temp_dir:
        archive_path = Path(temp_dir) / archive_name
        download_archive(url, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            extract_archive_safely(archive, destination)

    protoc = destination / "bin" / "protoc"
    descriptor = destination / "include" / "google" / "protobuf" / "descriptor.proto"

    if not protoc.is_file():
        raise RuntimeError(f"downloaded archive is missing protoc at {protoc}")
    if not descriptor.is_file():
        raise RuntimeError(f"downloaded archive is missing descriptor.proto at {descriptor}")

    protoc.chmod(protoc.stat().st_mode | 0o111)
    subprocess.run([str(protoc), "--version"], check=True)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        output_path = Path(github_output)
        with output_path.open("a", encoding="utf-8") as output:
            output.write(f"version={version}\n")
            output.write(f"root={destination.as_posix()}\n")
            output.write(f"protoc={protoc.as_posix()}\n")

    print(f"Installed protoc {version} to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
