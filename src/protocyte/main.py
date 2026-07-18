from __future__ import annotations

import argparse
import sys

from google.protobuf.message import DecodeError
from google.protobuf.compiler import plugin_pb2

from protocyte import __version__
from protocyte.plugin import generate_response


_PROGRAM_NAME = "protoc-gen-protocyte"


def _help_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description=(
            "Generate Protocyte C++ code with protoc and inspect protobuf descriptor sets."
        ),
        epilog=(
            "Most users generate code by running protoc, which starts this plugin "
            "automatically:\n"
            "  protoc --proto_path=. --protocyte_out=generated schema.proto\n\n"
            "To inspect a descriptor set:\n"
            "  protoc-gen-protocyte descriptor-set list descriptor_set.pb\n\n"
            "Running this executable with no arguments is reserved for protoc's "
            "plugin protocol."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show the installed Protocyte version and exit",
    )
    commands = parser.add_subparsers(dest="command", title="commands")
    commands.add_parser(
        "descriptor-set",
        add_help=False,
        help="inspect a serialized protobuf descriptor set",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["-h"], ["--help"]):
        _help_parser().print_help()
        return 0
    if args == ["--version"]:
        print(__version__)
        return 0
    if args[:1] == ["descriptor-set"]:
        from protocyte.descriptor_set import main as descriptor_set_main

        return descriptor_set_main(
            args[1:],
            prog=f"{_PROGRAM_NAME} descriptor-set",
        )
    if args:
        parser = _help_parser()
        parser.print_usage(file=sys.stderr)
        print(
            f"{_PROGRAM_NAME}: error: unsupported arguments: {' '.join(args)}",
            file=sys.stderr,
        )
        print(
            f"Run '{_PROGRAM_NAME} --help' to see the available commands.",
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
