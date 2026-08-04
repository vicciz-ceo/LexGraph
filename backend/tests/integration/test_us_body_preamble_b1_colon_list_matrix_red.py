"""RED live-path parameterized capture matrix for US family 2 (sprint
2026-08-04-defs-us-preamble, gates U1/U4/U6), idiom **B1** (scout S3's
naming): `"As used in this <unit>, the term:"` / `"For (the) purposes of
this <unit>, the term:"`, immediately followed by a colon and a numbered
or lettered list of >=2 quoted-or-derivable terms.

**The single biggest simplification available to this sprint** (S3
finding, M-R19): this ONE idiom, plus the existing `(N)`-numbered-block
splitter (`USProfile.extract_definitions_from_section`) and inline-quote
fallback (`pipeline._extract_inline_quoted_definitions`) -- BOTH already
shipped, BOTH unedited by this sprint -- covers essentially the whole
40-state long tail's genuine BLOCK population (~30 real rows across 9
states in S3's own count, out of 803 candidates). A `BodyPreambleRule`
recognizing this ONE trigger shape needs no per-state bespoke regex.

This file proves that claim with REAL rows, one per state, rather than
asserting it in prose: every row below is fetched live from its state's
real parquet file (never downloaded by this test) and vendored byte-for-
byte into `fixtures/us_statutes/us_preamble_b1_rows.json`. Every expected-
terms set below was checked by calling the REAL, unedited
`extract_definitions_from_section` / `_extract_inline_quoted_definitions`
directly against each row's real body text before being written here --
these are the terms the EXISTING extractors already parse correctly once
a `BodyPreambleRule` supplies the heading; nothing about the extraction
layer needs to change for B1 states.

**States NOT included here despite S3 naming them as B1** (GA, KS's own
neighbor RI): GA already has its own dedicated fixture/tests
(`ga_preamble_rows.json` / `test_us_body_preamble_capture_red.py`), so it
is not duplicated. RI's own named example
(`STATE_RI_T42_C42-28_S42-28-3.5`) was checked live and found to use a
REAL, DIFFERENT, currently-unrelated corpus defect: its quote characters
are stored as a mangled byte sequence (`\\x80\\x9c`/`\\x80\\x9d`, distinct
from the already-documented DE-style `Â` mojibake in this fixtures
directory's own README), so NEITHER extractor recognizes any term in it at
all -- 0 candidates, confirmed live. This is a genuine, new, real
data-quality finding (not fabricated, not silently dropped -- flagged in
this sprint's log for whoever owns corpus ingestion next), but it means
that specific row cannot serve as an "achievable capture" example the way
the other 9 states' rows can, so RI is intentionally left out of this
capture matrix rather than asserting something the real corpus data cannot
support today. SC/VA/OK/IL below cover the fallback-path variant (their
primary extractor returns nothing, so the inline-quote fallback -- already
shipped for CA/IL/GA -- is what actually produces the achievable terms;
each is called out per-row below).

No test in this file reads or downloads the parquet snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _rows() -> dict[str, dict]:
    return json.loads((FIXTURES / "us_preamble_b1_rows.json").read_text(encoding="utf-8"))


# (jurisdiction, act_id, expected_terms_subset, extractor_note)
# `expected_terms_subset` is intentionally a SUBSET of what each real row's
# body actually defines, not an exact set -- see each row's own comment for
# what was deliberately left out and why (a known, separately-tracked
# extractor gap, never silently smoothed over).
B1_CASES = [
    pytest.param(
        "US-DE",
        "STATE_DE_T8_C1_SXVII_S390",
        {"Foreign jurisdiction", "Resulting entity"},
        id="de-corporations-transfer",
    ),
    pytest.param(
        "US-ID",
        "STATE_ID_T28_C51_S28-51-103",
        {"Cardholder", "Merchant", "Payment card"},
        id="id-payment-card-receipts",
    ),
    pytest.param(
        "US-KS",
        "STATE_KS_C50_A6_S50-6,114",
        # KS's real body also defines "vehicle protection product warranty"
        # (extract_definitions_from_section's own real output for that
        # entry) -- left out of the asserted subset only because its exact
        # returned casing is corpus-quirky, not because it fails to
        # extract; this subset is the SAFE, unambiguous part.
        {"Vehicle protection product", "incidental costs", "warrantor"},
        id="ks-vehicle-protection-products",
    ),
    pytest.param(
        "US-LA",
        "STATE_LA_Crevised-statutes_T47_S53.1",
        # LA's own preamble sentence itself defines "Bad debt" BEFORE the
        # "(1)"-numbered list starts -- `extract_definitions_from_section`
        # only recognizes the numbered block, so "Bad debt" is a REAL,
        # confirmed-live miss (not asserted here; the inline fallback is
        # never tried since the primary extractor already returns 3 real
        # candidates). This is a pre-existing extractor limitation the
        # rule inherits, not something this sprint's file can fix without
        # editing `us_profile.py` (out of bounds for this sprint).
        {"Prior tax", "Delinquency amount", "Recovery exclusion"},
        id="la-bad-debt-recovery",
    ),
    pytest.param(
        "US-OK",
        "STATE_OK_T63_S63-1-727",
        # OK's body has NO "(N)"-numbered markers at the start of each
        # entry in the shape extract_definitions_from_section requires
        # (verified live: 0 candidates from that extractor) -- the
        # inline-quote fallback is what actually produces these 4 terms,
        # the same fallback mechanism already shipped for CA/IL/GA.
        {"Human cloning", "Somatic cell", "Nucleus", "Oocyte"},
        id="ok-human-cloning-fallback-path",
    ),
    pytest.param(
        "US-SC",
        "STATE_SC_T12_C54_S12-54-122",
        # Same fallback-path shape as OK -- extract_definitions_from_
        # section returns 0 (no adjacent-quote numbered markers), the
        # inline fallback produces the real terms.
        {"Security interest", "Motor vehicle", "Purchaser"},
        id="sc-tax-lien-fallback-path",
    ),
    pytest.param(
        "US-VA",
        "STATE_VA_T8.01_C1_S8.01-2",
        # Same fallback-path shape; VA's own heading ("General definitions
        # for this title") is itself a real, near-miss English heading --
        # NOT recognized by `is_definitions_heading` today (verified live
        # below) because it never contains the literal word
        # "Definition(s)".
        {"Rendition of a judgment", "receivership court", "bill in equity"},
        id="va-title-scoped-fallback-path",
    ),
    pytest.param(
        "US-WV",
        "STATE_WV_C27_A5_S2A",
        # WV's own row is a MIXED shape (S3 finding): entry 1
        # ("Addiction") is itself a forwarding reference to another
        # section ("has the same meaning as the term is defined in
        # §27-1-11"), entries 2+ are genuinely local. Deliberately NOT
        # asserting "Addiction" here -- whether a mixed BLOCK's own
        # forwarding-shaped first entry should be captured at all is a
        # precision question for the rule to resolve, not something to
        # bake into this simple achievable-subset pin.
        {"Authorized staff physician", "Hospital", "Psychiatric emergency"},
        id="wv-mixed-forwarding-and-local",
    ),
    pytest.param(
        "US-IL",
        "STATE_IL_C765_A835_S.01",
        # IL's "no-marker inline-quote" variant of B1 (S3's own §3 note):
        # no numeric/letter markers at all, a pure inline quote run --
        # this is literally family-3's existing shape (already-shipped
        # CA/IL/GA fallback), confirming it recurs even under B1's own
        # preamble wording. extract_definitions_from_section returns 0
        # (no markers); the inline fallback produces these terms.
        {"Cemetery authority", "Community mausoleum", "Veteran"},
        id="il-cemetery-authority-no-marker-variant",
    ),
]


@pytest.mark.parametrize("jurisdiction, act_id, expected_terms, ", B1_CASES)
def test_b1_colon_list_preamble_is_captured(
    db_session, matter_with_users, jurisdiction, act_id, expected_terms
):
    from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
    from app.definition_links.pipeline import run_definition_linking

    m = matter_with_users
    row = _rows()[act_id]

    ingest_us_statute_rows(
        db_session,
        repository_id=m["repository_id"],
        matter_id=m["matter_id"],
        title=f"{jurisdiction} B1 colon-list matrix (test)",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=m["matter_id"], triggered_by_user_id=m["contributor_id"]
    )

    created_terms = {t for d in result["created_definitions"] for t in d["terms"]}
    assert expected_terms <= created_terms, (
        f"the real production pipeline recognized ZERO of {act_id}'s real "
        f"'As used in/For purposes of this <unit>, the term:' definitions "
        f"(expected {sorted(expected_terms)}, got {sorted(created_terms)}) -- "
        "this is idiom B1 (scout S3), the single shared shape covering "
        "essentially the whole 40-state long tail's genuine BLOCK "
        "population; a BodyPreambleRule recognizing it needs no per-state "
        "bespoke regex"
    )


def test_va_general_definitions_for_this_title_heading_is_a_genuine_near_miss_not_recognized_today():
    """Unit-level pin: VA's real heading ('General definitions for this
    title') is a genuine, informative, human-readable heading that a naive
    reader would call a Definitions heading -- but it is NOT recognized by
    today's `is_definitions_heading` (which requires the literal word
    "Definition(s)"), and it is NOT a placeholder either (so today's wave-6
    gate never even tries body derivation for it). Documents precisely why
    VA's row above needs an ungated body-preamble rule, not a heading-regex
    widening -- the heading itself carries real words, just not the
    specific word the matcher looks for.
    """
    from app.definition_links.us_profile import _is_placeholder_heading, is_definitions_heading

    rows = _rows()
    row = rows["STATE_VA_T8.01_C1_S8.01-2"]

    assert row["section_title"] == "General definitions for this title"
    assert is_definitions_heading(row["section_title"]) is False
    assert _is_placeholder_heading(row["section_title"]) is False
