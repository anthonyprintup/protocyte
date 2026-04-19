# Protocyte Smoke Project

This project keeps checked-in protocyte output fixtures for
`proto/example.proto` and builds two smoke targets:

- `protocyte_host_smoke`: a Catch2-based user-mode C++20 test binary that
  exercises `test.ultimate.UltimateComplexMessage` plus cross-message constant
  resolution cases.
- `protocyte_kernel_smoke`: an optional WDK kernel driver that uses an
  `ExAllocatePool2` allocator and performs the same protobuf round trip in
  `DriverEntry`.

Configure and run the host smoke test:

```powershell
cmake --preset windows-clangcl-ninja -S smoke
cmake --build --preset windows-clangcl-ninja
ctest --preset windows-clangcl-ninja
```

The host binary uses Catch2 via `FetchContent`, so a normal `ctest` run will
discover and execute the individual smoke cases.

Build the driver smoke test:

```powershell
cmake --preset windows-clangcl-ninja-driver -S smoke
cmake --build --preset windows-clangcl-ninja-driver
```

Refresh the checked generated output from `proto/example.proto`:

```powershell
cmake --preset windows-clangcl-ninja -S smoke -DPROTOCYTE_SMOKE_REGENERATE=ON
cmake --build smoke/build/clangcl --target protocyte_smoke_regenerate
```

If `protoc` is unavailable, the regenerate target fetches protobuf with CMake
`FetchContent` and builds the `protoc` binary locally.
