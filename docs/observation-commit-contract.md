# Experimental observation commit

Status: experimental `commit-shadow` and `indexed` integrations on
`codex/experimental-generation-engine`. The
[retained consumer qualification](consumer-validation-results.md) failed the
reliable-under-30-second timing gate. The default remains reference validation.
An explicit source guard blocks consumer index authority, including the private
API and CLI. Isolated fixtures and the mutation-forbidden read-only harness can
exercise the proposed indexed success path; it accepts only a verified, fully
closed read set. Other outcomes use reference validation.

This replaces the previous fresh-observation experiment's repeated full path
walks with a provisional read set. Its certificate verifies the requested native
object/version witnesses; it is not unconditional namespace authority. The read
set is discarded before reference fallback or an indexed acceptance, and before
any reconciliation mutation. There is no persistent filesystem cache, new claim
format, change to the ownership lock namespace, watcher, service, or privileged
setup. A separate observer mutex coordinates the journal markers described below.

## Scope and dependencies

The caller holds the existing registry, generation, and publication locks in the
existing order. Cooperative coordinators therefore cannot change the ownership
records while they are being authenticated. Each retained claim and recorded
plan is still read and checked against its canonical JSON encoding, record
schema, root key, build identity, plan digest, and projected paths. The index is
an in-memory derivative, never a replacement for authenticating those records.

The prototype accepts local DOS-drive paths on NTFS with an already active USN
journal and the required ordinary-user handle operations. It does not create or
configure a journal. Unsupported paths, filesystems, access, case-sensitive
directories at initial observation, record formats, API responses, resource
budgets, or changed observations abandon the candidate and run the reference
validator. A missing
capability never requests administrator access or a user configuration change.

Windows object identity consists of the volume serial and the full 128-bit file
ID. Reaching a second drive with an already observed volume serial forces
reference fallback, preventing ambiguous root-handle routing. Every positive
path component is observed through a short root-relative
native open with `OBJ_DONT_REPARSE`. Only volume-root handles survive a lookup;
ordinary build, staging, registry, and record handles are promptly closed, with
read/write/delete sharing. A competing cleanup can delete an observed directory;
this invalidates the candidate instead of keeping the directory delete-pending
behind a long-lived handle.

Positive reuse also requires every component's input spelling to exactly match
the canonical native spelling. Case variants, short-name aliases, and other
noncanonical spellings fall back. This is a correctness boundary, not a path
normalization performed on behalf of the caller.

## Positive read-set argument

For each unique positive object, the prototype performs these steps:

1. Obtain its identity and force a USN close record **before** collecting its
   type, canonical path, ancestry, or contents. Save the returned USN.
2. Collect provisional facts. Reusing a previously observed object never resets
   its starting USN, including when reached through a case alias.
3. Finish all indexed computations, re-enumerate relevant registry inventories,
   and recheck DOS-drive and positive name bindings with root-relative opens.
4. Require each reopened object's identity and current USN to match the initial
   values. Force a new close record and retain its exact returned USN.
5. Retrieve the **specific** end records. Every requested USN must identify the
   expected file and contain exactly `USN_REASON_CLOSE`. Any accumulated reason,
   missing record, wrong ID, duplicate witness, unknown version, malformed data,
   journal reset, trimming, or bounded-read failure abandons the candidate.

The end close record matters: equal metadata snapshots alone cannot rule out an
ABA change or pending reasons on a writer opened before observation. Microsoft
documents that a forced close includes current reasons for the file and returns
the USN associated with that operation. The filesystem specification describes
posting a nonzero USN change as advancing the volume sequence and updating the
file's USN. The inference used here is that a relevant NTFS mutation during an
object's observation interval either changes its version or appears among the
forced end record's reasons. The native tests exercise rename, content/timestamp,
and attribute-only reparse ABA changes, including a preexisting writer primed
with the same reason before registration. Additional tests inject those changes
after the last version read but before the end close is posted: the dirty end
record must reject a change that the preceding version read could not see.

An adversarial native test found a counterexample to treating **all** metadata
as versioned: changing a directory's case-sensitivity flag and changing it back
can leave its USN unchanged and produce a clean end marker. The candidate does
not certify that flag's stability. It rejects initially case-sensitive objects
and rejects noncanonical positive spellings. An exact existing name binds to
the same object in either case mode; changing or removing that object's name
requires a rename/deletion witnessed by its version. Thus the reused geometry
does not depend on a case alias remaining usable. Fresh negative probes still
use the caller's exact spelling. Tests preserve the unjournaled flag
counterexample, test the exact-binding case, and require aliases to fall back.
The case-folded lexical predicate remains the reference validator's conservative
overlap rule; it is not used to resolve a native positive object.
Microsoft describes the lookup behavior under the directory flag in
[per-directory case sensitivity](https://devblogs.microsoft.com/commandline/per-directory-case-sensitivity-and-wsl/).

This argument covers the anchored NTFS objects. DOS-device mappings are outside
the NTFS journal: reopening each drive at seal checks its final binding, not
whether it was temporarily remapped and restored. After each root is bound, all
lookups and refreshed negatives use its retained volume-root handle, so a
temporary DOS remapping cannot supply cached geometry from another volume.
Final bindings must still match. Later mutation checks resolve their paths
afresh under the unchanged v1 rules.

Reading canonical record bytes under the registry lock retains the reference
implementation's cooperative-writer model; it does not claim an atomic data
snapshot against unsynchronized memory-mapped writers. The v1 writer protocol
uses the same existing locks and durable record operations. This is a retained
trust boundary, not a new guarantee about arbitrary external writers.

Sources for that inference:

- [Forced close record and accumulated reasons](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_write_usn_close_record)
- [Filesystem forced-close operation](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/6b3e0c41-83b4-403e-bdf1-8443eafa8f00)
- [Posting a USN change](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/2c897c5e-b29e-464d-825f-565ff587f7f1)
- [Root-relative object attributes and reparse refusal](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes)

The unprivileged journal transport has narrower public documentation than the
ordinary volume read API. On the tested host, directory handles supply journal
epoch queries and unprivileged reads whose names are redacted. The implementation
uses the public V2/V3 record headers and requires positive coverage of every
exact marker. It never treats the absence of an event in this filtered transport
as evidence that nothing changed. A transport that omits a required marker
cannot produce a certificate. Native mutation tests qualify the relevant
semantics on the measured Windows/NTFS host. This does not claim a test matrix
covering every Windows build, filesystem filter, or security product; capability
failures or unverified replies on another installation use reference validation.

## Missing paths are not indexed as stable

Creating a child does **not** necessarily advance its parent's USN. A parent
version is therefore insufficient evidence that a previously missing child
remains absent. Missing roots and staging paths stay in a separate partition.
Whenever either side of a directional overlap comparison is missing, its first
missing component is freshly probed relative to the held volume root with
reparse traversal refused. The reverse direction refreshes those observations
again. The final binding sweep checks them once more. A dangling junction is an
existing reparse point, not a successful negative lookup.

The positive partition uses the independently tested pure ownership index.
Comparisons against the negative partition retain fresh namespace checks; a
negative current endpoint compares against every reservation. Ownership and
same-build retirement exemptions remain the reference rules. This intentionally
retains an O(claims × plans × targets²) negative-check term. A faster sampled
index that assumes all missing paths remain absent would not meet this contract.

As with the reference validator's successive fresh probes, absence can change
between system calls. This experiment does not claim an atomic snapshot or a
namespace freeze. Its goal is to justify cached **positive** geometry during the
calculations while preserving fresh negative checks. Existing mutation-time
checks remain necessary. The integration's boundary is a completed past
validation computation: seal has verified the positive intervals, all native
handles have been released, and the read set has been erased before the caller
can enter the unchanged reconciliation and mutation methods. There is no new
claim that namespace stability persists after validation returns.

## Expiry, fallback, and operational costs

Instances are local to one validation phase. Sealing disables further reads;
closing releases roots and clears all observations, locators, inventories, and
object tables. No certificate or path facts cross into claim initialization,
recovery, publication, reset, or the next invocation. A failed or unsupported
commit still runs the ordinary reference validator. Indexed conflicts also use
reference validation, preserving its diagnostics and acceptance behavior.
`commit-shadow` additionally treats a verified candidate conflict followed by
reference acceptance as a disagreement and fails closed.

The experiment posts journal metadata records on observed objects, including
common ancestors. It does not modify their contents or namespace. These posts
are real filesystem work and are included in timing and operation counters.
They can invalidate another observer's saved versions even when neither changed
the geometry. Same-registry operations already serialize through the existing
lock. New observers in independent registries additionally share a per-user
`observation-commit-v1.lock` beneath the ordinary user cache (or temporary
directory fallback). It is acquired inside the existing ownership locks and
released before reference fallback or mutation. No additional ownership lock is
acquired while it is held, so it introduces no reverse lock-order dependency.
It changes neither registry identity nor old/new ownership exclusion. Other
users, older prototypes, or external marker writers can still invalidate a
candidate; such collisions conservatively fall back to reference validation.

Bounds are 32,768 unique objects, 16 MiB per ownership record, and 64 MiB of
journal transport per volume. Exceeding them falls back. Metrics include native
opens, information queries, negative probes, close posts, version reads, epoch
queries, journal bytes/reads, record seeks/reads, directory enumerations, complete
registry inventories, name-binding checks, and opened/closed handle counts.
Published diagnostics retain no unrelated journal names, claim contents, paths,
or tokens. An exception records its type, not its message.

## Upgrade contract and promotion gate

Normal installations continue to use reference validation. Neither consumer
configuration nor the hidden experiment flag can override the closed promotion
guard. Only a future reviewed source change after qualification can promote it.
Packaging installs
the additional trusted sibling Python helper, without requiring a new consumer
command or runtime dependency. Protocol v1, plan serialization, claim tokens,
lock locations, and recovery/publication formats are unchanged. Old and new
coordinators must be able to alternate, including recovery across crash cuts.

One independent reference fix inspects a retained `plan.json` with `lstat` and
treats only `FileNotFoundError` as absence. A dangling link is rejected as
malformed state; inaccessible metadata fails validation instead of silently
skipping the record. Valid registries need no migration, reset, regeneration, or
token rotation. Malformed or unreadable recorded state requires its underlying
problem to be repaired rather than being skipped.

Promotion remains closed until all of the following have evidence:

- Relevant native mutation semantics and fallback behavior are qualified for
  the enabled capability, with the namespace and writer boundaries above explicit.
- Differential, race, malformed-state, crash-recovery, packaging, minimum-Python,
  and old/new upgrade checks pass with the final source fingerprints.
- **All validation**, including current plans, every retained record, fresh
  negatives, inventories, versions, witnesses, and handle release, reliably stays
  below 30 seconds at the target scale and representative layouts/contention.
- A reviewed authoritative integration preserves the mutation-time boundary.

The read-only candidate benchmark reports that entire candidate cost separately
from its optional reference oracle. It produces no tokens and authorizes no
reconciliation. Ordinary `commit-shadow` timings always include the mandatory
reference pass; candidate timing must never be presented as that full operation.
