# Protocyte Smoke Tests

This project is a repository-internal integration and runtime fixture. User
onboarding lives in the [Getting Started
guide](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started); do not
copy the smoke project as a minimal consumer.

## Contributor prerequisites

- Windows with a Visual Studio Developer PowerShell or an equivalent MSVC
  developer environment.
- CMake 3.24 or newer and a C++20 compiler.
- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
- The repository's locked development environment.

The presets use `VCINSTALLDIR`, `VSINSTALLDIR`, and `WindowsSdkVerBinPath`
instead of hard-coding a Visual Studio edition or Windows SDK version.

## Hosted smoke preset

Run from the repository root:

```powershell
Push-Location tests/smoke
cmake --preset windows-clangcl-ninja
cmake --build --preset windows-clangcl-ninja
ctest --preset windows-clangcl-ninja
Pop-Location
```

## Regenerate checked outputs

Never edit files under `tests/smoke/generated/` manually. Regenerate the entire
checked tree from generator and runtime sources:

```powershell
uv sync --locked --group dev
uv run python .github/scripts/install_protoc.py --dest build/canonical-protoc
$env:PROTOCYTE_SMOKE_PROTOC = (Resolve-Path build/canonical-protoc/bin/protoc.exe)
$env:PROTOCYTE_SMOKE_PROTOBUF_IMPORT_DIR = (Resolve-Path build/canonical-protoc/include)
$env:PROTOCYTE_SMOKE_PLUGIN = (Resolve-Path .venv/Scripts/protoc-gen-protocyte.exe)
$env:PROTOCYTE_SMOKE_CLANG_FORMAT = (Resolve-Path .venv/Scripts/clang-format.exe)
uv run python tests/smoke/tools/generate_checked_outputs.py
```

The regeneration helper uses official `protoc`, the installed Protocyte plugin,
and the locked `clang-format`. It verifies the pinned protobuf archive and tool
versions, generates into a staging tree, and replaces the checked output tree
only after every output succeeds.

Review the complete generated diff and run the hosted smoke preset after
regeneration.

## Optional WDK driver preset

```powershell
Push-Location tests/smoke
cmake --preset windows-clangcl-ninja-driver
cmake --build --preset windows-clangcl-ninja-driver
Pop-Location
```

The driver preset requires the matching WDK environment. It validates the
freestanding runtime surface without running a driver.

## Fixture map

- [`CMakeLists.txt`](CMakeLists.txt) owns repository regeneration wiring.
- [`proto/example.proto`](proto/example.proto) exercises Protocyte options.
- [`src/host_smoke.cpp`](src/host_smoke.cpp) exercises generated hosted code.

For consumer-facing integration contracts, use the [CMake API
Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference).
