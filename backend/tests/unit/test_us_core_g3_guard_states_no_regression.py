"""Non-regression guard -- sprint 2026-08-05-defs-core-follow-on-2, gate G3
("FED unbounded-last-entry").

**Why this file exists.** `_split_into_numbered_blocks`'s baseline splitter
runs BEFORE any registered rule and unconditionally for EVERY US
jurisdiction (`extract_definitions_from_section` / `USProfile.extract_
definitions_from_section` both call it directly) -- so G3's fix changes
behavior for every US-* jurisdiction, not just FED/DC. Per this sprint's
brief (design caution #2): "Non-regression evidence must cover the
working-baseline guard states: IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK." This
file pins TODAY's real, already-correct extraction output for one real
multi-entry Definitions row per guard state, so the Developer's boundary
fix must reproduce it byte-for-byte -- if any of these 12 assertions goes
red once the fix lands, that is evidence the fix over-corrected (cut a
genuine entry short), not evidence of an unrelated regression elsewhere.

**How the 12 rows were chosen.** For each guard state, scanned every real
`is_definitions_heading`-True row in that state's `us_<xx>_statutes.parquet`
file (real corpus, snapshot `301000fc3465374ee0f23c3c6953a8a861e95cad`),
kept only rows where baseline already extracts >=2 candidates (so the
"last entry" is a genuine LAST of several, not a degenerate single-entry
case) AND the last entry's `definition_text` contains none of the 10
independently-confirmed trailing-commentary markers this sprint's G3 RED
test and its own corpus sample turned up ("Editorial Notes", "Amendments",
"Statutory Notes", "References in Text", "Congressional Findings",
"Pub. L.", "History:", "Amended by Act", "Source:", "Cited."), then took
the FIRST such row found. This is a "today's baseline is already right
here" selection, not a claim that these 12 rows are free of every OTHER
extraction defect (MI's pinned text below in fact shows a DIFFERENT,
unrelated marker-format issue -- see its own comment) -- the guard only
asserts G3's specific fix does not perturb them.

**Live path.** Each row is fed to `extract_definitions_from_section`
(the same bare production function `USProfile.extract_definitions_from_
section` and `pipeline.py` both build on) -- the module-level function is
used directly here (unit-level, no registry rules are registered for any
of these 12 states/rows on this branch, so it is behaviorally identical to
going through `USProfile` for these specific inputs; verified while
building this fixture). All 12 fixture rows are vendored verbatim (real
`text`/`section_title`/`act_id`, byte-for-byte) in `backend/tests/
fixtures/us_statutes/g3_guard_states_rows.json`. The already-shipped M14
newline-unescape (`ingest_us_statutes.py:237`, a no-op for every state here
except NY) is reproduced inline before extraction, matching what
production actually feeds this function.

**Currently GREEN, must STAY green.** Unlike this gate's RED test, every
assertion below passes on today's code -- that is the point of a
non-regression guard (pin known-good behavior before the fix, not after).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.us_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "g3_guard_states_rows.json"
)

# Pinned TODAY (this sprint pass), against the real corpus rows named
# below -- one per working-baseline guard state named in the sprint brief.
# `last_definition_text` is MI's real ` ( l ) "Sibling" ...` continuation
# noted in-line below: that specific pin is NOT a G3 boundary-marker case
# (none of the 10 known trailing-notes markers appear in it) -- it is a
# SEPARATE, out-of-this-gate's-scope marker-recognition gap
# (`_MARKER_TOKEN_RE` requires `\(\w+\)` with NO internal space, and
# MI's real convention is spaced, `"( l )"` not `"(l)"`) flagged in this
# sprint's report, not fixed here -- pinned as-is so G3's narrower fix does
# not accidentally perturb it either way.
PINNED = [
    {
        "state": 'IN',
        "act_id": 'STATE_IN_T6_A9_C56_S6-9-56-2',
        "count": 2,
        "last_term": ('Gross retail income',),
        "last_definition_text": 'and "person" have the same meanings that are prescribed by IC 6-2.5-1.\n\nAs added by P.L.236-2023, SEC.121.',
    },
    {
        "state": 'CO',
        "act_id": 'STATE_CO_T10_A19_S10-19-103',
        "count": 8,
        "last_term": ('Qualified long-term care insurance contract',),
        "last_definition_text": 'or "federally tax-qualified long-term care insurance contract" also means the portion of a life insurance contract that provides long-term care insurance coverage by rider or as part of the contract and that satisfies the requirements of 26 U.S.C. sec. 7702B (b) and (e) of the federal "Internal Revenue Code of 1986", as amended.',
    },
    {
        "state": 'KY',
        "act_id": 'STATE_KY_TIX_C67C_S67C.301',
        "count": 5,
        "last_term": ('Officer',),
        "last_definition_text": 'means any member of the consolidated local government police forces\n\naffected by KRS 67C.301 to 67C.327, including police officers, corporals,\n\nsergeants, lieutenants, and captains.',
    },
    {
        "state": 'LA',
        "act_id": 'STATE_LA_Crevised-statutes_T11_S952.1',
        "count": 20,
        "last_term": ('University Retirement System',),
        "last_definition_text": 'or "funded system" means the funded Louisiana State University and Agricultural and Mechanical College Retirement System as defined in R.S. 11:952.2.',
    },
    {
        "state": 'DE',
        "act_id": 'STATE_DE_T30_C20_SIV_S2032',
        "count": 9,
        "last_term": ('The Secretary',),
        "last_definition_text": 'shall mean the Secretary of the Department of Transportation or the Secretary’s duly appointed delegate.',
    },
    {
        "state": 'ID',
        "act_id": 'STATE_ID_T33_C1_S33-133',
        "count": 14,
        "last_term": ('Violation',),
        "last_definition_text": 'means an act contrary to the provisions of this section that materially compromises the security, confidentiality or integrity of personally identifiable data of one (1) or more students and that results in the unauthorized release or disclosure of such data.',
    },
    {
        "state": 'NJ',
        "act_id": 'STATE_NJ_T58_C22_S22-3',
        "count": 11,
        "last_term": ('Water supply facility',),
        "last_definition_text": 'or "facility" means and refers to the real property and the plans, structures, machinery and equipment and other property, real, personal and mixed, acquired, constructed or operated, or to be acquired, constructed or operated by or on behalf of the State, for the purpose of augmenting the natural water resources of the State and making available an increased supply of water for all uses, and any and all appurtenances necessary, useful or convenient for the collection, storage, control, sale or exchange of water, and to preserve and protect these resources and facilities and provide for the conservation and development of future water supply sources, and to facilitate incidental recreational uses of either of them.\nL.1958, c. 34, p. 97, s. 3.',
    },
    {
        "state": 'MI',
        "act_id": 'STATE_MI_C701_AAct-288-of-1939_S712A.13a',
        "count": 11,
        "last_term": ('Sex offenders registration act',),
        "last_definition_text": 'means the sex offenders registration act, 1994 PA 295, MCL 28.721 to 28.730.\n\n( l ) "Sibling" means a child who is related through birth or adoption by at least 1 common parent. Sibling includes that term as defined by an American Indian or Alaskan native child\'s tribal code or custom.',
    },
    {
        "state": 'MT',
        "act_id": 'STATE_MT_T61_C1_P1_S61-1-101',
        "count": 94,
        "last_term": ('Wholesaler',),
        "last_definition_text": 'means a person that for a commission or with intent to make a profit or gain of money or other thing of value sells, exchanges, or attempts to negotiate a sale or exchange of an interest in a used motor vehicle, trailer, semitrailer, pole trailer, travel trailer, motorboat, snowmobile, off-highway vehicle, or special mobile equipment only to dealers and auto auctions licensed under chapter 4, part 1.',
    },
    {
        "state": 'ND',
        "act_id": 'STATE_ND_T51_C51-19_S51-19-02',
        "count": 2,
        "last_term": ('Offer to purchase',),
        "last_definition_text": 'includes every attempt to offer to acquire, or solicitation\n\nof an offer to sell, a franchise or interest in a franchise for value.\n\nb. (1) An offer or sale of a franchise is made in this state when an offer to sell is\n\nmade in this state or an offer to buy is accepted in this state, or, if the\n\nfranchisee is domiciled in this state, the franchised business is or will be\n\noperated in this state.',
    },
    {
        "state": 'NY',
        "act_id": 'STATE_NY_APBA_A8_T18_S2432',
        "count": 27,
        "last_term": ('Local public safety communications bonds',),
        "last_definition_text": '. A municipal bond\nissued to finance or fund all or a portion of the costs of building\nregional, interoperable public communications networks for statewide use\nby first-responder agencies in the state, including equipment and\nincidental costs. Local public safety communication bonds may also be\nissued to refinance outstanding bonds issued by municipalities for the\npurposes described herein provided that present value savings are\nrealized from such a refunding.',
    },
    {
        "state": 'OK',
        "act_id": 'STATE_OK_T15_S15-32',
        "count": 3,
        "last_term": ('educational loan',),
        "last_definition_text": "means a loan or assistance for the\n\npurpose of directly furthering the obligor's education at an\n\neducational institution.",
    },
]


@pytest.fixture(scope="module")
def guard_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {r["state"]: r for r in rows}


@pytest.mark.parametrize("expected", PINNED, ids=[p["state"] for p in PINNED])
def test_guard_state_last_entry_capture_is_unperturbed(guard_rows, expected):
    row = guard_rows[expected["state"]]
    assert row["act_id"] == expected["act_id"]

    # M14/I8 (already-shipped, `ingest_us_statutes.py:237`): production
    # unescapes a literal `\n` two-character sequence to a real newline
    # BEFORE `extract_definitions_from_section` ever sees the body -- a
    # no-op for every state here except NY, whose real `text` column
    # stores line breaks exactly this way (verified corpus-wide,
    # 40,102/40,102 rows). Reproduced here since this test calls the bare
    # extraction function directly rather than going through
    # `ingest_us_statute_rows`; omitting it would make NY's guard row
    # exercise a pre-ingest, not-actually-live shape.
    text = row["text"].replace("\\n", "\n")
    candidates = extract_definitions_from_section(text, scope="law-wide")

    assert len(candidates) == expected["count"], (
        f"{expected['state']} ({expected['act_id']}): candidate COUNT "
        f"changed -- got {len(candidates)}, pinned {expected['count']}. "
        "G3's fix must only affect the LAST entry's definition_text length, "
        "never how many entries are recognized."
    )

    last = candidates[-1]
    assert last.terms == expected["last_term"], (
        f"{expected['state']} ({expected['act_id']}): last entry's TERM "
        f"changed -- got {last.terms!r}, pinned {expected['last_term']!r}"
    )
    assert last.definition_text == expected["last_definition_text"], (
        f"{expected['state']} ({expected['act_id']}): last entry's "
        f"definition_text changed -- got "
        f"{len(last.definition_text)} chars, pinned "
        f"{len(expected['last_definition_text'])} chars. This is the "
        "over-correction failure mode design caution #1 warns about: a "
        "genuine long/continuing final entry cut short."
    )
