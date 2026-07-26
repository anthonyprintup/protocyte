include_guard(GLOBAL)

function(_protocyte_normalized_path_identity out_var path)
    cmake_path(NORMAL_PATH path OUTPUT_VARIABLE path_identity)
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${path_identity}" path_identity)
    endif()
    set(${out_var} "${path_identity}" PARENT_SCOPE)
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

function(
    _protocyte_verify_atomic_file_rename
    out_var
    source_path
    destination_path
)
    set(${out_var} FALSE PARENT_SCOPE)
    if(NOT EXISTS "${source_path}" AND NOT IS_SYMLINK "${source_path}")
        set(${out_var} TRUE PARENT_SCOPE)
        return()
    endif()
    if(
        IS_DIRECTORY "${source_path}"
        OR IS_SYMLINK "${source_path}"
        OR NOT EXISTS "${destination_path}"
        OR IS_DIRECTORY "${destination_path}"
        OR IS_SYMLINK "${destination_path}"
    )
        return()
    endif()
    file(SHA256 "${source_path}" source_hash)
    file(SHA256 "${destination_path}" destination_hash)
    if(NOT source_hash STREQUAL destination_hash)
        return()
    endif()
    file(REMOVE "${source_path}")
    if(NOT EXISTS "${source_path}" AND NOT IS_SYMLINK "${source_path}")
        set(${out_var} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(
    _protocyte_owner_transaction_paths
    out_prepared
    out_committed
    root_owner_marker
    transaction_id
)
    set(transaction_prefix "${root_owner_marker}.${transaction_id}")
    set(${out_prepared} "${transaction_prefix}.prepared" PARENT_SCOPE)
    set(${out_committed} "${transaction_prefix}.committed" PARENT_SCOPE)
endfunction()

function(
    _protocyte_owner_record_status
    out_status
    out_transaction_id
    owner_marker
    expected_build_hash
    root_owner_marker
)
    set(owner_status "missing")
    set(owner_transaction_id "")
    if(EXISTS "${owner_marker}" OR IS_SYMLINK "${owner_marker}")
        if(IS_DIRECTORY "${owner_marker}" OR IS_SYMLINK "${owner_marker}")
            set(owner_status "malformed")
        else()
            file(READ "${owner_marker}" observed_owner LIMIT 512)
            string(
                REGEX MATCH
                "^version=1\nbuild-tree-sha256=([0-9a-f]+)\n$"
                valid_legacy_owner
                "${observed_owner}"
            )
            set(observed_build_hash "${CMAKE_MATCH_1}")
            string(LENGTH "${observed_build_hash}" observed_build_hash_length)
            if(
                valid_legacy_owner STREQUAL observed_owner
                AND observed_build_hash_length EQUAL 64
            )
                if(observed_build_hash STREQUAL expected_build_hash)
                    set(owner_status "current")
                else()
                    set(owner_status "different")
                endif()
            else()
                string(
                    REGEX MATCH
                    "^version=2\nbuild-tree-sha256=([0-9a-f]+)\ntransaction-sha256=([0-9a-f]+)\n$"
                    valid_transaction_owner
                    "${observed_owner}"
                )
                set(observed_build_hash "${CMAKE_MATCH_1}")
                set(owner_transaction_id "${CMAKE_MATCH_2}")
                string(LENGTH "${observed_build_hash}" observed_build_hash_length)
                string(LENGTH "${owner_transaction_id}" transaction_id_length)
                if(
                    NOT valid_transaction_owner STREQUAL observed_owner
                    OR NOT observed_build_hash_length EQUAL 64
                    OR NOT transaction_id_length EQUAL 64
                )
                    set(owner_status "malformed")
                else()
                    _protocyte_owner_transaction_paths(
                        prepared_path
                        committed_path
                        "${root_owner_marker}"
                        "${owner_transaction_id}"
                    )
                    set(owner_manifest_path "")
                    set(owner_manifest_state "")
                    if(EXISTS "${committed_path}" OR IS_SYMLINK "${committed_path}")
                        if(IS_DIRECTORY "${committed_path}" OR IS_SYMLINK "${committed_path}")
                            set(owner_status "malformed")
                        else()
                            set(owner_manifest_path "${committed_path}")
                            set(owner_manifest_state "committed")
                        endif()
                    elseif(EXISTS "${prepared_path}" OR IS_SYMLINK "${prepared_path}")
                        if(IS_DIRECTORY "${prepared_path}" OR IS_SYMLINK "${prepared_path}")
                            set(owner_status "unverifiable")
                        else()
                            set(owner_manifest_path "${prepared_path}")
                            set(owner_manifest_state "prepared")
                        endif()
                    else()
                        # A missing witness may mean interrupted publication, cache
                        # deletion, or an alternate historical lock namespace. It
                        # is never sufficient proof for automatic reclamation.
                        set(owner_status "unverifiable")
                    endif()
                    if(NOT owner_manifest_path STREQUAL "")
                        set(manifest_is_valid TRUE)
                        file(SIZE "${owner_manifest_path}" owner_manifest_size)
                        if(owner_manifest_size GREATER 16777216)
                            set(manifest_is_valid FALSE)
                        else()
                            file(STRINGS "${owner_manifest_path}" committed_manifest_lines)
                            list(LENGTH committed_manifest_lines manifest_line_count)
                            if(manifest_line_count LESS 5)
                                set(manifest_is_valid FALSE)
                            else()
                                list(GET committed_manifest_lines 0 manifest_version_line)
                                list(GET committed_manifest_lines 1 manifest_nonce_line)
                                list(GET committed_manifest_lines 2 manifest_build_hash_line)
                                list(GET committed_manifest_lines 3 manifest_claims_hash_line)
                                if(NOT manifest_version_line STREQUAL "version=1")
                                    set(manifest_is_valid FALSE)
                                endif()
                                string(
                                    REGEX MATCH
                                    "^nonce=([0-9a-f]+)$"
                                    valid_manifest_nonce
                                    "${manifest_nonce_line}"
                                )
                                set(manifest_nonce "${CMAKE_MATCH_1}")
                                string(
                                    REGEX MATCH
                                    "^build-tree-sha256=([0-9a-f]+)$"
                                    valid_manifest_build_hash
                                    "${manifest_build_hash_line}"
                                )
                                set(manifest_build_hash "${CMAKE_MATCH_1}")
                                string(
                                    REGEX MATCH
                                    "^claims-sha256=([0-9a-f]+)$"
                                    valid_manifest_claims_hash
                                    "${manifest_claims_hash_line}"
                                )
                                set(manifest_claims_hash "${CMAKE_MATCH_1}")
                                string(LENGTH "${manifest_nonce}" manifest_nonce_length)
                                string(
                                    LENGTH
                                    "${manifest_build_hash}"
                                    manifest_build_hash_length
                                )
                                string(
                                    LENGTH
                                    "${manifest_claims_hash}"
                                    manifest_claims_hash_length
                                )
                                if(
                                    NOT valid_manifest_nonce STREQUAL manifest_nonce_line
                                    OR NOT valid_manifest_build_hash STREQUAL manifest_build_hash_line
                                    OR NOT valid_manifest_claims_hash STREQUAL manifest_claims_hash_line
                                    OR NOT manifest_nonce_length EQUAL 64
                                    OR NOT manifest_build_hash_length EQUAL 64
                                    OR NOT manifest_claims_hash_length EQUAL 64
                                    OR NOT manifest_build_hash STREQUAL observed_build_hash
                                )
                                    set(manifest_is_valid FALSE)
                                endif()

                                list(SUBLIST committed_manifest_lines 4 -1 manifest_claim_lines)
                                set(manifest_claim_ids)
                                foreach(manifest_claim_line IN LISTS manifest_claim_lines)
                                    string(
                                        REGEX MATCH
                                        "^claim-sha256=([0-9a-f]+)$"
                                        valid_manifest_claim
                                        "${manifest_claim_line}"
                                    )
                                    set(manifest_claim_id "${CMAKE_MATCH_1}")
                                    string(
                                        LENGTH
                                        "${manifest_claim_id}"
                                        manifest_claim_id_length
                                    )
                                    if(
                                        NOT valid_manifest_claim STREQUAL manifest_claim_line
                                        OR NOT manifest_claim_id_length EQUAL 64
                                    )
                                        set(manifest_is_valid FALSE)
                                    endif()
                                    list(APPEND manifest_claim_ids "${manifest_claim_id}")
                                endforeach()
                                set(sorted_manifest_claim_ids "${manifest_claim_ids}")
                                list(REMOVE_DUPLICATES sorted_manifest_claim_ids)
                                list(SORT sorted_manifest_claim_ids)
                                string(SHA256 observed_claims_hash "${manifest_claim_ids}")
                                _protocyte_normalized_path_identity(
                                    owner_marker_identity
                                    "${owner_marker}"
                                )
                                string(SHA256 owner_claim_id "${owner_marker_identity}")
                                list(FIND manifest_claim_ids "${owner_claim_id}" owner_claim_index)
                                if(
                                    NOT sorted_manifest_claim_ids STREQUAL manifest_claim_ids
                                    OR NOT observed_claims_hash STREQUAL manifest_claims_hash
                                    OR owner_claim_index EQUAL -1
                                )
                                    set(manifest_is_valid FALSE)
                                endif()
                            endif()
                        endif()
                        file(SHA256 "${owner_manifest_path}" committed_hash)
                        if(
                            NOT committed_hash STREQUAL owner_transaction_id
                            OR NOT manifest_is_valid
                        )
                            set(owner_status "malformed")
                        elseif(owner_manifest_state STREQUAL "prepared")
                            set(owner_status "incomplete")
                        elseif(observed_build_hash STREQUAL expected_build_hash)
                            set(owner_status "current")
                        else()
                            set(owner_status "different")
                        endif()
                    endif()
                endif()
            endif()
        endif()
    endif()
    set(${out_status} "${owner_status}" PARENT_SCOPE)
    set(${out_transaction_id} "${owner_transaction_id}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_recover_incomplete_owner_record
    out_recovered
    owner_marker
    transaction_id
    root_owner_marker
)
    set(recovered FALSE)
    string(LENGTH "${transaction_id}" transaction_id_length)
    if(NOT transaction_id_length EQUAL 64 OR NOT transaction_id MATCHES "^[0-9a-f]+$")
        set(${out_recovered} FALSE PARENT_SCOPE)
        return()
    endif()
    if(
        EXISTS "${owner_marker}"
        AND NOT IS_DIRECTORY "${owner_marker}"
        AND NOT IS_SYMLINK "${owner_marker}"
    )
        file(READ "${owner_marker}" observed_owner LIMIT 512)
        string(
            REGEX MATCH
            "^version=2\nbuild-tree-sha256=([0-9a-f]+)\ntransaction-sha256=([0-9a-f]+)\n$"
            valid_transaction_owner
            "${observed_owner}"
        )
        set(observed_build_hash "${CMAKE_MATCH_1}")
        set(observed_transaction_id "${CMAKE_MATCH_2}")
        string(LENGTH "${observed_build_hash}" observed_build_hash_length)
        if(
            valid_transaction_owner STREQUAL observed_owner
            AND observed_build_hash_length EQUAL 64
            AND observed_transaction_id STREQUAL transaction_id
        )
            _protocyte_owner_record_status(
                rechecked_owner_status
                rechecked_transaction_id
                "${owner_marker}"
                "${observed_build_hash}"
                "${root_owner_marker}"
            )
            if(
                rechecked_owner_status STREQUAL "incomplete"
                AND rechecked_transaction_id STREQUAL transaction_id
            )
                file(REMOVE "${owner_marker}")
                if(NOT EXISTS "${owner_marker}" AND NOT IS_SYMLINK "${owner_marker}")
                    set(recovered TRUE)
                endif()
            endif()
        endif()
    endif()
    set(${out_recovered} "${recovered}" PARENT_SCOPE)
endfunction()

function(_protocyte_path_has_linked_existing_component out_var input_path)
    set(${out_var} FALSE PARENT_SCOPE)
    if(NOT IS_ABSOLUTE "${input_path}")
        return()
    endif()

    cmake_path(NORMAL_PATH input_path OUTPUT_VARIABLE current_component)
    while(NOT current_component STREQUAL "")
        # CMake 3.24 does not resolve Windows junctions through REAL_PATH, but
        # IS_SYMLINK identifies both junctions and symbolic links. Inspect each
        # component explicitly before canonicalizing any existing prefix.
        if(IS_SYMLINK "${current_component}")
            set(${out_var} TRUE PARENT_SCOPE)
            return()
        endif()
        cmake_path(GET current_component PARENT_PATH parent_component)
        if(parent_component STREQUAL current_component)
            return()
        endif()
        set(current_component "${parent_component}")
    endwhile()
endfunction()

function(
    _protocyte_project_path_through_existing_components
    out_path
    out_valid
    input_path
    leaf_may_be_file
)
    set(${out_path} "" PARENT_SCOPE)
    set(${out_valid} FALSE PARENT_SCOPE)
    if(NOT IS_ABSOLUTE "${input_path}")
        return()
    endif()

    _protocyte_path_has_linked_existing_component(path_has_link "${input_path}")
    if(path_has_link)
        return()
    endif()

    cmake_path(NORMAL_PATH input_path OUTPUT_VARIABLE normalized_path)
    set(existing_component "${normalized_path}")
    while(NOT EXISTS "${existing_component}" AND NOT IS_SYMLINK "${existing_component}")
        cmake_path(GET existing_component PARENT_PATH parent_component)
        if(parent_component STREQUAL existing_component OR parent_component STREQUAL "")
            return()
        endif()
        set(existing_component "${parent_component}")
    endwhile()

    # A dangling link cannot be canonicalized safely. Existing ancestors must
    # be directories; only the requested leaf may be a regular file.
    if(NOT EXISTS "${existing_component}")
        return()
    endif()
    if(
        NOT IS_DIRECTORY "${existing_component}"
        AND (NOT leaf_may_be_file OR NOT existing_component STREQUAL normalized_path)
    )
        return()
    endif()

    # Linked components were rejected explicitly above for compatibility with
    # the CMake 3.24 floor. Append only the suffix that does not exist yet so
    # fresh generated directories remain valid without trusting lexical paths.
    file(REAL_PATH "${existing_component}" canonical_existing_component)
    if(canonical_existing_component STREQUAL "")
        return()
    endif()
    file(
        RELATIVE_PATH
        missing_suffix
        "${existing_component}"
        "${normalized_path}"
    )
    if(NOT missing_suffix STREQUAL "")
        cmake_path(
            APPEND canonical_existing_component
            "${missing_suffix}"
            OUTPUT_VARIABLE projected_path
        )
    else()
        set(projected_path "${canonical_existing_component}")
    endif()
    cmake_path(NORMAL_PATH projected_path)
    set(${out_path} "${projected_path}" PARENT_SCOPE)
    set(${out_valid} TRUE PARENT_SCOPE)
endfunction()

function(_protocyte_generated_output_root_is_safe out_var output_root)
    set(${out_var} FALSE PARENT_SCOPE)
    _protocyte_project_path_through_existing_components(
        projected_output_root
        output_root_is_projectable
        "${output_root}"
        FALSE
    )
    if(NOT output_root_is_projectable)
        return()
    endif()

    _protocyte_normalized_path_identity(expected_root_identity "${output_root}")
    _protocyte_normalized_path_identity(projected_root_identity "${projected_output_root}")
    if(expected_root_identity STREQUAL projected_root_identity)
        set(${out_var} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_generated_output_path_is_lexically_owned out_var output_path output_root)
    set(${out_var} FALSE PARENT_SCOPE)
    if(NOT IS_ABSOLUTE "${output_path}" OR NOT IS_ABSOLUTE "${output_root}")
        return()
    endif()

    cmake_path(NORMAL_PATH output_path OUTPUT_VARIABLE normalized_output_path)
    cmake_path(NORMAL_PATH output_root OUTPUT_VARIABLE normalized_output_root)
    if(NOT normalized_output_path MATCHES "([.]protocyte[.](hpp|cpp)|/runtime[.]hpp)$")
        return()
    endif()
    cmake_path(
        IS_PREFIX normalized_output_root
        "${normalized_output_path}"
        NORMALIZE
        output_is_lexically_under_root
    )
    if(NOT output_is_lexically_under_root)
        return()
    endif()
    set(${out_var} TRUE PARENT_SCOPE)
endfunction()

function(_protocyte_generated_output_path_is_canonically_safe out_var output_path output_root)
    set(${out_var} FALSE PARENT_SCOPE)
    _protocyte_generated_output_path_is_lexically_owned(
        output_is_lexically_owned
        "${output_path}"
        "${output_root}"
    )
    if(NOT output_is_lexically_owned)
        return()
    endif()

    cmake_path(NORMAL_PATH output_path OUTPUT_VARIABLE normalized_output_path)
    cmake_path(NORMAL_PATH output_root OUTPUT_VARIABLE normalized_output_root)

    _protocyte_generated_output_root_is_safe(
        output_root_is_safe
        "${normalized_output_root}"
    )
    if(NOT output_root_is_safe)
        return()
    endif()
    _protocyte_project_path_through_existing_components(
        projected_output_path
        output_path_is_projectable
        "${normalized_output_path}"
        TRUE
    )
    if(NOT output_path_is_projectable)
        return()
    endif()

    _protocyte_normalized_path_identity(
        projected_root_identity
        "${normalized_output_root}"
    )
    _protocyte_normalized_path_identity(
        expected_output_identity
        "${normalized_output_path}"
    )
    _protocyte_normalized_path_identity(
        projected_output_identity
        "${projected_output_path}"
    )
    cmake_path(
        IS_PREFIX projected_root_identity
        "${projected_output_identity}"
        NORMALIZE
        output_is_canonically_under_root
    )
    if(
        output_is_canonically_under_root
        AND projected_output_identity STREQUAL expected_output_identity
    )
        set(${out_var} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_generated_output_path_is_safe out_var output_path output_root)
    _protocyte_generated_output_path_is_canonically_safe(
        output_path_is_safe
        "${output_path}"
        "${output_root}"
    )
    set(${out_var} "${output_path_is_safe}" PARENT_SCOPE)
endfunction()
