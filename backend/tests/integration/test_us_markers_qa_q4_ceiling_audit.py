"""QA1 (phase-2 QA cycle 1) -- Q4: audit of the 3,000-char
`MAX_CLEAN_DEFINITION_LENGTH` ceiling + list-introducer exclusion
(sprint 2026-08-04-defs-us-markers, gate U1).

**Measurement, corpus-wide, across the 7 jurisdictions
`us_markers_boundary.extract_quote_anchored_entries` directly covers
(VA/WA/FED/UT/TX/SC/AZ; scratchpad `markers-qa-q4-ceiling-audit.py`, not
committed per data policy -- no test reads the corpus):**

```
Total KEPT entries (<= 3000 chars): 144,706
Total DROPPED entries (> 3000 chars, silently discarded): 1,308

Histogram of KEPT lengths, 2000-3000+ in 100-char bins:
  [2000-2099]: 196   [2500-2599]: 143   [2900-2999]:  91
  [2100-2199]: 184   [2600-2699]: 102   [3000-3099]:   1  (the one entry
  [2200-2299]: 173   [2700-2799]:  99                     exactly == 3000)
  [2300-2399]: 143   [2800-2899]: 105
  [2400-2499]: 167
```

**Finding 1 -- NO spike at the boundary; the distribution is a smooth,
monotonic decline (196 -> 91 across 2000-2999), then an abrupt drop to
essentially zero above 3000 (only the single exactly-3000 value, then
nothing -- everything above is DROPPED, not truncated-and-kept).** The
brief's hypothesis ("a spike at the boundary is evidence of truncation")
is NOT confirmed in the literal sense: nothing in `us_markers_boundary.py`
truncates a definition TO 3000 chars -- `extract_quote_anchored_entries`'s
own filter (`if definition_text and len(definition_text) <=
MAX_CLEAN_DEFINITION_LENGTH: entries.append(...)`) DROPS the whole
candidate outright when it exceeds the ceiling, it never clips it down to
3000. So there is no artificial pile-up of values AT exactly 3000 the way
a true truncate-to-N mechanism would produce -- reported honestly, not
rounded to confirm the hypothesis.

**Finding 2 -- the real defect is not a truncation artifact, it is a pure
MISS: 1,308 real candidate definitions are silently discarded corpus-wide
(0.9% of all quote-anchored entries), and manual inspection of a 15-row
VA sample shows a GENUINE MIX**, not "all correctly excluded swallows" as
the ceiling's own docstring implies ("a bounded, honest MISS ... the right
side of ruling U-R1's bar"):

- Several ARE real swallows, correctly excluded (e.g. VA "Waste
  management" and "State dairy regulation" both bleed into unrelated
  interstate-compact ARTICLE text; VA "remote supervision" and "wrongful
  use of electronic self-help" both swallow trailing amendment-history
  citation blocks -- the same defect FAMILY as the already-known FED
  unbounded-last-entry issue).
- **At least one is proven, byte-verified, to be a genuine, clean, single
  statutory definition wrongly dropped**: `STATE_VA_T47.1_C1_S47.1-2`
  ("Definitions", Virginia's Notary Act), term `"Satisfactory evidence of
  identity"` -- a real ~3,020-char definition enumerating acceptable
  identification documents and identity-verification methods, starting
  immediately after `"Satisfactory evidence of identity" means` and
  ending cleanly right before the next real quoted term, `"Seal" means...`
  Confirmed against the real row this pass: no swallowed neighbor content,
  no amendment-history leakage, a single coherent legal provision that
  happens to be long because notary identity-verification law genuinely
  enumerates many document types and methods. **This is a real U-R1 miss
  today**: the term is captured by NEITHER baseline (no numbered-block
  structure) NOR our own rule (dropped by the ceiling) NOR any other
  registered rule -- confirmed via the real pipeline in the RED test
  below. Also genuinely plausible from inspection but NOT byte-verified
  this pass (reported as unverified, not claimed): VA "Professional
  corporation" / "Professional limited liability company" (parallel,
  consistent definitions about licensed-profession corporate structures)
  and "Deceased person" (a death-benefit statute with a long enumerated
  list of covered occupations, ending cleanly on-topic).

**Finding 3 -- a SEPARATE, real boundary bug in the SAME engine, found
while diagnosing Finding 2, that makes some ceiling-dropped lengths an
UNDER-count of the true swallow/genuine question**: for this exact VA row,
`_LETTER_MARKER_RE`'s hard-stop (`_QUOTE_WITHIN_LOOKAHEAD_RE`, "a quote
within 40 non-period chars after the marker") false-fires on the
parenthetical abbreviation `"(PIV)"` inside `..."Personal Identity
Verification (PIV) of Federal Employees and Contractors,"...` -- the
closing quote of that SAME already-open quoted phrase sits within the
40-char lookahead window, so `"(PIV)"` (a real acronym expansion, not a
lettered sub-entry marker) is wrongly treated as introducing a new nested
entry. Diagnosed directly against the real row (not guessed): without this
false hard-stop, "Satisfactory evidence of identity"'s true span would run
to 3,332 chars (still over the ceiling, so the OUTCOME for this exact row
is unchanged -- dropped either way), but on a DIFFERENT row where the true
span is closer to the ceiling this same false hard-stop could just as
easily produce a KEPT-but-truncated-mid-sentence definition instead of a
dropped one. Not separately pinned with its own RED this pass (a broader
corpus sweep for "parenthetical 2-4-letter acronym near any quote
character" is real follow-up work, out of this pass's time budget) --
recorded here so it is not lost, and so Finding 2's 1,308-entry count is
understood as covering BOTH true-length-over-ceiling misses AND some
share of this false-hard-stop-shortened misses.

**Scope note**: this measurement is necessarily scoped to the 7
jurisdictions `us_markers_boundary.py` directly covers (its ceiling has no
effect anywhere else) -- NOT the full 53-jurisdiction corpus, since the
ceiling mechanism does not run outside these rules at all. Reported as
"across the jurisdictions the ceiling actually gates," matching the
brief's own framing that a corpus-wide claim must be honest about what the
mechanism can even reach.

Row vendored verbatim, byte-verified against `us_va_statutes.parquet` this
pass.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.ingest_us_statutes import ingest_us_statute_rows
from app.definition_links.pipeline import run_definition_linking
from app.definition_links.rules.us_markers_boundary import (
    MAX_CLEAN_DEFINITION_LENGTH,
    extract_quote_anchored_entries,
)
from app.definition_links.us_profile import is_definitions_heading
from app.models.definition import Definition

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "us_markers_qa_q4_va_notary_definitions_row.json"
)

ACT_ID = "STATE_VA_T47.1_C1_S47.1-2"
TERM = "Satisfactory evidence of identity"


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["act_id"] == ACT_ID
    return rows[0]


def test_fixture_row_is_directly_definitions_headed():
    row = _load_row()
    assert is_definitions_heading(row["section_title"]) is True


def test_the_real_definition_is_genuinely_long_not_a_swallow():
    """Documents WHY this is classified genuine, not a swallow: the raw
    body content between the term's idiom and the true next term ("Seal")
    is one coherent notary-law provision throughout, with no unrelated
    content, no amendment-history leakage, and no nested quoted term with
    its own idiom in between (confirmed: only the term's own internal
    self-reference `"satisfactory evidence of identity"` appears, and it
    is NOT followed by a defining idiom, so it correctly does not start a
    new entry)."""
    row = _load_row()
    text = row["text"]
    term_pos = text.index(f'"{TERM}" means')
    seal_pos = text.index('"Seal" means')
    assert term_pos < seal_pos
    span = text[term_pos:seal_pos]
    # No amendment-history / editorial-notes leakage inside this span.
    for forbidden in ("Editorial Notes", "Amendments", "ARTICLE ", "Sue and be sued"):
        assert forbidden not in span, f"{forbidden!r} found -- this may actually be a swallow"
    # Genuinely long: the raw span (before any ceiling) exceeds 3,000.
    idiom_end = term_pos + len(f'"{TERM}" means')
    assert (seal_pos - idiom_end) > MAX_CLEAN_DEFINITION_LENGTH


def test_red_our_engine_silently_drops_the_genuine_long_definition():
    """The RED at the engine level: `extract_quote_anchored_entries`
    should still surface this term even though its true definition is
    long -- today it is silently ABSENT from the returned entries (dropped
    by the 3,000-char ceiling), not merely truncated."""
    row = _load_row()
    entries = dict(extract_quote_anchored_entries(row["text"]))
    assert TERM in entries, (
        f"{TERM!r} is missing from extract_quote_anchored_entries's output entirely -- "
        f"the ceiling silently dropped a genuine, clean, ~3,020-char real definition. "
        f"Got terms: {sorted(t for t, _ in extract_quote_anchored_entries(row['text']))!r}"
    )


def test_red_real_pipeline_never_captures_this_genuine_definition_at_all(
    db_session, matter_with_users
):
    """The load-bearing RED, end-to-end: through the real production
    pipeline, this genuine VA notary-law term should be captured with its
    real, complete definition -- today it is captured by NO path at all
    (not baseline -- no numbered-block structure in this body; not our
    rule -- dropped by the ceiling), so the term is entirely invisible to
    `run_definition_linking`."""
    row = _load_row()
    ingest_us_statute_rows(
        db_session,
        repository_id=matter_with_users["repository_id"],
        matter_id=matter_with_users["matter_id"],
        title="VA notary Definitions (QA1 Q4)",
        rows=[row],
        jurisdiction="US-VA",
    )
    result = run_definition_linking(
        db_session,
        matter_id=matter_with_users["matter_id"],
        triggered_by_user_id=matter_with_users["contributor_id"],
    )
    definitions = [db_session.get(Definition, d["id"]) for d in result["created_definitions"]]
    by_term = {t: d for d in definitions for t in d.terms}
    assert TERM in by_term, (
        f"{TERM!r} was never captured by the real pipeline at all -- got terms "
        f"{sorted(by_term)!r}. This is a genuine, real, clean statutory definition "
        "silently invisible to every path today because it exceeds the 3,000-char "
        "safety-net ceiling."
    )
