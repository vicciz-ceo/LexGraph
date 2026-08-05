"""RED tests for sprint 2026-08-04-defs-us-multiterm, ruling M-R23: the
M-R18 guard that landed in `rules/us_inline_parenthetical.py` (pinned by
`test_definition_links_leading_quote_guard.py` /
`test_definition_links_tx_2009_003_full_row_findings.py`) introduced a
SILENT RECALL REGRESSION -- found by a corpus kill-experiment, not by the
suite (no existing test covered the affected rows, which is exactly how
it shipped green).

**Mechanism (root cause).** `us_profile.py`'s baseline entry-start
recognition (`_MARKER_TOKEN_RE = re.compile(r"\\(\\w+\\)\\s*")`, used by
`_strip_marker_chain_before_quote` / `_entry_start_remainder`) requires a
parenthesized marker to contain ONLY `\\w` characters -- `\\w` excludes the
hyphen. A SUFFIXED marker such as `(9-a)` or `(5-a)` (Texas's real
drafting convention for inserting a new definition between two existing
numbered entries without renumbering the whole list) therefore does not
match `_MARKER_TOKEN_RE` at all, `_BARE_DIGIT_MARKER_RE` doesn't match it
either (it isn't a bare digit), so `_entry_start_remainder` returns `None`
for that line and `_split_into_numbered_blocks` never opens a new block
for it -- the whole suffixed-marker entry (marker, quoted term, and
cross-reference idiom) is silently swallowed into whatever PRECEDING
block is still open. Baseline produces ZERO candidate for that entry.

The ONLY thing that can still capture the term is F6's cross-reference
scan (`_cross_reference_candidates` in `rules/us_inline_parenthetical.py`,
wired in via the `TermClauseRule` registered for `jurisdiction_codes=
("US-*",)`), which scans the WHOLE swallowed block's text unconditionally
for `"Term" has the meaning assigned by ...` / `has the meaning given
that term in ...` / `as defined in ...`.  But `_parse_block`'s M-R18
guard (`_leading_quote_terms`, built from `_ENTRY_LEADING_QUOTE_RE =
re.compile(r'(?:\\A|\\n)\\s*\\([^\\s()]{1,10}\\)\\s*[“"]([^”"]+)[”"]')`)
uses `[^\\s()]{1,10}` inside the parens -- UNLIKE baseline's `\\w`-only
`_MARKER_TOKEN_RE`, this DOES match a hyphen. So `_ENTRY_LEADING_QUOTE_RE`
finds `(9-a) "Supplier"` / `(5-a) "Low-income community"` mid-block and
adds `"Supplier"` / `"Low-income community"` to `leading_terms`, on the
(here false) assumption that baseline already captured this term from ITS
OWN, separately-split block elsewhere (true for every marker shape the
guard was validated against, M-R16 -- but baseline never split THIS
marker shape into its own block at all, per the mechanism above). F6's
own cross-reference candidate for that exact term is then discarded as an
assumed-duplicate in `_parse_block`:

    for candidate in _cross_reference_candidates(block, scope="law-wide"):
        if candidate.terms and candidate.terms[0] in leading_terms:
            continue  # <-- wrongly discards Supplier / Low-income community
        candidates.append(candidate)

Net effect: baseline yields nothing (marker unrecognized) AND the guard
suppresses the one rule that would have caught it anyway -- the term is
lost ENTIRELY, not merely miscounted. This is a full recall regression
(1 -> 0), corpus-measured via a kill-experiment (sprint log, ruling
M-R23):

    tx STATE_TX_Coc_C2310_S2310.001  term='Supplier'             1->0
    tx STATE_TX_Cin_C228_S228.001    term='Low-income community' 1->0

**Scope note (reported to the sprint manager, not silently expanded
here):** an exhaustive scan of the full real `us_tx_statutes.parquet`
file for this exact shape (a non-`\\w` marker immediately followed by a
quoted term immediately followed by a cross-reference idiom) found **111
occurrences across 91 distinct real TX sections**, not merely these 2 --
this hyphen-suffixed-marker drafting convention is pervasive in Texas.
The same scan against 8 other already-fixtured state files (DE, NY, CA,
IL, FL, OH, PA, GA, AR) found ZERO occurrences in every one of them, so
this appears to be a Texas-specific (not corpus-wide) drafting
convention. Per the sprint manager's own instruction this is reported,
not acted on -- this file pins only the 2 named rows; broadening the
fixture/test population beyond that is explicitly out of this task's
scope.

**Fixture provenance.** 2 REAL rows, vendored byte-exact (all 24 original
parquet columns, values unmodified, no trimming), from the local HF
snapshot at `~/.cache/huggingface/hub/datasets--vaquill--open-us-law`
(`us_tx_statutes.parquet`, snapshot `301000fc3465374ee0f23c3c6953a8a861e95cad`
-- same dataset/commit as every other fixture in this directory), written
straight to JSON by a script reading the parquet directly (no manual
retyping, byte-exactness holds by construction), then independently
re-verified by a SEPARATE second parquet read/script diffed field-by-field
against the committed JSON: zero mismatched fields across all 24 columns
for both rows, `real_row == fixture_row` `True` for both -- see
`backend/tests/fixtures/us_statutes/README.md` for the full provenance
note and this file's own entry.

**Both rows have genuine `DEFINITIONS` section titles** (verified live,
not taken on the ruling's word):
`is_definitions_heading("§ 2310.001. DEFINITIONS.")` and
`is_definitions_heading("§ 228.001. GENERAL DEFINITIONS.")` both
return `True` (`app.definition_links.us_profile.is_definitions_heading`).

**Live-path discipline.** Both tests drive the REAL, current
`USProfile.extract_definitions_from_section` -- the dispatching profile
METHOD, reached via `get_profile("US-TX")`, scope obtained from the real
`determine_scope` -- never a bare helper, never a private import of
`_cross_reference_candidates`/`_parse_block` directly. This is the exact
same production path `pipeline.py` uses once a section's heading is
recognized as a genuine Definitions heading (both rows' headings are, per
the check above), so what these tests observe is what a real ingest run
over these two real TX sections would produce today.

**Assertion altitude.** A bare "the term string appears somewhere in the
flattened candidate population" check is exactly what let this regression
ship green in the first place (no existing test covered these rows at
all, so a shallow presence check on some OTHER row would not have caught
it either) -- so each test here asserts (a) the term is captured EXACTLY
ONCE (not zero, not duplicated) as its OWN single-term
`DefinitionCandidate`, AND (b) that candidate's `definition_text` is the
REAL cross-reference sentence's citation content, not empty or junk --
pinned by `.startswith(...)` on the citation text
(`"Section 162.001, Tax Code."` / `"Section 45D(e), Internal Revenue Code
of 1986."`) rather than a full exact-string match. `startswith` (not
`==`) is a deliberate choice, not a weaker check taken for convenience:
`_cross_reference_candidates`' own entry-bounding (unchanged by whatever
fix lands for this guard, per the sprint's own disjoint-write-set
framing) has a separate, already-known characteristic where a candidate's
`definition_text` window can run on into trailing unrelated text when
there is no NEXT recognized entry boundary to stop at (measured directly
against these exact two real rows, this Planner cycle: `"Supplier"`'s raw
`_cross_reference_candidates` output today already bleeds into the
following `(9-b) "Wholesaler" means ...` entry's own text, since `(9-b)`
is a fellow non-`\\w` marker baseline ALSO can't use as a boundary --
a pre-existing, separately-owned imprecision, not this guard's own
recall-loss mechanism). Pinning the exact full string here would
conflate that separate, already-accepted bounding imprecision with the
recall-loss defect this test exists to catch, and could go spuriously RED
even after a correct guard fix if the fix's exact bounding behavior
differs in that unrelated tail. `startswith` on the real citation content
is deliberately still strict enough to reject a "just stop suppressing it
with an empty/junk definition_text" degenerate fix.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.definition_links.profiles import get_profile
from app.definition_links.us_profile import is_definitions_heading

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "m_r23_hyphen_marker_recall_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


def _extract(row: dict) -> list:
    profile = get_profile("US-TX")
    scope = profile.determine_scope(row["text"])
    return profile.extract_definitions_from_section(row["text"], scope=scope)


def test_tx_2310_001_supplier_is_a_genuine_definitions_section():
    """Precondition check, not the regression itself: confirms
    `STATE_TX_Coc_C2310_S2310.001`'s real `section_title`
    (`"§ 2310.001. DEFINITIONS."`) is genuinely heading-recognized, so
    `extract_definitions_from_section` below is the real production path
    for this row, not an artificial detour."""
    row = _load_rows()["STATE_TX_Coc_C2310_S2310.001"]
    assert is_definitions_heading(row["section_title"]) is True, (
        f'expected {row["section_title"]!r} to be heading-recognized as a genuine '
        f"Definitions section (it is real TX statutory text, ALL-CAPS convention) -- if "
        f"this is False, the test below would not be exercising the real production path "
        f"the ruling claims it is."
    )


def test_tx_2310_001_supplier_cross_reference_is_captured_exactly_once():
    """Ruling M-R23. Real row `STATE_TX_Coc_C2310_S2310.001`, entry
    `(9-a) "Supplier" has the meaning assigned by Section 162.001, Tax
    Code.` -- a hyphen-suffixed marker baseline's `_MARKER_TOKEN_RE`
    (`\\w`-only) cannot recognize as an entry start, so baseline yields
    NOTHING for this entry; F6's cross-reference scan is the only
    candidate this term could ever get, and today the M-R18 guard
    wrongly discards it (see module docstring for the full mechanism).
    RED today (0 candidates, not 1); goes GREEN when the Developer's
    guard fix lands."""
    row = _load_rows()["STATE_TX_Coc_C2310_S2310.001"]
    candidates = _extract(row)
    term_counts = Counter(t for c in candidates for t in c.terms)
    assert term_counts["Supplier"] == 1, (
        f'"Supplier" was captured {term_counts["Supplier"]} times through the real '
        f'dispatching path (`get_profile("US-TX").extract_definitions_from_section`) -- '
        f"expected exactly 1. Ruling M-R23: baseline's \\w-only `_MARKER_TOKEN_RE` cannot "
        f'recognize the real row\'s hyphen-suffixed `(9-a)` marker as an entry start, so '
        f"baseline produces zero candidates for this entry; the M-R18 guard's own "
        f'`_ENTRY_LEADING_QUOTE_RE` (which, unlike baseline, DOES match a hyphen inside '
        f"the parens) then wrongly treats \"Supplier\" as already-captured-elsewhere and "
        f"discards F6's cross-reference candidate for it -- the only candidate this term "
        f"could ever get. All captured terms: {sorted(t for c in candidates for t in c.terms)!r}"
    )
    supplier_candidates = [c for c in candidates if c.terms == ("Supplier",)]
    assert len(supplier_candidates) == 1, (
        f'expected exactly one single-term ("Supplier",) candidate, found '
        f"{len(supplier_candidates)}: {supplier_candidates!r}"
    )
    definition_text = supplier_candidates[0].definition_text
    assert definition_text.startswith("Section 162.001, Tax Code."), (
        f'expected "Supplier"\'s captured definition_text to be the REAL cross-reference '
        f'citation from the row (`"Section 162.001, Tax Code."` at minimum) -- not empty, '
        f"not junk, not some other entry's text -- proving the regression fix restores the "
        f"correct DEFINITION, not merely a bare term-presence check (which is exactly what "
        f"let this regression ship green in the first place, since no test covered these "
        f"rows at all). Got: {definition_text!r}"
    )


def test_tx_228_001_low_income_community_is_a_genuine_definitions_section():
    """Precondition check, not the regression itself: confirms
    `STATE_TX_Cin_C228_S228.001`'s real `section_title`
    (`"§ 228.001. GENERAL DEFINITIONS."`) is genuinely
    heading-recognized, so `extract_definitions_from_section` below is the
    real production path for this row, not an artificial detour."""
    row = _load_rows()["STATE_TX_Cin_C228_S228.001"]
    assert is_definitions_heading(row["section_title"]) is True, (
        f'expected {row["section_title"]!r} to be heading-recognized as a genuine '
        f"Definitions section (it is real TX statutory text, ALL-CAPS convention) -- if "
        f"this is False, the test below would not be exercising the real production path "
        f"the ruling claims it is."
    )


def test_tx_228_001_low_income_community_cross_reference_is_captured_exactly_once():
    """Ruling M-R23. Real row `STATE_TX_Cin_C228_S228.001`, entry
    `(5-a) "Low-income community" has the meaning assigned by Section
    45D(e), Internal Revenue Code of 1986.` -- the second real corpus row
    the kill-experiment found this exact recall-loss mechanism on
    (identical root cause to `Supplier` above, a different real section,
    proving this is a genuine class, not a one-row fluke). RED today (0
    candidates, not 1); goes GREEN when the Developer's guard fix lands."""
    row = _load_rows()["STATE_TX_Cin_C228_S228.001"]
    candidates = _extract(row)
    term_counts = Counter(t for c in candidates for t in c.terms)
    assert term_counts["Low-income community"] == 1, (
        f'"Low-income community" was captured {term_counts["Low-income community"]} times '
        f'through the real dispatching path (`get_profile("US-TX").extract_definitions_'
        f"from_section`) -- expected exactly 1. Ruling M-R23 (same mechanism as "
        f'"Supplier", see module docstring and the sibling 2310.001 test): baseline\'s '
        f"\\w-only `_MARKER_TOKEN_RE` cannot recognize the real row's hyphen-suffixed "
        f"`(5-a)` marker as an entry start, so baseline produces zero candidates for this "
        f"entry; the M-R18 guard's own `_ENTRY_LEADING_QUOTE_RE` then wrongly treats "
        f'"Low-income community" as already-captured-elsewhere and discards F6\'s '
        f"cross-reference candidate for it -- the only candidate this term could ever get. "
        f"All captured terms: {sorted(t for c in candidates for t in c.terms)!r}"
    )
    lic_candidates = [c for c in candidates if c.terms == ("Low-income community",)]
    assert len(lic_candidates) == 1, (
        f'expected exactly one single-term ("Low-income community",) candidate, found '
        f"{len(lic_candidates)}: {lic_candidates!r}"
    )
    definition_text = lic_candidates[0].definition_text
    assert definition_text.startswith("Section 45D(e), Internal Revenue Code of 1986."), (
        f'expected "Low-income community"\'s captured definition_text to be the REAL '
        f'cross-reference citation from the row (`"Section 45D(e), Internal Revenue Code '
        f'of 1986."` at minimum) -- not empty, not junk, not some other entry\'s text -- '
        f"proving the regression fix restores the correct DEFINITION, not merely a bare "
        f"term-presence check. Got: {definition_text!r}"
    )
