include_guard(GLOBAL)

include(CMakeParseArguments)
include(FetchContent)
include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteOutputSafety.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteProcess.cmake")
_protocyte_configure_tool_timeout()
set_property(
    GLOBAL
    PROPERTY PROTOCYTE_INTERNAL_MANAGED_ENVIRONMENT_HELPER
    "${CMAKE_CURRENT_LIST_DIR}/ProtocyteManagedEnvironment.py"
)

function(_protocyte_configure_python_environment_root)
    if(NOT DEFINED PROTOCYTE_PYTHON_ENV_ROOT OR "${PROTOCYTE_PYTHON_ENV_ROOT}" STREQUAL "")
        message(FATAL_ERROR "PROTOCYTE_PYTHON_ENV_ROOT must name a non-empty filesystem path")
    endif()

    set(canonical_root "${PROTOCYTE_PYTHON_ENV_ROOT}")
    cmake_path(
        ABSOLUTE_PATH canonical_root
        BASE_DIRECTORY "${CMAKE_BINARY_DIR}"
        NORMALIZE
        OUTPUT_VARIABLE canonical_root
    )
    string(FIND "${canonical_root}" ";" semicolon_index)
    if(NOT semicolon_index EQUAL -1)
        message(
            FATAL_ERROR
            "PROTOCYTE_PYTHON_ENV_ROOT must not contain ';' because CMake list expansion cannot "
            "preserve semicolons safely during Python environment provisioning. Choose an environment "
            "root without semicolons."
        )
    endif()

    set(
        PROTOCYTE_PYTHON_ENV_ROOT
        "${canonical_root}"
        CACHE PATH
        "Directory for Protocyte-managed Python virtual environments."
        FORCE
    )
    set(PROTOCYTE_PYTHON_ENV_ROOT "${canonical_root}" PARENT_SCOPE)
    set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PYTHON_ENV_ROOT "${canonical_root}")
endfunction()

function(_protocyte_encode_generator_parameter out_var value)
    if("${value}" STREQUAL "")
        set(${out_var} "" PARENT_SCOPE)
        return()
    endif()

    string(HEX "${value}" encoded)
    set(${out_var} "_protocyte_options_hex=${encoded}" PARENT_SCOPE)
endfunction()

function(_protocyte_append_protoc_response_argument out_var argument)
    string(FIND "${argument}" "\r" carriage_return_index)
    string(FIND "${argument}" "\n" line_feed_index)
    if(NOT carriage_return_index EQUAL -1 OR NOT line_feed_index EQUAL -1)
        message(
            FATAL_ERROR
            "Protocyte CMake generation cannot pass descriptor names or paths containing carriage returns or "
            "line feeds: protoc response files define one literal argument per line and provide no newline escaping"
        )
    endif()

    set(response_content "${${out_var}}")
    string(APPEND response_content "${argument}\n")
    set(${out_var} "${response_content}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_write_protoc_response_file
    out_absolute_path
    out_relative_path
    identity
    content
)
    string(SHA256 response_key "${identity}")
    set(response_relative_path "CMakeFiles/protocyte-arguments/${response_key}.rsp")
    set(response_absolute_path "${CMAKE_CURRENT_BINARY_DIR}/${response_relative_path}")
    cmake_path(GET response_absolute_path PARENT_PATH response_directory)
    file(MAKE_DIRECTORY "${response_directory}")

    set(write_response TRUE)
    if(EXISTS "${response_absolute_path}")
        file(READ "${response_absolute_path}" existing_content)
        if(existing_content STREQUAL content)
            set(write_response FALSE)
        endif()
    endif()
    if(write_response)
        file(WRITE "${response_absolute_path}" "${content}")
    endif()

    set(${out_absolute_path} "${response_absolute_path}" PARENT_SCOPE)
    set(${out_relative_path} "${response_relative_path}" PARENT_SCOPE)
endfunction()

function(_protocyte_output_lock_key out_var output_path)
    set(output_identity "${output_path}")
    cmake_path(NORMAL_PATH output_identity)
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${output_identity}" output_identity)
    endif()
    string(SHA256 output_lock_key "${output_identity}")
    set(${out_var} "${output_lock_key}" PARENT_SCOPE)
endfunction()

function(_protocyte_canonical_output_lock_directory out_var candidate)
    _protocyte_path_has_linked_existing_component(
        lock_directory_has_linked_component
        "${candidate}"
    )
    if(lock_directory_has_linked_component)
        message(
            FATAL_ERROR
            "PROTOCYTE_OUTPUT_LOCK_ROOT must not contain symbolic-link or junction components because "
            "every build tree must use the same physical output-lock namespace: ${candidate}"
        )
    endif()

    _protocyte_project_path_through_existing_components(
        canonical_lock_directory
        lock_directory_is_projectable
        "${candidate}"
        FALSE
    )
    if(NOT lock_directory_is_projectable)
        message(
            FATAL_ERROR
            "Protocyte could not canonicalize the output-lock directory safely: ${candidate}"
        )
    endif()
    set(${out_var} "${canonical_lock_directory}" PARENT_SCOPE)
endfunction()

function(_protocyte_pin_output_lock_namespace output_lock_directory)
    _protocyte_normalized_path_identity(
        output_lock_identity
        "${output_lock_directory}"
    )
    get_property(
        output_lock_namespace_is_pinned
        GLOBAL
        PROPERTY PROTOCYTE_INTERNAL_OUTPUT_LOCK_DIRECTORY
        SET
    )
    if(output_lock_namespace_is_pinned)
        get_property(
            pinned_output_lock_directory
            GLOBAL
            PROPERTY PROTOCYTE_INTERNAL_OUTPUT_LOCK_DIRECTORY
        )
        _protocyte_normalized_path_identity(
            pinned_output_lock_identity
            "${pinned_output_lock_directory}"
        )
        if(NOT output_lock_identity STREQUAL pinned_output_lock_identity)
            message(
                FATAL_ERROR
                "Every Protocyte target in one CMake configure graph must use the same canonical output-lock "
                "namespace. The graph already uses '${pinned_output_lock_directory}', but another target "
                "selected '${output_lock_directory}'. Set PROTOCYTE_OUTPUT_LOCK_ROOT once before adding "
                "Protocyte targets and reconfigure."
            )
        endif()
        return()
    endif()
    set_property(
        GLOBAL
        PROPERTY PROTOCYTE_INTERNAL_OUTPUT_LOCK_DIRECTORY "${output_lock_directory}"
    )
endfunction()

function(_protocyte_shared_output_lock_directory out_var)
    if(
        DEFINED PROTOCYTE_OUTPUT_LOCK_ROOT
        AND NOT "${PROTOCYTE_OUTPUT_LOCK_ROOT}" STREQUAL ""
    )
        if("${PROTOCYTE_OUTPUT_LOCK_ROOT}" MATCHES "\\$<")
            message(
                FATAL_ERROR
                "PROTOCYTE_OUTPUT_LOCK_ROOT must be a configure-time absolute path, not a generator expression"
            )
        endif()
        if(NOT IS_ABSOLUTE "${PROTOCYTE_OUTPUT_LOCK_ROOT}")
            message(
                FATAL_ERROR
                "PROTOCYTE_OUTPUT_LOCK_ROOT must be absolute so all build processes use a stable lock namespace: "
                "${PROTOCYTE_OUTPUT_LOCK_ROOT}"
            )
        endif()
        _protocyte_canonical_output_lock_directory(
            output_lock_directory
            "${PROTOCYTE_OUTPUT_LOCK_ROOT}"
        )
        _protocyte_pin_output_lock_namespace("${output_lock_directory}")
        set(${out_var} "${output_lock_directory}" PARENT_SCOPE)
        return()
    endif()

    set(output_lock_base "")
    if(CMAKE_HOST_WIN32)
        foreach(environment_name IN ITEMS LOCALAPPDATA TEMP TMP)
            if(
                "${output_lock_base}" STREQUAL ""
                AND NOT "$ENV{${environment_name}}" STREQUAL ""
                AND IS_ABSOLUTE "$ENV{${environment_name}}"
            )
                set(output_lock_base "$ENV{${environment_name}}")
            endif()
        endforeach()
    else()
        if(
            NOT "$ENV{XDG_CACHE_HOME}" STREQUAL ""
            AND IS_ABSOLUTE "$ENV{XDG_CACHE_HOME}"
        )
            set(output_lock_base "$ENV{XDG_CACHE_HOME}")
        elseif(NOT "$ENV{HOME}" STREQUAL "" AND IS_ABSOLUTE "$ENV{HOME}")
            set(output_lock_base "$ENV{HOME}/.cache")
        endif()
    endif()

    if("${output_lock_base}" STREQUAL "")
        message(
            FATAL_ERROR
            "Protocyte could not choose a user-scoped output lock directory. "
            "Set PROTOCYTE_OUTPUT_LOCK_ROOT to an absolute writable directory shared by build trees "
            "that generate the same outputs."
        )
    endif()
    set(output_lock_directory "${output_lock_base}/protocyte/output-locks-v1")
    _protocyte_canonical_output_lock_directory(
        output_lock_directory
        "${output_lock_directory}"
    )
    _protocyte_pin_output_lock_namespace("${output_lock_directory}")
    set(${out_var} "${output_lock_directory}" PARENT_SCOPE)
endfunction()

function(_protocyte_canonical_output_directory out_var output_directory)
    cmake_path(NORMAL_PATH output_directory OUTPUT_VARIABLE normalized_output_directory)
    if(EXISTS "${normalized_output_directory}" OR IS_SYMLINK "${normalized_output_directory}")
        if(NOT IS_DIRECTORY "${normalized_output_directory}")
            message(
                FATAL_ERROR
                "protocyte_generate OUT_DIR must be a directory when it already exists: ${output_directory}"
            )
        endif()
        file(REAL_PATH "${normalized_output_directory}" canonical_output_directory)
        set(${out_var} "${canonical_output_directory}" PARENT_SCOPE)
        return()
    endif()

    set(existing_ancestor "${normalized_output_directory}")
    while(NOT EXISTS "${existing_ancestor}" AND NOT IS_SYMLINK "${existing_ancestor}")
        cmake_path(GET existing_ancestor PARENT_PATH parent_ancestor)
        if(parent_ancestor STREQUAL existing_ancestor OR parent_ancestor STREQUAL "")
            message(
                FATAL_ERROR
                "Protocyte could not find an existing ancestor for OUT_DIR '${output_directory}'"
            )
        endif()
        set(existing_ancestor "${parent_ancestor}")
    endwhile()
    if(NOT IS_DIRECTORY "${existing_ancestor}")
        message(
            FATAL_ERROR
            "Protocyte cannot create OUT_DIR '${output_directory}' because ancestor "
            "'${existing_ancestor}' is not a directory"
        )
    endif()
    file(REAL_PATH "${existing_ancestor}" canonical_ancestor)
    file(
        RELATIVE_PATH
        missing_suffix
        "${existing_ancestor}"
        "${normalized_output_directory}"
    )
    cmake_path(
        APPEND canonical_ancestor
        "${missing_suffix}"
        OUTPUT_VARIABLE canonical_output_directory
    )
    cmake_path(NORMAL_PATH canonical_output_directory)
    set(${out_var} "${canonical_output_directory}" PARENT_SCOPE)
endfunction()

function(_protocyte_output_directory_owner_paths out_marker out_lock output_directory)
    _protocyte_canonical_output_directory(
        canonical_output_directory
        "${output_directory}"
    )
    set(output_identity "${canonical_output_directory}")
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${output_identity}" output_identity)
    endif()
    string(SHA256 output_key "${output_identity}")
    cmake_path(GET canonical_output_directory PARENT_PATH output_parent)
    set(owner_prefix "${output_parent}/.protocyte-out-dir-${output_key}")
    set(${out_marker} "${owner_prefix}.owner" PARENT_SCOPE)
    set(${out_lock} "${owner_prefix}.lock" PARENT_SCOPE)
endfunction()

function(_protocyte_build_tree_owner_hash out_var)
    file(REAL_PATH "${CMAKE_BINARY_DIR}" canonical_binary_directory)
    set(build_tree_identity "${canonical_binary_directory}")
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${build_tree_identity}" build_tree_identity)
    endif()
    string(SHA256 build_tree_hash "${build_tree_identity}")
    set(${out_var} "${build_tree_hash}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_preflight_output_ownership
    out_marker
    out_lock
    out_build_tree_hash
    out_lock_directory
    output_directory
    outputs_var
)
    _protocyte_output_directory_owner_paths(
        owner_marker
        owner_lock
        "${output_directory}"
    )
    _protocyte_build_tree_owner_hash(build_tree_hash)
    _protocyte_shared_output_lock_directory(output_lock_directory)

    set(output_keys)
    foreach(command_output IN LISTS ${outputs_var})
        _protocyte_output_lock_key(output_key "${command_output}")
        list(APPEND output_keys "${output_key}")
        set("protocyte_claim_output_${output_key}" "${command_output}")
    endforeach()
    list(REMOVE_DUPLICATES output_keys)
    list(SORT output_keys)
    file(MAKE_DIRECTORY "${output_lock_directory}")
    set(conflicting_owner_markers)
    foreach(output_key IN LISTS output_keys)
        file(
            LOCK "${output_lock_directory}/${output_key}.lock"
            GUARD FUNCTION
            TIMEOUT 600
            RESULT_VARIABLE output_lock_result
        )
        if(NOT "${output_lock_result}" STREQUAL "0")
            message(
                FATAL_ERROR
                "Protocyte could not lock generated output '${protocyte_claim_output_${output_key}}' "
                "while checking ownership: ${output_lock_result}"
            )
        endif()
    endforeach()
    cmake_path(GET owner_lock PARENT_PATH owner_lock_parent)
    file(MAKE_DIRECTORY "${owner_lock_parent}")
    file(
        LOCK "${owner_lock}"
        GUARD FUNCTION
        TIMEOUT 600
        RESULT_VARIABLE owner_lock_result
    )
    if(NOT "${owner_lock_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Protocyte could not lock OUT_DIR '${output_directory}' while checking ownership: "
            "${owner_lock_result}"
        )
    endif()

    foreach(output_key IN LISTS output_keys)
        set(output_owner_marker "${output_lock_directory}/${output_key}.owner")
        _protocyte_owner_record_status(
            output_owner_status
            output_owner_transaction_id
            "${output_owner_marker}"
            "${build_tree_hash}"
            "${owner_marker}"
        )
        if(output_owner_status STREQUAL "incomplete")
            _protocyte_recover_incomplete_owner_record(
                recovered_incomplete_owner
                "${output_owner_marker}"
                "${output_owner_transaction_id}"
                "${owner_marker}"
            )
            if(recovered_incomplete_owner)
                set(output_owner_status "missing")
            else()
                _protocyte_owner_record_status(
                    output_owner_status
                    unused_output_transaction_id
                    "${output_owner_marker}"
                    "${build_tree_hash}"
                    "${owner_marker}"
                )
            endif()
        endif()
        if(output_owner_status STREQUAL "different")
            list(APPEND conflicting_owner_markers "${output_owner_marker}")
        elseif(output_owner_status STREQUAL "malformed")
            message(
                FATAL_ERROR
                "Protocyte cannot generate '${protocyte_claim_output_${output_key}}' because ownership record "
                "'${output_owner_marker}' is malformed. Protocyte will not reclaim it automatically. "
                "After confirming no build uses the output, remove the record manually and reconfigure."
            )
        elseif(output_owner_status STREQUAL "incomplete")
            message(
                FATAL_ERROR
                "Protocyte cannot generate '${protocyte_claim_output_${output_key}}' because an incomplete "
                "ownership transaction could not be recovered safely. No generated output was changed."
            )
        elseif(output_owner_status STREQUAL "unverifiable")
            _protocyte_owner_transaction_paths(
                unused_output_prepared_witness
                output_committed_witness
                "${owner_marker}"
                "${output_owner_transaction_id}"
            )
            message(
                FATAL_ERROR
                "Protocyte cannot generate '${protocyte_claim_output_${output_key}}' because ownership record "
                "'${output_owner_marker}' references missing or unverifiable transaction witness "
                "'${output_committed_witness}'. Protocyte will not reclaim the output automatically. Choose "
                "disjoint generated outputs, restore the witness, or, after confirming no build uses the output, "
                "remove '${output_owner_marker}' manually and reconfigure."
            )
        endif()
    endforeach()

    _protocyte_owner_record_status(
        root_owner_status
        root_owner_transaction_id
        "${owner_marker}"
        "${build_tree_hash}"
        "${owner_marker}"
    )
    if(root_owner_status STREQUAL "incomplete")
        _protocyte_recover_incomplete_owner_record(
            recovered_incomplete_root_owner
            "${owner_marker}"
            "${root_owner_transaction_id}"
            "${owner_marker}"
        )
        if(recovered_incomplete_root_owner)
            set(root_owner_status "missing")
        else()
            _protocyte_owner_record_status(
                root_owner_status
                unused_root_transaction_id
                "${owner_marker}"
                "${build_tree_hash}"
                "${owner_marker}"
            )
        endif()
    endif()
    if(root_owner_status STREQUAL "different")
        list(APPEND conflicting_owner_markers "${owner_marker}")
    elseif(root_owner_status STREQUAL "malformed")
        message(
            FATAL_ERROR
            "Protocyte cannot use OUT_DIR '${output_directory}' because its ownership record '${owner_marker}' "
            "is malformed. Protocyte will not reclaim it automatically. After confirming that no build is using "
            "this OUT_DIR, remove the ownership record manually and reconfigure."
        )
    elseif(root_owner_status STREQUAL "incomplete")
        message(
            FATAL_ERROR
            "Protocyte cannot use OUT_DIR '${output_directory}' because an incomplete ownership transaction "
            "could not be recovered safely. No generated output was changed."
        )
    elseif(root_owner_status STREQUAL "unverifiable")
        _protocyte_owner_transaction_paths(
            unused_root_prepared_witness
            root_committed_witness
            "${owner_marker}"
            "${root_owner_transaction_id}"
        )
        message(
            FATAL_ERROR
            "Protocyte cannot use OUT_DIR '${output_directory}' because ownership record '${owner_marker}' "
            "references missing or unverifiable transaction witness '${root_committed_witness}'. Protocyte will "
            "not reclaim the directory automatically. Reuse the owning build tree, choose a different OUT_DIR, "
            "restore the witness, or, after confirming no build uses the OUT_DIR, remove '${owner_marker}' "
            "manually and reconfigure."
        )
    endif()

    if(conflicting_owner_markers)
        list(REMOVE_DUPLICATES conflicting_owner_markers)
        list(SORT conflicting_owner_markers)
        string(
            REPLACE ";" "\n  "
            conflicting_owner_marker_locations
            "${conflicting_owner_markers}"
        )
        message(
            FATAL_ERROR
            "Protocyte cannot use OUT_DIR '${output_directory}' because it is owned by a different or deleted "
            "CMake build tree. The exact conflicting owner records are:\n  "
            "${conflicting_owner_marker_locations}\n"
            "To transfer this OUT_DIR and its declared generated outputs, first stop every build that could use "
            "them and preserve any files you need. Then remove exactly the owner records listed above manually and "
            "reconfigure. Do not delete the whole output-lock namespace or cache. No generated output was changed."
        )
    endif()

    set(${out_marker} "${owner_marker}" PARENT_SCOPE)
    set(${out_lock} "${owner_lock}" PARENT_SCOPE)
    set(${out_build_tree_hash} "${build_tree_hash}" PARENT_SCOPE)
    set(${out_lock_directory} "${output_lock_directory}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_protoc_import_root_alias_status
    out_status
    out_target
    alias_path
    expected_target
)
    set(alias_status "missing")
    set(alias_target "")
    if(IS_SYMLINK "${alias_path}")
        file(REAL_PATH "${alias_path}" alias_target)
        file(REAL_PATH "${expected_target}" canonical_expected_target)
        cmake_path(NORMAL_PATH alias_target)
        cmake_path(NORMAL_PATH canonical_expected_target)
        set(alias_target_identity "${alias_target}")
        set(expected_target_identity "${canonical_expected_target}")
        if(CMAKE_HOST_WIN32)
            string(TOLOWER "${alias_target_identity}" alias_target_identity)
            string(TOLOWER "${expected_target_identity}" expected_target_identity)
        endif()
        if(
            IS_DIRECTORY "${alias_path}"
            AND alias_target_identity STREQUAL expected_target_identity
        )
            set(alias_status "valid")
        else()
            set(alias_status "wrong-target")
        endif()
    elseif(EXISTS "${alias_path}")
        set(alias_status "wrong-type")
    endif()

    set(${out_status} "${alias_status}" PARENT_SCOPE)
    set(${out_target} "${alias_target}" PARENT_SCOPE)
endfunction()

function(_protocyte_protoc_safe_import_root out_var import_root)
    set(protoc_import_root "${import_root}")
    if(CMAKE_HOST_WIN32)
        # Windows protoc treats ';' as an unescapable --proto_path list
        # separator. Prefer a directory symlink and fall back to an unprivileged
        # junction so protoc sees an equivalent semicolon-free root.
        string(FIND "${import_root}" ";" semicolon_index)
        if(NOT semicolon_index EQUAL -1)
            cmake_path(NORMAL_PATH import_root OUTPUT_VARIABLE normalized_import_root)
            string(SHA256 import_root_key "${normalized_import_root}")
            set(proxy_property "PROTOCYTE_INTERNAL_PROTOC_IMPORT_ROOT_${import_root_key}")
            set(
                protoc_import_root
                "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-protoc-import-roots/${import_root_key}"
            )
            get_property(proxy_is_registered GLOBAL PROPERTY "${proxy_property}" SET)
            if(proxy_is_registered)
                get_property(registered_protoc_import_root GLOBAL PROPERTY "${proxy_property}")
                if(NOT registered_protoc_import_root STREQUAL protoc_import_root)
                    message(FATAL_ERROR "Protocyte protoc-safe import-root alias identity collision")
                endif()
            endif()

            cmake_path(GET protoc_import_root PARENT_PATH proxy_parent)
            file(MAKE_DIRECTORY "${proxy_parent}")
            file(
                LOCK "${proxy_parent}/${import_root_key}.lock"
                GUARD FUNCTION
                TIMEOUT 600
                RESULT_VARIABLE proxy_lock_result
            )
            if(NOT "${proxy_lock_result}" STREQUAL "0")
                message(
                    FATAL_ERROR
                    "Protocyte could not lock protoc-safe alias '${protoc_import_root}': "
                    "${proxy_lock_result}"
                )
            endif()

            _protocyte_protoc_import_root_alias_status(
                alias_status
                alias_target
                "${protoc_import_root}"
                "${normalized_import_root}"
            )
            if(alias_status STREQUAL "valid")
                set_property(
                    GLOBAL
                    PROPERTY "${proxy_property}"
                    "${protoc_import_root}"
                )
                set(${out_var} "${protoc_import_root}" PARENT_SCOPE)
                return()
            elseif(NOT alias_status STREQUAL "missing")
                message(
                    FATAL_ERROR
                    "Protocyte refuses to reuse protoc-safe alias '${protoc_import_root}' for import root "
                    "'${normalized_import_root}': the existing entry is not a directory symbolic link or "
                    "junction with that canonical target (status: ${alias_status}, target: '${alias_target}'). "
                    "Protocyte did not modify the existing entry."
                )
            endif()

            file(
                CREATE_LINK
                "${normalized_import_root}"
                "${protoc_import_root}"
                SYMBOLIC
                RESULT symbolic_link_result
            )
            _protocyte_protoc_import_root_alias_status(
                alias_status
                alias_target
                "${protoc_import_root}"
                "${normalized_import_root}"
            )
            if(NOT alias_status STREQUAL "valid" AND NOT alias_status STREQUAL "missing")
                message(
                    FATAL_ERROR
                    "Protocyte refuses protoc-safe alias '${protoc_import_root}' for import root "
                    "'${normalized_import_root}' after symbolic-link creation: the entry is not a directory "
                    "symbolic link or junction with that canonical target (status: ${alias_status}, target: "
                    "'${alias_target}'). Protocyte did not modify the entry."
                )
            endif()

            if(alias_status STREQUAL "missing")
                cmake_path(
                    NATIVE_PATH normalized_import_root
                    NORMALIZE native_import_root
                )
                cmake_path(
                    NATIVE_PATH protoc_import_root
                    NORMALIZE native_protoc_import_root
                )
                string(REPLACE "'" "''" native_protoc_import_root "${native_protoc_import_root}")
                string(REPLACE "'" "''" native_import_root "${native_import_root}")
                string(
                    CONCAT
                    junction_command
                    "[void](New-Item -ItemType Junction "
                    "-Path '${native_protoc_import_root}' "
                    "-Target '${native_import_root}')"
                )
                execute_process(
                    COMMAND
                        powershell.exe
                        -NoLogo
                        -NoProfile
                        -NonInteractive
                        -Command
                        "${junction_command}"
                    RESULT_VARIABLE junction_result
                    OUTPUT_VARIABLE junction_output
                    ERROR_VARIABLE junction_error
                )
                _protocyte_protoc_import_root_alias_status(
                    alias_status
                    alias_target
                    "${protoc_import_root}"
                    "${normalized_import_root}"
                )
            else()
                set(junction_result "not attempted")
                set(junction_output "")
                set(junction_error "")
            endif()

            if(NOT alias_status STREQUAL "valid")
                string(STRIP "${junction_output}" junction_output)
                string(STRIP "${junction_error}" junction_error)
                message(
                    FATAL_ERROR
                    "Protocyte could not create a verified protoc-safe alias for import root "
                    "'${normalized_import_root}'. Symbolic-link creation failed with "
                    "'${symbolic_link_result}', and junction creation returned "
                    "'${junction_result}': ${junction_output} ${junction_error}. Final alias status: "
                    "${alias_status}, target: '${alias_target}'. Protocyte did not remove the entry."
                )
            endif()

            set_property(
                GLOBAL
                PROPERTY "${proxy_property}"
                "${protoc_import_root}"
            )
        endif()
    endif()
    set(${out_var} "${protoc_import_root}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_write_lock_manifest_file
    out_absolute_path
    identity
    lock_keys_var
)
    string(SHA256 manifest_key "${identity}")
    set(manifest_path "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/protocyte-locks/${manifest_key}.list")
    cmake_path(GET manifest_path PARENT_PATH manifest_directory)
    file(MAKE_DIRECTORY "${manifest_directory}")

    set(manifest_content "")
    foreach(lock_key IN LISTS ${lock_keys_var})
        string(APPEND manifest_content "${lock_key}\n")
    endforeach()

    set(write_manifest TRUE)
    if(EXISTS "${manifest_path}")
        file(READ "${manifest_path}" existing_content)
        if(existing_content STREQUAL manifest_content)
            set(write_manifest FALSE)
        endif()
    endif()
    if(write_manifest)
        file(WRITE "${manifest_path}" "${manifest_content}")
    endif()

    set(${out_absolute_path} "${manifest_path}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_get_source_dependency_proxy
    out_proxy_path
    out_check_target
    source_path
)
    cmake_path(NORMAL_PATH source_path OUTPUT_VARIABLE normalized_source_path)
    cmake_path(
        NORMAL_PATH CMAKE_BINARY_DIR
        OUTPUT_VARIABLE normalized_binary_directory
    )
    set(proxy_identity "${normalized_binary_directory}|${normalized_source_path}")
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${proxy_identity}" proxy_identity)
    endif()
    string(SHA256 proxy_key "${proxy_identity}")

    set(
        proxy_root
        "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-source-dependencies"
    )
    set(proxy_path "${proxy_root}/${proxy_key}.proto")
    set(source_argument_file "${proxy_root}/${proxy_key}.path")
    set(proxy_lock_file "${proxy_root}/${proxy_key}.lock")
    set(check_target "protocyte_source_check_${proxy_key}")

    get_property(
        proxy_is_registered
        GLOBAL PROPERTY "PROTOCYTE_INTERNAL_SOURCE_PROXY_${proxy_key}"
        SET
    )
    if(proxy_is_registered)
        get_property(
            registered_source
            GLOBAL PROPERTY "PROTOCYTE_INTERNAL_SOURCE_PROXY_SOURCE_${proxy_key}"
        )
        get_property(
            registered_proxy
            GLOBAL PROPERTY "PROTOCYTE_INTERNAL_SOURCE_PROXY_PATH_${proxy_key}"
        )
        set(registered_source_identity "${registered_source}")
        set(normalized_source_identity "${normalized_source_path}")
        if(CMAKE_HOST_WIN32)
            string(TOLOWER "${registered_source_identity}" registered_source_identity)
            string(TOLOWER "${normalized_source_identity}" normalized_source_identity)
        endif()
        if(
            NOT "${registered_source_identity}" STREQUAL "${normalized_source_identity}"
            OR NOT "${registered_proxy}" STREQUAL "${proxy_path}"
            OR NOT TARGET "${check_target}"
        )
            message(FATAL_ERROR "Protocyte source dependency proxy identity collision")
        endif()
    else()
        file(MAKE_DIRECTORY "${proxy_root}")
        file(
            LOCK "${proxy_lock_file}"
            GUARD FUNCTION
            TIMEOUT 600
            RESULT_VARIABLE proxy_lock_result
        )
        if(NOT "${proxy_lock_result}" STREQUAL "0")
            message(
                FATAL_ERROR
                "Failed to lock Protocyte source dependency proxy '${proxy_path}': ${proxy_lock_result}"
            )
        endif()
        file(COPY_FILE "${normalized_source_path}" "${proxy_path}" ONLY_IF_DIFFERENT)
        set(write_source_argument TRUE)
        if(EXISTS "${source_argument_file}")
            file(READ "${source_argument_file}" existing_source_argument)
            if(existing_source_argument STREQUAL normalized_source_path)
                set(write_source_argument FALSE)
            endif()
        endif()
        if(write_source_argument)
            file(WRITE "${source_argument_file}" "${normalized_source_path}")
        endif()
        file(SHA256 "${proxy_path}" proxy_expected_hash)
        # The aggregate import guard refreshes this proxy before generation.
        # Keep it unowned so IDE and Ninja no-op builds remain timestamp-clean.
        add_custom_target(
            "${check_target}"
            COMMAND
                "${CMAKE_COMMAND}"
                "-DSOURCE_ARGUMENT_FILE=${source_argument_file}"
                "-DPROXY_FILE=${proxy_path}"
                "-DLOCK_FILE=${proxy_lock_file}"
                -P "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteSourceDependency.cmake"
            VERBATIM
        )
        set_property(
            GLOBAL PROPERTY
            "PROTOCYTE_INTERNAL_SOURCE_PROXY_${proxy_key}"
            TRUE
        )
        set_property(
            GLOBAL PROPERTY
            "PROTOCYTE_INTERNAL_SOURCE_PROXY_SOURCE_${proxy_key}"
            "${normalized_source_path}"
        )
        set_property(
            GLOBAL PROPERTY
            "PROTOCYTE_INTERNAL_SOURCE_PROXY_PATH_${proxy_key}"
            "${proxy_path}"
        )
        set_property(
            GLOBAL PROPERTY
            "PROTOCYTE_INTERNAL_SOURCE_PROXY_EXPECTED_HASH_${proxy_key}"
            "${proxy_expected_hash}"
        )
    endif()

    set(${out_proxy_path} "${proxy_path}" PARENT_SCOPE)
    set(${out_check_target} "${check_target}" PARENT_SCOPE)
endfunction()

function(_protocyte_descriptor_name_is_unsafe out_var name)
    if("${name}" MATCHES "^/" OR "${name}" MATCHES "^[A-Za-z]:/" OR "${name}" MATCHES "\\\\")
        set(${out_var} TRUE PARENT_SCOPE)
    else()
        set(${out_var} FALSE PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_validate_descriptor_name name)
    if("${name}" STREQUAL "")
        message(FATAL_ERROR "descriptor file name must not be empty")
    endif()
    if("${name}" MATCHES "^-")
        message(
            FATAL_ERROR
            "descriptor file name must not begin with '-' because protoc interprets it as an option: ${name}"
        )
    endif()
    _protocyte_descriptor_name_is_unsafe(name_is_unsafe "${name}")
    if(name_is_unsafe)
        message(FATAL_ERROR "descriptor file name must be a relative virtual path using '/': ${name}")
    endif()
    if("${name}" MATCHES "(^|/)(\\.|\\.\\.)(/|$)" OR "${name}" MATCHES "(^/|//|/$)")
        message(FATAL_ERROR "descriptor file name contains an unsafe path segment: ${name}")
    endif()
endfunction()

function(_protocyte_validate_virtual_directory_prefix parameter_name value)
    if("${value}" STREQUAL "")
        message(FATAL_ERROR "${parameter_name} must not be empty")
    endif()
    if(IS_ABSOLUTE "${value}" OR "${value}" MATCHES ":" OR "${value}" MATCHES "\\\\")
        message(FATAL_ERROR "${parameter_name} must be a relative virtual directory using '/': ${value}")
    endif()

    string(HEX "${value}" value_hex)
    string(LENGTH "${value_hex}" value_hex_length)
    math(EXPR value_hex_last "${value_hex_length} - 2")
    foreach(offset RANGE 0 ${value_hex_last} 2)
        string(SUBSTRING "${value_hex}" ${offset} 2 byte_hex)
        math(EXPR byte_value "0x${byte_hex}")
        if(byte_value LESS 32 OR byte_value EQUAL 127)
            message(FATAL_ERROR "${parameter_name} must not contain control characters")
        endif()
    endforeach()

    if("${value}" MATCHES "(^|/)(\\.|\\.\\.)(/|$)" OR "${value}" MATCHES "(^/|//|/$)")
        message(FATAL_ERROR "${parameter_name} contains an unsafe or non-normalized path segment: ${value}")
    endif()
    if("${value}" MATCHES "(^|/) | (/|$)")
        message(FATAL_ERROR "${parameter_name} must not have leading or trailing segment whitespace: ${value}")
    endif()

    foreach(invalid_character IN ITEMS "<" ">" "\"" "|" "?" "*")
        string(FIND "${value}" "${invalid_character}" invalid_character_index)
        if(NOT invalid_character_index EQUAL -1)
            message(FATAL_ERROR "${parameter_name} contains characters that are unsafe in generated includes: ${value}")
        endif()
    endforeach()
    string(FIND "${value}" ";" semicolon_index)
    if(NOT semicolon_index EQUAL -1)
        message(FATAL_ERROR "${parameter_name} contains characters that are unsafe in generated includes: ${value}")
    endif()

    string(REPLACE "/" ";" value_segments "${value}")
    foreach(segment IN LISTS value_segments)
        if(segment MATCHES "\\.$")
            message(FATAL_ERROR "${parameter_name} contains a path segment ending in '.': ${value}")
        endif()
        string(REGEX REPLACE "\\..*$" "" device_stem "${segment}")
        string(TOUPPER "${device_stem}" device_stem)
        if(device_stem MATCHES "^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$")
            message(FATAL_ERROR "${parameter_name} contains a Windows-reserved device name: ${value}")
        endif()
    endforeach()
endfunction()

function(_protocyte_source_path_requires_proxy out_var source_path)
    set(requires_proxy FALSE)
    if("${source_path}" MATCHES ";")
        set(requires_proxy TRUE)
    endif()

    string(HEX "${source_path}" encoded_source_path)
    string(LENGTH "${encoded_source_path}" encoded_source_path_length)
    if(encoded_source_path_length GREATER 0)
        math(EXPR encoded_source_path_last "${encoded_source_path_length} - 2")
        foreach(offset RANGE 0 ${encoded_source_path_last} 2)
            string(SUBSTRING "${encoded_source_path}" ${offset} 2 encoded_byte)
            if(encoded_byte MATCHES "^(0[0-9a-f]|1[0-9a-f]|22|5c|7f)$")
                set(requires_proxy TRUE)
                break()
            endif()
        endforeach()
    endif()
    set(${out_var} "${requires_proxy}" PARENT_SCOPE)
endfunction()

function(_protocyte_validate_namespace_prefix function_name value)
    if("${value}" STREQUAL "")
        return()
    endif()

    string(
        REGEX MATCH
        "^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*$"
        normalized_namespace_prefix
        "${value}"
    )
    if(NOT normalized_namespace_prefix STREQUAL value)
        message(
            FATAL_ERROR
            "${function_name} NAMESPACE_PREFIX must be a normalized '::'-separated namespace "
            "of portable, non-reserved C++ identifiers (for example, vendor::wire): '${value}'"
        )
    endif()

    set(
        cpp_keywords
        alignas alignof and and_eq asm atomic_cancel atomic_commit atomic_noexcept auto
        bitand bitor bool break case catch char char8_t char16_t char32_t class compl
        concept const const_cast consteval constexpr constinit continue co_await co_return
        co_yield decltype default delete do double dynamic_cast else enum explicit export
        extern false float for friend goto if inline int long mutable namespace new noexcept
        not not_eq nullptr operator or or_eq private protected public reflexpr register
        reinterpret_cast requires return short signed sizeof static static_assert static_cast
        struct switch synchronized template this thread_local throw true try typedef typeid
        typename union unsigned using virtual void volatile wchar_t while xor xor_eq
    )
    string(REPLACE "::" ";" namespace_components "${value}")
    foreach(namespace_component IN LISTS namespace_components)
        if(namespace_component MATCHES "^_" OR namespace_component MATCHES "__")
            message(
                FATAL_ERROR
                "${function_name} NAMESPACE_PREFIX must be a normalized '::'-separated namespace "
                "of portable, non-reserved C++ identifiers (for example, vendor::wire): '${value}'"
            )
        endif()
        list(FIND cpp_keywords "${namespace_component}" keyword_index)
        if(NOT keyword_index EQUAL -1)
            message(
                FATAL_ERROR
                "${function_name} NAMESPACE_PREFIX must be a normalized '::'-separated namespace "
                "of portable, non-reserved C++ identifiers (for example, vendor::wire): '${value}'"
            )
        endif()
    endforeach()
endfunction()

function(_protocyte_validate_forwarded_generator_options function_name)
    foreach(generator_option IN LISTS ARGN)
        string(REPLACE "," ";" generator_option_parts "${generator_option}")
        foreach(generator_option_part IN LISTS generator_option_parts)
            string(FIND "${generator_option_part}" "=" option_separator)
            if(option_separator EQUAL -1)
                string(STRIP "${generator_option_part}" generator_option_part)
                message(
                    FATAL_ERROR
                    "${function_name} OPTIONS entry '${generator_option_part}' must use key=value"
                )
            endif()
            string(SUBSTRING "${generator_option_part}" 0 ${option_separator} generator_option_name)
            string(STRIP "${generator_option_name}" generator_option_name)
            math(EXPR option_value_start "${option_separator} + 1")
            string(SUBSTRING "${generator_option_part}" ${option_value_start} -1 generator_option_value)

            if(generator_option_name MATCHES "^_protocyte_")
                message(
                    FATAL_ERROR
                    "${function_name} OPTIONS must not use reserved _protocyte_ transport parameters"
                )
            elseif(generator_option_name STREQUAL "runtime" OR generator_option_name STREQUAL "runtime_prefix")
                message(
                    FATAL_ERROR
                    "${function_name} OPTIONS must not set runtime or runtime_prefix; "
                    "use EMIT_RUNTIME and RUNTIME_PREFIX so CMake can declare runtime outputs consistently"
                )
            elseif(generator_option_name STREQUAL "include_prefix")
                message(
                    FATAL_ERROR
                    "${function_name} OPTIONS must not set include_prefix; use INCLUDE_PREFIX so CMake can "
                    "model the generated-header include layout consistently"
                )
            elseif(generator_option_name STREQUAL "namespace_prefix")
                message(
                    FATAL_ERROR
                    "${function_name} OPTIONS must not set namespace_prefix; use NAMESPACE_PREFIX so CMake can "
                    "validate the generated C++ namespace during configuration"
                )
            endif()
        endforeach()
    endforeach()
endfunction()

function(_protocyte_normalize_generated_segment out_var segment max_length)
    string(REGEX REPLACE "\\..*$" "" device_stem "${segment}")
    string(TOUPPER "${device_stem}" device_stem)
    if(device_stem MATCHES "^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$")
        set(escape_first TRUE)
    else()
        set(escape_first FALSE)
    endif()
    if("${segment}" MATCHES "\\.$")
        set(escape_last_dot TRUE)
    else()
        set(escape_last_dot FALSE)
    endif()

    string(HEX "${segment}" segment_hex)
    string(LENGTH "${segment_hex}" segment_hex_length)
    set(normalized "")
    if(segment_hex_length GREATER 0)
        math(EXPR segment_hex_last "${segment_hex_length} - 2")
        foreach(offset RANGE 0 ${segment_hex_last} 2)
            string(SUBSTRING "${segment_hex}" ${offset} 2 byte_hex)
            math(EXPR byte_value "0x${byte_hex}")
            math(EXPR byte_index "${offset} / 2")
            set(byte_is_safe FALSE)
            if(
                (byte_value GREATER_EQUAL 48 AND byte_value LESS_EQUAL 57)
                OR (byte_value GREATER_EQUAL 65 AND byte_value LESS_EQUAL 90)
                OR (byte_value GREATER_EQUAL 97 AND byte_value LESS_EQUAL 122)
                OR byte_value EQUAL 45
                OR byte_value EQUAL 46
                OR byte_value EQUAL 95
            )
                set(byte_is_safe TRUE)
            endif()
            if(byte_index EQUAL 0 AND escape_first)
                set(byte_is_safe FALSE)
            endif()
            if(offset EQUAL segment_hex_last AND escape_last_dot)
                set(byte_is_safe FALSE)
            endif()

            if(byte_is_safe)
                string(SUBSTRING "${segment}" ${byte_index} 1 byte_character)
                string(APPEND normalized "${byte_character}")
            else()
                string(TOUPPER "${byte_hex}" byte_hex)
                string(APPEND normalized "~${byte_hex}")
            endif()
        endforeach()
    endif()

    string(LENGTH "${normalized}" normalized_length)
    if(normalized_length GREATER max_length)
        string(SHA256 segment_digest "${segment}")
        string(TOUPPER "${segment_digest}" segment_digest)
        string(LENGTH "${segment_digest}" digest_length)
        math(EXPR prefix_length "${max_length} - ${digest_length} - 1")
        string(SUBSTRING "${normalized}" 0 ${prefix_length} normalized_prefix)
        set(normalized "${normalized_prefix}~${segment_digest}")
    endif()
    set(${out_var} "${normalized}" PARENT_SCOPE)
endfunction()

function(_protocyte_normalize_generated_path out_var proto_name)
    set(max_component_length 255)
    string(LENGTH ".protocyte.hpp" generated_file_suffix_length)
    math(
        EXPR
        max_final_stem_length
        "${max_component_length} - ${generated_file_suffix_length}"
    )
    string(REGEX REPLACE "\\.proto$" "" remaining "${proto_name}")
    set(normalized "")
    while(TRUE)
        string(FIND "${remaining}" "/" separator)
        if(separator EQUAL -1)
            _protocyte_normalize_generated_segment(
                normalized_segment
                "${remaining}"
                ${max_final_stem_length}
            )
            string(APPEND normalized "${normalized_segment}")
            break()
        endif()
        string(SUBSTRING "${remaining}" 0 ${separator} segment)
        math(EXPR next_segment "${separator} + 1")
        string(SUBSTRING "${remaining}" ${next_segment} -1 remaining)
        _protocyte_normalize_generated_segment(
            normalized_segment
            "${segment}"
            ${max_component_length}
        )
        string(APPEND normalized "${normalized_segment}/")
    endwhile()
    set(generated_base "${normalized}.protocyte")
    set(generated_path_exceeds_budget FALSE)
    if(ARGC GREATER 2 AND NOT "${ARGV2}" STREQUAL "")
        set(max_output_path_length "${ARGV2}")
        string(LENGTH "${generated_base}.hpp" output_path_length)
        if(output_path_length GREATER max_output_path_length)
            set(generated_path_exceeds_budget TRUE)
        endif()
    endif()
    if(ARGC GREATER 3 AND NOT "${ARGV3}" STREQUAL "")
        string(FIND "${normalized}" "/" final_directory_separator REVERSE)
        if(NOT final_directory_separator EQUAL -1)
            string(SUBSTRING "${normalized}" 0 ${final_directory_separator} generated_directory)
            string(LENGTH "${generated_directory}" generated_directory_length)
            if(generated_directory_length GREATER ARGV3)
                set(generated_path_exceeds_budget TRUE)
            endif()
        endif()
    endif()
    if(generated_path_exceeds_budget)
        if(NOT DEFINED max_output_path_length)
            set(max_output_path_length 255)
        elseif(max_output_path_length GREATER 255)
            set(max_output_path_length 255)
        endif()
        string(LENGTH ".protocyte.hpp" generated_file_suffix_length)
        string(SHA256 descriptor_digest "${proto_name}")
        string(TOUPPER "${descriptor_digest}" descriptor_digest)
        string(LENGTH "${descriptor_digest}" digest_length)
        math(
            EXPR
            readable_prefix_length
            "${max_output_path_length} - ${generated_file_suffix_length} - ${digest_length} - 1"
        )
        if(readable_prefix_length LESS 0)
            message(
                FATAL_ERROR
                "internal Protocyte generated-path budget is too small for a collision-resistant name"
            )
        endif()
        string(REPLACE "/" "_" flattened_readable "${normalized}")
        string(SUBSTRING "${flattened_readable}" 0 ${readable_prefix_length} readable_prefix)
        set(generated_base "${readable_prefix}~${descriptor_digest}.protocyte")
    endif()
    set(${out_var} "${generated_base}" PARENT_SCOPE)
endfunction()

function(_protocyte_windows_utf16_length out_var value)
    string(HEX "${value}" value_hex)
    string(LENGTH "${value_hex}" value_hex_length)
    set(offset 0)
    set(utf16_length 0)
    while(offset LESS value_hex_length)
        string(SUBSTRING "${value_hex}" ${offset} 2 byte_hex)
        math(EXPR byte_value "0x${byte_hex}")
        if(byte_value LESS 128)
            set(code_point_bytes 1)
            set(code_point_utf16_length 1)
        elseif(byte_value LESS 224)
            set(code_point_bytes 2)
            set(code_point_utf16_length 1)
        elseif(byte_value LESS 240)
            set(code_point_bytes 3)
            set(code_point_utf16_length 1)
        else()
            set(code_point_bytes 4)
            set(code_point_utf16_length 2)
        endif()
        math(EXPR offset "${offset} + (${code_point_bytes} * 2)")
        math(EXPR utf16_length "${utf16_length} + ${code_point_utf16_length}")
    endwhile()
    set(${out_var} "${utf16_length}" PARENT_SCOPE)
endfunction()

function(_protocyte_generated_path_budget out_path_var out_directory_var out_dir)
    set(generated_path_budget "")
    set(generated_directory_budget "")
    if(CMAKE_GENERATOR MATCHES "^Visual Studio ")
        set(normalized_out_dir "${out_dir}")
        cmake_path(NORMAL_PATH normalized_out_dir)
        _protocyte_windows_utf16_length(out_dir_length "${normalized_out_dir}")
        if(normalized_out_dir MATCHES "[/\\\\]$")
            set(path_separator_length 0)
        else()
            set(path_separator_length 1)
        endif()

        # MSBuild's project reader rejects source items whose full path is 260
        # characters or longer, and directories at 248 characters or longer.
        math(EXPR generated_path_budget "259 - ${out_dir_length} - ${path_separator_length}")
        math(EXPR generated_directory_budget "247 - ${out_dir_length} - ${path_separator_length}")
        if(generated_path_budget GREATER 255)
            set(generated_path_budget 255)
        endif()
        string(LENGTH ".protocyte.hpp" generated_file_suffix_length)
        set(generated_path_digest_length 64)
        math(
            EXPR
            minimum_hashed_generated_path_length
            "${generated_file_suffix_length} + ${generated_path_digest_length} + 1"
        )
        if(
            out_dir_length GREATER 247
            OR generated_path_budget LESS minimum_hashed_generated_path_length
        )
            message(
                FATAL_ERROR
                "protocyte_generate OUT_DIR is too long for Visual Studio/MSBuild: '${normalized_out_dir}'. "
                "MSBuild requires generated source paths shorter than 260 characters and directories "
                "shorter than 248 characters; collision-resistant Protocyte names need at least "
                "${minimum_hashed_generated_path_length} characters below OUT_DIR. "
                "Choose a shorter OUT_DIR or build directory."
            )
        endif()
    endif()
    set(${out_path_var} "${generated_path_budget}" PARENT_SCOPE)
    set(${out_directory_var} "${generated_directory_budget}" PARENT_SCOPE)
endfunction()

function(_protocyte_validate_parsed_arguments function_name unparsed_arguments missing_values)
    if(NOT "${missing_values}" STREQUAL "")
        list(JOIN missing_values ", " missing_values_text)
        message(
            FATAL_ERROR
            "${function_name} requires a value for the following keyword(s): ${missing_values_text}"
        )
    endif()
    if(NOT "${unparsed_arguments}" STREQUAL "")
        list(JOIN unparsed_arguments ", " unparsed_arguments_text)
        message(
            FATAL_ERROR
            "${function_name} received unknown argument(s): ${unparsed_arguments_text}"
        )
    endif()
endfunction()

macro(_protocyte_validate_unique_one_value_keywords_from_argv function_name one_value_keywords argument_count)
    set(_protocyte_duplicate_keywords)
    set(_protocyte_one_value_keywords "${one_value_keywords}")
    if(${argument_count} GREATER 0)
        math(EXPR _protocyte_last_argument_index "${argument_count} - 1")
        foreach(_protocyte_keyword IN LISTS _protocyte_one_value_keywords)
            set(_protocyte_keyword_count 0)
            foreach(_protocyte_argument_index RANGE 0 ${_protocyte_last_argument_index})
                set(_protocyte_argument_variable "ARGV${_protocyte_argument_index}")
                if("${${_protocyte_argument_variable}}" STREQUAL "${_protocyte_keyword}")
                    math(EXPR _protocyte_keyword_count "${_protocyte_keyword_count} + 1")
                endif()
            endforeach()
            if(_protocyte_keyword_count GREATER 1)
                list(APPEND _protocyte_duplicate_keywords "${_protocyte_keyword}")
            endif()
        endforeach()
    endif()

    if(_protocyte_duplicate_keywords)
        list(JOIN _protocyte_duplicate_keywords ", " _protocyte_duplicate_keywords_text)
        message(
            FATAL_ERROR
            "${function_name} received duplicate single-value keyword(s): ${_protocyte_duplicate_keywords_text}"
        )
    endif()

    unset(_protocyte_argument_index)
    unset(_protocyte_argument_variable)
    unset(_protocyte_duplicate_keywords)
    unset(_protocyte_duplicate_keywords_text)
    unset(_protocyte_keyword)
    unset(_protocyte_keyword_count)
    unset(_protocyte_last_argument_index)
    unset(_protocyte_one_value_keywords)
endmacro()

function(_protocyte_append_forwarded_values arguments_var keyword values_var)
    set(arguments "${${arguments_var}}")
    list(APPEND arguments "${keyword}")
    foreach(value IN LISTS ${values_var})
        string(REPLACE ";" "\\;" escaped_value "${value}")
        list(APPEND arguments "${escaped_value}")
    endforeach()
    set(${arguments_var} "${arguments}" PARENT_SCOPE)
endfunction()

function(_protocyte_value_is_nonempty out_var variable_name)
    if(DEFINED "${variable_name}" AND NOT "${${variable_name}}" STREQUAL "")
        set(${out_var} TRUE PARENT_SCOPE)
    else()
        set(${out_var} FALSE PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_claim_runtime_output output_path owner_target)
    set(output_identity "${output_path}")
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${output_identity}" output_identity)
    endif()
    string(SHA256 output_key "${output_identity}")
    set(owner_property "PROTOCYTE_INTERNAL_RUNTIME_OUTPUT_OWNER_${output_key}")
    set(path_property "PROTOCYTE_INTERNAL_RUNTIME_OUTPUT_PATH_${output_key}")
    get_property(output_is_claimed GLOBAL PROPERTY "${owner_property}" SET)
    if(output_is_claimed)
        get_property(existing_owner GLOBAL PROPERTY "${owner_property}")
        get_property(existing_path GLOBAL PROPERTY "${path_property}")
        message(
            FATAL_ERROR
            "Protocyte runtime output '${existing_path}' is already owned by code generation target "
            "'${existing_owner}'; target '${owner_target}' cannot also use EMIT_RUNTIME for that file. "
            "Each emitted runtime.hpp must have one generation owner. Use a distinct OUT_DIR or RUNTIME_PREFIX. "
            "For additional libraries, omit EMIT_RUNTIME and use RUNTIME_TARGET to select a shared runtime target."
        )
    endif()
    set_property(GLOBAL PROPERTY "${owner_property}" "${owner_target}")
    set_property(GLOBAL PROPERTY "${path_property}" "${output_path}")
endfunction()

function(_protocyte_descriptor_outputs out_headers out_sources out_dir proto_names_var)
    set(headers)
    set(sources)
    foreach(proto_name IN LISTS ${proto_names_var})
        _protocyte_validate_descriptor_name("${proto_name}")
        _protocyte_normalize_generated_path(
            normalized_generated_path
            "${proto_name}"
            "${ARGV4}"
            "${ARGV5}"
        )
        string(TOLOWER "${normalized_generated_path}" normalized_generated_path_casefolded)
        string(SHA256 generated_path_key "${normalized_generated_path_casefolded}")
        if(DEFINED protocyte_generated_path_owner_${generated_path_key})
            set(previous_proto_name "${protocyte_generated_path_owner_${generated_path_key}}")
            set(previous_generated_path "${protocyte_generated_path_value_${generated_path_key}}")
            string(TOLOWER "${previous_generated_path}" previous_generated_path_casefolded)
            if(previous_generated_path_casefolded STREQUAL normalized_generated_path_casefolded)
                message(
                    FATAL_ERROR
                    "generated file name collision after portable path normalization: descriptor files "
                    "'${previous_proto_name}' and '${proto_name}' produce '${previous_generated_path}' and "
                    "'${normalized_generated_path}', which collide on case-insensitive filesystems"
                )
            endif()
        endif()
        set(protocyte_generated_path_owner_${generated_path_key} "${proto_name}")
        set(
            protocyte_generated_path_value_${generated_path_key}
            "${normalized_generated_path}"
        )
        set(protocyte_base "${out_dir}/${normalized_generated_path}")
        list(APPEND headers "${protocyte_base}.hpp")
        list(APPEND sources "${protocyte_base}.cpp")
    endforeach()
    set(${out_headers} "${headers}" PARENT_SCOPE)
    set(${out_sources} "${sources}" PARENT_SCOPE)
endfunction()

function(_protocyte_owned_output_key out_var output_path)
    cmake_path(NORMAL_PATH output_path OUTPUT_VARIABLE normalized_output_path)
    set(output_identity "${normalized_output_path}")
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${output_identity}" output_identity)
    endif()
    string(SHA256 output_key "${output_identity}")
    set(${out_var} "${output_key}" PARENT_SCOPE)
endfunction()

function(_protocyte_owned_output_claim_key out_var output_path)
    cmake_path(NORMAL_PATH output_path OUTPUT_VARIABLE normalized_output_path)
    string(TOLOWER "${normalized_output_path}" portable_output_identity)
    string(SHA256 output_claim_key "${portable_output_identity}")
    set(${out_var} "${output_claim_key}" PARENT_SCOPE)
endfunction()

function(_protocyte_schedule_owned_output_cleanup)
    if(DEFINED CMAKE_SCRIPT_MODE_FILE)
        return()
    endif()
    get_property(
        cleanup_scheduled
        GLOBAL PROPERTY PROTOCYTE_INTERNAL_OWNED_OUTPUT_CLEANUP_SCHEDULED
        SET
    )
    if(cleanup_scheduled)
        return()
    endif()

    set(
        manifest_root
        "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-owned-outputs"
    )
    set_property(
        GLOBAL PROPERTY
        PROTOCYTE_INTERNAL_OWNED_OUTPUT_MANIFEST_ROOT
        "${manifest_root}"
    )
    set_property(
        GLOBAL PROPERTY
        PROTOCYTE_INTERNAL_OWNED_OUTPUT_CLEANUP_SCHEDULED
        TRUE
    )
    cmake_language(
        DEFER
        DIRECTORY "${CMAKE_SOURCE_DIR}"
        CALL _protocyte_finalize_owned_outputs
    )
endfunction()

function(_protocyte_owned_output_manifest_target_key out_var manifest_dir)
    set(manifest_target_key "")
    if(IS_DIRECTORY "${manifest_dir}")
        cmake_path(GET manifest_dir FILENAME candidate_target_key)
        string(LENGTH "${candidate_target_key}" candidate_target_key_length)
        if(
            candidate_target_key_length EQUAL 64
            AND candidate_target_key MATCHES "^[0-9a-f]+$"
        )
            set(manifest_target_key "${candidate_target_key}")
        endif()
    endif()
    set(${out_var} "${manifest_target_key}" PARENT_SCOPE)
endfunction()

function(_protocyte_legacy_owned_output_manifest_is_valid out_var manifest_dir)
    set(${out_var} FALSE PARENT_SCOPE)
    if(IS_SYMLINK "${manifest_dir}")
        return()
    endif()
    _protocyte_owned_output_manifest_target_key(manifest_target_key "${manifest_dir}")
    if(manifest_target_key STREQUAL "")
        return()
    endif()

    cmake_path(GET manifest_dir PARENT_PATH candidate_manifest_root)
    cmake_path(GET candidate_manifest_root FILENAME candidate_manifest_root_name)
    cmake_path(GET candidate_manifest_root PARENT_PATH candidate_cmakefiles_dir)
    cmake_path(GET candidate_cmakefiles_dir FILENAME candidate_cmakefiles_name)
    cmake_path(GET candidate_cmakefiles_dir PARENT_PATH candidate_binary_directory)
    set(build_tree_root "${CMAKE_BINARY_DIR}")
    cmake_path(
        IS_PREFIX build_tree_root
        "${candidate_binary_directory}"
        NORMALIZE
        candidate_is_in_build_tree
    )
    if(
        NOT candidate_manifest_root_name STREQUAL "protocyte-owned-outputs"
        OR NOT candidate_cmakefiles_name STREQUAL "CMakeFiles"
        OR NOT candidate_is_in_build_tree
        OR "${candidate_binary_directory}" STREQUAL "${CMAKE_BINARY_DIR}"
    )
        return()
    endif()

    set(output_root_file "${manifest_dir}/output-root.path")
    if(
        NOT EXISTS "${output_root_file}"
        OR IS_DIRECTORY "${output_root_file}"
        OR IS_SYMLINK "${output_root_file}"
    )
        return()
    endif()
    file(READ "${output_root_file}" output_root)
    file(GLOB manifest_files LIST_DIRECTORIES TRUE "${manifest_dir}/*")
    set(saw_output_marker FALSE)
    foreach(manifest_file IN LISTS manifest_files)
        if(manifest_file STREQUAL output_root_file)
            continue()
        endif()
        if(IS_DIRECTORY "${manifest_file}" OR IS_SYMLINK "${manifest_file}")
            return()
        endif()
        cmake_path(GET manifest_file EXTENSION manifest_file_extension)
        cmake_path(GET manifest_file STEM output_key)
        string(LENGTH "${output_key}" output_key_length)
        if(
            NOT manifest_file_extension STREQUAL ".path"
            OR NOT output_key_length EQUAL 64
            OR NOT output_key MATCHES "^[0-9a-f]+$"
        )
            return()
        endif()
        file(READ "${manifest_file}" output_path)
        _protocyte_owned_output_key(recorded_output_key "${output_path}")
        _protocyte_generated_output_path_is_safe(
            output_path_is_safe
            "${output_path}"
            "${output_root}"
        )
        if(
            NOT recorded_output_key STREQUAL output_key
            OR NOT output_path_is_safe
        )
            return()
        endif()
        set(saw_output_marker TRUE)
    endforeach()
    if(saw_output_marker)
        set(${out_var} TRUE PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_collect_owned_output_manifests out_var manifest_root)
    file(GLOB manifest_entries LIST_DIRECTORIES TRUE "${manifest_root}/*")
    file(
        GLOB_RECURSE legacy_output_root_files
        LIST_DIRECTORIES FALSE
        "${CMAKE_BINARY_DIR}/output-root.path"
    )
    foreach(legacy_output_root_file IN LISTS legacy_output_root_files)
        cmake_path(GET legacy_output_root_file PARENT_PATH candidate_manifest_dir)
        cmake_path(GET candidate_manifest_dir PARENT_PATH candidate_manifest_root)
        if(candidate_manifest_root STREQUAL manifest_root)
            continue()
        endif()
        _protocyte_legacy_owned_output_manifest_is_valid(
            candidate_manifest_is_valid
            "${candidate_manifest_dir}"
        )
        if(candidate_manifest_is_valid)
            list(APPEND manifest_entries "${candidate_manifest_dir}")
        endif()
    endforeach()
    list(REMOVE_DUPLICATES manifest_entries)
    set(${out_var} "${manifest_entries}" PARENT_SCOPE)
endfunction()

function(_protocyte_read_owned_output_hash out_var hash_file)
    set(output_hash "")
    if(EXISTS "${hash_file}")
        file(READ "${hash_file}" candidate_hash)
        string(LENGTH "${candidate_hash}" candidate_hash_length)
        if(candidate_hash_length EQUAL 64 AND candidate_hash MATCHES "^[0-9a-f]+$")
            set(output_hash "${candidate_hash}")
        endif()
    endif()
    set(${out_var} "${output_hash}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_retire_owned_output
    out_var
    output_path
    output_key
    trusted_hash
    output_root
)
    _protocyte_shared_output_lock_directory(output_lock_directory)
    file(MAKE_DIRECTORY "${output_lock_directory}")
    file(
        LOCK "${output_lock_directory}/${output_key}.lock"
        GUARD FUNCTION
        TIMEOUT 600
        RESULT_VARIABLE output_lock_result
    )
    if(NOT "${output_lock_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Protocyte could not lock retired generated output '${output_path}': ${output_lock_result}"
        )
    endif()

    _protocyte_generated_output_path_is_safe(
        output_path_is_safe
        "${output_path}"
        "${output_root}"
    )
    if(NOT output_path_is_safe)
        set(${out_var} "unsafe" PARENT_SCOPE)
        return()
    endif()

    _protocyte_build_tree_owner_hash(build_tree_hash)
    set(output_owner_marker "${output_lock_directory}/${output_key}.owner")
    _protocyte_output_directory_owner_paths(
        root_owner_marker
        unused_root_owner_lock
        "${output_root}"
    )
    _protocyte_owner_record_status(
        output_owner_status
        output_owner_transaction_id
        "${output_owner_marker}"
        "${build_tree_hash}"
        "${root_owner_marker}"
    )
    if(output_owner_status STREQUAL "incomplete")
        _protocyte_recover_incomplete_owner_record(
            recovered_incomplete_owner
            "${output_owner_marker}"
            "${output_owner_transaction_id}"
            "${root_owner_marker}"
        )
        if(recovered_incomplete_owner)
            set(output_owner_status "missing")
        endif()
    endif()
    if(output_owner_status STREQUAL "different")
        set(${out_var} "transferred" PARENT_SCOPE)
        return()
    elseif(
        output_owner_status STREQUAL "malformed"
        OR output_owner_status STREQUAL "incomplete"
        OR output_owner_status STREQUAL "unverifiable"
    )
        set(${out_var} "pending" PARENT_SCOPE)
        return()
    endif()

    if(NOT EXISTS "${output_path}")
        if(output_owner_status STREQUAL "current")
            file(REMOVE "${output_owner_marker}")
        endif()
        set(${out_var} "released" PARENT_SCOPE)
        return()
    endif()
    if(IS_DIRECTORY "${output_path}" OR trusted_hash STREQUAL "")
        set(${out_var} "pending" PARENT_SCOPE)
        return()
    endif()

    file(SHA256 "${output_path}" current_output_hash)
    if(current_output_hash STREQUAL trusted_hash)
        _protocyte_generated_output_path_is_safe(
            output_path_is_still_safe
            "${output_path}"
            "${output_root}"
        )
        if(NOT output_path_is_still_safe)
            set(${out_var} "unsafe" PARENT_SCOPE)
            return()
        endif()
        file(REMOVE "${output_path}")
        if(
            output_owner_status STREQUAL "current"
            AND NOT EXISTS "${output_path}"
        )
            file(REMOVE "${output_owner_marker}")
        endif()
        set(${out_var} "released" PARENT_SCOPE)
    else()
        set(${out_var} "preserved" PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_finalize_owned_outputs)
    get_property(
        manifest_root
        GLOBAL PROPERTY PROTOCYTE_INTERNAL_OWNED_OUTPUT_MANIFEST_ROOT
    )
    get_property(target_keys GLOBAL PROPERTY PROTOCYTE_INTERNAL_OWNED_OUTPUT_TARGET_KEYS)
    list(REMOVE_DUPLICATES target_keys)
    _protocyte_collect_owned_output_manifests(manifest_entries "${manifest_root}")
    set(manifest_target_keys)

    # Capture prior fingerprints before retiring any manifest. This lets an
    # output keep its fingerprint when ownership moves to a renamed target.
    foreach(manifest_dir IN LISTS manifest_entries)
        _protocyte_owned_output_manifest_target_key(manifest_target_key "${manifest_dir}")
        if(manifest_target_key STREQUAL "")
            continue()
        endif()
        list(APPEND manifest_target_keys "${manifest_target_key}")
        list(APPEND protocyte_manifest_dirs_${manifest_target_key} "${manifest_dir}")
        set(previous_output_root_file "${manifest_dir}/output-root.path")
        set(previous_output_root "")
        if(EXISTS "${previous_output_root_file}")
            file(READ "${previous_output_root_file}" previous_output_root)
        endif()
        file(GLOB previous_markers LIST_DIRECTORIES FALSE "${manifest_dir}/*.path")
        list(REMOVE_ITEM previous_markers "${previous_output_root_file}")
        foreach(previous_marker IN LISTS previous_markers)
            cmake_path(GET previous_marker STEM previous_output_key)
            file(READ "${previous_marker}" previous_output)
            _protocyte_owned_output_key(recorded_output_key "${previous_output}")
            _protocyte_generated_output_path_is_lexically_owned(
                previous_output_is_owned
                "${previous_output}"
                "${previous_output_root}"
            )
            set(previous_hash_file "${manifest_dir}/${previous_output_key}.sha256")
            if(
                previous_output_is_owned
                AND recorded_output_key STREQUAL previous_output_key
            )
                _protocyte_read_owned_output_hash(
                    previous_output_hash
                    "${previous_hash_file}"
                )
                if(NOT previous_output_hash STREQUAL "")
                    set(hash_variable "protocyte_owned_output_hash_${previous_output_key}")
                    set(ambiguous_variable "${hash_variable}_ambiguous")
                    if(
                        DEFINED ${hash_variable}
                        AND NOT "${${hash_variable}}" STREQUAL "${previous_output_hash}"
                    )
                        set(${ambiguous_variable} TRUE)
                    else()
                        set(${hash_variable} "${previous_output_hash}")
                    endif()
                endif()
            endif()
        endforeach()
    endforeach()
    list(REMOVE_DUPLICATES manifest_target_keys)

    foreach(manifest_target_key IN LISTS manifest_target_keys)
        set(manifest_dirs_variable "protocyte_manifest_dirs_${manifest_target_key}")
        list(REMOVE_DUPLICATES ${manifest_dirs_variable})
        list(FIND target_keys "${manifest_target_key}" current_target_index)
        if(current_target_index EQUAL -1)
            set(target_is_current FALSE)
        else()
            set(target_is_current TRUE)
        endif()

        set(pending_output_keys)
        set(unnotified_pending_outputs)
        set(unnotified_unsafe_outputs)
        foreach(manifest_dir IN LISTS ${manifest_dirs_variable})
            set(previous_output_root_file "${manifest_dir}/output-root.path")
            set(previous_output_root "")
            if(EXISTS "${previous_output_root_file}")
                file(READ "${previous_output_root_file}" previous_output_root)
            endif()
            file(GLOB previous_markers LIST_DIRECTORIES FALSE "${manifest_dir}/*.path")
            list(REMOVE_ITEM previous_markers "${previous_output_root_file}")
            foreach(previous_marker IN LISTS previous_markers)
                cmake_path(GET previous_marker STEM previous_output_key)
                file(READ "${previous_marker}" previous_output)
                _protocyte_owned_output_key(recorded_output_key "${previous_output}")
                _protocyte_generated_output_path_is_lexically_owned(
                    previous_output_is_owned
                    "${previous_output}"
                    "${previous_output_root}"
                )
                get_property(
                    output_is_still_owned
                    GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_CURRENT_${previous_output_key}"
                    SET
                )
                set(previous_hash_file "${manifest_dir}/${previous_output_key}.sha256")
                _protocyte_read_owned_output_hash(
                    previous_output_hash
                    "${previous_hash_file}"
                )
                if(
                    previous_output_is_owned
                    AND recorded_output_key STREQUAL previous_output_key
                    AND NOT output_is_still_owned
                )
                    _protocyte_retire_owned_output(
                        retired_output_result
                        "${previous_output}"
                        "${previous_output_key}"
                        "${previous_output_hash}"
                        "${previous_output_root}"
                    )
                    if(
                        retired_output_result STREQUAL "pending"
                        OR retired_output_result STREQUAL "unsafe"
                    )
                        list(APPEND pending_output_keys "${previous_output_key}")
                        set(
                            protocyte_pending_output_${previous_output_key}
                            "${previous_output}"
                        )
                        set(
                            protocyte_pending_output_root_${previous_output_key}
                            "${previous_output_root}"
                        )
                        set(
                            protocyte_pending_output_hash_${previous_output_key}
                            "${previous_output_hash}"
                        )
                        if(retired_output_result STREQUAL "unsafe")
                            set(
                                protocyte_pending_output_reason_${previous_output_key}
                                "unsafe"
                            )
                        endif()
                        if(
                            NOT EXISTS
                                "${manifest_dir}/${previous_output_key}.pending-notified"
                        )
                            if(retired_output_result STREQUAL "unsafe")
                                list(APPEND unnotified_unsafe_outputs "${previous_output}")
                            else()
                                list(APPEND unnotified_pending_outputs "${previous_output}")
                            endif()
                        endif()
                    endif()
                endif()
            endforeach()
        endforeach()
        list(REMOVE_DUPLICATES pending_output_keys)
        list(REMOVE_DUPLICATES unnotified_pending_outputs)
        list(REMOVE_DUPLICATES unnotified_unsafe_outputs)

        foreach(manifest_dir IN LISTS ${manifest_dirs_variable})
            file(REMOVE_RECURSE "${manifest_dir}")
        endforeach()

        set(manifest_dir "${manifest_root}/${manifest_target_key}")
        if(target_is_current)
            get_property(
                current_output_root
                GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_ROOT_${manifest_target_key}"
            )
            get_property(
                current_output_keys
                GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_KEYS_${manifest_target_key}"
            )

            file(MAKE_DIRECTORY "${manifest_dir}")
            file(WRITE "${manifest_dir}/output-root.path" "${current_output_root}")
            foreach(current_output_key IN LISTS current_output_keys)
                get_property(
                    current_output
                    GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_PATH_${current_output_key}"
                )
                file(WRITE "${manifest_dir}/${current_output_key}.path" "${current_output}")
                set(hash_variable "protocyte_owned_output_hash_${current_output_key}")
                set(ambiguous_variable "${hash_variable}_ambiguous")
                if(DEFINED ${hash_variable} AND NOT DEFINED ${ambiguous_variable})
                    file(
                        WRITE
                        "${manifest_dir}/${current_output_key}.sha256"
                        "${${hash_variable}}"
                    )
                endif()
            endforeach()
        endif()

        foreach(pending_output_key IN LISTS pending_output_keys)
            set(pending_output "${protocyte_pending_output_${pending_output_key}}")
            set(
                pending_output_root
                "${protocyte_pending_output_root_${pending_output_key}}"
            )
            set(
                pending_output_hash
                "${protocyte_pending_output_hash_${pending_output_key}}"
            )
            set(
                pending_output_reason
                "${protocyte_pending_output_reason_${pending_output_key}}"
            )
            if(pending_output_reason STREQUAL "")
                set(pending_output_reason "unverified legacy output")
            endif()
            string(
                SHA256
                pending_manifest_target_key
                "protocyte-pending-owned-output|${pending_output_key}"
            )
            set(pending_manifest_dir "${manifest_root}/${pending_manifest_target_key}")
            file(REMOVE_RECURSE "${pending_manifest_dir}")
            file(MAKE_DIRECTORY "${pending_manifest_dir}")
            file(WRITE "${pending_manifest_dir}/output-root.path" "${pending_output_root}")
            file(
                WRITE
                "${pending_manifest_dir}/${pending_output_key}.path"
                "${pending_output}"
            )
            file(
                WRITE
                "${pending_manifest_dir}/${pending_output_key}.pending"
                "${pending_output_reason}\n"
            )
            if(NOT pending_output_hash STREQUAL "")
                file(
                    WRITE
                    "${pending_manifest_dir}/${pending_output_key}.sha256"
                    "${pending_output_hash}"
                )
            endif()
            file(
                WRITE
                "${pending_manifest_dir}/${pending_output_key}.pending-notified"
                "notified\n"
            )
        endforeach()
        if(unnotified_pending_outputs)
            list(JOIN unnotified_pending_outputs "\n  " pending_output_text)
            message(
                WARNING
                "Protocyte preserved generated output(s) from a legacy ownership manifest because this "
                "build tree predates content fingerprints:\n  ${pending_output_text}\n"
                "Remove obsolete files manually. To restore automatic cleanup, temporarily restore a "
                "code-generation target that declares these outputs, back up any edits, delete the outputs, "
                "and build that target once before removing them again."
            )
        endif()
        if(unnotified_unsafe_outputs)
            list(JOIN unnotified_unsafe_outputs "\n  " unsafe_output_text)
            message(
                WARNING
                "Protocyte preserved retired generated output(s) because canonical containment under the "
                "recorded OUT_DIR could not be verified:\n  ${unsafe_output_text}\n"
                "Replace any nested symbolic link or junction with a real directory and reconfigure to retry "
                "automatic cleanup, or remove obsolete files and their ownership records manually."
            )
        endif()
    endforeach()

    # Newly registered targets have no prior manifest entry to recreate above.
    foreach(target_key IN LISTS target_keys)
        set(manifest_dir "${manifest_root}/${target_key}")
        if(IS_DIRECTORY "${manifest_dir}")
            continue()
        endif()
        get_property(
            current_output_root
            GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_ROOT_${target_key}"
        )
        get_property(
            current_output_keys
            GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_KEYS_${target_key}"
        )
        file(MAKE_DIRECTORY "${manifest_dir}")
        file(WRITE "${manifest_dir}/output-root.path" "${current_output_root}")
        foreach(current_output_key IN LISTS current_output_keys)
            get_property(
                current_output
                GLOBAL PROPERTY "PROTOCYTE_INTERNAL_OWNED_OUTPUT_PATH_${current_output_key}"
            )
            file(WRITE "${manifest_dir}/${current_output_key}.path" "${current_output}")
            set(hash_variable "protocyte_owned_output_hash_${current_output_key}")
            set(ambiguous_variable "${hash_variable}_ambiguous")
            if(DEFINED ${hash_variable} AND NOT DEFINED ${ambiguous_variable})
                file(
                    WRITE
                    "${manifest_dir}/${current_output_key}.sha256"
                    "${${hash_variable}}"
                )
            endif()
        endforeach()
    endforeach()
endfunction()

function(_protocyte_register_owned_outputs target_name output_root outputs_var)
    cmake_path(NORMAL_PATH output_root OUTPUT_VARIABLE normalized_output_root)
    string(
        SHA256
        target_key
        "${CMAKE_CURRENT_BINARY_DIR}|${target_name}"
    )
    _protocyte_schedule_owned_output_cleanup()
    get_property(
        manifest_root
        GLOBAL PROPERTY PROTOCYTE_INTERNAL_OWNED_OUTPUT_MANIFEST_ROOT
    )
    set(manifest_dir "${manifest_root}/${target_key}")
    set(current_output_keys)
    foreach(output_path IN LISTS ${outputs_var})
        cmake_path(NORMAL_PATH output_path OUTPUT_VARIABLE normalized_output_path)
        _protocyte_owned_output_key(output_key "${normalized_output_path}")
        _protocyte_owned_output_claim_key(output_claim_key "${normalized_output_path}")
        set(claim_owner_property "PROTOCYTE_INTERNAL_OWNED_OUTPUT_CLAIM_OWNER_${output_claim_key}")
        set(claim_path_property "PROTOCYTE_INTERNAL_OWNED_OUTPUT_CLAIM_PATH_${output_claim_key}")
        get_property(output_is_claimed GLOBAL PROPERTY "${claim_owner_property}" SET)
        if(output_is_claimed)
            get_property(existing_owner GLOBAL PROPERTY "${claim_owner_property}")
            get_property(existing_path GLOBAL PROPERTY "${claim_path_property}")
            if(NOT existing_owner STREQUAL target_name)
                message(
                    FATAL_ERROR
                    "Protocyte generated output '${normalized_output_path}' for target '${target_name}' "
                    "collides with portable-equivalent output '${existing_path}' already owned by target "
                    "'${existing_owner}'. Each generated file must have one current code-generation owner. "
                    "Use a distinct OUT_DIR, select disjoint descriptor files, or generate the shared file "
                    "once and reuse its generation target."
                )
            endif()
        else()
            set_property(GLOBAL PROPERTY "${claim_owner_property}" "${target_name}")
            set_property(GLOBAL PROPERTY "${claim_path_property}" "${normalized_output_path}")
        endif()
        list(APPEND current_output_keys "${output_key}")
        set_property(
            GLOBAL PROPERTY
            "PROTOCYTE_INTERNAL_OWNED_OUTPUT_PATH_${output_key}"
            "${normalized_output_path}"
        )
        set_property(
            GLOBAL PROPERTY
            "PROTOCYTE_INTERNAL_OWNED_OUTPUT_CURRENT_${output_key}"
            TRUE
        )
    endforeach()

    set_property(
        GLOBAL APPEND PROPERTY
        PROTOCYTE_INTERNAL_OWNED_OUTPUT_TARGET_KEYS
        "${target_key}"
    )
    set_property(
        GLOBAL PROPERTY
        "PROTOCYTE_INTERNAL_OWNED_OUTPUT_MANIFEST_DIR_${target_key}"
        "${manifest_dir}"
    )
    set_property(
        GLOBAL PROPERTY
        "PROTOCYTE_INTERNAL_OWNED_OUTPUT_ROOT_${target_key}"
        "${normalized_output_root}"
    )
    set_property(
        GLOBAL PROPERTY
        "PROTOCYTE_INTERNAL_OWNED_OUTPUT_KEYS_${target_key}"
        "${current_output_keys}"
    )

    set(
        PROTOCYTE_INTERNAL_CURRENT_OWNED_OUTPUT_MANIFEST_DIR
        "${manifest_dir}"
        PARENT_SCOPE
    )
endfunction()

_protocyte_schedule_owned_output_cleanup()

function(_protocyte_parse_discovered_descriptor_names out_var discovered_json)
    string(JSON discovered_count ERROR_VARIABLE json_error LENGTH "${discovered_json}")
    if(NOT json_error STREQUAL "NOTFOUND")
        message(FATAL_ERROR "Protocyte descriptor discovery returned invalid JSON: ${json_error}")
    endif()

    set(discovered_list)
    if(discovered_count GREATER 0)
        math(EXPR discovered_last "${discovered_count} - 1")
        foreach(index RANGE 0 ${discovered_last})
            string(JSON discovered_name ERROR_VARIABLE json_error GET "${discovered_json}" ${index})
            if(NOT json_error STREQUAL "NOTFOUND")
                message(FATAL_ERROR "Protocyte descriptor discovery returned invalid JSON: ${json_error}")
            endif()
            string(REPLACE ";" "\\;" discovered_name "${discovered_name}")
            list(APPEND discovered_list "${discovered_name}")
        endforeach()
    endif()
    set(${out_var} "${discovered_list}" PARENT_SCOPE)
endfunction()

function(_protocyte_discover_descriptor_set out_var descriptor_set)
    if(NOT EXISTS "${descriptor_set}")
        message(FATAL_ERROR "protocyte descriptor-set DISCOVER requires an existing file: ${descriptor_set}")
    endif()
    _protocyte_get_internal(protocyte_plugin_executable PLUGIN_EXECUTABLE)
    if("${protocyte_plugin_executable}" STREQUAL "")
        message(FATAL_ERROR "Protocyte descriptor discovery requires a prepared plugin executable")
    endif()
    _protocyte_get_internal(protocyte_plugin_is_managed PLUGIN_IS_MANAGED)
    if("${protocyte_plugin_is_managed}" STREQUAL "")
        set(protocyte_plugin_is_managed FALSE)
    endif()
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${protocyte_plugin_executable}")

    # The managed plugin is part of Protocyte's own environment boundary, so
    # do not let its Python startup inherit caller import-path overrides.
    # Explicit plugins remain caller-owned and deliberately retain their
    # ambient environment.
    set(descriptor_discovery_launcher "${protocyte_plugin_executable}")
    if(protocyte_plugin_is_managed)
        set(
            descriptor_discovery_launcher
            "${CMAKE_COMMAND}"
            -E
            env
            --unset=PYTHONHOME
            --unset=PYTHONPATH
            "${protocyte_plugin_executable}"
        )
    endif()

    _protocyte_resolve_tool_timeout(descriptor_discovery_timeout)
    _protocyte_execute_bounded(
        discover_result
        discovered
        discover_error
        discover_timed_out
        COMMAND
            ${descriptor_discovery_launcher}
            descriptor-set list "${descriptor_set}"
        TIMEOUT_SECONDS "${descriptor_discovery_timeout}"
    )
    if(discover_timed_out)
        string(STRIP "${discovered}" discovered_output)
        string(STRIP "${discover_error}" discover_error)
        if(discovered_output STREQUAL "")
            set(discovered_output "<no standard output>")
        endif()
        if(discover_error STREQUAL "")
            set(discover_error "<no standard error>")
        endif()
        message(
            FATAL_ERROR
            "Protocyte descriptor discovery through '${protocyte_plugin_executable}' timed out after "
            "${descriptor_discovery_timeout} seconds. Set PROTOCYTE_TOOL_TIMEOUT_SECONDS to a larger "
            "value or 0 to disable this timeout.\n\n"
            "Command:\n  \"${protocyte_plugin_executable}\" descriptor-set list \"${descriptor_set}\"\n\n"
            "Standard output:\n${discovered_output}\n\n"
            "Standard error:\n${discover_error}"
        )
    endif()
    if(NOT "${discover_result}" STREQUAL "0")
        string(STRIP "${discovered}" discovered_output)
        string(STRIP "${discover_error}" discover_error)
        if(discovered_output STREQUAL "")
            set(discovered_output "<no standard output>")
        endif()
        if(discover_error STREQUAL "")
            set(discover_error "<no standard error>")
        endif()
        if(protocyte_plugin_is_managed)
            string(
                CONCAT
                discover_plugin_hint
                "Protocyte's managed plugin is expected to support the 'descriptor-set list' command. "
                "Reconfigure after replacing the managed environment, or report this failure with the output above."
            )
        else()
            string(
                CONCAT
                discover_plugin_hint
                "PROTOCYTE_PLUGIN_EXECUTABLE overrides must point to a Protocyte plugin that supports "
                "the 'descriptor-set list' command."
            )
        endif()
        message(
            FATAL_ERROR
            "Failed to inspect descriptor set '${descriptor_set}'.\n\n"
            "Command:\n  \"${protocyte_plugin_executable}\" descriptor-set list \"${descriptor_set}\"\n"
            "Exit code: ${discover_result}\n\n"
            "Standard output:\n${discovered_output}\n\n"
            "Standard error:\n${discover_error}\n\n"
            "${discover_plugin_hint}"
        )
    endif()
    _protocyte_parse_discovered_descriptor_names(discovered_list "${discovered}")
    set(${out_var} "${discovered_list}" PARENT_SCOPE)
endfunction()

function(_protocyte_validate_explicit_plugin out_var plugin_executable)
    if("${plugin_executable}" MATCHES "\\$<")
        message(
            FATAL_ERROR
            "PROTOCYTE_PLUGIN_EXECUTABLE must be a configure-time executable path, not a generator expression"
        )
    endif()
    if(IS_ABSOLUTE "${plugin_executable}")
        set(plugin_path "${plugin_executable}")
    else()
        get_filename_component(plugin_path "${plugin_executable}" ABSOLUTE BASE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
    endif()
    cmake_path(NORMAL_PATH plugin_path)
    string(FIND "${plugin_path}" ";" semicolon_index)
    if(NOT semicolon_index EQUAL -1)
        message(
            FATAL_ERROR
            "PROTOCYTE_PLUGIN_EXECUTABLE must not contain ';' because CMake cannot safely preserve "
            "semicolons in executable paths. Move the plugin to a semicolon-free path or provide a "
            "wrapper from one."
        )
    endif()
    if(NOT EXISTS "${plugin_path}" OR IS_DIRECTORY "${plugin_path}")
        message(FATAL_ERROR "PROTOCYTE_PLUGIN_EXECUTABLE does not name an existing file: ${plugin_path}")
    endif()

    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${plugin_path}")

    _protocyte_get_internal(expected_version VERSION)
    if("${expected_version}" STREQUAL "")
        message(FATAL_ERROR "Protocyte's CMake package did not declare its expected plugin version")
    endif()
    execute_process(
        COMMAND "${plugin_path}" --version
        RESULT_VARIABLE version_result
        OUTPUT_VARIABLE version_output
        ERROR_VARIABLE version_error
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_STRIP_TRAILING_WHITESPACE
        TIMEOUT 15
    )
    if(NOT "${version_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "PROTOCYTE_PLUGIN_EXECUTABLE failed its required --version check: ${plugin_path}\n"
            "Exit code: ${version_result}\nStandard output: ${version_output}\nStandard error: ${version_error}"
        )
    endif()
    if(NOT "${version_output}" STREQUAL "${expected_version}")
        message(
            FATAL_ERROR
            "PROTOCYTE_PLUGIN_EXECUTABLE version mismatch: CMake package ${expected_version}, "
            "plugin reported ${version_output}\nPlugin: ${plugin_path}"
        )
    endif()
    set(${out_var} "${plugin_path}" PARENT_SCOPE)
endfunction()

function(_protocyte_get_internal out_var name)
    get_property(value GLOBAL PROPERTY "PROTOCYTE_INTERNAL_${name}")
    set(${out_var} "${value}" PARENT_SCOPE)
endfunction()

function(_protocyte_python_environment_paths out_python out_plugin environment_dir)
    if(CMAKE_HOST_WIN32)
        set(python_executable "${environment_dir}/Scripts/python.exe")
        set(plugin_executable "${environment_dir}/Scripts/protoc-gen-protocyte.exe")
    else()
        set(python_executable "${environment_dir}/bin/python")
        set(plugin_executable "${environment_dir}/bin/protoc-gen-protocyte")
    endif()

    set(${out_python} "${python_executable}" PARENT_SCOPE)
    set(${out_plugin} "${plugin_executable}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_python_environment_fingerprint
    out_var
    project_root
    constraints_file
    python_executable
    python_version
)
    set(project_files "${project_root}/pyproject.toml" "${constraints_file}")
    foreach(metadata_file IN ITEMS LICENSE NOTICE)
        if(EXISTS "${project_root}/${metadata_file}")
            list(APPEND project_files "${project_root}/${metadata_file}")
        endif()
    endforeach()
    file(
        GLOB_RECURSE package_files
        LIST_DIRECTORIES FALSE
        CONFIGURE_DEPENDS
        "${project_root}/src/protocyte/*.py"
        "${project_root}/src/protocyte/*.proto"
        "${project_root}/src/protocyte/*.hpp"
    )
    list(APPEND project_files ${package_files})
    list(REMOVE_DUPLICATES project_files)
    list(SORT project_files)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${project_files})

    set(fingerprint_material "python=${python_executable}\nversion=${python_version}")
    foreach(project_file IN LISTS project_files)
        if(NOT EXISTS "${project_file}")
            message(FATAL_ERROR "Protocyte Python installation input does not exist: ${project_file}")
        endif()
        file(SHA256 "${project_file}" project_file_hash)
        set(project_file_path "${project_file}")
        cmake_path(
            RELATIVE_PATH project_file_path
            BASE_DIRECTORY "${project_root}"
            OUTPUT_VARIABLE project_file_relative
        )
        string(APPEND fingerprint_material "\n${project_file_relative}=${project_file_hash}")
    endforeach()

    string(SHA256 fingerprint "${fingerprint_material}")
    set(${out_var} "${fingerprint}" PARENT_SCOPE)
endfunction()

function(_protocyte_stage_python_project source_root constraints_file destination)
    file(MAKE_DIRECTORY "${destination}/src")
    foreach(project_file IN ITEMS pyproject.toml LICENSE NOTICE)
        if(EXISTS "${source_root}/${project_file}")
            file(
                COPY_FILE
                "${source_root}/${project_file}"
                "${destination}/${project_file}"
                ONLY_IF_DIFFERENT
            )
        endif()
    endforeach()
    file(
        COPY_FILE
        "${constraints_file}"
        "${destination}/protocyte-cmake-constraints.txt"
        ONLY_IF_DIFFERENT
    )
    file(
        COPY "${source_root}/src/protocyte"
        DESTINATION "${destination}/src"
        FILE_PERMISSIONS
            OWNER_READ OWNER_WRITE
            GROUP_READ
            WORLD_READ
        DIRECTORY_PERMISSIONS
            OWNER_READ OWNER_WRITE OWNER_EXECUTE
            GROUP_READ GROUP_EXECUTE
            WORLD_READ WORLD_EXECUTE
        FILES_MATCHING
            PATTERN "*.py"
            PATTERN "*.proto"
            PATTERN "*.hpp"
            PATTERN "__pycache__" EXCLUDE
            PATTERN "*.pyc" EXCLUDE
    )
endfunction()

function(
    _protocyte_run_managed_pip
    out_result
    out_output
    out_error
    timeout
    python_executable
)
    _protocyte_check_managed_pip_configuration(
        configuration_result
        configuration_error
        "${python_executable}"
    )
    if(NOT "${configuration_result}" STREQUAL "0")
        set(${out_result} "${configuration_result}" PARENT_SCOPE)
        set(${out_output} "" PARENT_SCOPE)
        set(${out_error} "${configuration_error}" PARENT_SCOPE)
        return()
    endif()

    # Remove PIP_* destination and additive-install overrides, plus Python
    # import-path overrides, so every installation stays inside the managed
    # environment while index, proxy, and certificate configuration remains
    # available.
    execute_process(
        COMMAND
            "${CMAKE_COMMAND}" -E env
            "--unset=PIP_TARGET"
            "--unset=PIP_PREFIX"
            "--unset=PIP_ROOT"
            "--unset=PIP_USER"
            "--unset=PIP_PYTHON"
            "--unset=PIP_QUIET"
            "--unset=PIP_REQUIREMENT"
            "--unset=PIP_EDITABLE"
            "--unset=PIP_GROUP"
            "--unset=PIP_REQUIREMENTS_FROM_SCRIPT"
            "--unset=PYTHONUSERBASE"
            "--unset=PYTHONPATH"
            "--unset=PYTHONHOME"
            "PIP_ISOLATED=0"
            "${python_executable}" -I -m pip install
            --disable-pip-version-check
            --no-input
            --no-user
            ${ARGN}
        RESULT_VARIABLE result
        OUTPUT_VARIABLE output
        ERROR_VARIABLE error
        TIMEOUT "${timeout}"
    )
    set(${out_result} "${result}" PARENT_SCOPE)
    set(${out_output} "${output}" PARENT_SCOPE)
    set(${out_error} "${error}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_check_managed_pip_configuration
    out_result
    out_error
    python_executable
)
    # Inspect the effective configuration without destination overrides from
    # the parent process. The script reports only unsafe option names, never
    # values: index URLs can contain credentials.
    set(configuration_script [=[
from pip._internal.configuration import Configuration, ConfigurationError

configuration = Configuration(isolated=False)
configuration.load()
unsafe = set()
for scope in ("global", "install"):
    for option in ("target", "prefix", "root"):
        key = f"{scope}.{option}"
        try:
            value = configuration.get_value(key)
        except ConfigurationError:
            continue
        normalized = str(value).strip().casefold()
        if normalized:
            unsafe.add(key)
    for option in ("requirement", "editable", "group", "requirements-from-script"):
        key = f"{scope}.{option}"
        try:
            value = configuration.get_value(key)
        except ConfigurationError:
            continue
        if str(value).strip():
            unsafe.add(key)
try:
    global_python = configuration.get_value("global.python")
except ConfigurationError:
    global_python = ""
if str(global_python).strip():
    unsafe.add("global.python")
print(",".join(sorted(unsafe)))
]=])
    execute_process(
        COMMAND
            "${CMAKE_COMMAND}" -E env
            "--unset=PIP_TARGET"
            "--unset=PIP_PREFIX"
            "--unset=PIP_ROOT"
            "--unset=PIP_USER"
            "--unset=PIP_PYTHON"
            "--unset=PIP_QUIET"
            "--unset=PIP_REQUIREMENT"
            "--unset=PIP_EDITABLE"
            "--unset=PIP_GROUP"
            "--unset=PIP_REQUIREMENTS_FROM_SCRIPT"
            "--unset=PYTHONUSERBASE"
            "--unset=PYTHONPATH"
            "--unset=PYTHONHOME"
            "PIP_ISOLATED=0"
            "${python_executable}" -I -c "${configuration_script}"
        RESULT_VARIABLE config_result
        OUTPUT_VARIABLE config_output
        ERROR_VARIABLE config_error
        TIMEOUT 30
    )
    if(NOT "${config_result}" STREQUAL "0")
        set(${out_result} "configuration-inspection-failed" PARENT_SCOPE)
        set(
            ${out_error}
            "Failed to inspect pip configuration before provisioning Protocyte's managed Python environment. "
            "Fix the local pip configuration and retry."
            PARENT_SCOPE
        )
        return()
    endif()
    string(STRIP "${config_output}" configured_options)
    if(NOT "${configured_options}" STREQUAL "")
        set(${out_result} "unsafe-pip-configuration" PARENT_SCOPE)
        set(
            ${out_error}
            "Refusing to provision Protocyte's managed Python environment because the effective pip configuration "
            "sets unsupported managed-install options: ${configured_options}. Remove those options or use a pip "
            "configuration without custom install destinations or additional requirements; index, proxy, certificate, "
            "and cache settings remain supported."
            PARENT_SCOPE
        )
        return()
    endif()
    set(${out_result} "0" PARENT_SCOPE)
    set(${out_error} "" PARENT_SCOPE)
endfunction()

function(
    _protocyte_verify_python_environment
    out_result
    out_output
    out_error
    python_executable
    plugin_executable
    constraints_file
    expected_version
)
    if(NOT EXISTS "${python_executable}")
        set(${out_result} "missing-python" PARENT_SCOPE)
        set(${out_output} "" PARENT_SCOPE)
        set(${out_error} "The managed Python executable does not exist: ${python_executable}" PARENT_SCOPE)
        return()
    endif()
    if(NOT EXISTS "${plugin_executable}")
        set(${out_result} "missing-entry-point" PARENT_SCOPE)
        set(${out_output} "" PARENT_SCOPE)
        set(${out_error} "The managed plugin entry point does not exist: ${plugin_executable}" PARENT_SCOPE)
        return()
    endif()

    set(verify_script [=[
from importlib.metadata import version
from pathlib import Path
import sys

requirements = []
for raw_line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or line.startswith("--hash="):
        continue
    requirements.append(line.removesuffix("\\").rstrip())
expected = dict(requirement.split("==", 1) for requirement in requirements)
mismatches = {
    name: (wanted, version(name))
    for name, wanted in expected.items()
    if version(name) != wanted
}
if mismatches:
    raise RuntimeError(f"managed Python package versions do not match constraints: {mismatches}")

installed_protocyte_version = version("protocyte")
expected_protocyte_version = sys.argv[2]
if installed_protocyte_version != expected_protocyte_version:
    raise RuntimeError(
        "managed Protocyte package version mismatch: "
        f"expected {expected_protocyte_version}, installed {installed_protocyte_version}"
    )

import google.protobuf
import protocyte.main
]=])
    execute_process(
        COMMAND
            "${CMAKE_COMMAND}" -E env
            "--unset=PYTHONPATH"
            "--unset=PYTHONHOME"
            "${python_executable}" -I -c "${verify_script}"
            "${constraints_file}" "${expected_version}"
        RESULT_VARIABLE verify_result
        OUTPUT_VARIABLE verify_output
        ERROR_VARIABLE verify_error
        TIMEOUT 30
    )
    if("${verify_result}" STREQUAL "0")
        execute_process(
            COMMAND
                "${CMAKE_COMMAND}" -E env
                "--unset=PIP_PYTHON"
                "--unset=PIP_REQUIREMENT"
                "--unset=PIP_EDITABLE"
                "--unset=PIP_GROUP"
                "--unset=PIP_REQUIREMENTS_FROM_SCRIPT"
                "--unset=PYTHONPATH"
                "--unset=PYTHONHOME"
                "PIP_ISOLATED=0"
                "${python_executable}" -I -m pip check
            RESULT_VARIABLE pip_check_result
            OUTPUT_VARIABLE pip_check_output
            ERROR_VARIABLE pip_check_error
            TIMEOUT 60
        )
        string(APPEND verify_output "${pip_check_output}")
        string(APPEND verify_error "${pip_check_error}")
        if(NOT "${pip_check_result}" STREQUAL "0")
            set(verify_result "${pip_check_result}")
        endif()
    endif()
    if("${verify_result}" STREQUAL "0")
        execute_process(
            COMMAND
                "${CMAKE_COMMAND}" -E env
                "--unset=PYTHONPATH"
                "--unset=PYTHONHOME"
                "${plugin_executable}" --version
            RESULT_VARIABLE plugin_verify_result
            OUTPUT_VARIABLE plugin_verify_output
            ERROR_VARIABLE plugin_verify_error
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_STRIP_TRAILING_WHITESPACE
            TIMEOUT 15
        )
        string(APPEND verify_output "${plugin_verify_output}")
        string(APPEND verify_error "${plugin_verify_error}")
        if(NOT "${plugin_verify_result}" STREQUAL "0")
            set(verify_result "${plugin_verify_result}")
        elseif(NOT "${plugin_verify_output}" STREQUAL "${expected_version}")
            set(verify_result "version-mismatch")
            string(
                APPEND
                verify_error
                "\nmanaged Protocyte plugin version mismatch: expected ${expected_version}, "
                "reported ${plugin_verify_output}"
            )
        endif()
    endif()

    set(${out_result} "${verify_result}" PARENT_SCOPE)
    set(${out_output} "${verify_output}" PARENT_SCOPE)
    set(${out_error} "${verify_error}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_python_environment_is_ready
    out_var
    environment
    fingerprint
    constraints_file
    expected_version
)
    set(environment_ready FALSE)
    set(ready_marker "${environment}/.protocyte-ready")
    _protocyte_python_environment_paths(
        python_executable
        plugin_executable
        "${environment}"
    )
    if(
        EXISTS "${ready_marker}"
        AND EXISTS "${python_executable}"
        AND EXISTS "${plugin_executable}"
    )
        file(READ "${ready_marker}" cached_fingerprint)
        string(STRIP "${cached_fingerprint}" cached_fingerprint)
        if(cached_fingerprint STREQUAL fingerprint)
            _protocyte_verify_python_environment(
                verify_result
                verify_output
                verify_error
                "${python_executable}"
                "${plugin_executable}"
                "${constraints_file}"
                "${expected_version}"
            )
            if("${verify_result}" STREQUAL "0")
                set(environment_ready TRUE)
            endif()
        endif()
    endif()
    set(${out_var} "${environment_ready}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_run_managed_environment_transaction
    out_result
    out_output
    python_executable
    destination
    fingerprint
    action
)
    get_property(
        transaction_helper
        GLOBAL
        PROPERTY PROTOCYTE_INTERNAL_MANAGED_ENVIRONMENT_HELPER
    )
    if(NOT EXISTS "${transaction_helper}")
        message(
            FATAL_ERROR
            "Protocyte's managed-environment transaction helper is missing: ${transaction_helper}"
        )
    endif()
    set(transaction_command
        "${CMAKE_COMMAND}"
        -E
        env
        "--unset=PYTHONPATH"
        "--unset=PYTHONHOME"
        "${python_executable}"
        -I
        "${transaction_helper}"
        "${action}"
        --destination "${destination}"
        --fingerprint "${fingerprint}"
    )
    if(ARGC GREATER 6)
        list(APPEND transaction_command --transaction "${ARGV6}")
    endif()
    execute_process(
        COMMAND ${transaction_command}
        RESULT_VARIABLE transaction_result
        OUTPUT_VARIABLE transaction_output
        ERROR_VARIABLE transaction_error
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_STRIP_TRAILING_WHITESPACE
        TIMEOUT 60
    )
    if(NOT transaction_error STREQUAL "")
        if(NOT transaction_output STREQUAL "")
            string(APPEND transaction_output "\n")
        endif()
        string(APPEND transaction_output "${transaction_error}")
    endif()
    set(${out_result} "${transaction_result}" PARENT_SCOPE)
    set(${out_output} "${transaction_output}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_rollback_python_environment
    out_result
    out_output
    python_executable
    environment
    fingerprint
    transaction
)
    _protocyte_run_managed_environment_transaction(
        rollback_result
        rollback_output
        "${python_executable}"
        "${environment}"
        "${fingerprint}"
        restore
        "${transaction}"
    )
    set(${out_result} "${rollback_result}" PARENT_SCOPE)
    set(${out_output} "${rollback_output}" PARENT_SCOPE)
endfunction()

function(_protocyte_python_provisioning_error action command_text result output error)
    string(STRIP "${output}" output)
    string(STRIP "${error}" error)
    if(output STREQUAL "")
        set(output "<no standard output>")
    endif()
    if(error STREQUAL "")
        set(error "<no standard error>")
    endif()
    message(
        FATAL_ERROR
        "Failed to ${action} for Protocyte's managed Python environment.\n\n"
        "Command:\n  ${command_text}\n"
        "Exit code: ${result}\n\n"
        "Standard output:\n${output}\n\n"
        "Standard error:\n${error}\n\n"
        "To manage the Python tooling externally, set PROTOCYTE_PLUGIN_EXECUTABLE to a compatible "
        "preinstalled Protocyte plugin before requesting code generation."
    )
endfunction()

function(_protocyte_ensure_python_environment out_python out_plugin)
    _protocyte_get_internal(cached_python MANAGED_PYTHON_EXECUTABLE)
    _protocyte_get_internal(cached_plugin MANAGED_PLUGIN_EXECUTABLE)
    if(EXISTS "${cached_python}" AND EXISTS "${cached_plugin}")
        set(${out_python} "${cached_python}" PARENT_SCOPE)
        set(${out_plugin} "${cached_plugin}" PARENT_SCOPE)
        return()
    endif()

    _protocyte_get_internal(protocyte_python_project_root PYTHON_PROJECT_ROOT)
    _protocyte_get_internal(protocyte_python_constraints PYTHON_CONSTRAINTS)
    _protocyte_get_internal(protocyte_python_env_root PYTHON_ENV_ROOT)
    _protocyte_get_internal(protocyte_expected_version VERSION)
    if(NOT IS_DIRECTORY "${protocyte_python_project_root}")
        message(FATAL_ERROR "Protocyte Python project root does not exist: ${protocyte_python_project_root}")
    endif()
    if(NOT EXISTS "${protocyte_python_project_root}/pyproject.toml")
        message(FATAL_ERROR "Protocyte Python project root is missing pyproject.toml: ${protocyte_python_project_root}")
    endif()
    if(NOT EXISTS "${protocyte_python_constraints}")
        message(FATAL_ERROR "Protocyte Python constraints file does not exist: ${protocyte_python_constraints}")
    endif()
    if("${protocyte_python_env_root}" STREQUAL "")
        message(FATAL_ERROR "Protocyte is missing PROTOCYTE_PYTHON_ENV_ROOT")
    endif()
    if("${protocyte_expected_version}" STREQUAL "")
        message(FATAL_ERROR "Protocyte's CMake package did not declare its expected plugin version")
    endif()

    find_package(Python3 3.12 COMPONENTS Interpreter REQUIRED)
    _protocyte_python_environment_fingerprint(
        protocyte_python_fingerprint
        "${protocyte_python_project_root}"
        "${protocyte_python_constraints}"
        "${Python3_EXECUTABLE}"
        "${Python3_VERSION}"
    )
    string(SUBSTRING "${protocyte_python_fingerprint}" 0 16 protocyte_python_fingerprint_short)
    set(protocyte_python_environment "${protocyte_python_env_root}/${protocyte_python_fingerprint_short}")
    set(protocyte_python_lock "${protocyte_python_env_root}/.${protocyte_python_fingerprint_short}.lock")
    _protocyte_python_environment_paths(
        protocyte_python_executable
        protocyte_plugin_executable
        "${protocyte_python_environment}"
    )

    file(MAKE_DIRECTORY "${protocyte_python_env_root}")
    file(
        LOCK
        "${protocyte_python_lock}"
        GUARD FUNCTION
        RESULT_VARIABLE lock_result
        TIMEOUT 900
    )
    if(NOT "${lock_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Failed to acquire the Protocyte managed Python environment lock: ${lock_result}\n"
            "Lock: ${protocyte_python_lock}"
        )
    endif()

    _protocyte_run_managed_environment_transaction(
        recovery_result
        recovery_output
        "${Python3_EXECUTABLE}"
        "${protocyte_python_environment}"
        "${protocyte_python_fingerprint}"
        recover
    )
    if(NOT "${recovery_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Failed to recover Protocyte's managed Python environment transaction.\n\n"
            "Environment: ${protocyte_python_environment}\n\n"
            "Details:\n${recovery_output}\n\n"
            "The live environment and any unverified transaction were left unchanged. Inspect them "
            "before retrying."
        )
    endif()

    _protocyte_python_environment_is_ready(
        protocyte_python_environment_ready
        "${protocyte_python_environment}"
        "${protocyte_python_fingerprint}"
        "${protocyte_python_constraints}"
        "${protocyte_expected_version}"
    )

    if(NOT protocyte_python_environment_ready)
        _protocyte_run_managed_environment_transaction(
            transaction_result
            protocyte_python_transaction
            "${Python3_EXECUTABLE}"
            "${protocyte_python_environment}"
            "${protocyte_python_fingerprint}"
            create
        )
        if(NOT "${transaction_result}" STREQUAL "0")
            message(
                FATAL_ERROR
                "Failed to create a transaction for Protocyte's managed Python environment.\n\n"
                "Environment: ${protocyte_python_environment}\n\n"
                "Details:\n${protocyte_python_transaction}"
            )
        endif()
        string(STRIP "${protocyte_python_transaction}" protocyte_python_transaction)

        message(STATUS "Provisioning Protocyte Python environment: ${protocyte_python_environment}")
        set(protocyte_python_staging "${protocyte_python_transaction}/staging")
        _protocyte_python_environment_paths(
            protocyte_staged_python_executable
            protocyte_staged_plugin_executable
            "${protocyte_python_staging}"
        )
        if(WIN32)
            set(protocyte_disabled_pip_config "NUL")
        else()
            set(protocyte_disabled_pip_config "/dev/null")
        endif()
        set(venv_arguments -m venv "${protocyte_python_staging}")
        execute_process(
            COMMAND
                "${CMAKE_COMMAND}" -E env
                "--unset=PIP_TARGET"
                "--unset=PIP_PREFIX"
                "--unset=PIP_ROOT"
                "--unset=PIP_USER"
                "--unset=PIP_PYTHON"
                "--unset=PIP_QUIET"
                "--unset=PIP_REQUIREMENT"
                "--unset=PIP_EDITABLE"
                "--unset=PIP_GROUP"
                "--unset=PIP_REQUIREMENTS_FROM_SCRIPT"
                "--unset=PYTHONUSERBASE"
                "--unset=PYTHONPATH"
                "--unset=PYTHONHOME"
                "PIP_ISOLATED=0"
                "PIP_CONFIG_FILE=${protocyte_disabled_pip_config}"
                "${Python3_EXECUTABLE}" -I ${venv_arguments}
            RESULT_VARIABLE venv_result
            OUTPUT_VARIABLE venv_output
            ERROR_VARIABLE venv_error
            TIMEOUT 120
        )
        if(NOT "${venv_result}" STREQUAL "0")
            string(JOIN " " venv_command ${venv_arguments})
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND venv_error "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "create the virtual environment; ensure the selected Python provides venv and ensurepip"
                "\"${Python3_EXECUTABLE}\" ${venv_command}"
                "${venv_result}"
                "${venv_output}"
                "${venv_error}"
            )
        endif()

        _protocyte_check_managed_pip_configuration(
            configuration_result
            configuration_error
            "${protocyte_staged_python_executable}"
        )
        if(NOT "${configuration_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND configuration_error "\nFailed to clean up the staging environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "validate pip configuration for the managed Python environment"
                "\"${protocyte_staged_python_executable}\" -c pip-configuration-inspection"
                "${configuration_result}"
                ""
                "${configuration_error}"
            )
        endif()

        if(EXISTS "${protocyte_python_environment}")
            _protocyte_run_managed_environment_transaction(
                backup_result
                backup_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                backup
                "${protocyte_python_transaction}"
            )
            if(NOT "${backup_result}" STREQUAL "0")
                message(
                    FATAL_ERROR
                    "Failed to preserve the identity-bound backup of Protocyte's managed Python environment "
                    "before provisioning its replacement.\n\n"
                    "Environment: ${protocyte_python_environment}\n\n"
                    "Details:\n${backup_output}\n\n"
                    "The live environment and transaction were left unchanged."
                )
            endif()
        endif()

        set(protocyte_staged_project "${protocyte_python_staging}/project")
        set(protocyte_staged_constraints "${protocyte_staged_project}/protocyte-cmake-constraints.txt")
        _protocyte_stage_python_project(
            "${protocyte_python_project_root}"
            "${protocyte_python_constraints}"
            "${protocyte_staged_project}"
        )

        _protocyte_run_managed_pip(
            bootstrap_result
            bootstrap_output
            bootstrap_error
            300
            "${protocyte_staged_python_executable}"
            --no-build-isolation
            --upgrade
            --force-reinstall
            --only-binary=:all:
            --require-hashes
            --requirement "${protocyte_staged_constraints}"
        )
        if(NOT "${bootstrap_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND bootstrap_error "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "install Protocyte's pinned Python build tools"
                "\"${protocyte_staged_python_executable}\" -m pip install --disable-pip-version-check --no-input --no-build-isolation --upgrade --force-reinstall --only-binary=:all: --require-hashes --requirement \"${protocyte_staged_constraints}\""
                "${bootstrap_result}"
                "${bootstrap_output}"
                "${bootstrap_error}"
            )
        endif()

        _protocyte_run_managed_pip(
            install_result
            install_output
            install_error
            300
            "${protocyte_staged_python_executable}"
            --no-build-isolation
            --upgrade
            --force-reinstall
            --no-deps
            "${protocyte_staged_project}"
        )
        if(NOT "${install_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND install_error "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "install Protocyte and its Python dependencies"
                "\"${protocyte_staged_python_executable}\" -m pip install --disable-pip-version-check --no-input --no-build-isolation --upgrade --force-reinstall --no-deps \"${protocyte_staged_project}\""
                "${install_result}"
                "${install_output}"
                "${install_error}"
            )
        endif()

        _protocyte_verify_python_environment(
            verify_result
            verify_output
            verify_error
            "${protocyte_staged_python_executable}"
            "${protocyte_staged_plugin_executable}"
            "${protocyte_python_constraints}"
            "${protocyte_expected_version}"
        )
        if(NOT "${verify_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND verify_error "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "verify the installed Protocyte plugin"
                "\"${protocyte_staged_plugin_executable}\" --version"
                "${verify_result}"
                "${verify_output}"
                "${verify_error}"
            )
        endif()

        file(
            WRITE
            "${protocyte_python_staging}/.protocyte-ready"
            "${protocyte_python_fingerprint}\n"
        )
        _protocyte_run_managed_environment_transaction(
            prepare_result
            prepare_output
            "${Python3_EXECUTABLE}"
            "${protocyte_python_environment}"
            "${protocyte_python_fingerprint}"
            prepare
            "${protocyte_python_transaction}"
        )
        if(NOT "${prepare_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND prepare_output "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "prepare the verified Protocyte Python environment for promotion"
                "${Python3_EXECUTABLE} ${PROTOCYTE_INTERNAL_MANAGED_ENVIRONMENT_HELPER} prepare"
                "${prepare_result}"
                ""
                "${prepare_output}"
            )
        endif()
        _protocyte_run_managed_environment_transaction(
            promote_result
            promote_output
            "${Python3_EXECUTABLE}"
            "${protocyte_python_environment}"
            "${protocyte_python_fingerprint}"
            promote
            "${protocyte_python_transaction}"
        )
        if(NOT "${promote_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND promote_output "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "promote the verified Protocyte Python environment"
                "${Python3_EXECUTABLE} ${PROTOCYTE_INTERNAL_MANAGED_ENVIRONMENT_HELPER} promote"
                "${promote_result}"
                ""
                "${promote_output}"
            )
        endif()
        _protocyte_run_managed_pip(
            relocation_result
            relocation_output
            relocation_error
            120
            "${protocyte_python_executable}"
            --no-build-isolation
            --no-deps
            --force-reinstall
            "${protocyte_python_environment}/project"
        )
        if(NOT "${relocation_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND relocation_error "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "rewrite the managed Protocyte plugin entry point after promotion"
                "\"${protocyte_python_executable}\" -m pip install --disable-pip-version-check --no-input --no-build-isolation --no-deps --force-reinstall \"${protocyte_python_environment}/project\""
                "${relocation_result}"
                "${relocation_output}"
                "${relocation_error}"
            )
        endif()
        _protocyte_verify_python_environment(
            relocated_verify_result
            relocated_verify_output
            relocated_verify_error
            "${protocyte_python_executable}"
            "${protocyte_plugin_executable}"
            "${protocyte_python_constraints}"
            "${protocyte_expected_version}"
        )
        if(NOT "${relocated_verify_result}" STREQUAL "0")
            _protocyte_rollback_python_environment(
                rollback_result
                rollback_output
                "${Python3_EXECUTABLE}"
                "${protocyte_python_environment}"
                "${protocyte_python_fingerprint}"
                "${protocyte_python_transaction}"
            )
            if(NOT "${rollback_result}" STREQUAL "0")
                string(APPEND relocated_verify_error "\nFailed to restore the previous environment: ${rollback_output}")
            endif()
            _protocyte_python_provisioning_error(
                "verify the promoted Protocyte Python environment"
                "\"${protocyte_plugin_executable}\" --version"
                "${relocated_verify_result}"
                "${relocated_verify_output}"
                "${relocated_verify_error}"
            )
        endif()
        _protocyte_run_managed_environment_transaction(
            commit_result
            commit_output
            "${Python3_EXECUTABLE}"
            "${protocyte_python_environment}"
            "${protocyte_python_fingerprint}"
            commit
            "${protocyte_python_transaction}"
        )
        if(NOT "${commit_result}" STREQUAL "0")
            message(
                FATAL_ERROR
                "Protocyte verified its promoted managed Python environment but could not commit the "
                "transaction. A later configure will recover from the identity-bound backup.\n\n"
                "Environment: ${protocyte_python_environment}\n\n"
                "Details:\n${commit_output}"
            )
        endif()
        _protocyte_run_managed_environment_transaction(
            cleanup_result
            cleanup_output
            "${Python3_EXECUTABLE}"
            "${protocyte_python_environment}"
            "${protocyte_python_fingerprint}"
            cleanup
            "${protocyte_python_transaction}"
        )
        if(NOT "${cleanup_result}" STREQUAL "0")
            message(
                FATAL_ERROR
                "Protocyte promoted its managed Python environment but could not retire the verified "
                "transaction. A later configure will retry without touching unverified paths.\n\n"
                "Environment: ${protocyte_python_environment}\n\n"
                "Details:\n${cleanup_output}"
            )
        endif()
    endif()

    set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_MANAGED_PYTHON_EXECUTABLE "${protocyte_python_executable}")
    set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_MANAGED_PLUGIN_EXECUTABLE "${protocyte_plugin_executable}")
    set(${out_python} "${protocyte_python_executable}" PARENT_SCOPE)
    set(${out_plugin} "${protocyte_plugin_executable}" PARENT_SCOPE)
endfunction()

function(_protocyte_resolve_stable_filesystem_path out_var candidate namespace)
    if(IS_ABSOLUTE "${candidate}")
        cmake_path(NORMAL_PATH candidate OUTPUT_VARIABLE resolved_candidate)
    else()
        string(SHA256 candidate_key "${namespace}|${candidate}")
        set(property_name "PROTOCYTE_INTERNAL_RESOLVED_${namespace}_${candidate_key}")
        get_property(candidate_was_resolved GLOBAL PROPERTY "${property_name}" SET)
        if(candidate_was_resolved)
            get_property(resolved_candidate GLOBAL PROPERTY "${property_name}")
        else()
            cmake_path(
                ABSOLUTE_PATH candidate
                BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                NORMALIZE
                OUTPUT_VARIABLE resolved_candidate
            )
            set_property(GLOBAL PROPERTY "${property_name}" "${resolved_candidate}")
        endif()
    endif()

    set(${out_var} "${resolved_candidate}" PARENT_SCOPE)
endfunction()

function(_protocyte_set_resolved_protobuf_import_dir candidate_dir)
    set(
        PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR
        "${candidate_dir}"
        CACHE INTERNAL
        "resolved protobuf import root for the active protocyte toolchain"
    )
endfunction()

function(_protocyte_set_protobuf_import_dir candidate_dir toolchain_identity)
    if("${candidate_dir}" STREQUAL "")
        return()
    endif()

    cmake_path(ABSOLUTE_PATH candidate_dir NORMALIZE OUTPUT_VARIABLE candidate_dir)

    if(NOT IS_DIRECTORY "${candidate_dir}")
        return()
    endif()

    if(
        NOT EXISTS "${candidate_dir}/google/protobuf/descriptor.proto"
        OR IS_DIRECTORY "${candidate_dir}/google/protobuf/descriptor.proto"
    )
        return()
    endif()

    set(
        PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR
        "${candidate_dir}"
        CACHE INTERNAL
        "automatically discovered protobuf import root"
    )
    set(
        PROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN
        "${toolchain_identity}"
        CACHE INTERNAL
        "toolchain associated with the automatically discovered protobuf import root"
    )
    unset(PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR CACHE)
    _protocyte_set_resolved_protobuf_import_dir("${candidate_dir}")
endfunction()

function(_protocyte_resolve_protobuf_import_dir out_explicit toolchain_identity)
    set(${out_explicit} FALSE PARENT_SCOPE)
    unset(PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR CACHE)
    unset(PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR CACHE)
    set(protobuf_toolchain_changed FALSE)

    set(auto_import_dir "${PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR}")
    set(configured_import_dir "${PROTOCYTE_PROTOBUF_IMPORT_DIR}")
    if(NOT configured_import_dir STREQUAL "")
        _protocyte_resolve_stable_filesystem_path(
            resolved_configured_import_dir
            "${configured_import_dir}"
            PROTOBUF_IMPORT
        )

        set(migrate_legacy_auto_import FALSE)
        if(
            NOT auto_import_dir STREQUAL ""
            AND resolved_configured_import_dir STREQUAL auto_import_dir
            AND DEFINED CACHE{PROTOCYTE_PROTOBUF_IMPORT_DIR}
        )
            get_property(
                configured_import_cache_type
                CACHE PROTOCYTE_PROTOBUF_IMPORT_DIR
                PROPERTY TYPE
            )
            if(configured_import_cache_type STREQUAL "INTERNAL")
                set(migrate_legacy_auto_import TRUE)
            endif()
        endif()

        if(migrate_legacy_auto_import)
            # Older Protocyte releases exposed automatically discovered roots
            # through the public cache entry. Remove that legacy mirror so any
            # new public value is unambiguously caller-owned. A typed cache
            # override (for example :PATH) remains explicit even when it names
            # the same directory as the previous automatic root.
            unset(PROTOCYTE_PROTOBUF_IMPORT_DIR CACHE)
        else()
            if(NOT IS_DIRECTORY "${resolved_configured_import_dir}")
                message(
                    FATAL_ERROR
                    "PROTOCYTE_PROTOBUF_IMPORT_DIR '${configured_import_dir}' resolves to "
                    "'${resolved_configured_import_dir}', which is not an existing directory"
                )
            endif()
            if(NOT EXISTS "${resolved_configured_import_dir}/google/protobuf/descriptor.proto")
                message(
                    FATAL_ERROR
                    "PROTOCYTE_PROTOBUF_IMPORT_DIR '${configured_import_dir}' resolves to "
                    "'${resolved_configured_import_dir}', but that directory does not contain "
                    "google/protobuf/descriptor.proto"
                )
            endif()
            if(IS_DIRECTORY "${resolved_configured_import_dir}/google/protobuf/descriptor.proto")
                message(
                    FATAL_ERROR
                    "PROTOCYTE_PROTOBUF_IMPORT_DIR '${configured_import_dir}' resolves to "
                    "'${resolved_configured_import_dir}', but "
                    "'${resolved_configured_import_dir}/google/protobuf/descriptor.proto' is a directory; "
                    "an existing file is required"
                )
            endif()
            set(${out_explicit} TRUE PARENT_SCOPE)
            _protocyte_set_resolved_protobuf_import_dir("${resolved_configured_import_dir}")
            return()
        endif()
    endif()

    if(NOT auto_import_dir STREQUAL "")
        if(
            "${PROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN}" STREQUAL "${toolchain_identity}"
            AND EXISTS "${auto_import_dir}/google/protobuf/descriptor.proto"
            AND NOT IS_DIRECTORY "${auto_import_dir}/google/protobuf/descriptor.proto"
        )
            _protocyte_set_resolved_protobuf_import_dir("${auto_import_dir}")
            return()
        endif()

        if(NOT "${PROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN}" STREQUAL "${toolchain_identity}")
            set(protobuf_toolchain_changed TRUE)
            set(
                PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR
                "${auto_import_dir}"
                CACHE INTERNAL
                "protobuf import root associated with the previously selected protoc toolchain"
            )
        endif()
        unset(PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR CACHE)
        unset(PROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN CACHE)
    endif()

    set(protoc_import_executable "${PROTOCYTE_PROTOC_EXECUTABLE}")
    if(NOT protoc_import_executable STREQUAL "" AND NOT protoc_import_executable MATCHES "\\$<")
        cmake_path(GET protoc_import_executable PARENT_PATH protoc_bin_dir)
        _protocyte_set_protobuf_import_dir(
            "${protoc_bin_dir}/../include"
            "${toolchain_identity}"
        )
        if(DEFINED PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR)
            return()
        endif()
    endif()

    if(protobuf_toolchain_changed)
        # Protobuf_INCLUDE_DIRS, protobuf_SOURCE_DIR, and protobuf library targets
        # may still describe the previous toolchain. Reusing those values would
        # silently pair a new compiler with stale import definitions. Callers can
        # opt into a shared root through PROTOCYTE_PROTOBUF_IMPORT_DIR, while the
        # fetch fallback below provides a package-controlled shared source tree.
        return()
    endif()

    if(DEFINED protobuf_SOURCE_DIR AND EXISTS "${protobuf_SOURCE_DIR}/src/google/protobuf/descriptor.proto")
        _protocyte_set_protobuf_import_dir(
            "${protobuf_SOURCE_DIR}/src"
            "${toolchain_identity}"
        )
        return()
    endif()

    if(DEFINED Protobuf_INCLUDE_DIRS)
        foreach(include_dir IN LISTS Protobuf_INCLUDE_DIRS)
            _protocyte_set_protobuf_import_dir(
                "${include_dir}"
                "${toolchain_identity}"
            )
            if(DEFINED PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR)
                return()
            endif()
        endforeach()
    endif()

    foreach(target_name IN ITEMS protobuf::libprotobuf libprotobuf)
        if(NOT TARGET "${target_name}")
            continue()
        endif()

        get_target_property(target_include_dirs "${target_name}" INTERFACE_INCLUDE_DIRECTORIES)
        if(NOT target_include_dirs)
            continue()
        endif()

        foreach(include_dir IN LISTS target_include_dirs)
            if(include_dir MATCHES "^\\$<")
                continue()
            endif()

            _protocyte_set_protobuf_import_dir(
                "${include_dir}"
                "${toolchain_identity}"
            )
            if(DEFINED PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR)
                return()
            endif()
        endforeach()
    endforeach()
endfunction()

function(_protocyte_resolve_protoc_path out_executable out_dependency candidate)
    if("${candidate}" MATCHES "\\$<")
        set(${out_executable} "${candidate}" PARENT_SCOPE)
        set(${out_dependency} "${candidate}" PARENT_SCOPE)
        return()
    endif()

    _protocyte_resolve_stable_filesystem_path(
        resolved_candidate
        "${candidate}"
        PROTOC
    )
    if(NOT EXISTS "${resolved_candidate}" OR IS_DIRECTORY "${resolved_candidate}")
        message(
            FATAL_ERROR
            "Protobuf_PROTOC_EXECUTABLE '${candidate}' resolves to '${resolved_candidate}', "
            "which does not name an existing file"
        )
    endif()

    set(${out_executable} "${resolved_candidate}" PARENT_SCOPE)
    set(${out_dependency} "${resolved_candidate}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_try_host_protoc_path
    out_available
    out_executable
    out_diagnostic
    candidate
    source_description
)
    set(${out_available} FALSE PARENT_SCOPE)
    set(${out_executable} "" PARENT_SCOPE)

    if("${candidate}" MATCHES "\\$<")
        string(
            CONCAT candidate_diagnostic
            "${source_description} uses a generator expression, which cannot carry a "
            "cross-compiling emulator through Protocyte's generation scripts"
        )
        set(${out_diagnostic} "${candidate_diagnostic}" PARENT_SCOPE)
        return()
    endif()

    if(IS_ABSOLUTE "${candidate}")
        cmake_path(NORMAL_PATH candidate OUTPUT_VARIABLE resolved_candidate)
    else()
        cmake_path(
            ABSOLUTE_PATH candidate
            BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            NORMALIZE
            OUTPUT_VARIABLE resolved_candidate
        )
    endif()
    if(NOT EXISTS "${resolved_candidate}" OR IS_DIRECTORY "${resolved_candidate}")
        set(
            ${out_diagnostic}
            "${source_description} resolves to '${resolved_candidate}', which does not name an existing file"
            PARENT_SCOPE
        )
        return()
    endif()

    execute_process(
        COMMAND "${resolved_candidate}" --version
        RESULT_VARIABLE version_result
        OUTPUT_VARIABLE version_output
        ERROR_VARIABLE version_error
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_STRIP_TRAILING_WHITESPACE
        TIMEOUT 15
    )
    if(NOT "${version_result}" STREQUAL "0")
        if(version_error STREQUAL "")
            if(version_output STREQUAL "")
                set(version_error "<no output>")
            else()
                set(version_error "${version_output}")
            endif()
        endif()
        set(
            ${out_diagnostic}
            "${source_description} is not host-runnable (${version_result}): ${resolved_candidate}; ${version_error}"
            PARENT_SCOPE
        )
        return()
    endif()

    set(${out_available} TRUE PARENT_SCOPE)
    set(${out_executable} "${resolved_candidate}" PARENT_SCOPE)
    set(${out_diagnostic} "" PARENT_SCOPE)
endfunction()

function(_protocyte_find_host_protoc_on_path out_executable)
    set(host_path_protoc "host_path_protoc-NOTFOUND")
    if(NOT "$ENV{PATH}" STREQUAL "")
        cmake_path(
            CONVERT "$ENV{PATH}"
            TO_CMAKE_PATH_LIST host_program_directories
            NORMALIZE
        )
        find_program(
            host_path_protoc
            NAMES protoc
            PATHS ${host_program_directories}
            NO_DEFAULT_PATH
            NO_CACHE
        )
    endif()
    set(${out_executable} "${host_path_protoc}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_try_imported_host_protoc_target
    out_available
    out_executable
    out_diagnostic
    target_name
)
    set(${out_available} FALSE PARENT_SCOPE)
    set(${out_executable} "" PARENT_SCOPE)

    get_target_property(target_is_imported "${target_name}" IMPORTED)
    if(NOT target_is_imported)
        set(
            ${out_diagnostic}
            "target '${target_name}' is built by the target toolchain and has no configure-time host executable"
            PARENT_SCOPE
        )
        return()
    endif()

    # Generated outputs are shared by all project configurations, so select one
    # concrete imported tool using the generator's default configuration.
    set(project_configuration "")
    if(NOT "${CMAKE_BUILD_TYPE}" STREQUAL "")
        set(project_configuration "${CMAKE_BUILD_TYPE}")
    elseif(NOT "${CMAKE_DEFAULT_BUILD_TYPE}" STREQUAL "")
        set(project_configuration "${CMAKE_DEFAULT_BUILD_TYPE}")
    elseif(CMAKE_CONFIGURATION_TYPES)
        list(GET CMAKE_CONFIGURATION_TYPES 0 project_configuration)
    endif()

    if(project_configuration STREQUAL "")
        set(location_property LOCATION)
        set(location_description "target '${target_name}'")
    else()
        string(TOUPPER "${project_configuration}" project_configuration_upper)
        set(location_property "LOCATION_${project_configuration_upper}")
        set(
            location_description
            "target '${target_name}' for project configuration '${project_configuration}'"
        )
    endif()
    get_target_property(imported_location "${target_name}" "${location_property}")

    if(imported_location)
        _protocyte_try_host_protoc_path(
            location_is_host_runnable
            resolved_imported_location
            target_diagnostic
            "${imported_location}"
            "${location_description}"
        )
        if(location_is_host_runnable)
            set(${out_available} TRUE PARENT_SCOPE)
            set(${out_executable} "${resolved_imported_location}" PARENT_SCOPE)
            set(${out_diagnostic} "" PARENT_SCOPE)
            return()
        endif()
    else()
        set(
            target_diagnostic
            "${location_description} does not expose an imported executable location"
        )
    endif()

    get_target_property(target_emulator "${target_name}" CROSSCOMPILING_EMULATOR)
    if(target_emulator)
        string(
            APPEND
            target_diagnostic
            "; CROSSCOMPILING_EMULATOR is set, but Protocyte cannot propagate target "
            "emulators through its dependency-scan and generation scripts"
        )
    endif()
    set(${out_diagnostic} "${target_diagnostic}" PARENT_SCOPE)
endfunction()

function(_protocyte_fetch_protobuf_import_sources toolchain_identity)
    FetchContent_Declare(
        protocyte_protobuf_imports
        GIT_REPOSITORY https://github.com/protocolbuffers/protobuf.git
        GIT_TAG "${PROTOCYTE_PROTOBUF_GIT_TAG}"
        SOURCE_SUBDIR _protocyte_import_sources_only
    )
    FetchContent_MakeAvailable(protocyte_protobuf_imports)
    FetchContent_GetProperties(
        protocyte_protobuf_imports
        SOURCE_DIR protocyte_protobuf_imports_source_dir
    )
    _protocyte_set_protobuf_import_dir(
        "${protocyte_protobuf_imports_source_dir}/src"
        "${toolchain_identity}"
    )
endfunction()

function(
    _protocyte_decode_hex_string
    out_var
    encoded_value
)
    string(LENGTH "${encoded_value}" encoded_length)
    set(decoded_value "")
    if(encoded_length GREATER 0)
        math(EXPR encoded_last "${encoded_length} - 2")
        foreach(offset RANGE 0 ${encoded_last} 2)
            string(SUBSTRING "${encoded_value}" ${offset} 2 encoded_byte)
            math(EXPR byte_value "0x${encoded_byte}")
            string(ASCII ${byte_value} decoded_character)
            string(APPEND decoded_value "${decoded_character}")
        endforeach()
    endif()
    set(${out_var} "${decoded_value}" PARENT_SCOPE)
endfunction()

function(_protocyte_append_configure_dependency dependency_path)
    string(REPLACE ";" "\\;" escaped_dependency_path "${dependency_path}")
    set_property(
        DIRECTORY
        APPEND
        PROPERTY CMAKE_CONFIGURE_DEPENDS "${escaped_dependency_path}"
    )
endfunction()

function(_protocyte_write_if_different output_path output_content)
    set(write_output TRUE)
    if(EXISTS "${output_path}")
        file(READ "${output_path}" existing_output_content)
        if(existing_output_content STREQUAL output_content)
            set(write_output FALSE)
        endif()
    endif()
    if(write_output)
        file(WRITE "${output_path}" "${output_content}")
    endif()
endfunction()

function(
    _protocyte_run_source_import_scan
    out_requires_protobuf_imports
    out_scan_key
    out_scan_lines
    out_has_unwatchable_source
    source_files_var
    encoded_import_roots_var
)
    # Scan the complete selected source closure in one bounded host process.
    # Request paths stay hex-encoded so semicolons and non-ASCII paths never
    # cross a CMake list or command-line boundary.
    set(import_scan_request_content "version=1\n")
    foreach(encoded_import_root IN LISTS ${encoded_import_roots_var})
        string(APPEND import_scan_request_content "root ${encoded_import_root}\n")
    endforeach()
    foreach(source_file IN LISTS ${source_files_var})
        string(HEX "${source_file}" encoded_source_file)
        string(APPEND import_scan_request_content "source ${encoded_source_file}\n")
    endforeach()

    _protocyte_prepare_plugin()
    _protocyte_get_internal(import_scan_plugin PLUGIN_EXECUTABLE)
    _protocyte_get_internal(import_scan_plugin_is_managed PLUGIN_IS_MANAGED)
    if("${import_scan_plugin_is_managed}" STREQUAL "")
        set(import_scan_plugin_is_managed FALSE)
    endif()
    _protocyte_get_internal(import_scan_command IMPORT_SCAN_COMMAND)
    if("${import_scan_command}" STREQUAL "")
        set(import_scan_command "_cmake-import-scan-v1")
    endif()
    if("${import_scan_plugin}" STREQUAL "")
        message(FATAL_ERROR "Protocyte source import scanning requires a prepared plugin")
    endif()
    _protocyte_get_internal(import_scanner IMPORT_SCANNER)
    if("${import_scanner}" STREQUAL "")
        set(
            import_scanner
            "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../src/protocyte/import_scanner.py"
        )
    endif()
    if(NOT EXISTS "${import_scanner}")
        message(FATAL_ERROR "Protocyte import scanner source does not exist: ${import_scanner}")
    endif()
    cmake_path(GET import_scanner PARENT_PATH import_scan_package_dir)
    set(import_scan_entrypoint "${import_scan_package_dir}/main.py")
    if(NOT EXISTS "${import_scan_entrypoint}")
        message(FATAL_ERROR "Protocyte plugin entry point does not exist: ${import_scan_entrypoint}")
    endif()
    _protocyte_append_configure_dependency("${import_scan_plugin}")
    _protocyte_append_configure_dependency("${import_scanner}")
    _protocyte_append_configure_dependency("${import_scan_entrypoint}")
    set(import_scan_launcher "${import_scan_plugin}")
    if(import_scan_plugin_is_managed)
        set(
            import_scan_launcher
            "${CMAKE_COMMAND}"
            -E
            env
            --unset=PYTHONHOME
            --unset=PYTHONPATH
            "${import_scan_plugin}"
        )
    endif()
    string(SHA256 import_scan_key "${import_scan_request_content}")
    set(
        import_scan_request_dir
        "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-import-scans"
    )
    set(import_scan_request "${import_scan_request_dir}/${import_scan_key}.request")
    file(MAKE_DIRECTORY "${import_scan_request_dir}")
    set(write_import_scan_request TRUE)
    if(EXISTS "${import_scan_request}")
        file(READ "${import_scan_request}" existing_import_scan_request)
        if(existing_import_scan_request STREQUAL import_scan_request_content)
            set(write_import_scan_request FALSE)
        endif()
    endif()
    if(write_import_scan_request)
        file(WRITE "${import_scan_request}" "${import_scan_request_content}")
    endif()

    _protocyte_execute_bounded(
        import_scan_result
        import_scan_output
        import_scan_error
        import_scan_timed_out
        COMMAND
            ${import_scan_launcher}
            "${import_scan_command}"
            "${import_scan_request}"
    )
    string(REPLACE "\r\n" "\n" import_scan_output "${import_scan_output}")
    string(REPLACE "\r" "\n" import_scan_output "${import_scan_output}")
    string(STRIP "${import_scan_output}" import_scan_output)
    string(STRIP "${import_scan_error}" import_scan_error)
    if(import_scan_timed_out)
        message(
            FATAL_ERROR
            "Protocyte source import scan through '${import_scan_plugin}' timed out after "
            "${PROTOCYTE_TOOL_TIMEOUT_SECONDS} seconds. Set PROTOCYTE_TOOL_TIMEOUT_SECONDS "
            "to a larger value or 0 to disable this timeout."
        )
    endif()
    if(NOT import_scan_result EQUAL 0)
        message(
            FATAL_ERROR
            "Protocyte source import scan through '${import_scan_plugin}' failed with exit code "
            "${import_scan_result}: ${import_scan_error}\n"
            "PROTOCYTE_PLUGIN_EXECUTABLE overrides must name the actual version-matched "
            "Protocyte plugin with ${import_scan_command} support."
        )
    endif()
    string(REPLACE "\n" ";" import_scan_lines "${import_scan_output}")
    list(LENGTH import_scan_lines import_scan_line_count)
    if(import_scan_line_count LESS 2)
        message(
            FATAL_ERROR
            "Protocyte plugin '${import_scan_plugin}' returned an invalid ${import_scan_command} "
            "result: '${import_scan_output}'. PROTOCYTE_PLUGIN_EXECUTABLE overrides must name "
            "the actual version-matched Protocyte plugin."
        )
    endif()
    list(POP_FRONT import_scan_lines import_scan_result_line)
    if(import_scan_result_line STREQUAL "result TRUE")
        set(requires_protobuf_import_sources TRUE)
    elseif(import_scan_result_line STREQUAL "result FALSE")
        set(requires_protobuf_import_sources FALSE)
    else()
        message(
            FATAL_ERROR
            "Protocyte plugin '${import_scan_plugin}' returned an invalid ${import_scan_command} "
            "result: '${import_scan_output}'. PROTOCYTE_PLUGIN_EXECUTABLE overrides must name "
            "the actual version-matched Protocyte plugin."
        )
    endif()

    set(has_unwatchable_source FALSE)
    foreach(import_scan_line IN LISTS import_scan_lines)
        if(import_scan_line MATCHES "^source ([0-9a-f]+) (-|[0-9a-f]+)$")
            if(CMAKE_MATCH_2 STREQUAL "-")
                set(has_unwatchable_source TRUE)
            endif()
        elseif(import_scan_line MATCHES "^edge ([0-9a-f]+) (-|[0-9a-f]+)$")
        elseif(
            import_scan_line
            MATCHES "^candidate ([0-9a-f]+) (-|[0-9a-f]+) (-|[0-9a-f]+)$"
        )
        elseif(
            import_scan_line
            MATCHES "^(watch|watch-source) ([0-9a-f]+) ([0-9a-f]+)$"
        )
        else()
            message(
                FATAL_ERROR
                "Protocyte import scanner returned an invalid result: '${import_scan_output}'"
            )
        endif()
    endforeach()
    set(${out_requires_protobuf_imports} "${requires_protobuf_import_sources}" PARENT_SCOPE)
    set(${out_scan_key} "${import_scan_key}" PARENT_SCOPE)
    set(${out_scan_lines} "${import_scan_lines}" PARENT_SCOPE)
    set(${out_has_unwatchable_source} "${has_unwatchable_source}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_register_source_import_scan
    out_topology_dependencies
    out_source_check_targets
    import_scan_key
    import_scan_lines_var
)
    set(topology_witness_content "version=1\n")
    set(topology_runtime_witness_content "version=1\n")
    set(source_check_targets)
    set(registered_candidate_identities)
    set(registered_watch_identities)
    foreach(import_scan_line IN LISTS ${import_scan_lines_var})
        if(import_scan_line MATCHES "^source ([0-9a-f]+) (-|[0-9a-f]+)$")
            set(encoded_source "${CMAKE_MATCH_1}")
            set(encoded_dependency "${CMAKE_MATCH_2}")
            _protocyte_decode_hex_string(import_scan_source "${encoded_source}")
            if(encoded_dependency STREQUAL "-")
                _protocyte_get_source_dependency_proxy(
                    import_scan_dependency
                    import_scan_check_target
                    "${import_scan_source}"
                )
                _protocyte_append_configure_dependency("${import_scan_dependency}")
                list(APPEND source_check_targets "${import_scan_check_target}")
            else()
                _protocyte_decode_hex_string(
                    import_scan_dependency
                    "${encoded_dependency}"
                )
                _protocyte_append_configure_dependency("${import_scan_dependency}")
            endif()
        elseif(import_scan_line MATCHES "^edge ([0-9a-f]+) (-|[0-9a-f]+)$")
            string(APPEND topology_witness_content "${import_scan_line}\n")
        elseif(
            import_scan_line
            MATCHES "^candidate ([0-9a-f]+) (-|[0-9a-f]+) (-|[0-9a-f]+)$"
        )
            set(encoded_candidate "${CMAKE_MATCH_1}")
            set(encoded_pattern "${CMAKE_MATCH_2}")
            set(encoded_dependency "${CMAKE_MATCH_3}")
            _protocyte_decode_hex_string(import_candidate "${encoded_candidate}")
            set(candidate_identity "${import_candidate}")
            if(CMAKE_HOST_WIN32)
                string(TOLOWER "${candidate_identity}" candidate_identity)
            endif()
            string(SHA256 candidate_identity_hash "${candidate_identity}")
            if("${candidate_identity_hash}" IN_LIST registered_candidate_identities)
                continue()
            endif()
            list(APPEND registered_candidate_identities "${candidate_identity_hash}")

            if(NOT encoded_pattern STREQUAL "-")
                _protocyte_decode_hex_string(import_candidate_pattern "${encoded_pattern}")
                # Keep a raw semicolon inside this one quoted scalar. Escaping it
                # changes the glob expression; the result is intentionally
                # discarded because CMake list rendering cannot preserve such a
                # path even though CONFIGURE_DEPENDS can watch it correctly.
                file(
                    GLOB ignored_import_candidate
                    LIST_DIRECTORIES FALSE
                    CONFIGURE_DEPENDS
                    "${import_candidate_pattern}"
                )
            endif()
        elseif(
            import_scan_line
            MATCHES "^(watch|watch-source) ([0-9a-f]+) ([0-9a-f]+)$"
        )
            set(watch_kind "${CMAKE_MATCH_1}")
            set(encoded_watch_path "${CMAKE_MATCH_2}")
            set(encoded_watch_identity "${CMAKE_MATCH_3}")
            _protocyte_decode_hex_string(watch_path "${encoded_watch_path}")
            set(watch_path_identity "${watch_path}")
            if(CMAKE_HOST_WIN32)
                string(TOLOWER "${watch_path_identity}" watch_path_identity)
            endif()
            string(SHA256 watch_path_identity_hash "${watch_path_identity}")
            if("${watch_path_identity_hash}" IN_LIST registered_watch_identities)
                continue()
            endif()
            list(APPEND registered_watch_identities "${watch_path_identity_hash}")
            string(APPEND topology_witness_content "${import_scan_line}\n")
            string(
                APPEND
                topology_runtime_witness_content
                "${watch_kind} ${encoded_watch_path} ${encoded_watch_identity}\n"
            )
        else()
            message(FATAL_ERROR "Protocyte import scanner trace became invalid")
        endif()
    endforeach()

    set(
        topology_witness
        "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-import-topology/${import_scan_key}.list"
    )
    cmake_path(GET topology_witness PARENT_PATH topology_witness_directory)
    file(MAKE_DIRECTORY "${topology_witness_directory}")
    set(write_topology_witness TRUE)
    if(EXISTS "${topology_witness}")
        file(READ "${topology_witness}" existing_topology_witness_content)
        if(existing_topology_witness_content STREQUAL topology_witness_content)
            set(write_topology_witness FALSE)
        endif()
    endif()
    if(write_topology_witness)
        file(WRITE "${topology_witness}" "${topology_witness_content}")
    endif()

    set(topology_runtime_witness "${topology_witness_directory}/${import_scan_key}.watch.list")
    _protocyte_write_if_different(
        "${topology_runtime_witness}"
        "${topology_runtime_witness_content}"
    )
    file(SHA256 "${topology_runtime_witness}" topology_expected_hash)
    set_property(
        GLOBAL PROPERTY
        "PROTOCYTE_INTERNAL_TOPOLOGY_EXPECTED_HASH_${import_scan_key}"
        "${topology_expected_hash}"
    )

    set(
        topology_check_script
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteImportTopology.cmake"
    )
    if(NOT EXISTS "${topology_check_script}")
        message(
            FATAL_ERROR
            "Protocyte import topology checker does not exist: ${topology_check_script}"
        )
    endif()
    _protocyte_append_configure_dependency("${topology_check_script}")
    _protocyte_append_configure_dependency("${topology_runtime_witness}")

    set(topology_check_target "protocyte_import_topology_check_${import_scan_key}")
    list(APPEND source_check_targets "${topology_check_target}")
    list(REMOVE_DUPLICATES source_check_targets)
    if(CMAKE_GENERATOR MATCHES "Makefiles")
        # Makefile generators can refresh the runtime witness in the guard and
        # use it to dirty code generation in the same build invocation. Do not
        # also depend on the configure-time witness: updating that witness on
        # the following CMake reconfigure would regenerate correct outputs a
        # second time.
        set(topology_dependencies "${topology_runtime_witness}")
    else()
        set(topology_dependencies "${topology_witness}")
    endif()
    set(${out_topology_dependencies} "${topology_dependencies}" PARENT_SCOPE)
    set(${out_source_check_targets} "${source_check_targets}" PARENT_SCOPE)
endfunction()

function(
    _protocyte_create_import_guard
    out_guard_dependency
    check_targets_var
)
    set(${out_guard_dependency} "" PARENT_SCOPE)
    set(guard_manifest_content "version=1\n")
    foreach(check_target IN LISTS ${check_targets_var})
        if(check_target MATCHES "^protocyte_source_check_(.+)$")
            set(source_proxy_key "${CMAKE_MATCH_1}")
            get_property(
                source_proxy
                GLOBAL PROPERTY "PROTOCYTE_INTERNAL_SOURCE_PROXY_PATH_${source_proxy_key}"
            )
            get_property(
                source_proxy_expected_hash
                GLOBAL PROPERTY "PROTOCYTE_INTERNAL_SOURCE_PROXY_EXPECTED_HASH_${source_proxy_key}"
            )
            if(source_proxy STREQUAL "" OR source_proxy_expected_hash STREQUAL "")
                message(FATAL_ERROR "Protocyte source dependency proxy metadata is missing")
            endif()
            cmake_path(GET source_proxy PARENT_PATH source_proxy_directory)
            set(source_proxy_argument "${source_proxy_directory}/${source_proxy_key}.path")
            set(source_proxy_lock "${source_proxy_directory}/${source_proxy_key}.lock")
            set(
                source_proxy_check_script
                "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteSourceDependency.cmake"
            )
            string(HEX "${source_proxy_argument}" encoded_source_proxy_argument)
            string(HEX "${source_proxy}" encoded_source_proxy)
            string(HEX "${source_proxy_lock}" encoded_source_proxy_lock)
            string(HEX "${source_proxy_check_script}" encoded_source_proxy_check_script)
            string(
                APPEND
                guard_manifest_content
                "source ${encoded_source_proxy_argument} ${encoded_source_proxy} "
                "${encoded_source_proxy_lock} ${source_proxy_expected_hash} "
                "${encoded_source_proxy_check_script}\n"
            )
        elseif(check_target MATCHES "^protocyte_import_topology_check_(.+)$")
            set(topology_key "${CMAKE_MATCH_1}")
            set(
                topology_directory
                "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-import-topology"
            )
            set(
                topology_request
                "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-import-scans/${topology_key}.request"
            )
            set(topology_witness "${topology_directory}/${topology_key}.watch.list")
            set(topology_lock "${topology_directory}/${topology_key}.watch.lock")
            _protocyte_get_internal(topology_plugin PLUGIN_EXECUTABLE)
            _protocyte_get_internal(topology_plugin_is_managed PLUGIN_IS_MANAGED)
            if("${topology_plugin_is_managed}" STREQUAL "")
                set(topology_plugin_is_managed FALSE)
            endif()
            _protocyte_get_internal(topology_import_scan_command IMPORT_SCAN_COMMAND)
            if("${topology_import_scan_command}" STREQUAL "")
                set(topology_import_scan_command "_cmake-import-scan-v1")
            endif()
            if("${topology_plugin}" STREQUAL "")
                message(FATAL_ERROR "Protocyte topology guard requires a prepared plugin")
            endif()
            get_property(
                topology_expected_hash
                GLOBAL PROPERTY "PROTOCYTE_INTERNAL_TOPOLOGY_EXPECTED_HASH_${topology_key}"
            )
            if(topology_expected_hash STREQUAL "")
                message(FATAL_ERROR "Protocyte topology witness metadata is missing")
            endif()
            set(
                topology_check_script
                "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteImportTopology.cmake"
            )
            string(HEX "${topology_plugin}" encoded_topology_plugin)
            string(
                HEX
                "${topology_import_scan_command}"
                encoded_topology_import_scan_command
            )
            string(HEX "${topology_request}" encoded_topology_request)
            string(HEX "${topology_witness}" encoded_topology_witness)
            string(HEX "${topology_lock}" encoded_topology_lock)
            string(HEX "${topology_check_script}" encoded_topology_check_script)
            string(
                APPEND
                guard_manifest_content
                "topology ${encoded_topology_plugin} ${encoded_topology_import_scan_command} "
                "${topology_plugin_is_managed} ${encoded_topology_request} ${encoded_topology_witness} "
                "${encoded_topology_lock} ${topology_expected_hash} "
                "${encoded_topology_check_script}\n"
            )
        endif()
    endforeach()
    if(guard_manifest_content STREQUAL "version=1\n")
        return()
    endif()

    string(
        SHA256
        guard_key
        "${CMAKE_CURRENT_BINARY_DIR}|${guard_manifest_content}"
    )
    set(guard_directory "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/protocyte-prebuild")
    set(guard_manifest "${guard_directory}/${guard_key}.list")
    set(guard_script "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocytePreBuildGuard.cmake")
    file(MAKE_DIRECTORY "${guard_directory}")
    _protocyte_write_if_different("${guard_manifest}" "${guard_manifest_content}")
    _protocyte_append_configure_dependency("${guard_script}")

    set(guard_target "protocyte_import_guard_${guard_key}")
    if(NOT TARGET "${guard_target}")
        set(guard_fail_on_change TRUE)
        if(CMAKE_GENERATOR MATCHES "Makefiles")
            set(guard_fail_on_change FALSE)
        endif()
        add_custom_target(
            "${guard_target}"
            COMMAND
                "${CMAKE_COMMAND}"
                "-DMANIFEST_FILE=${guard_manifest}"
                "-DFAIL_ON_CHANGE=${guard_fail_on_change}"
                "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=${PROTOCYTE_TOOL_TIMEOUT_SECONDS}"
                -P "${guard_script}"
            VERBATIM
        )
    endif()
    set(${out_guard_dependency} "${guard_target}" PARENT_SCOPE)
endfunction()

function(_protocyte_prepare_plugin)
    _protocyte_get_internal(protocyte_prepared_plugin PLUGIN_EXECUTABLE)
    if(NOT "${protocyte_prepared_plugin}" STREQUAL "")
        _protocyte_get_internal(protocyte_plugin_is_managed PLUGIN_IS_MANAGED)
        if("${protocyte_plugin_is_managed}" STREQUAL "")
            set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_IS_MANAGED FALSE)
        endif()
        return()
    endif()

    if(DEFINED CACHE{PROTOCYTE_PLUGIN_EXECUTABLE})
        get_property(protocyte_plugin_help CACHE PROTOCYTE_PLUGIN_EXECUTABLE PROPERTY HELPSTRING)
        if(protocyte_plugin_help STREQUAL "protocyte protoc plugin wrapper")
            unset(PROTOCYTE_PLUGIN_EXECUTABLE CACHE)
        endif()
    endif()

    if(DEFINED PROTOCYTE_PLUGIN_EXECUTABLE AND NOT "${PROTOCYTE_PLUGIN_EXECUTABLE}" STREQUAL "")
        _protocyte_validate_explicit_plugin(
            protocyte_plugin_executable
            "${PROTOCYTE_PLUGIN_EXECUTABLE}"
        )
        set(protocyte_plugin_is_managed FALSE)
    else()
        _protocyte_ensure_python_environment(protocyte_python_executable protocyte_plugin_executable)
        set(protocyte_plugin_is_managed TRUE)
    endif()

    set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${protocyte_plugin_executable}")
    set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_IS_MANAGED "${protocyte_plugin_is_managed}")
endfunction()

function(_protocyte_ensure_protobuf fetch_missing_import_sources)
    set(require_protobuf_import_sources TRUE)
    if(ARGC GREATER 1)
        set(require_protobuf_import_sources "${ARGV1}")
    endif()
    set(protoc_executable "")
    set(protoc_dependency "")
    set(protocyte_path_protoc "protocyte_path_protoc-NOTFOUND")
    set(protocyte_cross_candidate_diagnostics)

    if(
        DEFINED Protobuf_PROTOC_EXECUTABLE
        AND NOT Protobuf_PROTOC_EXECUTABLE STREQUAL ""
        AND NOT Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
    )
        if(CMAKE_CROSSCOMPILING AND Protobuf_PROTOC_EXECUTABLE MATCHES "\\$<")
            message(
                FATAL_ERROR
                "Cross-compiling Protocyte requires Protobuf_PROTOC_EXECUTABLE to be a concrete, "
                "host-runnable compiler path. Target generator expressions cannot propagate "
                "CROSSCOMPILING_EMULATOR through Protocyte's generation scripts."
            )
        endif()
        _protocyte_resolve_protoc_path(
            protoc_executable
            protoc_dependency
            "${Protobuf_PROTOC_EXECUTABLE}"
        )
        if(CMAKE_CROSSCOMPILING)
            _protocyte_try_host_protoc_path(
                explicit_protoc_is_host_runnable
                explicit_protoc_executable
                explicit_protoc_diagnostic
                "${protoc_executable}"
                "Protobuf_PROTOC_EXECUTABLE"
            )
            if(NOT explicit_protoc_is_host_runnable)
                message(
                    FATAL_ERROR
                    "Cross-compiling Protocyte requires Protobuf_PROTOC_EXECUTABLE to name a "
                    "host-runnable compiler. ${explicit_protoc_diagnostic}"
                )
            endif()
            set(protoc_executable "${explicit_protoc_executable}")
            set(protoc_dependency "${explicit_protoc_executable}")
        endif()
    elseif(CMAKE_CROSSCOMPILING)
        _protocyte_find_host_protoc_on_path(protocyte_path_protoc)
        if(protocyte_path_protoc)
            _protocyte_try_host_protoc_path(
                path_protoc_is_host_runnable
                path_protoc_executable
                path_protoc_diagnostic
                "${protocyte_path_protoc}"
                "protoc found on the host PATH"
            )
            if(path_protoc_is_host_runnable)
                set(protoc_executable "${path_protoc_executable}")
                set(protoc_dependency "${path_protoc_executable}")
            else()
                list(APPEND protocyte_cross_candidate_diagnostics "${path_protoc_diagnostic}")
            endif()
        endif()
    elseif(TARGET protobuf::protoc)
        set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
        set(protoc_dependency protobuf::protoc)
    endif()

    if(protoc_executable STREQUAL "")
        if(
            NOT TARGET protobuf::protoc
            AND (
                NOT DEFINED Protobuf_PROTOC_EXECUTABLE
                OR Protobuf_PROTOC_EXECUTABLE STREQUAL ""
                OR Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
            )
        )
            find_package(Protobuf CONFIG QUIET)
        endif()
        if(
            NOT TARGET protobuf::protoc
            AND NOT TARGET protobuf::libprotobuf
            AND (
                NOT DEFINED Protobuf_PROTOC_EXECUTABLE
                OR Protobuf_PROTOC_EXECUTABLE STREQUAL ""
                OR Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
            )
        )
            find_package(Protobuf MODULE QUIET)
        endif()

        if(CMAKE_CROSSCOMPILING)
            if(
                DEFINED Protobuf_PROTOC_EXECUTABLE
                AND NOT Protobuf_PROTOC_EXECUTABLE STREQUAL ""
                AND NOT Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
            )
                _protocyte_try_host_protoc_path(
                    package_protoc_is_host_runnable
                    package_protoc_executable
                    package_protoc_diagnostic
                    "${Protobuf_PROTOC_EXECUTABLE}"
                    "Protobuf package compiler"
                )
                if(package_protoc_is_host_runnable)
                    set(protoc_executable "${package_protoc_executable}")
                    set(protoc_dependency "${package_protoc_executable}")
                else()
                    list(APPEND protocyte_cross_candidate_diagnostics "${package_protoc_diagnostic}")
                endif()
            endif()

            if(protoc_executable STREQUAL "" AND TARGET protobuf::protoc)
                _protocyte_try_imported_host_protoc_target(
                    target_protoc_is_host_runnable
                    target_protoc_executable
                    target_protoc_diagnostic
                    protobuf::protoc
                )
                if(target_protoc_is_host_runnable)
                    set(protoc_executable "${target_protoc_executable}")
                    set(protoc_dependency "${target_protoc_executable}")
                else()
                    list(APPEND protocyte_cross_candidate_diagnostics "${target_protoc_diagnostic}")
                endif()
            endif()
        else()
            if(TARGET protobuf::protoc)
                set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
                set(protoc_dependency protobuf::protoc)
            elseif(
                DEFINED Protobuf_PROTOC_EXECUTABLE
                AND NOT Protobuf_PROTOC_EXECUTABLE STREQUAL ""
                AND NOT Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
            )
                _protocyte_resolve_protoc_path(
                    protoc_executable
                    protoc_dependency
                    "${Protobuf_PROTOC_EXECUTABLE}"
                )
            else()
                _protocyte_find_host_protoc_on_path(protocyte_path_protoc)
            endif()
        endif()

        if(protoc_executable STREQUAL "" AND CMAKE_CROSSCOMPILING)
            if(protocyte_cross_candidate_diagnostics)
                list(JOIN protocyte_cross_candidate_diagnostics "\n  - " rejected_candidates)
                set(rejected_candidates "\nRejected compiler candidate(s):\n  - ${rejected_candidates}")
            else()
                set(rejected_candidates "")
            endif()
            message(
                FATAL_ERROR
                "Protocyte could not find a host-runnable protoc while cross-compiling. "
                "Set Protobuf_PROTOC_EXECUTABLE to a concrete host compiler path or add a host protoc "
                "to PATH. Ambient protobuf::protoc targets are used only when their imported executable "
                "can run directly on the host; target emulators are not propagated through Protocyte's "
                "generation scripts.${rejected_candidates}"
            )
        endif()

        if(protoc_executable STREQUAL "")
            if(protocyte_path_protoc)
                _protocyte_resolve_protoc_path(
                    protoc_executable
                    protoc_dependency
                    "${protocyte_path_protoc}"
                )
            elseif(PROTOCYTE_FETCH_PROTOBUF)
                if(NOT DEFINED protobuf_BUILD_TESTS)
                    set(protobuf_BUILD_TESTS OFF)
                endif()
                if(NOT DEFINED protobuf_BUILD_CONFORMANCE)
                    set(protobuf_BUILD_CONFORMANCE OFF)
                endif()
                if(NOT DEFINED protobuf_BUILD_EXAMPLES)
                    set(protobuf_BUILD_EXAMPLES OFF)
                endif()
                if(NOT DEFINED protobuf_BUILD_PROTOBUF_BINARIES)
                    set(protobuf_BUILD_PROTOBUF_BINARIES ON)
                endif()
                if(NOT DEFINED protobuf_INSTALL)
                    set(protobuf_INSTALL OFF)
                endif()
                FetchContent_Declare(
                    protobuf
                    GIT_REPOSITORY https://github.com/protocolbuffers/protobuf.git
                    GIT_TAG "${PROTOCYTE_PROTOBUF_GIT_TAG}"
                )
                FetchContent_MakeAvailable(protobuf)
                if(NOT TARGET protobuf::protoc)
                    message(
                        FATAL_ERROR
                        "Protocyte fetched protobuf, but the protobuf::protoc target is unavailable. "
                        "When configuring offline, pre-populate the protobuf FetchContent source or "
                        "set Protobuf_PROTOC_EXECUTABLE to a host-runnable protoc."
                    )
                endif()
                FetchContent_GetProperties(protobuf SOURCE_DIR protobuf_SOURCE_DIR)
                set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
                set(protoc_dependency protobuf::protoc)
            else()
                message(
                    FATAL_ERROR
                    "Protocyte could not find protoc. Set Protobuf_PROTOC_EXECUTABLE to a host-runnable "
                    "compiler, add protoc to PATH, or enable PROTOCYTE_FETCH_PROTOBUF."
                )
            endif()
        endif()
    endif()

    set(PROTOCYTE_PROTOC_EXECUTABLE "${protoc_executable}" CACHE INTERNAL "protoc executable for protocyte")
    set(PROTOCYTE_PROTOC_DEPENDENCY "${protoc_dependency}" CACHE INTERNAL "protoc dependency for protocyte")
    set(protoc_toolchain_identity "${protoc_dependency}|${protoc_executable}")
    if(TARGET "${protoc_dependency}")
        get_target_property(protoc_target_is_imported "${protoc_dependency}" IMPORTED)
        if(protoc_target_is_imported)
            get_target_property(protoc_imported_location "${protoc_dependency}" IMPORTED_LOCATION)
            if(protoc_imported_location)
                string(APPEND protoc_toolchain_identity "|${protoc_imported_location}")
            endif()
            get_target_property(
                protoc_imported_configurations
                "${protoc_dependency}"
                IMPORTED_CONFIGURATIONS
            )
            foreach(protoc_configuration IN LISTS protoc_imported_configurations)
                string(TOUPPER "${protoc_configuration}" protoc_configuration_upper)
                get_target_property(
                    protoc_configuration_location
                    "${protoc_dependency}"
                    "IMPORTED_LOCATION_${protoc_configuration_upper}"
                )
                if(protoc_configuration_location)
                    string(
                        APPEND
                        protoc_toolchain_identity
                        "|${protoc_configuration_upper}=${protoc_configuration_location}"
                    )
                endif()
            endforeach()
        endif()
    endif()
    set(resolve_protobuf_import_sources "${require_protobuf_import_sources}")
    if(
        DEFINED PROTOCYTE_PROTOBUF_IMPORT_DIR
        AND NOT PROTOCYTE_PROTOBUF_IMPORT_DIR STREQUAL ""
    )
        # An explicit root remains part of protoc's search order even when the
        # selected source closure happens not to import protobuf definitions.
        set(resolve_protobuf_import_sources TRUE)
    endif()
    if(resolve_protobuf_import_sources)
        _protocyte_resolve_protobuf_import_dir(
            protocyte_import_dir_is_explicit
            "${protoc_toolchain_identity}"
        )
        if(
            NOT DEFINED PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR
            AND NOT protocyte_import_dir_is_explicit
            AND fetch_missing_import_sources
            AND PROTOCYTE_FETCH_PROTOBUF
        )
            _protocyte_fetch_protobuf_import_sources("${protoc_toolchain_identity}")
        endif()
    endif()
endfunction()

function(_protocyte_setup_codegen_internal fetch_missing_import_sources)
    set(require_protobuf_import_sources TRUE)
    if(ARGC GREATER 1)
        set(require_protobuf_import_sources "${ARGV1}")
    endif()
    _protocyte_prepare_plugin()
    _protocyte_ensure_protobuf(
        "${fetch_missing_import_sources}"
        "${require_protobuf_import_sources}"
    )
endfunction()

function(protocyte_setup_codegen)
    _protocyte_validate_parsed_arguments("protocyte_setup_codegen" "${ARGN}" "")
    _protocyte_setup_codegen_internal(TRUE)
endfunction()

function(protocyte_generate)
    set(options DISCOVER EMIT_RUNTIME)
    set(oneValueArgs
        TARGET
        DESCRIPTOR_SET
        PROTO_ROOT
        OUT_DIR
        GENERATED_HEADERS_VAR
        GENERATED_SOURCES_VAR
        GENERATED_TARGET_VAR
        RUNTIME_PREFIX
        NAMESPACE_PREFIX
        INCLUDE_PREFIX
    )
    set(multiValueArgs PROTOS IMPORT_DIRS DEPENDS OPTIONS)
    _protocyte_validate_unique_one_value_keywords_from_argv(
        "protocyte_generate"
        "${oneValueArgs}"
        "${ARGC}"
    )
    cmake_parse_arguments(
        PARSE_ARGV
        0
        PROTOCYTE
        "${options}"
        "${oneValueArgs}"
        "${multiValueArgs}"
    )
    _protocyte_validate_parsed_arguments(
        "protocyte_generate"
        "${PROTOCYTE_UNPARSED_ARGUMENTS}"
        "${PROTOCYTE_KEYWORDS_MISSING_VALUES}"
    )
    _protocyte_validate_forwarded_generator_options("protocyte_generate" ${PROTOCYTE_OPTIONS})

    foreach(name IN LISTS oneValueArgs multiValueArgs)
        _protocyte_value_is_nonempty(protocyte_has_${name} PROTOCYTE_${name})
    endforeach()

    if(NOT protocyte_has_TARGET)
        message(FATAL_ERROR "protocyte_generate requires TARGET")
    endif()
    if(NOT protocyte_has_DESCRIPTOR_SET AND NOT protocyte_has_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_generate requires either PROTO_ROOT or DESCRIPTOR_SET")
    endif()
    if(NOT protocyte_has_OUT_DIR)
        message(FATAL_ERROR "protocyte_generate requires OUT_DIR")
    endif()
    if(protocyte_has_NAMESPACE_PREFIX)
        _protocyte_validate_namespace_prefix(
            "protocyte_generate"
            "${PROTOCYTE_NAMESPACE_PREFIX}"
        )
    endif()
    if("${PROTOCYTE_OUT_DIR}" MATCHES "\\$<")
        message(FATAL_ERROR "protocyte_generate OUT_DIR must be a configure-time path, not a generator expression")
    endif()
    if(NOT IS_ABSOLUTE "${PROTOCYTE_OUT_DIR}")
        cmake_path(
            ABSOLUTE_PATH PROTOCYTE_OUT_DIR
            BASE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
            NORMALIZE
            OUTPUT_VARIABLE PROTOCYTE_OUT_DIR
        )
    else()
        cmake_path(NORMAL_PATH PROTOCYTE_OUT_DIR OUTPUT_VARIABLE PROTOCYTE_OUT_DIR)
    endif()
    if(PROTOCYTE_DISCOVER AND protocyte_has_PROTOS)
        message(FATAL_ERROR "protocyte_generate accepts either DISCOVER or PROTOS, not both")
    endif()
    if(NOT PROTOCYTE_DISCOVER AND NOT protocyte_has_PROTOS)
        message(FATAL_ERROR "protocyte_generate requires either DISCOVER or PROTOS")
    endif()

    if(protocyte_has_DESCRIPTOR_SET)
        if("${PROTOCYTE_DESCRIPTOR_SET}" MATCHES "\\$<")
            message(
                FATAL_ERROR
                "protocyte_generate DESCRIPTOR_SET must be a configure-time path, not a generator expression. "
                "Use a concrete, config-independent descriptor-set output; when the build produces it, "
                "select explicit PROTOS/FILES and list the producing file or target in DEPENDS."
            )
        endif()
        if(IS_ABSOLUTE "${PROTOCYTE_DESCRIPTOR_SET}")
            set(protocyte_descriptor_set "${PROTOCYTE_DESCRIPTOR_SET}")
        else()
            cmake_path(
                ABSOLUTE_PATH PROTOCYTE_DESCRIPTOR_SET
                BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                NORMALIZE
                OUTPUT_VARIABLE protocyte_descriptor_set
            )
        endif()
        if(IS_DIRECTORY "${protocyte_descriptor_set}")
            message(FATAL_ERROR "protocyte_generate DESCRIPTOR_SET must be an existing file: ${protocyte_descriptor_set}")
        endif()
        if(NOT EXISTS "${protocyte_descriptor_set}")
            if(PROTOCYTE_DISCOVER)
                message(
                    FATAL_ERROR
                    "protocyte_generate DESCRIPTOR_SET must exist during configuration when using DISCOVER: "
                    "${protocyte_descriptor_set}. Generate the descriptor set before configuring, or use explicit "
                    "PROTOS/FILES with DEPENDS on the target that produces it."
                )
            elseif(NOT protocyte_has_DEPENDS)
                message(
                    FATAL_ERROR
                    "protocyte_generate DESCRIPTOR_SET must be an existing file: ${protocyte_descriptor_set}. "
                    "For a descriptor set produced by the build, use explicit PROTOS/FILES and add its producing "
                    "file or target to DEPENDS."
                )
            endif()
        endif()
        if(protocyte_has_PROTO_ROOT)
            message(FATAL_ERROR "protocyte_generate accepts either DESCRIPTOR_SET or PROTO_ROOT, not both")
        endif()
        if(protocyte_has_IMPORT_DIRS)
            message(FATAL_ERROR "protocyte_generate does not use IMPORT_DIRS with DESCRIPTOR_SET")
        endif()
    elseif(IS_ABSOLUTE "${PROTOCYTE_PROTO_ROOT}")
        set(protocyte_proto_root "${PROTOCYTE_PROTO_ROOT}")
    else()
        cmake_path(
            ABSOLUTE_PATH PROTOCYTE_PROTO_ROOT
            BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            NORMALIZE
            OUTPUT_VARIABLE protocyte_proto_root
        )
    endif()

    set(encoded_protocyte_proto_root "")
    set(encoded_protocyte_user_import_dirs)
    if(NOT protocyte_has_DESCRIPTOR_SET)
        if(NOT IS_DIRECTORY "${protocyte_proto_root}")
            message(FATAL_ERROR "protocyte_generate PROTO_ROOT must be an existing directory: ${protocyte_proto_root}")
        endif()
        string(HEX "${protocyte_proto_root}" encoded_protocyte_proto_root)
        foreach(import_dir IN LISTS PROTOCYTE_IMPORT_DIRS)
            if(IS_ABSOLUTE "${import_dir}")
                set(import_dir_abs "${import_dir}")
            else()
                cmake_path(
                    ABSOLUTE_PATH import_dir
                    BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                    NORMALIZE
                    OUTPUT_VARIABLE import_dir_abs
                )
            endif()
            if(NOT IS_DIRECTORY "${import_dir_abs}")
                message(FATAL_ERROR "protocyte_generate IMPORT_DIRS entry must be an existing directory: ${import_dir_abs}")
            endif()
            string(HEX "${import_dir_abs}" encoded_import_dir)
            list(APPEND encoded_protocyte_user_import_dirs "${encoded_import_dir}")
        endforeach()
        list(REMOVE_DUPLICATES encoded_protocyte_user_import_dirs)
    endif()

    if(protocyte_has_DESCRIPTOR_SET AND PROTOCYTE_DISCOVER)
        set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${protocyte_descriptor_set}")
        _protocyte_setup_codegen_internal(FALSE FALSE)
        _protocyte_discover_descriptor_set(protocyte_proto_files "${protocyte_descriptor_set}")
    elseif(PROTOCYTE_DISCOVER)
        file(GLOB_RECURSE protocyte_proto_files CONFIGURE_DEPENDS "${protocyte_proto_root}/*.proto")
    else()
        set(protocyte_proto_files "${PROTOCYTE_PROTOS}")
    endif()

    if("${protocyte_proto_files}" STREQUAL "")
        message(FATAL_ERROR "protocyte_generate did not receive any .proto files")
    endif()

    set(protocyte_requires_protobuf_import_sources FALSE)
    set(normalized_proto_files)
    set(normalized_proto_names)
    set(protocyte_source_check_targets "")
    if(protocyte_has_DESCRIPTOR_SET)
        foreach(proto_file IN LISTS protocyte_proto_files)
            _protocyte_validate_descriptor_name("${proto_file}")
            string(SHA256 proto_file_key "${proto_file}")
            if(DEFINED protocyte_seen_proto_file_${proto_file_key})
                continue()
            endif()
            set(protocyte_seen_proto_file_${proto_file_key} TRUE)
            string(REPLACE ";" "\\;" proto_file_list_element "${proto_file}")
            list(APPEND normalized_proto_files "${proto_file_list_element}")
            list(APPEND normalized_proto_names "${proto_file_list_element}")
        endforeach()
    else()
        # CMake list mutators discard escaped semicolons. Use a hexadecimal
        # sort key and a digest-backed scalar mapping until sorting and exact
        # duplicate removal are complete, then rebuild the escaped path list.
        set(normalized_proto_file_entries)
        foreach(proto_file IN LISTS protocyte_proto_files)
            if(IS_ABSOLUTE "${proto_file}")
                cmake_path(NORMAL_PATH proto_file OUTPUT_VARIABLE proto_abs)
            else()
                cmake_path(
                    ABSOLUTE_PATH proto_file
                    BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                    NORMALIZE
                    OUTPUT_VARIABLE proto_abs
                )
            endif()

            if(NOT EXISTS "${proto_abs}" OR IS_DIRECTORY "${proto_abs}")
                message(FATAL_ERROR "protocyte_generate PROTOS entry must be an existing file: ${proto_abs}")
            endif()

            file(RELATIVE_PATH proto_rel "${protocyte_proto_root}" "${proto_abs}")
            if(proto_rel STREQUAL ".." OR proto_rel MATCHES "^[.][.][/\\\\]")
                message(FATAL_ERROR "proto file '${proto_abs}' is outside PROTO_ROOT '${protocyte_proto_root}'")
            endif()
            string(REPLACE "\\" "/" proto_rel "${proto_rel}")

            string(HEX "${proto_abs}" proto_abs_sort_key)
            string(SHA256 proto_abs_key "${proto_abs}")
            set("protocyte_normalized_proto_file_${proto_abs_key}" "${proto_abs}")
            set("protocyte_normalized_proto_name_${proto_abs_key}" "${proto_rel}")
            # The final import scan supplies a generator-safe dependency alias
            # (or requests a proxy) after the complete root order is known.
            set(protocyte_source_dependency "${proto_abs}")
            set(
                "protocyte_source_dependency_${proto_abs_key}"
                "${protocyte_source_dependency}"
            )
            list(APPEND normalized_proto_file_entries "${proto_abs_sort_key}:${proto_abs_key}")
        endforeach()
        list(REMOVE_DUPLICATES normalized_proto_file_entries)
        list(SORT normalized_proto_file_entries)
        foreach(proto_file_entry IN LISTS normalized_proto_file_entries)
            string(REGEX REPLACE "^.*:" "" proto_abs_key "${proto_file_entry}")
            set(proto_abs_variable "protocyte_normalized_proto_file_${proto_abs_key}")
            set(proto_name_variable "protocyte_normalized_proto_name_${proto_abs_key}")
            string(REPLACE ";" "\\;" proto_abs_list_element "${${proto_abs_variable}}")
            string(REPLACE ";" "\\;" proto_name_list_element "${${proto_name_variable}}")
            list(APPEND normalized_proto_files "${proto_abs_list_element}")
            list(APPEND normalized_proto_names "${proto_name_list_element}")
        endforeach()
    endif()

    _protocyte_get_internal(protocyte_proto_dir PROTO_DIR)
    set(protocyte_import_topology_witness "")
    set(protocyte_declared_protobuf_descriptor "")
    set(protocyte_needs_resolved_protobuf_import_dir FALSE)
    if(NOT protocyte_has_DESCRIPTOR_SET)
        string(HEX "${protocyte_proto_dir}" encoded_protocyte_proto_dir)
        set(
            encoded_initial_import_dirs
            "${encoded_protocyte_proto_root}"
            ${encoded_protocyte_user_import_dirs}
            "${encoded_protocyte_proto_dir}"
        )
        list(REMOVE_DUPLICATES encoded_initial_import_dirs)
        foreach(encoded_import_dir IN LISTS encoded_initial_import_dirs)
            _protocyte_decode_hex_string(import_dir "${encoded_import_dir}")
            if(
                protocyte_declared_protobuf_descriptor STREQUAL ""
                AND EXISTS "${import_dir}/google/protobuf/descriptor.proto"
                AND NOT IS_DIRECTORY "${import_dir}/google/protobuf/descriptor.proto"
            )
                set(
                    protocyte_declared_protobuf_descriptor
                    "${import_dir}/google/protobuf/descriptor.proto"
                )
            endif()
        endforeach()
        _protocyte_run_source_import_scan(
            protocyte_requires_protobuf_import_sources
            protocyte_first_import_scan_key
            protocyte_first_import_scan_lines
            protocyte_first_scan_has_unwatchable_source
            normalized_proto_files
            encoded_initial_import_dirs
        )
        set(
            protocyte_needs_resolved_protobuf_import_dir
            "${protocyte_requires_protobuf_import_sources}"
        )
        if(NOT protocyte_declared_protobuf_descriptor STREQUAL "")
            # Caller-owned roots already satisfy the preflight requirement.
            # Do not discover or fetch an additional automatic root merely
            # because the closure imports a protobuf definition.
            set(protocyte_needs_resolved_protobuf_import_dir FALSE)
        elseif(
            CMAKE_GENERATOR MATCHES "Makefiles"
            AND protocyte_first_scan_has_unwatchable_source
        )
            # Makefile-family generators perform their top-level configure
            # check before the always-run source proxy checker. Keep the
            # protobuf root in the generated command line as a conservative
            # superset so a false-to-true source edit is still correct in its
            # first build; the refreshed proxy updates topology next time.
            set(protocyte_needs_resolved_protobuf_import_dir TRUE)
        endif()
    endif()

    if(NOT protocyte_has_DESCRIPTOR_SET OR NOT PROTOCYTE_DISCOVER)
        if(protocyte_has_DESCRIPTOR_SET)
            _protocyte_setup_codegen_internal(FALSE FALSE)
        else()
            _protocyte_setup_codegen_internal(
                "${protocyte_needs_resolved_protobuf_import_dir}"
                "${protocyte_needs_resolved_protobuf_import_dir}"
            )
        endif()
    endif()
    set(protocyte_selected_protobuf_import_dir "")
    if(NOT protocyte_has_DESCRIPTOR_SET)
        set(
            select_resolved_protobuf_import_dir
            "${protocyte_needs_resolved_protobuf_import_dir}"
        )
        if(
            DEFINED PROTOCYTE_PROTOBUF_IMPORT_DIR
            AND NOT PROTOCYTE_PROTOBUF_IMPORT_DIR STREQUAL ""
        )
            # A caller-owned root is part of the declared import order even for
            # an import-free closure. Automatic roots remain per-closure: keep
            # their cache metadata for reuse without leaking them into later
            # import-free targets or reconfigurations.
            set(select_resolved_protobuf_import_dir TRUE)
        endif()
        if(
            select_resolved_protobuf_import_dir
            AND DEFINED PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR
        )
            set(
                protocyte_selected_protobuf_import_dir
                "${PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}"
            )
        endif()

        set(encoded_final_import_dirs ${encoded_initial_import_dirs})
        set(protocyte_root_validity_descriptor "")
        if(NOT protocyte_selected_protobuf_import_dir STREQUAL "")
            string(
                HEX
                "${protocyte_selected_protobuf_import_dir}"
                encoded_protobuf_import_dir
            )
            list(APPEND encoded_final_import_dirs "${encoded_protobuf_import_dir}")
            set(
                protocyte_root_validity_descriptor
                "${protocyte_selected_protobuf_import_dir}/google/protobuf/descriptor.proto"
            )
        elseif(
            protocyte_requires_protobuf_import_sources
            AND NOT protocyte_declared_protobuf_descriptor STREQUAL ""
        )
            set(
                protocyte_root_validity_descriptor
                "${protocyte_declared_protobuf_descriptor}"
            )
        endif()
        list(REMOVE_DUPLICATES encoded_final_import_dirs)

        set(protocyte_final_scan_source_files "${normalized_proto_files}")
        if(NOT protocyte_root_validity_descriptor STREQUAL "")
            string(
                REPLACE ";" "\\;"
                escaped_root_validity_descriptor
                "${protocyte_root_validity_descriptor}"
            )
            list(APPEND protocyte_final_scan_source_files "${escaped_root_validity_descriptor}")
        endif()
        if(
            encoded_final_import_dirs STREQUAL encoded_initial_import_dirs
            AND protocyte_root_validity_descriptor STREQUAL ""
        )
            set(protocyte_final_import_scan_key "${protocyte_first_import_scan_key}")
            set(protocyte_final_import_scan_lines "${protocyte_first_import_scan_lines}")
        else()
            _protocyte_run_source_import_scan(
                protocyte_requires_protobuf_import_sources
                protocyte_final_import_scan_key
                protocyte_final_import_scan_lines
                protocyte_final_scan_has_unwatchable_source
                protocyte_final_scan_source_files
                encoded_final_import_dirs
            )
        endif()
        _protocyte_register_source_import_scan(
            protocyte_import_topology_witness
            protocyte_import_scan_check_targets
            "${protocyte_final_import_scan_key}"
            protocyte_final_import_scan_lines
        )
        foreach(import_scan_line IN LISTS protocyte_final_import_scan_lines)
            if(NOT import_scan_line MATCHES "^source ([0-9a-f]+) (-|[0-9a-f]+)$")
                continue()
            endif()
            set(encoded_source "${CMAKE_MATCH_1}")
            set(encoded_dependency "${CMAKE_MATCH_2}")
            _protocyte_decode_hex_string(import_scan_source "${encoded_source}")
            string(SHA256 import_scan_source_key "${import_scan_source}")
            set(
                import_scan_dependency_variable
                "protocyte_source_dependency_${import_scan_source_key}"
            )
            if(NOT DEFINED ${import_scan_dependency_variable})
                continue()
            endif()
            _protocyte_source_path_requires_proxy(
                import_scan_source_requires_proxy
                "${import_scan_source}"
            )
            if(
                encoded_dependency STREQUAL "-"
                OR import_scan_source_requires_proxy
            )
                _protocyte_get_source_dependency_proxy(
                    import_scan_dependency
                    import_scan_check_target
                    "${import_scan_source}"
                )
                list(
                    APPEND
                    protocyte_source_check_targets
                    "${import_scan_check_target}"
                )
            else()
                _protocyte_decode_hex_string(
                    import_scan_dependency
                    "${encoded_dependency}"
                )
            endif()
            set(
                "${import_scan_dependency_variable}"
                "${import_scan_dependency}"
            )
        endforeach()
        list(
            APPEND
            protocyte_source_check_targets
            ${protocyte_import_scan_check_targets}
        )
    endif()
    set(protocyte_import_guard_target "")
    if(NOT protocyte_has_DESCRIPTOR_SET)
        list(REMOVE_DUPLICATES protocyte_source_check_targets)
        _protocyte_create_import_guard(
            protocyte_import_guard_target
            protocyte_source_check_targets
        )
    endif()
    _protocyte_get_internal(protocyte_options_proto OPTIONS_PROTO)
    _protocyte_get_internal(protocyte_generator_sources GENERATOR_SOURCES)
    _protocyte_get_internal(protocyte_plugin_executable PLUGIN_EXECUTABLE)
    _protocyte_get_internal(protocyte_plugin_is_managed PLUGIN_IS_MANAGED)
    if("${protocyte_plugin_executable}" STREQUAL "")
        message(FATAL_ERROR "Protocyte code generation plugin was not prepared")
    endif()
    if("${protocyte_plugin_is_managed}" STREQUAL "")
        set(protocyte_plugin_is_managed FALSE)
    endif()
    _protocyte_canonical_output_directory(
        PROTOCYTE_OUT_DIR
        "${PROTOCYTE_OUT_DIR}"
    )

    set(generator_options ${PROTOCYTE_OPTIONS})
    if(protocyte_has_NAMESPACE_PREFIX)
        list(APPEND generator_options "namespace_prefix=${PROTOCYTE_NAMESPACE_PREFIX}")
    endif()
    if(protocyte_has_INCLUDE_PREFIX)
        _protocyte_validate_virtual_directory_prefix("include prefix" "${PROTOCYTE_INCLUDE_PREFIX}")
        list(APPEND generator_options "include_prefix=${PROTOCYTE_INCLUDE_PREFIX}")
    endif()
    if(DEFINED _protocyte_reflection_api_macro AND NOT "${_protocyte_reflection_api_macro}" STREQUAL "")
        list(APPEND generator_options "_protocyte_reflection_api_macro=${_protocyte_reflection_api_macro}")
    endif()

    if(PROTOCYTE_EMIT_RUNTIME)
        if(protocyte_has_RUNTIME_PREFIX)
            _protocyte_validate_virtual_directory_prefix("runtime prefix" "${PROTOCYTE_RUNTIME_PREFIX}")
            set(runtime_prefix "${PROTOCYTE_RUNTIME_PREFIX}")
            list(APPEND generator_options "runtime=emit:${PROTOCYTE_RUNTIME_PREFIX}")
        else()
            set(runtime_prefix "protocyte/runtime")
            list(APPEND generator_options "runtime=emit")
        endif()
    elseif(protocyte_has_RUNTIME_PREFIX)
        _protocyte_validate_virtual_directory_prefix("runtime prefix" "${PROTOCYTE_RUNTIME_PREFIX}")
        set(runtime_prefix "${PROTOCYTE_RUNTIME_PREFIX}")
        list(APPEND generator_options "runtime_prefix=${PROTOCYTE_RUNTIME_PREFIX}")
    else()
        set(runtime_prefix "protocyte/runtime")
    endif()

    _protocyte_generated_path_budget(
        protocyte_generated_path_budget
        protocyte_generated_directory_budget
        "${PROTOCYTE_OUT_DIR}"
    )
    if(NOT "${protocyte_generated_path_budget}" STREQUAL "")
        list(
            APPEND
            generator_options
            "_protocyte_generated_path_max_bytes=${protocyte_generated_path_budget}"
            "_protocyte_generated_directory_max_bytes=${protocyte_generated_directory_budget}"
        )
    endif()

    string(JOIN "," generator_parameter ${generator_options})
    _protocyte_encode_generator_parameter(encoded_generator_parameter "${generator_parameter}")

    set(protocyte_generated_headers)
    set(protocyte_generated_sources)
    _protocyte_descriptor_outputs(
        protocyte_generated_headers
        protocyte_generated_sources
        "${PROTOCYTE_OUT_DIR}"
        normalized_proto_names
        "${protocyte_generated_path_budget}"
        "${protocyte_generated_directory_budget}"
    )

    if(PROTOCYTE_EMIT_RUNTIME)
        set(protocyte_runtime_output "${PROTOCYTE_OUT_DIR}/${runtime_prefix}/runtime.hpp")
        _protocyte_claim_runtime_output("${protocyte_runtime_output}" "${PROTOCYTE_TARGET}")
        list(APPEND protocyte_generated_headers "${protocyte_runtime_output}")
    endif()

    set(protocyte_outputs "${protocyte_generated_headers}" "${protocyte_generated_sources}")

    set(protoc_descriptor_argument)
    set(protocyte_input_depends)
    if(NOT protocyte_has_DESCRIPTOR_SET)
        # The dependency-scan outputs below already track each direct source
        # and its complete import closure.
        # Keep roots encoded across every list mutation: escaped semicolons are
        # not stable under CMake's duplicate-removal and append operations.
        set(encoded_protocyte_import_dirs ${encoded_final_import_dirs})
        set(protocyte_import_inventory_depends ${protocyte_import_topology_witness})
        set(encoded_protoc_import_dirs)
        set(protocyte_protoc_proto_root "${protocyte_proto_root}")
        foreach(encoded_import_dir IN LISTS encoded_protocyte_import_dirs)
            _protocyte_decode_hex_string(import_dir "${encoded_import_dir}")
            _protocyte_protoc_safe_import_root(protoc_import_dir "${import_dir}")
            string(HEX "${protoc_import_dir}" encoded_protoc_import_dir)
            list(APPEND encoded_protoc_import_dirs "${encoded_protoc_import_dir}")
            if(encoded_import_dir STREQUAL encoded_protocyte_proto_root)
                set(protocyte_protoc_proto_root "${protoc_import_dir}")
            endif()
        endforeach()
        list(REMOVE_DUPLICATES encoded_protoc_import_dirs)

        foreach(proto_file IN LISTS normalized_proto_files)
            string(SHA256 proto_file_key "${proto_file}")
            if(protocyte_protoc_proto_root STREQUAL protocyte_proto_root)
                set(protocyte_protoc_input "${proto_file}")
            else()
                file(
                    RELATIVE_PATH
                    protoc_proto_name
                    "${protocyte_proto_root}"
                    "${proto_file}"
                )
                set(
                    protocyte_protoc_input
                    "${protocyte_protoc_proto_root}/${protoc_proto_name}"
                )
            endif()
            set(
                "protocyte_protoc_input_${proto_file_key}"
                "${protocyte_protoc_input}"
            )
        endforeach()

        set(has_protobuf_descriptor_proto FALSE)
        foreach(encoded_import_dir IN LISTS encoded_protocyte_import_dirs)
            _protocyte_decode_hex_string(import_dir "${encoded_import_dir}")
            if(
                EXISTS "${import_dir}/google/protobuf/descriptor.proto"
                AND NOT IS_DIRECTORY "${import_dir}/google/protobuf/descriptor.proto"
            )
                set(has_protobuf_descriptor_proto TRUE)
                break()
            endif()
        endforeach()

        if(protocyte_requires_protobuf_import_sources AND NOT has_protobuf_descriptor_proto)
            if(DEFINED PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR)
                message(
                    FATAL_ERROR
                    "protocyte_generate selected a different protoc toolchain, but the previously auto-discovered "
                    "protobuf import root belongs to the old toolchain: ${PROTOCYTE_INTERNAL_STALE_PROTOBUF_IMPORT_DIR}. "
                    "Set PROTOCYTE_PROTOBUF_IMPORT_DIR or IMPORT_DIRS explicitly to share an import root, "
                    "or enable PROTOCYTE_FETCH_PROTOBUF to provision matching import sources."
                )
            else()
                message(
                    FATAL_ERROR
                    "protocyte_generate could not locate google/protobuf/descriptor.proto. "
                    "Install protobuf headers or configure a matching import root via PROTOCYTE_PROTOBUF_IMPORT_DIR/IMPORT_DIRS."
                )
            endif()
        endif()

        set(protocyte_dependency_dir "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/protocyte-dependencies")
        set(protocyte_lock_dir "${CMAKE_BINARY_DIR}/CMakeFiles/protocyte-locks")
        set(protocyte_dependency_scan_script "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteDependencyScan.cmake")
        set(protocyte_dependency_outputs)
        set(protocyte_dependency_file_format)
        if(CMAKE_GENERATOR MATCHES "^Ninja")
            set(protocyte_dependency_file_format --ninja)
        elseif(CMAKE_GENERATOR MATCHES "^Visual Studio")
            set(protocyte_dependency_file_format --msbuild)
        endif()
        foreach(proto_file IN LISTS normalized_proto_files)
            string(SHA256 proto_file_key "${proto_file}")
            set(proto_file_dependency "${protocyte_source_dependency_${proto_file_key}}")
            string(REPLACE ";" "\\;" proto_file_dependency "${proto_file_dependency}")
            string(REPLACE ";" "[semicolon]" proto_file_display "${proto_file}")
            string(SHA256 dependency_key "${PROTOCYTE_TARGET}|${proto_file}")
            set(dependency_descriptor_rel "CMakeFiles/protocyte-dependencies/${dependency_key}.pb")
            set(dependency_depfile_rel "CMakeFiles/protocyte-dependencies/${dependency_key}.d")
            set(dependency_descriptor "${CMAKE_CURRENT_BINARY_DIR}/${dependency_descriptor_rel}")
            set(dependency_depfile "${CMAKE_CURRENT_BINARY_DIR}/${dependency_depfile_rel}")
            set(dependency_depfile_target "${dependency_descriptor_rel}")
            _protocyte_output_lock_key(dependency_lock_key "${dependency_descriptor}")
            set(dependency_lock_file "${protocyte_lock_dir}/${dependency_lock_key}.lock")
            set(dependency_response_content "")
            foreach(encoded_import_dir IN LISTS encoded_protoc_import_dirs)
                _protocyte_decode_hex_string(import_dir "${encoded_import_dir}")
                _protocyte_append_protoc_response_argument(
                    dependency_response_content
                    "--proto_path=${import_dir}"
                )
            endforeach()
            _protocyte_append_protoc_response_argument(
                dependency_response_content
                "--include_imports"
            )
            _protocyte_append_protoc_response_argument(
                dependency_response_content
                "--descriptor_set_out=${dependency_descriptor_rel}"
            )
            _protocyte_append_protoc_response_argument(
                dependency_response_content
                "${protocyte_protoc_input_${proto_file_key}}"
            )
            _protocyte_write_protoc_response_file(
                dependency_response_file
                dependency_response_file_relative
                "dependency-scan|${dependency_key}"
                "${dependency_response_content}"
            )

            set(protocyte_dependency_depfile "${dependency_depfile_rel}")
            set(protocyte_dependency_uses_untransformed_ninja_depfile FALSE)
            if(CMAKE_GENERATOR MATCHES "^Ninja")
                # CMake's CMP0116 transformation currently removes the escapes that
                # Ninja requires for literal '#' and '$' path characters. The
                # generated file already uses Ninja/GCC depfile syntax and absolute
                # dependency paths, so pass it through unchanged.
                file(
                    RELATIVE_PATH
                    dependency_depfile_target
                    "${CMAKE_BINARY_DIR}"
                    "${dependency_descriptor}"
                )
                string(REPLACE "\\" "/" dependency_depfile_target "${dependency_depfile_target}")
                set(protocyte_dependency_depfile "${dependency_depfile}")
                if(POLICY CMP0116)
                    cmake_policy(PUSH)
                    if(DEFINED CMAKE_WARN_DEPRECATED)
                        set(protocyte_saved_warn_deprecated "${CMAKE_WARN_DEPRECATED}")
                        set(protocyte_had_warn_deprecated TRUE)
                    else()
                        set(protocyte_had_warn_deprecated FALSE)
                    endif()
                    set(CMAKE_WARN_DEPRECATED FALSE)
                    cmake_policy(SET CMP0116 OLD)
                    if(protocyte_had_warn_deprecated)
                        set(CMAKE_WARN_DEPRECATED "${protocyte_saved_warn_deprecated}")
                    else()
                        unset(CMAKE_WARN_DEPRECATED)
                    endif()
                    set(protocyte_dependency_uses_untransformed_ninja_depfile TRUE)
                endif()
            endif()

            add_custom_command(
                OUTPUT "${dependency_descriptor}"
                COMMAND "${CMAKE_COMMAND}" -E make_directory "${protocyte_dependency_dir}"
                COMMAND
                    "${CMAKE_COMMAND}"
                    "-DPROTOC_EXECUTABLE=${PROTOCYTE_PROTOC_EXECUTABLE}"
                    "-DARGUMENT_FILE=${dependency_response_file_relative}"
                    "-DLOCK_FILE=${dependency_lock_file}"
                    "-DPROTO_FILE=${proto_file_display}"
                    "-DSCAN_WORKING_DIRECTORY=${CMAKE_CURRENT_BINARY_DIR}"
                    "-DDEPENDENCY_READER=${protocyte_plugin_executable}"
                    "-DDEPENDENCY_DESCRIPTOR=${dependency_descriptor_rel}"
                    "-DDEPENDENCY_DEPFILE=${dependency_depfile_rel}"
                    "-DDEPENDENCY_DEPFILE_TARGET=${dependency_depfile_target}"
                    "-DDEPENDENCY_FILE_FORMAT=${protocyte_dependency_file_format}"
                    "-DMANAGED_DEPENDENCY_READER=${protocyte_plugin_is_managed}"
                    "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=${PROTOCYTE_TOOL_TIMEOUT_SECONDS}"
                    -P "${protocyte_dependency_scan_script}"
                COMMAND "${CMAKE_COMMAND}" -E touch "${dependency_descriptor}"
                DEPENDS
                    "${proto_file_dependency}"
                    ${protocyte_import_inventory_depends}
                    "${dependency_response_file}"
                    "${protocyte_dependency_scan_script}"
                    "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteProcess.cmake"
                    "${PROTOCYTE_PROTOC_DEPENDENCY}"
                    "${protocyte_plugin_executable}"
                    ${protocyte_generator_sources}
                DEPFILE "${protocyte_dependency_depfile}"
                WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                COMMENT "Scanning protobuf imports for ${proto_file}"
                VERBATIM
            )
            if(protocyte_dependency_uses_untransformed_ninja_depfile)
                cmake_policy(POP)
            endif()
            list(APPEND protocyte_dependency_outputs "${dependency_descriptor}")
        endforeach()
        list(
            APPEND
            protocyte_input_depends
            ${protocyte_dependency_outputs}
            ${protocyte_import_topology_witness}
        )
    else()
        set(protoc_descriptor_argument "--descriptor_set_in=${protocyte_descriptor_set}")
        list(APPEND protocyte_input_depends "${protocyte_descriptor_set}")
    endif()

    set(protocyte_command_outputs "${protocyte_outputs}")
    _protocyte_preflight_output_ownership(
        protocyte_out_dir_owner_marker
        protocyte_out_dir_owner_lock
        protocyte_build_tree_owner_hash
        protocyte_lock_dir
        "${PROTOCYTE_OUT_DIR}"
        protocyte_command_outputs
    )
    _protocyte_register_owned_outputs(
        "${PROTOCYTE_TARGET}"
        "${PROTOCYTE_OUT_DIR}"
        protocyte_command_outputs
    )
    # Generate into an unclaimed sibling tree first.  It deliberately sits
    # outside OUT_DIR: a protobuf path is user-controlled and could otherwise
    # collide with an internal staging path beneath the generated root.
    # ProtocyteGenerate.cmake validates this path again under the output locks
    # and publishes expected files only after protoc and ownership publication
    # both succeed.
    # A stable, target-specific name also lets a retry safely discard only an
    # interrupted attempt's private staging tree.
    string(
        SHA256
        protocyte_generation_staging_key
        "generation-staging|${PROTOCYTE_TARGET}|${PROTOCYTE_OUT_DIR}"
    )
    cmake_path(GET PROTOCYTE_OUT_DIR PARENT_PATH protocyte_out_dir_parent)
    set(
        protocyte_generation_staging_directory
        "${protocyte_out_dir_parent}/.protocyte-generation-staging-${protocyte_generation_staging_key}"
    )
    set(
        protocyte_generation_staged_output_directory
        "${protocyte_generation_staging_directory}/generated"
    )
    if(encoded_generator_parameter STREQUAL "")
        set(
            protocyte_staging_out_arg
            "--protocyte_out=${protocyte_generation_staged_output_directory}"
        )
    else()
        set(
            protocyte_staging_out_arg
            "--protocyte_out=${encoded_generator_parameter}:${protocyte_generation_staged_output_directory}"
        )
    endif()
    set(protocyte_response_content "")
    if(NOT "${protoc_descriptor_argument}" STREQUAL "")
        _protocyte_append_protoc_response_argument(
            protocyte_response_content
            "${protoc_descriptor_argument}"
        )
    endif()
    foreach(encoded_import_dir IN LISTS encoded_protoc_import_dirs)
        _protocyte_decode_hex_string(import_dir "${encoded_import_dir}")
        _protocyte_append_protoc_response_argument(
            protocyte_response_content
            "--proto_path=${import_dir}"
        )
    endforeach()
    _protocyte_append_protoc_response_argument(
        protocyte_response_content
        "--plugin=protoc-gen-protocyte=${protocyte_plugin_executable}"
    )
    _protocyte_append_protoc_response_argument(
        protocyte_response_content
        "${protocyte_staging_out_arg}"
    )
    foreach(proto_file IN LISTS normalized_proto_files)
        if(protocyte_has_DESCRIPTOR_SET)
            set(protocyte_protoc_input "${proto_file}")
        else()
            string(SHA256 proto_file_key "${proto_file}")
            set(
                protocyte_protoc_input
                "${protocyte_protoc_input_${proto_file_key}}"
            )
        endif()
        _protocyte_append_protoc_response_argument(
            protocyte_response_content
            "${protocyte_protoc_input}"
        )
    endforeach()
    _protocyte_write_protoc_response_file(
        protocyte_response_file
        protocyte_response_file_relative
        "generation-staging|${PROTOCYTE_TARGET}|${PROTOCYTE_OUT_DIR}"
        "${protocyte_response_content}"
    )
    set(protocyte_generation_lock_keys)
    foreach(command_output IN LISTS protocyte_command_outputs)
        _protocyte_output_lock_key(output_lock_key "${command_output}")
        list(APPEND protocyte_generation_lock_keys "${output_lock_key}")
    endforeach()
    list(REMOVE_DUPLICATES protocyte_generation_lock_keys)
    list(SORT protocyte_generation_lock_keys)
    _protocyte_write_lock_manifest_file(
        protocyte_generation_lock_manifest
        "generation|${PROTOCYTE_TARGET}|${PROTOCYTE_OUT_DIR}"
        protocyte_generation_lock_keys
    )
    set(protocyte_generation_script "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteGenerate.cmake")
    set(
        protocyte_generation_transaction_script
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteGenerationTransaction.cmake"
    )
    set(
        protocyte_output_safety_script
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteOutputSafety.cmake"
    )
    _protocyte_normalized_path_identity(
        protocyte_lock_directory_identity
        "${protocyte_lock_dir}"
    )
    string(
        SHA256
        protocyte_lock_directory_identity_hash
        "${protocyte_lock_directory_identity}"
    )
    string(HEX "${CMAKE_CURRENT_SOURCE_DIR}" protocyte_source_directory_hex)

    add_custom_command(
        OUTPUT ${protocyte_command_outputs}
        COMMAND
            "${CMAKE_COMMAND}"
            "-DPROTOC_EXECUTABLE=${PROTOCYTE_PROTOC_EXECUTABLE}"
            "-DARGUMENT_FILE=${protocyte_response_file_relative}"
            "-DGENERATION_TARGET=${PROTOCYTE_TARGET}"
            "-DGENERATION_WORKING_DIRECTORY=${CMAKE_CURRENT_BINARY_DIR}"
            "-DLOCK_DIRECTORY=${protocyte_lock_dir}"
            "-DLOCK_DIRECTORY_IDENTITY_SHA256=${protocyte_lock_directory_identity_hash}"
            "-DLOCK_MANIFEST=${protocyte_generation_lock_manifest}"
            "-DOUTPUT_DIRECTORY=${PROTOCYTE_OUT_DIR}"
            "-DSTAGING_OUTPUT_DIRECTORY=${protocyte_generation_staging_directory}"
            "-DOUT_DIR_OWNER_MARKER=${protocyte_out_dir_owner_marker}"
            "-DOUT_DIR_OWNER_LOCK=${protocyte_out_dir_owner_lock}"
            "-DBUILD_OWNER_HASH=${protocyte_build_tree_owner_hash}"
            "-DOWNERSHIP_MANIFEST_DIR=${PROTOCYTE_INTERNAL_CURRENT_OWNED_OUTPUT_MANIFEST_DIR}"
            "-DSOURCE_DIRECTORY_HEX=${protocyte_source_directory_hex}"
            "-DPROTOCYTE_MANAGED_PLUGIN=${protocyte_plugin_is_managed}"
            "-DPROTOCYTE_TOOL_TIMEOUT_SECONDS=${PROTOCYTE_TOOL_TIMEOUT_SECONDS}"
            -P "${protocyte_generation_script}"
        DEPENDS
            ${protocyte_input_depends}
            ${PROTOCYTE_DEPENDS}
            "${protocyte_response_file}"
            "${protocyte_generation_lock_manifest}"
            "${protocyte_generation_script}"
            "${protocyte_generation_transaction_script}"
            "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteProcess.cmake"
            "${protocyte_output_safety_script}"
            "${PROTOCYTE_PROTOC_DEPENDENCY}"
            "${protocyte_plugin_executable}"
            "${protocyte_options_proto}"
            ${protocyte_generator_sources}
        WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
        VERBATIM
    )

    add_custom_target("${PROTOCYTE_TARGET}" DEPENDS ${protocyte_command_outputs})
    if(NOT protocyte_import_guard_target STREQUAL "")
        add_dependencies("${PROTOCYTE_TARGET}" "${protocyte_import_guard_target}")
    endif()

    if(protocyte_has_GENERATED_HEADERS_VAR)
        set(${PROTOCYTE_GENERATED_HEADERS_VAR} "${protocyte_generated_headers}" PARENT_SCOPE)
    endif()
    if(protocyte_has_GENERATED_SOURCES_VAR)
        set(${PROTOCYTE_GENERATED_SOURCES_VAR} "${protocyte_generated_sources}" PARENT_SCOPE)
    endif()
    if(protocyte_has_GENERATED_TARGET_VAR)
        set(${PROTOCYTE_GENERATED_TARGET_VAR} ${PROTOCYTE_TARGET} PARENT_SCOPE)
    endif()
endfunction()

function(protocyte_add_proto_library)
    set(options DISCOVER EMIT_RUNTIME HOSTED_ALLOCATOR)
    set(oneValueArgs
        TARGET
        ALIAS
        TYPE
        DESCRIPTOR_SET
        PROTO_ROOT
        OUT_DIR
        GENERATED_HEADERS_VAR
        GENERATED_SOURCES_VAR
        GENERATED_TARGET_VAR
        RUNTIME_TARGET
        RUNTIME_PREFIX
        NAMESPACE_PREFIX
        INCLUDE_PREFIX
        INSTALL_INCLUDE_DIR
    )
    set(multiValueArgs PROTOS IMPORT_DIRS DEPENDS OPTIONS)
    _protocyte_validate_unique_one_value_keywords_from_argv(
        "protocyte_add_proto_library"
        "${oneValueArgs}"
        "${ARGC}"
    )
    cmake_parse_arguments(
        PARSE_ARGV
        0
        PROTOCYTE
        "${options}"
        "${oneValueArgs}"
        "${multiValueArgs}"
    )
    _protocyte_validate_parsed_arguments(
        "protocyte_add_proto_library"
        "${PROTOCYTE_UNPARSED_ARGUMENTS}"
        "${PROTOCYTE_KEYWORDS_MISSING_VALUES}"
    )
    _protocyte_validate_forwarded_generator_options("protocyte_add_proto_library" ${PROTOCYTE_OPTIONS})

    foreach(name IN LISTS oneValueArgs multiValueArgs)
        _protocyte_value_is_nonempty(protocyte_has_${name} PROTOCYTE_${name})
    endforeach()

    if(NOT protocyte_has_TARGET)
        message(FATAL_ERROR "protocyte_add_proto_library requires TARGET")
    endif()
    if("${PROTOCYTE_TARGET}" MATCHES "::")
        message(
            FATAL_ERROR
            "protocyte_add_proto_library TARGET must not contain '::'; use ALIAS to expose a namespaced target"
        )
    endif()
    if(NOT protocyte_has_DESCRIPTOR_SET AND NOT protocyte_has_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_add_proto_library requires either PROTO_ROOT or DESCRIPTOR_SET")
    endif()
    if(protocyte_has_DESCRIPTOR_SET AND protocyte_has_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_add_proto_library accepts either DESCRIPTOR_SET or PROTO_ROOT, not both")
    endif()
    if(PROTOCYTE_DISCOVER AND protocyte_has_PROTOS)
        message(FATAL_ERROR "protocyte_add_proto_library accepts either DISCOVER or PROTOS, not both")
    endif()
    if(PROTOCYTE_EMIT_RUNTIME AND protocyte_has_RUNTIME_TARGET)
        message(FATAL_ERROR "protocyte_add_proto_library accepts either EMIT_RUNTIME or RUNTIME_TARGET, not both")
    endif()
    if(protocyte_has_RUNTIME_PREFIX AND NOT PROTOCYTE_EMIT_RUNTIME AND NOT protocyte_has_RUNTIME_TARGET)
        if(NOT "${PROTOCYTE_RUNTIME_PREFIX}" STREQUAL "protocyte/runtime")
            message(
                FATAL_ERROR
                "protocyte_add_proto_library requires EMIT_RUNTIME or RUNTIME_TARGET when using a custom RUNTIME_PREFIX"
            )
        endif()
    endif()
    if(protocyte_has_INSTALL_INCLUDE_DIR)
        if("${PROTOCYTE_INSTALL_INCLUDE_DIR}" MATCHES "\\$<")
            message(
                FATAL_ERROR
                "protocyte_add_proto_library INSTALL_INCLUDE_DIR must be a configure-time relative path, not a generator expression"
            )
        endif()
        _protocyte_validate_virtual_directory_prefix(
            "protocyte_add_proto_library INSTALL_INCLUDE_DIR"
            "${PROTOCYTE_INSTALL_INCLUDE_DIR}"
        )
    endif()

    if(NOT protocyte_has_TYPE)
        set(PROTOCYTE_TYPE STATIC)
    endif()

    set(valid_types STATIC SHARED MODULE OBJECT)
    list(FIND valid_types "${PROTOCYTE_TYPE}" protocyte_type_index)
    if(protocyte_type_index EQUAL -1)
        message(FATAL_ERROR "protocyte_add_proto_library TYPE must be one of: STATIC, SHARED, MODULE, OBJECT")
    endif()
    if(NOT PROTOCYTE_DISCOVER AND NOT protocyte_has_PROTOS)
        message(FATAL_ERROR "protocyte_add_proto_library requires either DISCOVER or PROTOS")
    endif()

    set(_protocyte_reflection_api_macro "")
    if(WIN32 AND "${PROTOCYTE_TYPE}" STREQUAL "SHARED")
        string(
            SHA256
            protocyte_reflection_api_hash
            "${CMAKE_CURRENT_SOURCE_DIR}|${CMAKE_CURRENT_BINARY_DIR}|${PROTOCYTE_TARGET}"
        )
        string(TOUPPER "${protocyte_reflection_api_hash}" protocyte_reflection_api_hash)
        set(
            _protocyte_reflection_api_macro
            "PROTOCYTE_REFLECTION_API_${protocyte_reflection_api_hash}"
        )
    endif()

    if(protocyte_has_OUT_DIR)
        if(IS_ABSOLUTE "${PROTOCYTE_OUT_DIR}")
            set(protocyte_include_root "${PROTOCYTE_OUT_DIR}")
        else()
            cmake_path(
                ABSOLUTE_PATH PROTOCYTE_OUT_DIR
                BASE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                OUTPUT_VARIABLE protocyte_include_root
            )
        endif()
    else()
        set(protocyte_include_root "${CMAKE_CURRENT_BINARY_DIR}/${PROTOCYTE_TARGET}_protocyte")
    endif()
    cmake_path(NORMAL_PATH protocyte_include_root)

    set(protocyte_out_dir "${protocyte_include_root}")
    if(protocyte_has_INCLUDE_PREFIX)
        _protocyte_validate_virtual_directory_prefix("include prefix" "${PROTOCYTE_INCLUDE_PREFIX}")
        set(protocyte_out_dir "${protocyte_include_root}/${PROTOCYTE_INCLUDE_PREFIX}")
        cmake_path(NORMAL_PATH protocyte_out_dir)
    endif()

    set(protocyte_codegen_target "${PROTOCYTE_TARGET}__protocyte_codegen")
    set(protocyte_generate_args
        TARGET "${protocyte_codegen_target}"
        OUT_DIR "${protocyte_out_dir}"
        GENERATED_HEADERS_VAR protocyte_generated_headers
        GENERATED_SOURCES_VAR protocyte_generated_sources
        GENERATED_TARGET_VAR protocyte_generated_target
    )
    if(protocyte_has_DESCRIPTOR_SET)
        list(APPEND protocyte_generate_args DESCRIPTOR_SET "${PROTOCYTE_DESCRIPTOR_SET}")
    else()
        list(APPEND protocyte_generate_args PROTO_ROOT "${PROTOCYTE_PROTO_ROOT}")
    endif()
    if(PROTOCYTE_DISCOVER)
        list(APPEND protocyte_generate_args DISCOVER)
    else()
        _protocyte_append_forwarded_values(
            protocyte_generate_args
            PROTOS
            PROTOCYTE_PROTOS
        )
    endif()
    if(PROTOCYTE_EMIT_RUNTIME)
        list(APPEND protocyte_generate_args EMIT_RUNTIME)
    endif()
    if(protocyte_has_IMPORT_DIRS)
        _protocyte_append_forwarded_values(
            protocyte_generate_args
            IMPORT_DIRS
            PROTOCYTE_IMPORT_DIRS
        )
    endif()
    if(protocyte_has_DEPENDS)
        _protocyte_append_forwarded_values(
            protocyte_generate_args
            DEPENDS
            PROTOCYTE_DEPENDS
        )
    endif()
    if(protocyte_has_OPTIONS)
        _protocyte_append_forwarded_values(
            protocyte_generate_args
            OPTIONS
            PROTOCYTE_OPTIONS
        )
    endif()
    if(protocyte_has_RUNTIME_PREFIX)
        list(APPEND protocyte_generate_args RUNTIME_PREFIX "${PROTOCYTE_RUNTIME_PREFIX}")
    endif()
    if(protocyte_has_NAMESPACE_PREFIX)
        list(APPEND protocyte_generate_args NAMESPACE_PREFIX "${PROTOCYTE_NAMESPACE_PREFIX}")
    endif()
    if(protocyte_has_INCLUDE_PREFIX)
        list(APPEND protocyte_generate_args INCLUDE_PREFIX "${PROTOCYTE_INCLUDE_PREFIX}")
    endif()

    protocyte_generate(${protocyte_generate_args})

    add_library("${PROTOCYTE_TARGET}" "${PROTOCYTE_TYPE}")
    if(NOT "${_protocyte_reflection_api_macro}" STREQUAL "")
        target_compile_definitions(
            "${PROTOCYTE_TARGET}"
            PRIVATE "${_protocyte_reflection_api_macro}_EXPORTS=1"
        )
    endif()
    target_sources(
        "${PROTOCYTE_TARGET}"
        PRIVATE
            ${protocyte_generated_sources}
    )
    if(protocyte_has_INSTALL_INCLUDE_DIR)
        target_sources(
            "${PROTOCYTE_TARGET}"
            PUBLIC
                FILE_SET protocyte_generated_headers
                TYPE HEADERS
                BASE_DIRS "${protocyte_include_root}"
                FILES ${protocyte_generated_headers}
        )
    else()
        target_sources("${PROTOCYTE_TARGET}" PRIVATE ${protocyte_generated_headers})
    endif()
    add_dependencies("${PROTOCYTE_TARGET}" "${protocyte_generated_target}")
    target_compile_features("${PROTOCYTE_TARGET}" PUBLIC cxx_std_20)
    target_include_directories(
        "${PROTOCYTE_TARGET}"
        PUBLIC
            "$<BUILD_INTERFACE:${protocyte_include_root}>"
    )
    if(PROTOCYTE_EMIT_RUNTIME AND NOT "${protocyte_include_root}" STREQUAL "${protocyte_out_dir}")
        target_include_directories(
            "${PROTOCYTE_TARGET}"
            PUBLIC
                "$<BUILD_INTERFACE:${protocyte_out_dir}>"
        )
    endif()
    if(protocyte_has_INSTALL_INCLUDE_DIR)
        target_include_directories(
            "${PROTOCYTE_TARGET}"
            PUBLIC
                "$<INSTALL_INTERFACE:${PROTOCYTE_INSTALL_INCLUDE_DIR}>"
        )
        if(PROTOCYTE_EMIT_RUNTIME AND protocyte_has_INCLUDE_PREFIX)
            target_include_directories(
                "${PROTOCYTE_TARGET}"
                PUBLIC
                    "$<INSTALL_INTERFACE:${PROTOCYTE_INSTALL_INCLUDE_DIR}/${PROTOCYTE_INCLUDE_PREFIX}>"
            )
        endif()
    endif()
    target_link_libraries("${PROTOCYTE_TARGET}" PUBLIC protocyte::codegen)

    if(PROTOCYTE_EMIT_RUNTIME)
        if(PROTOCYTE_HOSTED_ALLOCATOR)
            target_compile_definitions("${PROTOCYTE_TARGET}" PUBLIC PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
        endif()
    else()
        if(protocyte_has_RUNTIME_TARGET)
            set(protocyte_runtime_target "${PROTOCYTE_RUNTIME_TARGET}")
        elseif(PROTOCYTE_HOSTED_ALLOCATOR)
            set(protocyte_runtime_target protocyte::runtime_hosted)
        else()
            set(protocyte_runtime_target protocyte::runtime)
        endif()

        if(NOT TARGET "${protocyte_runtime_target}")
            message(FATAL_ERROR "protocyte_add_proto_library runtime target '${protocyte_runtime_target}' does not exist")
        endif()

        target_link_libraries("${PROTOCYTE_TARGET}" PUBLIC "${protocyte_runtime_target}")
    endif()

    if(protocyte_has_ALIAS)
        if(TARGET "${PROTOCYTE_ALIAS}")
            message(FATAL_ERROR "protocyte_add_proto_library alias target '${PROTOCYTE_ALIAS}' already exists")
        endif()
        add_library("${PROTOCYTE_ALIAS}" ALIAS "${PROTOCYTE_TARGET}")
    endif()

    if(protocyte_has_GENERATED_HEADERS_VAR)
        set(${PROTOCYTE_GENERATED_HEADERS_VAR} ${protocyte_generated_headers} PARENT_SCOPE)
    endif()
    if(protocyte_has_GENERATED_SOURCES_VAR)
        set(${PROTOCYTE_GENERATED_SOURCES_VAR} ${protocyte_generated_sources} PARENT_SCOPE)
    endif()
    if(protocyte_has_GENERATED_TARGET_VAR)
        set(${PROTOCYTE_GENERATED_TARGET_VAR} ${protocyte_generated_target} PARENT_SCOPE)
    endif()
endfunction()

function(protocyte_add_descriptor_set_library)
    set(options DISCOVER EMIT_RUNTIME HOSTED_ALLOCATOR)
    set(oneValueArgs
        TARGET
        ALIAS
        TYPE
        DESCRIPTOR_SET
        OUT_DIR
        GENERATED_HEADERS_VAR
        GENERATED_SOURCES_VAR
        GENERATED_TARGET_VAR
        RUNTIME_TARGET
        RUNTIME_PREFIX
        NAMESPACE_PREFIX
        INCLUDE_PREFIX
        INSTALL_INCLUDE_DIR
    )
    set(multiValueArgs FILES DEPENDS OPTIONS)
    _protocyte_validate_unique_one_value_keywords_from_argv(
        "protocyte_add_descriptor_set_library"
        "${oneValueArgs}"
        "${ARGC}"
    )
    cmake_parse_arguments(
        PARSE_ARGV
        0
        PROTOCYTE
        "${options}"
        "${oneValueArgs}"
        "${multiValueArgs}"
    )
    _protocyte_validate_parsed_arguments(
        "protocyte_add_descriptor_set_library"
        "${PROTOCYTE_UNPARSED_ARGUMENTS}"
        "${PROTOCYTE_KEYWORDS_MISSING_VALUES}"
    )
    _protocyte_validate_forwarded_generator_options(
        "protocyte_add_descriptor_set_library"
        ${PROTOCYTE_OPTIONS}
    )

    foreach(name IN LISTS oneValueArgs multiValueArgs)
        _protocyte_value_is_nonempty(protocyte_has_${name} PROTOCYTE_${name})
    endforeach()

    if(NOT protocyte_has_DESCRIPTOR_SET)
        message(FATAL_ERROR "protocyte_add_descriptor_set_library requires DESCRIPTOR_SET")
    endif()
    if(NOT protocyte_has_TARGET)
        message(FATAL_ERROR "protocyte_add_descriptor_set_library requires TARGET")
    endif()
    if(PROTOCYTE_DISCOVER AND protocyte_has_FILES)
        message(FATAL_ERROR "protocyte_add_descriptor_set_library accepts either DISCOVER or FILES, not both")
    endif()
    if(NOT PROTOCYTE_DISCOVER AND NOT protocyte_has_FILES)
        message(FATAL_ERROR "protocyte_add_descriptor_set_library requires either DISCOVER or FILES")
    endif()

    set(args
        TARGET "${PROTOCYTE_TARGET}"
        DESCRIPTOR_SET "${PROTOCYTE_DESCRIPTOR_SET}"
    )
    foreach(name IN ITEMS ALIAS TYPE OUT_DIR GENERATED_HEADERS_VAR GENERATED_SOURCES_VAR GENERATED_TARGET_VAR RUNTIME_TARGET RUNTIME_PREFIX NAMESPACE_PREFIX INCLUDE_PREFIX INSTALL_INCLUDE_DIR)
        if(protocyte_has_${name})
            list(APPEND args ${name} "${PROTOCYTE_${name}}")
        endif()
    endforeach()
    foreach(name IN ITEMS DISCOVER EMIT_RUNTIME HOSTED_ALLOCATOR)
        if(PROTOCYTE_${name})
            list(APPEND args ${name})
        endif()
    endforeach()
    if(protocyte_has_FILES)
        _protocyte_append_forwarded_values(args PROTOS PROTOCYTE_FILES)
    endif()
    if(protocyte_has_DEPENDS)
        _protocyte_append_forwarded_values(args DEPENDS PROTOCYTE_DEPENDS)
    endif()
    if(protocyte_has_OPTIONS)
        _protocyte_append_forwarded_values(args OPTIONS PROTOCYTE_OPTIONS)
    endif()

    protocyte_add_proto_library(${args})

    foreach(name IN ITEMS GENERATED_HEADERS_VAR GENERATED_SOURCES_VAR GENERATED_TARGET_VAR)
        if(protocyte_has_${name})
            set(output_var "${PROTOCYTE_${name}}")
            set(${output_var} ${${output_var}} PARENT_SCOPE)
        endif()
    endforeach()
endfunction()
