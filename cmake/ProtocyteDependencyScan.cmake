cmake_minimum_required(VERSION 3.24)

foreach(
    required_variable
    IN ITEMS
        PROTOC_EXECUTABLE
        DEPENDENCY_OUT
        DESCRIPTOR_SET_OUT
        PROTO_FILE
        SCAN_WORKING_DIRECTORY
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte dependency scan requires ${required_variable}")
    endif()
endforeach()

execute_process(
    COMMAND
        "${PROTOC_EXECUTABLE}"
        ${PROTO_PATH_ARGUMENTS}
        "--dependency_out=${DEPENDENCY_OUT}"
        "--descriptor_set_out=${DESCRIPTOR_SET_OUT}"
        "${PROTO_FILE}"
    WORKING_DIRECTORY "${SCAN_WORKING_DIRECTORY}"
    RESULT_VARIABLE protoc_result
    OUTPUT_VARIABLE protoc_output
    ERROR_VARIABLE protoc_error
)

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
