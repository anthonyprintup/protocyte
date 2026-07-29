#pragma once

#ifndef PROTOCYTE_GENERATED_OPEN_ENUM_PROTO_8F36FB2CA590_HPP
#define PROTOCYTE_GENERATED_OPEN_ENUM_PROTO_8F36FB2CA590_HPP

#include <protocyte/runtime/runtime.hpp>

#if PROTOCYTE_ENABLE_REFLECTION
#include <array>
#endif

namespace test::open {

#if PROTOCYTE_ENABLE_REFLECTION
    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 3> Mode_enum_values;
        extern const ::protocyte::ReflectionEnumInfo Mode_enum;
    } // namespace protocyte_reflection
#endif // PROTOCYTE_ENABLE_REFLECTION

    enum struct Mode : ::protocyte::i32 {
        MODE_UNSPECIFIED = 0,
        MODE_READY = 1,
        MODE_ACTIVE [[deprecated]] = 1,
    };
    inline constexpr Mode Mode_MIN {Mode::MODE_UNSPECIFIED};
    inline constexpr Mode Mode_MAX {Mode::MODE_READY};
    inline constexpr ::protocyte::i32 Mode_ARRAYSIZE {2};
    [[nodiscard]] inline constexpr bool Mode_is_valid(const ::protocyte::i32 value) noexcept {
        return 0 <= value && value <= 1;
    }
#if PROTOCYTE_ENABLE_REFLECTION
    [[nodiscard]] inline const ::protocyte::ReflectionEnumInfo *Mode_descriptor() noexcept {
        return &protocyte_reflection::Mode_enum;
    }
    [[nodiscard]] inline ::protocyte::StringView Mode_name(const Mode value) noexcept {
        for (const auto &item : Mode_descriptor()->values) {
            if (item.number == static_cast<::protocyte::i32>(value)) {
                return item.name;
            }
        }
        return {};
    }
    [[nodiscard]] inline bool Mode_parse(const ::protocyte::StringView name, Mode &value) noexcept {
        for (const auto &item : Mode_descriptor()->values) {
            if (::protocyte::string_view_equal(name, item.name)) {
                value = static_cast<Mode>(item.number);
                return true;
            }
        }
        return false;
    }
#endif // PROTOCYTE_ENABLE_REFLECTION


} // namespace test::open

#endif // PROTOCYTE_GENERATED_OPEN_ENUM_PROTO_8F36FB2CA590_HPP
