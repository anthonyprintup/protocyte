# Ownership-index experiment

The experiment is on `codex/experimental-generation-engine`, directly above
preservation commit `f804fd1` on `codex/issue-54-registry-scaling`. The preceding
work was committed before branching; no remote publication or consumer-registry
maintenance was performed.

## Result and limit

At **2,172 retained claims and 11 current plans**, the read-only sampled index
took **28.480 s**, with another **1.184 s** for ordinary current-plan validation:
**29.664 s** combined. It read all **4,344 claim/plan records** and indexed all
**4,344 root/staging reservations**. Setup took **372.588 s** separately; lock
preparation/acquisition took **0.666 s** separately.

This is an algorithm-phase result, **not a safe under-30-second reconciler**.
That run did not execute the fresh registry reference pass after setup, authorize
reconciliation or produce claim tokens. The reported 751.875-second consumer
observation was not rerun, and equal claim/plan counts do not calibrate the
synthetic filesystem layout to the consumer workload.

The only executable validation modes remain `reference` (default) and `shadow`.
Shadow always performs the fresh reference pass before proceeding, and fails
closed on disagreement. Thus the deployed/default behavior has no claimed
large-case speedup from this experiment, and shadow adds measurement work.

## Implementation

- A pure Python index retrieves possible conflicts using lexical prefixes and
  physical endpoint/ancestor keys, including normalized missing suffixes. It
  preserves ownership and retirement exemptions and performs no filesystem I/O.
- One scoped preview authenticates retained records and collects bounded sampled
  geometry. Samples are discarded when the preview ends. They cannot authorize
  initialization, reconciliation, retirement or publication.
- Shadow runs behind the existing coordinator entry point and lock order. Every
  reference rejection is preserved; preview failure cannot grant authority.
  Diagnostics contain counts, timings and agreement, without private paths.
- The optional helper installs beside the coordinator. An actual installed,
  relocated-prefix test exercises shadow mode and verifies that the entire
  package prefix remains unchanged, including absence of bytecode-cache writes.
- Full benchmark/POC shadow modes retain all checks. A separate read-only tool
  labels its unverified scope explicitly. Measurements fingerprint both source
  files and reject a run if either changes while it is being measured.

Existing CMake helpers and normal installation/build commands require no new
configuration. The broader Python packaging and public generation CLI changes
remain a later stage of [the engine proposal](generation-engine-proposal.md).

## Work counts and measurements

The exact-size preview made **6,542 sampled geometry projections** and **4,370
directory observations**, then answered **22 index queries**. Geometry projections
exclude the original JSON-loader path checks. Including the two fresh JSON-path
projections per claim gives **10,886 total projections** for this fixture.
Compare that with the prior reference operation-count inference of **254,257**
for this shape: about **23.4 times fewer projections**, not a measured end-to-end
wall-time ratio. There were still **200,446 `stat`**, **15,253 `lstat`**, and
**21,772 final-path** calls in the preview, so filesystem work remains substantial.

A full shadow sample with eight retained claims, eleven current plans, three
targets per plan, existing root/staging directories and one shared build root
accepted in both phases. It checked 16 records in each phase and indexed 32
reservations. The sampled phase took **0.333 s**, fresh registry reference
validation **8.810 s**, and current-plan validation **3.316 s**. Full
reconciliation took **13.891 s**, including locks and output-state reconciliation.
Those costs have not been hidden in the preview number.

The sanitized source fingerprints, complete phase metrics, 256-claim scaling
sample and anonymous layout variants are in
[experimental-index-results.json](experimental-index-results.json). Measurements
used CPython 3.12.9 on Windows, include instrumentation, and are individual
workstation samples. A fresh fixture/process does not imply a cold OS cache.
The exact-size run leaves essentially no margin for a safe lifetime mechanism
or slower layouts; it also misses the proposed 25-second research budget.

## Correctness evidence

- The full default Python regression suite passed, followed by **17 passed,
  1 skipped** CMake integration tests.
- The existing coordinator suite in shadow mode passed: **87 passed, 6 skipped**.
- Python 3.12 coordinator/index compatibility checks passed: **113 passed,
  6 skipped**. These include 26 new index tests.
- Fixed-seed differential tests compare indexed results to exhaustive geometry
  across aliases, missing suffixes and prefix boundaries. Focused tests cover
  ownership/retirement exemptions and disjoint-query scaling.
- Injected foreign root, staging and ancestor replacements, plus a simulated
  physical alias introduced after sampling, are rejected by fresh reference
  validation before new claims are initialized. Injected preview false positives,
  false negatives and parser errors cannot authorize a mutation.
- Read-only-preview tests prohibit filesystem mutation, retain abandoned state,
  enforce sample expiry and preserve the CLI token protocol.

These tests establish the safety of retaining reference authority. They do not
prove that sampled topology remains valid or that index-only operation is safe.

## Promotion gate

The remaining problem is the filesystem-observation lifetime, described in
[the experimental contract](experimental-index-contract.md). A registry lock
does not prevent foreign paths from changing. A second matching metadata sweep
or a filesystem watcher is insufficient to establish continuous validity.

Before removing the reference pass, define and review a mechanism that preserves
all relevant name/object/missing-component bindings through the mutation
boundary, with bounded fail-closed recovery. Test its exact race and alias
semantics, then measure **all** its work on the large case and representative
layouts. The fast preview alone provides neither that proof nor enough timing
margin. No index-only authorization switch is provided in this experiment.
