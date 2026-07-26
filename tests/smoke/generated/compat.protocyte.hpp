#pragma once

#ifndef PROTOCYTE_GENERATED_COMPAT_PROTO_ED5E6124729D_HPP
#define PROTOCYTE_GENERATED_COMPAT_PROTO_ED5E6124729D_HPP

#include <protocyte/runtime/runtime.hpp>

#if PROTOCYTE_ENABLE_REFLECTION
#include <array>
#endif

namespace protocyte_smoke::test::compat {

#if PROTOCYTE_ENABLE_REFLECTION
    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> EncodingMatrix_Inner_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 29> EncodingMatrix_fields;
    } // namespace protocyte_reflection
#endif // PROTOCYTE_ENABLE_REFLECTION

    enum struct EncodingMatrix_Mode : ::protocyte::i32 {
        MODE_UNSPECIFIED = 0,
        FIRST = 1,
        SECOND = 2,
    };

    template<typename Config = ::protocyte::DefaultConfig> struct EncodingMatrix_Inner;
    template<typename Config = ::protocyte::DefaultConfig> struct EncodingMatrix;

    template<typename Config> struct EncodingMatrix_Inner {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
            label = 2u,
        };

        explicit EncodingMatrix_Inner(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx}, label_ {&ctx} {}

        static EncodingMatrix_Inner create(Context &ctx) noexcept { return EncodingMatrix_Inner {ctx}; }
        Context *context() const noexcept { return ctx_; }
        EncodingMatrix_Inner(EncodingMatrix_Inner &&) noexcept = default;
        EncodingMatrix_Inner &operator=(EncodingMatrix_Inner &&) noexcept = default;
        EncodingMatrix_Inner(const EncodingMatrix_Inner &) = delete;
        EncodingMatrix_Inner &operator=(const EncodingMatrix_Inner &) = delete;

        ::protocyte::Status copy_from(const EncodingMatrix_Inner &source) noexcept {
            if (this == &source) {
                return {};
            }
            EncodingMatrix_Inner staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const EncodingMatrix_Inner &source,
                                      EncodingMatrix_Inner &staging_message) noexcept {
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

        ::protocyte::Result<EncodingMatrix_Inner> clone() const noexcept {
            auto output = EncodingMatrix_Inner::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(EncodingMatrix_Inner &output) const noexcept {
            if (this == &output) {
                return {};
            }
            Context *const output_ctx = output.context();
            reset_for_reuse_(output, *output_ctx);
            if (const auto st = output.copy_from_in_place_(*this); !st) {
                reset_for_reuse_(output, *output_ctx);
                return st;
            }
            return {};
        }

    protected:
        static void reset_for_reuse_(EncodingMatrix_Inner &value, Context &ctx) noexcept {
            value.~EncodingMatrix_Inner();
            new (&value) EncodingMatrix_Inner {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const EncodingMatrix_Inner &source) noexcept {
            set_value(source.value());
            if (const auto st = set_label(source.label()); !st) {
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

        constexpr ::protocyte::i32 value() const noexcept { return value_; }
        void set_value(const ::protocyte::i32 value) noexcept { value_ = value; }
        constexpr void clear_value() noexcept { value_ = {}; }

        ::protocyte::StringView label() const noexcept { return label_.view(); }
        typename Config::String &mutable_label() noexcept { return label_; }
        template<class Value>::protocyte::Status set_label(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::label));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::label));
            }
            label_ = ::protocyte::move(temp);
            return {};
        }
        template<class Value>::protocyte::Status set_label(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::label));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::label));
            }
            label_ = ::protocyte::move(temp);
            return {};
        }
        void clear_label() noexcept { label_.clear(); }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<EncodingMatrix_Inner> parse(Context &ctx, Reader &reader) noexcept {
            auto output = EncodingMatrix_Inner::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<EncodingMatrix_Inner>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, EncodingMatrix_Inner &output) noexcept {
            Context *const output_ctx = output.context();
            reset_for_reuse_(output, *output_ctx);
            if (const auto st = output.merge_from(reader); !st) {
                reset_for_reuse_(output, *output_ctx);
                return st;
            }
            return {};
        }

        template<::protocyte::ReaderLike Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            ::protocyte::ParseBudgetReader<Reader> budget_reader {
                reader, ctx_->limits.max_total_bytes, ctx_->limits.max_repeated_elements, ctx_->limits.max_map_entries};
            if (const auto st = merge_fields_from(budget_reader); !st) {
                return st;
            }
            if (budget_reader.limit_reached()) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, budget_reader.position());
            }
            return validate();
        }

    private:
        template<typename Reader>::protocyte::Status merge_field_from_(Reader &reader,
                                                                       const ::protocyte::u32 field_number,
                                                                       const ::protocyte::WireType wire_type) noexcept {
            switch (static_cast<FieldNumber>(field_number)) {
                case FieldNumber::value: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_value = ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_value) {
                        return decoded_value.status();
                    }
                    value_ = *decoded_value;
                    break;
                }
                case FieldNumber::label: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (const auto st =
                            ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, label_);
                        !st) {
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
            return {};
        }

    protected:
        friend class ::protocyte::MessageParseAccess;

        template<typename Reader>::protocyte::Status merge_fields_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                if (const auto st = merge_field_from_(reader, field_number, wire_type); !st) {
                    return ::protocyte::with_field(st, field_number);
                }
            }
            return {};
        }

    public:
        template<::protocyte::WriterLike Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (value_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::value), value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::value));
                }
            }
            if (!label_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::label), label_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::label));
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

        ::protocyte::Result<::protocyte::usize>
        serialize(const ::protocyte::Span<::protocyte::u8> output) const noexcept {
            return ::protocyte::serialize(*this, output);
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (const auto st = validate(); !st) {
                return ::protocyte::unexpected(st.error());
            }
            ::protocyte::usize total {};
            if (value_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::value)));
                }
                total = *st_size;
            }
            if (!label_.empty()) {
                const auto field_size_label = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::label), label_.size());
                if (!field_size_label) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_label.error(), static_cast<::protocyte::u32>(FieldNumber::label)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_label);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::label)));
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
            if (const auto st = label_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {}, static_cast<::protocyte::u32>(FieldNumber::label));
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::i32 value_ {};
        typename Config::String label_;
    };

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#elif defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
    /**
     *  Exercises protobuf wire compatibility across every supported field shape.
     */
    template<typename Config> struct EncodingMatrix {
        using Context = typename Config::Context;
        using Mode = EncodingMatrix_Mode;
        template<typename NestedConfig = Config> using Inner = EncodingMatrix_Inner<NestedConfig>;

        enum struct Special_oneofCase : ::protocyte::u32 {
            none = 0u,
            oneof_string = 21u,
            oneof_int32 = 22u,
            oneof_nested = 23u,
            oneof_bytes = 24u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            f_int32 = 1u,
            f_int64 = 2u,
            f_uint32 = 3u,
            f_uint64 = 4u,
            f_sint32 = 5u,
            f_sint64 = 6u,
            f_bool = 7u,
            mode = 8u,
            f_fixed32 = 9u,
            f_fixed64 = 10u,
            f_sfixed32 = 11u,
            f_sfixed64 = 12u,
            f_float = 13u,
            f_double = 14u,
            f_string = 15u,
            f_bytes = 16u,
            nested = 17u,
            r_int32_unpacked = 18u,
            r_int32_packed = 19u,
            r_double = 20u,
            oneof_string = 21u,
            oneof_int32 = 22u,
            oneof_nested = 23u,
            oneof_bytes = 24u,
            opt_int32 = 25u,
            opt_string = 26u,
            map_str_int32 = 27u,
            map_int32_str = 28u,
            /**
             *  Legacy field retained to verify generated deprecation diagnostics.
             */
            deprecated_unused = 29u,
        };

        explicit EncodingMatrix(Context &ctx) noexcept:
            ctx_ {&ctx},
            unknown_fields_ {&ctx},
            f_string_ {&ctx},
            f_bytes_ {&ctx},
            r_int32_unpacked_ {&ctx},
            r_int32_packed_ {&ctx},
            r_double_ {&ctx},
            opt_string_ {&ctx},
            map_str_int32_ {&ctx},
            map_int32_str_ {&ctx},
            deprecated_unused_ {&ctx} {}

        static EncodingMatrix create(Context &ctx) noexcept { return EncodingMatrix {ctx}; }
        Context *context() const noexcept { return ctx_; }
        EncodingMatrix(EncodingMatrix &&other) noexcept:
            ctx_ {other.ctx_},
            unknown_fields_ {::protocyte::move(other.unknown_fields_)},
            f_int32_ {other.f_int32_},
            f_int64_ {other.f_int64_},
            f_uint32_ {other.f_uint32_},
            f_uint64_ {other.f_uint64_},
            f_sint32_ {other.f_sint32_},
            f_sint64_ {other.f_sint64_},
            f_bool_ {other.f_bool_},
            mode_ {other.mode_},
            f_fixed32_ {other.f_fixed32_},
            f_fixed64_ {other.f_fixed64_},
            f_sfixed32_ {other.f_sfixed32_},
            f_sfixed64_ {other.f_sfixed64_},
            f_float_ {other.f_float_},
            f_double_ {other.f_double_},
            f_string_ {::protocyte::move(other.f_string_)},
            f_bytes_ {::protocyte::move(other.f_bytes_)},
            nested_ {::protocyte::move(other.nested_)},
            r_int32_unpacked_ {::protocyte::move(other.r_int32_unpacked_)},
            r_int32_packed_ {::protocyte::move(other.r_int32_packed_)},
            r_double_ {::protocyte::move(other.r_double_)},
            opt_int32_ {other.opt_int32_},
            opt_string_ {::protocyte::move(other.opt_string_)},
            map_str_int32_ {::protocyte::move(other.map_str_int32_)},
            map_int32_str_ {::protocyte::move(other.map_int32_str_)},
            deprecated_unused_ {::protocyte::move(other.deprecated_unused_)} {
            has_opt_int32_ = other.has_opt_int32_;
            has_opt_string_ = other.has_opt_string_;
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    new (&special_oneof_.oneof_string_)
                        typename Config::String {::protocyte::move(other.special_oneof_.oneof_string_)};
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    new (&special_oneof_.oneof_int32_)::protocyte::i32 {other.special_oneof_.oneof_int32_};
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    new (&special_oneof_.oneof_nested_) typename Config::template Optional<
                        ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {
                        ::protocyte::move(other.special_oneof_.oneof_nested_)};
                    special_oneof_case_ = Special_oneofCase::oneof_nested;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof_.oneof_bytes_)
                        typename Config::Bytes {::protocyte::move(other.special_oneof_.oneof_bytes_)};
                    special_oneof_case_ = Special_oneofCase::oneof_bytes;
                    break;
                }
                case Special_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_special_oneof();
        }
        EncodingMatrix &operator=(EncodingMatrix &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_special_oneof();
            ctx_ = other.ctx_;
            unknown_fields_ = ::protocyte::move(other.unknown_fields_);
            f_int32_ = other.f_int32_;
            f_int64_ = other.f_int64_;
            f_uint32_ = other.f_uint32_;
            f_uint64_ = other.f_uint64_;
            f_sint32_ = other.f_sint32_;
            f_sint64_ = other.f_sint64_;
            f_bool_ = other.f_bool_;
            mode_ = other.mode_;
            f_fixed32_ = other.f_fixed32_;
            f_fixed64_ = other.f_fixed64_;
            f_sfixed32_ = other.f_sfixed32_;
            f_sfixed64_ = other.f_sfixed64_;
            f_float_ = other.f_float_;
            f_double_ = other.f_double_;
            f_string_ = ::protocyte::move(other.f_string_);
            f_bytes_ = ::protocyte::move(other.f_bytes_);
            nested_ = ::protocyte::move(other.nested_);
            r_int32_unpacked_ = ::protocyte::move(other.r_int32_unpacked_);
            r_int32_packed_ = ::protocyte::move(other.r_int32_packed_);
            r_double_ = ::protocyte::move(other.r_double_);
            opt_int32_ = other.opt_int32_;
            has_opt_int32_ = other.has_opt_int32_;
            opt_string_ = ::protocyte::move(other.opt_string_);
            has_opt_string_ = other.has_opt_string_;
            map_str_int32_ = ::protocyte::move(other.map_str_int32_);
            map_int32_str_ = ::protocyte::move(other.map_int32_str_);
            deprecated_unused_ = ::protocyte::move(other.deprecated_unused_);
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    new (&special_oneof_.oneof_string_)
                        typename Config::String {::protocyte::move(other.special_oneof_.oneof_string_)};
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    new (&special_oneof_.oneof_int32_)::protocyte::i32 {other.special_oneof_.oneof_int32_};
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    new (&special_oneof_.oneof_nested_) typename Config::template Optional<
                        ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {
                        ::protocyte::move(other.special_oneof_.oneof_nested_)};
                    special_oneof_case_ = Special_oneofCase::oneof_nested;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof_.oneof_bytes_)
                        typename Config::Bytes {::protocyte::move(other.special_oneof_.oneof_bytes_)};
                    special_oneof_case_ = Special_oneofCase::oneof_bytes;
                    break;
                }
                case Special_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_special_oneof();
            return *this;
        }
        ~EncodingMatrix() noexcept { clear_special_oneof(); }
        EncodingMatrix(const EncodingMatrix &) = delete;
        EncodingMatrix &operator=(const EncodingMatrix &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const EncodingMatrix &source) noexcept {
            if (this == &source) {
                return {};
            }
            EncodingMatrix staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const EncodingMatrix &source, EncodingMatrix &staging_message) noexcept {
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

        ::protocyte::Result<EncodingMatrix> clone() const noexcept {
            auto output = EncodingMatrix::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(EncodingMatrix &output) const noexcept {
            if (this == &output) {
                return {};
            }
            Context *const output_ctx = output.context();
            reset_for_reuse_(output, *output_ctx);
            if (const auto st = output.copy_from_in_place_(*this); !st) {
                reset_for_reuse_(output, *output_ctx);
                return st;
            }
            return {};
        }

    protected:
        static void reset_for_reuse_(EncodingMatrix &value, Context &ctx) noexcept {
            value.~EncodingMatrix();
            new (&value) EncodingMatrix {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const EncodingMatrix &source) noexcept {
            set_f_int32(source.f_int32());
            set_f_int64(source.f_int64());
            set_f_uint32(source.f_uint32());
            set_f_uint64(source.f_uint64());
            set_f_sint32(source.f_sint32());
            set_f_sint64(source.f_sint64());
            set_f_bool(source.f_bool());
            if (const auto st = set_mode_raw(source.mode_raw()); !st) {
                return st;
            }
            set_f_fixed32(source.f_fixed32());
            set_f_fixed64(source.f_fixed64());
            set_f_sfixed32(source.f_sfixed32());
            set_f_sfixed64(source.f_sfixed64());
            set_f_float(source.f_float());
            set_f_double(source.f_double());
            if (const auto st = set_f_string(source.f_string()); !st) {
                return st;
            }
            if (const auto st = set_f_bytes(source.f_bytes()); !st) {
                return st;
            }
            if (source.has_nested()) {
                const auto ensured_nested = ensure_nested();
                if (!ensured_nested) {
                    return ::protocyte::with_field(ensured_nested.status(),
                                                   static_cast<::protocyte::u32>(FieldNumber::nested));
                }
                if (const auto st = ensured_nested->copy_from(*source.nested()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::nested));
                }
            } else {
                clear_nested();
            }
            if (const auto st = mutable_r_int32_unpacked().copy_from(source.r_int32_unpacked()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked));
            }
            if (const auto st = mutable_r_int32_packed().copy_from(source.r_int32_packed()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed));
            }
            if (const auto st = mutable_r_double().copy_from(source.r_double()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_double));
            }
            if (source.has_opt_int32()) {
                set_opt_int32(source.opt_int32());
            } else {
                clear_opt_int32();
            }
            if (source.has_opt_string()) {
                if (const auto st = set_opt_string(source.opt_string()); !st) {
                    return st;
                }
            } else {
                clear_opt_string();
            }
            if (const auto st = mutable_map_str_int32().copy_from(source.map_str_int32()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
            }
            if (const auto st = mutable_map_int32_str().copy_from(source.map_int32_str()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
            }
            if (const auto st = set_deprecated_unused(source.deprecated_unused()); !st) {
                return st;
            }
            switch (source.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    if (const auto st = set_oneof_string(source.oneof_string()); !st) {
                        return st;
                    }
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    set_oneof_int32(source.oneof_int32());
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    const auto ensured_oneof_nested = ensure_oneof_nested();
                    if (!ensured_oneof_nested) {
                        return ::protocyte::with_field(ensured_oneof_nested.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::oneof_nested));
                    }
                    if (const auto st = ensured_oneof_nested->copy_from(*source.oneof_nested()); !st) {
                        return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_nested));
                    }
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    if (const auto st = set_oneof_bytes(source.oneof_bytes()); !st) {
                        return st;
                    }
                    break;
                }
                case Special_oneofCase::none:
                default: {
                    clear_special_oneof();
                    break;
                }
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

        constexpr Special_oneofCase special_oneof_case() const noexcept { return special_oneof_case_; }
        void clear_special_oneof() noexcept {
            switch (special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    destroy_at_(&special_oneof_.oneof_string_);
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    destroy_at_(&special_oneof_.oneof_nested_);
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    destroy_at_(&special_oneof_.oneof_bytes_);
                    break;
                }
                case Special_oneofCase::none:
                default: {
                    break;
                }
            }
            special_oneof_case_ = Special_oneofCase::none;
        }

        constexpr ::protocyte::i32 f_int32() const noexcept { return f_int32_; }
        void set_f_int32(const ::protocyte::i32 value) noexcept { f_int32_ = value; }
        constexpr void clear_f_int32() noexcept { f_int32_ = {}; }

        constexpr ::protocyte::i64 f_int64() const noexcept { return f_int64_; }
        void set_f_int64(const ::protocyte::i64 value) noexcept { f_int64_ = value; }
        constexpr void clear_f_int64() noexcept { f_int64_ = {}; }

        constexpr ::protocyte::u32 f_uint32() const noexcept { return f_uint32_; }
        void set_f_uint32(const ::protocyte::u32 value) noexcept { f_uint32_ = value; }
        constexpr void clear_f_uint32() noexcept { f_uint32_ = {}; }

        constexpr ::protocyte::u64 f_uint64() const noexcept { return f_uint64_; }
        void set_f_uint64(const ::protocyte::u64 value) noexcept { f_uint64_ = value; }
        constexpr void clear_f_uint64() noexcept { f_uint64_ = {}; }

        constexpr ::protocyte::i32 f_sint32() const noexcept { return f_sint32_; }
        void set_f_sint32(const ::protocyte::i32 value) noexcept { f_sint32_ = value; }
        constexpr void clear_f_sint32() noexcept { f_sint32_ = {}; }

        constexpr ::protocyte::i64 f_sint64() const noexcept { return f_sint64_; }
        void set_f_sint64(const ::protocyte::i64 value) noexcept { f_sint64_ = value; }
        constexpr void clear_f_sint64() noexcept { f_sint64_ = {}; }

        constexpr bool f_bool() const noexcept { return f_bool_; }
        void set_f_bool(const bool value) noexcept { f_bool_ = value; }
        constexpr void clear_f_bool() noexcept { f_bool_ = {}; }

        constexpr ::protocyte::i32 mode_raw() const noexcept { return mode_; }
        constexpr ::protocyte_smoke::test::compat::EncodingMatrix_Mode mode() const noexcept {
            return static_cast<::protocyte_smoke::test::compat::EncodingMatrix_Mode>(mode_);
        }
        ::protocyte::Status set_mode_raw(const ::protocyte::i32 value) noexcept {
            mode_ = value;
            return {};
        }
        ::protocyte::Status set_mode(const ::protocyte_smoke::test::compat::EncodingMatrix_Mode value) noexcept {
            return set_mode_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_mode() noexcept { mode_ = {}; }

        constexpr ::protocyte::u32 f_fixed32() const noexcept { return f_fixed32_; }
        void set_f_fixed32(const ::protocyte::u32 value) noexcept { f_fixed32_ = value; }
        constexpr void clear_f_fixed32() noexcept { f_fixed32_ = {}; }

        constexpr ::protocyte::u64 f_fixed64() const noexcept { return f_fixed64_; }
        void set_f_fixed64(const ::protocyte::u64 value) noexcept { f_fixed64_ = value; }
        constexpr void clear_f_fixed64() noexcept { f_fixed64_ = {}; }

        constexpr ::protocyte::i32 f_sfixed32() const noexcept { return f_sfixed32_; }
        void set_f_sfixed32(const ::protocyte::i32 value) noexcept { f_sfixed32_ = value; }
        constexpr void clear_f_sfixed32() noexcept { f_sfixed32_ = {}; }

        constexpr ::protocyte::i64 f_sfixed64() const noexcept { return f_sfixed64_; }
        void set_f_sfixed64(const ::protocyte::i64 value) noexcept { f_sfixed64_ = value; }
        constexpr void clear_f_sfixed64() noexcept { f_sfixed64_ = {}; }

        constexpr ::protocyte::f32 f_float() const noexcept { return f_float_; }
        void set_f_float(const ::protocyte::f32 value) noexcept { f_float_ = value; }
        constexpr void clear_f_float() noexcept { f_float_ = {}; }

        constexpr ::protocyte::f64 f_double() const noexcept { return f_double_; }
        void set_f_double(const ::protocyte::f64 value) noexcept { f_double_ = value; }
        constexpr void clear_f_double() noexcept { f_double_ = {}; }

        ::protocyte::StringView f_string() const noexcept { return f_string_.view(); }
        typename Config::String &mutable_f_string() noexcept { return f_string_; }
        template<class Value>::protocyte::Status set_f_string(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::f_string));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_string));
            }
            f_string_ = ::protocyte::move(temp);
            return {};
        }
        template<class Value>::protocyte::Status set_f_string(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::f_string));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_string));
            }
            f_string_ = ::protocyte::move(temp);
            return {};
        }
        void clear_f_string() noexcept { f_string_.clear(); }

        ::protocyte::Span<const ::protocyte::u8> f_bytes() const noexcept { return f_bytes_.view(); }
        typename Config::Bytes &mutable_f_bytes() noexcept { return f_bytes_; }
        template<class Value>::protocyte::Status set_f_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::f_bytes));
            }
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_bytes));
            }
            f_bytes_ = ::protocyte::move(temp);
            return {};
        }
        void clear_f_bytes() noexcept { f_bytes_.clear(); }

        bool has_nested() const noexcept { return nested_.has_value(); }
        const ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> *nested() const noexcept {
            return has_nested() ? nested_.operator->() : nullptr;
        }
        ::protocyte::Result<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> &> ensure_nested() noexcept {
            if (nested_.has_value()) {
                return *nested_;
            }
            if (const auto st = nested_.emplace(*ctx_); !st) {
                return ::protocyte::unexpected(
                    ::protocyte::with_field(st.error(), static_cast<::protocyte::u32>(FieldNumber::nested)));
            }
            return *nested_;
        }
        void clear_nested() noexcept { nested_.reset(); }

        const typename Config::template Vector<::protocyte::i32> &r_int32_unpacked() const noexcept {
            return r_int32_unpacked_;
        }
        typename Config::template Vector<::protocyte::i32> &mutable_r_int32_unpacked() noexcept {
            return r_int32_unpacked_;
        }
        void clear_r_int32_unpacked() noexcept { r_int32_unpacked_.clear(); }

        const typename Config::template Vector<::protocyte::i32> &r_int32_packed() const noexcept {
            return r_int32_packed_;
        }
        typename Config::template Vector<::protocyte::i32> &mutable_r_int32_packed() noexcept {
            return r_int32_packed_;
        }
        void clear_r_int32_packed() noexcept { r_int32_packed_.clear(); }

        const typename Config::template Vector<::protocyte::f64> &r_double() const noexcept { return r_double_; }
        typename Config::template Vector<::protocyte::f64> &mutable_r_double() noexcept { return r_double_; }
        void clear_r_double() noexcept { r_double_.clear(); }

        constexpr bool has_oneof_string() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_string;
        }
        ::protocyte::StringView oneof_string() const noexcept {
            return has_oneof_string() ? special_oneof_.oneof_string_.view() : ::protocyte::StringView {};
        }
        template<class Value>::protocyte::Status set_oneof_string(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::oneof_string));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_string));
            }
            clear_special_oneof();
            new (&special_oneof_.oneof_string_) typename Config::String {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_string;
            return {};
        }
        template<class Value>::protocyte::Status set_oneof_string(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::oneof_string));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_string));
            }
            clear_special_oneof();
            new (&special_oneof_.oneof_string_) typename Config::String {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_string;
            return {};
        }

        constexpr bool has_oneof_int32() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_int32;
        }
        constexpr ::protocyte::i32 oneof_int32() const noexcept {
            return has_oneof_int32() ? special_oneof_.oneof_int32_ : 0;
        }
        void set_oneof_int32(const ::protocyte::i32 value) noexcept {
            clear_special_oneof();
            new (&special_oneof_.oneof_int32_)::protocyte::i32 {value};
            special_oneof_case_ = Special_oneofCase::oneof_int32;
        }

        constexpr bool has_oneof_nested() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_nested;
        }
        const ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> *oneof_nested() const noexcept {
            return has_oneof_nested() && special_oneof_.oneof_nested_.has_value() ?
                       special_oneof_.oneof_nested_.operator->() :
                       nullptr;
        }
        ::protocyte::Result<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> &>
        ensure_oneof_nested() noexcept {
            if (!has_oneof_nested()) {
                clear_special_oneof();
                new (&special_oneof_.oneof_nested_) typename Config::template Optional<
                    ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {};
            }
            special_oneof_case_ = Special_oneofCase::oneof_nested;
            if (special_oneof_.oneof_nested_.has_value()) {
                return *special_oneof_.oneof_nested_;
            }
            if (const auto st = special_oneof_.oneof_nested_.emplace(*ctx_); !st) {
                return ::protocyte::unexpected(
                    ::protocyte::with_field(st.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_nested)));
            }
            return *special_oneof_.oneof_nested_;
        }

        constexpr bool has_oneof_bytes() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_bytes;
        }
        ::protocyte::Span<const ::protocyte::u8> oneof_bytes() const noexcept {
            return has_oneof_bytes() ? special_oneof_.oneof_bytes_.view() : ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_oneof_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::oneof_bytes));
            }
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_bytes));
            }
            clear_special_oneof();
            new (&special_oneof_.oneof_bytes_) typename Config::Bytes {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_bytes;
            return {};
        }

        constexpr ::protocyte::i32 opt_int32() const noexcept { return opt_int32_; }
        constexpr bool has_opt_int32() const noexcept { return has_opt_int32_; }
        void set_opt_int32(const ::protocyte::i32 value) noexcept {
            opt_int32_ = value;
            has_opt_int32_ = true;
        }
        constexpr void clear_opt_int32() noexcept {
            opt_int32_ = {};
            has_opt_int32_ = false;
        }

        ::protocyte::StringView opt_string() const noexcept { return opt_string_.view(); }
        bool has_opt_string() const noexcept { return has_opt_string_; }
        typename Config::String &mutable_opt_string() noexcept {
            has_opt_string_ = true;
            return opt_string_;
        }
        template<class Value>::protocyte::Status set_opt_string(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::opt_string));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::opt_string));
            }
            opt_string_ = ::protocyte::move(temp);
            has_opt_string_ = true;
            return {};
        }
        template<class Value>::protocyte::Status set_opt_string(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::opt_string));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::opt_string));
            }
            opt_string_ = ::protocyte::move(temp);
            has_opt_string_ = true;
            return {};
        }
        void clear_opt_string() noexcept {
            opt_string_.clear();
            has_opt_string_ = false;
        }

        const typename Config::template Map<typename Config::String, ::protocyte::i32> &map_str_int32() const noexcept {
            return map_str_int32_;
        }
        typename Config::template Map<typename Config::String, ::protocyte::i32> &mutable_map_str_int32() noexcept {
            return map_str_int32_;
        }
        void clear_map_str_int32() noexcept { map_str_int32_.clear(); }

        const typename Config::template Map<::protocyte::i32, typename Config::String> &map_int32_str() const noexcept {
            return map_int32_str_;
        }
        typename Config::template Map<::protocyte::i32, typename Config::String> &mutable_map_int32_str() noexcept {
            return map_int32_str_;
        }
        void clear_map_int32_str() noexcept { map_int32_str_.clear(); }

        /**
         *  Legacy field retained to verify generated deprecation diagnostics.
         */
        [[deprecated]]
        ::protocyte::StringView deprecated_unused() const noexcept {
            return deprecated_unused_.view();
        }
        /**
         *  Legacy field retained to verify generated deprecation diagnostics.
         */
        [[deprecated]]
        typename Config::String &mutable_deprecated_unused() noexcept {
            return deprecated_unused_;
        }
        /**
         *  Legacy field retained to verify generated deprecation diagnostics.
         */
        template<class Value> [[deprecated]]
        ::protocyte::Status set_deprecated_unused(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(),
                                               static_cast<::protocyte::u32>(FieldNumber::deprecated_unused));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::deprecated_unused));
            }
            deprecated_unused_ = ::protocyte::move(temp);
            return {};
        }
        /**
         *  Legacy field retained to verify generated deprecation diagnostics.
         */
        template<class Value> [[deprecated]]
        ::protocyte::Status set_deprecated_unused(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(),
                                               static_cast<::protocyte::u32>(FieldNumber::deprecated_unused));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::deprecated_unused));
            }
            deprecated_unused_ = ::protocyte::move(temp);
            return {};
        }
        /**
         *  Legacy field retained to verify generated deprecation diagnostics.
         */
        [[deprecated]]
        void clear_deprecated_unused() noexcept {
            deprecated_unused_.clear();
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<EncodingMatrix> parse(Context &ctx, Reader &reader) noexcept {
            auto output = EncodingMatrix::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<EncodingMatrix> parse(Context &ctx,
                                                         ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, EncodingMatrix &output) noexcept {
            Context *const output_ctx = output.context();
            reset_for_reuse_(output, *output_ctx);
            if (const auto st = output.merge_from(reader); !st) {
                reset_for_reuse_(output, *output_ctx);
                return st;
            }
            return {};
        }

        template<::protocyte::ReaderLike Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            ::protocyte::ParseBudgetReader<Reader> budget_reader {
                reader, ctx_->limits.max_total_bytes, ctx_->limits.max_repeated_elements, ctx_->limits.max_map_entries};
            if (const auto st = merge_fields_from(budget_reader); !st) {
                return st;
            }
            if (budget_reader.limit_reached()) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, budget_reader.position());
            }
            return validate();
        }

    private:
        template<typename Reader>::protocyte::Status merge_field_from_(Reader &reader,
                                                                       const ::protocyte::u32 field_number,
                                                                       const ::protocyte::WireType wire_type) noexcept {
            switch (static_cast<FieldNumber>(field_number)) {
                case FieldNumber::f_int32: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_int32 = ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_f_int32) {
                        return decoded_f_int32.status();
                    }
                    f_int32_ = *decoded_f_int32;
                    break;
                }
                case FieldNumber::f_int64: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_int64 = ::protocyte::read_int64_field(reader, wire_type, field_number);
                    if (!decoded_f_int64) {
                        return decoded_f_int64.status();
                    }
                    f_int64_ = *decoded_f_int64;
                    break;
                }
                case FieldNumber::f_uint32: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_uint32 = ::protocyte::read_uint32_field(reader, wire_type, field_number);
                    if (!decoded_f_uint32) {
                        return decoded_f_uint32.status();
                    }
                    f_uint32_ = *decoded_f_uint32;
                    break;
                }
                case FieldNumber::f_uint64: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_uint64 = ::protocyte::read_uint64_field(reader, wire_type, field_number);
                    if (!decoded_f_uint64) {
                        return decoded_f_uint64.status();
                    }
                    f_uint64_ = *decoded_f_uint64;
                    break;
                }
                case FieldNumber::f_sint32: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_sint32 = ::protocyte::read_sint32_field(reader, wire_type, field_number);
                    if (!decoded_f_sint32) {
                        return decoded_f_sint32.status();
                    }
                    f_sint32_ = *decoded_f_sint32;
                    break;
                }
                case FieldNumber::f_sint64: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_sint64 = ::protocyte::read_sint64_field(reader, wire_type, field_number);
                    if (!decoded_f_sint64) {
                        return decoded_f_sint64.status();
                    }
                    f_sint64_ = *decoded_f_sint64;
                    break;
                }
                case FieldNumber::f_bool: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_f_bool = ::protocyte::read_bool_field(reader, wire_type, field_number);
                    if (!decoded_f_bool) {
                        return decoded_f_bool.status();
                    }
                    f_bool_ = *decoded_f_bool;
                    break;
                }
                case FieldNumber::mode: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_mode = ::protocyte::read_enum_field(reader, wire_type, field_number);
                    if (!decoded_mode) {
                        return decoded_mode.status();
                    }
                    mode_ = *decoded_mode;
                    break;
                }
                case FieldNumber::f_fixed32: {
                    if (wire_type != ::protocyte::WireType::I32) {
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
                    const auto decoded_f_fixed32 =
                        ::protocyte::read_fixed32_value_field(reader, wire_type, field_number);
                    if (!decoded_f_fixed32) {
                        return decoded_f_fixed32.status();
                    }
                    f_fixed32_ = *decoded_f_fixed32;
                    break;
                }
                case FieldNumber::f_fixed64: {
                    if (wire_type != ::protocyte::WireType::I64) {
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
                    const auto decoded_f_fixed64 =
                        ::protocyte::read_fixed64_value_field(reader, wire_type, field_number);
                    if (!decoded_f_fixed64) {
                        return decoded_f_fixed64.status();
                    }
                    f_fixed64_ = *decoded_f_fixed64;
                    break;
                }
                case FieldNumber::f_sfixed32: {
                    if (wire_type != ::protocyte::WireType::I32) {
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
                    const auto decoded_f_sfixed32 = ::protocyte::read_sfixed32_field(reader, wire_type, field_number);
                    if (!decoded_f_sfixed32) {
                        return decoded_f_sfixed32.status();
                    }
                    f_sfixed32_ = *decoded_f_sfixed32;
                    break;
                }
                case FieldNumber::f_sfixed64: {
                    if (wire_type != ::protocyte::WireType::I64) {
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
                    const auto decoded_f_sfixed64 = ::protocyte::read_sfixed64_field(reader, wire_type, field_number);
                    if (!decoded_f_sfixed64) {
                        return decoded_f_sfixed64.status();
                    }
                    f_sfixed64_ = *decoded_f_sfixed64;
                    break;
                }
                case FieldNumber::f_float: {
                    if (wire_type != ::protocyte::WireType::I32) {
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
                    const auto decoded_f_float = ::protocyte::read_float_field(reader, wire_type, field_number);
                    if (!decoded_f_float) {
                        return decoded_f_float.status();
                    }
                    f_float_ = *decoded_f_float;
                    break;
                }
                case FieldNumber::f_double: {
                    if (wire_type != ::protocyte::WireType::I64) {
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
                    const auto decoded_f_double = ::protocyte::read_double_field(reader, wire_type, field_number);
                    if (!decoded_f_double) {
                        return decoded_f_double.status();
                    }
                    f_double_ = *decoded_f_double;
                    break;
                }
                case FieldNumber::f_string: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (const auto st =
                            ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, f_string_);
                        !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::f_bytes: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (const auto st =
                            ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type, field_number, f_bytes_);
                        !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::nested: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type != ::protocyte::WireType::LEN) {
                        return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                       field_number);
                    }
                    ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> nested_value {*ctx_};
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
                case FieldNumber::r_int32_unpacked: {
                    if (wire_type != ::protocyte::WireType::VARINT && wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type == ::protocyte::WireType::LEN) {
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        typename Config::template Vector<::protocyte::i32> packed_r_int32_unpacked_values {ctx_};
                        ::protocyte::LimitedReader<Reader> packed {reader, *len};
                        while (!packed.eof()) {
                            if (const auto st = packed.consume_repeated_elements(1u, field_number); !st) {
                                return st;
                            }
                            ::protocyte::i32 value {};
                            const auto decoded_r_int32_unpacked = ::protocyte::read_int32(packed);
                            if (!decoded_r_int32_unpacked) {
                                return decoded_r_int32_unpacked.status();
                            }
                            value = *decoded_r_int32_unpacked;
                            if (const auto st = packed_r_int32_unpacked_values.push_back(value); !st) {
                                return st;
                            }
                        }
                        if (const auto st = r_int32_unpacked_.append_trivial_range(
                                packed_r_int32_unpacked_values.data(), packed_r_int32_unpacked_values.size());
                            !st) {
                            return st;
                        }
                        break;
                    }
                    if (const auto st = reader.consume_repeated_elements(1u, field_number); !st) {
                        return st;
                    }
                    ::protocyte::i32 value {};
                    {
                        const auto decoded_r_int32_unpacked =
                            ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded_r_int32_unpacked) {
                            return decoded_r_int32_unpacked.status();
                        }
                        value = *decoded_r_int32_unpacked;
                    }
                    if (const auto st = r_int32_unpacked_.push_back(value); !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::r_int32_packed: {
                    if (wire_type != ::protocyte::WireType::VARINT && wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type == ::protocyte::WireType::LEN) {
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        typename Config::template Vector<::protocyte::i32> packed_r_int32_packed_values {ctx_};
                        ::protocyte::LimitedReader<Reader> packed {reader, *len};
                        while (!packed.eof()) {
                            if (const auto st = packed.consume_repeated_elements(1u, field_number); !st) {
                                return st;
                            }
                            ::protocyte::i32 value {};
                            const auto decoded_r_int32_packed = ::protocyte::read_int32(packed);
                            if (!decoded_r_int32_packed) {
                                return decoded_r_int32_packed.status();
                            }
                            value = *decoded_r_int32_packed;
                            if (const auto st = packed_r_int32_packed_values.push_back(value); !st) {
                                return st;
                            }
                        }
                        if (const auto st = r_int32_packed_.append_trivial_range(packed_r_int32_packed_values.data(),
                                                                                 packed_r_int32_packed_values.size());
                            !st) {
                            return st;
                        }
                        break;
                    }
                    if (const auto st = reader.consume_repeated_elements(1u, field_number); !st) {
                        return st;
                    }
                    ::protocyte::i32 value {};
                    {
                        const auto decoded_r_int32_packed =
                            ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded_r_int32_packed) {
                            return decoded_r_int32_packed.status();
                        }
                        value = *decoded_r_int32_packed;
                    }
                    if (const auto st = r_int32_packed_.push_back(value); !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::r_double: {
                    if (wire_type != ::protocyte::WireType::I64 && wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type == ::protocyte::WireType::LEN) {
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st =
                                ::protocyte::read_fixed_width_packed_values(reader, *len, field_number, r_double_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    if (const auto st = reader.consume_repeated_elements(1u, field_number); !st) {
                        return st;
                    }
                    ::protocyte::f64 value {};
                    const auto decoded_r_double = ::protocyte::read_double_field(reader, wire_type, field_number);
                    if (!decoded_r_double) {
                        return decoded_r_double.status();
                    }
                    value = *decoded_r_double;
                    if (const auto st = r_double_.push_back(value); !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::oneof_string: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    typename Config::String oneof_string_value {ctx_};
                    if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number,
                                                                               oneof_string_value);
                        !st) {
                        return st;
                    }
                    clear_special_oneof();
                    new (&special_oneof_.oneof_string_) typename Config::String {::protocyte::move(oneof_string_value)};
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case FieldNumber::oneof_int32: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    ::protocyte::i32 oneof_int32_value {};
                    const auto decoded_oneof_int32 = ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_oneof_int32) {
                        return decoded_oneof_int32.status();
                    }
                    oneof_int32_value = *decoded_oneof_int32;
                    clear_special_oneof();
                    new (&special_oneof_.oneof_int32_)::protocyte::i32 {::protocyte::move(oneof_int32_value)};
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case FieldNumber::oneof_nested: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type != ::protocyte::WireType::LEN) {
                        return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                       field_number);
                    }
                    ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> oneof_nested_value {*ctx_};
                    if (has_oneof_nested() && special_oneof_.oneof_nested_.has_value()) {
                        if (const auto st = oneof_nested_value.copy_from(*special_oneof_.oneof_nested_); !st) {
                            return st;
                        }
                    }
                    if (const auto st =
                            ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number, oneof_nested_value);
                        !st) {
                        return st;
                    }
                    typename Config::template Optional<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>
                        oneof_nested_committed {};
                    if (const auto st = oneof_nested_committed.emplace(::protocyte::move(oneof_nested_value)); !st) {
                        return st;
                    }
                    clear_special_oneof();
                    new (&special_oneof_.oneof_nested_) typename Config::template Optional<
                        ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {
                        ::protocyte::move(oneof_nested_committed)};
                    special_oneof_case_ = Special_oneofCase::oneof_nested;
                    break;
                }
                case FieldNumber::oneof_bytes: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    typename Config::Bytes oneof_bytes_value {ctx_};
                    if (const auto st = ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type, field_number,
                                                                              oneof_bytes_value);
                        !st) {
                        return st;
                    }
                    clear_special_oneof();
                    new (&special_oneof_.oneof_bytes_) typename Config::Bytes {::protocyte::move(oneof_bytes_value)};
                    special_oneof_case_ = Special_oneofCase::oneof_bytes;
                    break;
                }
                case FieldNumber::opt_int32: {
                    if (wire_type != ::protocyte::WireType::VARINT) {
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
                    const auto decoded_opt_int32 = ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_opt_int32) {
                        return decoded_opt_int32.status();
                    }
                    opt_int32_ = *decoded_opt_int32;
                    has_opt_int32_ = true;
                    break;
                }
                case FieldNumber::opt_string: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (const auto st =
                            ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, opt_string_);
                        !st) {
                        return st;
                    }
                    has_opt_string_ = true;
                    break;
                }
                case FieldNumber::map_str_int32: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type != ::protocyte::WireType::LEN) {
                        return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                       field_number);
                    }
                    if (const auto st = reader.consume_map_entries(1u, field_number); !st) {
                        return st;
                    }
                    typename Config::String key {ctx_};
                    ::protocyte::i32 value {};
                    bool entry_is_unknown {};
                    const auto parse_map_str_int32_entry = [&](auto &entry_reader) noexcept -> ::protocyte::Status {
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, entry_reader,
                                                                                            entry_wire, entry_field);
                                            !st) {
                                            return st;
                                        }
                                        break;
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(*ctx_, entry_reader, key);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, entry_reader,
                                                                                            entry_wire, entry_field);
                                            !st) {
                                            return st;
                                        }
                                        break;
                                    }
                                    {
                                        const auto decoded_value = ::protocyte::read_int32(entry_reader);
                                        if (!decoded_value) {
                                            return decoded_value.status();
                                        }
                                        value = *decoded_value;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field<Config>(*ctx_, entry_reader, entry_wire,
                                                                                        entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        return {};
                    };
                    auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                    if (!entry) {
                        return entry.status();
                    }
                    auto &entry_reader = entry->reader();
                    if (const auto st = parse_map_str_int32_entry(entry_reader); !st) {
                        return st;
                    }
                    if (const auto st = entry->finish(); !st) {
                        return st;
                    }
                    if (!entry_is_unknown) {
                        if (const auto insert =
                                map_str_int32_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                    }
                    break;
                }
                case FieldNumber::map_int32_str: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (wire_type != ::protocyte::WireType::LEN) {
                        return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                       field_number);
                    }
                    if (const auto st = reader.consume_map_entries(1u, field_number); !st) {
                        return st;
                    }
                    ::protocyte::i32 key {};
                    typename Config::String value {ctx_};
                    bool entry_is_unknown {};
                    const auto parse_map_int32_str_entry = [&](auto &entry_reader) noexcept -> ::protocyte::Status {
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, entry_reader,
                                                                                            entry_wire, entry_field);
                                            !st) {
                                            return st;
                                        }
                                        break;
                                    }
                                    const auto decoded_key = ::protocyte::read_int32(entry_reader);
                                    if (!decoded_key) {
                                        return decoded_key.status();
                                    }
                                    key = *decoded_key;
                                    break;
                                }
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, entry_reader,
                                                                                            entry_wire, entry_field);
                                            !st) {
                                            return st;
                                        }
                                        break;
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(*ctx_, entry_reader, value);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field<Config>(*ctx_, entry_reader, entry_wire,
                                                                                        entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        return {};
                    };
                    auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                    if (!entry) {
                        return entry.status();
                    }
                    auto &entry_reader = entry->reader();
                    if (const auto st = parse_map_int32_str_entry(entry_reader); !st) {
                        return st;
                    }
                    if (const auto st = entry->finish(); !st) {
                        return st;
                    }
                    if (!entry_is_unknown) {
                        if (const auto insert =
                                map_int32_str_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                    }
                    break;
                }
                case FieldNumber::deprecated_unused: {
                    if (wire_type != ::protocyte::WireType::LEN) {
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
                    if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number,
                                                                               deprecated_unused_);
                        !st) {
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
            return {};
        }

    protected:
        friend class ::protocyte::MessageParseAccess;

        template<typename Reader>::protocyte::Status merge_fields_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                if (const auto st = merge_field_from_(reader, field_number, wire_type); !st) {
                    return ::protocyte::with_field(st, field_number);
                }
            }
            return {};
        }

    public:
        template<::protocyte::WriterLike Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (f_int32_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_int32), f_int32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_int32));
                }
            }
            if (f_int64_ != 0) {
                if (const auto st = ::protocyte::write_int64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_int64), f_int64_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_int64));
                }
            }
            if (f_uint32_ != 0u) {
                if (const auto st = ::protocyte::write_uint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_uint32), f_uint32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_uint32));
                }
            }
            if (f_uint64_ != 0u) {
                if (const auto st = ::protocyte::write_uint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_uint64), f_uint64_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_uint64));
                }
            }
            if (f_sint32_ != 0) {
                if (const auto st = ::protocyte::write_sint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sint32), f_sint32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_sint32));
                }
            }
            if (f_sint64_ != 0) {
                if (const auto st = ::protocyte::write_sint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sint64), f_sint64_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_sint64));
                }
            }
            if (f_bool_) {
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_bool), f_bool_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_bool));
                }
            }
            if (mode_ != 0) {
                if (const auto st =
                        ::protocyte::write_enum_field(writer, static_cast<::protocyte::u32>(FieldNumber::mode), mode_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::mode));
                }
            }
            if (f_fixed32_ != 0u) {
                if (const auto st = ::protocyte::write_fixed32_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_fixed32), f_fixed32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_fixed32));
                }
            }
            if (f_fixed64_ != 0u) {
                if (const auto st = ::protocyte::write_fixed64_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_fixed64), f_fixed64_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_fixed64));
                }
            }
            if (f_sfixed32_ != 0) {
                if (const auto st = ::protocyte::write_sfixed32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sfixed32), f_sfixed32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_sfixed32));
                }
            }
            if (f_sfixed64_ != 0) {
                if (const auto st = ::protocyte::write_sfixed64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sfixed64), f_sfixed64_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_sfixed64));
                }
            }
            if (::std::bit_cast<::protocyte::u32>(f_float_) != 0u) {
                if (const auto st = ::protocyte::write_float_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_float), f_float_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_float));
                }
            }
            if (::std::bit_cast<::protocyte::u64>(f_double_) != 0u) {
                if (const auto st = ::protocyte::write_double_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_double), f_double_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_double));
                }
            }
            if (!f_string_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_string), f_string_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_string));
                }
            }
            if (!f_bytes_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_bytes), f_bytes_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::f_bytes));
                }
            }
            if (nested_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested), *nested_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::nested));
                }
            }
            for (const auto &r_int32_unpacked_value : r_int32_unpacked_) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked), r_int32_unpacked_value);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked));
                }
            }
            if (!r_int32_packed_.empty()) {
                ::protocyte::usize packed_size_r_int32_packed {};
                for (const auto &packed_value_r_int32_packed : r_int32_packed_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_r_int32_packed,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_r_int32_packed)));
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::r_int32_packed));
                    }
                    packed_size_r_int32_packed = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed), ::protocyte::WireType::LEN);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed));
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_r_int32_packed));
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed));
                }
                for (const auto &packed_value_r_int32_packed : r_int32_packed_) {
                    if (const auto st = ::protocyte::write_int32(writer, packed_value_r_int32_packed); !st) {
                        return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed));
                    }
                }
            }
            if (!r_double_.empty()) {
                ::protocyte::usize packed_size_r_double {};
                const auto packed_size_r_double_result = ::protocyte::checked_mul(r_double_.size(), 8u);
                if (!packed_size_r_double_result) {
                    return ::protocyte::with_field(packed_size_r_double_result.status(),
                                                   static_cast<::protocyte::u32>(FieldNumber::r_double));
                }
                packed_size_r_double = *packed_size_r_double_result;
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::r_double),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_double));
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_r_double));
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_double));
                }
                if (const auto st =
                        ::protocyte::write_fixed_width_packed_values(writer, r_double_.data(), r_double_.size());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::r_double));
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_string),
                        special_oneof_.oneof_string_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_string));
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_int32), special_oneof_.oneof_int32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_int32));
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_nested) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_nested),
                        *special_oneof_.oneof_nested_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_nested));
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                if (const auto st =
                        ::protocyte::write_bytes_field(writer, static_cast<::protocyte::u32>(FieldNumber::oneof_bytes),
                                                       special_oneof_.oneof_bytes_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_bytes));
                }
            }
            if (has_opt_int32_) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::opt_int32), opt_int32_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::opt_int32));
                }
            }
            if (has_opt_string_) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::opt_string), opt_string_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::opt_string));
                }
            }
            for (const auto &entry : map_str_int32_) {
                ::protocyte::usize entry_payload {};
                {
                    const auto field_size_key = ::protocyte::length_delimited_field_size(1u, entry.key.size());
                    if (!field_size_key) {
                        return ::protocyte::with_field(field_size_key.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                    }
                    const auto st_size = ::protocyte::add_size(entry_payload, *field_size_key);
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(2u) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value)));
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::map_str_int32), ::protocyte::WireType::LEN);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                }
                if (const auto st = ::protocyte::write_string_field(writer, 1u, entry.key.view()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                }
                if (const auto st = ::protocyte::write_int32_field(writer, 2u, entry.value); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                }
            }
            for (const auto &entry : map_int32_str_) {
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload,
                        ::protocyte::tag_size(1u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto field_size_value = ::protocyte::length_delimited_field_size(2u, entry.value.size());
                    if (!field_size_value) {
                        return ::protocyte::with_field(field_size_value.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                    }
                    const auto st_size = ::protocyte::add_size(entry_payload, *field_size_value);
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::map_int32_str), ::protocyte::WireType::LEN);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                }
                if (const auto st = ::protocyte::write_int32_field(writer, 1u, entry.key); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                }
                if (const auto st = ::protocyte::write_string_field(writer, 2u, entry.value.view()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                }
            }
            if (!deprecated_unused_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::deprecated_unused),
                        deprecated_unused_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::deprecated_unused));
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

        ::protocyte::Result<::protocyte::usize>
        serialize(const ::protocyte::Span<::protocyte::u8> output) const noexcept {
            return ::protocyte::serialize(*this, output);
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (const auto st = validate(); !st) {
                return ::protocyte::unexpected(st.error());
            }
            ::protocyte::usize total {};
            if (f_int32_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_int32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_int32)));
                }
                total = *st_size;
            }
            if (f_int64_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_int64)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int64_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_int64)));
                }
                total = *st_size;
            }
            if (f_uint32_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_uint32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_uint32)));
                }
                total = *st_size;
            }
            if (f_uint64_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_uint64)) +
                               ::protocyte::varint_size(f_uint64_));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_uint64)));
                }
                total = *st_size;
            }
            if (f_sint32_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sint32)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag32(f_sint32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_sint32)));
                }
                total = *st_size;
            }
            if (f_sint64_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sint64)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag64(f_sint64_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_sint64)));
                }
                total = *st_size;
            }
            if (f_bool_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_bool)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_bool_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_bool)));
                }
                total = *st_size;
            }
            if (mode_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::mode)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(mode_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::mode)));
                }
                total = *st_size;
            }
            if (f_fixed32_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_fixed32)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_fixed32)));
                }
                total = *st_size;
            }
            if (f_fixed64_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_fixed64)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_fixed64)));
                }
                total = *st_size;
            }
            if (f_sfixed32_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sfixed32)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_sfixed32)));
                }
                total = *st_size;
            }
            if (f_sfixed64_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sfixed64)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_sfixed64)));
                }
                total = *st_size;
            }
            if (::std::bit_cast<::protocyte::u32>(f_float_) != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_float)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_float)));
                }
                total = *st_size;
            }
            if (::std::bit_cast<::protocyte::u64>(f_double_) != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_double)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_double)));
                }
                total = *st_size;
            }
            if (!f_string_.empty()) {
                const auto field_size_f_string = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::f_string), f_string_.size());
                if (!field_size_f_string) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_f_string.error(), static_cast<::protocyte::u32>(FieldNumber::f_string)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_f_string);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_string)));
                }
                total = *st_size;
            }
            if (!f_bytes_.empty()) {
                const auto field_size_f_bytes = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::f_bytes), f_bytes_.size());
                if (!field_size_f_bytes) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_f_bytes.error(), static_cast<::protocyte::u32>(FieldNumber::f_bytes)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_f_bytes);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::f_bytes)));
                }
                total = *st_size;
            }
            if (nested_.has_value()) {
                const auto field_size_nested =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::nested), *nested_);
                if (!field_size_nested) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_nested.error(), static_cast<::protocyte::u32>(FieldNumber::nested)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_nested);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::nested)));
                }
                total = *st_size;
            }
            for (const auto &r_int32_unpacked_value : r_int32_unpacked_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_unpacked_value)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked)));
                }
                total = *st_size;
            }
            if (!r_int32_packed_.empty()) {
                ::protocyte::usize packed_size_r_int32_packed {};
                for (const auto &r_int32_packed_value : r_int32_packed_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_r_int32_packed,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_packed_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::r_int32_packed)));
                    }
                    packed_size_r_int32_packed = *st_size;
                }
                const auto field_size_r_int32_packed = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::r_int32_packed), packed_size_r_int32_packed);
                if (!field_size_r_int32_packed) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_r_int32_packed.error(), static_cast<::protocyte::u32>(FieldNumber::r_int32_packed)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_r_int32_packed);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::r_int32_packed)));
                }
                total = *st_size;
            }
            if (!r_double_.empty()) {
                ::protocyte::usize packed_size_r_double {};
                const auto packed_size_r_double_result = ::protocyte::checked_mul(r_double_.size(), 8u);
                if (!packed_size_r_double_result) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        packed_size_r_double_result.error(), static_cast<::protocyte::u32>(FieldNumber::r_double)));
                }
                packed_size_r_double = *packed_size_r_double_result;
                const auto field_size_r_double = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::r_double), packed_size_r_double);
                if (!field_size_r_double) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_r_double.error(), static_cast<::protocyte::u32>(FieldNumber::r_double)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_r_double);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::r_double)));
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                const auto field_size_oneof_string = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::oneof_string), special_oneof_.oneof_string_.size());
                if (!field_size_oneof_string) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_oneof_string.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_string)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_oneof_string);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_string)));
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_int32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(special_oneof_.oneof_int32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_int32)));
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_nested) {
                const auto field_size_oneof_nested = ::protocyte::message_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::oneof_nested), *special_oneof_.oneof_nested_);
                if (!field_size_oneof_nested) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_oneof_nested.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_nested)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_oneof_nested);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_nested)));
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                const auto field_size_oneof_bytes = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::oneof_bytes), special_oneof_.oneof_bytes_.size());
                if (!field_size_oneof_bytes) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_oneof_bytes.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_bytes)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_oneof_bytes);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::oneof_bytes)));
                }
                total = *st_size;
            }
            if (has_opt_int32_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::opt_int32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(opt_int32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::opt_int32)));
                }
                total = *st_size;
            }
            if (has_opt_string_) {
                const auto field_size_opt_string = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::opt_string), opt_string_.size());
                if (!field_size_opt_string) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_opt_string.error(), static_cast<::protocyte::u32>(FieldNumber::opt_string)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_opt_string);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::opt_string)));
                }
                total = *st_size;
            }
            for (const auto &entry : map_str_int32_) {
                ::protocyte::usize entry_payload {};
                {
                    const auto field_size_key = ::protocyte::length_delimited_field_size(1u, entry.key.size());
                    if (!field_size_key) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            field_size_key.error(), static_cast<::protocyte::u32>(FieldNumber::map_str_int32)));
                    }
                    const auto st_size = ::protocyte::add_size(entry_payload, *field_size_key);
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::map_str_int32)));
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(2u) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::map_str_int32)));
                    }
                    entry_payload = *st_size;
                }
                const auto field_size_map_str_int32 = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::map_str_int32), entry_payload);
                if (!field_size_map_str_int32) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_map_str_int32.error(), static_cast<::protocyte::u32>(FieldNumber::map_str_int32)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_map_str_int32);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::map_str_int32)));
                }
                total = *st_size;
            }
            for (const auto &entry : map_int32_str_) {
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload,
                        ::protocyte::tag_size(1u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::map_int32_str)));
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto field_size_value = ::protocyte::length_delimited_field_size(2u, entry.value.size());
                    if (!field_size_value) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            field_size_value.error(), static_cast<::protocyte::u32>(FieldNumber::map_int32_str)));
                    }
                    const auto st_size = ::protocyte::add_size(entry_payload, *field_size_value);
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::map_int32_str)));
                    }
                    entry_payload = *st_size;
                }
                const auto field_size_map_int32_str = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::map_int32_str), entry_payload);
                if (!field_size_map_int32_str) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_map_int32_str.error(), static_cast<::protocyte::u32>(FieldNumber::map_int32_str)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_map_int32_str);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::map_int32_str)));
                }
                total = *st_size;
            }
            if (!deprecated_unused_.empty()) {
                const auto field_size_deprecated_unused = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::deprecated_unused), deprecated_unused_.size());
                if (!field_size_deprecated_unused) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(field_size_deprecated_unused.error(),
                                                static_cast<::protocyte::u32>(FieldNumber::deprecated_unused)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_deprecated_unused);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::deprecated_unused)));
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
            if (const auto st = f_string_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {},
                                               static_cast<::protocyte::u32>(FieldNumber::f_string));
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                if (const auto st = special_oneof_.oneof_string_.validate(); !st) {
                    return ::protocyte::unexpected(st.error().code, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::oneof_string));
                }
            }
            if (const auto st = opt_string_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {},
                                               static_cast<::protocyte::u32>(FieldNumber::opt_string));
            }
            for (const auto &map_str_int32_entry : map_str_int32_) {
                if (const auto st = map_str_int32_entry.key.validate(); !st) {
                    return ::protocyte::unexpected(st.error().code, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::map_str_int32));
                }
            }
            for (const auto &map_int32_str_entry : map_int32_str_) {
                if (const auto st = map_int32_str_entry.value.validate(); !st) {
                    return ::protocyte::unexpected(st.error().code, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::map_int32_str));
                }
            }
            if (const auto st = deprecated_unused_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {},
                                               static_cast<::protocyte::u32>(FieldNumber::deprecated_unused));
            }
            if (nested_.has_value()) {
                if (const auto st = nested_->validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::nested));
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_nested && special_oneof_.oneof_nested_.has_value()) {
                if (const auto st = special_oneof_.oneof_nested_->validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::oneof_nested));
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::i32 f_int32_ {};
        ::protocyte::i64 f_int64_ {};
        ::protocyte::u32 f_uint32_ {};
        ::protocyte::u64 f_uint64_ {};
        ::protocyte::i32 f_sint32_ {};
        ::protocyte::i64 f_sint64_ {};
        bool f_bool_ {};
        ::protocyte::i32 mode_ {};
        ::protocyte::u32 f_fixed32_ {};
        ::protocyte::u64 f_fixed64_ {};
        ::protocyte::i32 f_sfixed32_ {};
        ::protocyte::i64 f_sfixed64_ {};
        ::protocyte::f32 f_float_ {};
        ::protocyte::f64 f_double_ {};
        typename Config::String f_string_;
        typename Config::Bytes f_bytes_;
        typename Config::template Optional<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> nested_;
        typename Config::template Vector<::protocyte::i32> r_int32_unpacked_;
        typename Config::template Vector<::protocyte::i32> r_int32_packed_;
        typename Config::template Vector<::protocyte::f64> r_double_;
        Special_oneofCase special_oneof_case_ {Special_oneofCase::none};
        union Special_oneofStorage {
            Special_oneofStorage() noexcept {}
            ~Special_oneofStorage() noexcept {}
            typename Config::String oneof_string_;
            ::protocyte::i32 oneof_int32_;
            typename Config::template Optional<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>
                oneof_nested_;
            typename Config::Bytes oneof_bytes_;
        } special_oneof_;
        ::protocyte::i32 opt_int32_ {};
        bool has_opt_int32_ {};
        typename Config::String opt_string_;
        bool has_opt_string_ {};
        typename Config::template Map<typename Config::String, ::protocyte::i32> map_str_int32_;
        typename Config::template Map<::protocyte::i32, typename Config::String> map_int32_str_;
        /**
         *  Legacy field retained to verify generated deprecation diagnostics.
         */
        typename Config::String deprecated_unused_;
    };
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#elif defined(_MSC_VER)
#pragma warning(pop)
#endif

} // namespace protocyte_smoke::test::compat

#endif // PROTOCYTE_GENERATED_COMPAT_PROTO_ED5E6124729D_HPP
