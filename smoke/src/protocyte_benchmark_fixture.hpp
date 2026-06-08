#pragma once

#include "benchmark.protocyte.hpp"
#include "benchmark_fixture.hpp"

namespace protocyte_smoke::benchmark_fixture {

    using ProtocyteMessage = ::protocyte_smoke::test::benchmark::BenchmarkMessage<>;
    using ProtocyteNested1 = ::protocyte_smoke::test::benchmark::BenchmarkMessage_NestedLevel1<>;
    using ProtocyteNested2 = ::protocyte_smoke::test::benchmark::BenchmarkMessage_NestedLevel1_NestedLevel2<>;
    using ProtocyteFixedRepeatedBytesHolder =
        ::protocyte_smoke::test::benchmark::BenchmarkMessage_FixedRepeatedBytesHolder<>;
    using ProtocyteDeep = ::protocyte_smoke::test::benchmark::BenchmarkMessage_LevelA_LevelB_LevelC_LevelD_LevelE<>;
    using ProtocyteColor = ::protocyte_smoke::test::benchmark::BenchmarkMessage_Color;
    using ProtocyteInnerMode = ::protocyte_smoke::test::benchmark::BenchmarkMessage_NestedLevel1_NestedLevel2_InnerEnum;

    template<class Container> protocyte::Status append_bytes(Container &out, protocyte::DefaultConfig::Context &ctx,
                                                             protocyte::Span<const protocyte::u8> view) noexcept {
        protocyte::DefaultConfig::Bytes value(&ctx);
        if (const auto st = value.assign(view); !st) {
            return st;
        }
        return out.push_back(protocyte::move(value));
    }

    inline protocyte::Status populate_nested2(ProtocyteNested2 &value, protocyte::Span<const protocyte::u8> description,
                                              const float first, const float second,
                                              const ProtocyteInnerMode mode) noexcept {
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

    inline protocyte::Status populate_nested1(ProtocyteNested1 &value, protocyte::Span<const protocyte::u8> name,
                                              const int32_t id) noexcept {
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
        return populate_nested2(*inner, view_of(nested_description), 1.5f, 2.5f, ProtocyteInnerMode::B);
    }

    inline protocyte::Status populate_fixed_repeated_bytes_holder(ProtocyteFixedRepeatedBytesHolder &value,
                                                                  protocyte::DefaultConfig::Context &ctx) noexcept {
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_0)); !st) {
            return st;
        }
        if (const auto st = append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_2)); !st) {
            return st;
        }
        return append_bytes(value.mutable_values(), ctx, view_of(repeated_bytes_3));
    }

    inline protocyte::Status insert_map_str_int32(ProtocyteMessage &message,
                                                  protocyte::DefaultConfig::Context &ctx) noexcept {
        protocyte::DefaultConfig::String key(&ctx);
        if (const auto st = key.assign(view_of(map_key)); !st) {
            return st;
        }
        return message.mutable_map_str_int32().insert_or_assign(protocyte::move(key), 301);
    }

    inline protocyte::Status insert_map_int32_str(ProtocyteMessage &message,
                                                  protocyte::DefaultConfig::Context &ctx) noexcept {
        protocyte::DefaultConfig::String value(&ctx);
        if (const auto st = value.assign(view_of(map_value)); !st) {
            return st;
        }
        return message.mutable_map_int32_str().insert_or_assign(302, protocyte::move(value));
    }

    inline protocyte::Status insert_map_bool_bytes(ProtocyteMessage &message,
                                                   protocyte::DefaultConfig::Context &ctx) noexcept {
        protocyte::DefaultConfig::Bytes value(&ctx);
        if (const auto st = value.assign(view_of(bool_bytes)); !st) {
            return st;
        }
        return message.mutable_map_bool_bytes().insert_or_assign(true, protocyte::move(value));
    }

    inline protocyte::Status insert_map_uint64_msg(ProtocyteMessage &message,
                                                   protocyte::DefaultConfig::Context &ctx) noexcept {
        ProtocyteNested1 value(ctx);
        if (const auto st = populate_nested1(value, view_of(nested_name), 330); !st) {
            return st;
        }
        return message.mutable_map_uint64_msg().insert_or_assign(3300u, protocyte::move(value));
    }

    inline protocyte::Status insert_very_nested_map(ProtocyteMessage &message,
                                                    protocyte::DefaultConfig::Context &ctx) noexcept {
        protocyte::DefaultConfig::String key(&ctx);
        if (const auto st = key.assign(view_of(very_nested_key)); !st) {
            return st;
        }
        ProtocyteNested2 value(ctx);
        if (const auto st = populate_nested2(value, view_of(nested_description), 3.5f, 4.5f, ProtocyteInnerMode::C);
            !st) {
            return st;
        }
        return message.mutable_very_nested_map().insert_or_assign(protocyte::move(key), protocyte::move(value));
    }

    inline protocyte::Status populate_deep(ProtocyteDeep &value, protocyte::DefaultConfig::Context &ctx) noexcept {
        if (const auto st = value.set_extreme(view_of(extreme_value)); !st) {
            return st;
        }
        protocyte::DefaultConfig::String weird(&ctx);
        if (const auto st = weird.assign(view_of(weird_value)); !st) {
            return st;
        }
        if (const auto st = value.mutable_weird_map().insert_or_assign(7, protocyte::move(weird)); !st) {
            return st;
        }
        return value.set_text(view_of(deep_text));
    }

    inline protocyte::Status populate_protocyte_message(ProtocyteMessage &message,
                                                        protocyte::DefaultConfig::Context &ctx) noexcept {
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
        if (const auto st = message.set_color(ProtocyteColor::GREEN); !st) {
            return st;
        }

        auto nested = message.ensure_nested1();
        if (!nested) {
            return protocyte::unexpected(nested.error());
        }
        if (const auto st = populate_nested1(*nested, view_of(nested_name), 25); !st) {
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
        if (const auto st = recursive->set_f_string(view_of(recursive_string)); !st) {
            return st;
        }
        if (const auto st = recursive->set_f_int32(350); !st) {
            return st;
        }
        for (const auto value : fixed_integer_array_values) {
            if (const auto st = recursive->mutable_fixed_integer_array().push_back(value); !st) {
                return st;
            }
        }
        if (const auto st =
                append_bytes(recursive->mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_0));
            !st) {
            return st;
        }
        if (const auto st =
                append_bytes(recursive->mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_2));
            !st) {
            return st;
        }
        if (const auto st =
                append_bytes(recursive->mutable_fixed_repeated_byte_array(), ctx, view_of(repeated_bytes_3));
            !st) {
            return st;
        }

        auto nested_item = message.mutable_lots_of_nested().emplace_back(ctx);
        if (!nested_item) {
            return protocyte::unexpected(nested_item.error());
        }
        if (const auto st =
                populate_nested2(*nested_item, view_of(nested_description), 36.5f, 37.5f, ProtocyteInnerMode::A);
            !st) {
            return st;
        }
        if (const auto st = message.mutable_colors().push_back(static_cast<int32_t>(ProtocyteColor::RED)); !st) {
            return st;
        }
        if (const auto st = message.mutable_colors().push_back(static_cast<int32_t>(ProtocyteColor::BLUE)); !st) {
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
        if (const auto st = populate_fixed_repeated_bytes_holder(*crazy_fixed_repeated, ctx); !st) {
            return st;
        }
        for (const auto value : integer_array_values) {
            if (const auto st = message.mutable_integer_array().push_back(value); !st) {
                return st;
            }
        }
        for (const auto value : fixed_integer_array_values) {
            if (const auto st = message.mutable_fixed_integer_array().push_back(value); !st) {
                return st;
            }
        }

        auto deep = message.ensure_extreme_nesting();
        if (!deep) {
            return protocyte::unexpected(deep.error());
        }
        return populate_deep(*deep, ctx);
    }

} // namespace protocyte_smoke::benchmark_fixture
