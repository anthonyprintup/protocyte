# Protocyte End-to-End Guide

This document shows how to go from a fresh machine to a CMake target that
always rebuilds generated protocyte C++ when your `.proto` files change.

The smoke project in this repository is both:

- A runnable test project.
- A reference integration for using protocyte with `protoc` and CMake.

## What You Need

- Python 3.12 or newer.
- [uv](https://docs.astral.sh/uv/getting-started/installation/).
- A C++20-capable compiler.
- CMake 3.24 or newer.
- `protoc` from the Protocol Buffers project.

Verify the command-line prerequisites before continuing:

```console
uv --version
uv python find 3.12
cmake --version
protoc --version
```

Using `uv python find` avoids assuming that a POSIX installation exposes a
bare `python` command; many valid installations expose only `python3`. The
environment commands below always use an explicit `uv`-managed interpreter.

## 1. Install `protoc`

The canonical way to get `protoc` is to download a prebuilt release from the
Protocol Buffers project, unpack it somewhere on disk, and add its `bin`
directory to `PATH`. The official installation instructions are here:
[protobuf.dev/installation](https://protobuf.dev/installation/).

After that, this should work in a new shell:

```console
protoc --version
```

If you prefer, you can also install protobuf through your normal system package
manager instead of downloading a release archive manually. The important part
is that `protoc` is on `PATH` before you try to run code generation yourself.

Direct `protoc` commands always require a host-runnable `protoc` supplied by the
user. CMake source consumers using `FetchContent` or `add_subdirectory` default
`PROTOCYTE_FETCH_PROTOBUF` to `ON`, allowing them to fetch missing protobuf
import sources and, for native builds, a missing host `protoc`. Installed
`find_package(protocyte CONFIG REQUIRED)` consumers default that option to
`OFF` and must opt in explicitly. This repository's smoke regeneration and
benchmark paths expose the same fallback through
`PROTOCYTE_SMOKE_FETCH_PROTOBUF`.

## 2. Build And Install The Protocyte Python Package

Protocyte is a Python `protoc` plugin. `protoc` talks to it through the
`protoc-gen-protocyte` executable script that the Python package installs.
All of the Python packaging paths below require Python 3.12 or newer.

You have three normal ways to work with it.

### Option A: Use This Repository Checkout Directly

From the repository root:

```console
uv sync
```

That creates `.venv` and installs the `protoc-gen-protocyte` console script
into the virtual environment.

On Windows, the plugin executable will normally be here:

```text
<repo>\.venv\Scripts\protoc-gen-protocyte.exe
```

Select that environment's interpreter and, if you want `protoc` to discover the
plugin by name instead of passing an explicit `--plugin=...` path, prepend the
virtual environment to `PATH`:

```powershell
$python = "$PWD\.venv\Scripts\python.exe"
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
```

On a POSIX host, the plugin is `<repo>/.venv/bin/protoc-gen-protocyte`.
Select the matching interpreter and prepend that script directory in Bash with:

```bash
python="$PWD/.venv/bin/python"
export PATH="$PWD/.venv/bin:$PATH"
```

Both assignments capture an absolute interpreter path. Keep using that
`$python` value after moving into a separate consumer project; `uv run` resolves
its project from the current directory and would no longer select this checkout
environment there.

### Option B: Build A Wheel And Install It Somewhere Else

From the repository root:

```console
uv build
```

That produces a wheel under `dist/`. Install that wheel into the Python
environment you want to use for code generation. The following commands create
an isolated environment rather than modifying an ambient or system-managed
Python installation. In PowerShell:

```powershell
$wheel = (Get-ChildItem dist\protocyte-*.whl | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
uv venv build\plugin-venv --python 3.12
$python = "$PWD\build\plugin-venv\Scripts\python.exe"
uv pip install --python $python $wheel
```

In Bash:

```bash
wheel=$(ls -t dist/protocyte-*.whl | head -n 1)
uv venv build/plugin-venv --python 3.12
python="$PWD/build/plugin-venv/bin/python"
uv pip install --python "$python" "$wheel"
```

The corresponding plugin entry point is
`build\plugin-venv\Scripts\protoc-gen-protocyte.exe` on Windows and
`build/plugin-venv/bin/protoc-gen-protocyte` on POSIX hosts.

`uv build` also produces a source distribution under `dist/`. Both the wheel
and the sdist are plugin-only artifacts for `protoc-gen-protocyte`; they do
not provide the CMake package used by `find_package(protocyte CONFIG REQUIRED)`.

Protocyte has not published its first tag or
[GitHub release](https://github.com/anthonyprintup/protocyte/releases) yet. The
release workflow is prepared to publish these three asset types in the future:

- `protocyte-X.Y.Z-py3-none-any.whl`: install this into Python 3.12+ when you
  want the plugin executable.
- `protocyte-X.Y.Z.tar.gz`: the Python source distribution for the same plugin
  package. This is not the CMake package.
- `protocyte-X.Y.Z-cmake-prefix.tar.gz`: a preinstalled CMake prefix for
  `find_package(protocyte CONFIG REQUIRED)`.

For prerelease tags `vX.Y.Z-rcN`, the wheel and sdist use the normalized Python
package version `X.Y.ZrcN`, while the CMake prefix archive keeps the Git tag
spelling `X.Y.Z-rcN`.

### Option C: Install The CMake Package

If you want downstream CMake projects to consume protocyte through
`find_package(protocyte CONFIG REQUIRED)`, install the CMake package into a
prefix:

After the first release, you can download
`protocyte-X.Y.Z-cmake-prefix.tar.gz` from GitHub Releases, unpack it, and use
the extracted directory as your `CMAKE_PREFIX_PATH`. Until then, install from a
source checkout with one of the following blocks.

PowerShell:

```powershell
cmake -S . -B build/protocyte
cmake --install build/protocyte --prefix "$PWD\build\protocyte-prefix"
```

Bash:

```bash
cmake -S . -B build/protocyte
cmake --install build/protocyte --prefix "$PWD/build/protocyte-prefix"
```

That install prefix contains:

- the complete public CMake integration, including `protocyte_add_proto_library(...)`
- an installable copy of the protocyte Python generator project and its pinned CMake constraints
- `protocyte/options.proto`

Downstream consumers then configure with the matching
`-DCMAKE_PREFIX_PATH=<repo>/build/protocyte-prefix` and call
`find_package(protocyte CONFIG REQUIRED)`.

The installed package still expects a usable Python 3.12+ base interpreter at
configure time. When code generation is first requested, it creates a
fingerprinted virtual environment under `PROTOCYTE_PYTHON_ENV_ROOT` in the build
tree and installs protocyte plus its pinned Python dependencies there from a
writable staged copy. The installed CMake prefix and global or user-site Python
packages are not modified. A host-runnable `protoc` and required protobuf import
sources are caller-supplied by default. For native builds, set
`PROTOCYTE_FETCH_PROTOBUF=ON` before calling
`find_package(protocyte CONFIG REQUIRED)` to fetch either missing input as a
fallback. Cross-compiling consumers must always supply the host-runnable
`protoc`, but can enable the same option to fetch missing import sources.

## 3. Find `protocyte/options.proto`

If your `.proto` files use protocyte's custom options, they must import:

```proto
import "protocyte/options.proto";
```

That means `protoc` also needs a `--proto_path` entry that points at the
directory containing the `protocyte/` folder.

In a local checkout, that directory is:

```text
<repo>\src\protocyte\proto
```

With either Option A or Option B, print it through the explicit interpreter
selected above. In PowerShell:

```powershell
& $python -c "from pathlib import Path; import protocyte; print(Path(protocyte.__file__).with_name('proto'))"
```

In Bash:

```bash
"$python" -c "from pathlib import Path; import protocyte; print(Path(protocyte.__file__).with_name('proto'))"
```

Use the printed path as one of your `--proto_path` values.

## 4. Write A Proto Tree

For a real project, treat `proto/` as a tree, not a single file. For example:

```text
proto/
  common/types.proto
  sensors/sensor.proto
```

`proto/common/types.proto`:

```proto
syntax = "proto3";

package demo.common;

message SampleHeader {
  uint32 version = 1;
}
```

`proto/sensors/sensor.proto`:

```proto
syntax = "proto3";

package demo.sensors;

import "common/types.proto";
import "protocyte/options.proto";

message SensorSample {
  demo.common.SampleHeader header = 1;
  bytes digest = 2 [(protocyte.array) = { max: 32, fixed: true }];
  repeated uint32 values = 3 [(protocyte.array) = { max: 16 }];
}
```

## 5. Run `protoc` Directly (Optional)

This is useful for checking the plugin or integrating with a non-CMake build.
The high-level CMake helper in the next section runs `protoc` for you and uses a
separate generated directory in the build tree, so normal CMake users can skip
this direct step.

Assume:

- Your project-local schemas live under `proto/`.
- Generated files should go into `generated/`.
- Protocyte comes from this repository checkout.

PowerShell example that generates code for every `.proto` file under `proto/`:

```powershell
$repo = "C:\path\to\protocyte"
$protoSrc = "$PWD\proto"
$outDir = "$PWD\generated"
$protocyteProto = "$repo\src\protocyte\proto"
$plugin = "$repo\.venv\Scripts\protoc-gen-protocyte.exe"
$protoFiles = Get-ChildItem -Path $protoSrc -Recurse -Filter *.proto | ForEach-Object { $_.FullName }
New-Item -ItemType Directory -Force $outDir | Out-Null

protoc `
  --proto_path=$protoSrc `
  --proto_path=$protocyteProto `
  --plugin=protoc-gen-protocyte=$plugin `
  --protocyte_out=runtime=emit:$outDir `
  $protoFiles
```

Bash example for the same checkout and proto tree:

```bash
repo="/path/to/protocyte"
proto_src="$PWD/proto"
out_dir="$PWD/generated"
protocyte_proto="$repo/src/protocyte/proto"
plugin="$repo/.venv/bin/protoc-gen-protocyte"
proto_files=()
while IFS= read -r -d '' file; do
  proto_files+=("$file")
done < <(find "$proto_src" -type f -name '*.proto' -print0)
mkdir -p "$out_dir"

protoc \
  "--proto_path=$proto_src" \
  "--proto_path=$protocyte_proto" \
  "--plugin=protoc-gen-protocyte=$plugin" \
  "--protocyte_out=runtime=emit:$out_dir" \
  "${proto_files[@]}"
```

If `protoc-gen-protocyte` is already on `PATH`, you can omit the
`--plugin=...` argument and let `protoc` find it automatically.

The generated layout mirrors the source-relative proto paths:

- `generated/common/types.protocyte.hpp`
- `generated/common/types.protocyte.cpp`
- `generated/sensors/sensor.protocyte.hpp`
- `generated/sensors/sensor.protocyte.cpp`
- `generated/protocyte/runtime/runtime.hpp`

`runtime=emit` tells protocyte to emit its runtime support header together with
the generated message code. For one generated-code bundle per build tree, that
is usually the simplest setup for a header-only runtime.

## 6. Generate And Link With CMake

Use `protocyte_add_proto_library(...)` as the primary integration. It owns the
generated output list, code-generation target, generated C++ library, include
directory, C++20 requirement, runtime linkage, and import dependencies. This is
the complete minimal consumer after installing the CMake package from Option C:

<!-- ground-zero-cmake-start -->
```cmake
cmake_minimum_required(VERSION 3.24)
project(protocyte_demo LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

protocyte_add_proto_library(
    TARGET sensor_proto
    ALIAS demo::sensor_proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(app src/main.cpp)
target_link_libraries(app PRIVATE demo::sensor_proto)
```
<!-- ground-zero-cmake-end -->

Configure that project with
`-DCMAKE_PREFIX_PATH=<repo>/build/protocyte-prefix`. For a local source checkout
instead, replace `find_package(...)` with this block; the remaining target code
stays unchanged:

```cmake
include(FetchContent)
FetchContent_Declare(
    protocyte
    SOURCE_DIR "/absolute/path/to/protocyte"
)
FetchContent_MakeAvailable(protocyte)
```

`DISCOVER` follows additions and removals under `PROTO_ROOT`. The helper also
tracks transitive imports and generator inputs, creates `OUT_DIR`, and declares
Protocyte's escaped or path-budgeted output names exactly as the generator will
write them. `HOSTED_ALLOCATOR` selects the reusable malloc-backed runtime for
this hosted example. Freestanding and kernel targets should omit it and provide
their own allocator callbacks through the runtime config they instantiate.

If you provide a non-default runtime `Config`, generated messages use:

- `Config::Context` with `allocator`, `limits`, and `recursion_depth`.
- `Config::Vector<T>` with `reserve`, `push_back`, iteration, `size`, `data`,
  and `value_type` for repeated fields.
- `Config::Map<K, V>`, `Config::Box<T>`, `Config::Optional<T>`,
  `Config::Bytes`, and `Config::String` storage types.

Unknown fields are discarded by default. Set
`static constexpr bool preserve_unknown_fields = true` on the config to retain
and inspect them. The enabled path stores canonical wire bytes in
`Config::Vector<u8>` and observes `ctx.limits.max_unknown_field_bytes`; the
disabled path adds no message object footprint. Hosted smoke coverage exercises
typed mutation, self-aliasing views, canonical raw-range merges, recursion and
byte limits, packed closed-enum atomicity, and protobuf-compatible map-entry
unknown handling.

For untrusted input, set the resource policy on `ctx.limits` before parsing.
`max_total_bytes` and `max_recursion_depth` default to protobuf C++'s
`INT_MAX` and `100` behavior. `max_repeated_elements` and `max_map_entries`
are additional application-policy budgets shared across packed chunks, nested
messages, and duplicate map occurrences in one top-level parse. Lowering those
count budgets can intentionally reject otherwise valid protobuf messages.
`DefaultConfig` also supports a finite `max_total_allocation_bytes` budget
against live allocator-requested bytes for the whole context. It is unbounded by
default so normal parsing remains wire-compatible; custom configs should apply
an equivalent policy in their allocation hooks when they need the same
guarantee. Allocators without a deallocation callback retain their charged bytes.

Scalar `Config::Vector<T>` implementations must provide
`append_trivial_range(values, count)` and `resize_for_overwrite(count)` returning
`::protocyte::Status`. The runtime uses these primitives for packed scalar
commit and transactional fixed-width reads; vectors do not read from readers
directly.

Custom readers passed to generated parsing must provide `eof()`, `position()`,
`can_read(count)`, `read_byte()`, `read(out, count)`, and `skip(count)`.
`can_read(count)` returns `::protocyte::Status` without consuming input; it is a
required reader operation, not an optional packed-field optimization.
`position()` must remain in the top-level input coordinate through nested
reader adapters. `SliceReader` accepts an optional third `base_offset` argument
when it represents a subrange.
Parse readers passed between nested generated messages also provide
`consume_repeated_elements(count, field_number)` and
`consume_map_entries(count, field_number)`. `ParseBudgetReader` implements the
budgets and the nested reader adapters forward them directly.

Custom writers passed to generated serialization must provide
`can_write(count)`, `write_byte(value)`, and `write(data, count)`.
`can_write(count)` returns `bool` without consuming output capacity; it is a
required writer operation, not an optional packed-field optimization.
`SliceWriter` accepts the same optional `base_offset` argument for subranges.

Descriptor-set generation is the preferred path when descriptors were recovered
from a binary and rendered `.proto` files are only inspection artifacts. First
produce a descriptor set with imports. In PowerShell:

```powershell
$protoRoot = "$PWD\proto"
$protocyteProtoDir = & $python -c "from pathlib import Path; import protocyte; print(Path(protocyte.__file__).with_name('proto'))"
$descriptorSet = "$PWD\build\descriptor_set.pb"
New-Item -ItemType Directory -Force (Split-Path -Parent $descriptorSet) | Out-Null

protoc `
  --proto_path=$protoRoot `
  --proto_path=$protocyteProtoDir `
  --include_imports `
  --include_source_info `
  --descriptor_set_out=$descriptorSet `
  "$protoRoot\sensors\sensor.proto"
```

In Bash:

```bash
proto_root="$PWD/proto"
protocyte_proto_dir=$("$python" -c "from pathlib import Path; import protocyte; print(Path(protocyte.__file__).with_name('proto'))")
descriptor_set="$PWD/build/descriptor_set.pb"
mkdir -p "$(dirname "$descriptor_set")"

protoc \
  "--proto_path=$proto_root" \
  "--proto_path=$protocyte_proto_dir" \
  --include_imports \
  --include_source_info \
  "--descriptor_set_out=$descriptor_set" \
  "$proto_root/sensors/sensor.proto"
```

Then generate from descriptor names inside that set:

```cmake
protocyte_add_descriptor_set_library(
    TARGET sensor_proto
    ALIAS demo::sensor_proto
    DESCRIPTOR_SET "${CMAKE_CURRENT_BINARY_DIR}/descriptor_set.pb"
    FILES sensors/sensor.proto
    OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated"
    HOSTED_ALLOCATOR
)
```

In descriptor-set mode, `FILES`/`PROTOS` entries are not filesystem paths.
`--include_source_info` preserves schema comments so Protocyte can embed them as
Doxygen documentation. Descriptor sets created without it still generate valid
C++, but their generated declarations have no schema documentation.
Imports, including `google/protobuf/*.proto`, are resolved from the descriptor
set itself. Unreferenced runtime descriptors stay dependency-only under
`DISCOVER`; referenced runtime message/enum descriptors are generated when
selected files need their generated types.

If protobuf is not already available to that consumer project and you want
protocyte to fetch it, set `PROTOCYTE_FETCH_PROTOBUF=ON` before
`find_package(protocyte CONFIG REQUIRED)`.

## 7. Use The Generated Headers In C++

Once the target above is in place, your C++ code includes the generated headers
using their source-relative paths under the generated include root:

```cpp
#include <vector>

#include <protocyte/runtime/runtime.hpp>
#include "common/types.protocyte.hpp"
#include "sensors/sensor.protocyte.hpp"

int main() {
    auto ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };

    auto sample = demo::sensors::SensorSample<>::create(ctx);
    if (const auto status = sample.mutable_values().push_back(42u); !status) {
        return 1;
    }

    const auto size = sample.encoded_size();
    if (!size) {
        return 1;
    }

    std::vector<protocyte::u8> encoded(*size);
    const auto written = sample.serialize(encoded);
    if (!written) {
        return 1;
    }

    const auto parsed = demo::sensors::SensorSample<>::parse(ctx, encoded);
    if (!parsed) {
        return 1;
    }
    if ((*parsed).values().size() != 1u || (*parsed).values()[0] != 42u) {
        return 1;
    }

    return 0;
}
```

That example assumes `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1` was defined for the
target. If not, replace `protocyte::hosted_allocator()` with your own allocator
callbacks. Every failed `Status` or `Result<T>` exposes its structured
`code`, `offset`, and `field_number` through `.error()`; the compiled
[root quick-start example](../../examples/quickstart/main.cpp) demonstrates
reporting those values instead of discarding the failure.

## 8. Keep Generated Code Up To Date Automatically

The high-level helper in section 6 teaches the build graph what generation owns:

- `DISCOVER` reconfigures when `.proto` files are added or removed beneath
  `PROTO_ROOT`.
- Protocyte scans each selected source's transitive imports, so changing an
  imported `.proto` reruns generation without duplicating that graph in
  `DEPENDS`.
- The selected plugin, generator Python sources, options schema, response file,
  and `protoc` tool are generation inputs.
- Generated paths use the same escaping and Visual Studio path budgeting as the
  generator itself.
- The generated library depends on its private code-generation target, so C++
  compilation does not race stale or missing outputs.

Use the helper's `DEPENDS` argument only for project-specific prerequisites that
Protocyte cannot infer, such as another target that creates a descriptor set.
The lower-level `protocyte_generate(...)` API is available when a project needs
to own the C++ target itself, but it should not be the first integration copied
by a new user.

## 9. Run The Smoke Project In This Repository

The repository's full smoke presets are Windows-specific and live in
`tests/smoke/CMakePresets.json`. Run the preset-based configure, build, and test
commands from the `tests/smoke/` directory. Linux and macOS users can run the
portable quick-start commands in the root README; CI runs that path on Linux.

On Windows, open a Visual Studio Developer PowerShell or otherwise initialize
the MSVC developer environment first. The presets use the standard
`VCINSTALLDIR`, `VSINSTALLDIR`, and `WindowsSdkVerBinPath` environment
variables from that shell instead of hard-coding one specific Visual Studio
edition or Windows SDK version.

Build and run the hosted smoke test:

```powershell
Push-Location tests/smoke
cmake --preset windows-clangcl-ninja
cmake --build --preset windows-clangcl-ninja
ctest --preset windows-clangcl-ninja
Pop-Location
```

Regenerate the checked-in smoke fixtures:

```powershell
Push-Location tests/smoke
cmake --preset windows-clangcl-ninja -DPROTOCYTE_SMOKE_REGENERATE=ON
cmake --build build/clangcl --target protocyte_smoke_regenerate
Pop-Location
```

Build the optional WDK driver smoke target:

```powershell
Push-Location tests/smoke
cmake --preset windows-clangcl-ninja-driver
cmake --build --preset windows-clangcl-ninja-driver
Pop-Location
```

For downstream integration, copy the complete high-level example in section 6.
The smoke project is a broader repository-internal reference for advanced
fixtures and runtime coverage:

- [`tests/smoke/CMakeLists.txt`](./CMakeLists.txt) shows regeneration wiring.
- [`tests/smoke/proto/example.proto`](./proto/example.proto) shows protocyte options.
- [`tests/smoke/src/host_smoke.cpp`](./src/host_smoke.cpp) shows generated-code usage.
