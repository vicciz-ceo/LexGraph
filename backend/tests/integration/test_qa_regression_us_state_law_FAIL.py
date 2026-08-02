"""QA bounce evidence — sprint 2026-08-02-us-state-law, QA cycle 2.

These tests are INTENTIONALLY RED. Each proves a real defect that bounces
its item back to `## Next Steps` in the sprint contract. Do not "fix" them
by loosening the assertion -- fix the implementation, then this file goes
green on its own.

Cycle 1's three bounce-proofs (P3, live-path trace, P4) all now PASS against
the wave-3 fixes and have been folded into `test_qa_regression_us_state_law.py`
as ordinary green regression tests (assertions kept intact, only the
docstring framing changed from "RED, proves a bounce" to "green, guards
against a regression"). This file starts fresh for cycle 2's findings.

[QA-FAIL] Item 5 -- US dataset ingester [G6], ruling R7(b):

  1. `test_ingest_us_statute_rows_drops_a_real_row_with_empty_chapter_but_unique_citation`
     (Q2): the wave-3 idempotency fix SKIPS any row whose `chapter` is
     missing/empty, even when `citation` -- the dataset's actual canonical
     unique identifier, non-empty in 0% of real rows -- is present and
     unique. Manager-measured on the REAL `us_de_statutes.parquet`: 647 of
     21,649 rows (3.0%) have an empty `chapter` and would be silently
     dropped; QA independently reproduced this exact percentage against the
     live HuggingFace file during investigation (not part of this committed
     test, per ruling R6). This test proves the drop using a REAL row
     (`STATE_DE_T5_C7_SVIII_S796`, citation `5 Del. C. § 796`) with only
     `chapter` blanked to the real-world empty-string shape.

[QA-FAIL] Item 3 -- US jurisdiction profile [G2], NEW regressions introduced
by the wave-3 heading-tightening fix to `us_profile._DEFINITIONS_HEADING_RE`
(Q3 -- "highest-risk regression in wave 3", probed hard per the QA brief):

  2. `test_is_definitions_heading_hangs_catastrophically_on_a_real_de_heading`
     (Q3a, NEW defect): `_DEFINITIONS_HEADING_RE`'s
     `(?:[^A-Za-z]+|Section\\s+\\d+\\.?)*Definitions?\\b` construct is
     catastrophically backtracking (classic `(X+)*` ReDoS shape) on any
     heading with a long leading run of non-letter characters that does
     NOT end up matching "Definitions". The real DE dataset's own scrape-
     noise prefix (`"§ Â\\r\\n        "`) plus embedded annotation markup
     easily produces such a run: `STATE_DE_T10_C54_S5402`'s real
     `section_title` has a 43-character leading non-letter run (the
     dataset-wide maximum, verified against all 21,649 real DE rows) and
     is confirmed to not return within 8 real wall-clock seconds where the
     PRE-fix unanchored `\\bDefinitions?\\b` substring check (no nested
     quantifier, therefore linear-time) returned instantly. This is a
     regression introduced BY the wave-3 fix, not a pre-existing issue --
     and it sits directly on `pipeline.py` Stage 2's real per-article call
     path (`profile.is_definitions_heading(art.heading)`), so a single
     pathological real heading during the G6 bulk ingest (109 files, ~2M
     rows) would hang the deterministic pipeline indefinitely on that one
     article.

  3. `test_is_definitions_heading_undermatches_a_real_multiterm_definitions_section`
     (Q3b, NEW defect): the tightened regex requires "Definition(s)" to be
     the heading's first word after stripping a leading non-letter run --
     but real DE section identifiers routinely embed a letter INSIDE the
     section number itself (e.g. `4A-103`, `12D-102`, `9002A` -- the
     standard modern DE supplemental-section numbering convention), which
     breaks the "leading non-letter run" assumption the regex relies on to
     skip past the number. `STATE_DE_T6_A4A_P1_S4A-103`'s real heading
     ("Payment order — Definitions.") is a genuine 5-term Definitions
     section (`"Payment order"`, `"Beneficiary"`, `"Beneficiary's bank"`,
     `"Receiving bank"`, `"Sender"`, each `"Term" means ...`) using the
     standard UCC "Topic — Definitions." heading convention (Delaware
     Title 6, Articles 2/2A/3/4/4A/8/9) -- yet it is silently NOT
     recognized. Verified NOT a one-off: of the 973 real DE headings
     containing the word "Definition(s)", 152 (15.6%) are under-matched by
     this exact failure mode. This is the precise risk the QA brief warned
     about: "Under-matching would silently return G2 to 'parses nothing'
     while all tests stay green" -- it is realized here for a
     double-digit-percentage slice of one state's real definitions
     sections, invisibly, with the full suite green.
"""

from __future__ import annotations

import json
import pathlib
import signal
import time

FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes" / "de_sample_rows.json"
)
QA_CYCLE2_FIXTURE_JSON = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "de_qa_cycle2_rows.json"
)


def _load_rows() -> list[dict]:
    return json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))


def _load_qa_cycle2_rows() -> dict[str, dict]:
    rows = json.loads(QA_CYCLE2_FIXTURE_JSON.read_text(encoding="utf-8"))
    return {r["act_id"]: r for r in rows}


# --- Item 5, Q2: real-data row loss on empty chapter (ruling R7(b)) --------


def test_ingest_us_statute_rows_drops_a_real_row_with_empty_chapter_but_unique_citation(
    db_session, matter_with_users
):
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
        title="Delaware Code -- Statutes (QA cycle2 Q2 probe)",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction="US-DE",
    )

    assert result["skipped_rows"] == [], (
        "a real DE row with a valid, unique citation ('5 Del. C. § 796') was "
        f"dropped instead of ingested: {result['skipped_rows']!r}. On the real "
        "us_de_statutes.parquet, 647/21,649 rows (3.0%) share this exact shape "
        "(empty chapter, non-empty unique citation) and would all be lost the "
        "same way -- real law silently dropped, not merely 'explicitly skipped' "
        "in any way a bulk-run report could distinguish from a legitimately "
        "unparseable row"
    )
    assert len(result["article_ids"]) == 1, "the row must persist as a real Article"


# --- Item 3, Q3a: catastrophic backtracking on a real DE heading -----------


def _run_with_deadline(fn, *args, deadline_seconds: int, **kwargs):
    """Run `fn(*args, **kwargs)` but fail fast (instead of hanging the
    suite) if it has not returned within `deadline_seconds` -- same SIGALRM
    hard-wall-clock-deadline pattern already established in this codebase
    for exponential-blowup findings (see `test_validation.py`'s
    `_run_with_deadline`), needed here because a broken implementation can
    run for an unbounded amount of time (confirmed: still not returned after
    8 real wall-clock seconds on the exact real heading used below)."""

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


def test_is_definitions_heading_hangs_catastrophically_on_a_real_de_heading():
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_qa_cycle2_rows()
    heading = rows["STATE_DE_T10_C54_S5402"]["section_title"]
    # Real heading, real 43-char leading non-letter run (scrape noise +
    # embedded case-annotation markup) -- the dataset-wide maximum across
    # all 21,649 real US-DE rows. Not a definitions section at all (it's a
    # legislative "Evans v. State" nullification note), so the regex must
    # walk its entire non-matching prefix before giving up -- this is
    # exactly the shape that triggers catastrophic backtracking.

    result, elapsed = _run_with_deadline(is_definitions_heading, heading, deadline_seconds=3)
    assert result is not None, (
        f"is_definitions_heading did not return within {elapsed:.0f}s on a real "
        f"US-DE heading ({heading!r}) -- catastrophic backtracking in "
        "_DEFINITIONS_HEADING_RE's `(?:[^A-Za-z]+|...)* ` construct. This call "
        "sits directly on pipeline.py Stage 2's real per-article path "
        "(profile.is_definitions_heading(art.heading)); a single real heading "
        "like this one during the G6 bulk ingest (109 files, ~2M rows) would "
        "hang the deterministic pipeline indefinitely"
    )
    assert result is False, "this heading is genuinely not a Definitions section"


# --- Item 3, Q3b: under-match on a real letter-suffixed section number -----


def test_is_definitions_heading_undermatches_a_real_multiterm_definitions_section():
    from app.definition_links.us_profile import is_definitions_heading

    rows = _load_qa_cycle2_rows()
    heading = rows["STATE_DE_T6_A4A_P1_S4A-103"]["section_title"]
    assert heading == "§ Â\r\n        4A-103. Payment order â Definitions."

    assert is_definitions_heading(heading) is True, (
        f"{heading!r} is a real, genuine 5-term Delaware UCC Definitions section "
        "('Payment order', 'Beneficiary', \"Beneficiary's bank\", 'Receiving "
        "bank', 'Sender') using the standard 'Topic — Definitions.' UCC heading "
        "convention -- but is_definitions_heading's 'Definitions must be the "
        "first word' requirement silently misses it because the real section "
        "number ('4A-103') embeds a letter, breaking the leading-non-letter-run "
        "assumption the regex relies on to skip past the number. Not a one-off: "
        "152 of 973 real DE headings containing the word 'Definition(s)' "
        "(15.6%) are under-matched by this exact failure mode -- G2 silently "
        "regresses toward 'parses nothing' for a double-digit-percentage slice "
        "of one state's real definitions sections, with the full suite green"
    )
