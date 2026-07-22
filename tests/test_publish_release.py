from __future__ import annotations

import json
import importlib.util
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "publish_release.py"
SPEC = importlib.util.spec_from_file_location("publish_release", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
publish_release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = publish_release
SPEC.loader.exec_module(publish_release)


@dataclass(frozen=True)
class _HTTPResponse:
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class _RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


class _LocalHTTPServer:
    def __init__(self, respond: Callable[[_RecordedRequest], _HTTPResponse]) -> None:
        self._respond = respond
        self.requests: list[_RecordedRequest] = []
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> _LocalHTTPServer:
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._server.shutdown()
        self._thread.join()
        self._server.server_close()

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def _respond(self) -> None:
                content_length = int(self.headers.get("Content-Length", "0"))
                request = _RecordedRequest(
                    method=self.command,
                    path=self.path,
                    headers=dict(self.headers.items()),
                    body=self.rfile.read(content_length),
                )
                fixture.requests.append(request)
                response = fixture._respond(request)
                self.send_response(response.status)
                for name, value in response.headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(response.body)))
                self.end_headers()
                self.wfile.write(response.body)

            do_GET = _respond
            do_PATCH = _respond
            do_POST = _respond

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        return Handler


def _http_response(
    status: int, *, headers: dict[str, str] | None = None, body: bytes = b""
) -> _HTTPResponse:
    return _HTTPResponse(status=status, headers=headers or {}, body=body)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_authenticated_client_rejects_cross_origin_redirect_without_replay(
    status: int,
) -> None:
    with _LocalHTTPServer(
        lambda request: _http_response(
            200,
            headers={"Content-Type": "application/json"},
            body=json.dumps({"unexpected": request.path}).encode(),
        )
    ) as redirected:
        with _LocalHTTPServer(
            lambda _request: _http_response(
                status,
                headers={"Location": f"{redirected.url}/stolen"},
                body=b'{"message":"Bearer contents-token"}',
            )
        ) as source:
            client = publish_release._GitHubClient("contents-token", source.url)

            with pytest.raises(
                publish_release.RedirectRejectedError,
                match=rf"refused HTTP redirect \({status}\)",
            ) as error:
                client.request_json("POST", "mutate", payload={"draft": True})

    assert "contents-token" not in str(error.value)
    assert [(request.method, request.path) for request in source.requests] == [
        ("POST", "/mutate")
    ]
    assert source.requests[0].headers["Authorization"] == "Bearer contents-token"
    assert source.requests[0].body == b'{"draft":true}'
    assert redirected.requests == []


def test_authenticated_client_rejects_same_origin_redirect() -> None:
    with _LocalHTTPServer(
        lambda _request: _http_response(
            307,
            headers={"Location": f"{source.url}/follow-up"},
            body=b"redirect",
        )
    ) as source:
        client = publish_release._GitHubClient("contents-token", source.url)

        with pytest.raises(
            publish_release.RedirectRejectedError,
            match=r"refused HTTP redirect \(307\)",
        ):
            client.request_json("PATCH", "same-origin", payload={"draft": False})

    assert [(request.method, request.path) for request in source.requests] == [
        ("PATCH", "/same-origin")
    ]
    assert source.requests[0].headers["Authorization"] == "Bearer contents-token"


def test_authenticated_client_preserves_normal_and_error_handling() -> None:
    def respond(request: _RecordedRequest) -> _HTTPResponse:
        if request.path == "/ok":
            return _http_response(
                200,
                headers={"Content-Type": "application/json"},
                body=b'{"result":"ok"}',
            )
        return _http_response(404, body=b'{"message":"missing"}')

    with _LocalHTTPServer(respond) as server:
        client = publish_release._GitHubClient("contents-token", server.url)

        assert client.request_json("GET", "ok") == {"result": "ok"}
        with pytest.raises(publish_release.ApiError, match="returned 404: .*missing"):
            client.request_json("GET", "missing")

    assert [(request.method, request.path) for request in server.requests] == [
        ("GET", "/ok"),
        ("GET", "/missing"),
    ]
    assert all(
        request.headers["Authorization"] == "Bearer contents-token"
        for request in server.requests
    )


class _RecordedJSONClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str]] = []

    def request_json(self, method: str, url: str) -> object:
        self.requests.append((method, url))
        return self.responses.pop(0)


def _release_api_with_contents(contents: _RecordedJSONClient) -> Any:
    api = object.__new__(publish_release.GitHubReleaseAPI)
    api._repository_path = "repos/example/protocyte"
    api._contents = contents
    return api


def test_live_tag_resolution_accepts_a_lightweight_tag() -> None:
    target = "a" * 40
    contents = _RecordedJSONClient(
        [
            {
                "ref": "refs/tags/releases/v1.2.3",
                "object": {"type": "commit", "sha": target},
            }
        ]
    )
    api = _release_api_with_contents(contents)

    assert api.resolve_tag_target("releases/v1.2.3") == target
    assert contents.requests == [
        ("GET", "repos/example/protocyte/git/ref/tags/releases%2Fv1.2.3")
    ]


def test_live_trusted_branch_resolution_requires_a_direct_commit() -> None:
    target = "e" * 40
    contents = _RecordedJSONClient(
        [
            {
                "ref": "refs/heads/main",
                "object": {"type": "commit", "sha": target},
            }
        ]
    )
    api = _release_api_with_contents(contents)

    assert api.resolve_branch_target("main") == target
    assert contents.requests == [
        ("GET", "repos/example/protocyte/git/ref/heads/main")
    ]


def test_live_tag_resolution_peels_nested_annotated_tags() -> None:
    outer = "b" * 40
    inner = "c" * 40
    target = "d" * 40
    contents = _RecordedJSONClient(
        [
            {
                "ref": "refs/tags/v1.2.3",
                "object": {"type": "tag", "sha": outer},
            },
            {"sha": outer, "object": {"type": "tag", "sha": inner}},
            {"sha": inner, "object": {"type": "commit", "sha": target}},
        ]
    )
    api = _release_api_with_contents(contents)

    assert api.resolve_tag_target("v1.2.3") == target
    assert contents.requests == [
        ("GET", "repos/example/protocyte/git/ref/tags/v1.2.3"),
        ("GET", f"repos/example/protocyte/git/tags/{outer}"),
        ("GET", f"repos/example/protocyte/git/tags/{inner}"),
    ]


def _release(
    release_id: int,
    *,
    tag: str = "v1.2.3",
    draft: bool,
    prerelease: bool = False,
    immutable: bool = False,
) -> dict[str, Any]:
    return {
        "id": release_id,
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "immutable": immutable,
        "upload_url": (
            "https://uploads.github.com/repos/example/protocyte/releases/"
            f"{release_id}/assets{{?name,label}}"
        ),
    }


class FakeReleaseAPI:
    def __init__(self) -> None:
        self.policy_enabled = True
        self.tag_target = "a" * 40
        self.branch_target = "e" * 40
        self.releases: list[dict[str, Any]] = []
        self.assets: dict[int, list[dict[str, Any]]] = {}
        self.successful_mutations: list[tuple[str, int, str | None]] = []
        self.create_race = False
        self.competing_release_after_create = False
        self.publish_before_next_state_read = False
        self.disable_policy_after_create = False
        self.retarget_after_create = False
        self.retarget_after_final_upload = False
        self.inject_asset_at_final_boundary = False
        self.inject_asset_inside_publish = False

    def immutable_releases_enabled(self) -> bool:
        return self.policy_enabled

    def default_branch(self) -> str:
        return "main"

    def resolve_branch_target(self, branch: str) -> str:
        assert branch == "main"
        return self.branch_target

    def resolve_tag_target(self, tag: str) -> str:
        assert tag == "v1.2.3"
        if self.inject_asset_at_final_boundary and len(self.assets.get(41, [])) == 3:
            self.assets[41].append(
                {
                    "name": "injected.txt",
                    "state": "uploaded",
                    "size": 8,
                    "digest": f"sha256:{'b' * 64}",
                }
            )
            self.inject_asset_at_final_boundary = False
        return self.tag_target

    def list_releases(self) -> list[dict[str, Any]]:
        return [release.copy() for release in self.releases]

    def create_release(self, spec: publish_release.ReleaseSpec) -> dict[str, Any]:
        if self.create_race:
            self.releases.append(
                _release(99, tag=spec.tag, draft=False, immutable=True)
            )
            raise publish_release.ApiError(
                "POST", "https://api.github.com/releases", 422, "already exists"
            )

        created = _release(
            41,
            tag=spec.tag,
            draft=True,
            prerelease=spec.prerelease,
        )
        self.releases.append(created)
        if self.competing_release_after_create:
            self.releases.append(
                _release(99, tag=spec.tag, draft=False, immutable=True)
            )
        self.assets[41] = []
        self.successful_mutations.append(("create", 41, None))
        if self.disable_policy_after_create:
            self.policy_enabled = False
        if self.retarget_after_create:
            self.tag_target = "b" * 40
        return created.copy()

    def get_release(self, release_id: int) -> dict[str, Any]:
        release = next(item for item in self.releases if item["id"] == release_id)
        if self.publish_before_next_state_read:
            release["draft"] = False
            release["immutable"] = True
            self.publish_before_next_state_read = False
        return release.copy()

    def list_assets(self, release_id: int) -> list[dict[str, Any]]:
        return [asset.copy() for asset in self.assets[release_id]]

    def upload_asset(
        self,
        release_id: int,
        upload_url: str,
        artifact: publish_release.Artifact,
    ) -> dict[str, Any]:
        assert f"/releases/{release_id}/assets" in upload_url
        asset = {
            "name": artifact.name,
            "state": "uploaded",
            "size": artifact.size,
            "digest": artifact.digest,
        }
        self.assets[release_id].append(asset)
        self.successful_mutations.append(("upload", release_id, artifact.name))
        if self.retarget_after_final_upload and len(self.assets[release_id]) == 3:
            self.tag_target = "b" * 40
        return asset.copy()

    def publish_release(self, release_id: int) -> dict[str, Any]:
        release = next(item for item in self.releases if item["id"] == release_id)
        if self.inject_asset_inside_publish:
            self.assets[release_id].append(
                {
                    "name": "injected-after-list.txt",
                    "state": "uploaded",
                    "size": 8,
                    "digest": f"sha256:{'c' * 64}",
                }
            )
        release["draft"] = False
        release["immutable"] = True
        self.successful_mutations.append(("publish", release_id, None))
        return release.copy()


def _spec(*, prerelease: bool = False) -> publish_release.ReleaseSpec:
    return publish_release.ReleaseSpec(
        repository="example/protocyte",
        tag="v1.2.3",
        target="a" * 40,
        trusted_branch="main",
        trusted_target="e" * 40,
        prerelease=prerelease,
    )


def _artifacts(tmp_path: Path) -> list[Path]:
    artifacts = [
        tmp_path / "protocyte-1.2.3-py3-none-any.whl",
        tmp_path / "protocyte-1.2.3.tar.gz",
        tmp_path / "protocyte-1.2.3-cmake-prefix.tar.gz",
    ]
    for index, artifact in enumerate(artifacts):
        artifact.write_bytes(f"artifact-{index}\n".encode())
    return artifacts


@pytest.mark.parametrize("prerelease", [False, True])
def test_release_transaction_binds_every_mutation_to_created_id_and_state(
    tmp_path: Path, prerelease: bool
) -> None:
    api = FakeReleaseAPI()

    release_id = publish_release.publish(
        api, _spec(prerelease=prerelease), _artifacts(tmp_path)
    )

    assert release_id == 41
    assert api.successful_mutations == [
        ("create", 41, None),
        ("upload", 41, "protocyte-1.2.3-py3-none-any.whl"),
        ("upload", 41, "protocyte-1.2.3.tar.gz"),
        ("upload", 41, "protocyte-1.2.3-cmake-prefix.tar.gz"),
        ("publish", 41, None),
    ]
    assert api.releases[0]["immutable"] is True
    assert api.releases[0]["prerelease"] is prerelease


@pytest.mark.parametrize("draft", [False, True])
def test_existing_release_is_terminal_without_mutation(
    tmp_path: Path, draft: bool
) -> None:
    api = FakeReleaseAPI()
    api.releases.append(_release(17, draft=draft, immutable=not draft))

    with pytest.raises(publish_release.ReleaseError, match="never mutates existing"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == []


def test_absent_to_public_race_does_not_mutate_competing_release(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.create_race = True

    with pytest.raises(publish_release.ReleaseError, match="existence race"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == []
    assert api.releases == [_release(99, draft=False, immutable=True)]
    assert api.assets == {}


def test_duplicate_creation_race_aborts_before_uploading_to_owned_draft(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.competing_release_after_create = True

    with pytest.raises(publish_release.ReleaseError, match="raced"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == [("create", 41, None)]
    assert api.assets == {41: []}
    assert api.releases[1] == _release(99, draft=False, immutable=True)


def test_draft_to_public_race_aborts_before_asset_or_release_mutation(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.publish_before_next_state_read = True

    with pytest.raises(publish_release.ReleaseError, match="expected draft state"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == [("create", 41, None)]
    assert api.assets == {41: []}
    assert api.releases[0]["draft"] is False
    assert api.releases[0]["immutable"] is True


def test_disabled_immutable_release_policy_fails_before_mutation(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.policy_enabled = False

    with pytest.raises(publish_release.ReleaseError, match="immutability"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == []


def test_initial_tag_target_mismatch_fails_before_mutation(tmp_path: Path) -> None:
    api = FakeReleaseAPI()
    api.tag_target = "b" * 40

    with pytest.raises(publish_release.ReleaseError, match="not expected target"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == []


def test_tag_retarget_after_creation_fails_before_upload(tmp_path: Path) -> None:
    api = FakeReleaseAPI()
    api.retarget_after_create = True

    with pytest.raises(publish_release.ReleaseError, match="not expected target"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == [("create", 41, None)]
    assert api.assets == {41: []}


def test_tag_retarget_at_publication_boundary_fails_before_publish(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.retarget_after_final_upload = True

    with pytest.raises(publish_release.ReleaseError, match="not expected target"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert all(mutation[0] != "publish" for mutation in api.successful_mutations)
    assert api.releases[0]["draft"] is True


def test_unexpected_asset_observed_during_final_preflight_fails_before_publish(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.inject_asset_at_final_boundary = True

    with pytest.raises(publish_release.ReleaseError, match="exactly the expected"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert all(mutation[0] != "publish" for mutation in api.successful_mutations)
    assert api.releases[0]["draft"] is True


def test_external_writer_after_last_read_is_detected_only_after_publication(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.inject_asset_inside_publish = True

    with pytest.raises(publish_release.ReleaseError, match="exactly the expected"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations[-1] == ("publish", 41, None)
    assert api.releases[0]["draft"] is False
    assert api.releases[0]["immutable"] is True
    assert api.assets[41][-1]["name"] == "injected-after-list.txt"


def test_untrusted_workflow_revision_fails_before_release_mutation(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.branch_target = "f" * 40

    with pytest.raises(publish_release.ReleaseError, match="live trusted"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == []


def test_immutable_policy_drift_after_creation_aborts_before_upload(
    tmp_path: Path,
) -> None:
    api = FakeReleaseAPI()
    api.disable_policy_after_create = True

    with pytest.raises(publish_release.ReleaseError, match="changed during creation"):
        publish_release.publish(api, _spec(), _artifacts(tmp_path))

    assert api.successful_mutations == [("create", 41, None)]
    assert api.assets == {41: []}
