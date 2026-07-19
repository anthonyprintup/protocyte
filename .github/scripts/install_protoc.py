from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple
from urllib.request import urlopen


_SCRIPTS_DIRECTORY = Path(__file__).resolve().parent
if str(_SCRIPTS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIRECTORY))

from owned_transactions import (  # noqa: E402
    OwnedSibling,
    claim_dead_owner_for_path,
    create_owned_sibling,
    locked_destination,
    recover_owned_siblings,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DESTINATION = REPO_ROOT / ".github" / ".cache" / "protoc"
DOWNLOAD_TIMEOUT_SECONDS = 30.0
DOWNLOAD_CHUNK_BYTES = 64 * 1024
MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 4_096
MAX_ARCHIVE_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
VERSION_MARKER = ".protocyte-protobuf-version"


class ProtocAsset(NamedTuple):
    archive_suffix: str
    checksum_variable: str
    executable_name: str


_MACOS_UNIVERSAL_ASSET = ProtocAsset(
    archive_suffix="osx-universal_binary",
    checksum_variable="PROTOCYTE_PROTOBUF_MACOS_UNIVERSAL_SHA256",
    executable_name="protoc",
)


_SUPPORTED_ASSETS = {
    ("linux", "x86_64"): ProtocAsset(
        archive_suffix="linux-x86_64",
        checksum_variable="PROTOCYTE_PROTOBUF_LINUX_X86_64_SHA256",
        executable_name="protoc",
    ),
    ("windows", "x86_64"): ProtocAsset(
        archive_suffix="win64",
        checksum_variable="PROTOCYTE_PROTOBUF_WINDOWS_X86_64_SHA256",
        executable_name="protoc.exe",
    ),
    ("darwin", "x86_64"): _MACOS_UNIVERSAL_ASSET,
    ("darwin", "arm64"): _MACOS_UNIVERSAL_ASSET,
}


def resolve_platform_asset(
    system: str | None = None,
    machine: str | None = None,
) -> ProtocAsset:
    normalized_system = (system or platform.system()).casefold()
    normalized_machine = (machine or platform.machine()).casefold()
    if normalized_machine in {"amd64", "x86_64"}:
        normalized_machine = "x86_64"
    elif normalized_machine in {"aarch64", "arm64"}:
        normalized_machine = "arm64"

    try:
        return _SUPPORTED_ASSETS[(normalized_system, normalized_machine)]
    except KeyError as error:
        raise RuntimeError(
            "unsupported protoc prebuilt platform: "
            f"{system or platform.system()} {machine or platform.machine()}; "
            "supported platforms are Linux x86-64, Windows x86-64, and "
            "macOS x86-64 or arm64"
        ) from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and extract a prebuilt protobuf protoc archive."
    )
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
    parser.add_argument(
        "--sha256",
        help="expected archive SHA-256 (required when overriding the configured version)",
    )
    return parser.parse_args()


def _load_cmake_string(variable: str) -> str:
    cmake_text = (REPO_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    match = re.search(
        rf"set\(\s*{re.escape(variable)}\s*\"([^\"]+)\"",
        cmake_text,
        re.MULTILINE,
    )
    if match is None:
        raise RuntimeError(f"failed to read {variable} from CMakeLists.txt")
    return match.group(1)


def load_default_version() -> str:
    return _load_cmake_string("PROTOCYTE_PROTOBUF_VERSION")


def load_default_sha256(asset: ProtocAsset) -> str:
    return _normalize_sha256(_load_cmake_string(asset.checksum_variable))


def _normalize_sha256(value: str) -> str:
    normalized = value.removeprefix("sha256:").lower()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise RuntimeError(
            "expected SHA-256 must contain exactly 64 hexadecimal characters"
        )
    return normalized


def resolve_release(
    version: str | None,
    sha256: str | None,
    asset: ProtocAsset,
) -> tuple[str, str]:
    default_version = load_default_version()
    resolved_version = version or default_version
    if sha256 is not None:
        return resolved_version, _normalize_sha256(sha256)
    if resolved_version != default_version:
        raise RuntimeError(
            "--sha256 is required when --version overrides the configured release"
        )
    return resolved_version, load_default_sha256(asset)


def _content_length(response: object) -> int | None:
    headers = getattr(response, "headers", None)
    value = headers.get("Content-Length") if headers is not None else None
    if value is None:
        return None
    try:
        content_length = int(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "download response contains an invalid Content-Length"
        ) from error
    if content_length < 0:
        raise RuntimeError("download response contains a negative Content-Length")
    return content_length


def download_archive(
    url: str,
    archive_path: Path,
    *,
    timeout: float = DOWNLOAD_TIMEOUT_SECONDS,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> str:
    if timeout <= 0:
        raise ValueError("download timeout must be positive")
    if max_bytes <= 0:
        raise ValueError("maximum download size must be positive")

    deadline = time.monotonic() + timeout
    digest = hashlib.sha256()
    events: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=2)
    cancelled = threading.Event()
    response_lock = threading.Lock()
    active_response: list[object | None] = [None]

    def publish(event: tuple[str, object]) -> bool:
        while not cancelled.is_set():
            try:
                events.put(event, timeout=0.1)
            except queue.Full:
                continue
            return True
        return False

    def download_worker() -> None:
        completion: tuple[str, object] = ("done", None)
        try:
            with urlopen(url, timeout=timeout) as response:
                with response_lock:
                    active_response[0] = response

                content_length = _content_length(response)
                if content_length is not None and content_length > max_bytes:
                    raise RuntimeError(
                        f"download is too large: Content-Length {content_length} "
                        f"exceeds {max_bytes} bytes"
                    )

                bytes_received = 0
                while not cancelled.is_set():
                    chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    bytes_received += len(chunk)
                    if bytes_received > max_bytes:
                        raise RuntimeError(
                            f"download exceeds the {max_bytes}-byte limit"
                        )
                    if not publish(("chunk", chunk)):
                        return
        except Exception as error:
            completion = ("error", error)
        finally:
            with response_lock:
                active_response[0] = None

        publish(completion)

    worker = threading.Thread(
        target=download_worker,
        name="protocyte-protoc-download",
        daemon=True,
    )
    worker.start()

    def cancel_download() -> None:
        cancelled.set()
        with response_lock:
            response = active_response[0]
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    try:
        with archive_path.open("wb") as output:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError(
                        f"download exceeded the {timeout:g}-second wall-clock deadline"
                    )
                try:
                    event, payload = events.get(timeout=remaining)
                except queue.Empty as error:
                    raise RuntimeError(
                        f"download exceeded the {timeout:g}-second wall-clock deadline"
                    ) from error

                if event == "chunk":
                    assert isinstance(payload, bytes)
                    chunk = payload
                    digest.update(chunk)
                    output.write(chunk)
                elif event == "error":
                    assert isinstance(payload, Exception)
                    raise payload
                else:
                    assert event == "done"
                    break
    except Exception:
        cancel_download()
        archive_path.unlink(missing_ok=True)
        raise
    worker.join()
    return digest.hexdigest()


def verify_archive_sha256(
    actual_sha256: str, expected_sha256: str, archive_name: str
) -> None:
    actual = _normalize_sha256(actual_sha256)
    expected = _normalize_sha256(expected_sha256)
    if not hmac.compare_digest(actual, expected):
        raise RuntimeError(
            f"SHA-256 mismatch for {archive_name}: expected {expected}, received {actual}"
        )


def _reject_unsafe_archive_member(member_name: str) -> None:
    posix_path = PurePosixPath(member_name)
    windows_path = PureWindowsPath(member_name)
    if posix_path.is_absolute() or windows_path.root or windows_path.drive:
        raise RuntimeError(
            f"downloaded archive contains unsafe absolute path: {member_name}"
        )
    if ".." in posix_path.parts or ".." in windows_path.parts:
        raise RuntimeError(
            f"downloaded archive contains unsafe parent traversal path: {member_name}"
        )


def extract_archive_safely(
    archive: zipfile.ZipFile,
    destination: Path,
    *,
    max_members: int = MAX_ARCHIVE_MEMBERS,
    max_member_bytes: int = MAX_ARCHIVE_MEMBER_BYTES,
    max_uncompressed_bytes: int = MAX_ARCHIVE_UNCOMPRESSED_BYTES,
) -> None:
    members = archive.infolist()
    if len(members) > max_members:
        raise RuntimeError(
            f"downloaded archive contains more than {max_members} members"
        )

    uncompressed_bytes = 0
    for member in members:
        _reject_unsafe_archive_member(member.filename)
        if member.file_size > max_member_bytes:
            raise RuntimeError(
                f"downloaded archive member exceeds the {max_member_bytes}-byte limit: "
                f"{member.filename}"
            )
        uncompressed_bytes += member.file_size
        if uncompressed_bytes > max_uncompressed_bytes:
            raise RuntimeError(
                "downloaded archive exceeds the "
                f"{max_uncompressed_bytes}-byte uncompressed-size limit"
            )
    archive.extractall(destination)


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _remove_path(path: Path) -> None:
    if not _path_exists(path):
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def _installation_rollback_path(destination: Path) -> Path:
    return destination.with_name(f".{destination.name}.protocyte-rollback")


def _install_swap_phase(_phase: str) -> None:
    """Test seam for process interruptions between atomic filesystem operations."""


def _create_install_transaction(destination: Path, purpose: str) -> OwnedSibling:
    return create_owned_sibling(destination, purpose)


def _cleanup_install_transaction(transaction_owner: OwnedSibling) -> None:
    _install_swap_phase("before_cleanup")
    rollback = _installation_rollback_path(transaction_owner.destination)
    if _path_exists(rollback):
        transaction_owner.close(remove_marker=False)
    else:
        transaction_owner.cleanup(_remove_path)
    _install_swap_phase("after_cleanup")


def _unowned_installation_rollback_error(rollback: Path) -> RuntimeError:
    return RuntimeError(
        "refusing to recover an unowned or replaced protoc installation rollback at "
        f"{rollback}. The live installation was left unchanged. Inspect both paths, "
        "then move or remove the rollback manually before retrying."
    )


def _restore_installation_rollback(
    destination: Path,
    rollback: Path,
    rollback_owner: OwnedSibling | None = None,
) -> None:
    claimed_owner = rollback_owner is None
    if rollback_owner is None:
        rollback_owner = claim_dead_owner_for_path(
            destination,
            ("transaction",),
            "rollback",
            rollback,
        )
    if rollback_owner is None or not rollback_owner.owns_path("rollback", rollback):
        raise _unowned_installation_rollback_error(rollback)

    try:
        recovery_owner = _create_install_transaction(destination, "recovery")
        recovery = recovery_owner.path
        displaced = recovery / "interrupted-install"
        try:
            if _path_exists(destination):
                destination.replace(displaced)
            _install_swap_phase("recovery_after_displace")
            rollback.replace(destination)
            _install_swap_phase("recovery_after_restore")
        finally:
            try:
                recovery_owner.cleanup(_remove_path)
            except OSError:
                pass
    finally:
        if claimed_owner:
            rollback_owner.close(remove_marker=False)


def _recover_interrupted_install(destination: Path) -> None:
    rollback = _installation_rollback_path(destination)
    if _path_exists(rollback):
        _restore_installation_rollback(destination, rollback)


def _recover_interrupted_install_state(destination: Path) -> None:
    # Restore the authoritative fixed rollback before discarding dead UUID
    # transaction and recovery directories left by terminated processes.
    _recover_interrupted_install(destination)
    recover_owned_siblings(
        destination,
        ("transaction", "recovery"),
        _remove_path,
    )


def replace_destination(
    staging: Path,
    destination: Path,
    transaction_owner: OwnedSibling | None = None,
) -> None:
    _recover_interrupted_install(destination)
    rollback = _installation_rollback_path(destination)
    previous = staging.parent / "previous-install"
    had_previous = _path_exists(destination)
    local_owner = False

    try:
        _install_swap_phase("before_backup")
        if had_previous:
            if transaction_owner is None:
                transaction_owner = _create_install_transaction(
                    destination, "transaction"
                )
                local_owner = True
            transaction_owner.bind_path(
                "rollback",
                rollback,
                identity_source=destination,
            )
            destination.replace(rollback)
        _install_swap_phase("after_backup")
        _install_swap_phase("before_promote")
        staging.replace(destination)
        _install_swap_phase("after_promote")
        _install_swap_phase("before_commit")
        if had_previous:
            rollback.replace(previous)
        _install_swap_phase("after_commit")
    except BaseException:
        if had_previous:
            if not _path_exists(rollback) and _path_exists(previous):
                previous.replace(rollback)
            if _path_exists(rollback):
                _restore_installation_rollback(
                    destination,
                    rollback,
                    transaction_owner,
                )
        elif _path_exists(destination) and not _path_exists(staging):
            try:
                destination.replace(staging)
            except OSError:
                pass
        raise
    finally:
        if local_owner:
            _cleanup_install_transaction(transaction_owner)

    if had_previous:
        _remove_path(previous)


def main() -> int:
    args = parse_args()
    asset = resolve_platform_asset()
    version, expected_sha256 = resolve_release(args.version, args.sha256, asset)
    destination = args.dest.resolve()
    archive_name = f"protoc-{version}-{asset.archive_suffix}.zip"
    url = f"https://github.com/protocolbuffers/protobuf/releases/download/v{version}/{archive_name}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    with locked_destination(destination):
        _recover_interrupted_install_state(destination)
        transaction_owner = _create_install_transaction(destination, "transaction")
        transaction = transaction_owner.path
        try:
            archive_path = transaction / archive_name
            staging = transaction / "install"
            actual_sha256 = download_archive(url, archive_path)
            verify_archive_sha256(actual_sha256, expected_sha256, archive_name)
            with zipfile.ZipFile(archive_path) as archive:
                extract_archive_safely(archive, staging)

            staged_protoc = staging / "bin" / asset.executable_name
            staged_descriptor = (
                staging / "include" / "google" / "protobuf" / "descriptor.proto"
            )

            if not staged_protoc.is_file():
                raise RuntimeError(
                    f"downloaded archive is missing protoc at {staged_protoc}"
                )
            if not staged_descriptor.is_file():
                raise RuntimeError(
                    "downloaded archive is missing descriptor.proto at "
                    f"{staged_descriptor}"
                )

            (staging / VERSION_MARKER).write_text(f"{version}\n", encoding="utf-8")
            staged_protoc.chmod(staged_protoc.stat().st_mode | 0o111)
            subprocess.run([str(staged_protoc), "--version"], check=True)
            replace_destination(staging, destination, transaction_owner)
        finally:
            _cleanup_install_transaction(transaction_owner)

    protoc = destination / "bin" / asset.executable_name

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        output_path = Path(github_output)
        with output_path.open("a", encoding="utf-8") as output:
            output.write(f"version={version}\n")
            output.write(f"root={destination.as_posix()}\n")
            output.write(f"protoc={protoc.as_posix()}\n")
            output.write(f"include={(destination / 'include').as_posix()}\n")

    print(f"Installed protoc {version} to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
