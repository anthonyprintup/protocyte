#include "reserved_identifiers.protocyte.hpp"

namespace reserved_identifiers = ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f;

using ReservedMessage = reserved_identifiers::Protocyte_escaped_5f5f4c494e455f5f<>;
using ReservedEnum = reserved_identifiers::Protocyte_escaped_5f5f46494c455f5f;
using KeywordMessage = reserved_identifiers::Class_<>;
using ConfigMessage = reserved_identifiers::Config<>;
using ReaderMessage = reserved_identifiers::Reader<>;

static_assert(reserved_identifiers::protocyte_escaped_5f5f444154455f5f == 7);
static_assert(ReservedMessage::protocyte_escaped_5f5f54494d455f5f == 9);
static_assert(ReservedEnum::protocyte_escaped_5f5570706572 != ReservedEnum::protocyte_escaped_76616c75655f5f676170);

void compile_reserved_identifier_accessors(ReservedMessage &message) {
    message.set_protocyte_escaped_5f5570706572(1);
    message.set_trailing_protocyte(2);
    message.set_protocyte_escaped_5f(3);
    const auto status = message.set_protocyte_escaped_5f5f46494c455f5f(::protocyte::StringView {"value", 5u});
    (void) status;
    message.set_protocyte_escaped_76616c75655f5f676170(4);
    message.clear_class_protocyte();
}

void compile_keyword_identifier_accessors(KeywordMessage &message) {
    message.set_value(1);
    message.clear_and_protocyte();
    message.clear_nested();
}

void compile_internal_identifier_messages(::protocyte::DefaultConfig::Context &ctx) {
    auto config = ConfigMessage::create(ctx);
    const auto set_status = config.set_text(::protocyte::StringView {"value", 5u});
    (void) set_status;

    const auto parsed = ReaderMessage::parse(ctx, ::protocyte::Span<const ::protocyte::u8> {});
    (void) parsed;
}
