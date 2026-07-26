# Compatibility and Limitations

Protocyte targets protobuf message schemas and advertises
`FEATURE_PROTO3_OPTIONAL`.

## Supported schema features

- messages and enums, including nested declarations;
- all protobuf scalar field types;
- `string`, `bytes`, message, `oneof`, and optional fields;
- repeated fields and packed repeated scalars;
- maps and recursive message fields;
- normal proto2 optional, required, repeated, default, enum, string, bytes,
  message, map, and oneof codecs;
- runtime emission and optional debug reflection metadata.

Generated messages provide fallible parse, serialize, deep-copy, and clone
operations. The wire format is protobuf-compatible within the supported
feature set.

## Current limitations

- Protobuf Editions are rejected in V1.
- Generated proto2 extension fields are not supported.
- Groups are not supported.
- `protocyte.array` cannot be applied to map fields.
- Services and methods may appear in descriptor graphs but do not generate RPC
  stubs.
- C++ name collisions between separately generated headers are rejected.
  Protocyte remaps representable collisions within one `.proto` file, but does
  not rename colliding cross-file types, package constants, reflection
  symbols, or package namespaces.
- The generated/runtime API requires C++20.
- The generator requires Python 3.12 or newer.
- The checked CMake integration requires CMake 3.24 or newer.

## Wire and resource compatibility

Default total-byte and unknown-field limits preserve protobuf's sub-2-GiB
envelope, and the default recursion limit is 100. Application-selected
collection, message, string, unknown-field, and allocation budgets may
intentionally reject otherwise valid protobuf input.

Unknown-field preservation is disabled by default and canonicalizes tags and
scalar values when enabled. It preserves semantic occurrences, not necessarily
byte-identical forwarding.

See [Errors, Limits, and Wire Behavior](Errors-Limits-and-Wire-Behavior) for
the detailed contracts.

## Version compatibility

Protocyte is pre-1.0. Generated C++ APIs, runtime configuration requirements,
plugin parameters, and CMake interfaces may change between releases without
migration shims. Pin a reviewed immutable version and regenerate checked
outputs when updating.

No release tag or downloadable asset should be assumed to exist until it
appears on the [GitHub releases
page](https://github.com/anthonyprintup/protocyte/releases). Before the first
release, use a source checkout or the reviewed full commit SHA shown in
[FetchContent](FetchContent).
