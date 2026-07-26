# Runtime Reference

Protocyte's generated code uses a small C++20 runtime designed for hosted,
embedded, freestanding, and kernel-style consumers.

## Core types

- `Status` carries success or an `Error`.
- `Result<T>` carries a value or an `Error`.
- `Optional<T>`, `Box<T>`, `Vector<T>`, `Map<K, V>`, and `String` use the
  message configuration and context.
- `Span<T>` is a non-owning contiguous view.
- `SliceReader` and `SliceWriter` provide bounded in-memory wire I/O.
- `Reader` and `Writer` concepts support custom streaming implementations.

Access `.error()` only after a false status check. Successful results expose
their value through `*result` or `.value()`.

## Configuration and allocation

`DefaultConfig` defines the container aliases, allocator hooks, context type,
limits, and compile-time policies expected by generated templates. Messages
hold a non-owning context binding; the context, allocator state, and callback
state must outlive them.

The default runtime does not call global `malloc` or `new`. Hosted helpers are
compiled only when `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR` is nonzero. See
[Embedded and Freestanding](Embedded-and-Freestanding) for custom
configuration.

## Wire I/O

The runtime provides tag, varint, zig-zag, fixed-width, length-delimited,
scalar parse, scalar serialize, and unknown-field skip helpers. Generated
`merge_from()` and `serialize()` delegate scalar work to these helpers.

Readers and writers use absolute top-level byte positions for diagnostics.
Custom implementations must obey the runtime's capacity, cursor, and failure
contracts; successful calls advance exactly by the reported bytes, while
failed calls do not claim unwritten or unread data.

## Limits

`Limits` includes:

- `max_total_bytes` — default `0x7fffffff`;
- `max_recursion_depth` — default `100`;
- `max_message_bytes`;
- `max_string_bytes`;
- `max_unknown_field_bytes` — default `0x7fffffff`;
- `max_repeated_elements` — default `0x7fffffff`;
- `max_map_entries` — default `0x7fffffff`;
- `max_total_allocation_bytes` — unbounded by default for `DefaultConfig`.

Repeated and map budgets count occurrences across one top-level operation.
Finite collection and allocation limits are application policy and may reject
otherwise wire-valid protobuf input. Arena-like allocators without a
deallocation callback retain charged bytes until the context is reclaimed.

## String views

Generated `string` accessors use `::protocyte::Span<const char>` by default.
This keeps the default surface free of exception-bearing standard-library
operations.

Hosted users can opt into `std::string_view`:

```cmake
target_compile_definitions(
    demo_proto
    PUBLIC PROTOCYTE_ENABLE_STD_STRING_VIEW=1
)
```

The definition changes the public `::protocyte::StringView` type, generated
signatures, and constants. Apply it with `PUBLIC` visibility to the target
compiling generated sources. All translation units in that target graph must
compile with the same value.

## String formatting

`PROTOCYTE_ENABLE_STD_FORMAT` and `PROTOCYTE_ENABLE_FMT_FORMAT` are hosted
interoperability opt-ins, both defaulting to `0`.

```cmake
target_compile_definitions(demo_proto PUBLIC PROTOCYTE_ENABLE_STD_FORMAT=1)
target_compile_definitions(demo_proto PUBLIC PROTOCYTE_ENABLE_FMT_FORMAT=1)
```

The standard formatter is emitted only when the library advertises suitable
C++20 format support. The `{fmt}` integration exposes `format_as`; consumers
remain responsible for providing and linking `{fmt}`. These runtime macros are
unrelated to the generator's source-formatting parameters.

## Reflection

Reflection is disabled unless `PROTOCYTE_ENABLE_REFLECTION` is nonzero:

```cmake
target_compile_definitions(
    demo_proto
    PUBLIC PROTOCYTE_ENABLE_REFLECTION=1
)
```

PUBLIC visibility is required so generated `.protocyte.cpp` files and every
consumer see the same declaration surface. `TYPE SHARED` helper targets on
Windows receive target-unique import/export definitions automatically. Raw
generated output compiled into a Windows DLL must manage visibility itself.

Each message exposes an external
`std::array<protocyte::ReflectionFieldInfo, N>` in the generated package's
`protocyte_reflection` namespace. Entries report name, number, kind, descriptor
label, packed state, and protobuf presence independently.

## Compile-time feature macros

- `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR`
- `PROTOCYTE_ENABLE_STD_STRING_VIEW`
- `PROTOCYTE_ENABLE_STD_FORMAT`
- `PROTOCYTE_ENABLE_FMT_FORMAT`
- `PROTOCYTE_ENABLE_REFLECTION`

Treat macros that affect public generated declarations or template
instantiation as target-wide ABI settings.

## Related pages

- [Generated C++ API](Generated-Cpp-API)
- [Errors, Limits, and Wire Behavior](Errors-Limits-and-Wire-Behavior)
- [Embedded and Freestanding](Embedded-and-Freestanding)
