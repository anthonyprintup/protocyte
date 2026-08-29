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
        OWNERSHIP_MANIFEST_DIR
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
    if(
        NOT IS_DIRECTORY "${OWNERSHIP_MANIFEST_DIR}"
        OR IS_SYMLINK "${OWNERSHIP_MANIFEST_DIR}"
    )
        message(
            FATAL_ERROR
            "Protocyte generation plan is missing or unsafe for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    set(output_root_file "${OWNERSHIP_MANIFEST_DIR}/output-root.path")
    if(
        NOT EXISTS "${output_root_file}"
        OR IS_DIRECTORY "${output_root_file}"
        OR IS_SYMLINK "${output_root_file}"
    )
        message(FATAL_ERROR "Protocyte generation plan has no safe output root")
    endif()
    file(READ "${output_root_file}" manifest_output_root)
    _protocyte_normalized_path_identity(manifest_root_identity "${manifest_output_root}")
    _protocyte_normalized_path_identity(output_root_identity "${OUTPUT_DIRECTORY}")
    if(NOT manifest_root_identity STREQUAL output_root_identity)
        message(FATAL_ERROR "Protocyte generation plan names a different output root")
    endif()

    set(outputs_file "${OWNERSHIP_MANIFEST_DIR}/outputs.hex")
    if(
        NOT EXISTS "${outputs_file}"
        OR IS_DIRECTORY "${outputs_file}"
        OR IS_SYMLINK "${outputs_file}"
    )
        message(FATAL_ERROR "Protocyte generation plan has no safe output inventory")
    endif()
    file(STRINGS "${outputs_file}" encoded_outputs ENCODING UTF-8)
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

_protocyte_run_coordinator(reconcile recovery_result recovery_output recovery_error)
if(NOT "${recovery_result}" STREQUAL "0")
    string(STRIP "${recovery_error}" recovery_error)
    message(
        FATAL_ERROR
        "Protocyte could not recover or reconcile output state before generation.\n${recovery_error}"
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
    _protocyte_normalized_path_identity(output_identity "${generation_output}")
    string(SHA256 output_key "${output_identity}")
    file(SHA256 "${generation_output}" output_hash)
    file(WRITE "${OWNERSHIP_MANIFEST_DIR}/${output_key}.sha256" "${output_hash}")
endforeach()
_protocyte_discard_staging()
