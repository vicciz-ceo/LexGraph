"""RED live-path tests -- sprint 2026-08-04-defs-us-preamble (US family 2:
body preambles that introduce definitions without ever using the literal
word "Definitions").

Planner-authored per this sprint's role split: the Planner owns every test
in this file; the Developer never edits it (only production code). Every
assertion below is proven RED against the CURRENT code shape (see this
sprint's `-log.md` for the captured failure output) before handoff -- this
sprint's `D1` convention inventory (real full-corpus counts, not sampled)
is what each fixture row is drawn from:

- **GA** (`STATE_GA_T7_C8_S7-8-1`): 1,224/28,154 real rows carry this
  preamble ("As used in this chapter, the term:"). Gate A
  (`pipeline._is_placeholder_heading`) already passes for 1,222 of them
  (GA's `section_title` is a bare citation-breadcrumb placeholder,
  verified 100% of 28,154 rows). Only Gate B
  (`pipeline._BODY_DEFINITIONS_PREAMBLE_RE`, which requires the literal
  word "Definitions") blocks capture -- confirmed live: only 1/1,224 rows
  passes Gate B. Once recognized, the body's `(N) "Term" means` entries are
  fully parseable by the EXISTING `USProfile.extract_definitions_from_
  section` (verified live on this exact fixture: 6 real candidates,
  "Access area"/"Access device"/"Candlefoot power"/"Control"/"Customer"/
  "Defined parking area") -- this is a single-gate fix, not an extractor
  change.
- **MD** (`STATE_MD_Agcr_T8_S3_S8-305`): MD's real convention is NOT GA's
  shape (the manager's original "the term"-anchored probe found only 1 MD
  row -- confirmed too narrow). MD's dominant family-2 convention, found by
  a broad full-corpus signal scan (3,327/39,552 real rows, 8.4%), is
  `"In this <section/subtitle/title>[,] the following words have the
  meanings indicated. (N) "Term" means ..."` -- quoted terms, same `(N)
  "Term"` shape GA/DE already use. MD fails Gate A for a DIFFERENT reason
  than GA: 93.5% of real MD headings are a bare `"§N–NNN."` pinpoint-
  citation placeholder, a shape `_is_placeholder_heading` does not
  recognize at all (confirmed live: `_is_placeholder_heading("§8–305.")
  is False`) -- this is core's territory (widening the placeholder
  recognizer), not this sprint's to fix, but the RED test below still
  proves live-path miss against the CURRENT code and pins the expected
  final terms.
- **NE** (`STATE_NE_C43_S43-3329`): NE's dominant family-2 convention
  (559/25,997 real rows) is `"For purposes of [sections ...], the
  following definitions apply: (N) Term means ..."` -- but UNQUOTED
  (no quote marks around the term at all). Confirmed live: NEITHER
  `extract_definitions_from_section` NOR `_extract_inline_quoted_
  definitions` extracts anything from this real NE shape (both quote-
  anchored). NE's fix therefore needs BOTH this sprint's recognition
  work AND a new unquoted-term entry splitter -- the latter is
  `2026-08-04-defs-us-markers` territory (entry-marker/quote-shape
  parsing), flagged as a cross-sprint dependency, not planned here.

No test in this file reads or downloads the parquet snapshot -- every row
is a small, real, vendored fixture (`fixtures/us_statutes/
us_preamble_rows.json`), full original columns actually used by the
production ingester, values unmodified except where noted as trimmed
(GA's row has a real, observed duplicate-paragraph scrape artifact
collapsed to one copy per clause; both MD and NE rows are truncated after
their genuine defined-term entries, dropping unrelated trailing
procedural text -- never paraphrased).
"""

from __future__ import annotations

import json
import pathlib

PREAMBLE_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_preamble_rows.json"
)


def _load_preamble_rows() -> dict[str, dict]:
    return json.loads(PREAMBLE_FIXTURE.read_text(encoding="utf-8"))


def _row_for_ingest(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


# --- Gate-level pin (documents WHERE the GA defect lives, per the existing
# --- convention set by test_qa_regression_us_state_law.py's IL test) -------


def test_body_definitions_preamble_regex_does_not_recognize_georgias_real_as_used_in_the_term_shape():
    """Unit-level pin: Gate A (`_is_placeholder_heading`) already passes for
    GA's real citation-breadcrumb heading -- the defect is entirely in Gate
    B. This is NOT the spec for the fix (the live-path test below is); it
    exists so a future reader can see exactly which of the two gates is
    broken for GA, mirroring this repo's existing convention for pinning a
    gate-level defect before the live-path proof (see
    `test_is_definitions_heading_correctly_rejects_a_bare_section_
    placeholder_with_no_heading_text` in `test_qa_regression_us_state_
    law.py`).
    """
    from app.definition_links.us_profile import (
        _BODY_DEFINITIONS_PREAMBLE_RE,
        _derive_heading_from_body,
        _is_placeholder_heading,
    )

    rows = _load_preamble_rows()
    row = rows["STATE_GA_T7_C8_S7-8-1"]

    assert _is_placeholder_heading(row["section_title"]) is True, (
        "Gate A must already pass for GA's real citation-breadcrumb heading "
        f"{row['section_title']!r} -- if this assertion fails, GA's defect "
        "has moved to Gate A and the fix plan in this sprint's contract is "
        "stale"
    )
    assert _BODY_DEFINITIONS_PREAMBLE_RE.match(row["text"][:400]) is None, (
        "Gate B currently requires the literal word 'Definitions' in the "
        "body preamble -- GA's real convention ('As used in this chapter, "
        "the term:') never uses that word, so this regex must NOT match "
        "it today. If this assertion fails, Gate B has already been "
        "widened and the live-path test below should be green, not red"
    )
    assert _derive_heading_from_body(row["text"]) is None, (
        "with Gate B failing, no heading is derived at all -- confirms the "
        "pipeline never even attempts extraction for this real GA row today"
    )


# --- Live-path RED: GA ------------------------------------------------------


def test_real_pipeline_captures_a_real_georgia_body_preamble_definitions_section_end_to_end(
    db_session, matter_with_users
):
    """Live-path confirmation: the real production pipeline creates ZERO
    definitions from a real, genuine Georgia 'As used in this chapter, the
    term:' preamble section today -- Gate B blocks it (see the unit-level
    pin above). Once Gate B recognizes this convention, the body's `(N)
    "Term" means` entries are ALREADY parseable by the existing extractor
    (verified live, not merely asserted): 6 real terms -- 'Access area',
    'Access device', 'Candlefoot power', 'Control', 'Customer', 'Defined
    parking area'.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_preamble_rows()
    row = rows["STATE_GA_T7_C8_S7-8-1"]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Georgia Code (preamble family probe)",
        rows=[_row_for_ingest(row)],
        jurisdiction="US-GA",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    expected_terms = {
        "Access area",
        "Access device",
        "Candlefoot power",
        "Control",
        "Customer",
        "Defined parking area",
    }
    assert expected_terms <= created_terms, (
        "the real production pipeline recognized ZERO of GA's real "
        f"'As used in this chapter, the term:' definitions (expected "
        f"{sorted(expected_terms)}, got {sorted(created_terms)}) -- Gate B "
        "(`_BODY_DEFINITIONS_PREAMBLE_RE`) requires the literal word "
        "'Definitions', which this real GA convention never uses. Full "
        "corpus: 1,222/1,224 real GA preamble rows pass Gate A and fail "
        "only Gate B (manager probe, -log.md M-R1)"
    )


def test_real_pipeline_does_not_fabricate_a_definition_from_a_georgia_section_that_merely_uses_the_word_term_without_defining_anything(
    db_session, matter_with_users
):
    """False-positive hazard guard (this family's known risk, per the
    contract): a real GA section that merely CONTAINS the word 'term' in
    its ordinary English sense ('at the term of the court' -- a court
    session, nothing to do with a defined term) must never be mistaken for
    a definitions block. Ingested ALONGSIDE the genuine GA definitions row
    in the SAME matter so the assertion is exact: the final definitions
    set must equal exactly the genuine row's real terms, never more.

    Currently RED for the same reason as the test above (GA's genuine row
    captures 0 today) -- the negative expectation is baked into the same
    exact-set assertion so a FUTURE over-broad Gate-B regex (e.g. one that
    fires on bare 'the term' without requiring a real defining idiom to
    follow) would also fail this test, not just silently ship a false
    positive.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_preamble_rows()
    genuine = rows["STATE_GA_T7_C8_S7-8-1"]
    negative = rows["STATE_GA_T44_C6_S44-6-165"]
    assert "the term" in negative["text"].lower(), (
        "fixture must reproduce the real false-positive-hazard shape: a "
        "genuine GA row using the word 'term' with no definitional idiom "
        "anywhere near it ('at the term of the court' -- a court session)"
    )

    ingest_result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Georgia Code (preamble family probe)",
        rows=[_row_for_ingest(genuine), _row_for_ingest(negative)],
        jurisdiction="US-GA",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    expected_terms = {
        "Access area",
        "Access device",
        "Candlefoot power",
        "Control",
        "Customer",
        "Defined parking area",
    }
    assert created_terms == expected_terms, (
        f"expected exactly the genuine row's real terms {sorted(expected_terms)}, "
        f"got {sorted(created_terms)} -- either GA's real preamble ('As used in "
        "this chapter, the term:') still isn't being captured (Gate B unfixed), "
        "or the negative-control row ('at the term of the court', which merely "
        "uses the word 'term' in its ordinary English sense) was WRONGLY "
        "captured as a definitions section, which is the false-positive hazard "
        "this test exists to guard against"
    )

    negative_article_id = ingest_result["article_ids"][1]
    from sqlalchemy import select

    from app.models.definition import Definition

    spurious = (
        db_session.execute(
            select(Definition).where(
                Definition.matter_id == m["matter_id"],
                Definition.article_id == negative_article_id,
            )
        )
        .scalars()
        .all()
    )
    assert spurious == [], (
        "no Definition row may be attributed to the negative-control article "
        "('at the term of the court' -- not a definitions section at all)"
    )


# --- Live-path RED: MD ------------------------------------------------------


def test_real_pipeline_captures_a_real_maryland_body_preamble_definitions_section_end_to_end(
    db_session, matter_with_users
):
    """Live-path confirmation: the real production pipeline creates ZERO
    definitions from a real, genuine Maryland 'In this section the
    following words have the meanings indicated.' preamble section today.

    MD is NOT the GA shape (D1 finding -- the manager's original probe
    under-counted MD at 1 row; the real dominant convention, found by a
    broad full-corpus signal scan, is 3,327/39,552 rows, 8.4%). MD fails
    Gate A for a DIFFERENT reason than GA: 93.5% of real MD headings are a
    bare pinpoint-citation placeholder ('§N–NNN.') that
    `_is_placeholder_heading` does not recognize at all -- confirmed by the
    unit-level assertion below. Widening the placeholder recognizer is
    shared-module (`pipeline.py`) territory -- coordinate with
    `2026-08-04-defs-core-scope`, not planned as an edit in this sprint.
    Once BOTH gates recognize this convention, the body's `(N) "Term"
    means` entries are ALREADY parseable by the existing extractor
    (verified live): 'Identity fraud', 'Identity theft passport'.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.definition_links.us_profile import _is_placeholder_heading

    m = matter_with_users
    rows = _load_preamble_rows()
    row = rows["STATE_MD_Agcr_T8_S3_S8-305"]

    assert _is_placeholder_heading(row["section_title"]) is False, (
        f"{row['section_title']!r} is MD's real bare pinpoint-citation "
        "heading shape ('§N–NNN.') -- confirmed NOT recognized by "
        "_is_placeholder_heading today (verified: 93.5% of 39,552 real MD "
        "rows share this exact shape). Widening the placeholder recognizer "
        "to cover it is core's territory, not this sprint's -- see the "
        "sprint report's dependency note"
    )

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Maryland Code (preamble family probe)",
        rows=[_row_for_ingest(row)],
        jurisdiction="US-MD",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    expected_terms = {"Identity fraud", "Identity theft passport"}
    assert expected_terms <= created_terms, (
        "the real production pipeline recognized ZERO of MD's real 'In this "
        f"section the following words have the meanings indicated.' "
        f"definitions (expected {sorted(expected_terms)}, got "
        f"{sorted(created_terms)}). Full corpus: 3,327/39,552 real MD rows "
        "(8.4%) share this exact multi-term, quoted-term, `(N)`-marked "
        "convention (D1 finding)"
    )


# --- Live-path RED: NE ------------------------------------------------------
#
# Re-scoped by the consolidating Planner (sprint 2026-08-04-defs-us-preamble,
# D2/M-R18): the original single test here (`test_real_pipeline_captures_a_
# real_nebraska_body_preamble_definitions_section_end_to_end`) asserted full
# 4-term capture for `STATE_NE_C43_S43-3329`, whose entries are ALL unquoted
# ("(1) Account means...", no quote marks anywhere in the body -- confirmed
# live below). That assertion can never pass from THIS sprint's file alone --
# its own docstring already conceded the row needs a NEW unquoted-term entry
# splitter (`2026-08-04-defs-us-markers` territory), but neither the test's
# name nor its assertion disclosed that, making this sprint's gate hostage to
# another panel's delivery (manager-confirmed defect, M-R18, independently
# found by scout S4). Split into two tests, coverage preserved exactly, now
# correctly attributed:
#
# 1. `test_real_nebraska_unquoted_body_preamble_is_a_genuine_in_family_
#    candidate_but_no_current_extractor_can_parse_it` -- a unit-level pin
#    (mirroring the GA gate-level pin above) documenting precisely what a
#    `BodyPreambleRule` CAN and CANNOT do for this real row using ONLY
#    today's real, unedited code: (a) the row is a genuine in-family
#    candidate (its body opens with this sprint's own trigger convention,
#    "the following definitions apply:"); (b) it is unrecognized today for
#    the ordinary reason (no placeholder heading, so body derivation is
#    never attempted -- ungated dispatch is what THIS sprint's registry rule
#    will need to fix); (c) EVEN WITH a correct heading, BOTH real
#    extractors (`USProfile.extract_definitions_from_section`,
#    `pipeline._extract_inline_quoted_definitions`) already return `[]` on
#    this exact body, live-verified, isolating the unquoted-term gap as a
#    pure EXTRACTION defect, not a recognition defect. This test is GREEN
#    today (like the family's negative-guard tests) and pins the boundary a
#    `BodyPreambleRule` built in this sprint's own file CAN deliver:
#    recognition, never unquoted extraction.
# 2. `test_real_pipeline_still_cannot_capture_the_real_nebraska_unquoted_
#    body_preamble_definitions_needs_markers_sprint_too` -- the renamed
#    original test, assertion UNCHANGED (all 4 real terms still required,
#    nothing weakened), name now disclosing the true cross-sprint
#    dependency up front, matching the convention already established by
#    this sprint's own `test_ne_unquoted_term_means_needs_markers_sprint_too`
#    in `test_us_body_preamble_capture_red.py` (a DIFFERENT real NE row,
#    `STATE_NE_C44_S44-5003`, same unquoted shape, same disclosed
#    dependency). Intentionally stays RED after `us_body_preamble.py` ships
#    alone -- that is the correct, disclosed state, not a defect.


def test_real_nebraska_unquoted_body_preamble_is_a_genuine_in_family_candidate_but_no_current_extractor_can_parse_it():
    """Unit-level pin (real code, no live pipeline run needed): documents
    the exact boundary between this sprint's territory (recognizing the
    preamble) and `2026-08-04-defs-us-markers`'s territory (splitting an
    unquoted entry) for `STATE_NE_C43_S43-3329`, so the live-path sibling
    below can be read as "needs markers too" rather than "this sprint's
    rule is broken."
    """
    from app.definition_links.us_profile import (
        _extract_inline_quoted_definitions,
        _is_placeholder_heading,
        extract_definitions_from_section,
    )

    rows = _load_preamble_rows()
    row = rows["STATE_NE_C43_S43-3329"]

    assert "the following definitions apply" in row["text"][:200].lower(), (
        "fixture must reproduce NE's real dominant family-2 trigger "
        "convention ('For purposes of ..., the following definitions "
        "apply:') -- this row is a genuine in-family candidate, not an "
        "unrelated shape"
    )
    assert _is_placeholder_heading(row["section_title"]) is False, (
        f"{row['section_title']!r} is NE's real 'View Statute N-NNNN' "
        "heading shape -- confirmed NOT a bare placeholder, so today's "
        "gated dispatch never even attempts body derivation for it "
        "(matches D1: 0/559 captured today for any reason)"
    )
    assert extract_definitions_from_section(row["text"], scope="law-wide") == [], (
        "USProfile.extract_definitions_from_section must return [] for "
        "this row's real unquoted entries even given a correct heading -- "
        "if this assertion fails, the extractor now parses unquoted terms "
        "and the sibling test below should be re-evaluated, not silently "
        "left mis-scoped"
    )
    assert _extract_inline_quoted_definitions(row["text"], scope="law-wide") == [], (
        "the inline-quote fallback is quote-anchored and must also return "
        "[] for this unquoted shape -- confirms the gap is a pure "
        "extraction defect (markers-sprint territory), not a recognition "
        "defect (this sprint's territory)"
    )


def test_real_pipeline_still_cannot_capture_the_real_nebraska_unquoted_body_preamble_definitions_needs_markers_sprint_too(
    db_session, matter_with_users
):
    """Live-path confirmation, name now disclosing the cross-sprint
    dependency up front (assertion UNCHANGED from the original test this
    replaces -- see the module-level note above): the real production
    pipeline creates ZERO definitions from a real, genuine Nebraska 'For
    purposes of ..., the following definitions apply:' preamble section
    today, and will STILL create zero from `us_body_preamble.py` alone,
    because NE's terms are UNQUOTED ('Account means ...', no quote marks) --
    confirmed live by the unit-level pin above: NEITHER
    `USProfile.extract_definitions_from_section` NOR
    `pipeline._extract_inline_quoted_definitions` extracts anything from
    this shape, both being quote-anchored. Going green needs BOTH this
    sprint's preamble-recognition fix AND a NEW unquoted-term entry
    splitter -- the latter is `2026-08-04-defs-us-markers` territory
    (entry-marker/quote-shape parsing), a cross-sprint dependency now
    disclosed by this test's own name, not just its docstring.
    """
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_preamble_rows()
    row = rows["STATE_NE_C43_S43-3329"]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Nebraska Revised Statutes (preamble family probe)",
        rows=[_row_for_ingest(row)],
        jurisdiction="US-NE",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    expected_terms = {"Account", "Authorized attorney", "Child support", "Department"}
    assert expected_terms <= created_terms, (
        "the real production pipeline recognized ZERO of NE's real 'For "
        "purposes of ..., the following definitions apply:' definitions "
        f"(expected {sorted(expected_terms)}, got {sorted(created_terms)}). "
        "Full corpus: 559/25,997 real NE rows (2.15%) share this exact "
        "unquoted multi-term convention (D1 finding). NOTE: going green "
        "here needs a NEW unquoted-term entry splitter in addition to "
        "preamble recognition -- see this sprint's report for the "
        "cross-sprint dependency on 2026-08-04-defs-us-markers. This test "
        "is EXPECTED to stay RED after this sprint's own rule ships alone "
        "(see the module-level note above and the unit-level pin test) -- "
        "its name discloses that, it is not a bug in this sprint's rule."
    )
