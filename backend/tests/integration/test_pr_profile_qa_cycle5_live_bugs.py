r"""QA cycle-5 (sprint 2026-08-04-defs-us-pr), independent verification: two
REAL, LIVE-PATH precision bugs found via an exhaustive (not sampled)
corpus-wide sweep of the two functions cycle-5 registered for real via
`ScopeTriggerRule` (`us_pr_scope_triggers.py`) -- `extract_local_definitions`
and `extract_adhoc_definitions`. Both bugs are reachable TODAY through
`get_profile("US-PR")` (confirmed: neither function is gated behind any
core-dispatch machinery -- both are directly registered and unconditionally
reached by `USProfile.extract_local_scope_definitions` for every
non-canonical PR article, which today is EVERY PR article, canonical
included, since `is_definitions_heading` is English-only). Distinct from
item 18c's dead-code `extract_definitions_from_section` findings (a
SEPARATE, unreachable function -- see the QA cycle-5 log entry for that
class of finding).

## Bug 1 -- page-break footer boilerplate truncates `extract_local_
definitions`' `definition_text` (2/12 corpus-wide matches affected, 17%)

`_LOCAL_TRIGGER_RE`'s definition-text group is `(.+?[.;])` -- non-greedy,
stops at the FIRST period or semicolon. Cycle 3 added footer-stripping
(`_PAGE_BREAK_FOOTER_RE`) to `extract_heading_anchored_definition` but never
ported it to `extract_local_definitions`, whose captured span can run
straight into the "Rev. <date> www.ogp.pr.gov Página N de M..." scrape
artifact -- and because that boilerplate opens with "Rev." (itself a
period-terminated abbreviation), the non-greedy group stops there instead
of at the definition's real end. The TERM and `scope` are still correct;
`definition_text` is silently truncated/corrupted. Exhaustive corpus sweep
(all 23,636 rows, not sampled): 12 total corpus-wide matches for
`_LOCAL_TRIGGER_RE`, of which exactly 2 are footer-truncated.

## Bug 2 -- a Spanish definite article between "(en adelante," and an
opening curly quote leaves a stray quote character in the captured term
(9/32 corpus-wide candidates affected, 28%)

`_ADHOC_TRIGGER_RE` is `r'\(en adelante,\s*["“]?([^)"”]+?)["”]?\)'`. The
optional leading `["“]?` only strips a quote sitting DIRECTLY after
"en adelante,\s*" -- but the real corpus very often has a Spanish definite
article between the comma and the quote: "(en adelante, el "Plan
Estratégico")". When that happens the leading `["“]?` matches zero-width,
and the catch-all group `[^)"”]+?` (which excludes straight `"` and the
CLOSING curly quote `"` U+201D, but NOT the OPENING curly quote `"`
U+201C) sweeps up "el " and the opening curly quote itself.
`_LEADING_SPANISH_ARTICLE_RE` then strips "el "/"la " from the front of the
captured string, but the embedded opening curly quote survives, producing
a corrupted term like `'“Plan Estratégico'` instead of
`'Plan Estratégico'`. Exhaustive corpus sweep: 32 total corpus-wide
candidates from `extract_adhoc_definitions`, of which exactly 9 (28%) carry
this stray-leading-quote corruption (`STATE_PR_LEY_17_2017_ART3` x2,
`STATE_PR_LEY_20_2014_ART5`, `STATE_PR_LEY_88_1966_ART11`,
`STATE_PR_LEY_74_1965_ART21`, `STATE_PR_LEY_125_2008_ART7`,
`STATE_PR_LEY_17_2017_ART2` x3).

Both counts (2/12, 9/32) are corpus-wide totals, not samples -- every
matching row was individually inspected. Fixture rows below are a
representative subset (not all 11 affected rows), byte-verified against
the real parquet.

Deliberately RED (not `xfail`) -- both are real precision defects on
functions now reachable from the live path, not accepted/documented
gaps. Fix is a Planner/Developer decision for a future cycle (this QA
pass does not touch `backend/app/**`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "pr_sample_rows_qa_cycle5.json"
)


def _load() -> dict[str, dict]:
    return {row["act_id"]: row for row in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


@pytest.fixture()
def pr_rows():
    return _load()


class TestFooterTruncationInLocalDefinitions:
    """Bug 1. `get_profile("US-PR")` is the live seam -- both rows reach
    `extract_local_definitions` unconditionally today (confirmed: neither
    row is canonical, and even canonical rows currently fall into the same
    branch, per the QA cycle-5 log entry's P1 finding)."""

    def test_documento_ley_236_2015_definition_text_is_not_truncated_at_the_footer(self, pr_rows):
        from app.definition_links.profiles import get_profile

        row = pr_rows["STATE_PR_LEY_236_2015_ART12"]
        profile = get_profile("US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        matching = [c for c in candidates if "revisar la cuenta" in c.terms]
        assert len(matching) == 1
        assert "Rev." not in matching[0].definition_text, (
            "definition_text must not be truncated at the page-break footer "
            f"boilerplate -- got {matching[0].definition_text!r}"
        )

    def test_ciudadano_ley_83_1941_definition_text_is_not_truncated_at_the_footer(self, pr_rows):
        from app.definition_links.profiles import get_profile

        row = pr_rows["STATE_PR_LEY_83_1941_SEC28"]
        profile = get_profile("US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        matching = [c for c in candidates if "ciudadano" in c.terms]
        assert len(matching) == 1
        assert "Rev." not in matching[0].definition_text, (
            "definition_text must not be truncated at the page-break footer "
            f"boilerplate -- got {matching[0].definition_text!r}"
        )


class TestStrayQuoteCorruptionInAdhocDefinitions:
    """Bug 2. Same live seam, `extract_adhoc_definitions` half."""

    def test_plan_estrategico_term_has_no_stray_leading_quote_character(self, pr_rows):
        from app.definition_links.profiles import get_profile

        row = pr_rows["STATE_PR_LEY_17_2017_ART3"]
        profile = get_profile("US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        matching = [c for c in candidates if "Plan Estratégico" in c.terms]
        assert len(matching) == 1, (
            "the term must be the clean 'Plan Estratégico', not a "
            f"quote-corrupted variant -- got candidates={candidates!r}"
        )

    def test_junta_term_has_no_stray_leading_quote_character(self, pr_rows):
        from app.definition_links.profiles import get_profile

        row = pr_rows["STATE_PR_LEY_74_1965_ART21"]
        profile = get_profile("US-PR")
        candidates = profile.extract_local_scope_definitions(
            row["text"], article_number=row["section_number"]
        )
        matching = [c for c in candidates if "Junta" in c.terms]
        assert len(matching) == 1, (
            "the term must be the clean 'Junta', not a quote-corrupted "
            f"variant -- got candidates={candidates!r}"
        )
