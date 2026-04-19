# Protocyte

Protocyte is a Python `protoc` plugin that generates C++20 protobuf code for
freestanding, embedded, or kernel-style environments. The generated C++ avoids
the STL, exceptions, RTTI, iostreams, and implicit global allocation.

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

Install the project into an environment where `protoc` can find the console
script:

```powershell
uv sync
```

Generate code:

```powershell
protoc --proto_path=. --protocyte_out=runtime=emit:generated tests/example.proto
```

The plugin emits:

- `foo.protocyte.hpp`
- `foo.protocyte.cpp`
- `protocyte/runtime/runtime.hpp` and `runtime.cpp` when runtime emission is enabled

## Plugin Parameters

Supported `--protocyte_out=` parameters:

- `runtime=emit`: emit runtime files under `protocyte/runtime`.
- `runtime=emit:<prefix>`: emit runtime files under a custom prefix.
- `runtime=omit`: do not emit runtime files.
- `runtime_prefix=<path>`: override the runtime include/output prefix when
  runtime emission is enabled.
- `namespace_prefix=<a::b>`: prepend additional C++ namespaces around the file
  package namespace.
- `namespace=<a::b>`: accepted as an alias for `namespace_prefix`.
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
- `(protocyte.array) = { max: ... }` or `(protocyte.array) = { expr: ... }` on fields.
- `(protocyte.fixed) = true` on fields that also use `protocyte.array`.

Custom option extensions must use the parenthesized protobuf extension syntax.
This is valid:

```proto
bytes sha256 = 1 [(protocyte.array) = { max: 32 }, (protocyte.fixed) = true];
```

This is not valid protobuf extension syntax:

```proto
bytes sha256 = 1 [protocyte.array = { max: 32 }];
```

### Package Constants

Package constants are declared as repeated file options and are emitted as
namespace-scope `inline constexpr` declarations in the generated C++:

```proto
option (protocyte.package_constant) = { name: "CAP", kind: UINT32, literal: "32" };
option (protocyte.package_constant) = { name: "LABEL", kind: STRING, literal: "pkt" };
```

Package constants can reference other package constants from the same package.

### Message Constants

Message constants are declared as repeated message options:

```proto
message Packet {
  option (protocyte.constant) = { name: "DOUBLE_CAP", kind: UINT32, expr: "CAP * 2" };
  option (protocyte.constant) = { name: "FULL_LABEL", kind: STRING, expr: "LABEL + \"-frame\"" };
}
```

Supported constant kinds are:

- `BOOL`
- `INT32`
- `INT64`
- `UINT32`
- `UINT64`
- `FLOAT`
- `DOUBLE`
- `STRING`

Constants can be referenced from `array.expr`. Resolution works:

- Within the current message.
- Through enclosing messages.
- Through package constants from the current package.
- Across messages with qualified root-relative names such as
  `Outer.Inner.CAPACITY`.
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

`protocyte.fixed` tightens that storage:

- On `bytes`, it generates fixed-size storage with presence semantics.
- On repeated arrays, parse/serialize/size validation requires an exact element
  count rather than allowing any count up to the bound.

Examples:

```proto
message Digest {
  bytes sha256 = 1 [(protocyte.array) = { max: 32 }, (protocyte.fixed) = true];
}
```

```proto
option (protocyte.package_constant) = { name: "CAP", kind: UINT32, literal: "16" };

message Samples {
  option (protocyte.constant) = { name: "DOUBLE_CAP", kind: UINT32, expr: "CAP * 2" };
  repeated int32 values = 1 [(protocyte.array) = { expr: "CAP" }];
  repeated uint32 lanes = 2 [(protocyte.array) = { expr: "4" }, (protocyte.fixed) = true];
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
