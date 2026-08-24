"""QA regression coverage -- sprint 2026-08-23-defs-debt-31 (issue #31),
Item 3 (mis-paired-quote FP class, gate 3). Independent QA pass verified
PASS as a legitimate NO-CODE outcome: independently re-confirmed the
adjudication's core claim against real source text for its named
exemplars (`Crime Stoppers` mis-pair, `USC_T15_C93_S6701`'s "(8) NAIC...
(9) Person..." genuine marker-crossing counter-example) during QA
verification. Item 3 shipped no `backend/app/` code, so there is no
production behavior change to pin; the asset worth protecting is the
WRITTEN EVIDENCE the no-code verdict rests on -- a content pin so a
future silent edit/regeneration of the adjudication document (which
would invalidate this sprint's own gate-3 PASS without review) is
caught. The Developer's own evidence test
(`test_us_markers_defs_debt_31_mispaired_quote_evidence.py`, 3 tests,
GREEN, unchanged) already covers the shape-indistinguishability finding
at the code level; this file does not duplicate it."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADJUDICATION_PATH = (
    ROOT
    / "docs/sprint/sprints/2026-08-23-defs-debt-31-scripts/item3_mispaired_quote_adjudication.md"
)


def test_item3_adjudication_still_records_a_no_code_pass_outcome():
    """The document's own headline verdict line must not silently flip."""
    text = ADJUDICATION_PATH.read_text(encoding="utf-8")
    assert "NO-CODE" in text and "Legitimate PASS per gate 3" in text, (
        "item3_mispaired_quote_adjudication.md no longer records a NO-CODE "
        "PASS outcome -- gate 3's own verdict for this item has changed and "
        "needs a fresh QA/Planner review, not a silent drift"
    )


def test_item3_adjudication_still_names_all_four_prior_sprint_exemplars():
    """The 4 real mis-paired exemplars from the prior sprint's own
    `expansion_precision.md` that this pass's Finding 1 independently
    re-verified against live source text (own gap-text re-derivation, not
    quoted from the prior sprint) must stay named -- QA independently
    confirmed the `Crime Stoppers` (`STATE_VA_T22.1_C14_A3_S22.1-280.2`)
    gap live against the real VA corpus row during this verification
    pass."""
    text = ADJUDICATION_PATH.read_text(encoding="utf-8")
    for exemplar in (
        "apprenticeship",
        "Meeting Isotope Needs and Capturing Opportunities",
        "Crime Stoppers",
        "Warning: Electric Fence.",
    ):
        assert exemplar in text, f"named exemplar {exemplar!r} missing from the adjudication doc"
    assert "STATE_VA_T22.1_C14_A3_S22.1-280.2" in text


def test_item3_adjudication_still_names_the_fed_naic_person_counterexample():
    """Finding 2's own decisive counter-example (why a naive marker-
    crossing rule is unsafe): `USC_T15_C93_S6701`'s "(8) NAIC... (9)
    Person..." shape -- QA independently re-fetched this exact real FED
    row during verification and confirmed both are genuine, correctly
    adjacent `"(N) Label.—The term 'X' means Y."` entries, live-verified
    against the real `vaquill/open-us-law` snapshot text (not re-quoted
    from this document)."""
    text = ADJUDICATION_PATH.read_text(encoding="utf-8")
    assert "USC_T15_C93_S6701" in text
    assert "NAIC" in text and "Person" in text
    assert "No code this sprint." in text
