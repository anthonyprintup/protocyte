# Observation commit experiment: results

This is the historical synthetic qualification at commit `0fe8ad4`. Its source
fingerprints and closed promotion decision are retained below. See the newer
[retained consumer qualification](consumer-validation-results.md) for subsequent
real-workload measurements and the current integration decision.

The index remains **disabled as an authority** on
`codex/experimental-generation-engine`. The new read-set experiment has a safe
shadow integration, useful native evidence, and passing upgrade checks. It has
not met the requirement for reliable full validation below 30 seconds.

The default is still reference validation. There is no index-only command or
automatic promotion. The private `--experimental-observation-commit` switch runs
the candidate and then mandatory reference validation before reconciliation.
Unsupported capabilities, changed observations, and candidate failures fall
back to reference. A verified candidate conflict that reference accepts fails
closed before claim initialization.

## What changed

[ProtocyteObservationCommit.py](../cmake/ProtocyteObservationCommit.py) implements
one bounded optimistic read set. It collects positive geometry after a forced
USN close marker, authenticates every retained claim and plan, and checks final
identities and versions against exact close-record witnesses. Missing witnesses,
dirty reasons, unknown formats, changed epochs, and bounded-read failures cannot
certify a candidate. The unprivileged journal stream is used to retrieve specific
positive witnesses; missing events are never interpreted as proof of stability.

Only volume-root handles remain open between lookups. Ordinary directories and
record files use short opens, so deleting and recreating an observed build
directory is possible and invalidates the candidate. Observations expire before
reference validation, claim initialization, recovery, and output mutations. The
normal lock order and lock namespace remain unchanged.

Missing paths are deliberately excluded from the stable index partition. Every
directional overlap comparison refreshes its missing endpoints, and seal checks
them again. This preserves the expensive term in missing-directory layouts.

The [contract](observation-commit-contract.md) gives the consistency argument,
primary API sources, supported capabilities, costs, and remaining proof
boundaries. The certificate verifies its requested native witnesses; it is not
an unconditional filesystem snapshot or permission to skip reference validation.

## Measured target scale

The synthetic registry contains **2,172 real retained claims and 11 current
plans**, with one target per plan and missing output/staging directories.
Measurements use CPython 3.12.9 on Windows. Each run authenticates all **4,344
ownership records** and includes current-plan validation, the complete candidate,
final inventories, versions, close witnesses, and handle release.

| Measurement | Run 1 | Run 2 | Run 3 |
| --- | ---: | ---: | ---: |
| Final-source full candidate validation, wall/CPU timers without cProfile | 25.317 s | 19.984 s | 18.575 s |
| Earlier snapshot, with cProfile | 38.050 s | 40.208 s | 35.478 s |
| Earlier snapshot, wall/CPU timers without cProfile | 45.660 s | 55.897 s | 81.725 s |

All three final-source quiet samples pass 30 seconds. They establish feasibility
for this reused synthetic layout, not reliable performance across configurations
and contention. The six earlier samples precede the final reference
metadata-error correction; the native observation helper is byte-identical.
They retain their own source fingerprints and are explicitly historical in the
report. The large timing spread remains a reason to keep the promotion gate
closed. These are separate workstation runs, not controlled comparisons of
profiler overhead. Timer-only runs retain every validation check and counter.

Each candidate run performed **95,568 fresh reservation comparisons**, **412,812
negative probes**, **21,768 forced close posts**, and verified **10,884 exact
end witnesses**. It performed two complete registry inventories, plus per-state
enumerations, and balanced all **30,458 opened and closed handles**. Native
information, file-read, seek, final-path, epoch, and journal calls are also
reported. Python's small `stat` count must not be presented as total filesystem
work.

The registry was seeded once in a fresh private fixture, taking 330.130 seconds.
The three final-source samples reuse that fixture, create new read sets, and
reauthenticate every record each time. Setup and lock wait are reported
separately. A reused fixture or new process does not imply a cold OS cache.
The synthetic dimensions match the reported consumer case; its contents and
layout are synthetic. No consumer registry was accessed.

These large runs are read-only candidate measurements: they produce no current
claim, token, reconciliation, or publication. They do not include a subsequent
reference pass and are not timings of the currently authorized reconciler.
As in the API benchmark, current plan files are parsed during fixture
preparation; CLI plan parsing is outside these validation phase timings.

Final-source full shadow samples retain reference and reconciliation costs:

| Layout (11 current plans) | Candidate registry phase | Reference registry phase | Current-plan set check | Entire reconcile call |
| --- | ---: | ---: | ---: | ---: |
| 64 claims, one target, missing directories | 0.780 s | 10.124 s | 0.512 s | 12.309 s |
| 8 claims, three targets, existing directories, shared build root | 0.154 s | 4.809 s | 2.233 s | 8.173 s |

Both phases accepted in each sample, verified every required witness, and
balanced all handles. Each full sample counted **three** registry inventory
scans: two native candidate inventories and one reference scan. Per-state
enumerations are additional work. The complete counts and fingerprints are in
[the path-free report](observation-commit-results.json).

A fourth final-source target-scale run also executed the complete fresh
reference oracle on the same **2,172/11** fixture. The full read-only candidate
took **22.056 seconds**; the separate reference registry pass took **310.043
seconds**. Both accepted, all witnesses verified, and the fixture retained its
original 2,172 claims. No current tokens or reconciliation were produced. This
is agreement evidence and a phase comparison, not an enabled production speedup.

## Counterexamples and rejected optimization

- Parent-directory USNs do not reliably change when a missing child is created.
  Parent versions therefore cannot justify cached absence. Native tests cover
  creation after observation and changes between the two comparison directions.
- Case-mode changes can leave the directory USN unchanged, even after an ABA
  toggle. Positive reuse now requires exact canonical spelling; aliases fall
  back instead of assuming their continued usability. Tests retain this
  counterexample and exercise exact bindings in both end modes.
- A writer opened before registration can repeat attribute-only reparse changes
  and restore the original directory. Forced-close/version tests reject this,
  including a writer primed with the same reason before the observation began.
- Holding ordinary directory handles for the whole operation obstructs cleanup.
  The retained implementation closes them promptly and tests delete/recreate.
- A bounded parent-handle batching variant kept fresh probes, but added opens
  and request construction without lowering negative-query cost. Its first
  profiled target-scale validation took **46.832 seconds**. It was removed; the
  report identifies its different source fingerprint and rejected status.

The retained version's profile spends most of its time in negative namespace
queries. Further progress needs a proven way to avoid repeated missing-path
checks. The unprivileged journal's filtered, redacted stream is not proof that
all relevant namespace changes were absent.

## Upgrade and regression evidence

- Default suite on Python 3.14.4: **1,834 passed, 41 skipped**.
- Existing coordinator suite through commit-shadow: **89 passed, 6 skipped**.
- Observation/index and metadata-error tests on minimum Python 3.12:
  **109 passed**, no skips.
- CMake/installed relocation checks: **19 passed, 1 skipped**. All three private
  modes work after relocating the package, leave its files unchanged, and write
  no bytecode caches into the prefix.
- Offline upgrade/rollback qualification: **71 passed cases** against the exact
  public protocol-v1 source blob `25f1660190d3d1015fef3955814c8c737bd686c5`, also
  present at commit `72fc9087f6d7fd1c133aaf33903df8ca1585fe69`. Its SHA-256 is
  `2ff54b69242d46eb8e35a52d30b32bc9afd815c00b6c0abeb8765d6fe7ddbb85`.

Upgrade cases alternate old/new coordinators, preserve existing claim bytes,
tokens and no-op output timestamps, publish in both directions, and recover
across four publication, two initialization, and three reset crash cuts. The
harness also verifies twelve mutation/lock methods and `FileLock` remain AST
identical to preservation checkpoint `f804fd1`. The reference-validator AST is
not identical: observation adapters and explicit validation fixes are recorded
rather than claiming the whole implementation is unchanged.

Normal consumers need no new configuration, dependency, privilege, migration,
reset, or token rotation. Protocol v1, plan encoding, publication and recovery
formats remain compatible. The helper is installed through existing CMake
packaging; generated C++ and runtime ABI are untouched.

One reference fix intentionally rejects a dangling retained `plan.json` link,
which was previously skipped as if no recorded plan existed. It uses `lstat`
and treats only `FileNotFoundError` as absence: inaccessible metadata must also
fail validation. Regression tests prove rejection before a new claim is
initialized and preservation of the existing token. Valid registries retain
their existing behavior; malformed or unreadable state must be repaired.

## Remaining promotion blockers

Sub-30-second validation is demonstrated in three quiet one-target samples;
reliability across fresh layouts and contention is unqualified. More targets
multiply the fresh negative comparisons. Independent read
sets can also invalidate each other's common-ancestor versions with their own
close markers, causing a conservative reference fallback. The experiment adds
real journal metadata writes and does not remove the existing locks.

The native argument still needs qualification across supported Windows/NTFS
configurations. DOS-device mapping lifetime and unsynchronized record writers
are explicit boundaries in the contract, and no atomic namespace freeze is
claimed. Existing mutation-time checks remain necessary. An authoritative
integration requires separate review of those boundaries even if future
candidate timings improve.

## Reproduction

Run from a checkout with Python 3.12+; fixture/result directories must be new:

```text
python tests/benchmark_observation_commit.py --claims 2172 --plans 11 --large --repeat 3 --work NEW_PRIVATE_DIRECTORY
python tests/benchmark_observation_commit.py --claims 2172 --plans 11 --large --repeat 3 --no-profile --work ANOTHER_NEW_PRIVATE_DIRECTORY
python tests/benchmark_output_registry.py --registry-validation commit-shadow --claims 64 --plans 11 --repeat 1 --work NEW_SHADOW_DIRECTORY
python tests/verify_coordinator_upgrade.py --work NEW_UPGRADE_DIRECTORY
```

The public candidate tool seeds fresh fixtures per sample; the target-scale
measurements above used an explicitly reported reused fixture to avoid repeated setup.
Use `--reference-oracle` to time a separate fresh reference pass in the read-only
candidate tool. It still produces no current tokens or reconciliation.
Upgrade qualification requires the pinned source blob and checkpoint in local
Git history. Fixture directories, profiles, logs, claims, and tokens remain
private; share only the sanitized result JSON. Source-drift guards reject
measurements or qualification if the implementation changes during the run.

The report keeps the as-run source hashes and Git-normalized hashes separately.
Git changes only the coordinator's CRLF line endings to LF; byte normalization
and AST comparisons verify identical code for all four implementation files.
