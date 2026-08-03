"""RED tests for the Puerto Rico (Spanish) jurisdiction profile's entry
extractor (sprint 2026-08-04-defs-us-pr, gates P1 "Real PR statutes parse"
and P2 "Spanish definition idioms are captured").

`app.definition_links.pr_profile` does not exist yet -- `ModuleNotFoundError`
is the expected RED signal for every test in this file.

Design (grounded in a full-corpus survey of the real 23,636-row
`us_pr_statutes.parquet` -- see the sprint contract's `## Spanish idiom
survey (measured)` section for the measured counts behind every shape
tested here). Unlike `USProfile.extract_definitions_from_section` (which
assumes a "(N)" marker at the START OF A LINE -- the DE fixture's body has
real newlines separating entries), the real PR `text` column has **zero
newlines within a Definiciones section body** (verified: 0/635 canonical
rows contain `\\n`) -- every entry marker sits inline, immediately after a
sentence boundary (`. `/`; `) or at the very start of the text. The
extractor therefore cannot reuse `text.split("\\n")`; it must scan the
continuous string directly (closer in shape to `pipeline.py`'s
`_extract_inline_quoted_definitions`, which is itself `finditer`-based over
one continuous string, not line-based).

Four independently-measured entry-marker/separator combinations are pinned,
each from its own real row (see fixtures README for full detail):

  - letter-period marker (`a.` .. `i.`) + curly-quoted term + colon
    separator (`STATE_PR_LEY_249_2003_ART3`, 34/635 canonical rows use this
    marker family).
  - letter-full-paren marker (`(a)` .. `(f)`) + UNQUOTED term + em-dash
    separator + verb idiom (`Es`/`Significará`/`Será`)
    (`STATE_PR_LEY_63_2023_ART3`, 272/635 rows use this marker family, the
    single most common one).
  - letter-close-paren-ONLY marker (`a)` .. `f)`, no opening paren -- a
    distinct, newer-law convention, 82/635 rows) + UNQUOTED term + em-dash,
    no verb idiom required (`STATE_PR_LEY_15_2024_ART3`).
  - NO marker at all -- a single-entry Civil-Code-style article (174/635
    canonical rows have no genuine multi-entry marker whatsoever)
    (`STATE_PR_LEY_77_1957_ART1_090`).

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows.json` -- see that file's sibling `README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.extract import DefinitionCandidate

# RED: `pr_profile` does not exist yet.
from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


def test_extracts_every_term_letter_period_marker_quoted_term_colon_idiom(pr_rows):
    """`STATE_PR_LEY_249_2003_ART3`: 9 entries, `a.`..`i.` markers, curly
    quotes, colon separator -- e.g. `a. "Agencia Gubernamental": cualquier
    departamento...`."""
    row = pr_rows["STATE_PR_LEY_249_2003_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    assert all(isinstance(c, DefinitionCandidate) for c in candidates)

    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Agencia Gubernamental",
        "Contratista o Constructor",
        "Costo estimado de la obra",
        "Dueño de la obra",
        "Obra de construcción",
        "Obra terminada",
        "Profesional licenciado",
        "Proyecto de construcción",
        "Valor de la obra",
    }
    assert expected_terms <= all_terms
    assert len(candidates) == 9
    assert all(c.scope == "law-wide" for c in candidates)


def test_extracts_every_term_full_paren_marker_unquoted_term_emdash_idiom(pr_rows):
    """`STATE_PR_LEY_63_2023_ART3`: 6 entries, `(a)`..`(f)` markers,
    UNQUOTED terms, em-dash separator, verb idiom (`Es`/`Significará`/
    `Será`) -- e.g. `(a) Instituto de Ciencias Forenses — Es el Instituto...`."""
    row = pr_rows["STATE_PR_LEY_63_2023_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")

    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Instituto de Ciencias Forenses",
        "Causa de la Muerte",
        "Instituto de Estadísticas",
        "Junta de Licenciamiento y Disciplina Médica",
        "Manera de la Muerte",
        "Registro Demográfico",
    }
    assert expected_terms <= all_terms
    assert len(candidates) == 6


def test_extracts_every_term_close_paren_only_marker_unquoted_term_no_idiom_verb(pr_rows):
    """`STATE_PR_LEY_15_2024_ART3`: 6 entries, `a)`..`f)` CLOSE-PAREN-ONLY
    markers (no opening paren), UNQUOTED terms, em-dash separator, no verb
    idiom needed -- e.g. `a) Composta. — Proceso de descomposición...`."""
    row = pr_rows["STATE_PR_LEY_15_2024_ART3"]
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")

    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Composta",
        "Productos agrícolas",
        "Departamento",
        "Programa de educación agrícola o programas especializados en agricultura",
        "Reciclaje vegetal",
        "Secretario",
    }
    assert expected_terms <= all_terms
    assert len(candidates) == 6


def test_extracts_the_single_entry_with_no_list_marker_at_all(pr_rows):
    """`STATE_PR_LEY_77_1957_ART1_090`: the whole body is one entry, no
    letter/digit marker anywhere -- `"Secretario. — Significa el Secretario
    de Hacienda."` -- 174/635 (27.4%) of real canonical rows have this
    shape (single-term Civil-Code-style definitional articles)."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART1_090"]
    assert row["text"] == "Secretario. — Significa el Secretario de Hacienda."  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")

    assert len(candidates) == 1
    assert candidates[0].terms == ("Secretario",)
    assert "Secretario de Hacienda" in candidates[0].definition_text


def test_scope_is_stamped_through_unchanged_not_derived_by_the_extractor(pr_rows):
    """`extract_definitions_from_section` takes `scope` as a caller-supplied
    parameter and stamps it onto every candidate verbatim (mirrors
    `extract.extract_definitions_from_section`'s and `USProfile.extract_
    definitions_from_section`'s existing signature) -- it does NOT itself
    inspect the body for scope-setting phrases (that is a separate, core-
    seam-owned concern -- see `test_pr_profile_scope.py`). Real row
    `STATE_PR_LEY_77_1957_ART30_020` opens with the chapter-scope phrase "A
    los fines de este Capítulo" but this test passes `scope="chapter"`
    explicitly to prove pass-through, not autodetection."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART30_020"]
    assert row["text"].startswith("A los fines de este Capítulo")  # sanity
    candidates = extract_definitions_from_section(row["text"], scope="chapter")

    assert len(candidates) == 9
    assert all(c.scope == "chapter" for c in candidates)
    all_terms = {term for c in candidates for term in c.terms}
    expected_terms = {
        "Asegurador",
        "Reclamación Procesable para Pago",
        "Plan de Cuidado de Salud",
        "Comisionado",
        "Proveedor Participante",
        "Suscriptor",
        "Organización de Servicios de Salud",
        "Seguro de Salud",
    }
    assert expected_terms <= all_terms


def test_a_repeated_quoted_phrase_inside_an_entrys_own_body_is_not_a_spurious_new_entry(pr_rows):
    """Entry (c) of `STATE_PR_LEY_77_1957_ART30_020` re-quotes its own
    heading term mid-definition (`"...Significa aquél definido como "Plan
    de Cuidado de Salud" en el Artículo 19.020..."`) -- this repeated quote
    is NOT immediately preceded by a fresh `(N)`/letter marker, so it must
    NOT be mistaken for the start of a new entry (would otherwise silently
    truncate entry (c) and/or fabricate a bogus empty entry)."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART30_020"]
    candidates = extract_definitions_from_section(row["text"], scope="chapter")
    plan_candidates = [c for c in candidates if "Plan de Cuidado de Salud" in c.terms]
    comisionado_candidates = [c for c in candidates if c.terms == ("Comisionado",)]
    # Entry (c)'s own re-quote of its own term must not swallow entry (d)
    # ("Comisionado") into entry (c)'s definition_text -- both must survive
    # as their own distinct candidates.
    assert len(plan_candidates) == 1
    assert len(comisionado_candidates) == 1
    assert "Comisionado de Seguros" in comisionado_candidates[0].definition_text
