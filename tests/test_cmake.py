from __future__ import annotations

import subprocess
from pathlib import Path


def test_posix_wrapper_shell_quotes_single_quotes(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmake_script = tmp_path / "quote_test.cmake"
    quoted_output = tmp_path / "quoted.txt"

    cmake_script.write_text(
        "\n".join(
            [
                "cmake_minimum_required(VERSION 3.24)",
                f'include("{(repo_root / "cmake" / "ProtocyteFunctions.cmake").as_posix()}")',
                '_protocyte_shell_single_quote(quoted "alpha\'beta")',
                f'file(WRITE "{quoted_output.as_posix()}" "${{quoted}}")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(["cmake", "-P", str(cmake_script)], check=True)

    assert quoted_output.read_text(encoding="utf-8") == "'alpha'\"'\"'beta'"
