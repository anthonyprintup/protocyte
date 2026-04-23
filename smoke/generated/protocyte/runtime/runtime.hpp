#pragma once

#ifndef PROTOCYTE_RUNTIME_RUNTIME_HPP
#define PROTOCYTE_RUNTIME_RUNTIME_HPP

#include <bit>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <new>
#include <type_traits>

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

    template<class T> struct Optional;
    template<class E> struct Unexpected;
    template<class T, class E> struct Result;

    template<class T> constexpr ::std::remove_reference_t<T> &&move(T &&value) noexcept {
        return static_cast<::std::remove_reference_t<T> &&>(value);
    }

    template<class T> constexpr T &&forward(::std::remove_reference_t<T> &value) noexcept {
        return static_cast<T &&>(value);
    }

    template<class T> constexpr T &&forward(::std::remove_reference_t<T> &&value) noexcept {
        return static_cast<T &&>(value);
    }

    template<class T> auto declval() noexcept -> T &&;

    template<class F, class... Args> constexpr decltype(auto)
    invoke(F &&f, Args &&...args) noexcept(noexcept(protocyte::forward<F>(f)(protocyte::forward<Args>(args)...))) {
        return protocyte::forward<F>(f)(protocyte::forward<Args>(args)...);
    }

    template<class F, class... Args> using InvokeResult = ::std::invoke_result_t<F, Args...>;

    template<class T> inline constexpr bool is_result = false;

    template<class T, class E> inline constexpr bool is_result<Result<T, E>> = true;

    template<class T>
    concept ResultType = is_result<::std::remove_cvref_t<T>>;

    template<class T> inline constexpr bool is_unexpected = false;

    template<class E> inline constexpr bool is_unexpected<Unexpected<E>> = true;

    template<class T>
    concept UnexpectedType = is_unexpected<::std::remove_cvref_t<T>>;

    template<class T> inline constexpr bool is_optional = false;

    template<class T> inline constexpr bool is_optional<Optional<T>> = true;

    template<class T>
    concept OptionalType = is_optional<::std::remove_cvref_t<T>>;

    template<class T> struct ReverseIterator {
        using value_type = T;
        using difference_type = isize;
        using reference = T &;
        using pointer = T *;

        constexpr ReverseIterator() noexcept = default;
        constexpr explicit ReverseIterator(pointer current) noexcept: current_ {current} {}

        constexpr reference operator*() const noexcept { return current_[-1]; }
        constexpr pointer operator->() const noexcept { return &current_[-1]; }

        constexpr ReverseIterator &operator++() noexcept {
            --current_;
            return *this;
        }

        constexpr ReverseIterator operator++(int) noexcept {
            auto copy = *this;
            --current_;
            return copy;
        }

        constexpr ReverseIterator &operator--() noexcept {
            ++current_;
            return *this;
        }

        constexpr ReverseIterator operator--(int) noexcept {
            auto copy = *this;
            ++current_;
            return copy;
        }

        constexpr pointer base() const noexcept { return current_; }

        friend constexpr bool operator==(const ReverseIterator lhs, const ReverseIterator rhs) noexcept {
            return lhs.current_ == rhs.current_;
        }

        friend constexpr bool operator!=(const ReverseIterator lhs, const ReverseIterator rhs) noexcept {
            return lhs.current_ != rhs.current_;
        }

    protected:
        pointer current_ {};
    };

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

    struct Tag {
        u32 field_number {};
        WireType wire_type {};
    };

    struct Error {
        ErrorCode code {};
        usize offset {};
        u32 field_number {};
    };

    template<class E> struct Unexpected {
        using error_type = E;

        constexpr Unexpected(const Unexpected &) noexcept(noexcept(E {protocyte::declval<const E &>()})) = default;
        constexpr Unexpected(Unexpected &&) noexcept(noexcept(E {protocyte::declval<E &&>()})) = default;
        constexpr Unexpected &operator=(const Unexpected &) noexcept(
            noexcept(protocyte::declval<E &>() = protocyte::declval<const E &>())) = default;
        constexpr Unexpected &
        operator=(Unexpected &&) noexcept(noexcept(protocyte::declval<E &>() = protocyte::declval<E &&>())) = default;

        template<class G>
        constexpr Unexpected(G &&error_value) noexcept(noexcept(E {protocyte::forward<G>(error_value)}))
            requires(!::std::same_as<::std::remove_cvref_t<G>, Unexpected>)
            : error_ {protocyte::forward<G>(error_value)} {}

        constexpr E &error() & noexcept { return error_; }
        constexpr const E &error() const & noexcept { return error_; }
        constexpr E &&error() && noexcept { return protocyte::move(error_); }
        constexpr const E &&error() const && noexcept { return protocyte::move(error_); }

    protected:
        E error_;
    };

    template<class E>
    constexpr auto unexpected(E &&error_value) noexcept(noexcept(Unexpected<::std::remove_cvref_t<E>> {
        protocyte::forward<E>(error_value)})) -> Unexpected<::std::remove_cvref_t<E>> {
        return Unexpected<::std::remove_cvref_t<E>> {protocyte::forward<E>(error_value)};
    }

    constexpr Unexpected<Error> unexpected(const ErrorCode code, const usize offset,
                                           const u32 field_number = {}) noexcept {
        return Error {.code = code, .offset = offset, .field_number = field_number};
    }

    template<class T> struct Ref {
        constexpr explicit Ref(T &value) noexcept: ptr_ {&value} {}
        constexpr T &get() const noexcept { return *ptr_; }
        constexpr T &operator*() const noexcept { return *ptr_; }
        constexpr operator T &() const noexcept { return *ptr_; }
        constexpr T *operator->() const noexcept { return ptr_; }

    protected:
        T *ptr_;
    };

    struct ResultValueTag {};
    struct ResultErrorTag {};

    template<class T, class E = Error> struct Result {
        using value_type = T;
        using error_type = E;

        constexpr Result() noexcept(noexcept(T {}))
            requires(requires { T {}; })
            : ok_ {true}, value_ {} {}

        template<class U = T> constexpr Result(U &&value) noexcept(noexcept(T {protocyte::forward<U>(value)}))
            requires(!ResultType<U> && !UnexpectedType<U>)
            : ok_ {true}, value_ {protocyte::forward<U>(value)} {}

        template<class G>
        constexpr Result(const Unexpected<G> &unexpected_value) noexcept(noexcept(E {unexpected_value.error()}))
            requires(requires(const G &error_value) { E {error_value}; })
            : ok_ {false}, error_ {unexpected_value.error()} {}

        template<class G> constexpr Result(Unexpected<G> &&unexpected_value) noexcept(noexcept(E {
            protocyte::move(unexpected_value).error()}))
            requires(requires(G &&error_value) { E {protocyte::forward<G>(error_value)}; })
            : ok_ {false}, error_ {protocyte::move(unexpected_value).error()} {}

        template<class U, class G>
        constexpr Result(const Result<U, G> &other) noexcept(noexcept(T {*other}) && noexcept(E {other.error()}))
            requires(!::std::same_as<Result<U, G>, Result> && !::std::same_as<U, void> &&
                     requires(const Result<U, G> &source) {
                         T {*source};
                         E {source.error()};
                     })
            : ok_ {other.is_ok()} {
            if (ok_) {
                new (&value_) T {*other};
            } else {
                new (&error_) E {other.error()};
            }
        }

        template<class U, class G>
        constexpr Result(Result<U, G> &&other) noexcept(noexcept(T {*protocyte::move(other)}) &&
                                                        noexcept(E {protocyte::move(other).error()}))
            requires(!::std::same_as<Result<U, G>, Result> && !::std::same_as<U, void> &&
                     requires(Result<U, G> &&source) {
                         T {*protocyte::move(source)};
                         E {protocyte::move(source).error()};
                     })
            : ok_ {other.is_ok()} {
            if (ok_) {
                new (&value_) T {*protocyte::move(other)};
            } else {
                new (&error_) E {protocyte::move(other).error()};
            }
        }

        Result(Result &&other) noexcept(noexcept(T {protocyte::move(other.value_)}) &&
                                        noexcept(E {protocyte::move(other.error_)})):
            ok_ {other.ok_} {
            if (ok_) {
                new (&value_) T {protocyte::move(other.value_)};
            } else {
                new (&error_) E {protocyte::move(other.error_)};
            }
        }

        Result &operator=(Result &&other) noexcept(noexcept(T {protocyte::move(other.value_)}) &&
                                                   noexcept(E {protocyte::move(other.error_)})) {
            if (this == &other) {
                return *this;
            }
            destroy();
            ok_ = other.ok_;
            if (ok_) {
                new (&value_) T {protocyte::move(other.value_)};
            } else {
                new (&error_) E {protocyte::move(other.error_)};
            }
            return *this;
        }

        Result(const Result &other) noexcept(noexcept(T {other.value_}) && noexcept(E {other.error_})):
            ok_ {other.ok_} {
            if (ok_) {
                new (&value_) T {other.value_};
            } else {
                new (&error_) E {other.error_};
            }
        }

        Result &operator=(const Result &other) noexcept(noexcept(T {other.value_}) && noexcept(E {other.error_})) {
            if (this == &other) {
                return *this;
            }
            destroy();
            ok_ = other.ok_;
            if (ok_) {
                new (&value_) T {other.value_};
            } else {
                new (&error_) E {other.error_};
            }
            return *this;
        }

        template<class U, class G>
        Result &operator=(const Result<U, G> &other) noexcept(noexcept(T {*other}) && noexcept(E {other.error()}))
            requires(!::std::same_as<Result<U, G>, Result> && !::std::same_as<U, void> &&
                     requires(const Result<U, G> &source) {
                         T {*source};
                         E {source.error()};
                     })
        {
            destroy();
            ok_ = other.is_ok();
            if (ok_) {
                new (&value_) T {*other};
            } else {
                new (&error_) E {other.error()};
            }
            return *this;
        }

        template<class U, class G>
        Result &operator=(Result<U, G> &&other) noexcept(noexcept(T {*protocyte::move(other)}) &&
                                                         noexcept(E {protocyte::move(other).error()}))
            requires(!::std::same_as<Result<U, G>, Result> && !::std::same_as<U, void> &&
                     requires(Result<U, G> &&source) {
                         T {*protocyte::move(source)};
                         E {protocyte::move(source).error()};
                     })
        {
            destroy();
            ok_ = other.is_ok();
            if (ok_) {
                new (&value_) T {*protocyte::move(other)};
            } else {
                new (&error_) E {protocyte::move(other).error()};
            }
            return *this;
        }

        ~Result() noexcept { destroy(); }

        constexpr bool is_ok() const noexcept { return ok_; }
        constexpr explicit operator bool() const noexcept { return ok_; }

        T &operator*() & noexcept { return value_; }
        const T &operator*() const & noexcept { return value_; }
        T &&operator*() && noexcept { return protocyte::move(value_); }
        const T &&operator*() const && noexcept { return protocyte::move(value_); }

        T *operator->() noexcept { return &value_; }
        const T *operator->() const noexcept { return &value_; }

        T &value() & noexcept { return value_; }
        const T &value() const & noexcept { return value_; }
        T &&value() && noexcept { return protocyte::move(value_); }
        const T &&value() const && noexcept { return protocyte::move(value_); }
        T &&take_value() && noexcept { return protocyte::move(value_); }

        E &error() & noexcept { return error_; }
        const E &error() const & noexcept { return error_; }
        E &&error() && noexcept { return protocyte::move(error_); }
        const E &&error() const && noexcept { return protocyte::move(error_); }

        Result<void, E> status() const & noexcept(noexcept(Result<void, E> {protocyte::unexpected(error())})) {
            return ok_ ? Result<void, E> {} : Result<void, E> {protocyte::unexpected(error())};
        }

        Result<void, E>
        status() && noexcept(noexcept(Result<void, E> {protocyte::unexpected(protocyte::move(error_))})) {
            return ok_ ? Result<void, E> {} : Result<void, E> {protocyte::unexpected(protocyte::move(error_))};
        }

        template<class F>
        constexpr auto and_then(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), value())) &&
                                                  noexcept(::std::remove_cvref_t<InvokeResult<F, T &>> {
                                                      protocyte::unexpected(error())}))
            -> ::std::remove_cvref_t<InvokeResult<F, T &>>
            requires(ResultType<InvokeResult<F, T &>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, T &>>::error_type, E> &&
                     requires(F &&fn, T &value_ref, E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), value_ref);
                         ::std::remove_cvref_t<InvokeResult<F, T &>> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, T &>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f), value()) : U {protocyte::unexpected(error())};
        }

        template<class F> constexpr auto and_then(F &&f) const & noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), value())) &&
            noexcept(::std::remove_cvref_t<InvokeResult<F, const T &>> {protocyte::unexpected(error())}))
            -> ::std::remove_cvref_t<InvokeResult<F, const T &>>
            requires(ResultType<InvokeResult<F, const T &>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, const T &>>::error_type, E> &&
                     requires(F &&fn, const T &value_ref, const E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), value_ref);
                         ::std::remove_cvref_t<InvokeResult<F, const T &>> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, const T &>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f), value()) : U {protocyte::unexpected(error())};
        }

        template<class F> constexpr auto and_then(F &&f) && noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_))) &&
            noexcept(::std::remove_cvref_t<InvokeResult<F, T &&>> {protocyte::unexpected(protocyte::move(error_))}))
            -> ::std::remove_cvref_t<InvokeResult<F, T &&>>
            requires(ResultType<InvokeResult<F, T &&>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, T &&>>::error_type, E> &&
                     requires(F &&fn, T &&value_ref, E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<T>(value_ref));
                         ::std::remove_cvref_t<InvokeResult<F, T &&>> {
                             protocyte::unexpected(protocyte::forward<E>(error_ref))};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, T &&>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_)) :
                         U {protocyte::unexpected(protocyte::move(error_))};
        }

        template<class F>
        constexpr auto and_then(F &&f) const && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f),
                                                                                    protocyte::move(value_))) &&
                                                         noexcept(::std::remove_cvref_t<InvokeResult<F, const T &&>> {
                                                             protocyte::unexpected(protocyte::move(error_))}))
            -> ::std::remove_cvref_t<InvokeResult<F, const T &&>>
            requires(ResultType<InvokeResult<F, const T &&>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, const T &&>>::error_type, E> &&
                     requires(F &&fn, const T &&value_ref, const E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const T>(value_ref));
                         ::std::remove_cvref_t<InvokeResult<F, const T &&>> {
                             protocyte::unexpected(protocyte::forward<const E>(error_ref))};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, const T &&>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_)) :
                         U {protocyte::unexpected(protocyte::move(error_))};
        }

        template<class F>
        constexpr auto transform(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), value())) &&
                                                   noexcept(Result<::std::remove_cv_t<InvokeResult<F, T &>>, E> {
                                                       protocyte::unexpected(error())}))
            -> Result<::std::remove_cv_t<InvokeResult<F, T &>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, T &>>> &&
                     requires(F &&fn, T &value_ref, E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), value_ref);
                         Result<::std::remove_cv_t<InvokeResult<F, T &>>, E> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, T &>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(error())};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f), value());
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f), value());
            }
        }

        template<class F> constexpr auto transform(F &&f) const & noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), value())) &&
            noexcept(Result<::std::remove_cv_t<InvokeResult<F, const T &>>, E> {protocyte::unexpected(error())}))
            -> Result<::std::remove_cv_t<InvokeResult<F, const T &>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const T &>>> &&
                     requires(F &&fn, const T &value_ref, const E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), value_ref);
                         Result<::std::remove_cv_t<InvokeResult<F, const T &>>, E> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, const T &>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(error())};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f), value());
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f), value());
            }
        }

        template<class F> constexpr auto
        transform(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_))) &&
                                     noexcept(Result<::std::remove_cv_t<InvokeResult<F, T &&>>, E> {
                                         protocyte::unexpected(protocyte::move(error_))}))
            -> Result<::std::remove_cv_t<InvokeResult<F, T &&>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, T &&>>> &&
                     requires(F &&fn, T &&value_ref, E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<T>(value_ref));
                         Result<::std::remove_cv_t<InvokeResult<F, T &&>>, E> {
                             protocyte::unexpected(protocyte::forward<E>(error_ref))};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, T &&>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(protocyte::move(error_))};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_));
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_));
            }
        }

        template<class F> constexpr auto transform(F &&f) const && noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_))) &&
            noexcept(Result<::std::remove_cv_t<InvokeResult<F, const T &&>>, E> {
                protocyte::unexpected(protocyte::move(error_))}))
            -> Result<::std::remove_cv_t<InvokeResult<F, const T &&>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const T &&>>> &&
                     requires(F &&fn, const T &&value_ref, const E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const T>(value_ref));
                         Result<::std::remove_cv_t<InvokeResult<F, const T &&>>, E> {
                             protocyte::unexpected(protocyte::forward<const E>(error_ref))};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, const T &&>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(protocyte::move(error_))};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_));
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f), protocyte::move(value_));
            }
        }

        template<class F>
        constexpr auto or_else(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())) &&
                                                 noexcept(::std::remove_cvref_t<InvokeResult<F, E &>> {value()}))
            -> ::std::remove_cvref_t<InvokeResult<F, E &>>
            requires(ResultType<InvokeResult<F, E &>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, E &>>::value_type, T> &&
                     requires(F &&fn, E &error_ref, T &value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), error_ref);
                         ::std::remove_cvref_t<InvokeResult<F, E &>> {value_ref};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, E &>>;
            return ok_ ? G {value()} : protocyte::invoke(protocyte::forward<F>(f), error());
        }

        template<class F> constexpr auto
        or_else(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())) &&
                                        noexcept(::std::remove_cvref_t<InvokeResult<F, const E &>> {value()}))
            -> ::std::remove_cvref_t<InvokeResult<F, const E &>>
            requires(ResultType<InvokeResult<F, const E &>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, const E &>>::value_type, T> &&
                     requires(F &&fn, const E &error_ref, const T &value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), error_ref);
                         ::std::remove_cvref_t<InvokeResult<F, const E &>> {value_ref};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, const E &>>;
            return ok_ ? G {value()} : protocyte::invoke(protocyte::forward<F>(f), error());
        }

        template<class F> constexpr auto
        or_else(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_))) &&
                                   noexcept(::std::remove_cvref_t<InvokeResult<F, E &&>> {protocyte::move(value_)}))
            -> ::std::remove_cvref_t<InvokeResult<F, E &&>>
            requires(ResultType<InvokeResult<F, E &&>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, E &&>>::value_type, T> &&
                     requires(F &&fn, E &&error_ref, T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<E>(error_ref));
                         ::std::remove_cvref_t<InvokeResult<F, E &&>> {protocyte::forward<T>(value_ref)};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, E &&>>;
            return ok_ ? G {protocyte::move(value_)} :
                         protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_));
        }

        template<class F> constexpr auto or_else(F &&f) const && noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_))) &&
            noexcept(::std::remove_cvref_t<InvokeResult<F, const E &&>> {protocyte::move(value_)}))
            -> ::std::remove_cvref_t<InvokeResult<F, const E &&>>
            requires(ResultType<InvokeResult<F, const E &&>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F, const E &&>>::value_type, T> &&
                     requires(F &&fn, const E &&error_ref, const T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const E>(error_ref));
                         ::std::remove_cvref_t<InvokeResult<F, const E &&>> {protocyte::forward<const T>(value_ref)};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, const E &&>>;
            return ok_ ? G {protocyte::move(value_)} :
                         protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_));
        }

        template<class F> constexpr auto
        transform_error(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())) &&
                                          noexcept(Result<T, ::std::remove_cv_t<InvokeResult<F, E &>>> {value()}))
            -> Result<T, ::std::remove_cv_t<InvokeResult<F, E &>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, E &>>> &&
                     requires(F &&fn, E &error_ref, T &value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), error_ref);
                         Result<T, ::std::remove_cv_t<InvokeResult<F, E &>>> {value_ref};
                     })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, E &>>;
            return ok_ ? Result<T, G> {value()} :
                         Result<T, G> {protocyte::unexpected(protocyte::invoke(protocyte::forward<F>(f), error()))};
        }

        template<class F> constexpr auto transform_error(F &&f) const & noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), error())) &&
            noexcept(Result<T, ::std::remove_cv_t<InvokeResult<F, const E &>>> {value()}))
            -> Result<T, ::std::remove_cv_t<InvokeResult<F, const E &>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const E &>>> &&
                     requires(F &&fn, const E &error_ref, const T &value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), error_ref);
                         Result<T, ::std::remove_cv_t<InvokeResult<F, const E &>>> {value_ref};
                     })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, const E &>>;
            return ok_ ? Result<T, G> {value()} :
                         Result<T, G> {protocyte::unexpected(protocyte::invoke(protocyte::forward<F>(f), error()))};
        }

        template<class F> constexpr auto transform_error(F &&f) && noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_))) &&
            noexcept(Result<T, ::std::remove_cv_t<InvokeResult<F, E &&>>> {protocyte::move(value_)}))
            -> Result<T, ::std::remove_cv_t<InvokeResult<F, E &&>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, E &&>>> &&
                     requires(F &&fn, E &&error_ref, T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<E>(error_ref));
                         Result<T, ::std::remove_cv_t<InvokeResult<F, E &&>>> {protocyte::forward<T>(value_ref)};
                     })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, E &&>>;
            return ok_ ? Result<T, G> {protocyte::move(value_)} :
                         Result<T, G> {protocyte::unexpected(
                             protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_)))};
        }

        template<class F> constexpr auto transform_error(F &&f) const && noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_))) &&
            noexcept(Result<T, ::std::remove_cv_t<InvokeResult<F, const E &&>>> {protocyte::move(value_)}))
            -> Result<T, ::std::remove_cv_t<InvokeResult<F, const E &&>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const E &&>>> &&
                     requires(F &&fn, const E &&error_ref, const T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const E>(error_ref));
                         Result<T, ::std::remove_cv_t<InvokeResult<F, const E &&>>> {
                             protocyte::forward<const T>(value_ref)};
                     })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, const E &&>>;
            return ok_ ? Result<T, G> {protocyte::move(value_)} :
                         Result<T, G> {protocyte::unexpected(
                             protocyte::invoke(protocyte::forward<F>(f), protocyte::move(error_)))};
        }

    protected:
        void destroy() noexcept {
            if (ok_) {
                value_.~T();
            } else {
                error_.~E();
            }
        }

        bool ok_;
        union {
            T value_;
            E error_;
        };
    };

    template<class E> struct Result<void, E> {
        using value_type = void;
        using error_type = E;

        template<class G>
        constexpr Result(const Unexpected<G> &unexpected_value) noexcept(noexcept(E {unexpected_value.error()}))
            requires(requires(const G &error_value) { E {error_value}; })
            : ok_ {false} {
            new (&storage_.error_) E {unexpected_value.error()};
        }

        template<class G> constexpr Result(Unexpected<G> &&unexpected_value) noexcept(noexcept(E {
            protocyte::move(unexpected_value).error()}))
            requires(requires(G &&error_value) { E {protocyte::forward<G>(error_value)}; })
            : ok_ {false} {
            new (&storage_.error_) E {protocyte::move(unexpected_value).error()};
        }

        template<class G> constexpr Result(const Result<void, G> &other) noexcept(noexcept(E {other.error()}))
            requires(!::std::same_as<Result<void, G>, Result> &&
                     requires(const Result<void, G> &source) { E {source.error()}; })
            : ok_ {other.is_ok()} {
            if (!ok_) {
                new (&storage_.error_) E {other.error()};
            }
        }

        template<class G>
        constexpr Result(Result<void, G> &&other) noexcept(noexcept(E {protocyte::move(other).error()}))
            requires(!::std::same_as<Result<void, G>, Result> &&
                     requires(Result<void, G> &&source) { E {protocyte::move(source).error()}; })
            : ok_ {other.is_ok()} {
            if (!ok_) {
                new (&storage_.error_) E {protocyte::move(other).error()};
            }
        }

        Result(Result &&other) noexcept(noexcept(E {protocyte::move(other.storage_.error_)})): ok_ {other.ok_} {
            if (!ok_) {
                new (&storage_.error_) E {protocyte::move(other.storage_.error_)};
            }
        }

        Result &operator=(Result &&other) noexcept(noexcept(E {protocyte::move(other.storage_.error_)})) {
            if (this == &other) {
                return *this;
            }
            destroy();
            ok_ = other.ok_;
            if (!ok_) {
                new (&storage_.error_) E {protocyte::move(other.storage_.error_)};
            }
            return *this;
        }

        Result(const Result &other) noexcept(noexcept(E {other.storage_.error_})): ok_ {other.ok_} {
            if (!ok_) {
                new (&storage_.error_) E {other.storage_.error_};
            }
        }

        Result &operator=(const Result &other) noexcept(noexcept(E {other.storage_.error_})) {
            if (this == &other) {
                return *this;
            }
            destroy();
            ok_ = other.ok_;
            if (!ok_) {
                new (&storage_.error_) E {other.storage_.error_};
            }
            return *this;
        }

        template<class G> Result &operator=(const Result<void, G> &other) noexcept(noexcept(E {other.error()}))
            requires(!::std::same_as<Result<void, G>, Result> &&
                     requires(const Result<void, G> &source) { E {source.error()}; })
        {
            destroy();
            ok_ = other.is_ok();
            if (!ok_) {
                new (&storage_.error_) E {other.error()};
            }
            return *this;
        }

        template<class G>
        Result &operator=(Result<void, G> &&other) noexcept(noexcept(E {protocyte::move(other).error()}))
            requires(!::std::same_as<Result<void, G>, Result> &&
                     requires(Result<void, G> &&source) { E {protocyte::move(source).error()}; })
        {
            destroy();
            ok_ = other.is_ok();
            if (!ok_) {
                new (&storage_.error_) E {protocyte::move(other).error()};
            }
            return *this;
        }

        ~Result() noexcept { destroy(); }

        constexpr bool is_ok() const noexcept { return ok_; }
        constexpr explicit operator bool() const noexcept { return ok_; }
        constexpr void operator*() const noexcept {}
        constexpr void value() const noexcept {}
        constexpr void take_value() && noexcept {}

        E &error() & noexcept { return storage_.error_; }
        const E &error() const & noexcept { return storage_.error_; }
        E &&error() && noexcept { return protocyte::move(storage_.error_); }
        const E &&error() const && noexcept { return protocyte::move(storage_.error_); }

        Result status() const & noexcept(noexcept(Result {protocyte::unexpected(error())})) {
            return ok_ ? Result {} : Result {protocyte::unexpected(error())};
        }

        Result status() && noexcept(noexcept(Result {protocyte::unexpected(protocyte::move(storage_.error_))})) {
            return ok_ ? Result {} : Result {protocyte::unexpected(protocyte::move(storage_.error_))};
        }

        template<class F> constexpr auto
        and_then(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                   noexcept(::std::remove_cvref_t<InvokeResult<F>> {protocyte::unexpected(error())}))
            -> ::std::remove_cvref_t<InvokeResult<F>>
            requires(ResultType<InvokeResult<F>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F>>::error_type, E> &&
                     requires(F &&fn, E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         ::std::remove_cvref_t<InvokeResult<F>> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f)) : U {protocyte::unexpected(error())};
        }

        template<class F>
        constexpr auto and_then(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                        noexcept(::std::remove_cvref_t<InvokeResult<F>> {
                                                            protocyte::unexpected(error())}))
            -> ::std::remove_cvref_t<InvokeResult<F>>
            requires(ResultType<InvokeResult<F>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F>>::error_type, E> &&
                     requires(F &&fn, const E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         ::std::remove_cvref_t<InvokeResult<F>> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f)) : U {protocyte::unexpected(error())};
        }

        template<class F>
        constexpr auto and_then(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                   noexcept(::std::remove_cvref_t<InvokeResult<F>> {
                                                       protocyte::unexpected(protocyte::move(storage_.error_))}))
            -> ::std::remove_cvref_t<InvokeResult<F>>
            requires(ResultType<InvokeResult<F>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F>>::error_type, E> &&
                     requires(F &&fn, E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         ::std::remove_cvref_t<InvokeResult<F>> {
                             protocyte::unexpected(protocyte::forward<E>(error_ref))};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f)) :
                         U {protocyte::unexpected(protocyte::move(storage_.error_))};
        }

        template<class F>
        constexpr auto and_then(F &&f) const && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                         noexcept(::std::remove_cvref_t<InvokeResult<F>> {
                                                             protocyte::unexpected(protocyte::move(storage_.error_))}))
            -> ::std::remove_cvref_t<InvokeResult<F>>
            requires(ResultType<InvokeResult<F>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F>>::error_type, E> &&
                     requires(F &&fn, const E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         ::std::remove_cvref_t<InvokeResult<F>> {
                             protocyte::unexpected(protocyte::forward<const E>(error_ref))};
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F>>;
            return ok_ ? protocyte::invoke(protocyte::forward<F>(f)) :
                         U {protocyte::unexpected(protocyte::move(storage_.error_))};
        }

        template<class F>
        constexpr auto transform(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                   noexcept(Result<::std::remove_cv_t<InvokeResult<F>>, E> {
                                                       protocyte::unexpected(error())}))
            -> Result<::std::remove_cv_t<InvokeResult<F>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F>>> &&
                     requires(F &&fn, E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         Result<::std::remove_cv_t<InvokeResult<F>>, E> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(error())};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f));
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f));
            }
        }

        template<class F>
        constexpr auto transform(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                         noexcept(Result<::std::remove_cv_t<InvokeResult<F>>, E> {
                                                             protocyte::unexpected(error())}))
            -> Result<::std::remove_cv_t<InvokeResult<F>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F>>> &&
                     requires(F &&fn, const E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         Result<::std::remove_cv_t<InvokeResult<F>>, E> {protocyte::unexpected(error_ref)};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(error())};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f));
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f));
            }
        }

        template<class F>
        constexpr auto transform(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                    noexcept(Result<::std::remove_cv_t<InvokeResult<F>>, E> {
                                                        protocyte::unexpected(protocyte::move(storage_.error_))}))
            -> Result<::std::remove_cv_t<InvokeResult<F>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F>>> &&
                     requires(F &&fn, E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         Result<::std::remove_cv_t<InvokeResult<F>>, E> {
                             protocyte::unexpected(protocyte::forward<E>(error_ref))};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(protocyte::move(storage_.error_))};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f));
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f));
            }
        }

        template<class F>
        constexpr auto transform(F &&f) const && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))) &&
                                                          noexcept(Result<::std::remove_cv_t<InvokeResult<F>>, E> {
                                                              protocyte::unexpected(protocyte::move(storage_.error_))}))
            -> Result<::std::remove_cv_t<InvokeResult<F>>, E>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F>>> &&
                     requires(F &&fn, const E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn));
                         Result<::std::remove_cv_t<InvokeResult<F>>, E> {
                             protocyte::unexpected(protocyte::forward<const E>(error_ref))};
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F>>;
            if (!ok_) {
                return Result<U, E> {protocyte::unexpected(protocyte::move(storage_.error_))};
            }
            if constexpr (::std::is_void_v<U>) {
                protocyte::invoke(protocyte::forward<F>(f));
                return {};
            } else {
                return protocyte::invoke(protocyte::forward<F>(f));
            }
        }

        template<class F>
        constexpr auto or_else(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())) &&
                                                 noexcept(::std::remove_cvref_t<InvokeResult<F, E &>> {}))
            -> ::std::remove_cvref_t<InvokeResult<F, E &>>
            requires(ResultType<InvokeResult<F, E &>> &&
                     ::std::is_void_v<typename ::std::remove_cvref_t<InvokeResult<F, E &>>::value_type> &&
                     requires(F &&fn, E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), error_ref);
                         ::std::remove_cvref_t<InvokeResult<F, E &>> {};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, E &>>;
            return ok_ ? G {} : protocyte::invoke(protocyte::forward<F>(f), error());
        }

        template<class F>
        constexpr auto or_else(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())) &&
                                                       noexcept(::std::remove_cvref_t<InvokeResult<F, const E &>> {}))
            -> ::std::remove_cvref_t<InvokeResult<F, const E &>>
            requires(ResultType<InvokeResult<F, const E &>> &&
                     ::std::is_void_v<typename ::std::remove_cvref_t<InvokeResult<F, const E &>>::value_type> &&
                     requires(F &&fn, const E &error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), error_ref);
                         ::std::remove_cvref_t<InvokeResult<F, const E &>> {};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, const E &>>;
            return ok_ ? G {} : protocyte::invoke(protocyte::forward<F>(f), error());
        }

        template<class F>
        constexpr auto or_else(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f),
                                                                             protocyte::move(storage_.error_))) &&
                                                  noexcept(::std::remove_cvref_t<InvokeResult<F, E &&>> {}))
            -> ::std::remove_cvref_t<InvokeResult<F, E &&>>
            requires(ResultType<InvokeResult<F, E &&>> &&
                     ::std::is_void_v<typename ::std::remove_cvref_t<InvokeResult<F, E &&>>::value_type> &&
                     requires(F &&fn, E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<E>(error_ref));
                         ::std::remove_cvref_t<InvokeResult<F, E &&>> {};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, E &&>>;
            return ok_ ? G {} : protocyte::invoke(protocyte::forward<F>(f), protocyte::move(storage_.error_));
        }

        template<class F>
        constexpr auto or_else(F &&f) const && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f),
                                                                                   protocyte::move(storage_.error_))) &&
                                                        noexcept(::std::remove_cvref_t<InvokeResult<F, const E &&>> {}))
            -> ::std::remove_cvref_t<InvokeResult<F, const E &&>>
            requires(ResultType<InvokeResult<F, const E &&>> &&
                     ::std::is_void_v<typename ::std::remove_cvref_t<InvokeResult<F, const E &&>>::value_type> &&
                     requires(F &&fn, const E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const E>(error_ref));
                         ::std::remove_cvref_t<InvokeResult<F, const E &&>> {};
                     })
        {
            using G = ::std::remove_cvref_t<InvokeResult<F, const E &&>>;
            return ok_ ? G {} : protocyte::invoke(protocyte::forward<F>(f), protocyte::move(storage_.error_));
        }

        template<class F>
        constexpr auto transform_error(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())))
            -> Result<void, ::std::remove_cv_t<InvokeResult<F, E &>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, E &>>> &&
                     requires(F &&fn, E &error_ref) { protocyte::invoke(protocyte::forward<F>(fn), error_ref); })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, E &>>;
            return ok_ ? Result<void, G> {} :
                         Result<void, G> {protocyte::unexpected(protocyte::invoke(protocyte::forward<F>(f), error()))};
        }

        template<class F> constexpr auto
        transform_error(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), error())))
            -> Result<void, ::std::remove_cv_t<InvokeResult<F, const E &>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const E &>>> &&
                     requires(F &&fn, const E &error_ref) { protocyte::invoke(protocyte::forward<F>(fn), error_ref); })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, const E &>>;
            return ok_ ? Result<void, G> {} :
                         Result<void, G> {protocyte::unexpected(protocyte::invoke(protocyte::forward<F>(f), error()))};
        }

        template<class F>
        constexpr auto transform_error(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f),
                                                                                     protocyte::move(storage_.error_))))
            -> Result<void, ::std::remove_cv_t<InvokeResult<F, E &&>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, E &&>>> &&
                     requires(F &&fn, E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<E>(error_ref));
                     })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, E &&>>;
            return ok_ ? Result<void, G> {} :
                         Result<void, G> {protocyte::unexpected(
                             protocyte::invoke(protocyte::forward<F>(f), protocyte::move(storage_.error_)))};
        }

        template<class F> constexpr auto transform_error(F &&f) const && noexcept(
            noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(storage_.error_))))
            -> Result<void, ::std::remove_cv_t<InvokeResult<F, const E &&>>>
            requires(!::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const E &&>>> &&
                     requires(F &&fn, const E &&error_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const E>(error_ref));
                     })
        {
            using G = ::std::remove_cv_t<InvokeResult<F, const E &&>>;
            return ok_ ? Result<void, G> {} :
                         Result<void, G> {protocyte::unexpected(
                             protocyte::invoke(protocyte::forward<F>(f), protocyte::move(storage_.error_)))};
        }

        constexpr Result() noexcept = default;

    protected:
        void destroy() noexcept {
            if (!ok_) {
                storage_.error_.~E();
            }
        }

        union Storage {
            constexpr Storage() noexcept {}
            ~Storage() noexcept {}

            E error_;
        };

        bool ok_ {true};
        Storage storage_;
    };

    using Status = Result<void>;

    struct ByteView {
        using value_type = const u8;
        using iterator = const u8 *;
        using const_iterator = const u8 *;
        using reverse_iterator = ReverseIterator<const u8>;
        using const_reverse_iterator = ReverseIterator<const u8>;

        const u8 *data {};
        usize size {};

        constexpr iterator begin() const noexcept { return data; }
        constexpr iterator end() const noexcept { return data + size; }
        constexpr const_iterator cbegin() const noexcept { return begin(); }
        constexpr const_iterator cend() const noexcept { return end(); }
        constexpr reverse_iterator rbegin() const noexcept { return reverse_iterator {end()}; }
        constexpr reverse_iterator rend() const noexcept { return reverse_iterator {begin()}; }
        constexpr const_reverse_iterator crbegin() const noexcept { return rbegin(); }
        constexpr const_reverse_iterator crend() const noexcept { return rend(); }
        constexpr bool empty() const noexcept { return size == 0u; }
    };

    struct MutableByteView {
        using value_type = u8;
        using iterator = u8 *;
        using const_iterator = const u8 *;
        using reverse_iterator = ReverseIterator<u8>;
        using const_reverse_iterator = ReverseIterator<const u8>;

        u8 *data {};
        usize size {};

        constexpr iterator begin() noexcept { return data; }
        constexpr const_iterator begin() const noexcept { return data; }
        constexpr iterator end() noexcept { return data + size; }
        constexpr const_iterator end() const noexcept { return data + size; }
        constexpr const_iterator cbegin() const noexcept { return begin(); }
        constexpr const_iterator cend() const noexcept { return end(); }
        constexpr reverse_iterator rbegin() noexcept { return reverse_iterator {end()}; }
        constexpr const_reverse_iterator rbegin() const noexcept { return const_reverse_iterator {end()}; }
        constexpr reverse_iterator rend() noexcept { return reverse_iterator {begin()}; }
        constexpr const_reverse_iterator rend() const noexcept { return const_reverse_iterator {begin()}; }
        constexpr const_reverse_iterator crbegin() const noexcept { return rbegin(); }
        constexpr const_reverse_iterator crend() const noexcept { return rend(); }
        constexpr bool empty() const noexcept { return size == 0u; }
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

    inline Status checked_add(const usize lhs, const usize rhs, usize *out) noexcept {
        const auto value = lhs + rhs;
        if (value < lhs) {
            return protocyte::unexpected(ErrorCode::integer_overflow, {});
        }
        *out = value;
        return {};
    }

    inline Status checked_mul(const usize lhs, const usize rhs, usize *out) noexcept {
        if (lhs != 0u && rhs > static_cast<usize>(~static_cast<usize>(0u)) / lhs) {
            return protocyte::unexpected(ErrorCode::integer_overflow, {});
        }
        *out = lhs * rhs;
        return {};
    }

    template<class T> struct AlwaysFalse {
        static constexpr bool value = false;
    };

    inline void copy_bytes(u8 *dst, const u8 *src, const usize count) noexcept {
        for (usize i {}; i < count; ++i) { dst[i] = src[i]; }
    }

    template<class T, class Context> Result<T> copy_value(Context *ctx, const T &value) noexcept {
        if constexpr (requires { T {value}; }) {
            return T {value};
        } else if constexpr (
            requires(const T &src) { src.view(); } && requires(T &out, const ByteView view) { out.assign(view); }) {
            Context *copy_ctx {ctx};
            if constexpr (requires(const T &src) { src.context(); }) {
                if (copy_ctx == nullptr) {
                    copy_ctx = value.context();
                }
            }
            if constexpr (requires(Context *value_ctx) { T {value_ctx}; }) {
                T copied {copy_ctx};
                return copied.assign(value.view()).transform([&copied]() noexcept -> T {
                    return protocyte::move(copied);
                });
            } else if constexpr (requires { T {}; }) {
                T copied {};
                return copied.assign(value.view()).transform([&copied]() noexcept -> T {
                    return protocyte::move(copied);
                });
            } else {
                static_assert(AlwaysFalse<T>::value,
                              "protocyte copy_value requires a default or pointer-context constructor");
                return protocyte::unexpected(ErrorCode::invalid_argument, {});
            }
        } else if constexpr (requires(T &out, const T &src) { out.copy_from(src); }) {
            Context *copy_ctx {ctx};
            if constexpr (requires(const T &src) { src.context(); }) {
                if (copy_ctx == nullptr) {
                    copy_ctx = value.context();
                }
            }
            if constexpr (requires(Context &value_ctx) { T {value_ctx}; }) {
                if (copy_ctx == nullptr) {
                    return protocyte::unexpected(ErrorCode::invalid_argument, {});
                }
                T copied {*copy_ctx};
                return copied.copy_from(value).transform([&copied]() noexcept -> T { return protocyte::move(copied); });
            } else if constexpr (requires(Context *value_ctx) { T {value_ctx}; }) {
                T copied {copy_ctx};
                return copied.copy_from(value).transform([&copied]() noexcept -> T { return protocyte::move(copied); });
            } else if constexpr (requires { T {}; }) {
                T copied {};
                return copied.copy_from(value).transform([&copied]() noexcept -> T { return protocyte::move(copied); });
            } else {
                static_assert(AlwaysFalse<T>::value, "protocyte copy_value requires a default or context constructor");
                return protocyte::unexpected(ErrorCode::invalid_argument, {});
            }
        } else {
            static_assert(AlwaysFalse<T>::value, "protocyte copy_value does not support this type");
            return protocyte::unexpected(ErrorCode::invalid_argument, {});
        }
    }

    template<class T> Result<T> copy_value(const T &value) noexcept {
        if constexpr (requires(const T &src) { src.context(); }) {
            return copy_value(value.context(), value);
        } else if constexpr (requires { T {value}; }) {
            return T {value};
        } else if constexpr (
            requires(const T &src) { src.view(); } && requires(T &out, const ByteView view) { out.assign(view); } &&
            requires { T {}; }) {
            T copied {};
            return copied.assign(value.view()).transform([&copied]() noexcept -> T { return protocyte::move(copied); });
        } else if constexpr (requires(T &out, const T &src) { out.copy_from(src); } && requires { T {}; }) {
            T copied {};
            return copied.copy_from(value).transform([&copied]() noexcept -> T { return protocyte::move(copied); });
        } else {
            static_assert(AlwaysFalse<T>::value,
                          "protocyte copy_value without context requires a copy constructor or default constructor");
            return protocyte::unexpected(ErrorCode::invalid_argument, {});
        }
    }

    struct Limits {
        static constexpr usize default_max_recursion_depth = 100u;
        static constexpr usize default_max_message_bytes = 0x7fffffffu;
        static constexpr usize default_max_string_bytes = 0x7fffffffu;

        usize max_recursion_depth {default_max_recursion_depth};
        usize max_message_bytes {default_max_message_bytes};
        usize max_string_bytes {default_max_string_bytes};
    };

    struct Allocator {
        void *state {};
        void *(*allocate)(void *state, usize size, usize alignment) {};
        void (*deallocate)(void *state, void *ptr, usize size, usize alignment) {};
    };

    template<class T, class Config> struct Vector;

    template<class T, usize Max> struct Array;

    template<usize Max> struct ByteArray;

    template<usize Max> struct FixedByteArray;

    template<class Config> struct Bytes;

    template<class Config> struct String;

    template<class T, class Config> struct Box;

    template<class K, class V, class Config> struct HashMap;

    struct DefaultConfig {
        struct Context {
            Allocator allocator;
            Limits limits;
            usize recursion_depth {};
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
        using value_type = T;

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
        explicit operator bool() const noexcept { return has_; }
        T &operator*() & noexcept { return *ptr(); }
        const T &operator*() const & noexcept { return *ptr(); }
        T &&operator*() && noexcept { return protocyte::move(*ptr()); }
        const T &&operator*() const && noexcept { return protocyte::move(*ptr()); }
        T *operator->() noexcept { return ptr(); }
        const T *operator->() const noexcept { return ptr(); }
        T &value() & noexcept { return *ptr(); }
        const T &value() const & noexcept { return *ptr(); }
        T &&value() && noexcept { return protocyte::move(*ptr()); }
        const T &&value() const && noexcept { return protocyte::move(*ptr()); }
        T &&take_value() && noexcept { return protocyte::move(*ptr()); }

        template<class F>
        constexpr auto and_then(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), value())))
            -> ::std::remove_cvref_t<InvokeResult<F, T &>>
            requires(OptionalType<InvokeResult<F, T &>> &&
                     requires(F &&fn, T &value_ref) { protocyte::invoke(protocyte::forward<F>(fn), value_ref); })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, T &>>;
            return has_ ? protocyte::invoke(protocyte::forward<F>(f), value()) : U {};
        }

        template<class F>
        constexpr auto and_then(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), value())))
            -> ::std::remove_cvref_t<InvokeResult<F, const T &>>
            requires(OptionalType<InvokeResult<F, const T &>> &&
                     requires(F &&fn, const T &value_ref) { protocyte::invoke(protocyte::forward<F>(fn), value_ref); })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, const T &>>;
            return has_ ? protocyte::invoke(protocyte::forward<F>(f), value()) : U {};
        }

        template<class F> constexpr auto
        and_then(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(*ptr()))))
            -> ::std::remove_cvref_t<InvokeResult<F, T &&>>
            requires(OptionalType<InvokeResult<F, T &&>> &&
                     requires(F &&fn, T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<T>(value_ref));
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, T &&>>;
            return has_ ? protocyte::invoke(protocyte::forward<F>(f), protocyte::move(*ptr())) : U {};
        }

        template<class F>
        constexpr auto and_then(F &&f) const && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f),
                                                                                    protocyte::move(*ptr()))))
            -> ::std::remove_cvref_t<InvokeResult<F, const T &&>>
            requires(OptionalType<InvokeResult<F, const T &&>> &&
                     requires(F &&fn, const T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const T>(value_ref));
                     })
        {
            using U = ::std::remove_cvref_t<InvokeResult<F, const T &&>>;
            return has_ ? protocyte::invoke(protocyte::forward<F>(f), protocyte::move(*ptr())) : U {};
        }

        template<class F>
        constexpr auto transform(F &&f) & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), value())))
            -> Optional<::std::remove_cv_t<InvokeResult<F, T &>>>
            requires(!::std::is_void_v<::std::remove_cv_t<InvokeResult<F, T &>>> &&
                     !::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, T &>>> &&
                     requires(F &&fn, T &value_ref) { protocyte::invoke(protocyte::forward<F>(fn), value_ref); })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, T &>>;
            Optional<U> out {};
            if (has_) {
                (void) out.emplace(protocyte::invoke(protocyte::forward<F>(f), value()));
            }
            return out;
        }

        template<class F>
        constexpr auto transform(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), value())))
            -> Optional<::std::remove_cv_t<InvokeResult<F, const T &>>>
            requires(!::std::is_void_v<::std::remove_cv_t<InvokeResult<F, const T &>>> &&
                     !::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const T &>>> &&
                     requires(F &&fn, const T &value_ref) { protocyte::invoke(protocyte::forward<F>(fn), value_ref); })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, const T &>>;
            Optional<U> out {};
            if (has_) {
                (void) out.emplace(protocyte::invoke(protocyte::forward<F>(f), value()));
            }
            return out;
        }

        template<class F> constexpr auto
        transform(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(*ptr()))))
            -> Optional<::std::remove_cv_t<InvokeResult<F, T &&>>>
            requires(!::std::is_void_v<::std::remove_cv_t<InvokeResult<F, T &&>>> &&
                     !::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, T &&>>> &&
                     requires(F &&fn, T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<T>(value_ref));
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, T &&>>;
            Optional<U> out {};
            if (has_) {
                (void) out.emplace(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(*ptr())));
            }
            return out;
        }

        template<class F>
        constexpr auto transform(F &&f) const && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f),
                                                                                     protocyte::move(*ptr()))))
            -> Optional<::std::remove_cv_t<InvokeResult<F, const T &&>>>
            requires(!::std::is_void_v<::std::remove_cv_t<InvokeResult<F, const T &&>>> &&
                     !::std::is_reference_v<::std::remove_cv_t<InvokeResult<F, const T &&>>> &&
                     requires(F &&fn, const T &&value_ref) {
                         protocyte::invoke(protocyte::forward<F>(fn), protocyte::forward<const T>(value_ref));
                     })
        {
            using U = ::std::remove_cv_t<InvokeResult<F, const T &&>>;
            Optional<U> out {};
            if (has_) {
                (void) out.emplace(protocyte::invoke(protocyte::forward<F>(f), protocyte::move(*ptr())));
            }
            return out;
        }

        template<class F>
        constexpr Optional or_else(F &&f) const & noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))))
            requires(OptionalType<InvokeResult<F>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F>>::value_type, T> &&
                     ::std::is_constructible_v<T, const T &> &&
                     requires(F &&fn) { protocyte::invoke(protocyte::forward<F>(fn)); })
        {
            if (!has_) {
                return protocyte::invoke(protocyte::forward<F>(f));
            }
            Optional out {};
            (void) out.emplace(value());
            return out;
        }

        template<class F>
        constexpr Optional or_else(F &&f) && noexcept(noexcept(protocyte::invoke(protocyte::forward<F>(f))))
            requires(OptionalType<InvokeResult<F>> &&
                     ::std::same_as<typename ::std::remove_cvref_t<InvokeResult<F>>::value_type, T> &&
                     ::std::is_constructible_v<T, T &&> &&
                     requires(F &&fn) { protocyte::invoke(protocyte::forward<F>(fn)); })
        {
            if (!has_) {
                return protocyte::invoke(protocyte::forward<F>(f));
            }
            Optional out {};
            (void) out.emplace(protocyte::move(*ptr()));
            return out;
        }

    protected:
        T *ptr() noexcept { return reinterpret_cast<T *>(&storage_[0]); }
        const T *ptr() const noexcept { return reinterpret_cast<const T *>(&storage_[0]); }

        bool has_ {};
        alignas(T) unsigned char storage_[sizeof(T)];
    };

    template<class T, class Config> struct Vector {
        using Context = typename Config::Context;
        using value_type = T;
        using iterator = T *;
        using const_iterator = const T *;
        using reverse_iterator = ReverseIterator<T>;
        using const_reverse_iterator = ReverseIterator<const T>;

        explicit Vector(Context *ctx = nullptr) noexcept: ctx_ {ctx} {}
        Vector(Vector &&other) noexcept:
            ctx_ {other.ctx_}, data_ {other.data_}, size_ {other.size_}, capacity_ {other.capacity_} {
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
        iterator begin() noexcept { return data_; }
        const_iterator begin() const noexcept { return data_; }
        iterator end() noexcept { return data_ + size_; }
        const_iterator end() const noexcept { return data_ + size_; }
        const_iterator cbegin() const noexcept { return begin(); }
        const_iterator cend() const noexcept { return end(); }
        reverse_iterator rbegin() noexcept { return reverse_iterator {end()}; }
        const_reverse_iterator rbegin() const noexcept { return const_reverse_iterator {end()}; }
        reverse_iterator rend() noexcept { return reverse_iterator {begin()}; }
        const_reverse_iterator rend() const noexcept { return const_reverse_iterator {begin()}; }
        const_reverse_iterator crbegin() const noexcept { return rbegin(); }
        const_reverse_iterator crend() const noexcept { return rend(); }

        void clear() noexcept {
            for (usize i {}; i < size_; ++i) { data_[i].~T(); }
            size_ = {};
        }

        Status reserve(const usize requested) noexcept {
            if (requested <= capacity_) {
                return {};
            }
            if (ctx_ == nullptr) {
                return protocyte::unexpected(ErrorCode::invalid_argument, {});
            }
            usize bytes {};
            if (const auto st = checked_mul(requested, sizeof(T), &bytes); !st) {
                return st;
            }
            auto *raw = Config::allocate(*ctx_, bytes, alignof(T));
            if (raw == nullptr) {
                return protocyte::unexpected(ErrorCode::no_memory, {});
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
                    return protocyte::unexpected(st.error());
                }
            }
            new (&data_[size_]) T {protocyte::forward<Args>(args)...};
            Ref<T> ref {data_[size_]};
            ++size_;
            return ref;
        }

        Status push_back(const T &value) noexcept { return emplace_back(value).status(); }

        Status push_back(T &&value) noexcept { return emplace_back(protocyte::move(value)).status(); }

        Status copy_from(const Vector &other) noexcept {
            if (this == &other) {
                return {};
            }
            clear();
            if (const auto st = reserve(other.size_); !st) {
                return st;
            }
            for (usize i {}; i < other.size_; ++i) {
                auto copied = protocyte::copy_value(ctx_, other[i]);
                if (!copied) {
                    return copied.status();
                }
                if (const auto st = push_back(protocyte::move(*copied)); !st) {
                    return st;
                }
            }
            return {};
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

    template<class T, usize Max> struct Array {
        using value_type = T;
        using iterator = T *;
        using const_iterator = const T *;
        using reverse_iterator = ReverseIterator<T>;
        using const_reverse_iterator = ReverseIterator<const T>;

        Array() noexcept = default;
        Array(Array &&other) noexcept {
            for (usize i {}; i < other.size_; ++i) { new (ptr(i)) T {protocyte::move(other[i])}; }
            size_ = other.size_;
            other.clear();
        }
        Array &operator=(Array &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            clear();
            for (usize i {}; i < other.size_; ++i) { new (ptr(i)) T {protocyte::move(other[i])}; }
            size_ = other.size_;
            other.clear();
            return *this;
        }
        Array(const Array &) = delete;
        Array &operator=(const Array &) = delete;
        ~Array() noexcept { clear(); }

        static constexpr usize max_size() noexcept { return Max; }
        constexpr usize capacity() const noexcept { return Max; }
        usize size() const noexcept { return size_; }
        bool empty() const noexcept { return !size_; }
        T *data() noexcept { return size_ ? ptr(0u) : nullptr; }
        const T *data() const noexcept { return size_ ? ptr(0u) : nullptr; }
        T &operator[](const usize index) noexcept { return *ptr(index); }
        const T &operator[](const usize index) const noexcept { return *ptr(index); }
        iterator begin() noexcept { return data(); }
        const_iterator begin() const noexcept { return data(); }
        iterator end() noexcept { return data() + size_; }
        const_iterator end() const noexcept { return data() + size_; }
        const_iterator cbegin() const noexcept { return begin(); }
        const_iterator cend() const noexcept { return end(); }
        reverse_iterator rbegin() noexcept { return reverse_iterator {end()}; }
        const_reverse_iterator rbegin() const noexcept { return const_reverse_iterator {end()}; }
        reverse_iterator rend() noexcept { return reverse_iterator {begin()}; }
        const_reverse_iterator rend() const noexcept { return const_reverse_iterator {begin()}; }
        const_reverse_iterator crbegin() const noexcept { return rbegin(); }
        const_reverse_iterator crend() const noexcept { return rend(); }

        void clear() noexcept {
            while (size_) {
                --size_;
                ptr(size_)->~T();
            }
        }

        template<class... Args> Result<Ref<T>> emplace_back(Args &&...args) noexcept {
            if (size_ >= Max) {
                return protocyte::unexpected(ErrorCode::count_limit, {});
            }
            new (ptr(size_)) T {protocyte::forward<Args>(args)...};
            Ref<T> ref {*ptr(size_)};
            ++size_;
            return ref;
        }

        Status push_back(const T &value) noexcept { return emplace_back(value).status(); }
        Status push_back(T &&value) noexcept { return emplace_back(protocyte::move(value)).status(); }

        Status copy_from(const Array &other) noexcept {
            if (this == &other) {
                return {};
            }
            clear();
            for (usize i {}; i < other.size_; ++i) {
                auto copied = protocyte::copy_value(other[i]);
                if (!copied) {
                    return copied.status();
                }
                if (const auto st = push_back(protocyte::move(*copied)); !st) {
                    return st;
                }
            }
            return {};
        }

    protected:
        T *ptr(const usize index) noexcept { return reinterpret_cast<T *>(&storage_[index * sizeof(T)]); }
        const T *ptr(const usize index) const noexcept {
            return reinterpret_cast<const T *>(&storage_[index * sizeof(T)]);
        }

        alignas(T) unsigned char storage_[sizeof(T) * Max];
        usize size_ {};
    };

    template<usize Max> struct ByteArray {
        using value_type = u8;
        using iterator = u8 *;
        using const_iterator = const u8 *;
        using reverse_iterator = ReverseIterator<u8>;
        using const_reverse_iterator = ReverseIterator<const u8>;

        ByteArray() noexcept = default;
        ByteArray(ByteArray &&other) noexcept: size_ {other.size_} {
            for (usize i {}; i < other.size_; ++i) { bytes_[i] = other.bytes_[i]; }
            other.size_ = {};
        }
        ByteArray &operator=(ByteArray &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            size_ = other.size_;
            for (usize i {}; i < other.size_; ++i) { bytes_[i] = other.bytes_[i]; }
            other.size_ = {};
            return *this;
        }
        ByteArray(const ByteArray &) = delete;
        ByteArray &operator=(const ByteArray &) = delete;

        static constexpr usize max_size() noexcept { return Max; }
        ByteView view() const noexcept { return {.data = bytes_, .size = size_}; }
        MutableByteView mutable_view() noexcept { return {.data = bytes_, .size = size_}; }
        u8 *data() noexcept { return bytes_; }
        const u8 *data() const noexcept { return bytes_; }
        usize size() const noexcept { return size_; }
        bool empty() const noexcept { return !size_; }
        iterator begin() noexcept { return bytes_; }
        const_iterator begin() const noexcept { return bytes_; }
        iterator end() noexcept { return bytes_ + size_; }
        const_iterator end() const noexcept { return bytes_ + size_; }
        const_iterator cbegin() const noexcept { return begin(); }
        const_iterator cend() const noexcept { return end(); }
        reverse_iterator rbegin() noexcept { return reverse_iterator {end()}; }
        const_reverse_iterator rbegin() const noexcept { return const_reverse_iterator {end()}; }
        reverse_iterator rend() noexcept { return reverse_iterator {begin()}; }
        const_reverse_iterator rend() const noexcept { return const_reverse_iterator {begin()}; }
        const_reverse_iterator crbegin() const noexcept { return rbegin(); }
        const_reverse_iterator crend() const noexcept { return rend(); }
        void clear() noexcept { size_ = {}; }

        Status resize(const usize count) noexcept {
            if (count > Max) {
                return protocyte::unexpected(ErrorCode::count_limit, {});
            }
            if (count > size_) {
                for (usize i {size_}; i < count; ++i) { bytes_[i] = 0u; }
            }
            size_ = count;
            return {};
        }

        Status assign(const ByteView view) noexcept {
            if (view.size > Max) {
                return protocyte::unexpected(ErrorCode::count_limit, {});
            }
            copy_bytes(bytes_, view.data, view.size);
            size_ = view.size;
            return {};
        }

    protected:
        u8 bytes_[Max];
        usize size_ {};
    };

    template<usize Max> struct FixedByteArray {
        using value_type = u8;
        using iterator = u8 *;
        using const_iterator = const u8 *;
        using reverse_iterator = ReverseIterator<u8>;
        using const_reverse_iterator = ReverseIterator<const u8>;

        FixedByteArray() noexcept = default;
        FixedByteArray(FixedByteArray &&other) noexcept: has_ {other.has_} {
            if (other.has_) {
                for (usize i {}; i < Max; ++i) { bytes_[i] = other.bytes_[i]; }
            }
            other.has_ = false;
        }
        FixedByteArray &operator=(FixedByteArray &&other) noexcept {
            if (this == &other) {
                return *this;
            }
            has_ = other.has_;
            if (other.has_) {
                for (usize i {}; i < Max; ++i) { bytes_[i] = other.bytes_[i]; }
            }
            other.has_ = false;
            return *this;
        }
        FixedByteArray(const FixedByteArray &) = delete;
        FixedByteArray &operator=(const FixedByteArray &) = delete;

        static constexpr usize fixed_size() noexcept { return Max; }
        ByteView view() const noexcept { return has_ ? ByteView {.data = bytes_, .size = Max} : ByteView {}; }
        MutableByteView mutable_view() noexcept {
            if (!has_) {
                for (usize i {}; i < Max; ++i) { bytes_[i] = 0u; }
            }
            has_ = true;
            return {.data = bytes_, .size = Max};
        }
        u8 *data() noexcept { return bytes_; }
        const u8 *data() const noexcept { return bytes_; }
        usize size() const noexcept { return has_ ? Max : 0u; }
        bool empty() const noexcept { return !has_; }
        bool has_value() const noexcept { return has_; }
        iterator begin() noexcept { return bytes_; }
        const_iterator begin() const noexcept { return bytes_; }
        iterator end() noexcept { return bytes_ + size(); }
        const_iterator end() const noexcept { return bytes_ + size(); }
        const_iterator cbegin() const noexcept { return begin(); }
        const_iterator cend() const noexcept { return end(); }
        reverse_iterator rbegin() noexcept { return reverse_iterator {end()}; }
        const_reverse_iterator rbegin() const noexcept { return const_reverse_iterator {end()}; }
        reverse_iterator rend() noexcept { return reverse_iterator {begin()}; }
        const_reverse_iterator rend() const noexcept { return const_reverse_iterator {begin()}; }
        const_reverse_iterator crbegin() const noexcept { return rbegin(); }
        const_reverse_iterator crend() const noexcept { return rend(); }
        void clear() noexcept { has_ = false; }

        Status assign(const ByteView view) noexcept {
            if (view.size != Max) {
                return protocyte::unexpected(ErrorCode::invalid_argument, {});
            }
            copy_bytes(bytes_, view.data, Max);
            has_ = true;
            return {};
        }

    protected:
        u8 bytes_[Max];
        bool has_ {};
    };

    template<class Config> struct Bytes {
        using Context = typename Config::Context;
        using value_type = u8;
        using iterator = typename Config::template Vector<u8>::iterator;
        using const_iterator = typename Config::template Vector<u8>::const_iterator;
        using reverse_iterator = typename Config::template Vector<u8>::reverse_iterator;
        using const_reverse_iterator = typename Config::template Vector<u8>::const_reverse_iterator;

        explicit Bytes(Context *ctx = nullptr) noexcept: ctx_ {ctx}, bytes_ {ctx} {}
        Bytes(Bytes &&other) noexcept: ctx_ {other.ctx_}, bytes_ {protocyte::move(other.bytes_)} {}
        Bytes &operator=(Bytes &&other) noexcept {
            ctx_ = other.ctx_;
            bytes_ = protocyte::move(other.bytes_);
            return *this;
        }
        Bytes(const Bytes &) = delete;
        Bytes &operator=(const Bytes &) = delete;

        ByteView view() const noexcept { return {.data = bytes_.data(), .size = bytes_.size()}; }
        MutableByteView mutable_view() noexcept { return {.data = bytes_.data(), .size = bytes_.size()}; }
        iterator begin() noexcept { return bytes_.begin(); }
        const_iterator begin() const noexcept { return bytes_.begin(); }
        iterator end() noexcept { return bytes_.end(); }
        const_iterator end() const noexcept { return bytes_.end(); }
        const_iterator cbegin() const noexcept { return bytes_.cbegin(); }
        const_iterator cend() const noexcept { return bytes_.cend(); }
        reverse_iterator rbegin() noexcept { return bytes_.rbegin(); }
        const_reverse_iterator rbegin() const noexcept { return bytes_.rbegin(); }
        reverse_iterator rend() noexcept { return bytes_.rend(); }
        const_reverse_iterator rend() const noexcept { return bytes_.rend(); }
        const_reverse_iterator crbegin() const noexcept { return bytes_.crbegin(); }
        const_reverse_iterator crend() const noexcept { return bytes_.crend(); }
        u8 *data() noexcept { return bytes_.data(); }
        const u8 *data() const noexcept { return bytes_.data(); }
        Context *context() const noexcept { return ctx_; }
        usize size() const noexcept { return bytes_.size(); }
        bool empty() const noexcept { return bytes_.empty(); }
        void clear() noexcept { bytes_.clear(); }
        void bind(Context *ctx) noexcept {
            ctx_ = ctx;
            bytes_.bind(ctx);
        }
        Status resize(const usize count) noexcept {
            if (ctx_ != nullptr && count > ctx_->limits.max_string_bytes) {
                return protocyte::unexpected(ErrorCode::size_limit, {});
            }
            return bytes_.resize_default(count);
        }

        Status assign(const ByteView view) noexcept {
            if (ctx_ != nullptr && view.size > ctx_->limits.max_string_bytes) {
                return protocyte::unexpected(ErrorCode::size_limit, {});
            }
            Bytes temp {ctx_};
            if (const auto st = temp.resize(view.size); !st) {
                return st;
            }
            copy_bytes(temp.data(), view.data, view.size);
            *this = protocyte::move(temp);
            return {};
        }

    protected:
        Context *ctx_;
        typename Config::template Vector<u8> bytes_;
    };

    template<class Config> struct String {
        using Context = typename Config::Context;
        using value_type = const u8;
        using iterator = typename Config::Bytes::const_iterator;
        using const_iterator = typename Config::Bytes::const_iterator;
        using reverse_iterator = typename Config::Bytes::const_reverse_iterator;
        using const_reverse_iterator = typename Config::Bytes::const_reverse_iterator;

        explicit String(Context *ctx = nullptr) noexcept: bytes_ {ctx} {}
        String(String &&other) noexcept: bytes_ {protocyte::move(other.bytes_)} {}
        String &operator=(String &&other) noexcept {
            bytes_ = protocyte::move(other.bytes_);
            return *this;
        }
        String(const String &) = delete;
        String &operator=(const String &) = delete;

        ByteView view() const noexcept { return bytes_.view(); }
        const_iterator begin() const noexcept { return bytes_.begin(); }
        const_iterator end() const noexcept { return bytes_.end(); }
        const_iterator cbegin() const noexcept { return bytes_.cbegin(); }
        const_iterator cend() const noexcept { return bytes_.cend(); }
        const_reverse_iterator rbegin() const noexcept { return bytes_.rbegin(); }
        const_reverse_iterator rend() const noexcept { return bytes_.rend(); }
        const_reverse_iterator crbegin() const noexcept { return bytes_.crbegin(); }
        const_reverse_iterator crend() const noexcept { return bytes_.crend(); }
        const u8 *data() const noexcept { return bytes_.data(); }
        Context *context() const noexcept { return bytes_.context(); }
        usize size() const noexcept { return bytes_.size(); }
        bool empty() const noexcept { return bytes_.empty(); }
        void clear() noexcept { bytes_.clear(); }

        Status assign(const ByteView view) noexcept {
            if (!validate_utf8(view)) {
                return protocyte::unexpected(ErrorCode::invalid_utf8, {});
            }
            return bytes_.assign(view);
        }

        Status assign_owned(typename Config::Bytes &&bytes) noexcept {
            if (!validate_utf8(bytes.view())) {
                return protocyte::unexpected(ErrorCode::invalid_utf8, {});
            }
            bytes_ = protocyte::move(bytes);
            return {};
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

        explicit Box(Context *ctx = nullptr) noexcept: ctx_ {ctx} {}
        Box(Box &&other) noexcept: ctx_ {other.ctx_}, ptr_ {other.ptr_} { other.ptr_ = nullptr; }
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
        T &operator*() noexcept { return *ptr_; }
        const T &operator*() const noexcept { return *ptr_; }
        T *operator->() noexcept { return ptr_; }
        const T *operator->() const noexcept { return ptr_; }
        T &value() noexcept { return *ptr_; }
        const T &value() const noexcept { return *ptr_; }

        Result<Ref<T>> ensure() noexcept {
            if (ptr_ != nullptr) {
                return Ref<T> {*ptr_};
            }
            if (ctx_ == nullptr) {
                return protocyte::unexpected(ErrorCode::invalid_argument, {});
            }
            auto *raw = Config::allocate(*ctx_, sizeof(T), alignof(T));
            if (raw == nullptr) {
                return protocyte::unexpected(ErrorCode::no_memory, {});
            }
            ptr_ = new (raw) T {*ctx_};
            return Ref<T> {*ptr_};
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
        struct Entry {
            K key;
            V value;

            template<class KeyArg, class ValueArg> explicit Entry(KeyArg &&key_arg, ValueArg &&value_arg) noexcept:
                key {protocyte::forward<KeyArg>(key_arg)}, value {protocyte::forward<ValueArg>(value_arg)} {}
        };

        using Context = typename Config::Context;
        using Bucket = Optional<Entry>;

        struct EntryProxy {
            const K &key;
            V &value;
        };

        struct ConstEntryProxy {
            const K &key;
            const V &value;
        };

        struct iterator {
            using value_type = Entry;
            using difference_type = isize;
            using reference = EntryProxy;

            constexpr iterator() noexcept = default;
            constexpr iterator(Bucket *current, Bucket *end) noexcept: current_ {current}, end_ {end} { skip_empty(); }

            constexpr reference operator*() const noexcept { return {(*current_)->key, (*current_)->value}; }

            constexpr iterator &operator++() noexcept {
                ++current_;
                skip_empty();
                return *this;
            }

            constexpr iterator operator++(int) noexcept {
                auto copy = *this;
                ++(*this);
                return copy;
            }

            friend constexpr bool operator==(const iterator lhs, const iterator rhs) noexcept {
                return lhs.current_ == rhs.current_;
            }

            friend constexpr bool operator!=(const iterator lhs, const iterator rhs) noexcept {
                return lhs.current_ != rhs.current_;
            }

            friend struct const_iterator;

        protected:
            constexpr void skip_empty() noexcept {
                while (current_ != end_ && !current_->has_value()) { ++current_; }
            }

            Bucket *current_ {};
            Bucket *end_ {};
        };

        struct const_iterator {
            using value_type = Entry;
            using difference_type = isize;
            using reference = ConstEntryProxy;

            constexpr const_iterator() noexcept = default;
            constexpr const_iterator(const Bucket *current, const Bucket *end) noexcept:
                current_ {current}, end_ {end} {
                skip_empty();
            }
            constexpr const_iterator(const iterator other) noexcept: current_ {other.current_}, end_ {other.end_} {
                skip_empty();
            }

            constexpr reference operator*() const noexcept { return {(*current_)->key, (*current_)->value}; }

            constexpr const_iterator &operator++() noexcept {
                ++current_;
                skip_empty();
                return *this;
            }

            constexpr const_iterator operator++(int) noexcept {
                auto copy = *this;
                ++(*this);
                return copy;
            }

            friend constexpr bool operator==(const const_iterator lhs, const const_iterator rhs) noexcept {
                return lhs.current_ == rhs.current_;
            }

            friend constexpr bool operator!=(const const_iterator lhs, const const_iterator rhs) noexcept {
                return lhs.current_ != rhs.current_;
            }

        protected:
            constexpr void skip_empty() noexcept {
                while (current_ != end_ && !current_->has_value()) { ++current_; }
            }

            const Bucket *current_ {};
            const Bucket *end_ {};
        };

        explicit HashMap(Context *ctx = nullptr) noexcept: ctx_ {ctx}, buckets_ {ctx} {}
        HashMap(HashMap &&other) noexcept:
            ctx_ {other.ctx_}, buckets_ {protocyte::move(other.buckets_)}, size_ {other.size_} {
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
        iterator begin() noexcept { return iterator {buckets_.begin(), buckets_.end()}; }
        const_iterator begin() const noexcept { return const_iterator {buckets_.begin(), buckets_.end()}; }
        iterator end() noexcept { return iterator {buckets_.end(), buckets_.end()}; }
        const_iterator end() const noexcept { return const_iterator {buckets_.end(), buckets_.end()}; }
        const_iterator cbegin() const noexcept { return begin(); }
        const_iterator cend() const noexcept { return end(); }
        void clear() noexcept {
            for (usize i {}; i < buckets_.size(); ++i) { buckets_[i].reset(); }
            size_ = {};
        }

        Status copy_from(const HashMap &other) noexcept {
            if (this == &other) {
                return {};
            }
            clear();
            if (other.size_ == 0u) {
                return {};
            }
            if (const auto st = reserve(other.size_); !st) {
                return st;
            }
            for (const auto entry : other) {
                auto copied_key = protocyte::copy_value(ctx_, entry.key);
                if (!copied_key) {
                    return copied_key.status();
                }
                auto copied_value = protocyte::copy_value(ctx_, entry.value);
                if (!copied_value) {
                    return copied_value.status();
                }
                if (const auto st = insert_or_assign(protocyte::move(*copied_key), protocyte::move(*copied_value));
                    !st) {
                    return st;
                }
            }
            return {};
        }

        Status reserve(const usize count) noexcept {
            usize desired {8u};
            while (desired < count * 2u) { desired *= 2u; }
            if (desired <= buckets_.size()) {
                return {};
            }
            HashMap next {ctx_};
            if (const auto st = next.buckets_.resize_default(desired); !st) {
                return st;
            }
            for (usize i {}; i < buckets_.size(); ++i) {
                if (buckets_[i].has_value()) {
                    if (const auto st = next.insert_or_assign(protocyte::move((*buckets_[i]).key),
                                                              protocyte::move((*buckets_[i]).value));
                        !st) {
                        return st;
                    }
                }
            }
            *this = protocyte::move(next);
            return {};
        }

        Status insert_or_assign(K &&key, V &&value) noexcept {
            if (buckets_.size()) {
                usize existing_index {Config::hash(key) & (buckets_.size() - 1u)};
                for (;;) {
                    auto &bucket = buckets_[existing_index];
                    if (!bucket.has_value()) {
                        break;
                    }
                    if (Config::equal((*bucket).key, key)) {
                        K stored_key {protocyte::move((*bucket).key)};
                        bucket.reset();
                        bucket.emplace(protocyte::move(stored_key), protocyte::move(value));
                        return {};
                    }
                    existing_index = (existing_index + 1u) & (buckets_.size() - 1u);
                }
            }
            if (const auto st = ensure_capacity_for_one_more(); !st) {
                return st;
            }
            usize index {Config::hash(key) & (buckets_.size() - 1u)};
            for (;;) {
                if (auto &bucket = buckets_[index]; !bucket.has_value()) {
                    bucket.emplace(protocyte::move(key), protocyte::move(value));
                    ++size_;
                    return {};
                }
                index = (index + 1u) & (buckets_.size() - 1u);
            }
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
        SliceReader(const u8 *data, const usize size) noexcept: data_ {data}, size_ {size} {}
        bool eof() const noexcept { return pos_ >= size_; }
        usize position() const noexcept { return pos_; }
        Result<u8> read_byte() noexcept {
            if (pos_ >= size_) {
                return protocyte::unexpected(ErrorCode::unexpected_eof, pos_);
            }
            return data_[pos_++];
        }
        Status read(u8 *out, const usize count) noexcept {
            if (count > size_ - pos_) {
                return protocyte::unexpected(ErrorCode::unexpected_eof, pos_);
            }
            for (usize i {}; i < count; ++i) { out[i] = data_[pos_ + i]; }
            pos_ += count;
            return {};
        }
        Status skip(const usize count) noexcept {
            if (count > size_ - pos_) {
                return protocyte::unexpected(ErrorCode::unexpected_eof, pos_);
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
            reader_ {&reader},
            eof_ {&eof_impl<Reader>},
            position_ {&position_impl<Reader>},
            read_byte_ {&read_byte_impl<Reader>},
            read_ {&read_impl<Reader>},
            skip_ {&skip_impl<Reader>} {}

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
        LimitedReader(Reader &inner, const usize remaining) noexcept: inner_ {&inner}, remaining_ {remaining} {}
        bool eof() const noexcept { return !remaining_; }
        usize position() const noexcept { return pos_; }
        Result<u8> read_byte() noexcept {
            if (!remaining_) {
                return protocyte::unexpected(ErrorCode::unexpected_eof, pos_);
            }
            auto byte = inner_->read_byte();
            if (!byte) {
                return protocyte::unexpected(byte.error());
            }
            --remaining_;
            ++pos_;
            return byte;
        }
        Status read(u8 *out, const usize count) noexcept {
            if (count > remaining_) {
                return protocyte::unexpected(ErrorCode::unexpected_eof, pos_);
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
                return protocyte::unexpected(ErrorCode::unexpected_eof, pos_);
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

    template<class Config>
    Status push_recursion(typename Config::Context &ctx, const usize offset, const u32 field_number) noexcept {
        static_assert(
            requires(typename Config::Context &value) { value.recursion_depth; },
            "protocyte Config::Context must expose recursion_depth for recursion-limited parsing");
        if (ctx.recursion_depth >= ctx.limits.max_recursion_depth) {
            return protocyte::unexpected(ErrorCode::recursion_limit, offset, field_number);
        }
        ++ctx.recursion_depth;
        return {};
    }

    template<class Config> void pop_recursion(typename Config::Context &ctx) noexcept {
        if (ctx.recursion_depth != 0u) {
            --ctx.recursion_depth;
        }
    }

    template<class Reader, class Config> struct NestedMessageReader {
        using Context = typename Config::Context;

        NestedMessageReader(Context &ctx, Reader &inner, const usize remaining) noexcept:
            ctx_ {&ctx}, reader_ {inner, remaining}, active_ {true} {}
        NestedMessageReader(NestedMessageReader &&other) noexcept:
            ctx_ {other.ctx_}, reader_ {protocyte::move(other.reader_)}, active_ {other.active_} {
            other.ctx_ = nullptr;
            other.active_ = false;
        }
        NestedMessageReader &operator=(NestedMessageReader &&) noexcept = delete;
        NestedMessageReader(const NestedMessageReader &) = delete;
        NestedMessageReader &operator=(const NestedMessageReader &) = delete;
        ~NestedMessageReader() noexcept { release(); }

        LimitedReader<Reader> &reader() noexcept { return reader_; }
        ReaderRef reader_ref() noexcept { return ReaderRef {reader_}; }

        Status finish() noexcept {
            auto st = reader_.finish();
            release();
            return st;
        }

    protected:
        void release() noexcept {
            if (active_ && ctx_ != nullptr) {
                pop_recursion<Config>(*ctx_);
                active_ = false;
                ctx_ = nullptr;
            }
        }

        Context *ctx_ {};
        LimitedReader<Reader> reader_;
        bool active_ {};
    };

    struct SliceWriter {
        SliceWriter(u8 *data, const usize capacity) noexcept: data_ {data}, capacity_ {capacity} {}
        usize position() const noexcept { return pos_; }
        Status write_byte(const u8 value) noexcept {
            if (pos_ >= capacity_) {
                return protocyte::unexpected(ErrorCode::size_limit, pos_);
            }
            data_[pos_++] = value;
            return {};
        }
        Status write(const u8 *data, const usize count) noexcept {
            if (count > capacity_ - pos_) {
                return protocyte::unexpected(ErrorCode::size_limit, pos_);
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
                return protocyte::unexpected(byte.error());
            }
            value |= (static_cast<u64>(*byte & 0x7Fu) << shift);
            if ((*byte & 0x80u) == 0u) {
                return value;
            }
            shift += 7u;
        }
        return protocyte::unexpected(ErrorCode::malformed_varint, reader.position());
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
        const auto bits = static_cast<u32>(value);
        return (bits << 1u) ^ (static_cast<u32>(0u) - (bits >> 31u));
    }

    constexpr u64 encode_zigzag64(const i64 value) noexcept {
        const auto bits = static_cast<u64>(value);
        return (bits << 1u) ^ (static_cast<u64>(0u) - (bits >> 63u));
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
            return protocyte::unexpected(st.error());
        }
        const auto value = static_cast<u32>(bytes[0]) | (static_cast<u32>(bytes[1]) << 8u) |
                           (static_cast<u32>(bytes[2]) << 16u) | (static_cast<u32>(bytes[3]) << 24u);
        return value;
    }

    template<class Reader> Result<u64> read_fixed64(Reader &reader) noexcept {
        u8 bytes[8u];
        if (const auto st = reader.read(bytes, 8u); !st) {
            return protocyte::unexpected(st.error());
        }
        u64 value {};
        for (u32 i {}; i < 8u; ++i) { value |= static_cast<u64>(bytes[i]) << (i * 8u); }
        return value;
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
            static_cast<u8>(value),        static_cast<u8>(value >> 8u),  static_cast<u8>(value >> 16u),
            static_cast<u8>(value >> 24u), static_cast<u8>(value >> 32u), static_cast<u8>(value >> 40u),
            static_cast<u8>(value >> 48u), static_cast<u8>(value >> 56u),
        };
        return writer.write(bytes, 8u);
    }

    template<class Reader> Status expect_wire_type(Reader &reader, const WireType actual, const WireType expected,
                                                   const u32 field_number) noexcept {
        if (actual != expected) {
            return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field_number);
        }
        return {};
    }

    template<class T, class Reader> Result<T> read_varint_scalar(Reader &reader) noexcept {
        auto raw = read_varint(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return static_cast<T>(*raw);
    }

    template<class T, class Reader> Result<T> read_zigzag32_scalar(Reader &reader) noexcept {
        auto raw = read_varint(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return static_cast<T>(decode_zigzag32(static_cast<u32>(*raw)));
    }

    template<class T, class Reader> Result<T> read_zigzag64_scalar(Reader &reader) noexcept {
        auto raw = read_varint(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return static_cast<T>(decode_zigzag64(*raw));
    }

    template<class T, class Reader> Result<T> read_fixed32_scalar(Reader &reader) noexcept {
        auto raw = read_fixed32(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return static_cast<T>(*raw);
    }

    template<class T, class Reader> Result<T> read_fixed64_scalar(Reader &reader) noexcept {
        auto raw = read_fixed64(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return static_cast<T>(*raw);
    }

    template<class Reader> Result<i32> read_int32(Reader &reader) noexcept { return read_varint_scalar<i32>(reader); }

    template<class Reader> Result<i64> read_int64(Reader &reader) noexcept { return read_varint_scalar<i64>(reader); }

    template<class Reader> Result<u32> read_uint32(Reader &reader) noexcept { return read_varint_scalar<u32>(reader); }

    template<class Reader> Result<u64> read_uint64(Reader &reader) noexcept { return read_varint_scalar<u64>(reader); }

    template<class Reader> Result<bool> read_bool(Reader &reader) noexcept {
        auto raw = read_varint(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return *raw != 0u;
    }

    template<class Reader> Result<i32> read_enum(Reader &reader) noexcept { return read_varint_scalar<i32>(reader); }

    template<class Reader> Result<i32> read_sint32(Reader &reader) noexcept {
        return read_zigzag32_scalar<i32>(reader);
    }

    template<class Reader> Result<i64> read_sint64(Reader &reader) noexcept {
        return read_zigzag64_scalar<i64>(reader);
    }

    template<class Reader> Result<u32> read_fixed32_value(Reader &reader) noexcept {
        return read_fixed32_scalar<u32>(reader);
    }

    template<class Reader> Result<u64> read_fixed64_value(Reader &reader) noexcept {
        return read_fixed64_scalar<u64>(reader);
    }

    template<class Reader> Result<i32> read_sfixed32(Reader &reader) noexcept {
        return read_fixed32_scalar<i32>(reader);
    }

    template<class Reader> Result<i64> read_sfixed64(Reader &reader) noexcept {
        return read_fixed64_scalar<i64>(reader);
    }

    template<class Reader> Result<f32> read_float(Reader &reader) noexcept {
        auto raw = read_fixed32(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return ::std::bit_cast<f32>(*raw);
    }

    template<class Reader> Result<f64> read_double(Reader &reader) noexcept {
        auto raw = read_fixed64(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return ::std::bit_cast<f64>(*raw);
    }

    template<class Writer, class T> Status write_varint_scalar(Writer &writer, const T value) noexcept {
        return write_varint(writer, static_cast<u64>(value));
    }

    template<class Writer> Status write_int32(Writer &writer, const i32 value) noexcept {
        return write_varint_scalar(writer, value);
    }

    template<class Writer> Status write_int64(Writer &writer, const i64 value) noexcept {
        return write_varint_scalar(writer, value);
    }

    template<class Writer> Status write_uint32(Writer &writer, const u32 value) noexcept {
        return write_varint_scalar(writer, value);
    }

    template<class Writer> Status write_uint64(Writer &writer, const u64 value) noexcept {
        return write_varint_scalar(writer, value);
    }

    template<class Writer> Status write_bool(Writer &writer, const bool value) noexcept {
        return write_varint(writer, value ? 1u : 0u);
    }

    template<class Writer> Status write_enum(Writer &writer, const i32 value) noexcept {
        return write_varint_scalar(writer, value);
    }

    template<class Writer> Status write_sint32(Writer &writer, const i32 value) noexcept {
        return write_varint(writer, encode_zigzag32(value));
    }

    template<class Writer> Status write_sint64(Writer &writer, const i64 value) noexcept {
        return write_varint(writer, encode_zigzag64(value));
    }

    template<class Writer> Status write_fixed32_value(Writer &writer, const u32 value) noexcept {
        return write_fixed32(writer, value);
    }

    template<class Writer> Status write_fixed64_value(Writer &writer, const u64 value) noexcept {
        return write_fixed64(writer, value);
    }

    template<class Writer> Status write_sfixed32(Writer &writer, const i32 value) noexcept {
        return write_fixed32(writer, static_cast<u32>(value));
    }

    template<class Writer> Status write_sfixed64(Writer &writer, const i64 value) noexcept {
        return write_fixed64(writer, static_cast<u64>(value));
    }

    template<class Writer> Status write_float(Writer &writer, const f32 value) noexcept {
        return write_fixed32(writer, ::std::bit_cast<u32>(value));
    }

    template<class Writer> Status write_double(Writer &writer, const f64 value) noexcept {
        return write_fixed64(writer, ::std::bit_cast<u64>(value));
    }

    template<class Writer> Status write_tag(Writer &writer, const u32 field_number, const WireType wire_type) noexcept {
        return write_varint(writer, (static_cast<u64>(field_number) << 3u) | static_cast<u64>(wire_type));
    }

    constexpr usize tag_size(const u32 field_number, const WireType wire_type = WireType::LEN) noexcept {
        const auto size = varint_size((static_cast<u64>(field_number) << 3u) | static_cast<u64>(wire_type));
        return wire_type == WireType::SGROUP ? size * 2u : size;
    }

    constexpr Tag decode_tag(const u64 raw) noexcept {
        return Tag {
            .field_number = static_cast<u32>(raw >> 3u),
            .wire_type = static_cast<WireType>(raw & 0x7u),
        };
    }

    template<class Reader> Result<Tag> read_tag(Reader &reader) noexcept {
        auto raw = read_varint(reader);
        if (!raw) {
            return protocyte::unexpected(raw.error());
        }
        return decode_tag(*raw);
    }

    template<class Reader>
    Result<i32> read_int32_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_int32(reader);
        });
    }

    template<class Reader>
    Result<i64> read_int64_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_int64(reader);
        });
    }

    template<class Reader>
    Result<u32> read_uint32_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_uint32(reader);
        });
    }

    template<class Reader>
    Result<u64> read_uint64_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_uint64(reader);
        });
    }

    template<class Reader>
    Result<bool> read_bool_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_bool(reader);
        });
    }

    template<class Reader>
    Result<i32> read_enum_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_enum(reader);
        });
    }

    template<class Reader>
    Result<i32> read_sint32_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_sint32(reader);
        });
    }

    template<class Reader>
    Result<i64> read_sint64_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::VARINT, field_number).and_then([&reader]() noexcept {
            return read_sint64(reader);
        });
    }

    template<class Reader>
    Result<u32> read_fixed32_value_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::I32, field_number).and_then([&reader]() noexcept {
            return read_fixed32_value(reader);
        });
    }

    template<class Reader>
    Result<u64> read_fixed64_value_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::I64, field_number).and_then([&reader]() noexcept {
            return read_fixed64_value(reader);
        });
    }

    template<class Reader>
    Result<i32> read_sfixed32_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::I32, field_number).and_then([&reader]() noexcept {
            return read_sfixed32(reader);
        });
    }

    template<class Reader>
    Result<i64> read_sfixed64_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::I64, field_number).and_then([&reader]() noexcept {
            return read_sfixed64(reader);
        });
    }

    template<class Reader>
    Result<f32> read_float_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::I32, field_number).and_then([&reader]() noexcept {
            return read_float(reader);
        });
    }

    template<class Reader>
    Result<f64> read_double_field(Reader &reader, const WireType wire_type, const u32 field_number) noexcept {
        return expect_wire_type(reader, wire_type, WireType::I64, field_number).and_then([&reader]() noexcept {
            return read_double(reader);
        });
    }

    template<class Writer> Status write_int32_field(Writer &writer, const u32 field_number, const i32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_int32(writer, value);
    }

    template<class Writer> Status write_int64_field(Writer &writer, const u32 field_number, const i64 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_int64(writer, value);
    }

    template<class Writer> Status write_uint32_field(Writer &writer, const u32 field_number, const u32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_uint32(writer, value);
    }

    template<class Writer> Status write_uint64_field(Writer &writer, const u32 field_number, const u64 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_uint64(writer, value);
    }

    template<class Writer> Status write_bool_field(Writer &writer, const u32 field_number, const bool value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_bool(writer, value);
    }

    template<class Writer> Status write_enum_field(Writer &writer, const u32 field_number, const i32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_enum(writer, value);
    }

    template<class Writer> Status write_sint32_field(Writer &writer, const u32 field_number, const i32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_sint32(writer, value);
    }

    template<class Writer> Status write_sint64_field(Writer &writer, const u32 field_number, const i64 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::VARINT); !st) {
            return st;
        }
        return write_sint64(writer, value);
    }

    template<class Writer>
    Status write_fixed32_value_field(Writer &writer, const u32 field_number, const u32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::I32); !st) {
            return st;
        }
        return write_fixed32_value(writer, value);
    }

    template<class Writer>
    Status write_fixed64_value_field(Writer &writer, const u32 field_number, const u64 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::I64); !st) {
            return st;
        }
        return write_fixed64_value(writer, value);
    }

    template<class Writer>
    Status write_sfixed32_field(Writer &writer, const u32 field_number, const i32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::I32); !st) {
            return st;
        }
        return write_sfixed32(writer, value);
    }

    template<class Writer>
    Status write_sfixed64_field(Writer &writer, const u32 field_number, const i64 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::I64); !st) {
            return st;
        }
        return write_sfixed64(writer, value);
    }

    template<class Writer> Status write_float_field(Writer &writer, const u32 field_number, const f32 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::I32); !st) {
            return st;
        }
        return write_float(writer, value);
    }

    template<class Writer> Status write_double_field(Writer &writer, const u32 field_number, const f64 value) noexcept {
        if (const auto st = write_tag(writer, field_number, WireType::I64); !st) {
            return st;
        }
        return write_double(writer, value);
    }

    template<class Reader> Result<usize> read_length_delimited_size(Reader &reader) noexcept {
        return read_varint(reader).and_then([&reader](const u64 len) noexcept -> Result<usize> {
            if (len > static_cast<u64>(~static_cast<usize>(0u))) {
                return protocyte::unexpected(ErrorCode::integer_overflow, reader.position());
            }
            return static_cast<usize>(len);
        });
    }

    template<class Config, class Reader>
    Result<NestedMessageReader<Reader, Config>> open_nested_message_sized(typename Config::Context &ctx, Reader &reader,
                                                                          const usize size,
                                                                          const u32 field_number) noexcept {
        if (size > ctx.limits.max_message_bytes) {
            return protocyte::unexpected(ErrorCode::size_limit, reader.position(), field_number);
        }
        return push_recursion<Config>(ctx, reader.position(), field_number)
            .transform([&ctx, &reader, size]() noexcept -> NestedMessageReader<Reader, Config> {
                return NestedMessageReader<Reader, Config> {ctx, reader, size};
            });
    }

    template<class Config, class Reader> Result<NestedMessageReader<Reader, Config>>
    open_nested_message(typename Config::Context &ctx, Reader &reader, const u32 field_number) noexcept {
        return read_length_delimited_size(reader).and_then([&ctx, &reader, field_number](const usize size) noexcept {
            return open_nested_message_sized<Config>(ctx, reader, size, field_number);
        });
    }

    template<class Config, class Reader, class Message>
    Status read_message(typename Config::Context &ctx, Reader &reader, const u32 field_number, Message &out) noexcept {
        auto nested = open_nested_message<Config>(ctx, reader, field_number);
        if (!nested) {
            return nested.status();
        }
        auto &open = *nested;
        auto nested_reader = open.reader_ref();
        return out.merge_from(nested_reader).and_then([&open]() noexcept -> Status { return open.finish(); });
    }

    template<class Writer, class Message>
    Status write_message_field(Writer &writer, const u32 field_number, const Message &value) noexcept {
        return write_tag(writer, field_number, WireType::LEN).and_then([&writer, &value]() noexcept -> Status {
            return value.encoded_size().and_then([&writer, &value](const usize size) noexcept -> Status {
                return write_varint(writer, static_cast<u64>(size)).and_then([&writer, &value]() noexcept -> Status {
                    return value.serialize(writer);
                });
            });
        });
    }

    template<class Message> Result<usize> message_field_size(const u32 field_number, const Message &value) noexcept {
        return value.encoded_size().transform(
            [field_number](const usize size) noexcept { return tag_size(field_number) + varint_size(size) + size; });
    }

    template<class Reader> Status skip_group(Reader &reader, u32 start_field_number) noexcept;
    template<class Config, class Reader>
    Status skip_group(typename Config::Context &ctx, Reader &reader, u32 start_field_number) noexcept;

    template<class Reader>
    Status skip_field(Reader &reader, const WireType wire_type, const u32 field_number = {}) noexcept {
        switch (wire_type) {
            case WireType::VARINT: {
                return read_varint(reader).status();
            }
            case WireType::I64: return reader.skip(8u);
            case WireType::LEN: {
                return read_length_delimited_size(reader).and_then(
                    [&reader](const usize len) noexcept -> Status { return reader.skip(len); });
            }
            case WireType::SGROUP: return skip_group(reader, field_number);
            case WireType::EGROUP: return {};
            case WireType::I32: return reader.skip(4u);
            default: return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field_number);
        }
    }

    template<class Config, class Reader> Status skip_field(typename Config::Context &ctx, Reader &reader,
                                                           const WireType wire_type,
                                                           const u32 field_number = {}) noexcept {
        switch (wire_type) {
            case WireType::VARINT: {
                return read_varint(reader).status();
            }
            case WireType::I64: return reader.skip(8u);
            case WireType::LEN: {
                auto len = read_length_delimited_size(reader);
                if (!len) {
                    return len.status();
                }
                return reader.skip(*len);
            }
            case WireType::SGROUP: return skip_group<Config>(ctx, reader, field_number);
            case WireType::EGROUP: return {};
            case WireType::I32: return reader.skip(4u);
            default: return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field_number);
        }
    }

    template<class Reader> Status skip_group(Reader &reader, const u32 start_field_number) noexcept {
        for (;;) {
            if (const auto tag = read_tag(reader); !tag) {
                return tag.status();
            } else {
                const auto [field, wire] = *tag;
                if (wire == WireType::EGROUP) {
                    if (field != start_field_number) {
                        return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field);
                    }
                    return {};
                }
                if (const auto st = skip_field(reader, wire, field); !st) {
                    return st;
                }
            }
        }
    }

    template<class Config, class Reader>
    Status skip_group(typename Config::Context &ctx, Reader &reader, const u32 start_field_number) noexcept {
        if (const auto st = push_recursion<Config>(ctx, reader.position(), start_field_number); !st) {
            return st;
        }
        for (;;) {
            if (const auto tag = read_tag(reader); !tag) {
                pop_recursion<Config>(ctx);
                return tag.status();
            } else {
                const auto [field, wire] = *tag;
                if (wire == WireType::EGROUP) {
                    pop_recursion<Config>(ctx);
                    if (field != start_field_number) {
                        return protocyte::unexpected(ErrorCode::invalid_wire_type, reader.position(), field);
                    }
                    return {};
                }
                if (const auto st = skip_field<Config>(ctx, reader, wire, field); !st) {
                    pop_recursion<Config>(ctx);
                    return st;
                }
            }
        }
    }

    template<class Config, class Reader> Status read_bytes_sized(typename Config::Context &ctx, Reader &reader,
                                                                 const usize size,
                                                                 typename Config::Bytes &out) noexcept {
        if (size > ctx.limits.max_string_bytes) {
            return protocyte::unexpected(ErrorCode::size_limit, reader.position());
        }
        typename Config::Bytes temp {&ctx};
        if (const auto st = temp.resize(size); !st) {
            return st;
        }
        auto buffer = temp.mutable_view();
        for (usize i {}; i < size; ++i) {
            auto byte = reader.read_byte();
            if (!byte) {
                return byte.status();
            }
            buffer.data[i] = *byte;
        }
        out = protocyte::move(temp);
        return {};
    }

    template<class Config, class Reader>
    Status read_bytes(typename Config::Context &ctx, Reader &reader, typename Config::Bytes &out) noexcept {
        return read_length_delimited_size(reader).and_then([&ctx, &reader, &out](const usize size) noexcept -> Status {
            return read_bytes_sized<Config>(ctx, reader, size, out);
        });
    }

    template<class Config, class Reader> Status read_bytes_field(typename Config::Context &ctx, Reader &reader,
                                                                 const WireType wire_type, const u32 field_number,
                                                                 typename Config::Bytes &out) noexcept {
        return expect_wire_type(reader, wire_type, WireType::LEN, field_number)
            .and_then([&ctx, &reader, &out]() noexcept -> Status { return read_bytes<Config>(ctx, reader, out); });
    }

    template<class Config, class Reader> Status read_string_sized(typename Config::Context &ctx, Reader &reader,
                                                                  const usize size,
                                                                  typename Config::String &out) noexcept {
        if (size > ctx.limits.max_string_bytes) {
            return protocyte::unexpected(ErrorCode::size_limit, reader.position());
        }
        typename Config::Bytes buffer {&ctx};
        if (const auto st = buffer.resize(size); !st) {
            return st;
        }
        auto bytes = buffer.mutable_view();
        for (usize i {}; i < size; ++i) {
            auto byte = reader.read_byte();
            if (!byte) {
                return byte.status();
            }
            bytes.data[i] = *byte;
        }
        typename Config::String temp {&ctx};
        if (const auto st = temp.assign_owned(protocyte::move(buffer)); !st) {
            return st;
        }
        out = protocyte::move(temp);
        return {};
    }

    template<class Config, class Reader>
    Status read_string(typename Config::Context &ctx, Reader &reader, typename Config::String &out) noexcept {
        return read_length_delimited_size(reader).and_then([&ctx, &reader, &out](const usize size) noexcept -> Status {
            return read_string_sized<Config>(ctx, reader, size, out);
        });
    }

    template<class Config, class Reader> Status read_string_field(typename Config::Context &ctx, Reader &reader,
                                                                  const WireType wire_type, const u32 field_number,
                                                                  typename Config::String &out) noexcept {
        return expect_wire_type(reader, wire_type, WireType::LEN, field_number)
            .and_then([&ctx, &reader, &out]() noexcept -> Status { return read_string<Config>(ctx, reader, out); });
    }

    template<class Writer> Status write_bytes(Writer &writer, const ByteView view) noexcept {
        return write_varint(writer, static_cast<u64>(view.size)).and_then([&writer, view]() noexcept -> Status {
            return writer.write(view.data, view.size);
        });
    }

    template<class Writer>
    Status write_bytes_field(Writer &writer, const u32 field_number, const ByteView view) noexcept {
        return write_tag(writer, field_number, WireType::LEN).and_then([&writer, view]() noexcept -> Status {
            return write_bytes(writer, view);
        });
    }

    template<class Writer>
    Status write_string_field(Writer &writer, const u32 field_number, const ByteView view) noexcept {
        return write_bytes_field(writer, field_number, view);
    }

    inline Status add_size(usize *total, const usize value) noexcept { return checked_add(*total, value, total); }

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
    inline void *hosted_allocate(void *, const usize size, const usize alignment) noexcept {
        return ::operator new(size, static_cast<::std::align_val_t>(alignment), ::std::nothrow);
    }
    inline void hosted_deallocate(void *, void *ptr, const usize, const usize alignment) noexcept {
        ::operator delete(ptr, static_cast<::std::align_val_t>(alignment));
    }
    inline Allocator hosted_allocator() noexcept {
        return {.state = nullptr, .allocate = hosted_allocate, .deallocate = hosted_deallocate};
    }
#endif

} // namespace protocyte

#endif // PROTOCYTE_RUNTIME_RUNTIME_HPP
