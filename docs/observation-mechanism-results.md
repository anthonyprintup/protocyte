# Fresh observation experiment and rejected handle lease

The operation-wide observation proof and the under-30-second gate **have not
passed**. The index remains non-authoritative and disabled in normal use. This
experiment adds a bounded, fresh native path reader and tests a proposed handle
lease; it does not claim a safe cached-index replacement for the reference pass.

## What was implemented

`ProtocytePathObservation.py` provides an experimental Windows reader. Each call
opens an existing path with `NtCreateFile`, `FILE_OPEN` and `OBJ_DONT_REPARSE`,
checks the opened object's attributes, obtains its normalized path and closes
the handle before returning. Missing components are searched again on every
call. There is no filesystem-fact or negative-lookup cache, no watcher, no
persistent observation token and no topology freeze claim.

Microsoft documents
[OBJ_DONT_REPARSE](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes)
as refusing reparse traversal. The reader avoids combining `FILE_DIRECTORY_FILE`
with flags outside the compatibility list in
[NtCreateFile](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile).
It requests attribute access, shares read/write/delete and never creates or
writes files. It supports ordinary absolute drive paths; unsupported namespaces
or platforms use reference validation. Ordinary I/O errors are not converted to
successful negative observations.

The private `native-shadow` mode substitutes this reader into the existing
registry comparisons and record authentication, without removing the cross
product or fresh physical-ancestry checks. It then **always runs the ordinary
reference validator**. Native disagreement/errors fail closed if reference accepts;
reference rejection propagates. A known capability failure falls back to reference.
The native pass leaves abandoned-state cleanup to reference and never initializes
claims or reconciles outputs. Close failures also require reference verification
and cannot authorize initialization.

The native API bindings can survive the phase; filesystem observations and
handles cannot. Counters explicitly include native opens, attribute/final-path
queries and successful handle closes, so opaque ctypes calls are not reported as
eliminated filesystem work. Benchmark fingerprints include all three helper files.

## Why read-only handles do not prove operation-wide reuse

A real Windows adversarial test held an ordinary directory open with
`FILE_READ_ATTRIBUTES`, allowing only read sharing. A second attribute-only
handle still converted that directory into a junction with
`FSCTL_SET_REPARSE_POINT`. The native observer rejected the changed path on its
next call. The counterexample passed on this host; it was not a simulated alias.

This is consistent with Microsoft's
[sharing rules](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
which exclude attribute access from ordinary sharing restrictions, and the
[reparse operation specification](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/4aeefef8-92c3-4abc-af7a-a610caf8a165),
which permits the operation through write-attributes access. Keeping existing
directory handles open is therefore insufficient to retain cached name/geometry
authority. Missing children also cannot be protected by an ordinary read handle.

Directory-content oplock breaks remain advisory, as described in
[the initial contract](experimental-index-contract.md). USN journals are not a
drop-in proof either: reasons accumulate until close, so a complete protocol
must address existing open writers, forced posting, journal continuity and all
name/object dependencies. A bounded capability probe on this host could post a
close record for a new test directory, but a zero-access volume journal query
returned `ERROR_INVALID_FUNCTION`. No journal was created, resized or configured,
no elevation was requested for the application, and no journal-based authority
was implemented. These probe results do not establish availability on other hosts.

## Measurements and stop decision

The second measurement and the earlier four-case pilot are in
[observation-mechanism-results.json](observation-mechanism-results.json). Each
sample uses a fresh explicit synthetic registry and real locked fixture setup.
All timings include instrumentation and uncontrolled workstation/cache effects.

At **64 retained claims / 11 current plans**:

| Work | Pilot seconds | Second sample seconds |
| --- | ---: | ---: |
| Native fresh registry-validation phase | 9.197 | 11.421 |
| Mandatory reference registry-validation phase | 18.208 | 20.254 |
| Both registry phases | 27.405 | 31.677 |
| Separate current-plan validation | 0.852 | 1.556 |
| Complete reconciliation, including locks and output-state work | 29.591 | 35.245 |
| Separate fixture setup | 8.917 | 12.454 |

Each sample retains its measured source fingerprints. After the second sample,
the explicit extended-path namespace was conservatively restricted to reference
fallback because stripping that prefix would change existing ownership-key
spelling. This capability restriction was tested separately; the timings above
are not relabeled as measurements of that final source snapshot.

The native phase made **7,621 projections**, **14,663 opens**, **7,621 attribute
queries** and **7,621 final-path queries**. All **7,621 opened handles closed**.
Every one of the 64 retained claims/plans was authenticated in each relevant
phase. The full report retains both Python filesystem counters and native counters.

This is a smaller fixture than the 2,172/11 target, already consuming most of the
30-second budget in shadow mode. The native phase still repeats work across the
claim/plan cross product. A size-only projection of 9.197 seconds to 2,172 claims
would be roughly 312 seconds for that phase, **not a measurement or a lower
bound**. This mechanism fails the research cost gate; it is not reasonable to
claim that a small native-API substitution solves the target. No authoritative
index mode or automatic promotion was added, and no large reference run was
performed merely to reproduce another several-minute failure.

## Correctness and upgrade evidence

- Default regression suite: **1,772 passed, 41 skipped**.
- Existing coordinator suite with native-shadow: **87 passed, 6 skipped**.
- New observation tests: **22 passed**, including real reparse conversion,
  fresh missing/existing transitions, file/directory distinctions, scope expiry,
  unexpected status/permission failures, handle cleanup, fallback, and rejection
  before new claims after a foreign replacement.
- Minimum-version check on CPython 3.12.9: **48 passed** observation/index tests,
  including an existing explicit-namespace claim retaining its token and record
  through reference fallback.
- CMake integration: **18 passed, 1 skipped**, including both shadow modes from
  an installed, relocated package with an unchanged prefix.
- **51 cross-version upgrade/rollback/recovery cases passed** against the exact
  public protocol-v1 coordinator cited in #54, including native-shadow in both
  directions. Claim tokens, plan digests and unchanged output bytes/mtimes survive;
  publication, initialization and reset crash cuts recover across versions.

The file-lock implementation and twelve mutation/recovery/lock methods remain
unchanged from preservation checkpoint `f804fd1`. The reference validator now has
an explicit reader adapter; default behavioral regressions and cross-version
tests verify that path rather than claiming its AST remains byte-for-byte equal.
Protocol v1, registry namespace, public CMake calls, generator/runtime and normal
user commands remain unchanged. The optional module installs next to the existing
helpers and needs no extra Python package, service or native helper build.

## Remaining gate

This work establishes a conservative fresh-observation primitive under reference
authority and disproves one proposed reuse mechanism. It does **not** establish
operation-wide observation validity. Promotion still requires an independently
reviewable dependency-lifetime/commit argument, adversarial tests for that exact
mechanism and repeated full-validation measurements below 30 seconds with margin.
A timestamp, two matching sweeps, read-sharing restrictions or a watcher cannot
substitute for that argument. Retaining correctness and easy upgrades takes
precedence over enabling the index.
