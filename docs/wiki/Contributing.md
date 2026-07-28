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

## Documentation

The canonical wiki source is `docs/wiki/` in the main repository. Edit and
review those Markdown files in a normal pull request. The GitHub Wiki is a
published mirror and should not be treated as an independent source. A
path-filtered workflow automatically mirrors Wiki changes after they are merged
to `main`; serialized publication ensures the mirror eventually reflects the
newest merged documentation when several changes land close together.

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
