#!/usr/bin/env python3
"""Fail closed unless GitHub enforces Protocyte's single-writer release policy."""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from publish_release import _GitHubClient, ReleaseError


LEGACY_RELEASE_WORKFLOW_STUB = """\
name: Legacy Release (Retired)

on:
  workflow_call:

permissions:
  contents: none

jobs:
  retired:
    if: ${{ false }}
    runs-on: ubuntu-latest
    steps:
      - run: exit 1
"""


@dataclass(frozen=True)
class PolicySpec:
    repository: str
    environment: str
    default_branch: str
    workflow_ref: str
    workflow_target: str
    tag_ruleset_id: int
    legacy_workflow_id: int


class PolicyAPI(Protocol):
    def repository(self) -> dict[str, Any]: ...

    def branch_target(self, branch: str) -> str: ...

    def immutable_releases_enabled(self) -> bool: ...

    def legacy_workflow(self, workflow_id: int) -> dict[str, Any]: ...

    def environment(self, name: str) -> dict[str, Any]: ...

    def deployment_branch_policies(self, name: str) -> dict[str, Any]: ...

    def ruleset(self, ruleset_id: int) -> dict[str, Any]: ...


class GitHubPolicyAPI:
    def __init__(
        self,
        repository: str,
        contents_token: str,
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
        self._contents = _GitHubClient(contents_token, api_url)
        self._policy = _GitHubClient(policy_token, api_url)

    def repository(self) -> dict[str, Any]:
        return self._require_object(
            self._contents.request_json("GET", self._repository_path),
            "repository metadata",
        )

    def branch_target(self, branch: str) -> str:
        quoted_branch = urllib.parse.quote(branch, safe="")
        response = self._require_object(
            self._contents.request_json(
                "GET", f"{self._repository_path}/git/ref/heads/{quoted_branch}"
            ),
            "default-branch reference",
        )
        if response.get("ref") != f"refs/heads/{branch}":
            raise ReleaseError("GitHub returned the wrong default-branch reference")
        target = response.get("object")
        if not isinstance(target, dict) or target.get("type") != "commit":
            raise ReleaseError("GitHub returned an invalid default-branch target")
        sha = target.get("sha")
        if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
            raise ReleaseError("GitHub returned an invalid default-branch object ID")
        return sha

    def immutable_releases_enabled(self) -> bool:
        policy = self._require_object(
            self._policy.request_json(
                "GET", f"{self._repository_path}/immutable-releases"
            ),
            "immutable-release policy",
        )
        return policy.get("enabled") is True

    def legacy_workflow(self, workflow_id: int) -> dict[str, Any]:
        return self._require_object(
            self._policy.request_json(
                "GET", f"{self._repository_path}/actions/workflows/{workflow_id}"
            ),
            "legacy release workflow",
        )

    def environment(self, name: str) -> dict[str, Any]:
        quoted_name = urllib.parse.quote(name, safe="")
        return self._require_object(
            self._policy.request_json(
                "GET", f"{self._repository_path}/environments/{quoted_name}"
            ),
            "release environment",
        )

    def deployment_branch_policies(self, name: str) -> dict[str, Any]:
        quoted_name = urllib.parse.quote(name, safe="")
        return self._require_object(
            self._policy.request_json(
                "GET",
                f"{self._repository_path}/environments/{quoted_name}/"
                "deployment-branch-policies?per_page=100",
            ),
            "release deployment branch policies",
        )

    def ruleset(self, ruleset_id: int) -> dict[str, Any]:
        return self._require_object(
            self._policy.request_json(
                "GET",
                f"{self._repository_path}/rulesets/{ruleset_id}?includes_parents=true",
            ),
            "release tag ruleset",
        )

    @staticmethod
    def _require_object(value: object, description: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ReleaseError(f"GitHub returned invalid {description}")
        return value


def verify(api: PolicyAPI, spec: PolicySpec) -> None:
    expected_ref = f"refs/heads/{spec.default_branch}"
    if spec.workflow_ref != expected_ref:
        raise ReleaseError(
            f"release workflow must run from {expected_ref}, not {spec.workflow_ref}"
        )

    repository = api.repository()
    if repository.get("default_branch") != spec.default_branch:
        raise ReleaseError(
            f"repository default branch must be {spec.default_branch}"
        )
    if api.branch_target(spec.default_branch) != spec.workflow_target:
        raise ReleaseError(
            "release workflow revision is not the live default-branch target"
        )
    legacy_workflow = api.legacy_workflow(spec.legacy_workflow_id)
    if (
        legacy_workflow.get("id") != spec.legacy_workflow_id
        or legacy_workflow.get("path") != ".github/workflows/release.yml"
        or legacy_workflow.get("state") != "disabled_manually"
    ):
        raise ReleaseError(
            "legacy .github/workflows/release.yml must be disabled manually"
        )
    if not api.immutable_releases_enabled():
        raise ReleaseError("repository release immutability must be enabled")

    environment = api.environment(spec.environment)
    if environment.get("name") != spec.environment:
        raise ReleaseError("GitHub returned the wrong release environment")
    deployment_policy = environment.get("deployment_branch_policy")
    if deployment_policy != {
        "protected_branches": False,
        "custom_branch_policies": True,
    }:
        raise ReleaseError(
            "release environment must use selected deployment branches and tags"
        )
    protection_rules = environment.get("protection_rules")
    if not isinstance(protection_rules, list):
        raise ReleaseError("release environment returned invalid protection rules")
    reviewer_rules = [
        rule
        for rule in protection_rules
        if isinstance(rule, dict) and rule.get("type") == "required_reviewers"
    ]
    if len(reviewer_rules) != 1:
        raise ReleaseError("release environment must require reviewers")
    reviewer_rule = reviewer_rules[0]
    reviewers = reviewer_rule.get("reviewers")
    if reviewer_rule.get("prevent_self_review") is not True or not isinstance(
        reviewers, list
    ) or not reviewers:
        raise ReleaseError(
            "release environment must require a non-self reviewer"
        )

    branch_policies = api.deployment_branch_policies(spec.environment)
    policies = branch_policies.get("branch_policies")
    if (
        branch_policies.get("total_count") != 1
        or not isinstance(policies, list)
        or len(policies) != 1
        or not isinstance(policies[0], dict)
        or policies[0].get("name") != spec.default_branch
        or policies[0].get("type") != "branch"
    ):
        raise ReleaseError(
            "release environment must allow only the exact default branch"
        )

    ruleset = api.ruleset(spec.tag_ruleset_id)
    if ruleset.get("id") != spec.tag_ruleset_id:
        raise ReleaseError("GitHub returned the wrong release tag ruleset")
    if ruleset.get("target") != "tag" or ruleset.get("enforcement") != "active":
        raise ReleaseError("release tag ruleset must actively target tags")
    conditions = ruleset.get("conditions")
    if not isinstance(conditions, dict) or conditions.get("ref_name") != {
        "include": ["refs/tags/v*"],
        "exclude": [],
    }:
        raise ReleaseError("release tag ruleset must target exactly refs/tags/v*")
    rules = ruleset.get("rules")
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise ReleaseError("release tag ruleset returned invalid rules")
    rule_types = {rule.get("type") for rule in rules}
    if not {"update", "deletion"}.issubset(rule_types):
        raise ReleaseError("release tag ruleset must prohibit updates and deletions")
    if ruleset.get("bypass_actors") != []:
        raise ReleaseError(
            "release tag ruleset bypass actors must be visible and exactly empty"
        )


def verify_repository_workflows(repository_root: Path) -> None:
    workflow_directory = repository_root / ".github" / "workflows"
    workflows = sorted(
        (*workflow_directory.glob("*.yml"), *workflow_directory.glob("*.yaml"))
    )
    if not workflows:
        raise ReleaseError("repository does not contain GitHub Actions workflows")

    contents_write = re.compile(r"(?m)^[^#\n]*\bcontents\s*:\s*write\b")
    writers: list[Path] = []
    publisher_text: str | None = None
    wiki_publisher_text: str | None = None
    for path in workflows:
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^[^#\n]*\bpermissions\s*:\s*write-all\b", text):
            raise ReleaseError(f"workflow requests write-all permissions: {path.name}")
        matches = contents_write.findall(text)
        writers.extend(path for _ in matches)
        if path.name == "publish-release.yml":
            publisher_text = text
        elif path.name == "publish-wiki.yml":
            wiki_publisher_text = text

    expected_writers = ["publish-release.yml", "publish-wiki.yml"]
    if [path.name for path in writers] != expected_writers:
        names = ", ".join(path.name for path in writers) or "none"
        raise ReleaseError(
            "exactly publish-release.yml and publish-wiki.yml may each request "
            f"one contents-write token; found {names}"
        )
    legacy_path = workflow_directory / "release.yml"
    if (
        not legacy_path.is_file()
        or legacy_path.read_text(encoding="utf-8")
        != LEGACY_RELEASE_WORKFLOW_STUB
    ):
        raise ReleaseError("legacy release.yml must match the exact inert stub")
    if publisher_text is None or "workflow_dispatch:" not in publisher_text:
        raise ReleaseError("publisher workflow must use trusted manual dispatch")
    if re.search(r"(?m)^\s*tags\s*:\s*$", publisher_text):
        raise ReleaseError("publisher workflow must not run from a tag event")
    if wiki_publisher_text is None:
        raise ReleaseError("repository must contain publish-wiki.yml")
    expected_wiki_trigger = (
        "name: Publish Wiki\n\n"
        "on:\n"
        "  push:\n"
        "    branches:\n"
        "      - main\n"
        "    paths:\n"
        '      - "docs/wiki/**"\n'
        '      - ".github/scripts/sync_wiki.py"\n'
        '      - ".github/workflows/publish-wiki.yml"\n'
    )
    wiki_trigger = wiki_publisher_text.split("\npermissions:", maxsplit=1)[0]
    if wiki_trigger != expected_wiki_trigger:
        raise ReleaseError(
            "publish-wiki.yml must use the exact path-filtered main-branch trigger"
        )
    required_wiki_fragments = (
        "group: protocyte-wiki-publication-${{ github.repository }}",
        "cancel-in-progress: false",
        "persist-credentials: false",
        "${GITHUB_REPOSITORY}.wiki.git",
        'sync_wiki.py "$wiki_checkout" --apply',
        'git -C "$wiki_checkout" diff --check',
        'git -C "$wiki_checkout" add --all',
        'git -C "$wiki_checkout" push origin HEAD',
    )
    for fragment in required_wiki_fragments:
        if fragment not in wiki_publisher_text:
            raise ReleaseError(
                f"publish-wiki.yml is missing its required safety contract: {fragment}"
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--workflow-target", required=True)
    parser.add_argument("--tag-ruleset-id", required=True, type=int)
    parser.add_argument("--legacy-workflow-id", required=True, type=int)
    parser.add_argument("--repository-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    contents_token = os.environ.get("GH_TOKEN", "").strip()
    policy_token = os.environ.get("PROTOCYTE_RELEASE_POLICY_TOKEN", "").strip()
    if not contents_token:
        print("GH_TOKEN is required", file=sys.stderr)
        return 1
    if not policy_token:
        print("PROTOCYTE_RELEASE_POLICY_TOKEN is required", file=sys.stderr)
        return 1
    if args.tag_ruleset_id <= 0 or args.legacy_workflow_id <= 0:
        print("tag ruleset and legacy workflow IDs must be positive", file=sys.stderr)
        return 1

    spec = PolicySpec(
        repository=args.repository,
        environment=args.environment,
        default_branch=args.default_branch,
        workflow_ref=args.workflow_ref,
        workflow_target=args.workflow_target,
        tag_ruleset_id=args.tag_ruleset_id,
        legacy_workflow_id=args.legacy_workflow_id,
    )
    try:
        verify_repository_workflows(Path(args.repository_root).resolve())
        api = GitHubPolicyAPI(
            repository=spec.repository,
            contents_token=contents_token,
            policy_token=policy_token,
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
        verify(api, spec)
    except ReleaseError as error:
        print(f"release policy preflight failed: {error}", file=sys.stderr)
        return 1

    print("release single-writer policy verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
