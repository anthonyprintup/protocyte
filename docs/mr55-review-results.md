# MR #55 correctness and upgrade review

**Hold indexed promotion.** Four findings were fixed, including a reproduced
false acceptance through a valid-but-truncated helper. Correctness, failure
paths, packaging and **115 actual-source upgrade/recovery cases pass**.
The repeat timing gate failed at **30.115 seconds** on its fifth sample, so
**the index is disabled and the default is reference validation**. The MR
remains a draft. The prior [20-run qualification](parallel-probe-results.md)
is preserved as historical evidence, not a promotion override.

## Findings and fixes

### [P1] Incomplete helpers could authorize overlapping staging

A syntactically valid truncated pre-review helper accepted a root/staging conflict that fresh reference rejected.

Typed EOF capability markers and checks in both caller and helper entry points prevent incomplete or mixed helpers from gaining authority, including older callers.

### [P2] Worker bookkeeping and lost wakeups could strand retirement

An admission bookkeeping MemoryError left active=1 with no native query running; a failed final notification could strand a draining owner.

Admission is inside the retirement finally; active work retires before optional accounting, and draining rechecks the fence with a bounded condition wait.

### [P2] Native acquisition and release errors crossed the cleanup boundary

An interrupted successful open lost an uncounted handle; failed close accounting could still permit reference authorization.

Unpublished output handles are retired on foreign-call exceptions; uncertain close completion is latched as fatal, never retried, and never permits fallback authorization.

### [P2] Routine CI depended on experimental branch history

Pinned git-show unit tests could fail after shallow checkout, squash merge or branch deletion.

Routine contract tests are self-contained; actual pinned old/helper/coordinator checks live in the explicit 115-case historical-source qualifier. CI no longer fetches all history for these unit tests.

The incomplete-helper reproducer used the exact pre-review source, truncated
at a valid Python boundary before current staging comparisons. Its index
accepted a staging/root overlap that fresh reference validation rejected.
The unsafe plan was never reconciled and no current claim was created.
Caller checks alone would not protect an older coordinator, so helper
constructors also check their EOF markers before acquiring OS resources.

The cleanup tests cover failures before and after OS close completion. A
failed/uncertain numeric handle is never automatically retried; known
remaining roots close once, cleanup stays failed, and no reconciliation is
authorized. [Microsoft documents single-close usage and invalid-handle behavior](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle).
Tests explicitly release only the handles their injector knows it withheld
before any OS close; production cannot make that assumption.

## Repeat workload gate

The same original anonymous configuration still has **2,239 claims**,
**4,478 claim/plan records**, **11 current plans**, and **232 generated files**
on two NTFS volumes. Its captured ledger is byte-identical to the initial MR
qualification. No claims were pruned, split or reset. Each fresh process uses
CPython 3.12.9 and the original registry/generation/publication locks.

| Run | Complete validation | Under 30 seconds |
| --- | ---: | :---: |
| 1 | 28.856071 s | Yes |
| 2 | 29.550852 s | Yes |
| 3 | 29.314126 s | Yes |
| 4 | 28.384457 s | Yes |
| 5 | 30.115118 s | **No** |

The intended ten-sample series stopped on the first failure. Both complete
reference readers were active throughout every sample. All five index answers
were accepted with verified witnesses, 261,703 fresh negative probes, 84,579
comparisons, 4,478 authenticated records, fully retired workers and all 26,916
native handles closed. The gate measures current-plan parsing and the complete
validation, including observer-mutex wait; ownership-lock wait is separate.
The fifth sample includes plan parsing even though the progress phase timer
alone was just below 30 seconds. No timing component was removed to pass.

These samples include the cleanup fixes before final constructor-only
compatibility guards. The final source keeps the same comparison/IO algorithm
and remains disabled. A separate final-source control accepted the full ledger
in **29.136 seconds**, compared with **29.893 seconds** for the prior native
implementation. Both control samples overlapped the continuing legacy
reference reader, after the branch reference reader had completed. They are
descriptive single samples, not proof of a code regression or a reliable
latency bound, and do not replace the failed promotion gate.

The result calls for more headroom before promotion. A quieter sample,
rounding away plan parsing, or the previous successful series cannot reopen
the source gate. No production index enablement is included in this revision.

## Reference acceptance and preservation

- Exact historical coordinator: all **2,239 claims accepted**, **1249.391 seconds** under concurrent reader/test load.
- Branch reference validator: all **2,239 claims accepted**, **948.498 seconds** under concurrent reader/test load.

Slow oracles use byte-identical frozen ledgers and the original build/output/
staging geometry, with original lock-namespace checks performed separately.
They hold no long-lived live shared registry lock. Their reference methods
are AST-identical to the final implementation; frozen native helper files
are not used by reference validation. Timings are not controlled speedup ratios.

The final preservation audit verified original claim/plan bytes, current
snapshots, and all **232 generated-file hashes and mtimes**. Live qualification
created no tokens and performed no reconciliation, publication, reset or
ownership/output mutation. USN observation still posts counted journal
metadata. Raw consumer evidence remains ignored and anonymous.

## Final correctness and upgrade qualification

| Check | Result |
| --- | --- |
| CPython 3.14.4 complete suite, four pytest workers | 1,983 passed, 41 skipped |
| Explicit indexed coordinator suite | 89 passed, 6 skipped |
| Minimum CPython 3.12.9 native/index qualification | 257 passed |
| CMake packaging/integration | 22 passed, 1 skipped |
| Pinned actual-source upgrade, rollback and crash recovery | 115 passed |
| Ruff, source/AST and whitespace checks | Passed |

The parallel/failure suite now has **120 cases**. It adds admission/completion
allocation failures, lost final wakeups, interrupted native opens, short/root
close errors before and after OS completion, no-retry cleanup, incompatible
helper versions, valid truncated sources, and old API shapes. The historical
qualifier additionally executes the actual previous helpers and previous
coordinator with the updated helpers, including fatal cleanup. Ordinary
tests need no experimental commit history or network fetch.

**Protocol v1 is unchanged.** The plan/claim schema, tokens, path keys, lock
namespace/order, reference validator, publication and recovery methods are
AST-identical to the reviewed starting revision. Valid installations need no
migration, cache reset, regeneration or token rotation. Internal helper
contracts `(commit=2, ownership=1, path=1)` identify complete compatible Python
sources and do not change any on-disk format. Packaging installs the sibling
helpers; incompatible installations use reference before creating a read set.

The default now stays reference on every platform. The hidden indexed CLI and
private mode cannot bypass the closed promotion guard. Only isolated fixtures
and the mutation-forbidden qualification harness override their own module.
Existing CMake commands keep working, with continued progress during long
reference validation and no new configuration or runtime dependency.

## Remaining limits and next gate

Native IO must finish before workers and roots can retire, so a blocked native
read can delay cancellation. Uncertain native cleanup aborts the operation.
The read set certifies past positive intervals with fresh negative probes;
it does not freeze the namespace or replace the existing cooperative-writer
and mutation-time boundaries. Capabilities and timing were exercised on one
Windows/NTFS host with reused OS caches, not a universal platform/load matrix.

Before enabling the index again, improve worst-case headroom while preserving
all checks, then repeat the complete loaded and ordinary-default timing series
against the final source. The current failure remains a promotion blocker.

The [machine-readable report](mr55-review-results.json) records source hashes,
unchanged-AST assertions, every timing sample/counter, oracle receipts, the
preservation audit and all 115 upgrade cases.
