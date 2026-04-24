from pathlib import Path
from types import SimpleNamespace

import pytest
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

import protocyte.cpp as protocyte_cpp
from protocyte.cpp import CppWriter
from protocyte.model import (
    CONSTANT_KIND_UINT32,
    ProtocyteError,
    _ExprParser,
    _build_constants,
    _build_field,
    _coerce_literal,
    build_model,
)
from protocyte.plugin import generate_response
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


def test_runtime_rejects_unmatched_end_group_in_skip_field() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    assert (
        "case WireType::EGROUP:\n"
        "                return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field_number);"
    ) in runtime_header
    assert "case WireType::EGROUP: return {};" not in runtime_header


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
    assert "next_size >= rehash_threshold_for(buckets_.size())" in runtime_header
    assert "static constexpr usize rehash_threshold_for(const usize bucket_count) noexcept" in runtime_header
    assert "capacity_ * 2u" not in runtime_header
    assert "checked_mul(count, 2u, &target)" not in runtime_header
    assert "checked_add(size_, 1u, &requested)" not in runtime_header
    assert "(size_ + 1u) * 10u" not in runtime_header
    assert "buckets_.size() * 7u" not in runtime_header


def test_runtime_sequence_containers_accept_contiguous_ranges() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]
    vector_body = runtime_header.split("template<class T, class Config> struct Vector {", maxsplit=1)[1].split(
        "template<class T, usize Max> struct Array {", maxsplit=1
    )[0]
    array_body = runtime_header.split("template<class T, usize Max> struct Array {", maxsplit=1)[1].split(
        "template<usize Max> struct ByteArray {", maxsplit=1
    )[0]

    assert "concept ContiguousRange" in runtime_header
    assert "concept DataSizeContiguousRange" in runtime_header
    assert "concept PointerContiguousRange" in runtime_header
    assert "constexpr auto contiguous_range_data(const T &value) noexcept" in runtime_header
    assert "Result<usize> contiguous_range_size(const T &value) noexcept" in runtime_header
    assert "const auto first_addr = reinterpret_cast<uptr>(first);" in runtime_header
    assert "const auto last_addr = reinterpret_cast<uptr>(last);" in runtime_header
    assert "if (last < first)" not in runtime_header
    assert "last - first" not in runtime_header
    assert "template<class T> inline Result<usize> contiguous_range_size" not in runtime_header
    assert "template<class Range> Status assign(const Range &values) noexcept" in vector_body
    assert "template<class Range> Status append(const Range &values) noexcept" in vector_body
    assert "template<class Range> Status prepend(const Range &values) noexcept" in vector_body
    assert "temp.append_range_data(contiguous_range_data(values), *count)" in vector_body
    assert "::std::memcpy(&data_[size_], values, count * sizeof(T));" in vector_body
    assert "if constexpr (::std::is_trivially_copyable_v<T>) {\n                return assign(other);\n            } else {" in vector_body
    assert "if (*total > max_size())" in vector_body
    assert "template<class Range> Status assign(const Range &values) noexcept" in array_body
    assert "template<class Range> Status append(const Range &values) noexcept" in array_body
    assert "template<class Range> Status prepend(const Range &values) noexcept" in array_body
    assert "temp.append_range_data(contiguous_range_data(values), *count)" in array_body
    assert "::std::memcpy(ptr(size_), values, count * sizeof(T));" in array_body
    assert "if constexpr (::std::is_trivially_copyable_v<T>) {\n                return assign(other);\n            } else {" in array_body
    assert "if (*total > Max)" in array_body


def test_runtime_byte_containers_use_bulk_copy_helpers() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]
    byte_array_body = runtime_header.split("template<usize Max> struct ByteArray {", maxsplit=1)[1].split(
        "template<usize Max> struct FixedByteArray {", maxsplit=1
    )[0]
    fixed_byte_array_body = runtime_header.split("template<usize Max> struct FixedByteArray {", maxsplit=1)[1].split(
        "template<class Config> struct Bytes {", maxsplit=1
    )[0]
    bytes_body = runtime_header.split("template<class Config> struct Bytes {", maxsplit=1)[1].split(
        "template<class Config> struct String {", maxsplit=1
    )[0]
    slice_reader_body = runtime_header.split("struct SliceReader {", maxsplit=1)[1].split(
        "struct ReaderRef {", maxsplit=1
    )[0]
    slice_writer_body = runtime_header.split("struct SliceWriter {", maxsplit=1)[1].split(
        "template<class Reader> Result<u64> read_varint", maxsplit=1
    )[0]

    assert "#include <cstring>" in runtime_header
    assert "inline void copy_bytes(u8 *dst, const u8 *src, const usize count) noexcept" in runtime_header
    assert "if (!count || dst == src)" in runtime_header
    assert "::std::memmove(dst, src, count);" in runtime_header
    assert "::std::memcpy(dst, src, count);" in runtime_header
    assert "constexpr bool bytes_equal(const ByteView lhs, const ByteView rhs) noexcept" in runtime_header
    assert "if (!lhs.size)" in runtime_header
    assert "if (::std::is_constant_evaluated())" in runtime_header
    assert "return ::std::memcmp(lhs.data, rhs.data, lhs.size) == 0;" in runtime_header
    assert "copy_bytes(bytes_, other.bytes_, other.size_);" in byte_array_body
    assert "::std::memset(bytes_ + size_, 0, count - size_);" in byte_array_body
    assert "copy_bytes(bytes_, other.bytes_, Max);" in fixed_byte_array_body
    assert "::std::memset(bytes_, 0, Max);" in fixed_byte_array_body
    assert "copy_bytes(temp.data(), view.data, view.size);" in bytes_body
    assert "copy_bytes(out, data_ + pos_, count);" in slice_reader_body
    assert "copy_bytes(data_ + pos_, data, count);" in slice_writer_body
    assert "for (usize i {}; i < count; ++i)" not in slice_reader_body
    assert "for (usize i {}; i < count; ++i)" not in slice_writer_body


def test_runtime_discriminators_follow_payload_storage() -> None:
    runtime_header = runtime_files()["protocyte/runtime/runtime.hpp"]

    result_body = runtime_header.split("template<class T, class E = Error> struct Result {", maxsplit=1)[1].split(
        "template<class E> struct Result<void, E> {", maxsplit=1
    )[0]
    result_storage = result_body.split("protected:", maxsplit=1)[1]
    assert ": value_ {}, ok_ {true}" in result_body
    assert ": error_ {unexpected_value.error()}, ok_ {false}" in result_body
    assert result_storage.index("union {\n            T value_;") < result_storage.index("bool ok_;")

    void_result_body = runtime_header.split("template<class E> struct Result<void, E> {", maxsplit=1)[1].split(
        "using Status = Result<void>;", maxsplit=1
    )[0]
    void_result_storage = void_result_body.split("protected:", maxsplit=1)[1]
    assert void_result_storage.index("Storage storage_;") < void_result_storage.index("bool ok_ {true};")

    optional_body = runtime_header.split("template<class T> struct Optional {", maxsplit=1)[1].split(
        "template<class T, class Config> struct Vector {", maxsplit=1
    )[0]
    optional_storage = optional_body.split("protected:", maxsplit=1)[1]
    assert optional_storage.index("alignas(T) unsigned char storage_[sizeof(T)];") < optional_storage.index(
        "bool has_ {};"
    )

    fixed_bytes_body = runtime_header.split("template<usize Max> struct FixedByteArray {", maxsplit=1)[1].split(
        "template<class Config> struct Bytes {", maxsplit=1
    )[0]
    fixed_bytes_storage = fixed_bytes_body.split("protected:", maxsplit=1)[1]
    assert fixed_bytes_storage.index("u8 bytes_[Max];") < fixed_bytes_storage.index("bool has_ {};")


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
    assert response.supported_features & plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    files = {item.name: item.content for item in response.file}
    assert "simple.protocyte.hpp" in files
    assert "simple.protocyte.cpp" in files
    assert "protocyte/runtime/runtime.hpp" in files
    assert "struct Sample;" in files["simple.protocyte.hpp"]
    assert files["simple.protocyte.hpp"].startswith("#pragma once\n\n#ifndef PROTOCYTE_GENERATED_SIMPLE_PROTO_")
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
    assert "default_max_recursion_depth = 100u" in files["protocyte/runtime/runtime.hpp"]
    assert "default_max_message_bytes = 0x7fffffffu" in files["protocyte/runtime/runtime.hpp"]
    assert "default_max_string_bytes = 0x7fffffffu" in files["protocyte/runtime/runtime.hpp"]
    assert "usize recursion_depth {};" in files["protocyte/runtime/runtime.hpp"]
    assert "protocyte Config::Context must expose recursion_depth for recursion-limited parsing" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "template <typename Config = ::protocyte::DefaultConfig>" in files["simple.protocyte.hpp"]
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
    assert "template<class T, class E = Error> struct Result {" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class E> struct Result<void, E> {" in files["protocyte/runtime/runtime.hpp"]
    assert "using value_type = T;" in files["protocyte/runtime/runtime.hpp"]
    assert "using error_type = E;" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Result() noexcept(noexcept(T {}))" in files["protocyte/runtime/runtime.hpp"]
    assert "requires(!ResultType<U> && !UnexpectedType<U>)" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Result(const Result<U, G> &other)" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Result(Result<U, G> &&other)" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Result(const Result<void, G> &other)" in files["protocyte/runtime/runtime.hpp"]
    assert "static constexpr Result ok() noexcept" not in files["protocyte/runtime/runtime.hpp"]
    assert "const usize offset," in files["protocyte/runtime/runtime.hpp"]
    assert "inline void *hosted_allocate(void *, const usize size, const usize alignment) noexcept {" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "constexpr Unexpected<Error> unexpected(const ErrorCode code, const usize offset," in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "u64 value {};" in files["protocyte/runtime/runtime.hpp"]
    assert "u64 value = {};" not in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[4u];" in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[8u];" in files["protocyte/runtime/runtime.hpp"]
    assert "u8 bytes[8u] {\n" in files["protocyte/runtime/runtime.hpp"]
    assert "return ::std::memcmp(lhs.data, rhs.data, lhs.size) == 0;" in files["protocyte/runtime/runtime.hpp"]
    assert "if (!size)" in files["protocyte/runtime/runtime.hpp"]
    assert "concept ByteViewConvertible" not in files["protocyte/runtime/runtime.hpp"]
    assert "inline Result<usize> checked_add(const usize lhs, const usize rhs) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "inline Result<usize> checked_mul(const usize lhs, const usize rhs) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "const auto count = contiguous_range_size(value);" in files["protocyte/runtime/runtime.hpp"]
    assert "return checked_mul(*count, sizeof(ContiguousRangeElement<T>));" in files["protocyte/runtime/runtime.hpp"]
    assert "concept ByteViewRange" in files["protocyte/runtime/runtime.hpp"]
    assert "inline Result<ByteView> byte_view_of(const ByteView view) noexcept" in files["protocyte/runtime/runtime.hpp"]
    assert "Result<ByteView> byte_view_of(const T &value) noexcept" in files["protocyte/runtime/runtime.hpp"]
    assert "other.size_ = {};" in files["protocyte/runtime/runtime.hpp"]
    assert "const auto bytes = checked_mul(requested, sizeof(T));" in files["protocyte/runtime/runtime.hpp"]
    assert "explicit Vector(Context *ctx = nullptr) noexcept: ctx_ {ctx} {}" in files["protocyte/runtime/runtime.hpp"]
    assert "void bind(Context *ctx) noexcept { ctx_ = ctx; }" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr usize capacity() const noexcept { return Max; }" in files["protocyte/runtime/runtime.hpp"]
    assert "if (ctx_ != nullptr && view.size > ctx_->limits.max_string_bytes) {" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "using reverse_iterator = ReverseIterator<const u8>;" in files["protocyte/runtime/runtime.hpp"]
    assert "offset_ptr(" not in files["protocyte/runtime/runtime.hpp"]
    assert "using iterator = typename Config::Bytes::const_iterator;" in files["protocyte/runtime/runtime.hpp"]
    assert "using reverse_iterator = typename Config::Bytes::const_reverse_iterator;" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "using Bucket = Optional<Entry>;" in files["protocyte/runtime/runtime.hpp"]
    assert "struct EntryProxy {" in files["protocyte/runtime/runtime.hpp"]
    assert "struct ConstEntryProxy {" in files["protocyte/runtime/runtime.hpp"]
    assert "iterator begin() noexcept { return iterator {buckets_.begin(), buckets_.end()}; }" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "const_iterator begin() const noexcept { return const_iterator {buckets_.begin(), buckets_.end()}; }" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "template<class Fn> Status for_each(Fn &&fn) noexcept" not in files["protocyte/runtime/runtime.hpp"]
    assert "template<class Fn> Status for_each(Fn &&fn) const noexcept" not in files["protocyte/runtime/runtime.hpp"]
    assert "struct Tag {" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Tag decode_tag(const u64 raw) noexcept" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class Reader> Result<Tag> read_tag(Reader &reader) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "template<class E> struct Unexpected {" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr auto unexpected(E &&error_value) noexcept(" in files["protocyte/runtime/runtime.hpp"]
    assert "requires(!UnexpectedType<E>)" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class U = T>" in files["protocyte/runtime/runtime.hpp"]
    assert "Result<void, E> status() const & noexcept" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr auto and_then(F &&f) & noexcept(" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr auto transform(F &&f) & noexcept(" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr auto or_else(F &&f) & noexcept(" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr auto transform_error(F &&f) & noexcept(" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr Result() noexcept = default;" in files["protocyte/runtime/runtime.hpp"]
    assert "union Storage {" in files["protocyte/runtime/runtime.hpp"]
    assert "static constexpr Result err(const ErrorCode code, const usize offset = {}, const u32 field_number = {}) noexcept" not in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "constexpr void operator*() const noexcept {}" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr void value() const noexcept {}" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class T> struct Optional {" in files["protocyte/runtime/runtime.hpp"]
    assert "T &operator*() & noexcept { return *ptr(); }" in files["protocyte/runtime/runtime.hpp"]
    assert "const T &operator*() const & noexcept { return *ptr(); }" in files["protocyte/runtime/runtime.hpp"]
    assert "T *operator->() noexcept { return ptr(); }" in files["protocyte/runtime/runtime.hpp"]
    assert "const T *operator->() const noexcept { return ptr(); }" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class T, class Config> struct Box {" in files["protocyte/runtime/runtime.hpp"]
    assert "T &operator*() noexcept { return *ptr_; }" in files["protocyte/runtime/runtime.hpp"]
    assert "const T &operator*() const noexcept { return *ptr_; }" in files["protocyte/runtime/runtime.hpp"]
    assert "T *operator->() noexcept { return ptr_; }" in files["protocyte/runtime/runtime.hpp"]
    assert "const T *operator->() const noexcept { return ptr_; }" in files["protocyte/runtime/runtime.hpp"]
    assert "template<class T> struct Ref {" in files["protocyte/runtime/runtime.hpp"]
    assert "constexpr T &operator*() const noexcept { return *ptr_; }" in files["protocyte/runtime/runtime.hpp"]
    assert "const auto [field, wire] = *tag;" in files["protocyte/runtime/runtime.hpp"]
    assert "Status skip_field(Reader &reader, const WireType wire_type, const u32 field_number = {}) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status write_tag(Writer &writer, const u32 field_number, const WireType wire_type) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status expect_wire_type(Reader &reader, const WireType actual, const WireType expected," in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Result<usize> read_length_delimited_size(Reader &reader) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "if (len > static_cast<u64>(~static_cast<usize>(0u))) {" in files["protocyte/runtime/runtime.hpp"]
    assert "return protocyte::unexpected(ErrorCode::integer_overflow, reader.position());" in files[
        "protocyte/runtime/runtime.hpp"
    ] or "return protocyte::unexpected(ErrorCode::integer_overflow, {});" in files["protocyte/runtime/runtime.hpp"]
    assert "return read_length_delimited_size(reader)" in files["protocyte/runtime/runtime.hpp"]
    assert "open_nested_message(typename Config::Context &ctx, Reader &reader, const u32 field_number) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status read_message(typename Config::Context &ctx, Reader &reader, const u32 field_number, Message &out) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "template<class Config, class Reader> Status skip_field(typename Config::Context &ctx, Reader &reader," in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status read_string_field(typename Config::Context &ctx, Reader &reader," in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status write_bytes_field(Writer &writer, const u32 field_number, const ByteView view) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Result<f64> read_double_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status write_double_field(Writer &writer, const u32 field_number, const f64 value) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Status write_message_field(Writer &writer, const u32 field_number, const Message &value) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "Result<usize> message_field_size(const u32 field_number, const Message &value) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "inline Result<usize> length_delimited_field_size(const u32 field_number, const usize payload_size) noexcept" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "return checked_add(prefix_size, payload_size);" in files["protocyte/runtime/runtime.hpp"]
    assert "return copied.assign(value.view()).transform([&copied]() noexcept -> T {" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "return expect_wire_type(reader, wire_type, WireType::VARINT, field_number)" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "return value.encoded_size().and_then([field_number](const usize size) noexcept -> Result<usize> {" in files[
        "protocyte/runtime/runtime.hpp"
    ]
    assert "return length_delimited_field_size(field_number, size);" in files["protocyte/runtime/runtime.hpp"]
    assert (
        "constexpr usize tag_size(const u32 field_number, const WireType wire_type = WireType::LEN) noexcept"
        in files["protocyte/runtime/runtime.hpp"]
    )
    assert "return wire_type == WireType::SGROUP ? size * 2u : size;" in files["protocyte/runtime/runtime.hpp"]
    assert "FEATURE_PROTO3_OPTIONAL" not in files["simple.protocyte.hpp"]


def test_runtime_string_assign_checks_size_limit_before_utf8_validation() -> None:
    files = runtime_files()
    header = files["protocyte/runtime/runtime.hpp"]

    assign_body = header.split("Status assign(const ByteView view) noexcept {", maxsplit=1)[1]
    assign_body = assign_body.split("Status assign_owned", maxsplit=1)[0]

    assert "if (const auto st = check_size_limit(view.size); !st)" in assign_body
    assert assign_body.index("check_size_limit(view.size)") < assign_body.index("validate_utf8(view)")

    assign_owned_body = header.split("Status assign_owned(typename Config::Bytes &&bytes) noexcept {", maxsplit=1)[1]
    assign_owned_body = assign_owned_body.split("protected:", maxsplit=1)[0]

    assert "if (const auto st = check_size_limit(bytes.size()); !st)" in assign_owned_body
    assert assign_owned_body.index("check_size_limit(bytes.size())") < assign_owned_body.index(
        "validate_utf8(bytes.view())"
    )


def test_rejects_non_proto3_target() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("legacy.proto")
    file = request.proto_file.add()
    file.name = "legacy.proto"
    file.syntax = "proto2"
    file.message_type.add().name = "Legacy"

    response = generate_response(request)

    assert 'expected syntax = "proto3"' in response.error


def test_generation_succeeds_without_clang_format_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(protocyte_cpp.shutil, "which", lambda name: None)

    def fail_run(*args, **kwargs):
        raise AssertionError("clang-format should not be invoked when it is unavailable")

    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fail_run)

    response = generate_response(_basic_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    assert files["simple.protocyte.hpp"].startswith("#pragma once\n")


def test_generation_uses_explicit_clang_format_override_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
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
    response = generate_response(_basic_request(parameter=f"_protocyte_options_hex={encoded}"))

    assert not response.error
    assert commands
    assert all(command[0] == "C:/Program Files/LLVM/bin/clang-format.exe" for command in commands)
    assert all(f"--style=file:{config_path.as_posix()}" in command for command in commands)


def test_generation_reports_explicit_clang_format_launch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("missing executable")),
    )

    response = generate_response(_basic_request(parameter="clang_format=missing-format"))

    assert "failed to run clang-format" in response.error
    assert "missing executable" in response.error


def test_generation_reports_explicit_clang_format_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        protocyte_cpp.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="broken style"),
    )

    response = generate_response(_basic_request(parameter="clang_format=my-format"))

    assert "clang-format failed for simple.protocyte.hpp: broken style" in response.error


def test_generation_passes_explicit_clang_format_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "custom.style"
    config_path.write_text("BasedOnStyle: LLVM\n", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        assume_filename = next(part for part in command if part.startswith("--assume-filename="))
        return SimpleNamespace(returncode=0, stdout=assume_filename + "\n", stderr="")

    monkeypatch.setattr(protocyte_cpp.subprocess, "run", fake_run)

    response = generate_response(
        _basic_request(parameter=f"clang_format=my-format,clang_format_config={config_path.as_posix()}")
    )

    assert not response.error
    assert commands
    assert all(f"--style=file:{config_path.as_posix()}" in command for command in commands)


def test_generation_reports_missing_explicit_clang_format_config(tmp_path: Path) -> None:
    missing_config = tmp_path / "missing.style"

    response = generate_response(
        _basic_request(parameter=f"clang_format=my-format,clang_format_config={missing_config.as_posix()}")
    )

    assert response.error == f"clang-format config was not found: {missing_config.as_posix()}"


def test_generation_uses_clang_format_found_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        assume_filename = next(part for part in command if part.startswith("--assume-filename="))
        filename = assume_filename.split("=", 1)[1]
        return SimpleNamespace(returncode=0, stdout=f"formatted:{filename}\n", stderr="")

    monkeypatch.setattr(protocyte_cpp.shutil, "which", lambda name: "/usr/bin/clang-format")
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
    header = next(file.content for file in response.file if file.name == "simple.protocyte.hpp")

    assert "namespace demo {" in header
    assert "bool has_opt_name() const noexcept" in header
    assert "struct Sample {" in header
    assert "typename Config::template Map<typename Config::String, ::protocyte::i32> items_;" in header
    assert "typename Config::template Box<::demo::Sample<Config>> self_;" in header
    assert "ctx_{&ctx}" in header
    assert "items_{&ctx}" in header
    assert "samples_{&ctx}" in header
    assert "::protocyte::Status set_id(const ::protocyte::i32 value) noexcept" in header
    assert "const auto tag = ::protocyte::read_tag(reader);" in header
    assert "const auto [field_number, wire_type] = *tag;" in header
    assert "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept" in header
    assert "insert_or_assign(::protocyte::move(key), ::protocyte::move(value))" in header
    assert "template <typename Reader>" in header
    assert "::protocyte::Status merge_from(Reader& reader) noexcept" in header
    assert "for (const auto &packed_value_samples : samples_) {" in header
    assert "if (const auto st = out->copy_from(*this); !st)" in header
    assert "if (wire_type != ::protocyte::WireType::LEN)" in header
    assert "enum struct FieldNumber : ::protocyte::u32 {" in header
    assert "id = 1u," in header
    assert "opt_name = 2u," in header
    assert "case FieldNumber::id: {" in header
    assert "case FieldNumber::opt_name: {" in header
    assert "::protocyte::read_float(packed).transform([&](const auto decoded) noexcept { value = decoded; });" in header
    assert "auto decoded = ::protocyte::read_fixed32(packed);" not in header
    assert "::protocyte::read_int32_field(reader, wire_type, field_number).transform(" in header
    assert "::protocyte::write_int32_field(writer, static_cast<::protocyte::u32>(FieldNumber::id), id_);" in header
    assert "::protocyte::read_string_field<Config>(*ctx_, reader, wire_type," in header
    assert "::protocyte::write_string_field(" in header
    assert "::protocyte::write_message_field(" in header
    assert "::protocyte::message_field_size(" in header
    assert "FieldNumber::opt_name), opt_name_.view());" in header
    assert ".transform([&](const auto decoded) noexcept {" in header
    assert "::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::self), *self_).and_then(" in header
    assert "::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);" in header
    assert "ensure_self().and_then([&](auto ensured) noexcept -> ::protocyte::Status { return ::protocyte::read_message<Config>(*ctx_, reader, field_number, *ensured); });" in header
    assert "return has_self() ? self_.operator->() : nullptr;" in header
    assert "*ctx_, entry_reader, static_cast<::protocyte::u32>(EntryFieldNumber::value)," in header
    assert "::protocyte::skip_field<Config>(*ctx_, entry_reader, entry_wire," in header
    assert "mutable_items().copy_from(other.items())" in header
    assert "mutable_samples().copy_from(other.samples())" in header
    assert "mutable_message_items().copy_from(other.message_items())" in header
    assert "const auto packed_reserve_samples = ::protocyte::checked_add(samples_.size(), *len / 4u);" in header
    assert "samples_.reserve(*packed_reserve_samples)" in header
    assert "const auto packed_size_samples_result = ::protocyte::checked_mul(samples_.size(), 4u);" in header


def test_checked_smoke_output_reflects_copy_propagation() -> None:
    header = (Path(__file__).resolve().parents[1] / "smoke" / "generated" / "example.protocyte.hpp").read_text(
        encoding="utf-8"
    )
    cross_header = (
        Path(__file__).resolve().parents[1] / "smoke" / "generated" / "cross_package.protocyte.hpp"
    ).read_text(encoding="utf-8")

    assert "copy_from(const UltimateComplexMessage &other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "mutable_r_int32_unpacked().copy_from(other.r_int32_unpacked())" in header
    assert "mutable_r_int32_packed().copy_from(other.r_int32_packed())" in header
    assert "mutable_r_double().copy_from(other.r_double())" in header
    assert "mutable_map_str_int32().copy_from(other.map_str_int32())" in header
    assert "mutable_map_uint64_msg().copy_from(other.map_uint64_msg())" in header
    assert "::protocyte::Result<UltimateComplexMessage> clone() const noexcept" in header
    assert "if (const auto st = out->copy_from(*this); !st) {" in header
    assert "return has_recursive_self() ? recursive_self_.operator->() : nullptr;" in header
    assert "static_cast<::protocyte::u32>(FieldNumber::recursive_self), *recursive_self_" in header
    assert "fixed_integer_array_.size() != 0u && fixed_integer_array_.size() != 3u" in header
    assert "fixed_repeated_byte_array_.size() != 0u && fixed_repeated_byte_array_.size() != 3u" in header
    assert (
        "for (const auto &packed_value_remote_values : remote_values_) {\n"
        "                    {\n"
        "                        {"
        not in cross_header
    )
    assert (
        "for (const auto &packed_value_remote_values : remote_values_) {\n"
        "                    {"
        not in cross_header
    )
    assert (
        "for (const auto &remote_values_value : remote_values_) {\n"
        "                    {"
        not in cross_header
    )
    assert (
        "if (!remote_bytes_.empty()) {\n"
        "                {"
        not in cross_header
    )
    weird_map_serialize = header.split("for (const auto entry : weird_map_) {", maxsplit=1)[1].split(
        "if (deep_oneof_case_", maxsplit=1
    )[0]
    assert weird_map_serialize.count("                {\n                    const auto st_size =") == 2
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

    file_constants = {constant.name: constant for constant in model.files["arrays.proto"].constants}
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

    assert "field collides with 'class' after C++ identifier normalization" in response.error


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
    header = next(file.content for file in response.file if file.name == "accessor_names.protocyte.hpp")
    assert "void clear_values() noexcept" in header
    assert "::protocyte::Status set_set_values(const ::protocyte::i32 value) noexcept" in header


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
    for proto_name, message_name in (("foo-bar.proto", "Hyphen"), ("foo_bar.proto", "Underscore")):
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
    assert guards["foo-bar.protocyte.hpp"].startswith("PROTOCYTE_GENERATED_FOO_BAR_PROTO_")
    assert guards["foo_bar.protocyte.hpp"].startswith("PROTOCYTE_GENERATED_FOO_BAR_PROTO_")


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
    request.proto_file.extend([_options_file(), _array_bound_expr_file("negative_mod_bound.proto", "(-5 % 3) + 1")])

    model = build_model(request)
    field = model.messages["demo.ArrayBound"].fields[0]
    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert field.array_max == 2
    assert field.array_cpp_max == "2u"
    assert not response.error
    assert "::protocyte::ByteArray<2u> data_;" in files["negative_mod_bound.protocyte.hpp"]
    assert "-5u" not in files["negative_mod_bound.protocyte.hpp"]


def test_array_expression_same_package_file_constant_is_inlined() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("same_package_user.proto")
    request.proto_file.extend([_options_file(), _same_package_constant_provider_file(), _same_package_constant_user_file()])

    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert not response.error
    assert "::protocyte::ByteArray<6u> data_;" in files["same_package_user.protocyte.hpp"]
    assert "ByteArray<CAP + 1u>" not in files["same_package_user.protocyte.hpp"]


def test_large_integer_division_preserves_precision() -> None:
    assert _ExprParser("9007199254740993 / 1", lambda name: None, "large").parse().value == 9007199254740993
    assert _ExprParser("-5 / 2", lambda name: None, "negative").parse().value == -2


def test_generated_header_emits_constants_and_array_storage() -> None:
    response = generate_response(_constant_array_request())

    assert not response.error
    files = {item.name: item.content for item in response.file}
    header = files["arrays.protocyte.hpp"]
    runtime_header = files["protocyte/runtime/runtime.hpp"]

    assert '#include <protocyte/runtime/runtime.hpp>\n\n#include <string_view>' in header
    assert "#include <string_view>" in header
    assert "inline constexpr ::protocyte::u32 FILE_CAP {16u};" in header
    assert 'inline constexpr ::std::string_view FILE_LABEL {"ell", 3u};' in header
    assert "inline constexpr bool FILE_READY {true};" in header
    assert "static constexpr ::protocyte::i32 MAGIC_NUMBER {16};" in header
    assert "static constexpr ::protocyte::i32 DOUBLE_MAGIC {32};" in header
    assert "static constexpr ::protocyte::u32 HEX_MAGIC {32u};" in header
    assert "static constexpr ::protocyte::i32 HEX_EXPR {24};" in header
    assert 'static constexpr ::std::string_view LABEL {"ell", 3u};' in header
    assert "static constexpr bool HAS_PREFIX {true};" in header
    assert "::protocyte::FixedByteArray<32u> digest_;" in header
    assert "::protocyte::ByteArray<16u> blob_;" in header
    assert "::protocyte::ByteArray<16u> hex_blob_;" in header
    assert "::protocyte::Array<::protocyte::i32, 4u> values_;" in header
    assert "bool has_digest() const noexcept { return digest_.has_value(); }" in header
    assert "::protocyte::MutableByteView mutable_digest() noexcept {" in header
    assert "if (ctx_->limits.max_string_bytes < 32u) {" in header
    assert "::protocyte::usize digest_size() const noexcept" not in header
    assert "digest_max_size" not in header
    assert "::protocyte::Status resize_blob(const ::protocyte::usize size) noexcept" in header
    assert "::protocyte::ByteView digest() const noexcept { return digest_.view(); }" in header
    assert "template<class Value>\n  ::protocyte::Status set_digest(const Value &value) noexcept" in header
    assert "template<class Value>\n  ::protocyte::Status set_blob(const Value &value) noexcept" in header
    assert "requires(::protocyte::ByteViewRange<Value>)" in header
    assert "::protocyte::ByteViewConvertible" not in header
    assert "::protocyte::Status set_blob(const ::protocyte::ByteView value) noexcept" not in header
    assert "const auto view = ::protocyte::byte_view_of(value);" in header
    assert "if (!view)" in header
    assert "return view.status();" in header
    assert "if (const auto st = blob_.assign(*view); !st)" in header
    assert "if (*len != 32u)" in header
    assert "if (values_.size() != 0u && values_.size() != 4u) {" in header
    assert "template<class T, usize Max> struct Array" in runtime_header
    assert "template<usize Max> struct ByteArray" in runtime_header
    assert "template<usize Max> struct FixedByteArray" in runtime_header
    assert "iterator end() noexcept { return bytes_ + size_; }" in runtime_header
    assert "const_iterator end() const noexcept { return bytes_ + size_; }" in runtime_header
    assert "iterator end() noexcept { return bytes_ + size(); }" in runtime_header
    assert "const_iterator end() const noexcept { return bytes_ + size(); }" in runtime_header
    assert "u8 bytes_[Max];" in runtime_header
    assert "u8 bytes_[Max] {};" not in runtime_header


def test_generated_header_emits_portable_i64_min_constant() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("i64_min.proto")
    request.proto_file.extend([_options_file(), _i64_min_constant_file()])

    response = generate_response(request)
    files = {item.name: item.content for item in response.file}

    assert not response.error
    assert "static constexpr ::protocyte::i64 MIN {(-9223372036854775807ll - 1ll)};" in files[
        "i64_min.protocyte.hpp"
    ]
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
    assert "explicit Array(Context *ctx = nullptr) noexcept: ctx_ {ctx} {}" in runtime_header
    assert "Context *context() const noexcept { return ctx_.context(); }" in runtime_header
    assert "void bind(Context *ctx) noexcept { ctx_.bind(ctx); }" in runtime_header
    assert "ctx_.bind(other.context());" in runtime_header
    assert "new (ptr(size_)) T {context()};" in runtime_header
    assert "Array temp {context()};" in runtime_header
    assert "auto copied = protocyte::copy_value(context(), value);" in runtime_header
    assert "auto copied = protocyte::copy_value(value);" not in runtime_header
    assert "Status copy_from(const Vector &other) noexcept" in runtime_header
    assert "for (auto &value : other)" in runtime_header
    assert runtime_header.count("for (const auto &value : other)") >= 2
    assert "for (usize i {}; i < other.size_; ++i)" not in runtime_header
    assert "Status copy_from(const HashMap &other) noexcept" in runtime_header
    assert "for (auto &bucket : buckets_)" in runtime_header
    assert "for (usize i {}; i < buckets_.size(); ++i)" not in runtime_header
    assert "ByteArray(ByteArray &&other) noexcept" in runtime_header
    assert "ByteArray &operator=(ByteArray &&other) noexcept" in runtime_header
    assert "FixedByteArray(FixedByteArray &&other) noexcept" in runtime_header
    assert "FixedByteArray &operator=(FixedByteArray &&other) noexcept" in runtime_header


@pytest.mark.parametrize(
    ("expected", "request_factory"),
    [
        ("constant name must not be empty", lambda: _empty_constant_name_request()),
        ("exactly one typed constant value must be set", lambda: _missing_constant_value_request()),
        ("expression must evaluate to bool", lambda: _boolean_expr_type_error_request()),
        ("value 4294967296 is out of range for uint32", lambda: _typed_expr_overflow_request()),
        (
            "protocyte.array.fixed requires protocyte.array.max or protocyte.array.expr",
            lambda: _fixed_without_array_request(),
        ),
        ("protocyte.array is not supported on map fields", lambda: _array_on_map_request()),
        ("protocyte.array.max must be greater than zero", lambda: _zero_max_request()),
        ("protocyte.array.expr must not be empty", lambda: _empty_expr_request()),
    ],
)
def test_rejects_remaining_model_validator_branches(expected: str, request_factory) -> None:
    response = generate_response(request_factory())

    assert expected in response.error


def test_rejects_internal_typed_constant_literal_overflow_and_array_exclusivity() -> None:
    owner = SimpleNamespace(full_name="demo.Broken", descriptor=descriptor_pb2.DescriptorProto())

    constant = _build_constants(
        owner,
        SimpleNamespace(
            message_constants=lambda options: [
                SimpleNamespace(name="BROKEN", kind=CONSTANT_KIND_UINT32, literal=4294967296, expr=None)
            ]
        ),
    )[0]
    with pytest.raises(ProtocyteError, match="value 4294967296 is out of range for uint32"):
        _coerce_literal(constant.kind, constant.literal, constant.full_name)

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
    assert "return {};" in header
    assert "switch (other.choice_case_) {" in header
    assert "case ChoiceCase::text: {" in header
    assert "if (const auto st = set_text(other.text()); !st) {" in header
    assert "return st;" in header
    assert "ensure_inner().and_then([&](auto ensured) noexcept -> ::protocyte::Status { return ensured->copy_from(*other.inner()); });" in header
    assert "clear_choice();" in header


def test_generated_header_uses_other_for_repeated_array_only_copy() -> None:
    response = generate_response(_repeated_array_only_request())

    assert not response.error
    header = next(item.content for item in response.file if item.name == "repeated_array_only.protocyte.hpp")

    assert "copy_from(const OnlyArrays& other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "return {};" in header
    assert "mutable_values().copy_from(other.values())" in header


def test_generated_header_uses_real_other_for_map_only_copy() -> None:
    response = generate_response(_map_only_request())

    assert not response.error
    header = next(item.content for item in response.file if item.name == "map_only.protocyte.hpp")

    assert "copy_from(const OnlyMaps& other) noexcept" in header
    assert "if (this == &other) {" in header
    assert "const auto& source = other;" in header
    assert "mutable_items().copy_from(source.items())" in header
    assert "if (const auto st = out->copy_from(*this); !st) {" in header


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
    assert sink_fields["values"].array_cpp_max == "18u"
    assert nested_fields["nested_payload"].array_max == 9
    assert nested_fields["nested_payload"].array_cpp_max == "9u"


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
    assert "::protocyte::ByteArray<8u> payload_;" in header
    assert "::protocyte::Array<::protocyte::i32, 18u> values_;" in header
    assert "::protocyte::ByteArray<9u> nested_payload_;" in header


def test_resolves_package_constants_across_packages() -> None:
    model = build_model(_cross_package_package_constant_request())
    file_constants = {constant.name: constant for constant in model.files["cross_package_package.proto"].constants}
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
    assert 'static constexpr ::std::string_view NAME {"pkg-label-ok", 12u};' in header
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
    assert 'static constexpr ::std::string_view NAME {"pkg-label-source-ok", 19u};' in header
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
    header = next(file.content for file in response.file if file.name == "float_bound.protocyte.hpp")
    assert "::protocyte::ByteArray<2u> data_;" in header
    assert "return 2u;" in header
    assert "2.0" not in header


def test_generated_header_emits_utf8_string_constants() -> None:
    response = generate_response(_unicode_constant_request())

    assert not response.error
    header = next(file.content for file in response.file if file.name == "unicode.protocyte.hpp")
    assert '#include <protocyte/runtime/runtime.hpp>\n\n#include <string_view>' in header
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
    duplicate_response = generate_response(_constant_collision_request("duplicate.proto", [("dup", "i32", 1), ("dup", "i32", 2)]))
    normalized_response = generate_response(
        _constant_collision_request("normalized.proto", [("cap-value", "i32", 1), ("cap_value", "i32", 2)])
    )
    reserved_response = generate_response(_constant_collision_request("reserved.proto", [("create", "i32", 1)]))

    assert "constant cannot be redefined" in duplicate_response.error
    assert "collides after C++ identifier normalization" in normalized_response.error
    assert "collides with generated API" in reserved_response.error


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
    assert "new (&choice.count) ::protocyte::i32 {value};" in header
    assert "new (&choice.inner) typename Config::template Optional<::demo::Carrier_Inner<Config>> {};" in header
    assert "return has_inner() && choice.inner.has_value() ? choice.inner.operator->() : nullptr;" in header
    assert "::protocyte::Ref<::demo::Carrier_Inner<Config>>{*choice.inner}" in header
    assert "new (&choice.none)::protocyte::u8(0u);" not in header
    assert "::protocyte::u8 none;" not in header
    assert "return choice.inner.emplace(*ctx_).transform(" in header
    assert "clear_choice();" in header
    assert "choice_case_ == ChoiceCase::text" in header
    assert "choice_case_ == ChoiceCase::inner" in header
    assert "::protocyte::i32 before_{};" in protected
    assert "::protocyte::i32 after_{};" in protected
    assert protected.index("::protocyte::i32 before_{};") < protected.index("ChoiceCase choice_case_ {ChoiceCase::none};")
    assert protected.index("ChoiceCase choice_case_ {ChoiceCase::none};") < protected.index("union ChoiceStorage {")
    assert protected.index("} choice;") < protected.index("::protocyte::i32 after_{};")
    assert "typename Config::String text = " not in header


def test_generated_header_uses_normalized_oneof_case_type() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("keyword_oneof.proto")
    request.proto_file.append(_keyword_oneof_file())

    response = generate_response(request)

    assert not response.error
    header = next(file.content for file in response.file if file.name == "keyword_oneof.protocyte.hpp")
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


@pytest.mark.parametrize("field_name", ["choice_case_", "none"])
def test_rejects_oneof_generated_member_collisions(field_name: str) -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("oneof_member_collision.proto")
    request.proto_file.append(_oneof_member_collision_file(field_name))

    response = generate_response(request)

    assert "field collides with generated API" in response.error


def test_generated_header_parses_bounded_oneof_bytes() -> None:
    response = generate_response(_oneof_array_request())

    assert not response.error
    header = next(file.content for file in response.file if file.name == "oneof_array.protocyte.hpp")
    assert "template<class Value>\n  ::protocyte::Status set_data(const Value &value) noexcept" in header
    assert "requires(::protocyte::ByteViewRange<Value>)" in header
    assert "const auto view = ::protocyte::byte_view_of(value);" in header
    assert "if (const auto st = temp.assign(*view); !st)" in header
    assert "::protocyte::Status set_data(const ::protocyte::ByteView value) noexcept" not in header
    assert "new (&choice.data) ::protocyte::ByteArray<8u> {};" in header
    assert "choice_case_ = ChoiceCase::data;" in header
    assert "if (const auto st = choice.data.resize(*len); !st) {" in header
    assert "if (*len > ctx_->limits.max_string_bytes) {" in header
    assert "if (const auto st = reader.read(choice.data.data(), choice.data.size()); !st) {" in header
    assert "new (&choice.data)::protocyte::ByteArray<8u> {ctx_};" not in header


def test_recursive_oneof_box_sets_case_after_successful_ensure() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("recursive_oneof.proto")
    request.proto_file.append(_recursive_oneof_file())

    response = generate_response(request)

    assert not response.error
    header = next(file.content for file in response.file if file.name == "recursive_oneof.protocyte.hpp")
    ensure_body = header.split("Result<::protocyte::Ref<::demo::Node<Config>>> ensure_child()", maxsplit=1)[1]
    ensure_body = ensure_body.split("template <typename Reader>", maxsplit=1)[0]

    assert "auto ensured = choice.child.ensure();" in ensure_body
    assert "if (!ensured) {\n      destroy_at_(&choice.child);\n      return ensured;\n    }" in ensure_body
    assert ensure_body.index("auto ensured = choice.child.ensure();") < ensure_body.index(
        "choice_case_ = ChoiceCase::child;"
    )


def test_empty_message_comments_unused_writer_and_returns_zero_size() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("empty.proto")
    request.proto_file.append(_empty_file())

    response = generate_response(request)

    assert not response.error
    header = next(file.content for file in response.file if file.name == "empty.protocyte.hpp")

    assert "::protocyte::Status serialize(Writer& /* writer */) const noexcept {" in header
    assert "::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {" in header
    assert "::protocyte::usize total {};" not in header
    assert "return ::protocyte::usize {};" in header


def test_generated_header_keeps_runtime_status_globally_qualified() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("namespaced.proto")
    request.proto_file.append(_protocyte_package_file())

    response = generate_response(request)

    assert not response.error
    header = next(file.content for file in response.file if file.name == "namespaced.protocyte.hpp")

    assert "namespace test::protocyte {" in header
    assert "::protocyte::Status merge_from(Reader& reader) noexcept {" in header
    assert "::protocyte::Status serialize(Writer& writer) const noexcept {" in header


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


def _cross_package_package_constant_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("cross_package_package.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend(
        [_options_file(), _external_constant_provider_file(), _cross_package_package_constant_file()]
    )
    return request


def _cross_package_message_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("cross_package_message.proto")
    request.parameter = "runtime=emit"
    request.proto_file.extend([_options_file(), _external_constant_provider_file(), _cross_package_message_file()])
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
    message.options.ParseFromString(_constant_options_bytes([("BROKEN", "boolean_expr", "1 + 1")]))
    return file


def _typed_expr_overflow_file() -> descriptor_pb2.FileDescriptorProto:
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "typed_expr_overflow.proto"
    file.package = "demo"
    file.syntax = "proto3"
    file.dependency.append("protocyte/options.proto")

    message = file.message_type.add()
    message.name = "Broken"
    message.options.ParseFromString(_constant_options_bytes([("BROKEN", "u32_expr", "4294967296")]))
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
    message.options.ParseFromString(_constant_options_bytes([("NAME", "str", chr(0x0100) + chr(0x00E9))]))
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
                ("READY", "boolean_expr", "Source.ROOT_ENABLED && (MIRRORED_CAP == 18)"),
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
    field.options.ParseFromString(_array_option_bytes(expr="alpha.beta.Source.ROOT_CAP + 1"))

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
