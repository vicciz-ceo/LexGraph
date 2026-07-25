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
    """Return a RatingSummary for `strengths`, or None if `strengths` is empty."""
    raise NotImplementedError("developer: implement rating aggregate computation (B2)")
