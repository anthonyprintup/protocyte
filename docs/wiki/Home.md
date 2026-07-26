# Protocyte

Protocyte is a Python `protoc` plugin that generates C++20 protobuf code for freestanding, embedded, kernel-style, and hosted applications.

Generated code avoids the STL, exceptions, RTTI, iostreams, and implicit global allocation. Applications choose their own allocation and storage model through the runtime configuration interface.

> **Project status:** Protocyte is currently pre-1.0. Pin an immutable revision and regenerate checked outputs when upgrading.

## Start Here

- **New to Protocyte?** Follow [Getting Started](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started) for a complete hosted C++ round trip.
- **Adding Protocyte to an existing build?** See [CMake Integration](https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration).
- **Building without the hosted allocator or standard containers?** Continue with [Embedded and Freestanding](https://github.com/anthonyprintup/protocyte/wiki/Embedded-and-Freestanding).
- **Looking for exact options or signatures?** Open the [CMake API Reference](https://github.com/anthonyprintup/protocyte/wiki/CMake-API-Reference) or [Plugin Parameters](https://github.com/anthonyprintup/protocyte/wiki/Plugin-Parameters).

## Recommended Integration

For most C++ projects, consume Protocyte through CMake `FetchContent` and create a generated library with `protocyte_add_proto_library()`.

This route keeps code generation in the build graph, tracks schema dependencies, and provides reusable runtime targets. The first configuration can provision Protocyte's isolated Python environment and fetch missing protobuf tools or imports.

Use the [ExternalProject Superbuild](https://github.com/anthonyprintup/protocyte/wiki/ExternalProject-Superbuild) approach when Protocyte and the consumer must be configured in separate build trees. Prebuilt CMake prefixes and `find_package()` are covered under [Installed Package](https://github.com/anthonyprintup/protocyte/wiki/Installed-Package).

## What Protocyte Provides

- C++20 generation for protobuf messages and enums.
- Proto2 and proto3 message-codec support, including optional fields.
- Scalars, strings, bytes, nested messages, oneofs, repeated fields, packed fields, maps, and recursive messages.
- Source-tree and descriptor-set generation.
- Target-oriented CMake helpers with automatic dependency tracking.
- Hosted defaults for quick adoption and configurable storage for constrained environments.
- Fallible parsing, serialization, cloning, and merging without exceptions.
- Optional LLDB formatters and debug reflection metadata.

## Requirements

The recommended CMake workflow requires:

- CMake 3.24 or newer.
- A C++20 compiler.
- Python 3.12 or newer with `venv` and `ensurepip`.
- Git and network access during the first configuration unless dependencies are already available locally.

Cross builds must provide a concrete, host-runnable `protoc` executable. Protocyte does not build a host tool with the target toolchain.

## Important Limits

Protocyte v1 does not generate RPC stubs, protobuf groups, generated extension fields, or Protobuf Editions code. Cross-file C++ naming collisions are rejected rather than silently renamed.

See [Compatibility and Limitations](https://github.com/anthonyprintup/protocyte/wiki/Compatibility-and-Limitations) before adopting Protocyte for an existing schema.

## Project Links

- [Source repository](https://github.com/anthonyprintup/protocyte)
- [Releases](https://github.com/anthonyprintup/protocyte/releases)
- [Issue tracker](https://github.com/anthonyprintup/protocyte/issues)
- [Contributing](https://github.com/anthonyprintup/protocyte/wiki/Contributing)
- [Apache License 2.0](https://github.com/anthonyprintup/protocyte/blob/main/LICENSE)
