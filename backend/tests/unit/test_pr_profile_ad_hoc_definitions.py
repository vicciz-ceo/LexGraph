"""RED tests for Puerto Rico (Spanish) definitions found OUTSIDE the
canonical `Definiciones` section (sprint 2026-08-04-defs-us-pr, gate P2
"Spanish definition idioms are captured ... including definitions outside
canonical Definiciones sections" -- the director's explicit mandate that a
definition appearing in "another article ... not in the usual place for
definitions" must still be captured, scoped only to where it applies).

`app.definition_links.pr_profile` does not exist yet -- `ModuleNotFoundError`
is the expected RED signal for every test in this file.

Two mechanically DISTINCT Spanish idioms were measured in the real corpus
(see sprint contract `## Spanish idiom survey (measured)`), the Spanish
analogs of Hebrew's `extract.extract_local_definitions`
(`לענין זה, "X" - ...`) and `extract.extract_adhoc_definitions`
(`(להלן - X)`) respectively -- both always `scope="local"` (article-scoped,
never broader):

  1. **`A los fines de este Artículo "X" <idiom>`** -- an explicit,
     article-scoped defining clause embedded in an ordinary substantive
     (non-Definiciones) article. 16 real corpus-wide occurrences of the
     exact "A los fines de este Artículo" phrase (plus a further 26 of the
     synonymous "Para propósitos de este Artículo"); ZERO of either occur
     inside a canonical Definiciones section (the whole-section scope-setter
     there is essentially always law-wide or, rarely, chapter -- never
     article -- see the sprint contract survey) confirming this is a
     mutually-exclusive, independent signal from `extract_definitions_from_
     section`, exactly mirroring the Hebrew local/section-heading split.
  2. **`(en adelante, X)`** -- an inline parenthetical apposition restating
     an immediately-preceding long noun phrase under a short name, with NO
     idiom verb and NO quote marks at all (`"el Comité de Acción para la
     Prevención de la Mortalidad Infantil (en adelante, Comité)"` -> the
     short name "Comité" IS the defined term, the preceding noun phrase IS
     its definition). 49 real corpus-wide occurrences.

Both are live-path Stage-2 extraction concerns, analogous in shape to
`extract_local_definitions`/`extract_adhoc_definitions` but NOT yet wired
into `pipeline.py`'s dispatch for ANY non-Hebrew profile as of sprint open --
`pipeline.py`'s current non-definitions-section branch calls the bare,
Hebrew-only `extract.extract_local_definitions`/`extract.extract_adhoc_
definitions` unconditionally for every article regardless of jurisdiction
(recon dossier §1, the "Deviation" finding) -- moving that dispatch behind
the profile seam is core sprint C3's job. These tests exercise the PR-owned
extraction functions directly (not through `pipeline.py`), which is buildable
now, independent of C3's pipeline-wiring -- see the sprint contract's item
plan for the pipeline-wiring follow-up, sequenced after core.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows.json` -- see that file's sibling `README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.extract import DefinitionCandidate

# RED: `pr_profile` does not exist yet.
from app.definition_links.pr_profile import extract_adhoc_definitions, extract_local_definitions

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- "A los fines de este Artículo ..." -- article-scoped ad-hoc definition -


def test_extract_local_definitions_finds_the_real_article_scoped_definition(pr_rows):
    """`STATE_PR_LEY_85_2018_ART9_04` (heading "Posesión de Armas y
    Sustancias Controladas en las Escuelas" -- NOT a Definiciones section)
    contains `'A los fines de este Artículo "cualquier tipo de arma"
    incluye todas las armas...'`. This must be captured with scope="local",
    exactly the director's "definition appears in another article, not the
    usual place, scoped only to that article/subsection" requirement."""
    row = pr_rows["STATE_PR_LEY_85_2018_ART9_04"]
    candidates = extract_local_definitions(row["text"])
    assert all(isinstance(c, DefinitionCandidate) for c in candidates)
    assert len(candidates) >= 1
    matching = [c for c in candidates if "cualquier tipo de arma" in c.terms]
    assert len(matching) == 1
    assert matching[0].scope == "local"
    assert "armas" in matching[0].definition_text.lower()


def test_extract_local_definitions_returns_nothing_for_a_body_with_no_trigger_phrase(pr_rows):
    """A canonical Definiciones-section body (already handled by
    `extract_definitions_from_section`) must not ALSO be double-captured by
    the ad-hoc local extractor -- it carries no "A los fines de este
    Artículo"/"Para propósitos de este Artículo" trigger at all."""
    row = pr_rows["STATE_PR_LEY_249_2003_ART3"]
    assert extract_local_definitions(row["text"]) == []


@pytest.mark.parametrize(
    "text,expected_term",
    [
        (
            'Para propósitos de este Artículo, "vehículo de motor" incluye motocicletas.',
            "vehículo de motor",
        ),
        (
            'A los fines de este Artículo, "residencia principal" significa el domicilio habitual.',
            "residencia principal",
        ),
    ],
)
def test_extract_local_definitions_recognizes_both_trigger_phrase_variants(text, expected_term):
    candidates = extract_local_definitions(text)
    assert any(expected_term in c.terms for c in candidates)
    assert all(c.scope == "local" for c in candidates)


# --- "(en adelante, X)" -- inline parenthetical apposition -------------------


def test_extract_adhoc_definitions_finds_the_real_en_adelante_apposition(pr_rows):
    """`STATE_PR_LEY_70_1997_ART1` (heading names the Committee itself, NOT
    a Definiciones section) contains `"...Comité de Acción para la
    Prevención de la Mortalidad Infantil (en adelante, Comité)..."` -- the
    short name "Comité" is the defined term; no idiom verb, no quotes."""
    row = pr_rows["STATE_PR_LEY_70_1997_ART1"]
    candidates = extract_adhoc_definitions(row["text"])
    assert all(isinstance(c, DefinitionCandidate) for c in candidates)
    matching = [c for c in candidates if "Comité" in c.terms]
    assert len(matching) == 1
    assert matching[0].scope == "local"


def test_extract_adhoc_definitions_returns_nothing_for_a_body_with_no_en_adelante(pr_rows):
    row = pr_rows["STATE_PR_LEY_249_2003_ART3"]
    assert extract_adhoc_definitions(row["text"]) == []


def test_extract_adhoc_definitions_recognizes_a_synthetic_en_adelante_apposition():
    text = (
        "El Departamento de Recursos Naturales y Ambientales "
        "(en adelante, el Departamento) administrará este programa."
    )
    candidates = extract_adhoc_definitions(text)
    assert any("Departamento" in c.terms for c in candidates)
