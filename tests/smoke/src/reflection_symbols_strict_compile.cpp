#include "reflection_symbols.protocyte.hpp"
#include "reflection_symbols_other.protocyte.hpp"

int reflection_symbols_compile_check() {
    using namespace ::test::reflection_symbols::protocyte_reflection;

    const auto field_count =
        Foo_fields.size() + Foo_fields_.size() + Foo_fields_fields.size() + Foo_fields_fields_.size();
    using ShadowCarrier = ::test::reflection_symbols::ReflectionShadowCarrier<>;
    const auto *shadowed_enum = ShadowCarrier::protocyte_reflection_descriptor();
    return field_count == 0u && shadowed_enum->values.size() == 2u ? 0 : 4;
}
