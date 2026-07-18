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

if(
    DEFINED OWNERSHIP_MANIFEST_DIR
    AND NOT "${OWNERSHIP_MANIFEST_DIR}" STREQUAL ""
    AND IS_DIRECTORY "${OWNERSHIP_MANIFEST_DIR}"
)
    set(output_root_file "${OWNERSHIP_MANIFEST_DIR}/output-root.path")
    if(EXISTS "${output_root_file}")
        file(READ "${output_root_file}" output_root)
        file(GLOB output_markers LIST_DIRECTORIES FALSE "${OWNERSHIP_MANIFEST_DIR}/*.path")
        list(REMOVE_ITEM output_markers "${output_root_file}")
        foreach(output_marker IN LISTS output_markers)
            cmake_path(GET output_marker STEM output_key)
            file(READ "${output_marker}" owned_output)
            cmake_path(NORMAL_PATH owned_output OUTPUT_VARIABLE normalized_owned_output)
            set(output_identity "${normalized_owned_output}")
            if(CMAKE_HOST_WIN32)
                string(TOLOWER "${output_identity}" output_identity)
            endif()
            string(SHA256 recorded_output_key "${output_identity}")
            set(output_is_safe FALSE)
            if(IS_ABSOLUTE "${normalized_owned_output}" AND IS_ABSOLUTE "${output_root}")
                cmake_path(
                    IS_PREFIX output_root
                    "${normalized_owned_output}"
                    NORMALIZE
                    output_is_under_root
                )
                if(
                    output_is_under_root
                    AND normalized_owned_output MATCHES
                        "([.]protocyte[.](hpp|cpp)|/runtime[.]hpp)$"
                )
                    set(output_is_safe TRUE)
                endif()
            endif()
            if(
                output_is_safe
                AND recorded_output_key STREQUAL output_key
                AND EXISTS "${normalized_owned_output}"
                AND NOT IS_DIRECTORY "${normalized_owned_output}"
            )
                # Make successful custom-command completion newer than its
                # dependency scan even when the generator kept identical bytes.
                file(TOUCH_NOCREATE "${normalized_owned_output}")
                file(SHA256 "${normalized_owned_output}" output_hash)
                file(
                    WRITE
                    "${OWNERSHIP_MANIFEST_DIR}/${output_key}.sha256"
                    "${output_hash}"
                )
            endif()
        endforeach()
    endif()
endif()
