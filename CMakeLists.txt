cmake_minimum_required(VERSION 3.24)

file(
    STRINGS "${CMAKE_CURRENT_LIST_DIR}/src/protocyte/__init__.py"
    PROTOCYTE_VERSION_LINE
    REGEX "^__version__ = \"[^\"]+\"$"
)
if(NOT PROTOCYTE_VERSION_LINE)
    message(FATAL_ERROR "Failed to read protocyte version from src/protocyte/__init__.py")
endif()
string(
    REGEX REPLACE "^__version__ = \"([^\"]+)\"$"
    "\\1"
    PROTOCYTE_VERSION
    "${PROTOCYTE_VERSION_LINE}"
)
if(NOT PROTOCYTE_VERSION)
    message(FATAL_ERROR "Failed to parse protocyte version from src/protocyte/__init__.py")
endif()
string(REGEX MATCH "^([0-9]+\\.[0-9]+\\.[0-9]+)(rc[0-9]+)?$" PROTOCYTE_VERSION_MATCH "${PROTOCYTE_VERSION}")
if(NOT PROTOCYTE_VERSION_MATCH)
    message(FATAL_ERROR "Unsupported protocyte version format: ${PROTOCYTE_VERSION}")
endif()
set(PROTOCYTE_PROJECT_VERSION "${CMAKE_MATCH_1}")

project(protocyte VERSION "${PROTOCYTE_PROJECT_VERSION}" LANGUAGES CXX)

include(CMakePackageConfigHelpers)
if(NOT DEFINED CMAKE_INSTALL_LIBDIR)
    set(CMAKE_INSTALL_LIBDIR "lib" CACHE PATH "Object code libraries")
endif()
if(NOT DEFINED CMAKE_INSTALL_DATADIR)
    set(CMAKE_INSTALL_DATADIR "share" CACHE PATH "Read-only architecture-independent data")
endif()
include(GNUInstallDirs)

option(
    PROTOCYTE_FETCH_PROTOBUF
    "Fetch protobuf when protobuf CMake targets are unavailable."
    ON
)
set(
    PROTOCYTE_PROTOBUF_VERSION
    "34.1"
    CACHE STRING
    "protobuf release version used by CI prebuilt protoc installs."
)
# protobuf release v34.1
set(
    PROTOCYTE_PROTOBUF_GIT_TAG
    "4b0c3aacf0657fbf38253b38918d3358dd4319ec"
    CACHE STRING
    "protobuf git tag used when PROTOCYTE_FETCH_PROTOBUF is enabled."
)

set(PROTOCYTE_INSTALL_CMAKEDIR "${CMAKE_INSTALL_LIBDIR}/cmake/protocyte")
set(PROTOCYTE_INSTALL_PYTHONDIR "${CMAKE_INSTALL_DATADIR}/protocyte/python")
set(PROTOCYTE_INSTALL_PROTODIR "${CMAKE_INSTALL_DATADIR}/protocyte/proto")

include("${CMAKE_CURRENT_LIST_DIR}/cmake/Protocyte.cmake")

set(PROTOCYTE_RUNTIME_BASE_DIR "${CMAKE_CURRENT_LIST_DIR}/src")
set(PROTOCYTE_RUNTIME_HEADER "${PROTOCYTE_RUNTIME_BASE_DIR}/protocyte/runtime/runtime.hpp")

add_library(protocyte_codegen INTERFACE)
add_library(protocyte::codegen ALIAS protocyte_codegen)
set_target_properties(protocyte_codegen PROPERTIES EXPORT_NAME codegen)
target_compile_features(protocyte_codegen INTERFACE cxx_std_20)

function(protocyte_configure_runtime_target target_name export_name)
    add_library("${target_name}" INTERFACE)
    set_target_properties(
        "${target_name}"
        PROPERTIES
            EXPORT_NAME "${export_name}"
    )
    target_compile_features("${target_name}" INTERFACE cxx_std_20)
    target_include_directories(
        "${target_name}"
        INTERFACE
            "$<BUILD_INTERFACE:${PROTOCYTE_RUNTIME_BASE_DIR}>"
            "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
    )
    target_sources(
        "${target_name}"
        INTERFACE
            FILE_SET HEADERS
            BASE_DIRS "${PROTOCYTE_RUNTIME_BASE_DIR}"
            FILES "${PROTOCYTE_RUNTIME_HEADER}"
    )
endfunction()

protocyte_configure_runtime_target(protocyte_runtime runtime)
add_library(protocyte::runtime ALIAS protocyte_runtime)

protocyte_configure_runtime_target(protocyte_runtime_hosted runtime_hosted)
add_library(protocyte::runtime_hosted ALIAS protocyte_runtime_hosted)
target_compile_definitions(protocyte_runtime_hosted INTERFACE PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)

configure_package_config_file(
    "${CMAKE_CURRENT_LIST_DIR}/cmake/protocyteConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cmake/protocyteConfig.cmake"
    INSTALL_DESTINATION "${PROTOCYTE_INSTALL_CMAKEDIR}"
    NO_CHECK_REQUIRED_COMPONENTS_MACRO
)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/cmake/protocyteConfigVersion.cmake"
    VERSION "${PROJECT_VERSION}"
    COMPATIBILITY SameMajorVersion
)

install(
    TARGETS
        protocyte_runtime
        protocyte_runtime_hosted
    EXPORT protocyteTargets
    FILE_SET HEADERS DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
)
install(TARGETS protocyte_codegen EXPORT protocyteTargets)
install(
    EXPORT protocyteTargets
    NAMESPACE protocyte::
    DESTINATION "${PROTOCYTE_INSTALL_CMAKEDIR}"
)
install(
    FILES
        "${CMAKE_CURRENT_LIST_DIR}/cmake/ProtocyteFunctions.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/cmake/protocyteConfig.cmake"
        "${CMAKE_CURRENT_BINARY_DIR}/cmake/protocyteConfigVersion.cmake"
    DESTINATION "${PROTOCYTE_INSTALL_CMAKEDIR}"
)
install(
    DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/src/protocyte"
    DESTINATION "${PROTOCYTE_INSTALL_PYTHONDIR}"
    FILES_MATCHING
        PATTERN "*.py"
        PATTERN "*.hpp"
        PATTERN "proto" EXCLUDE
        PATTERN "__pycache__" EXCLUDE
        PATTERN "*.pyc" EXCLUDE
)
install(
    DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/src/protocyte/proto/"
    DESTINATION "${PROTOCYTE_INSTALL_PROTODIR}"
    FILES_MATCHING
        PATTERN "*.proto"
)
