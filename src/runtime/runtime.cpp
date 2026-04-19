#include <protocyte/runtime/runtime.hpp>

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
#include <new>

namespace protocyte {

    void *hosted_allocate(void *, const usize size, const usize alignment) noexcept {
        return ::operator new(size, static_cast<::std::align_val_t>(alignment), ::std::nothrow);
    }

    void hosted_deallocate(void *, void *ptr, const usize, const usize alignment) noexcept {
        ::operator delete(ptr, static_cast<::std::align_val_t>(alignment));
    }

} // namespace protocyte
#endif
