include_guard(GLOBAL)

include(CMakeParseArguments)

set(_PROTOCYTE_DEFAULT_TOOL_TIMEOUT_SECONDS "300")

function(_protocyte_validate_tool_timeout out_var value context)
    # Keep this deliberately decimal-only.  CMake accepts decimal TIMEOUT
    # values, while exponent notation and special floating-point values make
    # diagnostics and cross-version behavior needlessly surprising.
    if(NOT "${value}" MATCHES "^[0-9]+(\\.[0-9]+)?$")
        message(
            FATAL_ERROR
            "${context} must be a non-negative decimal number of seconds; use 0 to disable the timeout: '${value}'"
        )
    endif()

    # A timeout of zero is an explicit compatibility escape hatch for very
    # large or externally supervised tools.  Every default remains finite.
    if("${value}" MATCHES "^0+(\\.0+)?$")
        set(${out_var} "0" PARENT_SCOPE)
    else()
        set(${out_var} "${value}" PARENT_SCOPE)
    endif()
endfunction()

function(_protocyte_configure_tool_timeout)
    if(NOT DEFINED PROTOCYTE_TOOL_TIMEOUT_SECONDS)
        set(
            PROTOCYTE_TOOL_TIMEOUT_SECONDS
            "${_PROTOCYTE_DEFAULT_TOOL_TIMEOUT_SECONDS}"
            CACHE STRING
            "Maximum seconds for each Protocyte CMake-launched tool; 0 disables the timeout."
        )
    endif()
    _protocyte_validate_tool_timeout(
        validated_timeout
        "${PROTOCYTE_TOOL_TIMEOUT_SECONDS}"
        "PROTOCYTE_TOOL_TIMEOUT_SECONDS"
    )
    set(PROTOCYTE_TOOL_TIMEOUT_SECONDS "${validated_timeout}" PARENT_SCOPE)
endfunction()

function(_protocyte_resolve_tool_timeout out_var)
    if(DEFINED PROTOCYTE_TOOL_TIMEOUT_SECONDS)
        set(configured_timeout "${PROTOCYTE_TOOL_TIMEOUT_SECONDS}")
    else()
        # CMake -P scripts run outside the configure cache.  They use the
        # same safe default unless their invoking custom command forwarded the
        # configured value.
        set(configured_timeout "${_PROTOCYTE_DEFAULT_TOOL_TIMEOUT_SECONDS}")
    endif()
    _protocyte_validate_tool_timeout(
        validated_timeout
        "${configured_timeout}"
        "PROTOCYTE_TOOL_TIMEOUT_SECONDS"
    )
    set(${out_var} "${validated_timeout}" PARENT_SCOPE)
endfunction()

function(_protocyte_execute_bounded out_result out_output out_error out_timed_out)
    cmake_parse_arguments(
        PARSE_ARGV
        4
        execute
        "ECHO_OUTPUT;ECHO_ERROR"
        "WORKING_DIRECTORY;TIMEOUT_SECONDS"
        "COMMAND"
    )
    if(NOT execute_COMMAND)
        message(FATAL_ERROR "Protocyte bounded process launcher requires COMMAND")
    endif()
    if(NOT DEFINED execute_TIMEOUT_SECONDS OR "${execute_TIMEOUT_SECONDS}" STREQUAL "")
        _protocyte_resolve_tool_timeout(execute_timeout)
    else()
        _protocyte_validate_tool_timeout(
            execute_timeout
            "${execute_TIMEOUT_SECONDS}"
            "Protocyte process timeout"
        )
    endif()

    set(execute_timeout_argument)
    if(NOT execute_timeout STREQUAL "0")
        list(APPEND execute_timeout_argument TIMEOUT "${execute_timeout}")
    endif()
    set(execute_working_directory_argument)
    if(DEFINED execute_WORKING_DIRECTORY AND NOT "${execute_WORKING_DIRECTORY}" STREQUAL "")
        list(APPEND execute_working_directory_argument WORKING_DIRECTORY "${execute_WORKING_DIRECTORY}")
    endif()
    set(execute_echo_arguments)
    if(execute_ECHO_OUTPUT)
        list(APPEND execute_echo_arguments ECHO_OUTPUT_VARIABLE)
    endif()
    if(execute_ECHO_ERROR)
        list(APPEND execute_echo_arguments ECHO_ERROR_VARIABLE)
    endif()

    execute_process(
        COMMAND ${execute_COMMAND}
        ${execute_working_directory_argument}
        RESULT_VARIABLE execute_result
        OUTPUT_VARIABLE execute_output
        ERROR_VARIABLE execute_error
        ${execute_timeout_argument}
        ${execute_echo_arguments}
    )
    set(execute_timed_out FALSE)
    if("${execute_result}" STREQUAL "Process terminated due to timeout")
        set(execute_timed_out TRUE)
    endif()
    set(${out_result} "${execute_result}" PARENT_SCOPE)
    set(${out_output} "${execute_output}" PARENT_SCOPE)
    set(${out_error} "${execute_error}" PARENT_SCOPE)
    set(${out_timed_out} "${execute_timed_out}" PARENT_SCOPE)
endfunction()
