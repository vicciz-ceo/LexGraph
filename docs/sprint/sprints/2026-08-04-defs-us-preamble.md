---
id: "2026-08-04-defs-us-preamble"
status: review
blocked_on: null
current_role: qa
branch: claude/defs-us-preamble
worktree: /Users/nerya/LexGraph-wt/defs-us-preamble
locked_by: null
locked_at: null
last_agent: "claude:program-manager"
last_updated: "2026-08-09T20:30:39Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 7
completed_items: 0
dev_complete_items: 7
qa_cycles: 4
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
lint: "PASS 359 2026-08-09T20:32:38Z"
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

### M-R101 – M-R120 — superseded ruling chain (detail lives in the log)

Twenty reject/replan rounds between the Item-7 certification build and the
first executed full-population measurement. Their binding residue is carried
forward below and in M-R123; the complete text of each ruling stays in the
append-only log. Constraints that survive unchanged: no row-ID/hash/section/
term/date/title/exact-sentence keying and unseen-future-law direct plus
live-persistence controls (M-R107); `Vaquill-AI/open-us-law` is external, only
the `vicciz-ceo` fork is authorized, no upstream PR or Hugging Face publication
(M-R105); the B1 occurrence-metadata seam across `registry.py`,
`us_body_preamble_b1.py`, `us_profile.py`, and `pipeline.py` is authorized and
must stay backward-compatible for non-B1 rules (M-R106); no blanket HI,
large-row, quote, or `; and` suppression (M-R104).

### M-R121 — bounded certificate superseded by full-prototype evidence

M-R121's 556-key projection was independently byte-reconciled but never run
over the full normalized population. Its semantics remain binding; its ledger
is superseded where M-R122's raw-source inventory proves a conflict.

### M-R122 — provisional full normalized runtime-prototype correction

The reproducible persisted-record runner now applies the prototype over all
193,830 B1 winners (`851e85…6af5a`) against archived `5753e11` (592,694
records, `f065d8ee…b3f8`). All 207 c2-versus-M-R121 mismatches are classified:
188 certified removals contradict explicit raw-source relations (185 post-
quote, 3 pre-quote aliases); the remaining 14 missing and 5 extra removals are
one generic quote-direction defect. The corrected certificate is **368 = 364
removals + 4 additions**, SHA-256 `49a9d3f7…0933d`, with zero unexplained.
Production remains frozen at `c2a8717`; no identity exceptions are authorized.
The sole additional prototype/c2 mismatch is duplicate group discovery under
overlapping triggers; it has zero corpus impact but is pinned for future laws.

### M-R123 — M-R122 accepted, ported, and executed; the certificate is CLOSED

The program manager accepted M-R122 on independent evidence, not on the
outgoing Planner's summary. Four independent read-only auditors re-decided all
207 disputed keys against the pinned parquet: **207/207 excerpt-integrity
checks passed** (act_id, section_title, text SHA, span-exact excerpt, excerpt
SHA) and **205 agreed**. The five genuine definitions current production
deleted were source-read directly (PA `person in the position of a seller`,
FED `city`, TX `county judge`, OK `natural deterioration`, KY `telehealth`).

The Developer port landed at `941661b`: physical-line-start continuation
opener plus source-order exact-group dedup, module 295 lines. Gates, all
reproduced by the manager: focused direct+persistence 5F/49P → **54 passed**;
legacy raw provenance **13 passed**; runtime prototype **86 passed**; backend
**24 failed / 1199 passed**, exactly the accepted 23-marker + held-T35 ledger,
zero new failures; frontend **165 passed** and typecheck clean. The single
all-53 acceptance run reproduced 193,830 members (`851e85dc…6af5a`) and
592,334 records (`9e6e0196…22ca8`) against the 592,694-record `5753e11`
baseline (`f065d8ee…96b3f8`): **368 changed = 364 removed + 4 added**,
actual hash == certified hash == `49a9d3f7…00933d`, missing 0, extra 0. The
ported production output is byte-identical to the Planner prototype.

**No further re-adjudication of the 207 keys or the 368-key certificate is
authorized.** The certificate is executed evidence now, not a projection.

**Binding, and the reason this sprint circled: a changed-key certificate is
valid only when it was EMITTED BY an executed full-population run of the exact
implementation it certifies.** Hand-authored expected-change ledgers are
planning evidence, never gates. Adjudication decides whether each ACTUAL change
is correct; it never predicts the change set. Four projected ledgers
(636 → 586 → 556) were each superseded before this rule was applied; M-R121
froze 556 with "No all-53 run was made" and was wrong on 188 keys.

**Named residual — pre-quote alias mis-bodied tuples (NOT fixable in B1).**
The audit found a third class M-R122's two-bucket taxonomy cannot express:
right term, wrong body. Where the only preserving evidence is a PRE-quote
alias, the definiens sits before the quote while shared extraction harvests
after it, so a genuinely coined term is bound to unrelated text.
Verified in the acceptance record set for all three inventory members
(CO `25-3.5-108` "state report"; NM `73-7-1` "assessment of benefits." and
"assessments for construction."). Preserving them is still correct at B1
altitude — rejecting a genuinely coined term because the extractor mis-bodies
it is exactly M-R121's rule that deletes 185 real definitions. This joins the
existing held shared-extraction/P-FP debt beside the CO wrong-tuple control
and T35, and is owned by shared extraction + D-MT-E1, not by this sprint.

**G7 re-pin.** `qa_g7_common.INTEGRATION_SHA` still pinned `4fa9e7b…`, which
predates `c2a8717`, so every D-PFP-400 certification run fail-closed on
`validate_integration()` instead of measuring the tree under test. Re-pinned to
`941661b…`. The pin also seeds the D-PFP-400 sample rank, so the previously
recorded population/sample hashes are void and regenerated.

## Next Steps

_None. All 7 items are Dev Complete; QA cycle 5 owns the sprint verdict._

QA independently reruns the focused trio, the full evaluator, and the single
all-53 acceptance (production, **not** `--prototype`), then adjudicates the
regenerated D-PFP-400 sample. QA does NOT re-open the 207-key inventory or the
368-key certificate: disagreement with a closed, executed certificate is an
escalation to the program manager with source evidence, never a new ledger.

## Dev Complete

7. **D-PFP-400 certification + M-R122 source correction.** Certification
   entrypoint Q-D1 → Q-D2 → Q-D3 and the D-PFP-400 sampler are permanent and
   re-pinned to integration `941661b`. The one-file B1 correction is ported and
   executed: focused 54/54, legacy 13/13, prototype 86/86, module 295 lines,
   and the single all-53 acceptance at exactly 368 = 364 + 4 with
   `49a9d3f7…00933d`, missing 0, extra 0. Adjudication of the regenerated
   400-tuple sample is QA-owned and outstanding.

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
- Authoritative backend at `941661b` is **1199 passed / 24 failed / 18
  warnings**. The 24 failures are exactly the accepted ledger: 23 marker
  residuals plus held T35; the former NE x2, SD, and FED `eligible` release
  blockers are green. The M-R122 port adds zero new failures.
- Frontend is **25 files / 165 tests passed** and `tsc --noEmit` passes. Prior
  cycles recorded this gate as unrunnable because the worktree had no
  `frontend/node_modules`; `npm ci` was run there and it now executes locally.
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

## Evaluation Notes

- 2026-08-09 — QA non-B1 call-shape regression repaired. Hebrew live RED,
  11 QA provenance controls, and original focused gate are green (32 passed).

- 2026-08-06 — QA cycle 1 completed broad gates but held G7 because its three
  independent measurement scripts were unavailable; no regression reported.
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
- 2026-08-07T01:16:01Z — QA cycle 2 FAIL: pinned `STATE_HI_D2_T24_C431_S431`
  (`us_hi_statutes.parquet:5`, `2ff51dc5…`) is a 2,404,155-byte concatenation;
  live B1 emits its 529-char quoted indemnity provision as a term with `; and`.
  Root reproduced; remaining 400 review/all-53/full suites skipped fail-fast. New live RED is committed.

## Context Dump

1. All 7 items are Dev Complete at `941661b`; QA cycle 5 owns the verdict.
2. The 368-key certificate is EXECUTED and CLOSED — do not re-adjudicate it.
3. A certificate is valid only if an executed full-population run emitted it.
4. Membership 193,830 / `851e85…6af5a`; records 592,334 / `9e6e0196…22ca8`.
5. Only outstanding work is QA's D-PFP-400 sample adjudication.
6. `INTEGRATION_SHA` is re-pinned to `941661b`; old G7 sample hashes are void.
7. Pre-quote alias mis-bodied tuples are named held shared-extraction debt.
8. Escalate a disputed closed certificate; never author a replacement ledger.
