cmake_minimum_required(VERSION 3.24)

project(protocyte_hell_demo LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

set(HELL_PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(HELL_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

protocyte_generate(
    TARGET hell_proto_codegen
    PROTO_ROOT "${HELL_PROTO_ROOT}"
    OUT_DIR "${HELL_GENERATED_DIR}"
    DISCOVER
    EMIT_RUNTIME
    GENERATED_SOURCES_VAR HELL_GENERATED_SOURCES
)

add_library(hell_proto STATIC)
target_sources(hell_proto PRIVATE ${HELL_GENERATED_SOURCES})
add_dependencies(hell_proto hell_proto_codegen)
target_include_directories(hell_proto PUBLIC "${HELL_GENERATED_DIR}")
target_compile_definitions(hell_proto PUBLIC PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
target_compile_features(hell_proto PUBLIC cxx_std_20)

if(MSVC)
    target_compile_options(hell_proto PRIVATE /W4 /permissive-)
else()
    target_compile_options(hell_proto PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(hell_demo src/main.cpp)
target_link_libraries(hell_demo PRIVATE hell_proto)
target_compile_features(hell_demo PRIVATE cxx_std_20)

if(MSVC)
    target_compile_options(hell_demo PRIVATE /W4 /permissive-)
else()
    target_compile_options(hell_demo PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_test(NAME hell_demo COMMAND hell_demo)
set_tests_properties(
    hell_demo
    PROPERTIES
        PASS_REGULAR_EXPRESSION "Header: 080112024f4b\r?\nEnvelope: 0a06080112024f4b1096011a03686579"
)
