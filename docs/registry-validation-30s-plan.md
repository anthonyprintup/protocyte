# Assessing a 30-second validation target

## What has actually been reproduced

There is a scalable, explicitly isolated synthetic reproduction of the same
registry-validation bottleneck. There is **not** a measured synthetic run that
matches the reported 751.875 s consumer observation exactly.

| Case | Retained claims | Current plans | Validation | Status |
| --- | ---: | ---: | ---: | --- |
| Public issue #54 consumer observation | 2,172 | 11 | 751.875 s | Reported observation; consumer registry not accessed here |
| Earlier large synthetic run | 1,024 | 11 | 220.612 s | Measured on the first issue-54 implementation, Python 3.14.4 |
| Same synthetic shape at 2,172 claims | 2,172 | 11 | About 468 s | Simple size extrapolation of the preceding row, **not a measurement** |

The final small refinement did not establish an additional wall-time speedup.
The large measurement and extrapolation must not be relabeled as final-code
large-run results. Setup for the 1,024-claim case took another 136.632 s and is
excluded from validation.

An exact-size synthetic baseline can already be run from the repository root:

```powershell
py -3.12 -B tests/benchmark_output_registry.py --large --claims 2172 --plans 11 --repeat 1 --work .pytest-tmp/registry-2172-baseline
```

The workspace must not exist. Fixture setup and validation can take minutes on
the current algorithm. Every sample has a new private registry and uses real
locked initialization/reconciliation helpers; measured validation skips no
checks. Publish only sanitized results, never fixture directories.

This fixture has one target/output per plan, distinct synthetic build directories,
and initially absent output/staging directories. Equal claim/plan counts do not
make it a calibrated consumer-equivalent workload. Existing/missing roots,
targets per claim, shared build identities, directory depth and record sizes
must also be covered using anonymous layouts. We should not add artificial work
just to make a baseline last 750 seconds.

## Required improvement and remaining cost

751.875 s to under 30 s requires **more than 25x** improvement. Even the rough
468 s synthetic projection would need approximately **16x**. Changing locks or
replacing individual stat APIs does not address that scale of work.

The one-target synthetic cases currently perform approximately
`117 * retained_claims + 133` path projections during registry validation when
there are eleven current plans and at least one retained claim. This matches
the observed 119,941 projections at 1,024 claims and predicts about 254,257 at
2,172 claims. This is an operation-count inference, not a new large measurement.

A new bounded phase profile on **CPython 3.12.9** checked 64 retained claims
against eleven plans. Setup was separate; every retained claim/plan was checked.
The disjoint outermost function timers measured:

| Registry-validation work | Seconds | Share |
| --- | ---: | ---: |
| Direct overlap comparisons and repeated current-root keying | 6.634 | 87.8% |
| Claim JSON/path authentication and complete recorded-plan authentication | 0.871 | 11.5% |
| Remaining work | 0.055 | 0.7% |
| Total registry validation | 7.560 | 100% |

The authentication row includes its nested filesystem checks and plan parsing;
it is **not** just JSON decoding. Nested costs are not counted again in the
comparison row. The scan authenticated all 64 recorded plans, made 2,860 direct
overlap comparisons and derived 704 current-root keys. Lock preparation/acquisition
was 0.143 s, separately from validation. Current-plan validation was 0.399 s.

Simply extrapolating the authentication row to 2,172 claims gives about **29.6 s**
before the new conflict algorithm or its freshness checks. That is a descriptive
estimate from one instrumented run, not a lower bound or timing guarantee.
Nevertheless, it shows why optimizing only the cross product is insufficient:
record authentication must also stop repeatedly projecting the same paths.

The reproducible profiler is `tests/profile_output_registry.py`:

```powershell
py -3.12 -B tests/profile_output_registry.py --claims 64 --plans 11 --work .pytest-tmp/registry-phase-profile
```

It delegates every operation unchanged, verifies one authentication per retained
record, restores its wrappers, and writes path-free metrics. Results for this
assessment are in [registry-validation-feasibility.json](registry-validation-feasibility.json).
All these timings include instrumentation and uncontrolled workstation/cache
effects; use counts and matched baseline/candidate runs for acceptance.

## Architecture needed for an order-of-magnitude reduction

The recommended research direction is a **transient ownership index with an
explicit filesystem-observation/commit contract**, plus record-authentication
refactoring. This is a proposed design to prove, not permission to enable broad
caching under the existing per-comparison freshness contract.

1. **Separate record decoding from filesystem authority.** Split the work now
   coupled in `_load_recorded_plan`, `Plan.from_payload`, `_claim_paths`,
   `_require_plan_claim_binding` and `_validate_staging_path`. Read every record,
   validate every shape/digest/ownership binding and keep the registry lock.
   Authenticate path-dependent identities from an explicit observation object
   rather than recursively projecting root/build/staging paths again. Immutable
   JSON can be retained under the existing registry-lock contract; filesystem
   observations need a separate, justified lifetime.
2. **Index all root and staging reservations.** Index canonical lexical prefixes,
   physical directory/ancestor identities and missing-suffix relationships,
   including owner/build/target metadata. Lookup must cover containment in both
   directions, aliases of missing ancestors, and the existing retirement/same-owner
   exceptions. Every retained claim still participates. A lexical-only path trie
   cannot substitute for physical identity checks.
3. **Move filesystem work out of the claim × plan loop.** Build the index from
   bounded observations and perform conflict queries against the current plans.
   Aim for metadata work proportional to unique paths/components and necessary
   revalidation passes, rather than repeatedly walking ancestors per pair.
   The desired normal-case shape is approximately `O(unique path components +
   reservations + current-plan lookups)`, with appropriate indexing overhead.
   Even linear passes will fail the target if the old repeated authentication
   walks remain inside them.
4. **Prove the observation boundary before production use.** This is the difficult
   step. A registry lock protects cooperating record writers, not arbitrary
   external renames, reparse changes or creation of formerly missing components.
   An indexed negative conflict result can become stale through a foreign path,
   even if the current output root itself is freshly checked. The design must
   identify every dependency, invalidate/rebuild on changed bindings and freshly
   validate authority before mutation. Two matching metadata sweeps, a timestamp,
   a registry version or a filesystem watcher alone are not proof that topology
   remained unchanged. Any handle/identity-based scheme still needs a proof of
   the relationship between those objects, their names and missing components.
5. **Retain mutation-time protections.** Claim initialization, recovery,
   retirement, reset and publication must keep their existing ownership and
   topology checks. Do not carry an index through released locks or mutations.
   Changes must fail closed with bounded recovery/retry behavior. If a safe
   invalidation scheme requires returning to the full cross product, the proposed
   design has failed its performance objective and must not be advertised as a
   solution.

This could cut hundreds of thousands of repeated projections to a small number
of passes over thousands of distinct locations and their shared ancestors. That
is enough algorithmic headroom to make 30 seconds plausible. It is **not yet a
safety-proven design or a demonstrated 30-second result**. Under the unchanged
rule that each pair performs fresh full walks, there is no evidence that local
tuning can produce the required 16–25x improvement.

## Finite next phase and acceptance

1. Freeze one exact-size 2,172/11 synthetic baseline and representative anonymous
   layout variants. Define the target as **all validation work under 30 s**,
   including record I/O/authentication, geometry checks, conflict queries and
   any required fresh revalidation. Keep fixture setup, lock waiting and output
   reconciliation separately reported.
2. First prototype only record authentication and linear geometry observation
   under a written consistency contract. Measure 64 and 256 claims, plus operation
   counts. Budget the full 2,172/11 validation at less than 25 s to leave margin.
   If minimum safe observation/authentication work already consumes that budget,
   stop and revise the architecture before implementing the full index.
3. Prove race/alias behavior with injections between observation, lookup,
   precommit revalidation and actual mutations. Include foreign-path replacement,
   missing-component creation, ancestor replacement, ABA-style changes, Windows
   case/short-name aliases, links/junctions, concurrent writers and crash recovery.
   Existing passing tests are necessary but not a proof of the new lifetime model.
4. Add the ownership index only after the safety argument is reviewable. Require
   operation growth close to the number of reservations/unique components when
   moving through 64, 256, 1,024 and 2,172 claims with eleven plans. Require every
   record to remain authenticated and no lost overlap/ownership rejection.
5. Run the exact-size case and representative layout cases with the final design.
   Report first-process and repeated-process samples honestly; a fresh process
   does not imply a cold OS filesystem cache. Claim the target only from measured
   results on the stated environment, with instrumentation overhead disclosed.

Lock-wait convoy improvements can be pursued separately with the compatible
release/retry protocol discussed in [the locking review](registry-validation-refinements.md#locking-assessment).
They help unrelated writers under contention but cannot remove 750 seconds of
active validation work. Clearing retained claims, dropping physical checks,
changing the shared namespace or relaxing safety to meet a timing gate are not
part of this plan.

No production coordinator logic was changed for this feasibility assessment.
