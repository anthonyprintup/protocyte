cmake_minimum_required(VERSION 3.24)

project(protocyte_fetchcontent_demo LANGUAGES CXX)

include(FetchContent)

set(PROTOCYTE_PYTHON_ENV_ROOT "consumer-managed-python")
FetchContent_Declare(
    protocyte
    SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/../.."
)
FetchContent_MakeAvailable(protocyte)

set(expected_protocyte_python_env_root "${CMAKE_BINARY_DIR}/consumer-managed-python")
cmake_path(NORMAL_PATH expected_protocyte_python_env_root)
get_property(
    protocyte_internal_python_env_root
    GLOBAL PROPERTY PROTOCYTE_INTERNAL_PYTHON_ENV_ROOT
)
get_property(
    protocyte_cached_python_env_root
    CACHE PROTOCYTE_PYTHON_ENV_ROOT
    PROPERTY VALUE
)
foreach(
    configured_root
    IN ITEMS
        "${PROTOCYTE_PYTHON_ENV_ROOT}"
        "${protocyte_internal_python_env_root}"
        "${protocyte_cached_python_env_root}"
)
    if(NOT configured_root STREQUAL expected_protocyte_python_env_root)
        message(
            FATAL_ERROR
            "FetchContent did not publish one canonical PROTOCYTE_PYTHON_ENV_ROOT: "
            "expected ${expected_protocyte_python_env_root}, got ${configured_root}"
        )
    endif()
endforeach()

set(FETCHCONTENT_PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(FETCHCONTENT_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

protocyte_add_proto_library(
    TARGET fetchcontent_proto
    ALIAS fetchcontent::proto
    PROTO_ROOT "${FETCHCONTENT_PROTO_ROOT}"
    OUT_DIR "${FETCHCONTENT_GENERATED_DIR}"
    DISCOVER
    HOSTED_ALLOCATOR
)

get_property(
    protocyte_managed_plugin
    GLOBAL PROPERTY PROTOCYTE_INTERNAL_MANAGED_PLUGIN_EXECUTABLE
)
if(NOT EXISTS "${protocyte_managed_plugin}")
    message(FATAL_ERROR "FetchContent did not provision the managed Protocyte Python plugin")
endif()
cmake_path(
    IS_PREFIX PROTOCYTE_PYTHON_ENV_ROOT
    "${protocyte_managed_plugin}"
    NORMALIZE
    protocyte_plugin_is_managed
)
if(NOT protocyte_plugin_is_managed)
    message(FATAL_ERROR "FetchContent plugin is outside PROTOCYTE_PYTHON_ENV_ROOT: ${protocyte_managed_plugin}")
endif()

if(NOT TARGET fetchcontent::proto)
    message(FATAL_ERROR "protocyte_add_proto_library did not create the requested alias target")
endif()

if(MSVC)
    target_compile_options(fetchcontent_proto PRIVATE /W4 /permissive-)
else()
    target_compile_options(fetchcontent_proto PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(fetchcontent_demo src/main.cpp)
target_link_libraries(fetchcontent_demo PRIVATE fetchcontent::proto)
target_compile_features(fetchcontent_demo PRIVATE cxx_std_20)

set(FETCHCONTENT_INSTALL_MARKER "${CMAKE_CURRENT_BINARY_DIR}/fetchcontent-consumer.txt")
file(WRITE "${FETCHCONTENT_INSTALL_MARKER}" "fetchcontent consumer\n")
install(
    FILES "${FETCHCONTENT_INSTALL_MARKER}"
    DESTINATION "share/protocyte-integration"
)

if(MSVC)
    target_compile_options(fetchcontent_demo PRIVATE /W4 /permissive-)
else()
    target_compile_options(fetchcontent_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME fetchcontent_demo COMMAND fetchcontent_demo)
set_tests_properties(
    fetchcontent_demo
    PROPERTIES
        PASS_REGULAR_EXPRESSION "Header: 080112024f4b\r?\nEnvelope: 0a06080112024f4b1096011a03686579"
)
