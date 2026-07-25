"""GraphProjection interface + in-memory adapter (shape only).

Manager ruling R1: no live Neo4j in this environment — graph projection
sits behind a `GraphProjection` interface with an in-memory adapter. The
in-memory adapter is the REAL adapter for this sprint (not a mock, not a
stand-in for a "real" Neo4j implementation) — a Developer track (B6) fills
in its method bodies. Only the interface shape is scaffolded here; the
projection/visibility/aggregate-rebuild logic is a gate-G7 acceptance
target and therefore Developer work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GraphProjection(ABC):
    """Read/write interface for the assertion graph projection."""

    @abstractmethod
    def project_assertion(self, assertion: dict[str, Any]) -> None:
        """Upsert a projected node/edge state for one assertion."""
        raise NotImplementedError

    @abstractmethod
    def remove_assertion(self, assertion_id: str) -> None:
        """Remove a projected assertion (e.g. on hard supersession)."""
        raise NotImplementedError

    @abstractmethod
    def get_visible_assertions(
        self, matter_id: str, *, show_unreviewed: bool = False
    ) -> list[dict[str, Any]]:
        """Return projected assertions visible in the default (or unreviewed) view."""
        raise NotImplementedError

    @abstractmethod
    def rebuild(self, assertions: list[dict[str, Any]]) -> None:
        """Rebuild the entire projection from an authoritative assertion list.

        Proves rating aggregates / review-status projections in the graph
        are rebuildable, never authoritative (spec §11).
        """
        raise NotImplementedError


class InMemoryGraphProjection(GraphProjection):
    """In-memory GraphProjection adapter — real for this sprint (ruling R1).

    Method bodies are unimplemented (`NotImplementedError`) pending a
    Developer track (B6). This class is intentionally NOT a
    `unittest.mock.Mock` — tests instantiate and call it directly so a
    green result proves real projection behavior, per the self-mock ban.
    """

    def __init__(self) -> None:
        self._by_matter: dict[str, dict[str, dict[str, Any]]] = {}

    def project_assertion(self, assertion: dict[str, Any]) -> None:
        matter_id = assertion["matter_id"]
        bucket = self._by_matter.setdefault(matter_id, {})
        bucket[assertion["id"]] = dict(assertion)

    def remove_assertion(self, assertion_id: str) -> None:
        for bucket in self._by_matter.values():
            bucket.pop(assertion_id, None)

    def get_visible_assertions(
        self, matter_id: str, *, show_unreviewed: bool = False
    ) -> list[dict[str, Any]]:
        bucket = self._by_matter.get(matter_id, {})
        if show_unreviewed:
            return [dict(a) for a in bucket.values()]
        return [dict(a) for a in bucket.values() if a.get("status") == "accepted"]

    def rebuild(self, assertions: list[dict[str, Any]]) -> None:
        # Full replace, never an incremental merge — proves the projection
        # is rebuildable from the authoritative store (spec §11), not
        # itself a source of truth.
        self._by_matter = {}
        for assertion in assertions:
            self.project_assertion(assertion)
