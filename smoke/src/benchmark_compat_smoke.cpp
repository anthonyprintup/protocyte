#include <string>
#include <vector>

#include <catch2/catch_test_macros.hpp>

#include "protobuf_benchmark_fixture.hpp"
#include "protocyte_benchmark_fixture.hpp"

namespace {

    template<class TStatusLike> void require_success(const TStatusLike &status_like) {
        if (!status_like) {
            const auto error = status_like.error();
            CAPTURE(static_cast<uint32_t>(error.code), error.offset, error.field_number);
        }
        REQUIRE(status_like);
    }

    std::vector<protocyte::u8>
    serialize_protocyte(const protocyte_smoke::benchmark_fixture::ProtocyteMessage &message) {
        const auto size = message.encoded_size();
        require_success(size);
        std::vector<protocyte::u8> encoded(*size);
        protocyte::SliceWriter writer(encoded.data(), encoded.size());
        require_success(message.serialize(writer));
        REQUIRE(writer.position() == encoded.size());
        return encoded;
    }

    template<class T, protocyte::usize Extent>
    bool view_equal(const protocyte::Span<T, Extent> lhs, const std::string &rhs) {
        return lhs.size() == rhs.size() && protocyte::bytes_equal(protocyte::Span<const T> {lhs.data(), lhs.size()},
                                                                  protocyte::Span<const char> {rhs.data(), rhs.size()});
    }

} // namespace

TEST_CASE("benchmark schema round trips between Protocyte and protobuf", "[smoke][benchmark][protobuf]") {
    namespace fixture = protocyte_smoke::benchmark_fixture;

    auto ctx = fixture::make_context();
    fixture::ProtocyteMessage protocyte_message(ctx);
    require_success(fixture::populate_protocyte_message(protocyte_message, ctx));

    const auto protocyte_encoded = serialize_protocyte(protocyte_message);
    fixture::ProtobufMessage protobuf_from_protocyte;
    REQUIRE(
        protobuf_from_protocyte.ParseFromArray(protocyte_encoded.data(), static_cast<int>(protocyte_encoded.size())));
    CHECK(protobuf_from_protocyte.ByteSizeLong() == protocyte_encoded.size());
    CHECK(protobuf_from_protocyte.f_int32() == 42);
    CHECK(protobuf_from_protocyte.oneof_bytes() == fixture::bytes_of(fixture::view_of(fixture::oneof_bytes)));
    CHECK(protobuf_from_protocyte.map_str_int32().at(fixture::bytes_of(fixture::view_of(fixture::map_key))) == 301);

    fixture::ProtobufMessage protobuf_message;
    fixture::populate_protobuf_message(&protobuf_message);
    const auto protobuf_encoded = protobuf_message.SerializeAsString();

    auto parse_ctx = fixture::make_context();
    fixture::ProtocyteMessage protocyte_from_protobuf(parse_ctx);
    protocyte::SliceReader reader(reinterpret_cast<const protocyte::u8 *>(protobuf_encoded.data()),
                                  protobuf_encoded.size());
    require_success(protocyte_from_protobuf.merge_from(reader));
    REQUIRE(reader.eof());

    const auto protocyte_size = protocyte_from_protobuf.encoded_size();
    require_success(protocyte_size);
    CHECK(*protocyte_size == protobuf_message.ByteSizeLong());
    CHECK(protocyte_from_protobuf.f_int32() == 42);
    CHECK(view_equal(protocyte_from_protobuf.oneof_bytes(), protobuf_message.oneof_bytes()));
    CHECK(protocyte_from_protobuf.map_str_int32().size() == 1u);
}
