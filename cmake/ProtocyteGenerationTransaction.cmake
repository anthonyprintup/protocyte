include_guard(GLOBAL)

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
    # The lock namespace is the transaction's trust anchor.  It protects the
    # journal and backups from an untrusted or corrupt staging directory; it
    # is not a defence against an actor that can modify this lock namespace.
    _protocyte_normalized_path_identity(
        generation_transaction_staging_identity
        "${STAGING_OUTPUT_DIRECTORY}"
    )
    string(SHA256 generation_transaction_staging_key "${generation_transaction_staging_identity}")
    set(
        transaction_prefix
        "${LOCK_DIRECTORY}/.protocyte-generation-${generation_transaction_staging_key}"
    )
    set(${out_active} "${transaction_prefix}.active" PARENT_SCOPE)
    set(${out_committed} "${transaction_prefix}.committed" PARENT_SCOPE)
endfunction()

function(
    _protocyte_write_generation_transaction
    out_written
    owner_markers_var
    ownership_state
    owner_transaction_id
    owner_witness_state
    owner_release_states_var
    initial_states_var
    operation_states_var
    recovery_states_var
    initial_hashes_var
    staged_hashes_var
)
    set(${out_written} FALSE PARENT_SCOPE)
    list(LENGTH generation_outputs generation_output_count)
    list(LENGTH ${initial_states_var} initial_state_count)
    list(LENGTH ${operation_states_var} operation_state_count)
    list(LENGTH ${recovery_states_var} recovery_state_count)
    list(LENGTH ${initial_hashes_var} initial_hash_count)
    list(LENGTH ${staged_hashes_var} staged_hash_count)
    list(LENGTH ${owner_markers_var} owner_marker_count)
    list(LENGTH ${owner_release_states_var} owner_release_state_count)
    if(
        NOT initial_state_count EQUAL generation_output_count
        OR NOT operation_state_count EQUAL generation_output_count
        OR NOT recovery_state_count EQUAL generation_output_count
        OR NOT initial_hash_count EQUAL generation_output_count
        OR NOT staged_hash_count EQUAL generation_output_count
        OR NOT owner_release_state_count EQUAL owner_marker_count
    )
        return()
    endif()
    if(NOT (ownership_state STREQUAL "commit-pending" OR ownership_state STREQUAL "committed"))
        return()
    endif()
    string(LENGTH "${owner_transaction_id}" owner_transaction_id_length)
    if(
        NOT "${owner_transaction_id}" STREQUAL ""
        AND (
            NOT owner_transaction_id_length EQUAL 64
            OR NOT owner_transaction_id MATCHES "^[0-9a-f]+$"
        )
    )
        return()
    endif()
    if(
        NOT (
            owner_witness_state STREQUAL "retained"
            OR owner_witness_state STREQUAL "planned"
            OR owner_witness_state STREQUAL "remove-pending"
            OR owner_witness_state STREQUAL "removed"
        )
    )
        return()
    endif()
    _protocyte_generation_transaction_paths(transaction_active transaction_committed)
    _protocyte_normalized_path_identity(transaction_output_directory_identity "${OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_staging_directory_identity "${STAGING_OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_lock_directory_identity "${LOCK_DIRECTORY}")
    string(SHA256 transaction_target_hash "${GENERATION_TARGET}")
    string(SHA256 transaction_output_directory_hash "${transaction_output_directory_identity}")
    string(SHA256 transaction_staging_directory_hash "${transaction_staging_directory_identity}")
    string(SHA256 transaction_lock_directory_hash "${transaction_lock_directory_identity}")
    set(
        transaction_content
        "version=5\nbuild-tree-sha256=${BUILD_OWNER_HASH}\ntarget-sha256=${transaction_target_hash}\noutput-directory-sha256=${transaction_output_directory_hash}\nstaging-directory-sha256=${transaction_staging_directory_hash}\nlock-directory-sha256=${transaction_lock_directory_hash}\nownership-state=${ownership_state}\nowner-transaction-sha256=${owner_transaction_id}\nowner-witness-state=${owner_witness_state}\n"
    )
    string(APPEND transaction_content "owner-count=${owner_marker_count}\n")
    if(owner_marker_count GREATER 0)
        math(EXPR last_owner_index "${owner_marker_count} - 1")
        foreach(owner_index RANGE 0 ${last_owner_index})
            list(GET ${owner_markers_var} ${owner_index} owner_marker)
            list(GET ${owner_release_states_var} ${owner_index} owner_release_state)
            if(
                NOT (
                    owner_release_state STREQUAL "unreleased"
                    OR owner_release_state STREQUAL "release-pending"
                    OR owner_release_state STREQUAL "released"
                )
            )
                return()
            endif()
            _protocyte_normalized_path_identity(owner_marker_identity "${owner_marker}")
            _protocyte_normalized_path_identity(root_owner_marker_identity "${OUT_DIR_OWNER_MARKER}")
            if(owner_marker_identity STREQUAL root_owner_marker_identity)
                set(owner_role "root")
            else()
                set(owner_role "")
                foreach(output_lock_key IN LISTS output_lock_keys)
                    _protocyte_normalized_path_identity(
                        output_owner_marker_identity
                        "${LOCK_DIRECTORY}/${output_lock_key}.owner"
                    )
                    if(owner_marker_identity STREQUAL output_owner_marker_identity)
                        set(owner_role "${output_lock_key}")
                        break()
                    endif()
                endforeach()
                if(owner_role STREQUAL "")
                    return()
                endif()
            endif()
            string(APPEND transaction_content "owner-key=${owner_role}\n")
            string(APPEND transaction_content "owner-recovery=${owner_release_state}\n")
        endforeach()
    endif()
    string(APPEND transaction_content "output-count=${generation_output_count}\n")
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            list(GET generation_outputs ${generation_output_index} generation_output)
            list(GET ${initial_states_var} ${generation_output_index} initial_state)
            list(GET ${operation_states_var} ${generation_output_index} operation_state)
            list(GET ${recovery_states_var} ${generation_output_index} recovery_state)
            list(GET ${initial_hashes_var} ${generation_output_index} initial_hash)
            list(GET ${staged_hashes_var} ${generation_output_index} staged_hash)
            if(
                NOT (initial_state STREQUAL "prior" OR initial_state STREQUAL "absent")
                OR NOT (
                    operation_state STREQUAL "untouched"
                    OR operation_state STREQUAL "backup-pending"
                    OR operation_state STREQUAL "backed-up"
                    OR operation_state STREQUAL "publish-pending"
                    OR operation_state STREQUAL "published"
                )
                OR NOT (
                    recovery_state STREQUAL "none"
                    OR recovery_state STREQUAL "remove-pending"
                    OR recovery_state STREQUAL "removed"
                    OR recovery_state STREQUAL "restore-pending"
                    OR recovery_state STREQUAL "restored"
                )
            )
                return()
            endif()
            string(LENGTH "${initial_hash}" initial_hash_length)
            string(LENGTH "${staged_hash}" staged_hash_length)
            if(
                (initial_state STREQUAL "prior" AND (NOT initial_hash_length EQUAL 64 OR NOT initial_hash MATCHES "^[0-9a-f]+$"))
                OR (initial_state STREQUAL "absent" AND NOT initial_hash STREQUAL "absent")
                OR (NOT staged_hash_length EQUAL 64 OR NOT staged_hash MATCHES "^[0-9a-f]+$")
            )
                return()
            endif()
            if(initial_state STREQUAL "absent")
                set(serialized_initial_hash "")
            else()
                set(serialized_initial_hash "${initial_hash}")
            endif()
            file(
                RELATIVE_PATH generation_output_relative_path
                "${OUTPUT_DIRECTORY}" "${generation_output}"
            )
            if(
                generation_output_relative_path STREQUAL ""
                OR generation_output_relative_path MATCHES "^\\.\\.(\\\\|/|$)"
                OR IS_ABSOLUTE "${generation_output_relative_path}"
            )
                return()
            endif()
            string(HEX "${generation_output_relative_path}" encoded_generation_output)
            string(APPEND transaction_content "output-relative-hex=${encoded_generation_output}\n")
            string(APPEND transaction_content "initial=${initial_state}\n")
            string(APPEND transaction_content "initial-sha256=${serialized_initial_hash}\n")
            string(APPEND transaction_content "staged-sha256=${staged_hash}\n")
            string(APPEND transaction_content "state=${operation_state}\n")
            string(APPEND transaction_content "recovery=${recovery_state}\n")
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
    out_ownership_state
    out_owner_transaction_id
    out_owner_witness_state
    out_owner_release_states
    out_initial_states
    out_operation_states
    out_recovery_states
    out_initial_hashes
    out_staged_hashes
)
    set(${out_is_present} FALSE PARENT_SCOPE)
    set(${out_is_committed} FALSE PARENT_SCOPE)
    set(${out_owner_markers} "" PARENT_SCOPE)
    set(${out_ownership_state} "" PARENT_SCOPE)
    set(${out_owner_transaction_id} "" PARENT_SCOPE)
    set(${out_owner_witness_state} "" PARENT_SCOPE)
    set(${out_owner_release_states} "" PARENT_SCOPE)
    set(${out_initial_states} "" PARENT_SCOPE)
    set(${out_operation_states} "" PARENT_SCOPE)
    set(${out_recovery_states} "" PARENT_SCOPE)
    set(${out_initial_hashes} "" PARENT_SCOPE)
    set(${out_staged_hashes} "" PARENT_SCOPE)
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
    if(transaction_line_count LESS 11)
        return()
    endif()
    list(GET transaction_lines 0 transaction_version)
    list(GET transaction_lines 1 transaction_build_hash_line)
    list(GET transaction_lines 2 transaction_target_hash_line)
    list(GET transaction_lines 3 transaction_output_directory_hash_line)
    list(GET transaction_lines 4 transaction_staging_directory_hash_line)
    list(GET transaction_lines 5 transaction_lock_directory_hash_line)
    list(GET transaction_lines 6 transaction_ownership_state_line)
    list(GET transaction_lines 7 transaction_owner_id_line)
    list(GET transaction_lines 8 transaction_owner_witness_line)
    list(GET transaction_lines 9 transaction_owner_count_line)
    _protocyte_normalized_path_identity(transaction_output_directory_identity "${OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_staging_directory_identity "${STAGING_OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_lock_directory_identity "${LOCK_DIRECTORY}")
    string(SHA256 transaction_target_hash "${GENERATION_TARGET}")
    string(SHA256 transaction_output_directory_hash "${transaction_output_directory_identity}")
    string(SHA256 transaction_staging_directory_hash "${transaction_staging_directory_identity}")
    string(SHA256 transaction_lock_directory_hash "${transaction_lock_directory_identity}")
    if(
        NOT transaction_version STREQUAL "version=5"
        OR NOT transaction_build_hash_line STREQUAL "build-tree-sha256=${BUILD_OWNER_HASH}"
        OR NOT transaction_target_hash_line STREQUAL "target-sha256=${transaction_target_hash}"
        OR NOT transaction_output_directory_hash_line STREQUAL "output-directory-sha256=${transaction_output_directory_hash}"
        OR NOT transaction_staging_directory_hash_line STREQUAL "staging-directory-sha256=${transaction_staging_directory_hash}"
        OR NOT transaction_lock_directory_hash_line STREQUAL "lock-directory-sha256=${transaction_lock_directory_hash}"
        OR NOT transaction_ownership_state_line MATCHES "^ownership-state=(commit-pending|committed)$"
        OR NOT transaction_owner_id_line MATCHES "^owner-transaction-sha256=([0-9a-f]*)$"
        OR NOT transaction_owner_witness_line MATCHES "^owner-witness-state=(planned|retained|remove-pending|removed)$"
        OR NOT transaction_owner_count_line MATCHES "^owner-count=([0-9]+)$"
    )
        return()
    endif()
    string(REGEX REPLACE "^ownership-state=" "" transaction_ownership_state "${transaction_ownership_state_line}")
    string(REGEX REPLACE "^owner-transaction-sha256=" "" transaction_owner_transaction_id "${transaction_owner_id_line}")
    string(REGEX REPLACE "^owner-witness-state=" "" transaction_owner_witness_state "${transaction_owner_witness_line}")
    string(REGEX REPLACE "^owner-count=" "" transaction_owner_count "${transaction_owner_count_line}")
    string(LENGTH "${transaction_owner_transaction_id}" transaction_owner_transaction_id_length)
    if(
        NOT "${transaction_owner_transaction_id}" STREQUAL ""
        AND (
            NOT transaction_owner_transaction_id_length EQUAL 64
            OR NOT transaction_owner_transaction_id MATCHES "^[0-9a-f]+$"
        )
    )
        return()
    endif()
    list(LENGTH generation_outputs generation_output_count)
    math(EXPR maximum_transaction_owner_count "${generation_output_count} + 1")
    if(transaction_owner_count GREATER maximum_transaction_owner_count)
        return()
    endif()
    set(transaction_line_index 10)
    set(transaction_owner_markers)
    set(transaction_owner_release_states)
    if(transaction_owner_count GREATER 0)
        math(EXPR last_owner_index "${transaction_owner_count} - 1")
        foreach(owner_index RANGE 0 ${last_owner_index})
            if(transaction_line_index GREATER_EQUAL transaction_line_count)
                return()
            endif()
            list(GET transaction_lines ${transaction_line_index} owner_line)
            if(NOT owner_line MATCHES "^owner-key=(root|[0-9a-f]+)$")
                return()
            endif()
            set(transaction_owner_role "${CMAKE_MATCH_1}")
            if(transaction_owner_role STREQUAL "root")
                set(owner_marker "${OUT_DIR_OWNER_MARKER}")
            else()
                if(NOT transaction_owner_role IN_LIST output_lock_keys)
                    return()
                endif()
                set(owner_marker "${LOCK_DIRECTORY}/${transaction_owner_role}.owner")
            endif()
            math(EXPR owner_recovery_line_index "${transaction_line_index} + 1")
            if(owner_recovery_line_index GREATER_EQUAL transaction_line_count)
                return()
            endif()
            list(GET transaction_lines ${owner_recovery_line_index} owner_recovery_line)
            if(
                NOT owner_recovery_line MATCHES
                "^owner-recovery=(unreleased|release-pending|released)$"
            )
                return()
            endif()
            string(REPLACE ";" "\\;" owner_marker_list_element "${owner_marker}")
            list(APPEND transaction_owner_markers "${owner_marker_list_element}")
            string(REGEX REPLACE "^owner-recovery=" "" owner_release_state "${owner_recovery_line}")
            list(APPEND transaction_owner_release_states "${owner_release_state}")
            math(EXPR transaction_line_index "${transaction_line_index} + 2")
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
    set(transaction_recovery_states)
    set(transaction_initial_hashes)
    set(transaction_staged_hashes)
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            math(EXPR transaction_last_output_line "${transaction_line_index} + 5")
            if(transaction_last_output_line GREATER_EQUAL transaction_line_count)
                return()
            endif()
            list(GET transaction_lines ${transaction_line_index} transaction_output_line)
            math(EXPR transaction_initial_line_index "${transaction_line_index} + 1")
            math(EXPR transaction_initial_hash_line_index "${transaction_line_index} + 2")
            math(EXPR transaction_staged_hash_line_index "${transaction_line_index} + 3")
            math(EXPR transaction_state_line_index "${transaction_line_index} + 4")
            math(EXPR transaction_recovery_line_index "${transaction_line_index} + 5")
            list(GET transaction_lines ${transaction_initial_line_index} transaction_initial_line)
            list(GET transaction_lines ${transaction_initial_hash_line_index} transaction_initial_hash_line)
            list(GET transaction_lines ${transaction_staged_hash_line_index} transaction_staged_hash_line)
            list(GET transaction_lines ${transaction_state_line_index} transaction_state_line)
            list(GET transaction_lines ${transaction_recovery_line_index} transaction_recovery_line)
            if(NOT transaction_output_line MATCHES "^output-relative-hex=([0-9a-f]+)$")
                return()
            endif()
            set(encoded_transaction_output "${CMAKE_MATCH_1}")
            if(NOT transaction_initial_line MATCHES "^initial=(prior|absent)$")
                return()
            endif()
            if(NOT transaction_initial_hash_line MATCHES "^initial-sha256=([0-9a-f]*)$")
                return()
            endif()
            set(transaction_initial_hash "${CMAKE_MATCH_1}")
            if(NOT transaction_staged_hash_line MATCHES "^staged-sha256=([0-9a-f]+)$")
                return()
            endif()
            set(transaction_staged_hash "${CMAKE_MATCH_1}")
            string(LENGTH "${transaction_staged_hash}" transaction_staged_hash_length)
            if(NOT transaction_staged_hash_length EQUAL 64)
                return()
            endif()
            if(
                NOT transaction_state_line MATCHES
                "^state=(untouched|backup-pending|backed-up|publish-pending|published)$"
            )
                return()
            endif()
            if(
                NOT transaction_recovery_line MATCHES
                "^recovery=(none|remove-pending|removed|restore-pending|restored)$"
            )
                return()
            endif()
            string(LENGTH "${transaction_initial_hash}" transaction_initial_hash_length)
            _protocyte_decode_generation_hex(
                transaction_output_relative_path
                "${encoded_transaction_output}"
            )
            if(
                transaction_output_relative_path STREQUAL ""
                OR transaction_output_relative_path MATCHES "^\\.\\.(\\\\|/|$)"
                OR IS_ABSOLUTE "${transaction_output_relative_path}"
            )
                return()
            endif()
            cmake_path(
                APPEND OUTPUT_DIRECTORY "${transaction_output_relative_path}"
                OUTPUT_VARIABLE transaction_output
            )
            cmake_path(NORMAL_PATH transaction_output)
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
            string(REGEX REPLACE "^recovery=" "" transaction_recovery_state "${transaction_recovery_line}")
            if(transaction_initial_state STREQUAL "prior")
                if(
                    NOT transaction_initial_hash_length EQUAL 64
                    OR NOT transaction_initial_hash MATCHES "^[0-9a-f]+$"
                )
                    return()
                endif()
            elseif(transaction_initial_state STREQUAL "absent")
                if(NOT "${transaction_initial_hash}" STREQUAL "")
                    return()
                endif()
                set(transaction_initial_hash "absent")
            else()
                return()
            endif()
            list(APPEND transaction_initial_states "${transaction_initial_state}")
            list(APPEND transaction_operation_states "${transaction_operation_state}")
            list(APPEND transaction_recovery_states "${transaction_recovery_state}")
            list(APPEND transaction_initial_hashes "${transaction_initial_hash}")
            list(APPEND transaction_staged_hashes "${transaction_staged_hash}")
            math(EXPR transaction_line_index "${transaction_line_index} + 6")
        endforeach()
    endif()
    if(NOT transaction_line_index EQUAL transaction_line_count)
        return()
    endif()
    set(${out_is_present} TRUE PARENT_SCOPE)
    set(${out_is_committed} "${transaction_is_committed}" PARENT_SCOPE)
    set(${out_owner_markers} "${transaction_owner_markers}" PARENT_SCOPE)
    set(${out_ownership_state} "${transaction_ownership_state}" PARENT_SCOPE)
    set(${out_owner_transaction_id} "${transaction_owner_transaction_id}" PARENT_SCOPE)
    set(${out_owner_witness_state} "${transaction_owner_witness_state}" PARENT_SCOPE)
    set(${out_owner_release_states} "${transaction_owner_release_states}" PARENT_SCOPE)
    set(${out_initial_states} "${transaction_initial_states}" PARENT_SCOPE)
    set(${out_operation_states} "${transaction_operation_states}" PARENT_SCOPE)
    set(${out_recovery_states} "${transaction_recovery_states}" PARENT_SCOPE)
    set(${out_initial_hashes} "${transaction_initial_hashes}" PARENT_SCOPE)
    set(${out_staged_hashes} "${transaction_staged_hashes}" PARENT_SCOPE)
endfunction()

function(_protocyte_set_generation_transaction_list_item list_var item_index item_value)
    set(updated_list "${${list_var}}")
    list(REMOVE_AT updated_list ${item_index})
    list(INSERT updated_list ${item_index} "${item_value}")
    set(${list_var} "${updated_list}" PARENT_SCOPE)
endfunction()

function(_protocyte_generation_transaction_file_hash_matches out_matches path expected_hash)
    set(${out_matches} FALSE PARENT_SCOPE)
    if(
        NOT EXISTS "${path}"
        OR IS_DIRECTORY "${path}"
        OR IS_SYMLINK "${path}"
        OR NOT expected_hash MATCHES "^[0-9a-f]+$"
    )
        return()
    endif()
    string(LENGTH "${expected_hash}" expected_hash_length)
    if(NOT expected_hash_length EQUAL 64)
        return()
    endif()
    file(SHA256 "${path}" observed_hash)
    if(observed_hash STREQUAL expected_hash)
        set(${out_matches} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(
    _protocyte_generation_transaction_owner_record_hash_matches
    out_matches
    path
    transaction_id
)
    set(${out_matches} FALSE PARENT_SCOPE)
    if(
        NOT EXISTS "${path}"
        OR IS_DIRECTORY "${path}"
        OR IS_SYMLINK "${path}"
        OR NOT transaction_id MATCHES "^[0-9a-f]+$"
    )
        return()
    endif()
    string(LENGTH "${transaction_id}" transaction_id_length)
    if(NOT transaction_id_length EQUAL 64)
        return()
    endif()
    set(
        expected_owner_record
        "version=2\nbuild-tree-sha256=${BUILD_OWNER_HASH}\ntransaction-sha256=${transaction_id}\n"
    )
    if(CMAKE_HOST_WIN32)
        string(REPLACE "\n" "\r\n" expected_owner_record_bytes "${expected_owner_record}")
    else()
        set(expected_owner_record_bytes "${expected_owner_record}")
    endif()
    string(SHA256 expected_owner_record_hash "${expected_owner_record_bytes}")
    _protocyte_generation_transaction_file_hash_matches(
        owner_record_hash_matches
        "${path}"
        "${expected_owner_record_hash}"
    )
    if(owner_record_hash_matches)
        set(${out_matches} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(
    _protocyte_generation_transaction_claims_match
    out_matches
    owner_markers_var
    transaction_id
)
    set(${out_matches} FALSE PARENT_SCOPE)
    string(LENGTH "${transaction_id}" transaction_id_length)
    if(NOT transaction_id_length EQUAL 64 OR NOT transaction_id MATCHES "^[0-9a-f]+$")
        return()
    endif()
    set(transaction_witness_state "committed")
    if(ARGC EQUAL 4)
        set(transaction_witness_state "${ARGV3}")
    endif()
    _protocyte_owner_transaction_paths(
        transaction_prepared
        transaction_committed
        "${OUT_DIR_OWNER_MARKER}"
        "${transaction_id}"
    )
    if(transaction_witness_state STREQUAL "prepared")
        set(transaction_witness "${transaction_prepared}")
    elseif(transaction_witness_state STREQUAL "committed")
        set(transaction_witness "${transaction_committed}")
    else()
        return()
    endif()
    if(
        NOT EXISTS "${transaction_witness}"
        OR IS_DIRECTORY "${transaction_witness}"
        OR IS_SYMLINK "${transaction_witness}"
    )
        return()
    endif()
    file(SHA256 "${transaction_witness}" observed_transaction_id)
    if(NOT observed_transaction_id STREQUAL transaction_id)
        return()
    endif()
    file(STRINGS "${transaction_witness}" transaction_manifest_lines)
    list(LENGTH transaction_manifest_lines transaction_manifest_line_count)
    if(transaction_manifest_line_count LESS 5)
        return()
    endif()
    list(GET transaction_manifest_lines 0 transaction_manifest_version)
    list(GET transaction_manifest_lines 2 transaction_manifest_build_hash)
    if(
        NOT transaction_manifest_version STREQUAL "version=1"
        OR NOT transaction_manifest_build_hash STREQUAL "build-tree-sha256=${BUILD_OWNER_HASH}"
    )
        return()
    endif()
    list(SUBLIST transaction_manifest_lines 4 -1 transaction_manifest_claim_lines)
    set(observed_claim_ids)
    foreach(transaction_manifest_claim_line IN LISTS transaction_manifest_claim_lines)
        if(NOT transaction_manifest_claim_line MATCHES "^claim-sha256=([0-9a-f]+)$")
            return()
        endif()
        set(transaction_manifest_claim_id "${CMAKE_MATCH_1}")
        string(LENGTH "${transaction_manifest_claim_id}" transaction_manifest_claim_id_length)
        if(NOT transaction_manifest_claim_id_length EQUAL 64)
            return()
        endif()
        list(APPEND observed_claim_ids "${transaction_manifest_claim_id}")
    endforeach()
    set(expected_claim_ids)
    foreach(transaction_owner_marker IN LISTS ${owner_markers_var})
        _protocyte_normalized_path_identity(
            transaction_owner_identity
            "${transaction_owner_marker}"
        )
        string(SHA256 transaction_owner_claim_id "${transaction_owner_identity}")
        list(APPEND expected_claim_ids "${transaction_owner_claim_id}")
    endforeach()
    set(sorted_observed_claim_ids "${observed_claim_ids}")
    set(sorted_expected_claim_ids "${expected_claim_ids}")
    list(REMOVE_DUPLICATES sorted_observed_claim_ids)
    list(REMOVE_DUPLICATES sorted_expected_claim_ids)
    list(SORT sorted_observed_claim_ids)
    list(SORT sorted_expected_claim_ids)
    list(LENGTH observed_claim_ids observed_claim_count)
    list(LENGTH sorted_observed_claim_ids unique_observed_claim_count)
    if(
        NOT observed_claim_count EQUAL unique_observed_claim_count
        OR NOT sorted_observed_claim_ids STREQUAL sorted_expected_claim_ids
    )
        return()
    endif()
    set(${out_matches} TRUE PARENT_SCOPE)
endfunction()

# The recovery journal is deliberately advanced before and after every recovery
# mutation.  A process death therefore leaves either the pre-action or
# post-action state, both of which the next invocation can converge safely.
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
        transaction_ownership_state
        transaction_owner_transaction_id
        transaction_owner_witness_state
        transaction_owner_release_states
        transaction_initial_states
        transaction_operation_states
        transaction_recovery_states
        transaction_initial_hashes
        transaction_staged_hashes
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
        list(LENGTH generation_outputs generation_output_count)
        math(EXPR last_committed_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_committed_output_index})
            list(GET generation_outputs ${generation_output_index} generation_output)
            list(GET transaction_staged_hashes ${generation_output_index} transaction_staged_hash)
            if(
                NOT EXISTS "${generation_output}"
                OR IS_DIRECTORY "${generation_output}"
                OR IS_SYMLINK "${generation_output}"
            )
                return()
            endif()
            _protocyte_generation_transaction_file_hash_matches(
                transaction_output_hash_matches "${generation_output}" "${transaction_staged_hash}"
            )
            if(NOT transaction_output_hash_matches)
                return()
            endif()
        endforeach()
        file(REMOVE "${transaction_committed}")
        if(EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
            return()
        endif()
        set(${out_recovered} TRUE PARENT_SCOPE)
        return()
    endif()

    list(LENGTH generation_outputs generation_output_count)
    list(LENGTH transaction_owner_markers transaction_owner_count)
    list(LENGTH transaction_owner_release_states transaction_owner_release_state_count)
    if(NOT transaction_owner_release_state_count EQUAL transaction_owner_count)
        return()
    endif()
    math(EXPR maximum_transaction_owner_count "${generation_output_count} + 1")
    if(transaction_owner_count GREATER maximum_transaction_owner_count)
        return()
    endif()
    set(allowed_transaction_owner_markers)
    string(REPLACE ";" "\\;" allowed_transaction_owner_marker "${OUT_DIR_OWNER_MARKER}")
    list(APPEND allowed_transaction_owner_markers "${allowed_transaction_owner_marker}")
    foreach(output_lock_key IN LISTS output_lock_keys)
        set(allowed_transaction_owner_marker "${LOCK_DIRECTORY}/${output_lock_key}.owner")
        string(REPLACE ";" "\\;" allowed_transaction_owner_marker "${allowed_transaction_owner_marker}")
        list(APPEND allowed_transaction_owner_markers "${allowed_transaction_owner_marker}")
    endforeach()
    set(allowed_transaction_owner_identity_keys)
    foreach(allowed_transaction_owner_marker IN LISTS allowed_transaction_owner_markers)
        _protocyte_normalized_path_identity(
            allowed_transaction_owner_identity
            "${allowed_transaction_owner_marker}"
        )
        string(SHA256 allowed_transaction_owner_identity_key "${allowed_transaction_owner_identity}")
        list(APPEND
            allowed_transaction_owner_identity_keys
            "${allowed_transaction_owner_identity_key}"
        )
    endforeach()
    list(LENGTH allowed_transaction_owner_identity_keys allowed_transaction_owner_count)
    list(SORT allowed_transaction_owner_identity_keys)
    list(REMOVE_DUPLICATES allowed_transaction_owner_identity_keys)
    list(LENGTH allowed_transaction_owner_identity_keys unique_allowed_transaction_owner_count)
    if(NOT allowed_transaction_owner_count EQUAL unique_allowed_transaction_owner_count)
        return()
    endif()
    set(transaction_owner_identity_keys)
    foreach(transaction_owner_marker IN LISTS transaction_owner_markers)
        _protocyte_normalized_path_identity(
            transaction_owner_identity
            "${transaction_owner_marker}"
        )
        string(SHA256 transaction_owner_identity_key "${transaction_owner_identity}")
        list(APPEND transaction_owner_identity_keys "${transaction_owner_identity_key}")
    endforeach()
    list(LENGTH transaction_owner_identity_keys transaction_owner_identity_count)
    list(SORT transaction_owner_identity_keys)
    list(REMOVE_DUPLICATES transaction_owner_identity_keys)
    list(LENGTH transaction_owner_identity_keys unique_transaction_owner_identity_count)
    if(NOT transaction_owner_identity_count EQUAL unique_transaction_owner_identity_count)
        return()
    endif()
    foreach(transaction_owner_identity_key IN LISTS transaction_owner_identity_keys)
        if(NOT transaction_owner_identity_key IN_LIST allowed_transaction_owner_identity_keys)
            return()
        endif()
        set("transaction_journal_owner_${transaction_owner_identity_key}" TRUE)
    endforeach()

    # The journal's owner list is the exact subset of claims newly created by
    # this invocation.  Every other configured owner is retained authority and
    # may legitimately be legacy v1 or a v2 record from another epoch.
    set(transaction_created_owner_markers "${transaction_owner_markers}")
    set(transaction_pending_incomplete_owner_markers)
    set(transaction_commit_pending_ownership FALSE)
    set(transaction_discard_pending_ownership FALSE)
    list(LENGTH transaction_created_owner_markers transaction_created_owner_count)

    # This global, read-only pass is intentionally performed before output
    # planning or ownership cleanup.  It rejects a late unsafe owner record
    # without rolling back an earlier output.
    set(transaction_current_created_owner_markers)
    set(transaction_current_created_owner_ids)
    set(transaction_missing_or_incomplete_created_owner_markers)
    foreach(allowed_transaction_owner_marker IN LISTS allowed_transaction_owner_markers)
        _protocyte_normalized_path_identity(
            allowed_transaction_owner_identity "${allowed_transaction_owner_marker}"
        )
        string(SHA256 allowed_transaction_owner_identity_key "${allowed_transaction_owner_identity}")
        _protocyte_owner_record_status(
            allowed_transaction_owner_status
            allowed_transaction_owner_id
            "${allowed_transaction_owner_marker}"
            "${BUILD_OWNER_HASH}"
            "${OUT_DIR_OWNER_MARKER}"
        )
        if(DEFINED transaction_journal_owner_${allowed_transaction_owner_identity_key})
            if(transaction_ownership_state STREQUAL "commit-pending")
                if(allowed_transaction_owner_status STREQUAL "current")
                    list(APPEND transaction_current_created_owner_markers "${allowed_transaction_owner_marker}")
                    list(APPEND transaction_current_created_owner_ids "${allowed_transaction_owner_id}")
                elseif(
                    allowed_transaction_owner_status STREQUAL "missing"
                    OR allowed_transaction_owner_status STREQUAL "incomplete"
                )
                    list(APPEND transaction_missing_or_incomplete_created_owner_markers "${allowed_transaction_owner_marker}")
                    if(allowed_transaction_owner_status STREQUAL "incomplete")
                        list(APPEND transaction_pending_incomplete_owner_markers "${allowed_transaction_owner_marker}")
                    endif()
                else()
                    return()
                endif()
            else()
                # Committed new claims are checked against their persisted
                # per-claim release state below.
            endif()
        elseif(NOT allowed_transaction_owner_status STREQUAL "current")
            # v1 owners intentionally return current with no transaction id;
            # v2 retained owners can each have a distinct valid witness id.
            return()
        endif()
    endforeach()

    if(transaction_ownership_state STREQUAL "commit-pending")
        if(transaction_created_owner_count GREATER 0)
            string(LENGTH "${transaction_owner_transaction_id}" pending_transaction_id_length)
            if(
                NOT pending_transaction_id_length EQUAL 64
                OR NOT transaction_owner_transaction_id MATCHES "^[0-9a-f]+$"
                OR NOT transaction_owner_witness_state STREQUAL "planned"
            )
                return()
            endif()
        elseif(
            NOT transaction_owner_transaction_id STREQUAL ""
            OR NOT transaction_owner_witness_state STREQUAL "removed"
        )
            return()
        endif()
        foreach(transaction_owner_release_state IN LISTS transaction_owner_release_states)
            if(NOT transaction_owner_release_state STREQUAL "unreleased")
                return()
            endif()
        endforeach()
        if(transaction_created_owner_count EQUAL 0)
            set(transaction_commit_pending_ownership TRUE)
        else()
            list(LENGTH transaction_current_created_owner_markers current_pending_created_owner_count)
            list(LENGTH transaction_missing_or_incomplete_created_owner_markers missing_pending_created_owner_count)
            if(current_pending_created_owner_count EQUAL transaction_created_owner_count)
                set(pending_created_owner_transaction_ids "${transaction_current_created_owner_ids}")
                list(REMOVE_DUPLICATES pending_created_owner_transaction_ids)
                list(LENGTH pending_created_owner_transaction_ids pending_owner_transaction_id_count)
                if(NOT pending_owner_transaction_id_count EQUAL 1)
                    return()
                endif()
                list(GET pending_created_owner_transaction_ids 0 pending_owner_transaction_id)
                if(NOT pending_owner_transaction_id STREQUAL transaction_owner_transaction_id)
                    return()
                endif()
                _protocyte_generation_transaction_claims_match(
                    transaction_claims_match transaction_created_owner_markers
                    "${transaction_owner_transaction_id}"
                )
                if(NOT transaction_claims_match)
                    return()
                endif()
                set(transaction_commit_pending_ownership TRUE)
            elseif(missing_pending_created_owner_count EQUAL transaction_created_owner_count)
                set(transaction_discard_pending_ownership TRUE)
            else()
                return()
            endif()
        endif()
    elseif(NOT transaction_ownership_state STREQUAL "committed")
        return()
    elseif(transaction_created_owner_count EQUAL 0)
        if(
            NOT transaction_owner_transaction_id STREQUAL ""
            OR NOT transaction_owner_witness_state STREQUAL "removed"
        )
            return()
        endif()
    else()
        string(LENGTH "${transaction_owner_transaction_id}" transaction_owner_id_length)
        if(
            NOT transaction_owner_id_length EQUAL 64
            OR NOT transaction_owner_transaction_id MATCHES "^[0-9a-f]+$"
        )
            return()
        endif()
        set(all_transaction_created_owners_released TRUE)
        math(EXPR last_transaction_owner_index "${transaction_owner_count} - 1")
        foreach(transaction_owner_index RANGE 0 ${last_transaction_owner_index})
            list(GET transaction_owner_markers ${transaction_owner_index} transaction_owner_marker)
            list(GET transaction_owner_release_states ${transaction_owner_index} transaction_owner_release_state)
            _protocyte_owner_record_status(
                transaction_owner_status transaction_owner_id "${transaction_owner_marker}"
                "${BUILD_OWNER_HASH}" "${OUT_DIR_OWNER_MARKER}"
            )
            if(transaction_owner_release_state STREQUAL "unreleased")
                if(
                    NOT transaction_owner_status STREQUAL "current"
                    OR NOT transaction_owner_id STREQUAL transaction_owner_transaction_id
                )
                    return()
                endif()
                set(all_transaction_created_owners_released FALSE)
            elseif(transaction_owner_release_state STREQUAL "release-pending")
                if(
                    NOT transaction_owner_status STREQUAL "missing"
                    AND (
                        NOT transaction_owner_status STREQUAL "current"
                        OR NOT transaction_owner_id STREQUAL transaction_owner_transaction_id
                    )
                )
                    return()
                endif()
                set(all_transaction_created_owners_released FALSE)
            elseif(transaction_owner_release_state STREQUAL "released")
                if(NOT transaction_owner_status STREQUAL "missing")
                    return()
                endif()
            else()
                return()
            endif()
        endforeach()
        if(transaction_owner_witness_state STREQUAL "retained")
            _protocyte_generation_transaction_claims_match(
                transaction_claims_match transaction_created_owner_markers
                "${transaction_owner_transaction_id}"
            )
            if(NOT transaction_claims_match)
                return()
            endif()
        elseif(
            transaction_owner_witness_state STREQUAL "remove-pending"
            OR transaction_owner_witness_state STREQUAL "removed"
        )
            if(NOT all_transaction_created_owners_released)
                return()
            endif()
            _protocyte_owner_transaction_paths(
                unused_transaction_prepared_witness
                transaction_committed_witness
                "${OUT_DIR_OWNER_MARKER}"
                "${transaction_owner_transaction_id}"
            )
            if(transaction_owner_witness_state STREQUAL "remove-pending")
                if(EXISTS "${transaction_committed_witness}" OR IS_SYMLINK "${transaction_committed_witness}")
                    _protocyte_generation_transaction_claims_match(
                        remove_pending_claims_match
                        transaction_created_owner_markers
                        "${transaction_owner_transaction_id}"
                    )
                    if(NOT remove_pending_claims_match)
                        return()
                    endif()
                endif()
            elseif(EXISTS "${transaction_committed_witness}" OR IS_SYMLINK "${transaction_committed_witness}")
                return()
            endif()
        else()
            return()
        endif()
    endif()
    if(transaction_discard_pending_ownership AND transaction_created_owner_count GREATER 0)
        _protocyte_owner_transaction_paths(
            transaction_prepared_witness
            transaction_committed_witness
            "${OUT_DIR_OWNER_MARKER}"
            "${transaction_owner_transaction_id}"
        )
        if(EXISTS "${transaction_committed_witness}" OR IS_SYMLINK "${transaction_committed_witness}")
            return()
        endif()
        if(EXISTS "${transaction_prepared_witness}" OR IS_SYMLINK "${transaction_prepared_witness}")
            _protocyte_generation_transaction_claims_match(
                prepared_claims_match
                transaction_created_owner_markers
                "${transaction_owner_transaction_id}"
                "prepared"
            )
            if(NOT prepared_claims_match)
                return()
            endif()
        endif()
        set(transaction_manifest_staging "${OUT_DIR_OWNER_MARKER}.${transaction_owner_transaction_id}.manifest.tmp")
        if(EXISTS "${transaction_manifest_staging}" OR IS_SYMLINK "${transaction_manifest_staging}")
            _protocyte_generation_transaction_file_hash_matches(
                manifest_staging_hash_matches
                "${transaction_manifest_staging}"
                "${transaction_owner_transaction_id}"
            )
            if(NOT manifest_staging_hash_matches)
                return()
            endif()
        endif()
        foreach(transaction_owner_marker IN LISTS transaction_created_owner_markers)
            set(transaction_owner_staging "${transaction_owner_marker}.${transaction_owner_transaction_id}.tmp")
            if(EXISTS "${transaction_owner_staging}" OR IS_SYMLINK "${transaction_owner_staging}")
                _protocyte_generation_transaction_owner_record_hash_matches(
                    owner_staging_hash_matches
                    "${transaction_owner_staging}"
                    "${transaction_owner_transaction_id}"
                )
                if(NOT owner_staging_hash_matches)
                    return()
                endif()
            endif()
        endforeach()
    endif()
    # Validate every output and derive the complete rollback plan before the
    # first output or owner record is changed.  A malformed late journal entry
    # must leave earlier outputs byte-for-byte untouched.
    set(recovery_remove_actions)
    set(recovery_restore_actions)
    set(recovery_mark_restored_actions)
    math(EXPR last_generation_output_index "${generation_output_count} - 1")
    foreach(generation_output_index RANGE 0 ${last_generation_output_index})
        list(GET generation_outputs ${generation_output_index} generation_output)
        list(GET transaction_initial_states ${generation_output_index} transaction_initial_state)
        list(GET transaction_operation_states ${generation_output_index} transaction_operation_state)
        list(GET transaction_recovery_states ${generation_output_index} transaction_recovery_state)
        list(GET transaction_initial_hashes ${generation_output_index} transaction_initial_hash)
        list(GET transaction_staged_hashes ${generation_output_index} transaction_staged_hash)
        _protocyte_generated_output_path_is_safe(
            recovery_output_is_safe "${generation_output}" "${OUTPUT_DIRECTORY}"
        )
        _protocyte_staged_output_path(backup_generation_output "backups" "${generation_output}")
        _protocyte_generated_output_path_is_safe(
            backup_output_is_safe
            "${backup_generation_output}"
            "${STAGING_OUTPUT_DIRECTORY}/backups"
        )
        if(NOT recovery_output_is_safe OR NOT backup_output_is_safe)
            return()
        endif()

        set(recovery_requires_remove FALSE)
        set(recovery_requires_restore FALSE)
        set(recovery_marks_restored FALSE)
        if(transaction_recovery_state STREQUAL "none")
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
                        set(recovery_requires_restore TRUE)
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
                        if(IS_DIRECTORY "${generation_output}" OR IS_SYMLINK "${generation_output}")
                            return()
                        endif()
                        set(recovery_requires_remove TRUE)
                    endif()
                    set(recovery_requires_restore TRUE)
                else()
                    return()
                endif()
            elseif(transaction_initial_state STREQUAL "absent")
                if(
                    (
                        NOT transaction_operation_state STREQUAL "untouched"
                        AND NOT transaction_operation_state STREQUAL "publish-pending"
                        AND NOT transaction_operation_state STREQUAL "published"
                    )
                    OR EXISTS "${backup_generation_output}"
                    OR IS_SYMLINK "${backup_generation_output}"
                )
                    return()
                endif()
                if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                    if(
                        IS_DIRECTORY "${generation_output}"
                        OR IS_SYMLINK "${generation_output}"
                        OR transaction_operation_state STREQUAL "untouched"
                    )
                        return()
                    endif()
                    set(recovery_requires_remove TRUE)
                endif()
            else()
                return()
            endif()
        elseif(transaction_recovery_state STREQUAL "remove-pending")
            if(transaction_initial_state STREQUAL "prior")
                if(
                    NOT EXISTS "${backup_generation_output}"
                    OR IS_DIRECTORY "${backup_generation_output}"
                    OR IS_SYMLINK "${backup_generation_output}"
                )
                    return()
                endif()
                set(recovery_requires_restore TRUE)
            elseif(NOT transaction_initial_state STREQUAL "absent")
                return()
            endif()
            if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                if(IS_DIRECTORY "${generation_output}" OR IS_SYMLINK "${generation_output}")
                    return()
                endif()
                set(recovery_requires_remove TRUE)
            endif()
        elseif(transaction_recovery_state STREQUAL "removed")
            if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                return()
            endif()
            if(transaction_initial_state STREQUAL "prior")
                if(
                    NOT EXISTS "${backup_generation_output}"
                    OR IS_DIRECTORY "${backup_generation_output}"
                    OR IS_SYMLINK "${backup_generation_output}"
                )
                    return()
                endif()
                set(recovery_requires_restore TRUE)
            elseif(NOT transaction_initial_state STREQUAL "absent")
                return()
            endif()
        elseif(transaction_recovery_state STREQUAL "restore-pending")
            if(NOT transaction_initial_state STREQUAL "prior")
                return()
            endif()
            if(EXISTS "${backup_generation_output}")
                if(
                    IS_DIRECTORY "${backup_generation_output}"
                    OR IS_SYMLINK "${backup_generation_output}"
                    OR EXISTS "${generation_output}"
                    OR IS_SYMLINK "${generation_output}"
                )
                    return()
                endif()
                set(recovery_requires_restore TRUE)
            elseif(
                NOT EXISTS "${generation_output}"
                OR IS_DIRECTORY "${generation_output}"
                OR IS_SYMLINK "${generation_output}"
            )
                return()
            else()
                set(recovery_marks_restored TRUE)
            endif()
        elseif(transaction_recovery_state STREQUAL "restored")
            if(
                NOT transaction_initial_state STREQUAL "prior"
                OR NOT EXISTS "${generation_output}"
                OR IS_DIRECTORY "${generation_output}"
                OR IS_SYMLINK "${generation_output}"
                OR EXISTS "${backup_generation_output}"
                OR IS_SYMLINK "${backup_generation_output}"
            )
                return()
            endif()
        else()
            return()
        endif()
        # The trusted journal binds both possible byte identities.  Backup
        # files remain in isolated staging for locality and privacy; this
        # catches static corruption before any rollback mutation (not a
        # hostile same-privilege process racing the executing generator).
        if(EXISTS "${backup_generation_output}")
            _protocyte_generation_transaction_file_hash_matches(
                backup_hash_matches "${backup_generation_output}" "${transaction_initial_hash}"
            )
            if(NOT backup_hash_matches)
                return()
            endif()
        endif()
        if(EXISTS "${generation_output}")
            set(expected_current_hash "${transaction_staged_hash}")
            if(
                transaction_initial_state STREQUAL "prior"
                AND (
                    transaction_recovery_state STREQUAL "restored"
                    OR (
                        transaction_recovery_state STREQUAL "restore-pending"
                        AND NOT EXISTS "${backup_generation_output}"
                    )
                    OR (
                        transaction_recovery_state STREQUAL "none"
                        AND (
                            transaction_operation_state STREQUAL "untouched"
                            OR (
                                transaction_operation_state STREQUAL "backup-pending"
                                AND NOT EXISTS "${backup_generation_output}"
                            )
                        )
                    )
                )
            )
                set(expected_current_hash "${transaction_initial_hash}")
            endif()
            _protocyte_generation_transaction_file_hash_matches(
                output_hash_matches "${generation_output}" "${expected_current_hash}"
            )
            if(NOT output_hash_matches)
                return()
            endif()
        endif()
        list(APPEND recovery_remove_actions "${recovery_requires_remove}")
        list(APPEND recovery_restore_actions "${recovery_requires_restore}")
        list(APPEND recovery_mark_restored_actions "${recovery_marks_restored}")
    endforeach()

    if(transaction_discard_pending_ownership)
        foreach(transaction_operation_state IN LISTS transaction_operation_states)
            if(NOT transaction_operation_state STREQUAL "untouched")
                return()
            endif()
        endforeach()
        foreach(recovery_action IN LISTS recovery_remove_actions recovery_restore_actions recovery_mark_restored_actions)
            if(recovery_action)
                return()
            endif()
        endforeach()
        foreach(transaction_owner_marker IN LISTS transaction_pending_incomplete_owner_markers)
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
            elseif(NOT transaction_owner_status STREQUAL "missing")
                return()
            endif()
        endforeach()
        if(transaction_created_owner_count GREATER 0)
            foreach(transaction_owner_marker IN LISTS transaction_created_owner_markers)
                set(transaction_owner_staging "${transaction_owner_marker}.${transaction_owner_transaction_id}.tmp")
                file(REMOVE "${transaction_owner_staging}")
                if(EXISTS "${transaction_owner_staging}" OR IS_SYMLINK "${transaction_owner_staging}")
                    return()
                endif()
            endforeach()
            set(transaction_manifest_staging "${OUT_DIR_OWNER_MARKER}.${transaction_owner_transaction_id}.manifest.tmp")
            file(REMOVE "${transaction_manifest_staging}")
            if(EXISTS "${transaction_manifest_staging}" OR IS_SYMLINK "${transaction_manifest_staging}")
                return()
            endif()
            _protocyte_owner_transaction_paths(
                transaction_prepared_witness
                unused_transaction_committed_witness
                "${OUT_DIR_OWNER_MARKER}"
                "${transaction_owner_transaction_id}"
            )
            file(REMOVE "${transaction_prepared_witness}")
            if(EXISTS "${transaction_prepared_witness}" OR IS_SYMLINK "${transaction_prepared_witness}")
                return()
            endif()
        endif()
        file(REMOVE "${transaction_active}")
        if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
            return()
        endif()
        set(${out_recovered} TRUE PARENT_SCOPE)
        return()
    endif()

    if(transaction_commit_pending_ownership)
        set(transaction_ownership_state "committed")
        if(transaction_created_owner_count GREATER 0)
            set(transaction_owner_witness_state "retained")
        else()
            set(transaction_owner_witness_state "removed")
        endif()
        _protocyte_write_generation_transaction(
            recovered_transaction_written transaction_owner_markers
            "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
            "${transaction_owner_witness_state}" transaction_owner_release_states
        transaction_initial_states transaction_operation_states transaction_recovery_states
        transaction_initial_hashes transaction_staged_hashes
        )
        if(NOT recovered_transaction_written)
            return()
        endif()
    endif()

    if(
        transaction_created_owner_count GREATER 0
        AND NOT transaction_owner_witness_state STREQUAL "retained"
    )
        foreach(recovery_action IN LISTS recovery_remove_actions recovery_restore_actions recovery_mark_restored_actions)
            if(recovery_action)
                return()
            endif()
        endforeach()
    endif()

    foreach(generation_output_index RANGE 0 ${last_generation_output_index})
        list(GET recovery_remove_actions ${generation_output_index} recovery_requires_remove)
        list(GET recovery_restore_actions ${generation_output_index} recovery_requires_restore)
        list(GET recovery_mark_restored_actions ${generation_output_index} recovery_marks_restored)
        list(GET generation_outputs ${generation_output_index} generation_output)
        list(GET transaction_initial_hashes ${generation_output_index} transaction_initial_hash)
        if(recovery_marks_restored)
            _protocyte_set_generation_transaction_list_item(
                transaction_recovery_states ${generation_output_index} "restored"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
            continue()
        endif()
        if(recovery_requires_remove)
            _protocyte_set_generation_transaction_list_item(
                transaction_recovery_states ${generation_output_index} "remove-pending"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
            file(REMOVE "${generation_output}")
            if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                return()
            endif()
            _protocyte_set_generation_transaction_list_item(
                transaction_recovery_states ${generation_output_index} "removed"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
        endif()
        if(recovery_requires_restore)
            _protocyte_staged_output_path(backup_generation_output "backups" "${generation_output}")
            _protocyte_set_generation_transaction_list_item(
                transaction_recovery_states ${generation_output_index} "restore-pending"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
            _protocyte_generation_transaction_file_hash_matches(
                backup_hash_matches "${backup_generation_output}" "${transaction_initial_hash}"
            )
            if(NOT backup_hash_matches)
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
            _protocyte_set_generation_transaction_list_item(
                transaction_recovery_states ${generation_output_index} "restored"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
        endif()
    endforeach()

    if(transaction_owner_count GREATER 0)
        math(EXPR last_transaction_owner_index "${transaction_owner_count} - 1")
        foreach(transaction_owner_index RANGE 0 ${last_transaction_owner_index})
            list(GET transaction_owner_markers ${transaction_owner_index} transaction_owner_marker)
            list(GET transaction_owner_release_states ${transaction_owner_index} transaction_owner_release_state)
            if(
                transaction_owner_release_state STREQUAL "retained"
                OR transaction_owner_release_state STREQUAL "released"
            )
                continue()
            endif()
            _protocyte_set_generation_transaction_list_item(
                transaction_owner_release_states ${transaction_owner_index} "release-pending"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
            file(REMOVE "${transaction_owner_marker}")
            if(EXISTS "${transaction_owner_marker}" OR IS_SYMLINK "${transaction_owner_marker}")
                return()
            endif()
            _protocyte_set_generation_transaction_list_item(
                transaction_owner_release_states ${transaction_owner_index} "released"
            )
            _protocyte_write_generation_transaction(
                recovered_transaction_written transaction_owner_markers
                "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
                "${transaction_owner_witness_state}" transaction_owner_release_states
                transaction_initial_states transaction_operation_states transaction_recovery_states
                transaction_initial_hashes transaction_staged_hashes
            )
            if(NOT recovered_transaction_written)
                return()
            endif()
        endforeach()
    endif()

    if(
        transaction_created_owner_count GREATER 0
        AND NOT transaction_owner_witness_state STREQUAL "removed"
    )
        set(transaction_owner_witness_state "remove-pending")
        _protocyte_write_generation_transaction(
            recovered_transaction_written transaction_owner_markers
            "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
            "${transaction_owner_witness_state}" transaction_owner_release_states
            transaction_initial_states transaction_operation_states transaction_recovery_states
            transaction_initial_hashes transaction_staged_hashes
        )
        if(NOT recovered_transaction_written)
            return()
        endif()
        if(NOT transaction_owner_transaction_id STREQUAL "")
            _protocyte_owner_transaction_paths(
                unused_transaction_prepared transaction_owner_witness
                "${OUT_DIR_OWNER_MARKER}" "${transaction_owner_transaction_id}"
            )
            if(EXISTS "${transaction_owner_witness}" OR IS_SYMLINK "${transaction_owner_witness}")
                _protocyte_generation_transaction_claims_match(
                    witness_hash_matches
                    transaction_created_owner_markers
                    "${transaction_owner_transaction_id}"
                )
                if(NOT witness_hash_matches)
                    return()
                endif()
                file(REMOVE "${transaction_owner_witness}")
            endif()
            if(EXISTS "${transaction_owner_witness}" OR IS_SYMLINK "${transaction_owner_witness}")
                return()
            endif()
        endif()
        set(transaction_owner_witness_state "removed")
        _protocyte_write_generation_transaction(
            recovered_transaction_written transaction_owner_markers
            "${transaction_ownership_state}" "${transaction_owner_transaction_id}"
            "${transaction_owner_witness_state}" transaction_owner_release_states
            transaction_initial_states transaction_operation_states transaction_recovery_states
            transaction_initial_hashes transaction_staged_hashes
        )
        if(NOT recovered_transaction_written)
            return()
        endif()
    endif()
    file(REMOVE "${transaction_active}")
    if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        return()
    endif()
    set(${out_recovered} TRUE PARENT_SCOPE)
endfunction()
