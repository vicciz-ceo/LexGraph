"""Sprint 2026-08-23-defs-debt-31, Item 2 (issue #31 debt class 2 -- "19
enumerated single-letter wave phantoms"). Named fix direction (issue #31,
this sprint's contract gate 2): reject a single-letter fallback term ONLY
when no defining verb is ADJACENT to it -- distinguishing a genuine `"X"
means ...`-shaped definiendum from a citation/classification letter that
happens to sit within `_MEANS_IDIOM_GAP_RE`'s 200-char lookahead of some
OTHER, unrelated idiom.

Seam (gate 8): `app.definition_links.us_profile._is_implausible_fallback_
capture` / `_merge_fallback_candidates` -- today (this worktree's HEAD)
NEITHER function rejects single-letter terms at all (the blunt `^[A-Za-z]$`
rule shipped and was reverted in the prior sprint, `test_us_markers_
fallback_guard_single_letter_negative_control.py`, to protect the real NV
484B.307 "X" anchor). Every single-letter term the corpus-wide census found
(19/19, `expansion_precision_2.md`) is a phantom of one of two sub-
mechanisms: a lettered cross-reference citation (`paragraph "e"`, 14/19,
all US-IA) or a classification-letter label (`class "B" violation`, 5/19)
-- in BOTH, the idiom that matched belongs to a DIFFERENT, later noun
phrase, not to the quoted letter itself. The distinguishing signal, per
the evidence's own matched-pair analysis, is POSITION: whether the idiom
is the quote's own immediately-adjacent one, or a distant one reached only
because of intervening, unrelated prose.

Real-row exemplar (phantom, sub-mechanism 1): `STATE_IA_TIII_C97B_S97B.49B`,
term `"e"` -- live-verified this pass, currently (wrongly) admitted.
Real-row exemplar (protected anchor): `STATE_NV_T43_C484B_S484B.307`, term
`"X"` (padded `“ X ”` in source, `.strip()`ped) -- live-verified this pass,
currently (correctly) admitted; gate 2 requires this stays true. Two
synthetic M-R107 controls (novel letters, never real corpus identifiers)
give the adjacency signal itself full-population coverage independent of
these two specific real rows, matching the corpus's own two verified
sub-mechanisms.

Byte-exact `definition_text` content is Item 1's own concern (bleed
trimming), not this item's -- both real rows here also happen to exhibit
next-entry bleed (verified live); this file asserts TERM PRESENCE/ABSENCE
only, to keep the two items' seams independent."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.profiles import get_profile
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_defs_debt_31_single_letter_rows.json"
)


def _run(db_session, matter_with_users, act_id: str, jurisdiction: str) -> set[str]:
    rows = {r["act_id"]: r for r in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}
    row = rows[act_id]
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{act_id} debt-31 single-letter adjacency",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    terms: set[str] = set()
    for d in definitions:
        terms.update(d.terms)
    return terms


def test_red_ia_paragraph_citation_letter_rejected_not_admitted(db_session, matter_with_users):
    """`STATE_IA_TIII_C97B_S97B.49B`: the quoted `"e"` is a citation to
    `paragraph "e", subparagraph (2)` -- the idiom that follows
    (`includes`) belongs to `eligible service`, a distinct noun phrase
    introduced between the quote and the idiom, not to `"e"` itself.
    TODAY (live-verified this pass) `"e"` is wrongly admitted, captured as
    `'membership and prior service as a sheriff...'` -- content that is
    real, but belongs to `Eligible service`'s own definition, not to a
    one-letter citation token. Per gate 6 (deletion-side screen intent
    applied to a phantom, D-MAP): removing `"e"` must not touch the row's
    genuine terms."""
    terms = _run(db_session, matter_with_users, "STATE_IA_TIII_C97B_S97B.49B", "US-IA")
    assert "e" not in terms, (
        f"'e' is a paragraph-citation letter mis-paired with a distant "
        f"idiom belonging to 'Eligible service' -- must be rejected once "
        f"the adjacency rule lands, got terms {sorted(terms)!r}"
    )
    assert "Eligible service" in terms, "the genuine sibling term must be unaffected by rejecting 'e'"
    assert "Protection occupation" in terms, "an unrelated genuine term on the same row must be unaffected"


def test_nv_x_protected_anchor_stays_admitted_after_adjacency_fix(db_session, matter_with_users):
    """`STATE_NV_T43_C484B_S484B.307`: the quoted term (source `“ X ”`,
    padded, `.strip()`s to `"X"`) is immediately followed by `symbol means`
    -- a real, adjacent defining idiom for a standard traffic lane-control
    symbol. This is the exact real anchor the blunt `^[A-Za-z]$` rule
    deleted (prior sprint, reverted 2026-08-23). GREEN today (no filter
    exists yet) and MUST STAY GREEN once the adjacency-aware rule lands --
    this is gate 2's own named protected-anchor requirement, live-verified
    against the real row rather than a synthetic stand-in."""
    terms = _run(db_session, matter_with_users, "STATE_NV_T43_C484B_S484B.307", "US-NV")
    assert "X" in terms, (
        "NV 484B.307's 'X' is a genuine definiendum adjacent to its own "
        "'symbol means' idiom -- must never be rejected by the single-"
        f"letter fix, got terms {sorted(terms)!r}"
    )


# --- Structural controls (M-R107: novel letters, never a real corpus term) -

_PROFILE = get_profile("US-WA")  # has a registered EntrySplitterRule (family-3)


def _terms(candidates) -> set[str]:
    return {t for c in candidates for t in c.terms}


TEXT_DISTANT_CLASSIFICATION_LETTER = (
    "Introductory prose describing eligibility requirements at length. "
    'A person is described in subsection two, paragraph "K", which '
    "cross-references clause four of the enforcement schedule, and the "
    "eligible applicant includes any individual who has completed the "
    "certification process required by the board."
)

TEXT_ADJACENT_SINGLE_LETTER = (
    "Introductory prose with no leading quote at all. "
    'A red "Z" indicator means a control signal requiring the operator to '
    "pause all automated movement until manually cleared."
)


def test_red_synthetic_distant_classification_letter_rejected():
    """Novel single letter 'K' (deliberately NOT 'Q' -- `test_qa_regression_
    defs_boundary_idioms.py` already reserves 'Q' for the OPPOSITE,
    adjacent-idiom admitted case; distinct letters avoid any reader
    confusion between the two files even though nothing at runtime
    collides), mis-paired with a distant idiom belonging to 'the eligible
    applicant' (a new noun phrase introduced by an intervening relative
    clause) -- the classification-letter-label sub-mechanism (round-2
    evidence: CA 'B', OH 'F', IA 'C'/'D', SC 'S', 5/19 of the corpus-wide
    phantom census). TODAY wrongly admitted (no filter exists); must be
    rejected once the adjacency rule lands."""
    merged = _terms(
        _PROFILE.extract_definitions_from_section(
            TEXT_DISTANT_CLASSIFICATION_LETTER, scope="law-wide", heading_was_derived=True
        )
    )
    assert "K" not in merged, (
        f"a single-letter term whose nearest idiom belongs to a different, "
        f"later-introduced noun phrase must be rejected -- got {sorted(merged)!r}"
    )


def test_synthetic_adjacent_single_letter_stays_admitted():
    """Novel single letter 'Z', immediately adjacent to its own defining
    idiom (`"Z" indicator means ...`, same shape as the real NV "X"
    anchor's `symbol means`) -- must stay admitted both today and after
    the adjacency rule lands. Positive control protecting the admission
    direction generally, independent of the one real NV row above."""
    merged = _terms(
        _PROFILE.extract_definitions_from_section(
            TEXT_ADJACENT_SINGLE_LETTER, scope="law-wide", heading_was_derived=True
        )
    )
    assert "Z" in merged, (
        f"a single-letter term immediately adjacent to its own defining "
        f"verb must stay admitted -- got {sorted(merged)!r}"
    )
