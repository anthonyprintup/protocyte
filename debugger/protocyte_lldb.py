"""LLDB data formatters for Protocyte runtime types."""

from __future__ import annotations

import os
import string as _string
import sys


def _quote_path(path):
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


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


def write_smoke_lldbinit():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    formatter_path = os.path.join(repo_root, "debugger", "protocyte_lldb.py")
    smoke_lldbinit = os.path.join(repo_root, "smoke", ".lldbinit")
    content = "\n".join(
        [
            f"command script import {_quote_path(formatter_path)}",
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
        out.append(char if char in _string.printable and char not in "\r\n\t\x0b\x0c" else ".")
    return "".join(out)


def _hex_preview(data):
    return " ".join(f"{byte:02x}" for byte in data)


def _bytes_summary_from_span(value, data_value, size_value):
    data, size, address = _read_byte_span(value, data_value, size_value)
    suffix = " ..." if size > len(data) else ""
    if address == 0 and size != 0:
        return f"size={size}, data=null"
    return f"size={size}, hex=[{_hex_preview(data)}{suffix}], ascii=\"{_ascii_preview(data)}{suffix}\""


def _vector_storage(value):
    return _child(value, "data_"), _child(value, "size_"), _child(value, "capacity_")


def _bytes_storage(value):
    vector = _child(value, "bytes_")
    return _vector_storage(vector)


def _string_storage(value):
    bytes_value = _child(value, "bytes_")
    return _bytes_storage(bytes_value)


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
    if typename.startswith("protocyte::Bytes<") or typename in ("protocyte::ByteView", "protocyte::MutableByteView"):
        return bytes_summary(value, None) if typename.startswith("protocyte::Bytes<") else byte_view_summary(value, None)
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
    raw = value.GetNonSyntheticValue()
    children = []
    for index in range(raw.GetNumChildren()):
        child = raw.GetChildAtIndex(index)
        name = child.GetName() or f"[{index}]"
        children.append(_renamed_value(value, child, f"raw.{name}"))
    return children


def _raw_child_index(children, name):
    for index, child in enumerate(children):
        if child.GetName() == name:
            return index
    return -1


def status_summary(value, _internal_dict):
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
    code = _child(value, "code")
    code_name = code.GetValue() if code.IsValid() else None
    offset = _unsigned(_child(value, "offset"), 0)
    field = _unsigned(_child(value, "field_number"), 0)
    return f"code={code_name or 'error'}, offset={offset}, field={field}"


def result_summary(value, _internal_dict):
    ok = _bool(_child(value, "ok_"))
    if ok:
        return "ok"
    return "err, " + error_summary(_child(value, "error_"), _internal_dict)


def optional_summary(value, _internal_dict):
    return "some" if _bool(_child(value, "has_")) else "none"


def ref_summary(value, _internal_dict):
    ptr = _child(value, "ptr_")
    address = _pointer_value(ptr)
    return f"value=0x{address:x}" if address else "value=null"


def box_summary(value, _internal_dict):
    ptr = _child(value, "ptr_")
    address = _pointer_value(ptr)
    return f"value=0x{address:x}" if address else "value=null"


def vector_summary(value, _internal_dict):
    _data, size, capacity = _vector_storage(value)
    return f"size={_unsigned(size, 0)}, capacity={_unsigned(capacity, 0)}"


def bytes_summary(value, _internal_dict):
    data, size, _capacity = _bytes_storage(value)
    return _bytes_summary_from_span(value, data, size)


def string_summary(value, _internal_dict):
    data_value, size_value, _capacity = _string_storage(value)
    data, size, address = _read_byte_span(value, data_value, size_value)
    suffix = " ..." if size > len(data) else ""
    if address == 0 and size != 0:
        return f"size={size}, data=null"
    text = data.decode("utf-8", errors="replace")
    return f"size={size}, value=\"{text}{suffix}\", hex=[{_hex_preview(data)}{suffix}]"


def byte_view_summary(value, _internal_dict):
    return _bytes_summary_from_span(value, _child(value, "data"), _child(value, "size"))


def mutable_byte_view_summary(value, _internal_dict):
    return byte_view_summary(value, _internal_dict)


def hash_map_summary(value, _internal_dict):
    size = _child(value, "size_")
    buckets = _child(value, "buckets_")
    _data, bucket_count, _capacity = _vector_storage(buckets)
    return f"size={_unsigned(size, 0)}, buckets={_unsigned(bucket_count, 0)}"


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
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
        self.data, self.size_value, _capacity = _vector_storage(self.value)
        self.size = _unsigned(self.size_value, 0)
        self.element_type = _pointee_type(self.data)
        self.element_size = self.element_type.GetByteSize() if self.element_type.IsValid() else 0
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        return self.size + len(self.raw_children)

    def get_child_index(self, name):
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return self.size + raw_index
        if name.startswith("[") and name.endswith("]"):
            try:
                return int(name[1:-1])
            except ValueError:
                return -1
        return -1

    def get_child_at_index(self, index):
        if self.size <= index < self.size + len(self.raw_children):
            return self.raw_children[index - self.size]
        if index < 0 or index >= self.size or self.element_size == 0:
            return lldb.SBValue()
        address = _pointer_value(self.data) + index * self.element_size
        return self.value.CreateValueFromAddress(f"[{index}]", address, self.element_type)

    def has_children(self):
        return True


class ByteSpanSyntheticProvider:
    def __init__(self, value, _internal_dict):
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
        typename = self.value.GetTypeName() or ""
        if typename.startswith("protocyte::Bytes<"):
            self.data, self.size_value, _capacity = _bytes_storage(self.value)
        elif typename.startswith("protocyte::String<"):
            self.data, self.size_value, _capacity = _string_storage(self.value)
        else:
            self.data = _child(self.value, "data")
            self.size_value = _child(self.value, "size")
        self.size = _unsigned(self.size_value, 0)
        self.element_type = _pointee_type(self.data)
        self.element_size = self.element_type.GetByteSize() if self.element_type.IsValid() else 1
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        return self.size + len(self.raw_children)

    def get_child_index(self, name):
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return self.size + raw_index
        if name.startswith("[") and name.endswith("]"):
            try:
                return int(name[1:-1])
            except ValueError:
                return -1
        return -1

    def get_child_at_index(self, index):
        if self.size <= index < self.size + len(self.raw_children):
            return self.raw_children[index - self.size]
        if index < 0 or index >= self.size:
            return lldb.SBValue()
        address = _pointer_value(self.data) + index * self.element_size
        return self.value.CreateValueFromAddress(f"[{index}]", address, self.element_type)

    def has_children(self):
        return True


class PointerValueSyntheticProvider:
    def __init__(self, value, _internal_dict):
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
        if (self.value.GetTypeName() or "").startswith("protocyte::Box<"):
            self.ptr = _child(self.value, "ptr_")
        else:
            self.ptr = _child(self.value, "ptr_")
        self.pointee_type = _pointee_type(self.ptr)
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        return (1 if _pointer_value(self.ptr) != 0 and self.pointee_type.IsValid() else 0) + len(self.raw_children)

    def get_child_index(self, name):
        value_count = 1 if _pointer_value(self.ptr) != 0 and self.pointee_type.IsValid() else 0
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return value_count + raw_index
        return 0 if name == "value" else -1

    def get_child_at_index(self, index):
        value_count = 1 if _pointer_value(self.ptr) != 0 and self.pointee_type.IsValid() else 0
        if value_count <= index < value_count + len(self.raw_children):
            return self.raw_children[index - value_count]
        if index != 0 or value_count == 0:
            return lldb.SBValue()
        return self.value.CreateValueFromAddress("value", _pointer_value(self.ptr), self.pointee_type)

    def has_children(self):
        return True


class ResultSyntheticProvider:
    def __init__(self, value, _internal_dict):
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
        self.ok = _bool(_child(self.value, "ok_"))
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        return 1 + len(self.raw_children)

    def get_child_index(self, name):
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return 1 + raw_index
        if name == "value" and self.ok:
            return 0
        if name == "error" and not self.ok:
            return 0
        return -1

    def get_child_at_index(self, index):
        if 1 <= index < 1 + len(self.raw_children):
            return self.raw_children[index - 1]
        if index != 0:
            return lldb.SBValue()
        if self.ok:
            return _child(self.value, "value_")
        return _child(self.value, "error_")

    def has_children(self):
        return True


class OptionalSyntheticProvider:
    def __init__(self, value, _internal_dict):
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
        self.has_value = _bool(_child(self.value, "has_"))
        self.storage = _child(self.value, "storage_")
        try:
            self.value_type = self.value.GetType().GetTemplateArgumentType(0)
        except Exception:
            self.value_type = lldb.SBType()
        self.raw_children = _raw_children(self.value)

    def num_children(self):
        return (1 if self.has_value and self.value_type.IsValid() else 0) + len(self.raw_children)

    def get_child_index(self, name):
        value_count = 1 if self.has_value and self.value_type.IsValid() else 0
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return value_count + raw_index
        return 0 if name == "value" and value_count else -1

    def get_child_at_index(self, index):
        value_count = 1 if self.has_value and self.value_type.IsValid() else 0
        if value_count <= index < value_count + len(self.raw_children):
            return self.raw_children[index - value_count]
        if index != 0 or value_count == 0:
            return lldb.SBValue()
        return self.value.CreateValueFromAddress("value", self.storage.GetAddress(), self.value_type)

    def has_children(self):
        return True


class HashMapSyntheticProvider:
    def __init__(self, value, _internal_dict):
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
        self.entries = []
        self.raw_children = _raw_children(self.value)
        buckets = _child(self.value, "buckets_")
        data, bucket_count_value, _capacity = _vector_storage(buckets)
        bucket_count = _unsigned(bucket_count_value, 0)
        bucket_type = _pointee_type(data)
        bucket_size = bucket_type.GetByteSize() if bucket_type.IsValid() else 0
        base = _pointer_value(data)
        if base == 0 or bucket_size == 0:
            return
        for bucket_index in range(bucket_count):
            bucket = self.value.CreateValueFromAddress(f"bucket[{bucket_index}]", base + bucket_index * bucket_size, bucket_type)
            if not _bool(_child(bucket, "occupied")):
                continue
            key = _optional_payload(_child(bucket, "key"), "key")
            value = _optional_payload(_child(bucket, "value"), f"{_value_label(key)} =>")
            if value.IsValid():
                self.entries.append(value)

    def num_children(self):
        return len(self.entries) + len(self.raw_children)

    def get_child_index(self, name):
        raw_index = _raw_child_index(self.raw_children, name)
        if raw_index >= 0:
            return len(self.entries) + raw_index
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
        if len(self.entries) <= index < len(self.entries) + len(self.raw_children):
            return self.raw_children[index - len(self.entries)]
        if index < 0 or index >= len(self.entries):
            return lldb.SBValue()
        return self.entries[index]

    def has_children(self):
        return True


class GeneratedMessageOneofSyntheticProvider:
    def __init__(self, value, _internal_dict):
        self.value = value.GetNonSyntheticValue()
        self.update()

    def update(self):
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
                self.children.append(_renamed_value(self.value, payload if payload.IsValid() else case_field, prefix or case_field_name))
                continue
            payload = _oneof_payload(self.value, prefix, case_name)
            if not payload.IsValid():
                payload = _child(self.value, f"{prefix}_{case_name}_")
            if not payload.IsValid():
                self.children.append(_renamed_value(self.value, case_field, f"{prefix}: {case_name}"))
                continue
            self.children.append(_renamed_value(self.value, payload, f"{prefix}: {case_name}"))
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
    parts = []
    value = value.GetNonSyntheticValue()
    for case_field_name in _case_field_names(value):
        prefix = _oneof_prefix(case_field_name)
        case_name = _case_name(_child(value, case_field_name))
        parts.append(f"{prefix}={case_name}")
    return ", ".join(parts) if parts else None


def register_oneof_formatters(debugger, regex):
    category = "protocyte-oneof"
    commands = [
        f"type category define {category}",
        f"type summary add -w {category} -p -x -F protocyte_lldb.oneof_summary '{regex}'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.GeneratedMessageOneofSyntheticProvider '{regex}'",
        f"type category enable {category}",
    ]
    return _run_lldb_commands(debugger, commands, context="Protocyte oneof formatter registration")


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


def __lldb_init_module(debugger, _internal_dict):
    category = "protocyte"
    delete_command = f"type category delete {category}"
    commands = [
        delete_command,
        f"type category define {category}",
        f"type summary add -w {category} -p -F protocyte_lldb.status_summary protocyte::Status",
        f"type summary add -w {category} -p -F protocyte_lldb.error_summary protocyte::Error",
        f"type summary add -w {category} -p -x -F protocyte_lldb.result_summary '^protocyte::Result<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ResultSyntheticProvider '^protocyte::Result<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.optional_summary '^protocyte::Optional<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.OptionalSyntheticProvider '^protocyte::Optional<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.ref_summary '^protocyte::Ref<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.PointerValueSyntheticProvider '^protocyte::Ref<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.box_summary '^protocyte::Box<.+,.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.PointerValueSyntheticProvider '^protocyte::Box<.+,.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.vector_summary '^protocyte::Vector<.+,.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.VectorSyntheticProvider '^protocyte::Vector<.+,.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.bytes_summary '^protocyte::Bytes<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ByteSpanSyntheticProvider '^protocyte::Bytes<.+>$'",
        f"type summary add -w {category} -p -x -F protocyte_lldb.string_summary '^protocyte::String<.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.ByteSpanSyntheticProvider '^protocyte::String<.+>$'",
        f"type summary add -w {category} -p -F protocyte_lldb.byte_view_summary protocyte::ByteView",
        f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider protocyte::ByteView",
        f"type summary add -w {category} -p -F protocyte_lldb.mutable_byte_view_summary protocyte::MutableByteView",
        f"type synthetic add -w {category} -l protocyte_lldb.ByteSpanSyntheticProvider protocyte::MutableByteView",
        f"type summary add -w {category} -p -x -F protocyte_lldb.hash_map_summary '^protocyte::HashMap<.+,.+,.+>$'",
        f"type synthetic add -w {category} -x -l protocyte_lldb.HashMapSyntheticProvider '^protocyte::HashMap<.+,.+,.+>$'",
        f"type summary add -w {category} -p -F protocyte_lldb.slice_reader_summary protocyte::SliceReader",
        f"type summary add -w {category} -p -x -F protocyte_lldb.limited_reader_summary '^protocyte::LimitedReader<.+>$'",
        f"type summary add -w {category} -p -F protocyte_lldb.slice_writer_summary protocyte::SliceWriter",
        f"type category enable {category}",
        "command script add -f protocyte_lldb.protocyte_oneof protocyte-oneof",
    ]
    error = _run_lldb_commands(
        debugger,
        commands,
        context="Protocyte formatter registration",
        ignored_errors={
            delete_command: (
                "does not exist",
                "not found",
                "invalid type category",
            ),
        },
    )
    if error:
        raise RuntimeError(error)
