# Generated C++ API

Every generated message is templated on a runtime configuration:

```cpp
template <class Config = ::protocyte::DefaultConfig>
struct Message;
```

Generated messages are move-only. Ordinary C++ copying is deleted because it cannot report allocation failure.

## Construct a Message

Construction binds a non-owning context and does not allocate:

```cpp
protocyte::DefaultConfig::Context ctx {
    protocyte::hosted_allocator(),
    protocyte::Limits {},
};

auto message = demo::Sample<>::create(ctx);
```

The context and allocator state must outlive the message.

## Failure Model

Primitive scalar setters return `void`. Operations that can fail return `[[nodiscard]]` values:

- `protocyte::Status`;
- `protocyte::Result<T>`;
- `protocyte::Result<T&>` for reference-valued operations.

Check a result before reading its value:

```cpp
const auto parsed = demo::Sample<>::parse(ctx, bytes);
if (!parsed) {
    const auto &error = parsed.error();
    // error.code, error.offset, error.field_number
}

const auto &message = *parsed;
```

Access `.error()` only after a false status check.

## Common Operations

Generated messages expose:

- `create(ctx)`;
- `parse(ctx, reader)` and `parse(ctx, input_bytes)`;
- `parse(reader, output)`;
- `merge_from(reader)`;
- `serialize(writer)` and `serialize(output_bytes)`;
- `encoded_size()`;
- `copy_from(source)` and `copy_from(source, staging_message)`;
- `clone()` and `clone(output)`;
- protobuf-derived field accessors.

## Field Accessors

The exact accessor set depends on field kind and presence:

- immutable accessors such as `value()`;
- `set_*()` for scalar values;
- `has_*()` for fields with presence;
- `clear_*()` where clearing is meaningful;
- `mutable_*()` for mutable strings, bytes, messages, and containers;
- `ensure_*()` for fallible nested-message creation.

Repeated fields expose their configured vector surface. Maps expose their configured map surface. Oneofs expose a case discriminator and only commit case changes after the incoming value is ready.

The current setter and mutation failure model is:

| Field or operation | Generated result | Why it can fail |
|---|---|---|
| Numeric and boolean scalar setter | `void` | Direct assignment |
| Enum setter | `protocyte::Status` | Closed-enum validation |
| String or bytes setter | `protocyte::Status` | Allocation, configured limits, or fixed-size validation |
| Nested-message `ensure_*()` | `protocyte::Result<T&>` | Nested storage allocation |
| Repeated and map mutation | Container-specific `Status` or `Result<T&>` | Allocation, capacity, or configured limits |
| `clear_*()` | `void` | Releases or resets existing state |

Fallible return types are `[[nodiscard]]`; check them even when the selected
hosted allocator normally succeeds.

## Parse from Contiguous Bytes

`parse(ctx, input)` accepts `protocyte::Span<const protocyte::u8>`:

```cpp
const auto parsed = demo::Sample<>::parse(ctx, encoded);
```

Compatible lvalue ranges such as arrays, `std::array`, `std::vector`, and `std::span` convert to the dynamic span automatically.

The overload creates a `SliceReader` and delegates to the reader-based parser.

## Parse into Caller Storage

Avoid a complete outer-message temporary:

```cpp
demo::Sample<> output {ctx};
protocyte::SliceReader reader {encoded.data(), encoded.size()};

const auto status = demo::Sample<>::parse(reader, output);
if (!status) {
    // output is empty and remains bound to ctx
}
```

On failure, the output is reset to an empty message with its original destination context.

## Merge

`merge_from(reader)` follows protobuf merge semantics.

Successfully parsed field occurrences remain committed if a later occurrence fails. The failing occurrence itself does not change visible state:

- singular nested messages commit after the complete occurrence parses;
- oneofs switch cases only after successful parsing;
- repeated fields append only complete elements;
- malformed packed payloads append no decoded prefix;
- maps insert only complete entries.

See [Errors, Limits, and Wire Behavior](https://github.com/anthonyprintup/protocyte/wiki/Errors-Limits-and-Wire-Behavior).

## Encoded Size and Serialization

Compute the required size:

```cpp
const auto size = message.encoded_size();
if (!size) {
    return handle(size.error());
}
```

Serialize to a mutable contiguous range:

```cpp
std::vector<protocyte::u8> encoded(*size);
const auto written = message.serialize(encoded);
```

This overload returns the number of bytes written. It preflights the encoded size, so an undersized contiguous buffer returns `ErrorCode::size_limit` without modifying the buffer.

`serialize(writer)` is incremental rather than transactional. A custom writer failure can leave bytes from earlier successful calls committed. Stage output when all-or-nothing publication is required.

## Copy and Clone

Generated messages use explicit fallible deep copies:

```cpp
const auto status = destination.copy_from(source);
const auto cloned = source.clone();
```

Caller-controlled variants avoid an internal full-message temporary:

```cpp
demo::Sample<> staging {ctx};
const auto copy_status = destination.copy_from(source, staging);

demo::Sample<> output {ctx};
const auto clone_status = source.clone(output);
```

`copy_from(source, staging)` is transactional for the destination. On success, `staging` remains valid but moved-from and must not alias either operand.

`clone()` uses the source context. `clone(output)` retains the context already bound to `output`.

## Strings

Generated immutable `string` accessors return `protocyte::StringView`.

By default:

```cpp
using StringView = protocyte::Span<const char>;
```

Hosted targets can enable `std::string_view` interoperability:

```cmake
target_compile_definitions(
    demo_proto
    PUBLIC PROTOCYTE_ENABLE_STD_STRING_VIEW=1
)
```

The definition changes public signatures, so all translation units in that target graph must use the same value.

## Enums

Every generated enum has protobuf-like numeric helpers, even when reflection is
disabled:

```cpp
inline constexpr Mode Mode_MIN;
inline constexpr Mode Mode_MAX;
inline constexpr ::protocyte::i32 Mode_ARRAYSIZE;

[[nodiscard]] constexpr bool
Mode_is_valid(::protocyte::i32 value) noexcept;
```

`MIN` and `MAX` directly alias the first declared enum members having the
smallest and largest numeric values, regardless of declaration order.
`ARRAYSIZE` retains protobuf's spelling and means `MAX + 1`; it is not the
number of declared values. It is omitted when `MAX` is `INT32_MAX`.
`is_valid()` accepts declared numbers only, deduplicating aliases.

Helpers for a nested enum are static members of the declaring message:

```cpp
using Color = Paint<>::Color;

static_assert(Paint<>::Color_MIN == Color::COLOR_UNSPECIFIED);
static_assert(Paint<>::Color_is_valid(1));
```

Proto2 enums are closed. Their generated field APIs reject undeclared numeric
values according to the documented closed-enum wire behavior. Proto3 enums are
open and preserve undeclared `int32` values in their raw field surface, while
`is_valid()` still reports only declared values. Protocyte does not emit
protobuf's internal open-enum extrema sentinels.

## Unknown Fields

Unknown-field preservation is disabled by default:

```cpp
struct ForwardCompatibleConfig : protocyte::DefaultConfig {
    static constexpr bool preserve_unknown_fields = true;
};
```

Enabled messages expose:

- `unknown_fields()`;
- `unknown_field_count()`;
- `unknown_field_bytes()`;
- `clear_unknown_fields()`;
- `mutable_unknown_fields()`.

Unknown occurrences retain encounter order as canonical protobuf bytes. Parsing and reserialization do not promise byte-identical forwarding.

The disabled storage specialization adds no message object footprint.

## Reflection

Reflection tables are emitted only when `PROTOCYTE_ENABLE_REFLECTION` is nonzero:

```cmake
target_compile_definitions(
    demo_proto
    PUBLIC PROTOCYTE_ENABLE_REFLECTION=1
)
```

PUBLIC visibility is required so generated sources and consumers see the same declaration surface.

On Windows, `protocyte_add_proto_library(TYPE SHARED)` gives reflection data a target-unique import/export macro. Direct generator users that build a DLL must manage visibility themselves.

Each generated message receives an externally linked `std::array<protocyte::ReflectionFieldInfo, N>` in its package's `protocyte_reflection` namespace.

Reflection builds also add these enum helpers:

```cpp
[[nodiscard]] ::protocyte::StringView Mode_name(Mode value) noexcept;
[[nodiscard]] bool Mode_parse(
    ::protocyte::StringView name,
    Mode& value) noexcept;
[[nodiscard]] const ::protocyte::ReflectionEnumInfo*
Mode_descriptor() noexcept;
```

`name()` returns the first declared name for an aliased number and an empty view
for an unknown value. `parse()` is case-sensitive, accepts every declared alias,
does not allocate, and leaves its output unchanged on failure. The descriptor
preserves declaration order and reports short and protobuf full names,
deprecation state, and whether the enum is closed.

Unlike protobuf `LITE_RUNTIME`, a reflection-disabled Protocyte build
intentionally has no generated enum `name()`, `parse()`, or `descriptor()` API
and contains no enum-name tables.

## Generated Identifier Safety

Legal schema declarations that collide with generated helper names or internal template parameter spellings are remapped deterministically. The protobuf-derived type remains usable without emitting invalid C++.

When comments are enabled, a remapped field emits a nearby comment naming its
protobuf field and generated accessor stem. For example:

```cpp
// Protocyte C++ name mapping: protobuf field "class" uses
// accessor stem "class_protocyte" to avoid a C++ collision.
```

Use the generated declaration as the source of truth for collision-safe
spellings. `comments=off` suppresses these mapping comments together with
schema documentation.

Cross-file collisions that cannot be renamed consistently are rejected. See [Plugin Parameters](https://github.com/anthonyprintup/protocyte/wiki/Plugin-Parameters).

## Related Pages

- [Runtime Reference](https://github.com/anthonyprintup/protocyte/wiki/Runtime-Reference)
- [Embedded and Freestanding](https://github.com/anthonyprintup/protocyte/wiki/Embedded-and-Freestanding)
- [Errors, Limits, and Wire Behavior](https://github.com/anthonyprintup/protocyte/wiki/Errors-Limits-and-Wire-Behavior)
- [Debugging](https://github.com/anthonyprintup/protocyte/wiki/Debugging)
