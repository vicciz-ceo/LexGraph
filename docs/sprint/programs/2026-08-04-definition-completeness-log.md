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
