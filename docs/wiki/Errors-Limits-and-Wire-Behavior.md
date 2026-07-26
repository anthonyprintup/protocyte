# Errors, Limits, and Wire Behavior

Protocyte reports failures without exceptions, allocation-backed messages, or required reflection.

## Error Diagnostics

```cpp
struct Error {
    ErrorCode code {};
    usize offset {};
    u32 field_number {};
};
```

Both `Status` and `Result<T>` expose `.error()` after a false status check:

```cpp
const auto parsed = demo::Sample<>::parse(ctx, encoded);
if (!parsed) {
    const auto &error = parsed.error();
    report(error.code, error.offset, error.field_number);
}
```

- `code` identifies the failure category.
- `offset` is an absolute top-level reader or writer coordinate. It is zero when no meaningful I/O position exists.
- `field_number` identifies the public field whose operation returned the failure. It is zero when no message field is known.

Nested failures are contained by their outer public field. Map-entry failures identify the map field rather than synthetic entry fields.

No field names, nested paths, source names, or formatted strings are stored in `Error`.

## Resource Limits

`protocyte::Limits` separates protobuf wire compatibility from application policy:

| Limit | Default and behavior |
|---|---|
| `max_total_bytes` | `0x7fffffff`; bounds all bytes read or skipped by one top-level parse or merge |
| `max_recursion_depth` | `100`; matches protobuf C++ |
| `max_message_bytes` | `0x7fffffff`; bounds one embedded message |
| `max_string_bytes` | `0x7fffffff`; bounds dynamically stored string and bytes values |
| `max_unknown_field_bytes` | `0x7fffffff`; bounds canonical unknown bytes stored by one message |
| `max_repeated_elements` | `0x7fffffff`; counts decoded repeated occurrences across the top-level operation |
| `max_map_entries` | `0x7fffffff`; counts decoded entries across the top-level operation |
| `max_total_allocation_bytes` | Unbounded for `DefaultConfig`; caps live allocator-requested bytes when finite |

Packed chunks, nested messages, and duplicate map keys share their applicable top-level count budgets.

Reallocation peaks charge the new block before releasing the old one. Contexts without a deallocation callback retain charged bytes because the runtime cannot observe arena reclamation.

Limit failures return `size_limit` or `count_limit`; allocation-budget exhaustion returns `no_memory`.

## Parse Atomicity

`merge_from(reader)` commits successfully parsed field occurrences. It is not whole-message transactional.

The failing occurrence does not change visible state:

- a singular message occurrence is merged into staged state and committed only after it parses;
- a oneof switches cases only after the incoming value parses;
- repeated and map fields commit only complete elements or entries;
- malformed packed payloads append no decoded prefix;
- staged bounded bytes do not replace the visible value after a short read.

Fields committed before a later failure remain committed.

For whole-message replacement, use `parse(reader, output)`. It resets and fills the caller-owned output and leaves it empty on failure.

## Serialization Atomicity

`serialize(output_bytes)` computes the encoded size before writing. If the contiguous buffer is too small, it returns `size_limit` without modifying the buffer.

`serialize(writer)` validates the message first but writes incrementally. A failure after writing begins does not rewind a custom writer.

Use a staging buffer or a transactional writer when publication must be all-or-nothing.

## Unknown Fields

Preservation is compile-time configurable and disabled by default:

```cpp
struct ForwardCompatibleConfig : protocyte::DefaultConfig {
    static constexpr bool preserve_unknown_fields = true;
};

using Sample = demo::Sample<ForwardCompatibleConfig>;
```

Enabled messages retain unknown occurrences in encounter order as canonical protobuf wire bytes and expose:

```cpp
for (const auto field : message.unknown_fields()) {
    if (field.wire_type() == protocyte::WireType::VARINT) {
        const auto value = field.varint();
    }
}
```

Views provide field number, wire type, tag, protobuf-style type, and typed accessors for varint, fixed, length-delimited, and group payloads.

`mutable_unknown_fields()` provides typed add, replace, erase, subrange deletion, number-based deletion, merge, and clear operations. Writable raw storage is not exposed.

Mutations roll back on allocation, input, recursion, or size-limit failure. Added raw encoded ranges are validated and canonicalized before commit.

Unknown fields serialize after known fields. Encounter order is retained, but canonical tag and scalar encoding means forwarding is not byte-identical.

Unknown data inside map-entry messages is normally discarded while the known key/value is materialized. An undeclared closed-enum map value preserves the complete outer map occurrence as unknown instead of inserting the entry.

The default disabled storage uses `PROTOCYTE_NO_UNIQUE_ADDRESS`, so it adds no message object footprint.

## Reader Coordinates

Readers passed to generated APIs provide:

```text
eof()
position()
can_read(count)
read_byte()
read(out, count)
skip(count)
```

`position()` is absolute in the top-level input. `SliceReader(data, size, base_offset)` can establish an absolute source base for a subrange.

`ReaderRef`, `ParseBudgetReader`, `LimitedReader`, and staged map readers preserve the wrapped coordinate. This makes nested `Error::offset` values meaningful to the outer caller.

## Repeated and Map Budgets

Nested parse readers expose:

```text
consume_repeated_elements(count, field_number)
consume_map_entries(count, field_number)
```

`ParseBudgetReader` owns the counters. Reader wrappers forward them so nested messages share the top-level budget.

## String Views

Generated immutable string accessors return `protocyte::Span<const char>` by default. This avoids standard-library APIs whose contracts can throw.

Hosted users can opt into `std::string_view`:

```cmake
target_compile_definitions(demo_proto PUBLIC PROTOCYTE_ENABLE_STD_STRING_VIEW=1)
```

Apply the definition to the target that compiles the generated sources and propagate it to every consumer. `PROTOCYTE_ENABLE_STD_STRING_VIEW` changes the public `protocyte::StringView` type, so all translation units in that target graph must compile with the same value.

When enabled:

- the runtime includes `<string_view>`;
- Protocyte spans and strings convert to `std::string_view`;
- generated immutable string accessors return `std::string_view`.

Keep the default span API in kernel and freestanding builds.

## String Formatting

Formatting interoperability is disabled by default and is unrelated to generator source formatting.

Enable standard C++ formatting:

```cmake
target_compile_definitions(demo_proto PUBLIC PROTOCYTE_ENABLE_STD_FORMAT=1)
```

When the standard library advertises C++20 formatting support, Protocyte supplies a `std::formatter` for `protocyte::String<Config>`.

Enable `{fmt}` interoperability:

```cmake
target_compile_definitions(demo_proto PUBLIC PROTOCYTE_ENABLE_FMT_FORMAT=1)
```

This supplies `format_as()` returning `std::string_view`. Protocyte does not provide or link `{fmt}`.

Propagate either macro consistently to formatting consumers.

## Wire Compatibility

Protocyte follows protobuf wire behavior for supported messages:

- scalar tags and values use canonical encoding when serialized;
- singular message occurrences merge;
- repeated packed and unpacked scalar forms are accepted where protobuf permits them;
- unknown wire fields can be skipped or preserved;
- duplicate map keys use normal map materialization behavior;
- invalid, truncated, overlong, or limit-exceeding input returns a structured failure.

Application limits may intentionally reject otherwise wire-valid protobuf messages.

## Processing Untrusted Input

For attacker-controlled payloads:

1. set finite total-byte and recursion limits;
2. set finite string, message, repeated, and map limits;
3. set a finite allocation budget;
4. decide explicitly whether unknown fields should be preserved;
5. use caller-owned output when stack size matters;
6. check every returned status;
7. test malformed packed, nested, map, oneof, and bounded-byte cases.

## Related Pages

- [Generated C++ API](https://github.com/anthonyprintup/protocyte/wiki/Generated-Cpp-API)
- [Runtime Reference](https://github.com/anthonyprintup/protocyte/wiki/Runtime-Reference)
- [Embedded and Freestanding](https://github.com/anthonyprintup/protocyte/wiki/Embedded-and-Freestanding)
- [Compatibility and Limitations](https://github.com/anthonyprintup/protocyte/wiki/Compatibility-and-Limitations)
