from pathlib import Path

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

from protocyte.model import build_model
from protocyte.plugin import generate_response


F = descriptor_pb2.FieldDescriptorProto


def test_generates_proto3_files_and_runtime() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("simple.proto")
    request.parameter = "runtime=emit"
    request.proto_file.append(_simple_file())

    response = generate_response(request)

    assert not response.error
    assert response.supported_features & plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    files = {item.name: item.content for item in response.file}
    assert "simple.protocyte.hpp" in files
    assert "simple.protocyte.cpp" in files
    assert "protocyte/runtime/runtime.hpp" in files
    assert "struct Sample;" in files["simple.protocyte.hpp"]
    assert files["simple.protocyte.hpp"].startswith("#pragma once\n\n#ifndef PROTOCYTE_GENERATED_SIMPLE_PROTO_HPP")
    assert "#include <cstddef>" not in files["simple.protocyte.hpp"]
    assert "#include <cstdint>" not in files["simple.protocyte.hpp"]
    assert "#include <cstdlib>" not in files["simple.protocyte.hpp"]
    assert "#include <stddef.h>" not in files["simple.protocyte.hpp"]
    assert "#include <stdint.h>" not in files["simple.protocyte.hpp"]
    assert files["protocyte/runtime/runtime.hpp"].startswith("#pragma once\n\n#ifndef PROTOCYTE_RUNTIME_RUNTIME_HPP")
    assert "#include <cstddef>" in files["protocyte/runtime/runtime.hpp"]
    assert "#include <cstdint>" in files["protocyte/runtime/runtime.hpp"]
    assert "#include <cstdlib>" not in files["protocyte/runtime/runtime.hpp"]
    assert "#include <stddef.h>" not in files["protocyte/runtime/runtime.hpp"]
    assert "#include <stdint.h>" not in files["protocyte/runtime/runtime.hpp"]
    assert "kDefaultMaxRecursionDepth = 100u" in files["protocyte/runtime/runtime.hpp"]
    assert "kDefaultMaxMessageBytes = 0x7fffffffu" in files["protocyte/runtime/runtime.hpp"]
    assert "kDefaultMaxStringBytes = 0x7fffffffu" in files["protocyte/runtime/runtime.hpp"]
    assert "kDefaultMaxRepeatedCount = 0x7fffffffu" in files["protocyte/runtime/runtime.hpp"]
    assert "kDefaultMaxMapEntries = 0x7fffffffu" in files["protocyte/runtime/runtime.hpp"]
    assert "template<typename Config = ::protocyte::DefaultConfig>" in files["simple.protocyte.hpp"]
    assert "class Status" not in files["protocyte/runtime/runtime.hpp"]
    assert "public:" not in files["protocyte/runtime/runtime.hpp"]
    assert "private:" not in files["protocyte/runtime/runtime.hpp"]
    assert "protected:" in files["protocyte/runtime/runtime.hpp"]
    assert "protected:" in files["simple.protocyte.hpp"]
    assert "enum class ErrorCode : u32" in files["protocyte/runtime/runtime.hpp"]
    assert "enum class WireType : u32" in files["protocyte/runtime/runtime.hpp"]
    assert "VARINT = 0u" in files["protocyte/runtime/runtime.hpp"]
    assert "I64 = 1u" in files["protocyte/runtime/runtime.hpp"]
    assert "LEN = 2u" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Status() noexcept = default;" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Status() noexcept: error_" not in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr explicit Status(const Error error) noexcept" in files["protocyte/runtime/runtime.hpp"]
    assert "static constexpr Status ok() noexcept { return {}; }" in files["protocyte/runtime/runtime.hpp"]
    assert "const usize offset = {}" in files["protocyte/runtime/runtime.hpp"]
    assert "void *hosted_allocate(void *state, usize size, usize alignment) noexcept;" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "return Status {Error {.code = code, .offset = offset, .field_number = field_number}};" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "u64 value {};" in files["protocyte/runtime/runtime.hpp"]
    assert "u64 value = {};" not in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[4u];" in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[8u];" in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[8u] {\n" in files["protocyte/runtime/runtime.hpp"]
    assert "for (usize i {}; i < lhs.size; ++i)" in files["protocyte/runtime/runtime.hpp"]
    assert "if (!size)" in files["protocyte/runtime/runtime.hpp"]
    assert "other.size_ = {};" in files["protocyte/runtime/runtime.hpp"]
    assert "if (const auto st = checked_mul(requested, sizeof(T), &bytes); !st)" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "if (const Bucket &bucket = buckets_[i]; bucket.occupied)" in files["protocyte/runtime/runtime.hpp"]
    assert "const auto field = static_cast<u32>(tag.value() >> 3u);" in files["protocyte/runtime/runtime.hpp"]
    assert "const auto wire = static_cast<WireType>(tag.value() & 0x7u);" in files["protocyte/runtime/runtime.hpp"]
    assert "Status skip_field(Reader &reader, const WireType wire_type, const u32 field_number = {}) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status write_tag(Writer &writer, const u32 field_number, const WireType wire_type) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "FEATURE_PROTO3_OPTIONAL" not in files["simple.protocyte.hpp"]


def test_rejects_non_proto3_target() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("legacy.proto")
    file = request.proto_file.add()
    file.name = "legacy.proto"
    file.syntax = "proto2"
    file.message_type.add().name = "Legacy"

    response = generate_response(request)

    assert 'expected syntax = "proto3"' in response.error


def test_model_detects_maps_and_recursive_boxing() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("simple.proto")
    request.proto_file.append(_simple_file())

    model = build_model(request)
    sample = model.messages["demo.Sample"]
    fields = {field.name: field for field in sample.fields}

    assert fields["items"].kind == "map"
    assert fields["self"].recursive_box is True


def test_generated_header_contains_expected_field_api() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("simple.proto")
    request.proto_file.append(_simple_file())

    response = generate_response(request)
    header = next(file.content for file in response.file if file.name == "simple.protocyte.hpp")

    assert "namespace demo {" in header
    assert "bool has_opt_name() const noexcept" in header
    assert "struct Sample {" in header
    assert "typename Config::template Map<typename Config::String, ::protocyte::i32> items_;" in header
    assert "typename Config::template Box<::demo::Sample<Config>> self_;" in header
    assert "ctx_ {&ctx}" in header
    assert "items_ {&ctx}" in header
    assert "::protocyte::Status set_id(const ::protocyte::i32 value) noexcept" in header
    assert "const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);" in header
    assert "const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);" in header
    assert "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept" in header
    assert "using RuntimeStatus = ::protocyte::Status;" in header
    assert "insert_or_assign(::protocyte::move(key), ::protocyte::move(value))" in header
    assert "template<typename Reader>" in header
    assert "RuntimeStatus merge_from(Reader &reader) noexcept" in header
    assert "for (::protocyte::usize i {}; i < samples_.size(); ++i)" in header
    assert "if (const auto st = out.value().copy_from(*this); !st)" in header
    assert "if (wire_type != ::protocyte::WireType::LEN)" in header
    assert "enum struct FieldNumber : ::protocyte::u32 {" in header
    assert "id = 1u," in header
    assert "opt_name = 2u," in header
    assert "case FieldNumber::id: {" in header
    assert "case FieldNumber::opt_name: {" in header
    assert "auto raw = ::protocyte::read_fixed32(packed);" in header
    assert "auto value = ::protocyte::read_fixed32(packed);" not in header
    assert "if (other.has_items())" not in header
    assert "other.samples()" not in header
    assert "return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());" in header
    assert "::protocyte::LimitedReader nested {entry_reader" in header
    assert "::protocyte::ReaderRef sub_reader {sub};" in header
    assert "merge_from(sub_reader);" in header
    assert "::protocyte::ReaderRef nested_reader {nested};" in header


def test_model_decodes_fixed_size_bytes_option() -> None:
    model = build_model(_fixed_size_request())

    sha256 = model.messages["demo.FixedBytes"].fields[0]

    assert sha256.kind == "bytes"
    assert sha256.fixed_bytes is True
    assert sha256.fixed_size == 32


def test_generated_header_uses_inline_fixed_size_bytes_storage() -> None:
    response = generate_response(_fixed_size_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["fixed.protocyte.hpp"]
    runtime_header = files["protocyte/runtime/runtime.hpp"]

    assert "::protocyte::ByteView sha256() const noexcept" in header
    assert "::protocyte::MutableByteView mutable_sha256() noexcept" in header
    assert "bool has_sha256() const noexcept" in header
    assert "::protocyte::u8 sha256_[32u];" in header
    assert "bool has_sha256_ {};" in header
    assert "sha256_ {&ctx}" not in header
    assert "return has_sha256_ ? ::protocyte::ByteView {.data = sha256_, .size = 32u} : ::protocyte::ByteView {};" in header
    assert "if (!has_sha256_) {" in header
    assert "has_sha256_ = true;" in header
    assert "if (value.size != 32u)" in header
    assert "len.value() == 32u" in header
    assert "len.value() == 0u" not in header
    assert "if (const auto st = writer.write(" in header
    assert "::protocyte::bytes_zero(" not in header
    assert "if (has_sha256_)" in header
    assert "::protocyte::write_varint(writer, 32u)" in header
    assert "void clear_sha256() noexcept { has_sha256_ = false; }" in header
    assert "constexpr bool bytes_zero(const ByteView view) noexcept" in runtime_header


def test_rejects_invalid_fixed_size_targets() -> None:
    bad_type_response = generate_response(_fixed_size_request(field_type=F.TYPE_STRING))
    repeated_response = generate_response(_fixed_size_request(label=F.LABEL_REPEATED))

    assert "only supported on bytes fields" in bad_type_response.error
    assert "does not support repeated fields" in repeated_response.error


def test_generated_header_emits_tagged_union_oneofs() -> None:
    response = generate_response(_oneof_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["oneof.protocyte.hpp"]
    protected = header.split("protected:", maxsplit=1)[1]

    assert "Carrier(Carrier &&other) noexcept" in header
    assert "Carrier &operator=(Carrier &&other) noexcept" in header
    assert "~Carrier() noexcept { clear_choice(); }" in header
    assert "template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }" in header
    assert "void clear_choice() noexcept {" in header
    assert "destroy_at_(&choice.text);" in header
    assert "destroy_at_(&choice.inner);" in header
    assert "union ChoiceStorage {" in header
    assert "ChoiceStorage() noexcept {}" in header
    assert "~ChoiceStorage() noexcept {}" in header
    assert "} choice;" in header
    assert "typename Config::String text;" in header
    assert "::protocyte::i32 count;" in header
    assert "typename Config::template Optional<::demo::Carrier_Inner<Config>> inner;" in header
    assert "new (&choice.text) typename Config::String {::protocyte::move(temp)};" in header
    assert "new (&choice.count)::protocyte::i32 {value};" in header
    assert "new (&choice.inner) typename Config::template Optional<::demo::Carrier_Inner<Config>> {};" in header
    assert "new (&choice.none)::protocyte::u8(0u);" not in header
    assert "::protocyte::u8 none;" not in header
    assert "auto ensured = ensure_inner();" in header
    assert "clear_choice();" in header
    assert "choice_case_ == ChoiceCase::text" in header
    assert "choice_case_ == ChoiceCase::inner" in header
    assert "::protocyte::i32 before_ {};" in protected
    assert "::protocyte::i32 after_ {};" in protected
    assert protected.index("::protocyte::i32 before_ {};") < protected.index("ChoiceCase choice_case_ {ChoiceCase::none};")
    assert protected.index("ChoiceCase choice_case_ {ChoiceCase::none};") < protected.index("union ChoiceStorage {")
    assert protected.index("} choice;") < protected.index("::protocyte::i32 after_ {};")
    assert "typename Config::String text = " not in header


def test_empty_message_comments_unused_writer_and_returns_zero_size() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("empty.proto")
    request.proto_file.append(_empty_file())

    response = generate_response(request)

    assert not response.error
    header = next(file.content for file in response.file if file.name == "empty.protocyte.hpp")

    assert "RuntimeStatus serialize(Writer & /* writer */) const noexcept {" in header
    assert "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {" in header
    assert "::protocyte::usize total {};" not in header
    assert "return ::protocyte::Result<::protocyte::usize>::ok({});" in header


def test_generated_header_keeps_runtime_status_globally_qualified() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("namespaced.proto")
    request.proto_file.append(_protocyte_package_file())

    response = generate_response(request)

    assert not response.error
    header = next(file.content for file in response.file if file.name == "namespaced.protocyte.hpp")

    assert "namespace test::protocyte {" in header
    assert "using RuntimeStatus = ::protocyte::Status;" in header
    assert "RuntimeStatus merge_from(Reader &reader) noexcept {" in header
    assert "RuntimeStatus serialize(Writer &writer) const noexcept {" in header


def test_repo_root_options_proto_matches_generator_copy() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    root_copy = repo_root / "protocyte" / "options.proto"
    source_copy = repo_root / "src" / "protocyte" / "proto" / "protocyte" / "options.proto"

    assert root_copy.read_text(encoding="utf-8") == source_copy.read_text(encoding="utf-8")


def _simple_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "simple.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Sample"

    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    message.oneof_decl.add().name = "_opt_name"
    field = message.field.add()
    field.name = "opt_name"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field.proto3_optional = True
    field.oneof_index = 0

    entry = message.nested_type.add()
    entry.name = "ItemsEntry"
    entry.options.map_entry = True
    key = entry.field.add()
    key.name = "key"
    key.number = 1
    key.label = F.LABEL_OPTIONAL
    key.type = F.TYPE_STRING
    value = entry.field.add()
    value.name = "value"
    value.number = 2
    value.label = F.LABEL_OPTIONAL
    value.type = F.TYPE_INT32

    message_entry = message.nested_type.add()
    message_entry.name = "MessageItemsEntry"
    message_entry.options.map_entry = True
    key = message_entry.field.add()
    key.name = "key"
    key.number = 1
    key.label = F.LABEL_OPTIONAL
    key.type = F.TYPE_STRING
    value = message_entry.field.add()
    value.name = "value"
    value.number = 2
    value.label = F.LABEL_OPTIONAL
    value.type = F.TYPE_MESSAGE
    value.type_name = ".demo.Sample"

    field = message.field.add()
    field.name = "items"
    field.number = 3
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Sample.ItemsEntry"

    field = message.field.add()
    field.name = "samples"
    field.number = 5
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_FLOAT
    field.options.packed = True

    field = message.field.add()
    field.name = "message_items"
    field.number = 6
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Sample.MessageItemsEntry"

    field = message.field.add()
    field.name = "self"
    field.number = 4
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Sample"

    return file


def _fixed_size_request(
    *,
    field_type: int = F.TYPE_BYTES,
    label: int = F.LABEL_OPTIONAL,
) -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("fixed.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend([_fixed_size_options_file(), _fixed_size_file(field_type=field_type, label=label)])
    return request


def _oneof_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof.proto")
    request.proto_file.append(_oneof_file())
    return request


def _fixed_size_options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "protocyte/options.proto"
    file.package = "protocyte"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    ext = file.extension.add()
    ext.name = "fixed_size"
    ext.number = 50000
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_UINT32
    ext.extendee = ".google.protobuf.FieldOptions"

    return file


def _fixed_size_file(*, field_type: int, label: int) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "fixed.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "FixedBytes"

    field = message.field.add()
    field.name = "sha256"
    field.number = 1
    field.label = label
    field.type = field_type
    field.options.ParseFromString(_fixed_size_option_bytes(32))

    return file


def _oneof_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "oneof.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Carrier"

    inner = message.nested_type.add()
    inner.name = "Inner"
    field = inner.field.add()
    field.name = "value"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    message.oneof_decl.add().name = "choice"

    field = message.field.add()
    field.name = "before"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    field = message.field.add()
    field.name = "text"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field.oneof_index = 0

    field = message.field.add()
    field.name = "count"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    field.oneof_index = 0

    field = message.field.add()
    field.name = "inner"
    field.number = 4
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Carrier.Inner"
    field.oneof_index = 0

    field = message.field.add()
    field.name = "after"
    field.number = 5
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    return file


def _empty_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "empty.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Empty"

    return file


def _protocyte_package_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "namespaced.proto"
    file.package = "test.protocyte"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "StatusHolder"

    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    return file


def _fixed_size_option_bytes(size: int) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_fixed_size_options_file())
    field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    field_options_cls = message_factory.GetMessageClass(field_options_desc)
    fixed_size = pool.FindExtensionByName("protocyte.fixed_size")

    options = field_options_cls()
    options.Extensions[fixed_size] = size
    return options.SerializeToString()
