# Program log — 2026-08-04-definition-completeness (append-only)

Internal orchestration records. Not auto-loaded; not director-facing.

## Agent roster (role → agentId, for same-session resume)

- 2026-08-04 recon workflow #1: wf_aba457ee-0d4 (6 agents, complete; B3 non-delivery)
- 2026-08-04 recon workflow #2 (B3 re-run): wf_7f1827d1-1a7 (running)
- 2026-08-04 panel manager, defs-core-scope (opus): abb036d8b5a387023
- 2026-08-04 panel manager, defs-il (opus): ae31f4f535cd44786
- 2026-08-04 panel manager, defs-us-scoped-inline (opus): a735e7fdf23ed62f9
- 2026-08-04 panel manager, defs-us-preamble (opus): a3adfb6a9000b266e
- 2026-08-04 panel manager, defs-us-markers (opus): a77bfa457162d6951
- 2026-08-04 panel manager, defs-us-headings (opus): a5e7bb61c9278644e
- 2026-08-04 panel manager, defs-us-multiterm (opus): a007e4bbf7f366192
- 2026-08-04 panel manager, defs-us-pr (opus): a0f33c079eda12235
- 2026-08-04 core QA-phase manager (opus, fresh context after impl-phase
  manager clean-exit): a9efb2de1f275f494
- 2026-08-04 headings phase-2 manager (opus, fresh context after
  predecessor context-limit exit): aa5eb2a338fe6b0ab
- 2026-08-04 PR phase-2 manager (opus, fresh context after predecessor
  rebased onto merged core and clean-exited): a79f6fed9fced34da
- 2026-08-04 core dispatch phase-3 manager (opus, fresh context after
  phase-2 manager clean-exited at its named context line, pre-final-batch):
  adb9a8660bd062f7f
- 2026-08-04 IL phase-2 manager (opus, fresh context after predecessor
  clean-exited post QA cycle 2; runs Phase C): aebd052825067b722
- 2026-08-04 scoped-inline phase-2 manager (opus, fresh context after
  predecessor clean-exited post QA cycle-1 bounce): a1b29c30b33e45591
- 2026-08-04 headings phase-3 manager (opus, fresh context after phase-2
  manager context-exhausted clean exit @ b79f588; runs dev cycle 5 + QA
  cycle 4): a1d2487867915919a
- 2026-08-05 core follow-on-2 panel manager (opus, fresh; sprint
  2026-08-05-defs-core-follow-on-2, gates G1–G7, merges first):
  afa01292edb77329b
- 2026-08-05 markers phase-2 manager (opus, fresh after predecessor
  context-exhausted clean exit @ c4baf7ce; QA + 10-jurisdiction
  extension): a2ef4b689a844a074
- 2026-08-05 IL phase-3 manager (opus, fresh after phase-2 clean exit @
  64932d7; runs D-1 serialized Developers + QA cycle 4 + certification
  contract draft): a18597f9be6c49ed6
- 2026-08-05 multiterm phase-2 manager (opus, fresh after predecessor
  context-exhausted clean exit @ af0d548; runs M-R17/M-R18/rule-rename
  Developer pass + re-measure + QA cycle 2): ad9cf6f6c6a351c50
- 2026-08-05 markers phase-3 manager (opus, fresh after phase-2 handover
  @ c6732e3; runs U-R14 disposition + QA cycle 2 + merge readiness):
  a5c69b8e918e550cf

## Wave 3 checkpoint (2026-08-04, post-P-R8 repair + implementation wave)

Dispatch sprint: 26-RED map complete (count corrected from my 30 by the
manager's real run); all 7 kinds implemented live on both profiles
(733/0, dev branch, under verification); I9 Maine-annotation item added
(RED-first, parallel Planner); seam v2.6 (M-D1 StructuralUnitRule =
article-metadata enrichment; M-D2 ScopeKindRule first-non-None-wins).
Implementations landed: PR items 18a/26/27/28/29 (35/910 exact, verified
to bytecode level, hyphen-regression self-caught); scoped-inline family-1
rule (33/38 green, 5 stale pre-S-R9 pins routed to Planner pass-3); IL
buildable set (item 10 incl. the 2,335-occurrence בסעיף זה population).
IL QA cycle 1: honest I4 FAIL — ~4,859 buildable misses via P-R7 sweep
(canonical case: tzere-spelling לעניין זה, 1,702 occ dropped for one
letter); ::- shape 0.5% captured; 3 FPs; I1 count corrected +331 exactly
matching P-E3 (independent confirmation of core's bare-@ fix). Ruling:
takana=local-if-parsed (evidence-conditional); full fix-cycle go.
Infrastructure: 6 stream-stall deaths in one window, all recovered at
zero loss (commit-before-spawn + verified-state discipline). Rulings
added: P-R10 probe-sanity; PR 18c Option D (residual dissolves
post-dispatch); D-DF two-rule decomposition pinned.

## Wake wave (post core merge, 2026-08-04)

Core merged to main @ 06d67d8 (program-manager checklist run: containment
probe, risk-classed materialized diff read incl. full persistence hunks,
risk grep all-benign, own full evaluator 700/0/165/tsc on merged tree;
main venv refreshed for mcp>=2.0). All six family panels woken in one
wave with: seam v2.5 re-read requirement, rebase+venv instructions,
panel-specific rulings (D-DF, D-HG, D-PR-A, D-PR-18c, P-E3 corrected
facts, AK cp1252 fact, NY-fix baseline note), and routing artifacts
(CLAUSE package, guarded-cluster doc). Note: the "injection-styled"
messages re-QA disclosed are identified as the harness's benign
file-changed notices (program manager received the identical notice
verbatim during the merge) — no tampering; recorded closed.

## Events

- 2026-08-05 (truncation class ruled + preamble certification withheld):
  SCOPED-INLINE escalated the trigger-region truncation class with full
  verification: mechanism predates the sprint (two-commit proof at
  9c47af7/fcd2746, line 271 region_end), structural precondition in
  38,431 rows / 53 of 53 jurisdictions, real loss measured in CA AND GA
  (~2.7% of at-risk; order 1,000+ rows extrapolated from 75 sampled —
  labeled extrapolation, not count; 37-vs-9 exemplar row). RULED: class →
  D-CERT worklist as named/verified/self-alarming-pinned (xfail(strict)
  containment); exact sweep folds into the US certification build; the
  FIX (list-introducing vs mid-document-carve-out trigger classification —
  architecture-level, cross-panel) → core-follow-on-3 with all evidence
  attached. Not this cycle's work; nothing lost silently. PREAMBLE
  withheld its own certification: shape-3 FP measured 18% (~3,100 rows)
  + em-dash 14% — colon-list branch lacks its siblings' self-verification
  (the five self-verifying shapes all measured 0%); narrower-rule remedy
  in cycle 8 with the recall side of the trade to be measured; manager
  superseded its own 836 figure (undisclosed scan window; 984 is the
  load-bearing number); QA mutation-test found the working forwarding
  filter pinned by NOTHING (deletable green) — pin commissioned. CORE-2:
  G5+G6 green 8/8 with G6 shipped as 7-of-8-rows + TN named gap (seam
  v2.8 row-7 "proven" claim corrected in v2.10); G12 merged with
  real-data proof of the boundary+emission ruling (IL terms silently
  dropped today); (b)/(c) dispatch changes → core-3 with the 1-of-8
  number. IL: או-gap corrected downward by its Planner (230 shapes → 20
  lines/13 files reaching the broken path); INTERPRETATION LAWS finding —
  חוק הפרשנות art.3 and פקודת הפרשנות art.1 whole definitions lists
  unreached (no preamble) → certification worklist.

- 2026-08-05 (multiterm manager clean exit @ af0d548): context limit;
  suite 13/804, tree clean. Exit highlights: M-R19 — Planner overruled the
  manager on the 5-TX-duplicates test split and was RIGHT (4 of 5 are
  ledger R1/markers-owned, proven by excluding F6 and re-running; one
  combined test would have implied M-R18 fixes all five); the rule.
  hardcoding spans FOUR files not three (manager found the fourth in the
  Planner's own U-R10 file); standing lesson recorded — three worst
  defects were correct-in-isolation/wrong-in-composition, and the suite
  was green while shipping a duplicate-emission regression (corpus
  re-measure + a Planner refusing to test around an inconvenience found
  what the gates could not). U4 CANNOT CERTIFY yet (2 seam-blocked gaps on
  core G10). Open work by owner in the contract Context Dump. Phase-2
  successor spawned (roster).

- 2026-08-05 (HEADINGS QA-CERTIFIED — first family panel to certify):
  claude/defs-us-headings @ 60c0652, suite 860/0, recall 21,080/22,228 =
  94.8353%. All six gates pass; U4 = PASS-WITH-NAMED-RESIDUAL (full 1,148
  residual classified, buckets sum exactly; 3-row L12 residual named —
  unfixable in-panel: needs shared-module edit or D-HG relaxation, both
  forbidden); U5 = zero FP flips across all 1,931,308 non-defin-titled
  rows; U6 = WA 74.26→98.64, FL 84.56→98.74, NY 91.35→98.76, zero H-R3
  violations across 46 states. Convergence signal: FIRST cycle finding no
  new mechanical gap class (cycles 2/3/convergence-scan each found one);
  the 100-row unassigned bucket resolved entirely into known shapes.
  Cross-ledger insight for D-CERT: L12's 3 rows + L7's 2 remaining are ONE
  exclusionary-verb class ("does not include" — outside both panels'
  vocabularies) → single D-CERT item, not five orphans. Queued unblocked:
  item 16 (includes widening), L1 on core-2 G11, L9 on core-2 G6. Manager
  re-ran load-bearing claims incl. re-fetching L12 rows live; merge
  conflict in log resolved as union with zero-loss verification.
  qa_cycles 4/5, valve unused. Merge-queue position: after core-2 →
  markers → preamble per standing order.

- 2026-08-05 (milestone batch, post-harness-adjustment): CORE-2 @ e4032c7 —
  G2+G4 resolver fixes merged (SC connector chain solved; i9 test's
  docstring found to misdescribe its own fixture — load-bearing error,
  routed to plan1); G11 ruled DO-NOT-SHIP-ALONE (ships only with G12 +
  G3-sibling); G12 opened (includes boundary+emission under D-INCLUDES —
  manager chose emission over boundary-only on the inversion argument:
  boundary-only converts visible contamination into silent drops); G5+G6
  implementation spawned. SCOPED-INLINE @ 6b45c52 — pass-9 pin re-author
  verified; Planner found 2 more PA rows ("references to \"the
  corporation\" include") whose protection would evaporate under cycle-5's
  finding-5 connector widening — guard requirement routed to the Developer
  mid-flight with proof obligations. MARKERS @ 8edc197, 15/877 — Developer
  B's 4 modules: MN 91.7→4.6%, ME 99.9→3.9%, OH 99.9→6.7%, NY 217→298
  captured, MI 1,763 unchanged; two oracle rulings (U-R12 green-for-wrong-
  reason AZ test to QA re-author; U-R13); FED "26,028 swallow" in the
  module's own docstring found to be a genuine enumeration, never a swallow
  (5/42 spot-checked, 37 to QA). PROCESS FINDING worth keeping: markers
  Developer B REFUSED the delivery boilerplate as a suspected injection
  lure (raw id + urgency + "your normal channel is unreliable" is the
  exfiltration shape) and delivered via the normal path — correct instinct,
  fails safe; the manager's refinement is the durable fix: anchor the
  delivery instruction to a COMMITTED artifact the agent can verify in its
  own worktree (applied to its next brief; recommended to all panels as
  they next spawn). Manager also self-corrected an M19 role error (had
  planned to apply the tuple-widening itself — production code is not
  manager work; re-dispatched as Developer C).

- 2026-08-05 (HARNESS ADJUSTMENT, director-ordered): role agents now
  interact DIRECTLY with their panel managers, not through the program
  manager. Mechanism: manager-to-manager SendMessage by raw agentId is
  proven working in this session; the agent→manager direction failed only
  because role agents were never given their manager's id. Effective
  immediately, every panel manager embeds its own agentId in EVERY role
  agent brief with the instruction to deliver the full report/escalation
  via SendMessage to that id BEFORE returning (the plain-text final return
  is not a reliable channel). Escalations resolve at the panel manager,
  which escalates onward itself when needed. The program manager no longer
  relays; stray completion notifications reaching its session are
  forwarded as bare pointers ONLY if apparently undelivered (in-flight
  agents briefed before this change will still return through the old
  path until the fleet turns over). Broadcast to all 8 active managers
  with their ids. Complements the director's micro-management correction
  (program manager intervenes only on escalation, cross-panel
  arbitration, director rulings, and merge duties).

- 2026-08-05 (WA_T50 routing CORRECTED + the heading_was_derived gate,
  G11 candidate): headings manager falsified the rerouting with a
  layer-by-layer live trace — STATE_WA_T50_C29_S030's title IS
  recognition-covered ("\"Wages\" defined for purpose of..." → panel
  defined-for rule True); the failing layer is the heading_was_derived
  GATE on the inline-quote fallback in core-owned us_profile: the flag is
  True only on the body-derived-heading path, so registry-recognized
  headings get False and the fallback NEVER RUNS. extract(...,
  heading_was_derived=True) yields "wages"; False (the live value) yields
  0. BOTH panels' probes were right and BOTH diagnoses wrong (markers' QA
  drove extraction with the non-live flag value) — program lesson
  recorded: probe ARGUMENTS are part of the claim; my relay propagated
  the wrong diagnosis. QUANTIFIED: over defin-titled rows, 82,155
  live-recognized / 53,918 zero on the live path / 39,955 RESCUED by
  flipping the flag — the gate alone explains 74.1% of zero-yield (NV
  8,555, NJ 2,650, AZ 2,645, MI 2,205, WA 2,044). Reconciles with recon
  §6 finding #1 (the known existing-but-unwired fallback) — this NAMES
  the specific gate and sizes it. CAVEAT recorded: 39,955 (defin-titled
  population) and 12,869 (shape-1 bucket A) OVERLAP UNMEASURED — never
  add them. ROUTED: G11 candidate to core-2 (shared module; largest
  single lever measured in the program) with a BINDING both-sides
  condition — the gate presumably exists for precision on the
  body-derived path's messier inputs; find the original rationale (git
  history/comments) and measure what the fallback would capture on
  registry-recognized rows (FP side) before any flip; a per-call-site or
  per-origin loosening may be sounder than removal. MARKERS impact: the
  10-jurisdiction extension denominators must be RE-MEASURED under the
  gate-fixed assumption before building (much of PA1's worklist may be
  gate-rescued; PB1's MN/ME/OH boundary defects are gate-independent) —
  their manager sequences with core-2. WA_T50 itself: closes when G11
  lands; headings' reference-edge verification queues on it.

- 2026-08-05 (mega-wave: D-INCLUDES + 4 core-2 planners + markers QA1 +
  scoped-inline QA2 bounce + IL handoff + seam defect): Director ruled
  D-INCLUDES (recorded in program doc). CORE-2: all four Planners landed —
  plan1 @ 6455318 (G2 8 REDs; before/after prototype 8.4%→0.64% corpus,
  ME 81→0.2%, AZ 69.7→0.2%; G4 scale proxy 42%/34% PROVISIONAL; SC
  "or"-chain hazard named), plan2 @ 6abe042 (G3 content-marker design with
  both-sides sampling: narrow 13.54%/extended 24.62% of 27,051 last
  entries contaminated; G1 2 REDs + 5,423/242,193=2.24% padded terms
  [NC 55%, WY 61.6%, NM 79.8%]; DC 27.3% PROVEN unreachable by G3 —
  202/332 quoteless + 130/332 blocked by "The term " lead-in before quote;
  sibling _extract_inline_quoted_definitions has identical defect, IL
  71.4% contamination), plan3 @ 65c6336 (G5 reframed as bound-resolver
  field; G6 seam v2.8 additive detect_value/ScopeAssignment/
  determine_scope_assignments; 8 REDs; 10-row table corrected to 8 — NJ/UT
  not value cases), plan4 @ f27299c (G8: baseline collides with ITSELF —
  AR corpus duplication artifact; 2,282 rows/34 jurisdictions; 745
  containment-unambiguous vs 2,307 benign vs 1,308 ambiguous;
  design=strict-substring UPDATE path, ordering-flip and length-threshold
  REJECTED with data; G3-independence proven structurally 0/4,360).
  Markers manager sized collisions independently: 213 severe (TN 146/FED
  51), worst discarded improvement 163,875 chars (USC_T5_C83_S8331); TX
  labeled unclassified not counted. PROGRAM RULINGS: Q-G3-A = YES, sibling
  in G3 scope (one shared termination helper), CONDITIONAL on a sampled
  both-sides check for the fallback population before building; Q-G3-B =
  DC de-linked from G3 (merge-protocol pass condition amended: G3 proves
  FED RED green + corpus last-entry contamination near-zero; DC's real
  shapes routed — "The term" lead-in = markers TermClauseRule family
  [QA1 Q7 NC/DC shape], quoteless = unquoted family); G9 CANDIDATE added
  (IL M20 breadcrumbs data source: pipeline.py:212 hardcodes (),
  sections.py:138 len==2 gate; 2 committed REDs on claude/defs-il); G10
  CANDIDATE added (multiterm escalation, proven from source:
  TermClauseRule.parse receives block string only, us_profile.py:1351
  drops the scope the dispatcher HAS → every panel's TermClauseRules stamp
  law-wide; silent wrong-scope winner confirmed on real IN row; fix =
  thread scope to parse, seam version bump) — core-2 manager has
  accept/defer authority per gate with reasons. CORE-FOLLOW-ON-3
  accumulator opened: AZ bare-digit-dot sibling-swallow, WA mid-paragraph
  markers, MI spaced "( l )" markers, CT "Term:" convention + "Cited."
  annotations, AL nested-sub-list mis-split (markers QA1 Q2). MARKERS:
  QA1 PASS @ b294091 (6 defects pinned; Q3 = NEW bug in markers' OWN
  _TRAILING_MARKER_CHAIN_RE stripping NNN.NNN. citations, 1,842/144,706 =
  1.27%, TX 4.50% — most consequential, theirs to fix; Q4 ceiling: 1,308
  dropped, VA ~3,020-char row proven genuine; Q5 WA row: extraction
  PROVEN clean when driven directly — gap is 100% recognition-side →
  REROUTED to headings [supersedes the H-R1 markers routing, with
  evidence]; Q7 family-scoped miss 1.4% lower bound + NC/DC lead-in shape
  named); PA1 @ 25eebf6 (28 guard pins; 83–96% of five guard states'
  zero-yield is the SAME quote-anchored convention — tuple extension not
  new modules; 8 REDs); PB1 @ dfd5473 (NM/MN/ME/OH collapse into
  inline-quote family with 3 new boundary defects; NV = 2 stacked cheap
  gaps ~95%; NH/HI join, MA/PA need dedicated modules; 6 REDs).
  SCOPED-INLINE: QA cycle 2 BOUNCE @ 162f987 (U4 FAIL: 6 new
  in-vocabulary misses pinned RED — "the term(s)" before quote 12,189
  hits/52 states, shall-include 6,926/50 [now AUTHORIZED under D-INCLUDES
  with the References-to guard], and-chain, GA "this Code section" 1,299
  rows, boilerplate-connector break 2,113, second-entry drop; U6 honest
  number = 314,139 distinct not 359,437 raw; S-R12 census 34,972 events 0
  disagreements; D-S15 live: 4,034 recovered/143 regressed/1,924 genuine
  under-links remain; item-5 population DISCREPANCY disclosed 15,282/44.3%
  vs planner's 6,472/19.4% — reconcile in cycle 3; S-R17 residue now
  uncertain BOTH directions, 167-vs-714 both contaminated — fresh look
  ordered before the ownership split is sized). MULTITERM: QA cycle 1
  found the G10 seam defect (held findings 1-2 correctly); proceeds with
  findings 3/4/5 (as-defined-in 2,813 occ = largest; DC parent 289;
  AL nested-clause) + U-R10 narrowing; qa_cycles 1. IL: phase-2 manager
  clean exit @ 64932d7 (13 REDs; D-1a/b planners verified+merged; M20
  breadcrumbs → G9; M21 הכרזה spelling variant folded into D-1a; class-C
  law-wide-default design risk flagged for Developer+QA) — phase-3
  manager to be spawned for serialized Developers + QA cycle 4 +
  certification contract. PREAMBLE: Planner @ bf4fdcf (per-shape corpus
  table: shape 1 = 31,048 total/29,678 uncaptured; shape 2 CORRECTED to
  #2 at 17,477; ~59,900 matches Q-D2's 59,461 within 1%; 20 REDs with
  rule-identity attribution; FP remedy = extend _B1_FORWARDING_PHRASES to
  the widened branch, never a gate) — manager to verify + spawn Developer.

- 2026-08-05 (Q1 second finding → core-2 scope): markers QA attributed all
  3 WA >5,000-char definitions to BASELINE via kill control (family-3
  blinded: baseline alone emits the swallow; markers' engine alone emits
  the same terms at 303/188/105 chars, zero >=5,000) — G3 healing
  prediction holds for all 3. BUT one layer deeper: a SECOND distinct
  defect in pipeline.py's Stage-2 persistence (~line 275-310):
  `all_blocks = baseline_blocks + extra_blocks` + first-candidate-wins on
  key (article_id, sorted(terms)) means baseline's bad candidate WINS the
  collision and the rule's clean candidate is silently discarded —
  confirmed on the real ingest→run_definition_linking path. G3 fixing the
  splitter alone may not fix the WIN (depends whether baseline stops
  emitting vs merely shrinks). RULED into core-2 scope: either fold into
  G3's acceptance (no baseline bad-candidate survives collision against a
  cleaner same-term rule candidate on the evidence rows) or a named G8
  with its own RED — core-2 manager's design call, tracking non-optional.
  Evidence: test_us_markers_qa_q1_wa_newline_collapse_swallow.py on
  claude/defs-us-markers (3 diagnostic passes + 1 load-bearing RED on real
  persisted output).

- 2026-08-05 (markers phase-2 verification + U-R10 ruling): markers @
  cf0aa88 — inherited claims verified with kill-controls (blinding the
  registry returns exactly the pre-build rates: rules load-bearing, not
  registered-only). Three inherited-number corrections, all the manager's
  own probes: FED 7.3% (its first sweep used US-FEDERAL not US-FED — probe
  artifact); NY production-faithful is 1,262/85.3% NOT 1,479/100% (the
  parquet holds raw literal-\n that core's fix strips at INGEST — 217 NY
  rows already capture; only NY+CA affected, CA's 21 match core's recorded
  residual); the "ten jurisdictions ≈19,278" conflated figures — ten sum
  to 12,941 (12,724 post-ingest), 19,278 is the TOTAL uncovered residual,
  so NH (943/100%), MA, PA, HI are being measured for family membership
  (Planner B) rather than dropped by rank cutoff. U-R10 RULED (program
  manager, on markers' merged-tree simulation): multiterm's two
  EntrySplitterRules register US-* wildcard and re-contribute whole-section
  text — on the merged tree they double WA's >5,000-char damage 3→7 (new
  worst 11,314 chars) for −6 AL zero-yield, and AL recall belongs to
  markers' own engine. Multiterm NARROWS: jurisdiction registration scoped
  to the states its accepted items actually require (per its registry-audit
  table), plus a contribution length bound if its items permit; red-first
  per its own M-R13/M-R14 discipline; QA certifies the narrowed
  registration. Markers' QA audit stays bounded to its branch's 3 WA rows
  (attributed to baseline splitter — expected to heal at core-2 G3 merge).

- 2026-08-05 (headings cycle-5 COMPLETE + scout respawn): headings @
  533f12d — suite 860/0, recall 21,080/22,228 = 94.8353% (+76 verified).
  Pin re-authored to the stronger mechanism-level property (capture via
  dedicated R-POINTER predicate; manager added the negative control proving
  the legacy rules CAN fire elsewhere, making the pin falsifiable); manager
  recorded its own import-name verification error as its own, not the
  agents'. QA cycle 4 opens against d5c12ab. The includes-FP scout declared
  DEAD (~10.5h idle) after completing denominator, P-R10 control, full
  24MB occurrence scan, and both samples — died at hand-classification.
  Respawned by program manager (fresh Sonnet scout) reusing
  headings_scout1_* scratchpad artifacts: re-verify the control first,
  classify from the drawn samples, do NOT re-scan unless the control
  fails. D-Q1 includes class stays open on headings ledger L2 until the
  measurement lands.

- 2026-08-05 (markers exit report — baseline-states finding + bucket-A
  discrepancy): markers @ c4baf7ce, manager context-exhausted, clean exit,
  QA NOT spawned (correctly — could not have verified it). Probe-sanity on
  bucket A FAILED to reconcile: markers measures 21,072 zero-yield
  recognized rows on its branch vs headings' 12,869 — cannot be the same
  denominator. PROGRAM DIAGNOSIS (hypothesis, to be proven at merge):
  the branches carry DIFFERENT rule sets — headings' branch has its
  recognition rules (verb-form headings: NV etc.) but not markers'
  extraction rules; markers' branch the reverse; also headings' bucket A
  counts only shape-1 rows while markers counted ALL zero-yield recognized
  rows. TRUE bucket A is only measurable on the MERGED tree — neither
  number gets quoted at certification; both recorded as branch-partial.
  NV attribution corrected: 1,262 recognized on markers' branch (not
  ~6,866 — that count used headings' recognition rules). THE BIG FINDING:
  residual concentrates in ten uncovered jurisdictions ≈19,278 rows
  (NJ 2,372/99.7%, NM 1,578, NY 1,479/100%, NV 1,262/100%, OK 1,146,
  MI 1,116, ND 1,023, MN 1,016, ME 1,000, OH 949) — and NJ/MI/ND/NY/OK are
  the program's C5 "working baseline" regression-guard states, recognized
  but yielding zero at 94–100%: the baseline states were never capturing.
  RULED (program manager, under D-PREAMBLE-ALL "all states" + D-CERT —
  director-vetoable): the 10-jurisdiction engine extension is IN-MANDATE
  markers phase-2 scope (numbers re-derived first per standard), after its
  QA on the current build. Markers phase-2 manager spawned (roster).
  Merge order unchanged: core-2 → markers → preamble → rest.

- 2026-08-05 (core-2 commissioned + D-S15 shipped + L11): CORE FOLLOW-ON-2
  commissioned as sprint 2026-08-05-defs-core-follow-on-2 (contract with
  gates G1–G7 = all six candidates; shared modules its exclusive write-set;
  merges FIRST; pointer re-pointed). SCOPED-INLINE: D-S15 merged @ 8a2b239,
  suite 839/0; RED-provenance proven correctly across independent branches
  (plan8 tests alone on 3f41093 → 4 RED; merged → green); manager's
  independent harness confirms SC 0/4→4/4, OR 1/4→3/4; QA cycle 2 running
  (12-item break-the-claims brief incl. 19.4% both sides + S-R17 714-row
  re-derivation + re-mutation of both adjacency gates). Endorsed judgment
  calls recorded: remove-not-flip the corrupted OR test; testable SD/NY/VT
  ledger; measured (not asserted) policy-independent degrade. HEADINGS
  L11: shape-1 attribution measured to a decisive split — corpus 69,009
  (NV band confirmed 8,575 vs ~8,323 cited); bucket A = 12,869
  heading-RECOGNIZED-but-zero-yield rows (markers-family, in core-owned
  extractor; NV alone ~6,866 and NV is NOT in markers' built jurisdiction
  set) — biggest measured capture gap seen; bucket B = 51,855 rows with NO
  heading signal (CA 9,769/FED 3,451/IN/IL/MS) — body-only, currently
  UN-OWNED by any family → D-CERT worklist. L11 accepted as proposed (not
  absorbed into cycle 5); bucket A routed to markers (re-measure on THEIR
  branch post-merge — their family-3 rules likely already shrink it — then
  absorb residual + NV as new member); reconciliation caveat recorded
  (headings' operational shape-1 definition ≠ preamble's band definition).
  MULTITERM: Developer re-applied narrowing @ abe5127, exactly 4/790,
  OR test green with exclusion guard — manager's re-measure next. PREAMBLE:
  M-R43 (denominator hardened BEFORE shape fixes — per-shape corpus
  re-scan, classifier built without own trigger vocabulary), M-R44
  (which-rule-claimed pins vs first-non-None starvation), M-R45 (FP
  re-measure per widening) — noted, no action needed. IL: Phase D spec
  @ 2e6cfdb; D-2 split APPROVED — D-1 (classes A/B/C + E6 + old-E1
  StructuralUnitRule, concurrent Planners, serialized Developers) completes
  2026-08-04-defs-il on I1–I5 + enumerated residual; certification opens
  as NEW sprint 2026-08-05-defs-il-certification (own valve/gates; ~92,600
  gershayim-delimited spans measured incl. הגדרות articles; word-internal
  gershayim hazard 33.1% named as cluster 1; exhaustive+disjoint assignment
  test as backbone; committed re-runnable manifest). Budget already
  authorized by D-CERT's chosen option ("one certification sprint per
  track").

- 2026-08-05 (D-CERT + certification wave): Director ruled D-CERT (inverted
  certification — recorded in program doc). PREAMBLE verdicts certified @
  d5c12ab: GA 2→2,794/28,154 headline (both before-numbers carried: 2
  measured / 5 historic-unreconciled); 23,617 clean-primary is the
  certified corpus figure (27,209 fallback rows ledgered provisional); NE
  split — recognition preamble's and works, extraction markers' (267
  unquoted rows → queued to markers, NE joins unquoted family); P-R7
  shape 1 (bare "Term" means — largest, NV ~8,323) attributed to HEADINGS
  verb-form family; shape 3 ("In this <unit>", FED-dominant) STAYS preamble
  (pushback accepted — it is the family, and their item 14 depends on it);
  D3: IN×2+NM preamble, NV×2+CO headings; preposition cluster measured
  18 idiom-bearing / 12 already rescued / 6 UNREACHED named to director per
  D-HG: STATE_ID_T39_C1_S39-129, STATE_KY_TIX_C67_S67.323,
  STATE_ME_T28-A_P3_C55_S1401-A, STATE_MI_C500_AAct-218-of-1956_S500.1305,
  STATE_PA_T20_C77_S7721, STATE_SC_T59_C58_S59-58-30 — all enter the
  D-CERT worklist. HEADINGS: plan5 verified (823/37 reconciled exactly, 860
  collected, fixtures re-derived 42/42) and merged @ 6c7e5c7, dispositions
  @ f21537a (L8 IA residual, L9 scope-value seam → core, L10 VA copula
  excluded-endorsed, L7 pending-external); dev cycle 5 running; certified
  matrix pointer forwarded — cycle-4 certification may open when dev lands.
  SCOPED-INLINE: pass 7 merged @ 3f41093; manager caught mis-authored SC
  direction-2 test (would have shipped a deliberate under-link behind a
  green test); dev4 DONE @ efa712a (path[-1]→path[0]; SC 4/4 live on real
  matcher; degrade 12.97% identical both ways — structurally guaranteed;
  pre-existing gap found: no test exercises empty-path degrade on a real
  row); plan8 DONE @ 2df1c5c (corrupted OR test REMOVED with pin-cite
  evidence — flipped assertion would pass for the wrong reason; SC
  single-level re-authored with offset guards; 4 multi-level RED pins on
  two ladders, corruption-checked, verified flip-green under simulated
  fix; SD/NY/VT testable-ledger fixture incl. newly-found NY row) →
  manager merges, verifies RED provenance, lifts QA-2 hold. MULTITERM:
  exclusion assertion landed @ 047f83b (RED now 5/789, green-under-
  narrowing 4/790) → Developer released. IL relayed D-CERT for Phase D
  spec (build A/B/C + E6 first, then ~10^5 inverted certification).

- 2026-08-05 (five-panel wave + D-S15): Director ruled D-S15 (outermost) and
  D-INCLUDES-MEASURE (FP scout first) — recorded in program doc. PREAMBLE QA
  landed @ 10924fc: GA 2→2,794/28,154 (9.9%; "before=2" traced, historic "5"
  unreconciled — manager to rule), corpus-wide 29,667→80,493 (+50,826;
  23,617 clean primary / 27,209 flagged fallback), FP 0/50, mutation-proof
  31 flips; P-R7 independent denominator: 91,878 hits / 59,461 uncaptured /
  ~94% genuine sample / 8 named shapes (biggest: bare `"Term" means` no
  trigger; "In this section" = FED's dominant convention) → shape→owner
  attribution demanded from preamble manager; NE 7/25,997 disposition
  demanded; D3 guarded-cluster gaps (CO/NV×2/NM/IN×2) to rescue path; L7
  78-row third D-HG sibling routed to preamble for reach assessment.
  IL Phase C complete @ 7463dff (31 REDs green, M16 425-term instrument-wide
  scope fix class, M17 16 variants, M18 self-correction: denominators from
  entry LINE not entry grammar; I4 FAIL with named classes A 479/1,173,
  B 132, C 117; E6 unblocked) + IL manager escalates the certification-method
  question (iterating sweeps cannot terminate at zero; inverted denominator
  ~10^5 = its own sprint) — CONVERGES with preamble P-R7 finding and
  headings' whitelist-cannot-close-zero-miss diagnosis → consolidated
  D-Q to director. HEADINGS phase-3 boundary: inherited claims re-verified
  with kill-controls; 1,224-row residual fully classified; 5th class found;
  L7 escalated; cycle-5 Planner landed @ 8cd3829 (49 tests, 36 RED live,
  fixtures byte-verified 42/42, item-14 scope-VALUE seam gap → core
  follow-on, VA "is a" copula excluded as close call). MULTITERM Planner
  amendment @ 467e67a (OR test → 4 named terms, non-vacuous via extractor
  probe) — Developer released to re-apply narrowing.

- 2026-08-04 (markers build verified — largest recall event of the program):
  claude/defs-us-markers @ 4d1adff, 6 new rules/ modules (541 lines, zero
  shared/test edits), suite 1 failed / 814 passed. Zero-yield before→after:
  VA 97.2→4.4, WA 98.8→6.4, AL 97.0→13.9 (manager-reproduced EXACTLY),
  FED 83.3→7.3, UT 97.5→2.3, SC 97.8→4.3, RI 100→7.2, AK 99.9→4.6,
  AZ 99.0→13.7, NC 51.8→14.1, TX 21.3→3.3; DC 27.3→27.2 honestly flat
  (its misses are the last-entry class). Manager proved dispatch live with
  a spy EntrySplitterRule pre-build (all 8 registry accessors now called
  in production). Held RED = FED last-entry defect in shared
  us_profile._split_into_numbered_blocks (runs before rules, wins dedup) —
  routed to core follow-on-2 (recorded in program doc). U-R9: FL
  ScopeTriggerRule flagged as scoped-inline territory → adopt-or-veto
  relayed to scoped-inline. WA STATE_WA_T50_C29_S030 accepted into markers'
  zero-yield mandate, status honestly unknown (needs named-row RED next
  pass). Boilerplate-classification interface position: shared helper, not
  registry rule (predicate vs producer); markers coordinates with
  scoped-inline directly. Boundary-damage residuals named (WA 3 defs
  >5,000 chars; VA/WA/AL 1/5/7 defs <10 chars) → QA next role.

- 2026-08-04 (headings cycle-3 escalation + succession): headings @ b79f588,
  811/0, U1 live-path leg proven (CT test flipped green with panel file
  untouched — 20,307-heading recall win live); dispatch semantics (A)
  OR-across-all verified adversarially; D-DF live at 94.5% after one bounce
  (bound 200→80: 60 clean > 61-with-known-FP); decomposition equivalence
  zero violations over all 83,956 headings; denominator convention pinned
  (52 files, PR excluded, `defin` case-insensitive). QA cycle 3 BOUNCE
  accepted: 69 newly-evidenced misses (45 `defined and` connector-gap rows
  + RI mojibake em-dash + pointer tables + `defined (qualifier)`).
  RULINGS: (1) D-MT-E1 WA zero-yield row (STATE_WA_T50_C29_S030: heading
  True, citation found, 0 candidates) ROUTED TO MARKERS per H-R1 — headings
  puts the reference-edge verification on a residual ledger as cross-panel
  dependency; (2) `includes` class (15 rows) is D-Q1 → sent to director
  with data; (3) P-R7 matrix cross-check sequenced AFTER preamble QA lands
  (certified inventory doesn't exist yet — QA in flight); pre-QA log
  correctly refused. Incumbent phase-2 manager context-exhausted, clean
  exit (all pushed); phase-3 manager to be spawned for dev cycle 5
  (`and` gap + 3 classes + U2's now-expressible 10-row item) then QA
  cycle 4. qa_cycles 3/5 — valve risk named.

- 2026-08-04 (multiterm E3/E4 rulings): multiterm build verified by its
  manager (2 added files, U3 holds, 11 REDs green, 4 VT/SD stay red; dev
  self-caught a `.match(s, pos)` `^`-anchoring subtlety) but escalated two
  cross-panel boundaries. E3 RULED option (i): F6's ScopeTriggerRule was
  firing on 8.87% of rows (35,337 candidates) — that mechanism IS family 1
  (scoped-inline's active build), so F6 narrows to its apposition/
  cross-reference shapes; zero recall lost (family 1 actively owned +
  program-close signal-agnostic re-check); protects scoped-inline's U6
  measurement; no core dedup machinery. OR row must be re-proven live via
  the narrow shape; dup-terms fix (10.8% of firing rows) held until
  post-narrow re-measure. E4 RULED: both multiterm EntrySplitterRules stay
  (narrowly gated, non-firing on VT/SD) but markers holds design-time
  authority — inventory relayed to markers manager; multiterm must document
  gating/contribution per splitter; TX 2009.003 two-assertion hazard goes
  on multiterm's residual ledger (markers' fix per M-R5 closes it).
  Merge-order note: with (i) the overlap is removed at source, so no
  U6-corruption constraint on multiterm-vs-scoped-inline merge order
  remains; scoped-inline NOT resumed for this (token economy) — they learn
  at merge review.

- 2026-08-04 (AL-class + PR gate-1 routing): AL LABEL-class scout
  (aa02b1af67484dda8) reported — 714 genuine un-rescued rows (premise
  deflated from "tens of thousands"), "In general"/"en general" decoy is the
  systematic hazard (144 occ/94 rows). Program ruling under D-CF precedent:
  bounded additive item, joint ownership (scoped-inline: code + prefer-quote;
  markers: boilerplate classification); recorded in program doc roster row,
  both managers briefed (scoped-inline resumed; markers queued mid-build).
  PR gate-1 hyphen Planner (a8a942cf256b44b48) reported: 235 exact-match to
  QA, root cause ".-" boundary crossing in _UNQUOTED_TERM_DASH_RE, decision
  NARROW (61 junk rejected / 208 retained, ~41-53% precision), 3 RED +
  1 guard + 1 xfail direct-function tests with P1 upgrade condition; PR
  manager resumed to run Developer fix → QA re-verify per M-R15.

- 2026-08-04 (wave 2, checkpoint): director rulings D-MT-E1 (+no-typed-field
  clarification), D-ANCHOR, D-PREAMBLE-ALL, D-UNITS recorded; unit research
  dossier persisted (2026-08-04-law-system-units.md). CORE: seam spec
  v1→v2.4 stable; Stage B+C RED sets complete (38 RED); dev1 (I4 registry /
  I5 bare-@ / I6 case-fold) merged to sprint branch, combined tree 656
  green / 26 RED / frontend 165; NY literal-\n ingest bug accepted as I8
  (manager-verified 40,102/40,102 rows); Developer #2 building I1/I2/I3/I7.
  PREAMBLE: all-states inventory — scouts S1/S2/S3 done (S4 pending);
  findings: tail is ~96% CLAUSE-shaped (routes to scoped-inline), 2 shared
  BLOCK idioms cover the tail, NY blackout found by S2, unbounded-last-entry
  extractor defect confirmed FED 86%/DC 91.7%/NY 79.8% (routes to markers).
  Parked: scoped-inline, IL, markers, multiterm (awaiting core merge); PR
  cycle 3 + headings QA in flight. Escalation-relay pattern established:
  role-agent completions bubble to program manager, who relays to panel
  managers by agentId.

- 2026-08-04: prior sprint closed (300f464); program doc (ad3dfd9); roster +
  core/IL contracts + dossier persisted (ba1b398); core + IL panels spawned.
  US family panels pending B3 re-recon.
- 2026-08-04 (wave 1 reports): all 8 panels reported. Escalations E-1
  (core), S-R3 (scoped-inline), U2 (headings), E1+E5 (IL), M-R7(a)
  (preamble), A+B (PR) — director ruled D-E1/D-Q1/D-PR-A; core briefed for
  seam v2 + 2 new items; headings/preamble/multiterm/PR resumed with
  rulings. Parked pending core v2/merge: scoped-inline, IL, markers.
  Incidents: 2 phantom-wait stalls (caught, resumed); preamble double-
  Planner (benign, cross-validated); multiterm log corruption from
  concurrent writer (corrected with evidence). Main checkout verified clean
  after headings Planner leak report. Measured highlights: IL corpus
  6,133/6,133 ingested (37s); PR 0%→80.9% (5,594 terms, 0 FPs); headings
  91.4% of miss-pool recognized, 0 FPs corpus-wide; markers quantified
  ~34,017 real zero-yield misses corpus-wide.
