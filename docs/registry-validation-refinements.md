# Further registry optimization review

This follow-up compares against the first issue #54 implementation, rather than
claiming its improvements again. All measurements use new private registries;
the previous coordinator is preserved only in ignored local comparison storage.

Final choice: keep only lexical ancestor-list construction, eliminating one
duplicate existence query per stable projection. The Windows attribute-query
experiment was tested and discarded: its incremental benefit was inconsistent
across installed Python 3.12.9 and 3.14.4. Lock ordering/lifetime is unchanged.

## Findings and proposed changes (before implementation)

An 8-claim/11-plan profile measured 2.005 s registry validation. `project_path`
accounted for 1.230 s cumulatively; `_is_link` accounted for 0.616 s through
9,775 rich `lstat` probes. Physical ancestry checks accounted for another
0.744 s. These cumulative costs overlap and must not be added together.
The process performed 19,537 `lstat`, 1,069 `stat`, 3,077 native existence
queries and 2,138 final-path resolutions during registry validation.

Two bounded improvements are worth testing:

1. On Windows, `_is_link` only needs to know whether an ordinary path could be
   a link/reparse point. Query `GetFileAttributesW` freshly at every existing
   check. If the query succeeds and the reparse bit is absent, return false.
   For every reparse point or failed query, use the existing `lstat` and tag/
   mode handling unchanged. Do not replace physical identity probes, final-path
   resolution, directory-type checks, or post-projection revalidation.
2. `_existing_chain` repeats existence searches only to construct an ancestor
   list. Construct that list lexically instead, retaining a fresh link check for
   every component, the separate leaf type check, strict resolution and all
   eight retry attempts. If the leaf disappears, these subsequent observations
   still retry the complete projection. No existence observation is reused.

Only the Win32 function binding may be retained, never returned attributes.
Pass the original spelling to the API: adding an extended-path prefix would
change Windows trailing-dot/space normalization. Embedded NUL input must fall
back to the original path API, avoiding C-string truncation. Failed attribute
queries (including share roots or long paths) must also fall back, preserving
the original permission-error and missing-path behavior. Other reparse tags
must retain their original treatment rather than rejecting all reparse points.
Non-Windows `_is_link` behavior remains unchanged.

The first change substitutes a cheaper query for rich metadata; it does not
remove the corresponding filesystem observation. Count the new native queries
explicitly in both benchmark and POC. The second change removes an actual
existence probe per projection without removing link/type/identity checks.
The complete retained-claim/current-plan cross product remains O(claims * plans)
for bounded target counts and depth; no cross-comparison cache is introduced.

Windows API contracts used here are documented by Microsoft:
[GetFileAttributesW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileattributesw)
and [file attribute constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-attribute-constants).

## Locking assessment

The measured 1,024-claim run spent 220.612 s in registry validation but only
0.246 s preparing/acquiring locks. Removing a lock cannot address that dominant
cost. Registry serialization protects claim/plan visibility through commit;
generation locks exclude active generators and staging retirement; publication
locks exclude recovery/output mutations. Keep all three and the current order.

There is a separate potential contention problem: reconciliation holds registry
while waiting for a busy root's generation lock, blocking unrelated claim writers.
The uncontended POC does not measure that scenario. Addressing it requires a
coordinated protocol change, not deleting an acquisition:

- Taking generation locks before registry for every reconciliation/reset writer
  could avoid this convoy, but mixing old/new ordering deadlocks. Old processes
  from other checkouts can still share the registry, so a unilateral reorder is
  unsafe without a compatible migration protocol.
- A nonblocking generation-lock attempt while holding registry, followed by
  releasing all locks before waiting/retrying, preserves acquisition order but
  needs starvation bounds, fresh key/path validation and concurrency coverage.
  It could reduce unrelated-writer latency; it will not speed up the single
  operation's filesystem validation. Leave this as a targeted future experiment.
- Shared registry reads or validation outside the exclusive lock need a registry
  generation/retry protocol and revalidation before publication. Registry version
  checks alone do not detect external filesystem replacements. No such shortcut
  is justified by the present measurements.

## Bounded acceptance plan

Test the attribute fast path, both fallback cases, access failures, arbitrary
reparse tags, original Windows path spellings, embedded NUL, and real junctions.
Retain and strengthen disappearing-leaf, replacement-between-observations,
alias, crash/recovery and concurrent-writer regressions. Count native attribute
and existence queries so replacing `lstat` cannot masquerade as eliminating all
filesystem work. Run an alternating small benchmark matrix against the first
issue #54 implementation, plus focused/full unit tests and focused CMake tests.
Only repeat the 1,024-claim run if the pilot demonstrates a meaningful gain;
keep that run bounded at one sample and approximately six minutes including setup.

## Results and final implementation

All timings are instrumented Windows workstation observations, with uncontrolled
cache/machine activity. Operation counts are more reliable than small timing
differences. Samples are retained in the `refinements` section of
[the sanitized result JSON](registry-validation-results.json).

The initial combined prototype (attribute queries plus lexical ancestor list)
showed 4.150 s → 3.791 s median registry validation and 6.639 s → 5.745 s total
reconciliation over three alternating 16-claim/11-plan pairs. A full small POC
matrix completed for both sources. Further tests compared the attribute fast
path specifically against the simpler lexical-list variant:

| Runtime | Simple variant total median | Attribute variant total median | Attribute variant change |
| --- | ---: | ---: | ---: |
| CPython 3.14.4 | 5.886 s | 6.004 s | 2.0% slower |
| CPython 3.12.9 | 5.991 s | 5.672 s | 5.3% faster |

Each comparison used three alternating pairs. The Python 3.14 validation CPU
median also rose from 3.500 s to 3.781 s with the attribute variant. These mixed
results do not justify extra platform code and fallback semantics. The prototype
passed its focused fallback/path-spelling safety tests, but performance still
failed to establish a reliable advantage. No attribute fast path remains in the
coordinator. Its optional instrumentation remains available when comparing
experimental sources so old measurements do not conceal their replacement queries.

The final retained change was then compared directly against the previous issue
#54 implementation, with three alternating 16-claim/11-plan pairs on Python
3.14.4:

| Measurement | Previous fix | Final refinement |
| --- | ---: | ---: |
| Native existence queries during registry validation | 5,821 | 3,816 |
| `stat` / `lstat` calls | 45,814 | 45,814 |
| Final-path resolutions | 4,010 | 4,010 |
| Path projections | 2,005 | 2,005 |
| Registry scans / recorded-plan loads | 1 / 16 | 1 / 16 |
| Median registry validation | 3.398 s | 3.405 s |
| Median total reconciliation | 5.395 s | 5.398 s |
| Median registry-lock occupancy | 5.368 s | 5.363 s |

This removes exactly 2,005 existence queries (34.4% of that query family; 3.6%
of the metadata operations counted in this table). It preserves every link,
directory type and physical identity observation. Overall timing is within
noise, so no additional wall-time speedup is established. Retain the small
portable simplification and its concrete query reduction, rather than claiming
the prototype's early apparent speedup for the final code.

The final POC matrix also ran on the installed CPython **3.12.9**, matching the
original issue's runtime. All twelve before/after reconciliations completed.
That Python reports existence queries as `nt.lstat`, while newer Python reports
the corresponding calls as `nt._path_lexists`:

| Claims / plans | Baseline existence queries | Final existence queries | Eliminated queries / projections |
| --- | ---: | ---: | ---: |
| 0 / 1 | 32 | 20 | 12 |
| 0 / 11 | 342 | 210 | 132 |
| 8 / 1 | 617 | 388 | 229 |
| 8 / 11 | 3,077 | 2,008 | 1,069 |
| 16 / 1 | 1,201 | 756 | 445 |
| 16 / 11 | 5,821 | 3,816 | 2,005 |

The other counted `nt.stat` and final-path calls stayed identical in every pair.
For 16/11, validation was 3.276 s → 3.416 s in the single POC samples, with
identical 2.969 s CPU: again, no extra wall-time speedup is established. The
timing decision is supported by both runtimes rather than selecting a favorable
early sample.

The combined prototype's 64-claim pilot took 8.998 s setup and 15.911 s registry
validation. Given the mixed incremental benefit, the bounded-cost decision was
to stop large benchmark work after this pilot. The earlier 1,024-claim run
belongs to the first implementation; no final-refinement 1,024+ speedup is claimed.
The remaining claims × plans work still needs an architecture change for a
large reduction. An index must account for mutable physical topology, and a
lock-wait improvement must address contention while remaining compatible with
older coordinator processes.

The production change is restricted to deleting `_existing_chain` and building
the same lexical ancestor list inside `project_path`. The new regression covers
the initial leaf becoming absent, a regular file or a directory link before
ancestor checks. Fresh checks and the strict-resolution retry remain. No claim
records, lock protocol, durability fences or publication checks were changed.

## Final verification

- Python 3.14.4 full non-CMake suite: **1,724 passed, 41 skipped** (88.31 s).
- Python 3.12.9 coordinator suite: **87 passed, 6 skipped** (61.56 s).
  The existing repository pytest package was reused through this process's
  import path with plugin autoload disabled; no packages were installed.
- Python 3.14.4 focused CMake integration suite: **16 passed, 1 skipped**
  (69.70 s), including lock-wait diagnostics, recovery, competing writers and
  the test-registry isolation check.
- Both final Python 3.12.9 POC matrices completed, including continuous progress
  and completion diagnostics with no cutoff.
- `ruff check src tests cmake/ProtocyteOutputCoordinator.py`: passed.
- `git diff --check`: passed.
- Final source hashes match the measured final benchmark and POC candidates;
  the follow-up baseline hash matches the first implementation's large run.

Cross-platform runtime verification remains outstanding. No C++ files were
changed, and all fixture registries/data remain private and explicitly isolated.

For the subsequent under-30-second target, see the [synthetic-equivalence and
architecture assessment](registry-validation-30s-plan.md), including a bounded
phase profiler and explicit performance/safety milestones.
