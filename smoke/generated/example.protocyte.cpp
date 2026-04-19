#include "example.protocyte.hpp"

#ifdef PROTOCYTE_ENABLE_REFLECTION
namespace test::ultimate {

    namespace protocyte_reflection {
        struct FieldInfo {
            const char *name;
            ::protocyte::u32 number;
            const char *kind;
            bool repeated;
            bool optional;
            bool packed;
        };

        static const FieldInfo UltimateComplexMessage_NestedLevel1_NestedLevel2_fields[] = {
            {"description", 1u, "string", false, false, false},
            {"values", 2u, "scalar", true, false, true},
            {"mode", 3u, "enum", false, false, false},
        };

        static const FieldInfo UltimateComplexMessage_NestedLevel1_fields[] = {
            {"name", 1u, "string", false, false, false},
            {"id", 2u, "scalar", false, false, false},
            {"inner", 3u, "message", false, true, false},
        };

        static const FieldInfo UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE_fields[] = {
            {"extreme", 1u, "string", false, false, false},
            {"weird_map", 2u, "map", true, false, false},
            {"val", 3u, "scalar", false, true, false},
            {"text", 4u, "string", false, true, false},
        };

        static const FieldInfo UltimateComplexMessage_fields[] = {
            {"f_double", 1u, "scalar", false, false, false},
            {"f_float", 2u, "scalar", false, false, false},
            {"f_int32", 4u, "scalar", false, false, false},
            {"f_int64", 8u, "scalar", false, false, false},
            {"f_uint32", 9u, "scalar", false, false, false},
            {"f_uint64", 10u, "scalar", false, false, false},
            {"f_sint32", 11u, "scalar", false, false, false},
            {"f_sint64", 12u, "scalar", false, false, false},
            {"f_fixed32", 13u, "scalar", false, false, false},
            {"f_fixed64", 14u, "scalar", false, false, false},
            {"f_sfixed32", 15u, "scalar", false, false, false},
            {"f_sfixed64", 16u, "scalar", false, false, false},
            {"f_bool", 17u, "scalar", false, false, false},
            {"f_string", 18u, "string", false, false, false},
            {"f_bytes", 19u, "bytes", false, false, false},
            {"r_int32_unpacked", 21u, "scalar", true, false, false},
            {"r_int32_packed", 22u, "scalar", true, false, true},
            {"r_double", 23u, "scalar", true, false, true},
            {"color", 24u, "enum", false, false, false},
            {"nested1", 25u, "message", false, true, false},
            {"oneof_string", 26u, "string", false, true, false},
            {"oneof_int32", 27u, "scalar", false, true, false},
            {"oneof_msg", 28u, "message", false, true, false},
            {"oneof_bytes", 29u, "bytes", false, true, false},
            {"map_str_int32", 30u, "map", true, false, false},
            {"map_int32_str", 31u, "map", true, false, false},
            {"map_bool_bytes", 32u, "map", true, false, false},
            {"map_uint64_msg", 33u, "map", true, false, false},
            {"very_nested_map", 34u, "map", true, false, false},
            {"recursive_self", 35u, "message", false, true, false},
            {"lots_of_nested", 36u, "message", true, true, false},
            {"colors", 37u, "enum", true, false, true},
            {"opt_int32", 38u, "scalar", false, true, false},
            {"opt_string", 39u, "string", false, true, false},
            {"extreme_nesting", 40u, "message", false, true, false},
            {"sha256", 41u, "bytes", false, false, false},
            {"integer_array", 42u, "scalar", true, false, true},
            {"byte_array", 43u, "bytes", false, false, false},
            {"fixed_integer_array", 44u, "scalar", true, false, true},
            {"float_expr_array", 45u, "bytes", false, false, false},
            {"repeated_byte_array", 46u, "bytes", true, false, false},
            {"bounded_repeated_byte_array", 47u, "bytes", true, false, false},
            {"fixed_repeated_byte_array", 48u, "bytes", true, false, false},
        };

        static const FieldInfo UltimateComplexMessage_LevelA_fields[] = {};

        static const FieldInfo UltimateComplexMessage_LevelA_LevelB_fields[] = {};

        static const FieldInfo UltimateComplexMessage_LevelA_LevelB_LevelC_fields[] = {};

        static const FieldInfo UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_fields[] = {};

        static const FieldInfo ExtraMessage_fields[] = {
            {"tag", 1u, "string", false, false, false},
            {"ref", 2u, "message", false, true, false},
        };

        static const FieldInfo CrossMessageConstants_Nested_fields[] = {
            {"nested_bytes", 1u, "bytes", false, false, false},
        };

        static const FieldInfo CrossMessageConstants_fields[] = {
            {"external_bytes", 1u, "bytes", false, false, false},
            {"mirrored_values", 2u, "scalar", true, false, true},
            {"nested", 3u, "message", false, true, false},
        };

    } // namespace protocyte_reflection

} // namespace test::ultimate
#endif // PROTOCYTE_ENABLE_REFLECTION
