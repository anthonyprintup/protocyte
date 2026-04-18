#pragma once

#ifndef PROTOCYTE_GENERATED_EXAMPLE_PROTO_HPP
#define PROTOCYTE_GENERATED_EXAMPLE_PROTO_HPP

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

    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_NestedLevel1_NestedLevel2;
    template<typename Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_NestedLevel1;
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
        using RuntimeStatus = ::protocyte::Status;
        using InnerEnum = UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;

        enum struct FieldNumber : ::protocyte::u32 {
            description = 1u,
            values = 2u,
            mode = 3u,
        };

        explicit UltimateComplexMessage_NestedLevel1_NestedLevel2(Context &ctx) noexcept:
            ctx_ {&ctx}, description_ {&ctx}, values_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2>::ok(
                UltimateComplexMessage_NestedLevel1_NestedLevel2 {ctx});
        }
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
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_description(other.description()); !st) {
                return st;
            }
            clear_values();
            for (::protocyte::usize i {}; i < other.values().size(); ++i) {
                if (const auto st = mutable_values().push_back(other.values()[i]); !st) {
                    return st;
                }
            }
            if (const auto st = set_mode_raw(other.mode_raw()); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2> clone() const noexcept {
            auto out = UltimateComplexMessage_NestedLevel1_NestedLevel2::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2>::err(st.error());
            }
            return out;
        }

        ::protocyte::ByteView description() const noexcept { return description_.view(); }
        typename Config::String &mutable_description() noexcept { return description_; }
        ::protocyte::Status set_description(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            description_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
        }
        void clear_description() noexcept { description_.clear(); }

        const typename Config::template Vector<::protocyte::f32> &values() const noexcept { return values_; }
        typename Config::template Vector<::protocyte::f32> &mutable_values() noexcept { return values_; }
        void clear_values() noexcept { values_.clear(); }

        constexpr ::protocyte::i32 mode_raw() const noexcept { return mode_; }
        constexpr ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum mode() const noexcept {
            return static_cast<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum>(mode_);
        }
        constexpr ::protocyte::Status set_mode_raw(const ::protocyte::i32 value) noexcept {
            mode_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr ::protocyte::Status
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
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2>::err(st.error());
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
                    case FieldNumber::description: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), description_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::values: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::f32 value {};
                                auto raw = ::protocyte::read_fixed32(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = ::std::bit_cast<::protocyte::f32>(raw.value());
                                if (const auto st = values_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::I32) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::f32 value {};
                        auto raw = ::protocyte::read_fixed32(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = ::std::bit_cast<::protocyte::f32>(raw.value());
                        if (const auto st = values_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::mode: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        mode_ = static_cast<::protocyte::i32>(raw.value());
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
            if (!description_.empty()) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::description), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, description_.view()); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < values_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::values),
                                                           ::protocyte::WireType::I32);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed32(writer, ::std::bit_cast<::protocyte::u32>(values_[i]));
                    !st) {
                    return st;
                }
            }
            if (mode_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::mode),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(mode_)); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!description_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::description)) +
                                    ::protocyte::varint_size(description_.size()) + description_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < values_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::values)) + 4u);
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
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        typename Config::String description_;
        typename Config::template Vector<::protocyte::f32> values_;
        ::protocyte::i32 mode_ {};
    };

    template<typename Config> struct UltimateComplexMessage_NestedLevel1 {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        template<typename NestedConfig = Config> using NestedLevel2 =
            UltimateComplexMessage_NestedLevel1_NestedLevel2<NestedConfig>;

        enum struct FieldNumber : ::protocyte::u32 {
            name = 1u,
            id = 2u,
            inner = 3u,
        };

        explicit UltimateComplexMessage_NestedLevel1(Context &ctx) noexcept: ctx_ {&ctx}, name_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_NestedLevel1> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_NestedLevel1>::ok(
                UltimateComplexMessage_NestedLevel1 {ctx});
        }
        UltimateComplexMessage_NestedLevel1(UltimateComplexMessage_NestedLevel1 &&) noexcept = default;
        UltimateComplexMessage_NestedLevel1 &operator=(UltimateComplexMessage_NestedLevel1 &&) noexcept = default;
        UltimateComplexMessage_NestedLevel1(const UltimateComplexMessage_NestedLevel1 &) = delete;
        UltimateComplexMessage_NestedLevel1 &operator=(const UltimateComplexMessage_NestedLevel1 &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_NestedLevel1 &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_name(other.name()); !st) {
                return st;
            }
            if (const auto st = set_id(other.id()); !st) {
                return st;
            }
            if (other.has_inner()) {
                if (auto ensured = ensure_inner(); !ensured) {
                    return ensured.status();
                } else if (const auto st = ensured.value().get().copy_from(*other.inner()); !st) {
                    return st;
                }
            } else {
                clear_inner();
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_NestedLevel1> clone() const noexcept {
            auto out = UltimateComplexMessage_NestedLevel1::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_NestedLevel1>::err(st.error());
            }
            return out;
        }

        ::protocyte::ByteView name() const noexcept { return name_.view(); }
        typename Config::String &mutable_name() noexcept { return name_; }
        ::protocyte::Status set_name(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            name_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
        }
        void clear_name() noexcept { name_.clear(); }

        constexpr ::protocyte::i32 id() const noexcept { return id_; }
        constexpr ::protocyte::Status set_id(const ::protocyte::i32 value) noexcept {
            id_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_id() noexcept { id_ = {}; }

        bool has_inner() const noexcept { return inner_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> *inner() const noexcept {
            return has_inner() ? &inner_.value() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>>
        ensure_inner() noexcept {
            if (!inner_.has_value()) {
                if (const auto st = inner_.emplace(*ctx_); !st) {
                    return ::protocyte::Result<::protocyte::Ref<
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>>::err(st.error());
                }
            }
            return ::protocyte::Result<
                ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>>::
                ok(::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>> {
                    inner_.value()});
        }
        void clear_inner() noexcept { inner_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage_NestedLevel1> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_NestedLevel1::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_NestedLevel1>::err(st.error());
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
                    case FieldNumber::name: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), name_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::id: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        id_ = static_cast<::protocyte::i32>(raw.value());
                        break;
                    }
                    case FieldNumber::inner: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_inner();
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
            if (!name_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::name),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, name_.view()); !st) {
                    return st;
                }
            }
            if (id_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::id),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(id_)); !st) {
                    return st;
                }
            }
            if (inner_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::inner),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = inner_.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = inner_.value().serialize(writer); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!name_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::name)) +
                                    ::protocyte::varint_size(name_.size()) + name_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (id_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::id)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(id_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (inner_.has_value()) {
                auto nested_size = inner_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::inner)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        typename Config::String name_;
        ::protocyte::i32 id_ {};
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>
            inner_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;

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
            return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>::ok(
                UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE {ctx});
        }
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
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_extreme(other.extreme()); !st) {
                return st;
            }
            clear_weird_map();
            if (const auto st = other.weird_map().for_each([&](const auto &key, const auto &value) noexcept {
                    auto copied_key = key;
                    typename Config::String copied_value {ctx_};
                    if (const auto st = copied_value.assign(value.view()); !st) {
                        return st;
                    }
                    if (const auto insert = mutable_weird_map().insert_or_assign(::protocyte::move(copied_key),
                                                                                 ::protocyte::move(copied_value));
                        !insert) {
                        return insert;
                    }
                    return ::protocyte::Status::ok();
                });
                !st) {
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
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>::err(st.error());
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

        ::protocyte::ByteView extreme() const noexcept { return extreme_.view(); }
        typename Config::String &mutable_extreme() noexcept { return extreme_; }
        ::protocyte::Status set_extreme(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            extreme_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
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
            return ::protocyte::Status::ok();
        }

        constexpr bool has_text() const noexcept { return deep_oneof_case_ == Deep_oneofCase::text; }
        ::protocyte::ByteView text() const noexcept {
            return has_text() ? deep_oneof.text.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_text(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_deep_oneof();
            new (&deep_oneof.text) typename Config::String {::protocyte::move(temp)};
            deep_oneof_case_ = Deep_oneofCase::text;
            return ::protocyte::Status::ok();
        }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>::err(st.error());
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
                    case FieldNumber::extreme: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), extreme_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::weird_map: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto entry_len = ::protocyte::read_varint(reader);
                        if (!entry_len) {
                            return entry_len.status();
                        }
                        ::protocyte::LimitedReader<Reader> entry_reader {
                            reader, static_cast<::protocyte::usize>(entry_len.value())};
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::i32 key {};
                        typename Config::String value {ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = static_cast<::protocyte::i32>(raw.value());
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::usize>(len.value()), value);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        if (const auto finish = entry_reader.finish(); !finish) {
                            return finish;
                        }
                        if (const auto insert =
                                weird_map_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                            !insert) {
                            return insert;
                        }
                        break;
                    }
                    case FieldNumber::val: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        clear_deep_oneof();
                        new (&deep_oneof.val)::protocyte::i64 {0};
                        deep_oneof_case_ = Deep_oneofCase::val;
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        deep_oneof.val = static_cast<::protocyte::i64>(raw.value());
                        break;
                    }
                    case FieldNumber::text: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        clear_deep_oneof();
                        new (&deep_oneof.text) typename Config::String {ctx_};
                        deep_oneof_case_ = Deep_oneofCase::text;
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), deep_oneof.text);
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
            if (!extreme_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::extreme),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, extreme_.view()); !st) {
                    return st;
                }
            }
            if (const auto st_map_weird_map = weird_map_.for_each([&](const auto &key, const auto &value) noexcept {
                    enum struct EntryFieldNumber : ::protocyte::u32 {
                        key = 1u,
                        value = 2u,
                    };
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                    ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
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
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::key),
                                                       ::protocyte::WireType::VARINT);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key));
                            !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, value.view()); !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
                !st_map_weird_map) {
                return st_map_weird_map;
            }
            if (deep_oneof_case_ == Deep_oneofCase::val) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::val),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(deep_oneof.val));
                    !st) {
                    return st;
                }
            }
            if (deep_oneof_case_ == Deep_oneofCase::text) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::text),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, deep_oneof.text.view()); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!extreme_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::extreme)) +
                                    ::protocyte::varint_size(extreme_.size()) + extreme_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (const auto st_map_size_weird_map =
                    weird_map_.for_each([&](const auto &key, const auto &value) noexcept {
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::usize entry_payload {};
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                        ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                                !st_size) {
                                return st_size;
                            }
                        }
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                        ::protocyte::varint_size(value.size()) + value.size());
                                !st_size) {
                                return st_size;
                            }
                        }
                        return ::protocyte::add_size(
                            &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::weird_map)) +
                                        ::protocyte::varint_size(entry_payload) + entry_payload);
                    });
                !st_map_size_weird_map) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_weird_map.error());
            }
            if (deep_oneof_case_ == Deep_oneofCase::val) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::val)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(deep_oneof.val)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (deep_oneof_case_ == Deep_oneofCase::text) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::text)) +
                                    ::protocyte::varint_size(deep_oneof.text.size()) + deep_oneof.text.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
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
        using RuntimeStatus = ::protocyte::Status;
        using Color = UltimateComplexMessage_Color;
        template<typename NestedConfig = Config> using NestedLevel1 = UltimateComplexMessage_NestedLevel1<NestedConfig>;
        template<typename NestedConfig = Config> using LevelA = UltimateComplexMessage_LevelA<NestedConfig>;

        static constexpr ::protocyte::i32 BASE_COUNT {5};
        static constexpr ::protocyte::i64 SHIFTED_COUNT {5000000000};
        static constexpr ::protocyte::u64 MASK_BITS {1234567890123456789ull};
        static constexpr ::protocyte::f32 FLOAT_SCALE {1.25f};
        static constexpr ::protocyte::f64 DOUBLE_SCALE {3.75};
        static constexpr bool FLAG_LITERAL {true};
        static constexpr ::protocyte::u32 HEX_LITERAL {32u};
        static constexpr ::protocyte::u32 HEX_SUM {24u};
        static constexpr ::protocyte::u32 INTEGER_ARRAY_CAP {8u};
        static constexpr ::std::string_view PREFIX {"proto", 5u};
        static constexpr ::std::string_view LABEL {"proto-demo", 10u};
        static constexpr ::std::string_view UNICODE_LABEL {"\xc4"
                                                           "\x80"
                                                           "\xc3"
                                                           "\xa9",
                                                           4u};
        static constexpr ::protocyte::u32 BYTE_ARRAY_CAP {4u};
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
            opt_string_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage>::ok(UltimateComplexMessage {ctx});
        }
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
            float_expr_array_ {::protocyte::move(other.float_expr_array_)} {
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
                    new (&special_oneof.oneof_bytes)::protocyte::ByteArray<BYTE_ARRAY_CAP> {
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
        }
        UltimateComplexMessage &operator=(UltimateComplexMessage &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_special_oneof();
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
                    new (&special_oneof.oneof_bytes)::protocyte::ByteArray<BYTE_ARRAY_CAP> {
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
            return *this;
        }
        ~UltimateComplexMessage() noexcept { clear_special_oneof(); }
        UltimateComplexMessage(const UltimateComplexMessage &) = delete;
        UltimateComplexMessage &operator=(const UltimateComplexMessage &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const UltimateComplexMessage &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
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
            if (const auto st = set_color_raw(other.color_raw()); !st) {
                return st;
            }
            if (other.has_nested1()) {
                if (auto ensured = ensure_nested1(); !ensured) {
                    return ensured.status();
                } else if (const auto st = ensured.value().get().copy_from(*other.nested1()); !st) {
                    return st;
                }
            } else {
                clear_nested1();
            }
            clear_map_str_int32();
            if (const auto st = other.map_str_int32().for_each([&](const auto &key, const auto &value) noexcept {
                    typename Config::String copied_key {ctx_};
                    if (const auto st = copied_key.assign(key.view()); !st) {
                        return st;
                    }
                    auto copied_value = value;
                    if (const auto insert = mutable_map_str_int32().insert_or_assign(::protocyte::move(copied_key),
                                                                                     ::protocyte::move(copied_value));
                        !insert) {
                        return insert;
                    }
                    return ::protocyte::Status::ok();
                });
                !st) {
                return st;
            }
            clear_map_int32_str();
            if (const auto st = other.map_int32_str().for_each([&](const auto &key, const auto &value) noexcept {
                    auto copied_key = key;
                    typename Config::String copied_value {ctx_};
                    if (const auto st = copied_value.assign(value.view()); !st) {
                        return st;
                    }
                    if (const auto insert = mutable_map_int32_str().insert_or_assign(::protocyte::move(copied_key),
                                                                                     ::protocyte::move(copied_value));
                        !insert) {
                        return insert;
                    }
                    return ::protocyte::Status::ok();
                });
                !st) {
                return st;
            }
            clear_map_bool_bytes();
            if (const auto st = other.map_bool_bytes().for_each([&](const auto &key, const auto &value) noexcept {
                    auto copied_key = key;
                    typename Config::Bytes copied_value {ctx_};
                    if (const auto st = copied_value.assign(value.view()); !st) {
                        return st;
                    }
                    if (const auto insert = mutable_map_bool_bytes().insert_or_assign(::protocyte::move(copied_key),
                                                                                      ::protocyte::move(copied_value));
                        !insert) {
                        return insert;
                    }
                    return ::protocyte::Status::ok();
                });
                !st) {
                return st;
            }
            clear_map_uint64_msg();
            if (const auto st = other.map_uint64_msg().for_each([&](const auto &key, const auto &value) noexcept {
                    auto copied_key = key;
                    ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> copied_value {*ctx_};
                    if (const auto st = copied_value.copy_from(value); !st) {
                        return st;
                    }
                    if (const auto insert = mutable_map_uint64_msg().insert_or_assign(::protocyte::move(copied_key),
                                                                                      ::protocyte::move(copied_value));
                        !insert) {
                        return insert;
                    }
                    return ::protocyte::Status::ok();
                });
                !st) {
                return st;
            }
            clear_very_nested_map();
            if (const auto st = other.very_nested_map().for_each([&](const auto &key, const auto &value) noexcept {
                    typename Config::String copied_key {ctx_};
                    if (const auto st = copied_key.assign(key.view()); !st) {
                        return st;
                    }
                    ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> copied_value {*ctx_};
                    if (const auto st = copied_value.copy_from(value); !st) {
                        return st;
                    }
                    if (const auto insert = mutable_very_nested_map().insert_or_assign(::protocyte::move(copied_key),
                                                                                       ::protocyte::move(copied_value));
                        !insert) {
                        return insert;
                    }
                    return ::protocyte::Status::ok();
                });
                !st) {
                return st;
            }
            if (other.has_recursive_self()) {
                if (auto ensured = ensure_recursive_self(); !ensured) {
                    return ensured.status();
                } else if (const auto st = ensured.value().get().copy_from(*other.recursive_self()); !st) {
                    return st;
                }
            } else {
                clear_recursive_self();
            }
            clear_lots_of_nested();
            for (::protocyte::usize i {}; i < other.lots_of_nested().size(); ++i) {
                auto copied = mutable_lots_of_nested().emplace_back(*ctx_);
                if (!copied) {
                    return copied.status();
                }
                if (const auto st = copied.value().get().copy_from(other.lots_of_nested()[i]); !st) {
                    return st;
                }
            }
            clear_colors();
            for (::protocyte::usize i {}; i < other.colors().size(); ++i) {
                if (const auto st = mutable_colors().push_back(other.colors()[i]); !st) {
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
            if (other.has_extreme_nesting()) {
                if (auto ensured = ensure_extreme_nesting(); !ensured) {
                    return ensured.status();
                } else if (const auto st = ensured.value().get().copy_from(*other.extreme_nesting()); !st) {
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
            clear_integer_array();
            for (::protocyte::usize i {}; i < other.integer_array().size(); ++i) {
                if (const auto st = mutable_integer_array().push_back(other.integer_array()[i]); !st) {
                    return st;
                }
            }
            if (const auto st = set_byte_array(other.byte_array()); !st) {
                return st;
            }
            clear_fixed_integer_array();
            for (::protocyte::usize i {}; i < other.fixed_integer_array().size(); ++i) {
                if (const auto st = mutable_fixed_integer_array().push_back(other.fixed_integer_array()[i]); !st) {
                    return st;
                }
            }
            if (const auto st = set_float_expr_array(other.float_expr_array()); !st) {
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
                    if (auto ensured = ensure_oneof_msg(); !ensured) {
                        return ensured.status();
                    } else if (const auto st = ensured.value().get().copy_from(*other.oneof_msg()); !st) {
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

        ::protocyte::Result<UltimateComplexMessage> clone() const noexcept {
            auto out = UltimateComplexMessage::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage>::err(st.error());
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

        constexpr ::protocyte::f64 f_double() const noexcept { return f_double_; }
        constexpr ::protocyte::Status set_f_double(const ::protocyte::f64 value) noexcept {
            f_double_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_double() noexcept { f_double_ = {}; }

        constexpr ::protocyte::f32 f_float() const noexcept { return f_float_; }
        constexpr ::protocyte::Status set_f_float(const ::protocyte::f32 value) noexcept {
            f_float_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_float() noexcept { f_float_ = {}; }

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

        constexpr bool f_bool() const noexcept { return f_bool_; }
        constexpr ::protocyte::Status set_f_bool(const bool value) noexcept {
            f_bool_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr void clear_f_bool() noexcept { f_bool_ = {}; }

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
        constexpr ::protocyte::Status set_color_raw(const ::protocyte::i32 value) noexcept {
            color_ = value;
            return ::protocyte::Status::ok();
        }
        constexpr ::protocyte::Status set_color(const ::test::ultimate::UltimateComplexMessage_Color value) noexcept {
            return set_color_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_color() noexcept { color_ = {}; }

        bool has_nested1() const noexcept { return nested1_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> *nested1() const noexcept {
            return has_nested1() ? &nested1_.value() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>
        ensure_nested1() noexcept {
            if (!nested1_.has_value()) {
                if (const auto st = nested1_.emplace(*ctx_); !st) {
                    return ::protocyte::
                        Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>::err(
                            st.error());
                }
            }
            return ::protocyte::
                Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>::ok(
                    ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {nested1_.value()});
        }
        void clear_nested1() noexcept { nested1_.reset(); }

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

        constexpr bool has_oneof_msg() const noexcept { return special_oneof_case_ == Special_oneofCase::oneof_msg; }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> *oneof_msg() const noexcept {
            return has_oneof_msg() && special_oneof.oneof_msg.has_value() ? &special_oneof.oneof_msg.value() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>
        ensure_oneof_msg() noexcept {
            if (!has_oneof_msg()) {
                clear_special_oneof();
                new (&special_oneof.oneof_msg) typename Config::template Optional<
                    ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {};
            }
            special_oneof_case_ = Special_oneofCase::oneof_msg;
            if (!special_oneof.oneof_msg.has_value()) {
                if (const auto st = special_oneof.oneof_msg.emplace(*ctx_); !st) {
                    return ::protocyte::
                        Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>::err(
                            st.error());
                }
            }
            return ::protocyte::
                Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>::ok(
                    ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> {
                        special_oneof.oneof_msg.value()});
        }

        constexpr bool has_oneof_bytes() const noexcept {
            return special_oneof_case_ == Special_oneofCase::oneof_bytes;
        }
        ::protocyte::ByteView oneof_bytes() const noexcept {
            return has_oneof_bytes() ? special_oneof.oneof_bytes.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_oneof_bytes(const ::protocyte::ByteView value) noexcept {
            ::protocyte::ByteArray<BYTE_ARRAY_CAP> temp {};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_bytes)::protocyte::ByteArray<BYTE_ARRAY_CAP> {::protocyte::move(temp)};
            special_oneof_case_ = Special_oneofCase::oneof_bytes;
            return ::protocyte::Status::ok();
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
            return has_recursive_self() ? &recursive_self_.value() : nullptr;
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

        bool has_extreme_nesting() const noexcept { return extreme_nesting_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config> *
        extreme_nesting() const noexcept {
            return has_extreme_nesting() ? &extreme_nesting_.value() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>>>
        ensure_extreme_nesting() noexcept {
            if (!extreme_nesting_.has_value()) {
                if (const auto st = extreme_nesting_.emplace(*ctx_); !st) {
                    return ::protocyte::Result<::protocyte::Ref<
                        ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>>>::
                        err(st.error());
                }
            }
            return ::protocyte::Result<
                ::protocyte::Ref<::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>>>::
                ok(::protocyte::Ref<
                    ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>> {
                    extreme_nesting_.value()});
        }
        void clear_extreme_nesting() noexcept { extreme_nesting_.reset(); }

        bool has_sha256() const noexcept { return sha256_.has_value(); }
        ::protocyte::ByteView sha256() const noexcept { return sha256_.view(); }
        ::protocyte::MutableByteView mutable_sha256() noexcept { return sha256_.mutable_view(); }
        ::protocyte::Status set_sha256(const ::protocyte::ByteView value) noexcept { return sha256_.assign(value); }
        void clear_sha256() noexcept { sha256_.clear(); }

        const ::protocyte::Array<::protocyte::i32, INTEGER_ARRAY_CAP> &integer_array() const noexcept {
            return integer_array_;
        }
        ::protocyte::Array<::protocyte::i32, INTEGER_ARRAY_CAP> &mutable_integer_array() noexcept {
            return integer_array_;
        }
        void clear_integer_array() noexcept { integer_array_.clear(); }

        ::protocyte::ByteView byte_array() const noexcept { return byte_array_.view(); }
        ::protocyte::usize byte_array_size() const noexcept { return byte_array_.size(); }
        static constexpr ::protocyte::usize byte_array_max_size() noexcept { return BYTE_ARRAY_CAP; }
        ::protocyte::Status resize_byte_array(const ::protocyte::usize size) noexcept {
            if (const auto st = byte_array_.resize(size); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        ::protocyte::MutableByteView mutable_byte_array() noexcept { return byte_array_.mutable_view(); }
        ::protocyte::Status set_byte_array(const ::protocyte::ByteView value) noexcept {
            if (const auto st = byte_array_.assign(value); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        void clear_byte_array() noexcept { byte_array_.clear(); }

        const ::protocyte::Array<::protocyte::u32, FIXED_INTEGER_ARRAY_CAP> &fixed_integer_array() const noexcept {
            return fixed_integer_array_;
        }
        ::protocyte::Array<::protocyte::u32, FIXED_INTEGER_ARRAY_CAP> &mutable_fixed_integer_array() noexcept {
            return fixed_integer_array_;
        }
        void clear_fixed_integer_array() noexcept { fixed_integer_array_.clear(); }

        ::protocyte::ByteView float_expr_array() const noexcept { return float_expr_array_.view(); }
        ::protocyte::usize float_expr_array_size() const noexcept { return float_expr_array_.size(); }
        static constexpr ::protocyte::usize float_expr_array_max_size() noexcept { return FLOATISH_BOUND; }
        ::protocyte::Status resize_float_expr_array(const ::protocyte::usize size) noexcept {
            if (const auto st = float_expr_array_.resize(size); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        ::protocyte::MutableByteView mutable_float_expr_array() noexcept { return float_expr_array_.mutable_view(); }
        ::protocyte::Status set_float_expr_array(const ::protocyte::ByteView value) noexcept {
            if (const auto st = float_expr_array_.assign(value); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        void clear_float_expr_array() noexcept { float_expr_array_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage>::err(st.error());
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
                    case FieldNumber::f_double: {
                        if (wire_type != ::protocyte::WireType::I64) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed64(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_double_ = ::std::bit_cast<::protocyte::f64>(raw.value());
                        break;
                    }
                    case FieldNumber::f_float: {
                        if (wire_type != ::protocyte::WireType::I32) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed32(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_float_ = ::std::bit_cast<::protocyte::f32>(raw.value());
                        break;
                    }
                    case FieldNumber::f_int32: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_int32_ = static_cast<::protocyte::i32>(raw.value());
                        break;
                    }
                    case FieldNumber::f_int64: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_int64_ = static_cast<::protocyte::i64>(raw.value());
                        break;
                    }
                    case FieldNumber::f_uint32: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_uint32_ = static_cast<::protocyte::u32>(raw.value());
                        break;
                    }
                    case FieldNumber::f_uint64: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_uint64_ = static_cast<::protocyte::u64>(raw.value());
                        break;
                    }
                    case FieldNumber::f_sint32: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_sint32_ = ::protocyte::decode_zigzag32(static_cast<::protocyte::u32>(raw.value()));
                        break;
                    }
                    case FieldNumber::f_sint64: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_sint64_ = ::protocyte::decode_zigzag64(raw.value());
                        break;
                    }
                    case FieldNumber::f_fixed32: {
                        if (wire_type != ::protocyte::WireType::I32) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed32(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_fixed32_ = static_cast<::protocyte::u32>(raw.value());
                        break;
                    }
                    case FieldNumber::f_fixed64: {
                        if (wire_type != ::protocyte::WireType::I64) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed64(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_fixed64_ = static_cast<::protocyte::u64>(raw.value());
                        break;
                    }
                    case FieldNumber::f_sfixed32: {
                        if (wire_type != ::protocyte::WireType::I32) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed32(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_sfixed32_ = static_cast<::protocyte::i32>(raw.value());
                        break;
                    }
                    case FieldNumber::f_sfixed64: {
                        if (wire_type != ::protocyte::WireType::I64) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed64(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_sfixed64_ = static_cast<::protocyte::i64>(raw.value());
                        break;
                    }
                    case FieldNumber::f_bool: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        f_bool_ = raw.value() != 0u;
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
                                auto raw = ::protocyte::read_varint(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = static_cast<::protocyte::i32>(raw.value());
                                if (const auto st = r_int32_unpacked_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::i32 value {};
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = static_cast<::protocyte::i32>(raw.value());
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
                                auto raw = ::protocyte::read_varint(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = static_cast<::protocyte::i32>(raw.value());
                                if (const auto st = r_int32_packed_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::i32 value {};
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = static_cast<::protocyte::i32>(raw.value());
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
                                auto raw = ::protocyte::read_fixed64(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = ::std::bit_cast<::protocyte::f64>(raw.value());
                                if (const auto st = r_double_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::I64) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::f64 value {};
                        auto raw = ::protocyte::read_fixed64(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = ::std::bit_cast<::protocyte::f64>(raw.value());
                        if (const auto st = r_double_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::color: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        color_ = static_cast<::protocyte::i32>(raw.value());
                        break;
                    }
                    case FieldNumber::nested1: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_nested1();
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
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_int32)::protocyte::i32 {0};
                        special_oneof_case_ = Special_oneofCase::oneof_int32;
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        special_oneof.oneof_int32 = static_cast<::protocyte::i32>(raw.value());
                        break;
                    }
                    case FieldNumber::oneof_msg: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_oneof_msg();
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
                        clear_special_oneof();
                        new (&special_oneof.oneof_bytes)::protocyte::ByteArray<BYTE_ARRAY_CAP> {};
                        special_oneof_case_ = Special_oneofCase::oneof_bytes;
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() > BYTE_ARRAY_CAP) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::count_limit, reader.position(),
                                                              field_number);
                        }
                        if (const auto st =
                                special_oneof.oneof_bytes.resize(static_cast<::protocyte::usize>(len.value()));
                            !st) {
                            return st;
                        }
                        if (const auto st =
                                reader.read(special_oneof.oneof_bytes.data(), special_oneof.oneof_bytes.size());
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::map_str_int32: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto entry_len = ::protocyte::read_varint(reader);
                        if (!entry_len) {
                            return entry_len.status();
                        }
                        ::protocyte::LimitedReader<Reader> entry_reader {
                            reader, static_cast<::protocyte::usize>(entry_len.value())};
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        typename Config::String key {ctx_};
                        ::protocyte::i32 value {};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::usize>(len.value()), key);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    value = static_cast<::protocyte::i32>(raw.value());
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        if (const auto finish = entry_reader.finish(); !finish) {
                            return finish;
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
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto entry_len = ::protocyte::read_varint(reader);
                        if (!entry_len) {
                            return entry_len.status();
                        }
                        ::protocyte::LimitedReader<Reader> entry_reader {
                            reader, static_cast<::protocyte::usize>(entry_len.value())};
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::i32 key {};
                        typename Config::String value {ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = static_cast<::protocyte::i32>(raw.value());
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::usize>(len.value()), value);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        if (const auto finish = entry_reader.finish(); !finish) {
                            return finish;
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
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto entry_len = ::protocyte::read_varint(reader);
                        if (!entry_len) {
                            return entry_len.status();
                        }
                        ::protocyte::LimitedReader<Reader> entry_reader {
                            reader, static_cast<::protocyte::usize>(entry_len.value())};
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        bool key {};
                        typename Config::Bytes value {ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = raw.value() != 0u;
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    if (const auto st = ::protocyte::read_bytes<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::usize>(len.value()), value);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        if (const auto finish = entry_reader.finish(); !finish) {
                            return finish;
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
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto entry_len = ::protocyte::read_varint(reader);
                        if (!entry_len) {
                            return entry_len.status();
                        }
                        ::protocyte::LimitedReader<Reader> entry_reader {
                            reader, static_cast<::protocyte::usize>(entry_len.value())};
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::u64 key {};
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> value {*ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = static_cast<::protocyte::u64>(raw.value());
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    ::protocyte::LimitedReader nested {entry_reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                                    ::protocyte::ReaderRef nested_reader {nested};
                                    if (const auto st = value.merge_from(nested_reader); !st) {
                                        return st;
                                    }
                                    if (const auto st = nested.finish(); !st) {
                                        return st;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        if (const auto finish = entry_reader.finish(); !finish) {
                            return finish;
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
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto entry_len = ::protocyte::read_varint(reader);
                        if (!entry_len) {
                            return entry_len.status();
                        }
                        ::protocyte::LimitedReader<Reader> entry_reader {
                            reader, static_cast<::protocyte::usize>(entry_len.value())};
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        typename Config::String key {ctx_};
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> value {*ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (static_cast<EntryFieldNumber>(entry_field)) {
                                case EntryFieldNumber::key: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::key));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    if (const auto st = ::protocyte::read_string<Config>(
                                            *ctx_, entry_reader, static_cast<::protocyte::usize>(len.value()), key);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                                case EntryFieldNumber::value: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(
                                            ::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(),
                                            static_cast<::protocyte::u32>(EntryFieldNumber::value));
                                    }
                                    auto len = ::protocyte::read_varint(entry_reader);
                                    if (!len) {
                                        return len.status();
                                    }
                                    ::protocyte::LimitedReader nested {entry_reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                                    ::protocyte::ReaderRef nested_reader {nested};
                                    if (const auto st = value.merge_from(nested_reader); !st) {
                                        return st;
                                    }
                                    if (const auto st = nested.finish(); !st) {
                                        return st;
                                    }
                                    break;
                                }
                                default: {
                                    if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);
                                        !st) {
                                        return st;
                                    }
                                    break;
                                }
                            }
                        }
                        if (const auto finish = entry_reader.finish(); !finish) {
                            return finish;
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
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_recursive_self();
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
                    case FieldNumber::lots_of_nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> value {*ctx_};
                        ::protocyte::LimitedReader<Reader> sub {reader, static_cast<::protocyte::usize>(len.value())};
                        ::protocyte::ReaderRef sub_reader {sub};
                        if (const auto st = value.merge_from(sub_reader); !st) {
                            return st;
                        }
                        if (const auto st = sub.finish(); !st) {
                            return st;
                        }
                        if (const auto st = lots_of_nested_.push_back(::protocyte::move(value)); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::colors: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                auto raw = ::protocyte::read_varint(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = static_cast<::protocyte::i32>(raw.value());
                                if (const auto st = colors_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::i32 value {};
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = static_cast<::protocyte::i32>(raw.value());
                        if (const auto st = colors_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::opt_int32: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        opt_int32_ = static_cast<::protocyte::i32>(raw.value());
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
                    case FieldNumber::extreme_nesting: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_extreme_nesting();
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
                    case FieldNumber::sha256: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() != INTEGER_ARRAY_CAP * 4u) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument,
                                                              reader.position(), field_number);
                        }
                        auto view = sha256_.mutable_view();
                        if (const auto st = reader.read(view.data, view.size); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::integer_array: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                auto raw = ::protocyte::read_varint(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = static_cast<::protocyte::i32>(raw.value());
                                if (const auto st = integer_array_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::i32 value {};
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = static_cast<::protocyte::i32>(raw.value());
                        if (const auto st = integer_array_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::byte_array: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() > BYTE_ARRAY_CAP) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::count_limit, reader.position(),
                                                              field_number);
                        }
                        if (const auto st = byte_array_.resize(static_cast<::protocyte::usize>(len.value())); !st) {
                            return st;
                        }
                        if (const auto st = reader.read(byte_array_.data(), byte_array_.size()); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::fixed_integer_array: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::u32 value {};
                                auto raw = ::protocyte::read_varint(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = static_cast<::protocyte::u32>(raw.value());
                                if (const auto st = fixed_integer_array_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::u32 value {};
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = static_cast<::protocyte::u32>(raw.value());
                        if (const auto st = fixed_integer_array_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::float_expr_array: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() > FLOATISH_BOUND) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::count_limit, reader.position(),
                                                              field_number);
                        }
                        if (const auto st = float_expr_array_.resize(static_cast<::protocyte::usize>(len.value()));
                            !st) {
                            return st;
                        }
                        if (const auto st = reader.read(float_expr_array_.data(), float_expr_array_.size()); !st) {
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
            if (!(fixed_integer_array_.size() == FIXED_INTEGER_ARRAY_CAP)) {
                return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument, {},
                                                  static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array));
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer &writer) const noexcept {
            if (!(fixed_integer_array_.size() == FIXED_INTEGER_ARRAY_CAP)) {
                return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument, {},
                                                  static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array));
            }
            if (f_double_ != 0.0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_double),
                                                           ::protocyte::WireType::I64);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed64(writer, ::std::bit_cast<::protocyte::u64>(f_double_));
                    !st) {
                    return st;
                }
            }
            if (f_float_ != 0.0f) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_float),
                                                           ::protocyte::WireType::I32);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed32(writer, ::std::bit_cast<::protocyte::u32>(f_float_));
                    !st) {
                    return st;
                }
            }
            if (f_int32_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_int32),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_int32_)); !st) {
                    return st;
                }
            }
            if (f_int64_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_int64),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_int64_)); !st) {
                    return st;
                }
            }
            if (f_uint32_ != 0u) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_uint32),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_uint32_)); !st) {
                    return st;
                }
            }
            if (f_uint64_ != 0u) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_uint64),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_uint64_)); !st) {
                    return st;
                }
            }
            if (f_sint32_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_sint32),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, ::protocyte::encode_zigzag32(f_sint32_)); !st) {
                    return st;
                }
            }
            if (f_sint64_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_sint64),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, ::protocyte::encode_zigzag64(f_sint64_)); !st) {
                    return st;
                }
            }
            if (f_fixed32_ != 0u) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_fixed32), ::protocyte::WireType::I32);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed32(writer, static_cast<::protocyte::u32>(f_fixed32_));
                    !st) {
                    return st;
                }
            }
            if (f_fixed64_ != 0u) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_fixed64), ::protocyte::WireType::I64);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed64(writer, static_cast<::protocyte::u64>(f_fixed64_));
                    !st) {
                    return st;
                }
            }
            if (f_sfixed32_ != 0) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sfixed32), ::protocyte::WireType::I32);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed32(writer, static_cast<::protocyte::u32>(f_sfixed32_));
                    !st) {
                    return st;
                }
            }
            if (f_sfixed64_ != 0) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::f_sfixed64), ::protocyte::WireType::I64);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed64(writer, static_cast<::protocyte::u64>(f_sfixed64_));
                    !st) {
                    return st;
                }
            }
            if (f_bool_) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::f_bool),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_bool_)); !st) {
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
            for (::protocyte::usize i {}; i < r_int32_unpacked_.size(); ++i) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked),
                                               ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(r_int32_unpacked_[i]));
                    !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::r_int32_packed),
                                               ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(r_int32_packed_[i]));
                    !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::r_double),
                                                           ::protocyte::WireType::I64);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed64(writer, ::std::bit_cast<::protocyte::u64>(r_double_[i]));
                    !st) {
                    return st;
                }
            }
            if (color_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::color),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(color_)); !st) {
                    return st;
                }
            }
            if (nested1_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::nested1),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = nested1_.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = nested1_.value().serialize(writer); !st) {
                    return st;
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
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_int32), ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(special_oneof.oneof_int32));
                    !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_msg) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::oneof_msg), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = special_oneof.oneof_msg.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = special_oneof.oneof_msg.value().serialize(writer); !st) {
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
            if (const auto st_map_map_str_int32 = map_str_int32_.for_each([&](const auto &key,
                                                                              const auto &value) noexcept {
                    enum struct EntryFieldNumber : ::protocyte::u32 {
                        key = 1u,
                        value = 2u,
                    };
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                    ::protocyte::varint_size(key.size()) + key.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(value)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    if (const auto st =
                            ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::map_str_int32),
                                                   ::protocyte::WireType::LEN);
                        !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                        !st) {
                        return st;
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::key),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, key.view()); !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                                       ::protocyte::WireType::VARINT);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(value));
                            !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
                !st_map_map_str_int32) {
                return st_map_map_str_int32;
            }
            if (const auto st_map_map_int32_str = map_int32_str_.for_each([&](const auto &key,
                                                                              const auto &value) noexcept {
                    enum struct EntryFieldNumber : ::protocyte::u32 {
                        key = 1u,
                        value = 2u,
                    };
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                    ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    if (const auto st =
                            ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::map_int32_str),
                                                   ::protocyte::WireType::LEN);
                        !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                        !st) {
                        return st;
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::key),
                                                       ::protocyte::WireType::VARINT);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key));
                            !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, value.view()); !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
                !st_map_map_int32_str) {
                return st_map_map_int32_str;
            }
            if (const auto st_map_map_bool_bytes = map_bool_bytes_.for_each([&](const auto &key,
                                                                                const auto &value) noexcept {
                    enum struct EntryFieldNumber : ::protocyte::u32 {
                        key = 1u,
                        value = 2u,
                    };
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                    ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    if (const auto st =
                            ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::map_bool_bytes),
                                                   ::protocyte::WireType::LEN);
                        !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                        !st) {
                        return st;
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::key),
                                                       ::protocyte::WireType::VARINT);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key));
                            !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, value.view()); !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
                !st_map_map_bool_bytes) {
                return st_map_map_bool_bytes;
            }
            if (const auto st_map_map_uint64_msg = map_uint64_msg_.for_each([&](const auto &key,
                                                                                const auto &value) noexcept {
                    enum struct EntryFieldNumber : ::protocyte::u32 {
                        key = 1u,
                        value = 2u,
                    };
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        auto nested_size = value.encoded_size();
                        if (!nested_size) {
                            return nested_size.status();
                        }
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                            !st_size) {
                            return st_size;
                        }
                    }
                    if (const auto st =
                            ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::map_uint64_msg),
                                                   ::protocyte::WireType::LEN);
                        !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                        !st) {
                        return st;
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::key),
                                                       ::protocyte::WireType::VARINT);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key));
                            !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        auto msg_size = value.encoded_size();
                        if (!msg_size) {
                            return msg_size.status();
                        }
                        if (const auto st =
                                ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                            !st) {
                            return st;
                        }
                        if (const auto st = value.serialize(writer); !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
                !st_map_map_uint64_msg) {
                return st_map_map_uint64_msg;
            }
            if (const auto st_map_very_nested_map = very_nested_map_.for_each([&](const auto &key,
                                                                                  const auto &value) noexcept {
                    enum struct EntryFieldNumber : ::protocyte::u32 {
                        key = 1u,
                        value = 2u,
                    };
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                    ::protocyte::varint_size(key.size()) + key.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        auto nested_size = value.encoded_size();
                        if (!nested_size) {
                            return nested_size.status();
                        }
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                            !st_size) {
                            return st_size;
                        }
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
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::key),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, key.view()); !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st =
                                ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(EntryFieldNumber::value),
                                                       ::protocyte::WireType::LEN);
                            !st) {
                            return st;
                        }
                        auto msg_size = value.encoded_size();
                        if (!msg_size) {
                            return msg_size.status();
                        }
                        if (const auto st =
                                ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                            !st) {
                            return st;
                        }
                        if (const auto st = value.serialize(writer); !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
                !st_map_very_nested_map) {
                return st_map_very_nested_map;
            }
            if (recursive_self_.has_value()) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::recursive_self), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = recursive_self_.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = recursive_self_.value().serialize(writer); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < lots_of_nested_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::lots_of_nested), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = lots_of_nested_[i].encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = lots_of_nested_[i].serialize(writer); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < colors_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::colors),
                                                           ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(colors_[i])); !st) {
                    return st;
                }
            }
            if (has_opt_int32_) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::opt_int32), ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(opt_int32_)); !st) {
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
            if (extreme_nesting_.has_value()) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::extreme_nesting),
                                               ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = extreme_nesting_.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = extreme_nesting_.value().serialize(writer); !st) {
                    return st;
                }
            }
            if (sha256_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::sha256),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, sha256_.view()); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < integer_array_.size(); ++i) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::integer_array),
                                               ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(integer_array_[i]));
                    !st) {
                    return st;
                }
            }
            if (!byte_array_.empty()) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::byte_array), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, byte_array_.view()); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < fixed_integer_array_.size(); ++i) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array),
                                               ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(fixed_integer_array_[i]));
                    !st) {
                    return st;
                }
            }
            if (!float_expr_array_.empty()) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::float_expr_array),
                                               ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, float_expr_array_.view()); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            if (!(fixed_integer_array_.size() == FIXED_INTEGER_ARRAY_CAP)) {
                return ::protocyte::Result<::protocyte::usize>::err(
                    ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument, {},
                                               static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array))
                        .error());
            }
            ::protocyte::usize total {};
            if (f_double_ != 0.0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_double)) + 8u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_float_ != 0.0f) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_float)) + 4u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
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
            if (f_bool_) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::f_bool)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_bool_)));
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
            for (::protocyte::usize i {}; i < r_int32_unpacked_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_unpacked)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_unpacked_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_int32_packed)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_packed_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::r_double)) + 8u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (color_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::color)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(color_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (nested1_.has_value()) {
                auto nested_size = nested1_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::nested1)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
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
            if (special_oneof_case_ == Special_oneofCase::oneof_msg) {
                auto nested_size = special_oneof.oneof_msg.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::oneof_msg)) +
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
            if (const auto st_map_size_map_str_int32 =
                    map_str_int32_.for_each([&](const auto &key, const auto &value) noexcept {
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::usize entry_payload {};
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                        ::protocyte::varint_size(key.size()) + key.size());
                                !st_size) {
                                return st_size;
                            }
                        }
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                        ::protocyte::varint_size(static_cast<::protocyte::u64>(value)));
                                !st_size) {
                                return st_size;
                            }
                        }
                        return ::protocyte::add_size(
                            &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::map_str_int32)) +
                                        ::protocyte::varint_size(entry_payload) + entry_payload);
                    });
                !st_map_size_map_str_int32) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_str_int32.error());
            }
            if (const auto st_map_size_map_int32_str =
                    map_int32_str_.for_each([&](const auto &key, const auto &value) noexcept {
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::usize entry_payload {};
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                        ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                                !st_size) {
                                return st_size;
                            }
                        }
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                        ::protocyte::varint_size(value.size()) + value.size());
                                !st_size) {
                                return st_size;
                            }
                        }
                        return ::protocyte::add_size(
                            &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::map_int32_str)) +
                                        ::protocyte::varint_size(entry_payload) + entry_payload);
                    });
                !st_map_size_map_int32_str) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_int32_str.error());
            }
            if (const auto st_map_size_map_bool_bytes =
                    map_bool_bytes_.for_each([&](const auto &key, const auto &value) noexcept {
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::usize entry_payload {};
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                        ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                                !st_size) {
                                return st_size;
                            }
                        }
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                        ::protocyte::varint_size(value.size()) + value.size());
                                !st_size) {
                                return st_size;
                            }
                        }
                        return ::protocyte::add_size(
                            &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::map_bool_bytes)) +
                                        ::protocyte::varint_size(entry_payload) + entry_payload);
                    });
                !st_map_size_map_bool_bytes) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_bool_bytes.error());
            }
            if (const auto st_map_size_map_uint64_msg =
                    map_uint64_msg_.for_each([&](const auto &key, const auto &value) noexcept {
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::usize entry_payload {};
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                        ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                                !st_size) {
                                return st_size;
                            }
                        }
                        {
                            auto nested_size = value.encoded_size();
                            if (!nested_size) {
                                return nested_size.status();
                            }
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                        ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                                !st_size) {
                                return st_size;
                            }
                        }
                        return ::protocyte::add_size(
                            &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::map_uint64_msg)) +
                                        ::protocyte::varint_size(entry_payload) + entry_payload);
                    });
                !st_map_size_map_uint64_msg) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_uint64_msg.error());
            }
            if (const auto st_map_size_very_nested_map =
                    very_nested_map_.for_each([&](const auto &key, const auto &value) noexcept {
                        enum struct EntryFieldNumber : ::protocyte::u32 {
                            key = 1u,
                            value = 2u,
                        };
                        ::protocyte::usize entry_payload {};
                        {
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::key)) +
                                        ::protocyte::varint_size(key.size()) + key.size());
                                !st_size) {
                                return st_size;
                            }
                        }
                        {
                            auto nested_size = value.encoded_size();
                            if (!nested_size) {
                                return nested_size.status();
                            }
                            if (const auto st_size = ::protocyte::add_size(
                                    &entry_payload,
                                    ::protocyte::tag_size(static_cast<::protocyte::u32>(EntryFieldNumber::value)) +
                                        ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                                !st_size) {
                                return st_size;
                            }
                        }
                        return ::protocyte::add_size(
                            &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::very_nested_map)) +
                                        ::protocyte::varint_size(entry_payload) + entry_payload);
                    });
                !st_map_size_very_nested_map) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_very_nested_map.error());
            }
            if (recursive_self_.has_value()) {
                auto nested_size = recursive_self_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::recursive_self)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < lots_of_nested_.size(); ++i) {
                auto nested_size = lots_of_nested_[i].encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::lots_of_nested)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < colors_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::colors)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(colors_[i])));
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
            if (extreme_nesting_.has_value()) {
                auto nested_size = extreme_nesting_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::extreme_nesting)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (sha256_.has_value()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::sha256)) +
                                    ::protocyte::varint_size(sha256_.size()) + sha256_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < integer_array_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::integer_array)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(integer_array_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!byte_array_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::byte_array)) +
                                    ::protocyte::varint_size(byte_array_.size()) + byte_array_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < fixed_integer_array_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::fixed_integer_array)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(fixed_integer_array_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!float_expr_array_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::float_expr_array)) +
                                    ::protocyte::varint_size(float_expr_array_.size()) + float_expr_array_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
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
            ::protocyte::ByteArray<BYTE_ARRAY_CAP> oneof_bytes;
        } special_oneof;
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
        ::protocyte::FixedByteArray<INTEGER_ARRAY_CAP * 4u> sha256_;
        ::protocyte::Array<::protocyte::i32, INTEGER_ARRAY_CAP> integer_array_;
        ::protocyte::ByteArray<BYTE_ARRAY_CAP> byte_array_;
        ::protocyte::Array<::protocyte::u32, FIXED_INTEGER_ARRAY_CAP> fixed_integer_array_;
        ::protocyte::ByteArray<FLOATISH_BOUND> float_expr_array_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        template<typename NestedConfig = Config> using LevelB = UltimateComplexMessage_LevelA_LevelB<NestedConfig>;

        explicit UltimateComplexMessage_LevelA(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_LevelA>::ok(UltimateComplexMessage_LevelA {ctx});
        }
        UltimateComplexMessage_LevelA(UltimateComplexMessage_LevelA &&) noexcept = default;
        UltimateComplexMessage_LevelA &operator=(UltimateComplexMessage_LevelA &&) noexcept = default;
        UltimateComplexMessage_LevelA(const UltimateComplexMessage_LevelA &) = delete;
        UltimateComplexMessage_LevelA &operator=(const UltimateComplexMessage_LevelA &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA>::err(st.error());
            }
            return out;
        }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage_LevelA> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA>::err(st.error());
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
                if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer & /* writer */) const noexcept {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            return ::protocyte::Result<::protocyte::usize>::ok({});
        }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        template<typename NestedConfig = Config> using LevelC =
            UltimateComplexMessage_LevelA_LevelB_LevelC<NestedConfig>;

        explicit UltimateComplexMessage_LevelA_LevelB(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB>::ok(
                UltimateComplexMessage_LevelA_LevelB {ctx});
        }
        UltimateComplexMessage_LevelA_LevelB(UltimateComplexMessage_LevelA_LevelB &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB &operator=(UltimateComplexMessage_LevelA_LevelB &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB(const UltimateComplexMessage_LevelA_LevelB &) = delete;
        UltimateComplexMessage_LevelA_LevelB &operator=(const UltimateComplexMessage_LevelA_LevelB &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB>::err(st.error());
            }
            return out;
        }

        template<typename Reader>
        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB> parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB>::err(st.error());
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
                if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer & /* writer */) const noexcept {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            return ::protocyte::Result<::protocyte::usize>::ok({});
        }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        template<typename NestedConfig = Config> using LevelD =
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD<NestedConfig>;

        explicit UltimateComplexMessage_LevelA_LevelB_LevelC(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC>::ok(
                UltimateComplexMessage_LevelA_LevelB_LevelC {ctx});
        }
        UltimateComplexMessage_LevelA_LevelB_LevelC(UltimateComplexMessage_LevelA_LevelB_LevelC &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB_LevelC &
        operator=(UltimateComplexMessage_LevelA_LevelB_LevelC &&) noexcept = default;
        UltimateComplexMessage_LevelA_LevelB_LevelC(const UltimateComplexMessage_LevelA_LevelB_LevelC &) = delete;
        UltimateComplexMessage_LevelA_LevelB_LevelC &
        operator=(const UltimateComplexMessage_LevelA_LevelB_LevelC &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB_LevelC &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC>::err(st.error());
            }
            return out;
        }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC>::err(st.error());
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
                if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer & /* writer */) const noexcept {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            return ::protocyte::Result<::protocyte::usize>::ok({});
        }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        template<typename NestedConfig = Config> using LevelE =
            UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<NestedConfig>;

        explicit UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD>::ok(
                UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD {ctx});
        }
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
                return ::protocyte::Status::ok();
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD> clone() const noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD>::err(st.error());
            }
            return out;
        }

        template<typename Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD>
        parse(Context &ctx, Reader &reader) noexcept {
            auto out = UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD>::err(st.error());
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
                if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        template<typename Writer> RuntimeStatus serialize(Writer & /* writer */) const noexcept {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            return ::protocyte::Result<::protocyte::usize>::ok({});
        }
    protected:
        Context *ctx_;
    };

    template<typename Config> struct ExtraMessage {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        enum struct FieldNumber : ::protocyte::u32 {
            tag = 1u,
            ref = 2u,
        };

        explicit ExtraMessage(Context &ctx) noexcept: ctx_ {&ctx}, tag_ {&ctx} {}

        static ::protocyte::Result<ExtraMessage> create(Context &ctx) noexcept {
            return ::protocyte::Result<ExtraMessage>::ok(ExtraMessage {ctx});
        }
        ExtraMessage(ExtraMessage &&) noexcept = default;
        ExtraMessage &operator=(ExtraMessage &&) noexcept = default;
        ExtraMessage(const ExtraMessage &) = delete;
        ExtraMessage &operator=(const ExtraMessage &) = delete;

        ::protocyte::Status copy_from(const ExtraMessage &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_tag(other.tag()); !st) {
                return st;
            }
            if (other.has_ref()) {
                if (auto ensured = ensure_ref(); !ensured) {
                    return ensured.status();
                } else if (const auto st = ensured.value().get().copy_from(*other.ref()); !st) {
                    return st;
                }
            } else {
                clear_ref();
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<ExtraMessage> clone() const noexcept {
            auto out = ExtraMessage::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<ExtraMessage>::err(st.error());
            }
            return out;
        }

        ::protocyte::ByteView tag() const noexcept { return tag_.view(); }
        typename Config::String &mutable_tag() noexcept { return tag_; }
        ::protocyte::Status set_tag(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            tag_ = ::protocyte::move(temp);
            return ::protocyte::Status::ok();
        }
        void clear_tag() noexcept { tag_.clear(); }

        bool has_ref() const noexcept { return ref_.has_value(); }
        const ::test::ultimate::UltimateComplexMessage<Config> *ref() const noexcept {
            return has_ref() ? &ref_.value() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>>> ensure_ref() noexcept {
            if (!ref_.has_value()) {
                if (const auto st = ref_.emplace(*ctx_); !st) {
                    return ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>>>::err(
                        st.error());
                }
            }
            return ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>>>::ok(
                ::protocyte::Ref<::test::ultimate::UltimateComplexMessage<Config>> {ref_.value()});
        }
        void clear_ref() noexcept { ref_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<ExtraMessage> parse(Context &ctx, Reader &reader) noexcept {
            auto out = ExtraMessage::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<ExtraMessage>::err(st.error());
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
                    case FieldNumber::tag: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), tag_);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::ref: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        auto ensured = ensure_ref();
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
            if (!tag_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::tag),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, tag_.view()); !st) {
                    return st;
                }
            }
            if (ref_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::ref),
                                                           ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                auto msg_size = ref_.value().encoded_size();
                if (!msg_size) {
                    return msg_size.status();
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value()));
                    !st) {
                    return st;
                }
                if (const auto st = ref_.value().serialize(writer); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!tag_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::tag)) +
                                    ::protocyte::varint_size(tag_.size()) + tag_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (ref_.has_value()) {
                auto nested_size = ref_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::ref)) +
                                    ::protocyte::varint_size(nested_size.value()) + nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        typename Config::String tag_;
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage<Config>> ref_;
    };

    template<typename Config> struct CrossMessageConstants_Nested {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        static constexpr ::protocyte::u32 EXTERNAL_CAP {8u};

        enum struct FieldNumber : ::protocyte::u32 {
            nested_bytes = 1u,
        };

        explicit CrossMessageConstants_Nested(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<CrossMessageConstants_Nested> create(Context &ctx) noexcept {
            return ::protocyte::Result<CrossMessageConstants_Nested>::ok(CrossMessageConstants_Nested {ctx});
        }
        CrossMessageConstants_Nested(CrossMessageConstants_Nested &&) noexcept = default;
        CrossMessageConstants_Nested &operator=(CrossMessageConstants_Nested &&) noexcept = default;
        CrossMessageConstants_Nested(const CrossMessageConstants_Nested &) = delete;
        CrossMessageConstants_Nested &operator=(const CrossMessageConstants_Nested &) = delete;

        ::protocyte::Status copy_from(const CrossMessageConstants_Nested &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_nested_bytes(other.nested_bytes()); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<CrossMessageConstants_Nested> clone() const noexcept {
            auto out = CrossMessageConstants_Nested::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<CrossMessageConstants_Nested>::err(st.error());
            }
            return out;
        }

        ::protocyte::ByteView nested_bytes() const noexcept { return nested_bytes_.view(); }
        ::protocyte::usize nested_bytes_size() const noexcept { return nested_bytes_.size(); }
        static constexpr ::protocyte::usize nested_bytes_max_size() noexcept { return EXTERNAL_CAP; }
        ::protocyte::Status resize_nested_bytes(const ::protocyte::usize size) noexcept {
            if (const auto st = nested_bytes_.resize(size); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        ::protocyte::MutableByteView mutable_nested_bytes() noexcept { return nested_bytes_.mutable_view(); }
        ::protocyte::Status set_nested_bytes(const ::protocyte::ByteView value) noexcept {
            if (const auto st = nested_bytes_.assign(value); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        void clear_nested_bytes() noexcept { nested_bytes_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<CrossMessageConstants_Nested> parse(Context &ctx, Reader &reader) noexcept {
            auto out = CrossMessageConstants_Nested::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<CrossMessageConstants_Nested>::err(st.error());
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
                    case FieldNumber::nested_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() > EXTERNAL_CAP) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::count_limit, reader.position(),
                                                              field_number);
                        }
                        if (const auto st = nested_bytes_.resize(static_cast<::protocyte::usize>(len.value())); !st) {
                            return st;
                        }
                        if (const auto st = reader.read(nested_bytes_.data(), nested_bytes_.size()); !st) {
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
            if (!nested_bytes_.empty()) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested_bytes), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, nested_bytes_.view()); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!nested_bytes_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::nested_bytes)) +
                                    ::protocyte::varint_size(nested_bytes_.size()) + nested_bytes_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        ::protocyte::ByteArray<EXTERNAL_CAP> nested_bytes_;
    };

    template<typename Config> struct CrossMessageConstants {
        using Context = typename Config::Context;
        using RuntimeStatus = ::protocyte::Status;
        template<typename NestedConfig = Config> using Nested = CrossMessageConstants_Nested<NestedConfig>;

        static constexpr ::protocyte::u32 ROOT_MIRROR {10u};
        static constexpr ::std::string_view LABEL_COPY {"proto-cross", 11u};
        static constexpr bool READY {true};

        enum struct FieldNumber : ::protocyte::u32 {
            external_bytes = 1u,
            mirrored_values = 2u,
            nested = 3u,
        };

        explicit CrossMessageConstants(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<CrossMessageConstants> create(Context &ctx) noexcept {
            return ::protocyte::Result<CrossMessageConstants>::ok(CrossMessageConstants {ctx});
        }
        CrossMessageConstants(CrossMessageConstants &&) noexcept = default;
        CrossMessageConstants &operator=(CrossMessageConstants &&) noexcept = default;
        CrossMessageConstants(const CrossMessageConstants &) = delete;
        CrossMessageConstants &operator=(const CrossMessageConstants &) = delete;

        ::protocyte::Status copy_from(const CrossMessageConstants &other) noexcept {
            if (this == &other) {
                return ::protocyte::Status::ok();
            }
            if (const auto st = set_external_bytes(other.external_bytes()); !st) {
                return st;
            }
            clear_mirrored_values();
            for (::protocyte::usize i {}; i < other.mirrored_values().size(); ++i) {
                if (const auto st = mutable_mirrored_values().push_back(other.mirrored_values()[i]); !st) {
                    return st;
                }
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
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<CrossMessageConstants> clone() const noexcept {
            auto out = CrossMessageConstants::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().copy_from(*this); !st) {
                return ::protocyte::Result<CrossMessageConstants>::err(st.error());
            }
            return out;
        }

        ::protocyte::ByteView external_bytes() const noexcept { return external_bytes_.view(); }
        ::protocyte::usize external_bytes_size() const noexcept { return external_bytes_.size(); }
        static constexpr ::protocyte::usize external_bytes_max_size() noexcept { return 4u + 2u; }
        ::protocyte::Status resize_external_bytes(const ::protocyte::usize size) noexcept {
            if (const auto st = external_bytes_.resize(size); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        ::protocyte::MutableByteView mutable_external_bytes() noexcept { return external_bytes_.mutable_view(); }
        ::protocyte::Status set_external_bytes(const ::protocyte::ByteView value) noexcept {
            if (const auto st = external_bytes_.assign(value); !st) {
                return st;
            }
            return ::protocyte::Status::ok();
        }
        void clear_external_bytes() noexcept { external_bytes_.clear(); }

        const ::protocyte::Array<::protocyte::i32, ROOT_MIRROR> &mirrored_values() const noexcept {
            return mirrored_values_;
        }
        ::protocyte::Array<::protocyte::i32, ROOT_MIRROR> &mutable_mirrored_values() noexcept {
            return mirrored_values_;
        }
        void clear_mirrored_values() noexcept { mirrored_values_.clear(); }

        bool has_nested() const noexcept { return nested_.has_value(); }
        const ::test::ultimate::CrossMessageConstants_Nested<Config> *nested() const noexcept {
            return has_nested() ? &nested_.value() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>>>
        ensure_nested() noexcept {
            if (!nested_.has_value()) {
                if (const auto st = nested_.emplace(*ctx_); !st) {
                    return ::protocyte::Result<
                        ::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>>>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>>>::ok(
                ::protocyte::Ref<::test::ultimate::CrossMessageConstants_Nested<Config>> {nested_.value()});
        }
        void clear_nested() noexcept { nested_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<CrossMessageConstants> parse(Context &ctx, Reader &reader) noexcept {
            auto out = CrossMessageConstants::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<CrossMessageConstants>::err(st.error());
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
                    case FieldNumber::external_bytes: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() > 4u + 2u) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::count_limit, reader.position(),
                                                              field_number);
                        }
                        if (const auto st = external_bytes_.resize(static_cast<::protocyte::usize>(len.value())); !st) {
                            return st;
                        }
                        if (const auto st = reader.read(external_bytes_.data(), external_bytes_.size()); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::mirrored_values: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                auto raw = ::protocyte::read_varint(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                value = static_cast<::protocyte::i32>(raw.value());
                                if (const auto st = mirrored_values_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        ::protocyte::i32 value {};
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        value = static_cast<::protocyte::i32>(raw.value());
                        if (const auto st = mirrored_values_.push_back(value); !st) {
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
            if (!external_bytes_.empty()) {
                if (const auto st = ::protocyte::write_tag(
                        writer, static_cast<::protocyte::u32>(FieldNumber::external_bytes), ::protocyte::WireType::LEN);
                    !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, external_bytes_.view()); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < mirrored_values_.size(); ++i) {
                if (const auto st =
                        ::protocyte::write_tag(writer, static_cast<::protocyte::u32>(FieldNumber::mirrored_values),
                                               ::protocyte::WireType::VARINT);
                    !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(mirrored_values_[i]));
                    !st) {
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
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!external_bytes_.empty()) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::external_bytes)) +
                                    ::protocyte::varint_size(external_bytes_.size()) + external_bytes_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < mirrored_values_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::mirrored_values)) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(mirrored_values_[i])));
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
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        ::protocyte::ByteArray<4u + 2u> external_bytes_;
        ::protocyte::Array<::protocyte::i32, ROOT_MIRROR> mirrored_values_;
        typename Config::template Optional<::test::ultimate::CrossMessageConstants_Nested<Config>> nested_;
    };


} // namespace test::ultimate

#endif // PROTOCYTE_GENERATED_EXAMPLE_PROTO_HPP
