#include <cstddef>
#include <cstdint>
#include <cstdlib>

#include "example.protocyte.hpp"
#include "protocyte/runtime/runtime.hpp"

namespace {

    using Config = protocyte::DefaultConfig;
    using Message = test::ultimate::UltimateComplexMessage<>;
    using Nested1 = test::ultimate::UltimateComplexMessage_NestedLevel1<>;
    using Nested2 = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<>;
    using Deep = test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<>;
    using Color = test::ultimate::UltimateComplexMessage_Color;
    using InnerMode = test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;

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
    constexpr uint8_t kSha256[] = {
        0x10u, 0x21u, 0x32u, 0x43u, 0x54u, 0x65u, 0x76u, 0x87u, 0x98u, 0xa9u, 0xbau, 0xcbu, 0xdcu, 0xedu, 0xfeu, 0x0fu,
        0x1eu, 0x2du, 0x3cu, 0x4bu, 0x5au, 0x69u, 0x78u, 0x87u, 0x96u, 0xa5u, 0xb4u, 0xc3u, 0xd2u, 0xe1u, 0xf0u, 0x0fu,
    };

    void *smoke_allocate(void *, size_t size, size_t) noexcept { return malloc(size); }

    void smoke_deallocate(void *, void *ptr, size_t, size_t) noexcept { free(ptr); }

    bool view_equal(protocyte::ByteView lhs, protocyte::ByteView rhs) noexcept {
        return protocyte::bytes_equal(lhs, rhs);
    }

    template<size_t N> protocyte::ByteView view_of(const uint8_t (&data)[N]) noexcept {
        return protocyte::ByteView {data, N};
    }

    int fail_if(bool failed, int code) noexcept { return failed ? code : 0; }

    protocyte::Status assign_string(Config::String &out, protocyte::ByteView view) noexcept { return out.assign(view); }

    protocyte::Status assign_bytes(Config::Bytes &out, protocyte::ByteView view) noexcept { return out.assign(view); }

    protocyte::Status populate_nested2(Nested2 &value, protocyte::ByteView description, float first, float second,
                                       InnerMode mode) noexcept {
        auto st = value.set_description(description);
        if (!st) {
            return st;
        }
        st = value.mutable_values().push_back(first);
        if (!st) {
            return st;
        }
        st = value.mutable_values().push_back(second);
        if (!st) {
            return st;
        }
        return value.set_mode(mode);
    }

    protocyte::Status populate_nested1(Nested1 &value, protocyte::ByteView name, int32_t id) noexcept {
        auto st = value.set_name(name);
        if (!st) {
            return st;
        }
        st = value.set_id(id);
        if (!st) {
            return st;
        }
        auto inner = value.ensure_inner();
        if (!inner) {
            return inner.status();
        }
        return populate_nested2(inner.value().get(), view_of(kNestedDescription), 1.5f, 2.5f, InnerMode::B);
    }

    bool check_nested2(const Nested2 &value, protocyte::ByteView description, float first, float second,
                       InnerMode mode) noexcept {
        const auto &values = value.values();
        return view_equal(value.description(), description) && values.size() == 2u && values[0] == first &&
               values[1] == second && value.mode() == mode;
    }

    bool check_nested1(const Nested1 &value, protocyte::ByteView name, int32_t id) noexcept {
        return view_equal(value.name(), name) && value.id() == id && value.has_inner() &&
               check_nested2(*value.inner(), view_of(kNestedDescription), 1.5f, 2.5f, InnerMode::B);
    }

    protocyte::Status insert_map_str_int32(Message &message, Config::Context &ctx) noexcept {
        Config::String key(&ctx);
        auto st = assign_string(key, view_of(kMapKey));
        if (!st) {
            return st;
        }
        return message.mutable_map_str_int32().insert_or_assign(protocyte::move(key), 301);
    }

    protocyte::Status insert_map_int32_str(Message &message, Config::Context &ctx) noexcept {
        Config::String value(&ctx);
        auto st = assign_string(value, view_of(kMapValue));
        if (!st) {
            return st;
        }
        return message.mutable_map_int32_str().insert_or_assign(302, protocyte::move(value));
    }

    protocyte::Status insert_map_bool_bytes(Message &message, Config::Context &ctx) noexcept {
        Config::Bytes value(&ctx);
        auto st = assign_bytes(value, view_of(kBoolBytes));
        if (!st) {
            return st;
        }
        return message.mutable_map_bool_bytes().insert_or_assign(true, protocyte::move(value));
    }

    protocyte::Status insert_map_uint64_msg(Message &message, Config::Context &ctx) noexcept {
        Nested1 value(ctx);
        auto st = populate_nested1(value, view_of(kNestedName), 330);
        if (!st) {
            return st;
        }
        return message.mutable_map_uint64_msg().insert_or_assign(3300u, protocyte::move(value));
    }

    protocyte::Status insert_very_nested_map(Message &message, Config::Context &ctx) noexcept {
        Config::String key(&ctx);
        auto st = assign_string(key, view_of(kVeryNestedKey));
        if (!st) {
            return st;
        }
        Nested2 value(ctx);
        st = populate_nested2(value, view_of(kNestedDescription), 3.5f, 4.5f, InnerMode::C);
        if (!st) {
            return st;
        }
        return message.mutable_very_nested_map().insert_or_assign(protocyte::move(key), protocyte::move(value));
    }

    protocyte::Status populate_deep(Deep &value, Config::Context &ctx) noexcept {
        auto st = value.set_extreme(view_of(kExtreme));
        if (!st) {
            return st;
        }
        Config::String weird(&ctx);
        st = assign_string(weird, view_of(kWeirdValue));
        if (!st) {
            return st;
        }
        st = value.mutable_weird_map().insert_or_assign(7, protocyte::move(weird));
        if (!st) {
            return st;
        }
        return value.set_text(view_of(kDeepText));
    }

    protocyte::Status populate_message(Message &message, Config::Context &ctx) noexcept {
        auto st = message.set_f_double(123.5);
        if (!st) {
            return st;
        }
        st = message.set_f_float(12.25f);
        if (!st) {
            return st;
        }
        st = message.set_f_int32(42);
        if (!st) {
            return st;
        }
        st = message.set_f_int64(42000000000ll);
        if (!st) {
            return st;
        }
        st = message.set_f_uint32(99u);
        if (!st) {
            return st;
        }
        st = message.set_f_uint64(99000000000ull);
        if (!st) {
            return st;
        }
        st = message.set_f_sint32(-17);
        if (!st) {
            return st;
        }
        st = message.set_f_sint64(-17000000000ll);
        if (!st) {
            return st;
        }
        st = message.set_f_fixed32(0x11223344u);
        if (!st) {
            return st;
        }
        st = message.set_f_fixed64(0x1122334455667788ull);
        if (!st) {
            return st;
        }
        st = message.set_f_sfixed32(-1234567);
        if (!st) {
            return st;
        }
        st = message.set_f_sfixed64(-1234567890123ll);
        if (!st) {
            return st;
        }
        st = message.set_f_bool(true);
        if (!st) {
            return st;
        }
        st = message.set_f_string(view_of(kString));
        if (!st) {
            return st;
        }
        st = message.set_f_bytes(view_of(kBytes));
        if (!st) {
            return st;
        }
        st = message.mutable_r_int32_unpacked().push_back(21);
        if (!st) {
            return st;
        }
        st = message.mutable_r_int32_unpacked().push_back(22);
        if (!st) {
            return st;
        }
        st = message.mutable_r_int32_packed().push_back(23);
        if (!st) {
            return st;
        }
        st = message.mutable_r_int32_packed().push_back(24);
        if (!st) {
            return st;
        }
        st = message.mutable_r_double().push_back(23.5);
        if (!st) {
            return st;
        }
        st = message.mutable_r_double().push_back(24.5);
        if (!st) {
            return st;
        }
        st = message.set_color(Color::GREEN);
        if (!st) {
            return st;
        }
        auto nested = message.ensure_nested1();
        if (!nested) {
            return nested.status();
        }
        st = populate_nested1(nested.value().get(), view_of(kNestedName), 25);
        if (!st) {
            return st;
        }
        st = message.set_oneof_bytes(view_of(kOneofBytes));
        if (!st) {
            return st;
        }
        st = insert_map_str_int32(message, ctx);
        if (!st) {
            return st;
        }
        st = insert_map_int32_str(message, ctx);
        if (!st) {
            return st;
        }
        st = insert_map_bool_bytes(message, ctx);
        if (!st) {
            return st;
        }
        st = insert_map_uint64_msg(message, ctx);
        if (!st) {
            return st;
        }
        st = insert_very_nested_map(message, ctx);
        if (!st) {
            return st;
        }
        auto recursive = message.ensure_recursive_self();
        if (!recursive) {
            return recursive.status();
        }
        st = recursive.value().get().set_f_string(view_of(kRecursiveString));
        if (!st) {
            return st;
        }
        st = recursive.value().get().set_f_int32(350);
        if (!st) {
            return st;
        }
        auto nested_item = message.mutable_lots_of_nested().emplace_back(ctx);
        if (!nested_item) {
            return nested_item.status();
        }
        st = populate_nested2(nested_item.value().get(), view_of(kNestedDescription), 36.5f, 37.5f, InnerMode::A);
        if (!st) {
            return st;
        }
        st = message.mutable_colors().push_back(static_cast<int32_t>(Color::RED));
        if (!st) {
            return st;
        }
        st = message.mutable_colors().push_back(static_cast<int32_t>(Color::BLUE));
        if (!st) {
            return st;
        }
        st = message.set_opt_int32(38);
        if (!st) {
            return st;
        }
        st = message.set_opt_string(view_of(kOptionalString));
        if (!st) {
            return st;
        }
        st = message.set_sha256(view_of(kSha256));
        if (!st) {
            return st;
        }
        auto deep = message.ensure_extreme_nesting();
        if (!deep) {
            return deep.status();
        }
        return populate_deep(deep.value().get(), ctx);
    }

    int check_maps(const Message &message) noexcept {
        bool saw_str_int32 = false;
        auto st =
            message.map_str_int32().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
                if (view_equal(key.view(), view_of(kMapKey)) && value == 301) {
                    saw_str_int32 = true;
                }
                return protocyte::Status::ok();
            });
        if (!st || !saw_str_int32 || message.map_str_int32().size() != 1u) {
            return 101;
        }

        bool saw_int32_str = false;
        st = message.map_int32_str().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
            if (key == 302 && view_equal(value.view(), view_of(kMapValue))) {
                saw_int32_str = true;
            }
            return protocyte::Status::ok();
        });
        if (!st || !saw_int32_str || message.map_int32_str().size() != 1u) {
            return 102;
        }

        bool saw_bool_bytes = false;
        st = message.map_bool_bytes().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
            if (key && view_equal(value.view(), view_of(kBoolBytes))) {
                saw_bool_bytes = true;
            }
            return protocyte::Status::ok();
        });
        if (!st || !saw_bool_bytes || message.map_bool_bytes().size() != 1u) {
            return 103;
        }

        bool saw_uint64_msg = false;
        st = message.map_uint64_msg().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
            if (key == 3300u && check_nested1(value, view_of(kNestedName), 330)) {
                saw_uint64_msg = true;
            }
            return protocyte::Status::ok();
        });
        if (!st || !saw_uint64_msg || message.map_uint64_msg().size() != 1u) {
            return 104;
        }

        bool saw_very_nested = false;
        st = message.very_nested_map().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
            if (view_equal(key.view(), view_of(kVeryNestedKey)) &&
                check_nested2(value, view_of(kNestedDescription), 3.5f, 4.5f, InnerMode::C)) {
                saw_very_nested = true;
            }
            return protocyte::Status::ok();
        });
        if (!st || !saw_very_nested || message.very_nested_map().size() != 1u) {
            return 105;
        }
        return 0;
    }

    int check_message(const Message &parsed) noexcept {
        if (fail_if(parsed.f_double() != 123.5 || parsed.f_float() != 12.25f || parsed.f_int32() != 42 ||
                        parsed.f_int64() != 42000000000ll || parsed.f_uint32() != 99u ||
                        parsed.f_uint64() != 99000000000ull || parsed.f_sint32() != -17 ||
                        parsed.f_sint64() != -17000000000ll || parsed.f_fixed32() != 0x11223344u ||
                        parsed.f_fixed64() != 0x1122334455667788ull || parsed.f_sfixed32() != -1234567 ||
                        parsed.f_sfixed64() != -1234567890123ll || !parsed.f_bool(),
                    20) != 0) {
            return 20;
        }
        if (!view_equal(parsed.f_string(), view_of(kString)) || !view_equal(parsed.f_bytes(), view_of(kBytes))) {
            return 21;
        }
        const auto &unpacked = parsed.r_int32_unpacked();
        const auto &packed = parsed.r_int32_packed();
        const auto &doubles = parsed.r_double();
        if (unpacked.size() != 2u || unpacked[0] != 21 || unpacked[1] != 22 || packed.size() != 2u || packed[0] != 23 ||
            packed[1] != 24 || doubles.size() != 2u || doubles[0] != 23.5 || doubles[1] != 24.5) {
            return 22;
        }
        if (parsed.color() != Color::GREEN) {
            return 23;
        }
        if (!parsed.has_nested1() || !check_nested1(*parsed.nested1(), view_of(kNestedName), 25)) {
            return 24;
        }
        if (!parsed.has_oneof_bytes() || parsed.special_oneof_case() != Message::Special_oneofCase::oneof_bytes ||
            !view_equal(parsed.oneof_bytes(), view_of(kOneofBytes))) {
            return 25;
        }
        const int map_check = check_maps(parsed);
        if (map_check != 0) {
            return map_check;
        }
        if (!parsed.has_recursive_self() || parsed.recursive_self()->f_int32() != 350 ||
            !view_equal(parsed.recursive_self()->f_string(), view_of(kRecursiveString))) {
            return 26;
        }
        const auto &nested_items = parsed.lots_of_nested();
        if (nested_items.size() != 1u ||
            !check_nested2(nested_items[0], view_of(kNestedDescription), 36.5f, 37.5f, InnerMode::A)) {
            return 27;
        }
        const auto &colors = parsed.colors();
        if (colors.size() != 2u || colors[0] != static_cast<int32_t>(Color::RED) ||
            colors[1] != static_cast<int32_t>(Color::BLUE)) {
            return 28;
        }
        if (!parsed.has_opt_int32() || parsed.opt_int32() != 38 || !parsed.has_opt_string() ||
            !view_equal(parsed.opt_string(), view_of(kOptionalString))) {
            return 29;
        }
        if (!parsed.has_sha256() || !view_equal(parsed.sha256(), view_of(kSha256))) {
            return 33;
        }
        if (!parsed.has_extreme_nesting()) {
            return 30;
        }
        const Deep &deep = *parsed.extreme_nesting();
        if (!view_equal(deep.extreme(), view_of(kExtreme)) || !deep.has_text() ||
            deep.deep_oneof_case() != Deep::Deep_oneofCase::text || !view_equal(deep.text(), view_of(kDeepText))) {
            return 31;
        }
        bool saw_weird = false;
        auto st = deep.weird_map().for_each([&](const auto &key, const auto &value) noexcept -> protocyte::Status {
            if (key == 7 && view_equal(value.view(), view_of(kWeirdValue))) {
                saw_weird = true;
            }
            return protocyte::Status::ok();
        });
        if (!st || !saw_weird || deep.weird_map().size() != 1u) {
            return 32;
        }
        return 0;
    }

    int round_trip_and_check(Message &message, Config::Context &ctx) noexcept {
        auto encoded_size = message.encoded_size();
        if (!encoded_size) {
            return 40;
        }
        uint8_t encoded[4096] = {};
        if (encoded_size.value() > sizeof(encoded)) {
            return 41;
        }
        protocyte::SliceWriter writer(encoded, sizeof(encoded));
        if (!message.serialize(writer)) {
            return 42;
        }
        if (writer.position() != encoded_size.value()) {
            return 43;
        }

        Message parsed(ctx);
        protocyte::SliceReader reader(encoded, writer.position());
        if (!parsed.merge_from(reader)) {
            return 44;
        }
        if (!reader.eof()) {
            return 45;
        }
        return check_message(parsed);
    }

    int check_oneof_alternatives(Config::Context &ctx) noexcept {
        {
            Message message(ctx);
            if (!message.set_oneof_string(view_of(kOneofString))) {
                return 50;
            }
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!message.serialize(writer)) {
                return 51;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_oneof_string() ||
                !view_equal(parsed.oneof_string(), view_of(kOneofString))) {
                return 52;
            }
        }
        {
            Message message(ctx);
            if (!message.set_oneof_int32(2700)) {
                return 53;
            }
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!message.serialize(writer)) {
                return 54;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_oneof_int32() || parsed.oneof_int32() != 2700) {
                return 55;
            }
        }
        {
            Message message(ctx);
            auto oneof_msg = message.ensure_oneof_msg();
            if (!oneof_msg) {
                return 56;
            }
            auto st = populate_nested1(oneof_msg.value().get(), view_of(kNestedName), 2800);
            if (!st) {
                return 57;
            }
            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!message.serialize(writer)) {
                return 58;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_oneof_msg() ||
                !check_nested1(*parsed.oneof_msg(), view_of(kNestedName), 2800)) {
                return 59;
            }
        }
        {
            Message message(ctx);
            if (!message.set_oneof_bytes(view_of(kOneofBytes))) {
                return 60;
            }
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!message.serialize(writer)) {
                return 61;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_oneof_bytes() ||
                !view_equal(parsed.oneof_bytes(), view_of(kOneofBytes))) {
                return 62;
            }
        }
        {
            Deep deep(ctx);
            if (!deep.set_val(4000)) {
                return 63;
            }
            uint8_t encoded[128] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!deep.serialize(writer)) {
                return 64;
            }
            Deep parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_val() || parsed.val() != 4000) {
                return 65;
            }
        }
        {
            Message first(ctx);
            if (!first.set_oneof_string(view_of(kOneofString))) {
                return 66;
            }
            Message second(ctx);
            if (!second.set_oneof_int32(2701)) {
                return 67;
            }
            uint8_t encoded[256] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!first.serialize(writer)) {
                return 68;
            }
            if (!second.serialize(writer)) {
                return 69;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_oneof_int32() ||
                parsed.special_oneof_case() != Message::Special_oneofCase::oneof_int32 ||
                parsed.oneof_int32() != 2701) {
                return 70;
            }
        }
        {
            Message first(ctx);
            auto first_oneof = first.ensure_oneof_msg();
            if (!first_oneof) {
                return 71;
            }
            if (const auto st = first_oneof.value().get().set_name(view_of(kNestedName)); !st) {
                return 72;
            }
            Message second(ctx);
            auto second_oneof = second.ensure_oneof_msg();
            if (!second_oneof) {
                return 73;
            }
            if (const auto st = second_oneof.value().get().set_id(2801); !st) {
                return 74;
            }
            auto inner = second_oneof.value().get().ensure_inner();
            if (!inner) {
                return 75;
            }
            if (const auto st =
                    populate_nested2(inner.value().get(), view_of(kNestedDescription), 9.5f, 10.5f, InnerMode::C);
                !st) {
                return 76;
            }
            uint8_t encoded[512] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!first.serialize(writer)) {
                return 77;
            }
            if (!second.serialize(writer)) {
                return 78;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_oneof_msg() || parsed.oneof_msg() == nullptr) {
                return 79;
            }
            if (!view_equal(parsed.oneof_msg()->name(), view_of(kNestedName)) || parsed.oneof_msg()->id() != 2801 ||
                !parsed.oneof_msg()->has_inner() ||
                !check_nested2(*parsed.oneof_msg()->inner(), view_of(kNestedDescription), 9.5f, 10.5f, InnerMode::C)) {
                return 80;
            }
        }
        {
            Message source(ctx);
            if (!source.set_oneof_bytes(view_of(kOneofBytes))) {
                return 81;
            }
            Message moved(protocyte::move(source));
            if (!moved.has_oneof_bytes() || !view_equal(moved.oneof_bytes(), view_of(kOneofBytes)) ||
                source.special_oneof_case() != Message::Special_oneofCase::none || source.oneof_bytes().size != 0u) {
                return 82;
            }
        }
        {
            Message source(ctx);
            auto oneof_msg = source.ensure_oneof_msg();
            if (!oneof_msg) {
                return 83;
            }
            auto st = populate_nested1(oneof_msg.value().get(), view_of(kNestedName), 2802);
            if (!st) {
                return 84;
            }
            Message target(ctx);
            if (!target.set_oneof_string(view_of(kOneofString))) {
                return 85;
            }
            target = protocyte::move(source);
            if (!target.has_oneof_msg() || target.oneof_msg() == nullptr ||
                !check_nested1(*target.oneof_msg(), view_of(kNestedName), 2802) ||
                source.special_oneof_case() != Message::Special_oneofCase::none) {
                return 86;
            }
        }
        return 0;
    }

    int check_fixed_size_presence(Config::Context &ctx) noexcept {
        {
            Message message(ctx);
            if (message.has_sha256() || message.sha256().size != 0u) {
                return 90;
            }
            auto encoded_size = message.encoded_size();
            if (!encoded_size || encoded_size.value() != 0u) {
                return 91;
            }
            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!message.serialize(writer) || writer.position() != 0u) {
                return 92;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || parsed.has_sha256() || parsed.sha256().size != 0u) {
                return 93;
            }
        }
        {
            Message message(ctx);
            auto sha256 = message.mutable_sha256();
            if (!message.has_sha256() || sha256.size != 32u) {
                return 94;
            }
            for (size_t i = 0; i < sha256.size; ++i) {
                if (sha256.data[i] != 0u) {
                    return 95;
                }
            }
            message.clear_sha256();
            if (message.has_sha256() || message.sha256().size != 0u) {
                return 96;
            }
        }
        {
            Message message(ctx);
            constexpr uint8_t kZeroSha256[32] = {};
            if (!message.set_sha256(view_of(kZeroSha256)) || !message.has_sha256()) {
                return 97;
            }
            auto encoded_size = message.encoded_size();
            if (!encoded_size || encoded_size.value() == 0u) {
                return 98;
            }
            uint8_t encoded[64] = {};
            protocyte::SliceWriter writer(encoded, sizeof(encoded));
            if (!message.serialize(writer) || writer.position() != encoded_size.value()) {
                return 99;
            }
            Message parsed(ctx);
            protocyte::SliceReader reader(encoded, writer.position());
            if (!parsed.merge_from(reader) || !parsed.has_sha256() ||
                !view_equal(parsed.sha256(), view_of(kZeroSha256))) {
                return 100;
            }
        }
        return 0;
    }

} // namespace

int main() {
    Config::Context ctx {
        protocyte::Allocator {nullptr, smoke_allocate, smoke_deallocate},
        protocyte::Limits {},
    };

    auto created = Message::create(ctx);
    if (!created) {
        return 1;
    }

    auto &message = created.value();
    auto st = populate_message(message, ctx);
    if (!st) {
        return 2;
    }

    const int round_trip = round_trip_and_check(message, ctx);
    if (round_trip != 0) {
        return round_trip;
    }

    const int oneofs = check_oneof_alternatives(ctx);
    if (oneofs != 0) {
        return oneofs;
    }

    const int fixed_size = check_fixed_size_presence(ctx);
    if (fixed_size != 0) {
        return fixed_size;
    }

    return 0;
}
