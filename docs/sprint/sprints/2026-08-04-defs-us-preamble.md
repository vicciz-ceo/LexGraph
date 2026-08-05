---
id: "2026-08-04-defs-us-preamble"
status: planning
blocked_on: null   # P-FP ruled; option-(c) cycle ready to run — spawn Planner
current_role: planner
branch: claude/defs-us-preamble
worktree: /Users/nerya/LexGraph-wt/defs-us-preamble
locked_by: "/root/markers_panel_manager"
locked_at: "2026-08-05T21:44:41Z"
last_agent: "/root/markers_panel_manager"
last_updated: "2026-08-05T21:44:41Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US family 2 — body preambles without the word "Definitions"

## P-R7 — BINDING CONSTRAINT ON QA's U4 SWEEP (program ruling, from the PR panel's QA)

**Zero-miss ground truth must be independent of the capture mechanism's own
signals.** When QA runs the U4 zero-miss sweep, it **MUST NOT use the rules'
own trigger regexes as the denominator** — doing so measures "we caught what
we looked for", which is circular and cannot detect a whole missed shape.

This panel is better placed than most to satisfy it: our inventory is
**body-driven**, derived from reading real statutory prose across all 53
jurisdictions, not from the trigger list. But the constraint bites at sweep
time, so QA must build its denominator from an **independent** signal —
e.g. a broad definitional-language scan (`means`, `shall mean`, `has the
meaning`, `defined as`, unquoted-term shapes), or structural cues — and then
check our rules against it. Any hit the independent denominator finds that
our rules miss is a U4 failure, not a rule to be added quietly.

Related measurement hazard already recorded (M-R19): **S1 proved the inline
fallback's last entry runs to end-of-text** (FL 540.11: ~100% claimed vs ~12%
true coverage). Do NOT take U6 before/after numbers from that fallback
uncorrected.

## Mandate

Capture definitions sections whose only signal is a body preamble that never
uses the word "Definitions": GA's `"As used in this chapter, the term:"`
(173/400 sampled instances missed; GA capture is 0), MD and NE (0% capture,
no heading signal at all — strictly worse than GA), MS (0%), SD (dominant
miss type: `"For the purposes of this chapter, the term, X, means…"` under
term-name headings), plus low-volume instances in OR/PA/RI/SC/TN/TX/UT/VT.
This is the family the prior sprint deliberately skipped to protect zero
false positives — P-R2 escalation is EXPECTED here: bring the director real
conflict examples rather than silently choosing recall or precision.

## Acceptance gates (program manager-defined)

- **U1 — Every preamble variant is captured**, with RED tests from real GA/
  MD/NE/MS/SD rows before implementation.
- **U2 — Scope is stamped correctly and enforced** for scoped preambles
  ("As used in this chapter…" → chapter scope), live-path both directions,
  built on the core seam.
- **U3 — Rules ship as registry modules** per the core seam spec; zero edits
  to shared modules.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for preamble signals; every hit captured or proven not-a-definition.
- **U5 — Nothing regresses**: baseline states hold; all existing tests
  green; false-positive risk is the KNOWN hazard of this family — any
  precision/recall trade escalates per P-R2 with examples.
- **U6 — Measured before/after** full-corpus capture-rate report (GA must
  move from 5/28,154; report the new number honestly).

## Coordination

Core sprint owns scope plumbing + registry; read its published `## Seam
spec` from branch `claude/defs-core-scope`; merge after core. Registry
registrations are append-only. Out-of-family misses are reported to the
program manager for routing. Overlap warning: preamble detection feeds the
scoped-inline family (a preamble is often also a scope trigger) — the
boundary is: THIS sprint owns recognizing a definitions-bearing BLOCK with
no heading signal; the scoped-inline sprint owns scope-trigger parsing
inside otherwise-ordinary sections. Ambiguous cases escalate to the program
manager rather than being claimed by both panels.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager findings (full detail in `-log.md`, M-R1/M-R2)

Manager ran a full-corpus (not sampled) live probe of the real Stage-2 path.
The family-2 miss is **two gates**, not one regex:

| State | rows | preamble-signal | GATE A `_is_placeholder_heading` | GATE B `_BODY_DEFINITIONS_PREAMBLE_RE` |
|---|---|---|---|---|
| GA | 28,154 | 1,224 | **1,222 pass** | **1 pass** |
| MD | 39,552 | 1 | 0 | 0 |
| NE | 25,997 | 2 | 0 | 0 |
| MS | 158,688 | 637 | 0 | 0 |
| SD | 39,589 | 218 | 0 | 0 |

- **GA — single-gate fix**: Gate A already passes (bare citation breadcrumb
  heading); only the Gate-B regex's literal-"Definitions" requirement blocks
  `"As used in this article, the term:"`. Bodies then carry ordinary
  `(1) "Term" means` markers the existing extractor handles.
- **MD/NE/MS — fail Gate A**: their headings are *unrecognized placeholder
  shapes* (`"§5–114."`, `"View Statute 44-4051"`, `"Miss. Code Ann. §
  27-65-201"`). Widening the placeholder recognizer is shared-module work →
  coordinate with core, do not edit `pipeline.py` here.
- **MD/NE convention is NOT confirmed to be the GA shape** (1 and 2 rows
  respectively; both NE hits are false positives). Inventory them from real
  rows before writing tests — assuming GA's shape would be a planning bug.
- **SD — fails Gate A because its headings are real** (`"Loan processor or
  underwriter defined"`), and its term is **unquoted/comma-delimited**
  (`the term, X, means`), which no current extractor parses.

Three cross-sprint boundary conflicts are open (log M-R2): MS reads as
scoped-inline; SD overlaps the headings sprint's verb-form family; SD's
unquoted term is markers-sprint territory. The Planner quantifies each with
real rows; the manager then escalates per P-R2.

## Next Steps

**Rewritten by the consolidating Planner (D6) after D-PREAMBLE-ALL's scale-
out to all states.** M-R7(a) is ANSWERED (branch 1, ungated) and no longer
an open escalation — items below are written for that one answer, not
both. Items are grouped by **shape-cluster** (one parameterized rule +
test file often covers many states), not per-state, per the director's own
instruction that the long tail is a parameterized-rule problem, not 39
bespoke ones. Every item names its gate(s), its CHECK, and whether it is
blocked on core's `rules/` package (still docs-only as of this writing,
M-R17/S4 §1 re-confirmed) or on something else.

**Superseded by this rewrite**: the old items 1 (M-R7(a) escalation, now
answered), 7 (MS CLAUSE routing — folded into item 20's full 51-jurisdiction
package), and the old item 3's "3,327" MD target (corrected by D1's
reconciliation — see item 3 below).

1. **GA capture** — register a `BodyPreambleRule` recognizing "As used in
   this &lt;chapter/article&gt;, the term:" (1,222-1,229/1,224-1,257 real
   rows, D1/S4 re-measurement). Serves **U1, U6**. CHECK: `test_us_body_
   preamble_capture_red.py::test_ga_as_used_in_this_chapter_the_term_is_
   captured` and both GA tests in `test_definition_links_us_preamble_
   family.py` go green; full-corpus GA rate re-measured (was 5/28,154 per
   the program dossier). **Blocked on core's registry (`rules/` package)
   landing.**

2. **MD capture** — register recognizing "In this &lt;section/subtitle/
   title&gt;... the following words have the meanings indicated." Serves
   **U1, U6**. CHECK: `test_md_in_this_section_the_following_words_have_
   the_meanings_indicated` green; full-corpus MD rate measured. **Target
   corrected by this Planner's D1 reconciliation: ~1,841–1,849/39,552**
   (QA's D1 script and S4's independent re-measurement converge almost
   exactly), NOT the old "3,327" figure — that number traces to a
   different, looser, earlier script (`planner_md_ne_classify.py`) that
   counted quoted-term-means occurrences ANYWHERE in the full body, not
   rows whose body opens with MD's actual preamble; see `-log.md`'s P-D1
   for the full trace. **Blocked on core's registry landing** (M-R7(a) is
   answered; no further core dependency).

3. **NE capture, quoted subset (46/559)** — register recognizing NE's "For
   purposes of.../In the &lt;Named Code&gt;:" preambles. Serves **U1, U6**.
   CHECK: `test_ne_in_the_named_code_quoted_term_means_is_captured` green.
   **Blocked on core's registry landing.**

4. **NE unquoted subset (511/559) + SD unquoted subset (124/218)** — no
   further work possible in THIS sprint's file; both are confirmed live
   unparseable by any current extractor even with a perfect heading.
   Serves **U1** (documents the miss rather than silently dropping it).
   CHECK: `test_ne_unquoted_term_means_needs_markers_sprint_too` /
   `test_sd_unquoted_comma_term_needs_markers_sprint_too` go green, PLUS
   (D2 re-scope) `test_definition_links_us_preamble_family.py::test_real_
   nebraska_unquoted_body_preamble_is_a_genuine_in_family_candidate_but_
   no_current_extractor_can_parse_it` (already green today) and its
   renamed sibling `test_real_pipeline_still_cannot_capture_the_real_
   nebraska_unquoted_body_preamble_definitions_needs_markers_sprint_too`
   (intentionally, disclosedly RED until markers sprint lands). **Blocked
   on `2026-08-04-defs-us-markers`, not core.**

5. **MS capture, convention 1 ("As used in this article, the term:")** —
   same B1 idiom as item 12 below, MS-specific fixture already exists.
   Serves **U1, U2, U6**. CHECK: `test_ms_as_used_in_this_article_the_
   term_is_captured` green. **Blocked on core's registry landing.**

6. **MS capture, convention 2 ("shall have the meaning(s) ascribed
   herein")** — NEW this pass (scout S4 finding): ~845 real rows corpus-
   wide, previously uninventoried, comparable in scale to convention 1's
   entire original signal population. Serves **U1, U2, U6**. CHECK:
   `test_us_body_preamble_ms_second_convention_red.py` (2 parametrized
   real rows) green. **Blocked on core's registry landing.**

7. **SD capture, quoted subset (15/218)** — register recognizing SD's "For
   the purposes of this chapter, the term "X" means". Serves **U1, U2,
   U6**. CHECK: `test_sd_the_term_quoted_means_is_captured` green.
   **Blocked on core's registry landing** (SD's headings are genuinely
   real, not placeholders — confirmed unproblematic now dispatch is
   ungated by design, not a further open question).

8. **Scope stamping for chapter-scoped rows (GA/MS)** — "As used in this
   chapter/article" (GA) AND "For purposes of this chapter, unless the
   context requires otherwise..." (MS's OWN, differently-worded trigger)
   need core's `determine_scope` (Seam 1/C2) to recognize each as an
   English chapter-scope trigger. Not this sprint's file to build. Serves
   **U2**. CHECK: `test_us_body_preamble_scope_red.py::test_chapter_
   scoped_ga_definition_links_a_same_chapter_use_but_not_a_different_
   chapter_use` (GA) AND (D3, new this pass) `test_us_body_preamble_ms_
   chapter_scope_red.py::test_chapter_scoped_ms_definition_links_a_same_
   chapter_use_but_not_a_different_chapter_use` (MS) both go green in
   BOTH halves. **Blocked on core's C2 scope-trigger coverage — flagged
   explicitly as a PER-PHRASING dependency, not per-state: core
   recognizing GA's wording does not guarantee MS's differently-worded
   trigger is also recognized** (D3 finding).

9. **Regression guard** — baseline states and existing Hebrew tests stay
   green, unedited. Serves **U5**. CHECK: `backend/.venv/bin/pytest
   backend/tests -q` — pre-sprint 641 passing tests all still pass.
   **Already true today** and true by construction (zero edits to
   `pipeline.py`/`matcher.py`/`profiles.py`/`extract.py`/`us_profile.py`
   this whole sprint, including this consolidating pass). Not blocked on
   anything.

10. **Full-corpus before/after measurement** — once items 1/2/3/5/6/7/12-
    18 land, re-run a live scan across every jurisdiction this sprint
    touched to report the honest new capture number (GA was 5/28,154 per
    the program dossier). Serves **U4, U6**. CHECK: a probe script's
    output committed to the log, old vs. new counts side by side, every
    hit manually judged captured-or-proven-not-a-definition (U4's
    zero-miss sweep bar). **Measurement-hygiene requirement (D1)**: do NOT
    use `_extract_inline_quoted_definitions`'s raw "produced >=1
    candidate" as a proxy for "correctly captured" — its last entry runs
    unbounded (S1's proven FL 540.11 bug: ~100% claimed vs ~12% true
    coverage), and this specifically taints S2's own FEDERAL/DC/NY
    extraction-rate figures and S4's `n_extracted_today`/`extracted_terms`
    fields if reused uncorrected — see `-log.md`'s P-D1 for exactly which
    numbers are and are not affected. This is QA's deliverable per the
    harness role split, not the Planner's — flagged here so it is not
    lost.

11. **B1 colon-list capture — the biggest available simplification (M-R19,
    S3).** ONE parameterized `BodyPreambleRule` for `"As used in this
    <unit>, the term:"` / `"For (the) purposes of this <unit>, the term:"`
    + colon + a numbered/lettered list of >=2 terms covers DE, ID, KS, LA,
    OK, RI, SC, VA, WV, IL's no-marker variant (~30 genuine BLOCK rows
    across the 40-state tail, S3's own count) — no per-state bespoke
    regex, no extractor change (the existing `(N)"Term"` splitter and
    inline-quote fallback, both unedited, already parse every state's real
    shape). Serves **U1, U4, U6**. CHECK: `test_us_body_preamble_b1_
    colon_list_matrix_red.py` (9 parametrized real-row cases) all go
    green. **Blocked on core's registry landing.** **Known gap, not
    silently dropped**: RI's own named example (`STATE_RI_T42_C42-28_
    S42-28-3.5`) has a real, live-confirmed mangled-quote-byte corpus
    defect (distinct from the documented DE-style `Â` mojibake) that
    blocks BOTH extractors regardless of recognition — left out of the
    matrix rather than asserting something the data can't support; needs
    a corpus-ingestion fix, not a `BodyPreambleRule` fix.

12. **B2 words-have-meanings capture** — MD's own dominant shape (item 2),
    also DE/LA/WV (a strict subset of item 11's state list, same
    numbered-list splitter, no new logic). Serves **U1, U4, U6**. CHECK:
    `test_us_body_preamble_b2_words_have_meanings_matrix_red.py` (3
    parametrized real-row cases) all go green. **Blocked on core's
    registry landing.**

13. **CA BLOCK capture (663 rows)** — newly inventoried this pass (S4);
    **not a minor bonus population** — comparable in scale to GA's own.
    Serves **U1, U4, U6**. CHECK: `test_us_body_preamble_ca_block_red.py`
    green (1 real row; the file's own unit-level pin already documents
    live why today's pre-sprint Gate B narrowly misses this exact row).
    **Blocked on core's registry landing.**

14. **FEDERAL BLOCK capture, achievable subset (198/435, 45.5% of
    FEDERAL's signal)** — register recognizing FEDERAL's `(N) [heading]
    ... the term "X" means` shape. Serves **U1, U4, U6**. CHECK:
    `test_us_body_preamble_fed_dc_ny_red.py::test_federal_conservation_
    easements_definitions_first_two_clean_terms_are_captured` green.
    **Blocked on core's registry landing.** Deliberately asserts only the
    entries confirmed clean per row — see item 15.

15. **FEDERAL bounded extractor — NOT this sprint's file, named so it is
    not lost.** Contract's own open question, answered by this pass: **a
    body-preamble rule CANNOT produce clean text for every FEDERAL entry
    using either existing extractor as-is** — confirmed live, not
    asserted (`test_us_body_preamble_fed_dc_ny_red.py`'s own unit-level
    pin: a real row's last entry swallows 8,195 of 8,539 characters,
    including the entirely unrelated next subsection). Needs a NEW,
    properly-bounded extractor (stops at the next subsection-level marker
    or a legislative-history marker, not just the next quoted term) —
    production code out of this sprint's Planner-only remit and out of
    bounds for this sprint's frozen modules (`us_profile.py`/
    `pipeline.py`). Serves data quality behind **U1, U6**. CHECK: none
    from this sprint — tracked here so whoever owns the extraction layer
    next sees it, rather than it being silently absorbed into a
    partially-passing capture test. Two more real, independently
    confirmed FEDERAL extractor gaps (compound-quote entries, "includes"-
    verbed entries) are named in the same test file's docstring, same
    disposition.

16. **DC BLOCK capture (144/300, 48%, clean)** — register recognizing DC's
    own convention. Serves **U1, U4, U6**. CHECK: `test_us_body_preamble_
    fed_dc_ny_red.py::test_dc_trust_for_beneficiary_with_disability_all_
    four_terms_are_captured` green (all 4 real terms, 0% contamination
    risk on this row, unlike FEDERAL). **Blocked on core's registry
    landing.**

17. **NY BLOCK capture via the inline fallback (49/136, 36%)** — register
    recognizing NY's convention. Serves **U1, U4, U6**. CHECK: `test_us_
    body_preamble_fed_dc_ny_red.py::test_ny_literal_backslash_n_body_
    still_yields_clean_terms_via_the_inline_fallback` green (asserts 3 of
    11 real terms). **Blocked on core's registry landing ONLY** — NOT
    blocked on core's I8 (NY's corpus-wide literal-`\n` fix): the inline-
    quote fallback is newline-agnostic and already produces clean terms on
    this exact real row, confirmed live. Worth stating explicitly since it
    is easy to assume every NY item waits on I8; this one does not.

18. **Negative-guard hazard catalogue** — parameterized across CO/MT/AL/
    IN/SD/DC (S3's H1/H3 + S1's AL forwarding cluster + S4's SD finding +
    S2's DC exclusion-only clause). Serves **U5**. CHECK: `test_us_body_
    preamble_hazard_catalogue_red.py` (6 parametrized + 2 sharper unit-
    level pins) all pass TODAY (matches this family's established "green
    today, must stay green" convention) — becomes a regression gate once
    any B1/B2/MS/CA/FED/DC-recognizing rule ships. **Not blocked on
    anything — already true.** Two of the six rows (CO, MT) are proven
    live, not hypothetically, to already produce a real spurious candidate
    from the unedited extractors today if ever handed a recognized
    preamble — the sharpest evidence in this catalogue for why the guard
    matters.

19. **RI mangled-quote-byte corpus defect — routing, not this sprint's
    file.** Real, new, live-confirmed this pass (item 11's own gap note):
    `\x80\x9c`/`\x80\x9d` byte sequences in place of real quote characters,
    distinct from the documented DE-style `Â` mojibake. Not this sprint's
    file to fix. CHECK: none from this sprint; tracked here for whoever
    owns corpus ingestion next so it is not silently dropped.

20. **CLAUSE-shaped rows — routing, not building (supersedes the old item
    7).** The full consolidated package (D5): **2,659 real rows across 51
    jurisdictions**, merged from all four scouts'
    own CLAUSE lists, committed at `2026-08-04-defs-us-preamble-clause-
    package.{json,md}`. Routes to `defs-us-scoped-inline`, pending the
    program manager's routing decision. Not this sprint's file. CHECK:
    program manager's routing decision recorded in the program log; the
    receiving panel's own gate covers it. Tracked here only so it is not
    silently dropped by either panel.

## Historical basis (detail moved to the append-only log)

The original two-Planner reconciliation, manager verification, routings, and
then-blocked core-registry state are preserved in log M-R8/M-R10. The later
D-PREAMBLE-ALL ruling superseded the narrow inventory: all states are in scope,
dispatch is ungated, and precision comes from inventoried rules plus guards.
Its 7,383-row/2,038,247-row all-state worklist, four-scout scale-out, and
BLOCK/CLAUSE/hazard dispositions are preserved in log M-R15 through the D1–D6
consolidation entries. Core registry/dispatch subsequently landed; this cycle is
now the P-FP option-(c) correction described in M-R67–M-R78.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

1. P-FP judges captured `(row, term, definition_text)`; forwarding definitions are genuine.
2. Recovered Planner `a72c6a3` is tests-only but needs the M-R77 correction before integration.
3. Correction must strengthen tuple-level guards and causal right-occurrence tests.
4. It must measure live forwarding-filter load and preserve D-MT-E1 reference-edge debt.
5. Then Developer owns option-(c), blocking M-R53 comments, and the 386→≤300 split only.
6. Fresh QA owns definition-level FP certification and row-vs-definition evidence.
7. Main containment must be reconciled deliberately before final QA; root owns merge queue.
8. One writer per worktree; user `.claude/settings.json` is always out of scope.
