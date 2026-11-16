# Retained consumer qualification

Historical serial qualification at `8851bde`. Its failed timing gate and source
fingerprints are preserved here. The subsequent
[parallel-probe qualification](parallel-probe-results.md) passed the gate and
documents the current automatic default on the experimental branch.

This report uses an anonymous retained consumer configuration, not a synthetic
replacement. Raw manifests, logs, claim tokens, ledger copies, paths, and output
names stay in ignored local evidence. **Promotion failed:** six of ten complete
integrated validations exceeded 30 seconds. The default remains reference, and
an explicit source guard prevents consumer commands or the private API from
granting index authority. The success path is exercised only in isolated tests
or the mutation-forbidden read-only qualification harness.

## Workload identity and scope

The retained configure log contains the exact original measurement:
**751.875 seconds validation**, 0.328 seconds lock wait, 1.969 seconds
reconciliation, and 754.172 seconds total. It identifies 2,172 registry claims
and 11 current plans. The cached coordinator's SHA-256 is
`2ff54b69242d46eb8e35a52d30b32bc9afd815c00b6c0abeb8765d6fe7ddbb85`,
matching the pinned public source used by the upgrade qualification.

The same configuration still has 11 current plans, one target each, and 232
declared generated files. The shared v1 registry now contains **2,239 claims**,
67 more than the historical run, and **4,478 claim/plan records**. The extra
records are retained and checked. No registry was reset, pruned, split, or
replaced. Measurements use CPython 3.12.9 on Windows, with native observations
on two NTFS volumes.

Two distinct read-only procedures keep the live consumer usable:

- Candidate and integrated indexed validation acquire the original registry,
  generation, and publication locks in their original order and validate the
  complete live registry against the original current plans.
- Slow reference oracles operate on byte-identical ledger copies captured under
  those locks. Their claim payloads still refer to the real output, build, and
  staging paths. Each oracle also executes the original lock-namespace checks
  separately. The full copied-ledger pass filters no foreign records. It does
  not hold the shared consumer lock for several minutes.

The helper rejects ownership/output mutation attempts. It never reconciles,
publishes, resets, produces a claim token, or changes production defaults. A
separate preservation audit checks original claim/plan bytes, current snapshots,
generated file hashes, and generated file mtimes.
Source roots, states, and record files must be ordinary non-reparse objects;
capture rejects unsafe source topology rather than copying it into a clean tree.
Native validation posts the counted USN metadata witnesses described in the
contract; read-only here refers to ownership records and generated content.

## Final integration decision

The ten fresh-process integrated samples were **26.174, 35.604, 39.803, 36.978,
40.636, 41.542, 31.042, 27.058, 27.433, and 25.668 seconds**. All accepted the
same complete live ledger with verified end witnesses, no reference pass, and
balanced handles. Only **4/10** were below 30 seconds. The median was
**33.323 seconds**, and the worst was **41.542 seconds**.

Relative to the exact historical 751.875-second measurement, the median is
**22.56 times faster (95.57% less time)** and the worst is 18.10 times faster.
Relative to an approximate 700-second baseline, the median is 21.01 times faster
(95.24% less time). These are descriptive comparisons across different runs,
not controlled claims about the algorithm alone. They describe the proposed
indexed path, not a speedup delivered by the unchanged reference default.

One separate cProfile run attributed **15.791 of 30.202 profiled seconds** to
the **261,703 fresh negative probes**. Each unprofiled gate sample retained
84,579 fresh reservation comparisons, two full registry inventories, 17,958
close posts, 8,979 exact end witnesses, and all 26,916 handle closes. Alternate
fresh root-relative lookup microbenchmarks did not establish enough improvement
to close the observed timing gap reliably; no alternate API was shipped.
Caching negative results would remove a correctness check and remains rejected.

A separate read-only prototype scheduled independent fresh comparisons on four
workers, joining them before seal or handle release. It preserved all 261,703
negative probes and verified every witness. Its two runs took **24.284 and
16.795 seconds**; the paired serial run took **21.648 seconds**. The second
parallel run used **22.266 CPU seconds**, versus 18.500 for the paired serial
run. This is promising feasibility evidence, with additional CPU cost, not a
completed reliability or concurrency qualification. Production scheduling was
not changed. Worker teardown, exceptional exits, counter synchronization, and
the complete timing gate need evidence before adopting it.

After the failed series, the final source added the closed promotion guard.
Extra guarded read-only smoke samples check that prototype path and the final
preservation audit. No performance change follows the failed series: the native
helper is byte-identical. Those quieter samples do not reset the failed timing
history or justify enabling the index. Full per-run metrics, exact as-run and
Git-normalized source fingerprints, and preservation receipts are retained in
[the anonymous JSON report](consumer-validation-results.json).

## Completed reference and candidate checks

| Measurement | Validation wall time | Result |
| --- | ---: | --- |
| Historical original consumer log, 2,172 claims | 751.875 s | Accepted |
| Exact original source, frozen 2,239-claim ledger | 785.311 s | Accepted |
| Branch reference validator, same frozen ledger | 595.759 s | Accepted |
| First strict native candidate, live 2,239-claim ledger | 25.716 s | Verified, accepted |
| Five subsequent fresh-process strict candidates, live ledger | 17.613, 17.447, 17.314, 16.888, 16.807 s | All verified, accepted |

The two long reference measurements overlapped; their timings describe those
runs rather than a controlled speed comparison. Their purpose is complete
oracle agreement on the retained workload. The candidate times include current
plan parsing, current-plan set checks, all record authentication, index
construction, fresh missing-path comparisons, final inventories and bindings,
USN versions, exact end witnesses, and handle release. Lock wait is separate.
They exclude reconciliation and an additional reference pass.

These initial runs precede the final observer coordination and duplicate-volume
hardening. Their exact source fingerprints remain in the machine-readable
report. They are feasibility evidence, not final-source promotion evidence.
Each invocation builds a new read set and reauthenticates every record. The
workload and OS caches are reused; no cold-cache claim is made and no cache or
security setting was changed.

## Correctness and upgrade boundaries

The [observation contract](observation-commit-contract.md) explains which native
facts are certified. Existing positive paths require exact canonical spelling;
missing paths are freshly checked in both comparison directions and at seal.
Relevant mutations must change the saved version or make the exact forced end
record dirty. Native tests inject rename, record-content, and attribute-only
reparse ABA changes after the last version read, verifying that end witnesses
close that gap. Tests retain the unjournaled case-mode counterexample.

When enabled only inside qualification, the integrated path can return index
authority only after a verified seal and complete handle release. Incomplete
or inconsistent metrics grant no authority.
Conflicts and unavailable, changed, malformed, or over-budget observations run
the reference validator, preserving its diagnostics. Abandoned state uses the
reference cleanup path. A per-user observer mutex prevents independent new
observers from invalidating common-ancestor markers; it is released before
reference fallback and never replaces the existing ownership locks. Duplicate
volume serials reached through another drive binding force fallback.

No facts cross into initialization, recovery, publication, reset, or another
invocation. Those mutation methods and the ownership locks remain unchanged.
Protocol v1, record encodings, tokens, and recovery formats need no migration.
The independent recorded-plan metadata fix rejects dangling links and metadata
errors instead of silently skipping retained state; valid users need no reset.

## Reproduction and privacy

Verification passed: **1,863 default tests** (41 platform/capability skips),
**137 minimum-Python checks**, **89 indexed coordinator tests** (6 platform
skips), **91 old/new upgrade and crash-recovery cases**, and **21 CMake checks**
(1 platform skip), followed by **5 final-source relocated-install checks**.
The latter include default operation and rejection of the unqualified index
flag. Upgrade fixtures exercised 15 native acceptances and one recovery-state
fallback. A formatter test's reproduced startup assumption was replaced with
startup margin and a descendant release handshake, retaining its timeout and
tree-termination assertions; the complete suite passed afterward.

Use [the qualification helper](../tests/verify_consumer_registry.py) with a
private JSON manifest containing `registry`, `current_plans`, empty
`retired_plans`, and `legacy_coordinator` paths. Run `capture` into a new private
work directory, then `candidate`, `indexed`, `reference`, `legacy-reference`,
and `audit` as needed. The indexed mode exercises the production validation
entry point and requires index authority with no reference pass.
It overrides the closed promotion guard only in its own imported module, after
disabling all reconciliation, recovery, publication, reset, and mutation entry
points. A failed candidate aborts the live trial rather than blocking the
consumer for a slow reference pass; full reference fallback is checked separately.

Publish only sanitized `*-results.json` receipts. `preservation.private.json`,
`ledger/`, `inputs/`, raw logs, and the manifest contain private data and must
remain local. The frozen-reference tests verify both original-namespace and
foreign-staging rejection so copying the ledger cannot omit those checks.
