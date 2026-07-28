# CMake Integration

Protocyte provides target-oriented CMake functions for generating and compiling protobuf code. Most projects should consume Protocyte with `FetchContent`; isolated superbuilds and preinstalled packages are supported when dependency boundaries matter more than the shortest setup.

## Choose an Integration

| Integration | Choose it when | Protocyte availability |
|---|---|---|
| [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent) | Protocyte can participate directly in the application's configure and build graph | Source is fetched during configuration |
| [ExternalProject Superbuild](https://github.com/anthonyprintup/protocyte/wiki/ExternalProject-Superbuild) | Protocyte and the application need isolated configure/build trees | A superbuild installs Protocyte first, then configures the consumer |
| [Installed Package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package) | A toolchain, SDK, package manager, or release asset already provides a Protocyte prefix | The consumer uses `find_package(protocyte CONFIG REQUIRED)` |

Use [Code Generation](https://github.com/anthonyprintup/protocyte/wiki/Code-Generation) instead when CMake should not own generation or when you need to invoke `protoc` directly.

## Recommended Default: FetchContent

`FetchContent` is the shortest supported route for a normal C++ project:

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

target_link_libraries(application PRIVATE application::proto)
```

Source consumption keeps code generation in the application's build graph. Protocyte tracks selected schemas, transitive imports, tool inputs, and generated outputs.

When Protocyte is a dependency rather than the top-level project, `PROTOCYTE_INSTALL` defaults to `OFF`. Protocyte, protobuf fallback targets, and their install rules therefore stay out of the parent project's install tree unless the parent explicitly opts in.

See [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent) for tool overrides, protobuf fallback behavior, descriptor sets, installation, and offline builds.

## Isolated Builds: ExternalProject

CMake `ExternalProject` runs its configure and build steps after the superbuild has configured. An external Protocyte install therefore cannot satisfy `find_package(protocyte)` in the same parent configure.

Use two build stages instead:

1. an external project configures and installs Protocyte into a private prefix;
2. a dependent external project configures the application with that prefix in `CMAKE_PREFIX_PATH`.

```text
superbuild
|-- protocyte_external
|   `-- installs a private CMake prefix
`-- application_external
    |-- depends on protocyte_external
    `-- uses find_package(protocyte CONFIG REQUIRED)
```

This pattern costs an additional configure boundary but keeps Protocyte's build, cache, and dependency state isolated from the application.

See [ExternalProject Superbuild](https://github.com/anthonyprintup/protocyte/wiki/ExternalProject-Superbuild) for the complete tested layout.

## Preinstalled Prefixes

When Protocyte has already been installed, make its prefix visible to CMake and load the package:

```cmake
find_package(protocyte CONFIG REQUIRED)

protocyte_add_proto_library(
    TARGET application_proto
    ALIAS application::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

Configure with the prefix:

```console
cmake -S . -B build -DCMAKE_PREFIX_PATH=/path/to/protocyte-prefix
```

The package exports the same generation functions used by source consumers, together with the reusable runtime and code-generation targets.

See [Installed Package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package) for source installs, future release assets, relocation, exact version requests, and managed Python requirements.

## Public CMake Functions

All supported CMake consumption modes expose:

- `protocyte_setup_codegen()` to prepare the generator and protobuf compiler eagerly;
- `protocyte_generate()` as the lower-level generation primitive;
- `protocyte_add_proto_library()` as the recommended target-oriented source or descriptor-set API;
- `protocyte_add_descriptor_set_library()` as the descriptor-set-specific convenience wrapper.

Most projects need only `protocyte_add_proto_library()`.

See the [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference) for complete signatures, argument rules, outputs, installation behavior, and ownership guarantees.

## Exported Targets

Source and installed-package consumers receive:

- `protocyte::codegen`;
- `protocyte::runtime`;
- `protocyte::runtime_hosted`.

`protocyte_add_proto_library()` selects `protocyte::runtime` by default. Passing `HOSTED_ALLOCATOR` selects `protocyte::runtime_hosted` unless the project supplies another `RUNTIME_TARGET` or emits a private runtime.

## Tool Ownership

Protocyte code generation uses three host-side inputs:

- Python 3.12 or newer;
- the `protoc-gen-protocyte` plugin;
- a host-runnable protobuf compiler and its import tree.

By default, CMake creates a fingerprinted Python environment under the build tree and installs the matching Protocyte generator there. Set `PROTOCYTE_PLUGIN_EXECUTABLE` before making Protocyte available when the application owns that environment instead.

When a parent configure owns Protocyte's managed environment and launches an
independent child configure, export the already validated plugin instead of
reading Protocyte's private CMake properties:

```cmake
protocyte_get_host_tools(PLUGIN_EXECUTABLE_VAR protocyte_plugin)
```

Pass `protocyte_plugin` to the child as
`-DPROTOCYTE_PLUGIN_EXECUTABLE:FILEPATH=...`. See
[CMake API Reference](CMake-API-Reference) for the complete host-tool output
surface and [ExternalProject Superbuild](ExternalProject-Superbuild) for a
complete handoff.

For native builds, Protocyte can fetch a pinned protobuf fallback when a usable compiler or import tree is missing. Set `PROTOCYTE_FETCH_PROTOBUF=OFF` to prohibit fallback downloads.

Cross builds must provide a concrete compiler that runs on the host. Protocyte does not build a host `protoc` with the target toolchain and does not run it through `CROSSCOMPILING_EMULATOR`.

See [Troubleshooting](https://github.com/anthonyprintup/protocyte/wiki/Troubleshooting) for Python selection, protobuf discovery, offline configuration, and cross-compilation failures.

## Version Pinning

Protocyte is pre-1.0. Source consumers should pin a reviewed full commit SHA until releases exist, then prefer an immutable release tag.

Installed consumers should pin the prefix itself. Final-release CMake packages accept exact version requests; prerelease packages intentionally use the unversioned `find_package(protocyte CONFIG REQUIRED)` form.

Do not track `main` in a reproducible build.
