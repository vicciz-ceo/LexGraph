"""Rating aggregate math (shape only — Developer track B2 fills these in).

Spec §4: for every assertion revision, compute count, unrounded arithmetic
mean, median, and a 1-5 distribution from a list of current ratings. Must
return "no aggregate" semantics when `ratings` is empty (spec: "Do not
calculate or display an aggregate when there are no ratings") rather than
raising or returning zeros.

Sprint 2026-07-30-ratings-grade, item B1: `band_for_median` and
`compute_standing` below derive an assertion's *standing* (the
proposed-until-rated, then weak/probable/strong grade) at read time from
`AssertionRating` rows -- never persisted (ruling R3). Co-located here per
R3's own text pointing at this module.
"""

from __future__ import annotations

from typing import TypedDict


class RatingSummary(TypedDict):
    count: int
    average: float
    median: float
    distribution: dict[str, int]


def compute_rating_summary(strengths: list[int]) -> RatingSummary | None:
    """Return a RatingSummary for `strengths`, or None if `strengths` is empty.

    Per spec §4: count, unrounded arithmetic mean, median (midpoint average
    for even counts), and a 1-5 distribution. Callers (the ratings router)
    are responsible for enriching this pure aggregate with per-request
    context such as the current user's own rating or the rationale count
    -- this function only ever sees the list of current strengths.
    """
    if not strengths:
        return None

    count = len(strengths)
    average = sum(strengths) / count

    sorted_strengths = sorted(strengths)
    mid = count // 2
    if count % 2:
        median: float = sorted_strengths[mid]
    else:
        median = (sorted_strengths[mid - 1] + sorted_strengths[mid]) / 2

    distribution = {str(value): strengths.count(value) for value in range(1, 6)}

    return {
        "count": count,
        "average": average,
        "median": median,
        "distribution": distribution,
    }


def band_for_median(median: float) -> str:
    """Band a 1-5 median into weak/probable/strong per ruling R4.

    Edges: weak < 3, probable == 3, strong > 3 (fractional medians band by
    the same rule -- 2.5 is weak, 3.5 is strong).
    """
    if median < 3:
        return "weak"
    if median > 3:
        return "strong"
    return "probable"


def compute_standing(status: str, ratings: list[dict], author_user_id: str) -> str:
    """Derive an assertion's standing from its `status` and current ratings.

    Non-"proposed" statuses pass through unchanged -- this covers both
    gate G4 (an explicit reviewer decision overrides the grade
    presentation) and gate G5 (deterministic/system_generated assertions
    are born "accepted" and never enter the proposed-to-graded flow),
    since neither is ever "proposed".

    For "proposed", the author's own rating never counts (gate G3): if no
    non-author rating remains, standing stays "proposed" (gate G1);
    otherwise standing is the band of the median of the non-author
    strengths alone (gate G2, ruling R4).

    Each `ratings` item is `{"user_id": ..., "strength": ...}`.
    """
    if status != "proposed":
        return status

    outside_strengths = [
        r["strength"] for r in ratings if r["user_id"] != author_user_id
    ]
    if not outside_strengths:
        return "proposed"

    summary = compute_rating_summary(outside_strengths)
    assert summary is not None  # outside_strengths is non-empty here
    return band_for_median(summary["median"])
