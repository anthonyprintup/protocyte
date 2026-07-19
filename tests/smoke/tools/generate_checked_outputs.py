from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.message import DecodeError
from protocyte import __version__


ROOT = Path(__file__).resolve().parents[3]
SMOKE_PROTO_DIR = ROOT / "tests" / "smoke" / "proto"
PROTOCYTE_PROTO_DIR = ROOT / "src" / "protocyte" / "proto"
PROTOBUF_VERSION_MARKER = ".protocyte-protobuf-version"


def _load_cmake_string(variable: str) -> str:
    cmake_text = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    match = re.search(
        rf'set\(\s*{re.escape(variable)}\s*"([^"]+)"',
        cmake_text,
        re.MULTILINE,
    )
    if match is None:
        raise RuntimeError(f"failed to read {variable} from CMakeLists.txt")
    return match.group(1)


def _load_exact_dev_dependency_version(package: str) -> str:
    with (ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)
    prefix = f"{package}=="
    matches = [
        dependency.removeprefix(prefix)
        for dependency in pyproject["dependency-groups"]["dev"]
        if dependency.startswith(prefix)
    ]
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(
            f"pyproject.toml must pin exactly one {package} development dependency"
        )
    return matches[0]


PINNED_PROTOC_VERSION = _load_cmake_string("PROTOCYTE_PROTOBUF_VERSION")
PINNED_CLANG_FORMAT_VERSION = _load_exact_dev_dependency_version("clang-format")


@dataclass(frozen=True)
class GenerationSpec:
    source: str
    options: tuple[str, ...] = ()


GENERATION_SPECS = (
    GenerationSpec("example.proto", ("runtime=emit",)),
    GenerationSpec("compat.proto", ("namespace_prefix=protocyte_smoke",)),
    GenerationSpec("cross_package.proto"),
    GenerationSpec("proto2_required.proto"),
    GenerationSpec("reserved_identifiers.proto"),
)


def main() -> int:
    try:
        clang_format = _resolve_smoke_clang_format()
        clang_format_config = _resolve_smoke_clang_format_config()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    out_dir = Path(__file__).resolve().parents[1] / "generated"
    error = _regenerate_checked_outputs(out_dir, clang_format, clang_format_config)
    if error is not None:
        print(error, file=sys.stderr)
        return 1
    return 0


def _regenerate_checked_outputs(
    out_dir: Path,
    clang_format: str,
    clang_format_config: Path,
) -> str | None:
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    _recover_interrupted_checked_output_swap(out_dir)
    transaction = _create_checked_output_transaction(out_dir, "transaction")
    try:
        staged_out_dir = transaction / "generated"
        staged_out_dir.mkdir()
        error = _write_checked_outputs(
            staged_out_dir,
            clang_format,
            clang_format_config,
        )
        if error is not None:
            return error

        _swap_checked_outputs(out_dir, staged_out_dir, transaction)
        return None
    finally:
        _checked_output_swap_phase("before_cleanup")
        _remove_checked_output_path(transaction)
        _checked_output_swap_phase("after_cleanup")


def _checked_output_swap_phase(_phase: str) -> None:
    """Test seam for process interruptions between atomic filesystem operations."""


def _checked_output_path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _remove_checked_output_path(path: Path) -> None:
    if not _checked_output_path_exists(path):
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def _checked_output_rollback_path(out_dir: Path) -> Path:
    return out_dir.with_name(f".{out_dir.name}.protocyte-rollback")


def _create_checked_output_transaction(out_dir: Path, purpose: str) -> Path:
    # Path.mkdir uses the parent directory's normal ACL inheritance. tempfile's
    # Windows directories intentionally use a private DACL, which must never be
    # moved into the checked-out tree as the live generated directory.
    while True:
        transaction = out_dir.with_name(
            f".{out_dir.name}.protocyte-{purpose}-{uuid.uuid4().hex}"
        )
        try:
            transaction.mkdir()
        except FileExistsError:
            continue
        return transaction


def _restore_checked_output_rollback(out_dir: Path, rollback: Path) -> None:
    recovery = _create_checked_output_transaction(out_dir, "recovery")
    displaced = recovery / "interrupted-output"
    try:
        if _checked_output_path_exists(out_dir):
            out_dir.replace(displaced)
        rollback.replace(out_dir)
    finally:
        # Recovery is already durable once rollback.replace succeeds. Cleanup
        # must not mask the original interruption or endanger the restored tree.
        try:
            _remove_checked_output_path(recovery)
        except OSError:
            pass


def _recover_interrupted_checked_output_swap(out_dir: Path) -> None:
    rollback = _checked_output_rollback_path(out_dir)
    if _checked_output_path_exists(rollback):
        _restore_checked_output_rollback(out_dir, rollback)


def _swap_checked_outputs(
    out_dir: Path,
    staged_out_dir: Path,
    transaction: Path,
) -> None:
    rollback = _checked_output_rollback_path(out_dir)
    discard = transaction / "previous"
    had_previous = _checked_output_path_exists(out_dir)
    if _checked_output_path_exists(rollback):
        raise RuntimeError(f"unrecovered checked-output rollback exists: {rollback}")

    try:
        _checked_output_swap_phase("before_backup")
        if had_previous:
            out_dir.replace(rollback)
        _checked_output_swap_phase("after_backup")

        _checked_output_swap_phase("before_promote")
        staged_out_dir.replace(out_dir)
        _checked_output_swap_phase("after_promote")

        _checked_output_swap_phase("before_commit")
        if had_previous:
            # This atomic rename is the commit point. Once rollback disappears,
            # cleanup may be interrupted without making the live tree ambiguous.
            rollback.replace(discard)
        _checked_output_swap_phase("after_commit")
    except BaseException:
        if had_previous:
            if not _checked_output_path_exists(rollback) and _checked_output_path_exists(
                discard
            ):
                discard.replace(rollback)
            if _checked_output_path_exists(rollback):
                _restore_checked_output_rollback(out_dir, rollback)
        elif _checked_output_path_exists(out_dir) and not _checked_output_path_exists(
            staged_out_dir
        ):
            try:
                out_dir.replace(staged_out_dir)
            except OSError:
                pass
        raise


def _write_checked_outputs(
    out_dir: Path,
    clang_format: str,
    clang_format_config: Path,
) -> str | None:
    try:
        protoc = _resolve_smoke_protoc()
        plugin = _resolve_smoke_plugin()
        protobuf_import_dir = _resolve_protobuf_import_dir(protoc)
    except FileNotFoundError as exc:
        return str(exc)
    tool_error = _verify_smoke_tools(protoc, plugin, Path(clang_format))
    if tool_error is not None:
        return tool_error

    format_options = (
        f"clang_format={Path(clang_format).as_posix()}",
        f"clang_format_config={clang_format_config.as_posix()}",
    )
    common_arguments = (
        f"--proto_path={SMOKE_PROTO_DIR.as_posix()}",
        f"--proto_path={PROTOCYTE_PROTO_DIR.as_posix()}",
        f"--proto_path={protobuf_import_dir.as_posix()}",
    )

    for spec in GENERATION_SPECS:
        parameter = ",".join((*spec.options, *format_options))
        encoded_parameter = parameter.encode("utf-8").hex()
        arguments = (
            *common_arguments,
            f"--plugin=protoc-gen-protocyte={plugin.as_posix()}",
            f"--protocyte_out=_protocyte_options_hex={encoded_parameter}:{out_dir.as_posix()}",
            spec.source,
        )
        error = _run_protoc(
            protoc,
            arguments,
            response_file=out_dir.parent / f"generate-{spec.source}.rsp",
        )
        if error is not None:
            return error

    descriptor_set_path = out_dir.parent / "compat-descriptor-set.pb"
    error = _run_protoc(
        protoc,
        (
            *common_arguments,
            "--include_source_info",
            f"--descriptor_set_out={descriptor_set_path.as_posix()}",
            "compat.proto",
        ),
        response_file=out_dir.parent / "describe-compat.rsp",
    )
    if error is not None:
        return error

    try:
        descriptor_set = descriptor_pb2.FileDescriptorSet.FromString(
            descriptor_set_path.read_bytes()
        )
    except (OSError, DecodeError) as exc:
        return f"failed to read the canonical compat descriptor set: {exc}"
    compat_descriptor = next(
        (file for file in descriptor_set.file if file.name == "compat.proto"),
        None,
    )
    if compat_descriptor is None:
        return "canonical compat descriptor set does not contain compat.proto"

    compat_cases_path = out_dir / "compat_cases.hpp"
    compat_cases_path.write_text(
        compat_cases_header(compat_descriptor),
        encoding="utf-8",
        newline="\n",
    )
    _clang_format_file(compat_cases_path, clang_format, clang_format_config)
    return None


def _run_protoc(
    protoc: Path,
    arguments: tuple[str, ...],
    *,
    response_file: Path,
) -> str | None:
    response_file.write_text("\n".join((*arguments, "")), encoding="utf-8", newline="\n")
    result = subprocess.run(
        [str(protoc), f"@{response_file}"],
        cwd=SMOKE_PROTO_DIR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return None

    stdout = result.stdout.strip() or "<no standard output>"
    stderr = result.stderr.strip() or "<no standard error>"
    return (
        f"official protoc failed while processing {response_file.name}\n"
        f"protoc: {protoc}\n"
        f"exit code: {result.returncode}\n\n"
        f"standard output:\n{stdout}\n\n"
        f"standard error:\n{stderr}"
    )


def _verify_smoke_tools(
    protoc: Path,
    plugin: Path,
    clang_format: Path,
) -> str | None:
    commands = (
        (protoc, f"libprotoc {PINNED_PROTOC_VERSION}", True),
        (plugin, __version__, False),
        (
            clang_format,
            f"clang-format version {PINNED_CLANG_FORMAT_VERSION}",
            True,
        ),
    )
    for executable, expected, allow_suffix in commands:
        try:
            result = subprocess.run(
                [str(executable), "--version"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            return f"failed to execute smoke generation tool {executable}: {exc}"
        reported = result.stdout.strip()
        matches = reported == expected or (
            allow_suffix and reported.startswith(f"{expected} ")
        )
        if result.returncode != 0 or not matches:
            return (
                f"smoke generation tool is incompatible: {executable}\n"
                f"expected version output: {expected!r}\n"
                f"reported version output: {reported!r}\n"
                f"exit code: {result.returncode}"
            )
    return None


def _resolve_smoke_protoc() -> Path:
    configured = os.environ.get("PROTOCYTE_SMOKE_PROTOC") or os.environ.get(
        "PROTOCYTE_CI_PROTOC_EXECUTABLE"
    )
    if configured:
        protoc = Path(configured).resolve()
        if protoc.is_file():
            return protoc
        raise FileNotFoundError(f"configured protoc does not exist: {protoc}")

    executable = shutil.which("protoc")
    if executable:
        return Path(executable).resolve()
    raise FileNotFoundError(
        "official protoc was not found. Set PROTOCYTE_SMOKE_PROTOC or install protoc."
    )


def _resolve_smoke_plugin() -> Path:
    configured = os.environ.get("PROTOCYTE_SMOKE_PLUGIN")
    if configured:
        plugin = Path(configured).resolve()
        if plugin.is_file():
            return plugin
        raise FileNotFoundError(f"configured Protocyte plugin does not exist: {plugin}")

    executable = shutil.which("protoc-gen-protocyte")
    if executable:
        return Path(executable).resolve()
    raise FileNotFoundError(
        "protoc-gen-protocyte was not found. Set PROTOCYTE_SMOKE_PLUGIN or run the generator with 'uv run'."
    )


def _resolve_protobuf_import_dir(protoc: Path) -> Path:
    install_root = protoc.parent.parent.resolve()
    paired_import_dir = (install_root / "include").resolve()
    configured = os.environ.get("PROTOCYTE_SMOKE_PROTOBUF_IMPORT_DIR")
    if configured and Path(configured).resolve() != paired_import_dir:
        raise FileNotFoundError(
            "canonical smoke generation requires the protobuf import tree shipped "
            f"with the selected protoc: expected {paired_import_dir}, got "
            f"{Path(configured).resolve()}"
        )

    marker = install_root / PROTOBUF_VERSION_MARKER
    if not marker.is_file():
        raise FileNotFoundError(
            f"selected protoc is missing the repository installer marker: {marker}. "
            "Provision it with .github/scripts/install_protoc.py."
        )
    installed_version = marker.read_text(encoding="utf-8").strip()
    if installed_version != PINNED_PROTOC_VERSION:
        raise FileNotFoundError(
            "selected protoc/import installation does not match the repository pin: "
            f"expected {PINNED_PROTOC_VERSION}, marker reports {installed_version!r}"
        )

    descriptor = paired_import_dir / "google" / "protobuf" / "descriptor.proto"
    if not descriptor.is_file():
        raise FileNotFoundError(
            "the import tree paired with the selected protoc does not contain "
            f"google/protobuf/descriptor.proto: {paired_import_dir}"
        )
    return paired_import_dir


def _resolve_smoke_clang_format() -> str:
    override = os.environ.get("PROTOCYTE_SMOKE_CLANG_FORMAT")
    if override:
        executable = Path(override).resolve()
        if executable.is_file():
            return executable.as_posix()
        raise FileNotFoundError(
            f"configured canonical clang-format does not exist: {executable}"
        )

    for command in ("clang-format", "clang-format.exe"):
        resolved = shutil.which(command)
        if resolved:
            return Path(resolved).as_posix()

    for candidate in _clang_format_candidates():
        if candidate.is_file():
            return candidate.as_posix()

    raise FileNotFoundError(
        "clang-format was not found. Set PROTOCYTE_SMOKE_CLANG_FORMAT or install clang-format."
    )


def _resolve_smoke_clang_format_config() -> Path:
    override = os.environ.get("PROTOCYTE_SMOKE_CLANG_FORMAT_CONFIG")
    config = Path(override) if override else ROOT / ".clang-format"
    if config.is_file():
        return config

    raise FileNotFoundError(f"clang-format config was not found: {config.as_posix()}")


def _clang_format_candidates() -> list[Path]:
    candidates: list[Path] = []
    if os.name == "nt":
        for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
            prefix = os.environ.get(env_name)
            if prefix:
                candidates.append(Path(prefix) / "LLVM" / "bin" / "clang-format.exe")
        return candidates

    if sys.platform == "darwin":
        return [
            Path("/opt/homebrew/opt/llvm/bin/clang-format"),
            Path("/usr/local/opt/llvm/bin/clang-format"),
        ]

    candidates.extend(sorted(Path("/usr/lib").glob("llvm-*/bin/clang-format"), reverse=True))
    candidates.extend([Path("/usr/local/bin/clang-format"), Path("/usr/bin/clang-format")])
    return candidates


def _clang_format_file(path: Path, clang_format: str, clang_format_config: Path) -> None:
    subprocess.run(
        [clang_format, f"-style=file:{clang_format_config.as_posix()}", "-i", path.as_posix()],
        check=True,
    )


def compat_cases_header(file: descriptor_pb2.FileDescriptorProto) -> str:
    def encode_varint(value: int) -> bytes:
        out = bytearray()
        while value > 0x7F:
            out.append((value & 0x7F) | 0x80)
            value >>= 7
        out.append(value)
        return bytes(out)

    def key(field_number: int, wire_type: int) -> bytes:
        return encode_varint((field_number << 3) | wire_type)

    def length_delimited_field(field_number: int, payload: bytes) -> bytes:
        return key(field_number, 2) + encode_varint(len(payload)) + payload

    def int32_field(field_number: int, value: int) -> bytes:
        return key(field_number, 0) + encode_varint(value)

    def string_field(field_number: int, value: str) -> bytes:
        return length_delimited_field(field_number, value.encode("utf-8"))

    def map_str_int32_entry(key_value: str, value: int, *, extra: bytes = b"") -> bytes:
        return length_delimited_field(
            27,
            string_field(1, key_value) + extra + int32_field(2, value),
        )

    def map_int32_str_entry(
        key_value: int | None = None,
        value: str | None = None,
    ) -> bytes:
        payload = b""
        if key_value is not None:
            payload += int32_field(1, key_value)
        if value is not None:
            payload += string_field(2, value)
        return length_delimited_field(28, payload)

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file)
    message_desc = pool.FindMessageTypeByName("test.compat.EncodingMatrix")
    message_cls = message_factory.GetMessageClass(message_desc)

    cases: list[tuple[str, bytes]] = []
    cases.append(("empty", message_cls().SerializeToString()))

    message = message_cls()
    message.f_int32 = -(2**31)
    message.f_int64 = -(2**63)
    message.f_uint32 = (2**32) - 1
    message.f_uint64 = (2**64) - 1
    message.f_sint32 = -17
    message.f_sint64 = -17000000000
    message.f_bool = True
    message.mode = 2
    cases.append(("varint", message.SerializeToString()))

    message = message_cls()
    message.f_fixed32 = 0x11223344
    message.f_fixed64 = 0x1122334455667788
    message.f_sfixed32 = -1234567
    message.f_sfixed64 = -1234567890123
    message.f_float = -0.0
    message.f_double = 123.5
    cases.append(("fixed", message.SerializeToString()))

    message = message_cls()
    message.f_string = "smoke"
    message.f_bytes = bytes([0x00, 0x01, 0x7F, 0x80, 0xFF])
    message.nested.value = 417
    message.nested.label = "nested"
    cases.append(("length_delimited", message.SerializeToString()))

    message = message_cls()
    message.r_int32_unpacked.extend([-1, 0, 150])
    message.r_int32_packed.extend([-1, 0, 150])
    message.r_double.extend([23.5, -0.0])
    cases.append(("repeated", message.SerializeToString()))

    message = message_cls()
    message.oneof_string = "oneof-str"
    cases.append(("oneof_string", message.SerializeToString()))

    message = message_cls()
    message.oneof_int32 = -2701
    cases.append(("oneof_int32", message.SerializeToString()))

    message = message_cls()
    message.oneof_nested.value = 90210
    message.oneof_nested.label = "inner"
    cases.append(("oneof_nested", message.SerializeToString()))

    message = message_cls()
    message.oneof_bytes = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    cases.append(("oneof_bytes", message.SerializeToString()))

    message = message_cls()
    message.opt_int32 = -99
    message.opt_string = "opt"
    cases.append(("optional_case", message.SerializeToString()))

    message = message_cls()
    message.map_str_int32["map-key"] = 301
    message.map_int32_str[302] = "map-val"
    cases.append(("map_runtime", message.SerializeToString()))

    cases.append(
        ("map_duplicate_key", map_str_int32_entry("dup", 1) + map_str_int32_entry("dup", 2))
    )
    cases.append(("map_default_entries", map_int32_str_entry() + map_int32_str_entry(7)))
    cases.append(
        (
            "map_unknown_entry_field",
            map_str_int32_entry("mystery", 33, extra=int32_field(9, 123)),
        )
    )
    cases.append(
        (
            "mixed_repeated_numeric",
            int32_field(18, 1)
            + length_delimited_field(18, encode_varint(2) + encode_varint(3))
            + length_delimited_field(19, encode_varint(4))
            + int32_field(19, 5),
        )
    )
    cases.append(
        (
            "unknown_fields",
            int32_field(99, 123)
            + length_delimited_field(100, b"skip-me")
            + key(101, 5)
            + bytes([0x44, 0x33, 0x22, 0x11])
            + int32_field(1, 321),
        )
    )

    lines = [
        "#pragma once",
        "",
        "#include <array>",
        "#include <cstddef>",
        "",
        "namespace compat_cases {",
        "",
    ]
    for name, payload in cases:
        lines.append(
            f"inline constexpr ::std::array<unsigned char, {len(payload)}> {name} {{"
        )
        if payload:
            row = ", ".join(f"0x{byte:02x}" for byte in payload)
            lines.append(f"    {row},")
        lines.append("};")
        lines.append("")
    lines.append("} // namespace compat_cases")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
