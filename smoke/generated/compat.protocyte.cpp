#include "compat.protocyte.hpp"

#ifdef PROTOCYTE_ENABLE_REFLECTION
namespace protocyte_smoke::test::compat {

    namespace protocyte_reflection {
        struct FieldInfo {
            const char *name;
            ::protocyte::u32 number;
            const char *kind;
            bool repeated;
            bool optional;
            bool packed;
        };

        static const FieldInfo EncodingMatrix_Inner_fields[] = {
            {"value", 1u, "scalar", false, false, false},
            {"label", 2u, "string", false, false, false},
        };

        static const FieldInfo EncodingMatrix_fields[] = {
            {"f_int32", 1u, "scalar", false, false, false},
            {"f_int64", 2u, "scalar", false, false, false},
            {"f_uint32", 3u, "scalar", false, false, false},
            {"f_uint64", 4u, "scalar", false, false, false},
            {"f_sint32", 5u, "scalar", false, false, false},
            {"f_sint64", 6u, "scalar", false, false, false},
            {"f_bool", 7u, "scalar", false, false, false},
            {"mode", 8u, "enum", false, false, false},
            {"f_fixed32", 9u, "scalar", false, false, false},
            {"f_fixed64", 10u, "scalar", false, false, false},
            {"f_sfixed32", 11u, "scalar", false, false, false},
            {"f_sfixed64", 12u, "scalar", false, false, false},
            {"f_float", 13u, "scalar", false, false, false},
            {"f_double", 14u, "scalar", false, false, false},
            {"f_string", 15u, "string", false, false, false},
            {"f_bytes", 16u, "bytes", false, false, false},
            {"nested", 17u, "message", false, true, false},
            {"r_int32_unpacked", 18u, "scalar", true, false, false},
            {"r_int32_packed", 19u, "scalar", true, false, true},
            {"r_double", 20u, "scalar", true, false, true},
            {"oneof_string", 21u, "string", false, true, false},
            {"oneof_int32", 22u, "scalar", false, true, false},
            {"oneof_nested", 23u, "message", false, true, false},
            {"oneof_bytes", 24u, "bytes", false, true, false},
            {"opt_int32", 25u, "scalar", false, true, false},
            {"opt_string", 26u, "string", false, true, false},
            {"map_str_int32", 27u, "map", true, false, false},
            {"map_int32_str", 28u, "map", true, false, false},
        };

    } // namespace protocyte_reflection

} // namespace protocyte_smoke::test::compat
#endif // PROTOCYTE_ENABLE_REFLECTION
