#pragma once

#ifndef PROTOCYTE_GENERATED_COMPAT_PROTO_HPP
#define PROTOCYTE_GENERATED_COMPAT_PROTO_HPP

#include <protocyte/runtime/runtime.hpp>

namespace protocyte_smoke::test::compat {

    enum struct EncodingMatrix_Mode : ::protocyte::i32 {
        MODE_UNSPECIFIED = 0,
        FIRST = 1,
        SECOND = 2,
    };

    template<typename Config = ::protocyte::DefaultConfig> struct EncodingMatrix_Inner;
    template<typename Config = ::protocyte::DefaultConfig> struct EncodingMatrix;

    template<typename Config> struct EncodingMatrix_Inner {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
            label = 2u,
        };

        explicit EncodingMatrix_Inner(Context &ctx) noexcept: ctx_ {&ctx}, label_ {&ctx} {}

        static ::protocyte::Result<EncodingMatrix_Inner> create(Context &ctx) noexcept {
            return ::protocyte::Result<EncodingMatrix_Inner>::ok(EncodingMatrix_Inner {ctx});
        }
        EncodingMatrix_Inner(EncodingMatrix_Inner &&) noexcept = default;
        EncodingMatrix_Inner &operator=(EncodingMatrix_Inner &&) noexcept = default;
        EncodingMatrix_Inner(const EncodingMatrix_Inner &) = delete;
        EncodingMatrix_Inner &operator=(const EncodingMatrix_Inner &) = delete;

        ::protocyte::Status copy_from(const EncodingMatrix_Inner &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_value(other.value()); !st) {
                return st;
            }
            if (const auto st = set_label(other.label()); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<EncodingMatrix_Inner> clone() const noexcept {
            auto out = EncodingMatrix_Inner::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<EncodingMatrix_Inner>::err(st.error());
            }
            return out;
        }

        constexpr ::protocyte::i32 value() const noexcept { return value_; }
        constexpr ::protocyte::Status set_value(const ::protocyte::i32 value) noexcept {
            value_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_value() noexcept { value_ = {}; }

        ::protocyte::ByteView label() const noexcept { return label_.view(); }
        typename Config::String &mutable_label() noexcept { return label_; }
        ::protocyte::Status set_label(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            label_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
        }
        void clear_label() noexcept { label_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<EncodingMatrix_Inner> parse(Context &ctx, Reader &reader) noexcept {
            auto out = EncodingMatrix_Inner::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<EncodingMatrix_Inner>::err(st.error());
            }
            return out;
        }

        template<typename Reader> RuntimeStatus merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::value: {
                        auto decoded = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        value_ = decoded.value();
                        break;
                    }
                    case FieldNumber::label: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), label_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    default: {
                        if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) {
                            return st;
                        }
                        break;
                    }
                }
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer &writer) const noexcept {
            if (value_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::value), value_);
                    !st) {
                    return st;
                }
            }
            if (!label_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::label),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, label_.view()); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (value_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::value)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(value_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!label_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::label)) +
                                    ::protocyte::varint_size(label_.size()) + label_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        ::protocyte::i32 value_ {};
        typename Config::String label_;
    };

    template<typename Config> struct EncodingMatrix {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
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
        };

        explicit EncodingMatrix(Context &ctx) noexcept:
            ctx_ {&ctx},
            f_string_ {&ctx},
            f_bytes_ {&ctx},
            r_int32_unpacked_ {&ctx},
            r_int32_packed_ {&ctx},
            r_double_ {&ctx},
            opt_string_ {&ctx} {}

        static ::protocyte::Result<EncodingMatrix> create(Context &ctx) noexcept {
            return ::protocyte::Result<EncodingMatrix>::ok(EncodingMatrix {ctx});
        }
        EncodingMatrix(EncodingMatrix &&other) noexcept:
            ctx_ {other.ctx_},
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
            opt_string_ {::protocyte::move(other.opt_string_)} {
            has_opt_int32_ = other.has_opt_int32_;
            has_opt_string_ = other.has_opt_string_;
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    new (&special_oneof.oneof_string)
                        typename Config::String {::protocyte::move(other.special_oneof.oneof_string)};
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    new (&special_oneof.oneof_int32)::protocyte::i32 {other.special_oneof.oneof_int32};
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    new (&special_oneof.oneof_nested) typename Config::template Optional<
                        ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {
                        ::protocyte::move(other.special_oneof.oneof_nested)};
                    special_oneof_case_ = Special_oneofCase::oneof_nested;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof.oneof_bytes)
                        typename Config::Bytes {::protocyte::move(other.special_oneof.oneof_bytes)};
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
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    new (&special_oneof.oneof_string)
                        typename Config::String {::protocyte::move(other.special_oneof.oneof_string)};
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    new (&special_oneof.oneof_int32)::protocyte::i32 {other.special_oneof.oneof_int32};
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    new (&special_oneof.oneof_nested) typename Config::template Optional<
                        ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {
                        ::protocyte::move(other.special_oneof.oneof_nested)};
                    special_oneof_case_ = Special_oneofCase::oneof_nested;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof.oneof_bytes)
                        typename Config::Bytes {::protocyte::move(other.special_oneof.oneof_bytes)};
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

        ::protocyte::Status copy_from(const EncodingMatrix &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_f_int32(other.f_int32()); !st) {
                return st;
            }
            if (const auto st = set_f_int64(other.f_int64()); !st) {
                return st;
            }
            if (const auto st = set_f_uint32(other.f_uint32()); !st) {
                return st;
            }
            if (const auto st = set_f_uint64(other.f_uint64()); !st) {
                return st;
            }
            if (const auto st = set_f_sint32(other.f_sint32()); !st) {
                return st;
            }
            if (const auto st = set_f_sint64(other.f_sint64()); !st) {
                return st;
            }
            if (const auto st = set_f_bool(other.f_bool()); !st) {
                return st;
            }
            if (const auto st = set_mode_raw(other.mode_raw()); !st) {
                return st;
            }
            if (const auto st = set_f_fixed32(other.f_fixed32()); !st) {
                return st;
            }
            if (const auto st = set_f_fixed64(other.f_fixed64()); !st) {
                return st;
            }
            if (const auto st = set_f_sfixed32(other.f_sfixed32()); !st) {
                return st;
            }
            if (const auto st = set_f_sfixed64(other.f_sfixed64()); !st) {
                return st;
            }
            if (const auto st = set_f_float(other.f_float()); !st) {
                return st;
            }
            if (const auto st = set_f_double(other.f_double()); !st) {
                return st;
            }
            if (const auto st = set_f_string(other.f_string()); !st) {
                return st;
            }
            if (const auto st = set_f_bytes(other.f_bytes()); !st) {
                return st;
            }
            if (other.has_nested()) {
                if (auto ensured = ensure_nested(); !ensured) {
                    return ensured.status();
                } else if (const auto st = ensured.value().get().copy_from(*other.nested()); !st) {
                    return st;
                }
            } else {
                clear_nested();
            }
            clear_r_int32_unpacked();
            for (::protocyte::usize i {}; i < other.r_int32_unpacked().size(); ++i) {
                if (const auto st = mutable_r_int32_unpacked().push_back(other.r_int32_unpacked()[i]); !st) {
                    return st;
                }
            }
            clear_r_int32_packed();
            for (::protocyte::usize i {}; i < other.r_int32_packed().size(); ++i) {
                if (const auto st = mutable_r_int32_packed().push_back(other.r_int32_packed()[i]); !st) {
                    return st;
                }
            }
            clear_r_double();
            for (::protocyte::usize i {}; i < other.r_double().size(); ++i) {
                if (const auto st = mutable_r_double().push_back(other.r_double()[i]); !st) {
                    return st;
                }
            }
            if (other.has_opt_int32()) {
                if (const auto st = set_opt_int32(other.opt_int32()); !st) {
                    return st;
                }
            } else {
                clear_opt_int32();
            }
            if (other.has_opt_string()) {
                if (const auto st = set_opt_string(other.opt_string()); !st) {
                    return st;
                }
            } else {
                clear_opt_string();
            }
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    if (const auto st = set_oneof_string(other.oneof_string()); !st) {
                        return st;
                    }
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    if (const auto st = set_oneof_int32(other.oneof_int32()); !st) {
                        return st;
                    }
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    if (auto ensured = ensure_oneof_nested(); !ensured) {
                        return ensured.status();
                    } else if (const auto st = ensured.value().get().copy_from(*other.oneof_nested()); !st) {
                        return st;
                    }
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    if (const auto st = set_oneof_bytes(other.oneof_bytes()); !st) {
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
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<EncodingMatrix> clone() const noexcept {
            auto out = EncodingMatrix::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<EncodingMatrix>::err(st.error());
            }
            return out;
        }

        constexpr Special_oneofCase special_oneof_case() const noexcept { return special_oneof_case_; }
        void clear_special_oneof() noexcept {
            switch (special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    destroy_at_(&special_oneof.oneof_string);
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    break;
                }
                case Special_oneofCase::oneof_nested: {
                    destroy_at_(&special_oneof.oneof_nested);
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    destroy_at_(&special_oneof.oneof_bytes);
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
        constexpr ::protocyte::Status set_f_int32(const ::protocyte::i32 value) noexcept {
            f_int32_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_int32() noexcept { f_int32_ = {}; }

        constexpr ::protocyte::i64 f_int64() const noexcept { return f_int64_; }
        constexpr ::protocyte::Status set_f_int64(const ::protocyte::i64 value) noexcept {
            f_int64_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_int64() noexcept { f_int64_ = {}; }

        constexpr ::protocyte::u32 f_uint32() const noexcept { return f_uint32_; }
        constexpr ::protocyte::Status set_f_uint32(const ::protocyte::u32 value) noexcept {
            f_uint32_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_uint32() noexcept { f_uint32_ = {}; }

        constexpr ::protocyte::u64 f_uint64() const noexcept { return f_uint64_; }
        constexpr ::protocyte::Status set_f_uint64(const ::protocyte::u64 value) noexcept {
            f_uint64_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_uint64() noexcept { f_uint64_ = {}; }

        constexpr ::protocyte::i32 f_sint32() const noexcept { return f_sint32_; }
        constexpr ::protocyte::Status set_f_sint32(const ::protocyte::i32 value) noexcept {
            f_sint32_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_sint32() noexcept { f_sint32_ = {}; }

        constexpr ::protocyte::i64 f_sint64() const noexcept { return f_sint64_; }
        constexpr ::protocyte::Status set_f_sint64(const ::protocyte::i64 value) noexcept {
            f_sint64_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_sint64() noexcept { f_sint64_ = {}; }

        constexpr bool f_bool() const noexcept { return f_bool_; }
        constexpr ::protocyte::Status set_f_bool(const bool value) noexcept {
            f_bool_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_bool() noexcept { f_bool_ = {}; }

        constexpr ::protocyte::i32 mode_raw() const noexcept { return mode_; }
        constexpr ::protocyte_smoke::test::compat::EncodingMatrix_Mode mode() const noexcept {
            return static_cast<::protocyte_smoke::test::compat::EncodingMatrix_Mode>(mode_);
        }
        constexpr ::protocyte::Status set_mode_raw(const ::protocyte::i32 value) noexcept {
            mode_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr ::protocyte::Status
        set_mode(const ::protocyte_smoke::test::compat::EncodingMatrix_Mode value) noexcept {
            return set_mode_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_mode() noexcept { mode_ = {}; }

        constexpr ::protocyte::u32 f_fixed32() const noexcept { return f_fixed32_; }
        constexpr ::protocyte::Status set_f_fixed32(const ::protocyte::u32 value) noexcept {
            f_fixed32_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_fixed32() noexcept { f_fixed32_ = {}; }

        constexpr ::protocyte::u64 f_fixed64() const noexcept { return f_fixed64_; }
        constexpr ::protocyte::Status set_f_fixed64(const ::protocyte::u64 value) noexcept {
            f_fixed64_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_fixed64() noexcept { f_fixed64_ = {}; }

        constexpr ::protocyte::i32 f_sfixed32() const noexcept { return f_sfixed32_; }
        constexpr ::protocyte::Status set_f_sfixed32(const ::protocyte::i32 value) noexcept {
            f_sfixed32_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_sfixed32() noexcept { f_sfixed32_ = {}; }

        constexpr ::protocyte::i64 f_sfixed64() const noexcept { return f_sfixed64_; }
        constexpr ::protocyte::Status set_f_sfixed64(const ::protocyte::i64 value) noexcept {
            f_sfixed64_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_sfixed64() noexcept { f_sfixed64_ = {}; }

        constexpr ::protocyte::f32 f_float() const noexcept { return f_float_; }
        constexpr ::protocyte::Status set_f_float(const ::protocyte::f32 value) noexcept {
            f_float_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_float() noexcept { f_float_ = {}; }

        constexpr ::protocyte::f64 f_double() const noexcept { return f_double_; }
        constexpr ::protocyte::Status set_f_double(const ::protocyte::f64 value) noexcept {
            f_double_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_double() noexcept { f_double_ = {}; }

        ::protocyte::ByteView f_string() const noexcept { return f_string_.view(); }
        typename Config::String &mutable_f_string() noexcept { return f_string_; }
        ::protocyte::Status set_f_string(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            f_string_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
        }
        void clear_f_string() noexcept { f_string_.clear(); }

        ::protocyte::ByteView f_bytes() const noexcept { return f_bytes_.view(); }
        typename Config::Bytes &mutable_f_bytes() noexcept { return f_bytes_; }
        ::protocyte::Status set_f_bytes(const ::protocyte::ByteView value) noexcept {
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            f_bytes_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
        }
        void clear_f_bytes() noexcept { f_bytes_.clear(); }

        bool has_nested() const noexcept { return nested_.has_value(); }
        const ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> *nested() const noexcept {
            return has_nested() ? &nested_.value() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>>
        ensure_nested() noexcept {
            if (!nested_.has_value()) {
                if (const auto st = nested_.emplace(*ctx_); !st) {
                    return ::protocyte::
                        Result<::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>>::err(
                            st.error());
                }
            }
            return ::protocyte::
                Result<::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>>::ok(
                    ::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {nested_.value()});
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
        ::protocyte::ByteView oneof_string() const noexcept {
            return has_oneof_string() ? special_oneof.oneof_string.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_oneof_string(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_string) typename Config::String {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_string;
            return ::protocyte::Status::ok();
        }

        constexpr bool has_oneof_int32() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_int32;
        }
        constexpr ::protocyte::i32 oneof_int32() const noexcept {
            return has_oneof_int32() ? special_oneof.oneof_int32 : 0;
        }
        ::protocyte::Status set_oneof_int32(const ::protocyte::i32 value) noexcept {
            clear_special_oneof();
            new (&special_oneof.oneof_int32)::protocyte::i32 {value};
            special_oneof_case_ = Special_oneofCase::oneof_int32;
            return ::protocyte::Status::ok();
        }

        constexpr bool has_oneof_nested() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_nested;
        }
        const ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config> *oneof_nested() const noexcept {
            return has_oneof_nested() && special_oneof.oneof_nested.has_value() ? &special_oneof.oneof_nested.value() :
                                                                                  nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>>
        ensure_oneof_nested() noexcept {
            if (!has_oneof_nested()) {
                clear_special_oneof();
                new (&special_oneof.oneof_nested) typename Config::template Optional<
                    ::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {};
            }
            special_oneof_case_ = Special_oneofCase::oneof_nested;
            if (!special_oneof.oneof_nested.has_value()) {
                if (const auto st = special_oneof.oneof_nested.emplace(*ctx_); !st) {
                    return ::protocyte::
                        Result<::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>>::err(
                            st.error());
                }
            }
            return ::protocyte::
                Result<::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>>::ok(
                    ::protocyte::Ref<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>> {
                        special_oneof.oneof_nested.value()});
        }

        constexpr bool has_oneof_bytes() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_bytes;
        }
        ::protocyte::ByteView oneof_bytes() const noexcept {
            return has_oneof_bytes() ? special_oneof.oneof_bytes.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_oneof_bytes(const ::protocyte::ByteView value) noexcept {
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_bytes) typename Config::Bytes {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_bytes;
            return ::protocyte::Status::ok();
        }

        constexpr ::protocyte::i32 opt_int32() const noexcept { return opt_int32_; }
        constexpr bool has_opt_int32() const noexcept { return has_opt_int32_; }
        constexpr ::protocyte::Status set_opt_int32(const ::protocyte::i32 value) noexcept {
            opt_int32_ = value;
            has_opt_int32_ = true;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_opt_int32() noexcept {
            opt_int32_ = {};
            has_opt_int32_ = false;
        }

        ::protocyte::ByteView opt_string() const noexcept { return opt_string_.view(); }
        bool has_opt_string() const noexcept { return has_opt_string_; }
        typename Config::String &mutable_opt_string() noexcept {
            has_opt_string_ = true;
            return opt_string_;
        }
        ::protocyte::Status set_opt_string(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            opt_string_ = ::protocyte::move(temp);
            has_opt_string_ = true;
            return ::protocyte::Status::ok();
        }
        void clear_opt_string() noexcept {
            opt_string_.clear();
            has_opt_string_ = false;
        }

        template<typename Reader>
        static ::protocyte::Result<EncodingMatrix> parse(Context &ctx, Reader &reader) noexcept {
            auto out = EncodingMatrix::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<EncodingMatrix>::err(st.error());
            }
            return out;
        }

        template<typename Reader> RuntimeStatus merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::f_int32: {
                        auto decoded = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_int32_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_int64: {
                        auto decoded = ::protocyte::read_int64_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_int64_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_uint32: {
                        auto decoded = ::protocyte::read_uint32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_uint32_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_uint64: {
                        auto decoded = ::protocyte::read_uint64_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_uint64_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_sint32: {
                        auto decoded = ::protocyte::read_sint32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_sint32_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_sint64: {
                        auto decoded = ::protocyte::read_sint64_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_sint64_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_bool: {
                        auto decoded = ::protocyte::read_bool_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_bool_ = decoded.value();
                        break;
                    }
                    case FieldNumber::mode: {
                        auto decoded = ::protocyte::read_enum_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        mode_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_fixed32: {
                        auto decoded = ::protocyte::read_fixed32_value_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_fixed32_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_fixed64: {
                        auto decoded = ::protocyte::read_fixed64_value_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_fixed64_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_sfixed32: {
                        auto decoded = ::protocyte::read_sfixed32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_sfixed32_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_sfixed64: {
                        auto decoded = ::protocyte::read_sfixed64_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_sfixed64_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_float: {
                        auto decoded = ::protocyte::read_float_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_float_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_double: {
                        auto decoded = ::protocyte::read_double_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        f_double_ = decoded.value();
                        break;
                    }
                    case FieldNumber::f_string: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), f_string_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_bytes<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), f_bytes_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_nested();
                        if (!ensured) {
                            return ensured.status();
                        }
                        ::protocyte::LimitedReader<Reader> sub {reader, static_cast<::protocyte::usize>(len.value())};
                        ::protocyte::ReaderRef sub_reader {sub};
                        if (const auto st = ensured.value().get().merge_from(sub_reader); !st) {
                            return st;
                        }
                        if (const auto st = sub.finish(); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::r_int32_unpacked: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                auto decoded = ::protocyte::read_int32(packed);
                                if (!decoded) {
                                    return decoded.status();
                                }
                                value = decoded.value();
                                if (const auto st = r_int32_unpacked_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        auto decoded = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        value = decoded.value();
                        if (const auto st = r_int32_unpacked_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::r_int32_packed: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                auto decoded = ::protocyte::read_int32(packed);
                                if (!decoded) {
                                    return decoded.status();
                                }
                                value = decoded.value();
                                if (const auto st = r_int32_packed_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        auto decoded = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        value = decoded.value();
                        if (const auto st = r_int32_packed_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::r_double: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::f64 value {};
                                auto decoded = ::protocyte::read_double(packed);
                                if (!decoded) {
                                    return decoded.status();
                                }
                                value = decoded.value();
                                if (const auto st = r_double_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        ::protocyte::f64 value {};
                        auto decoded = ::protocyte::read_double_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        value = decoded.value();
                        if (const auto st = r_double_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::oneof_string: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_string) typename Config::String {ctx_};
                        special_oneof_case_ = Special_oneofCase::oneof_string;
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()),
                                special_oneof.oneof_string);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::oneof_int32: {
                        clear_special_oneof();
                        new (&special_oneof.oneof_int32)::protocyte::i32 {0};
                        special_oneof_case_ = Special_oneofCase::oneof_int32;
                        auto decoded = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        special_oneof.oneof_int32 = decoded.value();
                        break;
                    }
                    case FieldNumber::oneof_nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_oneof_nested();
                        if (!ensured) {
                            return ensured.status();
                        }
                        ::protocyte::LimitedReader<Reader> sub {reader, static_cast<::protocyte::usize>(len.value())};
                        ::protocyte::ReaderRef sub_reader {sub};
                        if (const auto st = ensured.value().get().merge_from(sub_reader); !st) {
                            return st;
                        }
                        if (const auto st = sub.finish(); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::oneof_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_bytes) typename Config::Bytes {ctx_};
                        special_oneof_case_ = Special_oneofCase::oneof_bytes;
                        if (const auto st = ::protocyte::read_bytes<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), special_oneof.oneof_bytes);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::opt_int32: {
                        auto decoded = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded) {
                            return decoded.status();
                        }
                        opt_int32_ = decoded.value();
                        has_opt_int32_ = true;
                        break;
                    }
                    case FieldNumber::opt_string: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), opt_string_);
                            !st) {
                            return st;
                        }
                        has_opt_string_ = true;
                        break;
                    }
                    default: {
                        if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) {
                            return st;
                        }
                        break;
                    }
                }
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer &writer) const noexcept {
            if (f_int32_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_int32), f_int32_);
                    !st) {
                    return st;
                }
            }
            if (f_int64_ != 0) {
                if (const auto st = ::protocyte::write_int64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_int64), f_int64_);
                    !st) {
                    return st;
                }
            }
            if (f_uint32_ != 0u) {
                if (const auto st = ::protocyte::write_uint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_uint32), f_uint32_);
                    !st) {
                    return st;
                }
            }
            if (f_uint64_ != 0u) {
                if (const auto st = ::protocyte::write_uint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_uint64), f_uint64_);
                    !st) {
                    return st;
                }
            }
            if (f_sint32_ != 0) {
                if (const auto st = ::protocyte::write_sint32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sint32), f_sint32_);
                    !st) {
                    return st;
                }
            }
            if (f_sint64_ != 0) {
                if (const auto st = ::protocyte::write_sint64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sint64), f_sint64_);
                    !st) {
                    return st;
                }
            }
            if (f_bool_) {
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_bool), f_bool_);
                    !st) {
                    return st;
                }
            }
            if (mode_ != 0) {
                if (const auto st =
                        ::protocyte::write_enum_field(writer, static_cast<::protocyte::u32>(FieldNumber::mode), mode_);
                    !st) {
                    return st;
                }
            }
            if (f_fixed32_ != 0u) {
                if (const auto st = ::protocyte::write_fixed32_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_fixed32), f_fixed32_);
                    !st) {
                    return st;
                }
            }
            if (f_fixed64_ != 0u) {
                if (const auto st = ::protocyte::write_fixed64_value_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_fixed64), f_fixed64_);
                    !st) {
                    return st;
                }
            }
            if (f_sfixed32_ != 0) {
                if (const auto st = ::protocyte::write_sfixed32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sfixed32), f_sfixed32_);
                    !st) {
                    return st;
                }
            }
            if (f_sfixed64_ != 0) {
                if (const auto st = ::protocyte::write_sfixed64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sfixed64), f_sfixed64_);
                    !st) {
                    return st;
                }
            }
            if (::std::bit_cast<::protocyte::u32>(f_float_) != 0u) {
                if (const auto st = ::protocyte::write_float_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_float), f_float_);
                    !st) {
                    return st;
                }
            }
            if (::std::bit_cast<::protocyte::u64>(f_double_) != 0u) {
                if (const auto st = ::protocyte::write_double_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_double), f_double_);
                    !st) {
                    return st;
                }
            }
            if (!f_string_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_string),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, f_string_.view()); !st) {
                    return st;
                }
            }
            if (!f_bytes_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_bytes),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, f_bytes_.view()); !st) {
                    return st;
                }
            }
            if (nested_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::nested),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = nested_.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = nested_.value().serialize(writer); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < r_int32_unpacked_.size(); ++i) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked), r_int32_unpacked_[i]);
                    !st) {
                    return st;
                }
            }
            if (!r_int32_packed_.empty()) {
                ::protocyte::usize packed_size_r_int32_packed {};
                for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &packed_size_r_int32_packed,
                                ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_packed_[i])));
                            !st_size) {
                            return st_size;
                        }
                    }
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_r_int32_packed));
                    !st) {
                    return st;
                }
                for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                    if (const auto st = ::protocyte::write_int32(writer, r_int32_packed_[i]); !st) {
                        return st;
                    }
                }
            }
            if (!r_double_.empty()) {
                ::protocyte::usize packed_size_r_double {};
                for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                    {
                        if (const auto st_size = ::protocyte::add_size(&packed_size_r_double, 8u); !st_size) {
                            return st_size;
                        }
                    }
                }
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::r_double),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_r_double));
                    !st) {
                    return st;
                }
                for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                    if (const auto st = ::protocyte::write_double(writer, r_double_[i]); !st) {
                        return st;
                    }
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_string), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, special_oneof.oneof_string.view()); !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_int32), special_oneof.oneof_int32);
                    !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_nested) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_nested), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = special_oneof.oneof_nested.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = special_oneof.oneof_nested.value().serialize(writer); !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_bytes), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, special_oneof.oneof_bytes.view()); !st) {
                    return st;
                }
            }
            if (has_opt_int32_) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::opt_int32), opt_int32_);
                    !st) {
                    return st;
                }
            }
            if (has_opt_string_) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::opt_string), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, opt_string_.view()); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (f_int32_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_int32)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_int64_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_int64)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int64_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_uint32_ != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_uint32)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_uint64_ != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_uint64)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint64_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sint32_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sint32)) +
                                    ::protocyte::varint_size(::protocyte::encode_zigzag32(f_sint32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sint64_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sint64)) +
                                    ::protocyte::varint_size(::protocyte::encode_zigzag64(f_sint64_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_bool_) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_bool)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_bool_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (mode_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::mode)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(mode_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_fixed32_ != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_fixed32)) + 4u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_fixed64_ != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_fixed64)) + 8u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sfixed32_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sfixed32)) + 4u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sfixed64_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sfixed64)) + 8u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (::std::bit_cast<::protocyte::u32>(f_float_) != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_float)) + 4u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (::std::bit_cast<::protocyte::u64>(f_double_) != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_double)) + 8u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!f_string_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_string)) +
                                    ::protocyte::varint_size(f_string_.size()) + f_string_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!f_bytes_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_bytes)) +
                                    ::protocyte::varint_size(f_bytes_.size()) + f_bytes_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (nested_.has_value()) {
                auto nested_size = nested_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::nested)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < r_int32_unpacked_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_unpacked_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!r_int32_packed_.empty()) {
                ::protocyte::usize packed_size_r_int32_packed {};
                for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &packed_size_r_int32_packed,
                                ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_packed_[i])));
                            !st_size) {
                            return ::protocyte::Result<::protocyte::usize>::err(st_size.error());
                        }
                    }
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_packed)) +
                                    ::protocyte::varint_size(packed_size_r_int32_packed) + packed_size_r_int32_packed);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!r_double_.empty()) {
                ::protocyte::usize packed_size_r_double {};
                for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                    {
                        if (const auto st_size = ::protocyte::add_size(&packed_size_r_double, 8u); !st_size) {
                            return ::protocyte::Result<::protocyte::usize>::err(st_size.error());
                        }
                    }
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_double)) +
                                    ::protocyte::varint_size(packed_size_r_double) + packed_size_r_double);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_string)) +
                                    ::protocyte::varint_size(special_oneof.oneof_string.size()) +
                                    special_oneof.oneof_string.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_int32)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(special_oneof.oneof_int32)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_nested) {
                auto nested_size = special_oneof.oneof_nested.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_nested)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_bytes)) +
                                    ::protocyte::varint_size(special_oneof.oneof_bytes.size()) +
                                    special_oneof.oneof_bytes.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (has_opt_int32_) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::opt_int32)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(opt_int32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (has_opt_string_) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::opt_string)) +
                                    ::protocyte::varint_size(opt_string_.size()) + opt_string_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
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
            typename Config::String oneof_string;
            ::protocyte::i32 oneof_int32;
            typename Config::template Optional<::protocyte_smoke::test::compat::EncodingMatrix_Inner<Config>>
                oneof_nested;
            typename Config::Bytes oneof_bytes;
        } special_oneof;
        ::protocyte::i32 opt_int32_ {};
        bool has_opt_int32_ {};
        typename Config::String opt_string_;
        bool has_opt_string_ {};
    };


} // namespace protocyte_smoke::test::compat

#endif // PROTOCYTE_GENERATED_COMPAT_PROTO_HPP
