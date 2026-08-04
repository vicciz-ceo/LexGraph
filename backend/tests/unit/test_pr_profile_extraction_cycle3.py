r"""RED tests for the cycle-3 "ordinary workload" -- rows that yield zero
but have real markers and/or real idioms and/or a real quoted term, so
they are NOT bucket D (see `test_pr_profile_bucket_d_heading_anchored.py`)
-- sprint 2026-08-04-defs-us-pr, cycle 3, gates P1/P4.

## Why this file exists / recount

The cycle-2 manager measured "33 ordinary workload" rows. Per this
cycle's brief ("recount rather than trusting my 33" -- bucket boundaries
shift once the `se refiere a` idiom gap is fixed), the real count is
**37**: the manager's 33, MINUS 1 fully solved by the idiom-widening in
`test_pr_profile_idiom_widening_cycle3.py` (`STATE_PR_LEY_66_2011_ART3`
had real markers so it was already inside the 33, not bucket D), PLUS 5
more rows the manager's crude bucket-D categorizer mis-labelled as
"anchor-less residue" that actually contain a real quoted term and are
ordinary mechanical gaps (4 re-triaged here; the 5th,
`STATE_PR_LEY_48_2018_ART3`, turned out to be a correct-zero guard, not a
gap at all -- see below).

## Distinct diagnosed shapes (each with a real example; not the same
defect repeated)

1. **"El término 'X' <idiom>" unquoted lead-in, no marker.**
   `_extract_term_and_definition`'s no-marker single-entry dispatch
   currently tries the body starting from its own literal first
   character. When that first character is NOT a quote (e.g. the body
   opens `"El término "equipo solar" significa..."`), none of the
   QUOTED patterns are ever tried (`_extract_term_and_definition` only
   selects the quoted-pattern group when `block[:1]` is itself a quote
   character) -- and none of the UNQUOTED patterns match either (no
   colon/dash/period near the front). `STATE_PR_LEY_133_1979_ART1`.
2. **Same lead-in family, a scope-phrase variant.**
   `"A los fines de la aplicación de esta Ley, "Sistema de Clasificación
   de Películas", es aquel..."` -- same root cause (unquoted lead-in
   before the quoted term), a comma before the quoted term instead of
   directly-adjacent. `STATE_PR_LEY_141_2002_ART6`.
3. **A NEW idiom, `se considera como`, also behind an unquoted lead-in.**
   `"A los fines de esta ley se considera como "amplificador o
   altoparlante" todo artefacto..."` -- corpus survey (this cycle):
   `se considera(rá) como` is 303 rows corpus-wide / 30 canonical / 5
   among current zero-yield rows (see
   `test_pr_profile_idiom_widening_cycle3.py`'s survey table). Only this
   ONE of its 5 zero-yield rows is diagnosed and pinned here -- the other
   4 need their own individual diagnosis before a blanket idiom-set
   widening, per the SAME recall-vs-precision discipline
   `test_pr_profile_idiom_widening_cycle3.py` already demonstrated for
   `se refiere a`. `STATE_PR_LEY_155_1937_SEC1`.
4. **Unquoted term + INTERJECTED scope clause + idiom, no marker.**
   `"Mujer trabajadora, a los fines de esta Ley, significará..."` -- the
   term and its idiom are correctly unquoted-shaped, but a scope clause
   ("a los fines de esta Ley") is interjected by commas BETWEEN the term
   and its own idiom, which none of `_UNQUOTED_TERM_SEPARATOR_PATTERNS`
   expects. `STATE_PR_LEY_9_2020_ART2`.
5. **`el término "X" se referirá a` -- idiom-widening ALONE does not fix
   this row** (a correction to this cycle's own initial idiom-gap
   framing -- see module docstring's cross-reference below). Same
   unquoted-lead-in family as #1/#2, just with the `se referirá a` idiom
   instead of `significa`. `STATE_PR_LEY_26_1941_ART57`.
6. **The highest-marker-count remaining row (37 markers) -- a distinct
   "Label.-El término 'X' se interpretará que significa" shape.**
   `"(1) Persona.-El término "persona" se interpretará que significa e
   incluye..."` -- the marker's own block starts with an UNQUOTED label
   ("Persona") immediately followed by a period+HYPHEN (no space, so the
   A6 pattern's own `\.(?!-)` exclusion correctly refuses to treat this
   as an ordinary trailing-period separator -- by the SAME design that
   correctly protects the M-R7 `"(a) En General.-"` rows from
   fabrication), then a SECOND, nested "El término 'X' se interpretará
   que significa" clause repeating the same term in quotes. Pinned at
   floor granularity only (not exact term text) -- the correct extraction
   mechanism (label vs. re-quoted term) is a Developer design choice, not
   pinned here. `STATE_PR_RENTAS_SEC1010_01`.

## Correct-zero guard (NOT a gap -- found via this cycle's re-triage)

`STATE_PR_LEY_48_2018_ART3`: `"Para fines de esta Ley se adoptan las
definiciones de la Ley 38-2017, conocida como, "Ley de Procedimiento
Administrativo Uniforme del Gobierno de Puerto Rico"..."` -- a WHOLESALE
cross-law deferral, the SAME shape as the already-pinned
`STATE_PR_LEY_52_2019_ART3` correct-zero guard
(`test_pr_profile_extraction_cycle2.py`). The quote here is a LAW TITLE
via the `conocido como` idiom -- the cycle-1 survey already flagged
`conocido como`/`denominado` as "overwhelmingly a law-title-naming idiom,
NOT a term definition" and explicitly recommended against using it as a
blanket extraction trigger. Pinned here as a MUST-STAY-ZERO guard so a
future idiom widening (e.g. for `se considera como`, above) does not
accidentally start capturing law titles as if they were defined terms.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows_cycle3.json`; `STATE_PR_LEY_15_1931_SEC22` (a further
unquoted-lead-in shape example, `"se entiende por" + 2 alt-quoted-terms`)
REUSES the already-vendored cycle-2 fixture row (no need to re-vendor).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_cycle3.json"
)
CYCLE2_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_cycle2.json"
)


def _load(*paths) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for path in paths:
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows:
            merged[row["act_id"]] = row
    return merged


@pytest.fixture()
def pr_rows():
    return _load(FIXTURE_PATH, CYCLE2_FIXTURE_PATH)


# --- Shape 1/2: unquoted lead-in before a quoted term, no marker ------------


def test_el_termino_x_significa_lead_in_no_marker(pr_rows):
    """`STATE_PR_LEY_133_1979_ART1`: `"El término "equipo solar"
    significa..."` -- unquoted lead-in before the quoted term, no
    top-level marker at all."""
    row = pr_rows["STATE_PR_LEY_133_1979_ART1"]
    assert row["text"].startswith('El término “equipo solar” significa')  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1
    all_terms = {term for c in candidates for term in c.terms}
    assert "equipo solar" in all_terms
    equipo = next(c for c in candidates if c.terms == ("equipo solar",))
    assert "energía del sol en energía utilizable" in equipo.definition_text


def test_scope_phrase_lead_in_before_quoted_term_comma_idiom(pr_rows):
    """`STATE_PR_LEY_141_2002_ART6`: `"A los fines de la aplicación de
    esta Ley, "Sistema de Clasificación de Películas", es aquel..."` --
    same unquoted-lead-in family as above, comma-separated scope phrase
    before the quoted term instead of a bare "El término" lead-in."""
    row = pr_rows["STATE_PR_LEY_141_2002_ART6"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1
    all_terms = {term for c in candidates for term in c.terms}
    assert "Sistema de Clasificación de Películas" in all_terms


# --- Shape 3: NEW idiom "se considera como", also behind a lead-in ---------


def test_se_considera_como_new_idiom_behind_lead_in(pr_rows):
    """`STATE_PR_LEY_155_1937_SEC1`: `"A los fines de esta ley se
    considera como "amplificador o altoparlante" todo artefacto..."` --
    a genuinely NEW idiom (`se considera como`, 303 corpus-wide / 30
    canonical rows measured this cycle) behind the same unquoted-lead-in
    shape as shapes 1/2 above."""
    row = pr_rows["STATE_PR_LEY_155_1937_SEC1"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1
    all_terms = {term for c in candidates for term in c.terms}
    assert "amplificador o altoparlante" in all_terms


# --- Shape 4: unquoted term + interjected scope clause + idiom -------------


def test_unquoted_term_with_interjected_scope_clause_before_idiom(pr_rows):
    """`STATE_PR_LEY_9_2020_ART2`: `"Mujer trabajadora, a los fines de
    esta Ley, significará..."` -- the scope clause "a los fines de esta
    Ley" is interjected by commas between the unquoted term and its own
    idiom verb."""
    row = pr_rows["STATE_PR_LEY_9_2020_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1
    all_terms = {term for c in candidates for term in c.terms}
    assert "Mujer trabajadora" in all_terms


# --- Shape 5: correction -- idiom-widening alone does NOT fix this row ------


def test_el_termino_x_se_referira_a_still_needs_lead_in_strip(pr_rows):
    """`STATE_PR_LEY_26_1941_ART57`: `"Para los fines de esta Ley el
    término "persona jurídica" se referirá a corporaciones..."`. This row
    was INITIALLY thought to be purely an idiom-widening gap (it uses `se
    referirá a`) -- but it is actually the SAME unquoted-lead-in family as
    shapes 1/2/3 above (the block does not START with a quote character,
    so `_extract_term_and_definition` never even tries the quoted
    patterns where a widened idiom alternation would help). Widening the
    idiom set alone (`test_pr_profile_idiom_widening_cycle3.py`) does
    NOT capture this row -- it additionally needs the lead-in-strip fix
    shapes 1-4 above need. Pinned here, in the lead-in-strip family file,
    not the idiom file, to correct that initial framing on the record."""
    row = pr_rows["STATE_PR_LEY_26_1941_ART57"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1
    all_terms = {term for c in candidates for term in c.terms}
    assert "persona jurídica" in all_terms


# --- Shape 6: highest-marker-count remaining row (floor granularity only) --


def test_label_dot_dash_el_termino_x_se_interpretara_que_significa(pr_rows):
    r"""`STATE_PR_RENTAS_SEC1010_01`: 37 real markers, `"(1) Persona.-El
    término "persona" se interpretará que significa e incluye un
    individuo..."` -- the marker's own block starts with an unquoted
    label immediately followed by `.-` (no space), which the existing A6
    pattern's `\.(?!-)` exclusion correctly refuses (by the same design
    that protects the M-R7 rows from fabrication), then a nested
    re-quoted-term idiom clause. Pinned at FLOOR granularity only (>=1
    candidate) -- the exact extraction mechanism (label vs. re-quoted
    term) is a Developer design choice, not pinned here, matching this
    sprint's corpus-floor-test discipline for under-specified complex
    rows."""
    row = pr_rows["STATE_PR_RENTAS_SEC1010_01"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1, f"{row['act_id']}: expected >=1 candidate, got 0"


# --- Correct-zero guard: cross-law/title deferral via "conocido como" ------


def test_conocida_como_law_title_deferral_correctly_yields_zero_candidates(pr_rows):
    """`STATE_PR_LEY_48_2018_ART3`: `"...se adoptan las definiciones de la
    Ley 38-2017, conocida como, "Ley de Procedimiento Administrativo
    Uniforme..."` -- a WHOLESALE cross-law deferral, the SAME shape as
    the already-pinned `STATE_PR_LEY_52_2019_ART3` correct-zero guard.
    The quote is a LAW TITLE via `conocido como` (already flagged by the
    cycle-1 survey as overwhelmingly a law-naming idiom, not a
    term-defining one), not a defined term -- must continue to yield
    zero, guarding against a future `conocido como`/`se considera como`
    widening fabricating a "term" out of a law's own title."""
    row = pr_rows["STATE_PR_LEY_48_2018_ART3"]
    assert "conocida como" in row["text"]  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert candidates == [], f"expected 0 candidates (law-title deferral), got {candidates!r}"
