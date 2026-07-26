"""B2 — pure rating-aggregate math (spec §4). Unit-level: exercises
`app.services.ratings.compute_rating_summary` directly, no HTTP/DB.

The function exists (import succeeds) but its body is
`raise NotImplementedError` pending the B2 Developer track — so every test
here fails at call time with NotImplementedError, a missing-behavior RED,
never an import/collection error.
"""

from __future__ import annotations

import pytest

from app.services.ratings import compute_rating_summary


def test_empty_ratings_returns_none():
    assert compute_rating_summary([]) is None


def test_single_rating_summary():
    result = compute_rating_summary([4])
    assert result == {
        "count": 1,
        "average": 4.0,
        "median": 4,
        "distribution": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 0},
    }


def test_mean_is_unrounded():
    result = compute_rating_summary([1, 2, 2])
    assert result["average"] == pytest.approx(5 / 3)


def test_median_odd_count():
    result = compute_rating_summary([1, 5, 3])
    assert result["median"] == 3


def test_median_even_count_is_midpoint_average():
    result = compute_rating_summary([1, 2, 4, 5])
    assert result["median"] == 3.0


def test_distribution_counts_each_bucket():
    result = compute_rating_summary([1, 1, 3, 5, 5, 5])
    assert result["distribution"] == {"1": 2, "2": 0, "3": 1, "4": 0, "5": 3}


def test_count_matches_input_length():
    result = compute_rating_summary([2, 2, 2, 2, 2, 2, 2])
    assert result["count"] == 7
