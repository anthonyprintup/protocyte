cmake_minimum_required(VERSION 3.24)

project(protocyte_quickstart LANGUAGES CXX)

include(FetchContent)

FetchContent_Declare(
    protocyte
    GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
    GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14
)
FetchContent_MakeAvailable(protocyte)

protocyte_add_proto_library(
    TARGET quickstart_proto
    ALIAS quickstart::proto
    PROTO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/proto"
    DISCOVER
    HOSTED_ALLOCATOR
)

add_executable(protocyte_quickstart main.cpp)
target_link_libraries(protocyte_quickstart PRIVATE quickstart::proto)
target_compile_features(protocyte_quickstart PRIVATE cxx_std_20)

if(MSVC)
    target_compile_options(protocyte_quickstart PRIVATE /W4 /WX /permissive-)
else()
    target_compile_options(protocyte_quickstart PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

enable_testing()
add_test(
    NAME protocyte_getting_started
    COMMAND protocyte_quickstart
)
