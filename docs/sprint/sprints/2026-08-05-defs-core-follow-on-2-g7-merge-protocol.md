# G7 merge-time verification protocol — sprint 2026-08-05-defs-core-follow-on-2

**Purpose.** Gate G7's binding form splits into (a) an ON-BRANCH obligation
owned by this sprint (suite green + per-gate measured before/after) and
(b) an AT-MERGE obligation owned by the **program manager**: no
panel-certified number moves except in its intended direction. This document
is the executable input to (b).

**Provenance.** Traced by a read-only scout (agentId `a682047c7fe5507af`,
Sonnet/high), commissioned by the panel manager; committed by the panel
manager (the scout wrote nothing — single-writer-per-tree discipline).
Two load-bearing claims independently re-verified by the panel manager
against source before commit; see the "manager verification" notes inline.

**Status of each number**

| # | Number | Classification |
|---|---|---|
| 1 | Markers' zero-yield table (incl. DC 27.3%) | **reproducible on the sprint branch's code alone** (verified, exact match) |
| 2 | Preamble's 23,617 / 27,209 | **merged-tree only** (requires unmerged `us_body_preamble.py`) |
| 3 | GA 2,794 | **merged-tree only** (same recipe as #2); its BEFORE value (2) *is* reproducible on-branch |

Nothing was untraceable. One genuine gap is disclosed rather than
reconstructed: the preamble QA's harness scripts were never committed.

---

## 1. Markers' zero-yield table (incl. DC 27.3%)

**What it measures.** The baseline (zero panel rules registered) rate at
which real Definitions-headed sections in a US jurisdiction's statute file
yield NO extracted definition candidate — "heading says Definitions,
extractor got nothing."

**Traced recipe.** Branch `claude/defs-us-markers`,
`docs/sprint/sprints/2026-08-04-defs-us-markers-log.md`. Two independent
passes report identical numbers: Planner pass-1 "Cross-cutting finding #1"
table (~L119-136) and the post-rebase re-measurement in §M7 (~L1236-1240).
Method as stated there: read each `us_<state>_statutes.parquet` directly;
`heading = row["section_title"]`, `body = row["text"].replace("\\n","\n")`;
call `USProfile(code).is_definitions_heading(heading, body)` for the "headed"
count, then `USProfile(code).extract_definitions_from_section(body,
scope=..., heading_was_derived=...)` — both real, unmodified production
functions in `backend/app/definition_links/us_profile.py`.

- **Denominator:** rows where `is_definitions_heading` is True ("headed").
- **Numerator:** that subset where `extract_definitions_from_section`
  returns zero candidates.
- DC row as logged: `| DC | 23,694 | 1,216 | 332 | 27.3% | 114 | 34.3% |`
  (total / headed / zero / zero% / rescuable-by-forced-fallback / rescue%).

**Classification: REPRODUCIBLE ON THE SPRINT BRANCH ALONE — verified.**
`registry.heading_rules_for("US-DC")`, `entry_splitter_rules_for("US-DC")`,
`term_clause_rules_for("US-DC")` all return `[]` on the sprint branch (the
same zero-rule state the original measurement was taken in). Re-run against
the follow-on-2 tree reproduced **all 7 states exactly**:

```
Jur        total    headed    zero       %  rescue   %resc
va         33856      1096    1065    97.2    1025    96.2
wa         51498      1800    1778    98.8    1682    94.6
wv         25460      1068     297    27.8     263    88.6
wi         18158       541      62    11.5      42    67.7
wy         10219       495      56    11.3      25    44.6
federal    54853      1920    1600    83.3    1477    92.3
dc         23694      1216     332    27.3     114    34.3
```

**P-R7 signal-agnostic? NO.** The denominator is built from the capture
mechanism's own heading signal (`is_definitions_heading`). This table
answers the narrower, signal-COUPLED question "given a recognized heading,
how often does extraction still fail." It is **not** an independent
total-miss population (that role belongs to the separate P-R7 sweeps —
preamble's 59,461, IL's ~4,859). Do not conflate the two when reporting
"reproduces."

**Expected direction — CONTESTED; see the open question below.** G3
(`_split_into_numbered_blocks`, us_profile.py:346) is G3's named driver and
the gate text states "DC's 27.3% zero-yield moves measurably."

> **Manager verification (independently confirmed against source).** The
> only committed held-RED for G3 —
> `backend/tests/integration/test_us_markers_unbounded_last_entry.py`, branch
> `claude/defs-us-markers` — proves a **contamination** failure mode, not a
> zero-to-nonzero conversion: `USC_T5_C34_S3401`'s "part-time career
> employment" definition (~487 real chars) is captured as **4,627 chars**,
> swallowing trailing amendment history. That row **already captures
> non-zero candidates today**. Furthermore the same file records, verbatim,
> that **DC's relayed 91.7% did NOT reproduce under any operationalization
> tried**: DC's sampled Definitions bodies "ended cleanly at genuine
> sentence boundaries with zero trailing-annotation markers in 8/8 sampled
> rows"; a trailing-marker measure gave **DC 0.1%**.
>
> Therefore **no evidence currently supports the claim that fixing the
> unbounded-last-entry defect converts any of DC's 332 zero-candidate rows
> into captures.** "DC moves up" is stated intent with an unproven — and
> partially counter-evidenced — mechanism. See the open question at the end
> of this document.

**Merge-time step.**
1. Immediately after G3 lands (before any panel rebase), re-run the harness
   against `us_dc_statutes.parquet`; record DC's new zero/headed/%. This
   isolates G3's own shared-code effect. Report the exact new number — do
   not assert direction only.
2. Run the vendored G3 RED and confirm PASS.
3. After `claude/defs-us-markers` is rebased onto the merged tree, re-run
   with markers' rules registered for the combined post-merge number.

---

## 2 & 3. Preamble's 23,617 / 27,209 and GA's 2,794

Grouped: one recipe, one table, one reproducibility verdict.

**What each measures.**
- **23,617** — rows newly captured once preamble's 4 registered
  `BodyPreambleRule`s are added, whose candidate came via the CLEAN primary
  numbered-block splitter path (summed over 53 jurisdictions).
- **27,209** — the same population's twin: newly-captured rows whose
  candidate came via the KNOWN-BUGGY `_extract_inline_quoted_definitions`
  inline fallback (fires only when `heading_was_derived=True` and the
  primary splitter found nothing). **This is the population carrying the
  `definition_text` boundary/contamination caveat** (FL `540.11`: ~12% true
  vs ~100% claimed byte coverage on the last entry).
- **GA 2,794** — GA's "after" captured-row count out of 28,154 GA rows
  (before = 2); the program's cited "GA 2->2794" headline.

**Traced recipe.** Branch `claude/defs-us-preamble`,
`docs/sprint/sprints/2026-08-04-defs-us-preamble-log.md`, QA commit
`10924fc`, verdicts ratified in `d5c12ab`. Per-state table + TOTAL at
~L2596-2645. Methodology quoted verbatim from the log's "Q-D1 —
Methodology":

> BEFORE = `is_definitions_heading(heading)` [bare fn] OR
> (`derive_heading_from_body(heading, body)` [BARE fn, registry untouched]
> gives a heading AND `is_definitions_heading` on it is True)... AFTER =
> same, but `derive_heading_from_body` is the profile method (bare-first,
> then our 4 registered `BodyPreambleRule`s, first-non-None-wins)...
> "captured": `is_definitions_section` resolves True for the row AND
> `extract_definitions_from_section` yields ≥1 `DefinitionCandidate` with a
> non-empty `.terms` tuple.

Corpus: all 53 `us_*_statutes.parquet`, **2,038,247 rows scanned**
(matches the census total). TOTAL row as logged:
`2,038,247 / 29,667 / 80,493 / 50,826 / 23,617 / 27,209`
(rows / before / after / new / new_primary / new_fallback).
GA row: `ga US-GA 28,154 2 2,794 2,792 1,926 866`.

**Script traceability — disclosed, not reconstructed.** The log names the
harnesses (`qa_d1_measure.py`, `qa_d2_independent_denominator.py`,
`qa_d3_crosscheck.py`) but states explicitly: *"all in the scratchpad, none
committed."* The runnable artifacts no longer exist. Only the
prose-documented methodology (quoted above) and the resulting table
survive. No script was fabricated and presented as "the" recipe.

**Classification: REQUIRES UNMERGED PANEL CODE — verified three ways.**
1. `from app.definition_links.rules import us_body_preamble` raises
   `ImportError` on the sprint branch; the module exists only on
   `claude/defs-us-preamble`.
2. `registry.body_preamble_rules_for("US-GA"|"US-NE"|"US-MS")` all return
   `[]` on the sprint branch.
3. Independent corroboration from a different agent on a different branch:
   the markers panel's manager hit the identical wall re-deriving preamble's
   NE number (markers log §M11): *"NE's recognition depends entirely on the
   preamble panel's own `BodyPreambleRule`, which lives on THEIR branch and
   is not merged here... Recorded as unverified."*

**BEFORE values ARE reproducible on-branch** — by the stated methodology
they are "main's behavior with the rules module absent," which is the sprint
branch's exact state. Independently re-verified: **GA before = 2/28,154,
exact match.** AFTER / new / 23,617 / 27,209 / 2,794 cannot be computed
without the panel branch.

**P-R7 signal-agnostic?** The **denominator** (2,038,247 corpus-wide;
28,154 for GA) is fully signal-agnostic — a raw row count with no
heading/extraction filter (in this respect stronger than #1's "headed"
denominator). The **numerator** ("captured") is necessarily defined by the
pipeline's own capture mechanism, as expected for a before/after capture
metric; it is not itself a P-R7 ground-truth sweep. It was cross-checked in
the same QA cycle against a genuinely independent sweep (D2: 59,461 raw
candidate misses, ~94% genuine on a 50-row hand sample; D1b: 0/50 confirmed
false positives on the newly-claimed population).

**Expected direction.** Program-manager intent: **GA's 2,794 does NOT
drop.**
- **G1** (padding strip in `_leading_quote_candidate`) changes captured TERM
  strings — a matching key — but is designed to RESCUE additional rows, not
  remove GA's. Expected neutral-to-additive.
- **G3** is the fix that actually touches this recipe's shared machinery.
  Preamble's split runs through the SAME `_split_into_numbered_blocks`
  (primary — G3's exact target) and a SIBLING function,
  `_extract_inline_quoted_definitions` (us_profile.py:551-595), whose
  last-entry defect sits at line 588.
- Expect **23,617 (clean-primary) not to decrease and possibly to increase
  slightly** (G3 bounds a previously-unbounded last block; it does not
  remove already-nonzero results, and may convert a few previously-zero
  primary rows into captures, shifting them out of the fallback bucket);
  **27,209's row count may decrease correspondingly.**

> **Scope gap — manager-verified, needs a ruling.** G3's scope as recorded
> in this sprint's Phase-0 table is `_split_into_numbered_blocks`
> (us_profile.py:346) **only**. The 27,209 population's contamination lives
> in `_extract_inline_quoted_definitions`. Manager re-read of
> us_profile.py:588 confirms the identical defect shape:
> `end = entries[index + 1][1] if index + 1 < len(entries) else len(text)`
> — the last entry runs to end-of-text. **G3 as scoped therefore makes the
> 27,209 population's row COUNT re-measurable (the gate's own word) but does
> not fix the function whose defect the 27,209 caveat is actually about.**
> See the open question below.

**Merge-time step.**
1. BEFORE preamble's branch is rebased in, re-run the BEFORE-only harness
   (GA → 2/28,154; ideally all 53 states) on the merged post-G1–G6 tree, to
   confirm none of G1–G6 silently moved the baseline path — this discharges
   G7(a)'s "don't touch baseline-path inputs unintentionally" obligation.
2. AFTER `claude/defs-us-preamble` is rebased onto the merged tree, re-run
   the full Q-D1 methodology exactly as quoted, same 53-file glob.
   **Pass condition: GA after ≥ 2,794 AND TOTAL new_primary ≥ 23,617.**
3. Report the new_fallback count as **informational only** (not pass/fail),
   alongside a fresh `definition_text` byte-coverage spot-check on a sample
   of it — the item the preamble QA explicitly deferred. This shows whether
   G3 incidentally helped the fallback population's data quality **without
   over-claiming the sibling function is fixed**.

---

## Cross-gate interaction — DO NOT DOUBLE-COUNT RESCUES (added 2026-08-05)

Later-accepted gates overlap the populations above and each other. Anyone
executing this protocol must treat these as interacting, not additive.

**Denominator hygiene — two valid rescue figures over DIFFERENT populations.
Never quote them as the same measurement, never average them:**

| Figure | Population |
|---|---|
| **39,955 / 74.1%** | headings panel — **corpus-wide defin-titled rows** (82,155 live-recognized, 53,918 zero on the live path) |
| **86.5% rescued** | markers panel — **their ten-state heading-recognized population (11,010)** |

**G11 ↔ G3 sequencing is COUPLED and binding.** Flipping the
`heading_was_derived` gate against the CURRENT, unmodified fallback produces
**202 new >5,000-char swallowed definitions across ten states alone**
(NJ 55, OK 39, NY 36, MN 22, OH 21, MI 11, ME 8, ND 7, NM 2, NV 1) — the
fallback's own unbounded-last-entry defect (us_profile.py:588) fires on every
newly-reached row. **G11's flip must land WITH the boundary fixes (G3 main +
G3 sibling), never before them.** Framing: *G11 delivers reach; the boundary
rules deliver cleanliness; 202 rows is the measured debt of reach alone.*

**Second-order dependency:** the G3 sibling fix is itself conditional on a
both-sides sample of the sibling's own population (Q-G3-A condition). If that
sample fails, the sibling becomes a separate follow-up — and G11's flip would
then have no sibling boundary fix to pair with. G11's recommendation must
cover both branches.

**Overlap, currently UNMEASURED:** a single row can be gate-blocked (G11) AND
carry a last-entry swallow (G3) AND be involved in a persistence collision
(G8). The G11 Planner is tasked to measure this overlap so rescues are not
counted twice across gates. Until those numbers land, **do not sum
per-gate rescue counts.**

**NV is gate-independent — exclude it from G11 accounting.** 73.2% of NV's
population survives the flip; NV stays on the markers panel's side
regardless of G11.

## SCHEMA MIGRATION — every panel's rebase must run it (added 2026-08-05)

This sprint ships **one additive, nullable schema change**: gate G9's
`heading_breadcrumbs` column on `articles` (program-manager approved; D-ANCHOR
`add_assertion_subject_unit_path_column.py` pattern — raw DDL against a plain
`Engine`, real `downgrade()`, **no backfill**, `NULL` is the honest value for
every pre-existing row).

**Binding step for EACH family panel's rebase onto the merged tree:**

> After rebasing onto this sprint's merged tree, run the G9 migration's
> `upgrade()` **in that panel's own worktree venv** BEFORE running its suite.
> A panel that skips it will see failures that are migration-absence, not
> genuine regressions.

Why this does not break any panel's rebase: the column is **additive and
nullable**, and code that never reads it is unaffected. Panels need the
migration only because their suites exercise the shared `Article` model.

**Acceptance evidence for G9 at merge — CORRECTED 2026-08-05.** The original
designation (IL's two held containment REDs) is **withdrawn as unachievable
by this sprint alone**, verified in code by both panel managers
independently:

- `matcher._value_matches(actual, expected)` is `return actual == expected`
  for non-tuple `expected`;
- `_in_scope`'s generic branch is
  `any(unit.kind == scope and _value_matches(unit.value, definition.scope_value) ...)`;
- the IL trigger module stamps `scope_value=**None**`, and that module is not
  on this sprint's branch at all — it is IL panel write-set.

So `"סימן א'" == None` → False: **a flawless G9 still leaves IL's REDs red.**
G9 delivers only half the chain. The other half — an IL `StructuralUnitRule`
deriving units from breadcrumbs, plus amending the trigger module to stamp a
real `scope_value` — belongs to the IL panel, and reaching into it would
breach P-R1.

**Corrected split:**
- **This sprint's merge evidence:** its own re-authored fixtures **plus the
  positive-control probe** (a throwaway `StructuralUnitRule` reading
  `heading_breadcrumbs` together with a throwaway rule stamping a REAL
  non-None `scope_value`) — proving the seam end-to-end in isolation from
  unshipped IL rules.
- **IL's two held REDs:** the correct **end-to-end** evidence for the
  COMBINED result, run by the IL panel once G9 lands. Tracked as a
  cross-panel follow-up, not as a gate on this sprint's merge.

**Correctness constraint recorded for anyone touching this data
(IL-manager-supplied, adopted):** **never infer unit KIND from depth.** In
`תקנות המשקלות והמידות`, חלק sits BELOW סימן (`== פרק ==` d2 → `=== סימן ===`
d3 → `==== חלק ====` d4) while most laws invert that. Depth stays monotonic;
the KINDS swap. Kind must derive from heading TEXT. A separate, genuinely
non-monotonic depth case (depth-4 before depth-3) exists in this sprint's own
`תקנות מחלות בעלי חיים` fixture — both shapes must work.

**Two distinct negative shapes** an implementation can get half-right:
different-VALUED unit (סימן א' vs סימן ב') and ABSENT unit (no חלק ancestor
at all). Both must be exercised.

## G3-main — MERGE BLOCKER CHECK: marker breadth (added 2026-08-05)

`_TRAILING_NOTES_MARKERS` are matched as **bare, case-sensitive substrings
anywhere in a line**. Generic tokens (`"Amendments"`, `"Source:"`,
`"History:"`, `"Cited."`) can therefore fire on substantive definition text.

**This is no longer hypothetical.** The G3-sibling measurement found real
false triggers on **statute names embedded in definition text** —
`"Clinical Laboratory Improvement Amendments (CLIA)"` and `"Clean Air Act
Amendments of 1990"`. G3-main is already merged, and its population (FED-style,
multi-paragraph) does not exhibit the sibling's total-wipe mode, but the
false-truncation mode applies directly: a genuine last entry whose text
contains such a line would be cut there.

**Pass condition:** over the main function's own last-entry population
(the 27,051 / 24.62% denominator), measure how many truncations remove
SUBSTANTIVE definition text rather than a genuine trailing-notes block, with
per-marker breakdown (specific `"Pub. L."`/`"Editorial Notes"`/`"Statutory
Notes"`/`"References in Text"`/`"Congressional Findings"` vs generic
`"Amendments"`/`"Source:"`/`"History:"`/`"Cited."`) and a seeded hand-judged
sample. **If the false-truncation rate is material, G3-main's marker set must
be NARROWED BEFORE MERGE** — this does not route to a follow-on.

## G8 — MERGE BLOCKER CHECK plus a named limitation (added 2026-08-05)

**BLOCKER CHECK — must run before G8 merges.** G8's containment-update
replaces a persisted `definition_text` when a later same-key candidate is a
strict SUBSTRING of it. The observed failure mode is a degenerate candidate
persisting FIRST and blocking a better one (see limitation below). **The
UNVERIFIED reverse ordering is the dangerous one:** if a good long candidate
persists first and a degenerate short one (e.g. `"means:"`) arrives second,
`_is_tighter_containment` evaluates `!=` ✓, `len <` ✓, and
`"means:" in <long text>` — plausible whenever the long text contains that
literal substring — and **G8 would REPLACE the good definition with the
6-char degenerate one.**

That would be **new damage introduced by G8**, not pre-existing behavior.
**Pass condition: measure on the real corpus whether any same-key pair
exhibits this ordering. If any does, G8's criterion must be AMENDED BEFORE
MERGE** — this does not route to a follow-on.

**NAMED LIMITATION (accepted, routed to core-follow-on-3).** In the OBSERVED
ordering, a degenerate 6-char candidate persisted first cannot be displaced
by a correct 941-char one, because replacement requires the new text to be a
strict substring of the old. Accepted for this sprint on zero-regression
grounds: first-wins is today's shipped behavior, so G8 neither created nor
worsened it — it is improvement-suppression, not damage. Part of the
1,308-row "ambiguous" group deliberately left untouched is therefore
quality-inverted. Design steer for core-3: prefer a *semantic emptiness*
test (a `definition_text` that is nothing but the defining idiom) over a
char-count threshold, which plan4 already measured and rejected.

**G8 COVERAGE, stated precisely so nothing waits on it:** G8 keys on
`(article_id, sorted(terms))` and fires ONLY on same-article/same-term-set
collisions. **Cross-term containment** (one term's text swallowed inside
ANOTHER term's `definition_text`) yields a different key and creates a new
row — **G8 structurally cannot close it.** The markers panel's class-D is
re-routed to core-follow-on-3's boundary work.

## Open questions for the program manager (both G3-related)

**Q-G3-A — Is `_extract_inline_quoted_definitions` in G3's scope?**
It is inside this sprint's declared write-set (`us_profile.py`), so there is
no fence violation either way; the question is purely whether the GATE
covers it. G3's named function and G3's stated purpose are in tension: the
purpose clause invokes the 27,209 rows' `definition_text` boundary caveat,
which lives in the sibling function, not the named one. Deciding it also
determines whether one Planner should design both together (the same
"design them together so they compose" logic the contract applied to
G2+G4).

**Q-G3-B — What can G3 honestly promise about DC?**
The gate says DC's 27.3% zero-yield "moves measurably," but the markers
panel's own investigation found DC's bodies end cleanly (8/8 sampled;
trailing-marker measure 0.1%) and the held RED demonstrates contamination on
an already-capturing FED row rather than any zero-to-nonzero conversion. A
plausible alternative attribution — **not yet measured, flagged as a
hypothesis only** — is that DC's zero-yield is driven by its unquoted-term
shape (`_leading_quote_candidate` requires a leading quote; the program
roster lists "DC's unquoted-term shape" under the markers family), which G3
cannot touch. The G3 Planner has been tasked to measure DC's actual
causation before any DC promise is made.
