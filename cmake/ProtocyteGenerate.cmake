cmake_minimum_required(VERSION 3.24)

foreach(
    required_variable
    IN ITEMS
        PROTOC_EXECUTABLE
        ARGUMENT_FILE
        GENERATION_TARGET
        GENERATION_WORKING_DIRECTORY
        LOCK_DIRECTORY
        LOCK_MANIFEST
        SOURCE_DIRECTORY_HEX
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte generation requires ${required_variable}")
    endif()
endforeach()

if(NOT EXISTS "${LOCK_MANIFEST}")
    message(FATAL_ERROR "Protocyte generation lock manifest does not exist: ${LOCK_MANIFEST}")
endif()

file(STRINGS "${LOCK_MANIFEST}" output_lock_keys)
if(NOT output_lock_keys)
    message(FATAL_ERROR "Protocyte generation lock manifest is empty: ${LOCK_MANIFEST}")
endif()
list(REMOVE_DUPLICATES output_lock_keys)
list(SORT output_lock_keys)

file(MAKE_DIRECTORY "${LOCK_DIRECTORY}")
foreach(output_lock_key IN LISTS output_lock_keys)
    string(LENGTH "${output_lock_key}" output_lock_key_length)
    if(NOT output_lock_key_length EQUAL 64 OR NOT "${output_lock_key}" MATCHES "^[0-9a-f]+$")
        message(
            FATAL_ERROR
            "Protocyte generation lock manifest contains an invalid output identity: ${output_lock_key}"
        )
    endif()
    file(
        LOCK "${LOCK_DIRECTORY}/${output_lock_key}.lock"
        GUARD PROCESS
        TIMEOUT 600
        RESULT_VARIABLE lock_result
    )
    if(NOT "${lock_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Failed to lock a generated output for target '${GENERATION_TARGET}': ${lock_result}"
        )
    endif()
endforeach()

execute_process(
    COMMAND
        "${CMAKE_COMMAND}" -E env
        "PROTOCYTE_CMAKE_WORKING_DIRECTORY_HEX=${SOURCE_DIRECTORY_HEX}"
        "${PROTOC_EXECUTABLE}"
        "@${ARGUMENT_FILE}"
    WORKING_DIRECTORY "${GENERATION_WORKING_DIRECTORY}"
    RESULT_VARIABLE protoc_result
    OUTPUT_VARIABLE protoc_output
    ERROR_VARIABLE protoc_error
    ECHO_OUTPUT_VARIABLE
    ECHO_ERROR_VARIABLE
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
        "Failed to generate Protocyte sources for target '${GENERATION_TARGET}'.\n"
        "protoc: ${PROTOC_EXECUTABLE}\n"
        "Exit code: ${protoc_result}\n\n"
        "Standard output:\n${protoc_output}\n\n"
        "Standard error:\n${protoc_error}"
    )
endif()
