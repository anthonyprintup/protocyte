# CMake API Reference

These functions are available after either
`FetchContent_MakeAvailable(protocyte)` or
`find_package(protocyte CONFIG REQUIRED)`. Keyword order does not matter.
Unknown arguments, missing keyword values, duplicate single-value keywords,
and incompatible mode selections are configuration errors.

## `protocyte_setup_codegen`

```cmake
protocyte_setup_codegen()
```

Prepares the Protocyte plugin and locates or provisions `protoc`. The
generation helpers call it automatically, so most projects do not call it
directly. It accepts no arguments.

An explicit `Protobuf_PROTOC_EXECUTABLE` takes precedence over
package-provided targets and `PATH`. An ordinary relative value is anchored to
the source directory of the first Protocyte setup call that consumes that exact
value; descendants and siblings reuse the resolved executable instead of
rebasing it. Cross builds require a concrete host path here. Generator
expressions and target emulators are not supported, and the executable must
pass a `--version` probe.

Automatically discovered protobuf imports remain associated with their
compiler. Set `PROTOCYTE_PROTOBUF_IMPORT_DIR` explicitly when different
compilers should intentionally share one import root.

## `protocyte_generate`

```text
protocyte_generate(
    TARGET <codegen-target>
    OUT_DIR <directory>

    PROTO_ROOT <directory>
    # or: DESCRIPTOR_SET <file>

    DISCOVER
    # or: PROTOS <source-file-or-descriptor-name>...

    [IMPORT_DIRS <directory>...]
    [DEPENDS <file-or-target>...]
    [OPTIONS <plugin-option>...]
    [EMIT_RUNTIME]
    [RUNTIME_PREFIX <virtual-directory>]
    [NAMESPACE_PREFIX <c++-namespace>]
    [INCLUDE_PREFIX <virtual-directory>]
    [GENERATED_HEADERS_VAR <variable>]
    [GENERATED_SOURCES_VAR <variable>]
    [GENERATED_TARGET_VAR <variable>]
)
```

This lower-level primitive creates a code-generation target but no C++
library.

- `TARGET` names the required custom target.
- `OUT_DIR` is required and must be known at configure time. A relative path
  is resolved from `CMAKE_CURRENT_BINARY_DIR`; generator expressions are
  rejected. With Visual Studio, Protocyte compacts overlong descriptor output
  paths while preserving a stable, collision-resistant name.
- `PROTO_ROOT` selects source mode and must name an existing directory.
  Explicit `PROTOS` are resolved from `CMAKE_CURRENT_SOURCE_DIR`, must exist at
  configure time, and must be beneath `PROTO_ROOT`.
- `DESCRIPTOR_SET` selects descriptor-set mode. Its path must be concrete and
  configuration-independent. Relative paths resolve from
  `CMAKE_CURRENT_SOURCE_DIR`. With `DISCOVER`, the file must exist at configure
  time. With explicit `PROTOS`, it may be build-generated when its producer is
  named in `DEPENDS`.
- `DISCOVER` is mutually exclusive with `PROTOS`. Source discovery recursively
  finds `*.proto` beneath `PROTO_ROOT` and reconfigures when that set changes.
  Descriptor discovery selects each supported non-runtime descriptor from the
  existing set.
- `IMPORT_DIRS` adds existing source-mode protobuf import roots. It is rejected
  in descriptor-set mode. Protocyte tracks transitive imports and import-root
  topology.
- `DEPENDS` adds files or targets to the generation command. Prefer absolute
  file paths or target names.
- `OPTIONS` accepts non-runtime [plugin parameters](Plugin-Parameters), each as
  `key=value`. Do not pass `runtime`, `runtime_prefix`, or `include_prefix`
  here; use their dedicated CMake arguments. Names beginning with
  `_protocyte_` are reserved.
- `EMIT_RUNTIME` emits `runtime.hpp`. The default path is
  `protocyte/runtime/runtime.hpp`. Each emitted runtime path has exactly one
  generation owner.
- `RUNTIME_PREFIX` selects the runtime's normalized relative virtual
  directory. With `EMIT_RUNTIME`, it controls the output and include path;
  otherwise, it changes only the generated include.
- `NAMESPACE_PREFIX` prepends a C++ namespace to generated declarations.
- `INCLUDE_PREFIX` prepends a relative virtual directory to imported generated
  header includes. At this level the caller must arrange matching output and
  include roots.
- `GENERATED_HEADERS_VAR` and `GENERATED_SOURCES_VAR` receive generated paths
  in the caller's scope.
- `GENERATED_TARGET_VAR` receives `TARGET` in the caller's scope.

### Output ownership and transactions

Generated files in one configure have exactly one current target owner,
including portable case-insensitive path aliases. One canonical `OUT_DIR`
belongs to one canonical CMake build tree. Trees may share the directory only
when they have the same canonical identity; generation is protected by
cross-process locks.

Protocyte stores a hashed sibling `.owner` record for the output directory and
a path-keyed record for every concrete generated file. The records contain a
format version and SHA-256 identities, not private absolute paths.

Configuration performs a read-only conflict preflight. The build revalidates
the claims, runs `protoc` into a private staging directory, and validates every
expected file before it publishes an ownership transaction or replaces a
declared output. A `protoc` failure, timeout, or invalid staging result attempts
to discard staging and publishes no new ownership claim. If cleanup refuses an
unsafe staging path or cannot remove it, Protocyte warns that inert staging
data outside `OUT_DIR` may remain; ownership claims and declared generated
files stay unchanged. Configuration itself never publishes a claim.

After staging succeeds, Protocyte durably commits the ownership transaction
before publishing generated files. An interrupted publication is reconciled by
a later build. A previously configured tree loses write access at its next
build after a deliberate ownership transfer.

Protocyte fingerprints generated outputs and removes an unchanged file when
its owner stops declaring it. Outputs from older records without fingerprints
are preserved because user edits cannot be distinguished safely.

`PROTOCYTE_OUTPUT_LOCK_ROOT` may select an absolute shared output-lock
namespace. The default is the current user's cache directory. Different
namespaces opt trees out of cross-tree collision detection and are unsafe for
overlapping outputs.

Deleting a build directory does not release its outputs. To transfer an
`OUT_DIR`, stop every build that may use it, preserve needed files, and use the
configure-time diagnostic to identify the exact output-directory and
generated-file owner records. Remove only those listed records, then configure
the new tree. Do not delete the whole output-lock namespace. `.lock` files
contain no ownership state and may remain.

`RUNTIME_PREFIX` and `INCLUDE_PREFIX` are portable virtual directories. They
must be normalized, relative, `/`-separated paths without `.` or `..`
segments, Windows device names, or characters unsafe in generated includes.

## `protocyte_add_proto_library`

```text
protocyte_add_proto_library(
    TARGET <library-target>
    [ALIAS <alias-target>]
    [TYPE STATIC|SHARED|MODULE|OBJECT]
    [OUT_DIR <directory>]
    [INSTALL_INCLUDE_DIR <relative-directory>]

    PROTO_ROOT <directory>
    # or: DESCRIPTOR_SET <file>

    DISCOVER
    # or: PROTOS <source-file-or-descriptor-name>...

    [IMPORT_DIRS <directory>...]
    [DEPENDS <file-or-target>...]
    [OPTIONS <plugin-option>...]
    [EMIT_RUNTIME]
    [HOSTED_ALLOCATOR]
    [RUNTIME_TARGET <target>]
    [RUNTIME_PREFIX <virtual-directory>]
    [NAMESPACE_PREFIX <c++-namespace>]
    [INCLUDE_PREFIX <virtual-directory>]
    [GENERATED_HEADERS_VAR <variable>]
    [GENERATED_SOURCES_VAR <variable>]
    [GENERATED_TARGET_VAR <variable>]
)
```

This is the recommended target-oriented API. It forwards the generation
arguments above, creates the internal `<TARGET>__protocyte_codegen` target,
and compiles the generated sources as a C++20 library.

- `TARGET` is required and must be a real target name without `::`.
- `ALIAS` optionally creates an alias such as `demo::proto`.
- `TYPE` accepts `STATIC`, `SHARED`, `MODULE`, or `OBJECT`; the default is
  `STATIC`.
- `OUT_DIR` defaults to
  `${CMAKE_CURRENT_BINARY_DIR}/<TARGET>_protocyte`. It is the public build
  include root. With `INCLUDE_PREFIX`, generation occurs beneath
  `OUT_DIR/INCLUDE_PREFIX`.
- `INSTALL_INCLUDE_DIR` opts the target into install/export support and adds
  the normalized relative path to its install interface. Generated headers are
  exposed through the `protocyte_generated_headers` file set.
- `HOSTED_ALLOCATOR` selects hosted allocation support. With `EMIT_RUNTIME`, it
  publicly defines `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1`. Otherwise it selects
  `protocyte::runtime_hosted`.
- `RUNTIME_TARGET` selects an existing runtime target. It is mutually exclusive
  with `EMIT_RUNTIME`.
- A custom `RUNTIME_PREFIX` requires either `EMIT_RUNTIME` or a matching custom
  `RUNTIME_TARGET`.
- The three `GENERATED_*_VAR` arguments return the generated paths or internal
  code-generation target in the caller's scope.

The created target requires C++20, publicly exposes its build include root,
links `protocyte::codegen`, and links the selected runtime. Without
`INSTALL_INCLUDE_DIR`, the library remains build-only.

Install an opted-in target and its generated headers together:

```cmake
include(GNUInstallDirs)

protocyte_add_proto_library(
    TARGET demo_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    INSTALL_INCLUDE_DIR "${CMAKE_INSTALL_INCLUDEDIR}"
)

install(
    TARGETS demo_proto
    EXPORT demoTargets
    FILE_SET protocyte_generated_headers
        DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
)
install(
    EXPORT demoTargets
    NAMESPACE demo::
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/demo"
)
```

The consuming package config must call
`find_dependency(protocyte CONFIG)` before including the exported targets.

## `protocyte_add_descriptor_set_library`

```text
protocyte_add_descriptor_set_library(
    TARGET <library-target>
    DESCRIPTOR_SET <file>
    [ALIAS <alias-target>]
    [TYPE STATIC|SHARED|MODULE|OBJECT]
    [OUT_DIR <directory>]
    [INSTALL_INCLUDE_DIR <relative-directory>]

    DISCOVER
    # or: FILES <virtual-descriptor-name>...

    [DEPENDS <file-or-target>...]
    [OPTIONS <plugin-option>...]
    [EMIT_RUNTIME]
    [HOSTED_ALLOCATOR]
    [RUNTIME_TARGET <target>]
    [RUNTIME_PREFIX <virtual-directory>]
    [NAMESPACE_PREFIX <c++-namespace>]
    [INCLUDE_PREFIX <virtual-directory>]
    [GENERATED_HEADERS_VAR <variable>]
    [GENERATED_SOURCES_VAR <variable>]
    [GENERATED_TARGET_VAR <variable>]
)
```

This wrapper requires `DESCRIPTOR_SET` and otherwise has the library, runtime,
dependency, option, prefix, output, and installation behavior described above.
`FILES` is the descriptor-set spelling of `PROTOS`; choose exactly one of
`DISCOVER` and `FILES`. `PROTO_ROOT` and `IMPORT_DIRS` do not apply.

## Package variables and targets

The package exposes these configuration variables:

- `PROTOCYTE_FETCH_PROTOBUF`
- `PROTOCYTE_PYTHON_ENV_ROOT`
- `PROTOCYTE_PLUGIN_EXECUTABLE`
- `PROTOCYTE_PROTOBUF_IMPORT_DIR`
- `PROTOCYTE_OUTPUT_LOCK_ROOT`
- `Protobuf_PROTOC_EXECUTABLE`

It provides `protocyte::codegen`, `protocyte::runtime`, and
`protocyte::runtime_hosted`. See [FetchContent](FetchContent) and
[Installed Package](Installed-Package) for default values in each integration
mode.
