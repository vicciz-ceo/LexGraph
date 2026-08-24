"""QA bounce, sprint 2026-08-23-defs-debt-31 (issue #31). RED-before-fix
reproductions of TWO independent regressions QA found during Gate 1/Gate 2
verification that the Developer's own scoped test suite did not catch.
Both are real, vendored corpus rows (post-ingest, via the real
`ingest_us_statute_rows` -> `run_definition_linking` pipeline -- not
unit-only), live-verified against the actual worktree HEAD before this
file was written (P-R11: no hand-authored ledger).

Fixture: `us_markers_defs_debt_31_qa_overtrim_rows.json` (3 real rows,
frozen at QA verification time from the same corpus snapshot
`run_gate5_certification.sh` uses).

=====================================================================
Bug 1 (Item 1, gate 1): `_fallback_bleed_trim_end`'s own new relaxed
`_FALLBACK_TRIM_LETTER_PAREN_RE`/`_FALLBACK_TRIM_DIGIT_DOT_RE` checks
cannot distinguish "a letter/digit marker that starts a genuinely NEW,
unrelated entry" from "the NEXT enumerated item of the SAME definition's
own list" -- both shapes are `[period][whitespace]([Letter])[prose]`,
byte-for-byte identical to the heuristic. When a definition is a
`means X, ... includes: (A) ... (B) ... (C) ...`-shaped multi-item list,
the trim now cuts after the FIRST item, discarding every subsequent item
even when (as both real rows below independently prove) there is no
bleed there at all -- baseline already had a completely correct,
fully-bounded capture with NOTHING else following it in the source row.
This is not a rare shape: a bounded heuristic rescan of
`gate5-adjudication/text_changes.jsonl` (73,720 rows) found ~15% of the
population textually shaped this way (upper-bound signal, includes some
false positives where each lettered item genuinely is its own separate
term -- but both rows below were confirmed GENUINE regressions via direct
live-pipeline execution against BOTH `main@8850401` and this worktree's
HEAD, not sampling).

Bug 2 (Item 2, gate 2): `_single_letter_term_lacks_adjacent_idiom`'s
20-char gap threshold is not actually the "wide, unambiguous margin"
its own docstring claims (genuine 8/11 chars vs phantom 37/93 chars).
Real CA `STATE_CA_Chsc_D2_C2.4_S1424` term `"B"` -- ONE OF THE PRIOR
SPRINT'S OWN NAMED "19 enumerated phantoms" (`expansion_precision_2.md`:
"CA 'B'... captured definition_text is a LATER, unrelated usage-context
sentence about appeal rights, not the row's actual 'class "B" violations
are...' definitional clause 4,000+ characters earlier") -- is STILL
admitted after Item 2's fix, confirmed byte-identical between
`gate5-run/baseline/records.jsonl` and `gate5-run/current/records.jsonl`.
Root cause, live-measured: the phantom's own gap ("...in the same manner
as a class "B" violation, and shall include the right of appeal...") is
only 16 chars from the quote's close to "shall include" -- UNDER the
20-char threshold, so `_single_letter_term_lacks_adjacent_idiom` returns
False (wrongly treats it as adjacent/genuine). The contract's own Item 2
claim ("All 19 enumerated phantoms removed") does not hold for this
named exemplar."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

QA_OVERTRIM_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_defs_debt_31_qa_overtrim_rows.json"
)


def _run(db_session, matter_with_users, act_id: str, jurisdiction: str) -> dict:
    rows = {r["act_id"]: r for r in json.loads(QA_OVERTRIM_FIXTURE.read_text(encoding="utf-8"))}
    row = rows[act_id]
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{act_id} debt-31 QA gap recovery",
        rows=[{k: v for k, v in row.items() if not k.startswith("_")}],
        jurisdiction=jurisdiction,
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term: dict[str, list[str]] = {}
    for d in definitions:
        for t in d.terms:
            by_term.setdefault(t, []).append(d.definition_text)
    return by_term


def test_red_ca_covered_populations_multi_item_list_not_truncated_to_first_item(
    db_session, matter_with_users
):
    """`STATE_CA_Cgov_T2_D3_P1_C5.6_S11546.46`, term "Covered populations".
    Baseline (`main@8850401`) captures the FULL, correctly-bounded 8-item
    list (A)-(H) -- 648 chars, live-verified to consume the row's raw text
    all the way to its own end (there is nothing left in the row to bleed
    into). Item 1's trim cuts it to 253 chars, ending right after item
    (A) alone -- items (B) through (H) ('Individuals 60 years of age or
    older.' through 'Residents of rural areas.') are discarded even
    though they are NOT bleed (not next-entry text, not a citation
    footer, not scrape metadata) -- they are the SAME definition's own
    remaining list items. This is the exact shape Gate 1 forbids losing
    (D-RECALL-FP's own spirit: genuine anchor content, not merely the
    anchor's bare presence, must survive a trim)."""
    by_term = _run(
        db_session, matter_with_users, "STATE_CA_Cgov_T2_D3_P1_C5.6_S11546.46", "US-CA"
    )
    texts = by_term.get("Covered populations")
    assert texts, "the anchor itself must never be dropped while fixing its bytes (D-RECALL-FP)"
    expected = (
        "means demographics that are underserved in regards to internet access and "
        "digital literacy, and includes, but is not limited to, the following:\n\n"
        "(A) Households whose income is 150 percent of the federal poverty level or "
        "less for the prior calendar year.\n\n(B) Individuals 60 years of age or "
        "older.\n\n(C) Incarcerated individuals, other than individuals who are "
        "incarcerated in a federal correctional facility.\n\n(D) Veterans.\n\n"
        "(E) Individuals with disabilities.\n\n(F) Individuals with language "
        "barriers, such as English learners and individuals with low literacy "
        "levels.\n\n(G) Members of a racial or ethnic minority group.\n\n"
        "(H) Residents of rural areas."
    )
    assert texts == [expected], (
        f"'Covered populations' must keep its full 8-item (A)-(H) list -- items "
        f"(B)-(H) are the SAME definition's own content, not bleed -- got "
        f"{texts[0]!r} ({len(texts[0])} chars, expected {len(expected)})"
    )


def test_red_fl_cancer_21_item_list_not_truncated_to_first_item(db_session, matter_with_users):
    """`STATE_FL_TX_C112_PI_S112.1816`, term "Cancer". Baseline captures
    the FULL, correctly-bounded 21-item list (Bladder cancer. through
    Thyroid cancer.) -- 509 chars, ending cleanly right before the row's
    own next lettered definition, "(b) 'Employer' has the same meaning
    as in s. 112.191." Item 1's trim cuts it to 18 chars -- "1. Bladder
    cancer." alone -- discarding cancer types 2-21 (Brain cancer through
    Thyroid cancer), a 96.5% loss of genuine, correctly-scoped list
    content that is not bleed by any definition gate 1 uses (not another
    entry's text, not a citation footer, not scrape metadata)."""
    by_term = _run(db_session, matter_with_users, "STATE_FL_TX_C112_PI_S112.1816", "US-FL")
    texts = by_term.get("Cancer")
    assert texts, "the anchor itself must never be dropped while fixing its bytes (D-RECALL-FP)"
    expected = (
        "includes: 1. Bladder cancer. 2. Brain cancer. 3. Breast cancer. "
        "4. Cervical cancer. 5. Colon cancer. 6. Esophageal cancer. "
        "7. Invasive skin cancer. 8. Kidney cancer. 9. Large intestinal cancer. "
        "10. Lung cancer. 11. Malignant melanoma. 12. Mesothelioma. "
        "13. Multiple myeloma. 14. Non-Hodgkin’s lymphoma. "
        "15. Oral cavity and pharynx cancer. 16. Ovarian cancer. "
        "17. Prostate cancer. 18. Rectal cancer. 19. Stomach cancer. "
        "20. Testicular cancer. 21. Thyroid cancer."
    )
    got = texts[0]
    assert len(got) > 100, (
        f"'Cancer' must keep its full 21-item list, not just the first entry -- "
        f"got {got!r} ({len(got)} chars) -- expected something close to the full "
        f"{len(expected)}-char list ending '...21. Thyroid cancer.'"
    )


def test_red_ca_class_b_phantom_still_survives_item2_adjacency_fix(db_session, matter_with_users):
    """`STATE_CA_Chsc_D2_C2.4_S1424`, term "B" -- ONE OF THE PRIOR SPRINT'S
    OWN NAMED 19 ENUMERATED PHANTOMS (`expansion_precision_2.md`, the
    "classification-letter label" sub-shape, named explicitly as "CA
    'B'"). The row's TRUE genuine defining clause is subdivision (e)(1):
    'class "B" violations are violations that the department determines
    have a direct or immediate relationship to the health, safety, or
    security of long-term health care facility residents...'. The
    phantom capture instead pairs the quoted "B" with a LATER, unrelated
    usage in subdivision (2)(A) ('...in the same manner as a class "B"
    violation, and shall include the right of appeal as specified in
    Section 1428. Where the assessed penalty is in excess of...') --
    live-measured gap from that quote's close to "shall include" is 16
    chars, UNDER Item 2's own 20-char adjacency threshold, so
    `_single_letter_term_lacks_adjacent_idiom` wrongly treats it as
    adjacent/genuine. Confirmed still present, byte-identical, in both
    `gate5-run/baseline/records.jsonl` and `gate5-run/current/
    records.jsonl` (Item 2's fix never touched it). RED: the term must
    NOT be admitted at all (D-MAP requires either the genuine definition
    or nothing -- not a phantom byte-fragment); today it survives."""
    by_term = _run(db_session, matter_with_users, "STATE_CA_Chsc_D2_C2.4_S1424", "US-CA")
    texts = by_term.get("B")
    assert not texts, (
        "'B' is one of the prior sprint's own named 19 single-letter phantoms "
        "(CA 'B', a classification-letter label mis-paired with unrelated "
        "appeal-rights prose 4,000+ chars from its own real definition) -- "
        "Item 2's adjacency fix must reject it (16-char gap to 'shall include' "
        "is a coincidental short distance, not a genuine 'B means ...' "
        f"definiendum), but it is still admitted today: {texts!r}"
    )
