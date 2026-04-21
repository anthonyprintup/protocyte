#include "cross_package.protocyte.hpp"

#ifdef PROTOCYTE_ENABLE_REFLECTION
namespace test::crosspkg {

    namespace protocyte_reflection {
        struct FieldInfo {
            const char *name;
            ::protocyte::u32 number;
            const char *kind;
            bool repeated;
            bool optional;
            bool packed;
        };

        static const FieldInfo CrossPackageConstants_Nested_fields[] = {
            {"nested_bytes", 1u, "bytes", false, false, false},
        };

        static const FieldInfo CrossPackageConstants_fields[] = {
            {"remote_bytes", 1u, "bytes", false, false, false},
            {"remote_values", 2u, "scalar", true, false, true},
            {"nested", 3u, "message", false, true, false},
        };

    } // namespace protocyte_reflection

} // namespace test::crosspkg
#endif // PROTOCYTE_ENABLE_REFLECTION
