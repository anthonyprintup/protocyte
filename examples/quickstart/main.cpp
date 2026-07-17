#include <vector>

#include <protocyte/runtime/runtime.hpp>

#include "quickstart.protocyte.hpp"

int main() {
    auto encode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    auto reading = demo::quickstart::Reading<>::create(encode_ctx);
    reading.set_value(42u);

    const auto size = reading.encoded_size();
    if (!size) {
        return 1;
    }

    std::vector<protocyte::u8> encoded(*size);
    const auto written = reading.serialize(encoded);
    if (!written || *written != encoded.size()) {
        return 2;
    }

    auto decode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    const auto parsed = demo::quickstart::Reading<>::parse(decode_ctx, encoded);
    if (!parsed || (*parsed).value() != 42u) {
        return 3;
    }

    return 0;
}
