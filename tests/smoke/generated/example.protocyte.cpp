#include "example.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace test::ultimate {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 3>
            UltimateComplexMessage_NestedLevel1_NestedLevel2_fields {{
                {"description", 1u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
                {"values", 2u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
                {"mode", 3u, "enum", ::protocyte::ReflectionFieldLabel::optional, false, false},
            }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 3> UltimateComplexMessage_NestedLevel1_fields {{
            {"name", 1u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"id", 2u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"inner", 3u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1>
            UltimateComplexMessage_RepeatedBytesHolder_fields {{
                {"values", 1u, "bytes", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1>
            UltimateComplexMessage_BoundedRepeatedBytesHolder_fields {{
                {"values", 1u, "bytes", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1>
            UltimateComplexMessage_FixedRepeatedBytesHolder_fields {{
                {"values", 1u, "bytes", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 4>
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE_fields {{
                {"extreme", 1u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
                {"weird_map", 2u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
                {"val", 3u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
                {"text", 4u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 49> UltimateComplexMessage_fields {{
            {"f_double", 1u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_float", 2u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_int32", 4u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_int64", 8u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_uint32", 9u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_uint64", 10u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sint32", 11u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sint64", 12u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_fixed32", 13u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_fixed64", 14u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sfixed32", 15u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_sfixed64", 16u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_bool", 17u, "scalar", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_string", 18u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"f_bytes", 19u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"r_int32_unpacked", 21u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"r_int32_packed", 22u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"r_double", 23u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"color", 24u, "enum", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"nested1", 25u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_string", 26u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_int32", 27u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_msg", 28u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"oneof_bytes", 29u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"crazy_plain_bytes", 49u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"crazy_bounded_bytes", 50u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"crazy_fixed_bytes", 51u, "bytes", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"crazy_repeated_bytes", 52u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"crazy_bounded_repeated_bytes", 53u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"crazy_fixed_repeated_bytes", 54u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"map_str_int32", 30u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"map_int32_str", 31u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"map_bool_bytes", 32u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"map_uint64_msg", 33u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"very_nested_map", 34u, "map", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"recursive_self", 35u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"lots_of_nested", 36u, "message", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"colors", 37u, "enum", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"opt_int32", 38u, "scalar", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"opt_string", 39u, "string", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"extreme_nesting", 40u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
            {"sha256", 41u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"integer_array", 42u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"byte_array", 43u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"fixed_integer_array", 44u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"float_expr_array", 45u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"repeated_byte_array", 46u, "bytes", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"bounded_repeated_byte_array", 47u, "bytes", ::protocyte::ReflectionFieldLabel::repeated, false, false},
            {"fixed_repeated_byte_array", 48u, "bytes", ::protocyte::ReflectionFieldLabel::repeated, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> UltimateComplexMessage_LevelA_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> UltimateComplexMessage_LevelA_LevelB_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0>
            UltimateComplexMessage_LevelA_LevelB_LevelC_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0>
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_fields {{}};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> ExtraMessage_fields {{
            {"tag", 1u, "string", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"ref", 2u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> CrossMessageConstants_Nested_fields {{
            {"nested_bytes", 1u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 3> CrossMessageConstants_fields {{
            {"external_bytes", 1u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"mirrored_values", 2u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"nested", 3u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

    } // namespace protocyte_reflection

} // namespace test::ultimate
#endif // PROTOCYTE_ENABLE_REFLECTION
