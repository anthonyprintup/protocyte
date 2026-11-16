from __future__ import annotations

import importlib.util
import ctypes
import os
import struct
import sys
from pathlib import Path

import pytest


_spec = importlib.util.spec_from_file_location(
    "path_observation_test_helpers",
    Path(__file__).with_name("test_output_coordinator.py"),
)
assert _spec is not None and _spec.loader is not None
_helpers = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _helpers
_spec.loader.exec_module(_helpers)
coordinator = _helpers.coordinator
native = coordinator._load_path_observation()


@pytest.fixture
def observer():
    if os.name != "nt":
        pytest.skip("native no-reparse opens require Windows")
    reader = native.FreshPathObserver()
    try:
        yield reader
    finally:
        reader.close()
        assert reader.handles_opened == reader.handles_closed


def _plan(tmp_path: Path, name: str):
    return _helpers._write_plan(
        tmp_path / f"{name}.plan",
        tmp_path / name / "generated",
        tmp_path / name / "build",
        ((_helpers._target(name), "sample.protocyte.hpp"),),
    )


@pytest.mark.parametrize("missing_depth", [0, 1, 6])
def test_native_projection_matches_reference_for_existing_and_missing_paths(
    tmp_path: Path, observer, missing_depth: int
) -> None:
    existing = tmp_path / "mixed Case ü 🧬"
    existing.mkdir()
    path = existing.joinpath(*(f"missing-{n}" for n in range(missing_depth)))
    assert observer.project(path) == coordinator.project_path(path)
    assert observer.handles_opened == observer.handles_closed
    assert observer.project(path) == coordinator.project_path(path)
    assert observer.projections == 2


def test_native_observations_do_not_cache_absence_or_existing_identity(
    tmp_path: Path, observer
) -> None:
    path = tmp_path / "changing"
    assert observer.project(path) == path
    opened = observer.open_calls
    path.mkdir()
    assert observer.project(path) == path
    assert observer.open_calls > opened
    path.rmdir()
    path.write_text("foreign file")
    with pytest.raises(native.UnsafeObservation, match="non-directory"):
        observer.project(path)


def test_native_projection_distinguishes_regular_file_leaf_from_ancestor(
    tmp_path: Path, observer
) -> None:
    path = tmp_path / "sample.json"
    path.write_text("{}")
    assert observer.project(path, leaf_may_be_file=True) == path
    for candidate in (path, path / "nested"):
        with pytest.raises((native.UnsafeObservation, OSError)):
            observer.project(candidate)


def test_native_reparse_traversal_is_rejected_at_leaf_and_ancestor(
    tmp_path: Path, observer
) -> None:
    target = tmp_path / "ordinary"
    target.mkdir()
    link = tmp_path / "link"
    _helpers._directory_link(link, target)
    for path in (link, link / "missing", link / "missing" / "leaf"):
        with pytest.raises((native.UnsafeObservation, OSError)):
            observer.project(path)


def test_native_rejects_missing_ancestor_replaced_by_junction_on_next_call(
    tmp_path: Path, observer
) -> None:
    path = tmp_path / "missing" / "generated"
    assert observer.project(path) == path
    outside = tmp_path / "outside"
    outside.mkdir()
    _helpers._directory_link(path.parent, outside)
    with pytest.raises((native.UnsafeObservation, OSError)):
        observer.project(path)


def test_readonly_handle_cannot_be_treated_as_a_reparse_stability_lease(
    tmp_path: Path, observer
) -> None:
    """Counterexample to promoting share-restricted handles into cached authority."""
    from ctypes import wintypes as w

    victim, target = tmp_path / "victim", tmp_path / "target"
    victim.mkdir()
    target.mkdir()
    create = observer._kernel.CreateFileW
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
    control = observer._kernel.DeviceIoControl
    control.argtypes = (
        w.HANDLE,
        w.DWORD,
        w.LPVOID,
        w.DWORD,
        w.LPVOID,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
        w.LPVOID,
    )
    control.restype = w.BOOL
    invalid = ctypes.c_void_p(-1).value
    handles = []
    try:
        # Denying write/delete sharing does not constrain attribute-only access.
        pin = create(str(victim), 0x80, 1, None, 3, 0x02200000, None)
        assert pin != invalid
        handles.append(pin)
        writer = create(str(victim), 0x100, 7, None, 3, 0x02200000, None)
        assert writer != invalid
        handles.append(writer)
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
        buffer = ctypes.create_string_buffer(data)
        returned = w.DWORD()
        if not control(
            writer, 0x900A4, buffer, len(data), None, 0, ctypes.byref(returned), None
        ):
            error = ctypes.get_last_error()
            if error in (1, 5, 50, 1314):
                pytest.skip(
                    f"attribute-only reparse conversion unavailable: error {error}"
                )
            raise ctypes.WinError(error)
        assert victim.is_junction()
        with pytest.raises((native.UnsafeObservation, OSError)):
            observer.project(victim)
    finally:
        for handle in reversed(handles):
            assert observer._close(handle)
        if victim.is_junction():
            victim.rmdir()


def test_observer_releases_handles_on_failure_and_rejects_use_after_close(
    tmp_path: Path, observer, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("injected description failure")

    monkeypatch.setattr(observer, "_describe", fail)
    with pytest.raises(RuntimeError, match="description failure"):
        observer.project(tmp_path)
    assert observer.handles_opened == observer.handles_closed
    observer.close()
    with pytest.raises(native.UnsafeObservation, match="outside its scope"):
        observer.project(tmp_path)


def test_unexpected_success_status_closes_its_native_handle(
    tmp_path: Path, observer, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = observer._open

    def informational(*args):
        assert original(*args) == 0
        return 1

    monkeypatch.setattr(observer, "_open", informational)
    with pytest.raises(native.UnsafeObservation, match="unsupported result"):
        observer.project(tmp_path)
    assert observer.handles_opened == observer.handles_closed == 1


def test_permission_error_is_not_cached_or_reinterpreted_as_absence(
    tmp_path: Path, observer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(observer, "_open", lambda *args: -1073741790)  # ACCESS_DENIED
    with pytest.raises(PermissionError):
        observer.project(tmp_path)
    assert observer.open_calls == 1
    assert observer.handles_opened == 0


@pytest.mark.parametrize(
    "name",
    ["relative", "C:\\data:stream", "\\\\server\\share\\folder", "\\\\?\\C:\\folder"],
)
def test_unsupported_names_cannot_acquire_native_authority(name: str) -> None:
    with pytest.raises(native.ObservationUnavailable):
        native.FreshPathObserver._native_name(Path(name))


def test_default_validation_never_loads_native_observer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected():
        pytest.fail("reference validation loaded the native observer")

    monkeypatch.setattr(coordinator, "_load_path_observation", unexpected)
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    assert engine.reconcile(_plan(tmp_path, "current"))


def test_native_shadow_authenticates_all_records_and_reference_remains_authority(
    tmp_path: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("native no-reparse opens require Windows")
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="native-shadow"
    )
    engine.reconcile_set((), [_plan(tmp_path, "first"), _plan(tmp_path, "second")])
    assert engine.reconcile(_plan(tmp_path, "current"))
    metrics = engine.validation_metrics
    assert metrics["authoritative"] == "reference"
    assert metrics["agreement"] is True
    assert metrics["native_claims_checked"] == 2
    assert metrics["native_handles_opened"] == metrics["native_handles_closed"]


def test_native_capability_failure_uses_reference_without_migration_or_new_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable():
        raise native.ObservationUnavailable("injected unsupported filesystem")

    monkeypatch.setattr(native, "FreshPathObserver", unavailable)
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="native-shadow"
    )
    assert engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["fallback"] == "reference"
    assert engine.validation_metrics["agreement"] is None


def test_extended_namespace_upgrade_preserves_claim_through_reference_fallback(
    tmp_path: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("explicit Windows namespace paths require Windows")
    root = Path("\\\\?\\" + str(tmp_path / "generated"))
    plan = _helpers._write_plan(
        tmp_path / "extended.plan",
        root,
        tmp_path / "build",
        ((_helpers._target("extended"), "sample.protocyte.hpp"),),
    )
    locks = tmp_path / "locks"
    reference = coordinator.OutputCoordinator(locks, registry_validation="reference")
    token = reference.reconcile(plan)
    before = (reference._state_directory(plan.root) / "claim.json").read_bytes()
    observed = coordinator.OutputCoordinator(locks, registry_validation="native-shadow")
    assert observed.reconcile(plan) == token
    assert observed.validation_metrics["fallback"] == "reference"
    assert (reference._state_directory(plan.root) / "claim.json").read_bytes() == before


def test_native_sample_error_cannot_authorize_even_if_reference_accepts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken():
        raise RuntimeError("injected observer failure")

    monkeypatch.setattr(native, "FreshPathObserver", broken)
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="native-shadow"
    )
    with pytest.raises(coordinator.CoordinatorError, match="disagrees"):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["reference_result"] == "accepted"
    assert not list((engine.lock_root / "roots").glob("*/claim.json"))


def test_native_scope_close_error_still_runs_reference_before_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name != "nt":
        pytest.skip("native no-reparse opens require Windows")
    original = native.FreshPathObserver.close

    def broken_close(self):
        original(self)
        raise RuntimeError("injected scope close failure")

    monkeypatch.setattr(native.FreshPathObserver, "close", broken_close)
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="native-shadow"
    )
    with pytest.raises(coordinator.CoordinatorError, match="disagrees"):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["reference_result"] == "accepted"
    assert not list((engine.lock_root / "roots").glob("*/claim.json"))


def test_foreign_replacement_after_native_phase_is_rejected_before_new_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name != "nt":
        pytest.skip("native no-reparse opens require Windows")
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="native-shadow"
    )
    retained = _plan(tmp_path, "retained")
    engine.reconcile(retained)

    def replace(stage: str):
        if stage == "after-native-observation":
            retained.root.touch()

    monkeypatch.setattr(engine, "_inject", replace)
    with pytest.raises(coordinator.CoordinatorError, match="non-directory"):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["preview_result"] == "accepted"
    assert engine.validation_metrics["reference_result"] == "rejected"
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1
