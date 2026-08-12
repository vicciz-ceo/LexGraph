"""RED live-path end-to-end tests for the family-4 heading-variants rule
(sprint 2026-08-04-defs-us-headings, gate U1 "every heading variant is
captured ... AND, where today's extractor can already parse that body, end-
to-end definition rows appear" -- ruling H-R1).

Two tiers, deliberately kept separate because they are blocked on
DIFFERENT things (see each test class's docstring):

- `TestComposedDeterministicEngine`: chains the REAL, already-existing
  `us_profile` functions (`extract_definitions_from_section`,
  `find_term_uses` via `matcher.link_articles_to_definitions`) together
  with our new module's `matches_heading_variant`, using the documented
  baseline-first/registry-second contract HAND-COMPOSED in the test (same
  technique as the registry-integration unit test) -- mirrors the existing
  `test_us_profile_definitions_section_end_to_end.py` pattern. This tier
  is blocked ONLY on the Developer creating
  `app.definition_links.rules.us_heading_variants` -- it does NOT need
  `claude/defs-core-scope` to have merged, because it never calls through
  `profiles.py`'s real registry consumption -- it simulates that contract
  directly against real `us_profile`/`matcher` functions that already
  exist on this branch today.

- `TestRealProductionPipeline`: drives the REAL, unmodified
  `pipeline.run_definition_linking` (DB-backed, via `matter_with_users`).
  This tier is BLOCKED ON CORE (`claude/defs-core-scope` C4): today's
  `pipeline.py` calls `profile.is_definitions_heading` directly with NO
  registry consultation at all (the registry doesn't exist in this
  worktree), so even a perfect `us_heading_variants.py` sitting in the
  `rules/` directory does nothing to the live production pipeline until
  core's seam lands and this branch is rebased onto it. Kept in this file
  (not deleted) so the Developer has the exact live-path target to build
  toward once unblocked -- see the sprint contract's Next Steps for the
  explicit blocked-on-core flag.

Fixture: `backend/tests/fixtures/us_statutes/us_heading_variants_rows.json`
(see its README section for full provenance and body-yield numbers, all
reproduced by the assertions below, not just asserted in prose).
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_heading_variants_rows.json"
)


def _load_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


class TestComposedDeterministicEngine:
    """Blocked ONLY on the Developer's `us_heading_variants.py` -- does not
    need core to have merged. See module docstring."""

    def test_connecticut_ucc_row_recognized_and_yields_82_real_candidates(self):
        """The sprint's flagship U1 proof: R-SEC recognizes the heading,
        and TODAY's (unmodified) numbered-entry extractor already parses
        the body -- both layers of ruling H-R1's split, in one row."""
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import (
            extract_definitions_from_section,
            is_definitions_heading,
        )

        row = _load_rows()["STATE_CT_T42a_C9_S42a-9-102"]
        assert is_definitions_heading(row["section_title"]) is False
        assert matches_heading_variant(row["section_title"]) is True

        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert len(candidates) == 82, (
            "live re-verification of the manager's own counterfactual: "
            "the real CT UCC 'Sec. 42a-9-102' body yields exactly 82 "
            "candidates via today's unmodified extractor"
        )
        terms = {t for c in candidates for t in c.terms}
        assert "Accession" in terms
        assert "Account debtor" in terms

    def test_missouri_mid_token_row_recognized_and_yields_6_real_candidates(self):
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import (
            extract_definitions_from_section,
            is_definitions_heading,
        )

        row = _load_rows()["STATE_MO_C334_S334.043"]
        assert is_definitions_heading(row["section_title"]) is False
        assert matches_heading_variant(row["section_title"]) is True

        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert len(candidates) == 6
        terms = {t for c in candidates for t in c.terms}
        assert {"Board", "License", "Military"}.issubset(terms)

    def test_wisconsin_verb_form_row_recognized_and_yields_27_real_candidates(self):
        """Upgrades ruling H-R1's 'verb-form yields 0/85, expected' framing:
        WI's own 'Words and phrases defined.' -- the sprint mandate's own
        cited example -- parses cleanly TODAY once recognized."""
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import (
            extract_definitions_from_section,
            is_definitions_heading,
        )

        row = _load_rows()["STATE_WI_C939_S939.22"]
        assert is_definitions_heading(row["section_title"]) is False
        assert matches_heading_variant(row["section_title"]) is True

        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert len(candidates) == 27

    def test_misspelled_row_recognized_and_yields_3_real_candidates(self):
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import (
            extract_definitions_from_section,
            is_definitions_heading,
        )

        row = _load_rows()["STATE_CT_T36a_C668_S36a-636"]
        assert is_definitions_heading(row["section_title"]) is False
        assert matches_heading_variant(row["section_title"]) is True

        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert len(candidates) == 3
        terms = {t for c in candidates for t in c.terms}
        assert "License" in terms
        assert "Licensee" in terms

    def test_a_defined_term_later_used_in_the_document_links_back(self):
        """Full Stage-1-to-3 composition (heading -> extraction -> term-use
        matching), mirroring
        test_us_profile_definitions_section_end_to_end.py's own pattern,
        but starting from a heading baseline alone cannot recognize."""
        from app.definition_links.matcher import link_articles_to_definitions
        from app.definition_links.profiles import get_profile
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.sections import Article as MatcherArticle
        from app.definition_links.us_profile import is_definitions_heading

        row = _load_rows()["STATE_MO_C334_S334.043"]
        assert is_definitions_heading(row["section_title"]) is False
        assert matches_heading_variant(row["section_title"]) is True

        us_profile = get_profile("US-MO")
        candidates = us_profile.extract_definitions_from_section(row["text"], scope="chapter")

        definitions_article = MatcherArticle(
            number=row["section_number"], heading=row["section_title"], body=row["text"]
        )
        using_article = MatcherArticle(
            number="334.045",
            heading="334.045. Fees for licensure by reciprocity.",
            body="An applicant seeking a License under section 334.043 shall pay a fee.",
        )

        edges = link_articles_to_definitions(
            candidates, [definitions_article, using_article], profile=us_profile
        )
        using_edges = [e for e in edges if e.article_index == 1]
        assert len(using_edges) == 1
        assert using_edges[0].term == "License"

    def test_colorado_truncated_row_zero_yield_is_a_documented_hand_off(self):
        """Ruling H-R1: a newly-recognized heading whose body yields zero
        is markers-family work, not ours to fix. This pins the CURRENT
        zero-yield behavior so nobody mistakes it for a regression later,
        and documents the act_id for the manager's hand-off routing:
        `STATE_CO_T22_A33_P1_S22-33-106.3` (CO, source-data-truncated
        heading, ordinary single-topic body with no `(N) "Term" means`
        block the current extractor recognizes)."""
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import extract_definitions_from_section

        row = _load_rows()["STATE_CO_T22_A33_P1_S22-33-106.3"]
        assert matches_heading_variant(row["section_title"]) is True
        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert candidates == [], (
            "HAND-OFF, not a defect: heading recognition (U1's first layer) is "
            "correct; body-yield (U1's second layer) is zero today -- markers-"
            "family territory per ruling H-R1, act_id logged for the manager"
        )

    def test_nevada_bare_verb_form_row_zero_yield_is_a_documented_hand_off(self):
        """Same hand-off shape, representative of NV's 8,829-row dominant
        bare-verb-form cluster (52% of the entire family-4 miss pool).
        act_id: `STATE_NV_T58_C706_S706.074`."""
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import extract_definitions_from_section

        row = _load_rows()["STATE_NV_T58_C706_S706.074"]
        assert matches_heading_variant(row["section_title"]) is True
        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert candidates == []

    def test_alaska_scope_unit_row_zero_yield_is_a_documented_hand_off(self):
        """Same hand-off shape, AND the sprint's chosen U2 scope-seam
        worked example -- see the Planner's report/log for the full scope
        escalation. act_id: `STATE_AK_T13_C13.06_S13.06.050`."""
        from app.definition_links.rules.us_heading_variants import matches_heading_variant
        from app.definition_links.us_profile import extract_definitions_from_section

        row = _load_rows()["STATE_AK_T13_C13.06_S13.06.050"]
        assert matches_heading_variant(row["section_title"]) is True
        candidates = extract_definitions_from_section(row["text"], scope="chapter")
        assert candidates == [], (
            "the body is one unbroken paragraph with no line break before its "
            "first '(1)' marker -- the extractor's line-anchored entry-boundary "
            "scan never finds a start; a markers-family defect, not ours"
        )


class TestRealProductionPipeline:
    """BLOCKED ON CORE (`claude/defs-core-scope` C4 -- the rule registry
    consultation in `pipeline.py`/`profiles.py`). See module docstring.
    Do not send the Developer chasing this class until core has merged and
    this branch has been rebased onto it."""

    def test_connecticut_ucc_row_produces_real_definitions_via_the_real_pipeline(
        self, db_session, matter_with_users
    ):
        from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
        from app.definition_links.pipeline import run_definition_linking

        m = matter_with_users
        row = _load_rows()["STATE_CT_T42a_C9_S42a-9-102"]

        ingest_us_statute_rows(
            db_session,
            repository_id=m["repository_id"],
            matter_id=m["matter_id"],
            title="Connecticut General Statutes (family-4 heading-variants probe)",
            rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
            jurisdiction="US-CT",
        )
        result = run_definition_linking(
            db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
        )
        assert len(result["created_definitions"]) > 0, (
            "the real production pipeline must recognize this heading and create "
            "real Definition rows once (a) core's registry consultation lands in "
            "pipeline.py/profiles.py and (b) this branch is rebased onto it -- "
            "until then this is EXPECTED RED, not a Developer defect (see class "
            "docstring)"
        )
