#pragma once

#ifndef PROTOCYTE_GENERATED_RESERVED_IDENTIFIERS_PROTO_1427A5F03FB8_HPP
#define PROTOCYTE_GENERATED_RESERVED_IDENTIFIERS_PROTO_1427A5F03FB8_HPP

#include <protocyte/runtime/runtime.hpp>

#if PROTOCYTE_ENABLE_REFLECTION
#include <array>
#endif

namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f {

#if PROTOCYTE_ENABLE_REFLECTION
    namespace protocyte_reflection {
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1>
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 7> protocyte_escaped_5f5f4c494e455f5f_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> class_struct_fields_;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> class_protocyte_bae1d4f6754b_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> Config_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> Reader_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> MergeHelperNeighbors_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> MergeHelperNeighbors_merge_field_from_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 1> MergeHelperNeighbors_merge_fields_from_fields_;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 0> LegacyPayload_fields;
        extern const ::std::array<::protocyte::ReflectionFieldInfo, 2> DeprecationCarrier_fields;
        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2>
            protocyte_escaped_5f5f46494c455f5f_enum_values;
        extern const ::protocyte::ReflectionEnumInfo protocyte_escaped_5f5f46494c455f5f_enum;
        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 1> LegacyMode_enum_values;
        extern const ::protocyte::ReflectionEnumInfo LegacyMode_enum;
        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 2>
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum_values;
        extern const ::protocyte::ReflectionEnumInfo
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum;
        extern const ::std::array<::protocyte::ReflectionEnumValueInfo, 1> class_KeywordValues_enum_values;
        extern const ::protocyte::ReflectionEnumInfo class_KeywordValues_enum;
    } // namespace protocyte_reflection
#endif // PROTOCYTE_ENABLE_REFLECTION

    enum struct protocyte_escaped_5f5f46494c455f5f : ::protocyte::i32 {
        protocyte_escaped_5f5570706572 = 0,
        protocyte_escaped_76616c75655f5f676170 = 1,
    };
    inline constexpr protocyte_escaped_5f5f46494c455f5f protocyte_escaped_5f5f46494c455f5f_MIN {
        protocyte_escaped_5f5f46494c455f5f::protocyte_escaped_5f5570706572};
    inline constexpr protocyte_escaped_5f5f46494c455f5f protocyte_escaped_5f5f46494c455f5f_MAX {
        protocyte_escaped_5f5f46494c455f5f::protocyte_escaped_76616c75655f5f676170};
    inline constexpr ::protocyte::i32 protocyte_escaped_5f5f46494c455f5f_ARRAYSIZE {2};
    [[nodiscard]] inline constexpr bool
    protocyte_escaped_5f5f46494c455f5f_is_valid(const ::protocyte::i32 value) noexcept {
        return 0 <= value && value <= 1;
    }
#if PROTOCYTE_ENABLE_REFLECTION
    [[nodiscard]] inline const ::protocyte::ReflectionEnumInfo *
    protocyte_escaped_5f5f46494c455f5f_descriptor() noexcept {
        return &::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::protocyte_reflection::
            protocyte_escaped_5f5f46494c455f5f_enum;
    }
    [[nodiscard]] inline ::protocyte::StringView
    protocyte_escaped_5f5f46494c455f5f_name(const protocyte_escaped_5f5f46494c455f5f value) noexcept {
        for (const auto &item : protocyte_escaped_5f5f46494c455f5f_descriptor()->values) {
            if (item.number == static_cast<::protocyte::i32>(value)) {
                return item.name;
            }
        }
        return {};
    }
    [[nodiscard]] inline bool
    protocyte_escaped_5f5f46494c455f5f_parse(const ::protocyte::StringView name,
                                             protocyte_escaped_5f5f46494c455f5f &value) noexcept {
        for (const auto &item : protocyte_escaped_5f5f46494c455f5f_descriptor()->values) {
            if (::protocyte::string_view_equal(name, item.name)) {
                value = static_cast<protocyte_escaped_5f5f46494c455f5f>(item.number);
                return true;
            }
        }
        return false;
    }
    template<::protocyte::usize N> [[nodiscard]] inline bool
    protocyte_escaped_5f5f46494c455f5f_parse(const char (&name)[N],
                                             protocyte_escaped_5f5f46494c455f5f &value) noexcept {
        ::protocyte::usize size {};
        while (size < N && name[size] != '\0') { ++size; }
        return protocyte_escaped_5f5f46494c455f5f_parse(::protocyte::StringView {name, size}, value);
    }
#endif // PROTOCYTE_ENABLE_REFLECTION

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#elif defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
    enum struct [[deprecated]] LegacyMode : ::protocyte::i32 {
        LEGACY_MODE_UNSPECIFIED = 0,
    };
    inline constexpr LegacyMode LegacyMode_MIN {LegacyMode::LEGACY_MODE_UNSPECIFIED};
    inline constexpr LegacyMode LegacyMode_MAX {LegacyMode::LEGACY_MODE_UNSPECIFIED};
    inline constexpr ::protocyte::i32 LegacyMode_ARRAYSIZE {1};
    [[nodiscard]] inline constexpr bool LegacyMode_is_valid(const ::protocyte::i32 value) noexcept {
        return value == 0;
    }
#if PROTOCYTE_ENABLE_REFLECTION
    [[nodiscard]] inline const ::protocyte::ReflectionEnumInfo *LegacyMode_descriptor() noexcept {
        return &::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::protocyte_reflection::
            LegacyMode_enum;
    }
    [[nodiscard]] inline ::protocyte::StringView LegacyMode_name(const LegacyMode value) noexcept {
        for (const auto &item : LegacyMode_descriptor()->values) {
            if (item.number == static_cast<::protocyte::i32>(value)) {
                return item.name;
            }
        }
        return {};
    }
    [[nodiscard]] inline bool LegacyMode_parse(const ::protocyte::StringView name, LegacyMode &value) noexcept {
        for (const auto &item : LegacyMode_descriptor()->values) {
            if (::protocyte::string_view_equal(name, item.name)) {
                value = static_cast<LegacyMode>(item.number);
                return true;
            }
        }
        return false;
    }
    template<::protocyte::usize N>
    [[nodiscard]] inline bool LegacyMode_parse(const char (&name)[N], LegacyMode &value) noexcept {
        ::protocyte::usize size {};
        while (size < N && name[size] != '\0') { ++size; }
        return LegacyMode_parse(::protocyte::StringView {name, size}, value);
    }
#endif // PROTOCYTE_ENABLE_REFLECTION
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#elif defined(_MSC_VER)
#pragma warning(pop)
#endif

    enum struct protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d : ::protocyte::i32 {
        protocyte_escaped_5f5f535444435f5f = 0,
        enum_trailing_ = 1,
    };

    enum struct class_KeywordValues : ::protocyte::i32 {
        class_ = 0,
    };

    inline constexpr ::protocyte::i32 protocyte_escaped_5f5f444154455f5f {7};
    inline constexpr ::protocyte::i32 class_ {8};

    template<typename Config = ::protocyte::DefaultConfig>
    struct protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765;
    template<typename Config = ::protocyte::DefaultConfig> struct protocyte_escaped_5f5f4c494e455f5f;
    template<typename Config = ::protocyte::DefaultConfig> struct class_struct_;
    template<typename Config = ::protocyte::DefaultConfig> struct class_protocyte_bae1d4f6754b;
    template<typename Config_ = ::protocyte::DefaultConfig> struct Config;
    template<typename Config = ::protocyte::DefaultConfig> struct Reader;
    template<typename Config = ::protocyte::DefaultConfig> struct MergeHelperNeighbors;
    template<typename Config = ::protocyte::DefaultConfig> struct MergeHelperNeighbors_merge_field_from;
    template<typename Config = ::protocyte::DefaultConfig> struct MergeHelperNeighbors_merge_fields_from_;
    template<typename Config = ::protocyte::DefaultConfig> struct [[deprecated]] LegacyPayload;
    template<typename Config = ::protocyte::DefaultConfig> struct DeprecationCarrier;

    template<typename Config>
    struct protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            protocyte_escaped_5f496e6e6572 = 1u,
        };

        explicit protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765(
            Context &ctx) noexcept:
            ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765
        create(Context &ctx) noexcept {
            return protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765(
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &&) noexcept = default;
        protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &operator=(
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &&) noexcept = default;
        protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765(
            const protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &) = delete;
        protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &
        operator=(const protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &) = delete;

        ::protocyte::Status
        copy_from(const protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765
                      &source) noexcept {
            if (this == &source) {
                return {};
            }
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status
        copy_from(const protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &source,
                  protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765
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

        ::protocyte::Result<protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765>
        clone() const noexcept {
            auto output =
                protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765
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
        reset_for_reuse_(protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &value,
                         Context &ctx) noexcept {
            value.~protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765();
            new (&value) protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 {ctx};
        }

        ::protocyte::Status
        copy_from_in_place_(const protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765
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
        static ::protocyte::Result<protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765>
        parse(Context &ctx, Reader &reader) noexcept {
            auto output =
                protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader> static ::protocyte::Status
        parse(Reader &reader,
              protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765 &output) noexcept {
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

    template<typename Config> struct protocyte_escaped_5f5f4c494e455f5f {
        using Context = typename Config::Context;
        using protocyte_escaped_5f4e6573746564456e756d =
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d;
        static constexpr protocyte_escaped_5f4e6573746564456e756d protocyte_escaped_5f4e6573746564456e756d_MIN {
            protocyte_escaped_5f4e6573746564456e756d::protocyte_escaped_5f5f535444435f5f};
        static constexpr protocyte_escaped_5f4e6573746564456e756d protocyte_escaped_5f4e6573746564456e756d_MAX {
            protocyte_escaped_5f4e6573746564456e756d::enum_trailing_};
        static constexpr ::protocyte::i32 protocyte_escaped_5f4e6573746564456e756d_ARRAYSIZE {2};
        [[nodiscard]] static constexpr bool
        protocyte_escaped_5f4e6573746564456e756d_is_valid(const ::protocyte::i32 value) noexcept {
            return 0 <= value && value <= 1;
        }
#if PROTOCYTE_ENABLE_REFLECTION
        [[nodiscard]] static const ::protocyte::ReflectionEnumInfo *
        protocyte_escaped_5f4e6573746564456e756d_descriptor() noexcept {
            return &::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::protocyte_reflection::
                protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_5f4e6573746564456e756d_enum;
        }
        [[nodiscard]] static ::protocyte::StringView
        protocyte_escaped_5f4e6573746564456e756d_name(const protocyte_escaped_5f4e6573746564456e756d value) noexcept {
            for (const auto &item : protocyte_escaped_5f4e6573746564456e756d_descriptor()->values) {
                if (item.number == static_cast<::protocyte::i32>(value)) {
                    return item.name;
                }
            }
            return {};
        }
        [[nodiscard]] static bool
        protocyte_escaped_5f4e6573746564456e756d_parse(const ::protocyte::StringView name,
                                                       protocyte_escaped_5f4e6573746564456e756d &value) noexcept {
            for (const auto &item : protocyte_escaped_5f4e6573746564456e756d_descriptor()->values) {
                if (::protocyte::string_view_equal(name, item.name)) {
                    value = static_cast<protocyte_escaped_5f4e6573746564456e756d>(item.number);
                    return true;
                }
            }
            return false;
        }
        template<::protocyte::usize N> [[nodiscard]] static bool
        protocyte_escaped_5f4e6573746564456e756d_parse(const char (&name)[N],
                                                       protocyte_escaped_5f4e6573746564456e756d &value) noexcept {
            ::protocyte::usize size {};
            while (size < N && name[size] != '\0') { ++size; }
            return protocyte_escaped_5f4e6573746564456e756d_parse(::protocyte::StringView {name, size}, value);
        }
#endif // PROTOCYTE_ENABLE_REFLECTION
        template<typename NestedConfig = Config> using protocyte_escaped_4e65737465645f5f4d657373616765 =
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765<NestedConfig>;

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

        explicit protocyte_escaped_5f5f4c494e455f5f(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static protocyte_escaped_5f5f4c494e455f5f create(Context &ctx) noexcept {
            return protocyte_escaped_5f5f4c494e455f5f {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        protocyte_escaped_5f5f4c494e455f5f(protocyte_escaped_5f5f4c494e455f5f &&other) noexcept:
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
        protocyte_escaped_5f5f4c494e455f5f &operator=(protocyte_escaped_5f5f4c494e455f5f &&other) noexcept {
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
        ~protocyte_escaped_5f5f4c494e455f5f() noexcept { clear_protocyte_escaped_5f43686f696365(); }
        protocyte_escaped_5f5f4c494e455f5f(const protocyte_escaped_5f5f4c494e455f5f &) = delete;
        protocyte_escaped_5f5f4c494e455f5f &operator=(const protocyte_escaped_5f5f4c494e455f5f &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const protocyte_escaped_5f5f4c494e455f5f &source) noexcept {
            if (this == &source) {
                return {};
            }
            protocyte_escaped_5f5f4c494e455f5f staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const protocyte_escaped_5f5f4c494e455f5f &source,
                                      protocyte_escaped_5f5f4c494e455f5f &staging_message) noexcept {
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

        ::protocyte::Result<protocyte_escaped_5f5f4c494e455f5f> clone() const noexcept {
            auto output = protocyte_escaped_5f5f4c494e455f5f::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(protocyte_escaped_5f5f4c494e455f5f &output) const noexcept {
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
        static void reset_for_reuse_(protocyte_escaped_5f5f4c494e455f5f &value, Context &ctx) noexcept {
            value.~protocyte_escaped_5f5f4c494e455f5f();
            new (&value) protocyte_escaped_5f5f4c494e455f5f {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const protocyte_escaped_5f5f4c494e455f5f &source) noexcept {
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

        // Protocyte C++ name mapping: protobuf field "trailing_" uses accessor stem "trailing_protocyte" to avoid a C++
        // collision.
        constexpr ::protocyte::i32 trailing_protocyte() const noexcept { return trailing_protocyte_; }
        void set_trailing_protocyte(const ::protocyte::i32 value) noexcept { trailing_protocyte_ = value; }
        constexpr void clear_trailing_protocyte() noexcept { trailing_protocyte_ = {}; }

        constexpr ::protocyte::i32 protocyte_escaped_656e756d5f5f76616c7565_raw() const noexcept {
            return protocyte_escaped_656e756d5f5f76616c7565_;
        }
        constexpr ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
            protocyte_escaped_5f5f46494c455f5f
            protocyte_escaped_656e756d5f5f76616c7565() const noexcept {
            return static_cast<::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                                   protocyte_escaped_5f5f46494c455f5f>(protocyte_escaped_656e756d5f5f76616c7565_);
        }
        ::protocyte::Status set_protocyte_escaped_656e756d5f5f76616c7565_raw(const ::protocyte::i32 value) noexcept {
            protocyte_escaped_656e756d5f5f76616c7565_ = value;
            return {};
        }
        ::protocyte::Status set_protocyte_escaped_656e756d5f5f76616c7565(
            const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                protocyte_escaped_5f5f46494c455f5f value) noexcept {
            return set_protocyte_escaped_656e756d5f5f76616c7565_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_protocyte_escaped_656e756d5f5f76616c7565() noexcept {
            protocyte_escaped_656e756d5f5f76616c7565_ = {};
        }

        // Protocyte C++ name mapping: protobuf field "class" uses accessor stem "class_protocyte" to avoid a C++
        // collision.
        bool has_class_protocyte() const noexcept { return class_protocyte_.has_value(); }
        const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
            protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765<Config> *
            class_protocyte() const noexcept {
            return has_class_protocyte() ? class_protocyte_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::
                protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765<Config> &>
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
        static ::protocyte::Result<protocyte_escaped_5f5f4c494e455f5f> parse(Context &ctx, Reader &reader) noexcept {
            auto output = protocyte_escaped_5f5f4c494e455f5f::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<protocyte_escaped_5f5f4c494e455f5f>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, protocyte_escaped_5f5f4c494e455f5f &output) noexcept {
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
                        protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765<Config>
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
                protocyte_escaped_5f5f4c494e455f5f_protocyte_escaped_4e65737465645f5f4d657373616765<Config>>
            class_protocyte_;
        ::protocyte::i32 protocyte_escaped_5f_ {};
    };

    template<typename Config> struct class_struct_ {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
        };

        explicit class_struct_(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static class_struct_ create(Context &ctx) noexcept { return class_struct_ {ctx}; }
        Context *context() const noexcept { return ctx_; }
        class_struct_(class_struct_ &&) noexcept = default;
        class_struct_ &operator=(class_struct_ &&) noexcept = default;
        class_struct_(const class_struct_ &) = delete;
        class_struct_ &operator=(const class_struct_ &) = delete;

        ::protocyte::Status copy_from(const class_struct_ &source) noexcept {
            if (this == &source) {
                return {};
            }
            class_struct_ staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const class_struct_ &source, class_struct_ &staging_message) noexcept {
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

        ::protocyte::Result<class_struct_> clone() const noexcept {
            auto output = class_struct_::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(class_struct_ &output) const noexcept {
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
        static void reset_for_reuse_(class_struct_ &value, Context &ctx) noexcept {
            value.~class_struct_();
            new (&value) class_struct_ {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const class_struct_ &source) noexcept {
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
        static ::protocyte::Result<class_struct_> parse(Context &ctx, Reader &reader) noexcept {
            auto output = class_struct_::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<class_struct_> parse(Context &ctx,
                                                        ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, class_struct_ &output) noexcept {
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

    template<typename Config> struct class_protocyte_bae1d4f6754b {
        using Context = typename Config::Context;
        using KeywordValues = class_KeywordValues;
        static constexpr KeywordValues KeywordValues_MIN {KeywordValues::class_};
        static constexpr KeywordValues KeywordValues_MAX {KeywordValues::class_};
        static constexpr ::protocyte::i32 KeywordValues_ARRAYSIZE {1};
        [[nodiscard]] static constexpr bool KeywordValues_is_valid(const ::protocyte::i32 value) noexcept {
            return value == 0;
        }
#if PROTOCYTE_ENABLE_REFLECTION
        [[nodiscard]] static const ::protocyte::ReflectionEnumInfo *KeywordValues_descriptor() noexcept {
            return &::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::protocyte_reflection::
                class_KeywordValues_enum;
        }
        [[nodiscard]] static ::protocyte::StringView KeywordValues_name(const KeywordValues value) noexcept {
            for (const auto &item : KeywordValues_descriptor()->values) {
                if (item.number == static_cast<::protocyte::i32>(value)) {
                    return item.name;
                }
            }
            return {};
        }
        [[nodiscard]] static bool KeywordValues_parse(const ::protocyte::StringView name,
                                                      KeywordValues &value) noexcept {
            for (const auto &item : KeywordValues_descriptor()->values) {
                if (::protocyte::string_view_equal(name, item.name)) {
                    value = static_cast<KeywordValues>(item.number);
                    return true;
                }
            }
            return false;
        }
        template<::protocyte::usize N>
        [[nodiscard]] static bool KeywordValues_parse(const char (&name)[N], KeywordValues &value) noexcept {
            ::protocyte::usize size {};
            while (size < N && name[size] != '\0') { ++size; }
            return KeywordValues_parse(::protocyte::StringView {name, size}, value);
        }
#endif // PROTOCYTE_ENABLE_REFLECTION
        template<typename NestedConfig = Config> using struct_ = class_struct_<NestedConfig>;

        enum struct And_Case : ::protocyte::u32 {
            none = 0u,
            value = 1u,
        };

        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
            nested = 2u,
        };

        explicit class_protocyte_bae1d4f6754b(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static class_protocyte_bae1d4f6754b create(Context &ctx) noexcept { return class_protocyte_bae1d4f6754b {ctx}; }
        Context *context() const noexcept { return ctx_; }
        class_protocyte_bae1d4f6754b(class_protocyte_bae1d4f6754b &&other) noexcept:
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
        class_protocyte_bae1d4f6754b &operator=(class_protocyte_bae1d4f6754b &&other) noexcept {
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
        ~class_protocyte_bae1d4f6754b() noexcept { clear_and_protocyte(); }
        class_protocyte_bae1d4f6754b(const class_protocyte_bae1d4f6754b &) = delete;
        class_protocyte_bae1d4f6754b &operator=(const class_protocyte_bae1d4f6754b &) = delete;

        template<typename T> static void destroy_at_(T *value) noexcept { value->~T(); }

        ::protocyte::Status copy_from(const class_protocyte_bae1d4f6754b &source) noexcept {
            if (this == &source) {
                return {};
            }
            class_protocyte_bae1d4f6754b staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const class_protocyte_bae1d4f6754b &source,
                                      class_protocyte_bae1d4f6754b &staging_message) noexcept {
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

        ::protocyte::Result<class_protocyte_bae1d4f6754b> clone() const noexcept {
            auto output = class_protocyte_bae1d4f6754b::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(class_protocyte_bae1d4f6754b &output) const noexcept {
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
        static void reset_for_reuse_(class_protocyte_bae1d4f6754b &value, Context &ctx) noexcept {
            value.~class_protocyte_bae1d4f6754b();
            new (&value) class_protocyte_bae1d4f6754b {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const class_protocyte_bae1d4f6754b &source) noexcept {
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
        const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::class_struct_<Config> *
        nested() const noexcept {
            return has_nested() ? nested_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::class_struct_<Config> &>
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
        static ::protocyte::Result<class_protocyte_bae1d4f6754b> parse(Context &ctx, Reader &reader) noexcept {
            auto output = class_protocyte_bae1d4f6754b::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<class_protocyte_bae1d4f6754b>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, class_protocyte_bae1d4f6754b &output) noexcept {
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
                    ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::class_struct_<Config>
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
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::class_struct_<Config>>
            nested_;
    };

    template<typename Config_> struct Config {
        using Context = typename Config_::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            text = 1u,
        };

        explicit Config(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx}, text_ {&ctx} {}

        static Config create(Context &ctx) noexcept { return Config {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Config(Config &&) noexcept = default;
        Config &operator=(Config &&) noexcept = default;
        Config(const Config &) = delete;
        Config &operator=(const Config &) = delete;

        ::protocyte::Status copy_from(const Config &source) noexcept {
            if (this == &source) {
                return {};
            }
            Config staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Config &source, Config &staging_message) noexcept {
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

        ::protocyte::Result<Config> clone() const noexcept {
            auto output = Config::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(Config &output) const noexcept {
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
        static void reset_for_reuse_(Config &value, Context &ctx) noexcept {
            value.~Config();
            new (&value) Config {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Config &source) noexcept {
            if (const auto st = set_text(source.text()); !st) {
                return st;
            }
            if constexpr (::protocyte::preserve_unknown_fields_v<Config_>) {
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
        ::protocyte::MutableUnknownFieldSet<Config_> mutable_unknown_fields() noexcept
            requires(::protocyte::preserve_unknown_fields_v<Config_>)
        {
            return ::protocyte::MutableUnknownFieldSet<Config_> {*ctx_, unknown_fields_};
        }

        ::protocyte::StringView text() const noexcept { return text_.view(); }
        typename Config_::String &mutable_text() noexcept { return text_; }
        template<class Value>::protocyte::Status set_text(const Value &value) noexcept
            requires(::protocyte::ByteSpanSource<Value> && !::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::text));
            }
            typename Config_::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::text));
            }
            text_ = ::protocyte::move(temp);
            return {};
        }
        template<class Value>::protocyte::Status set_text(const Value &value) noexcept
            requires(::protocyte::TextSource<Value>)
        {
            const auto view = ::protocyte::text_byte_span_of(value);
            if (!view) {
                return ::protocyte::with_field(view.status(), static_cast<::protocyte::u32>(FieldNumber::text));
            }
            typename Config_::String temp {ctx_};
            if (const auto st = temp.assign(*view); !st) {
                return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::text));
            }
            text_ = ::protocyte::move(temp);
            return {};
        }
        void clear_text() noexcept { text_.clear(); }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<Config> parse(Context &ctx, Reader &reader) noexcept {
            auto output = Config::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<Config> parse(Context &ctx,
                                                 ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, Config &output) noexcept {
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
                case FieldNumber::text: {
                    if (wire_type != ::protocyte::WireType::LEN) {
                        if constexpr (::protocyte::preserve_unknown_fields_v<Config_>) {
                            if (const auto st = ::protocyte::read_unknown_field<Config_>(*ctx_, reader, wire_type,
                                                                                         field_number, unknown_fields_);
                                !st) {
                                return st;
                            }
                        } else {
                            if (const auto st =
                                    ::protocyte::skip_field<Config_>(*ctx_, reader, wire_type, field_number);
                                !st) {
                                return st;
                            }
                        }
                        break;
                    }
                    if (const auto st =
                            ::protocyte::read_string_field<Config_>(*ctx_, reader, wire_type, field_number, text_);
                        !st) {
                        return st;
                    }
                    break;
                }
                default: {
                    if constexpr (::protocyte::preserve_unknown_fields_v<Config_>) {
                        if (const auto st = ::protocyte::read_unknown_field<Config_>(*ctx_, reader, wire_type,
                                                                                     field_number, unknown_fields_);
                            !st) {
                            return st;
                        }
                    } else {
                        if (const auto st = ::protocyte::skip_field<Config_>(*ctx_, reader, wire_type, field_number);
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
            if (!text_.empty()) {
                if (const auto st = ::protocyte::write_string_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::text), text_.view());
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::text));
                }
            }
            if constexpr (::protocyte::preserve_unknown_fields_v<Config_>) {
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
            if (!text_.empty()) {
                const auto field_size_text = ::protocyte::length_delimited_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::text), text_.size());
                if (!field_size_text) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_text.error(), static_cast<::protocyte::u32>(FieldNumber::text)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_text);
                if (!st_size) {
                    return ::protocyte::unexpected(
                        ::protocyte::with_field(st_size.error(), static_cast<::protocyte::u32>(FieldNumber::text)));
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
            if (const auto st = text_.validate(); !st) {
                return ::protocyte::unexpected(st.error().code, {}, static_cast<::protocyte::u32>(FieldNumber::text));
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config_> unknown_fields_;
        typename Config_::String text_;
    };

    template<typename Config> struct Reader {
        using Context = typename Config::Context;
        explicit Reader(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static Reader create(Context &ctx) noexcept { return Reader {ctx}; }
        Context *context() const noexcept { return ctx_; }
        Reader(Reader &&) noexcept = default;
        Reader &operator=(Reader &&) noexcept = default;
        Reader(const Reader &) = delete;
        Reader &operator=(const Reader &) = delete;

        ::protocyte::Status copy_from(const Reader &source) noexcept {
            if (this == &source) {
                return {};
            }
            Reader staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const Reader &source, Reader &staging_message) noexcept {
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

        ::protocyte::Result<Reader> clone() const noexcept {
            auto output = Reader::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(Reader &output) const noexcept {
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
        static void reset_for_reuse_(Reader &value, Context &ctx) noexcept {
            value.~Reader();
            new (&value) Reader {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const Reader &source) noexcept {
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

        template<::protocyte::ReaderLike Reader_>
        static ::protocyte::Result<Reader> parse(Context &ctx, Reader_ &reader) noexcept {
            auto output = Reader::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<Reader> parse(Context &ctx,
                                                 ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader_>
        static ::protocyte::Status parse(Reader_ &reader, Reader &output) noexcept {
            Context *const output_ctx = output.context();
            reset_for_reuse_(output, *output_ctx);
            if (const auto st = output.merge_from(reader); !st) {
                reset_for_reuse_(output, *output_ctx);
                return st;
            }
            return {};
        }

        template<::protocyte::ReaderLike Reader_>::protocyte::Status merge_from(Reader_ &reader) noexcept {
            ::protocyte::ParseBudgetReader<Reader_> budget_reader {
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
        template<typename Reader_>
        ::protocyte::Status merge_field_from_(Reader_ &reader, const ::protocyte::u32 field_number,
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

        template<typename Reader_>::protocyte::Status merge_fields_from(Reader_ &reader) noexcept {
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

    template<typename Config> struct MergeHelperNeighbors {
        using Context = typename Config::Context;
        template<typename NestedConfig = Config> using merge_field_from =
            MergeHelperNeighbors_merge_field_from<NestedConfig>;
        template<typename NestedConfig = Config> using merge_fields_from_ =
            MergeHelperNeighbors_merge_fields_from_<NestedConfig>;

        explicit MergeHelperNeighbors(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static MergeHelperNeighbors create(Context &ctx) noexcept { return MergeHelperNeighbors {ctx}; }
        Context *context() const noexcept { return ctx_; }
        MergeHelperNeighbors(MergeHelperNeighbors &&) noexcept = default;
        MergeHelperNeighbors &operator=(MergeHelperNeighbors &&) noexcept = default;
        MergeHelperNeighbors(const MergeHelperNeighbors &) = delete;
        MergeHelperNeighbors &operator=(const MergeHelperNeighbors &) = delete;

        ::protocyte::Status copy_from(const MergeHelperNeighbors &source) noexcept {
            if (this == &source) {
                return {};
            }
            MergeHelperNeighbors staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const MergeHelperNeighbors &source,
                                      MergeHelperNeighbors &staging_message) noexcept {
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

        ::protocyte::Result<MergeHelperNeighbors> clone() const noexcept {
            auto output = MergeHelperNeighbors::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(MergeHelperNeighbors &output) const noexcept {
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
        static void reset_for_reuse_(MergeHelperNeighbors &value, Context &ctx) noexcept {
            value.~MergeHelperNeighbors();
            new (&value) MergeHelperNeighbors {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const MergeHelperNeighbors &source) noexcept {
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
        static ::protocyte::Result<MergeHelperNeighbors> parse(Context &ctx, Reader &reader) noexcept {
            auto output = MergeHelperNeighbors::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<MergeHelperNeighbors>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, MergeHelperNeighbors &output) noexcept {
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

    template<typename Config> struct MergeHelperNeighbors_merge_field_from {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
        };

        explicit MergeHelperNeighbors_merge_field_from(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static MergeHelperNeighbors_merge_field_from create(Context &ctx) noexcept {
            return MergeHelperNeighbors_merge_field_from {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        MergeHelperNeighbors_merge_field_from(MergeHelperNeighbors_merge_field_from &&) noexcept = default;
        MergeHelperNeighbors_merge_field_from &operator=(MergeHelperNeighbors_merge_field_from &&) noexcept = default;
        MergeHelperNeighbors_merge_field_from(const MergeHelperNeighbors_merge_field_from &) = delete;
        MergeHelperNeighbors_merge_field_from &operator=(const MergeHelperNeighbors_merge_field_from &) = delete;

        ::protocyte::Status copy_from(const MergeHelperNeighbors_merge_field_from &source) noexcept {
            if (this == &source) {
                return {};
            }
            MergeHelperNeighbors_merge_field_from staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const MergeHelperNeighbors_merge_field_from &source,
                                      MergeHelperNeighbors_merge_field_from &staging_message) noexcept {
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

        ::protocyte::Result<MergeHelperNeighbors_merge_field_from> clone() const noexcept {
            auto output = MergeHelperNeighbors_merge_field_from::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(MergeHelperNeighbors_merge_field_from &output) const noexcept {
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
        static void reset_for_reuse_(MergeHelperNeighbors_merge_field_from &value, Context &ctx) noexcept {
            value.~MergeHelperNeighbors_merge_field_from();
            new (&value) MergeHelperNeighbors_merge_field_from {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const MergeHelperNeighbors_merge_field_from &source) noexcept {
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
        static ::protocyte::Result<MergeHelperNeighbors_merge_field_from> parse(Context &ctx, Reader &reader) noexcept {
            auto output = MergeHelperNeighbors_merge_field_from::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<MergeHelperNeighbors_merge_field_from>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, MergeHelperNeighbors_merge_field_from &output) noexcept {
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
                    {
                        const auto decoded_value = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded_value) {
                            return decoded_value.status();
                        }
                        value_ = *decoded_value;
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

    template<typename Config> struct MergeHelperNeighbors_merge_fields_from_ {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            value = 1u,
        };

        explicit MergeHelperNeighbors_merge_fields_from_(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static MergeHelperNeighbors_merge_fields_from_ create(Context &ctx) noexcept {
            return MergeHelperNeighbors_merge_fields_from_ {ctx};
        }
        Context *context() const noexcept { return ctx_; }
        MergeHelperNeighbors_merge_fields_from_(MergeHelperNeighbors_merge_fields_from_ &&) noexcept = default;
        MergeHelperNeighbors_merge_fields_from_ &
        operator=(MergeHelperNeighbors_merge_fields_from_ &&) noexcept = default;
        MergeHelperNeighbors_merge_fields_from_(const MergeHelperNeighbors_merge_fields_from_ &) = delete;
        MergeHelperNeighbors_merge_fields_from_ &operator=(const MergeHelperNeighbors_merge_fields_from_ &) = delete;

        ::protocyte::Status copy_from(const MergeHelperNeighbors_merge_fields_from_ &source) noexcept {
            if (this == &source) {
                return {};
            }
            MergeHelperNeighbors_merge_fields_from_ staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const MergeHelperNeighbors_merge_fields_from_ &source,
                                      MergeHelperNeighbors_merge_fields_from_ &staging_message) noexcept {
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

        ::protocyte::Result<MergeHelperNeighbors_merge_fields_from_> clone() const noexcept {
            auto output = MergeHelperNeighbors_merge_fields_from_::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(MergeHelperNeighbors_merge_fields_from_ &output) const noexcept {
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
        static void reset_for_reuse_(MergeHelperNeighbors_merge_fields_from_ &value, Context &ctx) noexcept {
            value.~MergeHelperNeighbors_merge_fields_from_();
            new (&value) MergeHelperNeighbors_merge_fields_from_ {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const MergeHelperNeighbors_merge_fields_from_ &source) noexcept {
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

        template<::protocyte::ReaderLike Reader> static ::protocyte::Result<MergeHelperNeighbors_merge_fields_from_>
        parse(Context &ctx, Reader &reader) noexcept {
            auto output = MergeHelperNeighbors_merge_fields_from_::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<MergeHelperNeighbors_merge_fields_from_>
        parse(Context &ctx, ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, MergeHelperNeighbors_merge_fields_from_ &output) noexcept {
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
                    {
                        const auto decoded_value = ::protocyte::read_int32_field(reader, wire_type, field_number);
                        if (!decoded_value) {
                            return decoded_value.status();
                        }
                        value_ = *decoded_value;
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

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#elif defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
    template<typename Config> struct [[deprecated]] LegacyPayload {
        using Context = typename Config::Context;
        explicit LegacyPayload(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static LegacyPayload create(Context &ctx) noexcept { return LegacyPayload {ctx}; }
        Context *context() const noexcept { return ctx_; }
        LegacyPayload(LegacyPayload &&) noexcept = default;
        LegacyPayload &operator=(LegacyPayload &&) noexcept = default;
        LegacyPayload(const LegacyPayload &) = delete;
        LegacyPayload &operator=(const LegacyPayload &) = delete;

        ::protocyte::Status copy_from(const LegacyPayload &source) noexcept {
            if (this == &source) {
                return {};
            }
            LegacyPayload staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const LegacyPayload &source, LegacyPayload &staging_message) noexcept {
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

        ::protocyte::Result<LegacyPayload> clone() const noexcept {
            auto output = LegacyPayload::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(LegacyPayload &output) const noexcept {
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
        static void reset_for_reuse_(LegacyPayload &value, Context &ctx) noexcept {
            value.~LegacyPayload();
            new (&value) LegacyPayload {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const LegacyPayload &source) noexcept {
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
        static ::protocyte::Result<LegacyPayload> parse(Context &ctx, Reader &reader) noexcept {
            auto output = LegacyPayload::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<LegacyPayload> parse(Context &ctx,
                                                        ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, LegacyPayload &output) noexcept {
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
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#elif defined(_MSC_VER)
#pragma warning(pop)
#endif

#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#elif defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
    template<typename Config> struct DeprecationCarrier {
        using Context = typename Config::Context;
        enum struct FieldNumber : ::protocyte::u32 {
            legacy_mode = 1u,
            legacy_payload = 2u,
        };

        explicit DeprecationCarrier(Context &ctx) noexcept: ctx_ {&ctx}, unknown_fields_ {&ctx} {}

        static DeprecationCarrier create(Context &ctx) noexcept { return DeprecationCarrier {ctx}; }
        Context *context() const noexcept { return ctx_; }
        DeprecationCarrier(DeprecationCarrier &&) noexcept = default;
        DeprecationCarrier &operator=(DeprecationCarrier &&) noexcept = default;
        DeprecationCarrier(const DeprecationCarrier &) = delete;
        DeprecationCarrier &operator=(const DeprecationCarrier &) = delete;

        ::protocyte::Status copy_from(const DeprecationCarrier &source) noexcept {
            if (this == &source) {
                return {};
            }
            DeprecationCarrier staging_message {*ctx_};
            return copy_from(source, staging_message);
        }

        ::protocyte::Status copy_from(const DeprecationCarrier &source, DeprecationCarrier &staging_message) noexcept {
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

        ::protocyte::Result<DeprecationCarrier> clone() const noexcept {
            auto output = DeprecationCarrier::create(*ctx_);
            if (const auto st = clone(output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        ::protocyte::Status clone(DeprecationCarrier &output) const noexcept {
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
        static void reset_for_reuse_(DeprecationCarrier &value, Context &ctx) noexcept {
            value.~DeprecationCarrier();
            new (&value) DeprecationCarrier {ctx};
        }

        ::protocyte::Status copy_from_in_place_(const DeprecationCarrier &source) noexcept {
            if (const auto st = set_legacy_mode_raw(source.legacy_mode_raw()); !st) {
                return st;
            }
            if (source.has_legacy_payload()) {
                const auto ensured_legacy_payload = ensure_legacy_payload();
                if (!ensured_legacy_payload) {
                    return ::protocyte::with_field(ensured_legacy_payload.status(),
                                                   static_cast<::protocyte::u32>(FieldNumber::legacy_payload));
                }
                if (const auto st = ensured_legacy_payload->copy_from(*source.legacy_payload()); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::legacy_payload));
                }
            } else {
                clear_legacy_payload();
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

        constexpr ::protocyte::i32 legacy_mode_raw() const noexcept { return legacy_mode_; }
        constexpr ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyMode
        legacy_mode() const noexcept {
            return static_cast<::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyMode>(
                legacy_mode_);
        }
        ::protocyte::Status set_legacy_mode_raw(const ::protocyte::i32 value) noexcept {
            legacy_mode_ = value;
            return {};
        }
        ::protocyte::Status set_legacy_mode(
            const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyMode value) noexcept {
            return set_legacy_mode_raw(static_cast<::protocyte::i32>(value));
        }
        constexpr void clear_legacy_mode() noexcept { legacy_mode_ = {}; }

        bool has_legacy_payload() const noexcept { return legacy_payload_.has_value(); }
        const ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyPayload<Config> *
        legacy_payload() const noexcept {
            return has_legacy_payload() ? legacy_payload_.operator->() : nullptr;
        }
        ::protocyte::Result<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyPayload<Config> &>
        ensure_legacy_payload() noexcept {
            if (legacy_payload_.has_value()) {
                return *legacy_payload_;
            }
            if (const auto st = legacy_payload_.emplace(*ctx_); !st) {
                return ::protocyte::unexpected(
                    ::protocyte::with_field(st.error(), static_cast<::protocyte::u32>(FieldNumber::legacy_payload)));
            }
            return *legacy_payload_;
        }
        void clear_legacy_payload() noexcept { legacy_payload_.reset(); }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Result<DeprecationCarrier> parse(Context &ctx, Reader &reader) noexcept {
            auto output = DeprecationCarrier::create(ctx);
            if (const auto st = parse(reader, output); !st) {
                return ::protocyte::unexpected(st.error());
            }
            return output;
        }

        static ::protocyte::Result<DeprecationCarrier> parse(Context &ctx,
                                                             ::protocyte::Span<const ::protocyte::u8> input) noexcept {
            const auto checked_input = ::protocyte::checked_span_of(input);
            if (!checked_input) {
                return ::protocyte::unexpected(checked_input.error());
            }
            ::protocyte::SliceReader reader {checked_input->data(), checked_input->size()};
            return parse(ctx, reader);
        }

        template<::protocyte::ReaderLike Reader>
        static ::protocyte::Status parse(Reader &reader, DeprecationCarrier &output) noexcept {
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
                case FieldNumber::legacy_mode: {
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
                    const auto decoded_legacy_mode = ::protocyte::read_enum_field(reader, wire_type, field_number);
                    if (!decoded_legacy_mode) {
                        return decoded_legacy_mode.status();
                    }
                    legacy_mode_ = *decoded_legacy_mode;
                    break;
                }
                case FieldNumber::legacy_payload: {
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
                    ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyPayload<Config>
                        legacy_payload_value {*ctx_};
                    if (legacy_payload_.has_value()) {
                        if (const auto st = legacy_payload_value.copy_from(*legacy_payload_); !st) {
                            return st;
                        }
                    }
                    if (const auto st = ::protocyte::read_message_partial<Config>(*ctx_, reader, field_number,
                                                                                  legacy_payload_value);
                        !st) {
                        return st;
                    }
                    if (const auto st = legacy_payload_.emplace(::protocyte::move(legacy_payload_value)); !st) {
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
            if (legacy_mode_ != 0) {
                if (const auto st = ::protocyte::write_enum_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::legacy_mode), legacy_mode_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::legacy_mode));
                }
            }
            if (legacy_payload_.has_value()) {
                if (const auto st = ::protocyte::write_message_field(
                        writer, static_cast<::protocyte::u32>(FieldNumber::legacy_payload), *legacy_payload_);
                    !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::legacy_payload));
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
            if (legacy_mode_ != 0) {
                const auto st_size = ::protocyte::add_size(
                    total, ::protocyte::tag_size(static_cast<::protocyte::u32>(FieldNumber::legacy_mode)) +
                               ::protocyte::varint_size(static_cast<::protocyte::u64>(legacy_mode_)));
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::legacy_mode)));
                }
                total = *st_size;
            }
            if (legacy_payload_.has_value()) {
                const auto field_size_legacy_payload = ::protocyte::message_field_size(
                    static_cast<::protocyte::u32>(FieldNumber::legacy_payload), *legacy_payload_);
                if (!field_size_legacy_payload) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        field_size_legacy_payload.error(), static_cast<::protocyte::u32>(FieldNumber::legacy_payload)));
                }
                const auto st_size = ::protocyte::add_size(total, *field_size_legacy_payload);
                if (!st_size) {
                    return ::protocyte::unexpected(::protocyte::with_field(
                        st_size.error(), static_cast<::protocyte::u32>(FieldNumber::legacy_payload)));
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
            if (legacy_payload_.has_value()) {
                if (const auto st = legacy_payload_->validate(); !st) {
                    return ::protocyte::with_field(st, static_cast<::protocyte::u32>(FieldNumber::legacy_payload));
                }
            }
            return {};
        }
    protected:
        Context *ctx_;
        PROTOCYTE_NO_UNIQUE_ADDRESS ::protocyte::UnknownFieldStorage<Config> unknown_fields_;
        ::protocyte::i32 legacy_mode_ {};
        typename Config::template Optional<
            ::protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f::LegacyPayload<Config>>
            legacy_payload_;
    };
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#elif defined(_MSC_VER)
#pragma warning(pop)
#endif

} // namespace protocyte_escaped_5f5061636b616765::protocyte_escaped_5f5f4c494e455f5f

#endif // PROTOCYTE_GENERATED_RESERVED_IDENTIFIERS_PROTO_1427A5F03FB8_HPP
