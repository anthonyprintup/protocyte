from __future__ import annotations

import sys

from google.protobuf.message import DecodeError
from google.protobuf.compiler import plugin_pb2

from protocyte import __version__
from protocyte.plugin import generate_response


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--version"]:
        print(__version__)
        return 0
    if args[:1] == ["descriptor-set"]:
        from protocyte.descriptor_set import main as descriptor_set_main

        return descriptor_set_main(args[1:])
    if args:
        print(
            "protocyte: unsupported arguments; expected --version or descriptor-set <command>",
            file=sys.stderr,
        )
        return 2

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
