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

    } // namespace protocyte_reflection

} // namespace test::required
#endif // PROTOCYTE_ENABLE_REFLECTION
