# Code Generation

Protocyte is a `protoc` plugin. It accepts protobuf source descriptors and emits C++20 headers and translation units.

For most C++ projects, let the [CMake integration](https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration) own generation. Invoke `protoc` directly when another build system owns the generated files, when inspecting plugin behavior, or when producing checked-in output intentionally.

## Choose a Workflow

| Workflow | Recommended use |
|---|---|
| `protocyte_add_proto_library()` | Generate and compile a reusable CMake target |
| `protocyte_add_descriptor_set_library()` | Generate a CMake target from a descriptor set |
| `protocyte_generate()` | Integrate generation into custom CMake target logic |
| Direct `protoc` | Non-CMake builds, inspection, or intentionally checked-in output |

## Install the Plugin from a Source Checkout

Protocyte requires Python 3.12 or newer.

From a Protocyte checkout:

### PowerShell

```powershell
uv sync
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
```

### Linux, macOS, or Another POSIX Host

```bash
uv sync
export PATH="$PWD/.venv/bin:$PATH"
```

Verify the command:

```console
protoc-gen-protocyte --version
protoc-gen-protocyte --help
```

CMake consumers normally do not need this step. The CMake package provisions an isolated plugin environment automatically unless `PROTOCYTE_PLUGIN_EXECUTABLE` is supplied.

## Locate `protocyte/options.proto`

Schemas using Protocyte extensions must make `protocyte/options.proto` visible to `protoc`.

From a source checkout, its import root is:

```text
src/protocyte/proto
```

From an installed Python package, locate it with:

```console
python -c "from pathlib import Path; import protocyte; print((Path(protocyte.__file__).resolve().parent / 'proto').as_posix())"
```

An installed CMake package exposes:

```cmake
PROTOCYTE_PROTO_DIR
PROTOCYTE_OPTIONS_PROTO
```

A schema that does not import Protocyte extensions does not need this additional import root.

## Generate from Proto Sources

Assume this layout:

```text
project/
|-- proto/
|   `-- reading.proto
`-- generated/
```

The output directory must exist before `protoc` runs.

### PowerShell

```powershell
New-Item -ItemType Directory -Force generated | Out-Null

protoc `
  --proto_path=proto `
  --protocyte_out=runtime=emit:generated `
  proto/reading.proto
```

### Linux, macOS, or Another POSIX Host

```bash
mkdir -p generated

protoc \
  --proto_path=proto \
  --protocyte_out=runtime=emit:generated \
  proto/reading.proto
```

When the schema imports `protocyte/options.proto`, add its import root:

```console
--proto_path=/path/to/protocyte/proto
```

`protoc` locates `protoc-gen-protocyte` on `PATH`. Select another executable explicitly when needed:

```console
--plugin=protoc-gen-protocyte=/path/to/protoc-gen-protocyte
```

## Generated Files

For a virtual descriptor named `reading.proto`, Protocyte emits:

```text
reading.protocyte.hpp
reading.protocyte.cpp
```

With `runtime=emit`, it also emits:

```text
protocyte/runtime/runtime.hpp
```

Compile the generated `.cpp` file and add the generation root to the target's include directories.

Use `runtime=omit` when the application supplies the runtime header through an installed or reusable CMake target. Direct invocations commonly use `runtime=emit` so the generated tree is self-contained.

## Keep Parameters Separate from the Output Directory

Simple parameters can be placed in the combined `--protocyte_out=<parameters>:<directory>` form:

```console
--protocyte_out=runtime=emit:generated
```

Use `--protocyte_opt` when parameter values contain colons or when several settings are easier to read separately:

### PowerShell

```powershell
protoc `
  --proto_path=proto `
  --protocyte_out=generated `
  --protocyte_opt=runtime=emit:vendor/protocyte,namespace_prefix=mycorp::wire,include_prefix=generated `
  proto/reading.proto
```

### Linux, macOS, or Another POSIX Host

```bash
protoc \
  --proto_path=proto \
  --protocyte_out=generated \
  --protocyte_opt=runtime=emit:vendor/protocyte,namespace_prefix=mycorp::wire,include_prefix=generated \
  proto/reading.proto
```

`protoc` treats the first colon in the combined output form as the parameter/output separator. Keeping colon-valued options in `--protocyte_opt` prevents a prefix from being mistaken for the output directory.

See [Plugin Parameters](https://github.com/anthonyprintup/protocyte/wiki/Plugin-Parameters) for all supported settings.

## Generate from a Descriptor Set

Use a descriptor set when `.proto` source files are not the generation authority:

### PowerShell

```powershell
New-Item -ItemType Directory -Force generated | Out-Null

protoc `
  --descriptor_set_in=descriptor_set.pb `
  --plugin=protoc-gen-protocyte=path\to\protoc-gen-protocyte.exe `
  --protocyte_out=runtime=emit:generated `
  core.proto messages.proto settings.proto
```

### Linux, macOS, or Another POSIX Host

```bash
mkdir -p generated

protoc \
  --descriptor_set_in=descriptor_set.pb \
  --plugin=protoc-gen-protocyte="$(command -v protoc-gen-protocyte)" \
  --protocyte_out=runtime=emit:generated \
  core.proto messages.proto settings.proto
```

The trailing names are virtual descriptors inside `descriptor_set.pb`, not host filesystem paths.

Imported descriptors remain available for type and custom-option resolution, but Protocyte emits code only for descriptors selected for generation and any required runtime message or enum types.

## Inspect a Descriptor Set

List the descriptors Protocyte can discover:

```console
protoc-gen-protocyte descriptor-set list descriptor_set.pb
```

The command uses the same generator environment as descriptor-set `DISCOVER` in CMake.

Unsupported descriptors may remain dependency-only when generated fields do not require their message or enum types. Discovery reports a targeted error when a selected type depends on a descriptor Protocyte cannot generate.

## Preserve Schema Comments

Generated C++ documentation requires protobuf source information.

When producing a descriptor set, pass:

```console
--include_source_info
```

Descriptor sets without source information remain valid, but Protocyte cannot reproduce their source comments as generated C++ documentation.

Source-mode `protoc` invocations receive source information directly.

## CMake-Owned Generation

The recommended target-oriented source flow is:

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    ALIAS application::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

CMake tracks:

- selected schemas;
- transitive imports;
- changes in discovered source membership;
- generator and runtime support files;
- the selected plugin and protobuf compiler;
- declared generated outputs.

Changing an existing schema or import regenerates affected files. With `DISCOVER`, adding or removing a `.proto` file also causes reconfiguration.

Use explicit `PROTOS` when the selected set should remain fixed.

See the [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference) for lower-level generation and output variables.

## Descriptor Names and Generated Paths

Protobuf descriptor names are portable virtual paths, not necessarily valid host paths.

Protocyte preserves ordinary segments and escapes nonportable UTF-8 bytes as `~HH`:

```text
api/bad"name.proto  -> api/bad~22name.protocyte.hpp
a:b.proto           -> a~3Ab.protocyte.hpp
```

A literal `~` is escaped as well, preventing aliases between original and escaped names. Semicolons become `~3B`, so generated paths remain safe inside CMake lists.

If a path component would exceed a common 255-byte filesystem limit, Protocyte retains a readable prefix and appends a SHA-256 digest. Visual Studio builds also compact complete paths when necessary to remain within legacy MSBuild source-item limits.

Protocyte rejects:

- descriptor names beginning with `-`, because `protoc` interprets them as options;
- distinct names whose generated paths differ only by letter case;
- carriage returns or line feeds in descriptor names or CMake tool/source/output paths;
- generated output collisions between separately selected descriptors.

The collision checks are portable even on a case-sensitive host.

## CMake Process Transport

CMake-launched generation and dependency scans use `protoc` UTF-8 response files.

Spaces, non-ASCII characters, quotes, semicolons, and portable colons remain literal arguments on Windows and POSIX. Newlines are rejected because the response-file format has no escaping for line breaks.

Direct non-CMake integrations are responsible for preserving the same argument boundaries.

## Reproducible Generation

For checked-in or release-generated output:

1. pin the Protocyte revision;
2. pin or record the protobuf compiler version;
3. use explicit plugin parameters;
4. keep formatter configuration under version control;
5. regenerate every output with the same command;
6. compile and test the generated sources;
7. review the generated diff.

Protocyte is pre-1.0. Regenerate all checked outputs when changing versions rather than relying on migration shims.

## Related Pages

- [Getting Started](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started)
- [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent)
- [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference)
- [Plugin Parameters](https://github.com/anthonyprintup/protocyte/wiki/Plugin-Parameters)
- [Protocyte Extensions](https://github.com/anthonyprintup/protocyte/wiki/Protocyte-Extensions)
