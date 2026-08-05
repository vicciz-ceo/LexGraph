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

HISTORY (Planner pass 10, repair): the two coupling tests below originally
used `shall include` as their synthetic example of an idiom `_IDIOM_RE`
did NOT recognize. Director ruling D-INCLUDES (2026-08-05) put the
`includes`-family verbs (`includes`/`shall include`) into this family's
defining vocabulary program-wide (100/100 hand-read definitional; broad
guards measured and rejected as pure recall loss -- see
`us_scoped_inline_entries.py`'s docstring for the one narrow guard that DID
survive, the PA "References to" construction-clause exclusion). Developer
fix cycle 5 shipped `shall include` into `_IDIOM_RE`, so entry 1 in both
tests stopped failing to parse -- the tests' own chosen example of "an
UNRECOGNIZED idiom" was no longer unrecognized, and both went RED for a
reason unrelated to the `_unmarked_multi_entries` coupling mechanism they
actually pin. Both tests' own original docstrings predicted this exact
failure mode ("SYNTHETIC probes... easier to construct than to find
verbatim in the wild"): a vocabulary-dependent example rots as the
vocabulary grows, and this program's vocabulary grew twice this sprint
(cycle 2, cycle 5).

Repaired here by swapping the placeholder idiom to `denotes` -- chosen and
VERIFIED directly against the shipped `_IDIOM_RE` (see
`_assert_idiom_is_unrecognized` below), not assumed to be "obviously"
outside the vocabulary; `denotes` shares no word or prefix with any current
alternative (`has`/`have the (same )?meaning(s)`, `shall be construed to
mean`, `shall include`, `shall mean`, `does not include`, `is defined as`,
`include(s)`, `means`, bare `is`). Both coupling tests below now call that
guard FIRST, so a third rot of this exact kind -- the vocabulary widening
again to include `denotes` specifically -- fails LOUDLY with a message
naming the real cause, instead of a bare `candidates == [...]` mismatch a
future reader would have to re-diagnose from scratch. This is the third
time this sprint a test was protected by a vocabulary accident rather than
a mechanism (the second: `test_us_scoped_inline_rules_negative_controls.py`
's `test_pa_construction_clause_guard_is_load_bearing_under_widened_vocabulary`,
re-authored under D-INCLUDES for the same reason); the guard below exists
to stop a fourth.
"""

from __future__ import annotations

from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions
from app.definition_links.rules.us_scoped_inline_shapes import _IDIOM_RE


def _assert_idiom_is_unrecognized(idiom_text: str) -> None:
    """Precondition guard for the two coupling tests below: both need a
    synthetic idiom that `_IDIOM_RE` genuinely does NOT recognize on entry
    1, so entry 1 fails to parse and it is the COUPLING (not the
    vocabulary) under test. Checked directly against the SHIPPED regex --
    exactly the check that, run against `shall include` before D-INCLUDES
    landed, would have caught this file's rot before it silently
    invalidated both tests (see module docstring's HISTORY note).

    If this assertion ever fires, the correct response is NOT to loosen
    it: pick a fresh placeholder idiom, re-verify it here, update the two
    tests' text, and extend this file's HISTORY note with what changed and
    why -- the same repair already performed once."""
    match = _IDIOM_RE.match(f"{idiom_text} ")
    assert match is None, (
        f"the placeholder idiom {idiom_text!r} used to pin _unmarked_multi_entries' "
        "\"stops at the first entry that fails to parse\" coupling is now RECOGNIZED "
        f"by _IDIOM_RE (matched {match.group(0)!r}) -- its premise "
        "(entry 1 fails to parse) no longer holds, so the coupling tests below would be "
        "pinning nothing. This is the exact rot that previously invalidated `shall "
        "include` under D-INCLUDES. Pick a new idiom NOT in _IDIOM_RE, update both "
        "coupling tests' text, and record the change in this file's HISTORY note."
    )


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
    """The GENERAL claim `_unmarked_multi_entries`'s own docstring makes:
    entry 1 uses `denotes` -- SYNTHETIC, chosen and verified (see
    `_assert_idiom_is_unrecognized`, called first below) to be genuinely
    UNRECOGNIZED by the shipped `_IDIOM_RE`, standing in for whatever real
    idiom gap the vocabulary has NOT yet closed at any given time; entry 2
    uses the ALREADY-recognized bare `includes`. Because entry 1 fails,
    `_unmarked_multi_entries` breaks out of its loop immediately -- entry
    2's own, individually-valid `"Beta" includes...` entry is NEVER EVEN
    ATTEMPTED, not merely also-failed. This is the coupling: fixing
    whatever root cause makes entry 1's idiom unrecognized would recover
    BOTH entries here, not just entry 1's -- the true blast radius of any
    one idiom gap is every list-mate after the first unrecognized-idiom
    entry in an unmarked colon-list, not just that entry itself.

    (Originally pinned with `shall include` as the synthetic unrecognized
    idiom -- see module docstring's HISTORY note for why that stopped
    working and why `denotes` replaced it.)"""
    _assert_idiom_is_unrecognized("denotes")
    text = (
        'As used in this section: "Alpha" denotes a small device. '
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
    transaction). Same `denotes` placeholder as the test above, same
    guard call, same HISTORY note."""
    _assert_idiom_is_unrecognized("denotes")
    text = (
        'As used in this section: "Beta" includes a larger device. '
        '"Alpha" denotes a small device.'
    )
    candidates = extract_us_scoped_inline_definitions(text)
    terms = {t for c in candidates for t in c.terms}
    assert terms == {"Beta"}, (
        f"expected only the FIRST entry ('Beta', which parses fine) to survive -- got {candidates!r}"
    )
