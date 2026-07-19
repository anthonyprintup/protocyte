import hashlib
import importlib.util
import io
import subprocess
import threading
import zipfile
from pathlib import Path

import pytest


def _load_install_protoc_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "scripts"
        / "install_protoc.py"
    )
    spec = importlib.util.spec_from_file_location("install_protoc", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install_protoc = _load_install_protoc_module()


def _write_archive(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, "content")


class _Response(io.BytesIO):
    def __init__(self, content: bytes, content_length: str | None = None) -> None:
        super().__init__(content)
        self.headers = (
            {} if content_length is None else {"Content-Length": content_length}
        )


class _SlowResponse(_Response):
    def __init__(
        self,
        content: bytes,
        read_started: threading.Event,
        release_read: threading.Event,
    ) -> None:
        super().__init__(content)
        self.read_started = read_started
        self.release_read = release_read

    def read(self, size: int = -1) -> bytes:
        self.read_started.set()
        self.release_read.wait(timeout=1.0)
        return super().read(size)


def test_extract_archive_safely_preserves_normal_archive_layout(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(
        archive_path,
        [
            "bin/protoc",
            "include/google/protobuf/descriptor.proto",
        ],
    )

    with zipfile.ZipFile(archive_path) as archive:
        install_protoc.extract_archive_safely(archive, destination)

    assert (destination / "bin" / "protoc").read_text(encoding="utf-8") == "content"
    assert (
        destination / "include" / "google" / "protobuf" / "descriptor.proto"
    ).is_file()


def test_download_archive_hashes_content_and_applies_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = b"trusted archive bytes"
    observed: dict[str, object] = {}

    def fake_urlopen(url: str, *, timeout: float) -> _Response:
        observed.update(url=url, timeout=timeout)
        return _Response(content, str(len(content)))

    monkeypatch.setattr(install_protoc, "urlopen", fake_urlopen)
    archive_path = tmp_path / "protoc.zip"

    actual_sha256 = install_protoc.download_archive(
        "https://example.invalid/protoc.zip",
        archive_path,
        timeout=7.5,
    )

    assert observed == {"url": "https://example.invalid/protoc.zip", "timeout": 7.5}
    assert archive_path.read_bytes() == content
    assert actual_sha256 == hashlib.sha256(content).hexdigest()


def test_download_archive_enforces_wall_clock_deadline_against_slow_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_started = threading.Event()
    release_read = threading.Event()
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _SlowResponse(
            b"slow bytes",
            read_started,
            release_read,
        ),
    )
    archive_path = tmp_path / "protoc.zip"

    try:
        with pytest.raises(RuntimeError, match="wall-clock deadline"):
            install_protoc.download_archive(
                "https://example.invalid/protoc.zip",
                archive_path,
                timeout=0.02,
            )
    finally:
        release_read.set()

    assert read_started.is_set()
    assert not archive_path.exists()


@pytest.mark.parametrize("declared_size", ["not-a-number", "9"])
def test_download_archive_rejects_invalid_or_oversized_content_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declared_size: str,
) -> None:
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _Response(b"content", declared_size),
    )
    archive_path = tmp_path / "protoc.zip"

    with pytest.raises(RuntimeError, match="Content-Length|too large"):
        install_protoc.download_archive(
            "https://example.invalid/protoc.zip", archive_path, max_bytes=8
        )

    assert not archive_path.exists()


def test_download_archive_rejects_stream_that_exceeds_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        install_protoc,
        "urlopen",
        lambda _url, *, timeout: _Response(b"ninebytes"),
    )
    archive_path = tmp_path / "protoc.zip"

    with pytest.raises(RuntimeError, match="exceeds"):
        install_protoc.download_archive(
            "https://example.invalid/protoc.zip", archive_path, max_bytes=8
        )

    assert not archive_path.exists()


def test_verify_archive_sha256_rejects_mismatch() -> None:
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        install_protoc.verify_archive_sha256("0" * 64, "1" * 64, "protoc.zip")


def test_main_rejects_digest_mismatch_before_extraction_or_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )
    monkeypatch.setattr(
        install_protoc,
        "download_archive",
        lambda _url, _archive_path: "0" * 64,
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unverified archive was extracted or executed")

    monkeypatch.setattr(install_protoc.zipfile, "ZipFile", forbidden)
    monkeypatch.setattr(install_protoc.subprocess, "run", forbidden)

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        install_protoc.main()

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_main_preserves_existing_destination_when_staged_protoc_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = install_protoc.resolve_platform_asset()
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")

    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )

    def fake_download(_url: str, archive_path: Path) -> str:
        _write_archive(
            archive_path,
            [
                f"bin/{asset.executable_name}",
                "include/google/protobuf/descriptor.proto",
            ],
        )
        return install_protoc.load_default_sha256(asset)

    monkeypatch.setattr(install_protoc, "download_archive", fake_download)
    monkeypatch.setattr(
        install_protoc.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, "protoc --version")
        ),
    )

    with pytest.raises(subprocess.CalledProcessError):
        install_protoc.main()

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_replace_destination_installs_staging_and_removes_previous(
    tmp_path: Path,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    (staging / "new").write_text("new", encoding="utf-8")
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "old").write_text("old", encoding="utf-8")

    install_protoc.replace_destination(staging, destination)

    assert (destination / "new").read_text(encoding="utf-8") == "new"
    assert not (destination / "old").exists()
    assert not (transaction / "previous-install").exists()


def test_replace_destination_restores_previous_if_staging_rename_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = tmp_path / "transaction"
    transaction.mkdir()
    staging = transaction / "install"
    staging.mkdir()
    destination = tmp_path / "protoc"
    destination.mkdir()
    marker = destination / "known-good"
    marker.write_text("preserve", encoding="utf-8")
    original_replace = Path.replace

    def fail_staging_replace(source: Path, target: Path) -> Path:
        if source == staging:
            raise OSError("injected staging rename failure")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_staging_replace)

    with pytest.raises(OSError, match="injected staging rename failure"):
        install_protoc.replace_destination(staging, destination)

    assert marker.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("promoted_new_install", [False, True])
def test_next_install_recovers_an_interrupted_swap(
    tmp_path: Path,
    promoted_new_install: bool,
) -> None:
    destination = tmp_path / "protoc"
    destination.mkdir()
    (destination / "known-good").write_text("preserve", encoding="utf-8")
    rollback = install_protoc._installation_rollback_path(destination)
    destination.replace(rollback)
    if promoted_new_install:
        destination.mkdir()
        (destination / "partial").write_text("discard", encoding="utf-8")

    install_protoc._recover_interrupted_install(destination)

    assert (destination / "known-good").read_text(encoding="utf-8") == "preserve"
    assert not (destination / "partial").exists()
    assert not rollback.exists()


def test_resolve_release_requires_digest_for_version_override() -> None:
    asset = install_protoc.resolve_platform_asset("Linux", "x86_64")
    with pytest.raises(RuntimeError, match="--sha256 is required"):
        install_protoc.resolve_release("999.0", None, asset)


@pytest.mark.parametrize(
    ("system", "machine", "archive_suffix", "checksum_variable", "executable_name"),
    [
        (
            "Linux",
            "AMD64",
            "linux-x86_64",
            "PROTOCYTE_PROTOBUF_LINUX_X86_64_SHA256",
            "protoc",
        ),
        (
            "Windows",
            "x86_64",
            "win64",
            "PROTOCYTE_PROTOBUF_WINDOWS_X86_64_SHA256",
            "protoc.exe",
        ),
    ],
)
def test_resolve_platform_asset_selects_supported_x86_64_archive(
    system: str,
    machine: str,
    archive_suffix: str,
    checksum_variable: str,
    executable_name: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)

    assert asset == install_protoc.ProtocAsset(
        archive_suffix=archive_suffix,
        checksum_variable=checksum_variable,
        executable_name=executable_name,
    )


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Darwin", "arm64"),
        ("Linux", "aarch64"),
        ("Windows", "x86"),
    ],
)
def test_resolve_platform_asset_rejects_unsupported_host(
    system: str,
    machine: str,
) -> None:
    with pytest.raises(RuntimeError, match="unsupported protoc prebuilt platform"):
        install_protoc.resolve_platform_asset(system, machine)


@pytest.mark.parametrize(
    ("system", "machine", "expected_sha256"),
    [
        (
            "Linux",
            "x86_64",
            "af27ea66cd26938fe48587804ca7d4817457a08350021a1c6e23a27ccc8c6904",
        ),
        (
            "Windows",
            "AMD64",
            "6d7ebdc75e9c1f0026d4fb28f17ef1d0aae77d36744d83a9e052d79ba493724f",
        ),
    ],
)
def test_configured_release_digests_match_upstream_assets(
    system: str,
    machine: str,
    expected_sha256: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)
    version, sha256 = install_protoc.resolve_release(None, None, asset)

    assert version == "34.1"
    assert sha256 == expected_sha256


@pytest.mark.parametrize(
    ("system", "machine"),
    [
        ("Linux", "x86_64"),
        ("Windows", "AMD64"),
    ],
)
def test_main_installs_selected_platform_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    machine: str,
) -> None:
    asset = install_protoc.resolve_platform_asset(system, machine)
    destination = tmp_path / "protoc"
    github_output = tmp_path / "github-output"
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        install_protoc,
        "parse_args",
        lambda: install_protoc.argparse.Namespace(
            version=None,
            sha256=None,
            dest=destination,
        ),
    )
    monkeypatch.setattr(install_protoc, "resolve_platform_asset", lambda: asset)

    def fake_download(url: str, archive_path: Path) -> str:
        observed["url"] = url
        _write_archive(
            archive_path,
            [
                f"bin/{asset.executable_name}",
                "include/google/protobuf/descriptor.proto",
            ],
        )
        return install_protoc.load_default_sha256(asset)

    def fake_run(command: list[str], *, check: bool) -> None:
        observed["command"] = command
        observed["check"] = check

    monkeypatch.setattr(install_protoc, "download_archive", fake_download)
    monkeypatch.setattr(install_protoc.subprocess, "run", fake_run)
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    assert install_protoc.main() == 0

    archive_name = f"protoc-34.1-{asset.archive_suffix}.zip"
    assert observed["url"] == (
        "https://github.com/protocolbuffers/protobuf/releases/download/"
        f"v34.1/{archive_name}"
    )
    command = observed["command"]
    assert isinstance(command, list)
    assert Path(command[0]).name == asset.executable_name
    assert command[1:] == ["--version"]
    assert observed["check"] is True
    assert (destination / "bin" / asset.executable_name).is_file()
    assert (
        destination / "include" / "google" / "protobuf" / "descriptor.proto"
    ).is_file()
    assert (destination / install_protoc.VERSION_MARKER).read_text(
        encoding="utf-8"
    ) == "34.1\n"
    outputs = github_output.read_text(encoding="utf-8").splitlines()
    assert "version=34.1" in outputs
    assert f"root={destination.as_posix()}" in outputs
    assert f"protoc={(destination / 'bin' / asset.executable_name).as_posix()}" in outputs
    assert f"include={(destination / 'include').as_posix()}" in outputs


@pytest.mark.parametrize(
    "member",
    [
        "/tmp/protoc",
        r"C:\tmp\protoc.exe",
        r"\tmp\protoc.exe",
        "../protoc",
        "bin/../../protoc",
        r"bin\..\protoc.exe",
    ],
)
def test_extract_archive_safely_rejects_absolute_or_parent_traversal_members(
    tmp_path: Path,
    member: str,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, [member, "bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="unsafe"):
            install_protoc.extract_archive_safely(archive, destination)

    assert not destination.exists()


def test_extract_archive_safely_rejects_too_many_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc", "include/descriptor.proto"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="more than 1 members"):
            install_protoc.extract_archive_safely(archive, destination, max_members=1)

    assert not destination.exists()


def test_extract_archive_safely_rejects_oversized_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="member exceeds"):
            install_protoc.extract_archive_safely(
                archive, destination, max_member_bytes=6
            )

    assert not destination.exists()


def test_extract_archive_safely_rejects_oversized_uncompressed_total(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "protoc.zip"
    destination = tmp_path / "destination"
    _write_archive(archive_path, ["bin/protoc", "include/descriptor.proto"])

    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(RuntimeError, match="uncompressed-size limit"):
            install_protoc.extract_archive_safely(
                archive, destination, max_uncompressed_bytes=13
            )

    assert not destination.exists()
