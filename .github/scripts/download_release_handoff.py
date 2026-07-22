#!/usr/bin/env python3
"""Download and verify one immutable GitHub Actions release handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO


_API_VERSION = "2022-11-28"
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_BUFFER_SIZE = 1024 * 1024


class HandoffError(RuntimeError):
    """The release handoff could not be authenticated or extracted safely."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_digest(value: str) -> str:
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise HandoffError("release artifact digest is not a lowercase SHA-256 value")
    return digest


def _safe_https_url(value: str, *, description: str) -> str:
    if not value.isascii() or any(ord(character) <= 0x20 for character in value):
        raise HandoffError(f"{description} contains invalid characters")
    try:
        parsed = urllib.parse.urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise HandoffError(f"{description} is not a valid HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise HandoffError(f"{description} is not a valid HTTPS URL")
    return value


def _authenticated_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": _API_VERSION,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                raise HandoffError(
                    f"GitHub artifact metadata request returned HTTP {response.status}"
                )
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in _REDIRECT_STATUSES:
            raise HandoffError(
                "authenticated GitHub metadata requests must not redirect"
            ) from error
        raise HandoffError(
            f"GitHub artifact metadata request returned HTTP {error.code}"
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise HandoffError("GitHub artifact metadata request failed") from error
    if not isinstance(payload, dict):
        raise HandoffError("GitHub artifact metadata response is not an object")
    return payload


def _artifact_redirect(url: str, token: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": _API_VERSION,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=30):
            pass
    except urllib.error.HTTPError as error:
        if error.code not in _REDIRECT_STATUSES:
            raise HandoffError(
                f"GitHub artifact download request returned HTTP {error.code}"
            ) from error
        locations = error.headers.get_all("Location", [])
        if len(locations) != 1:
            raise HandoffError(
                "GitHub artifact download did not return exactly one redirect"
            ) from error
        return _safe_https_url(
            locations[0].strip(), description="GitHub artifact redirect"
        )
    except OSError as error:
        raise HandoffError("GitHub artifact download request failed") from error
    raise HandoffError("GitHub artifact download did not return a redirect")


def _copy_response(response: BinaryIO, destination: Path) -> None:
    with destination.open("xb") as target:
        shutil.copyfileobj(response, target, length=_BUFFER_SIZE)


def _download_signed(url: str, destination: Path) -> None:
    current = _safe_https_url(url, description="signed artifact URL")
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(4):
        request = urllib.request.Request(current)
        try:
            with opener.open(request, timeout=120) as response:
                if response.status != 200:
                    raise HandoffError(
                        f"signed artifact download returned HTTP {response.status}"
                    )
                _copy_response(response, destination)
                return
        except urllib.error.HTTPError as error:
            if error.code not in _REDIRECT_STATUSES:
                raise HandoffError(
                    f"signed artifact download returned HTTP {error.code}"
                ) from error
            locations = error.headers.get_all("Location", [])
            if len(locations) != 1:
                raise HandoffError(
                    "signed artifact download did not return exactly one redirect"
                ) from error
            current = _safe_https_url(
                locations[0].strip(), description="signed artifact redirect"
            )
        except OSError as error:
            raise HandoffError("signed artifact download failed") from error
    raise HandoffError("signed artifact download exceeded three redirects")


def validate_metadata(
    metadata: dict[str, object],
    *,
    artifact_id: int,
    artifact_name: str,
    artifact_digest: str,
    run_id: int,
    head_sha: str,
) -> None:
    workflow_run = metadata.get("workflow_run")
    if not isinstance(workflow_run, dict):
        raise HandoffError("release artifact metadata is missing its workflow run")
    if (
        metadata.get("id") != artifact_id
        or metadata.get("name") != artifact_name
        or metadata.get("digest") != f"sha256:{artifact_digest}"
        or metadata.get("expired") is not False
        or workflow_run.get("id") != run_id
        or workflow_run.get("head_sha") != head_sha
    ):
        raise HandoffError("release artifact does not match this workflow run")


def extract_verified_archive(
    archive: Path,
    destination: Path,
    *,
    expected_digest: str,
    artifact_names: tuple[str, str, str],
) -> None:
    actual_digest = _sha256(archive)
    if actual_digest != expected_digest:
        raise HandoffError("downloaded release artifact failed SHA-256 verification")
    expected_names = ("SHA256SUMS", *artifact_names)
    if len(set(expected_names)) != 4 or any(
        Path(name).name != name for name in expected_names
    ):
        raise HandoffError("release handoff names must be unique plain filenames")
    if destination.exists() or destination.is_symlink():
        raise HandoffError("release handoff destination already exists")

    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    try:
        with zipfile.ZipFile(archive) as handoff:
            entries = handoff.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != 4 or set(names) != set(expected_names):
                raise HandoffError("release handoff contains an unexpected file set")
            for entry in entries:
                path = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                if (
                    entry.is_dir()
                    or path.is_absolute()
                    or len(path.parts) != 1
                    or path.name != entry.filename
                    or stat.S_ISLNK(mode)
                ):
                    raise HandoffError("release handoff contains an unsafe entry")
                with (
                    handoff.open(entry) as source,
                    (temporary / entry.filename).open("xb") as target,
                ):
                    shutil.copyfileobj(source, target, length=_BUFFER_SIZE)

        checksum_bytes = b"".join(
            f"{_sha256(temporary / name)}  {name}\n".encode() for name in artifact_names
        )
        if (temporary / "SHA256SUMS").read_bytes() != checksum_bytes:
            raise HandoffError(
                "release handoff checksum manifest does not match its files"
            )
        temporary.rename(destination)
    except (
        OSError,
        RuntimeError,
        ValueError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ) as error:
        raise HandoffError(
            "release handoff archive could not be extracted safely"
        ) from error
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--artifact-id", required=True, type=int)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--artifact-digest", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--sdist", required=True)
    parser.add_argument("--archive", required=True)
    args = parser.parse_args(argv)
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("release handoff download failed: GH_TOKEN is required", file=sys.stderr)
        return 1
    try:
        expected_digest = _normalized_digest(args.artifact_digest)
        if args.artifact_id <= 0 or args.run_id <= 0:
            raise HandoffError("artifact and workflow run IDs must be positive")
        api_url = _safe_https_url(args.api_url, description="GitHub API URL").rstrip(
            "/"
        )
        repository = urllib.parse.quote(args.repository, safe="/")
        artifact_url = (
            f"{api_url}/repos/{repository}/actions/artifacts/{args.artifact_id}"
        )
        metadata = _authenticated_json(artifact_url, token)
        validate_metadata(
            metadata,
            artifact_id=args.artifact_id,
            artifact_name=args.artifact_name,
            artifact_digest=expected_digest,
            run_id=args.run_id,
            head_sha=args.head_sha,
        )
        redirect = _artifact_redirect(f"{artifact_url}/zip", token)
        args.destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="release-handoff-download-", dir=args.destination.parent
        ) as download_directory:
            downloaded = Path(download_directory) / "release-handoff.zip"
            _download_signed(redirect, downloaded)
            extract_verified_archive(
                downloaded,
                args.destination,
                expected_digest=expected_digest,
                artifact_names=(args.wheel, args.sdist, args.archive),
            )
    except HandoffError as error:
        print(f"release handoff download failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
