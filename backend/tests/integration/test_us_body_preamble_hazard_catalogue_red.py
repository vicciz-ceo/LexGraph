"""Mandatory false-positive guard matrix for US family 2 (sprint
2026-08-04-defs-us-preamble, gates U1/U4/U5), assembled from scout S3's
hazard catalogue (H1-H4) plus S1's own genuine AL hazards and S4's SD
finding -- consolidated here because a single trigger-anchored candidate
rule (B1: "As used in this/For purposes of this <unit> ... the term")
would reach ALL of these real rows' bodies, and each represents a
DIFFERENT way that trigger phrase can appear WITHOUT the body actually
introducing a new local definition.

Like `test_us_body_preamble_negative_guard.py` and this sprint's QA
forwarding-reference addition, every test here is GREEN TODAY (nothing
captures ANY US body-preamble row yet) and must STAY GREEN once a
`BodyPreambleRule` ships -- that persistence is what each test pins, not
today's trivial pass.

Two rows below (`STATE_CO_T15_A11_P7_S15-11-701`, `STATE_MT_T7_C14_P41_
S7-14-4103`) are SHARPER than a simple "nothing is captured today"
guard: both are confirmed LIVE, calling the real, unedited
`extract_definitions_from_section`, to already produce a real,
non-empty, WRONG candidate today when called directly on the body text --
i.e. if a future rule's own extraction step is ever pointed at these
bodies without a defensive check for the forwarding-reference shape, it
would create a spurious pointer-only Definition RIGHT NOW, not
hypothetically. This mirrors QA's own `STATE_MS_T17_C2_S25-34` finding
(`test_us_body_preamble_negative_guard_qa_forwarding_reference.py`) on two
NEW real rows from two states never covered by that guard.

Hazard classes covered (scout S3 naming):

- **H1 -- pure forwarding/cross-reference** (CO, MT): `"the term X" has/
  shall be as defined in <citation>[; except: ...]"` -- the definition
  lives in ANOTHER section; nothing local to capture.
- **H1, AL's own recurring cluster** (S1 finding): `"all words and phrases
  defined in Section 36-27-1 shall have the same meanings ascribed to
  them"` -- a whole-section forwarding reference, one of a 4-row recurring
  AL Title 36 Chapter 27 cluster (S1 confirmed all 4 forward to the same
  "mother" section).
- **H3 -- forwarded single term with a colon-introduced EXCEPTION list**
  (CO, IN): looks exactly like a B1 colon-list BLOCK (colon + numbered
  list) but the list items are exceptions/carve-outs to ONE forwarded
  term, not separate defined terms. S3's own colon-after-trigger
  heuristic misfired on this shape by hand-check -- this is the sharpest,
  most realistic false-BLOCK-signal case in the whole catalogue.
- **SD's "does not impair" shape** (S4 finding): the trigger phrase's own
  sentence never actually defines the term at all -- it only asserts what
  the term does NOT do to something else.
- **DC's exclusion-only clause** (S2 finding): `"the term X shall not
  include Y"` where X is defined ELSEWHERE, not here.

Every row is real, fetched live from its own state's real parquet file
(never downloaded by this test), vendored byte-for-byte into `fixtures/
us_statutes/us_preamble_hazard_rows.json`.

No test in this file reads or downloads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _row(act_id: str) -> dict:
    data = json.loads((FIXTURES / "us_preamble_hazard_rows.json").read_text(encoding="utf-8"))
    return data[act_id]


HAZARD_CASES = [
    pytest.param(
        "US-CO",
        "STATE_CO_T15_A11_P7_S15-11-701",
        id="co-h1-h3-forwarding-with-exception-colon-list",
    ),
    pytest.param(
        "US-MT",
        "STATE_MT_T7_C14_P41_S7-14-4103",
        id="mt-h1-forwarding-with-exception",
    ),
    pytest.param(
        "US-AL",
        "STATE_AL_T36_C27_S36-27-48",
        id="al-h1-whole-section-forwarding-cluster",
    ),
    pytest.param(
        "US-IN",
        "STATE_IN_T27_A1_C4.1_S27-1-4.1-4",
        id="in-h3-forwarded-term-exception-colon-list",
    ),
    pytest.param(
        "US-SD",
        "STATE_SD_T36_C21A_S36-21A-68",
        id="sd-does-not-impair-never-defines",
    ),
    pytest.param(
        "US-DC",
        "STATE_DC_T31_C11A_S31-1131.04",
        id="dc-exclusion-only-term-defined-elsewhere",
    ),
]


@pytest.mark.parametrize("jurisdiction, act_id", HAZARD_CASES)
def test_hazard_row_produces_no_definitions(db_session, matter_with_users, jurisdiction, act_id):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _row(act_id)

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=f"{jurisdiction} hazard catalogue (test)",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    assert result["created_definitions"] == [], (
        f"{act_id} must produce ZERO Definitions -- it matches a "
        "trigger-anchored candidate rule's own regex (a plausible "
        "BodyPreambleRule genuinely reaches this body) but defines "
        "nothing locally (forwarding reference / exception list / "
        "exclusion-only clause), the same hazard class as this sprint's "
        "other negative guards"
    )


def test_colorado_row_already_produces_a_real_spurious_candidate_from_the_unedited_live_extractor():
    """Sharper than 'nothing is captured today': calling the REAL, unedited
    `extract_definitions_from_section` directly on this real CO body
    (bypassing heading/gate logic entirely) already produces a non-empty,
    WRONG candidate -- 'Governing instrument' -> 'shall not include a deed
    that transfers...', a spurious EXCEPTION masquerading as a definition.
    A future rule that recognizes this row's preamble and hands its body to
    the existing extractor unmodified WOULD create this spurious Definition
    -- confirmed live, not hypothetical. This is exactly S3's H3 hazard
    class (colon-introduced exception list, not a term list).
    """
    from app.definition_links.us_profile import extract_definitions_from_section

    row = _row("STATE_CO_T15_A11_P7_S15-11-701")
    candidates = extract_definitions_from_section(row["text"], scope="law-wide")
    terms = {c.terms for c in candidates}
    assert ("Governing instrument",) in terms, (
        "expected the real extractor to already produce a spurious "
        "'Governing instrument' candidate from this exact body -- if this "
        "fails, re-verify the hazard framing above against the extractor's "
        "current behavior before reusing this row as evidence"
    )


def test_montana_row_already_produces_a_real_spurious_forwarding_candidate_from_the_unedited_live_extractor():
    """Same class as the Colorado pin above, different extractor path:
    `_extract_inline_quoted_definitions` (the CA/IL/GA/OK/SC/VA fallback,
    see the B1 matrix file) already produces a non-empty, WRONG candidate
    for this real MT body -- 'motor vehicles' -> 'has the meaning provided
    in 61-1-101 , except the term does not include...', a pure
    forwarding-reference pointer, not a local definition. Confirmed live.
    """
    from app.definition_links.us_profile import _extract_inline_quoted_definitions

    row = _row("STATE_MT_T7_C14_P41_S7-14-4103")
    candidates = _extract_inline_quoted_definitions(row["text"], scope="law-wide")
    terms = {c.terms for c in candidates}
    assert ("motor vehicles",) in terms, (
        "expected the real inline-quote extractor to already produce a "
        "spurious 'motor vehicles' forwarding-pointer candidate from this "
        "exact body -- if this fails, re-verify the hazard framing above "
        "before reusing this row as evidence"
    )
