cmake_minimum_required(VERSION 3.24)

project(protocyte_release_package_contract LANGUAGES NONE)

find_package(protocyte CONFIG REQUIRED)

foreach(
    required_target
    IN ITEMS
        protocyte::codegen
        protocyte::runtime
        protocyte::runtime_hosted
)
    if(NOT TARGET "${required_target}")
        message(FATAL_ERROR "Release package did not define ${required_target}")
    endif()
endforeach()

foreach(
    required_path
    IN ITEMS
        PROTOCYTE_PYTHON_PROJECT_ROOT
        PROTOCYTE_PYTHON_CONSTRAINTS
        PROTOCYTE_PYTHON_SOURCE_ROOT
        PROTOCYTE_PACKAGE_ROOT
        PROTOCYTE_PROTO_DIR
        PROTOCYTE_OPTIONS_PROTO
)
    if(NOT EXISTS "${${required_path}}")
        message(FATAL_ERROR "Release package path ${required_path} is missing: ${${required_path}}")
    endif()
endforeach()
