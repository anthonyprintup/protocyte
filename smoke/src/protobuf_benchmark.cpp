#include <benchmark/benchmark.h>

#include <cstdint>
#include <string>

#include "protobuf_benchmark_fixture.hpp"

namespace {

    using Message = protocyte_smoke::benchmark_fixture::ProtobufMessage;

    void BM_ProtobufBenchmarkMessage_ByteSizeLong(benchmark::State &state) {
        Message message;
        protocyte_smoke::benchmark_fixture::populate_protobuf_message(&message);

        for (auto _ : state) {
            auto size = message.ByteSizeLong();
            benchmark::DoNotOptimize(size);
        }
    }

    void BM_ProtobufBenchmarkMessage_Serialize(benchmark::State &state) {
        Message message;
        protocyte_smoke::benchmark_fixture::populate_protobuf_message(&message);
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
        protocyte_smoke::benchmark_fixture::populate_protobuf_message(&message);
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
