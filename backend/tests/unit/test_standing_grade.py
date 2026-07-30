"""Sprint 2026-07-30-ratings-grade, item B1 — pure standing/grade math.

Mandate (director): "Proposed" covers user-submitted AND AI-deduced
assertions until rated by a NON-AUTHOR user; from that first outside
rating the assertion's *standing* is its grade — a 1-5 median banded
weak/probable/strong (ruling R4). The reviewer accept/reject workflow
takes precedence over the grade presentation (gate G4), and
origin=system_generated assertions never enter this flow at all (gate
G5, they are born "accepted" per sprint 2026-07-30-deterministic-
assertions).

Ruling R3 (manager lean, confirmed): standing is DERIVED at read time
from existing `AssertionRating` rows, not persisted. This test file pins
two new pure functions in `app.services.ratings` (co-located with the
existing `compute_rating_summary`, per R3's own text pointing at this
module):

- `band_for_median(median: float) -> str` — R4's band edges: weak < 3,
  probable == 3, strong > 3 (so a fractional median of 2.5 is "weak" and
  3.5 is "strong").
- `compute_standing(status: str, ratings: list[dict], author_user_id:
  str) -> str` — gates G1-G5 in one place: passes `status` through
  unchanged for every non-"proposed" status (covers G4's reviewer
  override AND G5's deterministic/accepted assertions in one rule, since
  neither is ever "proposed"); for "proposed", excludes the author's own
  rating (G3) and returns "proposed" when no outside rating remains (G1),
  else bands the outside-only median (G2). Each `ratings` item is
  `{"user_id": ..., "strength": ...}` (the shape a caller reads straight
  off `AssertionRating` rows).

Neither function exists yet in `app.services.ratings` — this whole file is
expected RED via `ImportError: cannot import name 'band_for_median'...`
at collection time (documented exception per the sprint-harness planner
brief: pinning not-yet-written functions), not a behavioral failure.
"""

from __future__ import annotations

from app.services.ratings import band_for_median, compute_standing

AUTHOR = "author-user-1"
OUTSIDER_A = "outsider-a"
OUTSIDER_B = "outsider-b"


# --- band_for_median: R4's edges, including the fractional ones ------------


def test_band_whole_number_1_is_weak():
    assert band_for_median(1) == "weak"


def test_band_whole_number_2_is_weak():
    assert band_for_median(2) == "weak"


def test_band_fractional_2_5_is_weak():
    assert band_for_median(2.5) == "weak"


def test_band_whole_number_3_is_probable():
    assert band_for_median(3) == "probable"


def test_band_fractional_3_5_is_strong():
    assert band_for_median(3.5) == "strong"


def test_band_whole_number_4_is_strong():
    assert band_for_median(4) == "strong"


def test_band_whole_number_5_is_strong():
    assert band_for_median(5) == "strong"


# --- compute_standing: non-"proposed" statuses pass through unchanged ------
# (gate G4 — reviewer decisions override the grade presentation; gate G5 —
# deterministic assertions are born "accepted" and never graded)


def test_accepted_status_passes_through_regardless_of_ratings():
    ratings = [{"user_id": OUTSIDER_A, "strength": 5}, {"user_id": OUTSIDER_B, "strength": 5}]
    assert compute_standing("accepted", ratings, AUTHOR) == "accepted"


def test_rejected_status_passes_through_even_with_no_ratings():
    assert compute_standing("rejected", [], AUTHOR) == "rejected"


def test_disputed_status_passes_through():
    ratings = [{"user_id": OUTSIDER_A, "strength": 1}]
    assert compute_standing("disputed", ratings, AUTHOR) == "disputed"


def test_revision_requested_status_passes_through():
    assert compute_standing("revision_requested", [], AUTHOR) == "revision_requested"


def test_superseded_status_passes_through():
    assert compute_standing("superseded", [], AUTHOR) == "superseded"


def test_withdrawn_status_passes_through():
    assert compute_standing("withdrawn", [], AUTHOR) == "withdrawn"


def test_draft_status_passes_through_unaffected_by_grading():
    ratings = [{"user_id": OUTSIDER_A, "strength": 5}]
    assert compute_standing("draft", ratings, AUTHOR) == "draft"


# --- compute_standing: "proposed" — gate G1 (zero outside ratings) ---------


def test_proposed_with_zero_ratings_stays_proposed():
    assert compute_standing("proposed", [], AUTHOR) == "proposed"


# --- compute_standing: "proposed" — gate G3 (author ratings don't count) --


def test_proposed_with_only_the_authors_own_rating_stays_proposed():
    ratings = [{"user_id": AUTHOR, "strength": 5}]
    assert compute_standing("proposed", ratings, AUTHOR) == "proposed"


def test_proposed_with_authors_rating_plus_one_outside_rating_grades_on_outside_only():
    # Author rates it a 1 (would be "weak" if it counted); the one outside
    # rating of 4 is what must actually drive the median (-> "strong").
    ratings = [
        {"user_id": AUTHOR, "strength": 1},
        {"user_id": OUTSIDER_A, "strength": 4},
    ]
    assert compute_standing("proposed", ratings, AUTHOR) == "strong"


# --- compute_standing: "proposed" — gate G2 (first outside rating grades) --


def test_proposed_with_single_outside_rating_of_2_bands_weak():
    ratings = [{"user_id": OUTSIDER_A, "strength": 2}]
    assert compute_standing("proposed", ratings, AUTHOR) == "weak"


def test_proposed_with_single_outside_rating_of_3_bands_probable():
    ratings = [{"user_id": OUTSIDER_A, "strength": 3}]
    assert compute_standing("proposed", ratings, AUTHOR) == "probable"


def test_proposed_with_single_outside_rating_of_4_bands_strong():
    ratings = [{"user_id": OUTSIDER_A, "strength": 4}]
    assert compute_standing("proposed", ratings, AUTHOR) == "strong"


# --- compute_standing: "proposed" — R4's fractional-median pin ------------


def test_proposed_with_outside_ratings_2_and_3_medians_2_5_bands_weak():
    ratings = [
        {"user_id": OUTSIDER_A, "strength": 2},
        {"user_id": OUTSIDER_B, "strength": 3},
    ]
    assert compute_standing("proposed", ratings, AUTHOR) == "weak"


def test_proposed_with_outside_ratings_3_and_4_medians_3_5_bands_strong():
    ratings = [
        {"user_id": OUTSIDER_A, "strength": 3},
        {"user_id": OUTSIDER_B, "strength": 4},
    ]
    assert compute_standing("proposed", ratings, AUTHOR) == "strong"
