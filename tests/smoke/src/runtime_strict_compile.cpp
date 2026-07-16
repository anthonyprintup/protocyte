#include <protocyte/runtime/runtime.hpp>

static_assert(PROTOCYTE_ENABLE_STD_FORMAT == 0);
static_assert(PROTOCYTE_ENABLE_STD_STRING_VIEW == 0);
static_assert(PROTOCYTE_ENABLE_FMT_FORMAT == 0);
static_assert(PROTOCYTE_ENABLE_HOSTED_ALLOCATOR == 0);
static_assert(PROTOCYTE_ENABLE_REFLECTION == 0);

namespace {

    struct alignas(32) AlignedValue {
        protocyte::u8 bytes[32];
    };

    [[maybe_unused]] auto instantiate_strict_runtime_surface() noexcept -> protocyte::usize {
        protocyte::Array<AlignedValue, 3> values;
        return values.capacity();
    }

} // namespace
