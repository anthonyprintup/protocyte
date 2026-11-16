"""Experimental ownership geometry, with no mutation or filesystem authority.

An index describes sampled observations only. It cannot authorize reconciliation
or publication. The coordinator's shadow mode always runs its fresh reference
validator after the preview, and fails closed on disagreement.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Iterable, Literal


LocationKey = tuple[int, int, tuple[str, ...]]


@dataclass(frozen=True)
class DirectoryObservation:
    portable: str
    location: LocationKey
    ancestors: tuple[LocationKey, ...]

    def overlaps(self, other: DirectoryObservation) -> bool:
        return (
            self.portable == other.portable
            or self.portable.startswith(other.portable + "/")
            or other.portable.startswith(self.portable + "/")
            or self.location in other.ancestors
            or other.location in self.ancestors
        )


@dataclass(frozen=True)
class Reservation:
    kind: Literal["root", "staging"]
    root_key: str
    build_id: str
    target: str | None
    directory: DirectoryObservation


class OwnershipIndex:
    """Find overlapping reservations from both lexical and physical geometry.

    Physical ancestors include normalized missing-suffix prefixes. Indexing both
    endpoint and ancestor keys covers containment in either direction, including
    non-link aliases whose names have no lexical prefix in common. Common
    ancestors alone do not imply overlap.
    """

    def __init__(self, reservations: Iterable[Reservation]) -> None:
        contract = globals().get("OWNERSHIP_CONTRACT_VERSION")
        if type(contract) is not int or contract != 1:
            raise RuntimeError("incomplete ownership helper installation")
        self.reservations = tuple(reservations)
        self.queries = 0
        exact: dict[LocationKey, set[int]] = {}
        ancestors: dict[LocationKey, set[int]] = {}
        lexical: dict[str, set[int]] = {}
        for identifier, reservation in enumerate(self.reservations):
            facts = reservation.directory
            exact.setdefault(facts.location, set()).add(identifier)
            for ancestor in facts.ancestors:
                ancestors.setdefault(ancestor, set()).add(identifier)
            lexical.setdefault(facts.portable, set()).add(identifier)
        self._exact = {key: frozenset(value) for key, value in exact.items()}
        self._ancestors = {key: frozenset(value) for key, value in ancestors.items()}
        self._lexical = {key: frozenset(value) for key, value in lexical.items()}
        self._names = sorted(lexical)

    def overlapping(self, directory: DirectoryObservation) -> tuple[Reservation, ...]:
        self.queries += 1
        candidates: set[int] = set(self._ancestors.get(directory.location, ()))
        for ancestor in directory.ancestors:
            candidates.update(self._exact.get(ancestor, ()))

        current = directory.portable
        while True:
            candidates.update(self._lexical.get(current, ()))
            if "/" not in current:
                break
            current = current.rsplit("/", 1)[0]
        prefix = directory.portable + "/"
        position = bisect_left(self._names, prefix)
        while position < len(self._names) and self._names[position].startswith(prefix):
            candidates.update(self._lexical[self._names[position]])
            position += 1
        # Keep deterministic reporting. The final predicate is also a defensive
        # check on candidate retrieval; it uses observations, never fresh I/O.
        return tuple(
            self.reservations[identifier]
            for identifier in sorted(candidates)
            if self.reservations[identifier].directory.overlaps(directory)
        )

    def conflict(
        self,
        *,
        root: DirectoryObservation,
        root_key: str,
        build_id: str,
        staging: Iterable[tuple[str, DirectoryObservation]],
        retiring_root_keys: set[str],
    ) -> str | None:
        for reservation in self.overlapping(root):
            if reservation.kind == "root":
                if reservation.root_key != root_key:
                    return "root-root"
            else:
                return "root-staging"
        for target, directory in staging:
            for reservation in self.overlapping(directory):
                if reservation.kind == "root":
                    return "staging-root"
                if target == reservation.target and (
                    root_key == reservation.root_key
                    or (
                        reservation.root_key in retiring_root_keys
                        and build_id == reservation.build_id
                    )
                ):
                    continue
                return "staging-staging"
        return None


# EOF capability marker; an incomplete installed source cannot advertise it.
OWNERSHIP_CONTRACT_VERSION = 1
