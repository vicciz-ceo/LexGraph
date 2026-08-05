"""Sprint 2026-08-04-defs-us-scoped-inline (Planner pass 3, ruling S-R10;
xfail markers added passes 4-5 ruling S-R11; markers REMOVED pass 7 rulings
S-R14/S-R15 -- their job is done, this is now an ordinary live-path file).

This file's finding (subsection scope dead on the live path, S-R10) drove
the S-R11 interim (`"subsection"` -> `"local"`) and, once core's dispatch
sprint merged a `scope_unit_kind` field + 3-ladder `resolve_unit_path`
(S-R14), the Developer's revert of that interim. The manager's own probe
(sprint log, S-R14 section) validated the new mechanism end-to-end on THIS
exact Oregon row: both tripwires below XPASS once the rule derives
`scope_value`/`scope_unit_kind` from ONE call to core's resolver at the
trigger offset, instead of the two never-agreeing derivations S-R10 found.
Both `xfail(strict=True)` markers are REMOVED here -- the self-alarm did
its job (forced the revert to happen, not ossify) and continuing to mark
now-genuinely-passing assertions `xfail` would hide a real regression if
either direction ever broke again.

S-R15 (then OPEN, now RULED -- see director ruling D-S15 below): WHICH step
of the resolved path to stamp as `scope_unit_kind` was a named policy
question. This row's own defining clause happens to be `(2)(a)(A)(c)`, 4
levels deep with the SAME level reused for both directions below, so it
never by itself proved the innermost-step interim generalized -- Planner
pass 7's Task A report found real corpus rows (South Carolina) where it
does not, which is what drove the D-S15 escalation.

`test_us_scoped_inline_pipeline_live.py`'s U2 both-directions proofs cover
`scope="local"` and `scope="chapter"` only. `scope="subsection"` was never
proven on the live path -- only STAMPED (that file's own
`test_a_scope_unit_not_yet_enforced_by_matcher_is_still_stamped_faithfully`).
This file closes that coverage gap for DIRECTION 1 only (see below).

The risk (S-R10): `us_scoped_inline._subsection_label` derives the defining
subsection's label with its OWN regex (a paragraph-initial-marker
heuristic). `matcher._subsection_contains_offset` (`matcher.py:166`)
compares that label against a SECOND, INDEPENDENT derivation --
`profile.resolve_unit_path(article, char_offset)[0].value`, a flat,
sequential marker-kind-ladder scan living entirely in core's
`us_profile.py`. Nothing before this proved the two derivations ever
agree. If they disagree, `_subsection_contains_offset` returns False for
EVERY mention, including one sitting inside the definition's own
subsection -- a silent, total under-link, exactly what the absolute
zero-miss bar forbids and exactly what unit-green-but-live-dead testing
hides.

Deliberately does NOT assert the label's literal string (e.g. `"(c)"`)
anywhere -- core has a pending fix to `resolve_unit_path`'s handling of
Maine's inline `(NEW)`/`(AMD)`/`(AFF)` legislative-history annotations,
which will change nearest-marker derivation edge cases. This test pins
AGREEMENT/behavior only, so it survives that fix unchanged.

Uses the real, unmodified `STATE_OR_T22_C238_S238.300` (Oregon --
deliberately NON-Maine, so this proof is not confounded by that specific,
already-known annotation defect). The row's own real text defines
`"number of years of membership"` via `"(c) As used in this subsection,
... means ..."` nested inside subsection `(2)`, and NATURALLY (no
invented prose) reuses the same phrase twice more later in that SAME `(c)`
clause -- direction 1, kept below.

REMOVED (Planner pass 8, Task 1, director ruling D-S15): the second
direction this file used to carry --
`test_subsection_scoped_definition_does_not_link_a_mention_in_a_different_
subsection`, which called the row's own earlier `(2)(a)(A)`/`(2)(a)(B)`
mentions "a DIFFERENT subsection" and asserted they must NOT link.

That premise is factually wrong under D-S15. Reading the row's own raw
markers: the definition at `(c)` (offset 3401 in the normalized body) sits
inside top-level subsection `(2)` (marker at offset 1262); the mentions at
offsets 2046/2344 (`(2)(a)(A)`/`(2)(a)(B)`) are in the SAME top-level
subsection `(2)`, merely a different PARAGRAPH one level down. Under
D-S15 (`"this subsection"` scopes to the OUTERMOST subdivision) those
mentions SHOULD link, so the old assertion (`assert not uses_edges`) was
pinning an under-link as though it were correct behavior.

Simply flipping the assertion to `assert uses_edges` was rejected, not
attempted: this row's OWN `resolve_unit_path` result is independently
corrupted at exactly the offsets this proof would need. Core's resolver
returns top-level `digit '1'` for the trigger (offset 3405) because it
latches onto the CITATION `"under subsection (1) of this section"`
(offset ~1735) instead of the real structural marker `(2)` -- a pin-cite
stack-corruption defect, routed to core, not ours to fix. Because that
SAME citation precedes both the trigger and the two out-of-subsection
mentions in the raw text, all three coincidentally resolve to the same
bogus `'1'` -- so a flipped assertion would have passed, but for the WRONG
reason (a corrupted core resolver, not correct outermost semantics), which
would have baked a core defect into this suite as though it demonstrated
D-S15 correctness.

Chose option (a) from the pass-8 brief: re-author the direction-2 proof
onto a row whose resolver path is NOT corrupted, rather than (b) keep
Oregon with a corruption caveat. The genuine "same top-level subsection,
different paragraph, must link" proof (D-S15's whole point) now lives in
`test_us_scoped_inline_pipeline_subsection_outermost_live.py` (South
Carolina, upper_alpha-outermost ladder) and its digit-outermost sibling
(Washington) -- both byte-verified free of this corruption class, both
independently reproducing the manager's own S-R15-verdict harness result
on real, unmodified corpus text. Direction 1 below is UNAFFECTED by any
of this (it only proves "an in-subsection reuse links", true regardless
of which step is stamped, and regardless of the corruption, since trigger
and in-subsection mention share whatever step gets resolved) and is kept
exactly as before.
"""

from __future__ import annotations

import json
import pathlib
import re

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "us_scoped_inline_rows.json"
)

_TERM = "number of years of membership"
_DEFINING_SENTENCE_END = (
    "creditable service plus any remaining fraction of a year of creditable service."
)


def _row() -> dict:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(r for r in rows if r["act_id"] == "STATE_OR_T22_C238_S238.300")


def _clean(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def _uses_edges(result, db_session, definition_id):
    from app.models.assertion import Assertion

    return [
        a
        for a in result["created_assertions"]
        if a["assertion_type"] == "USES_DEFINITION"
        and db_session.get(Assertion, a["id"]).object_entity_id == definition_id
    ]


def test_subsection_scoped_definition_links_a_mention_inside_its_own_subsection(
    db_session, matter_with_users
):
    """Direction 1 of gate U2 for `scope="subsection"`: the real row's OWN
    later reuse of "number of years of membership", inside the SAME `(c)`
    clause that defines it, must get a `USES_DEFINITION` edge.

    Ground-truthed against the real, unmodified text (not assumed): the
    defining sentence ends at `_DEFINING_SENTENCE_END`; any occurrence of
    the term AFTER that point is a genuine in-subsection reuse, not the
    definition's own quoted entry.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.definition import Definition

    m = matter_with_users
    row = _row()
    text = row["text"]
    def_end = text.index(_DEFINING_SENTENCE_END) + len(_DEFINING_SENTENCE_END)
    in_subsection_offsets = [
        match.start() for match in re.finditer(re.escape(_TERM), text) if match.start() >= def_end
    ]
    assert in_subsection_offsets, (
        "fixture must reuse the term again inside its own defining subsection, "
        "after the defining sentence -- ground truth missing, test cannot prove anything"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Oregon Revised Statutes (subsection-scope live agreement proof, in-subsection direction)",
        rows=[_clean(row)],
        jurisdiction="US-OR",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    nym_defs = [d for d in result["created_definitions"] if _TERM in d["terms"]]
    assert nym_defs, "the real Oregon subsection-scoped definition was never captured at all"
    definition_id = nym_defs[0]["id"]
    definition_row = db_session.get(Definition, definition_id)
    assert definition_row.scope == "subsection"

    uses_edges = _uses_edges(result, db_session, definition_id)
    assert uses_edges, (
        "a mention of 'number of years of membership' inside its OWN defining subsection "
        "got no USES_DEFINITION edge at all. Per S-R14, scope_value/scope_unit_kind are "
        "now both derived from ONE call to profile.resolve_unit_path at the trigger offset "
        "-- if this fails, that mechanism itself (or matcher._subsection_contains_offset's "
        "consumption of it) has regressed. Report to the manager; do not patch "
        "us_scoped_inline.py to route around a core (us_profile.py) defect."
    )


# Direction 2 (a mention in a genuinely different top-level subsection must
# NOT link) used to live here, on this same Oregon row. REMOVED, Planner
# pass 8, Task 1, per director ruling D-S15 -- see the module docstring
# above for why this row cannot supply that proof (its own resolved path is
# pin-cite-corrupted at the relevant offsets) and where the real proof now
# lives (`test_us_scoped_inline_pipeline_subsection_outermost_live.py` and
# its Washington sibling).
