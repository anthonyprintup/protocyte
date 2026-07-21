#!/usr/bin/env python3
"""Parse one safe HTTPS signed-artifact redirect from curl response headers."""

from __future__ import annotations

import argparse
import sys
from email.parser import BytesHeaderParser
from pathlib import Path
from urllib.parse import urlsplit


class RedirectLocationError(ValueError):
    """The authenticated artifact response did not contain a safe redirect."""


def parse_redirect_location(contents: bytes) -> str:
    blocks = [block for block in contents.split(b"\r\n\r\n") if b"\n" in block]
    if not blocks:
        raise RedirectLocationError(
            "artifact redirect did not include response headers"
        )

    status_line, separator, raw_headers = blocks[-1].partition(b"\r\n")
    if not separator or not status_line.startswith(b"HTTP/"):
        raise RedirectLocationError("artifact redirect response headers are malformed")

    headers = BytesHeaderParser().parsebytes(raw_headers + b"\r\n\r\n")
    locations = headers.get_all("Location", [])
    if len(locations) != 1:
        raise RedirectLocationError(
            "artifact redirect did not contain exactly one Location header"
        )

    location = locations[0].strip()
    if not location.isascii() or any(ord(character) <= 0x20 for character in location):
        raise RedirectLocationError("artifact redirect Location has invalid characters")
    try:
        parsed = urlsplit(location)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise RedirectLocationError(
            "artifact redirect Location is not a valid HTTPS URL"
        ) from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise RedirectLocationError(
            "artifact redirect Location is not a valid HTTPS URL"
        )
    return location


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("headers", type=Path)
    args = parser.parse_args(argv)
    try:
        print(parse_redirect_location(args.headers.read_bytes()))
    except (OSError, RedirectLocationError) as error:
        print(f"artifact redirect validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
