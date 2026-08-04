"""QA cycle 1 (sprint 2026-08-04-defs-us-scoped-inline), independent
verification pass -- U4/U1 findings.

Gate U4 required a zero-miss sweep with a P-R7-compliant denominator built
INDEPENDENTLY of this family's own trigger regex (D12): a stratified random
sample of 530 raw rows (10/jurisdiction, all 53 jurisdictions), drawn
BEFORE any trigger regex touched the text, semantically judged (7 parallel
independent readers, cross-validated at 96.7% agreement on a 60-row
sub-sample) for "does this text define any term, in any phrasing." Of 82
judge-confirmed genuine definitions, 22 were NOT captured by the shipped
`extract_us_scoped_inline_definitions`. Of those 22, at least 12 (across 8
distinct root causes) are confirmed misses squarely WITHIN this family's
OWN already-claimed vocabulary -- a recognized STRONG trigger, a quoted
term, a recognized defining idiom, or a colon-then-list -- present, yet the
rule still returns nothing. This file pins 6 of those (one real, unmodified
corpus row per distinct root cause, chosen as the clearest representative
of each class; the other 6 confirmed rows -- STATE_OH_T17_C1707_S1707.47,
STATE_OR_T62_C835_S835.200, STATE_DC_T47_C20_S47-2002.01,
STATE_NY_ARPP_A8_S280-D, STATE_MS_T27_C29_S51-5,
STATE_FL_TXVIII_C253_S253.04 -- are the same root causes on different
states/rows, documented but not independently re-pinned here to keep this
file under the style gate; full per-row diagnosis is in the QA cycle-1
report).

Per this sprint's own QA role boundary: these are RED tests proving a
defect, not a fix. `us_scoped_inline.py` is READ-ONLY to QA. Every row
below is real, unmodified, vendored corpus text
(`qa_cycle1_missed_conventions_rows.json`, byte-verified against the live
HF snapshot at fetch time) -- no invented text, no synthetic reproduction
standing in for a real miss.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "qa_cycle1_missed_conventions_rows.json"
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


def test_colon_then_unmarked_quoted_list_is_not_split_into_zero_entries():
    """`STATE_IL_C20_A2105_S2105-370`: `"(a) As used in this Section:
    "Cultural competency" means a set of integrated attitudes... "Health
    care professional" means a person licensed..."` -- a clean, unambiguous
    STRONG trigger + colon + TWO quoted terms each followed by a recognized
    idiom ("means"). ROOT CAUSE: `_leading_events` routes every
    colon-triggered event to `_multi_entries`, which ONLY recognizes
    entries prefixed by a parenthesized marker (`_MARKER_QUOTE_RE`); a
    colon-then-list with NO marker before each quoted term (a real,
    common convention -- this row uses it for both its terms) matches
    zero markers, so `_multi_entries` returns [] and `_single_entry` is
    never tried as a fallback. Result: the ENTIRE two-term block is lost,
    not just under-split -- the single most severe miss class found this
    cycle."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_IL_C20_A2105_S2105-370"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert {"Cultural competency", "Health care professional"} <= terms, (
        "the rule captured nothing at all from a clean 'As used in this Section: "
        '"X" means... "Y" means...\' colon-list with no per-entry marker -- '
        f"got {candidates!r}"
    )


def test_colon_then_unmarked_quoted_list_seven_terms_virginia():
    """`STATE_VA_T58.1_SI_C3_A10_S58.1-405.1`: `"A. For purposes of this
    section: "Authority" means... "Eligible company" means... ... "Traded-
    sector company" means..."` -- SAME root cause as the Illinois case
    above (unmarked colon-list, no parenthesized marker between any of the
    7 entries, only blank lines), a second, independent real-corpus
    confirmation that this is a recurring convention, not a one-off."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_VA_T58.1_SI_C3_A10_S58.1-405.1"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "Authority" in terms, (
        "the rule captured nothing from a clean 7-term unmarked colon-list -- "
        f"got {candidates!r}"
    )


def test_chained_parenthetical_unit_qualifiers_after_the_trigger_colorado():
    """`STATE_CO_T39_A27_P1_S39-27-102`: `"For purposes of this subsection
    (1)(a)(I)(A), "special fuel" does not include liquefied petroleum
    gas."` -- ROOT CAUSE: `_UNIT_TAIL`'s optional parenthetical-qualifier
    group (`(?:\\s*\\([^)\\n]{1,12}\\))?`) only consumes ONE parenthetical
    group. A CHAIN of qualifiers immediately after the unit word --
    `(1)(a)(I)(A)`, a real, unremarkable Colorado numbering convention --
    leaves `(a)(I)(A)` unconsumed directly before the comma+quote, which
    breaks both the connector match and the quote-adjacency check that
    follows. The trigger is textbook STRONG-trigger-vocabulary
    ("for purposes of this subsection") with a quoted term and a
    recognized idiom ("does not include") immediately after -- every
    ingredient the rule's own docstring claims to handle, absent only the
    chained-qualifier tolerance."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_CO_T39_A27_P1_S39-27-102"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "special fuel" in terms, (
        "the rule captured nothing from a 'for purposes of this subsection "
        "(1)(a)(I)(A), \"special fuel\" does not include...' entry -- the chained "
        f"parenthetical qualifier after the unit word broke recognition -- got {candidates!r}"
    )


def test_intervening_secondary_citation_clause_breaks_recognition_delaware():
    """`STATE_DE_T6_C15_SIX_S15-901`: `"(a) As used in this section and in
    Section 15-105 of this title, the term "other entity" means a
    corporation..."` -- ROOT CAUSE: `_STRONG_CONNECTOR_RE` has zero
    tolerance for text between the unit word and "the term"/the colon --
    it expects `this section` to be followed (after an optional comma) by
    one of a small fixed set of connector phrases immediately. A second,
    parallel citation ("and in Section 15-105 of this title") inserted
    before "the term X means" -- a completely ordinary way to name two
    co-extensive scope units in one trigger -- makes the connector stop
    short, so the quote-match position never reaches the actual quoted
    term at all. This is not a one-off: the same shape (an "and [citation]"
    clause between the unit word and the definiendum) is independently
    confirmed on two more real rows this cycle
    (STATE_OH_T17_C1707_S1707.47's "and section 1707.471 of the Revised
    Code", STATE_OR_T62_C835_S835.200's "and ORS 835.210 (...)")."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_DE_T6_C15_SIX_S15-901"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "other entity" in terms, (
        "the rule captured nothing from 'As used in this section and in Section "
        "15-105 of this title, the term \"other entity\" means...' -- the intervening "
        f"citation clause broke recognition -- got {candidates!r}"
    )


def test_plural_have_the_same_meaning_as_is_not_recognized_tennessee():
    """`STATE_TN_T55_C9_S55-9-414`: `"As used in this section, the terms
    "emergency equipment company" or "company" have the same meaning as
    defined in Section 55-9-402."` -- ROOT CAUSE: `_IDIOM_RE` recognizes
    singular `has the same meaning as` only. A plural subject ("the terms
    ... have...") is the grammatically ordinary way to phrase a two-way
    alias ("X" or "Y"), and it fails the idiom match outright -- not a
    fuzzy-match miss, a literal singular/plural vocabulary gap."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_TN_T55_C9_S55-9-414"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "emergency equipment company" in terms, (
        "the rule captured nothing from 'the terms \"emergency equipment company\" or "
        "\"company\" HAVE the same meaning as...' -- only singular 'has' is recognized -- "
        f"got {candidates!r}"
    )


def test_bare_copula_is_without_defined_as_is_not_recognized_north_dakota():
    """`STATE_ND_T50_C50-25.1_S50-25.1-09.1`: `"For purposes of this
    subsection, an "adverse action" is action taken by an employer
    against the individual..."` -- ROOT CAUSE: `_IDIOM_RE` requires one of
    a fixed idiom list (`means`/`shall mean`/`is defined as`/`includes`/
    etc.); a bare copula `is` (without `defined as` immediately after) is
    not in that list, so `_split_idiom` finds neither a recognized idiom
    nor a comma right after the quote and returns nothing. `"X" is Y`
    (dropping "defined as") is a real, plain-English defining idiom this
    row uses natively."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_ND_T50_C50-25.1_S50-25.1-09.1"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    terms = {t for c in candidates for t in c.terms}
    assert "adverse action" in terms, (
        "the rule captured nothing from 'For purposes of this subsection, an "
        "\"adverse action\" IS action taken by...' -- bare copula 'is' (no 'defined as') "
        f"is not a recognized idiom -- got {candidates!r}"
    )
