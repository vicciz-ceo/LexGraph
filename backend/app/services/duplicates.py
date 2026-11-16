"""Duplicate/related-assertion detection (Developer track B5).

Spec §8: before submission, search for exact proposition matches, same
subject+type+object, semantically similar propositions, superseded
versions, accepted assertions on the same relationship, and
competing/contradicting assertions. Must never auto-merge — this module
only surfaces candidates; callers decide whether to block (exact
duplicates, spec §7 "similarity warnings must not prevent submission
unless there is an exact duplicate") or merely warn.

Which exact duplicates block (audit finding api:16, recorded in the spec's
"Exact duplicates" rule): an existing assertion in a LIVE status (anything
but draft, withdrawn, rejected or superseded) blocks every author, and an
existing draft blocks only its own author -- unless that draft is the one
being submitted. Withdrawn, rejected and superseded assertions never block;
they are still returned by `find_related_assertions` as matches, so callers
report them as non-blocking `similar_assertions`.
"""

from __future__ import annotations

from collections.abc import Iterable
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


#: Statuses whose exact-proposition twin never blocks: the claim was
#: abandoned, decided against, or replaced, so proposing it again (for
#: example with new evidence) is a new submission, not a duplicate.
ENDED_STATUSES = frozenset({"withdrawn", "rejected", "superseded"})


def normalize_proposition(text: str | None) -> str:
    """The comparison key for exact-duplicate detection (case and
    surrounding whitespace are ignored)."""
    return (text or "").strip().lower()


_norm = normalize_proposition


def blocks_exact_duplicate(
    status: str | None,
    author_user_id: str | None,
    *,
    owner_user_id: str | None,
    submitting: bool = False,
) -> bool:
    """Whether an existing assertion with an identical proposition blocks.

    `owner_user_id` is the author of the assertion being created, edited or
    submitted. `submitting` is True when a draft is being submitted: its
    author's other drafts do not block it (they are checked when they are
    submitted themselves).
    """
    if status in ENDED_STATUSES:
        return False
    if status == "draft":
        return not submitting and author_user_id == owner_user_id
    return True


def first_blocking_duplicate(
    proposition: str | None,
    existing: Iterable[tuple[str, str | None, str | None, str | None]],
    *,
    owner_user_id: str | None,
    exclude_id: str | None = None,
    submitting: bool = False,
) -> str | None:
    """Return the id of the first `(id, proposition, status, author_user_id)`
    row in `existing` that blocks `proposition` as an exact duplicate."""
    key = normalize_proposition(proposition)
    if not key:
        return None
    for row_id, other_proposition, status, author_user_id in existing:
        if row_id == exclude_id or normalize_proposition(other_proposition) != key:
            continue
        if blocks_exact_duplicate(status, author_user_id, owner_user_id=owner_user_id,
                                  submitting=submitting):
            return row_id
    return None


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
