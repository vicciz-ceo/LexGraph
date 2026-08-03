"""RED tests for the Puerto Rico (Spanish) jurisdiction profile's heading
detector -- CYCLE 2 (sprint 2026-08-04-defs-us-pr), gate P1.

## Why this file exists

The manager's full-corpus sweep found `is_definitions_heading` misses 15 of
635 genuine canonical headings (620/635 detected, 0 false positives). 13 are
REAL misses; the other 2 (`STATE_PR_LEY_165_2020_ART1_2`,
`STATE_PR_LEY_51_2020_ART1_2`) are CORRECT rejections (Table-of-Contents
listings) that must STAY rejected -- widening the rule must not break them.
Full detail: `docs/sprint/sprints/2026-08-04-defs-us-pr-log.md`, the
manager's "Developer verification + GENERALIZATION GAP" entry.

## Root-cause diagnosis (Planner, cycle 2)

`is_definitions_heading` only checks the FIRST substantive token of the
whole (prefix-stripped) heading tail, or the LAST substantive token of the
whole tail (with a preposition exclusion). This is too GLOBAL: real PR
headings very often structure "definición(es)" as the first (or trailing-
preposition-suffixed) word of an INNER CLAUSE -- delimited by a semicolon,
a comma, or an em-dash -- not necessarily of the entire tail. Live-verified
(against `pr_profile.py`, all 13 misses individually re-checked -- see the
cycle-2 panel log for the full transcript) into three DISTINCT, independent
structural gaps:

  1. **Clause-scoped first-word position** -- the stem is the first
     substantive token of an inner clause, not of the whole tail. This
     single generalization covers ALL of:
       - the 7-row Civil-Code family `X; definición y <noun>` (semicolon-
         delimited): `"Parentesco; definición y alcance"`
         (`STATE_PR_CIVIL_ART365`), `"Subrogación; definición y alcance"`,
         `"Tutela; definición y objeto"`, `"Acto jurídico; definición y
         clasificación"`, `"Inoponibilidad; definición y clases"`,
         `"Retención; definición y ejercicio"`, `"Las normas de la
         compraventa; definición y aplicabilidad"`.
       - the comma-delimited statute-title variant of the SAME shape:
         `"Microseguros, definición y clases autorizadas"`
         (`STATE_PR_LEY_77_1957_ART15_020`).
       - the 2-row trailing-preposition family `..., definición de`
         (comma-delimited): `"Obrero o empleado, definición de"`
         (`STATE_PR_LEY_15_1931_SEC22` -- clause "definición de", "de" is
         the DANGLING trailing preposition, but "definición" is still the
         FIRST word of ITS OWN clause, so first-word-of-clause matching
         handles it WITHOUT needing a separate trailing-preposition rule).
         `STATE_PR_LEY_26_1941_ART78`'s `"Agregado, Definición de;
         Limitado a Un Solo Predio; ..."` needs the SAME clause-splitting
         one level deeper (comma-split first, THEN semicolon-split, or
         vice versa) -- "definición" is not the first/last word of the
         WHOLE tail at all (that's "Predio"), only of the innermost
         "Definición de" comma-sub-clause.
       - the em-dash-delimited family: `"Tasación y Cobro de Deficiencia
         —Definición de Términos"` (`STATE_PR_MUNICIPAL_ART7_212`) --
         "Definición" is the first word of the clause AFTER the em-dash,
         not of the whole tail (whose last word is "Términos").
     A single fix -- split the tail on `;`, `,`, and `—`/`–` into clauses,
     then apply the EXISTING first-word (or last-word-with-preposition-
     exclusion) rule to each clause independently, matching if ANY clause
     matches -- appears to cover all of the above based on this
     diagnosis, but the exact algorithm is the Developer's call; these
     tests pin the required OUTCOME, not the implementation.
  2. **Fully-parenthesized whole heading** -- `"(Definiciones)"`
     (`STATE_PR_LEY_77_1964_ART1`, `STATE_PR_LEY_60_1963_ART100`). Neither
     the first-word nor last-word regex ever matches because the
     surrounding `(`/`)` are not in `_TAIL_TOKEN_SPLIT_RE`'s split class,
     so the whole parenthesized string tokenizes as ONE token
     (`"(Definiciones)"`), which does not equal the bare stem pattern.
     Needs enclosing-parenthesis stripping before the existing rule runs --
     orthogonal to gap 1.

## The TOC rejections MUST stay rejected

`STATE_PR_LEY_165_2020_ART1_2` and `STATE_PR_LEY_51_2020_ART1_2` are both
`"Artículo 1.2. Tabla de Contenido ... Artículo 1.4 Definiciones Artí..."`
-- a Table-of-Contents dump that happens to NAME an article called
"Definiciones" as one line-item among many, truncated mid-word by the same
~200-char scrape artifact already documented for
`STATE_PR_LEY_135_1979_ART1` in cycle 1. Widening the rule per gap 1 above
(clause-scoped first-word matching) must NOT start matching these: neither
row's own SUBJECT is "Definiciones" (their subject is "Tabla de
Contenido", literally the heading's own first word) -- "Definiciones"
merely appears as the target of "Artículo 1.4" deep inside a long run-on
listing, never as the first or last word of any semicolon/comma/em-dash
clause of the heading's OWN tail (there are no such delimiters immediately
around "Definiciones" in either TOC dump -- it sits between "Artículo 1.4"
and "Artí[culo 1.5]", both plain whitespace-joined). Cycle 1 already pins
`STATE_PR_LEY_165_2020_ART1_2`; `test_second_toc_row_also_stays_rejected`
below adds the SECOND real row so both are red-lined, per the manager's
explicit instruction.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows_cycle2.json` -- see that file's sibling `README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import is_definitions_heading

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


# --- Gap 1: clause-scoped first-word position -------------------------------


def test_civil_code_semicolon_compound_heading_real_row(pr_rows):
    """`STATE_PR_CIVIL_ART365`: `"Artículo 365. Parentesco; definición y
    alcance"` -- "definición" is the first word of the SECOND
    semicolon-delimited clause, neither the first nor last word of the
    whole tail."""
    row = pr_rows["STATE_PR_CIVIL_ART365"]
    assert row["section_title"] == "Artículo 365. Parentesco; definición y alcance"  # sanity
    assert is_definitions_heading(row["section_title"]) is True


@pytest.mark.parametrize(
    "heading",
    [
        "Artículo 1139. Subrogación; definición y alcance",
        "Artículo 122. Tutela; definición y objeto",
        "Artículo 264. Acto jurídico; definición y clasificación",
        "Artículo 352. Inoponibilidad; definición y clases",
        "Artículo 1223. Retención; definición y ejercicio",
        "Artículo 1293. Las normas de la compraventa; definición y aplicabilidad",
    ],
)
def test_civil_code_semicolon_compound_heading_family(heading):
    """The remaining 6 of the 7 real Civil-Code `X; definición y <noun>`
    heading misses (verbatim real `section_title` strings, verified live
    against the corpus -- vendored as bare strings here rather than full
    fixture rows since the extraction body is irrelevant to a heading-only
    test, matching cycle 1's own precedent of mixing real-string
    parametrize cases with full JSON fixtures)."""
    assert is_definitions_heading(heading) is True


def test_comma_delimited_mid_token_compound_heading_real_row(pr_rows):
    """`STATE_PR_LEY_77_1957_ART15_020`: `"Artículo 15.020. Microseguros,
    definición y clases autorizadas"` -- the SAME mid-token-compound shape
    as the Civil-Code family, but comma-delimited instead of semicolon-
    delimited, proving the fix must not be semicolon-specific."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART15_020"]
    assert is_definitions_heading(row["section_title"]) is True


def test_trailing_preposition_heading_real_row(pr_rows):
    """`STATE_PR_LEY_15_1931_SEC22`: `"Sección 22. Obrero o empleado,
    definición de"` -- "definición" is the first word of the comma-
    delimited clause "definición de"; "de" dangles at the very end with
    nothing following it. First-word-of-clause matching catches this
    without needing any special trailing-preposition-specific rule."""
    row = pr_rows["STATE_PR_LEY_15_1931_SEC22"]
    assert row["section_title"] == "Sección 22. Obrero o empleado, definición de"  # sanity
    assert is_definitions_heading(row["section_title"]) is True


def test_trailing_preposition_heading_nested_clause():
    """`STATE_PR_LEY_26_1941_ART78`'s real heading: `"Artículo 78. Agregado,
    Definición de; Limitado a Un Solo Predio; Enajenación de o Gravamen
    Sobre el Predio"`. "Definición" is NEITHER the first nor the last
    substantive word of the WHOLE tail (that's "Agregado" / "Predio") --
    it is only the first word of the innermost comma-sub-clause
    ("Definición de") of the FIRST semicolon-clause ("Agregado, Definición
    de"). Needs clause-splitting at both delimiter levels, not just one."""
    heading = (
        "Artículo 78. Agregado, Definición de; Limitado a Un Solo Predio; "
        "Enajenación de o Gravamen Sobre el Predio"
    )
    assert is_definitions_heading(heading) is True


def test_em_dash_compound_heading_real_row(pr_rows):
    """`STATE_PR_MUNICIPAL_ART7_212`: `"Artículo 7.212. Tasación y Cobro de
    Deficiencia —Definición de Términos"` -- "Definición" is the first word
    of the clause immediately after the em-dash, not of the whole tail
    (whose own last word is "Términos")."""
    row = pr_rows["STATE_PR_MUNICIPAL_ART7_212"]
    assert (
        row["section_title"]
        == "Artículo 7.212. Tasación y Cobro de Deficiencia —Definición de Términos"
    )  # sanity
    assert is_definitions_heading(row["section_title"]) is True


# --- Gap 2: fully-parenthesized whole heading --------------------------------


def test_parenthesized_whole_heading_real_row(pr_rows):
    """`STATE_PR_LEY_77_1964_ART1`: `"Artículo 1. (Definiciones)"` -- the
    entire heading tail is wrapped in parentheses. Neither the first-word
    nor last-word regex matches today because `(`/`)` are not in
    `_TAIL_TOKEN_SPLIT_RE`'s split class, so the tail tokenizes as the
    single token `"(Definiciones)"`, never equal to the bare stem."""
    row = pr_rows["STATE_PR_LEY_77_1964_ART1"]
    assert row["section_title"] == "Artículo 1. (Definiciones)"  # sanity
    assert is_definitions_heading(row["section_title"]) is True


def test_parenthesized_whole_heading_second_real_row():
    """`STATE_PR_LEY_60_1963_ART100`'s real heading: `"Artículo 100.
    (Definiciones)"` -- the second of the 2 real corpus rows sharing this
    exact shape (vendored as a bare string; the extraction body is
    irrelevant here and is a 3,470-word row not worth vendoring in full
    just for a heading check)."""
    assert is_definitions_heading("Artículo 100. (Definiciones)") is True


# --- Negative: the 2 TOC rejections MUST stay rejected -----------------------


def test_second_toc_row_also_stays_rejected(pr_rows):
    """`STATE_PR_LEY_51_2020_ART1_2` -- the SECOND real Table-of-Contents
    row (cycle 1 only pinned the first, `STATE_PR_LEY_165_2020_ART1_2`).
    Both must stay rejected after the gap-1/gap-2 widening above: neither
    row's own subject is "Definiciones" (it's "Tabla de Contenido", the
    heading's own literal first word) -- "Definiciones" merely appears
    inside a long whitespace-joined TOC run-on naming "Artículo 1.4
    Definiciones" as one line-item, never adjacent to a semicolon/comma/
    em-dash clause boundary of this heading's OWN tail."""
    row = pr_rows["STATE_PR_LEY_51_2020_ART1_2"]
    assert "Definiciones" in row["section_title"]  # sanity: substring really present
    assert row["section_title"].startswith("Artículo 1.2. Tabla de Contenido")  # sanity
    assert is_definitions_heading(row["section_title"]) is False


def test_first_toc_row_still_rejected_after_widening():
    """Explicit re-confirmation (not merely relying on cycle 1's own file
    remaining green) that `STATE_PR_LEY_165_2020_ART1_2` -- the row whose
    widening risk M-R6 called out by name -- stays rejected in THIS file
    too, so a reviewer scanning cycle 2 alone sees the guard, not just a
    cross-file assumption. Real heading string, already byte-vendored in
    cycle 1's `pr_sample_rows.json` (not re-vendored here -- this test only
    needs the string, not the full row)."""
    heading = (
        "Artículo 1.2. Tabla de Contenido TABLA DE CONTENIDO CAPÍTULO I - "
        "DISPOSICIONES GENERALES Artículo 1.1 Título Artículo 1.2 Tabla de "
        "Contenido Artículo 1.3 Declaración de Política Pública Artículo 1.4 "
        "Definiciones Ar"
    )
    assert is_definitions_heading(heading) is False


# --- Negative: widening must not start capturing bucket-D-shaped headings --


@pytest.mark.parametrize(
    "heading",
    [
        # Ordinary substantive headings that happen to contain a comma or
        # semicolon elsewhere -- the clause-splitting widening must not
        # turn every comma/semicolon into a false-positive trigger.
        "Artículo 5. Poderes, deberes y facultades del Secretario",
        "Sección 12. Vigencia; disposiciones transitorias",
        "Artículo 9. Penalidades y sanciones administrativas",
    ],
)
def test_clause_splitting_widening_does_not_create_new_false_positives(heading):
    """Regression guard for the gap-1 fix's blast radius: splitting the
    tail into clauses and checking EACH one must not turn an ordinary
    semicolon/comma-joined heading with NO "definición" stem anywhere into
    a false positive."""
    assert is_definitions_heading(heading) is False
