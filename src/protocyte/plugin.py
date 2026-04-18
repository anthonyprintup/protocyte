from __future__ import annotations

from google.protobuf.compiler import plugin_pb2

from protocyte.cpp import generate_outputs
from protocyte.errors import ProtocyteError
from protocyte.model import build_model
from protocyte.parameters import parse_parameter


def generate_response(request: plugin_pb2.CodeGeneratorRequest) -> plugin_pb2.CodeGeneratorResponse:
    response = plugin_pb2.CodeGeneratorResponse()
    response.supported_features = plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL

    try:
        options = parse_parameter(request.parameter)
        model = build_model(request)
        outputs = generate_outputs(model, options)
    except ProtocyteError as exc:
        response.error = str(exc)
        return response

    for name, content in sorted(outputs.items()):
        file = response.file.add()
        file.name = name.replace("\\", "/")
        file.content = content

    return response

