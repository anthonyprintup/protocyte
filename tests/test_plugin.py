from pathlib import Path
from types import SimpleNamespace

import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

from protocyte.model import ProtocyteError, _build_constants, _build_field, build_model
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
    assert "return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());" in header
    assert "::protocyte::LimitedReader nested {entry_reader" in header
    assert "::protocyte::ReaderRef sub_reader {sub};" in header
    assert "merge_from(sub_reader);" in header
    assert "::protocyte::ReaderRef nested_reader {nested};" in header
    assert "clear_items();" in header
    assert "other.items().for_each([&](const auto &key, const auto &value) noexcept {" in header
    assert "clear_samples();" in header
    assert "mutable_samples().push_back(other.samples()[i])" in header
    assert "clear_message_items();" in header
    assert "copied_value.copy_from(value)" in header


def test_checked_smoke_output_reflects_copy_propagation() -> None:
    header = (Path(__file__).resolve().parents[1] / "smoke" / "generated" / "example.protocyte.hpp").read_text(
        encoding="utf-8"
    )

    assert "copy_from(const UltimateComplexMessage &other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "clear_r_int32_unpacked();" in header
    assert "clear_r_int32_packed();" in header
    assert "clear_r_double();" in header
    assert "clear_map_str_int32();" in header
    assert "other.map_str_int32().for_each([&](const auto &key, const auto &value) noexcept {" in header
    assert "clear_map_uint64_msg();" in header
    assert "other.map_uint64_msg().for_each([&](const auto &key, const auto &value) noexcept {" in header
    assert "copied_value.copy_from(value)" in header
    assert "::protocyte::Result<UltimateComplexMessage> clone() const noexcept" in header
    assert "if (const auto st = out.value().copy_from(*this); !st) {" in header


def test_model_decodes_constants_and_array_options() -> None:
    model = build_model(_constant_array_request())

    holder = model.messages["demo.Holder"]
    nested = model.messages["demo.Holder.Nested"]
    constants = {constant.name: constant for constant in holder.constants}
    nested_constants = {constant.name: constant for constant in nested.constants}
    fields = {field.name: field for field in holder.fields}
    nested_fields = {field.name: field for field in nested.fields}

    assert constants["MAGIC_NUMBER"].value == 16
    assert constants["DOUBLE_MAGIC"].value == 32
    assert constants["HEX_MAGIC"].value == 32
    assert constants["HEX_EXPR"].value == 24
    assert constants["LABEL"].value == "ell"
    assert nested_constants["HAS_PREFIX"].value is True
    assert fields["digest"].array_max == 32
    assert fields["digest"].array_fixed is True
    assert fields["blob"].array_max == 16
    assert fields["hex_blob"].array_max == 16
    assert fields["hex_blob"].array_cpp_max == "0x8u + 0x8u"
    assert fields["values"].array_max == 4
    assert fields["values"].repeated_array is True
    assert nested_fields["payload"].array_max == 32


def test_generated_header_emits_constants_and_array_storage() -> None:
    response = generate_response(_constant_array_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["arrays.protocyte.hpp"]
    runtime_header = files["protocyte/runtime/runtime.hpp"]

    assert "#include <string_view>" in header
    assert "static constexpr ::protocyte::i32 MAGIC_NUMBER {16};" in header
    assert "static constexpr ::protocyte::i32 DOUBLE_MAGIC {32};" in header
    assert "static constexpr ::protocyte::u32 HEX_MAGIC {32u};" in header
    assert "static constexpr ::protocyte::i32 HEX_EXPR {24};" in header
    assert 'static constexpr ::std::string_view LABEL {"ell", 3u};' in header
    assert "static constexpr bool HAS_PREFIX {true};" in header
    assert "::protocyte::FixedByteArray<DOUBLE_MAGIC> digest_;" in header
    assert "::protocyte::ByteArray<16u> blob_;" in header
    assert "::protocyte::ByteArray<0x8u + 0x8u> hex_blob_;" in header
    assert "::protocyte::Array<::protocyte::i32, 4u> values_;" in header
    assert "bool has_digest() const noexcept { return digest_.has_value(); }" in header
    assert "::protocyte::MutableByteView mutable_digest() noexcept { return digest_.mutable_view(); }" in header
    assert "::protocyte::usize digest_size() const noexcept" not in header
    assert "digest_max_size" not in header
    assert "::protocyte::Status resize_blob(const ::protocyte::usize size) noexcept" in header
    assert "::protocyte::ByteView digest() const noexcept { return digest_.view(); }" in header
    assert "if (len.value() != DOUBLE_MAGIC)" in header
    assert "if (!(values_.size() == 4u)) {" in header
    assert "template<class T, usize Max> struct Array" in runtime_header
    assert "template<usize Max> struct ByteArray" in runtime_header
    assert "template<usize Max> struct FixedByteArray" in runtime_header


def test_generated_header_copies_and_moves_bounded_arrays() -> None:
    response = generate_response(_constant_array_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["arrays.protocyte.hpp"]
    runtime_header = files["protocyte/runtime/runtime.hpp"]

    assert "if (other.has_digest()) {" in header
    assert "set_digest(other.digest())" in header
    assert "set_blob(other.blob())" in header
    assert "set_hex_blob(other.hex_blob())" in header
    assert "clear_values();" in header
    assert "for (::protocyte::usize i {}; i < other.values().size(); ++i) {" in header
    assert "mutable_values().push_back(other.values()[i])" in header
    assert "Array(Array &&other) noexcept" in runtime_header
    assert "Array &operator=(Array &&other) noexcept" in runtime_header
    assert "ByteArray(ByteArray &&other) noexcept" in runtime_header
    assert "ByteArray &operator=(ByteArray &&other) noexcept" in runtime_header
    assert "FixedByteArray(FixedByteArray &&other) noexcept" in runtime_header
    assert "FixedByteArray &operator=(FixedByteArray &&other) noexcept" in runtime_header


@pytest.mark.parametrize(
    ("expected", "request_factory"),
    [
        ("unsupported constant kind", lambda: _unsupported_constant_kind_request()),
        ("constant name must not be empty", lambda: _empty_constant_name_request()),
        ("protocyte.fixed requires protocyte.array", lambda: _fixed_without_array_request()),
        ("protocyte.array is not supported on map fields", lambda: _array_on_map_request()),
        ("protocyte.array.max must be greater than zero", lambda: _zero_max_request()),
        ("protocyte.array.expr must not be empty", lambda: _empty_expr_request()),
    ],
)
def test_rejects_remaining_model_validator_branches(expected: str, request_factory) -> None:
    response = generate_response(request_factory())

    assert expected in response.error


def test_rejects_constant_and_array_exclusivity_branches() -> None:
    owner = SimpleNamespace(full_name="demo.Broken", descriptor=descriptor_pb2.DescriptorProto())

    constant_options = SimpleNamespace(
        message_constants=lambda options: [SimpleNamespace(name="BROKEN", kind=2, literal="1", expr="2")]
    )
    with pytest.raises(ProtocyteError, match="exactly one of literal or expr must be set"):
        _build_constants(owner, constant_options)

    array_field = descriptor_pb2.FieldDescriptorProto()
    array_field.name = "digest"
    array_field.number = 1
    array_field.label = F.LABEL_OPTIONAL
    array_field.type = F.TYPE_BYTES

    array_options = SimpleNamespace(field_array=lambda options: (4, "2", False))
    with pytest.raises(ProtocyteError, match="protocyte.array requires exactly one of max or expr"):
        _build_field(owner, array_field, {}, {}, array_options)


def test_rejects_invalid_constant_cpp_identifier() -> None:
    response = generate_response(_invalid_cpp_identifier_request())

    assert "constant name is not a valid C++ identifier" in response.error


def test_generated_header_copies_oneof_state() -> None:
    response = generate_response(_oneof_request())

    assert not response.error
    header = next(item.content for item in response.file if item.name == "oneof.protocyte.hpp")

    assert "if (this == &other) {" in header
    assert "return ::protocyte::Status::ok();" in header
    assert "switch (other.choice_case_) {" in header
    assert "case ChoiceCase::text: {" in header
    assert "if (const auto st = set_text(other.text()); !st) {" in header
    assert "return st;" in header
    assert "if (auto ensured = ensure_inner(); !ensured) {" in header
    assert "ensured.value().get().copy_from(*other.inner())" in header
    assert "clear_choice();" in header


def test_generated_header_uses_other_for_repeated_array_only_copy() -> None:
    response = generate_response(_repeated_array_only_request())

    assert not response.error
    header = next(item.content for item in response.file if item.name == "repeated_array_only.protocyte.hpp")

    assert "copy_from(const OnlyArrays &other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "return ::protocyte::Status::ok();" in header
    assert "clear_values();" in header
    assert "for (::protocyte::usize i {}; i < other.values().size(); ++i) {" in header
    assert "mutable_values().push_back(other.values()[i])" in header


def test_generated_header_uses_real_other_for_map_only_copy() -> None:
    response = generate_response(_map_only_request())

    assert not response.error
    header = next(item.content for item in response.file if item.name == "map_only.protocyte.hpp")

    assert "copy_from(const OnlyMaps &other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "const auto &source = other;" in header
    assert "clear_items();" in header
    assert "source.items().for_each([&](const auto &key, const auto &value) noexcept {" in header
    assert "auto copied_value = value;" in header
    assert "if (const auto st = out.value().copy_from(*this); !st) {" in header


def test_rejects_invalid_hex_numeric_literals() -> None:
    response = generate_response(_invalid_hex_request())

    assert "invalid numeric literal '0x'" in response.error


def test_resolves_constants_across_messages() -> None:
    model = build_model(_cross_message_request())
    source = model.messages["demo.Source"]
    sink = model.messages["demo.Sink"]
    nested = model.messages["demo.Sink.Nested"]

    source_constants = {constant.name: constant for constant in source.constants}
    sink_constants = {constant.name: constant for constant in sink.constants}
    nested_constants = {constant.name: constant for constant in nested.constants}
    sink_fields = {field.name: field for field in sink.fields}
    nested_fields = {field.name: field for field in nested.fields}

    assert source_constants["ROOT_CAP"].value == 6
    assert source_constants["ROOT_LABEL"].value == "cross"
    assert source_constants["ROOT_ENABLED"].value is True
    assert sink_constants["MIRRORED_CAP"].value == 18
    assert sink_constants["DIRECT_CAP"].value == 8
    assert sink_constants["PREFIX"].value == "cross-sink"
    assert sink_constants["READY"].value is True
    assert nested_constants["NESTED_CAP"].value == 9
    assert sink_fields["payload"].array_max == 8
    assert sink_fields["values"].array_max == 18
    assert sink_fields["values"].array_cpp_max == "MIRRORED_CAP"
    assert nested_fields["nested_payload"].array_max == 9
    assert nested_fields["nested_payload"].array_cpp_max == "NESTED_CAP"


def test_generated_header_emits_cross_message_constant_arrays() -> None:
    response = generate_response(_cross_message_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["cross.protocyte.hpp"]

    assert "static constexpr ::protocyte::u32 ROOT_CAP {6u};" in header
    assert 'static constexpr ::std::string_view ROOT_LABEL {"cross", 5u};' in header
    assert "static constexpr bool ROOT_ENABLED {true};" in header
    assert "static constexpr ::protocyte::u32 MIRRORED_CAP {18u};" in header
    assert "static constexpr ::protocyte::u32 DIRECT_CAP {8u};" in header
    assert 'static constexpr ::std::string_view PREFIX {"cross-sink", 10u};' in header
    assert "static constexpr bool READY {true};" in header
    assert "::protocyte::ByteArray<6u + 2u> payload_;" in header
    assert "::protocyte::Array<::protocyte::i32, MIRRORED_CAP> values_;" in header
    assert "::protocyte::ByteArray<NESTED_CAP> nested_payload_;" in header


def test_canonicalizes_floatish_array_bounds() -> None:
    model = build_model(_floatish_bound_request())
    field = model.messages["demo.Sample"].fields[0]

    assert field.array_max == 2
    assert field.array_cpp_max == "2u"

    response = generate_response(_floatish_bound_request())

    assert not response.error
    header = next(file.content for file in response.file if file.name == "float_bound.protocyte.hpp")
    assert "::protocyte::ByteArray<2u> data_;" in header
    assert "return 2u;" in header
    assert "2.0" not in header


def test_generated_header_emits_utf8_string_constants() -> None:
    response = generate_response(_unicode_constant_request())

    assert not response.error
    header = next(file.content for file in response.file if file.name == "unicode.protocyte.hpp")
    assert '#include <string_view>' in header
    assert 'static constexpr ::std::string_view NAME {"\\xc4"' in header
    assert '"\\x80"' in header
    assert '"\\xc3"' in header
    assert '"\\xa9",' in header
    assert "4u};" in header


def test_rejects_invalid_array_targets_and_constant_cycles() -> None:
    bad_type_response = generate_response(_invalid_array_request())
    cycle_response = generate_response(_constant_cycle_request())

    assert "only supported on bytes or repeated fields" in bad_type_response.error
    assert "cycle detected" in cycle_response.error


def test_rejects_constant_name_collisions() -> None:
    duplicate_response = generate_response(_constant_collision_request("duplicate.proto", [("dup", 2, "1", None), ("dup", 2, "2", None)]))
    normalized_response = generate_response(
        _constant_collision_request("normalized.proto", [("cap-value", 2, "1", None), ("cap_value", 2, "2", None)])
    )
    reserved_response = generate_response(_constant_collision_request("reserved.proto", [("create", 2, "1", None)]))

    assert "constant cannot be redefined" in duplicate_response.error
    assert "collides after C++ identifier normalization" in normalized_response.error
    assert "collides with generated API" in reserved_response.error


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


def test_generated_header_parses_bounded_oneof_bytes() -> None:
    response = generate_response(_oneof_array_request())

    assert not response.error
    header = next(file.content for file in response.file if file.name == "oneof_array.protocyte.hpp")
    assert "new (&choice.data)::protocyte::ByteArray<8u> {};" in header
    assert "choice_case_ = ChoiceCase::data;" in header
    assert "if (const auto st = choice.data.resize(static_cast<::protocyte::usize>(len.value())); !st) {" in header
    assert "if (const auto st = reader.read(choice.data.data(), choice.data.size()); !st) {" in header
    assert "new (&choice.data)::protocyte::ByteArray<8u> {ctx_};" not in header


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


def _constant_array_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("arrays.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend([_options_file(), _constant_array_file()])
    return request


def _invalid_array_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("invalid_array.proto")
    request.proto_file.extend([_options_file(), _invalid_array_file()])
    return request


def _constant_cycle_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("cycle.proto")
    request.proto_file.extend([_options_file(), _constant_cycle_file()])
    return request


def _cross_message_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("cross.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend([_options_file(), _cross_message_file()])
    return request


def _oneof_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof.proto")
    request.proto_file.append(_oneof_file())
    return request


def _oneof_array_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof_array.proto")
    request.proto_file.extend([_options_file(), _oneof_file(array_bytes=True)])
    return request


def _repeated_array_only_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("repeated_array_only.proto")
    request.proto_file.extend([_options_file(), _repeated_array_only_file()])
    return request


def _map_only_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("map_only.proto")
    request.proto_file.extend([_options_file(), _map_only_file()])
    return request


def _unsupported_constant_kind_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("unsupported_constant_kind.proto")
    request.proto_file.extend([_options_file(), _unsupported_constant_kind_file()])
    return request


def _empty_constant_name_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("empty_constant_name.proto")
    request.proto_file.extend([_options_file(), _empty_constant_name_file()])
    return request


def _constant_literal_expr_conflict_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("constant_literal_expr_conflict.proto")
    request.proto_file.extend([_options_file(), _constant_literal_expr_conflict_file()])
    return request


def _fixed_without_array_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("fixed_without_array.proto")
    request.proto_file.extend([_options_file(), _fixed_without_array_file()])
    return request


def _array_with_max_and_expr_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("array_with_max_and_expr.proto")
    request.proto_file.extend([_options_file(), _array_with_max_and_expr_file()])
    return request


def _array_on_map_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("array_on_map.proto")
    request.proto_file.extend([_options_file(), _array_on_map_file()])
    return request


def _zero_max_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("zero_max.proto")
    request.proto_file.extend([_options_file(), _zero_max_file()])
    return request


def _empty_expr_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("empty_expr.proto")
    request.proto_file.extend([_options_file(), _empty_expr_file()])
    return request


def _constant_collision_request(
    file_name: str,
    constants: list[tuple[str, int, str | None, str | None]],
) -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(file_name)
    request.proto_file.extend([_options_file(), _constant_collision_file(file_name, constants)])
    return request


def _invalid_cpp_identifier_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("invalid_cpp_identifier.proto")
    request.proto_file.extend([_options_file(), _invalid_cpp_identifier_file()])
    return request


def _options_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "protocyte/options.proto"
    file.package = "protocyte"
    file.syntax = "proto3"
    file.dependency.append("google/protobuf/descriptor.proto")

    enum = file.enum_type.add()
    enum.name = "ConstantKind"
    for number, name in [
        (0, "KIND_UNSPECIFIED"),
        (1, "BOOL"),
        (2, "INT32"),
        (3, "INT64"),
        (4, "UINT32"),
        (5, "UINT64"),
        (6, "FLOAT"),
        (7, "DOUBLE"),
        (8, "STRING"),
    ]:
        value = enum.value.add()
        value.name = name
        value.number = number

    struct_constant = file.message_type.add()
    struct_constant.name = "StructConstant"
    field = struct_constant.field.add()
    field.name = "name"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field = struct_constant.field.add()
    field.name = "kind"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_ENUM
    field.type_name = ".protocyte.ConstantKind"
    _add_oneof_field(struct_constant, "value", "literal", 3, F.TYPE_STRING)
    _add_oneof_field(struct_constant, "value", "expr", 4, F.TYPE_STRING)

    array_options = file.message_type.add()
    array_options.name = "ArrayOptions"
    _add_oneof_field(array_options, "bound", "max", 1, F.TYPE_UINT32)
    _add_oneof_field(array_options, "bound", "expr", 2, F.TYPE_STRING)

    ext = file.extension.add()
    ext.name = "constant"
    ext.number = 50000
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.StructConstant"
    ext.extendee = ".google.protobuf.MessageOptions"

    ext = file.extension.add()
    ext.name = "array"
    ext.number = 50000
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.ArrayOptions"
    ext.extendee = ".google.protobuf.FieldOptions"

    ext = file.extension.add()
    ext.name = "fixed"
    ext.number = 50001
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_BOOL
    ext.extendee = ".google.protobuf.FieldOptions"

    return file


def _constant_array_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "arrays.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Holder"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("MAGIC_NUMBER", 2, "16", None),
                ("DOUBLE_MAGIC", 2, None, "MAGIC_NUMBER * 2"),
                ("HEX_MAGIC", 4, "0x20", None),
                ("HEX_EXPR", 2, None, "0x10 + 0x8"),
                ("LABEL", 8, None, 'substr("hello", 1, 3)'),
            ]
        )
    )

    field = message.field.add()
    field.name = "digest"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="DOUBLE_MAGIC", fixed=True))

    field = message.field.add()
    field.name = "blob"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(max_value=16))

    field = message.field.add()
    field.name = "hex_blob"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="0x8 + 0x8"))

    field = message.field.add()
    field.name = "values"
    field.number = 4
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32
    field.options.ParseFromString(_array_option_bytes(max_value=4, fixed=True))

    nested = message.nested_type.add()
    nested.name = "Nested"
    nested.options.ParseFromString(
        _constant_options_bytes(
            [
                ("HAS_PREFIX", 1, None, 'starts_with(LABEL, "e")'),
            ]
        )
    )
    field = nested.field.add()
    field.name = "payload"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="Holder.DOUBLE_MAGIC"))

    field = message.field.add()
    field.name = "nested"
    field.number = 5
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Holder.Nested"

    return file


def _repeated_array_only_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "repeated_array_only.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "OnlyArrays"

    field = message.field.add()
    field.name = "values"
    field.number = 1
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32
    field.options.ParseFromString(_array_option_bytes(max_value=4, fixed=True))

    return file


def _map_only_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "map_only.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "OnlyMaps"

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

    field = message.field.add()
    field.name = "items"
    field.number = 1
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.OnlyMaps.ItemsEntry"

    return file


def _unsupported_constant_kind_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "unsupported_constant_kind.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes([("BROKEN", 99, "1", None)]))
    return file


def _empty_constant_name_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "empty_constant_name.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes([("", 2, "1", None)]))
    return file


def _constant_literal_expr_conflict_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "constant_literal_expr_conflict.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes([("BROKEN", 2, "1", "2")]))
    return file


def _fixed_without_array_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "fixed_without_array.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    field = message.field.add()
    field.name = "digest"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(fixed=True))
    return file


def _array_with_max_and_expr_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "array_with_max_and_expr.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    field = message.field.add()
    field.name = "digest"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(max_value=4, expr="2"))
    return file


def _array_on_map_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "array_on_map.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
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

    field = message.field.add()
    field.name = "items"
    field.number = 1
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Broken.ItemsEntry"
    field.options.ParseFromString(_array_option_bytes(max_value=4))
    return file


def _zero_max_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "zero_max.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    field = message.field.add()
    field.name = "digest"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(max_value=0))
    return file


def _empty_expr_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "empty_expr.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    field = message.field.add()
    field.name = "digest"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr=""))
    return file


def _invalid_array_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "invalid_array.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    field.options.ParseFromString(_array_option_bytes(max_value=8))
    return file


def _constant_collision_file(
    file_name: str,
    constants: list[tuple[str, int, str | None, str | None]],
) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = file_name
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes(constants))
    return file


def _invalid_cpp_identifier_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "invalid_cpp_identifier.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes([("1", 2, "1", None)]))
    return file


def _constant_cycle_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "cycle.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Cycle"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("A", 2, None, "B + 1"),
                ("B", 2, None, "A + 1"),
            ]
        )
    )
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="A"))
    return file


def _invalid_hex_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("invalid_hex.proto")
    request.proto_file.extend([_options_file(), _invalid_hex_file()])
    return request


def _floatish_bound_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("float_bound.proto")
    request.proto_file.extend([_options_file(), _floatish_bound_file()])
    return request


def _unicode_constant_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("unicode.proto")
    request.proto_file.extend([_options_file(), _unicode_constant_file()])
    return request


def _invalid_hex_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "invalid_hex.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "InvalidHex"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("BROKEN", 2, None, "0x + 1"),
            ]
        )
    )
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="BROKEN"))
    return file


def _floatish_bound_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "float_bound.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Sample"
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="4 / 2.0"))
    return file


def _unicode_constant_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "unicode.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Words"
    message.options.ParseFromString(_constant_options_bytes([("NAME", 8, chr(0x0100) + chr(0x00E9), None)]))
    return file


def _oneof_file(*, array_bytes: bool = False) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "oneof_array.proto" if array_bytes else "oneof.proto"
    file.package = "demo"
    file.syntax = "proto3"
    if array_bytes:
        file.dependency.append("protocyte/options.proto")

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

    if array_bytes:
        field = message.field.add()
        field.name = "data"
        field.number = 6
        field.label = F.LABEL_OPTIONAL
        field.type = F.TYPE_BYTES
        field.oneof_index = 0
        field.options.ParseFromString(_array_option_bytes(max_value=8))

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


def _cross_message_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "cross.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    source = file.message_type.add()
    source.name = "Source"
    source.options.ParseFromString(
        _constant_options_bytes(
            [
                ("ROOT_CAP", 4, "6", None),
                ("ROOT_LABEL", 8, None, 'substr("crossing", 0, 5)'),
                ("ROOT_ENABLED", 1, None, 'starts_with(ROOT_LABEL, "cr")'),
            ]
        )
    )

    sink = file.message_type.add()
    sink.name = "Sink"
    sink.options.ParseFromString(
        _constant_options_bytes(
            [
                ("MIRRORED_CAP", 4, None, "Source.ROOT_CAP * 3"),
                ("DIRECT_CAP", 4, None, "Source.ROOT_CAP + 2"),
                ("PREFIX", 8, None, 'Source.ROOT_LABEL + "-sink"'),
                ("READY", 1, None, "Source.ROOT_ENABLED && (MIRRORED_CAP == 18)"),
            ]
        )
    )

    field = sink.field.add()
    field.name = "payload"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="Source.ROOT_CAP + 2"))

    field = sink.field.add()
    field.name = "values"
    field.number = 2
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32
    field.options.ParseFromString(_array_option_bytes(expr="MIRRORED_CAP"))

    nested = sink.nested_type.add()
    nested.name = "Nested"
    nested.options.ParseFromString(
        _constant_options_bytes(
            [
                ("NESTED_CAP", 4, None, "Source.ROOT_CAP + 3"),
            ]
        )
    )
    field = nested.field.add()
    field.name = "nested_payload"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="NESTED_CAP"))

    field = sink.field.add()
    field.name = "nested"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Sink.Nested"

    return file


def _add_oneof_field(
    message: descriptor_pb2.DescriptorProto,
    oneof_name: str,
    name: str,
    number: int,
    field_type: int,
) -> None:
    oneof_index: int | None = None
    for index, oneof in enumerate(message.oneof_decl):
        if oneof.name == oneof_name:
            oneof_index = index
            break
    if oneof_index is None:
        oneof = message.oneof_decl.add()
        oneof.name = oneof_name
        oneof_index = len(message.oneof_decl) - 1

    field = message.field.add()
    field.name = name
    field.number = number
    field.label = F.LABEL_OPTIONAL
    field.type = field_type
    field.oneof_index = oneof_index


def _constant_options_bytes(
    constants: list[tuple[str, int, str | None, str | None]],
) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_options_file())
    message_options_desc = pool.FindMessageTypeByName("google.protobuf.MessageOptions")
    message_options_cls = message_factory.GetMessageClass(message_options_desc)
    constant_ext = pool.FindExtensionByName("protocyte.constant")

    options = message_options_cls()
    for name, kind, literal, expr in constants:
        item = options.Extensions[constant_ext].add()
        item.name = name
        item.kind = kind
        if literal is not None:
            item.literal = literal
        if expr is not None:
            item.expr = expr
    return options.SerializeToString()


def _array_option_bytes(
    *,
    max_value: int | None = None,
    expr: str | None = None,
    fixed: bool = False,
) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_options_file())
    field_options_desc = pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    field_options_cls = message_factory.GetMessageClass(field_options_desc)
    array_ext = pool.FindExtensionByName("protocyte.array")
    fixed_ext = pool.FindExtensionByName("protocyte.fixed")

    options = field_options_cls()
    array_options = options.Extensions[array_ext]
    if max_value is not None:
        array_options.max = max_value
    if expr is not None:
        array_options.expr = expr
    if fixed:
        options.Extensions[fixed_ext] = True
    return options.SerializeToString()
