import importlib.util
import io
import os
import stat
import tarfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "reproducible_archive.py"
SPEC = importlib.util.spec_from_file_location("reproducible_archive", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
reproducible_archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reproducible_archive)


def _write_zip(path: Path, *, reverse: bool, timestamp: tuple[int, ...]) -> None:
    entries = [("package/", b""), ("package/value.txt", b"release\n")]
    if reverse:
        entries.reverse()
    with zipfile.ZipFile(path, "w") as archive:
        for name, contents in entries:
            info = zipfile.ZipInfo(name, timestamp)
            info.external_attr = (0o777 if name.endswith("/") else 0o600) << 16
            archive.writestr(info, contents)


def _write_tar(path: Path, *, reverse: bool, mtime: int) -> None:
    entries = [("package/", b""), ("package/value.txt", b"release\n")]
    if reverse:
        entries.reverse()
    with tarfile.open(path, "w:gz") as archive:
        for name, contents in entries:
            info = tarfile.TarInfo(name)
            info.type = tarfile.DIRTYPE if name.endswith("/") else tarfile.REGTYPE
            info.mode = 0o777 if name.endswith("/") else 0o600
            info.mtime = mtime
            info.uid = 123
            info.gid = 456
            info.uname = "builder"
            info.gname = "builder"
            info.size = 0 if name.endswith("/") else len(contents)
            archive.addfile(info, None if name.endswith("/") else io.BytesIO(contents))


def test_zip_normalization_removes_order_timestamp_and_mode_drift(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.whl"
    second = tmp_path / "second.whl"
    _write_zip(first, reverse=False, timestamp=(2024, 1, 2, 3, 4, 6))
    _write_zip(second, reverse=True, timestamp=(2025, 5, 6, 7, 8, 10))

    epoch = 1_700_000_000
    reproducible_archive.normalize_zip(first, epoch)
    reproducible_archive.normalize_zip(second, epoch)

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["package/", "package/value.txt"]
        for info in archive.infolist():
            mode = info.external_attr >> 16
            assert stat.S_IMODE(mode) == (0o755 if info.is_dir() else 0o644)


def test_tar_normalization_removes_order_owner_timestamp_and_mode_drift(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    _write_tar(first, reverse=False, mtime=1_600_000_000)
    _write_tar(second, reverse=True, mtime=1_800_000_000)

    epoch = 1_700_000_000
    reproducible_archive.normalize_tar_gz(first, epoch)
    reproducible_archive.normalize_tar_gz(second, epoch)

    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        assert archive.getnames() == ["package", "package/value.txt"]
        for member in archive.getmembers():
            assert member.mtime == epoch
            assert member.uid == 0
            assert member.gid == 0
            assert member.uname == ""
            assert member.gname == ""
            assert member.mode == (0o755 if member.isdir() else 0o644)


def test_directory_packing_is_reproducible_with_one_normalized_root(
    tmp_path: Path,
) -> None:
    sources = [tmp_path / variant / "protocyte-prefix" for variant in ("a", "b")]
    outputs = [tmp_path / variant / "prefix.tar.gz" for variant in ("a", "b")]
    for source, source_mtime in zip(sources, (1_600_000_000, 1_800_000_000)):
        (source / "include").mkdir(parents=True)
        header = source / "include" / "runtime.hpp"
        header.write_text("// runtime\n", encoding="utf-8")
        header.touch()
        header.chmod(0o600)
        os.utime(header, (source_mtime, source_mtime))

    for source, output in zip(sources, outputs):
        reproducible_archive.pack_tar_gz(source, output, 1_700_000_000)

    assert outputs[0].read_bytes() == outputs[1].read_bytes()

    with tarfile.open(outputs[0], "r:gz") as archive:
        assert archive.getnames() == [
            "protocyte-prefix",
            "protocyte-prefix/include",
            "protocyte-prefix/include/runtime.hpp",
        ]
