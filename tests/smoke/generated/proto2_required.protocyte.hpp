#pragma once

#ifndef PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP
#define PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP

#include <protocyte/runtime/runtime.hpp>

#if PROTOCYTE_ENABLE_REFLECTION
#include <array>
#endif

namespace test::required {

#if PROTOCYTE_ENABLE_REFLECTION
    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> RequiredChild_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> RequiredParent_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> Proto2ArrayDefaults_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 19> Proto2DefaultValues_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> OneofShadowingValue_fields;
    } // namespace protocyte_reflection
#endif // PROTOCYTE_ENABLE_REFLECTION

    enum struct Proto2DefaultMode : ::protocyte::i32 {
        PROTO2_DEFAULT_MODE_UNKNOWN = 5,
        PROTO2_DEFAULT_MODE_READY = 9,
    };

    enum struct Proto2MapMode : ::protocyte::i32 {
        PROTO2_MAP_MODE_UNKNOWN = 0,
        PROTO2_MAP_MODE_READY = 9,
    };

    template<typename Config = ::protocyte::DefaultConfig> struct RequiredChild;
    template<typename Config = ::protocyte::DefaultConfig> struct RequiredParent;
    template<typename Config = ::protocyte::DefaultConfig> struct Proto2ArrayDefaults;
    template<typename Config = ::protocyte::DefaultConfig> struct Proto2DefaultValues;
    template<typename Config = ::protocyte::DefaultConfig> struct OneofShadowingValue;

    template<typename Config> struct RequiredChild {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            id = 1u,
            note = 2u,
        };

        explicit RequiredChild(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx}, note_ {&ctx} {}

        static RequiredChild create(Context &ctx) noexcept { return RequiredChild {ctx}; }
        Context *context() const noexcept { return ctx_; }
        RequiredChild(RequiredChild &&) noexcept = default;
        RequiredChild &operator=(RequiredChild &&) noexcept = default;
        RequiredChild(const RequiredChild &) = delete;
        RequiredChild &operator=(const RequiredChild &) = delete;

        ::protocyte::Status copy_from(const RequiredChild &source) noexcept {
            if (this == &source) {
                return {};
            }
            RequiredChild staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const RequiredChild &source, RequiredChild &staging_message) noexcept {
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

        ::protocyte::Result<RequiredChild> clone() const noexcept {
            auto output = RequiredChild::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(RequiredChild &output) const noexcept {
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
        static void reset_for_reuse_(RequiredChild &value, Context &ctx) noexcept {
            value.~RequiredChild();
            new (&value) RequiredChild {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const RequiredChild &source) noexcept {
            if (source.has_id()) {
                set_id(source.id());
            } else {
                clear_id();
            }
            if (source.has_note()) {
                if (const auto st = set_note(source.note()); !st) {
                    return st;
                }
            } else {
                clear_note();
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

        constexpr ::protocyte::i32 id() const noexcept { return id_; }
        constexpr bool has_id() const noexcept { return has_id_; }
        void set_id(const ::protocyte::i32 value) noexcept {
            id_ = value;
            has_id_ = true;
        }
        constexpr void clear_id() noexcept {
            id_ = {};
            has_id_ = false;
        }

        ::protocyte::StringView note() const noexcept { return note_.view(); }
        bool has_note() const noexcept { return has_note_; }
        typename Config::String &mutable_note() noexcept {
            has_note_ = true;
            return note_;
        }
        template<class Value>::protocyte::Status set_note(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::note));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::note));
            }
            note_ = ::protocyte::move(temp);
            has_note_ = true;
            return {};
        }
        template<class Value>::protocyte::Status set_note(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::note));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::note));
            }
            note_ = ::protocyte::move(temp);
            has_note_ = true;
            return {};
        }
        void clear_note() noexcept {
            note_.clear();
            has_note_ = false;
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<RequiredChild> parse(Context &ctx, Reader &reader) noexcept {
            auto output = RequiredChild::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<RequiredChild> parse(Context &ctx,
                                                        ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, RequiredChild &output) noexcept {
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
                case FieldNumber::id: {
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
                    const auto decoded_id = ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_id) {
                        return decoded_id.status();
                    }
                    id_ = *decoded_id;
                    has_id_ = true;
                    break;
                }
                case FieldNumber::note: {
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
                            ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, note_);
                        !st) {
                        return st;
                    }
                    has_note_ = true;
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
            if (has_id_) {
                if (const auto st =
                        ::protocyte::write_int32_field(writer, static_cast<::protocyte::u32>(FieldNumber::id), id_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::id));
                }
            }
            if (has_note_) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::note), note_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::note));
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
            if (has_id_) {
                const auto st_size =
                    ::protocyte::add_size(total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::id)) +
                                                     ::protocyte::varint_size(static_cast<::protocyte::u64>(id_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::id)));
                }
                total = *st_size;
            }
            if (has_note_) {
                const auto field_size_note = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::note), note_.size());
                if (!field_size_note) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_note.error(), static_cast<::protocyte::u32>(FieldNumber::note)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_note);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::note)));
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
            if (!has_id()) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::id));
            }
            if (const auto st = note_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {}, static_cast<::protocyte::u32>(FieldNumber::note));
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::i32 id_ {};
        bool has_id_ {};
        typename Config::String note_;
        bool has_note_ {};
    };

    template<typename Config> struct RequiredParent {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            child = 1u,
            children = 2u,
        };

        explicit RequiredParent(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx}, children_ {&ctx} {}

        static RequiredParent create(Context &ctx) noexcept { return RequiredParent {ctx}; }
        Context *context() const noexcept { return ctx_; }
        RequiredParent(RequiredParent &&) noexcept = default;
        RequiredParent &operator=(RequiredParent &&) noexcept = default;
        RequiredParent(const RequiredParent &) = delete;
        RequiredParent &operator=(const RequiredParent &) = delete;

        ::protocyte::Status copy_from(const RequiredParent &source) noexcept {
            if (this == &source) {
                return {};
            }
            RequiredParent staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const RequiredParent &source, RequiredParent &staging_message) noexcept {
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

        ::protocyte::Result<RequiredParent> clone() const noexcept {
            auto output = RequiredParent::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(RequiredParent &output) const noexcept {
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
        static void reset_for_reuse_(RequiredParent &value, Context &ctx) noexcept {
            value.~RequiredParent();
            new (&value) RequiredParent {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const RequiredParent &source) noexcept {
            if (source.has_child()) {
                const auto ensured_child = ensure_child();
                if (!ensured_child) {
                    return ::protocyte::with_field(ensured_child.status(),
                                                   static_cast<::protocyte::u32>(FieldNumber::child));
                }
                if (const auto st = ensured_child->copy_from(*source.child()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::child));
                }
            } else {
                clear_child();
            }
            if (const auto st = mutable_children().copy_from(source.children()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::children));
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

        bool has_child() const noexcept { return child_.has_value(); }
        const ::test::required::RequiredChild<Config> *child() const noexcept {
            return has_child() ? child_.operator->() : nullptr;
        }
        ::protocyte::Result<::test::required::RequiredChild<Config> &> ensure_child() noexcept {
            if (child_.has_value()) {
                return *child_;
            }
            if (const auto st = child_.emplace(*ctx_); !st) {
                return ::protocyte::unexpected(
                    ::protocyte::with_field(st.error(), static_cast<::protocyte::u32>(FieldNumber::child)));
            }
            return *child_;
        }
        void clear_child() noexcept { child_.reset(); }

        const typename Config::template Vector<::test::required::RequiredChild<Config>> &children() const noexcept {
            return children_;
        }
        typename Config::template Vector<::test::required::RequiredChild<Config>> &mutable_children() noexcept {
            return children_;
        }
        void clear_children() noexcept { children_.clear(); }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<RequiredParent> parse(Context &ctx, Reader &reader) noexcept {
            auto output = RequiredParent::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<RequiredParent> parse(Context &ctx,
                                                         ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, RequiredParent &output) noexcept {
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
                case FieldNumber::child: {
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
                    ::test::required::RequiredChild<Config> child_value {*ctx_};
                    if (child_.has_value()) {
                        if (const auto st = child_value.copy_from(*child_); !st) {
                            return st;
                        }
                    }
                    if (const auto st =
                            ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number, child_value);
                        !st) {
                        return st;
                    }
                    if (const auto st = child_.emplace(::protocyte::move(child_value)); !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::children: {
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
                    if (const auto st = reader.consume_repeated_elements(1u, field_number); !st) {
                        return st;
                    }
                    ::test::required::RequiredChild<Config> value {*ctx_};
                    if (const auto st = ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number, value);
                        !st) {
                        return st;
                    }
                    if (const auto st = children_.push_back(::protocyte::move(value)); !st) {
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
            if (child_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::child), *child_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::child));
                }
            }
            for (const auto &children_value : children_) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::children), children_value);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::children));
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
            if (child_.has_value()) {
                const auto field_size_child =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::child), *child_);
                if (!field_size_child) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_child.error(), static_cast<::protocyte::u32>(FieldNumber::child)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_child);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::child)));
                }
                total = *st_size;
            }
            for (const auto &children_value : children_) {
                const auto field_size_children = ::protocyte::message_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::children), children_value);
                if (!field_size_children) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_children.error(), static_cast<::protocyte::u32>(FieldNumber::children)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_children);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::children)));
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
            if (child_.has_value()) {
                if (const auto st = child_->validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::child));
                }
            }
            for (const auto &children_value : children_) {
                if (const auto st = children_value.validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::children));
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        typename Config::template Optional<::test::required::RequiredChild<Config>> child_;
        typename Config::template Vector<::test::required::RequiredChild<Config>> children_;
    };

    template<typename Config> struct Proto2ArrayDefaults {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            bounded_bytes = 1u,
            fixed_bytes = 2u,
        };

        explicit Proto2ArrayDefaults(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Proto2ArrayDefaults create(Context &ctx) noexcept { return Proto2ArrayDefaults {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Proto2ArrayDefaults(Proto2ArrayDefaults &&) noexcept = default;
        Proto2ArrayDefaults &operator=(Proto2ArrayDefaults &&) noexcept = default;
        Proto2ArrayDefaults(const Proto2ArrayDefaults &) = delete;
        Proto2ArrayDefaults &operator=(const Proto2ArrayDefaults &) = delete;

        ::protocyte::Status copy_from(const Proto2ArrayDefaults &source) noexcept {
            if (this == &source) {
                return {};
            }
            Proto2ArrayDefaults staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Proto2ArrayDefaults &source,
                                      Proto2ArrayDefaults &staging_message) noexcept {
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

        ::protocyte::Result<Proto2ArrayDefaults> clone() const noexcept {
            auto output = Proto2ArrayDefaults::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Proto2ArrayDefaults &output) const noexcept {
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
        static void reset_for_reuse_(Proto2ArrayDefaults &value, Context &ctx) noexcept {
            value.~Proto2ArrayDefaults();
            new (&value) Proto2ArrayDefaults {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Proto2ArrayDefaults &source) noexcept {
            if (source.has_bounded_bytes()) {
                if (const auto st = set_bounded_bytes(source.bounded_bytes()); !st) {
                    return st;
                }
            } else {
                clear_bounded_bytes();
            }
            if (source.has_fixed_bytes()) {
                if (const auto st = set_fixed_bytes(source.fixed_bytes()); !st) {
                    return st;
                }
            } else {
                clear_fixed_bytes();
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

        ::protocyte::Span<const ::protocyte::u8> bounded_bytes() const noexcept {
            return has_bounded_bytes_ ?
                       bounded_bytes_.view() :
                       ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("abc"), 3u};
        }
        bool has_bounded_bytes() const noexcept { return has_bounded_bytes_; }
        ::protocyte::usize bounded_bytes_size() const noexcept { return bounded_bytes().size(); }
        static constexpr ::protocyte::usize bounded_bytes_max_size() noexcept { return 8u; }
        ::protocyte::Status resize_bounded_bytes(const ::protocyte::usize size) noexcept {
            if (size > 8u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, {},
                                               static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
            }
            if (!has_bounded_bytes_) {
                const auto default_value =
                    ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("abc"), 3u};
                if (const auto st = bounded_bytes_.assign(default_value); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
                }
            }
            if (const auto st = bounded_bytes_.resize(size); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
            }
            has_bounded_bytes_ = true;
            return {};
        }
        ::protocyte::Status resize_bounded_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (const auto st = bounded_bytes_.resize_for_overwrite(size); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
            }
            has_bounded_bytes_ = true;
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_bounded_bytes() noexcept {
            if (!has_bounded_bytes_) {
                const auto default_value =
                    ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("abc"), 3u};
                if (const auto st = bounded_bytes_.assign(default_value); !st) {
                    return ::protocyte::Span<::protocyte::u8> {};
                }
            }
            has_bounded_bytes_ = true;
            return bounded_bytes_.mutable_view();
        }
        template<class Value>::protocyte::Status set_bounded_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(),
                                               static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
            }
            if (const auto st = bounded_bytes_.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
            }
            has_bounded_bytes_ = true;
            return {};
        }
        void clear_bounded_bytes() noexcept {
            bounded_bytes_.clear();
            has_bounded_bytes_ = false;
        }

        bool has_fixed_bytes() const noexcept { return fixed_bytes_.has_value(); }
        ::protocyte::Span<const ::protocyte::u8> fixed_bytes() const noexcept {
            return has_fixed_bytes() ?
                       fixed_bytes_.view() :
                       ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("xyz"), 3u};
        }
        ::protocyte::Span<::protocyte::u8> mutable_fixed_bytes() noexcept {
            if (!has_fixed_bytes()) {
                const auto default_value =
                    ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("xyz"), 3u};
                if (const auto st = fixed_bytes_.assign(default_value); !st) {
                    return ::protocyte::Span<::protocyte::u8> {};
                }
            }
            return fixed_bytes_.mutable_view();
        }
        ::protocyte::Status resize_fixed_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            return ::protocyte::with_field(fixed_bytes_.resize_for_overwrite(size),
                                           static_cast<::protocyte::u32>(FieldNumber::fixed_bytes));
        }
        template<class Value>::protocyte::Status set_fixed_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::fixed_bytes));
            }
            return ::protocyte::with_field(fixed_bytes_.assign(*view),
                                           static_cast<::protocyte::u32>(FieldNumber::fixed_bytes));
        }
        void clear_fixed_bytes() noexcept { fixed_bytes_.clear(); }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Proto2ArrayDefaults> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Proto2ArrayDefaults::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Proto2ArrayDefaults> parse(Context &ctx,
                                                              ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Proto2ArrayDefaults &output) noexcept {
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
                case FieldNumber::bounded_bytes: {
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
                    auto len = ::protocyte::read_length_delimited_size(reader);
                    if (!len) {
                        return len.status();
                    }
                    if (*len > 8u) {
                        return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                       field_number);
                    }
                    if (const auto st = reader.can_read(*len); !st) {
                        return st;
                    }
                    ::protocyte::ByteArray<8u> bounded_bytes_value {};
                    if (const auto st = bounded_bytes_value.resize_for_overwrite(*len); !st) {
                        return st;
                    }
                    const auto view = bounded_bytes_value.mutable_view();
                    if (const auto st = reader.read(view.data(), view.size()); !st) {
                        return st;
                    }
                    bounded_bytes_ = ::protocyte::move(bounded_bytes_value);
                    has_bounded_bytes_ = true;
                    break;
                }
                case FieldNumber::fixed_bytes: {
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
                    auto len = ::protocyte::read_length_delimited_size(reader);
                    if (!len) {
                        return len.status();
                    }
                    if (*len != 3u) {
                        return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, reader.position(),
                                                       field_number);
                    }
                    if (const auto st = reader.can_read(*len); !st) {
                        return st;
                    }
                    ::protocyte::FixedByteArray<3u> fixed_bytes_value {};
                    if (const auto st = fixed_bytes_value.resize_for_overwrite(*len); !st) {
                        return st;
                    }
                    const auto view = fixed_bytes_value.mutable_view();
                    if (const auto st = reader.read(view.data(), view.size()); !st) {
                        return st;
                    }
                    fixed_bytes_ = ::protocyte::move(fixed_bytes_value);
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
            if (has_bounded_bytes_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes), bounded_bytes_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes));
                }
            }
            if (fixed_bytes_.has_value()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed_bytes), fixed_bytes_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::fixed_bytes));
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
            if (has_bounded_bytes_) {
                const auto field_size_bounded_bytes = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::bounded_bytes), bounded_bytes_.size());
                if (!field_size_bounded_bytes) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_bounded_bytes.error(), static_cast<::protocyte::u32>(FieldNumber::bounded_bytes)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_bounded_bytes);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::bounded_bytes)));
                }
                total = *st_size;
            }
            if (fixed_bytes_.has_value()) {
                const auto field_size_fixed_bytes = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::fixed_bytes), fixed_bytes_.size());
                if (!field_size_fixed_bytes) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_fixed_bytes.error(), static_cast<::protocyte::u32>(FieldNumber::fixed_bytes)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_fixed_bytes);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::fixed_bytes)));
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
        ::protocyte::ByteArray<8u> bounded_bytes_;
        bool has_bounded_bytes_ {};
        ::protocyte::FixedByteArray<3u> fixed_bytes_;
    };

    template<typename Config> struct Proto2DefaultValues {
        using Context = typename Config::Context;

        enum struct FieldNumber : ::protocyte::u32 {
            double_value = 1u,
            float_value = 2u,
            int64_value = 3u,
            uint64_value = 4u,
            int32_value = 5u,
            fixed64_value = 6u,
            fixed32_value = 7u,
            bool_value = 8u,
            string_value = 9u,
            bytes_value = 10u,
            uint32_value = 11u,
            enum_value = 12u,
            sfixed32_value = 13u,
            sfixed64_value = 14u,
            sint32_value = 15u,
            sint64_value = 16u,
            implicit_enum_value = 17u,
            enum_values = 18u,
            enum_by_name = 19u,
        };

        explicit Proto2DefaultValues(Context &ctx) noexcept:
            ctx_ {&ctx},
            unknown_fields_ {&ctx},
            string_value_ {&ctx},
            bytes_value_ {&ctx},
            enum_values_ {&ctx},
            enum_by_name_ {&ctx} {}

        static Proto2DefaultValues create(Context &ctx) noexcept { return Proto2DefaultValues {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Proto2DefaultValues(Proto2DefaultValues &&) noexcept = default;
        Proto2DefaultValues &operator=(Proto2DefaultValues &&) noexcept = default;
        Proto2DefaultValues(const Proto2DefaultValues &) = delete;
        Proto2DefaultValues &operator=(const Proto2DefaultValues &) = delete;

        ::protocyte::Status copy_from(const Proto2DefaultValues &source) noexcept {
            if (this == &source) {
                return {};
            }
            Proto2DefaultValues staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Proto2DefaultValues &source,
                                      Proto2DefaultValues &staging_message) noexcept {
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

        ::protocyte::Result<Proto2DefaultValues> clone() const noexcept {
            auto output = Proto2DefaultValues::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Proto2DefaultValues &output) const noexcept {
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
        static void reset_for_reuse_(Proto2DefaultValues &value, Context &ctx) noexcept {
            value.~Proto2DefaultValues();
            new (&value) Proto2DefaultValues {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Proto2DefaultValues &source) noexcept {
            if (source.has_double_value()) {
                set_double_value(source.double_value());
            } else {
                clear_double_value();
            }
            if (source.has_float_value()) {
                set_float_value(source.float_value());
            } else {
                clear_float_value();
            }
            if (source.has_int64_value()) {
                set_int64_value(source.int64_value());
            } else {
                clear_int64_value();
            }
            if (source.has_uint64_value()) {
                set_uint64_value(source.uint64_value());
            } else {
                clear_uint64_value();
            }
            if (source.has_int32_value()) {
                set_int32_value(source.int32_value());
            } else {
                clear_int32_value();
            }
            if (source.has_fixed64_value()) {
                set_fixed64_value(source.fixed64_value());
            } else {
                clear_fixed64_value();
            }
            if (source.has_fixed32_value()) {
                set_fixed32_value(source.fixed32_value());
            } else {
                clear_fixed32_value();
            }
            if (source.has_bool_value()) {
                set_bool_value(source.bool_value());
            } else {
                clear_bool_value();
            }
            if (source.has_string_value()) {
                if (const auto st = set_string_value(source.string_value()); !st) {
                    return st;
                }
            } else {
                clear_string_value();
            }
            if (source.has_bytes_value()) {
                if (const auto st = set_bytes_value(source.bytes_value()); !st) {
                    return st;
                }
            } else {
                clear_bytes_value();
            }
            if (source.has_uint32_value()) {
                set_uint32_value(source.uint32_value());
            } else {
                clear_uint32_value();
            }
            if (source.has_enum_value()) {
                if (const auto st = set_enum_value_raw(source.enum_value_raw()); !st) {
                    return st;
                }
            } else {
                clear_enum_value();
            }
            if (source.has_sfixed32_value()) {
                set_sfixed32_value(source.sfixed32_value());
            } else {
                clear_sfixed32_value();
            }
            if (source.has_sfixed64_value()) {
                set_sfixed64_value(source.sfixed64_value());
            } else {
                clear_sfixed64_value();
            }
            if (source.has_sint32_value()) {
                set_sint32_value(source.sint32_value());
            } else {
                clear_sint32_value();
            }
            if (source.has_sint64_value()) {
                set_sint64_value(source.sint64_value());
            } else {
                clear_sint64_value();
            }
            if (source.has_implicit_enum_value()) {
                if (const auto st = set_implicit_enum_value_raw(source.implicit_enum_value_raw()); !st) {
                    return st;
                }
            } else {
                clear_implicit_enum_value();
            }
            if (const auto st = mutable_enum_values().copy_from(source.enum_values()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_values));
            }
            if (const auto st = mutable_enum_by_name().copy_from(source.enum_by_name()); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
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

        constexpr ::protocyte::f64 double_value() const noexcept { return has_double_value_ ? double_value_ : 1.5; }
        constexpr bool has_double_value() const noexcept { return has_double_value_; }
        void set_double_value(const ::protocyte::f64 value) noexcept {
            double_value_ = value;
            has_double_value_ = true;
        }
        constexpr void clear_double_value() noexcept {
            double_value_ = {};
            has_double_value_ = false;
        }

        constexpr ::protocyte::f32 float_value() const noexcept { return has_float_value_ ? float_value_ : -2.25f; }
        constexpr bool has_float_value() const noexcept { return has_float_value_; }
        void set_float_value(const ::protocyte::f32 value) noexcept {
            float_value_ = value;
            has_float_value_ = true;
        }
        constexpr void clear_float_value() noexcept {
            float_value_ = {};
            has_float_value_ = false;
        }

        constexpr ::protocyte::i64 int64_value() const noexcept {
            return has_int64_value_ ? int64_value_ : -1234567890123ll;
        }
        constexpr bool has_int64_value() const noexcept { return has_int64_value_; }
        void set_int64_value(const ::protocyte::i64 value) noexcept {
            int64_value_ = value;
            has_int64_value_ = true;
        }
        constexpr void clear_int64_value() noexcept {
            int64_value_ = {};
            has_int64_value_ = false;
        }

        constexpr ::protocyte::u64 uint64_value() const noexcept {
            return has_uint64_value_ ? uint64_value_ : 1234567890123ull;
        }
        constexpr bool has_uint64_value() const noexcept { return has_uint64_value_; }
        void set_uint64_value(const ::protocyte::u64 value) noexcept {
            uint64_value_ = value;
            has_uint64_value_ = true;
        }
        constexpr void clear_uint64_value() noexcept {
            uint64_value_ = {};
            has_uint64_value_ = false;
        }

        constexpr ::protocyte::i32 int32_value() const noexcept { return has_int32_value_ ? int32_value_ : -12345; }
        constexpr bool has_int32_value() const noexcept { return has_int32_value_; }
        void set_int32_value(const ::protocyte::i32 value) noexcept {
            int32_value_ = value;
            has_int32_value_ = true;
        }
        constexpr void clear_int32_value() noexcept {
            int32_value_ = {};
            has_int32_value_ = false;
        }

        constexpr ::protocyte::u64 fixed64_value() const noexcept {
            return has_fixed64_value_ ? fixed64_value_ : 12345678901234ull;
        }
        constexpr bool has_fixed64_value() const noexcept { return has_fixed64_value_; }
        void set_fixed64_value(const ::protocyte::u64 value) noexcept {
            fixed64_value_ = value;
            has_fixed64_value_ = true;
        }
        constexpr void clear_fixed64_value() noexcept {
            fixed64_value_ = {};
            has_fixed64_value_ = false;
        }

        constexpr ::protocyte::u32 fixed32_value() const noexcept {
            return has_fixed32_value_ ? fixed32_value_ : 123456789u;
        }
        constexpr bool has_fixed32_value() const noexcept { return has_fixed32_value_; }
        void set_fixed32_value(const ::protocyte::u32 value) noexcept {
            fixed32_value_ = value;
            has_fixed32_value_ = true;
        }
        constexpr void clear_fixed32_value() noexcept {
            fixed32_value_ = {};
            has_fixed32_value_ = false;
        }

        constexpr bool bool_value() const noexcept { return has_bool_value_ ? bool_value_ : true; }
        constexpr bool has_bool_value() const noexcept { return has_bool_value_; }
        void set_bool_value(const bool value) noexcept {
            bool_value_ = value;
            has_bool_value_ = true;
        }
        constexpr void clear_bool_value() noexcept {
            bool_value_ = {};
            has_bool_value_ = false;
        }

        ::protocyte::StringView string_value() const noexcept {
            return has_string_value_ ? string_value_.view() : ::protocyte::StringView {"default-text", 12u};
        }
        bool has_string_value() const noexcept { return has_string_value_; }
        typename Config::String &mutable_string_value() noexcept {
            has_string_value_ = true;
            return string_value_;
        }
        template<class Value>::protocyte::Status set_string_value(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::string_value));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::string_value));
            }
            string_value_ = ::protocyte::move(temp);
            has_string_value_ = true;
            return {};
        }
        template<class Value>::protocyte::Status set_string_value(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::string_value));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::string_value));
            }
            string_value_ = ::protocyte::move(temp);
            has_string_value_ = true;
            return {};
        }
        void clear_string_value() noexcept {
            string_value_.clear();
            has_string_value_ = false;
        }

        ::protocyte::Span<const ::protocyte::u8> bytes_value() const noexcept {
            return has_bytes_value_ ? bytes_value_.view() :
                                      ::protocyte::Span<const ::protocyte::u8> {
                                          reinterpret_cast<const ::protocyte::u8 *>("default-bytes"), 13u};
        }
        bool has_bytes_value() const noexcept { return has_bytes_value_; }
        typename Config::Bytes &mutable_bytes_value() noexcept {
            has_bytes_value_ = true;
            return bytes_value_;
        }
        template<class Value>::protocyte::Status set_bytes_value(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::bytes_value));
            }
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bytes_value));
            }
            bytes_value_ = ::protocyte::move(temp);
            has_bytes_value_ = true;
            return {};
        }
        void clear_bytes_value() noexcept {
            bytes_value_.clear();
            has_bytes_value_ = false;
        }

        constexpr ::protocyte::u32 uint32_value() const noexcept { return has_uint32_value_ ? uint32_value_ : 456789u; }
        constexpr bool has_uint32_value() const noexcept { return has_uint32_value_; }
        void set_uint32_value(const ::protocyte::u32 value) noexcept {
            uint32_value_ = value;
            has_uint32_value_ = true;
        }
        constexpr void clear_uint32_value() noexcept {
            uint32_value_ = {};
            has_uint32_value_ = false;
        }

        constexpr ::protocyte::i32 enum_value_raw() const noexcept { return has_enum_value_ ? enum_value_ : 9; }
        constexpr ::test::required::Proto2DefaultMode enum_value() const noexcept {
            return static_cast<::test::required::Proto2DefaultMode>(has_enum_value_ ? enum_value_ : 9);
        }
        constexpr bool has_enum_value() const noexcept { return has_enum_value_; }
        ::protocyte::Status set_enum_value_raw(const ::protocyte::i32 value) noexcept {
            if (value != 5 && value != 9) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::enum_value));
            }
            enum_value_ = value;
            has_enum_value_ = true;
            return {};
        }
        ::protocyte::Status set_enum_value(const ::test::required::Proto2DefaultMode value) noexcept {
            return set_enum_value_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_enum_value() noexcept {
            enum_value_ = {};
            has_enum_value_ = false;
        }

        constexpr ::protocyte::i32 sfixed32_value() const noexcept {
            return has_sfixed32_value_ ? sfixed32_value_ : -54321;
        }
        constexpr bool has_sfixed32_value() const noexcept { return has_sfixed32_value_; }
        void set_sfixed32_value(const ::protocyte::i32 value) noexcept {
            sfixed32_value_ = value;
            has_sfixed32_value_ = true;
        }
        constexpr void clear_sfixed32_value() noexcept {
            sfixed32_value_ = {};
            has_sfixed32_value_ = false;
        }

        constexpr ::protocyte::i64 sfixed64_value() const noexcept {
            return has_sfixed64_value_ ? sfixed64_value_ : -9876543210ll;
        }
        constexpr bool has_sfixed64_value() const noexcept { return has_sfixed64_value_; }
        void set_sfixed64_value(const ::protocyte::i64 value) noexcept {
            sfixed64_value_ = value;
            has_sfixed64_value_ = true;
        }
        constexpr void clear_sfixed64_value() noexcept {
            sfixed64_value_ = {};
            has_sfixed64_value_ = false;
        }

        constexpr ::protocyte::i32 sint32_value() const noexcept { return has_sint32_value_ ? sint32_value_ : -23456; }
        constexpr bool has_sint32_value() const noexcept { return has_sint32_value_; }
        void set_sint32_value(const ::protocyte::i32 value) noexcept {
            sint32_value_ = value;
            has_sint32_value_ = true;
        }
        constexpr void clear_sint32_value() noexcept {
            sint32_value_ = {};
            has_sint32_value_ = false;
        }

        constexpr ::protocyte::i64 sint64_value() const noexcept {
            return has_sint64_value_ ? sint64_value_ : -123456789012ll;
        }
        constexpr bool has_sint64_value() const noexcept { return has_sint64_value_; }
        void set_sint64_value(const ::protocyte::i64 value) noexcept {
            sint64_value_ = value;
            has_sint64_value_ = true;
        }
        constexpr void clear_sint64_value() noexcept {
            sint64_value_ = {};
            has_sint64_value_ = false;
        }

        constexpr ::protocyte::i32 implicit_enum_value_raw() const noexcept {
            return has_implicit_enum_value_ ? implicit_enum_value_ : 5;
        }
        constexpr ::test::required::Proto2DefaultMode implicit_enum_value() const noexcept {
            return static_cast<::test::required::Proto2DefaultMode>(has_implicit_enum_value_ ? implicit_enum_value_ :
                                                                                               5);
        }
        constexpr bool has_implicit_enum_value() const noexcept { return has_implicit_enum_value_; }
        ::protocyte::Status set_implicit_enum_value_raw(const ::protocyte::i32 value) noexcept {
            if (value != 5 && value != 9) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value));
            }
            implicit_enum_value_ = value;
            has_implicit_enum_value_ = true;
            return {};
        }
        ::protocyte::Status set_implicit_enum_value(const ::test::required::Proto2DefaultMode value) noexcept {
            return set_implicit_enum_value_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_implicit_enum_value() noexcept {
            implicit_enum_value_ = {};
            has_implicit_enum_value_ = false;
        }

        const typename Config::template Vector<::protocyte::i32> &enum_values() const noexcept { return enum_values_; }
        typename Config::template Vector<::protocyte::i32> &mutable_enum_values() noexcept { return enum_values_; }
        void clear_enum_values() noexcept { enum_values_.clear(); }

        const typename Config::template Map<typename Config::String, ::protocyte::i32> &enum_by_name() const noexcept {
            return enum_by_name_;
        }
        typename Config::template Map<typename Config::String, ::protocyte::i32> &mutable_enum_by_name() noexcept {
            return enum_by_name_;
        }
        void clear_enum_by_name() noexcept { enum_by_name_.clear(); }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Proto2DefaultValues> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Proto2DefaultValues::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Proto2DefaultValues> parse(Context &ctx,
                                                              ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Proto2DefaultValues &output) noexcept {
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
                case FieldNumber::double_value: {
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
                    const auto decoded_double_value = ::protocyte::read_double_field(reader, wire_type, field_number);
                    if (!decoded_double_value) {
                        return decoded_double_value.status();
                    }
                    double_value_ = *decoded_double_value;
                    has_double_value_ = true;
                    break;
                }
                case FieldNumber::float_value: {
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
                    const auto decoded_float_value = ::protocyte::read_float_field(reader, wire_type, field_number);
                    if (!decoded_float_value) {
                        return decoded_float_value.status();
                    }
                    float_value_ = *decoded_float_value;
                    has_float_value_ = true;
                    break;
                }
                case FieldNumber::int64_value: {
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
                    const auto decoded_int64_value = ::protocyte::read_int64_field(reader, wire_type, field_number);
                    if (!decoded_int64_value) {
                        return decoded_int64_value.status();
                    }
                    int64_value_ = *decoded_int64_value;
                    has_int64_value_ = true;
                    break;
                }
                case FieldNumber::uint64_value: {
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
                    const auto decoded_uint64_value = ::protocyte::read_uint64_field(reader, wire_type, field_number);
                    if (!decoded_uint64_value) {
                        return decoded_uint64_value.status();
                    }
                    uint64_value_ = *decoded_uint64_value;
                    has_uint64_value_ = true;
                    break;
                }
                case FieldNumber::int32_value: {
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
                    const auto decoded_int32_value = ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_int32_value) {
                        return decoded_int32_value.status();
                    }
                    int32_value_ = *decoded_int32_value;
                    has_int32_value_ = true;
                    break;
                }
                case FieldNumber::fixed64_value: {
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
                    const auto decoded_fixed64_value =
                        ::protocyte::read_fixed64_value_field(reader, wire_type, field_number);
                    if (!decoded_fixed64_value) {
                        return decoded_fixed64_value.status();
                    }
                    fixed64_value_ = *decoded_fixed64_value;
                    has_fixed64_value_ = true;
                    break;
                }
                case FieldNumber::fixed32_value: {
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
                    const auto decoded_fixed32_value =
                        ::protocyte::read_fixed32_value_field(reader, wire_type, field_number);
                    if (!decoded_fixed32_value) {
                        return decoded_fixed32_value.status();
                    }
                    fixed32_value_ = *decoded_fixed32_value;
                    has_fixed32_value_ = true;
                    break;
                }
                case FieldNumber::bool_value: {
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
                    const auto decoded_bool_value = ::protocyte::read_bool_field(reader, wire_type, field_number);
                    if (!decoded_bool_value) {
                        return decoded_bool_value.status();
                    }
                    bool_value_ = *decoded_bool_value;
                    has_bool_value_ = true;
                    break;
                }
                case FieldNumber::string_value: {
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
                                                                               string_value_);
                        !st) {
                        return st;
                    }
                    has_string_value_ = true;
                    break;
                }
                case FieldNumber::bytes_value: {
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
                            ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type, field_number, bytes_value_);
                        !st) {
                        return st;
                    }
                    has_bytes_value_ = true;
                    break;
                }
                case FieldNumber::uint32_value: {
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
                    const auto decoded_uint32_value = ::protocyte::read_uint32_field(reader, wire_type, field_number);
                    if (!decoded_uint32_value) {
                        return decoded_uint32_value.status();
                    }
                    uint32_value_ = *decoded_uint32_value;
                    has_uint32_value_ = true;
                    break;
                }
                case FieldNumber::enum_value: {
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
                    const auto decoded_enum_value_raw = ::protocyte::read_varint(reader);
                    if (!decoded_enum_value_raw) {
                        return decoded_enum_value_raw.status();
                    }
                    const auto enum_value_value = static_cast<::protocyte::i32>(*decoded_enum_value_raw);
                    bool enum_value_accepted {true};
                    if (enum_value_value != 5 && enum_value_value != 9) {
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            auto unknown = mutable_unknown_fields();
                            if (const auto st = unknown.add_varint(field_number, *decoded_enum_value_raw); !st) {
                                return st;
                            }
                        }
                        enum_value_accepted = false;
                    } else {
                        enum_value_ = enum_value_value;
                    }
                    if (!enum_value_accepted) {
                        break;
                    }
                    has_enum_value_ = true;
                    break;
                }
                case FieldNumber::sfixed32_value: {
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
                    const auto decoded_sfixed32_value =
                        ::protocyte::read_sfixed32_field(reader, wire_type, field_number);
                    if (!decoded_sfixed32_value) {
                        return decoded_sfixed32_value.status();
                    }
                    sfixed32_value_ = *decoded_sfixed32_value;
                    has_sfixed32_value_ = true;
                    break;
                }
                case FieldNumber::sfixed64_value: {
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
                    const auto decoded_sfixed64_value =
                        ::protocyte::read_sfixed64_field(reader, wire_type, field_number);
                    if (!decoded_sfixed64_value) {
                        return decoded_sfixed64_value.status();
                    }
                    sfixed64_value_ = *decoded_sfixed64_value;
                    has_sfixed64_value_ = true;
                    break;
                }
                case FieldNumber::sint32_value: {
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
                    const auto decoded_sint32_value = ::protocyte::read_sint32_field(reader, wire_type, field_number);
                    if (!decoded_sint32_value) {
                        return decoded_sint32_value.status();
                    }
                    sint32_value_ = *decoded_sint32_value;
                    has_sint32_value_ = true;
                    break;
                }
                case FieldNumber::sint64_value: {
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
                    const auto decoded_sint64_value = ::protocyte::read_sint64_field(reader, wire_type, field_number);
                    if (!decoded_sint64_value) {
                        return decoded_sint64_value.status();
                    }
                    sint64_value_ = *decoded_sint64_value;
                    has_sint64_value_ = true;
                    break;
                }
                case FieldNumber::implicit_enum_value: {
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
                    const auto decoded_implicit_enum_value_raw = ::protocyte::read_varint(reader);
                    if (!decoded_implicit_enum_value_raw) {
                        return decoded_implicit_enum_value_raw.status();
                    }
                    const auto implicit_enum_value_value =
                        static_cast<::protocyte::i32>(*decoded_implicit_enum_value_raw);
                    bool implicit_enum_value_accepted {true};
                    if (implicit_enum_value_value != 5 && implicit_enum_value_value != 9) {
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            auto unknown = mutable_unknown_fields();
                            if (const auto st = unknown.add_varint(field_number, *decoded_implicit_enum_value_raw);
                                !st) {
                                return st;
                            }
                        }
                        implicit_enum_value_accepted = false;
                    } else {
                        implicit_enum_value_ = implicit_enum_value_value;
                    }
                    if (!implicit_enum_value_accepted) {
                        break;
                    }
                    has_implicit_enum_value_ = true;
                    break;
                }
                case FieldNumber::enum_values: {
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
                        typename Config::template Vector<::protocyte::i32> packed_enum_values_values {ctx_};
                        ::protocyte::UnknownFieldStorage<Config> packed_enum_values_unknown_fields {ctx_};
                        ::protocyte::LimitedReader<Reader> packed {reader, *len};
                        while (!packed.eof()) {
                            if (const auto st = packed.consume_repeated_elements(1u, field_number); !st) {
                                return st;
                            }
                            ::protocyte::i32 value {};
                            const auto decoded_enum_values_raw = ::protocyte::read_varint(packed);
                            if (!decoded_enum_values_raw) {
                                return decoded_enum_values_raw.status();
                            }
                            const auto enum_values_value = static_cast<::protocyte::i32>(*decoded_enum_values_raw);
                            bool enum_values_accepted {true};
                            if (enum_values_value != 5 && enum_values_value != 9) {
                                if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                                    ::protocyte::MutableUnknownFieldSet<Config> unknown {
                                        *ctx_, packed_enum_values_unknown_fields};
                                    if (const auto st = unknown.add_varint(field_number, *decoded_enum_values_raw);
                                        !st) {
                                        return st;
                                    }
                                }
                                enum_values_accepted = false;
                            } else {
                                value = enum_values_value;
                            }
                            if (!enum_values_accepted) {
                                continue;
                            }
                            if (const auto st = packed_enum_values_values.push_back(value); !st) {
                                return st;
                            }
                        }
                        const auto packed_enum_values_values_prepared_size =
                            ::protocyte::checked_add(enum_values_.size(), packed_enum_values_values.size());
                        if (!packed_enum_values_values_prepared_size) {
                            return packed_enum_values_values_prepared_size.status();
                        }
                        if (const auto st = enum_values_.reserve(*packed_enum_values_values_prepared_size); !st) {
                            return st;
                        }
                        ::protocyte::UnknownFieldStorage<Config> merged_enum_values_unknown_fields {ctx_};
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            if (!packed_enum_values_unknown_fields.empty()) {
                                if (const auto st = ::protocyte::prepare_unknown_field_merge<Config>(
                                        *ctx_, unknown_fields_, packed_enum_values_unknown_fields,
                                        merged_enum_values_unknown_fields);
                                    !st) {
                                    return st;
                                }
                            }
                        }
                        if (const auto st = enum_values_.append_trivial_range(packed_enum_values_values.data(),
                                                                              packed_enum_values_values.size());
                            !st) {
                            return st;
                        }
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            if (!packed_enum_values_unknown_fields.empty()) {
                                unknown_fields_ = ::protocyte::move(merged_enum_values_unknown_fields);
                            }
                        }
                        break;
                    }
                    if (const auto st = reader.consume_repeated_elements(1u, field_number); !st) {
                        return st;
                    }
                    ::protocyte::i32 value {};
                    const auto decoded_enum_values_raw = ::protocyte::read_varint(reader);
                    if (!decoded_enum_values_raw) {
                        return decoded_enum_values_raw.status();
                    }
                    const auto enum_values_value = static_cast<::protocyte::i32>(*decoded_enum_values_raw);
                    bool enum_values_accepted {true};
                    if (enum_values_value != 5 && enum_values_value != 9) {
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                            auto unknown = mutable_unknown_fields();
                            if (const auto st = unknown.add_varint(field_number, *decoded_enum_values_raw); !st) {
                                return st;
                            }
                        }
                        enum_values_accepted = false;
                    } else {
                        value = enum_values_value;
                    }
                    if (!enum_values_accepted) {
                        break;
                    }
                    if (const auto st = enum_values_.push_back(value); !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::enum_by_name: {
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
                    const auto parse_enum_by_name_entry = [&](auto &entry_reader) noexcept -> ::protocyte::Status {
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
                                    const auto decoded_value_enum = ::protocyte::read_enum(entry_reader);
                                    if (!decoded_value_enum) {
                                        return decoded_value_enum.status();
                                    }
                                    const auto value_enum_value = *decoded_value_enum;
                                    if (value_enum_value != 0 && value_enum_value != 9) {
                                        entry_is_unknown = true;
                                    } else {
                                        entry_is_unknown = false;
                                        value = value_enum_value;
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
                    if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                        const auto entry_size = ::protocyte::read_length_delimited_size(reader);
                        if (!entry_size) {
                            return entry_size.status();
                        }
                        if (*entry_size > ctx_->limits.max_message_bytes) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*entry_size); !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::push_recursion<Config>(*ctx_, reader.position(), field_number);
                            !st) {
                            return st;
                        }
                        const auto entry_offset = reader.position();
                        typename Config::template Vector<::protocyte::u8> staged_enum_by_name_entry {ctx_};
                        if (const auto st = staged_enum_by_name_entry.resize_for_overwrite(*entry_size); !st) {
                            ::protocyte::pop_recursion<Config>(*ctx_);
                            return st;
                        }
                        if (const auto st =
                                reader.read(staged_enum_by_name_entry.data(), staged_enum_by_name_entry.size());
                            !st) {
                            ::protocyte::pop_recursion<Config>(*ctx_);
                            return st;
                        }
                        ::protocyte::StagedReader<Reader> entry_reader {
                            ::protocyte::Span<const ::protocyte::u8> {staged_enum_by_name_entry.data(),
                                                                      staged_enum_by_name_entry.size()},
                            reader, entry_offset};
                        const auto entry_status = parse_enum_by_name_entry(entry_reader);
                        ::protocyte::pop_recursion<Config>(*ctx_);
                        if (!entry_status) {
                            return entry_status;
                        }
                        if (entry_is_unknown) {
                            auto unknown = mutable_unknown_fields();
                            if (const auto st = unknown.add_length_delimited(
                                    field_number,
                                    ::protocyte::Span<const ::protocyte::u8> {staged_enum_by_name_entry.data(),
                                                                              staged_enum_by_name_entry.size()});
                                !st) {
                                return st;
                            }
                        } else {
                            if (const auto insert =
                                    enum_by_name_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                                !insert) {
                                return insert;
                            }
                        }
                    } else {
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        if (const auto st = parse_enum_by_name_entry(entry_reader); !st) {
                            return st;
                        }
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (!entry_is_unknown) {
                            if (const auto insert =
                                    enum_by_name_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                                !insert) {
                                return insert;
                            }
                        }
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
            if (has_double_value_) {
                if (const auto st = ::protocyte::write_double_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::double_value), double_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::double_value));
                }
            }
            if (has_float_value_) {
                if (const auto st = ::protocyte::write_float_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::float_value), float_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::float_value));
                }
            }
            if (has_int64_value_) {
                if (const auto st = ::protocyte::write_int64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::int64_value), int64_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::int64_value));
                }
            }
            if (has_uint64_value_) {
                if (const auto st = ::protocyte::write_uint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::uint64_value), uint64_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::uint64_value));
                }
            }
            if (has_int32_value_) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::int32_value), int32_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::int32_value));
                }
            }
            if (has_fixed64_value_) {
                if (const auto st = ::protocyte::write_fixed64_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed64_value), fixed64_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::fixed64_value));
                }
            }
            if (has_fixed32_value_) {
                if (const auto st = ::protocyte::write_fixed32_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed32_value), fixed32_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::fixed32_value));
                }
            }
            if (has_bool_value_) {
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bool_value), bool_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bool_value));
                }
            }
            if (has_string_value_) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::string_value), string_value_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::string_value));
                }
            }
            if (has_bytes_value_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bytes_value), bytes_value_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bytes_value));
                }
            }
            if (has_uint32_value_) {
                if (const auto st = ::protocyte::write_uint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::uint32_value), uint32_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::uint32_value));
                }
            }
            if (has_enum_value_) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::enum_value), enum_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_value));
                }
            }
            if (has_sfixed32_value_) {
                if (const auto st = ::protocyte::write_sfixed32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sfixed32_value), sfixed32_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::sfixed32_value));
                }
            }
            if (has_sfixed64_value_) {
                if (const auto st = ::protocyte::write_sfixed64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sfixed64_value), sfixed64_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::sfixed64_value));
                }
            }
            if (has_sint32_value_) {
                if (const auto st = ::protocyte::write_sint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sint32_value), sint32_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::sint32_value));
                }
            }
            if (has_sint64_value_) {
                if (const auto st = ::protocyte::write_sint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sint64_value), sint64_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::sint64_value));
                }
            }
            if (has_implicit_enum_value_) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value), implicit_enum_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value));
                }
            }
            if (!enum_values_.empty()) {
                ::protocyte::usize packed_size_enum_values {};
                for (const auto &packed_value_enum_values : enum_values_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_enum_values,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_enum_values)));
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::enum_values));
                    }
                    packed_size_enum_values = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::enum_values), ::protocyte::WireType::LEN);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_values));
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_enum_values));
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_values));
                }
                for (const auto &packed_value_enum_values : enum_values_) {
                    if (const auto st = ::protocyte::write_enum(writer, packed_value_enum_values); !st) {
                        return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_values));
                    }
                }
            }
            for (const auto &entry : enum_by_name_) {
                ::protocyte::usize entry_payload {};
                {
                    const auto field_size_key = ::protocyte::length_delimited_field_size(1u, entry.key.size());
                    if (!field_size_key) {
                        return ::protocyte::with_field(field_size_key.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                    }
                    const auto st_size = ::protocyte::add_size(entry_payload, *field_size_key);
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(2u) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value)));
                    if (!st_size) {
                        return ::protocyte::with_field(st_size.status(),
                                                       static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::enum_by_name), ::protocyte::WireType::LEN);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                }
                if (const auto st = ::protocyte::write_string_field(writer, 1u, entry.key.view()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                }
                if (const auto st = ::protocyte::write_enum_field(writer, 2u, entry.value); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
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
            if (has_double_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::double_value)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::double_value)));
                }
                total = *st_size;
            }
            if (has_float_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::float_value)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::float_value)));
                }
                total = *st_size;
            }
            if (has_int64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::int64_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(int64_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::int64_value)));
                }
                total = *st_size;
            }
            if (has_uint64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::uint64_value)) +
                               ::protocyte::varint_size(uint64_value_));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::uint64_value)));
                }
                total = *st_size;
            }
            if (has_int32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::int32_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(int32_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::int32_value)));
                }
                total = *st_size;
            }
            if (has_fixed64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::fixed64_value)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::fixed64_value)));
                }
                total = *st_size;
            }
            if (has_fixed32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::fixed32_value)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::fixed32_value)));
                }
                total = *st_size;
            }
            if (has_bool_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::bool_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(bool_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::bool_value)));
                }
                total = *st_size;
            }
            if (has_string_value_) {
                const auto field_size_string_value = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::string_value), string_value_.size());
                if (!field_size_string_value) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_string_value.error(), static_cast<::protocyte::u32>(FieldNumber::string_value)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_string_value);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::string_value)));
                }
                total = *st_size;
            }
            if (has_bytes_value_) {
                const auto field_size_bytes_value = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::bytes_value), bytes_value_.size());
                if (!field_size_bytes_value) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_bytes_value.error(), static_cast<::protocyte::u32>(FieldNumber::bytes_value)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_bytes_value);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::bytes_value)));
                }
                total = *st_size;
            }
            if (has_uint32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::uint32_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(uint32_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::uint32_value)));
                }
                total = *st_size;
            }
            if (has_enum_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::enum_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(enum_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::enum_value)));
                }
                total = *st_size;
            }
            if (has_sfixed32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sfixed32_value)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::sfixed32_value)));
                }
                total = *st_size;
            }
            if (has_sfixed64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sfixed64_value)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::sfixed64_value)));
                }
                total = *st_size;
            }
            if (has_sint32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sint32_value)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag32(sint32_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::sint32_value)));
                }
                total = *st_size;
            }
            if (has_sint64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sint64_value)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag64(sint64_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::sint64_value)));
                }
                total = *st_size;
            }
            if (has_implicit_enum_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(implicit_enum_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value)));
                }
                total = *st_size;
            }
            if (!enum_values_.empty()) {
                ::protocyte::usize packed_size_enum_values {};
                for (const auto &enum_values_value : enum_values_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_enum_values,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(enum_values_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::enum_values)));
                    }
                    packed_size_enum_values = *st_size;
                }
                const auto field_size_enum_values = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::enum_values), packed_size_enum_values);
                if (!field_size_enum_values) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_enum_values.error(), static_cast<::protocyte::u32>(FieldNumber::enum_values)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_enum_values);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::enum_values)));
                }
                total = *st_size;
            }
            for (const auto &entry : enum_by_name_) {
                ::protocyte::usize entry_payload {};
                {
                    const auto field_size_key = ::protocyte::length_delimited_field_size(1u, entry.key.size());
                    if (!field_size_key) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            field_size_key.error(), static_cast<::protocyte::u32>(FieldNumber::enum_by_name)));
                    }
                    const auto st_size = ::protocyte::add_size(entry_payload, *field_size_key);
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::enum_by_name)));
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(2u) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(::protocyte::with_field(
                            st_size.error(), static_cast<::protocyte::u32>(FieldNumber::enum_by_name)));
                    }
                    entry_payload = *st_size;
                }
                const auto field_size_enum_by_name = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::enum_by_name), entry_payload);
                if (!field_size_enum_by_name) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_enum_by_name.error(), static_cast<::protocyte::u32>(FieldNumber::enum_by_name)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_enum_by_name);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::enum_by_name)));
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
            if (has_enum_value_) {
                if (enum_value_ != 5 && enum_value_ != 9) {
                    return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::enum_value));
                }
            }
            if (has_implicit_enum_value_) {
                if (implicit_enum_value_ != 5 && implicit_enum_value_ != 9) {
                    return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value));
                }
            }
            for (const auto enum_values_value : enum_values_) {
                if (enum_values_value != 5 && enum_values_value != 9) {
                    return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::enum_values));
                }
            }
            for (const auto &enum_by_name_entry : enum_by_name_) {
                if (enum_by_name_entry.value != 0 && enum_by_name_entry.value != 9) {
                    return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                }
            }
            if (const auto st = string_value_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {},
                                               static_cast<::protocyte::u32>(FieldNumber::string_value));
            }
            for (const auto &enum_by_name_entry : enum_by_name_) {
                if (const auto st = enum_by_name_entry.key.validate(); !st) {
                    return ::protocyte::unexpected(st.error().code, {},
                                                   static_cast<::protocyte::u32>(FieldNumber::enum_by_name));
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::f64 double_value_ {};
        bool has_double_value_ {};
        ::protocyte::f32 float_value_ {};
        bool has_float_value_ {};
        ::protocyte::i64 int64_value_ {};
        bool has_int64_value_ {};
        ::protocyte::u64 uint64_value_ {};
        bool has_uint64_value_ {};
        ::protocyte::i32 int32_value_ {};
        bool has_int32_value_ {};
        ::protocyte::u64 fixed64_value_ {};
        bool has_fixed64_value_ {};
        ::protocyte::u32 fixed32_value_ {};
        bool has_fixed32_value_ {};
        bool bool_value_ {};
        bool has_bool_value_ {};
        typename Config::String string_value_;
        bool has_string_value_ {};
        typename Config::Bytes bytes_value_;
        bool has_bytes_value_ {};
        ::protocyte::u32 uint32_value_ {};
        bool has_uint32_value_ {};
        ::protocyte::i32 enum_value_ {};
        bool has_enum_value_ {};
        ::protocyte::i32 sfixed32_value_ {};
        bool has_sfixed32_value_ {};
        ::protocyte::i64 sfixed64_value_ {};
        bool has_sfixed64_value_ {};
        ::protocyte::i32 sint32_value_ {};
        bool has_sint32_value_ {};
        ::protocyte::i64 sint64_value_ {};
        bool has_sint64_value_ {};
        ::protocyte::i32 implicit_enum_value_ {};
        bool has_implicit_enum_value_ {};
        typename Config::template Vector<::protocyte::i32> enum_values_;
        typename Config::template Map<typename Config::String, ::protocyte::i32> enum_by_name_;
    };

    template<typename Config> struct OneofShadowingValue {
        using Context = typename Config::Context;
        enum struct ValueCase : ::protocyte::u32 {
            none = 0u,
            bool_value = 1u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            bool_value = 1u,
        };

        explicit OneofShadowingValue(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static OneofShadowingValue create(Context &ctx) noexcept { return OneofShadowingValue {ctx}; }
        Context *context() const noexcept { return ctx_; }
        OneofShadowingValue(OneofShadowingValue &&other) noexcept:
            ctx_ {other.ctx_}, unknown_fields_ {::protocyte::move(other.unknown_fields_)} {
            switch (other.value_case_) {
                case ValueCase::bool_value: {
                    new (&value_.bool_value_) bool {other.value_.bool_value_};
                    value_case_ = ValueCase::bool_value;
                    break;
                }
                case ValueCase::none:
                default: {
                    break;
                }
            }
            other.clear_value();
        }
        OneofShadowingValue &operator=(OneofShadowingValue &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_value();
            ctx_ = other.ctx_;
            unknown_fields_ = ::protocyte::move(other.unknown_fields_);
            switch (other.value_case_) {
                case ValueCase::bool_value: {
                    new (&value_.bool_value_) bool {other.value_.bool_value_};
                    value_case_ = ValueCase::bool_value;
                    break;
                }
                case ValueCase::none:
                default: {
                    break;
                }
            }
            other.clear_value();
            return *this;
        }
        ~OneofShadowingValue() noexcept { clear_value(); }
        OneofShadowingValue(const OneofShadowingValue &) = delete;
        OneofShadowingValue &operator=(const OneofShadowingValue &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const OneofShadowingValue &source) noexcept {
            if (this == &source) {
                return {};
            }
            OneofShadowingValue staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const OneofShadowingValue &source,
                                      OneofShadowingValue &staging_message) noexcept {
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

        ::protocyte::Result<OneofShadowingValue> clone() const noexcept {
            auto output = OneofShadowingValue::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(OneofShadowingValue &output) const noexcept {
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
        static void reset_for_reuse_(OneofShadowingValue &value, Context &ctx) noexcept {
            value.~OneofShadowingValue();
            new (&value) OneofShadowingValue {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const OneofShadowingValue &source) noexcept {
            switch (source.value_case_) {
                case ValueCase::bool_value: {
                    set_bool_value(source.bool_value());
                    break;
                }
                case ValueCase::none:
                default: {
                    clear_value();
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

        constexpr ValueCase value_case() const noexcept { return value_case_; }
        void clear_value() noexcept {
            switch (value_case_) {
                case ValueCase::bool_value: {
                    break;
                }
                case ValueCase::none:
                default: {
                    break;
                }
            }
            value_case_ = ValueCase::none;
        }

        constexpr bool has_bool_value() const noexcept { return value_case_ == ValueCase::bool_value; }
        constexpr bool bool_value() const noexcept { return has_bool_value() ? value_.bool_value_ : false; }
        void set_bool_value(const bool value) noexcept {
            clear_value();
            new (&value_.bool_value_) bool {value};
            value_case_ = ValueCase::bool_value;
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<OneofShadowingValue> parse(Context &ctx, Reader &reader) noexcept {
            auto output = OneofShadowingValue::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<OneofShadowingValue> parse(Context &ctx,
                                                              ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, OneofShadowingValue &output) noexcept {
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
                case FieldNumber::bool_value: {
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
                    bool bool_value_value {};
                    {
                        const auto decoded_bool_value = ::protocyte::read_bool_field(reader, wire_type, field_number);
                        if (!decoded_bool_value) {
                            return decoded_bool_value.status();
                        }
                        bool_value_value = *decoded_bool_value;
                    }
                    clear_value();
                    new (&value_.bool_value_) bool {::protocyte::move(bool_value_value)};
                    value_case_ = ValueCase::bool_value;
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
            if (value_case_ == ValueCase::bool_value) {
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bool_value), value_.bool_value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::bool_value));
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
            if (value_case_ == ValueCase::bool_value) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::bool_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(value_.bool_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::bool_value)));
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
        ValueCase value_case_ {ValueCase::none};
        union ValueStorage {
            ValueStorage() noexcept {}
            ~ValueStorage() noexcept {}
            bool bool_value_;
        } value_;
    };

} // namespace test::required

#endif // PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP
