"""QA cycle 2 (sprint 2026-08-04-defs-us-scoped-inline). Item 8, specifically
requested: `_unmarked_multi_entries`'s own docstring claims it "[s]tops at
the first entry that fails to parse (conservative by design...)" -- so an
unrecognized idiom on entry N of an unmarked colon-list should silently
drop every list-mate AFTER it too, not just entry N itself. Tested
explicitly, both the brief's own literal recipe and the general claim.

SYNTHETIC probes (labelled, not corpus text) -- same methodology as
`test_us_scoped_inline_rules_negative_controls.py`'s mechanism-isolation
probes: this needs a precise, minimal two-entry unmarked colon-list with a
controlled idiom on each entry, which is easier to construct than to find
verbatim in the wild. `_unmarked_multi_entries` itself is exercised
identically either way (it only ever sees already-located region text, not
raw corpus rows).
"""

from __future__ import annotations

from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions


def test_the_briefs_own_recipe_is_then_includes_both_entries_captured():
    """The brief's literal recipe: entry 1 needs the bare-copula `is`
    (root cause 8), entry 2 uses `includes` (already-recognized). BOTH
    idioms are individually recognized today, so `_unmarked_multi_entries`
    never hits its own "first entry fails to parse" branch here -- this is
    a documented NEGATIVE result (no coupling defect for THIS specific
    pair), pinned so a future reader does not have to re-derive it."""
    text = 'As used in this section: "Alpha" is a small device. "Beta" includes a larger device.'
    candidates = extract_us_scoped_inline_definitions(text)
    terms = {t for c in candidates for t in c.terms}
    assert terms == {"Alpha", "Beta"}, (
        "the brief's own is-then-includes recipe was expected to capture BOTH entries -- "
        f"got {candidates!r}"
    )


def test_an_unrecognized_idiom_on_entry_one_silently_drops_a_recognized_entry_two():
    """The GENERAL claim `_unmarked_multi_entries`'s own docstring makes,
    proven with a real gap this cycle found (`shall include`, QA cycle-2
    finding B -- see `test_us_scoped_inline_qa_cycle2_new_conventions.py`):
    entry 1 uses the UNRECOGNIZED `shall include` idiom (fails to parse);
    entry 2 uses the ALREADY-recognized bare `includes`. Because entry 1
    fails, `_unmarked_multi_entries` breaks out of its loop immediately --
    entry 2's own, individually-valid `"Beta" includes...` entry is NEVER
    EVEN ATTEMPTED, not merely also-failed. This is the coupling: fixing
    root cause B (adding `shall include` to `_IDIOM_RE`) would recover
    BOTH entries here, not just entry 1's -- the true blast radius of that
    one gap is every list-mate after the first `shall include` entry in
    an unmarked colon-list, not just the `shall include` entry itself."""
    text = (
        'As used in this section: "Alpha" shall include a small device. '
        '"Beta" includes a larger device.'
    )
    candidates = extract_us_scoped_inline_definitions(text)
    assert candidates == [], (
        "expected BOTH entries lost (entry 1's unrecognized idiom stops the unmarked-list scan "
        f"before entry 2, whose OWN idiom is recognized, is ever tried) -- got {candidates!r}"
    )


def test_an_unrecognized_idiom_on_entry_two_does_not_affect_a_preceding_entry_one():
    """The asymmetry, confirmed: a parse failure on a LATER entry does not
    retroactively undo an earlier, already-parsed entry -- only entries
    AFTER the first failure are lost, matching "stops at the first entry
    that fails to parse" literally (a scan, not an all-or-nothing
    transaction)."""
    text = (
        'As used in this section: "Beta" includes a larger device. '
        '"Alpha" shall include a small device.'
    )
    candidates = extract_us_scoped_inline_definitions(text)
    terms = {t for c in candidates for t in c.terms}
    assert terms == {"Beta"}, (
        f"expected only the FIRST entry ('Beta', which parses fine) to survive -- got {candidates!r}"
    )
