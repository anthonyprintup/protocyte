from __future__ import annotations

import sys

from google.protobuf.message import DecodeError
from google.protobuf.compiler import plugin_pb2

from protocyte.plugin import generate_response


def main() -> int:
    request = plugin_pb2.CodeGeneratorRequest()
    try:
        request.ParseFromString(sys.stdin.buffer.read())
    except DecodeError as exc:
        print(f"protocyte: failed to parse CodeGeneratorRequest: {exc}", file=sys.stderr)
        return 1

    response = generate_response(request)
    sys.stdout.buffer.write(response.SerializeToString())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

