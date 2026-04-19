cmake_minimum_required(VERSION 3.24)

project(protocyte_hell_gate LANGUAGES NONE)

if(NOT DEFINED PROTOCYTE_SOURCE_DIR OR PROTOCYTE_SOURCE_DIR STREQUAL "")
    message(FATAL_ERROR "PROTOCYTE_SOURCE_DIR must point at the protocyte repository root")
endif()

cmake_path(ABSOLUTE_PATH PROTOCYTE_SOURCE_DIR NORMALIZE OUTPUT_VARIABLE protocyte_source_dir)

if(NOT IS_DIRECTORY "${protocyte_source_dir}")
    message(FATAL_ERROR "PROTOCYTE_SOURCE_DIR '${protocyte_source_dir}' does not exist")
endif()
if(NOT EXISTS "${protocyte_source_dir}/CMakeLists.txt")
    message(FATAL_ERROR "PROTOCYTE_SOURCE_DIR '${protocyte_source_dir}' does not look like the protocyte repository root")
endif()

add_subdirectory("${protocyte_source_dir}" "${CMAKE_CURRENT_BINARY_DIR}/protocyte")
