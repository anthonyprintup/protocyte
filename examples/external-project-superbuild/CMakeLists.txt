cmake_minimum_required(VERSION 3.24)

project(protocyte_superbuild LANGUAGES NONE)

include(ExternalProject)

set(PROTOCYTE_SOURCE_DIR "" CACHE PATH "Use an existing Protocyte source checkout")
set(
    PROTOCYTE_PRIVATE_PREFIX
    "${CMAKE_BINARY_DIR}/protocyte-prefix"
    CACHE PATH
    "Private Protocyte install prefix"
)

set(superbuild_config_args)
if(NOT CMAKE_CONFIGURATION_TYPES AND CMAKE_BUILD_TYPE)
    list(
        APPEND superbuild_config_args
        "-DCMAKE_BUILD_TYPE:STRING=${CMAKE_BUILD_TYPE}"
    )
endif()

set(protocyte_download_args)
if(PROTOCYTE_SOURCE_DIR)
    cmake_path(
        ABSOLUTE_PATH PROTOCYTE_SOURCE_DIR
        BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        NORMALIZE
    )
    list(
        APPEND protocyte_download_args
        SOURCE_DIR "${PROTOCYTE_SOURCE_DIR}"
        DOWNLOAD_COMMAND ""
        UPDATE_COMMAND ""
    )
else()
    list(
        APPEND protocyte_download_args
        GIT_REPOSITORY https://github.com/anthonyprintup/protocyte.git
        GIT_TAG 9bae6fe8bf78a47a6356dc1fdc1e0ab8baa97d14
        UPDATE_DISCONNECTED TRUE
    )
endif()

ExternalProject_Add(
    protocyte_external
    PREFIX "${CMAKE_BINARY_DIR}/protocyte"
    ${protocyte_download_args}
    INSTALL_DIR "${PROTOCYTE_PRIVATE_PREFIX}"
    CMAKE_ARGS
        ${superbuild_config_args}
        "-DCMAKE_INSTALL_PREFIX:PATH=<INSTALL_DIR>"
        "-DPROTOCYTE_INSTALL:BOOL=ON"
)

set(application_tool_args "-DPROTOCYTE_FETCH_PROTOBUF:BOOL=ON")
foreach(
    tool_variable
    IN ITEMS
        PROTOCYTE_PLUGIN_EXECUTABLE
        PROTOCYTE_PROTOBUF_IMPORT_DIR
        Protobuf_PROTOC_EXECUTABLE
        Python3_EXECUTABLE
)
    if(DEFINED ${tool_variable} AND NOT "${${tool_variable}}" STREQUAL "")
        list(APPEND application_tool_args "-D${tool_variable}:FILEPATH=${${tool_variable}}")
    endif()
endforeach()
if(
    DEFINED PROTOCYTE_FETCH_PROTOBUF
    AND NOT "${PROTOCYTE_FETCH_PROTOBUF}" STREQUAL ""
)
    list(
        TRANSFORM application_tool_args
        REPLACE "^-DPROTOCYTE_FETCH_PROTOBUF:BOOL=ON$"
                "-DPROTOCYTE_FETCH_PROTOBUF:BOOL=${PROTOCYTE_FETCH_PROTOBUF}"
    )
endif()

ExternalProject_Add(
    application_external
    PREFIX "${CMAKE_BINARY_DIR}/application-prefix"
    SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/application"
    BINARY_DIR "${CMAKE_BINARY_DIR}/application"
    DEPENDS protocyte_external
    CMAKE_ARGS
        ${superbuild_config_args}
        "-DCMAKE_PREFIX_PATH:PATH=${PROTOCYTE_PRIVATE_PREFIX}"
        ${application_tool_args}
    INSTALL_COMMAND ""
)
