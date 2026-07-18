cmake_minimum_required(VERSION 3.24)

project(protocyte_quickstart LANGUAGES CXX)

set(PROTOC_EXECUTABLE "" CACHE FILEPATH "Path to protoc")
set(PROTOCYTE_PLUGIN_EXECUTABLE "" CACHE FILEPATH "Path to protoc-gen-protocyte")

foreach(tool_variable IN ITEMS PROTOC_EXECUTABLE PROTOCYTE_PLUGIN_EXECUTABLE)
    set(tool_path "${${tool_variable}}")
    cmake_path(
        ABSOLUTE_PATH tool_path
        BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        NORMALIZE
        OUTPUT_VARIABLE resolved_tool_path
    )
    if(NOT EXISTS "${resolved_tool_path}" OR IS_DIRECTORY "${resolved_tool_path}")
        message(FATAL_ERROR "Set ${tool_variable} to an existing executable file")
    endif()
    set(${tool_variable} "${resolved_tool_path}")
endforeach()

set(PROTO_FILE "${CMAKE_CURRENT_SOURCE_DIR}/quickstart.proto")
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(GENERATED_HEADER "${GENERATED_DIR}/quickstart.protocyte.hpp")
set(GENERATED_SOURCE "${GENERATED_DIR}/quickstart.protocyte.cpp")
set(RUNTIME_HEADER "${GENERATED_DIR}/protocyte/runtime/runtime.hpp")

add_custom_command(
    OUTPUT
        "${GENERATED_HEADER}"
        "${GENERATED_SOURCE}"
        "${RUNTIME_HEADER}"
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${GENERATED_DIR}"
    COMMAND
        "${PROTOC_EXECUTABLE}"
        "--proto_path=${CMAKE_CURRENT_SOURCE_DIR}"
        "--plugin=protoc-gen-protocyte=${PROTOCYTE_PLUGIN_EXECUTABLE}"
        "--protocyte_out=runtime=emit:${GENERATED_DIR}"
        "${PROTO_FILE}"
    DEPENDS
        "${PROTO_FILE}"
        "${PROTOC_EXECUTABLE}"
        "${PROTOCYTE_PLUGIN_EXECUTABLE}"
    COMMENT "Generating the Protocyte quick-start message"
    VERBATIM
)

add_executable(
    protocyte_quickstart
    main.cpp
    "${GENERATED_HEADER}"
    "${GENERATED_SOURCE}"
    "${RUNTIME_HEADER}"
)
target_include_directories(protocyte_quickstart PRIVATE "${GENERATED_DIR}")
target_compile_definitions(protocyte_quickstart PRIVATE PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
target_compile_features(protocyte_quickstart PRIVATE cxx_std_20)

if(MSVC)
    target_compile_options(protocyte_quickstart PRIVATE /W4 /WX /permissive-)
else()
    target_compile_options(protocyte_quickstart PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

enable_testing()
add_test(NAME protocyte_quickstart_round_trip COMMAND protocyte_quickstart)
