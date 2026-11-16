from __future__ import annotations

import ctypes
import importlib.util
import os
import struct
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "observation_commit_test_helpers",
    Path(__file__).with_name("test_output_coordinator.py"),
)
assert spec and spec.loader
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)
coordinator = helpers.coordinator
commit = coordinator._load_observation_commit()
native = coordinator._load_path_observation()
model = coordinator._load_ownership_index()


@pytest.fixture(autouse=True)
def qualify_native_commit_cases(monkeypatch):
    # Exercise the guarded success path only in isolated test fixtures.
    monkeypatch.setattr(coordinator, "_COMMITTED_INDEX_QUALIFIED", True)


@pytest.fixture
def native_capability(tmp_path):
    if os.name != "nt":
        pytest.skip("native commit witnesses require Windows")
    scope = commit.WindowsObservationCommit(native, model)
    try:
        scope.project(tmp_path)
        scope.seal()
    except commit.CapabilityUnavailable as error:
        pytest.skip(str(error))
    finally:
        scope.close()


def _record(usn: int, file_id: int, reason: int, major: int = 2) -> bytes:
    minimum = 60 if major == 2 else 76
    length = (minimum + 7) & ~7
    data = bytearray(length)
    struct.pack_into("<IHH", data, 0, length, major, 0)
    width = 8 if major == 2 else 16
    data[8 : 8 + width] = file_id.to_bytes(width, "little")
    offset = 24 if major == 2 else 40
    struct.pack_into("<q", data, offset, usn)
    struct.pack_into("<I", data, offset + 16, reason)
    return bytes(data)


@pytest.mark.parametrize("major", [2, 3])
def test_redacted_record_headers_can_supply_exact_positive_witnesses(
    major: int,
) -> None:
    page = struct.pack("<q", 200) + _record(100, 11, commit.CLOSE_REASON, major)
    cursor, records = commit.parse_journal_page(page)
    assert cursor == 200
    commit.verify_witnesses({100: 11}, records)


@pytest.mark.skipif(os.name != "nt", reason="DOS drive roots")
@pytest.mark.parametrize("same_root_id", [False, True])
def test_second_drive_with_duplicate_volume_serial_cannot_reuse_first_root(
    monkeypatch: pytest.MonkeyPatch, same_root_id: bool
) -> None:
    scope = object.__new__(commit.WindowsObservationCommit)
    scope._counts = defaultdict(int)
    scope._roots = {"c:\\": SimpleNamespace(guard=SimpleNamespace(volume=77))}
    scope.reader = SimpleNamespace(
        _native_name=lambda path: None, _open_existing=lambda path: 123
    )
    guard = SimpleNamespace(volume=77, file_id=1 if same_root_id else 2)
    monkeypatch.setattr(scope, "_adopt", lambda handle, **kwargs: (guard, Path("D:\\")))
    with pytest.raises(commit.CapabilityUnavailable, match="duplicate volume binding"):
        scope._root(Path("D:/generated"))
    assert list(scope._roots) == ["c:\\"]


@pytest.mark.parametrize("reason", [0, 1, 0x200, 0x1000, 0x8000, 0x10000, 0x100000])
def test_close_witness_must_not_hide_pending_changes(reason: int) -> None:
    flags = 0 if reason == 0 else commit.CLOSE_REASON | reason
    with pytest.raises(commit.ObservationChanged):
        commit.verify_witnesses({100: 11}, [commit.JournalRecord(100, 11, flags)])


@pytest.mark.parametrize(
    "records",
    [
        [],
        [commit.JournalRecord(101, 11, commit.CLOSE_REASON)],
        [commit.JournalRecord(100, 12, commit.CLOSE_REASON)],
        [commit.JournalRecord(100, 11, commit.CLOSE_REASON)] * 2,
    ],
)
def test_missing_wrong_or_duplicate_records_cannot_certify_a_read_set(records) -> None:
    with pytest.raises(commit.CommitUnavailable):
        commit.verify_witnesses({100: 11}, records)


@pytest.mark.parametrize(
    "corruption",
    ["short", "truncated", "version", "minor", "length", "name", "backward", "cursor"],
)
def test_journal_parser_fails_closed_on_unsupported_or_malformed_data(
    corruption: str,
) -> None:
    record = bytearray(_record(100, 11, commit.CLOSE_REASON))
    cursor = 200
    if corruption == "short":
        page = b"short"
    elif corruption == "truncated":
        page = struct.pack("<q", cursor) + record[:-1]
    else:
        if corruption == "version":
            struct.pack_into("<H", record, 4, 4)
        elif corruption == "minor":
            struct.pack_into("<H", record, 6, 1)
        elif corruption == "length":
            struct.pack_into("<I", record, 0, 63)
        elif corruption == "name":
            struct.pack_into("<HH", record, 56, 20, 60)
        elif corruption == "cursor":
            cursor = 100
        page = struct.pack("<q", cursor) + record
        if corruption == "backward":
            page += _record(99, 12, commit.CLOSE_REASON)
    with pytest.raises(commit.CommitUnavailable):
        commit.parse_journal_page(bytes(page))


@pytest.mark.parametrize(
    "failure",
    ["epoch", "trim", "missing", "stalled", "changed", "epoch-after", "budget"],
)
def test_commit_requires_complete_bound_witnesses_and_journal_continuity(
    failure: str,
) -> None:
    scope = object.__new__(commit.WindowsObservationCommit)
    scope._counts = defaultdict(int)
    scope.MAX_JOURNAL_BYTES = 8 if failure == "budget" else 1024
    epochs = iter(
        [
            (2 if failure == "epoch" else 1, 101 if failure == "trim" else 0, 200),
            (2 if failure == "epoch-after" else 1, 0, 200),
        ]
    )
    scope._epoch = lambda handle: next(epochs)
    records = (
        b""
        if failure in ("missing", "stalled")
        else _record(100, 11, commit.CLOSE_REASON | (1 if failure == "changed" else 0))
    )
    scope._io = lambda *args: (
        struct.pack("<q", 100 if failure == "stalled" else 200) + records
    )
    with pytest.raises((commit.CommitUnavailable, commit.ObservationChanged)):
        scope._collect_witnesses(SimpleNamespace(handle=None, epoch=1), {100: 11})


@pytest.fixture
def readset(native_capability):
    if os.name != "nt":
        pytest.skip("native commit witnesses require Windows")
    scope = commit.WindowsObservationCommit(native, model)
    try:
        yield scope
    finally:
        scope.close()
        metrics = scope.metrics()
        assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]


def test_quiet_read_set_seals_and_expires_without_pinning_user_directories(
    tmp_path: Path, readset
) -> None:
    directory = tmp_path / "existing 🧬"
    directory.mkdir()
    assert readset.project(directory) == directory
    assert not readset.overlaps(tmp_path / "missing-a", tmp_path / "missing-b")
    # Only volume roots are retained. Ordinary directory observations close now.
    roots = {id(view.guard) for view in readset._roots.values()}
    assert all(
        guard.handle is None or id(guard) in roots
        for guard in readset._objects.values()
    )
    readset.seal()
    assert readset.metrics()["commit_state"] == "sealed"
    assert readset.metrics()["commit_witnesses"] == len(readset._objects)
    with pytest.raises(commit.ObservationChanged, match="outside"):
        readset.project(directory)


def test_existing_object_delete_and_recreate_is_not_blocked_and_invalidates(
    tmp_path: Path, readset
) -> None:
    directory = tmp_path / "existing"
    directory.mkdir()
    readset.project(directory)
    directory.rmdir()
    directory.mkdir()
    with pytest.raises(commit.ObservationChanged):
        readset.seal()


def test_rename_aba_cannot_pass_even_when_name_and_identity_return(
    tmp_path: Path, readset
) -> None:
    directory, moved = tmp_path / "existing", tmp_path / "moved"
    directory.mkdir()
    readset.project(directory)
    directory.rename(moved)
    moved.rename(directory)
    with pytest.raises(commit.ObservationChanged):
        readset.seal()


def test_record_content_aba_with_restored_timestamp_invalidates(
    tmp_path: Path, readset
) -> None:
    record = tmp_path / "claim.json"
    data = b'{"value":1}\n'
    record.write_bytes(data)
    assert readset.read_json(record, "test record") == {"value": 1}
    original = record.stat()
    record.write_bytes(b'{"value":2}\n')
    record.write_bytes(data)
    os.utime(record, ns=(original.st_atime_ns, original.st_mtime_ns))
    with pytest.raises(commit.ObservationChanged):
        readset.seal()


@pytest.mark.parametrize("timing", ["before-seal", "after-version-read"])
def test_reparse_aba_from_a_preexisting_attribute_writer_cannot_certify(
    tmp_path: Path, readset, monkeypatch: pytest.MonkeyPatch, timing: str
) -> None:
    from ctypes import wintypes as w

    directory, target = tmp_path / "existing", tmp_path / "target"
    directory.mkdir()
    target.mkdir()
    create = readset.reader._kernel.CreateFileW
    create.argtypes = (
        w.LPCWSTR,
        w.DWORD,
        w.DWORD,
        w.LPVOID,
        w.DWORD,
        w.DWORD,
        w.HANDLE,
    )
    create.restype = w.HANDLE
    writer = create(str(directory), 0x100, 7, None, 3, 0x02200000, None)
    assert writer != ctypes.c_void_p(-1).value

    def reparse(set_point: bool):
        if set_point:
            substitute = ("\\??\\" + str(target)).encode("utf-16-le")
            printable = str(target).encode("utf-16-le")
            names = substitute + b"\x00\x00" + printable + b"\x00\x00"
            data = (
                struct.pack(
                    "<IHHHHHH",
                    0xA0000003,
                    8 + len(names),
                    0,
                    0,
                    len(substitute),
                    len(substitute) + 2,
                    len(printable),
                )
                + names
            )
        else:
            data = struct.pack("<IHH", 0xA0000003, 0, 0)
        buffer = ctypes.create_string_buffer(data)
        size = w.DWORD()
        if not readset._control(
            writer,
            0x900A4 if set_point else 0x900AC,
            buffer,
            len(data),
            None,
            0,
            ctypes.byref(size),
            None,
        ):
            error = ctypes.get_last_error()
            if error in (1, 5, 50, 1314):
                pytest.skip(f"attribute reparse operation unavailable: error {error}")
            raise ctypes.WinError(error)

    try:
        # Prime the same reason on a handle that stays open across registration.
        reparse(True)
        reparse(False)
        readset.project(directory)
        if timing == "before-seal":
            reparse(True)
            reparse(False)
        else:
            identity = readset.facts(directory).location[:2]
            original_version = readset._version
            changed = False

            def change_after_version(handle):
                nonlocal changed
                version = original_version(handle)
                if not changed and readset._identity(handle) == identity:
                    changed = True
                    reparse(True)
                    reparse(False)
                return version

            monkeypatch.setattr(readset, "_version", change_after_version)
        assert not directory.is_junction()
        match = (
            "close witness contains accumulated changes"
            if timing == "after-version-read"
            else None
        )
        with pytest.raises(commit.ObservationChanged, match=match):
            readset.seal()
        if timing == "after-version-read":
            assert changed
    finally:
        if directory.is_junction():
            reparse(False)
        assert readset.reader._close(writer)


@pytest.mark.parametrize("mutation", ["rename-aba", "record-content-aba"])
def test_native_close_witness_catches_changes_after_the_version_read(
    tmp_path: Path, readset, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    path = tmp_path / "observed"
    if mutation == "rename-aba":
        path.mkdir()
        readset.project(path)
        guard = readset._view(path).guard
    else:
        path.write_bytes(b'{"value":1}\n')
        readset.read_json(path, "test record")
        guard = readset._view(path, leaf_may_be_file=True).guard
    identity = guard.volume, guard.file_id
    original_version = readset._version
    changed = False

    def change_after_version(handle):
        nonlocal changed
        version = original_version(handle)
        if not changed and readset._identity(handle) == identity:
            changed = True
            if mutation == "rename-aba":
                moved = path.with_name("moved")
                path.rename(moved)
                moved.rename(path)
            else:
                original = path.stat()
                path.write_bytes(b'{"value":2}\n')
                path.write_bytes(b'{"value":1}\n')
                os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        return version

    monkeypatch.setattr(readset, "_version", change_after_version)
    with pytest.raises(
        commit.ObservationChanged, match="close witness contains accumulated changes"
    ):
        readset.seal()
    assert changed


@pytest.mark.parametrize("phase", ["comparison", "seal"])
def test_missing_component_creation_is_freshly_checked(
    tmp_path: Path, readset, phase: str
) -> None:
    missing = tmp_path / "missing"
    assert not readset.overlaps(missing, tmp_path / "other")
    missing.mkdir()
    with pytest.raises(commit.ObservationChanged):
        readset.overlaps(
            missing, tmp_path / "other"
        ) if phase == "comparison" else readset.seal()


def test_case_aliases_fall_back_without_resetting_prior_versions(
    tmp_path: Path, readset
) -> None:
    directory = tmp_path / "MixedCase"
    directory.mkdir()
    first = readset.facts(directory)
    start = readset._objects[first.location[:2]].start_usn
    with pytest.raises(commit.CapabilityUnavailable, match="noncanonical"):
        readset.facts(tmp_path / "mixedcase")
    assert readset._objects[first.location[:2]].start_usn == start


def test_overlapping_read_sets_invalidate_rather_than_certify_changed_versions(
    tmp_path: Path, readset
) -> None:
    other = commit.WindowsObservationCommit(native, model)
    try:
        readset.project(tmp_path)
        other.project(tmp_path)
        with pytest.raises(commit.ObservationChanged):
            readset.seal()
        other.seal()
    finally:
        other.close()


def _plan(tmp_path: Path, name: str):
    return helpers._write_plan(
        tmp_path / f"{name}.plan",
        tmp_path / name / "generated",
        tmp_path / name / "build",
        ((helpers._target(name), "sample.protocyte.hpp"),),
    )


@pytest.mark.parametrize("phase", ["comparison", "seal"])
def test_dangling_junction_cannot_masquerade_as_a_missing_component(
    tmp_path: Path, readset, phase: str
) -> None:
    missing, target = tmp_path / "missing", tmp_path / "target"
    target.mkdir()
    readset.project(missing / "generated")
    helpers._directory_link(missing, target)
    target.rmdir()
    assert missing.is_junction()
    with pytest.raises(commit.ObservationChanged):
        readset.overlaps(
            missing / "generated", tmp_path / "other"
        ) if phase == "comparison" else readset.seal()


def test_default_never_loads_commit_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        coordinator,
        "_load_observation_commit",
        lambda: pytest.fail("default loaded commit reader"),
    )
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    assert engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["authoritative"] == "reference"


def test_negative_observations_are_refreshed_for_the_reverse_direction(
    tmp_path: Path, readset, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "first-missing", tmp_path / "second-missing"
    readset.project(first)
    readset.project(second)
    original = readset._probe_absence
    probes = 0

    def replace_after_forward(request):
        nonlocal probes
        original(request)
        probes += 1
        if probes == 2:
            first.touch()

    monkeypatch.setattr(readset, "_probe_absence", replace_after_forward)
    with pytest.raises(commit.ObservationChanged):
        readset.overlaps(first, second)


@pytest.mark.parametrize("restore", [False, True])
def test_case_mode_changes_preserve_exact_bindings_without_versioned_flags(
    tmp_path: Path, readset, restore: bool
) -> None:
    from ctypes import wintypes as w

    directory = tmp_path / "case-mode"
    directory.mkdir()
    create = readset.reader._kernel.CreateFileW
    create.argtypes = (
        w.LPCWSTR,
        w.DWORD,
        w.DWORD,
        w.LPVOID,
        w.DWORD,
        w.DWORD,
        w.HANDLE,
    )
    create.restype = w.HANDLE
    writer = create(str(directory), 0x100, 7, None, 3, 0x02200000, None)
    assert writer != ctypes.c_void_p(-1).value
    set_info = readset.reader._kernel.SetFileInformationByHandle
    set_info.argtypes = (w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD)
    set_info.restype = w.BOOL

    def set_mode(enabled):
        flag = w.DWORD(int(enabled))
        if not set_info(writer, 23, ctypes.byref(flag), ctypes.sizeof(flag)):
            error = ctypes.get_last_error()
            if error in (1, 5, 50, 87, 1314):
                pytest.skip(f"case sensitivity mutation unavailable: error {error}")
            raise ctypes.WinError(error)

    try:
        readset.project(directory)
        before = readset._objects[readset.facts(directory).location[:2]].start_usn
        set_mode(True)
        if restore:
            set_mode(False)
        # On NTFS this mode can change without advancing the USN. The read set
        # must not depend on mode stability: it only reuses exact name bindings.
        with readset._lease(readset._view(directory).guard) as handle:
            versioned = readset._version(handle) != before
        if versioned:
            with pytest.raises(commit.ObservationChanged):
                readset.seal()
        else:
            readset.seal()
    finally:
        try:
            set_mode(False)
        finally:
            assert readset.reader._close(writer)


@pytest.mark.parametrize("positive_mask", range(8))
def test_partitioned_index_matches_reference_ownership_and_retirement(
    positive_mask: int,
) -> None:
    names = ("root", "stage", "other")
    facts = {}
    for number, name in enumerate(names, start=2):
        key = (7, number, ())
        facts[name] = model.DirectoryObservation("/" + name, key, (key, (7, 1, ())))

    class Filesystem:
        def is_stable(self, path):
            return bool(positive_mask & (1 << names.index(path)))

        def facts(self, path):
            return facts[path]

        def overlaps(self, first, second):
            # Independent exhaustive predicate, as used by the reference path.
            left, right = facts[first], facts[second]
            return (
                left.portable == right.portable
                or left.portable.startswith(right.portable + "/")
                or right.portable.startswith(left.portable + "/")
                or left.location in right.ancestors
                or right.location in left.ancestors
            )

    filesystem = Filesystem()
    reservations = (
        model.Reservation("root", "old", "build", None, facts["root"]),
        model.Reservation("staging", "old", "build", "target", facts["stage"]),
    )
    cases = (
        ("root", None, "new", "build", "target", set(), "root-root"),
        ("root", None, "old", "other-build", "target", set(), None),
        ("stage", None, "old", "build", "target", set(), "root-staging"),
        ("other", "root", "new", "build", "target", set(), "staging-root"),
        ("other", "stage", "old", "build", "target", set(), None),
        ("other", "stage", "new", "build", "target", {"old"}, None),
        ("other", "stage", "new", "other-build", "target", {"old"}, "staging-staging"),
        ("other", "stage", "new", "build", "other-target", {"old"}, "staging-staging"),
        ("other", "stage", "new", "build", "target", set(), "staging-staging"),
    )
    for root, stage, root_key, build, target, retiring, expected in cases:
        index = commit.ProvisionalOwnershipIndex(
            model,
            filesystem,
            tuple(
                (reservation, path, filesystem.is_stable(path))
                for reservation, path in zip(reservations, names)
            ),
        )
        assert (
            index.conflict(
                root=root,
                root_key=root_key,
                build_id=build,
                staging=() if stage is None else ((target, stage),),
                retiring_root_keys=retiring,
            )
            == expected
        )


@pytest.mark.parametrize(
    "error",
    [commit.CapabilityUnavailable("no capability"), RuntimeError("unexpected failure")],
)
@pytest.mark.parametrize("mode", ["commit-shadow", "indexed"])
def test_unavailable_or_failed_commit_uses_reference_and_preserves_existing_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception, mode: str
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    plan = _plan(tmp_path, "current")
    token = engine.reconcile(plan)
    state = engine._state_directory(plan.root)
    claim_bytes = (state / "claim.json").read_bytes()

    def unavailable(*args, **kwargs):
        raise error

    monkeypatch.setattr(engine, "_preview_committed_index", unavailable)
    engine.registry_validation = mode
    assert engine.reconcile(plan) == token
    assert (state / "claim.json").read_bytes() == claim_bytes
    assert engine.validation_metrics["fallback"] == "reference"
    assert engine.validation_metrics["commit_certificate"] == "unverified"
    assert engine.validation_metrics["reference_result"] == "accepted"


def test_commit_conflict_disagreement_cannot_initialize_a_new_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    engine.reconcile(_plan(tmp_path, "retained"))
    monkeypatch.setattr(
        engine, "_preview_committed_index", lambda *args, **kwargs: False
    )
    engine.registry_validation = "commit-shadow"
    with pytest.raises(coordinator.CoordinatorError, match="disagrees"):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["reference_result"] == "accepted"
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1


@pytest.mark.parametrize(
    "certificate",
    [
        {},
        {"commit_certificate": "verified", "commit_state": "closed"},
        {
            "commit_certificate": "unverified",
            "commit_state": "closed",
            "commit_handles_opened": 2,
            "commit_handles_closed": 2,
        },
        {
            "commit_certificate": "verified",
            "commit_state": "sealed",
            "commit_handles_opened": 2,
            "commit_handles_closed": 2,
        },
        {
            "commit_certificate": "verified",
            "commit_state": "closed",
            "commit_handles_opened": 2,
            "commit_handles_closed": 1,
        },
        {
            "commit_certificate": "verified",
            "commit_state": "closed",
            "commit_handles_opened": 0,
            "commit_handles_closed": 0,
        },
        {
            "commit_certificate": "verified",
            "commit_state": "closed",
            "commit_handles_opened": 1,
            "commit_handles_closed": True,
        },
    ],
)
def test_indexed_incomplete_certificate_runs_reference_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, certificate: dict
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="indexed"
    )
    plan = _plan(tmp_path, "current")

    def incomplete(*args, **kwargs):
        engine.validation_metrics.update(
            commit_cleanup_failed=False,
            commit_probe_state="closed",
            commit_probe_native_retired=True,
            commit_probe_active=0,
            commit_probe_pending=0,
            commit_probe_comparisons=0,
            commit_fresh_comparisons=0,
        )
        engine.validation_metrics.update(certificate)
        return True

    monkeypatch.setattr(engine, "_preview_committed_index", incomplete)
    original = engine._initialize_claim_locked

    def initialize(state, current):
        assert engine.validation_metrics["fallback"] == "reference"
        assert engine.validation_metrics["reference_result"] == "accepted"
        original(state, current)

    monkeypatch.setattr(engine, "_initialize_claim_locked", initialize)
    assert engine.reconcile(plan)


def test_indexed_conflict_uses_reference_diagnostics_and_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="indexed"
    )
    monkeypatch.setattr(
        engine, "_preview_committed_index", lambda *args, **kwargs: False
    )
    retained = _plan(tmp_path, "retained")
    assert engine.reconcile(retained)
    assert engine.validation_metrics["reference_result"] == "accepted"
    retained.root.touch()
    with pytest.raises(coordinator.CoordinatorError, match="non-directory"):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["reference_result"] == "rejected"
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1


def test_failed_promotion_gate_blocks_api_and_cli_before_index_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(coordinator, "_COMMITTED_INDEX_QUALIFIED", False)
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="indexed"
    )

    def forbidden(*args, **kwargs):
        pytest.fail("unqualified index was consulted")

    monkeypatch.setattr(engine, "_preview_committed_index", forbidden)
    assert engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["index_authorization_blocked"]
    assert engine.validation_metrics["authoritative"] == "reference"
    assert engine.validation_metrics["reference_result"] == "accepted"
    rejected = tmp_path / "unqualified-cli-locks"
    assert (
        coordinator.main(
            [
                "reconcile",
                "--lock-root",
                str(rejected),
                "--experimental-committed-index",
            ]
        )
        == 1
    )
    assert "not qualified for consumer use" in capsys.readouterr().err
    assert not rejected.exists()


@pytest.mark.skipif(os.name != "nt", reason="native commit witnesses require Windows")
def test_indexed_verified_readset_closes_before_mutation_without_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_capability
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    retained = [_plan(tmp_path, f"retained-{number}") for number in range(3)]
    engine.reconcile_set((), retained)
    engine.registry_validation = "indexed"

    def forbidden(*args, **kwargs):
        pytest.fail("verified native read set unexpectedly ran reference")

    monkeypatch.setattr(engine, "_validate_registry_reference", forbidden)
    original = engine._initialize_claim_locked

    def initialize(state, plan):
        metrics = engine.validation_metrics
        assert metrics["authoritative"] == "index"
        assert metrics["commit_certificate"] == "verified"
        assert metrics["commit_state"] == "closed"
        assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]
        assert metrics["commit_claims_checked"] == 3
        assert metrics["commit_records_read"] == 6
        original(state, plan)

    monkeypatch.setattr(engine, "_initialize_claim_locked", initialize)
    assert engine.reconcile(_plan(tmp_path, "current"))


@pytest.mark.skipif(os.name != "nt", reason="native commit witnesses require Windows")
def test_indexed_abandoned_state_falls_back_to_reference_cleanup(
    tmp_path: Path, native_capability
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="indexed"
    )
    abandoned = engine.lock_root / "roots" / ("a" * 64)
    abandoned.mkdir(parents=True)
    (abandoned / "snapshot.json").write_bytes(b"{}")
    assert engine.reconcile(_plan(tmp_path, "current"))
    assert not abandoned.exists()
    assert engine.validation_metrics["fallback"] == "reference"
    assert engine.validation_metrics["reference_result"] == "accepted"


@pytest.mark.skipif(os.name != "nt", reason="native commit witnesses require Windows")
@pytest.mark.parametrize("replacement", ["file", "junction"])
def test_indexed_success_keeps_fresh_mutation_time_path_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_capability, replacement: str
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    engine.reconcile(_plan(tmp_path, "retained"))
    current = _plan(tmp_path, "current")
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sample.protocyte.hpp"
    sentinel.write_bytes(b"// preserve external output\n")
    engine.registry_validation = "indexed"
    validate = engine._validate_registry

    def change_after_validation(*args, **kwargs):
        validate(*args, **kwargs)
        assert engine.validation_metrics["authoritative"] == "index"
        assert engine.validation_metrics["commit_state"] == "closed"
        if replacement == "file":
            current.root.touch()
        else:
            helpers._directory_link(current.root, outside)

    monkeypatch.setattr(engine, "_validate_registry", change_after_validation)
    with pytest.raises(
        coordinator.CoordinatorError, match="non-directory|symbolic link or junction"
    ):
        engine.reconcile(current)
    assert sentinel.read_bytes() == b"// preserve external output\n"
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows observer coordination")
def test_independent_registries_serialize_observers_and_release_before_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import concurrent.futures
    import contextlib
    import threading

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    first = coordinator.OutputCoordinator(
        tmp_path / "first", registry_validation="indexed"
    )
    second = coordinator.OutputCoordinator(
        tmp_path / "second", registry_validation="indexed"
    )
    assert first._observation_lock().path == second._observation_lock().path
    entered, attempted, release = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    order = []
    actual_lock = second._observation_lock

    @contextlib.contextmanager
    def second_lock():
        attempted.set()
        with actual_lock():
            yield

    def observe_first(*args, **kwargs):
        order.append("first")
        entered.set()
        assert release.wait(5)
        return False

    def observe_second(*args, **kwargs):
        order.append("second")
        return False

    def reference_first(*args, **kwargs):
        # The second observer can enter while the first reference is active.
        assert second_entered.wait(5)

    second_entered = threading.Event()

    def reference_second(*args, **kwargs):
        second_entered.set()

    monkeypatch.setattr(first, "_preview_committed_index", observe_first)
    monkeypatch.setattr(second, "_preview_committed_index", observe_second)
    monkeypatch.setattr(second, "_observation_lock", second_lock)
    monkeypatch.setattr(first, "_validate_registry_reference", reference_first)
    monkeypatch.setattr(second, "_validate_registry_reference", reference_second)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(first._validate_registry, [])
        assert entered.wait(5)
        two = pool.submit(second._validate_registry, [])
        try:
            assert attempted.wait(5)
            assert order == ["first"]
        finally:
            release.set()
        one.result(timeout=10)
        two.result(timeout=10)
    assert order == ["first", "second"]


@pytest.mark.parametrize(
    "other_flag",
    [
        "--experimental-registry-index",
        "--experimental-native-observation",
        "--experimental-committed-index",
    ],
)
def test_commit_flag_rejects_other_experiments_before_mutation(
    tmp_path: Path, capsys, other_flag: str
) -> None:
    locks = tmp_path / "locks"
    assert (
        coordinator.main(
            [
                "reconcile",
                "--lock-root",
                str(locks),
                "--experimental-observation-commit",
                other_flag,
            ]
        )
        == 1
    )
    assert "choose one experimental" in capsys.readouterr().err
    assert not locks.exists()


@pytest.mark.skipif(os.name != "nt", reason="native commit witnesses require Windows")
def test_commit_shadow_authenticates_records_closes_scopes_then_uses_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_capability
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    engine.reconcile_set((), [_plan(tmp_path, f"retained-{n}") for n in range(3)])
    engine.registry_validation = "commit-shadow"
    initialize = engine._initialize_claim_locked

    def checked(state, plan):
        assert engine.validation_metrics["reference_result"] == "accepted"
        assert engine.validation_metrics["commit_certificate"] == "verified"
        assert engine.validation_metrics["commit_state"] == "closed"
        initialize(state, plan)

    monkeypatch.setattr(engine, "_initialize_claim_locked", checked)
    assert engine.reconcile(_plan(tmp_path, "current"))
    metrics = engine.validation_metrics
    assert metrics["agreement"] is True
    assert metrics["commit_claims_checked"] == 3
    assert metrics["commit_records_read"] == 6
    assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]


@pytest.mark.skipif(os.name != "nt", reason="native commit witnesses require Windows")
def test_changed_but_safe_observation_falls_back_without_breaking_a_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_capability
) -> None:
    retained = _plan(tmp_path, "retained")
    engine = coordinator.OutputCoordinator(tmp_path / "locks")
    engine.reconcile(retained)
    engine.registry_validation = "commit-shadow"

    def inject(phase):
        if phase == "before-observation-commit":
            retained.root.mkdir()

    monkeypatch.setattr(engine, "_inject", inject)
    assert engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["fallback"] == "reference"
    assert engine.validation_metrics["reference_result"] == "accepted"


@pytest.mark.parametrize(
    "phase", ["before-observation-commit", "after-observation-commit"]
)
@pytest.mark.skipif(os.name != "nt", reason="native commit witnesses require Windows")
def test_foreign_change_before_or_after_commit_cannot_bypass_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, native_capability
) -> None:
    retained = _plan(tmp_path, "retained")
    engine = coordinator.OutputCoordinator(tmp_path / "locks")
    engine.reconcile(retained)
    engine.registry_validation = "commit-shadow"

    def inject(current):
        if current == phase:
            retained.root.touch()

    monkeypatch.setattr(engine, "_inject", inject)
    with pytest.raises(coordinator.CoordinatorError, match="non-directory"):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["reference_result"] == "rejected"
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1
