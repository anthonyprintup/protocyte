#include <array>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

#include "common.protocyte.hpp"
#include "demo.protocyte.hpp"
#include "protocyte/runtime/runtime.hpp"

namespace {

    using Config = ::protocyte::DefaultConfig;
    using Header = ::findpackage::common::Header<>;
    using Envelope = ::findpackage::demo::Envelope<>;

    template<std::size_t N>::protocyte::ByteView view_of(const std::array<unsigned char, N> &bytes) noexcept {
        return ::protocyte::ByteView {bytes.data(), bytes.size()};
    }

    template<class Message> std::string encode_hex(const Message &message) {
        const auto size = message.encoded_size();
        if (!size) {
            throw std::runtime_error("encoded_size failed");
        }

        std::string buffer(*size, '\0');
        ::protocyte::SliceWriter writer(reinterpret_cast<unsigned char *>(buffer.data()), buffer.size());
        if (const auto st = message.serialize(writer); !st) {
            throw std::runtime_error("serialize failed");
        }

        std::ostringstream hex;
        hex << std::hex << std::setfill('0');
        for (const unsigned char byte : buffer) { hex << std::setw(2) << static_cast<unsigned int>(byte); }
        return hex.str();
    }

} // namespace

int main() {
    auto ctx = Config::Context {
        ::protocyte::hosted_allocator(),
        ::protocyte::Limits {},
    };

    auto header = Header::create(ctx);
    if (!header) {
        std::cerr << "failed to create Header\n";
        return EXIT_FAILURE;
    }
    if (const auto st = header->set_version(1u); !st) {
        std::cerr << "failed to set header version\n";
        return EXIT_FAILURE;
    }
    constexpr std::array<unsigned char, 2> kTag {'O', 'K'};
    if (const auto st = header->set_tag(view_of(kTag)); !st) {
        std::cerr << "failed to set header tag\n";
        return EXIT_FAILURE;
    }

    auto envelope = Envelope::create(ctx);
    if (!envelope) {
        std::cerr << "failed to create Envelope\n";
        return EXIT_FAILURE;
    }
    if (auto ensured = envelope->ensure_header(); !ensured) {
        std::cerr << "failed to create envelope header\n";
        return EXIT_FAILURE;
    } else if (const auto st = ensured->get().copy_from(*header); !st) {
        std::cerr << "failed to copy header into envelope\n";
        return EXIT_FAILURE;
    }
    if (const auto st = envelope->set_id(150u); !st) {
        std::cerr << "failed to set envelope id\n";
        return EXIT_FAILURE;
    }
    constexpr std::array<unsigned char, 3> kPayload {'h', 'e', 'y'};
    if (const auto st = envelope->set_payload(view_of(kPayload)); !st) {
        std::cerr << "failed to set envelope payload\n";
        return EXIT_FAILURE;
    }

    const std::string header_hex = encode_hex(*header);
    const std::string envelope_hex = encode_hex(*envelope);

    std::cout << "Header: " << header_hex << '\n';
    std::cout << "Envelope: " << envelope_hex << '\n';

    if (header_hex != "080112024f4b") {
        std::cerr << "unexpected header bytes\n";
        return EXIT_FAILURE;
    }
    if (envelope_hex != "0a06080112024f4b1096011a03686579") {
        std::cerr << "unexpected envelope bytes\n";
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
