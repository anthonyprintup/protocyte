from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIRECTORY = REPO_ROOT / ".github" / "scripts"
sys.path.insert(0, str(SCRIPT_DIRECTORY))
SPEC = importlib.util.spec_from_file_location(
    "check_release_policy", SCRIPT_DIRECTORY / "check_release_policy.py"
)
assert SPEC is not None
assert SPEC.loader is not None
check_release_policy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check_release_policy
SPEC.loader.exec_module(check_release_policy)


@dataclass
class FakePolicyAPI:
    default_branch: str = "main"
    branch_sha: str = "a" * 40
    immutable: bool = True

    def repository(self) -> dict[str, Any]:
        return {"default_branch": self.default_branch}

    def branch_target(self, branch: str) -> str:
        assert branch == "main"
        return self.branch_sha

    def immutable_releases_enabled(self) -> bool:
        return self.immutable

    def legacy_workflow(self, workflow_id: int) -> dict[str, Any]:
        return {
            "id": workflow_id,
            "path": ".github/workflows/release.yml",
            "state": "disabled_manually",
        }

    def environment(self, name: str) -> dict[str, Any]:
        return {
            "name": name,
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
            "protection_rules": [
                {
                    "type": "required_reviewers",
                    "prevent_self_review": True,
                    "reviewers": [{"type": "Team", "reviewer": {"id": 7}}],
                }
            ],
        }

    def deployment_branch_policies(self, name: str) -> dict[str, Any]:
        assert name == "release"
        return {
            "total_count": 1,
            "branch_policies": [
                {"id": 11, "name": "main", "type": "branch"}
            ],
        }

    def ruleset(self, ruleset_id: int) -> dict[str, Any]:
        return {
            "id": ruleset_id,
            "target": "tag",
            "enforcement": "active",
            "bypass_actors": [],
            "conditions": {
                "ref_name": {"include": ["refs/tags/v*"], "exclude": []}
            },
            "rules": [{"type": "update"}, {"type": "deletion"}],
        }


def _spec(**overrides: object) -> check_release_policy.PolicySpec:
    values = {
        "repository": "example/protocyte",
        "environment": "release",
        "default_branch": "main",
        "workflow_ref": "refs/heads/main",
        "workflow_target": "a" * 40,
        "tag_ruleset_id": 19,
        "legacy_workflow_id": 23,
    }
    values.update(overrides)
    return check_release_policy.PolicySpec(**values)


def test_release_policy_accepts_exact_single_writer_configuration() -> None:
    check_release_policy.verify(FakePolicyAPI(), _spec())


def test_repository_workflow_policy_accepts_the_trusted_checkout() -> None:
    check_release_policy.verify_repository_workflows(REPO_ROOT)


def test_repository_workflow_policy_rejects_a_competing_writer(
    tmp_path: Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "publish-release.yml").write_text(
        "on:\n  workflow_dispatch:\njobs:\n  publish:\n"
        "    permissions:\n      contents: write\n",
        encoding="utf-8",
    )
    (workflows / "historical-bypass.yml").write_text(
        "on:\n  push:\n    tags:\n      - 'v*'\njobs:\n  publish:\n"
        "    permissions:\n      contents: write\n",
        encoding="utf-8",
    )
    (workflows / "release.yml").write_text(
        check_release_policy.LEGACY_RELEASE_WORKFLOW_STUB,
        encoding="utf-8",
    )

    with pytest.raises(
        check_release_policy.ReleaseError, match="exactly publish-release.yml"
    ):
        check_release_policy.verify_repository_workflows(tmp_path)


def test_repository_workflow_policy_rejects_tag_triggered_publication(
    tmp_path: Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "publish-release.yml").write_text(
        "on:\n  workflow_dispatch:\n  push:\n    tags:\n      - 'v*'\n"
        "jobs:\n  publish:\n    permissions:\n      contents: write\n",
        encoding="utf-8",
    )
    (workflows / "release.yml").write_text(
        check_release_policy.LEGACY_RELEASE_WORKFLOW_STUB,
        encoding="utf-8",
    )

    with pytest.raises(check_release_policy.ReleaseError, match="tag event"):
        check_release_policy.verify_repository_workflows(tmp_path)


@pytest.mark.parametrize(
    "legacy_text",
    [
        None,
        check_release_policy.LEGACY_RELEASE_WORKFLOW_STUB.replace(
            "workflow_call:", "workflow_dispatch:"
        ),
        check_release_policy.LEGACY_RELEASE_WORKFLOW_STUB.replace(
            "contents: none", "contents: read"
        ),
        check_release_policy.LEGACY_RELEASE_WORKFLOW_STUB.replace(
            "if: ${{ false }}", "if: ${{ true }}"
        ),
    ],
)
def test_repository_workflow_policy_requires_the_exact_inert_legacy_stub(
    tmp_path: Path,
    legacy_text: str | None,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "publish-release.yml").write_text(
        "on:\n  workflow_dispatch:\njobs:\n  publish:\n"
        "    permissions:\n      contents: write\n",
        encoding="utf-8",
    )
    if legacy_text is not None:
        (workflows / "release.yml").write_text(legacy_text, encoding="utf-8")

    with pytest.raises(check_release_policy.ReleaseError, match="exact inert stub"):
        check_release_policy.verify_repository_workflows(tmp_path)


@pytest.mark.parametrize(
    ("spec_overrides", "api_mutation", "message"),
    [
        ({"workflow_ref": "refs/tags/v1.2.3"}, None, "must run from"),
        ({"workflow_target": "b" * 40}, None, "live default-branch"),
        ({}, lambda api: setattr(api, "immutable", False), "immutability"),
    ],
)
def test_release_policy_rejects_untrusted_source_or_disabled_immutability(
    spec_overrides: dict[str, object],
    api_mutation: object,
    message: str,
) -> None:
    api = FakePolicyAPI()
    if callable(api_mutation):
        api_mutation(api)
    with pytest.raises(check_release_policy.ReleaseError, match=message):
        check_release_policy.verify(api, _spec(**spec_overrides))


def test_release_policy_rejects_a_tag_enabled_environment() -> None:
    api = FakePolicyAPI()

    def policies(_name: str) -> dict[str, Any]:
        return {
            "total_count": 2,
            "branch_policies": [
                {"id": 11, "name": "main", "type": "branch"},
                {"id": 12, "name": "v*", "type": "tag"},
            ],
        }

    api.deployment_branch_policies = policies  # type: ignore[method-assign]
    with pytest.raises(check_release_policy.ReleaseError, match="only the exact"):
        check_release_policy.verify(api, _spec())


@pytest.mark.parametrize("state", ["active", "disabled_inactivity", None])
def test_release_policy_rejects_an_enabled_or_unverifiable_legacy_workflow(
    state: str | None,
) -> None:
    api = FakePolicyAPI()

    def legacy_workflow(workflow_id: int) -> dict[str, Any]:
        value: dict[str, Any] = {
            "id": workflow_id,
            "path": ".github/workflows/release.yml",
        }
        if state is not None:
            value["state"] = state
        return value

    api.legacy_workflow = legacy_workflow  # type: ignore[method-assign]
    with pytest.raises(check_release_policy.ReleaseError, match="disabled manually"):
        check_release_policy.verify(api, _spec())


@pytest.mark.parametrize(
    "identity_change",
    [
        {"id": 24},
        {"path": ".github/workflows/publish-release.yml"},
    ],
)
def test_release_policy_rejects_the_wrong_legacy_workflow_identity(
    identity_change: dict[str, object],
) -> None:
    api = FakePolicyAPI()
    original = api.legacy_workflow

    def legacy_workflow(workflow_id: int) -> dict[str, Any]:
        value = original(workflow_id)
        value.update(identity_change)
        return value

    api.legacy_workflow = legacy_workflow  # type: ignore[method-assign]
    with pytest.raises(check_release_policy.ReleaseError, match="disabled manually"):
        check_release_policy.verify(api, _spec())


def test_release_policy_rejects_self_review_or_missing_reviewers() -> None:
    api = FakePolicyAPI()

    def environment(name: str) -> dict[str, Any]:
        value = FakePolicyAPI().environment(name)
        value["protection_rules"][0]["prevent_self_review"] = False
        return value

    api.environment = environment  # type: ignore[method-assign]
    with pytest.raises(check_release_policy.ReleaseError, match="non-self reviewer"):
        check_release_policy.verify(api, _spec())


@pytest.mark.parametrize(
    "ruleset_change",
    [
        {"enforcement": "evaluate"},
        {"bypass_actors": [{"actor_type": "RepositoryRole", "actor_id": 5}]},
        {"rules": [{"type": "deletion"}]},
        {
            "conditions": {
                "ref_name": {"include": ["refs/tags/*"], "exclude": []}
            }
        },
    ],
)
def test_release_policy_rejects_an_unsafe_tag_ruleset(
    ruleset_change: dict[str, object],
) -> None:
    api = FakePolicyAPI()
    original = api.ruleset

    def ruleset(ruleset_id: int) -> dict[str, Any]:
        value = original(ruleset_id)
        value.update(ruleset_change)
        return value

    api.ruleset = ruleset  # type: ignore[method-assign]
    with pytest.raises(check_release_policy.ReleaseError):
        check_release_policy.verify(api, _spec())


def test_release_policy_rejects_hidden_tag_ruleset_bypass_actors() -> None:
    api = FakePolicyAPI()
    original = api.ruleset

    def ruleset(ruleset_id: int) -> dict[str, Any]:
        value = original(ruleset_id)
        value.pop("bypass_actors")
        return value

    api.ruleset = ruleset  # type: ignore[method-assign]
    with pytest.raises(check_release_policy.ReleaseError, match="visible and exactly"):
        check_release_policy.verify(api, _spec())
