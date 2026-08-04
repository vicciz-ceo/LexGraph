"""RED (and explicitly DEFERRED-pending-core-seam) end-to-end integration
test for the PR (Spanish) profile's Stage-1-to-3 chain -- sprint
2026-08-04-defs-us-pr, cycle 3, item 8 / gate P1 "Real PR statutes parse"
on the FULL pipeline, not just the profile layer in isolation.

## Why this file exists now (it slipped a cycle already)

Cycles 1 and 2 both flagged this item ("the natural closing proof for
P1's 'real PR statutes parse' on the full pipeline") and both deferred
authoring it, waiting on core's seam spec. The program manager was
explicit this cycle: this is the live-path proof gate **P2** needs once
core's dispatch lands, and it must be authored NOW (marked `xfail` if it
cannot pass yet), not deferred a third time.

## Mirrors `test_us_profile_definitions_section_end_to_end.py` exactly

Same shape as the DE (English) sibling test: drives the real profile's
methods CHAINED together the way `pipeline.py` Stages 1-3 chain them
(`profile.is_definitions_heading` -> `profile.
extract_definitions_from_section` -> `matcher.link_articles_to_
definitions(..., profile=profile)`), proving the three PR-profile
capabilities (already unit-tested in isolation across this sprint's other
test files) actually COMPOSE through the SAME `get_profile(code)` seam
every other jurisdiction uses -- not just that `pr_profile.py`'s bare
module-level functions work when imported directly.

## Why this is core-gated (xfail, not a hard failure)

`get_profile("US-PR")` today resolves to a generic `USProfile(code=
"US-PR")` -- confirmed live (`backend/.venv/bin/python -c "from app.
definition_links.profiles import get_profile; print(type(get_profile(
'US-PR')))"` -> `USProfile`) -- because `PRProfile` is NOT YET registered
in `profiles.py`'s `_REGISTRY` (item 7, a shared-module edit M-R3 defers
until core `2026-08-04-defs-core-scope` publishes its seam spec AND this
sprint's own item 6 -- `PRProfile` construction -- lands; see the sprint
contract's `## Core seam coordination status`). `USProfile`'s baseline is
CONFIRMED INERT on Spanish text (`is_definitions_heading` returns `False`
on a real Spanish heading, `extract_definitions_from_section` returns
`[]` on Spanish body text with zero newlines defeating its line
splitter) -- so Stage 1 of this test genuinely fails today, for the
documented, core-gated reason, not a bug in this test or in
`pr_profile.py` itself. Marked `xfail(strict=False)`, same pattern as
`test_pr_profile_scope.py` (P3) -- re-run once core publishes and items
6/7 land; if it unexpectedly passes (`XPASS`), that is a SIGNAL the
registry wiring landed and this file should be promoted to a real,
non-xfail assertion, not silently ignored (`strict=False` surfaces XPASS
without failing the suite, matching this sprint's existing convention).

Fixture: REUSES `STATE_PR_LEY_249_2003_ART3` from `pr_sample_rows.json`
(cycle 1, already vendored, byte-compared) -- no new fixture row needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.xfail(
    reason=(
        "P1's full-pipeline live-path proof is core-gated: get_profile("
        "'US-PR') resolves to the generic (Spanish-inert) USProfile until "
        "PRProfile is registered in profiles.py's _REGISTRY (item 7), "
        "deferred per M-R3 until core sprint 2026-08-04-defs-core-scope "
        "publishes its seam spec and this sprint's item 6 (PRProfile "
        "construction) lands. Re-run once both land; promote off xfail "
        "once it passes for real."
    ),
    strict=False,
    raises=AssertionError,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows.json"
)


def test_definitions_section_terms_link_to_a_later_use_in_the_same_pr_document():
    from app.definition_links.matcher import link_articles_to_definitions
    from app.definition_links.profiles import get_profile
    from app.definition_links.sections import Article as MatcherArticle

    rows = {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}
    definitions_row = rows["STATE_PR_LEY_249_2003_ART3"]

    pr_profile = get_profile("US-PR")

    # Stage 1: this really is a Definiciones section, no English rule involved.
    assert pr_profile.is_definitions_heading(definitions_row["section_title"]) is True

    # Stage 2: extract every defined term.
    candidates = pr_profile.extract_definitions_from_section(
        definitions_row["text"], scope="law-wide"
    )
    all_terms = {term for c in candidates for term in c.terms}
    assert "Agencia Gubernamental" in all_terms
    assert "Contratista o Constructor" in all_terms

    # Stage 3: a LATER article/section using "Agencia Gubernamental"
    # (Spanish word-boundary rule, no Hebrew prefix-letter expansion) must
    # link back to its definition.
    definitions_article = MatcherArticle(
        number="3", heading=definitions_row["section_title"], body=definitions_row["text"]
    )
    using_article = MatcherArticle(
        number="4",
        heading="Artículo 4. Requisitos de fianza",
        body=(
            "Toda Agencia Gubernamental que otorgue un contrato de "
            "construcción exigirá al Contratista o Constructor una fianza "
            "de cumplimiento."
        ),
    )

    edges = link_articles_to_definitions(
        candidates, [definitions_article, using_article], profile=pr_profile
    )

    using_edges = [e for e in edges if e.article_index == 1]
    assert len(using_edges) >= 1
    assert any(e.term == "Agencia Gubernamental" for e in using_edges)
