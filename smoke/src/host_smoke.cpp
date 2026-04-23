#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <string>
#include <string_view>
#include <type_traits>

#include <catch2/catch_test_macros.hpp>

#include "compat.protocyte.hpp"
#include "compat_cases.hpp"
#include "cross_package.protocyte.hpp"
#include "example.protocyte.hpp"
#include "protocyte/runtime/runtime.hpp"

namespace {

    struct alignas(64) HostedOverAligned final {
        uint8_t bytes[64];
    };

    struct CustomConfig {
        struct Context {
            protocyte::Allocator allocator;
            protocyte::Limits limits;
            protocyte::usize recursion_depth {};
        };

        template<class T> using Vector = protocyte::Vector<T, CustomConfig>;
        template<class K, class V> using Map = protocyte::HashMap<K, V, CustomConfig>;
        template<class T> using Box = protocyte::Box<T, CustomConfig>;
        template<class T> using Optional = protocyte::Optional<T>;
        using Bytes = protocyte::Bytes<CustomConfig>;
        using String = protocyte::String<CustomConfig>;

        static void *allocate(Context &ctx, const protocyte::usize size, const protocyte::usize alignment) noexcept {
            if (!size || ctx.allocator.allocate == nullptr) {
                return nullptr;
            }
            return ctx.allocator.allocate(ctx.allocator.state, size, alignment);
        }

        static void deallocate(Context &ctx, void *ptr, const protocyte::usize size,
                               const protocyte::usize alignment) noexcept {
            if (ptr != nullptr && ctx.allocator.deallocate != nullptr) {
                ctx.allocator.deallocate(ctx.allocator.state, ptr, size, alignment);
            }
        }

        template<class T> static protocyte::u64 hash(const T &value) noexcept {
            return protocyte::fnv1a(
                protocyte::ByteView {.data = reinterpret_cast<const protocyte::u8 *>(&value), .size = sizeof(T)});
        }

        template<class T> static bool equal(const T &lhs, const T &rhs) noexcept { return lhs == rhs; }

        static protocyte::u64 hash(const Bytes &value) noexcept { return protocyte::fnv1a(value.view()); }
        static protocyte::u64 hash(const String &value) noexcept { return protocyte::fnv1a(value.view()); }
        static bool equal(const Bytes &lhs, const Bytes &rhs) noexcept {
            return protocyte::bytes_equal(lhs.view(), rhs.view());
        }
        static bool equal(const String &lhs, const String &rhs) noexcept {
            return protocyte::bytes_equal(lhs.view(), rhs.view());
        }
    };

    using Config = protocyte::DefaultConfig;
    using Message = test::ultimate::UltimateComplexMessage<>;
    using Nested1 = test::ultimate::UltimateComplexMessage_NestedLevel1<>;
    using Nested2 = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<>;
    using RepeatedBytesHolder = test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<>;
    using BoundedRepeatedBytesHolder = test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<>;
    using FixedRepeatedBytesHolder = test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<>;
    using Deep = test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<>;
    using Cross = test::ultimate::CrossMessageConstants<>;
    using CrossNested = test::ultimate::CrossMessageConstants_Nested<>;
    using CrossPackage = test::crosspkg::CrossPackageConstants<>;
    using CrossPackageNested = test::crosspkg::CrossPackageConstants_Nested<>;
    using Color = test::ultimate::UltimateComplexMessage_Color;
    using InnerMode = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;
    using CompatMessage = protocyte_smoke::test::compat::EncodingMatrix<>;
    using CompatNested = protocyte_smoke::test::compat::EncodingMatrix_Inner<>;
    using CompatMode = protocyte_smoke::test::compat::EncodingMatrix_Mode;
    using CustomMessage = test::ultimate::UltimateComplexMessage<CustomConfig>;
    using CustomNested1 = test::ultimate::UltimateComplexMessage_NestedLevel1<CustomConfig>;
    using CustomNested2 = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<CustomConfig>;

    static_assert(test::ultimate::BASE_COUNT == 5);
    static_assert(Message::SHIFTED_COUNT == 5000000000ll);
    static_assert(Message::MASK_BITS == 1234567890123456789ull);
    static_assert(Message::FLOAT_SCALE == 1.25f);
    static_assert(Message::DOUBLE_SCALE == 3.75);
    static_assert(Message::FLAG_LITERAL);
    static_assert(Message::HEX_LITERAL == 32u);
    static_assert(Message::HEX_SUM == 24u);
    static_assert(Message::INTEGER_ARRAY_CAP == 8u);
    static_assert(test::ultimate::BYTE_ARRAY_CAP == 4u);
    static_assert(Message::FIXED_INTEGER_ARRAY_CAP == 3u);
    static_assert(Message::FLOATISH_BOUND == 2u);
    static_assert(Message::GT_CHECK);
    static_assert(Message::LE_CHECK);
    static_assert(Message::EQ_CHECK);
    static_assert(Message::NE_CHECK);
    static_assert(Message::HAS_PREFIX);
    static_assert(Message::MOD_CHECK == 1);
    static_assert(Message::OR_CHECK);
    static_assert(test::ultimate::PREFIX == std::string_view {"proto", 5u});
    static_assert(Message::LABEL == std::string_view {"proto-demo", 10u});
    static_assert(Message::UNICODE_LABEL == std::string_view {"\xc4"
                                                              "\x80"
                                                              "\xc3"
                                                              "\xa9",
                                                              4u});
    static_assert(Message::INTEGER_ARRAY_CAP * 4u == 32u);
    static_assert(Cross::ROOT_MIRROR == 10u);
    static_assert(Cross::LABEL_COPY == std::string_view {"proto-cross", 11u});
    static_assert(Cross::READY);
    static_assert(CrossNested::EXTERNAL_CAP == 8u);
    static_assert(test::crosspkg::FOREIGN_BASE == 7u);
    static_assert(test::crosspkg::FOREIGN_LABEL == std::string_view {"proto-xpkg", 10u});
    static_assert(CrossPackage::REMOTE_COUNT == 16u);
    static_assert(CrossPackage::REMOTE_LABEL == std::string_view {"proto-demo-external", 19u});
    static_assert(CrossPackage::REMOTE_READY);
    static_assert(CrossPackage::NESTED_COUNT == 9u);
    static_assert(CrossPackageNested::MIRRORED_COUNT == 15u);

    constexpr uint8_t string_bytes[] = {'s', 'm', 'o', 'k', 'e'};
    constexpr uint8_t bytes_data[] = {0x00u, 0x01u, 0x7fu, 0x80u, 0xffu};
    constexpr uint8_t nested_name[] = {'n', 'e', 's', 't', 'e', 'd'};
    constexpr uint8_t nested_description[] = {'i', 'n', 'n', 'e', 'r'};
    constexpr uint8_t oneof_string[] = {'o', 'n', 'e', 'o', 'f', '-', 's', 't', 'r'};
    constexpr uint8_t oneof_bytes[] = {0xdeu, 0xadu, 0xbeu, 0xefu};
    constexpr uint8_t crazy_plain_bytes[] = {0x60u, 0x61u, 0x62u, 0x63u, 0x64u};
    constexpr uint8_t crazy_bounded_bytes[] = {0x70u, 0x71u, 0x72u, 0x73u};
    constexpr uint8_t crazy_fixed_bytes[] = {0x80u, 0x81u, 0x82u, 0x83u};
    constexpr uint8_t map_key[] = {'m', 'a', 'p', '-', 'k', 'e', 'y'};
    constexpr uint8_t map_value[] = {'m', 'a', 'p', '-', 'v', 'a', 'l'};
    constexpr uint8_t bool_bytes[] = {'b', 'o', 'o', 'l'};
    constexpr uint8_t very_nested_key[] = {'v', 'e', 'r', 'y'};
    constexpr uint8_t recursive_string[] = {'r', 'e', 'c'};
    constexpr uint8_t optional_string[] = {'o', 'p', 't'};
    constexpr uint8_t extreme_value[] = {'e', 'x', 't', 'r', 'e', 'm', 'e'};
    constexpr uint8_t deep_text[] = {'d', 'e', 'e', 'p'};
    constexpr uint8_t weird_value[] = {'w', 'e', 'i', 'r', 'd'};
    constexpr uint8_t byte_array[] = {0xa1u, 0xb2u, 0xc3u, 0xd4u};
    constexpr uint8_t float_expr_array[] = {0x91u, 0x92u};
    constexpr uint8_t external_bytes[] = {0x11u, 0x22u, 0x33u, 0x44u, 0x55u, 0x66u};
    constexpr uint8_t nested_bytes[] = {0x80u, 0x81u, 0x82u, 0x83u, 0x84u, 0x85u, 0x86u, 0x87u};
    constexpr uint8_t cross_package_bytes[] = {0x91u, 0x92u, 0x93u, 0x94u, 0x95u, 0x96u, 0x97u, 0x98u, 0x99u};
    constexpr uint8_t cross_package_nested_bytes[] = {
        0xa0u, 0xa1u, 0xa2u, 0xa3u, 0xa4u, 0xa5u, 0xa6u, 0xa7u, 0xa8u, 0xa9u, 0xaau, 0xabu, 0xacu, 0xadu, 0xaeu,
    };
    constexpr uint8_t large_byte_array[] = {0x01u, 0x02u, 0x03u, 0x04u, 0x05u};
    constexpr uint8_t alternate_byte_array[] = {0x55u, 0x66u, 0x77u, 0x88u};
    constexpr uint8_t repeated_bytes_0[] = {0x11u};
    constexpr uint8_t repeated_bytes_1[] = {0x22u, 0x23u};
    constexpr uint8_t repeated_bytes_2[] = {0x34u, 0x35u, 0x36u, 0x37u};
    constexpr uint8_t repeated_bytes_3[] = {0x48u, 0x49u, 0x4au};
    constexpr uint8_t sha256_bytes[] = {
        0x10u, 0x21u, 0x32u, 0x43u, 0x54u, 0x65u, 0x76u, 0x87u, 0x98u, 0xa9u, 0xbau, 0xcbu, 0xdcu, 0xedu, 0xfeu, 0x0fu,
        0x1eu, 0x2du, 0x3cu, 0x4bu, 0x5au, 0x69u, 0x78u, 0x87u, 0x96u, 0xa5u, 0xb4u, 0xc3u, 0xd2u, 0xe1u, 0xf0u, 0x0fu,
    };
    constexpr int32_t integer_array_values[] = {101, 102, 103, 104, 105, 106, 107, 108};
    constexpr int32_t mirrored_values[] = {501, 502, 503, 504, 505, 506, 507, 508, 509, 510};
    constexpr int32_t cross_package_values[] = {601, 602, 603, 604, 605, 606, 607, 608, 609};
    constexpr uint32_t fixed_integer_array_values[] = {901u, 902u, 903u};
    constexpr uint8_t short_sha256[31] = {};

    static_assert(sizeof(byte_array) == test::ultimate::BYTE_ARRAY_CAP);
    static_assert(sizeof(float_expr_array) == Message::FLOATISH_BOUND);
    static_assert(sizeof(external_bytes) == test::ultimate::BYTE_ARRAY_CAP + 2u);
    static_assert(sizeof(nested_bytes) == CrossNested::EXTERNAL_CAP);
    static_assert(sizeof(cross_package_bytes) == Message::INTEGER_ARRAY_CAP + 1u);
    static_assert(sizeof(cross_package_nested_bytes) == CrossPackageNested::MIRRORED_COUNT);
    static_assert(sizeof(integer_array_values) / sizeof(integer_array_values[0]) == Message::INTEGER_ARRAY_CAP);
    static_assert(sizeof(mirrored_values) / sizeof(mirrored_values[0]) == Cross::ROOT_MIRROR);
    static_assert(sizeof(cross_package_values) / sizeof(cross_package_values[0]) == CrossPackage::NESTED_COUNT);
    static_assert(sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]) ==
                  Message::FIXED_INTEGER_ARRAY_CAP);

    void *smoke_allocate(void *, size_t size, size_t) noexcept { return malloc(size); }

    void smoke_deallocate(void *, void *ptr, size_t, size_t) noexcept { free(ptr); }

    Config::Context make_context() noexcept {
        return Config::Context {
            protocyte::Allocator {nullptr, smoke_allocate, smoke_deallocate},
            protocyte::Limits {},
        };
    }

    CustomConfig::Context make_custom_context() noexcept {
        return CustomConfig::Context {
            protocyte::Allocator {nullptr, smoke_allocate, smoke_deallocate},
            protocyte::Limits {},
        };
    }

    bool view_equal(protocyte::ByteView lhs, protocyte::ByteView rhs) noexcept {
        return protocyte::bytes_equal(lhs, rhs);
    }

    template<size_t N> protocyte::ByteView view_of(const uint8_t (&data)[N]) noexcept {
        return protocyte::ByteView {data, N};
    }

    struct ResultTransformQualifier {
        int operator()(int &value) const noexcept { return value + 1; }
        int operator()(const int &value) const noexcept { return value + 2; }
        int operator()(int &&value) const noexcept { return value + 3; }
        int operator()(const int &&value) const noexcept { return value + 4; }
    };

    struct ResultAndThenQualifier {
        protocyte::Result<int> operator()(int &value) const noexcept { return value + 10; }
        protocyte::Result<int> operator()(const int &value) const noexcept { return value + 20; }
        protocyte::Result<int> operator()(int &&value) const noexcept { return value + 30; }
        protocyte::Result<int> operator()(const int &&value) const noexcept { return value + 40; }
    };

    struct ResultErrorQualifier {
        protocyte::Result<int, protocyte::u32> operator()(protocyte::Error &error) const noexcept {
            return protocyte::unexpected(static_cast<protocyte::u32>(100u + error.field_number));
        }
        protocyte::Result<int, protocyte::u32> operator()(const protocyte::Error &error) const noexcept {
            return protocyte::unexpected(static_cast<protocyte::u32>(200u + error.field_number));
        }
        protocyte::Result<int, protocyte::u32> operator()(protocyte::Error &&error) const noexcept {
            return protocyte::unexpected(static_cast<protocyte::u32>(300u + error.field_number));
        }
        protocyte::Result<int, protocyte::u32> operator()(const protocyte::Error &&error) const noexcept {
            return protocyte::unexpected(static_cast<protocyte::u32>(400u + error.field_number));
        }
    };

    struct ResultTransformErrorQualifier {
        protocyte::u32 operator()(protocyte::Error &error) const noexcept {
            return static_cast<protocyte::u32>(500u + error.field_number);
        }
        protocyte::u32 operator()(const protocyte::Error &error) const noexcept {
            return static_cast<protocyte::u32>(600u + error.field_number);
        }
        protocyte::u32 operator()(protocyte::Error &&error) const noexcept {
            return static_cast<protocyte::u32>(700u + error.field_number);
        }
        protocyte::u32 operator()(const protocyte::Error &&error) const noexcept {
            return static_cast<protocyte::u32>(800u + error.field_number);
        }
    };

    struct OptionalTransformQualifier {
        int operator()(int &value) const noexcept { return value + 1; }
        int operator()(const int &value) const noexcept { return value + 2; }
        int operator()(int &&value) const noexcept { return value + 3; }
        int operator()(const int &&value) const noexcept { return value + 4; }
    };

    struct OptionalAndThenQualifier {
        protocyte::Optional<int> operator()(int &value) const noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(value + 10);
            return out;
        }
        protocyte::Optional<int> operator()(const int &value) const noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(value + 20);
            return out;
        }
        protocyte::Optional<int> operator()(int &&value) const noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(value + 30);
            return out;
        }
        protocyte::Optional<int> operator()(const int &&value) const noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(value + 40);
            return out;
        }
    };

    struct MemberInvokeProbe {
        int value {};

        int doubled() const noexcept { return value * 2; }

        protocyte::Result<int> next() const noexcept { return value + 3; }

        protocyte::Optional<int> maybe() const noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(value + 4);
            return out;
        }
    };

    struct MoveOnlyMember {
        int value {};

        explicit MoveOnlyMember(const int current) noexcept: value {current} {}
        MoveOnlyMember(const MoveOnlyMember &) = delete;
        MoveOnlyMember &operator=(const MoveOnlyMember &) = delete;
        MoveOnlyMember(MoveOnlyMember &&) noexcept = default;
        MoveOnlyMember &operator=(MoveOnlyMember &&) noexcept = default;
    };

    struct MoveOnlyMemberProbe {
        MoveOnlyMember child;

        explicit MoveOnlyMemberProbe(const int current) noexcept: child {current} {}
    };

    struct ErrorMemberProbe {
        protocyte::u32 code {};
        protocyte::usize offset {};
    };

    struct TrackedPayload {
        inline static int copies = 0;
        inline static int moves = 0;

        int value {};

        constexpr TrackedPayload() noexcept = default;
        constexpr explicit TrackedPayload(const int current) noexcept: value {current} {}

        TrackedPayload(const TrackedPayload &other) noexcept: value {other.value} { ++copies; }

        TrackedPayload(TrackedPayload &&other) noexcept: value {other.value} {
            ++moves;
            other.value = -1;
        }

        TrackedPayload &operator=(const TrackedPayload &other) noexcept {
            value = other.value;
            ++copies;
            return *this;
        }

        TrackedPayload &operator=(TrackedPayload &&other) noexcept {
            value = other.value;
            ++moves;
            other.value = -1;
            return *this;
        }

        static void reset() noexcept {
            copies = 0;
            moves = 0;
        }
    };

    template<class T>
    concept CanCallUnexpected = requires(T &&value) { protocyte::unexpected(protocyte::forward<T>(value)); };

    template<class T>
    concept CanTransformMoveOnlyMember =
        requires(T &&value) { protocyte::forward<T>(value).transform(&MoveOnlyMemberProbe::child); };

    std::string hex_of(std::string_view bytes) {
        static constexpr char hex_digits[] = "0123456789abcdef";
        std::string out;
        out.reserve(bytes.size() * 2u);
        for (const unsigned char value : bytes) {
            out.push_back(hex_digits[value >> 4u]);
            out.push_back(hex_digits[value & 0x0fu]);
        }
        return out;
    }

    template<class TStatusLike> void require_success(const TStatusLike &status_like) {
        if (!status_like) {
            const auto error = status_like.error();
            CAPTURE(static_cast<uint32_t>(error.code), error.offset, error.field_number);
        }
        REQUIRE(status_like);
    }

    template<class TStatusLike> void require_failure(const TStatusLike &status_like, protocyte::ErrorCode expected) {
        const auto error = status_like.error();
        CAPTURE(static_cast<uint32_t>(error.code), error.offset, error.field_number, static_cast<uint32_t>(expected));
        REQUIRE_FALSE(status_like);
        REQUIRE(error.code == expected);
    }

    void assign_string(Config::String &out, protocyte::ByteView view) { require_success(out.assign(view)); }

    void assign_bytes(Config::Bytes &out, protocyte::ByteView view) { require_success(out.assign(view)); }

    template<class Container> void append_bytes(Container &out, Config::Context &ctx, protocyte::ByteView view) {
        Config::Bytes value(&ctx);
        assign_bytes(value, view);
        require_success(out.push_back(protocyte::move(value)));
    }

    template<class Container, class T, size_t N>
    void check_scalar_sequence(const Container &values, const T (&expected)[N]) {
        REQUIRE(values.size() == N);
        size_t index {};
        for (const auto &value : values) {
            REQUIRE(index < N);
            CHECK(value == expected[index]);
            ++index;
        }
        CHECK(index == N);
    }

    template<class Container, class T, size_t N>
    void check_scalar_reverse_sequence(const Container &values, const T (&expected)[N]) {
        size_t index {N};
        for (auto it = values.rbegin(); it != values.rend(); ++it) {
            REQUIRE(index != 0u);
            --index;
            CHECK(*it == expected[index]);
        }
        CHECK(index == 0u);
    }

    template<class Container, size_t N>
    void check_byte_entry_sequence(const Container &values, const protocyte::ByteView (&expected)[N]) {
        REQUIRE(values.size() == N);
        size_t index {};
        for (const auto &value : values) {
            REQUIRE(index < N);
            CHECK(view_equal(value.view(), expected[index]));
            ++index;
        }
        CHECK(index == N);
    }

    std::string serialize_compat(const CompatMessage &message) {
        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        std::string out(*encoded_size, '\0');
        protocyte::SliceWriter writer(reinterpret_cast<uint8_t *>(out.data()), out.size());
        require_success(message.serialize(writer));
        REQUIRE(writer.position() == out.size());
        return out;
    }

    template<size_t N> void require_same_compat_bytes(const char *label, const CompatMessage &protocyte_message,
                                                      const std::array<unsigned char, N> &expected_bytes) {
        const auto protocyte_bytes = serialize_compat(protocyte_message);
        const auto expected = std::string(reinterpret_cast<const char *>(expected_bytes.data()), expected_bytes.size());

        CAPTURE(label);
        CAPTURE(hex_of(protocyte_bytes));
        CAPTURE(hex_of(expected));
        REQUIRE(protocyte_bytes == expected);
    }

    void populate_compat_nested(CompatNested &nested, const int32_t value, const protocyte::ByteView label) {
        require_success(nested.set_value(value));
        require_success(nested.set_label(label));
    }

    void populate_required_fixed_array(Message &message, Config::Context &ctx) {
        for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
            require_success(message.mutable_fixed_integer_array().push_back(fixed_integer_array_values[i]));
        }
        append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_0));
        append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
        append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
    }

    template<class Container> void check_three_byte_entries(const Container &values, protocyte::ByteView first,
                                                            protocyte::ByteView second, protocyte::ByteView third) {
        const protocyte::ByteView expected[] = {first, second, third};
        check_byte_entry_sequence(values, expected);
    }

    void populate_repeated_bytes_holder(RepeatedBytesHolder &value, Config::Context &ctx) {
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_0));
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_1));
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2));
    }

    void check_repeated_bytes_holder(const RepeatedBytesHolder &value) {
        check_three_byte_entries(value.values(), view_of(repeated_bytes_0), view_of(repeated_bytes_1),
                                 view_of(repeated_bytes_2));
    }

    void populate_bounded_repeated_bytes_holder(BoundedRepeatedBytesHolder &value, Config::Context &ctx) {
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_1));
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2));
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_3));
    }

    void check_bounded_repeated_bytes_holder(const BoundedRepeatedBytesHolder &value) {
        check_three_byte_entries(value.values(), view_of(repeated_bytes_1), view_of(repeated_bytes_2),
                                 view_of(repeated_bytes_3));
    }

    void populate_fixed_repeated_bytes_holder(FixedRepeatedBytesHolder &value, Config::Context &ctx) {
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_0));
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2));
        append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_3));
    }

    void check_fixed_repeated_bytes_holder(const FixedRepeatedBytesHolder &value) {
        check_three_byte_entries(value.values(), view_of(repeated_bytes_0), view_of(repeated_bytes_2),
                                 view_of(repeated_bytes_3));
    }

    bool nested2_matches(const Nested2 &value, protocyte::ByteView description, float first, float second,
                         InnerMode mode) noexcept {
        const float expected[] = {first, second};
        size_t index {};
        if (!view_equal(value.description(), description) || value.values().size() != 2u || value.mode() != mode) {
            return false;
        }
        for (const auto current : value.values()) {
            if (index >= 2u || current != expected[index]) {
                return false;
            }
            ++index;
        }
        return index == 2u;
    }

    void check_nested2(const Nested2 &value, protocyte::ByteView description, float first, float second,
                       InnerMode mode) {
        const float expected[] = {first, second};
        CHECK(view_equal(value.description(), description));
        check_scalar_sequence(value.values(), expected);
        CHECK(value.mode() == mode);
    }

    void populate_nested2(Nested2 &value, protocyte::ByteView description, float first, float second, InnerMode mode) {
        require_success(value.set_description(description));
        require_success(value.mutable_values().push_back(first));
        require_success(value.mutable_values().push_back(second));
        require_success(value.set_mode(mode));
        check_nested2(value, description, first, second, mode);
    }

    bool nested1_matches(const Nested1 &value, protocyte::ByteView name, int32_t id) noexcept {
        return view_equal(value.name(), name) && value.id() == id && value.has_inner() &&
               nested2_matches(*value.inner(), view_of(nested_description), 1.5f, 2.5f, InnerMode::B);
    }

    void check_nested1(const Nested1 &value, protocyte::ByteView name, int32_t id) {
        CHECK(view_equal(value.name(), name));
        CHECK(value.id() == id);
        REQUIRE(value.has_inner());
        check_nested2(*value.inner(), view_of(nested_description), 1.5f, 2.5f, InnerMode::B);
    }

    void populate_nested1(Nested1 &value, protocyte::ByteView name, int32_t id) {
        require_success(value.set_name(name));
        require_success(value.set_id(id));
        auto inner = value.ensure_inner();
        require_success(inner);
        populate_nested2(**inner, view_of(nested_description), 1.5f, 2.5f, InnerMode::B);
        check_nested1(value, name, id);
    }

    void insert_map_str_int32(Message &message, Config::Context &ctx) {
        Config::String key(&ctx);
        assign_string(key, view_of(map_key));
        require_success(message.mutable_map_str_int32().insert_or_assign(protocyte::move(key), 301));
    }

    void insert_map_int32_str(Message &message, Config::Context &ctx) {
        Config::String value(&ctx);
        assign_string(value, view_of(map_value));
        require_success(message.mutable_map_int32_str().insert_or_assign(302, protocyte::move(value)));
    }

    void insert_map_bool_bytes(Message &message, Config::Context &ctx) {
        Config::Bytes value(&ctx);
        assign_bytes(value, view_of(bool_bytes));
        require_success(message.mutable_map_bool_bytes().insert_or_assign(true, protocyte::move(value)));
    }

    void insert_map_uint64_msg(Message &message, Config::Context &ctx) {
        Nested1 value(ctx);
        populate_nested1(value, view_of(nested_name), 330);
        require_success(message.mutable_map_uint64_msg().insert_or_assign(3300u, protocyte::move(value)));
    }

    void insert_very_nested_map(Message &message, Config::Context &ctx) {
        Config::String key(&ctx);
        assign_string(key, view_of(very_nested_key));
        Nested2 value(ctx);
        populate_nested2(value, view_of(nested_description), 3.5f, 4.5f, InnerMode::C);
        require_success(
            message.mutable_very_nested_map().insert_or_assign(protocyte::move(key), protocyte::move(value)));
    }

    void populate_deep(Deep &value, Config::Context &ctx) {
        require_success(value.set_extreme(view_of(extreme_value)));
        Config::String weird(&ctx);
        assign_string(weird, view_of(weird_value));
        require_success(value.mutable_weird_map().insert_or_assign(7, protocyte::move(weird)));
        require_success(value.set_text(view_of(deep_text)));
    }

    void populate_message(Message &message, Config::Context &ctx) {
        require_success(message.set_f_double(123.5));
        require_success(message.set_f_float(12.25f));
        require_success(message.set_f_int32(42));
        require_success(message.set_f_int64(42000000000ll));
        require_success(message.set_f_uint32(99u));
        require_success(message.set_f_uint64(99000000000ull));
        require_success(message.set_f_sint32(-17));
        require_success(message.set_f_sint64(-17000000000ll));
        require_success(message.set_f_fixed32(0x11223344u));
        require_success(message.set_f_fixed64(0x1122334455667788ull));
        require_success(message.set_f_sfixed32(-1234567));
        require_success(message.set_f_sfixed64(-1234567890123ll));
        require_success(message.set_f_bool(true));
        require_success(message.set_f_string(view_of(string_bytes)));
        require_success(message.set_f_bytes(view_of(bytes_data)));
        require_success(message.mutable_r_int32_unpacked().push_back(21));
        require_success(message.mutable_r_int32_unpacked().push_back(22));
        require_success(message.mutable_r_int32_packed().push_back(23));
        require_success(message.mutable_r_int32_packed().push_back(24));
        require_success(message.mutable_r_double().push_back(23.5));
        require_success(message.mutable_r_double().push_back(24.5));
        require_success(message.set_color(Color::GREEN));

        auto nested = message.ensure_nested1();
        require_success(nested);
        populate_nested1(**nested, view_of(nested_name), 25);

        require_success(message.set_oneof_bytes(view_of(oneof_bytes)));
        insert_map_str_int32(message, ctx);
        insert_map_int32_str(message, ctx);
        insert_map_bool_bytes(message, ctx);
        insert_map_uint64_msg(message, ctx);
        insert_very_nested_map(message, ctx);

        auto recursive = message.ensure_recursive_self();
        require_success(recursive);
        require_success((*recursive)->set_f_string(view_of(recursive_string)));
        require_success((*recursive)->set_f_int32(350));
        populate_required_fixed_array(**recursive, ctx);

        auto nested_item = message.mutable_lots_of_nested().emplace_back(ctx);
        require_success(nested_item);
        populate_nested2(**nested_item, view_of(nested_description), 36.5f, 37.5f, InnerMode::A);

        require_success(message.mutable_colors().push_back(static_cast<int32_t>(Color::RED)));
        require_success(message.mutable_colors().push_back(static_cast<int32_t>(Color::BLUE)));
        require_success(message.set_opt_int32(38));
        require_success(message.set_opt_string(view_of(optional_string)));
        require_success(message.set_sha256(view_of(sha256_bytes)));
        require_success(message.set_byte_array(view_of(byte_array)));
        require_success(message.set_float_expr_array(view_of(float_expr_array)));
        append_bytes(message.mutable_repeated_byte_array(), ctx, view_of(repeated_bytes_0));
        append_bytes(message.mutable_repeated_byte_array(), ctx, view_of(repeated_bytes_1));
        append_bytes(message.mutable_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
        append_bytes(message.mutable_bounded_repeated_byte_array(), ctx, view_of(repeated_bytes_1));
        append_bytes(message.mutable_bounded_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
        append_bytes(message.mutable_bounded_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
        append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_0));
        append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
        append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
        auto crazy_fixed_repeated = message.ensure_crazy_fixed_repeated_bytes();
        require_success(crazy_fixed_repeated);
        populate_fixed_repeated_bytes_holder(**crazy_fixed_repeated, ctx);

        for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
            require_success(message.mutable_integer_array().push_back(integer_array_values[i]));
        }
        for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
            require_success(message.mutable_fixed_integer_array().push_back(fixed_integer_array_values[i]));
        }

        auto deep = message.ensure_extreme_nesting();
        require_success(deep);
        populate_deep(**deep, ctx);
    }

    void check_maps(const Message &message) {
        bool saw_str_int32 = false;
        for (const auto entry : message.map_str_int32()) {
            if (view_equal(entry.key.view(), view_of(map_key)) && entry.value == 301) {
                saw_str_int32 = true;
            }
        }
        CHECK(saw_str_int32);
        CHECK(message.map_str_int32().size() == 1u);

        bool saw_int32_str = false;
        for (const auto entry : message.map_int32_str()) {
            if (entry.key == 302 && view_equal(entry.value.view(), view_of(map_value))) {
                saw_int32_str = true;
            }
        }
        CHECK(saw_int32_str);
        CHECK(message.map_int32_str().size() == 1u);

        bool saw_bool_bytes = false;
        for (const auto entry : message.map_bool_bytes()) {
            if (entry.key && view_equal(entry.value.view(), view_of(bool_bytes))) {
                saw_bool_bytes = true;
            }
        }
        CHECK(saw_bool_bytes);
        CHECK(message.map_bool_bytes().size() == 1u);

        bool saw_uint64_msg = false;
        for (const auto entry : message.map_uint64_msg()) {
            if (entry.key == 3300u && nested1_matches(entry.value, view_of(nested_name), 330)) {
                saw_uint64_msg = true;
            }
        }
        CHECK(saw_uint64_msg);
        CHECK(message.map_uint64_msg().size() == 1u);

        bool saw_very_nested = false;
        for (const auto entry : message.very_nested_map()) {
            if (view_equal(entry.key.view(), view_of(very_nested_key)) &&
                nested2_matches(entry.value, view_of(nested_description), 3.5f, 4.5f, InnerMode::C)) {
                saw_very_nested = true;
            }
        }
        CHECK(saw_very_nested);
        CHECK(message.very_nested_map().size() == 1u);
    }

    void check_message(const Message &parsed) {
        CHECK(parsed.f_double() == 123.5);
        CHECK(parsed.f_float() == 12.25f);
        CHECK(parsed.f_int32() == 42);
        CHECK(parsed.f_int64() == 42000000000ll);
        CHECK(parsed.f_uint32() == 99u);
        CHECK(parsed.f_uint64() == 99000000000ull);
        CHECK(parsed.f_sint32() == -17);
        CHECK(parsed.f_sint64() == -17000000000ll);
        CHECK(parsed.f_fixed32() == 0x11223344u);
        CHECK(parsed.f_fixed64() == 0x1122334455667788ull);
        CHECK(parsed.f_sfixed32() == -1234567);
        CHECK(parsed.f_sfixed64() == -1234567890123ll);
        CHECK(parsed.f_bool());
        CHECK(view_equal(parsed.f_string(), view_of(string_bytes)));
        CHECK(view_equal(parsed.f_bytes(), view_of(bytes_data)));

        const protocyte::i32 expected_unpacked[] = {21, 22};
        const protocyte::i32 expected_packed[] = {23, 24};
        const protocyte::f64 expected_doubles[] = {23.5, 24.5};
        check_scalar_sequence(parsed.r_int32_unpacked(), expected_unpacked);
        check_scalar_sequence(parsed.r_int32_packed(), expected_packed);
        check_scalar_sequence(parsed.r_double(), expected_doubles);

        CHECK(parsed.color() == Color::GREEN);

        REQUIRE(parsed.has_nested1());
        check_nested1(*parsed.nested1(), view_of(nested_name), 25);

        REQUIRE(parsed.has_oneof_bytes());
        CHECK(parsed.special_oneof_case() == Message::Special_oneofCase::oneof_bytes);
        CHECK(view_equal(parsed.oneof_bytes(), view_of(oneof_bytes)));
        REQUIRE(parsed.has_crazy_fixed_repeated_bytes());
        CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes);
        check_fixed_repeated_bytes_holder(*parsed.crazy_fixed_repeated_bytes());

        check_maps(parsed);

        REQUIRE(parsed.has_recursive_self());
        CHECK(parsed.recursive_self()->f_int32() == 350);
        CHECK(view_equal(parsed.recursive_self()->f_string(), view_of(recursive_string)));

        const auto &nested_items = parsed.lots_of_nested();
        REQUIRE(nested_items.size() == 1u);
        check_nested2(nested_items[0], view_of(nested_description), 36.5f, 37.5f, InnerMode::A);

        const protocyte::i32 expected_colors[] = {static_cast<int32_t>(Color::RED), static_cast<int32_t>(Color::BLUE)};
        check_scalar_sequence(parsed.colors(), expected_colors);

        REQUIRE(parsed.has_opt_int32());
        CHECK(parsed.opt_int32() == 38);
        REQUIRE(parsed.has_opt_string());
        CHECK(view_equal(parsed.opt_string(), view_of(optional_string)));

        CHECK(view_equal(parsed.sha256(), view_of(sha256_bytes)));
        CHECK(view_equal(parsed.byte_array(), view_of(byte_array)));
        CHECK(parsed.byte_array_size() == test::ultimate::BYTE_ARRAY_CAP);
        CHECK(view_equal(parsed.float_expr_array(), view_of(float_expr_array)));
        CHECK(parsed.float_expr_array_size() == Message::FLOATISH_BOUND);
        check_three_byte_entries(parsed.repeated_byte_array(), view_of(repeated_bytes_0), view_of(repeated_bytes_1),
                                 view_of(repeated_bytes_2));
        check_three_byte_entries(parsed.bounded_repeated_byte_array(), view_of(repeated_bytes_1),
                                 view_of(repeated_bytes_2), view_of(repeated_bytes_3));
        check_three_byte_entries(parsed.fixed_repeated_byte_array(), view_of(repeated_bytes_0),
                                 view_of(repeated_bytes_2), view_of(repeated_bytes_3));

        check_scalar_sequence(parsed.integer_array(), integer_array_values);
        check_scalar_reverse_sequence(parsed.integer_array(), integer_array_values);
        check_scalar_sequence(parsed.fixed_integer_array(), fixed_integer_array_values);

        REQUIRE(parsed.has_extreme_nesting());
        const Deep &deep = *parsed.extreme_nesting();
        CHECK(view_equal(deep.extreme(), view_of(extreme_value)));
        REQUIRE(deep.has_text());
        CHECK(deep.deep_oneof_case() == Deep::Deep_oneofCase::text);
        CHECK(view_equal(deep.text(), view_of(deep_text)));

        bool saw_weird = false;
        for (const auto entry : deep.weird_map()) {
            if (entry.key == 7 && view_equal(entry.value.view(), view_of(weird_value))) {
                saw_weird = true;
            }
        }
        CHECK(saw_weird);
        CHECK(deep.weird_map().size() == 1u);
    }

    void round_trip_and_check(Message &message, Config::Context &ctx) {
        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        uint8_t encoded[4096] = {};
        REQUIRE(*encoded_size <= sizeof(encoded));

        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(message.serialize(writer));
        REQUIRE(writer.position() == *encoded_size);

        Message parsed(ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_success(parsed.merge_from(reader));
        REQUIRE(reader.eof());
        check_message(parsed);

        Message copied(ctx);
        require_success(copied.copy_from(parsed));
        check_message(copied);

        auto cloned = parsed.clone();
        require_success(cloned);
        check_message(*cloned);

        Message moved(protocyte::move(parsed));
        check_message(moved);
    }

    void check_oneof_alternatives(Config::Context &ctx) {
        SECTION("string alternative round trips") {
            Message message(ctx);
            require_success(message.set_oneof_string(view_of(oneof_string)));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_string());
            CHECK(view_equal(parsed.oneof_string(), view_of(oneof_string)));
        }

        SECTION("int32 alternative round trips") {
            Message message(ctx);
            require_success(message.set_oneof_int32(2700));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_int32());
            CHECK(parsed.oneof_int32() == 2700);
        }

        SECTION("message alternative round trips") {
            Message message(ctx);
            auto oneof_msg = message.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(**oneof_msg, view_of(nested_name), 2800);
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_msg());
            check_nested1(*parsed.oneof_msg(), view_of(nested_name), 2800);
        }

        SECTION("bytes alternative round trips") {
            Message message(ctx);
            require_success(message.set_oneof_bytes(view_of(oneof_bytes)));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_bytes());
            CHECK(view_equal(parsed.oneof_bytes(), view_of(oneof_bytes)));
            CHECK(parsed.oneof_bytes().size == test::ultimate::BYTE_ARRAY_CAP);
        }

        SECTION("deep oneof alternative round trips") {
            Deep deep(ctx);
            require_success(deep.set_val(4000));

            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(deep.serialize(writer));

            Deep parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_val());
            CHECK(parsed.val() == 4000);
        }

        SECTION("new oneof assignment replaces old case") {
            Message first(ctx);
            require_success(first.set_oneof_string(view_of(oneof_string)));
            populate_required_fixed_array(first, ctx);
            require_success(first.set_oneof_int32(2701));

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(first.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_int32());
            CHECK(parsed.special_oneof_case() == Message::Special_oneofCase::oneof_int32);
            CHECK(parsed.oneof_int32() == 2701);
        }

        SECTION("bytes overwrite oneof message case") {
            Message first(ctx);
            auto first_oneof = first.ensure_oneof_msg();
            require_success(first_oneof);
            require_success((*first_oneof)->set_name(view_of(nested_name)));
            populate_required_fixed_array(first, ctx);
            require_success(first.set_oneof_bytes(view_of(oneof_bytes)));

            uint8_t encoded[512] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(first.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_bytes());
            CHECK(parsed.special_oneof_case() == Message::Special_oneofCase::oneof_bytes);
            CHECK(view_equal(parsed.oneof_bytes(), view_of(oneof_bytes)));
        }

        SECTION("move construction preserves active bytes case") {
            Message source(ctx);
            require_success(source.set_oneof_bytes(view_of(oneof_bytes)));

            Message moved(protocyte::move(source));
            REQUIRE(moved.has_oneof_bytes());
            CHECK(view_equal(moved.oneof_bytes(), view_of(oneof_bytes)));
            CHECK(source.special_oneof_case() == Message::Special_oneofCase::none);
            CHECK(source.oneof_bytes().size == 0u);
        }

        SECTION("move assignment transfers active message case") {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(**oneof_msg, view_of(nested_name), 2802);

            Message target(ctx);
            require_success(target.set_oneof_string(view_of(oneof_string)));
            target = protocyte::move(source);

            REQUIRE(target.has_oneof_msg());
            REQUIRE(target.oneof_msg() != nullptr);
            check_nested1(*target.oneof_msg(), view_of(nested_name), 2802);
            CHECK(source.special_oneof_case() == Message::Special_oneofCase::none);
        }

        SECTION("copy_from preserves active oneof state") {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(**oneof_msg, view_of(nested_name), 2802);

            Message target(ctx);
            require_success(target.set_oneof_string(view_of(oneof_string)));
            require_success(target.copy_from(source));

            REQUIRE(target.has_oneof_msg());
            REQUIRE(target.oneof_msg() != nullptr);
            check_nested1(*target.oneof_msg(), view_of(nested_name), 2802);
            CHECK(target.special_oneof_case() == Message::Special_oneofCase::oneof_msg);
        }

        SECTION("clone preserves active oneof state") {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(**oneof_msg, view_of(nested_name), 2802);

            auto cloned = source.clone();
            require_success(cloned);
            REQUIRE(cloned->has_oneof_msg());
            REQUIRE(cloned->oneof_msg() != nullptr);
            check_nested1(*cloned->oneof_msg(), view_of(nested_name), 2802);
            CHECK(cloned->special_oneof_case() == Message::Special_oneofCase::oneof_msg);
        }
    }

    void check_crazy_bytes_oneof_alternatives(Config::Context &ctx) {
        SECTION("plain bytes alternative round trips") {
            Message message(ctx);
            require_success(message.set_crazy_plain_bytes(view_of(crazy_plain_bytes)));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_plain_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_plain_bytes);
            CHECK(view_equal(parsed.crazy_plain_bytes(), view_of(crazy_plain_bytes)));
        }

        SECTION("bounded bytes alternative round trips") {
            Message message(ctx);
            require_success(message.set_crazy_bounded_bytes(view_of(crazy_bounded_bytes)));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_bounded_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_bounded_bytes);
            CHECK(view_equal(parsed.crazy_bounded_bytes(), view_of(crazy_bounded_bytes)));
        }

        SECTION("fixed bytes alternative round trips") {
            Message message(ctx);
            require_success(message.set_crazy_fixed_bytes(view_of(crazy_fixed_bytes)));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_fixed_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_fixed_bytes);
            CHECK(view_equal(parsed.crazy_fixed_bytes(), view_of(crazy_fixed_bytes)));
        }

        SECTION("repeated bytes wrapper alternative round trips") {
            Message message(ctx);
            auto crazy_repeated = message.ensure_crazy_repeated_bytes();
            require_success(crazy_repeated);
            populate_repeated_bytes_holder(**crazy_repeated, ctx);
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_repeated_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_repeated_bytes);
            check_repeated_bytes_holder(*parsed.crazy_repeated_bytes());
        }

        SECTION("bounded repeated bytes wrapper alternative round trips") {
            Message message(ctx);
            auto crazy_bounded = message.ensure_crazy_bounded_repeated_bytes();
            require_success(crazy_bounded);
            populate_bounded_repeated_bytes_holder(**crazy_bounded, ctx);
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_bounded_repeated_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes);
            check_bounded_repeated_bytes_holder(*parsed.crazy_bounded_repeated_bytes());
        }

        SECTION("fixed repeated bytes wrapper alternative round trips") {
            Message message(ctx);
            auto crazy_fixed = message.ensure_crazy_fixed_repeated_bytes();
            require_success(crazy_fixed);
            populate_fixed_repeated_bytes_holder(**crazy_fixed, ctx);
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_fixed_repeated_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes);
            check_fixed_repeated_bytes_holder(*parsed.crazy_fixed_repeated_bytes());
        }

        SECTION("fixed bytes replace repeated wrapper case") {
            Message message(ctx);
            auto crazy_repeated = message.ensure_crazy_repeated_bytes();
            require_success(crazy_repeated);
            populate_repeated_bytes_holder(**crazy_repeated, ctx);
            require_success(message.set_crazy_fixed_bytes(view_of(crazy_fixed_bytes)));
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_fixed_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_fixed_bytes);
            CHECK(view_equal(parsed.crazy_fixed_bytes(), view_of(crazy_fixed_bytes)));
        }

        SECTION("fixed repeated wrapper replaces bounded bytes case") {
            Message message(ctx);
            require_success(message.set_crazy_bounded_bytes(view_of(crazy_bounded_bytes)));
            auto crazy_fixed = message.ensure_crazy_fixed_repeated_bytes();
            require_success(crazy_fixed);
            populate_fixed_repeated_bytes_holder(**crazy_fixed, ctx);
            populate_required_fixed_array(message, ctx);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_crazy_fixed_repeated_bytes());
            CHECK(parsed.crazy_bytes_oneof_case() == Message::Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes);
            check_fixed_repeated_bytes_holder(*parsed.crazy_fixed_repeated_bytes());
        }
    }

    void check_fixed_array_presence(Config::Context &ctx) {
        SECTION("unset fixed bytes stay absent through round trip") {
            Message message(ctx);
            CHECK_FALSE(message.has_sha256());
            CHECK(message.sha256().size == 0u);
            populate_required_fixed_array(message, ctx);

            auto encoded_size = message.encoded_size();
            require_success(encoded_size);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));
            REQUIRE(writer.position() == *encoded_size);

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            CHECK_FALSE(parsed.has_sha256());
            CHECK(parsed.sha256().size == 0u);
        }

        SECTION("mutable fixed bytes mark presence and zero initialize") {
            Message message(ctx);
            auto sha256 = message.mutable_sha256();
            REQUIRE(message.has_sha256());
            REQUIRE(sha256.size == 32u);
            uint8_t expected_byte = 1u;
            for (auto &byte : sha256) {
                CHECK(byte == 0u);
                byte = expected_byte++;
            }
            CHECK(expected_byte == 33u);

            uint8_t forward_byte = 1u;
            for (const auto byte : message.sha256()) { CHECK(byte == forward_byte++); }
            CHECK(forward_byte == 33u);

            uint8_t reverse_byte = 32u;
            for (auto it = message.sha256().rbegin(); it != message.sha256().rend(); ++it) {
                CHECK(*it == reverse_byte--);
            }
            CHECK(reverse_byte == 0u);

            message.clear_sha256();
            CHECK_FALSE(message.has_sha256());
            CHECK(message.sha256().size == 0u);
        }

        SECTION("explicit zero bytes stay present through round trip") {
            Message message(ctx);
            constexpr uint8_t zero_sha256[32] = {};
            require_success(message.set_sha256(view_of(zero_sha256)));
            REQUIRE(message.has_sha256());
            populate_required_fixed_array(message, ctx);

            auto encoded_size = message.encoded_size();
            require_success(encoded_size);
            REQUIRE(*encoded_size > 0u);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));
            REQUIRE(writer.position() == *encoded_size);

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_sha256());
            CHECK(view_equal(parsed.sha256(), view_of(zero_sha256)));
        }
    }

    void check_array_validation(Config::Context &ctx) {
        SECTION("byte array capacity is enforced") {
            Message message(ctx);
            CHECK(message.byte_array_size() == 0u);
            CHECK(Message::byte_array_max_size() == test::ultimate::BYTE_ARRAY_CAP);
            CHECK(Message::float_expr_array_max_size() == Message::FLOATISH_BOUND);

            require_success(message.resize_byte_array(test::ultimate::BYTE_ARRAY_CAP));
            REQUIRE(message.byte_array_size() == test::ultimate::BYTE_ARRAY_CAP);
            size_t zero_bytes {};
            for (const auto byte : message.byte_array()) {
                CHECK(byte == 0u);
                ++zero_bytes;
            }
            CHECK(zero_bytes == test::ultimate::BYTE_ARRAY_CAP);

            message.clear_byte_array();
            CHECK(message.byte_array_size() == 0u);

            require_failure(message.resize_byte_array(test::ultimate::BYTE_ARRAY_CAP + 1u),
                            protocyte::ErrorCode::count_limit);
            require_failure(message.set_byte_array(view_of(large_byte_array)), protocyte::ErrorCode::count_limit);
            require_success(message.set_float_expr_array(view_of(float_expr_array)));
            require_failure(message.set_float_expr_array(view_of(byte_array)), protocyte::ErrorCode::count_limit);
        }

        SECTION("bounded repeated arrays reject extra elements") {
            Message message(ctx);
            auto &integer_array = message.mutable_integer_array();
            for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
                require_success(integer_array.push_back(integer_array_values[i]));
            }
            require_failure(integer_array.push_back(999), protocyte::ErrorCode::count_limit);
        }

        SECTION("bounded repeated bytes reject extra elements") {
            Message message(ctx);
            auto &bounded_repeated_byte_array = message.mutable_bounded_repeated_byte_array();
            append_bytes(bounded_repeated_byte_array, ctx, view_of(repeated_bytes_0));
            append_bytes(bounded_repeated_byte_array, ctx, view_of(repeated_bytes_1));
            append_bytes(bounded_repeated_byte_array, ctx, view_of(repeated_bytes_2));

            Config::Bytes overflow(&ctx);
            assign_bytes(overflow, view_of(repeated_bytes_3));
            require_failure(bounded_repeated_byte_array.push_back(protocyte::move(overflow)),
                            protocyte::ErrorCode::count_limit);
        }

        SECTION("empty fixed repeated arrays may stay absent before encoding") {
            Message message(ctx);

            auto encoded_size = message.encoded_size();
            require_success(encoded_size);
            CHECK(*encoded_size == 0u);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));
            CHECK(writer.position() == 0u);
        }

        SECTION("partially populated fixed repeated bytes are rejected before encoding") {
            Message message(ctx);
            auto &fixed_repeated_byte_array = message.mutable_fixed_repeated_byte_array();
            append_bytes(fixed_repeated_byte_array, ctx, view_of(repeated_bytes_0));
            append_bytes(fixed_repeated_byte_array, ctx, view_of(repeated_bytes_1));

            require_failure(message.encoded_size(), protocyte::ErrorCode::invalid_argument);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_failure(message.serialize(writer), protocyte::ErrorCode::invalid_argument);
        }

        SECTION("copy_from self-assignment keeps bounded repeated arrays intact") {
            Message message(ctx);
            require_success(message.set_byte_array(view_of(byte_array)));
            for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
                require_success(message.mutable_integer_array().push_back(integer_array_values[i]));
            }
            for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
                require_success(message.mutable_fixed_integer_array().push_back(fixed_integer_array_values[i]));
            }

            require_success(message.copy_from(message));

            CHECK(view_equal(message.byte_array(), view_of(byte_array)));
            CHECK(message.byte_array_size() == sizeof(byte_array));
            for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
                CHECK(message.integer_array()[i] == integer_array_values[i]);
            }
            for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
                CHECK(message.fixed_integer_array()[i] == fixed_integer_array_values[i]);
            }
        }

        SECTION("move assignment transfers bounded arrays") {
            Message source(ctx);
            require_success(source.set_byte_array(view_of(byte_array)));
            for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
                require_success(source.mutable_integer_array().push_back(integer_array_values[i]));
            }
            for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
                require_success(source.mutable_fixed_integer_array().push_back(fixed_integer_array_values[i]));
            }

            Message target(ctx);
            require_success(target.set_byte_array(view_of(alternate_byte_array)));
            require_success(target.mutable_integer_array().push_back(999));
            require_success(target.mutable_fixed_integer_array().push_back(111u));
            target = protocyte::move(source);

            CHECK(view_equal(target.byte_array(), view_of(byte_array)));
            CHECK(target.byte_array_size() == sizeof(byte_array));
            const auto &target_integer_array = target.integer_array();
            REQUIRE(target_integer_array.size() == Message::INTEGER_ARRAY_CAP);
            for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
                CHECK(target_integer_array[i] == integer_array_values[i]);
            }
            const auto &target_fixed_integer_array = target.fixed_integer_array();
            REQUIRE(target_fixed_integer_array.size() == Message::FIXED_INTEGER_ARRAY_CAP);
            for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
                CHECK(target_fixed_integer_array[i] == fixed_integer_array_values[i]);
            }
            CHECK(source.byte_array_size() == 0u);
            CHECK(source.integer_array().size() == 0u);
            CHECK(source.fixed_integer_array().size() == 0u);
        }

        SECTION("partially populated fixed arrays are rejected before encoding") {
            Message message(ctx);
            auto &fixed_integer_array = message.mutable_fixed_integer_array();
            require_success(fixed_integer_array.push_back(fixed_integer_array_values[0]));
            require_success(fixed_integer_array.push_back(fixed_integer_array_values[1]));

            require_failure(message.encoded_size(), protocyte::ErrorCode::invalid_argument);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_failure(message.serialize(writer), protocyte::ErrorCode::invalid_argument);
        }

        SECTION("short fixed-byte payloads are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::sha256),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, sizeof(short_sha256)));
            require_success(writer.write(short_sha256, sizeof(short_sha256)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_argument);
        }

        SECTION("oversized bounded byte arrays are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::byte_array),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, sizeof(large_byte_array)));
            require_success(writer.write(large_byte_array, sizeof(large_byte_array)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::count_limit);
        }

        SECTION("oversized bounded oneof bytes are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::oneof_bytes),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, sizeof(large_byte_array)));
            require_success(writer.write(large_byte_array, sizeof(large_byte_array)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::count_limit);
        }

        SECTION("malformed map entries are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::map_str_int32),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, 2u));
            require_success(protocyte::write_tag(writer, 1u, protocyte::WireType::VARINT));
            require_success(protocyte::write_varint(writer, 7u));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_wire_type);
        }

        SECTION("overlong UTF-8 is rejected while parsing") {
            constexpr uint8_t overlong_utf8[] = {0xc1u, 0xbfu};
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::f_string),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, sizeof(overlong_utf8)));
            require_success(writer.write(overlong_utf8, sizeof(overlong_utf8)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_utf8);
        }

        SECTION("overflowing 10-byte varints are rejected") {
            constexpr uint8_t malformed_varint[] = {
                0x80u, 0x80u, 0x80u, 0x80u, 0x80u, 0x80u, 0x80u, 0x80u, 0x80u, 0x02u,
            };

            protocyte::SliceReader reader(malformed_varint, sizeof(malformed_varint));
            require_failure(protocyte::read_varint(reader), protocyte::ErrorCode::malformed_varint);
        }

        SECTION("invalid tag field numbers are rejected") {
            {
                constexpr uint8_t zero_field_varint[] = {0x00u, 0x00u};

                Message parsed(ctx);
                protocyte::SliceReader reader(zero_field_varint, sizeof(zero_field_varint));
                require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_wire_type);
            }
            {
                uint8_t encoded[128] = {};
                protocyte::SliceWriter writer(encoded, sizeof(encoded));
                require_success(protocyte::write_tag(writer, 0x20000000u, protocyte::WireType::VARINT));
                require_success(protocyte::write_varint(writer, 0u));

                Message parsed(ctx);
                protocyte::SliceReader reader(encoded, writer.position());
                require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_wire_type);
            }
        }

        SECTION("partial fixed arrays are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(
                writer, static_cast<uint32_t>(Message::FieldNumber::fixed_integer_array), protocyte::WireType::VARINT));
            require_success(protocyte::write_varint(writer, fixed_integer_array_values[0]));
            require_success(protocyte::write_tag(
                writer, static_cast<uint32_t>(Message::FieldNumber::fixed_integer_array), protocyte::WireType::VARINT));
            require_success(protocyte::write_varint(writer, fixed_integer_array_values[1]));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_argument);
        }

        SECTION("bounded repeated bytes reject a fourth parsed element") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_bytes_field(
                writer, static_cast<uint32_t>(Message::FieldNumber::bounded_repeated_byte_array),
                view_of(repeated_bytes_0)));
            require_success(protocyte::write_bytes_field(
                writer, static_cast<uint32_t>(Message::FieldNumber::bounded_repeated_byte_array),
                view_of(repeated_bytes_1)));
            require_success(protocyte::write_bytes_field(
                writer, static_cast<uint32_t>(Message::FieldNumber::bounded_repeated_byte_array),
                view_of(repeated_bytes_2)));
            require_success(protocyte::write_bytes_field(
                writer, static_cast<uint32_t>(Message::FieldNumber::bounded_repeated_byte_array),
                view_of(repeated_bytes_3)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::count_limit);
        }

        SECTION("partial fixed repeated bytes are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_bytes_field(
                writer, static_cast<uint32_t>(Message::FieldNumber::fixed_repeated_byte_array),
                view_of(repeated_bytes_0)));
            require_success(protocyte::write_bytes_field(
                writer, static_cast<uint32_t>(Message::FieldNumber::fixed_repeated_byte_array),
                view_of(repeated_bytes_1)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_argument);
        }
    }

    void populate_cross_message(Cross &message) {
        require_success(message.set_external_bytes(view_of(external_bytes)));
        for (size_t i = 0; i < sizeof(mirrored_values) / sizeof(mirrored_values[0]); ++i) {
            require_success(message.mutable_mirrored_values().push_back(mirrored_values[i]));
        }
        auto nested = message.ensure_nested();
        require_success(nested);
        require_success((*nested)->set_nested_bytes(view_of(nested_bytes)));
    }

    void check_cross_message(const Cross &message) {
        CHECK(view_equal(message.external_bytes(), view_of(external_bytes)));
        CHECK(message.external_bytes_size() == sizeof(external_bytes));

        check_scalar_sequence(message.mirrored_values(), mirrored_values);

        REQUIRE(message.has_nested());
        CHECK(view_equal(message.nested()->nested_bytes(), view_of(nested_bytes)));
        CHECK(message.nested()->nested_bytes_size() == sizeof(nested_bytes));
    }

    void round_trip_cross_message(Config::Context &ctx) {
        Cross message(ctx);
        populate_cross_message(message);

        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        uint8_t encoded[256] = {};
        REQUIRE(*encoded_size <= sizeof(encoded));

        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(message.serialize(writer));

        Cross parsed(ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_success(parsed.merge_from(reader));
        REQUIRE(reader.eof());
        check_cross_message(parsed);
    }

    void populate_cross_package(CrossPackage &message) {
        require_success(message.set_remote_bytes(view_of(cross_package_bytes)));
        for (size_t i = 0; i < sizeof(cross_package_values) / sizeof(cross_package_values[0]); ++i) {
            require_success(message.mutable_remote_values().push_back(cross_package_values[i]));
        }
        auto nested = message.ensure_nested();
        require_success(nested);
        require_success((*nested)->set_nested_bytes(view_of(cross_package_nested_bytes)));
    }

    void check_cross_package(const CrossPackage &message) {
        CHECK(view_equal(message.remote_bytes(), view_of(cross_package_bytes)));
        CHECK(message.remote_bytes_size() == sizeof(cross_package_bytes));

        check_scalar_sequence(message.remote_values(), cross_package_values);

        REQUIRE(message.has_nested());
        CHECK(view_equal(message.nested()->nested_bytes(), view_of(cross_package_nested_bytes)));
        CHECK(message.nested()->nested_bytes_size() == sizeof(cross_package_nested_bytes));
    }

    void round_trip_cross_package(Config::Context &ctx) {
        CrossPackage message(ctx);
        populate_cross_package(message);

        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        uint8_t encoded[256] = {};
        REQUIRE(*encoded_size <= sizeof(encoded));

        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(message.serialize(writer));

        CrossPackage parsed(ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_success(parsed.merge_from(reader));
        REQUIRE(reader.eof());
        check_cross_package(parsed);
    }

} // namespace

TEST_CASE("UltimateComplexMessage round-trips", "[smoke][roundtrip]") {
    auto ctx = make_context();
    auto created = Message::create(ctx);
    require_success(created);

    auto &message = *created;
    populate_message(message, ctx);
    round_trip_and_check(message, ctx);
}

TEST_CASE("UltimateComplexMessage oneofs merge correctly", "[smoke][oneof]") {
    auto ctx = make_context();
    check_oneof_alternatives(ctx);
}

TEST_CASE("Crazy bytes oneof variants merge correctly", "[smoke][oneof][bytes]") {
    auto ctx = make_context();
    check_crazy_bytes_oneof_alternatives(ctx);
}

TEST_CASE("Fixed bytes preserve presence semantics", "[smoke][fixed]") {
    auto ctx = make_context();
    check_fixed_array_presence(ctx);
}

TEST_CASE("Array bounds are enforced", "[smoke][array]") {
    auto ctx = make_context();
    check_array_validation(ctx);
}

TEST_CASE("Runtime containers expose iterator APIs", "[smoke][iterators]") {
    auto ctx = make_context();

    SECTION("vector and array support range and reverse traversal") {
        Config::Vector<protocyte::i32> values(&ctx);
        require_success(values.push_back(1));
        require_success(values.push_back(2));
        require_success(values.push_back(3));

        protocyte::i32 expected_values[] = {10, 20, 30};
        size_t index {};
        for (auto &value : values) {
            value = expected_values[index];
            ++index;
        }
        CHECK(index == 3u);

        check_scalar_sequence(values, expected_values);
        check_scalar_reverse_sequence(values, expected_values);

        protocyte::Array<protocyte::i32, 3u> bounded;
        for (const auto value : expected_values) { require_success(bounded.push_back(value)); }
        check_scalar_sequence(bounded, expected_values);
        check_scalar_reverse_sequence(bounded, expected_values);
    }

    SECTION("byte containers and views iterate in const and mutable contexts") {
        protocyte::ByteArray<sizeof(byte_array)> bytes;
        require_success(bytes.assign(view_of(byte_array)));

        size_t index {};
        for (const auto byte : bytes.view()) {
            CHECK(byte == byte_array[index]);
            ++index;
        }
        CHECK(index == sizeof(byte_array));

        auto mutable_bytes = bytes.mutable_view();
        for (auto &byte : mutable_bytes) { byte = static_cast<uint8_t>(byte ^ 0xffu); }

        index = 0u;
        for (const auto byte : bytes) {
            CHECK(byte == static_cast<uint8_t>(byte_array[index] ^ 0xffu));
            ++index;
        }
        CHECK(index == sizeof(byte_array));

        index = sizeof(byte_array);
        for (auto it = bytes.rbegin(); it != bytes.rend(); ++it) {
            --index;
            CHECK(*it == static_cast<uint8_t>(byte_array[index] ^ 0xffu));
        }
        CHECK(index == 0u);

        protocyte::FixedByteArray<sizeof(oneof_bytes)> fixed_bytes;
        auto fixed_view = fixed_bytes.mutable_view();
        index = 0u;
        for (auto &byte : fixed_view) {
            byte = oneof_bytes[index];
            ++index;
        }
        CHECK(index == sizeof(oneof_bytes));
        CHECK(view_equal(fixed_bytes.view(), view_of(oneof_bytes)));
    }

    SECTION("bytes wrappers expose mutable iterators and strings stay read-only") {
        Config::Bytes payload(&ctx);
        assign_bytes(payload, view_of(bytes_data));

        size_t index {};
        for (auto &byte : payload) { byte = static_cast<uint8_t>(byte ^ 0x1u); }

        index = 0u;
        for (const auto byte : payload) {
            CHECK(byte == static_cast<uint8_t>(bytes_data[index] ^ 0x1u));
            ++index;
        }
        CHECK(index == sizeof(bytes_data));

        Config::String text(&ctx);
        assign_string(text, view_of(string_bytes));
        index = 0u;
        for (const auto byte : text) {
            CHECK(byte == string_bytes[index]);
            ++index;
        }
        CHECK(index == sizeof(string_bytes));

        index = sizeof(string_bytes);
        for (auto it = text.rbegin(); it != text.rend(); ++it) {
            --index;
            CHECK(*it == string_bytes[index]);
        }
        CHECK(index == 0u);
    }
}

TEST_CASE("HashMap iterators expose key/value proxies", "[smoke][iterators][map]") {
    auto ctx = make_context();
    Message message(ctx);
    insert_map_str_int32(message, ctx);

    bool mutated = false;
    for (auto entry : message.mutable_map_str_int32()) {
        if (view_equal(entry.key.view(), view_of(map_key))) {
            entry.value = 302;
            mutated = true;
        }
    }
    CHECK(mutated);

    bool saw_iterator = false;
    for (const auto entry : message.map_str_int32()) {
        if (view_equal(entry.key.view(), view_of(map_key)) && entry.value == 302) {
            saw_iterator = true;
        }
    }
    CHECK(saw_iterator);
}

TEST_CASE("Cross-message constants resolve into arrays", "[smoke][constants]") {
    auto ctx = make_context();
    round_trip_cross_message(ctx);
}

TEST_CASE("Cross-package constants resolve into arrays", "[smoke][constants]") {
    auto ctx = make_context();
    round_trip_cross_package(ctx);
}

TEST_CASE("Protocyte encoding matches protobuf runtime bytes", "[smoke][compat]") {
    auto ctx = make_context();

    SECTION("empty message") {
        CompatMessage protocyte_message(ctx);
        require_same_compat_bytes("empty", protocyte_message, compat_cases::empty);
    }

    SECTION("varint scalars") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_f_int32(std::numeric_limits<int32_t>::min()));
        require_success(protocyte_message.set_f_int64(std::numeric_limits<int64_t>::min()));
        require_success(protocyte_message.set_f_uint32(std::numeric_limits<uint32_t>::max()));
        require_success(protocyte_message.set_f_uint64(std::numeric_limits<uint64_t>::max()));
        require_success(protocyte_message.set_f_sint32(-17));
        require_success(protocyte_message.set_f_sint64(-17000000000ll));
        require_success(protocyte_message.set_f_bool(true));
        require_success(protocyte_message.set_mode(CompatMode::SECOND));

        require_same_compat_bytes("varint", protocyte_message, compat_cases::varint);
    }

    SECTION("fixed scalars") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_f_fixed32(0x11223344u));
        require_success(protocyte_message.set_f_fixed64(0x1122334455667788ull));
        require_success(protocyte_message.set_f_sfixed32(-1234567));
        require_success(protocyte_message.set_f_sfixed64(-1234567890123ll));
        require_success(protocyte_message.set_f_float(-0.0f));
        require_success(protocyte_message.set_f_double(123.5));

        require_same_compat_bytes("fixed", protocyte_message, compat_cases::fixed);
    }

    SECTION("length delimited fields") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_f_string(view_of(string_bytes)));
        require_success(protocyte_message.set_f_bytes(view_of(bytes_data)));
        if (auto nested = protocyte_message.ensure_nested(); nested) {
            populate_compat_nested(**nested, 417, view_of(nested_name));
        } else {
            require_success(nested);
        }

        require_same_compat_bytes("length-delimited", protocyte_message, compat_cases::length_delimited);
    }

    SECTION("repeated fields") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.mutable_r_int32_unpacked().push_back(-1));
        require_success(protocyte_message.mutable_r_int32_unpacked().push_back(0));
        require_success(protocyte_message.mutable_r_int32_unpacked().push_back(150));
        require_success(protocyte_message.mutable_r_int32_packed().push_back(-1));
        require_success(protocyte_message.mutable_r_int32_packed().push_back(0));
        require_success(protocyte_message.mutable_r_int32_packed().push_back(150));
        require_success(protocyte_message.mutable_r_double().push_back(23.5));
        require_success(protocyte_message.mutable_r_double().push_back(-0.0));

        require_same_compat_bytes("repeated", protocyte_message, compat_cases::repeated);
    }

    SECTION("oneof string") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_oneof_string(view_of(oneof_string)));
        require_same_compat_bytes("oneof-string", protocyte_message, compat_cases::oneof_string);
    }

    SECTION("oneof int32") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_oneof_int32(-2701));
        require_same_compat_bytes("oneof-int32", protocyte_message, compat_cases::oneof_int32);
    }

    SECTION("oneof nested") {
        CompatMessage protocyte_message(ctx);

        if (auto nested = protocyte_message.ensure_oneof_nested(); nested) {
            populate_compat_nested(**nested, 90210, view_of(nested_description));
        } else {
            require_success(nested);
        }
        require_same_compat_bytes("oneof-nested", protocyte_message, compat_cases::oneof_nested);
    }

    SECTION("oneof bytes") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_oneof_bytes(view_of(oneof_bytes)));
        require_same_compat_bytes("oneof-bytes", protocyte_message, compat_cases::oneof_bytes);
    }

    SECTION("optional fields") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_opt_int32(-99));
        require_success(protocyte_message.set_opt_string(view_of(optional_string)));
        require_same_compat_bytes("optional", protocyte_message, compat_cases::optional_case);
    }
}

TEST_CASE("Hosted allocator honors requested alignment", "[smoke][allocator]") {
    auto allocator = protocyte::hosted_allocator();
    auto *raw = allocator.allocate(allocator.state, sizeof(HostedOverAligned), alignof(HostedOverAligned));
    REQUIRE(raw != nullptr);
    CHECK((reinterpret_cast<std::uintptr_t>(raw) % alignof(HostedOverAligned)) == 0u);
    allocator.deallocate(allocator.state, raw, sizeof(HostedOverAligned), alignof(HostedOverAligned));
}

TEST_CASE("ZigZag encoding matches protobuf wire mapping", "[smoke][zigzag]") {
    CHECK(protocyte::encode_zigzag32(0) == 0u);
    CHECK(protocyte::encode_zigzag32(-1) == 1u);
    CHECK(protocyte::encode_zigzag32(1) == 2u);
    CHECK(protocyte::encode_zigzag32(-2) == 3u);
    CHECK(protocyte::encode_zigzag32(std::numeric_limits<int32_t>::max()) == 0xfffffffeu);
    CHECK(protocyte::encode_zigzag32(std::numeric_limits<int32_t>::min()) == 0xffffffffu);

    CHECK(protocyte::encode_zigzag64(0) == 0u);
    CHECK(protocyte::encode_zigzag64(-1) == 1u);
    CHECK(protocyte::encode_zigzag64(1) == 2u);
    CHECK(protocyte::encode_zigzag64(-2) == 3u);
    CHECK(protocyte::encode_zigzag64(std::numeric_limits<int64_t>::max()) == 0xfffffffffffffffeull);
    CHECK(protocyte::encode_zigzag64(std::numeric_limits<int64_t>::min()) == 0xffffffffffffffffull);

    CHECK(protocyte::decode_zigzag32(0u) == 0);
    CHECK(protocyte::decode_zigzag32(1u) == -1);
    CHECK(protocyte::decode_zigzag32(2u) == 1);
    CHECK(protocyte::decode_zigzag32(3u) == -2);
    CHECK(protocyte::decode_zigzag32(0xfffffffeu) == std::numeric_limits<int32_t>::max());
    CHECK(protocyte::decode_zigzag32(0xffffffffu) == std::numeric_limits<int32_t>::min());

    CHECK(protocyte::decode_zigzag64(0u) == 0);
    CHECK(protocyte::decode_zigzag64(1u) == -1);
    CHECK(protocyte::decode_zigzag64(2u) == 1);
    CHECK(protocyte::decode_zigzag64(3u) == -2);
    CHECK(protocyte::decode_zigzag64(0xfffffffffffffffeull) == std::numeric_limits<int64_t>::max());
    CHECK(protocyte::decode_zigzag64(0xffffffffffffffffull) == std::numeric_limits<int64_t>::min());
}

TEST_CASE("tag_size matches protobuf group sizing", "[smoke][runtime]") {
    CHECK(protocyte::tag_size(1u) == 1u);
    CHECK(protocyte::tag_size(1u, protocyte::WireType::VARINT) == 1u);
    CHECK(protocyte::tag_size(1u, protocyte::WireType::LEN) == 1u);
    CHECK(protocyte::tag_size(1u, protocyte::WireType::SGROUP) == 2u);

    constexpr uint32_t large_field_number = 2048u;
    const auto single_tag_size = protocyte::varint_size((static_cast<protocyte::u64>(large_field_number) << 3u) |
                                                        static_cast<protocyte::u64>(protocyte::WireType::VARINT));
    CHECK(protocyte::tag_size(large_field_number, protocyte::WireType::VARINT) == single_tag_size);
    CHECK(protocyte::tag_size(large_field_number, protocyte::WireType::SGROUP) == single_tag_size * 2u);
}

TEST_CASE("length-delimited sizes reject values that do not fit usize", "[smoke][runtime]") {
    if constexpr (sizeof(protocyte::usize) == sizeof(protocyte::u64)) {
        SUCCEED("usize can represent every u64 length on this target");
    } else {
        constexpr uint8_t overflow_length[] = {0x80u, 0x80u, 0x80u, 0x80u, 0x10u};

        protocyte::SliceReader size_reader(overflow_length, sizeof(overflow_length));
        auto size = protocyte::read_length_delimited_size(size_reader);
        require_failure(size, protocyte::ErrorCode::integer_overflow);

        protocyte::SliceReader skip_reader(overflow_length, sizeof(overflow_length));
        require_failure(protocyte::skip_field(skip_reader, protocyte::WireType::LEN),
                        protocyte::ErrorCode::integer_overflow);
    }
}

TEST_CASE("Result<void> carries status without a payload", "[smoke][runtime]") {
    const auto ok = protocyte::Result<void> {};
    REQUIRE(ok);
    CHECK(ok.is_ok());
    ok.value();
    *ok;
    CHECK(ok.status());

    const auto err = protocyte::Result<void> {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 12u, 7u)};
    REQUIRE_FALSE(err);
    CHECK_FALSE(err.is_ok());
    CHECK(err.error().code == protocyte::ErrorCode::invalid_argument);
    CHECK(err.error().offset == 12u);
    CHECK(err.error().field_number == 7u);
    CHECK_FALSE(err.status());
    CHECK(err.status().error().code == protocyte::ErrorCode::invalid_argument);

    const auto make_status = []() noexcept -> protocyte::Status { return {}; };
    require_success(make_status());

    const auto fail_status = []() noexcept -> protocyte::Status {
        return protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 4u, 2u);
    };
    require_failure(fail_status(), protocyte::ErrorCode::invalid_argument);
}

TEST_CASE("monadic runtime operations compose for status, result, and optional", "[smoke][runtime]") {
    SECTION("Status supports value and error transformations") {
        auto transformed = protocyte::Status {}.transform([]() noexcept { return 17; });
        require_success(transformed);
        CHECK(*transformed == 17);

        auto transformed_void = protocyte::Status {}.transform([]() noexcept {});
        require_success(transformed_void);

        auto chained = protocyte::Status {}.and_then([]() noexcept { return protocyte::Result<int> {23}; });
        require_success(chained);
        CHECK(*chained == 23);

        auto recovered =
            protocyte::Status {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 9u, 4u)}.or_else(
                [](const protocyte::Error &error) noexcept {
                    return protocyte::Result<void, protocyte::u32> {
                        protocyte::unexpected(static_cast<protocyte::u32>(error.offset))};
                });
        REQUIRE_FALSE(recovered);
        CHECK(recovered.error() == 9u);

        auto transformed_error =
            protocyte::Status {protocyte::unexpected(protocyte::ErrorCode::count_limit, 5u, 2u)}.transform_error(
                [](const protocyte::Error &error) noexcept { return static_cast<protocyte::u32>(error.field_number); });
        REQUIRE_FALSE(transformed_error);
        CHECK(transformed_error.error() == 2u);

        auto member_error =
            protocyte::Status {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 12u, 7u)}.transform_error(
                &protocyte::Error::offset);
        REQUIRE_FALSE(member_error);
        CHECK(member_error.error() == 12u);
    }

    SECTION("Result<T> supports expected-style chaining") {
        const auto make_value = []() noexcept -> protocyte::Result<int> { return 4; };
        require_success(make_value());
        CHECK(*make_value() == 4);

        const auto fail_value = []() noexcept -> protocyte::Result<int> {
            return protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 13u, 6u);
        };
        require_failure(fail_value(), protocyte::ErrorCode::invalid_argument);

        auto transformed = protocyte::Result<int> {4}.transform([](const int value) noexcept { return value + 3; });
        require_success(transformed);
        CHECK(*transformed == 7);

        auto transformed_void = protocyte::Result<int> {4}.transform([](const int) noexcept {});
        require_success(transformed_void);

        auto chained = protocyte::Result<int> {6}.and_then(
            [](const int value) noexcept { return protocyte::Result<int> {value * 2}; });
        require_success(chained);
        CHECK(*chained == 12);

        auto recovered =
            protocyte::Result<int> {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 11u, 3u)}.or_else(
                [](const protocyte::Error &error) noexcept {
                    return protocyte::Result<int, protocyte::u32> {
                        protocyte::unexpected(static_cast<protocyte::u32>(error.offset))};
                });
        REQUIRE_FALSE(recovered);
        CHECK(recovered.error() == 11u);

        auto transformed_error =
            protocyte::Result<int> {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 13u, 6u)}
                .transform_error([](const protocyte::Error &error) noexcept {
                    return static_cast<protocyte::u32>(error.field_number);
                });
        REQUIRE_FALSE(transformed_error);
        CHECK(transformed_error.error() == 6u);
    }

    SECTION("Optional supports and_then, transform, and or_else") {
        protocyte::Optional<int> value {};
        require_success(value.emplace(8));

        auto chained = value.and_then([](const int current) noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(current + 1);
            return out;
        });
        REQUIRE(chained);
        CHECK(*chained == 9);

        auto transformed = value.transform([](const int current) noexcept { return current * 3; });
        REQUIRE(transformed);
        CHECK(*transformed == 24);

        protocyte::Optional<int> empty {};
        auto recovered = protocyte::move(empty).or_else([]() noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(42);
            return out;
        });
        REQUIRE(recovered);
        CHECK(*recovered == 42);
    }
}

TEST_CASE("monadic runtime operations stay lazy and preserve overload flexibility", "[smoke][runtime]") {
    SECTION("Status only invokes the relevant callback branch") {
        bool transform_called = false;
        bool and_then_called = false;
        bool or_else_called = false;
        bool transform_error_called = false;

        auto failed_status = protocyte::Status {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 8u, 3u)};
        auto transformed = failed_status.transform([&]() noexcept -> int {
            transform_called = true;
            return 99;
        });
        REQUIRE_FALSE(transformed);
        CHECK_FALSE(transform_called);

        auto chained = failed_status.and_then([&]() noexcept -> protocyte::Result<int> {
            and_then_called = true;
            return 99;
        });
        REQUIRE_FALSE(chained);
        CHECK_FALSE(and_then_called);

        auto recovered = protocyte::Status {}.or_else([&](const protocyte::Error &) noexcept -> protocyte::Status {
            or_else_called = true;
            return {};
        });
        require_success(recovered);
        CHECK_FALSE(or_else_called);

        auto ok_error_transform = protocyte::Status {}.transform_error([&](const protocyte::Error &) noexcept {
            transform_error_called = true;
            return protocyte::u32 {42u};
        });
        REQUIRE(ok_error_transform);
        CHECK_FALSE(transform_error_called);
    }

    SECTION("Result monadic overloads follow value category and constness") {
        using ResultU32 = protocyte::Result<int, protocyte::u32>;

        static_assert(std::is_same_v<decltype(protocyte::Result<int> {1}.transform(ResultTransformQualifier {})),
                                     protocyte::Result<int>>);
        static_assert(std::is_same_v<decltype(protocyte::Result<int> {1}.and_then(ResultAndThenQualifier {})),
                                     protocyte::Result<int>>);
        static_assert(!CanTransformMoveOnlyMember<protocyte::Result<MoveOnlyMemberProbe> &>);
        static_assert(!CanTransformMoveOnlyMember<const protocyte::Result<MoveOnlyMemberProbe> &>);
        static_assert(CanTransformMoveOnlyMember<protocyte::Result<MoveOnlyMemberProbe> &&>);
        static_assert(!CanTransformMoveOnlyMember<const protocyte::Result<MoveOnlyMemberProbe> &&>);
        static_assert(std::is_same_v<decltype(protocyte::Result<int> {
                                         protocyte::unexpected(protocyte::ErrorCode::invalid_argument)}
                                                  .or_else(ResultErrorQualifier {})),
                                     ResultU32>);
        static_assert(std::is_same_v<decltype(protocyte::Result<int> {
                                         protocyte::unexpected(protocyte::ErrorCode::invalid_argument)}
                                                  .transform_error(ResultTransformErrorQualifier {})),
                                     ResultU32>);
        static_assert(std::is_same_v<decltype(protocyte::unexpected(protocyte::ErrorCode::invalid_argument)),
                                     protocyte::Unexpected<protocyte::ErrorCode>>);
        static_assert(!CanCallUnexpected<protocyte::Unexpected<protocyte::u32>>);
        static_assert(std::is_same_v<decltype(protocyte::Result<int> {7}.status()), protocyte::Status>);
        static_assert(
            std::is_same_v<decltype(protocyte::Result<int, protocyte::u32> {protocyte::unexpected(9u)}.status()),
                           protocyte::Result<void, protocyte::u32>>);

        auto custom_error_result = protocyte::Result<int, protocyte::ErrorCode> {
            protocyte::unexpected(protocyte::ErrorCode::invalid_argument)};
        REQUIRE_FALSE(custom_error_result);
        CHECK(custom_error_result.error() == protocyte::ErrorCode::invalid_argument);

        protocyte::Result<int> lvalue {10};
        const protocyte::Result<int> const_lvalue {10};
        auto lvalue_transform = lvalue.transform(ResultTransformQualifier {});
        auto const_lvalue_transform = const_lvalue.transform(ResultTransformQualifier {});
        auto rvalue_transform = protocyte::Result<int> {10}.transform(ResultTransformQualifier {});
        auto const_rvalue_transform = protocyte::move(const_lvalue).transform(ResultTransformQualifier {});
        CHECK(*lvalue_transform == 11);
        CHECK(*const_lvalue_transform == 12);
        CHECK(*rvalue_transform == 13);
        CHECK(*const_rvalue_transform == 14);

        auto lvalue_chain = lvalue.and_then(ResultAndThenQualifier {});
        auto const_lvalue_chain = const_lvalue.and_then(ResultAndThenQualifier {});
        auto rvalue_chain = protocyte::Result<int> {10}.and_then(ResultAndThenQualifier {});
        auto const_rvalue_chain = protocyte::move(const_lvalue).and_then(ResultAndThenQualifier {});
        CHECK(*lvalue_chain == 20);
        CHECK(*const_lvalue_chain == 30);
        CHECK(*rvalue_chain == 40);
        CHECK(*const_rvalue_chain == 50);

        protocyte::Result<int> lvalue_error {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 0u, 5u)};
        const protocyte::Result<int> const_lvalue_error {
            protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 0u, 5u)};
        auto lvalue_or_else = lvalue_error.or_else(ResultErrorQualifier {});
        auto const_lvalue_or_else = const_lvalue_error.or_else(ResultErrorQualifier {});
        auto rvalue_or_else =
            protocyte::Result<int> {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 0u, 5u)}.or_else(
                ResultErrorQualifier {});
        auto const_rvalue_or_else = protocyte::move(const_lvalue_error).or_else(ResultErrorQualifier {});
        REQUIRE_FALSE(lvalue_or_else);
        REQUIRE_FALSE(const_lvalue_or_else);
        REQUIRE_FALSE(rvalue_or_else);
        REQUIRE_FALSE(const_rvalue_or_else);
        CHECK(lvalue_or_else.error() == 105u);
        CHECK(const_lvalue_or_else.error() == 205u);
        CHECK(rvalue_or_else.error() == 305u);
        CHECK(const_rvalue_or_else.error() == 405u);

        auto lvalue_transform_error = lvalue_error.transform_error(ResultTransformErrorQualifier {});
        auto const_lvalue_transform_error = const_lvalue_error.transform_error(ResultTransformErrorQualifier {});
        auto rvalue_transform_error =
            protocyte::Result<int> {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 0u, 5u)}
                .transform_error(ResultTransformErrorQualifier {});
        auto const_rvalue_transform_error =
            protocyte::move(const_lvalue_error).transform_error(ResultTransformErrorQualifier {});
        REQUIRE_FALSE(lvalue_transform_error);
        REQUIRE_FALSE(const_lvalue_transform_error);
        REQUIRE_FALSE(rvalue_transform_error);
        REQUIRE_FALSE(const_rvalue_transform_error);
        CHECK(lvalue_transform_error.error() == 505u);
        CHECK(const_lvalue_transform_error.error() == 605u);
        CHECK(rvalue_transform_error.error() == 705u);
        CHECK(const_rvalue_transform_error.error() == 805u);

        auto ok_status = protocyte::Result<int, protocyte::u32> {17}.status();
        auto err_status = protocyte::Result<int, protocyte::u32> {protocyte::unexpected(21u)}.status();
        REQUIRE(ok_status);
        REQUIRE_FALSE(err_status);
        CHECK(err_status.error() == 21u);

        MemberInvokeProbe probe {9};
        auto member_object_transform =
            protocyte::Result<MemberInvokeProbe> {MemberInvokeProbe {7}}.transform(&MemberInvokeProbe::value);
        auto member_pointer_transform =
            protocyte::Result<MemberInvokeProbe *> {&probe}.transform(&MemberInvokeProbe::value);
        auto member_function_transform =
            protocyte::Result<MemberInvokeProbe> {MemberInvokeProbe {8}}.transform(&MemberInvokeProbe::doubled);
        auto member_function_chain =
            protocyte::Result<MemberInvokeProbe> {MemberInvokeProbe {10}}.and_then(&MemberInvokeProbe::next);
        require_success(member_object_transform);
        require_success(member_pointer_transform);
        require_success(member_function_transform);
        require_success(member_function_chain);
        CHECK(*member_object_transform == 7);
        CHECK(*member_pointer_transform == 9);
        CHECK(*member_function_transform == 16);
        CHECK(*member_function_chain == 13);

        auto move_only_member =
            protocyte::Result<MoveOnlyMemberProbe> {MoveOnlyMemberProbe {31}}.transform(&MoveOnlyMemberProbe::child);
        require_success(move_only_member);
        CHECK(move_only_member->value == 31);

        auto error_member_transform =
            protocyte::Result<int, ErrorMemberProbe> {protocyte::unexpected(ErrorMemberProbe {19u, 23u})}
                .transform_error(&ErrorMemberProbe::code);
        REQUIRE_FALSE(error_member_transform);
        CHECK(error_member_transform.error() == 19u);
    }

    SECTION("Optional monadic overloads follow value category and stay lazy") {
        static_assert(std::is_same_v<decltype(protocyte::Optional<int> {}.transform(OptionalTransformQualifier {})),
                                     protocyte::Optional<int>>);
        static_assert(std::is_same_v<decltype(protocyte::Optional<int> {}.and_then(OptionalAndThenQualifier {})),
                                     protocyte::Optional<int>>);
        static_assert(!CanTransformMoveOnlyMember<protocyte::Optional<MoveOnlyMemberProbe> &>);
        static_assert(!CanTransformMoveOnlyMember<const protocyte::Optional<MoveOnlyMemberProbe> &>);
        static_assert(CanTransformMoveOnlyMember<protocyte::Optional<MoveOnlyMemberProbe> &&>);
        static_assert(!CanTransformMoveOnlyMember<const protocyte::Optional<MoveOnlyMemberProbe> &&>);

        protocyte::Optional<int> lvalue {};
        require_success(lvalue.emplace(10));
        const auto const_lvalue = []() noexcept {
            protocyte::Optional<int> out {};
            (void) out.emplace(10);
            return out;
        }();

        auto lvalue_transform = lvalue.transform(OptionalTransformQualifier {});
        auto const_lvalue_transform = const_lvalue.transform(OptionalTransformQualifier {});
        auto rvalue_transform =
            []() noexcept {
                protocyte::Optional<int> out {};
                (void) out.emplace(10);
                return out;
            }()
                .transform(OptionalTransformQualifier {});
        auto const_rvalue_transform = protocyte::move(const_lvalue).transform(OptionalTransformQualifier {});
        REQUIRE(lvalue_transform);
        REQUIRE(const_lvalue_transform);
        REQUIRE(rvalue_transform);
        REQUIRE(const_rvalue_transform);
        CHECK(*lvalue_transform == 11);
        CHECK(*const_lvalue_transform == 12);
        CHECK(*rvalue_transform == 13);
        CHECK(*const_rvalue_transform == 14);

        auto lvalue_chain = lvalue.and_then(OptionalAndThenQualifier {});
        auto const_lvalue_chain = const_lvalue.and_then(OptionalAndThenQualifier {});
        auto rvalue_chain =
            []() noexcept {
                protocyte::Optional<int> out {};
                (void) out.emplace(10);
                return out;
            }()
                .and_then(OptionalAndThenQualifier {});
        auto const_rvalue_chain = protocyte::move(const_lvalue).and_then(OptionalAndThenQualifier {});
        REQUIRE(lvalue_chain);
        REQUIRE(const_lvalue_chain);
        REQUIRE(rvalue_chain);
        REQUIRE(const_rvalue_chain);
        CHECK(*lvalue_chain == 20);
        CHECK(*const_lvalue_chain == 30);
        CHECK(*rvalue_chain == 40);
        CHECK(*const_rvalue_chain == 50);

        bool transform_called = false;
        bool and_then_called = false;
        bool or_else_called = false;
        protocyte::Optional<int> empty {};
        auto transformed_empty = empty.transform([&](const int) noexcept {
            transform_called = true;
            return 1;
        });
        auto chained_empty = empty.and_then([&](const int) noexcept {
            and_then_called = true;
            protocyte::Optional<int> out {};
            (void) out.emplace(1);
            return out;
        });
        protocyte::Optional<int> filled {};
        require_success(filled.emplace(3));
        auto recovered_filled = filled.or_else([&]() noexcept {
            or_else_called = true;
            protocyte::Optional<int> out {};
            (void) out.emplace(7);
            return out;
        });
        REQUIRE_FALSE(transformed_empty);
        REQUIRE_FALSE(chained_empty);
        REQUIRE(recovered_filled);
        CHECK(*recovered_filled == 3);
        CHECK_FALSE(transform_called);
        CHECK_FALSE(and_then_called);
        CHECK_FALSE(or_else_called);

        protocyte::Optional<MemberInvokeProbe> member_value {};
        require_success(member_value.emplace(MemberInvokeProbe {6}));
        auto member_object_transform = member_value.transform(&MemberInvokeProbe::value);
        auto member_function_transform = member_value.transform(&MemberInvokeProbe::doubled);
        auto member_function_chain = member_value.and_then(&MemberInvokeProbe::maybe);
        REQUIRE(member_object_transform);
        REQUIRE(member_function_transform);
        REQUIRE(member_function_chain);
        CHECK(*member_object_transform == 6);
        CHECK(*member_function_transform == 12);
        CHECK(*member_function_chain == 10);

        auto move_only_member =
            []() noexcept {
                protocyte::Optional<MoveOnlyMemberProbe> out {};
                (void) out.emplace(43);
                return out;
            }()
                .transform(&MoveOnlyMemberProbe::child);
        REQUIRE(move_only_member);
        CHECK(move_only_member->value == 43);
    }
}

TEST_CASE("Result special members and payload propagation stay correct", "[smoke][runtime][result]") {
    static_assert(requires { protocyte::Result<int> {}; });
    static_assert(!std::is_constructible_v<protocyte::Result<bool>, protocyte::Result<int>>);
    static_assert(requires { protocyte::Result<long, protocyte::u64> {protocyte::Result<int, protocyte::u32> {7}}; });
    static_assert(requires {
        protocyte::Result<void, protocyte::u64> {
            protocyte::Result<void, protocyte::u32> {protocyte::unexpected(protocyte::u32 {3u})}};
    });

    SECTION("Result<T, E> preserves the active value or error across copy and move operations") {
        using TrackedResult = protocyte::Result<TrackedPayload, TrackedPayload>;

        TrackedPayload::reset();
        TrackedResult value_source {TrackedPayload {7}};
        TrackedPayload::reset();
        TrackedResult value_copy {value_source};
        REQUIRE(value_copy);
        CHECK(value_copy->value == 7);
        CHECK(TrackedPayload::copies > 0);

        TrackedPayload::reset();
        TrackedResult value_move_source {TrackedPayload {11}};
        TrackedPayload::reset();
        TrackedResult value_move {protocyte::move(value_move_source)};
        REQUIRE(value_move);
        CHECK(value_move->value == 11);
        CHECK(TrackedPayload::moves > 0);

        TrackedPayload::reset();
        TrackedResult value_copy_assign_target {TrackedPayload {1}};
        value_copy_assign_target = value_copy;
        REQUIRE(value_copy_assign_target);
        CHECK(value_copy_assign_target->value == 7);
        CHECK(TrackedPayload::copies > 0);

        TrackedPayload::reset();
        TrackedResult value_move_assign_target {TrackedPayload {2}};
        value_move_assign_target = protocyte::move(value_move);
        REQUIRE(value_move_assign_target);
        CHECK(value_move_assign_target->value == 11);
        CHECK(TrackedPayload::moves > 0);

        TrackedPayload::reset();
        TrackedResult error_source {protocyte::unexpected(TrackedPayload {17})};
        TrackedPayload::reset();
        TrackedResult error_copy {error_source};
        REQUIRE_FALSE(error_copy);
        CHECK(error_copy.error().value == 17);
        CHECK(TrackedPayload::copies > 0);

        TrackedPayload::reset();
        TrackedResult error_move_source {protocyte::unexpected(TrackedPayload {23})};
        TrackedPayload::reset();
        TrackedResult error_move {protocyte::move(error_move_source)};
        REQUIRE_FALSE(error_move);
        CHECK(error_move.error().value == 23);
        CHECK(TrackedPayload::moves > 0);

        TrackedPayload::reset();
        TrackedResult error_copy_assign_target {TrackedPayload {5}};
        error_copy_assign_target = error_copy;
        REQUIRE_FALSE(error_copy_assign_target);
        CHECK(error_copy_assign_target.error().value == 17);
        CHECK(TrackedPayload::copies > 0);

        TrackedPayload::reset();
        TrackedResult error_move_assign_target {TrackedPayload {6}};
        error_move_assign_target = protocyte::move(error_move);
        REQUIRE_FALSE(error_move_assign_target);
        CHECK(error_move_assign_target.error().value == 23);
        CHECK(TrackedPayload::moves > 0);

        auto &same_value_copy_assign_target = value_copy_assign_target;
        value_copy_assign_target = same_value_copy_assign_target;
        REQUIRE(value_copy_assign_target);
        CHECK(value_copy_assign_target->value == 7);

        auto &same_error_copy_assign_target = error_copy_assign_target;
        error_copy_assign_target = same_error_copy_assign_target;
        REQUIRE_FALSE(error_copy_assign_target);
        CHECK(error_copy_assign_target.error().value == 17);
    }

    SECTION("Result<void, E> preserves success and error state across copy and move operations") {
        using VoidTrackedResult = protocyte::Result<void, TrackedPayload>;

        VoidTrackedResult ok {};
        VoidTrackedResult ok_copy {ok};
        REQUIRE(ok_copy);

        VoidTrackedResult ok_move_source {};
        VoidTrackedResult ok_move {protocyte::move(ok_move_source)};
        REQUIRE(ok_move);

        VoidTrackedResult ok_copy_assign_target {};
        ok_copy_assign_target = ok_copy;
        REQUIRE(ok_copy_assign_target);

        VoidTrackedResult ok_move_assign_target {};
        ok_move_assign_target = protocyte::move(ok_move);
        REQUIRE(ok_move_assign_target);

        TrackedPayload::reset();
        VoidTrackedResult error_source {protocyte::unexpected(TrackedPayload {31})};
        TrackedPayload::reset();
        VoidTrackedResult error_copy {error_source};
        REQUIRE_FALSE(error_copy);
        CHECK(error_copy.error().value == 31);
        CHECK(TrackedPayload::copies > 0);

        TrackedPayload::reset();
        VoidTrackedResult error_move_source {protocyte::unexpected(TrackedPayload {37})};
        TrackedPayload::reset();
        VoidTrackedResult error_move {protocyte::move(error_move_source)};
        REQUIRE_FALSE(error_move);
        CHECK(error_move.error().value == 37);
        CHECK(TrackedPayload::moves > 0);

        TrackedPayload::reset();
        VoidTrackedResult error_copy_assign_target {};
        error_copy_assign_target = error_copy;
        REQUIRE_FALSE(error_copy_assign_target);
        CHECK(error_copy_assign_target.error().value == 31);
        CHECK(TrackedPayload::copies > 0);

        TrackedPayload::reset();
        VoidTrackedResult error_move_assign_target {};
        error_move_assign_target = protocyte::move(error_move);
        REQUIRE_FALSE(error_move_assign_target);
        CHECK(error_move_assign_target.error().value == 37);
        CHECK(TrackedPayload::moves > 0);

        auto &same_ok_copy_assign_target = ok_copy_assign_target;
        ok_copy_assign_target = same_ok_copy_assign_target;
        REQUIRE(ok_copy_assign_target);

        auto &same_void_error_copy_assign_target = error_copy_assign_target;
        error_copy_assign_target = same_void_error_copy_assign_target;
        REQUIRE_FALSE(error_copy_assign_target);
        CHECK(error_copy_assign_target.error().value == 31);
    }

    SECTION("Result accepts converted unexpected payloads for value and void specializations") {
        const protocyte::Result<int, protocyte::u64> converted_value_error {
            protocyte::unexpected(protocyte::u32 {19u})};
        REQUIRE_FALSE(converted_value_error);
        CHECK(converted_value_error.error() == 19u);

        const protocyte::Result<void, protocyte::u64> converted_status_error {
            protocyte::unexpected(protocyte::u32 {23u})};
        REQUIRE_FALSE(converted_status_error);
        CHECK(converted_status_error.error() == 23u);
    }

    SECTION("Result converts across compatible Result specializations") {
        const protocyte::Result<int, protocyte::u32> value_source {41};
        const protocyte::Result<long, protocyte::u64> converted_value {value_source};
        REQUIRE(converted_value);
        CHECK(*converted_value == 41);

        const protocyte::Result<int, protocyte::u32> error_source {protocyte::unexpected(protocyte::u32 {43u})};
        const protocyte::Result<long, protocyte::u64> converted_error {error_source};
        REQUIRE_FALSE(converted_error);
        CHECK(converted_error.error() == 43u);

        protocyte::Result<long, protocyte::u64> assigned_value {0};
        assigned_value = value_source;
        REQUIRE(assigned_value);
        CHECK(*assigned_value == 41);

        protocyte::Result<long, protocyte::u64> assigned_error {0};
        assigned_error = error_source;
        REQUIRE_FALSE(assigned_error);
        CHECK(assigned_error.error() == 43u);

        const protocyte::Result<void, protocyte::u32> void_ok_source {};
        const protocyte::Result<void, protocyte::u64> converted_void_ok {void_ok_source};
        REQUIRE(converted_void_ok);

        const protocyte::Result<void, protocyte::u32> void_error_source {protocyte::unexpected(protocyte::u32 {47u})};
        const protocyte::Result<void, protocyte::u64> converted_void_error {void_error_source};
        REQUIRE_FALSE(converted_void_error);
        CHECK(converted_void_error.error() == 47u);

        protocyte::Result<void, protocyte::u64> assigned_void_ok {protocyte::unexpected(protocyte::u64 {1u})};
        assigned_void_ok = void_ok_source;
        REQUIRE(assigned_void_ok);

        protocyte::Result<void, protocyte::u64> assigned_void_error {};
        assigned_void_error = void_error_source;
        REQUIRE_FALSE(assigned_void_error);
        CHECK(assigned_void_error.error() == 47u);
    }

    SECTION("Result preserves the original error payload when the success callback is skipped") {
        const auto original =
            protocyte::Result<int> {protocyte::unexpected(protocyte::ErrorCode::invalid_argument, 17u, 5u)};

        const auto transformed = original.transform([](const int) noexcept { return 99; });
        require_failure(transformed, protocyte::ErrorCode::invalid_argument);
        CHECK(transformed.error().offset == 17u);
        CHECK(transformed.error().field_number == 5u);

        const auto chained = original.and_then([](const int) noexcept -> protocyte::Result<int> { return 99; });
        require_failure(chained, protocyte::ErrorCode::invalid_argument);
        CHECK(chained.error().offset == 17u);
        CHECK(chained.error().field_number == 5u);

        const auto status = original.status();
        require_failure(status, protocyte::ErrorCode::invalid_argument);
        CHECK(status.error().offset == 17u);
        CHECK(status.error().field_number == 5u);

        const auto failed_status = protocyte::Status {protocyte::unexpected(protocyte::ErrorCode::count_limit, 9u, 4u)};
        const auto transformed_status = failed_status.transform([]() noexcept { return 123; });
        require_failure(transformed_status, protocyte::ErrorCode::count_limit);
        CHECK(transformed_status.error().offset == 9u);
        CHECK(transformed_status.error().field_number == 4u);

        const auto chained_status = failed_status.and_then([]() noexcept -> protocyte::Result<int> { return 123; });
        require_failure(chained_status, protocyte::ErrorCode::count_limit);
        CHECK(chained_status.error().offset == 9u);
        CHECK(chained_status.error().field_number == 4u);
    }
}

TEST_CASE("runtime limits are enforced for mutation and parsing", "[smoke][runtime][limits]") {
    SECTION("string assignment respects max_string_bytes") {
        auto ctx = make_context();
        ctx.limits.max_string_bytes = 3u;

        Message message(ctx);
        require_failure(message.set_f_string(view_of(string_bytes)), protocyte::ErrorCode::size_limit);

        Config::Bytes bytes(&ctx);
        require_failure(bytes.assign(view_of(bytes_data)), protocyte::ErrorCode::size_limit);
    }

    SECTION("mutable fixed bytes respect max_string_bytes") {
        auto ctx = make_context();
        ctx.limits.max_string_bytes = sizeof(sha256_bytes) - 1u;

        Message message(ctx);
        const auto view = message.mutable_sha256();
        CHECK(view.data == nullptr);
        CHECK(view.size == 0u);
    }

    SECTION("nested message fields respect max_message_bytes") {
        auto build_ctx = make_context();
        Nested1 nested(build_ctx);
        populate_nested1(nested, view_of(nested_name), 25);

        auto nested_size = nested.encoded_size();
        require_success(nested_size);
        REQUIRE(*nested_size > 1u);

        uint8_t encoded[256] = {};
        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::nested1),
                                             protocyte::WireType::LEN));
        require_success(protocyte::write_varint(writer, static_cast<uint64_t>(*nested_size)));
        require_success(nested.serialize(writer));

        auto parse_ctx = make_context();
        parse_ctx.limits.max_message_bytes = *nested_size - 1u;

        Message parsed(parse_ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_failure(parsed.merge_from(reader), protocyte::ErrorCode::size_limit);
        CHECK(parse_ctx.recursion_depth == 0u);
    }

    SECTION("map entries respect max_message_bytes") {
        uint8_t encoded[128] = {};
        protocyte::SliceWriter writer(encoded, sizeof(encoded));

        uint8_t entry[64] = {};
        protocyte::SliceWriter entry_writer(entry, sizeof(entry));
        require_success(protocyte::write_bool_field(entry_writer, 1u, true));
        require_success(protocyte::write_bytes_field(entry_writer, 2u, view_of(bool_bytes)));

        require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::map_bool_bytes),
                                             protocyte::WireType::LEN));
        require_success(protocyte::write_varint(writer, static_cast<uint64_t>(entry_writer.position())));
        require_success(writer.write(entry, entry_writer.position()));

        auto parse_ctx = make_context();
        parse_ctx.limits.max_message_bytes = 4u;

        Message parsed(parse_ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_failure(parsed.merge_from(reader), protocyte::ErrorCode::size_limit);
        CHECK(parse_ctx.recursion_depth == 0u);
    }

    SECTION("nested messages respect max_recursion_depth") {
        auto build_ctx = make_context();
        Nested1 nested(build_ctx);
        populate_nested1(nested, view_of(nested_name), 25);

        auto nested_size = nested.encoded_size();
        require_success(nested_size);

        uint8_t encoded[256] = {};
        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::nested1),
                                             protocyte::WireType::LEN));
        require_success(protocyte::write_varint(writer, static_cast<uint64_t>(*nested_size)));
        require_success(nested.serialize(writer));

        auto parse_ctx = make_context();
        parse_ctx.limits.max_recursion_depth = 1u;

        Message parsed(parse_ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_failure(parsed.merge_from(reader), protocyte::ErrorCode::recursion_limit);
        CHECK(parse_ctx.recursion_depth == 0u);
    }

    SECTION("group skipping respects max_recursion_depth") {
        auto ctx = make_context();
        ctx.limits.max_recursion_depth = 1u;

        constexpr uint8_t nested_groups[] = {0x0bu, 0x13u, 0x14u, 0x0cu};
        protocyte::SliceReader reader(nested_groups, sizeof(nested_groups));
        require_failure(protocyte::skip_field<Config>(ctx, reader, protocyte::WireType::SGROUP, 1u),
                        protocyte::ErrorCode::recursion_limit);
        CHECK(ctx.recursion_depth == 0u);
    }
}

TEST_CASE("Custom runtime config satisfies the explicit protocyte contract", "[smoke][runtime][custom-config]") {
    auto build_ctx = make_custom_context();
    CustomMessage message(build_ctx);

    require_success(message.mutable_r_double().push_back(12.5));
    require_success(message.mutable_r_double().push_back(13.5));

    auto nested = message.ensure_nested1();
    require_success(nested);
    require_success((*nested)->set_name(view_of(nested_name)));
    require_success((*nested)->set_id(77));

    auto inner = (*nested)->ensure_inner();
    require_success(inner);
    require_success((*inner)->set_description(view_of(nested_description)));
    require_success((*inner)->mutable_values().push_back(4.5f));
    require_success((*inner)->mutable_values().push_back(5.5f));
    require_success((*inner)->set_mode(InnerMode::C));

    auto encoded_size = message.encoded_size();
    require_success(encoded_size);

    uint8_t encoded[256] = {};
    protocyte::SliceWriter writer(encoded, sizeof(encoded));
    require_success(message.serialize(writer));
    require_success(protocyte::write_int32_field(writer, 99u, 1234));

    auto parse_ctx = make_custom_context();
    CustomMessage parsed(parse_ctx);
    protocyte::SliceReader reader(encoded, writer.position());
    require_success(parsed.merge_from(reader));
    REQUIRE(reader.eof());
    CHECK(parse_ctx.recursion_depth == 0u);

    const auto &doubles = parsed.r_double();
    REQUIRE(doubles.size() == 2u);
    CHECK(doubles[0] == 12.5);
    CHECK(doubles[1] == 13.5);

    REQUIRE(parsed.has_nested1());
    const CustomNested1 &parsed_nested = *parsed.nested1();
    CHECK(view_equal(parsed_nested.name(), view_of(nested_name)));
    CHECK(parsed_nested.id() == 77);
    REQUIRE(parsed_nested.has_inner());
    const CustomNested2 &parsed_inner = *parsed_nested.inner();
    CHECK(view_equal(parsed_inner.description(), view_of(nested_description)));
    REQUIRE(parsed_inner.values().size() == 2u);
    CHECK(parsed_inner.values()[0] == 4.5f);
    CHECK(parsed_inner.values()[1] == 5.5f);
    CHECK(parsed_inner.mode() == InnerMode::C);
}
