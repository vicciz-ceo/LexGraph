---
id: "2026-08-04-defs-us-preamble"
status: review
blocked_on: null
current_role: qa
branch: claude/defs-us-preamble
worktree: /Users/nerya/LexGraph-wt/defs-us-preamble
locked_by: "/root/markers_panel_manager"
locked_at: "2026-08-05T21:44:41Z"
last_agent: "/root/markers_panel_manager"
last_updated: "2026-08-06T23:25:02Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 6
completed_items: 0
dev_complete_items: 6
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
lint: "PASS 188 2026-08-06T23:25:42Z"
---

# Sprint: US body-preamble P-FP correction

## Governing decisions

P-FP measures a capture/extraction rule at persisted `(row, term,
definition_text)` granularity. Forwarding definitions are genuine under
D-MT-E1 and must remain captured. This sprint does **not** implement the
second D-MT-E1 requirement: a definition-to-target reference edge remains a
core shared dependency/held gate. D-INCLUDES authorizes B1 recognition of
`includes`/`shall include`; core-2 G12's shared inline-extraction widening and
targeted `References to` guard are now main-contained, shipped, and read-only
for this sprint.

## Next Steps

## Dev Complete

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

4. **G8 shared local-scope dispatch repair.** A B1-derived heading must not
   turn ordinary `As used in this section` definitions from a clean local
   candidate into a trailing `law-wide` candidate. Planner first owns a new
   live ingest-to-link RED plus two-sided local/chapter and B1 controls. The
   accepted shared seam is `pipeline.py` only: only for a body-derived
   Definitions heading, emit registered local-scope candidates first, retain
   their first candidate per sorted-term key, then append existing
   definitions-section candidates only for keys not already owned. This
   preserves B1 and non-colliding section entries while preventing a later
   same-key law-wide candidate from entering persistence or Stage 3 linking.
   Registry order remains the local-candidate order; do not change generic G8
   persistence, profiles/registry APIs, or IL. Acceptance: clean local text
   and scope persist; an outside article gains no law-wide edge; a real GA
   chapter B1 preamble stays chapter-scoped; and a distinct section term
   survives. Core G8 reverse-order safety must remain green.

5. **NE/SD recognition and scope.** Release-blocker
   rows `STATE_NE_C43_S43-3329`, `STATE_NE_C44_S44-5003`, and
   `STATE_SD_T54_C14_S54-14-12.1` need independent raw recognition and raw
   extraction gates plus a live persisted `(term, definition_text, scope)`
   gate. Add only the exact `US-NE`/`US-SD` BodyPreambleRule conventions (no
   `US-*`); SD's “For the purposes of this chapter” must be chapter-scoped via
   a `US-SD` scope rule. Preamble Developer owns only
   `backend/app/definition_links/rules/us_body_preamble.py`. The all-53-file
   persisted-output measurement and every changed-key judgment are required
   before development; acceptance preserves the existing ledgers/gates.

6. **Exact markers splitters.** `USC_T43_C35_S1742a` must persist
   exactly the clean, law-wide `eligible`, `good Samaritan search-and-recovery
   mission`, and `Secretary` tuples. Markers Developer owns only two new,
   non-overlapping modules:
   `us_markers_ne_sd_unquoted.py` (exact source-bound `EntrySplitterRule`s
   only; no `TermClauseRule`) and `us_markers_fed_good_samaritan.py`.
   The FED rule is a US-FED-only `(a) Definitions` / `In this section:` exact
   shape: it requires exactly the three reviewed labels and
   terminates before top-level `(b)`. It is one priority EntrySplitter stream,
   not a profile fallback append or global parser. Measure both exact proposals
   across all 53 files at persisted `(row,key,definition_text,scope)` altitude
   and classify every changed key. Acceptance keeps G8 11, markers G3H 21,
   Option-C 5, G9, the exact 23-marker-plus-T35 hold ledger, and every
   existing RED intact.

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
- **D-INCLUDES `References to` (shipped G12 evidence):** the actual
  `_extract_inline_quoted_definitions` path suppresses PA
  `STATE_PA_T15_C57_S5749` via `_preceded_by_references_to` while retaining and
  emitting genuine USC `"United States" includes ...`. This is main-contained
  integration evidence, not a future held dependency or B1 Developer gate.
- NE/SD are no longer accepted inherited dependencies: the merged markers
  tree did not ship rules for them, and item 5 must close their live misses.

## Evidence

- Post-main Option-C integration is **5 passed**. Combined defining-verb plus
  Option-C is exactly **1 held-T35 failed, 15 passed**. The shipped core-2 G12
  unit file is **6 passed**; the repointed fifth Option-C pin drives the real
  inline extractor in both PA-suppressed and USC-emitted directions.
- Post-G12 FED/DC/NY integration is **4 passed**. Its green shared-boundary
  debt pin now follows the actual final candidate: `recreational purposes`
  remains swollen beyond 8,000 characters and contains both unrelated
  subsection headings. `wildlife` is only 70 characters but still carries
  `(4) The term`, so it is not described as fully clean.
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
- Integrated tip `4fa9e7b368801757039091646e06a832620a3a2c` contains both
  root-accepted Developer tips. The combined correction is **13 passed**; G8
  scope/collision is **11 passed**; markers G3H is **21 passed**; Option-C plus
  G9 is **6 passed**. Root independently reproduced the 13/13 combined gate.
- Authoritative backend is **1085 passed / 24 failed / 18 warnings**. The 24
  failures are exactly the accepted ledger: 23 marker residuals plus held T35;
  the former NE x2, SD, and FED `eligible` release blockers are green.
- Frontend is **25 files / 165 tests passed** and `tsc --noEmit` passes. The
  shared worktree is clean and local/remote tips match.

## Stale-pin sweep

Searched every repo-profile root (`backend/tests/unit`, `backend/tests/integration`,
`backend/tests/e2e`, `frontend/src/components/__tests__`) case-insensitively
for the six superseded cycle-8/9 Option-C and held-G12 test names: zero hits.
The sole stale held-G12 name was repointed in the owned Option-C file; the stale
FED debt-pin/capture-test names were repointed in their owned integration file.
No external pins remain and no production signature/class/CSS rename occurred.

## Context Dump

1. The four B1 causal gates are green; T35 is a separate held extraction RED.
2. Item 4 owns the shared B1-derived local-scope dispatch regression.
3. Keep forwarding tuples and name D-MT-E1 reference edges as core-held.
4. PA must make the real bounded B1 call return `Definitions`, not just shorten a regex.
5. Preserve the four paired full ingest+link guards.
6. M-R53 comments are corrected and the B1 facade is 259 lines.
7. Main-contained G12 is shipped integration evidence, not a held dependency.
8. Item 4's `pipeline.py` local-before-section canonicalization is integrated.
9. Items 5–6 removed the extras without expanding 24 holds; QA starts at `4fa9e7b`.
