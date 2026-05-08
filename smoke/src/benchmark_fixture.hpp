#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdlib>

#include "protocyte/runtime/runtime.hpp"

namespace protocyte_smoke::benchmark_fixture {

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

    inline void *benchmark_allocate(void *, const size_t size, size_t) noexcept { return malloc(size); }

    inline void benchmark_deallocate(void *, void *ptr, size_t, size_t) noexcept { free(ptr); }

    inline protocyte::DefaultConfig::Context make_context() noexcept {
        return protocyte::DefaultConfig::Context {
            protocyte::Allocator {nullptr, benchmark_allocate, benchmark_deallocate},
            protocyte::Limits {},
        };
    }

    template<size_t N> constexpr protocyte::Span<const protocyte::u8> view_of(const uint8_t (&data)[N]) noexcept {
        return protocyte::Span<const protocyte::u8> {data, N};
    }

} // namespace protocyte_smoke::benchmark_fixture
