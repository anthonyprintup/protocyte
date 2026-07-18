# Protocyte LLDB Formatters

This document describes LLDB visualizers for the generated Protocyte runtime:

- `protocyte::String<Config>`: shows `size=<N>, value="<text>", hex=[<bytes>]`.
- `protocyte::Bytes<Config>`: shows `size=<N>, hex=[<bytes>], ascii="<preview>"` and expandable byte children.
- `protocyte::Vector<T, Config>`: shows size/capacity and expandable indexed elements.
- `HashMap<K, V, Config>`: shows `key => value` entries when expanded.
- Generated message oneofs: optional tagged-union view for generated message types.
- `Status`, `Error`, `Result<T>`, `Result<T&>`, `Optional<T>`, `Optional<T&>`, `Box<T, Config>`, and the slice reader/writer types get compact summaries.

## Plain LLDB

### Installed package

When Protocyte is installed in a Python environment, locate the packaged
formatter with that environment's Python interpreter:

```shell
python -c "from pathlib import Path; import protocyte.debugger as d; print(Path(d.__file__).with_name('protocyte_lldb.py').resolve().as_posix())"
```

If the package is managed by `uv`, use `uv run python` in place of `python`.
Copy the printed absolute path into LLDB:

```text
(lldb) command script import "C:/path/to/site-packages/protocyte/debugger/protocyte_lldb.py"
```

To load the formatters in future LLDB sessions, add the same `command script
import` line, without the `(lldb)` prompt, to your user-level `.lldbinit`. Run
the locator command again if you recreate or move the Python environment.

### Source checkout

This repository includes a project-local [`.lldbinit`](../.lldbinit) at the repo root. From the repository root, load that file:

```text
(lldb) command source .lldbinit
```

That init file imports [src/protocyte/debugger/protocyte_lldb.py](../src/protocyte/debugger/protocyte_lldb.py). If you prefer, import the formatter module directly:

```text
(lldb) command script import src/protocyte/debugger/protocyte_lldb.py
```

Then inspect values normally:

```text
(lldb) frame variable msg
(lldb) frame variable msg.name_
(lldb) frame variable bytes
(lldb) frame variable bytes[0] bytes[1]
```

The previews inline at most 64 bytes to keep variable views responsive. Expanding
a formatted value also exposes a **Raw View** child. Expand it to inspect the
underlying members such as `ctx_`, `data_`, `size_`, and `capacity_`.

Generated oneofs are stored as a case tag plus payload fields, so the oneof formatter is opt-in per generated type regex. Register it after importing the formatter:

```text
(lldb) protocyte-oneof '^test::ultimate::.*<.*>$'
```

After that, generated messages in the matching namespace get a summary such as `special_oneof=oneof_string`, and expansion includes a synthetic child named like `special_oneof: oneof_string` that points at the active payload.

## CLion

CLion can use project-local `.lldbinit` files, but execution is disabled by default for security. Enable it once in your user-level LLDB init file, then CLion will load the applicable project-local `.lldbinit`.

Add this to your user-level `.lldbinit`:

```text
settings set target.load-cwd-lldbinit true
```

On Windows with the MSVC toolchain, CLion uses JetBrains' LLDB-based debugger for MSVC. Use a CMake profile that debugs with LLDB, start a debug session, and the variables view should pick up these formatters through the project `.lldbinit`.

The smoke CMake project lives under `tests/smoke`, so this repository also tracks [tests/smoke/.lldbinit](../tests/smoke/.lldbinit). That file imports the same formatter module with a path relative to the smoke project root and registers the generated-message oneof formatter used by `protocyte_host_smoke`.

If CLion starts the debugger from a different working directory, add the same
import command under **Settings | Build, Execution, Deployment | Debugger |
LLDB Startup Commands**. Use the installed formatter path reported by the
locator command above, or the absolute path to
`src/protocyte/debugger/protocyte_lldb.py` when working from a source checkout.

To enable the oneof tagged-union view in CLion, add a second startup command with the generated namespace or message regex you want, for example:

```text
protocyte-oneof '^test::ultimate::.*<.*>$'
```
