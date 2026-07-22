cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteProcess.cmake")

foreach(
    required_variable
    IN ITEMS
        PLUGIN_EXECUTABLE
        PLUGIN_IS_MANAGED
        IMPORT_SCAN_COMMAND
        REQUEST_FILE
        WITNESS_FILE
        LOCK_FILE
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte import topology check requires ${required_variable}")
    endif()
endforeach()

file(
    LOCK "${LOCK_FILE}"
    GUARD PROCESS
    TIMEOUT 600
    RESULT_VARIABLE topology_lock_result
)
if(NOT "${topology_lock_result}" STREQUAL "0")
    message(
        FATAL_ERROR
        "Failed to lock Protocyte import topology witness '${WITNESS_FILE}': ${topology_lock_result}"
    )
endif()

set(import_scan_launcher "${PLUGIN_EXECUTABLE}")
if(PLUGIN_IS_MANAGED)
    set(
        import_scan_launcher
        "${CMAKE_COMMAND}"
        -E
        env
        --unset=PYTHONHOME
        --unset=PYTHONPATH
        "${PLUGIN_EXECUTABLE}"
    )
endif()

_protocyte_resolve_tool_timeout(protocyte_tool_timeout)
_protocyte_execute_bounded(
    topology_check_result
    topology_check_output
    topology_check_error
    topology_check_timed_out
    TIMEOUT_SECONDS "${protocyte_tool_timeout}"
    COMMAND
        ${import_scan_launcher}
        "${IMPORT_SCAN_COMMAND}"
        --scan-topology-witness
        "${REQUEST_FILE}"
        "${WITNESS_FILE}"
)
if(topology_check_timed_out)
    message(
        FATAL_ERROR
        "Protocyte import topology check through '${PLUGIN_EXECUTABLE}' timed out after "
        "${protocyte_tool_timeout} seconds. Set PROTOCYTE_TOOL_TIMEOUT_SECONDS to a larger "
        "value or 0 to disable this timeout."
    )
endif()
if(NOT topology_check_result EQUAL 0)
    string(STRIP "${topology_check_output}" topology_check_output)
    string(STRIP "${topology_check_error}" topology_check_error)
    message(
        FATAL_ERROR
        "Protocyte import topology check through '${PLUGIN_EXECUTABLE}' failed with exit code "
        "${topology_check_result}: ${topology_check_output} ${topology_check_error}. "
        "PROTOCYTE_PLUGIN_EXECUTABLE overrides must name the actual version-matched Protocyte "
        "plugin with ${IMPORT_SCAN_COMMAND} support."
    )
endif()
