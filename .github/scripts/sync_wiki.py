#!/usr/bin/env python3
"""Mirror the canonical wiki Markdown into an existing GitHub Wiki checkout."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MirrorPlan:
    add: tuple[str, ...]
    update: tuple[str, ...]
    remove: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.add or self.update or self.remove)


def _default_source() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "wiki"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mirror docs/wiki/*.md into an existing wiki checkout. "
            "The helper never commits or pushes."
        )
    )
    parser.add_argument("wiki_checkout", type=Path)
    parser.add_argument(
        "--source",
        type=Path,
        default=_default_source(),
        help="canonical Markdown directory (default: repository docs/wiki)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="write additions and updates, and remove stale Markdown files",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit nonzero when the checkout differs",
    )
    return parser.parse_args()


def _validate_directory(path: Path, description: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise ValueError(f"{description} is not an existing directory: {resolved}")
    return resolved


def _read_markdown(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        for path in sorted(directory.glob("*.md"), key=lambda item: item.name)
        if path.is_file()
    }


def _plan(source: dict[str, bytes], destination: dict[str, bytes]) -> MirrorPlan:
    source_names = set(source)
    destination_names = set(destination)
    return MirrorPlan(
        add=tuple(sorted(source_names - destination_names)),
        update=tuple(
            sorted(
                name
                for name in source_names & destination_names
                if source[name] != destination[name]
            )
        ),
        remove=tuple(sorted(destination_names - source_names)),
    )


def _print_plan(plan: MirrorPlan) -> None:
    for operation, names in (
        ("add", plan.add),
        ("update", plan.update),
        ("remove", plan.remove),
    ):
        for name in names:
            print(f"{operation}: {name}")
    if not plan.changed:
        print("Wiki checkout already matches the canonical source.")


def _apply(
    plan: MirrorPlan,
    source_files: dict[str, bytes],
    destination: Path,
) -> None:
    for name in (*plan.add, *plan.update):
        (destination / name).write_bytes(source_files[name])
    for name in plan.remove:
        (destination / name).unlink()


def main() -> int:
    args = _parse_args()
    try:
        source = _validate_directory(args.source, "source")
        destination = _validate_directory(args.wiki_checkout, "wiki checkout")
        if not (destination / ".git").exists():
            raise ValueError(
                f"wiki checkout has no .git metadata: {destination}"
            )
        source_files = _read_markdown(source)
        if "Home.md" not in source_files:
            raise ValueError(f"canonical source has no Home.md: {source}")
        destination_files = _read_markdown(destination)
        plan = _plan(source_files, destination_files)
        _print_plan(plan)
        if args.apply and plan.changed:
            _apply(plan, source_files, destination)
            print("Applied wiki mirror. Review the Git diff before committing.")
        elif plan.changed and not args.check:
            print("Dry run only. Re-run with --apply to modify the checkout.")
        return 1 if args.check and plan.changed else 0
    except (OSError, ValueError) as error:
        print(f"sync_wiki.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
