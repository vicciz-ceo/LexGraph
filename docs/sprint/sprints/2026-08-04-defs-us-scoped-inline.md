---
id: "2026-08-04-defs-us-scoped-inline"
status: in_progress
current_role: developer
branch: claude/defs-us-scoped-inline
locked_by: "claude-code:sprint-manager"
locked_at: "2026-08-04"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 1
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: US family 1 — scoped-inline definitions (no Definitions heading)

## Mandate

Capture the dominant US miss-class: definitions declared inside ordinary
substantive sections via `"As used in this section…"` / `"For purposes of
this section/subsection/chapter/part…"` — the English analog of the Hebrew
local-definitions path. 0% captured today in every state tested (dossier §2
family 1, §6 addendum). Lead states by measured frequency: OH 47%, UT 34.6%,
ME 39%, MO 33%, MT 27%, plus F1 presence in all 36 first-round states and
OR/TN/VT/RI/SC/PA/TX. These definitions are the canonical SCOPED case: the
scope unit named by the trigger (section/subsection/chapter/part) must be
stamped and enforced (assertions only within scope) via the core seam.

## Acceptance gates (program manager-defined)

- **U1 — Every convention variant in this family is captured**, with RED
  tests from real corpus rows of the lead states before implementation.
- **U2 — Scope is stamped correctly and enforced**: each captured definition
  carries the scope its trigger names; live-path proof both directions
  (in-scope mention links, out-of-scope does not) — built on the core seam.
- **U3 — Rules ship as registry modules** per the core seam spec; zero edits
  to shared modules.
- **U4 — Zero-miss sweep (director bar)**: QA sweeps ALL 53 jurisdictions
  for this family's signal patterns; every hit is captured or proven
  not-a-definition; any confirmed miss fails.
- **U5 — Nothing regresses**: baseline states (IN/CO/KY/LA/DE/ID/NJ/MI/MT/
  ND/NY/OK) capture rates hold; all existing tests green; zero-miss vs
  false-positive conflicts escalate per P-R2.
- **U6 — Measured before/after**: full-corpus capture-rate report for this
  family's signals (before vs after), same honesty standard as prior runs.

## Coordination

Core sprint `2026-08-04-defs-core-scope` owns scope plumbing + registry; read
its published `## Seam spec` from branch `claude/defs-core-scope` before
implementation; merge after core. Registry registrations are a
Planner-pre-declared append-only zone (program P-R5 merges). Misses found
outside this family's classes are REPORTED to the program manager for
routing, never fixed here. File-boundary conflicts escalate immediately.

## Standing constraints

All program standing constraints apply (program doc): CodeGraph first;
red-before-green live-path tests; Planner owns tests; QA independent; no
test downloads the corpus; absolute zero-miss bar; P-R2.

## Manager rulings

Full reasoning in `2026-08-04-defs-us-scoped-inline-log.md` (append-only).

- **S-R1** — Core's `## Seam spec` is NOT yet published (`origin/claude/defs-core-scope`
  @ `5b93ef8`). RED tests are authored against two core-proof targets: the new
  pure rule module this sprint owns, and the pipeline live path
  (`run_definition_linking`, `pipeline.py:311`) asserting persisted
  `Definition.scope` + `USES_DEFINITION` edges. No test may be written against
  core's registry-registration API before the spec publishes.
- **S-R2** — Developers are fenced to the new rule module until core merges to
  `main`. Zero edits to `pipeline.py` / `extract.py` / `matcher.py` /
  `profiles.py` / `us_profile.py` / `sections.py` (gate U3).

## D12 — U4 zero-miss sweep denominator design (Planner pass 2, program
ruling P-R7)

**P-R7, binding**: a zero-miss sweep's ground truth must be built
INDEPENDENTLY of the capture mechanism's own signals. This Planner's own D1
inventory (12 lead states, the trigger-regex-hit population) was built
exactly the way P-R7 forbids for a DENOMINATOR — it is a fine tool for
precision/recall measurement WITHIN the population the regex already finds
(D1/D3's own purpose), but circular as ground truth for "did we miss
anything the regex never looked at in the first place." QA's U4 sweep needs
a denominator that does not, at any step, invoke this family's own trigger
vocabulary (or any other capture-mechanism's own signal, including core's).

**Design**:

1. **Sample BEFORE any trigger regex touches the text.** Draw a stratified
   RANDOM sample of raw `text` rows straight from the parquet, per
   jurisdiction (minimum N per state — e.g. 200-300 — regardless of that
   state's corpus size, so small states are not statistically invisible;
   gate U4 says ALL 53 jurisdictions, not volume-weighted). No regex,
   keyword list, or heading check filters the sample at draw time — this
   is the step that actually breaks circularity; everything downstream can
   be automated without reintroducing it, AS LONG AS this step stays
   trigger-blind.
2. **Judge each sampled row's FULL text with an INDEPENDENT method** — a
   general-purpose semantic read (LLM-judged, or a qualified human panel
   for a sub-sample), prompted in PLAIN LANGUAGE ("does this text
   introduce/define any term, with any scope claim, in any phrasing —
   quote the term and the defining sentence if so") — never given this
   family's trigger-phrase list, never given the rule module's regex, and
   never told what "family 1" means technically. A semantic reader is
   methodologically independent of pattern-matching in a way that even a
   DIFFERENT, broader regex is not (D11's own experience is the proof:
   this Planner's OWN "improved" v2 regex still needed a human/manual pass
   to catch curly-quote variants, MO's comma-appositive convention, and
   idiom phrases like "shall be construed to mean" — regexes share blind
   spots as a FAMILY, even with different keyword lists).
3. **Cross-validate, do not trust one judge.** Run a SECOND, differently-
   sourced judge (a different model, or a human spot-check) over a
   sub-sample of the first judge's positives AND negatives. Report
   agreement rate. Low agreement means the denominator itself is not yet
   trustworthy — fix the prompt/method before using it to score any
   family panel's miss rate.
4. **The miss test**: for every denominator-positive row, run the REAL
   production pipeline (post-Phase-B) and check whether ANY assertion
   traces to that row's definition. A denominator-positive row with zero
   real-pipeline output is a candidate miss — triage each one (genuinely
   missed vs. a boundary case some OTHER family/sprint owns, per S-R3-style
   boundaries) before counting it against this family.

**How this is PROVEN signal-agnostic (not just claimed)**:

- **Zero keyword overlap, audited.** The sampling code and the judge's
  prompt are committed artifacts; an auditor greps both for every string
  in this family's own `TRIGGER_RE`/idiom vocabulary and confirms zero
  overlap with the SAMPLING step (the judge's PROMPT may legitimately
  describe "definitions" in plain English — that is not the same as
  sharing the regex/keyword list the extractor matches against).
- **Divergence measurement.** Run this family's OWN trigger regex over the
  SAME sampled rows and report the confusion matrix (regex-hit vs.
  judge-positive) x 4 cells. A genuinely independent judge WILL disagree
  with the regex on some rows in both directions (finds phrasings the
  regex misses -- expected, e.g. MO's comma-appositive shape; and rejects
  some regex hits as bait -- expected, e.g. the "Nothing in this section
  may be construed..." bare-`in` noise this sprint's own negative controls
  already document). Perfect agreement is a red flag that the "independent"
  judge secretly mirrors the regex signal, not evidence of quality.
- **Reproducibility.** The sample, the prompt, and the raw judge outputs
  are all committed artifacts (not summarized away), so a later auditor
  can re-run the SAME judge over the SAME sample and get the SAME
  classification, and so a differently-tasked reviewer can re-judge a
  sub-sample independently without needing to reconstruct the method from
  a description.

**Honest limitation, stated rather than hidden**: sampling bounds a miss
RATE with a confidence interval; it cannot prove literal zero misses over
an unbounded population the way a full census could. "Zero-miss" as a
practical program bar means "no confirmed miss survives triage on a
sample large and random enough to make a non-trivial miss rate
implausible," not a mathematical guarantee — stated here so a future
reader does not mistake a passing sweep for a stronger claim than it is.

Not run by this Planner (QA's job, per the deliverable's own instruction
— design and document only). No sweep numbers are claimed or implied here.

## Next Steps

Full design rationale, the D1 convention inventory, D2 boundary verdict, D3
scope-unit gap table, and (Planner pass 2) the D8 part/subchapter
measurement, D10 dedup verdict, D11 CLAUSE-package accuracy, and D12
denominator design are in the panel log (`## 2026-08-04 — Planner` and
`## 2026-08-04 — Planner (pass 2)`). This section is the executable item
list only.

**STATUS UPDATE (Planner pass 2, post-core-merge): Phase A is unchanged and
still buildable now. Phase B is UNBLOCKED** -- core merged to `main`
(`0d57228`); the registry/registration mechanism is no longer speculative.
A new rule module self-registers by existing as a file in
`backend/app/definition_links/rules/` (see `rules/us_scope_trigger_proof.py`
and `rules/il_scope_triggers.py` as working examples this sprint's own
module should follow) -- `profiles.py`'s `USProfile.extract_local_scope_
definitions` already discovers and unions every registered `ScopeTriggerRule`
for `US-*`, so Phase B step 2 below ("register through core's registry") is
satisfied by FILE PLACEMENT alone, not a separate registration call the
Developer writes by hand.

### Phase A — the ONLY Developer step left (ruling S-R2 fences it to ONE
new file; zero edits to `pipeline.py`/`extract.py`/`matcher.py`/
`profiles.py`/`us_profile.py`/`sections.py`)

**Phase A/B are now COLLAPSED into one step.** Pre-merge, "register" and
"wire into `pipeline.py`" were assumed to be separate Developer actions
(items 2/3 below, historical). Verified against the SHIPPED code (Planner
pass 2): `pipeline.py`'s Stage 2 `else:` branch ALREADY calls `profile.
extract_local_scope_definitions(...)`, which ALREADY unions every
registered `ScopeTriggerRule` for the document's jurisdiction code
(`us_profile.py`, read directly). A new rule module self-registers purely
by EXISTING as a file in `backend/app/definition_links/rules/` (auto-
discovery, `rules/__init__.py`, core-authored, "stable forever" per its own
docstring) — there is no separate registration call or pipeline.py edit
left for the Developer to write. Items 2/3 below are KEPT for their
still-live provenance requirement (below) but are no longer distinct
Developer actions; step 1 alone lands Phase A AND B.

1. **Create `backend/app/definition_links/rules/us_scoped_inline.py`**
   (the `rules/` package itself already exists, core-authored) exposing
   BOTH:

   ```python
   def extract_us_scoped_inline_definitions(body: str) -> list[DefinitionCandidate]
   ```

   — the PURE function this sprint's unit tests pin directly (trigger
   vocabulary, scope-unit mapping, idiom recognition, entry-boundary
   algorithm; `.source_article_number`/`.source_chapter` left `None` on
   every candidate it returns, matching `extract_local_definitions`'s
   existing convention) — AND a thin adapter matching core's shipped
   `ScopeTriggerRule.extract: Callable[[str, RuleContext], list[
   DefinitionCandidate]]` signature (see `rules/us_scope_trigger_proof.py`
   for the exact worked pattern), registered via `register_scope_trigger_
   rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))`
   at module import time. **Critical provenance requirement, corrected
   from the pre-merge draft**: `extract_local_scope_definitions`
   (`us_profile.py`) auto-defaults ONLY `.source_article_number` when
   `None` — it does NOT fill in `.source_chapter` for a `scope="chapter"`
   candidate. The adapter itself, not anything downstream, must stamp
   `candidate.source_chapter = ctx.chapter` whenever the pure function
   returns a `scope="chapter"` candidate (mirrors core's own `pipeline.py`
   Definitions-section-path pattern, `if scope == "chapter": candidate.
   source_chapter = art.chapter`) — otherwise a `"chapter"`-scoped
   candidate on the live path silently degrades to matching only
   articles whose `.chapter` is also `None`.

   **Scope-unit mapping the adapter must stamp (Planner pass 2 amendment;
   full table + rationale in the trigger-axis test file's module
   docstring and the `-log.md`'s D8/S-R4/S-R5 sections)**: `section` ->
   `"local"`, `chapter` -> `"chapter"`, `subsection` -> `"subsection"`
   (all three shipped/enforced); `act`/`article`/`title`/`subdivision`/
   `paragraph`/`division`/`subpart` -> `"law-wide"` (dead-kind fallback,
   core's own AK-range precedent); `part`/`subchapter` -> **PENDING** the
   manager's D8 ruling (chapter-fallback vs. law-wide-fallback) — do NOT
   implement either until that ruling lands; the RED tests currently
   pinning the literal `"part"`/`"subchapter"` strings are placeholders,
   not a final answer (see those tests' own docstrings).

   Serves gates **U1**, **U2** (both directions — enforcement is core's,
   already shipped for local/chapter/subsection), **U3**.

   Proven by (RED today, real tails in the `-log.md`'s D13 section):
   - `backend/tests/unit/test_us_scoped_inline_rules_trigger_axis.py` (13
     tests), `..._body_axis.py` (15 tests, +1 Planner-pass-2 Missouri
     appositive-convention case), `..._negative_controls.py` (6 tests) —
     `ModuleNotFoundError`.
   - `backend/tests/integration/test_us_scoped_inline_pipeline_live.py` (4
     tests) — real `AssertionError`s against the unmodified pipeline.
   - `backend/tests/integration/test_us_scoped_inline_pipeline_core_overlap_
     dedup.py` (1 test, Planner pass 2, D10) — already GREEN today (proves,
     independently of Phase A landing, that core's proof rule + a second
     overlapping `ScopeTriggerRule` dedupe to one `Definition` row on the
     live path now) — a regression tripwire, not a RED-then-GREEN gate.

2. *(historical, see the collapse note above — no longer a distinct step)*
   Register through core's per-jurisdiction rule registry for every
   `US-*`/`US-FED` code (never `IL`) — satisfied by file placement alone.
3. *(historical — no longer a distinct step)* Wire into `pipeline.py`
   Stage 2's `else:` branch — already true on `main`, nothing to edit.
4. **Confirm** `backend/tests/integration/test_us_scoped_inline_pipeline_baseline_regression.py`
   stays GREEN, unchanged, after step 1 lands (gate **U5**).
5. **Full-corpus before/after capture-rate measurement** for this family's
   trigger signal across all 53 jurisdictions (gate **U6**) — QA's sweep,
   unblocked once step 1 lands. **U4's zero-miss sweep denominator is now
   DESIGNED** (Planner pass 2, D12; P-R7-compliant, signal-agnostic —
   full design in the `-log.md`'s D12 section) — QA should read that
   section before building the sweep, not re-derive a denominator from
   this family's own trigger regex.

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Cycle-2 fix pending. See log for full history.
`origin/main` `83532fe`; own backend venv built and importing. Panel log
opened with the manager's verified architecture read (F1 root cause is the
`else:` branch at `pipeline.py:436-442` calling Hebrew-only
`extract_local_definitions`/`extract_adhoc_definitions` for US articles).
Core seam spec still unpublished — Planner proceeds per S-R1/S-R2.
