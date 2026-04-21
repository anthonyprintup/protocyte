include_guard(GLOBAL)

include(CMakeParseArguments)
include(FetchContent)

function(_protocyte_shell_single_quote out_var value)
    string(REPLACE "'" "'\"'\"'" escaped "${value}")
    set(${out_var} "'${escaped}'" PARENT_SCOPE)
endfunction()

function(_protocyte_get_internal out_var name)
    get_property(value GLOBAL PROPERTY "PROTOCYTE_INTERNAL_${name}")
    if(NOT DEFINED value OR value STREQUAL "")
        set(fallback_var "PROTOCYTE_${name}")
        if(DEFINED ${fallback_var})
            set(value "${${fallback_var}}")
        endif()
    endif()
    set(${out_var} "${value}" PARENT_SCOPE)
endfunction()

function(_protocyte_set_protobuf_import_dir candidate_dir)
    if("${candidate_dir}" STREQUAL "")
        return()
    endif()

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
endfunction()

function(_protocyte_resolve_protobuf_import_dir)
    if(DEFINED PROTOCYTE_PROTOBUF_IMPORT_DIR AND NOT PROTOCYTE_PROTOBUF_IMPORT_DIR STREQUAL "")
        return()
    endif()

    if(DEFINED protobuf_SOURCE_DIR AND EXISTS "${protobuf_SOURCE_DIR}/src/google/protobuf/descriptor.proto")
        _protocyte_set_protobuf_import_dir("${protobuf_SOURCE_DIR}/src")
        return()
    endif()

    if(DEFINED Protobuf_INCLUDE_DIRS)
        foreach(include_dir IN LISTS Protobuf_INCLUDE_DIRS)
            _protocyte_set_protobuf_import_dir("${include_dir}")
            if(DEFINED PROTOCYTE_PROTOBUF_IMPORT_DIR AND NOT PROTOCYTE_PROTOBUF_IMPORT_DIR STREQUAL "")
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

            _protocyte_set_protobuf_import_dir("${include_dir}")
            if(DEFINED PROTOCYTE_PROTOBUF_IMPORT_DIR AND NOT PROTOCYTE_PROTOBUF_IMPORT_DIR STREQUAL "")
                return()
            endif()
        endforeach()
    endforeach()

    if(
        DEFINED Protobuf_PROTOC_EXECUTABLE
        AND NOT Protobuf_PROTOC_EXECUTABLE STREQUAL ""
        AND NOT Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
    )
        cmake_path(GET Protobuf_PROTOC_EXECUTABLE PARENT_PATH protoc_bin_dir)
        _protocyte_set_protobuf_import_dir("${protoc_bin_dir}/../include")
        if(DEFINED PROTOCYTE_PROTOBUF_IMPORT_DIR AND NOT PROTOCYTE_PROTOBUF_IMPORT_DIR STREQUAL "")
            return()
        endif()
    endif()
endfunction()

function(_protocyte_write_plugin_wrapper)
    if(DEFINED PROTOCYTE_PLUGIN_EXECUTABLE)
        return()
    endif()

    _protocyte_get_internal(protocyte_python_source_root PYTHON_SOURCE_ROOT)
    if("${protocyte_python_source_root}" STREQUAL "")
        message(FATAL_ERROR "protocyte is missing PROTOCYTE_PYTHON_SOURCE_ROOT")
    endif()

    find_package(Python3 COMPONENTS Interpreter REQUIRED)

    if(WIN32)
        set(wrapper "${CMAKE_CURRENT_BINARY_DIR}/protoc-gen-protocyte.cmd")
        file(WRITE "${wrapper}"
            "@echo off\r\n"
            "set \"PYTHONPATH=${protocyte_python_source_root};%PYTHONPATH%\"\r\n"
            "\"${Python3_EXECUTABLE}\" -m protocyte.main\r\n"
        )
    else()
        set(wrapper "${CMAKE_CURRENT_BINARY_DIR}/protoc-gen-protocyte")
        _protocyte_shell_single_quote(protocyte_python_source_root_shell "${protocyte_python_source_root}")
        _protocyte_shell_single_quote(python3_executable_shell "${Python3_EXECUTABLE}")
        file(WRITE "${wrapper}"
            "#!/usr/bin/env sh\n"
            "PYTHONPATH=${protocyte_python_source_root_shell}:$PYTHONPATH exec ${python3_executable_shell} -m protocyte.main\n"
        )
        file(
            CHMOD "${wrapper}"
            PERMISSIONS
            OWNER_READ OWNER_WRITE OWNER_EXECUTE
            GROUP_READ GROUP_EXECUTE
            WORLD_READ WORLD_EXECUTE
        )
    endif()

    set(PROTOCYTE_PLUGIN_EXECUTABLE "${wrapper}" CACHE INTERNAL "protocyte protoc plugin wrapper")
endfunction()

function(_protocyte_ensure_protobuf)
    if(TARGET protobuf::protoc)
        set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
    elseif(TARGET protoc)
        set(protoc_executable "$<TARGET_FILE:protoc>")
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
        elseif(
            DEFINED Protobuf_PROTOC_EXECUTABLE
            AND NOT Protobuf_PROTOC_EXECUTABLE STREQUAL ""
            AND NOT Protobuf_PROTOC_EXECUTABLE MATCHES "-NOTFOUND$"
        )
            set(protoc_executable "${Protobuf_PROTOC_EXECUTABLE}")
        elseif(PROTOCYTE_FETCH_PROTOBUF)
            set(protobuf_BUILD_TESTS OFF CACHE BOOL "" FORCE)
            set(protobuf_BUILD_CONFORMANCE OFF CACHE BOOL "" FORCE)
            set(protobuf_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
            set(protobuf_BUILD_PROTOBUF_BINARIES ON CACHE BOOL "" FORCE)
            FetchContent_Declare(
                protobuf
                GIT_REPOSITORY https://github.com/protocolbuffers/protobuf.git
                GIT_TAG "${PROTOCYTE_PROTOBUF_GIT_TAG}"
            )
            FetchContent_MakeAvailable(protobuf)
            FetchContent_GetProperties(protobuf SOURCE_DIR protobuf_source_dir)
            _protocyte_set_protobuf_import_dir("${protobuf_source_dir}/src")
            set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
        else()
            find_program(protoc_executable protoc REQUIRED)
        endif()
    endif()

    set(PROTOCYTE_PROTOC_EXECUTABLE "${protoc_executable}" CACHE INTERNAL "protoc executable for protocyte")
    _protocyte_resolve_protobuf_import_dir()
endfunction()

function(protocyte_setup_codegen)
    _protocyte_write_plugin_wrapper()
    _protocyte_ensure_protobuf()
endfunction()

function(protocyte_generate)
    set(options DISCOVER EMIT_RUNTIME)
    set(oneValueArgs
        TARGET
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

    if(NOT PROTOCYTE_TARGET)
        message(FATAL_ERROR "protocyte_generate requires TARGET")
    endif()
    if(NOT PROTOCYTE_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_generate requires PROTO_ROOT")
    endif()
    if(NOT PROTOCYTE_OUT_DIR)
        message(FATAL_ERROR "protocyte_generate requires OUT_DIR")
    endif()
    if(PROTOCYTE_DISCOVER AND PROTOCYTE_PROTOS)
        message(FATAL_ERROR "protocyte_generate accepts either DISCOVER or PROTOS, not both")
    endif()

    if(PROTOCYTE_DISCOVER)
        file(GLOB_RECURSE protocyte_proto_files CONFIGURE_DEPENDS "${PROTOCYTE_PROTO_ROOT}/*.proto")
    else()
        set(protocyte_proto_files ${PROTOCYTE_PROTOS})
    endif()

    if(NOT protocyte_proto_files)
        message(FATAL_ERROR "protocyte_generate did not receive any .proto files")
    endif()

    protocyte_setup_codegen()
    _protocyte_get_internal(protocyte_proto_dir PROTO_DIR)
    _protocyte_get_internal(protocyte_options_proto OPTIONS_PROTO)
    _protocyte_get_internal(protocyte_generator_sources GENERATOR_SOURCES)

    set(normalized_proto_files)
    foreach(proto_file IN LISTS protocyte_proto_files)
        if(IS_ABSOLUTE "${proto_file}")
            set(proto_abs "${proto_file}")
        else()
            cmake_path(ABSOLUTE_PATH proto_file BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" OUTPUT_VARIABLE proto_abs)
        endif()

        file(RELATIVE_PATH proto_rel "${PROTOCYTE_PROTO_ROOT}" "${proto_abs}")
        if(proto_rel MATCHES "^[.][.]")
            message(FATAL_ERROR "proto file '${proto_abs}' is outside PROTO_ROOT '${PROTOCYTE_PROTO_ROOT}'")
        endif()

        list(APPEND normalized_proto_files "${proto_abs}")
    endforeach()
    list(REMOVE_DUPLICATES normalized_proto_files)
    list(SORT normalized_proto_files)

    set(generator_options ${PROTOCYTE_OPTIONS})
    if(PROTOCYTE_NAMESPACE_PREFIX)
        list(APPEND generator_options "namespace_prefix=${PROTOCYTE_NAMESPACE_PREFIX}")
    endif()
    if(PROTOCYTE_INCLUDE_PREFIX)
        list(APPEND generator_options "include_prefix=${PROTOCYTE_INCLUDE_PREFIX}")
    endif()

    if(PROTOCYTE_EMIT_RUNTIME)
        if(PROTOCYTE_RUNTIME_PREFIX)
            set(runtime_prefix "${PROTOCYTE_RUNTIME_PREFIX}")
            list(APPEND generator_options "runtime=emit:${PROTOCYTE_RUNTIME_PREFIX}")
        else()
            set(runtime_prefix "protocyte/runtime")
            list(APPEND generator_options "runtime=emit")
        endif()
    elseif(PROTOCYTE_RUNTIME_PREFIX)
        set(runtime_prefix "${PROTOCYTE_RUNTIME_PREFIX}")
        list(APPEND generator_options "runtime_prefix=${PROTOCYTE_RUNTIME_PREFIX}")
    else()
        set(runtime_prefix "protocyte/runtime")
    endif()

    string(JOIN "," generator_parameter ${generator_options})

    set(protocyte_generated_headers)
    set(protocyte_generated_sources)
    foreach(proto_file IN LISTS normalized_proto_files)
        file(RELATIVE_PATH proto_rel "${PROTOCYTE_PROTO_ROOT}" "${proto_file}")
        get_filename_component(proto_rel_dir "${proto_rel}" DIRECTORY)
        get_filename_component(proto_stem "${proto_rel}" NAME_WLE)

        if(proto_rel_dir STREQUAL "")
            set(protocyte_base "${PROTOCYTE_OUT_DIR}/${proto_stem}.protocyte")
        else()
            set(protocyte_base "${PROTOCYTE_OUT_DIR}/${proto_rel_dir}/${proto_stem}.protocyte")
        endif()

        list(APPEND protocyte_generated_headers "${protocyte_base}.hpp")
        list(APPEND protocyte_generated_sources "${protocyte_base}.cpp")
    endforeach()

    if(PROTOCYTE_EMIT_RUNTIME)
        list(APPEND protocyte_generated_headers "${PROTOCYTE_OUT_DIR}/${runtime_prefix}/runtime.hpp")
    endif()

    set(protocyte_outputs
        ${protocyte_generated_headers}
        ${protocyte_generated_sources}
    )

    set(
        protocyte_import_dirs
        "${PROTOCYTE_PROTO_ROOT}"
        ${PROTOCYTE_IMPORT_DIRS}
        "${protocyte_proto_dir}"
        "${PROTOCYTE_PROTOBUF_IMPORT_DIR}"
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
        message(
            FATAL_ERROR
            "protocyte_generate could not locate google/protobuf/descriptor.proto. "
            "Install protobuf headers or configure a matching import root via PROTOCYTE_PROTOBUF_IMPORT_DIR/IMPORT_DIRS."
        )
    endif()

    set(protoc_proto_paths)
    foreach(import_dir IN LISTS protocyte_import_dirs)
        list(APPEND protoc_proto_paths "--proto_path=${import_dir}")
    endforeach()

    if(generator_parameter STREQUAL "")
        set(protocyte_out_arg "--protocyte_out=${PROTOCYTE_OUT_DIR}")
    else()
        set(protocyte_out_arg "--protocyte_out=${generator_parameter}:${PROTOCYTE_OUT_DIR}")
    endif()

    add_custom_command(
        OUTPUT ${protocyte_outputs}
        COMMAND "${CMAKE_COMMAND}" -E make_directory "${PROTOCYTE_OUT_DIR}"
        COMMAND "${PROTOCYTE_PROTOC_EXECUTABLE}"
            ${protoc_proto_paths}
            "--plugin=protoc-gen-protocyte=${PROTOCYTE_PLUGIN_EXECUTABLE}"
            "${protocyte_out_arg}"
            ${normalized_proto_files}
        DEPENDS
            ${normalized_proto_files}
            ${PROTOCYTE_DEPENDS}
            "${protocyte_options_proto}"
            ${protocyte_generator_sources}
        VERBATIM
        COMMAND_EXPAND_LISTS
    )

    add_custom_target("${PROTOCYTE_TARGET}" DEPENDS ${protocyte_outputs})

    if(PROTOCYTE_GENERATED_HEADERS_VAR)
        set(${PROTOCYTE_GENERATED_HEADERS_VAR} ${protocyte_generated_headers} PARENT_SCOPE)
    endif()
    if(PROTOCYTE_GENERATED_SOURCES_VAR)
        set(${PROTOCYTE_GENERATED_SOURCES_VAR} ${protocyte_generated_sources} PARENT_SCOPE)
    endif()
    if(PROTOCYTE_GENERATED_TARGET_VAR)
        set(${PROTOCYTE_GENERATED_TARGET_VAR} ${PROTOCYTE_TARGET} PARENT_SCOPE)
    endif()
endfunction()

function(protocyte_add_proto_library)
    set(options DISCOVER EMIT_RUNTIME HOSTED_ALLOCATOR)
    set(oneValueArgs
        TARGET
        TYPE
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

    if(NOT PROTOCYTE_TARGET)
        message(FATAL_ERROR "protocyte_add_proto_library requires TARGET")
    endif()
    if(NOT PROTOCYTE_PROTO_ROOT)
        message(FATAL_ERROR "protocyte_add_proto_library requires PROTO_ROOT")
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
        PROTO_ROOT "${PROTOCYTE_PROTO_ROOT}"
        OUT_DIR "${protocyte_out_dir}"
        GENERATED_HEADERS_VAR protocyte_generated_headers
        GENERATED_SOURCES_VAR protocyte_generated_sources
        GENERATED_TARGET_VAR protocyte_generated_target
    )
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
