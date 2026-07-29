#include "open_enum.protocyte.hpp"

#if PROTOCYTE_ENABLE_REFLECTION
namespace test::open {

    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 3> Mode_enum_values {{
            {::protocyte::StringView {"MODE_UNSPECIFIED", 16u}, 0, false},
            {::protocyte::StringView {"MODE_READY", 10u}, 1, false},
            {::protocyte::StringView {"MODE_ACTIVE", 11u}, 1, true},
        }};
        extern const ::protocyte::ReflectionEnumInfo Mode_enum {
            ::protocyte::StringView {"Mode", 4u},
            ::protocyte::StringView {"test.open.Mode", 14u},
            ::protocyte::Span<const ::protocyte::ReflectionEnumValueInfo> {Mode_enum_values.data(),
                                                                           Mode_enum_values.size()},
            false,
            false,
        };

    } // namespace protocyte_reflection

} // namespace test::open
#endif // PROTOCYTE_ENABLE_REFLECTION
