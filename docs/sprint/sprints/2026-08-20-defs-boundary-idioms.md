---
id: "2026-08-20-defs-boundary-idioms"
status: review
current_role: planner
branch: claude/defs-boundary-idioms
locked_by: "claude-code:qa"
locked_at: "2026-08-23T09:00:00Z"
last_agent: "claude-code:developer"
last_updated: "2026-08-23T09:00:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 3
completed_items: 3
dev_complete_items: 0
qa_cycles: 1
lint: "PASS 161 2026-08-23T09:20:45Z"
previous_sprint: "2026-08-12-defs-b1-refers-to"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: boundary-idiom widening — recover the 41 ceiling-tripped losses (issue #27)

## Mandate

GitHub issue #27. Forty-one (row, term) anchors produce no definition at all:
each is the LAST entry in its section with zero hard-stops found, because the
NEXT term's defining idiom (e.g. "shall include") is not in `_TIGHT_IDIOM_RE`
(`backend/app/definition_links/rules/us_markers_boundary.py:295` — currently
means | shall mean | has the meaning). With no boundary, capture runs to
end-of-text, exceeds `MAX_CLEAN_DEFINITION_LENGTH` (3,000 chars, line ~497),
and is correctly dropped by `close_entries` (~lines 640-693). The issue
owner's adjudication: all 41 are genuine runaway captures; the ceiling works;
the recovery path is idiom-vocabulary widening so a genuine closing boundary
is recognized. Raising the ceiling and scoping the guard are BOTH ruled out
(FX7 ruling, sprint 2026-08-10-green-the-suite: any guard-scoping broad
enough to recover the 41 flips the safety test RED — proven by QA).

Known examples: `USC_T5_C75_S7511` "furlough" (real def ~135 chars, captured
3,017), `STATE_NJ_T27_C1A_S1A-3.1` "Department" (real def one sentence,
captured 10,319). 2026-08-11 manager triage of all 66 affected rows:
41 ceiling-tripped / 25 present-but-shorter / 0 discriminator errors;
uncapped lengths min 3,017 / median 4,342 / max 11,730.

Director decisions taken: idiom list must be DERIVED from the 41 rows' actual
next-entry verbs (Planner enumerates the evidence; no guessed vocabulary).
Issue #26 stays deferred to its own sprint.

**AMENDED 2026-08-21 (director ruling, after the gate-2 footprint
investigation — see `2026-08-20-defs-boundary-idioms-scripts/investigation.md`):**
the widening's 130 collateral anchor losses trace to the pre-existing
fallback-suppression guard (`us_profile.py` ~2551: `if not candidates and
heading_was_derived`) — fallback definitions vanish the moment the primary
engine finds its first entry. Ruling: (a) fix that guard IN THIS SPRINT
(merge, don't suppress — Item 2); (b) also fix the ~9 degraded re-boundings
(investigation Q3: the "active efforts"-shape displacement family and the
NY "General service lamp" corruption — Item 3); (c) ONE combined
certification run ships only with ZERO genuine losses. Vocabulary itself is
vindicated: additions sample 80/80 genuine, re-boundings 97.6% improving.

## Acceptance gates (manager-defined, director-approved 2026-08-20)

1. **Recovery with correct text.** The 41 ceiling-tripped anchors are
   captured with text bounded at the true end of each definition. Any
   unrecoverable one is individually adjudicated with a stated reason —
   never silently skipped.
2. **Certified by execution (P-R11).** One full all-53 run; 100%
   anchor-granularity adjudication of the ACTUAL delta; measurement runs
   under the corrected convention — `--current` on BOTH sides of
   `measure_actual_production.py` (see Known traps).
3. **No collateral damage.** No existing correct capture is split by an
   idiom occurring INSIDE a definition body; every ADDED anchor in the delta
   is adjudicated genuine; P-R15 deletion-side screen clean. AMENDED
   2026-08-21: the combined run must show ZERO genuine anchor losses (100%
   of removals adjudicated; the 4 investigation-classified phantom removals
   are acceptable); the itemized degraded re-boundings (investigation Q3)
   must be fixed — no displacement or corruption ships. Additions and
   re-boundings are adjudicated by stratified sampling plus full-population
   structural checks per the investigation's methodology.
4. **The ceiling guard still works.** FX7 safety test
   (`backend/tests/integration/test_us_markers_fx7_ceiling_known_closed_scope.py`)
   stays GREEN — genuinely unbounded runaways are still dropped.
5. **No regression.** Full backend/frontend/lint green, explicitly including
   the boundary-engine guard estate: 16 c5guard class-B tests, the 5
   discriminator safety guards, the SC #28 run-membership test, the NV #25
   exclusion-bridge tests, and the module-docstring-pinned fixtures (AZ
   qualified actuary, UT Insolvent, VA sell, NV UCC, FED new drug).
6. **Red before green.** RED tests reproducing representative losses +
   novel structural controls (M-R107 — no jurisdiction/term/section keying;
   controls use unseen identifiers).
7. **Bounded.** AMENDED 2026-08-21: `git diff -- backend/app/` may touch
   `us_markers_boundary.py` AND the fallback-suppression guard site in
   `us_profile.py` (the `if not candidates and heading_was_derived` dispatch
   at ~2551 and, if the Item-3 diagnosis requires it, the term-set dedup it
   feeds — the Planner names the exact seam; anything beyond these escalates
   to the manager for a deliberate bound extension). Still forbidden:
   `_citation_or_xref_context`, `_extract_inline_quoted_definitions`'s own
   internals, and any B1 module.

## Rulings in force

P-R11, P-R12, P-R15, M-R107, D-RECALL-FP, D-MAP (see program doc and
handoff). FX7 prior ruling: ceiling-scoping not buildable as framed —
recovery goes through idiom vocabulary only.

## Known traps (do not rediscover)

- **Harness flags are part of the certificate**: `measure_actual_production.py`
  gates `recognized_by_registered_rule` on `--current`; production computes it
  unconditionally. Baseline runs MUST pass `--current` too, or the diff
  manufactures phantom deltas (proven in the #19 sprint — see
  `docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/investigation.md`;
  reusable corrected runner: that sprint's `run_gate2.sh`).
- "shall include" (and kin) commonly appear INSIDE definition bodies
  ("'X' means ... and 'Y' shall include ...") — this is exactly why the gate
  was kept tight. New idioms create new `starts` entries corpus-wide.
- `extract_quote_anchored_entries` returns (term, definition_text) tuples;
  a try/except-swallowing probe once manufactured a false "66/66
  discriminator errors" catastrophe — never swallow exceptions in probes.
- `qa_g7_common.INTEGRATION_SHA` re-pin + evidence regeneration whenever
  `backend/app` moves.
- Worktree venv: main checkout's venv with `PYTHONPATH=.:backend` from the
  worktree root; no `git stash`; raw-vs-ingest (escaped-\n) on raw parquet.

## Next Steps

_None — Items 1-3 moved to Completed._

## Dev Complete

_None._

## Completed

- **Items 1-3** — boundary-idiom widening + fallback-merge fix + dedup
  ordering fix (issue #27). PASS — all 7 gates independently re-verified
  (QA Notes below); 7 new regression tests, commit `a6ce3c0`.

## QA Notes

- 2026-08-23 qa cycle 1: independent evaluator PASS — backend 1401→1408
  (7 new QA regression tests, 0 failed), frontend 165/165, typecheck
  clean, contract lint PASS, zero flakes. All 7 gates independently
  re-verified from scratch: G1 exemplars/adjudication, G2 byte-identity +
  28,654-anchor re-derivation, G3 own seeded samples (10/10 removals
  phantom, 20 additions ~1 FP, tolerance) + swap-hazard/NV "X" checks,
  G4-G6 guard estate/FX7/provenance, G7 pin. Full transcript in `-log.md`.
  Items 1-3 → Completed.

## Context Dump

QA cycle 1 PASS, all 7 gates independently re-verified from scratch (not
reusing Developer's numbers) — full transcript in QA Notes above and
`-log.md`. Regression: 7 new tests, commit `a6ce3c0`; full backend
1408/1408, frontend 165/165, typecheck clean. Byte-identity to `f267644`
re-confirmed empty; `cc51c49` certificate (28,654 anchors) re-derived
independently, matches exactly. Named tracked debt confirmed, not
re-litigated (next-entry-bleed + 19 single-letter phantoms). Items 1-3 →
Completed; sprint → `review`. Next: Planner (director sign-off/close).
