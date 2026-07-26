# Protocyte

Protocyte is a Python `protoc` plugin that generates C++20 protobuf code for
freestanding, embedded, kernel-style, and hosted applications.

Generated code avoids the STL, exceptions, RTTI, iostreams, and implicit global
allocation. Applications choose their allocation and storage model through the
runtime configuration interface.

> **Project status:** Protocyte is currently version `0.1.0` and pre-1.0.
> Pin an immutable revision and regenerate checked outputs when upgrading.

## Start Here

Follow the **[Getting Started
guide](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started)** for a
complete schema-to-C++ round trip on Windows, Linux, or macOS.

- [Choose a CMake integration](https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration)
- [Review compatibility and limitations](https://github.com/anthonyprintup/protocyte/wiki/Compatibility-and-Limitations)
- [Browse the complete wiki](https://github.com/anthonyprintup/protocyte/wiki)

## What It Supports

- C++20 generation for protobuf messages and enums.
- Proto2 and proto3 message codecs, including optional fields.
- Scalars, strings, bytes, nested messages, oneofs, repeated and packed fields,
  maps, and recursive messages.
- Source-tree and descriptor-set generation.
- Target-oriented CMake helpers with automatic schema dependency tracking.
- Hosted defaults plus configurable allocation and storage for constrained
  environments.
- Fallible parsing, serialization, cloning, and merging without exceptions.
- Optional LLDB formatters and debug reflection metadata.

Protocyte V1 does not generate RPC stubs, protobuf groups, generated extension
fields, or Protobuf Editions code. Cross-file C++ naming collisions are
rejected rather than silently renamed. See [Compatibility and
Limitations](https://github.com/anthonyprintup/protocyte/wiki/Compatibility-and-Limitations)
for the complete boundary.

## Requirements

The recommended CMake workflow requires:

- CMake 3.24 or newer.
- A C++20 compiler.
- Python 3.12 or newer with `venv` and `ensurepip`.
- Git and network access during the first configuration unless all sources and
  tools are supplied locally.

Cross builds must provide a concrete, host-runnable `protoc` executable.

## CMake FetchContent

`FetchContent` is the recommended integration for most C++ projects. Pin the
reviewed full commit SHA:

```cmake
cmake_minimum_required(VERSION 3.24)
project(application LANGUAGES CXX)

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
target_compile_features(application PRIVATE cxx_std_20)
```

The first configuration can provision Protocyte's isolated Python environment
and fetch missing protobuf tools or imports. The checked
[`examples/quickstart`](examples/quickstart) project exercises this exact
integration.

Use the [ExternalProject
superbuild](https://github.com/anthonyprintup/protocyte/wiki/ExternalProject-Superbuild)
when Protocyte and the consumer must configure in separate build trees. Use the
[installed package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package)
workflow for a preinstalled private or system prefix.

## Project

- [Documentation](https://github.com/anthonyprintup/protocyte/wiki)
- [Releases and versioning](https://github.com/anthonyprintup/protocyte/wiki/Releases-and-Versioning)
- [Contributing](https://github.com/anthonyprintup/protocyte/wiki/Contributing)
- [Issue tracker](https://github.com/anthonyprintup/protocyte/issues)
- [AI disclosure](https://github.com/anthonyprintup/protocyte/wiki/AI-Disclosure)
- [Apache License 2.0](LICENSE)
