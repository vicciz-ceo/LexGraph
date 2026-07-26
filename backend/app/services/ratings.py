"""Rating aggregate math (shape only — Developer track B2 fills these in).

Spec §4: for every assertion revision, compute count, unrounded arithmetic
mean, median, and a 1-5 distribution from a list of current ratings. Must
return "no aggregate" semantics when `ratings` is empty (spec: "Do not
calculate or display an aggregate when there are no ratings") rather than
raising or returning zeros.
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
