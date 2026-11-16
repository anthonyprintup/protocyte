# Registry validation follow-up (#54)

## Analysis and proposal (before coordinator changes)

The current checkout includes #52: `reconcile_set` scans the registry once and
authenticates each retained claim/configured plan once, rather than once per
current plan. The remaining confirmed cost is the retained-claim/current-plan
cross product in `_validate_registry`, including root/root, staging/root,
root/staging and staging/staging comparisons. Every comparison projects both
paths and performs physical containment in both directions. Missing suffixes
are repeatedly searched for an existing ancestor; `samefile` adds two following
stat calls per ancestor beside the non-following identity checks. JSON loading,
current-plan all-pairs validation, lock waiting, reconciliation and fixture
setup are separate costs. Reported consumer timing is evidence of validation
cost, not proof that every metadata call is redundant or that claims leaked.

### Ownership and locks

A physical output root has an immutable claim (root/build identities and token),
a configured plan (targets, staging reservations and outputs), a committed
snapshot (generation and output digests), and possibly durable pending intent.
Publication recovers pending work by rolling forward. Initialization publishes
the snapshot before the claim. Reset authenticates ownership, persists absence
of owned outputs, and only then releases the claim. Empty plans and missing build
directories do not release ownership. Test-looking names and age are not proof
that a claim is disposable; this change will not prune retained claims.

Reconciliation takes registry, then sorted generation, then sorted publication
locks, retaining them through plan commits. Reset takes the same ordering for
one root. Generation holds its root generation lock; publication/validation
take the publication lock. Claim/plan writers serialize via registry; payload
writers serialize via publication. Keep these lifetimes and the shared namespace.
Reducing validation time reduces registry-lock occupancy without moving checks
outside the lock or introducing a writer race.

Locks do not freeze arbitrary filesystem topology. Projection rejects links,
junctions and non-directory ancestors, resolves Windows case/short spellings,
and appends a normalized missing suffix. Physical identity checks catch aliases
that lexical containment cannot see, including aliases of existing ancestors of
missing paths. File/directory, ancestor and reparse replacements can occur after
projection or between comparisons. The existing comment forbidding reuse across
comparisons is a safety contract, not an invitation to operation-wide caching.
Neither the existing nor proposed path API provides an atomic filesystem
snapshot against arbitrary external writers; mutation-time checks remain vital.

### Recommended bounded change

Keep the complete claim/current-plan cross product and two fresh projections
per `_paths_overlap`. Replace repeated physical ancestor searches with a local
physical ancestry observation in `_projected_physically_contains`. Observe each
component with non-following metadata, reject links/non-directories, identify
ordinary directories by device/inode (the same identity relation as `samefile`),
and represent missing descendants by that identity plus case-folded suffixes.
Compare the parent's location key against the child's ancestor keys. No
observations escape that single directional comparison. Retain the separate
reverse comparison and all projection, claim binding and mutation-time checks.
This reduces physical metadata work from quadratic in missing depth to linear in
total depth and removes following stat probes duplicating ordinary-directory
identity. Constructing all missing-suffix tuple prefixes still has quadratic
worst-case Python copying cost in missing depth; filesystem probes are linear.
For bounded targets/depth the registry remains O(claims * current plans), with
lower filesystem work; no sublinear registry-scaling claim is intended.

If measurements show projection dominates, assess its repeated metadata walks
separately; do not combine observations across comparisons to meet a timing goal.
The initial implementation surfaces are physical containment helpers, progress,
focused regression tests and the reusable benchmark.

Alternative: an operation-wide identity index could reduce projections toward
O(claims + plans), but external changes can invalidate a negative conflict lookup
without touching registry records. Fresh revalidation could restore the cross
product, while watcher-based invalidation is platform-specific and incomplete.
A durable ownership index also requires migration/crash recovery and does not
solve topology invalidation. Those are separate designs, not this bounded fix.
Pure lexical filtering is unsafe for physical aliases. No registry observations
will be reused across pairs, lock acquisitions, mutations, or publication.

Reconciliation must still freshly derive state/lock keys, authenticate claims and
plans, recover snapshots and validate output/staging topology before mutation.
Publication retains its own current-plan, payload, containment, destination and
transaction checks; no optimization token grants later filesystem authority.

### Progress, isolation and acceptance

Continue path-free phase/count/timing reports at five-second frequency for the
whole operation. Bound frequency rather than total report count; retain silence
for fast operations, completion/failure reports and clean stdout claim tokens.
Remove the lifetime cap; adapt the POC's progress metadata to report no cutoff
when that constant is absent. Leave its measured reconciliation method intact.

Direct coordinator tests already pass explicit temporary lock roots. CMake
ownership fixtures choose temporary `output-locks`; inspect other integration
fixtures before running them. Benchmarks must use a new explicitly isolated
registry for every sample. Keep synthetic records untracked because they contain
local paths. Only sanitized scripts, counts and timing summaries are deliverables.

Acceptance: existing adversarial/recovery/concurrent-writer tests pass; add
bounded-depth operation-count coverage, aliases of missing ancestors, replacement
after projection and between comparisons, and progress past the former cutoff.
Run the issue's unchanged measured `reconcile_set((), current)` POC matrix
(0/8/16 claims, 1/11 plans) before/after. Count filesystem calls as well as time;
keep setup separate. Adapt only the POC progress metadata if necessary, preserving
the production measurement unchanged. Extend the maintained benchmark to allow
thousands of claims with explicit opt-in and linear private fixture seeding using
real locked initialization/reconciliation, as in the issue POC. First run 64/11;
then cap larger work at one 1,024/11 sample if projected runtime is reasonable.
Do not run the old quadratic seeding path at thousands of claims. Record skips,
actual costs and limitations rather than inferring results from small samples.

## Implementation decisions after the pilot

The baseline coordinator's LF-normalized SHA-256 matches the issue exactly:
`2ff54b69242d46eb8e35a52d30b32bc9afd815c00b6c0abeb8765d6fe7ddbb85`.
The local checkout was retained on its existing history and a new task branch.
Private fixture directories are under ignored pytest storage.

The ancestry helper retains both directional observations and projection at
every pair. `samefile` uses the same device/inode equality now obtained through
non-following metadata for ordinary directories. Alias test doubles therefore
model matching directory IDs, rather than overriding only the removed stat API.
Added checks cover missing depth, ancestor replacement, Windows short spellings,
and the progress worker surviving the old lifetime cutoff.

The isolation audit found older CMake integration fixtures that exercise the
default selector. An autouse fixture gives marked CMake tests a private cache
base (`LOCALAPPDATA` on Windows, `XDG_CACHE_HOME` elsewhere), retaining a shared
namespace across build trees within each test. Explicit lock-root tests retain
their explicit selection. No existing shared registry was inspected or changed.

The 64-claim/11-plan pilot measured 9.02 s setup and 12.34 s registry validation.
The larger measured run is capped at 1,024 claims/11 plans, roughly six minutes
projected including setup; 2,048+ cases are supported but not measured here.
The benchmark now separately measures lock acquisition, actual registry-lock
occupancy, and current-plan validation, and enforces a new directory per sample.

The later [optimization review](registry-validation-refinements.md) evaluates
further metadata and locking changes. Its final refinement removes a repeated
existence search used only to construct the projection's ancestor list, while
retaining every component check, leaf type check, strict resolution and retry.
