include_guard(GLOBAL)

function(_protocyte_normalized_path_identity out_var path)
    cmake_path(NORMAL_PATH path OUTPUT_VARIABLE path_identity)
    if(CMAKE_HOST_WIN32)
        string(TOLOWER "${path_identity}" path_identity)
    endif()
    set(${out_var} "${path_identity}" PARENT_SCOPE)
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
