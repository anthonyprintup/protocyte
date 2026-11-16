from __future__ import annotations

import importlib.util
import itertools
import ctypes
import os
import random
import sys
import subprocess
import threading
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "parallel_probe_helpers", Path(__file__).with_name("test_output_coordinator.py")
)
assert spec and spec.loader
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)
coordinator = helpers.coordinator
commit = coordinator._load_observation_commit()
model = coordinator._load_ownership_index()
_modules = itertools.count()


@pytest.fixture(autouse=True)
def qualify_native_cases(monkeypatch):
    monkeypatch.setattr(coordinator, "_COMMITTED_INDEX_QUALIFIED", True)


@pytest.fixture
def scope(tmp_path):
    if os.name != "nt":
        pytest.skip("native root-relative comparisons require Windows")
    result = commit.WindowsObservationCommit(
        coordinator._load_path_observation(), model
    )
    try:
        result.project(tmp_path)
        # Qualify the transport separately, then use a new read set for tests.
        result.seal()
    except commit.CapabilityUnavailable as error:
        pytest.skip(str(error))
    finally:
        result.close()
    result = commit.WindowsObservationCommit(
        coordinator._load_path_observation(), model
    )
    try:
        yield result
    finally:
        result.close()
        metrics = result.metrics()
        assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]


@pytest.mark.parametrize("workers", [1, 2, 4])
@pytest.mark.parametrize("size", [0, 1, 31, 32, 33, 257])
def test_bounded_batches_preserve_order_and_retire(workers, size):
    session = commit.ProbeSession(lambda number: number % 3 == 0, workers=workers)
    try:
        assert session.compare((number, number) for number in range(size)) == list(
            range(0, size, 3)
        )
    finally:
        session.close()
    metrics = session.metrics()
    assert metrics["commit_probe_state"] == "closed"
    assert metrics["commit_probe_active"] == metrics["commit_probe_pending"] == 0
    assert metrics["commit_probe_comparisons"] == size
    assert (
        metrics["commit_probe_batches_started"]
        == metrics["commit_probe_batches_finished"]
    )
    assert metrics["commit_probe_peak_pending"] <= workers * 2
    assert metrics["commit_probe_peak_active"] <= workers
    assert metrics["commit_probe_threads"] <= workers
    with pytest.raises(commit.ObservationChanged, match="after retirement"):
        session.compare([(0, 0)])


def raw_coordinator():
    source = Path(__file__).resolve().parents[1] / "cmake/ProtocyteOutputCoordinator.py"
    specification = importlib.util.spec_from_file_location(
        f"parallel_default_{next(_modules)}", source
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


@pytest.mark.parametrize("qualified", [False, True])
@pytest.mark.parametrize("selection", [None, "auto", "reference", "REFERENCE", ""])
def test_automatic_default_and_simple_reference_escape_hatch(
    tmp_path, monkeypatch, qualified, selection
):
    module = raw_coordinator()
    monkeypatch.setattr(module, "_COMMITTED_INDEX_QUALIFIED", qualified)
    if selection is None:
        monkeypatch.delenv("PROTOCYTE_REGISTRY_VALIDATION", raising=False)
    else:
        monkeypatch.setenv("PROTOCYTE_REGISTRY_VALIDATION", selection)
    engine = module.OutputCoordinator(tmp_path / "locks")
    expected = (
        "indexed"
        if qualified and os.name == "nt" and selection not in ("reference", "REFERENCE")
        else "reference"
    )
    assert engine.registry_validation == expected


def test_invalid_default_override_is_rejected_and_explicit_reference_recovers(
    tmp_path, monkeypatch
):
    module = raw_coordinator()
    monkeypatch.setenv("PROTOCYTE_REGISTRY_VALIDATION", "unrecognized")
    locks = tmp_path / "locks"
    with pytest.raises(module.CoordinatorError, match="must be auto or reference"):
        module.OutputCoordinator(locks)
    assert not locks.exists()
    assert (
        module.OutputCoordinator(
            locks, registry_validation="reference"
        ).registry_validation
        == "reference"
    )


@pytest.mark.parametrize(
    "override",
    [
        {"commit_probe_state": "active"},
        {"commit_probe_state": "failed"},
        {"commit_probe_native_retired": False},
        {"commit_probe_native_retired": 1},
        {"commit_probe_active": 1},
        {"commit_probe_active": False},
        {"commit_probe_pending": 1},
        {"commit_probe_pending": False},
        {"commit_probe_comparisons": 1},
        {"commit_probe_comparisons": False},
    ],
)
def test_incomplete_worker_accounting_cannot_authorize_mutation(
    tmp_path, monkeypatch, override
):
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="indexed"
    )
    plan = helpers._write_plan(
        tmp_path / "plan",
        tmp_path / "generated",
        tmp_path / "build",
        ((helpers._target("worker-accounting"), "sample.protocyte.hpp"),),
    )

    def incomplete(*args, **kwargs):
        engine.validation_metrics.update(
            commit_certificate="verified",
            commit_state="closed",
            commit_handles_opened=2,
            commit_handles_closed=2,
            commit_probe_state="closed",
            commit_probe_native_retired=True,
            commit_probe_active=0,
            commit_probe_pending=0,
            commit_probe_comparisons=0,
            commit_fresh_comparisons=0,
        )
        engine.validation_metrics.update(override)
        return True

    monkeypatch.setattr(engine, "_preview_committed_index", incomplete)
    assert engine.reconcile(plan)
    assert engine.validation_metrics["authoritative"] == "reference"
    assert engine.validation_metrics["reference_result"] == "accepted"


def test_workers_overlap_and_cannot_control_the_session():
    rendezvous = threading.Barrier(4)
    entered = threading.local()
    session = None

    def compare(number):
        if not getattr(entered, "ready", False):
            entered.ready = True
            rendezvous.wait(timeout=5)
        with pytest.raises(commit.ObservationChanged, match="control used by a worker"):
            session.close()
        return False

    session = commit.ProbeSession(compare)
    try:
        assert session.compare((number, number) for number in range(256)) == []
    finally:
        session.close()
    assert session.metrics()["commit_probe_peak_active"] == 4
    assert session.metrics()["commit_probe_threads"] == 4


@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("site", ["worker", "submit-after-queue", "shutdown", "wait"])
def test_every_failure_drains_admitted_work(error_type, site):
    first_started = threading.Event()
    second_started = threading.Event()
    failed = threading.Event()
    wait_interrupted = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    errors, sessions, actual_shutdowns = [], [], []

    def compare(number):
        if number == 0:
            first_started.set()
            assert second_started.wait(5)
            if site in ("worker", "shutdown", "wait"):
                failed.set()
                raise error_type("injected worker failure")
            assert release.wait(5)
        elif number == 32:
            second_started.set()
            assert release.wait(5)
        return False

    def control():
        session = commit.ProbeSession(compare, workers=2)
        sessions.append(session)
        real_submit = session._executor.submit
        real_shutdown = session._executor.shutdown
        actual_shutdowns.append(real_shutdown)
        if site == "submit-after-queue":
            submissions = 0

            def submit(*args, **kwargs):
                nonlocal submissions
                future = real_submit(*args, **kwargs)
                submissions += 1
                if submissions == 2:
                    assert second_started.wait(5)
                    failed.set()
                    raise error_type("submit queued work before failing")
                return future

            session._executor.submit = submit
        if site == "shutdown":

            def shutdown(**kwargs):
                raise error_type("injected shutdown failure")

            session._executor.shutdown = shutdown
        if site == "wait":
            real_wait = session._condition.wait
            interrupted = False

            def wait(*args, **kwargs):
                nonlocal interrupted
                if not interrupted:
                    interrupted = True
                    wait_interrupted.set()
                    raise error_type("injected interruption while draining")
                return real_wait(*args, **kwargs)

            session._condition.wait = wait
        try:
            session.compare((number, number) for number in range(128))
        except BaseException as error:
            errors.append(error)
        finally:
            try:
                session.close()
            except BaseException:
                pass
            finished.set()

    thread = threading.Thread(target=control)
    thread.start()
    try:
        assert first_started.wait(5) and second_started.wait(5) and failed.wait(5)
        if site == "wait":
            assert wait_interrupted.wait(5)
        assert not finished.is_set(), (
            "retired a session with an admitted query still active"
        )
        assert sessions[0].metrics()["commit_probe_active"] >= 1
    finally:
        release.set()
        thread.join(timeout=10)
        for shutdown in actual_shutdowns:
            shutdown(wait=True, cancel_futures=True)
    assert not thread.is_alive() and finished.is_set()
    assert len(errors) == 1
    expected = (
        commit.ProbeCleanupFailed
        if site in ("shutdown", "wait") and error_type is RuntimeError
        else error_type
    )
    assert isinstance(errors[0], expected)
    session = sessions[0]
    assert session.metrics()["commit_probe_active"] == 0
    assert session.metrics()["commit_probe_pending"] == 0
    assert session.native_retired is True
    # Even a job hidden by a failed submit cannot read prepared facts after close.
    with pytest.raises(commit.ObservationChanged, match="after retirement"):
        session._run(object())


def test_parallel_index_matches_serial_on_randomized_ownership_and_retirement():
    def overlaps(pair):
        left, right = pair
        return (
            left.portable == right.portable
            or left.portable.startswith(right.portable + "/")
            or right.portable.startswith(left.portable + "/")
            or left.location in right.ancestors
            or right.location in left.ancestors
        )

    session = commit.ProbeSession(overlaps)
    randomizer = random.Random(54)
    try:
        for _ in range(64):
            facts, stable = {}, {}
            paths = [Path(f"path-{number}") for number in range(96)]
            for path in paths:
                parent, leaf = randomizer.randrange(8), randomizer.randrange(8)
                location = (7, parent * 8 + leaf + 2, ())
                ancestors = (location, (7, parent + 100, ()), (7, 1, ()))
                facts[path] = model.DirectoryObservation(
                    f"/p{parent}/p{leaf}", location, ancestors
                )
                stable[path] = randomizer.choice((True, False))

            class Serial:
                def is_stable(self, path):
                    return stable[path]

                def facts(self, path):
                    return facts[path]

                def overlaps(self, first, second):
                    return overlaps((facts[first], facts[second]))

            class Parallel(Serial):
                probe_session = session

                def prepare_overlap(self, first, second):
                    return facts[first], facts[second]

            entries = [
                (
                    model.Reservation(
                        randomizer.choice(("root", "staging")),
                        f"k{randomizer.randrange(8)}",
                        f"b{randomizer.randrange(2)}",
                        f"t{randomizer.randrange(2)}",
                        facts[path],
                    ),
                    path,
                    stable[path],
                )
                for path in paths[:64]
            ]
            for _ in range(16):
                arguments = dict(
                    root=randomizer.choice(paths),
                    root_key=f"k{randomizer.randrange(8)}",
                    build_id=f"b{randomizer.randrange(2)}",
                    staging=tuple(
                        (f"t{n}", randomizer.choice(paths)) for n in range(2)
                    ),
                    retiring_root_keys={f"k{randomizer.randrange(8)}"},
                )
                serial = commit.ProvisionalOwnershipIndex(model, Serial(), entries)
                parallel = commit.ProvisionalOwnershipIndex(model, Parallel(), entries)
                assert parallel.conflict(**arguments) == serial.conflict(**arguments)
    finally:
        session.close()


def test_frozen_phase_allows_only_prepared_comparisons(tmp_path, scope, monkeypatch):
    first, second = tmp_path / "missing-first", tmp_path / "missing-second"
    scope.facts(first)
    scope.facts(second)
    views = dict(scope._views)
    with scope.comparisons() as reader:
        with pytest.raises(commit.ObservationChanged):
            scope.project(first)
        with pytest.raises(commit.ObservationChanged):
            scope.seal()
        with pytest.raises(
            commit.CommitUnavailable, match="not observed before freezing"
        ):
            reader.prepare_overlap(tmp_path / "never-observed", second)
        prepared = reader.prepare_overlap(first, second)
        assert reader.probe_session.compare([(0, prepared)] * 128) == []
        assert scope._views == views
    assert reader.probe_session.metrics()["commit_probe_state"] == "closed"
    with pytest.raises(commit.ObservationChanged):
        reader.facts(first)
    with pytest.raises(commit.ObservationChanged):
        scope.facts(first)
    scope.seal()


def test_unproved_retirement_preserves_bindings_until_cleanup_retries(
    tmp_path, scope, monkeypatch
):
    first, second = tmp_path / "first", tmp_path / "second"
    scope.facts(first)
    scope.facts(second)
    with pytest.raises(commit.ProbeCleanupFailed, match="retirement is unproved"):
        with scope.comparisons() as reader:
            original = reader.probe_session.close

            def interrupted_before_retirement():
                raise KeyboardInterrupt("interrupted before the admission fence")

            monkeypatch.setattr(
                reader.probe_session, "close", interrupted_before_retirement
            )
            reader.probe_session.compare([(0, reader.prepare_overlap(first, second))])
    assert not reader.probe_session.native_retired
    assert scope._state == "comparing"
    assert not reader._closed and reader._views
    assert scope.reader.handles_opened > scope.reader.handles_closed
    with pytest.raises(commit.ProbeCleanupFailed, match="root handles cannot close"):
        scope.close()
    assert scope.reader.handles_opened > scope.reader.handles_closed
    monkeypatch.setattr(reader.probe_session, "close", original)
    scope.close()
    assert reader.probe_session.native_retired
    assert scope.reader.handles_opened == scope.reader.handles_closed


def test_impersonation_cannot_move_probes_to_a_different_context(tmp_path, scope):
    from ctypes import wintypes as w

    scope.facts(tmp_path / "missing")
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    impersonate = security.ImpersonateSelf
    impersonate.argtypes = (ctypes.c_int,)
    impersonate.restype = w.BOOL
    revert = security.RevertToSelf
    revert.argtypes = ()
    revert.restype = w.BOOL
    if not impersonate(2):  # SecurityImpersonation; only our own test-process token.
        pytest.skip("self-impersonation is unavailable")
    try:
        with pytest.raises(commit.CapabilityUnavailable, match="impersonating caller"):
            with scope.comparisons():
                pytest.fail("created workers for an impersonating caller")
        assert scope._comparison_reader is None
    finally:
        assert revert()
    # The rejection neither poisons the ordinary caller nor opens worker leases.
    with scope.comparisons() as reader:
        assert reader.probe_session.metrics()["commit_probe_threads"] == 0
    scope.seal()


@pytest.mark.parametrize("reply", ["failure", "emulated", "unknown-native"])
def test_uncertain_process_context_rejects_workers(scope, monkeypatch, reply):
    from ctypes import wintypes as w

    def machine(process, emulated, native):
        ctypes.cast(emulated, ctypes.POINTER(w.WORD)).contents.value = (
            0x14C if reply == "emulated" else 0
        )
        ctypes.cast(native, ctypes.POINTER(w.WORD)).contents.value = (
            0 if reply == "unknown-native" else 0x8664
        )
        return reply != "failure"

    monkeypatch.setattr(scope.reader._kernel, "IsWow64Process2", machine)
    with pytest.raises(
        commit.CapabilityUnavailable, match="emulated filesystem context"
    ):
        with scope.comparisons():
            pytest.fail("started a worker in an unqualified process context")
    assert scope._comparison_reader is None


@pytest.mark.parametrize("replacement", ["file", "dangling-junction"])
def test_reverse_probe_still_detects_mutation_in_parallel(
    tmp_path, scope, monkeypatch, replacement
):
    first, second = tmp_path / "missing-first", tmp_path / "missing-second"
    scope.facts(first)
    scope.facts(second)
    request = scope._views[str(first)].probe
    original = scope._probe_absence
    owner = threading.get_ident()
    changed = threading.Event()

    def mutate_after_forward(observed):
        original(observed)
        if (
            observed is request
            and threading.get_ident() != owner
            and not changed.is_set()
        ):
            changed.set()
            if replacement == "file":
                first.touch()
            else:
                target = tmp_path / "junction-target"
                target.mkdir()
                helpers._directory_link(first, target)
                target.rmdir()

    monkeypatch.setattr(scope, "_probe_absence", mutate_after_forward)
    with pytest.raises(commit.ObservationChanged):
        with scope.comparisons() as reader:
            reader.probe_session.compare([(0, reader.prepare_overlap(first, second))])
    assert changed.is_set()
    metrics = scope.metrics()
    assert metrics["commit_probe_state"] == "closed"
    assert metrics["commit_probe_active"] == metrics["commit_probe_pending"] == 0


@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_worker_failure_fallback_and_fatal_cleanup_preserve_claims(
    tmp_path, monkeypatch, cleanup_failure
):
    if os.name != "nt":
        pytest.skip("native coordinator qualification requires Windows")
    plan = helpers._write_plan(
        tmp_path / "current.plan",
        tmp_path / "generated",
        tmp_path / "build",
        ((helpers._target("parallel"), "sample.protocyte.hpp"),),
    )
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    token = engine.reconcile(plan)
    state = engine._state_directory(plan.root)
    claim = (state / "claim.json").read_bytes()
    engine.registry_validation = "indexed"
    if cleanup_failure:
        original = commit.concurrent.futures.ThreadPoolExecutor.shutdown

        def failed_shutdown(self, *args, **kwargs):
            original(self, *args, **kwargs)
            raise RuntimeError("injected executor retirement failure")

        monkeypatch.setattr(
            commit.concurrent.futures.ThreadPoolExecutor, "shutdown", failed_shutdown
        )
        monkeypatch.setattr(
            engine,
            "_validate_registry_reference",
            lambda *a, **k: pytest.fail("unsafe cleanup used reference authority"),
        )
        with pytest.raises(
            coordinator.CoordinatorError, match="could not be retired safely"
        ):
            engine.reconcile(plan)
    else:

        def failed_comparison(self, prepared):
            raise RuntimeError("injected native worker failure")

        monkeypatch.setattr(commit._FrozenComparisons, "_compare", failed_comparison)
        assert engine.reconcile(plan) == token
        assert engine.validation_metrics["fallback"] == "reference"
        assert engine.validation_metrics["reference_result"] == "accepted"
    assert (state / "claim.json").read_bytes() == claim
    metrics = engine.validation_metrics
    assert metrics["commit_probe_active"] == metrics["commit_probe_pending"] == 0
    assert metrics["commit_handles_opened"] == metrics["commit_handles_closed"]


def test_previous_helper_during_upgrade_uses_reference_without_token_rotation(
    tmp_path, monkeypatch
):
    from types import ModuleType

    source = tmp_path / "previous-observation-helper.py"
    repo = Path(__file__).resolve().parents[1]
    source.write_bytes(
        subprocess.check_output(
            ["git", "show", "8851bde:cmake/ProtocyteObservationCommit.py"], cwd=repo
        )
    )
    previous = ModuleType("previous_observation_helper")
    sys.modules[previous.__name__] = previous
    exec(compile(source.read_bytes(), str(source), "exec"), previous.__dict__)
    assert not hasattr(previous, "ProbeCleanupFailed")
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="reference"
    )
    plan = helpers._write_plan(
        tmp_path / "plan",
        tmp_path / "generated",
        tmp_path / "build",
        ((helpers._target("mixed-helper"), "sample.protocyte.hpp"),),
    )
    token = engine.reconcile(plan)
    state = engine._state_directory(plan.root)
    claim = (state / "claim.json").read_bytes()
    monkeypatch.setattr(coordinator, "_observation_commit_module", previous)
    monkeypatch.setattr(coordinator, "_load_observation_commit", lambda: previous)
    engine.registry_validation = "indexed"
    assert engine.reconcile(plan) == token
    assert engine.validation_metrics["fallback"] == "reference"
    assert engine.validation_metrics["reference_result"] == "accepted"
    assert (state / "claim.json").read_bytes() == claim
