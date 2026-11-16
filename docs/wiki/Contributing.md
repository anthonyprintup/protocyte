# Contributing

Contributions are welcome through
[GitHub issues](https://github.com/anthonyprintup/protocyte/issues) and pull
requests.

## Prepare a checkout

Install the tracked privacy hooks once:

```bash
git config --local core.hooksPath .githooks
```

The hooks scan staged paths and content, local Git objects, pending commit
metadata, and finalized objects before push. Failures are deliberately
redacted. CI repeats the object scan from a full-history checkout.

Run the guard directly with:

```bash
python .github/scripts/check_private_paths.py
```

Hooks are a local safeguard, not an access-control boundary. They can be
bypassed, and unreachable local objects are not transferred for CI to inspect.

## Test

Install the locked environment and run the default suite:

```bash
uv sync --locked
uv run pytest -q
```

The CMake integration matrix creates and builds temporary projects and is
excluded from the default run:

```bash
uv run pytest -q -m cmake_integration
```

For generator or runtime changes, regenerate the checked smoke outputs rather
than editing files under `tests/smoke/generated/`:

```bash
uv run python tests/smoke/tools/generate_checked_outputs.py
```

Then follow [the smoke contributor
instructions](https://github.com/anthonyprintup/protocyte/blob/main/tests/smoke/README.md)
for the focused build matrix.

Format every touched C++ source or header with `clang-format`.

### Output registry performance

Run the offline scaling benchmark with Python 3.12 or newer:

```bash
python tests/benchmark_output_registry.py --claims 0 8 16 --plans 1 4 --repeat 3
```

It creates each retained claim through the real coordinator in a fresh private
registry and reports seed, registry validation, and reconciliation wall/CPU times
separately. Setup includes plan creation and uses real initialization/reconciliation
helpers under private registry/generation/publication locks; it avoids an
all-pairs setup scan. The measured `reconcile_set` performs every production
check unchanged. It counts registry scans, recorded-plan loads, path projections,
and profiled filesystem calls. It does not generate C++, use the shared registry, or access the
network. The printed temporary directory retains the synthetic state and
`results.json`; use `--work NEW_DIRECTORY` to choose that directory explicitly.

Use `--baseline-source /path/to/baseline-checkout` for an alternating comparison
against another revision at the same workspace depth. The report includes every
sample and median times. Compare operation counts as well as wall times: Windows
filesystem probes, path depth, caching, and concurrent machine activity affect
timings. The focused regression tests are in `tests/test_output_coordinator.py`.

Filesystem counters include native existence queries on newer Windows Python.
Attribute probes from experimental compared sources are counted separately:
substituting a cheaper query must not be reported as eliminating an observation.

For a larger sample, explicitly opt in (up to 4,096 claims and 32 plans):

```bash
python tests/benchmark_output_registry.py --large --claims 2048 --plans 11 --repeat 1
```

Start with 64 claims to estimate cost; large setup and validation may take
minutes. The original issue #54 measurement is also available as
`tests/registry_validation_poc.py`. Publish only scripts and sanitized results;
synthetic fixture records contain local paths and must remain private. CMake
pytest fixtures use a per-test cache base even when exercising the default
registry selector. Retained claims are released only by an ownership-aware
reset, never by age, missing build trees or test-looking names.

The experimental ownership index supports a `shadow` benchmark mode. It runs
both the sampled preview and the mandatory fresh reference validator; full
validation timings include both. Baseline checkouts use reference mode:

```bash
python tests/benchmark_output_registry.py --registry-validation shadow --claims 0 8 16 --plans 1 11 --repeat 1
python tests/registry_validation_poc.py --registry-validation shadow --claims 0 8 16 --plans 1 11
```

The scaling benchmark also accepts `--targets-per-plan 3 --shared-build-root
--existing-directories` to exercise anonymous alternate layouts. Both sides of a
baseline comparison use the same layout. The defaults preserve the original
one-target, separate-build, absent-directory fixture.

A separate **read-only, non-authoritative** experiment measures only the sampled
algorithm. It performs no fresh registry reference pass after seeding and grants
no authority to reconcile or publish; its timing is not a reconciler speedup:

```bash
python tests/benchmark_ownership_preview.py --large --claims 2172 --plans 11 --work .pytest-tmp/index-preview-new
```

The work directory must be new. The preview supports the same layout flags.
Both tools record the coordinator/helper fingerprints and reject source changes
during a measurement. See the experiment's
[results](../experimental-index-results.md) and
[correctness contract](../experimental-index-contract.md) before interpreting
the preview numbers. That sampled experiment always retains reference authority.
The subsequent committed index is now the automatic Windows default when native
capabilities and its complete certificate are verified; see the
[parallel qualification](../parallel-probe-results.md) and
[observation contract](../observation-commit-contract.md). Unsupported or
unverified observations fall back to reference validation. Set
`PROTOCYTE_REGISTRY_VALIDATION=reference` to compare an existing build using the
reference path.

The fresh native-reader investigation can be measured with
`--registry-validation native-shadow` in the scaling benchmark or POC. It keeps
the cross product and fresh physical checks, then always runs reference validation.
Native open/query/close counters and all three source fingerprints are reported.
This mode is an experiment and has not passed the large-workload timing gate;
see [its results and counterexample](../observation-mechanism-results.md).

## Documentation

The canonical wiki source is `docs/wiki/` in the main repository. Edit and
review those Markdown files in a normal pull request. The GitHub Wiki is a
published mirror and should not be treated as an independent source. A
path-filtered workflow automatically mirrors Wiki changes after they are merged
to `main`; serialized publication ensures the mirror eventually reflects the
newest merged documentation when several changes land close together. The
workflow authenticates to the separate Wiki repository through the
`PROTOCYTE_WIKI_TOKEN` Actions secret. Configure that secret with a dedicated
fine-grained personal access token restricted to this repository with
read/write Contents permission; do not reuse a developer's broad CLI token.

The local sync helper remains available to preview, verify, or repair an
existing Wiki checkout. It never commits or pushes.

```bash
python .github/scripts/sync_wiki.py /path/to/protocyte.wiki
python .github/scripts/sync_wiki.py /path/to/protocyte.wiki --apply
python .github/scripts/sync_wiki.py /path/to/protocyte.wiki --check
```

The default invocation is a dry run. `--apply` mirrors additions, updates, and
stale Markdown removals. Inspect the wiki checkout's exact Git diff before
creating its single documentation commit.

## Pull requests

Keep changes focused, include tests for behavioral contracts, and explain
generated-output changes. Report security-sensitive issues privately to the
maintainers rather than opening a public exploit report.
