# Protocyte

Protocyte is a Python `protoc` plugin that generates C++20 protobuf code for
freestanding, embedded, or kernel-style environments. The generated C++ avoids
the STL, exceptions, RTTI, iostreams, and implicit global allocation.

## AI Disclosure

This repository contains a mix of human-written and AI-assisted work. Some
source code, documentation, and generated artifacts were drafted or produced
with the help of AI tools and then reviewed, edited, and accepted by human
maintainers.

Because this project generates code intended for downstream use, users should
treat all generated output as needing normal engineering review, testing, and
validation before production use.

Responsibility for the contents of this repository and its releases remains
with the human maintainers and contributors.

## What It Supports

Protocyte currently targets `proto3` schemas and advertises
`FEATURE_PROTO3_OPTIONAL`.

Generated code supports:

- Messages and enums, including nested declarations.
- Scalar fields: `double`, `float`, `int32`, `int64`, `uint32`, `uint64`,
  `sint32`, `sint64`, `fixed32`, `fixed64`, `sfixed32`, `sfixed64`, `bool`,
  and enum-valued fields.
- `string`, `bytes`, message fields, `oneof`, `optional`, repeated fields,
  packed repeated scalars, maps, and recursive message fields.
- Fallible deep-copy helpers via `copy_from()` and `clone()`.
- Runtime emission under `protocyte/runtime/...`.
- Optional debug reflection metadata behind `PROTOCYTE_ENABLE_REFLECTION`.

The generated `merge_from()` and `serialize()` paths delegate scalar wire
parsing and writing to runtime helpers, so per-field generated code stays
smaller while preserving protobuf wire behavior.

## Current Limits

- `proto2` files are rejected.
- Protobuf Editions are rejected in v1.
- Proto3 extension declarations are not supported.
- Groups are not supported.
- `protocyte.array` cannot be applied to map fields.

## Usage

Protocyte's Python package requires Python 3.14 or newer. That applies to
local `uv sync` development, published wheel and sdist installs, and any CMake
workflow that runs the plugin through `Python3_EXECUTABLE`.

Install the project and make the virtual environment's script directory
discoverable to `protoc`:

```powershell
uv sync
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
```

On other shells, either activate `.venv` first or prepend the matching
`.venv/bin` directory to `PATH`.

For a ground-zero walkthrough that covers getting `protoc`, building and
installing the protocyte package, running `protoc` with the plugin, wiring the
generated files into a CMake target, and setting up automatic regeneration, see
[smoke/README.md](smoke/README.md).

Generate code:

```powershell
protoc --proto_path=. --protocyte_out=runtime=emit:generated tests/example.proto
```

The plugin emits:

- `foo.protocyte.hpp`
- `foo.protocyte.cpp`
- `protocyte/runtime/runtime.hpp` when runtime emission is enabled

## CMake Integration

Protocyte supports two CMake consumption modes:

- Source consumption with `FetchContent`
- Installed-package consumption with `find_package(protocyte CONFIG REQUIRED)`

### Release Assets

Published GitHub releases contain three different asset types:

- `protocyte-X.Y.Z-py3-none-any.whl`: the Python wheel for
  `protoc-gen-protocyte`. Install it into a Python 3.14+ environment when you
  want the plugin executable.
- `protocyte-X.Y.Z.tar.gz`: the Python source distribution for the same plugin
  package. It is also a Python 3.14+ artifact, not a CMake install tree.
- `protocyte-X.Y.Z-cmake-prefix.tar.gz`: a preinstalled CMake prefix for
  `find_package(protocyte CONFIG REQUIRED)`. Unpack it and add the extracted
  directory to `CMAKE_PREFIX_PATH`.

The CMake prefix archive includes the CMake files, C++ runtime headers, and
the protocyte Python generator sources, but it does not bundle Python itself.
Any downstream build that calls `protocyte_generate(...)` or
`protocyte_add_proto_library(...)` still needs a local Python 3.14+ interpreter
available to CMake through `Python3_EXECUTABLE` or the normal `find_package(Python3)`
search path.

For prerelease tags `vX.Y.Z-rcN`, the Python packaging artifacts use the
normalized version spelling `X.Y.ZrcN` in the wheel and sdist filenames,
while the CMake prefix archive keeps the Git tag spelling
`protocyte-X.Y.Z-rcN-cmake-prefix.tar.gz`.

### FetchContent

Minimal source-consumption setup:

```cmake
include(FetchContent)

FetchContent_Declare(
    protocyte
    GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
    GIT_TAG vX.Y.Z
)
FetchContent_MakeAvailable(protocyte)

protocyte_add_proto_library(
    TARGET demo_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

By default, the protocyte CMake project fetches protobuf when protobuf CMake
targets are not already available, then exposes:

- `protocyte_add_proto_library(...)` for the common target-oriented workflow
- `protocyte_generate(...)` as the lower-level codegen primitive
- `protocyte::runtime` and `protocyte::runtime_hosted` for reusable runtime linkage

Pin a published release tag for downstream builds instead of tracking `main`.

### Installed Package

You can also install protocyte into a prefix and consume it later with
`find_package`.

For published releases, use the `protocyte-X.Y.Z-cmake-prefix.tar.gz` asset
described above, unpack it, and point `CMAKE_PREFIX_PATH` at the extracted
prefix directory. Do not use the plain `protocyte-X.Y.Z.tar.gz` sdist here;
that archive is only the Python plugin package source.

Install protocyte:

```powershell
cmake -S . -B build/protocyte
cmake --install build/protocyte --prefix C:\path\to\protocyte-prefix
```

Minimal consumer setup:

```cmake
find_package(protocyte CONFIG REQUIRED)

protocyte_add_proto_library(
    TARGET demo_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    DISCOVER
    HOSTED_ALLOCATOR
)
```

Configure the consumer with `-DCMAKE_PREFIX_PATH=<prefix>` so CMake can find
`protocyteConfig.cmake`.

The installed CMake package installs:

- the `protocyte_add_proto_library(...)` and `protocyte_generate(...)` CMake integration
- the exported `protocyte::codegen`, `protocyte::runtime`, and `protocyte::runtime_hosted` targets
- the protocyte Python sources used by the plugin wrapper
- the reusable C++ runtime headers and targets
- `protocyte/options.proto`

The installed package does not embed Python or protobuf. Consumers that run
code generation still need a working Python 3.14+ interpreter, and they either
need protobuf/protoc available already or they can opt into the fetch fallback:

```cmake
set(PROTOCYTE_FETCH_PROTOBUF ON CACHE BOOL "" FORCE)
find_package(protocyte CONFIG REQUIRED)
```

Public CMake variables exposed by the package:

- `PROTOCYTE_PROTO_DIR`: the installed directory that contains `protocyte/options.proto`
- `PROTOCYTE_OPTIONS_PROTO`: the full path to `protocyte/options.proto`
- `PROTOCYTE_PROTOBUF_GIT_TAG`: the protobuf revision used when `PROTOCYTE_FETCH_PROTOBUF=ON`

`protocyte_add_proto_library(...)` links generated code against
`protocyte::runtime` by default, or `protocyte::runtime_hosted` when
`HOSTED_ALLOCATOR` is enabled. Use `EMIT_RUNTIME` only when you explicitly want
the runtime header emitted into the generated output tree instead of reusing
the installed/runtime target.

The full end-to-end examples, including building a static library from
generated translation units, are in [smoke/README.md](smoke/README.md),
[tests/fetchcontent/CMakeLists.txt](tests/fetchcontent/CMakeLists.txt), and
[tests/find_package/CMakeLists.txt](tests/find_package/CMakeLists.txt).

## Plugin Parameters

Supported `--protocyte_out=` parameters:

- `runtime=emit`: emit `runtime.hpp` under `protocyte/runtime`.
- `runtime=emit:<prefix>`: emit `runtime.hpp` under a custom prefix.
- `runtime=omit`: do not emit runtime files.
- `runtime_prefix=<path>`: override the runtime include/output prefix when
  runtime emission is enabled.
- `namespace_prefix=<a::b>`: prepend additional C++ namespaces around the file
  package namespace.
- `namespace=<a::b>`: accepted as an alias for `namespace_prefix`; specify only
  one of the two names.
- `include_prefix=<path>`: prefix includes for imported generated headers.

Example:

```powershell
protoc `
  --proto_path=. `
  --protocyte_out=runtime=emit:vendor/protocyte,namespace_prefix=mycorp::wire,include_prefix=generated:out `
  tests/example.proto
```

## Protocyte Extensions

Protocyte ships custom protobuf options in
[protocyte/options.proto](protocyte/options.proto).

Available extensions:

- `option (protocyte.package_constant) = { ... };` on files.
- `option (protocyte.constant) = { ... };` on messages.
- `(protocyte.array) = { max: ... }`, `(protocyte.array) = { expr: ... }`, or
  `(protocyte.array) = { ..., fixed: true }` on fields.

Custom option extensions must use the parenthesized protobuf extension syntax.
This is valid:

```proto
bytes sha256 = 1 [(protocyte.array) = { max: 32, fixed: true }];
```

This is not valid protobuf extension syntax:

```proto
bytes sha256 = 1 [protocyte.array = { max: 32 }];
```

### Package Constants

Package constants are declared as repeated file options and are emitted as
namespace-scope `inline constexpr` declarations in the generated C++:

```proto
option (protocyte.package_constant) = { name: "CAP", u32: 32 };
option (protocyte.package_constant) = { name: "LABEL", str: "pkt" };
```

Package constants can reference other package constants from the same package.

### Message Constants

Message constants are declared as repeated message options:

```proto
message Packet {
  option (protocyte.constant) = { name: "DOUBLE_CAP", u32_expr: "CAP * 2" };
  option (protocyte.constant) = { name: "FULL_LABEL", str_expr: "LABEL + \"-frame\"" };
}
```

Constants must set exactly one typed value field. Supported fields are:

- `boolean`, `boolean_expr`
- `i32`, `i32_expr`
- `u32`, `u32_expr`
- `i64`, `i64_expr`
- `u64`, `u64_expr`
- `f32`, `f32_expr`
- `f64`, `f64_expr`
- `str`, `str_expr`

Constants can be referenced from `array.expr`. Resolution works:

- Within the current message.
- Through enclosing messages.
- Through package constants from the current package.
- Across messages with qualified root-relative names such as
  `Outer.Inner.CAPACITY`.
- Across messages in other packages with fully qualified names such as
  `my.pkg.Outer.Inner.CAPACITY`.
- Through package-qualified constants such as `my.pkg.CAPACITY`.

Supported expression features:

- Numeric operators: `+`, `-`, `*`, `/`, `%`
- Comparisons: `<`, `<=`, `>`, `>=`
- Equality: `==`, `!=`
- Boolean operators: `!`, `&&`, `||`
- String concatenation: `+`
- String helpers: `len(...)`, `substr(...)`, `starts_with(...)`

### Array And Fixed Storage

`protocyte.array` changes storage generation for bounded fields:

- On `bytes`, it generates inline bounded byte storage with a mutable size.
- On repeated scalar fields, it generates bounded inline array storage.

`protocyte.array.fixed` tightens that storage:

- On `bytes`, it generates fixed-size storage with presence semantics.
- On repeated arrays, parse/serialize/size validation allows either zero
  elements or the exact element count, rather than allowing any count up to the
  bound.

Examples:

```proto
message Digest {
  bytes sha256 = 1 [(protocyte.array) = { max: 32, fixed: true }];
}
```

```proto
option (protocyte.package_constant) = { name: "CAP", u32: 16 };

message Samples {
  option (protocyte.constant) = { name: "DOUBLE_CAP", u32_expr: "CAP * 2" };
  repeated int32 values = 1 [(protocyte.array) = { expr: "CAP" }];
  repeated uint32 lanes = 2 [(protocyte.array) = { expr: "4", fixed: true }];
}
```

## Generated C++ API

Every generated message is templated on a runtime config:

```cpp
template <class Config = ::protocyte::DefaultConfig>
struct Message;
```

The default config uses a caller-supplied allocator context. Construction is
non-allocating. Operations that may allocate return `::protocyte::Status` or
`::protocyte::Result<T>`.

```cpp
protocyte::DefaultConfig::Context ctx{/* allocator */, /* limits */};
auto msg = demo::Sample<>::create(ctx);
```

If you provide a non-default `Config`, protocyte now treats that as a stricter
public contract:

- `Config::Context` must expose `allocator`, `limits`, and `recursion_depth`.

This is a source-breaking change for custom configs. Default-config users are
unaffected.

Generated messages are move-only. Ordinary C++ copying is deleted because it
cannot report allocation failure.

Common generated operations include:

- `create(ctx)`
- `parse(ctx, reader)`
- `merge_from(reader)`
- `serialize(writer)`
- `encoded_size()`
- `copy_from(other)`
- `clone()`
- field accessors, `has_*()`, `set_*()`, `mutable_*()`, and `ensure_*()` where applicable

## Runtime Notes

The default runtime does not call `malloc` or `new` globally. Hosted allocation
helpers are compiled only when `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR` is defined,
which is intended for tests and examples rather than kernel builds.

The runtime provides:

- `Status` and `Result<T>`
- allocator-aware vectors, strings/bytes, optionals, boxes, and maps
- bounded byte and array storage helpers
- slice readers and writers
- protobuf tag, varint, fixed-width, skip, scalar parse, and scalar serialize helpers

Reflection tables are emitted only when `PROTOCYTE_ENABLE_REFLECTION` is
defined. Release builds do not get descriptor pools or dynamic reflection.
