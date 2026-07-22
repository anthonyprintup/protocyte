#!/usr/bin/env python3
"""Create and publish one immutable GitHub release without tag-based upserts."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
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


class RedirectRejectedError(ReleaseError):
    """An authenticated GitHub request received an unsafe redirect."""

    def __init__(self, method: str, url: str, status: int) -> None:
        super().__init__(
            f"GitHub API {method} {url} refused HTTP redirect ({status}); "
            "authenticated requests never follow redirects"
        )


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Reject redirects before urllib can replay an authenticated request."""

    def _reject(
        self,
        request: urllib.request.Request,
        response: object,
        code: int,
        message: str,
        headers: object,
    ) -> None:
        del response, message, headers
        raise RedirectRejectedError(request.get_method(), request.full_url, code)

    http_error_301 = _reject
    http_error_302 = _reject
    http_error_303 = _reject
    http_error_307 = _reject
    http_error_308 = _reject

    def http_error_default(
        self,
        request: urllib.request.Request,
        response: object,
        code: int,
        message: str,
        headers: object,
    ) -> None:
        if 300 <= code < 400:
            self._reject(request, response, code, message, headers)
        return None


@dataclass(frozen=True)
class ReleaseSpec:
    repository: str
    tag: str
    target: str
    trusted_branch: str
    trusted_target: str
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

    def default_branch(self) -> str: ...

    def resolve_branch_target(self, branch: str) -> str: ...

    def resolve_tag_target(self, tag: str) -> str: ...

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
        self._opener = urllib.request.build_opener(_RejectRedirects())

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
            with self._opener.open(request, timeout=60) as response:
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

    def default_branch(self) -> str:
        response = self._contents.request_json("GET", self._repository_path)
        if not isinstance(response, dict) or not isinstance(
            response.get("default_branch"), str
        ):
            raise ReleaseError("GitHub returned invalid repository metadata")
        return response["default_branch"]

    def resolve_branch_target(self, branch: str) -> str:
        target = self._resolve_ref("heads", branch)
        object_type, object_sha = _git_object(target)
        if object_type != "commit":
            raise ReleaseError("default branch does not resolve directly to a commit")
        return object_sha

    def resolve_tag_target(self, tag: str) -> str:
        target = self._resolve_ref("tags", tag)
        visited: set[str] = set()
        for _ in range(32):
            object_type, object_sha = _git_object(target)
            if object_type == "commit":
                return object_sha
            if object_type != "tag":
                raise ReleaseError(
                    f"release tag resolves to unsupported Git object type: {object_type}"
                )
            if object_sha in visited:
                raise ReleaseError("release tag contains an annotated-tag cycle")
            visited.add(object_sha)
            tag_object = self._contents.request_json(
                "GET", f"{self._repository_path}/git/tags/{object_sha}"
            )
            if not isinstance(tag_object, dict) or tag_object.get("sha") != object_sha:
                raise ReleaseError("GitHub returned an invalid annotated tag object")
            target = tag_object.get("object")
        raise ReleaseError("release tag contains too many nested annotated tags")

    def _resolve_ref(self, namespace: str, name: str) -> object:
        quoted_name = urllib.parse.quote(name, safe="")
        response = self._contents.request_json(
            "GET", f"{self._repository_path}/git/ref/{namespace}/{quoted_name}"
        )
        if (
            not isinstance(response, dict)
            or response.get("ref") != f"refs/{namespace}/{name}"
        ):
            raise ReleaseError("GitHub returned an invalid trusted Git reference")
        return response.get("object")

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


def _git_object(value: object) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise ReleaseError("GitHub returned an invalid release tag target")
    object_type = value.get("type")
    object_sha = value.get("sha")
    if not isinstance(object_type, str) or not isinstance(object_sha, str):
        raise ReleaseError("GitHub returned an invalid release tag target")
    if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", object_sha) is None:
        raise ReleaseError("GitHub returned an invalid release tag object ID")
    return object_type, object_sha


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


def _require_tag_target(api: ReleaseAPI, spec: ReleaseSpec) -> None:
    actual = api.resolve_tag_target(spec.tag)
    if actual != spec.target:
        raise ReleaseError(
            f"release tag {spec.tag} resolves to {actual}, not expected target "
            f"{spec.target}; refusing to mutate a release"
        )


def _require_trusted_source(api: ReleaseAPI, spec: ReleaseSpec) -> None:
    if api.default_branch() != spec.trusted_branch:
        raise ReleaseError(
            f"repository default branch is not trusted branch {spec.trusted_branch}"
        )
    actual = api.resolve_branch_target(spec.trusted_branch)
    if actual != spec.trusted_target:
        raise ReleaseError(
            "publication code is not the live trusted default-branch revision"
        )


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

    _require_trusted_source(api, spec)
    _require_tag_target(api, spec)
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

    _require_trusted_source(api, spec)
    _require_tag_target(api, spec)
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

    _require_trusted_source(api, spec)
    _require_tag_target(api, spec)
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
        _require_trusted_source(api, spec)
        _require_tag_target(api, spec)
        uploaded_asset = api.upload_asset(release_id, upload_url, artifact)
        _require_exact_assets([uploaded_asset], [artifact])
        uploaded.append(artifact)
        _require_exact_assets(api.list_assets(release_id), uploaded)

    _require_current_draft(api, spec, release_id)
    _require_only_owned_draft(api, spec, release_id)
    _require_trusted_source(api, spec)
    _require_tag_target(api, spec)
    _require_exact_assets(api.list_assets(release_id), artifacts)
    if not api.immutable_releases_enabled():
        raise ReleaseError(
            "release immutability changed before publication; the populated draft "
            "requires manual inspection and cleanup"
        )
    # GitHub does not support conditional PATCH requests for release publication.
    # This last read is therefore a drift detector, not a lock: the repository's
    # single-writer workflow and credential policy is the publication boundary.
    _require_trusted_source(api, spec)
    _require_tag_target(api, spec)

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
    parser.add_argument("--trusted-branch", required=True)
    parser.add_argument("--trusted-target", required=True)
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
        trusted_branch=args.trusted_branch,
        trusted_target=args.trusted_target,
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
