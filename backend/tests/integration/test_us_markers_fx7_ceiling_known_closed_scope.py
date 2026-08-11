"""FX7 (issue #27, sprint 2026-08-10-green-the-suite) -- Planner pass on the
director's ruling: issue #21's discriminator improves 11,977 rows but costs
41 lost terms to `MAX_CLEAN_DEFINITION_LENGTH` (the 3,000-char last-resort
ceiling in `us_markers_boundary.close_entries`). The ruling asked whether
`bounded` should be widened so an entry the discriminator "deliberately
closed by reaching the next captured quote with zero hard-stops" survives
regardless of length, since that shape is *known-closed*, not runaway.

**Finding (evidence, not a fixture): the premise does not hold.** Every one
of the 41 lost terms was measured directly against the real corpus this
pass (`mgr_lost_term_triage_result.json`, `devD_item21_blast_radius_result
.json` -- manager/developer triage handed to this Planner) and, independently,
re-derived here structurally against `close_entries`'s own `starts`/
`hard_stops` machinery: **41/41 have `has_next_term=False`** (no subsequent
recognized quote+idiom term anywhere in the remaining text) **and zero
hard-stops** in range. Zero of the 41 match the "reaches the next captured
quote with zero hard-stops" shape the brief describes -- that shape is
`has_next_term=True`, and `close_entries`'s own
`bounded = bool(candidate_stops) or has_next_term` *already* grants it an
unconditional ceiling exemption today, regardless of hard-stop count. There
is no gap there to close.

The 41 are instead the OTHER shape this module's own docstring names as the
ceiling's actual, intended target: "ran off the end of the text with
nothing to close it." Byte-verified spot checks against the real corpus
(not committed here, per the QA1 Q4 fixture-vendoring norm and M-R107 --
reported as evidence, not encoded as a keyed test) confirm real swallowed
content, not clean closure: `STATE_NJ_T27_C1A_S1A-3.1`'s `"Department"`
(true definition: `"the Department of Transportation."`, ~34 chars) runs
10,319 chars into an entirely unrelated `"New Jersey tolling entity"`
clause because that term's own idiom ("shall include") is not one
`_TIGHT_IDIOM_RE` recognizes, so it never becomes a `starts` entry and
never bounds anything; `USC_T5_C75_S7511`'s `"furlough"` (true definition:
one ~140-char sentence, the SMALLEST of the 41 overruns at 3,017 chars)
swallows an entire unrelated `"(b) ... (1) ... (2) ..."` eligibility list.
Both are the identical FED/TN/AZ "unbounded last entry" defect family this
module's docstring already documents, not a new discriminator-created
false positive.

**Why the guard cannot be safely narrowed to recover them**: the ONLY
signal available at the point `close_entries` decides `bounded` for a
last-`starts`-entry candidate is "no hard-stop found before end-of-text."
That is exactly the same signal both a genuinely long-but-closed last entry
(architecturally possible, if rare) and a genuine swallow share -- there is
no third signal in the data to tell them apart. Any widening broad enough
to recover the 41 (treating "ran to end of text with zero hard-stops" as
bounded) would with equal force exempt the classic runaway shapes the
ceiling exists for (FED's 22,880-char "State" swallow, etc.) -- see
`test_genuinely_unbounded_last_entry_still_dropped_by_the_ceiling` below,
which is the concrete, executable version of this argument: it fails the
moment `bounded` is widened that way.

**Consequently there is no RED test in this file.** `test_
known_closed_by_next_term_already_survives_the_ceiling_regardless_of_length`
below is GREEN today -- it is the structural proof that the ONE signal the
brief hypothesized (`has_next_term=True`, zero hard-stops) is *already* the
right, already-correctly-implemented exemption, not a gap. Per M-R107 both
tests below are built from the general STRUCTURAL shape (synthetic
definitions text engineered to have zero digit/letter/dot markers anywhere,
so no hard-stop can accidentally fire), not from any of the 41 act_ids or
term names.
"""

from __future__ import annotations

from app.definition_links.rules.us_markers_boundary import (
    MAX_CLEAN_DEFINITION_LENGTH,
    extract_quote_anchored_entries,
)

# A long, ordinary-prose sentence containing no digits, no parentheses, no
# colons, no dashes, and no quote characters -- so repeating it can never
# accidentally create a `_DIGIT_MARKER_RE`/`_LETTER_MARKER_RE`/
# `_DIGIT_DOT_MARKER_RE`/`_LETTER_DOT_MARKER_RE` hard-stop or a
# `_LIST_INTRODUCER_BEFORE_RE` list-introducer, and can never contain a
# nested quoted term of its own. Repeated well past `MAX_CLEAN_DEFINITION_
# LENGTH` (3,000 chars) to exercise the ceiling honestly.
_MARKER_FREE_SENTENCE = (
    "This clause continues at exceptional length purely as a matter of "
    "ordinary statutory drafting style, adding qualifying language after "
    "qualifying language without ever introducing a numbered or lettered "
    "sub item, a colon, or a dash, so nothing in this padding can ever be "
    "mistaken for a marker boundary. "
)
_LONG_MARKER_FREE_PADDING = _MARKER_FREE_SENTENCE * 30

assert len(_LONG_MARKER_FREE_PADDING) > MAX_CLEAN_DEFINITION_LENGTH, (
    "test padding must itself exceed the ceiling for either test below to "
    "be meaningful"
)


def test_known_closed_by_next_term_already_survives_the_ceiling_regardless_of_length():
    """The ONLY structural shape that can honestly be called "the
    discriminator deliberately closed this by reaching the next captured
    quote with zero hard-stops": a `starts` entry with `has_next_term=True`
    and no hard-stop marker anywhere between it and that next term. Per
    `close_entries`'s own `bounded = bool(candidate_stops) or has_next_term`,
    this is UNCONDITIONALLY exempt from `MAX_CLEAN_DEFINITION_LENGTH` today
    -- proving `bounded` is *already* the correct signal for this shape, so
    there is nothing to widen here. (GREEN today; this is evidence for the
    Planner's feasibility finding, not a RED recovery test -- see this
    file's own docstring.)"""
    text = f'"Alpha" means {_LONG_MARKER_FREE_PADDING}"Beta" means the second concept.'
    entries = dict(extract_quote_anchored_entries(text))

    assert "Alpha" in entries, (
        "a known-closed entry (bounded by a real next quoted+idiom term, "
        "zero hard-stops in between) must survive regardless of length -- "
        "it did not even get extracted at all"
    )
    assert len(entries["Alpha"]) > MAX_CLEAN_DEFINITION_LENGTH, (
        f"test setup error: 'Alpha' definition ({len(entries['Alpha'])} chars) "
        f"must itself exceed the ceiling for this to prove anything"
    )
    assert entries["Alpha"] == _LONG_MARKER_FREE_PADDING.strip(), (
        f"'Alpha' must close exactly at 'Beta''s own quote, not before or "
        f"after: got {entries['Alpha'][:80]!r}...{entries['Alpha'][-80:]!r}"
    )
    assert entries.get("Beta") == "the second concept.", (
        f"sanity: 'Beta' itself must still be captured correctly, got {entries.get('Beta')!r}"
    )


def test_genuinely_unbounded_last_entry_still_dropped_by_the_ceiling():
    """The safety test protecting the ceiling's real purpose: a `starts`
    entry that is the LAST recognized term in the text (`has_next_term=
    False`) with zero hard-stops anywhere before the end -- the exact
    structural shape of all 41 of issue #21's real lost terms (byte-verified
    against the corpus this pass, see this file's own docstring; e.g.
    `STATE_NJ_T27_C1A_S1A-3.1`'s `"Department"` and `USC_T5_C75_S7511`'s
    `"furlough"`, both genuine swallows of unrelated trailing statutory
    text, not clean closures) -- must still be DROPPED. This is what makes
    an attempted "fix" that recovers the 41 by broadening `bounded` to cover
    "ran to end of text with zero hard-stops" indistinguishable from
    deleting the guard: it would flip this exact assertion. If this test
    ever goes RED, the guard's real purpose (dropping genuinely unrecognized
    runaway text) has been silently lost -- it must fail loudly, not be
    weakened to accommodate whatever change broke it."""
    text = f'"Gamma" means {_LONG_MARKER_FREE_PADDING}'
    entries = dict(extract_quote_anchored_entries(text))

    assert "Gamma" not in entries, (
        f"a genuinely unbounded last entry (no next term, no hard-stop, "
        f"{len(_LONG_MARKER_FREE_PADDING.strip())} chars past the "
        f"{MAX_CLEAN_DEFINITION_LENGTH}-char ceiling) must still be dropped -- "
        f"got {entries.get('Gamma', '<absent>')[:120]!r}. The ceiling's own "
        f"purpose (see us_markers_boundary.py's module docstring, "
        f"'MAX_CLEAN_DEFINITION_LENGTH') is to catch exactly this shape; a "
        f"change that lets this survive has made the guard a no-op for "
        f"genuine runaway text, not scoped it."
    )
