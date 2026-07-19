from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def compare_tracked_tree(
    tree: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[set[str], set[str]]:
    repo_root = repo_root.resolve()
    tree = tree if tree.is_absolute() else repo_root / tree
    tree = tree.resolve()
    try:
        relative_tree = tree.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"tree is outside the repository: {tree}") from exc
    if not tree.is_dir():
        raise RuntimeError(f"tracked tree does not exist or is not a directory: {tree}")

    result = subprocess.run(
        ["git", "ls-files", "-z", "--", relative_tree],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git ls-files failed"
        raise RuntimeError(detail)

    tracked = {item for item in result.stdout.split("\0") if item}
    actual = {
        path.relative_to(repo_root).as_posix()
        for path in tree.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    return tracked - actual, actual - tracked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that a generated directory contains exactly its Git-tracked files, "
            "including files ignored by .gitignore."
        )
    )
    parser.add_argument("tree", type=Path, help="repository-relative directory to verify")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        missing, extra = compare_tracked_tree(args.tree)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if missing:
        print("Tracked files missing from the generated tree:", file=sys.stderr)
        for path in sorted(missing):
            print(f"  {path}", file=sys.stderr)
    if extra:
        print("Untracked or ignored files present in the generated tree:", file=sys.stderr)
        for path in sorted(extra):
            print(f"  {path}", file=sys.stderr)
    return 1 if missing or extra else 0


if __name__ == "__main__":
    raise SystemExit(main())
