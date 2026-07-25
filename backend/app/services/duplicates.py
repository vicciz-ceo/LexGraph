"""Duplicate/related-assertion detection (Developer track B5).

Spec §8: before submission, search for exact proposition matches, same
subject+type+object, semantically similar propositions, superseded
versions, accepted assertions on the same relationship, and
competing/contradicting assertions. Must never auto-merge — this module
only surfaces candidates; callers decide whether to block (exact
duplicates, spec §7 "similarity warnings must not prevent submission
unless there is an exact duplicate") or merely warn.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, TypedDict

# Below this similarity ratio, two propositions are considered unrelated
# rather than merely differently worded. Tuned against the fixture pair in
# spec/test data ("...limited exception to the notification obligation in
# Clause 8.2." vs "...narrow exception to the Clause 8.2 notice
# obligation.", ratio ~0.71) with headroom on both sides.
SIMILARITY_THRESHOLD = 0.55


class DuplicateCandidate(TypedDict):
    assertion_id: str
    match_kind: str  # "exact_proposition" | "same_subject_type_object" | "similar"
    score: float


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def _entity_key(entity: dict[str, Any] | None) -> tuple[str | None, str | None] | None:
    if not entity:
        return None
    return (entity.get("type"), entity.get("id"))


def _proposition_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def find_related_assertions(
    candidate: dict[str, Any], existing: list[dict[str, Any]]
) -> list[DuplicateCandidate]:
    """Compare `candidate` (a proposed/new assertion's fields) against
    `existing` assertions in the same matter and return match candidates,
    strongest first.

    Each entry in `existing` is expected to carry at least: "id",
    "proposition", "assertion_type", "subject_entity", "object_entity".
    """
    cand_id = candidate.get("id")
    cand_proposition = _norm(candidate.get("proposition"))
    cand_type = candidate.get("assertion_type")
    cand_subject = _entity_key(candidate.get("subject_entity"))
    cand_object = _entity_key(candidate.get("object_entity"))

    results: list[DuplicateCandidate] = []

    for other in existing:
        other_id = other.get("id")
        if other_id is not None and cand_id is not None and other_id == cand_id:
            continue

        other_proposition = _norm(other.get("proposition"))

        if cand_proposition and other_proposition and cand_proposition == other_proposition:
            results.append(
                {"assertion_id": other_id, "match_kind": "exact_proposition", "score": 1.0}
            )
            continue

        if (
            cand_type is not None
            and cand_type == other.get("assertion_type")
            and cand_subject is not None
            and cand_subject == _entity_key(other.get("subject_entity"))
            and cand_object == _entity_key(other.get("object_entity"))
        ):
            results.append(
                {"assertion_id": other_id, "match_kind": "same_subject_type_object", "score": 0.95}
            )
            continue

        score = _proposition_similarity(cand_proposition, other_proposition)
        if score >= SIMILARITY_THRESHOLD:
            results.append(
                {"assertion_id": other_id, "match_kind": "similar", "score": round(score, 4)}
            )

    results.sort(key=lambda c: c["score"], reverse=True)
    return results
