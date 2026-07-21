"""Retain a POSIX formatter process group until its caller tears it down."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys


def _write_status(control_fd: int, payload: object) -> bool:
    content = (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )
    while content:
        try:
            written = os.write(control_fd, content)
        except InterruptedError:
            continue
        except OSError:
            return False
        content = content[written:]
    return True


def _redirect_standard_streams() -> None:
    devnull = os.open(os.devnull, os.O_RDWR)
    try:
        for descriptor in (0, 1, 2):
            if descriptor != devnull:
                os.dup2(devnull, descriptor)
    finally:
        if devnull > 2:
            os.close(devnull)


def _wait_for_termination() -> None:
    while True:
        try:
            signal.pause()
        except InterruptedError:
            pass


def _launch_error_payload(exc: BaseException) -> dict[str, object]:
    if isinstance(exc, OSError):
        filename = exc.filename
        if isinstance(filename, bytes):
            filename = os.fsdecode(filename)
        return {
            "error": {
                "errno": exc.errno,
                "message": exc.strerror or str(exc),
                "filename": filename,
            }
        }
    return {"error": {"errno": None, "message": str(exc), "filename": None}}


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) < 2:
        return 2

    try:
        control_fd = int(arguments[0])
    except ValueError:
        return 2
    command = arguments[1:]
    try:
        os.set_inheritable(control_fd, False)
    except OSError:
        return 2

    try:
        formatter = subprocess.Popen(command, close_fds=True)
    except Exception as exc:
        _redirect_standard_streams()
        if _write_status(control_fd, _launch_error_payload(exc)):
            _wait_for_termination()
        return 1

    _redirect_standard_streams()
    returncode = formatter.wait()
    if _write_status(control_fd, {"returncode": returncode}):
        _wait_for_termination()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
