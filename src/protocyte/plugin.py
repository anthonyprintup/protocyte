from __future__ import annotations

from dataclasses import dataclass, fields

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte.cpp import generate_outputs
from protocyte.errors import ProtocyteError
from protocyte.model import build_model
from protocyte.parameters import parse_parameter


@dataclass(frozen=True)
class GeneratorPolicy:
    """Operator-controlled restrictions for embedding Protocyte with untrusted input."""

    allow_formatter_parameters: bool = True
    format_outputs: bool = True
    formatter_timeout_seconds: float | None = None
    max_request_bytes: int | None = None
    max_files_to_generate: int | None = None
    max_proto_files: int | None = None
    max_descriptor_nodes: int | None = None
    max_nesting_depth: int | None = None
    max_generated_bytes: int | None = None

    def __post_init__(self) -> None:
        for item in fields(self):
            if not item.name.startswith("max_"):
                continue
            value = getattr(self, item.name)
            if value is not None and value < 0:
                raise ValueError(f"{item.name} must not be negative")
        if (
            self.formatter_timeout_seconds is not None
            and self.formatter_timeout_seconds <= 0
        ):
            raise ValueError("formatter_timeout_seconds must be positive")


def generate_response(
    request: plugin_pb2.CodeGeneratorRequest,
    *,
    policy: GeneratorPolicy | None = None,
) -> plugin_pb2.CodeGeneratorResponse:
    response = plugin_pb2.CodeGeneratorResponse()
    response.supported_features = plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    active_policy = policy or GeneratorPolicy()
    phase = "validating the generator request"

    try:
        _validate_request_policy(request, active_policy)
        phase = "parsing generator parameters"
        options = parse_parameter(request.parameter)
        if not active_policy.allow_formatter_parameters and (
            options.clang_format is not None
            or options.clang_format_config is not None
        ):
            raise ProtocyteError(
                "clang_format and clang_format_config are disabled by the generator policy"
            )
        phase = "building the descriptor model"
        model = build_model(request)
        phase = "generating C++ outputs"
        outputs = generate_outputs(
            model,
            options,
            format_outputs=active_policy.format_outputs,
            formatter_timeout_seconds=active_policy.formatter_timeout_seconds,
            max_output_bytes=active_policy.max_generated_bytes,
        )
        phase = "assembling the generator response"
        for name, content in sorted(outputs.items()):
            file = response.file.add()
            file.name = name.replace("\\", "/")
            file.content = content
    except ProtocyteError as exc:
        response.ClearField("file")
        response.error = str(exc)
        return response
    except Exception as exc:
        response.ClearField("file")
        detail = str(exc).strip()
        response.error = f"internal Protocyte error while {phase} ({type(exc).__name__})"
        if detail:
            response.error += f": {detail}"
        return response

    return response


def _validate_request_policy(
    request: plugin_pb2.CodeGeneratorRequest, policy: GeneratorPolicy
) -> None:
    _check_limit("serialized request bytes", request.ByteSize(), policy.max_request_bytes)
    _check_limit(
        "files to generate", len(request.file_to_generate), policy.max_files_to_generate
    )
    _check_limit("proto files", len(request.proto_file), policy.max_proto_files)

    _request_descriptor_complexity(
        request,
        max_descriptor_nodes=policy.max_descriptor_nodes,
        max_nesting_depth=policy.max_nesting_depth,
    )


def _check_limit(label: str, actual: int, limit: int | None) -> None:
    if limit is not None and actual > limit:
        raise ProtocyteError(
            f"generator policy limit exceeded for {label}: {actual} > {limit}"
        )


def _request_descriptor_complexity(
    request: plugin_pb2.CodeGeneratorRequest,
    *,
    max_descriptor_nodes: int | None,
    max_nesting_depth: int | None,
) -> tuple[int, int]:
    nodes = 0
    max_depth = 0
    for file in request.proto_file:
        nodes += 1 + len(file.extension)
        _check_limit("descriptor nodes", nodes, max_descriptor_nodes)
        nodes += sum(_enum_node_count(enum) for enum in file.enum_type)
        _check_limit("descriptor nodes", nodes, max_descriptor_nodes)
        nodes += sum(1 + len(service.method) for service in file.service)
        _check_limit("descriptor nodes", nodes, max_descriptor_nodes)
        _check_limit(
            "descriptor nodes",
            nodes + len(file.message_type),
            max_descriptor_nodes,
        )
        stack = [(message, 1) for message in file.message_type]
        while stack:
            message, depth = stack.pop()
            _check_limit("message nesting depth", depth, max_nesting_depth)
            nodes += 1 + len(message.field) + len(message.extension) + len(
                message.oneof_decl
            )
            _check_limit("descriptor nodes", nodes, max_descriptor_nodes)
            nodes += sum(_enum_node_count(enum) for enum in message.enum_type)
            _check_limit("descriptor nodes", nodes, max_descriptor_nodes)
            max_depth = max(max_depth, depth)
            _check_limit(
                "descriptor nodes",
                nodes + len(message.nested_type),
                max_descriptor_nodes,
            )
            stack.extend((nested, depth + 1) for nested in message.nested_type)
    return nodes, max_depth


def _enum_node_count(enum: descriptor_pb2.EnumDescriptorProto) -> int:
    return 1 + len(enum.value)
