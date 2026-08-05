"""QA (sprint 2026-08-04-defs-us-multiterm) -- U4 zero-miss sweep findings.

Independent adversarial verification (Sonnet/high). These 4 real rows were
found by an independent 53-jurisdiction sweep of the real corpus (QA's own
signal/adjudication, re-derived from scratch, never sampled -- see the QA
log entry for full methodology and per-jurisdiction counts) and represent
FOUR DISTINCT, VERIFIED gaps, none of which are on the sprint's own
Residual ledger under this description. Per this panel's QA role rule, this
file NEVER touches implementation -- these are RED, on purpose, pinning the
exact real-world shape each defect needs to stop reproducing, for whichever
panel/sprint picks each one up.

All four rows are vendored, byte-verified against the real parquet snapshot
(`301000fc3465374ee0f23c3c6953a8a861e95cad`) -- see
`qa_u4_finding_rows.json`.
"""

from __future__ import annotations

import json
import pathlib

FIXTURE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "qa_u4_finding_rows.json"
)


def _row(act_id: str) -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}[act_id]


def _ingest_and_link(db_session, matter_with_users, *, title, row, jurisdiction):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=title,
        rows=[row],
        jurisdiction=jurisdiction,
    )
    return run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )


def test_finding1_top_level_list_double_assertion_when_section_scope_is_law_wide(
    db_session, matter_with_users
):
    """FINDING 1 (NOT residual R1 -- R1 is scoped to TX's parent-clause-
    redirect mechanism specifically, attributed to markers' entry-boundary
    damage; this is a DIFFERENT mechanism, caused by F5's OWN top-level-list
    rule (`_leading_multiterm_candidate`), and verified to recur broadly --
    an independent corpus-overlap measurement found 524 rows across the
    full 53-jurisdiction corpus where a degenerate baseline candidate and a
    new F5 candidate share a term; this WY row is the exact live-path proof
    that the overlap materializes as a genuine double assertion, worked all
    the way through the real pipeline including Stage 3's "narrowest
    governs" precedence, not merely a candidate-level artifact).

    Mechanism, precisely: baseline's `_leading_quote_candidate` stamps
    whatever `scope` `profile.determine_scope(body)` returns for the
    SECTION (here: `"law-wide"`, since this row has no chapter-scope
    trigger phrase). F5's own `_leading_multiterm_candidate`
    (`rules/us_multiterm_shared_clause.py`) HARD-CODES
    `scope="law-wide"` -- it never reads or forwards the section's actual
    determined scope at all (`TermClauseRule.parse` doesn't even receive
    it; the seam's interface is `Callable[[str], list[DefinitionCandidate]]`,
    one block string in). When the section's real scope genuinely IS
    "law-wide" (the common case -- `determine_scope` only returns
    "chapter" for a narrow, specific trigger phrase), the two candidates'
    scopes TIE at the same rank. Per the core seam's own M10 ruling
    ("equal-rank ties: both survive, both get an assertion" -- a
    deliberate, documented, zero-miss-safe design for GENUINELY
    independent same-rank definitions), Stage 3 correctly does NOT
    suppress either -- but these two rows are not independent, they are
    ONE baseline row degenerately re-describing exactly what the OTHER row
    already captures correctly. The result: a single real downstream
    mention draws TWO `USES_DEFINITION` assertions for the same term, not
    because M10's tie-handling is wrong, but because F5's candidate was
    never given the chance to genuinely tie OR win on the section's real
    determined scope -- it was hardcoded.

    Real row `STATE_WY_T17_C14_S17-14-202`: `(vi) "Limited partnership" ...
    "domestic limited partnership" mean a partnership formed by two (2) or
    more persons ...` Baseline's degenerate candidate: `terms=("Limited
    partnership",)`. F5's correct candidate:
    `terms=("Limited partnership", "domestic limited partnership")`. Both
    `scope="law-wide"` -- a genuine tie, both created, both fire.

    See `test_finding1b` below for a RELATED but DISTINCT and arguably
    WORSE consequence of the same hardcoding, on a different real row whose
    section scope genuinely is "chapter" -- there, the SAME hardcoding
    causes the WRONG (degenerate) definition to win outright, silently,
    with no duplicate to signal that anything is wrong."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    row = _row("STATE_WY_T17_C14_S17-14-202")
    using_row = {
        "act_id": "STATE_WY_TEST_QA_FINDING1_USING",
        "text": "A limited partnership shall file its annual report by March 1.",
        "section_title": "17-14-299 Unrelated annual report requirement.",
        "section_number": "17-14-299",
        "chapter": "14",
    }
    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="WY Code (QA finding 1 -- F5 top-level-list double-assertion, tied scope)",
        rows=[row, using_row],
        jurisdiction="US-WY",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    using_article_uses = [
        a
        for a in uses
        if a["proposition"].startswith("Article 17-14-299 ")
        and '"Limited partnership"' in a["proposition"]
    ]

    assert len(using_article_uses) == 1, (
        f"F5's hardcoded scope=\"law-wide\" produced a genuine rank TIE with baseline's own "
        f"degenerate candidate (same section, both law-wide), so the SAME single mention of "
        f"'Limited partnership' in article 17-14-299 drew {len(using_article_uses)} "
        f"USES_DEFINITION assertions instead of 1: {using_article_uses!r}"
    )


def test_finding1b_wrong_definition_governs_when_section_scope_is_chapter(
    db_session, matter_with_users
):
    """FINDING 1b -- the SAME hardcoded `scope="law-wide"` from finding 1
    above, but on a real row whose section scope genuinely IS "chapter"
    (`STATE_IN_T4_A3_C9_S4-3-9-1`'s body opens "As used in this chapter:").
    Here baseline's degenerate candidate gets the REAL, narrower
    `scope="chapter"` while F5's correct candidate is stuck at the
    hardcoded `"law-wide"`. Per the seam's "narrowest governs" rule,
    "chapter" (rank 2) beats "law-wide" (rank 1000) OUTRIGHT -- no tie, no
    duplicate assertion to signal a problem. The WRONG, degenerate
    definition silently governs every downstream mention: a reviewer sees
    ONE clean `USES_DEFINITION` assertion, pointing at the WRONG
    `Definition` row (`terms=("Title",)`,
    `definition_text='and "interest in land" means...'`, dead prose) while
    the correct row (`terms=("Title", "interest in land")`, the entire
    reason F5 exists) sits in the database, created, but never linked to
    anything. This is arguably worse than finding 1's duplicate: a
    duplicate is at least visibly odd; a single assertion pointing at
    degenerate text looks completely normal."""
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking
    from app.models.assertion import Assertion
    from app.models.definition import Definition

    row = _row("STATE_IN_T4_A3_C9_S4-3-9-1")
    using_row = {
        "act_id": "STATE_IN_TEST_QA_FINDING1B_USING",
        "text": "The Title to the property shall be recorded within 30 days.",
        "section_title": "4-3-9-99 Unrelated recording requirement.",
        "section_number": "4-3-9-99",
        "chapter": "9",
    }
    m = matter_with_users
    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title="IN Code (QA finding 1b -- wrong degenerate definition wins outright)",
        rows=[row, using_row],
        jurisdiction="US-IN",
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    uses = [a for a in result["created_assertions"] if a["assertion_type"] == "USES_DEFINITION"]
    using_article_uses = [
        a
        for a in uses
        if a["proposition"].startswith("Article 4-3-9-99 ") and '"Title"' in a["proposition"]
    ]
    assert len(using_article_uses) == 1, (
        f"precondition failed -- expected exactly one assertion (this finding is about WHICH "
        f"row governs, not about duplication); got {using_article_uses!r}"
    )
    governing_definition_id = db_session.get(Assertion, using_article_uses[0]["id"]).object_entity_id
    governing = db_session.get(Definition, governing_definition_id)

    assert governing.terms == ["Title", "interest in land"], (
        f"the WRONG (degenerate baseline) Definition row governs this mention -- F5's correct "
        f"row (terms=['Title', 'interest in land']) LOST precedence to baseline's own degenerate "
        f"row (terms=['Title'], scope='chapter') because F5's rule hardcodes scope=\"law-wide\" "
        f"instead of forwarding the section's real determined scope (\"chapter\" for this row), "
        f"and \"chapter\" outranks \"law-wide\" under the seam's narrowest-governs rule. Governing "
        f"row: terms={governing.terms!r} scope={governing.scope!r} "
        f"definition_text={governing.definition_text!r}"
    )


def test_finding2_f5_nested_clause_boundary_skips_later_independent_clauses(
    db_session, matter_with_users
):
    """FINDING 2 -- new gap, not on the ledger. F5's nested-clause mechanism
    (`_nested_clause_candidates` in `rules/us_multiterm_shared_clause.py`)
    uses `_NEXT_NESTED_CLAUSE_RE` (matches only `", and the term(s)"`) to
    find where ONE nested clause's definition_text ends, then sets `cursor`
    to that boundary -- skipping every OTHER "the term(s)... means..."
    trigger whose start falls before the boundary. This works for the
    fixture shape it was built against (MT's `STATE_MT_..._S16-11-402`,
    exactly TWO nested clauses chained by literal ", and the term"), but
    real drafting routinely has a LONG RUN of entirely INDEPENDENT "The
    term X means Y." sentences with no "and"-chaining between them at all
    (real row below: 18 such triggers in one block; only the FIRST and one
    other far downstream are captured -- everything between is silently
    dropped, including the multi-term one this test pins).

    Real row `STATE_AL_T40_C21_S40-21-100`: inside its "TELEPHONE SERVICES"
    entry, `'The terms "teletypewriter" and "computer exchange service"
    mean the access from a teletypewriter, telephone, computer, or other
    device...'` -- a genuine 2-term F5 nested clause, reachable (baseline
    DOES split this section; `is_definitions_heading` is True), but never
    captured because an earlier nested clause's boundary search overshoots
    past it."""
    row = _row("STATE_AL_T40_C21_S40-21-100")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="AL Code (QA finding 2 -- F5 nested-clause boundary skip)",
        row=row,
        jurisdiction="US-AL",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    for term in ("teletypewriter", "computer exchange service"):
        assert term in all_terms, (
            f'"{term}" was not captured -- the nested-clause boundary mechanism skips it '
            f"because it sits after an EARLIER nested clause whose own boundary search "
            f"overshoots past it (see module docstring above for the exact mechanism). "
            f"All captured terms: {sorted(all_terms)!r}"
        )


def test_finding3_f6_as_defined_in_idiom_is_not_recognized(db_session, matter_with_users):
    """FINDING 3 -- new gap, not on the ledger. F6's `_IDIOM_GAP_RE`
    (`rules/us_inline_parenthetical.py`) recognizes exactly TWO
    cross-reference idioms (`has the meaning given that term in` /
    `has the meaning assigned by`). `"as defined in <citation>"` is a
    DIFFERENT, extremely common real-world cross-reference idiom -- the QA
    sweep found 2,813 occurrences of this exact shape across the full
    53-jurisdiction corpus (the single largest contributor to F6's overall
    miss count), none of them captured.

    Real row `STATE_AL_T13A_C8_S13A-8-52` (small, clean, reachable via the
    ordinary-body `ScopeTriggerRule` path -- heading is "Penalty for
    Violation of Article", not a Definitions heading, so this isolates the
    idiom-list gap specifically, not a reachability gap): `'... the
    criminal offense of "pharmacy robbery" as defined in Section
    13A-8-51(2) ...'`"""
    row = _row("STATE_AL_T13A_C8_S13A-8-52")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="AL Code (QA finding 3 -- F6 'as defined in' idiom not recognized)",
        row=row,
        jurisdiction="US-AL",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "pharmacy robbery" in all_terms, (
        f'"pharmacy robbery" was not captured -- F6\'s _IDIOM_GAP_RE does not recognize '
        f'"as defined in" as a cross-reference idiom (only the two "has the meaning..." '
        f"forms are recognized). All captured terms: {sorted(all_terms)!r}"
    )


def test_finding4_f6_cross_reference_idiom_never_fires_inside_a_recognized_definitions_section(
    db_session, matter_with_users
):
    """FINDING 4 -- new gap, not on the ledger, and architecturally
    distinct from finding 3. F6's cross-reference mechanism
    (`_cross_reference_candidates`) is wired into TWO dispatch paths, but
    only ONE of them actually calls it: the `ScopeTriggerRule`
    (`_extract_ordinary_body`, ordinary non-Definitions article bodies)
    calls both `_apposition_candidates` AND `_cross_reference_candidates`;
    the `TermClauseRule` (`_parse_block`, used for blocks INSIDE a
    recognized Definitions section) calls ONLY `_apposition_candidates`.
    Any cross-reference-idiom-defined term sitting inside a genuine,
    correctly-recognized Definitions section (the MOST common place such
    definitions occur in practice -- e.g. federal statutes' own extensive
    "Definitions" sections) is therefore never captured by F6 at all, even
    though the idiom itself IS one `_IDIOM_GAP_RE` already recognizes. The
    QA sweep found 289 such rows using only the two idioms already in
    `_IDIOM_GAP_RE` (i.e. NOT counting finding 3's separate "as defined in"
    gap) -- this is a pure reachability defect, not an idiom-list gap.

    Real row `STATE_DC_T38_C18N_S38-1853.13` (heading "§ 38-1853.13.
    Definitions." -- unambiguously a recognized Definitions section,
    confirmed live: `is_definitions_heading(...)` is `True` for this row):
    `'(6) Parent. -- The term "parent" has the meaning given that term in
    section 8101 of the Elementary and Secondary Education Act of 1965...'`
    -- the EXACT idiom `_IDIOM_GAP_RE` already matches, on a row that
    reaches the Definitions-section path instead of the ordinary-body
    path."""
    row = _row("STATE_DC_T38_C18N_S38-1853.13")

    from app.definition_links.profiles import get_profile

    profile = get_profile("US-DC")
    assert profile.is_definitions_heading(row["section_title"], row["text"]), (
        "precondition failed -- this row must be a RECOGNIZED Definitions section for the "
        "finding to isolate the TermClauseRule-vs-ScopeTriggerRule reachability gap; if this "
        "heading is no longer recognized, this test is no longer proving what it claims."
    )

    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="DC Code (QA finding 4 -- F6 cross-reference unreachable inside a Definitions section)",
        row=row,
        jurisdiction="US-DC",
    )
    all_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert "parent" in all_terms, (
        f'"parent" was not captured -- F6\'s cross-reference mechanism '
        f"(_cross_reference_candidates) is never invoked by the TermClauseRule path "
        f"(_parse_block calls only _apposition_candidates), so a cross-reference idiom "
        f"INSIDE a recognized Definitions section is unreachable even though the idiom "
        f"itself is recognized. All captured terms: {sorted(all_terms)!r}"
    )


def test_cross_reference_path_duplicate_candidates_are_still_deduped_at_persist_layer(
    db_session, matter_with_users
):
    """QA re-derivation, GREEN -- honestly reporting a suspected gap that
    did NOT hold up under a live-path check, per this panel's "re-derive,
    don't re-read" mandate. Re-deriving the sprint's own "duplicate-term
    rows: 0" post-M-R14-fix claim independently (full, not sampled,
    53-jurisdiction re-run of the bare `_extract_ordinary_body` function)
    found 32 real rows where `_cross_reference_candidates`
    (`rules/us_inline_parenthetical.py`) emits the SAME term twice within
    one extraction call -- M-R14's dedup (`seen_terms`) lives inside
    `_apposition_candidates` only, with no equivalent guard on the
    cross-reference path. That looked like a real gap in the "0
    duplicates" claim at the CANDIDATE level.

    Checked one level deeper before reporting it as a finding: real row
    `STATE_AR_T26_C57_S13_S26-57-1302` defines "Participating manufacturer"
    via the cross-reference idiom TWICE (same citation, same
    definition_text both times) -- two `DefinitionCandidate`s, confirmed.
    But run through the REAL production pipeline (this test), the
    PERSIST-layer dedup key `(article_id, sorted(candidate.terms))`
    (`pipeline.py`, unrelated to and unmodified by this sprint) collapses
    them: since BOTH candidates carry the IDENTICAL single-term tuple
    `("Participating manufacturer",)` for the SAME article, they resolve
    to ONE `Definition` row, not two. This is DIFFERENT from finding 1's
    hazard (whose two candidates have DIFFERENT term tuples --
    `("Title",)` vs `("Title", "interest in land")` -- so the dedup key
    never collides). Kept as a GREEN regression guard rather than
    discarded silently, so a future reader does not have to re-derive this
    same distinction from scratch."""
    row = _row("STATE_AR_T26_C57_S13_S26-57-1302")
    result = _ingest_and_link(
        db_session,
        matter_with_users,
        title="AR Code (QA re-derivation -- cross-reference persist-layer dedup)",
        row=row,
        jurisdiction="US-AR",
    )
    pm_defs = [d for d in result["created_definitions"] if "Participating manufacturer" in d["terms"]]
    assert len(pm_defs) == 1, (
        f"expected the persist-layer (article_id, sorted(terms)) dedup key to collapse two "
        f"identical-term-tuple candidates into one Definition row; got {len(pm_defs)}: {pm_defs!r}"
    )
