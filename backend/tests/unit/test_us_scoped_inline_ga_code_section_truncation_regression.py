"""Sprint 2026-08-04-defs-us-scoped-inline, Planner pass 10, Task 2
(program ruling ESCALATION 2, 2026-08-05 manager log: "SHIP finding 4, PIN
the regression, ESCALATE the root cause upward").

*** KNOWN, ACCEPTED-FOR-NOW REGRESSION -- NOT AN ORDINARY BUG. READ BEFORE
TOUCHING. ***

Developer fix cycle 5, finding 4, widened `_UNIT_TAIL`
(`us_scoped_inline.py`) to tolerate Georgia's "Code section"/"Code
chapter" phrasing. Corpus-wide this is STRONGLY net-positive -- 3,605
distinct new terms gained across 1,527 GA rows, against 116 distinct terms
LOST across only 12 GA rows (a 31:1 ratio) -- and the director's ruling
was to SHIP it (reverting is not on the table; finding 4 is itself a
mandatory QA cycle-2 RED). But under this program's absolute zero-miss
bar, "net positive" does not make the 116 lost terms disappear, and they
must not quietly dissolve into a merged branch. This file exists to keep
them VISIBLE.

ROOT CAUSE (verified by this Planner pass, not merely accepted from the
Developer's report -- see below): `_leading_events` finds every
`_STRONG_TRIGGER_RE` match in a document and treats each as a NEW trigger
event; `extract_us_scoped_inline_definitions` then truncates event i's
capture region at event (i+1)'s start (`us_scoped_inline.py`:
`region_end = events[i + 1].start if i + 1 < len(events) else len(body)`).
Once "Code section" joined the trigger vocabulary, an ORDINARY mid-document
sentence that happens to contain "for the purpose(s) of this Code
section..." -- not a definitional carve-out, just ordinary cross-
referencing prose -- now ALSO matches `_STRONG_TRIGGER_RE`, manufacturing a
spurious SECOND trigger event that truncates the FIRST (correct,
full-spanning) trigger's region long before the colon-list it introduces
actually ends. Everything after the spurious truncation point is silently
lost.

THIS ROOT CAUSE IS PRE-EXISTING, NOT NEW, AND NOT GEORGIA-SPECIFIC --
independently verified by this Planner pass, not accepted on the
Developer's word alone:

1. The region-truncation mechanism itself (`region_end` bounded by the
   NEXT trigger event's start) is present, byte-for-byte, in this rule
   module's ORIGINAL authorship commit (`9c47af7`/`fcd2746`, "US family-1
   scoped-inline definitions rule") -- before ANY of this sprint's fix
   cycles, including finding 4, ever touched the file. Georgia's "Code
   section" widening did not create this mechanism; it only widened WHICH
   phrases can trigger it.
2. On THIS row (`STATE_GA_T14_C3_S14-3-140`), the fixture pinned below,
   re-running the real extraction with `_STRONG_TRIGGER_RE`/
   `_BARE_IN_TRIGGER_RE` swapped back to their PRE-finding-4 form (no
   "Code " tolerance in `_UNIT_TAIL`) still finds 37 distinct terms where
   today's shipped code finds only 9 -- because a SEPARATE, always-plain
   "for purposes of this chapter" sentence later in the SAME body (no
   "Code" needed at all -- "chapter" has always been in `_UNIT_ALT`) was
   ALREADY capable of manufacturing its own spurious truncating event, and
   the same truncation would recur for any state/row whose body happens to
   repeat a plain "for purposes of this section"/"as used in this
   chapter"-shaped sentence anywhere after its real leading trigger.
3. A corpus-wide scale probe (`si_cycle3_plan10_scale_scan.py`, this
   worktree's scratchpad; not committed) counted rows where the SHIPPED,
   real `_STRONG_TRIGGER_RE` matches 2+ times in one body (the exact
   structural precondition for this truncation) across all 53 real
   `vaquill/open-us-law` state files, 2,038,247 rows total: **38,431 rows
   (1.89% of the whole corpus) in ALL 53 of 53 states**, ranging from
   under 1% of a state's rows (e.g. MD, 0.16%) to over 10% (TN 10.66%, AR
   9.47%, GA 9.42%). This is not a Georgia footnote.

   A second, deeper probe (`si_cycle3_plan10_actual_loss_sample.py`, same
   scratchpad) checked whether the structural precondition actually
   costs real terms: 15 rows randomly sampled (seed 20260805) from EACH of
   the 5 highest-density states (CA/AR/TN/MA/GA), for each comparing the
   REAL shipped extraction against a "no-truncation" proxy (only the
   FIRST leading trigger event, region extended to the end of the body --
   i.e. what the row would capture if the spurious second event did not
   exist). Of 75 sampled at-risk rows, 2 (one CA, one GA -- different
   states, confirming this is not GA-only) showed real, measurable term
   loss under the proxy; the other 73 had a structurally-spurious second
   event that happened not to cost anything (e.g. it landed after the
   real list had already ended). That is a ~2.7% actual-loss rate WITHIN
   the at-risk population, not 100% -- but applied to 38,431 at-risk rows
   corpus-wide, even this conservative sampled rate extrapolates (roughly
   -- a real corpus-wide sweep was not run by this pass; treat this as an
   order-of-magnitude estimate, not a count) to on the order of
   1,000+ affected rows and plausibly several thousand lost terms
   PROGRAM-WIDE, not the 12-row/116-term Georgia-only figure the original
   escalation measured. The PROGRAM-WIDE zero-miss classification is
   confirmed by both probes; an exact aggregate count across all 53
   states is NOT done by this pass and is the natural next step for
   whoever owns the escalation.

ESCALATION STATUS: reported upward in the 2026-08-05 manager log
(ESCALATION 2) as a program-wide zero-miss class predating this sprint,
contingent on this pass VERIFYING the pre-existing claim and probing
scale. Both are now done (above): the claim holds, and the scale is large
enough (38,431 structurally at-risk rows / all 53 states / an
order-of-magnitude estimate in the 1,000+ affected-row range) that this
pass's own report to the manager leads with a fresh `ESCALATION:` line
per its own instructions, rather than treating this as GA-only follow-up.
This pass's job was to VERIFY the pre-existing claim (done, above) and PIN
the clearest row so the regression cannot be forgotten while a decision is
pending -- not to fix it (would require touching `backend/app/`, outside
this pass's fence) and not to re-litigate the ruling.

MECHANISM CHOSEN: `@pytest.mark.xfail(strict=True)`, the same tripwire
pattern this sprint already used for the S-R11 subsection interim
(`test_us_scoped_inline_pipeline_subsection_live.py`). Rationale: a plain
`@pytest.mark.skip` would make this regression invisible in a routine test
run (skipped tests are easy to stop noticing); an ordinary failing
assertion would make the WHOLE SUITE red today, which is wrong -- this is
an accepted, ruled-on, shipped tradeoff, not an open defect blocking work.
`xfail(strict=True)` gets both properties at once: it shows up as XFAIL
(not a silent pass) in every test report, so a reader scanning results
still sees "1 known regression, tracked here" -- and the day someone fixes
the truncation mechanism (region-splitting logic that can tell a genuine
list-introducing trigger from a spurious mid-document repeat), this exact
test starts PASSING, which `strict=True` turns into an XPASS **suite
failure**, forcing the fix to be reflected here (delete the marker,
promote this to an ordinary green regression guard) rather than quietly
sailing through unnoticed.

FIXTURE: `planner_pass10_ga_code_section_truncation_regression_rows.json`,
1 REAL row (`STATE_GA_T14_C3_S14-3-140`, O.C.G.A. Section 14-3-140,
Georgia Nonprofit Corporation Code definitions), full original 24-column
schema, values unmodified, independently byte-verified across 2 separate
fetches from this worktree's own read of the local, already-cached HF
snapshot (`~/.cache/huggingface/hub/datasets--vaquill--open-us-law/
snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad/us_ga_statutes.parquet`,
row index 9526; sha256 of the `text` column, both fetches:
`b657bcd2f22be52b7c637f5ebe16e986d58abba0a820a1d837e1e7be333592d3`) --
never downloaded, never read at test time (P-R9): the test below reads
only this committed JSON.
"""

from __future__ import annotations

import json
import pathlib

import pytest

FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "planner_pass10_ga_code_section_truncation_regression_rows.json"
)

# The 28 distinct terms this row's genuine "As used in this chapter, the
# term:" colon-list defines AFTER the spurious "for the purpose of this
# Code section, rights shall be considered..." mid-document trigger event
# (position ~2509 in the body) truncates the real trigger's region.
# Derived by re-running the REAL, unmodified extraction against this exact
# row with `_STRONG_TRIGGER_RE`/`_BARE_IN_TRIGGER_RE` reverted (in-memory
# only, never touching `backend/app/`) to their pre-finding-4 form (no
# "Code " tolerance) -- that reverted run captures 37 distinct terms;
# today's shipped code captures only 9; these 28 are the set difference.
# (The manager log's headline figure, "116 distinct terms lost across 12
# rows" corpus-wide, is a candidate-level count across 12 rows -- this
# row's own ~26-candidate/28-term contribution is consistent with it.)
_TRUNCATION_LOST_TERMS = frozenset(
    {
        "Corporation",
        "Delegate",
        "Deliver",
        "Document",
        "Effective date of notice",
        "Electronic",
        "Electronic network",
        "Electronic transmission",
        "Entity",
        "Foreign business corporation",
        "Foreign corporation",
        "Foreign limited liability company",
        "Governing agreements",
        "Governmental subdivision",
        "Individual",
        "Joint-stock association",
        "Limited liability company",
        "Limited partnership",
        "Mail",
        "Member",
        "Membership corporation",
        "Notice",
        "Person",
        "Principal office",
        "Proceeding",
        "Record date",
        "domestic corporation",
        "electronically transmitted",
    }
)


def _rows() -> dict[str, dict]:
    return {r["act_id"]: r for r in json.loads(FIXTURE.read_text(encoding="utf-8"))}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN, ACCEPTED-FOR-NOW regression (manager log 2026-08-05, "
        "ESCALATION 2): Developer fix cycle 5 finding 4 (Georgia 'Code "
        "section' support) is net strongly positive corpus-wide (3,605 "
        "distinct new terms / 1,527 rows gained vs. 116 distinct terms / "
        "12 rows lost, 31:1) and SHIPPED per director ruling, but the 116 "
        "lost terms are a real, measured, NEW miss under the absolute "
        "zero-miss bar. Root cause (verified pre-existing, not "
        "Georgia-specific -- see this file's module docstring): a "
        "mid-document sentence that incidentally matches "
        "_STRONG_TRIGGER_RE (here, 'for the purpose of this Code "
        "section, rights shall be considered...') manufactures a "
        "spurious trigger event that truncates an earlier, correctly "
        "full-spanning trigger's capture region "
        "(us_scoped_inline.py:extract_us_scoped_inline_definitions's "
        "`region_end = events[i + 1].start...`). Escalated upward as a "
        "program-wide zero-miss class predating this sprint; fixing it "
        "requires touching backend/app/, outside this Planner pass's "
        "fence. This test asserts the CORRECT, desired behavior (all 28 "
        "genuinely-defined terms captured) so it fails today for the "
        "documented reason above -- the day someone lands a fix that "
        "distinguishes a genuine list-introducing trigger from a "
        "spurious mid-document repeat, this test starts passing, which "
        "turns into an XPASS suite failure under strict=True, forcing "
        "this marker to be removed rather than the fix going unnoticed."
    ),
)
def test_ga_code_section_truncation_does_not_lose_the_later_colon_list_entries():
    """`STATE_GA_T14_C3_S14-3-140`: a real, single "As used in this
    chapter, the term:" colon-list defining dozens of terms for the
    Georgia Nonprofit Corporation Code. Byte-verified real corpus row (see
    module docstring for sha256 + two-fetch provenance). Today, a spurious
    second trigger event -- an ordinary mid-body sentence, "For the
    purpose of this Code section, rights shall be considered the same
    if...", which only became trigger-shaped once finding 4 widened
    `_UNIT_TAIL` for "Code section" -- truncates the real trigger's region
    at char offset ~2509, long before the colon-list it introduces
    actually ends, silently dropping every entry after that point. RED
    today (only 9 of the row's genuine terms survive); see the `xfail`
    marker above for why this is tracked, not silently accepted."""
    from app.definition_links.rules.us_scoped_inline import extract_us_scoped_inline_definitions

    row = _rows()["STATE_GA_T14_C3_S14-3-140"]
    candidates = extract_us_scoped_inline_definitions(row["text"])
    captured_terms = {t for c in candidates for t in c.terms}

    missing = _TRUNCATION_LOST_TERMS - captured_terms
    assert not missing, (
        "expected all 28 genuinely-defined, truncation-lost terms to be captured -- "
        f"still missing {sorted(missing)!r} (captured: {sorted(captured_terms)!r})"
    )
