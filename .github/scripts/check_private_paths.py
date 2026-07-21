from __future__ import annotations

import argparse
import codecs
import io
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


_HOME_ACCOUNT = rb"[A-Za-z0-9_\x80-\xff](?:[A-Za-z0-9._ -]|[\x80-\xff])*+"
_HOME_PATH_BOUNDARY = rb"(?:[\\/]|(?=$|[\x00\r\n\t \"'`),;:!?)}\]]))"


_PRIVATE_PATH_PATTERNS = (
    re.compile(
        rb"(?<![A-Za-z0-9])(?:[A-Za-z]:|/[A-Za-z]:)[\\/]+"
        rb"Users[\\/]+" + _HOME_ACCOUNT + _HOME_PATH_BOUNDARY,
        re.IGNORECASE,
    ),
    re.compile(
        rb"(?<![A-Za-z0-9._-])/(?:mnt/[A-Za-z]|cygdrive/[A-Za-z]|[A-Za-z])/"
        rb"Users/" + _HOME_ACCOUNT + _HOME_PATH_BOUNDARY,
        re.IGNORECASE,
    ),
    re.compile(
        rb"(?<![:\\/A-Za-z0-9])(?:[\\/]{2})"
        rb"[A-Za-z0-9_](?:[A-Za-z0-9._-])*[\\/]+"
        rb"Users[\\/]+" + _HOME_ACCOUNT + _HOME_PATH_BOUNDARY,
        re.IGNORECASE,
    ),
    re.compile(
        rb"(?<![A-Za-z0-9._-])/(?:home|Users)/"
        + _HOME_ACCOUNT
        + _HOME_PATH_BOUNDARY,
        re.IGNORECASE,
    ),
    re.compile(
        rb"(?<![A-Za-z0-9._-])/" + rb"root" + _HOME_PATH_BOUNDARY,
        re.IGNORECASE,
    ),
)
_SCAN_CHUNK_BYTES = 1024 * 1024
_SCAN_OVERLAP_BYTES = 4096


class GitCommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class _TreeEntry:
    name: bytes
    child_tree: str | None


@dataclass(frozen=True, order=True)
class Violation:
    source: str
    object_id: str | None = None


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
        raise GitCommandError("a required Git command failed; details are redacted")
    return completed.stdout


def _matches_private_path(data: bytes) -> bool:
    lowered = data.lower()
    if not any(
        needle in lowered
        for needle in (
            b"/" + b"users",
            b"\\" + b"users",
            b"/" + b"home",
            b"/" + b"root",
        )
    ):
        return False
    return any(pattern.search(data) is not None for pattern in _PRIVATE_PATH_PATTERNS)


def _index_state(repository: Path) -> tuple[set[str], bool]:
    object_ids: set[str] = set()
    path_violation = False
    for entry in _run_git(repository, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", maxsplit=1)
        _, object_id, _ = metadata.split(b" ", maxsplit=2)
        if set(object_id) != {ord("0")}:
            object_ids.add(object_id.decode("ascii"))
        if _matches_private_path(path):
            path_violation = True
    return object_ids, path_violation


def _scan_window(tail: bytes, chunk: bytes) -> tuple[bytes, bool]:
    window = tail + chunk
    return window[-_SCAN_OVERLAP_BYTES:], _matches_private_path(window)


def _read_and_scan_payload(
    stream, size: int, *, capture: bool
) -> tuple[bool, bytes | None]:
    found = False
    raw_tail = b""
    decoded_tail = b""
    bom_tail = b""
    decoder = None
    captured = bytearray() if capture else None
    remaining = size

    while remaining:
        chunk = stream.read(min(_SCAN_CHUNK_BYTES, remaining))
        if not chunk:
            raise GitCommandError(
                "Git object streaming ended early; details are redacted"
            )
        remaining -= len(chunk)
        if captured is not None:
            captured.extend(chunk)

        raw_tail, raw_match = _scan_window(raw_tail, chunk)
        found = found or raw_match

        decode_chunk = chunk
        if decoder is None:
            bom_window = bom_tail + chunk
            bom_positions = [
                position
                for byte_order_mark in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)
                if (position := bom_window.find(byte_order_mark)) >= 0
            ]
            if bom_positions:
                decoder = codecs.getincrementaldecoder("utf-16")(errors="replace")
                decode_chunk = bom_window[min(bom_positions) :]
            else:
                bom_tail = bom_window[-1:]
        if decoder is not None:
            decoded = decoder.decode(decode_chunk, final=remaining == 0).encode("utf-8")
            decoded_tail, decoded_match = _scan_window(decoded_tail, decoded)
            found = found or decoded_match

    return found, bytes(captured) if captured is not None else None


def _object_id_bytes(repository: Path) -> int:
    object_format = _run_git(repository, "rev-parse", "--show-object-format").strip()
    if object_format == b"sha1":
        return 20
    if object_format == b"sha256":
        return 32
    raise GitCommandError("the repository uses an unsupported object format")


def _parse_tree(payload: bytes, object_id_bytes: int) -> tuple[_TreeEntry, ...]:
    entries: list[_TreeEntry] = []
    position = 0
    while position < len(payload):
        mode_end = payload.find(b" ", position)
        if mode_end < 0:
            raise GitCommandError("a stored Git tree is malformed; details are redacted")
        name_end = payload.find(b"\0", mode_end + 1)
        if name_end < 0:
            raise GitCommandError("a stored Git tree is malformed; details are redacted")
        object_end = name_end + 1 + object_id_bytes
        if object_end > len(payload):
            raise GitCommandError("a stored Git tree is malformed; details are redacted")

        mode = payload[position:mode_end]
        name = payload[mode_end + 1 : name_end]
        child_tree = (
            payload[name_end + 1 : object_end].hex()
            if mode in (b"40000", b"040000")
            else None
        )
        entries.append(_TreeEntry(name=name, child_tree=child_tree))
        position = object_end
    return tuple(entries)


def _commit_tree(payload: bytes, object_id_hex_chars: int) -> str | None:
    first_line = payload.split(b"\n", maxsplit=1)[0]
    if not first_line.startswith(b"tree "):
        return None
    object_id = first_line.removeprefix(b"tree ")
    if len(object_id) != object_id_hex_chars:
        return None
    try:
        int(object_id, 16)
    except ValueError:
        return None
    return object_id.decode("ascii")


def _scan_stored_objects(
    repository: Path,
) -> tuple[dict[str, str], dict[str, tuple[_TreeEntry, ...]], set[str]]:
    object_id_bytes = _object_id_bytes(repository)
    process = subprocess.Popen(
        [
            "git",
            "-C",
            str(repository),
            "cat-file",
            "--batch",
            "--batch-all-objects",
            "--unordered",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise GitCommandError("failed to open Git object streaming pipes")

    content_violations: dict[str, str] = {}
    trees: dict[str, tuple[_TreeEntry, ...]] = {}
    commit_trees: set[str] = set()
    try:
        while True:
            header = process.stdout.readline()
            if not header:
                break
            fields = header.rstrip(b"\n").split(b" ")
            if len(fields) != 3:
                raise GitCommandError(
                    "Git returned a malformed object header; details are redacted"
                )
            object_id_bytes_text, object_type_bytes, size_bytes = fields
            object_id = object_id_bytes_text.decode("ascii")
            object_type = object_type_bytes.decode("ascii")
            size = int(size_bytes)
            capture = object_type in ("commit", "tree")
            matched, payload = _read_and_scan_payload(
                process.stdout, size, capture=capture
            )
            if process.stdout.read(1) != b"\n":
                raise GitCommandError(
                    "Git returned a malformed object boundary; details are redacted"
                )

            if matched and object_type in ("blob", "commit", "tag"):
                content_violations[object_id] = object_type
            if object_type == "tree":
                assert payload is not None
                trees[object_id] = _parse_tree(payload, object_id_bytes)
            elif object_type == "commit":
                assert payload is not None
                root_tree = _commit_tree(payload, object_id_bytes * 2)
                if root_tree is not None:
                    commit_trees.add(root_tree)
    except BaseException:
        process.kill()
        process.wait()
        process.stderr.read()
        raise

    return_code = process.wait()
    process.stderr.read()
    if return_code != 0:
        raise GitCommandError("Git object streaming failed; details are redacted")
    return content_violations, trees, commit_trees


def _scan_tree_paths(
    trees: dict[str, tuple[_TreeEntry, ...]], commit_trees: set[str]
) -> set[str]:
    child_trees = {
        entry.child_tree
        for entries in trees.values()
        for entry in entries
        if entry.child_tree in trees
    }
    roots = (set(trees) - child_trees) | (commit_trees & set(trees))
    violations: set[str] = set()
    stack = [(root, b"") for root in sorted(roots)]

    while stack:
        tree_id, prefix = stack.pop()
        for entry in trees[tree_id]:
            path = prefix + b"/" + entry.name if prefix else entry.name
            if _matches_private_path(path):
                violations.add(tree_id)
            if entry.child_tree in trees:
                stack.append((entry.child_tree, path))
    return violations


def _pending_commit_violations(
    repository: Path, commit_message: Path
) -> list[Violation]:
    try:
        message = commit_message.read_bytes()
    except OSError as exc:
        raise GitCommandError(
            "the pending commit message could not be read; details are redacted"
        ) from exc

    violations: list[Violation] = []
    if _read_and_scan_payload_bytes(message):
        violations.append(Violation("pending commit message"))

    identities = b"\n".join(
        (
            _run_git(repository, "var", "GIT_AUTHOR_IDENT"),
            _run_git(repository, "var", "GIT_COMMITTER_IDENT"),
        )
    )
    if _read_and_scan_payload_bytes(identities):
        violations.append(Violation("pending commit metadata"))
    return violations


def _read_and_scan_payload_bytes(payload: bytes) -> bool:
    matched, _ = _read_and_scan_payload(
        io.BytesIO(payload), len(payload), capture=False
    )
    return matched


def check_repository(repository: Path) -> list[Violation]:
    repository = repository.resolve()
    index_object_ids, index_path_violation = _index_state(repository)
    content_violations, trees, commit_trees = _scan_stored_objects(repository)

    sources: dict[str, set[str]] = defaultdict(set)
    for object_id, object_type in content_violations.items():
        sources[object_id].add(f"stored Git {object_type} object")
        if object_type == "blob" and object_id in index_object_ids:
            sources[object_id].add("tracked index blob")
    for object_id in _scan_tree_paths(trees, commit_trees):
        sources[object_id].add("stored Git tree path")

    violations = [
        Violation(" and ".join(sorted(object_sources)), object_id)
        for object_id, object_sources in sources.items()
    ]
    if index_path_violation:
        violations.append(Violation("tracked index path"))
    return sorted(violations)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reject private user-home absolute paths in the tracked Git index, "
            "stored Git objects, reconstructed tree paths, and pending commits."
        )
    )
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
        help="repository to inspect (defaults to the current directory)",
    )
    parser.add_argument(
        "--commit-message",
        type=Path,
        help="also inspect a pending commit message and commit identities",
    )
    args = parser.parse_args(argv)

    try:
        violations = check_repository(args.repository)
        if args.commit_message is not None:
            violations.extend(
                _pending_commit_violations(args.repository.resolve(), args.commit_message)
            )
    except Exception:
        print(
            "private-path guard failed; all error details are redacted",
            file=sys.stderr,
        )
        return 2

    if not violations:
        print(
            "Private-path guard passed: tracked index, stored Git objects, "
            "tree paths, and pending inputs are clean."
        )
        return 0

    for violation in sorted(violations):
        object_detail = (
            f" object {violation.object_id}" if violation.object_id is not None else ""
        )
        print(
            f"private-path guard: private absolute path detected in "
            f"{violation.source}{object_detail}; matched path text is redacted",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
