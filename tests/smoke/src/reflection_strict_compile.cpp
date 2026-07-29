#include "open_enum.protocyte.hpp"
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

    const auto *closed = ::test::required::Proto2AliasMode_descriptor();
    if (!closed->closed || closed->deprecated || closed->values.size() != 3u) {
        return 5;
    }
    if (!::protocyte::string_view_equal(closed->name, {"Proto2AliasMode", 15u}) ||
        !::protocyte::string_view_equal(closed->full_name, {"test.required.Proto2AliasMode", 29u})) {
        return 6;
    }
    if (!::protocyte::string_view_equal(closed->values[0].name, {"PROTO2_ALIAS_MODE_UNKNOWN", 25u}) ||
        closed->values[0].number != 5 || closed->values[0].deprecated ||
        !::protocyte::string_view_equal(closed->values[1].name, {"PROTO2_ALIAS_MODE_READY", 23u}) ||
        closed->values[1].number != 9 || closed->values[1].deprecated ||
        !::protocyte::string_view_equal(closed->values[2].name, {"PROTO2_ALIAS_MODE_ACTIVE", 24u}) ||
        closed->values[2].number != 9 || !closed->values[2].deprecated) {
        return 7;
    }

    using ClosedMode = ::test::required::Proto2AliasMode;
    if (!::protocyte::string_view_equal(::test::required::Proto2AliasMode_name(ClosedMode::PROTO2_ALIAS_MODE_READY),
                                        {"PROTO2_ALIAS_MODE_READY", 23u})) {
        return 8;
    }
    ClosedMode closed_value = ClosedMode::PROTO2_ALIAS_MODE_UNKNOWN;
    if (!::test::required::Proto2AliasMode_parse({"PROTO2_ALIAS_MODE_ACTIVE", 24u}, closed_value) ||
        closed_value != ClosedMode::PROTO2_ALIAS_MODE_READY) {
        return 9;
    }
    if (::test::required::Proto2AliasMode_parse({"proto2_alias_mode_ready", 23u}, closed_value) ||
        closed_value != ClosedMode::PROTO2_ALIAS_MODE_READY) {
        return 10;
    }
    if (!::test::required::Proto2AliasMode_name(static_cast<ClosedMode>(7)).empty()) {
        return 11;
    }

    const auto *open = ::test::open::Mode_descriptor();
    if (open->closed || open->deprecated || open->values.size() != 3u) {
        return 12;
    }
    using OpenMode = ::test::open::Mode;
    if (!::protocyte::string_view_equal(::test::open::Mode_name(OpenMode::MODE_READY), {"MODE_READY", 10u})) {
        return 13;
    }
    OpenMode open_value = static_cast<OpenMode>(77);
    if (!::test::open::Mode_parse({"MODE_ACTIVE", 11u}, open_value) || open_value != OpenMode::MODE_READY) {
        return 14;
    }
    if (::test::open::Mode_parse({"MODE_MISSING", 12u}, open_value) || open_value != OpenMode::MODE_READY) {
        return 15;
    }
    if (!::test::open::Mode_name(static_cast<OpenMode>(77)).empty()) {
        return 16;
    }

    return reflection_symbols_compile_check();
}
