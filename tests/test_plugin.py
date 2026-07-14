import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

import protocyte.cpp as protocyte_cpp
import protocyte.plugin as protocyte_plugin
from protocyte.cpp import CppWriter
from protocyte.model import (
    CONSTANT_KIND_BOOL,
    CONSTANT_KIND_DOUBLE,
    CONSTANT_KIND_FLOAT,
    CONSTANT_KIND_INT32,
    CONSTANT_KIND_INT64,
    CONSTANT_KIND_STRING,
    CONSTANT_KIND_UINT32,
    CONSTANT_KIND_UINT64,
    ProtocyteError,
    _ExprParser,
    _MAX_CONSTANT_DEPENDENCY_DEPTH,
    _MAX_EXPRESSION_NESTING,
    _TypedValue,
    _build_constants,
    _build_field,
    _coerce_expression_value,
    _coerce_literal,
    _is_packed,
    build_model,
)
from protocyte.plugin import GeneratorPolicy, generate_response
from protocyte.runtime import runtime_files


F = descriptor_pb2.FieldDescriptorProto


def _basic_request(*, parameter: str = "") -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("simple.proto")
    request.parameter = parameter
    request.proto_file.append(_simple_file())
    return request


@pytest.fixture(autouse=True)
def _disable_implicit_clang_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(protocyte_cpp.shutil, "which", lambda name: None)


def test_runtime_files_load_packaged_sources() -> None:
    files = runtime_files()

    assert set(files) == {"protocyte/runtime/runtime.hpp"}
    assert files["protocyte/runtime/runtime.hpp"].startswith("#pragma once\n")


def test_runtime_files_reject_parent_relative_prefix() -> None:
    with pytest.raises(ProtocyteError, match="runtime prefix"):
        runtime_files("../escaped")


def test_runtime_files_reject_explicit_empty_prefix() -> None:
    with pytest.raises(ProtocyteError, match="runtime prefix must not be empty"):
        runtime_files("")


def test_response_file_names_keep_valid_runtime_prefix_relative() -> None:
    response = generate_response(
        _basic_request(parameter="runtime=emit:vendor/protocyte")
    )

    assert not response.error
    assert {file.name for file in response.file} == {
        "simple.protocyte.cpp",
        "simple.protocyte.hpp",
        "vendor/protocyte/runtime.hpp",
    }


def test_rejects_obsolete_protocyte_options_schema() -> None:
    response = generate_response(_obsolete_fixed_size_request())

    assert "obsolete or unsupported Protocyte options schema" in response.error
    assert not response.file


def test_rejects_protocyte_options_from_noncanonical_descriptor() -> None:
    forged_options = _options_file()
    forged_options.name = "forged/options.proto"
    array_options = next(
        message
        for message in forged_options.message_type
        if message.name == "ArrayOptions"
    )
    next(field for field in array_options.field if field.name == "max").type = F.TYPE_UINT64
    array_extension = descriptor_pb2.FieldDescriptorProto()
    array_extension.CopyFrom(
        next(
            extension
            for extension in forged_options.extension
            if extension.name == "array"
        )
    )
    del forged_options.extension[:]
    forged_options.extension.add().CopyFrom(array_extension)

    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(forged_options)
    field_options_cls = message_factory.GetMessageClass(
        pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    )
    field_options = field_options_cls()
    field_options.Extensions[pool.FindExtensionByName("protocyte.array")].max = 1 << 40

    source = descriptor_pb2.FileDescriptorProto()
    source.name = "forged_user.proto"
    source.package = "demo"
    source.syntax = "proto3"
    source.dependency.append(forged_options.name)
    message = source.message_type.add()
    message.name = "Holder"
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(field_options.SerializeToString())

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(source.name)
    request.proto_file.extend([forged_options, source])
    response = generate_response(request)

    assert response.error == (
        "forged/options.proto: Protocyte option extension protocyte.array must be "
        "declared by protocyte/options.proto"
    )
    assert not response.file


@pytest.mark.parametrize("oneof_index", [-1, 1])
def test_invalid_oneof_indices_return_descriptor_errors(oneof_index: int) -> None:
    request = _basic_request()
    request.proto_file[0].message_type[0].field[0].oneof_index = oneof_index

    response = generate_response(request)

    assert response.error == (
        f"demo.Sample.id: oneof_index {oneof_index} is outside the message's "
        "1 oneof declaration(s)"
    )
    assert not response.file


def test_malformed_recognized_option_payload_returns_descriptor_error() -> None:
    source = _simple_file()
    source.dependency.append("protocyte/options.proto")
    source.message_type[0].field[0].options.ParseFromString(
        bytes.fromhex("82b5180180")
    )
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(source.name)
    request.proto_file.extend([_options_file(), source])

    response = generate_response(request)

    assert response.error.startswith(
        "demo.Sample.id: malformed protocyte.array option payload:"
    )
    assert "DecodeError" not in response.error
    assert not response.file


def test_unexpected_generator_exception_returns_diagnostic_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_build_model(request: object) -> None:
        del request
        raise RuntimeError("descriptor registry exploded")

    monkeypatch.setattr(protocyte_plugin, "build_model", fail_build_model)

    response = generate_response(_basic_request())

    assert response.error == (
        "internal Protocyte error while building the descriptor model (RuntimeError): "
        "descriptor registry exploded"
    )
    assert not response.file


def test_runtime_rejects_unmatched_end_group_in_skip_field() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    assert (
        "case WireType::EGROUP:\n"
        "                return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field_number);"
    ) in runtime_header
    assert "case WireType::EGROUP: return {};" not in runtime_header


def test_runtime_varint_read_helpers_use_direct_fast_paths() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    read_varint_body = runtime_header.split(
        "template<class Reader> Result<u64> read_varint(Reader &reader) noexcept {",
        maxsplit=1,
    )[1].split("template<class Writer> Status write_varint", maxsplit=1)[0]
    length_body = runtime_header.split(
        "template<class Reader> Result<usize> read_length_delimited_size(Reader &reader) noexcept {",
        maxsplit=1,
    )[1].split("template<class Config, class Reader>", maxsplit=1)[0]

    assert "const auto first = reader.read_byte();" in read_varint_body
    assert "if ((*first & 0x80u) == 0u)" in read_varint_body
    assert "const auto len = read_varint(reader);" in length_body
    assert "return read_varint(reader).and_then" not in length_body


def test_runtime_length_delimited_parse_helpers_use_direct_checks() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    open_nested_sized_body = runtime_header.split(
        "open_nested_message_sized(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader> Result<NestedMessageReader<Reader, Config>>",
        maxsplit=1,
    )[0]
    open_nested_body = runtime_header.split(
        "open_nested_message(typename Config::Context &ctx, Reader &reader, const u32 field_number) noexcept {",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader, class Message> Status", maxsplit=1
    )[0]
    read_message_partial_body = runtime_header.split(
        "read_message_partial(typename Config::Context &ctx, Reader &reader, const u32 field_number, Message &out) noexcept {",
        maxsplit=1,
    )[1].split("template<class Config, class Reader, class Message>", maxsplit=1)[0]
    read_message_body = runtime_header.split(
        "Status read_message(typename Config::Context &ctx, Reader &reader, const u32 field_number, Message &out) noexcept {",
        maxsplit=1,
    )[1].split("template<class Writer, class Message>", maxsplit=1)[0]
    skip_field_body = runtime_header.split(
        "template<class Config, class Reader> Status skip_field(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader>\n    Status skip_group",
        maxsplit=1,
    )[0]
    read_bytes_sized_body = runtime_header.split(
        "Status read_bytes_sized(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[1].split(
        "Status read_bytes(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[0]
    read_bytes_body = runtime_header.split(
        "Status read_bytes(typename Config::Context &ctx, Reader &reader, typename Config::Bytes &out) noexcept {",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader> Status read_bytes_field", maxsplit=1
    )[0]
    read_bytes_field_body = runtime_header.split(
        "Status read_bytes_field(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader> Status read_string_sized", maxsplit=1
    )[0]
    read_string_sized_body = runtime_header.split(
        "Status read_string_sized(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[1].split(
        "Status read_string(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[0]
    read_string_body = runtime_header.split(
        "Status read_string(typename Config::Context &ctx, Reader &reader, typename Config::String &out) noexcept {",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader> Status read_string_field", maxsplit=1
    )[0]
    read_string_field_body = runtime_header.split(
        "Status read_string_field(typename Config::Context &ctx, Reader &reader,",
        maxsplit=1,
    )[1].split("template<class Writer> Status write_bytes", maxsplit=1)[0]

    assert (
        "const auto st = push_recursion<Config>(ctx, reader.position(), field_number);"
        in open_nested_sized_body
    )
    assert ".transform(" not in open_nested_sized_body

    for body in (open_nested_body, skip_field_body, read_bytes_body, read_string_body):
        assert "const auto size = read_length_delimited_size(reader);" in body
        assert "read_length_delimited_size(reader).and_then" not in body

    for body, allocation in (
        (read_bytes_sized_body, "typename Config::Bytes temp"),
        (read_string_sized_body, "typename Config::String temp"),
    ):
        assert "reader.can_read(size)" in body
        assert body.index("reader.can_read(size)") < body.index(allocation)

    assert ".and_then" not in read_message_partial_body
    assert ".and_then" not in read_message_body
    assert (
        "MessageParseAccess::merge_fields_from(out, nested_reader)"
        in read_message_partial_body
    )
    assert "Message parsed {ctx};" in read_message_body
    assert "parsed.copy_from(out)" in read_message_body
    assert (
        "read_message_partial<Config>(ctx, reader, field_number, parsed)"
        in read_message_body
    )
    assert "parsed.validate()" in read_message_body
    assert "out = protocyte::move(parsed);" in read_message_body

    for body in (read_bytes_field_body, read_string_field_body):
        assert (
            "const auto st = expect_wire_type(reader, wire_type, WireType::LEN, field_number);"
            in body
        )
        assert (
            "expect_wire_type(reader, wire_type, WireType::LEN, field_number).and_then"
            not in body
        )


def test_runtime_scalar_copy_and_write_helpers_use_direct_checks() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    copy_helpers = runtime_header.split(
        "template<class T, class Context> Result<T> copy_value(Context *ctx, const T &value) noexcept {",
        maxsplit=1,
    )[1].split(
        "template<class T, class Context>\n    concept PointerContextConstructible",
        maxsplit=1,
    )[0]
    range_value_body = runtime_header.split(
        "template<class Source> Result<T> range_value_from(const Source &value) noexcept {",
        maxsplit=1,
    )[1].split("} else if constexpr (requires { T(value); })", maxsplit=1)[0]
    scalar_read_fields = runtime_header.split(
        "template<class Reader>\n    Result<i32> read_int32_field",
        maxsplit=1,
    )[1].split("template<class Writer> Status write_int32_field", maxsplit=1)[0]
    message_write_helpers = runtime_header.split(
        "template<class Writer, class Message>\n    Status write_message_field",
        maxsplit=1,
    )[1].split(
        "template<class Config, class Reader>\n    Status skip_group", maxsplit=1
    )[0]
    bytes_write_helpers = runtime_header.split(
        "template<class Writer> Status write_bytes(Writer &writer, const Span<const u8> view) noexcept {",
        maxsplit=1,
    )[1].split("template<class Writer>\n    Status write_string_field", maxsplit=1)[0]

    assert ".transform([&copied]" not in copy_helpers
    assert ".transform(\n                        [&copied]" not in range_value_body
    assert "auto copied = [&]() noexcept" not in runtime_header
    assert ".and_then([&reader]" not in scalar_read_fields
    assert ".and_then(" not in message_write_helpers
    assert ".and_then(" not in bytes_write_helpers


def test_kernel_smoke_provides_debug_string_view_crt_shims() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "smoke"
        / "src"
        / "kernel_driver_smoke.cpp"
    ).read_text()

    assert "#if PROTOCYTE_ENABLE_STD_STRING_VIEW && defined(_DEBUG)" in source
    assert "__imp__invoke_watson" in source
    assert "__imp__CrtDbgReport" in source
    assert "DbgPrintEx" in source
    assert "KeBugCheckEx" in source


def test_runtime_container_growth_checks_capacity_limits() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    assert (
        "static constexpr usize max_size() noexcept { return static_cast<usize>(~static_cast<usize>(0u)) / sizeof(T); }"
        in runtime_header
    )
    assert "if (size_ == max_size())" in runtime_header
    assert "const auto requested = checked_add(size_, 1u);" in runtime_header
    assert "if (!requested)" in runtime_header
    assert (
        "if (capacity_ > maximum - capacity_ / 2u) {\n"
        "                return maximum;\n"
        "            }\n"
        "            const usize geometric {capacity_ + capacity_ / 2u};"
    ) in runtime_header
    assert (
        "static constexpr usize max_size() noexcept { return Config::template Vector<Bucket>::max_size() / 2u; }"
        in runtime_header
    )
    assert "const usize target {count * 2u};" in runtime_header
    assert (
        "buckets_.empty() || *next_size >= rehash_threshold_for(buckets_.size())"
        in runtime_header
    )
    assert (
        "static constexpr usize rehash_threshold_for(const usize bucket_count) noexcept"
        in runtime_header
    )
    assert "capacity_ * 2u" not in runtime_header
    assert "checked_mul(count, 2u, &target)" not in runtime_header
    assert "checked_add(size_, 1u, &requested)" not in runtime_header
    assert "(size_ + 1u) * 10u" not in runtime_header
    assert "buckets_.size() * 7u" not in runtime_header


def test_runtime_sequence_containers_accept_spans() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]
    vector_body = runtime_header.split(
        "template<class T, class Config> struct Vector {", maxsplit=1
    )[1].split("template<class T, usize Max> struct Array {", maxsplit=1)[0]
    array_body = runtime_header.split(
        "template<class T, usize Max> struct Array {", maxsplit=1
    )[1].split("template<usize Max> using ByteArray = Array<u8, Max>;", maxsplit=1)[0]

    assert (
        "template<class T, usize Extent = dynamic_extent> struct Span" in runtime_header
    )
    assert "inline constexpr usize dynamic_extent" in runtime_header
    assert "static constexpr usize extent {Extent};" in runtime_header
    assert (
        "constexpr explicit(Extent != dynamic_extent) Span(pointer data, const usize size) noexcept"
        in runtime_header
    )
    assert "Pointer range constructors follow std::span" in runtime_header
    assert (
        "explicit(Extent != dynamic_extent && OtherExtent == dynamic_extent)"
        in runtime_header
    )
    assert "constexpr reference front() const noexcept" in runtime_header
    assert "constexpr reference back() const noexcept" in runtime_header
    assert (
        "template<usize Count> constexpr Span<T, Count> first() const noexcept"
        in runtime_header
    )
    assert "requires(Extent == dynamic_extent || Count <= Extent)" in runtime_header
    assert "constexpr Span<T> first(const usize count) const noexcept" in runtime_header
    assert (
        "template<usize Count> constexpr Span<T, Count> last() const noexcept"
        in runtime_header
    )
    assert "constexpr Span<T> last(const usize count) const noexcept" in runtime_header
    assert "constexpr auto subspan() const noexcept" in runtime_header
    assert (
        "Offset <= Extent && (Count == dynamic_extent || Count <= Extent - Offset)"
        in runtime_header
    )
    assert (
        "constexpr Span<T> subspan(const usize offset, const usize count = dynamic_extent) const noexcept"
        in runtime_header
    )
    assert (
        "constexpr auto as_bytes(const Span<T, Extent> view) noexcept" in runtime_header
    )
    assert (
        "constexpr auto as_writable_bytes(const Span<T, Extent> view) noexcept"
        in runtime_header
    )
    assert "concept SpanSource" in runtime_header
    assert "concept CheckedSpanSource" in runtime_header
    assert "concept ContainerCompatibleSpanSource" in runtime_header
    assert "concept DataSizeSpanSource" in runtime_header
    assert "concept PointerSpanSource" in runtime_header
    assert "concept ContiguousRange" not in runtime_header
    assert "contiguous_range_data" not in runtime_header
    assert "contiguous_range_size" not in runtime_header
    assert "const auto first_addr = reinterpret_cast<uptr>(first);" in runtime_header
    assert "const auto last_addr = reinterpret_cast<uptr>(last);" in runtime_header
    assert "if (!view.empty() && view.data() == nullptr)" in runtime_header
    assert "if (view.size() != 0u && view.data() == nullptr)" not in runtime_header
    assert "if (*size != 0u && value.data() == nullptr)" in runtime_header
    assert "if (last < first)" not in runtime_header
    assert (
        "template<class Range> Status assign(const Range &values) noexcept"
        in vector_body
    )
    assert (
        "template<class Range> Status append(const Range &values) noexcept"
        in vector_body
    )
    assert (
        "template<class Range> Status prepend(const Range &values) noexcept"
        in vector_body
    )
    assert (
        "requires(ContainerCompatibleSpanSource<T, const Range, Context>)"
        in vector_body
    )
    assert "const auto view = checked_span_of(values);" in vector_body
    assert "temp.append_range_data(view->data(), view->size())" in vector_body
    assert (
        "const usize target_capacity {capacity_ > *total ? capacity_ : *total};"
        in vector_body
    )
    assert "::std::memcpy(next, data_, size_ * sizeof(T));" in vector_body
    assert "::std::memcpy(&data_[size_], values, count * sizeof(T));" in vector_body
    assert (
        "if constexpr (::std::is_trivially_copyable_v<T>) {\n                return assign(other);\n            } else {"
        in vector_body
    )
    assert "if (*total > max_size())" in vector_body
    assert (
        "template<class Range> Status assign(const Range &values) noexcept"
        in array_body
    )
    assert (
        "template<class Range> Status append(const Range &values) noexcept"
        in array_body
    )
    assert (
        "template<class Range> Status prepend(const Range &values) noexcept"
        in array_body
    )
    assert (
        "requires(ContainerCompatibleSpanSource<T, const Range, Context>)" in array_body
    )
    assert "T *data() noexcept { return ptr(0u); }" in array_body
    assert "const T *data() const noexcept { return ptr(0u); }" in array_body
    assert "size_ ? ptr(0u) : nullptr" not in array_body
    assert "const auto view = checked_span_of(values);" in array_body
    assert "temp.append_range_data(view->data(), view->size())" in array_body
    assert "::std::memcpy(ptr(size_), values, count * sizeof(T));" in array_body
    assert (
        "if constexpr (::std::is_trivially_copyable_v<T>) {\n                return assign(other);\n            } else {"
        in array_body
    )
    assert "if (*total > Max)" in array_body


def test_runtime_byte_containers_use_bulk_copy_helpers() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]
    array_body = runtime_header.split(
        "template<class T, usize Max> struct Array {", maxsplit=1
    )[1].split("template<usize Max> using ByteArray = Array<u8, Max>;", maxsplit=1)[0]
    fixed_byte_array_body = runtime_header.split(
        "template<usize Max> struct FixedByteArray {", maxsplit=1
    )[1].split("template<class Config> struct Bytes {", maxsplit=1)[0]
    bytes_body = runtime_header.split(
        "template<class Config> struct Bytes {", maxsplit=1
    )[1].split("template<class Config> struct String {", maxsplit=1)[0]
    span_body = runtime_header.split(
        "template<class T, usize Extent> struct Span {", maxsplit=1
    )[1].split("template<class T> Span(T *, usize) -> Span<T>;", maxsplit=1)[0]
    string_body = runtime_header.split(
        "template<class Config> struct String {", maxsplit=1
    )[1].split("template<class T, class Config> struct Box {", maxsplit=1)[0]
    slice_reader_body = runtime_header.split("struct SliceReader {", maxsplit=1)[
        1
    ].split("struct ReaderRef {", maxsplit=1)[0]
    slice_writer_body = runtime_header.split("struct SliceWriter {", maxsplit=1)[
        1
    ].split("template<class Reader> Result<u64> read_varint", maxsplit=1)[0]

    assert "#include <cstring>" in runtime_header
    assert (
        "#if PROTOCYTE_ENABLE_STD_FORMAT\n#include <version>\n#if defined(__cpp_lib_format) && __cpp_lib_format >= 201907L\n#include <format>\n#endif\n#endif"
        in runtime_header
    )
    assert (
        "#if PROTOCYTE_ENABLE_STD_STRING_VIEW || PROTOCYTE_ENABLE_STD_FORMAT || PROTOCYTE_ENABLE_FMT_FORMAT\n#include <string_view>\n#endif"
        in runtime_header
    )
    assert "#ifdef PROTOCYTE_ENABLE_STD_STRING_VIEW" not in runtime_header
    assert "#ifdef PROTOCYTE_ENABLE_STD_FORMAT" not in runtime_header
    assert "#ifdef PROTOCYTE_ENABLE_FMT_FORMAT" not in runtime_header
    assert (
        "inline void copy_bytes(u8 *dst, const u8 *src, const usize count) noexcept"
        in runtime_header
    )
    assert "if (!count || dst == src)" in runtime_header
    assert "::std::memmove(dst, src, count);" in runtime_header
    assert "::std::memcpy(dst, src, count);" in runtime_header
    assert (
        "constexpr bool bytes_equal(const Span<const u8> lhs, const Span<const u8> rhs) noexcept"
        in runtime_header
    )
    assert "if (lhs.empty())" in runtime_header
    assert "if (::std::is_constant_evaluated())" in runtime_header
    assert (
        "return ::std::memcmp(lhs.data(), rhs.data(), lhs.size()) == 0;"
        in runtime_header
    )
    assert "template<usize Max> using ByteArray = Array<u8, Max>;" in runtime_header
    assert "ByteArray(ByteArray &&other) noexcept" not in runtime_header
    assert "Status assign(const Span<const u8> view) noexcept" in array_body
    assert "copy_bytes(data(), view.data(), view.size());" in array_body
    assert "Span<const u8> view() const noexcept" in array_body
    assert "Span<u8> mutable_view() noexcept" in array_body
    assert "const usize old_size {size_};" in array_body
    assert "::std::memset(data() + old_size, 0, count - old_size);" in array_body
    assert "Status resize_for_overwrite(const usize count) noexcept" in array_body
    assert "copy_bytes(bytes_, other.bytes_, Max);" in fixed_byte_array_body
    assert "::std::memset(bytes_, 0, Max);" in fixed_byte_array_body
    assert (
        "Status resize_for_overwrite(const usize count) noexcept"
        in fixed_byte_array_body
    )
    assert "return bytes_.resize_for_overwrite(count);" in bytes_body
    assert "copy_bytes(temp.data(), view.data(), view.size());" in bytes_body
    assert "constexpr operator ::std::string_view() const noexcept" in span_body
    assert "requires(::std::same_as<::std::remove_cv_t<T>, char>)" in span_body
    assert "return ::std::string_view {data_, size_};" in span_body
    assert "data_ == nullptr ? ::std::string_view {}" not in span_body
    assert (
        "#if PROTOCYTE_ENABLE_STD_STRING_VIEW\n    using StringView = ::std::string_view;\n#else\n    using StringView = Span<const char>;\n#endif"
        in runtime_header
    )
    assert "using value_type = const char;" in string_body
    assert "Span<const char> view() const noexcept" in string_body
    assert "Span<const u8> byte_view() const noexcept" in string_body
    assert "const char *data() const noexcept" in string_body
    assert "usize length() const noexcept { return size(); }" in string_body
    assert (
        "operator ::std::string_view() const noexcept { return view(); }" in string_body
    )
    assert (
        "#if PROTOCYTE_ENABLE_FMT_FORMAT\n    template<class Config> std::string_view format_as(const String<Config> &value) noexcept"
        in runtime_header
    )
    assert "return ::std::string_view {value.data(), value.size()};" in runtime_header
    assert (
        "#if PROTOCYTE_ENABLE_STD_FORMAT && defined(__cpp_lib_format) && __cpp_lib_format >= 201907L\nnamespace std {"
        in runtime_header
    )
    assert (
        "template<class Config> struct formatter<::protocyte::String<Config>, char>"
        in runtime_header
    )
    assert "public ::std::formatter<::std::string_view, char>" in runtime_header
    assert (
        "auto format(const ::protocyte::String<Config> &value, FormatContext &ctx) const"
        in runtime_header
    )
    assert "Status assign(const Span<const char> view) noexcept" in string_body
    assert "Status assign(const Span<const u8> view) noexcept" in string_body
    assert "copy_bytes(out, data_ + pos_, count);" in slice_reader_body
    assert "copy_bytes(data_ + pos_, data, count);" in slice_writer_body
    assert "for (usize i {}; i < count; ++i)" not in slice_reader_body
    assert "for (usize i {}; i < count; ++i)" not in slice_writer_body
    assert (
        "if constexpr (requires(Reader &source, const usize bytes)"
        not in runtime_header
    )
    assert "reader.can_read(byte_count)" in runtime_header
    assert (
        "if constexpr (requires(const Writer &target, const usize bytes)"
        not in runtime_header
    )
    assert "if (writer.can_write(*byte_count))" in runtime_header


def test_runtime_discriminators_follow_payload_storage() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    result_body = runtime_header.split(
        "template<class T, class E = Error> struct Result {", maxsplit=1
    )[1].split("template<class E> struct Result<void, E> {", maxsplit=1)[0]
    result_storage = result_body.split("protected:", maxsplit=1)[1]
    assert ": value_ {}, ok_ {true}" in result_body
    assert ": error_ {unexpected_value.error()}, ok_ {false}" in result_body
    assert result_storage.index(
        "union {\n            T value_;"
    ) < result_storage.index("bool ok_;")

    void_result_body = runtime_header.split(
        "template<class E> struct Result<void, E> {", maxsplit=1
    )[1].split("using Status = Result<void>;", maxsplit=1)[0]
    void_result_storage = void_result_body.split("protected:", maxsplit=1)[1]
    assert void_result_storage.index("Storage storage_;") < void_result_storage.index(
        "bool ok_ {true};"
    )

    optional_body = runtime_header.split(
        "template<class T> struct Optional {", maxsplit=1
    )[1].split("template<class T, class Config> struct Vector {", maxsplit=1)[0]
    optional_storage = optional_body.split("protected:", maxsplit=1)[1]
    assert optional_storage.index(
        "alignas(T) unsigned char storage_[sizeof(T)];"
    ) < optional_storage.index("bool has_ {};")

    fixed_bytes_body = runtime_header.split(
        "template<usize Max> struct FixedByteArray {", maxsplit=1
    )[1].split("template<class Config> struct Bytes {", maxsplit=1)[0]
    fixed_bytes_storage = fixed_bytes_body.split("protected:", maxsplit=1)[1]
    assert fixed_bytes_storage.index("u8 bytes_[Max];") < fixed_bytes_storage.index(
        "bool has_ {};"
    )


def test_cpp_writer_indent_context_manager_restores_indentation() -> None:
    writer = CppWriter()
    writer.line("root")
    with writer.indent():
        writer.line("child")
        with writer.indent(2):
            writer.line("grandchild")
    writer.line("tail")

    assert writer.render() == "root\n  child\n      grandchild\ntail\n"


def test_generates_proto3_files_and_runtime() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("simple.proto")
    request.parameter = "runtime=emit"
    request.proto_file.append(_simple_file())

    response = generate_response(request)

    assert not response.error
    assert (
        response.supported_features
        & plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    )
    files = {item.name: item.content for item in response.file}
    assert "simple.protocyte.hpp" in files
    assert "simple.protocyte.cpp" in files
    assert "protocyte/runtime/runtime.hpp" in files
    assert "struct Sample;" in files["simple.protocyte.hpp"]
    assert files["simple.protocyte.hpp"].startswith(
        "#pragma once\n\n#ifndef PROTOCYTE_GENERATED_SIMPLE_PROTO_"
    )
    assert "#include <cstddef>" not in files["simple.protocyte.hpp"]
    assert "#include <cstdint>" not in files["simple.protocyte.hpp"]
    assert "#include <cstdlib>" not in files["simple.protocyte.hpp"]
    assert "#include <stddef.h>" not in files["simple.protocyte.hpp"]
    assert "#include <stdint.h>" not in files["simple.protocyte.hpp"]
    assert files["protocyte/runtime/runtime.hpp"].startswith(
        "#pragma once\n\n#ifndef PROTOCYTE_RUNTIME_RUNTIME_HPP"
    )
    assert "#include <cstddef>" in files["protocyte/runtime/runtime.hpp"]
    assert "#include <cstdint>" in files["protocyte/runtime/runtime.hpp"]
    assert "#include <cstdlib>" not in files["protocyte/runtime/runtime.hpp"]
    assert "#include <stddef.h>" not in files["protocyte/runtime/runtime.hpp"]
    assert "#include <stdint.h>" not in files["protocyte/runtime/runtime.hpp"]
    assert (
        "default_max_recursion_depth = 100u" in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "default_max_total_bytes = 0x7fffffffu"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "default_max_message_bytes = 0x7fffffffu"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "default_max_string_bytes = 0x7fffffffu"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "default_max_repeated_elements = 0x7fffffffu"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "default_max_map_entries = 0x7fffffffu"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "default_max_total_allocation_bytes = ~usize {0u}"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "usize recursion_depth {};" in files["protocyte/runtime/runtime.hpp"]
    assert "usize total_allocated_bytes {};" in files["protocyte/runtime/runtime.hpp"]
    assert "struct ParseBudgetReader" in files["protocyte/runtime/runtime.hpp"]
    assert "append_trivial_from_reader" not in files["protocyte/runtime/runtime.hpp"]
    assert (
        "return static_cast<Reader *>(reader)->consume_repeated_elements(count, field_number);"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "return static_cast<Reader *>(reader)->consume_map_entries(count, field_number);"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "if constexpr (requires { inner_->consume_repeated_elements" not in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "if constexpr (requires { inner_->consume_map_entries" not in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert (
        "protocyte Config::Context must expose recursion_depth for recursion-limited parsing"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template <typename Config = ::protocyte::DefaultConfig>"
        in files["simple.protocyte.hpp"]
    )
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
    assert "using Status = Result<void>;" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "template<class T, class E = Error> struct Result {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class E> struct Result<void, E> {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "using value_type = T;" in files["protocyte/runtime/runtime.hpp"]
    assert "using error_type = E;" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "constexpr Result() noexcept(noexcept(T {}))"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "requires(!ResultType<U> && !UnexpectedType<U>)"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr Result(const Result<U, G> &other)"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr Result(Result<U, G> &&other)"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr Result(const Result<void, G> &other)"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "static constexpr Result ok() noexcept"
        not in files["protocyte/runtime/runtime.hpp"]
    )
    assert "const usize offset," in files["protocyte/runtime/runtime.hpp"]
    assert (
        "inline void *hosted_allocate(void *, const usize size, const usize alignment) noexcept {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr Unexpected<Error> unexpected(const ErrorCode code, const usize offset,"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "u64 value {};" in files["protocyte/runtime/runtime.hpp"]
    assert "u64 value = {};" not in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[4u];" in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[8u];" in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[8u] {\n" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "return ::std::memcmp(lhs.data(), rhs.data(), lhs.size()) == 0;"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "if (!size)" in files["protocyte/runtime/runtime.hpp"]
    assert "concept ByteViewConvertible" not in files["protocyte/runtime/runtime.hpp"]
    assert "ByteView" not in files["protocyte/runtime/runtime.hpp"]
    assert "MutableByteView" not in files["protocyte/runtime/runtime.hpp"]
    assert (
        "inline Result<usize> checked_add(const usize lhs, const usize rhs) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "inline Result<usize> checked_mul(const usize lhs, const usize rhs) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "concept ByteSpanSource" in files["protocyte/runtime/runtime.hpp"]
    assert "concept TextChar" in files["protocyte/runtime/runtime.hpp"]
    assert "concept TextArray" in files["protocyte/runtime/runtime.hpp"]
    assert "concept TextPointer" in files["protocyte/runtime/runtime.hpp"]
    assert "concept TextSource" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "Result<Span<const u8>> byte_span_of(const Span<T, Extent> view) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<Span<const u8>> cstring_byte_span_of(const Char *value) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<Span<const u8>> cstring_byte_span_of(const Char (&value)[N]) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<Span<const u8>> text_byte_span_of(const T &value) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<Span<const u8>> text_byte_span_of(const Char (&value)[N]) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<Span<const u8>> byte_span_of(const Char (&value)[N]) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<Span<const u8>> byte_span_of(const T &value) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "other.size_ = {};" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "const auto bytes = checked_mul(requested, sizeof(T));"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "explicit Vector(Context *ctx = nullptr) noexcept: ctx_ {ctx} {}"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "void bind(Context *ctx) noexcept { ctx_ = ctx; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr usize capacity() const noexcept { return Max; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "if (ctx_ != nullptr && view.size() > ctx_->limits.max_string_bytes) {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "using reverse_iterator = ReverseIterator<T>;"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "offset_ptr(" not in files["protocyte/runtime/runtime.hpp"]
    assert "using iterator = const char *;" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "using reverse_iterator = ReverseIterator<const char>;"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "using Bucket = Optional<Entry>;" in files["protocyte/runtime/runtime.hpp"]
    assert "struct EntryProxy {" in files["protocyte/runtime/runtime.hpp"]
    assert "struct ConstEntryProxy {" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "iterator begin() noexcept { return iterator {buckets_.begin(), buckets_.end()}; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const_iterator begin() const noexcept { return const_iterator {buckets_.begin(), buckets_.end()}; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class Fn> Status for_each(Fn &&fn) noexcept"
        not in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class Fn> Status for_each(Fn &&fn) const noexcept"
        not in files["protocyte/runtime/runtime.hpp"]
    )
    assert "struct Tag {" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "constexpr Tag decode_tag(const u64 raw) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class Reader> Result<Tag> read_tag(Reader &reader) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class E> struct Unexpected {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr auto unexpected(E &&error_value) noexcept("
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "requires(!UnexpectedType<E>)" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class U = T>" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "Result<void, E> status() const & noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr auto and_then(F &&f) & noexcept("
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr auto transform(F &&f) & noexcept("
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr auto or_else(F &&f) & noexcept("
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr auto transform_error(F &&f) & noexcept("
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr Result() noexcept = default;"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "union Storage {" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "static constexpr Result err(const ErrorCode code, const usize offset = {}, const u32 field_number = {}) noexcept"
        not in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr void operator*() const noexcept {}"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr void value() const noexcept {}"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class T> struct Optional {" in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "T &operator*() & noexcept { return *ptr(); }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const T &operator*() const & noexcept { return *ptr(); }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "T *operator->() noexcept { return ptr(); }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const T *operator->() const noexcept { return ptr(); }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class T, class Config> struct Box {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "T &operator*() noexcept { return *ptr_; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const T &operator*() const noexcept { return *ptr_; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "T *operator->() noexcept { return ptr_; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const T *operator->() const noexcept { return ptr_; }"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class T, class E> struct Result<T &, E> {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class T> struct Optional<T &> {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class T, class E> struct Result<T &&, E> {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class T> struct Optional<T &&> {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "const auto [field, wire] = *tag;" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "Status skip_field(Reader &reader, const WireType wire_type, const u32 field_number = {}) noexcept"
        not in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "template<class Reader> Status skip_group(Reader &reader"
        not in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status write_tag(Writer &writer, const u32 field_number, const WireType wire_type) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status expect_wire_type(Reader &reader, const WireType actual, const WireType expected,"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<usize> read_length_delimited_size(Reader &reader) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "if (*len > static_cast<u64>(~static_cast<usize>(0u))) {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "return protocyte::unexpected(ErrorCode::integer_overflow, reader.position());"
        in files["protocyte/runtime/runtime.hpp"]
        or "return protocyte::unexpected(ErrorCode::integer_overflow, {});"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const auto size = read_length_delimited_size(reader);"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "open_nested_message(typename Config::Context &ctx, Reader &reader, const u32 field_number) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status read_message(typename Config::Context &ctx, Reader &reader, const u32 field_number, Message &out) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "merge_message_fragment" not in files["protocyte/runtime/runtime.hpp"]
    assert "merge_message(Message" not in files["protocyte/runtime/runtime.hpp"]
    assert "commit_read_message" not in files["protocyte/runtime/runtime.hpp"]
    assert "read_message_staged" not in files["protocyte/runtime/runtime.hpp"]
    assert (
        "MessageParseAccess::merge_fields_from(out, nested_reader)"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "parsed.validate()" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "template<class Config, class Reader> Status skip_field(typename Config::Context &ctx, Reader &reader,"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status read_string_field(typename Config::Context &ctx, Reader &reader,"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status write_bytes_field(Writer &writer, const u32 field_number, const Span<const u8> view) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<f64> read_double_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status write_double_field(Writer &writer, const u32 field_number, const f64 value) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Status write_message_field(Writer &writer, const u32 field_number, const Message &value) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "Result<usize> message_field_size(const u32 field_number, const Message &value) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "inline Result<usize> length_delimited_field_size(const u32 field_number, const usize payload_size) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "return checked_add(*prefix_size, payload_size);"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "if (const auto st = copied.assign(value.view()); !st) {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "if (const auto st = expect_wire_type(reader, wire_type, WireType::VARINT, field_number); !st) {"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "const auto size = value.encoded_size();"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "return length_delimited_field_size(field_number, *size);"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "constexpr usize tag_size(const u32 field_number, const WireType wire_type = WireType::LEN) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert (
        "return wire_type == WireType::SGROUP ? size * 2u : size;"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "FEATURE_PROTO3_OPTIONAL" not in files["simple.protocyte.hpp"]


def test_runtime_string_assign_checks_size_limit_before_utf8_validation() -> None:
    files = runtime_files()
    header = files["protocyte/runtime/runtime.hpp"]

    assign_body = header.split(
        "Status assign(const Span<const u8> view) noexcept {", maxsplit=1
    )[1]
    assign_body = assign_body.split("Status validate() const noexcept", maxsplit=1)[0]

    assert "if (const auto st = check_size_limit(view.size()); !st)" in assign_body
    assert assign_body.index("check_size_limit(view.size())") < assign_body.index(
        "validate_utf8(view)"
    )
    assert "Status assign_owned" not in header


def test_allows_generating_messages_from_files_with_top_level_extension_declarations() -> (
    None
):
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("legacy.proto")
    file = request.proto_file.add()
    file.name = "legacy.proto"
    file.package = "legacy"
    file.syntax = "proto2"
    message = file.message_type.add()
    message.name = "Legacy"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    extension = file.extension.add()
    extension.name = "legacy_extension"
    extension.number = 100
    extension.label = F.LABEL_OPTIONAL
    extension.type = F.TYPE_INT32
    extension.extendee = ".legacy.Legacy"

    response = generate_response(request)

    assert not response.error
    files = {item.name: item.content for item in response.file}
    assert "legacy.protocyte.hpp" in files
    assert "legacy_extension" not in files["legacy.protocyte.hpp"]


def test_descriptor_request_with_descriptor_proto_generates_only_selected_user_files() -> (
    None
):
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("arrays.proto")
    request.proto_file.extend(
        [
            descriptor_pb2.FileDescriptorProto.FromString(
                descriptor_pb2.DESCRIPTOR.serialized_pb
            ),
            _options_file(),
            _constant_array_file(),
        ]
    )

    response = generate_response(request)

    assert not response.error
    assert [file.name for file in response.file] == [
        "arrays.protocyte.cpp",
        "arrays.protocyte.hpp",
    ]


def test_rejects_duplicate_descriptor_file_names() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("simple.proto")
    request.proto_file.extend([_simple_file(), _simple_file()])

    response = generate_response(request)

    assert "duplicate descriptor file name: simple.proto" in response.error


def test_rejects_missing_import_dependency() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("imports_missing.proto")
    file = request.proto_file.add()
    file.name = "imports_missing.proto"
    file.syntax = "proto3"
    file.dependency.append("missing.proto")
    file.message_type.add().name = "ImportsMissing"

    response = generate_response(request)

    assert (
        "imports_missing.proto imports missing descriptor missing.proto"
        in response.error
    )


def test_rejects_proto3_explicit_defaults_from_descriptor_semantics() -> None:
    request = _basic_request()
    request.proto_file[0].message_type[0].field[0].default_value = "7"

    response = generate_response(request)

    assert (
        "demo.Sample.id: explicit default values are not allowed in proto3"
        in response.error
    )


def test_rejects_proto2_repeated_field_defaults_from_descriptor_semantics() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("bad_defaults.proto")
    file = request.proto_file.add()
    file.name = "bad_defaults.proto"
    file.package = "bad"
    file.syntax = "proto2"
    message = file.message_type.add()
    message.name = "BadDefaults"
    field = message.field.add()
    field.name = "ids"
    field.number = 1
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32
    field.default_value = "7"

    response = generate_response(request)

    assert (
        "bad.BadDefaults.ids: repeated fields cannot have default values"
        in response.error
    )


def test_rejects_proto2_message_field_defaults_from_descriptor_semantics() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("bad_defaults.proto")
    file = request.proto_file.add()
    file.name = "bad_defaults.proto"
    file.package = "bad"
    file.syntax = "proto2"
    nested = file.message_type.add()
    nested.name = "Nested"
    message = file.message_type.add()
    message.name = "BadDefaults"
    field = message.field.add()
    field.name = "nested"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".bad.Nested"
    field.default_value = "nested"

    response = generate_response(request)

    assert (
        "bad.BadDefaults.nested: message fields cannot have default values"
        in response.error
    )


def test_rejects_selected_group_fields() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("legacy_group.proto")
    file = request.proto_file.add()
    file.name = "legacy_group.proto"
    file.package = "legacy"
    file.syntax = "proto2"
    message = file.message_type.add()
    message.name = "Legacy"
    group = message.field.add()
    group.name = "Payload"
    group.number = 1
    group.label = F.LABEL_OPTIONAL
    group.type = F.TYPE_GROUP

    response = generate_response(request)

    assert "legacy.Legacy.Payload: groups are not supported" in response.error


def test_rejects_selected_edition_files() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("edition.proto")
    file = request.proto_file.add()
    file.name = "edition.proto"
    file.package = "demo"
    file.edition = descriptor_pb2.EDITION_2023
    file.message_type.add().name = "EditionMessage"

    response = generate_response(request)

    assert (
        "target file edition.proto: protobuf Editions are not supported in v1"
        in response.error
    )


def test_proto2_model_tracks_presence_defaults_required_and_unpacked_repeated() -> None:
    model = build_model(_proto2_request())
    fields = {field.name: field for field in model.messages["legacy.Legacy"].fields}

    assert model.files["legacy.proto"].syntax == "proto2"
    assert fields["count"].explicit_presence
    assert not fields["count"].required
    assert fields["count"].default_cpp == "7"
    assert fields["label"].explicit_presence
    assert fields["label"].default_cpp == '::protocyte::StringView {"legacy", 6u}'
    assert fields["name"].explicit_presence
    assert fields["name"].required
    assert fields["samples"].packed is False
    assert fields["blob"].default_cpp == (
        '::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8*>("\\x01""\\xff"), 2u}'
    )
    assert (
        fields["ratio"].default_cpp
        == "::std::numeric_limits<::protocyte::f32>::infinity()"
    )
    assert (
        fields["precise"].default_cpp
        == "::std::numeric_limits<::protocyte::f64>::quiet_NaN()"
    )
    assert fields["max_counter"].default_cpp == "18446744073709551615ull"
    assert fields["min_counter"].default_cpp == "(-9223372036854775807ll - 1ll)"


@pytest.mark.parametrize(
    ("syntax", "explicit", "expected"),
    [
        ("proto2", None, False),
        ("proto2", False, False),
        ("proto2", True, True),
        ("proto3", None, True),
        ("proto3", False, False),
        ("proto3", True, True),
    ],
)
def test_packed_option_presence_follows_protobuf_syntax_defaults(
    syntax: str, explicit: bool | None, expected: bool
) -> None:
    field = F(label=F.LABEL_REPEATED, type=F.TYPE_INT32)
    if explicit is not None:
        field.options.packed = explicit

    assert _is_packed(field, syntax) is expected


def test_empty_syntax_model_uses_proto2_presence_defaults_and_packing() -> None:
    request = _proto2_request()
    request.proto_file[0].ClearField("syntax")

    model = build_model(request)
    fields = {field.name: field for field in model.messages["legacy.Legacy"].fields}

    assert model.files["legacy.proto"].syntax == "proto2"
    assert fields["count"].explicit_presence
    assert fields["count"].default_cpp == "7"
    assert fields["samples"].packed is False


def test_generates_proto2_presence_defaults_and_required_validation() -> None:
    response = generate_response(_proto2_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["legacy.protocyte.hpp"]
    assert (
        "constexpr ::protocyte::i32 count() const noexcept { return has_count_ ? count_ : 7; }"
        in header
    )
    assert "constexpr bool has_count() const noexcept { return has_count_; }" in header
    assert (
        'label() const noexcept { return has_label_ ? label_.view() : ::protocyte::StringView {"legacy", 6u}; }'
        in header
    )
    assert "bool has_name_ {};" in header
    assert "bool has_name() const noexcept { return has_name_; }" in header
    assert "if (!has_name()) {" in header
    assert (
        "::protocyte::ErrorCode::invalid_argument, {}, static_cast<::protocyte::u32>(FieldNumber::name)"
        in header
    )
    assert "for (const auto &samples_value : samples_) {" in header
    assert "packed_size_samples" not in header
    assert "#include <limits>" in header
    assert (
        'blob() const noexcept { return has_blob_ ? blob_.view() : ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8*>("\\x01""\\xff"), 2u}; }'
        in header
    )
    assert (
        "constexpr ::protocyte::f32 ratio() const noexcept { return has_ratio_ ? ratio_ : ::std::numeric_limits<::protocyte::f32>::infinity(); }"
        in header
    )
    assert (
        "constexpr ::protocyte::f64 precise() const noexcept { return has_precise_ ? precise_ : ::std::numeric_limits<::protocyte::f64>::quiet_NaN(); }"
        in header
    )
    assert (
        "constexpr ::protocyte::u64 max_counter() const noexcept { return has_max_counter_ ? max_counter_ : 18446744073709551615ull; }"
        in header
    )
    assert (
        "constexpr ::protocyte::i64 min_counter() const noexcept { return has_min_counter_ ? min_counter_ : (-9223372036854775807ll - 1ll); }"
        in header
    )


def test_generates_empty_syntax_defaults_as_proto2() -> None:
    request = _proto2_request()
    request.proto_file[0].ClearField("syntax")

    response = generate_response(request)

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["legacy.protocyte.hpp"]
    assert (
        "constexpr ::protocyte::i32 count() const noexcept { return has_count_ ? count_ : 7; }"
        in header
    )
    assert "constexpr bool has_count() const noexcept { return has_count_; }" in header
    assert "packed_size_samples" not in header


def test_proto2_default_semantics_follow_protobuf_spec() -> None:
    model = build_model(_proto2_default_semantics_request())
    fields = {field.name: field for field in model.messages["defaults.Defaults"].fields}

    assert fields["implicit_int32"].explicit_presence
    assert fields["implicit_int32"].default_cpp is None
    assert fields["implicit_bool"].default_cpp is None
    assert fields["implicit_string"].default_cpp is None
    assert fields["implicit_bytes"].default_cpp is None
    assert fields["implicit_message"].default_cpp is None
    assert fields["implicit_numbers"].packed is False
    assert fields["implicit_choice"].default_cpp == "5"
    assert fields["explicit_choice"].default_cpp == "9"
    assert fields["implicit_choices"].default_cpp is None
    assert fields["required_int32"].required
    assert fields["required_int32"].default_cpp == "17"


def test_empty_syntax_default_semantics_follow_proto2_spec() -> None:
    request = _proto2_default_semantics_request()
    request.proto_file[0].ClearField("syntax")

    model = build_model(request)
    fields = {field.name: field for field in model.messages["defaults.Defaults"].fields}

    assert model.files["defaults.proto"].syntax == "proto2"
    assert fields["implicit_int32"].explicit_presence
    assert fields["implicit_numbers"].packed is False
    assert fields["implicit_choice"].default_cpp == "5"
    assert fields["explicit_choice"].default_cpp == "9"
    assert fields["implicit_choices"].default_cpp is None
    assert fields["required_int32"].default_cpp == "17"


def test_generates_proto2_default_semantics() -> None:
    response = generate_response(_proto2_default_semantics_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["defaults.protocyte.hpp"]
    assert (
        "constexpr ::protocyte::i32 implicit_int32() const noexcept { return implicit_int32_; }"
        in header
    )
    assert (
        "constexpr bool implicit_bool() const noexcept { return implicit_bool_; }"
        in header
    )
    assert (
        "::protocyte::StringView implicit_string() const noexcept { return implicit_string_.view(); }"
        in header
    )
    assert (
        "::protocyte::Span<const ::protocyte::u8> implicit_bytes() const noexcept { return implicit_bytes_.view(); }"
        in header
    )
    assert (
        "bool has_implicit_message() const noexcept { return implicit_message_.has_value(); }"
        in header
    )
    assert "if (implicit_message_.has_value()) {" in header
    assert "has_implicit_message_" not in header
    assert "packed_size_implicit_numbers" not in header
    assert (
        "constexpr ::protocyte::i32 implicit_choice_raw() const noexcept { return has_implicit_choice_ ? implicit_choice_ : 5; }"
        in header
    )
    assert (
        "constexpr ::defaults::DefaultChoice implicit_choice() const noexcept { return static_cast<::defaults::DefaultChoice>(has_implicit_choice_ ? implicit_choice_ : 5); }"
        in header
    )
    assert (
        "constexpr ::protocyte::i32 explicit_choice_raw() const noexcept { return has_explicit_choice_ ? explicit_choice_ : 9; }"
        in header
    )
    assert (
        "constexpr ::defaults::DefaultChoice explicit_choice() const noexcept { return static_cast<::defaults::DefaultChoice>(has_explicit_choice_ ? explicit_choice_ : 9); }"
        in header
    )
    assert (
        "constexpr ::protocyte::i32 oneof_int32() const noexcept { return has_oneof_int32() ? choice_.oneof_int32_ : 11; }"
        in header
    )
    assert (
        '::protocyte::StringView oneof_string() const noexcept { return has_oneof_string() ? choice_.oneof_string_.view() : ::protocyte::StringView {"chosen", 6u}; }'
        in header
    )
    assert (
        '::protocyte::Span<const ::protocyte::u8> oneof_bytes() const noexcept { return has_oneof_bytes() ? choice_.oneof_bytes_.view() : ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8*>("\\x02""\\xfe"), 2u}; }'
        in header
    )
    assert (
        "constexpr ::protocyte::i32 implicit_oneof_choice_raw() const noexcept { return has_implicit_oneof_choice() ? choice_.implicit_oneof_choice_ : 5; }"
        in header
    )
    assert (
        "constexpr ::protocyte::i32 explicit_oneof_choice_raw() const noexcept { return has_explicit_oneof_choice() ? choice_.explicit_oneof_choice_ : 9; }"
        in header
    )
    assert (
        "constexpr ::protocyte::i32 required_int32() const noexcept { return has_required_int32_ ? required_int32_ : 17; }"
        in header
    )


def test_generates_closed_enum_validation_for_proto2_enums() -> None:
    response = generate_response(_proto2_default_semantics_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["defaults.protocyte.hpp"]
    assert "if (value != 5 && value != 9) {" in header
    assert (
        "::protocyte::ErrorCode::invalid_argument, {}, static_cast<::protocyte::u32>(FieldNumber::implicit_choice)"
        in header
    )
    assert "implicit_choices_value != 5 && implicit_choices_value != 9" in header
    assert (
        "explicit_oneof_choice_value != 5 && explicit_oneof_choice_value != 9" in header
    )


def test_generated_proto3_file_can_reference_imported_proto2_message() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("uses_legacy.proto")
    request.proto_file.extend(
        [_proto2_dependency_file(), _proto3_uses_proto2_dependency_file()]
    )

    response = generate_response(request)

    assert not response.error
    files = {item.name: item.content for item in response.file}
    assert '#include "legacy_dep.protocyte.hpp"' in files["uses_legacy.protocyte.hpp"]


def test_generation_succeeds_without_clang_format_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(protocyte_cpp.shutil, "which", lambda name: None)

    def fail_run(*args, **kwargs):
        raise AssertionError(
            "clang-format should not be invoked when it is unavailable"
        )

    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fail_run)

    response = generate_response(_basic_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    assert files["simple.protocyte.hpp"].startswith("#pragma once\n")


def test_generation_uses_explicit_clang_format_override_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="formatted\n", stderr="")

    monkeypatch.setattr(protocyte_cpp.shutil, "which", lambda name: None)
    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fake_run)

    response = generate_response(_basic_request(parameter="clang_format=my-format"))

    assert not response.error
    assert commands
    assert all(command[0] == "my-format" for command in commands)
    assert all(item.content == "formatted\n" for item in response.file)


def test_generator_policy_rejects_tenant_formatter_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("formatter must not be launched"),
    )

    response = generate_response(
        _basic_request(parameter="clang_format=tenant-controlled"),
        policy=GeneratorPolicy(allow_formatter_parameters=False),
    )

    assert response.error == (
        "clang_format and clang_format_config are disabled by the generator policy"
    )
    assert not response.file


def test_generator_policy_can_disable_all_formatting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocyte_cpp.shutil, "which", lambda name: "/operator/bin/clang-format"
    )
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("formatter must not be launched"),
    )

    response = generate_response(
        _basic_request(), policy=GeneratorPolicy(format_outputs=False)
    )

    assert not response.error
    assert response.file


def test_generator_policy_applies_formatter_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def time_out(command: list[str], **kwargs):
        raise protocyte_cpp.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(
        protocyte_cpp.shutil, "which", lambda name: "/operator/bin/clang-format"
    )
    monkeypatch.setattr(protocyte_cpp.subprocess, "run", time_out)

    response = generate_response(
        _basic_request(), policy=GeneratorPolicy(formatter_timeout_seconds=0.5)
    )

    assert (
        "clang-format timed out for simple.protocyte.hpp after 0.5 seconds"
        in response.error
    )
    assert not response.file


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_bounded_formatter_stops_oversized_process_output(stream: str) -> None:
    script = (
        "import sys; "
        f"sys.{stream}.buffer.write(b'x' * (1024 * 1024)); "
        f"sys.{stream}.buffer.flush()"
    )

    with pytest.raises(protocyte_cpp._FormatterOutputLimit):
        protocyte_cpp._run_formatter_bounded(
            [sys.executable, "-c", script],
            "",
            timeout_seconds=5.0,
            max_output_bytes=64,
        )


def test_formatter_policy_uses_live_output_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], int]] = []

    def fake_bounded(
        command: list[str],
        content: str,
        *,
        timeout_seconds: float | None,
        max_output_bytes: int,
    ) -> protocyte_cpp._FormatterResult:
        del content, timeout_seconds
        calls.append((command, max_output_bytes))
        return protocyte_cpp._FormatterResult(0, "formatted\n", "")

    monkeypatch.setattr(protocyte_cpp, "_run_formatter_bounded", fake_bounded)
    monkeypatch.setattr(
        protocyte_cpp, "_clang_format_style_args", lambda options: ["--style=file"]
    )
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("bounded formatting must not use run()"),
    )

    formatted = protocyte_cpp._format_cpp_outputs(
        {"sample.cpp": "int x;\n"},
        protocyte_cpp.GeneratorOptions(clang_format="my-format"),
        max_output_bytes=64,
    )

    assert formatted == {"sample.cpp": "formatted\n"}
    assert calls == [
        (["my-format", "--style=file", "--assume-filename=sample.cpp"], 64)
    ]


@pytest.mark.parametrize(
    ("policy", "label"),
    [
        (GeneratorPolicy(max_request_bytes=0), "serialized request bytes"),
        (GeneratorPolicy(max_files_to_generate=0), "files to generate"),
        (GeneratorPolicy(max_proto_files=0), "proto files"),
        (GeneratorPolicy(max_descriptor_nodes=1), "descriptor nodes"),
        (GeneratorPolicy(max_nesting_depth=0), "message nesting depth"),
        (GeneratorPolicy(max_generated_bytes=1), "generated output bytes"),
    ],
)
def test_generator_policy_returns_clean_errors_for_limits(
    policy: GeneratorPolicy, label: str
) -> None:
    response = generate_response(_basic_request(), policy=policy)

    assert f"generator policy limit exceeded for {label}" in response.error
    assert not response.file


def test_generated_output_budget_is_cumulative_and_stops_before_append() -> None:
    budget = protocyte_cpp._OutputBudget(max_bytes=5)
    first = CppWriter(output_budget=budget)
    first.line("1234")
    second = CppWriter(output_budget=budget)

    with pytest.raises(
        ProtocyteError,
        match=r"generated output bytes: 6 > 5",
    ):
        second.line()

    assert first.render() == "1234\n"
    assert second.lines == []


def test_generator_policy_short_circuits_genuinely_deep_descriptors() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("deep.proto")
    file = request.proto_file.add()
    file.name = "deep.proto"
    file.syntax = "proto3"
    message = file.message_type.add()
    message.name = "M0"
    for index in range(1, 1_500):
        message = message.nested_type.add()
        message.name = f"M{index}"

    response = generate_response(
        request,
        policy=GeneratorPolicy(max_nesting_depth=64, format_outputs=False),
    )

    assert response.error == (
        "generator policy limit exceeded for message nesting depth: 65 > 64"
    )
    assert not response.file


def test_generator_policy_rejects_invalid_limit_configuration() -> None:
    with pytest.raises(ValueError, match="max_request_bytes must not be negative"):
        GeneratorPolicy(max_request_bytes=-1)
    with pytest.raises(ValueError, match="formatter_timeout_seconds must be positive"):
        GeneratorPolicy(formatter_timeout_seconds=0)


def test_generation_decodes_explicit_clang_format_override_from_transport_parameter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "custom.style"
    config_path.write_text("BasedOnStyle: LLVM\n", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="formatted\n", stderr="")

    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fake_run)

    raw = (
        "clang_format=C:/Program Files/LLVM/bin/clang-format.exe,"
        f"clang_format_config={config_path.as_posix()}"
    )
    encoded = raw.encode("utf-8").hex()
    response = generate_response(
        _basic_request(parameter=f"_protocyte_options_hex={encoded}")
    )

    assert not response.error
    assert commands
    assert all(
        command[0] == "C:/Program Files/LLVM/bin/clang-format.exe"
        for command in commands
    )
    assert all(
        f"--style=file:{config_path.as_posix()}" in command for command in commands
    )


def test_generation_reports_explicit_clang_format_launch_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("missing executable")),
    )

    response = generate_response(
        _basic_request(parameter="clang_format=missing-format")
    )

    assert "failed to run clang-format" in response.error
    assert "missing executable" in response.error


def test_generation_reports_explicit_clang_format_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="broken style"
        ),
    )

    response = generate_response(_basic_request(parameter="clang_format=my-format"))

    assert (
        "clang-format failed for simple.protocyte.hpp: broken style" in response.error
    )


def test_generation_passes_explicit_clang_format_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "custom.style"
    config_path.write_text("BasedOnStyle: LLVM\n", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        assume_filename = next(
            part for part in command if part.startswith("--assume-filename=")
        )
        return SimpleNamespace(returncode=0, stdout=assume_filename + "\n", stderr="")

    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fake_run)

    response = generate_response(
        _basic_request(
            parameter=f"clang_format=my-format,clang_format_config={config_path.as_posix()}"
        )
    )

    assert not response.error
    assert commands
    assert all(
        f"--style=file:{config_path.as_posix()}" in command for command in commands
    )


def test_generation_reports_missing_explicit_clang_format_config(
    tmp_path: Path,
) -> None:
    missing_config = tmp_path / "missing.style"

    response = generate_response(
        _basic_request(
            parameter=f"clang_format=my-format,clang_format_config={missing_config.as_posix()}"
        )
    )

    assert (
        response.error
        == f"clang-format config was not found: {missing_config.as_posix()}"
    )


def test_generation_uses_clang_format_found_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        assume_filename = next(
            part for part in command if part.startswith("--assume-filename=")
        )
        filename = assume_filename.split("=", 1)[1]
        return SimpleNamespace(
            returncode=0, stdout=f"formatted:{filename}\n", stderr=""
        )

    monkeypatch.setattr(
        protocyte_cpp.shutil, "which", lambda name: "/usr/bin/clang-format"
    )
    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fake_run)

    response = generate_response(_basic_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    assert files["simple.protocyte.hpp"] == "formatted:simple.protocyte.hpp\n"
    assert files["simple.protocyte.cpp"] == "formatted:simple.protocyte.cpp\n"
    assert all(command[0] == "/usr/bin/clang-format" for command in commands)


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
    header = next(
        file.content for file in response.file if file.name == "simple.protocyte.hpp"
    )

    assert "namespace demo {" in header
    assert "bool has_opt_name() const noexcept" in header
    assert "#include <string_view>" not in header
    assert (
        "  ::protocyte::StringView opt_name() const noexcept { return opt_name_.view(); }"
        in header
    )
    assert "::std::string_view opt_name()" not in header
    assert "::protocyte::Span<const char> opt_name()" not in header
    assert "struct Sample {" in header
    assert (
        "typename Config::template Map<typename Config::String, ::protocyte::i32> items_;"
        in header
    )
    assert "typename Config::template Box<::demo::Sample<Config>> self_;" in header
    assert "ctx_{&ctx}" in header
    assert "items_{&ctx}" in header
    assert "samples_{&ctx}" in header
    assert "::protocyte::Status set_id(const ::protocyte::i32 value) noexcept" in header
    assert "const auto tag = ::protocyte::read_tag(reader);" in header
    assert "const auto [field_number, wire_type] = *tag;" in header
    assert (
        "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept"
        in header
    )
    assert (
        "insert_or_assign(::protocyte::move(key), ::protocyte::move(value))" in header
    )
    assert "template <typename Reader>" in header
    assert "::protocyte::Status merge_from(Reader& reader) noexcept" in header
    assert (
        "::protocyte::Status merge_partial_from(InputReader& reader) noexcept" in header
    )
    assert (
        "::protocyte::Status merge_partial_from(::protocyte::ReaderRef& reader) noexcept"
        not in header
    )
    assert "friend class ::protocyte::MessageParseAccess;" in header
    assert "ctx_->recursion_depth != 0u" not in header
    assert "::protocyte::Status merge_fields_from(Reader& reader) noexcept" in header
    assert (
        "::protocyte::ParseBudgetReader<InputReader> budget_reader{reader, ctx_->limits.max_total_bytes, ctx_->limits.max_repeated_elements, ctx_->limits.max_map_entries};"
        in header
    )
    assert "::protocyte::Status validate() const noexcept" in header
    assert "if (const auto st = validate(); !st) { return st; }" in header
    assert (
        "if (const auto st = ::protocyte::write_fixed_width_packed_values(writer, samples_.data(), samples_.size()); !st) { return st; }"
        in header
    )
    assert "for (const auto &packed_value_samples : samples_) {" not in header
    assert (
        "write_fixed_width_packed_values(writer, signed_samples_.data(), signed_samples_.size())"
        not in header
    )
    assert "for (const auto &packed_value_signed_samples : signed_samples_) {" in header
    assert "if (const auto st = out->copy_from(*this); !st)" in header
    assert "if (wire_type != ::protocyte::WireType::LEN)" in header
    assert "enum struct FieldNumber : ::protocyte::u32 {" in header
    assert "id = 1u," in header
    assert "opt_name = 2u," in header
    assert "case FieldNumber::id: {" in header
    assert "case FieldNumber::opt_name: {" in header
    assert "::std::endian::native == ::std::endian::little" not in header
    assert "decltype(samples_) &target" not in header
    assert "source.can_read(bytes)" not in header
    assert "requires(Reader &source, const ::protocyte::usize bytes)" not in header
    assert "append_trivial_from_reader" not in header
    assert "::protocyte::consume_repeated_elements" not in header
    assert header.index(
        "if (const auto st = reader.consume_repeated_elements(1u, field_number); !st)"
    ) < header.index("const auto decoded_samples")
    assert header.index(
        "if (const auto st = reader.consume_repeated_elements(*len / 4u, field_number); !st)"
    ) < header.index("packed_signed_samples_values{ctx_}")
    assert (
        "if (const auto st = reader.consume_map_entries(1u, field_number); !st) { return st; }"
        in header
    )
    assert header.index(
        "if (const auto st = reader.consume_map_entries(1u, field_number); !st)"
    ) < header.index("open_nested_message<Config>(*ctx_, reader, field_number)")
    assert (
        "read_fixed_width_packed_values(reader, *len, field_number, samples_)"
        in header
    )
    assert (
        "read_fixed_width_packed_values(reader, *len, packed_signed_samples_values)"
        not in header
    )
    assert (
        "const auto decoded_signed_samples = ::protocyte::read_sfixed32(packed);"
        in header
    )
    assert "const auto decoded_samples = ::protocyte::read_float(packed);" not in header
    assert "auto decoded = ::protocyte::read_fixed32(packed);" not in header
    assert (
        "const auto decoded_id = ::protocyte::read_int32_field(reader, wire_type, field_number);"
        in header
    )
    assert "if (!decoded_id) { return decoded_id.status(); }" in header
    assert "id_ = *decoded_id;" in header
    assert (
        "::protocyte::write_int32_field(writer, static_cast<::protocyte::u32>(FieldNumber::id), id_);"
        in header
    )
    assert "::protocyte::read_string_field<Config>(*ctx_, reader, wire_type," in header
    assert "::protocyte::write_string_field(" in header
    assert "::protocyte::write_message_field(" in header
    assert "::protocyte::message_field_size(" in header
    assert "FieldNumber::opt_name), opt_name_.view());" in header
    assert ".transform(" not in header
    assert (
        "const auto field_size_self = ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::self), *self_);"
        in header
    )
    assert ".and_then(" not in header
    assert (
        "::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);"
        in header
    )
    assert "::demo::Sample<Config> self_value{*ctx_};" in header
    assert "if (self_.has_value()) {" in header
    assert (
        "if (const auto st = self_value.copy_from(*self_); !st) { return st; }"
        in header
    )
    assert (
        "if (const auto st = ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number, self_value); !st) { return st; }"
        in header
    )
    assert (
        "if (const auto st = self_.assign(::protocyte::move(self_value)); !st) { return st; }"
        in header
    )
    assert "return has_self() ? self_.operator->() : nullptr;" in header
    assert "enum struct EntryFieldNumber" not in header
    assert "switch (entry_field) {" in header
    assert "case 2u: {" in header
    assert "*ctx_, entry_reader, 2u," in header
    assert "::protocyte::skip_field<Config>(*ctx_, entry_reader, entry_wire," in header
    assert "mutable_items().copy_from(other.items())" in header
    assert "mutable_samples().copy_from(other.samples())" in header
    assert "mutable_message_items().copy_from(other.message_items())" in header
    assert "const auto packed_reserve_samples = *len / 4u;" not in header
    assert "packed_samples_values.reserve(packed_reserve_samples)" not in header
    signed_reserve_index = header.index(
        "packed_signed_samples_values.reserve(packed_reserve_signed_samples)"
    )
    signed_preflight_index = header.rfind(
        "reader.can_read(*len)", 0, signed_reserve_index
    )
    assert signed_preflight_index != -1
    assert "checked_add(packed_samples_values.size(), *len / 4u)" not in header
    assert "if constexpr (requires(decltype(samples_) &target" not in header
    assert "packed_samples_values" not in header
    assert (
        "signed_samples_.append_trivial_range(packed_signed_samples_values.data(),"
        in header
    )
    assert (
        "const auto packed_size_samples_result = ::protocyte::checked_mul(samples_.size(), 4u);"
        in header
    )


def test_checked_smoke_output_reflects_copy_propagation() -> None:
    header = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "smoke"
        / "generated"
        / "example.protocyte.hpp"
    ).read_text(encoding="utf-8")
    cross_header = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "smoke"
        / "generated"
        / "cross_package.protocyte.hpp"
    ).read_text(encoding="utf-8")

    assert "copy_from(const UltimateComplexMessage &other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "mutable_r_int32_unpacked().copy_from(other.r_int32_unpacked())" in header
    assert "mutable_r_int32_packed().copy_from(other.r_int32_packed())" in header
    assert "mutable_r_double().copy_from(other.r_double())" in header
    assert "mutable_map_str_int32().copy_from(other.map_str_int32())" in header
    assert "mutable_map_uint64_msg().copy_from(other.map_uint64_msg())" in header
    assert (
        "::protocyte::Result<UltimateComplexMessage> clone() const noexcept" in header
    )
    assert "if (const auto st = out->copy_from(*this); !st) {" in header
    assert (
        "return has_recursive_self() ? recursive_self_.operator->() : nullptr;"
        in header
    )
    assert (
        "static_cast<::protocyte::u32>(FieldNumber::recursive_self), *recursive_self_"
        in header
    )
    assert (
        "!fixed_integer_array_.empty() && fixed_integer_array_.size() != 3u" in header
    )
    assert (
        "!fixed_repeated_byte_array_.empty() && fixed_repeated_byte_array_.size() != 3u"
        in header
    )
    assert (
        "for (const auto &packed_value_remote_values : remote_values_) {\n"
        "                    {\n"
        "                        {" not in cross_header
    )
    assert (
        "for (const auto &packed_value_remote_values : remote_values_) {\n"
        "                    {" not in cross_header
    )
    assert (
        "for (const auto &remote_values_value : remote_values_) {\n"
        "                    {" not in cross_header
    )
    assert "if (!remote_bytes_.empty()) {\n                {" not in cross_header
    weird_map_serialize = header.split(
        "for (const auto &entry : weird_map_) {", maxsplit=1
    )[1].split("if (deep_oneof_case_", maxsplit=1)[0]
    assert (
        weird_map_serialize.count(
            "                {\n                    const auto st_size ="
        )
        == 1
    )
    assert "const auto field_size_value" in weird_map_serialize
    assert "::protocyte::add_length_delimited_field_size(" not in weird_map_serialize
    assert (
        "const auto st_size = ::protocyte::add_size(entry_payload, *field_size_value);"
        in weird_map_serialize
    )
    assert "const auto key_size" not in header
    assert "const auto value_size" not in header
    assert (
        "                {\n"
        "                    if (const auto st = ::protocyte::write_int32_field("
        not in weird_map_serialize
    )
    assert (
        "                {\n"
        "                    if (const auto st = ::protocyte::write_string_field("
        not in weird_map_serialize
    )


def test_model_decodes_constants_and_array_options() -> None:
    model = build_model(_constant_array_request())

    file_constants = {
        constant.name: constant for constant in model.files["arrays.proto"].constants
    }
    holder = model.messages["demo.Holder"]
    nested = model.messages["demo.Holder.Nested"]
    constants = {constant.name: constant for constant in holder.constants}
    nested_constants = {constant.name: constant for constant in nested.constants}
    fields = {field.name: field for field in holder.fields}
    nested_fields = {field.name: field for field in nested.fields}

    assert file_constants["FILE_CAP"].value == 16
    assert file_constants["FILE_LABEL"].value == "ell"
    assert file_constants["FILE_READY"].value is True
    assert constants["MAGIC_NUMBER"].value == 16
    assert constants["DOUBLE_MAGIC"].value == 32
    assert constants["HEX_MAGIC"].value == 32
    assert constants["HEX_EXPR"].value == 24
    assert constants["LABEL"].value == "ell"
    assert nested_constants["HAS_PREFIX"].value is True
    assert fields["digest"].array_max == 32
    assert fields["digest"].array_fixed is True
    assert fields["blob"].array_max == 16
    assert fields["blob"].array_cpp_max == "16u"
    assert fields["hex_blob"].array_max == 16
    assert fields["hex_blob"].array_cpp_max == "16u"
    assert fields["values"].array_max == 4
    assert fields["values"].repeated_array is True
    assert nested_fields["payload"].array_max == 16
    assert nested_fields["payload"].array_cpp_max == "16u"


def test_rejects_field_cpp_name_collisions() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("field_collision.proto")
    file = request.proto_file.add()
    file.name = "field_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"
    message = file.message_type.add()
    message.name = "Broken"
    for number, name in enumerate(("class", "class_"), start=1):
        field = message.field.add()
        field.name = name
        field.number = number
        field.label = F.LABEL_OPTIONAL
        field.type = F.TYPE_INT32

    response = generate_response(request)

    assert (
        "field collides with 'class' after C++ identifier normalization"
        in response.error
    )


def test_field_collision_checks_only_emitted_accessors() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("accessor_names.proto")
    file = request.proto_file.add()
    file.name = "accessor_names.proto"
    file.package = "demo"
    file.syntax = "proto3"
    message = file.message_type.add()
    message.name = "AccessorNames"

    values = message.field.add()
    values.name = "values"
    values.number = 1
    values.label = F.LABEL_REPEATED
    values.type = F.TYPE_INT32

    set_values = message.field.add()
    set_values.name = "set_values"
    set_values.number = 2
    set_values.label = F.LABEL_OPTIONAL
    set_values.type = F.TYPE_INT32

    response = generate_response(request)

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "accessor_names.protocyte.hpp"
    )
    assert "void clear_values() noexcept" in header
    assert (
        "::protocyte::Status set_set_values(const ::protocyte::i32 value) noexcept"
        in header
    )


def test_rejects_top_level_cpp_type_name_collisions() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("type_collision.proto")
    file = request.proto_file.add()
    file.name = "type_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"
    for name in ("foo", "Foo"):
        message = file.message_type.add()
        message.name = name

    response = generate_response(request)

    assert "type collides with" in response.error
    assert "after C++ identifier normalization" in response.error


def test_rejects_enum_value_cpp_name_collisions() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("enum_value_collision.proto")
    file = request.proto_file.add()
    file.name = "enum_value_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"
    enum = file.enum_type.add()
    enum.name = "Broken"
    for number, name in enumerate(("class", "class_")):
        value = enum.value.add()
        value.name = name
        value.number = number

    response = generate_response(request)

    assert "enum value collides with" in response.error
    assert "after C++ identifier normalization" in response.error


def test_rejects_cpp_namespace_type_collisions() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    for proto_name, package in (("and.proto", "and"), ("and_.proto", "and_")):
        request.file_to_generate.append(proto_name)
        file = request.proto_file.add()
        file.name = proto_name
        file.package = package
        file.syntax = "proto3"
        message = file.message_type.add()
        message.name = "M"

    response = generate_response(request)

    assert "type collides with" in response.error
    assert "after C++ identifier normalization" in response.error


def test_generated_include_guards_are_unique_for_normalized_path_collisions() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    for proto_name, message_name in (
        ("foo-bar.proto", "Hyphen"),
        ("foo_bar.proto", "Underscore"),
    ):
        request.file_to_generate.append(proto_name)
        file = request.proto_file.add()
        file.name = proto_name
        file.package = "demo"
        file.syntax = "proto3"
        message = file.message_type.add()
        message.name = message_name

    response = generate_response(request)

    assert not response.error
    guards = {
        item.name: item.content.split("#ifndef ", maxsplit=1)[1].splitlines()[0]
        for item in response.file
        if item.name.endswith(".hpp")
    }
    assert guards["foo-bar.protocyte.hpp"] != guards["foo_bar.protocyte.hpp"]
    assert guards["foo-bar.protocyte.hpp"].startswith(
        "PROTOCYTE_GENERATED_FOO_BAR_PROTO_"
    )
    assert guards["foo_bar.protocyte.hpp"].startswith(
        "PROTOCYTE_GENERATED_FOO_BAR_PROTO_"
    )


def test_nested_aliases_use_cpp_identifiers() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("nested_alias.proto")
    file = request.proto_file.add()
    file.name = "nested_alias.proto"
    file.package = "demo"
    file.syntax = "proto3"
    message = file.message_type.add()
    message.name = "HasNested"

    enum = message.enum_type.add()
    enum.name = "enum"
    value = enum.value.add()
    value.name = "zero"
    value.number = 0

    nested = message.nested_type.add()
    nested.name = "class"

    response = generate_response(request)

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["nested_alias.protocyte.hpp"]
    assert "using enum_ = HasNested_Enum_;" in header
    assert "using class_ = HasNested_Class_<NestedConfig>;" in header
    assert "using enum = " not in header
    assert "using class = " not in header


def test_len_array_expression_emits_numeric_bound() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("len_bound.proto")
    request.proto_file.extend([_options_file(), _len_bound_file()])

    model = build_model(request)
    field = model.messages["demo.LenBound"].fields[0]
    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert field.array_max == 4
    assert field.array_cpp_max == "4u"
    assert not response.error
    assert "::protocyte::ByteArray<4u> data_;" in files["len_bound.protocyte.hpp"]
    assert '".size()' not in files["len_bound.protocyte.hpp"]


def test_array_expression_emits_validated_numeric_bound_for_cpp_semantics() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("negative_mod_bound.proto")
    request.proto_file.extend(
        [
            _options_file(),
            _array_bound_expr_file("negative_mod_bound.proto", "(-5 % 3) + 1"),
        ]
    )

    model = build_model(request)
    field = model.messages["demo.ArrayBound"].fields[0]
    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert field.array_max == 3
    assert field.array_cpp_max == "3u"
    assert not response.error
    assert (
        "::protocyte::ByteArray<3u> data_;" in files["negative_mod_bound.protocyte.hpp"]
    )
    assert "-5u" not in files["negative_mod_bound.protocyte.hpp"]


def test_array_expression_same_package_file_constant_is_inlined() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("same_package_user.proto")
    request.proto_file.extend(
        [
            _options_file(),
            _same_package_constant_provider_file(),
            _same_package_constant_user_file(),
        ]
    )

    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert not response.error
    assert (
        "::protocyte::ByteArray<6u> data_;" in files["same_package_user.protocyte.hpp"]
    )
    assert "ByteArray<CAP + 1u>" not in files["same_package_user.protocyte.hpp"]


def test_large_integer_division_preserves_precision() -> None:
    assert (
        _ExprParser("9007199254740993 / 1", lambda name: None, "large").parse().value
        == 9007199254740993
    )
    assert _ExprParser("-5 / 2", lambda name: None, "negative").parse().value == -2


def test_f32_integer_literal_rounding_does_not_double_round() -> None:
    literal = 2**63 + 2**39 + 1

    coerced = _coerce_literal(CONSTANT_KIND_FLOAT, literal, "f32 literal")

    assert coerced == float(2**63 + 2**40)
    assert struct.unpack("<I", struct.pack("<f", coerced))[0] == 0x5F000001


@pytest.mark.parametrize("kind", [CONSTANT_KIND_FLOAT, CONSTANT_KIND_DOUBLE])
def test_floating_literal_integer_overflow_has_labeled_error(kind: str) -> None:
    with pytest.raises(
        ProtocyteError, match="huge literal: numeric literal must be finite"
    ):
        _coerce_literal(kind, 10**1000, "huge literal")


@pytest.mark.parametrize(
    ("expression", "expected", "expected_kind"),
    [
        ("I32_NEG + U32_ONE", 0, CONSTANT_KIND_UINT32),
        ("U32_ZERO - I32_ONE", 2**32 - 1, CONSTANT_KIND_UINT32),
        ("I32_NEG_TWO * U32_TWO", 2**32 - 4, CONSTANT_KIND_UINT32),
        ("I32_NEG_TWO / U32_TWO", 2**31 - 1, CONSTANT_KIND_UINT32),
        ("I32_NEG % U32_MAX", 0, CONSTANT_KIND_UINT32),
        ("I64_NEG + U32_ZERO", -1, CONSTANT_KIND_INT64),
        ("I64_NEG + U64_ZERO", 2**64 - 1, CONSTANT_KIND_UINT64),
        ("U64_MAX + I32_ONE", 0, CONSTANT_KIND_UINT64),
        ("I64_NEG_FIVE % U32_TWO", -1, CONSTANT_KIND_INT64),
    ],
)
def test_mixed_integer_arithmetic_uses_cpp_common_conversions(
    expression: str, expected: int, expected_kind: str
) -> None:
    values = {
        "I32_NEG": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT32),
        "I32_NEG_TWO": _TypedValue("numeric", -2, numeric_kind=CONSTANT_KIND_INT32),
        "I32_ONE": _TypedValue("numeric", 1, numeric_kind=CONSTANT_KIND_INT32),
        "U32_ZERO": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT32),
        "U32_ONE": _TypedValue("numeric", 1, numeric_kind=CONSTANT_KIND_UINT32),
        "U32_TWO": _TypedValue("numeric", 2, numeric_kind=CONSTANT_KIND_UINT32),
        "U32_MAX": _TypedValue("numeric", 2**32 - 1, numeric_kind=CONSTANT_KIND_UINT32),
        "I64_NEG": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT64),
        "I64_NEG_FIVE": _TypedValue("numeric", -5, numeric_kind=CONSTANT_KIND_INT64),
        "U64_ZERO": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT64),
        "U64_MAX": _TypedValue("numeric", 2**64 - 1, numeric_kind=CONSTANT_KIND_UINT64),
    }

    parsed = _ExprParser(expression, values.__getitem__, expression).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


@pytest.mark.parametrize(
    ("expression", "expected", "expected_kind"),
    [
        ("-1 + I64_ZERO", 2**32 - 1, CONSTANT_KIND_INT64),
        ("-1 + F64_ZERO", float(2**32 - 1), CONSTANT_KIND_DOUBLE),
    ],
)
def test_contextual_unsigned_values_are_normalized_before_widening(
    expression: str, expected: int | float, expected_kind: str
) -> None:
    values = {
        "I64_ZERO": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_INT64),
        "F64_ZERO": _TypedValue("numeric", 0.0, numeric_kind=CONSTANT_KIND_DOUBLE),
    }

    parsed = _ExprParser(
        expression,
        values.__getitem__,
        expression,
        integer_context=CONSTANT_KIND_UINT32,
    ).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


@pytest.mark.parametrize(
    ("expression", "integer_context", "kind"),
    [
        ("2147483647 + 1", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("-2147483648 - 1", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("2147483647 * 2", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("-2147483648 / -1", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("-2147483648 % -1", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("-(-2147483648)", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("+2147483648", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        (
            "9223372036854775807 + 1",
            CONSTANT_KIND_INT64,
            CONSTANT_KIND_INT64,
        ),
        (
            "-9223372036854775808 / -1",
            CONSTANT_KIND_INT64,
            CONSTANT_KIND_INT64,
        ),
        (
            "-9223372036854775808 % -1",
            CONSTANT_KIND_INT64,
            CONSTANT_KIND_INT64,
        ),
    ],
)
def test_signed_integer_operations_reject_out_of_range_results(
    expression: str, integer_context: str, kind: str
) -> None:
    with pytest.raises(ProtocyteError, match=f"out of range for {kind}"):
        _ExprParser(
            expression,
            lambda name: None,
            expression,
            integer_context=integer_context,
        ).parse()


def test_integer_truth_and_destination_conversion_validate_source_kind() -> None:
    invalid_i32 = _TypedValue("numeric", 2**31, numeric_kind=CONSTANT_KIND_INT32)
    too_large = _TypedValue("numeric", 2**64)
    raw_u32 = _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_UINT32)

    for destination in (
        "bool",
        CONSTANT_KIND_DOUBLE,
        CONSTANT_KIND_UINT64,
    ):
        with pytest.raises(ProtocyteError, match="out of range for int32"):
            _coerce_expression_value(destination, invalid_i32, "invalid i32")
        with pytest.raises(ProtocyteError, match="supported range"):
            _coerce_expression_value(destination, too_large, "too large")

    assert _coerce_expression_value("bool", raw_u32, "raw u32") is True
    assert _coerce_expression_value(CONSTANT_KIND_DOUBLE, raw_u32, "raw u32") == float(
        2**32 - 1
    )
    assert (
        _coerce_expression_value(CONSTANT_KIND_UINT64, raw_u32, "raw u32") == 2**32 - 1
    )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("I32_NEG < U32_ZERO", False),
        ("I32_NEG > U32_ZERO", True),
        ("I64_NEG < U32_ZERO", True),
        ("I32_NEG < U64_ZERO", False),
        ("I64_NEG < U64_ZERO", False),
        ("I32_NEG == U32_MAX", True),
        ("I32_NEG != U32_MAX", False),
        ("I64_NEG == U32_MAX", False),
        ("I64_NEG == U64_MAX", True),
        ("F32_ROUNDED == I32_UNROUNDED", True),
        ("F32_DISTINCT == I32_UNROUNDED", False),
        ("F32_INTEGER_EDGE == U64_F32_EDGE", True),
        ("F64_ROUNDED == I64_UNROUNDED", True),
    ],
)
def test_numeric_comparisons_and_equality_use_common_kind(
    expression: str, expected: bool
) -> None:
    values = {
        "I32_NEG": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT32),
        "I32_UNROUNDED": _TypedValue(
            "numeric", 16777217, numeric_kind=CONSTANT_KIND_INT32
        ),
        "U32_ZERO": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT32),
        "U32_MAX": _TypedValue("numeric", 2**32 - 1, numeric_kind=CONSTANT_KIND_UINT32),
        "I64_NEG": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT64),
        "I64_UNROUNDED": _TypedValue(
            "numeric", 9007199254740993, numeric_kind=CONSTANT_KIND_INT64
        ),
        "U64_F32_EDGE": _TypedValue(
            "numeric",
            2**63 + 2**39 + 1,
            numeric_kind=CONSTANT_KIND_UINT64,
        ),
        "U64_ZERO": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT64),
        "U64_MAX": _TypedValue("numeric", 2**64 - 1, numeric_kind=CONSTANT_KIND_UINT64),
        "F32_ROUNDED": _TypedValue(
            "numeric", 16777216.0, numeric_kind=CONSTANT_KIND_FLOAT
        ),
        "F32_DISTINCT": _TypedValue(
            "numeric", 16777218.0, numeric_kind=CONSTANT_KIND_FLOAT
        ),
        "F32_INTEGER_EDGE": _TypedValue(
            "numeric",
            float(2**63 + 2**40),
            numeric_kind=CONSTANT_KIND_FLOAT,
        ),
        "F64_ROUNDED": _TypedValue(
            "numeric", 9007199254740992.0, numeric_kind=CONSTANT_KIND_DOUBLE
        ),
    }

    parsed = _ExprParser(expression, values.__getitem__, expression).parse()

    assert parsed.value is expected


@pytest.mark.parametrize(
    ("expression", "integer_context", "expected", "expected_kind"),
    [
        ("~0", CONSTANT_KIND_INT32, -1, CONSTANT_KIND_INT32),
        ("~0", CONSTANT_KIND_UINT32, 2**32 - 1, CONSTANT_KIND_UINT32),
        ("~0", CONSTANT_KIND_INT64, -1, CONSTANT_KIND_INT64),
        ("~0", CONSTANT_KIND_UINT64, 2**64 - 1, CONSTANT_KIND_UINT64),
        ("true & false", None, 0, CONSTANT_KIND_INT32),
        ("true | false", None, 1, CONSTANT_KIND_INT32),
        ("true ^ true", None, 0, CONSTANT_KIND_INT32),
        ("~true", None, -2, CONSTANT_KIND_INT32),
        ("true << 2", None, 4, CONSTANT_KIND_INT32),
        ("8 >> true", None, 4, CONSTANT_KIND_INT32),
        ("-8 >> 2", CONSTANT_KIND_INT32, -2, CONSTANT_KIND_INT32),
        (
            "1 << 31",
            CONSTANT_KIND_INT32,
            -(2**31),
            CONSTANT_KIND_INT32,
        ),
        ("-1 << 1", CONSTANT_KIND_INT32, -2, CONSTANT_KIND_INT32),
        ("1073741824 << 2", CONSTANT_KIND_INT32, 0, CONSTANT_KIND_INT32),
        (
            "1 << 63",
            CONSTANT_KIND_INT64,
            -(2**63),
            CONSTANT_KIND_INT64,
        ),
        (
            "-9223372036854775808 << 1",
            CONSTANT_KIND_INT64,
            0,
            CONSTANT_KIND_INT64,
        ),
        (
            "0xffffffff << 4",
            CONSTANT_KIND_UINT32,
            0xFFFFFFF0,
            CONSTANT_KIND_UINT32,
        ),
    ],
)
def test_bitwise_expression_values_follow_fixed_width_integer_semantics(
    expression: str,
    integer_context: str | None,
    expected: int,
    expected_kind: str,
) -> None:
    parsed = _ExprParser(
        expression,
        lambda name: None,
        expression,
        integer_context=integer_context,
    ).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 | 2 ^ 3 & 4", 3),
        ("1 << 2 + 1", 8),
        ("1 + 1 << 1", 4),
        ("1 & 3 == 1", 0),
        ("1 | 0 && 0", False),
        ("(4 & 1) || 2", True),
        ("!(4 & 1)", True),
    ],
)
def test_bitwise_expression_precedence_and_integer_logical_conversion(
    expression: str, expected: int | bool
) -> None:
    assert (
        _ExprParser(expression, lambda name: None, expression).parse().value == expected
    )


@pytest.mark.parametrize(
    ("expression", "expected", "expected_kind"),
    [
        ("U32 & I64", 0xFFFFFFFF, CONSTANT_KIND_INT64),
        ("I32 | U64", 2**64 - 1, CONSTANT_KIND_UINT64),
        ("I32 ^ U32", 0xFFFFFF0F, CONSTANT_KIND_UINT32),
    ],
)
def test_bitwise_expression_uses_usual_mixed_integer_conversions(
    expression: str, expected: int, expected_kind: str
) -> None:
    values = {
        "I32": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT32),
        "U32": _TypedValue("numeric", 0xF0, numeric_kind=CONSTANT_KIND_UINT32),
        "I64": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT64),
        "U64": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT64),
    }
    if expression == "U32 & I64":
        values["U32"].value = 0xFFFFFFFF

    parsed = _ExprParser(expression, values.__getitem__, expression).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


def test_bitwise_operands_are_normalized_in_their_source_kinds() -> None:
    values = {
        "I64_HIGH_BIT": _TypedValue(
            "numeric", 1 << 32, numeric_kind=CONSTANT_KIND_INT64
        ),
        "RAW_U32_NEGATIVE": _TypedValue(
            "numeric", -1, numeric_kind=CONSTANT_KIND_UINT32
        ),
    }

    contextual = _ExprParser(
        "-1 & I64_HIGH_BIT",
        values.__getitem__,
        "contextual u32 bitwise",
        integer_context=CONSTANT_KIND_UINT32,
    ).parse()
    referenced = _ExprParser(
        "RAW_U32_NEGATIVE & I64_HIGH_BIT",
        values.__getitem__,
        "referenced u32 bitwise",
    ).parse()

    assert contextual.value == 0
    assert contextual.numeric_kind == CONSTANT_KIND_INT64
    assert referenced.value == 0
    assert referenced.numeric_kind == CONSTANT_KIND_INT64


def test_bitwise_conversion_rejects_an_invalid_signed_source_value() -> None:
    values = {
        "INVALID_I32": _TypedValue(
            "numeric", 1 << 32, numeric_kind=CONSTANT_KIND_INT32
        ),
        "U64_ZERO": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT64),
    }

    with pytest.raises(ProtocyteError, match="out of range for int32"):
        _ExprParser(
            "INVALID_I32 & U64_ZERO",
            values.__getitem__,
            "invalid signed source",
        ).parse()


def test_shift_operands_are_normalized_in_their_source_kinds() -> None:
    values = {
        "U32_MAX": _TypedValue("numeric", 2**32 - 1, numeric_kind=CONSTANT_KIND_UINT32),
        "RAW_U32_NEGATIVE": _TypedValue(
            "numeric", -1, numeric_kind=CONSTANT_KIND_UINT32
        ),
    }

    shifted_by_wrapped_count = _ExprParser(
        "1 << -U32_MAX",
        values.__getitem__,
        "wrapped shift count",
    ).parse()
    shifted_wrapped_value = _ExprParser(
        "RAW_U32_NEGATIVE << 1",
        values.__getitem__,
        "wrapped shift value",
    ).parse()

    assert shifted_by_wrapped_count.value == 2
    assert shifted_by_wrapped_count.numeric_kind == CONSTANT_KIND_INT32
    assert shifted_wrapped_value.value == 2**32 - 2
    assert shifted_wrapped_value.numeric_kind == CONSTANT_KIND_UINT32


@pytest.mark.parametrize(
    ("expression", "integer_context", "error"),
    [
        ("1.0 & 1", None, "require integer or bool operands"),
        ('"text" | 1', None, "require integer or bool operands"),
        ("1 << -1", None, "shift count must not be negative"),
        ("1 << 32", None, "shift count 32 must be less than 32"),
        ("1.0 && true", None, "expected bool or integer expression"),
    ],
)
def test_bitwise_expression_rejects_invalid_operands_and_shifts(
    expression: str, integer_context: str | None, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        _ExprParser(
            expression,
            lambda name: None,
            expression,
            integer_context=integer_context,
        ).parse()


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("true || (1 / 0 == 0)", True),
        ("false && (1 / 0 == 0)", False),
        ("true || (sqrt(-1) == 0)", True),
        ("false && (pow(2, -1) == 0)", False),
        ("true || (false && (1 / 0 == 0))", True),
    ],
)
def test_logical_operators_do_not_evaluate_dead_rhs_values(
    expression: str, expected: bool
) -> None:
    parsed = _ExprParser(expression, lambda name: None, expression).parse()

    assert parsed.value is expected


@pytest.mark.parametrize(
    ("expression", "error"),
    [
        ("false || (1 / 0 == 0)", "division by zero"),
        ("true && (sqrt(-1) == 0)", "sqrt\\(\\) domain error"),
    ],
)
def test_logical_operators_propagate_live_rhs_errors(
    expression: str, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        _ExprParser(expression, lambda name: None, expression).parse()


@pytest.mark.parametrize(
    ("expression", "error"),
    [
        ("true || 1.0", "expected bool or integer expression"),
        ("false && 1.0", "expected bool or integer expression"),
        ("true || unsupported()", "unsupported function unsupported\\(\\)"),
        ("false && sqrt(1, 2)", "sqrt\\(\\) expects one numeric argument"),
        ("true || (1.0 % 1 == 0)", "only supports integer operands"),
    ],
)
def test_logical_operators_still_type_check_dead_rhs(
    expression: str, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        _ExprParser(expression, lambda name: None, expression).parse()


@pytest.mark.parametrize(
    ("expression", "expected", "expected_kind"),
    [
        ("0xdeadbeef", 0xDEADBEEF, CONSTANT_KIND_UINT32),
        ("0xFE", 0xFE, CONSTANT_KIND_INT32),
        ("0XDEAD", 0xDEAD, CONSTANT_KIND_INT32),
        ("0x1e2", 0x1E2, CONSTANT_KIND_INT32),
        ("0xBEEF & 0xffff", 0xBEEF, CONSTANT_KIND_INT32),
        ("0x1E + 1", 0x1F, CONSTANT_KIND_INT32),
        ("0x7fffffff", 0x7FFFFFFF, CONSTANT_KIND_INT32),
        ("0x80000000", 0x80000000, CONSTANT_KIND_UINT32),
        ("0x100000000", 0x100000000, CONSTANT_KIND_INT64),
        ("0x7fffffffffffffff", 0x7FFFFFFFFFFFFFFF, CONSTANT_KIND_INT64),
        ("0x8000000000000000", 0x8000000000000000, CONSTANT_KIND_UINT64),
        ("1e2", 100.0, CONSTANT_KIND_DOUBLE),
    ],
)
def test_hexadecimal_literals_containing_e_are_not_floats(
    expression: str, expected: int | float, expected_kind: str
) -> None:
    parsed = _ExprParser(expression, lambda name: None, expression).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


@pytest.mark.parametrize(
    ("expression", "expected", "expected_kind"),
    [
        ("-1 == 0xffffffff", True, None),
        ("-1 < 0xffffffff", False, None),
        ("0xffffffff + 1", 0, CONSTANT_KIND_UINT32),
        ("~0xffffffff", 0, CONSTANT_KIND_UINT32),
        ("pow(2, -0xffffffff)", 2, CONSTANT_KIND_UINT32),
    ],
)
def test_hexadecimal_literals_use_cpp_unsuffixed_integer_kinds(
    expression: str, expected: int | bool, expected_kind: str | None
) -> None:
    parsed = _ExprParser(expression, lambda name: None, expression).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


@pytest.mark.parametrize(
    "expression",
    [
        r'"\x"',
        r'"\u12"',
        r'"\q"',
        r'"\8"',
        r'"\400"',
        '"line\nbreak"',
        '"null\0byte"',
    ],
)
def test_expression_string_literals_reject_malformed_python_syntax(
    expression: str,
) -> None:
    with pytest.raises(ProtocyteError, match="invalid string literal"):
        _ExprParser(expression, lambda name: None, "malformed string").parse()


@pytest.mark.parametrize(
    "expression",
    [
        r'true || ("\q" == "")',
        r'false && ("\400" == "")',
    ],
)
def test_logical_operators_reject_invalid_string_escapes_on_dead_rhs(
    expression: str,
) -> None:
    with pytest.raises(ProtocyteError, match="invalid string literal"):
        _ExprParser(expression, lambda name: None, "dead RHS string").parse()


@pytest.mark.parametrize("expression", [r'"\ud800"', r'"\ud83d\ude00"'])
def test_expression_string_literals_reject_non_utf8_surrogates(
    expression: str,
) -> None:
    with pytest.raises(ProtocyteError, match="string value must be valid UTF-8"):
        _ExprParser(expression, lambda name: None, "non-UTF-8 string").parse()


def test_string_destinations_reject_non_utf8_values_before_emission() -> None:
    with pytest.raises(ProtocyteError, match="string value must be valid UTF-8"):
        _coerce_literal(CONSTANT_KIND_STRING, "\ud800", "string literal")
    with pytest.raises(ProtocyteError, match="string value must be valid UTF-8"):
        _coerce_expression_value(
            CONSTANT_KIND_STRING,
            _TypedValue(CONSTANT_KIND_STRING, "\ud800"),
            "string expression",
        )


@pytest.mark.parametrize(
    "expression",
    [
        "(" * (_MAX_EXPRESSION_NESTING + 1)
        + "1"
        + ")" * (_MAX_EXPRESSION_NESTING + 1),
        "i32(" * (_MAX_EXPRESSION_NESTING + 1)
        + "1"
        + ")" * (_MAX_EXPRESSION_NESTING + 1),
        "-" * (_MAX_EXPRESSION_NESTING + 1) + "1",
    ],
)
def test_expression_nesting_limit_returns_a_stable_error(expression: str) -> None:
    with pytest.raises(
        ProtocyteError,
        match=rf"expression nesting exceeds maximum depth of {_MAX_EXPRESSION_NESTING}",
    ):
        _ExprParser(expression, lambda name: None, "deep expression").parse()


def test_expression_nesting_limit_accepts_the_boundary() -> None:
    expression = (
        "(" * _MAX_EXPRESSION_NESTING
        + "1"
        + ")" * _MAX_EXPRESSION_NESTING
    )

    parsed = _ExprParser(expression, lambda name: None, expression).parse()

    assert parsed.value == 1


def test_expression_parser_translates_residual_recursion_errors() -> None:
    def recurse(_name: str) -> _TypedValue:
        raise RecursionError

    with pytest.raises(
        ProtocyteError,
        match="expression evaluation exceeds safe recursion depth",
    ):
        _ExprParser("RECURSE", recurse, "recursive expression").parse()


def test_bitwise_operators_work_in_every_expression_destination() -> None:
    request = _bitwise_expression_request()
    model = build_model(request)
    message = model.messages["demo.BitwiseExpressions"]
    constants = {constant.name: constant.value for constant in message.constants}

    assert model.files["bitwise_expressions.proto"].constants[0].value == 10
    assert constants == {
        "I32_MASK": -1,
        "U32_MASK": 2**32 - 1,
        "I64_SHIFT": 1 << 40,
        "U64_MASK": 2**64 - 16,
        "F32_BITS": 9.0,
        "F64_BITS": 16.0,
        "BOOL_BITS": True,
        "BOOL_LOGIC": True,
        "BOOL_ARITH": True,
        "STR_BITS": "b",
    }
    assert message.fields[0].array_max == 9

    response = generate_response(request)
    assert not response.error
    header = next(
        item.content
        for item in response.file
        if item.name == "bitwise_expressions.protocyte.hpp"
    )
    assert "inline constexpr ::protocyte::u32 BASE_BITS {10u};" in header
    assert "static constexpr ::protocyte::i32 I32_MASK {-1};" in header
    assert "static constexpr ::protocyte::u32 U32_MASK {4294967295u};" in header
    assert "static constexpr ::protocyte::i64 I64_SHIFT {1099511627776ll};" in header
    assert (
        "static constexpr ::protocyte::u64 U64_MASK {18446744073709551600ull};"
        in header
    )
    assert "static constexpr bool BOOL_BITS {true};" in header
    assert "::protocyte::ByteArray<9u> data_;" in header


@pytest.mark.parametrize(
    ("expression", "expected", "expected_family", "expected_kind"),
    [
        ("bool(false)", False, CONSTANT_KIND_BOOL, None),
        ("bool(0)", False, CONSTANT_KIND_BOOL, None),
        ("bool(-0.0)", False, CONSTANT_KIND_BOOL, None),
        ("bool(0.5)", True, CONSTANT_KIND_BOOL, None),
        ("i32(true)", 1, "numeric", CONSTANT_KIND_INT32),
        ("i32(4294967295)", -1, "numeric", CONSTANT_KIND_INT32),
        ("i32(-2.9)", -2, "numeric", CONSTANT_KIND_INT32),
        ("u32(-1)", 2**32 - 1, "numeric", CONSTANT_KIND_UINT32),
        ("u32(4294967297)", 1, "numeric", CONSTANT_KIND_UINT32),
        ("u32(-0.5)", 0, "numeric", CONSTANT_KIND_UINT32),
        ("i64(false)", 0, "numeric", CONSTANT_KIND_INT64),
        (
            "i64(18446744073709551615)",
            -1,
            "numeric",
            CONSTANT_KIND_INT64,
        ),
        ("u64(true)", 1, "numeric", CONSTANT_KIND_UINT64),
        ("u64(-1)", 2**64 - 1, "numeric", CONSTANT_KIND_UINT64),
        ("f32(16777217)", 16777216.0, "numeric", CONSTANT_KIND_FLOAT),
        ("f32(true)", 1.0, "numeric", CONSTANT_KIND_FLOAT),
        (
            "f64(9007199254740993)",
            9007199254740992.0,
            "numeric",
            CONSTANT_KIND_DOUBLE,
        ),
        ("f64(false)", 0.0, "numeric", CONSTANT_KIND_DOUBLE),
        ('str("hello")', "hello", CONSTANT_KIND_STRING, None),
        ("str(true)", "true", CONSTANT_KIND_STRING, None),
        ("str(-42)", "-42", CONSTANT_KIND_STRING, None),
        ("str(f32(1.5))", "1.5", CONSTANT_KIND_STRING, None),
    ],
)
def test_scalar_casts_convert_supported_values(
    expression: str,
    expected: object,
    expected_family: str,
    expected_kind: str | None,
) -> None:
    parsed = _ExprParser(expression, lambda name: None, expression).parse()

    assert parsed.value == expected
    assert parsed.family == expected_family
    assert parsed.numeric_kind == expected_kind


@pytest.mark.parametrize(
    ("expression", "integer_context", "expected", "expected_kind"),
    [
        (
            "f64(-3)",
            CONSTANT_KIND_UINT32,
            -3.0,
            CONSTANT_KIND_DOUBLE,
        ),
        (
            "i32(4294967295)",
            CONSTANT_KIND_INT32,
            -1,
            CONSTANT_KIND_INT32,
        ),
        (
            "u32(-1) + 1",
            CONSTANT_KIND_INT64,
            2**32,
            CONSTANT_KIND_INT64,
        ),
        (
            "i32(u32(-1))",
            CONSTANT_KIND_UINT64,
            -1,
            CONSTANT_KIND_INT32,
        ),
        (
            "u32(i32(-1))",
            CONSTANT_KIND_INT64,
            2**32 - 1,
            CONSTANT_KIND_UINT32,
        ),
    ],
)
def test_scalar_cast_arguments_have_an_independent_literal_context(
    expression: str,
    integer_context: str,
    expected: int | float,
    expected_kind: str,
) -> None:
    parsed = _ExprParser(
        expression,
        lambda name: None,
        expression,
        integer_context=integer_context,
    ).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


def test_scalar_casts_support_nested_comparisons_with_cpp_conversions() -> None:
    equal = _ExprParser(
        "i32(-1) == u32(4294967295)",
        lambda name: None,
        "mixed cast equality",
    ).parse()
    ordered = _ExprParser(
        "i64(-1) < u32(0)",
        lambda name: None,
        "mixed cast ordering",
    ).parse()

    assert equal.value is True
    assert ordered.value is True


def test_str_cast_preserves_floating_signed_zero() -> None:
    parsed = _ExprParser(
        "str(f64(-0.0))",
        lambda name: None,
        "string negative zero",
    ).parse()

    assert parsed.value == "-0.0"


@pytest.mark.parametrize(
    "name",
    ["bool", "i32", "u32", "i64", "u64", "f32", "f64", "str"],
)
@pytest.mark.parametrize("arguments", ["", "1, 2"])
def test_scalar_casts_require_exactly_one_argument(name: str, arguments: str) -> None:
    with pytest.raises(
        ProtocyteError, match=rf"{name}\(\) expects one scalar argument"
    ):
        _ExprParser(
            f"{name}({arguments})",
            lambda value: None,
            f"{name} arity",
        ).parse()


@pytest.mark.parametrize("name", ["bool", "i32", "u32", "i64", "u64", "f32", "f64"])
def test_numeric_and_bool_casts_do_not_parse_strings(name: str) -> None:
    with pytest.raises(
        ProtocyteError, match=rf"{name}\(\) expects one bool or numeric argument"
    ):
        _ExprParser(
            f'{name}("1")',
            lambda value: None,
            f"{name} string source",
        ).parse()


@pytest.mark.parametrize(
    ("expression", "error"),
    [
        ("i32(2147483648.0)", "i32\\(\\) result is out of range for int32"),
        ("u32(-1.0)", "u32\\(\\) result is out of range for uint32"),
        ("i64(9223372036854775808.0)", "i64\\(\\) result is out of range for int64"),
        ("u64(-1.0)", "u64\\(\\) result is out of range for uint64"),
        ("f32(1e100)", "f32\\(\\) result is not finite"),
    ],
)
def test_scalar_casts_reject_undefined_or_nonfinite_results(
    expression: str, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        _ExprParser(expression, lambda name: None, expression).parse()


@pytest.mark.parametrize(
    ("name", "expression"),
    [
        ("pow", "pow(X, 2)"),
        ("abs", "abs(X)"),
        ("min", "min(X, X)"),
        ("max", "max(X, X)"),
        ("sqrt", "sqrt(X)"),
        ("exp", "exp(X)"),
        ("log", "log(X)"),
        ("log2", "log2(X)"),
        ("log10", "log10(X)"),
        ("ceil", "ceil(X)"),
        ("floor", "floor(X)"),
        ("trunc", "trunc(X)"),
        ("round", "round(X)"),
    ],
)
@pytest.mark.parametrize(
    ("source", "source_kind"),
    [
        (_TypedValue("bool", True), "bool"),
        (
            _TypedValue("numeric", 4, numeric_kind=CONSTANT_KIND_INT32),
            CONSTANT_KIND_INT32,
        ),
        (
            _TypedValue("numeric", 4, numeric_kind=CONSTANT_KIND_UINT32),
            CONSTANT_KIND_UINT32,
        ),
        (
            _TypedValue("numeric", 4, numeric_kind=CONSTANT_KIND_INT64),
            CONSTANT_KIND_INT64,
        ),
        (
            _TypedValue("numeric", 4, numeric_kind=CONSTANT_KIND_UINT64),
            CONSTANT_KIND_UINT64,
        ),
        (
            _TypedValue("numeric", 4.0, numeric_kind=CONSTANT_KIND_FLOAT),
            CONSTANT_KIND_FLOAT,
        ),
        (
            _TypedValue("numeric", 4.0, numeric_kind=CONSTANT_KIND_DOUBLE),
            CONSTANT_KIND_DOUBLE,
        ),
    ],
)
def test_math_functions_accept_every_numeric_kind_and_bool(
    name: str, expression: str, source: _TypedValue, source_kind: str
) -> None:
    parsed = _ExprParser(expression, {"X": source}.__getitem__, expression).parse()

    if name in {
        "sqrt",
        "exp",
        "log",
        "log2",
        "log10",
        "ceil",
        "floor",
        "trunc",
        "round",
    }:
        expected_kind = (
            CONSTANT_KIND_FLOAT
            if source_kind == CONSTANT_KIND_FLOAT
            else CONSTANT_KIND_DOUBLE
        )
    elif source_kind == "bool":
        expected_kind = CONSTANT_KIND_INT32
    else:
        expected_kind = source_kind
    assert parsed.numeric_kind == expected_kind
    assert isinstance(parsed.value, int | float)
    assert math.isfinite(parsed.value)


@pytest.mark.parametrize(
    ("expression", "integer_context", "expected", "expected_kind"),
    [
        ("pow(0, 0)", None, 1, CONSTANT_KIND_INT32),
        ("pow(2, -3.0)", None, 0.125, CONSTANT_KIND_DOUBLE),
        ("pow(-1, -3.0)", None, -1.0, CONSTANT_KIND_DOUBLE),
        ("pow(2.0, -3.0)", None, 0.125, CONSTANT_KIND_DOUBLE),
        ("pow(2, f64(-3))", CONSTANT_KIND_UINT32, 0.125, CONSTANT_KIND_DOUBLE),
        ("pow(2, f32(-3))", CONSTANT_KIND_UINT32, 0.125, CONSTANT_KIND_FLOAT),
        ("pow(2, -3)", CONSTANT_KIND_UINT32, 0, CONSTANT_KIND_UINT32),
        ("pow(2, -3)", CONSTANT_KIND_UINT64, 0, CONSTANT_KIND_UINT64),
        ("pow(0, -1)", CONSTANT_KIND_UINT32, 0, CONSTANT_KIND_UINT32),
        ("pow(0.0, -1)", CONSTANT_KIND_UINT32, 0.0, CONSTANT_KIND_DOUBLE),
        ("pow(-1, -3)", CONSTANT_KIND_UINT32, 2**32 - 1, CONSTANT_KIND_UINT32),
        ("pow(65536, 2)", CONSTANT_KIND_UINT32, 0, CONSTANT_KIND_UINT32),
        (
            "pow(2, 18446744073709551615)",
            CONSTANT_KIND_UINT64,
            0,
            CONSTANT_KIND_UINT64,
        ),
        ("pow(2.0, 3)", None, 8.0, CONSTANT_KIND_DOUBLE),
    ],
)
def test_pow_semantics(
    expression: str,
    integer_context: str | None,
    expected: int | float,
    expected_kind: str,
) -> None:
    parsed = _ExprParser(
        expression,
        lambda name: None,
        expression,
        integer_context=integer_context,
    ).parse()

    assert parsed.value == expected
    assert parsed.numeric_kind == expected_kind


def test_pow_rounds_f32_before_nested_operations() -> None:
    source = _TypedValue(
        "numeric",
        struct.unpack("<f", struct.pack("<f", 1.1))[0],
        numeric_kind=CONSTANT_KIND_FLOAT,
    )
    parsed = _ExprParser("pow(F, 2) + F", {"F": source}.__getitem__, "f32 pow").parse()
    expected = struct.unpack(
        "<f",
        struct.pack(
            "<f",
            struct.unpack("<f", struct.pack("<f", source.value * source.value))[0]
            + source.value,
        ),
    )[0]

    assert parsed.value == expected
    assert parsed.numeric_kind == CONSTANT_KIND_FLOAT


def test_pow_rounds_explicit_f32_exponent_before_evaluation() -> None:
    source = _TypedValue("numeric", -1.0, numeric_kind=CONSTANT_KIND_FLOAT)
    parsed = _ExprParser(
        "pow(F, f32(-16777217))",
        {"F": source}.__getitem__,
        "f32 negative exponent",
        integer_context=CONSTANT_KIND_UINT32,
    ).parse()

    assert parsed.value == 1.0
    assert parsed.numeric_kind == CONSTANT_KIND_FLOAT


@pytest.mark.parametrize("exponent", [-23, -305])
def test_pow_with_an_explicit_f64_exponent_is_accurately_rounded(
    exponent: int,
) -> None:
    expression = f"pow(10, f64({exponent}))"
    parsed = _ExprParser(expression, lambda name: None, expression).parse()

    assert parsed.value == math.pow(10.0, float(exponent))
    assert parsed.numeric_kind == CONSTANT_KIND_DOUBLE


@pytest.mark.parametrize(
    ("expression", "integer_context", "error"),
    [
        ("pow(0, -1)", None, "pow\\(\\) domain error"),
        ("pow(0.0, -1)", None, "pow\\(\\) domain error"),
        ("pow(2, -3)", None, "pow\\(\\) domain error"),
        ("pow(2.0, -3)", None, "pow\\(\\) domain error"),
        ("pow(-2, 0.5)", None, "pow\\(\\) domain error"),
        (
            "pow(2, 31)",
            CONSTANT_KIND_INT32,
            "pow\\(\\) result is out of range for int32",
        ),
        ("pow(2.0, 1024)", None, "pow\\(\\) result is not finite"),
        (
            'pow("bad", 2)',
            None,
            "pow\\(\\) expects numeric arguments",
        ),
        ("pow(2)", None, "pow\\(\\) expects two numeric arguments"),
        (
            "pow(2, 100000000000000000000000000)",
            None,
            "pow\\(\\) argument is outside the supported numeric range",
        ),
        (
            "pow(2, 4294967296)",
            CONSTANT_KIND_UINT32,
            "value 4294967296 is out of range for uint32",
        ),
    ],
)
def test_pow_rejects_invalid_or_unrepresentable_results(
    expression: str, integer_context: str | None, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        _ExprParser(
            expression,
            lambda name: None,
            expression,
            integer_context=integer_context,
        ).parse()


def test_abs_preserves_kind_and_normalizes_floating_negative_zero() -> None:
    negative_zero = _TypedValue("numeric", -0.0, numeric_kind=CONSTANT_KIND_DOUBLE)
    parsed = _ExprParser("abs(Z)", {"Z": negative_zero}.__getitem__, "abs zero").parse()

    assert parsed.value == 0.0
    assert math.copysign(1.0, parsed.value) == 1.0
    assert parsed.numeric_kind == CONSTANT_KIND_DOUBLE


@pytest.mark.parametrize(
    ("expression", "integer_context", "kind"),
    [
        ("abs(-2147483648)", CONSTANT_KIND_INT32, CONSTANT_KIND_INT32),
        ("abs(-9223372036854775808)", CONSTANT_KIND_INT64, CONSTANT_KIND_INT64),
    ],
)
def test_abs_rejects_signed_minimum(
    expression: str, integer_context: str, kind: str
) -> None:
    with pytest.raises(
        ProtocyteError, match=f"abs\\(\\) result is out of range for {kind}"
    ):
        _ExprParser(
            expression,
            lambda name: None,
            expression,
            integer_context=integer_context,
        ).parse()


def test_min_max_use_common_kind_and_keep_first_equal_value() -> None:
    values = {
        "U": _TypedValue("numeric", 0, numeric_kind=CONSTANT_KIND_UINT32),
        "NEG": _TypedValue("numeric", -1, numeric_kind=CONSTANT_KIND_INT32),
        "NZ": _TypedValue("numeric", -0.0, numeric_kind=CONSTANT_KIND_DOUBLE),
        "PZ": _TypedValue("numeric", 0.0, numeric_kind=CONSTANT_KIND_DOUBLE),
    }

    promoted = _ExprParser("max(U, NEG)", values.__getitem__, "mixed max").parse()
    min_zero = _ExprParser("min(NZ, PZ)", values.__getitem__, "min zero").parse()
    max_zero = _ExprParser("max(NZ, PZ)", values.__getitem__, "max zero").parse()

    assert promoted.value == 2**32 - 1
    assert promoted.numeric_kind == CONSTANT_KIND_UINT32
    assert math.copysign(1.0, min_zero.value) == -1.0
    assert math.copysign(1.0, max_zero.value) == -1.0


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("ceil(2.1)", 3.0),
        ("ceil(-2.1)", -2.0),
        ("floor(2.9)", 2.0),
        ("floor(-2.1)", -3.0),
        ("trunc(2.9)", 2.0),
        ("trunc(-2.9)", -2.0),
        ("round(2.5)", 3.0),
        ("round(-2.5)", -3.0),
        ("round(0.49999999999999994)", 0.0),
        ("round(0.5000000000000001)", 1.0),
        ("round(-0.5000000000000001)", -1.0),
    ],
)
def test_rounding_functions_match_cpp_semantics(
    expression: str, expected: float
) -> None:
    assert (
        _ExprParser(expression, lambda name: None, expression).parse().value == expected
    )


@pytest.mark.parametrize("name", ["ceil", "trunc", "round"])
def test_rounding_functions_preserve_negative_zero(name: str) -> None:
    parsed = _ExprParser(
        f"{name}(-0.25)", lambda value: None, f"{name} negative zero"
    ).parse()

    assert parsed.value == 0.0
    assert math.copysign(1.0, parsed.value) == -1.0


def test_round_preserves_negative_zero_immediately_below_half() -> None:
    parsed = _ExprParser(
        "round(-0.49999999999999994)",
        lambda value: None,
        "round below half",
    ).parse()

    assert parsed.value == 0.0
    assert math.copysign(1.0, parsed.value) == -1.0


@pytest.mark.parametrize(
    ("expression", "error"),
    [
        ("sqrt(-1)", "sqrt\\(\\) domain error"),
        ("log(0)", "log\\(\\) domain error"),
        ("log2(-1)", "log2\\(\\) domain error"),
        ("log10(0)", "log10\\(\\) domain error"),
        ("exp(1000)", "exp\\(\\) result is not finite"),
        ('abs("bad")', "abs\\(\\) expects numeric arguments"),
        ("min(1)", "min\\(\\) expects at least two numeric arguments"),
        ('max(1, "bad")', "max\\(\\) expects numeric arguments"),
        ("sqrt(1, 2)", "sqrt\\(\\) expects one numeric argument"),
    ],
)
def test_math_functions_reject_invalid_arguments_and_domains(
    expression: str, error: str
) -> None:
    with pytest.raises(ProtocyteError, match=error):
        _ExprParser(expression, lambda name: None, expression).parse()


def test_math_functions_work_in_every_expression_destination() -> None:
    request = _math_expression_request()
    model = build_model(request)
    message = model.messages["demo.MathExpressions"]
    constants = {constant.name: constant.value for constant in message.constants}

    assert model.files["math_expressions.proto"].constants[0].value == 3
    assert constants["I32_POWER"] == 32
    assert constants["I32_TRUNC"] == -2
    assert constants["U32_MAX"] == 5
    assert constants["U32_TRUNC"] == 2
    assert constants["U32_NEGATIVE_POWER"] == 1
    assert constants["I64_POWER"] == 1 << 40
    assert constants["U64_POWER"] == 1 << 63
    assert (
        constants["F32_ROOT"]
        == struct.unpack("<f", struct.pack("<f", math.sqrt(2.0)))[0]
    )
    assert constants["F64_NESTED"] == pytest.approx(2.0)
    assert constants["BOOL_MATH"] is True
    assert constants["BOOL_MIXED_EQUAL"] is True
    assert constants["BOOL_F32_EQUAL"] is True
    assert constants["STR_MATH"] == "b"
    assert message.fields[0].array_max == 7

    response = generate_response(request)
    assert not response.error
    header = next(
        item.content
        for item in response.file
        if item.name == "math_expressions.protocyte.hpp"
    )
    assert "inline constexpr ::protocyte::u32 PACKAGE_ROOT {3u};" in header
    assert "static constexpr ::protocyte::i32 I32_TRUNC {-2};" in header
    assert "static constexpr ::protocyte::u32 U32_TRUNC {2u};" in header
    assert "static constexpr ::protocyte::u32 U32_NEGATIVE_POWER {1u};" in header
    assert "static constexpr bool BOOL_MATH {true};" in header
    assert "static constexpr bool BOOL_MIXED_EQUAL {true};" in header
    assert "static constexpr bool BOOL_F32_EQUAL {true};" in header
    assert "::protocyte::ByteArray<7u> data_;" in header
    assert all(f"{name}(" not in header for name in ("pow", "sqrt", "exp", "log"))


def test_generated_header_emits_constants_and_array_storage() -> None:
    response = generate_response(_constant_array_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["arrays.protocyte.hpp"]
    runtime_header = files["protocyte/runtime/runtime.hpp"]

    assert "#include <string_view>" not in header
    assert "::std::string_view" not in header
    assert "inline constexpr ::protocyte::u32 FILE_CAP {16u};" in header
    assert 'inline constexpr ::protocyte::StringView FILE_LABEL {"ell", 3u};' in header
    assert "inline constexpr bool FILE_READY {true};" in header
    assert "static constexpr ::protocyte::i32 MAGIC_NUMBER {16};" in header
    assert "static constexpr ::protocyte::i32 DOUBLE_MAGIC {32};" in header
    assert "static constexpr ::protocyte::u32 HEX_MAGIC {32u};" in header
    assert "static constexpr ::protocyte::i32 HEX_EXPR {24};" in header
    assert 'static constexpr ::protocyte::StringView LABEL {"ell", 3u};' in header
    assert "static constexpr bool HAS_PREFIX {true};" in header
    assert "::protocyte::FixedByteArray<32u> digest_;" in header
    assert "::protocyte::ByteArray<16u> blob_;" in header
    assert "::protocyte::ByteArray<16u> hex_blob_;" in header
    assert "::protocyte::Array<::protocyte::i32, 4u> values_;" in header
    assert "bool has_digest() const noexcept { return digest_.has_value(); }" in header
    assert "::protocyte::Span<::protocyte::u8> mutable_digest() noexcept {" in header
    assert "if (ctx_->limits.max_string_bytes < 32u) {" in header
    assert "::protocyte::usize digest_size() const noexcept" not in header
    assert "digest_max_size" not in header
    assert (
        "::protocyte::Status resize_blob(const ::protocyte::usize size) noexcept"
        in header
    )
    assert (
        "::protocyte::Status resize_digest_for_overwrite(const ::protocyte::usize size) noexcept"
        in header
    )
    assert (
        "::protocyte::Status resize_blob_for_overwrite(const ::protocyte::usize size) noexcept"
        in header
    )
    assert "if (const auto st = blob_.resize_for_overwrite(size); !st)" in header
    assert (
        "::protocyte::Span<const ::protocyte::u8> digest() const noexcept { return digest_.view(); }"
        in header
    )
    compact_header = "".join(header.split())
    assert (
        "template<classValue>::protocyte::Statusset_digest(constValue&value)noexcept"
        in compact_header
    )
    assert (
        "template<classValue>::protocyte::Statusset_blob(constValue&value)noexcept"
        in compact_header
    )
    assert (
        compact_header.count(
            "template<classValue>::protocyte::Statusset_blob(constValue&value)noexcept"
        )
        == 1
    )
    assert "autoset_blob" not in compact_header
    assert "requires(::protocyte::TextSource<Value>)" not in header
    assert "requires(::protocyte::ByteSpanSource<Value>)" in header
    assert "::protocyte::ByteViewConvertible" not in header
    assert "::protocyte::ByteView" not in header
    assert "::protocyte::MutableByteView" not in header
    assert (
        "::protocyte::Status set_blob(const ::protocyte::ByteView value) noexcept"
        not in header
    )
    assert "const auto view = ::protocyte::byte_span_of(value);" in header
    assert "const auto view = ::protocyte::cstring_byte_span_of(value);" not in header
    assert "const auto view = ::protocyte::text_byte_span_of(value);" not in header
    assert "if (!view)" in header
    assert "return view.status();" in header
    assert "if (const auto st = blob_.assign(*view); !st)" in header
    assert "if (*len != 32u)" in header
    assert "if (!values_.empty() && values_.size() != 4u) {" in header
    assert "template<class T, usize Max> struct Array" in runtime_header
    assert "template<usize Max> using ByteArray = Array<u8, Max>;" in runtime_header
    assert "template<usize Max> struct FixedByteArray" in runtime_header
    assert "iterator end() noexcept { return data() + size_; }" in runtime_header
    assert (
        "const_iterator end() const noexcept { return data() + size_; }"
        in runtime_header
    )
    assert "iterator end() noexcept { return bytes_ + size(); }" in runtime_header
    assert (
        "const_iterator end() const noexcept { return bytes_ + size(); }"
        in runtime_header
    )
    assert "u8 bytes_[Max];" in runtime_header
    assert "u8 bytes_[Max] {};" not in runtime_header


def test_generated_header_emits_portable_i64_min_constant() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("i64_min.proto")
    request.proto_file.extend([_options_file(), _i64_min_constant_file()])

    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert not response.error
    assert (
        "static constexpr ::protocyte::i64 MIN {(-9223372036854775807ll - 1ll)};"
        in files["i64_min.protocyte.hpp"]
    )
    assert "{-9223372036854775808}" not in files["i64_min.protocyte.hpp"]


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
    assert "values_{&ctx}" in header
    assert "mutable_values().copy_from(other.values())" in header
    assert "Array(Array &&other) noexcept" in runtime_header
    assert "Array &operator=(Array &&other) noexcept" in runtime_header
    assert "Status copy_from(const Array &other) noexcept" in runtime_header
    assert "template<class T> struct ValueContext" in runtime_header
    assert "using Context = typename ValueContext<T>::type;" in runtime_header
    assert (
        "explicit Array(Context *ctx = nullptr) noexcept: ctx_ {ctx} {}"
        in runtime_header
    )
    assert (
        "Context *context() const noexcept { return ctx_.context(); }" in runtime_header
    )
    assert "void bind(Context *ctx) noexcept { ctx_.bind(ctx); }" in runtime_header
    assert "ctx_.bind(other.context());" in runtime_header
    assert "new (ptr(size_)) T {context()};" in runtime_header
    assert "Array temp {context()};" in runtime_header
    assert "auto copied = protocyte::copy_value(context(), value);" in runtime_header
    assert "auto copied = protocyte::copy_value(value);" not in runtime_header
    assert (
        "template<class T> Result<T> copy_value(const T &value) noexcept"
        not in runtime_header
    )
    assert "Status copy_from(const Vector &other) noexcept" in runtime_header
    assert "for (auto &value : other)" in runtime_header
    assert runtime_header.count("for (const auto &value : other)") >= 2
    assert "for (usize i {}; i < other.size_; ++i)" not in runtime_header
    assert "Status copy_from(const HashMap &other) noexcept" in runtime_header
    assert "for (auto &bucket : buckets_)" in runtime_header
    assert "for (usize i {}; i < buckets_.size(); ++i)" not in runtime_header
    assert "template<usize Max> using ByteArray = Array<u8, Max>;" in runtime_header
    assert "ByteArray(ByteArray &&other) noexcept" not in runtime_header
    assert "ByteArray &operator=(ByteArray &&other) noexcept" not in runtime_header
    assert (
        "::std::memcpy(ptr(0u), other.ptr(0u), other.size_ * sizeof(T));"
        in runtime_header
    )
    assert "if constexpr (::std::is_trivially_destructible_v<T>)" in runtime_header
    assert "FixedByteArray(FixedByteArray &&other) noexcept" in runtime_header
    assert (
        "FixedByteArray &operator=(FixedByteArray &&other) noexcept" in runtime_header
    )


@pytest.mark.parametrize(
    ("expected", "request_factory"),
    [
        ("constant name must not be empty", lambda: _empty_constant_name_request()),
        (
            "exactly one typed constant value must be set",
            lambda: _missing_constant_value_request(),
        ),
        (
            "expression must evaluate to bool or integer",
            lambda: _boolean_expr_type_error_request(),
        ),
        (
            "value 4294967296 is out of range for uint32",
            lambda: _typed_expr_overflow_request(),
        ),
        (
            "protocyte.array.fixed requires protocyte.array.max or protocyte.array.expr",
            lambda: _fixed_without_array_request(),
        ),
        (
            "protocyte.array is not supported on map fields",
            lambda: _array_on_map_request(),
        ),
        ("protocyte.array.max must be greater than zero", lambda: _zero_max_request()),
        ("protocyte.array.expr must not be empty", lambda: _empty_expr_request()),
    ],
)
def test_rejects_remaining_model_validator_branches(
    expected: str, request_factory
) -> None:
    response = generate_response(request_factory())

    assert expected in response.error


def test_rejects_internal_typed_constant_literal_overflow_and_array_exclusivity() -> (
    None
):
    owner = SimpleNamespace(
        full_name="demo.Broken", descriptor=descriptor_pb2.DescriptorProto()
    )

    constant = _build_constants(
        owner,
        SimpleNamespace(
                message_constants=lambda options, *, label: [
                SimpleNamespace(
                    name="BROKEN",
                    kind=CONSTANT_KIND_UINT32,
                    literal=4294967296,
                    expr=None,
                )
            ]
        ),
    )[0]
    with pytest.raises(
        ProtocyteError, match="value 4294967296 is out of range for uint32"
    ):
        _coerce_literal(constant.kind, constant.literal, constant.full_name)

    array_field = descriptor_pb2.FieldDescriptorProto()
    array_field.name = "digest"
    array_field.number = 1
    array_field.label = F.LABEL_OPTIONAL
    array_field.type = F.TYPE_BYTES

    array_options = SimpleNamespace(
        field_array=lambda options, *, label: (4, "2", False)
    )
    with pytest.raises(
        ProtocyteError, match="protocyte.array requires exactly one of max or expr"
    ):
        _build_field(
            owner, SimpleNamespace(syntax="proto3"), array_field, {}, {}, array_options
        )


def test_rejects_invalid_constant_cpp_identifier() -> None:
    response = generate_response(_invalid_cpp_identifier_request())

    assert "constant name is not a valid C++ identifier" in response.error


def test_generated_header_copies_oneof_state() -> None:
    response = generate_response(_oneof_request())

    assert not response.error
    header = next(
        item.content for item in response.file if item.name == "oneof.protocyte.hpp"
    )

    assert "if (this == &other) {" in header
    assert "return {};" in header
    assert "switch (other.choice_case_) {" in header
    assert "case ChoiceCase::text: {" in header
    assert "if (const auto st = set_text(other.text()); !st) {" in header
    assert "return st;" in header
    assert "const auto ensured_inner = ensure_inner();" in header
    assert "if (!ensured_inner) { return ensured_inner.status(); }" in header
    assert (
        "if (const auto st = ensured_inner->copy_from(*other.inner()); !st) {" in header
    )
    assert "clear_choice();" in header


def test_generated_header_uses_other_for_repeated_array_only_copy() -> None:
    response = generate_response(_repeated_array_only_request())

    assert not response.error
    header = next(
        item.content
        for item in response.file
        if item.name == "repeated_array_only.protocyte.hpp"
    )

    assert "copy_from(const OnlyArrays& other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "return {};" in header
    assert "mutable_values().copy_from(other.values())" in header


def test_generated_header_uses_real_other_for_map_only_copy() -> None:
    response = generate_response(_map_only_request())

    assert not response.error
    header = next(
        item.content for item in response.file if item.name == "map_only.protocyte.hpp"
    )

    assert "copy_from(const OnlyMaps& other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "const auto& source = other;" in header
    assert "mutable_items().copy_from(source.items())" in header
    assert "if (const auto st = out->copy_from(*this); !st) {" in header


def test_rejects_invalid_hex_numeric_literals() -> None:
    response = generate_response(_invalid_hex_request())

    assert "invalid numeric literal '0x'" in response.error


@pytest.mark.parametrize(
    ("value_field", "expression", "expected"),
    [
        ("str_expr", r'"\x"', "invalid string literal"),
        ("str_expr", r'"\q"', "invalid string literal"),
        (
            "str_expr",
            r'"\ud800"',
            "string value must be valid UTF-8",
        ),
        (
            "i32_expr",
            "(" * (_MAX_EXPRESSION_NESTING + 1)
            + "1"
            + ")" * (_MAX_EXPRESSION_NESTING + 1),
            f"expression nesting exceeds maximum depth of {_MAX_EXPRESSION_NESTING}",
        ),
    ],
)
def test_expression_parser_failures_are_public_generator_errors(
    value_field: str, expression: str, expected: str
) -> None:
    response = generate_response(_expression_error_request(value_field, expression))

    assert expected in response.error
    assert "internal Protocyte error" not in response.error
    assert not response.file


@pytest.mark.parametrize(
    "package_scope", [False, True], ids=["message", "package"]
)
def test_constant_dependency_nesting_accepts_the_boundary(
    package_scope: bool,
) -> None:
    model = build_model(
        _constant_dependency_chain_request(
            _MAX_CONSTANT_DEPENDENCY_DEPTH,
            package_scope=package_scope,
        )
    )
    constants = (
        model.files["package_constant_chain.proto"].constants
        if package_scope
        else model.messages["demo.ConstantChain"].constants
    )

    assert constants[0].value == 1


@pytest.mark.parametrize(
    "package_scope", [False, True], ids=["message", "package"]
)
def test_constant_dependency_nesting_returns_a_public_error(
    package_scope: bool,
) -> None:
    expected = (
        "constant dependency nesting exceeds maximum depth of "
        f"{_MAX_CONSTANT_DEPENDENCY_DEPTH}"
    )
    with pytest.raises(ProtocyteError, match=expected):
        build_model(
            _constant_dependency_chain_request(
                _MAX_CONSTANT_DEPENDENCY_DEPTH + 1,
                package_scope=package_scope,
            )
        )

    response = generate_response(
        _constant_dependency_chain_request(
            _MAX_CONSTANT_DEPENDENCY_DEPTH + 1,
            package_scope=package_scope,
        )
    )

    assert expected in response.error
    assert "internal Protocyte error" not in response.error
    assert not response.file


@pytest.mark.parametrize(
    "package_scope", [False, True], ids=["message", "package"]
)
def test_constant_dependency_nesting_is_independent_of_declaration_order(
    package_scope: bool,
) -> None:
    expected = (
        "constant dependency nesting exceeds maximum depth of "
        f"{_MAX_CONSTANT_DEPENDENCY_DEPTH}"
    )
    with pytest.raises(ProtocyteError, match=expected):
        build_model(
            _constant_dependency_chain_request(
                _MAX_CONSTANT_DEPENDENCY_DEPTH + 1,
                package_scope=package_scope,
                leaf_first=True,
            )
        )

    response = generate_response(
        _constant_dependency_chain_request(
            _MAX_CONSTANT_DEPENDENCY_DEPTH + 1,
            package_scope=package_scope,
            leaf_first=True,
        )
    )

    assert expected in response.error
    assert "internal Protocyte error" not in response.error
    assert not response.file


@pytest.mark.parametrize(
    "package_scope", [False, True], ids=["message", "package"]
)
def test_expression_and_dependency_nesting_boundaries_compose(
    package_scope: bool,
) -> None:
    expression = (
        "(" * _MAX_EXPRESSION_NESTING
        + "1"
        + ")" * _MAX_EXPRESSION_NESTING
    )
    request = _constant_dependency_chain_request(
        _MAX_CONSTANT_DEPENDENCY_DEPTH,
        package_scope=package_scope,
        leaf_expression=expression,
    )

    build_model(request)
    response = generate_response(
        _constant_dependency_chain_request(
            _MAX_CONSTANT_DEPENDENCY_DEPTH,
            package_scope=package_scope,
            leaf_expression=expression,
        )
    )

    assert not response.error


@pytest.mark.parametrize(
    "package_scope", [False, True], ids=["message", "package"]
)
def test_composed_nesting_failure_is_a_public_generator_error(
    package_scope: bool,
) -> None:
    expression = (
        "(" * (_MAX_EXPRESSION_NESTING + 1)
        + "1"
        + ")" * (_MAX_EXPRESSION_NESTING + 1)
    )
    expected = (
        "expression nesting exceeds maximum depth of "
        f"{_MAX_EXPRESSION_NESTING}"
    )
    with pytest.raises(ProtocyteError, match=expected):
        build_model(
            _constant_dependency_chain_request(
                _MAX_CONSTANT_DEPENDENCY_DEPTH,
                package_scope=package_scope,
                leaf_expression=expression,
            )
        )

    response = generate_response(
        _constant_dependency_chain_request(
            _MAX_CONSTANT_DEPENDENCY_DEPTH,
            package_scope=package_scope,
            leaf_expression=expression,
        )
    )

    assert expected in response.error
    assert "internal Protocyte error" not in response.error
    assert not response.file


def test_package_and_message_constants_with_the_same_full_name_resolve() -> None:
    model = build_model(_constant_scope_identity_collision_request())

    assert model.files["package_identity.proto"].constants[0].value == 2
    assert model.messages["demo.Foo"].constants[0].value == 1

    response = generate_response(_constant_scope_identity_collision_request())

    assert not response.error


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
    assert sink_fields["values"].array_cpp_max == "18u"
    assert nested_fields["nested_payload"].array_max == 9
    assert nested_fields["nested_payload"].array_cpp_max == "9u"


def test_generated_header_emits_cross_message_constant_arrays() -> None:
    response = generate_response(_cross_message_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["cross.protocyte.hpp"]

    assert "static constexpr ::protocyte::u32 ROOT_CAP {6u};" in header
    assert 'static constexpr ::protocyte::StringView ROOT_LABEL {"cross", 5u};' in header
    assert "static constexpr bool ROOT_ENABLED {true};" in header
    assert "static constexpr ::protocyte::u32 MIRRORED_CAP {18u};" in header
    assert "static constexpr ::protocyte::u32 DIRECT_CAP {8u};" in header
    assert 'static constexpr ::protocyte::StringView PREFIX {"cross-sink", 10u};' in header
    assert "static constexpr bool READY {true};" in header
    assert "::protocyte::ByteArray<8u> payload_;" in header
    assert "::protocyte::Array<::protocyte::i32, 18u> values_;" in header
    assert "::protocyte::ByteArray<9u> nested_payload_;" in header


def test_resolves_package_constants_across_packages() -> None:
    model = build_model(_cross_package_package_constant_request())
    file_constants = {
        constant.name: constant
        for constant in model.files["cross_package_package.proto"].constants
    }
    message = model.messages["demo.UsesExternalPackage"]
    message_constants = {constant.name: constant for constant in message.constants}
    fields = {field.name: field for field in message.fields}

    assert file_constants["FROM_EXTERNAL"].value == 15
    assert message_constants["MIRROR"].value == 30
    assert message_constants["NAME"].value == "pkg-label-ok"
    assert fields["payload"].array_max == 8
    assert fields["values"].array_max == 15
    assert fields["values"].array_cpp_max == "15u"


def test_generated_header_emits_cross_package_package_constant_arrays() -> None:
    response = generate_response(_cross_package_package_constant_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["cross_package_package.protocyte.hpp"]

    assert "inline constexpr ::protocyte::u32 FROM_EXTERNAL {15u};" in header
    assert "static constexpr ::protocyte::u32 MIRROR {30u};" in header
    assert 'static constexpr ::protocyte::StringView NAME {"pkg-label-ok", 12u};' in header
    assert "::protocyte::ByteArray<8u> payload_;" in header
    assert "::protocyte::Array<::protocyte::i32, 15u> values_;" in header


def test_resolves_constants_across_packages_and_messages() -> None:
    model = build_model(_cross_package_message_request())
    message = model.messages["demo.UsesExternalMessage"]
    message_constants = {constant.name: constant for constant in message.constants}
    fields = {field.name: field for field in message.fields}

    assert message_constants["MIRROR"].value == 32
    assert message_constants["NAME"].value == "pkg-label-source-ok"
    assert message_constants["NESTED"].value == 18
    assert fields["payload"].array_max == 17
    assert fields["values"].array_max == 18
    assert fields["values"].array_cpp_max == "18u"


def test_generated_header_emits_cross_package_message_constant_arrays() -> None:
    response = generate_response(_cross_package_message_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["cross_package_message.protocyte.hpp"]

    assert "static constexpr ::protocyte::u32 MIRROR {32u};" in header
    assert (
        'static constexpr ::protocyte::StringView NAME {"pkg-label-source-ok", 19u};'
        in header
    )
    assert "static constexpr ::protocyte::u32 NESTED {18u};" in header
    assert "::protocyte::ByteArray<17u> payload_;" in header
    assert "::protocyte::Array<::protocyte::i32, 18u> values_;" in header


def test_canonicalizes_floatish_array_bounds() -> None:
    model = build_model(_floatish_bound_request())
    field = model.messages["demo.Sample"].fields[0]

    assert field.array_max == 2
    assert field.array_cpp_max == "2u"

    response = generate_response(_floatish_bound_request())

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "float_bound.protocyte.hpp"
    )
    assert "::protocyte::ByteArray<2u> data_;" in header
    assert "return 2u;" in header
    assert "2.0" not in header


def test_generated_header_emits_utf8_string_constants() -> None:
    response = generate_response(_unicode_constant_request())

    assert not response.error
    header = next(
        file.content for file in response.file if file.name == "unicode.protocyte.hpp"
    )
    assert "#include <string_view>" not in header
    assert "::std::string_view" not in header
    assert 'static constexpr ::protocyte::StringView NAME {"\\xc4"' in header
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
    duplicate_response = generate_response(
        _constant_collision_request(
            "duplicate.proto", [("dup", "i32", 1), ("dup", "i32", 2)]
        )
    )
    normalized_response = generate_response(
        _constant_collision_request(
            "normalized.proto", [("cap-value", "i32", 1), ("cap_value", "i32", 2)]
        )
    )
    reserved_response = generate_response(
        _constant_collision_request("reserved.proto", [("create", "i32", 1)])
    )
    validate_reserved_response = generate_response(
        _constant_collision_request("validate.proto", [("validate", "i32", 1)])
    )

    assert "constant cannot be redefined" in duplicate_response.error
    assert "collides after C++ identifier normalization" in normalized_response.error
    assert "collides with generated API" in reserved_response.error
    assert "collides with generated API" in validate_reserved_response.error


def test_generated_header_emits_tagged_union_oneofs() -> None:
    response = generate_response(_oneof_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["oneof.protocyte.hpp"]
    protected = header.split("protected:", maxsplit=1)[1]

    assert "Carrier(Carrier&& other) noexcept" in header
    assert "Carrier& operator=(Carrier&& other) noexcept" in header
    assert "~Carrier() noexcept {\n    clear_choice();\n  }" in header
    assert "template <typename T>" in header
    assert "static void destroy_at_(T* value) noexcept { value->~T(); }" in header
    assert "void clear_choice() noexcept {" in header
    assert "destroy_at_(&choice_.text_);" in header
    assert "destroy_at_(&choice_.inner_);" in header
    assert "#include <string_view>" not in header
    assert (
        "  ::protocyte::StringView text() const noexcept { "
        "return has_text() ? choice_.text_.view() : ::protocyte::StringView{}; }"
    ) in header
    assert "::std::string_view text()" not in header
    assert "::protocyte::Span<const char> text()" not in header
    assert "union ChoiceStorage {" in header
    assert "ChoiceStorage() noexcept {}" in header
    assert "~ChoiceStorage() noexcept {}" in header
    assert "} choice_;" in header
    assert "typename Config::String text_;" in header
    assert "::protocyte::i32 count_;" in header
    assert (
        "typename Config::template Optional<::demo::Carrier_Inner<Config>> inner_;"
        in header
    )
    assert (
        "new (&choice_.text_) typename Config::String {::protocyte::move(temp)};"
        in header
    )
    assert "new (&choice_.count_) ::protocyte::i32 {value};" in header
    assert (
        "new (&choice_.inner_) typename Config::template Optional<::demo::Carrier_Inner<Config>> {};"
        in header
    )
    assert (
        "return has_inner() && choice_.inner_.has_value() ? choice_.inner_.operator->() : nullptr;"
        in header
    )
    assert (
        "if (const auto st = choice_.inner_->validate(); !st) { return st; }" in header
    )
    assert "(*choice_.inner_).validate()" not in header
    assert (
        "::protocyte::Result<::demo::Carrier_Inner<Config>&> ensure_inner() noexcept"
        in header
    )
    assert "return *choice_.inner_;" in header
    assert "new (&choice_.none_)::protocyte::u8(0u);" not in header
    assert "::protocyte::u8 none_;" not in header
    assert "if (const auto st = choice_.inner_.emplace(*ctx_); !st) {" in header
    assert "return ::protocyte::unexpected(st.error());" in header
    assert "return *choice_.inner_;" in header
    assert "clear_choice();" in header
    assert "choice_case_ == ChoiceCase::text" in header
    assert "choice_case_ == ChoiceCase::inner" in header
    assert "::protocyte::i32 before_{};" in protected
    assert "::protocyte::i32 after_{};" in protected
    assert protected.index("::protocyte::i32 before_{};") < protected.index(
        "ChoiceCase choice_case_ {ChoiceCase::none};"
    )
    assert protected.index(
        "ChoiceCase choice_case_ {ChoiceCase::none};"
    ) < protected.index("union ChoiceStorage {")
    assert protected.index("} choice_;") < protected.index("::protocyte::i32 after_{};")
    assert "typename Config::String text = " not in header


def test_generated_header_suffixes_shadow_prone_oneof_storage() -> None:
    response = generate_response(_shadowing_oneof_request())

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "shadowing_oneof.protocyte.hpp"
    )

    assert "ValueCase value_case_ {ValueCase::none};" in header
    assert "} value_;" in header
    assert "bool bool_value_;" in header
    assert "new (&value_.bool_value_) bool {value};" in header
    assert "new (&value.bool_value) bool {value};" not in header
    assert (
        "constexpr bool bool_value() const noexcept { return has_bool_value() ? value_.bool_value_ : false; }"
        in header
    )
    assert "::protocyte::Status set_bool_value(const bool value) noexcept" in header
    assert (
        "constexpr ValueCase value_case() const noexcept { return value_case_; }"
        in header
    )


def test_cpp_name_registry_tracks_generated_names_by_emitted_scope() -> None:
    model = build_model(_oneof_request())
    registry = protocyte_cpp._build_message_cpp_name_registry(
        model.messages["demo.Carrier"], protocyte_cpp.GeneratorOptions()
    )

    class_scope = registry.scope("demo.Carrier")
    choice_scope = registry.scope("demo.Carrier::ChoiceStorage")
    choice_case_scope = registry.scope("demo.Carrier::ChoiceCase")
    field_number_scope = registry.scope("demo.Carrier::FieldNumber")

    assert class_scope.owner("ctx_") == "generated context storage"
    assert class_scope.owner("choice_") == "oneof choice storage"
    assert class_scope.owner("choice_case_") == "oneof choice case storage"
    assert class_scope.owner("ChoiceStorage") == "oneof choice storage type"
    assert class_scope.owner("text_") is None
    assert choice_scope.owner("text_") == "oneof field text storage"
    assert choice_case_scope.owner("none") == "oneof choice empty case"
    assert choice_case_scope.owner("text") == "oneof field text case"
    assert field_number_scope.owner("text") == "field text number"


def test_cpp_function_registry_rejects_parameters_that_shadow_visible_storage() -> None:
    function_scope = protocyte_cpp._CppFunctionScope(
        "demo.Message::set_flag", visible_storage={"value"}
    )

    with pytest.raises(
        ProtocyteError, match="parameter 'value' shadows visible generated storage"
    ):
        function_scope.parameter("value")


def test_generated_header_uses_normalized_oneof_case_type() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("keyword_oneof.proto")
    request.proto_file.append(_keyword_oneof_file())

    response = generate_response(request)

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "keyword_oneof.protocyte.hpp"
    )
    assert "enum struct And_Case" in header
    assert "constexpr And_Case and__case() const noexcept" in header
    assert "and__case_ == And_Case::value" in header
    assert "AndCase" not in header


def test_rejects_oneof_cpp_name_collisions() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof_collision.proto")
    request.proto_file.append(_oneof_collision_file())

    response = generate_response(request)

    assert "oneof collides with" in response.error
    assert "after C++ identifier normalization" in response.error


@pytest.mark.parametrize("oneof_name", ["ctx", "context", "destroy_at"])
def test_rejects_oneof_fixed_generated_name_collisions(oneof_name: str) -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof_internal_collision.proto")
    request.proto_file.append(_oneof_internal_collision_file(oneof_name))

    response = generate_response(request)

    assert "oneof collides with generated API" in response.error


@pytest.mark.parametrize("field_name", ["choice_case_", "none"])
def test_rejects_oneof_generated_member_collisions(field_name: str) -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof_member_collision.proto")
    request.proto_file.append(_oneof_member_collision_file(field_name))

    response = generate_response(request)

    assert "field collides with generated API" in response.error


@pytest.mark.parametrize(
    ("oneof_name", "field_name"),
    [
        ("class", "class_"),
        ("choice", "choice"),
    ],
)
def test_rejects_field_backing_member_collisions_with_oneof_storage(
    oneof_name: str, field_name: str
) -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("field_backing_collision.proto")
    request.proto_file.append(_field_backing_collision_file(oneof_name, field_name))

    response = generate_response(request)

    assert "field collides with generated API" in response.error


def test_rejects_presence_flag_collisions_with_oneof_storage() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("presence_flag_collision.proto")
    request.proto_file.append(_presence_flag_collision_file())

    response = generate_response(request)

    assert "field collides with generated API" in response.error


def test_generated_header_parses_bounded_oneof_bytes() -> None:
    response = generate_response(_oneof_array_request())

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "oneof_array.protocyte.hpp"
    )
    compact_header = "".join(header.split())
    assert (
        "template<classValue>::protocyte::Statusset_data(constValue&value)noexcept"
        in compact_header
    )
    assert "autoset_data" not in compact_header
    assert "requires(::protocyte::ByteSpanSource<Value>)" in header
    assert "const auto view = ::protocyte::byte_span_of(value);" in header
    assert "if (const auto st = temp.assign(*view); !st)" in header
    assert (
        "::protocyte::Status set_data(const ::protocyte::ByteView value) noexcept"
        not in header
    )
    assert "if (const auto st = reader.can_read(*len); !st) { return st; }" in header
    assert "::protocyte::ByteArray<8u> data_value{};" in header
    assert "if (const auto st = data_value.resize_for_overwrite(*len); !st)" in header
    assert "const auto view = data_value.mutable_view();" in header
    assert "if (const auto st = reader.read(view.data(), view.size()); !st)" in header
    assert (
        "new (&choice_.data_) ::protocyte::ByteArray<8u> {::protocyte::move(data_value)};"
        in header
    )
    assert "choice_case_ = ChoiceCase::data;" in header
    after_read = header.split(
        "if (const auto st = reader.read(view.data(), view.size()); !st) {", maxsplit=1
    )[1]
    before_commit = after_read.split("clear_choice();", maxsplit=1)[0]
    assert "return st;" in before_commit
    assert (
        "static_cast<void>(choice_.data_.resize_for_overwrite(old_data_size));"
        not in header
    )
    assert "if (*len > ctx_->limits.max_string_bytes) {" in header
    assert "new (&choice_.data_)::protocyte::ByteArray<8u> {ctx_};" not in header


def test_recursive_oneof_box_sets_case_after_successful_ensure() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("recursive_oneof.proto")
    request.proto_file.append(_recursive_oneof_file())

    response = generate_response(request)

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "recursive_oneof.protocyte.hpp"
    )
    ensure_body = header.split(
        "Result<::demo::Node<Config>&> ensure_child()", maxsplit=1
    )[1]
    ensure_body = ensure_body.split("template <typename Reader>", maxsplit=1)[0]

    assert "auto ensured = choice_.child_.ensure();" in ensure_body
    assert (
        "if (!ensured) {\n      destroy_at_(&choice_.child_);\n      return ensured;\n    }"
        in ensure_body
    )
    assert ensure_body.index(
        "auto ensured = choice_.child_.ensure();"
    ) < ensure_body.index("choice_case_ = ChoiceCase::child;")


def test_empty_message_comments_unused_writer_and_returns_zero_size() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("empty.proto")
    request.proto_file.append(_empty_file())

    response = generate_response(request)

    assert not response.error
    header = next(
        file.content for file in response.file if file.name == "empty.protocyte.hpp"
    )

    assert (
        "::protocyte::Status serialize(Writer& /* writer */) const noexcept {" in header
    )
    assert (
        "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {"
        in header
    )
    assert "::protocyte::usize total {};" not in header
    assert "return ::protocyte::usize {};" in header


def test_generated_encoded_size_omits_redundant_uint64_varint_casts() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("uint64_casts.proto")
    request.proto_file.append(_uint64_casts_file())

    response = generate_response(request)

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "uint64_casts.protocyte.hpp"
    )
    encoded_size_body = header.split(
        "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {",
        maxsplit=1,
    )[1].split("\n};", maxsplit=1)[0]

    assert "::protocyte::varint_size(version_)" in encoded_size_body
    assert "::protocyte::varint_size(values_value)" in encoded_size_body
    assert "::protocyte::varint_size(loose_values_value)" in encoded_size_body
    assert "::protocyte::varint_size(choice_.choice_value_)" in encoded_size_body
    assert "::protocyte::varint_size(entry.key)" in encoded_size_body
    assert "::protocyte::varint_size(entry.value)" in encoded_size_body
    assert (
        "::protocyte::varint_size(static_cast<::protocyte::u64>(version_))"
        not in encoded_size_body
    )
    assert (
        "::protocyte::varint_size(static_cast<::protocyte::u64>(values_value))"
        not in encoded_size_body
    )
    assert (
        "::protocyte::varint_size(static_cast<::protocyte::u64>(loose_values_value))"
        not in encoded_size_body
    )
    assert (
        "::protocyte::varint_size(static_cast<::protocyte::u64>(choice_.choice_value_))"
        not in encoded_size_body
    )
    assert (
        "::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key))"
        not in encoded_size_body
    )
    assert (
        "::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value))"
        not in encoded_size_body
    )


def test_generated_header_keeps_runtime_status_globally_qualified() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("namespaced.proto")
    request.proto_file.append(_protocyte_package_file())

    response = generate_response(request)

    assert not response.error
    header = next(
        file.content
        for file in response.file
        if file.name == "namespaced.protocyte.hpp"
    )

    assert "namespace test::protocyte {" in header
    assert "::protocyte::Status merge_from(Reader& reader) noexcept {" in header
    assert "::protocyte::Status serialize(Writer& writer) const noexcept {" in header


def test_packaged_options_proto_is_the_only_repo_copy() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    root_copy = repo_root / "protocyte" / "options.proto"
    source_copy = (
        repo_root / "src" / "protocyte" / "proto" / "protocyte" / "options.proto"
    )

    assert not root_copy.exists()
    assert source_copy.is_file()


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
    field.name = "signed_samples"
    field.number = 7
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_SFIXED32
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


def _uint64_casts_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "uint64_casts.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Uint64CastCases"

    field = message.field.add()
    field.name = "version"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_UINT64

    field = message.field.add()
    field.name = "values"
    field.number = 2
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_UINT64
    field.options.packed = True

    field = message.field.add()
    field.name = "loose_values"
    field.number = 5
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_UINT64
    field.options.packed = False

    message.oneof_decl.add().name = "choice"
    field = message.field.add()
    field.name = "choice_value"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_UINT64
    field.oneof_index = 0

    entry = message.nested_type.add()
    entry.name = "CountersEntry"
    entry.options.map_entry = True
    key = entry.field.add()
    key.name = "key"
    key.number = 1
    key.label = F.LABEL_OPTIONAL
    key.type = F.TYPE_UINT64
    value = entry.field.add()
    value.name = "value"
    value.number = 2
    value.label = F.LABEL_OPTIONAL
    value.type = F.TYPE_UINT64

    field = message.field.add()
    field.name = "counters"
    field.number = 4
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Uint64CastCases.CountersEntry"

    return file


def _constant_array_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("arrays.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend([_options_file(), _constant_array_file()])
    return request


def _expression_error_request(
    value_field: str, expression: str
) -> plugin_pb2.CodeGeneratorRequest:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "expression_error.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    message = file.message_type.add()
    message.name = "ExpressionError"
    message.options.ParseFromString(
        _constant_options_bytes([("BROKEN", value_field, expression)])
    )

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(file.name)
    request.proto_file.extend([_options_file(), file])
    return request


def _constant_dependency_chain_request(
    count: int,
    *,
    package_scope: bool,
    leaf_expression: str = "1",
    leaf_first: bool = False,
) -> plugin_pb2.CodeGeneratorRequest:
    assert count > 0
    file = descriptor_pb2.FileDescriptorProto()
    file.name = (
        "package_constant_chain.proto"
        if package_scope
        else "message_constant_chain.proto"
    )
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    constants = [
        (
            f"C{index}",
            "i32_expr",
            f"C{index + 1}" if index + 1 < count else leaf_expression,
        )
        for index in range(count)
    ]
    if leaf_first:
        constants.reverse()
    if package_scope:
        file.options.ParseFromString(_package_constant_options_bytes(constants))
    else:
        message = file.message_type.add()
        message.name = "ConstantChain"
        message.options.ParseFromString(_constant_options_bytes(constants))

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(file.name)
    request.proto_file.extend([_options_file(), file])
    return request


def _constant_scope_identity_collision_request() -> plugin_pb2.CodeGeneratorRequest:
    package_file = descriptor_pb2.FileDescriptorProto()
    package_file.name = "package_identity.proto"
    package_file.package = "demo.Foo"
    package_file.syntax = "proto3"
    package_file.dependency.append("protocyte/options.proto")
    package_file.options.ParseFromString(
        _package_constant_options_bytes([("C", "i32_expr", "2")])
    )

    message_file = descriptor_pb2.FileDescriptorProto()
    message_file.name = "message_identity.proto"
    message_file.package = "demo"
    message_file.syntax = "proto3"
    message_file.dependency.append("protocyte/options.proto")
    message = message_file.message_type.add()
    message.name = "Foo"
    message.options.ParseFromString(
        _constant_options_bytes([("C", "i32_expr", "1")])
    )

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(message_file.name)
    request.proto_file.extend([_options_file(), package_file, message_file])
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


def _cross_package_package_constant_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("cross_package_package.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend(
        [
            _options_file(),
            _external_constant_provider_file(),
            _cross_package_package_constant_file(),
        ]
    )
    return request


def _cross_package_message_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("cross_package_message.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend(
        [
            _options_file(),
            _external_constant_provider_file(),
            _cross_package_message_file(),
        ]
    )
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


def _shadowing_oneof_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("shadowing_oneof.proto")
    request.proto_file.append(_shadowing_oneof_file())
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


def _missing_constant_value_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("missing_constant_value.proto")
    request.proto_file.extend([_options_file(), _missing_constant_value_file()])
    return request


def _empty_constant_name_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("empty_constant_name.proto")
    request.proto_file.extend([_options_file(), _empty_constant_name_file()])
    return request


def _boolean_expr_type_error_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("boolean_expr_type_error.proto")
    request.proto_file.extend([_options_file(), _boolean_expr_type_error_file()])
    return request


def _typed_expr_overflow_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("typed_expr_overflow.proto")
    request.proto_file.extend([_options_file(), _typed_expr_overflow_file()])
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
    constants: list[tuple[str, str, object]],
) -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(file_name)
    request.proto_file.extend(
        [_options_file(), _constant_collision_file(file_name, constants)]
    )
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

    constant = file.message_type.add()
    constant.name = "Constant"
    field = constant.field.add()
    field.name = "name"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    for number, (field_name, field_type) in enumerate(
        [
            ("boolean", F.TYPE_BOOL),
            ("boolean_expr", F.TYPE_STRING),
            ("i32", F.TYPE_INT32),
            ("i32_expr", F.TYPE_STRING),
            ("u32", F.TYPE_UINT32),
            ("u32_expr", F.TYPE_STRING),
            ("i64", F.TYPE_INT64),
            ("i64_expr", F.TYPE_STRING),
            ("u64", F.TYPE_UINT64),
            ("u64_expr", F.TYPE_STRING),
            ("f32", F.TYPE_FLOAT),
            ("f32_expr", F.TYPE_STRING),
            ("f64", F.TYPE_DOUBLE),
            ("f64_expr", F.TYPE_STRING),
            ("str", F.TYPE_STRING),
            ("str_expr", F.TYPE_STRING),
        ],
        start=2,
    ):
        _add_oneof_field(constant, "value", field_name, number, field_type)

    array_options = file.message_type.add()
    array_options.name = "ArrayOptions"
    _add_oneof_field(array_options, "bound", "max", 1, F.TYPE_UINT32)
    _add_oneof_field(array_options, "bound", "expr", 2, F.TYPE_STRING)
    field = array_options.field.add()
    field.name = "fixed"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BOOL

    ext = file.extension.add()
    ext.name = "constant"
    ext.number = 50000
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.Constant"
    ext.extendee = ".google.protobuf.MessageOptions"

    ext = file.extension.add()
    ext.name = "package_constant"
    ext.number = 50002
    ext.label = F.LABEL_REPEATED
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.Constant"
    ext.extendee = ".google.protobuf.FileOptions"

    ext = file.extension.add()
    ext.name = "array"
    ext.number = 50000
    ext.label = F.LABEL_OPTIONAL
    ext.type = F.TYPE_MESSAGE
    ext.type_name = ".protocyte.ArrayOptions"
    ext.extendee = ".google.protobuf.FieldOptions"

    return file


def _obsolete_fixed_size_request() -> plugin_pb2.CodeGeneratorRequest:
    options_file = descriptor_pb2.FileDescriptorProto()
    options_file.name = "protocyte/options.proto"
    options_file.package = "protocyte"
    options_file.syntax = "proto3"
    options_file.dependency.append("google/protobuf/descriptor.proto")

    extension = options_file.extension.add()
    extension.name = "fixed_size"
    extension.number = 50000
    extension.label = F.LABEL_OPTIONAL
    extension.type = F.TYPE_UINT32
    extension.extendee = ".google.protobuf.FieldOptions"

    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(options_file)
    field_options_cls = message_factory.GetMessageClass(
        pool.FindMessageTypeByName("google.protobuf.FieldOptions")
    )
    field_options = field_options_cls()
    field_options.Extensions[pool.FindExtensionByName("protocyte.fixed_size")] = 32

    source_file = descriptor_pb2.FileDescriptorProto()
    source_file.name = "obsolete_options.proto"
    source_file.package = "demo"
    source_file.syntax = "proto3"
    source_file.dependency.append("protocyte/options.proto")
    message = source_file.message_type.add()
    message.name = "Sample"
    field = message.field.add()
    field.name = "blob"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(field_options.SerializeToString())

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append(source_file.name)
    request.proto_file.extend([options_file, source_file])
    return request


def _bitwise_expression_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("bitwise_expressions.proto")
    request.proto_file.extend([_options_file(), _bitwise_expression_file()])
    return request


def _bitwise_expression_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "bitwise_expressions.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    file.options.ParseFromString(
        _package_constant_options_bytes([("BASE_BITS", "u32_expr", "(true << 3) | 2")])
    )

    message = file.message_type.add()
    message.name = "BitwiseExpressions"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("I32_MASK", "i32_expr", "~0"),
                ("U32_MASK", "u32_expr", "~0"),
                ("I64_SHIFT", "i64_expr", "1 << 40"),
                ("U64_MASK", "u64_expr", "(~0) ^ 0xf"),
                ("F32_BITS", "f32_expr", "(1 << 3) | 1"),
                ("F64_BITS", "f64_expr", "true << 4"),
                ("BOOL_BITS", "boolean_expr", "BASE_BITS & 0x8"),
                ("BOOL_LOGIC", "boolean_expr", "(BASE_BITS & 0x8) && true"),
                ("BOOL_ARITH", "boolean_expr", "1 + 1"),
                ("STR_BITS", "str_expr", 'substr("abcd", 1 << 0, 1 | 0)'),
            ]
        )
    )

    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="(BASE_BITS & 0xf) - 1"))
    return file


def _math_expression_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("math_expressions.proto")
    request.proto_file.extend([_options_file(), _math_expression_file()])
    return request


def _math_expression_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "math_expressions.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    file.options.ParseFromString(
        _package_constant_options_bytes(
            [("PACKAGE_ROOT", "u32_expr", "max(2, sqrt(9))")]
        )
    )

    message = file.message_type.add()
    message.name = "MathExpressions"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("F32_INPUT", "f32", 2.0),
                ("I32_POWER", "i32_expr", "pow(2, 5)"),
                ("I32_TRUNC", "i32_expr", "-2.9"),
                ("U32_MAX", "u32_expr", "max(PACKAGE_ROOT, 5)"),
                ("U32_TRUNC", "u32_expr", "2.9"),
                ("U32_NEGATIVE_POWER", "u32_expr", "pow(2, f64(-3)) * 8"),
                ("I64_POWER", "i64_expr", "pow(2, 40)"),
                ("U64_POWER", "u64_expr", "pow(2, 63)"),
                ("F32_ROOT", "f32_expr", "sqrt(F32_INPUT)"),
                ("F64_NESTED", "f64_expr", "log(exp(2.0))"),
                ("BOOL_MATH", "boolean_expr", "min(1, 2)"),
                ("I32_NEGATIVE_ONE", "i32_expr", "-1"),
                ("U32_ALL_ONES", "u32_expr", "~0"),
                (
                    "BOOL_MIXED_EQUAL",
                    "boolean_expr",
                    "I32_NEGATIVE_ONE == U32_ALL_ONES",
                ),
                ("F32_ROUNDED", "f32", 16777216.0),
                (
                    "BOOL_F32_EQUAL",
                    "boolean_expr",
                    "F32_ROUNDED == 16777217",
                ),
                (
                    "STR_MATH",
                    "str_expr",
                    'substr("abcd", floor(1.9), max(1, 1))',
                ),
            ]
        )
    )

    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(
        _array_option_bytes(expr="pow(2, f64(-1)) * 8 + PACKAGE_ROOT")
    )
    return file


def _constant_array_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "arrays.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    file.options.ParseFromString(
        _package_constant_options_bytes(
            [
                ("FILE_CAP", "u32", 16),
                ("FILE_LABEL", "str_expr", 'substr("hello", 1, 3)'),
                ("FILE_READY", "boolean_expr", 'starts_with(FILE_LABEL, "e")'),
            ]
        )
    )

    message = file.message_type.add()
    message.name = "Holder"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("MAGIC_NUMBER", "i32_expr", "FILE_CAP"),
                ("DOUBLE_MAGIC", "i32_expr", "MAGIC_NUMBER * 2"),
                ("HEX_MAGIC", "u32", 0x20),
                ("HEX_EXPR", "i32_expr", "0x10 + 0x8"),
                ("LABEL", "str_expr", "demo.FILE_LABEL"),
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
    field.options.ParseFromString(_array_option_bytes(expr="FILE_CAP"))

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
                ("HAS_PREFIX", "boolean_expr", 'starts_with(FILE_LABEL, "e")'),
            ]
        )
    )
    field = nested.field.add()
    field.name = "payload"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="demo.FILE_CAP"))

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


def _missing_constant_value_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "missing_constant_value.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_options_file())
    message_options_desc = pool.FindMessageTypeByName("google.protobuf.MessageOptions")
    message_options_cls = message_factory.GetMessageClass(message_options_desc)
    constant_ext = pool.FindExtensionByName("protocyte.constant")

    message = file.message_type.add()
    message.name = "Broken"
    options = message_options_cls()
    item = options.Extensions[constant_ext].add()
    item.name = "BROKEN"
    message.options.ParseFromString(options.SerializeToString())
    return file


def _empty_constant_name_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "empty_constant_name.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes([("", "i32", 1)]))
    return file


def _boolean_expr_type_error_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "boolean_expr_type_error.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(
        _constant_options_bytes([("BROKEN", "boolean_expr", "1.0")])
    )
    return file


def _typed_expr_overflow_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "typed_expr_overflow.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(
        _constant_options_bytes([("BROKEN", "u32_expr", "4294967296")])
    )
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


def _len_bound_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "len_bound.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "LenBound"
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr='len("abcd")'))
    return file


def _array_bound_expr_file(name: str, expr: str) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = name
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "ArrayBound"
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr=expr))
    return file


def _same_package_constant_provider_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "same_package_provider.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    file.options.ParseFromString(_package_constant_options_bytes([("CAP", "u32", 5)]))
    return file


def _same_package_constant_user_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "same_package_user.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.extend(["protocyte/options.proto", "same_package_provider.proto"])

    message = file.message_type.add()
    message.name = "UsesSamePackageConstant"
    field = message.field.add()
    field.name = "data"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="CAP + 1"))
    return file


def _i64_min_constant_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "i64_min.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Limits"
    message.options.ParseFromString(_constant_options_bytes([("MIN", "i64", -(2**63))]))
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
    constants: list[tuple[str, str, object]],
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
    message.options.ParseFromString(_constant_options_bytes([("1", "i32", 1)]))
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
                ("A", "i32_expr", "B + 1"),
                ("B", "i32_expr", "A + 1"),
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
                ("BROKEN", "i32_expr", "0x + 1"),
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
    message.options.ParseFromString(
        _constant_options_bytes([("NAME", "str", chr(0x0100) + chr(0x00E9))])
    )
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


def _keyword_oneof_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "keyword_oneof.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "KeywordOneof"
    message.oneof_decl.add().name = "and"

    field = message.field.add()
    field.name = "value"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    field.oneof_index = 0

    return file


def _shadowing_oneof_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "shadowing_oneof.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "AnyValue"
    message.oneof_decl.add().name = "value"

    field = message.field.add()
    field.name = "bool_value"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BOOL
    field.oneof_index = 0

    return file


def _oneof_collision_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "oneof_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Broken"
    for name in ("and", "and_"):
        message.oneof_decl.add().name = name

    for index, name in enumerate(("first", "second")):
        field = message.field.add()
        field.name = name
        field.number = index + 1
        field.label = F.LABEL_OPTIONAL
        field.type = F.TYPE_INT32
        field.oneof_index = index

    return file


def _oneof_internal_collision_file(
    oneof_name: str,
) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "oneof_internal_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Broken"
    message.oneof_decl.add().name = oneof_name

    field = message.field.add()
    field.name = "flag"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BOOL
    field.oneof_index = 0

    return file


def _oneof_member_collision_file(field_name: str) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "oneof_member_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Broken"
    message.oneof_decl.add().name = "choice"

    field = message.field.add()
    field.name = field_name
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    field.oneof_index = 0

    return file


def _field_backing_collision_file(
    oneof_name: str, field_name: str
) -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "field_backing_collision.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Broken"
    message.oneof_decl.add().name = oneof_name

    field = message.field.add()
    field.name = field_name
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    oneof_field = message.field.add()
    oneof_field.name = "flag"
    oneof_field.number = 2
    oneof_field.label = F.LABEL_OPTIONAL
    oneof_field.type = F.TYPE_BOOL
    oneof_field.oneof_index = 0

    return file


def _presence_flag_collision_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "presence_flag_collision.proto"
    file.package = "demo"
    file.syntax = "proto2"

    message = file.message_type.add()
    message.name = "Broken"
    message.oneof_decl.add().name = "has_flag"

    field = message.field.add()
    field.name = "flag"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    oneof_field = message.field.add()
    oneof_field.name = "choice"
    oneof_field.number = 2
    oneof_field.label = F.LABEL_OPTIONAL
    oneof_field.type = F.TYPE_BOOL
    oneof_field.oneof_index = 0

    return file


def _recursive_oneof_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "recursive_oneof.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Node"
    message.oneof_decl.add().name = "choice"

    field = message.field.add()
    field.name = "child"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".demo.Node"
    field.oneof_index = 0

    return file


def _empty_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "empty.proto"
    file.package = "demo"
    file.syntax = "proto3"

    message = file.message_type.add()
    message.name = "Empty"

    return file


def _proto2_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("legacy.proto")
    request.proto_file.append(_proto2_file())
    return request


def _proto2_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "legacy.proto"
    file.package = "legacy"
    file.syntax = "proto2"

    message = file.message_type.add()
    message.name = "Legacy"

    field = message.field.add()
    field.name = "count"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    field.default_value = "7"

    field = message.field.add()
    field.name = "label"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field.default_value = "legacy"

    field = message.field.add()
    field.name = "name"
    field.number = 3
    field.label = F.LABEL_REQUIRED
    field.type = F.TYPE_STRING

    field = message.field.add()
    field.name = "samples"
    field.number = 4
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32

    field = message.field.add()
    field.name = "blob"
    field.number = 5
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.default_value = r"\001\377"

    field = message.field.add()
    field.name = "ratio"
    field.number = 6
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_FLOAT
    field.default_value = "inf"

    field = message.field.add()
    field.name = "precise"
    field.number = 7
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_DOUBLE
    field.default_value = "nan"

    field = message.field.add()
    field.name = "max_counter"
    field.number = 8
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_UINT64
    field.default_value = "18446744073709551615"

    field = message.field.add()
    field.name = "min_counter"
    field.number = 9
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT64
    field.default_value = "-9223372036854775808"

    return file


def _proto2_default_semantics_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("defaults.proto")
    request.proto_file.append(_proto2_default_semantics_file())
    return request


def _proto2_default_semantics_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "defaults.proto"
    file.package = "defaults"
    file.syntax = "proto2"

    enum = file.enum_type.add()
    enum.name = "DefaultChoice"
    value = enum.value.add()
    value.name = "DEFAULT_CHOICE_UNKNOWN"
    value.number = 5
    value = enum.value.add()
    value.name = "DEFAULT_CHOICE_READY"
    value.number = 9

    nested = file.message_type.add()
    nested.name = "Nested"
    field = nested.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    message = file.message_type.add()
    message.name = "Defaults"

    field = message.field.add()
    field.name = "implicit_int32"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32

    field = message.field.add()
    field.name = "implicit_bool"
    field.number = 2
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BOOL

    field = message.field.add()
    field.name = "implicit_string"
    field.number = 3
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING

    field = message.field.add()
    field.name = "implicit_bytes"
    field.number = 4
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES

    field = message.field.add()
    field.name = "implicit_message"
    field.number = 5
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".defaults.Nested"

    field = message.field.add()
    field.name = "implicit_numbers"
    field.number = 6
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32

    field = message.field.add()
    field.name = "implicit_choice"
    field.number = 7
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_ENUM
    field.type_name = ".defaults.DefaultChoice"

    field = message.field.add()
    field.name = "explicit_choice"
    field.number = 8
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_ENUM
    field.type_name = ".defaults.DefaultChoice"
    field.default_value = "DEFAULT_CHOICE_READY"

    oneof = message.oneof_decl.add()
    oneof.name = "choice"

    field = message.field.add()
    field.name = "oneof_int32"
    field.number = 9
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    field.oneof_index = 0
    field.default_value = "11"

    field = message.field.add()
    field.name = "oneof_string"
    field.number = 10
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_STRING
    field.oneof_index = 0
    field.default_value = "chosen"

    field = message.field.add()
    field.name = "oneof_bytes"
    field.number = 11
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.oneof_index = 0
    field.default_value = r"\002\376"

    field = message.field.add()
    field.name = "implicit_oneof_choice"
    field.number = 12
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_ENUM
    field.type_name = ".defaults.DefaultChoice"
    field.oneof_index = 0

    field = message.field.add()
    field.name = "explicit_oneof_choice"
    field.number = 13
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_ENUM
    field.type_name = ".defaults.DefaultChoice"
    field.oneof_index = 0
    field.default_value = "DEFAULT_CHOICE_READY"

    field = message.field.add()
    field.name = "implicit_choices"
    field.number = 14
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_ENUM
    field.type_name = ".defaults.DefaultChoice"

    field = message.field.add()
    field.name = "required_int32"
    field.number = 15
    field.label = F.LABEL_REQUIRED
    field.type = F.TYPE_INT32
    field.default_value = "17"

    return file


def _proto2_dependency_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "legacy_dep.proto"
    file.package = "legacy"
    file.syntax = "proto2"

    message = file.message_type.add()
    message.name = "LegacyDep"
    field = message.field.add()
    field.name = "id"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_INT32
    return file


def _proto3_uses_proto2_dependency_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "uses_legacy.proto"
    file.package = "modern"
    file.syntax = "proto3"
    file.dependency.append("legacy_dep.proto")

    message = file.message_type.add()
    message.name = "UsesLegacy"
    field = message.field.add()
    field.name = "legacy"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_MESSAGE
    field.type_name = ".legacy.LegacyDep"
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
                ("ROOT_CAP", "u32", 6),
                ("ROOT_LABEL", "str_expr", 'substr("crossing", 0, 5)'),
                ("ROOT_ENABLED", "boolean_expr", 'starts_with(ROOT_LABEL, "cr")'),
            ]
        )
    )

    sink = file.message_type.add()
    sink.name = "Sink"
    sink.options.ParseFromString(
        _constant_options_bytes(
            [
                ("MIRRORED_CAP", "u32_expr", "Source.ROOT_CAP * 3"),
                ("DIRECT_CAP", "u32_expr", "Source.ROOT_CAP + 2"),
                ("PREFIX", "str_expr", 'Source.ROOT_LABEL + "-sink"'),
                (
                    "READY",
                    "boolean_expr",
                    "Source.ROOT_ENABLED && (MIRRORED_CAP == 18)",
                ),
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
                ("NESTED_CAP", "u32_expr", "Source.ROOT_CAP + 3"),
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


def _external_constant_provider_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "external.proto"
    file.package = "alpha.beta"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")
    file.options.ParseFromString(
        _package_constant_options_bytes(
            [
                ("CAP", "u32", 7),
                ("DOUBLE_CAP", "u32_expr", "CAP * 2"),
                ("LABEL", "str_expr", '"pkg" + "-label"'),
            ]
        )
    )

    source = file.message_type.add()
    source.name = "Source"
    source.options.ParseFromString(
        _constant_options_bytes(
            [
                ("ROOT_CAP", "u32_expr", "DOUBLE_CAP + 2"),
                ("ROOT_LABEL", "str_expr", 'LABEL + "-source"'),
            ]
        )
    )

    nested = source.nested_type.add()
    nested.name = "Inner"
    nested.options.ParseFromString(
        _constant_options_bytes(
            [
                ("NESTED_CAP", "u32_expr", "ROOT_CAP + 1"),
            ]
        )
    )

    return file


def _cross_package_package_constant_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "cross_package_package.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.extend(["protocyte/options.proto", "external.proto"])
    file.options.ParseFromString(
        _package_constant_options_bytes(
            [
                ("FROM_EXTERNAL", "u32_expr", "alpha.beta.DOUBLE_CAP + 1"),
            ]
        )
    )

    message = file.message_type.add()
    message.name = "UsesExternalPackage"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("MIRROR", "u32_expr", "FROM_EXTERNAL * 2"),
                ("NAME", "str_expr", 'alpha.beta.LABEL + "-ok"'),
            ]
        )
    )

    field = message.field.add()
    field.name = "payload"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(_array_option_bytes(expr="alpha.beta.CAP + 1"))

    field = message.field.add()
    field.name = "values"
    field.number = 2
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32
    field.options.ParseFromString(_array_option_bytes(expr="FROM_EXTERNAL"))

    return file


def _cross_package_message_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "cross_package_message.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.extend(["protocyte/options.proto", "external.proto"])

    message = file.message_type.add()
    message.name = "UsesExternalMessage"
    message.options.ParseFromString(
        _constant_options_bytes(
            [
                ("MIRROR", "u32_expr", "alpha.beta.Source.ROOT_CAP * 2"),
                ("NAME", "str_expr", 'alpha.beta.Source.ROOT_LABEL + "-ok"'),
                ("NESTED", "u32_expr", "alpha.beta.Source.Inner.NESTED_CAP + 1"),
            ]
        )
    )

    field = message.field.add()
    field.name = "payload"
    field.number = 1
    field.label = F.LABEL_OPTIONAL
    field.type = F.TYPE_BYTES
    field.options.ParseFromString(
        _array_option_bytes(expr="alpha.beta.Source.ROOT_CAP + 1")
    )

    field = message.field.add()
    field.name = "values"
    field.number = 2
    field.label = F.LABEL_REPEATED
    field.type = F.TYPE_INT32
    field.options.ParseFromString(_array_option_bytes(expr="NESTED"))

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


def _constant_options_bytes(constants: list[tuple[str, str, object]]) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_options_file())
    message_options_desc = pool.FindMessageTypeByName("google.protobuf.MessageOptions")
    message_options_cls = message_factory.GetMessageClass(message_options_desc)
    constant_ext = pool.FindExtensionByName("protocyte.constant")

    options = message_options_cls()
    for name, value_field, value in constants:
        item = options.Extensions[constant_ext].add()
        item.name = name
        setattr(item, value_field, value)
    return options.SerializeToString()


def _package_constant_options_bytes(constants: list[tuple[str, str, object]]) -> bytes:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(_options_file())
    file_options_desc = pool.FindMessageTypeByName("google.protobuf.FileOptions")
    file_options_cls = message_factory.GetMessageClass(file_options_desc)
    constant_ext = pool.FindExtensionByName("protocyte.package_constant")

    options = file_options_cls()
    for name, value_field, value in constants:
        item = options.Extensions[constant_ext].add()
        item.name = name
        setattr(item, value_field, value)
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

    options = field_options_cls()
    array_options = options.Extensions[array_ext]
    if max_value is not None:
        array_options.max = max_value
    if expr is not None:
        array_options.expr = expr
    if fixed:
        array_options.fixed = True
    return options.SerializeToString()
