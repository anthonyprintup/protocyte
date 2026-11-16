# Experimental ownership-index contract

This records the first sampled-index experiment. For the reviewed parallel
observation mechanism and closed promotion guard, see the
[observation contract](observation-commit-contract.md) and
[MR review](mr55-review-results.md).

Branch: `codex/experimental-generation-engine`, based on preservation checkpoint
`f804fd1` (`codex/issue-54-registry-scaling`). No remote publication is involved.

## First experiment

Implement a portable, filesystem-independent ownership index and bounded sampled
geometry/record authentication behind the existing coordinator entry point.
Initially expose **reference** and **shadow** validation only. The default remains
reference. There is no index-only authorization mode.

In shadow mode:

1. Sample and authenticate all records, collect geometry and compute an indexed
   preview under the existing registry/generation/publication locks.
2. Discard the sampled index as an authority. Always run the original fresh
   registry validator, preserving its comparison order and filesystem checks.
3. Propagate every reference rejection. If the preview rejected a case the
   reference accepted, fail before claim initialization or output reconciliation.
4. Publish only path-free diagnostic counts, phase timings and agreement status.
   Preview timing is not complete validation timing. Full timings include the
   mandatory reference pass, even when that means the experiment is slower.

The preview never deletes abandoned initialization directories, initializes a
claim, resets ownership or writes generated payloads. Reference reconciliation
retains all mutation/recovery authority. A read-only large preview may be measured
separately, but it must be labeled as an unverified algorithm phase, not as an
under-30-second reconciler.

## Why a sampled index is not yet authoritative

An immutable record under the registry lock does not imply immutable filesystem
topology. A foreign missing path can become a link between observations; an
ancestor or physical binding can change and return to its old state. A matching
second metadata sweep is not proof of uninterrupted validity.

Windows native mechanisms were reviewed before implementation:

- [CreateFile sharing rules](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
  can constrain deletion/rename and data-write opens, but attribute access has
  distinct rules. An open directory handle is not proof that missing children
  cannot appear or that every name-to-object relationship remains unchanged.
- [Directory oplocks](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_request_oplock)
  provide cache invalidation notifications, but changes to enumeration contents
  can cause advisory breaks without waiting for acknowledgment. They must not be
  treated as an unconditional filesystem write barrier.

No native guard or watcher will be used as mutation authority without a reviewed
consistency argument and adversarial tests covering its exact semantics. The
current experiment instead has a simple safety argument: every successful
operation still passes the existing fresh validator before any reconciliation
mutation. The preview can add a fail-closed rejection but cannot bypass one.

## Acceptance and stop boundary

- Pure geometry index results match an exhaustive predicate across lexical,
  physical, missing-ancestor, prefix-boundary and ownership/retirement cases.
- Reference mode retains existing test behavior and its original observations.
- Real mutations between preview and reference, including foreign-path changes,
  are rejected by the reference path before new claims are initialized.
- Shadow false positives fail closed; shadow false negatives never bypass the
  reference failure. Every retained record participates in both relevant phases.
- Benchmarks identify the requested/effective mode, preview/reference durations,
  implementation fingerprints and total filesystem work truthfully.

The first milestone is a reviewable experimental index with differential and
adversarial evidence. Promotion to authoritative indexed validation, packaging
refactoring and the public generation CLI remain gated on the filesystem-lifetime
proof. Correctness takes precedence over meeting a timing threshold.

## Follow-up observation experiment

The [fresh observation experiment](observation-mechanism-results.md) adds a
private `native-shadow` mode. It retains reference authority and adds no indexed
authorization mode. A real attribute-only reparse conversion disproved ordinary
read-handle pinning as a path-lifetime proof. The fresh reader's pilot also failed
the performance gate. The original cached-index promotion boundary remains closed.

The next experiment uses an optimistic read-set commit with exact USN close
witnesses and fresh negative comparisons. Its
[contract and remaining proof boundaries](observation-commit-contract.md) and
[measurements and upgrade evidence](observation-commit-results.md) preserve that
boundary: reference validation remains mandatory and the default is unchanged.
