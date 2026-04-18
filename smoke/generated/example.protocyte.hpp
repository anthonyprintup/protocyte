#pragma once

#ifndef PROTOCYTE_GENERATED_EXAMPLE_PROTO_HPP
#define PROTOCYTE_GENERATED_EXAMPLE_PROTO_HPP

#include <protocyte/runtime/runtime.hpp>

namespace test::ultimate {

    enum class UltimateComplexMessage_Color : ::protocyte::i32 {
        COLOR_UNSPECIFIED = 0,
        RED = 1,
        GREEN = 2,
        BLUE = 3,
    };

    enum class UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum : ::protocyte::i32 {
        INNER_UNSPECIFIED = 0,
        A = 1,
        B = 2,
        C = 3,
    };

    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_NestedLevel1_NestedLevel2;
    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_NestedLevel1;
    template<class Config = ::protocyte::DefaultConfig>
    struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE;
    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage;
    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA;
    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA_LevelB;
    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA_LevelB_LevelC;
    template<class Config = ::protocyte::DefaultConfig> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD;
    template<class Config = ::protocyte::DefaultConfig> struct ExtraMessage;

    template<class Config> struct UltimateComplexMessage_NestedLevel1_NestedLevel2 {
        using Context = typename Config::Context;
        using InnerEnum = UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum;

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
            (void) other;
            auto st_description = set_description(other.description());
            if (!st_description) {
                return st_description;
            }
            auto st_mode = set_mode_raw(other.mode_raw());
            if (!st_mode) {
                return st_mode;
            }
            // Full deep copy for repeated, map, and oneof storage is reserved for the next conformance pass.
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

        ::protocyte::i32 mode_raw() const noexcept { return mode_; }
        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum mode() const noexcept {
            return static_cast<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum>(mode_);
        }
        ::protocyte::Status set_mode_raw(const ::protocyte::i32 value) noexcept {
            mode_ = value;
            return ::protocyte::Status::ok();
        }
        ::protocyte::Status
        set_mode(const ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2_InnerEnum value) noexcept {
            return set_mode_raw(static_cast<::protocyte::i32>(value));
        }
        void clear_mode() noexcept { mode_ = 0; }

        template<class Reader> static ::protocyte::Result<UltimateComplexMessage_NestedLevel1_NestedLevel2>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
                    case 1u: {
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
                    case 2u: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::f32 value {0.0f};
                                auto raw = ::protocyte::read_fixed32(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                union {
                                    ::protocyte::u32 bits;
                                    ::protocyte::f32 value;
                                } conv;
                                conv.bits = raw.value();
                                value = conv.value;
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
                        ::protocyte::f32 value {0.0f};
                        auto raw = ::protocyte::read_fixed32(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        union {
                            ::protocyte::u32 bits;
                            ::protocyte::f32 value;
                        } conv;
                        conv.bits = raw.value();
                        value = conv.value;
                        if (const auto st = values_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case 3u: {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            if (!description_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, description_.view()); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < values_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::I32); !st) {
                    return st;
                }
                union {
                    ::protocyte::f32 value;
                    ::protocyte::u32 bits;
                } conv;
                conv.value = values_[i];
                if (const auto st = ::protocyte::write_fixed32(writer, conv.bits); !st) {
                    return st;
                }
            }
            if (mode_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 3u, ::protocyte::WireType::VARINT); !st) {
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
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(1u) +
                                                                      ::protocyte::varint_size(description_.size()) +
                                                                      description_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < values_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(2u) + 4u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (mode_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(3u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(mode_)));
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
        ::protocyte::i32 mode_ = 0;
    };

    template<class Config> struct UltimateComplexMessage_NestedLevel1 {
        using Context = typename Config::Context;
        template<class NestedConfig = Config> using NestedLevel2 =
            UltimateComplexMessage_NestedLevel1_NestedLevel2<NestedConfig>;

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
            (void) other;
            auto st_name = set_name(other.name());
            if (!st_name) {
                return st_name;
            }
            auto st_id = set_id(other.id());
            if (!st_id) {
                return st_id;
            }
            if (other.has_inner()) {
                auto ensured = ensure_inner();
                if (!ensured) {
                    return ensured.status();
                }
                if (const auto st = ensured.value().get().copy_from(*other.inner()); !st) {
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

        ::protocyte::i32 id() const noexcept { return id_; }
        ::protocyte::Status set_id(const ::protocyte::i32 value) noexcept {
            id_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_id() noexcept { id_ = 0; }

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

        template<class Reader>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
                    case 1u: {
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
                    case 2u: {
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
                    case 3u: {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            if (!name_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, name_.view()); !st) {
                    return st;
                }
            }
            if (id_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(id_)); !st) {
                    return st;
                }
            }
            if (inner_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, 3u, ::protocyte::WireType::LEN); !st) {
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
                        &total, ::protocyte::tag_size(1u) + ::protocyte::varint_size(name_.size()) + name_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (id_ != 0) {
                if (const auto st =
                        ::protocyte::add_size(&total, ::protocyte::tag_size(2u) +
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
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(3u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        typename Config::String name_;
        ::protocyte::i32 id_ = 0;
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config>>
            inner_;
    };

    template<class Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE {
        using Context = typename Config::Context;

        enum class Deep_oneofCase : ::protocyte::u32 {
            none = 0u,
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
                    new (&deep_oneof.val)::protocyte::i64(other.deep_oneof.val);
                    deep_oneof_case_ = Deep_oneofCase::val;
                    break;
                }
                case Deep_oneofCase::text: {
                    new (&deep_oneof.text) typename Config::String(::protocyte::move(other.deep_oneof.text));
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
                    new (&deep_oneof.val)::protocyte::i64(other.deep_oneof.val);
                    deep_oneof_case_ = Deep_oneofCase::val;
                    break;
                }
                case Deep_oneofCase::text: {
                    new (&deep_oneof.text) typename Config::String(::protocyte::move(other.deep_oneof.text));
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

        template<class T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE &other) noexcept {
            (void) other;
            auto st_extreme = set_extreme(other.extreme());
            if (!st_extreme) {
                return st_extreme;
            }
            // Full deep copy for repeated, map, and oneof storage is reserved for the next conformance pass.
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

        Deep_oneofCase deep_oneof_case() const noexcept { return deep_oneof_case_; }
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

        bool has_val() const noexcept { return deep_oneof_case_ == Deep_oneofCase::val; }
        ::protocyte::i64 val() const noexcept { return has_val() ? deep_oneof.val : 0; }
        ::protocyte::Status set_val(const ::protocyte::i64 value) noexcept {
            clear_deep_oneof();
            new (&deep_oneof.val)::protocyte::i64(value);
            deep_oneof_case_ = Deep_oneofCase::val;
            return ::protocyte::Status::ok();
        }

        bool has_text() const noexcept { return deep_oneof_case_ == Deep_oneofCase::text; }
        ::protocyte::ByteView text() const noexcept {
            return has_text() ? deep_oneof.text.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_text(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_deep_oneof();
            new (&deep_oneof.text) typename Config::String(::protocyte::move(temp));
            deep_oneof_case_ = Deep_oneofCase::text;
            return ::protocyte::Status::ok();
        }

        template<class Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
                    case 1u: {
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
                    case 2u: {
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
                        ::protocyte::i32 key = 0;
                        typename Config::String value {ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 1u);
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = static_cast<::protocyte::i32>(raw.value());
                                    break;
                                }
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 2u);
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
                        auto insert = weird_map_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                        if (!insert) {
                            return insert;
                        }
                        break;
                    }
                    case 3u: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        clear_deep_oneof();
                        new (&deep_oneof.val)::protocyte::i64(0);
                        deep_oneof_case_ = Deep_oneofCase::val;
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        deep_oneof.val = static_cast<::protocyte::i64>(raw.value());
                        break;
                    }
                    case 4u: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        clear_deep_oneof();
                        new (&deep_oneof.text) typename Config::String(ctx_);
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            if (!extreme_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, extreme_.view()); !st) {
                    return st;
                }
            }
            auto st_map_weird_map = weird_map_.for_each([&](const auto &key,
                                                            const auto &value) noexcept -> ::protocyte::Status {
                ::protocyte::usize entry_payload {};
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(1u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                        !st_size) {
                        return st_size;
                    }
                }
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(2u) + ::protocyte::varint_size(value.size()) + value.size());
                        !st_size) {
                        return st_size;
                    }
                }
                if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::VARINT); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key)); !st) {
                        return st;
                    }
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_bytes(writer, value.view()); !st) {
                        return st;
                    }
                }
                return ::protocyte::Status {};
            });
            if (!st_map_weird_map) {
                return st_map_weird_map;
            }
            if (deep_oneof_case_ == Deep_oneofCase::val) {
                if (const auto st = ::protocyte::write_tag(writer, 3u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(deep_oneof.val));
                    !st) {
                    return st;
                }
            }
            if (deep_oneof_case_ == Deep_oneofCase::text) {
                if (const auto st = ::protocyte::write_tag(writer, 4u, ::protocyte::WireType::LEN); !st) {
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
                if (const auto st =
                        ::protocyte::add_size(&total, ::protocyte::tag_size(1u) +
                                                          ::protocyte::varint_size(extreme_.size()) + extreme_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            auto st_map_size_weird_map =
                weird_map_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload, ::protocyte::tag_size(1u) +
                                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(2u) + ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    return ::protocyte::add_size(&total, ::protocyte::tag_size(2u) +
                                                             ::protocyte::varint_size(entry_payload) + entry_payload);
                });
            if (!st_map_size_weird_map) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_weird_map.error());
            }
            if (deep_oneof_case_ == Deep_oneofCase::val) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(3u) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(deep_oneof.val)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (deep_oneof_case_ == Deep_oneofCase::text) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(4u) +
                                                                      ::protocyte::varint_size(deep_oneof.text.size()) +
                                                                      deep_oneof.text.size());
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
        Deep_oneofCase deep_oneof_case_ = Deep_oneofCase::none;
        union Deep_oneofStorage {
            Deep_oneofStorage() noexcept {}
            ~Deep_oneofStorage() noexcept {}
            ::protocyte::i64 val;
            typename Config::String text;
        } deep_oneof;
    };

    template<class Config> struct UltimateComplexMessage {
        using Context = typename Config::Context;
        using Color = UltimateComplexMessage_Color;
        template<class NestedConfig = Config> using NestedLevel1 = UltimateComplexMessage_NestedLevel1<NestedConfig>;
        template<class NestedConfig = Config> using LevelA = UltimateComplexMessage_LevelA<NestedConfig>;

        enum class Special_oneofCase : ::protocyte::u32 {
            none = 0u,
            oneof_string = 26u,
            oneof_int32 = 27u,
            oneof_msg = 28u,
            oneof_bytes = 29u,
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
            extreme_nesting_ {::protocyte::move(other.extreme_nesting_)} {
            has_opt_int32_ = other.has_opt_int32_;
            has_opt_string_ = other.has_opt_string_;
            has_sha256_ = other.has_sha256_;
            if (other.has_sha256_) {
                for (::protocyte::usize i {}; i < 32u; ++i) { sha256_[i] = other.sha256_[i]; }
            }
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    new (&special_oneof.oneof_string)
                        typename Config::String(::protocyte::move(other.special_oneof.oneof_string));
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    new (&special_oneof.oneof_int32)::protocyte::i32(other.special_oneof.oneof_int32);
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case Special_oneofCase::oneof_msg: {
                    new (&special_oneof.oneof_msg) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>(
                        ::protocyte::move(other.special_oneof.oneof_msg));
                    special_oneof_case_ = Special_oneofCase::oneof_msg;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof.oneof_bytes)
                        typename Config::Bytes(::protocyte::move(other.special_oneof.oneof_bytes));
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
            has_sha256_ = other.has_sha256_;
            if (other.has_sha256_) {
                for (::protocyte::usize i {}; i < 32u; ++i) { sha256_[i] = other.sha256_[i]; }
            }
            extreme_nesting_ = ::protocyte::move(other.extreme_nesting_);
            switch (other.special_oneof_case_) {
                case Special_oneofCase::oneof_string: {
                    new (&special_oneof.oneof_string)
                        typename Config::String(::protocyte::move(other.special_oneof.oneof_string));
                    special_oneof_case_ = Special_oneofCase::oneof_string;
                    break;
                }
                case Special_oneofCase::oneof_int32: {
                    new (&special_oneof.oneof_int32)::protocyte::i32(other.special_oneof.oneof_int32);
                    special_oneof_case_ = Special_oneofCase::oneof_int32;
                    break;
                }
                case Special_oneofCase::oneof_msg: {
                    new (&special_oneof.oneof_msg) typename Config::template Optional<
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>(
                        ::protocyte::move(other.special_oneof.oneof_msg));
                    special_oneof_case_ = Special_oneofCase::oneof_msg;
                    break;
                }
                case Special_oneofCase::oneof_bytes: {
                    new (&special_oneof.oneof_bytes)
                        typename Config::Bytes(::protocyte::move(other.special_oneof.oneof_bytes));
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

        template<class T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const UltimateComplexMessage &other) noexcept {
            (void) other;
            auto st_f_double = set_f_double(other.f_double());
            if (!st_f_double) {
                return st_f_double;
            }
            auto st_f_float = set_f_float(other.f_float());
            if (!st_f_float) {
                return st_f_float;
            }
            auto st_f_int32 = set_f_int32(other.f_int32());
            if (!st_f_int32) {
                return st_f_int32;
            }
            auto st_f_int64 = set_f_int64(other.f_int64());
            if (!st_f_int64) {
                return st_f_int64;
            }
            auto st_f_uint32 = set_f_uint32(other.f_uint32());
            if (!st_f_uint32) {
                return st_f_uint32;
            }
            auto st_f_uint64 = set_f_uint64(other.f_uint64());
            if (!st_f_uint64) {
                return st_f_uint64;
            }
            auto st_f_sint32 = set_f_sint32(other.f_sint32());
            if (!st_f_sint32) {
                return st_f_sint32;
            }
            auto st_f_sint64 = set_f_sint64(other.f_sint64());
            if (!st_f_sint64) {
                return st_f_sint64;
            }
            auto st_f_fixed32 = set_f_fixed32(other.f_fixed32());
            if (!st_f_fixed32) {
                return st_f_fixed32;
            }
            auto st_f_fixed64 = set_f_fixed64(other.f_fixed64());
            if (!st_f_fixed64) {
                return st_f_fixed64;
            }
            auto st_f_sfixed32 = set_f_sfixed32(other.f_sfixed32());
            if (!st_f_sfixed32) {
                return st_f_sfixed32;
            }
            auto st_f_sfixed64 = set_f_sfixed64(other.f_sfixed64());
            if (!st_f_sfixed64) {
                return st_f_sfixed64;
            }
            auto st_f_bool = set_f_bool(other.f_bool());
            if (!st_f_bool) {
                return st_f_bool;
            }
            auto st_f_string = set_f_string(other.f_string());
            if (!st_f_string) {
                return st_f_string;
            }
            auto st_f_bytes = set_f_bytes(other.f_bytes());
            if (!st_f_bytes) {
                return st_f_bytes;
            }
            auto st_color = set_color_raw(other.color_raw());
            if (!st_color) {
                return st_color;
            }
            if (other.has_nested1()) {
                auto ensured = ensure_nested1();
                if (!ensured) {
                    return ensured.status();
                }
                if (const auto st = ensured.value().get().copy_from(*other.nested1()); !st) {
                    return st;
                }
            } else {
                clear_nested1();
            }
            if (other.has_recursive_self()) {
                auto ensured = ensure_recursive_self();
                if (!ensured) {
                    return ensured.status();
                }
                if (const auto st = ensured.value().get().copy_from(*other.recursive_self()); !st) {
                    return st;
                }
            } else {
                clear_recursive_self();
            }
            if (other.has_opt_int32()) {
                auto st_opt_int32 = set_opt_int32(other.opt_int32());
                if (!st_opt_int32) {
                    return st_opt_int32;
                }
            } else {
                clear_opt_int32();
            }
            if (other.has_opt_string()) {
                auto st_opt_string = set_opt_string(other.opt_string());
                if (!st_opt_string) {
                    return st_opt_string;
                }
            } else {
                clear_opt_string();
            }
            if (other.has_sha256()) {
                auto st_sha256 = set_sha256(other.sha256());
                if (!st_sha256) {
                    return st_sha256;
                }
            } else {
                clear_sha256();
            }
            if (other.has_extreme_nesting()) {
                auto ensured = ensure_extreme_nesting();
                if (!ensured) {
                    return ensured.status();
                }
                if (const auto st = ensured.value().get().copy_from(*other.extreme_nesting()); !st) {
                    return st;
                }
            } else {
                clear_extreme_nesting();
            }
            // Full deep copy for repeated, map, and oneof storage is reserved for the next conformance pass.
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

        Special_oneofCase special_oneof_case() const noexcept { return special_oneof_case_; }
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

        ::protocyte::f64 f_double() const noexcept { return f_double_; }
        ::protocyte::Status set_f_double(const ::protocyte::f64 value) noexcept {
            f_double_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_double() noexcept { f_double_ = 0.0; }

        ::protocyte::f32 f_float() const noexcept { return f_float_; }
        ::protocyte::Status set_f_float(const ::protocyte::f32 value) noexcept {
            f_float_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_float() noexcept { f_float_ = 0.0f; }

        ::protocyte::i32 f_int32() const noexcept { return f_int32_; }
        ::protocyte::Status set_f_int32(const ::protocyte::i32 value) noexcept {
            f_int32_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_int32() noexcept { f_int32_ = 0; }

        ::protocyte::i64 f_int64() const noexcept { return f_int64_; }
        ::protocyte::Status set_f_int64(const ::protocyte::i64 value) noexcept {
            f_int64_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_int64() noexcept { f_int64_ = 0; }

        ::protocyte::u32 f_uint32() const noexcept { return f_uint32_; }
        ::protocyte::Status set_f_uint32(const ::protocyte::u32 value) noexcept {
            f_uint32_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_uint32() noexcept { f_uint32_ = 0u; }

        ::protocyte::u64 f_uint64() const noexcept { return f_uint64_; }
        ::protocyte::Status set_f_uint64(const ::protocyte::u64 value) noexcept {
            f_uint64_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_uint64() noexcept { f_uint64_ = 0u; }

        ::protocyte::i32 f_sint32() const noexcept { return f_sint32_; }
        ::protocyte::Status set_f_sint32(const ::protocyte::i32 value) noexcept {
            f_sint32_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_sint32() noexcept { f_sint32_ = 0; }

        ::protocyte::i64 f_sint64() const noexcept { return f_sint64_; }
        ::protocyte::Status set_f_sint64(const ::protocyte::i64 value) noexcept {
            f_sint64_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_sint64() noexcept { f_sint64_ = 0; }

        ::protocyte::u32 f_fixed32() const noexcept { return f_fixed32_; }
        ::protocyte::Status set_f_fixed32(const ::protocyte::u32 value) noexcept {
            f_fixed32_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_fixed32() noexcept { f_fixed32_ = 0u; }

        ::protocyte::u64 f_fixed64() const noexcept { return f_fixed64_; }
        ::protocyte::Status set_f_fixed64(const ::protocyte::u64 value) noexcept {
            f_fixed64_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_fixed64() noexcept { f_fixed64_ = 0u; }

        ::protocyte::i32 f_sfixed32() const noexcept { return f_sfixed32_; }
        ::protocyte::Status set_f_sfixed32(const ::protocyte::i32 value) noexcept {
            f_sfixed32_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_sfixed32() noexcept { f_sfixed32_ = 0; }

        ::protocyte::i64 f_sfixed64() const noexcept { return f_sfixed64_; }
        ::protocyte::Status set_f_sfixed64(const ::protocyte::i64 value) noexcept {
            f_sfixed64_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_sfixed64() noexcept { f_sfixed64_ = 0; }

        bool f_bool() const noexcept { return f_bool_; }
        ::protocyte::Status set_f_bool(const bool value) noexcept {
            f_bool_ = value;
            return ::protocyte::Status::ok();
        }
        void clear_f_bool() noexcept { f_bool_ = false; }

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

        ::protocyte::i32 color_raw() const noexcept { return color_; }
        ::test::ultimate::UltimateComplexMessage_Color color() const noexcept {
            return static_cast<::test::ultimate::UltimateComplexMessage_Color>(color_);
        }
        ::protocyte::Status set_color_raw(const ::protocyte::i32 value) noexcept {
            color_ = value;
            return ::protocyte::Status::ok();
        }
        ::protocyte::Status set_color(const ::test::ultimate::UltimateComplexMessage_Color value) noexcept {
            return set_color_raw(static_cast<::protocyte::i32>(value));
        }
        void clear_color() noexcept { color_ = 0; }

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

        bool has_oneof_string() const noexcept { return special_oneof_case_ == Special_oneofCase::oneof_string; }
        ::protocyte::ByteView oneof_string() const noexcept {
            return has_oneof_string() ? special_oneof.oneof_string.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_oneof_string(const ::protocyte::ByteView value) noexcept {
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_string) typename Config::String(::protocyte::move(temp));
            special_oneof_case_ = Special_oneofCase::oneof_string;
            return ::protocyte::Status::ok();
        }

        bool has_oneof_int32() const noexcept { return special_oneof_case_ == Special_oneofCase::oneof_int32; }
        ::protocyte::i32 oneof_int32() const noexcept { return has_oneof_int32() ? special_oneof.oneof_int32 : 0; }
        ::protocyte::Status set_oneof_int32(const ::protocyte::i32 value) noexcept {
            clear_special_oneof();
            new (&special_oneof.oneof_int32)::protocyte::i32(value);
            special_oneof_case_ = Special_oneofCase::oneof_int32;
            return ::protocyte::Status::ok();
        }

        bool has_oneof_msg() const noexcept { return special_oneof_case_ == Special_oneofCase::oneof_msg; }
        const ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> *oneof_msg() const noexcept {
            return has_oneof_msg() && special_oneof.oneof_msg.has_value() ? &special_oneof.oneof_msg.value() : nullptr;
        }
        ::protocyte::Result<::protocyte::Ref<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>>
        ensure_oneof_msg() noexcept {
            if (!has_oneof_msg()) {
                clear_special_oneof();
                new (&special_oneof.oneof_msg)
                    typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>>();
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

        bool has_oneof_bytes() const noexcept { return special_oneof_case_ == Special_oneofCase::oneof_bytes; }
        ::protocyte::ByteView oneof_bytes() const noexcept {
            return has_oneof_bytes() ? special_oneof.oneof_bytes.view() : ::protocyte::ByteView {};
        }
        ::protocyte::Status set_oneof_bytes(const ::protocyte::ByteView value) noexcept {
            typename Config::Bytes temp {ctx_};
            if (const auto st = temp.assign(value); !st) {
                return st;
            }
            clear_special_oneof();
            new (&special_oneof.oneof_bytes) typename Config::Bytes(::protocyte::move(temp));
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

        ::protocyte::i32 opt_int32() const noexcept { return opt_int32_; }
        bool has_opt_int32() const noexcept { return has_opt_int32_; }
        ::protocyte::Status set_opt_int32(const ::protocyte::i32 value) noexcept {
            opt_int32_ = value;
            has_opt_int32_ = true;
            return ::protocyte::Status::ok();
        }
        void clear_opt_int32() noexcept {
            opt_int32_ = 0;
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

        bool has_sha256() const noexcept { return has_sha256_; }
        ::protocyte::ByteView sha256() const noexcept {
            return has_sha256_ ? ::protocyte::ByteView {.data = sha256_, .size = 32u} : ::protocyte::ByteView {};
        }
        ::protocyte::MutableByteView mutable_sha256() noexcept {
            if (!has_sha256_) {
                for (::protocyte::usize i {}; i < 32u; ++i) { sha256_[i] = 0u; }
                has_sha256_ = true;
            }
            return ::protocyte::MutableByteView {.data = sha256_, .size = 32u};
        }
        ::protocyte::Status set_sha256(const ::protocyte::ByteView value) noexcept {
            if (value.size != 32u) {
                return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument);
            }
            for (::protocyte::usize i {}; i < 32u; ++i) { sha256_[i] = value.data[i]; }
            has_sha256_ = true;
            return ::protocyte::Status::ok();
        }
        void clear_sha256() noexcept { has_sha256_ = false; }

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

        template<class Reader>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
                    case 1u: {
                        if (wire_type != ::protocyte::WireType::I64) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed64(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        union {
                            ::protocyte::u64 bits;
                            ::protocyte::f64 value;
                        } conv;
                        conv.bits = raw.value();
                        f_double_ = conv.value;
                        break;
                    }
                    case 2u: {
                        if (wire_type != ::protocyte::WireType::I32) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto raw = ::protocyte::read_fixed32(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        union {
                            ::protocyte::u32 bits;
                            ::protocyte::f32 value;
                        } conv;
                        conv.bits = raw.value();
                        f_float_ = conv.value;
                        break;
                    }
                    case 4u: {
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
                    case 8u: {
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
                    case 9u: {
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
                    case 10u: {
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
                    case 11u: {
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
                    case 12u: {
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
                    case 13u: {
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
                    case 14u: {
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
                    case 15u: {
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
                    case 16u: {
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
                    case 17u: {
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
                    case 18u: {
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
                    case 19u: {
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
                    case 21u: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {0};
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
                        ::protocyte::i32 value {0};
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
                    case 22u: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {0};
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
                        ::protocyte::i32 value {0};
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
                    case 23u: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::f64 value {0.0};
                                auto raw = ::protocyte::read_fixed64(packed);
                                if (!raw) {
                                    return raw.status();
                                }
                                union {
                                    ::protocyte::u64 bits;
                                    ::protocyte::f64 value;
                                } conv;
                                conv.bits = raw.value();
                                value = conv.value;
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
                        ::protocyte::f64 value {0.0};
                        auto raw = ::protocyte::read_fixed64(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        union {
                            ::protocyte::u64 bits;
                            ::protocyte::f64 value;
                        } conv;
                        conv.bits = raw.value();
                        value = conv.value;
                        if (const auto st = r_double_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case 24u: {
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
                    case 25u: {
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
                    case 26u: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_string) typename Config::String(ctx_);
                        special_oneof_case_ = Special_oneofCase::oneof_string;
                        if (const auto st = ::protocyte::read_string<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()),
                                special_oneof.oneof_string);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case 27u: {
                        if (wire_type != ::protocyte::WireType::VARINT) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_int32)::protocyte::i32(0);
                        special_oneof_case_ = Special_oneofCase::oneof_int32;
                        auto raw = ::protocyte::read_varint(reader);
                        if (!raw) {
                            return raw.status();
                        }
                        special_oneof.oneof_int32 = static_cast<::protocyte::i32>(raw.value());
                        break;
                    }
                    case 28u: {
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
                    case 29u: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        clear_special_oneof();
                        new (&special_oneof.oneof_bytes) typename Config::Bytes(ctx_);
                        special_oneof_case_ = Special_oneofCase::oneof_bytes;
                        if (const auto st = ::protocyte::read_bytes<Config>(
                                *ctx_, reader, static_cast<::protocyte::usize>(len.value()), special_oneof.oneof_bytes);
                            !st) {
                            return st;
                        }
                        break;
                    }
                    case 30u: {
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
                        typename Config::String key {ctx_};
                        ::protocyte::i32 value = 0;
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 1u);
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
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 2u);
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
                        auto insert = map_str_int32_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                        if (!insert) {
                            return insert;
                        }
                        break;
                    }
                    case 31u: {
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
                        ::protocyte::i32 key = 0;
                        typename Config::String value {ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 1u);
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = static_cast<::protocyte::i32>(raw.value());
                                    break;
                                }
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 2u);
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
                        auto insert = map_int32_str_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                        if (!insert) {
                            return insert;
                        }
                        break;
                    }
                    case 32u: {
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
                        bool key = false;
                        typename Config::Bytes value {ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 1u);
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = raw.value() != 0u;
                                    break;
                                }
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 2u);
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
                        auto insert =
                            map_bool_bytes_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                        if (!insert) {
                            return insert;
                        }
                        break;
                    }
                    case 33u: {
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
                        ::protocyte::u64 key = 0u;
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1<Config> value {*ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::VARINT) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 1u);
                                    }
                                    auto raw = ::protocyte::read_varint(entry_reader);
                                    if (!raw) {
                                        return raw.status();
                                    }
                                    key = static_cast<::protocyte::u64>(raw.value());
                                    break;
                                }
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 2u);
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
                        auto insert =
                            map_uint64_msg_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                        if (!insert) {
                            return insert;
                        }
                        break;
                    }
                    case 34u: {
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
                        typename Config::String key {ctx_};
                        ::test::ultimate::UltimateComplexMessage_NestedLevel1_NestedLevel2<Config> value {*ctx_};
                        while (!entry_reader.eof()) {
                            auto entry_tag = ::protocyte::read_varint(entry_reader);
                            if (!entry_tag) {
                                return entry_tag.status();
                            }
                            const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);
                            const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);
                            switch (entry_field) {
                                case 1u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 1u);
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
                                case 2u: {
                                    if (entry_wire != ::protocyte::WireType::LEN) {
                                        return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                                          entry_reader.position(), 2u);
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
                        auto insert =
                            very_nested_map_.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));
                        if (!insert) {
                            return insert;
                        }
                        break;
                    }
                    case 35u: {
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
                    case 36u: {
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
                    case 37u: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_varint(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader,
                                                                       static_cast<::protocyte::usize>(len.value())};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {0};
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
                        ::protocyte::i32 value {0};
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
                    case 38u: {
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
                    case 39u: {
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
                    case 40u: {
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
                    case 41u: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type,
                                                              reader.position(), field_number);
                        }
                        auto len = ::protocyte::read_varint(reader);
                        if (!len) {
                            return len.status();
                        }
                        if (len.value() == 32u) {
                            if (const auto st = reader.read(sha256_, 32u); !st) {
                                return st;
                            }
                            has_sha256_ = true;
                        } else {
                            return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument,
                                                              reader.position(), field_number);
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            if (f_double_ != 0.0) {
                if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::I64); !st) {
                    return st;
                }
                union {
                    ::protocyte::f64 value;
                    ::protocyte::u64 bits;
                } conv;
                conv.value = f_double_;
                if (const auto st = ::protocyte::write_fixed64(writer, conv.bits); !st) {
                    return st;
                }
            }
            if (f_float_ != 0.0f) {
                if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::I32); !st) {
                    return st;
                }
                union {
                    ::protocyte::f32 value;
                    ::protocyte::u32 bits;
                } conv;
                conv.value = f_float_;
                if (const auto st = ::protocyte::write_fixed32(writer, conv.bits); !st) {
                    return st;
                }
            }
            if (f_int32_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 4u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_int32_)); !st) {
                    return st;
                }
            }
            if (f_int64_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 8u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_int64_)); !st) {
                    return st;
                }
            }
            if (f_uint32_ != 0u) {
                if (const auto st = ::protocyte::write_tag(writer, 9u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_uint32_)); !st) {
                    return st;
                }
            }
            if (f_uint64_ != 0u) {
                if (const auto st = ::protocyte::write_tag(writer, 10u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_uint64_)); !st) {
                    return st;
                }
            }
            if (f_sint32_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 11u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, ::protocyte::encode_zigzag32(f_sint32_)); !st) {
                    return st;
                }
            }
            if (f_sint64_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 12u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, ::protocyte::encode_zigzag64(f_sint64_)); !st) {
                    return st;
                }
            }
            if (f_fixed32_ != 0u) {
                if (const auto st = ::protocyte::write_tag(writer, 13u, ::protocyte::WireType::I32); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed32(writer, static_cast<::protocyte::u32>(f_fixed32_));
                    !st) {
                    return st;
                }
            }
            if (f_fixed64_ != 0u) {
                if (const auto st = ::protocyte::write_tag(writer, 14u, ::protocyte::WireType::I64); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed64(writer, static_cast<::protocyte::u64>(f_fixed64_));
                    !st) {
                    return st;
                }
            }
            if (f_sfixed32_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 15u, ::protocyte::WireType::I32); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed32(writer, static_cast<::protocyte::u32>(f_sfixed32_));
                    !st) {
                    return st;
                }
            }
            if (f_sfixed64_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 16u, ::protocyte::WireType::I64); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_fixed64(writer, static_cast<::protocyte::u64>(f_sfixed64_));
                    !st) {
                    return st;
                }
            }
            if (f_bool_) {
                if (const auto st = ::protocyte::write_tag(writer, 17u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(f_bool_)); !st) {
                    return st;
                }
            }
            if (!f_string_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, 18u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, f_string_.view()); !st) {
                    return st;
                }
            }
            if (!f_bytes_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, 19u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, f_bytes_.view()); !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < r_int32_unpacked_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, 21u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(r_int32_unpacked_[i]));
                    !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, 22u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(r_int32_packed_[i]));
                    !st) {
                    return st;
                }
            }
            for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                if (const auto st = ::protocyte::write_tag(writer, 23u, ::protocyte::WireType::I64); !st) {
                    return st;
                }
                union {
                    ::protocyte::f64 value;
                    ::protocyte::u64 bits;
                } conv;
                conv.value = r_double_[i];
                if (const auto st = ::protocyte::write_fixed64(writer, conv.bits); !st) {
                    return st;
                }
            }
            if (color_ != 0) {
                if (const auto st = ::protocyte::write_tag(writer, 24u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(color_)); !st) {
                    return st;
                }
            }
            if (nested1_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, 25u, ::protocyte::WireType::LEN); !st) {
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
                if (const auto st = ::protocyte::write_tag(writer, 26u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, special_oneof.oneof_string.view()); !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                if (const auto st = ::protocyte::write_tag(writer, 27u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st =
                        ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(special_oneof.oneof_int32));
                    !st) {
                    return st;
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_msg) {
                if (const auto st = ::protocyte::write_tag(writer, 28u, ::protocyte::WireType::LEN); !st) {
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
                if (const auto st = ::protocyte::write_tag(writer, 29u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, special_oneof.oneof_bytes.view()); !st) {
                    return st;
                }
            }
            auto st_map_map_str_int32 = map_str_int32_.for_each([&](const auto &key,
                                                                    const auto &value) noexcept -> ::protocyte::Status {
                ::protocyte::usize entry_payload {};
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(1u) + ::protocyte::varint_size(key.size()) + key.size());
                        !st_size) {
                        return st_size;
                    }
                }
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(2u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(value)));
                        !st_size) {
                        return st_size;
                    }
                }
                if (const auto st = ::protocyte::write_tag(writer, 30u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::LEN); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_bytes(writer, key.view()); !st) {
                        return st;
                    }
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::VARINT); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(value)); !st) {
                        return st;
                    }
                }
                return ::protocyte::Status {};
            });
            if (!st_map_map_str_int32) {
                return st_map_map_str_int32;
            }
            auto st_map_map_int32_str = map_int32_str_.for_each([&](const auto &key,
                                                                    const auto &value) noexcept -> ::protocyte::Status {
                ::protocyte::usize entry_payload {};
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(1u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                        !st_size) {
                        return st_size;
                    }
                }
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(2u) + ::protocyte::varint_size(value.size()) + value.size());
                        !st_size) {
                        return st_size;
                    }
                }
                if (const auto st = ::protocyte::write_tag(writer, 31u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::VARINT); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key)); !st) {
                        return st;
                    }
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_bytes(writer, value.view()); !st) {
                        return st;
                    }
                }
                return ::protocyte::Status {};
            });
            if (!st_map_map_int32_str) {
                return st_map_map_int32_str;
            }
            auto st_map_map_bool_bytes =
                map_bool_bytes_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload, ::protocyte::tag_size(1u) +
                                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(2u) + ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    if (const auto st = ::protocyte::write_tag(writer, 32u, ::protocyte::WireType::LEN); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                        !st) {
                        return st;
                    }
                    {
                        if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::VARINT); !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key));
                            !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, value.view()); !st) {
                            return st;
                        }
                    }
                    return ::protocyte::Status {};
                });
            if (!st_map_map_bool_bytes) {
                return st_map_map_bool_bytes;
            }
            auto st_map_map_uint64_msg = map_uint64_msg_.for_each([&](const auto &key, const auto &value) noexcept
                                                                      -> ::protocyte::Status {
                ::protocyte::usize entry_payload {};
                {
                    if (const auto st_size = ::protocyte::add_size(
                            &entry_payload,
                            ::protocyte::tag_size(1u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
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
                            &entry_payload, ::protocyte::tag_size(2u) + ::protocyte::varint_size(nested_size.value()) +
                                                nested_size.value());
                        !st_size) {
                        return st_size;
                    }
                }
                if (const auto st = ::protocyte::write_tag(writer, 33u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                    !st) {
                    return st;
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::VARINT); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(key)); !st) {
                        return st;
                    }
                }
                {
                    if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
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
            if (!st_map_map_uint64_msg) {
                return st_map_map_uint64_msg;
            }
            auto st_map_very_nested_map =
                very_nested_map_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(1u) + ::protocyte::varint_size(key.size()) + key.size());
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
                                &entry_payload, ::protocyte::tag_size(2u) +
                                                    ::protocyte::varint_size(nested_size.value()) +
                                                    nested_size.value());
                            !st_size) {
                            return st_size;
                        }
                    }
                    if (const auto st = ::protocyte::write_tag(writer, 34u, ::protocyte::WireType::LEN); !st) {
                        return st;
                    }
                    if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload));
                        !st) {
                        return st;
                    }
                    {
                        if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::LEN); !st) {
                            return st;
                        }
                        if (const auto st = ::protocyte::write_bytes(writer, key.view()); !st) {
                            return st;
                        }
                    }
                    {
                        if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
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
            if (!st_map_very_nested_map) {
                return st_map_very_nested_map;
            }
            if (recursive_self_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, 35u, ::protocyte::WireType::LEN); !st) {
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
                if (const auto st = ::protocyte::write_tag(writer, 36u, ::protocyte::WireType::LEN); !st) {
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
                if (const auto st = ::protocyte::write_tag(writer, 37u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(colors_[i])); !st) {
                    return st;
                }
            }
            if (has_opt_int32_) {
                if (const auto st = ::protocyte::write_tag(writer, 38u, ::protocyte::WireType::VARINT); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(opt_int32_)); !st) {
                    return st;
                }
            }
            if (has_opt_string_) {
                if (const auto st = ::protocyte::write_tag(writer, 39u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, opt_string_.view()); !st) {
                    return st;
                }
            }
            if (extreme_nesting_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, 40u, ::protocyte::WireType::LEN); !st) {
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
            if (has_sha256_) {
                if (const auto st = ::protocyte::write_tag(writer, 41u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_varint(writer, 32u); !st) {
                    return st;
                }
                if (const auto st = writer.write(sha256_, 32u); !st) {
                    return st;
                }
            }
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (f_double_ != 0.0) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(1u) + 8u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_float_ != 0.0f) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(2u) + 4u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_int32_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(4u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_int64_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(8u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(f_int64_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_uint32_ != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(9u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_uint64_ != 0u) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(10u) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(f_uint64_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sint32_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(11u) + ::protocyte::varint_size(::protocyte::encode_zigzag32(f_sint32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sint64_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(12u) + ::protocyte::varint_size(::protocyte::encode_zigzag64(f_sint64_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_fixed32_ != 0u) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(13u) + 4u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_fixed64_ != 0u) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(14u) + 8u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sfixed32_ != 0) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(15u) + 4u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_sfixed64_ != 0) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(16u) + 8u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (f_bool_) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(17u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(f_bool_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!f_string_.empty()) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(18u) +
                                                                      ::protocyte::varint_size(f_string_.size()) +
                                                                      f_string_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (!f_bytes_.empty()) {
                if (const auto st =
                        ::protocyte::add_size(&total, ::protocyte::tag_size(19u) +
                                                          ::protocyte::varint_size(f_bytes_.size()) + f_bytes_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < r_int32_unpacked_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(21u) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_unpacked_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < r_int32_packed_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(22u) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(r_int32_packed_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < r_double_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(23u) + 8u); !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (color_ != 0) {
                if (const auto st = ::protocyte::add_size(
                        &total,
                        ::protocyte::tag_size(24u) + ::protocyte::varint_size(static_cast<::protocyte::u64>(color_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (nested1_.has_value()) {
                auto nested_size = nested1_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(25u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_string) {
                if (const auto st =
                        ::protocyte::add_size(&total, ::protocyte::tag_size(26u) +
                                                          ::protocyte::varint_size(special_oneof.oneof_string.size()) +
                                                          special_oneof.oneof_string.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_int32) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(27u) +
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
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(28u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (special_oneof_case_ == Special_oneofCase::oneof_bytes) {
                if (const auto st =
                        ::protocyte::add_size(&total, ::protocyte::tag_size(29u) +
                                                          ::protocyte::varint_size(special_oneof.oneof_bytes.size()) +
                                                          special_oneof.oneof_bytes.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            auto st_map_size_map_str_int32 =
                map_str_int32_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(1u) + ::protocyte::varint_size(key.size()) + key.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload, ::protocyte::tag_size(2u) +
                                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(value)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    return ::protocyte::add_size(&total, ::protocyte::tag_size(30u) +
                                                             ::protocyte::varint_size(entry_payload) + entry_payload);
                });
            if (!st_map_size_map_str_int32) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_str_int32.error());
            }
            auto st_map_size_map_int32_str =
                map_int32_str_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload, ::protocyte::tag_size(1u) +
                                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(2u) + ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    return ::protocyte::add_size(&total, ::protocyte::tag_size(31u) +
                                                             ::protocyte::varint_size(entry_payload) + entry_payload);
                });
            if (!st_map_size_map_int32_str) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_int32_str.error());
            }
            auto st_map_size_map_bool_bytes =
                map_bool_bytes_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload, ::protocyte::tag_size(1u) +
                                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(key)));
                            !st_size) {
                            return st_size;
                        }
                    }
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(2u) + ::protocyte::varint_size(value.size()) + value.size());
                            !st_size) {
                            return st_size;
                        }
                    }
                    return ::protocyte::add_size(&total, ::protocyte::tag_size(32u) +
                                                             ::protocyte::varint_size(entry_payload) + entry_payload);
                });
            if (!st_map_size_map_bool_bytes) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_bool_bytes.error());
            }
            auto st_map_size_map_uint64_msg =
                map_uint64_msg_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload, ::protocyte::tag_size(1u) +
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
                                &entry_payload, ::protocyte::tag_size(2u) +
                                                    ::protocyte::varint_size(nested_size.value()) +
                                                    nested_size.value());
                            !st_size) {
                            return st_size;
                        }
                    }
                    return ::protocyte::add_size(&total, ::protocyte::tag_size(33u) +
                                                             ::protocyte::varint_size(entry_payload) + entry_payload);
                });
            if (!st_map_size_map_uint64_msg) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_map_uint64_msg.error());
            }
            auto st_map_size_very_nested_map =
                very_nested_map_.for_each([&](const auto &key, const auto &value) noexcept -> ::protocyte::Status {
                    ::protocyte::usize entry_payload {};
                    {
                        if (const auto st_size = ::protocyte::add_size(
                                &entry_payload,
                                ::protocyte::tag_size(1u) + ::protocyte::varint_size(key.size()) + key.size());
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
                                &entry_payload, ::protocyte::tag_size(2u) +
                                                    ::protocyte::varint_size(nested_size.value()) +
                                                    nested_size.value());
                            !st_size) {
                            return st_size;
                        }
                    }
                    return ::protocyte::add_size(&total, ::protocyte::tag_size(34u) +
                                                             ::protocyte::varint_size(entry_payload) + entry_payload);
                });
            if (!st_map_size_very_nested_map) {
                return ::protocyte::Result<::protocyte::usize>::err(st_map_size_very_nested_map.error());
            }
            if (recursive_self_.has_value()) {
                auto nested_size = recursive_self_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(35u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < lots_of_nested_.size(); ++i) {
                auto nested_size = lots_of_nested_[i].encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(36u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            for (::protocyte::usize i {}; i < colors_.size(); ++i) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(37u) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(colors_[i])));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (has_opt_int32_) {
                if (const auto st = ::protocyte::add_size(
                        &total, ::protocyte::tag_size(38u) +
                                    ::protocyte::varint_size(static_cast<::protocyte::u64>(opt_int32_)));
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (has_opt_string_) {
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(39u) +
                                                                      ::protocyte::varint_size(opt_string_.size()) +
                                                                      opt_string_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (extreme_nesting_.has_value()) {
                auto nested_size = extreme_nesting_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(40u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (has_sha256_) {
                if (const auto st =
                        ::protocyte::add_size(&total, ::protocyte::tag_size(41u) + ::protocyte::varint_size(32u) + 32u);
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
        ::protocyte::f64 f_double_ = 0.0;
        ::protocyte::f32 f_float_ = 0.0f;
        ::protocyte::i32 f_int32_ = 0;
        ::protocyte::i64 f_int64_ = 0;
        ::protocyte::u32 f_uint32_ = 0u;
        ::protocyte::u64 f_uint64_ = 0u;
        ::protocyte::i32 f_sint32_ = 0;
        ::protocyte::i64 f_sint64_ = 0;
        ::protocyte::u32 f_fixed32_ = 0u;
        ::protocyte::u64 f_fixed64_ = 0u;
        ::protocyte::i32 f_sfixed32_ = 0;
        ::protocyte::i64 f_sfixed64_ = 0;
        bool f_bool_ = false;
        typename Config::String f_string_;
        typename Config::Bytes f_bytes_;
        typename Config::template Vector<::protocyte::i32> r_int32_unpacked_;
        typename Config::template Vector<::protocyte::i32> r_int32_packed_;
        typename Config::template Vector<::protocyte::f64> r_double_;
        ::protocyte::i32 color_ = 0;
        typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> nested1_;
        Special_oneofCase special_oneof_case_ = Special_oneofCase::none;
        union Special_oneofStorage {
            Special_oneofStorage() noexcept {}
            ~Special_oneofStorage() noexcept {}
            typename Config::String oneof_string;
            ::protocyte::i32 oneof_int32;
            typename Config::template Optional<::test::ultimate::UltimateComplexMessage_NestedLevel1<Config>> oneof_msg;
            typename Config::Bytes oneof_bytes;
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
        ::protocyte::i32 opt_int32_ = 0;
        bool has_opt_int32_ = false;
        typename Config::String opt_string_;
        bool has_opt_string_ = false;
        ::protocyte::u8 sha256_[32u];
        bool has_sha256_ = false;
        typename Config::template Optional<
            ::test::ultimate::UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD_LevelE<Config>>
            extreme_nesting_;
    };

    template<class Config> struct UltimateComplexMessage_LevelA {
        using Context = typename Config::Context;
        template<class NestedConfig = Config> using LevelB = UltimateComplexMessage_LevelA_LevelB<NestedConfig>;

        explicit UltimateComplexMessage_LevelA(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<UltimateComplexMessage_LevelA> create(Context &ctx) noexcept {
            return ::protocyte::Result<UltimateComplexMessage_LevelA>::ok(UltimateComplexMessage_LevelA {ctx});
        }
        UltimateComplexMessage_LevelA(UltimateComplexMessage_LevelA &&) noexcept = default;
        UltimateComplexMessage_LevelA &operator=(UltimateComplexMessage_LevelA &&) noexcept = default;
        UltimateComplexMessage_LevelA(const UltimateComplexMessage_LevelA &) = delete;
        UltimateComplexMessage_LevelA &operator=(const UltimateComplexMessage_LevelA &) = delete;

        ::protocyte::Status copy_from(const UltimateComplexMessage_LevelA &other) noexcept {
            (void) other;
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

        template<class Reader>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
    };

    template<class Config> struct UltimateComplexMessage_LevelA_LevelB {
        using Context = typename Config::Context;
        template<class NestedConfig = Config> using LevelC = UltimateComplexMessage_LevelA_LevelB_LevelC<NestedConfig>;

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
            (void) other;
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

        template<class Reader>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
    };

    template<class Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC {
        using Context = typename Config::Context;
        template<class NestedConfig = Config> using LevelD =
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
            (void) other;
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

        template<class Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
    };

    template<class Config> struct UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD {
        using Context = typename Config::Context;
        template<class NestedConfig = Config> using LevelE =
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
            (void) other;
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

        template<class Reader> static ::protocyte::Result<UltimateComplexMessage_LevelA_LevelB_LevelC_LevelD>
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

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            return ::protocyte::Status::ok();
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            return ::protocyte::Result<::protocyte::usize>::ok(total);
        }
    protected:
        Context *ctx_;
    };

    template<class Config> struct ExtraMessage {
        using Context = typename Config::Context;
        explicit ExtraMessage(Context &ctx) noexcept: ctx_ {&ctx}, tag_ {&ctx} {}

        static ::protocyte::Result<ExtraMessage> create(Context &ctx) noexcept {
            return ::protocyte::Result<ExtraMessage>::ok(ExtraMessage {ctx});
        }
        ExtraMessage(ExtraMessage &&) noexcept = default;
        ExtraMessage &operator=(ExtraMessage &&) noexcept = default;
        ExtraMessage(const ExtraMessage &) = delete;
        ExtraMessage &operator=(const ExtraMessage &) = delete;

        ::protocyte::Status copy_from(const ExtraMessage &other) noexcept {
            (void) other;
            auto st_tag = set_tag(other.tag());
            if (!st_tag) {
                return st_tag;
            }
            if (other.has_ref()) {
                auto ensured = ensure_ref();
                if (!ensured) {
                    return ensured.status();
                }
                if (const auto st = ensured.value().get().copy_from(*other.ref()); !st) {
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

        template<class Reader> static ::protocyte::Result<ExtraMessage> parse(Context &ctx, Reader &reader) noexcept {
            auto out = ExtraMessage::create(ctx);
            if (!out) {
                return out;
            }
            if (const auto st = out.value().merge_from(reader); !st) {
                return ::protocyte::Result<ExtraMessage>::err(st.error());
            }
            return out;
        }

        template<class Reader> auto merge_from(Reader &reader) noexcept -> ::protocyte::Status {
            while (!reader.eof()) {
                auto tag = ::protocyte::read_varint(reader);
                if (!tag) {
                    return tag.status();
                }
                const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);
                const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);
                switch (field_number) {
                    case 1u: {
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
                    case 2u: {
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

        template<class Writer> auto serialize(Writer &writer) const noexcept -> ::protocyte::Status {
            if (!tag_.empty()) {
                if (const auto st = ::protocyte::write_tag(writer, 1u, ::protocyte::WireType::LEN); !st) {
                    return st;
                }
                if (const auto st = ::protocyte::write_bytes(writer, tag_.view()); !st) {
                    return st;
                }
            }
            if (ref_.has_value()) {
                if (const auto st = ::protocyte::write_tag(writer, 2u, ::protocyte::WireType::LEN); !st) {
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
                        &total, ::protocyte::tag_size(1u) + ::protocyte::varint_size(tag_.size()) + tag_.size());
                    !st) {
                    return ::protocyte::Result<::protocyte::usize>::err(st.error());
                }
            }
            if (ref_.has_value()) {
                auto nested_size = ref_.value().encoded_size();
                if (!nested_size) {
                    return ::protocyte::Result<::protocyte::usize>::err(nested_size.error());
                }
                if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size(2u) +
                                                                      ::protocyte::varint_size(nested_size.value()) +
                                                                      nested_size.value());
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


} // namespace test::ultimate

#endif // PROTOCYTE_GENERATED_EXAMPLE_PROTO_HPP
