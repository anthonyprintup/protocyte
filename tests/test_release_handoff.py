from __future__ import annotations

import hashlib
import importlib.util
import stat
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "download_release_handoff.py"
SPEC = importlib.util.spec_from_file_location("download_release_handoff", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
download_release_handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download_release_handoff)


def _write_handoff(
    archive: Path,
    *,
    extra: tuple[tuple[str, bytes], ...] = (),
    symlink_name: str | None = None,
    checksum_override: bytes | None = None,
) -> tuple[str, tuple[str, str, str]]:
    names = ("protocyte.whl", "protocyte.tar.gz", "protocyte-cmake.tar.gz")
    contents = {
        names[0]: b"wheel\n",
        names[1]: b"sdist\n",
        names[2]: b"cmake\n",
    }
    checksums = b"".join(
        f"{hashlib.sha256(contents[name]).hexdigest()}  {name}\n".encode()
        for name in names
    )
    with zipfile.ZipFile(archive, "w") as handoff:
        handoff.writestr("SHA256SUMS", checksum_override or checksums)
        for name, content in contents.items():
            if name == symlink_name:
                entry = zipfile.ZipInfo(name)
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                handoff.writestr(entry, b"target")
            else:
                handoff.writestr(name, content)
        for name, content in extra:
            handoff.writestr(name, content)
    return hashlib.sha256(archive.read_bytes()).hexdigest(), names


def test_verified_handoff_extracts_exact_files(tmp_path: Path) -> None:
    archive = tmp_path / "handoff.zip"
    digest, names = _write_handoff(archive)
    destination = tmp_path / "handoff"

    download_release_handoff.extract_verified_archive(
        archive,
        destination,
        expected_digest=digest,
        artifact_names=names,
    )

    assert sorted(path.name for path in destination.iterdir()) == sorted(
        ("SHA256SUMS", *names)
    )


def test_outer_digest_mismatch_blocks_before_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "handoff.zip"
    _, names = _write_handoff(archive)
    destination = tmp_path / "handoff"

    with pytest.raises(
        download_release_handoff.HandoffError,
        match="failed SHA-256 verification",
    ):
        download_release_handoff.extract_verified_archive(
            archive,
            destination,
            expected_digest="0" * 64,
            artifact_names=names,
        )

    assert not destination.exists()
    assert not list(tmp_path.glob(".handoff-*"))


@pytest.mark.parametrize(
    "extra",
    [
        ("unexpected.txt", b"unexpected\n"),
        ("../outside.txt", b"outside\n"),
    ],
)
def test_handoff_rejects_extra_entries_without_partial_output(
    tmp_path: Path,
    extra: tuple[str, bytes],
) -> None:
    archive = tmp_path / "handoff.zip"
    digest, names = _write_handoff(archive, extra=(extra,))
    destination = tmp_path / "handoff"

    with pytest.raises(download_release_handoff.HandoffError):
        download_release_handoff.extract_verified_archive(
            archive,
            destination,
            expected_digest=digest,
            artifact_names=names,
        )

    assert not destination.exists()
    assert not (tmp_path / "outside.txt").exists()


def test_handoff_rejects_symlink_and_bad_inner_checksums(tmp_path: Path) -> None:
    for case in ("symlink", "checksums"):
        archive = tmp_path / f"{case}.zip"
        options = (
            {"symlink_name": "protocyte.whl"}
            if case == "symlink"
            else {"checksum_override": b"0" * 64 + b"  protocyte.whl\n"}
        )
        digest, names = _write_handoff(archive, **options)
        destination = tmp_path / case

        with pytest.raises(download_release_handoff.HandoffError):
            download_release_handoff.extract_verified_archive(
                archive,
                destination,
                expected_digest=digest,
                artifact_names=names,
            )

        assert not destination.exists()


def test_metadata_is_bound_to_id_name_digest_run_and_head() -> None:
    digest = "a" * 64
    metadata = {
        "id": 42,
        "name": "release",
        "digest": f"sha256:{digest}",
        "expired": False,
        "workflow_run": {"id": 7, "head_sha": "b" * 40},
    }
    download_release_handoff.validate_metadata(
        metadata,
        artifact_id=42,
        artifact_name="release",
        artifact_digest=digest,
        run_id=7,
        head_sha="b" * 40,
    )

    for field, value in (
        ("id", 43),
        ("name", "other"),
        ("digest", f"sha256:{'c' * 64}"),
        ("expired", True),
    ):
        tampered = dict(metadata)
        tampered[field] = value
        with pytest.raises(download_release_handoff.HandoffError):
            download_release_handoff.validate_metadata(
                tampered,
                artifact_id=42,
                artifact_name="release",
                artifact_digest=digest,
                run_id=7,
                head_sha="b" * 40,
            )
