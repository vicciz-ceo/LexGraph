"""RED live-path tests for US family 2 (sprint 2026-08-04-defs-us-preamble,
gates U1/U5/U6): "a body preamble that never uses the literal word
'Definitions' -- 'As used in this chapter, the term:', 'In this section...
means', etc. -- must still produce a captured Definition, for GA/MD/NE/MS/SD
(the five states the sprint contract's manager table names as the two-gate
failure)."

Live-path discipline (recorded lesson, this repo:
"a named wiring test is not a live-path test"): every test here drives the
REAL public entry points -- `ingest_us_statute_rows` (writes real Article +
SourceSpan rows) then `run_definition_linking` (the real Stage 0-5
pipeline) -- never a bare regex-matches-a-string assertion, never a mock.

Fixtures: `backend/tests/fixtures/us_statutes/{ga,md,ne,ms,sd}_preamble_rows
.json`, each a JSON list of REAL, VERBATIM, full parquet row dicts pulled
live from the on-disk vaquill/open-us-law HF snapshot (never downloaded by
this test -- see each state's positive/negative selection in the sprint log,
D1/D3). No test in this file reads the parquet snapshot.

RED today, for the following confirmed reason (manager M-R1 + planner D1,
verified live against `backend/app/definition_links/pipeline.py` at time of
writing): GA passes Gate A (`_is_placeholder_heading`, its `section_title`
is a bare citation breadcrumb) but fails Gate B (`_BODY_DEFINITIONS_
PREAMBLE_RE` demands the literal word "Definitions", GA writes "the
term:"). MD/NE/MS/SD fail Gate A outright (their `section_title` shapes --
"section-number-only", "View Statute N-NNNN", "Miss. Code Ann. ...",
descriptive-but-real -- are not among the two patterns Gate A recognizes),
so body derivation is never even attempted. Either way, `is_definitions_
section` stays False for every row below, the Hebrew-only `extract_local_
definitions`/`extract_adhoc_definitions` fallback returns `[]` for English
text, and ZERO `Definition` rows are created for ANY of them today --
independently reproduced by running this file before `us_body_preamble.py`
exists (see the sprint log's RED run output).

**Cross-sprint dependency, not hidden**: this sprint's entire deliverable is
`BodyPreambleRule.derive_heading: body -> synthesized heading`, registered
via `register_body_preamble_rule` -- it can only ever supply a HEADING.
Whether the registry is even consulted for MD/NE/MS/SD's headings (which
fail today's Gate A) is the open question logged as M-R7(a)/escalated in
this sprint's D0; if the placeholder gate still wraps registry dispatch,
those states have a hard dependency on core widening `_is_placeholder_
heading` (or an equivalent), not just on this file landing. Separately, the
NE and SD tests marked `_needs_markers_sprint` below stay RED even after
BOTH `us_body_preamble.py` AND core's gate answer land, because their entry
text is UNQUOTED ("(1) Health insurance plan means...", "the term, loan
processor or underwriter, means...") -- verified live that NEITHER `USProfile
.extract_definitions_from_section` NOR the inline-quote fallback can parse
an unquoted entry today; that gap is `2026-08-04-defs-us-markers` territory
(M-R2 boundary #3), confirmed, not assumed.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _rows(state: str) -> dict[str, dict]:
    data = json.loads((FIXTURES / f"{state}_preamble_rows.json").read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in data}


def _ingest_and_link(db_session, matter_with_users, *, state: str, act_id: str, title: str):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _rows(state)[act_id]
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        rows=[row],
        jurisdiction=f"US-{state.upper()}",
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


def test_ga_as_used_in_this_chapter_the_term_is_captured(db_session, matter_with_users):
    """STATE_GA_T7_C8_S7-8-1: 'As used in this chapter, the term: (1)
    "Access area" means ...'. Real GA convention (manager M-R1's single-gate
    fix case); the source row itself carries the corpus's own documented
    duplicate-entry artifact (recon R2:F6) for "Access area", so this
    asserts a SUBSET of the real defined terms, not an exact set."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ga", act_id="STATE_GA_T7_C8_S7-8-1", title="GA T7 C8 (test)"
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert {"Access area", "Access device", "Financial institution"} <= all_terms


def test_md_in_this_section_the_following_words_have_the_meanings_indicated(
    db_session, matter_with_users
):
    """STATE_MD_Agtp_T9_S2_S9-258: '(a) (1) In this section the following
    words have the meanings indicated. (2) "Dwelling" has the meaning
    stated ... (3) "Eligible individual" means ...'. Real MD convention
    (planner D1: MD's `section_title` NEVER carries "Definitions" in any of
    its 39,552 rows; this is the dominant multi-entry shape, 3,327/39,552
    live-verified rows, 0/3,327 captured today)."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="md", act_id="STATE_MD_Agtp_T9_S2_S9-258", title="MD T9 (test)"
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert {"Dwelling", "Eligible individual"} <= all_terms


def test_ne_in_the_named_code_quoted_term_means_is_captured(db_session, matter_with_users):
    """STATE_NE_C30_S30-3803 (Nebraska Uniform Trust Code): '(1) "Action",
    with respect to an act of a trustee, includes a failure to act. (2)
    "Ascertainable standard" means ...'. Real NE convention with QUOTED
    terms (achievable within this sprint's own scope, verified live: once
    a heading is recognized, `extract_definitions_from_section` already
    parses this shape with zero changes needed there)."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ne", act_id="STATE_NE_C30_S30-3803", title="NE C30 (test)"
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert {"Action", "Ascertainable standard", "Beneficiary"} <= all_terms


def test_ne_unquoted_term_means_needs_markers_sprint_too(db_session, matter_with_users):
    """STATE_NE_C44_S44-5003: 'For purposes of the Children of Nebraska
    Hearing Aid Act: (1) Health insurance plan means ...' -- UNQUOTED term.
    Verified live (planner D1/D3): even with a synthesized heading,
    NEITHER `extract_definitions_from_section` NOR the inline-quote
    fallback yields a single candidate on this exact real body (both return
    `[]`) -- the unquoted shape is a marker-format gap, not a heading gap.
    This test intentionally stays RED after `us_body_preamble.py` ships
    alone; it documents a real cross-sprint dependency on
    `2026-08-04-defs-us-markers`, it is not a bug in this sprint's rule."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ne", act_id="STATE_NE_C44_S44-5003", title="NE C44 (test)"
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "Health insurance plan" in all_terms


def test_ms_as_used_in_this_article_the_term_is_captured(db_session, matter_with_users):
    """STATE_MS_T45_C9_S35-51: 'As used in this article, the term: (a)
    "Commissioner" means ... (b) "Department" means ...' -- 7 lettered
    entries, tail-after-last-entry only 10% of body (planner D2's
    discriminator: a clean whole-body BLOCK, not a clause). Real MS
    convention; body identical across duplicate `act_id` rows
    T45_C1/C2/C4/C7/C9_S35-51 in the corpus (a data-quality artifact noted
    in D1, not this test's concern)."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="ms", act_id="STATE_MS_T45_C9_S35-51", title="MS T45 (test)"
    )
    all_terms = {t.strip() for d in result["created_definitions"] for t in d["terms"]}
    assert {"Commissioner", "Department", "Disability"} <= all_terms


def test_sd_the_term_quoted_means_is_captured(db_session, matter_with_users):
    """STATE_SD_T11_C9_S11-9-10, heading 'Blighted area defined' (verb-form,
    a real heading -- SD fails Gate A because its heading IS genuine, not a
    placeholder): 'For the purposes of this chapter, the term "blighted
    area" means ...'. QUOTED term -- achievable within this sprint's own
    scope (verified live: the inline-quote fallback already parses this
    body once a heading is recognized as Definitions)."""
    result = _ingest_and_link(
        db_session, matter_with_users, state="sd", act_id="STATE_SD_T11_C9_S11-9-10", title="SD T11 (test)"
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "blighted area" in all_terms


def test_sd_unquoted_comma_term_needs_markers_sprint_too(db_session, matter_with_users):
    """STATE_SD_T54_C14_S54-14-12.1, heading 'Loan processor or underwriter
    defined': 'For the purposes of this chapter, the term, loan processor
    or underwriter, means ...' -- UNQUOTED, comma-delimited term (SD's
    dominant shape, 124/218 preamble rows, planner D2). Verified live: both
    extractors return `[]` on this exact body even with a real heading.
    Same documented cross-sprint dependency as the NE unquoted test above
    (M-R2 boundary #3: SD's unquoted term is markers-sprint territory even
    once the block itself is recognized)."""
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        state="sd",
        act_id="STATE_SD_T54_C14_S54-14-12.1",
        title="SD T54 (test)",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "loan processor or underwriter" in all_terms
