from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType


def _load_verify_tracked_tree_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "scripts"
        / "verify_tracked_tree.py"
    )
    spec = importlib.util.spec_from_file_location("verify_tracked_tree", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_tracked_tree = _load_verify_tracked_tree_module()


def test_exact_tree_membership_includes_ignored_untracked_files(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "generated"
    generated.mkdir()
    tracked = generated / "tracked.hpp"
    tracked.write_text("tracked\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("generated/*.ignored\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "add", ".gitignore", "generated/tracked.hpp"],
        cwd=tmp_path,
        check=True,
    )
    ignored = generated / "stale.ignored"
    ignored.write_text("stale\n", encoding="utf-8")

    missing, extra = verify_tracked_tree.compare_tracked_tree(
        generated,
        repo_root=tmp_path,
    )

    assert missing == set()
    assert extra == {"generated/stale.ignored"}

    tracked.unlink()
    missing, extra = verify_tracked_tree.compare_tracked_tree(
        generated,
        repo_root=tmp_path,
    )
    assert missing == {"generated/tracked.hpp"}
    assert extra == {"generated/stale.ignored"}
