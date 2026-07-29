#include "reflection_symbols.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace test::reflection_symbols {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> Foo_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> Foo_fields_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> ReflectionShadowCarrier_fields {{}};

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2>
            ReflectionShadowCarrier_protocyte_reflection_enum_values {{
                {::protocyte::StringView {"PROTOCYTE_REFLECTION_UNSPECIFIED", 32u}, 0, false},
                {::protocyte::StringView {"PROTOCYTE_REFLECTION_READY", 26u}, 1, false},
            }};
        extern const ::protocyte::ReflectionEnumInfo ReflectionShadowCarrier_protocyte_reflection_enum {
            ::protocyte::StringView {"protocyte_reflection", 20u},
            ::protocyte::StringView {"test.reflection_symbols.ReflectionShadowCarrier.protocyte_reflection", 68u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {
                ReflectionShadowCarrier_protocyte_reflection_enum_values.data(),
                ReflectionShadowCarrier_protocyte_reflection_enum_values.size()},
            false,
            false,
        };

    } // namespace protocyte_reflection

} // namespace test::reflection_symbols
#endif // PROTOCYTE_ENABLE_REFLECTION
