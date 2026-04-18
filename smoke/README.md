# Protocyte Smoke Project

This project keeps a checked-in protocyte output fixture for `example.proto` and
builds two smoke targets:

- `protocyte_host_smoke`: a user-mode C++20 executable that serializes and
  deserializes `test.ultimate.UltimateComplexMessage`.
- `protocyte_kernel_smoke`: an optional WDK kernel driver that uses an
  `ExAllocatePool2` allocator and performs the same protobuf round trip in
  `DriverEntry`.

Configure and run the host smoke test:

```powershell
cmake --preset windows-clangcl-ninja -S smoke
cmake --build --preset windows-clangcl-ninja
ctest --preset windows-clangcl-ninja
```

Build the driver smoke test:

```powershell
cmake --preset windows-clangcl-ninja-driver -S smoke
cmake --build --preset windows-clangcl-ninja-driver
```

Refresh the checked generated output from `example.proto`:

```powershell
cmake --preset windows-clangcl-ninja -S smoke -DPROTOCYTE_SMOKE_REGENERATE=ON
cmake --build smoke/build/clangcl --target protocyte_smoke_regenerate
```

If `protoc` is unavailable, the regenerate target fetches protobuf with CMake
`FetchContent` and builds the `protoc` binary locally.
