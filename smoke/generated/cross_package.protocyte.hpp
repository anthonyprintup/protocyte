#pragma once

#ifndef PROTOCYTE_GENERATED_CROSS_PACKAGE_PROTO_1F7F3252503C_HPP
#define PROTOCYTE_GENERATED_CROSS_PACKAGE_PROTO_1F7F3252503C_HPP

#include <protocyte/runtime/runtime.hpp>

#include <string_view>

namespace test::crosspkg {

    inline constexpr ::protocyte::u32 FOREIGN_BASE {7u};
    inline constexpr ::std::string_view FOREIGN_LABEL {"proto-xpkg", 10u};

    template<typename Config = ::protocyte::DefaultConfig> struct CrossPackageConstants_Nested;
    template<typename Config = ::protocyte::DefaultConfig> struct CrossPackageConstants;

    template<typename Config> struct CrossPackageConstants_Nested {
        using Context = typename Config::Context;
        static constexpr ::protocyte::u32 MIRRORED_COUNT {15u};

        enum struct FieldNumber : ::protocyte::u32 {
            nested_bytes = 1u,
        };

        explicit CrossPackageConstants_Nested(Context &ctx) noexcept: ctx_ {&ctx} {}

        static ::protocyte::Result<CrossPackageConstants_Nested> create(Context &ctx) noexcept {
            return CrossPackageConstants_Nested {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        CrossPackageConstants_Nested(CrossPackageConstants_Nested &&) noexcept = default;
        CrossPackageConstants_Nested &operator=(CrossPackageConstants_Nested &&) noexcept = default;
        CrossPackageConstants_Nested(const CrossPackageConstants_Nested &) = delete;
        CrossPackageConstants_Nested &operator=(const CrossPackageConstants_Nested &) = delete;

        ::protocyte::Status copy_from(const CrossPackageConstants_Nested &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_nested_bytes(other.nested_bytes()); !st) {
                return st;
            }
            return {};
        }

        ::protocyte::Result<CrossPackageConstants_Nested> clone() const noexcept {
            auto out = CrossPackageConstants_Nested::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::ByteView nested_bytes() const noexcept { return nested_bytes_.view(); }
        ::protocyte::usize nested_bytes_size() const noexcept { return nested_bytes_.size(); }
        static constexpr ::protocyte::usize nested_bytes_max_size() noexcept { return 15u; }
        ::protocyte::Status resize_nested_bytes(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = nested_bytes_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::MutableByteView mutable_nested_bytes() noexcept { return nested_bytes_.mutable_view(); }
        template<class Value>::protocyte::Status set_nested_bytes(const Value &value) noexcept
            requires(::protocyte::ByteViewRange<Value>)
        {
            const auto view = ::protocyte::byte_view_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = nested_bytes_.assign(*view); !st) {
                return st;
            }
            return {};
        }
        void clear_nested_bytes() noexcept { nested_bytes_.clear(); }

        template<typename Reader>
        static ::protocyte::Result<CrossPackageConstants_Nested> parse(Context &ctx, Reader &reader) noexcept {
            auto out = CrossPackageConstants_Nested::create(ctx);
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
                        if (*len > 15u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = nested_bytes_.resize(*len); !st) {
                            return st;
                        }
                        if (const auto st = reader.read(nested_bytes_.data(), nested_bytes_.size()); !st) {
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
        ::protocyte::ByteArray<15u> nested_bytes_;
    };

    template<typename Config> struct CrossPackageConstants {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using Nested = CrossPackageConstants_Nested<NestedConfig>;

        static constexpr ::protocyte::u32 REMOTE_COUNT {16u};
        static constexpr ::std::string_view REMOTE_LABEL {"proto-demo-external", 19u};
        static constexpr bool REMOTE_READY {true};
        static constexpr ::protocyte::u32 NESTED_COUNT {9u};

        enum struct FieldNumber : ::protocyte::u32 {
            remote_bytes = 1u,
            remote_values = 2u,
            nested = 3u,
        };

        explicit CrossPackageConstants(Context &ctx) noexcept: ctx_ {&ctx}, remote_values_ {&ctx} {}

        static ::protocyte::Result<CrossPackageConstants> create(Context &ctx) noexcept {
            return CrossPackageConstants {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        CrossPackageConstants(CrossPackageConstants &&) noexcept = default;
        CrossPackageConstants &operator=(CrossPackageConstants &&) noexcept = default;
        CrossPackageConstants(const CrossPackageConstants &) = delete;
        CrossPackageConstants &operator=(const CrossPackageConstants &) = delete;

        ::protocyte::Status copy_from(const CrossPackageConstants &other) noexcept {
            if (this == &other) {
                return {};
            }
            if (const auto st = set_remote_bytes(other.remote_bytes()); !st) {
                return st;
            }
            if (const auto st = mutable_remote_values().copy_from(other.remote_values()); !st) {
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

        ::protocyte::Result<CrossPackageConstants> clone() const noexcept {
            auto out = CrossPackageConstants::create(*ctx_);
            if (!out) {
                return out;
            }
            if (const auto st = out->copy_from(*this); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return out;
        }

        ::protocyte::ByteView remote_bytes() const noexcept { return remote_bytes_.view(); }
        ::protocyte::usize remote_bytes_size() const noexcept { return remote_bytes_.size(); }
        static constexpr ::protocyte::usize remote_bytes_max_size() noexcept { return 9u; }
        ::protocyte::Status resize_remote_bytes(const ::protocyte::usize size) noexcept {
            if (size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
            }
            if (const auto st = remote_bytes_.resize(size); !st) {
                return st;
            }
            return {};
        }
        ::protocyte::MutableByteView mutable_remote_bytes() noexcept { return remote_bytes_.mutable_view(); }
        template<class Value>::protocyte::Status set_remote_bytes(const Value &value) noexcept
            requires(::protocyte::ByteViewRange<Value>)
        {
            const auto view = ::protocyte::byte_view_of(value);
            if (!view) {
                return view.status();
            }
            if (view->size > ctx_->limits.max_string_bytes) {
                return ::protocyte::unexpected(::protocyte::ErrorCode::size_limit, {});
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
        ::protocyte::Result<::protocyte::Ref<::test::crosspkg::CrossPackageConstants_Nested<Config>>>
        ensure_nested() noexcept {
            if (nested_.has_value()) {
                return ::protocyte::Ref<::test::crosspkg::CrossPackageConstants_Nested<Config>> {*nested_};
            }
            return nested_.emplace(*ctx_).transform(
                [this]() noexcept -> ::protocyte::Ref<::test::crosspkg::CrossPackageConstants_Nested<Config>> {
                    return ::protocyte::Ref<::test::crosspkg::CrossPackageConstants_Nested<Config>> {*nested_};
                });
        }
        void clear_nested() noexcept { nested_.reset(); }

        template<typename Reader>
        static ::protocyte::Result<CrossPackageConstants> parse(Context &ctx, Reader &reader) noexcept {
            auto out = CrossPackageConstants::create(ctx);
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
                    case FieldNumber::remote_bytes: {
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
                        if (*len > 9u) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::count_limit, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = remote_bytes_.resize(*len); !st) {
                            return st;
                        }
                        if (const auto st = reader.read(remote_bytes_.data(), remote_bytes_.size()); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::remote_values: {
                        if (wire_type == ::protocyte::WireType::LEN) {
                            auto len = ::protocyte::read_length_delimited_size(reader);
                            if (!len) {
                                return len.status();
                            }
                            ::protocyte::LimitedReader<Reader> packed {reader, *len};
                            while (!packed.eof()) {
                                ::protocyte::i32 value {};
                                if (const auto st = ::protocyte::read_int32(packed).transform(
                                        [&](const auto decoded) noexcept { value = decoded; });
                                    !st) {
                                    return st;
                                }
                                if (const auto st = remote_values_.push_back(value); !st) {
                                    return st;
                                }
                            }
                            if (const auto finish = packed.finish(); !finish) {
                                return finish;
                            }
                            break;
                        }
                        ::protocyte::i32 value {};
                        if (const auto st = ::protocyte::read_int32_field(reader, wire_type, field_number)
                                                .transform([&](const auto decoded) noexcept { value = decoded; });
                            !st) {
                            return st;
                        }
                        if (const auto st = remote_values_.push_back(value); !st) {
                            return st;
                        }
                        break;
                    }
                    case FieldNumber::nested: {
                        if (wire_type != ::protocyte::WireType::LEN) {
                            return ::protocyte::unexpected(::protocyte::ErrorCode::invalid_wire_type, reader.position(),
                                                           field_number);
                        }
                        if (const auto st = ensure_nested().and_then([&](auto ensured) noexcept -> ::protocyte::Status {
                                return ::protocyte::read_message<Config>(*ctx_, reader, field_number, *ensured);
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
            return {};
        }

        ::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {
            ::protocyte::usize total {};
            if (!remote_bytes_.empty()) {
                const auto st_size = ::protocyte::length_delimited_field_size(
                                         static_cast<::protocyte::u32>(FieldNumber::remote_bytes), remote_bytes_.size())
                                         .and_then([&](const ::protocyte::usize field_size) noexcept
                                                       -> ::protocyte::Result<::protocyte::usize> {
                                             return ::protocyte::add_size(total, field_size);
                                         });
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
                const auto st_size =
                    ::protocyte::length_delimited_field_size(static_cast<::protocyte::u32>(FieldNumber::remote_values),
                                                             packed_size_remote_values)
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
        ::protocyte::ByteArray<9u> remote_bytes_;
        ::protocyte::Array<::protocyte::i32, 9u> remote_values_;
        typename Config::template Optional<::test::crosspkg::CrossPackageConstants_Nested<Config>> nested_;
    };

} // namespace test::crosspkg

#endif // PROTOCYTE_GENERATED_CROSS_PACKAGE_PROTO_1F7F3252503C_HPP
