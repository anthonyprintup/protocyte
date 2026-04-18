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
set(PROTOCYTE_EXAMPLE_PROTO "${CMAKE_CURRENT_LIST_DIR}/example.proto")
set(PROTOCYTE_OPTIONS_PROTO "${PROTOCYTE_REPO_ROOT}/src/protocyte/proto/protocyte/options.proto")
set(PROTOCYTE_OPTIONS_ROOT "${PROTOCYTE_REPO_ROOT}/src/protocyte/proto")
set(PROTOCYTE_GENERATED_DIR "${CMAKE_CURRENT_LIST_DIR}/generated")
set(PROTOCYTE_GENERATOR_SOURCES
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/__init__.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/cpp.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/errors.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/main.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/model.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/parameters.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/plugin.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/runtime.py"
)
set(PROTOCYTE_GENERATED_FILES
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.hpp"
    "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.cpp"
)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

if(PROTOCYTE_SMOKE_REGENERATE)
    find_program(PROTOC_EXECUTABLE protoc)

    if(NOT PROTOC_EXECUTABLE AND PROTOCYTE_SMOKE_FETCH_PROTOBUF)
        set(protobuf_BUILD_TESTS OFF CACHE BOOL "" FORCE)
        set(protobuf_BUILD_CONFORMANCE OFF CACHE BOOL "" FORCE)
        set(protobuf_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
        set(protobuf_BUILD_PROTOBUF_BINARIES ON CACHE BOOL "" FORCE)
        FetchContent_Declare(
            protobuf
            GIT_REPOSITORY https://github.com/protocolbuffers/protobuf.git
            GIT_TAG v31.1
        )
        FetchContent_MakeAvailable(protobuf)
        set(PROTOC_EXECUTABLE "$<TARGET_FILE:protoc>")
    endif()

    if(NOT PROTOC_EXECUTABLE)
        message(FATAL_ERROR "protoc was not found. Enable PROTOCYTE_SMOKE_FETCH_PROTOBUF or install protoc.")
    endif()

    if(WIN32)
        set(PROTOCYTE_PLUGIN_WRAPPER "${CMAKE_CURRENT_BINARY_DIR}/protoc-gen-protocyte.cmd")
        file(WRITE "${PROTOCYTE_PLUGIN_WRAPPER}"
            "@echo off\r\n"
            "set PYTHONPATH=${PROTOCYTE_REPO_ROOT}/src;%PYTHONPATH%\r\n"
            "\"${Python3_EXECUTABLE}\" -m protocyte.main\r\n"
        )
    else()
        set(PROTOCYTE_PLUGIN_WRAPPER "${CMAKE_CURRENT_BINARY_DIR}/protoc-gen-protocyte")
        file(WRITE "${PROTOCYTE_PLUGIN_WRAPPER}"
            "#!/usr/bin/env sh\n"
            "PYTHONPATH='${PROTOCYTE_REPO_ROOT}/src':$PYTHONPATH exec '${Python3_EXECUTABLE}' -m protocyte.main\n"
        )
        file(CHMOD "${PROTOCYTE_PLUGIN_WRAPPER}" PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
    endif()

    add_custom_command(
        OUTPUT ${PROTOCYTE_GENERATED_FILES}
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${PROTOCYTE_GENERATED_DIR}"
        COMMAND "${PROTOC_EXECUTABLE}"
            "--proto_path=${CMAKE_CURRENT_LIST_DIR}"
            "--proto_path=${PROTOCYTE_OPTIONS_ROOT}"
            "--plugin=protoc-gen-protocyte=${PROTOCYTE_PLUGIN_WRAPPER}"
            "--protocyte_out=runtime=emit:${PROTOCYTE_GENERATED_DIR}"
            "${PROTOCYTE_EXAMPLE_PROTO}"
        DEPENDS
            "${PROTOCYTE_EXAMPLE_PROTO}"
            "${PROTOCYTE_OPTIONS_PROTO}"
            ${PROTOCYTE_GENERATOR_SOURCES}
        WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
        VERBATIM
    )

    add_custom_target(protocyte_smoke_regenerate DEPENDS ${PROTOCYTE_GENERATED_FILES})
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
