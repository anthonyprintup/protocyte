# Installed Package

Use an installed Protocyte CMake package when a toolchain, SDK, package manager, superbuild, or release artifact owns the dependency prefix.

Consumers load the package with:

```cmake
find_package(protocyte CONFIG REQUIRED)
```

The installed package exposes the same generation functions and runtime targets as source consumption.

## Current Availability

Protocyte has not published its first tag or GitHub release.

Until a release exists, either:

- use the recommended [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent) integration; or
- install a reviewed source checkout into a private prefix.

Do not write installation instructions that imply unpublished assets already exist.

## Install from a Source Checkout

`PROTOCYTE_INSTALL` defaults to `ON` when Protocyte is the top-level CMake project.

### PowerShell

```powershell
cmake -S C:\path\to\protocyte -B build\protocyte
cmake --build build\protocyte --config Release
cmake --install build\protocyte `
  --config Release `
  --prefix "$PWD\build\protocyte-prefix"
```

### Linux, macOS, or Another POSIX Host

```bash
cmake \
  -S /path/to/protocyte \
  -B build/protocyte \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build/protocyte
cmake \
  --install build/protocyte \
  --prefix "$PWD/build/protocyte-prefix"
```

The resulting prefix can be moved or made read-only before a consumer uses it.

## Consume the Prefix

Minimal consumer configuration:

```cmake
cmake_minimum_required(VERSION 3.24)

project(protocyte_consumer LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

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

Make the prefix visible when configuring the consumer:

```console
cmake -S . -B build -DCMAKE_PREFIX_PATH=/path/to/protocyte-prefix
```

`CMAKE_PREFIX_PATH` must identify the prefix containing:

```text
lib/cmake/protocyte/protocyteConfig.cmake
```

On platforms or installations that select another CMake library directory, point `CMAKE_PREFIX_PATH` at the prefix root rather than directly at the package directory.

## Installed Contents

The prefix contains:

- the public Protocyte CMake functions;
- `protocyte::codegen`;
- `protocyte::runtime`;
- `protocyte::runtime_hosted`;
- the reusable C++ runtime header;
- the installable Protocyte Python project;
- hash-locked Python dependency constraints;
- `protocyte/options.proto`;
- license and notice files.

It does not contain:

- Python itself;
- a globally installed `protoc-gen-protocyte`;
- a protobuf compiler;
- a complete protobuf import tree.

The consumer still needs Python 3.12 or newer. Protobuf tools and imports must be available locally or explicitly fetched.

## Managed Python from an Installed Prefix

When code generation is first needed, the CMake package:

1. selects Python 3.12 or newer;
2. creates a fingerprinted environment under the consumer build tree;
3. copies the installed Python project to writable staging;
4. installs Protocyte and its locked dependencies into that environment;
5. leaves the package prefix and base interpreter unchanged.

This allows the installed prefix to remain read-only.

Python must provide `venv` and `ensurepip`. On Debian or Ubuntu, install `python3-venv` or the matching version-specific package when those modules are absent.

Select the base interpreter with:

```console
cmake -S . -B build \
  -DCMAKE_PREFIX_PATH=/path/to/protocyte-prefix \
  -DPython3_EXECUTABLE=/path/to/python3.12
```

Choose another managed-environment root with:

```cmake
set(
    PROTOCYTE_PYTHON_ENV_ROOT
    "${CMAKE_BINARY_DIR}/tools/protocyte-python"
)
find_package(protocyte CONFIG REQUIRED)
```

Relative roots resolve against `CMAKE_BINARY_DIR`. The path must not contain a semicolon.

Use `PROTOCYTE_PLUGIN_EXECUTABLE` when the consumer owns the plugin environment:

```cmake
set(
    PROTOCYTE_PLUGIN_EXECUTABLE
    "/path/to/protoc-gen-protocyte"
)
find_package(protocyte CONFIG REQUIRED)
```

The override must be version-compatible with the installed package.

## Protobuf Fallback

For installed packages, `PROTOCYTE_FETCH_PROTOBUF` defaults to `OFF`.

A consumer can explicitly allow the pinned fallback before loading the package:

```cmake
set(PROTOCYTE_FETCH_PROTOBUF ON CACHE BOOL "" FORCE)
find_package(protocyte CONFIG REQUIRED)
```

The fallback can:

- build a missing protobuf compiler for a native build;
- fetch only protobuf import sources when a host compiler already exists.

It does not replace an explicitly selected compiler.

Set `PROTOCYTE_FETCH_PROTOBUF=OFF` for controlled or offline builds and provide:

```cmake
set(
    Protobuf_PROTOC_EXECUTABLE
    "/path/to/host/protoc"
    CACHE FILEPATH
    "Host protobuf compiler"
)
set(
    PROTOCYTE_PROTOBUF_IMPORT_DIR
    "/path/to/protobuf/src"
)
```

Cross builds must provide a concrete compiler that runs directly on the host.

## Public Package Variables

After `find_package(protocyte CONFIG REQUIRED)`, consumers can use:

| Variable | Purpose |
|---|---|
| `PROTOCYTE_PROTO_DIR` | Installed directory containing `protocyte/options.proto` |
| `PROTOCYTE_OPTIONS_PROTO` | Full path to the installed `protocyte/options.proto` |
| `PROTOCYTE_FETCH_PROTOBUF` | Whether missing protobuf tools or imports may be fetched |
| `PROTOCYTE_PROTOBUF_GIT_TAG` | Pinned protobuf revision used by the fallback |
| `PROTOCYTE_PROTOBUF_IMPORT_DIR` | Optional caller-owned protobuf import root |
| `Protobuf_PROTOC_EXECUTABLE` | Optional explicit host compiler |
| `PROTOCYTE_PYTHON_ENV_ROOT` | Consumer-build root for managed Python environments |
| `PROTOCYTE_PLUGIN_EXECUTABLE` | Compatible preinstalled plugin override |
| `PROTOCYTE_TOOL_TIMEOUT_SECONDS` | Timeout for compiler and dependency-scan processes |

See the [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference) for argument-level behavior.

## Install a Generated Library

Opt a generated target into install/export support with `INSTALL_INCLUDE_DIR`:

```cmake
include(GNUInstallDirs)

find_package(protocyte CONFIG REQUIRED)

protocyte_add_proto_library(
    TARGET application_proto
    ALIAS application::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
    INSTALL_INCLUDE_DIR "${CMAKE_INSTALL_INCLUDEDIR}"
)

install(
    TARGETS application_proto
    EXPORT applicationTargets
    FILE_SET protocyte_generated_headers
        DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
)

install(
    EXPORT applicationTargets
    NAMESPACE application::
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/application"
)
```

`INSTALL_INCLUDE_DIR` adds the install interface and exposes generated headers through the `protocyte_generated_headers` file set.

The consuming package configuration must make Protocyte available before including the exported targets:

```cmake
include(CMakeFindDependencyMacro)
find_dependency(protocyte CONFIG)

include("${CMAKE_CURRENT_LIST_DIR}/applicationTargets.cmake")
```

The exported generated library retains its public Protocyte runtime and code-generation dependencies.

## Future Release Assets

The prepared release workflow is designed to publish three artifact types:

| Asset | Purpose |
|---|---|
| `protocyte-X.Y.Z-py3-none-any.whl` | Python plugin installation |
| `protocyte-X.Y.Z.tar.gz` | Python source distribution |
| `protocyte-X.Y.Z-cmake-prefix.tar.gz` | Preinstalled relocatable CMake prefix |

Only the `-cmake-prefix.tar.gz` archive is a `find_package()` prefix.

The wheel and plain source archive provide the Python plugin package. They do not provide `protocyteConfig.cmake`.

For prerelease tags such as `vX.Y.Z-rcN`:

- Python artifacts use the normalized version spelling `X.Y.ZrcN`;
- the CMake prefix keeps the tag spelling `protocyte-X.Y.Z-rcN-cmake-prefix.tar.gz`.

Check the [GitHub releases page](https://github.com/anthonyprintup/protocyte/releases) rather than assuming an asset exists.

## Version Requests

Final-release CMake packages accept exact version requests:

```cmake
find_package(protocyte <version> EXACT CONFIG REQUIRED)
```

Protocyte is pre-1.0 and does not promise compatibility across releases.

Prerelease package versions intentionally reject versioned `find_package()` calls. Pin the prerelease prefix itself and use:

```cmake
find_package(protocyte CONFIG REQUIRED)
```

## Relocation

The CMake prefix is designed to be relocatable:

- package paths are resolved from the loaded prefix;
- the managed Python project is staged into the consumer build tree;
- generated runtime targets use install-relative include directories;
- generated libraries can preserve virtual include prefixes through their header file sets.

After moving a prefix, remove or reconfigure consumer build trees that cached its previous absolute location.

## Related Pages

- [CMake Integration](https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration)
- [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent)
- [ExternalProject Superbuild](https://github.com/anthonyprintup/protocyte/wiki/ExternalProject-Superbuild)
- [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference)
- [Releases and Versioning](https://github.com/anthonyprintup/protocyte/wiki/Releases-and-Versioning)
