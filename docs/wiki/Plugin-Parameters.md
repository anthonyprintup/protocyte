# Plugin Parameters

Protocyte plugin parameters are exact and case-sensitive. Unknown names,
duplicate names, aliases, and bare tokens without `=` are errors.

## Parameters

- `runtime=emit` emits `runtime.hpp` under `protocyte/runtime`.
- `runtime=emit:<prefix>` emits it under a custom virtual prefix.
- `runtime=omit` omits runtime files.
- `runtime_prefix=<path>` selects the runtime include prefix and, when runtime
  emission is enabled, the output directory.
- `namespace_prefix=<a::b>` wraps generated package namespaces.
- `include_prefix=<path>` prefixes includes for imported generated headers.
- `comments=on|off` controls schema comments as Doxygen documentation. The
  default is `on`; protobuf deprecation options still produce
  `[[deprecated]]`.
- `format=auto|off|required` controls formatting. `auto` is the default and
  formats when `clang-format` is available. `required` fails when no formatter
  is available.
- `clang_format=<executable-or-path>` selects one formatter executable. The
  value is executed directly, never through a shell, and must not include
  command-line arguments.
- `clang_format_config=<path>` selects an explicit configuration. Either
  explicit formatter parameter implies `format=required`; neither may be
  combined with `format=off`.
- `formatter_timeout_seconds=<seconds>` sets the per-file command-line
  formatter timeout. The default is `60`; `0` disables only this timeout.

Runtime and include prefixes are protobuf virtual directories, not filesystem
paths. They must be normalized relative paths using `/`. Protocyte rejects
absolute or drive-rooted paths, backslashes, control characters, empty
segments, `.` and `..`, segment-edge whitespace, include delimiters, CMake list
separators, Windows-reserved characters, and Windows device names.

Names beginning with `_protocyte_` are reserved for CMake transport.
`namespace_prefix` must be a normalized `::`-separated namespace of portable,
non-reserved C++ identifiers. `std` and `protocyte` are valid components, but
keywords, leading underscores, empty components, non-ASCII identifiers, and
extra colons are rejected.

## CMake and direct `protoc`

CMake callers pass non-runtime parameters through `OPTIONS`, always as
`key=value`. Use `EMIT_RUNTIME`, `RUNTIME_PREFIX`, `NAMESPACE_PREFIX`, and
`INCLUDE_PREFIX` for values that have dedicated CMake arguments.

```cmake
protocyte_add_proto_library(
    TARGET demo_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    OPTIONS
        "comments=off"
        "formatter_timeout_seconds=180"
)
```

Direct callers should keep options separate from the output directory:

```powershell
protoc `
  --proto_path=. `
  --proto_path=src/protocyte/proto `
  --protocyte_out=out `
  --protocyte_opt=runtime=emit:vendor/protocyte,namespace_prefix=mycorp::wire,include_prefix=generated `
  tests/example.proto
```

```bash
protoc \
  --proto_path=. \
  --proto_path=src/protocyte/proto \
  --protocyte_out=out \
  --protocyte_opt=runtime=emit:vendor/protocyte,namespace_prefix=mycorp::wire,include_prefix=generated \
  tests/example.proto
```

The first `:` in combined `--protocyte_out=<parameters>:<directory>` syntax is
a separator, so that form misparses colon-valued parameters.

## Generated C++ identifier mapping

Protocyte allocates emitted names deterministically by C++ scope and symbol
kind, independent of descriptor declaration order. Type names preserve
descriptor case. Nested types use `Parent_Child`. A real within-file collision
receives a stable suffix based on its full protobuf name; cross-file collisions
are rejected.

C++ keywords normally receive a trailing underscore. Field and oneof stems use
`protocyte` suffixes where an underscore would create a reserved derived name.
Leading or double underscores, predefined-macro-like names, raw
`protocyte_escaped_` prefixes, impersonated keyword escapes, and invalid option
constant spellings are encoded as `protocyte_escaped_<utf8-hex>`.

Generated-helper collisions are resolved by symbol kind. Overload-compatible
accessors such as parameterized `serialize`, `parse`, and `copy_from` may retain
their source spelling. Nullary helper collisions are escaped as one accessor
group. Generator-owned storage, oneof state, temporaries, and template
parameters move around schema-owned names and are never emitted as reserved
C++ identifiers.

There are no alternate compatibility spellings: `message payload` defines
`payload`, not an additional `Payload`.

## Formatting and reproducibility

With `format=auto`, implicit style discovery starts in the plugin invocation
directory and is delegated to `clang-format --style=file`. CMake preserves the
directory containing the calling `CMakeLists.txt`; direct callers should invoke
the plugin from their project or pass `clang_format_config`.

`auto` is not a byte-for-byte reproducibility guarantee across machines or
formatter versions. Repositories that check generated files in should use
`format=off`, or pin a formatter and configuration with `format=required`.

## Generator trust boundary

The command-line plugin is designed for trusted local build configuration.
`clang_format` and `clang_format_config` select developer-controlled executable
and configuration paths. Do not forward tenant-controlled values unchanged.

Embedding services can supply an operator-owned policy:

```python
from protocyte.plugin import GeneratorPolicy, generate_response

policy = GeneratorPolicy(
    allow_formatter_parameters=False,
    format_outputs=False,
    max_request_bytes=4 * 1024 * 1024,
    max_files_to_generate=256,
    max_proto_files=1_024,
    max_descriptor_nodes=50_000,
    max_descriptor_metadata_bytes=4 * 1024 * 1024,
    max_nesting_depth=64,
    max_generated_bytes=64 * 1024 * 1024,
)
response = generate_response(request, policy=policy)
```

`GeneratorPolicy()` itself preserves the embedding API's opt-in behavior:
budgets and timeout are unset, formatter parameters are allowed, and formatting
is enabled. An embedding service must pass its explicit policy. The transport
must cap input bytes before parsing.

Before model construction, `generate_response()` validates structural
descriptor invariants. Metadata limits include source locations, paths,
comments, dependencies, and unknown descriptor fields. Generated-byte limits
are cumulative across rendered source and formatter streams. Run untrusted
generation in a constrained worker with overall time and memory limits, and
keep formatter parameters disabled.

## Related pages

- [Code Generation](Code-Generation)
- [CMake API Reference](CMake-API-Reference)
- [Compatibility and Limitations](Compatibility-and-Limitations)
