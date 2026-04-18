# Redistribution and use is allowed under the OSI-approved 3-clause BSD license.
# Copyright (c) 2018 Sergey Podobry.
#
# Minimal WDK finder for smoke-test drivers. It locates the newest installed
# WDK and provides wdk_add_driver(<target> <sources...>).

get_filename_component(WDK_ROOT
    "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows Kits\\Installed Roots;KitsRoot10]"
    ABSOLUTE
)

file(GLOB WDK_NTDDK_FILES "${WDK_ROOT}/Include/*/km/ntddk.h")
if(WDK_NTDDK_FILES)
    if(NOT CMAKE_VERSION VERSION_LESS 3.18)
        list(SORT WDK_NTDDK_FILES COMPARE NATURAL)
    endif()
    list(GET WDK_NTDDK_FILES -1 WDK_LATEST_NTDDK_FILE)
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(WDK REQUIRED_VARS WDK_LATEST_NTDDK_FILE)
if(NOT WDK_FOUND)
    return()
endif()

get_filename_component(WDK_ROOT "${WDK_LATEST_NTDDK_FILE}" DIRECTORY)
get_filename_component(WDK_ROOT "${WDK_ROOT}" DIRECTORY)
get_filename_component(WDK_VERSION "${WDK_ROOT}" NAME)
get_filename_component(WDK_ROOT "${WDK_ROOT}" DIRECTORY)
if(NOT WDK_ROOT MATCHES ".*/[0-9][0-9.]*$")
    get_filename_component(WDK_ROOT "${WDK_ROOT}" DIRECTORY)
    set(WDK_LIB_VERSION "${WDK_VERSION}")
    set(WDK_INC_VERSION "${WDK_VERSION}")
else()
    set(WDK_INC_VERSION "")
    foreach(VERSION winv6.3 win8 win7)
        if(EXISTS "${WDK_ROOT}/Lib/${VERSION}/")
            set(WDK_LIB_VERSION "${VERSION}")
            break()
        endif()
    endforeach()
    set(WDK_VERSION "${WDK_LIB_VERSION}")
endif()

set(WDK_WINVER "0x0A00" CACHE STRING "Default _WIN32_WINNT for WDK targets")
set(WDK_NTDDI_VERSION "" CACHE STRING "Optional NTDDI_VERSION for WDK targets")
option(WDK_SIGN_DRIVER "Sign WDK smoke drivers after build." OFF)
set(WDK_PFX "" CACHE FILEPATH "Optional PFX used when WDK_SIGN_DRIVER is ON")

if(CMAKE_SIZEOF_VOID_P EQUAL 4)
    set(WDK_PLATFORM "x86")
    set(WDK_ARCH_DEFINITIONS "_X86_=1;i386=1;STD_CALL")
elseif(CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(WDK_PLATFORM "x64")
    set(WDK_ARCH_DEFINITIONS "_WIN64;_AMD64_;AMD64")
else()
    message(FATAL_ERROR "Unsupported WDK architecture")
endif()

file(GLOB WDK_LIBRARIES "${WDK_ROOT}/Lib/${WDK_LIB_VERSION}/km/${WDK_PLATFORM}/*.lib")
foreach(LIBRARY IN LISTS WDK_LIBRARIES)
    get_filename_component(LIBRARY_NAME "${LIBRARY}" NAME_WE)
    string(TOUPPER "${LIBRARY_NAME}" LIBRARY_NAME)
    if(NOT TARGET WDK::${LIBRARY_NAME})
        add_library(WDK::${LIBRARY_NAME} INTERFACE IMPORTED)
        set_property(TARGET WDK::${LIBRARY_NAME} PROPERTY INTERFACE_LINK_LIBRARIES "${LIBRARY}")
    endif()
endforeach()

find_program(WDK_SIGNTOOL signtool
    HINTS "${WDK_ROOT}/bin"
    PATH_SUFFIXES "${WDK_VERSION}/x64" "${WDK_VERSION}/x86" x64 x86
)

function(wdk_add_driver target)
    add_executable(${target} ${ARGN})
    set_target_properties(${target} PROPERTIES
        SUFFIX ".sys"
        LINK_FLAGS "/MANIFEST:NO /DRIVER /OPT:REF /INCREMENTAL:NO /OPT:ICF /SUBSYSTEM:NATIVE /MERGE:_TEXT=.text /MERGE:.retplne=.rdata /NODEFAULTLIB /SECTION:INIT,ERD /VERSION:10.0 -tsaware:no"
    )

    target_compile_options(${target} PRIVATE
        /Zp8
        /GF
        /GR-
        /D_HAS_STATIC_RTTI=0
        /D_STATIC_CPPLIB=1
        /D_CRTIMP=
        /kernel
    )
    target_compile_definitions(${target} PRIVATE
        WINNT=1
        _WIN32_WINNT=${WDK_WINVER}
        ${WDK_ARCH_DEFINITIONS}
        $<$<CONFIG:Debug>:MSC_NOOPT;DEPRECATE_DDK_FUNCTIONS=1;DBG=1>
    )
    if(WDK_NTDDI_VERSION)
        target_compile_definitions(${target} PRIVATE NTDDI_VERSION=${WDK_NTDDI_VERSION})
    endif()

    target_include_directories(${target} SYSTEM PRIVATE
        "${WDK_ROOT}/Include/${WDK_INC_VERSION}/shared"
        "${WDK_ROOT}/Include/${WDK_INC_VERSION}/km"
    )
    target_link_libraries(${target} PRIVATE WDK::NTOSKRNL WDK::HAL WDK::BUFFEROVERFLOWK WDK::WMILIB)
    if(CMAKE_SIZEOF_VOID_P EQUAL 4 AND TARGET WDK::MEMCMP)
        target_link_libraries(${target} PRIVATE WDK::MEMCMP)
        set_property(TARGET ${target} APPEND_STRING PROPERTY LINK_FLAGS " /ENTRY:GsDriverEntry@8")
    else()
        set_property(TARGET ${target} APPEND_STRING PROPERTY LINK_FLAGS " /ENTRY:GsDriverEntry")
    endif()

    if(WDK_SIGN_DRIVER)
        if(NOT WDK_SIGNTOOL OR NOT EXISTS "${WDK_PFX}")
            message(FATAL_ERROR "WDK_SIGN_DRIVER requires WDK_SIGNTOOL and WDK_PFX")
        endif()
        add_custom_command(
            TARGET ${target} POST_BUILD
            COMMAND "${WDK_SIGNTOOL}" sign /fd SHA256 /f "${WDK_PFX}" "$<TARGET_FILE:${target}>"
            VERBATIM
        )
    endif()
endfunction()
