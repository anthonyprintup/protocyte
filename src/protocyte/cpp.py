from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess

from protocyte.errors import ProtocyteError
from protocyte.model import (
    SCALAR_CPP_TYPES,
    SCALAR_DEFAULTS,
    DescriptorModel,
    EnumModel,
    FieldDescriptorProto,
    FieldModel,
    FileModel,
    MessageModel,
    cpp_identifier,
)
from protocyte.parameters import GeneratorOptions
from protocyte.runtime import runtime_files


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
    w.line(f"#ifndef {guard}")
    w.line(f"#define {guard}")
    w.line()
    w.line("#include <stddef.h>")
    w.line("#include <stdint.h>")
    w.line(f"#include <{options.runtime_prefix}/runtime.hpp>")
    for dependency in sorted(file_model.dependencies):
        w.line(f'#include "{_include_path(dependency, options)}"')
    w.line()
    _open_namespace(w, _namespace_parts(file_model, options))
    _emit_enums(w, file_model)
    for message in _ordered_messages(file_model):
        w.line("template <class Config = ::protocyte::DefaultConfig>")
        w.line(f"class {message.cpp_name};")
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
    w.line("struct FieldInfo { const char* name; uint32_t number; const char* kind; bool repeated; bool optional; bool packed; };")
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
        w.line(f"enum class {enum.cpp_name} : int32_t {{")
        w.push()
        for value in enum.values:
            w.line(f"{value.cpp_name} = {value.number},")
        w.pop()
        w.line("};")
        w.line()


def _emit_message(w: CppWriter, message: MessageModel, options: GeneratorOptions) -> None:
    w.line("template <class Config>")
    w.line(f"class {message.cpp_name} {{")
    w.push()
    w.line("public:")
    w.push()
    w.line("using Context = typename Config::Context;")
    for enum in message.nested_enums:
        w.line(f"using {enum.name} = {enum.cpp_name};")
    for nested in message.nested_messages:
        if not nested.is_map_entry:
            w.line(f"template <class NestedConfig = Config>")
            w.line(f"using {nested.name} = {nested.cpp_name}<NestedConfig>;")
    if message.nested_enums or message.nested_messages:
        w.line()
    _emit_oneof_case_enums(w, message)
    w.line(f"explicit {message.cpp_name}(Context& ctx) noexcept")
    _emit_constructor_initializers(w, message)
    w.line("{}")
    w.line()
    w.line(f"static ::protocyte::Result<{message.cpp_name}> create(Context& ctx) noexcept {{")
    w.push()
    w.line(f"return ::protocyte::Result<{message.cpp_name}>::ok({message.cpp_name}(ctx));")
    w.pop()
    w.line("}")
    w.line(f"{message.cpp_name}({message.cpp_name}&&) noexcept = default;")
    w.line(f"{message.cpp_name}& operator=({message.cpp_name}&&) noexcept = default;")
    w.line(f"{message.cpp_name}(const {message.cpp_name}&) = delete;")
    w.line(f"{message.cpp_name}& operator=(const {message.cpp_name}&) = delete;")
    w.line()
    _emit_clone_api(w, message)
    for oneof in message.oneofs:
        lower = cpp_identifier(oneof.name)
        w.line(f"{oneof.cpp_name}Case {lower}_case() const noexcept {{ return {lower}_case_; }}")
        w.line(f"void clear_{lower}() noexcept {{")
        w.push()
        for item in oneof.fields:
            _emit_clear_statement(w, item)
        w.line(f"{lower}_case_ = {oneof.cpp_name}Case::none;")
        w.pop()
        w.line("}")
        w.line()
    for item in message.fields:
        _emit_accessors(w, item, options)
        w.line()
    _emit_wire_api(w, message, options)
    w.pop()
    w.line("private:")
    w.push()
    w.line("Context* ctx_;")
    for oneof in message.oneofs:
        w.line(f"{oneof.cpp_name}Case {cpp_identifier(oneof.name)}_case_ = {oneof.cpp_name}Case::none;")
    for item in message.fields:
        _emit_member(w, item, options)
    w.pop()
    w.pop()
    w.line("};")


def _emit_oneof_case_enums(w: CppWriter, message: MessageModel) -> None:
    for oneof in message.oneofs:
        w.line(f"enum class {oneof.cpp_name}Case : uint32_t {{")
        w.push()
        w.line("none = 0u,")
        for item in oneof.fields:
            w.line(f"{item.cpp_name} = {item.number}u,")
        w.pop()
        w.line("};")
        w.line()


def _emit_constructor_initializers(w: CppWriter, message: MessageModel) -> None:
    initializers = ["ctx_(&ctx)"]
    for item in message.fields:
        member = _member(item)
        if item.kind in {"string", "bytes", "map"} or (item.repeated and item.kind != "map"):
            initializers.append(f"{member}(&ctx)")
        elif item.kind == "message" and item.recursive_box:
            initializers.append(f"{member}(&ctx)")
    w.push()
    for index, initializer in enumerate(initializers):
        prefix = ": " if index == 0 else ", "
        w.line(f"{prefix}{initializer}")
    w.pop()


def _emit_clone_api(w: CppWriter, message: MessageModel) -> None:
    w.line(f"::protocyte::Status copy_from(const {message.cpp_name}& other) noexcept {{")
    w.push()
    w.line("(void)other;")
    for item in message.fields:
        if item.oneof_name is not None:
            continue
        if item.kind in {"string", "bytes"}:
            w.line(f"auto st_{item.cpp_name} = set_{item.cpp_name}(other.{item.cpp_name}());")
            w.line(f"if (!st_{item.cpp_name}) {{ return st_{item.cpp_name}; }}")
        elif item.kind == "message":
            w.line(f"if (other.has_{item.cpp_name}()) {{")
            w.push()
            w.line(f"auto ensured = ensure_{item.cpp_name}();")
            w.line("if (!ensured) { return ensured.status(); }")
            w.line(f"auto st = ensured.value().get().copy_from(*other.{item.cpp_name}());")
            w.line("if (!st) { return st; }")
            w.pop()
            w.line(f"}} else {{ clear_{item.cpp_name}(); }}")
        elif item.kind == "enum":
            w.line(f"auto st_{item.cpp_name} = set_{item.cpp_name}_raw(other.{item.cpp_name}_raw());")
            w.line(f"if (!st_{item.cpp_name}) {{ return st_{item.cpp_name}; }}")
        elif not item.repeated and item.kind != "map":
            w.line(f"auto st_{item.cpp_name} = set_{item.cpp_name}(other.{item.cpp_name}());")
            w.line(f"if (!st_{item.cpp_name}) {{ return st_{item.cpp_name}; }}")
    if any(item.repeated or item.kind == "map" or item.oneof_name is not None for item in message.fields):
        w.line("// Full deep copy for repeated, map, and oneof storage is reserved for the next conformance pass.")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")
    w.line()
    w.line(f"::protocyte::Result<{message.cpp_name}> clone() const noexcept {{")
    w.push()
    w.line(f"auto out = {message.cpp_name}::create(*ctx_);")
    w.line("if (!out) { return out; }")
    w.line("auto st = out.value().copy_from(*this);")
    w.line(f"if (!st) {{ return ::protocyte::Result<{message.cpp_name}>::err(st.error()); }}")
    w.line("return out;")
    w.pop()
    w.line("}")
    w.line()


def _emit_accessors(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.oneof_name is not None:
        _emit_oneof_accessors(w, item, options)
        return
    if item.repeated and item.kind != "map":
        typ = f"typename Config::template Vector<{_element_type(item, options)}>"
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
            w.line(f"auto st = {_member(item)}.emplace(*ctx_);")
            w.line(f"if (!st) {{ return ::protocyte::Result<::protocyte::Ref<{typ}>>::err(st.error()); }}")
            w.pop()
            w.line("}")
            w.line(f"return ::protocyte::Result<::protocyte::Ref<{typ}>>::ok(::protocyte::Ref<{typ}>({_member(item)}.value()));")
        w.pop()
        w.line("}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)}.reset(); }}")
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
        w.line(f"::protocyte::Status set_{item.cpp_name}(::protocyte::ByteView value) noexcept {{")
        w.push()
        w.line(f"{typ} temp(ctx_);")
        w.line("auto st = temp.assign(value);")
        w.line("if (!st) { return st; }")
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
        w.line(f"int32_t {item.cpp_name}_raw() const noexcept {{ return {_member(item)}; }}")
        w.line(f"{enum_typ} {item.cpp_name}() const noexcept {{ return static_cast<{enum_typ}>({_member(item)}); }}")
        if item.proto3_optional:
            w.line(f"bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}")
        w.line(f"::protocyte::Status set_{item.cpp_name}_raw(int32_t value) noexcept {{ {_member(item)} = value;")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        w.line("return ::protocyte::Status::ok(); }")
        w.line(f"::protocyte::Status set_{item.cpp_name}({enum_typ} value) noexcept {{ return set_{item.cpp_name}_raw(static_cast<int32_t>(value)); }}")
        w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)} = 0;")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = false;")
        w.line("}")
        return
    typ = _field_type(item, options)
    w.line(f"{typ} {item.cpp_name}() const noexcept {{ return {_member(item)}; }}")
    if item.proto3_optional:
        w.line(f"bool has_{item.cpp_name}() const noexcept {{ return has_{item.cpp_name}_; }}")
    w.line(f"::protocyte::Status set_{item.cpp_name}({typ} value) noexcept {{ {_member(item)} = value;")
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = true;")
    w.line("return ::protocyte::Status::ok(); }")
    w.line(f"void clear_{item.cpp_name}() noexcept {{ {_member(item)} = {_default(item)};")
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = false;")
    w.line("}")


def _emit_oneof_accessors(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.oneof_name is not None
    case_type = f"{item.oneof_name[0].upper() + item.oneof_name[1:]}Case"
    case_member = f"{cpp_identifier(item.oneof_name)}_case_"
    typ = _field_type(item, options)
    w.line(f"bool has_{item.cpp_name}() const noexcept {{ return {case_member} == {case_type}::{item.cpp_name}; }}")
    if item.kind in {"string", "bytes"}:
        w.line(f"::protocyte::ByteView {item.cpp_name}() const noexcept {{ return {_member(item)}.view(); }}")
        w.line(f"::protocyte::Status set_{item.cpp_name}(::protocyte::ByteView value) noexcept {{")
        w.push()
        w.line(f"{typ} temp(ctx_);")
        w.line("auto st = temp.assign(value);")
        w.line("if (!st) { return st; }")
        w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
        w.line(f"{_member(item)} = ::protocyte::move(temp);")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        return
    if item.kind == "message":
        w.line(f"const {typ}* {item.cpp_name}() const noexcept {{ return has_{item.cpp_name}() && {_member(item)}.has_value() ? &{_member(item)}.value() : nullptr; }}")
        w.line(f"::protocyte::Result<::protocyte::Ref<{typ}>> ensure_{item.cpp_name}() noexcept {{")
        w.push()
        w.line(f"if (!has_{item.cpp_name}()) {{ clear_{cpp_identifier(item.oneof_name)}(); }}")
        if item.recursive_box:
            w.line(f"auto ensured = {_member(item)}.ensure();")
            w.line("if (!ensured) { return ensured; }")
        else:
            w.line(f"if (!{_member(item)}.has_value()) {{")
            w.push()
            w.line(f"auto st = {_member(item)}.emplace(*ctx_);")
            w.line(f"if (!st) {{ return ::protocyte::Result<::protocyte::Ref<{typ}>>::err(st.error()); }}")
            w.pop()
            w.line("}")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line(f"return ::protocyte::Result<::protocyte::Ref<{typ}>>::ok(::protocyte::Ref<{typ}>({_member(item)}.value()));")
        w.pop()
        w.line("}")
        return
    if item.kind == "enum":
        enum_typ = _enum_type(item.enum_type, options)
        w.line(f"int32_t {item.cpp_name}_raw() const noexcept {{ return {_member(item)}; }}")
        w.line(f"{enum_typ} {item.cpp_name}() const noexcept {{ return static_cast<{enum_typ}>({_member(item)}); }}")
        w.line(f"::protocyte::Status set_{item.cpp_name}_raw(int32_t value) noexcept {{")
        w.push()
        w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
        w.line(f"{_member(item)} = value;")
        w.line(f"{case_member} = {case_type}::{item.cpp_name};")
        w.line("return ::protocyte::Status::ok();")
        w.pop()
        w.line("}")
        w.line(f"::protocyte::Status set_{item.cpp_name}({enum_typ} value) noexcept {{ return set_{item.cpp_name}_raw(static_cast<int32_t>(value)); }}")
        return
    w.line(f"{typ} {item.cpp_name}() const noexcept {{ return {_member(item)}; }}")
    w.line(f"::protocyte::Status set_{item.cpp_name}({typ} value) noexcept {{")
    w.push()
    w.line(f"clear_{cpp_identifier(item.oneof_name)}();")
    w.line(f"{_member(item)} = value;")
    w.line(f"{case_member} = {case_type}::{item.cpp_name};")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")


def _emit_wire_api(w: CppWriter, message: MessageModel, options: GeneratorOptions) -> None:
    w.line("template <class Reader>")
    w.line(f"static ::protocyte::Result<{message.cpp_name}> parse(Context& ctx, Reader& reader) noexcept {{")
    w.push()
    w.line(f"auto out = {message.cpp_name}::create(ctx);")
    w.line("if (!out) { return out; }")
    w.line("auto st = out.value().merge_from(reader);")
    w.line(f"if (!st) {{ return ::protocyte::Result<{message.cpp_name}>::err(st.error()); }}")
    w.line("return out;")
    w.pop()
    w.line("}")
    w.line()
    w.line("template <class Reader>")
    w.line("::protocyte::Status merge_from(Reader& reader) noexcept {")
    w.push()
    w.line("while (!reader.eof()) {")
    w.push()
    w.line("auto tag = ::protocyte::read_varint(reader);")
    w.line("if (!tag) { return tag.status(); }")
    w.line("uint32_t field_number = static_cast<uint32_t>(tag.value() >> 3u);")
    w.line("uint32_t wire_type = static_cast<uint32_t>(tag.value() & 0x7u);")
    w.line("switch (field_number) {")
    w.push()
    for item in sorted(message.fields, key=lambda f: f.number):
        w.line(f"case {item.number}u:")
        w.push()
        _emit_parse_case(w, item, options)
        w.line("break;")
        w.pop()
    w.line("default: {")
    w.push()
    w.line("auto st = ::protocyte::skip_field(reader, wire_type, field_number);")
    w.line("if (!st) { return st; }")
    w.line("break;")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")
    w.line()
    w.line("template <class Writer>")
    w.line("::protocyte::Status serialize(Writer& writer) const noexcept {")
    w.push()
    for item in sorted(message.fields, key=lambda f: f.number):
        _emit_serialize_statement(w, item, options)
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("}")
    w.line()
    w.line("::protocyte::Result<size_t> encoded_size() const noexcept {")
    w.push()
    w.line("size_t total = 0u;")
    for item in sorted(message.fields, key=lambda f: f.number):
        _emit_size_statement(w, item, options)
    w.line("return ::protocyte::Result<size_t>::ok(total);")
    w.pop()
    w.line("}")


def _emit_parse_case(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.repeated and item.kind != "map":
        if item.packable:
            w.line("if (wire_type == 2u) {")
            w.push()
            w.line("auto len = ::protocyte::read_varint(reader);")
            w.line("if (!len) { return len.status(); }")
            w.line("::protocyte::LimitedReader<Reader> packed(reader, static_cast<size_t>(len.value()));")
            w.line("while (!packed.eof()) {")
            w.push()
            _emit_read_repeated_value(w, item, "packed", options)
            w.pop()
            w.line("}")
            w.line("return packed.finish();")
            w.pop()
            w.line("}")
        w.line(f"if (wire_type != {_wire(item)}u) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }}")
        _emit_read_repeated_value(w, item, "reader", options)
        return
    if item.kind == "map":
        _emit_read_map(w, item, options)
        return
    w.line(f"if (wire_type != {_wire(item)}u) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }}")
    _emit_read_single_value(w, item, "reader", options)


def _emit_read_repeated_value(w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions) -> None:
    if item.kind in {"string", "bytes"}:
        typ = _field_type(item, options)
        helper = "read_string" if item.kind == "string" else "read_bytes"
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"{typ} value(ctx_);")
        w.line(f"auto st = ::protocyte::{helper}<Config>(*ctx_, {reader}, static_cast<size_t>(len.value()), value);")
        w.line("if (!st) { return st; }")
        w.line(f"st = {_member(item)}.push_back(::protocyte::move(value));")
        w.line("if (!st) { return st; }")
        return
    if item.kind == "message":
        typ = _field_type(item, options)
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"{typ} value(*ctx_);")
        w.line(f"::protocyte::LimitedReader<Reader> sub({reader}, static_cast<size_t>(len.value()));")
        w.line("auto st = value.merge_from(sub);")
        w.line("if (!st) { return st; }")
        w.line("st = sub.finish();")
        w.line("if (!st) { return st; }")
        w.line(f"st = {_member(item)}.push_back(::protocyte::move(value));")
        w.line("if (!st) { return st; }")
        return
    w.line(f"{_element_type(item, options)} value = {_default(item)};")
    _emit_read_scalar(w, item, reader, "value", options)
    w.line(f"auto st = {_member(item)}.push_back(value);")
    w.line("if (!st) { return st; }")


def _emit_read_single_value(w: CppWriter, item: FieldModel, reader: str, options: GeneratorOptions) -> None:
    if item.kind in {"string", "bytes"}:
        helper = "read_string" if item.kind == "string" else "read_bytes"
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"auto st = ::protocyte::{helper}<Config>(*ctx_, {reader}, static_cast<size_t>(len.value()), {_member(item)});")
        w.line("if (!st) { return st; }")
        if item.proto3_optional:
            w.line(f"has_{item.cpp_name}_ = true;")
        if item.oneof_name:
            w.line(f"{cpp_identifier(item.oneof_name)}_case_ = {item.oneof_name[0].upper() + item.oneof_name[1:]}Case::{item.cpp_name};")
        return
    if item.kind == "message":
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"auto ensured = ensure_{item.cpp_name}();")
        w.line("if (!ensured) { return ensured.status(); }")
        w.line(f"::protocyte::LimitedReader<Reader> sub({reader}, static_cast<size_t>(len.value()));")
        w.line("auto st = ensured.value().get().merge_from(sub);")
        w.line("if (!st) { return st; }")
        w.line("return sub.finish();")
        return
    _emit_read_scalar(w, item, reader, _member(item), options)
    if item.proto3_optional:
        w.line(f"has_{item.cpp_name}_ = true;")
    if item.oneof_name:
        w.line(f"{cpp_identifier(item.oneof_name)}_case_ = {item.oneof_name[0].upper() + item.oneof_name[1:]}Case::{item.cpp_name};")


def _emit_read_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    key = item.map_key
    value = item.map_value
    w.line("if (wire_type != 2u) { return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, reader.position(), field_number); }")
    w.line("auto entry_len = ::protocyte::read_varint(reader);")
    w.line("if (!entry_len) { return entry_len.status(); }")
    w.line("::protocyte::LimitedReader<Reader> entry_reader(reader, static_cast<size_t>(entry_len.value()));")
    _emit_temp_decl(w, key, "key", options)
    _emit_temp_decl(w, value, "value", options)
    w.line("while (!entry_reader.eof()) {")
    w.push()
    w.line("auto entry_tag = ::protocyte::read_varint(entry_reader);")
    w.line("if (!entry_tag) { return entry_tag.status(); }")
    w.line("uint32_t entry_field = static_cast<uint32_t>(entry_tag.value() >> 3u);")
    w.line("uint32_t entry_wire = static_cast<uint32_t>(entry_tag.value() & 0x7u);")
    w.line("switch (entry_field) {")
    w.push()
    w.line("case 1u:")
    w.push()
    w.line(f"if (entry_wire != {_wire(key)}u) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(), 1u); }}")
    _emit_read_named_value(w, key, "entry_reader", "key", options)
    w.line("break;")
    w.pop()
    w.line("case 2u:")
    w.push()
    w.line(f"if (entry_wire != {_wire(value)}u) {{ return ::protocyte::Status::error(::protocyte::ErrorCode::invalid_wire_type, entry_reader.position(), 2u); }}")
    _emit_read_named_value(w, value, "entry_reader", "value", options)
    w.line("break;")
    w.pop()
    w.line("default: {")
    w.push()
    w.line("auto st = ::protocyte::skip_field(entry_reader, entry_wire, entry_field);")
    w.line("if (!st) { return st; }")
    w.line("break;")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.pop()
    w.line("}")
    w.line("auto finish = entry_reader.finish();")
    w.line("if (!finish) { return finish; }")
    w.line(f"auto insert = {_member(item)}.insert_or_assign(::protocyte::move(key), ::protocyte::move(value));")
    w.line("if (!insert) { return insert; }")


def _emit_temp_decl(w: CppWriter, item: FieldModel, name: str, options: GeneratorOptions) -> None:
    typ = _field_type(item, options)
    if item.kind in {"string", "bytes"}:
        w.line(f"{typ} {name}(ctx_);")
    elif item.kind == "message":
        w.line(f"{typ} {name}(*ctx_);")
    else:
        w.line(f"{typ} {name} = {_default(item)};")


def _emit_read_named_value(w: CppWriter, item: FieldModel, reader: str, target: str, options: GeneratorOptions) -> None:
    if item.kind in {"string", "bytes"}:
        helper = "read_string" if item.kind == "string" else "read_bytes"
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"auto st = ::protocyte::{helper}<Config>(*ctx_, {reader}, static_cast<size_t>(len.value()), {target});")
        w.line("if (!st) { return st; }")
    elif item.kind == "message":
        w.line(f"auto len = ::protocyte::read_varint({reader});")
        w.line("if (!len) { return len.status(); }")
        w.line(f"::protocyte::LimitedReader<Reader> nested({reader}, static_cast<size_t>(len.value()));")
        w.line(f"auto st = {target}.merge_from(nested);")
        w.line("if (!st) { return st; }")
        w.line("st = nested.finish();")
        w.line("if (!st) { return st; }")
    else:
        _emit_read_scalar(w, item, reader, target, options)


def _emit_read_scalar(w: CppWriter, item: FieldModel, reader: str, target: str, options: GeneratorOptions) -> None:
    del options
    t = item.proto_type
    if t in {
        FieldDescriptorProto.TYPE_INT32,
        FieldDescriptorProto.TYPE_INT64,
        FieldDescriptorProto.TYPE_UINT32,
        FieldDescriptorProto.TYPE_UINT64,
        FieldDescriptorProto.TYPE_BOOL,
        FieldDescriptorProto.TYPE_ENUM,
    }:
        w.line(f"auto value = ::protocyte::read_varint({reader});")
        w.line("if (!value) { return value.status(); }")
        if t == FieldDescriptorProto.TYPE_BOOL:
            w.line(f"{target} = value.value() != 0u;")
        else:
            w.line(f"{target} = static_cast<{_field_type(item, GeneratorOptions())}>(value.value());")
        return
    if t == FieldDescriptorProto.TYPE_SINT32:
        w.line(f"auto value = ::protocyte::read_varint({reader});")
        w.line("if (!value) { return value.status(); }")
        w.line(f"{target} = ::protocyte::decode_zigzag32(static_cast<uint32_t>(value.value()));")
        return
    if t == FieldDescriptorProto.TYPE_SINT64:
        w.line(f"auto value = ::protocyte::read_varint({reader});")
        w.line("if (!value) { return value.status(); }")
        w.line(f"{target} = ::protocyte::decode_zigzag64(value.value());")
        return
    if t in {FieldDescriptorProto.TYPE_FIXED32, FieldDescriptorProto.TYPE_SFIXED32, FieldDescriptorProto.TYPE_FLOAT}:
        w.line(f"auto value = ::protocyte::read_fixed32({reader});")
        w.line("if (!value) { return value.status(); }")
        if t == FieldDescriptorProto.TYPE_FLOAT:
            w.line("union { uint32_t bits; float value; } conv;")
            w.line("conv.bits = value.value();")
            w.line(f"{target} = conv.value;")
        else:
            w.line(f"{target} = static_cast<{_field_type(item, GeneratorOptions())}>(value.value());")
        return
    if t in {FieldDescriptorProto.TYPE_FIXED64, FieldDescriptorProto.TYPE_SFIXED64, FieldDescriptorProto.TYPE_DOUBLE}:
        w.line(f"auto value = ::protocyte::read_fixed64({reader});")
        w.line("if (!value) { return value.status(); }")
        if t == FieldDescriptorProto.TYPE_DOUBLE:
            w.line("union { uint64_t bits; double value; } conv;")
            w.line("conv.bits = value.value();")
            w.line(f"{target} = conv.value;")
        else:
            w.line(f"{target} = static_cast<{_field_type(item, GeneratorOptions())}>(value.value());")


def _emit_serialize_statement(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    condition = _presence(item)
    if item.oneof_name:
        condition = f"{cpp_identifier(item.oneof_name)}_case_ == {item.oneof_name[0].upper() + item.oneof_name[1:]}Case::{item.cpp_name}"
    if item.repeated and item.kind != "map":
        w.line(f"for (size_t i = 0u; i < {_member(item)}.size(); ++i) {{")
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


def _emit_write_field(w: CppWriter, item: FieldModel, value: str, options: GeneratorOptions) -> None:
    del options
    w.line(f"auto st = ::protocyte::write_tag(writer, {item.number}u, {_wire(item)}u);")
    w.line("if (!st) { return st; }")
    if item.kind in {"string", "bytes"}:
        w.line(f"st = ::protocyte::write_bytes(writer, {value}.view());")
        w.line("if (!st) { return st; }")
    elif item.kind == "message":
        expr = f"{value}.value()" if value == _member(item) else value
        w.line(f"auto msg_size = {expr}.encoded_size();")
        w.line("if (!msg_size) { return msg_size.status(); }")
        w.line("st = ::protocyte::write_varint(writer, static_cast<uint64_t>(msg_size.value()));")
        w.line("if (!st) { return st; }")
        w.line(f"st = {expr}.serialize(writer);")
        w.line("if (!st) { return st; }")
    else:
        _emit_write_scalar(w, item, value)


def _emit_write_map(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    assert item.map_key is not None and item.map_value is not None
    w.line(f"auto st_map_{item.cpp_name} = {_member(item)}.for_each([&](const auto& key, const auto& value) noexcept -> ::protocyte::Status {{")
    w.push()
    w.line("size_t entry_payload = 0u;")
    _emit_add_size_status(w, _field_with_number(item.map_key, 1), "key", options, "entry_payload")
    _emit_add_size_status(w, _field_with_number(item.map_value, 2), "value", options, "entry_payload")
    w.line(f"auto st = ::protocyte::write_tag(writer, {item.number}u, 2u);")
    w.line("if (!st) { return st; }")
    w.line("st = ::protocyte::write_varint(writer, static_cast<uint64_t>(entry_payload));")
    w.line("if (!st) { return st; }")
    w.line("{")
    w.push()
    _emit_write_field(w, _field_with_number(item.map_key, 1), "key", options)
    w.pop()
    w.line("}")
    w.line("{")
    w.push()
    _emit_write_field(w, _field_with_number(item.map_value, 2), "value", options)
    w.pop()
    w.line("}")
    w.line("return ::protocyte::Status::ok();")
    w.pop()
    w.line("});")
    w.line(f"if (!st_map_{item.cpp_name}) {{ return st_map_{item.cpp_name}; }}")


def _emit_write_scalar(w: CppWriter, item: FieldModel, value: str) -> None:
    t = item.proto_type
    if t in {
        FieldDescriptorProto.TYPE_INT32,
        FieldDescriptorProto.TYPE_INT64,
        FieldDescriptorProto.TYPE_UINT32,
        FieldDescriptorProto.TYPE_UINT64,
        FieldDescriptorProto.TYPE_BOOL,
        FieldDescriptorProto.TYPE_ENUM,
    }:
        w.line(f"st = ::protocyte::write_varint(writer, static_cast<uint64_t>({value}));")
    elif t == FieldDescriptorProto.TYPE_SINT32:
        w.line(f"st = ::protocyte::write_varint(writer, ::protocyte::encode_zigzag32({value}));")
    elif t == FieldDescriptorProto.TYPE_SINT64:
        w.line(f"st = ::protocyte::write_varint(writer, ::protocyte::encode_zigzag64({value}));")
    elif t in {FieldDescriptorProto.TYPE_FIXED32, FieldDescriptorProto.TYPE_SFIXED32}:
        w.line(f"st = ::protocyte::write_fixed32(writer, static_cast<uint32_t>({value}));")
    elif t == FieldDescriptorProto.TYPE_FLOAT:
        w.line("union { float value; uint32_t bits; } conv;")
        w.line(f"conv.value = {value};")
        w.line("st = ::protocyte::write_fixed32(writer, conv.bits);")
    elif t in {FieldDescriptorProto.TYPE_FIXED64, FieldDescriptorProto.TYPE_SFIXED64}:
        w.line(f"st = ::protocyte::write_fixed64(writer, static_cast<uint64_t>({value}));")
    elif t == FieldDescriptorProto.TYPE_DOUBLE:
        w.line("union { double value; uint64_t bits; } conv;")
        w.line(f"conv.value = {value};")
        w.line("st = ::protocyte::write_fixed64(writer, conv.bits);")
    w.line("if (!st) { return st; }")


def _emit_size_statement(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    condition = _presence(item)
    if item.oneof_name:
        condition = f"{cpp_identifier(item.oneof_name)}_case_ == {item.oneof_name[0].upper() + item.oneof_name[1:]}Case::{item.cpp_name}"
    if item.repeated and item.kind != "map":
        w.line(f"for (size_t i = 0u; i < {_member(item)}.size(); ++i) {{")
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
    w.line(f"auto st_map_size_{item.cpp_name} = {_member(item)}.for_each([&](const auto& key, const auto& value) noexcept -> ::protocyte::Status {{")
    w.push()
    w.line("size_t entry_payload = 0u;")
    _emit_add_size_status(w, _field_with_number(item.map_key, 1), "key", options, "entry_payload")
    _emit_add_size_status(w, _field_with_number(item.map_value, 2), "value", options, "entry_payload")
    w.line(f"return ::protocyte::add_size(&total, ::protocyte::tag_size({item.number}u) + ::protocyte::varint_size(entry_payload) + entry_payload);")
    w.pop()
    w.line("});")
    w.line(f"if (!st_map_size_{item.cpp_name}) {{ return ::protocyte::Result<size_t>::err(st_map_size_{item.cpp_name}.error()); }}")


def _emit_add_size(w: CppWriter, item: FieldModel, value: str, options: GeneratorOptions) -> None:
    del options
    if item.kind in {"string", "bytes"}:
        value_size = f"::protocyte::tag_size({item.number}u) + ::protocyte::varint_size({value}.size()) + {value}.size()"
    elif item.kind == "message":
        expr = f"{value}.value()" if value == _member(item) else value
        w.line(f"auto nested_size = {expr}.encoded_size();")
        w.line("if (!nested_size) { return nested_size.status(); }")
        value_size = f"::protocyte::tag_size({item.number}u) + ::protocyte::varint_size(nested_size.value()) + nested_size.value()"
    else:
        value_size = f"::protocyte::tag_size({item.number}u) + {_scalar_size(item, value)}"
    w.line(f"auto st = ::protocyte::add_size(&total, {value_size});")
    w.line("if (!st) { return ::protocyte::Result<size_t>::err(st.error()); }")


def _emit_add_size_status(
    w: CppWriter,
    item: FieldModel,
    value: str,
    options: GeneratorOptions,
    total_name: str,
) -> None:
    if item.kind in {"string", "bytes"}:
        value_size = f"::protocyte::tag_size({item.number}u) + ::protocyte::varint_size({value}.size()) + {value}.size()"
    elif item.kind == "message":
        w.line(f"auto nested_size = {value}.encoded_size();")
        w.line("if (!nested_size) { return nested_size.status(); }")
        value_size = f"::protocyte::tag_size({item.number}u) + ::protocyte::varint_size(nested_size.value()) + nested_size.value()"
    else:
        value_size = f"::protocyte::tag_size({item.number}u) + {_scalar_size(item, value)}"
    w.line(f"auto st_size = ::protocyte::add_size(&{total_name}, {value_size});")
    w.line("if (!st_size) { return st_size; }")


def _emit_member(w: CppWriter, item: FieldModel, options: GeneratorOptions) -> None:
    if item.repeated and item.kind != "map":
        w.line(f"typename Config::template Vector<{_element_type(item, options)}> {_member(item)};")
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
    if item.kind in {"string", "bytes"}:
        w.line(f"{_field_type(item, options)} {_member(item)};")
        if item.proto3_optional:
            w.line(f"bool has_{item.cpp_name}_ = false;")
        return
    w.line(f"{_field_type(item, options)} {_member(item)} = {_default(item)};")
    if item.proto3_optional:
        w.line(f"bool has_{item.cpp_name}_ = false;")


def _emit_clear_statement(w: CppWriter, item: FieldModel) -> None:
    if item.kind == "message":
        w.line(f"{_member(item)}.reset();")
    elif item.kind in {"string", "bytes"}:
        w.line(f"{_member(item)}.clear();")
    else:
        w.line(f"{_member(item)} = {_default(item)};")


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
        return "int32_t"
    return SCALAR_CPP_TYPES[item.proto_type]


def _enum_type(enum: EnumModel | None, options: GeneratorOptions) -> str:
    if enum is None:
        return "int32_t"
    return _qualified_name(enum.package, enum.cpp_name, options)


def _element_type(item: FieldModel, options: GeneratorOptions) -> str:
    return _field_type(item, options)


def _default(item: FieldModel) -> str:
    if item.kind == "enum":
        return "0"
    return SCALAR_DEFAULTS.get(item.proto_type, "{}")


def _member(item: FieldModel) -> str:
    return f"{item.cpp_name}_"


def _wire(item: FieldModel) -> int:
    if item.kind in {"string", "bytes", "message", "map"}:
        return 2
    if item.proto_type in {
        FieldDescriptorProto.TYPE_DOUBLE,
        FieldDescriptorProto.TYPE_FIXED64,
        FieldDescriptorProto.TYPE_SFIXED64,
    }:
        return 1
    if item.proto_type in {
        FieldDescriptorProto.TYPE_FLOAT,
        FieldDescriptorProto.TYPE_FIXED32,
        FieldDescriptorProto.TYPE_SFIXED32,
    }:
        return 5
    return 0


def _presence(item: FieldModel) -> str:
    if item.proto3_optional:
        return f"has_{item.cpp_name}_"
    if item.kind == "message":
        return f"{_member(item)}.has_value()"
    if item.kind in {"string", "bytes"}:
        return f"!{_member(item)}.empty()"
    if item.kind == "enum":
        return f"{_member(item)} != 0"
    if item.proto_type == FieldDescriptorProto.TYPE_BOOL:
        return _member(item)
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
    return f"::protocyte::varint_size(static_cast<uint64_t>({value}))"


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
