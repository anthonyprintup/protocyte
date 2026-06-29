#include "proto2_required.protocyte.hpp"

#ifdef PROTOCYTE_ENABLE_REFLECTION
namespace test::required {

    namespace protocyte_reflection {
        struct FieldInfo {
            const char *name;
            ::protocyte::u32 number;
            const char *kind;
            bool repeated;
            bool optional;
            bool packed;
        };

        static const FieldInfo RequiredChild_fields[] = {
            {"id", 1u, "scalar", false, true, false},
            {"note", 2u, "string", false, true, false},
        };

        static const FieldInfo RequiredParent_fields[] = {
            {"child", 1u, "message", false, true, false},
            {"children", 2u, "message", true, true, false},
        };

        static const FieldInfo Proto2ArrayDefaults_fields[] = {
            {"bounded_bytes", 1u, "bytes", false, true, false},
            {"fixed_bytes", 2u, "bytes", false, true, false},
        };

        static const FieldInfo Proto2DefaultValues_fields[] = {
            {"double_value", 1u, "scalar", false, true, false},
            {"float_value", 2u, "scalar", false, true, false},
            {"int64_value", 3u, "scalar", false, true, false},
            {"uint64_value", 4u, "scalar", false, true, false},
            {"int32_value", 5u, "scalar", false, true, false},
            {"fixed64_value", 6u, "scalar", false, true, false},
            {"fixed32_value", 7u, "scalar", false, true, false},
            {"bool_value", 8u, "scalar", false, true, false},
            {"string_value", 9u, "string", false, true, false},
            {"bytes_value", 10u, "bytes", false, true, false},
            {"uint32_value", 11u, "scalar", false, true, false},
            {"enum_value", 12u, "enum", false, true, false},
            {"sfixed32_value", 13u, "scalar", false, true, false},
            {"sfixed64_value", 14u, "scalar", false, true, false},
            {"sint32_value", 15u, "scalar", false, true, false},
            {"sint64_value", 16u, "scalar", false, true, false},
            {"implicit_enum_value", 17u, "enum", false, true, false},
        };

        static const FieldInfo OneofShadowingValue_fields[] = {
            {"bool_value", 1u, "scalar", false, true, false},
        };

    } // namespace protocyte_reflection

} // namespace test::required
#endif // PROTOCYTE_ENABLE_REFLECTION
