from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest
from google.protobuf.compiler import plugin_pb2

from protocyte import __version__
import protocyte.main as protocyte_main_module
from protocyte.main import main as plugin_main
from protocyte.plugin import generate_response


class _BinaryInput:
    def __init__(self, payload: bytes, *, interactive: bool) -> None:
        self.buffer = io.BytesIO(payload)
        self._interactive = interactive

    def isatty(self) -> bool:
        return self._interactive


class _UnreadableInteractiveInput:
    def isatty(self) -> bool:
        return True

    @property
    def buffer(self) -> io.BytesIO:
        raise AssertionError("interactive input must not be read")


class _BinaryOutput:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()


def _request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("example.proto")
    file = request.proto_file.add()
    file.name = "example.proto"
    file.syntax = "proto3"
    file.message_type.add().name = "Example"
    return request


def _wire_length_delimited(field_number: int, payload: bytes) -> bytes:
    assert field_number < 16
    assert len(payload) < 128
    return bytes([(field_number << 3) | 2, len(payload)]) + payload


def test_no_argument_interactive_invocation_exits_with_help_hint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "stdin", _UnreadableInteractiveInput())

    assert plugin_main([]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cannot read a binary CodeGeneratorRequest" in captured.err
    assert "interactive standard input" in captured.err
    assert "protoc-gen-protocyte --help" in captured.err


def test_no_argument_non_interactive_invocation_preserves_plugin_protocol(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request = _request()
    standard_input = _BinaryInput(request.SerializeToString(), interactive=False)
    standard_output = _BinaryOutput()

    with monkeypatch.context() as context:
        context.setattr(sys, "stdin", standard_input)
        context.setattr(sys, "stdout", standard_output)
        result = plugin_main([])

    assert result == 0
    assert (
        standard_output.buffer.getvalue()
        == generate_response(request).SerializeToString()
    )
    assert capsys.readouterr().err == ""


def test_plugin_protocol_enables_normal_formatter_timeout_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    standard_input = _BinaryInput(request.SerializeToString(), interactive=False)
    standard_output = _BinaryOutput()
    observed: dict[str, object] = {}

    def fake_generate_response(
        received_request: plugin_pb2.CodeGeneratorRequest, **kwargs: object
    ) -> plugin_pb2.CodeGeneratorResponse:
        observed["request"] = received_request
        observed.update(kwargs)
        return plugin_pb2.CodeGeneratorResponse()

    with monkeypatch.context() as context:
        context.setattr(sys, "stdin", standard_input)
        context.setattr(sys, "stdout", standard_output)
        context.setattr(
            protocyte_main_module, "generate_response", fake_generate_response
        )
        assert plugin_main([]) == 0

    assert observed["request"] == request
    assert observed["use_plugin_defaults"] is True


def test_plugin_protocol_rejects_formatter_timeout_positive_underflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()
    request.parameter = "formatter_timeout_seconds=1e-9999"
    standard_input = _BinaryInput(request.SerializeToString(), interactive=False)
    standard_output = _BinaryOutput()

    with monkeypatch.context() as context:
        context.setattr(sys, "stdin", standard_input)
        context.setattr(sys, "stdout", standard_output)
        assert plugin_main([]) == 0

    response = plugin_pb2.CodeGeneratorResponse.FromString(
        standard_output.buffer.getvalue()
    )
    assert (
        "formatter_timeout_seconds must be a finite non-negative number"
        in response.error
    )
    assert not response.file


def test_plugin_protocol_rejects_malformed_descriptor_utf8(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    malformed_file = _wire_length_delimited(1, b"api/invalid-\xff.proto")
    payload = _wire_length_delimited(1, b"api/input.proto") + _wire_length_delimited(
        15, malformed_file
    )
    standard_input = _BinaryInput(payload, interactive=False)
    standard_output = _BinaryOutput()

    with monkeypatch.context() as context:
        context.setattr(sys, "stdin", standard_input)
        context.setattr(sys, "stdout", standard_output)
        result = plugin_main([])

    response = plugin_pb2.CodeGeneratorResponse.FromString(
        standard_output.buffer.getvalue()
    )
    assert result == 0
    assert response.error == (
        "invalid UTF-8 in descriptor string field "
        "CodeGeneratorRequest.proto_file[0].name: b'api/invalid-\\xff.proto'"
    )
    assert not response.file
    assert capsys.readouterr().err == ""


def test_help_generation_example_uses_an_existing_output_and_explains_protocol(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert plugin_main(["--help"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "--protocyte_out=runtime=emit:." in captured.out
    assert "--protocyte_out=generated" not in captured.out
    assert (
        "protoc writes a binary CodeGeneratorRequest to the plugin's standard input"
        in captured.out
    )
    assert "it writes a binary CodeGeneratorRequest" not in captured.out
    assert "_cmake-import-scan-v1" not in captured.out


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["--help"], "usage: protoc-gen-protocyte"),
        (["--version"], __version__),
    ],
)
def test_package_module_delegates_to_cli(
    tmp_path: Path,
    arguments: list[str],
    expected: str,
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "protocyte", *arguments],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert expected in result.stdout
    assert result.stderr == ""
