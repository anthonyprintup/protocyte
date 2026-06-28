#pragma once

#ifndef PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP
#define PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP

#include <protocyte/runtime/runtime.hpp>

namespace test::required {

    template<typename Config = ::protocyte::DefaultConfig> struct RequiredChild;
    template<typename Config = ::protocyte::DefaultConfig> struct RequiredParent;

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
        template<class Value>::protocyte::Status set_note(const Value &value) noexcept
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
        template<class Value>::protocyte::Status set_note(const Value &value) noexcept
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
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number, child_value);
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
                                ::protocyte::read_message<Config>(*ctx_, reader, field_number, value)
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

} // namespace test::required

#endif // PROTOCYTE_GENERATED_PROTO2_REQUIRED_PROTO_4DC6EBF259D4_HPP
