"""B6 — unit tests against the REAL InMemoryGraphProjection adapter (ruling
R1: the in-memory adapter is the real adapter for this sprint, not a
mock). Method bodies are `raise NotImplementedError` pending the B6
Developer track — tests fail on missing behavior, not on a mocked
substitute, per the self-mock ban.
"""

from __future__ import annotations

from app.graph_projection import InMemoryGraphProjection


def _accepted_assertion(assertion_id="a1", matter_id="m1"):
    return {
        "id": assertion_id,
        "matter_id": matter_id,
        "status": "accepted",
        "subject_entity_id": "e1",
        "object_entity_id": "e2",
    }


def _proposed_assertion(assertion_id="a2", matter_id="m1"):
    return {
        "id": assertion_id,
        "matter_id": matter_id,
        "status": "proposed",
        "subject_entity_id": "e1",
        "object_entity_id": "e3",
    }


def test_project_then_default_view_shows_only_accepted():
    projection = InMemoryGraphProjection()
    projection.project_assertion(_accepted_assertion("a1"))
    projection.project_assertion(_proposed_assertion("a2"))

    visible = projection.get_visible_assertions("m1", show_unreviewed=False)
    ids = [a["id"] for a in visible]
    assert "a1" in ids
    assert "a2" not in ids


def test_show_unreviewed_mode_includes_proposed_with_distinct_state():
    projection = InMemoryGraphProjection()
    projection.project_assertion(_proposed_assertion("a2"))

    visible = projection.get_visible_assertions("m1", show_unreviewed=True)
    match = next(a for a in visible if a["id"] == "a2")
    assert match["status"] == "proposed"


def test_remove_assertion_drops_it_from_projection():
    projection = InMemoryGraphProjection()
    projection.project_assertion(_accepted_assertion("a1"))
    projection.remove_assertion("a1")

    visible = projection.get_visible_assertions("m1", show_unreviewed=True)
    assert all(a["id"] != "a1" for a in visible)


def test_rebuild_replaces_projection_entirely():
    projection = InMemoryGraphProjection()
    projection.project_assertion(_accepted_assertion("stale"))
    projection.rebuild([_accepted_assertion("fresh")])

    visible = projection.get_visible_assertions("m1", show_unreviewed=True)
    ids = [a["id"] for a in visible]
    assert "stale" not in ids
    assert "fresh" in ids


def test_projection_never_mixes_matters():
    projection = InMemoryGraphProjection()
    projection.project_assertion(_accepted_assertion("a1", matter_id="m1"))
    projection.project_assertion(_accepted_assertion("b1", matter_id="m2"))

    visible_m1 = projection.get_visible_assertions("m1", show_unreviewed=True)
    assert all(a["matter_id"] == "m1" for a in visible_m1)
