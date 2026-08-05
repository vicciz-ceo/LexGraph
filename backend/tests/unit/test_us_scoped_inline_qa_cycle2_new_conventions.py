"""QA cycle 2 (sprint 2026-08-04-defs-us-scoped-inline), independent U4/U1
re-sweep. A FRESH stratified random sample (5/jurisdiction, all 53
jurisdictions, 265 rows, seed 20260805 -- independent of QA cycle 1's own
20260804 sample), drawn before any trigger regex touched the text, judged
by 5 independent parallel readers given only a plain-language "does this
define any term" prompt (never this family's trigger vocabulary). 69 of 265
rows were judge-positive; triaged against the REAL, unmodified
`is_definitions_heading`/`derive_heading_from_body` (9 F3-rescued, not
ours) and the REAL `extract_us_scoped_inline_definitions` (28 genuinely
outside this family's own trigger vocabulary, e.g. cross-reference-only "as
defined in section N" pointer definitions with no local "as used in
this..." trigger at all). Of the remaining 32, 14 are already captured; 18
are CANDIDATE_MISS. Manual review of all 18 found most are the
ALREADY-KNOWN, already-accepted unquoted-term precision tradeoff (AK's bare
"knowingly has the meaning given in...", MA's bare "research means...", RI's
bare "killed in the line of duty shall mean...", SC's bare "an affiliated
group of automobile insurers includes...") or a genuinely new, out-of-
vocabulary scope phrase this family was never designed to recognize (CA's
"for purposes of the preceding sentence", not a scope unit at all) -- both
reported, neither pinned here (same class QA cycle 1 already routed to the
manager, not a new root cause).

Six of the 18, however, are confirmed misses squarely WITHIN this family's
OWN already-claimed vocabulary -- a recognized trigger, a quoted term, a
recognized (or should-be-recognized) idiom -- present, yet the rule
returns nothing. These 6 are DISTINCT from all 8 of QA cycle 1's root
causes (verified against that cycle's own list) and are pinned below, one
real corpus row per class, with corpus-wide volume measured directly
(`si_cycle2_qa_u4_newbugs_volume.py`, scratchpad) so the manager sees scale,
not just an anecdote:

1. Bare-`in this <unit>` trigger's connector does not tolerate a
   `the term(s)` phrase before the quote (unlike the STRONG trigger's own
   connector, which explicitly does) -- 12,189 hits / 9,510 rows / 52
   states for the `in this <unit>[:,] the terms?` shape corpus-wide.
2. `shall include` is not a recognized idiom (`_IDIOM_RE` has bare
   `includes?` and `shall mean`/`shall be construed to mean`, but no
   `shall include`) -- 6,926 hits / 4,817 rows / 50 states for a quote
   immediately followed by `shall include`.
3. A quote chain joined by `and` (two terms sharing one idiom) is not
   recognized -- only `or` is (`_QUOTE_CHAIN_SEP_RE`).
4. Georgia's own dominant drafting convention, `as used in this Code
   section` (two words, `Code section`, between `this` and the unit
   word), never matches `_UNIT_TAIL` (which requires the unit word
   directly after `this\\s+`) -- 1,299 rows use this exact phrase and only
   ONE Georgia row in the entire state corpus uses the plain `as used in
   this section` form our rule recognizes; `for purposes of this Code
   section` accounts for another 598 rows. This is a near-total,
   state-specific miss for this family's leading trigger phrase.
5. `unless the context otherwise indicates` (or equivalent) intervening
   between the trigger's unit word and `the following terms have the
   following meanings` is not tolerated by `_STRONG_CONNECTOR_RE` (which
   only tolerates one bounded `and <citation>` clause, not this) -- 2,113
   hits / 2,089 rows / 31 states for the combined
   `unless the context ... the following terms` shape.
6. `_single_entry` (the non-colon path) only ever extracts the FIRST
   quoted term + definition in its region; when a second, independent
   `and "Y" means Z` entry follows in the SAME region with no colon and no
   marker, it is silently dropped (not merely under-split -- the region
   never gets a second look). Distinct from cause 1/8's coupling (that is
   about `_unmarked_multi_entries` stopping after a colon; this is
   `_single_entry` never even trying for a second entry when there was no
   colon to begin with).

Per this sprint's QA role boundary: RED tests proving a defect, not a fix.
`us_scoped_inline.py`/`us_scoped_inline_shapes.py` are READ-ONLY to QA.
Every row below is real, unmodified, vendored corpus text
(`qa_cycle2_new_conventions_rows.json`, byte-verified against the live HF
snapshot via two independent fetches before being written into the
fixture) -- no invented text, no synthetic reproduction standing in for a
real miss.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "qa_cycle2_new_conventions_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def test_bare_in_trigger_does_not_tolerate_the_term_before_the_quote():
    """`USC_T18_C83_S1716E`: `"(C) Definition.--In this paragraph, the term
    "minor" means an individual who is less than the minimum age
    required..."` -- a clean bare-`in this <unit>` trigger, strict comma
    adjacency satisfied (`,` immediately follows `paragraph`), quoted term,
    recognized idiom (`means`). ROOT CAUSE: the bare-`in` trigger's
    connector (`_BARE_CONNECTOR_RE`) is only `\\s*(?:colon|comma)?\\s*` --
    unlike `_STRONG_CONNECTOR_RE`, it has no `(?:the terms?\\b\\s*|an?\\s+)?`
    tolerance, so `region_start` lands on `"the term "minor"...` rather
    than the quote itself, and `_match_quote_chain`'s anchored match fails
    immediately. 12,189 corpus-wide hits for this shape (9,510 rows, 52
    states)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["USC_T18_C83_S1716E"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "minor" in terms, (
        "the rule captured nothing for a clean 'In this paragraph, the term \"minor\" means...' "
        f"bare-in trigger -- got {candidates!r}"
    )


def test_shall_include_is_not_a_recognized_idiom():
    """`STATE_NY_ARSS_A2_T9_S89-H`: `"...As used in this section
    "creditable service" shall include (1) in the case of a sheriff..."` --
    a clean STRONG trigger, no connector filler, quoted term, immediately
    followed by `shall include`. ROOT CAUSE: `_IDIOM_RE` recognizes bare
    `includes?` and `shall mean`/`shall be construed to mean`, but not
    `shall include` -- the `shall`-prefixed cousin of `includes` that
    `shall mean` already proves the vocabulary intends to support. 6,926
    corpus-wide hits for a quote immediately followed by `shall include`
    (4,817 rows, 50 states)."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_NY_ARSS_A2_T9_S89-H"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "creditable service" in terms, (
        "the rule captured nothing for a clean 'As used in this section \"creditable service\" "
        f"shall include...' trigger -- got {candidates!r}"
    )


def test_quote_chain_and_separator_not_recognized_only_or_is():
    """`STATE_KS_C74_A21_S74-2113`: `"(e) For the purposes of this section,
    the terms "governing body" and "municipality" shall have the meanings
    ascribed to such terms in K.S.A. 12-105a..."` -- a clean STRONG
    trigger, two quoted terms sharing one idiom, joined by `and`. ROOT
    CAUSE: `_QUOTE_CHAIN_SEP_RE` only recognizes a literal `or` (optionally
    comma-preceded) as a chain separator between quotes -- the same
    structural shape as root cause 7's Tennessee `"X" or "Y"` fix, but with
    `and` instead, which breaks the chain at the first quote and leaves
    `_split_idiom_chain` looking for an idiom right after `"governing
    body"` where the text actually has `and "municipality"...`."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_KS_C74_A21_S74-2113"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert {"governing body", "municipality"} & terms, (
        "the rule captured nothing for a clean 'the terms \"X\" and \"Y\" shall have the "
        f"meanings...' and-joined quote chain -- got {candidates!r}"
    )


def test_georgia_code_section_naming_convention_not_recognized():
    """`STATE_GA_T10_C12_S10-12-16`: `"(a) As used in this Code section,
    " transferable record " means an electronic record that..."` --
    Georgia's OWN dominant drafting convention: `Code section` (two words)
    where every other jurisdiction's rows say plain `section`. ROOT CAUSE:
    `_UNIT_TAIL` requires the unit word directly after `this\\s+`;
    `this Code section` has an extra word (`Code`) in between, so neither
    `_STRONG_TRIGGER_RE` nor `_BARE_IN_TRIGGER_RE` ever matches. Measured
    directly against the real Georgia corpus: 1,299 rows use `as used in
    this Code section` and 598 more use `for purposes of this Code
    section`, against exactly ONE Georgia row anywhere in the corpus using
    the plain `as used in this section` form this rule recognizes -- a
    near-total, state-specific miss of this family's own leading trigger
    phrase."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_GA_T10_C12_S10-12-16"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t.strip() for c in candidates for t in c.terms}
    assert "transferable record" in terms, (
        "the rule captured nothing for 'As used in this Code section, \"transferable record\" "
        f"means...' -- got {candidates!r}"
    )


def test_intervening_unless_the_context_clause_breaks_the_following_terms_connector():
    """`STATE_ME_T20-A_P7_C606-B_S15671-A`: `"As used in this section,
    unless the context otherwise indicates, the following terms have the
    following meanings. A. "Funding public education from kindergarten to
    grade 12" means..."` -- a clean STRONG trigger, four quoted terms each
    with a recognized idiom. ROOT CAUSE: `_STRONG_CONNECTOR_RE` tolerates
    exactly one bounded `and <citation>` clause between the unit word and
    `the following terms ... mean(s)`, but not this extremely common
    boilerplate qualifier (`unless the context otherwise indicates`),
    which is neither an `and`-clause nor immediately `the following
    terms`. 2,113 corpus-wide hits for the combined `unless the context
    ... the following terms` shape (2,089 rows, 31 states) -- a
    widely-shared statutory idiom, not a Maine-specific one."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ME_T20-A_P7_C606-B_S15671-A"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "Funding public education from kindergarten to grade 12" in terms, (
        "the rule captured nothing for a clean 'As used in this section, unless the context "
        f"otherwise indicates, the following terms have the following meanings...' row -- got {candidates!r}"
    )


def test_single_entry_drops_a_second_and_joined_entry_in_the_same_region():
    """`STATE_NY_APBS_A2_S42-A`: `"For purposes of this section "major
    electric generating facility" means an electric generating facility
    with a nameplate generating capacity of twenty-five thousand kilowatts
    or more... and "major steam generating facility" means a steam
    generating facility with a generating capacity to be determined by the
    department."` -- ONE STRONG trigger (no colon, so `_single_entry`
    handles the whole region), TWO independent `"X" means Y` entries
    joined by a plain `and`. ROOT CAUSE: `_single_entry` extracts exactly
    one quote-chain-then-idiom entry and returns -- it never re-scans the
    remainder of its region for a follow-on entry the way
    `_unmarked_multi_entries` does for a colon-triggered region. The first
    entry (`major electric generating facility`) IS captured; the second
    is silently dropped. Distinct from cause 1/8's coupling (which is
    about `_unmarked_multi_entries` stopping after a colon-list's first
    parse failure) -- this region never had a colon, so
    `_unmarked_multi_entries` is never even reached; `_single_entry` itself
    has no multi-entry mechanism at all."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_NY_APBS_A2_S42-A"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    assert candidates, "expected at least the first entry to be captured -- got nothing at all"
    terms = {t.lower() for c in candidates for t in c.terms}
    assert any("steam" in t for t in terms), (
        "the row's SECOND 'and \"major steam generating facility\" means...' entry, sharing the "
        "same trigger region as the first (already-captured) entry, got no candidate at all -- "
        f"got {candidates!r}"
    )
