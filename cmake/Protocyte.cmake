include_guard(GLOBAL)

set(PROTOCYTE_REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/.." CACHE INTERNAL "protocyte repository root")
set(PROTOCYTE_PYTHON_SOURCE_ROOT "${PROTOCYTE_REPO_ROOT}/src" CACHE INTERNAL "protocyte python import root")
set(PROTOCYTE_PACKAGE_ROOT "${PROTOCYTE_PYTHON_SOURCE_ROOT}/protocyte" CACHE INTERNAL "protocyte python package root")
set(PROTOCYTE_PROTO_DIR "${PROTOCYTE_PACKAGE_ROOT}/proto" CACHE INTERNAL "protocyte proto include root")
set(
    PROTOCYTE_OPTIONS_PROTO
    "${PROTOCYTE_PROTO_DIR}/protocyte/options.proto"
    CACHE INTERNAL
    "protocyte options proto file"
)
set(
    PROTOCYTE_GENERATOR_SOURCES
    "${PROTOCYTE_PACKAGE_ROOT}/__init__.py"
    "${PROTOCYTE_PACKAGE_ROOT}/cpp.py"
    "${PROTOCYTE_PACKAGE_ROOT}/errors.py"
    "${PROTOCYTE_PACKAGE_ROOT}/main.py"
    "${PROTOCYTE_PACKAGE_ROOT}/model.py"
    "${PROTOCYTE_PACKAGE_ROOT}/parameters.py"
    "${PROTOCYTE_PACKAGE_ROOT}/plugin.py"
    "${PROTOCYTE_PACKAGE_ROOT}/runtime.py"
    CACHE INTERNAL
    "protocyte generator source files"
)

include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteFunctions.cmake")
