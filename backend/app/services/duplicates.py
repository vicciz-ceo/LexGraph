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

What callers show (audit findings agent:2, ui:5): `surface_similar` keeps
the strongest `SIMILAR_ASSERTIONS_LIMIT` matches (score descending, then
assertion id) and gives each the matched assertion's display text, status
and type, so a response stays small however many rows match -- a matter
holding definition-linking output can match tens of thousands. Callers
report the uncapped count next to the list. The exact-duplicate check
always runs over every match, never over the capped list.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from difflib import SequenceMatcher
from typing import Any, TypedDict

from fastapi import HTTPException

# Below this similarity ratio, two propositions are considered unrelated
# rather than merely differently worded. Tuned against the fixture pair in
# spec/test data ("...limited exception to the notification obligation in
# Clause 8.2." vs "...narrow exception to the Clause 8.2 notice
# obligation.", ratio ~0.71) with headroom on both sides.
SIMILARITY_THRESHOLD = 0.55

#: How many matches a response lists (`surface_similar`).
SIMILAR_ASSERTIONS_LIMIT = 20
#: The longest proposition text a listed match carries; longer text is cut
#: and ends with an ellipsis (the full text is at GET /assertions/{id}).
SIMILAR_PROPOSITION_DISPLAY_LENGTH = 300


class DuplicateCandidate(TypedDict):
    assertion_id: str
    match_kind: str  # "exact_proposition" | "same_subject_type_object" | "similar"
    score: float


def duplicate_detail(existing_assertion_id: str) -> str:
    return (
        "duplicate: an identical proposition already exists in this matter "
        f"(assertion {existing_assertion_id})"
    )


class DuplicateAssertionError(HTTPException):
    """The exact-duplicate 409. `detail` is the documented message; the API
    also answers `existing_assertion_id` next to it (registered in
    `app.request_guards`). Callers that catch `HTTPException` (the agent
    CLI, the MCP server) see a plain HTTPException with that detail."""

    def __init__(self, existing_assertion_id: str) -> None:
        super().__init__(status_code=409, detail=duplicate_detail(existing_assertion_id))
        self.existing_assertion_id = existing_assertion_id


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


def _similar_score(a: str, b: str) -> float | None:
    """`SequenceMatcher(None, a, b).ratio()` when it reaches
    SIMILARITY_THRESHOLD, else None.

    Prefiltered without changing any result (agent:2): the length bound is
    difflib's `real_quick_ratio`, an upper bound of `ratio`, so a pair it
    rules out could never have matched. (Its character-multiset bound,
    `quick_ratio`, was measured and dropped: it rules out almost no pair of
    same-language sentences and costs about a tenth of `ratio`.)"""
    if not a or not b:
        return None
    la, lb = len(a), len(b)
    if 2.0 * min(la, lb) / (la + lb) < SIMILARITY_THRESHOLD:
        return None
    score = SequenceMatcher(None, a, b).ratio()
    return score if score >= SIMILARITY_THRESHOLD else None


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
    # Generated rows repeat their wording ('Article 2 uses the definition
    # of "person".' in every law of a matter): each distinct text is scored
    # once.
    scores: dict[str, float | None] = {}

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

        if other_proposition not in scores:
            scores[other_proposition] = _similar_score(cand_proposition, other_proposition)
        score = scores[other_proposition]
        if score is not None:
            results.append(
                {"assertion_id": other_id, "match_kind": "similar", "score": round(score, 4)}
            )

    results.sort(key=lambda c: c["score"], reverse=True)
    return results


def display_proposition(text: str | None) -> str:
    """A proposition shortened for a list of matches."""
    text = text or ""
    if len(text) <= SIMILAR_PROPOSITION_DISPLAY_LENGTH:
        return text
    return text[: SIMILAR_PROPOSITION_DISPLAY_LENGTH - 1].rstrip() + "…"


def surface_similar(
    matches: Iterable[DuplicateCandidate],
    assertions: Mapping[str, Any],
    *,
    limit: int = SIMILAR_ASSERTIONS_LIMIT,
) -> tuple[list[dict[str, Any]], int]:
    """The `limit` strongest `matches` (score descending, then assertion id)
    as response entries, and how many matches there were before the cap.

    Each entry keeps `assertion_id`, `match_kind` and `score` and adds the
    matched assertion's `proposition` (display text, see
    `display_proposition`), `status` and `assertion_type`, read from
    `assertions[assertion_id]` (any object with those attributes)."""
    ordered = sorted(matches, key=lambda m: (-m["score"], m["assertion_id"]))
    shown = []
    for match in ordered[:limit]:
        row = assertions[match["assertion_id"]]
        shown.append({
            **match,
            "proposition": display_proposition(row.proposition),
            "status": row.status,
            "assertion_type": row.assertion_type,
        })
    return shown, len(ordered)
