from pathlib import Path

import pytest

from tests.smoke.tools import generate_checked_outputs


def test_checked_smoke_regeneration_replaces_the_owned_tree_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_out_dir = tmp_path / "generated"
    (checked_out_dir / "nested").mkdir(parents=True)
    (checked_out_dir / "kept-but-stale.hpp").write_text("stale\n", encoding="utf-8")
    (checked_out_dir / "nested" / "removed.cpp").write_text(
        "stale\n",
        encoding="utf-8",
    )

    def write_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> None:
        del clang_format, clang_format_config
        (out_dir / "nested").mkdir()
        (out_dir / "current.hpp").write_text("current\n", encoding="utf-8")
        (out_dir / "nested" / "current.cpp").write_text(
            "current\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        write_staged_outputs,
    )

    error = generate_checked_outputs._regenerate_checked_outputs(
        checked_out_dir,
        "unused-clang-format",
        tmp_path / ".clang-format",
    )

    assert error is None
    assert {
        path.relative_to(checked_out_dir).as_posix()
        for path in checked_out_dir.rglob("*")
        if path.is_file()
    } == {"current.hpp", "nested/current.cpp"}


def test_failed_smoke_regeneration_keeps_the_previous_checked_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_out_dir = tmp_path / "generated"
    checked_out_dir.mkdir()
    previous = checked_out_dir / "previous.hpp"
    previous.write_text("previous\n", encoding="utf-8")

    def fail_staged_outputs(
        out_dir: Path,
        clang_format: str,
        clang_format_config: Path,
    ) -> str:
        del clang_format, clang_format_config
        (out_dir / "partial.hpp").write_text("partial\n", encoding="utf-8")
        return "generation failed"

    monkeypatch.setattr(
        generate_checked_outputs,
        "_write_checked_outputs",
        fail_staged_outputs,
    )

    error = generate_checked_outputs._regenerate_checked_outputs(
        checked_out_dir,
        "unused-clang-format",
        tmp_path / ".clang-format",
    )

    assert error == "generation failed"
    assert previous.read_text(encoding="utf-8") == "previous\n"
    assert not (checked_out_dir / "partial.hpp").exists()
