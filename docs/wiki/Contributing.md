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
separately. It also counts registry scans, recorded-plan loads, and path
projections. It does not generate C++, use the shared registry, or access the
network. The printed temporary directory retains the synthetic state and
`results.json`; use `--work NEW_DIRECTORY` to choose that directory explicitly.

Use `--baseline-source /path/to/baseline-checkout` for an alternating comparison
against another revision at the same workspace depth. The report includes every
sample and median times. Compare operation counts as well as wall times: Windows
filesystem probes, path depth, caching, and concurrent machine activity affect
timings. The focused regression tests are in `tests/test_output_coordinator.py`.

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
