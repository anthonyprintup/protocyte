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
        LOCK_DIRECTORY_IDENTITY_SHA256
        LOCK_MANIFEST
        OUTPUT_DIRECTORY
        STAGING_OUTPUT_DIRECTORY
        OUT_DIR_OWNER_MARKER
        OUT_DIR_OWNER_LOCK
        BUILD_OWNER_HASH
        OWNERSHIP_MANIFEST_DIR
        SOURCE_DIRECTORY_HEX
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte generation requires ${required_variable}")
    endif()
endforeach()

function(_protocyte_load_generation_outputs out_var)
    if(
        NOT IS_DIRECTORY "${OWNERSHIP_MANIFEST_DIR}"
        OR IS_SYMLINK "${OWNERSHIP_MANIFEST_DIR}"
    )
        message(
            FATAL_ERROR
            "Protocyte generation ownership manifest is missing or unsafe for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    set(output_root_file "${OWNERSHIP_MANIFEST_DIR}/output-root.path")
    if(
        NOT EXISTS "${output_root_file}"
        OR IS_DIRECTORY "${output_root_file}"
        OR IS_SYMLINK "${output_root_file}"
    )
        message(
            FATAL_ERROR
            "Protocyte generation ownership manifest has no safe output root for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    file(READ "${output_root_file}" manifest_output_root)
    _protocyte_normalized_path_identity(
        manifest_output_root_identity
        "${manifest_output_root}"
    )
    _protocyte_normalized_path_identity(
        generation_output_root_identity
        "${OUTPUT_DIRECTORY}"
    )
    if(NOT manifest_output_root_identity STREQUAL generation_output_root_identity)
        message(
            FATAL_ERROR
            "Protocyte generation ownership manifest names a different output root for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()

    file(GLOB output_markers LIST_DIRECTORIES TRUE "${OWNERSHIP_MANIFEST_DIR}/*.path")
    list(REMOVE_ITEM output_markers "${output_root_file}")
    set(generation_outputs)
    set(manifest_output_keys)
    foreach(output_marker IN LISTS output_markers)
        if(IS_DIRECTORY "${output_marker}" OR IS_SYMLINK "${output_marker}")
            message(
                FATAL_ERROR
                "Protocyte generation ownership manifest contains an unsafe output marker for target "
                "'${GENERATION_TARGET}'. No generated output was changed."
            )
        endif()
        cmake_path(GET output_marker STEM output_key)
        string(LENGTH "${output_key}" output_key_length)
        if(NOT output_key_length EQUAL 64 OR NOT output_key MATCHES "^[0-9a-f]+$")
            message(
                FATAL_ERROR
                "Protocyte generation ownership manifest contains an invalid output identity for target "
                "'${GENERATION_TARGET}'. No generated output was changed."
            )
        endif()
        file(READ "${output_marker}" owned_output)
        cmake_path(NORMAL_PATH owned_output OUTPUT_VARIABLE normalized_owned_output)
        _protocyte_normalized_path_identity(output_identity "${normalized_owned_output}")
        string(SHA256 recorded_output_key "${output_identity}")
        list(FIND output_lock_keys "${output_key}" output_lock_index)
        _protocyte_generated_output_path_is_safe(
            output_is_safe
            "${normalized_owned_output}"
            "${manifest_output_root}"
        )
        if(
            NOT recorded_output_key STREQUAL output_key
            OR output_lock_index EQUAL -1
            OR NOT output_is_safe
        )
            message(
                FATAL_ERROR
                "Protocyte generated-output canonical containment check failed for target "
                "'${GENERATION_TARGET}'. No generated output was changed."
            )
        endif()
        list(APPEND generation_outputs "${normalized_owned_output}")
        list(APPEND manifest_output_keys "${output_key}")
    endforeach()
    list(REMOVE_DUPLICATES manifest_output_keys)
    list(SORT manifest_output_keys)
    if(NOT manifest_output_keys STREQUAL output_lock_keys)
        message(
            FATAL_ERROR
            "Protocyte generation ownership manifest does not match its output locks for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    set(${out_var} "${generation_outputs}" PARENT_SCOPE)
endfunction()

function(_protocyte_validate_generation_paths)
    _protocyte_generated_output_root_is_safe(output_root_is_safe "${OUTPUT_DIRECTORY}")
    if(NOT output_root_is_safe)
        message(
            FATAL_ERROR
            "Protocyte generated-output canonical containment check failed for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    foreach(generation_output IN LISTS generation_outputs)
        _protocyte_generated_output_path_is_safe(
            output_is_safe
            "${generation_output}"
            "${OUTPUT_DIRECTORY}"
        )
        if(NOT output_is_safe)
            message(
                FATAL_ERROR
                "Protocyte generated-output canonical containment check failed for target "
                "'${GENERATION_TARGET}'. No generated output was changed."
            )
        endif()
    endforeach()
endfunction()

function(_protocyte_validate_generation_staging_directory)
    if(NOT IS_ABSOLUTE "${STAGING_OUTPUT_DIRECTORY}")
        message(
            FATAL_ERROR
            "Protocyte generation staging directory is invalid for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    cmake_path(NORMAL_PATH OUTPUT_DIRECTORY OUTPUT_VARIABLE normalized_output_directory)
    cmake_path(
        NORMAL_PATH
        STAGING_OUTPUT_DIRECTORY
        OUTPUT_VARIABLE normalized_staging_directory
    )
    cmake_path(
        IS_PREFIX
        normalized_output_directory
        "${normalized_staging_directory}"
        NORMALIZE
        staging_is_under_output_directory
    )
    if(staging_is_under_output_directory)
        message(
            FATAL_ERROR
            "Protocyte generation staging directory is inside the configured output root for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
    _protocyte_path_has_linked_existing_component(
        staging_has_linked_component
        "${normalized_staging_directory}"
    )
    _protocyte_project_path_through_existing_components(
        projected_staging_directory
        staging_directory_is_projectable
        "${normalized_staging_directory}"
        FALSE
    )
    _protocyte_normalized_path_identity(
        expected_staging_identity
        "${normalized_staging_directory}"
    )
    _protocyte_normalized_path_identity(
        projected_staging_identity
        "${projected_staging_directory}"
    )
    if(
        staging_has_linked_component
        OR NOT staging_directory_is_projectable
        OR NOT projected_staging_identity STREQUAL expected_staging_identity
    )
        message(
            FATAL_ERROR
            "Protocyte generation staging directory is unsafe for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
endfunction()

function(_protocyte_staged_output_path out_var staging_subdirectory generation_output)
    file(
        RELATIVE_PATH
        output_relative_path
        "${OUTPUT_DIRECTORY}"
        "${generation_output}"
    )
    cmake_path(
        APPEND
        STAGING_OUTPUT_DIRECTORY
        "${staging_subdirectory}"
        "${output_relative_path}"
        OUTPUT_VARIABLE staged_output
    )
    cmake_path(NORMAL_PATH staged_output)
    set(${out_var} "${staged_output}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_release_generation_ownership
    out_released
    owner_markers_var
    transaction_id
)
    set(released FALSE)
    if("${transaction_id}" STREQUAL "")
        set(${out_released} TRUE PARENT_SCOPE)
        return()
    endif()
    string(LENGTH "${transaction_id}" transaction_id_length)
    if(NOT transaction_id_length EQUAL 64 OR NOT transaction_id MATCHES "^[0-9a-f]+$")
        set(${out_released} FALSE PARENT_SCOPE)
        return()
    endif()
    _protocyte_owner_transaction_paths(
        unused_transaction_prepared
        transaction_committed
        "${OUT_DIR_OWNER_MARKER}"
        "${transaction_id}"
    )
    if(
        NOT EXISTS "${transaction_committed}"
        OR IS_DIRECTORY "${transaction_committed}"
        OR IS_SYMLINK "${transaction_committed}"
    )
        set(${out_released} FALSE PARENT_SCOPE)
        return()
    endif()
    file(SHA256 "${transaction_committed}" observed_transaction_id)
    if(NOT observed_transaction_id STREQUAL transaction_id)
        set(${out_released} FALSE PARENT_SCOPE)
        return()
    endif()

    foreach(owner_marker IN LISTS ${owner_markers_var})
        _protocyte_owner_record_status(
            owner_status
            owner_transaction_id
            "${owner_marker}"
            "${BUILD_OWNER_HASH}"
            "${OUT_DIR_OWNER_MARKER}"
        )
        if(
            NOT owner_status STREQUAL "current"
            OR NOT owner_transaction_id STREQUAL transaction_id
        )
            set(${out_released} FALSE PARENT_SCOPE)
            return()
        endif()
    endforeach()

    foreach(owner_marker IN LISTS ${owner_markers_var})
        file(REMOVE "${owner_marker}")
        if(EXISTS "${owner_marker}" OR IS_SYMLINK "${owner_marker}")
            set(${out_released} FALSE PARENT_SCOPE)
            return()
        endif()
    endforeach()
    file(REMOVE "${transaction_committed}")
    if(NOT EXISTS "${transaction_committed}" AND NOT IS_SYMLINK "${transaction_committed}")
        set(released TRUE)
    endif()
    set(${out_released} "${released}" PARENT_SCOPE)
endfunction()

function(_protocyte_decode_generation_hex out_var encoded_value)
    string(LENGTH "${encoded_value}" encoded_length)
    math(EXPR encoded_is_odd "${encoded_length} % 2")
    if(encoded_length EQUAL 0 OR encoded_length GREATER 32768 OR encoded_is_odd)
        set(${out_var} "" PARENT_SCOPE)
        return()
    endif()
    math(EXPR encoded_last "${encoded_length} - 2")
    set(decoded_value "")
    foreach(offset RANGE 0 ${encoded_last} 2)
        string(SUBSTRING "${encoded_value}" ${offset} 2 encoded_byte)
        if(NOT encoded_byte MATCHES "^[0-9a-f][0-9a-f]$")
            set(${out_var} "" PARENT_SCOPE)
            return()
        endif()
        math(EXPR byte_value "0x${encoded_byte}")
        string(ASCII ${byte_value} decoded_character)
        string(APPEND decoded_value "${decoded_character}")
    endforeach()
    set(${out_var} "${decoded_value}" PARENT_SCOPE)
endfunction()

function(_protocyte_generation_transaction_paths out_active out_committed)
    set(transaction_prefix "${STAGING_OUTPUT_DIRECTORY}/publication.transaction")
    set(${out_active} "${transaction_prefix}.active" PARENT_SCOPE)
    set(${out_committed} "${transaction_prefix}.committed" PARENT_SCOPE)
endfunction()

function(
    _protocyte_write_generation_transaction
    out_written
    owner_markers_var
    initial_states_var
    operation_states_var
)
    set(${out_written} FALSE PARENT_SCOPE)
    list(LENGTH generation_outputs generation_output_count)
    list(LENGTH ${initial_states_var} initial_state_count)
    list(LENGTH ${operation_states_var} operation_state_count)
    if(
        NOT initial_state_count EQUAL generation_output_count
        OR NOT operation_state_count EQUAL generation_output_count
    )
        return()
    endif()
    _protocyte_generation_transaction_paths(transaction_active transaction_committed)
    set(transaction_content "version=1\nbuild-tree-sha256=${BUILD_OWNER_HASH}\n")
    list(LENGTH ${owner_markers_var} owner_marker_count)
    string(APPEND transaction_content "owner-count=${owner_marker_count}\n")
    foreach(owner_marker IN LISTS ${owner_markers_var})
        string(HEX "${owner_marker}" encoded_owner_marker)
        string(APPEND transaction_content "owner-hex=${encoded_owner_marker}\n")
    endforeach()
    string(APPEND transaction_content "output-count=${generation_output_count}\n")
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            list(GET generation_outputs ${generation_output_index} generation_output)
            list(GET ${initial_states_var} ${generation_output_index} initial_state)
            list(GET ${operation_states_var} ${generation_output_index} operation_state)
            if(
                NOT (initial_state STREQUAL "prior" OR initial_state STREQUAL "absent")
                OR NOT (
                    operation_state STREQUAL "untouched"
                    OR operation_state STREQUAL "backup-pending"
                    OR operation_state STREQUAL "backed-up"
                    OR operation_state STREQUAL "publish-pending"
                    OR operation_state STREQUAL "published"
                )
            )
                return()
            endif()
            string(HEX "${generation_output}" encoded_generation_output)
            string(APPEND transaction_content "output-hex=${encoded_generation_output}\n")
            string(APPEND transaction_content "initial=${initial_state}\n")
            string(APPEND transaction_content "state=${operation_state}\n")
        endforeach()
    endif()

    set(transaction_staging "${transaction_active}.tmp")
    file(WRITE "${transaction_staging}" "${transaction_content}")
    if(
        NOT EXISTS "${transaction_staging}"
        OR IS_DIRECTORY "${transaction_staging}"
        OR IS_SYMLINK "${transaction_staging}"
    )
        return()
    endif()
    file(READ "${transaction_staging}" observed_transaction_content)
    if(NOT observed_transaction_content STREQUAL transaction_content)
        return()
    endif()
    file(
        RENAME "${transaction_staging}" "${transaction_active}"
        RESULT transaction_write_result
    )
    if("${transaction_write_result}" STREQUAL "0")
        set(${out_written} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(
    _protocyte_read_generation_transaction
    out_is_present
    out_is_committed
    out_owner_markers
    out_initial_states
    out_operation_states
)
    set(${out_is_present} FALSE PARENT_SCOPE)
    set(${out_is_committed} FALSE PARENT_SCOPE)
    set(${out_owner_markers} "" PARENT_SCOPE)
    set(${out_initial_states} "" PARENT_SCOPE)
    set(${out_operation_states} "" PARENT_SCOPE)
    _protocyte_generation_transaction_paths(transaction_active transaction_committed)
    if(
        (EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        AND (EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
    )
        return()
    endif()
    if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        set(transaction_record "${transaction_active}")
        set(transaction_is_committed FALSE)
    elseif(EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
        set(transaction_record "${transaction_committed}")
        set(transaction_is_committed TRUE)
    else()
        return()
    endif()
    if(IS_DIRECTORY "${transaction_record}" OR IS_SYMLINK "${transaction_record}")
        return()
    endif()
    file(SIZE "${transaction_record}" transaction_size)
    if(transaction_size GREATER 16777216)
        return()
    endif()
    file(STRINGS "${transaction_record}" transaction_lines)
    list(LENGTH transaction_lines transaction_line_count)
    if(transaction_line_count LESS 4)
        return()
    endif()
    list(GET transaction_lines 0 transaction_version)
    list(GET transaction_lines 1 transaction_build_hash_line)
    list(GET transaction_lines 2 transaction_owner_count_line)
    if(
        NOT transaction_version STREQUAL "version=1"
        OR NOT transaction_build_hash_line STREQUAL "build-tree-sha256=${BUILD_OWNER_HASH}"
        OR NOT transaction_owner_count_line MATCHES "^owner-count=([0-9]+)$"
    )
        return()
    endif()
    set(transaction_owner_count "${CMAKE_MATCH_1}")
    if(transaction_owner_count GREATER 256)
        return()
    endif()
    set(transaction_line_index 3)
    set(transaction_owner_markers)
    if(transaction_owner_count GREATER 0)
        math(EXPR last_owner_index "${transaction_owner_count} - 1")
        foreach(owner_index RANGE 0 ${last_owner_index})
            if(transaction_line_index GREATER_EQUAL transaction_line_count)
                return()
            endif()
            list(GET transaction_lines ${transaction_line_index} owner_line)
            if(NOT owner_line MATCHES "^owner-hex=([0-9a-f]+)$")
                return()
            endif()
            _protocyte_decode_generation_hex(owner_marker "${CMAKE_MATCH_1}")
            if(owner_marker STREQUAL "")
                return()
            endif()
            list(APPEND transaction_owner_markers "${owner_marker}")
            math(EXPR transaction_line_index "${transaction_line_index} + 1")
        endforeach()
    endif()
    if(transaction_line_index GREATER_EQUAL transaction_line_count)
        return()
    endif()
    list(GET transaction_lines ${transaction_line_index} transaction_output_count_line)
    if(NOT transaction_output_count_line MATCHES "^output-count=([0-9]+)$")
        return()
    endif()
    set(transaction_output_count "${CMAKE_MATCH_1}")
    list(LENGTH generation_outputs generation_output_count)
    if(NOT transaction_output_count EQUAL generation_output_count)
        return()
    endif()
    math(EXPR transaction_line_index "${transaction_line_index} + 1")
    set(transaction_initial_states)
    set(transaction_operation_states)
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            math(EXPR transaction_last_output_line "${transaction_line_index} + 2")
            if(transaction_last_output_line GREATER_EQUAL transaction_line_count)
                return()
            endif()
            list(GET transaction_lines ${transaction_line_index} transaction_output_line)
            math(EXPR transaction_initial_line_index "${transaction_line_index} + 1")
            math(EXPR transaction_state_line_index "${transaction_line_index} + 2")
            list(GET transaction_lines ${transaction_initial_line_index} transaction_initial_line)
            list(GET transaction_lines ${transaction_state_line_index} transaction_state_line)
            if(NOT transaction_output_line MATCHES "^output-hex=([0-9a-f]+)$")
                return()
            endif()
            set(encoded_transaction_output "${CMAKE_MATCH_1}")
            if(NOT transaction_initial_line MATCHES "^initial=(prior|absent)$")
                return()
            endif()
            if(
                NOT transaction_state_line MATCHES
                "^state=(untouched|backup-pending|backed-up|publish-pending|published)$"
            )
                return()
            endif()
            _protocyte_decode_generation_hex(
                transaction_output
                "${encoded_transaction_output}"
            )
            list(GET generation_outputs ${generation_output_index} generation_output)
            _protocyte_normalized_path_identity(
                transaction_output_identity
                "${transaction_output}"
            )
            _protocyte_normalized_path_identity(
                generation_output_identity
                "${generation_output}"
            )
            if(NOT transaction_output_identity STREQUAL generation_output_identity)
                return()
            endif()
            string(REGEX REPLACE "^initial=" "" transaction_initial_state "${transaction_initial_line}")
            string(REGEX REPLACE "^state=" "" transaction_operation_state "${transaction_state_line}")
            list(APPEND transaction_initial_states "${transaction_initial_state}")
            list(APPEND transaction_operation_states "${transaction_operation_state}")
            math(EXPR transaction_line_index "${transaction_line_index} + 3")
        endforeach()
    endif()
    if(NOT transaction_line_index EQUAL transaction_line_count)
        return()
    endif()
    set(${out_is_present} TRUE PARENT_SCOPE)
    set(${out_is_committed} "${transaction_is_committed}" PARENT_SCOPE)
    set(${out_owner_markers} "${transaction_owner_markers}" PARENT_SCOPE)
    set(${out_initial_states} "${transaction_initial_states}" PARENT_SCOPE)
    set(${out_operation_states} "${transaction_operation_states}" PARENT_SCOPE)
endfunction()

function(_protocyte_recover_generation_transaction out_recovered)
    set(${out_recovered} FALSE PARENT_SCOPE)
    _protocyte_generation_transaction_paths(transaction_active transaction_committed)
    if(
        (EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        AND (EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
    )
        return()
    endif()
    foreach(transaction_record IN ITEMS "${transaction_active}" "${transaction_committed}")
        if(
            (EXISTS "${transaction_record}" OR IS_SYMLINK "${transaction_record}")
            AND (IS_DIRECTORY "${transaction_record}" OR IS_SYMLINK "${transaction_record}")
        )
            return()
        endif()
    endforeach()
    _protocyte_read_generation_transaction(
        transaction_is_present
        transaction_is_committed
        transaction_owner_markers
        transaction_initial_states
        transaction_operation_states
    )
    if(NOT transaction_is_present)
        if(
            NOT EXISTS "${transaction_active}"
            AND NOT IS_SYMLINK "${transaction_active}"
            AND NOT EXISTS "${transaction_committed}"
            AND NOT IS_SYMLINK "${transaction_committed}"
        )
            set(${out_recovered} TRUE PARENT_SCOPE)
        endif()
        return()
    endif()
    if(transaction_is_committed)
        foreach(transaction_operation_state IN LISTS transaction_operation_states)
            if(NOT transaction_operation_state STREQUAL "published")
                return()
            endif()
        endforeach()
        foreach(generation_output IN LISTS generation_outputs)
            if(
                NOT EXISTS "${generation_output}"
                OR IS_DIRECTORY "${generation_output}"
                OR IS_SYMLINK "${generation_output}"
            )
                return()
            endif()
        endforeach()
        set(${out_recovered} TRUE PARENT_SCOPE)
        return()
    endif()

    list(LENGTH generation_outputs generation_output_count)
    math(EXPR last_generation_output_index "${generation_output_count} - 1")
    foreach(generation_output_index RANGE 0 ${last_generation_output_index})
        list(GET generation_outputs ${generation_output_index} generation_output)
        list(GET transaction_initial_states ${generation_output_index} transaction_initial_state)
        list(GET transaction_operation_states ${generation_output_index} transaction_operation_state)
        _protocyte_staged_output_path(
            backup_generation_output
            "backups"
            "${generation_output}"
        )
        _protocyte_generated_output_path_is_safe(
            backup_output_is_safe
            "${backup_generation_output}"
            "${STAGING_OUTPUT_DIRECTORY}/backups"
        )
        if(NOT backup_output_is_safe)
            return()
        endif()
        if(transaction_initial_state STREQUAL "prior")
            if(transaction_operation_state STREQUAL "untouched")
                if(
                    NOT EXISTS "${generation_output}"
                    OR IS_DIRECTORY "${generation_output}"
                    OR IS_SYMLINK "${generation_output}"
                    OR EXISTS "${backup_generation_output}"
                    OR IS_SYMLINK "${backup_generation_output}"
                )
                    return()
                endif()
            elseif(transaction_operation_state STREQUAL "backup-pending")
                if(EXISTS "${backup_generation_output}")
                    if(
                        IS_DIRECTORY "${backup_generation_output}"
                        OR IS_SYMLINK "${backup_generation_output}"
                        OR EXISTS "${generation_output}"
                        OR IS_SYMLINK "${generation_output}"
                    )
                        return()
                    endif()
                    file(
                        RENAME "${backup_generation_output}" "${generation_output}"
                        NO_REPLACE
                        RESULT restore_output_result
                    )
                    if(NOT "${restore_output_result}" STREQUAL "0")
                        return()
                    endif()
                elseif(
                    NOT EXISTS "${generation_output}"
                    OR IS_DIRECTORY "${generation_output}"
                    OR IS_SYMLINK "${generation_output}"
                )
                    return()
                endif()
            elseif(
                transaction_operation_state STREQUAL "backed-up"
                OR transaction_operation_state STREQUAL "publish-pending"
                OR transaction_operation_state STREQUAL "published"
            )
                if(
                    NOT EXISTS "${backup_generation_output}"
                    OR IS_DIRECTORY "${backup_generation_output}"
                    OR IS_SYMLINK "${backup_generation_output}"
                )
                    return()
                endif()
                if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                    if(
                        IS_DIRECTORY "${generation_output}"
                        OR IS_SYMLINK "${generation_output}"
                    )
                        return()
                    endif()
                    file(REMOVE "${generation_output}")
                    if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                        return()
                    endif()
                endif()
                file(
                    RENAME "${backup_generation_output}" "${generation_output}"
                    NO_REPLACE
                    RESULT restore_output_result
                )
                if(NOT "${restore_output_result}" STREQUAL "0")
                    return()
                endif()
            else()
                return()
            endif()
        elseif(transaction_initial_state STREQUAL "absent")
            if(
                transaction_operation_state STREQUAL "publish-pending"
                OR transaction_operation_state STREQUAL "published"
            )
                if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                    if(
                        IS_DIRECTORY "${generation_output}"
                        OR IS_SYMLINK "${generation_output}"
                    )
                        return()
                    endif()
                    file(REMOVE "${generation_output}")
                    if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                        return()
                    endif()
                endif()
            elseif(NOT transaction_operation_state STREQUAL "untouched")
                return()
            endif()
            if(EXISTS "${backup_generation_output}" OR IS_SYMLINK "${backup_generation_output}")
                return()
            endif()
        else()
            return()
        endif()
    endforeach()

    set(allowed_transaction_owner_markers "${OUT_DIR_OWNER_MARKER}")
    foreach(output_lock_key IN LISTS output_lock_keys)
        list(
            APPEND
            allowed_transaction_owner_markers
            "${LOCK_DIRECTORY}/${output_lock_key}.owner"
        )
    endforeach()
    list(LENGTH transaction_owner_markers transaction_owner_count)
    set(unique_transaction_owner_markers "${transaction_owner_markers}")
    list(REMOVE_DUPLICATES unique_transaction_owner_markers)
    list(LENGTH unique_transaction_owner_markers unique_transaction_owner_count)
    if(NOT unique_transaction_owner_count EQUAL transaction_owner_count)
        return()
    endif()
    foreach(transaction_owner_marker IN LISTS transaction_owner_markers)
        list(
            FIND
            allowed_transaction_owner_markers
            "${transaction_owner_marker}"
            allowed_owner_index
        )
        if(allowed_owner_index EQUAL -1)
            return()
        endif()
    endforeach()

    set(current_transaction_owner_markers)
    set(observed_transaction_ids)
    foreach(transaction_owner_marker IN LISTS transaction_owner_markers)
        _protocyte_owner_record_status(
            transaction_owner_status
            transaction_owner_id
            "${transaction_owner_marker}"
            "${BUILD_OWNER_HASH}"
            "${OUT_DIR_OWNER_MARKER}"
        )
        if(transaction_owner_status STREQUAL "incomplete")
            _protocyte_recover_incomplete_owner_record(
                recovered_incomplete_transaction_owner
                "${transaction_owner_marker}"
                "${transaction_owner_id}"
                "${OUT_DIR_OWNER_MARKER}"
            )
            if(NOT recovered_incomplete_transaction_owner)
                return()
            endif()
        elseif(transaction_owner_status STREQUAL "current")
            if("${transaction_owner_id}" STREQUAL "")
                return()
            endif()
            list(APPEND current_transaction_owner_markers "${transaction_owner_marker}")
            list(APPEND observed_transaction_ids "${transaction_owner_id}")
        elseif(NOT transaction_owner_status STREQUAL "missing")
            return()
        endif()
    endforeach()
    if(current_transaction_owner_markers)
        list(LENGTH current_transaction_owner_markers current_transaction_owner_count)
        list(REMOVE_DUPLICATES observed_transaction_ids)
        list(LENGTH observed_transaction_ids observed_transaction_id_count)
        if(
            NOT current_transaction_owner_count EQUAL transaction_owner_count
            OR NOT observed_transaction_id_count EQUAL 1
        )
            return()
        endif()
        list(GET observed_transaction_ids 0 observed_transaction_id)
        _protocyte_release_generation_ownership(
            released_generation_ownership
            "current_transaction_owner_markers"
            "${observed_transaction_id}"
        )
        if(NOT released_generation_ownership)
            return()
        endif()
    endif()
    file(REMOVE "${transaction_active}")
    if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        return()
    endif()
    set(${out_recovered} TRUE PARENT_SCOPE)
endfunction()

function(_protocyte_discard_generation_staging)
    # The staging directory is not a declared custom-command output.  Never
    # recurse through a link if a concurrent actor replaced it; retaining an
    # inert staging tree is safer than following it during error cleanup.
    _protocyte_path_has_linked_existing_component(
        staging_has_linked_component
        "${STAGING_OUTPUT_DIRECTORY}"
    )
    if(staging_has_linked_component)
        message(
            WARNING
            "Protocyte left unsafe staging data at '${STAGING_OUTPUT_DIRECTORY}' for target "
            "'${GENERATION_TARGET}'. It contains no declared generated output and must be removed manually."
        )
        return()
    endif()
    file(REMOVE_RECURSE "${STAGING_OUTPUT_DIRECTORY}")
    if(EXISTS "${STAGING_OUTPUT_DIRECTORY}" OR IS_SYMLINK "${STAGING_OUTPUT_DIRECTORY}")
        message(
            WARNING
            "Protocyte could not remove staging data at '${STAGING_OUTPUT_DIRECTORY}' for target "
            "'${GENERATION_TARGET}'. It contains no declared generated output and may be removed manually."
        )
    endif()
endfunction()

function(_protocyte_validate_generation_lock_namespace)
    string(
        LENGTH
        "${LOCK_DIRECTORY_IDENTITY_SHA256}"
        lock_directory_identity_hash_length
    )
    if(
        NOT lock_directory_identity_hash_length EQUAL 64
        OR NOT LOCK_DIRECTORY_IDENTITY_SHA256 MATCHES "^[0-9a-f]+$"
    )
        message(
            FATAL_ERROR
            "Protocyte generation received an invalid configured output-lock identity for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()

    _protocyte_path_has_linked_existing_component(
        lock_directory_has_linked_component
        "${LOCK_DIRECTORY}"
    )
    if(lock_directory_has_linked_component)
        message(
            FATAL_ERROR
            "Protocyte generation refused output-lock directory '${LOCK_DIRECTORY}' for target "
            "'${GENERATION_TARGET}' because it now contains a symbolic-link or junction component. "
            "Restore a link-free directory at the configured canonical path and reconfigure before building. "
            "No generated output was changed."
        )
    endif()

    _protocyte_project_path_through_existing_components(
        observed_lock_directory
        lock_directory_is_projectable
        "${LOCK_DIRECTORY}"
        FALSE
    )
    if(lock_directory_is_projectable)
        _protocyte_normalized_path_identity(
            observed_lock_directory_identity
            "${observed_lock_directory}"
        )
        string(
            SHA256
            observed_lock_directory_identity_hash
            "${observed_lock_directory_identity}"
        )
    else()
        set(observed_lock_directory_identity_hash "")
    endif()
    if(
        NOT lock_directory_is_projectable
        OR NOT observed_lock_directory_identity_hash STREQUAL LOCK_DIRECTORY_IDENTITY_SHA256
    )
        message(
            FATAL_ERROR
            "Protocyte generation refused output-lock directory '${LOCK_DIRECTORY}' for target "
            "'${GENERATION_TARGET}' because it no longer resolves to the canonical namespace recorded during "
            "configuration. Restore the configured link-free directory and reconfigure before building. "
            "No generated output was changed."
        )
    endif()
endfunction()

if(NOT EXISTS "${LOCK_MANIFEST}")
    message(FATAL_ERROR "Protocyte generation lock manifest does not exist: ${LOCK_MANIFEST}")
endif()

file(STRINGS "${LOCK_MANIFEST}" output_lock_keys)
if(NOT output_lock_keys)
    message(FATAL_ERROR "Protocyte generation lock manifest is empty: ${LOCK_MANIFEST}")
endif()
list(REMOVE_DUPLICATES output_lock_keys)
list(SORT output_lock_keys)

string(LENGTH "${BUILD_OWNER_HASH}" build_owner_hash_length)
if(NOT build_owner_hash_length EQUAL 64 OR NOT BUILD_OWNER_HASH MATCHES "^[0-9a-f]+$")
    message(FATAL_ERROR "Protocyte generation received an invalid build-owner identity")
endif()

foreach(output_lock_key IN LISTS output_lock_keys)
    string(LENGTH "${output_lock_key}" output_lock_key_length)
    if(NOT output_lock_key_length EQUAL 64 OR NOT "${output_lock_key}" MATCHES "^[0-9a-f]+$")
        message(
            FATAL_ERROR
            "Protocyte generation lock manifest contains an invalid output identity: ${output_lock_key}"
        )
    endif()
endforeach()

# Re-attest the configured namespace before creating or locking anything. The
# second check detects replacement during directory creation before ownership
# records or generated outputs can be touched.
_protocyte_validate_generation_lock_namespace()
file(MAKE_DIRECTORY "${LOCK_DIRECTORY}")
_protocyte_validate_generation_lock_namespace()
foreach(output_lock_key IN LISTS output_lock_keys)
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

_protocyte_load_generation_outputs(generation_outputs)
_protocyte_validate_generation_paths()
_protocyte_validate_generation_staging_directory()

# Hold the root ownership lock while recovering an interrupted publication.
# The output locks above serialize every declared output; together they make
# the on-disk transaction record safe to reconcile before owner status is read.
cmake_path(GET OUT_DIR_OWNER_MARKER PARENT_PATH out_dir_owner_parent)
file(MAKE_DIRECTORY "${out_dir_owner_parent}")
file(
    LOCK "${OUT_DIR_OWNER_LOCK}"
    GUARD PROCESS
    TIMEOUT 600
    RESULT_VARIABLE owner_lock_result
)
if(NOT "${owner_lock_result}" STREQUAL "0")
    message(
        FATAL_ERROR
        "Failed to lock OUT_DIR ownership for target '${GENERATION_TARGET}': ${owner_lock_result}"
    )
endif()
_protocyte_recover_generation_transaction(recovered_generation_transaction)
if(NOT recovered_generation_transaction)
    message(
        FATAL_ERROR
        "Protocyte could not safely recover an interrupted generation transaction for target "
        "'${GENERATION_TARGET}'. No generated output was changed."
    )
endif()

function(
    _protocyte_recover_published_transaction_owners
    out_all_recovered
    owner_markers_var
    transaction_id
)
    set(all_recovered TRUE)
    foreach(owner_marker IN LISTS ${owner_markers_var})
        _protocyte_recover_incomplete_owner_record(
            recovered_owner
            "${owner_marker}"
            "${transaction_id}"
            "${OUT_DIR_OWNER_MARKER}"
        )
        if(NOT recovered_owner)
            set(all_recovered FALSE)
        endif()
    endforeach()
    set(${out_all_recovered} "${all_recovered}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_commit_generation_ownership
    out_transaction_id
    out_published_owner_markers
)
    set(${out_transaction_id} "" PARENT_SCOPE)
    set(${out_published_owner_markers} "" PARENT_SCOPE)
    set(owner_markers_to_publish)
    if(root_owner_is_missing)
        list(APPEND owner_markers_to_publish "${OUT_DIR_OWNER_MARKER}")
    endif()
    foreach(output_lock_key IN LISTS missing_output_owner_keys)
        list(
            APPEND
            owner_markers_to_publish
            "${LOCK_DIRECTORY}/${output_lock_key}.owner"
        )
    endforeach()
    if(NOT owner_markers_to_publish)
        return()
    endif()

    set(owner_claim_ids)
    foreach(owner_marker IN LISTS owner_markers_to_publish)
        _protocyte_normalized_path_identity(owner_marker_identity "${owner_marker}")
        string(SHA256 owner_claim_id "${owner_marker_identity}")
        list(APPEND owner_claim_ids "${owner_claim_id}")
    endforeach()
    list(SORT owner_claim_ids)
    string(SHA256 claims_hash "${owner_claim_ids}")
    string(RANDOM LENGTH 64 ALPHABET 0123456789abcdef transaction_nonce)
    set(
        transaction_manifest
        "version=1\nnonce=${transaction_nonce}\nbuild-tree-sha256=${BUILD_OWNER_HASH}\nclaims-sha256=${claims_hash}\n"
    )
    foreach(owner_claim_id IN LISTS owner_claim_ids)
        string(APPEND transaction_manifest "claim-sha256=${owner_claim_id}\n")
    endforeach()
    set(transaction_staging "${OUT_DIR_OWNER_MARKER}.${transaction_nonce}.tmp")

    # Stage and read back the complete transaction before any durable owner
    # record is published. A staging failure can therefore leave only inert
    # temporary files, never a claim that blocks another build tree.
    file(WRITE "${transaction_staging}" "${transaction_manifest}")
    file(READ "${transaction_staging}" observed_transaction_manifest)
    if(NOT "${observed_transaction_manifest}" STREQUAL "${transaction_manifest}")
        message(
            FATAL_ERROR
            "Protocyte could not validate staged ownership transaction for target "
            "'${GENERATION_TARGET}'. No durable ownership was published."
        )
    endif()
    file(SHA256 "${transaction_staging}" transaction_id)
    _protocyte_owner_transaction_paths(
        transaction_prepared
        transaction_committed
        "${OUT_DIR_OWNER_MARKER}"
        "${transaction_id}"
    )
    file(
        RENAME "${transaction_staging}" "${transaction_prepared}"
        NO_REPLACE
        RESULT transaction_stage_result
    )
    if(NOT "${transaction_stage_result}" STREQUAL "0")
        file(REMOVE "${transaction_staging}")
        message(
            FATAL_ERROR
            "Protocyte could not stage ownership transaction for target "
            "'${GENERATION_TARGET}': ${transaction_stage_result}"
        )
    endif()
    set(
        transaction_owner
        "version=2\nbuild-tree-sha256=${BUILD_OWNER_HASH}\ntransaction-sha256=${transaction_id}\n"
    )

    set(staged_owner_markers)
    set(owner_stage_index 0)
    foreach(owner_marker IN LISTS owner_markers_to_publish)
        math(EXPR owner_stage_index "${owner_stage_index} + 1")
        set(owner_staging "${owner_marker}.${transaction_id}.tmp")
        file(WRITE "${owner_staging}" "${transaction_owner}")
        file(READ "${owner_staging}" observed_transaction_owner LIMIT 512)
        if(NOT "${observed_transaction_owner}" STREQUAL "${transaction_owner}")
            message(
                FATAL_ERROR
                "Protocyte could not validate a staged ownership record for target "
                "'${GENERATION_TARGET}'. No durable ownership was published."
            )
        endif()
        list(APPEND staged_owner_markers "${owner_staging}")
    endforeach()

    set(published_owner_markers)
    list(LENGTH owner_markers_to_publish owner_marker_count)
    math(EXPR last_owner_marker_index "${owner_marker_count} - 1")
    foreach(owner_marker_index RANGE 0 ${last_owner_marker_index})
        list(GET owner_markers_to_publish ${owner_marker_index} owner_marker)
        list(GET staged_owner_markers ${owner_marker_index} owner_staging)
        file(
            RENAME "${owner_staging}" "${owner_marker}"
            NO_REPLACE
            RESULT owner_publish_result
        )
        if(NOT "${owner_publish_result}" STREQUAL "0")
            _protocyte_recover_published_transaction_owners(
                all_published_owners_recovered
                published_owner_markers
                "${transaction_id}"
            )
            if(all_published_owners_recovered)
                file(REMOVE "${transaction_prepared}")
            endif()
            message(
                FATAL_ERROR
                "Protocyte could not publish ownership for target "
                "'${GENERATION_TARGET}': ${owner_publish_result}"
            )
        endif()
        list(APPEND published_owner_markers "${owner_marker}")
    endforeach()

    # This atomic rename is the sole commit point. Before it, every published
    # owner record is recoverable as incomplete; after it, the content-addressed
    # manifest proves that the complete prepared claim set was published.
    file(
        RENAME "${transaction_prepared}" "${transaction_committed}"
        NO_REPLACE
        RESULT transaction_publish_result
    )
    if(NOT "${transaction_publish_result}" STREQUAL "0")
        _protocyte_recover_published_transaction_owners(
            all_published_owners_recovered
            published_owner_markers
            "${transaction_id}"
        )
        if(all_published_owners_recovered)
            file(REMOVE "${transaction_prepared}")
        endif()
        message(
            FATAL_ERROR
            "Protocyte could not commit ownership for target "
            "'${GENERATION_TARGET}': ${transaction_publish_result}"
        )
    endif()
    set(${out_transaction_id} "${transaction_id}" PARENT_SCOPE)
    set(${out_published_owner_markers} "${owner_markers_to_publish}" PARENT_SCOPE)
endfunction()

set(missing_output_owner_keys)
foreach(output_lock_key IN LISTS output_lock_keys)
    set(output_owner_marker "${LOCK_DIRECTORY}/${output_lock_key}.owner")
    _protocyte_owner_record_status(
        output_owner_status
        output_owner_transaction_id
        "${output_owner_marker}"
        "${BUILD_OWNER_HASH}"
        "${OUT_DIR_OWNER_MARKER}"
    )
    if(output_owner_status STREQUAL "incomplete")
        _protocyte_recover_incomplete_owner_record(
            recovered_incomplete_owner
            "${output_owner_marker}"
            "${output_owner_transaction_id}"
            "${OUT_DIR_OWNER_MARKER}"
        )
        if(recovered_incomplete_owner)
            set(output_owner_status "missing")
        else()
            _protocyte_owner_record_status(
                output_owner_status
                unused_output_transaction_id
                "${output_owner_marker}"
                "${BUILD_OWNER_HASH}"
                "${OUT_DIR_OWNER_MARKER}"
            )
        endif()
    endif()
    if(output_owner_status STREQUAL "missing")
        list(APPEND missing_output_owner_keys "${output_lock_key}")
    elseif(output_owner_status STREQUAL "different")
        message(
            FATAL_ERROR
            "Generated-output ownership belongs to a different build tree for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    elseif(output_owner_status STREQUAL "unverifiable")
        _protocyte_owner_transaction_paths(
            unused_output_prepared_witness
            output_committed_witness
            "${OUT_DIR_OWNER_MARKER}"
            "${output_owner_transaction_id}"
        )
        message(
            FATAL_ERROR
            "Generated-output ownership record '${output_owner_marker}' references missing or unverifiable "
            "transaction witness '${output_committed_witness}' for target '${GENERATION_TARGET}'. Protocyte "
            "will not reclaim the output automatically. Choose disjoint generated outputs, restore the witness, "
            "or, after confirming no build uses the output, remove '${output_owner_marker}' manually and "
            "reconfigure. No generated output was changed."
        )
    elseif(NOT output_owner_status STREQUAL "current")
        message(
            FATAL_ERROR
            "Generated-output ownership is malformed or could not be recovered for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
endforeach()

set(root_owner_is_missing FALSE)
_protocyte_owner_record_status(
    root_owner_status
    root_owner_transaction_id
    "${OUT_DIR_OWNER_MARKER}"
    "${BUILD_OWNER_HASH}"
    "${OUT_DIR_OWNER_MARKER}"
)
if(root_owner_status STREQUAL "incomplete")
    _protocyte_recover_incomplete_owner_record(
        recovered_incomplete_root_owner
        "${OUT_DIR_OWNER_MARKER}"
        "${root_owner_transaction_id}"
        "${OUT_DIR_OWNER_MARKER}"
    )
    if(recovered_incomplete_root_owner)
        set(root_owner_status "missing")
    else()
        _protocyte_owner_record_status(
            root_owner_status
            unused_root_transaction_id
            "${OUT_DIR_OWNER_MARKER}"
            "${BUILD_OWNER_HASH}"
            "${OUT_DIR_OWNER_MARKER}"
        )
    endif()
endif()
if(root_owner_status STREQUAL "missing")
    set(root_owner_is_missing TRUE)
elseif(root_owner_status STREQUAL "different")
    message(
        FATAL_ERROR
        "OUT_DIR ownership belongs to a different build tree for target "
        "'${GENERATION_TARGET}'. No generated output was changed."
    )
elseif(root_owner_status STREQUAL "unverifiable")
    _protocyte_owner_transaction_paths(
        unused_root_prepared_witness
        root_committed_witness
        "${OUT_DIR_OWNER_MARKER}"
        "${root_owner_transaction_id}"
    )
    message(
        FATAL_ERROR
        "OUT_DIR ownership record '${OUT_DIR_OWNER_MARKER}' references missing or unverifiable transaction "
        "witness '${root_committed_witness}' for target '${GENERATION_TARGET}'. Protocyte will not reclaim the "
        "OUT_DIR automatically. Reuse the owning build tree, choose a different OUT_DIR, restore the witness, "
        "or, after confirming no build uses the OUT_DIR, remove '${OUT_DIR_OWNER_MARKER}' manually and "
        "reconfigure. No generated output was changed."
    )
elseif(NOT root_owner_status STREQUAL "current")
    message(
        FATAL_ERROR
        "OUT_DIR ownership is malformed or could not be recovered for target "
        "'${GENERATION_TARGET}'. No generated output was changed."
    )
endif()

file(MAKE_DIRECTORY "${OUTPUT_DIRECTORY}")
_protocyte_validate_generation_paths()
_protocyte_validate_generation_staging_directory()
_protocyte_discard_generation_staging()
file(MAKE_DIRECTORY "${STAGING_OUTPUT_DIRECTORY}/generated")
_protocyte_validate_generation_staging_directory()

set(staged_generation_outputs)
foreach(generation_output IN LISTS generation_outputs)
    _protocyte_staged_output_path(
        staged_generation_output
        "generated"
        "${generation_output}"
    )
    _protocyte_generated_output_path_is_safe(
        staged_output_is_safe
        "${staged_generation_output}"
        "${STAGING_OUTPUT_DIRECTORY}/generated"
    )
    if(NOT staged_output_is_safe)
        _protocyte_discard_generation_staging()
        message(
            FATAL_ERROR
            "Protocyte generation staging path is unsafe for target '${GENERATION_TARGET}'. "
            "No generated output was changed."
        )
    endif()
    list(APPEND staged_generation_outputs "${staged_generation_output}")
endforeach()

set(protoc_environment)
if(PROTOCYTE_MANAGED_PLUGIN)
    # protoc inherits this environment when it launches the managed Python
    # plugin; explicit user-provided plugins keep their environment unchanged.
    list(APPEND protoc_environment "--unset=PYTHONPATH" "--unset=PYTHONHOME")
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
    _protocyte_discard_generation_staging()
    message(
        FATAL_ERROR
        "Protocyte generation for target '${GENERATION_TARGET}' timed out after ${protocyte_tool_timeout} seconds. "
        "Staged generation output was discarded before ownership was published. Set "
        "PROTOCYTE_TOOL_TIMEOUT_SECONDS to a larger value or 0 to disable this timeout."
    )
endif()
if(NOT "${protoc_result}" STREQUAL "0")
    _protocyte_discard_generation_staging()
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

foreach(staged_generation_output IN LISTS staged_generation_outputs)
    if(
        NOT EXISTS "${staged_generation_output}"
        OR IS_DIRECTORY "${staged_generation_output}"
        OR IS_SYMLINK "${staged_generation_output}"
    )
        _protocyte_discard_generation_staging()
        message(
            FATAL_ERROR
            "Protocyte generation for target '${GENERATION_TARGET}' did not produce every expected staged output. "
            "No generated output was changed."
        )
    endif()
    _protocyte_generated_output_path_is_safe(
        staged_output_is_safe
        "${staged_generation_output}"
        "${STAGING_OUTPUT_DIRECTORY}/generated"
    )
    if(NOT staged_output_is_safe)
        _protocyte_discard_generation_staging()
        message(
            FATAL_ERROR
            "Protocyte generation produced an unsafe staged output for target '${GENERATION_TARGET}'. "
            "No generated output was changed."
        )
    endif()
endforeach()
_protocyte_validate_generation_paths()
_protocyte_validate_generation_staging_directory()

set(generation_initial_states)
set(generation_operation_states)
foreach(generation_output IN LISTS generation_outputs)
    if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
        if(
            IS_DIRECTORY "${generation_output}"
            OR IS_SYMLINK "${generation_output}"
        )
            _protocyte_discard_generation_staging()
            message(
                FATAL_ERROR
                "Protocyte cannot replace unsafe existing output '${generation_output}' for target "
                "'${GENERATION_TARGET}'. No generated output was changed."
            )
        endif()
        list(APPEND generation_initial_states "prior")
    else()
        list(APPEND generation_initial_states "absent")
    endif()
    list(APPEND generation_operation_states "untouched")
endforeach()
set(generation_transaction_owner_markers)
if(root_owner_is_missing)
    list(APPEND generation_transaction_owner_markers "${OUT_DIR_OWNER_MARKER}")
endif()
foreach(output_lock_key IN LISTS missing_output_owner_keys)
    list(
        APPEND
        generation_transaction_owner_markers
        "${LOCK_DIRECTORY}/${output_lock_key}.owner"
    )
endforeach()
_protocyte_write_generation_transaction(
    generation_transaction_written
    generation_transaction_owner_markers
    generation_initial_states
    generation_operation_states
)
if(NOT generation_transaction_written)
    _protocyte_discard_generation_staging()
    message(
        FATAL_ERROR
        "Protocyte could not persist the generation transaction for target '${GENERATION_TARGET}'. "
        "No generated output was changed."
    )
endif()
_protocyte_commit_generation_ownership(
    generation_owner_transaction_id
    generation_published_owner_markers
)
list(LENGTH generation_outputs generation_output_count)
math(EXPR last_generation_output_index "${generation_output_count} - 1")
foreach(generation_output_index RANGE 0 ${last_generation_output_index})
    list(GET generation_outputs ${generation_output_index} generation_output)
    list(GET generation_initial_states ${generation_output_index} generation_initial_state)
    if(generation_initial_state STREQUAL "prior")
        _protocyte_staged_output_path(
            backup_generation_output
            "backups"
            "${generation_output}"
        )
        _protocyte_generated_output_path_is_safe(
            backup_output_is_safe
            "${backup_generation_output}"
            "${STAGING_OUTPUT_DIRECTORY}/backups"
        )
        if(NOT backup_output_is_safe)
            _protocyte_recover_generation_transaction(recovered_generation_transaction)
            if(recovered_generation_transaction)
                _protocyte_discard_generation_staging()
            endif()
            message(
                FATAL_ERROR
                "Protocyte backup path changed before publication for target '${GENERATION_TARGET}'. "
                "Existing output was restored."
            )
        endif()
        list(REMOVE_AT generation_operation_states ${generation_output_index})
        list(
            INSERT
            generation_operation_states
            ${generation_output_index}
            "backup-pending"
        )
        _protocyte_write_generation_transaction(
            generation_transaction_written
            generation_transaction_owner_markers
            generation_initial_states
            generation_operation_states
        )
        if(NOT generation_transaction_written)
            _protocyte_recover_generation_transaction(recovered_generation_transaction)
            if(recovered_generation_transaction)
                _protocyte_discard_generation_staging()
            endif()
            message(
                FATAL_ERROR
                "Protocyte could not persist backup intent for '${generation_output}' in target "
                "'${GENERATION_TARGET}'."
            )
        endif()
        cmake_path(GET backup_generation_output PARENT_PATH backup_output_parent)
        file(MAKE_DIRECTORY "${backup_output_parent}")
        file(
            RENAME "${generation_output}" "${backup_generation_output}"
            NO_REPLACE
            RESULT backup_output_result
        )
        if(NOT "${backup_output_result}" STREQUAL "0")
            _protocyte_recover_generation_transaction(recovered_generation_transaction)
            if(recovered_generation_transaction)
                _protocyte_discard_generation_staging()
            endif()
            message(
                FATAL_ERROR
                "Protocyte could not prepare existing output '${generation_output}' for atomic publication "
                "for target '${GENERATION_TARGET}': ${backup_output_result}."
            )
        endif()
        list(REMOVE_AT generation_operation_states ${generation_output_index})
        list(
            INSERT
            generation_operation_states
            ${generation_output_index}
            "backed-up"
        )
        _protocyte_write_generation_transaction(
            generation_transaction_written
            generation_transaction_owner_markers
            generation_initial_states
            generation_operation_states
        )
        if(NOT generation_transaction_written)
            _protocyte_recover_generation_transaction(recovered_generation_transaction)
            if(recovered_generation_transaction)
                _protocyte_discard_generation_staging()
            endif()
            message(
                FATAL_ERROR
                "Protocyte could not persist completed backup state for '${generation_output}' in target "
                "'${GENERATION_TARGET}'."
            )
        endif()
    endif()
endforeach()

foreach(generation_output_index RANGE 0 ${last_generation_output_index})
    list(GET generation_outputs ${generation_output_index} generation_output)
    list(GET staged_generation_outputs ${generation_output_index} staged_generation_output)
    _protocyte_validate_generation_paths()
    _protocyte_validate_generation_staging_directory()
    _protocyte_generated_output_path_is_safe(
        staged_output_is_safe
        "${staged_generation_output}"
        "${STAGING_OUTPUT_DIRECTORY}/generated"
    )
    if(NOT staged_output_is_safe)
        _protocyte_recover_generation_transaction(recovered_generation_transaction)
        if(recovered_generation_transaction)
            _protocyte_discard_generation_staging()
        endif()
        message(
            FATAL_ERROR
            "Protocyte staging changed before output publication for target '${GENERATION_TARGET}'. "
            "Existing output was restored."
        )
    endif()
    list(REMOVE_AT generation_operation_states ${generation_output_index})
    list(
        INSERT
        generation_operation_states
        ${generation_output_index}
        "publish-pending"
    )
    _protocyte_write_generation_transaction(
        generation_transaction_written
        generation_transaction_owner_markers
        generation_initial_states
        generation_operation_states
    )
    if(NOT generation_transaction_written)
        _protocyte_recover_generation_transaction(recovered_generation_transaction)
        if(recovered_generation_transaction)
            _protocyte_discard_generation_staging()
        endif()
        message(
            FATAL_ERROR
            "Protocyte could not persist publication intent for '${generation_output}' in target "
            "'${GENERATION_TARGET}'."
        )
    endif()
    file(
        RENAME "${staged_generation_output}" "${generation_output}"
        NO_REPLACE
        RESULT output_publish_result
    )
    if(NOT "${output_publish_result}" STREQUAL "0")
        _protocyte_recover_generation_transaction(recovered_generation_transaction)
        if(recovered_generation_transaction)
            _protocyte_discard_generation_staging()
        endif()
        message(
            FATAL_ERROR
            "Protocyte could not publish staged output '${generation_output}' for target "
            "'${GENERATION_TARGET}': ${output_publish_result}. Existing output was restored."
        )
    endif()
    list(REMOVE_AT generation_operation_states ${generation_output_index})
    list(
        INSERT
        generation_operation_states
        ${generation_output_index}
        "published"
    )
    _protocyte_write_generation_transaction(
        generation_transaction_written
        generation_transaction_owner_markers
        generation_initial_states
        generation_operation_states
    )
    if(NOT generation_transaction_written)
        _protocyte_recover_generation_transaction(recovered_generation_transaction)
        if(recovered_generation_transaction)
            _protocyte_discard_generation_staging()
        endif()
        message(
            FATAL_ERROR
            "Protocyte could not persist completed publication state for '${generation_output}' in target "
            "'${GENERATION_TARGET}'."
        )
    endif()
endforeach()
_protocyte_generation_transaction_paths(transaction_active transaction_committed)
file(
    RENAME "${transaction_active}" "${transaction_committed}"
    NO_REPLACE
    RESULT transaction_complete_result
)
if(NOT "${transaction_complete_result}" STREQUAL "0")
    _protocyte_recover_generation_transaction(recovered_generation_transaction)
    if(recovered_generation_transaction)
        _protocyte_discard_generation_staging()
    endif()
    message(
        FATAL_ERROR
        "Protocyte could not commit completed generation publication for target "
        "'${GENERATION_TARGET}': ${transaction_complete_result}."
    )
endif()
_protocyte_discard_generation_staging()

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
            _protocyte_generated_output_path_is_safe(
                output_is_safe
                "${normalized_owned_output}"
                "${output_root}"
            )
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
