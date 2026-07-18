#pragma once

#ifndef PROTOCYTE_GENERATED_RESERVED_IDENTIFIERS_PROTO_1427A5F03FB8_HPP
#define PROTOCYTE_GENERATED_RESERVED_IDENTIFIERS_PROTO_1427A5F03FB8_HPP

#include <protocyte/runtime/runtime.hpp>

namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f {

    enum struct Protocyte_escaped_5f5f46494c455f5f : ::protocyte::i32 {
        protocyte_escaped_5f5570706572 = 0,
        protocyte_escaped_76616c75655f5f676170 = 1,
    };

    enum struct Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_5f4e6573746564456e756d : ::protocyte::i32 {
        protocyte_escaped_5f5f535444435f5f = 0,
        enum_trailing_ = 1,
    };

    enum struct Class_KeywordValues : ::protocyte::i32 {
        class_ = 0,
    };

    inline constexpr ::protocyte::i32 protocyte_escaped_5f5f444154455f5f {7};
    inline constexpr ::protocyte::i32 class_ {8};

    template<typename Config = ::protocyte::DefaultConfig>
    struct Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765;
    template<typename Config = ::protocyte::DefaultConfig> struct Protocyte_escaped_5f5f4c494e455f5f;
    template<typename Config = ::protocyte::DefaultConfig> struct Class_Struct_;
    template<typename Config = ::protocyte::DefaultConfig> struct Class_;

    template<typename Config>
    struct Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            protocyte_escaped_5f496e6e6572 = 1u,
        };

        explicit Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765(
            Context &ctx) noexcept:
            ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765
        create(Context &ctx) noexcept {
            return Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765(
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &&) noexcept = default;
        Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &operator=(
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &&) noexcept = default;
        Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765(
            const Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &) = delete;
        Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &
        operator=(const Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &) = delete;

        ::protocyte::Status
        copy_from(const Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765
                      &source) noexcept {
            if (this == &source) {
                return {};
            }
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status
        copy_from(const Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &source,
                  Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765
                      &staging_message) noexcept {
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

        ::protocyte::Result<Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765>
        clone() const noexcept {
            auto output =
                Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765
                                      &output) const noexcept {
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
        static void
        reset_for_reuse_(Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &value,
                         Context &ctx) noexcept {
            value.~Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765();
            new (&value) Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 {ctx};
        }

        ::protocyte::Status
        copy_from_in_place_(const Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765
                                &source) noexcept {
            set_protocyte_escaped_5f496e6e6572(source.protocyte_escaped_5f496e6e6572());
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

        constexpr ::protocyte::i32 protocyte_escaped_5f496e6e6572() const noexcept {
            return protocyte_escaped_5f496e6e6572_;
        }
        void set_protocyte_escaped_5f496e6e6572(const ::protocyte::i32 value) noexcept {
            protocyte_escaped_5f496e6e6572_ = value;
        }
        constexpr void clear_protocyte_escaped_5f496e6e6572() noexcept { protocyte_escaped_5f496e6e6572_ = {}; }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765>
        parse(Context &ctx, Reader &reader) noexcept {
            auto output =
                Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            ::protocyte::SliceReader reader {input.data(), input.size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader> static ::protocyte::Status
        parse(Reader &reader,
              Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765 &output) noexcept {
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
                case FieldNumber::protocyte_escaped_5f496e6e6572: {
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
                    const auto decoded_protocyte_escaped_5f496e6e6572 =
                        ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_protocyte_escaped_5f496e6e6572) {
                        return decoded_protocyte_escaped_5f496e6e6572.status();
                    }
                    protocyte_escaped_5f496e6e6572_ = *decoded_protocyte_escaped_5f496e6e6572;
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
            if (protocyte_escaped_5f496e6e6572_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f496e6e6572),
                        protocyte_escaped_5f496e6e6572_);
                    !st) {
                    return ::protocyte::with_field(
                        st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f496e6e6572));
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
            if (protocyte_escaped_5f496e6e6572_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total,
                    ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f496e6e6572)) +
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(protocyte_escaped_5f496e6e6572_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f496e6e6572)));
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
        ::protocyte::i32 protocyte_escaped_5f496e6e6572_ {};
    };

    template<typename Config> struct Protocyte_escaped_5f5f4c494e455f5f {
        using Context = typename Config::Context;
        using protocyte_escaped_5f4e6573746564456e756d =
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_5f4e6573746564456e756d;
        template<typename NestedConfig = Config> using protocyte_escaped_4e65737465645f5f4d657373616765 =
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765<NestedConfig>;

        static constexpr ::protocyte::i32 protocyte_escaped_5f5f54494d455f5f {9};

        enum struct Protocyte_escaped_5f43686f696365Case : ::protocyte::u32 {
            none = 0u,
            protocyte_escaped_5f5f46494c455f5f = 1u,
            protocyte_escaped_76616c75655f5f676170 = 2u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            protocyte_escaped_5f5f46494c455f5f = 1u,
            protocyte_escaped_76616c75655f5f676170 = 2u,
            protocyte_escaped_5f5570706572 = 3u,
            trailing_protocyte = 4u,
            protocyte_escaped_656e756d5f5f76616c7565 = 5u,
            class_protocyte = 6u,
            protocyte_escaped_5f = 7u,
        };

        explicit Protocyte_escaped_5f5f4c494e455f5f(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Protocyte_escaped_5f5f4c494e455f5f create(Context &ctx) noexcept {
            return Protocyte_escaped_5f5f4c494e455f5f {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        Protocyte_escaped_5f5f4c494e455f5f(Protocyte_escaped_5f5f4c494e455f5f &&other) noexcept:
            ctx_ {other.ctx_},
            unknown_fields_ {::protocyte::move(other.unknown_fields_)},
            protocyte_escaped_5f5570706572_ {other.protocyte_escaped_5f5570706572_},
            trailing_protocyte_ {other.trailing_protocyte_},
            protocyte_escaped_656e756d5f5f76616c7565_ {other.protocyte_escaped_656e756d5f5f76616c7565_},
            class_protocyte_ {::protocyte::move(other.class_protocyte_)},
            protocyte_escaped_5f_ {other.protocyte_escaped_5f_} {
            switch (other.protocyte_escaped_5f43686f696365_case_) {
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f: {
                    new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)
                        typename Config::String {::protocyte::move(
                            other.protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)};
                    protocyte_escaped_5f43686f696365_case_ =
                        Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f;
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170: {
                    new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_)::protocyte::i32 {
                        other.protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_};
                    protocyte_escaped_5f43686f696365_case_ =
                        Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170;
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::none:
                default: {
                    break;
                }
            }
            other.clear_protocyte_escaped_5f43686f696365();
        }
        Protocyte_escaped_5f5f4c494e455f5f &operator=(Protocyte_escaped_5f5f4c494e455f5f &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_protocyte_escaped_5f43686f696365();
            ctx_ = other.ctx_;
            unknown_fields_ = ::protocyte::move(other.unknown_fields_);
            protocyte_escaped_5f5570706572_ = other.protocyte_escaped_5f5570706572_;
            trailing_protocyte_ = other.trailing_protocyte_;
            protocyte_escaped_656e756d5f5f76616c7565_ = other.protocyte_escaped_656e756d5f5f76616c7565_;
            class_protocyte_ = ::protocyte::move(other.class_protocyte_);
            protocyte_escaped_5f_ = other.protocyte_escaped_5f_;
            switch (other.protocyte_escaped_5f43686f696365_case_) {
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f: {
                    new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)
                        typename Config::String {::protocyte::move(
                            other.protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)};
                    protocyte_escaped_5f43686f696365_case_ =
                        Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f;
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170: {
                    new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_)::protocyte::i32 {
                        other.protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_};
                    protocyte_escaped_5f43686f696365_case_ =
                        Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170;
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::none:
                default: {
                    break;
                }
            }
            other.clear_protocyte_escaped_5f43686f696365();
            return *this;
        }
        ~Protocyte_escaped_5f5f4c494e455f5f() noexcept { clear_protocyte_escaped_5f43686f696365(); }
        Protocyte_escaped_5f5f4c494e455f5f(const Protocyte_escaped_5f5f4c494e455f5f &) = delete;
        Protocyte_escaped_5f5f4c494e455f5f &operator=(const Protocyte_escaped_5f5f4c494e455f5f &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const Protocyte_escaped_5f5f4c494e455f5f &source) noexcept {
            if (this == &source) {
                return {};
            }
            Protocyte_escaped_5f5f4c494e455f5f staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Protocyte_escaped_5f5f4c494e455f5f &source,
                                      Protocyte_escaped_5f5f4c494e455f5f &staging_message) noexcept {
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

        ::protocyte::Result<Protocyte_escaped_5f5f4c494e455f5f> clone() const noexcept {
            auto output = Protocyte_escaped_5f5f4c494e455f5f::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Protocyte_escaped_5f5f4c494e455f5f &output) const noexcept {
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
        static void reset_for_reuse_(Protocyte_escaped_5f5f4c494e455f5f &value, Context &ctx) noexcept {
            value.~Protocyte_escaped_5f5f4c494e455f5f();
            new (&value) Protocyte_escaped_5f5f4c494e455f5f {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Protocyte_escaped_5f5f4c494e455f5f &source) noexcept {
            set_protocyte_escaped_5f5570706572(source.protocyte_escaped_5f5570706572());
            set_trailing_protocyte(source.trailing_protocyte());
            if (const auto st = set_protocyte_escaped_656e756d5f5f76616c7565_raw(
                    source.protocyte_escaped_656e756d5f5f76616c7565_raw());
                !st) {
                return st;
            }
            if (source.has_class_protocyte()) {
                const auto ensured_class_protocyte = ensure_class_protocyte();
                if (!ensured_class_protocyte) {
                    return ::protocyte::with_field(ensured_class_protocyte.status(),
                                                   static_cast<::protocyte::u32>(FieldNumber::class_protocyte));
                }
                if (const auto st = ensured_class_protocyte->copy_from(*source.class_protocyte()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::class_protocyte));
                }
            } else {
                clear_class_protocyte();
            }
            set_protocyte_escaped_5f(source.protocyte_escaped_5f());
            switch (source.protocyte_escaped_5f43686f696365_case_) {
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f: {
                    if (const auto st =
                            set_protocyte_escaped_5f5f46494c455f5f(source.protocyte_escaped_5f5f46494c455f5f());
                        !st) {
                        return st;
                    }
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170: {
                    set_protocyte_escaped_76616c75655f5f676170(source.protocyte_escaped_76616c75655f5f676170());
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::none:
                default: {
                    clear_protocyte_escaped_5f43686f696365();
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

        constexpr Protocyte_escaped_5f43686f696365Case protocyte_escaped_5f43686f696365_case() const noexcept {
            return protocyte_escaped_5f43686f696365_case_;
        }
        void clear_protocyte_escaped_5f43686f696365() noexcept {
            switch (protocyte_escaped_5f43686f696365_case_) {
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f: {
                    destroy_at_(&protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_);
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170: {
                    break;
                }
                case Protocyte_escaped_5f43686f696365Case::none:
                default: {
                    break;
                }
            }
            protocyte_escaped_5f43686f696365_case_ = Protocyte_escaped_5f43686f696365Case::none;
        }

        constexpr bool has_protocyte_escaped_5f5f46494c455f5f() const noexcept {
            return protocyte_escaped_5f43686f696365_case_ ==
                   Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f;
        }
        ::protocyte::StringView protocyte_escaped_5f5f46494c455f5f() const noexcept {
            return has_protocyte_escaped_5f5f46494c455f5f() ?
                       protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_.view() :
                       ::protocyte::StringView {};
        }
        template<class Value>::protocyte::Status set_protocyte_escaped_5f5f46494c455f5f(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(
                    view.status(), static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(
                    st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f));
            }
            clear_protocyte_escaped_5f43686f696365();
            new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)
                typename Config::String {::protocyte::move(temp)};
            protocyte_escaped_5f43686f696365_case_ =
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f;
            return {};
        }
        template<class Value>::protocyte::Status set_protocyte_escaped_5f5f46494c455f5f(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(
                    view.status(), static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f));
            }
            typename Config::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(
                    st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f));
            }
            clear_protocyte_escaped_5f43686f696365();
            new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)
                typename Config::String {::protocyte::move(temp)};
            protocyte_escaped_5f43686f696365_case_ =
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f;
            return {};
        }

        constexpr bool has_protocyte_escaped_76616c75655f5f676170() const noexcept {
            return protocyte_escaped_5f43686f696365_case_ ==
                   Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170;
        }
        constexpr ::protocyte::i32 protocyte_escaped_76616c75655f5f676170() const noexcept {
            return has_protocyte_escaped_76616c75655f5f676170() ?
                       protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_ :
                       0;
        }
        void set_protocyte_escaped_76616c75655f5f676170(const ::protocyte::i32 value) noexcept {
            clear_protocyte_escaped_5f43686f696365();
            new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_)::protocyte::i32 {value};
            protocyte_escaped_5f43686f696365_case_ =
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170;
        }

        constexpr ::protocyte::i32 protocyte_escaped_5f5570706572() const noexcept {
            return protocyte_escaped_5f5570706572_;
        }
        void set_protocyte_escaped_5f5570706572(const ::protocyte::i32 value) noexcept {
            protocyte_escaped_5f5570706572_ = value;
        }
        constexpr void clear_protocyte_escaped_5f5570706572() noexcept { protocyte_escaped_5f5570706572_ = {}; }

        constexpr ::protocyte::i32 trailing_protocyte() const noexcept { return trailing_protocyte_; }
        void set_trailing_protocyte(const ::protocyte::i32 value) noexcept { trailing_protocyte_ = value; }
        constexpr void clear_trailing_protocyte() noexcept { trailing_protocyte_ = {}; }

        constexpr ::protocyte::i32 protocyte_escaped_656e756d5f5f76616c7565_raw() const noexcept {
            return protocyte_escaped_656e756d5f5f76616c7565_;
        }
        constexpr ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
            Protocyte_escaped_5f5f46494c455f5f
            protocyte_escaped_656e756d5f5f76616c7565() const noexcept {
            return static_cast<::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                                   Protocyte_escaped_5f5f46494c455f5f>(protocyte_escaped_656e756d5f5f76616c7565_);
        }
        ::protocyte::Status set_protocyte_escaped_656e756d5f5f76616c7565_raw(const ::protocyte::i32 value) noexcept {
            protocyte_escaped_656e756d5f5f76616c7565_ = value;
            return {};
        }
        ::protocyte::Status set_protocyte_escaped_656e756d5f5f76616c7565(
            const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                Protocyte_escaped_5f5f46494c455f5f value) noexcept {
            return set_protocyte_escaped_656e756d5f5f76616c7565_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_protocyte_escaped_656e756d5f5f76616c7565() noexcept {
            protocyte_escaped_656e756d5f5f76616c7565_ = {};
        }

        bool has_class_protocyte() const noexcept { return class_protocyte_.has_value(); }
        const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
            Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765<Config> *
            class_protocyte() const noexcept {
            return has_class_protocyte() ? class_protocyte_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765<Config> &>
        ensure_class_protocyte() noexcept {
            if (class_protocyte_.has_value()) {
                return *class_protocyte_;
            }
            if (const auto st = class_protocyte_.emplace(*ctx_); !st) {
                return ::protocyte::unexpected(
                    ::protocyte::with_field(st.error(), static_cast<::protocyte::u32>(FieldNumber::class_protocyte)));
            }
            return *class_protocyte_;
        }
        void clear_class_protocyte() noexcept { class_protocyte_.reset(); }

        constexpr ::protocyte::i32 protocyte_escaped_5f() const noexcept { return protocyte_escaped_5f_; }
        void set_protocyte_escaped_5f(const ::protocyte::i32 value) noexcept { protocyte_escaped_5f_ = value; }
        constexpr void clear_protocyte_escaped_5f() noexcept { protocyte_escaped_5f_ = {}; }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Protocyte_escaped_5f5f4c494e455f5f> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Protocyte_escaped_5f5f4c494e455f5f::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Protocyte_escaped_5f5f4c494e455f5f>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            ::protocyte::SliceReader reader {input.data(), input.size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Protocyte_escaped_5f5f4c494e455f5f &output) noexcept {
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
                case FieldNumber::protocyte_escaped_5f5f46494c455f5f: {
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
                    typename Config::String protocyte_escaped_5f5f46494c455f5f_value {ctx_};
                    if (const auto st = ::protocyte::read_string_field<Config>(
                            *ctx_, reader, wire_type, field_number, protocyte_escaped_5f5f46494c455f5f_value);
                        !st) {
                        return st;
                    }
                    clear_protocyte_escaped_5f43686f696365();
                    new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_)
                        typename Config::String {::protocyte::move(protocyte_escaped_5f5f46494c455f5f_value)};
                    protocyte_escaped_5f43686f696365_case_ =
                        Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f;
                    break;
                }
                case FieldNumber::protocyte_escaped_76616c75655f5f676170: {
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
                    ::protocyte::i32 protocyte_escaped_76616c75655f5f676170_value {};
                    const auto decoded_protocyte_escaped_76616c75655f5f676170 =
                        ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_protocyte_escaped_76616c75655f5f676170) {
                        return decoded_protocyte_escaped_76616c75655f5f676170.status();
                    }
                    protocyte_escaped_76616c75655f5f676170_value = *decoded_protocyte_escaped_76616c75655f5f676170;
                    clear_protocyte_escaped_5f43686f696365();
                    new (&protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_)::protocyte::i32 {
                        ::protocyte::move(protocyte_escaped_76616c75655f5f676170_value)};
                    protocyte_escaped_5f43686f696365_case_ =
                        Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170;
                    break;
                }
                case FieldNumber::protocyte_escaped_5f5570706572: {
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
                    const auto decoded_protocyte_escaped_5f5570706572 =
                        ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_protocyte_escaped_5f5570706572) {
                        return decoded_protocyte_escaped_5f5570706572.status();
                    }
                    protocyte_escaped_5f5570706572_ = *decoded_protocyte_escaped_5f5570706572;
                    break;
                }
                case FieldNumber::trailing_protocyte: {
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
                    const auto decoded_trailing_protocyte =
                        ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_trailing_protocyte) {
                        return decoded_trailing_protocyte.status();
                    }
                    trailing_protocyte_ = *decoded_trailing_protocyte;
                    break;
                }
                case FieldNumber::protocyte_escaped_656e756d5f5f76616c7565: {
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
                    const auto decoded_protocyte_escaped_656e756d5f5f76616c7565 =
                        ::protocyte::read_enum_field(reader, wire_type, field_number);
                    if (!decoded_protocyte_escaped_656e756d5f5f76616c7565) {
                        return decoded_protocyte_escaped_656e756d5f5f76616c7565.status();
                    }
                    protocyte_escaped_656e756d5f5f76616c7565_ = *decoded_protocyte_escaped_656e756d5f5f76616c7565;
                    break;
                }
                case FieldNumber::class_protocyte: {
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
                    ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                        Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765<Config>
                            class_protocyte_value {*ctx_};
                    if (class_protocyte_.has_value()) {
                        if (const auto st = class_protocyte_value.copy_from(*class_protocyte_); !st) {
                            return st;
                        }
                    }
                    if (const auto st = ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number,
                                                                                  class_protocyte_value);
                        !st) {
                        return st;
                    }
                    if (const auto st = class_protocyte_.emplace(::protocyte::move(class_protocyte_value)); !st) {
                        return st;
                    }
                    break;
                }
                case FieldNumber::protocyte_escaped_5f: {
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
                    const auto decoded_protocyte_escaped_5f =
                        ::protocyte::read_int32_field(reader, wire_type, field_number);
                    if (!decoded_protocyte_escaped_5f) {
                        return decoded_protocyte_escaped_5f.status();
                    }
                    protocyte_escaped_5f_ = *decoded_protocyte_escaped_5f;
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
            if (protocyte_escaped_5f43686f696365_case_ ==
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f),
                        protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_.view());
                    !st) {
                    return ::protocyte::with_field(
                        st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f));
                }
            }
            if (protocyte_escaped_5f43686f696365_case_ ==
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_76616c75655f5f676170),
                        protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_);
                    !st) {
                    return ::protocyte::with_field(
                        st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_76616c75655f5f676170));
                }
            }
            if (protocyte_escaped_5f5570706572_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5570706572),
                        protocyte_escaped_5f5570706572_);
                    !st) {
                    return ::protocyte::with_field(
                        st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5570706572));
                }
            }
            if (trailing_protocyte_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::trailing_protocyte), trailing_protocyte_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::trailing_protocyte));
                }
            }
            if (protocyte_escaped_656e756d5f5f76616c7565_ != 0) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_656e756d5f5f76616c7565),
                        protocyte_escaped_656e756d5f5f76616c7565_);
                    !st) {
                    return ::protocyte::with_field(
                        st, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_656e756d5f5f76616c7565));
                }
            }
            if (class_protocyte_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::class_protocyte), *class_protocyte_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::class_protocyte));
                }
            }
            if (protocyte_escaped_5f_ != 0) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f),
                        protocyte_escaped_5f_);
                    !st) {
                    return ::protocyte::with_field(st,
                                                   static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f));
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
            if (protocyte_escaped_5f43686f696365_case_ ==
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f) {
                const auto field_size_protocyte_escaped_5f5f46494c455f5f = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f),
                    protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_.size());
                if (!field_size_protocyte_escaped_5f5f46494c455f5f) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_protocyte_escaped_5f5f46494c455f5f.error(),
                        static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_protocyte_escaped_5f5f46494c455f5f);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(),
                        static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f)));
                }
                total = *st_size;
            }
            if (protocyte_escaped_5f43686f696365_case_ ==
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_76616c75655f5f676170) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(
                               static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_76616c75655f5f676170)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(
                                   protocyte_escaped_5f43686f696365_.protocyte_escaped_76616c75655f5f676170_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(),
                        static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_76616c75655f5f676170)));
                }
                total = *st_size;
            }
            if (protocyte_escaped_5f5570706572_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total,
                    ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5570706572)) +
                        ::protocyte::varint_size(static_cast<::protocyte::u64>(protocyte_escaped_5f5570706572_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5570706572)));
                }
                total = *st_size;
            }
            if (trailing_protocyte_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::trailing_protocyte)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(trailing_protocyte_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::trailing_protocyte)));
                }
                total = *st_size;
            }
            if (protocyte_escaped_656e756d5f5f76616c7565_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(
                               static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_656e756d5f5f76616c7565)) +
                               ::protocyte::varint_size(
                                   static_cast<::protocyte::u64>(protocyte_escaped_656e756d5f5f76616c7565_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(),
                        static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_656e756d5f5f76616c7565)));
                }
                total = *st_size;
            }
            if (class_protocyte_.has_value()) {
                const auto field_size_class_protocyte = ::protocyte::message_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::class_protocyte), *class_protocyte_);
                if (!field_size_class_protocyte) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(field_size_class_protocyte.error(),
                                                static_cast<::protocyte::u32>(FieldNumber::class_protocyte)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_class_protocyte);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::class_protocyte)));
                }
                total = *st_size;
            }
            if (protocyte_escaped_5f_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(protocyte_escaped_5f_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f)));
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
            if (protocyte_escaped_5f43686f696365_case_ ==
                Protocyte_escaped_5f43686f696365Case::protocyte_escaped_5f5f46494c455f5f) {
                if (const auto st = protocyte_escaped_5f43686f696365_.protocyte_escaped_5f5f46494c455f5f_.validate();
                    !st) {
                    return ::protocyte::unexpected(
                        st.error().code, {},
                        static_cast<::protocyte::u32>(FieldNumber::protocyte_escaped_5f5f46494c455f5f));
                }
            }
            if (class_protocyte_.has_value()) {
                if (const auto st = class_protocyte_->validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::class_protocyte));
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        Protocyte_escaped_5f43686f696365Case protocyte_escaped_5f43686f696365_case_ {
            Protocyte_escaped_5f43686f696365Case::none};
        union Protocyte_escaped_5f43686f696365Storage {
            Protocyte_escaped_5f43686f696365Storage() noexcept {}
            ~Protocyte_escaped_5f43686f696365Storage() noexcept {}
            typename Config::String protocyte_escaped_5f5f46494c455f5f_;
            ::protocyte::i32 protocyte_escaped_76616c75655f5f676170_;
        } protocyte_escaped_5f43686f696365_;
        ::protocyte::i32 protocyte_escaped_5f5570706572_ {};
        ::protocyte::i32 trailing_protocyte_ {};
        ::protocyte::i32 protocyte_escaped_656e756d5f5f76616c7565_ {};
        typename Config::template Optional<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                Protocyte_escaped_5f5f4c494e455f5f_Protocyte_escaped_4e65737465645f5f4d657373616765<Config>>
            class_protocyte_;
        ::protocyte::i32 protocyte_escaped_5f_ {};
    };

    template<typename Config> struct Class_Struct_ {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
        };

        explicit Class_Struct_(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Class_Struct_ create(Context &ctx) noexcept { return Class_Struct_ {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Class_Struct_(Class_Struct_ &&) noexcept = default;
        Class_Struct_ &operator=(Class_Struct_ &&) noexcept = default;
        Class_Struct_(const Class_Struct_ &) = delete;
        Class_Struct_ &operator=(const Class_Struct_ &) = delete;

        ::protocyte::Status copy_from(const Class_Struct_ &source) noexcept {
            if (this == &source) {
                return {};
            }
            Class_Struct_ staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Class_Struct_ &source, Class_Struct_ &staging_message) noexcept {
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

        ::protocyte::Result<Class_Struct_> clone() const noexcept {
            auto output = Class_Struct_::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Class_Struct_ &output) const noexcept {
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
        static void reset_for_reuse_(Class_Struct_ &value, Context &ctx) noexcept {
            value.~Class_Struct_();
            new (&value) Class_Struct_ {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Class_Struct_ &source) noexcept {
            set_value(source.value());
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

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Class_Struct_> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Class_Struct_::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Class_Struct_> parse(Context &ctx,
                                                        ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            ::protocyte::SliceReader reader {input.data(), input.size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Class_Struct_ &output) noexcept {
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
        ::protocyte::i32 value_ {};
    };

    template<typename Config> struct Class_ {
        using Context = typename Config::Context;
        using KeywordValues = Class_KeywordValues;
        template<typename NestedConfig = Config> using struct_ = Class_Struct_<NestedConfig>;

        enum struct And_Case : ::protocyte::u32 {
            none = 0u,
            value = 1u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
            nested = 2u,
        };

        explicit Class_(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Class_ create(Context &ctx) noexcept { return Class_ {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Class_(Class_ &&other) noexcept:
            ctx_ {other.ctx_},
            unknown_fields_ {::protocyte::move(other.unknown_fields_)},
            nested_ {::protocyte::move(other.nested_)} {
            switch (other.and_protocyte_case_) {
                case And_Case::value: {
                    new (&and_protocyte_.value_)::protocyte::i32 {other.and_protocyte_.value_};
                    and_protocyte_case_ = And_Case::value;
                    break;
                }
                case And_Case::none:
                default: {
                    break;
                }
            }
            other.clear_and_protocyte();
        }
        Class_ &operator=(Class_ &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear_and_protocyte();
            ctx_ = other.ctx_;
            unknown_fields_ = ::protocyte::move(other.unknown_fields_);
            nested_ = ::protocyte::move(other.nested_);
            switch (other.and_protocyte_case_) {
                case And_Case::value: {
                    new (&and_protocyte_.value_)::protocyte::i32 {other.and_protocyte_.value_};
                    and_protocyte_case_ = And_Case::value;
                    break;
                }
                case And_Case::none:
                default: {
                    break;
                }
            }
            other.clear_and_protocyte();
            return *this;
        }
        ~Class_() noexcept { clear_and_protocyte(); }
        Class_(const Class_ &) = delete;
        Class_ &operator=(const Class_ &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const Class_ &source) noexcept {
            if (this == &source) {
                return {};
            }
            Class_ staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Class_ &source, Class_ &staging_message) noexcept {
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

        ::protocyte::Result<Class_> clone() const noexcept {
            auto output = Class_::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Class_ &output) const noexcept {
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
        static void reset_for_reuse_(Class_ &value, Context &ctx) noexcept {
            value.~Class_();
            new (&value) Class_ {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Class_ &source) noexcept {
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
            switch (source.and_protocyte_case_) {
                case And_Case::value: {
                    set_value(source.value());
                    break;
                }
                case And_Case::none:
                default: {
                    clear_and_protocyte();
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

        constexpr And_Case and_protocyte_case() const noexcept { return and_protocyte_case_; }
        void clear_and_protocyte() noexcept {
            switch (and_protocyte_case_) {
                case And_Case::value: {
                    break;
                }
                case And_Case::none:
                default: {
                    break;
                }
            }
            and_protocyte_case_ = And_Case::none;
        }

        constexpr bool has_value() const noexcept { return and_protocyte_case_ == And_Case::value; }
        constexpr ::protocyte::i32 value() const noexcept { return has_value() ? and_protocyte_.value_ : 0; }
        void set_value(const ::protocyte::i32 value) noexcept {
            clear_and_protocyte();
            new (&and_protocyte_.value_)::protocyte::i32 {value};
            and_protocyte_case_ = And_Case::value;
        }

        bool has_nested() const noexcept { return nested_.has_value(); }
        const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::Class_Struct_<Config> *
        nested() const noexcept {
            return has_nested() ? nested_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::Class_Struct_<Config> &>
        ensure_nested() noexcept {
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

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Class_> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Class_::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Class_> parse(Context &ctx,
                                                 ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            ::protocyte::SliceReader reader {input.data(), input.size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Class_ &output) noexcept {
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
                    ::protocyte::i32 value_value {};
                    {
                        const auto decoded_value = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded_value) {
                            return decoded_value.status();
                        }
                        value_value = *decoded_value;
                    }
                    clear_and_protocyte();
                    new (&and_protocyte_.value_)::protocyte::i32 {::protocyte::move(value_value)};
                    and_protocyte_case_ = And_Case::value;
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
                    ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::Class_Struct_<Config>
                        nested_value {*ctx_};
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
            if (and_protocyte_case_ == And_Case::value) {
                if (const auto st = ::protocyte::write_int32_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::value), and_protocyte_.value_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::value));
                }
            }
            if (nested_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::nested), *nested_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::nested));
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
            if (and_protocyte_case_ == And_Case::value) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::value)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(and_protocyte_.value_)));
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::value)));
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
            const auto total_with_unknown = ::protocyte::checked_add(total, unknown_fields_.size());
            if (!total_with_unknown) {
                return ::protocyte::unexpected(total_with_unknown.error());
            }
            return *total_with_unknown;
        }

        ::protocyte::Status validate() const noexcept {
            if (nested_.has_value()) {
                if (const auto st = nested_->validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::nested));
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        And_Case and_protocyte_case_ {And_Case::none};
        union And_Storage {
            And_Storage() noexcept {}
            ~And_Storage() noexcept {}
            ::protocyte::i32 value_;
        } and_protocyte_;
        typename Config::template Optional<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::Class_Struct_<Config>>
            nested_;
    };

} // namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f

#endif // PROTOCYTE_GENERATED_RESERVED_IDENTIFIERS_PROTO_1427A5F03FB8_HPP
