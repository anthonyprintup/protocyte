include_guard(GLOBAL)

# Transaction records are deliberately immutable.  Each forward mutation is an
# atomic rename, so the expected initial/staged hashes and the presence of the
# source/backup/output files describe progress without rewriting an O(N)
# journal for every output.

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

function(_protocyte_generation_transaction_paths out_active out_releasing out_committed)
    _protocyte_normalized_path_identity(
        generation_transaction_staging_identity
        "${STAGING_OUTPUT_DIRECTORY}"
    )
    string(SHA256 generation_transaction_staging_key "${generation_transaction_staging_identity}")
    set(transaction_prefix "${LOCK_DIRECTORY}/.protocyte-generation-${generation_transaction_staging_key}")
    set(${out_active} "${transaction_prefix}.active" PARENT_SCOPE)
    set(${out_releasing} "${transaction_prefix}.releasing" PARENT_SCOPE)
    set(${out_committed} "${transaction_prefix}.committed" PARENT_SCOPE)
endfunction()

function(_protocyte_generation_transaction_owner_marker_for_key out_marker out_known owner_key)
    set(${out_marker} "" PARENT_SCOPE)
    set(${out_known} FALSE PARENT_SCOPE)
    if(owner_key STREQUAL "root")
        set(${out_marker} "${OUT_DIR_OWNER_MARKER}" PARENT_SCOPE)
        set(${out_known} TRUE PARENT_SCOPE)
    elseif(
        owner_key MATCHES "^[0-9a-f]+$"
        AND DEFINED "protocyte_generation_known_owner_${owner_key}"
    )
        set(${out_marker} "${LOCK_DIRECTORY}/${owner_key}.owner" PARENT_SCOPE)
        set(${out_known} TRUE PARENT_SCOPE)
    endif()
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
        owner_record_hash_matches "${path}" "${expected_owner_record_hash}"
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
        transaction_prepared transaction_committed "${OUT_DIR_OWNER_MARKER}" "${transaction_id}"
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
        _protocyte_normalized_path_identity(transaction_owner_identity "${transaction_owner_marker}")
        string(SHA256 transaction_owner_claim_id "${transaction_owner_identity}")
        list(APPEND expected_claim_ids "${transaction_owner_claim_id}")
    endforeach()
    list(LENGTH observed_claim_ids observed_claim_count)
    list(LENGTH expected_claim_ids expected_claim_count)
    if(NOT observed_claim_count EQUAL expected_claim_count)
        return()
    endif()
    list(SORT observed_claim_ids)
    list(SORT expected_claim_ids)
    list(REMOVE_DUPLICATES observed_claim_ids)
    list(REMOVE_DUPLICATES expected_claim_ids)
    if(NOT observed_claim_ids STREQUAL expected_claim_ids)
        return()
    endif()
    set(${out_matches} TRUE PARENT_SCOPE)
endfunction()

function(
    _protocyte_write_generation_transaction
    out_written
    out_error
    owner_keys_var
    owner_transaction_id
    initial_states_var
    initial_hashes_var
    staged_hashes_var
)
    set(${out_written} FALSE PARENT_SCOPE)
    set(
        ${out_error}
        "transaction content or filesystem validation failed"
        PARENT_SCOPE
    )
    list(LENGTH generation_outputs generation_output_count)
    list(LENGTH ${owner_keys_var} owner_key_count)
    list(LENGTH ${initial_states_var} initial_state_count)
    list(LENGTH ${initial_hashes_var} initial_hash_count)
    list(LENGTH ${staged_hashes_var} staged_hash_count)
    math(EXPR maximum_owner_key_count "${generation_output_count} + 1")
    if(
        NOT initial_state_count EQUAL generation_output_count
        OR NOT initial_hash_count EQUAL generation_output_count
        OR NOT staged_hash_count EQUAL generation_output_count
        OR owner_key_count GREATER maximum_owner_key_count
    )
        set(${out_error} "transaction list cardinality validation failed" PARENT_SCOPE)
        return()
    endif()
    if(owner_key_count GREATER 0)
        string(LENGTH "${owner_transaction_id}" owner_transaction_id_length)
        if(
            NOT owner_transaction_id_length EQUAL 64
            OR NOT owner_transaction_id MATCHES "^[0-9a-f]+$"
        )
            set(${out_error} "ownership transaction identity validation failed" PARENT_SCOPE)
            return()
        endif()
    elseif(NOT "${owner_transaction_id}" STREQUAL "")
        set(${out_error} "unexpected ownership transaction identity" PARENT_SCOPE)
        return()
    endif()

    set(seen_owner_keys)
    foreach(owner_key IN LISTS ${owner_keys_var})
        _protocyte_generation_transaction_owner_marker_for_key(owner_marker owner_key_known "${owner_key}")
        if(NOT owner_key_known OR DEFINED "transaction_written_owner_${owner_key}")
            set(${out_error} "ownership key validation failed" PARENT_SCOPE)
            return()
        endif()
        set("transaction_written_owner_${owner_key}" TRUE)
        list(APPEND seen_owner_keys "${owner_key}")
    endforeach()

    _protocyte_generation_transaction_paths(transaction_active unused_transaction_releasing transaction_committed)
    _protocyte_normalized_path_identity(transaction_output_directory_identity "${OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_staging_directory_identity "${STAGING_OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_lock_directory_identity "${LOCK_DIRECTORY}")
    string(SHA256 transaction_target_hash "${GENERATION_TARGET}")
    string(SHA256 transaction_output_directory_hash "${transaction_output_directory_identity}")
    string(SHA256 transaction_staging_directory_hash "${transaction_staging_directory_identity}")
    string(SHA256 transaction_lock_directory_hash "${transaction_lock_directory_identity}")
    set(
        transaction_content
        "version=6\nbuild-tree-sha256=${BUILD_OWNER_HASH}\ntarget-sha256=${transaction_target_hash}\noutput-directory-sha256=${transaction_output_directory_hash}\nstaging-directory-sha256=${transaction_staging_directory_hash}\nlock-directory-sha256=${transaction_lock_directory_hash}\nowner-transaction-sha256=${owner_transaction_id}\nowner-count=${owner_key_count}\n"
    )
    foreach(owner_key IN LISTS seen_owner_keys)
        string(APPEND transaction_content "owner-key=${owner_key}\n")
    endforeach()
    string(APPEND transaction_content "output-count=${generation_output_count}\n")
    cmake_path(
        NORMAL_PATH
        OUTPUT_DIRECTORY
        OUTPUT_VARIABLE normalized_transaction_output_directory
    )
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            list(GET generation_outputs ${generation_output_index} generation_output)
            list(GET ${initial_states_var} ${generation_output_index} initial_state)
            list(GET ${initial_hashes_var} ${generation_output_index} initial_hash)
            list(GET ${staged_hashes_var} ${generation_output_index} staged_hash)
            if(
                NOT (initial_state STREQUAL "prior" OR initial_state STREQUAL "absent")
                OR (initial_state STREQUAL "prior" AND NOT initial_hash MATCHES "^[0-9a-f]+$")
                OR (initial_state STREQUAL "absent" AND NOT initial_hash STREQUAL "absent")
                OR NOT staged_hash MATCHES "^[0-9a-f]+$"
            )
                set(${out_error} "output state validation failed" PARENT_SCOPE)
                return()
            endif()
            string(LENGTH "${initial_hash}" initial_hash_length)
            string(LENGTH "${staged_hash}" staged_hash_length)
            if(
                (initial_state STREQUAL "prior" AND NOT initial_hash_length EQUAL 64)
                OR NOT staged_hash_length EQUAL 64
            )
                set(${out_error} "output hash length validation failed" PARENT_SCOPE)
                return()
            endif()
            cmake_path(
                RELATIVE_PATH
                generation_output
                BASE_DIRECTORY "${normalized_transaction_output_directory}"
                OUTPUT_VARIABLE generation_output_relative_path
            )
            cmake_path(
                IS_ABSOLUTE
                generation_output_relative_path
                generation_output_relative_is_absolute
            )
            if(
                generation_output_relative_path STREQUAL ""
                OR generation_output_relative_path MATCHES "^\\.\\.(\\\\|/|$)"
                OR generation_output_relative_is_absolute
            )
                set(${out_error} "output-relative path validation failed" PARENT_SCOPE)
                return()
            endif()
            string(HEX "${generation_output_relative_path}" encoded_generation_output)
            if(initial_state STREQUAL "absent")
                set(serialized_initial_hash "")
            else()
                set(serialized_initial_hash "${initial_hash}")
            endif()
            string(APPEND transaction_content "output-relative-hex=${encoded_generation_output}\n")
            string(APPEND transaction_content "initial=${initial_state}\n")
            string(APPEND transaction_content "initial-sha256=${serialized_initial_hash}\n")
            string(APPEND transaction_content "staged-sha256=${staged_hash}\n")
        endforeach()
    endif()
    set(transaction_staging "${transaction_active}.tmp")
    file(REMOVE "${transaction_staging}")
    if(EXISTS "${transaction_staging}" OR IS_SYMLINK "${transaction_staging}")
        set(${out_error} "stale journal staging cleanup failed" PARENT_SCOPE)
        return()
    endif()
    file(WRITE "${transaction_staging}" "${transaction_content}")
    if(
        NOT EXISTS "${transaction_staging}"
        OR IS_DIRECTORY "${transaction_staging}"
        OR IS_SYMLINK "${transaction_staging}"
    )
        set(${out_error} "journal staging creation failed" PARENT_SCOPE)
        return()
    endif()
    file(READ "${transaction_staging}" observed_transaction_content)
    if(NOT observed_transaction_content STREQUAL transaction_content)
        set(${out_error} "journal staging content verification failed" PARENT_SCOPE)
        return()
    endif()
    # Every declared output lock and the OUT_DIR ownership lock are held by
    # this process. An existing journal is therefore static corruption, while
    # a same-privilege actor racing this check is outside the execution model.
    # Check explicitly, then use the portable atomic rename path; CMake's
    # NO_REPLACE result is not reliable on every supported POSIX filesystem.
    if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        set(
            ${out_error}
            "an active journal already exists after recovery"
            PARENT_SCOPE
        )
        return()
    endif()
    file(
        RENAME "${transaction_staging}" "${transaction_active}"
        RESULT transaction_write_result
    )
    if("${transaction_write_result}" STREQUAL "0")
        _protocyte_verify_atomic_file_rename(
            transaction_write_consumed_source
            "${transaction_staging}"
            "${transaction_active}"
        )
        if(transaction_write_consumed_source)
            set(${out_written} TRUE PARENT_SCOPE)
            set(${out_error} "" PARENT_SCOPE)
            return()
        endif()
        set(transaction_write_result "rename retained conflicting source data")
    endif()
    if(NOT "${transaction_write_result}" STREQUAL "0")
        set(
            ${out_error}
            "atomic journal publication failed: ${transaction_write_result}"
            PARENT_SCOPE
        )
    endif()
endfunction()

function(
    _protocyte_read_generation_transaction
    out_is_present
    out_is_committed
    out_is_releasing
    out_owner_keys
    out_owner_transaction_id
    out_initial_states
    out_initial_hashes
    out_staged_hashes
)
    set(${out_is_present} FALSE PARENT_SCOPE)
    set(${out_is_committed} FALSE PARENT_SCOPE)
    set(${out_owner_keys} "" PARENT_SCOPE)
    set(${out_owner_transaction_id} "" PARENT_SCOPE)
    set(${out_initial_states} "" PARENT_SCOPE)
    set(${out_initial_hashes} "" PARENT_SCOPE)
    set(${out_staged_hashes} "" PARENT_SCOPE)
    set(${out_is_releasing} FALSE PARENT_SCOPE)
    _protocyte_generation_transaction_paths(transaction_active transaction_releasing transaction_committed)
    if(
        (EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        AND (EXISTS "${transaction_releasing}" OR IS_SYMLINK "${transaction_releasing}")
    )
        return()
    endif()
    if(
        (EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        AND (EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
    )
        return()
    endif()
    if(
        (EXISTS "${transaction_releasing}" OR IS_SYMLINK "${transaction_releasing}")
        AND (EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
    )
        return()
    endif()
    if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        set(transaction_record "${transaction_active}")
        set(transaction_is_committed FALSE)
        set(transaction_is_releasing FALSE)
    elseif(EXISTS "${transaction_releasing}" OR IS_SYMLINK "${transaction_releasing}")
        set(transaction_record "${transaction_releasing}")
        set(transaction_is_committed FALSE)
        set(transaction_is_releasing TRUE)
    elseif(EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
        set(transaction_record "${transaction_committed}")
        set(transaction_is_committed TRUE)
        set(transaction_is_releasing FALSE)
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
    if(transaction_line_count LESS 9)
        return()
    endif()
    list(GET transaction_lines 0 transaction_version)
    list(GET transaction_lines 1 transaction_build_hash_line)
    list(GET transaction_lines 2 transaction_target_hash_line)
    list(GET transaction_lines 3 transaction_output_directory_hash_line)
    list(GET transaction_lines 4 transaction_staging_directory_hash_line)
    list(GET transaction_lines 5 transaction_lock_directory_hash_line)
    list(GET transaction_lines 6 transaction_owner_id_line)
    list(GET transaction_lines 7 transaction_owner_count_line)
    _protocyte_normalized_path_identity(transaction_output_directory_identity "${OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_staging_directory_identity "${STAGING_OUTPUT_DIRECTORY}")
    _protocyte_normalized_path_identity(transaction_lock_directory_identity "${LOCK_DIRECTORY}")
    string(SHA256 transaction_target_hash "${GENERATION_TARGET}")
    string(SHA256 transaction_output_directory_hash "${transaction_output_directory_identity}")
    string(SHA256 transaction_staging_directory_hash "${transaction_staging_directory_identity}")
    string(SHA256 transaction_lock_directory_hash "${transaction_lock_directory_identity}")
    if(
        NOT transaction_version STREQUAL "version=6"
        OR NOT transaction_build_hash_line STREQUAL "build-tree-sha256=${BUILD_OWNER_HASH}"
        OR NOT transaction_target_hash_line STREQUAL "target-sha256=${transaction_target_hash}"
        OR NOT transaction_output_directory_hash_line STREQUAL "output-directory-sha256=${transaction_output_directory_hash}"
        OR NOT transaction_staging_directory_hash_line STREQUAL "staging-directory-sha256=${transaction_staging_directory_hash}"
        OR NOT transaction_lock_directory_hash_line STREQUAL "lock-directory-sha256=${transaction_lock_directory_hash}"
        OR NOT transaction_owner_id_line MATCHES "^owner-transaction-sha256=([0-9a-f]*)$"
        OR NOT transaction_owner_count_line MATCHES "^owner-count=([0-9]+)$"
    )
        return()
    endif()
    string(REGEX REPLACE "^owner-transaction-sha256=" "" transaction_owner_transaction_id "${transaction_owner_id_line}")
    string(REGEX REPLACE "^owner-count=" "" transaction_owner_count "${transaction_owner_count_line}")
    list(LENGTH generation_outputs generation_output_count)
    math(EXPR maximum_transaction_owner_count "${generation_output_count} + 1")
    if(transaction_owner_count GREATER maximum_transaction_owner_count)
        return()
    endif()
    if(transaction_owner_count GREATER 0)
        string(LENGTH "${transaction_owner_transaction_id}" transaction_owner_transaction_id_length)
        if(
            NOT transaction_owner_transaction_id_length EQUAL 64
            OR NOT transaction_owner_transaction_id MATCHES "^[0-9a-f]+$"
        )
            return()
        endif()
    elseif(NOT transaction_owner_transaction_id STREQUAL "")
        return()
    endif()
    set(transaction_line_index 8)
    set(transaction_owner_keys)
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
            set(transaction_owner_key "${CMAKE_MATCH_1}")
            _protocyte_generation_transaction_owner_marker_for_key(
                transaction_owner_marker transaction_owner_key_known "${transaction_owner_key}"
            )
            if(NOT transaction_owner_key_known OR DEFINED "transaction_read_owner_${transaction_owner_key}")
                return()
            endif()
            set("transaction_read_owner_${transaction_owner_key}" TRUE)
            list(APPEND transaction_owner_keys "${transaction_owner_key}")
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
    if(NOT transaction_output_count EQUAL generation_output_count)
        return()
    endif()
    math(EXPR transaction_line_index "${transaction_line_index} + 1")
    set(transaction_initial_states)
    set(transaction_initial_hashes)
    set(transaction_staged_hashes)
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            math(EXPR transaction_last_output_line "${transaction_line_index} + 3")
            if(transaction_last_output_line GREATER_EQUAL transaction_line_count)
                return()
            endif()
            list(GET transaction_lines ${transaction_line_index} transaction_output_line)
            math(EXPR transaction_initial_line_index "${transaction_line_index} + 1")
            math(EXPR transaction_initial_hash_line_index "${transaction_line_index} + 2")
            math(EXPR transaction_staged_hash_line_index "${transaction_line_index} + 3")
            list(GET transaction_lines ${transaction_initial_line_index} transaction_initial_line)
            list(GET transaction_lines ${transaction_initial_hash_line_index} transaction_initial_hash_line)
            list(GET transaction_lines ${transaction_staged_hash_line_index} transaction_staged_hash_line)
            if(NOT transaction_output_line MATCHES "^output-relative-hex=([0-9a-f]+)$")
                return()
            endif()
            set(encoded_transaction_output "${CMAKE_MATCH_1}")
            if(NOT transaction_initial_line MATCHES "^initial=(prior|absent)$")
                return()
            endif()
            string(REGEX REPLACE "^initial=" "" transaction_initial_state "${transaction_initial_line}")
            if(NOT transaction_initial_hash_line MATCHES "^initial-sha256=([0-9a-f]*)$")
                return()
            endif()
            string(REGEX REPLACE "^initial-sha256=" "" transaction_initial_hash "${transaction_initial_hash_line}")
            if(NOT transaction_staged_hash_line MATCHES "^staged-sha256=([0-9a-f]+)$")
                return()
            endif()
            string(REGEX REPLACE "^staged-sha256=" "" transaction_staged_hash "${transaction_staged_hash_line}")
            string(LENGTH "${transaction_initial_hash}" transaction_initial_hash_length)
            string(LENGTH "${transaction_staged_hash}" transaction_staged_hash_length)
            if(
                (transaction_initial_state STREQUAL "prior" AND (NOT transaction_initial_hash_length EQUAL 64 OR NOT transaction_initial_hash MATCHES "^[0-9a-f]+$"))
                OR (transaction_initial_state STREQUAL "absent" AND NOT transaction_initial_hash STREQUAL "")
                OR NOT transaction_staged_hash_length EQUAL 64
            )
                return()
            endif()
            _protocyte_decode_generation_hex(transaction_output_relative_path "${encoded_transaction_output}")
            if(
                transaction_output_relative_path STREQUAL ""
                OR transaction_output_relative_path MATCHES "^\\.\\.(\\\\|/|$)"
                OR IS_ABSOLUTE "${transaction_output_relative_path}"
            )
                return()
            endif()
            cmake_path(APPEND OUTPUT_DIRECTORY "${transaction_output_relative_path}" OUTPUT_VARIABLE transaction_output)
            cmake_path(NORMAL_PATH transaction_output)
            list(GET generation_outputs ${generation_output_index} generation_output)
            _protocyte_normalized_path_identity(transaction_output_identity "${transaction_output}")
            _protocyte_normalized_path_identity(generation_output_identity "${generation_output}")
            if(NOT transaction_output_identity STREQUAL generation_output_identity)
                return()
            endif()
            if(transaction_initial_state STREQUAL "absent")
                set(transaction_initial_hash "absent")
            endif()
            list(APPEND transaction_initial_states "${transaction_initial_state}")
            list(APPEND transaction_initial_hashes "${transaction_initial_hash}")
            list(APPEND transaction_staged_hashes "${transaction_staged_hash}")
            math(EXPR transaction_line_index "${transaction_line_index} + 4")
        endforeach()
    endif()
    if(NOT transaction_line_index EQUAL transaction_line_count)
        return()
    endif()
    set(${out_is_present} TRUE PARENT_SCOPE)
    set(${out_is_committed} "${transaction_is_committed}" PARENT_SCOPE)
    set(${out_is_releasing} "${transaction_is_releasing}" PARENT_SCOPE)
    set(${out_owner_keys} "${transaction_owner_keys}" PARENT_SCOPE)
    set(${out_owner_transaction_id} "${transaction_owner_transaction_id}" PARENT_SCOPE)
    set(${out_initial_states} "${transaction_initial_states}" PARENT_SCOPE)
    set(${out_initial_hashes} "${transaction_initial_hashes}" PARENT_SCOPE)
    set(${out_staged_hashes} "${transaction_staged_hashes}" PARENT_SCOPE)
endfunction()

function(_protocyte_generation_transaction_path_hash_state out_state path first_hash second_hash)
    set(${out_state} "missing" PARENT_SCOPE)
    if(NOT EXISTS "${path}" AND NOT IS_SYMLINK "${path}")
        return()
    endif()
    if(IS_DIRECTORY "${path}" OR IS_SYMLINK "${path}")
        set(${out_state} "unsafe" PARENT_SCOPE)
        return()
    endif()
    file(SHA256 "${path}" observed_hash)
    if(observed_hash STREQUAL first_hash)
        # A no-op regeneration legitimately gives the prior and staged bytes
        # the same digest.  Keep that ambiguity explicit: the caller must use
        # the complete output/backup/staging triple to classify progress.
        if(first_hash STREQUAL second_hash)
            set(${out_state} "both" PARENT_SCOPE)
        else()
            set(${out_state} "first" PARENT_SCOPE)
        endif()
    elseif(observed_hash STREQUAL second_hash)
        set(${out_state} "second" PARENT_SCOPE)
    else()
        set(${out_state} "mismatch" PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_generation_transaction_staged_state out_state path staged_hash)
    set(${out_state} "missing" PARENT_SCOPE)
    if(NOT EXISTS "${path}" AND NOT IS_SYMLINK "${path}")
        return()
    endif()
    if(IS_DIRECTORY "${path}" OR IS_SYMLINK "${path}")
        set(${out_state} "unsafe" PARENT_SCOPE)
        return()
    endif()
    _protocyte_generation_transaction_file_hash_matches(matches "${path}" "${staged_hash}")
    if(matches)
        set(${out_state} "present" PARENT_SCOPE)
    else()
        set(${out_state} "mismatch" PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_recover_generation_transaction out_recovered)
    set(${out_recovered} FALSE PARENT_SCOPE)
    _protocyte_generation_transaction_paths(transaction_active transaction_releasing transaction_committed)
    if(
        (EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        AND (EXISTS "${transaction_releasing}" OR IS_SYMLINK "${transaction_releasing}")
    )
        return()
    endif()
    if(
        (EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
        AND (EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
    )
        return()
    endif()
    if(
        (EXISTS "${transaction_releasing}" OR IS_SYMLINK "${transaction_releasing}")
        AND (EXISTS "${transaction_committed}" OR IS_SYMLINK "${transaction_committed}")
    )
        return()
    endif()
    foreach(transaction_record IN ITEMS "${transaction_active}" "${transaction_releasing}" "${transaction_committed}")
        if(
            (EXISTS "${transaction_record}" OR IS_SYMLINK "${transaction_record}")
            AND (IS_DIRECTORY "${transaction_record}" OR IS_SYMLINK "${transaction_record}")
        )
            return()
        endif()
    endforeach()
    _protocyte_read_generation_transaction(
        transaction_is_present transaction_is_committed transaction_is_releasing transaction_owner_keys
        transaction_owner_transaction_id transaction_initial_states
        transaction_initial_hashes transaction_staged_hashes
    )
    if(NOT transaction_is_present)
        if(
            NOT EXISTS "${transaction_active}" AND NOT IS_SYMLINK "${transaction_active}"
            AND NOT EXISTS "${transaction_releasing}" AND NOT IS_SYMLINK "${transaction_releasing}"
            AND NOT EXISTS "${transaction_committed}" AND NOT IS_SYMLINK "${transaction_committed}"
        )
            set(${out_recovered} TRUE PARENT_SCOPE)
        endif()
        return()
    endif()

    # Resolve every journal key, attest all owner records, and derive every
    # output action before a recovery mutation.  This is the static-corruption
    # trust boundary: late malformed entries cannot partially roll back a tree.
    set(transaction_owner_markers)
    foreach(transaction_owner_key IN LISTS transaction_owner_keys)
        _protocyte_generation_transaction_owner_marker_for_key(
            transaction_owner_marker transaction_owner_key_known "${transaction_owner_key}"
        )
        if(NOT transaction_owner_key_known)
            return()
        endif()
        list(APPEND transaction_owner_markers "${transaction_owner_marker}")
        set("transaction_journal_owner_${transaction_owner_key}" TRUE)
    endforeach()
    set(allowed_owner_keys root)
    foreach(output_lock_key IN LISTS output_lock_keys)
        list(APPEND allowed_owner_keys "${output_lock_key}")
    endforeach()
    foreach(allowed_owner_key IN LISTS allowed_owner_keys)
        _protocyte_generation_transaction_owner_marker_for_key(
            allowed_owner_marker allowed_owner_key_known "${allowed_owner_key}"
        )
        if(NOT allowed_owner_key_known)
            return()
        endif()
        _protocyte_owner_record_status(
            allowed_owner_status allowed_owner_id "${allowed_owner_marker}"
            "${BUILD_OWNER_HASH}" "${OUT_DIR_OWNER_MARKER}"
        )
        set("transaction_owner_status_${allowed_owner_key}" "${allowed_owner_status}")
        set("transaction_owner_id_${allowed_owner_key}" "${allowed_owner_id}")
        if(
            NOT DEFINED "transaction_journal_owner_${allowed_owner_key}"
            AND NOT allowed_owner_status STREQUAL "current"
        )
            return()
        endif()
    endforeach()

    list(LENGTH transaction_owner_keys transaction_owner_count)
    set(transaction_ownership_committed FALSE)
    set(transaction_discard_preparation FALSE)
    set(transaction_releasing_witness_removed FALSE)
    if(transaction_owner_count EQUAL 0)
        if(NOT transaction_owner_transaction_id STREQUAL "")
            return()
        endif()
        set(transaction_ownership_committed TRUE)
    else()
        _protocyte_owner_transaction_paths(
            transaction_prepared_witness transaction_committed_witness
            "${OUT_DIR_OWNER_MARKER}" "${transaction_owner_transaction_id}"
        )
        if(EXISTS "${transaction_committed_witness}" OR IS_SYMLINK "${transaction_committed_witness}")
            _protocyte_generation_transaction_claims_match(
                committed_claims_match transaction_owner_markers "${transaction_owner_transaction_id}"
            )
            if(NOT committed_claims_match)
                return()
            endif()
            foreach(transaction_owner_key IN LISTS transaction_owner_keys)
                set(owner_status "${transaction_owner_status_${transaction_owner_key}}")
                set(owner_id "${transaction_owner_id_${transaction_owner_key}}")
                if(owner_status STREQUAL "current")
                    if(NOT owner_id STREQUAL transaction_owner_transaction_id)
                        return()
                    endif()
                elseif(
                    NOT owner_status STREQUAL "missing"
                    OR NOT transaction_is_releasing
                )
                    # The committed publication record is an ownership
                    # attestation, not a cleanup record: every planned claim
                    # must still exist and bind to its witness.  A missing
                    # claim becomes recoverable only after the separate
                    # active->releasing rename records that release began.
                    return()
                endif()
            endforeach()
            set(transaction_ownership_committed TRUE)
        elseif(EXISTS "${transaction_prepared_witness}" OR IS_SYMLINK "${transaction_prepared_witness}")
            _protocyte_generation_transaction_claims_match(
                prepared_claims_match transaction_owner_markers
                "${transaction_owner_transaction_id}" "prepared"
            )
            if(NOT prepared_claims_match)
                return()
            endif()
            foreach(transaction_owner_key IN LISTS transaction_owner_keys)
                set(owner_status "${transaction_owner_status_${transaction_owner_key}}")
                set(owner_id "${transaction_owner_id_${transaction_owner_key}}")
                if(
                    NOT owner_status STREQUAL "missing"
                    AND (NOT owner_status STREQUAL "incomplete" OR NOT owner_id STREQUAL transaction_owner_transaction_id)
                )
                    return()
                endif()
            endforeach()
            set(transaction_discard_preparation TRUE)
        else()
            foreach(transaction_owner_key IN LISTS transaction_owner_keys)
                if(NOT "${transaction_owner_status_${transaction_owner_key}}" STREQUAL "missing")
                    return()
                endif()
            endforeach()
            if(transaction_is_releasing)
                # A crash after the committed witness is removed leaves the
                # immutable release-phase journal plus no remaining claims.
                # That exact cut is safe only after the output preflight below
                # proves every planned output was restored.
                set(transaction_releasing_witness_removed TRUE)
            else()
                set(transaction_manifest_staging "${OUT_DIR_OWNER_MARKER}.${transaction_owner_transaction_id}.manifest.tmp")
                if(EXISTS "${transaction_manifest_staging}" OR IS_SYMLINK "${transaction_manifest_staging}")
                    _protocyte_generation_transaction_file_hash_matches(
                        manifest_staging_hash_matches "${transaction_manifest_staging}"
                        "${transaction_owner_transaction_id}"
                    )
                    if(NOT manifest_staging_hash_matches)
                        return()
                    endif()
                endif()
                foreach(transaction_owner_marker IN LISTS transaction_owner_markers)
                    set(transaction_owner_staging "${transaction_owner_marker}.${transaction_owner_transaction_id}.tmp")
                    if(EXISTS "${transaction_owner_staging}" OR IS_SYMLINK "${transaction_owner_staging}")
                        _protocyte_generation_transaction_owner_record_hash_matches(
                            owner_staging_hash_matches "${transaction_owner_staging}"
                            "${transaction_owner_transaction_id}"
                        )
                        if(NOT owner_staging_hash_matches)
                            return()
                        endif()
                    endif()
                endforeach()
                set(transaction_discard_preparation TRUE)
            endif()
        endif()
    endif()

    list(LENGTH generation_outputs generation_output_count)

    # A committed journal has crossed the publication commit point.  Its only
    # recovery is attestation plus removal; backups may still exist if a hard
    # exit landed before staging cleanup, but they must never trigger rollback.
    if(transaction_is_committed)
        if(NOT transaction_ownership_committed)
            return()
        endif()
        foreach(generation_output_index RANGE 0 ${generation_output_count})
            if(generation_output_index EQUAL generation_output_count)
                break()
            endif()
            list(GET generation_outputs ${generation_output_index} generation_output)
            list(GET transaction_staged_hashes ${generation_output_index} transaction_staged_hash)
            _protocyte_generated_output_path_is_safe(committed_output_is_safe "${generation_output}" "${OUTPUT_DIRECTORY}")
            _protocyte_generation_transaction_file_hash_matches(
                committed_output_hash_matches "${generation_output}" "${transaction_staged_hash}"
            )
            if(NOT committed_output_is_safe OR NOT committed_output_hash_matches)
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

    set(recovery_remove_actions)
    set(recovery_restore_actions)
    set(all_outputs_forward_initial TRUE)
    set(all_outputs_recovered TRUE)
    if(generation_output_count GREATER 0)
        math(EXPR last_generation_output_index "${generation_output_count} - 1")
        foreach(generation_output_index RANGE 0 ${last_generation_output_index})
            list(GET generation_outputs ${generation_output_index} generation_output)
            list(GET transaction_initial_states ${generation_output_index} transaction_initial_state)
            list(GET transaction_initial_hashes ${generation_output_index} transaction_initial_hash)
            list(GET transaction_staged_hashes ${generation_output_index} transaction_staged_hash)
            _protocyte_staged_output_path(staged_generation_output "generated" "${generation_output}")
            _protocyte_staged_output_path(backup_generation_output "backups" "${generation_output}")
            _protocyte_generated_output_path_is_safe(recovery_output_is_safe "${generation_output}" "${OUTPUT_DIRECTORY}")
            _protocyte_generated_output_path_is_safe(backup_output_is_safe "${backup_generation_output}" "${STAGING_OUTPUT_DIRECTORY}/backups")
            if(NOT recovery_output_is_safe OR NOT backup_output_is_safe)
                return()
            endif()
            _protocyte_generation_transaction_staged_state(staged_state "${staged_generation_output}" "${transaction_staged_hash}")
            # Recovery never consumes staged bytes. A late mismatch, directory,
            # or linked leaf must prevent publication, but it must not strand
            # trusted originals that are already in the journal-bound backup
            # paths. Output and backup hashes below remain the rollback trust
            # boundary; the entire staging tree is discarded afterward.
            if(transaction_initial_state STREQUAL "prior")
                _protocyte_generation_transaction_path_hash_state(
                    output_state "${generation_output}" "${transaction_initial_hash}" "${transaction_staged_hash}"
                )
                _protocyte_generation_transaction_path_hash_state(
                    backup_state "${backup_generation_output}" "${transaction_initial_hash}" "${transaction_staged_hash}"
                )
                if(transaction_initial_hash STREQUAL transaction_staged_hash)
                    # The hash alone cannot distinguish an untouched prior
                    # output from a published no-op.  The three atomic rename
                    # locations do: source+staging is untouched, backup+
                    # staging is backed up, source+backup is published, and
                    # source alone is an already-restored recovery cut.
                    if(output_state STREQUAL "both" AND backup_state STREQUAL "missing")
                        if(staged_state STREQUAL "present")
                            # Untouched forward state.
                        elseif(NOT staged_state STREQUAL "missing")
                            return()
                        else()
                            # Recovery already restored this output after a
                            # published no-op; the staged source is gone.
                            set(all_outputs_forward_initial FALSE)
                        endif()
                        list(APPEND recovery_remove_actions FALSE)
                        list(APPEND recovery_restore_actions FALSE)
                    elseif(output_state STREQUAL "missing" AND backup_state STREQUAL "both")
                        set(all_outputs_forward_initial FALSE)
                        set(all_outputs_recovered FALSE)
                        list(APPEND recovery_remove_actions FALSE)
                        list(APPEND recovery_restore_actions TRUE)
                    elseif(output_state STREQUAL "both" AND backup_state STREQUAL "both")
                        set(all_outputs_forward_initial FALSE)
                        set(all_outputs_recovered FALSE)
                        list(APPEND recovery_remove_actions TRUE)
                        list(APPEND recovery_restore_actions TRUE)
                    else()
                        return()
                    endif()
                else()
                    if(
                        NOT (output_state STREQUAL "first" OR output_state STREQUAL "second" OR output_state STREQUAL "missing")
                        OR NOT (backup_state STREQUAL "first" OR backup_state STREQUAL "missing")
                    )
                        return()
                    endif()
                    if(
                        (output_state STREQUAL "first" AND NOT backup_state STREQUAL "missing")
                        OR (output_state STREQUAL "second" AND NOT backup_state STREQUAL "first")
                        OR (output_state STREQUAL "missing" AND NOT backup_state STREQUAL "first")
                    )
                        return()
                    endif()
                    if(NOT (output_state STREQUAL "first" AND backup_state STREQUAL "missing" AND staged_state STREQUAL "present"))
                        set(all_outputs_forward_initial FALSE)
                    endif()
                    if(NOT (output_state STREQUAL "first" AND backup_state STREQUAL "missing"))
                        set(all_outputs_recovered FALSE)
                    endif()
                    if(output_state STREQUAL "second")
                        list(APPEND recovery_remove_actions TRUE)
                        list(APPEND recovery_restore_actions TRUE)
                    elseif(output_state STREQUAL "missing")
                        list(APPEND recovery_remove_actions FALSE)
                        list(APPEND recovery_restore_actions TRUE)
                    else()
                        list(APPEND recovery_remove_actions FALSE)
                        list(APPEND recovery_restore_actions FALSE)
                    endif()
                endif()
            elseif(transaction_initial_state STREQUAL "absent")
                _protocyte_generation_transaction_path_hash_state(
                    output_state "${generation_output}" "${transaction_staged_hash}" "${transaction_staged_hash}"
                )
                if(NOT (output_state STREQUAL "both" OR output_state STREQUAL "missing"))
                    return()
                endif()
                if(EXISTS "${backup_generation_output}" OR IS_SYMLINK "${backup_generation_output}")
                    return()
                endif()
                if(NOT (output_state STREQUAL "missing" AND staged_state STREQUAL "present"))
                    set(all_outputs_forward_initial FALSE)
                endif()
                if(NOT output_state STREQUAL "missing")
                    set(all_outputs_recovered FALSE)
                endif()
                if(output_state STREQUAL "both")
                    list(APPEND recovery_remove_actions TRUE)
                else()
                    list(APPEND recovery_remove_actions FALSE)
                endif()
                list(APPEND recovery_restore_actions FALSE)
            else()
                return()
            endif()
        endforeach()
    endif()

    if(transaction_releasing_witness_removed)
        if(NOT all_outputs_recovered)
            return()
        endif()
        file(REMOVE "${transaction_releasing}")
        if(EXISTS "${transaction_releasing}" OR IS_SYMLINK "${transaction_releasing}")
            return()
        endif()
        set(${out_recovered} TRUE PARENT_SCOPE)
        return()
    endif()

    if(transaction_discard_preparation)
        if(transaction_is_releasing OR NOT all_outputs_forward_initial)
            return()
        endif()
        foreach(transaction_owner_key IN LISTS transaction_owner_keys)
            set(transaction_owner_marker "")
            _protocyte_generation_transaction_owner_marker_for_key(transaction_owner_marker unused_known "${transaction_owner_key}")
            if("${transaction_owner_status_${transaction_owner_key}}" STREQUAL "incomplete")
                _protocyte_recover_incomplete_owner_record(
                    recovered_incomplete_owner "${transaction_owner_marker}"
                    "${transaction_owner_transaction_id}" "${OUT_DIR_OWNER_MARKER}"
                )
                if(NOT recovered_incomplete_owner)
                    return()
                endif()
            endif()
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
            transaction_prepared_witness unused_transaction_committed_witness
            "${OUT_DIR_OWNER_MARKER}" "${transaction_owner_transaction_id}"
        )
        file(REMOVE "${transaction_prepared_witness}")
        if(EXISTS "${transaction_prepared_witness}" OR IS_SYMLINK "${transaction_prepared_witness}")
            return()
        endif()
        file(REMOVE "${transaction_active}")
        if(EXISTS "${transaction_active}" OR IS_SYMLINK "${transaction_active}")
            return()
        endif()
        set(${out_recovered} TRUE PARENT_SCOPE)
        return()
    endif()

    # A single immutable phase rename records that owner release began.  It is
    # needed only for the one otherwise ambiguous state: a release interrupted
    # before any output was ever published.  It is O(1), path-free, and does
    # not add mutable per-output journal state.
    set(any_missing_committed_owner FALSE)
    foreach(transaction_owner_key IN LISTS transaction_owner_keys)
        if("${transaction_owner_status_${transaction_owner_key}}" STREQUAL "missing")
            set(any_missing_committed_owner TRUE)
        endif()
    endforeach()
    if(
        (transaction_is_releasing AND NOT all_outputs_recovered)
        OR (any_missing_committed_owner AND NOT transaction_is_releasing)
    )
        return()
    endif()

    # The plan above fully validated every action and hash before this first
    # mutation.  A hard exit between any two atomics simply re-enters one of
    # the accepted filesystem states on the next invocation.
    foreach(generation_output_index RANGE 0 ${last_generation_output_index})
        list(GET recovery_remove_actions ${generation_output_index} recovery_remove)
        list(GET recovery_restore_actions ${generation_output_index} recovery_restore)
        list(GET generation_outputs ${generation_output_index} generation_output)
        if(recovery_remove)
            file(REMOVE "${generation_output}")
            if(EXISTS "${generation_output}" OR IS_SYMLINK "${generation_output}")
                return()
            endif()
        endif()
        if(recovery_restore)
            _protocyte_staged_output_path(backup_generation_output "backups" "${generation_output}")
            file(RENAME "${backup_generation_output}" "${generation_output}" NO_REPLACE RESULT restore_output_result)
            if("${restore_output_result}" STREQUAL "0")
                _protocyte_verify_atomic_file_rename(
                    restore_consumed_source
                    "${backup_generation_output}"
                    "${generation_output}"
                )
            endif()
            if(
                NOT "${restore_output_result}" STREQUAL "0"
                OR NOT restore_consumed_source
            )
                return()
            endif()
        endif()
    endforeach()
    if(transaction_owner_count GREATER 0 AND NOT transaction_is_releasing)
        file(RENAME "${transaction_active}" "${transaction_releasing}" NO_REPLACE RESULT transaction_release_result)
        if("${transaction_release_result}" STREQUAL "0")
            _protocyte_verify_atomic_file_rename(
                transaction_release_consumed_source
                "${transaction_active}"
                "${transaction_releasing}"
            )
        endif()
        if(
            NOT "${transaction_release_result}" STREQUAL "0"
            OR NOT transaction_release_consumed_source
        )
            return()
        endif()
        set(transaction_is_releasing TRUE)
    endif()
    foreach(transaction_owner_key IN LISTS transaction_owner_keys)
        if("${transaction_owner_status_${transaction_owner_key}}" STREQUAL "current")
            _protocyte_generation_transaction_owner_marker_for_key(
                transaction_owner_marker unused_known "${transaction_owner_key}"
            )
            file(REMOVE "${transaction_owner_marker}")
            if(EXISTS "${transaction_owner_marker}" OR IS_SYMLINK "${transaction_owner_marker}")
                return()
            endif()
        endif()
    endforeach()
    if(transaction_owner_count GREATER 0)
        _protocyte_owner_transaction_paths(
            unused_transaction_prepared_witness transaction_committed_witness
            "${OUT_DIR_OWNER_MARKER}" "${transaction_owner_transaction_id}"
        )
        file(REMOVE "${transaction_committed_witness}")
        if(EXISTS "${transaction_committed_witness}" OR IS_SYMLINK "${transaction_committed_witness}")
            return()
        endif()
    endif()
    if(transaction_is_releasing)
        set(transaction_cleanup_record "${transaction_releasing}")
    else()
        set(transaction_cleanup_record "${transaction_active}")
    endif()
    file(REMOVE "${transaction_cleanup_record}")
    if(EXISTS "${transaction_cleanup_record}" OR IS_SYMLINK "${transaction_cleanup_record}")
        return()
    endif()
    set(${out_recovered} TRUE PARENT_SCOPE)
endfunction()
