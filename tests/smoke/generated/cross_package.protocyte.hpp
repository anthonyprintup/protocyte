#pragma once

#ifndef PROTOCYTE_GENERATED_CROSS_PACKAGE_PROTO_1F7F3252503C_HPP
#define PROTOCYTE_GENERATED_CROSS_PACKAGE_PROTO_1F7F3252503C_HPP

#include <protocyte/runtime/runtime.hpp>

namespace test::crosspkg {

    inline constexpr ::protocyte::u32 FOREIGN_BASE {7u};
    inline constexpr ::protocyte::StringView FOREIGN_LABEL {"proto-xpkg", 10u};

    template<typename Config = ::protocyte::DefaultConfig> struct CrossPackageConstants_Nested;
    template<typename Config = ::protocyte::DefaultConfig> struct CrossPackageConstants;

    template<typename Config> struct CrossPackageConstants_Nested {
        using Context = typename Config::Context;
        static constexpr ::protocyte::u32 MIRRORED_COUNT {15u};

        enum struct FieldNumber : ::protocyte::u32 {
            nested_bytes = 1u,
        };

        explicit CrossPackageConstants_Nested(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static CrossPackageConstants_Nested create(Context &ctx) noexcept { return CrossPackageConstants_Nested {ctx}; }
        Context *context() const noexcept { return ctx_; }
        CrossPackageConstants_Nested(CrossPackageConstants_Nested &&) noexcept = default;
        CrossPackageConstants_Nested &operator=(CrossPackageConstants_Nested &&) noexcept = default;
        CrossPackageConstants_Nested(const CrossPackageConstants_Nested &) = delete;
        CrossPackageConstants_Nested &operator=(const CrossPackageConstants_Nested &) = delete;

        ::protocyte::Status copy_from(const CrossPackageConstants_Nested &source) noexcept {
            if (this == &source) {
                return {};
            }
            CrossPackageConstants_Nested staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const CrossPackageConstants_Nested &source,
                                      CrossPackageConstants_Nested &staging_message) noexcept {
            if (this == &source) {
                return {};
            }
            if (this == &staging_message || &source == &staging_message) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {});
            }
            reset_for_reuse_(staging_message, *ctx_);
            if (const auto st = staging_message.copy_from_in_place_(source); !st) {
                reset_for_reuse_(staging_message, *ctx_);
                return st;
            }
            *this = ::protocyte::move(staging_message);
            return {};
        }

        ::protocyte::Result<CrossPackageConstants_Nested> clone() const noexcept {
            auto output = CrossPackageConstants_Nested::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(CrossPackageConstants_Nested &output) const noexcept {
            if (this == &output) {
                return {};
            }
            reset_for_reuse_(output, *ctx_);
            if (const auto st = output.copy_from_in_place_(*this); !st) {
                reset_for_reuse_(output, *ctx_);
                return st;
            }
            return {};
        }

    protected:
        static void reset_for_reuse_(CrossPackageConstants_Nested &value, Context &ctx) noexcept {
            value.~CrossPackageConstants_Nested();
            new (&value) CrossPackageConstants_Nested {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const CrossPackageConstants_Nested &source) noexcept {
            if (const auto st = set_nested_bytes(source.nested_bytes()); !st) {
                return st;
            }
            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                if (const auto st =
                        unknown_fields_.copy_from(source.unknown_fields_, ctx_->limits.max_unknown_field_bytes);
                    !st) {
                    return st;
                }
            }
            return {};
        }

    public:

        ::protocyte::UnknownFieldRange unknown_fields() const noexcept {
            return ::protocyte::UnknownFieldRange {unknown_fields_.bytes(), ctx_->limits.max_recursion_depth};
        }
        ::protocyte::usize unknown_field_count() const noexcept { return unknown_fields().field_count(); }
        ::protocyte::Span<const ::protocyte::u8> unknown_field_bytes() const noexcept {
            return unknown_fields_.bytes();
        }
        void clear_unknown_fields() noexcept { unknown_fields_.clear(); }
        ::protocyte::MutableUnknownFieldSet<Config> mutable_unknown_fields() noexcept
            requires(::protocyte::preserve_unknown_fields_v<Config>)
        {
            return ::protocyte::MutableUnknownFieldSet<Config> {*ctx_, unknown_fields_};
        }

        ::protocyte::Span<const ::protocyte::u8> nested_bytes() const noexcept { return nested_bytes_.view(); }
        ::protocyte::usize nested_bytes_size() const noexcept { return nested_bytes_.size(); }
        static constexpr ::protocyte::usize nested_bytes_max_size() noexcept { return 15u; }
        ::protocyte::Status resize_nested_bytes(const ::protocyte::usize size) noexcept {
            if (size > 15u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, {});
            }
            if (const auto st = nested_bytes_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Status resize_nested_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (const auto st = nested_bytes_.resize_for_overwrite(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_nested_bytes() noexcept { return nested_bytes_.mutable_view(); }
        template<class Value>::protocyte::Status set_nested_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (const auto st = nested_bytes_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_nested_bytes() noexcept { nested_bytes_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<CrossPackageConstants_Nested> parse(Context &ctx, Reader &reader) noexcept {
            auto output = CrossPackageConstants_Nested::create(ctx);
            if (const auto st = parse(ctx, reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        template<typename Reader>
        static ::protocyte::Status parse(Context &ctx, Reader &reader, CrossPackageConstants_Nested &output) noexcept {
            reset_for_reuse_(output, ctx);
            if (const auto st = output.merge_from(reader); !st) {
                reset_for_reuse_(output, ctx);
                return st;
            }
            return {};
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            if (const auto st = merge_partial_from(reader); !st) {
                return st;
            }
            return validate();
        }

        template<typename InputReader>::protocyte::Status merge_partial_from(InputReader &reader) noexcept {
            ::protocyte::ParseBudgetReader<InputReader> budget_reader {
                reader, ctx_->limits.max_total_bytes, ctx_->limits.max_repeated_elements, ctx_->limits.max_map_entries};
            if (const auto st = merge_fields_from(budget_reader); !st) {
                return st;
            }
            if (budget_reader.limit_reached()) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, budget_reader.position());
            }
            return {};
        }

        friend class ::protocyte::MessageParseAccess;

    protected:
        template<typename Reader>::protocyte::Status merge_fields_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::nested_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                                if (const auto st = ::protocyte::read_unknown_field<Config>(
                                        *ctx_, reader, wire_type, field_number, unknown_fields_);
                                    !st) {
                                    return st;
                                }
                            } else {
                                if (const auto st =
                                        ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                                    !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (*len > 15u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<15u> nested_bytes_value {};
                        if (const auto st = nested_bytes_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = nested_bytes_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        nested_bytes_ = ::protocyte::move(nested_bytes_value);
                        break;
                    }
                    default: {
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            if (const auto st = ::protocyte::read_unknown_field<Config>(*ctx_, reader, wire_type,
                                                                                        field_number, unknown_fields_);
                                !st) {
                                return st;
                            }
                        } else {
                            if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                                !st) {
                                return st;
                            }
                        }
                        break;
                    }
                }
            }
            return {};
        }

    public:
        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (!nested_bytes_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested_bytes), nested_bytes_.view());
                    !st) {
                    return st;
                }
            }
            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                const auto unknown_bytes = unknown_fields_.bytes();
                if (!unknown_bytes.empty()) {
                    if (const auto st = writer.write(unknown_bytes.data(), unknown_bytes.size()); !st) {
                        return st;
                    }
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (const auto st = validate(); !st) {
                return ::protocyte::unexpected(st.error());
            }
            ::protocyte::usize total {};
            if (!nested_bytes_.empty()) {
                const auto field_size_nested_bytes = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::nested_bytes), nested_bytes_.size());
                if (!field_size_nested_bytes) {
                    return ::protocyte::unexpected(field_size_nested_bytes.error());
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_nested_bytes);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            const auto total_with_unknown = ::protocyte::checked_add(total, unknown_fields_.size());
            if (!total_with_unknown) {
                return ::protocyte::unexpected(total_with_unknown.error());
            }
            return *total_with_unknown;
        }

        ::protocyte::Status validate() const noexcept { return {}; }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::ByteArray<15u> nested_bytes_;
    };

    template<typename Config> struct CrossPackageConstants {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using Nested = CrossPackageConstants_Nested<NestedConfig>;

        static constexpr ::protocyte::u32 REMOTE_COUNT {16u};
        static constexpr ::protocyte::StringView REMOTE_LABEL {"proto-demo-external", 19u};
        static constexpr bool REMOTE_READY {true};
        static constexpr ::protocyte::u32 NESTED_COUNT {9u};

        enum struct FieldNumber : ::protocyte::u32 {
            remote_bytes = 1u,
            remote_values = 2u,
            nested = 3u,
        };

        explicit CrossPackageConstants(Context &ctx) noexcept:
            ctx_ {&ctx}, unknown_fields_ {&ctx}, remote_values_ {&ctx} {}

        static CrossPackageConstants create(Context &ctx) noexcept { return CrossPackageConstants {ctx}; }
        Context *context() const noexcept { return ctx_; }
        CrossPackageConstants(CrossPackageConstants &&) noexcept = default;
        CrossPackageConstants &operator=(CrossPackageConstants &&) noexcept = default;
        CrossPackageConstants(const CrossPackageConstants &) = delete;
        CrossPackageConstants &operator=(const CrossPackageConstants &) = delete;

        ::protocyte::Status copy_from(const CrossPackageConstants &source) noexcept {
            if (this == &source) {
                return {};
            }
            CrossPackageConstants staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const CrossPackageConstants &source,
                                      CrossPackageConstants &staging_message) noexcept {
            if (this == &source) {
                return {};
            }
            if (this == &staging_message || &source == &staging_message) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {});
            }
            reset_for_reuse_(staging_message, *ctx_);
            if (const auto st = staging_message.copy_from_in_place_(source); !st) {
                reset_for_reuse_(staging_message, *ctx_);
                return st;
            }
            *this = ::protocyte::move(staging_message);
            return {};
        }

        ::protocyte::Result<CrossPackageConstants> clone() const noexcept {
            auto output = CrossPackageConstants::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(CrossPackageConstants &output) const noexcept {
            if (this == &output) {
                return {};
            }
            reset_for_reuse_(output, *ctx_);
            if (const auto st = output.copy_from_in_place_(*this); !st) {
                reset_for_reuse_(output, *ctx_);
                return st;
            }
            return {};
        }

    protected:
        static void reset_for_reuse_(CrossPackageConstants &value, Context &ctx) noexcept {
            value.~CrossPackageConstants();
            new (&value) CrossPackageConstants {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const CrossPackageConstants &source) noexcept {
            if (const auto st = set_remote_bytes(source.remote_bytes()); !st) {
                return st;
            }
            if (const auto st = mutable_remote_values().copy_from(source.remote_values()); !st) {
                return st;
            }
            if (source.has_nested()) {
                const auto ensured_nested = ensure_nested();
                if (!ensured_nested) {
                    return ensured_nested.status();
                }
                if (const auto st = ensured_nested->copy_from(*source.nested()); !st) {
                    return st;
                }
            } else {
                clear_nested();
            }
            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                if (const auto st =
                        unknown_fields_.copy_from(source.unknown_fields_, ctx_->limits.max_unknown_field_bytes);
                    !st) {
                    return st;
                }
            }
            return {};
        }

    public:

        ::protocyte::UnknownFieldRange unknown_fields() const noexcept {
            return ::protocyte::UnknownFieldRange {unknown_fields_.bytes(), ctx_->limits.max_recursion_depth};
        }
        ::protocyte::usize unknown_field_count() const noexcept { return unknown_fields().field_count(); }
        ::protocyte::Span<const ::protocyte::u8> unknown_field_bytes() const noexcept {
            return unknown_fields_.bytes();
        }
        void clear_unknown_fields() noexcept { unknown_fields_.clear(); }
        ::protocyte::MutableUnknownFieldSet<Config> mutable_unknown_fields() noexcept
            requires(::protocyte::preserve_unknown_fields_v<Config>)
        {
            return ::protocyte::MutableUnknownFieldSet<Config> {*ctx_, unknown_fields_};
        }

        ::protocyte::Span<const ::protocyte::u8> remote_bytes() const noexcept { return remote_bytes_.view(); }
        ::protocyte::usize remote_bytes_size() const noexcept { return remote_bytes_.size(); }
        static constexpr ::protocyte::usize remote_bytes_max_size() noexcept { return 9u; }
        ::protocyte::Status resize_remote_bytes(const ::protocyte::usize size) noexcept {
            if (size > 9u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, {});
            }
            if (const auto st = remote_bytes_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Status resize_remote_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (const auto st = remote_bytes_.resize_for_overwrite(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_remote_bytes() noexcept { return remote_bytes_.mutable_view(); }
        template<class Value>::protocyte::Status set_remote_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (const auto st = remote_bytes_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_remote_bytes() noexcept { remote_bytes_.clear(); }

        const ::protocyte::Array<::protocyte::i32, 9u> &remote_values() const noexcept { return remote_values_; }
        ::protocyte::Array<::protocyte::i32, 9u> &mutable_remote_values() noexcept { return remote_values_; }
        void clear_remote_values() noexcept { remote_values_.clear(); }

        bool has_nested() const noexcept { return nested_.has_value(); }
        const ::test::crosspkg::CrossPackageConstants_Nested<Config> *nested() const noexcept {
            return has_nested() ? nested_.operator->() : nullptr;
        }
        ::protocyte::Result<::test::crosspkg::CrossPackageConstants_Nested<Config> &> ensure_nested() noexcept {
            if (nested_.has_value()) {
                return *nested_;
            }
            if (const auto st = nested_.emplace(*ctx_); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return *nested_;
        }
        void clear_nested() noexcept { nested_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<CrossPackageConstants> parse(Context &ctx, Reader &reader) noexcept {
            auto output = CrossPackageConstants::create(ctx);
            if (const auto st = parse(ctx, reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        template<typename Reader>
        static ::protocyte::Status parse(Context &ctx, Reader &reader, CrossPackageConstants &output) noexcept {
            reset_for_reuse_(output, ctx);
            if (const auto st = output.merge_from(reader); !st) {
                reset_for_reuse_(output, ctx);
                return st;
            }
            return {};
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            if (const auto st = merge_partial_from(reader); !st) {
                return st;
            }
            return validate();
        }

        template<typename InputReader>::protocyte::Status merge_partial_from(InputReader &reader) noexcept {
            ::protocyte::ParseBudgetReader<InputReader> budget_reader {
                reader, ctx_->limits.max_total_bytes, ctx_->limits.max_repeated_elements, ctx_->limits.max_map_entries};
            if (const auto st = merge_fields_from(budget_reader); !st) {
                return st;
            }
            if (budget_reader.limit_reached()) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, budget_reader.position());
            }
            return {};
        }

        friend class ::protocyte::MessageParseAccess;

    protected:
        template<typename Reader>::protocyte::Status merge_fields_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::remote_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                                if (const auto st = ::protocyte::read_unknown_field<Config>(
                                        *ctx_, reader, wire_type, field_number, unknown_fields_);
                                    !st) {
                                    return st;
                                }
                            } else {
                                if (const auto st =
                                        ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                                    !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (*len > 9u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<9u> remote_bytes_value {};
                        if (const auto st = remote_bytes_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = remote_bytes_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        remote_bytes_ = ::protocyte::move(remote_bytes_value);
                        break;
                    }
                    case FieldNumber::remote_values: {
                        if (wire_type != ::protocyte::WireType::VARINT && wire_type != ::protocyte::WireType::LEN) {
                            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                                if (const auto st = ::protocyte::read_unknown_field<Config>(
                                        *ctx_, reader, wire_type, field_number, unknown_fields_);
                                    !st) {
                                    return st;
                                }
                            } else {
                                if (const auto st =
                                        ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                                    !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            if (const auto st = reader.can_read(*len); !st) {
                                return st;
                            }
                            ::protocyte::Array<::protocyte::i32, 9u> packed_remote_values_values {};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                if (const auto st = packed.consume_repeated_elements(1u, field_number); !st) {
                                    return st;
                                }
                                ::protocyte::i32 value {};
                                const auto decoded_remote_values = ::protocyte::read_int32(packed);
                                if (!decoded_remote_values) {
                                    return decoded_remote_values.status();
                                }
                                value = *decoded_remote_values;
                                if (const auto st = packed_remote_values_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_remote_values_values_commit_size =
                                ::protocyte::checked_add(remote_values_.size(), packed_remote_values_values.size());
                            if (!packed_remote_values_values_commit_size) {
                                return packed_remote_values_values_commit_size.status();
                            }
                            if (*packed_remote_values_values_commit_size > 9u) {
                                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                               field_number);
                            }
                            for (const auto &value : packed_remote_values_values) {
                                if (const auto st = remote_values_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        if (const auto st = reader.consume_repeated_elements(1u, field_number); !st) {
                            return st;
                        }
                        ::protocyte::i32 value {};
                        {
                            const auto decoded_remote_values =
                                ::protocyte::read_int32_field(reader, wire_type, field_number);
                            if (!decoded_remote_values) {
                                return decoded_remote_values.status();
                            }
                            value = *decoded_remote_values;
                        }
                        if (const auto st = remote_values_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                                if (const auto st = ::protocyte::read_unknown_field<Config>(
                                        *ctx_, reader, wire_type, field_number, unknown_fields_);
                                    !st) {
                                    return st;
                                }
                            } else {
                                if (const auto st =
                                        ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                                    !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::crosspkg::CrossPackageConstants_Nested<Config> nested_value {*ctx_};
                        if (nested_.has_value()) {
                            if (const auto st = nested_value.copy_from(*nested_); !st) {
                                return st;
                            }
                        }
                        if (const auto st =
                                ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number, nested_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = nested_.emplace(::protocyte::move(nested_value)); !st) {
                            return st;
                        }
                        break;
                    }
                    default: {
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            if (const auto st = ::protocyte::read_unknown_field<Config>(*ctx_, reader, wire_type,
                                                                                        field_number, unknown_fields_);
                                !st) {
                                return st;
                            }
                        } else {
                            if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                                !st) {
                                return st;
                            }
                        }
                        break;
                    }
                }
            }
            return {};
        }

    public:
        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (!remote_bytes_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::remote_bytes), remote_bytes_.view());
                    !st) {
                    return st;
                }
            }
            if (!remote_values_.empty()) {
                ::protocyte::usize packed_size_remote_values {};
                for (const auto &packed_value_remote_values : remote_values_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_remote_values,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_remote_values)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    packed_size_remote_values = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::remote_values), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_remote_values));
                    !st) {
                    return st;
                }
                for (const auto &packed_value_remote_values : remote_values_) {
                    if (const auto st = ::protocyte::write_int32(writer, packed_value_remote_values); !st) {
                        return st;
                    }
                }
            }
            if (nested_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested), *nested_);
                    !st) {
                    return st;
                }
            }
            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                const auto unknown_bytes = unknown_fields_.bytes();
                if (!unknown_bytes.empty()) {
                    if (const auto st = writer.write(unknown_bytes.data(), unknown_bytes.size()); !st) {
                        return st;
                    }
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (const auto st = validate(); !st) {
                return ::protocyte::unexpected(st.error());
            }
            ::protocyte::usize total {};
            if (!remote_bytes_.empty()) {
                const auto field_size_remote_bytes = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::remote_bytes), remote_bytes_.size());
                if (!field_size_remote_bytes) {
                    return ::protocyte::unexpected(field_size_remote_bytes.error());
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_remote_bytes);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!remote_values_.empty()) {
                ::protocyte::usize packed_size_remote_values {};
                for (const auto &remote_values_value : remote_values_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_remote_values,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(remote_values_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    packed_size_remote_values = *st_size;
                }
                const auto field_size_remote_values = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::remote_values), packed_size_remote_values);
                if (!field_size_remote_values) {
                    return ::protocyte::unexpected(field_size_remote_values.error());
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_remote_values);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (nested_.has_value()) {
                const auto field_size_nested =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::nested), *nested_);
                if (!field_size_nested) {
                    return ::protocyte::unexpected(field_size_nested.error());
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_nested);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            const auto total_with_unknown = ::protocyte::checked_add(total, unknown_fields_.size());
            if (!total_with_unknown) {
                return ::protocyte::unexpected(total_with_unknown.error());
            }
            return *total_with_unknown;
        }

        ::protocyte::Status validate() const noexcept {
            if (nested_.has_value()) {
                if (const auto st = nested_->validate(); !st) {
                    return st;
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::ByteArray<9u> remote_bytes_;
        ::protocyte::Array<::protocyte::i32, 9u> remote_values_;
        typename Config::template Optional<::test::crosspkg::CrossPackageConstants_Nested<Config>> nested_;
    };

} // namespace test::crosspkg

#endif // PROTOCYTE_GENERATED_CROSS_PACKAGE_PROTO_1F7F3252503C_HPP
