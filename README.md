# Protocyte

Protocyte is a Python `protoc` plugin that generates C++20 protobuf code for
freestanding, embedded, or kernel-style environments. The generated C++ avoids
the STL, exceptions, RTTI, iostreams, and implicit global allocation.

## Quick Start

You need Python 3.12 or newer, [uv](https://docs.astral.sh/uv/), `protoc`,
CMake 3.24 or newer, and a C++20 compiler. From a Protocyte checkout, this
PowerShell flow builds and installs the wheel into an isolated environment,
then generates, builds, and runs the checked-in example:

```powershell
uv build --wheel
uv venv build\quickstart-venv --python 3.12

$wheel = (Get-ChildItem dist\protocyte-*.whl | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
$python = "$PWD\build\quickstart-venv\Scripts\python.exe"
uv pip install --python $python $wheel

$protoc = (Get-Command protoc).Source
$plugin = "$PWD\build\quickstart-venv\Scripts\protoc-gen-protocyte.exe"
cmake -S examples/quickstart -B build/quickstart `
  "-DPROTOC_EXECUTABLE=$protoc" `
  "-DPROTOCYTE_PLUGIN_EXECUTABLE=$plugin"
cmake --build build/quickstart --config Release
ctest --test-dir build/quickstart -C Release --output-on-failure
```

[`examples/quickstart/main.cpp`](examples/quickstart/main.cpp) mutates a
generated message, serializes it into a byte vector, parses those bytes into a
new message, and verifies the value. CI compiles and runs this exact source as
part of the complete install-to-round-trip path:

<!-- quickstart-main-start -->
```cpp
#include <vector>

#include <protocyte/runtime/runtime.hpp>

#include "quickstart.protocyte.hpp"

int main() {
    auto encode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    auto reading = demo::quickstart::Reading<>::create(encode_ctx);
    reading.set_value(42u);

    const auto size = reading.encoded_size();
    if (!size) {
        return 1;
    }

    std::vector<protocyte::u8> encoded(*size);
    const auto written = reading.serialize(encoded);
    if (!written || *written != encoded.size()) {
        return 2;
    }

    auto decode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    const auto parsed = demo::quickstart::Reading<>::parse(decode_ctx, encoded);
    if (!parsed || (*parsed).value() != 42u) {
        return 3;
    }

    return 0;
}
```
<!-- quickstart-main-end -->

On POSIX systems, the virtual-environment executables are under
`build/quickstart-venv/bin` instead of `Scripts`.

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

Protocyte's Python package requires Python 3.12 or newer. That applies to
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

Protobuf virtual descriptor names may contain characters that are not portable
host-file names. Protocyte preserves ordinary path segments and hex-escapes
nonportable UTF-8 bytes as `~HH` in generated paths; for example,
`api/bad"name.proto` emits `api/bad~22name.protocyte.hpp`, and semicolons are
escaped as `~3B` so generated names remain safe in CMake lists. A literal `~`
is escaped too, so this mapping cannot alias an unescaped descriptor name. If
escaping would exceed a filesystem's common 255-byte component limit,
Protocyte retains a readable prefix and appends the full SHA-256 digest of the
original segment. The final segment also reserves room for
`.protocyte.hpp`/`.protocyte.cpp`.

The CMake helpers pass protoc options and file names through protoc's UTF-8
response-file interface. Non-ASCII characters and spaces are retained in
descriptor names and source, tool, and output paths; semicolons and quotes in
descriptor names remain literal too. This behavior is consistent on Windows and
POSIX hosts. Protoc defines each response-file line as one literal argument and
provides no escaping for line breaks, so the CMake helpers reject descriptor
names or paths containing carriage returns or line feeds.

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
listed for generation. Generated C++ documentation requires source information;
when creating a descriptor set that should retain schema comments, pass
`--include_source_info` to `protoc`. Descriptor sets without source information
remain valid but cannot reproduce documentation comments.

## CMake Integration

Protocyte supports two CMake consumption modes:

- Source consumption with `FetchContent`
- Installed-package consumption with `find_package(protocyte CONFIG REQUIRED)`

### Release Assets

Published GitHub releases contain three different asset types:

- `protocyte-X.Y.Z-py3-none-any.whl`: the Python wheel for
  `protoc-gen-protocyte`. Install it into a Python 3.12+ environment when you
  want the plugin executable.
- `protocyte-X.Y.Z.tar.gz`: the Python source distribution for the same plugin
  package. It is also a Python 3.12+ artifact, not a CMake install tree.
- `protocyte-X.Y.Z-cmake-prefix.tar.gz`: a preinstalled CMake prefix for
  `find_package(protocyte CONFIG REQUIRED)`. Unpack it and add the extracted
  directory to `CMAKE_PREFIX_PATH`.

The CMake prefix archive includes the CMake files, C++ runtime headers, and an
installable copy of the protocyte Python generator project. It does not bundle
Python itself. The first downstream configuration that needs code generation
finds a local Python 3.12+ interpreter, creates a fingerprinted virtual
environment under the build tree, and installs protocyte and its Python
dependencies there from the exact versions in the bundled CMake constraints
file. The install is built from a writable staged copy, so it never modifies
the CMake package prefix, installs packages globally, or changes the selected
base interpreter.

The initial configuration may access the configured Python package index.
Subsequent configurations reuse the environment while the Python interpreter,
protocyte sources, and package metadata remain unchanged. Set
`PROTOCYTE_PYTHON_ENV_ROOT` before making protocyte available to choose another
build-local environment directory. Set `PROTOCYTE_PLUGIN_EXECUTABLE` to a
preinstalled plugin when dependency provisioning must be managed externally.
The override must be version-compatible with the CMake package and support
`--version` plus `descriptor-set list <file>`; descriptor-set `DISCOVER` uses
that command so discovery and generation always run in the same Python
environment.

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

When Protocyte is consumed through `FetchContent` or `add_subdirectory`,
`PROTOCYTE_INSTALL` defaults to `OFF`. This keeps Protocyte's headers, Python
project, and CMake package out of the parent project's install tree. A parent
that intentionally packages Protocyte can opt in before making it available:

```cmake
set(PROTOCYTE_INSTALL ON)
FetchContent_MakeAvailable(protocyte)
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

Descriptors that Protocyte cannot generate, such as files with unsupported
message-scoped extension declarations, may remain dependency-only when no
generated field uses their types. If a selected field references a message or
enum from such a file, `DISCOVER` fails immediately and identifies the field,
type, descriptor, and unsupported declaration instead of emitting a header with
an unavailable generated include.

Formatter executable and config values in `OPTIONS` may use absolute Windows
or POSIX paths. Generated include and runtime prefixes are not filesystem paths;
they must use the normalized relative virtual-directory form documented below.

By default, the protocyte CMake project fetches protobuf when protobuf CMake
targets are not already available, then exposes:

- `protocyte_add_proto_library(...)` for the common target-oriented workflow
- `protocyte_add_descriptor_set_library(...)` as the descriptor-set-specific wrapper
- `protocyte_generate(...)` as the lower-level codegen primitive
- `protocyte_setup_codegen()` to prepare the generator and `protoc` eagerly
- `protocyte::runtime` and `protocyte::runtime_hosted` for reusable runtime linkage

The fallback protobuf revision is the exact commit recorded in
`PROTOCYTE_PROTOBUF_GIT_TAG`, rather than a mutable branch or release tag.
When this fallback owns the protobuf build, Protocyte supplies function-scoped
defaults for protobuf's build options, including `protobuf_INSTALL=OFF`, so
protobuf, Abseil, upb, utf8_range, and protoc do not leak into the consumer's
install tree. Parent-defined protobuf option values remain authoritative and
Protocyte does not force or persist them in the parent cache.

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

`PROTOCYTE_INSTALL` defaults to `ON` when Protocyte is the top-level project,
so this standalone installation path remains enabled without extra options.

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

- the complete public CMake API documented below
- the exported `protocyte::codegen`, `protocyte::runtime`, and `protocyte::runtime_hosted` targets
- an installable protocyte Python project and pinned constraints used to provision the managed plugin environment
- the reusable C++ runtime headers and targets
- `protocyte/options.proto`

The installed package does not embed Python or protobuf. Consumers that run
code generation still need a working Python 3.12+ base interpreter. Protocyte
installs its Python package and Python dependencies into an isolated directory
under `PROTOCYTE_PYTHON_ENV_ROOT`; `protoc` and the C++ protobuf files remain
caller-supplied unless the fetch fallback is enabled:

```cmake
set(PROTOCYTE_FETCH_PROTOBUF ON CACHE BOOL "" FORCE)
find_package(protocyte CONFIG REQUIRED)
```

Public CMake variables exposed by the package:

- `PROTOCYTE_PROTO_DIR`: the installed directory that contains `protocyte/options.proto`
- `PROTOCYTE_OPTIONS_PROTO`: the full path to `protocyte/options.proto`
- `PROTOCYTE_PROTOBUF_GIT_TAG`: the protobuf revision used when `PROTOCYTE_FETCH_PROTOBUF=ON`
- `PROTOCYTE_PYTHON_ENV_ROOT`: the build-local root for fingerprinted managed Python environments
- `PROTOCYTE_PLUGIN_EXECUTABLE`: an optional compatible preinstalled plugin that bypasses managed provisioning

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

### CMake API Reference

These functions are available after either `FetchContent_MakeAvailable(protocyte)`
or `find_package(protocyte CONFIG REQUIRED)`. Keyword order does not matter.
In the signatures below, `<value>` is a placeholder, `...` means that a keyword
accepts multiple values, and commented `or` lines identify mutually exclusive
choices rather than literal CMake syntax.

#### `protocyte_setup_codegen`

```cmake
protocyte_setup_codegen()
```

Prepares the Protocyte plugin and locates or provisions `protoc`. Generation
helpers call it automatically, so most projects do not need to call it. Use it
when configuration should perform that setup eagerly, before any generation
target is declared. It has no options.

#### `protocyte_generate`

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

This is the lower-level primitive. It creates the custom target named by
`TARGET`, but it does not create a C++ library.

- `TARGET` is the required code-generation target name.
- `OUT_DIR` is required and must be known at configure time; generator
  expressions are not accepted. A relative path is resolved from
  `CMAKE_CURRENT_BINARY_DIR`.
- `PROTO_ROOT` selects source mode. It must name an existing directory. Explicit
  `PROTOS` entries are source files resolved from `CMAKE_CURRENT_SOURCE_DIR`,
  must exist during configuration, and must be inside `PROTO_ROOT`.
- `DESCRIPTOR_SET` selects descriptor-set mode and is mutually exclusive with
  `PROTO_ROOT`. It must name an existing file; relative paths are resolved from
  `CMAKE_CURRENT_SOURCE_DIR`. In this mode, `PROTOS` entries are relative virtual
  descriptor names inside the set rather than filesystem paths.
- `DISCOVER` is mutually exclusive with `PROTOS`. In source mode it recursively
  discovers `*.proto` beneath `PROTO_ROOT` and reconfigures when that set changes.
  In descriptor-set mode it asks the Protocyte plugin to select every supported
  non-runtime descriptor, including referenced runtime types when required.
- `IMPORT_DIRS` adds source-mode protobuf import roots. Entries must be existing
  directories and are resolved from `CMAKE_CURRENT_SOURCE_DIR`. It is rejected
  in descriptor-set mode. Each selected source tracks its transitive imports,
  so changing an imported `.proto` triggers regeneration without requiring the
  import graph to be repeated through `DEPENDS`.
- `DEPENDS` adds dependencies to the generation custom command. Entries are
  passed to CMake's `add_custom_command(DEPENDS ...)`; prefer absolute file paths
  or CMake targets. Use it for project-specific prerequisite files or targets
  that Protocyte does not otherwise track.
- `OPTIONS` forwards non-runtime [plugin parameters](#plugin-parameters).
  Do not pass `runtime` or `runtime_prefix` here; use `EMIT_RUNTIME` and
  `RUNTIME_PREFIX` so CMake can declare the generated runtime output correctly.
  Names beginning with `_protocyte_` are reserved. Do not duplicate
  `NAMESPACE_PREFIX` or `INCLUDE_PREFIX` through `OPTIONS`; duplicate plugin
  parameter names are rejected.
- `EMIT_RUNTIME` emits `runtime.hpp` into `OUT_DIR`. The default location is
  `protocyte/runtime/runtime.hpp`.
- `RUNTIME_PREFIX` changes the runtime's relative virtual directory. With
  `EMIT_RUNTIME`, it controls both the emitted path and generated include. Without
  `EMIT_RUNTIME`, it changes only the generated include path.
- `NAMESPACE_PREFIX` prepends a C++ namespace to generated declarations.
- `INCLUDE_PREFIX` prepends a relative virtual directory to imported generated
  header includes.
- `GENERATED_HEADERS_VAR` receives the generated header paths in the caller's
  scope.
- `GENERATED_SOURCES_VAR` receives the generated source paths in the caller's
  scope.
- `GENERATED_TARGET_VAR` receives `TARGET` in the caller's scope.

`RUNTIME_PREFIX` and `INCLUDE_PREFIX` are virtual include directories, not host
filesystem paths. They must be normalized, relative, `/`-separated paths and
must not contain `.`/`..` segments, Windows device names, or characters unsafe
in generated includes.

#### `protocyte_add_proto_library`

```text
protocyte_add_proto_library(
    TARGET <library-target>
    [ALIAS <alias-target>]
    [TYPE STATIC|SHARED|MODULE|OBJECT]
    [OUT_DIR <directory>]

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

This is the recommended target-oriented API. It forwards `PROTO_ROOT`,
`DESCRIPTOR_SET`, `DISCOVER`, `PROTOS`, `IMPORT_DIRS`, `DEPENDS`, `OPTIONS`,
`EMIT_RUNTIME`, `RUNTIME_PREFIX`, `NAMESPACE_PREFIX`, and `INCLUDE_PREFIX` to
`protocyte_generate`, then compiles the generated sources as a C++20 library.

- `TARGET` is required and must be a real target name without `::`.
- `ALIAS` optionally creates an alias for `TARGET`; namespaced aliases such as
  `demo::proto` are recommended for downstream linkage. The alias must not
  already exist.
- `TYPE` accepts `STATIC`, `SHARED`, `MODULE`, or `OBJECT` and defaults to
  `STATIC`.
- `OUT_DIR` defaults to
  `${CMAKE_CURRENT_BINARY_DIR}/<TARGET>_protocyte`. Relative paths are resolved
  from `CMAKE_CURRENT_BINARY_DIR`; generator expressions are not accepted.
- `HOSTED_ALLOCATOR` selects hosted allocation support. With `EMIT_RUNTIME`, it
  adds `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1` to consumers of the emitted runtime.
  Otherwise, it selects the default `protocyte::runtime_hosted` target when no
  explicit `RUNTIME_TARGET` is supplied.
- `RUNTIME_TARGET` selects an existing runtime target instead of the default
  `protocyte::runtime` or `protocyte::runtime_hosted`. It is mutually exclusive
  with `EMIT_RUNTIME`; the supplied target owns its allocator configuration.
- A custom `RUNTIME_PREFIX` requires either `EMIT_RUNTIME` or a matching custom
  `RUNTIME_TARGET`; this prevents generated includes from disagreeing with the
  linked reusable runtime.
- `GENERATED_HEADERS_VAR` and `GENERATED_SOURCES_VAR` receive the generated path
  lists in the caller's scope.
- `GENERATED_TARGET_VAR` receives the internal
  `<TARGET>__protocyte_codegen` target in the caller's scope.

The created library publicly exposes `OUT_DIR`, requires C++20, links
`protocyte::codegen`, and depends on its generated target. When neither
`EMIT_RUNTIME` nor `RUNTIME_TARGET` is supplied, it links `protocyte::runtime`
or `protocyte::runtime_hosted` according to `HOSTED_ALLOCATOR`.

#### `protocyte_add_descriptor_set_library`

```text
protocyte_add_descriptor_set_library(
    TARGET <library-target>
    DESCRIPTOR_SET <file>
    [ALIAS <alias-target>]
    [TYPE STATIC|SHARED|MODULE|OBJECT]
    [OUT_DIR <directory>]

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

This convenience wrapper requires `DESCRIPTOR_SET` and otherwise has the same
library, runtime, `DEPENDS`, `OPTIONS`, prefix, and output-variable behavior as
`protocyte_add_proto_library`. `FILES` is the descriptor-set-specific spelling
of `PROTOS`: each entry is a relative virtual descriptor name inside the set.
Choose exactly one of `DISCOVER` or `FILES`. `PROTO_ROOT` and `IMPORT_DIRS` do
not apply because the descriptor set already carries its dependency descriptors.

All public helpers reject unknown arguments during configuration.
`protocyte_generate`, `protocyte_add_proto_library`, and
`protocyte_add_descriptor_set_library` also reject keywords without values.

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
- `comments=on|off`: emit schema comments as Doxygen documentation on generated
  C++ types and field APIs. The default is `on`. This setting does not suppress
  `[[deprecated]]` attributes derived from protobuf field and enum-value options.
- `format=auto|off|required`: control generated C++ formatting. `auto` is the
  default and formats when `clang-format` is available; `off` never launches a
  formatter; `required` reports an error when no formatter is available.
- `clang_format=<executable-or-path>`: run an explicit `clang-format`
  executable after generation. The value is passed as one executable argument,
  not interpreted by a shell; do not append command-line options. When
  specified, launch and formatting failures are reported as plugin errors.
- `clang_format_config=<path>`: use an explicit clang-format config file when
  formatting runs. Supplying either explicit formatter parameter implies
  `format=required`; neither can be combined with `format=off`.

Runtime and include prefixes are portable protobuf virtual directories, not
filesystem paths. They must be normalized relative paths using `/`; absolute or
drive-rooted paths, backslashes, control characters, empty segments, `.` and
`..` segments, leading or trailing segment whitespace, C++ include delimiters,
CMake list separators, Windows-reserved characters, and Windows device names
are rejected. The same validation is applied by the CMake helpers before
generated outputs are declared.

Parameter names are exact and case-sensitive. Unknown names, duplicate names,
and bare tokens without `=` are errors; aliases are not accepted.
Names beginning with `_protocyte_` are reserved for CMake's parameter transport
and must not be supplied through CMake `OPTIONS`.
`namespace_prefix` must be a normalized `::`-separated namespace whose
components are portable, non-reserved C++ identifiers. Empty components, C++
keywords, leading underscores, extra colons, surrounding component whitespace,
control characters, and non-ASCII identifier characters are rejected.

Formatting uses `format=auto` by default. If `clang-format` is on `PATH`,
protocyte uses it for generated C++ output. If it is unavailable and no
explicit formatter setting is supplied, protocyte still emits generated files
without failing. Implicit style discovery is anchored to the caller's working
directory and delegated to clang-format through `--style=file`; Protocyte never
searches its own package or source tree for a consumer's `.clang-format`.
CMake's response-file transport preserves the directory containing the calling
`CMakeLists.txt` as the plugin invocation directory, so clang-format searches
that source directory and its ancestors. Direct `protoc` callers should invoke
it from the intended project directory or pass `clang_format_config` explicitly.

`format=auto` is a convenience mode, not a byte-for-byte reproducibility
guarantee across machines or clang-format versions. Projects that check
generated files into source control should either use `format=off`, or use
`format=required` with a project-pinned formatter version and configuration.

CMake users can forward non-runtime parameters through the existing `OPTIONS`
argument on `protocyte_generate(...)` or `protocyte_add_proto_library(...)`.
Absolute Windows and POSIX formatter paths are safe in `OPTIONS`; include
prefixes remain relative virtual directories. Runtime state is the exception:
use the dedicated `EMIT_RUNTIME` and `RUNTIME_PREFIX` arguments so CMake can
declare the emitted runtime header and runtime linkage consistently. Forwarded
`runtime` and `runtime_prefix` parameters are rejected.

For example, size-sensitive builds can disable generated documentation with
`OPTIONS "comments=off"`. Direct `.proto` generation normally receives source
information from `protoc`; descriptor-set generation emits comments only when
the set was created with `--include_source_info`.

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
`generate_response()` does not opt into the example limits above. When a
request requires formatting, a policy with `format_outputs=False` rejects the
request rather than silently returning unformatted output.

Before model construction, `generate_response()` validates structural
descriptor invariants such as field numbers and uniqueness, labels, oneof and
proto3-optional membership, reserved ranges, and canonical map-entry shapes.
Malformed requests return a contextual response error without generated files.

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

For singular `bytes` fields with `protocyte.array`, the schema bound owns the
field's storage policy. Bounded fields accept at most the declared size, and
`fixed: true` fields accept exactly that size. These inline fields do not use
`Limits::max_string_bytes`; in particular, mutable access to fixed storage is
infallible and always returns the declared extent. `max_total_bytes` still
bounds aggregate wire input during parsing.

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
non-allocating, so `create(ctx)` returns the message directly. Primitive scalar
setters also return `void`. Operations that can fail, including allocation,
parsing, serialization, strings, bytes, containers, and deep copies, return
`[[nodiscard]]` `::protocyte::Status` or `::protocyte::Result<T>` values.

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
hook. The public `::protocyte::ReaderLike` concept checks this contract at the
generated API boundary. `position()` is an absolute byte coordinate within the
top-level input; reader adapters must preserve that coordinate rather than
restarting at zero.
`SliceReader(data, size, base_offset)` accepts an optional source base for
subranges. `ReaderRef`, `ParseBudgetReader`, `LimitedReader`, and staged map
readers preserve the wrapped reader's coordinate. Parse readers passed between
generated nested messages additionally expose `consume_repeated_elements(count,
field_number)` and `consume_map_entries(count, field_number)`, both returning
`::protocyte::Status`. `ParseBudgetReader` owns those counters; `ReaderRef` and
`LimitedReader` forward them unconditionally.

For contiguous bytes, `parse(ctx, input)` accepts
`::protocyte::Span<const ::protocyte::u8>` directly. Compatible lvalue ranges
such as byte arrays, `std::array`, `std::vector`, and `std::span` convert to that
dynamic span automatically; the overload creates a `SliceReader` and delegates
to the same reader-based parser.

Writers passed to generated `serialize()` are required to expose
`can_write(count)`, `write_byte(value)`, and `write(data, count)`.
`can_write(count)` returns `bool`, does not consume output capacity, and is part
of the writer contract rather than an optional bulk-write optimization. The
public `::protocyte::WriterLike` concept checks this contract.
`SliceWriter(data, size, base_offset)` implements this contract and accepts the
same optional absolute base for a subrange.

`serialize(writer)` is incremental, not transactional. It validates the message
before writing, but once writing begins, any later failure (including insufficient
capacity or a failed `write_byte()` or `write()` call) leaves bytes from earlier
successful calls committed; Protocyte does not rewind the writer. Callers that
require all-or-nothing output should serialize into a contiguous staging buffer
first or provide a writer that stages or rolls back its output.

For contiguous writable bytes, `serialize(output)` accepts
`::protocyte::Span<::protocyte::u8>` and compatible mutable lvalue ranges. It
returns the number of bytes written. The helper computes the encoded size first,
so an undersized output returns `ErrorCode::size_limit` without modifying the
buffer, then delegates the actual write to `serialize(writer)`.

Generated messages are move-only. Ordinary C++ copying is deleted because it
cannot report allocation failure.

Common generated operations include:

- `create(ctx)`
- `parse(ctx, reader)`, `parse(ctx, input_bytes)`, and `parse(reader, output)`
- `merge_from(reader)`
- `serialize(writer)` and `serialize(output_bytes)`
- `encoded_size()`
- `copy_from(source)` and `copy_from(source, staging_message)`
- `clone()` and `clone(output)`
- field accessors, `has_*()`, `set_*()`, `mutable_*()`, and `ensure_*()` where applicable

### Error Diagnostics

Runtime and generated failures remain allocation-free and reflection-free:

```cpp
struct Error {
    ErrorCode code {};
    usize offset {};
    u32 field_number {};
};
```

The numeric members have these contracts:

- `code` identifies the failure category through `ErrorCode`.
- `offset` is the absolute reader or writer position in the top-level byte
  coordinate. It is `0` when the failure has no meaningful I/O position, such
  as validation, API misuse, or an allocation failure outside parsing. It is
  never a container size or element index.
- `field_number` identifies the field on the message operation that returned
  the failure. Nested message failures are contained by their outer field, and
  map-entry key/value failures identify the public map field rather than the
  synthetic entry fields `1` or `2`. It is `0` when no message field is known.

No field names, nested paths, source identifiers, or formatted diagnostic
strings are stored in `Error`. Applications that need names can map the numeric
field themselves; doing so is separate from the core runtime and is not needed
for these diagnostics. Custom field-aware helpers can use
`::protocyte::with_field(error_or_result, field_number)` to apply the same
containment rule.

### Unknown Fields

Unknown-field preservation is compile-time configurable and disabled by
default. Enable it on a config used to instantiate generated messages:

```cpp
struct ForwardCompatibleConfig : protocyte::DefaultConfig {
    static constexpr bool preserve_unknown_fields = true;
};

using Sample = demo::Sample<ForwardCompatibleConfig>;
```

This is useful for a proxy built against an older schema: it can parse a
message produced by a newer service, change a field it understands, and
forward the message without deleting fields introduced by that newer service.

When enabled, each message keeps unknown occurrences in encounter order as
canonical protobuf wire bytes. Generated messages expose
`unknown_fields()`, `unknown_field_count()`, `unknown_field_bytes()`, and
`clear_unknown_fields()`. `UnknownFieldRange::field(index)` and iteration
provide lazy `UnknownFieldView` values with `field_number()`, `wire_type()`,
`tag()`, protobuf-style `type()`, `varint()`, `fixed32()`, `fixed64()`,
`length_delimited()`, and `group()` accessors:

```cpp
for (const auto field : message.unknown_fields()) {
    if (field.wire_type() == protocyte::WireType::VARINT) {
        const auto value = field.varint();
        // value is Result<uint64_t>
    }
}
```

`mutable_unknown_fields()` is available only when preservation is enabled. It
returns a typed façade supporting `add_*`, `replace_*`, `erase`,
`delete_subrange`, `delete_by_number`, `merge_from`, and `clear`; writable raw
bytes are intentionally not exposed. Mutations and individual parse captures
roll back on allocation, input, recursion, or size-limit failure. Raw encoded
ranges passed to `merge_from` or `add_group` are validated against the
destination context's recursion policy and canonicalized before commit.

Unknown fields serialize after known fields. Their relative encounter order is
retained, but parsing and serialization canonicalize tags and scalar values, so
this API does not promise byte-identical forwarding. Unknown fields and
incompatible wire types inside map-entry messages are discarded while the
remaining key and value are materialized. An undeclared closed-enum map value
instead preserves the complete outer map occurrence as unknown and does not
insert the entry, matching protobuf's native map representation.

The disabled storage specialization is empty and generated messages apply
`PROTOCYTE_NO_UNIQUE_ADDRESS` (`[[msvc::no_unique_address]]` on MSVC and
`[[no_unique_address]]` elsewhere), so the default policy adds no message
object footprint. Enabling preservation uses `Config::Vector<u8>` and is
bounded independently by `Limits::max_unknown_field_bytes`, including copies
between messages with different contexts.

### Caller-Controlled Message Storage

Copying, cloning, and parsing each have a convenience form and a
caller-supplied-storage form:

```cpp
Status copy_from(const Message& source);
Status copy_from(const Message& source, Message& staging_message);

Result<Message> clone() const;
Status clone(Message& output) const;

static Result<Message> parse(Context& ctx, Reader& reader);
static Status parse(Reader& reader, Message& output);
```

The convenience forms are concise for hosted applications, but may materialize
one complete generated message in automatic storage. That can be undesirable
for large schemas and especially for kernel code with a small stack. The
reference-taking variants create no full outer-message temporary internally:

```cpp
demo::Sample<> staging_message{ctx};
if (const auto st = destination.copy_from(source, staging_message); !st) {
    // destination is unchanged
}

demo::Sample<> output{ctx};
auto clone_status = source.clone(output);

protocyte::SliceReader reader{encoded, encoded_size};
auto parse_status = demo::Sample<>::parse(reader, output);
```

The caller decides where `staging_message` and `output` live: stack, static
storage, an arena, or a kernel-appropriate pool. Protocyte neither allocates nor
deallocates those outer objects.

`copy_from(source, staging_message)` uses `staging_message` as transactional
working state. The destination remains unchanged on failure; after success the
staging message is valid but moved-from. It must not alias either copy operand.
`clone()` binds its result to the source message's context. `clone(output)` and
`parse(reader, output)` retain the context supplied when `output` was
constructed. Both reference-taking operations reset and directly populate
`output`; on failure, `output` is reset to an empty message bound to that same
destination context.

A message's context binding is non-owning. The `Context`, its allocator state,
and any state referenced by its allocator callbacks must outlive every message
bound to it. Moving or cloning a message does not extend those lifetimes.

This only controls storage for the outer message object. Dynamic strings,
bytes, vectors, maps, and boxed messages still allocate through `Config` and
its caller-supplied context. Protocyte uses heap storage only when that context
is configured with a heap-backed allocator.

### Parse Resource Limits

`protocyte::Limits` separates protobuf-compatible wire limits from optional
application resource policy:

- `max_total_bytes` defaults to `0x7fffffff` and bounds all wire bytes read or
  skipped by one top-level `parse` or `merge_from` call,
  including nested and unknown fields. This matches protobuf C++
  `CodedInputStream`'s default `INT_MAX` total-byte limit.
- `max_recursion_depth` defaults to `100`, matching protobuf C++.
- `max_message_bytes` bounds individual embedded messages.
- `max_string_bytes` bounds dynamically stored string and bytes values,
  including individual elements of repeated bytes fields. Singular inline
  `bytes` fields using `protocyte.array` instead use their schema-declared
  bound, or exact extent with `fixed: true`.
- `max_unknown_field_bytes` defaults to `0x7fffffff` and bounds canonical
  unknown-field bytes retained by each message when
  `Config::preserve_unknown_fields` is enabled. The limit is separate from
  `max_string_bytes`, while all input still counts against `max_total_bytes`.
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
helpers are compiled only when `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR` is set to a
nonzero value, which is intended for tests and examples rather than kernel
builds.

The runtime provides:

- `Status` and `Result<T>`
- allocator-aware vectors, strings/bytes, optionals, boxes, and maps
- bounded byte and array storage helpers
- slice readers and writers
- protobuf tag, varint, fixed-width, skip, scalar parse, and scalar serialize helpers

Reflection tables are emitted only when `PROTOCYTE_ENABLE_REFLECTION` is set to
a nonzero value. Release builds do not get descriptor pools or dynamic
reflection.
