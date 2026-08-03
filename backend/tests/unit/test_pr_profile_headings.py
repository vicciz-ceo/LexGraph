"""RED tests for the Puerto Rico (Spanish) jurisdiction profile's heading
detector (sprint 2026-08-04-defs-us-pr, gate P1 "Real PR statutes parse").

`app.definition_links.pr_profile` does not exist yet -- `ModuleNotFoundError`
is the expected RED signal for every test in this file.

Design (grounded in a full-corpus survey of the real 23,636-row
`us_pr_statutes.parquet`, not the recon's translation-guess lead -- see the
sprint contract's `## Spanish idiom survey (measured)` section):

  - `is_definitions_heading(heading)` must recognize the Spanish noun stem
    `Definici(ón|ones)` (NOT the generic substring `defin`) as the heading's
    own subject, using the SAME first-word-or-last-word-with-preposition-
    exclusion shape as `USProfile.is_definitions_heading` -- but Spanish,
    not English: `Artículo N.`/`Sección N.` prefix-stripped, then
    "Definici(ón|ones)" as the first substantive token, OR as the last
    substantive token when not preceded by a Spanish preposition (de, para,
    a, en, según...).
  - It must NOT fire on the generic `defin` substring alone -- real PR
    headings carry unrelated Spanish words sharing that prefix:
    "Aportaciones **Definidas**" (Defined Contributions, a pension term of
    art) and "sentencia **definitiva**" (final judgment) are NOT definitions
    headings; a naive substring check would wrongly flag both (12 + 2 real
    corpus rows respectively).
  - It must NOT fire when "Definiciones" appears merely as one item inside a
    longer heading it is not the subject of (a Table-of-Contents listing
    that happens to name an article called "Definiciones").
  - It MUST still fire on a real, confirmed data-quality artifact: 9/635 real
    canonical rows have `section_title` truncated mid-word into what should
    be the article's own BODY (the scrape splits `section_title`/`text` at a
    fixed ~200-char boundary with no regard for word boundaries) -- despite
    the resulting garbage tail, "Definiciones" is still the FIRST substantive
    token right after the "Artículo N." prefix in every one of these, so a
    first-word-anchored rule (not last-word-only) recognizes them correctly.

Fixture data: REAL rows from `vaquill/open-us-law`'s `us_pr_statutes.parquet`,
committed at `backend/tests/fixtures/us_statutes/pr_sample_rows.json` -- see
that file's sibling `README.md` (`## pr_sample_rows.json` section) for full
provenance and why each row was picked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# RED: `pr_profile` does not exist yet.
from app.definition_links.pr_profile import is_definitions_heading

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- Positive: bare canonical headings ---------------------------------------


def test_recognizes_bare_definiciones_heading(pr_rows):
    row = pr_rows["STATE_PR_LEY_249_2003_ART3"]
    assert row["section_title"] == "Artículo 3. Definiciones"  # sanity
    assert is_definitions_heading(row["section_title"]) is True


def test_recognizes_definiciones_heading_with_trailing_colon(pr_rows):
    row = pr_rows["STATE_PR_LEY_77_1957_ART30_020"]
    assert is_definitions_heading(row["section_title"]) is True


def test_recognizes_bare_definiciones_heading_second_law(pr_rows):
    row = pr_rows["STATE_PR_LEY_15_2024_ART3"]
    assert is_definitions_heading(row["section_title"]) is True


def test_recognizes_singular_definicion_compound_heading(pr_rows):
    """Compound `"Secretario, definición"` -- "definición" is the heading's
    own (last, non-prepositional) substantive word."""
    row = pr_rows["STATE_PR_LEY_77_1957_ART1_090"]
    assert is_definitions_heading(row["section_title"]) is True


@pytest.mark.parametrize(
    "heading",
    [
        "Definiciones",
        "Definición",
        "DEFINICIONES",
        "Artículo 3. Definiciones",
        "Sección 3. Definiciones",
        "Definiciones Generales",
        "Definiciones aplicables a las Zonas de Oportunidad",
        "Bienes; definición",
        "Poder; definición",
    ],
)
def test_recognizes_clean_synthetic_definiciones_headings(heading):
    assert is_definitions_heading(heading) is True


# --- Positive, but grounded in a real corpus data-quality artifact ----------


def test_recognizes_the_real_truncated_title_artifact_via_first_word_position(pr_rows):
    """`STATE_PR_LEY_135_1979_ART1`'s `section_title` is a REAL, NOT-injected
    scrape artifact: the title/body split lands mid-word, so the heading
    string runs on for 212 chars past "Definiciones" into what is really the
    article's own opening body prose (see fixtures README). Despite the
    garbage tail, "Definiciones" is the FIRST substantive token right after
    the "Artículo 1." prefix -- a first-word-anchored rule must still catch
    it; a last-word-only rule never would (the string doesn't end anywhere
    near "Definiciones")."""
    row = pr_rows["STATE_PR_LEY_135_1979_ART1"]
    assert len(row["section_title"]) > 120  # sanity: this really is the long/garbled title
    assert is_definitions_heading(row["section_title"]) is True


# --- Negative: false-positive guards (P-R2 zero-false-positive discipline) --


def test_does_not_flag_aportaciones_definidas_pension_heading(pr_rows):
    """"Aportaciones Definidas" = "Defined Contributions" (a retirement-plan
    term of art) -- shares the `defin` substring with "Definiciones" but is
    an unrelated Spanish word (`definida`, not `definici(ón|ones)`). 12/635
    real corpus headings share this exact false-positive-prone stem."""
    row = pr_rows["STATE_PR_LEY_160_2013_ART5_4"]
    assert "Definidas" in row["section_title"]  # sanity
    assert is_definitions_heading(row["section_title"]) is False


def test_does_not_flag_a_table_of_contents_listing_that_merely_names_an_article(pr_rows):
    """Real heading is a Table-of-Contents dump naming several articles,
    including "Artículo 1.4 Definiciones" as one line-item among many --
    "Definiciones" is not this article's OWN subject (this article's real
    subject is "Tabla de Contenido", the first substantive token)."""
    row = pr_rows["STATE_PR_LEY_165_2020_ART1_2"]
    assert "Definiciones" in row["section_title"]  # sanity: the substring really is present
    assert is_definitions_heading(row["section_title"]) is False


def test_does_not_flag_an_ordinary_non_definitions_heading(pr_rows):
    row = pr_rows["STATE_PR_LEY_85_2018_ART9_04"]
    assert is_definitions_heading(row["section_title"]) is False


def test_does_not_flag_another_ordinary_non_definitions_heading(pr_rows):
    row = pr_rows["STATE_PR_LEY_70_1997_ART1"]
    assert is_definitions_heading(row["section_title"]) is False


@pytest.mark.parametrize(
    "heading",
    [
        "Imposibilidad total y definitiva",  # "definitiva" = "final", unrelated word
        "Alcance de la sentencia definitiva",
        "Establecimiento de Cuentas de Aportaciones para el Programa de Aportaciones Definidas",
        "Repeal of Definitions",  # English preposition-object case must not leak in either
        "Section 3. Definitions",  # plain English heading -- not this profile's language at all
    ],
)
def test_does_not_flag_synthetic_false_positive_headings(heading):
    assert is_definitions_heading(heading) is False
