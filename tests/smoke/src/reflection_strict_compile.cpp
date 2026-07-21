#include "proto2_required.protocyte.hpp"

int reflection_symbols_compile_check();

int main() {
    using ::protocyte::ReflectionFieldLabel;
    using namespace ::test::required::protocyte_reflection;

    const auto &required_id = RequiredChild_fields[0];
    if (required_id.label != ReflectionFieldLabel::required || !required_id.has_presence) {
        return 1;
    }

    const auto &optional_note = RequiredChild_fields[1];
    if (optional_note.label != ReflectionFieldLabel::optional || !optional_note.has_presence) {
        return 2;
    }

    const auto &optional_child = RequiredParent_fields[0];
    if (optional_child.label != ReflectionFieldLabel::optional || !optional_child.has_presence) {
        return 3;
    }

    const auto &repeated_children = RequiredParent_fields[1];
    if (repeated_children.label != ReflectionFieldLabel::repeated || repeated_children.has_presence) {
        return 4;
    }

    return reflection_symbols_compile_check();
}
