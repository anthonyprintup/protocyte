# Protocyte

Protocyte is a Python `protoc` plugin that generates C++20 protobuf code for
freestanding or kernel-style environments. The generated C++ avoids STL
containers, exceptions, RTTI, iostreams, and hidden global allocation.

## Status

This repository implements the first generator/runtime milestone:

- `protoc-gen-protocyte` plugin plumbing.
- Proto3-only descriptor validation.
- C++ header/source generation for messages, enums, nested declarations,
  oneofs, optional fields, repeated fields, maps, and recursive message fields.
- Runtime emission under `protocyte/runtime/...`.
- Fallible runtime primitives: `Status`, `Result`, allocator context, byte
  views, vectors, strings/bytes, boxes, optionals, hash map storage, slice
  readers/writers, and protobuf wire helpers.
- Debug reflection metadata behind `PROTOCYTE_ENABLE_REFLECTION`.

Full deep-copy coverage for repeated, map, and oneof storage is intentionally
marked in the generated code as the next conformance pass.

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
- `protocyte/runtime/runtime.hpp` and `runtime.cpp` when `runtime=emit` is set

Supported parameters:

- `runtime=emit` or `runtime=emit:<prefix>`: emit runtime files.
- `runtime=omit`: do not emit runtime files.
- `namespace=<a::b>`: wrap generated package namespaces.
- `include_prefix=<path>`: prefix includes for imported generated headers.
- `explicit_default_instantiations=true`: reserved for future source emission.

Custom field options:

- Import `protocyte/options.proto` and use `bytes sha256 = 1 [(protocyte.array) = { max: 32 }, (protocyte.fixed) = true];`.
- Message constants are declared with repeated `option (protocyte.constant) = { ... };` entries and can be referenced from `array.expr`.
- Constants resolve within the current message, through enclosing messages, and across messages via qualified root-relative names such as `Outer.Inner.CAPACITY`.
- Supported constant kinds are `bool`, `int32`, `int64`, `uint32`, `uint64`, `float`, `double`, and `string`.
- Supported expression features are numeric `+ - * / %`, comparisons `< <= > >=`, equality `== !=`, boolean `! && ||`, string `+`, and the string helpers `len(...)`, `substr(...)`, and `starts_with(...)`.
- `array` on `bytes` generates inline bounded byte storage with a mutable size; `fixed` changes `bytes` to fixed-size storage with presence semantics and changes repeated arrays to exact-count validation on parse/serialize.
- Custom protobuf options must use the parenthesized extension syntax; `protocyte.array = { max: 32 }` is not valid `.proto` syntax for an extension option.

## C++ Contract

Every generated message is templated on a runtime config:

```cpp
template <class Config = ::protocyte::DefaultConfig>
class Message;
```

The default config uses a caller-supplied allocator context. Construction is
non-allocating, while operations that can allocate return `Status` or
`Result<T>`.

```cpp
protocyte::DefaultConfig::Context ctx{/* allocator */, /* limits */};
auto msg = demo::Sample<>::create(ctx);
```

Generated messages are move-only. Ordinary C++ copying is deleted because it
cannot report allocation failure. Use `clone()` or `copy_from()` for fallible
copying.

## Kernel Notes

The default runtime does not call `malloc` or `new` globally. Hosted allocation
helpers are available only when `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR` is defined,
which is intended for tests and examples rather than kernel builds.

Reflection tables are compiled only when `PROTOCYTE_ENABLE_REFLECTION` is
defined. Release builds do not get descriptor pools or dynamic reflection.
