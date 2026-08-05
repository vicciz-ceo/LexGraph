---
id: "2026-08-04-defs-us-preamble"
status: planned
blocked_on: null
current_role: developer
branch: claude/defs-us-preamble
worktree: /Users/nerya/LexGraph-wt/defs-us-preamble
locked_by: "/root/markers_panel_manager"
locked_at: "2026-08-05T21:44:41Z"
last_agent: "/root/markers_panel_manager/planner_cycle9_correction"
last_updated: "2026-08-05T21:57:23Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 3
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
lint: PASS
---

# Sprint: US body-preamble P-FP correction

## Governing decisions

P-FP measures a capture/extraction rule at persisted `(row, term,
definition_text)` granularity. Forwarding definitions are genuine under
D-MT-E1 and must remain captured. This sprint does **not** implement the
second D-MT-E1 requirement: a definition-to-target reference edge remains a
core shared dependency/held gate. D-INCLUDES authorizes B1 recognition of
`includes`/`shall include`; it does not authorize widening shared
`us_profile.py::_MEANS_IDIOM_GAP_RE`.

## Next Steps

1. **Four B1 causal fixes.** Allowed
   production surface: `backend/app/definition_links/rules/us_body_preamble.py`
   and, only if needed for the mandated <=300-line split,
   `backend/app/definition_links/rules/us_body_preamble_b1.py` (new).
   Preserve all five re-adjudicated genuine tuples. Make the real B1 call
   site recognize the bounded PA greedy-tail, USC `includes`, AR singular
   `purpose`, and OH intervening-divisions occurrences. Do not edit shared
   extraction or remove/change `_B1_FORWARDING_PHRASES`. Acceptance: the four
   REDs in `test_us_body_preamble_option_c_root_cause_red.py` go green; their paired
   full ingest+link guards remain green.

2. **M-R53 production-comment correction.** Remove the false corpus-wide
   uniqueness claim in `us_body_preamble.py` without changing runtime
   behavior. Acceptance: the focused test command retains exactly the four
   causal REDs before item 1 lands.

3. **Bounded B1 module split.** Split `us_body_preamble.py` from 386 to at
   most 300 lines without changing registration order or behavior. Acceptance:
   `wc -l` is `<=300` and all B1 integration tests retain their outcomes.

## Held dependencies / non-gates

- **Forwarding filter ledger (Option A):** retain every live forwarding filter.
  Full snapshot `301000fc…` scanned 105 parquet files / 2,046,009 rows at
  B1's actual filler/gap: `shall be as defined in` 12 hits/8 newly recognized;
  `shall have the same meaning as` 99/71; `has the same meaning as` 152/117;
  `has the meaning provided in` 17/14; `has the meaning found in` 0/0; `has
  the meaning stated in` 46/41. Therefore five of six observed forwarding
  phrases have nonzero current-corpus deltas; the 0/0 phrase is not load-bearing
  in this snapshot. Hazards: `shall not include` 182/74; `does not impair` 1/0.
  The 251 forwarding candidates and 74 exclusion candidates are HELD debt, not
  an authorization to remove filters.
- **CO wrong-tuple control:** `STATE_CO_T15_A11_P7_S15-11-701` proves that a
  B1-only removal would hand a forwarding-plus-exception body to the current
  extractor, which persists the exception rather than the forwarding target.
  Correct capture needs shared extraction plus D-MT-E1 reference-edge work and
  is out of scope.
- **T35 P-FP wrong tuple:** `USC_T35_C4_S41` has a real correct B1 occurrence
  and a later genuine `Director` definition, but body-wide extraction persists
  `SEC. 804. DEFINITION.` with 8,431 characters. B1 has no occurrence-level
  output, so this is held shared-extraction/P-FP debt, not a B1 Developer gate.
- **D-MT-E1 reference edges:** core shared reference-edge plumbing must add a
  link from each captured forwarding definition to its cited target. This
  sprint preserves the definition tuples but must not claim the edge shipped.
- **D-INCLUDES `References to`:** PA `STATE_PA_T15_C57_S5749` is an
  extraction-side held specification for the future `_MEANS_IDIOM_GAP_RE`
  owner. It is not a Developer gate here; no `us_profile.py` widening is
  authorized.
- Existing NE/SD unquoted markers dependencies are inherited and expected in
  the full backend baseline; they are unrelated to these Developer items.

## Evidence

- Focused inventory command returns **5 failed, 11 passed**: held T35 plus
  PA/USC/AR/OH B1 causal gates. Developer target is
  `backend/.venv/bin/pytest backend/tests/integration/test_us_body_preamble_option_c_root_cause_red.py -q` → four causal REDs.
- The five P-FP guards query persisted `Definition` rows and verify definition
  text; forwarding rows retain the real 31 CFR / IRC / 20 U.S.C. target text.
- Runtime-only mutation evidence (restored before every command): PA requires
  both a non-greedy trigger and a direct-`means` B1 branch; USC adds
  `includes|shall include`; AR adds `purpose`; OH adds the bounded divisions
  alternative. Each changes its named bounded B1 probe from `None` to
  `Definitions`; restoring returns all four to `None`.
- Full-corpus forwarding-filter measurement is recorded in M-R79; Option A
  holds filters unchanged because the required tuple preservation is shared
  extraction/reference-edge work, not a safe B1-only change.

## Stale-pin sweep

Searched every repo-profile root (`backend/tests/unit`, `backend/tests/integration`,
`backend/tests/e2e`, `frontend/src/components/__tests__`) case-insensitively
for the five replaced cycle-9 test names; no external pins found. No production
signature/class/CSS rename occurred.

## Context Dump

1. Start from four Developer causal REDs; T35 is a separate held extraction RED.
2. Fix B1 only; do not edit `us_profile.py` or shared extraction.
3. Keep forwarding tuples and name D-MT-E1 reference edges as core-held.
4. PA must make the real bounded B1 call return `Definitions`, not just shorten a regex.
5. Preserve the four paired full ingest+link guards.
6. M-R53 comment correction and the <=300 line split are still Developer work.
7. Full evaluator expected: four causal + held T35 + three NE/SD markers REDs.
8. Root owns integration/main-containment reconciliation and final QA dispatch.
