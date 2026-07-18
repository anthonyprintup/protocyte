#include "reserved_identifiers.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f {

    namespace protocyte_reflection {
        struct FieldInfo {
            const char *name;
            ::protocyte::u32 number;
            const char *kind;
            bool repeated;
            bool optional;
            bool packed;
        };

        static const FieldInfo
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765_fields[] = {
                {"_Inner", 1u, "scalar", false, false, false},
        };

        static const FieldInfo Protocyte_escaped_5f5f4c494e455f5f_fields[] = {
            {"__FILE__", 1u, "string", false, true, false},   {"value__gap", 2u, "scalar", false, true, false},
            {"_Upper", 3u, "scalar", false, false, false},    {"trailing_", 4u, "scalar", false, false, false},
            {"enum__value", 5u, "enum", false, false, false}, {"class", 6u, "message", false, true, false},
            {"_", 7u, "scalar", false, false, false},
        };

        static const FieldInfo Class_Struct_fields[] = {
            {"value", 1u, "scalar", false, false, false},
        };

        static const FieldInfo Class_fields[] = {
            {"value", 1u, "scalar", false, true, false},
            {"nested", 2u, "message", false, true, false},
        };

    } // namespace protocyte_reflection

} // namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f
#endif // PROTOCYTE_ENABLE_REFLECTION
