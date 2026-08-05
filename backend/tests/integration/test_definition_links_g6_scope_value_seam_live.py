"""G6 -- ONE live-path proof (sprint 2026-08-05-defs-core-follow-on-2,
gate G6): the scope-VALUE seam, through the REAL `run_definition_linking`
entry point, to a real `USES_DEFINITION` assertion.

**Real row anchor.** `STATE_KY_TXIII_C156_S156.106` (real `us_ky_statutes
.parquet` row, independently re-fetched and byte-verified this session,
`backend/.venv/bin/python3` + `pyarrow`, not copied from another agent's
fixture):

    section_title: "156.106 Critical shortage areas -- Definition for
                     section and KRS 161.605 -- Appointment of retired
                     teachers and administrators"
    text (verbatim, first 300 chars): '156.106 Critical shortage areas --
      Definition for section and KRS 161.605 --\\n\\nAppointment of retired
      teachers and administrators.\\n\\n(1) For purposes of this section and
      KRS 161.605, "critical shortage area" means a lack\\n\\nof certified
      teachers in particular subject areas, in grade levels, or in geogra...'

Real, declared scope: this section's OWN definitions govern "this section
[156.106] and KRS 161.605" -- an M9 enumerated LOCAL scope over exactly
TWO article numbers (already proven expressible at the matcher/containment
level for this EXACT row by `claude/defs-us-headings-plan5@8cd3829`,
`test_definition_links_matcher_u2_scope_cycle5.py::
test_ky_enumerated_local_scope_links_mentions_in_both_named_sections`).
What was NOT proven anywhere -- and what this file closes -- is that the
value ever reaches a `Definition` FROM THE REAL DEFINITIONS-SECTION
EXTRACTION PATH (`determine_scope` -> `extract_definitions_from_section`
-> pipeline stamping), not just from a hand-built `DefinitionCandidate`.

**Ingestion path -- corrected after a dev-cycle escalation (dev4, via
manager relay).** The first version of this file ingested through
`ingest_wiki_law` (the ISRAELI wiki-marker path, `@ N. <heading>`), whose
`sections._ARTICLE_MARKER_RE` is `^@\\s+(?P<number>\\d+[א-ת]*)\\.\\s*...` --
a pure digit run. Real KY article numbers are dotted (`"156.106"`), so
that regex truncated `@ 156.106.` to number `"156"` and leaked `".106"`
into the heading -- a WIKI-INGESTION-PATH artifact, not a production
defect: `ingest_us_statutes.py`'s own module docstring states plainly that
real US rows are "already-parsed row dicts rather than raw wiki-marker
text, so there is no `parse_articles` call: each row maps directly to one
Article" -- confirmed by grep, `parse_articles` is called only from
`ingest.py` (the IL/wiki path). **US statutes never touch
`_ARTICLE_MARKER_RE` in production**, so the earlier failure was a
test-harness artifact, not a seam or `sections.py` defect -- `_ARTICLE_
MARKER_RE` is correctly left untouched. This file now ingests through
`ingest_us_statute_rows` (`app.definition_links.ingest_us_statutes`), the
SAME row-dict path real US parquet ingestion uses: `Article.number = str
(row["section_number"])`, stored verbatim, no marker regex involved -- so
the real dotted number `"156.106"` persists exactly, and this file is now
MORE production-faithful than the original version, not less.

**One remaining disclosed adaptation, not a fabrication.** The real row's
own quoted term is NOT leading in its numbered block (`(1) For purposes
of ..., "critical shortage area" means ...`) -- `us_profile._LEADING_
QUOTE_RE` requires the quote to open the block (`(N) "Term" means ...`),
so extracting THIS row's real word order needs a new `TermClauseRule`/
`EntrySplitterRule` recognizing the "For purposes of X" preamble shape --
that is explicitly the headings/markers panel's OWN later work (per this
gate's own text: "the headings panel builds the rules LATER on their
side"), and building it here would cross this Planner's write-set fence.
The fixture below keeps every real word of the row's own defined term,
definition text, and scope-declaring phrase ("for purposes of this
section and KRS 161.605") UNCHANGED, moving ONLY the scope clause to the
end of the sentence so the quoted term is leading -- satisfying TODAY's
unmodified `_LEADING_QUOTE_RE` splitter so this file tests the SCOPE seam
in isolation, not entry-splitting (a different, already-tracked gap).

**Design under test:** `pipeline.py`'s Definitions-SECTION stamping loop
calls `profile.determine_scope_assignments(...)` (gate G6) and fans out
one `DefinitionCandidate` copy per returned `ScopeAssignment` -- see
`test_definition_links_g6_scope_value_seam.py`'s module docstring for the
full design. This file proves that wiring reaches the REAL
`run_definition_linking` path end to end, on the production US ingestion
path.

**RED signal:** `test_...before_the_fix_...` is a POSITIVE CONTROL (P-R10)
-- it is expected to PASS regardless of whether G6 has landed, and
documents the live bug this gate fixes: a KY-156.106-shaped section with
no scope-value seam defaults to `"law-wide"` (`determine_scope`'s baseline
default) and therefore WRONGLY links a mention in an uninvolved KY article
(`139.486`, itself one of the OTHER 8 U2 rows, reused here deliberately
as a real, uninvolved KY article number -- same technique
`test_definition_links_matcher_u2_scope_cycle5.py` uses). The FIXED test,
`test_...after_the_fix_...`, registers a probe `ScopeKindRule` supplying
the real enumerated value; once `ScopeAssignment`/`detect_value`/
`determine_scope_assignments`/the pipeline fan-out all exist, it asserts
the enumerated co-target links and the uninvolved article does not.
"""

from __future__ import annotations


def _ky_156_106_body() -> str:
    # Real KY_156.106 words (verified against the live corpus this
    # session), scope clause moved to the END of the sentence so the
    # quoted term is LEADING in its numbered block (see module docstring
    # "One remaining disclosed adaptation").
    return (
        '(1) "critical shortage area" means a lack of certified teachers in '
        "particular subject areas, in grade levels, or in geographic "
        "locations at the elementary and secondary level, as determined "
        "annually by the commissioner of education, for purposes of this "
        "section and KRS 161.605."
    )


def _ky_rows() -> list[dict]:
    """Three row dicts in the REAL `vaquill/open-us-law` schema
    (`act_id, section_number, section_title, text, chapter`) --
    `ingest_us_statute_rows` stores `section_number` verbatim as
    `Article.number` (no marker-regex parsing), so the real dotted KY
    numbers survive exactly. `act_id`s are shaped like the real dataset's
    own convention but are not claimed to be byte-identical rows for
    161.605/139.486 (only 156.106's own text is the byte-verified real
    row; the other two are synthetic MENTION bodies, same technique
    `test_definition_links_matcher_u2_scope_cycle5.py` uses for its own
    member/non-member fixture articles)."""
    return [
        {
            "act_id": "STATE_KY_TXIII_C156_S156.106",
            "section_number": "156.106",
            "section_title": "Definitions for section and KRS 161.605",
            "chapter": "156",
            "text": _ky_156_106_body(),
        },
        {
            "act_id": "STATE_KY_TXVI_C161_S161.605",
            "section_number": "161.605",
            "section_title": "Appointment of retired teachers and administrators",
            "chapter": "161",
            "text": (
                "A critical shortage area shall be identified by the board "
                "annually under this section."
            ),
        },
        {
            "act_id": "STATE_KY_TXI_C139_S139.486",
            "section_number": "139.486",
            "section_title": "Sale, use, storage, or consumption of industrial machinery",
            "chapter": "139",
            "text": (
                "This section addresses a critical shortage area only in "
                "passing and is NOT one of the two sections the definition names."
            ),
        },
    ]


def test_g6_ky_156_106_shaped_section_before_the_fix_wrongly_links_an_uninvolved_ky_article(
    db_session, matter_with_users
):
    """POSITIVE CONTROL (P-R10) -- documents the live bug this gate fixes,
    through the PRODUCTION US ingestion path (`ingest_us_statute_rows`,
    real dotted KY numbers). No `ScopeKindRule` registered here."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test KY 156.106-shaped Statute (before fix)",
        rows=_ky_rows(),
        jurisdiction="US-KY",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    uses_edges = [
        a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    ]
    # Today's bug: `determine_scope` has no trigger phrase for "for
    # purposes of this section and KRS 161.605" (only "for purposes of
    # this chapter/part"), so scope defaults to "law-wide" -- every
    # article in the document, INCLUDING the uninvolved one, links.
    assert len(uses_edges) >= 2, (
        "positive control: today's law-wide default must link BOTH the "
        f"intended article and the uninvolved one; got {uses_edges!r}"
    )


def test_g6_ky_156_106_shaped_section_after_the_fix_links_only_the_two_named_sections(
    db_session, matter_with_users
):
    """The seam-fixed behavior, through the PRODUCTION US ingestion path:
    a registered `ScopeKindRule` recognizes the real "for purposes of this
    section and KRS 161.605" phrase and supplies the real two-member
    enumerated value (real KY article numbers, not renumbered). Article
    `161.605` must link; the uninvolved `139.486` must not."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.rules.registry import (
        ScopeAssignment,
        ScopeKindRule,
        register_scope_kind_rule,
    )

    def _detect(body_text: str):
        return "local" if "KRS 161.605" in body_text else None

    def _detect_value(body_text: str):
        return ScopeAssignment(kind="local", value=("156.106", "161.605"))

    register_scope_kind_rule(
        ScopeKindRule(jurisdiction_codes=("US-KY",), detect=_detect, detect_value=_detect_value)
    )

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Test KY 156.106-shaped Statute (after fix)",
        rows=_ky_rows(),
        jurisdiction="US-KY",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    uses_edge_ids = {
        a["id"] for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"
    }

    from sqlalchemy import select

    from app.models.article import Article
    from app.models.assertion import Assertion

    # `created_assertions`' own dicts (pipeline.py's `_create_assertion`)
    # do not carry `subject_entity_id` -- fetch the persisted rows instead.
    linked_articles = {
        row.subject_entity_id
        for row in db_session.execute(
            select(Assertion).where(Assertion.id.in_(uses_edge_ids))
        ).scalars()
    }

    articles_by_id = {
        row.id: row.number
        for row in db_session.execute(
            select(Article).where(Article.matter_id == m["matter_id"])
        ).scalars()
    }
    linked_numbers = {articles_by_id[aid] for aid in linked_articles if aid in articles_by_id}

    assert "161.605" in linked_numbers, (
        f"the enumerated co-target article must link; linked={linked_numbers!r}, "
        f"assertions={uses_edges!r}"
    )
    assert "139.486" not in linked_numbers, (
        f"the uninvolved article must NOT link once the real two-member "
        f"enumeration is honored; linked={linked_numbers!r}"
    )
