#include "cross_package.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
#include <array>

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

        [[maybe_unused]] static const ::std::array<FieldInfo, 1> CrossPackageConstants_Nested_fields {{
            {"nested_bytes", 1u, "bytes", false, false, false},
        }};

        [[maybe_unused]] static const ::std::array<FieldInfo, 3> CrossPackageConstants_fields {{
            {"remote_bytes", 1u, "bytes", false, false, false},
            {"remote_values", 2u, "scalar", true, false, true},
            {"nested", 3u, "message", false, true, false},
        }};

    } // namespace protocyte_reflection

} // namespace test::crosspkg
#endif // PROTOCYTE_ENABLE_REFLECTION
