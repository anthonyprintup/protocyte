#include <benchmark/benchmark.h>

#include <cstdint>
#include <vector>

#include "host_fixture.hpp"

namespace {

    using Fixture = protocyte_smoke::fixture::Message;

    bool make_populated_message(Fixture &message, protocyte_smoke::fixture::Config::Context &ctx,
                                benchmark::State &state) {
        if (const auto st = protocyte_smoke::fixture::populate_message(message, ctx); !st) {
            state.SkipWithError("populate_message failed");
            return false;
        }
        return true;
    }

    bool make_encoded_message(std::vector<protocyte::u8> &encoded, benchmark::State &state) {
        auto ctx = protocyte_smoke::fixture::make_context();
        Fixture message(ctx);
        if (!make_populated_message(message, ctx, state)) {
            return false;
        }

        const auto encoded_size = message.encoded_size();
        if (!encoded_size) {
            state.SkipWithError("encoded_size failed");
            return false;
        }

        encoded.resize(*encoded_size);
        protocyte::SliceWriter writer(encoded.data(), encoded.size());
        if (const auto st = message.serialize(writer); !st) {
            state.SkipWithError("serialize failed");
            return false;
        }
        if (writer.position() != encoded.size()) {
            state.SkipWithError("serialize wrote an unexpected number of bytes");
            return false;
        }
        return true;
    }

    void BM_UltimateComplexMessage_EncodedSize(benchmark::State &state) {
        auto ctx = protocyte_smoke::fixture::make_context();
        Fixture message(ctx);
        if (!make_populated_message(message, ctx, state)) {
            return;
        }

        for (auto _ : state) {
            const auto encoded_size = message.encoded_size();
            if (!encoded_size) {
                state.SkipWithError("encoded_size failed");
                break;
            }
            auto size_value = *encoded_size;
            benchmark::DoNotOptimize(size_value);
        }
    }

    void BM_UltimateComplexMessage_Serialize(benchmark::State &state) {
        auto ctx = protocyte_smoke::fixture::make_context();
        Fixture message(ctx);
        if (!make_populated_message(message, ctx, state)) {
            return;
        }

        const auto encoded_size = message.encoded_size();
        if (!encoded_size) {
            state.SkipWithError("encoded_size failed");
            return;
        }
        std::vector<protocyte::u8> buffer(*encoded_size);

        for (auto _ : state) {
            protocyte::SliceWriter writer(buffer.data(), buffer.size());
            if (const auto st = message.serialize(writer); !st) {
                state.SkipWithError("serialize failed");
                break;
            }
            benchmark::DoNotOptimize(writer.position());
            benchmark::ClobberMemory();
        }
        state.SetBytesProcessed(static_cast<int64_t>(state.iterations()) * static_cast<int64_t>(buffer.size()));
    }

    void BM_UltimateComplexMessage_MergeFrom(benchmark::State &state) {
        std::vector<protocyte::u8> encoded;
        if (!make_encoded_message(encoded, state)) {
            return;
        }

        for (auto _ : state) {
            auto ctx = protocyte_smoke::fixture::make_context();
            Fixture parsed(ctx);
            protocyte::SliceReader reader(encoded.data(), encoded.size());
            if (const auto st = parsed.merge_from(reader); !st) {
                state.SkipWithError("merge_from failed");
                break;
            }
            benchmark::DoNotOptimize(parsed.f_int32());
            benchmark::ClobberMemory();
        }
        state.SetBytesProcessed(static_cast<int64_t>(state.iterations()) * static_cast<int64_t>(encoded.size()));
    }

    BENCHMARK(BM_UltimateComplexMessage_EncodedSize);
    BENCHMARK(BM_UltimateComplexMessage_Serialize);
    BENCHMARK(BM_UltimateComplexMessage_MergeFrom);

} // namespace
