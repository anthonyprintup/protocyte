# ExternalProject Superbuild

Use CMake `ExternalProject` when Protocyte and the consuming application must have separate configure, cache, build, and install boundaries.

This is an isolation-oriented alternative to the recommended [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent) workflow.

## Why a Superbuild Needs Two External Projects

`ExternalProject_Add()` performs its configure and build steps after the parent superbuild has configured. A Protocyte prefix produced by an external project therefore cannot satisfy `find_package(protocyte)` in the parent configure.

Use this dependency chain:

```text
superbuild
|-- protocyte_external
|   |-- configures Protocyte independently
|   `-- installs a private CMake prefix
`-- application_external
    |-- depends on protocyte_external
    |-- configures after the prefix exists
    `-- uses find_package(protocyte CONFIG REQUIRED)
```

Do not call `find_package(protocyte)` from the superbuild itself.

## Project Layout

```text
protocyte-superbuild/
|-- CMakeLists.txt
`-- application/
    |-- CMakeLists.txt
    |-- main.cpp
    `-- proto/
        `-- reading.proto
```

The application sources can be copied from [Getting Started](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started). Only the CMake integration changes.

## Superbuild CMakeLists

Create the top-level `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.24)

project(protocyte_superbuild LANGUAGES NONE)

include(ExternalProject)

set(
    PROTOCYTE_PRIVATE_PREFIX
    "${CMAKE_BINARY_DIR}/protocyte-prefix"
)

set(superbuild_config_args)
if(NOT CMAKE_CONFIGURATION_TYPES AND CMAKE_BUILD_TYPE)
    list(
        APPEND superbuild_config_args
        "-DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}"
    )
endif()

ExternalProject_Add(
    protocyte_external
    PREFIX "${CMAKE_BINARY_DIR}/protocyte"
    GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
    GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14
    UPDATE_DISCONNECTED TRUE
    INSTALL_DIR "${PROTOCYTE_PRIVATE_PREFIX}"
    CMAKE_ARGS
        ${superbuild_config_args}
        "-DCMAKE_INSTALL_PREFIX:PATH=<INSTALL_DIR>"
        "-DPROTOCYTE_INSTALL:BOOL=ON"
)

ExternalProject_Add(
    application_external
    PREFIX "${CMAKE_BINARY_DIR}/application-prefix"
    SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/application"
    BINARY_DIR "${CMAKE_BINARY_DIR}/application"
    DEPENDS protocyte_external
    BUILD_ALWAYS TRUE
    CMAKE_ARGS
        ${superbuild_config_args}
        "-DCMAKE_PREFIX_PATH:PATH=${PROTOCYTE_PRIVATE_PREFIX}"
        "-DPROTOCYTE_FETCH_PROTOBUF:BOOL=ON"
    INSTALL_COMMAND ""
)
```

The Protocyte project installs into a build-private prefix. The application receives that prefix through its own `CMAKE_PREFIX_PATH`; it does not inherit Protocyte targets or cache entries from the superbuild.

`BUILD_ALWAYS TRUE` lets the application's own build system recheck source
dependencies on every superbuild invocation. Without it, ExternalProject's
completed build stamp could hide edits made under the local `application`
source tree.

The full commit SHA is intentional. Pin a reviewed immutable commit until releases exist, then prefer an immutable release tag.

## Application CMakeLists

Create `application/CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.24)

project(protocyte_external_application LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

protocyte_add_proto_library(
    TARGET application_proto
    ALIAS application::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(protocyte_external_application main.cpp)
target_link_libraries(
    protocyte_external_application
    PRIVATE application::proto
)
target_compile_features(
    protocyte_external_application
    PRIVATE cxx_std_20
)

enable_testing()
add_test(
    NAME protocyte_external_project_round_trip
    COMMAND protocyte_external_application
)
```

The installed package defaults `PROTOCYTE_FETCH_PROTOBUF` to `OFF`. The superbuild explicitly passes `ON` to the application so a native build can fetch a pinned protobuf fallback when the compiler or import tree is absent.

For a controlled or offline build, leave that option off and pass explicit tool paths instead.

## Configure, Build, and Test

### PowerShell

```powershell
cmake -S . -B build
cmake --build build --config Release --target application_external
ctest --test-dir build\application -C Release --output-on-failure
```

### Linux, macOS, or Another POSIX Host

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target application_external
ctest --test-dir build/application --output-on-failure
```

Building `application_external` first builds and installs `protocyte_external`, then configures and builds the application.

The installed prefix is located at:

```text
build/protocyte-prefix/
```

The application build tree is located at:

```text
build/application/
```

A successful test ends with:

```text
100% tests passed, 0 tests failed out of 1
```

## Pass an Explicit Python Interpreter

External projects have independent CMake caches. A `Python3_EXECUTABLE` value in the superbuild is not inherited automatically.

Add it to the application external project's `CMAKE_ARGS`:

```cmake
ExternalProject_Add(
    application_external
    # ...
    CMAKE_ARGS
        ${superbuild_config_args}
        "-DCMAKE_PREFIX_PATH:PATH=${PROTOCYTE_PRIVATE_PREFIX}"
        "-DPROTOCYTE_FETCH_PROTOBUF:BOOL=ON"
        "-DPython3_EXECUTABLE:FILEPATH=/path/to/python3.12"
    INSTALL_COMMAND ""
)
```

The application configure uses Python to provision the generator from the installed Protocyte prefix.

## Controlled and Offline Builds

A fully offline superbuild must control both stages:

1. provide an existing Protocyte source checkout to the install stage;
2. provide the application stage with a compatible plugin, host `protoc`, and protobuf import tree.

Replace the Git download fields in `protocyte_external` with:

```cmake
SOURCE_DIR "/path/to/protocyte"
DOWNLOAD_COMMAND ""
UPDATE_COMMAND ""
```

Pass the tool paths to `application_external`:

```cmake
CMAKE_ARGS
    ${superbuild_config_args}
    "-DCMAKE_PREFIX_PATH:PATH=${PROTOCYTE_PRIVATE_PREFIX}"
    "-DPROTOCYTE_FETCH_PROTOBUF:BOOL=OFF"
    "-DPROTOCYTE_PLUGIN_EXECUTABLE:FILEPATH=/path/to/protoc-gen-protocyte"
    "-DProtobuf_PROTOC_EXECUTABLE:FILEPATH=/path/to/protoc"
    "-DPROTOCYTE_PROTOBUF_IMPORT_DIR:PATH=/path/to/protobuf/src"
```

The checked example also accepts
`-DPROTOCYTE_SOURCE_DIR=/path/to/protocyte`. That cache variable replaces the
Git download with the supplied source tree and is how repository tests exercise
the current checkout. Explicit plugin, `protoc`, protobuf import, and Python
variables supplied to the superbuild are forwarded to the dependent
application configure.

`PROTOCYTE_PROTOBUF_IMPORT_DIR` must contain `google/protobuf/descriptor.proto`.

## Cross Compilation

Treat the two external projects separately:

- the Protocyte install contains architecture-independent CMake files, Python sources, protobuf options, and C++ headers;
- the application external project owns the target toolchain and generated C++ build;
- code generation still requires a concrete `protoc` that runs on the build host.

Pass the target toolchain file only to `application_external` unless the Protocyte install stage has an independent reason to use it:

```cmake
"-DCMAKE_TOOLCHAIN_FILE:FILEPATH=/path/to/target-toolchain.cmake"
```

Also pass a host-runnable `Protobuf_PROTOC_EXECUTABLE`. Protocyte does not build a host compiler with the target toolchain or invoke one through `CROSSCOMPILING_EMULATOR`.

## Updating Protocyte

Change the pinned `GIT_TAG`, reconfigure the superbuild, and rebuild `application_external`.

Because `UPDATE_DISCONNECTED` is enabled, repeated builds do not contact the remote merely to check for updates. Changing the declared revision still gives CMake an explicit reason to update the external source.

Protocyte is pre-1.0. Regenerate and retest all checked outputs when changing the pin.

## Tradeoffs

Compared with FetchContent, this design provides:

- separate CMake caches;
- an explicit install boundary;
- no Protocyte targets in the superbuild;
- easier reuse of one private prefix across dependent external consumers.

It also introduces:

- two configure phases;
- a longer first build;
- explicit forwarding for toolchains, Python, and other cache settings;
- more complicated IDE integration.

Use FetchContent unless one of these isolation properties is required.

## Checked Example

The repository's tested version of this layout lives under:

[examples/external-project-superbuild](https://github.com/anthonyprintup/protocyte/tree/main/examples/external-project-superbuild)

## Related Pages

- [CMake Integration](https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration)
- [FetchContent](https://github.com/anthonyprintup/protocyte/wiki/FetchContent)
- [Installed Package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package)
- [Troubleshooting](https://github.com/anthonyprintup/protocyte/wiki/Troubleshooting)
