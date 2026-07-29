#include "reserved_identifiers.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1>
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765_fields {{
                {"_Inner", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 7> protocyte_escaped_5f5f4c494e455f5f_fields {{
            {"__FILE__", 1u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"value__gap", 2u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"_Upper", 3u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"trailing_", 4u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"enum__value", 5u, "enum", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"class", 6u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"_", 7u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> class_struct_fields_ {{
            {"value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> class_protocyte_bae1d4f6754b_fields {{
            {"value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"nested", 2u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> Config_fields {{
            {"text", 1u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> Reader_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> MergeHelperNeighbors_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> MergeHelperNeighbors_merge_field_from_fields {{
            {"value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> MergeHelperNeighbors_merge_fields_from_fields_ {{
            {"value", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> LegacyPayload_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> DeprecationCarrier_fields {{
            {"legacy_mode", 1u, "enum", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"legacy_payload", 2u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2>
            protocyte_escaped_5f5f46494c455f5f_enum_values {{
                {::protocyte::StringView {"_Upper", 6u}, 0, false},
                {::protocyte::StringView {"value__gap", 10u}, 1, false},
            }};
        extern const ::protocyte::ReflectionEnumInfo protocyte_escaped_5f5f46494c455f5f_enum {
            ::protocyte::StringView {"__FILE__", 8u},
            ::protocyte::StringView {"_Package.__LINE__.__FILE__", 26u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {
                protocyte_escaped_5f5f46494c455f5f_enum_values.data(),
                protocyte_escaped_5f5f46494c455f5f_enum_values.size()},
            false,
            false,
        };

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 1> LegacyMode_enum_values {{
            {::protocyte::StringView {"LEGACY_MODE_UNSPECIFIED", 23u}, 0, false},
        }};
        extern const ::protocyte::ReflectionEnumInfo LegacyMode_enum {
            ::protocyte::StringView {"LegacyMode", 10u},
            ::protocyte::StringView {"_Package.__LINE__.LegacyMode", 28u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {LegacyMode_enum_values.data(),
                                                                           LegacyMode_enum_values.size()},
            false,
            true,
        };

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2>
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum_values {{
                {::protocyte::StringView {"__STDC__", 8u}, 0, false},
                {::protocyte::StringView {"enum_trailing_", 14u}, 1, false},
            }};
        extern const ::protocyte::ReflectionEnumInfo
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum {
                ::protocyte::StringView {"_NestedEnum", 11u},
                ::protocyte::StringView {"_Package.__LINE__.__LINE__._NestedEnum", 38u},
                ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {
                    protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum_values.data(),
                    protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum_values.size()},
                false,
                false,
            };

        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 1> class_KeywordValues_enum_values {{
            {::protocyte::StringView {"class", 5u}, 0, false},
        }};
        extern const ::protocyte::ReflectionEnumInfo class_KeywordValues_enum {
            ::protocyte::StringView {"KeywordValues", 13u},
            ::protocyte::StringView {"_Package.__LINE__.class.KeywordValues", 37u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {class_KeywordValues_enum_values.data(),
                                                                           class_KeywordValues_enum_values.size()},
            false,
            false,
        };

    } // namespace protocyte_reflection

} // namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f
#endif // PROTOCYTE_ENABLE_REFLECTION
