include_guard(GLOBAL)

include(CMakeParseArguments)
include(FetchContent)

function(_protocyte_encode_generator_parameter out_var value)
    if("${value}" STREQUAL "")
        set(${out_var} "" PARENT_SCOPE)
        return()
    endif()

    string(HEX "${value}" encoded)
    set(${out_var} "_protocyte_options_hex=${encoded}" PARENT_SCOPE)
endfunction()

function(_protocyte_descriptor_name_is_unsafe out_var name)
    if(IS_ABSOLUTE "${name}" OR "${name}" MATCHES "^[A-Za-z]:" OR "${name}" MATCHES "\\\\")
        set(${out_var} TRUE PARENT_SCOPE)
    else()
        set(${out_var} FALSE PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_validate_descriptor_name name)
    if("${name}" STREQUAL "")
        message(FATAL_ERROR "descriptor file name must not be empty")
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

function(_protocyte_validate_forwarded_generator_options)
    foreach(generator_option IN LISTS ARGN)
        string(REPLACE "," ";" generator_option_parts "${generator_option}")
        foreach(generator_option_part IN LISTS generator_option_parts)
            string(FIND "${generator_option_part}" "=" option_separator)
            if(option_separator EQUAL -1)
                continue()
            endif()
            string(SUBSTRING "${generator_option_part}" 0 ${option_separator} generator_option_name)
            string(STRIP "${generator_option_name}" generator_option_name)
            math(EXPR option_value_start "${option_separator} + 1")
            string(SUBSTRING "${generator_option_part}" ${option_value_start} -1 generator_option_value)

            if(generator_option_name MATCHES "^_protocyte_")
                message(
                    FATAL_ERROR
                    "protocyte_generate OPTIONS must not use reserved _protocyte_ transport parameters"
                )
            elseif(generator_option_name STREQUAL "runtime" OR generator_option_name STREQUAL "runtime_prefix")
                message(
                    FATAL_ERROR
                    "protocyte_generate OPTIONS must not set runtime or runtime_prefix; "
                    "use EMIT_RUNTIME and RUNTIME_PREFIX so CMake can declare runtime outputs consistently"
                )
            elseif(generator_option_name STREQUAL "include_prefix")
                _protocyte_validate_virtual_directory_prefix("include prefix" "${generator_option_value}")
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
    set(${out_var} "${normalized}.protocyte" PARENT_SCOPE)
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

function(_protocyte_descriptor_outputs out_headers out_sources out_dir proto_names_var)
    set(headers)
    set(sources)
    foreach(proto_name IN LISTS ${proto_names_var})
        _protocyte_validate_descriptor_name("${proto_name}")
        _protocyte_normalize_generated_path(normalized_generated_path "${proto_name}")
        set(protocyte_base "${out_dir}/${normalized_generated_path}")
        list(APPEND headers "${protocyte_base}.hpp")
        list(APPEND sources "${protocyte_base}.cpp")
    endforeach()
    set(${out_headers} "${headers}" PARENT_SCOPE)
    set(${out_sources} "${sources}" PARENT_SCOPE)
endfunction()

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
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${protocyte_plugin_executable}")

    execute_process(
        COMMAND
            "${protocyte_plugin_executable}" descriptor-set list "${descriptor_set}"
        OUTPUT_VARIABLE discovered
        ERROR_VARIABLE discover_error
        RESULT_VARIABLE discover_result
        OUTPUT_STRIP_TRAILING_WHITESPACE
        TIMEOUT 30
    )
    if(NOT "${discover_result}" STREQUAL "0")
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
            "Failed to inspect descriptor set '${descriptor_set}'.\n\n"
            "Command:\n  \"${protocyte_plugin_executable}\" descriptor-set list \"${descriptor_set}\"\n"
            "Exit code: ${discover_result}\n\n"
            "Standard output:\n${discovered_output}\n\n"
            "Standard error:\n${discover_error}\n\n"
            "PROTOCYTE_PLUGIN_EXECUTABLE overrides must point to a Protocyte plugin that supports "
            "the 'descriptor-set list' command."
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
    _protocyte_verify_python_environment
    out_result
    out_output
    out_error
    python_executable
    plugin_executable
    constraints_file
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

requirements = [
    line.strip()
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
expected = dict(requirement.split("==", 1) for requirement in requirements)
mismatches = {
    name: (wanted, version(name))
    for name, wanted in expected.items()
    if version(name) != wanted
}
if mismatches:
    raise RuntimeError(f"managed Python package versions do not match constraints: {mismatches}")

import google.protobuf
import protocyte.main
]=])
    execute_process(
        COMMAND "${python_executable}" -c "${verify_script}" "${constraints_file}"
        RESULT_VARIABLE verify_result
        OUTPUT_VARIABLE verify_output
        ERROR_VARIABLE verify_error
    )
    if("${verify_result}" STREQUAL "0")
        execute_process(
            COMMAND "${python_executable}" -m pip check
            RESULT_VARIABLE pip_check_result
            OUTPUT_VARIABLE pip_check_output
            ERROR_VARIABLE pip_check_error
        )
        string(APPEND verify_output "${pip_check_output}")
        string(APPEND verify_error "${pip_check_error}")
        if(NOT "${pip_check_result}" STREQUAL "0")
            set(verify_result "${pip_check_result}")
        endif()
    endif()
    if("${verify_result}" STREQUAL "0")
        execute_process(
            COMMAND "${plugin_executable}" --version
            RESULT_VARIABLE plugin_verify_result
            OUTPUT_VARIABLE plugin_verify_output
            ERROR_VARIABLE plugin_verify_error
        )
        string(APPEND verify_output "${plugin_verify_output}")
        string(APPEND verify_error "${plugin_verify_error}")
        if(NOT "${plugin_verify_result}" STREQUAL "0")
            set(verify_result "${plugin_verify_result}")
        endif()
    endif()

    set(${out_result} "${verify_result}" PARENT_SCOPE)
    set(${out_output} "${verify_output}" PARENT_SCOPE)
    set(${out_error} "${verify_error}" PARENT_SCOPE)
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
    set(protocyte_python_ready "${protocyte_python_environment}/.protocyte-ready")
    _protocyte_python_environment_paths(
        protocyte_python_executable
        protocyte_plugin_executable
        "${protocyte_python_environment}"
    )

    set(protocyte_python_needs_provisioning TRUE)
    if(
        EXISTS "${protocyte_python_ready}"
        AND EXISTS "${protocyte_python_executable}"
        AND EXISTS "${protocyte_plugin_executable}"
    )
        file(READ "${protocyte_python_ready}" cached_fingerprint)
        string(STRIP "${cached_fingerprint}" cached_fingerprint)
        if(cached_fingerprint STREQUAL protocyte_python_fingerprint)
            _protocyte_verify_python_environment(
                cached_verify_result
                cached_verify_output
                cached_verify_error
                "${protocyte_python_executable}"
                "${protocyte_plugin_executable}"
                "${protocyte_python_constraints}"
            )
            if("${cached_verify_result}" STREQUAL "0")
                set(protocyte_python_needs_provisioning FALSE)
            endif()
        endif()
    endif()

    if(protocyte_python_needs_provisioning)
        message(STATUS "Provisioning Protocyte Python environment: ${protocyte_python_environment}")
        file(MAKE_DIRECTORY "${protocyte_python_env_root}")

        set(venv_arguments -m venv)
        if(IS_DIRECTORY "${protocyte_python_environment}")
            list(APPEND venv_arguments --clear)
        endif()
        list(APPEND venv_arguments "${protocyte_python_environment}")
        execute_process(
            COMMAND "${Python3_EXECUTABLE}" ${venv_arguments}
            RESULT_VARIABLE venv_result
            OUTPUT_VARIABLE venv_output
            ERROR_VARIABLE venv_error
            TIMEOUT 120
        )
        if(NOT "${venv_result}" STREQUAL "0")
            string(JOIN " " venv_command ${venv_arguments})
            _protocyte_python_provisioning_error(
                "create the virtual environment; ensure the selected Python provides venv and ensurepip"
                "\"${Python3_EXECUTABLE}\" ${venv_command}"
                "${venv_result}"
                "${venv_output}"
                "${venv_error}"
            )
        endif()

        set(protocyte_staged_project "${protocyte_python_environment}/project")
        set(protocyte_staged_constraints "${protocyte_staged_project}/protocyte-cmake-constraints.txt")
        _protocyte_stage_python_project(
            "${protocyte_python_project_root}"
            "${protocyte_python_constraints}"
            "${protocyte_staged_project}"
        )

        execute_process(
            COMMAND
                "${protocyte_python_executable}" -m pip install
                --disable-pip-version-check
                --no-input
                --upgrade
                --force-reinstall
                --constraint "${protocyte_staged_constraints}"
                pip setuptools wheel
            RESULT_VARIABLE bootstrap_result
            OUTPUT_VARIABLE bootstrap_output
            ERROR_VARIABLE bootstrap_error
            TIMEOUT 300
        )
        if(NOT "${bootstrap_result}" STREQUAL "0")
            _protocyte_python_provisioning_error(
                "install Protocyte's pinned Python build tools"
                "\"${protocyte_python_executable}\" -m pip install --disable-pip-version-check --no-input --upgrade --force-reinstall --constraint \"${protocyte_staged_constraints}\" pip setuptools wheel"
                "${bootstrap_result}"
                "${bootstrap_output}"
                "${bootstrap_error}"
            )
        endif()

        execute_process(
            COMMAND
                "${protocyte_python_executable}" -m pip install
                --disable-pip-version-check
                --no-input
                --no-build-isolation
                --upgrade
                --force-reinstall
                --constraint "${protocyte_staged_constraints}"
                "${protocyte_staged_project}"
            RESULT_VARIABLE install_result
            OUTPUT_VARIABLE install_output
            ERROR_VARIABLE install_error
            TIMEOUT 300
        )
        if(NOT "${install_result}" STREQUAL "0")
            _protocyte_python_provisioning_error(
                "install Protocyte and its Python dependencies"
                "\"${protocyte_python_executable}\" -m pip install --disable-pip-version-check --no-input --no-build-isolation --upgrade --force-reinstall --constraint \"${protocyte_staged_constraints}\" \"${protocyte_staged_project}\""
                "${install_result}"
                "${install_output}"
                "${install_error}"
            )
        endif()

        _protocyte_verify_python_environment(
            verify_result
            verify_output
            verify_error
            "${protocyte_python_executable}"
            "${protocyte_plugin_executable}"
            "${protocyte_python_constraints}"
        )
        if(NOT "${verify_result}" STREQUAL "0")
            _protocyte_python_provisioning_error(
                "verify the installed Protocyte plugin"
                "\"${protocyte_plugin_executable}\" --version"
                "${verify_result}"
                "${verify_output}"
                "${verify_error}"
            )
        endif()

        file(WRITE "${protocyte_python_ready}" "${protocyte_python_fingerprint}\n")
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

    if(NOT EXISTS "${candidate_dir}/google/protobuf/descriptor.proto")
        return()
    endif()

    set(
        PROTOCYTE_PROTOBUF_IMPORT_DIR
        "${candidate_dir}"
        CACHE INTERNAL
        "protobuf import root containing google/protobuf/descriptor.proto"
    )
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

    set(configured_import_dir "${PROTOCYTE_PROTOBUF_IMPORT_DIR}")
    if(NOT configured_import_dir STREQUAL "")
        _protocyte_resolve_stable_filesystem_path(
            resolved_configured_import_dir
            "${configured_import_dir}"
            PROTOBUF_IMPORT
        )
        set(auto_import_dir "${PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR}")
        if(
            NOT auto_import_dir STREQUAL ""
            AND resolved_configured_import_dir STREQUAL auto_import_dir
        )
            if(
                "${PROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN}" STREQUAL "${toolchain_identity}"
                AND EXISTS "${auto_import_dir}/google/protobuf/descriptor.proto"
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
            unset(PROTOCYTE_PROTOBUF_IMPORT_DIR CACHE)
            unset(PROTOCYTE_INTERNAL_AUTO_PROTOBUF_IMPORT_DIR CACHE)
            unset(PROTOCYTE_INTERNAL_AUTO_PROTOBUF_TOOLCHAIN CACHE)
        else()
            set(${out_explicit} TRUE PARENT_SCOPE)
            if(
                IS_DIRECTORY "${resolved_configured_import_dir}"
                AND EXISTS "${resolved_configured_import_dir}/google/protobuf/descriptor.proto"
            )
                _protocyte_set_resolved_protobuf_import_dir("${resolved_configured_import_dir}")
            endif()
            return()
        endif()
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

function(_protocyte_prepare_plugin)
    _protocyte_get_internal(protocyte_prepared_plugin PLUGIN_EXECUTABLE)
    if(NOT "${protocyte_prepared_plugin}" STREQUAL "")
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
    else()
        _protocyte_ensure_python_environment(protocyte_python_executable protocyte_plugin_executable)
    endif()

    set_property(GLOBAL PROPERTY PROTOCYTE_INTERNAL_PLUGIN_EXECUTABLE "${protocyte_plugin_executable}")
endfunction()

function(_protocyte_ensure_protobuf fetch_missing_import_sources)
    if(TARGET protobuf::protoc)
        set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
        set(protoc_dependency protobuf::protoc)
    elseif(TARGET protoc)
        set(protoc_executable "$<TARGET_FILE:protoc>")
        set(protoc_dependency protoc)
    else()
        find_package(Protobuf CONFIG QUIET)
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
            FetchContent_GetProperties(protobuf SOURCE_DIR protobuf_SOURCE_DIR)
            set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
            set(protoc_dependency protobuf::protoc)
        else()
            find_program(protoc_executable protoc REQUIRED)
            _protocyte_resolve_protoc_path(
                protoc_executable
                protoc_dependency
                "${protoc_executable}"
            )
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
endfunction()

function(_protocyte_setup_codegen_internal fetch_missing_import_sources)
    _protocyte_prepare_plugin()
    _protocyte_ensure_protobuf("${fetch_missing_import_sources}")
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
    cmake_parse_arguments(PROTOCYTE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    _protocyte_validate_parsed_arguments(
        "protocyte_generate"
        "${PROTOCYTE_UNPARSED_ARGUMENTS}"
        "${PROTOCYTE_KEYWORDS_MISSING_VALUES}"
    )

    if(NOT PROTOCYTE_TARGET)
        message(FATAL_ERROR "protocyte_generate requires TARGET")
    endif()
    if(NOT PROTOCYTE_DESCRIPTOR_SET AND NOT PROTOCYTE_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_generate requires PROTO_ROOT")
    endif()
    if(NOT PROTOCYTE_OUT_DIR)
        message(FATAL_ERROR "protocyte_generate requires OUT_DIR")
    endif()
    if(NOT IS_ABSOLUTE "${PROTOCYTE_OUT_DIR}")
        cmake_path(
            ABSOLUTE_PATH PROTOCYTE_OUT_DIR
            BASE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
            NORMALIZE
            OUTPUT_VARIABLE PROTOCYTE_OUT_DIR
        )
    endif()
    if(PROTOCYTE_DISCOVER AND PROTOCYTE_PROTOS)
        message(FATAL_ERROR "protocyte_generate accepts either DISCOVER or PROTOS, not both")
    endif()
    _protocyte_validate_forwarded_generator_options(${PROTOCYTE_OPTIONS})

    if(PROTOCYTE_DESCRIPTOR_SET)
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
        if(NOT EXISTS "${protocyte_descriptor_set}" OR IS_DIRECTORY "${protocyte_descriptor_set}")
            message(FATAL_ERROR "protocyte_generate DESCRIPTOR_SET must be an existing file: ${protocyte_descriptor_set}")
        endif()
        if(PROTOCYTE_PROTO_ROOT)
            message(FATAL_ERROR "protocyte_generate accepts either DESCRIPTOR_SET or PROTO_ROOT, not both")
        endif()
        if(PROTOCYTE_IMPORT_DIRS)
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

    set(protocyte_user_import_dirs)
    set(protocyte_needs_fallback_import_sources FALSE)
    if(NOT PROTOCYTE_DESCRIPTOR_SET)
        if(NOT IS_DIRECTORY "${protocyte_proto_root}")
            message(FATAL_ERROR "protocyte_generate PROTO_ROOT must be an existing directory: ${protocyte_proto_root}")
        endif()
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
            list(APPEND protocyte_user_import_dirs "${import_dir_abs}")
        endforeach()
        list(REMOVE_DUPLICATES protocyte_user_import_dirs)
        set(protocyte_needs_fallback_import_sources TRUE)
        foreach(import_dir IN LISTS protocyte_proto_root protocyte_user_import_dirs)
            if(EXISTS "${import_dir}/google/protobuf/descriptor.proto")
                set(protocyte_needs_fallback_import_sources FALSE)
                break()
            endif()
        endforeach()
    endif()

    if(PROTOCYTE_DESCRIPTOR_SET AND PROTOCYTE_DISCOVER)
        set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${protocyte_descriptor_set}")
        _protocyte_setup_codegen_internal(FALSE)
        _protocyte_discover_descriptor_set(protocyte_proto_files "${protocyte_descriptor_set}")
    elseif(PROTOCYTE_DISCOVER)
        file(GLOB_RECURSE protocyte_proto_files CONFIGURE_DEPENDS "${protocyte_proto_root}/*.proto")
    else()
        set(protocyte_proto_files ${PROTOCYTE_PROTOS})
    endif()

    if(NOT protocyte_proto_files)
        message(FATAL_ERROR "protocyte_generate did not receive any .proto files")
    endif()

    set(normalized_proto_files)
    if(PROTOCYTE_DESCRIPTOR_SET)
        foreach(proto_file IN LISTS protocyte_proto_files)
            _protocyte_validate_descriptor_name("${proto_file}")
            string(SHA256 proto_file_key "${proto_file}")
            if(DEFINED protocyte_seen_proto_file_${proto_file_key})
                continue()
            endif()
            set(protocyte_seen_proto_file_${proto_file_key} TRUE)
            string(REPLACE ";" "\\;" proto_file_list_element "${proto_file}")
            list(APPEND normalized_proto_files "${proto_file_list_element}")
        endforeach()
    else()
        foreach(proto_file IN LISTS protocyte_proto_files)
            if(IS_ABSOLUTE "${proto_file}")
                set(proto_abs "${proto_file}")
            else()
                cmake_path(ABSOLUTE_PATH proto_file BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" OUTPUT_VARIABLE proto_abs)
            endif()

            if(NOT EXISTS "${proto_abs}" OR IS_DIRECTORY "${proto_abs}")
                message(FATAL_ERROR "protocyte_generate PROTOS entry must be an existing file: ${proto_abs}")
            endif()

            file(RELATIVE_PATH proto_rel "${protocyte_proto_root}" "${proto_abs}")
            if(proto_rel MATCHES "^[.][.]")
                message(FATAL_ERROR "proto file '${proto_abs}' is outside PROTO_ROOT '${protocyte_proto_root}'")
            endif()

            list(APPEND normalized_proto_files "${proto_abs}")
        endforeach()
        list(REMOVE_DUPLICATES normalized_proto_files)
        list(SORT normalized_proto_files)
    endif()

    if(NOT PROTOCYTE_DESCRIPTOR_SET OR NOT PROTOCYTE_DISCOVER)
        if(PROTOCYTE_DESCRIPTOR_SET)
            _protocyte_setup_codegen_internal(FALSE)
        else()
            _protocyte_setup_codegen_internal("${protocyte_needs_fallback_import_sources}")
        endif()
    endif()
    _protocyte_get_internal(protocyte_proto_dir PROTO_DIR)
    _protocyte_get_internal(protocyte_options_proto OPTIONS_PROTO)
    _protocyte_get_internal(protocyte_generator_sources GENERATOR_SOURCES)
    _protocyte_get_internal(protocyte_plugin_executable PLUGIN_EXECUTABLE)
    if("${protocyte_plugin_executable}" STREQUAL "")
        message(FATAL_ERROR "Protocyte code generation plugin was not prepared")
    endif()

    set(generator_options ${PROTOCYTE_OPTIONS})
    if(PROTOCYTE_NAMESPACE_PREFIX)
        list(APPEND generator_options "namespace_prefix=${PROTOCYTE_NAMESPACE_PREFIX}")
    endif()
    if(PROTOCYTE_INCLUDE_PREFIX)
        _protocyte_validate_virtual_directory_prefix("include prefix" "${PROTOCYTE_INCLUDE_PREFIX}")
        list(APPEND generator_options "include_prefix=${PROTOCYTE_INCLUDE_PREFIX}")
    endif()

    if(PROTOCYTE_EMIT_RUNTIME)
        if(PROTOCYTE_RUNTIME_PREFIX)
            _protocyte_validate_virtual_directory_prefix("runtime prefix" "${PROTOCYTE_RUNTIME_PREFIX}")
            set(runtime_prefix "${PROTOCYTE_RUNTIME_PREFIX}")
            list(APPEND generator_options "runtime=emit:${PROTOCYTE_RUNTIME_PREFIX}")
        else()
            set(runtime_prefix "protocyte/runtime")
            list(APPEND generator_options "runtime=emit")
        endif()
    elseif(PROTOCYTE_RUNTIME_PREFIX)
        _protocyte_validate_virtual_directory_prefix("runtime prefix" "${PROTOCYTE_RUNTIME_PREFIX}")
        set(runtime_prefix "${PROTOCYTE_RUNTIME_PREFIX}")
        list(APPEND generator_options "runtime_prefix=${PROTOCYTE_RUNTIME_PREFIX}")
    else()
        set(runtime_prefix "protocyte/runtime")
    endif()

    string(JOIN "," generator_parameter ${generator_options})
    _protocyte_encode_generator_parameter(encoded_generator_parameter "${generator_parameter}")

    set(protocyte_generated_headers)
    set(protocyte_generated_sources)
    if(PROTOCYTE_DESCRIPTOR_SET)
        _protocyte_descriptor_outputs(
            protocyte_generated_headers
            protocyte_generated_sources
            "${PROTOCYTE_OUT_DIR}"
            normalized_proto_files
        )
    else()
        foreach(proto_file IN LISTS normalized_proto_files)
            file(RELATIVE_PATH proto_rel "${protocyte_proto_root}" "${proto_file}")
            string(REPLACE "\\" "/" proto_rel "${proto_rel}")
            _protocyte_validate_descriptor_name("${proto_rel}")
            _protocyte_normalize_generated_path(normalized_generated_path "${proto_rel}")
            set(protocyte_base "${PROTOCYTE_OUT_DIR}/${normalized_generated_path}")

            list(APPEND protocyte_generated_headers "${protocyte_base}.hpp")
            list(APPEND protocyte_generated_sources "${protocyte_base}.cpp")
        endforeach()
    endif()

    if(PROTOCYTE_EMIT_RUNTIME)
        list(APPEND protocyte_generated_headers "${PROTOCYTE_OUT_DIR}/${runtime_prefix}/runtime.hpp")
    endif()

    set(protocyte_outputs "${protocyte_generated_headers}" "${protocyte_generated_sources}")

    set(protoc_proto_paths)
    set(protoc_descriptor_args)
    set(protocyte_input_depends)
    if(NOT PROTOCYTE_DESCRIPTOR_SET)
        set(protocyte_input_depends ${normalized_proto_files})
        set(
            protocyte_import_dirs
            "${protocyte_proto_root}"
            ${protocyte_user_import_dirs}
            "${protocyte_proto_dir}"
            "${PROTOCYTE_INTERNAL_RESOLVED_PROTOBUF_IMPORT_DIR}"
        )
        list(REMOVE_DUPLICATES protocyte_import_dirs)

        set(has_protobuf_descriptor_proto FALSE)
        foreach(import_dir IN LISTS protocyte_import_dirs)
            if(EXISTS "${import_dir}/google/protobuf/descriptor.proto")
                set(has_protobuf_descriptor_proto TRUE)
                break()
            endif()
        endforeach()

        if(NOT has_protobuf_descriptor_proto)
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

        foreach(import_dir IN LISTS protocyte_import_dirs)
            list(APPEND protoc_proto_paths "--proto_path=${import_dir}")
        endforeach()

        set(protocyte_dependency_dir "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/protocyte-dependencies")
        set(protocyte_dependency_scan_script "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/ProtocyteDependencyScan.cmake")
        set(protocyte_dependency_outputs)
        foreach(proto_file IN LISTS normalized_proto_files)
            string(SHA256 dependency_key "${PROTOCYTE_TARGET}|${proto_file}")
            set(dependency_descriptor_rel "CMakeFiles/protocyte-dependencies/${dependency_key}.pb")
            set(dependency_depfile_rel "CMakeFiles/protocyte-dependencies/${dependency_key}.d")
            set(dependency_descriptor "${CMAKE_CURRENT_BINARY_DIR}/${dependency_descriptor_rel}")

            add_custom_command(
                OUTPUT "${dependency_descriptor}"
                COMMAND "${CMAKE_COMMAND}" -E make_directory "${protocyte_dependency_dir}"
                COMMAND
                    "${CMAKE_COMMAND}"
                    "-DPROTOC_EXECUTABLE=${PROTOCYTE_PROTOC_EXECUTABLE}"
                    "-DPROTO_PATH_ARGUMENTS=${protoc_proto_paths}"
                    "-DDEPENDENCY_OUT=${dependency_depfile_rel}"
                    "-DDESCRIPTOR_SET_OUT=${dependency_descriptor_rel}"
                    "-DPROTO_FILE=${proto_file}"
                    "-DSCAN_WORKING_DIRECTORY=${CMAKE_CURRENT_BINARY_DIR}"
                    -P "${protocyte_dependency_scan_script}"
                COMMAND "${CMAKE_COMMAND}" -E touch "${dependency_descriptor}"
                DEPENDS
                    "${proto_file}"
                    "${protocyte_dependency_scan_script}"
                    "${PROTOCYTE_PROTOC_DEPENDENCY}"
                DEPFILE "${dependency_depfile_rel}"
                WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                COMMENT "Scanning protobuf imports for ${proto_file}"
                VERBATIM
            )
            list(APPEND protocyte_dependency_outputs "${dependency_descriptor}")
        endforeach()
        list(APPEND protocyte_input_depends ${protocyte_dependency_outputs})
    else()
        list(APPEND protoc_descriptor_args "--descriptor_set_in=${protocyte_descriptor_set}")
        list(APPEND protocyte_input_depends "${protocyte_descriptor_set}")
    endif()

    if(encoded_generator_parameter STREQUAL "")
        set(protocyte_out_arg "--protocyte_out=${PROTOCYTE_OUT_DIR}")
    else()
        set(protocyte_out_arg "--protocyte_out=${encoded_generator_parameter}:${PROTOCYTE_OUT_DIR}")
    endif()

    set(protocyte_command_outputs "${protocyte_outputs}")

    add_custom_command(
        OUTPUT ${protocyte_command_outputs}
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${PROTOCYTE_OUT_DIR}"
        COMMAND "${PROTOCYTE_PROTOC_EXECUTABLE}"
            ${protoc_descriptor_args}
            ${protoc_proto_paths}
            "--plugin=protoc-gen-protocyte=${protocyte_plugin_executable}"
            "${protocyte_out_arg}"
            ${normalized_proto_files}
        DEPENDS
            ${protocyte_input_depends}
            ${PROTOCYTE_DEPENDS}
            "${PROTOCYTE_PROTOC_DEPENDENCY}"
            "${protocyte_plugin_executable}"
            "${protocyte_options_proto}"
            ${protocyte_generator_sources}
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        VERBATIM
    )

    add_custom_target("${PROTOCYTE_TARGET}" DEPENDS ${protocyte_command_outputs})

    if(PROTOCYTE_GENERATED_HEADERS_VAR)
        set(${PROTOCYTE_GENERATED_HEADERS_VAR} "${protocyte_generated_headers}" PARENT_SCOPE)
    endif()
    if(PROTOCYTE_GENERATED_SOURCES_VAR)
        set(${PROTOCYTE_GENERATED_SOURCES_VAR} "${protocyte_generated_sources}" PARENT_SCOPE)
    endif()
    if(PROTOCYTE_GENERATED_TARGET_VAR)
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
    )
    set(multiValueArgs PROTOS IMPORT_DIRS DEPENDS OPTIONS)
    cmake_parse_arguments(PROTOCYTE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    _protocyte_validate_parsed_arguments(
        "protocyte_add_proto_library"
        "${PROTOCYTE_UNPARSED_ARGUMENTS}"
        "${PROTOCYTE_KEYWORDS_MISSING_VALUES}"
    )

    if(NOT PROTOCYTE_TARGET)
        message(FATAL_ERROR "protocyte_add_proto_library requires TARGET")
    endif()
    if(PROTOCYTE_TARGET MATCHES "::")
        message(
            FATAL_ERROR
            "protocyte_add_proto_library TARGET must not contain '::'; use ALIAS to expose a namespaced target"
        )
    endif()
    if(NOT PROTOCYTE_DESCRIPTOR_SET AND NOT PROTOCYTE_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_add_proto_library requires PROTO_ROOT")
    endif()
    if(PROTOCYTE_DESCRIPTOR_SET AND PROTOCYTE_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_add_proto_library accepts either DESCRIPTOR_SET or PROTO_ROOT, not both")
    endif()
    if(PROTOCYTE_EMIT_RUNTIME AND PROTOCYTE_RUNTIME_TARGET)
        message(FATAL_ERROR "protocyte_add_proto_library accepts either EMIT_RUNTIME or RUNTIME_TARGET, not both")
    endif()
    if(PROTOCYTE_RUNTIME_PREFIX AND NOT PROTOCYTE_EMIT_RUNTIME AND NOT PROTOCYTE_RUNTIME_TARGET)
        if(NOT PROTOCYTE_RUNTIME_PREFIX STREQUAL "protocyte/runtime")
            message(
                FATAL_ERROR
                "protocyte_add_proto_library requires EMIT_RUNTIME or RUNTIME_TARGET when using a custom RUNTIME_PREFIX"
            )
        endif()
    endif()

    if(NOT PROTOCYTE_TYPE)
        set(PROTOCYTE_TYPE STATIC)
    endif()

    set(valid_types STATIC SHARED MODULE OBJECT)
    list(FIND valid_types "${PROTOCYTE_TYPE}" protocyte_type_index)
    if(protocyte_type_index EQUAL -1)
        message(FATAL_ERROR "protocyte_add_proto_library TYPE must be one of: STATIC, SHARED, MODULE, OBJECT")
    endif()

    if(PROTOCYTE_OUT_DIR)
        if(IS_ABSOLUTE "${PROTOCYTE_OUT_DIR}")
            set(protocyte_out_dir "${PROTOCYTE_OUT_DIR}")
        else()
            cmake_path(
                ABSOLUTE_PATH PROTOCYTE_OUT_DIR
                BASE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
                OUTPUT_VARIABLE protocyte_out_dir
            )
        endif()
    else()
        set(protocyte_out_dir "${CMAKE_CURRENT_BINARY_DIR}/${PROTOCYTE_TARGET}_protocyte")
    endif()

    set(protocyte_codegen_target "${PROTOCYTE_TARGET}__protocyte_codegen")
    set(protocyte_generate_args
        TARGET "${protocyte_codegen_target}"
        OUT_DIR "${protocyte_out_dir}"
        GENERATED_HEADERS_VAR protocyte_generated_headers
        GENERATED_SOURCES_VAR protocyte_generated_sources
        GENERATED_TARGET_VAR protocyte_generated_target
    )
    if(PROTOCYTE_DESCRIPTOR_SET)
        list(APPEND protocyte_generate_args DESCRIPTOR_SET "${PROTOCYTE_DESCRIPTOR_SET}")
    else()
        list(APPEND protocyte_generate_args PROTO_ROOT "${PROTOCYTE_PROTO_ROOT}")
    endif()
    if(PROTOCYTE_DISCOVER)
        list(APPEND protocyte_generate_args DISCOVER)
    else()
        list(APPEND protocyte_generate_args PROTOS ${PROTOCYTE_PROTOS})
    endif()
    if(PROTOCYTE_EMIT_RUNTIME)
        list(APPEND protocyte_generate_args EMIT_RUNTIME)
    endif()
    if(PROTOCYTE_IMPORT_DIRS)
        list(APPEND protocyte_generate_args IMPORT_DIRS ${PROTOCYTE_IMPORT_DIRS})
    endif()
    if(PROTOCYTE_DEPENDS)
        list(APPEND protocyte_generate_args DEPENDS ${PROTOCYTE_DEPENDS})
    endif()
    if(PROTOCYTE_OPTIONS)
        list(APPEND protocyte_generate_args OPTIONS ${PROTOCYTE_OPTIONS})
    endif()
    if(PROTOCYTE_RUNTIME_PREFIX)
        list(APPEND protocyte_generate_args RUNTIME_PREFIX "${PROTOCYTE_RUNTIME_PREFIX}")
    endif()
    if(PROTOCYTE_NAMESPACE_PREFIX)
        list(APPEND protocyte_generate_args NAMESPACE_PREFIX "${PROTOCYTE_NAMESPACE_PREFIX}")
    endif()
    if(PROTOCYTE_INCLUDE_PREFIX)
        list(APPEND protocyte_generate_args INCLUDE_PREFIX "${PROTOCYTE_INCLUDE_PREFIX}")
    endif()

    protocyte_generate(${protocyte_generate_args})

    add_library("${PROTOCYTE_TARGET}" "${PROTOCYTE_TYPE}")
    target_sources(
        "${PROTOCYTE_TARGET}"
        PRIVATE
            ${protocyte_generated_sources}
            ${protocyte_generated_headers}
    )
    add_dependencies("${PROTOCYTE_TARGET}" "${protocyte_generated_target}")
    target_compile_features("${PROTOCYTE_TARGET}" PUBLIC cxx_std_20)
    target_include_directories("${PROTOCYTE_TARGET}" PUBLIC "${protocyte_out_dir}")
    target_link_libraries("${PROTOCYTE_TARGET}" PUBLIC protocyte::codegen)

    if(PROTOCYTE_EMIT_RUNTIME)
        if(PROTOCYTE_HOSTED_ALLOCATOR)
            target_compile_definitions("${PROTOCYTE_TARGET}" PUBLIC PROTOCYTE_ENABLE_HOSTED_ALLOCATOR=1)
        endif()
    else()
        if(PROTOCYTE_RUNTIME_TARGET)
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

    if(PROTOCYTE_ALIAS)
        if(TARGET "${PROTOCYTE_ALIAS}")
            message(FATAL_ERROR "protocyte_add_proto_library alias target '${PROTOCYTE_ALIAS}' already exists")
        endif()
        add_library("${PROTOCYTE_ALIAS}" ALIAS "${PROTOCYTE_TARGET}")
    endif()

    if(PROTOCYTE_GENERATED_HEADERS_VAR)
        set(${PROTOCYTE_GENERATED_HEADERS_VAR} ${protocyte_generated_headers} PARENT_SCOPE)
    endif()
    if(PROTOCYTE_GENERATED_SOURCES_VAR)
        set(${PROTOCYTE_GENERATED_SOURCES_VAR} ${protocyte_generated_sources} PARENT_SCOPE)
    endif()
    if(PROTOCYTE_GENERATED_TARGET_VAR)
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
    )
    set(multiValueArgs FILES DEPENDS OPTIONS)
    cmake_parse_arguments(PROTOCYTE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    _protocyte_validate_parsed_arguments(
        "protocyte_add_descriptor_set_library"
        "${PROTOCYTE_UNPARSED_ARGUMENTS}"
        "${PROTOCYTE_KEYWORDS_MISSING_VALUES}"
    )

    if(NOT PROTOCYTE_DESCRIPTOR_SET)
        message(FATAL_ERROR "protocyte_add_descriptor_set_library requires DESCRIPTOR_SET")
    endif()

    set(args
        TARGET "${PROTOCYTE_TARGET}"
        DESCRIPTOR_SET "${PROTOCYTE_DESCRIPTOR_SET}"
    )
    foreach(name IN ITEMS ALIAS TYPE OUT_DIR GENERATED_HEADERS_VAR GENERATED_SOURCES_VAR GENERATED_TARGET_VAR RUNTIME_TARGET RUNTIME_PREFIX NAMESPACE_PREFIX INCLUDE_PREFIX)
        if(PROTOCYTE_${name})
            list(APPEND args ${name} "${PROTOCYTE_${name}}")
        endif()
    endforeach()
    foreach(name IN ITEMS DISCOVER EMIT_RUNTIME HOSTED_ALLOCATOR)
        if(PROTOCYTE_${name})
            list(APPEND args ${name})
        endif()
    endforeach()
    if(PROTOCYTE_FILES)
        list(APPEND args PROTOS ${PROTOCYTE_FILES})
    endif()
    if(PROTOCYTE_DEPENDS)
        list(APPEND args DEPENDS ${PROTOCYTE_DEPENDS})
    endif()
    if(PROTOCYTE_OPTIONS)
        list(APPEND args OPTIONS ${PROTOCYTE_OPTIONS})
    endif()

    protocyte_add_proto_library(${args})

    foreach(name IN ITEMS GENERATED_HEADERS_VAR GENERATED_SOURCES_VAR GENERATED_TARGET_VAR)
        if(PROTOCYTE_${name})
            set(output_var "${PROTOCYTE_${name}}")
            set(${output_var} ${${output_var}} PARENT_SCOPE)
        endif()
    endforeach()
endfunction()
