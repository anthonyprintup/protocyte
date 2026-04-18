from __future__ import annotations


def runtime_files(prefix: str = "protocyte/runtime") -> dict[str, str]:
    normalized = prefix.strip("/") or "protocyte/runtime"
    return {
        f"{normalized}/runtime.hpp": RUNTIME_HPP,
        f"{normalized}/runtime.cpp": RUNTIME_CPP,
    }


RUNTIME_HPP = r"""#pragma once

#ifndef PROTOCYTE_RUNTIME_RUNTIME_HPP
#define PROTOCYTE_RUNTIME_RUNTIME_HPP

#include <bit>
#include <cstddef>
#include <cstdint>
#include <new>

namespace protocyte {

    using i8 = ::std::int8_t;
    using u8 = ::std::uint8_t;
    using i16 = ::std::int16_t;
    using u16 = ::std::uint16_t;
    using i32 = ::std::int32_t;
    using u32 = ::std::uint32_t;
    using i64 = ::std::int64_t;
    using u64 = ::std::uint64_t;
    using f32 = float;
    using f64 = double;
    using isize = ::std::ptrdiff_t;
    using usize = ::std::size_t;
    using iptr = ::std::intptr_t;
    using uptr = ::std::uintptr_t;
    using ptr = uptr;

    template<class T> struct RemoveReference {
        using Type = T;
    };

    template<class T> struct RemoveReference<T &> {
        using Type = T;
    };

    template<class T> struct RemoveReference<T &&> {
        using Type = T;
    };

    template<class T> constexpr typename RemoveReference<T>::Type &&move(T &&value) noexcept {
        return static_cast<typename RemoveReference<T>::Type &&>(value);
    }

    template<class T> constexpr T &&forward(typename RemoveReference<T>::Type &value) noexcept {
        return static_cast<T &&>(value);
    }

    template<class T> constexpr T &&forward(typename RemoveReference<T>::Type &&value) noexcept {
        return static_cast<T &&>(value);
    }

    enum class ErrorCode : u32 {
        ok = 0,
        no_memory = 1,
        invalid_argument = 2,
        malformed_varint = 3,
        unexpected_eof = 4,
        invalid_wire_type = 5,
        invalid_utf8 = 6,
        recursion_limit = 7,
        size_limit = 8,
        count_limit = 9,
        integer_overflow = 10,
        unsupported = 11,
    };

    enum class WireType : u32 {
        VARINT = 0u,
        I64 = 1u,
        LEN = 2u,
        SGROUP = 3u,
        EGROUP = 4u,
        I32 = 5u,
    };

    struct Error {
        ErrorCode code {};
        usize offset {};
        u32 field_number {};
    };

    struct Status {
        constexpr Status() noexcept = default;
        constexpr explicit Status(const Error error) noexcept: error_ {error} {}

        static constexpr Status ok() noexcept { return {}; }
        static constexpr Status error(const ErrorCode code, const usize offset = {}, const u32 field_number = {}) noexcept {
            return Status {Error {.code = code, .offset = offset, .field_number = field_number}};
        }

        constexpr bool is_ok() const noexcept { return error_.code == ErrorCode::ok; }
        constexpr explicit operator bool() const noexcept { return is_ok(); }
        constexpr Error error() const noexcept { return error_; }

    protected:
        Error error_;
    };

    template<class T> struct Ref {
        constexpr explicit Ref(T &value) noexcept: ptr_{&value} {}
        constexpr T &get() const noexcept { return *ptr_; }
        constexpr operator T &() const noexcept { return *ptr_; }
        constexpr T *operator->() const noexcept { return ptr_; }

    protected:
        T *ptr_;
    };

    template<class T> struct Result {
        static Result ok(T value) noexcept { return Result {protocyte::move(value)}; }
        static Result err(const Error error) noexcept { return Result {error}; }
        static Result err(const ErrorCode code, const usize offset = {}, const u32 field_number = {}) noexcept {
            return Result {Error {.code = code, .offset = offset, .field_number = field_number}};
        }

        Result(Result &&other) noexcept: ok_{other.ok_} {
            if (ok_) {
                new (&value_) T {protocyte::move(other.value_)};
            } else {
                error_ = other.error_;
            }
        }

        Result &operator=(Result &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            this->~Result();
            ok_ = other.ok_;
            if (ok_) {
                new (&value_) T {protocyte::move(other.value_)};
            } else {
                error_ = other.error_;
            }
            return *this;
        }

        Result(const Result &) = delete;
        Result &operator=(const Result &) = delete;

        ~Result() noexcept {
            if (ok_) {
                value_.~T();
            }
        }

        constexpr bool is_ok() const noexcept { return ok_; }
        constexpr explicit operator bool() const noexcept { return ok_; }
        T &value() & noexcept { return value_; }
        const T &value() const & noexcept { return value_; }
        T &&take_value() && noexcept { return protocyte::move(value_); }
        Error error() const noexcept { return ok_ ? Error {} : error_; }
        Status status() const noexcept { return ok_ ? Status {} : Status {error_}; }

    protected:
        explicit Result(T &&value) noexcept: ok_{true} { new (&value_) T {protocyte::move(value)}; }
        explicit Result(const Error error) noexcept: ok_{false}, error_{error} {}

        bool ok_;
        union {
            T value_;
            Error error_;
        };
    };

    struct ByteView {
        const u8 *data {};
        usize size {};
    };

    struct MutableByteView {
        u8 *data {};
        usize size {};
    };

    constexpr bool bytes_equal(const ByteView lhs, const ByteView rhs) noexcept {
        if (lhs.size != rhs.size) {
            return false;
        }
        for (usize i {}; i < lhs.size; ++i) {
            if (lhs.data[i] != rhs.data[i]) {
                return false;
            }
        }
        return true;
    }

    constexpr bool bytes_zero(const ByteView view) noexcept {
        for (usize i {}; i < view.size; ++i) {
            if (view.data[i] != 0u) {
                return false;
            }
        }
        return true;
    }

    constexpr u64 fnv1a(const ByteView view) noexcept {
        u64 hash {1469598103934665603ull};
        for (usize i {}; i < view.size; ++i) {
            hash ^= static_cast<u64>(view.data[i]);
            hash *= 1099511628211ull;
        }
        return hash;
    }

    constexpr Status checked_add(const usize lhs, const usize rhs, usize *out) noexcept {
        const auto value = lhs + rhs;
        if (value < lhs) {
            return Status::error(ErrorCode::integer_overflow);
        }
        *out = value;
        return {};
    }

    constexpr Status checked_mul(const usize lhs, const usize rhs, usize *out) noexcept {
        if (lhs != 0u && rhs > static_cast<usize>(~static_cast<usize>(0u)) / lhs) {
            return Status::error(ErrorCode::integer_overflow);
        }
        *out = lhs * rhs;
        return {};
    }

    struct Limits {
        static constexpr usize kDefaultMaxRecursionDepth = 100u;
        static constexpr usize kDefaultMaxMessageBytes = 0x7fffffffu;
        static constexpr usize kDefaultMaxStringBytes = 0x7fffffffu;
        static constexpr usize kDefaultMaxRepeatedCount = 0x7fffffffu;
        static constexpr usize kDefaultMaxMapEntries = 0x7fffffffu;

        usize max_recursion_depth {kDefaultMaxRecursionDepth};
        usize max_message_bytes {kDefaultMaxMessageBytes};
        usize max_string_bytes {kDefaultMaxStringBytes};
        usize max_repeated_count {kDefaultMaxRepeatedCount};
        usize max_map_entries {kDefaultMaxMapEntries};
    };

    struct Allocator {
        void *state {};
        void *(*allocate)(void *state, usize size, usize alignment) {};
        void (*deallocate)(void *state, void *ptr, usize size, usize alignment) {};
    };

    template<class T> struct Optional;

    template<class T, class Config> struct Vector;

    template<class Config> struct Bytes;

    template<class Config> struct String;

    template<class T, class Config> struct Box;

    template<class K, class V, class Config> struct HashMap;

    struct DefaultConfig {
        struct Context {
            Allocator allocator;
            Limits limits;
        };

        template<class T> using Vector = protocyte::Vector<T, DefaultConfig>;
        template<class K, class V> using Map = protocyte::HashMap<K, V, DefaultConfig>;
        template<class T> using Box = protocyte::Box<T, DefaultConfig>;
        template<class T> using Optional = protocyte::Optional<T>;
        using Bytes = protocyte::Bytes<DefaultConfig>;
        using String = protocyte::String<DefaultConfig>;

        static void *allocate(Context &ctx, const usize size, const usize alignment) noexcept {
            if (!size) {
                return nullptr;
            }
            if (ctx.allocator.allocate == nullptr) {
                return nullptr;
            }
            return ctx.allocator.allocate(ctx.allocator.state, size, alignment);
        }

        static void deallocate(Context &ctx, void *ptr, const usize size, const usize alignment) noexcept {
            if (ptr != nullptr && ctx.allocator.deallocate != nullptr) {
                ctx.allocator.deallocate(ctx.allocator.state, ptr, size, alignment);
            }
        }

        template<class T> static u64 hash(const T &value) noexcept {
            return fnv1a(ByteView {.data = reinterpret_cast<const u8 *>(&value), .size = sizeof(T)});
        }

        template<class T> static bool equal(const T &lhs, const T &rhs) noexcept { return lhs == rhs; }

        static u64 hash(const Bytes &value) noexcept;
        static u64 hash(const String &value) noexcept;
        static bool equal(const Bytes &lhs, const Bytes &rhs) noexcept;
        static bool equal(const String &lhs, const String &rhs) noexcept;
    };

    template<class T> struct Optional {
        Optional() noexcept = default;
        Optional(Optional &&other) noexcept {
            if (other.has_) {
                new (ptr()) T {protocyte::move(*other.ptr())};
                has_ = true;
                other.reset();
            }
        }
        Optional &operator=(Optional &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            reset();
            if (other.has_) {
                new (ptr()) T {protocyte::move(*other.ptr())};
                has_ = true;
                other.reset();
            }
            return *this;
        }
        Optional(const Optional &) = delete;
        Optional &operator=(const Optional &) = delete;
        ~Optional() noexcept { reset(); }

        template<class... Args> Status emplace(Args &&...args) noexcept {
            reset();
            new (ptr()) T {protocyte::forward<Args>(args)...};
            has_ = true;
            return {};
        }

        void reset() noexcept {
            if (has_) {
                ptr()->~T();
                has_ = false;
            }
        }

        bool has_value() const noexcept { return has_; }
        T &value() noexcept { return *ptr(); }
        const T &value() const noexcept { return *ptr(); }

    protected:
        T *ptr() noexcept { return reinterpret_cast<T *>(&storage_[0]); }
        const T *ptr() const noexcept { return reinterpret_cast<const T *>(&storage_[0]); }

        bool has_ {};
        alignas(T) unsigned char storage_[sizeof(T)];
    };

    template<class T, class Config> struct Vector {
        using Context = typename Config::Context;

        explicit Vector(Context *ctx = nullptr) noexcept: ctx_{ctx} {}
        Vector(Vector &&other) noexcept:
            ctx_{other.ctx_}, data_{other.data_}, size_{other.size_}, capacity_{other.capacity_} {
            other.data_ = nullptr;
            other.size_ = {};
            other.capacity_ = {};
        }
        Vector &operator=(Vector &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            destroy();
            ctx_ = other.ctx_;
            data_ = other.data_;
            size_ = other.size_;
            capacity_ = other.capacity_;
            other.data_ = nullptr;
            other.size_ = {};
            other.capacity_ = {};
            return *this;
        }
        Vector(const Vector &) = delete;
        Vector &operator=(const Vector &) = delete;
        ~Vector() noexcept { destroy(); }

        void bind(Context *ctx) noexcept { ctx_ = ctx; }
        usize size() const noexcept { return size_; }
        usize capacity() const noexcept { return capacity_; }
        bool empty() const noexcept { return !size_; }
        T *data() noexcept { return data_; }
        const T *data() const noexcept { return data_; }
        T &operator[](const usize index) noexcept { return data_[index]; }
        const T &operator[](const usize index) const noexcept { return data_[index]; }

        void clear() noexcept {
            for (usize i {}; i < size_; ++i) { data_[i].~T(); }
            size_ = {};
        }

        Status reserve(const usize requested) noexcept {
            if (requested <= capacity_) {
                return {};
            }
            if (ctx_ == nullptr) {
                return Status::error(ErrorCode::invalid_argument);
            }
            usize bytes {};
            if (const auto st = checked_mul(requested, sizeof(T), &bytes); !st) {
                return st;
            }
            auto *raw = Config::allocate(*ctx_, bytes, alignof(T));
            if (raw == nullptr) {
                return Status::error(ErrorCode::no_memory);
            }
            auto *next = static_cast<T *>(raw);
            for (usize i {}; i < size_; ++i) {
                new (&next[i]) T {protocyte::move(data_[i])};
                data_[i].~T();
            }
            if (data_ != nullptr) {
                Config::deallocate(*ctx_, data_, capacity_ * sizeof(T), alignof(T));
            }
            data_ = next;
            capacity_ = requested;
            return {};
        }

        template<class... Args> Result<Ref<T>> emplace_back(Args &&...args) noexcept {
            if (size_ == capacity_) {
                const usize next_capacity = !capacity_ ? 4u : capacity_ * 2u;
                if (const auto st = reserve(next_capacity); !st) {
                    return Result<Ref<T>>::err(st.error());
                }
            }
            new (&data_[size_]) T {protocyte::forward<Args>(args)...};
            Ref<T> ref {data_[size_]};
            ++size_;
            return Result<Ref<T>>::ok(ref);
        }

        Status push_back(const T &value) noexcept {
            auto result = emplace_back(value);
            return result.status();
        }

        Status push_back(T &&value) noexcept {
            auto result = emplace_back(protocyte::move(value));
            return result.status();
        }

        Status resize_default(const usize count) noexcept {
            if (count < size_) {
                while (size_ > count) {
                    --size_;
                    data_[size_].~T();
                }
                return {};
            }
            if (const auto st = reserve(count); !st) {
                return st;
            }
            while (size_ < count) {
                new (&data_[size_]) T {};
                ++size_;
            }
            return {};
        }

    protected:
        void destroy() noexcept {
            clear();
            if (data_ != nullptr && ctx_ != nullptr) {
                Config::deallocate(*ctx_, data_, capacity_ * sizeof(T), alignof(T));
            }
            data_ = nullptr;
            capacity_ = {};
        }

        Context *ctx_ {};
        T *data_ {};
        usize size_ {};
        usize capacity_ {};
    };

    template<class Config> struct Bytes {
        using Context = typename Config::Context;

        explicit Bytes(Context *ctx = nullptr) noexcept: ctx_{ctx}, bytes_{ctx} {}
        Bytes(Bytes &&other) noexcept: ctx_{other.ctx_}, bytes_{protocyte::move(other.bytes_)} {}
        Bytes &operator=(Bytes &&other) noexcept {
            ctx_ = other.ctx_;
            bytes_ = protocyte::move(other.bytes_);
            return *this;
        }
        Bytes(const Bytes &) = delete;
        Bytes &operator=(const Bytes &) = delete;

        ByteView view() const noexcept { return {.data = bytes_.data(), .size = bytes_.size()}; }
        const u8 *data() const noexcept { return bytes_.data(); }
        usize size() const noexcept { return bytes_.size(); }
        bool empty() const noexcept { return bytes_.empty(); }
        void clear() noexcept { bytes_.clear(); }
        void bind(Context *ctx) noexcept {
            ctx_ = ctx;
            bytes_.bind(ctx);
        }

        Status assign(const ByteView view) noexcept {
            Bytes temp{ctx_};
            if (const auto st = temp.bytes_.reserve(view.size); !st) {
                return st;
            }
            for (usize i {}; i < view.size; ++i) {
                if (const auto st = temp.bytes_.push_back(view.data[i]); !st) {
                    return st;
                }
            }
            *this = protocyte::move(temp);
            return {};
        }

    protected:
        Context *ctx_;
        typename Config::template Vector<u8> bytes_;
    };

    template<class Config> struct String {
        using Context = typename Config::Context;

        explicit String(Context *ctx = nullptr) noexcept: bytes_{ctx} {}
        String(String &&other) noexcept: bytes_{protocyte::move(other.bytes_)} {}
        String &operator=(String &&other) noexcept {
            bytes_ = protocyte::move(other.bytes_);
            return *this;
        }
        String(const String &) = delete;
        String &operator=(const String &) = delete;

        ByteView view() const noexcept { return bytes_.view(); }
        const u8 *data() const noexcept { return bytes_.data(); }
        usize size() const noexcept { return bytes_.size(); }
        bool empty() const noexcept { return bytes_.empty(); }
        void clear() noexcept { bytes_.clear(); }

        Status assign(const ByteView view) noexcept {
            if (!validate_utf8(view)) {
                return Status::error(ErrorCode::invalid_utf8);
            }
            return bytes_.assign(view);
        }

    protected:
        static bool validate_utf8(const ByteView view) noexcept {
            usize i {};
            while (i < view.size) {
                const u8 byte = view.data[i];
                if (byte < 0x80u) {
                    ++i;
                    continue;
                }
                usize need {};
                u32 code {};
                if ((byte & 0xE0u) == 0xC0u) {
                    need = 1u;
                    code = byte & 0x1Fu;
                    if (!code) {
                        return false;
                    }
                } else if ((byte & 0xF0u) == 0xE0u) {
                    need = 2u;
                    code = byte & 0x0Fu;
                } else if ((byte & 0xF8u) == 0xF0u) {
                    need = 3u;
                    code = byte & 0x07u;
                } else {
                    return false;
                }
                if (i + need >= view.size) {
                    return false;
                }
                for (usize j {}; j < need; ++j) {
                    const u8 next = view.data[i + 1u + j];
                    if ((next & 0xC0u) != 0x80u) {
                        return false;
                    }
                    code = (code << 6u) | static_cast<u32>(next & 0x3Fu);
                }
                if ((need == 2u && code < 0x800u) || (need == 3u && code < 0x10000u)) {
                    return false;
                }
                if (code > 0x10FFFFu || (code >= 0xD800u && code <= 0xDFFFu)) {
                    return false;
                }
                i += need + 1u;
            }
            return true;
        }

        typename Config::Bytes bytes_;
    };

    template<class T, class Config> struct Box {
        using Context = typename Config::Context;

        explicit Box(Context *ctx = nullptr) noexcept: ctx_{ctx} {}
        Box(Box &&other) noexcept: ctx_{other.ctx_}, ptr_{other.ptr_} { other.ptr_ = nullptr; }
        Box &operator=(Box &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            reset();
            ctx_ = other.ctx_;
            ptr_ = other.ptr_;
            other.ptr_ = nullptr;
            return *this;
        }
        Box(const Box &) = delete;
        Box &operator=(const Box &) = delete;
        ~Box() noexcept { reset(); }

        bool has_value() const noexcept { return ptr_ != nullptr; }
        T &value() noexcept { return *ptr_; }
        const T &value() const noexcept { return *ptr_; }

        Result<Ref<T>> ensure() noexcept {
            if (ptr_ != nullptr) {
                return Result<Ref<T>>::ok(Ref<T> {*ptr_});
            }
            if (ctx_ == nullptr) {
                return Result<Ref<T>>::err(ErrorCode::invalid_argument);
            }
            auto *raw = Config::allocate(*ctx_, sizeof(T), alignof(T));
            if (raw == nullptr) {
                return Result<Ref<T>>::err(ErrorCode::no_memory);
            }
            ptr_ = new (raw) T {*ctx_};
            return Result<Ref<T>>::ok(Ref<T> {*ptr_});
        }

        void reset() noexcept {
            if (ptr_ != nullptr && ctx_ != nullptr) {
                ptr_->~T();
                Config::deallocate(*ctx_, ptr_, sizeof(T), alignof(T));
                ptr_ = nullptr;
            }
        }

    protected:
        Context *ctx_ {};
        T *ptr_ {};
    };

    template<class K, class V, class Config> struct HashMap {
        struct Bucket {
            bool occupied {};
            Optional<K> key;
            Optional<V> value;
        };

        using Context = typename Config::Context;

        explicit HashMap(Context *ctx = nullptr) noexcept: ctx_{ctx}, buckets_{ctx} {}
        HashMap(HashMap &&other) noexcept:
            ctx_{other.ctx_}, buckets_{protocyte::move(other.buckets_)}, size_{other.size_} {
            other.size_ = {};
        }
        HashMap &operator=(HashMap &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            ctx_ = other.ctx_;
            buckets_ = protocyte::move(other.buckets_);
            size_ = other.size_;
            other.size_ = {};
            return *this;
        }
        HashMap(const HashMap &) = delete;
        HashMap &operator=(const HashMap &) = delete;

        usize size() const noexcept { return size_; }
        bool empty() const noexcept { return !size_; }
        void clear() noexcept {
            for (usize i {}; i < buckets_.size(); ++i) {
                buckets_[i].occupied = false;
                buckets_[i].key.reset();
                buckets_[i].value.reset();
            }
            size_ = {};
        }

        Status reserve(const usize count) noexcept {
            usize desired {8u};
            while (desired < count * 2u) { desired *= 2u; }
            if (desired <= buckets_.size()) {
                return {};
            }
            HashMap next{ctx_};
            if (const auto st = next.buckets_.resize_default(desired); !st) {
                return st;
            }
            for (usize i {}; i < buckets_.size(); ++i) {
                if (buckets_[i].occupied) {
                    if (const auto st = next.insert_or_assign(protocyte::move(buckets_[i].key.value()),
                                                              protocyte::move(buckets_[i].value.value()));
                        !st) {
                        return st;
                    }
                }
            }
            *this = protocyte::move(next);
            return {};
        }

        Status insert_or_assign(K &&key, V &&value) noexcept {
            if (const auto st = ensure_capacity_for_one_more(); !st) {
                return st;
            }
            usize index {Config::hash(key) & (buckets_.size() - 1u)};
            for (;;) {
                auto &bucket = buckets_[index];
                if (!bucket.occupied) {
                    bucket.occupied = true;
                    bucket.key.emplace(protocyte::move(key));
                    bucket.value.emplace(protocyte::move(value));
                    ++size_;
                    return {};
                }
                if (Config::equal(bucket.key.value(), key)) {
                    bucket.value.reset();
                    bucket.value.emplace(protocyte::move(value));
                    return {};
                }
                index = (index + 1u) & (buckets_.size() - 1u);
            }
        }

        template<class Fn> Status for_each(Fn &&fn) const noexcept {
            for (usize i {}; i < buckets_.size(); ++i) {
                if (const Bucket &bucket = buckets_[i]; bucket.occupied) {
                    if (const auto st = fn(bucket.key.value(), bucket.value.value()); !st) {
                        return st;
                    }
                }
            }
            return {};
        }

    protected:
        Status ensure_capacity_for_one_more() noexcept {
            if (!buckets_.size() || ((size_ + 1u) * 10u) >= buckets_.size() * 7u) {
                return reserve(size_ + 1u);
            }
            return {};
        }

        Context *ctx_ {};
        typename Config::template Vector<Bucket> buckets_;
        usize size_ {};
    };

    inline u64 DefaultConfig::hash(const Bytes &value) noexcept { return fnv1a(value.view()); }

    inline u64 DefaultConfig::hash(const String &value) noexcept { return fnv1a(value.view()); }

    inline bool DefaultConfig::equal(const Bytes &lhs, const Bytes &rhs) noexcept {
        return bytes_equal(lhs.view(), rhs.view());
    }

    inline bool DefaultConfig::equal(const String &lhs, const String &rhs) noexcept {
        return bytes_equal(lhs.view(), rhs.view());
    }

    struct SliceReader {
        SliceReader(const u8 *data, const usize size) noexcept: data_{data}, size_{size} {}
        bool eof() const noexcept { return pos_ >= size_; }
        usize position() const noexcept { return pos_; }
        Result<u8> read_byte() noexcept {
            if (pos_ >= size_) {
                return Result<u8>::err(ErrorCode::unexpected_eof, pos_);
            }
            return Result<u8>::ok(data_[pos_++]);
        }
        Status read(u8 *out, const usize count) noexcept {
            if (count > size_ - pos_) {
                return Status::error(ErrorCode::unexpected_eof, pos_);
            }
            for (usize i {}; i < count; ++i) { out[i] = data_[pos_ + i]; }
            pos_ += count;
            return {};
        }
        Status skip(const usize count) noexcept {
            if (count > size_ - pos_) {
                return Status::error(ErrorCode::unexpected_eof, pos_);
            }
            pos_ += count;
            return {};
        }

    protected:
        const u8 *data_;
        usize size_;
        usize pos_ {};
    };

    struct ReaderRef {
        template<class Reader> explicit ReaderRef(Reader &reader) noexcept:
            reader_{&reader},
            eof_{&eof_impl<Reader>},
            position_{&position_impl<Reader>},
            read_byte_{&read_byte_impl<Reader>},
            read_{&read_impl<Reader>},
            skip_{&skip_impl<Reader>} {}

        bool eof() const noexcept { return eof_(reader_); }
        usize position() const noexcept { return position_(reader_); }
        Result<u8> read_byte() noexcept { return read_byte_(reader_); }
        Status read(u8 *out, const usize count) noexcept { return read_(reader_, out, count); }
        Status skip(const usize count) noexcept { return skip_(reader_, count); }

    protected:
        template<class Reader> static bool eof_impl(void *reader) noexcept {
            return static_cast<Reader *>(reader)->eof();
        }

        template<class Reader> static usize position_impl(void *reader) noexcept {
            return static_cast<Reader *>(reader)->position();
        }

        template<class Reader> static Result<u8> read_byte_impl(void *reader) noexcept {
            return static_cast<Reader *>(reader)->read_byte();
        }

        template<class Reader> static Status read_impl(void *reader, u8 *out, const usize count) noexcept {
            return static_cast<Reader *>(reader)->read(out, count);
        }

        template<class Reader> static Status skip_impl(void *reader, const usize count) noexcept {
            return static_cast<Reader *>(reader)->skip(count);
        }

        void *reader_;
        bool (*eof_)(void *) noexcept;
        usize (*position_)(void *) noexcept;
        Result<u8> (*read_byte_)(void *) noexcept;
        Status (*read_)(void *, u8 *, usize) noexcept;
        Status (*skip_)(void *, usize) noexcept;
    };

    template<class Reader> struct LimitedReader {
        LimitedReader(Reader &inner, const usize remaining) noexcept:
            inner_{&inner}, remaining_{remaining} {}
        bool eof() const noexcept { return !remaining_; }
        usize position() const noexcept { return pos_; }
        Result<u8> read_byte() noexcept {
            if (!remaining_) {
                return Result<u8>::err(ErrorCode::unexpected_eof, pos_);
            }
            auto byte = inner_->read_byte();
            if (!byte) {
                return Result<u8>::err(byte.error());
            }
            --remaining_;
            ++pos_;
            return byte;
        }
        Status read(u8 *out, const usize count) noexcept {
            if (count > remaining_) {
                return Status::error(ErrorCode::unexpected_eof, pos_);
            }
            if (const auto st = inner_->read(out, count); !st) {
                return st;
            }
            remaining_ -= count;
            pos_ += count;
            return {};
        }
        Status skip(const usize count) noexcept {
            if (count > remaining_) {
                return Status::error(ErrorCode::unexpected_eof, pos_);
            }
            if (const auto st = inner_->skip(count); !st) {
                return st;
            }
            remaining_ -= count;
            pos_ += count;
            return {};
        }
        Status finish() noexcept { return skip(remaining_); }

    protected:
        Reader *inner_;
        usize remaining_;
        usize pos_ {};
    };

    struct SliceWriter {
        SliceWriter(u8 *data, const usize capacity) noexcept: data_{data}, capacity_{capacity} {}
        usize position() const noexcept { return pos_; }
        Status write_byte(const u8 value) noexcept {
            if (pos_ >= capacity_) {
                return Status::error(ErrorCode::size_limit, pos_);
            }
            data_[pos_++] = value;
            return {};
        }
        Status write(const u8 *data, const usize count) noexcept {
            if (count > capacity_ - pos_) {
                return Status::error(ErrorCode::size_limit, pos_);
            }
            for (usize i {}; i < count; ++i) { data_[pos_ + i] = data[i]; }
            pos_ += count;
            return {};
        }

    protected:
        u8 *data_;
        usize capacity_;
        usize pos_ {};
    };

    template<class Reader> Result<u64> read_varint(Reader &reader) noexcept {
        u64 value {};
        u32 shift {};
        for (u32 i {}; i < 10u; ++i) {
            auto byte = reader.read_byte();
            if (!byte) {
                return Result<u64>::err(byte.error());
            }
            value |= (static_cast<u64>(byte.value() & 0x7Fu) << shift);
            if ((byte.value() & 0x80u) == 0u) {
                return Result<u64>::ok(value);
            }
            shift += 7u;
        }
        return Result<u64>::err(ErrorCode::malformed_varint, reader.position());
    }

    template<class Writer> Status write_varint(Writer &writer, u64 value) noexcept {
        while (value >= 0x80u) {
            if (const auto st = writer.write_byte(static_cast<u8>(value | 0x80u)); !st) {
                return st;
            }
            value >>= 7u;
        }
        return writer.write_byte(static_cast<u8>(value));
    }

    constexpr usize varint_size(u64 value) noexcept {
        usize size {1u};
        while (value >= 0x80u) {
            value >>= 7u;
            ++size;
        }
        return size;
    }

    constexpr u32 encode_zigzag32(const i32 value) noexcept {
        return static_cast<u32>((value << 1) ^ (value >> 31));
    }

    constexpr u64 encode_zigzag64(const i64 value) noexcept {
        return static_cast<u64>((value << 1) ^ (value >> 63));
    }

    constexpr i32 decode_zigzag32(const u32 value) noexcept {
        return static_cast<i32>((value >> 1) ^ (~(value & 1u) + 1u));
    }

    constexpr i64 decode_zigzag64(const u64 value) noexcept {
        return static_cast<i64>((value >> 1) ^ (~(value & 1u) + 1u));
    }

    template<class Reader> Result<u32> read_fixed32(Reader &reader) noexcept {
        u8 bytes[4u];
        if (const auto st = reader.read(bytes, 4u); !st) {
            return Result<u32>::err(st.error());
        }
        const auto value = static_cast<u32>(bytes[0]) | (static_cast<u32>(bytes[1]) << 8u) |
                           (static_cast<u32>(bytes[2]) << 16u) | (static_cast<u32>(bytes[3]) << 24u);
        return Result<u32>::ok(value);
    }

    template<class Reader> Result<u64> read_fixed64(Reader &reader) noexcept {
        u8 bytes[8u];
        if (const auto st = reader.read(bytes, 8u); !st) {
            return Result<u64>::err(st.error());
        }
        u64 value {};
        for (u32 i {}; i < 8u; ++i) { value |= static_cast<u64>(bytes[i]) << (i * 8u); }
        return Result<u64>::ok(value);
    }

    template<class Writer> Status write_fixed32(Writer &writer, const u32 value) noexcept {
        u8 bytes[4u] {
            static_cast<u8>(value),
            static_cast<u8>(value >> 8u),
            static_cast<u8>(value >> 16u),
            static_cast<u8>(value >> 24u),
        };
        return writer.write(bytes, 4u);
    }

    template<class Writer> Status write_fixed64(Writer &writer, const u64 value) noexcept {
        u8 bytes[8u] {
            static_cast<u8>(value),
            static_cast<u8>(value >> 8u),
            static_cast<u8>(value >> 16u),
            static_cast<u8>(value >> 24u),
            static_cast<u8>(value >> 32u),
            static_cast<u8>(value >> 40u),
            static_cast<u8>(value >> 48u),
            static_cast<u8>(value >> 56u),
        };
        return writer.write(bytes, 8u);
    }

    template<class Writer>
    Status write_tag(Writer &writer, const u32 field_number, const WireType wire_type) noexcept {
        return write_varint(writer, (static_cast<u64>(field_number) << 3u) | static_cast<u64>(wire_type));
    }

    constexpr usize tag_size(const u32 field_number) noexcept {
        return varint_size(static_cast<u64>(field_number) << 3u);
    }

    template<class Reader> Status skip_group(Reader &reader, u32 start_field_number) noexcept;

    template<class Reader>
    Status skip_field(Reader &reader, const WireType wire_type, const u32 field_number = {}) noexcept {
        switch (wire_type) {
            case WireType::VARINT: {
                auto ignored = read_varint(reader);
                return ignored.status();
            }
            case WireType::I64: return reader.skip(8u);
            case WireType::LEN: {
                auto len = read_varint(reader);
                if (!len) {
                    return len.status();
                }
                return reader.skip(static_cast<usize>(len.value()));
            }
            case WireType::SGROUP: return skip_group(reader, field_number);
            case WireType::EGROUP: return {};
            case WireType::I32: return reader.skip(4u);
            default: return Status::error(ErrorCode::invalid_wire_type, reader.position(), field_number);
        }
    }

    template<class Reader> Status skip_group(Reader &reader, const u32 start_field_number) noexcept {
        for (;;) {
            if (const auto tag = read_varint(reader); !tag) {
                return tag.status();
            } else {
                const auto field = static_cast<u32>(tag.value() >> 3u);
                const auto wire = static_cast<WireType>(tag.value() & 0x7u);
                if (wire == WireType::EGROUP) {
                    if (field != start_field_number) {
                        return Status::error(ErrorCode::invalid_wire_type, reader.position(), field);
                    }
                    return {};
                }
                if (const auto st = skip_field(reader, wire, field); !st) {
                    return st;
                }
            }
        }
    }

    template<class Config, class Reader> Status read_bytes(typename Config::Context &ctx, Reader &reader,
                                                           const usize size, typename Config::Bytes &out) noexcept {
        if (size > ctx.limits.max_string_bytes) {
            return Status::error(ErrorCode::size_limit, reader.position());
        }
        typename Config::Bytes temp{&ctx};
        if (const auto st = temp.assign(ByteView {.data = nullptr, .size = {}}); !st) {
            return st;
        }
        typename Config::template Vector<u8> buffer{&ctx};
        if (const auto st = buffer.reserve(size); !st) {
            return st;
        }
        for (usize i {}; i < size; ++i) {
            auto byte = reader.read_byte();
            if (!byte) {
                return byte.status();
            }
            if (const auto st = buffer.push_back(byte.value()); !st) {
                return st;
            }
        }
        if (const auto st = temp.assign(ByteView {.data = buffer.data(), .size = buffer.size()}); !st) {
            return st;
        }
        out = protocyte::move(temp);
        return {};
    }

    template<class Config, class Reader> Status read_string(typename Config::Context &ctx, Reader &reader,
                                                            const usize size, typename Config::String &out) noexcept {
        if (size > ctx.limits.max_string_bytes) {
            return Status::error(ErrorCode::size_limit, reader.position());
        }
        typename Config::template Vector<u8> buffer{&ctx};
        if (const auto st = buffer.reserve(size); !st) {
            return st;
        }
        for (usize i {}; i < size; ++i) {
            auto byte = reader.read_byte();
            if (!byte) {
                return byte.status();
            }
            if (const auto st = buffer.push_back(byte.value()); !st) {
                return st;
            }
        }
        typename Config::String temp{&ctx};
        if (const auto st = temp.assign(ByteView {.data = buffer.data(), .size = buffer.size()}); !st) {
            return st;
        }
        out = protocyte::move(temp);
        return {};
    }

    template<class Writer> Status write_bytes(Writer &writer, const ByteView view) noexcept {
        if (const auto st = write_varint(writer, static_cast<u64>(view.size)); !st) {
            return st;
        }
        return writer.write(view.data, view.size);
    }

    inline Status add_size(usize *total, const usize value) noexcept { return checked_add(*total, value, total); }

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
    void *hosted_allocate(void *state, usize size, usize alignment) noexcept;
    void hosted_deallocate(void *state, void *ptr, usize size, usize alignment) noexcept;
    inline Allocator hosted_allocator() noexcept {
        return {.state = nullptr, .allocate = hosted_allocate, .deallocate = hosted_deallocate};
    }
#endif

} // namespace protocyte

#endif // PROTOCYTE_RUNTIME_RUNTIME_HPP
"""


RUNTIME_CPP = r"""#include "runtime.hpp"

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
#include <cstdlib>

namespace protocyte {

    void *hosted_allocate(void *, const usize size, usize) noexcept { return std::malloc(size); }

    void hosted_deallocate(void *, void *ptr, const usize, const usize) noexcept { std::free(ptr); }

} // namespace protocyte
#endif
"""
