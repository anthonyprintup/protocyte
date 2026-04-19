cmake_minimum_required(VERSION 3.24)

project(protocyte_find_package_demo LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

set(FIND_PACKAGE_PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(FIND_PACKAGE_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

protocyte_generate(
    TARGET find_package_proto_codegen
    PROTO_ROOT "${FIND_PACKAGE_PROTO_ROOT}"
    OUT_DIR "${FIND_PACKAGE_GENERATED_DIR}"
    DISCOVER
    EMIT_RUNTIME
    GENERATED_SOURCES_VAR FIND_PACKAGE_GENERATED_SOURCES
)

add_library(find_package_proto STATIC)
target_sources(find_package_proto PRIVATE ${FIND_PACKAGE_GENERATED_SOURCES})
add_dependencies(find_package_proto find_package_proto_codegen)
target_include_directories(find_package_proto PUBLIC "${FIND_PACKAGE_GENERATED_DIR}")
target_compile_definitions(find_package_proto PUBLIC PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
target_compile_features(find_package_proto PUBLIC cxx_std_20)

if(MSVC)
    target_compile_options(find_package_proto PRIVATE /W4 /permissive-)
else()
    target_compile_options(find_package_proto PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(find_package_demo src/main.cpp)
target_link_libraries(find_package_demo PRIVATE find_package_proto)
target_compile_features(find_package_demo PRIVATE cxx_std_20)

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
