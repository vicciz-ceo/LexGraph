"""RED tests for `_UNQUOTED_TERM_DASH_RE`'s precision fix (sprint
2026-08-04-defs-us-pr, cycle 7, gate M-R14 gate 1 / M-R15 step 1). Planner-
authored, tests/fixtures only -- `backend/app/**` is untouched by this
file.

## Why this cycle exists

QA's cycle-5 per-block measurement (the correct denominator -- a whole-body
measurement is directionally uninformative, confirmed twice on this exact
regex) found the cycle-5 ASCII-hyphen widening of `_UNQUOTED_TERM_DASH_RE`
changes 235 per-block dispatch outcomes at ~30-35% precision. Ruling M-R14
made fixing/narrowing this regex a hard, blocking entry criterion before
ANY canonical-path item (18c, 19-24) ships, because
`pr_profile.extract_definitions_from_section` -- the only caller of this
regex -- has zero production callers TODAY but goes live the moment item
P1 (the very next item after this gate) registers a PR
`TermClauseRule`/`EntrySplitterRule`. Ruling M-R15 confirmed gate 1 (this
one) must land strictly before that wiring.

## Independent re-measurement (Planner, this cycle)

Reproduced QA's per-block method independently against the real
`us_pr_statutes.parquet` (measurement only -- see the panel log; no test
here reads the corpus, per program standing constraints), splitting every
one of the corpus's 23,636 row bodies into blocks via the module's own
`_ENTRY_MARKER_RE` exactly as `extract_definitions_from_section` does, and
diffing OLD (typographic dash only) vs the live NEW (cycle-5 widened)
dispatch per block: **235 changed outcomes, exact match to QA's number**
(224 brand-new / 11 reclassified in this independent run vs QA's 213/22 --
the 1-in-235 split difference is immaterial; the total, the number that
matters for the gate, reproduces exactly). This CONFIRMS QA's measurement
rather than contradicting it -- no escalation needed.

Manually classified two independent random samples (n=50, n=60, both
seeded, both drawn from the changed-outcome population) against the real
corpus text. Root cause of the majority of junk: the term-capture group
`.{1,100}?` is not excluded from crossing a `.-` (period immediately
followed by a hyphen, NO space) boundary -- a real, common PR legal-
drafting convention marking a subsection/heading label ("Definiciones.-
Para fines de esta sección", "Método de depreciación aplicable.- Para
propósitos de esta sección"). `_UNQUOTED_TERM_PERIOD_RE`, this file's
OTHER unquoted pattern, already refuses to cross exactly this boundary
(its own `(?:[^.]|\\.(?!-))` term-group exclusion, documented in its own
comment block as protecting the identical M-R7 "(a) En General.-" shape).
`_UNQUOTED_TERM_DASH_RE` never received the same discipline, so instead of
failing closed at the `.-`, its non-greedy search walks past it hunting
for the next reachable, real space-preceded hyphen -- frequently a
structural "... - (1) ..." list-intro dozens of characters later,
fabricating a bogus split with the whole heading-plus-preamble as `term`
and the first list item as `definition_text`. Live-confirmed this defect
predates cycle 5 (17 real rows where OLD's typographic-dash-only pattern
ALREADY produced the identical class of garbage via a LATER typographic
dash reached the same way) -- cycle 5's ASCII-hyphen widening did not
create this defect, it just multiplied the opportunities for it to fire
(many more candidate hyphens now qualify), which is exactly why the
changed-outcome count is as large as it is.

## The fix (proposed to the Developer, not applied by this Planner)

```python
_UNQUOTED_TERM_DASH_RE = re.compile(
    r"^((?:[^.]|\\.(?!-)){1,100}?)\\s*\\.?\\s*(?:[–—]|(?<=\\s)-)\\s*"
)
```

Only the term-capture group changes (`.{1,100}?` ->
`(?:[^.]|\\.(?!-)){1,100}?`), exactly mirroring `_UNQUOTED_TERM_PERIOD_RE`'s
own established discipline in this same file. Nothing about which
separator characters are accepted changes: the typographic dash stays
unconditional, the ASCII hyphen still requires an immediately preceding
whitespace (cycle 5's own, already-verified-correct lookbehind).

## Measured precision AND recall of this narrowing (Planner, this cycle)

- **Rejects 61/235 (26%) of the changed outcomes.** Random sample n=40
  (seeded) of the rejected set, hand-classified against real corpus text:
  **40/40 (100%) confirmed junk** -- every single sampled rejection is the
  ".- Para propósitos/efectos/fines de ..." heading-swallow shape above.
  Measured recall cost of this rejection: effectively zero genuine rows
  lost (0/40 in the sample).
- **Retains 208/235 (88.5%) of the changed outcomes**, including BOTH
  explicitly-named genuine target rows (`STATE_PR_LEY_209_2016_ART2`,
  `STATE_PR_LEY_236_2015_ART2` -- 7/7 individual entries preserved,
  verified end-to-end through the real `extract_definitions_from_section`,
  not simulated). Random sample n=60 (seeded, 58 non-degenerate) of the
  retained set, hand-classified: **~31/58 (53%) genuine on a lenient
  reading, ~24/58 (41%) genuine on a strict reading that resolves every
  "rule vs. definition" borderline call against the candidate** -- i.e.
  **measured precision ~41-53%** on the retained set, roughly 1.4-1.6x the
  pre-narrowing ~30-35%.
- **Known, NOT addressed by this narrowing:** a second, smaller junk class
  -- an ASCII hyphen embedded in ordinary prose with no period involved at
  all, e.g. a hyphenated proper name (`"...al Consejo Juanadino Pro -
  Festejos de Reyes, Inc...."`, real row `STATE_PR_LEY_163_2005_ART2`,
  NOT a Definiciones section, NOT a definition of any kind) or a garbled
  mid-sentence split. This class shares no clean, generalizable mechanical
  signature the way the `.-` class does -- pinned below as an explicit,
  accepted residual limitation (`xfail`), not silently dropped from this
  report.
- **Decision: NARROW, not drop.** Dropping back to typographic-dash-only
  would cost roughly 90-110 real genuine captures corpus-wide (the
  precision-weighted estimate over the 208-row retained population), not
  "a handful" -- far more than the two explicitly-named anchor rows. A
  single, mechanistically-justified, already-precedented fix recovers most
  of that recall while rejecting the single largest, most systematic junk
  class at ~100% measured precision on its own rejected set. Precision on
  what remains (~41-53%) is a real, honestly-reported limitation, not
  claimed to be fully resolved -- recorded as open for whoever wires P1's
  canonical extraction next.

## Live-path status of every test below (read before trusting these greens)

`pr_profile.extract_definitions_from_section` has ZERO production callers
today (`USProfile.extract_definitions_from_section` calls the
`us_profile` module function plus registry rules, never `pr_profile`'s --
identity-verified by the cycle-5/cycle-6 Manager and re-confirmed at the
cycle-6 wake). Every test below therefore calls
`extract_definitions_from_section` DIRECTLY, not through
`get_profile("US-PR")` -- this is a DIRECT-FUNCTION test, not a live-path
proof. It proves the function's own behavior in isolation; it does NOT
prove anything reaches this code from a real document today, and cannot,
because nothing does yet.

**Upgrade condition (binding on whoever does P1):** once P1 registers a
PR `TermClauseRule`/`EntrySplitterRule` that routes through
`pr_profile`'s block parser, `_UNQUOTED_TERM_DASH_RE` goes live and these
assertions must be re-proven through `get_profile("US-PR")` /
`run_definition_linking`, not merely re-confirmed at the direct-function
level -- this file's own greens must not be mistaken for that proof, per
this panel's own standing lesson about direct-call greens that look like
live proof.

Three real rows, `pr_sample_rows_cycle7.json`, byte-compared against the
live parquet immediately after writing (`3 rows checked, 0 problems`) --
see the fixtures README. `STATE_PR_LEY_209_2016_ART2` (the fourth genuine
anchor row) is NOT re-vendored here -- it is already vendored in
`pr_sample_rows_qa_cycle4.json` and already has a passing regression test
(`test_pr_profile_qa_cycle4_findings.py::
test_unquoted_dash_separator_rejects_a_real_ascii_hyphen`) that this
narrowing must not weaken; verified end-to-end above, not re-pinned here
to avoid a duplicate assertion on the same fixture row.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.definition_links.pr_profile import extract_definitions_from_section

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "pr_sample_rows_cycle7.json"
)


def _load_fixture_rows() -> dict[str, dict]:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {row["act_id"]: row for row in rows}


@pytest.fixture()
def pr_rows():
    return _load_fixture_rows()


# --- Junk rejection: the ".- Para propósitos/efectos/fines de ..." class ---
# ---------------------------------------------------------------------------


def test_heading_swallow_junk_term_is_not_captured(pr_rows):
    """`STATE_PR_RENTAS_SEC1072_04`, clause (c): 'Aportación de Propiedad
    con Pérdida de Capital.- En el caso de cualquier propiedad que - (1)
    fue aportada por un socio a la sociedad, y (2) constituía un activo de
    capital...' -- the source itself is inconsistent (clauses (a)/(b) use
    'que:' with a colon, a real `_ENTRY_MARKER_RE` boundary; clause (c)
    uses 'que -' with a hyphen instead, which is NOT a marker boundary).
    Under the live (unnarrowed) regex this whole clause becomes ONE block,
    and `_UNQUOTED_TERM_DASH_RE`'s non-greedy term group walks straight
    past the 'Capital.-' subsection-label boundary hunting for the next
    reachable space-preceded hyphen, landing on the accidental 'que - (1)'
    hyphen and fabricating a bogus ~88-char 'term' out of the entire
    heading-plus-preamble, with the first numbered list item mis-captured
    as its 'definition_text'. Currently captured (RED against
    unnarrowed `backend/app/**`): this bogus term IS present. After the
    Developer's `.-`-exclusion fix, `_UNQUOTED_TERM_DASH_RE` must fail
    closed at 'Capital.-' instead, and (since `_UNQUOTED_TERM_PERIOD_RE`
    also cannot cross the same `.-` and finds no other qualifying period+
    capital-letter boundary in this clause) the whole clause should
    produce NO candidate at all -- correctly skipped, not fabricated."""
    row = pr_rows["STATE_PR_RENTAS_SEC1072_04"]
    assert "que - (1) fue aportada" in row["text"]
    candidates = extract_definitions_from_section(row["text"], scope="canonical")
    terms = {t for c in candidates for t in c.terms}
    bogus = {
        t
        for t in terms
        if t.startswith("Aportación de Propiedad con Pérdida de Capital")
    }
    assert not bogus, (
        "_UNQUOTED_TERM_DASH_RE's term group crosses the 'Capital.-' "
        "subsection-label boundary and fabricates a bogus term out of the "
        f"whole heading-plus-preamble -- currently captured: {bogus!r}"
    )


def test_heading_swallow_junk_with_footer_contamination_is_not_captured(pr_rows):
    """`STATE_PR_RENTAS_SEC1072_04`, clause (d): 'Definiciones.- Para
    fines de esta sección - LexJuris de Puerto Rico ©2011
    www.LexJuris.net 375 (1) Créditos no realizados.- Tendrá el mismo
    significado...' -- the SAME `.-`-crossing defect as the sibling test
    above, compounded here by an unstripped page-break/watermark artifact
    (the 'LexJuris de Puerto Rico ©2011 www.LexJuris.net 375' scrape
    boilerplate) landing inside the fabricated 'definition_text', the same
    footer-contamination class QA's cycle-5/6 findings fixed in
    `extract_local_definitions` but which was never ported to this
    function's own per-block scan. Currently captured (RED): the bogus
    'Definiciones.- Para fines de esta sección' term IS present, with a
    footer-contaminated definition_text. After the fix, this clause
    should also correctly yield NO candidate at all."""
    row = pr_rows["STATE_PR_RENTAS_SEC1072_04"]
    assert "LexJuris de Puerto Rico" in row["text"]
    candidates = extract_definitions_from_section(row["text"], scope="canonical")
    terms = {t for c in candidates for t in c.terms}
    bogus = {t for t in terms if t.startswith("Definiciones.- Para fines de esta")}
    assert not bogus, (
        "_UNQUOTED_TERM_DASH_RE's term group crosses the 'Definiciones.-' "
        "subsection-label boundary and fabricates a bogus term whose "
        "definition_text is contaminated by unstripped LexJuris footer "
        f"boilerplate -- currently captured: {bogus!r}"
    )


def test_heading_swallow_row_yields_no_candidates_at_all(pr_rows):
    """Whole-row regression pin for the same fixture: today
    `extract_definitions_from_section` returns exactly 2 candidates for
    `STATE_PR_RENTAS_SEC1072_04`, BOTH bogus (the two clauses pinned
    individually above) -- there is no genuine Definiciones content in
    this row at all (it is an ordinary substantive tax-code section, not a
    canonical definitions section). After the fix, the correct count is
    0, not merely 'the two known-bad terms are absent' -- this closes off
    a fix that suppresses the bad terms' TEXT while still emitting some
    other candidate for the same spans."""
    row = pr_rows["STATE_PR_RENTAS_SEC1072_04"]
    candidates = extract_definitions_from_section(row["text"], scope="canonical")
    assert candidates == [], (
        "expected zero candidates from this non-Definiciones tax-code "
        f"section after the .- narrowing -- currently returns {candidates!r}"
    )


# --- Genuine-capture regression guards (already GREEN today; pinned so ----
# --- the Developer's fix cannot accidentally regress them) ----------------


def test_genuine_ascii_hyphen_entries_survive_the_narrowing(pr_rows):
    """`STATE_PR_LEY_236_2015_ART2`: 5 genuine 'Term - idiom' entries
    (`Consumidor`, `Informe de consumidor`, `Agencia de informes de
    crédito`, `Identificación apropiada`, `Congelación por seguridad`),
    none of which contain a period anywhere in their own term span -- the
    `.-`-exclusion narrowing must not affect these at all. This is a
    REGRESSION GUARD, not a RED test: it already passes against today's
    unnarrowed code (verified directly, not assumed) and must keep passing
    after the Developer's fix -- included so a careless implementation of
    the narrowing (e.g. over-broadly excluding ALL periods from the term
    group, not just period-directly-followed-by-hyphen) cannot silently
    cost this real recall."""
    row = pr_rows["STATE_PR_LEY_236_2015_ART2"]
    candidates = extract_definitions_from_section(row["text"], scope="canonical")
    terms = {t for c in candidates for t in c.terms}
    expected = {
        "Consumidor",
        "Informe de consumidor",
        "Agencia de informes de crédito",
        "Identificación apropiada",
        "Congelación por seguridad",
    }
    assert expected <= terms, (
        f"expected all 5 genuine entries preserved, got terms={terms!r}"
    )


# --- Known, accepted residual limitation (NOT fixed by this narrowing) ----


@pytest.mark.xfail(
    reason=(
        "Accepted residual limitation of the cycle-7 `.-`-exclusion "
        "narrowing (M-R14 gate 1 / M-R15 step 1): an ASCII hyphen embedded "
        "in ordinary prose with NO period anywhere nearby -- a hyphenated "
        "proper name in a budget-appropriation article, not a Definiciones "
        "section at all -- shares no mechanical signature with the "
        "'.- Para propósitos de ...' class the narrowing targets, so it "
        "remains a live false positive. Documented and measured, not "
        "silently dropped from the precision report. A further, distinct "
        "signal (e.g. requiring the block to look like it opens a "
        "definitional sentence at all) would be needed to close this gap "
        "-- out of scope for this bounded gate; left for a future cycle "
        "if the residual junk rate on the canonical path (once P1 wires "
        "this live) proves unacceptable in practice."
    ),
    strict=True,
    raises=AssertionError,
)
def test_hyphenated_proper_name_remains_a_known_false_positive(pr_rows):
    """`STATE_PR_LEY_163_2005_ART2`: 'Se concede una asignación anual de
    setenta y cinco mil (75,000) dólares, al Consejo Juanadino Pro -
    Festejos de Reyes, Inc., para sufragar los gastos...' -- an ordinary
    budget-appropriation article (not a Definiciones section), containing
    the real hyphenated organization name 'Consejo Juanadino Pro -
    Festejos de Reyes, Inc.'. Both before AND after the cycle-7 `.-`
    narrowing, `_UNQUOTED_TERM_DASH_RE` still fabricates a ~99-char bogus
    'term' out of the narrative preamble by matching this hyphen. Written
    `xfail(strict=True, raises=AssertionError)` specifically so this
    residual gap is pinned and independently re-verifiable (by QA or a
    future cycle), not merely asserted in a docstring."""
    row = pr_rows["STATE_PR_LEY_163_2005_ART2"]
    assert "Consejo Juanadino Pro - Festejos" in row["text"]
    candidates = extract_definitions_from_section(row["text"], scope="canonical")
    # States the DESIRED future behavior (no candidate at all from a
    # budget-appropriation article) -- currently fails because the
    # hyphenated-proper-name class is a known, undischarged limitation of
    # this cycle's narrowing (see the xfail reason above).
    assert candidates == [], (
        "expected zero candidates once the hyphenated-proper-name false "
        f"positive is separately closed -- currently returns {candidates!r}"
    )
