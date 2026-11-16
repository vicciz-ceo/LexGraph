"""InMemoryGraphProjection visibility follows spec §11 exactly (api:23)."""

from __future__ import annotations

from app.graph_projection import DEFAULT_VIEW_STATES, UNREVIEWED_VIEW_STATES, InMemoryGraphProjection

ALL_STATUSES = (
    "draft", "proposed", "revision_requested", "accepted", "rejected", "disputed", "superseded", "withdrawn",
)


def _projection() -> InMemoryGraphProjection:
    projection = InMemoryGraphProjection()
    projection.rebuild([{"id": status, "matter_id": "m1", "status": status} for status in ALL_STATUSES])
    return projection


def test_the_view_state_sets_are_the_spec_lists():
    assert DEFAULT_VIEW_STATES == ("accepted",)
    assert set(UNREVIEWED_VIEW_STATES) == {"accepted", "proposed", "disputed", "rejected", "superseded"}


def test_show_unreviewed_never_returns_drafts_withdrawn_or_returned_assertions():
    visible = [a["status"] for a in _projection().get_visible_assertions("m1", show_unreviewed=True)]
    assert visible == [s for s in ALL_STATUSES if s in UNREVIEWED_VIEW_STATES]


def test_default_view_returns_accepted_only():
    assert [a["id"] for a in _projection().get_visible_assertions("m1")] == ["accepted"]
