from __future__ import annotations


def runtime_files(prefix: str = "protocyte/runtime") -> dict[str, str]:
    normalized = prefix.strip("/") or "protocyte/runtime"
    return {
        f"{normalized}/runtime.hpp": RUNTIME_HPP,
        f"{normalized}/runtime.cpp": RUNTIME_CPP,
    }


RUNTIME_HPP = r"""#ifndef PROTOCYTE_RUNTIME_RUNTIME_HPP
#define PROTOCYTE_RUNTIME_RUNTIME_HPP

#include <stddef.h>
#include <stdint.h>
#include <new>

namespace protocyte {

template <class T>
struct RemoveReference {
  using Type = T;
};

template <class T>
struct RemoveReference<T&> {
  using Type = T;
};

template <class T>
struct RemoveReference<T&&> {
  using Type = T;
};

template <class T>
constexpr typename RemoveReference<T>::Type&& move(T&& value) noexcept {
  return static_cast<typename RemoveReference<T>::Type&&>(value);
}

template <class T>
constexpr T&& forward(typename RemoveReference<T>::Type& value) noexcept {
  return static_cast<T&&>(value);
}

template <class T>
constexpr T&& forward(typename RemoveReference<T>::Type&& value) noexcept {
  return static_cast<T&&>(value);
}

enum class ErrorCode : uint32_t {
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

struct Error {
  ErrorCode code;
  size_t offset;
  uint32_t field_number;
};

class Status {
 public:
  constexpr Status() noexcept : error_{ErrorCode::ok, 0u, 0u} {}
  constexpr explicit Status(Error error) noexcept : error_(error) {}

  static constexpr Status ok() noexcept { return Status(); }
  static constexpr Status error(ErrorCode code, size_t offset = 0u, uint32_t field_number = 0u) noexcept {
    return Status(Error{code, offset, field_number});
  }

  constexpr bool is_ok() const noexcept { return error_.code == ErrorCode::ok; }
  constexpr explicit operator bool() const noexcept { return is_ok(); }
  constexpr Error error() const noexcept { return error_; }

 private:
  Error error_;
};

template <class T>
class Ref {
 public:
  constexpr explicit Ref(T& value) noexcept : ptr_(&value) {}
  constexpr T& get() const noexcept { return *ptr_; }
  constexpr operator T&() const noexcept { return *ptr_; }
  constexpr T* operator->() const noexcept { return ptr_; }

 private:
  T* ptr_;
};

template <class T>
class Result {
 public:
  static Result ok(T value) noexcept { return Result(protocyte::move(value)); }
  static Result err(Error error) noexcept { return Result(error); }
  static Result err(ErrorCode code, size_t offset = 0u, uint32_t field_number = 0u) noexcept {
    return Result(Error{code, offset, field_number});
  }

  Result(Result&& other) noexcept : ok_(other.ok_) {
    if (ok_) {
      new (&value_) T(protocyte::move(other.value_));
    } else {
      error_ = other.error_;
    }
  }

  Result& operator=(Result&& other) noexcept {
    if (this == &other) {
      return *this;
    }
    this->~Result();
    ok_ = other.ok_;
    if (ok_) {
      new (&value_) T(protocyte::move(other.value_));
    } else {
      error_ = other.error_;
    }
    return *this;
  }

  Result(const Result&) = delete;
  Result& operator=(const Result&) = delete;

  ~Result() noexcept {
    if (ok_) {
      value_.~T();
    }
  }

  constexpr bool is_ok() const noexcept { return ok_; }
  constexpr explicit operator bool() const noexcept { return ok_; }
  T& value() & noexcept { return value_; }
  const T& value() const& noexcept { return value_; }
  T&& take_value() && noexcept { return protocyte::move(value_); }
  Error error() const noexcept { return ok_ ? Error{ErrorCode::ok, 0u, 0u} : error_; }
  Status status() const noexcept { return ok_ ? Status::ok() : Status(error_); }

 private:
  explicit Result(T&& value) noexcept : ok_(true) { new (&value_) T(protocyte::move(value)); }
  explicit Result(Error error) noexcept : ok_(false), error_(error) {}

  bool ok_;
  union {
    T value_;
    Error error_;
  };
};

struct ByteView {
  const uint8_t* data;
  size_t size;
};

struct MutableByteView {
  uint8_t* data;
  size_t size;
};

inline bool bytes_equal(ByteView lhs, ByteView rhs) noexcept {
  if (lhs.size != rhs.size) {
    return false;
  }
  for (size_t i = 0; i < lhs.size; ++i) {
    if (lhs.data[i] != rhs.data[i]) {
      return false;
    }
  }
  return true;
}

inline uint64_t fnv1a(ByteView view) noexcept {
  uint64_t hash = 1469598103934665603ull;
  for (size_t i = 0; i < view.size; ++i) {
    hash ^= static_cast<uint64_t>(view.data[i]);
    hash *= 1099511628211ull;
  }
  return hash;
}

inline Status checked_add(size_t lhs, size_t rhs, size_t* out) noexcept {
  const size_t value = lhs + rhs;
  if (value < lhs) {
    return Status::error(ErrorCode::integer_overflow);
  }
  *out = value;
  return Status::ok();
}

inline Status checked_mul(size_t lhs, size_t rhs, size_t* out) noexcept {
  if (lhs != 0u && rhs > static_cast<size_t>(~static_cast<size_t>(0u)) / lhs) {
    return Status::error(ErrorCode::integer_overflow);
  }
  *out = lhs * rhs;
  return Status::ok();
}

struct Limits {
  size_t max_recursion_depth = 64u;
  size_t max_message_bytes = static_cast<size_t>(~static_cast<size_t>(0u));
  size_t max_string_bytes = static_cast<size_t>(~static_cast<size_t>(0u));
  size_t max_repeated_count = static_cast<size_t>(~static_cast<size_t>(0u));
  size_t max_map_entries = static_cast<size_t>(~static_cast<size_t>(0u));
};

struct Allocator {
  void* state = nullptr;
  void* (*allocate)(void* state, size_t size, size_t alignment) = nullptr;
  void (*deallocate)(void* state, void* ptr, size_t size, size_t alignment) = nullptr;
};

template <class T>
class Optional;

template <class T, class Config>
class Vector;

template <class Config>
class Bytes;

template <class Config>
class String;

template <class T, class Config>
class Box;

template <class K, class V, class Config>
class HashMap;

struct DefaultConfig {
  struct Context {
    Allocator allocator;
    Limits limits;
  };

  template <class T>
  using Vector = protocyte::Vector<T, DefaultConfig>;
  template <class K, class V>
  using Map = protocyte::HashMap<K, V, DefaultConfig>;
  template <class T>
  using Box = protocyte::Box<T, DefaultConfig>;
  template <class T>
  using Optional = protocyte::Optional<T>;
  using Bytes = protocyte::Bytes<DefaultConfig>;
  using String = protocyte::String<DefaultConfig>;

  static void* allocate(Context& ctx, size_t size, size_t alignment) noexcept {
    if (size == 0u) {
      return nullptr;
    }
    if (ctx.allocator.allocate == nullptr) {
      return nullptr;
    }
    return ctx.allocator.allocate(ctx.allocator.state, size, alignment);
  }

  static void deallocate(Context& ctx, void* ptr, size_t size, size_t alignment) noexcept {
    if (ptr != nullptr && ctx.allocator.deallocate != nullptr) {
      ctx.allocator.deallocate(ctx.allocator.state, ptr, size, alignment);
    }
  }

  template <class T>
  static uint64_t hash(const T& value) noexcept {
    return fnv1a(ByteView{reinterpret_cast<const uint8_t*>(&value), sizeof(T)});
  }

  template <class T>
  static bool equal(const T& lhs, const T& rhs) noexcept {
    return lhs == rhs;
  }

  static uint64_t hash(const Bytes& value) noexcept;
  static uint64_t hash(const String& value) noexcept;
  static bool equal(const Bytes& lhs, const Bytes& rhs) noexcept;
  static bool equal(const String& lhs, const String& rhs) noexcept;
};

template <class T>
class Optional {
 public:
  Optional() noexcept : has_(false) {}
  Optional(Optional&& other) noexcept : has_(false) {
    if (other.has_) {
      new (ptr()) T(protocyte::move(*other.ptr()));
      has_ = true;
      other.reset();
    }
  }
  Optional& operator=(Optional&& other) noexcept {
    if (this == &other) {
      return *this;
    }
    reset();
    if (other.has_) {
      new (ptr()) T(protocyte::move(*other.ptr()));
      has_ = true;
      other.reset();
    }
    return *this;
  }
  Optional(const Optional&) = delete;
  Optional& operator=(const Optional&) = delete;
  ~Optional() noexcept { reset(); }

  template <class... Args>
  Status emplace(Args&&... args) noexcept {
    reset();
    new (ptr()) T(protocyte::forward<Args>(args)...);
    has_ = true;
    return Status::ok();
  }

  void reset() noexcept {
    if (has_) {
      ptr()->~T();
      has_ = false;
    }
  }

  bool has_value() const noexcept { return has_; }
  T& value() noexcept { return *ptr(); }
  const T& value() const noexcept { return *ptr(); }

 private:
  T* ptr() noexcept { return reinterpret_cast<T*>(&storage_[0]); }
  const T* ptr() const noexcept { return reinterpret_cast<const T*>(&storage_[0]); }

  bool has_;
  alignas(T) unsigned char storage_[sizeof(T)];
};

template <class T, class Config>
class Vector {
 public:
  using Context = typename Config::Context;

  explicit Vector(Context* ctx = nullptr) noexcept : ctx_(ctx), data_(nullptr), size_(0u), capacity_(0u) {}
  Vector(Vector&& other) noexcept
      : ctx_(other.ctx_), data_(other.data_), size_(other.size_), capacity_(other.capacity_) {
    other.data_ = nullptr;
    other.size_ = 0u;
    other.capacity_ = 0u;
  }
  Vector& operator=(Vector&& other) noexcept {
    if (this == &other) {
      return *this;
    }
    destroy();
    ctx_ = other.ctx_;
    data_ = other.data_;
    size_ = other.size_;
    capacity_ = other.capacity_;
    other.data_ = nullptr;
    other.size_ = 0u;
    other.capacity_ = 0u;
    return *this;
  }
  Vector(const Vector&) = delete;
  Vector& operator=(const Vector&) = delete;
  ~Vector() noexcept { destroy(); }

  void bind(Context* ctx) noexcept { ctx_ = ctx; }
  size_t size() const noexcept { return size_; }
  size_t capacity() const noexcept { return capacity_; }
  bool empty() const noexcept { return size_ == 0u; }
  T* data() noexcept { return data_; }
  const T* data() const noexcept { return data_; }
  T& operator[](size_t index) noexcept { return data_[index]; }
  const T& operator[](size_t index) const noexcept { return data_[index]; }

  void clear() noexcept {
    for (size_t i = 0; i < size_; ++i) {
      data_[i].~T();
    }
    size_ = 0u;
  }

  Status reserve(size_t requested) noexcept {
    if (requested <= capacity_) {
      return Status::ok();
    }
    if (ctx_ == nullptr) {
      return Status::error(ErrorCode::invalid_argument);
    }
    size_t bytes = 0u;
    Status st = checked_mul(requested, sizeof(T), &bytes);
    if (!st) {
      return st;
    }
    void* raw = Config::allocate(*ctx_, bytes, alignof(T));
    if (raw == nullptr) {
      return Status::error(ErrorCode::no_memory);
    }
    T* next = static_cast<T*>(raw);
    for (size_t i = 0; i < size_; ++i) {
      new (&next[i]) T(protocyte::move(data_[i]));
      data_[i].~T();
    }
    if (data_ != nullptr) {
      Config::deallocate(*ctx_, data_, capacity_ * sizeof(T), alignof(T));
    }
    data_ = next;
    capacity_ = requested;
    return Status::ok();
  }

  template <class... Args>
  Result<Ref<T>> emplace_back(Args&&... args) noexcept {
    if (size_ == capacity_) {
      const size_t next_capacity = capacity_ == 0u ? 4u : capacity_ * 2u;
      Status st = reserve(next_capacity);
      if (!st) {
        return Result<Ref<T>>::err(st.error());
      }
    }
    new (&data_[size_]) T(protocyte::forward<Args>(args)...);
    Ref<T> ref(data_[size_]);
    ++size_;
    return Result<Ref<T>>::ok(ref);
  }

  Status push_back(const T& value) noexcept {
    auto result = emplace_back(value);
    return result.status();
  }

  Status push_back(T&& value) noexcept {
    auto result = emplace_back(protocyte::move(value));
    return result.status();
  }

  Status resize_default(size_t count) noexcept {
    if (count < size_) {
      while (size_ > count) {
        --size_;
        data_[size_].~T();
      }
      return Status::ok();
    }
    Status st = reserve(count);
    if (!st) {
      return st;
    }
    while (size_ < count) {
      new (&data_[size_]) T();
      ++size_;
    }
    return Status::ok();
  }

 private:
  void destroy() noexcept {
    clear();
    if (data_ != nullptr && ctx_ != nullptr) {
      Config::deallocate(*ctx_, data_, capacity_ * sizeof(T), alignof(T));
    }
    data_ = nullptr;
    capacity_ = 0u;
  }

  Context* ctx_;
  T* data_;
  size_t size_;
  size_t capacity_;
};

template <class Config>
class Bytes {
 public:
  using Context = typename Config::Context;

  explicit Bytes(Context* ctx = nullptr) noexcept : ctx_(ctx), bytes_(ctx) {}
  Bytes(Bytes&& other) noexcept : ctx_(other.ctx_), bytes_(protocyte::move(other.bytes_)) {}
  Bytes& operator=(Bytes&& other) noexcept {
    ctx_ = other.ctx_;
    bytes_ = protocyte::move(other.bytes_);
    return *this;
  }
  Bytes(const Bytes&) = delete;
  Bytes& operator=(const Bytes&) = delete;

  ByteView view() const noexcept { return ByteView{bytes_.data(), bytes_.size()}; }
  const uint8_t* data() const noexcept { return bytes_.data(); }
  size_t size() const noexcept { return bytes_.size(); }
  bool empty() const noexcept { return bytes_.empty(); }
  void clear() noexcept { bytes_.clear(); }
  void bind(Context* ctx) noexcept {
    ctx_ = ctx;
    bytes_.bind(ctx);
  }

  Status assign(ByteView view) noexcept {
    Bytes temp(ctx_);
    Status st = temp.bytes_.reserve(view.size);
    if (!st) {
      return st;
    }
    for (size_t i = 0; i < view.size; ++i) {
      st = temp.bytes_.push_back(view.data[i]);
      if (!st) {
        return st;
      }
    }
    *this = protocyte::move(temp);
    return Status::ok();
  }

 private:
  Context* ctx_;
  typename Config::template Vector<uint8_t> bytes_;
};

template <class Config>
class String {
 public:
  using Context = typename Config::Context;

  explicit String(Context* ctx = nullptr) noexcept : bytes_(ctx) {}
  String(String&& other) noexcept : bytes_(protocyte::move(other.bytes_)) {}
  String& operator=(String&& other) noexcept {
    bytes_ = protocyte::move(other.bytes_);
    return *this;
  }
  String(const String&) = delete;
  String& operator=(const String&) = delete;

  ByteView view() const noexcept { return bytes_.view(); }
  const uint8_t* data() const noexcept { return bytes_.data(); }
  size_t size() const noexcept { return bytes_.size(); }
  bool empty() const noexcept { return bytes_.empty(); }
  void clear() noexcept { bytes_.clear(); }

  Status assign(ByteView view) noexcept {
    if (!validate_utf8(view)) {
      return Status::error(ErrorCode::invalid_utf8);
    }
    return bytes_.assign(view);
  }

 private:
  static bool validate_utf8(ByteView view) noexcept {
    size_t i = 0u;
    while (i < view.size) {
      const uint8_t byte = view.data[i];
      if (byte < 0x80u) {
        ++i;
        continue;
      }
      size_t need = 0u;
      uint32_t code = 0u;
      if ((byte & 0xE0u) == 0xC0u) {
        need = 1u;
        code = byte & 0x1Fu;
        if (code == 0u) {
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
      for (size_t j = 0u; j < need; ++j) {
        const uint8_t next = view.data[i + 1u + j];
        if ((next & 0xC0u) != 0x80u) {
          return false;
        }
        code = (code << 6u) | static_cast<uint32_t>(next & 0x3Fu);
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

template <class T, class Config>
class Box {
 public:
  using Context = typename Config::Context;

  explicit Box(Context* ctx = nullptr) noexcept : ctx_(ctx), ptr_(nullptr) {}
  Box(Box&& other) noexcept : ctx_(other.ctx_), ptr_(other.ptr_) {
    other.ptr_ = nullptr;
  }
  Box& operator=(Box&& other) noexcept {
    if (this == &other) {
      return *this;
    }
    reset();
    ctx_ = other.ctx_;
    ptr_ = other.ptr_;
    other.ptr_ = nullptr;
    return *this;
  }
  Box(const Box&) = delete;
  Box& operator=(const Box&) = delete;
  ~Box() noexcept { reset(); }

  bool has_value() const noexcept { return ptr_ != nullptr; }
  T& value() noexcept { return *ptr_; }
  const T& value() const noexcept { return *ptr_; }

  Result<Ref<T>> ensure() noexcept {
    if (ptr_ != nullptr) {
      return Result<Ref<T>>::ok(Ref<T>(*ptr_));
    }
    if (ctx_ == nullptr) {
      return Result<Ref<T>>::err(ErrorCode::invalid_argument);
    }
    void* raw = Config::allocate(*ctx_, sizeof(T), alignof(T));
    if (raw == nullptr) {
      return Result<Ref<T>>::err(ErrorCode::no_memory);
    }
    ptr_ = new (raw) T(*ctx_);
    return Result<Ref<T>>::ok(Ref<T>(*ptr_));
  }

  void reset() noexcept {
    if (ptr_ != nullptr && ctx_ != nullptr) {
      ptr_->~T();
      Config::deallocate(*ctx_, ptr_, sizeof(T), alignof(T));
      ptr_ = nullptr;
    }
  }

 private:
  Context* ctx_;
  T* ptr_;
};

template <class K, class V, class Config>
class HashMap {
  struct Bucket {
    bool occupied = false;
    Optional<K> key;
    Optional<V> value;
  };

 public:
  using Context = typename Config::Context;

  explicit HashMap(Context* ctx = nullptr) noexcept : ctx_(ctx), buckets_(ctx), size_(0u) {}
  HashMap(HashMap&& other) noexcept
      : ctx_(other.ctx_), buckets_(protocyte::move(other.buckets_)), size_(other.size_) {
    other.size_ = 0u;
  }
  HashMap& operator=(HashMap&& other) noexcept {
    if (this == &other) {
      return *this;
    }
    ctx_ = other.ctx_;
    buckets_ = protocyte::move(other.buckets_);
    size_ = other.size_;
    other.size_ = 0u;
    return *this;
  }
  HashMap(const HashMap&) = delete;
  HashMap& operator=(const HashMap&) = delete;

  size_t size() const noexcept { return size_; }
  bool empty() const noexcept { return size_ == 0u; }
  void clear() noexcept {
    for (size_t i = 0; i < buckets_.size(); ++i) {
      buckets_[i].occupied = false;
      buckets_[i].key.reset();
      buckets_[i].value.reset();
    }
    size_ = 0u;
  }

  Status reserve(size_t count) noexcept {
    size_t desired = 8u;
    while (desired < count * 2u) {
      desired *= 2u;
    }
    if (desired <= buckets_.size()) {
      return Status::ok();
    }
    HashMap next(ctx_);
    Status st = next.buckets_.resize_default(desired);
    if (!st) {
      return st;
    }
    for (size_t i = 0; i < buckets_.size(); ++i) {
      if (buckets_[i].occupied) {
        st = next.insert_or_assign(protocyte::move(buckets_[i].key.value()), protocyte::move(buckets_[i].value.value()));
        if (!st) {
          return st;
        }
      }
    }
    *this = protocyte::move(next);
    return Status::ok();
  }

  Status insert_or_assign(K&& key, V&& value) noexcept {
    Status st = ensure_capacity_for_one_more();
    if (!st) {
      return st;
    }
    size_t index = Config::hash(key) & (buckets_.size() - 1u);
    for (;;) {
      Bucket& bucket = buckets_[index];
      if (!bucket.occupied) {
        bucket.occupied = true;
        bucket.key.emplace(protocyte::move(key));
        bucket.value.emplace(protocyte::move(value));
        ++size_;
        return Status::ok();
      }
      if (Config::equal(bucket.key.value(), key)) {
        bucket.value.reset();
        bucket.value.emplace(protocyte::move(value));
        return Status::ok();
      }
      index = (index + 1u) & (buckets_.size() - 1u);
    }
  }

  template <class Fn>
  Status for_each(Fn&& fn) const noexcept {
    for (size_t i = 0; i < buckets_.size(); ++i) {
      const Bucket& bucket = buckets_[i];
      if (bucket.occupied) {
        Status st = fn(bucket.key.value(), bucket.value.value());
        if (!st) {
          return st;
        }
      }
    }
    return Status::ok();
  }

 private:
  Status ensure_capacity_for_one_more() noexcept {
    if (buckets_.size() == 0u || ((size_ + 1u) * 10u) >= buckets_.size() * 7u) {
      return reserve(size_ + 1u);
    }
    return Status::ok();
  }

  Context* ctx_;
  typename Config::template Vector<Bucket> buckets_;
  size_t size_;
};

inline uint64_t DefaultConfig::hash(const Bytes& value) noexcept {
  return fnv1a(value.view());
}

inline uint64_t DefaultConfig::hash(const String& value) noexcept {
  return fnv1a(value.view());
}

inline bool DefaultConfig::equal(const Bytes& lhs, const Bytes& rhs) noexcept {
  return bytes_equal(lhs.view(), rhs.view());
}

inline bool DefaultConfig::equal(const String& lhs, const String& rhs) noexcept {
  return bytes_equal(lhs.view(), rhs.view());
}

class SliceReader {
 public:
  SliceReader(const uint8_t* data, size_t size) noexcept : data_(data), size_(size), pos_(0u) {}
  bool eof() const noexcept { return pos_ >= size_; }
  size_t position() const noexcept { return pos_; }
  Result<uint8_t> read_byte() noexcept {
    if (pos_ >= size_) {
      return Result<uint8_t>::err(ErrorCode::unexpected_eof, pos_);
    }
    return Result<uint8_t>::ok(data_[pos_++]);
  }
  Status read(uint8_t* out, size_t count) noexcept {
    if (count > size_ - pos_) {
      return Status::error(ErrorCode::unexpected_eof, pos_);
    }
    for (size_t i = 0; i < count; ++i) {
      out[i] = data_[pos_ + i];
    }
    pos_ += count;
    return Status::ok();
  }
  Status skip(size_t count) noexcept {
    if (count > size_ - pos_) {
      return Status::error(ErrorCode::unexpected_eof, pos_);
    }
    pos_ += count;
    return Status::ok();
  }

 private:
  const uint8_t* data_;
  size_t size_;
  size_t pos_;
};

template <class Reader>
class LimitedReader {
 public:
  LimitedReader(Reader& inner, size_t remaining) noexcept : inner_(&inner), remaining_(remaining), pos_(0u) {}
  bool eof() const noexcept { return remaining_ == 0u; }
  size_t position() const noexcept { return pos_; }
  Result<uint8_t> read_byte() noexcept {
    if (remaining_ == 0u) {
      return Result<uint8_t>::err(ErrorCode::unexpected_eof, pos_);
    }
    auto byte = inner_->read_byte();
    if (!byte) {
      return Result<uint8_t>::err(byte.error());
    }
    --remaining_;
    ++pos_;
    return byte;
  }
  Status read(uint8_t* out, size_t count) noexcept {
    if (count > remaining_) {
      return Status::error(ErrorCode::unexpected_eof, pos_);
    }
    Status st = inner_->read(out, count);
    if (!st) {
      return st;
    }
    remaining_ -= count;
    pos_ += count;
    return Status::ok();
  }
  Status skip(size_t count) noexcept {
    if (count > remaining_) {
      return Status::error(ErrorCode::unexpected_eof, pos_);
    }
    Status st = inner_->skip(count);
    if (!st) {
      return st;
    }
    remaining_ -= count;
    pos_ += count;
    return Status::ok();
  }
  Status finish() noexcept { return skip(remaining_); }

 private:
  Reader* inner_;
  size_t remaining_;
  size_t pos_;
};

class SliceWriter {
 public:
  SliceWriter(uint8_t* data, size_t capacity) noexcept : data_(data), capacity_(capacity), pos_(0u) {}
  size_t position() const noexcept { return pos_; }
  Status write_byte(uint8_t value) noexcept {
    if (pos_ >= capacity_) {
      return Status::error(ErrorCode::size_limit, pos_);
    }
    data_[pos_++] = value;
    return Status::ok();
  }
  Status write(const uint8_t* data, size_t count) noexcept {
    if (count > capacity_ - pos_) {
      return Status::error(ErrorCode::size_limit, pos_);
    }
    for (size_t i = 0; i < count; ++i) {
      data_[pos_ + i] = data[i];
    }
    pos_ += count;
    return Status::ok();
  }

 private:
  uint8_t* data_;
  size_t capacity_;
  size_t pos_;
};

template <class Reader>
Result<uint64_t> read_varint(Reader& reader) noexcept {
  uint64_t value = 0u;
  uint32_t shift = 0u;
  for (uint32_t i = 0u; i < 10u; ++i) {
    auto byte = reader.read_byte();
    if (!byte) {
      return Result<uint64_t>::err(byte.error());
    }
    value |= (static_cast<uint64_t>(byte.value() & 0x7Fu) << shift);
    if ((byte.value() & 0x80u) == 0u) {
      return Result<uint64_t>::ok(value);
    }
    shift += 7u;
  }
  return Result<uint64_t>::err(ErrorCode::malformed_varint, reader.position());
}

template <class Writer>
Status write_varint(Writer& writer, uint64_t value) noexcept {
  while (value >= 0x80u) {
    Status st = writer.write_byte(static_cast<uint8_t>(value | 0x80u));
    if (!st) {
      return st;
    }
    value >>= 7u;
  }
  return writer.write_byte(static_cast<uint8_t>(value));
}

inline size_t varint_size(uint64_t value) noexcept {
  size_t size = 1u;
  while (value >= 0x80u) {
    value >>= 7u;
    ++size;
  }
  return size;
}

inline uint32_t encode_zigzag32(int32_t value) noexcept {
  return static_cast<uint32_t>((value << 1) ^ (value >> 31));
}

inline uint64_t encode_zigzag64(int64_t value) noexcept {
  return static_cast<uint64_t>((value << 1) ^ (value >> 63));
}

inline int32_t decode_zigzag32(uint32_t value) noexcept {
  return static_cast<int32_t>((value >> 1) ^ (~(value & 1u) + 1u));
}

inline int64_t decode_zigzag64(uint64_t value) noexcept {
  return static_cast<int64_t>((value >> 1) ^ (~(value & 1u) + 1u));
}

template <class Reader>
Result<uint32_t> read_fixed32(Reader& reader) noexcept {
  uint8_t bytes[4];
  Status st = reader.read(bytes, 4u);
  if (!st) {
    return Result<uint32_t>::err(st.error());
  }
  uint32_t value = static_cast<uint32_t>(bytes[0]) |
                   (static_cast<uint32_t>(bytes[1]) << 8u) |
                   (static_cast<uint32_t>(bytes[2]) << 16u) |
                   (static_cast<uint32_t>(bytes[3]) << 24u);
  return Result<uint32_t>::ok(value);
}

template <class Reader>
Result<uint64_t> read_fixed64(Reader& reader) noexcept {
  uint8_t bytes[8];
  Status st = reader.read(bytes, 8u);
  if (!st) {
    return Result<uint64_t>::err(st.error());
  }
  uint64_t value = 0u;
  for (uint32_t i = 0u; i < 8u; ++i) {
    value |= static_cast<uint64_t>(bytes[i]) << (i * 8u);
  }
  return Result<uint64_t>::ok(value);
}

template <class Writer>
Status write_fixed32(Writer& writer, uint32_t value) noexcept {
  uint8_t bytes[4] = {
      static_cast<uint8_t>(value),
      static_cast<uint8_t>(value >> 8u),
      static_cast<uint8_t>(value >> 16u),
      static_cast<uint8_t>(value >> 24u),
  };
  return writer.write(bytes, 4u);
}

template <class Writer>
Status write_fixed64(Writer& writer, uint64_t value) noexcept {
  uint8_t bytes[8];
  for (uint32_t i = 0u; i < 8u; ++i) {
    bytes[i] = static_cast<uint8_t>(value >> (i * 8u));
  }
  return writer.write(bytes, 8u);
}

template <class Writer>
Status write_tag(Writer& writer, uint32_t field_number, uint32_t wire_type) noexcept {
  return write_varint(writer, (static_cast<uint64_t>(field_number) << 3u) | wire_type);
}

inline size_t tag_size(uint32_t field_number) noexcept {
  return varint_size(static_cast<uint64_t>(field_number) << 3u);
}

template <class Reader>
Status skip_group(Reader& reader, uint32_t start_field_number) noexcept;

template <class Reader>
Status skip_field(Reader& reader, uint32_t wire_type, uint32_t field_number = 0u) noexcept {
  switch (wire_type) {
    case 0u: {
      auto ignored = read_varint(reader);
      return ignored.status();
    }
    case 1u:
      return reader.skip(8u);
    case 2u: {
      auto len = read_varint(reader);
      if (!len) {
        return len.status();
      }
      return reader.skip(static_cast<size_t>(len.value()));
    }
    case 3u:
      return skip_group(reader, field_number);
    case 4u:
      return Status::ok();
    case 5u:
      return reader.skip(4u);
    default:
      return Status::error(ErrorCode::invalid_wire_type, reader.position(), field_number);
  }
}

template <class Reader>
Status skip_group(Reader& reader, uint32_t start_field_number) noexcept {
  for (;;) {
    auto tag = read_varint(reader);
    if (!tag) {
      return tag.status();
    }
    const uint32_t field = static_cast<uint32_t>(tag.value() >> 3u);
    const uint32_t wire = static_cast<uint32_t>(tag.value() & 0x7u);
    if (wire == 4u) {
      if (field != start_field_number) {
        return Status::error(ErrorCode::invalid_wire_type, reader.position(), field);
      }
      return Status::ok();
    }
    Status st = skip_field(reader, wire, field);
    if (!st) {
      return st;
    }
  }
}

template <class Config, class Reader>
Status read_bytes(typename Config::Context& ctx, Reader& reader, size_t size, typename Config::Bytes& out) noexcept {
  if (size > ctx.limits.max_string_bytes) {
    return Status::error(ErrorCode::size_limit, reader.position());
  }
  typename Config::Bytes temp(&ctx);
  Status st = temp.assign(ByteView{nullptr, 0u});
  if (!st) {
    return st;
  }
  typename Config::template Vector<uint8_t> buffer(&ctx);
  st = buffer.reserve(size);
  if (!st) {
    return st;
  }
  for (size_t i = 0u; i < size; ++i) {
    auto byte = reader.read_byte();
    if (!byte) {
      return byte.status();
    }
    st = buffer.push_back(byte.value());
    if (!st) {
      return st;
    }
  }
  st = temp.assign(ByteView{buffer.data(), buffer.size()});
  if (!st) {
    return st;
  }
  out = protocyte::move(temp);
  return Status::ok();
}

template <class Config, class Reader>
Status read_string(typename Config::Context& ctx, Reader& reader, size_t size, typename Config::String& out) noexcept {
  if (size > ctx.limits.max_string_bytes) {
    return Status::error(ErrorCode::size_limit, reader.position());
  }
  typename Config::template Vector<uint8_t> buffer(&ctx);
  Status st = buffer.reserve(size);
  if (!st) {
    return st;
  }
  for (size_t i = 0u; i < size; ++i) {
    auto byte = reader.read_byte();
    if (!byte) {
      return byte.status();
    }
    st = buffer.push_back(byte.value());
    if (!st) {
      return st;
    }
  }
  typename Config::String temp(&ctx);
  st = temp.assign(ByteView{buffer.data(), buffer.size()});
  if (!st) {
    return st;
  }
  out = protocyte::move(temp);
  return Status::ok();
}

template <class Writer>
Status write_bytes(Writer& writer, ByteView view) noexcept {
  Status st = write_varint(writer, static_cast<uint64_t>(view.size));
  if (!st) {
    return st;
  }
  return writer.write(view.data, view.size);
}

inline Status add_size(size_t* total, size_t value) noexcept {
  return checked_add(*total, value, total);
}

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
void* hosted_allocate(void* state, size_t size, size_t alignment) noexcept;
void hosted_deallocate(void* state, void* ptr, size_t size, size_t alignment) noexcept;
inline Allocator hosted_allocator() noexcept {
  return Allocator{nullptr, hosted_allocate, hosted_deallocate};
}
#endif

}  // namespace protocyte

#endif  // PROTOCYTE_RUNTIME_RUNTIME_HPP
"""


RUNTIME_CPP = r"""#include "runtime.hpp"

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
#include <stdlib.h>

namespace protocyte {

void* hosted_allocate(void*, size_t size, size_t) noexcept {
  return malloc(size);
}

void hosted_deallocate(void*, void* ptr, size_t, size_t) noexcept {
  free(ptr);
}

}  // namespace protocyte
#endif
"""
