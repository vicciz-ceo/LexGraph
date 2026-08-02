"""QA regression coverage — sprint 2026-08-02-us-state-law.

Independent QA pass (separate agent from every Developer on this sprint).
Covers the manager-flagged probes (P1-P5) plus gap-filling regression tests
for every item that PASSED this QA cycle. FAIL items get their bounce
evidence recorded in `test_qa_regression_us_state_law_FAIL.py` (RED tests,
kept in a separate file so a `pytest -k qa_regression` sweep can
distinguish "QA added and expects green" from "QA added and expects red,
on purpose, to prove a bounce").

Item-by-item:

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
"""

from __future__ import annotations

import json
import pathlib
import re

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
