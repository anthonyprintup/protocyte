"""Offline protocol-v1 upgrade/rollback and crash-recovery qualification.

Run with Python 3.12+ from a checkout containing the pinned public source blob
and preservation checkpoint. Every case uses a fresh private registry. No consumer
registry or remote service is accessed. Publish upgrade-results.json only; the
fixture records and subprocess logs can contain private paths and claim tokens.
"""

from __future__ import annotations

import ast
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work", type=Path, help="new private result/fixture directory"
    )
    options = parser.parse_args()
    REPO = Path(__file__).resolve().parents[1]
    WORK = (
        options.work.absolute()
        if options.work
        else Path(tempfile.mkdtemp(prefix="protocyte-upgrade-"))
    )
    if options.work:
        WORK.mkdir(parents=True, exist_ok=False)
    LEGACY = WORK / "legacy/ProtocyteOutputCoordinator.py"
    CURRENT = REPO / "cmake/ProtocyteOutputCoordinator.py"
    LEGACY.parent.mkdir()
    LEGACY.write_bytes(
        subprocess.check_output(
            [
                "git",
                "show",
                "25f1660190d3d1015fef3955814c8c737bd686c5",
            ],
            cwd=REPO,
        )
    )
    assert (
        hashlib.sha256(LEGACY.read_bytes()).hexdigest()
        == "2ff54b69242d46eb8e35a52d30b32bc9afd815c00b6c0abeb8765d6fe7ddbb85"
    )
    IMPLEMENTATION = (
        CURRENT,
        *(
            CURRENT.with_name(name)
            for name in (
                "ProtocyteOwnershipIndex.py",
                "ProtocytePathObservation.py",
                "ProtocyteObservationCommit.py",
            )
        ),
    )
    EXPECTED_SOURCES = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in IMPLEMENTATION
    }

    def load(name: str, script: Path):
        spec = importlib.util.spec_from_file_location(name, script)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        exec(compile(script.read_bytes(), os.fspath(script), "exec"), module.__dict__)
        return module

    old = load("review_legacy", LEGACY)
    new = load("review_current", CURRENT)
    production_qualified = new._COMMITTED_INDEX_QUALIFIED
    # Only isolated fixture registries below can exercise provisional authority.
    new._COMMITTED_INDEX_QUALIFIED = True
    assert old.PROTOCOL_VERSION == new.PROTOCOL_VERSION == 1
    assert old.PLAN_HEADER == new.PLAN_HEADER

    def functions(source: bytes):
        tree = ast.parse(source)
        return {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        }

    checkpoint = functions(
        subprocess.check_output(
            ["git", "show", "f804fd1:cmake/ProtocyteOutputCoordinator.py"], cwd=REPO
        )
    )
    candidate = functions(CURRENT.read_bytes())
    old_methods = {
        node.name: node
        for node in checkpoint["OutputCoordinator"].body
        if isinstance(node, ast.FunctionDef)
    }
    new_methods = {
        node.name: node
        for node in candidate["OutputCoordinator"].body
        if isinstance(node, ast.FunctionDef)
    }
    unchanged = []
    for name in (
        "reconcile_set",
        "_reconcile_locked",
        "validate",
        "publish",
        "reset",
        "_recover",
        "_apply_pending",
        "_publish_one",
        "_initialize_claim_locked",
        "_release_claim",
        "_generation_lock",
        "_publication_lock",
    ):
        assert ast.dump(old_methods[name]) == ast.dump(new_methods[name]), name
        unchanged.append(name)
    reference = new_methods["_validate_registry_reference"]
    reference.name = "_validate_registry"
    reference_unchanged = ast.dump(old_methods["_validate_registry"]) == ast.dump(
        reference
    )
    assert ast.dump(checkpoint["FileLock"]) == ast.dump(candidate["FileLock"])

    indexed_validations = []

    def engine(version: str, locks: Path):
        if version == "old":
            return old.OutputCoordinator(locks)
        result = new.OutputCoordinator(
            locks, **({} if version == "default" else {"registry_validation": version})
        )
        if version in ("indexed", "default"):
            validate = result._validate_registry

            def recorded(*args, **kwargs):
                validate(*args, **kwargs)
                indexed_validations.append(dict(result.validation_metrics))

            result._validate_registry = recorded
        return result

    def module(version: str):
        return old if version == "old" else new

    def fixture(name: str):
        directory = WORK / "fixtures" / name
        directory.mkdir(parents=True, exist_ok=False)
        build = directory / "build"
        build.mkdir()
        root = directory / "generated"
        locks = directory / "locks"
        plan = directory / "outputs.plan"
        target = hashlib.sha256(b"upgrade-target").hexdigest()
        staging = directory / (".protocyte-generation-staging-" + target) / "generated"

        def encode(value):
            return os.fspath(value).encode().hex()

        plan.write_text(
            "\n".join(
                [
                    old.PLAN_HEADER,
                    "root-hex=" + encode(root),
                    "build-root-hex=" + encode(build),
                    "target=" + target + "|" + encode(staging.parent),
                    "output=" + target + "|" + encode("demo.protocyte.cpp"),
                    "output=" + target + "|" + encode("demo.protocyte.hpp"),
                ]
            )
            + "\n",
            encoding="ascii",
        )
        assert old.Plan.read(plan).payload == new.Plan.read(plan).payload
        assert old.Plan.read(plan).digest == new.Plan.read(plan).digest
        return root, locks, plan, target, staging

    def stage(staging: Path, generation: int):
        staging.mkdir(parents=True, exist_ok=True)
        for suffix in ("cpp", "hpp"):
            (staging / ("demo.protocyte." + suffix)).write_bytes(
                f"// generated {generation}\n".encode()
            )

    def verify_outputs(root: Path, generation: int):
        for suffix in ("cpp", "hpp"):
            assert (
                root / ("demo.protocyte." + suffix)
            ).read_bytes() == f"// generated {generation}\n".encode()

    def run(version: str, command: str, locks: Path, plan: Path, extras=(), crash=None):
        args = [
            sys.executable,
            os.fspath(LEGACY if version == "old" else CURRENT),
            command,
            "--lock-root",
            os.fspath(locks),
            "--plan",
            os.fspath(plan),
            *extras,
        ]
        if version == "shadow":
            args.append("--experimental-registry-index")
        elif version == "native-shadow":
            args.append("--experimental-native-observation")
        elif version == "commit-shadow":
            args.append("--experimental-observation-commit")
        elif version == "reference":
            args.append("--reference-registry-validation")
        if version in ("indexed", "default"):
            if version == "indexed":
                args.append("--experimental-committed-index")
        if version in ("indexed", "default") and not production_qualified:
            qualified_main = (
                "import importlib.util,sys; "
                "spec=importlib.util.spec_from_file_location('qualified_upgrade_cli',sys.argv[1]); "
                "module=importlib.util.module_from_spec(spec); "
                "sys.modules[spec.name]=module; spec.loader.exec_module(module); "
                "module._COMMITTED_INDEX_QUALIFIED=True; "
                "raise SystemExit(module.main(sys.argv[2:]))"
            )
            args = [sys.executable, "-c", qualified_main, *args[1:]]
        environment = os.environ.copy()
        environment.pop("PROTOCYTE_COORDINATOR_CRASH_AFTER", None)
        if crash:
            environment["PROTOCYTE_COORDINATOR_CRASH_AFTER"] = crash
        completed = subprocess.run(
            args, env=environment, capture_output=True, timeout=40
        )
        assert completed.returncode == (86 if crash else 0), (
            version,
            command,
            crash,
            completed.returncode,
            completed.stderr,
        )
        return completed

    results = []
    transitions = (
        ("old", "reference"),
        ("old", "shadow"),
        ("reference", "old"),
        ("shadow", "old"),
        ("old", "native-shadow"),
        ("native-shadow", "old"),
        ("old", "commit-shadow"),
        ("commit-shadow", "old"),
        ("old", "indexed"),
        ("indexed", "old"),
        ("old", "default"),
        ("default", "old"),
    )
    for writer, reader in transitions:
        root, locks, plan, target, staging = fixture(f"steady-{writer}-{reader}")
        first, second = engine(writer, locks), engine(reader, locks)
        first_plan, second_plan = (
            module(writer).Plan.read(plan),
            module(reader).Plan.read(plan),
        )
        token = first.reconcile(first_plan)
        state = first._state_directory(root)
        assert first._generation_lock(root) == second._generation_lock(root)
        assert first._publication_lock(root) == second._publication_lock(root)
        claim = (state / "claim.json").read_bytes()
        stage(staging, 1)
        first.publish(first_plan, target, staging)
        unchanged_outputs = {
            path.name: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.iterdir()
        }
        assert second.reconcile(second_plan) == token
        second.validate(second_plan)
        assert (state / "claim.json").read_bytes() == claim
        assert unchanged_outputs == {
            path.name: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.iterdir()
        }
        stage(staging, 2)
        second.publish(second_plan, target, staging)
        first.validate(first_plan)
        assert first.reconcile(first_plan) == token
        verify_outputs(root, 2)
        results.append(
            {
                "kind": "upgrade-rollback-noop-token-and-publication",
                "writer": writer,
                "reader": reader,
                "passed": True,
            }
        )

    for writer, reader in (
        ("old", "reference"),
        ("old", "shadow"),
        ("shadow", "old"),
        ("old", "native-shadow"),
        ("native-shadow", "old"),
        ("old", "commit-shadow"),
        ("commit-shadow", "old"),
        ("old", "indexed"),
        ("indexed", "old"),
        ("old", "default"),
        ("default", "old"),
    ):
        for phase in (
            "after-pending",
            "after-output-1",
            "after-output-2",
            "after-snapshot",
        ):
            root, locks, plan, target, staging = fixture(
                f"publish-{writer}-{reader}-{phase}"
            )
            first = engine(writer, locks)
            p = module(writer).Plan.read(plan)
            token = first.reconcile(p)
            stage(staging, 1)
            first.publish(p, target, staging)
            stage(staging, 2)
            run(
                writer,
                "publish",
                locks,
                plan,
                ("--target", target, "--staging-root", os.fspath(staging)),
                crash=phase,
            )
            for payload in staging.iterdir():
                payload.unlink()
            second = engine(reader, locks)
            assert second.reconcile(module(reader).Plan.read(plan)) == token
            verify_outputs(root, 2)
            assert not list((second._state_directory(root) / "transactions").iterdir())
            results.append(
                {
                    "kind": "publication-crash-recovery",
                    "writer": writer,
                    "reader": reader,
                    "cut": phase,
                    "passed": True,
                }
            )
        for phase in ("after-initial-snapshot", "after-claim"):
            root, locks, plan, target, staging = fixture(
                f"init-{writer}-{reader}-{phase}"
            )
            run(writer, "reconcile", locks, plan, crash=phase)
            second = engine(reader, locks)
            assert len(second.reconcile(module(reader).Plan.read(plan))) == 64
            second.validate(module(reader).Plan.read(plan))
            results.append(
                {
                    "kind": "initialization-crash-recovery",
                    "writer": writer,
                    "reader": reader,
                    "cut": phase,
                    "passed": True,
                }
            )
        for phase in (
            "after-reset-intent",
            "after-reset-output-1",
            "after-reset-disposable",
        ):
            root, locks, plan, target, staging = fixture(
                f"reset-{writer}-{reader}-{phase}"
            )
            first = engine(writer, locks)
            p = module(writer).Plan.read(plan)
            token = first.reconcile(p)
            stage(staging, 1)
            first.publish(p, target, staging)
            run(writer, "reset", locks, plan, ("--expected-claim", token), crash=phase)
            second = engine(reader, locks)
            second.reset(module(reader).Plan.read(plan), token)
            assert not second._state_directory(root).exists()
            assert not list(root.glob("*.protocyte.*"))
            results.append(
                {
                    "kind": "reset-crash-recovery",
                    "writer": writer,
                    "reader": reader,
                    "cut": phase,
                    "passed": True,
                }
            )

    # Historical source checks are deliberately in this explicit qualifier,
    # not routine unit tests: a squash merge need not retain branch commits.
    mixed_source_hashes = {}
    for revision in ("8851bde", "1d1e1b0"):
        path = WORK / f"legacy/helper-{revision}.py"
        path.write_bytes(
            subprocess.check_output(
                ["git", "show", f"{revision}:cmake/ProtocyteObservationCommit.py"],
                cwd=REPO,
            )
        )
        previous_helper = load(f"mixed_helper_{revision}", path)
        mixed_source_hashes[f"helper-{revision}"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        root, locks, plan_file, _, _ = fixture(f"mixed-helper-{revision}")
        reader = engine("reference", locks)
        plan = new.Plan.read(plan_file)
        token = reader.reconcile(plan)
        state = reader._state_directory(root)
        claim = (state / "claim.json").read_bytes()
        load_commit, commit_module = (
            new._load_observation_commit,
            new._observation_commit_module,
        )
        try:
            new._load_observation_commit = lambda: previous_helper
            new._observation_commit_module = previous_helper
            reader.registry_validation = "indexed"
            assert reader.reconcile(plan) == token
            assert reader.validation_metrics["fallback"] == "reference"
            assert reader.validation_metrics["reference_result"] == "accepted"
            assert "commit_handles_opened" not in reader.validation_metrics
            assert (state / "claim.json").read_bytes() == claim
        finally:
            new._load_observation_commit, new._observation_commit_module = (
                load_commit,
                commit_module,
            )
        results.append(
            {
                "kind": "actual-previous-helper-reference-fallback",
                "revision": revision,
                "passed": True,
            }
        )

    path = WORK / "legacy/pre-review-coordinator.py"
    path.write_bytes(
        subprocess.check_output(
            ["git", "show", "1d1e1b0:cmake/ProtocyteOutputCoordinator.py"], cwd=REPO
        )
    )
    previous = load("mixed_previous_coordinator", path)
    mixed_source_hashes["coordinator-1d1e1b0"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    previous._COMMITTED_INDEX_QUALIFIED = True
    previous._load_ownership_index = new._load_ownership_index
    previous._load_path_observation = new._load_path_observation
    previous._load_observation_commit = new._load_observation_commit
    updated_helper = new._load_observation_commit()
    previous._observation_commit_module = updated_helper
    for failed_cleanup in (False, True):
        root, locks, plan_file, _, _ = fixture(
            f"previous-coordinator-updated-helper-{failed_cleanup}"
        )
        reader = previous.OutputCoordinator(locks, registry_validation="reference")
        plan = previous.Plan.read(plan_file)
        token = reader.reconcile(plan)
        claim = (reader._state_directory(root) / "claim.json").read_bytes()
        constructor = updated_helper.WindowsObservationCommit.__init__
        failed = []
        if failed_cleanup:

            def initialize(readset, *args, **kwargs):
                constructor(readset, *args, **kwargs)
                raw_close = readset.reader._close

                def close(handle):
                    if not failed:
                        failed.append((raw_close, handle))
                        return False
                    return raw_close(handle)

                readset.reader._close = close

            updated_helper.WindowsObservationCommit.__init__ = initialize
        try:
            reader.registry_validation = "indexed"
            if failed_cleanup:
                try:
                    reader.reconcile(plan)
                except previous.CoordinatorError as error:
                    assert "could not be retired safely" in str(error)
                else:
                    raise AssertionError(
                        "previous coordinator accepted failed native cleanup"
                    )
                assert reader.validation_metrics["reference_wall_seconds"] == 0.0
            else:
                assert reader.reconcile(plan) == token
                assert reader.validation_metrics["authoritative"] == "index"
            assert (reader._state_directory(root) / "claim.json").read_bytes() == claim
        finally:
            updated_helper.WindowsObservationCommit.__init__ = constructor
            # Only the injector knows that no OS close was attempted.
            for raw_close, handle in failed:
                assert raw_close(handle)
        results.append(
            {
                "kind": "actual-previous-coordinator-updated-helper",
                "failed_cleanup": failed_cleanup,
                "passed": True,
            }
        )

    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in IMPLEMENTATION
    } == EXPECTED_SOURCES, "sources changed during qualification; discard the run"
    report = {
        "scope": "isolated Windows cross-version checks; no consumer registry accessed",
        "legacy_git_blob": "25f1660190d3d1015fef3955814c8c737bd686c5",
        "legacy_coordinator_sha256": hashlib.sha256(LEGACY.read_bytes()).hexdigest(),
        "candidate_coordinator_sha256": hashlib.sha256(
            CURRENT.read_bytes()
        ).hexdigest(),
        "implementation_files": EXPECTED_SOURCES,
        "candidate_helper_sha256": {
            name: hashlib.sha256((CURRENT.parent / name).read_bytes()).hexdigest()
            for name in (
                "ProtocyteOwnershipIndex.py",
                "ProtocytePathObservation.py",
                "ProtocyteObservationCommit.py",
            )
        },
        "mixed_source_sha256": mixed_source_hashes,
        "unchanged_ast_methods_since_checkpoint": unchanged,
        "reference_validator_ast_unchanged_since_checkpoint": reference_unchanged,
        "file_lock_ast_unchanged_since_checkpoint": True,
        "passed_cases": len(results),
        "production_index_authorization_qualified": production_qualified,
        "index_authority_enabled_only_in_isolated_fixture_module": not production_qualified,
        "indexed_validations": len(indexed_validations),
        "index_authorized_validations": sum(
            metrics["authoritative"] == "index" for metrics in indexed_validations
        ),
        "indexed_reference_fallbacks": sum(
            metrics.get("fallback") == "reference" for metrics in indexed_validations
        ),
        "cases": results,
    }
    (WORK / "upgrade-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed_cases": len(results),
                "protocol": 1,
                "unchanged_reference_validator": reference_unchanged,
                "unchanged_file_locks": True,
            }
        )
    )


if __name__ == "__main__":
    main()
