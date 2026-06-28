#pragma once

#ifndef PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP
#define PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP

#include <protocyte/runtime/runtime.hpp>

namespace test::required {

    enum struct Proto2DefaultMode : ::protocyte::i32 {
        PROTO2_DEFAULT_MODE_UNKNOWN = 5,
        PROTO2_DEFAULT_MODE_READY = 9,
    };

    template<typename Config = ::protocyte::DefaultConfig> struct RequiredChild;
    template<typename Config = ::protocyte::DefaultConfig> struct RequiredParent;
    template<typename Config = ::protocyte::DefaultConfig> struct Proto2ArrayDefaults;
    template<typename Config = ::protocyte::DefaultConfig> struct Proto2DefaultValues;

    template<typename Config> struct RequiredChild {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            id = 1u,
            note = 2u,
        };

        explicit RequiredChild(Context &ctx) noexcept: ctx_ {&ctx}, note_ {&ctx} {}

        static ::protocyte::Result<RequiredChild> create(Context &ctx) noexcept { return RequiredChild {ctx}; }
        Context *context() const noexcept { return ctx_; }
        RequiredChild(RequiredChild &&) noexcept = default;
        RequiredChild &operator=(RequiredChild &&) noexcept = default;
        RequiredChild(const RequiredChild &) = delete;
        RequiredChild &operator=(const RequiredChild &) = delete;

        ::protocyte::Status copy_from(const RequiredChild &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (other.has_id()) {
                if (const auto st = set_id(other.id()); !st) {
                    return st;
                }
            } else {
                clear_id();
            }
            if (other.has_note()) {
                if (const auto st = set_note(other.note()); !st) {
                    return st;
                }
            } else {
                clear_note();
            }
            return {};
        }

        ::protocyte::Result<RequiredChild> clone() const noexcept {
            auto out = RequiredChild::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        constexpr ::protocyte::i32 id() const noexcept { return id_; }
        constexpr bool has_id() const noexcept { return has_id_; }
        ::protocyte::Status set_id(const ::protocyte::i32 value) noexcept {
            id_ = value;
            has_id_ = true;
            return {};
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
        template<class Value> auto set_note(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            note_ = ::protocyte::move(temp);
            has_note_ = true;
            return {};
        }
        template<class Value> auto set_note(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            note_ = ::protocyte::move(temp);
            has_note_ = true;
            return {};
        }
        void clear_note() noexcept {
            note_.clear();
            has_note_ = false;
        }

        template<typename Reader>
        static ::protocyte::Result<RequiredChild> parse(Context &ctx, Reader &reader) noexcept {
            auto out = RequiredChild::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            if (const auto st = merge_partial_from(reader); !st) {
                return st;
            }
            return validate();
        }

        template<typename Reader>::protocyte::Status merge_partial_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::id: {
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { id_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_id_ = true;
                        break;
                    }
                    case FieldNumber::note: {
                        if (const auto st =
                                ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, note_);
                            !st) {
                            return st;
                        }
                        has_note_ = true;
                        break;
                    }
                    default: {
                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                            !st) {
                            return st;
                        }
                        break;
                    }
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (has_id_) {
                if (const auto st =
                        ::protocyte::write_int32_field(writer, static_cast<::protocyte::u32>(FieldNumber::id), id_);
                    !st) {
                    return st;
                }
            }
            if (has_note_) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::note), note_.view());
                    !st) {
                    return st;
                }
            }
            return {};
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
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_note_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::note), note_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            return total;
        }

        ::protocyte::Status validate() const noexcept {
            if (!has_id()) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::id));
            }
            return {};
        }
    protected:
        Context *ctx_;
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

        explicit RequiredParent(Context &ctx) noexcept: ctx_ {&ctx}, children_ {&ctx} {}

        static ::protocyte::Result<RequiredParent> create(Context &ctx) noexcept { return RequiredParent {ctx}; }
        Context *context() const noexcept { return ctx_; }
        RequiredParent(RequiredParent &&) noexcept = default;
        RequiredParent &operator=(RequiredParent &&) noexcept = default;
        RequiredParent(const RequiredParent &) = delete;
        RequiredParent &operator=(const RequiredParent &) = delete;

        ::protocyte::Status copy_from(const RequiredParent &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (other.has_child()) {
                if (const auto st = ensure_child().and_then(
                        [&](auto &ensured) noexcept { return ensured.copy_from(*other.child()); });
                    !st) {
                    return st;
                }
            } else {
                clear_child();
            }
            if (const auto st = mutable_children().copy_from(other.children()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<RequiredParent> clone() const noexcept {
            auto out = RequiredParent::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        bool has_child() const noexcept { return child_.has_value(); }
        const ::test::required::RequiredChild<Config> *child() const noexcept {
            return has_child() ? child_.operator->() : nullptr;
        }
        ::protocyte::Result<::test::required::RequiredChild<Config> &> ensure_child() noexcept {
            if (child_.has_value()) {
                return *child_;
            }
            return child_.emplace(*ctx_).transform(
                [this]() noexcept -> ::test::required::RequiredChild<Config> & { return *child_; });
        }
        void clear_child() noexcept { child_.reset(); }

        const typename Config::template Vector<::test::required::RequiredChild<Config>> &children() const noexcept {
            return children_;
        }
        typename Config::template Vector<::test::required::RequiredChild<Config>> &mutable_children() noexcept {
            return children_;
        }
        void clear_children() noexcept { children_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<RequiredParent> parse(Context &ctx, Reader &reader) noexcept {
            auto out = RequiredParent::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            if (const auto st = merge_partial_from(reader); !st) {
                return st;
            }
            return validate();
        }

        template<typename Reader>::protocyte::Status merge_partial_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::child: {
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
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::required::RequiredChild<Config> value {*ctx_};
                        if (const auto st =
                                ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number, value)
                                    .and_then([&]() noexcept { return children_.push_back(::protocyte::move(value)); });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    default: {
                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                            !st) {
                            return st;
                        }
                        break;
                    }
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (child_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::child), *child_);
                    !st) {
                    return st;
                }
            }
            for (const auto &children_value : children_) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::children), children_value);
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (const auto st = validate(); !st) {
                return ::protocyte::unexpected(st.error());
            }
            ::protocyte::usize total {};
            if (child_.has_value()) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::child), *child_)
                        .and_then([&](const ::protocyte::usize nested_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, nested_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto &children_value : children_) {
                const auto st_size = ::protocyte::message_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::children), children_value)
                                         .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, nested_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            return total;
        }

        ::protocyte::Status validate() const noexcept {
            if (child_.has_value()) {
                if (const auto st = (*child_).validate(); !st) {
                    return st;
                }
            }
            for (const auto &children_value : children_) {
                if (const auto st = children_value.validate(); !st) {
                    return st;
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        typename Config::template Optional<::test::required::RequiredChild<Config>> child_;
        typename Config::template Vector<::test::required::RequiredChild<Config>> children_;
    };

    template<typename Config> struct Proto2ArrayDefaults {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            bounded_bytes = 1u,
            fixed_bytes = 2u,
        };

        explicit Proto2ArrayDefaults(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<Proto2ArrayDefaults> create(Context &ctx) noexcept {
            return Proto2ArrayDefaults {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        Proto2ArrayDefaults(Proto2ArrayDefaults &&) noexcept = default;
        Proto2ArrayDefaults &operator=(Proto2ArrayDefaults &&) noexcept = default;
        Proto2ArrayDefaults(const Proto2ArrayDefaults &) = delete;
        Proto2ArrayDefaults &operator=(const Proto2ArrayDefaults &) = delete;

        ::protocyte::Status copy_from(const Proto2ArrayDefaults &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (other.has_bounded_bytes()) {
                if (const auto st = set_bounded_bytes(other.bounded_bytes()); !st) {
                    return st;
                }
            } else {
                clear_bounded_bytes();
            }
            if (other.has_fixed_bytes()) {
                if (const auto st = set_fixed_bytes(other.fixed_bytes()); !st) {
                    return st;
                }
            } else {
                clear_fixed_bytes();
            }
            return {};
        }

        ::protocyte::Result<Proto2ArrayDefaults> clone() const noexcept {
            auto out = Proto2ArrayDefaults::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
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
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (size > 8u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, {});
            }
            if (!has_bounded_bytes_) {
                const auto default_value =
                    ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("abc"), 3u};
                if (default_value.size() > ctx_->limits.max_string_bytes) {
                    return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
                }
                if (const auto st = bounded_bytes_.assign(default_value); !st) {
                    return st;
                }
            }
            if (const auto st = bounded_bytes_.resize(size); !st) {
                return st;
            }
            has_bounded_bytes_ = true;
            return {};
        }
        ::protocyte::Status resize_bounded_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = bounded_bytes_.resize_for_overwrite(size); !st) {
                return st;
            }
            has_bounded_bytes_ = true;
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_bounded_bytes() noexcept {
            if (!has_bounded_bytes_) {
                const auto default_value =
                    ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("abc"), 3u};
                if (default_value.size() > ctx_->limits.max_string_bytes) {
                    return ::protocyte::Span<::protocyte::u8> {};
                }
                if (const auto st = bounded_bytes_.assign(default_value); !st) {
                    return ::protocyte::Span<::protocyte::u8> {};
                }
            }
            has_bounded_bytes_ = true;
            return bounded_bytes_.mutable_view();
        }
        template<class Value> auto set_bounded_bytes(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = bounded_bytes_.assign(*view); !st) {
                return st;
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
            if (ctx_->limits.max_string_bytes < 3u) {
                return ::protocyte::Span<::protocyte::u8> {};
            }
            if (!has_fixed_bytes()) {
                const auto default_value =
                    ::protocyte::Span<const ::protocyte::u8> {reinterpret_cast<const ::protocyte::u8 *>("xyz"), 3u};
                if (default_value.size() > ctx_->limits.max_string_bytes) {
                    return ::protocyte::Span<::protocyte::u8> {};
                }
                if (const auto st = fixed_bytes_.assign(default_value); !st) {
                    return ::protocyte::Span<::protocyte::u8> {};
                }
            }
            return fixed_bytes_.mutable_view();
        }
        ::protocyte::Status resize_fixed_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            return fixed_bytes_.resize_for_overwrite(size);
        }
        template<class Value> auto set_fixed_bytes(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            return fixed_bytes_.assign(*view);
        }
        void clear_fixed_bytes() noexcept { fixed_bytes_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<Proto2ArrayDefaults> parse(Context &ctx, Reader &reader) noexcept {
            auto out = Proto2ArrayDefaults::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            if (const auto st = merge_partial_from(reader); !st) {
                return st;
            }
            return validate();
        }

        template<typename Reader>::protocyte::Status merge_partial_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::bounded_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (*len > ctx_->limits.max_string_bytes) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, reader.position(),
                                                           field_number);
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
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto len = ::protocyte::read_length_delimited_size(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (*len > ctx_->limits.max_string_bytes) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, reader.position(),
                                                           field_number);
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
                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                            !st) {
                            return st;
                        }
                        break;
                    }
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (has_bounded_bytes_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bounded_bytes), bounded_bytes_.view());
                    !st) {
                    return st;
                }
            }
            if (fixed_bytes_.has_value()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed_bytes), fixed_bytes_.view());
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (const auto st = validate(); !st) {
                return ::protocyte::unexpected(st.error());
            }
            ::protocyte::usize total {};
            if (has_bounded_bytes_) {
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::bounded_bytes),
                                                             bounded_bytes_.size())
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (fixed_bytes_.has_value()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::fixed_bytes), fixed_bytes_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            return total;
        }

        ::protocyte::Status validate() const noexcept { return {}; }
    protected:
        Context *ctx_;
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
        };

        explicit Proto2DefaultValues(Context &ctx) noexcept: ctx_ {&ctx}, string_value_ {&ctx}, bytes_value_ {&ctx} {}

        static ::protocyte::Result<Proto2DefaultValues> create(Context &ctx) noexcept {
            return Proto2DefaultValues {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        Proto2DefaultValues(Proto2DefaultValues &&) noexcept = default;
        Proto2DefaultValues &operator=(Proto2DefaultValues &&) noexcept = default;
        Proto2DefaultValues(const Proto2DefaultValues &) = delete;
        Proto2DefaultValues &operator=(const Proto2DefaultValues &) = delete;

        ::protocyte::Status copy_from(const Proto2DefaultValues &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (other.has_double_value()) {
                if (const auto st = set_double_value(other.double_value()); !st) {
                    return st;
                }
            } else {
                clear_double_value();
            }
            if (other.has_float_value()) {
                if (const auto st = set_float_value(other.float_value()); !st) {
                    return st;
                }
            } else {
                clear_float_value();
            }
            if (other.has_int64_value()) {
                if (const auto st = set_int64_value(other.int64_value()); !st) {
                    return st;
                }
            } else {
                clear_int64_value();
            }
            if (other.has_uint64_value()) {
                if (const auto st = set_uint64_value(other.uint64_value()); !st) {
                    return st;
                }
            } else {
                clear_uint64_value();
            }
            if (other.has_int32_value()) {
                if (const auto st = set_int32_value(other.int32_value()); !st) {
                    return st;
                }
            } else {
                clear_int32_value();
            }
            if (other.has_fixed64_value()) {
                if (const auto st = set_fixed64_value(other.fixed64_value()); !st) {
                    return st;
                }
            } else {
                clear_fixed64_value();
            }
            if (other.has_fixed32_value()) {
                if (const auto st = set_fixed32_value(other.fixed32_value()); !st) {
                    return st;
                }
            } else {
                clear_fixed32_value();
            }
            if (other.has_bool_value()) {
                if (const auto st = set_bool_value(other.bool_value()); !st) {
                    return st;
                }
            } else {
                clear_bool_value();
            }
            if (other.has_string_value()) {
                if (const auto st = set_string_value(other.string_value()); !st) {
                    return st;
                }
            } else {
                clear_string_value();
            }
            if (other.has_bytes_value()) {
                if (const auto st = set_bytes_value(other.bytes_value()); !st) {
                    return st;
                }
            } else {
                clear_bytes_value();
            }
            if (other.has_uint32_value()) {
                if (const auto st = set_uint32_value(other.uint32_value()); !st) {
                    return st;
                }
            } else {
                clear_uint32_value();
            }
            if (other.has_enum_value()) {
                if (const auto st = set_enum_value_raw(other.enum_value_raw()); !st) {
                    return st;
                }
            } else {
                clear_enum_value();
            }
            if (other.has_sfixed32_value()) {
                if (const auto st = set_sfixed32_value(other.sfixed32_value()); !st) {
                    return st;
                }
            } else {
                clear_sfixed32_value();
            }
            if (other.has_sfixed64_value()) {
                if (const auto st = set_sfixed64_value(other.sfixed64_value()); !st) {
                    return st;
                }
            } else {
                clear_sfixed64_value();
            }
            if (other.has_sint32_value()) {
                if (const auto st = set_sint32_value(other.sint32_value()); !st) {
                    return st;
                }
            } else {
                clear_sint32_value();
            }
            if (other.has_sint64_value()) {
                if (const auto st = set_sint64_value(other.sint64_value()); !st) {
                    return st;
                }
            } else {
                clear_sint64_value();
            }
            if (other.has_implicit_enum_value()) {
                if (const auto st = set_implicit_enum_value_raw(other.implicit_enum_value_raw()); !st) {
                    return st;
                }
            } else {
                clear_implicit_enum_value();
            }
            return {};
        }

        ::protocyte::Result<Proto2DefaultValues> clone() const noexcept {
            auto out = Proto2DefaultValues::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        constexpr ::protocyte::f64 double_value() const noexcept { return has_double_value_ ? double_value_ : 1.5; }
        constexpr bool has_double_value() const noexcept { return has_double_value_; }
        ::protocyte::Status set_double_value(const ::protocyte::f64 value) noexcept {
            double_value_ = value;
            has_double_value_ = true;
            return {};
        }
        constexpr void clear_double_value() noexcept {
            double_value_ = {};
            has_double_value_ = false;
        }

        constexpr ::protocyte::f32 float_value() const noexcept { return has_float_value_ ? float_value_ : -2.25f; }
        constexpr bool has_float_value() const noexcept { return has_float_value_; }
        ::protocyte::Status set_float_value(const ::protocyte::f32 value) noexcept {
            float_value_ = value;
            has_float_value_ = true;
            return {};
        }
        constexpr void clear_float_value() noexcept {
            float_value_ = {};
            has_float_value_ = false;
        }

        constexpr ::protocyte::i64 int64_value() const noexcept {
            return has_int64_value_ ? int64_value_ : -1234567890123ll;
        }
        constexpr bool has_int64_value() const noexcept { return has_int64_value_; }
        ::protocyte::Status set_int64_value(const ::protocyte::i64 value) noexcept {
            int64_value_ = value;
            has_int64_value_ = true;
            return {};
        }
        constexpr void clear_int64_value() noexcept {
            int64_value_ = {};
            has_int64_value_ = false;
        }

        constexpr ::protocyte::u64 uint64_value() const noexcept {
            return has_uint64_value_ ? uint64_value_ : 1234567890123ull;
        }
        constexpr bool has_uint64_value() const noexcept { return has_uint64_value_; }
        ::protocyte::Status set_uint64_value(const ::protocyte::u64 value) noexcept {
            uint64_value_ = value;
            has_uint64_value_ = true;
            return {};
        }
        constexpr void clear_uint64_value() noexcept {
            uint64_value_ = {};
            has_uint64_value_ = false;
        }

        constexpr ::protocyte::i32 int32_value() const noexcept { return has_int32_value_ ? int32_value_ : -12345; }
        constexpr bool has_int32_value() const noexcept { return has_int32_value_; }
        ::protocyte::Status set_int32_value(const ::protocyte::i32 value) noexcept {
            int32_value_ = value;
            has_int32_value_ = true;
            return {};
        }
        constexpr void clear_int32_value() noexcept {
            int32_value_ = {};
            has_int32_value_ = false;
        }

        constexpr ::protocyte::u64 fixed64_value() const noexcept {
            return has_fixed64_value_ ? fixed64_value_ : 12345678901234ull;
        }
        constexpr bool has_fixed64_value() const noexcept { return has_fixed64_value_; }
        ::protocyte::Status set_fixed64_value(const ::protocyte::u64 value) noexcept {
            fixed64_value_ = value;
            has_fixed64_value_ = true;
            return {};
        }
        constexpr void clear_fixed64_value() noexcept {
            fixed64_value_ = {};
            has_fixed64_value_ = false;
        }

        constexpr ::protocyte::u32 fixed32_value() const noexcept {
            return has_fixed32_value_ ? fixed32_value_ : 123456789u;
        }
        constexpr bool has_fixed32_value() const noexcept { return has_fixed32_value_; }
        ::protocyte::Status set_fixed32_value(const ::protocyte::u32 value) noexcept {
            fixed32_value_ = value;
            has_fixed32_value_ = true;
            return {};
        }
        constexpr void clear_fixed32_value() noexcept {
            fixed32_value_ = {};
            has_fixed32_value_ = false;
        }

        constexpr bool bool_value() const noexcept { return has_bool_value_ ? bool_value_ : true; }
        constexpr bool has_bool_value() const noexcept { return has_bool_value_; }
        ::protocyte::Status set_bool_value(const bool value) noexcept {
            bool_value_ = value;
            has_bool_value_ = true;
            return {};
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
        template<class Value> auto set_string_value(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            string_value_ = ::protocyte::move(temp);
            has_string_value_ = true;
            return {};
        }
        template<class Value> auto set_string_value(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
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
        template<class Value> auto set_bytes_value(const Value &value) noexcept -> ::protocyte::Status
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
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
        ::protocyte::Status set_uint32_value(const ::protocyte::u32 value) noexcept {
            uint32_value_ = value;
            has_uint32_value_ = true;
            return {};
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
        ::protocyte::Status set_sfixed32_value(const ::protocyte::i32 value) noexcept {
            sfixed32_value_ = value;
            has_sfixed32_value_ = true;
            return {};
        }
        constexpr void clear_sfixed32_value() noexcept {
            sfixed32_value_ = {};
            has_sfixed32_value_ = false;
        }

        constexpr ::protocyte::i64 sfixed64_value() const noexcept {
            return has_sfixed64_value_ ? sfixed64_value_ : -9876543210ll;
        }
        constexpr bool has_sfixed64_value() const noexcept { return has_sfixed64_value_; }
        ::protocyte::Status set_sfixed64_value(const ::protocyte::i64 value) noexcept {
            sfixed64_value_ = value;
            has_sfixed64_value_ = true;
            return {};
        }
        constexpr void clear_sfixed64_value() noexcept {
            sfixed64_value_ = {};
            has_sfixed64_value_ = false;
        }

        constexpr ::protocyte::i32 sint32_value() const noexcept { return has_sint32_value_ ? sint32_value_ : -23456; }
        constexpr bool has_sint32_value() const noexcept { return has_sint32_value_; }
        ::protocyte::Status set_sint32_value(const ::protocyte::i32 value) noexcept {
            sint32_value_ = value;
            has_sint32_value_ = true;
            return {};
        }
        constexpr void clear_sint32_value() noexcept {
            sint32_value_ = {};
            has_sint32_value_ = false;
        }

        constexpr ::protocyte::i64 sint64_value() const noexcept {
            return has_sint64_value_ ? sint64_value_ : -123456789012ll;
        }
        constexpr bool has_sint64_value() const noexcept { return has_sint64_value_; }
        ::protocyte::Status set_sint64_value(const ::protocyte::i64 value) noexcept {
            sint64_value_ = value;
            has_sint64_value_ = true;
            return {};
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

        template<typename Reader>
        static ::protocyte::Result<Proto2DefaultValues> parse(Context &ctx, Reader &reader) noexcept {
            auto out = Proto2DefaultValues::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            if (const auto st = merge_partial_from(reader); !st) {
                return st;
            }
            return validate();
        }

        template<typename Reader>::protocyte::Status merge_partial_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::double_value: {
                        if (const auto st =
                                ::protocyte::read_double_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { double_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_double_value_ = true;
                        break;
                    }
                    case FieldNumber::float_value: {
                        if (const auto st =
                                ::protocyte::read_float_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { float_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_float_value_ = true;
                        break;
                    }
                    case FieldNumber::int64_value: {
                        if (const auto st =
                                ::protocyte::read_int64_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { int64_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_int64_value_ = true;
                        break;
                    }
                    case FieldNumber::uint64_value: {
                        if (const auto st =
                                ::protocyte::read_uint64_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { uint64_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_uint64_value_ = true;
                        break;
                    }
                    case FieldNumber::int32_value: {
                        if (const auto st =
                                ::protocyte::read_int32_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { int32_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_int32_value_ = true;
                        break;
                    }
                    case FieldNumber::fixed64_value: {
                        if (const auto st =
                                ::protocyte::read_fixed64_value_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { fixed64_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_fixed64_value_ = true;
                        break;
                    }
                    case FieldNumber::fixed32_value: {
                        if (const auto st =
                                ::protocyte::read_fixed32_value_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { fixed32_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_fixed32_value_ = true;
                        break;
                    }
                    case FieldNumber::bool_value: {
                        if (const auto st = ::protocyte::read_bool_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { bool_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_bool_value_ = true;
                        break;
                    }
                    case FieldNumber::string_value: {
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, string_value_);
                            !st) {
                            return st;
                        }
                        has_string_value_ = true;
                        break;
                    }
                    case FieldNumber::bytes_value: {
                        if (const auto st = ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type,
                                                                                  field_number, bytes_value_);
                            !st) {
                            return st;
                        }
                        has_bytes_value_ = true;
                        break;
                    }
                    case FieldNumber::uint32_value: {
                        if (const auto st =
                                ::protocyte::read_uint32_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { uint32_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_uint32_value_ = true;
                        break;
                    }
                    case FieldNumber::enum_value: {
                        if (const auto st = ::protocyte::read_enum_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { enum_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_enum_value_ = true;
                        break;
                    }
                    case FieldNumber::sfixed32_value: {
                        if (const auto st =
                                ::protocyte::read_sfixed32_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { sfixed32_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_sfixed32_value_ = true;
                        break;
                    }
                    case FieldNumber::sfixed64_value: {
                        if (const auto st =
                                ::protocyte::read_sfixed64_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { sfixed64_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_sfixed64_value_ = true;
                        break;
                    }
                    case FieldNumber::sint32_value: {
                        if (const auto st =
                                ::protocyte::read_sint32_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { sint32_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_sint32_value_ = true;
                        break;
                    }
                    case FieldNumber::sint64_value: {
                        if (const auto st =
                                ::protocyte::read_sint64_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { sint64_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_sint64_value_ = true;
                        break;
                    }
                    case FieldNumber::implicit_enum_value: {
                        if (const auto st =
                                ::protocyte::read_enum_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { implicit_enum_value_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_implicit_enum_value_ = true;
                        break;
                    }
                    default: {
                        if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number);
                            !st) {
                            return st;
                        }
                        break;
                    }
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (const auto st = validate(); !st) {
                return st;
            }
            if (has_double_value_) {
                if (const auto st = ::protocyte::write_double_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::double_value), double_value_);
                    !st) {
                    return st;
                }
            }
            if (has_float_value_) {
                if (const auto st = ::protocyte::write_float_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::float_value), float_value_);
                    !st) {
                    return st;
                }
            }
            if (has_int64_value_) {
                if (const auto st = ::protocyte::write_int64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::int64_value), int64_value_);
                    !st) {
                    return st;
                }
            }
            if (has_uint64_value_) {
                if (const auto st = ::protocyte::write_uint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::uint64_value), uint64_value_);
                    !st) {
                    return st;
                }
            }
            if (has_int32_value_) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::int32_value), int32_value_);
                    !st) {
                    return st;
                }
            }
            if (has_fixed64_value_) {
                if (const auto st = ::protocyte::write_fixed64_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed64_value), fixed64_value_);
                    !st) {
                    return st;
                }
            }
            if (has_fixed32_value_) {
                if (const auto st = ::protocyte::write_fixed32_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed32_value), fixed32_value_);
                    !st) {
                    return st;
                }
            }
            if (has_bool_value_) {
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bool_value), bool_value_);
                    !st) {
                    return st;
                }
            }
            if (has_string_value_) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::string_value), string_value_.view());
                    !st) {
                    return st;
                }
            }
            if (has_bytes_value_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bytes_value), bytes_value_.view());
                    !st) {
                    return st;
                }
            }
            if (has_uint32_value_) {
                if (const auto st = ::protocyte::write_uint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::uint32_value), uint32_value_);
                    !st) {
                    return st;
                }
            }
            if (has_enum_value_) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::enum_value), enum_value_);
                    !st) {
                    return st;
                }
            }
            if (has_sfixed32_value_) {
                if (const auto st = ::protocyte::write_sfixed32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sfixed32_value), sfixed32_value_);
                    !st) {
                    return st;
                }
            }
            if (has_sfixed64_value_) {
                if (const auto st = ::protocyte::write_sfixed64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sfixed64_value), sfixed64_value_);
                    !st) {
                    return st;
                }
            }
            if (has_sint32_value_) {
                if (const auto st = ::protocyte::write_sint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sint32_value), sint32_value_);
                    !st) {
                    return st;
                }
            }
            if (has_sint64_value_) {
                if (const auto st = ::protocyte::write_sint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sint64_value), sint64_value_);
                    !st) {
                    return st;
                }
            }
            if (has_implicit_enum_value_) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value), implicit_enum_value_);
                    !st) {
                    return st;
                }
            }
            return {};
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
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_float_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::float_value)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_int64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::int64_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(int64_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_uint64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::uint64_value)) +
                               ::protocyte::varint_size(uint64_value_));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_int32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::int32_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(int32_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_fixed64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::fixed64_value)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_fixed32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::fixed32_value)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_bool_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::bool_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(bool_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_string_value_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::string_value), string_value_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_bytes_value_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::bytes_value), bytes_value_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_uint32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::uint32_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(uint32_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_enum_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::enum_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(enum_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_sfixed32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sfixed32_value)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_sfixed64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sfixed64_value)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_sint32_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sint32_value)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag32(sint32_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_sint64_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sint64_value)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag64(sint64_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_implicit_enum_value_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::implicit_enum_value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(implicit_enum_value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            return total;
        }

        ::protocyte::Status validate() const noexcept { return {}; }
    protected:
        Context *ctx_;
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
    };

} // namespace test::required

#endif // PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP
