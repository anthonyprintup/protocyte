include_guard(GLOBAL)

include(CMakeParseArguments)
include(FetchContent)

set(PROTOCYTE_REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/.." CACHE INTERNAL "protocyte repository root")
set(PROTOCYTE_PROTO_DIR "${PROTOCYTE_REPO_ROOT}/src/protocyte/proto" CACHE INTERNAL "protocyte proto include root")
set(
    PROTOCYTE_OPTIONS_PROTO
    "${PROTOCYTE_PROTO_DIR}/protocyte/options.proto"
    CACHE INTERNAL
    "protocyte options proto file"
)
set(
    PROTOCYTE_GENERATOR_SOURCES
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/__init__.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/cpp.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/errors.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/main.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/model.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/parameters.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/plugin.py"
    "${PROTOCYTE_REPO_ROOT}/src/protocyte/runtime.py"
    CACHE INTERNAL
    "protocyte generator source files"
)

function(_protocyte_verify_git_commit source_dir expected_commit repo_name)
    if("${expected_commit}" STREQUAL "")
        return()
    endif()

    if(NOT EXISTS "${source_dir}/.git")
        message(
            FATAL_ERROR
            "Cannot verify ${repo_name} commit '${expected_commit}' because '${source_dir}' has no .git directory. "
            "Either supply a git checkout or clear/update the expected commit explicitly."
        )
    endif()

    find_package(Git REQUIRED)
    execute_process(
        COMMAND "${GIT_EXECUTABLE}" rev-parse HEAD
        WORKING_DIRECTORY "${source_dir}"
        OUTPUT_VARIABLE actual_commit
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE git_result
    )

    if(NOT git_result EQUAL 0)
        message(FATAL_ERROR "Failed to resolve ${repo_name} commit in '${source_dir}'")
    endif()

    if(NOT actual_commit STREQUAL expected_commit)
        message(
            FATAL_ERROR
            "Resolved ${repo_name} commit '${actual_commit}' does not match expected commit '${expected_commit}' "
            "for tag '${PROTOCYTE_PROTOBUF_GIT_TAG}'."
        )
    endif()
endfunction()

function(_protocyte_write_plugin_wrapper)
    if(DEFINED PROTOCYTE_PLUGIN_EXECUTABLE)
        return()
    endif()

    find_package(Python3 COMPONENTS Interpreter REQUIRED)

    if(WIN32)
        set(wrapper "${CMAKE_CURRENT_BINARY_DIR}/protoc-gen-protocyte.cmd")
        file(WRITE "${wrapper}"
            "@echo off\r\n"
            "set \"PYTHONPATH=${PROTOCYTE_REPO_ROOT}/src;%PYTHONPATH%\"\r\n"
            "\"${Python3_EXECUTABLE}\" -m protocyte.main\r\n"
        )
    else()
        set(wrapper "${CMAKE_CURRENT_BINARY_DIR}/protoc-gen-protocyte")
        file(WRITE "${wrapper}"
            "#!/usr/bin/env sh\n"
            "PYTHONPATH='${PROTOCYTE_REPO_ROOT}/src':$PYTHONPATH exec '${Python3_EXECUTABLE}' -m protocyte.main\n"
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
        find_package(Protobuf QUIET)

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
            _protocyte_verify_git_commit(
                "${protobuf_source_dir}"
                "${PROTOCYTE_PROTOBUF_GIT_COMMIT}"
                "protobuf"
            )
            set(protoc_executable "$<TARGET_FILE:protobuf::protoc>")
        else()
            find_program(protoc_executable protoc REQUIRED)
        endif()
    endif()

    set(PROTOCYTE_PROTOC_EXECUTABLE "${protoc_executable}" CACHE INTERNAL "protoc executable for protocyte")
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
        list(APPEND protocyte_generated_sources "${PROTOCYTE_OUT_DIR}/${runtime_prefix}/runtime.cpp")
    endif()

    set(protocyte_outputs
        ${protocyte_generated_headers}
        ${protocyte_generated_sources}
    )

    set(protocyte_import_dirs "${PROTOCYTE_PROTO_ROOT}" ${PROTOCYTE_IMPORT_DIRS} "${PROTOCYTE_PROTO_DIR}")
    list(REMOVE_DUPLICATES protocyte_import_dirs)

    set(protoc_proto_paths)
    foreach(import_dir IN LISTS protocyte_import_dirs)
        list(APPEND protoc_proto_paths "--proto_path=${import_dir}")
    endforeach()

    if(generator_parameter STREQUAL "")
        set(protocyte_out_arg "--protocyte_out=${PROTOCYTE_OUT_DIR}")
    else()
        set(protocyte_out_arg "--protocyte_out=${generator_parameter}:${PROTOCYTE_OUT_DIR}")
    endif()

    _protocyte_write_plugin_wrapper()
    _protocyte_ensure_protobuf()

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
            "${PROTOCYTE_OPTIONS_PROTO}"
            ${PROTOCYTE_GENERATOR_SOURCES}
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

_protocyte_write_plugin_wrapper()
if(PROTOCYTE_FETCH_PROTOBUF)
    _protocyte_ensure_protobuf()
endif()
