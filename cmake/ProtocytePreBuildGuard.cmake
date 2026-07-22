cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteProcess.cmake")

if(NOT DEFINED MANIFEST_FILE OR "${MANIFEST_FILE}" STREQUAL "")
    message(FATAL_ERROR "Protocyte pre-build guard requires MANIFEST_FILE")
endif()
if(NOT EXISTS "${MANIFEST_FILE}")
    message(FATAL_ERROR "Protocyte pre-build guard manifest does not exist: ${MANIFEST_FILE}")
endif()

function(_protocyte_decode_guard_path out_var encoded_path)
    string(LENGTH "${encoded_path}" encoded_length)
    math(EXPR encoded_last "${encoded_length} - 2")
    set(decoded_path "")
    foreach(offset RANGE 0 ${encoded_last} 2)
        string(SUBSTRING "${encoded_path}" ${offset} 2 encoded_byte)
        math(EXPR byte_value "0x${encoded_byte}")
        string(ASCII ${byte_value} decoded_character)
        string(APPEND decoded_path "${decoded_character}")
    endforeach()
    set(${out_var} "${decoded_path}" PARENT_SCOPE)
endfunction()

file(STRINGS "${MANIFEST_FILE}" manifest_lines ENCODING UTF-8)
list(POP_FRONT manifest_lines manifest_version)
if(NOT manifest_version STREQUAL "version=1")
    message(FATAL_ERROR "Protocyte pre-build guard manifest has an unsupported version")
endif()
if(NOT DEFINED FAIL_ON_CHANGE)
    set(FAIL_ON_CHANGE TRUE)
endif()

set(topology_timeout_argument)
if(
    DEFINED PROTOCYTE_TOOL_TIMEOUT_SECONDS
    AND NOT "${PROTOCYTE_TOOL_TIMEOUT_SECONDS}" STREQUAL ""
)
    _protocyte_resolve_tool_timeout(topology_timeout)
    list(
        APPEND
        topology_timeout_argument
        "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=${topology_timeout}"
    )
endif()

set(changed_count 0)
foreach(manifest_line IN LISTS manifest_lines)
    string(REPLACE " " ";" manifest_fields "${manifest_line}")
    list(POP_FRONT manifest_fields manifest_kind)
    if(manifest_kind STREQUAL "source")
        list(LENGTH manifest_fields field_count)
        if(NOT field_count EQUAL 5)
            message(FATAL_ERROR "Protocyte source guard entry is malformed")
        endif()
        list(GET manifest_fields 0 encoded_argument_file)
        list(GET manifest_fields 1 encoded_proxy_file)
        list(GET manifest_fields 2 encoded_lock_file)
        list(GET manifest_fields 3 expected_hash)
        list(GET manifest_fields 4 encoded_script)
        _protocyte_decode_guard_path(argument_file "${encoded_argument_file}")
        _protocyte_decode_guard_path(guarded_file "${encoded_proxy_file}")
        _protocyte_decode_guard_path(lock_file "${encoded_lock_file}")
        _protocyte_decode_guard_path(check_script "${encoded_script}")
        string(LENGTH "${expected_hash}" expected_hash_length)
        if(
            NOT expected_hash_length EQUAL 64
            OR NOT expected_hash MATCHES "^[0-9a-fA-F]+$"
        )
            message(FATAL_ERROR "Protocyte pre-build guard entry has a malformed expected hash")
        endif()
        execute_process(
            COMMAND
                "${CMAKE_COMMAND}"
                "-DSOURCE_ARGUMENT_FILE=${argument_file}"
                "-DPROXY_FILE=${guarded_file}"
                "-DLOCK_FILE=${lock_file}"
                -P "${check_script}"
            RESULT_VARIABLE check_result
            OUTPUT_VARIABLE check_output
            ERROR_VARIABLE check_error
        )
    elseif(manifest_kind STREQUAL "topology")
        list(LENGTH manifest_fields field_count)
        if(NOT field_count EQUAL 8)
            message(FATAL_ERROR "Protocyte topology guard entry is malformed")
        endif()
        list(GET manifest_fields 0 encoded_plugin)
        list(GET manifest_fields 1 encoded_import_scan_command)
        list(GET manifest_fields 2 plugin_is_managed)
        list(GET manifest_fields 3 encoded_request_file)
        list(GET manifest_fields 4 encoded_witness_file)
        list(GET manifest_fields 5 encoded_lock_file)
        list(GET manifest_fields 6 expected_hash)
        list(GET manifest_fields 7 encoded_script)
        if(NOT plugin_is_managed MATCHES "^(TRUE|FALSE)$")
            message(FATAL_ERROR "Protocyte topology guard environment mode is malformed")
        endif()
        _protocyte_decode_guard_path(plugin_executable "${encoded_plugin}")
        _protocyte_decode_guard_path(import_scan_command "${encoded_import_scan_command}")
        _protocyte_decode_guard_path(request_file "${encoded_request_file}")
        _protocyte_decode_guard_path(guarded_file "${encoded_witness_file}")
        _protocyte_decode_guard_path(lock_file "${encoded_lock_file}")
        _protocyte_decode_guard_path(check_script "${encoded_script}")
        string(LENGTH "${expected_hash}" expected_hash_length)
        if(
            NOT expected_hash_length EQUAL 64
            OR NOT expected_hash MATCHES "^[0-9a-fA-F]+$"
        )
            message(FATAL_ERROR "Protocyte pre-build guard entry has a malformed expected hash")
        endif()
        execute_process(
            COMMAND
                "${CMAKE_COMMAND}"
                "-DPLUGIN_EXECUTABLE=${plugin_executable}"
                "-DPLUGIN_IS_MANAGED=${plugin_is_managed}"
                "-DIMPORT_SCAN_COMMAND=${import_scan_command}"
                "-DREQUEST_FILE=${request_file}"
                "-DWITNESS_FILE=${guarded_file}"
                "-DLOCK_FILE=${lock_file}"
                ${topology_timeout_argument}
                -P "${check_script}"
            RESULT_VARIABLE check_result
            OUTPUT_VARIABLE check_output
            ERROR_VARIABLE check_error
        )
    else()
        message(FATAL_ERROR "Protocyte pre-build guard entry has an unknown kind")
    endif()

    if(NOT check_result EQUAL 0)
        string(STRIP "${check_output}" check_output)
        string(STRIP "${check_error}" check_error)
        message(
            FATAL_ERROR
            "Protocyte pre-build refresh failed with exit code ${check_result}: "
            "${check_output} ${check_error}"
        )
    endif()
    if(NOT EXISTS "${guarded_file}" OR IS_DIRECTORY "${guarded_file}")
        math(EXPR changed_count "${changed_count} + 1")
        continue()
    endif()
    file(SHA256 "${guarded_file}" current_hash)
    if(NOT current_hash STREQUAL expected_hash)
        math(EXPR changed_count "${changed_count} + 1")
    endif()
endforeach()

if(changed_count GREATER 0 AND FAIL_ON_CHANGE)
    message(
        FATAL_ERROR
        "Protocyte import topology changed before code generation "
        "(${changed_count} guarded input(s)). "
        "Rebuild the target to reconfigure safely."
    )
endif()
