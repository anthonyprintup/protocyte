cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteProcess.cmake")

foreach(
    required_variable
    IN ITEMS
        PROTOC_EXECUTABLE
        ARGUMENT_FILE
        LOCK_FILE
        PROTO_FILE
        SCAN_WORKING_DIRECTORY
        DEPENDENCY_READER
        DEPENDENCY_DESCRIPTOR
        DEPENDENCY_DEPFILE
        DEPENDENCY_DEPFILE_TARGET
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte dependency scan requires ${required_variable}")
    endif()
endforeach()

cmake_path(GET LOCK_FILE PARENT_PATH lock_directory)
file(MAKE_DIRECTORY "${lock_directory}")
file(
    LOCK "${LOCK_FILE}"
    GUARD PROCESS
    TIMEOUT 600
    RESULT_VARIABLE lock_result
)
if(NOT "${lock_result}" STREQUAL "0")
    message(
        FATAL_ERROR
        "Failed to lock the dependency-scan output for '${PROTO_FILE}': ${lock_result}"
    )
endif()

set(protocyte_dependency_environment)
if(MANAGED_DEPENDENCY_READER)
    list(APPEND protocyte_dependency_environment "--unset=PYTHONPATH" "--unset=PYTHONHOME")
endif()

_protocyte_resolve_tool_timeout(protocyte_tool_timeout)
_protocyte_execute_bounded(
    protoc_result
    protoc_output
    protoc_error
    protoc_timed_out
    WORKING_DIRECTORY "${SCAN_WORKING_DIRECTORY}"
    TIMEOUT_SECONDS "${protocyte_tool_timeout}"
    COMMAND
        "${PROTOC_EXECUTABLE}"
        "@${ARGUMENT_FILE}"
)

if(protoc_timed_out)
    file(REMOVE "${DEPENDENCY_DESCRIPTOR}" "${DEPENDENCY_DEPFILE}")
    message(
        FATAL_ERROR
        "Protocyte dependency scan for '${PROTO_FILE}' timed out while running protoc after "
        "${protocyte_tool_timeout} seconds. Partial dependency outputs were removed. Set "
        "PROTOCYTE_TOOL_TIMEOUT_SECONDS to a larger value or 0 to disable this timeout."
    )
endif()
if(NOT "${protoc_result}" STREQUAL "0")
    string(STRIP "${protoc_output}" protoc_output)
    string(STRIP "${protoc_error}" protoc_error)
    if(protoc_output STREQUAL "")
        set(protoc_output "<no standard output>")
    endif()
    if(protoc_error STREQUAL "")
        set(protoc_error "<no standard error>")
    endif()
    message(
        FATAL_ERROR
        "Failed to scan protobuf imports for '${PROTO_FILE}'.\n"
        "protoc: ${PROTOC_EXECUTABLE}\n"
        "Exit code: ${protoc_result}\n\n"
        "Standard output:\n${protoc_output}\n\n"
        "Standard error:\n${protoc_error}"
    )
endif()

# file(LOCK GUARD PROCESS) is released when this script exits.  Keep the
# descriptor reader in this lock-owning process so another configuration cannot
# overwrite the descriptor between protoc finishing and dependency-file reading
# it.  Do not split this into a second lock-taking script: CMake locks are not
# reentrant across nested CMake processes.
set(dependency_reader_format_arguments)
if(DEFINED DEPENDENCY_FILE_FORMAT AND NOT "${DEPENDENCY_FILE_FORMAT}" STREQUAL "")
    list(APPEND dependency_reader_format_arguments "${DEPENDENCY_FILE_FORMAT}")
endif()

_protocyte_execute_bounded(
    dependency_reader_result
    dependency_reader_output
    dependency_reader_error
    dependency_reader_timed_out
    WORKING_DIRECTORY "${SCAN_WORKING_DIRECTORY}"
    TIMEOUT_SECONDS "${protocyte_tool_timeout}"
    COMMAND
        "${CMAKE_COMMAND}" -E env
        ${protocyte_dependency_environment}
        "${DEPENDENCY_READER}"
        descriptor-set
        dependency-file
        ${dependency_reader_format_arguments}
        "${DEPENDENCY_DESCRIPTOR}"
        "${ARGUMENT_FILE}"
        "${DEPENDENCY_DEPFILE}"
        "${DEPENDENCY_DEPFILE_TARGET}"
)

if(dependency_reader_timed_out)
    file(REMOVE "${DEPENDENCY_DESCRIPTOR}" "${DEPENDENCY_DEPFILE}")
    message(
        FATAL_ERROR
        "Protocyte dependency scan for '${PROTO_FILE}' timed out while reading its descriptor after "
        "${protocyte_tool_timeout} seconds. Partial dependency outputs were removed. Set "
        "PROTOCYTE_TOOL_TIMEOUT_SECONDS to a larger value or 0 to disable this timeout."
    )
endif()
if(NOT "${dependency_reader_result}" STREQUAL "0")
    string(STRIP "${dependency_reader_output}" dependency_reader_output)
    string(STRIP "${dependency_reader_error}" dependency_reader_error)
    if(dependency_reader_output STREQUAL "")
        set(dependency_reader_output "<no standard output>")
    endif()
    if(dependency_reader_error STREQUAL "")
        set(dependency_reader_error "<no standard error>")
    endif()
    message(
        FATAL_ERROR
        "Failed to read the protobuf dependency descriptor for '${PROTO_FILE}'.\n"
        "Reader: ${DEPENDENCY_READER}\n"
        "Exit code: ${dependency_reader_result}\n\n"
        "Standard output:\n${dependency_reader_output}\n\n"
        "Standard error:\n${dependency_reader_error}"
    )
endif()
