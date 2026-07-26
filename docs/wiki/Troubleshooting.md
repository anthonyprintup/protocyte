# Troubleshooting

Start with the first failing configure, generation, compile, or runtime operation. Protocyte diagnostics are designed to name the rejected input and the controlling setting.

## CMake Cannot Find Python 3.12

Select an interpreter explicitly:

```console
cmake -S . -B build -DPython3_EXECUTABLE=/path/to/python3.12
```

Verify required standard-library modules:

```console
python3.12 -c "import ensurepip, venv"
```

On Debian or Ubuntu, install `python3-venv` or the matching version-specific package.

An interpreter without `venv` or `ensurepip` cannot provision Protocyte's managed environment.

## Managed Python Provisioning Fails

Check:

- the selected interpreter can create virtual environments;
- the first configure has package-index access;
- `PROTOCYTE_PYTHON_ENV_ROOT` is writable;
- the path contains no semicolon;
- endpoint security is not blocking the environment's executables.

Set another environment root:

```console
cmake -S . -B build \
  -DPROTOCYTE_PYTHON_ENV_ROOT=/short/writable/path
```

Delete only the affected managed environment after all related CMake processes stop. Protocyte will recreate it from the current fingerprint.

## Use a Preinstalled Plugin

Bypass managed provisioning:

```console
cmake -S . -B build \
  -DPROTOCYTE_PLUGIN_EXECUTABLE=/path/to/protoc-gen-protocyte
```

Verify:

```console
protoc-gen-protocyte --version
protoc-gen-protocyte descriptor-set list descriptor_set.pb
```

The executable must match the CMake package version and its path must not contain a semicolon. Provide a wrapper from a semicolon-free path when necessary.

## No Usable `protoc`

For native FetchContent builds, the protobuf fallback is enabled by default. Installed packages default it to off.

Allow fallback explicitly:

```console
cmake -S . -B build -DPROTOCYTE_FETCH_PROTOBUF=ON
```

Or provide a compiler:

```console
cmake -S . -B build \
  -DProtobuf_PROTOC_EXECUTABLE=/path/to/protoc
```

The compiler must pass a configure-time `--version` probe.

## `descriptor.proto` Cannot Be Found

Provide the import root containing `google/protobuf/descriptor.proto`:

```console
cmake -S . -B build \
  -DPROTOCYTE_PROTOBUF_IMPORT_DIR=/path/to/protobuf/src
```

Do not point the variable directly at `google/protobuf`; point it at the root above `google`.

## Cross Build Selects a Target `protoc`

Set a concrete host-runnable compiler:

```console
cmake -S . -B build \
  -DCMAKE_TOOLCHAIN_FILE=/path/to/toolchain.cmake \
  -DProtobuf_PROTOC_EXECUTABLE=/path/to/host/protoc
```

Protocyte does not build a host tool with the target toolchain and does not forward `CROSSCOMPILING_EMULATOR`.

If a launcher is required, point the variable at a host-runnable wrapper.

## Configure Without Network Access

Provide all inputs:

```console
cmake -S . -B build \
  -DFETCHCONTENT_SOURCE_DIR_PROTOCYTE=/path/to/protocyte \
  -DPROTOCYTE_FETCH_PROTOBUF=OFF \
  -DPROTOCYTE_PLUGIN_EXECUTABLE=/path/to/protoc-gen-protocyte \
  -DProtobuf_PROTOC_EXECUTABLE=/path/to/protoc \
  -DPROTOCYTE_PROTOBUF_IMPORT_DIR=/path/to/protobuf/src
```

The plugin environment must already contain compatible dependencies.

## Tool Operation Times Out

Increase the CMake process limit:

```console
cmake -S . -B build -DPROTOCYTE_TOOL_TIMEOUT_SECONDS=900
```

The default is 300 seconds. Use zero only when another supervisor enforces a timeout.

For direct plugin formatting, `formatter_timeout_seconds` controls each `clang-format` invocation separately.

## Generated Output Path Is Too Long

Choose shorter build and output roots, especially with Visual Studio/MSBuild:

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    OUT_DIR "${CMAKE_BINARY_DIR}/gen"
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
)
```

Protocyte compacts descriptor output names when possible, but the absolute `OUT_DIR` must leave enough room for a collision-resistant generated name.

## Descriptor Name Is Rejected

Protocyte rejects names that:

- begin with `-`;
- contain carriage returns or line feeds;
- alias another generated path by portable case folding;
- collide after output normalization.

Nonportable bytes in otherwise valid names are escaped as `~HH`. See [Code Generation](https://github.com/anthonyprintup/protocyte/wiki/Code-Generation).

## `OUT_DIR` Belongs to Another Build Tree

Generated output trees have persistent ownership records. Deleting a build directory does not silently transfer its output tree.

To transfer ownership:

1. stop every build that can use the output;
2. preserve any generated files that were edited;
3. read the configure or build diagnostic;
4. remove only the exact owner records named by that diagnostic;
5. reconfigure the new build tree.

Do not delete the entire output-lock namespace or cache. `.lock` files carry no ownership state and may remain.

See [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference) for the complete ownership contract.

## Failed Generation Left Staging Data

Protocyte generates into private staging and validates outputs before publication. A compiler failure, timeout, or invalid result publishes no new ownership claim.

If cleanup refuses an unsafe path or cannot remove it, the diagnostic warns that inert staging data outside `OUT_DIR` may remain. Stop related processes and remove only the named staging path after inspecting it.

## Adding a Proto File Does Not Generate It

With explicit `PROTOS`, add the new path to the CMake call.

With `DISCOVER`, rerun CMake if the generator does not automatically reconfigure:

```console
cmake -S . -B build
```

The file must be beneath `PROTO_ROOT`.

## Descriptor-Set `DISCOVER` Fails During Configure

`DISCOVER` must inspect the descriptor set during configuration, so the file must already exist.

For a build-generated descriptor set, use explicit `FILES` or `PROTOS` and add its producing file or target through `DEPENDS`.

## Generated Headers Compile with Different Public Types

Feature definitions such as reflection and standard string views change public declarations. Apply them with `PUBLIC` visibility to the generated library:

```cmake
target_compile_definitions(
    application_proto
    PUBLIC
        PROTOCYTE_ENABLE_REFLECTION=1
        PROTOCYTE_ENABLE_STD_STRING_VIEW=1
)
```

Do not define them privately on only the executable or generated source.

## Link Errors for Reflection in a Windows DLL

Use the target-oriented CMake helper with `TYPE SHARED`. It assigns a target-unique import/export macro to reflection data.

Direct generator users must provide their own DLL visibility decoration.

## A Runtime Operation Failed

Inspect:

```cpp
error.code
error.offset
error.field_number
```

`offset` is absolute within the top-level I/O coordinate. `field_number` identifies the public containing field.

Check resource limits before treating `size_limit`, `count_limit`, or `no_memory` as wire corruption.

## LLDB Shows Raw Runtime Internals

Import Protocyte's Python formatter and confirm the LLDB build supports scripting:

```text
(lldb) script print("LLDB Python scripting is available")
(lldb) command script import "/path/to/protocyte_lldb.py"
```

See [Debugging](https://github.com/anthonyprintup/protocyte/wiki/Debugging).

## An Expected Release Asset Is Missing

Protocyte has not published its first release. Check the [releases page](https://github.com/anthonyprintup/protocyte/releases).

Until a release exists, pin a reviewed source commit or install a source checkout. Do not substitute a fictional release tag.

## Ask for Help

When opening an [issue](https://github.com/anthonyprintup/protocyte/issues), include:

- operating system and architecture;
- compiler and CMake versions;
- Python and `protoc` versions;
- Protocyte revision;
- integration mode;
- the complete redacted diagnostic;
- a minimal schema and CMake reproduction when possible.
