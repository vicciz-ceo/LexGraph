"""RED (sprint 2026-08-20-defs-boundary-idioms, pass 2 amendment, Item 2) --
representative real losses caused by the fallback-suppression guard
(`backend/app/definition_links/us_profile.py::USProfile.
extract_definitions_from_section`, ~line 2551):

    if not candidates and heading_was_derived:
        candidates = _extract_inline_quoted_definitions(text, scope=scope)

`candidates` is the union of baseline's own numbered-block splitter plus
every registered `EntrySplitterRule`'s contribution (the "primary engine").
`_extract_inline_quoted_definitions` (the "fallback") is a SEPARATE, much
broader scan with its own idiom regex (already recognizes bare `includes`)
and NO trailing-stop cutoff. The guard is all-or-nothing PER ROW: the
fallback runs only when the primary engine finds ZERO entries. Once Item
1's widened `_TIGHT_IDIOM_RE` makes the primary engine recognize even ONE
entry on a row, the guard flips and the fallback never runs -- silently
discarding every OTHER term only the fallback could reach, even though the
widening did nothing to fix how those other terms are recognized. Full
evidence: `docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts/
investigation.md`, Q1 (134-row table, 130 genuine losses).

Item 2's spec'd fix (Developer implements; see the sprint contract's Item 2
Next Steps entry for the precise design): merge, don't suppress -- ALWAYS
run the fallback when `heading_was_derived`, and admit a fallback
candidate only when its own term does not collide with any primary-engine
term on that row (per-term, not per-row, suppression), further filtered by
a narrow, evidence-derived "implausible capture" rejection (see the
companion `test_us_markers_fallback_guard_phantom_negative_control.py`).

Every row below is byte-verified against the real corpus this pass
(`vaquill/open-us-law`, snapshot pinned in investigation.md); fixtures are
vendored verbatim (act_id/section_title/chapter/section_number unchanged).
Expected recovery texts were originally the fallback function's OWN
existing (bleeding) output, on the premise that `_extract_inline_quoted_
definitions`'s internals were out of bounds per the amended gate 7 --
investigation.md documented these bleed tails as GENUINE LOSSES regardless
of byte quality (the core definitional content is real and completely
absent today, not merely re-bounded).

**Re-pointed 2026-08-23 (sprint 2026-08-23-defs-debt-31, Item 1, mandatory
stale-pin sweep)**: THIS sprint's own gate 8 explicitly widens the seam to
include `_extract_inline_quoted_definitions`'s internals (needed for Item
1's trim-not-drop fix). Five of this file's exact-match assertions baked
in the very bleed tails Item 1 targets as required substrings (FED
'Pre-Apprenticeship' swallowing the next entry's own "(c) The term"
lead-in; WA 'convicted' swallowing a dangling "For the purposes of this
section," list-introducer stub; OH 'Derivative transaction' swallowing
the next entry's own " (2)" marker; NY 'Bakery basket'/'Dairy case' each
swallowing the next lettered entry's own "\\n  b."/"\\n  e." marker+quote
start) -- a GREEN test pinning exactly the pre-fix broken bytes this same
sprint's Item 1 is meant to correct. Re-pointed to each term's TRUE,
correctly-bounded text (verified against the same vendored real rows);
this file is now ALSO Item 1 RED-test coverage on already-vendored real
fixtures, not just the original Item 2 (issue #27) recovery target."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "us_statutes"


def _load_row(fname: str) -> dict:
    rows = json.loads((FIXTURES / fname).read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def _run(db_session, matter_with_users, row: dict, jurisdiction: str) -> dict[str, list]:
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{row['act_id']} fallback-guard recovery (issue #27 pass 2, Item 2)",
        rows=[row],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d)
    return by_term


def test_red_fed_12889_recovers_seven_executive_order_terms_without_losing_state(
    db_session, matter_with_users
):
    """`USC_T29_C4C_S50` (FED row 12889). Primary engine already correctly
    recognizes 'State' -> 'the District of Columbia.' today (post-Item-1;
    this is a regression pin, must stay unchanged). The other 7 terms,
    quoted inside an Executive Order embedded in the section's own body,
    are ONLY reachable through the fallback -- today entirely absent."""
    row = _load_row("us_markers_fallback_guard_fed_12889_row.json")
    by_term = _run(db_session, matter_with_users, row, "US-FED")

    state_texts = [d.definition_text.strip() for d in by_term.get("State", [])]
    assert "the District of Columbia." in state_texts, (
        f"'State' regression: primary-engine capture must stay unchanged, got {state_texts!r}"
    )

    expected_prefixes = {
        "Registered Apprenticeship": "an industry-driven career pathway",
        "Pre-Apprenticeship": "set forth in 29 CFR 30.2.",
        "Labor-Management Forum": "a nonadversarial forum for managers",
        "agencies": "the Department of State, the Department of the Treasury",
        "participating agencies": "agencies led by the heads of agencies",
        "interested agencies": "agencies as defined in subsection (d)",
        "Labor-Management Forum agencies": "all agencies subject to chapter 71",
    }
    missing = sorted(t for t in expected_prefixes if t not in by_term)
    assert not missing, (
        f"lost fallback-only terms never captured by any path today: {missing!r}. "
        f"Got terms: {sorted(by_term)!r}"
    )
    for term, prefix in expected_prefixes.items():
        texts = [d.definition_text for d in by_term[term]]
        assert any(t.startswith(prefix) for t in texts), (
            f"{term!r} captured but not with the expected fallback text (prefix "
            f"{prefix!r}): got {texts!r}"
        )
    # Exact-text pin for the two short ones (content-fidelity spot check).
    # Re-pointed (sprint 2026-08-23-defs-debt-31, Item 1 stale-pin sweep):
    # the true definition ends at "29 CFR 30.2." -- "\n\n(c) The term" is
    # the NEXT entry's own lead-in bleeding through; TRIM not DROP is this
    # sprint's own Item 1 target for exactly this shape.
    assert "set forth in 29 CFR 30.2." in [
        d.definition_text for d in by_term["Pre-Apprenticeship"]
    ]


def test_red_wa_717_recovers_convicted_without_corrupting_domestic_violence(
    db_session, matter_with_users
):
    """`STATE_WA_T10_C99_S080` (WA row 717, "Penalty assessment"). Primary
    now cleanly recognizes 'domestic violence' via the widened "has the
    same meaning" idiom (regression pin). 'convicted' uses bare `includes`
    -- never recognized by the primary engine even after Item 1's widening
    -- and is ONLY reachable through the fallback; today entirely absent."""
    row = _load_row("us_markers_fallback_guard_wa_717_row.json")
    by_term = _run(db_session, matter_with_users, row, "US-WA")

    dv_texts = [d.definition_text.strip() for d in by_term.get("domestic violence", [])]
    assert (
        "as that term is defined under RCW 10.99.020 and includes violations of equivalent local ordinances."
        in dv_texts
    ), f"'domestic violence' regression: primary-engine capture must stay unchanged, got {dv_texts!r}"

    assert "convicted" in by_term, (
        f"'convicted' never captured by any path today -- got terms {sorted(by_term)!r}"
    )
    convicted_texts = [d.definition_text for d in by_term["convicted"]]
    # Re-pointed (sprint 2026-08-23-defs-debt-31, Item 1 stale-pin sweep):
    # the true definition ends "...or the levying of a fine." -- "For the
    # purposes of this section," is a list-introducer stub leading into
    # the NEXT entry ('domestic violence'), the exact bleed shape Item 1
    # targets (round-1 evidence's "list-introducer stub" failure mode).
    expected = (
        "a plea of guilty, a finding of guilt regardless of whether the "
        "imposition of the sentence is deferred or any part of the penalty "
        "is suspended, or the levying of a fine."
    )
    assert expected in convicted_texts, (
        f"'convicted' captured but not with the expected fallback text: got {convicted_texts!r}"
    )


def test_red_oh_3296_recovers_derivative_transaction_and_person(db_session, matter_with_users):
    """`STATE_OH_T11_C1109_S1109.22` (OH row 3296). Primary now recognizes
    an unrelated 'Loans and extensions of credit' entry via 'shall
    include' (regression pin). 'Derivative transaction' and 'Person' are
    ONLY reachable through the fallback; today entirely absent."""
    row = _load_row("us_markers_fallback_guard_oh_3296_row.json")
    by_term = _run(db_session, matter_with_users, row, "US-OH")

    primary_texts = [d.definition_text for d in by_term.get("Loans and extensions of credit", [])]
    assert any(t.startswith("all of the following: (a) All direct or indirect") for t in primary_texts), (
        f"'Loans and extensions of credit' regression: primary-engine capture "
        f"must stay unchanged, got {primary_texts!r}"
    )

    missing = sorted(t for t in ("Derivative transaction", "Person") if t not in by_term)
    assert not missing, (
        f"lost fallback-only terms never captured by any path today: {missing!r}. "
        f"Got terms: {sorted(by_term)!r}"
    )
    # Re-pointed (sprint 2026-08-23-defs-debt-31, Item 1 stale-pin sweep):
    # the true definition ends "...or other assets." -- the trailing " (2)"
    # is the NEXT entry's own marker ('Loans and extensions of credit'),
    # the exact next-entry-bleed shape Item 1 targets.
    dt_expected = (
        "any transaction that is a contract, agreement, swap, warrant, note, "
        "or option that is based, in whole or in part, on the value of, any "
        "interest in, or any quantitative measure or the occurrence of any "
        "event relating to, one or more commodities, securities, currencies, "
        "interest or other rates, indices, or other assets."
    )
    assert dt_expected in [d.definition_text for d in by_term["Derivative transaction"]], (
        f"'Derivative transaction' captured but not with the expected fallback "
        f"text: got {[d.definition_text for d in by_term['Derivative transaction']]!r}"
    )
    person_texts = [d.definition_text for d in by_term["Person"]]
    assert any(t.startswith("an individual; sole proprietorship; partnership") for t in person_texts), (
        f"'Person' captured but not with the expected fallback text: got {person_texts!r}"
    )


def test_red_ny_1978_recovers_five_container_terms(db_session, matter_with_users):
    """`STATE_NY_AGBS_A26_S399-Q` (NY row 1978). Primary now recognizes
    'consent' via the widened idiom set (regression pin). Five container
    terms enumerated earlier in the same numbered list ('Bakery basket',
    'Bakery tray', 'Dairy case', 'Egg basket', 'Poultry box') are ONLY
    reachable through the fallback; today entirely absent. Also exercises
    the raw-vs-ingest `\\n` unescape trap (NY parquet text is escaped-\\n
    by design; the fixture carries the literal escape, same as production)."""
    row = _load_row("us_markers_fallback_guard_ny_1978_row.json")
    by_term = _run(db_session, matter_with_users, row, "US-NY")

    consent_texts = [d.definition_text for d in by_term.get("consent", [])]
    assert any(t.startswith("tokens or other\nindicia of consent") for t in consent_texts), (
        f"'consent' regression: primary-engine capture must stay unchanged, got {consent_texts!r}"
    )

    lost_terms = ["Bakery basket", "Bakery tray", "Dairy case", "Egg basket", "Poultry box"]
    missing = sorted(t for t in lost_terms if t not in by_term)
    assert not missing, (
        f"lost fallback-only container terms never captured by any path today: "
        f"{missing!r}. Got terms: {sorted(by_term)!r}"
    )
    # Re-pointed (sprint 2026-08-23-defs-debt-31, Item 1 stale-pin sweep):
    # each true definition ends at "...products." -- the trailing
    # "\n  b."/"\n  e." is the NEXT lettered entry's own marker+quote
    # start bleeding through, the exact shape Item 1 targets.
    assert "to transport, store or carry bakery products." in [
        d.definition_text for d in by_term["Bakery basket"]
    ]
    assert "to transport, store or carry dairy products." in [
        d.definition_text for d in by_term["Dairy case"]
    ]
