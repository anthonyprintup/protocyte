#include "cross_package.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace test::crosspkg {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> CrossPackageConstants_Nested_fields {{
            {"nested_bytes", 1u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
        }};

        extern const ::std::array<::protocyte::ReflectionFieldInfo, 3> CrossPackageConstants_fields {{
            {"remote_bytes", 1u, "bytes", ::protocyte::ReflectionFieldLabel::optional, false, false},
            {"remote_values", 2u, "scalar", ::protocyte::ReflectionFieldLabel::repeated, false, true},
            {"nested", 3u, "message", ::protocyte::ReflectionFieldLabel::optional, true, false},
        }};

    } // namespace protocyte_reflection

} // namespace test::crosspkg
#endif // PROTOCYTE_ENABLE_REFLECTION
