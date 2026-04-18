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
#endif

namespace {

    constexpr ULONG kProtocytePoolTag = 'TyCP';

    void *kernel_allocate(void *, size_t size, size_t) noexcept {
        return ExAllocatePool2(POOL_FLAG_NON_PAGED, size, kProtocytePoolTag);
    }

    void kernel_deallocate(void *, void *ptr, size_t, size_t) noexcept {
        if (ptr != nullptr) {
            ExFreePoolWithTag(ptr, kProtocytePoolTag);
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

        auto &message = created.value();
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
