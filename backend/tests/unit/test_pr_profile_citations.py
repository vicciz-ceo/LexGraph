"""RED tests for the Puerto Rico (Spanish) jurisdiction profile's citation
grammar (sprint 2026-08-04-defs-us-pr; recon dossier §1 notes `find_citations`
is the one Protocol method that is "cleanly abstracted" per-profile already
-- this fills in PR's real Spanish citation shapes, measured over the full
23,636-row corpus, not English `Section N`/`U.S.C.` grammar).

`app.definition_links.pr_profile` does not exist yet -- `ModuleNotFoundError`
is the expected RED signal for every test in this file.

Measured citation shapes (corpus-wide row counts, `## Spanish idiom survey
(measured)` in the sprint contract):

  - `Ley N-YYYY` (dash form, e.g. "Ley 404-2000") -- 7,052 rows, the single
    most common PR citation shape, no English analog.
  - `Ley Núm. N de <date>` (e.g. "Ley Núm. 4 de 23 de junio de 1971") --
    2,194 rows, the older/formal citation form.
  - `Artículo N de esta Ley` / bare `Artículo N` -- 1,123 rows, PR's analog
    of English "Section N".
  - bare `§ N` -- 2,249 rows (the symbol itself is language-neutral, already
    partially handled by `USProfile.find_citations`'s `_SECTION_SYMBOL_RE`,
    but PR's own citation short-form is `N L.P.R.A. § N`, not `N U.S.C. §
    N`) -- 2,498 rows carry `L.P.R.A.`.

Fixture data: REAL rows, `backend/tests/fixtures/us_statutes/
pr_sample_rows.json` -- see that file's sibling `README.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# RED: `pr_profile` does not exist yet.
from app.definition_links.pr_profile import find_citations

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


def test_find_citations_detects_the_real_fixtures_dash_form_law_citation(pr_rows):
    """`STATE_PR_LEY_85_2018_ART9_04` real body cites `"la Ley 404-2000"`
    (dash form, 7,052 corpus-wide rows -- the dominant PR citation shape)."""
    row = pr_rows["STATE_PR_LEY_85_2018_ART9_04"]
    citations = find_citations(row["text"])
    assert any("404-2000" in c for c in citations)


def test_find_citations_detects_the_real_fixtures_ley_num_de_fecha_citation(pr_rows):
    """Same fixture row also cites `"la Ley Núm. 4 de 23 de junio de
    1971"` (the older formal citation form, 2,194 corpus-wide rows)."""
    row = pr_rows["STATE_PR_LEY_85_2018_ART9_04"]
    citations = find_citations(row["text"])
    assert any("Ley Núm. 4" in c or "Ley Núm. 4" in c for c in citations)


@pytest.mark.parametrize(
    "text,expected_substring",
    [
        ("Según dispuesto en el Artículo 30.050 de esta Ley.", "Artículo 30.050"),
        ("El límite establecido por el § 101 controla.", "§ 101"),
        ("Conforme a 15 L.P.R.A. § 1234, el término aplica.", "L.P.R.A."),
        ("Como se dispone en la Ley 249-2003, según enmendada.", "249-2003"),
        ("Ley Núm. 173 de 12 agosto de 1988, según enmendada.", "173"),
    ],
)
def test_find_citations_detects_named_spanish_reference_forms(text, expected_substring):
    citations = find_citations(text)
    assert any(expected_substring in c for c in citations)


def test_find_citations_returns_empty_list_for_text_with_no_citation():
    assert find_citations("Esta es una oración sin ninguna referencia legal.") == []
