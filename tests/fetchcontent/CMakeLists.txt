cmake_minimum_required(VERSION 3.24)

project(protocyte_fetchcontent_demo LANGUAGES CXX)

include(FetchContent)

FetchContent_Declare(
    protocyte
    SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/../.."
)
FetchContent_MakeAvailable(protocyte)

set(FETCHCONTENT_PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(FETCHCONTENT_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

protocyte_add_proto_library(
    TARGET fetchcontent_proto
    PROTO_ROOT "${FETCHCONTENT_PROTO_ROOT}"
    OUT_DIR "${FETCHCONTENT_GENERATED_DIR}"
    DISCOVER
    HOSTED_ALLOCATOR
)

if(MSVC)
    target_compile_options(fetchcontent_proto PRIVATE /W4 /permissive-)
else()
    target_compile_options(fetchcontent_proto PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(fetchcontent_demo src/main.cpp)
target_link_libraries(fetchcontent_demo PRIVATE fetchcontent_proto)
target_compile_features(fetchcontent_demo PRIVATE cxx_std_20)

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
