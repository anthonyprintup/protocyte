from __future__ import annotations

import math
from dataclasses import dataclass, fields

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from protocyte.cpp import generate_outputs
from protocyte.descriptor_set import (
    render_diagnostic_context,
    validate_descriptor_string_fields,
)
from protocyte.errors import ProtocyteError
from protocyte.model import build_model
from protocyte.parameters import parse_parameter


@dataclass(frozen=True)
class GeneratorPolicy:
    """Operator-controlled restrictions for embedding Protocyte with untrusted input.

    ``max_descriptor_nodes`` preserves its declaration-node meaning.  Set
    ``max_descriptor_metadata_bytes`` to bound every serialized descriptor
    surface traversed before model construction, including source-code
    locations, paths, spans, comments, dependency strings, and unknown fields.
    For backwards-compatible safe embedding, a configured
    ``max_descriptor_nodes`` also supplies this metadata byte budget unless an
    explicit ``max_descriptor_metadata_bytes`` overrides it.
    """

    allow_formatter_parameters: bool = True
    format_outputs: bool = True
    formatter_timeout_seconds: float | None = None
    max_request_bytes: int | None = None
    max_files_to_generate: int | None = None
    max_proto_files: int | None = None
    max_descriptor_nodes: int | None = None
    max_descriptor_metadata_bytes: int | None = None
    max_nesting_depth: int | None = None
    max_generated_bytes: int | None = None

    def __post_init__(self) -> None:
        for item in fields(self):
            if type(item.default) is not bool:
                continue
            if type(getattr(self, item.name)) is not bool:
                raise TypeError(f"{item.name} must be a boolean")

        for item in fields(self):
            if not item.name.startswith("max_"):
                continue
            value = getattr(self, item.name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{item.name} must be an integer or None")
            if value < 0:
                raise ValueError(f"{item.name} must not be negative")

        timeout = self.formatter_timeout_seconds
        if timeout is None:
            return
        if isinstance(timeout, bool) or not isinstance(timeout, int | float):
            raise TypeError(
                "formatter_timeout_seconds must be a real number or None"
            )
        try:
            finite = math.isfinite(timeout)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("formatter_timeout_seconds must be finite")
        if timeout <= 0:
            raise ValueError("formatter_timeout_seconds must be positive")


def generate_response(
    request: plugin_pb2.CodeGeneratorRequest,
    *,
    policy: GeneratorPolicy | None = None,
    use_plugin_defaults: bool = False,
) -> plugin_pb2.CodeGeneratorResponse:
    response = plugin_pb2.CodeGeneratorResponse()
    response.supported_features = plugin_pb2.CodeGeneratorResponse.FEATURE_PROTO3_OPTIONAL
    active_policy = policy or GeneratorPolicy()
    phase = "validating the generator request"

    try:
        _validate_request_policy(request, active_policy)
        validate_descriptor_string_fields(request, root="CodeGeneratorRequest")
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
        formatter_timeout_seconds = (
            options.formatter_timeout_seconds
            if use_plugin_defaults and policy is None
            else active_policy.formatter_timeout_seconds
        )
        outputs = generate_outputs(
            model,
            options,
            format_outputs=active_policy.format_outputs,
            formatter_timeout_seconds=formatter_timeout_seconds,
            max_output_bytes=active_policy.max_generated_bytes,
        )
        phase = "assembling the generator response"
        for name, content in sorted(outputs.items()):
            file = response.file.add()
            file.name = name.replace("\\", "/")
            file.content = content
    except ProtocyteError as exc:
        response.ClearField("file")
        response.error = render_diagnostic_context(str(exc))
        return response
    except Exception as exc:
        response.ClearField("file")
        detail = render_diagnostic_context(str(exc).strip())
        response.error = f"internal Protocyte error while {phase} ({type(exc).__name__})"
        if detail:
            response.error += f": {detail}"
        return response

    return response


def _validate_request_policy(
    request: plugin_pb2.CodeGeneratorRequest, policy: GeneratorPolicy
) -> None:
    metadata_limit = _descriptor_metadata_limit(policy)
    request_bytes: int | None = None
    if policy.max_request_bytes is not None or metadata_limit is not None:
        request_bytes = request.ByteSize()
        _check_limit(
            "serialized request bytes", request_bytes, policy.max_request_bytes
        )
    _check_limit(
        "files to generate", len(request.file_to_generate), policy.max_files_to_generate
    )
    _check_limit("proto files", len(request.proto_file), policy.max_proto_files)
    if metadata_limit is not None:
        assert request_bytes is not None
        _check_limit("descriptor metadata bytes", request_bytes, metadata_limit)

    if policy.max_descriptor_nodes is not None or policy.max_nesting_depth is not None:
        _request_descriptor_complexity(
            request,
            max_descriptor_nodes=policy.max_descriptor_nodes,
            max_nesting_depth=policy.max_nesting_depth,
        )


def _descriptor_metadata_limit(policy: GeneratorPolicy) -> int | None:
    """Select the independent metadata budget with a safe legacy fallback."""
    if policy.max_descriptor_metadata_bytes is not None:
        return policy.max_descriptor_metadata_bytes
    return policy.max_descriptor_nodes


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
    """Return legacy declaration-node total and descriptor message depth."""
    nodes = 0
    max_depth = 0
    for file in request.proto_file:
        nodes = _add_descriptor_nodes(
            nodes,
            1 + len(file.extension),
            max_descriptor_nodes,
        )
        for enum in file.enum_type:
            nodes = _add_descriptor_nodes(
                nodes,
                _enum_node_count(enum),
                max_descriptor_nodes,
            )
        for service in file.service:
            nodes = _add_descriptor_nodes(
                nodes,
                1 + len(service.method),
                max_descriptor_nodes,
            )
        _check_limit(
            "descriptor nodes",
            nodes + len(file.message_type),
            max_descriptor_nodes,
        )
        stack = [(message, 1) for message in file.message_type]
        while stack:
            message, depth = stack.pop()
            _check_limit("message nesting depth", depth, max_nesting_depth)
            nodes = _add_descriptor_nodes(
                nodes,
                _message_node_count(message),
                max_descriptor_nodes,
            )
            for enum in message.enum_type:
                nodes = _add_descriptor_nodes(
                    nodes,
                    _enum_node_count(enum),
                    max_descriptor_nodes,
                )
            max_depth = max(max_depth, depth)
            _check_limit(
                "descriptor nodes",
                nodes + len(message.nested_type),
                max_descriptor_nodes,
            )
            stack.extend((nested, depth + 1) for nested in message.nested_type)
    return nodes, max_depth


def _add_descriptor_nodes(nodes: int, count: int, limit: int | None) -> int:
    nodes += count
    _check_limit("descriptor nodes", nodes, limit)
    return nodes


def _enum_node_count(enum: descriptor_pb2.EnumDescriptorProto) -> int:
    return (
        1
        + len(enum.value)
        + len(enum.reserved_name)
        + len(enum.reserved_range)
    )


def _message_node_count(message: descriptor_pb2.DescriptorProto) -> int:
    return (
        1
        + len(message.field)
        + len(message.extension)
        + len(message.oneof_decl)
        + len(message.extension_range)
        + len(message.reserved_range)
        + len(message.reserved_name)
    )
