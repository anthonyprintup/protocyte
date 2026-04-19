from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess

from protocyte.errors import ProtocyteError
from protocyte.model import (
    CONSTANT_KIND_STRING,
    SCALAR_CPP_TYPES,
    SCALAR_DEFAULTS,
    DescriptorModel,
    EnumModel,
    FieldDescriptorProto,
    FieldModel,
    FileModel,
    MessageModel,
    OneofModel,
    cpp_identifier,
)
from protocyte.parameters import GeneratorOptions
from protocyte.runtime import runtime_files


_RUNTIME_SCALAR_TYPES = {
    "int32_t": "::protocyte::i32",
    "int64_t": "::protocyte::i64",
    "uint32_t": "::protocyte::u32",
    "uint64_t": "::protocyte::u64",
    "float": "::protocyte::f32",
    "double": "::protocyte::f64",
}

_SCALAR_READ_HELPERS = {
    FieldDescriptorProto.TYPE_INT32: "read_int32",
    FieldDescriptorProto.TYPE_INT64: "read_int64",
    FieldDescriptorProto.TYPE_UINT32: "read_uint32",
    FieldDescriptorProto.TYPE_UINT64: "read_uint64",
    FieldDescriptorProto.TYPE_SINT32: "read_sint32",
    FieldDescriptorProto.TYPE_SINT64: "read_sint64",
    FieldDescriptorProto.TYPE_FIXED32: "read_fixed32_value",
    FieldDescriptorProto.TYPE_FIXED64: "read_fixed64_value",
    FieldDescriptorProto.TYPE_SFIXED32: "read_sfixed32",
    FieldDescriptorProto.TYPE_SFIXED64: "read_sfixed64",
    FieldDescriptorProto.TYPE_FLOAT: "read_float",
    FieldDescriptorProto.TYPE_DOUBLE: "read_double",
    FieldDescriptorProto.TYPE_BOOL: "read_bool",
    FieldDescriptorProto.TYPE_ENUM: "read_enum",
}

_SCALAR_WRITE_HELPERS = {
    FieldDescriptorProto.TYPE_INT32: "write_int32",
    FieldDescriptorProto.TYPE_INT64: "write_int64",
    FieldDescriptorProto.TYPE_UINT32: "write_uint32",
    FieldDescriptorProto.TYPE_UINT64: "write_uint64",
    FieldDescriptorProto.TYPE_SINT32: "write_sint32",
    FieldDescriptorProto.TYPE_SINT64: "write_sint64",
    FieldDescriptorProto.TYPE_FIXED32: "write_fixed32_value",
    FieldDescriptorProto.TYPE_FIXED64: "write_fixed64_value",
    FieldDescriptorProto.TYPE_SFIXED32: "write_sfixed32",
    FieldDescriptorProto.TYPE_SFIXED64: "write_sfixed64",
    FieldDescriptorProto.TYPE_FLOAT: "write_float",
    FieldDescriptorProto.TYPE_DOUBLE: "write_double",
    FieldDescriptorProto.TYPE_BOOL: "write_bool",
    FieldDescriptorProto.TYPE_ENUM: "write_enum",
}


@dataclass
class CppWriter:
    indent: int = 0
    lines: list[str] = field(default_factory=list)

    def line(self, text: str = "") -> None:
        self.lines.append(("  " * self.indent + text) if text else "")

    def push(self) -> None:
        self.indent += 1

    def pop(self) -> None:
        self.indent -= 1

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"


def generate_outputs(model: DescriptorModel, options: GeneratorOptions) -> dict[str, str]:
    outputs: dict[str, str] = {}
    if options.emit_runtime:
        outputs.update(runtime_files(options.runtime_prefix))
    for file_model in model.generated_files():
        outputs[_header_name(file_model.name)] = generate_header(file_model, options)
        outputs[_source_name(file_model.name)] = generate_source(file_model, options)
    return _format_cpp_outputs(outputs)


def _format_cpp_outputs(outputs: dict[str, str]) -> dict[str, str]:
    clang_format = _clang_format_executable()
    style_args = _clang_format_style_args()
    formatted: dict[str, str] = {}
    for name, content in outputs.items():
        if not name.endswith((".h", ".hh", ".hpp", ".c", ".cc", ".cpp", ".cxx")):
            formatted[name] = content
            continue
        try:
            result = subprocess.run(
                [clang_format, *style_args, f"--assume-filename={name}"],
                input=content,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise ProtocyteError(f"failed to run clang-format: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise ProtocyteError(f"clang-format failed for {name}: {detail}")
        formatted[name] = result.stdout
    return formatted


def _clang_format_executable() -> str:
    found = shutil.which("clang-format")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files\LLVM\bin\clang-format.exe"),
        Path(r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\VC\Tools\Llvm\x64\bin\clang-format.exe"),
        Path(r"C:\Program Files\Microsoft Visual Studio\18\Enterprise\VC\Tools\Llvm\bin\clang-format.exe"),
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\Llvm\x64\bin\clang-format.exe"),
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Tools\Llvm\bin\clang-format.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise ProtocyteError("clang-format is required to format generated C++ output")


def _clang_format_style_args() -> list[str]:
    config = _find_clang_format_config()
    if config is None:
        return ["--style=file"]
    return [f"--style=file:{config}"]


def _find_clang_format_config() -> Path | None:
    for root in (Path.cwd(), Path(__file__).resolve().parents[2]):
        for directory in (root, *root.parents):
            config = directory / ".clang-format"
            if config.is_file():
                return config
    return None


def generate_header(file_model: FileModel, options: GeneratorOptions) -> str:
    w = CppWriter()
    guard = _include_guard(file_model.name)
    w.line("#pragma once")
    w.line()
    w.line(f"#ifndef {guard}")
    w.line(f"#define {guard}")
    w.line()
    w.line(f"#include <{options.runtime_prefix}/runtime.hpp>")
    extra_includes: list[str] = []
    if _file_uses_string_view(file_model):
        extra_includes.append("#include <string_view>")
    for dependency in sorted(file_model.dependencies):
        extra_includes.append(f'#include "{_include_path(dependency, options)}"')
    if extra_includes:
        w.line()
        for include in extra_includes:
            w.line(include)
    w.line()
    _open_namespace(w, _namespace_parts(file_model, options))
    _emit_enums(w, file_model)
    _emit_file_constants(w, file_model)
    for message in _ordered_messages(file_model):
        w.line("template <typename Config = ::protocyte::DefaultConfig>")
        w.line(f"struct {message.cpp_name};")
    w.line()
    for message in _ordered_messages(file_model):
        _emit_message(w, message, options)
        w.line()
    _close_namespace(w, _namespace_parts(file_model, options))
    w.line()
    w.line(f"#endif  // {guard}")
    return w.render()


def generate_source(file_model: FileModel, options: GeneratorOptions) -> str:
    w = CppWriter()
    w.line(f'#include "{_header_name(file_model.name)}"')
    w.line()
    w.line("#ifdef PROTOCYTE_ENABLE_REFLECTION")
    _open_namespace(w, _namespace_parts(file_model, options))
    w.line("namespace protocyte_reflection {")
    w.push()
    w.line(
        "struct FieldInfo { const char* name; ::protocyte::u32 number; const char* kind; bool repeated; bool optional; bool packed; };"
    )
    w.line()
    for message in _ordered_messages(file_model):
        w.line(f"static const FieldInfo {message.cpp_name}_fields[] = {{")
        w.push()
        for item in message.fields:
            w.line(
                f'{{"{_escape(item.name)}", {item.number}u, "{item.kind}", '
                f"{_cpp_bool(item.repeated)}, {_cpp_bool(item.has_explicit_presence)}, {_cpp_bool(item.packed)}}},"
            )
        w.pop()
        w.line("};")
        w.line()
    w.pop()
    w.line("}  // namespace protocyte_reflection")
    _close_namespace(w, _namespace_parts(file_model, options))
    w.line("#endif  // PROTOCYTE_ENABLE_REFLECTION")
    return w.render()


def _emit_enums(w: CppWriter, file_model: FileModel) -> None:
    enums = list(file_model.enums)
    for message in _walk_messages(file_model.messages):
        enums.extend(message.nested_enums)
    for enum in enums:
        w.line(f"enum struct {enum.cpp_name} : ::protocyte::i32 {{")
        w.push()
        for value in enum.values:
            w.line(f"{value.cpp_name} = {value.number},")
        w.pop()
        w.line("};")
        w.line()


def _emit_constants(w: CppWriter, message: MessageModel) -> None:
    if not message.constants:
        return
    for constant in message.constants:
        w.line(f"static constexpr {constant.cpp_type} {constant.cpp_name} {{{constant.cpp_value}}};")
    w.line()


def _emit_file_constants(w: CppWriter, file_model: FileModel) -> None:
    if not file_model.constants:
        return
    for constant in file_model.constants:
        w.line(f"inline constexpr {constant.cpp_type} {constant.cpp_name} {{{constant.cpp_value}}};")
    w.line()


def _emit_message(w: CppWriter, message: MessageModel, options: GeneratorOptions) -> None:
    w.line("template <typename Config>")
    w.line(f"struct {message.cpp_name} {{")
    w.push()
    w.line("using Context = typename Config::Context;")
    w.line("using RuntimeStatus = ::protocyte::Status;")
    for enum in message.nested_enums:
        w.line(f"using {enum.name} = {enum.cpp_name};")
    for nested in message.nested_messages:
        if not nested.is_map_entry:
            w.line("template <typename NestedConfig = Config>")
            w.line(f"using {nested.name} = {nested.cpp_name}<NestedConfig>;")
    if message.nested_enums or message.nested_messages:
        w.line()
    _emit_constants(w, message)
    _emit_oneof_case_enums(w, message)
    _emit_field_number_enum(w, message)
    w.line(f"explicit {message.cpp_name}(Context& ctx) noexcept")
    _emit_constructor_initializers(w, message)
    _emit_constructor_body(w, message)
    w.line()
    w.line(f"static ::protocyte::Result<{message.cpp_name}> create(Context& ctx) noexcept {{")
    w.push()
    w.line(f"return ::protocyte::Result<{message.cpp_name}>::ok({message.cpp_name}{{ctx}});")
    w.pop()
    w.line("}")
    _emit_special_members(w, message, options)
    w.line(f"{message.cpp_name}(const {message.cpp_name}&) = delete;")
    w.line(f"{message.cpp_name}& operator=(const {message.cpp_name}&) = delete;")
    w.line()
    if message.oneofs:
        w.line("template <typename T>")
        w.line("static void destroy_at_(T* value) noexcept { value->~T(); }")
        w.line()
    _emit_clone_api(w, message, options)
    for oneof in message.oneofs:
        lower = cpp_identifier(oneof.name)
        w.line(f"constexpr {oneof.cpp_name}Case {lower}_case() const noexcept {{ return {lower}_case_; }}")
        w.line(f"void clear_{lower}() noexcept {{")
        w.push()
        w.line(f"switch ({lower}_case_) {{")
        w.push()
        for item in oneof.fields:
            w.line(f"case {oneof.cpp_name}Case::{item.cpp_name}: {{")
            w.push()
            _emit_destroy_oneof_member(w, item)
            w.line("break;")
            w.pop()
            w.line("}")
        w.line(f"case {oneof.cpp_name}Case::none:")
        w.line("default: {")
        w.push()
        w.line("break;")
        w.pop()
        w.line("}")
        w.pop()
        w.line("}")
        w.line(f"{lower}_case_ = {oneof.cpp_name}Case::none;")
        w.pop()
        w.line("}")
        w.line()
    for item in message.fields:
        _emit_accessors(w, item, options)
        w.line()
    _emit_wire_api(w, message, options)
    w.pop()
    w.line("protected:")
    w.push()
    w.line("Context* ctx_;")
    oneofs_by_name = {oneof.name: oneof for oneof in message.oneofs}
    emitted_oneofs: set[str] = set()
    for item in message.fields:
        if item.oneof_name is not None:
            if item.oneof_name in emitted_oneofs:
                continue
            oneof = oneofs_by_name[item.oneof_name]
            w.line(f"{oneof.cpp_name}Case {cpp_identifier(oneof.name)}_case_ {{{oneof.cpp_name}Case::none}};")
            _emit_oneof_storage(w, oneof, options)
            emitted_oneofs.add(item.oneof_name)
            continue
        _emit_member(w, item, options)
    w.pop()
    w.line("};")


def _emit_oneof_case_enums(w: CppWriter, message: MessageModel) -> None:
    for oneof in message.oneofs:
        w.line(f"enum struct {oneof.cpp_name}Case : ::protocyte::u32 {{")
        w.push()
        w.line("none = 0u,")
        for item in oneof.fields:
            w.line(f"{item.cpp_name} = {item.number}u,")
        w.pop()
        w.line("};")
        w.line()


def _emit_field_number_enum(w: CppWriter, message: MessageModel) -> None:
    if not message.fields:
        return
    w.line("enum struct FieldNumber : ::protocyte::u32 {")
    w.push()
    for item in sorted(message.fields, key=lambda field: field.number):
        w.line(f"{_field_number_name(item)} = {item.number}u,")
    w.pop()
    w.line("};")
    w.line()


def _emit_constructor_initializers(w: CppWriter, message: MessageModel) -> None:
    initializers = ["ctx_{&ctx}"]
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        member = _member(item)
        if item.repeated_array or item.array_enabled:
            continue
        if (item.kind in {"string", "bytes", "map"}) or (item.repeated and item.kind != "map"):
            initializers.append(f"{member}{{&ctx}}")
        elif item.kind == "message" and item.recursive_box:
            initializers.append(f"{member}{{&ctx}}")
    w.push()
    for index, initializer in enumerate(initializers):
        prefix = ": " if index == 0 else ", "
        w.line(f"{prefix}{initializer}")
    w.pop()


def _emit_constructor_body(w: CppWriter, message: MessageModel) -> None:
    del message
    w.line("{}")


def _emit_special_members(w: CppWriter, message: MessageModel, options: GeneratorOptions) -> None:
    if not message.oneofs:
        w.line(f"{message.cpp_name}({message.cpp_name}&&) noexcept = default;")
        w.line(f"{message.cpp_name}& operator=({message.cpp_name}&&) noexcept = default;")
        return
    w.line(f"{message.cpp_name}({message.cpp_name}&& other) noexcept")
    _emit_move_constructor_initializers(w, message)
    w.line("{")
    w.push()
    _emit_move_state_setup(w, message)
    for oneof in message.oneofs:
        _emit_move_oneof_from_other(w, oneof, options, source="other")
    w.pop()
    w.line("}")
    w.line(f"{message.cpp_name}& operator=({message.cpp_name}&& other) noexcept {{")
    w.push()
    w.line("if (this == &other) { return *this; }")
    for oneof in message.oneofs:
        w.line(f"clear_{cpp_identifier(oneof.name)}();")
    w.line("ctx_ = other.ctx_;")
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        _emit_move_assignment_for_field(w, item)
    for oneof in message.oneofs:
        _emit_move_oneof_from_other(w, oneof, options, source="other")
    w.line("return *this;")
    w.pop()
    w.line("}")
    w.line(f"~{message.cpp_name}() noexcept {{")
    w.push()
    for oneof in message.oneofs:
        w.line(f"clear_{cpp_identifier(oneof.name)}();")
    w.pop()
    w.line("}")


def _emit_move_constructor_initializers(w: CppWriter, message: MessageModel) -> None:
    initializers = ["ctx_{other.ctx_}"]
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        member = _member(item)
        if item.repeated or item.kind == "map" or item.kind in {"string", "bytes", "message"}:
            initializers.append(f"{member}{{::protocyte::move(other.{member})}}")
        else:
            initializers.append(f"{member}{{other.{member}}}")
    w.push()
    for index, initializer in enumerate(initializers):
        prefix = ": " if index == 0 else ", "
        w.line(f"{prefix}{initializer}")
    w.pop()


def _emit_move_state_setup(w: CppWriter, message: MessageModel) -> None:
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        if _has_presence_flag(item):
            w.line(f"has_{item.cpp_name}_ = other.has_{item.cpp_name}_;")


def _emit_move_assignment_for_field(w: CppWriter, item: FieldModel) -> None:
    member = _member(item)
    if item.repeated or item.kind == "map" or item.kind in {"string", "bytes", "message"}:
        w.line(f"{member} = ::protocyte::move(other.{member});")
    else:
        w.line(f"{member} = other.{member};")
    if _has_presence_flag(item):
        w.line(f"has_{item.cpp_name}_ = other.has_{item.cpp_name}_;")


def _emit_move_oneof_from_other(w: CppWriter, oneof: OneofModel, options: GeneratorOptions, *, source: str) -> None:
    lower = cpp_identifier(oneof.name)
    case_type = oneof.cpp_name + "Case"
    w.line(f"switch ({source}.{lower}_case_) {{")
    w.push()
    for item in oneof.fields:
        storage_type = _storage_type(item, options)
        value = f"::protocyte::move({source}.{_member(item)})" if item.kind in {"string", "bytes", "message"} else f"{source}.{_member(item)}"
        w.line(f"case {case_type}::{item.cpp_name}: {{")
        w.push()
        w.line(f"new (&{_member(item)}) {storage_type} {{{value}}};")
        w.line(f"{lower}_case_ = {case_type}::{item.cpp_name};")
        w.line("break;")
        w.pop()
        w.line("}")
    w.line(f"case {case_type}::none:")
    w.line("default: {")
    w.push()
    w.line("break;")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.line(f"{source}.clear_{lower}();")


def _emit_clone_api(w: CppWriter, message: MessageModel, options: GeneratorOptions) -> None:
    non_oneof_fields = [item for item in message.fields if item.oneof_name is None]
    map_only = bool(non_oneof_fields) and all(item.kind == "map" for item in non_oneof_fields)
    w.line(f"::protocyte::Status copy_from(const {message.cpp_name}& other) noexcept {{")
    w.push()
    w.line("if (this == &other) { return ::protocyte::Status::ok(); }")
    if map_only:
        w.line("const auto& source = other;")
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        if item.fixed_bytes:
            w.line(f"if (other.has_{item.cpp_name}()) {{")
            w.push()
            w.line(f"if (const auto st = set_{item.cpp_name}(other.{item.cpp_name}()); !st) {{ return st; }}")
            w.pop()
            w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            continue
        if item.kind == "map":
            _emit_copy_map_field(w, item, options, source="source" if map_only else "other")
            continue
        if item.repeated_array:
            _emit_copy_repeated_field(w, item, options)
            continue
        if item.repeated:
            _emit_copy_repeated_field(w, item, options)
            continue
        if item.kind in {"string", "bytes"}:
            if _has_presence_flag(item):
                w.line(f"if (other.has_{item.cpp_name}()) {{")
                w.push()
                w.line(f"if (const auto st = set_{item.cpp_name}(other.{item.cpp_name}()); !st) {{ return st; }}")
                w.pop()
                w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            else:
                w.line(f"if (const auto st = set_{item.cpp_name}(other.{item.cpp_name}()); !st) {{ return st; }}")
        elif item.kind == "message":
            w.line(f"if (other.has_{item.cpp_name}()) {{")
            w.push()
            w.line(f"if (auto ensured = ensure_{item.cpp_name}(); !ensured) {{")
            w.push()
            w.line("return ensured.status();")
            w.pop()
            w.line("} else if (const auto st = ensured.value().get().copy_from(*other." + f"{item.cpp_name}()); !st) {{")
            w.push()
            w.line("return st;")
            w.pop()
            w.line("}")
            w.pop()
            w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
        elif item.kind == "enum":
            if _has_presence_flag(item):
                w.line(f"if (other.has_{item.cpp_name}()) {{")
                w.push()
                w.line(f"if (const auto st = set_{item.cpp_name}_raw(other.{item.cpp_name}_raw()); !st) {{ return st; }}")
                w.pop()
                w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            else:
                w.line(f"if (const auto st = set_{item.cpp_name}_raw(other.{item.cpp_name}_raw()); !st) {{ return st; }}")
        elif not item.repeated and item.kind != "map":
            if _has_presence_flag(item):
                w.line(f"if (other.has_{item.cpp_name}()) {{")
                w.push()
                w.line(f"if (const auto st = set_{item.cpp_name}(other.{item.cpp_name}()); !st) {{ return st; }}")
                w.pop()
                w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
            else:
                w.line(f"if (const auto st = set_{item.cpp_name}(other.{item.cpp_name}()); !st) {{ return st; }}")
    for oneof in message.oneofs:
        _emit_copy_oneof_from_other(w, oneof, options, source="other")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")
    w.line()
    w.line(f"::protocyte::Result<{message.cpp_name}> clone() const noexcept {{")
    w.push()
    w.line(f"auto out = {message.cpp_name}::create(*ctx_);")
    w.line("if (!out) { return out; }")
    w.line(f"if (const auto st = out.value().copy_from(*this); !st) {{ return ::protocyte::Result<{message.cpp_name}>::err(st.error()); }}")
    w.line("return out;")
    w.pop()
    w.line("}")
    w.line()


def _emit_copy_repeated_field(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    source = f"other.{item.cpp_name}()"
    w.line(f"clear_{item.cpp_name}();")
    w.line(f"for (::protocyte::usize i {{}}; i < {source}.size(); ++i) {{")
    w.push()
    if item.kind in {"string", "bytes"}:
        typ = _field_type(item, options)
        w.line(f"{typ} value{{ctx_}};")
        w.line(f"if (const auto st = value.assign({source}[i].view()); !st) {{ return st; }}")
        w.line(f"if (const auto st = mutable_{item.cpp_name}().push_back(::protocyte::move(value)); !st) {{ return st; }}")
    elif item.kind == "message":
        w.line(f"auto copied = mutable_{item.cpp_name}().emplace_back(*ctx_);")
        w.line("if (!copied) { return copied.status(); }")
        w.line(f"if (const auto st = copied.value().get().copy_from({source}[i]); !st) {{ return st; }}")
    else:
        w.line(f"if (const auto st = mutable_{item.cpp_name}().push_back({source}[i]); !st) {{ return st; }}")
    w.pop()
    w.line("}")


def _emit_copy_map_field(w: CppWriter, item: FieldModel, options: GeneratorOptions, *, source: str = "other") -> None:
    assert item.map_key is not None and item.map_value is not None
    key_type = _field_type(item.map_key, options)
    value_type = _field_type(item.map_value, options)
    w.line(f"clear_{item.cpp_name}();")
    w.line(f"if (const auto st = {source}.{item.cpp_name}().for_each([&](const auto& key, const auto& value) noexcept {{")
    w.push()
    if item.map_key.kind == "string":
        w.line(f"{key_type} copied_key{{ctx_}};")
        w.line("if (const auto st = copied_key.assign(key.view()); !st) { return st; }")
    else:
        w.line("auto copied_key = key;")
    if item.map_value.kind in {"string", "bytes"}:
        w.line(f"{value_type} copied_value{{ctx_}};")
        w.line("if (const auto st = copied_value.assign(value.view()); !st) { return st; }")
    elif item.map_value.kind == "message":
        w.line(f"{value_type} copied_value{{*ctx_}};")
        w.line("if (const auto st = copied_value.copy_from(value); !st) { return st; }")
    else:
        w.line("auto copied_value = value;")
    w.line(f"if (const auto insert = mutable_{item.cpp_name}().insert_or_assign(::protocyte::move(copied_key), ::protocyte::move(copied_value)); !insert) {{ return insert; }}")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}); !st) { return st; }")


def _emit_copy_oneof_from_other(w: CppWriter, oneof: OneofModel, options: GeneratorOptions, *, source: str) -> None:
    lower = cpp_identifier(oneof.name)
    case_type = oneof.cpp_name + "Case"
    case_member = _oneof_case_member(oneof.name)
    w.line(f"switch ({source}.{case_member}) {{")
    w.push()
    for item in oneof.fields:
        w.line(f"case {case_type}::{item.cpp_name}: {{")
        w.push()
        if item.kind in {"string", "bytes"}:
            w.line(f"if (const auto st = set_{item.cpp_name}({source}.{item.cpp_name}()); !st) {{ return st; }}")
        elif item.kind == "message":
            w.line(f"if (auto ensured = ensure_{item.cpp_name}(); !ensured) {{")
            w.push()
            w.line("return ensured.status();")
            w.pop()
            w.line(f"}} else if (const auto st = ensured.value().get().copy_from(*{source}.{item.cpp_name}()); !st) {{")
            w.push()
            w.line("return st;")
            w.pop()
            w.line("}")
        elif item.kind == "enum":
            w.line(f"if (const auto st = set_{item.cpp_name}_raw({source}.{item.cpp_name}_raw()); !st) {{ return st; }}")
        else:
            w.line(f"if (const auto st = set_{item.cpp_name}({source}.{item.cpp_name}()); !st) {{ return st; }}")
        w.line("break;")
        w.pop()
        w.line("}")
    w.line(f"case {case_type}::none:")
    w.line("default: {")
    w.push()
    w.line(f"clear_{lower}();")
    w.line("break;")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")


def _emit_accessors(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.oneof_name is not None:
        _emit_oneof_accessors(w, item, options)
        return
    if item.repeated and item.kind != "map":
        typ = _storage_type(item, options)
        w.line(f"const {typ}& {item.cpp_name}() const noexcept {{ return {_member(item)}; }}")
        w.line(f"{typ}& mutable_{item.cpp_name}() noexcept {{ return {_member(item)}; }}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear(); }}")
        return
    if item.kind == "map":
        assert item.map_key is not None and item.map_value is not None
        typ = f"typename Config::template Map<{_field_type(item.map_key, options)}, {_field_type(item.map_value, options)}>"
        w.line(f"const {typ}& {item.cpp_name}() const noexcept {{ return {_member(item)}; }}")
        w.line(f"{typ}& mutable_{item.cpp_name}() noexcept {{ return {_member(item)}; }}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear(); }}")
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        w.line(f"bool has_{item.cpp_name}() const noexcept {{ return {_member(item)}.has_value(); }}")
        w.line(f"const {typ}* {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() ? &{_member(item)}.value() : nullptr; }}")
        w.line(f"::protocyte::Result<::protocyte::Ref<{typ}>> ensure_{item.cpp_name}() noexcept {{")
        w.push()
        if item.recursive_box:
            w.line(f"return {_member(item)}.ensure();")
        else:
            w.line(f"if (!{_member(item)}.has_value()) {{")
            w.push()
            w.line(f"if (const auto st = {_member(item)}.emplace(*ctx_); !st) {{ return ::protocyte::Result<::protocyte::Ref<{typ}>>::err(st.error()); }}")
            w.pop()
            w.line("}")
            w.line(f"return ::protocyte::Result<::protocyte::Ref<{typ}>>::ok(::protocyte::Ref<{typ}>{{{_member(item)}.value()}});")
        w.pop()
        w.line("}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.reset(); }}")
        return
    if item.fixed_bytes:
        w.line(f"bool has_{item.cpp_name}() const noexcept {{ return {_member(item)}.has_value(); }}")
        w.line(f"::protocyte::ByteView {item.cpp_name}() const noexcept {{ return {_member(item)}.view(); }}")
        w.line(f"::protocyte::MutableByteView mutable_{item.cpp_name}() noexcept {{ return {_member(item)}.mutable_view(); }}")
        w.line(f"::protocyte::Status set_{item.cpp_name}(const ::protocyte::ByteView value) noexcept {{")
        w.push()
        w.line(f"return {_member(item)}.assign(value);")
        w.pop()
        w.line("}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear(); }}")
        return
    if item.kind == "bytes" and item.array_enabled:
        bound = _array_max_literal(item)
        w.line(f"::protocyte::ByteView {item.cpp_name}() const noexcept {{ return {_member(item)}.view(); }}")
        if item.proto3_optional:
            w.line(f"bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}")
        w.line(f"::protocyte::usize {item.cpp_name}_size() const noexcept {{ return {_member(item)}.size(); }}")
        w.line(f"static constexpr ::protocyte::usize {item.cpp_name}_max_size() noexcept {{ return {bound}; }}")
        w.line(f"::protocyte::Status resize_{item.cpp_name}(const ::protocyte::usize size) noexcept {{")
        w.push()
        if item.array_fixed:
            w.line(f"if (size != {bound}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument); }}")
        w.line(f"if (const auto st = {_member(item)}.resize(size); !st) {{ return st; }}")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        w.line(f"::protocyte::MutableByteView mutable_{item.cpp_name}() noexcept {{")
        w.push()
        if item.array_fixed:
            w.line(f"if ({_member(item)}.size() != {bound}) {{")
            w.push()
            w.line(f"(void){_member(item)}.resize({bound});")
            w.pop()
            w.line("}")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line(f"return {_member(item)}.mutable_view();")
        w.pop()
        w.line("}")
        w.line(f"::protocyte::Status set_{item.cpp_name}(const ::protocyte::ByteView value) noexcept {{")
        w.push()
        if item.array_fixed:
            w.line(f"if (value.size != {bound}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument); }}")
        w.line(f"if (const auto st = {_member(item)}.assign(value); !st) {{ return st; }}")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear();")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    if item.kind in {"string", "bytes"}:
        typ = _field_type(item, options)
        w.line(f"::protocyte::ByteView {item.cpp_name}() const noexcept {{ return {_member(item)}.view(); }}")
        if item.proto3_optional:
            w.line(f"bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}")
        w.line(f"{typ}& mutable_{item.cpp_name}() noexcept {{")
        w.push()
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line(f"return {_member(item)};")
        w.pop()
        w.line("}")
        w.line(f"::protocyte::Status set_{item.cpp_name}(const ::protocyte::ByteView value) noexcept {{")
        w.push()
        w.line(f"{typ} temp{{ctx_}};")
        w.line("if (const auto st = temp.assign(value); !st) { return st; }")
        w.line(f"{_member(item)} = ::protocyte::move(temp);")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.clear();")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    if item.kind == "enum":
        enum_typ = _enum_type(item.enum_type, options)
        w.line(f"constexpr ::protocyte::i32 {item.cpp_name}_raw() const noexcept {{ return {_member(item)}; }}")
        w.line(f"constexpr {enum_typ} {item.cpp_name}() const noexcept {{ return static_cast<{enum_typ}>({_member(item)}); }}")
        if item.proto3_optional:
            w.line(f"constexpr bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}")
        w.line(
            f"constexpr ::protocyte::Status set_{item.cpp_name}_raw(const ::protocyte::i32 value) noexcept {{ {_member(item)} = value;"
        )
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return ::protocyte::Status::ok(); }")
        w.line(
            f"constexpr ::protocyte::Status set_{item.cpp_name}(const {enum_typ} value) noexcept {{ return set_{item.cpp_name}_raw(static_cast<::protocyte::i32>(value)); }}"
        )
        w.line(f"constexpr void clear_{item.cpp_name}() noexcept {{ {_member(item)} = {{}};")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    typ = _field_type(item, options)
    w.line(f"constexpr {typ} {item.cpp_name}() const noexcept {{ return {_member(item)}; }}")
    if item.proto3_optional:
        w.line(f"constexpr bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}")
    w.line(f"constexpr ::protocyte::Status set_{item.cpp_name}(const {typ} value) noexcept {{ {_member(item)} = value;")
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = true;")
    w.line("return ::protocyte::Status::ok(); }")
    w.line(f"constexpr void clear_{item.cpp_name}() noexcept {{ {_member(item)} = {{}};")
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = false;")
    w.line("}")


def _emit_oneof_accessors(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.oneof_name is not None
    case_type = _oneof_case_type(item.oneof_name)
    case_member = _oneof_case_member(item.oneof_name)
    typ = _field_type(item, options)
    w.line(
        f"constexpr bool has_{item.cpp_name}() const noexcept {{ return {case_member} == {case_type}::{item.cpp_name}; }}"
    )
    if item.kind in {"string", "bytes"}:
        w.line(
            f"::protocyte::ByteView {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)}.view() : ::protocyte::ByteView{{}}; }}"
        )
        w.line(f"::protocyte::Status set_{item.cpp_name}(const ::protocyte::ByteView value) noexcept {{")
        w.push()
        if item.kind == "bytes" and item.array_enabled:
            w.line(f"{_storage_type(item, options)} temp{{}};")
        else:
            w.line(f"{typ} temp{{ctx_}};")
        w.line("if (const auto st = temp.assign(value); !st) { return st; }")
        w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
        w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{::protocyte::move(temp)}};")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        return
    if item.kind == "message":
        w.line(
            f"const {typ}* {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() && {_member(item)}.has_value() ? &{_member(item)}.value() : nullptr; }}"
        )
        w.line(f"::protocyte::Result<::protocyte::Ref<{typ}>> ensure_{item.cpp_name}() noexcept {{")
        w.push()
        w.line(f"if (!has_{item.cpp_name}()) {{")
        w.push()
        w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
        if item.recursive_box:
            w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{ctx_}};")
        else:
            w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{}};")
        w.pop()
        w.line("}")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        if item.recursive_box:
            w.line(f"auto ensured = {_member(item)}.ensure();")
            w.line("if (!ensured) { return ensured; }")
        else:
            w.line(f"if (!{_member(item)}.has_value()) {{")
            w.push()
            w.line(f"if (const auto st = {_member(item)}.emplace(*ctx_); !st) {{ return ::protocyte::Result<::protocyte::Ref<{typ}>>::err(st.error()); }}")
            w.pop()
            w.line("}")
        w.line(f"return ::protocyte::Result<::protocyte::Ref<{typ}>>::ok(::protocyte::Ref<{typ}>{{{_member(item)}.value()}});")
        w.pop()
        w.line("}")
        return
    if item.kind == "enum":
        enum_typ = _enum_type(item.enum_type, options)
        w.line(
            f"constexpr ::protocyte::i32 {item.cpp_name}_raw() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)} : 0; }}"
        )
        w.line(f"constexpr {enum_typ} {item.cpp_name}() const noexcept {{ return static_cast<{enum_typ}>({item.cpp_name}_raw()); }}")
        w.line(f"::protocyte::Status set_{item.cpp_name}_raw(const ::protocyte::i32 value) noexcept {{")
        w.push()
        w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
        w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{value}};")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        w.line(
            f"::protocyte::Status set_{item.cpp_name}(const {enum_typ} value) noexcept {{ return set_{item.cpp_name}_raw(static_cast<::protocyte::i32>(value)); }}"
        )
        return
    w.line(f"constexpr {typ} {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() ? {_member(item)} : {_default(item)}; }}")
    w.line(f"::protocyte::Status set_{item.cpp_name}(const {typ} value) noexcept {{")
    w.push()
    w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
    w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{value}};")
    w.line(f"{case_member} = {case_type}::{item.cpp_name};")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")


def _emit_wire_api(w: CppWriter, message: MessageModel, options: GeneratorOptions) -> None:
    w.line("template <typename Reader>")
    w.line(f"static ::protocyte::Result<{message.cpp_name}> parse(Context& ctx, Reader& reader) noexcept {{")
    w.push()
    w.line(f"auto out = {message.cpp_name}::create(ctx);")
    w.line("if (!out) { return out; }")
    w.line(f"if (const auto st = out.value().merge_from(reader); !st) {{ return ::protocyte::Result<{message.cpp_name}>::err(st.error()); }}")
    w.line("return out;")
    w.pop()
    w.line("}")
    w.line()
    w.line("template <typename Reader>")
    w.line("RuntimeStatus merge_from(Reader& reader) noexcept {")
    w.push()
    w.line("while (!reader.eof()) {")
    w.push()
    w.line("auto tag = ::protocyte::read_varint(reader);")
    w.line("if (!tag) { return tag.status(); }")
    w.line("const auto field_number = static_cast<::protocyte::u32>(tag.value() >> 3u);")
    w.line("const auto wire_type = static_cast<::protocyte::WireType>(tag.value() & 0x7u);")
    if message.fields:
        w.line("switch (static_cast<FieldNumber>(field_number)) {")
        w.push()
        for item in sorted(message.fields, key=lambda f: f.number):
            w.line(f"case FieldNumber::{_field_number_name(item)}: {{")
            w.push()
            _emit_parse_case(w, item, options)
            w.line("break;")
            w.pop()
            w.line("}")
        w.line("default: {")
        w.push()
        w.line("if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) { return st; }")
        w.line("break;")
        w.pop()
        w.line("}")
        w.pop()
        w.line("}")
    else:
        w.line("if (const auto st = ::protocyte::skip_field(reader, wire_type, field_number); !st) { return st; }")
    w.pop()
    w.line("}")
    _emit_fixed_array_validation(w, message)
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")
    w.line()
    writer_name = "writer" if message.fields else "/* writer */"
    w.line("template <typename Writer>")
    w.line(f"RuntimeStatus serialize(Writer& {writer_name}) const noexcept {{")
    w.push()
    _emit_fixed_array_validation(w, message)
    for item in sorted(message.fields, key=lambda f: f.number):
        _emit_serialize_statement(w, item, options)
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")
    w.line()
    w.line("::protocyte::Result<::protocyte::usize> encoded_size() const noexcept {")
    w.push()
    if message.fields:
        _emit_fixed_array_validation(w, message, for_size=True)
        w.line("::protocyte::usize total {};")
        for item in sorted(message.fields, key=lambda f: f.number):
            _emit_size_statement(w, item, options)
        w.line("return ::protocyte::Result<::protocyte::usize>::ok(total);")
    else:
        w.line("return ::protocyte::Result<::protocyte::usize>::ok({});")
    w.pop()
    w.line("}")


def _emit_fixed_array_validation(w: CppWriter, message: MessageModel, *, for_size: bool = False) -> None:
    for item in sorted(message.fields, key=lambda f: f.number):
        if not item.array_fixed or item.array_max is None:
            continue
        if item.repeated:
            condition = f"{_member(item)}.size() != {_array_max_literal(item)}"
        else:
            continue
        error = (
            "::protocyte::Result<::protocyte::usize>::err(::protocyte::Status::error("
            "::protocyte::ErrorCode::invalid_argument, {}, "
            f"{_field_number_u32(item)}).error())"
        )
        w.line(f"if ({condition}) {{")
        w.push()
        if for_size:
            w.line(f"return {error};")
        else:
            w.line(
                f"return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument, {{}}, {_field_number_u32(item)});"
            )
        w.pop()
        w.line("}")


def _emit_parse_case(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.repeated and item.kind != "map":
        if item.packable:
            w.line("if (wire_type == ::protocyte::WireType::LEN) {")
            w.push()
            w.line("auto len = ::protocyte::read_varint(reader);")
            w.line("if (!len) { return len.status(); }")
            w.line("::protocyte::LimitedReader<Reader> packed{reader, static_cast<::protocyte::usize>(len.value())};")
            w.line("while (!packed.eof()) {")
            w.push()
            _emit_read_repeated_value(w, item, "packed", options)
            w.pop()
            w.line("}")
            w.line("if (const auto finish = packed.finish(); !finish) { return finish; }")
            w.line("break;")
            w.pop()
            w.line("}")
        if _is_scalar_field(item) or _uses_runtime_len_field_helper(item):
            _emit_read_repeated_value(w, item, "reader", options, checked=True)
        else:
            w.line(f"if (wire_type != {_wire(item)}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }}")
            _emit_read_repeated_value(w, item, "reader", options)
        return
    if item.kind == "map":
        _emit_read_map(w, item, options)
        return
    if _is_scalar_field(item) or _uses_runtime_len_field_helper(item):
        _emit_read_single_value(w, item, "reader", options)
        return
    w.line(f"if (wire_type != {_wire(item)}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }}")
    _emit_read_single_value(w, item, "reader", options)


def _emit_read_repeated_value(
    w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions, *, checked: bool = False
) -> None:
    if item.kind in {"string", "bytes"}:
        typ = _field_type(item, options)
        w.line(f"{typ} value{{ctx_}};")
        helper = _length_delimited_read_helper(item, checked=checked)
        args = f"*ctx_, {reader}, wire_type, field_number, value" if checked else f"*ctx_, {reader}, value"
        w.line(f"if (const auto st = ::protocyte::{helper}<Config>({args}); !st) {{ return st; }}")
        w.line(f"if (const auto st = {_member(item)}.push_back(::protocyte::move(value)); !st) {{ return st; }}")
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"{typ} value{{*ctx_}};")
        w.line(f"::protocyte::LimitedReader<Reader> sub{{{reader}, static_cast<::protocyte::usize>(len.value())}};")
        w.line("::protocyte::ReaderRef sub_reader{sub};")
        w.line("if (const auto st = value.merge_from(sub_reader); !st) { return st; }")
        w.line("if (const auto st = sub.finish(); !st) { return st; }")
        w.line(f"if (const auto st = {_member(item)}.push_back(::protocyte::move(value)); !st) {{ return st; }}")
        return
    w.line(f"{_element_type(item, options)} value{{}};")
    _emit_read_scalar(w, item, reader, "value", options, checked=checked)
    w.line(f"if (const auto st = {_member(item)}.push_back(value); !st) {{ return st; }}")


def _emit_read_bounded_bytes(w: CppWriter, item: FieldModel, reader: str) -> None:
    bound = _array_max_literal(item)
    w.line(f"auto len = ::protocyte::read_varint({reader});")
    w.line("if (!len) { return len.status(); }")
    if item.array_fixed:
        w.line(
            f"if (len.value() != {bound}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_argument, {reader}.position(), field_number); }}"
        )
        w.line(f"auto view = {_member(item)}.mutable_view();")
        w.line(f"if (const auto st = {reader}.read(view.data, view.size); !st) {{ return st; }}")
    else:
        w.line(
            f"if (len.value() > {bound}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::count_limit, {reader}.position(), field_number); }}"
        )
        w.line(f"if (const auto st = {_member(item)}.resize(static_cast<::protocyte::usize>(len.value())); !st) {{ return st; }}")
        w.line(f"if (const auto st = {reader}.read({_member(item)}.data(), {_member(item)}.size()); !st) {{ return st; }}")
    if _has_presence_flag(item):
        w.line(f"has_{item.cpp_name}_ = true;")


def _emit_read_single_value(w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions) -> None:
    if item.oneof_name and item.kind in {"string", "bytes"}:
        case_type = _oneof_case_type(item.oneof_name)
        case_member = _oneof_case_member(item.oneof_name)
        if item.kind == "bytes" and item.array_enabled:
            w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
            w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{}};")
            w.line(f"{case_member} = {case_type}::{item.cpp_name};")
            _emit_read_bounded_bytes(w, item, reader)
        else:
            w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
            w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{ctx_}};")
            w.line(f"{case_member} = {case_type}::{item.cpp_name};")
            helper = _length_delimited_read_helper(item, checked=True)
            w.line(f"if (const auto st = ::protocyte::{helper}<Config>(*ctx_, {reader}, wire_type, field_number, {_member(item)}); !st) {{ return st; }}")
        return
    if item.kind == "bytes" and item.array_enabled:
        _emit_read_bounded_bytes(w, item, reader)
        return
    if item.kind in {"string", "bytes"}:
        helper = _length_delimited_read_helper(item, checked=True)
        w.line(f"if (const auto st = ::protocyte::{helper}<Config>(*ctx_, {reader}, wire_type, field_number, {_member(item)}); !st) {{ return st; }}")
        if _has_presence_flag(item):
            w.line(f"has_{item.cpp_name}_ = true;")
        return
    if item.kind == "message":
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"auto ensured = ensure_{item.cpp_name}();")
        w.line("if (!ensured) { return ensured.status(); }")
        w.line(f"::protocyte::LimitedReader<Reader> sub{{{reader}, static_cast<::protocyte::usize>(len.value())}};")
        w.line("::protocyte::ReaderRef sub_reader{sub};")
        w.line("if (const auto st = ensured.value().get().merge_from(sub_reader); !st) { return st; }")
        w.line("if (const auto st = sub.finish(); !st) { return st; }")
        return
    if item.oneof_name:
        case_type = _oneof_case_type(item.oneof_name)
        case_member = _oneof_case_member(item.oneof_name)
        w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
        w.line(f"new (&{_member(item)}) {_storage_type(item, options)} {{{_default(item)}}};")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        _emit_read_scalar(w, item, reader, _member(item), options, checked=True)
        return
    _emit_read_scalar(w, item, reader, _member(item), options, checked=True)
    if _has_presence_flag(item):
        w.line(f"has_{item.cpp_name}_ = true;")


def _emit_read_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    key = item.map_key
    value = item.map_value
    w.line("if (wire_type != ::protocyte::WireType::LEN) { return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }")
    w.line("auto entry_len = ::protocyte::read_varint(reader);")
    w.line("if (!entry_len) { return entry_len.status(); }")
    w.line("::protocyte::LimitedReader<Reader> entry_reader{reader, static_cast<::protocyte::usize>(entry_len.value())};")
    w.line("enum struct EntryFieldNumber : ::protocyte::u32 {")
    w.push()
    w.line(f"{_field_number_name(key)} = 1u,")
    w.line(f"{_field_number_name(value)} = 2u,")
    w.pop()
    w.line("};")
    _emit_temp_decl(w, key, "key", options)
    _emit_temp_decl(w, value, "value", options)
    w.line("while (!entry_reader.eof()) {")
    w.push()
    w.line("auto entry_tag = ::protocyte::read_varint(entry_reader);")
    w.line("if (!entry_tag) { return entry_tag.status(); }")
    w.line("const auto entry_field = static_cast<::protocyte::u32>(entry_tag.value() >> 3u);")
    w.line("const auto entry_wire = static_cast<::protocyte::WireType>(entry_tag.value() & 0x7u);")
    w.line("switch (static_cast<EntryFieldNumber>(entry_field)) {")
    w.push()
    w.line(f"case EntryFieldNumber::{_field_number_name(key)}: {{")
    w.push()
    w.line(
        f"if (entry_wire != {_wire(key)}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(), {_field_number_u32(key, 'EntryFieldNumber')}); }}"
    )
    _emit_read_named_value(w, key, "entry_reader", "key", options)
    w.line("break;")
    w.pop()
    w.line("}")
    w.line(f"case EntryFieldNumber::{_field_number_name(value)}: {{")
    w.push()
    w.line(
        f"if (entry_wire != {_wire(value)}) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(), {_field_number_u32(value, 'EntryFieldNumber')}); }}"
    )
    _emit_read_named_value(w, value, "entry_reader", "value", options)
    w.line("break;")
    w.pop()
    w.line("}")
    w.line("default: {")
    w.push()
    w.line("if (const auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field); !st) { return st; }")
    w.line("break;")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.line("if (const auto finish = entry_reader.finish(); !finish) { return finish; }")
    w.line(f"if (const auto insert = {_member(item)}.insert_or_assign(::protocyte::move(key), ::protocyte::move(value)); !insert) {{ return insert; }}")


def _emit_temp_decl(w: CppWriter, item: FieldModel, name: str, options: GeneratorOptions) -> None:
    typ = _field_type(item, options)
    if item.kind in {"string", "bytes"}:
        w.line(f"{typ} {name}{{ctx_}};")
    elif item.kind == "message":
        w.line(f"{typ} {name}{{*ctx_}};")
    else:
        w.line(f"{typ} {name}{{}};")


def _emit_read_named_value(w: CppWriter, item: FieldModel, reader: str, target: str, options: GeneratorOptions) -> None:
    if item.kind in {"string", "bytes"}:
        helper = _length_delimited_read_helper(item, checked=False)
        w.line(f"if (const auto st = ::protocyte::{helper}<Config>(*ctx_, {reader}, {target}); !st) {{ return st; }}")
    elif item.kind == "message":
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"::protocyte::LimitedReader nested{{{reader}, static_cast<::protocyte::usize>(len.value())}};")
        w.line("::protocyte::ReaderRef nested_reader{nested};")
        w.line(f"if (const auto st = {target}.merge_from(nested_reader); !st) {{ return st; }}")
        w.line("if (const auto st = nested.finish(); !st) { return st; }")
    else:
        _emit_read_scalar(w, item, reader, target, options)


def _emit_read_scalar(
    w: CppWriter, item: FieldModel, reader: str, target: str, options: GeneratorOptions, *, checked: bool = False
) -> None:
    del options
    helper = _scalar_read_helper(item, checked=checked)
    args = f"{reader}, wire_type, field_number" if checked else reader
    w.line(f"auto decoded = ::protocyte::{helper}({args});")
    w.line("if (!decoded) { return decoded.status(); }")
    w.line(f"{target} = decoded.value();")


def _emit_serialize_statement(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    condition = _presence(item)
    if item.oneof_name:
        condition = f"{cpp_identifier(item.oneof_name)}_case_ == {item.oneof_name[0].upper() + item.oneof_name[1:]}Case::{item.cpp_name}"
    if item.repeated and item.kind != "map":
        if item.packed:
            w.line(f"if (!{_member(item)}.empty()) {{")
            w.push()
            _emit_write_packed_field(w, item, _member(item), options)
            w.pop()
            w.line("}")
            return
        w.line(f"for (::protocyte::usize i {{}}; i < {_member(item)}.size(); ++i) {{")
        w.push()
        _emit_write_field(w, item, f"{_member(item)}[i]", options)
        w.pop()
        w.line("}")
        return
    if item.kind == "map":
        _emit_write_map(w, item, options)
        return
    w.line(f"if ({condition}) {{")
    w.push()
    _emit_write_field(w, item, _member(item), options)
    w.pop()
    w.line("}")


def _emit_write_field(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    *,
    enum_type: str = "FieldNumber",
) -> None:
    del options
    if _is_scalar_field(item):
        helper = _scalar_write_helper(item, field=True)
        w.line(
            f"if (const auto st = ::protocyte::{helper}(writer, {_field_number_u32(item, enum_type)}, {value}); !st) {{ return st; }}"
        )
        return
    if item.kind in {"string", "bytes"}:
        helper = _length_delimited_write_helper(item)
        w.line(
            f"if (const auto st = ::protocyte::{helper}(writer, {_field_number_u32(item, enum_type)}, {value}.view()); !st) {{ return st; }}"
        )
        return
    w.line(
        f"if (const auto st = ::protocyte::write_tag(writer, {_field_number_u32(item, enum_type)}, {_wire(item)}); !st) {{ return st; }}"
    )
    if item.kind == "message":
        expr = f"{value}.value()" if value == _member(item) else value
        w.line(f"auto msg_size = {expr}.encoded_size();")
        w.line("if (!msg_size) { return msg_size.status(); }")
        w.line("if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(msg_size.value())); !st) { return st; }")
        w.line(f"if (const auto st = {expr}.serialize(writer); !st) {{ return st; }}")
    else:
        _emit_write_scalar(w, item, value)


def _emit_write_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    w.line(f"if (const auto st_map_{item.cpp_name} = {_member(item)}.for_each([&](const auto& key, const auto& value) noexcept {{")
    w.push()
    w.line("enum struct EntryFieldNumber : ::protocyte::u32 {")
    w.push()
    w.line(f"{_field_number_name(item.map_key)} = 1u,")
    w.line(f"{_field_number_name(item.map_value)} = 2u,")
    w.pop()
    w.line("};")
    w.line("::protocyte::usize entry_payload {};")
    _emit_add_size_status(
        w, _field_with_number(item.map_key, 1), "key", options, "entry_payload", enum_type="EntryFieldNumber"
    )
    _emit_add_size_status(
        w, _field_with_number(item.map_value, 2), "value", options, "entry_payload", enum_type="EntryFieldNumber"
    )
    w.line(
        f"if (const auto st = ::protocyte::write_tag(writer, {_field_number_u32(item)}, ::protocyte::WireType::LEN); !st) {{ return st; }}"
    )
    w.line("if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>(entry_payload)); !st) { return st; }")
    w.line("{")
    w.push()
    _emit_write_field(w, _field_with_number(item.map_key, 1), "key", options, enum_type="EntryFieldNumber")
    w.pop()
    w.line("}")
    w.line("{")
    w.push()
    _emit_write_field(w, _field_with_number(item.map_value, 2), "value", options, enum_type="EntryFieldNumber")
    w.pop()
    w.line("}")
    w.line("return ::protocyte::Status{};")
    w.pop()
    w.line(f"}}); !st_map_{item.cpp_name}) {{ return st_map_{item.cpp_name}; }}")


def _emit_write_packed_field(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    *,
    enum_type: str = "FieldNumber",
) -> None:
    del options
    packed_name = f"packed_size_{item.cpp_name}"
    w.line(f"::protocyte::usize {packed_name} {{}};")
    w.line(f"for (::protocyte::usize i {{}}; i < {value}.size(); ++i) {{")
    w.push()
    _emit_add_packed_size_status(w, item, f"{value}[i]", packed_name)
    w.pop()
    w.line("}")
    w.line(
        f"if (const auto st = ::protocyte::write_tag(writer, {_field_number_u32(item, enum_type)}, ::protocyte::WireType::LEN); !st) {{ return st; }}"
    )
    w.line(
        f"if (const auto st = ::protocyte::write_varint(writer, static_cast<::protocyte::u64>({packed_name})); !st) {{ return st; }}"
    )
    w.line(f"for (::protocyte::usize i {{}}; i < {value}.size(); ++i) {{")
    w.push()
    _emit_write_scalar(w, item, f"{value}[i]")
    w.pop()
    w.line("}")


def _emit_write_scalar(w: CppWriter, item: FieldModel, value: str) -> None:
    helper = _scalar_write_helper(item, field=False)
    w.line(f"if (const auto st = ::protocyte::{helper}(writer, {value}); !st) {{ return st; }}")


def _emit_size_statement(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    condition = _presence(item)
    if item.oneof_name:
        condition = f"{cpp_identifier(item.oneof_name)}_case_ == {item.oneof_name[0].upper() + item.oneof_name[1:]}Case::{item.cpp_name}"
    if item.repeated and item.kind != "map":
        if item.packed:
            packed_name = f"packed_size_{item.cpp_name}"
            w.line(f"if (!{_member(item)}.empty()) {{")
            w.push()
            w.line(f"::protocyte::usize {packed_name} {{}};")
            w.line(f"for (::protocyte::usize i {{}}; i < {_member(item)}.size(); ++i) {{")
            w.push()
            _emit_add_packed_size_result(w, item, f"{_member(item)}[i]", packed_name)
            w.pop()
            w.line("}")
            w.line(
                f"if (const auto st = ::protocyte::add_size(&total, ::protocyte::tag_size({_field_number_u32(item)}) + ::protocyte::varint_size({packed_name}) + {packed_name}); !st) {{ return ::protocyte::Result<::protocyte::usize>::err(st.error()); }}"
            )
            w.pop()
            w.line("}")
            return
        w.line(f"for (::protocyte::usize i {{}}; i < {_member(item)}.size(); ++i) {{")
        w.push()
        _emit_add_size(w, item, f"{_member(item)}[i]", options)
        w.pop()
        w.line("}")
        return
    if item.kind == "map":
        _emit_size_map(w, item, options)
        return
    w.line(f"if ({condition}) {{")
    w.push()
    _emit_add_size(w, item, _member(item), options)
    w.pop()
    w.line("}")


def _emit_size_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    w.line(
        f"if (const auto st_map_size_{item.cpp_name} = {_member(item)}.for_each([&](const auto& key, const auto& value) noexcept {{"
    )
    w.push()
    w.line("enum struct EntryFieldNumber : ::protocyte::u32 {")
    w.push()
    w.line(f"{_field_number_name(item.map_key)} = 1u,")
    w.line(f"{_field_number_name(item.map_value)} = 2u,")
    w.pop()
    w.line("};")
    w.line("::protocyte::usize entry_payload {};")
    _emit_add_size_status(
        w, _field_with_number(item.map_key, 1), "key", options, "entry_payload", enum_type="EntryFieldNumber"
    )
    _emit_add_size_status(
        w, _field_with_number(item.map_value, 2), "value", options, "entry_payload", enum_type="EntryFieldNumber"
    )
    w.line(
        f"return ::protocyte::add_size(&total, ::protocyte::tag_size({_field_number_u32(item)}) + ::protocyte::varint_size(entry_payload) + entry_payload);"
    )
    w.pop()
    w.line(f"}}); !st_map_size_{item.cpp_name}) {{ return ::protocyte::Result<::protocyte::usize>::err(st_map_size_{item.cpp_name}.error()); }}")


def _emit_add_size(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    *,
    enum_type: str = "FieldNumber",
) -> None:
    del options
    if item.kind in {"string", "bytes"}:
        value_size = (
            f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + ::protocyte::varint_size({value}.size()) + {value}.size()"
        )
    elif item.kind == "message":
        expr = f"{value}.value()" if value == _member(item) else value
        w.line(f"auto nested_size = {expr}.encoded_size();")
        w.line("if (!nested_size) { return ::protocyte::Result<::protocyte::usize>::err(nested_size.error()); }")
        value_size = (
            f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + ::protocyte::varint_size(nested_size.value()) + nested_size.value()"
        )
    else:
        value_size = f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + {_scalar_size(item, value)}"
    w.line(f"if (const auto st = ::protocyte::add_size(&total, {value_size}); !st) {{ return ::protocyte::Result<::protocyte::usize>::err(st.error()); }}")


def _emit_add_size_status(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    total_name: str,
    *,
    enum_type: str = "FieldNumber",
) -> None:
    w.line("{")
    w.push()
    if item.kind in {"string", "bytes"}:
        value_size = (
            f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + ::protocyte::varint_size({value}.size()) + {value}.size()"
        )
    elif item.kind == "message":
        w.line(f"auto nested_size = {value}.encoded_size();")
        w.line("if (!nested_size) { return nested_size.status(); }")
        value_size = (
            f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + ::protocyte::varint_size(nested_size.value()) + nested_size.value()"
        )
    else:
        value_size = f"::protocyte::tag_size({_field_number_u32(item, enum_type)}) + {_scalar_size(item, value)}"
    w.line(f"if (const auto st_size = ::protocyte::add_size(&{total_name}, {value_size}); !st_size) {{ return st_size; }}")
    w.pop()
    w.line("}")


def _emit_add_packed_size_status(w: CppWriter, item: FieldModel, value: str, total_name: str) -> None:
    w.line("{")
    w.push()
    w.line(
        f"if (const auto st_size = ::protocyte::add_size(&{total_name}, {_scalar_size(item, value)}); !st_size) {{ return st_size; }}"
    )
    w.pop()
    w.line("}")


def _emit_add_packed_size_result(w: CppWriter, item: FieldModel, value: str, total_name: str) -> None:
    w.line("{")
    w.push()
    w.line(
        f"if (const auto st_size = ::protocyte::add_size(&{total_name}, {_scalar_size(item, value)}); !st_size) {{ return ::protocyte::Result<::protocyte::usize>::err(st_size.error()); }}"
    )
    w.pop()
    w.line("}")


def _emit_member(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.repeated and item.kind != "map":
        w.line(f"{_storage_type(item, options)} {_member(item)};")
        return
    if item.kind == "map":
        assert item.map_key is not None and item.map_value is not None
        w.line(f"typename Config::template Map<{_field_type(item.map_key, options)}, {_field_type(item.map_value, options)}> {_member(item)};")
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        if item.recursive_box:
            w.line(f"typename Config::template Box<{typ}> {_member(item)};")
        else:
            w.line(f"typename Config::template Optional<{typ}> {_member(item)};")
        return
    if item.kind == "bytes" and item.array_enabled:
        w.line(f"{_storage_type(item, options)} {_member(item)};")
        if _has_presence_flag(item):
            w.line(f"bool has_{item.cpp_name}_ {{}};")
        return
    if item.kind in {"string", "bytes"}:
        w.line(f"{_field_type(item, options)} {_member(item)};")
        if _has_presence_flag(item):
            w.line(f"bool has_{item.cpp_name}_ {{}};")
        return
    w.line(f"{_field_type(item, options)} {_member(item)}{{}};")
    if _has_presence_flag(item):
        w.line(f"bool has_{item.cpp_name}_ {{}};")


def _emit_clear_statement(w: CppWriter, item: FieldModel) -> None:
    if item.kind == "message":
        w.line(f"{_member(item)}.reset();")
    elif item.kind in {"string", "bytes"}:
        w.line(f"{_member(item)}.clear();")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
    else:
        w.line(f"{_member(item)} = {{}};")


def _emit_oneof_member(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    w.line(f"{_storage_type(item, options)} {_oneof_member_name(item)};")


def _emit_destroy_oneof_member(w: CppWriter, item: FieldModel) -> None:
    if item.kind in {"string", "bytes", "message"}:
        w.line(f"destroy_at_(&{_member(item)});")


def _emit_oneof_storage(w: CppWriter, oneof: OneofModel, options: GeneratorOptions) -> None:
    storage_type = _oneof_storage_type(oneof)
    w.line(f"union {storage_type} {{")
    w.push()
    w.line(f"{storage_type}() noexcept {{}}")
    w.line(f"~{storage_type}() noexcept {{}}")
    for item in oneof.fields:
        _emit_oneof_member(w, item, options)
    w.pop()
    w.line(f"}} {_oneof_storage_member(oneof.name)};")


def _storage_type(item: FieldModel, options: GeneratorOptions) -> str:
    if item.repeated and item.kind != "map":
        if item.repeated_array and item.array_max is not None:
            return f"::protocyte::Array<{_element_type(item, options)}, {_array_max_literal(item)}>"
        return f"typename Config::template Vector<{_element_type(item, options)}>"
    if item.kind == "map":
        assert item.map_key is not None and item.map_value is not None
        return f"typename Config::template Map<{_field_type(item.map_key, options)}, {_field_type(item.map_value, options)}>"
    if item.kind == "message":
        typ = _field_type(item, options)
        if item.recursive_box:
            return f"typename Config::template Box<{typ}>"
        return f"typename Config::template Optional<{typ}>"
    if item.fixed_bytes and item.array_max is not None:
        return f"::protocyte::FixedByteArray<{_array_max_literal(item)}>"
    if item.kind == "bytes" and item.array_enabled and item.array_max is not None:
        return f"::protocyte::ByteArray<{_array_max_literal(item)}>"
    return _field_type(item, options)


def _has_presence_flag(item: FieldModel) -> bool:
    return item.proto3_optional


def _field_with_number(item: FieldModel, number: int) -> FieldModel:
    return FieldModel(
        name=item.name,
        cpp_name=item.cpp_name,
        number=number,
        proto_type=item.proto_type,
        label=item.label,
        file_name=item.file_name,
        repeated=False,
        proto3_optional=False,
        oneof_index=None,
        oneof_name=None,
        packed=False,
        deprecated=item.deprecated,
        type_name=item.type_name,
        kind=item.kind,
        cpp_type=item.cpp_type,
        message_type=item.message_type,
        enum_type=item.enum_type,
        map_key=item.map_key,
        map_value=item.map_value,
        recursive_box=item.recursive_box,
        array_max=item.array_max,
        array_expr=item.array_expr,
        array_cpp_max=item.array_cpp_max,
        array_fixed=item.array_fixed,
    )


def _field_type(item: FieldModel, options: GeneratorOptions) -> str:
    if item.kind == "message":
        assert item.message_type is not None
        return f"{_qualified_name(item.message_type.package, item.message_type.cpp_name, options)}<Config>"
    if item.kind == "string":
        return "typename Config::String"
    if item.kind == "bytes":
        return "typename Config::Bytes"
    if item.kind == "enum":
        return "::protocyte::i32"
    return _runtime_scalar_type(SCALAR_CPP_TYPES[item.proto_type])


def _enum_type(enum: EnumModel | None, options: GeneratorOptions) -> str:
    if enum is None:
        return "::protocyte::i32"
    return _qualified_name(enum.package, enum.cpp_name, options)


def _element_type(item: FieldModel, options: GeneratorOptions) -> str:
    return _field_type(item, options)


def _default(item: FieldModel) -> str:
    if item.kind == "enum":
        return "0"
    return SCALAR_DEFAULTS.get(item.proto_type, "{}")


def _field_number_name(item: FieldModel) -> str:
    return item.cpp_name


def _field_number_u32(item: FieldModel, enum_type: str = "FieldNumber") -> str:
    return f"static_cast<::protocyte::u32>({enum_type}::{_field_number_name(item)})"


def _member(item: FieldModel) -> str:
    if item.oneof_name is not None:
        return f"{_oneof_storage_member(item.oneof_name)}.{_oneof_member_name(item)}"
    return f"{item.cpp_name}_"


def _oneof_case_type(oneof_name: str) -> str:
    return f"{oneof_name[0].upper() + oneof_name[1:]}Case"


def _oneof_case_member(oneof_name: str) -> str:
    return f"{cpp_identifier(oneof_name)}_case_"


def _oneof_storage_type(oneof: OneofModel) -> str:
    return f"{oneof.cpp_name}Storage"


def _oneof_storage_member(oneof_name: str) -> str:
    return cpp_identifier(oneof_name)


def _oneof_member_name(item: FieldModel) -> str:
    return item.cpp_name


def _array_max_literal(item: FieldModel) -> str:
    if item.array_cpp_max:
        return item.array_cpp_max
    assert item.array_max is not None
    return f"{item.array_max}u"


def _wire(item: FieldModel) -> str:
    if item.kind in {"string", "bytes", "message", "map"}:
        return "::protocyte::WireType::LEN"
    if item.proto_type in {
        FieldDescriptorProto.TYPE_DOUBLE,
        FieldDescriptorProto.TYPE_FIXED64,
        FieldDescriptorProto.TYPE_SFIXED64,
    }:
        return "::protocyte::WireType::I64"
    if item.proto_type in {
        FieldDescriptorProto.TYPE_FLOAT,
        FieldDescriptorProto.TYPE_FIXED32,
        FieldDescriptorProto.TYPE_SFIXED32,
    }:
        return "::protocyte::WireType::I32"
    return "::protocyte::WireType::VARINT"


def _presence(item: FieldModel) -> str:
    if item.fixed_bytes:
        return f"{_member(item)}.has_value()"
    if _has_presence_flag(item):
        return f"has_{item.cpp_name}_"
    if item.kind == "message":
        return f"{_member(item)}.has_value()"
    if item.kind in {"string", "bytes"}:
        return f"!{_member(item)}.empty()"
    if item.kind == "enum":
        return f"{_member(item)} != 0"
    if item.proto_type == FieldDescriptorProto.TYPE_BOOL:
        return _member(item)
    if item.proto_type == FieldDescriptorProto.TYPE_FLOAT:
        return f"::std::bit_cast<::protocyte::u32>({_member(item)}) != 0u"
    if item.proto_type == FieldDescriptorProto.TYPE_DOUBLE:
        return f"::std::bit_cast<::protocyte::u64>({_member(item)}) != 0u"
    return f"{_member(item)} != {_default(item)}"


def _scalar_size(item: FieldModel, value: str) -> str:
    if item.proto_type in {
        FieldDescriptorProto.TYPE_DOUBLE,
        FieldDescriptorProto.TYPE_FIXED64,
        FieldDescriptorProto.TYPE_SFIXED64,
    }:
        return "8u"
    if item.proto_type in {
        FieldDescriptorProto.TYPE_FLOAT,
        FieldDescriptorProto.TYPE_FIXED32,
        FieldDescriptorProto.TYPE_SFIXED32,
    }:
        return "4u"
    if item.proto_type == FieldDescriptorProto.TYPE_SINT32:
        return f"::protocyte::varint_size(::protocyte::encode_zigzag32({value}))"
    if item.proto_type == FieldDescriptorProto.TYPE_SINT64:
        return f"::protocyte::varint_size(::protocyte::encode_zigzag64({value}))"
    return f"::protocyte::varint_size(static_cast<::protocyte::u64>({value}))"


def _is_scalar_field(item: FieldModel) -> bool:
    return item.kind not in {"string", "bytes", "message", "map"}


def _uses_runtime_len_field_helper(item: FieldModel) -> bool:
    return item.kind in {"string", "bytes"} and not (item.kind == "bytes" and item.array_enabled)


def _length_delimited_read_helper(item: FieldModel, *, checked: bool) -> str:
    base = "read_string" if item.kind == "string" else "read_bytes"
    return f"{base}_field" if checked else base


def _length_delimited_write_helper(item: FieldModel) -> str:
    return "write_string_field" if item.kind == "string" else "write_bytes_field"


def _scalar_read_helper(item: FieldModel, *, checked: bool) -> str:
    helper = _SCALAR_READ_HELPERS[item.proto_type]
    return f"{helper}_field" if checked else helper


def _scalar_write_helper(item: FieldModel, *, field: bool) -> str:
    helper = _SCALAR_WRITE_HELPERS[item.proto_type]
    return f"{helper}_field" if field else helper


def _runtime_scalar_type(cpp_type: str) -> str:
    return _RUNTIME_SCALAR_TYPES.get(cpp_type, cpp_type)


def _file_uses_string_view(file_model: FileModel) -> bool:
    if any(constant.kind == CONSTANT_KIND_STRING for constant in file_model.constants):
        return True
    for message in _walk_messages(file_model.messages):
        if any(constant.kind == CONSTANT_KIND_STRING for constant in message.constants):
            return True
    return False


def _ordered_messages(file_model: FileModel) -> list[MessageModel]:
    all_messages = [item for item in _walk_messages(file_model.messages) if not item.is_map_entry]
    by_name = {item.full_name: item for item in all_messages}
    ordered: list[MessageModel] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(message: MessageModel) -> None:
        if message.full_name in visited or message.full_name in visiting:
            return
        visiting.add(message.full_name)
        for item in message.fields:
            if item.message_type is not None and item.message_type.full_name in by_name and not item.recursive_box:
                visit(item.message_type)
            if item.map_value is not None and item.map_value.message_type is not None:
                target = item.map_value.message_type
                if target.full_name in by_name:
                    visit(target)
        visiting.remove(message.full_name)
        visited.add(message.full_name)
        ordered.append(message)

    for item in all_messages:
        visit(item)
    return ordered


def _walk_messages(messages: list[MessageModel]):
    for message in messages:
        if not message.is_map_entry:
            yield message
        yield from _walk_messages(message.nested_messages)


def _header_name(proto_name: str) -> str:
    return proto_name.removesuffix(".proto") + ".protocyte.hpp"


def _source_name(proto_name: str) -> str:
    return proto_name.removesuffix(".proto") + ".protocyte.cpp"


def _include_path(proto_name: str, options: GeneratorOptions) -> str:
    path = _header_name(proto_name)
    return f"{options.include_prefix}/{path}" if options.include_prefix else path


def _include_guard(proto_name: str) -> str:
    return "PROTOCYTE_GENERATED_" + "".join(ch if ch.isalnum() else "_" for ch in proto_name.upper()) + "_HPP"


def _namespace_parts(file_model: FileModel, options: GeneratorOptions) -> list[str]:
    parts: list[str] = []
    if options.namespace_prefix:
        parts.extend(part for part in options.namespace_prefix.split("::") if part)
    if file_model.package:
        parts.extend(cpp_identifier(part) for part in file_model.package.split("."))
    return parts


def _qualified_name(package: str, cpp_name: str, options: GeneratorOptions) -> str:
    parts: list[str] = []
    if options.namespace_prefix:
        parts.extend(part for part in options.namespace_prefix.split("::") if part)
    if package:
        parts.extend(cpp_identifier(part) for part in package.split("."))
    parts.append(cpp_name)
    return "::" + "::".join(parts)


def _open_namespace(w: CppWriter, parts: list[str]) -> None:
    if parts:
        w.line(f"namespace {'::'.join(parts)} {{")
        w.line()


def _close_namespace(w: CppWriter, parts: list[str]) -> None:
    if parts:
        w.line()
        w.line(f"}}  // namespace {'::'.join(parts)}")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _cpp_bool(value: bool) -> str:
    return "true" if value else "false"
