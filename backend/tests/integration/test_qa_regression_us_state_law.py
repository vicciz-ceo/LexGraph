"""QA regression coverage — sprint 2026-08-02-us-state-law.

Independent QA pass (separate agent from every Developer on this sprint).
Covers the manager-flagged probes (P1-P5) plus gap-filling regression tests
for every item that PASSED this QA cycle. FAIL items get their bounce
evidence recorded in `test_qa_regression_us_state_law_FAIL.py` (RED tests,
kept in a separate file so a `pytest -k qa_regression` sweep can
distinguish "QA added and expects green" from "QA added and expects red,
on purpose, to prove a bounce").

Item-by-item (QA cycle 1):

- Item 1 (vocabulary) PASS: a genuine backend<->frontend DRIFT GUARD --
  the sprint contract's own R5 design notes call this out as a documented
  follow-up ("comparing this mirror against a live/mocked fetch of the new
  endpoint") never actually written by the Developer. This test parses the
  REAL `frontend/src/constants/jurisdictions.ts` source (not a second
  hardcoded copy of the list) and diffs it against the backend's real
  `JURISDICTION_CODES` AND the live `GET /api/v1/jurisdictions` response,
  so a future edit to either side alone is caught.
- Item 2 (seam) PASS: `HebrewProfile`'s pass-through is checked against the
  bare module functions on inputs the Developer's own
  `test_definition_links_profiles.py` doesn't happen to exercise (a
  chapter-scope trigger phrase, and an empty string) -- confirms the
  wrapper really is behavior-identical, not just matching on the fixture
  the Developer picked.
- Item 4 (stamping) PASS, probe P1: proves `document_jurisdictions.get(...)`
  returning `None` on a miss is NOT reachable via either production
  ingester (`ingest_wiki_law` / `ingest_us_statute_rows`) -- both always
  create a Document and its Articles with the SAME `matter_id` in one
  call, and `Document.jurisdiction` is NOT NULL (ORM default AND DB
  `server_default`, both `"IL"`) -- so a genuinely ingested Article's
  document is always present in `document_jurisdictions` with a real,
  non-null value. The miss branch is defensive-only.
- Item 5 (US ingester), probe P1 sanity continued: a normal (non-colliding)
  two-file idempotent re-ingest keeps behaving correctly (companion to the
  FAIL file's collision reproduction, so the passing case doesn't regress
  while the bug above it gets fixed).

Folded in from QA cycle 1 (2026-08-02, QA cycle 2): the three cycle-1
bounce-proofs (P3 heading false-positive, the mandatory live-path trace for
item 3, and P4 the cross-title section_number collision for item 5) all now
PASS against the wave-3 fixes -- independently re-run and re-verified by QA
cycle 2 (including a from-scratch live-path reproduction: real DE rows
through the real `ingest_us_statute_rows` -> `run_definition_linking`
producing 3 real definitions and 2 DERIVES_FROM_LAW assertions stamped
`US-DE`, matching the manager's own probe exactly). Moved here, assertions
kept byte-identical, only the docstring framing changed from "RED, proves a
bounce" to "green, guards against a regression" -- per the sprint contract's
instruction that the estate carry no permanently "FAIL"-named file once a
cycle's bounces are fixed.

Folded in from QA cycle 2 (2026-08-02, QA cycle 3): the three cycle-2
bounce-proofs (Q2 empty-chapter row drop, Q3a ReDoS on a long non-letter
run, Q3b under-match on a letter-embedded section number) all now PASS
against the wave-4 fixes -- independently re-run and re-verified by QA
cycle 3. Moved here for the same reason as above;
`test_qa_regression_us_state_law_FAIL.py` (cycle 2's file) is deleted.
QA cycle 3's OWN fresh findings (6 new real defects across items 3 and 5,
found by testing 6 real state files -- IL, TX, FL, OH, PA, CA -- none of
which the Developer or QA cycle 2 had tested) are recorded separately in
`test_qa_regression_us_state_law_cycle3_FAIL.py`, RED on purpose.
"""

from __future__ import annotations

import json
import pathlib
import re
import signal
import time

import pytest

FRONTEND_JURISDICTIONS_TS = (
    pathlib.Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "constants"
    / "jurisdictions.ts"
)

US_STATUTES_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)


def _load_us_statutes_rows() -> list[dict]:
    return json.loads(US_STATUTES_FIXTURE.read_text(encoding="utf-8"))


# --- Item 1 (vocabulary) PASS: real backend<->frontend drift guard ---------


def _parse_frontend_jurisdiction_codes() -> list[str]:
    """Reconstruct the frontend's real `JURISDICTION_CODES` list by parsing
    the ACTUAL `.ts` source file (not a hand-copied literal) -- so this
    test breaks the moment the frontend file's list changes, not only when
    someone remembers to also update a second hardcoded copy.
    """
    assert FRONTEND_JURISDICTIONS_TS.is_file(), FRONTEND_JURISDICTIONS_TS
    src = FRONTEND_JURISDICTIONS_TS.read_text(encoding="utf-8")

    postal_block_match = re.search(
        r'const US_STATE_POSTAL_CODES = \(\s*((?:"[^"]*"\s*\+?\s*)+)\)\.split\(" "\);', src
    )
    assert postal_block_match, "could not locate US_STATE_POSTAL_CODES in jurisdictions.ts"
    joined = "".join(re.findall(r'"([^"]*)"', postal_block_match.group(1)))
    postal_codes = joined.split()

    return ["IL"] + [f"US-{code}" for code in postal_codes] + ["US-DC", "US-PR", "US-FED"]


def test_frontend_jurisdiction_list_source_matches_backend_source_exactly():
    from app.services.jurisdiction import JURISDICTION_CODES

    frontend_codes = _parse_frontend_jurisdiction_codes()
    assert frontend_codes == list(JURISDICTION_CODES), (
        "frontend/src/constants/jurisdictions.ts's real code list has drifted "
        "from backend app.services.jurisdiction.JURISDICTION_CODES"
    )


def test_live_jurisdictions_endpoint_matches_both_the_backend_constant_and_the_frontend_mirror(
    client, matter_with_users
):
    from app.services.jurisdiction import JURISDICTION_CODES

    m = matter_with_users
    response = client.get("/api/v1/jurisdictions", headers=m["contributor_headers"])
    assert response.status_code == 200
    body = response.json()

    assert body == list(JURISDICTION_CODES)
    assert body == _parse_frontend_jurisdiction_codes()


# --- Item 2 (seam) PASS: HebrewProfile pass-through on untested inputs -----


def test_hebrew_profile_is_identical_to_bare_functions_on_a_chapter_scoped_heading_and_empty_input():
    from app.definition_links import normalize, sections
    from app.definition_links.profiles import get_profile

    profile = get_profile("IL")
    assert profile.code == "IL"

    # A chapter-scope-trigger-bearing string is not itself a heading form,
    # but exercises normalize/is_definitions_heading on realistic prose the
    # Developer's own profile test didn't pick.
    body = "לענין פרק זה - הגדרות הבאות יחולו."
    assert profile.normalize_for_parsing(body) == normalize.normalize_for_parsing(body)

    assert profile.is_definitions_heading("הגדרות") == sections.is_definitions_heading("הגדרות")
    # Empty-string edge case: neither wrapper nor bare function may raise.
    assert profile.is_definitions_heading("") == sections.is_definitions_heading("")
    assert profile.normalize_for_parsing("") == normalize.normalize_for_parsing("") == ""


# --- Item 4 (stamping) PASS, probe P1: null-jurisdiction miss is -----------
# --- unreachable via either real production ingester ----------------------


def test_document_jurisdiction_is_never_null_after_either_production_ingester_runs(
    db_session, matter_with_users
):
    """P1: `pipeline.py`'s `document_jurisdictions.get(using_article.document_id)`
    returns `None` only if an Article's owning Document is missing from the
    per-matter jurisdiction map. Both real ingesters
    (`ingest_wiki_law`/`ingest_us_statute_rows`) always create the Document
    and every Article it produces with the SAME `matter_id` inside one call
    -- so a genuinely-ingested Article's document is always in that matter's
    document set. `Document.jurisdiction` is NOT NULL at the schema level
    (ORM default AND DB `server_default`, both `"IL"`), so even an
    inherited/legacy row can't carry a null jurisdiction. This test proves
    both invariants hold for BOTH ingesters, on a mixed-jurisdiction matter."""
    from sqlalchemy import select

    from app.definition_links.ingest import ingest_wiki_law
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.article import Article
    from app.models.assertion import Assertion
    from app.models.document import Document

    m = matter_with_users
    fixtures = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "wiki_laws"
    ingest_wiki_law(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title='חוק להגנת רכוש מופקד, תשכ"ה-1964',
        wiki_text=(fixtures / "חוק להגנת רכוש מופקד.wiki").read_text(encoding="utf-8"),
        jurisdiction="IL",
    )
    rows = json.loads(US_STATUTES_FIXTURE.read_text(encoding="utf-8"))
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (QA P1 probe)",
        rows=rows,
        jurisdiction="US-DE",
    )

    # Every Document created by either ingester carries a real, non-null
    # jurisdiction, and every Article's document_id resolves to a Document
    # in the SAME matter.
    documents = (
        db_session.execute(select(Document).where(Document.matter_id == m["matter_id"]))
        .scalars()
        .all()
    )
    assert len(documents) == 2
    doc_ids = {d.id for d in documents}
    for doc in documents:
        assert doc.jurisdiction is not None

    articles = (
        db_session.execute(select(Article).where(Article.matter_id == m["matter_id"]))
        .scalars()
        .all()
    )
    assert len(articles) > 0
    for art in articles:
        assert art.document_id in doc_ids  # never a miss against this matter's document set

    # And every assertion the real pipeline goes on to create is stamped
    # with a real (never null) jurisdiction.
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )
    assert len(result["created_assertions"]) > 0
    for created in result["created_assertions"]:
        row = db_session.get(Assertion, created["id"])
        assert row.jurisdiction is not None


# --- Item 5 (US ingester) PASS-case companion: non-colliding re-ingest -----
# --- still idempotent (sibling to the FAIL file's collision reproduction) -


def test_ingest_us_statute_rows_idempotent_reingest_across_two_separate_files_stays_correct(
    db_session, matter_with_users
):
    """Companion to the collision bounce: confirm the NORMAL (non-colliding)
    case -- two DIFFERENT files (different `title`s, so different
    Documents), each internally re-ingested twice -- still behaves
    correctly (no cross-file bleed, idempotent per file). This must stay
    green after the collision bug is fixed."""
    from sqlalchemy import select

    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.article import Article

    m = matter_with_users
    rows = json.loads(US_STATUTES_FIXTURE.read_text(encoding="utf-8"))

    for _ in range(2):
        ingest_us_statute_rows(
            db_session,
            repository_id=m["repository_id"],
            matter_id=m["matter_id"],
            title="Delaware Code -- Statutes (file A)",
            rows=rows,
            jurisdiction="US-DE",
        )
    for _ in range(2):
        ingest_us_statute_rows(
            db_session,
            repository_id=m["repository_id"],
            matter_id=m["matter_id"],
            title="Delaware Code -- Statutes (file B)",
            rows=rows,
            jurisdiction="US-DE",
        )

    articles = (
        db_session.execute(select(Article).where(Article.matter_id == m["matter_id"]))
        .scalars()
        .all()
    )
    # 3 rows/file * 2 files = 6 distinct articles, NOT 12 (idempotent) and
    # not fewer (no cross-file bleed).
    assert len(articles) == 6


# =============================================================================
# Folded in from QA cycle 1's test_qa_regression_us_state_law_FAIL.py --
# all three now PASS against the wave-3 fixes (independently re-verified by
# QA cycle 2, not merely re-run). Assertions kept byte-identical to the
# cycle-1 originals; only docstrings were reworded from "RED, proves a
# bounce" to "green, guards against a regression".
# =============================================================================


# --- Item 3 (US profile), probe P3: heading substring-match false-positive -
# --- regression guard -- confirmed fixed by the tightened first-word check -


def test_us_profile_is_definitions_heading_does_not_false_positive_on_non_definitions_headings():
    """P3 (QA cycle 1) confirmed FIXED: `is_definitions_heading` no longer
    matches real non-definitions headings that merely CONTAIN the word
    "Definitions" ("Application of Definitions to Prior Acts", "Repeal of
    Definitions"), while still matching the real DE fixture's genuine,
    scrape-noise-prefixed Definitions headings. (QA cycle 2 separately
    found a NEW regression the tightened regex itself introduces -- see
    `test_qa_regression_us_state_law_FAIL.py`'s Q3a/Q3b.)"""
    from app.definition_links.us_profile import is_definitions_heading

    non_definitions_headings = [
        "Application of Definitions to Prior Acts",
        "Repeal of Definitions",
    ]
    for heading in non_definitions_headings:
        assert is_definitions_heading(heading) is False, (
            f"{heading!r} was mis-classified as a Definitions-section heading; "
            "the unanchored \\bDefinitions?\\b substring check over-matches"
        )

    # Sanity: genuine definitions headings must still match (the fix must
    # not regress the real DE fixture's scrape-noise-prefixed heading).
    assert is_definitions_heading("§ Â\r\n        796. Definitions.") is True
    assert is_definitions_heading("§ Â\r\n        5227. Definition.") is True


# --- Item 3/4, mandatory live-path trace: US profile now reachable in prod -


def test_real_pipeline_recognizes_a_real_us_definitions_section_for_a_us_document(
    db_session, matter_with_users
):
    """QA cycle 1's mandatory live-path trace confirmed FIXED: the real
    production pipeline (`run_definition_linking`) now dispatches to
    `get_profile(document.jurisdiction)` per document -- a real US-DE row
    ingested via the real `ingest_us_statute_rows` and run through the real
    `run_definition_linking` recognizes the real "Definitions" section and
    creates real definitions/assertions, matching the manager's own
    from-scratch probe (3 definitions, 2 DERIVES_FROM_LAW assertions
    stamped US-DE) which QA cycle 2 independently reproduced."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    rows = _load_us_statutes_rows()  # real Delaware rows; row 0 is a genuine Definitions section

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (QA live-path trace)",
        rows=rows,
        jurisdiction="US-DE",
    )

    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "Affiliate" in all_terms, (
        "the real production pipeline (run_definition_linking) never recognized "
        "the real US-DE 'Definitions' section at all -- it created "
        f"{result['created_definitions']!r} definitions and "
        f"{result['created_assertions']!r} assertions from a real US Definitions "
        "row with 3 real defined terms. app.definition_links.profiles.get_profile "
        "is never called from pipeline.py, so USProfile is unreachable from any "
        "real product entry point; G2/G3/G4 are unmet at the product level"
    )
    assert "Branch office" in all_terms
    assert "Insured depository institution" in all_terms
    derives = [a for a in result["created_assertions"] if a["assertion_type"] == "DERIVES_FROM_LAW"]
    assert len(derives) == 2
    for a in derives:
        assert a["status"] == "accepted"


# --- Item 5, probe P4: cross-title section_number collision -- regression --
# --- guard -- confirmed fixed by the (document_id, section_number, ---------
# --- chapter, section_title) idempotency key --------------------------------


def test_ingest_us_statute_rows_no_longer_drops_a_row_when_its_section_number_collides_across_titles(
    db_session, matter_with_users
):
    """P4 (QA cycle 1) confirmed FIXED: `ingest_us_statute_rows`'s
    idempotency key now includes `chapter`/`section_title`, not just
    `section_number` -- a second, genuinely different row that happens to
    share an already-seen `section_number` across titles/chapters is no
    longer silently merged into the first row's Article."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.models.source_span import SourceSpan

    m = matter_with_users
    rows = _load_us_statutes_rows()
    row_a = dict(rows[0])  # act_id STATE_DE_T5_C7_SVIII_S796, section_number "796"
    row_b = dict(rows[1])  # act_id STATE_DE_T29_C60A_S6060, real DIFFERENT text

    # Simulate a real cross-title collision: a different title/chapter's
    # section happens to share Title 5 Section 796's bare section number.
    row_b["section_number"] = row_a["section_number"]
    row_b["act_id"] = "STATE_DE_T29_DIFFERENT_SECTION_SHARING_796"
    assert row_a["text"] != row_b["text"]  # genuinely different real content

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (QA collision probe)",
        rows=[row_a, row_b],
        jurisdiction="US-DE",
    )

    assert len(result["skipped_rows"]) == 0, (
        "row_b was not reported as skipped either -- it silently vanished, "
        "which is worse than an explicit skip: a bulk-run report would show "
        "a plausible row count while quietly losing a real section"
    )
    assert len(set(result["article_ids"])) == 2, (
        "row_b (a genuinely different section) was silently merged into "
        "row_a's Article because ingest_us_statute_rows keys idempotency by "
        "(document_id, section_number) only, ignoring title/chapter -- real "
        "statute files repeat bare section numbers across titles/chapters"
    )
    span_b = db_session.get(SourceSpan, result["source_span_ids"][1])
    assert row_b["text"] in span_b.quote_text, "row_b's real text was never persisted at all"


# =============================================================================
# Folded in from QA cycle 2's test_qa_regression_us_state_law_FAIL.py --
# all three now PASS against the wave-4 fixes (independently re-verified by
# QA cycle 3, not merely re-run). Assertions kept byte-identical to the
# cycle-2 originals; only docstrings were reworded from "RED, proves a
# bounce" to "green, guards against a regression".
# =============================================================================

QA_CYCLE2_FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "de_qa_cycle2_rows.json"
)


def _load_qa_cycle2_rows() -> dict[str, dict]:
    rows = json.loads(QA_CYCLE2_FIXTURE_JSON.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


# --- Item 5, Q2 (QA cycle 2): empty-chapter real row is no longer dropped --


def test_ingest_us_statute_rows_no_longer_drops_a_real_row_with_empty_chapter(
    db_session, matter_with_users
):
    """Q2 (QA cycle 2) confirmed FIXED: the wave-4 idempotency key no longer
    requires `chapter` to be non-empty -- a real DE row with an empty
    `chapter` but a valid, unique `citation` is ingested, not skipped (ruling
    R7(b): 647/21,649 real DE rows, 3.0%, share this exact shape)."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows

    m = matter_with_users
    rows = _load_qa_cycle2_rows()
    row = rows["STATE_DE_T5_C7_SVIII_S796"]
    assert row["chapter"] == "", "fixture must reproduce the real empty-chapter shape"
    assert row["citation"] == "5 Del. C. § 796", "citation is the real, unique canonical id"

    result = ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="Delaware Code -- Statutes (QA cycle2 Q2 probe, now green)",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-DE",
    )

    assert result["skipped_rows"] == []
    assert len(result["article_ids"]) == 1


# --- Item 3, Q3a (QA cycle 2): no more catastrophic backtracking -----------


def _run_with_deadline(fn, *args, deadline_seconds: int, **kwargs):
    """Run `fn(*args, **kwargs)` but fail fast (instead of hanging the
    suite) if it has not returned within `deadline_seconds` -- kept as a
    permanent regression guard even though the underlying implementation is
    now linear-time (a future regression back to a backtracking construct
    must not hang this suite either)."""

    class _DeadlineExceeded(Exception):
        pass

    def _handler(signum, frame):
        raise _DeadlineExceeded()

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(deadline_seconds)
    try:
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        return result, elapsed
    except _DeadlineExceeded:
        return None, float(deadline_seconds)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def test_is_definitions_heading_no_longer_hangs_on_a_real_de_heading_with_a_long_noise_prefix():
    """Q3a (QA cycle 2) confirmed FIXED: the wave-4 rewrite (linear-time,
    no nested-quantifier-over-alternation) returns well within budget on the
    real DE heading (43-char leading non-letter run, dataset-wide maximum)
    that hung the wave-3 regex for 15.8s+."""
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_qa_cycle2_rows()
    heading = rows["STATE_DE_T10_C54_S5402"]["section_title"]

    result, elapsed = _run_with_deadline(is_definitions_heading, heading, deadline_seconds=3)
    assert result is not None, f"is_definitions_heading did not return within {elapsed:.0f}s"
    assert result is False, "this heading is genuinely not a Definitions section"


# --- Item 3, Q3b (QA cycle 2): letter-in-section-number no longer breaks --
# --- the "Definitions is the first word" check -----------------------------


def test_is_definitions_heading_no_longer_undermatches_a_real_multiterm_definitions_section():
    """Q3b (QA cycle 2) confirmed FIXED: a real DE section number embedding
    a letter (`4A-103`) no longer defeats the noise-skip; the genuine
    'Payment order â€” Definitions.' UCC-convention heading now matches."""
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_qa_cycle2_rows()
    heading = rows["STATE_DE_T6_A4A_P1_S4A-103"]["section_title"]
    assert heading == "§ Â\r\n        4A-103. Payment order â Definitions."

    assert is_definitions_heading(heading) is True
