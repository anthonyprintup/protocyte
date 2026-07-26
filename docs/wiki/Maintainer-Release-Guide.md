# Maintainer Release Guide

This page is for repository administrators. Users integrating Protocyte should
read [Releases and Versioning](Releases-and-Versioning).

## Required repository policy

Release publication requires GitHub release immutability. Create a protected
`release` environment and configure:

- `RELEASE_IMMUTABILITY_TOKEN`, a fine-grained credential with
  `Administration: read`;
- `RELEASE_POLICY_AUDIT_TOKEN`, a separate credential with
  `Administration: write` and `Actions: read`;
- `RELEASE_TAG_RULESET_ID`, the numeric ID of the active release-tag ruleset.

The environment must allow exactly `main`, require a non-self reviewer, and
disable administrator bypass. The ruleset must target exactly
`refs/tags/v*`, prohibit tag updates and deletions, and have no bypass actors.

## Retire the historical writer

The repository previously published from `.github/workflows/release.yml` on
tag pushes. Source changes cannot retroactively disable copies of that workflow
in Git history. Record and disable the legacy workflow identity with an
administrator credential that has `Actions: write`, then save its ID as
`LEGACY_RELEASE_WORKFLOW_ID`:

```console
legacy_id="$(gh api repos/OWNER/REPOSITORY/actions/workflows/release.yml --jq .id)"
gh api --method PUT "repos/OWNER/REPOSITORY/actions/workflows/$legacy_id/disable"
```

The repository deliberately keeps `.github/workflows/release.yml` as an inert
stub with no push, tag, or manual trigger, `contents: none`, and one
always-skipped retirement job. Removing it would make GitHub report the legacy
identity as deleted instead of `disabled_manually`. Do not enable or modify it.

The preflight requires the historical path and workflow ID to report
`disabled_manually`. It also rejects disabled immutability, a stale
default-branch workflow, unsafe environment branch policy, a missing non-self
reviewer, any tag-ruleset bypass actor, and another write-capable workflow.

## Single-writer boundary

GitHub's release API exposes creation, asset upload, listing, and draft
publication as separate calls. Its publication `PATCH` has no conditional
write precondition. Source code cannot make separate GitHub API calls atomic.

The workflow therefore serializes all releases in one repository-wide
concurrency group. Repository policy reserves `contents: write` for the
protected release-environment publication job. No user, GitHub App, PAT,
deploy key, or other automation with release write access may edit the draft
while the transaction runs. This writer exclusivity establishes the
single-writer boundary.

Most policy is audited through the REST API. GitHub does not expose the
environment's administrator-bypass setting, so disabling that bypass and
excluding other writers remain administrator prerequisites.

## Publish

Create the version tag, then dispatch `publish-release.yml` from `main`:

```console
gh workflow run publish-release.yml --ref main -f tag=vX.Y.Z
```

Only the live default-branch workflow SHA may enter the protected environment.
The separately enforced legacy `disabled_manually` state prevents a tag push
from activating the older writer.

The build job has `contents: read`. It hands the three tested assets and a
SHA-256 manifest to the publication job as one immutable Actions artifact. On a
fresh runner, publication checks out the trusted workflow revision, verifies
the artifact identity, server-side digest, tag commit, and exact file manifest,
then gives the clean checkout's publication client the short-lived
`GITHUB_TOKEN`.

The client resolves annotated tags before creation, each upload, and
publication, and rejects target drift. `target_commitish` is not trusted when a
tag already exists.

## Failure handling

The workflow never resumes, repairs, or replaces assets on an existing release.
If a failed run leaves an unpublished draft, inspect and manually delete that
draft before redispatching. A published immutable release is terminal and must
not be deleted merely to retry.

An external writer could upload an asset after the final list and before
GitHub processes the publication `PATCH`; the client could observe that only
after publication. There is no conditional release-publication operation to
close the interval. This is why administrator-enforced writer exclusivity is a
prerequisite, not merely a client check.
