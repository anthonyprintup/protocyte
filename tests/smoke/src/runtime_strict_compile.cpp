#include <protocyte/runtime/runtime.hpp>

static_assert(PROTOCYTE_ENABLE_STD_FORMAT == 0);
static_assert(PROTOCYTE_ENABLE_STD_STRING_VIEW == 0);
static_assert(PROTOCYTE_ENABLE_FMT_FORMAT == 0);
static_assert(PROTOCYTE_ENABLE_HOSTED_ALLOCATOR == 0);
static_assert(PROTOCYTE_ENABLE_REFLECTION == 0);

namespace {

    struct DisabledUnknownStorageLayout {
        void *context;
        PROTOCYTE_NO_UNIQUE_ADDRESS protocyte::UnknownFieldStorage<protocyte::DefaultConfig> unknown_fields;
    };

    static_assert(!protocyte::preserve_unknown_fields_v<protocyte::DefaultConfig>);
    static_assert(sizeof(DisabledUnknownStorageLayout) == sizeof(void *));
    static_assert(static_cast<protocyte::u32>(protocyte::UnknownFieldView::Type::TYPE_VARINT) == 0u);
    static_assert(static_cast<protocyte::u32>(protocyte::UnknownFieldView::Type::TYPE_FIXED32) == 1u);
    static_assert(static_cast<protocyte::u32>(protocyte::UnknownFieldView::Type::TYPE_FIXED64) == 2u);
    static_assert(static_cast<protocyte::u32>(protocyte::UnknownFieldView::Type::TYPE_LENGTH_DELIMITED) == 3u);
    static_assert(static_cast<protocyte::u32>(protocyte::UnknownFieldView::Type::TYPE_GROUP) == 4u);

    struct alignas(32) AlignedValue {
        protocyte::u8 bytes[32];
    };

    [[maybe_unused]] auto instantiate_strict_runtime_surface() noexcept -> protocyte::usize {
        protocyte::Array<AlignedValue, 3> values;
        return values.capacity();
    }

    [[maybe_unused]] auto instantiate_noncopyable_sequence_lvalue_push_back() noexcept -> protocyte::Status {
        protocyte::DefaultConfig::Context context {};
        protocyte::DefaultConfig::String value {&context};
        protocyte::DefaultConfig::Vector<protocyte::DefaultConfig::String> vector {&context};
        protocyte::Array<protocyte::DefaultConfig::String, 2u> array {&context};
        if (const auto st = vector.push_back(value); !st) {
            return st;
        }
        return array.push_back(value);
    }

} // namespace
