#!/usr/bin/env python3
"""Create and publish one immutable GitHub release without tag-based upserts."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


API_VERSION = "2026-03-10"


class ReleaseError(RuntimeError):
    """Fail-closed release transaction error."""


class ApiError(ReleaseError):
    """GitHub returned an unsuccessful HTTP response."""

    def __init__(self, method: str, url: str, status: int, response: str) -> None:
        message = response.strip() or "empty response"
        super().__init__(f"GitHub API {method} {url} returned {status}: {message}")
        self.status = status


@dataclass(frozen=True)
class ReleaseSpec:
    repository: str
    tag: str
    target: str
    prerelease: bool


@dataclass(frozen=True)
class Artifact:
    path: Path
    name: str
    size: int
    digest: str
    content_type: str

    @classmethod
    def from_path(cls, path: Path) -> Artifact:
        if not path.is_file():
            raise ReleaseError(f"release artifact is not a file: {path}")
        contents = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return cls(
            path=path,
            name=path.name,
            size=len(contents),
            digest=f"sha256:{hashlib.sha256(contents).hexdigest()}",
            content_type=content_type,
        )


class ReleaseAPI(Protocol):
    def immutable_releases_enabled(self) -> bool: ...

    def list_releases(self) -> list[dict[str, Any]]: ...

    def create_release(self, spec: ReleaseSpec) -> dict[str, Any]: ...

    def get_release(self, release_id: int) -> dict[str, Any]: ...

    def list_assets(self, release_id: int) -> list[dict[str, Any]]: ...

    def upload_asset(
        self, release_id: int, upload_url: str, artifact: Artifact
    ) -> dict[str, Any]: ...

    def publish_release(self, release_id: int) -> dict[str, Any]: ...


class _GitHubClient:
    def __init__(self, token: str, api_url: str) -> None:
        self._token = token
        self.api_url = api_url.rstrip("/")

    def request_json(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, object] | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
    ) -> Any:
        if not url.startswith("https://"):
            url = f"{self.api_url}/{url.lstrip('/')}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "User-Agent": "protocyte-release-workflow",
            "X-GitHub-Api-Version": API_VERSION,
        }
        data = content
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif content_type is not None:
            headers["Content-Type"] = content_type

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            response_body = error.read().decode("utf-8", errors="replace")
            raise ApiError(method, url, error.code, response_body) from error
        except urllib.error.URLError as error:
            raise ReleaseError(
                f"GitHub API {method} {url} failed: {error.reason}"
            ) from error

        if not response_body:
            return None
        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise ReleaseError(
                f"GitHub API {method} {url} returned invalid JSON"
            ) from error


class GitHubReleaseAPI:
    def __init__(
        self,
        repository: str,
        release_token: str,
        policy_token: str,
        api_url: str,
    ) -> None:
        try:
            owner, name = repository.split("/", maxsplit=1)
        except ValueError as error:
            raise ReleaseError(
                f"repository must use OWNER/NAME syntax: {repository}"
            ) from error
        if not owner or not name or "/" in name:
            raise ReleaseError(f"repository must use OWNER/NAME syntax: {repository}")

        quoted_owner = urllib.parse.quote(owner, safe="")
        quoted_name = urllib.parse.quote(name, safe="")
        self._repository_path = f"repos/{quoted_owner}/{quoted_name}"
        self._contents = _GitHubClient(release_token, api_url)
        self._policy = _GitHubClient(policy_token, api_url)
        api_location = urllib.parse.urlsplit(api_url)
        if api_location.scheme != "https" or not api_location.netloc:
            raise ReleaseError("GitHub API URL must use HTTPS")
        self._upload_netlocs = {api_location.netloc}
        if api_location.netloc == "api.github.com":
            self._upload_netlocs.add("uploads.github.com")

    def immutable_releases_enabled(self) -> bool:
        try:
            policy = self._policy.request_json(
                "GET", f"{self._repository_path}/immutable-releases"
            )
        except ApiError as error:
            if error.status == 404:
                return False
            raise
        return isinstance(policy, dict) and policy.get("enabled") is True

    def list_releases(self) -> list[dict[str, Any]]:
        releases: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self._contents.request_json(
                "GET",
                f"{self._repository_path}/releases?per_page=100&page={page}",
            )
            if not isinstance(response, list) or not all(
                isinstance(release, dict) for release in response
            ):
                raise ReleaseError("GitHub returned an invalid release list")
            releases.extend(response)
            if len(response) < 100:
                return releases
            page += 1

    def create_release(self, spec: ReleaseSpec) -> dict[str, Any]:
        response = self._contents.request_json(
            "POST",
            f"{self._repository_path}/releases",
            payload={
                "tag_name": spec.tag,
                "target_commitish": spec.target,
                "draft": True,
                "prerelease": spec.prerelease,
                "generate_release_notes": True,
            },
        )
        if not isinstance(response, dict):
            raise ReleaseError("GitHub returned an invalid created release")
        return response

    def get_release(self, release_id: int) -> dict[str, Any]:
        response = self._contents.request_json(
            "GET", f"{self._repository_path}/releases/{release_id}"
        )
        if not isinstance(response, dict):
            raise ReleaseError("GitHub returned an invalid release")
        return response

    def list_assets(self, release_id: int) -> list[dict[str, Any]]:
        response = self._contents.request_json(
            "GET",
            f"{self._repository_path}/releases/{release_id}/assets?per_page=100",
        )
        if not isinstance(response, list) or not all(
            isinstance(asset, dict) for asset in response
        ):
            raise ReleaseError("GitHub returned an invalid release asset list")
        if len(response) == 100:
            raise ReleaseError("release has too many assets for exact verification")
        return response

    def upload_asset(
        self, release_id: int, upload_url: str, artifact: Artifact
    ) -> dict[str, Any]:
        endpoint = upload_url.partition("{")[0]
        parsed = urllib.parse.urlsplit(endpoint)
        expected_path = f"/{self._repository_path}/releases/{release_id}/assets"
        if (
            parsed.scheme != "https"
            or parsed.netloc not in self._upload_netlocs
            or parsed.path != expected_path
        ):
            raise ReleaseError(
                "created release returned an invalid ID-bound upload URL"
            )
        query = urllib.parse.urlencode({"name": artifact.name})
        response = self._contents.request_json(
            "POST",
            urllib.parse.urlunsplit(parsed._replace(query=query)),
            content=artifact.path.read_bytes(),
            content_type=artifact.content_type,
        )
        if not isinstance(response, dict):
            raise ReleaseError("GitHub returned an invalid uploaded asset")
        return response

    def publish_release(self, release_id: int) -> dict[str, Any]:
        response = self._contents.request_json(
            "PATCH",
            f"{self._repository_path}/releases/{release_id}",
            payload={"draft": False},
        )
        if not isinstance(response, dict):
            raise ReleaseError("GitHub returned an invalid published release")
        return response


def _matching_releases(
    releases: list[dict[str, Any]], tag: str
) -> list[dict[str, Any]]:
    return [release for release in releases if release.get("tag_name") == tag]


def _release_id(release: dict[str, Any]) -> int:
    release_id = release.get("id")
    if isinstance(release_id, bool) or not isinstance(release_id, int):
        raise ReleaseError("GitHub release did not contain a numeric ID")
    return release_id


def _require_release_state(
    release: dict[str, Any],
    spec: ReleaseSpec,
    release_id: int,
    *,
    draft: bool,
) -> None:
    if (
        _release_id(release) != release_id
        or release.get("tag_name") != spec.tag
        or release.get("draft") is not draft
        or release.get("prerelease") is not spec.prerelease
    ):
        state = "draft" if draft else "published"
        raise ReleaseError(
            f"release {release_id} no longer matches the expected {state} state"
        )


def _require_only_owned_draft(
    api: ReleaseAPI, spec: ReleaseSpec, release_id: int
) -> None:
    matches = _matching_releases(api.list_releases(), spec.tag)
    if len(matches) != 1:
        raise ReleaseError(
            "release creation raced with another publisher; no assets were mutated. "
            "Inspect and manually delete the workflow-owned draft before retrying"
        )
    _require_release_state(matches[0], spec, release_id, draft=True)


def _require_current_draft(api: ReleaseAPI, spec: ReleaseSpec, release_id: int) -> None:
    _require_release_state(api.get_release(release_id), spec, release_id, draft=True)


def _require_exact_assets(
    actual_assets: list[dict[str, Any]], expected_artifacts: list[Artifact]
) -> None:
    expected = {artifact.name: artifact for artifact in expected_artifacts}
    actual = {asset.get("name"): asset for asset in actual_assets}
    if len(actual) != len(actual_assets) or set(actual) != set(expected):
        raise ReleaseError("draft release does not contain exactly the expected assets")
    for name, artifact in expected.items():
        asset = actual[name]
        if (
            asset.get("state") != "uploaded"
            or asset.get("size") != artifact.size
            or asset.get("digest") != artifact.digest
        ):
            raise ReleaseError(f"release asset does not match local artifact: {name}")


def publish(api: ReleaseAPI, spec: ReleaseSpec, artifact_paths: list[Path]) -> int:
    artifacts = [Artifact.from_path(path) for path in artifact_paths]
    if len({artifact.name for artifact in artifacts}) != len(artifacts):
        raise ReleaseError("release artifact names must be unique")
    if not artifacts:
        raise ReleaseError("at least one release artifact is required")

    if not api.immutable_releases_enabled():
        raise ReleaseError(
            "repository release immutability must be enabled before publishing"
        )

    existing = _matching_releases(api.list_releases(), spec.tag)
    if existing:
        raise ReleaseError(
            f"release {spec.tag} already exists; this workflow never mutates existing "
            "releases. Inspect and manually delete an unpublished draft before retrying"
        )

    try:
        created = api.create_release(spec)
    except ApiError as error:
        if error.status == 422:
            raise ReleaseError(
                "release creation lost an existence race; no existing release was "
                "mutated. Inspect releases before retrying"
            ) from error
        raise

    release_id = _release_id(created)
    _require_release_state(created, spec, release_id, draft=True)
    upload_url = created.get("upload_url")
    if not isinstance(upload_url, str):
        raise ReleaseError("created release did not contain an upload URL")

    if not api.immutable_releases_enabled():
        raise ReleaseError(
            "release immutability changed during creation; the empty draft requires "
            "manual inspection and cleanup"
        )
    _require_only_owned_draft(api, spec, release_id)
    uploaded: list[Artifact] = []
    for artifact in artifacts:
        _require_current_draft(api, spec, release_id)
        _require_exact_assets(api.list_assets(release_id), uploaded)
        uploaded_asset = api.upload_asset(release_id, upload_url, artifact)
        _require_exact_assets([uploaded_asset], [artifact])
        uploaded.append(artifact)
        _require_exact_assets(api.list_assets(release_id), uploaded)

    _require_current_draft(api, spec, release_id)
    _require_only_owned_draft(api, spec, release_id)
    _require_exact_assets(api.list_assets(release_id), artifacts)

    published = api.publish_release(release_id)
    _require_release_state(published, spec, release_id, draft=False)
    if published.get("immutable") is not True:
        raise ReleaseError(f"published release {release_id} is not immutable")
    _require_exact_assets(api.list_assets(release_id), artifacts)
    return release_id


def _parse_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--prerelease", required=True, type=_parse_bool)
    parser.add_argument("artifacts", nargs="+")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    release_token = os.environ.get("GH_TOKEN", "").strip()
    policy_token = os.environ.get("PROTOCYTE_RELEASE_POLICY_TOKEN", "").strip()
    if not release_token:
        print("GH_TOKEN is required", file=sys.stderr)
        return 1
    if not policy_token:
        print("PROTOCYTE_RELEASE_POLICY_TOKEN is required", file=sys.stderr)
        return 1

    spec = ReleaseSpec(
        repository=args.repository,
        tag=args.tag,
        target=args.target,
        prerelease=args.prerelease,
    )
    try:
        api = GitHubReleaseAPI(
            repository=spec.repository,
            release_token=release_token,
            policy_token=policy_token,
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
        release_id = publish(api, spec, [Path(path) for path in args.artifacts])
    except ReleaseError as error:
        print(f"release publication failed: {error}", file=sys.stderr)
        return 1

    print(f"published immutable GitHub release {release_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
