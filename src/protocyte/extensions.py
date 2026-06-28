from __future__ import annotations

from google.protobuf import descriptor_pb2


CUSTOM_OPTION_EXTENDEES = {
    ".google.protobuf.FileOptions",
    ".google.protobuf.MessageOptions",
    ".google.protobuf.FieldOptions",
    ".google.protobuf.OneofOptions",
    ".google.protobuf.EnumOptions",
    ".google.protobuf.EnumValueOptions",
    ".google.protobuf.ExtensionRangeOptions",
    ".google.protobuf.ServiceOptions",
    ".google.protobuf.MethodOptions",
}


def is_custom_option_extension(field: descriptor_pb2.FieldDescriptorProto) -> bool:
    return field.extendee in CUSTOM_OPTION_EXTENDEES
