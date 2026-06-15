cmake_minimum_required(VERSION 3.24)

project(protocyte_smoke LANGUAGES CXX)

option(PROTOCYTE_SMOKE_REGENERATE "Regenerate checked protocyte output with protoc." OFF)
option(PROTOCYTE_SMOKE_FETCH_PROTOBUF "Fetch and build protobuf when protoc is not installed." ON)
option(PROTOCYTE_SMOKE_BUILD_DRIVER "Build the WDK kernel driver smoke test." OFF)
option(PROTOCYTE_SMOKE_BUILD_BENCHMARKS "Build Protocyte marshalling benchmarks." OFF)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
include(CheckCXXSourceCompiles)

set(PROTOCYTE_REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../..")
set(PROTOCYTE_SMOKE_PROTO_DIR "${CMAKE_CURRENT_LIST_DIR}/proto")
set(PROTOCYTE_EXAMPLE_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/example.proto")
set(PROTOCYTE_COMPAT_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/compat.proto")
set(PROTOCYTE_CROSS_PACKAGE_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/cross_package.proto")
set(PROTOCYTE_BENCHMARK_PROTO "${PROTOCYTE_SMOKE_PROTO_DIR}/benchmark.proto")
set(PROTOCYTE_GENERATED_DIR "${CMAKE_CURRENT_LIST_DIR}/generated")
set(
    PROTOCYTE_SMOKE_CLANG_FORMAT
    ""
    CACHE FILEPATH
    "Explicit clang-format executable for smoke code generation."
)
set(
    PROTOCYTE_SMOKE_CLANG_FORMAT_CONFIG
    "${PROTOCYTE_REPO_ROOT}/.clang-format"
    CACHE FILEPATH
    "clang-format config used for smoke code generation."
)
set(PROTOCYTE_GENERATED_FILES
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/compat.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/compat.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/cross_package.protocyte.hpp"
    "${PROTOCYTE_GENERATED_DIR}/cross_package.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/protocyte/runtime/runtime.hpp"
)

check_cxx_source_compiles([=[
#include <version>
#if !defined(__cpp_lib_format) || __cpp_lib_format < 201907L
#error "std::format is unavailable"
#endif
#include <format>
#include <string_view>
#include <type_traits>

int main() {
    using Formatter = ::std::formatter<::std::string_view, char>;
    static_assert(::std::is_default_constructible_v<Formatter>);
    const auto formatted = ::std::format("{}", ::std::string_view {"ok"});
    return formatted == "ok" ? 0 : 1;
}
]=] PROTOCYTE_SMOKE_HAS_STD_FORMAT)

function(protocyte_smoke_enable_std_format_if_available target_name)
    if(PROTOCYTE_SMOKE_HAS_STD_FORMAT)
        target_compile_definitions("${target_name}" PRIVATE PROTOCYTE_ENABLE_STD_FORMAT=1)
    endif()
endfunction()

if(PROTOCYTE_SMOKE_REGENERATE OR PROTOCYTE_SMOKE_BUILD_BENCHMARKS)
    set(PROTOCYTE_FETCH_PROTOBUF "${PROTOCYTE_SMOKE_FETCH_PROTOBUF}")
else()
    set(PROTOCYTE_FETCH_PROTOBUF OFF)
endif()
add_subdirectory("${PROTOCYTE_REPO_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/protocyte")

if(PROTOCYTE_SMOKE_REGENERATE)
    if(PROTOCYTE_SMOKE_CLANG_FORMAT)
        set(protocyte_smoke_clang_format "${PROTOCYTE_SMOKE_CLANG_FORMAT}")
    else()
        set(protocyte_smoke_clang_format_hints)
        if(WIN32)
            list(APPEND protocyte_smoke_clang_format_hints "$ENV{ProgramFiles}/LLVM/bin")
            list(APPEND protocyte_smoke_clang_format_hints "$ENV{ProgramW6432}/LLVM/bin")
        endif()
        find_program(
            protocyte_smoke_clang_format
            NAMES clang-format clang-format.exe
            HINTS ${protocyte_smoke_clang_format_hints}
            REQUIRED
        )
    endif()
    if(NOT EXISTS "${PROTOCYTE_SMOKE_CLANG_FORMAT_CONFIG}")
        message(
            FATAL_ERROR
            "PROTOCYTE_SMOKE_CLANG_FORMAT_CONFIG does not exist: ${PROTOCYTE_SMOKE_CLANG_FORMAT_CONFIG}"
        )
    endif()
    set(
        PROTOCYTE_SMOKE_FORMAT_OPTIONS
        "clang_format=${protocyte_smoke_clang_format}"
        "clang_format_config=${PROTOCYTE_SMOKE_CLANG_FORMAT_CONFIG}"
    )

    protocyte_generate(
        TARGET protocyte_smoke_example_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_EXAMPLE_PROTO}"
        EMIT_RUNTIME
        OPTIONS ${PROTOCYTE_SMOKE_FORMAT_OPTIONS}
    )

    protocyte_generate(
        TARGET protocyte_smoke_compat_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_COMPAT_PROTO}"
        OPTIONS ${PROTOCYTE_SMOKE_FORMAT_OPTIONS} "namespace_prefix=protocyte_smoke"
    )

    protocyte_generate(
        TARGET protocyte_smoke_cross_package_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_CROSS_PACKAGE_PROTO}"
        OPTIONS ${PROTOCYTE_SMOKE_FORMAT_OPTIONS}
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
FetchContent_GetProperties(Catch2 SOURCE_DIR protocyte_smoke_catch2_source_dir)
list(APPEND CMAKE_MODULE_PATH "${protocyte_smoke_catch2_source_dir}/extras")

if(PROTOCYTE_SMOKE_BUILD_BENCHMARKS)
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_GTEST_TESTS OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_INSTALL_DOCS OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_INSTALL_TOOLS OFF CACHE BOOL "" FORCE)
    if(WIN32)
        set(CMAKE_USE_WIN32_THREADS_INIT ON CACHE BOOL "" FORCE)
        set(CMAKE_USE_PTHREADS_INIT OFF CACHE BOOL "" FORCE)
        set(CMAKE_THREAD_LIBS_INIT "" CACHE STRING "" FORCE)
        set(HAVE_LIB_RT OFF CACHE BOOL "" FORCE)
    endif()
    FetchContent_Declare(
        benchmark
        GIT_REPOSITORY https://github.com/google/benchmark.git
        GIT_TAG v1.9.5
    )
    FetchContent_MakeAvailable(benchmark)

    set(protobuf_MSVC_STATIC_RUNTIME OFF CACHE BOOL "" FORCE)
    protocyte_setup_codegen()
    if(NOT TARGET protobuf::libprotobuf AND NOT TARGET libprotobuf)
        find_package(Protobuf CONFIG QUIET)
    endif()
    if(NOT TARGET protobuf::libprotobuf AND NOT TARGET libprotobuf)
        find_package(Protobuf MODULE QUIET)
    endif()
    if(NOT TARGET protobuf::libprotobuf AND NOT TARGET libprotobuf AND PROTOCYTE_SMOKE_FETCH_PROTOBUF)
        set(protobuf_BUILD_TESTS OFF CACHE BOOL "" FORCE)
        set(protobuf_BUILD_CONFORMANCE OFF CACHE BOOL "" FORCE)
        set(protobuf_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
        set(protobuf_BUILD_PROTOBUF_BINARIES ON CACHE BOOL "" FORCE)
        FetchContent_Declare(
            protobuf
            GIT_REPOSITORY https://github.com/protocolbuffers/protobuf.git
            GIT_TAG "${PROTOCYTE_PROTOBUF_GIT_TAG}"
        )
        FetchContent_MakeAvailable(protobuf)
        set(PROTOCYTE_PROTOC_EXECUTABLE "$<TARGET_FILE:protobuf::protoc>" CACHE INTERNAL "protoc executable for protocyte")
    endif()
    set(PROTOCYTE_PROTOCYTE_BENCHMARK_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated/protocyte")
    set(PROTOCYTE_PROTOCYTE_BENCHMARK_HEADER "${PROTOCYTE_PROTOCYTE_BENCHMARK_GENERATED_DIR}/benchmark.protocyte.hpp")
    set(PROTOCYTE_PROTOCYTE_BENCHMARK_SOURCE "${PROTOCYTE_PROTOCYTE_BENCHMARK_GENERATED_DIR}/benchmark.protocyte.cpp")
    protocyte_generate(
        TARGET protocyte_smoke_benchmark_codegen
        PROTO_ROOT "${PROTOCYTE_SMOKE_PROTO_DIR}"
        OUT_DIR "${PROTOCYTE_PROTOCYTE_BENCHMARK_GENERATED_DIR}"
        PROTOS "${PROTOCYTE_BENCHMARK_PROTO}"
        OPTIONS "namespace_prefix=protocyte_smoke"
    )

    set(PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated/protobuf")
    set(PROTOCYTE_PROTOBUF_BENCHMARK_HEADER "${PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR}/benchmark.pb.h")
    set(PROTOCYTE_PROTOBUF_BENCHMARK_SOURCE "${PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR}/benchmark.pb.cc")
    add_custom_command(
        OUTPUT
            "${PROTOCYTE_PROTOBUF_BENCHMARK_HEADER}"
            "${PROTOCYTE_PROTOBUF_BENCHMARK_SOURCE}"
        COMMAND
            "${CMAKE_COMMAND}" -E make_directory "${PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR}"
        COMMAND
            ${PROTOCYTE_PROTOC_EXECUTABLE}
            "--proto_path=${PROTOCYTE_SMOKE_PROTO_DIR}"
            "--cpp_out=${PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR}"
            "${PROTOCYTE_BENCHMARK_PROTO}"
        DEPENDS "${PROTOCYTE_BENCHMARK_PROTO}"
        COMMENT "Generating protobuf benchmark C++ sources"
        VERBATIM
    )
    add_custom_target(
        protocyte_smoke_protobuf_benchmark_codegen
        DEPENDS
            "${PROTOCYTE_PROTOBUF_BENCHMARK_HEADER}"
            "${PROTOCYTE_PROTOBUF_BENCHMARK_SOURCE}"
    )
    set_source_files_properties(
        "${PROTOCYTE_PROTOBUF_BENCHMARK_SOURCE}"
        PROPERTIES
            COMPILE_OPTIONS "$<$<CXX_COMPILER_ID:Clang>:-Wno-invalid-offsetof>"
    )

    if(TARGET protobuf::libprotobuf)
        set(protocyte_smoke_libprotobuf_target protobuf::libprotobuf)
    elseif(TARGET libprotobuf)
        set(protocyte_smoke_libprotobuf_target libprotobuf)
    else()
        message(FATAL_ERROR "protobuf benchmark requires a libprotobuf CMake target")
    endif()
endif()

add_executable(protocyte_host_smoke
    src/host_smoke.cpp
    "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/compat.protocyte.cpp"
    "${PROTOCYTE_GENERATED_DIR}/cross_package.protocyte.cpp"
)
target_include_directories(protocyte_host_smoke PRIVATE "${PROTOCYTE_GENERATED_DIR}")
target_compile_definitions(
    protocyte_host_smoke
    PRIVATE
        PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1
        PROTOCYTE_ENABLE_STD_STRING_VIEW=1
)
protocyte_smoke_enable_std_format_if_available(protocyte_host_smoke)
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

if(PROTOCYTE_SMOKE_BUILD_BENCHMARKS)
    add_executable(protocyte_host_benchmark
        src/host_benchmark.cpp
        "${PROTOCYTE_PROTOCYTE_BENCHMARK_SOURCE}"
    )
    target_include_directories(
        protocyte_host_benchmark
        PRIVATE
            "${PROTOCYTE_GENERATED_DIR}"
            "${PROTOCYTE_PROTOCYTE_BENCHMARK_GENERATED_DIR}"
    )
    target_compile_definitions(
        protocyte_host_benchmark
        PRIVATE
            PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1
            PROTOCYTE_ENABLE_STD_STRING_VIEW=1
    )
    protocyte_smoke_enable_std_format_if_available(protocyte_host_benchmark)
    target_compile_features(protocyte_host_benchmark PRIVATE cxx_std_20)
    target_link_libraries(protocyte_host_benchmark PRIVATE benchmark::benchmark_main)

    if(PROTOCYTE_SMOKE_REGENERATE)
        add_dependencies(protocyte_host_benchmark protocyte_smoke_regenerate)
    endif()
    add_dependencies(protocyte_host_benchmark protocyte_smoke_benchmark_codegen)

    if(MSVC)
        target_compile_options(protocyte_host_benchmark PRIVATE /W4 /permissive-)
    else()
        target_compile_options(protocyte_host_benchmark PRIVATE -Wall -Wextra -Wpedantic)
    endif()

    add_executable(protocyte_host_protobuf_benchmark
        src/protobuf_benchmark.cpp
        "${PROTOCYTE_PROTOBUF_BENCHMARK_SOURCE}"
    )
    target_include_directories(
        protocyte_host_protobuf_benchmark
        PRIVATE
            "${PROTOCYTE_GENERATED_DIR}"
            "${PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR}"
    )
    target_compile_definitions(
        protocyte_host_protobuf_benchmark
        PRIVATE
            PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1
            PROTOCYTE_ENABLE_STD_STRING_VIEW=1
    )
    protocyte_smoke_enable_std_format_if_available(protocyte_host_protobuf_benchmark)
    target_compile_features(protocyte_host_protobuf_benchmark PRIVATE cxx_std_20)
    target_link_libraries(
        protocyte_host_protobuf_benchmark
        PRIVATE
            benchmark::benchmark_main
            "${protocyte_smoke_libprotobuf_target}"
    )
    add_dependencies(protocyte_host_protobuf_benchmark protocyte_smoke_protobuf_benchmark_codegen)

    if(PROTOCYTE_SMOKE_REGENERATE)
        add_dependencies(protocyte_host_protobuf_benchmark protocyte_smoke_regenerate)
    endif()

    if(MSVC)
        target_compile_options(protocyte_host_protobuf_benchmark PRIVATE /W4 /permissive-)
    else()
        target_compile_options(protocyte_host_protobuf_benchmark PRIVATE -Wall -Wextra -Wpedantic)
    endif()

    add_executable(protocyte_host_benchmark_smoke
        src/benchmark_compat_smoke.cpp
        "${PROTOCYTE_PROTOCYTE_BENCHMARK_SOURCE}"
        "${PROTOCYTE_PROTOBUF_BENCHMARK_SOURCE}"
    )
    target_include_directories(
        protocyte_host_benchmark_smoke
        PRIVATE
            "${PROTOCYTE_GENERATED_DIR}"
            "${PROTOCYTE_PROTOCYTE_BENCHMARK_GENERATED_DIR}"
            "${PROTOCYTE_PROTOBUF_BENCHMARK_GENERATED_DIR}"
    )
    target_compile_definitions(
        protocyte_host_benchmark_smoke
        PRIVATE
            PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1
            PROTOCYTE_ENABLE_STD_STRING_VIEW=1
    )
    protocyte_smoke_enable_std_format_if_available(protocyte_host_benchmark_smoke)
    target_compile_features(protocyte_host_benchmark_smoke PRIVATE cxx_std_20)
    target_link_libraries(
        protocyte_host_benchmark_smoke
        PRIVATE
            Catch2::Catch2WithMain
            "${protocyte_smoke_libprotobuf_target}"
    )
    add_dependencies(
        protocyte_host_benchmark_smoke
        protocyte_smoke_benchmark_codegen
        protocyte_smoke_protobuf_benchmark_codegen
    )

    if(PROTOCYTE_SMOKE_REGENERATE)
        add_dependencies(protocyte_host_benchmark_smoke protocyte_smoke_regenerate)
    endif()

    if(MSVC)
        target_compile_options(protocyte_host_benchmark_smoke PRIVATE /W4 /permissive-)
    else()
        target_compile_options(protocyte_host_benchmark_smoke PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endif()

enable_testing()
include(Catch)
catch_discover_tests(protocyte_host_smoke)
if(PROTOCYTE_SMOKE_BUILD_BENCHMARKS)
    catch_discover_tests(protocyte_host_benchmark_smoke)
endif()

if(PROTOCYTE_SMOKE_BUILD_DRIVER)
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake")
    find_package(WDK REQUIRED)

    wdk_add_driver(protocyte_kernel_smoke
        src/kernel_driver_smoke.cpp
        "${PROTOCYTE_GENERATED_DIR}/example.protocyte.cpp"
    )
    target_include_directories(protocyte_kernel_smoke PRIVATE "${PROTOCYTE_GENERATED_DIR}")
    target_compile_definitions(protocyte_kernel_smoke PRIVATE PROTOCYTE_ENABLE_STD_STRING_VIEW=1)
    target_compile_features(protocyte_kernel_smoke PRIVATE cxx_std_20)
    target_compile_options(protocyte_kernel_smoke PRIVATE /std:c++20 /permissive- /W4)

    if(PROTOCYTE_SMOKE_REGENERATE)
        add_dependencies(protocyte_kernel_smoke protocyte_smoke_regenerate)
    endif()
endif()
