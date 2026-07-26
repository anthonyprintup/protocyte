# Getting Started

This walkthrough builds a small hosted C++20 application, generates protobuf code during the CMake build, serializes a value, parses it, and verifies the round trip.

Protocyte is consumed through CMake `FetchContent`. You do not need to install the Protocyte plugin globally or invoke `protoc` yourself.

## What You Will Build

```text
protocyte-quickstart/
|-- CMakeLists.txt
|-- main.cpp
`-- proto/
    `-- reading.proto
```

The finished project contains:

- one protobuf message;
- one generated static library;
- one executable linked to that library;
- one CTest round-trip test.

## Requirements

Install:

- CMake 3.24 or newer;
- a C++20 compiler;
- Python 3.12 or newer;
- Git.

Python must provide the standard-library `venv` and `ensurepip` modules:

```console
python --version
python -c "import ensurepip, venv"
```

On Debian or Ubuntu, install `python3-venv` or the matching version-specific package if that check fails.

The first configuration requires network access unless the Python packages and protobuf sources are already available locally. Run CMake from an environment in which your intended compiler is available—for example, a Visual Studio Developer PowerShell on Windows.

## 1. Create the Schema

Create `proto/reading.proto`:

```proto
syntax = "proto3";

package demo.quickstart;

message Reading {
  uint32 value = 1;
}
```

## 2. Add Protocyte to CMake

Create `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.24)

project(protocyte_quickstart LANGUAGES CXX)

include(FetchContent)

FetchContent_Declare(
    protocyte
    GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
    GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14
)
FetchContent_MakeAvailable(protocyte)

protocyte_add_proto_library(
    TARGET quickstart_proto
    ALIAS quickstart::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(protocyte_quickstart main.cpp)
target_link_libraries(protocyte_quickstart PRIVATE quickstart::proto)
target_compile_features(protocyte_quickstart PRIVATE cxx_std_20)

enable_testing()
add_test(
    NAME protocyte_getting_started
    COMMAND protocyte_quickstart
)
```

The full commit SHA is intentional: Protocyte is pre-1.0 and has not published its first release. Pin a reviewed immutable revision rather than tracking `main`. Once a release exists, prefer its immutable release tag.

`HOSTED_ALLOCATOR` selects Protocyte's hosted runtime target. It is convenient for the first build and can later be replaced with application-owned allocation and storage.

## 3. Use the Generated Message

Create `main.cpp`:

```cpp
#include <cstdio>
#include <vector>

#include <protocyte/runtime/runtime.hpp>

#include "reading.protocyte.hpp"

namespace {
    int report_error(const char *operation, const protocyte::Error &error, const int exit_code) {
        std::fprintf(stderr, "%s failed: code=%u offset=%llu field=%u\n", operation, static_cast<unsigned>(error.code),
                     static_cast<unsigned long long>(error.offset), static_cast<unsigned>(error.field_number));
        return exit_code;
    }
} // namespace

int main() {
    auto encode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    auto reading = demo::quickstart::Reading<>::create(encode_ctx);
    reading.set_value(42u);

    const auto size = reading.encoded_size();
    if (!size) {
        return report_error("encoded_size", size.error(), 1);
    }

    std::vector<protocyte::u8> encoded(*size);
    const auto written = reading.serialize(encoded);
    if (!written) {
        return report_error("serialize", written.error(), 2);
    }
    if (*written != encoded.size()) {
        std::fputs("serialize returned an unexpected byte count\n", stderr);
        return 2;
    }

    auto decode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    const auto parsed = demo::quickstart::Reading<>::parse(decode_ctx, encoded);
    if (!parsed) {
        return report_error("parse", parsed.error(), 3);
    }
    if ((*parsed).value() != 42u) {
        std::fputs("parsed value did not match the encoded value\n", stderr);
        return 3;
    }

    return 0;
}
```

Protocyte operations that can fail return result objects. This example checks each result before accessing its value and prints structured error information when an operation fails.

## 4. Configure, Build, and Test

### PowerShell

From the project directory:

```powershell
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

If CMake does not select the intended Python installation, configure with an explicit interpreter:

```powershell
cmake -S . -B build "-DPython3_EXECUTABLE=C:\Path\To\Python312\python.exe"
```

### Linux, macOS, or Another POSIX Host

From the project directory:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

To select a particular Python installation:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE=/path/to/python3.12
```

A successful run ends with output similar to:

```text
1/1 Test #1: protocyte_getting_started ... Passed

100% tests passed, 0 tests failed out of 1
```

## What CMake Did

During configuration and build, Protocyte:

1. made its CMake functions and runtime targets available through `FetchContent`;
2. selected Python 3.12 or newer;
3. created a fingerprinted Python environment under the build tree;
4. installed the Protocyte generator and its locked Python dependencies into that environment;
5. located a usable protobuf compiler and import tree, fetching the native-build fallback when necessary;
6. discovered `proto/reading.proto`;
7. generated `reading.protocyte.hpp` and `reading.protocyte.cpp`;
8. compiled those files into `quickstart_proto`;
9. linked the generated library and hosted runtime into the executable.

The generated message files are placed under:

```text
build/quickstart_proto_protocyte/
```

Changing an existing schema automatically regenerates the affected outputs. Adding or removing a `.proto` file beneath `PROTO_ROOT` causes CMake to reconfigure because this example uses `DISCOVER`.

## Next Steps

- Read [CMake Integration](https://github.com/anthonyprintup/protocyte/wiki/CMake-Integration) before integrating Protocyte into a larger build.
- See [Code Generation](https://github.com/anthonyprintup/protocyte/wiki/Code-Generation) for explicit source lists, descriptor sets, and direct `protoc` usage.
- Continue with [Embedded and Freestanding](https://github.com/anthonyprintup/protocyte/wiki/Embedded-and-Freestanding) to replace the hosted allocator and standard containers.
- Review [Errors, Limits, and Wire Behavior](https://github.com/anthonyprintup/protocyte/wiki/Errors-Limits-and-Wire-Behavior) before processing untrusted payloads.
- Use [Troubleshooting](https://github.com/anthonyprintup/protocyte/wiki/Troubleshooting) if dependency provisioning or tool discovery fails.
