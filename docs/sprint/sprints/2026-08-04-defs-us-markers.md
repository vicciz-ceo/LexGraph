---
id: "2026-08-04-defs-us-markers"
status: in-progress
current_role: developer
branch: claude/defs-us-markers
worktree: /Users/nerya/LexGraph-wt/defs-us-markers
locked_by: "claude-code:planner"
locked_at: "2026-08-04T01:00:00Z"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 10
completed_items: 0
dev_complete_items: 1
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US family 3 — entry-marker mismatch (highest corpus impact)

## Mandate

The heading IS recognized as a Definitions section, but the extractor's
expected entry shape rejects the real body and yields zero. Sub-cases, all
confirmed live (dossier §2 family 3 + §6 addendum):
- **No-marker inline-quote** — `"As used in this chapter… \"Term\" means…"`
  with no `(N)` before the quote. Dominates VA (97% of 1,117 Definitions
  sections yield 0), WA (98% of 2,007), FED (84% of 1,949 — largest raw
  miss in the corpus), WV/DC minority. The EXISTING
  `_extract_inline_quoted_definitions` fallback rescues 77-93% of these but
  is wired to fire only on body-derived headings (dossier §6 finding #1).
- **Bare `(N)` numeric markers** (SC), **bare digit-dot** (AZ), **unquoted
  ALL-CAPS terms** (AL), **mojibake curly quotes** `\x80\x9c/\x9d` (AK, RI —
  RI's leading cause at 15%), **nested lettered sub-clauses under numbered
  entries** (UT, 24.2%), **colon-then-list** (TN), **ALL-CAPS singular
  "DEFINITION." + single inline entry** (TX), **prose bodies under matched
  headings** (OR), **unquoted-term definitions** (DC: `A bond… means…`).
Also owns the prior sprint's recorded residual: entry-boundary bloat/
truncation (Open-space purposes 21,174 chars; TX 17.33% degenerate recovered
terms) — "captured" means captured CLEANLY (right term, right boundary).

## Acceptance gates (program manager-defined)

- **U1 — Every sub-case above is captured cleanly**, RED tests from the
  exact recon rows (incl. `STATE_VA_T23.1_SI_C3_S23.1-300`,
  `STATE_CA_..._S54221`'s residual) before implementation. Entry boundaries
  are precise: no swallowed neighbors, no sentence-fragment terms, no
  degenerate near-empty definitions.
- **U2 — Scope stamped/enforced** where bodies carry scope preambles, via
  the core seam, live-path both directions.
- **U3 — Rules ship as registry modules**; zero shared-module edits; the
  fallback-rewiring decision is designed WITH the core panel (it currently
  lives in pipeline.py, which core is moving behind the seam).
- **U4 — Zero-miss sweep (director bar)** across all 53 jurisdictions for
  detected-heading-zero-candidate sections: each is captured or proven
  correctly-empty (pure cross-reference sections are correctly empty —
  document the classifier).
- **U5 — Nothing regresses**: baseline states hold; existing tests green;
  P-R2 escalation on precision conflicts.
- **U6 — Measured before/after**: per-jurisdiction zero-candidate rates for
  Definitions-headed sections (VA 97%→?, WA 98%→?, FED 84%→?) reported
  honestly on the full corpus.

## Coordination

Core sprint owns scope plumbing + registry + the pipeline.py extraction
migration — THIS sprint's fallback-rewiring overlaps core's C3 gate: the two
Planners must agree the boundary in writing (both contracts) before either
Developer touches it; disagreement escalates. Read core's `## Seam spec`
from branch `claude/defs-core-scope`; merge after core. Registry
registrations append-only. Out-of-family misses route via program manager.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings

Full text in `2026-08-04-defs-us-markers-log.md` §M1. Summary:
- **U-R1** — "captured" = captured CLEANLY (right term, right boundary);
  boundary quality is a measurable RED assertion, not prose.
- **U-R2** — the `_extract_inline_quoted_definitions` rewiring is a JOINT
  decision with the core panel; no Developer touches it before both Planners
  record the boundary in writing in both contracts.
- **U-R3** — the correctly-empty classifier is a Planner deliverable and is
  independently verified by QA.
- **U-R4** — P-R2 escalation per conflict class, with real statute rows.

## Boundary with core sprint (`2026-08-04-defs-core-scope`)

_Status: PROPOSED by this sprint's Planner (pass 1, 2026-08-04). **UPDATE
(pass 2, same day)**: core's `## Seam spec (published)` IS NOW LIVE on
`origin/claude/defs-core-scope` (polled this pass) -- `EntrySplitterRule`/
`TermClauseRule`/`ScopeTriggerRule` registry kinds, a profile-overridable
`normalize_for_parsing`, and `extract_definitions_from_section`'s
try-baseline-then-registered-rules dispatch all match what this sprint's
pass-1 proposal (c)(1)-(4) asked for. Full re-reconciliation against the
published spec (confirming waves 3/4/5/6/10 above each map onto a named
seam hook, and re-raising anything that doesn't) is NOT done this pass
(outside pass 2's assigned priorities) -- flagged for the next planner
pass or the sub-manager before any Developer starts implementation. No
Developer of ours touches shared modules until that reconciliation is
recorded (U-R2 still applies)._

**(a) What this sprint WILL touch**: only NEW files -- the wave-1 fixture
(`backend/tests/fixtures/us_statutes/us_markers_wave1_rows.json`) and test
file (`backend/tests/integration/test_us_markers_wave1_inline_quote_
fallback.py`), plus later waves' own new registry-rule modules (a
correctly-empty classifier module, a DC/AL non-quote-anchored extractor,
etc.) once C4's registry seam exists. We do not propose editing
`pipeline.py` ourselves.

**(b) What this sprint will NOT touch, because core owns it**: the
`_extract_inline_quoted_definitions` function body, the
`used_body_derived_heading` gate (pipeline.py:405-432), `_derive_heading_
from_body`, `_is_placeholder_heading`, and any other pipeline.py
jurisdiction-specific literal -- all exactly C3's migration target.

**(c) What this sprint needs FROM the seam** -- the exact hook shape our
rules need, derived from this pass's live findings, not guessed:
  1. A per-jurisdiction (or per-shape) **entry-boundary rule** that can be
     registered WITHOUT editing shared code: given a Definitions-section
     body and scope, return `list[DefinitionCandidate]` or "no opinion" (so
     the default `(N)`-block extractor still runs first, and this rule only
     fires as a fallback) -- this is exactly today's
     `_extract_inline_quoted_definitions` shape, just profile-owned and
     registrable per jurisdiction/family rather than pipeline-owned and
     globally gated on `used_body_derived_heading`.
  2. The rule interface must let us express an **idiom set per rule
     registration** (wave 2 needs `shall include`/`includes`/`shall be
     deemed to refer to` in addition to today's `means`/`shall mean`/`has
     the meaning`) and an **entry-boundary truncation point** (wave 1's FED
     fix needs to stop before an `Editorial Notes`/`Amendments`/`Statutory
     Notes`/`References in Text` marker even mid-body) -- both must be
     rule-local, not global regex edits, so one jurisdiction's idiom
     broadening never changes another's behavior.
  3. Confirmation whether `normalize_for_parsing` is overridable per
     profile (dossier §1 lists it as a Protocol method) -- if so, wave 4's
     RI/AK mojibake-quote fix can ship as a profile-level override,
     independent of C3/C4 timing; if the shared `normalize.py` function
     must be edited instead, that IS blocked on core and we need to know
     now, not when wave 4 starts.
  4. Confirmation whether C4's registry supports a rule that does NOT use
     quote-anchoring at all (DC unquoted-term shape, AL unquoted-ALL-CAPS
     shape, waves 5/9) -- i.e. whether the seam's rule shape is generic
     enough for a non-quote extractor, or whether it is quote-shaped by
     design and those two waves need a different seam hook.

**(d) The `used_body_derived_heading` gate: what happens to it, and who
removes it.** Live-measured this pass: naively deleting the gate (letting
`_extract_inline_quoted_definitions` fire for EVERY zero-candidate
Definitions section regardless of how the heading was found) is NOT safe
as a standalone change -- it would also fire the CURRENT, unmodified
function verbatim, which this pass proved produces real defects on VA, WA,
and FED (degenerate near-empty collapses, a phantom nested term, and
FED's editorial-notes swallow, all with real-row evidence in the sprint
log's §1). **Proposal**: core's C3 migration and this sprint's wave-1 fix
must land as ONE coordinated change, not gate-removal-then-separately-
patch-the-bugs -- whoever holds the pen when C3 lands should replace the
gate with the per-rule dispatch in (c)(1) above, with wave 1's boundary
fixes (idiom-gap tightening, nested-quote handling, notes-boundary
truncation) as part of the SAME change, verified by this sprint's already-
RED tests. We propose the core Developer implements the seam AND wires the
gate's replacement; this sprint's Developer implements the wave-1-specific
rule content (idiom sets, truncation markers) against that seam once
published. If core's Planner disagrees with this division, it escalates
per U-R2/P-R2.

Full supporting evidence (live re-confirmation table, cross-cutting
finding #1 full-corpus re-verification, the FED editorial-notes finding,
and the correctly-empty classifier) is in this sprint's log, `## P1 --
planner pass 1`.

## Next Steps

Ordered by corpus impact; full rationale and measured rates in the log's
`## P1`/`## P2` sections. Each item independently testable, each names
its gate(s). **Core's seam spec is now PUBLISHED** (`## Seam spec
(published)`, `origin/claude/defs-core-scope`, polled this pass) -- items
below note whether they land as a registry-rule module (`EntrySplitterRule`/
`TermClauseRule`, seam `rules/us_entry_marker_variants.py`) once core's
Developer ships C1-C4, superseding the earlier "possibly blocked" framing.
Not re-planned this pass (out of pass-2's assigned priorities); flagged for
the next planner pass or the sub-manager.

1. **Wave 1 [U1, U6] -- RED tests authored pass 1, still the correct
   contract.** No-marker inline-quote (VA/WA/FED) + boundary-precision
   guards. Corpus impact: 4,443 zero-candidate rows. **BLOCKED on the core
   seam** landing (touches pipeline.py's exact C3 migration target).
   Side-effect auto-rescue claim (UT/TX/AZ) -- **RED tests authored THIS
   pass, `test_us_markers_wave1_auto_rescue_subcases.py`** -- TX confirmed
   genuinely clean; UT and AZ needed CORRECTION (not rejection): both
   have their own boundary defect distinct from wave 1's known ones (UT
   swallows the next 2 entries when their idiom isn't "means"; AZ leaks
   the next entry's bare digit-dot marker, same defect class as item 3
   below) -- see log `## P2`.
2. **Wave 2 [U1, U4] -- idiom-set broadening.** Unchanged from pass 1.
   **BLOCKED on core** (same shared code area as wave 1).
3. **Wave 3 [U1] -- SC/AZ marker-splitter fix.** SC's bare `(N)` boundary
   noise + a SECOND, previously-unrecorded SC defect this pass (trailing
   "Effect of Amendment" commentary swallow); AZ's no-quote minority PLUS
   (new this pass) a marker-leak defect in AZ's own "auto-rescued"
   dominant shape (see item 1). **RED tests authored THIS pass** for SC,
   `test_us_markers_not_yet_rescued_subcases.py`; AZ's marker-leak guard
   is in item 1's test file. Likely ships as an `EntrySplitterRule` module
   under the now-published seam.
4. **Wave 4 [U1] -- RI/AK mojibake-quote normalization.** Corrected this
   pass: RI (`\x80\x9c`/`\x9d`) and AK (`\x93`/`\x94`) use TWO DIFFERENT
   mojibake byte sequences, not one shared shape -- a fix covering only
   one does not cover the other. AK's full-corpus rate (new measurement
   this pass): 766/767 (99.9%) zero-candidate, larger than RI's known
   15%. **RED tests authored THIS pass** for both,
   `test_us_markers_not_yet_rescued_subcases.py`. Per the published seam,
   ships as a profile-level `normalize_for_parsing` override -- confirmed
   available (Seam 1), not blocked on C3/C4 timing.
5. **Wave 5 [U1] -- DC unquoted-term + AL unquoted-ALL-CAPS.** Folded
   into one item this pass (both non-quote-anchored, same rule family).
   **RED tests authored THIS pass** for both,
   `test_us_markers_not_yet_rescued_subcases.py`. AL is the highest-value
   item in this whole list: 1,603/1,653 = 97.0% zero-candidate, full
   corpus. Ships as a `TermClauseRule` module under the published seam.
6. **Wave 6 [U1] -- TN colon-then-list.** **RED test authored THIS pass**,
   `test_us_markers_not_yet_rescued_subcases.py`. Note: the real row's
   `text` field itself carries a duplicated-content data-quality quirk
   (not injected) -- test asserts content presence + trailing-annotation
   exclusion, not an exact length; see the test's own docstring.
7. **Wave 7 [U1] -- OR prose-body boundary check.** Unchanged from pass
   1, not picked up this pass -- still needs closer inspection before any
   test is authored.
8. **VT overlap -- flagged to the program manager, not claimed.**
   Unchanged from pass 1.
9. _Retired as a separate item -- folded into item 5 above._
10. **Correctly-empty classifier, committed for real [U4, U-R3] -- RED
    tests authored THIS pass**, `test_definition_links_correctly_empty.py`,
    defining the required contract for a new
    `app/definition_links/correctly_empty.py` module (not yet
    implemented -- every test in this file currently fails with
    `ModuleNotFoundError`, deferred to test-run time so it doesn't abort
    collection of the rest of the suite). **Material correction to pass
    1's own classifier measurement, found this pass**: the cross-reference
    rule as pass 1 described it ("matched at the START of the stripped
    body") is dangerously over-broad -- it misclassifies wave 1's OWN
    flagship WA test row (2 real terms) and two real VA rows (46 and 7
    real terms) as "correctly empty". Corrected rule requires the ENTIRE
    body (minus an optional trailing `History:` annotation) to be nothing
    but the cross-reference sentence. Recomputed full-corpus rate: **WA
    4/1,778 (0.2%)**, not pass 1's reported 734/1,778 (41.3%); VA 0/1,065
    (0.0%), not 2/1,065. DC/WI/WY unaffected. Full detail: log `## P2`,
    fixtures README.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

New sprint. Planner: read program doc + dossier §2 family 3 + §6 addendum
(findings #1, per-jurisdiction detail), re-confirm examples live, author RED
tests. Largest-impact sprint in the program — plan waves accordingly.
