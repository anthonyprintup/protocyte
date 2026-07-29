#include "compat.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace protocyte_smoke::test::compat {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> EncodingMatrix_Inner_fields {{
            {"value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"label", 2u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 29> EncodingMatrix_fields {{
            {"f_int32", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_int64", 2u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_uint32", 3u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_uint64", 4u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sint32", 5u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sint64", 6u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_bool", 7u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"mode", 8u, "enum", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_fixed32", 9u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_fixed64", 10u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sfixed32", 11u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sfixed64", 12u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_float", 13u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_double", 14u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_string", 15u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_bytes", 16u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"nested", 17u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"r_int32_unpacked", 18u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"r_int32_packed", 19u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"r_double", 20u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"oneof_string", 21u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_int32", 22u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_nested", 23u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_bytes", 24u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"opt_int32", 25u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"opt_string", 26u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"map_str_int32", 27u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"map_int32_str", 28u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"deprecated_unused", 29u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 3> EncodingMatrix_Mode_enum_values {{
            {::protocyte::StringView {"MODE_UNSPECIFIED", 16u}, 0, false},
            {::protocyte::StringView {"FIRST", 5u}, 1, false},
            {::protocyte::StringView {"SECOND", 6u}, 2, false},
        }};
        extern const ::protocyte::ReflectionEnumInfo EncodingMatrix_Mode_enum {
            ::protocyte::StringView {"Mode", 4u},
            ::protocyte::StringView {"test.compat.EncodingMatrix.Mode", 31u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {EncodingMatrix_Mode_enum_values.data(),
                                                                           EncodingMatrix_Mode_enum_values.size()},
            false,
            false,
        };

    } // namespace protocyte_reflection

} // namespace protocyte_smoke::test::compat
#endif // PROTOCYTE_ENABLE_REFLECTION
