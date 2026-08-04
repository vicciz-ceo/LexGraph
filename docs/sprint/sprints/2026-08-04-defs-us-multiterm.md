---
id: "2026-08-04-defs-us-multiterm"
status: planning
current_role: manager
branch: claude/defs-us-multiterm
worktree: /Users/nerya/LexGraph-wt/defs-us-multiterm
locked_by: "claude-code:sprint-manager"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager"
escalations_open: ["E1-pointer-only-definitions", "E2-sd-enumerated-scope"]
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 11
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US families 5+6 — multi-term shared clauses + inline parentheticals

## Mandate

Two lower-volume but confirmed miss-classes (dossier §2 families 5-6 + §6):
- **F5 multi-term shared-clause**: `The term(s) "X", "Y", and "Z" mean(s)…`
  — one clause defines several terms; the splitter assumes one term per
  entry. MT(7/300), MI, NH, ND, NY, OK; VT's `"mail," "mails," "mailing,"
  and "mailed" mean…` (simultaneously an F3 zero-yield case); SD's 4-term
  clause under a proper heading (extractor yield unconfirmed — verify);
  TX-style parent-clause lists from the prior sprint's known limitations
  (13/75 degenerate recovered terms).
- **F6 inline parentheticals**: apposition abbreviations `("Term")` with no
  means-idiom following — rejected even by the inline fallback's idiom-gap
  check. MI/MT/NH/ND/NY/OK (~1-2/300 each), OR's cross-reference-style
  `"X" has the meaning given that term in ORS…` variant.
Each term in a shared clause must become its OWN definition row linked to
the shared definition text, with correct scope.

## Acceptance gates (program manager-defined)

- **U1 — Every variant is captured**, RED tests from real rows (incl. the
  VT/SD flagged rows and a TX parent-clause list) before implementation;
  every term in a multi-term clause resolves individually.
- **U2 — Scope stamped/enforced** where applicable via the core seam,
  live-path both directions.
- **U3 — Rules ship as registry modules**; zero shared-module edits.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for multi-term/parenthetical signals; every hit captured or proven
  not-a-definition.
- **U5 — Nothing regresses**: baseline states hold; existing tests green;
  P-R2 escalation on precision conflicts (parentheticals are FP-prone —
  expected escalation surface).
- **U6 — Measured before/after** full-corpus report for these signals.

## Coordination

Core sprint owns scope plumbing + registry; read its `## Seam spec` from
branch `claude/defs-core-scope`; merge after core. Boundary with markers
sprint: rows that are BOTH zero-yield and multi-term (VT case) — splitting
mechanics belong to markers, per-term fan-out belongs here; the two Planners
agree the boundary in writing before Developers start; disagreement
escalates. Registry registrations append-only. Out-of-family misses route
via program manager.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings

Full text in `2026-08-04-defs-us-multiterm-log.md`. Summary:
- **M-R1** — CodeGraph queries run against the index in the main checkout
  (`codegraph explore` with cwd `/Users/nerya/LexGraph`, read-only) because
  worktrees carry no `.codegraph/`; all edits/tests/commits stay in the
  worktree.

## Next Steps

Numbered, independently verifiable. Every item's proving test already
exists and is committed RED (see the log's Planner entry for full output).
Two items are explicitly blocked on other sprints; do not spend Developer
time on them until the blocking work lands (rebase after).

1. **Top-level multi-term shared-clause capture (MI shape).** `(N) "Term1",
   "Term2", and "Term3" mean X` — today `USProfile.extract_definitions_
   from_section`'s block parser (`_LEADING_QUOTE_RE.match(block)`,
   us_profile.py:373) captures only the FIRST quoted span; the rest are
   dead prose in `definition_text`. **Re-expressed per M-R8** (core's
   published Seam 2 pre-declares this sprint's module filenames and a
   `TermClauseRule` kind — `parse: Callable[[str], list[DefinitionCandidate]]`,
   one entry block to PLURAL candidates — discovered by directory listing):
   ships as a NEW FILE, `rules/us_multiterm_shared_clause.py`, that pulls
   EVERY comma/and-joined quoted span immediately before the block's
   defining idiom into one candidate's `.terms` tuple — porting (to
   English) the same logic Hebrew's `extract._parse_terms_and_qualifier`
   already uses (extract.py:71-79). **ZERO edits to `us_profile.py`.**
   Serves **U1**. Proven RED by `test_multiterm_f5_shared_clause.py::
   test_mi_top_level_multi_term_clause_resolves_all_three_terms` and
   `test_definition_links_multiterm_shared_clause.py`'s MI-shaped
   assertions. Not blocked on any other sprint. **Coordination flag
   WITHDRAWN (M-R8):** the seam's directory-auto-discovery registry means
   file creation never conflicts in git; the markers/headings concurrent-
   edit concern this item previously flagged no longer applies.

2. **Nested multi-term shared-clause recovery (MT shape).** A multi-term
   clause embedded INSIDE another entry's own `definition_text` (entry
   "Affiliate" containing `"Solely for purposes of this definition, the
   terms \"owns,\" \"is owned\" and \"ownership\" mean..."`) — today
   silently absorbed with no trace. Fix: after item 1's list-capture logic
   exists, re-scan every candidate's OWN `definition_text` for a second,
   subordinate occurrence of the same quoted-list-before-idiom shape and
   split it out as additional entries sharing the parent candidate's scope
   — this is the SAME underlying mechanism as item 1, applied recursively;
   design it as one shared helper if practical. **Re-expressed per M-R8**:
   ships in the SAME new file as item 1 (`rules/us_multiterm_shared_clause
   .py`) — zero `us_profile.py` edits. Serves **U1**. Out of scope,
   deliberately: "person" (a nested SINGLE-term sub-definition in the same
   MT sentence) — reported to the program manager as a structurally-related
   but out-of-family gap (English has no analogue of Hebrew's
   `_NESTED_MARKER_RE`/`parent_term` recursion at all). Proven RED by
   `test_multiterm_f5_shared_clause.py::
   test_mt_nested_multi_term_clause_resolves_all_three_terms` and
   `test_definition_links_multiterm_shared_clause.py::
   test_mt_s16_11_402_nested_shared_clause_terms_are_extracted`.

3. **TX parent-clause redirect attachment.** `(4) The following terms have
   the meanings assigned by Section 2001.003: (A) "contested case"; (B)
   "party"; ...` — the block splitter already produces one candidate PER
   lettered child (not a zero-yield miss) but each `definition_text` is
   degenerate trailing punctuation (";", "; and", "") because the parent
   "(4)" line itself never becomes a candidate (`_LEADING_QUOTE_RE` doesn't
   match text starting with plain prose) and its redirect text is
   discarded rather than attached to its children. This is the prior
   sprint's recorded residual ("13 of 75 / 17.33% degenerate recovered
   terms", 2026-08-02-us-state-law-log.md) — root-caused precisely by this
   Planner. **PANEL QUESTION (see log): this exact residual is ALSO
   claimed by `claude/defs-us-markers`'s contract** ("entry-boundary
   bloat/truncation... TX 17.33% degenerate recovered terms"). Recommend
   this sprint owns it (mechanism is multi-term/parent-clause semantics,
   not marker-format boundary detection) — needs manager arbitration
   before a Developer starts. Serves **U1**. Proven RED by
   `test_multiterm_f5_shared_clause.py::
   test_tx_parent_clause_redirect_list_2009_003` /
   `test_tx_parent_clause_redirect_list_2002_001` and
   `test_definition_links_multiterm_shared_clause.py::
   test_tx_s2009_003_parent_clause_terms_get_the_real_shared_definition_text`.

4. **VT/SD marker-less multi-term sentence fan-out — BLOCKED on
   `claude/defs-us-markers`.** Both real rows (`STATE_VT_T23_C35_S3700`,
   `STATE_SD_T3_C14_S3-14-5`) are ONE unmarked sentence with zero `(N)`
   entry markers at all — `_split_into_numbered_blocks` finds no entry-start
   line and returns an empty list, so `extract_definitions_from_section`
   yields 0 candidates today (SD's yield, flagged "UNCONFIRMED" in the
   dossier, is CONFIRMED zero-yield by this Planner, live). See the log's
   markers-boundary proposal for the exact contract. Once markers' splitter
   change lands and this sprint rebases, item 1/2's list-capture logic
   should require zero further changes to also fix these two rows — verify
   that expectation with a live rerun once unblocked, don't assume it.
   Serves **U1**. Proven RED (for the stacked, honestly-labeled reason) by
   `test_multiterm_f5_blocked_on_markers.py` (both tests).

5. **F6 apposition, no-heading-context — BLOCKED on `claude/defs-core-
   scope` C3.** `("withdrawing state")`-style shorthand appositions (real
   examples: NH `STATE_NH_TXXXVII_C408-C_S14`, ND
   `STATE_ND_T26.1_C26.1-59_S26.1-59-01`, plus the pre-existing NH
   short-title fixture `STATE_NH_TXXVII_C301-B_S1`) sit inside ORDINARY
   (non-Definitions-heading) article bodies. `pipeline.py`'s non-
   Definitions-section `else` branch (pipeline.py:436-442) calls the
   Hebrew-only `extract_local_definitions`/`extract_adhoc_definitions`
   UNCONDITIONALLY — an English analogue (an `extract_us_adhoc_
   definitions`-shaped function: scan for `("Term")` immediately after a
   naming/introducing phrase, reject anything followed by NO further
   defining idiom being required — this IS the trigger, not a rejection
   condition) needs that branch to become profile-dispatched, which is
   core's own C3 mandate ("extraction lives behind the seam"), not yet
   landed. **Precision guard already written and green today**:
   `test_definition_links_inline_parenthetical.py::
   test_ok_boundary_marker_apposition_is_not_treated_as_a_definition` (a
   real `("-..-")` map-marker apposition that must NEVER be captured) —
   keep this passing when the new rule lands. Serves **U1**. Proven RED by
   `test_multiterm_f6_blocked_on_core_seam.py::
   test_nh_plain_apposition_with_no_means_idiom_resolves` /
   `test_nd_plain_apposition_with_no_means_idiom_resolves` and
   `test_definition_links_inline_parenthetical.py::
   test_nh_s1_act_apposition_is_extracted_as_a_definition`.

6. **F6 cross-reference variant (OR) — BLOCKED on core-scope C3 AND
   `claude/defs-us-scoped-inline` (family 1).** `STATE_OR_T41_
   C496_S496.716`: `"Enforcement officer" has the meaning given that term
   in ORS 153.005...`. **Correction to the recon dossier**: this is NOT an
   idiom-gap rejection — live-tested, `pipeline._MEANS_IDIOM_GAP_RE`
   already matches "has the meaning" and `_extract_inline_quoted_
   definitions` already extracts all 5 of this row's terms correctly WHEN
   RUN DIRECTLY against the body. The real blocker is reachability: this
   section's heading is a genuine substantive caption (not a placeholder),
   so `_derive_heading_from_body`/the inline fallback never gets invoked at
   all — the body is actually family 1's "As used in this section:"
   scoped-inline shape. Once family 1 + core C3 land, verify whether this
   sprint's own idiom handling needs ANY changes (current evidence says
   no). **PANEL QUESTION (see log)**: is a definition whose only content is
   a cross-reference pointer ("has the meaning given ... in ORS 153.005"),
   with no substantive text of its own, something that should even create
   a `Definition` row, or correctly nothing? Serves **U1**. Proven RED by
   `test_multiterm_f6_blocked_on_core_seam.py::
   test_or_cross_reference_style_definitions_resolve`.
   **Update — core seam published mid-Planner-run**: `claude/defs-core-
   scope`'s `## Seam spec (published)` landed during this session (was
   absent at manager setup). It names this sprint's two target rule
   modules verbatim (`rules/us_multiterm_shared_clause.py` as a
   `TermClauseRule`, `rules/us_inline_parenthetical.py` as a
   `ScopeTriggerRule`) — items 5/6 above are no longer blocked on core's
   MECHANISM landing, only on the Developer rebasing onto it once core's
   own Developer track lands the code (the seam doc alone is not yet
   runnable code). One open interface question the seam doesn't resolve:
   `TermClauseRule.parse` takes ONE already-split block, but item 3's TX
   parent-clause fix needs the PARENT block's text attached to 4 SEPARATE
   CHILD blocks — the Developer should raise this with core's panel before
   assuming a whole-section bypass (mirroring today's
   `_extract_inline_quoted_definitions` pattern) is the right answer. Full
   trace: log §3.

7. **Row-shape design decision — PANEL QUESTION, resolve before items 1-4
   implement.** The contract's literal wording ("every term ... becomes its
   OWN definition row") conflicts with the existing, deliberate,
   already-shipped design: `Definition.terms` is a JSON list explicitly
   built for "Stage 2's multi-term single definition case" (definition.py
   docstring), and `matcher.link_articles_to_definitions` ALREADY resolves
   `definition.terms` one at a time (matcher.py:132-134,140-160) into
   independent `USES_DEFINITION` assertions per term against a SHARED row
   — no matcher/pipeline change needed for "each term resolves
   individually" under that design. Recommend: reuse the existing
   one-row/N-terms design (zero shared-module edits, matches Hebrew
   precedent, already proven end-to-end). All RED tests in this sprint are
   written to pass under EITHER resolution (term-set membership + shared
   definition-text-content assertions only, never row-count). Needs
   director/manager sign-off, not a Developer judgment call.

8. **U2 scope enforcement — verification-only item, mostly blocked on core
   C1/C2.** `_determine_scope` returns `"law-wide"` for every real English
   row tested this sprint (confirmed live for all 8 F5/F6 fixture rows) —
   English chapter/local scope triggers don't exist yet (core's own remit).
   `matcher._in_scope`/`link_articles_to_definitions` are ALREADY
   jurisdiction-agnostic and require no change for multi-term rows (a
   `Definition` with `scope="local"` and `terms=(A,B,C)` already restricts
   each of A/B/C independently — this is existing, tested behavior, not
   new work). Once core C1/C2 land and produce non-law-wide English scope,
   re-verify live with a real multi-term+scope-trigger row (none exists in
   this sprint's fixtures — the real rows sampled are all law-wide) rather
   than assuming U2 is automatically satisfied. **PANEL QUESTION (see
   log §5, Q3)**: SD `STATE_SD_T3_C14_S3-14-5`'s real text restricts its
   4-term clause to `"when used in § 3-14-3 or 3-14-4"` — two NAMED
   sibling sections, a scope shape that fits NONE of the now-published
   seam's 4 values (`chapter`/`local`/`subsection`/`law-wide`). Recommend
   deferring SD's scope correctness to a follow-up once core's Planner has
   weighed in, while still requiring SD's 4 terms to extract (item 4) for
   U1 — do not block item 4 on this question.

8b. **Out-of-family finding — route via program manager, not this
   sprint's to fix.** `STATE_MT_T16_C11_P4_S16-11-402` entry (1)
   (`"Adjusted for inflation"`) is silently dropped today for a reason
   unrelated to multi-term clauses: the real row's `text` column repeats
   the section heading on the SAME line as entry (1)'s own `"(1)"` marker,
   so `_split_into_numbered_blocks`'s line-start-anchored marker check
   never fires for that line and the whole line (recap + entry 1) is
   dropped. Verified live (log §2). Likely belongs to
   `claude/defs-us-markers` (family 3, entry-marker mismatch) but flagged
   for the program manager to route, not decided here.

9. **U4 zero-miss sweep — QA deliverable, Planner-designed methodology.**
   Full design in the log's Planner entry: per-jurisdiction regex
   pre-filter (multi-term: 2+ adjacent quoted spans before "mean(s)"/"shall
   mean", no marker between quotes; parenthetical: `("Term")` with no
   idiom in the following ~80 chars) over all 53 real
   `us_<state>_statutes.parquet` files, each candidate hand-judged against
   3 buckets (captured / genuine miss / correctly-not-a-definition, with
   the OK `("-..-")` shape as the canonical correctly-rejected example),
   reported per-jurisdiction with counts — never a sampled extrapolation.
   Depends on items 1-6 landing (or partially, reported honestly per
   family) before it can report "captured" rates; the sweep METHODOLOGY
   itself can be dry-run against today's code first to re-confirm the
   baseline miss rates the dossier reports.

10. **U6 measured before/after report.** Run item 9's sweep script twice
    (pre-fix commit, post-fix commit) across all 53 jurisdictions' real
    parquet files; report rows scanned, candidates found, captured vs.
    correctly-rejected vs. genuine-miss counts per family, wall time —
    same standard as the prior sprint's full-corpus R17 report. Blocked on
    items 1-6's Developer work landing first.

11. **E1 pointer capture 2 — reference/link, primitives-only, NOT the
    plumbing.** Director ruling (log "ESCALATIONS RESOLVED"): a pointer-only
    cross-reference entry (`"X" has the meaning assigned by Section N`) is a
    definition with TWO captures — (1) the definition row, redirect sentence
    as `definition_text` (already correct today for single-term pointers
    like TX `Governmental body`; still blocked on item 3's fan-out for the
    six-term TX `2001.003` parent clause and on item 6 for OR) — and (2) a
    captured reference/link to the target law/section. **Scope discipline
    (director/program-manager order): this sprint does NOT build reference
    plumbing** (where a family rule's pointer target becomes a pipeline-
    emitted reference/assertion is core's seam v2, spanning 32 jurisdictions
    and 4+ panels). This item is bounded to the two REAL, already-existing,
    already profile-dispatched primitives the eventual wiring will need
    (`us_profile.find_citations` / `.detect_cross_law_derivations`), each
    with THREE distinct, separately-verified defects: (i) no state-code
    citation grammar at all (`ORS 153.005` → `[]`); (ii) decimal section
    numbers TRUNCATED to a DIFFERENT, real, existing section (`Section
    552.003` → `Section 552`) — a wrong-target defect, not a miss; (iii) the
    three real pointer idioms (`has the meaning given that term in`, `has
    the meaning assigned by`, `have the meanings assigned by`) are absent
    from `_TRIGGER_PHRASES`. Serves **U1** (zero-miss extends to the
    reference, per the director). Proven RED by
    `test_definition_links_e1_pointer_reference_capture.py` (6 RED + 1 GREEN
    control establishing the correct `detect_cross_law_derivations`
    invocation, resolving the log's previously-unresolved (iii) item) —
    OR `Enforcement officer`/TX `Governmental body`/TX `2001.003` parent
    clause, all three real rows named in the ruling. **Not blocked on any
    other sprint for the primitive-level fix** (both functions already live
    in `us_profile.py`, profile-dispatched); the PIPELINE-level wiring that
    turns a produced reference into a stored/queryable capture is core's
    seam v2 and is explicitly out of scope here.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Planner pass COMPLETE and manager-verified. Branch `claude/defs-us-multiterm`.
Manager-run verification (not agent claims): full suite **15 failed / 644
passed** (= 641 pre-sprint baseline + 3 new green guards); diff `83532fe...HEAD`
touches ZERO production files, ZERO pre-existing tests, ZERO deletions under
`backend/`; all 11 vendored fixture rows re-verified BYTE-EXACT against the
real parquet by an independent manager script (`ok=11 bad=0`). Note for QA:
the parquet body column is `text` — `section_text` does not exist and a wrong
guess yields a silent empty-string false negative.

PROCESS INCIDENT (owned, see log M-R7): two Planners edited this worktree
concurrently because the manager re-spawned on a false liveness signal and
then logged a false "attempt 1 FAILED SILENTLY" entry, which contaminated the
panel's evidence base and caused a Planner to misdiagnose concurrency as
fabrication. Retracted in the log. Rule M-R6 now: one writer per worktree,
liveness proven via artifacts, never assumed. No injection/tampering — two
concurrent writers explains every disputed observation.

Rulings: **M-R4** per-term resolution is behavioural, N terms may share a row
(matcher.py:132-134 already resolves each term independently) — no schema
migration. **M-R5** TX 2002.001: entry (4) shared-clause = ours, entry (3)
(A)-(E) boundary = markers (accepted program-wide); the 13/75 "17.33%" metric
aggregates BOTH mechanisms and must be decomposed — neither sprint claims it
whole. **M-R8** the seam's `TermClauseRule` (block -> candidates, plural) plus
directory auto-discovery means items 1-2 ship as the NEW file
`rules/us_multiterm_shared_clause.py` with ZERO `us_profile.py` edits; the
Planner's shared-edit collision flag is withdrawn. Item 3 needs markers'
`EntrySplitterRule` for TX to keep a parent-redirect clause and its lettered
children in ONE block (same shape as the agreed VT boundary) — relayed, not
escalated.

BLOCKED on two escalations (log §ESCALATIONS): **E1** pointer-only cross-
reference definitions — capture vs filter; manager-measured at **7,610 rows
across 32 of 53 jurisdictions** (tx 2,333, federal 1,951, in 1,438, mn 806),
i.e. program-scale, not F6-scale. **E2** SD `3-14-5` is scoped to two NAMED
SIBLING sections, fitting none of core's four STABLE scope values.

BOTH ESCALATIONS RESOLVED. **E1 — director:** pointer-only entries ARE
definitions; capture is TWO captures — the definition row (redirect sentence
as text) AND a reference assertion to the target law/section. **NO typed
"pointer" field, now or ever — the reference edge IS the typing** (my earlier
option (c) is RETRACTED; do not revive it). Reference plumbing belongs to
core seam v2, NOT built here — behaviour pinned in RED tests only. **E2 —**
routed to core seam v2 (same class as AK multi-chapter ranges, core's M4
adopt-or-defer-with-recorded-fallback). Silently stamping `law-wide` is
FORBIDDEN program-wide; if core defers the kind, the row defers with a
recorded fallback.

Manager-verified after the Planner amendment (13c5529): suite **21 failed /
645 passed** (15+6 RED, 644+1 green; my 641 pre-sprint greens intact); ONE
new test file; zero production files and zero pre-existing tests touched;
`grep -rniE "pointer_kind|is_pointer|definition_type|type_marker"
backend/tests/` returns NO matches, so the no-typed-field ruling holds.
Planner also corrected my probe error on (iii): the derivation invocation was
right; the citation match is anchored immediately after the trigger phrase,
so intervening words kill it.

STATUS: **PARKED** — planning complete, no Developer spawned by design.
RESUME WHEN core merges to main AND seam v2 publishes. Then, in order:
(1) rebase this branch on main; (2) spawn Developer (Sonnet/medium) for items
1-2 ONLY — ship `rules/us_multiterm_shared_clause.py` as a NEW FILE, zero
`us_profile.py` edits (M-R8); (3) items 3-4 stay blocked on markers'
EntrySplitterRule keeping TX/VT parent-redirect clauses and their lettered
children in ONE block; (4) item 11's reference half waits on seam v2.
Developer must never touch tests; QA (Sonnet/high) never touches
implementation. qa_cycles=5 → status blocked, report to program manager.
