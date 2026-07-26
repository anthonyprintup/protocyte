#!/usr/bin/env python3
"""Normalize release archives so identical inputs produce identical bytes."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import stat
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path


ZIP_MINIMUM_EPOCH = 315532800  # 1980-01-01, the earliest ZIP timestamp.


def _normalized_mode(is_directory: bool, source_mode: int) -> int:
    if is_directory:
        return 0o755
    return 0o755 if source_mode & 0o111 else 0o644


def normalize_zip(path: Path, epoch: int) -> None:
    if epoch < ZIP_MINIMUM_EPOCH:
        raise ValueError("ZIP timestamps cannot predate 1980-01-01")

    with zipfile.ZipFile(path, "r") as source:
        entries = []
        for info in source.infolist():
            source_mode = info.external_attr >> 16
            if stat.S_ISLNK(source_mode):
                raise ValueError(
                    f"symbolic links are not supported in ZIP archives: {info.filename}"
                )
            entries.append(
                (info.filename, info.is_dir(), source_mode, source.read(info))
            )

    timestamp = time.gmtime(epoch)[:6]
    temporary = _temporary_sibling(path)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as destination:
            for name, is_directory, source_mode, contents in sorted(entries):
                normalized_name = name.rstrip("/") + "/" if is_directory else name
                info = zipfile.ZipInfo(normalized_name, timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                mode = _normalized_mode(is_directory, source_mode)
                file_type = stat.S_IFDIR if is_directory else stat.S_IFREG
                info.external_attr = (file_type | mode) << 16
                info.external_attr |= 0x10 if is_directory else 0
                destination.writestr(info, contents)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def normalize_tar_gz(path: Path, epoch: int) -> None:
    with tarfile.open(path, "r:gz") as source:
        entries = _read_tar_entries(source)
    _write_tar_gz(path, entries, epoch)


def pack_tar_gz(directory: Path, output: Path, epoch: int) -> None:
    if not directory.is_dir():
        raise ValueError(f"archive input is not a directory: {directory}")

    entries: list[tuple[str, bool, int, bytes]] = [
        (directory.name, True, directory.stat().st_mode, b"")
    ]
    for entry in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        relative = entry.relative_to(directory).as_posix()
        name = f"{directory.name}/{relative}"
        if entry.is_symlink():
            raise ValueError(
                f"symbolic links are not supported in release archives: {entry}"
            )
        if entry.is_dir():
            entries.append((name, True, entry.stat().st_mode, b""))
        elif entry.is_file():
            entries.append((name, False, entry.stat().st_mode, entry.read_bytes()))
        else:
            raise ValueError(
                f"unsupported filesystem entry in release archive: {entry}"
            )
    _write_tar_gz(output, entries, epoch)


def _read_tar_entries(source: tarfile.TarFile) -> list[tuple[str, bool, int, bytes]]:
    entries: list[tuple[str, bool, int, bytes]] = []
    for member in source.getmembers():
        if member.isdir():
            entries.append((member.name, True, member.mode, b""))
            continue
        if not member.isfile():
            raise ValueError(
                f"unsupported member in release archive: {member.name} ({member.type!r})"
            )
        extracted = source.extractfile(member)
        if extracted is None:
            raise ValueError(f"could not read release archive member: {member.name}")
        entries.append((member.name, False, member.mode, extracted.read()))
    return entries


def _write_tar_gz(
    output: Path,
    entries: list[tuple[str, bool, int, bytes]],
    epoch: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_sibling(output)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=9,
                fileobj=raw,
                mtime=epoch,
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed,
                    mode="w",
                    format=tarfile.PAX_FORMAT,
                ) as destination:
                    for name, is_directory, source_mode, contents in sorted(entries):
                        normalized_name = (
                            name.rstrip("/") + "/" if is_directory else name
                        )
                        info = tarfile.TarInfo(normalized_name)
                        info.type = tarfile.DIRTYPE if is_directory else tarfile.REGTYPE
                        info.mode = _normalized_mode(is_directory, source_mode)
                        info.mtime = epoch
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        info.pax_headers = {}
                        info.size = 0 if is_directory else len(contents)
                        if is_directory:
                            destination.addfile(info)
                        else:
                            destination.addfile(info, io.BytesIO(contents))
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def _temporary_sibling(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    return Path(name)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epoch", type=int, required=True)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    normalize = subparsers.add_parser("normalize")
    normalize.add_argument("kind", choices=("zip", "tar-gz"))
    normalize.add_argument("archive", type=Path)

    pack = subparsers.add_parser("pack-tar-gz")
    pack.add_argument("directory", type=Path)
    pack.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.operation == "normalize":
        if args.kind == "zip":
            normalize_zip(args.archive, args.epoch)
        else:
            normalize_tar_gz(args.archive, args.epoch)
    else:
        pack_tar_gz(args.directory, args.output, args.epoch)


if __name__ == "__main__":
    main()
