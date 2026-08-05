"""End-to-end integration test for the PR (Spanish) profile's Stage-1-to-3
chain -- sprint 2026-08-04-defs-us-pr, cycle 3, item 8 / gate P1 "Real PR
statutes parse" on the FULL pipeline, not just the profile layer in
isolation.

## PROMOTED off xfail (cycle-9 Planner, M-R15 step 2)

Originally authored cycle 3, marked `xfail(strict=False)` because
`get_profile("US-PR")` resolved to the generic (Spanish-inert) `USProfile`
until a `PRProfile` was registered -- that blocking REASON is now STALE:
the seam question was settled AGAINST the distinct-`PRProfile`-class
proposal (contract `## Coordination`) before that registration work was
ever done. `PRProfile` is a dead, unregistered leftover class; `US-PR`
was always going to resolve to `USProfile` with PR's Spanish rules
registered as `HeadingRule`/`EntrySplitterRule`/`TermClauseRule`/
`ScopeKindRule` instances (core's dispatch seam, merged this cycle). The
file's own original docstring anticipated exactly this moment ("if it
unexpectedly passes (XPASS), that is a SIGNAL the registry wiring landed
and this file should be promoted to a real, non-xfail assertion, not
silently ignored") -- promoting NOW rather than waiting for a silent
XPASS, so this is a visible, ordinary RED test like the rest of this
cycle's work, not a passively-monitored one.

**Confirmed still RED today, for the CURRENT correct reason**: no
`HeadingRule`/`EntrySplitterRule`/`TermClauseRule` is registered for
`"US-PR"` yet (this cycle's own item 31/33, `test_pr_profile_heading_
rule_live_cycle9.py` / `test_pr_profile_canonical_extraction_live_
cycle9.py`) -- Stage 1 (`is_definitions_heading`) genuinely returns
`False` for this row's real heading via `get_profile("US-PR")` right now.

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

Fixture: REUSES `STATE_PR_LEY_249_2003_ART3` from `pr_sample_rows.json`
(cycle 1, already vendored, byte-compared) -- no new fixture row needed.
Confirmed this cycle NOT to be one of the 21 canonical rows affected by
the baseline-collision defect named in `test_pr_profile_canonical_
extraction_live_cycle9.py` -- this row's own live-path extraction is
byte-identical to the already-tested direct call.
"""

from __future__ import annotations

import json
from pathlib import Path

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
