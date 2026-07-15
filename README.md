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

Protocyte currently targets protobuf message schemas, advertises
`FEATURE_PROTO3_OPTIONAL` for proto3 optional fields, and supports the proto2
message-codec subset listed below.

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

- `proto2` message codecs support normal optional, required, repeated, default,
  enum, string, bytes, message, map, and oneof field generation, but generated
  extension fields are not supported.
- Protobuf Editions are rejected in v1.
- Groups are not supported.
- `protocyte.array` cannot be applied to map fields.
- Services and methods are accepted in descriptor graphs but do not generate
  RPC stubs.

Protocyte is pre-1.0. Generated C++ APIs, runtime config requirements, plugin
parameters, and CMake interfaces may change between releases without
compatibility aliases or migration shims. Pin the intended Protocyte version
and regenerate checked outputs when updating.

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
[tests/smoke/README.md](tests/smoke/README.md).

Generate code:

```powershell
protoc `
  --proto_path=. `
  --proto_path=src/protocyte/proto `
  --protocyte_out=runtime=emit:generated `
  tests/example.proto
```

The plugin emits:

- `foo.protocyte.hpp`
- `foo.protocyte.cpp`
- `protocyte/runtime/runtime.hpp` when runtime emission is enabled

Generate from a descriptor set when `.proto` source is not the authority:

```powershell
protoc `
  --descriptor_set_in=descriptor_set.pb `
  --plugin=protoc-gen-protocyte=path\to\protoc-gen-protocyte `
  --protocyte_out=generated `
  core.proto messages.proto settings.proto
```

The names after `--protocyte_out` are descriptor names inside
`descriptor_set.pb`, not filesystem paths. Imported descriptors from the set are
available for type and custom-option resolution, but Protocyte only emits files
listed for generation.

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
    ALIAS demo::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE demo::proto)
```

Non-runtime generator options can be forwarded through `OPTIONS`:

```cmake
protocyte_add_proto_library(
    TARGET demo_proto
    ALIAS demo::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    DISCOVER
    OPTIONS
        "clang_format=C:/Program Files/LLVM/bin/clang-format.exe"
        "clang_format_config=${CMAKE_SOURCE_DIR}/.clang-format"
)
```

Descriptor-set inputs use the same target-oriented API. In this mode `PROTOS`
are virtual descriptor names inside the set and `PROTO_ROOT` is omitted:

```cmake
protocyte_add_proto_library(
    TARGET recovered_proto
    ALIAS recovered::proto
    DESCRIPTOR_SET "${CMAKE_CURRENT_BINARY_DIR}/descriptor_set.pb"
    PROTOS
        core.proto
        messages.proto
        settings.proto
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    HOSTED_ALLOCATOR
)
```

The convenience wrapper is equivalent and names the descriptor-set intent more
directly:

```cmake
protocyte_add_descriptor_set_library(
    TARGET recovered_proto
    ALIAS recovered::proto
    DESCRIPTOR_SET "${CMAKE_CURRENT_BINARY_DIR}/descriptor_set.pb"
    FILES core.proto messages.proto settings.proto
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    HOSTED_ALLOCATOR
)
```

`DISCOVER` is available for descriptor sets and generates every non-runtime
descriptor by default. `google/protobuf/*.proto` descriptors are kept for
option/type resolution; unreferenced runtime descriptors stay dependency-only,
while referenced runtime message/enum descriptors are generated when selected
files need their generated types.

Formatter executable and config values in `OPTIONS` may use absolute Windows
or POSIX paths. Generated include and runtime prefixes are not filesystem paths;
they must use the normalized relative virtual-directory form documented below.

By default, the protocyte CMake project fetches protobuf when protobuf CMake
targets are not already available, then exposes:

- `protocyte_add_proto_library(...)` for the common target-oriented workflow
- `protocyte_generate(...)` as the lower-level codegen primitive
- `protocyte::runtime` and `protocyte::runtime_hosted` for reusable runtime linkage

The fallback protobuf revision is the exact commit recorded in
`PROTOCYTE_PROTOBUF_GIT_TAG`, rather than a mutable branch or release tag.

`TARGET` must be a real CMake target name without `::`. `ALIAS` can use any
valid alias target name; namespaced aliases like `demo::proto` are recommended
for downstream linkage.

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
    ALIAS demo::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(demo main.cpp)
target_link_libraries(demo PRIVATE demo::proto)
```

Configure the consumer with `-DCMAKE_PREFIX_PATH=<prefix>` so CMake can find
`protocyteConfig.cmake`.

Final-release CMake package versions accept only exact version requests.
Prerelease package versions intentionally reject versioned `find_package`
requests; pin the prerelease prefix itself and use the unversioned
`find_package(protocyte CONFIG REQUIRED)` form shown above.

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
generated translation units, are in [tests/smoke/README.md](tests/smoke/README.md),
[tests/fetchcontent/CMakeLists.txt](tests/fetchcontent/CMakeLists.txt), and
[tests/find_package/CMakeLists.txt](tests/find_package/CMakeLists.txt).

Descriptor-set mode intentionally does not require a protobuf include tree for
descriptors already present in the set. Source-mode generation still uses
`PROTO_ROOT`/`IMPORT_DIRS` and still needs import roots for source parsing.

## Debugging

LLDB formatters for Protocyte runtime and generated message types are documented
in [docs/debugger.md](docs/debugger.md).

## Plugin Parameters

Supported `--protocyte_out=` parameters:

- `runtime=emit`: emit `runtime.hpp` under `protocyte/runtime`.
- `runtime=emit:<prefix>`: emit `runtime.hpp` under a custom prefix.
- `runtime=omit`: do not emit runtime files.
- `runtime_prefix=<path>`: set the runtime header include prefix and, when
  runtime emission is enabled, its output directory.
- `namespace_prefix=<a::b>`: prepend additional C++ namespaces around the file
  package namespace.
- `include_prefix=<path>`: prefix includes for imported generated headers.
- `clang_format=<executable-or-path>`: run an explicit `clang-format`
  executable after generation. The value is passed as one executable argument,
  not interpreted by a shell; do not append command-line options. When
  specified, launch and formatting failures are reported as plugin errors.
- `clang_format_config=<path>`: use an explicit clang-format config file when
  formatting runs.

Runtime and include prefixes are portable protobuf virtual directories, not
filesystem paths. They must be normalized relative paths using `/`; absolute or
drive-rooted paths, backslashes, control characters, empty segments, `.` and
`..` segments, and leading or trailing segment whitespace are rejected. The
same validation is applied by the CMake helpers before generated outputs are
declared.

Parameter names are exact and case-sensitive. Unknown names, duplicate names,
and bare tokens without `=` are errors; aliases are not accepted.
Names beginning with `_protocyte_` are reserved for CMake's parameter transport
and must not be supplied through CMake `OPTIONS`.
`namespace_prefix` must be a normalized `::`-separated namespace with no empty
components, extra colons, surrounding component whitespace, or control
characters.

Formatting is best-effort by default. If `clang-format` is on `PATH`, protocyte
uses it for generated C++ output. If it is not available and no explicit
`clang_format=...` override is supplied, protocyte still emits generated files
without failing.

CMake users can forward non-runtime parameters through the existing `OPTIONS`
argument on `protocyte_generate(...)` or `protocyte_add_proto_library(...)`.
Absolute Windows and POSIX formatter paths are safe in `OPTIONS`; include
prefixes remain relative virtual directories. Runtime state is the exception:
use the dedicated `EMIT_RUNTIME` and `RUNTIME_PREFIX` arguments so CMake can
declare the emitted runtime header and runtime linkage consistently. Forwarded
`runtime` and `runtime_prefix` parameters are rejected.

Example:

```powershell
protoc `
  --proto_path=. `
  --proto_path=src/protocyte/proto `
  --protocyte_out=runtime=emit:vendor/protocyte,namespace_prefix=mycorp::wire,include_prefix=generated:out `
  tests/example.proto
```

### Generator trust boundary

The `protoc-gen-protocyte` command-line plugin is designed for trusted local
build configuration. In particular, `clang_format` and `clang_format_config`
select developer-controlled executable and configuration paths. Do not forward
tenant-controlled plugin parameters to that entry point unchanged.

Services that embed the Python API can supply an operator-owned
`GeneratorPolicy` without changing normal local generation:

```python
from protocyte.plugin import GeneratorPolicy, generate_response

policy = GeneratorPolicy(
    allow_formatter_parameters=False,
    format_outputs=False,
    max_request_bytes=4 * 1024 * 1024,
    max_files_to_generate=256,
    max_proto_files=1_024,
    max_descriptor_nodes=50_000,
    max_nesting_depth=64,
    max_generated_bytes=64 * 1024 * 1024,
)
response = generate_response(request, policy=policy)
```

`GeneratorPolicy()` preserves normal local plugin behavior: its resource
budgets are unset, formatter parameters are allowed, and output formatting is
enabled. An embedding service must pass its own explicit policy; merely calling
`generate_response()` does not opt into the example limits above.

The values above are an example deployment profile, not protobuf format
limits. Choose budgets for the service workload. `max_request_bytes` is checked
on the parsed request, so the transport must also cap bytes before parsing.
`max_generated_bytes` is enforced cumulatively while generated source lines are
appended and while formatter stdout and stderr are streamed. Formatter capture
uses the remaining cumulative byte budget and terminates the process before
retaining output beyond it. A single descriptor operation, rendered file, or
formatter input encoding can still require additional transient memory. Run
untrusted generation in a constrained worker with overall time and memory
limits. If formatting is enabled, `formatter_timeout_seconds` applies to each
generated file; keep `allow_formatter_parameters=False` so the executable
remains operator-selected from the worker environment.

## Protocyte Extensions

Protocyte ships custom protobuf options in
[src/protocyte/proto/protocyte/options.proto](src/protocyte/proto/protocyte/options.proto).

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
- Bitwise operators: `~`, `&`, `^`, `|`, `<<`, `>>`
- Comparisons: `<`, `<=`, `>`, `>=`
- Equality: `==`, `!=`
- Boolean operators: `!`, `&&`, `||`
- String concatenation: `+`
- String helpers: `len(...)`, `substr(...)`, `starts_with(...)`
- Scalar casts: `bool(...)`, `i32(...)`, `u32(...)`, `i64(...)`, `u64(...)`,
  `f32(...)`, `f64(...)`, `str(...)`
- Math functions: `pow(...)`, `abs(...)`, `min(...)`, `max(...)`, `sqrt(...)`,
  `exp(...)`, `log(...)`, `log2(...)`, `log10(...)`, `ceil(...)`, `floor(...)`,
  `trunc(...)`, `round(...)`

#### Expression And Constant Resolution Limits

Protocyte bounds generator-side recursion along two dimensions:

- Expression syntax may be nested to at most 32 levels. Parenthesized
  subexpressions, unary-operator operands, and nested function-argument
  expressions contribute to that depth. The boundary is accepted; entering a
  33rd level rejects the expression with a labeled
  `expression nesting exceeds maximum depth of 32` error.
- A constant dependency chain may contain at most 32 constants, including the
  constant where resolution begins. This applies to message and package
  constants, including chains reached from `array.expr`, and is independent of
  constant declaration order. The boundary is accepted; resolving a 33rd
  constant rejects the model with a labeled
  `constant dependency nesting exceeds maximum depth of 32` error.

The two boundaries may be used together. Residual host recursion exhaustion is
also translated to a labeled `expression evaluation exceeds safe recursion
depth` error. All three failures are normal `ProtocyteError` generator
diagnostics; the plugin returns the diagnostic without emitting partial
generated files.

#### Numeric Literals And Conversions

Integer literals may be decimal or hexadecimal with a `0x` or `0X` prefix;
hexadecimal digits are case-insensitive. Bare integer literals are typed before
and independently of the expression destination, following the fixed-width
equivalent of the standard C++ unsuffixed candidate order. Decimal literals use
`i32` and then `i64`; a decimal value greater than `INT64_MAX` is rejected
instead of being inferred as `u64`. Hexadecimal literals use `i32`, `u32`,
`i64`, then `u64`, so `0xffffffff` is a `u32` value. Referenced constants retain
their declared kind, and bare floating-point literals, including exponent
notation, are `f64`. As in C++, a leading sign is a unary operator rather than
part of the literal, so `-2147483648` has `i64` kind; use `i32(-2147483648)`
when the intermediate must be `i32`.

The destination converts only the completed expression; it never changes the
types of literals or intermediate operations. Use an explicit cast when an
intermediate must have a particular width or signedness, for example
`u64(1) << 40`.

Bool operands promote to `i32` for every numeric or integral operator,
including unary arithmetic, ordering, and mixed bool/numeric equality. Binary
numeric arithmetic, ordering, equality, and non-shift bitwise operators then
convert their operands to one common kind: `f64` wins over every other kind,
then `f32`, then the C++ usual signed/unsigned integer conversion result. For
example, `true + true` is the `i32` value `2`, `true == 1` is true,
`i32(-1) == u32(0xFFFFFFFF)` is true after both operands convert to `u32`, and
`i64(-1) < u32(0)` remains true because every `u32` value fits in `i64`. Every
`f32` operation is rounded to binary32 before a containing operation uses it.

Unsigned arithmetic wraps to its selected width. Signed overflow and the
unrepresentable signed `MIN / -1` and `MIN % -1` cases are rejected. Signed
division truncates toward zero and signed remainder has the dividend's sign,
matching C++ integer semantics. `%` and bitwise operators reject floating-point
operands.

#### Scalar Casts

Scalar casts are generator-side functions that require exactly one argument.
Because literals and operations do not inherit the expression destination's
kind, an explicit cast is the way to select a width or signedness for an
intermediate. For example, `u64(1) << 40` performs a 64-bit shift and
`u32(-1) + 1` performs unsigned 32-bit arithmetic. Referenced constants retain
and convert from their declared kind.

| Cast | Accepted source | Result |
| --- | --- | --- |
| `bool(value)` | Bool or numeric | `false` for zero, including either floating signed zero; `true` for every other finite numeric value. |
| `i32(value)`, `u32(value)`, `i64(value)`, `u64(value)` | Bool or numeric | Bool becomes `0` or `1`. Integer conversion uses the target-width C++ modulo/two's-complement result. Floating conversion truncates toward zero and then requires the result to fit the target range. |
| `f32(value)` | Bool or numeric | Converts to finite binary32 and rounds immediately before reuse. |
| `f64(value)` | Bool or numeric | Converts to finite binary64. |
| `str(value)` | Any scalar | Leaves strings unchanged; formats bool as `true` or `false`, integers in decimal, `f32` with up to 9 significant digits, and `f64` with up to 17 significant digits. Integral-looking floating values retain a floating marker such as `.0`, and signed zero formats as `-0.0`. |

String conversion is deliberately one-way: numeric and bool casts do not parse
strings. Use expression operations or typed constants to produce a numeric or
bool source before casting it.

#### String Helpers

Generator-side strings are Unicode values. `len(value)` returns a `u32` count
of Unicode code points, and `substr(value, start, count)` interprets `start` and
`count` as Unicode code-point indices. This intentionally differs from the
generated C++ `StringView`: generated strings contain UTF-8, so its `size()` and
indexing are byte-oriented. For example, expression `len("\u00e9")` is `1`,
while the generated view contains two UTF-8 bytes. Do not reuse a generator-side
`substr` index as a runtime byte offset without converting it to a UTF-8 byte
offset. `starts_with(value, prefix)` compares the generator-side Unicode
strings.

#### Math Functions

Math functions are evaluated by the generator and emitted as final typed
literals; they do not add generated runtime dependencies. Numeric arguments
preserve their declared `i32`, `u32`, `i64`, `u64`, `f32`, or `f64` kind.
Booleans passed to math functions promote to signed `i32` values. Except for
`pow`, mixed arguments promote to `f64` when present, then `f32`, then the C++
usual integer conversion result.

| Function | Arguments | Result and restrictions |
| --- | --- | --- |
| `pow(base, exponent)` | Exactly two numeric values | Converts both arguments to `f64` and always returns `f64`. This is a uniform Protocyte rule: unlike the dedicated C++ `std::pow(float, float)` overload, two `f32` arguments do not produce `f32`. Negative exponents produce reciprocal powers. A negative base with a non-integral exponent and zero with a negative exponent are domain errors; zero to zero is `1`. Non-finite results are rejected. There is no signed checked or unsigned modular integer-power mode. |
| `abs(value)` | One numeric value | Preserves the promoted input kind. Signed minimum values are rejected; unsigned values are unchanged and floating negative zero becomes positive zero. |
| `min(...)`, `max(...)` | At least two numeric values | Convert every argument to one common kind and return that kind. The first argument wins a tie, including signed-zero ties. |
| `sqrt`, `exp`, `log`, `log2`, `log10` | One numeric value | `f32` returns `f32`; every other non-`f32` numeric kind returns `f64`. Square root rejects negative values, logarithms reject zero and negative values, and all non-finite results are rejected. |
| `ceil`, `floor`, `trunc`, `round` | One numeric value | `f32` returns `f32`; every other non-`f32` numeric kind returns `f64`. `round` uses halfway-away-from-zero behavior like `std::round`; signed zero is preserved where the corresponding C++ operation preserves it. |

`pow` does not perform integral exponentiation: `pow(2, -3)` is the `f64` value
`0.125`, and `pow(2, 63)` is evaluated and returned as `f64` regardless of the
destination. Use an explicit cast if the final floating result must be
converted to an integer.

`pow`, `sqrt`, `exp`, `log`, `log2`, and `log10` use Protocyte's
dependency-free deterministic math backend rather than the host's `libm`.
After the function's type promotion, the backend converts each resulting
binary32 or binary64 input exactly to a decimal value. It evaluates the
operation in a 160-digit decimal context using round-to-nearest, ties-to-even.
`sqrt`, `exp`, `log`, and `log10` use the corresponding decimal primitive;
`log2(x)` is `ln(x) / ln(2)`. Before using decimal transcendental operations,
`pow` evaluates integral exponents as an exact rational whenever a conservative
bound keeps both powered operands within 4096 bits. Exact power-of-two bases
also use a constant-space direct binary path whenever multiplying the base's
binary exponent by the supplied exponent produces an integer. These exact
paths round the resulting ratio or power of two directly to binary64, including
subnormal halfway cases. Other powers use `exp(y * ln(abs(x)))` with the
real-domain checks and result sign applied separately. Each decimal primitive
and arithmetic step rounds in the 160-digit context. The backend then converts
the decimal result directly to IEEE-754 binary32 or binary64 with
round-to-nearest, ties-to-even. This defines stable generator behavior but does
not promise bit-for-bit agreement with a target C++ CRT; edge cases may differ
from the MSVC, clang, or platform `<cmath>` implementation. Domain and
non-finite checks still apply before a literal is emitted.

All numeric expressions must remain finite. Floating signed zero is preserved
except where a function specifies otherwise: `abs(-0.0)` returns positive
zero, `min` and `max` retain the first converted operand on a zero tie, and
`ceil`, `floor`, `trunc`, and `round` preserve the operand's sign when their
result is zero.

When a floating result is assigned to an integer expression destination, it is
truncated toward zero before the destination range check (`2.9` becomes `2`,
and `-2.9` becomes `-2`). Explicit floating-to-integer casts use the same
truncation rule. Floating results are not implicitly accepted by
`boolean_expr`. Integer source kinds are validated before destination
conversion, and a completed value outside the destination range is rejected.

#### Bitwise And Shift Operators

Bitwise operators use fixed-width `i32`, `u32`, `i64`, or `u64` evaluation.
Mixed operands use the C++ usual integer conversions described above. Boolean
operands are promoted to signed `i32` values (`false` to `0`, `true` to `1`);
floating-point and string values are not valid bitwise operands.

Shifts follow C++'s per-operand conversion model rather than converting both
operands to a common kind. Each operand is first normalized in its own source
kind, bool promotes to `i32`, and the result keeps the left operand's kind and
width. Consequently, negating an unsigned shift count wraps in that unsigned
kind before validation. The normalized count must be nonnegative and smaller
than the left operand's width.

Left shifts use C++20 width-modulo behavior for both signed and unsigned left
operands: bits shifted beyond the left operand's width are discarded, and a
signed result is interpreted in that same signed kind. For example, `i32(1) <<
31` is `INT32_MIN`, while `i32(-1) << 1` is `-2`. Unsigned right shifts are
logical and signed right shifts are arithmetic.

#### Logical Operators

Logical operators accept bool and finite numeric operands and use zero/nonzero
conversion, matching C++ contextual conversion to bool. `&&` and `||` evaluate
left to right and genuinely short-circuit value evaluation of an unreachable
right operand. The skipped operand is still parsed, names are resolved, and its
arity and types are validated. Thus `false && (1 / 0 > 0)` is `false`, while
`false && "not numeric"` remains a type error.

A `boolean_expr` may likewise resolve to bool or integer, with zero emitted as
`false` and nonzero as `true`. A bare floating result is still rejected by a
`boolean_expr`; use `bool(value)` or a logical operator when floating
zero/nonzero conversion is intended. Operator precedence follows C++: unary,
multiplication, addition, shifts, comparisons, equality, bitwise AND, bitwise
XOR, bitwise OR, logical AND, then logical OR.

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

If you provide a non-default `Config`, generated messages use these runtime
hooks:

- `Config::Context` exposes `allocator`, `limits`, and `recursion_depth`.
- `Config::Vector<T>` supports `reserve`, `push_back`, iteration, `size`,
  `data`, and `value_type` for repeated fields. Scalar vectors additionally
  provide `append_trivial_range(values, count)` and
  `resize_for_overwrite(count)`, both returning `::protocyte::Status`.
- `Config::Map<K, V>`, `Config::Box<T>`, `Config::Optional<T>`,
  `Config::Bytes`, and `Config::String` provide the storage operations used by
  the generated field APIs.

`append_trivial_range` is the required bulk-commit primitive for staged packed
scalar values. `resize_for_overwrite` must support infallible shrinking to a
previous size so fixed-width packed reads can roll back the logical vector size
after an input failure. Reader interaction stays in the runtime rather than in
the vector contract.

Readers passed to generated `parse()` or `merge_from()` are required to expose
`eof()`, `position()`, `can_read(count)`, `read_byte()`, `read(out, count)`, and
`skip(count)`. `can_read(count)` returns `::protocyte::Status`, does not consume
input, and is part of the reader contract rather than an optional fast-path
hook. `SliceReader`, `ReaderRef`, `ParseBudgetReader`, and `LimitedReader` all
implement this transport contract. Parse readers passed between generated
nested messages additionally expose `consume_repeated_elements(count,
field_number)` and `consume_map_entries(count, field_number)`, both returning
`::protocyte::Status`. `ParseBudgetReader` owns those counters; `ReaderRef` and
`LimitedReader` forward them unconditionally.

Writers passed to generated `serialize()` are required to expose
`can_write(count)`, `write_byte(value)`, and `write(data, count)`.
`can_write(count)` returns `bool`, does not consume output capacity, and is part
of the writer contract rather than an optional bulk-write optimization.
`SliceWriter` implements this contract.

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

### Parse Resource Limits

`protocyte::Limits` separates protobuf-compatible wire limits from optional
application resource policy:

- `max_total_bytes` defaults to `0x7fffffff` and bounds all wire bytes read or
  skipped by one top-level `parse`, `merge_from`, or `merge_partial_from` call,
  including nested and unknown fields. This matches protobuf C++
  `CodedInputStream`'s default `INT_MAX` total-byte limit.
- `max_recursion_depth` defaults to `100`, matching protobuf C++.
- `max_message_bytes` and `max_string_bytes` bound individual
  length-delimited values.
- `max_repeated_elements` and `max_map_entries` default to `0x7fffffff` and
  count decoded occurrences across the complete top-level call. Packed chunks,
  expanded values, nested messages, and duplicate map keys share their
  respective budgets. Lower values are application security policy and may
  intentionally reject otherwise valid protobuf payloads; protobuf's wire
  format does not define collection-count limits.
- `max_total_allocation_bytes` is unbounded by default for `DefaultConfig` so
  the default does not reject a wire-valid message solely because its in-memory
  representation exceeds its wire size. Setting a finite value caps live
  allocator-requested bytes for the lifetime of its `Context`.
  Reallocation peaks count the new block before the old block is released.
  Allocators without a deallocation callback retain charged bytes because the
  runtime cannot know when an arena or bump allocator reclaims storage.
  Custom configs can implement equivalent allocator policy in `Config::allocate`
  and `Config::deallocate`.

Limit failures return `size_limit` or `count_limit`; allocation-budget
exhaustion returns `no_memory`. The default wire limits preserve protobuf's
sub-2-GiB envelope. Finite collection and allocation budgets are application
policy for attacker-controlled messages and can reject otherwise valid input.

### String Views

Generated `string` field accessors return `::protocyte::Span<const char>` by
default. Protocyte does not return `std::string_view` by default because the
runtime is designed for freestanding and kernel-style builds that avoid
standard-library exception surfaces. `std::string_view` includes checked APIs
such as `at()` and some `substr()` overloads whose standard contract can throw
`std::out_of_range`; `::protocyte::Span<const char>` keeps the default string
view API in Protocyte's no-exceptions runtime surface.

Hosted users who want standard-library interoperability can opt in:

```cmake
target_compile_definitions(my_target PRIVATE PROTOCYTE_ENABLE_STD_STRING_VIEW=1)
```

When `PROTOCYTE_ENABLE_STD_STRING_VIEW` is set to a nonzero value, the runtime
includes `<string_view>` and both `::protocyte::Span<char>` / `Span<const char>`
and `::protocyte::String` are implicitly convertible to `std::string_view`.
Generated immutable `string` field accessors also return `std::string_view` under
this opt-in, so hosted code can pass string fields directly to
standard-library APIs such as `std::format`. Code that does not enable the
option keeps the smaller no-exception `Span<const char>` accessor surface.

Generated package and message string constants use the
`::protocyte::StringView` alias. The alias is `::protocyte::Span<const char>`
when `PROTOCYTE_ENABLE_STD_STRING_VIEW` is zero and `std::string_view` when it
is nonzero. Both alternatives support constant-expression construction and
basic view operations used by generated constants, including `data()`,
`size()`, `empty()`, and indexing. The `Span<const char>` alternative is not a
drop-in replacement for the complete `std::string_view` API: it intentionally
does not provide string-specific operations such as `find()`, `substr()`, or
the comparison operators. Code that requires those APIs should enable
`PROTOCYTE_ENABLE_STD_STRING_VIEW` or handle the returned span explicitly.

In a Windows kernel driver, one technically possible MSVC/STL-specific escape
hatch is to provide the STL's internal out-of-range throw helper yourself so
`std::string_view::at()` can link even though exceptions are unavailable. This
should be treated as a last-resort compatibility shim, not as a recommended
Protocyte configuration: any accidental checked access would bugcheck the
system.

```cpp
#include <ntddk.h>

namespace std {
[[noreturn]] void __cdecl _Xout_of_range(char const*) {
    KeBugCheckEx(MANUALLY_INITIATED_CRASH, 'svat', 0, 0, 0);
    __assume(0);
}
}  // namespace std
```

Prefer the default `::protocyte::Span<const char>` API in kernel and
freestanding builds. It avoids depending on implementation-private STL symbols
and keeps checked string access out of the generated-code runtime surface.

### Parse Atomicity

`merge_from(reader)` commits parsed data per wire field occurrence. If a field
occurrence is malformed, truncated, exceeds a configured limit, or otherwise
fails while it is being read, that field occurrence does not change the visible
message state. Fields that were parsed successfully before the failing
occurrence remain committed, so `merge_from()` is not whole-message
transactional.

For singular message fields, a later valid occurrence still follows protobuf
merge semantics: it merges into the current field value and then replaces the
visible field only after the nested occurrence has parsed successfully. Oneof
fields switch cases only after the incoming occurrence is fully parsed.
Repeated fields and map fields append or insert only fully parsed elements or
entries; malformed packed repeated payloads do not append decoded prefix
values.

For bounded and fixed `bytes` storage, generated parsing may use
`resize_for_overwrite()` on staged scratch storage before the field is
committed. The reader's `can_read()` preflight only checks whether the
length-delimited payload should be available; if the following `read()` still
fails, the staged storage is discarded and the visible field remains unchanged.

For example, given this shape:

```proto
message Inner {
  string name = 1;
  repeated int32 values = 2 [packed = true];
}

message Packet {
  bytes digest = 1 [(protocyte.array) = { max: 32, fixed: true }];
  oneof choice {
    int32 code = 2;
    string label = 3;
    Inner nested_choice = 4;
  }
  Inner nested = 5;
  repeated int32 samples = 6 [packed = true];
  map<string, int32> counters = 7;
}
```

The contract is:

- If `digest` already contains 32 bytes and the wire stream later contains
  field `1` with a declared length of 32 but only 4 payload bytes available,
  `merge_from()` returns an error and the old 32-byte digest remains present
  and unchanged.
- If `choice` currently holds `label = "old"` and the wire stream contains a
  malformed `code` field or a truncated `nested_choice`, the active oneof case
  remains `label` with value `"old"`.
- If `nested` already contains `name = "old"` and `values = [1]`, a later
  valid `nested` occurrence containing `values = [2]` commits as protobuf
  merge semantics require: the visible field becomes `name = "old"` and
  `values = [1, 2]`. If that later nested occurrence is truncated, the visible
  field remains `name = "old"` and `values = [1]`.
- If `samples` is `[7]` and a later packed payload decodes the first value
  before failing on a truncated varint, no prefix values from that malformed
  payload are appended; `samples` remains `[7]`.
- If `counters` contains `{"ok": 1}` and a later map entry is malformed before
  the key and value are fully parsed, no partial entry is inserted and existing
  entries are left alone.
- If a stream contains a valid `digest` occurrence followed by a malformed
  `samples` occurrence, the valid `digest` stays committed after
  `merge_from()` returns the error from `samples`.

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
