"""RED tests for the Puerto Rico (Spanish) jurisdiction profile's entry
extractor -- CYCLE 2 (sprint 2026-08-04-defs-us-pr), gates P1/P4.

## Why this file exists

Cycle 1's `test_pr_profile_extraction.py` pinned 5 real fixture rows and all
5 passed. The manager then ran the SAME extractor over the full 23,636-row
corpus (the check a fixture suite structurally cannot make) and found
extraction succeeds on only 346/614 (56.4%) of the canonical Definiciones
rows the cycle-1 panel never looked at -- 268 rows yield ZERO candidates.
The manager categorized the 268 misses into buckets A (153, unambiguous
extractor bug), B (7, settled -- safe to capture), C (22, re-diagnosed
below), D (86, ESCALATED to the director, OUT OF SCOPE for this file -- see
`## Bucket D is explicitly out of scope` below). Full detail:
`docs/sprint/sprints/2026-08-04-defs-us-pr-log.md`, the manager's
"Developer verification + GENERALIZATION GAP" entry and ruling M-R6.

## Root-cause diagnosis (Planner, cycle 2 -- re-run live against
`pr_profile.py` for every row in this file; see the cycle-2 panel log entry
for the full diagnostic transcripts)

`extract_definitions_from_section`'s per-entry helper,
`_extract_term_and_definition`, tries exactly THREE separator patterns in
order: quoted-term+colon, quoted-term+typographic-em/en-dash, unquoted-
term+typographic-em/en-dash. Every bucket-A/B/C row in this file fails
because its real separator shape is NOT one of those three. Live-diagnosed
shapes (each a real, corpus-verified, DISTINCT reason `_extract_term_and_
definition` returns `None` today):

  - **A1 -- quoted term (curly OR straight) directly followed by whitespace
    then a defining-verb idiom (`significa`/`significará`/`es`), with NO
    separator character at all**: `"Cuenta" significa cualquiera de las
    cuentas...` (`STATE_PR_LEY_77_1957_ART39_050`, curly) / `"Body Piercer"
    significa la persona...` (`STATE_PR_LEY_73_2003_ART2`, straight). This
    is the single largest shape (124 curly + 9 straight = 133/153 of bucket
    A) -- confirming the quote CHARACTER was never the bug; the missing
    separator pattern is.
  - **A1-variant -- quoted term + comma + idiom** (a punctuation mark
    appears, but it's a comma, not the colon/dash the code recognizes):
    `"Análisis Clínico", significará...` (`STATE_PR_LEY_167_1988_ART2`),
    `"Barbero" o "Estilista en Barbería", significará...`
    (`STATE_PR_LEY_60_1988_ART1`).
  - **A2 -- quoted term + ASCII hyphen-minus `-` (NOT a typographic en/em
    dash) + idiom**: `"Activo" - significa cualquier cosa...`
    (`STATE_PR_LEY_189_1996_ART2`). `_QUOTED_TERM_DASH_RE` only accepts
    `[–—]`; a plain keyboard hyphen never matches it.
  - **A3 -- quoted term, NO separator, NO idiom verb at all -- the
    definition is a bare capitalized noun phrase**: `"Activos líquidos"
    Aquellos activos que se pueden transformar...`
    (`STATE_PR_LEY_214_1995_ART2`).
  - **A4 -- unquoted term + colon** (there is no `_UNQUOTED_TERM_COLON_RE`
    at all -- only `_UNQUOTED_TERM_DASH_RE` exists for unquoted terms):
    `Certificación: documento oficial que expide...`
    (`STATE_PR_LEY_33_2017_ART3`), `dependencias gubernamentales: se
    refiere a...` (`STATE_PR_LEY_46_2008_ART3`, bucket B), `Diabetes tipo 1:
    es un desorden autoinmune...` (`STATE_PR_LEY_199_2015_ART2`, bucket B).
  - **A6 -- unquoted term + its OWN trailing period (not colon, not dash) +
    bare definition**: `Agencia. Cualquier departamento, negociado...`
    (`STATE_PR_LEY_66_1975_ART3`), `Acuerdo Cooperativo. Un acuerdo de
    cooperación...` (`STATE_PR_LEY_51_2003_ART2`, bucket B).

### Bucket C re-diagnosis (correction to M-R6's "marker-inventory gap"
characterization -- see cycle-2 log for the full transcript)

Live-diagnosing both of M-R6's named C examples shows `_ENTRY_MARKER_RE`
**already matches both shapes** -- this is NOT a marker-regex gap:

  - `STATE_PR_LEY_430_2000_ART3`'s `A.`/`B.`/`C.`... markers: the period-
    marker alternative's character class is `[a-zA-Z]`, which is
    case-insensitive by construction -- 26/26 real markers in this row are
    found correctly. The row's zero-yield is plain bucket A1 (quoted term +
    `significa`, no separator) -- same root cause, not a new one.
  - `STATE_PR_LEY_190_1995_ART2`'s `a. —`/`b. —`... markers: also found
    correctly (12/12). What's unhandled is the BLOCK content after the
    marker: a decorative em-dash sits between the marker and the quoted
    term (`a. — "Nueva programación" significa...`), and no term/separator
    pattern expects a block to start with a bare dash before the term. This
    genuinely IS a new, distinct shape -- **A5: marker followed by a
    decorative dash, then the term** -- not a marker-recognition gap.

Neither of M-R6's two named bucket-C examples needs a new MARKER shape --
the fix surface for both is entirely in `_extract_term_and_definition`'s
separator-pattern set (A1) plus one new block-prefix case (A5). But the
re-survey mandate ("so cycle 2 doesn't leave a third gap behind") DID turn
up one genuine, new, previously-uncatalogued marker-inventory gap while
diagnosing a bucket-B row (not bucket C): traditional Spanish alphabetical
enumeration treats **"ch" as its own letter**, producing a real TWO-
CHARACTER letter marker `ch)` (`STATE_PR_LEY_46_2008_ART3`:
`"...c) expresiones... ch) normas de seguridad..."`). `_ENTRY_MARKER_RE`'s
letter alternatives are all single-character (`[a-zA-Z]`), so `ch)` matches
none of them -- confirmed live, this row's marker scan finds only 6
markers (`a) b) c) d) e) f)`), silently skipping `ch)` entirely and letting
entry `c)` swallow its content.
`test_two_letter_ch_marker_is_not_recognized_as_an_entry_boundary` below
pins this distinctly from the A4 (unquoted+colon) fix the rest of that row
needs.

### An incidental, real, previously-undiscovered defect (found via bucket B)

`STATE_PR_LEY_51_2003_ART2`'s body contains `"...que utilizan los servicios
del U. S. Geological Survey..."` (a spaced abbreviation) THREE times inside
entry bodies. `_ENTRY_MARKER_RE`'s period-marker alternative
(`(?:[a-zA-Z]|\\d{1,3})\\.(?=\\s)`, preceded by `[.;:\\]]\\s+`) has no
abbreviation exclusion, so `U. S.`'s own `S.` token gets misfired as a
spurious entry marker (preceded by `U. ` which ends `.`+space), corrupting
entry 1's `definition_text` mid-sentence. `test_captures_all_four_entries_
despite_spaced_abbreviation_marker_misfire` below pins the correct,
unfragmented extraction -- proving this defect independently of the A6
separator-pattern gap the same row also has.

## A no-marker dispatch gap (found via bucket B)

`STATE_PR_LEY_77_1957_ART9_040` (`"Agente General, definición"`) is a
single-entry, no-marker Civil-Code-style article: `"Agente General es la
persona nombrada por un asegurador..."`. Its body ALSO contains an
enumerated `(1)`..`(11)` list of the agent's OWN duties -- sub-clauses of
the ONE definition, not separate defined terms. Today's dispatch
(`if not markers: <single-entry path> else: <markers path>`) is all-or-
nothing: because `(1)`..`(11)` exist SOMEWHERE in the text, the whole body
takes the markers path, which silently discards everything before the
FIRST marker (`marker.end()` is the block start for entry 0; there is no
"entry -1" for text before the first marker) -- the term "Agente General"
and its lead-in definition are dropped entirely, and 11 bogus fragment
"entries" (one per duty clause) are produced instead.
`test_single_no_marker_entry_survives_a_trailing_incidental_sub_list` below
pins the correct behavior: ONE candidate, term `"Agente General"`.

## Bucket D is explicitly out of scope

Bucket D (86 rows -- copulative/prose definitions with no marker and no
canonical idiom, e.g. `"Son bienes las cosas o derechos que pueden ser
apropiables..."`) is ESCALATED to the director (M-R6, program ruling P-R2 /
standing question Q-1). No test in this file targets a bucket-D row, and no
fix implied by these tests should be widened to capture bucket-D-shaped
prose -- if it incidentally does, that is a precision regression to report,
not a feature.

## A correct-zero guard

`STATE_PR_LEY_52_2019_ART3` (`"Artículo 3. Definiciones"`) is a REAL bucket-
A-workload row whose body defers WHOLESALE to another law's definitions
(`"...se entenderán de aplicación las definiciones de la Ley Núm. 228 de 12
de mayo de 1942..."`) and defines ZERO local terms itself.
`test_wholesale_cross_law_deferral_correctly_yields_zero_candidates` pins
that this MUST continue to yield zero candidates -- it is a correct
rejection, not a miss, and must not be force-fixed into fabricating local
terms that do not exist in the text.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows_cycle2.json` -- see that file's sibling `README.md`'s
`## pr_sample_rows_cycle2.json` section for full provenance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_cycle2.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- A1: quoted term (curly/straight), no separator, idiom verb -------------


def test_a1_curly_quoted_term_idiom_no_separator(pr_rows):
    """`STATE_PR_LEY_77_1957_ART39_050`: 14 top-level entries, `(1)`..`(14)`
    markers, curly-quoted terms directly followed by `significa`/
    `significará` with NO separator character at all. (Entry (7) also
    contains its OWN nested `(a)`..`(g)` sub-clause list -- this test does
    not pin an exact candidate count because how nested sub-markers are
    handled is not this test's concern; it only pins that every TOP-LEVEL
    term is still recoverable.)"""
    row = pr_rows["STATE_PR_LEY_77_1957_ART39_050"]
    candidates = extract_definitions_from_section(row["text"], scope="chapter")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Cuenta",
        "Asociación",
        "Obligación contractual",
        "Póliza cubierta",
        "Residente",
        "Contrato suplementario",
    }
    assert expected_terms <= all_terms
    assert all(c.scope == "chapter" for c in candidates)
    cuenta = next(c for c in candidates if c.terms == ("Cuenta",))
    assert "cuentas creadas por el Artículo 39.060" in cuenta.definition_text


def test_a1_straight_quoted_term_idiom_no_separator(pr_rows):
    """`STATE_PR_LEY_73_2003_ART2`: 10 entries, `(a)`..`(j)` markers,
    STRAIGHT-quoted terms + `significa`, no separator -- proves the fix is
    not curly-quote-specific."""
    row = pr_rows["STATE_PR_LEY_73_2003_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Body Piercer",
        "Body Piercing",
        "Departamento",
        "Secretario",
        "Técnicas de asepsia",
    }
    assert expected_terms <= all_terms
    assert len(candidates) == 10


def test_a1_tiny_row_all_three_entries_captured(pr_rows):
    """`STATE_PR_LEY_39_1988_ART2`: tiny (3-entry) row, same A1 shape --
    minimal reproduction."""
    row = pr_rows["STATE_PR_LEY_39_1988_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert all_terms == {"Sistema de Retiro", "Plan", "Pensionado"}
    assert len(candidates) == 3


def test_a1_confirmatory_row_493_1952(pr_rows):
    row = pr_rows["STATE_PR_LEY_493_1952_ART1"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert "Quiropráctica" in all_terms
    assert len(candidates) >= 1


def test_a1_confirmatory_row_318_1999(pr_rows):
    row = pr_rows["STATE_PR_LEY_318_1999_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Artista Dermatógrafo",
        "Departamento",
        "Dermatografía",
    }
    assert expected_terms <= all_terms


# --- A1-variant: quoted term + comma + idiom ---------------------------------


def test_a1_variant_quoted_term_comma_idiom(pr_rows):
    """`STATE_PR_LEY_167_1988_ART2`: `"Análisis Clínico", significará...` --
    a comma (not colon/dash) sits between the quoted term and the idiom."""
    row = pr_rows["STATE_PR_LEY_167_1988_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert "Análisis Clínico" in all_terms
    assert "Tecnología Médica" in all_terms


def test_a1_variant_quoted_term_comma_idiom_with_alt_term(pr_rows):
    """`STATE_PR_LEY_60_1988_ART1`: `"Barbero" o "Estilista en Barbería",
    significará...` -- same comma-before-idiom shape, first entry names an
    alternate term via "o" (not itself required to be split into two
    candidates -- only that entry (a)'s block is not silently dropped)."""
    row = pr_rows["STATE_PR_LEY_60_1988_ART1"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) >= 1
    all_terms = {term for c in candidates for term in c.terms}
    assert any("Barbero" in t or "Estilista" in t for t in all_terms)


# --- A2: quoted term + ASCII hyphen (not typographic dash) + idiom ----------


def test_a2_quoted_term_ascii_hyphen_idiom(pr_rows):
    """`STATE_PR_LEY_189_1996_ART2`: 18 entries, `(a)`..`(r)` markers,
    `"Término" - significará...` -- an ASCII keyboard hyphen `-`, not a
    typographic em/en dash, separates the quoted term from the idiom."""
    row = pr_rows["STATE_PR_LEY_189_1996_ART2"]
    assert row["text"].startswith("Los siguientes términos")  # sanity
    assert " - significa" in row["text"] or "” - significar" in row["text"]  # sanity: ASCII hyphen
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {"Activo", "Autoridad", "Azúcar", "Banco", "Corporación", "Secretario"}
    assert expected_terms <= all_terms
    assert len(candidates) == 18


# --- A3: quoted term, no separator, no idiom verb (bare definition) --------


def test_a3_quoted_term_no_separator_no_idiom_bare_definition(pr_rows):
    """`STATE_PR_LEY_214_1995_ART2`: 15 entries, `a)`..`o)` markers,
    `"Activos líquidos" Aquellos activos que...` -- NO separator character
    and NO defining-verb idiom at all; the definition is a bare capitalized
    noun phrase directly after the quoted term."""
    row = pr_rows["STATE_PR_LEY_214_1995_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Activos líquidos",
        "Agente",
        "Comisionado",
        "Documentos",
        "Persona",
        "Préstamos",
    }
    assert expected_terms <= all_terms
    assert len(candidates) == 15
    activos = next(c for c in candidates if c.terms == ("Activos líquidos",))
    assert "vencimiento menor de tres" in activos.definition_text


# --- A4: unquoted term + colon ----------------------------------------------


def test_a4_unquoted_term_colon(pr_rows):
    """`STATE_PR_LEY_33_2017_ART3`: 3 entries, `(1)`..`(3)` markers,
    `Certificación: documento oficial que expide...` -- unquoted term +
    colon; there is no `_UNQUOTED_TERM_COLON_RE` in `pr_profile.py` today,
    only a dash variant."""
    row = pr_rows["STATE_PR_LEY_33_2017_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert all_terms == {"Certificación", "Departamento", "Iglesias-escuela"}
    assert len(candidates) == 3
    cert = next(c for c in candidates if c.terms == ("Certificación",))
    assert "documento oficial que expide el Departamento" in cert.definition_text


def test_a4_settled_bucket_b_row_46_2008(pr_rows):
    """`STATE_PR_LEY_46_2008_ART3` (bucket B, settled): `a)`..`f)` markers,
    `dependencias gubernamentales: se refiere a...` -- confirms the A4
    (unquoted+colon) fix generalizes to a bucket-B row. Does NOT assert an
    exact candidate count or require "normas de seguridad" (entry `ch)`) --
    see `test_two_letter_ch_marker_is_not_recognized_as_an_entry_boundary`
    below for that distinct, separately-diagnosed gap."""
    row = pr_rows["STATE_PR_LEY_46_2008_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "dependencias gubernamentales",
        "empleados",
        "expresiones constitucionalmente protegidas",
        "propiedad pública",
        "reglamentos",
        "visitantes",
    }
    assert expected_terms <= all_terms


def test_two_letter_ch_marker_is_not_recognized_as_an_entry_boundary(pr_rows):
    """A THIRD, newly-found marker-inventory gap (re-survey deliverable,
    distinct from A1-A6 above and from the bucket-C re-diagnosis): real PR
    legal drafting (`STATE_PR_LEY_46_2008_ART3`) uses the traditional
    Spanish alphabetical enumeration where "ch" is its own letter, giving a
    TWO-CHARACTER letter marker `ch)` (`"...c) expresiones
    constitucionalmente protegidas: ... ch) normas de seguridad: se
    refiere a..."`). `_ENTRY_MARKER_RE`'s letter alternatives all use the
    SINGLE-character class `[a-zA-Z]` -- `ch)` matches NONE of the 3
    marker alternatives today (confirmed live: this row's marker scan
    finds only `a) b) c) d) e) f)`, six markers, never `ch)`), so entry
    `c)`'s block silently swallows `ch)`'s entire span (up to the next
    real marker `d)`), and "normas de seguridad" never becomes its own
    term. This is a genuine marker-shape gap, not a separator gap -- listed
    here separately so it is not confused with the A4 fix that
    `test_a4_settled_bucket_b_row_46_2008` above already proves."""
    row = pr_rows["STATE_PR_LEY_46_2008_ART3"]
    assert "ch) normas de seguridad" in row["text"]  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert "normas de seguridad" in all_terms
    assert "expresiones constitucionalmente protegidas" in all_terms  # entry c) not swallowed either


def test_a4_settled_bucket_b_row_199_2015_no_canonical_idiom(pr_rows):
    """`STATE_PR_LEY_199_2015_ART2` (bucket B, settled): `(a) Diabetes tipo
    1: es un desorden autoinmune...` -- unquoted+colon, entries use lower-
    case `es`/`son` rather than a survey-measured canonical idiom. The
    marker list itself establishes definitional context (M-R6: "safe to
    capture")."""
    row = pr_rows["STATE_PR_LEY_199_2015_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Diabetes tipo 1",
        "Diabetes tipo 2",
        "Hipoglucemia",
        "Hiperglucemia",
        "Institución escolar",
        "Estudiante",
    }
    assert expected_terms <= all_terms
    assert len(candidates) == 12


# --- A5: marker + decorative dash before the term (bucket C re-diagnosis) --


def test_a5_marker_followed_by_decorative_dash_then_term(pr_rows):
    """`STATE_PR_LEY_190_1995_ART2`: 11 entries, `a.`..`k.` markers are
    matched correctly TODAY (confirmed live) -- what fails is the block
    content: `a. — "Nueva programación" significa...` has a decorative
    em-dash between the marker and the quoted term. This is a genuinely NEW
    shape (not a marker-regex gap -- see module docstring's bucket-C
    re-diagnosis)."""
    row = pr_rows["STATE_PR_LEY_190_1995_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Nueva programación",
        "Ultimo año",
        "Artista o literario puertorriqueño",
        "Artista",
        "Músico",
        "Persona",
        "Literario",
    }
    assert expected_terms <= all_terms
    nueva = next(c for c in candidates if c.terms == ("Nueva programación",))
    assert "tiempo adicional que transmita el canal" in nueva.definition_text


# --- A6: unquoted term + own trailing period + bare definition -------------


def test_a6_unquoted_term_trailing_period_bare_definition(pr_rows):
    """`STATE_PR_LEY_66_1975_ART3`: `(a) Agencia. Cualquier departamento,
    negociado...` -- unquoted term ends its OWN sentence with a period,
    then the definition starts as a bare noun phrase. Not colon, not dash."""
    row = pr_rows["STATE_PR_LEY_66_1975_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert "Agencia" in all_terms
    agencia = next(c for c in candidates if c.terms == ("Agencia",))
    assert "Cualquier departamento, negociado" in agencia.definition_text


def test_a6_digit_period_marker_variant(pr_rows):
    """`STATE_PR_AMBIENTAL_ART51`: `1. Contaminación. Significa la
    degradación...` -- digit-period marker family + A6 separator shape
    together."""
    row = pr_rows["STATE_PR_AMBIENTAL_ART51"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert "Contaminación" in all_terms


def test_a6_captures_all_four_entries_despite_spaced_abbreviation_marker_misfire(pr_rows):
    """`STATE_PR_LEY_51_2003_ART2` (bucket B, settled): `1. Acuerdo
    Cooperativo. Un acuerdo de cooperación...`. This row has TWO stacked,
    independently real defects: (1) the A6 separator gap (unquoted term +
    own trailing period, no colon/dash), and (2) `_ENTRY_MARKER_RE`
    misfires on the spaced abbreviation `"U. S. Geological Survey"` inside
    entry 1's own body -- `S.` (single letter, preceded by `U. ` which ends
    in `.`+space) is indistinguishable from a genuine letter-period marker
    today, corrupting/fragmenting entry 1 even once the separator gap is
    fixed. This test requires BOTH to be fixed: exactly 4 clean entries,
    with entry 1's `definition_text` running unbroken through the first
    "U. S. Geological Survey" mention."""
    row = pr_rows["STATE_PR_LEY_51_2003_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    all_terms = {term for c in candidates for term in c.terms}
    assert all_terms == {
        "Acuerdo Cooperativo",
        "Fondo Especial",
        "Comité",
        "U.S. Geological Survey",
    }
    assert len(candidates) == 4
    acuerdo = next(c for c in candidates if c.terms == ("Acuerdo Cooperativo",))
    # The definition must survive past the FIRST "U. S. Geological Survey"
    # mention unbroken -- proving the abbreviation did not fragment it.
    assert (
        "que interesen compartir entre ellos" in acuerdo.definition_text
    ), f"definition_text truncated/fragmented at the U. S. abbreviation: {acuerdo.definition_text!r}"


# --- No-marker dispatch gap (found via bucket B) ----------------------------


def test_single_no_marker_entry_survives_a_trailing_incidental_sub_list(pr_rows):
    """`STATE_PR_LEY_77_1957_ART9_040` (bucket B, settled): `"Agente
    General es la persona nombrada por un asegurador..."` is a single-entry,
    no-top-level-marker Civil-Code-style article whose body ALSO contains an
    enumerated `(1)`..`(11)` list of the term's own duties -- sub-clauses of
    ONE definition, not 11 separate entries. Today's all-or-nothing
    dispatch (`if not markers: <single-entry>; else: <markers-path>`)
    silently drops the term/lead-in text before the first marker and
    fragments the body into 11 bogus per-clause "entries" instead. Correct
    behavior: exactly ONE candidate, term "Agente General", whose
    definition includes both the lead-in sentence and the duties list."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART9_040"]
    assert row["text"].startswith("Agente General es la persona")  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert len(candidates) == 1
    assert candidates[0].terms == ("Agente General",)
    assert "persona nombrada por un asegurador" in candidates[0].definition_text
    assert "computar tarifas" in candidates[0].definition_text  # duty (2), still included


# --- Correct-zero guard: wholesale cross-law deferral -----------------------


def test_wholesale_cross_law_deferral_correctly_yields_zero_candidates(pr_rows):
    """`STATE_PR_LEY_52_2019_ART3` is a REAL bucket-A-workload row whose
    ENTIRE body defers to another law's definitions (`"...se entenderán de
    aplicación las definiciones de la Ley Núm. 228 de 12 de mayo de
    1942..."`) and defines zero terms of its own. This is a CORRECT
    rejection (there is nothing to extract), not a miss -- pinned here so a
    future fix does not fabricate local terms out of a cross-reference
    sentence to chase a zero-miss number."""
    row = pr_rows["STATE_PR_LEY_52_2019_ART3"]
    assert "se entenderán de aplicación las definiciones de la Ley" in row["text"]  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert candidates == []
