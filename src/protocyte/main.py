from __future__ import annotations

import argparse
import os
import sys

from google.protobuf.message import DecodeError
from google.protobuf.compiler import plugin_pb2

from protocyte import __version__
from protocyte.plugin import generate_response


_PROGRAM_NAME = "protoc-gen-protocyte"
_CMAKE_WORKING_DIRECTORY_ENV = "PROTOCYTE_CMAKE_WORKING_DIRECTORY_HEX"
_CMAKE_IMPORT_SCAN_COMMAND = "_cmake-import-scan-v1"


def _enter_cmake_working_directory() -> tuple[str | None, str | None]:
    encoded = os.environ.get(_CMAKE_WORKING_DIRECTORY_ENV)
    if encoded is None:
        return None, None

    try:
        directory = bytes.fromhex(encoded).decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None, f"invalid {_CMAKE_WORKING_DIRECTORY_ENV} payload"
    if not os.path.isabs(directory):
        return None, f"{_CMAKE_WORKING_DIRECTORY_ENV} must decode to an absolute path"

    previous_directory = os.getcwd()
    try:
        os.chdir(directory)
    except OSError as exc:
        return None, f"failed to enter CMake invocation directory {directory!r}: {exc}"
    return previous_directory, None


def _help_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description=(
            "Generate Protocyte C++ code with protoc and inspect protobuf descriptor sets."
        ),
        epilog=(
            "Most users generate code by running protoc, which starts this plugin "
            "automatically:\n"
            "  protoc --proto_path=. --protocyte_out=runtime=emit:. schema.proto\n\n"
            "To inspect a descriptor set:\n"
            "  protoc-gen-protocyte descriptor-set list descriptor_set.pb\n\n"
            "When protoc starts this executable with no arguments, protoc writes a "
            "binary CodeGeneratorRequest to the plugin's standard input."
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
    if args[:1] == [_CMAKE_IMPORT_SCAN_COMMAND]:
        from protocyte.import_scanner import main as import_scanner_main

        return import_scanner_main(args[1:])
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

    if sys.stdin.isatty():
        print(
            f"{_PROGRAM_NAME}: cannot read a binary CodeGeneratorRequest from "
            "interactive standard input.",
            file=sys.stderr,
        )
        print(
            f"This plugin is normally launched by protoc; run "
            f"'{_PROGRAM_NAME} --help' for usage.",
            file=sys.stderr,
        )
        return 2

    previous_directory, working_directory_error = _enter_cmake_working_directory()
    if working_directory_error is not None:
        print(f"protocyte: {working_directory_error}", file=sys.stderr)
        return 1

    try:
        request = plugin_pb2.CodeGeneratorRequest()
        try:
            request.ParseFromString(sys.stdin.buffer.read())
        except DecodeError as exc:
            print(
                f"protocyte: failed to parse CodeGeneratorRequest: {exc}",
                file=sys.stderr,
            )
            return 1

        response = generate_response(request)
        sys.stdout.buffer.write(response.SerializeToString())
        return 0
    finally:
        if previous_directory is not None:
            os.chdir(previous_directory)


if __name__ == "__main__":
    raise SystemExit(main())
