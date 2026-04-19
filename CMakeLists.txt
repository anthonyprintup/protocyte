cmake_minimum_required(VERSION 3.24)

project(protocyte VERSION 0.1.0 LANGUAGES NONE)

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
        PATTERN "*.proto"
        PATTERN "__pycache__" EXCLUDE
        PATTERN "*.pyc" EXCLUDE
)
install(
    DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/src/protocyte/proto/"
    DESTINATION "${PROTOCYTE_INSTALL_PROTODIR}"
    FILES_MATCHING
        PATTERN "*.proto"
)
