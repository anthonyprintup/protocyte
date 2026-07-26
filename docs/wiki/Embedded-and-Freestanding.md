# Embedded and Freestanding

Protocyte's generated C++ is designed for environments where exceptions, RTTI, iostreams, the STL, and implicit global allocation are unavailable or undesirable.

The [Getting Started](https://github.com/anthonyprintup/protocyte/wiki/Getting-Started) example uses hosted allocation for convenience. This page explains how to replace it with application-owned policy.

## Runtime Ownership

The default runtime never calls global `malloc` or `new`. Hosted allocation helpers are compiled only when `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR` is nonzero.

`HOSTED_ALLOCATOR` in `protocyte_add_proto_library()` selects the `protocyte::runtime_hosted` target and propagates that definition. Omit it for embedded or kernel targets:

```cmake
protocyte_add_proto_library(
    TARGET device_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
)
```

The generated library then links `protocyte::runtime`. The application supplies a context containing its allocation callbacks and resource limits.

## DefaultConfig Context

`protocyte::DefaultConfig` uses:

```cpp
struct Allocator {
    void *state {};
    void *(*allocate)(void *state, usize size, usize alignment) {};
    void (*deallocate)(void *state, void *ptr, usize size, usize alignment) {};
};

struct Context {
    Allocator allocator;
    Limits limits;
    usize recursion_depth {};
    usize total_allocated_bytes {};
};
```

The callback state is caller-owned. The context, allocator state, and anything referenced by the callbacks must outlive every message and dynamic container bound to that context.

Construct a message without allocating:

```cpp
protocyte::DefaultConfig::Context ctx {
    application_allocator,
    protocyte::Limits {},
};

auto message = device::Packet<>::create(ctx);
```

Primitive scalar setters remain infallible. Operations that allocate or process wire data return `protocyte::Status` or `protocyte::Result<T>`.

## Example Pool Adapter

An allocator can route requests into an arena, pool, kernel heap, or another application facility:

```cpp
struct Pool {
    void *allocate(protocyte::usize size, protocyte::usize alignment) noexcept;
    void deallocate(
        void *ptr,
        protocyte::usize size,
        protocyte::usize alignment
    ) noexcept;
};

void *pool_allocate(
    void *state,
    protocyte::usize size,
    protocyte::usize alignment
) noexcept {
    return static_cast<Pool *>(state)->allocate(size, alignment);
}

void pool_deallocate(
    void *state,
    void *ptr,
    protocyte::usize size,
    protocyte::usize alignment
) noexcept {
    static_cast<Pool *>(state)->deallocate(ptr, size, alignment);
}

protocyte::Allocator allocator_for(Pool &pool) noexcept {
    return {
        .state = &pool,
        .allocate = pool_allocate,
        .deallocate = pool_deallocate,
    };
}
```

If an arena never releases individual allocations, its `deallocate` callback may be null. A finite `max_total_allocation_bytes` then remains charged for the context lifetime because Protocyte cannot observe arena resets.

## Resource Limits

Set application policy before constructing or parsing messages:

```cpp
auto limits = protocyte::Limits {};
limits.max_total_bytes = 64u * 1024u;
limits.max_message_bytes = 16u * 1024u;
limits.max_string_bytes = 4096u;
limits.max_repeated_elements = 1024u;
limits.max_map_entries = 256u;
limits.max_total_allocation_bytes = 32u * 1024u;

protocyte::DefaultConfig::Context ctx {
    allocator_for(pool),
    limits,
};
```

Collection and allocation limits are application security policy and may reject otherwise valid protobuf payloads. See [Errors, Limits, and Wire Behavior](https://github.com/anthonyprintup/protocyte/wiki/Errors-Limits-and-Wire-Behavior).

## Custom Config

Generated messages are templates:

```cpp
template <class Config = ::protocyte::DefaultConfig>
struct Message;
```

A custom config owns these types and hooks:

- `Config::Context`, including allocation and parsing policy;
- `Config::Vector<T>`;
- `Config::Map<K, V>`;
- `Config::Box<T>`;
- `Config::Optional<T>`;
- `Config::Bytes`;
- `Config::String`;
- `Config::allocate(ctx, size, alignment)`;
- `Config::deallocate(ctx, ptr, size, alignment)`;
- hash and equality operations required by maps.

Repeated-field vectors support `reserve`, `push_back`, iteration, `size`, `data`, and `value_type`. Scalar vectors also support:

```cpp
Status append_trivial_range(const T *values, usize count);
Status resize_for_overwrite(usize count);
```

`append_trivial_range` is the bulk commit hook for staged packed values. `resize_for_overwrite` must shrink infallibly so failed fixed-width reads can restore the previous logical size.

Use the built-in runtime containers as the reference contract before replacing them.

## Inline Bounded Storage

The `protocyte.array` schema extension moves supported `bytes` or repeated scalar storage inline:

```proto
import "protocyte/options.proto";

message Digest {
  bytes sha256 = 1 [
    (protocyte.array) = { max: 32, fixed: true }
  ];
}
```

Inline bounded fields do not allocate through `Config`. Fixed byte storage has presence semantics and requires exactly its declared extent when present.

See [Protocyte Extensions](https://github.com/anthonyprintup/protocyte/wiki/Protocyte-Extensions).

## Caller-Controlled Outer Message Storage

Convenience parsing, cloning, and copying can materialize one complete message in automatic storage. Reference-taking variants let the caller choose stack, static, arena, or pool storage:

```cpp
device::Packet<> output {ctx};
protocyte::SliceReader reader {encoded, encoded_size};

if (const auto status = device::Packet<>::parse(reader, output); !status) {
    // output is reset and remains bound to ctx
}
```

Available forms include:

```cpp
Status copy_from(const Message &source, Message &staging_message);
Status clone(Message &output) const;
static Status parse(Reader &reader, Message &output);
```

These forms create no full outer-message temporary internally. Dynamic fields still allocate according to `Config`.

## Reader and Writer Adapters

Custom readers provide:

- `eof()`;
- `position()`;
- `can_read(count)`;
- `read_byte()`;
- `read(out, count)`;
- `skip(count)`.

`position()` is an absolute coordinate in the top-level input. Adapters for subranges must preserve it.

Custom writers provide:

- `can_write(count)`;
- `write_byte(value)`;
- `write(data, count)`.

Use the public `protocyte::ReaderLike` and `protocyte::WriterLike` concepts to validate adapters at generated API boundaries.

## Build Definitions Must Be Consistent

Runtime feature macros change public generated or runtime declarations. Apply them to the generated library with `PUBLIC` visibility so every translation unit sees the same surface:

```cmake
target_compile_definitions(
    device_proto
    PUBLIC PROTOCYTE_ENABLE_REFLECTION=1
)
```

The same consistency rule applies to standard string views and formatting interoperability. See [Runtime Reference](https://github.com/anthonyprintup/protocyte/wiki/Runtime-Reference).

## Kernel Guidance

- Keep `HOSTED_ALLOCATOR` disabled.
- Prefer `protocyte::Span<const char>` over `std::string_view`.
- Use caller-controlled outer-message storage for large schemas.
- Set finite input, collection, recursion, and allocation limits.
- Treat every `Status` and `Result<T>` as `[[nodiscard]]`.
- Keep host code generation outside the target toolchain.
- Exercise malformed input and allocation-failure paths with the production config.

## Related Pages

- [Generated C++ API](https://github.com/anthonyprintup/protocyte/wiki/Generated-Cpp-API)
- [Runtime Reference](https://github.com/anthonyprintup/protocyte/wiki/Runtime-Reference)
- [Errors, Limits, and Wire Behavior](https://github.com/anthonyprintup/protocyte/wiki/Errors-Limits-and-Wire-Behavior)
- [Compatibility and Limitations](https://github.com/anthonyprintup/protocyte/wiki/Compatibility-and-Limitations)
