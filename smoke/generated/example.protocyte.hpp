#pragma once

#ifndef PROTOCYTE_GENERATED_EXAMPLE_PROTO_69F808DB6B7B_HPP
#define PROTOCYTE_GENERATED_EXAMPLE_PROTO_69F808DB6B7B_HPP

#include <protocyte/runtime/runtime.hpp>

#include <string_view>

namespace test::ultimate {

    enum struct UltimateComplexMessage_Color : ::protocyte::i32 {
        COLOR_UNSPECIFIED = 0,
        RED = 1,
        GREEN = 2,
        BLUE = 3,
    };

    enum struct UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum : ::protocyte::i32 {
        INNER_UNSPECIFIED = 0,
        A = 1,
        B = 2,
        C = 3,
    };

    inline constexpr ::protocyte::i32 BASE_COUNT {5};
    inline constexpr ::std::string_view PREFIX {"proto", 5u};
    inline constexpr ::protocyte::u32 BYTE_ARRAY_CAP {4u};

    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_NestedLevel1_NestedLevel2;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_NestedLevel1;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_RepeatedBytesHolder;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_BoundedRepeatedBytesHolder;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_FixedRepeatedBytesHolder;
    template<typename Config = ::protocyte::DefaultConfig>
    struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA_LevelB;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA_LevelB_LevelC;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD;
    template<typename Config = ::protocyte::DefaultConfig> struct ExtraMessage;
    template<typename Config = ::protocyte::DefaultConfig> struct CrossMessageConstants_Nested;
    template<typename Config = ::protocyte::DefaultConfig> struct CrossMessageConstants;

    template<typename Config> struct UltimateComplexMessage_NestedLevel1_NestedLevel2 {
        using Context = typename Config::Context;
        using InnerEnum = UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;

        enum struct FieldNumber : ::protocyte::u32 {
            description = 1u,
            values = 2u,
            mode = 3u,
        };

        explicit UltimateComplexMessage_NestedLevel1_NestedLevel2(Context &ctx) noexcept:
            ctx_ {&ctx}, description_ {&ctx}, values_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2> create(Context &ctx) noexcept {
            return UltimateComplexMessage_NestedLevel1_NestedLevel2 {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_NestedLevel1_NestedLevel2(UltimateComplexMessage_NestedLevel1_NestedLevel2 &&) noexcept =
            default;
        UltimateComplexMessage_NestedLevel1_NestedLevel2 &
        operator=(UltimateComplexMessage_NestedLevel1_NestedLevel2 &&) noexcept = default;
        UltimateComplexMessage_NestedLevel1_NestedLevel2(const UltimateComplexMessage_NestedLevel1_NestedLevel2 &) =
            delete;
        UltimateComplexMessage_NestedLevel1_NestedLevel2 &
        operator=(const UltimateComplexMessage_NestedLevel1_NestedLevel2 &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_NestedLevel1_NestedLevel2 &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_description(other.description()); !st) {
                return st;
            }
            if (const auto st = mutable_values().copy_from(other.values()); !st) {
                return st;
            }
            if (const auto st = set_mode_raw(other.mode_raw()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2> clone() const noexcept {
            auto out = UltimateComplexMessage_NestedLevel1_NestedLevel2::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::Span<const ::protocyte::u8> description() const noexcept { return description_.view(); }
        typename Config::String &mutable_description() noexcept { return description_; }
        template<class Value>::protocyte::Status set_description(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            description_ = ::protocyte::move(temp);
            return {};
        }
        void clear_description() noexcept { description_.clear(); }

        const typename Config::template Vector<::protocyte::f32> &values() const noexcept { return values_; }
        typename Config::template Vector<::protocyte::f32> &mutable_values() noexcept { return values_; }
        void clear_values() noexcept { values_.clear(); }

        constexpr ::protocyte::i32 mode_raw() const noexcept { return mode_; }
        constexpr ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum mode() const noexcept {
            return static_cast<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum>(mode_);
        }
        ::protocyte::Status set_mode_raw(const ::protocyte::i32 value) noexcept {
            mode_ = value;
            return {};
        }
        ::protocyte::Status
        set_mode(const ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum value) noexcept {
            return set_mode_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_mode() noexcept { mode_ = {}; }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_NestedLevel1_NestedLevel2::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::description: {
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, description_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::values: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            typename Config::template Vector<::protocyte::f32> packed_values_values {ctx_};
                            const auto packed_reserve_values =
                                ::protocyte::checked_add(packed_values_values.size(), *len / 4u);
                            if (!packed_reserve_values) {
                                return packed_reserve_values.status();
                            }
                            if (const auto st = packed_values_values.reserve(*packed_reserve_values); !st) {
                                return st;
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::f32 value {};
                                if (const auto st = ::protocyte::read_float(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_values_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_values_values_commit_size =
                                ::protocyte::checked_add(values_.size(), packed_values_values.size());
                            if (!packed_values_values_commit_size) {
                                return packed_values_values_commit_size.status();
                            }
                            if (const auto st = values_.reserve(*packed_values_values_commit_size); !st) {
                                return st;
                            }
                            for (const auto &value : packed_values_values) {
                                if (const auto st = values_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::f32 value {};
                        if (const auto st = ::protocyte::read_float_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = values_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::mode: {
                        if (const auto st = ::protocyte::read_enum_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { mode_ = decoded; });
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
            if (!description_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::description), description_.view());
                    !st) {
                    return st;
                }
            }
            if (!values_.empty()) {
                ::protocyte::usize packed_size_values {};
                const auto packed_size_values_result = ::protocyte::checked_mul(values_.size(), 4u);
                if (!packed_size_values_result) {
                    return packed_size_values_result.status();
                }
                packed_size_values = *packed_size_values_result;
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::values),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_values));
                    !st) {
                    return st;
                }
                for (const auto &packed_value_values : values_) {
                    if (const auto st = ::protocyte::write_float(writer, packed_value_values); !st) {
                        return st;
                    }
                }
            }
            if (mode_ != 0) {
                if (const auto st =
                        ::protocyte::write_enum_field(writer, static_cast<::protocyte::u32>(FieldNumber::mode), mode_);
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!description_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::description), description_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!values_.empty()) {
                ::protocyte::usize packed_size_values {};
                const auto packed_size_values_result = ::protocyte::checked_mul(values_.size(), 4u);
                if (!packed_size_values_result) {
                    return ::protocyte::unexpected(packed_size_values_result.error());
                }
                packed_size_values = *packed_size_values_result;
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::values), packed_size_values)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (mode_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::mode)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(mode_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            return total;
        }
    protected:
        Context *ctx_;
        typename Config::String description_;
        typename Config::template Vector<::protocyte::f32> values_;
        ::protocyte::i32 mode_ {};
    };

    template<typename Config> struct UltimateComplexMessage_NestedLevel1 {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using NestedLevel2 =
            UltimateComplexMessage_NestedLevel1_NestedLevel2<NestedConfig>;

        enum struct FieldNumber : ::protocyte::u32 {
            name = 1u,
            id = 2u,
            inner = 3u,
        };

        explicit UltimateComplexMessage_NestedLevel1(Context &ctx) noexcept: ctx_ {&ctx}, name_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_NestedLevel1> create(Context &ctx) noexcept {
            return UltimateComplexMessage_NestedLevel1 {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_NestedLevel1(UltimateComplexMessage_NestedLevel1 &&) noexcept = default;
        UltimateComplexMessage_NestedLevel1 &operator=(UltimateComplexMessage_NestedLevel1 &&) noexcept = default;
        UltimateComplexMessage_NestedLevel1(const UltimateComplexMessage_NestedLevel1 &) = delete;
        UltimateComplexMessage_NestedLevel1 &operator=(const UltimateComplexMessage_NestedLevel1 &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_NestedLevel1 &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_name(other.name()); !st) {
                return st;
            }
            if (const auto st = set_id(other.id()); !st) {
                return st;
            }
            if (other.has_inner()) {
                if (const auto st = ensure_inner().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                        return ensured->copy_from(*other.inner());
                    });
                    !st) {
                    return st;
                }
            } else {
                clear_inner();
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_NestedLevel1> clone() const noexcept {
            auto out = UltimateComplexMessage_NestedLevel1::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::Span<const ::protocyte::u8> name() const noexcept { return name_.view(); }
        typename Config::String &mutable_name() noexcept { return name_; }
        template<class Value>::protocyte::Status set_name(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            name_ = ::protocyte::move(temp);
            return {};
        }
        void clear_name() noexcept { name_.clear(); }

        constexpr ::protocyte::i32 id() const noexcept { return id_; }
        ::protocyte::Status set_id(const ::protocyte::i32 value) noexcept {
            id_ = value;
            return {};
        }
        constexpr void clear_id() noexcept { id_ = {}; }

        bool has_inner() const noexcept { return inner_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> *inner() const noexcept {
            return has_inner() ? inner_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>>
        ensure_inner() noexcept {
            if (inner_.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> {
                    *inner_};
            }
            return inner_.emplace(*ctx_).transform(
                [this]() noexcept
                    -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> {
                    return ::protocyte::Ref<
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> {*inner_};
                });
        }
        void clear_inner() noexcept { inner_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage_NestedLevel1> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_NestedLevel1::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::name: {
                        if (const auto st =
                                ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, name_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::id: {
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { id_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::inner: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> inner_value {*ctx_};
                        if (inner_.has_value()) {
                            if (const auto st = inner_value.copy_from(*inner_); !st) {
                                return st;
                            }
                        }
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number, inner_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = inner_.emplace(::protocyte::move(inner_value)); !st) {
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
            if (!name_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::name), name_.view());
                    !st) {
                    return st;
                }
            }
            if (id_ != 0) {
                if (const auto st =
                        ::protocyte::write_int32_field(writer, static_cast<::protocyte::u32>(FieldNumber::id), id_);
                    !st) {
                    return st;
                }
            }
            if (inner_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::inner), *inner_);
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!name_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::name), name_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (id_ != 0) {
                const auto st_size =
                    ::protocyte::add_size(total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::id)) +
                                                     ::protocyte::varint_size(static_cast<::protocyte::u64>(id_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (inner_.has_value()) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::inner), *inner_)
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
    protected:
        Context *ctx_;
        typename Config::String name_;
        ::protocyte::i32 id_ {};
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>
            inner_;
    };

    template<typename Config> struct UltimateComplexMessage_RepeatedBytesHolder {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            values = 1u,
        };

        explicit UltimateComplexMessage_RepeatedBytesHolder(Context &ctx) noexcept: ctx_ {&ctx}, values_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_RepeatedBytesHolder> create(Context &ctx) noexcept {
            return UltimateComplexMessage_RepeatedBytesHolder {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_RepeatedBytesHolder(UltimateComplexMessage_RepeatedBytesHolder &&) noexcept = default;
        UltimateComplexMessage_RepeatedBytesHolder &
        operator=(UltimateComplexMessage_RepeatedBytesHolder &&) noexcept = default;
        UltimateComplexMessage_RepeatedBytesHolder(const UltimateComplexMessage_RepeatedBytesHolder &) = delete;
        UltimateComplexMessage_RepeatedBytesHolder &
        operator=(const UltimateComplexMessage_RepeatedBytesHolder &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_RepeatedBytesHolder &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = mutable_values().copy_from(other.values()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_RepeatedBytesHolder> clone() const noexcept {
            auto out = UltimateComplexMessage_RepeatedBytesHolder::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        const typename Config::template Vector<typename Config::Bytes> &values() const noexcept { return values_; }
        typename Config::template Vector<typename Config::Bytes> &mutable_values() noexcept { return values_; }
        void clear_values() noexcept { values_.clear(); }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_RepeatedBytesHolder>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_RepeatedBytesHolder::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::values: {
                        typename Config::Bytes value {ctx_};
                        if (const auto st =
                                ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type, field_number, value)
                                    .and_then([&]() noexcept -> ::protocyte::Status {
                                        return values_.push_back(::protocyte::move(value));
                                    });
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
            for (const auto &values_value : values_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::values), values_value.view());
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            for (const auto &values_value : values_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::values), values_value.size())
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
    protected:
        Context *ctx_;
        typename Config::template Vector<typename Config::Bytes> values_;
    };

    template<typename Config> struct UltimateComplexMessage_BoundedRepeatedBytesHolder {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            values = 1u,
        };

        explicit UltimateComplexMessage_BoundedRepeatedBytesHolder(Context &ctx) noexcept:
            ctx_ {&ctx}, values_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_BoundedRepeatedBytesHolder> create(Context &ctx) noexcept {
            return UltimateComplexMessage_BoundedRepeatedBytesHolder {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_BoundedRepeatedBytesHolder(
            UltimateComplexMessage_BoundedRepeatedBytesHolder &&) noexcept = default;
        UltimateComplexMessage_BoundedRepeatedBytesHolder &
        operator=(UltimateComplexMessage_BoundedRepeatedBytesHolder &&) noexcept = default;
        UltimateComplexMessage_BoundedRepeatedBytesHolder(const UltimateComplexMessage_BoundedRepeatedBytesHolder &) =
            delete;
        UltimateComplexMessage_BoundedRepeatedBytesHolder &
        operator=(const UltimateComplexMessage_BoundedRepeatedBytesHolder &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_BoundedRepeatedBytesHolder &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = mutable_values().copy_from(other.values()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_BoundedRepeatedBytesHolder> clone() const noexcept {
            auto out = UltimateComplexMessage_BoundedRepeatedBytesHolder::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        const ::protocyte::Array<typename Config::Bytes, 3u> &values() const noexcept { return values_; }
        ::protocyte::Array<typename Config::Bytes, 3u> &mutable_values() noexcept { return values_; }
        void clear_values() noexcept { values_.clear(); }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_BoundedRepeatedBytesHolder>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_BoundedRepeatedBytesHolder::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::values: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        typename Config::Bytes value {ctx_};
                        if (const auto st = ::protocyte::read_bytes<Config>(*ctx_, reader, value)
                                                .and_then([&]() noexcept -> ::protocyte::Status {
                                                    return values_.push_back(::protocyte::move(value));
                                                });
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
            for (const auto &values_value : values_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::values), values_value.view());
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            for (const auto &values_value : values_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::values), values_value.size())
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
    protected:
        Context *ctx_;
        ::protocyte::Array<typename Config::Bytes, 3u> values_;
    };

    template<typename Config> struct UltimateComplexMessage_FixedRepeatedBytesHolder {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            values = 1u,
        };

        explicit UltimateComplexMessage_FixedRepeatedBytesHolder(Context &ctx) noexcept: ctx_ {&ctx}, values_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_FixedRepeatedBytesHolder> create(Context &ctx) noexcept {
            return UltimateComplexMessage_FixedRepeatedBytesHolder {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_FixedRepeatedBytesHolder(UltimateComplexMessage_FixedRepeatedBytesHolder &&) noexcept =
            default;
        UltimateComplexMessage_FixedRepeatedBytesHolder &
        operator=(UltimateComplexMessage_FixedRepeatedBytesHolder &&) noexcept = default;
        UltimateComplexMessage_FixedRepeatedBytesHolder(const UltimateComplexMessage_FixedRepeatedBytesHolder &) =
            delete;
        UltimateComplexMessage_FixedRepeatedBytesHolder &
        operator=(const UltimateComplexMessage_FixedRepeatedBytesHolder &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_FixedRepeatedBytesHolder &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = mutable_values().copy_from(other.values()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_FixedRepeatedBytesHolder> clone() const noexcept {
            auto out = UltimateComplexMessage_FixedRepeatedBytesHolder::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        const ::protocyte::Array<typename Config::Bytes, 3u> &values() const noexcept { return values_; }
        ::protocyte::Array<typename Config::Bytes, 3u> &mutable_values() noexcept { return values_; }
        void clear_values() noexcept { values_.clear(); }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_FixedRepeatedBytesHolder>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_FixedRepeatedBytesHolder::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::values: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        typename Config::Bytes value {ctx_};
                        if (const auto st = ::protocyte::read_bytes<Config>(*ctx_, reader, value)
                                                .and_then([&]() noexcept -> ::protocyte::Status {
                                                    return values_.push_back(::protocyte::move(value));
                                                });
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
            if (values_.size() != 0u && values_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::values));
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (values_.size() != 0u && values_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::values));
            }
            for (const auto &values_value : values_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::values), values_value.view());
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (values_.size() != 0u && values_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::values));
            }
            ::protocyte::usize total {};
            for (const auto &values_value : values_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::values), values_value.size())
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
    protected:
        Context *ctx_;
        ::protocyte::Array<typename Config::Bytes, 3u> values_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE {
        using Context = typename Config::Context;

        enum struct Deep_oneofCase : ::protocyte::u32 {
            none = 0u,
            val = 3u,
            text = 4u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            extreme = 1u,
            weird_map = 2u,
            val = 3u,
            text = 4u,
        };

        explicit UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE(Context &ctx) noexcept:
            ctx_ {&ctx}, extreme_ {&ctx}, weird_map_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>
        create(Context &ctx) noexcept {
            return UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE(
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &&other) noexcept:
            ctx_ {other.ctx_},
            extreme_ {::protocyte::move(other.extreme_)},
            weird_map_ {::protocyte::move(other.weird_map_)} {
            switch (other.deep_oneof_case_) {
                case Deep_oneofCase::val: {
                    new (&deep_oneof.val)::protocyte::i64 {other.deep_oneof.val};
                    deep_oneof_case_ = Deep_oneofCase::val;
                    break;
                }
                case Deep_oneofCase::text: {
                    new (&deep_oneof.text) typename Config::String {::protocyte::move(other.deep_oneof.text)};
                    deep_oneof_case_ = Deep_oneofCase::text;
                    break;
                }
                case Deep_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_deep_oneof();
        }
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &
        operator=(UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_deep_oneof();
            ctx_ = other.ctx_;
            extreme_ = ::protocyte::move(other.extreme_);
            weird_map_ = ::protocyte::move(other.weird_map_);
            switch (other.deep_oneof_case_) {
                case Deep_oneofCase::val: {
                    new (&deep_oneof.val)::protocyte::i64 {other.deep_oneof.val};
                    deep_oneof_case_ = Deep_oneofCase::val;
                    break;
                }
                case Deep_oneofCase::text: {
                    new (&deep_oneof.text) typename Config::String {::protocyte::move(other.deep_oneof.text)};
                    deep_oneof_case_ = Deep_oneofCase::text;
                    break;
                }
                case Deep_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_deep_oneof();
            return *this;
        }
        ~UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE() noexcept { clear_deep_oneof(); }
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE(
            const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &) = delete;
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &
        operator=(const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_extreme(other.extreme()); !st) {
                return st;
            }
            if (const auto st = mutable_weird_map().copy_from(other.weird_map()); !st) {
                return st;
            }
            switch (other.deep_oneof_case_) {
                case Deep_oneofCase::val: {
                    if (const auto st = set_val(other.val()); !st) {
                        return st;
                    }
                    break;
                }
                case Deep_oneofCase::text: {
                    if (const auto st = set_text(other.text()); !st) {
                        return st;
                    }
                    break;
                }
                case Deep_oneofCase::none:
                default: {
                    clear_deep_oneof();
                    break;
                }
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        constexpr Deep_oneofCase deep_oneof_case() const noexcept { return deep_oneof_case_; }
        void clear_deep_oneof() noexcept {
            switch (deep_oneof_case_) {
                case Deep_oneofCase::val: {
                    break;
                }
                case Deep_oneofCase::text: {
                    destroy_at_(&deep_oneof.text);
                    break;
                }
                case Deep_oneofCase::none:
                default: {
                    break;
                }
            }
            deep_oneof_case_ = Deep_oneofCase::none;
        }

        ::protocyte::Span<const ::protocyte::u8> extreme() const noexcept { return extreme_.view(); }
        typename Config::String &mutable_extreme() noexcept { return extreme_; }
        template<class Value>::protocyte::Status set_extreme(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            extreme_ = ::protocyte::move(temp);
            return {};
        }
        void clear_extreme() noexcept { extreme_.clear(); }

        const typename Config::template Map<::protocyte::i32, typename Config::String> &weird_map() const noexcept {
            return weird_map_;
        }
        typename Config::template Map<::protocyte::i32, typename Config::String> &mutable_weird_map() noexcept {
            return weird_map_;
        }
        void clear_weird_map() noexcept { weird_map_.clear(); }

        constexpr bool has_val() const noexcept { return deep_oneof_case_ == Deep_oneofCase::val; }
        constexpr ::protocyte::i64 val() const noexcept { return has_val() ? deep_oneof.val : 0; }
        ::protocyte::Status set_val(const ::protocyte::i64 value) noexcept {
            clear_deep_oneof();
            new (&deep_oneof.val)::protocyte::i64 {value};
            deep_oneof_case_ = Deep_oneofCase::val;
            return {};
        }

        constexpr bool has_text() const noexcept { return deep_oneof_case_ == Deep_oneofCase::text; }
        ::protocyte::Span<const ::protocyte::u8> text() const noexcept {
            return has_text() ? deep_oneof.text.view() : ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_text(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            clear_deep_oneof();
            new (&deep_oneof.text) typename Config::String {::protocyte::move(temp)};
            deep_oneof_case_ = Deep_oneofCase::text;
            return {};
        }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::extreme: {
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, extreme_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::weird_map: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::i32 key {};
                        typename Config::String value {ctx_};
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    if (const auto st =
                                            ::protocyte::read_int32(entry_reader)
                                                .transform([&](const auto decoded) noexcept { key = decoded; });
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
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
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (const auto insert =
                                weird_map_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::val: {
                        ::protocyte::i64 val_value {};
                        if (const auto st = ::protocyte::read_int64_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { val_value = decoded; });
                            !st) {
                            return st;
                        }
                        clear_deep_oneof();
                        new (&deep_oneof.val)::protocyte::i64 {::protocyte::move(val_value)};
                        deep_oneof_case_ = Deep_oneofCase::val;
                        break;
                    }
                    case FieldNumber::text: {
                        typename Config::String text_value {ctx_};
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, text_value);
                            !st) {
                            return st;
                        }
                        clear_deep_oneof();
                        new (&deep_oneof.text) typename Config::String {::protocyte::move(text_value)};
                        deep_oneof_case_ = Deep_oneofCase::text;
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
            if (!extreme_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::extreme), extreme_.view());
                    !st) {
                    return st;
                }
            }
            for (const auto entry : weird_map_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::weird_map), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.view());
                    !st) {
                    return st;
                }
            }
            if (deep_oneof_case_ == Deep_oneofCase::val) {
                if (const auto st = ::protocyte::write_int64_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::val), deep_oneof.val);
                    !st) {
                    return st;
                }
            }
            if (deep_oneof_case_ == Deep_oneofCase::text) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::text), deep_oneof.text.view());
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!extreme_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::extreme), extreme_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto entry : weird_map_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::weird_map), entry_payload)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (deep_oneof_case_ == Deep_oneofCase::val) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::val)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(deep_oneof.val)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (deep_oneof_case_ == Deep_oneofCase::text) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::text), deep_oneof.text.size())
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
    protected:
        Context *ctx_;
        typename Config::String extreme_;
        typename Config::template Map<::protocyte::i32, typename Config::String> weird_map_;
        Deep_oneofCase deep_oneof_case_ {Deep_oneofCase::none};
        union Deep_oneofStorage {
            Deep_oneofStorage() noexcept {}
            ~Deep_oneofStorage() noexcept {}
            ::protocyte::i64 val;
            typename Config::String text;
        } deep_oneof;
    };

    template<typename Config> struct UltimateComplexMessage {
        using Context = typename Config::Context;
        using Color = UltimateComplexMessage_Color;
        template<typename NestedConfig = Config> using NestedLevel1 = UltimateComplexMessage_NestedLevel1<NestedConfig>;
        template<typename NestedConfig = Config> using RepeatedBytesHolder =
            UltimateComplexMessage_RepeatedBytesHolder<NestedConfig>;
        template<typename NestedConfig = Config> using BoundedRepeatedBytesHolder =
            UltimateComplexMessage_BoundedRepeatedBytesHolder<NestedConfig>;
        template<typename NestedConfig = Config> using FixedRepeatedBytesHolder =
            UltimateComplexMessage_FixedRepeatedBytesHolder<NestedConfig>;
        template<typename NestedConfig = Config> using LevelA = UltimateComplexMessage_LevelA<NestedConfig>;

        static constexpr ::protocyte::i64 SHIFTED_COUNT {5000000000ll};
        static constexpr ::protocyte::u64 MASK_BITS {1234567890123456789ull};
        static constexpr ::protocyte::f32 FLOAT_SCALE {1.25f};
        static constexpr ::protocyte::f64 DOUBLE_SCALE {3.75};
        static constexpr bool FLAG_LITERAL {true};
        static constexpr ::protocyte::u32 HEX_LITERAL {32u};
        static constexpr ::protocyte::u32 HEX_SUM {24u};
        static constexpr ::protocyte::u32 INTEGER_ARRAY_CAP {8u};
        static constexpr ::std::string_view LABEL {"proto-demo", 10u};
        static constexpr ::std::string_view UNICODE_LABEL {"\xc4"
                                                           "\x80"
                                                           "\xc3"
                                                           "\xa9",
                                                           4u};
        static constexpr ::protocyte::u32 FIXED_INTEGER_ARRAY_CAP {3u};
        static constexpr ::protocyte::u32 FLOATISH_BOUND {2u};
        static constexpr bool GT_CHECK {true};
        static constexpr bool LE_CHECK {true};
        static constexpr bool EQ_CHECK {true};
        static constexpr bool NE_CHECK {true};
        static constexpr bool HAS_PREFIX {true};
        static constexpr ::protocyte::i32 MOD_CHECK {1};
        static constexpr bool OR_CHECK {true};

        enum struct Special_oneofCase : ::protocyte::u32 {
            none = 0u,
            oneof_string = 26u,
            oneof_int32 = 27u,
            oneof_msg = 28u,
            oneof_bytes = 29u,
        };

        enum struct Crazy_bytes_oneofCase : ::protocyte::u32 {
            none = 0u,
            crazy_plain_bytes = 49u,
            crazy_bounded_bytes = 50u,
            crazy_fixed_bytes = 51u,
            crazy_repeated_bytes = 52u,
            crazy_bounded_repeated_bytes = 53u,
            crazy_fixed_repeated_bytes = 54u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            f_double = 1u,
            f_float = 2u,
            f_int32 = 4u,
            f_int64 = 8u,
            f_uint32 = 9u,
            f_uint64 = 10u,
            f_sint32 = 11u,
            f_sint64 = 12u,
            f_fixed32 = 13u,
            f_fixed64 = 14u,
            f_sfixed32 = 15u,
            f_sfixed64 = 16u,
            f_bool = 17u,
            f_string = 18u,
            f_bytes = 19u,
            r_int32_unpacked = 21u,
            r_int32_packed = 22u,
            r_double = 23u,
            color = 24u,
            nested1 = 25u,
            oneof_string = 26u,
            oneof_int32 = 27u,
            oneof_msg = 28u,
            oneof_bytes = 29u,
            map_str_int32 = 30u,
            map_int32_str = 31u,
            map_bool_bytes = 32u,
            map_uint64_msg = 33u,
            very_nested_map = 34u,
            recursive_self = 35u,
            lots_of_nested = 36u,
            colors = 37u,
            opt_int32 = 38u,
            opt_string = 39u,
            extreme_nesting = 40u,
            sha256 = 41u,
            integer_array = 42u,
            byte_array = 43u,
            fixed_integer_array = 44u,
            float_expr_array = 45u,
            repeated_byte_array = 46u,
            bounded_repeated_byte_array = 47u,
            fixed_repeated_byte_array = 48u,
            crazy_plain_bytes = 49u,
            crazy_bounded_bytes = 50u,
            crazy_fixed_bytes = 51u,
            crazy_repeated_bytes = 52u,
            crazy_bounded_repeated_bytes = 53u,
            crazy_fixed_repeated_bytes = 54u,
        };

        explicit UltimateComplexMessage(Context &ctx) noexcept:
            ctx_ {&ctx},
            f_string_ {&ctx},
            f_bytes_ {&ctx},
            r_int32_unpacked_ {&ctx},
            r_int32_packed_ {&ctx},
            r_double_ {&ctx},
            map_str_int32_ {&ctx},
            map_int32_str_ {&ctx},
            map_bool_bytes_ {&ctx},
            map_uint64_msg_ {&ctx},
            very_nested_map_ {&ctx},
            recursive_self_ {&ctx},
            lots_of_nested_ {&ctx},
            colors_ {&ctx},
            opt_string_ {&ctx},
            integer_array_ {&ctx},
            fixed_integer_array_ {&ctx},
            repeated_byte_array_ {&ctx},
            bounded_repeated_byte_array_ {&ctx},
            fixed_repeated_byte_array_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage> create(Context &ctx) noexcept {
            return UltimateComplexMessage {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage(UltimateComplexMessage &&other) noexcept:
            ctx_ {other.ctx_},
            f_double_ {other.f_double_},
            f_float_ {other.f_float_},
            f_int32_ {other.f_int32_},
            f_int64_ {other.f_int64_},
            f_uint32_ {other.f_uint32_},
            f_uint64_ {other.f_uint64_},
            f_sint32_ {other.f_sint32_},
            f_sint64_ {other.f_sint64_},
            f_fixed32_ {other.f_fixed32_},
            f_fixed64_ {other.f_fixed64_},
            f_sfixed32_ {other.f_sfixed32_},
            f_sfixed64_ {other.f_sfixed64_},
            f_bool_ {other.f_bool_},
            f_string_ {::protocyte::move(other.f_string_)},
            f_bytes_ {::protocyte::move(other.f_bytes_)},
            r_int32_unpacked_ {::protocyte::move(other.r_int32_unpacked_)},
            r_int32_packed_ {::protocyte::move(other.r_int32_packed_)},
            r_double_ {::protocyte::move(other.r_double_)},
            color_ {other.color_},
            nested1_ {::protocyte::move(other.nested1_)},
            map_str_int32_ {::protocyte::move(other.map_str_int32_)},
            map_int32_str_ {::protocyte::move(other.map_int32_str_)},
            map_bool_bytes_ {::protocyte::move(other.map_bool_bytes_)},
            map_uint64_msg_ {::protocyte::move(other.map_uint64_msg_)},
            very_nested_map_ {::protocyte::move(other.very_nested_map_)},
            recursive_self_ {::protocyte::move(other.recursive_self_)},
            lots_of_nested_ {::protocyte::move(other.lots_of_nested_)},
            colors_ {::protocyte::move(other.colors_)},
            opt_int32_ {other.opt_int32_},
            opt_string_ {::protocyte::move(other.opt_string_)},
            extreme_nesting_ {::protocyte::move(other.extreme_nesting_)},
            sha256_ {::protocyte::move(other.sha256_)},
            integer_array_ {::protocyte::move(other.integer_array_)},
            byte_array_ {::protocyte::move(other.byte_array_)},
            fixed_integer_array_ {::protocyte::move(other.fixed_integer_array_)},
            float_expr_array_ {::protocyte::move(other.float_expr_array_)},
            repeated_byte_array_ {::protocyte::move(other.repeated_byte_array_)},
            bounded_repeated_byte_array_ {::protocyte::move(other.bounded_repeated_byte_array_)},
            fixed_repeated_byte_array_ {::protocyte::move(other.fixed_repeated_byte_array_)} {
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
                case Special_oneofCase::oneof_msg: {
                    new (&special_oneof.oneof_msg) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                        ::protocyte::move(other.special_oneof.oneof_msg)};
                    special_oneof_case_ = Special_oneofCase::oneof_msg;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof.oneof_bytes)::protocyte::ByteArray<4u> {
                        ::protocyte::move(other.special_oneof.oneof_bytes)};
                    special_oneof_case_ = Special_oneofCase::oneof_bytes;
                    break;
                }
                case Special_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_special_oneof();
            switch (other.crazy_bytes_oneof_case_) {
                case Crazy_bytes_oneofCase::crazy_plain_bytes: {
                    new (&crazy_bytes_oneof.crazy_plain_bytes)
                        typename Config::Bytes {::protocyte::move(other.crazy_bytes_oneof.crazy_plain_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_plain_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_bytes: {
                    new (&crazy_bytes_oneof.crazy_bounded_bytes)::protocyte::ByteArray<4u> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_bounded_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_bytes: {
                    new (&crazy_bytes_oneof.crazy_fixed_bytes)::protocyte::FixedByteArray<4u> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_fixed_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_repeated_bytes: {
                    new (&crazy_bytes_oneof.crazy_repeated_bytes) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_repeated_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_repeated_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes: {
                    new (&crazy_bytes_oneof.crazy_bounded_repeated_bytes) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_bounded_repeated_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes: {
                    new (&crazy_bytes_oneof.crazy_fixed_repeated_bytes) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_fixed_repeated_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_crazy_bytes_oneof();
        }
        UltimateComplexMessage &operator=(UltimateComplexMessage &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_special_oneof();
            clear_crazy_bytes_oneof();
            ctx_ = other.ctx_;
            f_double_ = other.f_double_;
            f_float_ = other.f_float_;
            f_int32_ = other.f_int32_;
            f_int64_ = other.f_int64_;
            f_uint32_ = other.f_uint32_;
            f_uint64_ = other.f_uint64_;
            f_sint32_ = other.f_sint32_;
            f_sint64_ = other.f_sint64_;
            f_fixed32_ = other.f_fixed32_;
            f_fixed64_ = other.f_fixed64_;
            f_sfixed32_ = other.f_sfixed32_;
            f_sfixed64_ = other.f_sfixed64_;
            f_bool_ = other.f_bool_;
            f_string_ = ::protocyte::move(other.f_string_);
            f_bytes_ = ::protocyte::move(other.f_bytes_);
            r_int32_unpacked_ = ::protocyte::move(other.r_int32_unpacked_);
            r_int32_packed_ = ::protocyte::move(other.r_int32_packed_);
            r_double_ = ::protocyte::move(other.r_double_);
            color_ = other.color_;
            nested1_ = ::protocyte::move(other.nested1_);
            map_str_int32_ = ::protocyte::move(other.map_str_int32_);
            map_int32_str_ = ::protocyte::move(other.map_int32_str_);
            map_bool_bytes_ = ::protocyte::move(other.map_bool_bytes_);
            map_uint64_msg_ = ::protocyte::move(other.map_uint64_msg_);
            very_nested_map_ = ::protocyte::move(other.very_nested_map_);
            recursive_self_ = ::protocyte::move(other.recursive_self_);
            lots_of_nested_ = ::protocyte::move(other.lots_of_nested_);
            colors_ = ::protocyte::move(other.colors_);
            opt_int32_ = other.opt_int32_;
            has_opt_int32_ = other.has_opt_int32_;
            opt_string_ = ::protocyte::move(other.opt_string_);
            has_opt_string_ = other.has_opt_string_;
            extreme_nesting_ = ::protocyte::move(other.extreme_nesting_);
            sha256_ = ::protocyte::move(other.sha256_);
            integer_array_ = ::protocyte::move(other.integer_array_);
            byte_array_ = ::protocyte::move(other.byte_array_);
            fixed_integer_array_ = ::protocyte::move(other.fixed_integer_array_);
            float_expr_array_ = ::protocyte::move(other.float_expr_array_);
            repeated_byte_array_ = ::protocyte::move(other.repeated_byte_array_);
            bounded_repeated_byte_array_ = ::protocyte::move(other.bounded_repeated_byte_array_);
            fixed_repeated_byte_array_ = ::protocyte::move(other.fixed_repeated_byte_array_);
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
                case Special_oneofCase::oneof_msg: {
                    new (&special_oneof.oneof_msg) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                        ::protocyte::move(other.special_oneof.oneof_msg)};
                    special_oneof_case_ = Special_oneofCase::oneof_msg;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof.oneof_bytes)::protocyte::ByteArray<4u> {
                        ::protocyte::move(other.special_oneof.oneof_bytes)};
                    special_oneof_case_ = Special_oneofCase::oneof_bytes;
                    break;
                }
                case Special_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_special_oneof();
            switch (other.crazy_bytes_oneof_case_) {
                case Crazy_bytes_oneofCase::crazy_plain_bytes: {
                    new (&crazy_bytes_oneof.crazy_plain_bytes)
                        typename Config::Bytes {::protocyte::move(other.crazy_bytes_oneof.crazy_plain_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_plain_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_bytes: {
                    new (&crazy_bytes_oneof.crazy_bounded_bytes)::protocyte::ByteArray<4u> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_bounded_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_bytes: {
                    new (&crazy_bytes_oneof.crazy_fixed_bytes)::protocyte::FixedByteArray<4u> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_fixed_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_repeated_bytes: {
                    new (&crazy_bytes_oneof.crazy_repeated_bytes) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_repeated_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_repeated_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes: {
                    new (&crazy_bytes_oneof.crazy_bounded_repeated_bytes) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_bounded_repeated_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes: {
                    new (&crazy_bytes_oneof.crazy_fixed_repeated_bytes) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {
                        ::protocyte::move(other.crazy_bytes_oneof.crazy_fixed_repeated_bytes)};
                    crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes;
                    break;
                }
                case Crazy_bytes_oneofCase::none:
                default: {
                    break;
                }
            }
            other.clear_crazy_bytes_oneof();
            return *this;
        }
        ~UltimateComplexMessage() noexcept {
            clear_special_oneof();
            clear_crazy_bytes_oneof();
        }
        UltimateComplexMessage(const UltimateComplexMessage &) = delete;
        UltimateComplexMessage &operator=(const UltimateComplexMessage &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const UltimateComplexMessage &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_f_double(other.f_double()); !st) {
                return st;
            }
            if (const auto st = set_f_float(other.f_float()); !st) {
                return st;
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
            if (const auto st = set_f_bool(other.f_bool()); !st) {
                return st;
            }
            if (const auto st = set_f_string(other.f_string()); !st) {
                return st;
            }
            if (const auto st = set_f_bytes(other.f_bytes()); !st) {
                return st;
            }
            if (const auto st = mutable_r_int32_unpacked().copy_from(other.r_int32_unpacked()); !st) {
                return st;
            }
            if (const auto st = mutable_r_int32_packed().copy_from(other.r_int32_packed()); !st) {
                return st;
            }
            if (const auto st = mutable_r_double().copy_from(other.r_double()); !st) {
                return st;
            }
            if (const auto st = set_color_raw(other.color_raw()); !st) {
                return st;
            }
            if (other.has_nested1()) {
                if (const auto st = ensure_nested1().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                        return ensured->copy_from(*other.nested1());
                    });
                    !st) {
                    return st;
                }
            } else {
                clear_nested1();
            }
            if (const auto st = mutable_map_str_int32().copy_from(other.map_str_int32()); !st) {
                return st;
            }
            if (const auto st = mutable_map_int32_str().copy_from(other.map_int32_str()); !st) {
                return st;
            }
            if (const auto st = mutable_map_bool_bytes().copy_from(other.map_bool_bytes()); !st) {
                return st;
            }
            if (const auto st = mutable_map_uint64_msg().copy_from(other.map_uint64_msg()); !st) {
                return st;
            }
            if (const auto st = mutable_very_nested_map().copy_from(other.very_nested_map()); !st) {
                return st;
            }
            if (other.has_recursive_self()) {
                if (const auto st = ensure_recursive_self().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                        return ensured->copy_from(*other.recursive_self());
                    });
                    !st) {
                    return st;
                }
            } else {
                clear_recursive_self();
            }
            if (const auto st = mutable_lots_of_nested().copy_from(other.lots_of_nested()); !st) {
                return st;
            }
            if (const auto st = mutable_colors().copy_from(other.colors()); !st) {
                return st;
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
            if (other.has_extreme_nesting()) {
                if (const auto st =
                        ensure_extreme_nesting().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                            return ensured->copy_from(*other.extreme_nesting());
                        });
                    !st) {
                    return st;
                }
            } else {
                clear_extreme_nesting();
            }
            if (other.has_sha256()) {
                if (const auto st = set_sha256(other.sha256()); !st) {
                    return st;
                }
            } else {
                clear_sha256();
            }
            if (const auto st = mutable_integer_array().copy_from(other.integer_array()); !st) {
                return st;
            }
            if (const auto st = set_byte_array(other.byte_array()); !st) {
                return st;
            }
            if (const auto st = mutable_fixed_integer_array().copy_from(other.fixed_integer_array()); !st) {
                return st;
            }
            if (const auto st = set_float_expr_array(other.float_expr_array()); !st) {
                return st;
            }
            if (const auto st = mutable_repeated_byte_array().copy_from(other.repeated_byte_array()); !st) {
                return st;
            }
            if (const auto st = mutable_bounded_repeated_byte_array().copy_from(other.bounded_repeated_byte_array());
                !st) {
                return st;
            }
            if (const auto st = mutable_fixed_repeated_byte_array().copy_from(other.fixed_repeated_byte_array()); !st) {
                return st;
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
                case Special_oneofCase::oneof_msg: {
                    if (const auto st = ensure_oneof_msg().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                            return ensured->copy_from(*other.oneof_msg());
                        });
                        !st) {
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
            switch (other.crazy_bytes_oneof_case_) {
                case Crazy_bytes_oneofCase::crazy_plain_bytes: {
                    if (const auto st = set_crazy_plain_bytes(other.crazy_plain_bytes()); !st) {
                        return st;
                    }
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_bytes: {
                    if (const auto st = set_crazy_bounded_bytes(other.crazy_bounded_bytes()); !st) {
                        return st;
                    }
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_bytes: {
                    if (const auto st = set_crazy_fixed_bytes(other.crazy_fixed_bytes()); !st) {
                        return st;
                    }
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_repeated_bytes: {
                    if (const auto st =
                            ensure_crazy_repeated_bytes().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                                return ensured->copy_from(*other.crazy_repeated_bytes());
                            });
                        !st) {
                        return st;
                    }
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes: {
                    if (const auto st = ensure_crazy_bounded_repeated_bytes().and_then(
                            [&](auto ensured) noexcept -> ::protocyte::Status {
                                return ensured->copy_from(*other.crazy_bounded_repeated_bytes());
                            });
                        !st) {
                        return st;
                    }
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes: {
                    if (const auto st = ensure_crazy_fixed_repeated_bytes().and_then(
                            [&](auto ensured) noexcept -> ::protocyte::Status {
                                return ensured->copy_from(*other.crazy_fixed_repeated_bytes());
                            });
                        !st) {
                        return st;
                    }
                    break;
                }
                case Crazy_bytes_oneofCase::none:
                default: {
                    clear_crazy_bytes_oneof();
                    break;
                }
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage> clone() const noexcept {
            auto out = UltimateComplexMessage::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
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
                case Special_oneofCase::oneof_msg: {
                    destroy_at_(&special_oneof.oneof_msg);
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

        constexpr Crazy_bytes_oneofCase crazy_bytes_oneof_case() const noexcept { return crazy_bytes_oneof_case_; }
        void clear_crazy_bytes_oneof() noexcept {
            switch (crazy_bytes_oneof_case_) {
                case Crazy_bytes_oneofCase::crazy_plain_bytes: {
                    destroy_at_(&crazy_bytes_oneof.crazy_plain_bytes);
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_bytes: {
                    destroy_at_(&crazy_bytes_oneof.crazy_bounded_bytes);
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_bytes: {
                    destroy_at_(&crazy_bytes_oneof.crazy_fixed_bytes);
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_repeated_bytes: {
                    destroy_at_(&crazy_bytes_oneof.crazy_repeated_bytes);
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes: {
                    destroy_at_(&crazy_bytes_oneof.crazy_bounded_repeated_bytes);
                    break;
                }
                case Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes: {
                    destroy_at_(&crazy_bytes_oneof.crazy_fixed_repeated_bytes);
                    break;
                }
                case Crazy_bytes_oneofCase::none:
                default: {
                    break;
                }
            }
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::none;
        }

        constexpr ::protocyte::f64 f_double() const noexcept { return f_double_; }
        ::protocyte::Status set_f_double(const ::protocyte::f64 value) noexcept {
            f_double_ = value;
            return {};
        }
        constexpr void clear_f_double() noexcept { f_double_ = {}; }

        constexpr ::protocyte::f32 f_float() const noexcept { return f_float_; }
        ::protocyte::Status set_f_float(const ::protocyte::f32 value) noexcept {
            f_float_ = value;
            return {};
        }
        constexpr void clear_f_float() noexcept { f_float_ = {}; }

        constexpr ::protocyte::i32 f_int32() const noexcept { return f_int32_; }
        ::protocyte::Status set_f_int32(const ::protocyte::i32 value) noexcept {
            f_int32_ = value;
            return {};
        }
        constexpr void clear_f_int32() noexcept { f_int32_ = {}; }

        constexpr ::protocyte::i64 f_int64() const noexcept { return f_int64_; }
        ::protocyte::Status set_f_int64(const ::protocyte::i64 value) noexcept {
            f_int64_ = value;
            return {};
        }
        constexpr void clear_f_int64() noexcept { f_int64_ = {}; }

        constexpr ::protocyte::u32 f_uint32() const noexcept { return f_uint32_; }
        ::protocyte::Status set_f_uint32(const ::protocyte::u32 value) noexcept {
            f_uint32_ = value;
            return {};
        }
        constexpr void clear_f_uint32() noexcept { f_uint32_ = {}; }

        constexpr ::protocyte::u64 f_uint64() const noexcept { return f_uint64_; }
        ::protocyte::Status set_f_uint64(const ::protocyte::u64 value) noexcept {
            f_uint64_ = value;
            return {};
        }
        constexpr void clear_f_uint64() noexcept { f_uint64_ = {}; }

        constexpr ::protocyte::i32 f_sint32() const noexcept { return f_sint32_; }
        ::protocyte::Status set_f_sint32(const ::protocyte::i32 value) noexcept {
            f_sint32_ = value;
            return {};
        }
        constexpr void clear_f_sint32() noexcept { f_sint32_ = {}; }

        constexpr ::protocyte::i64 f_sint64() const noexcept { return f_sint64_; }
        ::protocyte::Status set_f_sint64(const ::protocyte::i64 value) noexcept {
            f_sint64_ = value;
            return {};
        }
        constexpr void clear_f_sint64() noexcept { f_sint64_ = {}; }

        constexpr ::protocyte::u32 f_fixed32() const noexcept { return f_fixed32_; }
        ::protocyte::Status set_f_fixed32(const ::protocyte::u32 value) noexcept {
            f_fixed32_ = value;
            return {};
        }
        constexpr void clear_f_fixed32() noexcept { f_fixed32_ = {}; }

        constexpr ::protocyte::u64 f_fixed64() const noexcept { return f_fixed64_; }
        ::protocyte::Status set_f_fixed64(const ::protocyte::u64 value) noexcept {
            f_fixed64_ = value;
            return {};
        }
        constexpr void clear_f_fixed64() noexcept { f_fixed64_ = {}; }

        constexpr ::protocyte::i32 f_sfixed32() const noexcept { return f_sfixed32_; }
        ::protocyte::Status set_f_sfixed32(const ::protocyte::i32 value) noexcept {
            f_sfixed32_ = value;
            return {};
        }
        constexpr void clear_f_sfixed32() noexcept { f_sfixed32_ = {}; }

        constexpr ::protocyte::i64 f_sfixed64() const noexcept { return f_sfixed64_; }
        ::protocyte::Status set_f_sfixed64(const ::protocyte::i64 value) noexcept {
            f_sfixed64_ = value;
            return {};
        }
        constexpr void clear_f_sfixed64() noexcept { f_sfixed64_ = {}; }

        constexpr bool f_bool() const noexcept { return f_bool_; }
        ::protocyte::Status set_f_bool(const bool value) noexcept {
            f_bool_ = value;
            return {};
        }
        constexpr void clear_f_bool() noexcept { f_bool_ = {}; }

        ::protocyte::Span<const ::protocyte::u8> f_string() const noexcept { return f_string_.view(); }
        typename Config::String &mutable_f_string() noexcept { return f_string_; }
        template<class Value>::protocyte::Status set_f_string(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
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
                return view.status();
            }
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            f_bytes_ = ::protocyte::move(temp);
            return {};
        }
        void clear_f_bytes() noexcept { f_bytes_.clear(); }

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

        constexpr ::protocyte::i32 color_raw() const noexcept { return color_; }
        constexpr ::test::ultimate::UltimateComplexMessage_Color color() const noexcept {
            return static_cast<::test::ultimate::UltimateComplexMessage_Color>(color_);
        }
        ::protocyte::Status set_color_raw(const ::protocyte::i32 value) noexcept {
            color_ = value;
            return {};
        }
        ::protocyte::Status set_color(const ::test::ultimate::UltimateComplexMessage_Color value) noexcept {
            return set_color_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_color() noexcept { color_ = {}; }

        bool has_nested1() const noexcept { return nested1_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> *nested1() const noexcept {
            return has_nested1() ? nested1_.operator->() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>
        ensure_nested1() noexcept {
            if (nested1_.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {*nested1_};
            }
            return nested1_.emplace(*ctx_).transform(
                [this]() noexcept -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                    return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {*nested1_};
                });
        }
        void clear_nested1() noexcept { nested1_.reset(); }

        constexpr bool has_oneof_string() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_string;
        }
        ::protocyte::Span<const ::protocyte::u8> oneof_string() const noexcept {
            return has_oneof_string() ? special_oneof.oneof_string.view() : ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_oneof_string(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_string) typename Config::String {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_string;
            return {};
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
            return {};
        }

        constexpr bool has_oneof_msg() const noexcept { return special_oneof_case_ == Special_oneofCase::oneof_msg; }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> *oneof_msg() const noexcept {
            return has_oneof_msg() && special_oneof.oneof_msg.has_value() ? special_oneof.oneof_msg.operator->() :
                                                                            nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>
        ensure_oneof_msg() noexcept {
            if (!has_oneof_msg()) {
                clear_special_oneof();
                new (&special_oneof.oneof_msg) typename Config::template Optional<
                    ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {};
            }
            special_oneof_case_ = Special_oneofCase::oneof_msg;
            if (special_oneof.oneof_msg.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                    *special_oneof.oneof_msg};
            }
            return special_oneof.oneof_msg.emplace(*ctx_).transform(
                [this]() noexcept -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                    return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                        *special_oneof.oneof_msg};
                });
        }

        constexpr bool has_oneof_bytes() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_bytes;
        }
        ::protocyte::Span<const ::protocyte::u8> oneof_bytes() const noexcept {
            return has_oneof_bytes() ? special_oneof.oneof_bytes.view() : ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_oneof_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            ::protocyte::ByteArray<4u> temp {};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_bytes)::protocyte::ByteArray<4u> {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_bytes;
            return {};
        }

        constexpr bool has_crazy_plain_bytes() const noexcept {
            return crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_plain_bytes;
        }
        ::protocyte::Span<const ::protocyte::u8> crazy_plain_bytes() const noexcept {
            return has_crazy_plain_bytes() ? crazy_bytes_oneof.crazy_plain_bytes.view() :
                                             ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_crazy_plain_bytes(const Value &value) noexcept
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
            clear_crazy_bytes_oneof();
            new (&crazy_bytes_oneof.crazy_plain_bytes) typename Config::Bytes {::protocyte::move(temp)};
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_plain_bytes;
            return {};
        }

        constexpr bool has_crazy_bounded_bytes() const noexcept {
            return crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_bounded_bytes;
        }
        ::protocyte::Span<const ::protocyte::u8> crazy_bounded_bytes() const noexcept {
            return has_crazy_bounded_bytes() ? crazy_bytes_oneof.crazy_bounded_bytes.view() :
                                               ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_crazy_bounded_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            ::protocyte::ByteArray<4u> temp {};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            clear_crazy_bytes_oneof();
            new (&crazy_bytes_oneof.crazy_bounded_bytes)::protocyte::ByteArray<4u> {::protocyte::move(temp)};
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_bytes;
            return {};
        }

        constexpr bool has_crazy_fixed_bytes() const noexcept {
            return crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_fixed_bytes;
        }
        ::protocyte::Span<const ::protocyte::u8> crazy_fixed_bytes() const noexcept {
            return has_crazy_fixed_bytes() ? crazy_bytes_oneof.crazy_fixed_bytes.view() :
                                             ::protocyte::Span<const ::protocyte::u8> {};
        }
        template<class Value>::protocyte::Status set_crazy_fixed_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            ::protocyte::FixedByteArray<4u> temp {};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            clear_crazy_bytes_oneof();
            new (&crazy_bytes_oneof.crazy_fixed_bytes)::protocyte::FixedByteArray<4u> {::protocyte::move(temp)};
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_bytes;
            return {};
        }

        constexpr bool has_crazy_repeated_bytes() const noexcept {
            return crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_repeated_bytes;
        }
        const ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config> *
        crazy_repeated_bytes() const noexcept {
            return has_crazy_repeated_bytes() && crazy_bytes_oneof.crazy_repeated_bytes.has_value() ?
                       crazy_bytes_oneof.crazy_repeated_bytes.operator->() :
                       nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>>>
        ensure_crazy_repeated_bytes() noexcept {
            if (!has_crazy_repeated_bytes()) {
                clear_crazy_bytes_oneof();
                new (&crazy_bytes_oneof.crazy_repeated_bytes) typename Config::template Optional<
                    ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {};
            }
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_repeated_bytes;
            if (crazy_bytes_oneof.crazy_repeated_bytes.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {
                    *crazy_bytes_oneof.crazy_repeated_bytes};
            }
            return crazy_bytes_oneof.crazy_repeated_bytes.emplace(*ctx_).transform(
                [this]() noexcept
                    -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {
                    return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {
                        *crazy_bytes_oneof.crazy_repeated_bytes};
                });
        }

        constexpr bool has_crazy_bounded_repeated_bytes() const noexcept {
            return crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes;
        }
        const ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config> *
        crazy_bounded_repeated_bytes() const noexcept {
            return has_crazy_bounded_repeated_bytes() && crazy_bytes_oneof.crazy_bounded_repeated_bytes.has_value() ?
                       crazy_bytes_oneof.crazy_bounded_repeated_bytes.operator->() :
                       nullptr;
        }
        ::protocyte::Result<
            ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>>>
        ensure_crazy_bounded_repeated_bytes() noexcept {
            if (!has_crazy_bounded_repeated_bytes()) {
                clear_crazy_bytes_oneof();
                new (&crazy_bytes_oneof.crazy_bounded_repeated_bytes) typename Config::template Optional<
                    ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {};
            }
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes;
            if (crazy_bytes_oneof.crazy_bounded_repeated_bytes.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {
                    *crazy_bytes_oneof.crazy_bounded_repeated_bytes};
            }
            return crazy_bytes_oneof.crazy_bounded_repeated_bytes.emplace(*ctx_).transform(
                [this]() noexcept
                    -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {
                    return ::protocyte::Ref<
                        ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {
                        *crazy_bytes_oneof.crazy_bounded_repeated_bytes};
                });
        }

        constexpr bool has_crazy_fixed_repeated_bytes() const noexcept {
            return crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes;
        }
        const ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config> *
        crazy_fixed_repeated_bytes() const noexcept {
            return has_crazy_fixed_repeated_bytes() && crazy_bytes_oneof.crazy_fixed_repeated_bytes.has_value() ?
                       crazy_bytes_oneof.crazy_fixed_repeated_bytes.operator->() :
                       nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>>>
        ensure_crazy_fixed_repeated_bytes() noexcept {
            if (!has_crazy_fixed_repeated_bytes()) {
                clear_crazy_bytes_oneof();
                new (&crazy_bytes_oneof.crazy_fixed_repeated_bytes) typename Config::template Optional<
                    ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {};
            }
            crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes;
            if (crazy_bytes_oneof.crazy_fixed_repeated_bytes.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {
                    *crazy_bytes_oneof.crazy_fixed_repeated_bytes};
            }
            return crazy_bytes_oneof.crazy_fixed_repeated_bytes.emplace(*ctx_).transform(
                [this]() noexcept
                    -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {
                    return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {
                        *crazy_bytes_oneof.crazy_fixed_repeated_bytes};
                });
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

        const typename Config::template Map<bool, typename Config::Bytes> &map_bool_bytes() const noexcept {
            return map_bool_bytes_;
        }
        typename Config::template Map<bool, typename Config::Bytes> &mutable_map_bool_bytes() noexcept {
            return map_bool_bytes_;
        }
        void clear_map_bool_bytes() noexcept { map_bool_bytes_.clear(); }

        const typename Config::template Map<::protocyte::u64,
                                            ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> &
        map_uint64_msg() const noexcept {
            return map_uint64_msg_;
        }
        typename Config::template Map<::protocyte::u64, ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> &
        mutable_map_uint64_msg() noexcept {
            return map_uint64_msg_;
        }
        void clear_map_uint64_msg() noexcept { map_uint64_msg_.clear(); }

        const typename Config::template Map<
            typename Config::String, ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> &
        very_nested_map() const noexcept {
            return very_nested_map_;
        }
        typename Config::template Map<typename Config::String,
                                      ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> &
        mutable_very_nested_map() noexcept {
            return very_nested_map_;
        }
        void clear_very_nested_map() noexcept { very_nested_map_.clear(); }

        bool has_recursive_self() const noexcept { return recursive_self_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage<Config> *recursive_self() const noexcept {
            return has_recursive_self() ? recursive_self_.operator->() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>>>
        ensure_recursive_self() noexcept {
            return recursive_self_.ensure();
        }
        void clear_recursive_self() noexcept { recursive_self_.reset(); }

        const typename Config::template Vector<
            ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> &
        lots_of_nested() const noexcept {
            return lots_of_nested_;
        }
        typename Config::template Vector<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> &
        mutable_lots_of_nested() noexcept {
            return lots_of_nested_;
        }
        void clear_lots_of_nested() noexcept { lots_of_nested_.clear(); }

        const typename Config::template Vector<::protocyte::i32> &colors() const noexcept { return colors_; }
        typename Config::template Vector<::protocyte::i32> &mutable_colors() noexcept { return colors_; }
        void clear_colors() noexcept { colors_.clear(); }

        constexpr ::protocyte::i32 opt_int32() const noexcept { return opt_int32_; }
        constexpr bool has_opt_int32() const noexcept { return has_opt_int32_; }
        ::protocyte::Status set_opt_int32(const ::protocyte::i32 value) noexcept {
            opt_int32_ = value;
            has_opt_int32_ = true;
            return {};
        }
        constexpr void clear_opt_int32() noexcept {
            opt_int32_ = {};
            has_opt_int32_ = false;
        }

        ::protocyte::Span<const ::protocyte::u8> opt_string() const noexcept { return opt_string_.view(); }
        bool has_opt_string() const noexcept { return has_opt_string_; }
        typename Config::String &mutable_opt_string() noexcept {
            has_opt_string_ = true;
            return opt_string_;
        }
        template<class Value>::protocyte::Status set_opt_string(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            opt_string_ = ::protocyte::move(temp);
            has_opt_string_ = true;
            return {};
        }
        void clear_opt_string() noexcept {
            opt_string_.clear();
            has_opt_string_ = false;
        }

        bool has_extreme_nesting() const noexcept { return extreme_nesting_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config> *
        extreme_nesting() const noexcept {
            return has_extreme_nesting() ? extreme_nesting_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>>>
        ensure_extreme_nesting() noexcept {
            if (extreme_nesting_.has_value()) {
                return ::protocyte::Ref<
                    ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>> {
                    *extreme_nesting_};
            }
            return extreme_nesting_.emplace(*ctx_).transform(
                [this]() noexcept
                    -> ::protocyte::Ref<
                        ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>> {
                    return ::protocyte::Ref<
                        ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>> {
                        *extreme_nesting_};
                });
        }
        void clear_extreme_nesting() noexcept { extreme_nesting_.reset(); }

        bool has_sha256() const noexcept { return sha256_.has_value(); }
        ::protocyte::Span<const ::protocyte::u8> sha256() const noexcept { return sha256_.view(); }
        ::protocyte::Span<::protocyte::u8> mutable_sha256() noexcept {
            if (ctx_->limits.max_string_bytes < 32u) {
                return ::protocyte::Span<::protocyte::u8> {};
            }
            return sha256_.mutable_view();
        }
        ::protocyte::Status resize_sha256_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            return sha256_.resize_for_overwrite(size);
        }
        template<class Value>::protocyte::Status set_sha256(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            return sha256_.assign(*view);
        }
        void clear_sha256() noexcept { sha256_.clear(); }

        const ::protocyte::Array<::protocyte::i32, 8u> &integer_array() const noexcept { return integer_array_; }
        ::protocyte::Array<::protocyte::i32, 8u> &mutable_integer_array() noexcept { return integer_array_; }
        void clear_integer_array() noexcept { integer_array_.clear(); }

        ::protocyte::Span<const ::protocyte::u8> byte_array() const noexcept { return byte_array_.view(); }
        ::protocyte::usize byte_array_size() const noexcept { return byte_array_.size(); }
        static constexpr ::protocyte::usize byte_array_max_size() noexcept { return 4u; }
        ::protocyte::Status resize_byte_array(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = byte_array_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Status resize_byte_array_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = byte_array_.resize_for_overwrite(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_byte_array() noexcept { return byte_array_.mutable_view(); }
        template<class Value>::protocyte::Status set_byte_array(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = byte_array_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_byte_array() noexcept { byte_array_.clear(); }

        const ::protocyte::Array<::protocyte::u32, 3u> &fixed_integer_array() const noexcept {
            return fixed_integer_array_;
        }
        ::protocyte::Array<::protocyte::u32, 3u> &mutable_fixed_integer_array() noexcept {
            return fixed_integer_array_;
        }
        void clear_fixed_integer_array() noexcept { fixed_integer_array_.clear(); }

        ::protocyte::Span<const ::protocyte::u8> float_expr_array() const noexcept { return float_expr_array_.view(); }
        ::protocyte::usize float_expr_array_size() const noexcept { return float_expr_array_.size(); }
        static constexpr ::protocyte::usize float_expr_array_max_size() noexcept { return 2u; }
        ::protocyte::Status resize_float_expr_array(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = float_expr_array_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Status resize_float_expr_array_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = float_expr_array_.resize_for_overwrite(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_float_expr_array() noexcept {
            return float_expr_array_.mutable_view();
        }
        template<class Value>::protocyte::Status set_float_expr_array(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = float_expr_array_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_float_expr_array() noexcept { float_expr_array_.clear(); }

        const typename Config::template Vector<typename Config::Bytes> &repeated_byte_array() const noexcept {
            return repeated_byte_array_;
        }
        typename Config::template Vector<typename Config::Bytes> &mutable_repeated_byte_array() noexcept {
            return repeated_byte_array_;
        }
        void clear_repeated_byte_array() noexcept { repeated_byte_array_.clear(); }

        const ::protocyte::Array<typename Config::Bytes, 3u> &bounded_repeated_byte_array() const noexcept {
            return bounded_repeated_byte_array_;
        }
        ::protocyte::Array<typename Config::Bytes, 3u> &mutable_bounded_repeated_byte_array() noexcept {
            return bounded_repeated_byte_array_;
        }
        void clear_bounded_repeated_byte_array() noexcept { bounded_repeated_byte_array_.clear(); }

        const ::protocyte::Array<typename Config::Bytes, 3u> &fixed_repeated_byte_array() const noexcept {
            return fixed_repeated_byte_array_;
        }
        ::protocyte::Array<typename Config::Bytes, 3u> &mutable_fixed_repeated_byte_array() noexcept {
            return fixed_repeated_byte_array_;
        }
        void clear_fixed_repeated_byte_array() noexcept { fixed_repeated_byte_array_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::f_double: {
                        if (const auto st = ::protocyte::read_double_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_double_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_float: {
                        if (const auto st = ::protocyte::read_float_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_float_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_int32: {
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_int32_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_int64: {
                        if (const auto st = ::protocyte::read_int64_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_int64_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_uint32: {
                        if (const auto st = ::protocyte::read_uint32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_uint32_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_uint64: {
                        if (const auto st = ::protocyte::read_uint64_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_uint64_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_sint32: {
                        if (const auto st = ::protocyte::read_sint32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_sint32_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_sint64: {
                        if (const auto st = ::protocyte::read_sint64_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_sint64_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_fixed32: {
                        if (const auto st = ::protocyte::read_fixed32_value_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_fixed32_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_fixed64: {
                        if (const auto st = ::protocyte::read_fixed64_value_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_fixed64_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_sfixed32: {
                        if (const auto st = ::protocyte::read_sfixed32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_sfixed32_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_sfixed64: {
                        if (const auto st = ::protocyte::read_sfixed64_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_sfixed64_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_bool: {
                        if (const auto st = ::protocyte::read_bool_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { f_bool_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_string: {
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, f_string_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::f_bytes: {
                        if (const auto st =
                                ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type, field_number, f_bytes_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::r_int32_unpacked: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            typename Config::template Vector<::protocyte::i32> packed_r_int32_unpacked_values {ctx_};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                if (const auto st = ::protocyte::read_int32(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_r_int32_unpacked_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_r_int32_unpacked_values_commit_size = ::protocyte::checked_add(
                                r_int32_unpacked_.size(), packed_r_int32_unpacked_values.size());
                            if (!packed_r_int32_unpacked_values_commit_size) {
                                return packed_r_int32_unpacked_values_commit_size.status();
                            }
                            if (const auto st = r_int32_unpacked_.reserve(*packed_r_int32_unpacked_values_commit_size);
                                !st) {
                                return st;
                            }
                            for (const auto &value : packed_r_int32_unpacked_values) {
                                if (const auto st = r_int32_unpacked_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = r_int32_unpacked_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::r_int32_packed: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            typename Config::template Vector<::protocyte::i32> packed_r_int32_packed_values {ctx_};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                if (const auto st = ::protocyte::read_int32(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_r_int32_packed_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_r_int32_packed_values_commit_size =
                                ::protocyte::checked_add(r_int32_packed_.size(), packed_r_int32_packed_values.size());
                            if (!packed_r_int32_packed_values_commit_size) {
                                return packed_r_int32_packed_values_commit_size.status();
                            }
                            if (const auto st = r_int32_packed_.reserve(*packed_r_int32_packed_values_commit_size);
                                !st) {
                                return st;
                            }
                            for (const auto &value : packed_r_int32_packed_values) {
                                if (const auto st = r_int32_packed_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = r_int32_packed_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::r_double: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            typename Config::template Vector<::protocyte::f64> packed_r_double_values {ctx_};
                            const auto packed_reserve_r_double =
                                ::protocyte::checked_add(packed_r_double_values.size(), *len / 8u);
                            if (!packed_reserve_r_double) {
                                return packed_reserve_r_double.status();
                            }
                            if (const auto st = packed_r_double_values.reserve(*packed_reserve_r_double); !st) {
                                return st;
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::f64 value {};
                                if (const auto st = ::protocyte::read_double(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_r_double_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_r_double_values_commit_size =
                                ::protocyte::checked_add(r_double_.size(), packed_r_double_values.size());
                            if (!packed_r_double_values_commit_size) {
                                return packed_r_double_values_commit_size.status();
                            }
                            if (const auto st = r_double_.reserve(*packed_r_double_values_commit_size); !st) {
                                return st;
                            }
                            for (const auto &value : packed_r_double_values) {
                                if (const auto st = r_double_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::f64 value {};
                        if (const auto st = ::protocyte::read_double_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = r_double_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::color: {
                        if (const auto st = ::protocyte::read_enum_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { color_ = decoded; });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::nested1: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> nested1_value {*ctx_};
                        if (nested1_.has_value()) {
                            if (const auto st = nested1_value.copy_from(*nested1_); !st) {
                                return st;
                            }
                        }
                        if (const auto st =
                                ::protocyte::read_message<Config>(*ctx_, reader, field_number, nested1_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = nested1_.emplace(::protocyte::move(nested1_value)); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::oneof_string: {
                        typename Config::String oneof_string_value {ctx_};
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, oneof_string_value);
                            !st) {
                            return st;
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_string)
                            typename Config::String {::protocyte::move(oneof_string_value)};
                        special_oneof_case_ = Special_oneofCase::oneof_string;
                        break;
                    }
                    case FieldNumber::oneof_int32: {
                        ::protocyte::i32 oneof_int32_value {};
                        if (const auto st =
                                ::protocyte::read_int32_field(reader, wire_type, field_number)
                                    .transform([&](const auto decoded) noexcept { oneof_int32_value = decoded; });
                            !st) {
                            return st;
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_int32)::protocyte::i32 {::protocyte::move(oneof_int32_value)};
                        special_oneof_case_ = Special_oneofCase::oneof_int32;
                        break;
                    }
                    case FieldNumber::oneof_msg: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> oneof_msg_value {*ctx_};
                        if (has_oneof_msg() && special_oneof.oneof_msg.has_value()) {
                            if (const auto st = oneof_msg_value.copy_from(*special_oneof.oneof_msg); !st) {
                                return st;
                            }
                        }
                        if (const auto st =
                                ::protocyte::read_message<Config>(*ctx_, reader, field_number, oneof_msg_value);
                            !st) {
                            return st;
                        }
                        typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>
                            oneof_msg_committed {};
                        if (const auto st = oneof_msg_committed.emplace(::protocyte::move(oneof_msg_value)); !st) {
                            return st;
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_msg) typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                            ::protocyte::move(oneof_msg_committed)};
                        special_oneof_case_ = Special_oneofCase::oneof_msg;
                        break;
                    }
                    case FieldNumber::oneof_bytes: {
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
                        if (*len > 4u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<4u> oneof_bytes_value {};
                        if (const auto st = oneof_bytes_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = oneof_bytes_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_bytes)::protocyte::ByteArray<4u> {
                            ::protocyte::move(oneof_bytes_value)};
                        special_oneof_case_ = Special_oneofCase::oneof_bytes;
                        break;
                    }
                    case FieldNumber::map_str_int32: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        typename Config::String key {ctx_};
                        ::protocyte::i32 value {};
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(*ctx_, entry_reader, key);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    if (const auto st =
                                            ::protocyte::read_int32(entry_reader)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
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
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (const auto insert =
                                map_str_int32_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::map_int32_str: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::i32 key {};
                        typename Config::String value {ctx_};
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    if (const auto st =
                                            ::protocyte::read_int32(entry_reader)
                                                .transform([&](const auto decoded) noexcept { key = decoded; });
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
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
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (const auto insert =
                                map_int32_str_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::map_bool_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        bool key {};
                        typename Config::Bytes value {ctx_};
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    if (const auto st =
                                            ::protocyte::read_bool(entry_reader)
                                                .transform([&](const auto decoded) noexcept { key = decoded; });
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    if (const auto st = ::protocyte::read_bytes<Config>(*ctx_, entry_reader, value);
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
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (const auto insert =
                                map_bool_bytes_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::map_uint64_msg: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::u64 key {};
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> value {*ctx_};
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    if (const auto st =
                                            ::protocyte::read_uint64(entry_reader)
                                                .transform([&](const auto decoded) noexcept { key = decoded; });
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    if (const auto st = ::protocyte::read_message<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                            value);
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
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (const auto insert =
                                map_uint64_msg_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::very_nested_map: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        auto entry = ::protocyte::open_nested_message<Config>(*ctx_, reader, field_number);
                        if (!entry) {
                            return entry.status();
                        }
                        auto &entry_reader = entry->reader();
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        typename Config::String key {ctx_};
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> value {*ctx_};
                        while (!entry_reader.eof()) {
                            const auto entry_tag = ::protocyte::read_tag(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto [entry_field, entry_wire] = *entry_tag;
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(*ctx_, entry_reader, key);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::unexpected(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    if (const auto st = ::protocyte::read_message<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                            value);
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
                        if (const auto st = entry->finish(); !st) {
                            return st;
                        }
                        if (const auto insert =
                                very_nested_map_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::recursive_self: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage<Config> recursive_self_value {*ctx_};
                        if (recursive_self_.has_value()) {
                            if (const auto st = recursive_self_value.copy_from(*recursive_self_); !st) {
                                return st;
                            }
                        }
                        if (const auto st =
                                ::protocyte::read_message<Config>(*ctx_, reader, field_number, recursive_self_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = recursive_self_.assign(::protocyte::move(recursive_self_value)); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::lots_of_nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> value {*ctx_};
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number, value)
                                                .and_then([&]() noexcept -> ::protocyte::Status {
                                                    return lots_of_nested_.push_back(::protocyte::move(value));
                                                });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::colors: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            typename Config::template Vector<::protocyte::i32> packed_colors_values {ctx_};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                if (const auto st = ::protocyte::read_enum(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_colors_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_colors_values_commit_size =
                                ::protocyte::checked_add(colors_.size(), packed_colors_values.size());
                            if (!packed_colors_values_commit_size) {
                                return packed_colors_values_commit_size.status();
                            }
                            if (const auto st = colors_.reserve(*packed_colors_values_commit_size); !st) {
                                return st;
                            }
                            for (const auto &value : packed_colors_values) {
                                if (const auto st = colors_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        if (const auto st = ::protocyte::read_enum_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = colors_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::opt_int32: {
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { opt_int32_ = decoded; });
                            !st) {
                            return st;
                        }
                        has_opt_int32_ = true;
                        break;
                    }
                    case FieldNumber::opt_string: {
                        if (const auto st = ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type,
                                                                                   field_number, opt_string_);
                            !st) {
                            return st;
                        }
                        has_opt_string_ = true;
                        break;
                    }
                    case FieldNumber::extreme_nesting: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>
                            extreme_nesting_value {*ctx_};
                        if (extreme_nesting_.has_value()) {
                            if (const auto st = extreme_nesting_value.copy_from(*extreme_nesting_); !st) {
                                return st;
                            }
                        }
                        if (const auto st =
                                ::protocyte::read_message<Config>(*ctx_, reader, field_number, extreme_nesting_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = extreme_nesting_.emplace(::protocyte::move(extreme_nesting_value)); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::sha256: {
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
                        if (*len != 32u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::FixedByteArray<32u> sha256_value {};
                        if (const auto st = sha256_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = sha256_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        sha256_ = ::protocyte::move(sha256_value);
                        break;
                    }
                    case FieldNumber::integer_array: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::Array<::protocyte::i32, 8u> packed_integer_array_values {};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                if (const auto st = ::protocyte::read_int32(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_integer_array_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_integer_array_values_commit_size =
                                ::protocyte::checked_add(integer_array_.size(), packed_integer_array_values.size());
                            if (!packed_integer_array_values_commit_size) {
                                return packed_integer_array_values_commit_size.status();
                            }
                            if (*packed_integer_array_values_commit_size > 8u) {
                                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                               field_number);
                            }
                            for (const auto &value : packed_integer_array_values) {
                                if (const auto st = integer_array_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = integer_array_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::byte_array: {
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
                        if (*len > 4u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<4u> byte_array_value {};
                        if (const auto st = byte_array_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = byte_array_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        byte_array_ = ::protocyte::move(byte_array_value);
                        break;
                    }
                    case FieldNumber::fixed_integer_array: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::Array<::protocyte::u32, 3u> packed_fixed_integer_array_values {};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::u32 value {};
                                if (const auto st = ::protocyte::read_uint32(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_fixed_integer_array_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_fixed_integer_array_values_commit_size = ::protocyte::checked_add(
                                fixed_integer_array_.size(), packed_fixed_integer_array_values.size());
                            if (!packed_fixed_integer_array_values_commit_size) {
                                return packed_fixed_integer_array_values_commit_size.status();
                            }
                            if (*packed_fixed_integer_array_values_commit_size > 3u) {
                                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                               field_number);
                            }
                            for (const auto &value : packed_fixed_integer_array_values) {
                                if (const auto st = fixed_integer_array_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::u32 value {};
                        if (const auto st = ::protocyte::read_uint32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = fixed_integer_array_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::float_expr_array: {
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
                        if (*len > 2u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<2u> float_expr_array_value {};
                        if (const auto st = float_expr_array_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = float_expr_array_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        float_expr_array_ = ::protocyte::move(float_expr_array_value);
                        break;
                    }
                    case FieldNumber::repeated_byte_array: {
                        typename Config::Bytes value {ctx_};
                        if (const auto st =
                                ::protocyte::read_bytes_field<Config>(*ctx_, reader, wire_type, field_number, value)
                                    .and_then([&]() noexcept -> ::protocyte::Status {
                                        return repeated_byte_array_.push_back(::protocyte::move(value));
                                    });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::bounded_repeated_byte_array: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        typename Config::Bytes value {ctx_};
                        if (const auto st =
                                ::protocyte::read_bytes<Config>(*ctx_, reader, value)
                                    .and_then([&]() noexcept -> ::protocyte::Status {
                                        return bounded_repeated_byte_array_.push_back(::protocyte::move(value));
                                    });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::fixed_repeated_byte_array: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        typename Config::Bytes value {ctx_};
                        if (const auto st =
                                ::protocyte::read_bytes<Config>(*ctx_, reader, value)
                                    .and_then([&]() noexcept -> ::protocyte::Status {
                                        return fixed_repeated_byte_array_.push_back(::protocyte::move(value));
                                    });
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::crazy_plain_bytes: {
                        typename Config::Bytes crazy_plain_bytes_value {ctx_};
                        if (const auto st = ::protocyte::read_bytes_field<Config>(
                                *ctx_, reader, wire_type, field_number, crazy_plain_bytes_value);
                            !st) {
                            return st;
                        }
                        clear_crazy_bytes_oneof();
                        new (&crazy_bytes_oneof.crazy_plain_bytes)
                            typename Config::Bytes {::protocyte::move(crazy_plain_bytes_value)};
                        crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_plain_bytes;
                        break;
                    }
                    case FieldNumber::crazy_bounded_bytes: {
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
                        if (*len > 4u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<4u> crazy_bounded_bytes_value {};
                        if (const auto st = crazy_bounded_bytes_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = crazy_bounded_bytes_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        clear_crazy_bytes_oneof();
                        new (&crazy_bytes_oneof.crazy_bounded_bytes)::protocyte::ByteArray<4u> {
                            ::protocyte::move(crazy_bounded_bytes_value)};
                        crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_bytes;
                        break;
                    }
                    case FieldNumber::crazy_fixed_bytes: {
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
                        if (*len != 4u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::FixedByteArray<4u> crazy_fixed_bytes_value {};
                        if (const auto st = crazy_fixed_bytes_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = crazy_fixed_bytes_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        clear_crazy_bytes_oneof();
                        new (&crazy_bytes_oneof.crazy_fixed_bytes)::protocyte::FixedByteArray<4u> {
                            ::protocyte::move(crazy_fixed_bytes_value)};
                        crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_bytes;
                        break;
                    }
                    case FieldNumber::crazy_repeated_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>
                            crazy_repeated_bytes_value {*ctx_};
                        if (has_crazy_repeated_bytes() && crazy_bytes_oneof.crazy_repeated_bytes.has_value()) {
                            if (const auto st =
                                    crazy_repeated_bytes_value.copy_from(*crazy_bytes_oneof.crazy_repeated_bytes);
                                !st) {
                                return st;
                            }
                        }
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number,
                                                                              crazy_repeated_bytes_value);
                            !st) {
                            return st;
                        }
                        typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>>
                            crazy_repeated_bytes_committed {};
                        if (const auto st =
                                crazy_repeated_bytes_committed.emplace(::protocyte::move(crazy_repeated_bytes_value));
                            !st) {
                            return st;
                        }
                        clear_crazy_bytes_oneof();
                        new (&crazy_bytes_oneof.crazy_repeated_bytes) typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>> {
                            ::protocyte::move(crazy_repeated_bytes_committed)};
                        crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_repeated_bytes;
                        break;
                    }
                    case FieldNumber::crazy_bounded_repeated_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>
                            crazy_bounded_repeated_bytes_value {*ctx_};
                        if (has_crazy_bounded_repeated_bytes() &&
                            crazy_bytes_oneof.crazy_bounded_repeated_bytes.has_value()) {
                            if (const auto st = crazy_bounded_repeated_bytes_value.copy_from(
                                    *crazy_bytes_oneof.crazy_bounded_repeated_bytes);
                                !st) {
                                return st;
                            }
                        }
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number,
                                                                              crazy_bounded_repeated_bytes_value);
                            !st) {
                            return st;
                        }
                        typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>>
                            crazy_bounded_repeated_bytes_committed {};
                        if (const auto st = crazy_bounded_repeated_bytes_committed.emplace(
                                ::protocyte::move(crazy_bounded_repeated_bytes_value));
                            !st) {
                            return st;
                        }
                        clear_crazy_bytes_oneof();
                        new (&crazy_bytes_oneof.crazy_bounded_repeated_bytes) typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>> {
                            ::protocyte::move(crazy_bounded_repeated_bytes_committed)};
                        crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes;
                        break;
                    }
                    case FieldNumber::crazy_fixed_repeated_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>
                            crazy_fixed_repeated_bytes_value {*ctx_};
                        if (has_crazy_fixed_repeated_bytes() &&
                            crazy_bytes_oneof.crazy_fixed_repeated_bytes.has_value()) {
                            if (const auto st = crazy_fixed_repeated_bytes_value.copy_from(
                                    *crazy_bytes_oneof.crazy_fixed_repeated_bytes);
                                !st) {
                                return st;
                            }
                        }
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number,
                                                                              crazy_fixed_repeated_bytes_value);
                            !st) {
                            return st;
                        }
                        typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>>
                            crazy_fixed_repeated_bytes_committed {};
                        if (const auto st = crazy_fixed_repeated_bytes_committed.emplace(
                                ::protocyte::move(crazy_fixed_repeated_bytes_value));
                            !st) {
                            return st;
                        }
                        clear_crazy_bytes_oneof();
                        new (&crazy_bytes_oneof.crazy_fixed_repeated_bytes) typename Config::template Optional<
                            ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>> {
                            ::protocyte::move(crazy_fixed_repeated_bytes_committed)};
                        crazy_bytes_oneof_case_ = Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes;
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
            if (fixed_integer_array_.size() != 0u && fixed_integer_array_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array));
            }
            if (fixed_repeated_byte_array_.size() != 0u && fixed_repeated_byte_array_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_repeated_byte_array));
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer &writer) const noexcept {
            if (fixed_integer_array_.size() != 0u && fixed_integer_array_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array));
            }
            if (fixed_repeated_byte_array_.size() != 0u && fixed_repeated_byte_array_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_repeated_byte_array));
            }
            if (::std::bit_cast<::protocyte::u64>(f_double_) != 0u) {
                if (const auto st = ::protocyte::write_double_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_double), f_double_);
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
            if (f_bool_) {
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_bool), f_bool_);
                    !st) {
                    return st;
                }
            }
            if (!f_string_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_string), f_string_.view());
                    !st) {
                    return st;
                }
            }
            if (!f_bytes_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_bytes), f_bytes_.view());
                    !st) {
                    return st;
                }
            }
            for (const auto &r_int32_unpacked_value : r_int32_unpacked_) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked), r_int32_unpacked_value);
                    !st) {
                    return st;
                }
            }
            if (!r_int32_packed_.empty()) {
                ::protocyte::usize packed_size_r_int32_packed {};
                for (const auto &packed_value_r_int32_packed : r_int32_packed_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_r_int32_packed,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_r_int32_packed)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    packed_size_r_int32_packed = *st_size;
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
                for (const auto &packed_value_r_int32_packed : r_int32_packed_) {
                    if (const auto st = ::protocyte::write_int32(writer, packed_value_r_int32_packed); !st) {
                        return st;
                    }
                }
            }
            if (!r_double_.empty()) {
                ::protocyte::usize packed_size_r_double {};
                const auto packed_size_r_double_result = ::protocyte::checked_mul(r_double_.size(), 8u);
                if (!packed_size_r_double_result) {
                    return packed_size_r_double_result.status();
                }
                packed_size_r_double = *packed_size_r_double_result;
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
                for (const auto &packed_value_r_double : r_double_) {
                    if (const auto st = ::protocyte::write_double(writer, packed_value_r_double); !st) {
                        return st;
                    }
                }
            }
            if (color_ != 0) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::color), color_);
                    !st) {
                    return st;
                }
            }
            if (nested1_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested1), *nested1_);
                    !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_string),
                        special_oneof.oneof_string.view());
                    !st) {
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
            if (special_oneof_case_ == Special_oneofCase::oneof_msg) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_msg), *special_oneof.oneof_msg);
                    !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                if (const auto st =
                        ::protocyte::write_bytes_field(writer, static_cast<::protocyte::u32>(FieldNumber::oneof_bytes),
                                                       special_oneof.oneof_bytes.view());
                    !st) {
                    return st;
                }
            }
            for (const auto entry : map_str_int32_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::map_str_int32), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key.view());
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value);
                    !st) {
                    return st;
                }
            }
            for (const auto entry : map_int32_str_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::map_int32_str), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.view());
                    !st) {
                    return st;
                }
            }
            for (const auto entry : map_bool_bytes_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::map_bool_bytes), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bool_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.view());
                    !st) {
                    return st;
                }
            }
            for (const auto entry : map_uint64_msg_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::message_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value)
                                             .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, nested_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::map_uint64_msg), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_uint64_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value);
                    !st) {
                    return st;
                }
            }
            for (const auto entry : very_nested_map_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::message_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value)
                                             .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, nested_size);
                                             });
                    if (!st_size) {
                        return st_size.status();
                    }
                    entry_payload = *st_size;
                }
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::very_nested_map),
                                               ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key.view());
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value);
                    !st) {
                    return st;
                }
            }
            if (recursive_self_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::recursive_self), *recursive_self_);
                    !st) {
                    return st;
                }
            }
            for (const auto &lots_of_nested_value : lots_of_nested_) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::lots_of_nested), lots_of_nested_value);
                    !st) {
                    return st;
                }
            }
            if (!colors_.empty()) {
                ::protocyte::usize packed_size_colors {};
                for (const auto &packed_value_colors : colors_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_colors,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_colors)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    packed_size_colors = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::colors),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_colors));
                    !st) {
                    return st;
                }
                for (const auto &packed_value_colors : colors_) {
                    if (const auto st = ::protocyte::write_enum(writer, packed_value_colors); !st) {
                        return st;
                    }
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
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::opt_string), opt_string_.view());
                    !st) {
                    return st;
                }
            }
            if (extreme_nesting_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::extreme_nesting), *extreme_nesting_);
                    !st) {
                    return st;
                }
            }
            if (sha256_.has_value()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::sha256), sha256_.view());
                    !st) {
                    return st;
                }
            }
            if (!integer_array_.empty()) {
                ::protocyte::usize packed_size_integer_array {};
                for (const auto &packed_value_integer_array : integer_array_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_integer_array,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_integer_array)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    packed_size_integer_array = *st_size;
                }
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::integer_array), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_integer_array));
                    !st) {
                    return st;
                }
                for (const auto &packed_value_integer_array : integer_array_) {
                    if (const auto st = ::protocyte::write_int32(writer, packed_value_integer_array); !st) {
                        return st;
                    }
                }
            }
            if (!byte_array_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::byte_array), byte_array_.view());
                    !st) {
                    return st;
                }
            }
            if (!fixed_integer_array_.empty()) {
                ::protocyte::usize packed_size_fixed_integer_array {};
                for (const auto &packed_value_fixed_integer_array : fixed_integer_array_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_fixed_integer_array,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_fixed_integer_array)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    packed_size_fixed_integer_array = *st_size;
                }
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array),
                                               ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(
                        writer, static_cast<::protocyte::u64>(packed_size_fixed_integer_array));
                    !st) {
                    return st;
                }
                for (const auto &packed_value_fixed_integer_array : fixed_integer_array_) {
                    if (const auto st = ::protocyte::write_uint32(writer, packed_value_fixed_integer_array); !st) {
                        return st;
                    }
                }
            }
            if (!float_expr_array_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::float_expr_array), float_expr_array_.view());
                    !st) {
                    return st;
                }
            }
            for (const auto &repeated_byte_array_value : repeated_byte_array_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::repeated_byte_array),
                        repeated_byte_array_value.view());
                    !st) {
                    return st;
                }
            }
            for (const auto &bounded_repeated_byte_array_value : bounded_repeated_byte_array_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::bounded_repeated_byte_array),
                        bounded_repeated_byte_array_value.view());
                    !st) {
                    return st;
                }
            }
            for (const auto &fixed_repeated_byte_array_value : fixed_repeated_byte_array_) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::fixed_repeated_byte_array),
                        fixed_repeated_byte_array_value.view());
                    !st) {
                    return st;
                }
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_plain_bytes) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::crazy_plain_bytes),
                        crazy_bytes_oneof.crazy_plain_bytes.view());
                    !st) {
                    return st;
                }
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_bounded_bytes) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::crazy_bounded_bytes),
                        crazy_bytes_oneof.crazy_bounded_bytes.view());
                    !st) {
                    return st;
                }
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_fixed_bytes) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::crazy_fixed_bytes),
                        crazy_bytes_oneof.crazy_fixed_bytes.view());
                    !st) {
                    return st;
                }
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_repeated_bytes) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::crazy_repeated_bytes),
                        *crazy_bytes_oneof.crazy_repeated_bytes);
                    !st) {
                    return st;
                }
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::crazy_bounded_repeated_bytes),
                        *crazy_bytes_oneof.crazy_bounded_repeated_bytes);
                    !st) {
                    return st;
                }
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::crazy_fixed_repeated_bytes),
                        *crazy_bytes_oneof.crazy_fixed_repeated_bytes);
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (fixed_integer_array_.size() != 0u && fixed_integer_array_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array));
            }
            if (fixed_repeated_byte_array_.size() != 0u && fixed_repeated_byte_array_.size() != 3u) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_repeated_byte_array));
            }
            ::protocyte::usize total {};
            if (::std::bit_cast<::protocyte::u64>(f_double_) != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_double)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (::std::bit_cast<::protocyte::u32>(f_float_) != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_float)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_int32_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_int32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_int64_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_int64)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int64_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_uint32_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_uint32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_uint64_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_uint64)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint64_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_sint32_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sint32)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag32(f_sint32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_sint64_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sint64)) +
                               ::protocyte::varint_size(::protocyte::encode_zigzag64(f_sint64_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_fixed32_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_fixed32)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_fixed64_ != 0u) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_fixed64)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_sfixed32_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sfixed32)) + 4u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_sfixed64_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_sfixed64)) + 8u);
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (f_bool_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_bool)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(f_bool_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!f_string_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::f_string), f_string_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!f_bytes_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::f_bytes), f_bytes_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto &r_int32_unpacked_value : r_int32_unpacked_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_unpacked_value)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
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
                        return ::protocyte::unexpected(st_size.error());
                    }
                    packed_size_r_int32_packed = *st_size;
                }
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_packed),
                                                             packed_size_r_int32_packed)
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!r_double_.empty()) {
                ::protocyte::usize packed_size_r_double {};
                const auto packed_size_r_double_result = ::protocyte::checked_mul(r_double_.size(), 8u);
                if (!packed_size_r_double_result) {
                    return ::protocyte::unexpected(packed_size_r_double_result.error());
                }
                packed_size_r_double = *packed_size_r_double_result;
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::r_double), packed_size_r_double)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (color_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::color)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(color_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (nested1_.has_value()) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::nested1), *nested1_)
                        .and_then([&](const ::protocyte::usize nested_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, nested_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::oneof_string),
                                                             special_oneof.oneof_string.size())
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_int32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(special_oneof.oneof_int32)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_msg) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::oneof_msg),
                                                    *special_oneof.oneof_msg)
                        .and_then([&](const ::protocyte::usize nested_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, nested_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::oneof_bytes),
                                                             special_oneof.oneof_bytes.size())
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto entry : map_str_int32_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::map_str_int32), entry_payload)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto entry : map_int32_str_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::map_int32_str), entry_payload)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto entry : map_bool_bytes_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::map_bool_bytes), entry_payload)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto entry : map_uint64_msg_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::add_size(
                        entry_payload, ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                           ::protocyte::varint_size(static_cast<::protocyte::u64>(entry.key)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::message_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value)
                                             .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, nested_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::map_uint64_msg), entry_payload)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto entry : very_nested_map_) {
                enum struct EntryFieldNumber : ::protocyte::u32 {
                    key = 1u,
                    value = 2u,
                };
                ::protocyte::usize entry_payload {};
                {
                    const auto st_size = ::protocyte::length_delimited_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::key), entry.key.size())
                                             .and_then([&](const ::protocyte::usize field_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, field_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                {
                    const auto st_size = ::protocyte::message_field_size(
                                             static_cast<::protocyte::u32>(EntryFieldNumber::value), entry.value)
                                             .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                           -> ::protocyte::Result<::protocyte::usize> {
                                                 return ::protocyte::add_size(entry_payload, nested_size);
                                             });
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    entry_payload = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::very_nested_map), entry_payload)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (recursive_self_.has_value()) {
                const auto st_size = ::protocyte::message_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::recursive_self), *recursive_self_)
                                         .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, nested_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto &lots_of_nested_value : lots_of_nested_) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::lots_of_nested),
                                                    lots_of_nested_value)
                        .and_then([&](const ::protocyte::usize nested_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, nested_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!colors_.empty()) {
                ::protocyte::usize packed_size_colors {};
                for (const auto &colors_value : colors_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_colors, ::protocyte::varint_size(static_cast<::protocyte::u64>(colors_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    packed_size_colors = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::colors), packed_size_colors)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_opt_int32_) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::opt_int32)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(opt_int32_)));
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (has_opt_string_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::opt_string), opt_string_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (extreme_nesting_.has_value()) {
                const auto st_size = ::protocyte::message_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::extreme_nesting), *extreme_nesting_)
                                         .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, nested_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (sha256_.has_value()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::sha256), sha256_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!integer_array_.empty()) {
                ::protocyte::usize packed_size_integer_array {};
                for (const auto &integer_array_value : integer_array_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_integer_array,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(integer_array_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    packed_size_integer_array = *st_size;
                }
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::integer_array),
                                                             packed_size_integer_array)
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!byte_array_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::byte_array), byte_array_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!fixed_integer_array_.empty()) {
                ::protocyte::usize packed_size_fixed_integer_array {};
                for (const auto &fixed_integer_array_value : fixed_integer_array_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_fixed_integer_array,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(fixed_integer_array_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    packed_size_fixed_integer_array = *st_size;
                }
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array),
                                         packed_size_fixed_integer_array)
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!float_expr_array_.empty()) {
                const auto st_size =
                    ::protocyte::length_delimited_field_size(
                        static_cast<::protocyte::u32>(FieldNumber::float_expr_array), float_expr_array_.size())
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto &repeated_byte_array_value : repeated_byte_array_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::repeated_byte_array),
                                         repeated_byte_array_value.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto &bounded_repeated_byte_array_value : bounded_repeated_byte_array_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::bounded_repeated_byte_array),
                                         bounded_repeated_byte_array_value.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            for (const auto &fixed_repeated_byte_array_value : fixed_repeated_byte_array_) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::fixed_repeated_byte_array),
                                         fixed_repeated_byte_array_value.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_plain_bytes) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::crazy_plain_bytes),
                                         crazy_bytes_oneof.crazy_plain_bytes.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_bounded_bytes) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::crazy_bounded_bytes),
                                         crazy_bytes_oneof.crazy_bounded_bytes.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_fixed_bytes) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::crazy_fixed_bytes),
                                         crazy_bytes_oneof.crazy_fixed_bytes.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_repeated_bytes) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::crazy_repeated_bytes),
                                                    *crazy_bytes_oneof.crazy_repeated_bytes)
                        .and_then([&](const ::protocyte::usize nested_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, nested_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_bounded_repeated_bytes) {
                const auto st_size = ::protocyte::message_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::crazy_bounded_repeated_bytes),
                                         *crazy_bytes_oneof.crazy_bounded_repeated_bytes)
                                         .and_then([&](const ::protocyte::usize nested_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, nested_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (crazy_bytes_oneof_case_ == Crazy_bytes_oneofCase::crazy_fixed_repeated_bytes) {
                const auto st_size = ::protocyte::message_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::crazy_fixed_repeated_bytes),
                                         *crazy_bytes_oneof.crazy_fixed_repeated_bytes)
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
    protected:
        Context *ctx_;
        ::protocyte::f64 f_double_ {};
        ::protocyte::f32 f_float_ {};
        ::protocyte::i32 f_int32_ {};
        ::protocyte::i64 f_int64_ {};
        ::protocyte::u32 f_uint32_ {};
        ::protocyte::u64 f_uint64_ {};
        ::protocyte::i32 f_sint32_ {};
        ::protocyte::i64 f_sint64_ {};
        ::protocyte::u32 f_fixed32_ {};
        ::protocyte::u64 f_fixed64_ {};
        ::protocyte::i32 f_sfixed32_ {};
        ::protocyte::i64 f_sfixed64_ {};
        bool f_bool_ {};
        typename Config::String f_string_;
        typename Config::Bytes f_bytes_;
        typename Config::template Vector<::protocyte::i32> r_int32_unpacked_;
        typename Config::template Vector<::protocyte::i32> r_int32_packed_;
        typename Config::template Vector<::protocyte::f64> r_double_;
        ::protocyte::i32 color_ {};
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> nested1_;
        Special_oneofCase special_oneof_case_ {Special_oneofCase::none};
        union Special_oneofStorage {
            Special_oneofStorage() noexcept {}
            ~Special_oneofStorage() noexcept {}
            typename Config::String oneof_string;
            ::protocyte::i32 oneof_int32;
            typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> oneof_msg;
            ::protocyte::ByteArray<4u> oneof_bytes;
        } special_oneof;
        Crazy_bytes_oneofCase crazy_bytes_oneof_case_ {Crazy_bytes_oneofCase::none};
        union Crazy_bytes_oneofStorage {
            Crazy_bytes_oneofStorage() noexcept {}
            ~Crazy_bytes_oneofStorage() noexcept {}
            typename Config::Bytes crazy_plain_bytes;
            ::protocyte::ByteArray<4u> crazy_bounded_bytes;
            ::protocyte::FixedByteArray<4u> crazy_fixed_bytes;
            typename Config::template Optional<::test::ultimate::UltimateComplexMessage_RepeatedBytesHolder<Config>>
                crazy_repeated_bytes;
            typename Config::template Optional<
                ::test::ultimate::UltimateComplexMessage_BoundedRepeatedBytesHolder<Config>>
                crazy_bounded_repeated_bytes;
            typename Config::template Optional<
                ::test::ultimate::UltimateComplexMessage_FixedRepeatedBytesHolder<Config>>
                crazy_fixed_repeated_bytes;
        } crazy_bytes_oneof;
        typename Config::template Map<typename Config::String, ::protocyte::i32> map_str_int32_;
        typename Config::template Map<::protocyte::i32, typename Config::String> map_int32_str_;
        typename Config::template Map<bool, typename Config::Bytes> map_bool_bytes_;
        typename Config::template Map<::protocyte::u64, ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>
            map_uint64_msg_;
        typename Config::template Map<typename Config::String,
                                      ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>
            very_nested_map_;
        typename Config::template Box<::test::ultimate::UltimateComplexMessage<Config>> recursive_self_;
        typename Config::template Vector<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>
            lots_of_nested_;
        typename Config::template Vector<::protocyte::i32> colors_;
        ::protocyte::i32 opt_int32_ {};
        bool has_opt_int32_ {};
        typename Config::String opt_string_;
        bool has_opt_string_ {};
        typename Config::template Optional<
            ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>>
            extreme_nesting_;
        ::protocyte::FixedByteArray<32u> sha256_;
        ::protocyte::Array<::protocyte::i32, 8u> integer_array_;
        ::protocyte::ByteArray<4u> byte_array_;
        ::protocyte::Array<::protocyte::u32, 3u> fixed_integer_array_;
        ::protocyte::ByteArray<2u> float_expr_array_;
        typename Config::template Vector<typename Config::Bytes> repeated_byte_array_;
        ::protocyte::Array<typename Config::Bytes, 3u> bounded_repeated_byte_array_;
        ::protocyte::Array<typename Config::Bytes, 3u> fixed_repeated_byte_array_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using LevelB = UltimateComplexMessage_LevelA_LevelB<NestedConfig>;

        explicit UltimateComplexMessage_LevelA(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA> create(Context &ctx) noexcept {
            return UltimateComplexMessage_LevelA {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_LevelA(UltimateComplexMessage_LevelA &&) noexcept = default;
        UltimateComplexMessage_LevelA &operator=(UltimateComplexMessage_LevelA &&) noexcept = default;
        UltimateComplexMessage_LevelA(const UltimateComplexMessage_LevelA &) = delete;
        UltimateComplexMessage_LevelA &operator=(const UltimateComplexMessage_LevelA &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA &other) noexcept {
            if (this == &other) {
                return {};
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage_LevelA> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer & /* writer */) const noexcept { return {}; }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept { return ::protocyte::usize {}; }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using LevelC =
            UltimateComplexMessage_LevelA_LevelB_LevelC<NestedConfig>;

        explicit UltimateComplexMessage_LevelA_LevelB(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB> create(Context &ctx) noexcept {
            return UltimateComplexMessage_LevelA_LevelB {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_LevelA_LevelB(UltimateComplexMessage_LevelA_LevelB &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB &operator=(UltimateComplexMessage_LevelA_LevelB &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB(const UltimateComplexMessage_LevelA_LevelB &) = delete;
        UltimateComplexMessage_LevelA_LevelB &operator=(const UltimateComplexMessage_LevelA_LevelB &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB &other) noexcept {
            if (this == &other) {
                return {};
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer & /* writer */) const noexcept { return {}; }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept { return ::protocyte::usize {}; }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using LevelD =
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD<NestedConfig>;

        explicit UltimateComplexMessage_LevelA_LevelB_LevelC(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC> create(Context &ctx) noexcept {
            return UltimateComplexMessage_LevelA_LevelB_LevelC {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_LevelA_LevelB_LevelC(UltimateComplexMessage_LevelA_LevelB_LevelC &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB_LevelC &
        operator=(UltimateComplexMessage_LevelA_LevelB_LevelC &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB_LevelC(const UltimateComplexMessage_LevelA_LevelB_LevelC &) = delete;
        UltimateComplexMessage_LevelA_LevelB_LevelC &
        operator=(const UltimateComplexMessage_LevelA_LevelB_LevelC &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB_LevelC &other) noexcept {
            if (this == &other) {
                return {};
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer & /* writer */) const noexcept { return {}; }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept { return ::protocyte::usize {}; }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using LevelE =
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<NestedConfig>;

        explicit UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD> create(Context &ctx) noexcept {
            return UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD(
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &
        operator=(UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD(const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &) =
            delete;
        UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &
        operator=(const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD &other) noexcept {
            if (this == &other) {
                return {};
            }
            return {};
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return {};
        }

        template<typename Writer>::protocyte::Status serialize(Writer & /* writer */) const noexcept { return {}; }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept { return ::protocyte::usize {}; }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct ExtraMessage {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            tag = 1u,
            ref = 2u,
        };

        explicit ExtraMessage(Context &ctx) noexcept: ctx_ {&ctx}, tag_ {&ctx} {}

        static ::protocyte::Result<ExtraMessage> create(Context &ctx) noexcept { return ExtraMessage {ctx}; }
        Context *context() const noexcept { return ctx_; }
        ExtraMessage(ExtraMessage &&) noexcept = default;
        ExtraMessage &operator=(ExtraMessage &&) noexcept = default;
        ExtraMessage(const ExtraMessage &) = delete;
        ExtraMessage &operator=(const ExtraMessage &) = delete;

        ::protocyte::Status copy_from(const ExtraMessage &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_tag(other.tag()); !st) {
                return st;
            }
            if (other.has_ref()) {
                if (const auto st = ensure_ref().and_then(
                        [&](auto ensured) noexcept -> ::protocyte::Status { return ensured->copy_from(*other.ref()); });
                    !st) {
                    return st;
                }
            } else {
                clear_ref();
            }
            return {};
        }

        ::protocyte::Result<ExtraMessage> clone() const noexcept {
            auto out = ExtraMessage::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::Span<const ::protocyte::u8> tag() const noexcept { return tag_.view(); }
        typename Config::String &mutable_tag() noexcept { return tag_; }
        template<class Value>::protocyte::Status set_tag(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return st;
            }
            tag_ = ::protocyte::move(temp);
            return {};
        }
        void clear_tag() noexcept { tag_.clear(); }

        bool has_ref() const noexcept { return ref_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage<Config> *ref() const noexcept {
            return has_ref() ? ref_.operator->() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>>> ensure_ref() noexcept {
            if (ref_.has_value()) {
                return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>> {*ref_};
            }
            return ref_.emplace(*ctx_).transform(
                [this]() noexcept -> ::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>> {
                    return ::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>> {*ref_};
                });
        }
        void clear_ref() noexcept { ref_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<ExtraMessage> parse(Context &ctx, Reader &reader) noexcept {
            auto out = ExtraMessage::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::tag: {
                        if (const auto st =
                                ::protocyte::read_string_field<Config>(*ctx_, reader, wire_type, field_number, tag_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::ref: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::UltimateComplexMessage<Config> ref_value {*ctx_};
                        if (ref_.has_value()) {
                            if (const auto st = ref_value.copy_from(*ref_); !st) {
                                return st;
                            }
                        }
                        if (const auto st = ::protocyte::read_message<Config>(*ctx_, reader, field_number, ref_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = ref_.emplace(::protocyte::move(ref_value)); !st) {
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
            if (!tag_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::tag), tag_.view());
                    !st) {
                    return st;
                }
            }
            if (ref_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::ref), *ref_);
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!tag_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::tag), tag_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (ref_.has_value()) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::ref), *ref_)
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
    protected:
        Context *ctx_;
        typename Config::String tag_;
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage<Config>> ref_;
    };

    template<typename Config> struct CrossMessageConstants_Nested {
        using Context = typename Config::Context;
        static constexpr ::protocyte::u32 EXTERNAL_CAP {8u};

        enum struct FieldNumber : ::protocyte::u32 {
            nested_bytes = 1u,
        };

        explicit CrossMessageConstants_Nested(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<CrossMessageConstants_Nested> create(Context &ctx) noexcept {
            return CrossMessageConstants_Nested {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        CrossMessageConstants_Nested(CrossMessageConstants_Nested &&) noexcept = default;
        CrossMessageConstants_Nested &operator=(CrossMessageConstants_Nested &&) noexcept = default;
        CrossMessageConstants_Nested(const CrossMessageConstants_Nested &) = delete;
        CrossMessageConstants_Nested &operator=(const CrossMessageConstants_Nested &) = delete;

        ::protocyte::Status copy_from(const CrossMessageConstants_Nested &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_nested_bytes(other.nested_bytes()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<CrossMessageConstants_Nested> clone() const noexcept {
            auto out = CrossMessageConstants_Nested::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::Span<const ::protocyte::u8> nested_bytes() const noexcept { return nested_bytes_.view(); }
        ::protocyte::usize nested_bytes_size() const noexcept { return nested_bytes_.size(); }
        static constexpr ::protocyte::usize nested_bytes_max_size() noexcept { return 8u; }
        ::protocyte::Status resize_nested_bytes(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = nested_bytes_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Status resize_nested_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
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
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = nested_bytes_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_nested_bytes() noexcept { nested_bytes_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<CrossMessageConstants_Nested> parse(Context &ctx, Reader &reader) noexcept {
            auto out = CrossMessageConstants_Nested::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::nested_bytes: {
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
                        ::protocyte::ByteArray<8u> nested_bytes_value {};
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
            if (!nested_bytes_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested_bytes), nested_bytes_.view());
                    !st) {
                    return st;
                }
            }
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!nested_bytes_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::nested_bytes), nested_bytes_.size())
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
    protected:
        Context *ctx_;
        ::protocyte::ByteArray<8u> nested_bytes_;
    };

    template<typename Config> struct CrossMessageConstants {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using Nested = CrossMessageConstants_Nested<NestedConfig>;

        static constexpr ::protocyte::u32 ROOT_MIRROR {10u};
        static constexpr ::std::string_view LABEL_COPY {"proto-cross", 11u};
        static constexpr bool READY {true};

        enum struct FieldNumber : ::protocyte::u32 {
            external_bytes = 1u,
            mirrored_values = 2u,
            nested = 3u,
        };

        explicit CrossMessageConstants(Context &ctx) noexcept: ctx_ {&ctx}, mirrored_values_ {&ctx} {}

        static ::protocyte::Result<CrossMessageConstants> create(Context &ctx) noexcept {
            return CrossMessageConstants {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        CrossMessageConstants(CrossMessageConstants &&) noexcept = default;
        CrossMessageConstants &operator=(CrossMessageConstants &&) noexcept = default;
        CrossMessageConstants(const CrossMessageConstants &) = delete;
        CrossMessageConstants &operator=(const CrossMessageConstants &) = delete;

        ::protocyte::Status copy_from(const CrossMessageConstants &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_external_bytes(other.external_bytes()); !st) {
                return st;
            }
            if (const auto st = mutable_mirrored_values().copy_from(other.mirrored_values()); !st) {
                return st;
            }
            if (other.has_nested()) {
                if (const auto st = ensure_nested().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                        return ensured->copy_from(*other.nested());
                    });
                    !st) {
                    return st;
                }
            } else {
                clear_nested();
            }
            return {};
        }

        ::protocyte::Result<CrossMessageConstants> clone() const noexcept {
            auto out = CrossMessageConstants::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::Span<const ::protocyte::u8> external_bytes() const noexcept { return external_bytes_.view(); }
        ::protocyte::usize external_bytes_size() const noexcept { return external_bytes_.size(); }
        static constexpr ::protocyte::usize external_bytes_max_size() noexcept { return 6u; }
        ::protocyte::Status resize_external_bytes(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = external_bytes_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Status resize_external_bytes_for_overwrite(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = external_bytes_.resize_for_overwrite(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::Span<::protocyte::u8> mutable_external_bytes() noexcept { return external_bytes_.mutable_view(); }
        template<class Value>::protocyte::Status set_external_bytes(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size() > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = external_bytes_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_external_bytes() noexcept { external_bytes_.clear(); }

        const ::protocyte::Array<::protocyte::i32, 10u> &mirrored_values() const noexcept { return mirrored_values_; }
        ::protocyte::Array<::protocyte::i32, 10u> &mutable_mirrored_values() noexcept { return mirrored_values_; }
        void clear_mirrored_values() noexcept { mirrored_values_.clear(); }

        bool has_nested() const noexcept { return nested_.has_value(); }
        const ::test::ultimate::CrossMessageConstants_Nested<Config> *nested() const noexcept {
            return has_nested() ? nested_.operator->() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>>>
        ensure_nested() noexcept {
            if (nested_.has_value()) {
                return ::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>> {*nested_};
            }
            return nested_.emplace(*ctx_).transform(
                [this]() noexcept -> ::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>> {
                    return ::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>> {*nested_};
                });
        }
        void clear_nested() noexcept { nested_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<CrossMessageConstants> parse(Context &ctx, Reader &reader) noexcept {
            auto out = CrossMessageConstants::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out->merge_from(reader); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        template<typename Reader>::protocyte::Status merge_from(Reader &reader) noexcept {
            while (!reader.eof()) {
                const auto tag = ::protocyte::read_tag(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto [field_number, wire_type] = *tag;
                switch (static_cast<FieldNumber>(field_number)) {
                    case FieldNumber::external_bytes: {
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
                        if (*len > 6u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = reader.can_read(*len); !st) {
                            return st;
                        }
                        ::protocyte::ByteArray<6u> external_bytes_value {};
                        if (const auto st = external_bytes_value.resize_for_overwrite(*len); !st) {
                            return st;
                        }
                        const auto view = external_bytes_value.mutable_view();
                        if (const auto st = reader.read(view.data(), view.size()); !st) {
                            return st;
                        }
                        external_bytes_ = ::protocyte::move(external_bytes_value);
                        break;
                    }
                    case FieldNumber::mirrored_values: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::Array<::protocyte::i32, 10u> packed_mirrored_values_values {};
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                if (const auto st = ::protocyte::read_int32(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = packed_mirrored_values_values.push_back(value); !st) {
                                    return st;
                                }
                            }
                            const auto packed_mirrored_values_values_commit_size =
                                ::protocyte::checked_add(mirrored_values_.size(), packed_mirrored_values_values.size());
                            if (!packed_mirrored_values_values_commit_size) {
                                return packed_mirrored_values_values_commit_size.status();
                            }
                            if (*packed_mirrored_values_values_commit_size > 10u) {
                                return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                               field_number);
                            }
                            for (const auto &value : packed_mirrored_values_values) {
                                if (const auto st = mirrored_values_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = mirrored_values_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        ::test::ultimate::CrossMessageConstants_Nested<Config> nested_value {*ctx_};
                        if (nested_.has_value()) {
                            if (const auto st = nested_value.copy_from(*nested_); !st) {
                                return st;
                            }
                        }
                        if (const auto st =
                                ::protocyte::read_message<Config>(*ctx_, reader, field_number, nested_value);
                            !st) {
                            return st;
                        }
                        if (const auto st = nested_.emplace(::protocyte::move(nested_value)); !st) {
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
            if (!external_bytes_.empty()) {
                if (const auto st = ::protocyte::write_bytes_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::external_bytes), external_bytes_.view());
                    !st) {
                    return st;
                }
            }
            if (!mirrored_values_.empty()) {
                ::protocyte::usize packed_size_mirrored_values {};
                for (const auto &packed_value_mirrored_values : mirrored_values_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_mirrored_values,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(packed_value_mirrored_values)));
                    if (!st_size) {
                        return st_size.status();
                    }
                    packed_size_mirrored_values = *st_size;
                }
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::mirrored_values),
                                               ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(packed_size_mirrored_values));
                    !st) {
                    return st;
                }
                for (const auto &packed_value_mirrored_values : mirrored_values_) {
                    if (const auto st = ::protocyte::write_int32(writer, packed_value_mirrored_values); !st) {
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
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!external_bytes_.empty()) {
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::external_bytes),
                                                             external_bytes_.size())
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (!mirrored_values_.empty()) {
                ::protocyte::usize packed_size_mirrored_values {};
                for (const auto &mirrored_values_value : mirrored_values_) {
                    const auto st_size = ::protocyte::add_size(
                        packed_size_mirrored_values,
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(mirrored_values_value)));
                    if (!st_size) {
                        return ::protocyte::unexpected(st_size.error());
                    }
                    packed_size_mirrored_values = *st_size;
                }
                const auto st_size =
                    ::protocyte::length_delimited_field_size(
                        static_cast<::protocyte::u32>(FieldNumber::mirrored_values), packed_size_mirrored_values)
                        .and_then([&](const ::protocyte::usize field_size) noexcept
                                      -> ::protocyte::Result<::protocyte::usize> {
                            return ::protocyte::add_size(total, field_size);
                        });
                if (!st_size) {
                    return ::protocyte::unexpected(st_size.error());
                }
                total = *st_size;
            }
            if (nested_.has_value()) {
                const auto st_size =
                    ::protocyte::message_field_size(static_cast<::protocyte::u32>(FieldNumber::nested), *nested_)
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
    protected:
        Context *ctx_;
        ::protocyte::ByteArray<6u> external_bytes_;
        ::protocyte::Array<::protocyte::i32, 10u> mirrored_values_;
        typename Config::template Optional<::test::ultimate::CrossMessageConstants_Nested<Config>> nested_;
    };

} // namespace test::ultimate

#endif // PROTOCYTE_GENERATED_EXAMPLE_PROTO_69F808DB6B7B_HPP
