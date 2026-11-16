# Parallel-probe qualification

**Passed: 20/20 complete validations below 30 seconds.** The experimental
branch now automatically uses the committed index on qualified Windows
invocations. The enabled default took **14.489–16.538 seconds**, with a
**14.978-second median**. Ten additional samples while two complete reference
oracles ran concurrently took **23.003–27.461 seconds**. Every sample accepted
the entire retained workload with verified end witnesses, fully retired workers,
balanced native handles, and no reference fallback.

The default median is **50.20 times faster (98.01% less time)** than the
exact historical **751.875-second validation**, or
**46.74 times faster** than an approximate 700-second baseline.
These compare distinct observed runs, not controlled estimates of the algorithm
alone. They do not include reconciliation or promise the same latency on every
host. The previous [serial timing gate](consumer-validation-results.md) remains
recorded as a failure; these results come from a new parallel implementation.

## Complete workload and measurement boundary

This is the original anonymous consumer configuration, with **11 current plans**,
one target each, **232 generated files**, **2,239 retained claims**, and
**4,478 claim/plan records** on two NTFS volumes. The historical log had 2,172
claims: all 67 additional claims remain present. No registry was pruned, split,
reset, replaced, or moved to a new lock namespace. Frozen ledger hashes match
the previous qualification captures exactly.

Each live sample uses CPython 3.12.9 on Windows build 26300 in a fresh process,
acquires the original registry/generation/publication locks, parses the original
current plans, checks their complete plan set, and runs the production registry
validation entry point. The timer includes those plan checks, every retained
record, index construction, fresh directional negative probes, inventories,
name bindings, versions, exact close witnesses, worker retirement, and native
handle release. Registry/generation/publication lock wait is reported separately;
observer-mutex wait is included. OS caches and the workload are reused. No
cold-cache claim is made, and no cache or security settings were changed.

The first formal series kept the source promotion guard closed: only the
mutation-forbidden qualification module enabled its own indexed entry point.
After that series passed, the enabled-default series used the actual default
constructor and source guard, without an experimental flag or qualification
override. All twenty samples exercised production validation code. The harness
forbids reconciliation, recovery, publication, reset, and durable record writes;
it issues no tokens. Mutation behavior is tested separately in isolated builds.

## All formal samples

| Sample | Loaded validation | Enabled default | Default CPU |
| --- | ---: | ---: | ---: |
| 1 | 23.973 s | 15.683 s | 22.703 s |
| 2 | 24.294 s | 14.703 s | 22.141 s |
| 3 | 25.784 s | 14.951 s | 23.234 s |
| 4 | 26.714 s | 14.991 s | 22.781 s |
| 5 | 23.003 s | 14.965 s | 22.438 s |
| 6 | 25.767 s | 14.489 s | 21.828 s |
| 7 | 23.425 s | 14.834 s | 21.906 s |
| 8 | 25.576 s | 15.811 s | 24.734 s |
| 9 | 27.217 s | 15.464 s | 23.578 s |
| 10 | 27.461 s | 16.538 s | 24.203 s |

Loaded median: **25.672 seconds**. Default CPU median:
**22.742 seconds**, range **21.828–24.734**.
Parallelism spends additional CPU to reduce elapsed time. The earlier paired
prototype measured 22.266 CPU seconds in parallel versus 18.500 serial; that
historical pair is feasibility evidence, not a controlled comparison for the
hardened implementation. Three preliminary hardened-development samples
(18.565, 17.480, 17.873 seconds) are retained in the JSON, excluded from the
formal twenty-sample gate because the native helper was subsequently hardened.

Every formal sample retains the following work:

| Check | Count per validation |
| --- | ---: |
| Authenticated claim/plan records | 4,478 |
| Fresh reservation comparisons | 84,579 |
| Fresh negative probes | 261,703 |
| Full registry inventories | 2 |
| Forced close posts / exact end witnesses | 17,958 / 8,979 |
| Native handles opened / closed | 26,916 / 26,916 |
| Worker batches submitted / started / finished | 2,662 / 2,662 / 2,662 |
| Worker / pending-batch peaks | 4 / 8 |
| Active / pending work at return | 0 / 0 |

## Independent acceptance and preservation

Both complete reference oracles accepted all 2,239 claims: the exact historical
coordinator took **934.707 seconds**, and the branch reference validator took
**707.352 seconds**. They ran concurrently with each other and the loaded native
series. These elapsed times describe reader contention, not controlled speedup
ratios. The slow oracles validate byte-identical ledger copies captured under
the original locks, retain the original build/output/staging geometry, filter
no foreign records, and separately execute original lock-namespace checks. They
do not hold the live shared registry lock for their long reference passes.

The post-series audit verified unchanged original claim/plan bytes, current
snapshots, and all **232 generated-file hashes and mtimes**. No ownership/output
mutation, reconciliation, publication, reset, or token creation occurred in live
qualification. Native observation still posts counted USN journal metadata;
it does not alter file contents or names. Raw paths, names, ledger copies,
tokens, manifests, and logs remain in ignored local evidence.

## Scheduling and correctness

The owner authenticates records and freezes all prepared endpoint views before
creating work. Four workers perform independent comparisons in batches of 32,
with at most eight pending batches, preserving result order. Workers cannot
register paths, collect geometry, or mutate the read-set maps. Missing endpoints
are still freshly checked in both comparison directions and during sealing.
No negative result is cached as stable. Counters use explicit synchronization.

An admission gate covers even a task queued by a failing submission. Cleanup
closes admission and drains admitted native work before executor cancellation
and joining. The retirement fence is independently required before erasing
views, closing root handles, or sealing. Worker, submission, shutdown,
and interruption failures have explicit tests. Unproved retirement
retains bindings and aborts before any reference result can authorize mutation.

Index authority requires every positive USN witness, complete inventory/name
checks, fully closed native handles, a retired pool with zero pending/active
work, and exact comparison accounting. The [contract](observation-commit-contract.md)
retains the positive-version argument, noncanonical/case-sensitive alias
boundaries, fresh-negative semantics, and cooperative-writer assumptions.

## Final-source qualification

| Check | Result |
| --- | --- |
| Complete CPython 3.14.4 suite, `pytest -q -n 4` | 1,927 passed, 41 skipped |
| Explicit indexed coordinator suite | 89 passed, 6 skipped |
| Minimum CPython 3.12.9 native/index/parallel/qualifier tests | 201 passed |
| CMake packaging and integration | 22 passed, 1 skipped |
| Old/new upgrade, rollback, publication, crash recovery | 111 passed |
| Ruff on touched Python files | Passed |
| Mixed native/CMake run after narrowing the test gate | 168 passed, 1 skipped |
| CMake-only run with four pytest workers | 22 passed, 1 skipped; 35.91 seconds |

The parallel suite contains 64 tests, including 1,024 randomized serial/parallel
ownership and retirement comparisons; all batch boundaries; real simultaneous
workers; reverse-direction file/dangling-junction races; real caller
impersonation; uncertain/emulated process contexts; late/untracked submission;
worker/shutdown/wait interruptions; preserved bindings when retirement is
unproved; incomplete certificates; previous-helper fallback; and token
preservation. Existing native ABA, alias, metadata, malformed-record,
concurrency, crash-cut and packaging checks remain in the full qualification.

The first Linux CI pass identified two test portability assumptions: POSIX may
reject a replaced ancestor with `ENOTDIR` before the explicit parent-type check,
and shallow checkouts lack the pinned older-helper revision. The rejection test
now accepts that existing fail-closed diagnostic, and plugin CI fetches history
to execute the actual historical compatibility test. Production implementation
bytes and all timing/source fingerprints are unchanged by these test fixes.

When a run includes quiet native cases, those cases and default-enabled
CLI/integration cases share a test-only mutex so their own USN markers do not
invalidate each other on common volume ancestors. CMake-only runs keep their
ordinary process parallelism. Deliberate threads/processes inside each case
remain concurrent. This does not replace or alter production ownership locks. One
test-harness race in the injected-wait handshake was corrected to wait for
the actual injected interruption before releasing the blocked worker.

## Upgrades and failure boundaries

Existing CMake commands keep working. Packaging installs the trusted sibling
helpers; no service, administrator setup, new Python dependency, registry
migration, reset, or claim-token rotation is required. The shared v1 lock
namespace, records, plan format, publication and recovery protocol stay the
same. All 111 cross-version checks use the final enabled source, including
old/default and default/old operation and crash recovery. Core mutation and
lock methods are AST-identical to the preservation checkpoint. The prior
recorded-plan `lstat` correctness fix still rejects malformed/dangling or
unreadable state rather than silently skipping it; valid ledgers need no repair.

Automatic indexed validation requires native 64-bit Windows process context,
ordinary non-impersonating execution, local NTFS DOS paths, an existing usable
journal, exact supported observations, and the resource budgets in the contract.
Other platforms and unsupported capabilities use reference. Namespace changes,
aliases, dirty/missing witnesses, journal churn, external marker collisions,
and ordinary comparison failures after safe cleanup also use full reference
validation, which can exceed 30 seconds. Failed worker retirement aborts before
mutation. A broken native certificate never licenses an indexed acceptance.

To force reference validation in an existing build, set
`PROTOCYTE_REGISTRY_VALIDATION=reference` in its environment; direct coordinator
commands also accept `--reference-registry-validation`. No configuration is
needed for normal use. Partial/mixed helper installations safely fall back
when their trusted API cannot supply the required complete certificate.

This is evidence for the retained workload and tested Windows/NTFS host.
It does not prove a universal bound under cold caches, all filesystem filters,
or arbitrary machine load. Observation certifies past positive intervals, not
a namespace freeze or future stability. The existing cooperative-writer trust
model and mutation-time checks remain necessary.

## Source provenance

Qualification started at `8851bde`. The frozen pre-promotion native helper is
byte-identical to the enabled helper. Promotion changed automatic selection,
the qualification constant, and CLI default wiring in the coordinator;
its reference validator, lock class, and mutation methods are AST-identical
to the frozen oracle and starting checkpoint. Full final-source tests and the
enabled-default timing series ran after promotion.

| Final implementation | As-run SHA-256 |
| --- | --- |
| `ProtocyteObservationCommit.py` | `143cd5e26bc25aafd848e7cc79df6d1d9d99793481aa5600df4d0541432d4664` |
| `ProtocyteOutputCoordinator.py` | `8646c014f9b5537f47dcccada60f7df6935043ed6a8c70c2f65f830307f78b10` |
| `ProtocyteOwnershipIndex.py` | `7df8626756210f8dd0694bf26ffb7364f6c638f6361d14e61ef6c48df23dfd38` |
| `ProtocytePathObservation.py` | `a745ea87565dab8b7ff0883d72a3d781854f3b88139d2ffc37052715de0bf1e4` |

The [machine-readable report](parallel-probe-results.json) retains every formal
run and counter, the preliminary samples, reference receipts, preservation
audit, final upgrade receipt, frozen oracle fingerprints, and Git-normalized
source hashes. Normalization changes CRLF to LF only, with identical ASTs.
