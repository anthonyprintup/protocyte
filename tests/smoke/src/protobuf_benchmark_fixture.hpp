#pragma once

#include <iterator>
#include <string>

#include "benchmark.pb.h"
#include "benchmark_fixture.hpp"

namespace protocyte_smoke::benchmark_fixture {

    using ProtobufMessage = ::test::benchmark::BenchmarkMessage;

    inline std::string bytes_of(const protocyte::Span<const protocyte::u8> view) {
        return std::string {reinterpret_cast<const char *>(view.data()), view.size()};
    }

    inline void populate_nested2(ProtobufMessage::NestedLevel1::NestedLevel2 *value,
                                 const protocyte::Span<const protocyte::u8> description, const float first,
                                 const float second,
                                 const ProtobufMessage::NestedLevel1::NestedLevel2::InnerEnum mode) {
        value->set_description(bytes_of(description));
        value->add_values(first);
        value->add_values(second);
        value->set_mode(mode);
    }

    inline void populate_nested1(ProtobufMessage::NestedLevel1 *value, const protocyte::Span<const protocyte::u8> name,
                                 const int32_t id) {
        value->set_name(bytes_of(name));
        value->set_id(id);
        populate_nested2(value->mutable_inner(), view_of(nested_description), 1.5f, 2.5f,
                         ProtobufMessage::NestedLevel1::NestedLevel2::B);
    }

    inline void append_bytes(google::protobuf::RepeatedPtrField<std::string> *values,
                             const protocyte::Span<const protocyte::u8> view) {
        values->Add(bytes_of(view));
    }

    inline void populate_fixed_repeated_bytes_holder(ProtobufMessage::FixedRepeatedBytesHolder *value) {
        append_bytes(value->mutable_values(), view_of(repeated_bytes_0));
        append_bytes(value->mutable_values(), view_of(repeated_bytes_2));
        append_bytes(value->mutable_values(), view_of(repeated_bytes_3));
    }

    inline void populate_protobuf_message(ProtobufMessage *message) {
        message->set_f_double(123.5);
        message->set_f_float(12.25f);
        message->set_f_int32(42);
        message->set_f_int64(42000000000ll);
        message->set_f_uint32(99u);
        message->set_f_uint64(99000000000ull);
        message->set_f_sint32(-17);
        message->set_f_sint64(-17000000000ll);
        message->set_f_fixed32(0x11223344u);
        message->set_f_fixed64(0x1122334455667788ull);
        message->set_f_sfixed32(-1234567);
        message->set_f_sfixed64(-1234567890123ll);
        message->set_f_bool(true);
        message->set_f_string(bytes_of(view_of(string_bytes)));
        message->set_f_bytes(bytes_of(view_of(bytes_data)));
        message->add_r_int32_unpacked(21);
        message->add_r_int32_unpacked(22);
        message->add_r_int32_packed(23);
        message->add_r_int32_packed(24);
        message->add_r_double(23.5);
        message->add_r_double(24.5);
        message->set_color(ProtobufMessage::GREEN);

        populate_nested1(message->mutable_nested1(), view_of(nested_name), 25);
        message->set_oneof_bytes(bytes_of(view_of(oneof_bytes)));
        (*message->mutable_map_str_int32())[bytes_of(view_of(map_key))] = 301;
        (*message->mutable_map_int32_str())[302] = bytes_of(view_of(map_value));
        (*message->mutable_map_bool_bytes())[true] = bytes_of(view_of(bool_bytes));
        populate_nested1(&(*message->mutable_map_uint64_msg())[3300u], view_of(nested_name), 330);
        populate_nested2(&(*message->mutable_very_nested_map())[bytes_of(view_of(very_nested_key))],
                         view_of(nested_description), 3.5f, 4.5f, ProtobufMessage::NestedLevel1::NestedLevel2::C);

        auto *recursive = message->mutable_recursive_self();
        recursive->set_f_string(bytes_of(view_of(recursive_string)));
        recursive->set_f_int32(350);
        recursive->mutable_fixed_integer_array()->Add(
            fixed_integer_array_values, fixed_integer_array_values + std::size(fixed_integer_array_values));
        append_bytes(recursive->mutable_fixed_repeated_byte_array(), view_of(repeated_bytes_0));
        append_bytes(recursive->mutable_fixed_repeated_byte_array(), view_of(repeated_bytes_2));
        append_bytes(recursive->mutable_fixed_repeated_byte_array(), view_of(repeated_bytes_3));

        populate_nested2(message->add_lots_of_nested(), view_of(nested_description), 36.5f, 37.5f,
                         ProtobufMessage::NestedLevel1::NestedLevel2::A);
        message->add_colors(ProtobufMessage::RED);
        message->add_colors(ProtobufMessage::BLUE);
        message->set_opt_int32(38);
        message->set_opt_string(bytes_of(view_of(optional_string)));
        message->set_sha256(bytes_of(view_of(sha256_bytes)));
        message->set_byte_array(bytes_of(view_of(byte_array)));
        message->set_float_expr_array(bytes_of(view_of(float_expr_array)));
        append_bytes(message->mutable_repeated_byte_array(), view_of(repeated_bytes_0));
        append_bytes(message->mutable_repeated_byte_array(), view_of(repeated_bytes_1));
        append_bytes(message->mutable_repeated_byte_array(), view_of(repeated_bytes_2));
        append_bytes(message->mutable_bounded_repeated_byte_array(), view_of(repeated_bytes_1));
        append_bytes(message->mutable_bounded_repeated_byte_array(), view_of(repeated_bytes_2));
        append_bytes(message->mutable_bounded_repeated_byte_array(), view_of(repeated_bytes_3));
        append_bytes(message->mutable_fixed_repeated_byte_array(), view_of(repeated_bytes_0));
        append_bytes(message->mutable_fixed_repeated_byte_array(), view_of(repeated_bytes_2));
        append_bytes(message->mutable_fixed_repeated_byte_array(), view_of(repeated_bytes_3));
        populate_fixed_repeated_bytes_holder(message->mutable_crazy_fixed_repeated_bytes());
        message->mutable_integer_array()->Add(integer_array_values,
                                              integer_array_values + std::size(integer_array_values));
        message->mutable_fixed_integer_array()->Add(fixed_integer_array_values,
                                                    fixed_integer_array_values + std::size(fixed_integer_array_values));

        auto *deep = message->mutable_extreme_nesting();
        deep->set_extreme(bytes_of(view_of(extreme_value)));
        (*deep->mutable_weird_map())[7] = bytes_of(view_of(weird_value));
        deep->set_text(bytes_of(view_of(deep_text)));
    }

} // namespace protocyte_smoke::benchmark_fixture
