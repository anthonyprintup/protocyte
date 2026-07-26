# Protocyte Extensions

Protocyte defines custom protobuf options in `protocyte/options.proto`.

Add its import root to `protoc`, then import:

```proto
import "protocyte/options.proto";
```

Extensions use protobuf's parenthesized syntax:

```proto
bytes sha256 = 1 [
  (protocyte.array) = { max: 32, fixed: true }
];
```

`[protocyte.array = ...]` is not valid extension syntax.

## Available Extensions

- `option (protocyte.package_constant) = { ... };` on files;
- `option (protocyte.constant) = { ... };` on messages;
- `(protocyte.array) = { max: ... }` on supported fields;
- `(protocyte.array) = { expr: ... }` for expression-sized storage;
- `(protocyte.array) = { ..., fixed: true }` for exact extents.

## Package Constants

File options become namespace-scope `inline constexpr` C++ declarations:

```proto
option (protocyte.package_constant) = {
  name: "CAP",
  u32: 32
};

option (protocyte.package_constant) = {
  name: "LABEL",
  str: "pkt"
};
```

Package constants can reference other constants in the same package.

## Message Constants

Message options become generated class constants:

```proto
message Packet {
  option (protocyte.constant) = {
    name: "DOUBLE_CAP",
    u32_expr: "CAP * 2"
  };

  option (protocyte.constant) = {
    name: "FULL_LABEL",
    str_expr: "LABEL + \"-frame\""
  };
}
```

Each constant sets exactly one typed value:

- `boolean`, `boolean_expr`;
- `i32`, `i32_expr`;
- `u32`, `u32_expr`;
- `i64`, `i64_expr`;
- `u64`, `u64_expr`;
- `f32`, `f32_expr`;
- `f64`, `f64_expr`;
- `str`, `str_expr`.

## Name Resolution

Expressions can reference constants:

- in the current message;
- in enclosing messages;
- in the current package;
- through root-relative message names such as `Outer.Inner.CAPACITY`;
- across packages with names such as `my.pkg.Outer.Inner.CAPACITY`;
- through package-qualified names such as `my.pkg.CAPACITY`.

Declaration order does not change dependency resolution.

## Expression Operators

Supported syntax includes:

- arithmetic: `+`, `-`, `*`, `/`, `%`;
- bitwise: `~`, `&`, `^`, `|`, `<<`, `>>`;
- comparisons: `<`, `<=`, `>`, `>=`, `==`, `!=`;
- logical: `!`, `&&`, `||`;
- string concatenation with `+`;
- parentheses and normal C++-style precedence.

Logical `&&` and `||` short-circuit value evaluation. The skipped operand is still parsed and type-checked.

## Scalar Casts

Use:

```text
bool(value)
i32(value)
u32(value)
i64(value)
u64(value)
f32(value)
f64(value)
str(value)
```

Expression literals and intermediate operations do not inherit the destination type. Use an explicit cast when width or signedness matters:

```text
u64(1) << 40
u32(-1) + 1
```

Integer conversions use fixed-width C++ modulo/two's-complement behavior. Floating-to-integer conversion truncates toward zero and then checks the target range.

Numeric and boolean casts do not parse strings.

## Numeric Semantics

Integer literals follow fixed-width C++ unsuffixed candidate behavior:

- decimal: `i32`, then `i64`;
- hexadecimal: `i32`, `u32`, `i64`, then `u64`;
- floating literals: `f64`.

A leading sign is a unary operator. For example, `-2147483648` has `i64` kind unless explicitly cast.

Boolean values promote to `i32` for numeric and integral operators.

Mixed arithmetic uses:

1. `f64` when present;
2. otherwise `f32`;
3. otherwise C++ usual signed/unsigned integer conversions.

Unsigned arithmetic wraps. Signed overflow, division by zero, and signed `MIN / -1` or `MIN % -1` are rejected. Signed division truncates toward zero.

Every `f32` operation rounds to binary32 before a containing operation consumes it.

## Shifts and Bitwise Operations

Bitwise operands must be fixed-width integers or booleans. Floating-point and string operands are rejected.

Shift operands retain independent kinds. The result has the left operand's kind and width. The normalized count must be nonnegative and smaller than that width.

Left shifts use C++20 width-modulo behavior. Unsigned right shifts are logical; signed right shifts are arithmetic.

## Boolean Expressions

Logical operators accept booleans and finite numeric values using zero/nonzero conversion.

`boolean_expr` accepts a boolean or integer result. A bare floating result is rejected; use `bool(value)` when floating zero/nonzero conversion is intended.

## String Helpers

Available generator-side helpers:

```text
len(value)
substr(value, start, count)
starts_with(value, prefix)
```

Generator-side strings are Unicode. `len` and `substr` count Unicode code points.

Generated C++ strings store UTF-8, so runtime view sizes and indices are byte-based. Do not reuse a generator code-point index as a runtime byte offset without conversion.

## Math Functions

Available functions:

```text
pow
abs
min
max
sqrt
exp
log
log2
log10
ceil
floor
trunc
round
```

Math is evaluated by the generator and emitted as typed literals. It adds no generated runtime dependency.

- `pow(base, exponent)` converts both inputs to `f64` and returns `f64`.
- `abs` preserves the promoted input kind.
- `min` and `max` use one common promoted kind and let the first operand win ties.
- `sqrt`, `exp`, logarithms, and rounding functions return `f32` for an `f32` input and otherwise `f64`.
- `round` uses halfway-away-from-zero behavior.
- domain errors and non-finite results are rejected.

`pow`, `sqrt`, `exp`, `log`, `log2`, and `log10` use Protocyte's dependency-free deterministic backend rather than host `libm`. The backend evaluates with a 160-digit decimal context and rounds directly to IEEE-754 binary32 or binary64.

Integral powers use exact rational evaluation when bounded within 4096 bits. Exact power-of-two bases also use a direct binary path, including subnormal halfway cases.

This behavior is stable across generator hosts but does not promise bit-for-bit agreement with every target C++ runtime.

## Expression Safety Limits

Expression syntax may nest to 32 levels. Entering level 33 reports:

```text
expression nesting exceeds maximum depth of 32
```

A dependency chain may contain 32 constants. Resolving a 33rd reports:

```text
constant dependency nesting exceeds maximum depth of 32
```

Residual host recursion exhaustion is converted into a normal labeled generator error. No partial generated files are emitted.

## Bounded and Fixed Storage

Apply `protocyte.array` to:

- singular `bytes`;
- repeated scalar fields.

Bounded bytes use inline storage with a mutable size. Bounded repeated scalars use inline array storage.

`fixed: true` changes the contract:

- bytes have presence and exactly the declared extent when present;
- repeated fields are either empty or have exactly the declared element count.

```proto
message Digest {
  bytes sha256 = 1 [
    (protocyte.array) = { max: 32, fixed: true }
  ];
}
```

Use a constant expression for the extent:

```proto
option (protocyte.package_constant) = {
  name: "CAP",
  u32: 16
};

message Samples {
  option (protocyte.constant) = {
    name: "DOUBLE_CAP",
    u32_expr: "CAP * 2"
  };

  repeated int32 values = 1 [
    (protocyte.array) = { expr: "DOUBLE_CAP" }
  ];
}
```

Inline bytes do not use `Limits::max_string_bytes`; their schema bound owns the field limit. Aggregate input remains subject to `max_total_bytes`.

`protocyte.array` cannot be applied to map fields.

## Diagnostics

Invalid extension use reports a generator error with the relevant file, message, field, option, or expression label. Protocyte validates the complete model before publishing generated response files.

## Related Pages

- [Code Generation](https://github.com/anthonyprintup/protocyte/wiki/Code-Generation)
- [Plugin Parameters](https://github.com/anthonyprintup/protocyte/wiki/Plugin-Parameters)
- [Generated C++ API](https://github.com/anthonyprintup/protocyte/wiki/Generated-Cpp-API)
- [Embedded and Freestanding](https://github.com/anthonyprintup/protocyte/wiki/Embedded-and-Freestanding)
