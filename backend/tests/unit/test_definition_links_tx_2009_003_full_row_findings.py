"""RED tests for sprint 2026-08-04-defs-us-multiterm, ruling M-R18 --
pinning the FULL, unmodified `STATE_TX_Cgv_C2009_S2009.003` row's real
candidate-level duplication, driven through the real dispatching
`USProfile.extract_definitions_from_section` method (`get_profile(...)`),
never the bare free function.

Live-verified (2026-08-05) today's real output for the full row:

    total candidates: 9
    term counts: {'Alternative dispute resolution procedure': 1,
                   'Governmental body': 2, 'State agency': 1,
                   'contested case': 2, 'party': 2, 'person': 2,
                   'rule.': 2}

**Every one of the 5 terms this sprint's own F5/F6 work is meant to make
resolvable is double-counted -- but by TWO DIFFERENT, INDEPENDENT root
causes, not one.** Per the sprint manager's own instruction ("if they
share a test, fixing one masks the other"), that same discipline is
applied here to ALL five terms, not only the trailing-period case (see
below) -- each is its OWN test function, and the two mechanisms are never
conflated:

1. **`"Governmental body"` -- ruling M-R18, genuinely new.** Root cause
   confirmed live: ruling U-R10's TX-scoped parent-redirect
   `EntrySplitterRule` (`rules/us_multiterm_shared_clause.py`'s
   `_split_parent_redirect_whole_text`) re-contributes the WHOLE section
   text as an extra block. Baseline's own per-block pass already captures
   `"Governmental body"` correctly from its OWN small block. The
   Developer's finding-4 leading-quote guard
   (`rules/us_inline_parenthetical.py`'s `_parse_block`, pinned by
   `test_definition_links_leading_quote_guard.py`, M-R16) is SUPPOSED to
   stop a `TermClauseRule` pass from re-emitting a term baseline already
   captured for THAT block -- but the guard compares against the
   CONTAINING block's OWN leading quote, and the whole-text block's own
   leading token is `"In this chapter:"`, not a quote at all
   (`_leading_quote_term(...)` is `None`). So when `_parse_block` runs on
   the whole-text block, its unguarded `_cross_reference_candidates` scan
   re-discovers `"Governmental body"` a second time. This is a genuinely
   NEW candidate-level defect, first found while pinning M-R16 -- no
   existing test currently checks this term's COUNT (only its presence,
   e.g. `test_multiterm_f5_shared_clause.py`'s `working_term` regression
   guard).

2. **`"contested case"` / `"party"` / `"person"` / `"rule."`
   -- Residual ledger R1, PRE-EXISTING, unrelated to the guard.** This
   is NOT M-R18's mechanism. Root cause, matching the ledger's own R1
   entry verbatim ("The section now yields 8 candidates: our correct
   combined N-term row, the 4 ORIGINAL degenerate 1-term rows (`;`,
   `""`), and 3 already-working entries"): F5's own
   `_parent_redirect_candidates` (`rules/us_multiterm_shared_clause.py`)
   produces ONE combined 4-term candidate `("contested case", "party",
   "person", "rule.")` from the SAME whole-text block, while baseline's
   OWN per-block pass ALSO independently produces 4 separate degenerate
   1-term candidates (`";"`, `"; and"`, `""` as their `definition_text`)
   from the 4 ORIGINAL lettered blocks -- a completely different pair of
   rule modules and dispatch kinds (F5's `TermClauseRule` vs baseline's
   own per-block splitter) than what produces Governmental body's
   duplicate. R1 is EXPLICITLY on the sprint's own ledger, with its OWN
   owner ("markers", entry-boundary damage per M-R5) and its OWN closing
   condition ("markers' entry-boundary work lands and the degenerate
   rows stop being produced") -- NOT this sprint's to fix, and NOT the
   same defect M-R16/M-R18 investigated. Confirms the count: R1's own
   documented "8 candidates" does NOT include Governmental body's extra
   duplicate -- this file's own live measurement above found 9 total,
   exactly R1's 8 plus M-R18's 1 additional. Pinned here as separate,
   individually-named tests (not folded into the Governmental body pin)
   specifically so a fix to M-R18 (the guard/EntrySplitterRule
   interaction) is never mistaken for also fixing R1 (markers' own,
   differently-owned mechanism), and vice versa.

Live-path discipline: every test below drives the REAL, current
`USProfile.extract_definitions_from_section` method via `get_profile(...)`
on the real, full, unmodified fixture row -- never an excerpt, never the
bare free function.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.definition_links.profiles import get_profile

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "multiterm_f5_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _term_counts() -> Counter:
    row = _load_rows()["STATE_TX_Cgv_C2009_S2009.003"]
    profile = get_profile("US-TX")
    scope = profile.determine_scope(row["text"])
    candidates = profile.extract_definitions_from_section(row["text"], scope=scope)
    return Counter(t for c in candidates for t in c.terms)


# --- M-R18: guard defeated by the TX EntrySplitterRule's whole-text block -


def test_tx_governmental_body_captured_exactly_once_through_full_dispatch():
    """M-R18 (new). See module docstring, item 1, for the full root-cause
    trace (leading-quote guard's per-block comparison never sees a term
    reappearing inside the EntrySplitterRule's own whole-text
    contribution)."""
    counts = _term_counts()
    assert counts["Governmental body"] == 1, (
        f'"Governmental body" was captured {counts["Governmental body"]} times through the '
        f"full, real dispatching path -- expected exactly 1. Ruling M-R18: the finding-4 "
        f"leading-quote guard (rules/us_inline_parenthetical.py's _parse_block) cannot "
        f"suppress this, because the duplicate comes from the TX-scoped parent-redirect "
        f"EntrySplitterRule's whole-text block, whose OWN leading token is 'In this "
        f"chapter:' (not a quote), so the guard's per-block comparison never fires. All "
        f"term counts: {dict(counts)!r}"
    )


# --- Residual ledger R1: pre-existing, NOT M-R18, owned by markers --------


def test_tx_contested_case_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2). Kept as its OWN test, separate from Governmental body's M-R18
    pin above, because the two have different root causes, different
    owners, and different closing conditions on the ledger -- a fix to
    one must never be mistaken for a fix to the other."""
    counts = _term_counts()
    assert counts["contested case"] == 1, (
        f'"contested case" was captured {counts["contested case"]} times through the full, '
        f"real dispatching path -- expected exactly 1. This is Residual ledger R1 (owned by "
        f"markers, NOT M-R18/this sprint's own F6 guard defect): baseline's own degenerate "
        f'per-block candidate (definition_text=";") coexists with F5\'s correct combined '
        f"4-term candidate. All term counts: {dict(counts)!r}"
    )


def test_tx_party_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2 and the sibling `contested_case` test above for the shared
    root cause)."""
    counts = _term_counts()
    assert counts["party"] == 1, (
        f'"party" was captured {counts["party"]} times through the full, real dispatching '
        f"path -- expected exactly 1. Residual ledger R1 (owned by markers): baseline's own "
        f'degenerate per-block candidate (definition_text=";") coexists with F5\'s correct '
        f"combined 4-term candidate. All term counts: {dict(counts)!r}"
    )


def test_tx_person_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2 and the sibling `contested_case` test above for the shared
    root cause)."""
    counts = _term_counts()
    assert counts["person"] == 1, (
        f'"person" was captured {counts["person"]} times through the full, real dispatching '
        f"path -- expected exactly 1. Residual ledger R1 (owned by markers): baseline's own "
        f'degenerate per-block candidate (definition_text="; and") coexists with F5\'s correct '
        f"combined 4-term candidate. All term counts: {dict(counts)!r}"
    )


def test_tx_rule_entry_captured_exactly_once_through_full_dispatch():
    """Residual ledger R1 (pre-existing, NOT M-R18 -- see module docstring
    item 2). DEDUP COUNT ONLY -- this test intentionally checks the term
    string exactly as captured TODAY (`"rule."`, with the trailing
    period baked into the quoted span), regardless of whether that string
    is itself the correct term boundary. Whether the string SHOULD be
    `"rule"` instead is a completely different, unrelated defect, pinned
    on its own in `test_tx_rule_entry_term_boundary_excludes_trailing_
    period` below -- kept deliberately separate per the same "don't fold
    two defects into one test" instruction this ruling gave for that
    other test, applied here for consistency to every term in this file."""
    counts = _term_counts()
    assert counts["rule."] == 1, (
        f'"rule." was captured {counts["rule."]} times through the full, real dispatching '
        f"path -- expected exactly 1 (using today's actual captured spelling; see the "
        f"companion term-boundary test for whether that spelling itself is correct). "
        f"Residual ledger R1 (owned by markers): baseline's own degenerate per-block "
        f'candidate (definition_text="") coexists with F5\'s correct combined 4-term '
        f"candidate. All term counts: {dict(counts)!r}"
    )


# --- Separate defect: term-boundary (trailing period), NOT dedup ----------


def test_tx_rule_entry_term_boundary_excludes_trailing_period():
    """A SEPARATE defect from every dedup test above -- deliberately its
    own test, per the sprint manager's explicit instruction not to fold
    this into a dedup assertion (fixing one would mask the other).

    The real row's own text is `(D) "rule."` -- the sentence's own
    closing full stop sits inside the closing quote mark (a common legal-
    drafting/typesetting convention: the WHOLE list-sentence's final
    period, not part of the defined word itself). `_LETTERED_TERM_RE`
    (`rules/us_multiterm_shared_clause.py`) captures group 1 verbatim
    (`[^”"]+`, no `.rstrip()` at all -- contrast `_extract_leading_terms`
    in the SAME module, which already `.rstrip(" ,;")`s ITS OWN captured
    terms, just not `.`), so the captured term is `"rule."`, with the
    period, not the bare word `"rule"` a real downstream mention of "rule"
    would actually contain.

    **DEFENDED, not guessed, per the explicit instruction to say so if my
    own judgment differs:** I agree bare `"rule"` is the semantically
    correct term (the period here is the SENTENCE's own terminator
    adjacent to the closing quote, not part of the word, unlike a genuine
    abbreviation such as "Corp." where the period IS part of the term) --
    matching how `_extract_leading_terms` already strips comma/semicolon
    for the SAME reason on MT's `"owns,"`.

    **CONFLICT this test's own fix will create, flagged prominently, not
    silently absorbed:** THREE tests elsewhere in this sprint's OWN
    already-committed suite currently REQUIRE `"rule."` (WITH the
    trailing period) to be the correctly-captured term, and are
    CURRENTLY GREEN because of it:
      - `test_definition_links_multiterm_shared_clause.py::
        test_tx_s2009_003_parent_clause_terms_get_the_real_shared_
        definition_text` (`for term in (..., "rule."): assert term in
        by_term`)
      - `test_multiterm_f5_shared_clause.py::
        test_tx_parent_clause_redirect_list_2009_003`
      - `test_multiterm_f5_shared_clause.py::
        test_tx_parent_clause_redirect_list_2002_001`
    All three were re-run live (2026-08-05) and confirmed PASSING today,
    each depending on `"rule."` (with the period) appearing in the
    extracted/persisted terms. Whatever fix satisfies THIS test (making
    the captured term bare `"rule"`) will, by construction, make `"rule."`
    stop appearing -- which will break all three of those tests unless
    they are updated in the SAME change. This is a cross-test
    coordination question for the sprint manager to schedule, not
    something resolved unilaterally here (I do not own those three tests
    under this task's authorization, and rewriting an already-verified-
    passing test without being asked is its own kind of overreach)."""
    counts = _term_counts()
    assert "rule" in counts, (
        f'expected the bare term "rule" (no trailing period) to be captured -- the period '
        f"in the real row's own `(D) \"rule.\"` is the enclosing sentence's own terminal "
        f"punctuation, not part of the defined word. Got term counts: {dict(counts)!r} -- "
        f'"rule" (bare) is ABSENT; only "rule." (with the period) is ever produced today.'
    )
    assert "rule." not in counts, (
        f'"rule." (with the trailing period baked into the term string) must not be the '
        f"captured term -- it will never match a real downstream mention of the word "
        f"\"rule\" in running prose. Got term counts: {dict(counts)!r}"
    )
