"""LLDB data formatters for Protocyte runtime types."""

from __future__ import annotations

import os
import string as _string
import sys


_BYTES_TYPE_REGEX = r"^.*protocyte::Bytes<.*>$"
_STRING_TYPE_REGEX = r"^.*protocyte::String<.*>$"
_SPAN_TYPE_REGEX = r"^.*protocyte::Span<.*>$"
_VECTOR_TYPE_REGEX = r"^.*protocyte::Vector<.+,.+>$"
_HASH_MAP_TYPE_REGEX = r"^.*protocyte::HashMap<.+,.+,.+>$"
_DEFAULT_BYTES_TYPE = "protocyte::Bytes<protocyte::DefaultConfig>"
_DEFAULT_STRING_TYPE = "protocyte::String<protocyte::DefaultConfig>"
_registered_exact_types = set()
_SCRIPT_DELETE_IGNORED_ERRORS = (
    "does not exist",
    "not found",
    "unknown command",
    "can only delete user defined commands",
)


def _recognizer_type_name(type_):
    for method_name in ("GetDisplayTypeName", "GetName"):
        method = getattr(type_, method_name, None)
        if not callable(method):
            continue
        try:
            name = method()
        except Exception:
            continue
        if name:
            return _canonical_type_name(name)
    return ""


def _canonical_type_name(name):
    name = name.strip()
    for prefix in ("class ", "struct "):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _is_template_type(type_, template_name):
    name = _recognizer_type_name(type_)
    return name.startswith(template_name + "<") or name.startswith("::" + template_name + "<")


def _is_named_type(type_, type_name):
    name = _recognizer_type_name(type_)
    return name == type_name or name == "::" + type_name


def is_result_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::Result")


def is_optional_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::Optional")


def is_box_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::Box")


def is_vector_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::Vector")


def is_bytes_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::Bytes")


def is_string_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::String")


def is_span_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::Span")


def is_hash_map_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::HashMap")


def is_limited_reader_type(type_, _internal_dict):
    return _is_template_type(type_, "protocyte::LimitedReader")


def _run_lldb_commands(debugger, commands, *, context, ignored_errors=None):
    interpreter = debugger.GetCommandInterpreter()
    result = lldb.SBCommandReturnObject()
    ignored_errors = ignored_errors or {}
    for command in commands:
        result.Clear()
        interpreter.HandleCommand(command, result)
        if result.Succeeded():
            continue

        error = (result.GetError() or "").strip() or "unknown LLDB error"
        lowered_error = error.lower()
        ignored_fragments = ignored_errors.get(command, ())
        if any(fragment in lowered_error for fragment in ignored_fragments):
            continue

        return f"{context} failed while running {command!r}: {error}"
    return None


def _is_unsupported_option_error(error):
    lowered_error = error.lower()
    return "unknown or ambiguous option" in lowered_error or "unknown option" in lowered_error


def write_smoke_lldbinit():
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    smoke_lldbinit = os.path.join(repo_root, "tests", "smoke", ".lldbinit")
    content = "\n".join(
        [
            "command script import ../../src/protocyte/debugger/protocyte_lldb.py",
            "protocyte-oneof '^.*test::ultimate::.*<.*>$'",
            "",
        ]
    )
    with open(smoke_lldbinit, "w", encoding="utf-8") as file:
        file.write(content)


if __name__ == "__main__":
    write_smoke_lldbinit()
    sys.exit(0)


import lldb  # noqa: E402


MAX_INLINE_BYTES = 64


def _child(value, name):
    value = value.GetNonSyntheticValue()
    child = value.GetChildMemberWithName(name)
    if child.IsValid():
        return child
    return lldb.SBValue()


def _unsigned(value, default=0):
    if not value.IsValid():
        return default
    return value.GetValueAsUnsigned(default)


def _signed(value, default=0):
    if not value.IsValid():
        return default
    return value.GetValueAsSigned(default)


def _bool(value):
    return _unsigned(value, 0) != 0


def _pointer_value(value):
    return _unsigned(value, 0)


def _pointee_type(pointer):
    if not pointer.IsValid():
        return lldb.SBType()
    return pointer.GetType().GetPointeeType()


def _type_name(value_type):
    for method_name in ("GetDisplayTypeName", "GetName"):
        method = getattr(value_type, method_name, None)
        if callable(method):
            try:
                name = method()
            except Exception:
                continue
            if name:
                return name
    return ""


def _first_template_argument(type_name):
    start = type_name.find("<")
    if start < 0:
        return ""
    depth = 0
    for index in range(start + 1, len(type_name)):
        char = type_name[index]
        if char == "<":
            depth += 1
        elif char == ">":
            if depth == 0:
                return type_name[start + 1 : index].strip()
            depth -= 1
        elif char == "," and depth == 0:
            return type_name[start + 1 : index].strip()
    return ""


def _type_name_is_lvalue_reference(type_name):
    normalized = type_name.replace(" ", "")
    return normalized.endswith("&") and not normalized.endswith("&&")


def _first_template_argument_is_lvalue_reference(value):
    try:
        value_type = value.GetType().GetTemplateArgumentType(0)
    except Exception:
        value_type = lldb.SBType()
    if value_type.IsValid():
        is_reference_type = getattr(value_type, "IsReferenceType", None)
        if callable(is_reference_type):
            try:
                if is_reference_type():
                    return True
            except Exception:
                pass
        if _type_name_is_lvalue_reference(_type_name(value_type)):
            return True

    return _type_name_is_lvalue_reference(
        _first_template_argument(value.GetTypeName() or "")
    )


def _read_process_memory(value, address, size):
    if address == 0 or size == 0:
        return b""
    process = value.GetProcess()
    if not process.IsValid():
        return b""
    error = lldb.SBError()
    data = process.ReadMemory(address, size, error)
    if not error.Success():
        return b""
    return data


def _read_byte_span(value, data_value, size_value, limit=MAX_INLINE_BYTES):
    size = _unsigned(size_value, 0)
    address = _pointer_value(data_value)
    return _read_process_memory(value, address, min(size, limit)), size, address


def _ascii_preview(data):
    out = []
    for byte in data:
        char = chr(byte)
        out.append(
            char if char in _string.printable and char not in "\r\n\t\x0b\x0c" else "."
        )
    return "".join(out)


def _hex_preview(data):
    return " ".join(f"{byte:02x}" for byte in data)


def _bytes_summary_from_span(value, data_value, size_value):
    data, size, address = _read_byte_span(value, data_value, size_value)
    suffix = " ..." if size > len(data) else ""
    if address == 0 and size != 0:
        return f"{_count_summary('size', size)}, data=null"
    return (
        f"{_count_summary('size', size)}, hex=[{_hex_preview(data)}{suffix}], "
        f'ascii="{_ascii_preview(data)}{suffix}"'
    )


def _count_summary(name, value):
    return f"{name}={value} [0x{value:x}]"


def _vector_storage(value):
    return _child(value, "data_"), _child(value, "size_"), _child(value, "capacity_")


def _vector_context(value):
    return _child(value, "ctx_")


def _bytes_storage(value):
    vector = _child(value, "bytes_")
    return _vector_storage(vector)


def _bytes_context(value):
    return _child(value, "ctx_")


def _string_storage(value):
    bytes_value = _child(value, "bytes_")
    return _bytes_storage(bytes_value)


def _string_context(value):
    bytes_value = _child(value, "bytes_")
    return _bytes_context(bytes_value)


def _span_storage(value):
    data = _child(value, "data_")
    size = _child(value, "size_")
    if data.IsValid() or size.IsValid():
        return data, size
    return _child(value, "data"), _child(value, "size")


def _optional_payload(value, name="value"):
    has_value = _bool(_child(value, "has_"))
    storage = _child(value, "storage_")
    if not has_value or not storage.IsValid():
        return lldb.SBValue()
    try:
        value_type = value.GetType().GetTemplateArgumentType(0)
    except Exception:
        value_type = lldb.SBType()
    if not value_type.IsValid():
        return lldb.SBValue()
    return value.CreateValueFromAddress(name, storage.GetAddress(), value_type)


def _value_label(value):
    if not value.IsValid():
        return "<invalid>"
    typename = value.GetTypeName() or ""
    if typename.startswith("protocyte::String<"):
        return string_summary(value, None)
    if typename.startswith("protocyte::Bytes<") or typename in (
        "protocyte::ByteView",
        "protocyte::MutableByteView",
    ):
        return (
            bytes_summary(value, None)
            if typename.startswith("protocyte::Bytes<")
            else byte_view_summary(value, None)
        )
    summary = value.GetSummary()
    if summary:
        return summary
    raw = value.GetValue()
    if raw:
        return raw
    return typename or "<value>"


def _case_name(value):
    case_text = value.GetValue()
    if not case_text:
        return "none"
    return case_text.split("::")[-1]


def _oneof_prefix(case_field_name):
    suffix = "_case_"
    if case_field_name.endswith(suffix):
        return case_field_name[: -len(suffix)]
    return ""


def _case_field_names(value):
    names = []
    for index in range(value.GetNumChildren()):
        child = value.GetChildAtIndex(index)
        name = child.GetName() or ""
        if name.endswith("_case_"):
            names.append(name)
    return names


def _oneof_payload(value, prefix, case_name):
    if case_name == "none":
        return lldb.SBValue()
    payload = _child(value, f"{case_name}_")
    if payload.IsValid():
        return payload
    union_value = _child(value, prefix)
    if not union_value.IsValid():
        return lldb.SBValue()
    payload = _child(union_value, case_name)
    if payload.IsValid():
        return payload
    return _child(union_value, f"{case_name}_")


def _renamed_value(parent, source, name):
    if not source.IsValid():
        return lldb.SBValue()
    try:
        address = source.GetLoadAddress()
    except Exception:
        address = lldb.LLDB_INVALID_ADDRESS
    if address != lldb.LLDB_INVALID_ADDRESS:
        renamed = parent.CreateValueFromAddress(name, int(address), source.GetType())
        if renamed.IsValid():
            return renamed
    renamed = parent.CreateValueFromData(name, source.GetData(), source.GetType())
    if renamed.IsValid():
        return renamed
    return source


def _raw_children(value):
    raw = _raw_view(value)
    return [raw] if raw.IsValid() else []


def _disable_synthetic(value):
    for method_name, method_value in (
        ("SetPreferSyntheticValue", False),
        ("SetSyntheticChildrenGenerated", False),
    ):
        method = getattr(value, method_name, None)
        if not callable(method):
            continue
        try:
            method(method_value)
        except Exception:
            pass


def _raw_view(value):
    raw = value.GetNonSyntheticValue()
    if not raw.IsValid():
        return lldb.SBValue()
    try:
        renamed = raw.Clone("Raw View")
    except Exception:
        renamed = lldb.SBValue()
    if not renamed.IsValid():
        renamed = value.CreateValueFromData("Raw View", raw.GetData(), raw.GetType())
    if not renamed.IsValid():
        renamed = _renamed_value(value, raw, "Raw View")
    if not renamed.IsValid():
        return lldb.SBValue()
    _disable_synthetic(renamed)
    return renamed if renamed.GetNumChildren() else lldb.SBValue()


def _raw_child_index(children, name):
    for index, child in enumerate(children):
        if child.GetName() == name:
            return index
    return -1


def _is_raw_view_value(value):
    return (value.GetName() or "") == "Raw View"


def _parent_value(value):
    method = getattr(value, "GetParent", None)
    if not callable(method):
        return lldb.SBValue()
    try:
        parent = method()
    except Exception:
        return lldb.SBValue()
    return parent if parent.IsValid() else lldb.SBValue()


def _is_raw_tree_value(value):
    current = value
    for _depth in range(32):
        if not current.IsValid():
            return False
        if _is_raw_view_value(current):
            return True
        current = _parent_value(current)
    return False


def _raw_member_children(value):
    raw = value.GetNonSyntheticValue()
    if not raw.IsValid():
        return []
    children = []
    for index in range(raw.GetNumChildren()):
        child = raw.GetChildAtIndex(index)
        if child.IsValid():
            _disable_synthetic(child)
            children.append(child)
    return children


def _set_provider_value(provider, value):
    provider.raw_mode = _is_raw_tree_value(value)
    provider.value = value.GetNonSyntheticValue()


def _set_raw_mode(provider):
    provider.raw_mode_children = []
    if not provider.raw_mode:
        return False
    provider.raw_mode_children = _raw_member_children(provider.value)
    return True


def _raw_mode_child_index(provider, name):
    return _raw_child_index(provider.raw_mode_children, name)


def _raw_mode_child_at_index(provider, index):
    if index < 0 or index >= len(provider.raw_mode_children):
        return lldb.SBValue()
    return provider.raw_mode_children[index]


def status_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    error = _child(value, "error_")
    code = _child(error, "code")
    code_name = code.GetValue() if code.IsValid() else None
    if code_name and code_name.endswith("::ok"):
        return "ok"
    offset = _unsigned(_child(error, "offset"), 0)
    field = _unsigned(_child(error, "field_number"), 0)
    if code_name:
        return f"code={code_name}, offset={offset}, field={field}"
    return f"code=error, offset={offset}, field={field}"


def error_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    code = _child(value, "code")
    code_name = code.GetValue() if code.IsValid() else None
    offset = _unsigned(_child(value, "offset"), 0)
    field = _unsigned(_child(value, "field_number"), 0)
    return f"code={code_name or 'error'}, offset={offset}, field={field}"


def result_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    ok = _bool(_child(value, "ok_"))
    if ok:
        return "ok"
    return "err, " + error_summary(_child(value, "error_"), _internal_dict)


def optional_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    ptr = _child(value.GetNonSyntheticValue(), "ptr_")
    if ptr.IsValid():
        return "some" if _pointer_value(ptr) else "none"
    return "some" if _bool(_child(value, "has_")) else "none"


def box_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    ptr = _child(value, "ptr_")
    address = _pointer_value(ptr)
    return f"value=0x{address:x}" if address else "value=null"


def vector_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    _data, size, _capacity = _vector_storage(value)
    return _count_summary("size", _unsigned(size, 0))


def bytes_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    data, size, _capacity = _bytes_storage(value)
    return _bytes_summary_from_span(value, data, size)


def string_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    data_value, size_value, _capacity = _string_storage(value)
    data, size, address = _read_byte_span(value, data_value, size_value)
    suffix = " ..." if size > len(data) else ""
    if address == 0 and size != 0:
        return f"{_count_summary('size', size)}, data=null"
    text = data.decode("utf-8", errors="replace")
    return (
        f'{_count_summary("size", size)}, value="{text}{suffix}", '
        f"hex=[{_hex_preview(data)}{suffix}]"
    )


def byte_view_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    return _bytes_summary_from_span(value, _child(value, "data"), _child(value, "size"))


def mutable_byte_view_summary(value, _internal_dict):
    return byte_view_summary(value, _internal_dict)


def span_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    _data, size = _span_storage(value)
    return _count_summary("size", _unsigned(size, 0))


def hash_map_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    size = _child(value, "size_")
    buckets = _child(value, "buckets_")
    _data, bucket_count, _capacity = _vector_storage(buckets)
    return (
        f"{_count_summary('size', _unsigned(size, 0))}, "
        f"{_count_summary('buckets', _unsigned(bucket_count, 0))}"
    )


def slice_reader_summary(value, _internal_dict):
    pos = _unsigned(_child(value, "pos_"), 0)
    size = _unsigned(_child(value, "size_"), 0)
    return f"pos={pos}, size={size}, remaining={max(size - pos, 0)}"


def limited_reader_summary(value, _internal_dict):
    remaining = _unsigned(_child(value, "remaining_"), 0)
    pos = _unsigned(_child(value, "pos_"), 0)
    return f"pos={pos}, remaining={remaining}"


def slice_writer_summary(value, _internal_dict):
    pos = _unsigned(_child(value, "pos_"), 0)
    capacity = _unsigned(_child(value, "capacity_"), 0)
    return f"pos={pos}, capacity={capacity}, remaining={max(capacity - pos, 0)}"


class VectorSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            return
        self.data, self.size_value, self.capacity_value = _vector_storage(self.value)
        self.size = _unsigned(self.size_value, 0)
        self.element_type = _pointee_type(self.data)
        self.element_size = (
            self.element_type.GetByteSize() if self.element_type.IsValid() else 0
        )
        self.metadata_children = [
            child
            for child in (
                _renamed_value(self.value, _vector_context(self.value), "context"),
                _renamed_value(self.value, self.capacity_value, "capacity"),
            )
            if child.IsValid()
        ]
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        if self.raw_mode:
            return len(self.raw_mode_children)
        return len(self.metadata_children) + self.size + len(self.raw_children)

    def get_child_index(self, name):
        if self.raw_mode:
            return _raw_mode_child_index(self, name)
        for index, child in enumerate(self.metadata_children):
            if child.GetName() == name:
                return index
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return len(self.metadata_children) + self.size + raw_index
        if name.startswith("[") and name.endswith("]"):
            try:
                index = int(name[1:-1])
            except ValueError:
                return -1
            if 0 <= index < self.size:
                return len(self.metadata_children) + index
        return -1

    def get_child_at_index(self, index):
        if self.raw_mode:
            return _raw_mode_child_at_index(self, index)
        metadata_count = len(self.metadata_children)
        if 0 <= index < metadata_count:
            return self.metadata_children[index]
        element_index = index - metadata_count
        if self.size <= element_index < self.size + len(self.raw_children):
            return self.raw_children[element_index - self.size]
        if element_index < 0 or element_index >= self.size or self.element_size == 0:
            return lldb.SBValue()
        address = _pointer_value(self.data) + element_index * self.element_size
        return self.value.CreateValueFromAddress(
            f"[{element_index}]", address, self.element_type
        )

    def has_children(self):
        return True


class ByteSpanSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            return
        typename = self.value.GetTypeName() or ""
        if typename.startswith("protocyte::Bytes<"):
            self.data, self.size_value, _capacity = _bytes_storage(self.value)
            context = _bytes_context(self.value)
            metadata_sources = (
                ("context", context),
                ("capacity", _capacity),
            )
        elif typename.startswith("protocyte::String<"):
            self.data, self.size_value, _capacity = _string_storage(self.value)
            context = _string_context(self.value)
            metadata_sources = (
                ("context", context),
                ("capacity", _capacity),
            )
        elif typename.startswith("protocyte::Span<"):
            self.data, self.size_value = _span_storage(self.value)
            metadata_sources = ()
        else:
            self.data, self.size_value = _span_storage(self.value)
            metadata_sources = ()
        self.size = _unsigned(self.size_value, 0)
        self.element_type = _pointee_type(self.data)
        self.element_size = (
            self.element_type.GetByteSize() if self.element_type.IsValid() else 1
        )
        self.metadata_children = [
            _renamed_value(self.value, source, name)
            for name, source in metadata_sources
            if source.IsValid()
        ]
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        if self.raw_mode:
            return len(self.raw_mode_children)
        return len(self.metadata_children) + self.size + len(self.raw_children)

    def get_child_index(self, name):
        if self.raw_mode:
            return _raw_mode_child_index(self, name)
        for index, child in enumerate(self.metadata_children):
            if child.GetName() == name:
                return index
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return len(self.metadata_children) + self.size + raw_index
        if name.startswith("[") and name.endswith("]"):
            try:
                index = int(name[1:-1])
            except ValueError:
                return -1
            if 0 <= index < self.size:
                return len(self.metadata_children) + index
        return -1

    def get_child_at_index(self, index):
        if self.raw_mode:
            return _raw_mode_child_at_index(self, index)
        metadata_count = len(self.metadata_children)
        if 0 <= index < metadata_count:
            return self.metadata_children[index]
        element_index = index - metadata_count
        if self.size <= element_index < self.size + len(self.raw_children):
            return self.raw_children[element_index - self.size]
        if element_index < 0 or element_index >= self.size:
            return lldb.SBValue()
        address = _pointer_value(self.data) + element_index * self.element_size
        return self.value.CreateValueFromAddress(
            f"[{element_index}]", address, self.element_type
        )

    def has_children(self):
        return True


class PointerValueSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            return
        if (self.value.GetTypeName() or "").startswith("protocyte::Box<"):
            self.ptr = _child(self.value, "ptr_")
        else:
            self.ptr = _child(self.value, "ptr_")
        self.pointee_type = _pointee_type(self.ptr)
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        if self.raw_mode:
            return len(self.raw_mode_children)
        return (
            1 if _pointer_value(self.ptr) != 0 and self.pointee_type.IsValid() else 0
        ) + len(self.raw_children)

    def get_child_index(self, name):
        if self.raw_mode:
            return _raw_mode_child_index(self, name)
        value_count = (
            1 if _pointer_value(self.ptr) != 0 and self.pointee_type.IsValid() else 0
        )
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return value_count + raw_index
        return 0 if name == "value" else -1

    def get_child_at_index(self, index):
        if self.raw_mode:
            return _raw_mode_child_at_index(self, index)
        value_count = (
            1 if _pointer_value(self.ptr) != 0 and self.pointee_type.IsValid() else 0
        )
        if value_count <= index < value_count + len(self.raw_children):
            return self.raw_children[index - value_count]
        if index != 0 or value_count == 0:
            return lldb.SBValue()
        return self.value.CreateValueFromAddress(
            "value", _pointer_value(self.ptr), self.pointee_type
        )

    def has_children(self):
        return True


class ResultSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            return
        self.ok = _bool(_child(self.value, "ok_"))
        self.value_ptr = _child(self.value, "value_")
        self.value_is_reference = _first_template_argument_is_lvalue_reference(
            self.value
        )
        self.value_pointee_type = _pointee_type(self.value_ptr)
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        if self.raw_mode:
            return len(self.raw_mode_children)
        return 1 + len(self.raw_children)

    def get_child_index(self, name):
        if self.raw_mode:
            return _raw_mode_child_index(self, name)
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return 1 + raw_index
        if name == "value" and self.ok:
            return 0
        if name == "error" and not self.ok:
            return 0
        return -1

    def get_child_at_index(self, index):
        if self.raw_mode:
            return _raw_mode_child_at_index(self, index)
        if 1 <= index < 1 + len(self.raw_children):
            return self.raw_children[index - 1]
        if index != 0:
            return lldb.SBValue()
        if self.ok:
            address = _pointer_value(self.value_ptr)
            if (
                self.value_is_reference
                and address != 0
                and self.value_pointee_type.IsValid()
            ):
                return self.value.CreateValueFromAddress(
                    "value", address, self.value_pointee_type
                )
            return _child(self.value, "value_")
        return _child(self.value, "error_")

    def has_children(self):
        return True


class OptionalSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            return
        self.ptr = _child(self.value, "ptr_")
        self.has_value = (
            _pointer_value(self.ptr) != 0
            if self.ptr.IsValid()
            else _bool(_child(self.value, "has_"))
        )
        self.storage = _child(self.value, "storage_")
        try:
            self.value_type = self.value.GetType().GetTemplateArgumentType(0)
        except Exception:
            self.value_type = lldb.SBType()
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        if self.raw_mode:
            return len(self.raw_mode_children)
        return (1 if self.has_value and self.value_type.IsValid() else 0) + len(
            self.raw_children
        )

    def get_child_index(self, name):
        if self.raw_mode:
            return _raw_mode_child_index(self, name)
        value_count = 1 if self.has_value and self.value_type.IsValid() else 0
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return value_count + raw_index
        return 0 if name == "value" and value_count else -1

    def get_child_at_index(self, index):
        if self.raw_mode:
            return _raw_mode_child_at_index(self, index)
        value_count = 1 if self.has_value and self.value_type.IsValid() else 0
        if value_count <= index < value_count + len(self.raw_children):
            return self.raw_children[index - value_count]
        if index != 0 or value_count == 0:
            return lldb.SBValue()
        if self.ptr.IsValid():
            pointee_type = _pointee_type(self.ptr)
            if pointee_type.IsValid():
                return self.value.CreateValueFromAddress(
                    "value", _pointer_value(self.ptr), pointee_type
                )
        return self.value.CreateValueFromAddress(
            "value", self.storage.GetAddress(), self.value_type
        )

    def has_children(self):
        return True


class HashMapSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            return
        self.entries = []
        buckets = _child(self.value, "buckets_")
        self.metadata_children = [
            child
            for child in (_renamed_value(self.value, buckets, "buckets"),)
            if child.IsValid()
        ]
        self.raw_children = _raw_children(self.value)
        data, bucket_count_value, _capacity = _vector_storage(buckets)
        bucket_count = _unsigned(bucket_count_value, 0)
        bucket_type = _pointee_type(data)
        bucket_size = bucket_type.GetByteSize() if bucket_type.IsValid() else 0
        base = _pointer_value(data)
        if base == 0 or bucket_size == 0:
            return
        for bucket_index in range(bucket_count):
            bucket = self.value.CreateValueFromAddress(
                f"bucket[{bucket_index}]",
                base + bucket_index * bucket_size,
                bucket_type,
            )
            entry = _optional_payload(bucket, f"entry[{bucket_index}]")
            if not entry.IsValid():
                continue
            key = _child(entry, "key")
            value = _renamed_value(
                self.value, _child(entry, "value"), f"{_value_label(key)} =>"
            )
            if value.IsValid():
                self.entries.append(value)

    def num_children(self):
        if self.raw_mode:
            return len(self.raw_mode_children)
        return len(self.entries) + len(self.metadata_children) + len(self.raw_children)

    def get_child_index(self, name):
        if self.raw_mode:
            return _raw_mode_child_index(self, name)
        entry_count = len(self.entries)
        for index, child in enumerate(self.metadata_children):
            if child.GetName() == name:
                return entry_count + index
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return entry_count + len(self.metadata_children) + raw_index
        for index, entry in enumerate(self.entries):
            if entry.GetName() == name:
                return index
        if name.startswith("[") and name.endswith("]"):
            try:
                return int(name[1:-1])
            except ValueError:
                return -1
        return -1

    def get_child_at_index(self, index):
        if self.raw_mode:
            return _raw_mode_child_at_index(self, index)
        entry_count = len(self.entries)
        metadata_count = len(self.metadata_children)
        if entry_count <= index < entry_count + metadata_count:
            return self.metadata_children[index - entry_count]
        if entry_count + metadata_count <= index < entry_count + metadata_count + len(
            self.raw_children
        ):
            return self.raw_children[index - entry_count - metadata_count]
        if index < 0 or index >= entry_count:
            return lldb.SBValue()
        return self.entries[index]

    def has_children(self):
        return True


class GeneratedMessageOneofSyntheticProvider:
    def __init__(self, value, _internal_dict):
        _set_provider_value(self, value)
        self.update()

    def update(self):
        if _set_raw_mode(self):
            self.children = self.raw_mode_children
            return
        self.children = []
        self.real_child_count = self.value.GetNumChildren()
        for index in range(self.real_child_count):
            self.children.append(self.value.GetChildAtIndex(index))
        for case_field_name in _case_field_names(self.value):
            case_field = _child(self.value, case_field_name)
            case_name = _case_name(case_field)
            prefix = _oneof_prefix(case_field_name)
            if case_name == "none":
                payload = _oneof_payload(self.value, prefix, case_name)
                self.children.append(
                    _renamed_value(
                        self.value,
                        payload if payload.IsValid() else case_field,
                        prefix or case_field_name,
                    )
                )
                continue
            payload = _oneof_payload(self.value, prefix, case_name)
            if not payload.IsValid():
                payload = _child(self.value, f"{prefix}_{case_name}_")
            if not payload.IsValid():
                self.children.append(
                    _renamed_value(self.value, case_field, f"{prefix}: {case_name}")
                )
                continue
            self.children.append(
                _renamed_value(self.value, payload, f"{prefix}: {case_name}")
            )
        self.children.extend(_raw_children(self.value))

    def num_children(self):
        return len(self.children)

    def get_child_index(self, name):
        for index, child in enumerate(self.children):
            if child.GetName() == name:
                return index
        return -1

    def get_child_at_index(self, index):
        if index < 0 or index >= len(self.children):
            return lldb.SBValue()
        return self.children[index]

    def has_children(self):
        return bool(self.children)


def oneof_summary(value, _internal_dict):
    if _is_raw_tree_value(value):
        return None
    parts = []
    value = value.GetNonSyntheticValue()
    for case_field_name in _case_field_names(value):
        prefix = _oneof_prefix(case_field_name)
        case_name = _case_name(_child(value, case_field_name))
        parts.append(f"{prefix}={case_name}")
    return ", ".join(parts) if parts else None


def register_oneof_formatters(debugger, regex):
    category = "protocyte-oneof"
    disable_command = f"type category disable {category}"
    delete_command = f"type category delete {category}"
    define_command = f"type category define {category}"
    commands = [
        disable_command,
        delete_command,
        define_command,
        f"type summary add -w {category} -p -x -F protocyte_lldb.oneof_summary '{regex}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.GeneratedMessageOneofSyntheticProvider '{regex}'",
        f"type category enable {category}",
    ]
    return _run_lldb_commands(
        debugger,
        commands,
        context="Protocyte oneof formatter registration",
        ignored_errors={
            disable_command: (
                "does not exist",
                "not found",
                "invalid type category",
            ),
            delete_command: (
                "does not exist",
                "not found",
                "invalid type category",
                "cannot delete one or more categories",
            ),
            define_command: (
                "already exists",
                "exists already",
            ),
        },
    )


def protocyte_oneof(debugger, command, _exe_ctx, result, _internal_dict):
    regex = command.strip()
    if not regex:
        result.SetError("usage: protocyte-oneof <type-regex>")
        return
    error = register_oneof_formatters(debugger, regex)
    if error:
        result.SetError(error)
        return
    result.PutCString(f"registered Protocyte oneof formatter for {regex}")


def protocyte_formatters(_debugger, _command, _exe_ctx, result, _internal_dict):
    result.PutCString(
        "Protocyte formatter module is loaded. Runtime formatters use exact type "
        "registration, regexes, and LLDB recognizers when supported.\n"
        f"  Bytes exact: {_DEFAULT_BYTES_TYPE}\n"
        f"  String exact: {_DEFAULT_STRING_TYPE}\n"
        f"  Bytes: {_BYTES_TYPE_REGEX}\n"
        f"  String: {_STRING_TYPE_REGEX}\n"
        f"  Span: {_SPAN_TYPE_REGEX}\n"
        f"  Vector: {_VECTOR_TYPE_REGEX}\n"
        f"  HashMap: {_HASH_MAP_TYPE_REGEX}"
    )


def protocyte_bytes(_debugger, command, exe_ctx, result, _internal_dict):
    expression = command.strip()
    if not expression:
        result.SetError("usage: protocyte-bytes <expression>")
        return
    target = exe_ctx.GetTarget()
    value = target.EvaluateExpression(expression)
    if not value.IsValid():
        result.SetError(f"invalid expression: {expression}")
        return
    result.PutCString(bytes_summary(value, {}))


def _formatter_commands_for_type(type_name):
    category = "protocyte"
    type_name = _canonical_type_name(type_name)
    if type_name.startswith("protocyte::Result<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.result_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.ResultSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::Optional<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.optional_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.OptionalSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::Box<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.box_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.PointerValueSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::Vector<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.vector_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.VectorSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::Bytes<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.bytes_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::String<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.string_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::Span<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.span_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::HashMap<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.hash_map_summary '{type_name}'",
            f"type synthetic add -w {category} -l protocyte_lldb.HashMapSyntheticProvider '{type_name}'",
        ]
    if type_name.startswith("protocyte::LimitedReader<"):
        return [
            f"type summary add -w {category} -p -F protocyte_lldb.limited_reader_summary '{type_name}'",
        ]
    return []


def _register_exact_type(debugger, type_name, *, force=False):
    type_name = _canonical_type_name(type_name)
    if not force and type_name in _registered_exact_types:
        return None
    commands = _formatter_commands_for_type(type_name)
    if not commands:
        return f"no Protocyte formatter registration rule for {type_name}"
    commands.append("type category enable protocyte")
    ignored_errors = {
        command: ("already exists", "exists already") for command in commands
    }
    error = _run_lldb_commands(
        debugger,
        commands,
        context=f"Protocyte formatter registration for {type_name}",
        ignored_errors=ignored_errors,
    )
    if error:
        return error
    _registered_exact_types.add(type_name)
    return None


def protocyte_register_type(debugger, command, exe_ctx, result, _internal_dict):
    expression = command.strip()
    if not expression:
        result.SetError("usage: protocyte-register-type <expression>")
        return
    target = exe_ctx.GetTarget()
    value = target.EvaluateExpression(expression)
    if not value.IsValid():
        result.SetError(f"invalid expression: {expression}")
        return
    type_name = value.GetTypeName()
    if not type_name:
        result.SetError(f"could not resolve type for expression: {expression}")
        return
    error = _register_exact_type(debugger, type_name, force=True)
    if error:
        result.SetError(error)
        return
    result.PutCString(
        f"registered Protocyte formatter for {_canonical_type_name(type_name)}"
    )


def _frame_variables(frame):
    if not frame or not frame.IsValid():
        return []
    try:
        variables = frame.GetVariables(True, True, True, True)
    except Exception:
        return []
    try:
        size = variables.GetSize()
    except Exception:
        return []
    return [variables.GetValueAtIndex(index) for index in range(size)]


def protocyte_register_frame_types(debugger, _command, exe_ctx, result, _internal_dict):
    frame = exe_ctx.GetFrame()
    registered = []
    failures = []
    for value in _frame_variables(frame):
        type_name = value.GetTypeName()
        if not type_name:
            continue
        if not _formatter_commands_for_type(type_name):
            continue
        error = _register_exact_type(debugger, type_name)
        if error:
            failures.append(error)
        else:
            registered.append(_canonical_type_name(type_name))

    if failures:
        result.SetError("; ".join(failures))
    elif registered and _command.strip() == "verbose":
        result.PutCString(
            "registered Protocyte formatter types: " + ", ".join(registered)
        )


def __lldb_init_module(debugger, _internal_dict):
    category = "protocyte"
    disable_command = f"type category disable {category}"
    delete_command = f"type category delete {category}"
    define_command = f"type category define {category}"
    delete_oneof_command = "command script delete protocyte-oneof"
    delete_diagnostics_command = "command script delete protocyte-formatters"
    delete_bytes_command = "command script delete protocyte-bytes"
    delete_register_type_command = "command script delete protocyte-register-type"
    delete_register_frame_types_command = (
        "command script delete protocyte-register-frame-types"
    )
    stop_hook_command = 'target stop-hook add -o "protocyte-register-frame-types"'
    commands = [
        disable_command,
        delete_command,
        define_command,
        f"type summary add -w {category} -p -F protocyte_lldb.status_summary protocyte::Status",
        f"type summary add -w {category} -p -F protocyte_lldb.error_summary protocyte::Error",
        f"type summary add -w {category} -p -F protocyte_lldb.bytes_summary '{_DEFAULT_BYTES_TYPE}'",
        f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider '{_DEFAULT_BYTES_TYPE}'",
        f"type summary add -w {category} -p -F protocyte_lldb.string_summary '{_DEFAULT_STRING_TYPE}'",
        f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider '{_DEFAULT_STRING_TYPE}'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.result_summary '^protocyte::Result<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ResultSyntheticProvider '^protocyte::Result<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.optional_summary '^protocyte::Optional<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.OptionalSyntheticProvider '^protocyte::Optional<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.box_summary '^protocyte::Box<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.PointerValueSyntheticProvider '^protocyte::Box<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.vector_summary '{_VECTOR_TYPE_REGEX}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.VectorSyntheticProvider '{_VECTOR_TYPE_REGEX}'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.bytes_summary '{_BYTES_TYPE_REGEX}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ByteSpanSyntheticProvider '{_BYTES_TYPE_REGEX}'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.string_summary '{_STRING_TYPE_REGEX}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ByteSpanSyntheticProvider '{_STRING_TYPE_REGEX}'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.span_summary '{_SPAN_TYPE_REGEX}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ByteSpanSyntheticProvider '{_SPAN_TYPE_REGEX}'",
        f"type summary add -w {category} -p -F protocyte_lldb.byte_view_summary protocyte::ByteView",
        f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider protocyte::ByteView",
        f"type summary add -w {category} -p -F protocyte_lldb.mutable_byte_view_summary protocyte::MutableByteView",
        f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider protocyte::MutableByteView",
        f"type summary add -w {category} -p -x -F protocyte_lldb.hash_map_summary '{_HASH_MAP_TYPE_REGEX}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.HashMapSyntheticProvider '{_HASH_MAP_TYPE_REGEX}'",
        f"type summary add -w {category} -p -F protocyte_lldb.slice_reader_summary protocyte::SliceReader",
        f"type summary add -w {category} -p -x -F protocyte_lldb.limited_reader_summary '^protocyte::LimitedReader<.+>$'",
        f"type summary add -w {category} -p -F protocyte_lldb.slice_writer_summary protocyte::SliceWriter",
        f"type category enable {category}",
        delete_oneof_command,
        "command script add -f protocyte_lldb.protocyte_oneof protocyte-oneof",
        delete_diagnostics_command,
        "command script add -f protocyte_lldb.protocyte_formatters protocyte-formatters",
        delete_bytes_command,
        "command script add -f protocyte_lldb.protocyte_bytes protocyte-bytes",
        delete_register_type_command,
        "command script add -f protocyte_lldb.protocyte_register_type protocyte-register-type",
        delete_register_frame_types_command,
        "command script add -f protocyte_lldb.protocyte_register_frame_types protocyte-register-frame-types",
        stop_hook_command,
    ]
    recognizer_commands = [
        "type summary add -w protocyte -p --python-function protocyte_lldb.result_summary --recognizer-function protocyte_lldb.is_result_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.ResultSyntheticProvider --recognizer-function protocyte_lldb.is_result_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.optional_summary --recognizer-function protocyte_lldb.is_optional_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.OptionalSyntheticProvider --recognizer-function protocyte_lldb.is_optional_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.box_summary --recognizer-function protocyte_lldb.is_box_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.PointerValueSyntheticProvider --recognizer-function protocyte_lldb.is_box_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.vector_summary --recognizer-function protocyte_lldb.is_vector_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.VectorSyntheticProvider --recognizer-function protocyte_lldb.is_vector_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.bytes_summary --recognizer-function protocyte_lldb.is_bytes_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.ByteSpanSyntheticProvider --recognizer-function protocyte_lldb.is_bytes_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.string_summary --recognizer-function protocyte_lldb.is_string_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.ByteSpanSyntheticProvider --recognizer-function protocyte_lldb.is_string_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.span_summary --recognizer-function protocyte_lldb.is_span_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.ByteSpanSyntheticProvider --recognizer-function protocyte_lldb.is_span_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.hash_map_summary --recognizer-function protocyte_lldb.is_hash_map_type",
        "type synthetic add -w protocyte --python-class protocyte_lldb.HashMapSyntheticProvider --recognizer-function protocyte_lldb.is_hash_map_type",
        "type summary add -w protocyte -p --python-function protocyte_lldb.limited_reader_summary --recognizer-function protocyte_lldb.is_limited_reader_type",
    ]
    error = _run_lldb_commands(
        debugger,
        commands,
        context="Protocyte formatter registration",
        ignored_errors={
            disable_command: (
                "does not exist",
                "not found",
                "invalid type category",
            ),
            delete_command: (
                "does not exist",
                "not found",
                "invalid type category",
                "cannot delete one or more categories",
            ),
            define_command: (
                "already exists",
                "exists already",
            ),
            delete_oneof_command: _SCRIPT_DELETE_IGNORED_ERRORS,
            delete_diagnostics_command: _SCRIPT_DELETE_IGNORED_ERRORS,
            delete_bytes_command: _SCRIPT_DELETE_IGNORED_ERRORS,
            delete_register_type_command: _SCRIPT_DELETE_IGNORED_ERRORS,
            delete_register_frame_types_command: _SCRIPT_DELETE_IGNORED_ERRORS,
            stop_hook_command: (
                "invalid target",
                "no target",
                "requires a target",
            ),
        },
    )
    if error:
        raise RuntimeError(error)
    recognizer_error = _run_lldb_commands(
        debugger,
        recognizer_commands,
        context="Protocyte recognizer formatter registration",
    )
    if recognizer_error and not _is_unsupported_option_error(recognizer_error):
        raise RuntimeError(recognizer_error)
