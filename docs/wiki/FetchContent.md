# FetchContent

CMake `FetchContent` is the recommended way to use Protocyte in a C++ project. It makes Protocyte's generation functions and runtime targets available in the same configure and build graph as the consumer.

## Minimal Setup

```cmake
include(FetchContent)

FetchContent_Declare(
    protocyte
    GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
    GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14
)
FetchContent_MakeAvailable(protocyte)

protocyte_add_proto_library(
    TARGET application_proto
    ALIAS application::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(application main.cpp)
target_link_libraries(application PRIVATE application::proto)
```

The full commit SHA is intentional. Protocyte has not published its first release, so consumers should pin a reviewed immutable commit instead of tracking `main`. Prefer an immutable release tag after releases exist.

## Source Selection

`PROTO_ROOT` identifies the root used for protobuf virtual paths and imports. Choose either `DISCOVER` or `PROTOS`.

### Discover a Proto Tree

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

`DISCOVER` recursively selects `.proto` files beneath `PROTO_ROOT`. CMake reconfigures when files are added or removed.

### List Sources Explicitly

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    PROTOS
        proto/messages.proto
        proto/settings.proto
    HOSTED_ALLOCATOR
)
```

Explicit source paths are resolved from `CMAKE_CURRENT_SOURCE_DIR`, must exist during configuration, and must be inside `PROTO_ROOT`.

Both forms track transitive protobuf imports. Editing an imported schema regenerates affected outputs without repeating the import graph through `DEPENDS`.

## Descriptor Sets

Use `protocyte_add_descriptor_set_library()` when a descriptor set, rather than a source tree, is authoritative:

```cmake
protocyte_add_descriptor_set_library(
    TARGET recovered_proto
    ALIAS recovered::proto
    DESCRIPTOR_SET "${CMAKE_CURRENT_BINARY_DIR}/descriptor_set.pb"
    FILES
        core.proto
        messages.proto
        settings.proto
    HOSTED_ALLOCATOR
)

target_link_libraries(application PRIVATE recovered::proto)
```

`FILES` entries are virtual descriptor names inside the set, not filesystem paths.

Use `DISCOVER` to select every supported non-runtime descriptor:

```cmake
protocyte_add_descriptor_set_library(
    TARGET recovered_proto
    DESCRIPTOR_SET "${CMAKE_CURRENT_BINARY_DIR}/descriptor_set.pb"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

Descriptor-set `DISCOVER` requires the set to exist during configuration. Explicit `FILES` can consume a build-generated descriptor set when `DEPENDS` names its producing file or target and the descriptor-set path is concrete and configuration-independent.

## Generated Library Behavior

`protocyte_add_proto_library()`:

- creates the code-generation target;
- compiles generated `.cpp` files as C++20;
- exposes the generated include directory;
- links the selected Protocyte runtime;
- adds the generation dependency to the library;
- optionally creates a namespaced alias.

The library type defaults to `STATIC`. Set `TYPE` to `SHARED`, `MODULE`, or `OBJECT` when required.

The default output directory is:

```text
${CMAKE_CURRENT_BINARY_DIR}/<TARGET>_protocyte
```

Set `OUT_DIR` to choose another build-tree location:

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
)
```

Generated output trees are owned by one canonical CMake build tree. Do not point unrelated build directories at the same `OUT_DIR`.

## Runtime Selection

Without another runtime option, generated libraries link `protocyte::runtime`.

For a normal hosted application:

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

`HOSTED_ALLOCATOR` selects `protocyte::runtime_hosted`.

Use `RUNTIME_TARGET` when the application supplies another compatible runtime target. Use `EMIT_RUNTIME` only when the runtime header must be emitted into the generated output tree instead of reusing a shared target.

See [Embedded and Freestanding](https://github.com/anthonyprintup/protocyte/wiki/Embedded-and-Freestanding) and the [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference) before changing runtime ownership.

## Managed Python Environment

Protocyte requires Python 3.12 or newer for code generation.

By default, the first generation setup:

1. selects a Python interpreter;
2. creates a fingerprinted virtual environment under the build tree;
3. installs Protocyte and its locked Python dependencies there;
4. reuses that environment while its interpreter, Protocyte sources, and package metadata remain unchanged.

This process does not install packages globally or modify the selected base interpreter.

The interpreter must provide `venv` and `ensurepip`. On Debian or Ubuntu, install `python3-venv` or the matching version-specific package when those modules are missing.

Select a Python interpreter during configuration:

```console
cmake -S . -B build -DPython3_EXECUTABLE=/path/to/python3.12
```

Choose another build-local environment root before making Protocyte available:

```cmake
set(
    PROTOCYTE_PYTHON_ENV_ROOT
    "${CMAKE_BINARY_DIR}/tools/protocyte-python"
)
FetchContent_MakeAvailable(protocyte)
```

Relative environment roots resolve against `CMAKE_BINARY_DIR`. The path must not contain a semicolon.

### Use an Application-Owned Plugin

Set `PROTOCYTE_PLUGIN_EXECUTABLE` to bypass managed plugin provisioning:

```cmake
set(
    PROTOCYTE_PLUGIN_EXECUTABLE
    "/path/to/protoc-gen-protocyte"
)
FetchContent_MakeAvailable(protocyte)
```

The executable must be compatible with the fetched CMake package and support:

```console
protoc-gen-protocyte --version
protoc-gen-protocyte descriptor-set list descriptor_set.pb
```

The path must not contain a semicolon. If the real executable is beneath such a path, provide a wrapper from a semicolon-free location.

## Protobuf Compiler and Imports

Protocyte needs a host-runnable `protoc` and an import tree containing `google/protobuf/descriptor.proto`.

An explicit `Protobuf_PROTOC_EXECUTABLE` takes precedence:

```cmake
set(
    Protobuf_PROTOC_EXECUTABLE
    "/path/to/host/protoc"
    CACHE FILEPATH
    "Host protobuf compiler"
)
```

For native builds, Protocyte then prefers:

1. a package-provided `protobuf::protoc` target;
2. a host `protoc` on `PATH`;
3. the pinned protobuf FetchContent fallback.

If a compiler exists but its import tree is unavailable, the fallback can fetch only the protobuf import sources.

The fallback is controlled by:

```cmake
set(PROTOCYTE_FETCH_PROTOBUF ON)
```

For source consumption, `PROTOCYTE_FETCH_PROTOBUF` defaults to `ON`. Set it to
`OFF` before making Protocyte available to prohibit fallback downloads:

```cmake
set(PROTOCYTE_FETCH_PROTOBUF OFF)
FetchContent_MakeAvailable(protocyte)
```

When the fallback owns the native protobuf build, its install rules and dependency targets do not leak into the parent project's install tree.

Set an explicit caller-owned import root when necessary:

```cmake
set(
    PROTOCYTE_PROTOBUF_IMPORT_DIR
    "/path/to/protobuf/src"
)
```

The directory must contain `google/protobuf/descriptor.proto`.

## Cross Compilation

Cross builds must use a concrete compiler that runs directly on the host.

Selection order is:

1. explicit `Protobuf_PROTOC_EXECUTABLE`;
2. a host `protoc` found on the configure process's `PATH`;
3. a package-provided imported compiler whose mapped executable runs on the host.

Protocyte does not:

- build a host compiler with the target toolchain;
- capture an unrelated unnamespaced target named `protoc`;
- forward `CROSSCOMPILING_EMULATOR` through dependency scanning or generation.

When emulation or another launcher is required, point `Protobuf_PROTOC_EXECUTABLE` at a host-runnable wrapper.

## Fully Controlled or Offline Configuration

Provide every source and tool explicitly when configuration must not download anything:

```bash
cmake -S . -B build \
  -DFETCHCONTENT_SOURCE_DIR_PROTOCYTE=/path/to/protocyte \
  -DPROTOCYTE_FETCH_PROTOBUF=OFF \
  -DPROTOCYTE_PLUGIN_EXECUTABLE=/path/to/protoc-gen-protocyte \
  -DProtobuf_PROTOC_EXECUTABLE=/path/to/protoc \
  -DPROTOCYTE_PROTOBUF_IMPORT_DIR=/path/to/protobuf/src
```

The equivalent `-D` arguments can be passed individually from PowerShell.

`FETCHCONTENT_SOURCE_DIR_PROTOCYTE` substitutes an existing source checkout for the declared Git repository. The other overrides bypass managed plugin installation and protobuf fallback downloads.

## Generator Options

Forward non-runtime plugin parameters through `OPTIONS`. Every entry must use `key=value`:

```cmake
protocyte_add_proto_library(
    TARGET application_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    OPTIONS
        "clang_format=/path/to/clang-format"
        "clang_format_config=${CMAKE_SOURCE_DIR}/.clang-format"
)
```

Bare option names are rejected.

Do not pass `runtime`, `runtime_prefix`, `include_prefix`, or duplicate namespace settings through `OPTIONS`; use the dedicated CMake arguments so generated outputs and includes remain visible to the build graph.

See [Plugin Parameters](https://github.com/anthonyprintup/protocyte/wiki/Plugin-Parameters) for supported values.

## Tool Timeouts

Every CMake-launched compiler, dependency reader, and import scan has a wall-clock limit.

`PROTOCYTE_TOOL_TIMEOUT_SECONDS` defaults to `300`:

```console
cmake -S . -B build -DPROTOCYTE_TOOL_TIMEOUT_SECONDS=900
```

The value is a non-negative number of seconds. Use `0` only when another supervisor enforces the build timeout.

A timeout stops generation before partial outputs are published. The diagnostic names the operation and the setting to change.

## Installation Behavior

When Protocyte is consumed through `FetchContent` or `add_subdirectory`, `PROTOCYTE_INSTALL` defaults to `OFF`. Its CMake package, runtime headers, and Python project are omitted from the parent install tree.

A parent that intentionally packages Protocyte can opt in before making it available:

```cmake
set(PROTOCYTE_INSTALL ON)
FetchContent_MakeAvailable(protocyte)
```

Installing a generated library is a separate choice. Pass `INSTALL_INCLUDE_DIR` to `protocyte_add_proto_library()` and install its `protocyte_generated_headers` file set with the target.

See [Installed Package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package) for complete install/export examples.

## Test Against a Local Checkout

Keep the production declaration immutable and override only the source during local development or CI:

```console
cmake -S . -B build \
  -DFETCHCONTENT_SOURCE_DIR_PROTOCYTE=/path/to/protocyte-checkout
```

This tests the current checkout without editing the consumer's pinned `FetchContent_Declare()` block.

## Related Pages

- [Getting Started](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started)
- [ExternalProject Superbuild](https://github.com/anthonyprintup/protocyte/wiki/ExternalProject-Superbuild)
- [Installed Package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package)
- [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference)
- [Troubleshooting](https://github.com/anthonyprintup/protocyte/wiki/Troubleshooting)
