cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteOutputSafety.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteProcess.cmake")

foreach(
    required_variable
    IN ITEMS
        PROTOC_EXECUTABLE
        ARGUMENT_FILE
        GENERATION_TARGET
        GENERATION_WORKING_DIRECTORY
        LOCK_DIRECTORY
        OUTPUT_DIRECTORY
        STAGING_OUTPUT_DIRECTORY
        OUTPUT_PLAN
        OUTPUT_TARGET_ID
        OUTPUT_COORDINATOR_PYTHON
        OUTPUT_COORDINATOR_SCRIPT
        SOURCE_DIRECTORY_HEX
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte generation requires ${required_variable}")
    endif()
endforeach()

function(_protocyte_decode_output_hex out_var encoded_value)
    string(LENGTH "${encoded_value}" encoded_length)
    math(EXPR encoded_remainder "${encoded_length} % 2")
    if(
        encoded_length EQUAL 0
        OR NOT encoded_remainder EQUAL 0
        OR NOT encoded_value MATCHES "^[0-9a-f]+$"
    )
        message(FATAL_ERROR "Protocyte generation plan contains malformed output encoding")
    endif()
    math(EXPR encoded_last "${encoded_length} - 2")
    set(decoded_value "")
    foreach(offset RANGE 0 ${encoded_last} 2)
        string(SUBSTRING "${encoded_value}" ${offset} 2 encoded_byte)
        math(EXPR byte_value "0x${encoded_byte}")
        string(ASCII ${byte_value} decoded_character)
        string(APPEND decoded_value "${decoded_character}")
    endforeach()
    set(${out_var} "${decoded_value}" PARENT_SCOPE)
endfunction()

function(_protocyte_load_generation_outputs out_var)
    _protocyte_run_coordinator(
        target-outputs
        inventory_result
        encoded_output_text
        inventory_error
        --target "${OUTPUT_TARGET_ID}"
    )
    if(NOT "${inventory_result}" STREQUAL "0")
        string(STRIP "${inventory_error}" inventory_error)
        message(FATAL_ERROR "Protocyte could not load target outputs.\n${inventory_error}")
    endif()
    string(REPLACE "\r\n" "\n" encoded_output_text "${encoded_output_text}")
    string(REPLACE "\n" ";" encoded_outputs "${encoded_output_text}")
    list(FILTER encoded_outputs EXCLUDE REGEX "^$")
    set(outputs)
    foreach(encoded_output IN LISTS encoded_outputs)
        _protocyte_decode_output_hex(output_path "${encoded_output}")
        cmake_path(NORMAL_PATH output_path OUTPUT_VARIABLE output_path)
        _protocyte_generated_output_path_is_safe(
            output_is_safe
            "${output_path}"
            "${OUTPUT_DIRECTORY}"
        )
        if(NOT output_is_safe)
            message(FATAL_ERROR "Protocyte generation plan contains an unsafe output path")
        endif()
        list(APPEND outputs "${output_path}")
    endforeach()
    if(NOT outputs)
        message(FATAL_ERROR "Protocyte generation plan contains no outputs")
    endif()
    set(${out_var} "${outputs}" PARENT_SCOPE)
endfunction()

function(_protocyte_validate_staging_directory)
    if(NOT IS_ABSOLUTE "${STAGING_OUTPUT_DIRECTORY}")
        message(FATAL_ERROR "Protocyte generation staging directory is not absolute")
    endif()
    _protocyte_path_has_linked_existing_component(staging_has_link "${STAGING_OUTPUT_DIRECTORY}")
    _protocyte_project_path_through_existing_components(
        projected_staging
        staging_is_projectable
        "${STAGING_OUTPUT_DIRECTORY}"
        FALSE
    )
    cmake_path(
        IS_PREFIX OUTPUT_DIRECTORY
        "${projected_staging}"
        NORMALIZE
        staging_is_under_output
    )
    if(staging_has_link OR NOT staging_is_projectable OR staging_is_under_output)
        message(FATAL_ERROR "Protocyte generation staging directory is unsafe")
    endif()
endfunction()

function(_protocyte_staged_output_path out_var generation_output)
    file(RELATIVE_PATH relative_output "${OUTPUT_DIRECTORY}" "${generation_output}")
    cmake_path(
        APPEND STAGING_OUTPUT_DIRECTORY
        generated
        "${relative_output}"
        OUTPUT_VARIABLE staged_output
    )
    cmake_path(NORMAL_PATH staged_output)
    set(${out_var} "${staged_output}" PARENT_SCOPE)
endfunction()

function(_protocyte_discard_staging)
    _protocyte_path_has_linked_existing_component(staging_has_link "${STAGING_OUTPUT_DIRECTORY}")
    if(staging_has_link)
        message(
            WARNING
            "Protocyte preserved unsafe staging data at '${STAGING_OUTPUT_DIRECTORY}'. Remove it manually."
        )
        return()
    endif()
    file(REMOVE_RECURSE "${STAGING_OUTPUT_DIRECTORY}")
endfunction()

function(_protocyte_run_coordinator command out_result out_output out_error)
    set(extra_arguments ${ARGN})
    execute_process(
        COMMAND
            "${CMAKE_COMMAND}" -E env --unset=PYTHONHOME --unset=PYTHONPATH
            "${OUTPUT_COORDINATOR_PYTHON}"
            "${OUTPUT_COORDINATOR_SCRIPT}"
            "${command}"
            --lock-root "${LOCK_DIRECTORY}"
            --plan "${OUTPUT_PLAN}"
            ${extra_arguments}
        RESULT_VARIABLE result
        OUTPUT_VARIABLE output
        ERROR_VARIABLE error
        ENCODING UTF-8
    )
    set(${out_result} "${result}" PARENT_SCOPE)
    set(${out_output} "${output}" PARENT_SCOPE)
    set(${out_error} "${error}" PARENT_SCOPE)
endfunction()

if(NOT EXISTS "${OUTPUT_PLAN}" OR IS_DIRECTORY "${OUTPUT_PLAN}" OR IS_SYMLINK "${OUTPUT_PLAN}")
    message(FATAL_ERROR "Protocyte authoritative output plan is missing or unsafe: ${OUTPUT_PLAN}")
endif()
if(
    NOT EXISTS "${OUTPUT_COORDINATOR_SCRIPT}"
    OR IS_DIRECTORY "${OUTPUT_COORDINATOR_SCRIPT}"
    OR IS_SYMLINK "${OUTPUT_COORDINATOR_SCRIPT}"
)
    message(FATAL_ERROR "Protocyte output coordinator is missing or unsafe")
endif()

if(NOT PROTOCYTE_GENERATION_LOCK_HELD)
    _protocyte_run_coordinator(reconcile recovery_result recovery_output recovery_error)
    if(NOT "${recovery_result}" STREQUAL "0")
        string(STRIP "${recovery_error}" recovery_error)
        message(
            FATAL_ERROR
            "Protocyte could not recover or reconcile output state before generation.\n${recovery_error}"
        )
    endif()
    set(
        locked_generation_command
        "${CMAKE_COMMAND}"
        "-DPROTOCYTE_GENERATION_LOCK_HELD=TRUE"
        "-DPROTOC_EXECUTABLE=${PROTOC_EXECUTABLE}"
        "-DARGUMENT_FILE=${ARGUMENT_FILE}"
        "-DGENERATION_TARGET=${GENERATION_TARGET}"
        "-DGENERATION_WORKING_DIRECTORY=${GENERATION_WORKING_DIRECTORY}"
        "-DLOCK_DIRECTORY=${LOCK_DIRECTORY}"
        "-DOUTPUT_DIRECTORY=${OUTPUT_DIRECTORY}"
        "-DSTAGING_OUTPUT_DIRECTORY=${STAGING_OUTPUT_DIRECTORY}"
        "-DOUTPUT_PLAN=${OUTPUT_PLAN}"
        "-DOUTPUT_TARGET_ID=${OUTPUT_TARGET_ID}"
        "-DOUTPUT_COORDINATOR_PYTHON=${OUTPUT_COORDINATOR_PYTHON}"
        "-DOUTPUT_COORDINATOR_SCRIPT=${OUTPUT_COORDINATOR_SCRIPT}"
        "-DSOURCE_DIRECTORY_HEX=${SOURCE_DIRECTORY_HEX}"
        "-DPROTOCYTE_MANAGED_PLUGIN=${PROTOCYTE_MANAGED_PLUGIN}"
        "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=${PROTOCYTE_TOOL_TIMEOUT_SECONDS}"
        -P "${CMAKE_CURRENT_LIST_FILE}"
    )
    string(HEX "$ENV{PYTHONPATH}" locked_pythonpath_hex)
    string(HEX "$ENV{PYTHONHOME}" locked_pythonhome_hex)
    execute_process(
        COMMAND
            "${CMAKE_COMMAND}" -E env
            "PROTOCYTE_LOCKED_PYTHONPATH_HEX=${locked_pythonpath_hex}"
            "PROTOCYTE_LOCKED_PYTHONHOME_HEX=${locked_pythonhome_hex}"
            --unset=PYTHONHOME --unset=PYTHONPATH
            "${OUTPUT_COORDINATOR_PYTHON}"
            "${OUTPUT_COORDINATOR_SCRIPT}"
            run-generation
            --lock-root "${LOCK_DIRECTORY}"
            --plan "${OUTPUT_PLAN}"
            --exec ${locked_generation_command}
        RESULT_VARIABLE locked_generation_result
        OUTPUT_VARIABLE locked_generation_output
        ERROR_VARIABLE locked_generation_error
        ENCODING UTF-8
    )
    if(NOT "${locked_generation_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Protocyte locked generation failed.\n${locked_generation_output}${locked_generation_error}"
        )
    endif()
    return()
endif()

_protocyte_run_coordinator(validate validation_result validation_output validation_error)
if(NOT "${validation_result}" STREQUAL "0")
    string(STRIP "${validation_error}" validation_error)
    message(
        FATAL_ERROR
        "Protocyte output ownership changed before generation began.\n${validation_error}"
    )
endif()

_protocyte_load_generation_outputs(generation_outputs)
_protocyte_validate_staging_directory()
_protocyte_discard_staging()
file(MAKE_DIRECTORY "${STAGING_OUTPUT_DIRECTORY}/generated")
_protocyte_validate_staging_directory()

set(staged_outputs)
foreach(generation_output IN LISTS generation_outputs)
    _protocyte_staged_output_path(staged_output "${generation_output}")
    _protocyte_generated_output_path_is_safe(
        staged_output_is_safe
        "${staged_output}"
        "${STAGING_OUTPUT_DIRECTORY}/generated"
    )
    if(NOT staged_output_is_safe)
        _protocyte_discard_staging()
        message(FATAL_ERROR "Protocyte derived an unsafe staged output path")
    endif()
    list(APPEND staged_outputs "${staged_output}")
endforeach()

set(protoc_environment)
if(PROTOCYTE_MANAGED_PLUGIN)
    list(APPEND protoc_environment --unset=PYTHONPATH --unset=PYTHONHOME)
endif()
_protocyte_resolve_tool_timeout(protocyte_tool_timeout)
_protocyte_execute_bounded(
    protoc_result
    protoc_output
    protoc_error
    protoc_timed_out
    WORKING_DIRECTORY "${GENERATION_WORKING_DIRECTORY}"
    TIMEOUT_SECONDS "${protocyte_tool_timeout}"
    ECHO_OUTPUT
    ECHO_ERROR
    COMMAND
        "${CMAKE_COMMAND}" -E env
        ${protoc_environment}
        "PROTOCYTE_CMAKE_WORKING_DIRECTORY_HEX=${SOURCE_DIRECTORY_HEX}"
        "${PROTOC_EXECUTABLE}"
        "@${ARGUMENT_FILE}"
)
if(protoc_timed_out)
    _protocyte_discard_staging()
    message(FATAL_ERROR "Protocyte generation timed out before publication")
endif()
if(NOT "${protoc_result}" STREQUAL "0")
    _protocyte_discard_staging()
    string(STRIP "${protoc_output}" protoc_output)
    string(STRIP "${protoc_error}" protoc_error)
    message(
        FATAL_ERROR
        "Failed to generate Protocyte sources for target '${GENERATION_TARGET}'.\n"
        "protoc: ${PROTOC_EXECUTABLE}\nExit code: ${protoc_result}\n\n"
        "Standard output:\n${protoc_output}\n\nStandard error:\n${protoc_error}"
    )
endif()

foreach(staged_output IN LISTS staged_outputs)
    if(
        NOT EXISTS "${staged_output}"
        OR IS_DIRECTORY "${staged_output}"
        OR IS_SYMLINK "${staged_output}"
    )
        _protocyte_discard_staging()
        message(FATAL_ERROR "Protocyte generation did not produce every expected staged output")
    endif()
endforeach()

_protocyte_run_coordinator(
    publish
    publication_result
    publication_output
    publication_error
    --target "${OUTPUT_TARGET_ID}"
    --staging-root "${STAGING_OUTPUT_DIRECTORY}/generated"
)
if(NOT "${publication_result}" STREQUAL "0")
    string(STRIP "${publication_error}" publication_error)
    message(FATAL_ERROR "Protocyte output publication failed.\n${publication_error}")
endif()

foreach(generation_output IN LISTS generation_outputs)
    if(
        NOT EXISTS "${generation_output}"
        OR IS_DIRECTORY "${generation_output}"
        OR IS_SYMLINK "${generation_output}"
    )
        message(FATAL_ERROR "Protocyte publication reported success without every declared output")
    endif()
    file(TOUCH_NOCREATE "${generation_output}")
endforeach()
_protocyte_discard_staging()
