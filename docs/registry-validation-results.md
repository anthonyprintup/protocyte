# Registry validation results (#54)

These measurements cover the first implementation. The [subsequent optimization
review](registry-validation-refinements.md) records further experiments, the
final retained refinement and its verification. Historical samples remain intact.

The architecture proposal is in [registry-validation-design.md](registry-validation-design.md).
This is a bounded reduction in physical metadata work, preserving fresh
observations for every comparison. The retained-claim/current-plan cross product
and all path projections remain. It does not claim sublinear registry validation.
Full sanitized samples are in [registry-validation-results.json](registry-validation-results.json).

## Method and source identity

Windows, CPython 3.14.4; instrumented local measurements. Baseline is the local
coordinator before this change, with the exact LF-normalized SHA-256 reported
in #54 (`2ff54b69242d46eb8e35a52d30b32bc9afd815c00b6c0abeb8765d6fe7ddbb85`).
No historical checkout reset was needed. Every sample has a new isolated
synthetic registry. Setup uses real private locked initialization/reconciliation;
the measured operation is normal `reconcile_set((), current)`, with all checks
and filesystem calls delegated unchanged. Setup is excluded from validation.
No generated payloads, shared consumer registry or network are involved.

The issue POC is retained at `tests/registry_validation_poc.py`. Its sample
method is unchanged; progress metadata tolerates the removed lifetime cap,
and the encoding lambda was converted to a function for lint. Repository
formatting also changes presentation without changing the measurement. The
original script remains embedded in issue #54. Both initial matrices used that
original script before those presentation/metadata adaptations. The initial
candidate temporarily retained `MAX_REPORTS` solely as legacy POC metadata; it
was already ignored by the reporting loop. Thus that original candidate JSON's
nominal cutoff field is legacy metadata, not an actual cutoff (26 reports were
observed). The final implementation removes the constant entirely.

The reusable benchmark now profiles filesystem calls, restores instrumentation
in `finally`, rejects reused sample directories, and supports explicit `--large`
workloads up to 4,096 claims/32 plans. Private seeding avoids quadratic setup
validation, matching the POC; measured reconciliation never skips validation.
`seed_wall_seconds` now includes fixture plan creation. `lock_wait_wall_seconds`
includes preparing and acquiring all lock files (excluding key derivation
between calls); it is not pure kernel blocking.
`registry_lock_held_wall_seconds` measures acquisition to release directly.
Current-plan all-pairs validation is timed outside registry-validation profiling.

## Original POC matrix

Single descriptive samples; caches and concurrent workstation activity were not
controlled. All twelve operations completed. Counts combine `nt.stat` and
`nt.lstat`; Python versions can move calls between those two categories.

| Claims / plans | Baseline validation s | Candidate validation s | Baseline stat+lstat | Candidate stat+lstat | Projections (both) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 / 1 | 0.046 | 0.029 | 381 | 246 | 12 |
| 0 / 11 | 0.379 | 0.256 | 4,191 | 2,706 | 132 |
| 8 / 1 | 0.328 | 0.675 | 4,899 | 3,794 | 229 |
| 8 / 11 | 2.212 | 2.098 | 32,729 | 22,494 | 1,069 |
| 16 / 1 | 0.632 | 0.593 | 9,395 | 7,330 | 445 |
| 16 / 11 | 4.094 | 3.674 | 61,145 | 42,270 | 2,005 |

The 8/1 sample was slower despite fewer probes: single-run wall times are not
a performance gate. The POC's timed validation includes JSON loading, claim/plan
authentication and all comparisons. No JSON or unrelated-claim checks are removed.
Final-path resolutions at 16/11 remain 4,010; projections still dominate much
of the remaining work. Filesystem counts establish the reduced work more reliably
than these timings.

## Alternating comparison and lock occupancy

Three alternating baseline/candidate samples, 16 claims/11 plans, with the
maintained benchmark and equal path depth:

| Measurement | Baseline median | Candidate median |
| --- | ---: | ---: |
| Registry validation | 6.719 s | 4.552 s |
| Validation CPU | 5.438 s | 3.875 s |
| Total reconciliation | 10.468 s | 7.623 s |
| Setup (includes plan creation) | 3.143 s | 2.741 s |
| Registry scans | 1 | 1 |
| Recorded-plan loads during validation | 16 | 16 |
| Projections during validation | 2,005 | 2,005 |
| Validation stat+lstat | 66,272 | 45,814 |

This is 32.3% lower median registry-validation time and 27.2% lower total time.
Different path depths explain filesystem-count differences from the POC matrix.
One additional pair with direct lock instrumentation measured registry occupancy
7.090 s → 5.586 s, registry validation 4.787 s → 3.575 s, current-plan validation
1.075 s → 0.746 s, and lock acquisition/preparation 0.239 s → 0.273 s.
These are local descriptive results, not a CI timing guarantee.

## Larger workload and progress

The 64-claim/11-plan pilot completed with 9.023 s setup, 12.342 s registry
validation and 14.398 s reconciliation. It scanned once, loaded 64 recorded
plans, projected 7,621 paths, and made 174,406 stat+lstat calls.

The capped 1,024-claim/11-plan run completed: 136.632 s setup, 220.612 s registry
validation (198.672 s CPU), 0.670 s current-plan validation, 222.487 s total
reconciliation, 222.463 s registry-lock occupancy and 0.246 s lock acquisition/
preparation. It scanned once, loaded all 1,024 recorded plans, projected 119,941
paths and made 2,746,246 stat+lstat calls plus 239,882 final-path resolutions.
All 11 plans completed. Production progress continued at 65, 120 and 220 seconds
and ended with 1,024/1,024 claims checked. No 2,048-claim or original consumer
benchmark is claimed. This is a completion/scaling sample, not a large baseline
comparison or evidence that the remaining scaling cost is solved.

The original accelerated POC observed twelve periodic reports and suppression
at baseline. The candidate produced 26 periodic reports through claim 39/40,
no suppression, and a completion message. Scheduling affects the exact count.
Production remains at five-second frequency for the entire operation. Focused
tests also exercise the actual reporter loop beyond twelve intervals without
wall-clock sleeps, while keeping stdout clean and phase/count/timing fields.
The final maintained-POC smoke run confirms null lifetime-cap/cutoff metadata,
26 periodic reports, no suppression and successful completion.

## Safety and remaining limits

Claim format, ownership binding, lock ordering/lifetime, reset and crash recovery,
mutation-time path checks and publication transactions are unchanged. Non-following
directory identity replaces `samefile`'s redundant following probes inside
physical containment only. Other uses of `samefile` remain. Alias simulations now
provide matching directory identities as actual physical aliases do. No identity
observations escape one directional comparison; reverse checks remain fresh.

Filesystem metadata work is linear in ancestry depth within each direction;
materializing missing-suffix tuple prefixes still has quadratic worst-case
Python copying cost in missing depth. Registry cost remains proportional to
retained claims times current plans/targets; large registries can still take
minutes. Arbitrary external topology mutation is not frozen by registry locks.
A future index needs a separately reviewed topology-invalidation design.

The isolation audit found older default-selector CMake fixtures. They now receive
a per-test cache base, shared across that test's build trees, with a focused
selector regression. Existing explicit lock-root fixtures retain their choice.
No retained shared claims were inspected, classified as stale or removed.
Only sanitized result JSON is suitable for publication; synthetic fixture
directories and raw logs remain ignored and private.

## Verification

- `python -m pytest -q -n 4`: **1,721 passed, 41 skipped** (82.44 s), including
  coordinator recovery, concurrent writers, alias/ownership and adversarial
  topology checks plus the new metadata/progress regressions.
- `ruff check src tests cmake/ProtocyteOutputCoordinator.py`: passed.
- `python -m pytest -q -m cmake_integration tests/test_output_coordinator_cmake.py`:
  **16 passed, 1 skipped** (64.25 s), including default-registry isolation,
  lock-wait progress forwarding, recovery and competing-build rejection.
- `git diff --check`: passed.
- The original POC matrix, three alternating comparison pairs, direct lock
  occupancy pair, 64-claim pilot and capped 1,024-claim run all completed.
- The maintained POC smoke run completed with the final reporter API.

No C++ files were changed. Cross-platform execution and 2,048+ claim measurements
remain outside this run; timings are not inferred for those cases.
