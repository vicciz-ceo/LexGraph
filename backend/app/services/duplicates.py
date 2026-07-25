"""Duplicate/related-assertion detection (shape only — Developer track B5).

Spec §8: before submission, search for exact proposition matches, same
subject+type+object, semantically similar propositions, superseded
versions, accepted assertions on the same relationship, and
competing/contradicting assertions. Must never auto-merge.
"""

from __future__ import annotations

from typing import Any, TypedDict


class DuplicateCandidate(TypedDict):
    assertion_id: str
    match_kind: str  # "exact_proposition" | "same_subject_type_object" | "similar" | ...
    score: float


def find_related_assertions(
    candidate: dict[str, Any], existing: list[dict[str, Any]]
) -> list[DuplicateCandidate]:
    raise NotImplementedError("developer: implement duplicate/related detection (B5)")
