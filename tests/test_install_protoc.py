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
            ["bin/protoc", "include/google/protobuf/descriptor.proto"],
        )
        return install_protoc.load_default_sha256()

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


def test_resolve_release_requires_digest_for_version_override() -> None:
    with pytest.raises(RuntimeError, match="--sha256 is required"):
        install_protoc.resolve_release("999.0", None)


def test_configured_release_digest_matches_upstream_asset() -> None:
    version, sha256 = install_protoc.resolve_release(None, None)

    assert version == "34.1"
    assert sha256 == "af27ea66cd26938fe48587804ca7d4817457a08350021a1c6e23a27ccc8c6904"


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
