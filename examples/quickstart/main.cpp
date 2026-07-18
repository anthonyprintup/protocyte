#include <cstdio>
#include <vector>

#include <protocyte/runtime/runtime.hpp>

#include "quickstart.protocyte.hpp"

namespace {
    int report_error(const char *operation, const protocyte::Error &error, const int exit_code) {
        std::fprintf(stderr, "%s failed: code=%u offset=%llu field=%u\n", operation, static_cast<unsigned>(error.code),
                     static_cast<unsigned long long>(error.offset), static_cast<unsigned>(error.field_number));
        return exit_code;
    }
} // namespace

int main() {
    auto encode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    auto reading = demo::quickstart::Reading<>::create(encode_ctx);
    reading.set_value(42u);

    const auto size = reading.encoded_size();
    if (!size) {
        return report_error("encoded_size", size.error(), 1);
    }

    std::vector<protocyte::u8> encoded(*size);
    const auto written = reading.serialize(encoded);
    if (!written) {
        return report_error("serialize", written.error(), 2);
    }
    if (*written != encoded.size()) {
        std::fputs("serialize returned an unexpected byte count\n", stderr);
        return 2;
    }

    auto decode_ctx = protocyte::DefaultConfig::Context {
        protocyte::hosted_allocator(),
        protocyte::Limits {},
    };
    const auto parsed = demo::quickstart::Reading<>::parse(decode_ctx, encoded);
    if (!parsed) {
        return report_error("parse", parsed.error(), 3);
    }
    if ((*parsed).value() != 42u) {
        std::fputs("parsed value did not match the encoded value\n", stderr);
        return 3;
    }

    return 0;
}
