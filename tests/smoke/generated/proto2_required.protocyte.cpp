#include "proto2_required.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace test::required {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> RequiredChild_fields {{
            {"id", 1u, "scalar", ::protocyte::ReflectionFieldLabel::required, true, false},
            {"note", 2u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> RequiredParent_fields {{
            {"child", 1u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"children", 2u, "message", ::protocyte::ReflectionFieldLabel::repeated, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> Proto2ArrayDefaults_fields {{
            {"bounded_bytes", 1u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"fixed_bytes", 2u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 24> Proto2DefaultValues_fields {{
            {"double_value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"float_value", 2u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"int64_value", 3u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"uint64_value", 4u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"int32_value", 5u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"fixed64_value", 6u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"fixed32_value", 7u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"bool_value", 8u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"string_value", 9u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"bytes_value", 10u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"uint32_value", 11u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"enum_value", 12u, "enum", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"sfixed32_value", 13u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"sfixed64_value", 14u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"sint32_value", 15u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"sint64_value", 16u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"implicit_enum_value", 17u, "enum", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"enum_values", 18u, "enum", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"enum_by_name", 19u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"imported_open_enum", 20u, "enum", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"imported_open_unpacked", 21u, "enum", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"imported_open_packed", 22u, "enum", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"imported_open_oneof", 23u, "enum", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"imported_open_by_name", 24u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> OneofShadowingValue_fields {{
            {"bool_value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2> Proto2DefaultMode_enum_values {{
            {::protocyte::StringView {"PROTO2_DEFAULT_MODE_UNKNOWN", 27u}, 5, false},
            {::protocyte::StringView {"PROTO2_DEFAULT_MODE_READY", 25u}, 9, false},
        }};
        extern const ::protocyte::ReflectionEnumInfo Proto2DefaultMode_enum {
            ::protocyte::StringView {"Proto2DefaultMode", 17u},
            ::protocyte::StringView {"test.required.Proto2DefaultMode", 31u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {Proto2DefaultMode_enum_values.data(),
                                                                           Proto2DefaultMode_enum_values.size()},
            true,
            false,
        };

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 3> Proto2AliasMode_enum_values {{
            {::protocyte::StringView {"PROTO2_ALIAS_MODE_UNKNOWN", 25u}, 5, false},
            {::protocyte::StringView {"PROTO2_ALIAS_MODE_READY", 23u}, 9, false},
            {::protocyte::StringView {"PROTO2_ALIAS_MODE_ACTIVE", 24u}, 9, true},
        }};
        extern const ::protocyte::ReflectionEnumInfo Proto2AliasMode_enum {
            ::protocyte::StringView {"Proto2AliasMode", 15u},
            ::protocyte::StringView {"test.required.Proto2AliasMode", 29u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {Proto2AliasMode_enum_values.data(),
                                                                           Proto2AliasMode_enum_values.size()},
            true,
            false,
        };

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2> Proto2MapMode_enum_values {{
            {::protocyte::StringView {"PROTO2_MAP_MODE_UNKNOWN", 23u}, 0, false},
            {::protocyte::StringView {"PROTO2_MAP_MODE_READY", 21u}, 9, false},
        }};
        extern const ::protocyte::ReflectionEnumInfo Proto2MapMode_enum {
            ::protocyte::StringView {"Proto2MapMode", 13u},
            ::protocyte::StringView {"test.required.Proto2MapMode", 27u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {Proto2MapMode_enum_values.data(),
                                                                           Proto2MapMode_enum_values.size()},
            true,
            false,
        };

    } // namespace protocyte_reflection

} // namespace test::required
#endif // PROTOCYTE_ENABLE_REFLECTION
