---
id: "2026-08-04-defs-us-preamble"
status: dev-complete
blocked_on: null
current_role: qa
branch: claude/defs-us-preamble
worktree: /Users/nerya/LexGraph-wt/defs-us-preamble
locked_by: "claude-code:qa"
locked_at: "2026-08-07T01:02:44Z"
last_agent: "claude-code:qa"
last_updated: "2026-08-07T01:02:44Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 7
completed_items: 0
dev_complete_items: 7
qa_cycles: 1
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
lint: "PASS 285 2026-08-07T01:03:27Z"
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

### D-PFP-400 — strict definition-level false-capture gate (binding)

The director approved this manager recommendation with “fix this.” The
population is every definition newly persisted/captured by the final preamble
panel versus the documented BEFORE path on the same pinned 53-file snapshot,
at stable `(jurisdiction, source file/row id, term, definition_text, scope)`
granularity and using live persistence/dedup semantics. Forwarding definitions
remain genuine under D-MT-E1.

The evidence sample is 400 unique population tuples, or the whole population
when smaller. Ranking is deterministic SHA-256 seeded by the pinned corpus
snapshot plus integration SHA. Sampling must be jurisdiction-balanced and
stratified by extraction route and registered panel rule family: include every
non-empty jurisdiction, every live extraction route, and every registered
panel rule family; take all members of strata smaller than their allocation,
then fill remaining seats proportionally in deterministic hash order. Before
generating evidence, Planner must document the exact conflict-free allocation
algorithm for overlapping coverage requirements.

Fresh QA independently adjudicates every sampled tuple against its source. A
false capture means the row does not genuinely define or forward that term, or
the captured text is not the defining statement. Boundary overrun on an
otherwise genuine definition goes into a separate informational byte-quality
ledger and is not relabeled P-FP. PASS requires **0 false captures and 0
unresolved/ambiguous adjudications**; one false or ambiguous tuple blocks
merge. Commit the canonical sample, complete adjudication ledger, population
and sample canonical hashes, and the one-sided 95% upper bound (at 0/400,
`1 - 0.05^(1/400)`, about **0.75%**) without claiming corpus-wide zero.
G7 still requires GA-after `>=2794` and total `new_primary >=23617`;
`new_fallback` and byte quality remain informational. Production code is
read-only.

## Manager rulings

### M-R101 — prior Planner rejection (superseded by M-R102)

Root rejected `ca9dcd7` for duration-dependent hashes and incomplete
fail-closed finalizer/Q-D3/workflow guarantees. WIP `5355961` addresses much
of that ruling; full history is in the append-only log. It remains provisional.

### M-R102 — hardening WIP still not QA-ready

Root rejected `5355961` for exact-sample binding, self-referential verdict
hashing, and trusted component totals. Planner closed all three at `d0cecf2`;
full rejection/correction detail remains in the append-only log.

### M-R103 — Item 7 accepted for fresh QA

Root accepts cumulative Planner certification tip
`d0cecf285853fc6a16d784096d3532c920a85351`. The cumulative diff is confined
to tests, certification scripts/evidence, and sprint docs; `backend/app` is
unchanged. Root read hardening/micro diffs, found the risk grep empty, and
reproduced focused **11/11**, Python compile/diff checks, and evidence hashes.
The finalizer binds the verified exact 400 sample; Q-D3 recomputes component
rows. Item 7 is Dev Complete, not QA-passed: fresh QA still owns source
adjudication and the canonical verdict.

## Next Steps

## Dev Complete

7. **Permanent Q-D1/G7 certification infrastructure — root accepted.**
   Commits: `377bb796`, `b188b6b3`, `157b0ccd`, `6935abf9`, `ca9dcd78`,
   `2364972e`, `30da878b`, `53559619`, `6f7ee18c`, `d0cecf28` (accepted tip
   `d0cecf285853fc6a16d784096d3532c920a85351`). Root: focused 11/11,
   production unchanged, finalizer exact-400-bound, Q-D3 row recomputation.
   Evidence: Q-D1 `7269d7e02b44e08f3bb15048787a97c485e0adf3fde7c5f4c79dd70663f3a799`;
   Q-D2 `6138b58fafed100132c0aceb5830e38cc38ec7c6714bd0bbaf4f4b7421168e35`;
   Q-D3 `9ccb06cf78f8904e30338094fd600fc2bc42d8ccd8541c9eaa6ce2c8316a6725`.

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
- QA cycle 1 completed the focused, backend, frontend, all-53 exact-seam/hash,
  and broad-mutation gates at `ea0565059072d807a5f8564537917ca59b499a3f`.
  Binding G7 remains uncertified because its three independent QA measurement
  scripts were scratchpad-only and are gone; the committed widening measure is
  documented as approximate/non-gating and cannot substitute for Q-D1.
- The earlier Planner uncertainty is resolved by binding ruling D-PFP-400;
  sampling, adjudication, merge-blocking thresholds, confidence reporting, and
  preserved G7 volume gates are no longer open design choices.

## Stale-pin sweep

Searched every repo-profile root (`backend/tests/unit`, `backend/tests/integration`,
`backend/tests/e2e`, `frontend/src/components/__tests__`) case-insensitively
for the six superseded cycle-8/9 Option-C and held-G12 test names: zero hits.
The sole stale held-G12 name was repointed in the owned Option-C file; the stale
FED debt-pin/capture-test names were repointed in their owned integration file.
No external pins remain and no production signature/class/CSS rename occurred.

## QA Notes

- 2026-08-06T23:32:33Z — QA cycle 1 escalated after completing every focused,
  backend, frontend, all-53 seam/hash, and broad-mutation gate. G7 could not be
  independently certified: `qa_d1_measure.py`,
  `qa_d2_independent_denominator.py`, and `qa_d3_crosscheck.py` were ephemeral
  scratchpads and are unavailable. `measure_fp_after_widening.py` is explicitly
  approximate/non-gating. No production regression was reported.
- 2026-08-07 — PROVISIONAL/UNACCEPTED Planner Item 7 evidence at `ca9dcd7`:
  permanent Q-D1 → Q-D2 → Q-D3 entrypoint
  committed; it pins snapshot `301000fc…`, integration `4fa9e7b…`, 53 files,
  and 2,038,247 rows. Q-D1: before 29,698, after 156,322, new 126,624,
  primary 78,925, fallback 47,699, GA 2 → 3,093: both G7 gates pass.
- Q-D2: 99,877 candidates (57,094 captured / 42,783 uncaptured; quoted
  95,830, unquoted 4,170). Q-D3 PASS:
  `7e8eeafd85f41d00151174a9a0b9f4d319495abfcd84d5cdaf4b0ef57fb228d5`.
- D-PFP-400: 480,372 tuples (`08ca7a33…`); deterministic 400 sample
  (`880cdec8…`), 54 coverage seats then Hamilton allocation. All 400 ledger
  rows are `unreviewed`; Planner makes no P-FP PASS claim. 0/400 upper 95%
  bound is 0.7461%. Informational fallback byte ledger: 50 (`dc1fe464…`).
- Exact commands/all hashes: `...-scripts/G7_CERTIFICATION.md`; compact
  evidence: `...-scripts/g7-certification-evidence/`. RED was 3 failed;
  focused green is 7 passed. Stale-pin sweep: none. Production read-only.

## Context Dump

1. Items 1–6 remain Dev Complete; QA found no new production regression.
2. Root accepted Item 7 tip `d0cecf2`; all seven items are Dev Complete.
3. Root reproduced focused 11/11, compile/diff, hashes, and production isolation.
4. Q-D1/Q-D2/Q-D3 hashes are `7269d7e0` / `6138b58f` / `9ccb06cf`.
5. Fresh QA must rerun all-53 certification and independently adjudicate 400.
6. QA must retrieve sources, review immutable ledger, then finalize fail-closed.
7. D-PFP-400 passes only at 0 false and 0 ambiguous; no corpus-zero claim.
8. Production stays read-only; held ledger and all prior gates remain binding.
