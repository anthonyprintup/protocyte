from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path


_PRIVATE_PATH_PATTERNS = (
    re.compile(
        rb"(?<![A-Za-z0-9])(?:[A-Za-z]:|/[A-Za-z]:)[\\/]+"
        rb"Users[\\/]+[^\\/\x00\r\n]+[\\/]",
        re.IGNORECASE,
    ),
    re.compile(
        rb"(?<![A-Za-z0-9._-])/(?:home|Users)/[^/\x00\r\n]+/",
        re.IGNORECASE,
    ),
)
_SCAN_CHUNK_BYTES = 1024 * 1024
_SCAN_OVERLAP_BYTES = 4096


class GitCommandError(RuntimeError):
    pass


def _run_git(
    repository: Path, *arguments: str, input_bytes: bytes | None = None
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=input_bytes,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitCommandError(detail or f"git {' '.join(arguments)} failed")
    return completed.stdout


def _index_blob_ids(repository: Path) -> set[str]:
    blobs: set[str] = set()
    for entry in _run_git(repository, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, _path = entry.split(b"\t", maxsplit=1)
        _, object_id, _ = metadata.split(b" ", maxsplit=2)
        if set(object_id) == {ord("0")}:
            continue
        blobs.add(object_id.decode("ascii"))
    return blobs


def _reachable_object_ids(repository: Path) -> set[str]:
    output = _run_git(
        repository,
        "rev-list",
        "--objects",
        "--all",
        "--reflog",
        "--no-object-names",
    )
    return {line.decode("ascii") for line in output.splitlines() if line}


def _blob_object_ids(repository: Path, object_ids: Iterable[str]) -> set[str]:
    requested = sorted(set(object_ids))
    if not requested:
        return set()
    output = _run_git(
        repository,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype)",
        input_bytes=("\n".join(requested) + "\n").encode("ascii"),
    )
    blobs: set[str] = set()
    for line in output.splitlines():
        object_id, object_type = line.decode("ascii").split(" ", maxsplit=1)
        if object_type == "blob":
            blobs.add(object_id)
    return blobs


def _contains_private_path(stream, size: int) -> bool:
    found = False
    tail = b""
    remaining = size
    while remaining:
        chunk = stream.read(min(_SCAN_CHUNK_BYTES, remaining))
        if not chunk:
            raise GitCommandError("git cat-file ended before the advertised blob size")
        remaining -= len(chunk)
        window = tail + chunk
        if any(
            pattern.search(window) is not None for pattern in _PRIVATE_PATH_PATTERNS
        ):
            found = True
        tail = window[-_SCAN_OVERLAP_BYTES:]
    return found


def _scan_blobs(repository: Path, object_ids: Iterable[str]) -> set[str]:
    requested = sorted(set(object_ids))
    if not requested:
        return set()

    process = subprocess.Popen(
        ["git", "-C", str(repository), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        raise GitCommandError("failed to open git cat-file pipes")

    violations: set[str] = set()
    return_code = -1
    error_output = b""
    try:
        for object_id in requested:
            process.stdin.write(object_id.encode("ascii") + b"\n")
            process.stdin.flush()
            header = process.stdout.readline()
            if not header:
                raise GitCommandError(
                    "git cat-file ended before returning a blob header"
                )
            fields = header.rstrip(b"\n").split(b" ")
            if len(fields) != 3 or fields[1] != b"blob":
                raise GitCommandError(
                    f"git cat-file returned an unexpected header for object {object_id}"
                )
            size = int(fields[2])
            if _contains_private_path(process.stdout, size):
                violations.add(object_id)
            if process.stdout.read(1) != b"\n":
                raise GitCommandError("git cat-file returned a malformed blob boundary")
    finally:
        process.stdin.close()
        return_code = process.wait()
        error_output = process.stderr.read()

    if return_code != 0:
        detail = error_output.decode("utf-8", errors="replace").strip()
        raise GitCommandError(detail or "git cat-file failed")
    return violations


def check_repository(repository: Path) -> list[tuple[str, tuple[str, ...]]]:
    repository = repository.resolve()
    index = _index_blob_ids(repository)
    reachable = _blob_object_ids(repository, _reachable_object_ids(repository))

    sources: dict[str, set[str]] = defaultdict(set)
    for object_id in index:
        sources[object_id].add("tracked index")
    for object_id in reachable:
        sources[object_id].add("reachable Git history")

    violations = _scan_blobs(repository, sources)
    return [
        (object_id, tuple(sorted(sources[object_id])))
        for object_id in sorted(violations)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reject private user-home absolute paths in the tracked Git index and "
            "all reachable history blobs."
        )
    )
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
        help="repository to inspect (defaults to the current directory)",
    )
    args = parser.parse_args(argv)

    try:
        violations = check_repository(args.repository)
    except (GitCommandError, OSError, ValueError) as exc:
        print(f"private-path guard failed: {exc}", file=sys.stderr)
        return 2

    if not violations:
        print(
            "Private-path guard passed: tracked index and reachable history are clean."
        )
        return 0

    for object_id, sources in violations:
        source_list = " and ".join(sources)
        print(
            f"private-path guard: private absolute path detected in {source_list} "
            f"blob {object_id}; matched path text is redacted",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
