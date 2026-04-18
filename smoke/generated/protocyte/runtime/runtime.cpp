#include "runtime.hpp"

#ifdef PROTOCYTE_ENABLE_HOSTED_ALLOCATOR
#include <cstdlib>

namespace protocyte {

    void *hosted_allocate(void *, const usize size, usize) noexcept { return std::malloc(size); }

    void hosted_deallocate(void *, void *ptr, const usize, const usize) noexcept { std::free(ptr); }

} // namespace protocyte
#endif
