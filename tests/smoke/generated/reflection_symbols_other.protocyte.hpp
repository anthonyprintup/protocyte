#pragma once

#ifndef PROTOCYTE_GENERATED_REFLECTION_SYMBOLS_OTHER_PROTO_2301E483F915_HPP
#define PROTOCYTE_GENERATED_REFLECTION_SYMBOLS_OTHER_PROTO_2301E483F915_HPP

#include <protocyte/runtime/runtime.hpp>

#if PROTOCYTE_ENABLE_REFLECTION
#include <array>
#endif

namespace test::reflection_symbols {

#if PROTOCYTE_ENABLE_REFLECTION
    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> Foo_fields_;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> Foo_fields_fields_;
    } // namespace protocyte_reflection
#endif // PROTOCYTE_ENABLE_REFLECTION

    template<typename Config = ::protocyte::DefaultConfig> struct Foo_;
    template<typename Config = ::protocyte::DefaultConfig> struct Foo_fields_;

    template<typename Config> struct Foo_ {
        using Context = typename Config::Context;
        explicit Foo_(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Foo_ create(Context &ctx) noexcept { return Foo_ {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Foo_(Foo_ &&) noexcept = default;
        Foo_ &operator=(Foo_ &&) noexcept = default;
        Foo_(const Foo_ &) = delete;
        Foo_ &operator=(const Foo_ &) = delete;

        ::protocyte::Status copy_from(const Foo_ &source) noexcept {
            if (this == &source) {
                return {};
            }
            Foo_ staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Foo_ &source, Foo_ &staging_message) noexcept {
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

        ::protocyte::Result<Foo_> clone() const noexcept {
            auto output = Foo_::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Foo_ &output) const noexcept {
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
        static void reset_for_reuse_(Foo_ &value, Context &ctx) noexcept {
            value.~Foo_();
            new (&value) Foo_ {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Foo_ &source) noexcept {
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

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Foo_> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Foo_::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Foo_> parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Foo_ &output) noexcept {
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
            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                if (const auto st = ::protocyte::read_unknown_field<Config>(*ctx_, reader, wire_type, field_number,
                                                                            unknown_fields_);
                    !st) {
                    return st;
                }
            } else {
                if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number); !st) {
                    return st;
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
    };

    template<typename Config> struct Foo_fields_ {
        using Context = typename Config::Context;
        explicit Foo_fields_(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Foo_fields_ create(Context &ctx) noexcept { return Foo_fields_ {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Foo_fields_(Foo_fields_ &&) noexcept = default;
        Foo_fields_ &operator=(Foo_fields_ &&) noexcept = default;
        Foo_fields_(const Foo_fields_ &) = delete;
        Foo_fields_ &operator=(const Foo_fields_ &) = delete;

        ::protocyte::Status copy_from(const Foo_fields_ &source) noexcept {
            if (this == &source) {
                return {};
            }
            Foo_fields_ staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Foo_fields_ &source, Foo_fields_ &staging_message) noexcept {
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

        ::protocyte::Result<Foo_fields_> clone() const noexcept {
            auto output = Foo_fields_::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        ::protocyte::Status clone(Foo_fields_ &output) const noexcept {
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
        static void reset_for_reuse_(Foo_fields_ &value, Context &ctx) noexcept {
            value.~Foo_fields_();
            new (&value) Foo_fields_ {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Foo_fields_ &source) noexcept {
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

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Foo_fields_> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Foo_fields_::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return ::protocyte::move(output);
        }

        static ::protocyte::Result<Foo_fields_> parse(Context &ctx,
                                                      ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Foo_fields_ &output) noexcept {
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
            if constexpr (::protocyte::preserve_unknown_fields_v<Config>) {
                if (const auto st = ::protocyte::read_unknown_field<Config>(*ctx_, reader, wire_type, field_number,
                                                                            unknown_fields_);
                    !st) {
                    return st;
                }
            } else {
                if (const auto st = ::protocyte::skip_field<Config>(*ctx_, reader, wire_type, field_number); !st) {
                    return st;
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
    };

} // namespace test::reflection_symbols

#endif // PROTOCYTE_GENERATED_REFLECTION_SYMBOLS_OTHER_PROTO_2301E483F915_HPP
