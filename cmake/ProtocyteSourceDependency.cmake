cmake_minimum_required(VERSION 3.24)

foreach(required_variable IN ITEMS SOURCE_ARGUMENT_FILE PROXY_FILE)
    if(NOT DEFINED ${required_variable} OR "${${required_variable}}" STREQUAL "")
        message(FATAL_ERROR "Protocyte source dependency check requires ${required_variable}")
    endif()
endforeach()

file(READ "${SOURCE_ARGUMENT_FILE}" source_file)
if(source_file STREQUAL "")
    message(FATAL_ERROR "Protocyte source dependency path must not be empty")
endif()
if(NOT EXISTS "${source_file}" OR IS_DIRECTORY "${source_file}")
    message(FATAL_ERROR "Protocyte source dependency is not an existing file: ${source_file}")
endif()

file(COPY_FILE "${source_file}" "${PROXY_FILE}" ONLY_IF_DIFFERENT)
