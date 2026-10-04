"""Run venv's CLI entry point without discarding pip-bootstrap diagnostics.

CMake invokes this with the selected host Python and -I, and owns the timeout
and transaction rollback. Keep venv's platform/version defaults in one place.
"""

from __future__ import annotations

import re
import subprocess
import sys


_MAX_DIAGNOSTIC_CHARS = 16 * 1024
_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
_TRUNCATION = "\n[... bootstrap diagnostic truncated ...]\n"


def _diagnostic(value: bytes | str | None) -> str:
    if value is None:
        return "<no captured output>"
    text = (
        value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Redact whole URLs, including path/query tokens, before truncating so a
    # boundary cannot expose a credential. Never print the child command or env.
    text = _URL.sub("<redacted URL>", text)
    text = "".join(c if c.isprintable() or c in "\n\t" else "?" for c in text)
    if len(text) > _MAX_DIAGNOSTIC_CHARS:
        head = (_MAX_DIAGNOSTIC_CHARS - len(_TRUNCATION)) // 2
        tail = _MAX_DIAGNOSTIC_CHARS - len(_TRUNCATION) - head
        text = text[:head] + _TRUNCATION + text[-tail:]
    return text


def main() -> int:
    try:
        import venv

        # venv.__main__ catches this exception and prints only str(error),
        # losing the output captured by EnvBuilder._call_new_python.
        venv.main()
    except subprocess.CalledProcessError as error:
        print(
            f"Python environment bootstrap subprocess failed (exit code {error.returncode}).",
            file=sys.stderr,
        )
        print(_diagnostic(error.output), file=sys.stderr)
        if error.stderr is not None:
            print(_diagnostic(error.stderr), file=sys.stderr)
        return error.returncode if error.returncode > 0 else 1
    except Exception as error:
        print(_diagnostic(f"{type(error).__name__}: {error}"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stderr.reconfigure(errors="backslashreplace")
    sys.exit(main())
