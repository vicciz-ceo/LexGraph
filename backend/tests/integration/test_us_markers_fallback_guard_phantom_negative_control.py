"""RED + negative control (sprint 2026-08-20-defs-boundary-idioms, pass 2
amendment, Item 2). `USC_T12_C2_S84` (FED row 4978) is a dual-purpose real
row: it carries BOTH a genuine fallback-only loss ('derivative
transaction') AND two of investigation.md's 4 classified PHANTOM-REMOVAL
mis-captures on the exact same row -- baseline fallback false positives
whose captured "term" is not a real definiendum at all (a legislative-
history amendment caption, and a stray preposition), evidently mis-paired
by the fallback's own quote scanning against annotation text, unrelated to
this sprint's idiom widening.

Per the amended gate 3, the 4 phantom removals are "acceptable" (not
required to recover) -- but the Planner brief's own negative-control
requirement is stronger: the fix must not ADMIT junk. Item 2's spec (see
the sprint contract) therefore adds a narrow, evidence-derived implausible-
capture rejection alongside the per-term merge: reject an otherwise-
admissible fallback candidate when (a) its term, stripped, is nothing but
a bare common English function word (a closed list: for/and/or/the/a/an/
of/in/to/with/by -- exactly the observed 'for' shape), or (b) its term OR
definition_text begins with a legislative-history amendment-caption shape,
a 4-digit year immediately followed by an em/en dash or hyphen (`^\\d{4}
[\\u2014\\u2013-]`) -- exactly the observed '2010\\u2014Subsec. ...' shape.
Validated this pass against the full 130-row genuine-loss population
(0 false rejects) and all 4 known phantom rows (100% correctly rejected) --
see the Planner's report for the measurement script/output."""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_fallback_guard_fed_4978_phantom_row.json"
)

ACT_ID = "USC_T12_C2_S84"
PHANTOM_CAPTION = "2010—Subsec. (b)(1). Pub. L. 111–203, §610(a)(1), substituted"
PHANTOM_PREPOSITION = "for"


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["act_id"] == ACT_ID
    return rows[0]


def _run(db_session, matter_with_users) -> dict[str, list]:
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title=f"{ACT_ID} fallback-guard phantom negative control (Item 2)",
        rows=[row],
        jurisdiction="US-FED",
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


def test_fixture_carries_both_the_genuine_loss_and_the_two_phantom_mis_captures():
    """Sanity: guards against this RED silently going vacuous if the
    fixture is ever edited."""
    row = _load_row()
    text = row["text"]
    assert '"derivative transaction"' in text.lower() or "derivative transaction" in text.lower()
    assert '"loans and extensions of credit"' in text.lower() or "loans and extensions of credit" in text.lower()


def test_red_derivative_transaction_is_recovered(db_session, matter_with_users):
    """The genuine loss on this row (paired with the two phantom
    mis-captures below): 'derivative transaction' is only reachable
    through the fallback and is entirely absent today."""
    by_term = _run(db_session, matter_with_users)

    primary_texts = [d.definition_text for d in by_term.get("loans and extensions of credit", [])]
    assert any(t.startswith("—") or "all direct or indirect advances" in t for t in primary_texts), (
        f"'loans and extensions of credit' regression: primary-engine capture "
        f"must stay unchanged, got {primary_texts!r}"
    )
    assert "person" in by_term, f"'person' regression: got {sorted(by_term)!r}"

    assert "derivative transaction" in by_term, (
        f"'derivative transaction' never captured by any path today -- got "
        f"terms {sorted(by_term)!r}"
    )
    expected_prefix = (
        "any transaction that is a contract, agreement, swap, warrant, note, "
        "or option that is based, in whole or in part, on the value of"
    )
    texts = [d.definition_text for d in by_term["derivative transaction"]]
    assert any(t.startswith(expected_prefix) for t in texts), (
        f"'derivative transaction' captured but not with the expected fallback "
        f"text: got {texts!r}"
    )


def test_negative_control_the_stray_preposition_stays_absent(db_session, matter_with_users):
    """MUST STAY GREEN both before and after Item 2's fix: the phantom
    term 'for' (a preposition, not a real definiendum -- the fallback's
    own quote-pairing weakness, unrelated to this sprint) must not be
    resurrected as a persisted Definition anchor."""
    by_term = _run(db_session, matter_with_users)
    assert PHANTOM_PREPOSITION not in by_term, (
        f"'for' must NOT be admitted as a term -- it is a phantom mis-capture "
        f"(a stray preposition, not a real defined term), not a genuine loss. "
        f"Got: {[d.definition_text for d in by_term.get(PHANTOM_PREPOSITION, [])]!r}"
    )


def test_negative_control_the_legislative_history_caption_stays_absent(db_session, matter_with_users):
    """MUST STAY GREEN both before and after Item 2's fix: the phantom
    term (a legislative-history amendment caption glued together by the
    fallback's own mis-pairing, not a real definiendum) must not be
    resurrected as a persisted Definition anchor."""
    by_term = _run(db_session, matter_with_users)
    assert PHANTOM_CAPTION not in by_term, (
        f"the legislative-history caption must NOT be admitted as a term -- "
        f"it is a phantom mis-capture, not a real defined term. Got: "
        f"{[d.definition_text for d in by_term.get(PHANTOM_CAPTION, [])]!r}"
    )
    # Also guard against ANY term that merely starts with a caption shape
    # (4-digit year + em/en-dash/hyphen) slipping through under a
    # differently-truncated key.
    import re

    caption_shape = re.compile(r"^\d{4}[—–-]")
    caption_like = [t for t in by_term if caption_shape.match(t)]
    assert not caption_like, (
        f"a legislative-history-caption-shaped term was admitted: {caption_like!r}"
    )
