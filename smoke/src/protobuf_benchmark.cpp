#include <benchmark/benchmark.h>

#include <cstdint>
#include <string>

#include "benchmark.pb.h"
#include "host_fixture.hpp"

namespace {

    using Message = test::benchmark::BenchmarkMessage;
    using Fixture = protocyte_smoke::fixture::Message;

    std::string bytes_of(protocyte::Span<const protocyte::u8> view) {
        return std::string {reinterpret_cast<const char *>(view.data()), view.size()};
    }

    void populate_nested2(Message::NestedLevel1::NestedLevel2 *value, protocyte::Span<const protocyte::u8> description,
                          float first, float second, Message::NestedLevel1::NestedLevel2::InnerEnum mode) {
        value->set_description(bytes_of(description));
        value->add_values(first);
        value->add_values(second);
        value->set_mode(mode);
    }

    void populate_nested1(Message::NestedLevel1 *value, protocyte::Span<const protocyte::u8> name, int32_t id) {
        value->set_name(bytes_of(name));
        value->set_id(id);
        populate_nested2(value->mutable_inner(),
                         protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::nested_description), 1.5f, 2.5f,
                         Message::NestedLevel1::NestedLevel2::B);
    }

    void append_bytes(google::protobuf::RepeatedPtrField<std::string> *values,
                      protocyte::Span<const protocyte::u8> view) {
        values->Add(bytes_of(view));
    }

    void populate_fixed_repeated_bytes_holder(Message::FixedRepeatedBytesHolder *value) {
        append_bytes(value->mutable_values(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_0));
        append_bytes(value->mutable_values(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_2));
        append_bytes(value->mutable_values(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_3));
    }

    void populate_message(Message *message) {
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
        message->set_f_string(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::string_bytes)));
        message->set_f_bytes(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::bytes_data)));
        message->add_r_int32_unpacked(21);
        message->add_r_int32_unpacked(22);
        message->add_r_int32_packed(23);
        message->add_r_int32_packed(24);
        message->add_r_double(23.5);
        message->add_r_double(24.5);
        message->set_color(Message::GREEN);

        populate_nested1(message->mutable_nested1(),
                         protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::nested_name), 25);
        message->set_oneof_bytes(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::oneof_bytes)));

        (*message->mutable_map_str_int32())[bytes_of(
            protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::map_key))] = 301;
        (*message->mutable_map_int32_str())[302] =
            bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::map_value));
        (*message->mutable_map_bool_bytes())[true] =
            bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::bool_bytes));
        populate_nested1(&(*message->mutable_map_uint64_msg())[3300u],
                         protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::nested_name), 330);
        populate_nested2(&(*message->mutable_very_nested_map())[bytes_of(
                             protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::very_nested_key))],
                         protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::nested_description), 3.5f, 4.5f,
                         Message::NestedLevel1::NestedLevel2::C);

        auto *recursive = message->mutable_recursive_self();
        recursive->set_f_string(
            bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::recursive_string)));
        recursive->set_f_int32(350);
        recursive->mutable_fixed_integer_array()->Add(
            protocyte_smoke::fixture::fixed_integer_array_values,
            protocyte_smoke::fixture::fixed_integer_array_values +
                (sizeof(protocyte_smoke::fixture::fixed_integer_array_values) /
                 sizeof(protocyte_smoke::fixture::fixed_integer_array_values[0])));
        append_bytes(recursive->mutable_fixed_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_0));
        append_bytes(recursive->mutable_fixed_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_2));
        append_bytes(recursive->mutable_fixed_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_3));

        populate_nested2(message->add_lots_of_nested(),
                         protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::nested_description), 36.5f, 37.5f,
                         Message::NestedLevel1::NestedLevel2::A);

        message->add_colors(Message::RED);
        message->add_colors(Message::BLUE);
        message->set_opt_int32(38);
        message->set_opt_string(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::optional_string)));
        message->set_sha256(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::sha256_bytes)));
        message->set_byte_array(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::byte_array)));
        message->set_float_expr_array(
            bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::float_expr_array)));
        append_bytes(message->mutable_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_0));
        append_bytes(message->mutable_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_1));
        append_bytes(message->mutable_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_2));
        append_bytes(message->mutable_bounded_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_1));
        append_bytes(message->mutable_bounded_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_2));
        append_bytes(message->mutable_bounded_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_3));
        append_bytes(message->mutable_fixed_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_0));
        append_bytes(message->mutable_fixed_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_2));
        append_bytes(message->mutable_fixed_repeated_byte_array(),
                     protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::repeated_bytes_3));
        populate_fixed_repeated_bytes_holder(message->mutable_crazy_fixed_repeated_bytes());

        message->mutable_integer_array()->Add(protocyte_smoke::fixture::integer_array_values,
                                              protocyte_smoke::fixture::integer_array_values +
                                                  (sizeof(protocyte_smoke::fixture::integer_array_values) /
                                                   sizeof(protocyte_smoke::fixture::integer_array_values[0])));
        message->mutable_fixed_integer_array()->Add(
            protocyte_smoke::fixture::fixed_integer_array_values,
            protocyte_smoke::fixture::fixed_integer_array_values +
                (sizeof(protocyte_smoke::fixture::fixed_integer_array_values) /
                 sizeof(protocyte_smoke::fixture::fixed_integer_array_values[0])));

        auto *deep = message->mutable_extreme_nesting();
        deep->set_extreme(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::extreme_value)));
        (*deep->mutable_weird_map())[7] =
            bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::weird_value));
        deep->set_text(bytes_of(protocyte_smoke::fixture::view_of(protocyte_smoke::fixture::deep_text)));
    }

    void BM_ProtobufBenchmarkMessage_ByteSizeLong(benchmark::State &state) {
        Message message;
        populate_message(&message);

        for (auto _ : state) {
            auto size = message.ByteSizeLong();
            benchmark::DoNotOptimize(size);
        }
    }

    void BM_ProtobufBenchmarkMessage_Serialize(benchmark::State &state) {
        Message message;
        populate_message(&message);
        std::string encoded;
        encoded.resize(message.ByteSizeLong());

        for (auto _ : state) {
            if (!message.SerializeToArray(encoded.data(), static_cast<int>(encoded.size()))) {
                state.SkipWithError("SerializeToArray failed");
                break;
            }
            benchmark::DoNotOptimize(encoded.data());
            benchmark::ClobberMemory();
        }
        state.SetBytesProcessed(static_cast<int64_t>(state.iterations()) * static_cast<int64_t>(encoded.size()));
    }

    void BM_ProtobufBenchmarkMessage_ParseFromArray(benchmark::State &state) {
        Message message;
        populate_message(&message);
        std::string encoded = message.SerializeAsString();

        for (auto _ : state) {
            Message parsed;
            if (!parsed.ParseFromArray(encoded.data(), static_cast<int>(encoded.size()))) {
                state.SkipWithError("ParseFromArray failed");
                break;
            }
            benchmark::DoNotOptimize(parsed.f_int32());
            benchmark::ClobberMemory();
        }
        state.SetBytesProcessed(static_cast<int64_t>(state.iterations()) * static_cast<int64_t>(encoded.size()));
    }

    BENCHMARK(BM_ProtobufBenchmarkMessage_ByteSizeLong);
    BENCHMARK(BM_ProtobufBenchmarkMessage_Serialize);
    BENCHMARK(BM_ProtobufBenchmarkMessage_ParseFromArray);

} // namespace
