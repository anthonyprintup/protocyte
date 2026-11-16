from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "protocyte_ownership_index_test_helpers",
    Path(__file__).with_name("test_output_coordinator.py"),
)
assert _spec is not None and _spec.loader is not None
_helpers = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _helpers
_spec.loader.exec_module(_helpers)
_directory_link = _helpers._directory_link
_target = _helpers._target
_write_plan = _helpers._write_plan
coordinator = _helpers.coordinator


model = coordinator._load_ownership_index()


def _directory(name: str, inode: int, parents: tuple[int, ...] = (1,)) -> object:
    key = (7, inode, ())
    return model.DirectoryObservation(
        name, key, (key, *((7, parent, ()) for parent in parents))
    )


def _oracle_overlap(first: object, second: object) -> bool:
    def contains(parent: str, child: str) -> bool:
        return child == parent or child.startswith(parent + "/")

    return (
        contains(first.portable, second.portable)
        or contains(second.portable, first.portable)
        or any(first.location == key for key in second.ancestors)
        or any(second.location == key for key in first.ancestors)
    )


def test_index_matches_exhaustive_geometry_across_aliases_and_missing_suffixes() -> (
    None
):
    randomizer = random.Random(5411)
    parents: dict[int, tuple[int, ...]] = {1: ()}
    for inode in range(2, 72):
        parent = randomizer.randrange(1, inode)
        parents[inode] = (parent, *parents[parent])
    observations = []
    for index in range(300):
        inode = randomizer.randrange(1, 72)
        suffix = tuple(
            randomizer.choice(("nested", "nested-other", "unicode-ü", "leaf"))
            for _ in range(randomizer.randrange(4))
        )
        alias = "alias" if index % 3 == 0 else "tree"
        name = f"/{alias}/node-{inode}" + ("/" + "/".join(suffix) if suffix else "")
        keys = tuple(
            (7, inode, suffix[:length]) for length in range(len(suffix), -1, -1)
        )
        keys += tuple((7, parent, ()) for parent in parents[inode])
        observations.append(model.DirectoryObservation(name, (7, inode, suffix), keys))
    observations.extend((_directory("", 1, ()), _directory("/tree/node-2-other", 900)))
    reservations = tuple(
        model.Reservation("root", str(index), "owner", None, facts)
        for index, facts in enumerate(observations)
    )
    index = model.OwnershipIndex(reservations)
    for facts in observations:
        expected = tuple(
            reservation
            for reservation in reservations
            if _oracle_overlap(reservation.directory, facts)
        )
        assert index.overlapping(facts) == expected


@pytest.mark.parametrize(
    (
        "current_root",
        "current_stage",
        "root_key",
        "build_id",
        "target",
        "retiring",
        "expected",
    ),
    [
        ("root", None, "new", "build", "target", set(), "root-root"),
        ("root", None, "old", "another-build", "target", set(), None),
        ("stage", None, "old", "build", "target", set(), "root-staging"),
        ("other", "root", "new", "build", "target", set(), "staging-root"),
        ("other", "stage", "old", "build", "target", set(), None),
        ("other", "stage", "new", "build", "target", {"old"}, None),
        (
            "other",
            "stage",
            "new",
            "another-build",
            "target",
            {"old"},
            "staging-staging",
        ),
        (
            "other",
            "stage",
            "new",
            "build",
            "another-target",
            {"old"},
            "staging-staging",
        ),
        ("other", "stage", "new", "build", "target", set(), "staging-staging"),
    ],
)
def test_index_preserves_ownership_and_retiring_staging_exceptions(
    current_root: str,
    current_stage: str | None,
    root_key: str,
    build_id: str,
    target: str,
    retiring: set[str],
    expected: str | None,
) -> None:
    facts = {
        "root": _directory("/reserved-output", 2),
        "stage": _directory("/stage", 3),
        "other": _directory("/other", 4),
    }
    index = model.OwnershipIndex(
        (
            model.Reservation("root", "old", "build", None, facts["root"]),
            model.Reservation("staging", "old", "build", "target", facts["stage"]),
        )
    )
    assert (
        index.conflict(
            root=facts[current_root],
            root_key=root_key,
            build_id=build_id,
            staging=() if current_stage is None else ((target, facts[current_stage]),),
            retiring_root_keys=retiring,
        )
        == expected
    )


def _plan(tmp_path: Path, name: str, root: Path | None = None) -> object:
    return _write_plan(
        tmp_path / f"{name}.plan",
        root or tmp_path / name / "generated",
        tmp_path / name / "build",
        ((_target(name), "sample.protocyte.hpp"),),
    )


def test_reference_mode_never_loads_or_consults_the_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected() -> object:
        pytest.fail("default validation loaded the experimental index")

    monkeypatch.setattr(coordinator, "_load_ownership_index", unexpected)
    engine = coordinator.OutputCoordinator(tmp_path / "locks")
    assert engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["mode"] == "reference"
    assert engine.validation_metrics["authoritative"] == "reference"


def test_shadow_authenticates_all_records_in_both_phases_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="shadow"
    )
    retained = [_plan(tmp_path, f"retained-{index}") for index in range(3)]
    engine.reconcile_set((), retained)
    expected = {engine._state_directory(plan.root) for plan in retained}
    loaded: dict[str, list[Path]] = {"preview": [], "reference": []}
    original_load = engine._load_recorded_plan
    original_initialize = engine._initialize_claim_locked

    def load(state: Path, claim: object, **kwargs: object) -> object:
        phase = "preview" if kwargs.get("_filesystem") is not None else "reference"
        if state in expected:
            loaded[phase].append(state)
        return original_load(state, claim, **kwargs)

    def initialize(state: Path, plan: object) -> None:
        assert engine.validation_metrics["reference_result"] == "accepted"
        assert engine.validation_metrics["agreement"] is True
        original_initialize(state, plan)

    monkeypatch.setattr(engine, "_load_recorded_plan", load)
    monkeypatch.setattr(engine, "_initialize_claim_locked", initialize)
    assert (
        len(
            engine.reconcile_set(
                (), [_plan(tmp_path, "first"), _plan(tmp_path, "second")]
            )
        )
        == 2
    )
    assert sorted(loaded["preview"]) == sorted(expected)
    assert sorted(loaded["reference"]) == sorted(expected)
    assert engine.validation_metrics["preview_claims"] == 3
    assert engine.validation_metrics["indexed_reservations"] == 6
    assert engine.validation_metrics["index_queries"] == 4


@pytest.mark.parametrize(
    "replacement", ["file", "root-link", "staging-link", "ancestor-link"]
)
def test_foreign_changes_after_preview_are_rejected_before_new_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    retained = _plan(tmp_path, "retained")
    current = _plan(tmp_path, "current")
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="shadow"
    )
    engine.reconcile(retained)
    changed = False

    def inject(stage: str) -> None:
        nonlocal changed
        if stage != "after-index-preview" or changed:
            return
        changed = True
        if replacement == "file":
            retained.root.touch()
        elif replacement == "ancestor-link":
            retained.root.parent.rename(tmp_path / "moved-retained")
            _directory_link(retained.root.parent, tmp_path)
        else:
            path = (
                retained.root
                if replacement == "root-link"
                else retained.targets[0].staging
            )
            _directory_link(path, tmp_path)

    monkeypatch.setattr(engine, "_inject", inject)
    with pytest.raises(
        coordinator.CoordinatorError, match="symbolic link or junction|non-directory"
    ):
        engine.reconcile(current)
    assert changed
    assert engine.validation_metrics["preview_result"] == "accepted"
    assert engine.validation_metrics["reference_result"] == "rejected"
    assert engine.validation_metrics["agreement"] is False
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1


@pytest.mark.parametrize("preview", [False, RuntimeError("injected preview error")])
def test_preview_false_positive_or_error_cannot_authorize_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, preview: object
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="shadow"
    )

    def sample(*args: object, **kwargs: object) -> bool:
        if isinstance(preview, Exception):
            raise preview
        return bool(preview)

    monkeypatch.setattr(engine, "_preview_registry_index", sample)
    with pytest.raises(
        coordinator.CoordinatorError, match="disagrees with the fresh reference"
    ):
        engine.reconcile(_plan(tmp_path, "current"))
    assert engine.validation_metrics["reference_result"] == "accepted"
    assert not list((engine.lock_root / "roots").glob("*/claim.json"))


def test_preview_false_negative_never_bypasses_reference_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="shadow"
    )
    retained = _plan(tmp_path, "retained")
    engine.reconcile(retained)
    monkeypatch.setattr(engine, "_preview_registry_index", lambda *args, **kwargs: True)
    current = _plan(tmp_path, "current", retained.root / "nested")
    with pytest.raises(coordinator.CoordinatorError, match="overlaps a root"):
        engine.reconcile(current)
    assert engine.validation_metrics["agreement"] is False
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1


def test_samples_expire_and_index_only_authorization_is_not_available(
    tmp_path: Path,
) -> None:
    sample = coordinator._SampledRegistryFilesystem(model)
    sample.project(tmp_path)
    sample.close()
    for operation in (sample.project, sample.facts, sample.path_key):
        with pytest.raises(coordinator.CoordinatorError, match="outside its preview"):
            operation(tmp_path)
    with pytest.raises(coordinator.CoordinatorError, match="outside its preview"):
        sample.same_path(tmp_path, tmp_path)
    with pytest.raises(coordinator.CoordinatorError, match="reference or shadow"):
        coordinator.OutputCoordinator(
            tmp_path / "locks", registry_validation="index-only"
        )


def test_read_only_preview_never_cleans_unclaimed_state_or_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = coordinator.OutputCoordinator(tmp_path / "locks")
    retained = _plan(tmp_path, "retained")
    engine.reconcile(retained)
    abandoned = engine.lock_root / "roots" / ("a" * 64)
    abandoned.mkdir()
    (abandoned / "snapshot.json").write_text("{}\n")
    current = _plan(tmp_path, "current")

    def mutation(*args: object, **kwargs: object) -> None:
        pytest.fail("read-only preview attempted a filesystem mutation")

    for name in ("_atomic_write", "_durable_mkdir", "_durable_rmtree"):
        monkeypatch.setattr(coordinator, name, mutation)
    assert engine._preview_registry_index((current,), set())
    assert abandoned.exists()
    assert engine.validation_metrics["preview_claims"] == 1
    assert engine.validation_metrics["preview_unclaimed_states"] == 1


def test_foreign_physical_alias_introduced_after_preview_is_not_missed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    retained = _plan(tmp_path, "retained")
    current = _plan(tmp_path, "current")
    retained.root.mkdir()
    current.root.mkdir()
    engine = coordinator.OutputCoordinator(
        tmp_path / "locks", registry_validation="shadow"
    )
    engine.reconcile(retained)
    original_lstat = Path.lstat

    def alias_lstat(path: Path) -> object:
        return original_lstat(current.root if path == retained.root else path)

    def inject(stage: str) -> None:
        if stage == "after-index-preview":
            monkeypatch.setattr(Path, "lstat", alias_lstat)

    monkeypatch.setattr(engine, "_inject", inject)
    with pytest.raises(coordinator.CoordinatorError, match="overlaps a root"):
        engine.reconcile(current)
    assert engine.validation_metrics["preview_result"] == "accepted"
    assert engine.validation_metrics["agreement"] is False
    assert len(list((engine.lock_root / "roots").glob("*/claim.json"))) == 1


@pytest.mark.parametrize("count", [16, 1024])
def test_disjoint_index_query_does_not_compare_every_reservation(
    monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    calls = 0
    original = model.DirectoryObservation.overlaps

    def overlap(first: object, second: object) -> bool:
        nonlocal calls
        calls += 1
        return original(first, second)

    monkeypatch.setattr(model.DirectoryObservation, "overlaps", overlap)
    index = model.OwnershipIndex(
        model.Reservation(
            "root",
            str(number),
            "build",
            None,
            _directory(f"/retained/{number}", number + 2),
        )
        for number in range(count)
    )
    assert not index.overlapping(_directory("/current/generated", count + 1000))
    assert calls == 0


def test_optional_index_loader_does_not_write_bytecode_into_the_package_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper_source = Path(coordinator.__file__).with_name("ProtocyteOwnershipIndex.py")
    (tmp_path / helper_source.name).write_bytes(helper_source.read_bytes())
    module_name = f"{coordinator.__name__}_ownership_index"
    monkeypatch.setitem(sys.modules, module_name, sys.modules[module_name])
    monkeypatch.setattr(
        coordinator, "__file__", str(tmp_path / "ProtocyteOutputCoordinator.py")
    )
    monkeypatch.setattr(coordinator, "_ownership_module", None)
    loaded = coordinator._load_ownership_index()
    assert loaded.OwnershipIndex(())
    assert not (tmp_path / "__pycache__").exists()


def test_shadow_cli_preserves_the_claim_token_stdout_protocol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _plan(tmp_path, "current")
    result = coordinator.main(
        [
            "reconcile",
            "--lock-root",
            str(tmp_path / "locks"),
            "--plan",
            str(tmp_path / "current.plan"),
            "--experimental-registry-index",
        ]
    )
    captured = capsys.readouterr()
    assert result == 0
    tokens = captured.out.splitlines()
    assert len(tokens) == 1 and coordinator._is_sha256(tokens[0])
    assert all(
        line.startswith("Protocyte output coordinator:")
        for line in captured.err.splitlines()
    )
