"""RED + negative-control structural tests (sprint 2026-08-20-defs-
boundary-idioms, pass 2 amendment, Item 3) for the same-term-collision
dedup fix in `extract_quote_anchored_entries`
(`backend/app/definition_links/rules/us_markers_boundary.py`).

Per manager ruling M-R107: every fixture here is fully synthetic, built
from unseen identifiers -- no jurisdiction, term, section number, date, or
title is keyed on. Proves the GENERAL mechanism (both named shapes: the
"displacement family" and the "list-introducer corruption"), not a fact
about any one real row -- those are covered separately by
`test_us_markers_dedup_swap_hazard_recovery.py` (WA "active efforts" / NY
"General service lamp"). Engine-level (`extract_quote_anchored_entries`),
matching `test_us_markers_boundary_idioms_structural_controls.py`'s own
style."""
from __future__ import annotations

from app.definition_links.rules.us_markers_boundary import extract_quote_anchored_entries


# --- RED: positive recovery, "displacement family" shape -------------------


def test_red_idiom_inside_body_continuation_no_longer_displaces_the_complete_definition():
    """'fenwick term' is quoted TWICE: first inside what LOOKS like a
    top-level 'shall include' entry but is actually an enumeration
    continuation (mirrors WA 'active efforts' branch (a)), second as a
    genuinely complete, self-contained 'means' definition (mirrors branch
    (b)). Today, `extract_quote_anchored_entries` returns BOTH as separate
    `starts` entries in text order with no collision handling -- the
    downstream persist-time dedup (first-occurrence-wins) picks the
    displacing continuation. Once Item 3's collision filter runs, only the
    'means'-recognized (pre-Item-1 idiom) occurrence must survive."""
    text = (
        '"fenwick term" shall include the following sub-items: '
        "(i) sub-item one; and (ii) sub-item two. "
        '"fenwick term" means a complete alternate definition entirely on its own.'
    )
    entries = dict(extract_quote_anchored_entries(text))

    assert entries.get("fenwick term") == (
        "a complete alternate definition entirely on its own."
    ), (
        f"RED: 'fenwick term' must resolve to its complete, self-contained "
        f"'means' definition, not the displacing 'shall include' "
        f"continuation. Got: {entries.get('fenwick term')!r}"
    )
    all_matches = [d for t, d in extract_quote_anchored_entries(text) if t == "fenwick term"]
    assert len(all_matches) <= 1 or all(
        m == "a complete alternate definition entirely on its own." for m in all_matches
    ), (
        f"the displacing continuation must not survive as a competing "
        f"'fenwick term' entry at all: {all_matches!r}"
    )


# --- RED: positive recovery, "list-introducer corruption" shape ------------


def test_red_bare_list_introducer_no_longer_displaces_the_substantive_definition():
    """'Corvellan lamp' is quoted TWICE: first as a top-level 'shall
    include' entry whose own captured text is a bare list-introducer
    phrase (mirrors NY 'General service lamp' item 44), second, nested
    inside that same enumeration, as the genuine substantive 'means'
    definition (mirrors NY sub-item (c)). Today the bare introducer wins
    the dedup. Once Item 3's collision filter runs, only the 'means'-
    recognized occurrence must survive."""
    text = (
        '"Corvellan lamp" shall include the following definitions: '
        '(a) "Corvellan module" means a component part. '
        '(b) "Corvellan lamp" means a complete standalone fixture meeting '
        "every applicable safety standard."
    )
    entries = dict(extract_quote_anchored_entries(text))

    assert entries.get("Corvellan lamp") == (
        "a complete standalone fixture meeting every applicable safety standard."
    ), (
        f"RED: 'Corvellan lamp' must resolve to its substantive 'means' "
        f"definition, not the bare list-introducer ('the following "
        f"definitions:', not a definition at all). Got: "
        f"{entries.get('Corvellan lamp')!r}"
    )
    assert entries.get("Corvellan module") == "a component part.", (
        "sanity: the unrelated sibling term must still be captured, unaffected"
    )


# --- Negative controls: GREEN today, MUST STAY GREEN after Item 3's fix ----


def test_negative_control_all_new_idiom_collision_is_left_untouched():
    """'Thornwick unit' is quoted TWICE, but BOTH occurrences are
    recognized ONLY by idioms this sprint's Item 1 widened ('shall
    include' and 'has the same meaning') -- there is no pre-existing
    (means/shall mean/bare has-the-meaning) occurrence to prefer. Item 3's
    collision filter only acts when at least one colliding occurrence is
    pre-existing-idiom-recognized; with none, this collision is NOT this
    item's concern and must be left exactly as it is today (both entries
    still produced by this function -- the downstream persist-time dedup,
    unmodified by this sprint, resolves it the same way it always has)."""
    text = (
        '"Thornwick unit" shall include a first shape entirely. '
        '"Thornwick unit" has the same meaning as that term is defined '
        "elsewhere in this chapter."
    )
    entries = [d for t, d in extract_quote_anchored_entries(text) if t == "Thornwick unit"]
    assert entries == [
        "a first shape entirely.",
        "as that term is defined elsewhere in this chapter.",
    ], (
        f"an all-new-idiom collision (no pre-existing occurrence to prefer) "
        f"must be returned exactly as today, both entries intact and in text "
        f"order, unaffected by Item 3's fix: got {entries!r}"
    )


def test_negative_control_a_single_uncontested_means_entry_is_unaffected():
    """No collision at all: 'Marrowgate' is quoted once, via 'means'. Item
    3's fix only ever acts on a term with 2+ occurrences in the same call
    -- a single entry must be completely untouched."""
    text = '"Marrowgate" means an uncontested, single-occurrence definition.'
    entries = dict(extract_quote_anchored_entries(text))
    assert entries.get("Marrowgate") == "an uncontested, single-occurrence definition."
