cmake_minimum_required(VERSION 3.24)

foreach(
    required_variable
    IN ITEMS
        OUT_DIR
        EXPECTED_CLAIM
        PROTOCYTE_OUTPUT_LOCK_ROOT
        PROTOCYTE_OUTPUT_COORDINATOR_PYTHON
        PROTOCYTE_OUTPUT_COORDINATOR_SCRIPT
)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte output reset requires ${required_variable}")
    endif()
endforeach()

execute_process(
    COMMAND
        "${CMAKE_COMMAND}" -E env --unset=PYTHONHOME --unset=PYTHONPATH
        "${PROTOCYTE_OUTPUT_COORDINATOR_PYTHON}"
        "${PROTOCYTE_OUTPUT_COORDINATOR_SCRIPT}"
        reset
        --lock-root "${PROTOCYTE_OUTPUT_LOCK_ROOT}"
        --output-root "${OUT_DIR}"
        --expected-claim "${EXPECTED_CLAIM}"
    RESULT_VARIABLE reset_result
    OUTPUT_VARIABLE reset_output
    ERROR_VARIABLE reset_error
    ENCODING UTF-8
)
if(NOT "${reset_result}" STREQUAL "0")
    string(STRIP "${reset_error}" reset_error)
    message(FATAL_ERROR "Protocyte output reset failed.\n${reset_error}")
endif()
