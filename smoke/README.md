# Protocyte End-to-End Guide

This document shows how to go from a fresh machine to a CMake target that
always rebuilds generated protocyte C++ when your `.proto` files change.

The smoke project in this repository is both:

- A runnable test project.
- A reference integration for using protocyte with `protoc` and CMake.

## What You Need

- Python 3.14 or newer.
- A C++20-capable compiler.
- CMake 3.24 or newer.
- `protoc` from the Protocol Buffers project.

Verify that `protoc` is installed:

```powershell
protoc --version
```

## 1. Install `protoc`

The canonical way to get `protoc` is to download a prebuilt release from the
Protocol Buffers project, unpack it somewhere on disk, and add its `bin`
directory to `PATH`. The official installation instructions are here:
[protobuf.dev/installation](https://protobuf.dev/installation/).

After that, this should work in a new shell:

```powershell
protoc --version
```

If you prefer, you can also install protobuf through your normal system package
manager instead of downloading a release archive manually. The important part
is that `protoc` is on `PATH` before you try to run code generation yourself.

For this repository's smoke project only, `cmake` can also fetch and build
protobuf for the regeneration target when `protoc` is not already installed.
That fallback is convenient for the smoke tests, but for normal downstream
projects you should assume that `protoc` is an explicit tool dependency.

## 2. Build And Install The Protocyte Python Package

Protocyte is a Python `protoc` plugin. `protoc` talks to it through the
`protoc-gen-protocyte` executable script that the Python package installs.

You have two normal ways to work with it.

### Option A: Use This Repository Checkout Directly

From the repository root:

```powershell
uv sync
```

That creates `.venv` and installs the `protoc-gen-protocyte` console script
into the virtual environment.

On Windows, the plugin executable will normally be here:

```text
<repo>\.venv\Scripts\protoc-gen-protocyte.exe
```

If you want `protoc` to discover the plugin by name instead of passing an
explicit `--plugin=...` path, prepend the virtual environment to `PATH`:

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
```

### Option B: Build A Wheel And Install It Somewhere Else

From the repository root:

```powershell
uv build
```

That produces a wheel under `dist/`. Install that wheel into the Python
environment you want to use for code generation:

```powershell
python -m pip install dist\protocyte-<version>-py3-none-any.whl
```

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

In an installed Python environment, you can print it like this:

```powershell
python -c "from pathlib import Path; import protocyte; print(Path(protocyte.__file__).with_name('proto'))"
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
  bytes digest = 2 [(protocyte.array) = { max: 32 }, (protocyte.fixed) = true];
  repeated uint32 values = 3 [(protocyte.array) = { max: 16 }];
}
```

## 5. Run `protoc` With Protocyte

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

protoc `
  --proto_path=$protoSrc `
  --proto_path=$protocyteProto `
  --plugin=protoc-gen-protocyte=$plugin `
  --protocyte_out=runtime=emit:$outDir `
  $protoFiles
```

If `protoc-gen-protocyte` is already on `PATH`, you can omit the
`--plugin=...` argument and let `protoc` find it automatically.

The generated layout mirrors the source-relative proto paths:

- `generated/common/types.protocyte.hpp`
- `generated/common/types.protocyte.cpp`
- `generated/sensors/sensor.protocyte.hpp`
- `generated/sensors/sensor.protocyte.cpp`
- `generated/protocyte/runtime/runtime.hpp`
- `generated/protocyte/runtime/runtime.cpp`

`runtime=emit` tells protocyte to emit its runtime support files together with
the generated message code. For one generated-code bundle per build tree, that
is usually the simplest setup.

## 6. Use The Generated Files In CMake

The recommended pattern is:

- Generate into the build directory, not into source control.
- Treat the generated `.cpp` files as normal target sources.
- Add the generated directory to the include path.
- Make your consuming target depend on a dedicated codegen target.

This is the minimal shape for a project that discovers every `.proto` file
under `proto/` automatically, derives the generated output list from those
files, and builds a static library from all generated translation units:

```cmake
cmake_minimum_required(VERSION 3.24)
project(protocyte_demo LANGUAGES CXX)

find_program(PROTOC_EXECUTABLE protoc REQUIRED)

set(PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(PROTOCYTE_PROTO_DIR "C:/path/to/protocyte/src/protocyte/proto")
set(PROTOCYTE_PLUGIN "C:/path/to/protocyte/.venv/Scripts/protoc-gen-protocyte.exe")
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

file(GLOB_RECURSE PROJECT_PROTO_FILES CONFIGURE_DEPENDS "${PROTO_ROOT}/*.proto")
list(SORT PROJECT_PROTO_FILES)

if(NOT PROJECT_PROTO_FILES)
    message(FATAL_ERROR "No .proto files were found under ${PROTO_ROOT}")
endif()

set(PROTOCYTE_GENERATED_HEADERS)
set(PROTOCYTE_GENERATED_SOURCES)

foreach(PROTO_FILE IN LISTS PROJECT_PROTO_FILES)
    file(RELATIVE_PATH PROTO_REL "${PROTO_ROOT}" "${PROTO_FILE}")
    get_filename_component(PROTO_REL_DIR "${PROTO_REL}" DIRECTORY)
    get_filename_component(PROTO_STEM "${PROTO_REL}" NAME_WLE)

    if(PROTO_REL_DIR STREQUAL "")
        set(PROTOCYTE_BASE "${GENERATED_DIR}/${PROTO_STEM}.protocyte")
    else()
        set(PROTOCYTE_BASE "${GENERATED_DIR}/${PROTO_REL_DIR}/${PROTO_STEM}.protocyte")
    endif()

    list(APPEND PROTOCYTE_GENERATED_HEADERS "${PROTOCYTE_BASE}.hpp")
    list(APPEND PROTOCYTE_GENERATED_SOURCES "${PROTOCYTE_BASE}.cpp")
endforeach()

set(PROTOCYTE_RUNTIME_HEADER "${GENERATED_DIR}/protocyte/runtime/runtime.hpp")
set(PROTOCYTE_RUNTIME_SOURCE "${GENERATED_DIR}/protocyte/runtime/runtime.cpp")
set(PROTOCYTE_OUTPUTS
    ${PROTOCYTE_GENERATED_HEADERS}
    ${PROTOCYTE_GENERATED_SOURCES}
    "${PROTOCYTE_RUNTIME_HEADER}"
    "${PROTOCYTE_RUNTIME_SOURCE}"
)

add_custom_command(
    OUTPUT ${PROTOCYTE_OUTPUTS}
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND "${PROTOC_EXECUTABLE}"
        "--proto_path=${PROTO_ROOT}"
        "--proto_path=${PROTOCYTE_PROTO_DIR}"
        "--plugin=protoc-gen-protocyte=${PROTOCYTE_PLUGIN}"
        "--protocyte_out=runtime=emit:${GENERATED_DIR}"
        ${PROJECT_PROTO_FILES}
    DEPENDS
        ${PROJECT_PROTO_FILES}
        "${PROTOCYTE_PROTO_DIR}/protocyte/options.proto"
        "${PROTOCYTE_PLUGIN}"
    VERBATIM
    COMMAND_EXPAND_LISTS
)

add_custom_target(protocyte_codegen DEPENDS ${PROTOCYTE_OUTPUTS})

add_library(sensor_proto STATIC)
target_sources(sensor_proto PRIVATE
    ${PROTOCYTE_GENERATED_SOURCES}
    "${PROTOCYTE_RUNTIME_SOURCE}"
)
add_dependencies(sensor_proto protocyte_codegen)
target_include_directories(sensor_proto PUBLIC "${GENERATED_DIR}")
target_compile_features(sensor_proto PUBLIC cxx_std_20)

add_executable(app src/main.cpp)
target_link_libraries(app PRIVATE sensor_proto)
```

If your hosted build wants the default malloc-backed allocator helpers from the
runtime, also add:

```cmake
target_compile_definitions(sensor_proto PUBLIC PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
```

If you are targeting a freestanding or kernel environment, do not define that
macro. Instead, provide your own allocator callbacks through the runtime config
you instantiate in your C++ code.

## 7. Use The Generated Headers In C++

Once the target above is in place, your C++ code includes the generated headers
using their source-relative paths under the generated include root:

```cpp
#include <protocyte/runtime/runtime.hpp>
#include "common/types.protocyte.hpp"
#include "sensors/sensor.protocyte.hpp"

int main() {
    auto ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };

    auto sample = demo::sensors::SensorSample<>::create(ctx);
    if (!sample) {
        return 1;
    }

    return 0;
}
```

That example assumes `PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1` was defined for the
target. If not, replace `protocyte::hosted_allocator()` with your own allocator
callbacks.

## 8. Keep Generated Code Up To Date Automatically

The important part is not the `protoc` command itself. The important part is
teaching your build graph what the generated files depend on.

The pattern above works because:

- `add_custom_command(OUTPUT ...)` tells CMake exactly which files generation
  produces.
- `file(GLOB_RECURSE ... CONFIGURE_DEPENDS)` lets CMake pick up newly added or
  removed `.proto` files in the `proto/` tree on the next configure/build.
- `DEPENDS` lists every input that should trigger regeneration.
- The `foreach()` block turns the discovered proto list into the exact list of
  generated `*.protocyte.hpp` and `*.protocyte.cpp` outputs.
- `protocyte_codegen` gives you one stable target that can be depended on.
- `sensor_proto` depends on `protocyte_codegen`, so compilation never starts
  against stale generated sources.

Whenever any `.proto` file under `proto/` changes, the next
`cmake --build ...` reruns `protoc` before recompiling `sensor_proto`.

In a real project, also add these to `DEPENDS` when they matter:

- All imported `.proto` files from your project.
- `protocyte/options.proto` if you use protocyte extensions.
- The plugin executable or wrapper script you invoke with `--plugin=...`.
- Local protocyte generator source files if you are developing protocyte and
  the consumer in the same workspace.

The smoke project's [`CMakeLists.txt`](./CMakeLists.txt) shows that last case:
it makes regeneration depend on the generator's Python sources, so local
changes to protocyte itself also refresh the checked outputs.

## 9. Run The Smoke Project In This Repository

Build and run the hosted smoke test:

```powershell
cmake --preset windows-clangcl-ninja -S smoke
cmake --build --preset windows-clangcl-ninja
ctest --preset windows-clangcl-ninja
```

Regenerate the checked-in smoke fixtures:

```powershell
cmake --preset windows-clangcl-ninja -S smoke -DPROTOCYTE_SMOKE_REGENERATE=ON
cmake --build smoke/build/clangcl --target protocyte_smoke_regenerate
```

Build the optional WDK driver smoke target:

```powershell
cmake --preset windows-clangcl-ninja-driver -S smoke
cmake --build --preset windows-clangcl-ninja-driver
```

If you want a concrete reference, the smoke project is the best place to copy
from first:

- [`smoke/CMakeLists.txt`](./CMakeLists.txt) shows regeneration wiring.
- [`smoke/proto/example.proto`](./proto/example.proto) shows protocyte options.
- [`smoke/src/host_smoke.cpp`](./src/host_smoke.cpp) shows generated-code usage.
