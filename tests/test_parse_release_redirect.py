import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "parse_release_redirect.py"
SPEC = importlib.util.spec_from_file_location("parse_release_redirect", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
parse_release_redirect = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = parse_release_redirect
SPEC.loader.exec_module(parse_release_redirect)


def test_parse_redirect_location_accepts_the_final_https_response_block() -> None:
    headers = (
        b"HTTP/1.1 100 Continue\r\n\r\n"
        b"HTTP/2 302\r\n"
        b"Location: https://storage.example.invalid/archive.zip?signature=abc\r\n"
        b"X-Request-Id: request-id\r\n\r\n"
    )

    assert parse_release_redirect.parse_redirect_location(headers) == (
        "https://storage.example.invalid/archive.zip?signature=abc"
    )


@pytest.mark.parametrize(
    "headers",
    [
        b"",
        b"not an HTTP response\r\nLocation: https://storage.example.invalid/x\r\n\r\n",
        b"HTTP/1.1 302\r\n\r\n",
        b"HTTP/1.1 302\r\nLocation: https://a.invalid/x\r\nLocation: https://b.invalid/x\r\n\r\n",
        b"HTTP/1.1 302\r\nLocation: http://storage.example.invalid/x\r\n\r\n",
        b"HTTP/1.1 302\r\nLocation: https://user@storage.example.invalid/x\r\n\r\n",
        b"HTTP/1.1 302\r\nLocation: https://storage.example.invalid/x#fragment\r\n\r\n",
        b"HTTP/1.1 302\r\nLocation: https://storage.example.invalid/x bad\r\n\r\n",
    ],
)
def test_parse_redirect_location_rejects_unsafe_or_malformed_headers(
    headers: bytes,
) -> None:
    with pytest.raises(parse_release_redirect.RedirectLocationError) as error:
        parse_release_redirect.parse_redirect_location(headers)

    assert "https://" not in str(error.value)
