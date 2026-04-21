cmake_minimum_required(VERSION 3.24)

project(protocyte_smoke LANGUAGES CXX)

option(PROTOCYTE_SMOKE_REGENERATE "Regenerate checked protocyte output with protoc." OFF)
option(PROTOCYTE_SMOKE_FETCH_PROTOBUF "Fetch and build protobuf when protoc is not installed." ON)
option(PROTOCYTE_SMOKE_BUILD_DRIVER "Build the WDK kernel driver smoke test." OFF)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

set(PROTOCYTE_REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/..")
set(PROTOCYTE_SMOKE_PROTO_DIR "${CMAKE_CURRENT_LIST_DIR}/proto")
set(PROTOCYTE_EXAMPLE_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/example.proto")
set(PROTOCYTE_COMPAT_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/compat.proto")
set(PROTOCYTE_CROSS_PACKAGE_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/cross_package.proto")
set(PROTOCYTE_GENERATED_DIR "${CMAKE_CURRENT_LIST_DIR}/generated")
set(PROTOCYTE_GENERATED_FILES
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/compat.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/compat.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/cross_package.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/cross_package.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.hpp"
    "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.cpp"
)

if(PROTOCYTE_SMOKE_REGENERATE)
    set(PROTOCYTE_FETCH_PROTOBUF "${PROTOCYTE_SMOKE_FETCH_PROTOBUF}")
else()
    set(PROTOCYTE_FETCH_PROTOBUF OFF)
endif()
add_subdirectory("${PROTOCYTE_REPO_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/protocyte")

if(PROTOCYTE_SMOKE_REGENERATE)
    protocyte_generate(
        TARGET protocyte_smoke_example_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_EXAMPLE_PROTO}"
        EMIT_RUNTIME
    )

    protocyte_generate(
        TARGET protocyte_smoke_compat_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_COMPAT_PROTO}"
        OPTIONS "namespace_prefix=protocyte_smoke"
    )

    protocyte_generate(
        TARGET protocyte_smoke_cross_package_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_CROSS_PACKAGE_PROTO}"
    )

    add_custom_target(protocyte_smoke_regenerate)
    add_dependencies(
        protocyte_smoke_regenerate
        protocyte_smoke_example_codegen
        protocyte_smoke_compat_codegen
        protocyte_smoke_cross_package_codegen
    )
endif()

FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.7.1
)
FetchContent_MakeAvailable(Catch2)

add_executable(protocyte_host_smoke
    src/host_smoke.cpp
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/compat.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/cross_package.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.cpp"
)
target_include_directories(protocyte_host_smoke PRIVATE "${PROTOCYTE_GENERATED_DIR}")
target_compile_definitions(protocyte_host_smoke PRIVATE PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
target_compile_features(protocyte_host_smoke PRIVATE cxx_std_20)
target_link_libraries(protocyte_host_smoke PRIVATE Catch2::Catch2WithMain)

if(PROTOCYTE_SMOKE_REGENERATE)
    add_dependencies(protocyte_host_smoke protocyte_smoke_regenerate)
endif()

if(MSVC)
    target_compile_options(protocyte_host_smoke PRIVATE /W4 /permissive-)
else()
    target_compile_options(protocyte_host_smoke PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
include(Catch)
catch_discover_tests(protocyte_host_smoke)

if(PROTOCYTE_SMOKE_BUILD_DRIVER)
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
    find_package(WDK REQUIRED)

    wdk_add_driver(protocyte_kernel_smoke
        src/kernel_driver_smoke.cpp
        "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
        "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.cpp"
    )
    target_include_directories(protocyte_kernel_smoke PRIVATE "${PROTOCYTE_GENERATED_DIR}")
    target_compile_features(protocyte_kernel_smoke PRIVATE cxx_std_20)
    target_compile_options(protocyte_kernel_smoke PRIVATE /std:c++20 /permissive- /W4)

    if(PROTOCYTE_SMOKE_REGENERATE)
        add_dependencies(protocyte_kernel_smoke protocyte_smoke_regenerate)
    endif()
endif()
