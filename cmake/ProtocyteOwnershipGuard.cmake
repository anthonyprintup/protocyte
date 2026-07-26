cmake_minimum_required(VERSION 3.24)

include("${CMAKE_CURRENT_LIST_DIR}/ProtocyteOutputSafety.cmake")

foreach(
    required_variable
    IN ITEMS
        GENERATION_TARGET
        LOCK_DIRECTORY
        LOCK_DIRECTORY_IDENTITY_SHA256
        LOCK_MANIFEST
        OUT_DIR_OWNER_MARKER
        OUT_DIR_OWNER_LOCK
        BUILD_OWNER_HASH
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte ownership guard requires ${required_variable}")
    endif()
endforeach()

if(
    NOT EXISTS "${LOCK_MANIFEST}"
    OR IS_DIRECTORY "${LOCK_MANIFEST}"
    OR IS_SYMLINK "${LOCK_MANIFEST}"
)
    message(
        FATAL_ERROR
        "Protocyte ownership guard lock manifest is missing or unsafe for target "
        "'${GENERATION_TARGET}'. No generated output was changed."
    )
endif()
file(STRINGS "${LOCK_MANIFEST}" output_lock_keys)
if(NOT output_lock_keys)
    message(
        FATAL_ERROR
        "Protocyte ownership guard lock manifest is empty for target "
        "'${GENERATION_TARGET}'. No generated output was changed."
    )
endif()
list(REMOVE_DUPLICATES output_lock_keys)
list(SORT output_lock_keys)

string(LENGTH "${BUILD_OWNER_HASH}" build_owner_hash_length)
if(NOT build_owner_hash_length EQUAL 64 OR NOT BUILD_OWNER_HASH MATCHES "^[0-9a-f]+$")
    message(FATAL_ERROR "Protocyte ownership guard received an invalid build-owner identity")
endif()

_protocyte_validate_generation_lock_namespace()
file(MAKE_DIRECTORY "${LOCK_DIRECTORY}")
_protocyte_validate_generation_lock_namespace()
foreach(output_lock_key IN LISTS output_lock_keys)
    string(LENGTH "${output_lock_key}" output_lock_key_length)
    if(NOT output_lock_key_length EQUAL 64 OR NOT output_lock_key MATCHES "^[0-9a-f]+$")
        message(
            FATAL_ERROR
            "Protocyte ownership guard lock manifest contains an invalid output identity: "
            "${output_lock_key}"
        )
    endif()
    file(
        LOCK "${LOCK_DIRECTORY}/${output_lock_key}.lock"
        GUARD PROCESS
        TIMEOUT 600
        RESULT_VARIABLE output_lock_result
    )
    if(NOT "${output_lock_result}" STREQUAL "0")
        message(
            FATAL_ERROR
            "Protocyte could not lock a generated output while checking ownership for target "
            "'${GENERATION_TARGET}': ${output_lock_result}"
        )
    endif()
endforeach()

cmake_path(GET OUT_DIR_OWNER_LOCK PARENT_PATH owner_lock_parent)
file(MAKE_DIRECTORY "${owner_lock_parent}")
file(
    LOCK "${OUT_DIR_OWNER_LOCK}"
    GUARD PROCESS
    TIMEOUT 600
    RESULT_VARIABLE owner_lock_result
)
if(NOT "${owner_lock_result}" STREQUAL "0")
    message(
        FATAL_ERROR
        "Protocyte could not lock OUT_DIR ownership while checking target "
        "'${GENERATION_TARGET}': ${owner_lock_result}"
    )
endif()

set(different_output_owner_markers)
foreach(output_lock_key IN LISTS output_lock_keys)
    set(output_owner_marker "${LOCK_DIRECTORY}/${output_lock_key}.owner")
    _protocyte_owner_record_status(
        output_owner_status
        output_owner_transaction_id
        "${output_owner_marker}"
        "${BUILD_OWNER_HASH}"
        "${OUT_DIR_OWNER_MARKER}"
    )
    if(output_owner_status STREQUAL "different")
        list(APPEND different_output_owner_markers "${output_owner_marker}")
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
    elseif(
        NOT output_owner_status STREQUAL "missing"
        AND NOT output_owner_status STREQUAL "current"
    )
        message(
            FATAL_ERROR
            "Generated-output ownership is malformed or incomplete for target "
            "'${GENERATION_TARGET}'. No generated output was changed."
        )
    endif()
endforeach()

_protocyte_owner_record_status(
    root_owner_status
    root_owner_transaction_id
    "${OUT_DIR_OWNER_MARKER}"
    "${BUILD_OWNER_HASH}"
    "${OUT_DIR_OWNER_MARKER}"
)
if(root_owner_status STREQUAL "different")
    string(
        REPLACE ";" "\n  "
        different_output_owner_marker_locations
        "${different_output_owner_markers}"
    )
    message(
        FATAL_ERROR
        "OUT_DIR ownership belongs to a different build tree for target "
        "'${GENERATION_TARGET}'. The OUT_DIR owner record is '${OUT_DIR_OWNER_MARKER}'. "
        "The conflicting generated-output owner record(s) are:\n  "
        "${different_output_owner_marker_locations}\n"
        "To transfer this OUT_DIR, first stop every build that could use it and preserve any files "
        "you need. Then remove exactly the owner records listed above and reconfigure. Do not delete "
        "the whole output-lock namespace or cache. No generated output was changed."
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
elseif(
    NOT root_owner_status STREQUAL "missing"
    AND NOT root_owner_status STREQUAL "current"
)
    message(
        FATAL_ERROR
        "OUT_DIR ownership is malformed or incomplete for target "
        "'${GENERATION_TARGET}'. No generated output was changed."
    )
endif()

if(different_output_owner_markers)
    string(
        REPLACE ";" "\n  "
        different_output_owner_marker_locations
        "${different_output_owner_markers}"
    )
    message(
        FATAL_ERROR
        "Generated-output ownership belongs to a different build tree for target "
        "'${GENERATION_TARGET}'. The conflicting generated-output owner record(s) are:\n  "
        "${different_output_owner_marker_locations}\n"
        "To transfer these generated-output claim(s), first stop every build that declares them and "
        "preserve any files you need. Then remove exactly the owner records listed above and reconfigure. "
        "Do not delete the whole output-lock namespace or cache. No generated output was changed."
    )
endif()
