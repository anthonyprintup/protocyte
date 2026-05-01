#include <ntddk.h>
#include <stdint.h>

#include "example.protocyte.hpp"
#include "protocyte/runtime/runtime.hpp"

#ifdef __cplusplus
extern "C" {
#endif
    int _fltused = 0;
#ifdef __cplusplus
}

void __cdecl operator delete(void *ptr) noexcept {
    if (ptr != nullptr) {
        ExFreePool(ptr);
    }
}

void __cdecl operator delete(void *ptr, size_t) noexcept { ::operator delete(ptr); }

void __cdecl operator delete[](void *ptr) noexcept { ::operator delete(ptr); }

void __cdecl operator delete[](void *ptr, size_t) noexcept { ::operator delete(ptr); }
#endif

#if PROTOCYTE_ENABLE_STD_STRING_VIEW && defined(_DEBUG)
// MSVC's debug STL imports these CRT assertion hooks through __imp_* data symbols.
__declspec(noreturn) void protocyte_debug_crt_shim_bugcheck(const char *symbol_name) {
    DbgPrintEx(DPFLTR_IHVDRIVER_ID, DPFLTR_ERROR_LEVEL,
               "Protocyte kernel smoke: MSVC STL debug CRT fallback called for %s.\n", symbol_name);
    KeBugCheckEx(MANUALLY_INITIATED_CRASH, 0x50535643u, 0u, 0u, 0u);
    for (;;) {}
}

extern "C" __declspec(noreturn) void __cdecl protocyte_invoke_watson_shim(const wchar_t *, const wchar_t *,
                                                                          const wchar_t *, unsigned int, uintptr_t) {
    protocyte_debug_crt_shim_bugcheck("_invoke_watson");
}

extern "C" int __cdecl protocyte_crt_dbg_report_shim(int, const char *, int, const char *, const char *, ...) {
    protocyte_debug_crt_shim_bugcheck("_CrtDbgReport");
}

using protocyte_invoke_watson_fn = void(__cdecl *)(const wchar_t *, const wchar_t *, const wchar_t *, unsigned int,
                                                   uintptr_t);
using protocyte_crt_dbg_report_fn = int(__cdecl *)(int, const char *, int, const char *, const char *, ...);

extern "C" {
    protocyte_invoke_watson_fn __imp__invoke_watson = &protocyte_invoke_watson_shim;
    protocyte_crt_dbg_report_fn __imp__CrtDbgReport = &protocyte_crt_dbg_report_shim;
}
#endif

namespace {

    constexpr ULONG protocyte_pool_tag = 'TyCP';

    POOL_TYPE kernel_pool_type() noexcept {
#if NTDDI_VERSION >= NTDDI_WIN8
        return NonPagedPoolNx;
#else
        return NonPagedPool;
#endif
    }

    void *kernel_allocate(void *, size_t size, size_t) noexcept {
#if NTDDI_VERSION >= NTDDI_WIN10_VB
        return ExAllocatePool2(POOL_FLAG_NON_PAGED, size, protocyte_pool_tag);
#else
        return ExAllocatePoolWithTag(kernel_pool_type(), size, protocyte_pool_tag);
#endif
    }

    void kernel_deallocate(void *, void *ptr, size_t, size_t) noexcept {
        if (ptr != nullptr) {
            ExFreePoolWithTag(ptr, protocyte_pool_tag);
        }
    }

    extern "C" void ProtocyteSmokeUnload(PDRIVER_OBJECT) {}

    NTSTATUS run_smoke_round_trip() noexcept {
        protocyte::DefaultConfig::Context ctx {
            protocyte::Allocator {nullptr, kernel_allocate, kernel_deallocate},
            protocyte::Limits {},
        };

        auto created = test::ultimate::UltimateComplexMessage<>::create(ctx);
        if (!created) {
            return STATUS_INSUFFICIENT_RESOURCES;
        }

        auto &message = *created;
        if (!message.set_f_int32(42) || !message.set_f_bool(true)) {
            return STATUS_INVALID_PARAMETER;
        }

        uint8_t encoded[16] = {};
        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        if (!message.serialize(writer)) {
            return STATUS_BUFFER_TOO_SMALL;
        }

        test::ultimate::UltimateComplexMessage<> parsed(ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        if (!parsed.merge_from(reader)) {
            return STATUS_DATA_ERROR;
        }

        if (parsed.f_int32() != 42 || !parsed.f_bool()) {
            return STATUS_DATA_ERROR;
        }

        return STATUS_SUCCESS;
    }

} // namespace

extern "C" DRIVER_INITIALIZE DriverEntry;

extern "C" NTSTATUS DriverEntry(PDRIVER_OBJECT driver_object, PUNICODE_STRING) {
    driver_object->DriverUnload = ProtocyteSmokeUnload;
    return run_smoke_round_trip();
}
