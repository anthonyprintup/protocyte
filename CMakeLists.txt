cmake_minimum_required(VERSION 3.24)

project(protocyte LANGUAGES NONE)

option(
    PROTOCYTE_FETCH_PROTOBUF
    "Fetch protobuf when protobuf CMake targets are unavailable."
    ON
)
set(
    PROTOCYTE_PROTOBUF_GIT_TAG
    "v31.1"
    CACHE STRING
    "protobuf git tag used when PROTOCYTE_FETCH_PROTOBUF is enabled."
)
set(
    PROTOCYTE_PROTOBUF_GIT_COMMIT
    "74211c0dfc2777318ab53c2cd2c317a2ef9012de"
    CACHE STRING
    "protobuf commit expected for PROTOCYTE_PROTOBUF_GIT_TAG when PROTOCYTE_FETCH_PROTOBUF is enabled."
)

include("${CMAKE_CURRENT_LIST_DIR}/cmake/Protocyte.cmake")
