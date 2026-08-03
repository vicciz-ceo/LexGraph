"""RED integration tests -- sprint 2026-08-04-defs-us-markers, planner
pass 2, priority 3.

Six real, named sub-cases confirmed live this pass to be family-3 misses
that wave 1's mechanism (the `_extract_inline_quoted_definitions`
gate-removal, pipeline.py:246-289/405-432) does NOT rescue -- each needs
its OWN bespoke rule, not yet implemented. Highest corpus impact first
(sprint contract's `## Next Steps`, this pass's log `## P2`):

- **AL** (highest value here): 1,603/1,653 = 97.0% of AL's Definitions-
  headed sections are zero-candidate, full corpus (pass 1, re-confirmed
  this pass) -- unquoted ALL-CAPS terms (`(1) ORGAN. ... (2) ATTENDING
  PHYSICIAN. ...`), no quotes anywhere, so NEITHER extraction path can
  see a term boundary at all.
- **DC** unquoted-term shape: zero quote characters, the term is the
  grammatical SUBJECT of a `"A <term>, ..., means ..."` /
  `"An <term> means ..."` sentence -- a wholly different, harder
  extraction problem than AL's numbered-marker shape.
- **RI/AK** mojibake curly quotes: `\\x80\\x9c`/`\\x80\\x9d` (RI) and
  `\\x93`/`\\x94` (AK) -- confirmed this pass to be TWO DIFFERENT byte
  sequences, not one shared mojibake shape as the contract's wording
  implied ("mojibake curly quotes... AK, RI"). Neither is recognized as
  a quote character by either extraction path. AK's full-corpus rate
  (measured this pass, not previously stated in the contract): 766/767
  (99.9%) of AK's Definitions-headed sections are zero-candidate -- a
  materially larger, previously-unmeasured corpus impact than RI's
  already-known 15%.
- **TN** colon-then-list: idiom is "Has the same meaning as interpreted
  by...", which `_MEANS_IDIOM_GAP_RE`'s literal `has the meaning` never
  matches (the interposed "same...as interpreted by" breaks the bounded
  gap match). Confirmed NOT rescued by wave 1 (pass 1's own finding,
  re-confirmed here).
- **SC** bare-`(N)` boundary noise: SC IS reachable via the CURRENT
  (unmodified) `_extract_inline_quoted_definitions` once the gate is
  removed (bare `(N)` markers precede quoted terms, same mechanism as
  VA/WA/FED) -- but not CLEANLY: "Municipality"'s captured text ends
  with the literal next entry's `"(2)"` marker fragment (contract's own
  named defect), and this pass additionally found "Publicly-owned
  property" swallows a trailing "Effect of Amendment" commentary
  annotation (a FED-editorial-notes-shaped hazard, not previously
  recorded for SC). Both need wave 3's marker-splitter fix; SC therefore
  stays RED even after wave 1 lands.

Every test here defines the REQUIRED final behavior (real terms, real
definition boundaries, determined by reading the real row -- no code path
today can produce these, so ground truth is established by inspection,
the same discipline a spec/contract test always requires when no
implementation exists yet) and is proven RED against TODAY's real
production pipeline (`ingest_us_statute_rows` -> `run_definition_linking`,
imported unmodified, same live path as wave 1's own tests).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_wave2_subcases_rows.json"
)

DEGENERATE_THRESHOLD = 10  # chars; matches wave1's own fixture's justification


def _load_rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _ingest_and_link(
    db_session, matter, *, jurisdiction: str, title: str, row: dict
) -> list[Definition]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter["repository_id"],
        matter_id=matter["matter_id"],
        title=title,
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session, matter_id=matter["matter_id"], triggered_by_user_id=matter["contributor_id"]
    )
    return [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]


def test_all_six_subcase_fixture_headings_are_recognized_as_definitions_sections():
    """Sanity, mirroring wave 1's own sanity test: every one of these
    six rows already has a recognized Definitions heading -- the miss is
    purely in extraction, not detection."""
    rows = _load_rows()
    for act_id in (
        "STATE_AL_T1_C19_S22-19-141",
        "STATE_DC_T28_C25_S28-2501",
        "STATE_RI_T35_C35-13_S35-13-2",
        "STATE_AK_T44_C44.42_S44.42.900",
        "STATE_TN_T50_C2_S50-2-115",
        "STATE_SC_T5_C1_S5-1-20",
    ):
        heading = rows[act_id]["section_title"]
        assert is_definitions_heading(heading) is True, (
            f"{act_id}: {heading!r} must already be recognized as a Definitions heading"
        )


def test_real_pipeline_recovers_al_unquoted_allcaps_definitions(db_session, matter_with_users):
    """`STATE_AL_T1_C19_S22-19-141` -- real Alabama organ-donation
    Definitions section. Two unquoted ALL-CAPS terms, each `(N) TERM.
    Definition sentence.` -- no quotes anywhere in the body. This exact
    shape is AL's DOMINANT convention (97.0% of AL's Definitions-headed
    sections zero-candidate, full corpus, this pass)."""
    rows = _load_rows()
    row = rows["STATE_AL_T1_C19_S22-19-141"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-AL", title="AL unquoted allcaps", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"ORGAN", "ATTENDING PHYSICIAN"}, f"got {sorted(by_term)!r}"

    organ = by_term["ORGAN"]
    assert organ.definition_text.strip() == (
        "Organs, tissues, eyes, bones, arteries, blood or other fluids and any "
        "other part or portions of a human body."
    ), f"got {organ.definition_text!r}"

    physician = by_term["ATTENDING PHYSICIAN"]
    assert physician.definition_text.strip() == (
        "The physician selected by, or assigned to, the patient and who has "
        "primary responsibility for the treatment and care of the patient."
    ), f"got {physician.definition_text!r}"


def test_real_pipeline_recovers_dc_unquoted_term_definitions(db_session, matter_with_users):
    """`STATE_DC_T28_C25_S28-2501` -- real DC section. Zero quote
    characters anywhere; each defined term is the grammatical SUBJECT of
    its own sentence (`"A bond, ..., means ..."`, `"An undertaking means
    ..."`) -- a harder, non-marker-anchored extraction problem distinct
    from AL's numbered shape above."""
    rows = _load_rows()
    row = rows["STATE_DC_T28_C25_S28-2501"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-DC", title="DC unquoted term", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"bond", "undertaking"}, f"got {sorted(by_term)!r}"

    bond = by_term["bond"]
    assert "an obligation in a certain sum or penalty" in bond.definition_text
    assert "enforceable by action" in bond.definition_text
    assert "undertaking" not in bond.definition_text.lower(), (
        "bond's definition must not swallow the next entry (undertaking)"
    )

    undertaking = by_term["undertaking"]
    assert "an agreement entered into by a party to a suit" in undertaking.definition_text
    assert len(undertaking.definition_text) >= DEGENERATE_THRESHOLD


def test_real_pipeline_recovers_ri_mojibake_quoted_definitions(db_session, matter_with_users):
    """`STATE_RI_T35_C35-13_S35-13-2` -- real RI registered-public-
    obligations Definitions section, 14 numbered entries, each term
    wrapped in mojibake curly quotes (`\\x80\\x9c`/`\\x80\\x9d` bytes,
    confirmed live: neither extraction path recognizes these as quote
    characters today). Entry 11 ("Public entity") re-mentions the phrase
    "public entity" (mojibake-quoted again) INSIDE its own definition
    prose -- a real trap: exactly 14 terms exist, not 15; a naive
    quote-scanner that doesn't distinguish an entry-opening quote from an
    in-body re-quote would over-count (same defect CLASS as wave 1's WA
    "motor vehicle" phantom-nested-term guard)."""
    rows = _load_rows()
    row = rows["STATE_RI_T35_C35-13_S35-13-2"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-RI", title="RI mojibake quotes", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    expected_terms = {
        "Authorized officer",
        "Certificated registered public obligation",
        "Code",
        "Facsimile seal",
        "Facsimile signature",
        "Financial intermediary",
        "Issuer",
        "Obligation",
        "Official actions",
        "Official or official body",
        "Public entity",
        "Registered public obligations",
        "System of registration",
        "Uncertificated registered public obligation",
    }
    assert set(by_term) == expected_terms, (
        f"expected exactly these 14 real terms (not 15 -- entry 11's own body "
        f"re-mentions \"public entity\" as a quoted PHRASE, not a new entry), "
        f"missing={expected_terms - set(by_term)!r}, unexpected={set(by_term) - expected_terms!r}"
    )
    for term, d in by_term.items():
        assert len(d.definition_text) >= DEGENERATE_THRESHOLD, (
            f"{term!r} definition_text is only {len(d.definition_text)} chars"
        )

    issuer = by_term["Issuer"]
    assert issuer.definition_text.strip().rstrip(".") == (
        "a public entity which issues an obligation"
    ), f"got {issuer.definition_text!r}"

    code = by_term["Code"]
    assert "federal Internal Revenue Code of 1986" in code.definition_text
    assert "Facsimile seal" not in code.definition_text, (
        "Code's definition must not swallow the next entry"
    )


def test_real_pipeline_recovers_ak_mojibake_quoted_definitions_using_a_different_byte_sequence(
    db_session, matter_with_users
):
    """`STATE_AK_T44_C44.42_S44.42.900` -- real Alaska transportation
    Definitions section. Uses `\\x93`/`\\x94` mojibake curly-quote bytes
    -- CONFIRMED DIFFERENT from RI's `\\x80\\x9c`/`\\x80\\x9d` sequence
    (this pass's live finding, not previously recorded) -- so a fix
    covering only RI's byte pair would NOT also cover AK; wave 4's
    `normalize_for_parsing` mojibake table needs both. Only the first
    two entries ("commissioner", "department") are asserted here as an
    exact requirement: entries 3-4 ("transportation" / "transportation
    mode") share ONE clause via "or" (`"transportation" or "transportation
    mode" includes...`) and use the "includes" idiom, not "means" -- both
    wave 4 (mojibake) AND wave 2 (includes-idiom) are needed before they
    can be captured, and their multi-term-shared-clause shape may
    overlap `defs-us-multiterm`'s territory (same overlap class as pass
    1's flagged VT row) -- flagged, not claimed, here."""
    rows = _load_rows()
    row = rows["STATE_AK_T44_C44.42_S44.42.900"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-AK", title="AK mojibake quotes", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert {"commissioner", "department"} <= set(by_term), (
        f"expected at least the 2 unambiguous 'means'-idiom AK terms, got {sorted(by_term)!r}"
    )

    commissioner = by_term["commissioner"]
    assert commissioner.definition_text.strip().rstrip(";") == (
        "the commissioner of transportation and public facilities"
    ), f"got {commissioner.definition_text!r}"

    department = by_term["department"]
    assert department.definition_text.strip().rstrip(";") == (
        "the Department of Transportation and Public Facilities"
    ), f"got {department.definition_text!r}"


def test_real_pipeline_recovers_tn_colon_then_list_work_definition(db_session, matter_with_users):
    """`STATE_TN_T50_C2_S50-2-115` -- real TN wage-and-hour section.
    Single term "work", idiom "Has the same meaning as interpreted by
    the United States supreme court for purposes of..." -- confirmed
    live NOT to match `_MEANS_IDIOM_GAP_RE`'s literal `has the meaning`
    (the interposed "same...as interpreted by" breaks the gap). The raw
    row's `text` field is itself a real, non-injected data-quality quirk
    (the SAME statutory content appears twice, once flowing and once
    line-broken) -- this test only requires the real defining content be
    present and the trailing non-operative amendment-history annotation
    ("Added by 2024 Tenn. Acts...") be excluded, not an exact length (the
    row's own duplication makes byte-exact length assertions fragile and
    not this pass's job to resolve)."""
    rows = _load_rows()
    row = rows["STATE_TN_T50_C2_S50-2-115"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-TN", title="TN colon-then-list", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert "work" in by_term, f"got {sorted(by_term)!r}"

    work = by_term["work"]
    assert "Has the same meaning as interpreted by the United States supreme court" in (
        work.definition_text
    )
    assert "Fair Labor Standards Act" in work.definition_text
    assert "Added by 2024 Tenn. Acts" not in work.definition_text, (
        "definition must not swallow the trailing non-operative amendment-history "
        "annotation"
    )


def test_real_pipeline_recovers_sc_bare_paren_definitions_without_marker_or_amendment_leakage(
    db_session, matter_with_users
):
    """`STATE_SC_T5_C1_S5-1-20` -- the contract's own named SC row.
    Confirmed live: SC IS reachable via the current (unmodified)
    `_extract_inline_quoted_definitions` once wave 1's gate is removed
    (bare `(N)` markers precede quoted terms, same mechanism as
    VA/WA/FED) -- but NOT cleanly. Two real, distinct boundary defects
    on this one row: (a) the contract's own named defect, "Municipality"
    swallowing the literal next entry's `"(2)"` marker fragment; (b) a
    SECOND, previously-unrecorded defect this pass found:
    "Publicly-owned property" swallows a trailing "Effect of Amendment"
    commentary annotation (a FED-editorial-notes-shaped hazard). SC stays
    RED even once wave 1 lands, because wave 3's marker-splitter fix is a
    separate, not-yet-implemented item."""
    rows = _load_rows()
    row = rows["STATE_SC_T5_C1_S5-1-20"]

    definitions = _ingest_and_link(
        db_session, matter_with_users, jurisdiction="US-SC", title="SC bare paren", row=row
    )
    by_term = {t: d for d in definitions for t in d.terms}
    assert set(by_term) == {"Municipality", "Publicly-owned property"}, f"got {sorted(by_term)!r}"

    municipality = by_term["Municipality"]
    assert municipality.definition_text.strip() == (
        "a city or town issued a certificate of incorporation, or township "
        "created by act of the General Assembly."
    ), f"got {municipality.definition_text!r}"
    assert "(2)" not in municipality.definition_text, (
        "Municipality's definition must not leak the next entry's bare marker"
    )

    publicly_owned = by_term["Publicly-owned property"]
    assert publicly_owned.definition_text.strip() == (
        "any federally-owned, state-owned, or county-owned land or water area."
    ), f"got {publicly_owned.definition_text!r}"
    assert "Effect of Amendment" not in publicly_owned.definition_text, (
        "Publicly-owned property's definition must not swallow the trailing "
        "amendment-history commentary"
    )
