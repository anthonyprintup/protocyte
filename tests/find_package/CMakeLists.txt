cmake_minimum_required(VERSION 3.24)

project(protocyte_find_package_demo LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

set(FIND_PACKAGE_PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(FIND_PACKAGE_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

protocyte_add_proto_library(
    TARGET find_package_proto
    PROTO_ROOT "${FIND_PACKAGE_PROTO_ROOT}"
    OUT_DIR "${FIND_PACKAGE_GENERATED_DIR}"
    DISCOVER
    HOSTED_ALLOCATOR
)

get_property(
    protocyte_managed_plugin
    GLOBAL PROPERTY PROTOCYTE_INTERNAL_MANAGED_PLUGIN_EXECUTABLE
)
if(NOT EXISTS "${protocyte_managed_plugin}")
    message(FATAL_ERROR "find_package did not provision the managed Protocyte Python plugin")
endif()
cmake_path(
    IS_PREFIX PROTOCYTE_PYTHON_ENV_ROOT
    "${protocyte_managed_plugin}"
    NORMALIZE
    protocyte_plugin_is_managed
)
if(NOT protocyte_plugin_is_managed)
    message(FATAL_ERROR "find_package plugin is outside PROTOCYTE_PYTHON_ENV_ROOT: ${protocyte_managed_plugin}")
endif()
if(EXISTS "${PROTOCYTE_PYTHON_PROJECT_ROOT}/build")
    message(FATAL_ERROR "find_package provisioning modified the installed Python project with a build directory")
endif()
if(EXISTS "${PROTOCYTE_PYTHON_SOURCE_ROOT}/protocyte.egg-info")
    message(FATAL_ERROR "find_package provisioning modified the installed Python project with egg-info")
endif()

if(MSVC)
    target_compile_options(find_package_proto PRIVATE /W4 /permissive-)
else()
    target_compile_options(find_package_proto PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(find_package_demo src/main.cpp)
target_link_libraries(find_package_demo PRIVATE find_package_proto)
target_compile_features(find_package_demo PRIVATE cxx_std_20)

set(FIND_PACKAGE_INSTALL_MARKER "${CMAKE_CURRENT_BINARY_DIR}/find-package-consumer.txt")
file(WRITE "${FIND_PACKAGE_INSTALL_MARKER}" "find_package consumer\n")
install(
    FILES "${FIND_PACKAGE_INSTALL_MARKER}"
    DESTINATION "share/protocyte-integration"
)

if(MSVC)
    target_compile_options(find_package_demo PRIVATE /W4 /permissive-)
else()
    target_compile_options(find_package_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME find_package_demo COMMAND find_package_demo)
set_tests_properties(
    find_package_demo
    PROPERTIES
        PASS_REGULAR_EXPRESSION "Header: 080112024f4b\r?\nEnvelope: 0a06080112024f4b1096011a03686579"
)
