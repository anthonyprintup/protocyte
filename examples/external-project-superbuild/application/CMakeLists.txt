cmake_minimum_required(VERSION 3.24)

project(protocyte_external_application LANGUAGES CXX)

find_package(protocyte CONFIG REQUIRED)

protocyte_add_proto_library(
    TARGET application_proto
    ALIAS application::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(protocyte_external_application main.cpp)
target_link_libraries(
    protocyte_external_application
    PRIVATE application::proto
)
target_compile_features(
    protocyte_external_application
    PRIVATE cxx_std_20
)

if(MSVC)
    target_compile_options(
        protocyte_external_application
        PRIVATE /W4 /WX /permissive-
    )
else()
    target_compile_options(
        protocyte_external_application
        PRIVATE -Wall -Wextra -Wpedantic -Werror
    )
endif()

enable_testing()
add_test(
    NAME protocyte_external_project_round_trip
    COMMAND protocyte_external_application
)
