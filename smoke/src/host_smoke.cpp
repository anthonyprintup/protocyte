#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <string>
#include <string_view>

#include <catch2/catch_test_macros.hpp>

#include "compat.protocyte.hpp"
#include "compat_cases.hpp"
#include "example.protocyte.hpp"
#include "protocyte/runtime/runtime.hpp"

namespace {

    struct alignas(64) HostedOverAligned final {
        uint8_t bytes[64];
    };

    using Config = protocyte::DefaultConfig;
    using Message = test::ultimate::UltimateComplexMessage<>;
    using Nested1 = test::ultimate::UltimateComplexMessage_NestedLevel1<>;
    using Nested2 = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<>;
    using Deep = test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<>;
    using Cross = test::ultimate::CrossMessageConstants<>;
    using CrossNested = test::ultimate::CrossMessageConstants_Nested<>;
    using Color = test::ultimate::UltimateComplexMessage_Color;
    using InnerMode = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;
    using CompatMessage = protocyte_smoke::test::compat::EncodingMatrix<>;
    using CompatNested = protocyte_smoke::test::compat::EncodingMatrix_Inner<>;
    using CompatMode = protocyte_smoke::test::compat::EncodingMatrix_Mode;

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

    constexpr uint8_t kString[] = {'s', 'm', 'o', 'k', 'e'};
    constexpr uint8_t kBytes[] = {0x00u, 0x01u, 0x7fu, 0x80u, 0xffu};
    constexpr uint8_t kNestedName[] = {'n', 'e', 's', 't', 'e', 'd'};
    constexpr uint8_t kNestedDescription[] = {'i', 'n', 'n', 'e', 'r'};
    constexpr uint8_t kOneofString[] = {'o', 'n', 'e', 'o', 'f', '-', 's', 't', 'r'};
    constexpr uint8_t kOneofBytes[] = {0xdeu, 0xadu, 0xbeu, 0xefu};
    constexpr uint8_t kMapKey[] = {'m', 'a', 'p', '-', 'k', 'e', 'y'};
    constexpr uint8_t kMapValue[] = {'m', 'a', 'p', '-', 'v', 'a', 'l'};
    constexpr uint8_t kBoolBytes[] = {'b', 'o', 'o', 'l'};
    constexpr uint8_t kVeryNestedKey[] = {'v', 'e', 'r', 'y'};
    constexpr uint8_t kRecursiveString[] = {'r', 'e', 'c'};
    constexpr uint8_t kOptionalString[] = {'o', 'p', 't'};
    constexpr uint8_t kExtreme[] = {'e', 'x', 't', 'r', 'e', 'm', 'e'};
    constexpr uint8_t kDeepText[] = {'d', 'e', 'e', 'p'};
    constexpr uint8_t kWeirdValue[] = {'w', 'e', 'i', 'r', 'd'};
    constexpr uint8_t kByteArray[] = {0xa1u, 0xb2u, 0xc3u, 0xd4u};
    constexpr uint8_t kFloatExprArray[] = {0x91u, 0x92u};
    constexpr uint8_t kExternalBytes[] = {0x11u, 0x22u, 0x33u, 0x44u, 0x55u, 0x66u};
    constexpr uint8_t kNestedBytes[] = {0x80u, 0x81u, 0x82u, 0x83u, 0x84u, 0x85u, 0x86u, 0x87u};
    constexpr uint8_t kLargeByteArray[] = {0x01u, 0x02u, 0x03u, 0x04u, 0x05u};
    constexpr uint8_t kAlternateByteArray[] = {0x55u, 0x66u, 0x77u, 0x88u};
    constexpr uint8_t kSha256[] = {
        0x10u, 0x21u, 0x32u, 0x43u, 0x54u, 0x65u, 0x76u, 0x87u, 0x98u, 0xa9u, 0xbau, 0xcbu, 0xdcu, 0xedu, 0xfeu, 0x0fu,
        0x1eu, 0x2du, 0x3cu, 0x4bu, 0x5au, 0x69u, 0x78u, 0x87u, 0x96u, 0xa5u, 0xb4u, 0xc3u, 0xd2u, 0xe1u, 0xf0u, 0x0fu,
    };
    constexpr int32_t kIntegerArray[] = {101, 102, 103, 104, 105, 106, 107, 108};
    constexpr int32_t kMirroredValues[] = {501, 502, 503, 504, 505, 506, 507, 508, 509, 510};
    constexpr uint32_t kFixedIntegerArray[] = {901u, 902u, 903u};
    constexpr uint8_t kShortSha256[31] = {};

    static_assert(sizeof(kByteArray) == test::ultimate::BYTE_ARRAY_CAP);
    static_assert(sizeof(kFloatExprArray) == Message::FLOATISH_BOUND);
    static_assert(sizeof(kExternalBytes) == test::ultimate::BYTE_ARRAY_CAP + 2u);
    static_assert(sizeof(kNestedBytes) == CrossNested::EXTERNAL_CAP);
    static_assert(sizeof(kIntegerArray) / sizeof(kIntegerArray[0]) == Message::INTEGER_ARRAY_CAP);
    static_assert(sizeof(kMirroredValues) / sizeof(kMirroredValues[0]) == Cross::ROOT_MIRROR);
    static_assert(sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]) == Message::FIXED_INTEGER_ARRAY_CAP);

    void *smoke_allocate(void *, size_t size, size_t) noexcept { return malloc(size); }

    void smoke_deallocate(void *, void *ptr, size_t, size_t) noexcept { free(ptr); }

    Config::Context make_context() noexcept {
        return Config::Context {
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

    std::string hex_of(std::string_view bytes) {
        static constexpr char kHex[] = "0123456789abcdef";
        std::string out;
        out.reserve(bytes.size() * 2u);
        for (const unsigned char value : bytes) {
            out.push_back(kHex[value >> 4u]);
            out.push_back(kHex[value & 0x0fu]);
        }
        return out;
    }

    template<class TStatusLike> void require_success(const TStatusLike &status_like) {
        const auto error = status_like.error();
        CAPTURE(static_cast<uint32_t>(error.code), error.offset, error.field_number);
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

    std::string serialize_compat(const CompatMessage &message) {
        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        std::string out(encoded_size.value(), '\0');
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

    void populate_required_fixed_array(Message &message) {
        for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
            require_success(message.mutable_fixed_integer_array().push_back(kFixedIntegerArray[i]));
        }
    }

    bool nested2_matches(const Nested2 &value, protocyte::ByteView description, float first, float second,
                         InnerMode mode) noexcept {
        const auto &values = value.values();
        return view_equal(value.description(), description) && values.size() == 2u && values[0] == first &&
               values[1] == second && value.mode() == mode;
    }

    void check_nested2(const Nested2 &value, protocyte::ByteView description, float first, float second,
                       InnerMode mode) {
        const auto &values = value.values();
        CHECK(view_equal(value.description(), description));
        REQUIRE(values.size() == 2u);
        CHECK(values[0] == first);
        CHECK(values[1] == second);
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
               nested2_matches(*value.inner(), view_of(kNestedDescription), 1.5f, 2.5f, InnerMode::B);
    }

    void check_nested1(const Nested1 &value, protocyte::ByteView name, int32_t id) {
        CHECK(view_equal(value.name(), name));
        CHECK(value.id() == id);
        REQUIRE(value.has_inner());
        check_nested2(*value.inner(), view_of(kNestedDescription), 1.5f, 2.5f, InnerMode::B);
    }

    void populate_nested1(Nested1 &value, protocyte::ByteView name, int32_t id) {
        require_success(value.set_name(name));
        require_success(value.set_id(id));
        auto inner = value.ensure_inner();
        require_success(inner);
        populate_nested2(inner.value().get(), view_of(kNestedDescription), 1.5f, 2.5f, InnerMode::B);
        check_nested1(value, name, id);
    }

    void insert_map_str_int32(Message &message, Config::Context &ctx) {
        Config::String key(&ctx);
        assign_string(key, view_of(kMapKey));
        require_success(message.mutable_map_str_int32().insert_or_assign(protocyte::move(key), 301));
    }

    void insert_map_int32_str(Message &message, Config::Context &ctx) {
        Config::String value(&ctx);
        assign_string(value, view_of(kMapValue));
        require_success(message.mutable_map_int32_str().insert_or_assign(302, protocyte::move(value)));
    }

    void insert_map_bool_bytes(Message &message, Config::Context &ctx) {
        Config::Bytes value(&ctx);
        assign_bytes(value, view_of(kBoolBytes));
        require_success(message.mutable_map_bool_bytes().insert_or_assign(true, protocyte::move(value)));
    }

    void insert_map_uint64_msg(Message &message, Config::Context &ctx) {
        Nested1 value(ctx);
        populate_nested1(value, view_of(kNestedName), 330);
        require_success(message.mutable_map_uint64_msg().insert_or_assign(3300u, protocyte::move(value)));
    }

    void insert_very_nested_map(Message &message, Config::Context &ctx) {
        Config::String key(&ctx);
        assign_string(key, view_of(kVeryNestedKey));
        Nested2 value(ctx);
        populate_nested2(value, view_of(kNestedDescription), 3.5f, 4.5f, InnerMode::C);
        require_success(
            message.mutable_very_nested_map().insert_or_assign(protocyte::move(key), protocyte::move(value)));
    }

    void populate_deep(Deep &value, Config::Context &ctx) {
        require_success(value.set_extreme(view_of(kExtreme)));
        Config::String weird(&ctx);
        assign_string(weird, view_of(kWeirdValue));
        require_success(value.mutable_weird_map().insert_or_assign(7, protocyte::move(weird)));
        require_success(value.set_text(view_of(kDeepText)));
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
        require_success(message.set_f_string(view_of(kString)));
        require_success(message.set_f_bytes(view_of(kBytes)));
        require_success(message.mutable_r_int32_unpacked().push_back(21));
        require_success(message.mutable_r_int32_unpacked().push_back(22));
        require_success(message.mutable_r_int32_packed().push_back(23));
        require_success(message.mutable_r_int32_packed().push_back(24));
        require_success(message.mutable_r_double().push_back(23.5));
        require_success(message.mutable_r_double().push_back(24.5));
        require_success(message.set_color(Color::GREEN));

        auto nested = message.ensure_nested1();
        require_success(nested);
        populate_nested1(nested.value().get(), view_of(kNestedName), 25);

        require_success(message.set_oneof_bytes(view_of(kOneofBytes)));
        insert_map_str_int32(message, ctx);
        insert_map_int32_str(message, ctx);
        insert_map_bool_bytes(message, ctx);
        insert_map_uint64_msg(message, ctx);
        insert_very_nested_map(message, ctx);

        auto recursive = message.ensure_recursive_self();
        require_success(recursive);
        require_success(recursive.value().get().set_f_string(view_of(kRecursiveString)));
        require_success(recursive.value().get().set_f_int32(350));
        populate_required_fixed_array(recursive.value().get());

        auto nested_item = message.mutable_lots_of_nested().emplace_back(ctx);
        require_success(nested_item);
        populate_nested2(nested_item.value().get(), view_of(kNestedDescription), 36.5f, 37.5f, InnerMode::A);

        require_success(message.mutable_colors().push_back(static_cast<int32_t>(Color::RED)));
        require_success(message.mutable_colors().push_back(static_cast<int32_t>(Color::BLUE)));
        require_success(message.set_opt_int32(38));
        require_success(message.set_opt_string(view_of(kOptionalString)));
        require_success(message.set_sha256(view_of(kSha256)));
        require_success(message.set_byte_array(view_of(kByteArray)));
        require_success(message.set_float_expr_array(view_of(kFloatExprArray)));

        for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
            require_success(message.mutable_integer_array().push_back(kIntegerArray[i]));
        }
        for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
            require_success(message.mutable_fixed_integer_array().push_back(kFixedIntegerArray[i]));
        }

        auto deep = message.ensure_extreme_nesting();
        require_success(deep);
        populate_deep(deep.value().get(), ctx);
    }

    void check_maps(const Message &message) {
        bool saw_str_int32 = false;
        require_success(
            message.map_str_int32().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (view_equal(key.view(), view_of(kMapKey)) && value == 301) {
                    saw_str_int32 = true;
                }
                return protocyte::Status::ok();
            }));
        CHECK(saw_str_int32);
        CHECK(message.map_str_int32().size() == 1u);

        bool saw_int32_str = false;
        require_success(
            message.map_int32_str().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (key == 302 && view_equal(value.view(), view_of(kMapValue))) {
                    saw_int32_str = true;
                }
                return protocyte::Status::ok();
            }));
        CHECK(saw_int32_str);
        CHECK(message.map_int32_str().size() == 1u);

        bool saw_bool_bytes = false;
        require_success(
            message.map_bool_bytes().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (key && view_equal(value.view(), view_of(kBoolBytes))) {
                    saw_bool_bytes = true;
                }
                return protocyte::Status::ok();
            }));
        CHECK(saw_bool_bytes);
        CHECK(message.map_bool_bytes().size() == 1u);

        bool saw_uint64_msg = false;
        require_success(
            message.map_uint64_msg().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (key == 3300u && nested1_matches(value, view_of(kNestedName), 330)) {
                    saw_uint64_msg = true;
                }
                return protocyte::Status::ok();
            }));
        CHECK(saw_uint64_msg);
        CHECK(message.map_uint64_msg().size() == 1u);

        bool saw_very_nested = false;
        require_success(
            message.very_nested_map().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (view_equal(key.view(), view_of(kVeryNestedKey)) &&
                    nested2_matches(value, view_of(kNestedDescription), 3.5f, 4.5f, InnerMode::C)) {
                    saw_very_nested = true;
                }
                return protocyte::Status::ok();
            }));
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
        CHECK(view_equal(parsed.f_string(), view_of(kString)));
        CHECK(view_equal(parsed.f_bytes(), view_of(kBytes)));

        const auto &unpacked = parsed.r_int32_unpacked();
        REQUIRE(unpacked.size() == 2u);
        CHECK(unpacked[0] == 21);
        CHECK(unpacked[1] == 22);

        const auto &packed = parsed.r_int32_packed();
        REQUIRE(packed.size() == 2u);
        CHECK(packed[0] == 23);
        CHECK(packed[1] == 24);

        const auto &doubles = parsed.r_double();
        REQUIRE(doubles.size() == 2u);
        CHECK(doubles[0] == 23.5);
        CHECK(doubles[1] == 24.5);

        CHECK(parsed.color() == Color::GREEN);

        REQUIRE(parsed.has_nested1());
        check_nested1(*parsed.nested1(), view_of(kNestedName), 25);

        REQUIRE(parsed.has_oneof_bytes());
        CHECK(parsed.special_oneof_case() == Message::Special_oneofCase::oneof_bytes);
        CHECK(view_equal(parsed.oneof_bytes(), view_of(kOneofBytes)));

        check_maps(parsed);

        REQUIRE(parsed.has_recursive_self());
        CHECK(parsed.recursive_self()->f_int32() == 350);
        CHECK(view_equal(parsed.recursive_self()->f_string(), view_of(kRecursiveString)));

        const auto &nested_items = parsed.lots_of_nested();
        REQUIRE(nested_items.size() == 1u);
        check_nested2(nested_items[0], view_of(kNestedDescription), 36.5f, 37.5f, InnerMode::A);

        const auto &colors = parsed.colors();
        REQUIRE(colors.size() == 2u);
        CHECK(colors[0] == static_cast<int32_t>(Color::RED));
        CHECK(colors[1] == static_cast<int32_t>(Color::BLUE));

        REQUIRE(parsed.has_opt_int32());
        CHECK(parsed.opt_int32() == 38);
        REQUIRE(parsed.has_opt_string());
        CHECK(view_equal(parsed.opt_string(), view_of(kOptionalString)));

        CHECK(view_equal(parsed.sha256(), view_of(kSha256)));
        CHECK(view_equal(parsed.byte_array(), view_of(kByteArray)));
        CHECK(parsed.byte_array_size() == test::ultimate::BYTE_ARRAY_CAP);
        CHECK(view_equal(parsed.float_expr_array(), view_of(kFloatExprArray)));
        CHECK(parsed.float_expr_array_size() == Message::FLOATISH_BOUND);

        const auto &integer_array = parsed.integer_array();
        REQUIRE(integer_array.size() == Message::INTEGER_ARRAY_CAP);
        for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
            CHECK(integer_array[i] == kIntegerArray[i]);
        }

        const auto &fixed_integer_array = parsed.fixed_integer_array();
        REQUIRE(fixed_integer_array.size() == Message::FIXED_INTEGER_ARRAY_CAP);
        for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
            CHECK(fixed_integer_array[i] == kFixedIntegerArray[i]);
        }

        REQUIRE(parsed.has_extreme_nesting());
        const Deep &deep = *parsed.extreme_nesting();
        CHECK(view_equal(deep.extreme(), view_of(kExtreme)));
        REQUIRE(deep.has_text());
        CHECK(deep.deep_oneof_case() == Deep::Deep_oneofCase::text);
        CHECK(view_equal(deep.text(), view_of(kDeepText)));

        bool saw_weird = false;
        require_success(
            deep.weird_map().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (key == 7 && view_equal(value.view(), view_of(kWeirdValue))) {
                    saw_weird = true;
                }
                return protocyte::Status::ok();
            }));
        CHECK(saw_weird);
        CHECK(deep.weird_map().size() == 1u);
    }

    void round_trip_and_check(Message &message, Config::Context &ctx) {
        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        uint8_t encoded[4096] = {};
        REQUIRE(encoded_size.value() <= sizeof(encoded));

        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(message.serialize(writer));
        REQUIRE(writer.position() == encoded_size.value());

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
        check_message(cloned.value());

        Message moved(protocyte::move(parsed));
        check_message(moved);
    }

    void check_oneof_alternatives(Config::Context &ctx) {
        SECTION("string alternative round trips") {
            Message message(ctx);
            require_success(message.set_oneof_string(view_of(kOneofString)));
            populate_required_fixed_array(message);

            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_string());
            CHECK(view_equal(parsed.oneof_string(), view_of(kOneofString)));
        }

        SECTION("int32 alternative round trips") {
            Message message(ctx);
            require_success(message.set_oneof_int32(2700));
            populate_required_fixed_array(message);

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
            populate_nested1(oneof_msg.value().get(), view_of(kNestedName), 2800);
            populate_required_fixed_array(message);

            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_msg());
            check_nested1(*parsed.oneof_msg(), view_of(kNestedName), 2800);
        }

        SECTION("bytes alternative round trips") {
            Message message(ctx);
            require_success(message.set_oneof_bytes(view_of(kOneofBytes)));
            populate_required_fixed_array(message);

            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_bytes());
            CHECK(view_equal(parsed.oneof_bytes(), view_of(kOneofBytes)));
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
            require_success(first.set_oneof_string(view_of(kOneofString)));
            populate_required_fixed_array(first);
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
            require_success(first_oneof.value().get().set_name(view_of(kNestedName)));
            populate_required_fixed_array(first);
            require_success(first.set_oneof_bytes(view_of(kOneofBytes)));

            uint8_t encoded[512] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(first.serialize(writer));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_oneof_bytes());
            CHECK(parsed.special_oneof_case() == Message::Special_oneofCase::oneof_bytes);
            CHECK(view_equal(parsed.oneof_bytes(), view_of(kOneofBytes)));
        }

        SECTION("move construction preserves active bytes case") {
            Message source(ctx);
            require_success(source.set_oneof_bytes(view_of(kOneofBytes)));

            Message moved(protocyte::move(source));
            REQUIRE(moved.has_oneof_bytes());
            CHECK(view_equal(moved.oneof_bytes(), view_of(kOneofBytes)));
            CHECK(source.special_oneof_case() == Message::Special_oneofCase::none);
            CHECK(source.oneof_bytes().size == 0u);
        }

        SECTION("move assignment transfers active message case") {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(oneof_msg.value().get(), view_of(kNestedName), 2802);

            Message target(ctx);
            require_success(target.set_oneof_string(view_of(kOneofString)));
            target = protocyte::move(source);

            REQUIRE(target.has_oneof_msg());
            REQUIRE(target.oneof_msg() != nullptr);
            check_nested1(*target.oneof_msg(), view_of(kNestedName), 2802);
            CHECK(source.special_oneof_case() == Message::Special_oneofCase::none);
        }

        SECTION("copy_from preserves active oneof state") {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(oneof_msg.value().get(), view_of(kNestedName), 2802);

            Message target(ctx);
            require_success(target.set_oneof_string(view_of(kOneofString)));
            require_success(target.copy_from(source));

            REQUIRE(target.has_oneof_msg());
            REQUIRE(target.oneof_msg() != nullptr);
            check_nested1(*target.oneof_msg(), view_of(kNestedName), 2802);
            CHECK(target.special_oneof_case() == Message::Special_oneofCase::oneof_msg);
        }

        SECTION("clone preserves active oneof state") {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            require_success(oneof_msg);
            populate_nested1(oneof_msg.value().get(), view_of(kNestedName), 2802);

            auto cloned = source.clone();
            require_success(cloned);
            REQUIRE(cloned.value().has_oneof_msg());
            REQUIRE(cloned.value().oneof_msg() != nullptr);
            check_nested1(*cloned.value().oneof_msg(), view_of(kNestedName), 2802);
            CHECK(cloned.value().special_oneof_case() == Message::Special_oneofCase::oneof_msg);
        }
    }

    void check_fixed_array_presence(Config::Context &ctx) {
        SECTION("unset fixed bytes stay absent through round trip") {
            Message message(ctx);
            CHECK_FALSE(message.has_sha256());
            CHECK(message.sha256().size == 0u);
            populate_required_fixed_array(message);

            auto encoded_size = message.encoded_size();
            require_success(encoded_size);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));
            REQUIRE(writer.position() == encoded_size.value());

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
            for (size_t i = 0; i < sha256.size; ++i) { CHECK(sha256.data[i] == 0u); }

            message.clear_sha256();
            CHECK_FALSE(message.has_sha256());
            CHECK(message.sha256().size == 0u);
        }

        SECTION("explicit zero bytes stay present through round trip") {
            Message message(ctx);
            constexpr uint8_t kZeroSha256[32] = {};
            require_success(message.set_sha256(view_of(kZeroSha256)));
            REQUIRE(message.has_sha256());
            populate_required_fixed_array(message);

            auto encoded_size = message.encoded_size();
            require_success(encoded_size);
            REQUIRE(encoded_size.value() > 0u);

            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(message.serialize(writer));
            REQUIRE(writer.position() == encoded_size.value());

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_success(parsed.merge_from(reader));
            REQUIRE(parsed.has_sha256());
            CHECK(view_equal(parsed.sha256(), view_of(kZeroSha256)));
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
            for (size_t i = 0; i < message.byte_array().size; ++i) { CHECK(message.byte_array().data[i] == 0u); }

            message.clear_byte_array();
            CHECK(message.byte_array_size() == 0u);

            require_failure(message.resize_byte_array(test::ultimate::BYTE_ARRAY_CAP + 1u),
                            protocyte::ErrorCode::count_limit);
            require_failure(message.set_byte_array(view_of(kLargeByteArray)), protocyte::ErrorCode::count_limit);
            require_success(message.set_float_expr_array(view_of(kFloatExprArray)));
            require_failure(message.set_float_expr_array(view_of(kByteArray)), protocyte::ErrorCode::count_limit);
        }

        SECTION("bounded repeated arrays reject extra elements") {
            Message message(ctx);
            auto &integer_array = message.mutable_integer_array();
            for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
                require_success(integer_array.push_back(kIntegerArray[i]));
            }
            require_failure(integer_array.push_back(999), protocyte::ErrorCode::count_limit);
        }

        SECTION("copy_from self-assignment keeps bounded repeated arrays intact") {
            Message message(ctx);
            require_success(message.set_byte_array(view_of(kByteArray)));
            for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
                require_success(message.mutable_integer_array().push_back(kIntegerArray[i]));
            }
            for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
                require_success(message.mutable_fixed_integer_array().push_back(kFixedIntegerArray[i]));
            }

            require_success(message.copy_from(message));

            CHECK(view_equal(message.byte_array(), view_of(kByteArray)));
            CHECK(message.byte_array_size() == sizeof(kByteArray));
            for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
                CHECK(message.integer_array()[i] == kIntegerArray[i]);
            }
            for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
                CHECK(message.fixed_integer_array()[i] == kFixedIntegerArray[i]);
            }
        }

        SECTION("move assignment transfers bounded arrays") {
            Message source(ctx);
            require_success(source.set_byte_array(view_of(kByteArray)));
            for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
                require_success(source.mutable_integer_array().push_back(kIntegerArray[i]));
            }
            for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
                require_success(source.mutable_fixed_integer_array().push_back(kFixedIntegerArray[i]));
            }

            Message target(ctx);
            require_success(target.set_byte_array(view_of(kAlternateByteArray)));
            require_success(target.mutable_integer_array().push_back(999));
            require_success(target.mutable_fixed_integer_array().push_back(111u));
            target = protocyte::move(source);

            CHECK(view_equal(target.byte_array(), view_of(kByteArray)));
            CHECK(target.byte_array_size() == sizeof(kByteArray));
            const auto &target_integer_array = target.integer_array();
            REQUIRE(target_integer_array.size() == Message::INTEGER_ARRAY_CAP);
            for (size_t i = 0; i < sizeof(kIntegerArray) / sizeof(kIntegerArray[0]); ++i) {
                CHECK(target_integer_array[i] == kIntegerArray[i]);
            }
            const auto &target_fixed_integer_array = target.fixed_integer_array();
            REQUIRE(target_fixed_integer_array.size() == Message::FIXED_INTEGER_ARRAY_CAP);
            for (size_t i = 0; i < sizeof(kFixedIntegerArray) / sizeof(kFixedIntegerArray[0]); ++i) {
                CHECK(target_fixed_integer_array[i] == kFixedIntegerArray[i]);
            }
            CHECK(source.byte_array_size() == 0u);
            CHECK(source.integer_array().size() == 0u);
            CHECK(source.fixed_integer_array().size() == 0u);
        }

        SECTION("required fixed arrays must be fully populated before encoding") {
            Message message(ctx);
            auto &fixed_integer_array = message.mutable_fixed_integer_array();
            require_success(fixed_integer_array.push_back(kFixedIntegerArray[0]));
            require_success(fixed_integer_array.push_back(kFixedIntegerArray[1]));

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
            require_success(protocyte::write_varint(writer, sizeof(kShortSha256)));
            require_success(writer.write(kShortSha256, sizeof(kShortSha256)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_argument);
        }

        SECTION("oversized bounded byte arrays are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::byte_array),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, sizeof(kLargeByteArray)));
            require_success(writer.write(kLargeByteArray, sizeof(kLargeByteArray)));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::count_limit);
        }

        SECTION("oversized bounded oneof bytes are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(writer, static_cast<uint32_t>(Message::FieldNumber::oneof_bytes),
                                                 protocyte::WireType::LEN));
            require_success(protocyte::write_varint(writer, sizeof(kLargeByteArray)));
            require_success(writer.write(kLargeByteArray, sizeof(kLargeByteArray)));

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

        SECTION("partial required fixed arrays are rejected while parsing") {
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            require_success(protocyte::write_tag(
                writer, static_cast<uint32_t>(Message::FieldNumber::fixed_integer_array), protocyte::WireType::VARINT));
            require_success(protocyte::write_varint(writer, kFixedIntegerArray[0]));
            require_success(protocyte::write_tag(
                writer, static_cast<uint32_t>(Message::FieldNumber::fixed_integer_array), protocyte::WireType::VARINT));
            require_success(protocyte::write_varint(writer, kFixedIntegerArray[1]));

            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            require_failure(parsed.merge_from(reader), protocyte::ErrorCode::invalid_argument);
        }
    }

    void populate_cross_message(Cross &message) {
        require_success(message.set_external_bytes(view_of(kExternalBytes)));
        for (size_t i = 0; i < sizeof(kMirroredValues) / sizeof(kMirroredValues[0]); ++i) {
            require_success(message.mutable_mirrored_values().push_back(kMirroredValues[i]));
        }
        auto nested = message.ensure_nested();
        require_success(nested);
        require_success(nested.value().get().set_nested_bytes(view_of(kNestedBytes)));
    }

    void check_cross_message(const Cross &message) {
        CHECK(view_equal(message.external_bytes(), view_of(kExternalBytes)));
        CHECK(message.external_bytes_size() == sizeof(kExternalBytes));

        const auto &mirrored_values = message.mirrored_values();
        REQUIRE(mirrored_values.size() == Cross::ROOT_MIRROR);
        for (size_t i = 0; i < sizeof(kMirroredValues) / sizeof(kMirroredValues[0]); ++i) {
            CHECK(mirrored_values[i] == kMirroredValues[i]);
        }

        REQUIRE(message.has_nested());
        CHECK(view_equal(message.nested()->nested_bytes(), view_of(kNestedBytes)));
        CHECK(message.nested()->nested_bytes_size() == sizeof(kNestedBytes));
    }

    void round_trip_cross_message(Config::Context &ctx) {
        Cross message(ctx);
        populate_cross_message(message);

        auto encoded_size = message.encoded_size();
        require_success(encoded_size);

        uint8_t encoded[256] = {};
        REQUIRE(encoded_size.value() <= sizeof(encoded));

        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        require_success(message.serialize(writer));

        Cross parsed(ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        require_success(parsed.merge_from(reader));
        REQUIRE(reader.eof());
        check_cross_message(parsed);
    }

} // namespace

TEST_CASE("UltimateComplexMessage round-trips", "[smoke][roundtrip]") {
    auto ctx = make_context();
    auto created = Message::create(ctx);
    require_success(created);

    auto &message = created.value();
    populate_message(message, ctx);
    round_trip_and_check(message, ctx);
}

TEST_CASE("UltimateComplexMessage oneofs merge correctly", "[smoke][oneof]") {
    auto ctx = make_context();
    check_oneof_alternatives(ctx);
}

TEST_CASE("Fixed bytes preserve presence semantics", "[smoke][fixed]") {
    auto ctx = make_context();
    check_fixed_array_presence(ctx);
}

TEST_CASE("Array bounds are enforced", "[smoke][array]") {
    auto ctx = make_context();
    check_array_validation(ctx);
}

TEST_CASE("Cross-message constants resolve into arrays", "[smoke][constants]") {
    auto ctx = make_context();
    round_trip_cross_message(ctx);
}

TEST_CASE("Protocyte encoding matches protobuf runtime bytes", "[smoke][compat]") {
    auto ctx = make_context();

    SECTION("empty message") {
        CompatMessage protocyte_message(ctx);
        require_same_compat_bytes("empty", protocyte_message, compat_cases::kEmpty);
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

        require_same_compat_bytes("varint", protocyte_message, compat_cases::kVarint);
    }

    SECTION("fixed scalars") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_f_fixed32(0x11223344u));
        require_success(protocyte_message.set_f_fixed64(0x1122334455667788ull));
        require_success(protocyte_message.set_f_sfixed32(-1234567));
        require_success(protocyte_message.set_f_sfixed64(-1234567890123ll));
        require_success(protocyte_message.set_f_float(-0.0f));
        require_success(protocyte_message.set_f_double(123.5));

        require_same_compat_bytes("fixed", protocyte_message, compat_cases::kFixed);
    }

    SECTION("length delimited fields") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_f_string(view_of(kString)));
        require_success(protocyte_message.set_f_bytes(view_of(kBytes)));
        if (auto nested = protocyte_message.ensure_nested(); nested) {
            populate_compat_nested(nested.value().get(), 417, view_of(kNestedName));
        } else {
            require_success(nested);
        }

        require_same_compat_bytes("length-delimited", protocyte_message, compat_cases::kLengthDelimited);
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

        require_same_compat_bytes("repeated", protocyte_message, compat_cases::kRepeated);
    }

    SECTION("oneof string") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_oneof_string(view_of(kOneofString)));
        require_same_compat_bytes("oneof-string", protocyte_message, compat_cases::kOneofString);
    }

    SECTION("oneof int32") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_oneof_int32(-2701));
        require_same_compat_bytes("oneof-int32", protocyte_message, compat_cases::kOneofInt32);
    }

    SECTION("oneof nested") {
        CompatMessage protocyte_message(ctx);

        if (auto nested = protocyte_message.ensure_oneof_nested(); nested) {
            populate_compat_nested(nested.value().get(), 90210, view_of(kNestedDescription));
        } else {
            require_success(nested);
        }
        require_same_compat_bytes("oneof-nested", protocyte_message, compat_cases::kOneofNested);
    }

    SECTION("oneof bytes") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_oneof_bytes(view_of(kOneofBytes)));
        require_same_compat_bytes("oneof-bytes", protocyte_message, compat_cases::kOneofBytes);
    }

    SECTION("optional fields") {
        CompatMessage protocyte_message(ctx);

        require_success(protocyte_message.set_opt_int32(-99));
        require_success(protocyte_message.set_opt_string(view_of(kOptionalString)));
        require_same_compat_bytes("optional", protocyte_message, compat_cases::kOptional);
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

    constexpr uint32_t kLargeFieldNumber = 2048u;
    const auto single_tag_size = protocyte::varint_size((static_cast<protocyte::u64>(kLargeFieldNumber) << 3u) |
                                                        static_cast<protocyte::u64>(protocyte::WireType::VARINT));
    CHECK(protocyte::tag_size(kLargeFieldNumber, protocyte::WireType::VARINT) == single_tag_size);
    CHECK(protocyte::tag_size(kLargeFieldNumber, protocyte::WireType::SGROUP) == single_tag_size * 2u);
}
