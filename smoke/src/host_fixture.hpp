#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <string_view>

#include "example.protocyte.hpp"
#include "protocyte/runtime/runtime.hpp"

namespace protocyte_smoke::fixture {

    using Config = protocyte::DefaultConfig;
    using Message = ::test::ultimate::UltimateComplexMessage<>;
    using Nested1 = ::test::ultimate::UltimateComplexMessage_NestedLevel1<>;
    using Nested2 = ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<>;
    using RepeatedBytesHolder = ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<>;
    using BoundedRepeatedBytesHolder = ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<>;
    using FixedRepeatedBytesHolder = ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<>;
    using Deep = ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<>;
    using Color = ::test::ultimate::UltimateComplexMessage_Color;
    using InnerMode = ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;

    constexpr uint8_t string_bytes[] = {'s', 'm', 'o', 'k', 'e'};
    constexpr uint8_t bytes_data[] = {0x00u, 0x01u, 0x7fu, 0x80u, 0xffu};
    constexpr uint8_t nested_name[] = {'n', 'e', 's', 't', 'e', 'd'};
    constexpr uint8_t nested_description[] = {'i', 'n', 'n', 'e', 'r'};
    constexpr uint8_t oneof_bytes[] = {0xdeu, 0xadu, 0xbeu, 0xefu};
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
    constexpr uint8_t repeated_bytes_0[] = {0x11u};
    constexpr uint8_t repeated_bytes_1[] = {0x22u, 0x23u};
    constexpr uint8_t repeated_bytes_2[] = {0x34u, 0x35u, 0x36u, 0x37u};
    constexpr uint8_t repeated_bytes_3[] = {0x48u, 0x49u, 0x4au};
    constexpr uint8_t sha256_bytes[] = {
        0x10u, 0x21u, 0x32u, 0x43u, 0x54u, 0x65u, 0x76u, 0x87u, 0x98u, 0xa9u, 0xbau, 0xcbu, 0xdcu, 0xedu, 0xfeu, 0x0fu,
        0x1eu, 0x2du, 0x3cu, 0x4bu, 0x5au, 0x69u, 0x78u, 0x87u, 0x96u, 0xa5u, 0xb4u, 0xc3u, 0xd2u, 0xe1u, 0xf0u, 0x0fu,
    };
    constexpr int32_t integer_array_values[] = {101, 102, 103, 104, 105, 106, 107, 108};
    constexpr uint32_t fixed_integer_array_values[] = {901u, 902u, 903u};

    static_assert(sizeof(byte_array) == ::test::ultimate::BYTE_ARRAY_CAP);
    static_assert(sizeof(float_expr_array) == Message::FLOATISH_BOUND);
    static_assert(sizeof(integer_array_values) / sizeof(integer_array_values[0]) == Message::INTEGER_ARRAY_CAP);
    static_assert(sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]) ==
                  Message::FIXED_INTEGER_ARRAY_CAP);

    inline void *smoke_allocate(void *, size_t size, size_t) noexcept { return malloc(size); }

    inline void smoke_deallocate(void *, void *ptr, size_t, size_t) noexcept { free(ptr); }

    inline Config::Context make_context() noexcept {
        return Config::Context {
            protocyte::Allocator {nullptr, smoke_allocate, smoke_deallocate},
            protocyte::Limits {},
        };
    }

    template<size_t N> constexpr protocyte::Span<const protocyte::u8> view_of(const uint8_t (&data)[N]) noexcept {
        return protocyte::Span<const protocyte::u8> {data, N};
    }

    inline protocyte::Status assign_string(Config::String &out, protocyte::Span<const protocyte::u8> view) noexcept {
        return out.assign(view);
    }

    inline protocyte::Status assign_bytes(Config::Bytes &out, protocyte::Span<const protocyte::u8> view) noexcept {
        return out.assign(view);
    }

    template<class Container> protocyte::Status append_bytes(Container &out, Config::Context &ctx,
                                                             protocyte::Span<const protocyte::u8> view) noexcept {
        Config::Bytes value(&ctx);
        if (const auto st = assign_bytes(value, view); !st) {
            return st;
        }
        return out.push_back(protocyte::move(value));
    }

    inline protocyte::Status populate_required_fixed_array(Message &message, Config::Context &ctx) noexcept {
        for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
            if (const auto st = message.mutable_fixed_integer_array().push_back(fixed_integer_array_values[i]); !st) {
                return st;
            }
        }
        if (const auto st = append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_0));
            !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
            !st) {
            return st;
        }
        return append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
    }

    inline protocyte::Status populate_repeated_bytes_holder(RepeatedBytesHolder &value, Config::Context &ctx) noexcept {
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_0)); !st) {
            return st;
        }
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_1)); !st) {
            return st;
        }
        return append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2));
    }

    inline protocyte::Status populate_bounded_repeated_bytes_holder(BoundedRepeatedBytesHolder &value,
                                                                    Config::Context &ctx) noexcept {
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_1)); !st) {
            return st;
        }
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2)); !st) {
            return st;
        }
        return append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_3));
    }

    inline protocyte::Status populate_fixed_repeated_bytes_holder(FixedRepeatedBytesHolder &value,
                                                                  Config::Context &ctx) noexcept {
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_0)); !st) {
            return st;
        }
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2)); !st) {
            return st;
        }
        return append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_3));
    }

    inline protocyte::Status populate_nested2(Nested2 &value, protocyte::Span<const protocyte::u8> description,
                                              float first, float second, InnerMode mode) noexcept {
        if (const auto st = value.set_description(description); !st) {
            return st;
        }
        if (const auto st = value.mutable_values().push_back(first); !st) {
            return st;
        }
        if (const auto st = value.mutable_values().push_back(second); !st) {
            return st;
        }
        return value.set_mode(mode);
    }

    inline protocyte::Status populate_nested1(Nested1 &value, protocyte::Span<const protocyte::u8> name,
                                              int32_t id) noexcept {
        if (const auto st = value.set_name(name); !st) {
            return st;
        }
        if (const auto st = value.set_id(id); !st) {
            return st;
        }
        auto inner = value.ensure_inner();
        if (!inner) {
            return protocyte::unexpected(inner.error());
        }
        return populate_nested2(**inner, view_of(nested_description), 1.5f, 2.5f, InnerMode::B);
    }

    inline protocyte::Status insert_map_str_int32(Message &message, Config::Context &ctx) noexcept {
        Config::String key(&ctx);
        if (const auto st = assign_string(key, view_of(map_key)); !st) {
            return st;
        }
        return message.mutable_map_str_int32().insert_or_assign(protocyte::move(key), 301);
    }

    inline protocyte::Status insert_map_int32_str(Message &message, Config::Context &ctx) noexcept {
        Config::String value(&ctx);
        if (const auto st = assign_string(value, view_of(map_value)); !st) {
            return st;
        }
        return message.mutable_map_int32_str().insert_or_assign(302, protocyte::move(value));
    }

    inline protocyte::Status insert_map_bool_bytes(Message &message, Config::Context &ctx) noexcept {
        Config::Bytes value(&ctx);
        if (const auto st = assign_bytes(value, view_of(bool_bytes)); !st) {
            return st;
        }
        return message.mutable_map_bool_bytes().insert_or_assign(true, protocyte::move(value));
    }

    inline protocyte::Status insert_map_uint64_msg(Message &message, Config::Context &ctx) noexcept {
        Nested1 value(ctx);
        if (const auto st = populate_nested1(value, view_of(nested_name), 330); !st) {
            return st;
        }
        return message.mutable_map_uint64_msg().insert_or_assign(3300u, protocyte::move(value));
    }

    inline protocyte::Status insert_very_nested_map(Message &message, Config::Context &ctx) noexcept {
        Config::String key(&ctx);
        if (const auto st = assign_string(key, view_of(very_nested_key)); !st) {
            return st;
        }
        Nested2 value(ctx);
        if (const auto st = populate_nested2(value, view_of(nested_description), 3.5f, 4.5f, InnerMode::C); !st) {
            return st;
        }
        return message.mutable_very_nested_map().insert_or_assign(protocyte::move(key), protocyte::move(value));
    }

    inline protocyte::Status populate_deep(Deep &value, Config::Context &ctx) noexcept {
        if (const auto st = value.set_extreme(view_of(extreme_value)); !st) {
            return st;
        }
        Config::String weird(&ctx);
        if (const auto st = assign_string(weird, view_of(weird_value)); !st) {
            return st;
        }
        if (const auto st = value.mutable_weird_map().insert_or_assign(7, protocyte::move(weird)); !st) {
            return st;
        }
        return value.set_text(view_of(deep_text));
    }

    inline protocyte::Status populate_message(Message &message, Config::Context &ctx) noexcept {
        if (const auto st = message.set_f_double(123.5); !st) {
            return st;
        }
        if (const auto st = message.set_f_float(12.25f); !st) {
            return st;
        }
        if (const auto st = message.set_f_int32(42); !st) {
            return st;
        }
        if (const auto st = message.set_f_int64(42000000000ll); !st) {
            return st;
        }
        if (const auto st = message.set_f_uint32(99u); !st) {
            return st;
        }
        if (const auto st = message.set_f_uint64(99000000000ull); !st) {
            return st;
        }
        if (const auto st = message.set_f_sint32(-17); !st) {
            return st;
        }
        if (const auto st = message.set_f_sint64(-17000000000ll); !st) {
            return st;
        }
        if (const auto st = message.set_f_fixed32(0x11223344u); !st) {
            return st;
        }
        if (const auto st = message.set_f_fixed64(0x1122334455667788ull); !st) {
            return st;
        }
        if (const auto st = message.set_f_sfixed32(-1234567); !st) {
            return st;
        }
        if (const auto st = message.set_f_sfixed64(-1234567890123ll); !st) {
            return st;
        }
        if (const auto st = message.set_f_bool(true); !st) {
            return st;
        }
        if (const auto st = message.set_f_string(view_of(string_bytes)); !st) {
            return st;
        }
        if (const auto st = message.set_f_bytes(view_of(bytes_data)); !st) {
            return st;
        }
        if (const auto st = message.mutable_r_int32_unpacked().push_back(21); !st) {
            return st;
        }
        if (const auto st = message.mutable_r_int32_unpacked().push_back(22); !st) {
            return st;
        }
        if (const auto st = message.mutable_r_int32_packed().push_back(23); !st) {
            return st;
        }
        if (const auto st = message.mutable_r_int32_packed().push_back(24); !st) {
            return st;
        }
        if (const auto st = message.mutable_r_double().push_back(23.5); !st) {
            return st;
        }
        if (const auto st = message.mutable_r_double().push_back(24.5); !st) {
            return st;
        }
        if (const auto st = message.set_color(Color::GREEN); !st) {
            return st;
        }

        auto nested = message.ensure_nested1();
        if (!nested) {
            return protocyte::unexpected(nested.error());
        }
        if (const auto st = populate_nested1(**nested, view_of(nested_name), 25); !st) {
            return st;
        }

        if (const auto st = message.set_oneof_bytes(view_of(oneof_bytes)); !st) {
            return st;
        }
        if (const auto st = insert_map_str_int32(message, ctx); !st) {
            return st;
        }
        if (const auto st = insert_map_int32_str(message, ctx); !st) {
            return st;
        }
        if (const auto st = insert_map_bool_bytes(message, ctx); !st) {
            return st;
        }
        if (const auto st = insert_map_uint64_msg(message, ctx); !st) {
            return st;
        }
        if (const auto st = insert_very_nested_map(message, ctx); !st) {
            return st;
        }

        auto recursive = message.ensure_recursive_self();
        if (!recursive) {
            return protocyte::unexpected(recursive.error());
        }
        if (const auto st = (*recursive)->set_f_string(view_of(recursive_string)); !st) {
            return st;
        }
        if (const auto st = (*recursive)->set_f_int32(350); !st) {
            return st;
        }
        if (const auto st = populate_required_fixed_array(**recursive, ctx); !st) {
            return st;
        }

        auto nested_item = message.mutable_lots_of_nested().emplace_back(ctx);
        if (!nested_item) {
            return protocyte::unexpected(nested_item.error());
        }
        if (const auto st = populate_nested2(**nested_item, view_of(nested_description), 36.5f, 37.5f, InnerMode::A);
            !st) {
            return st;
        }

        if (const auto st = message.mutable_colors().push_back(static_cast<int32_t>(Color::RED)); !st) {
            return st;
        }
        if (const auto st = message.mutable_colors().push_back(static_cast<int32_t>(Color::BLUE)); !st) {
            return st;
        }
        if (const auto st = message.set_opt_int32(38); !st) {
            return st;
        }
        if (const auto st = message.set_opt_string(view_of(optional_string)); !st) {
            return st;
        }
        if (const auto st = message.set_sha256(view_of(sha256_bytes)); !st) {
            return st;
        }
        if (const auto st = message.set_byte_array(view_of(byte_array)); !st) {
            return st;
        }
        if (const auto st = message.set_float_expr_array(view_of(float_expr_array)); !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_repeated_byte_array(), ctx, view_of(repeated_bytes_0)); !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_repeated_byte_array(), ctx, view_of(repeated_bytes_1)); !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_repeated_byte_array(), ctx, view_of(repeated_bytes_2)); !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_bounded_repeated_byte_array(), ctx, view_of(repeated_bytes_1));
            !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_bounded_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
            !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_bounded_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
            !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_0));
            !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
            !st) {
            return st;
        }
        if (const auto st = append_bytes(message.mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
            !st) {
            return st;
        }
        auto crazy_fixed_repeated = message.ensure_crazy_fixed_repeated_bytes();
        if (!crazy_fixed_repeated) {
            return protocyte::unexpected(crazy_fixed_repeated.error());
        }
        if (const auto st = populate_fixed_repeated_bytes_holder(**crazy_fixed_repeated, ctx); !st) {
            return st;
        }

        for (size_t i = 0; i < sizeof(integer_array_values) / sizeof(integer_array_values[0]); ++i) {
            if (const auto st = message.mutable_integer_array().push_back(integer_array_values[i]); !st) {
                return st;
            }
        }
        for (size_t i = 0; i < sizeof(fixed_integer_array_values) / sizeof(fixed_integer_array_values[0]); ++i) {
            if (const auto st = message.mutable_fixed_integer_array().push_back(fixed_integer_array_values[i]); !st) {
                return st;
            }
        }

        auto deep = message.ensure_extreme_nesting();
        if (!deep) {
            return protocyte::unexpected(deep.error());
        }
        return populate_deep(**deep, ctx);
    }

} // namespace protocyte_smoke::fixture
