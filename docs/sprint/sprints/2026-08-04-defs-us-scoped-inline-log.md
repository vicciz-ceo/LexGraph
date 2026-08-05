# Panel log — sprint 2026-08-04-defs-us-scoped-inline

Append-only. Panel members (Planner / Developer / QA) speak to one another
THROUGH the sprint manager; every exchange is recorded here (program ruling
P-R3). Manager rulings for this sprint are numbered `S-Rn`.

---

## 2026-08-04 — Manager: sprint opened

Workspace: `/Users/nerya/LexGraph-wt/defs-us-scoped-inline`, branch
`claude/defs-us-scoped-inline` off `origin/main` (`83532fe`). Own backend venv
built (python3.13, `pip install -e '.[dev]'`, `import app` OK). Git identity
verified `256402398+vicciz-ceo@users.noreply.github.com`.

CodeGraph note for all panel agents: the `.codegraph/` index lives at
`/Users/nerya/LexGraph` (the program manager's checkout), NOT in this
worktree. Run `codegraph explore "<question>"` from `/Users/nerya/LexGraph`,
or pass `projectPath=/Users/nerya/LexGraph` to the MCP tool. The indexed tree
is the same code this branch starts from. CodeGraph BEFORE grep/find/Read.

### Manager architecture read (verified against on-disk source, not assumed)

- `run_definition_linking` (`backend/app/definition_links/pipeline.py:311`) is
  the live-path entry point. Stage 2 is `pipeline.py:386-442`.
- The F1 hook is the `else:` branch at `pipeline.py:436-442`: for an article
  whose heading is NOT a definitions heading, the pipeline calls
  `extract_local_definitions` / `extract_adhoc_definitions` (`extract.py:183`,
  `:202`) unconditionally for EVERY profile, including US. Both are
  Hebrew-regex-only (`extract.py:28-33`), so every US article takes this
  branch and yields zero candidates. That is family 1's exact root cause,
  re-confirmed live rather than taken from the dossier.
- Scope enforcement is `matcher._in_scope` (`matcher.py:104-110`): `"chapter"`
  → `article.chapter == definition.source_chapter`; `"local"` →
  `article.number == definition.source_article_number`; anything else
  (including `"law-wide"`) → unrestricted. There is **no subsection or part
  granularity today** — `Article` (`backend/app/models/article.py:23`) carries
  only `number`, `heading`, `chapter`. Family 1's triggers name section,
  subsection, chapter AND part, so finer granularity is core's to deliver.
- Vendored-fixture convention already exists:
  `backend/tests/fixtures/us_statutes/*.json` (list of raw corpus row dicts,
  e.g. `de_sample_rows.json`). Tests read these, never the HF snapshot.

### S-R1 — Test targets are chosen to not depend on core's unpublished API

Core sprint `2026-08-04-defs-core-scope` has NOT published its `## Seam spec`
yet (checked `origin/claude/defs-core-scope` @ `5b93ef8` — the only match for
"Seam spec" in that contract is the promise to publish one). Rather than
block, the Planner authors RED tests now against two targets that core cannot
invalidate:

1. **Pure rule module** — a NEW file this sprint owns outright. Unit tests
   import it directly. Conflicts with nothing.
2. **Pipeline live path** — integration tests drive `run_definition_linking`
   and assert on persisted `Definition.scope` + `USES_DEFINITION` assertions.
   This is behaviour, not API surface, so the seam spec can change the wiring
   without rewriting the tests.

Tests must NOT be written against the registry-registration API until the
seam spec publishes. The registration adapter is a thin, later commit.

### S-R2 — Developer work is fenced until core merges

Per the sprint contract's Coordination section and program P-R1: developers
implement ONLY the new pure rule module until core's merge lands on `main`.
Zero edits to `pipeline.py`, `extract.py`, `matcher.py`, `profiles.py`,
`us_profile.py`, `sections.py` (gate U3: "zero edits to shared modules").
After core merges: rebase, then add the registry-registration module.

---

## 2026-08-04 — Planner

Re-checked `origin/claude/defs-core-scope` before starting: still `5b93ef8`,
no `## Seam spec` published. S-R1/S-R2 stand unchanged; proceeded exactly as
ruled.

### Method

CodeGraph first (`codegraph explore` from `/Users/nerya/LexGraph`) for
`run_definition_linking`/`extract_local_definitions`/`matcher._in_scope`/
`DefinitionCandidate`/`profiles.py`/`us_profile.py` — confirmed the
manager's architecture read against verbatim current source, no
discrepancies found.

Corpus work used the worktree's own `backend/.venv` (`pyarrow` 25.0.0
already installed there — unlike the 2026-08-02 sprint's disposable-venv
note, no external venv was needed this time), reading directly from the
already-local HF snapshot, never downloading. Full scripts (scratchpad, not
committed): `f1_inventory.py` (per-state trigger/body classification,
lead-state full scan + 36-state spot-check), `f1_precision.py` (trigger-
phrase-vs-signal-quality cross-tab), `f1_unit_precision.py` (scope-unit-vs-
signal-quality cross-tab), `fetch_fixture_rows.py` (full raw rows for the
D4 fixture) — all under
`/private/tmp/claude-501/-Users-nerya-LexGraph/87b55b0a-5a38-44b6-887d-1e093b526197/scratchpad/`.
Every "captured today?" claim below was verified by calling the REAL
`is_definitions_heading`/`extract_local_definitions`/
`extract_adhoc_definitions`/`_is_placeholder_heading`/
`_derive_heading_from_body` from the worktree venv, not asserted.

### D1 — Convention inventory (12 lead states, full scan: 424,719 rows,
77,360 raw trigger-phrase hits)

**Trigger axis — what actually occurs.** A broad trigger regex (any of `As
used in` / `For (the) purpose(s) of` / `In` / `When used in` / `Wherever
used in`, tolerating a leading marker like `(a)`/`(1)`/`(a)(1)` and an
inserted `the`, followed by `this <unit>`) found real instances of every
scope unit the dossier predicted PLUS several more: `section` (49.3% of
hits), `chapter` (24.6%), `subsection` (7.2%), `part` (6.7%), `subchapter`
(4.6%), `article` (2.0%), `division` (1.5%), `title` (1.5%), `paragraph`
(1.1%), `subdivision` (0.8%), `act` (0.6%), `subpart` (0.1%).

**Critical finding — bare `In`/`in this <unit>` is NOT a reliable trigger
on its own.** Cross-tabulating trigger PHRASE against body-signal quality
(12 lead states): `as used in this <unit>` is genuine (adjacent quote +
defining idiom, or colon-then-list) **72.5-76.9%** of the time; `for
(the) purpose(s) of this <unit>` **~35-51%**; but bare `in this <unit>`
is genuine only **~21%** — the other **72.7%** is ordinary cross-
referencing prose (`"Nothing in this section may be construed..."`,
`STATE_UT_T11_S11_59_603`, real). Doing the same cross-tab PER SCOPE UNIT
(joint unit x signal-quality, 12-state aggregate) gives the precision each
unit's trigger population carries: `subchapter` 52.0%, `part` 42.3%,
`section` 41.0%, `chapter` 36.0%, `article` 33.2%, `subsection` 23.2%,
`subdivision` 22.4%, `paragraph` 21.8%, `title` 15.8%, `division` 13.2%,
`act` 7.8%, `subpart` 2.1% — precision varies a LOT by unit, not just by
phrase; a rule module that doesn't require an adjacent quote+idiom (or
colon-then-list) regardless of which phrase/unit matched would flood the
zero-miss sweep with false positives, especially for `act`/`division`/
`title`/`paragraph`.

**Body axis — what follows.** Confirmed real examples of every shape named
in the brief plus two the brief didn't name: `"X" includes` (TX, distinct
from `means`/`shall mean`) and the trigger appearing AFTER its own term
(`"State facilities," when used in this chapter, shall mean...`, VT, real
— not a leading preamble at all). Also confirmed two "must NOT over-split"
shapes that are the actual hard part of this family: (a) nested roman-
numeral sub-clauses one level deeper than the entry split
(`STATE_UT_T53G_S53G_10_402`: `(b) "Refusal skills" means...: (i)...(iv)`)
and (b) a single term's OWN numbered/lettered elaboration with no new
quoted term per item (`STATE_MT_T23_C5_P8_S23-5-801`, `STATE_TN_T36_C5_
S36-5-910`, `STATE_VT_T11C_C7_S701` — real, all three). And one row
(`STATE_VT_T3_C45_S2291`) defines 3 terms across 2 DIFFERENT scope units
in ONE body — scope must resolve per-entry, never once per body.

**Spot-check, all 36 first-round states**: family 1 present (heading NOT
recognized + genuine trigger) in every single one, from 122/2561 raw hits
(NE, lowest) to 15,574/83,148 rows (IN, highest raw hit count; IN's real
convention leans heavily on `chapter`-scoped triggers). CA/GA/IL/MD/NE/MS
show `heading_recognized_count == 0` across the board (their `section_
title` never carries real heading text at all, confirmed placeholder-
heading states, matching the dossier) — this does NOT exclude them from
family 1: a placeholder heading only gets body-derivation-rescued into F2
territory if the body's OWN derived label says "Definitions"; a scoped-
inline trigger inside an ordinary substantive placeholder-headed article
is still genuine, un-rescued F1. Not independently re-verified live for
these 6 states (out of the 12 lead states) — flagging as an open item, not
claiming it either way.

### D2 — Boundary verdict: S-R3 CONFIRMED, one new escalation-worthy case
found

**F1 vs F3 (heading recognized, extractor yields 0): CONFIRMED, with real
evidence.** Every heading-recognized + scope-trigger-present row sampled
(`STATE_UT_T34_S34_46_102`, `STATE_OH_T9_C953_S953.21` "Rendering plant
definitions" — a compound heading the wave-5 fix already recognizes,
`STATE_SC_T44_C93_S44-93-20`, others) is F3's problem, not this sprint's,
REGARDLESS of whether the trigger names a scope unit — matches S-R3
exactly. Caveat found while verifying: heading-recognized + trigger-present
does NOT always mean "0 extracted" — `STATE_TN_T57_C4_S57-4-102` (heading
"Chapter definitions") already extracts 211 candidates successfully today.
Either way, S-R3's boundary holds: this sprint owns neither the miss nor
the success once the heading is recognized.

**F1 vs F2 (preamble without a scope unit): no genuine ambiguity found in
the 12 lead states.** By construction, every row this sprint's trigger
regex matches already names an explicit scope unit (`this section`/`this
chapter`/etc.), so it's cleanly F1 by S-R3's own definition. I did NOT
independently test GA/MD/NE/MS (F2's assigned states, not in my lead-state
list) for a reverse case (a scope-unit-naming trigger that F2 might
otherwise have claimed) — no evidence of a conflict, but not ruled out
either; flagging for the manager to relay to `defs-us-preamble` if useful.

**NEW boundary question (flagging, not silently deciding) — "References to
'X' shall include Y" is NOT a `"X" means Y`-shaped definition.**
`STATE_PA_T15_C57_S5749`: `"For the purposes of this subchapter: (1)
References to "other enterprises" shall include employee benefit
plans..."` — grammatically a construction/interpretation clause about how
OTHER text should be read, not an introduction of "other enterprises" as a
term with its own meaning. My lean: EXCLUDE from v1 (pinned as a RED test,
`test_references_to_term_shall_include_is_excluded_by_design`, asserting
non-capture — the one test to flip if overruled). This is a genuine P-R2-
style precision-vs-recall question: if QA's zero-miss sweep later flags
this shape as a real miss, that's the signal to revisit, not something I
should guess at now. Not blocking Phase A (the rule module simply doesn't
capture this shape either way); raising it here per "escalate rather than
guess."

### D3 — Scope-unit gap table (coordination ask for core)

`matcher._in_scope` (matcher.py:104-110) enforces exactly two units today:
`"local"` (`article.number == definition.source_article_number`) and
`"chapter"` (`article.chapter == definition.source_chapter`). `Article`
(`backend/app/models/article.py:23`) carries only `number`/`heading`/
`chapter` — no subsection/part/subchapter/article/title granularity.

Measured GENUINE (non-bait, quote+idiom-or-colon-list-confirmed) frequency
per scope unit, 12 lead states, 424,719 rows scanned:

| Scope unit | Genuine hits | Representable today? | Note |
|---|---|---|---|
| section | 15,609 | **YES** — `"local"` | dominant unit, 53.8% of all genuine hits |
| chapter | 6,870 | **YES** — `"chapter"` | 23.7% of genuine hits |
| part | 2,187 | NO | 7.5% — largest un-representable unit |
| subchapter | 1,861 | NO | 6.4% — highest per-unit precision (52.0%) of any unit |
| subsection | 1,297 | NO | 4.5% |
| article | 513 | NO | 1.8% |
| title | 179 | NO | 0.6% |
| paragraph | 182 | NO | 0.6% — likely sub-subsection-level in practice |
| division | 152 | NO | 0.5% |
| subdivision | 147 | NO | 0.5% |
| act | 34 | **effectively YES, for free** | "this act" == the whole document == already-unenforced `"law-wide"` semantics; no new `Article` granularity needed, just map `act`→`"law-wide"` explicitly instead of a bespoke `"act"` string |
| subpart | 2 | NO | negligible, safe to defer |

**Bottom line for core**: `section` + `chapter` alone already cover ~77%
of genuine family-1 volume (matches today's enforceable units exactly, no
coincidence — these are the two units Hebrew's `extract_local_definitions`
tradition already established). The next-highest-value ask is `part` +
`subchapter` + `subsection` combined (~18.4% of genuine volume) —
`Article` would need one more nullable string column per unit (or a single
generic `(unit_kind, unit_value)` pair) plus a `matcher._in_scope` branch
per unit. `article`/`title`/`paragraph`/`division`/`subdivision` are each
under 2% individually — my lean is these are safe to defer past an initial
core rollout, revisit only if QA's full-53-jurisdiction sweep (U4) finds
concrete misses attributable to them. `subpart` (2 genuine hits total) and
`act` (already free via `"law-wide"`) need nothing further.

### D4/D5 — Fixtures and RED tests

Fixture: `backend/tests/fixtures/us_statutes/us_scoped_inline_rows.json`
(25 real, unmodified corpus rows — trigger axis, body axis, multi-scope,
negative controls, baseline regression). Provenance and per-row rationale:
`backend/tests/fixtures/us_statutes/README.md`'s new
"`us_scoped_inline_rows.json`" section. One row initially miscategorized
during construction (`STATE_MT_T87_C1_P2_S87-1-217`, believed trigger-free,
turned out on full-text read to be a rich multi-trigger F1 row of its own)
— caught by actually running the tests, not by re-reading; dropped from
the fixture, documented in the README rather than silently discarded.

Test files (all under the 300-line style gate):
- `backend/tests/unit/test_us_scoped_inline_rules_trigger_axis.py` (252
  lines, 13 tests)
- `backend/tests/unit/test_us_scoped_inline_rules_body_axis.py` (258
  lines, 14 tests)
- `backend/tests/unit/test_us_scoped_inline_rules_negative_controls.py`
  (123 lines, 6 tests)
- `backend/tests/integration/test_us_scoped_inline_pipeline_live.py` (294
  lines, 4 tests — U2 both-directions proof for `"local"` AND `"chapter"`
  scope, plus the D3 unenforced-unit stamping proof)
- `backend/tests/integration/test_us_scoped_inline_pipeline_baseline_regression.py`
  (154 lines, 3 tests — 2 pass today as pre-existing-behavior sanity pins,
  1 fails today for the exact reason it exists to catch: a fixture bug,
  now fixed)

Proven RED — `backend/.venv/bin/pytest backend/tests -q` from the worktree
root: **37 failed, 644 passed** (33 unit tests: `ModuleNotFoundError: No
module named 'app.definition_links.rules'`; 4 integration tests: real
`AssertionError`s against the unmodified, current `run_definition_linking`
— e.g. `"the real production pipeline recognized ZERO definitions in a
real Utah 'For purposes of this section, "concurrence" means...' article
-- got [] definitions from [] assertions"`). **644 passed confirms the
pre-existing suite is fully GREEN** — this sprint's RED is 100%
attributable to its own 37 new tests, nothing else regressed.

### Question for the panel

The PA "References to X shall include Y" exclusion (D2) — surfaced, not
escalated as blocking. No hard escalation this cycle: core's seam spec
absence was already ruled on (S-R1/S-R2), and no F1/F2 boundary conflict
was found in the states actually tested.


---

## 2026-08-04 — Manager: Planner handoff verified + core seam spec conflict

### Handoff verification (manager-run, not taken on the Planner's word)

- Three-dot diff materialized (`git diff origin/main...HEAD`, 2,278 lines) and
  reviewed. `--stat`: 9 files, +2,195/-7. **Zero production files touched** —
  tests, fixtures and docs only. Role separation held.
- Full read of the load-bearing file
  `backend/tests/integration/test_us_scoped_inline_pipeline_live.py` (294
  lines): it drives the REAL `ingest_us_statute_rows` → `run_definition_linking`
  and asserts on persisted `Definition.scope` plus `USES_DEFINITION`
  assertions. Both U2 directions are present and are real assertions, not
  mocks: `local` scope (own-article reuse links; synthetic sibling article does
  NOT) and `chapter` scope (same-chapter sibling links; different-chapter
  sibling does NOT).
- **Corpus-leak check**: `grep` for `parquet|huggingface|.cache|hf_hub|datasets`
  across all 5 new test files → the only hit is a comment stating tests do not
  read the parquet. Clean.
- **Fixture authenticity independently proven.** I re-read all 12 states'
  parquet files and compared `section_title` + `text` byte-for-byte against the
  25 vendored rows: **25/25 verbatim real, 0 suspect.** This matters because the
  Planner self-reported one fixture-construction error; the check confirms the
  committed fixture is clean.
- **RED independently reproduced**: `backend/.venv/bin/pytest backend/tests -q`
  → `37 failed, 644 passed`. The 644 passing confirms the pre-existing suite is
  green, so the RED is fully attributable to the new tests. 33 unit failures are
  `ModuleNotFoundError: No module named 'app.definition_links.rules'`; the 4
  integration failures are genuine `AssertionError`s against the unmodified
  pipeline (e.g. `assert []` — "the real Maine subsection-scoped definition was
  never captured"). Import-error RED and assertion RED are both legitimate here.
- All 5 test files are under the 300-line style gate.

Verdict: Planner handoff ACCEPTED.

### Core published its `## Seam spec` — and it conflicts with this family

Polled `origin/claude/defs-core-scope` after the Planner returned: advanced
`5b93ef8` → `9272f6e`, and `## Seam spec (published)` now exists. Read in full.

Good news: core's worked example names our module path exactly
(`backend/app/definition_links/rules/us_scoped_inline.py`) — the Planner's
guess was right, and Phase A's file placement needs no change. Rules
self-register by existing in `rules/`, so U3's "zero edits to shared modules"
is satisfied by construction.

**The conflict.** Core's `ScopeTriggerRule` is
`extract: Callable[[str, str], list[DefinitionCandidate]]` — it receives
`(article_body, article_number)` and nothing else. The scope data contract
states the ordinary-article path's rules stamp `"local"` or `"subsection"`
ONLY; `"chapter"` is reachable exclusively through `determine_scope`, which
core restricts to the Definitions-SECTION path. The worked example confirms
the shape: the rule stamps `source_article_number` itself.

Therefore a registered rule **structurally cannot produce a chapter-scoped
candidate** — it never sees the owning article's `chapter`, so it can never
stamp `source_chapter`, which is exactly what `matcher._in_scope`'s existing
`"chapter"` branch compares against. A candidate returned as `scope="chapter"`
with `source_chapter=None` would silently link only articles whose chapter is
also `None`.

This is not a theoretical gap. Per the Planner's D3 measurements (12 lead
states, 424,719 rows, 29,033 genuine hits), `chapter` is **6,870 genuine hits
= 23.7% of this family's volume** — the second-largest scope unit, behind only
`section`. It is already enforceable by today's `matcher._in_scope` at zero
new cost. A real, vendored, already-pinned example: `STATE_VT_T3_C45_S2291`
(`"State facilities," when used in this chapter, shall mean...`, chapter
`"45"`). Indiana — a baseline regression-guard state — has the highest raw
trigger count of the 36 first-round states and leans heavily chapter-scoped.

Secondary, same root cause: `part` (2,187) + `subchapter` (1,861) = **13.9%**
have no representation either. Core does deliver `subsection` (1,297, 4.5%).
The residue (`article`/`title`/`paragraph`/`division`/`subdivision`/`subpart`,
~4.0% combined) the Planner leans to defer, and I agree.

### S-R3 — Escalating rather than choosing a side (program P-R2)

The three ways to proceed without core changing anything all break a gate:
coercing chapter→`"law-wide"` OVER-links and violates the director's explicit
"assertions only to mentions within the section they are specified for";
coercing chapter→`"local"` UNDER-links and violates the absolute zero-miss
bar; dropping chapter entirely fails U1 and U4 on 23.7% of the family. This is
precisely the recall-vs-precision conflict class P-R2 forbids a panel from
settling silently, and core's spec declares itself STABLE with changes
escalating through the sub-manager. Escalated to the program manager; Developer
NOT spawned, because the answer changes the Planner's test expectations
(several tests currently assert scope strings `"part"`/`"subchapter"`/
`"article"`/`"title"` that core's 4-way vocabulary does not contain) and
amending tests is the Planner's job, never the Developer's.

Phase A is NOT started. Everything committed and pushed before returning.

---

## 2026-08-04 — Manager: core merged, escalation answered, branch rebased

Rebased `claude/defs-us-scoped-inline` onto `origin/main` (`0d57228`, core
merged at `06d67d8`). One conflict, in the SHARED
`backend/tests/fixtures/us_statutes/README.md` — another panel appended a
section (NY's literal-`\n` defect) while we appended ours. Resolved by keeping
BOTH sections; no content dropped from either side. Venv refreshed
(`pip install -e '.[dev]'`).

### S-R4 — escalation ANSWERED; verified against shipped CODE, not the spec doc

The seam doc is 1,220 lines and self-superseding (v1 → v2.5), and core's own
QA found one place where spec and code disagreed (I11). So I verified the
contract by reading the merged source, not the prose. Shipped facts:

- `RuleContext` (`rules/registry.py:63`) = `(article_number, chapter: str|None,
  unit_path: UnitPath)`. The owning article's chapter IS available to a rule.
- `ScopeTriggerRule.extract: Callable[[str, RuleContext], list[DefinitionCandidate]]`,
  a UNION kind — every matching rule runs, nothing suppresses anything.
- `_in_scope` (`matcher.py:135`) shipped branches: `"chapter"` →
  `article.chapter == definition.source_chapter`; `"local"` /
  `"subsection"` → `article.number == definition.source_article_number`
  (subsection additionally offset-checked by `_subsection_contains_offset` via
  `profile.resolve_unit_path`); `"law-wide"` → True.

**My escalation is fully resolved for the bulk of the family.** A rule can now
stamp `scope="chapter"`, `source_chapter=ctx.chapter` and it is genuinely
enforced. Coverage of this family's measured genuine volume that is now BOTH
expressible and enforceable: section→`local` 53.8% + chapter→`chapter` 23.7% +
subsection→`subsection` 4.5% = **82.0%**.

### S-R5 — NEW finding: the generic above-article kind branch is dead on the live path

`_in_scope`'s final branch resolves any OTHER kind (e.g. `"part"`,
`"subchapter"`) against `getattr(article, "structural_units", ())`. Core's own
comment states a production `MatcherArticle` has no such attribute, so the
generic branch returns False **for every article, including the definition's
own**. Compounding it, v2.2 replaced `structural_units` with `unit_path`, and
v2.4 re-scoped `UnitPath` to BELOW-article only — so `StructuralUnitRule`
feeds `resolve_unit_path` (sub-article), NOT this branch. There is no seam a
family panel can use to populate it, and `MatcherArticle` is built in
`pipeline.py`, which U3 forbids us to touch.

Consequence: stamping `scope="part"` would capture the definition but link
**zero** mentions — a silent under-link, the worst outcome under a zero-miss
bar. This affects `part` (2,187) + `subchapter` (1,861) = **13.9%** of genuine
volume, plus the ~4.0% residue.

Core already set a precedent for exactly this shape (v2 §1, AK multi-chapter
ranges): an unrepresentable narrowing falls back to `"law-wide"` — zero-miss-safe,
with the precision cost recorded rather than silently dropped. A possibly
better fallback exists: in US codes a part/subchapter is a subdivision OF a
chapter, so `scope="chapter"` with `source_chapter=ctx.chapter` would be a
strictly tighter over-approximation that still never under-links. It is only
sound if those rows reliably carry a non-null chapter. **I am not guessing:
the Planner must MEASURE it (D8 below), and I rule afterwards.** Recorded as a
named open conflict class; re-escalated with volume numbers after the U4 sweep,
same treatment as the PA construction-clause pin.

### S-R6 — core's proof rule OVERLAPS our dominant pattern

`rules/us_scope_trigger_proof.py` already registers, for `US-*`,
`As used in this section, "Term" means ...` → `scope="local"`. That is this
family's single most common shape. `ScopeTriggerRule` is a union kind, so
core's rule and ours will both fire on the same text and emit duplicate
candidates. The seam says duplicates dedupe downstream on
`(article_id, sorted(terms))`. That is a claim to TEST, not to assume — a
duplicate-`Definition` pin is now a required deliverable.

### S-R7 — `Definition.scope_value` is TRANSIENT (v2.5)

No persisted column, no migration; `scope_value` /`source_chapter` /
`source_article_number` live only on the in-memory `DefinitionCandidate`.
`Definition.scope` IS persisted. Tests may assert persisted `.scope`; they must
NOT assert a persisted `.scope_value`.

### S-R8 — CodeGraph freshness

The `.codegraph/` index at `/Users/nerya/LexGraph` now tracks `main` and does
resolve core's new symbols (verified: `RuleContext` at `registry.py:63`). Per
core QA's binding process note, agents on this divergent branch still verify
BRANCH-LOCAL files by direct read; CodeGraph is authoritative for main-state
structure.

### New input routed in: preamble panel's CLAUSE package

2,659 real `act_id`s across 51 jurisdictions, ours by routing, at
`docs/sprint/sprints/2026-08-04-defs-us-preamble-clause-package.{json,md}` on
`claude/defs-us-preamble` (`8a8837a`). Their honest caveat: ~148 rows are
sample-verified only, and the package documents a discriminator bias found and
corrected for MS/SD. Per the program manager: verify a sample against the
corpus before trusting the classifications. Also inbound under P-R2: MS's
clause-embedded subset. P-R7 binds our U4 denominator — it must be
signal-agnostic, and we must state and prove what it is.

---

## 2026-08-04 — Planner (pass 2)

Resumed post-core-merge to amend pass 1's work to the shipped seam and
execute D8-D14. CodeGraph checked first (`.codegraph/` at
`/Users/nerya/LexGraph` tracks `main`, confirmed resolving `RuleContext` at
`registry.py:63` per S-R8) but per the manager's binding process note, every
file this branch actually differs on (`registry.py`, `us_scope_trigger_
proof.py`, `il_scope_triggers.py`, `matcher.py`, `pipeline.py`, `us_profile.py`)
was verified by direct read, not trusted from the index. No discrepancy
found between CodeGraph's main-state view and the branch's own checkout for
any of these files.

### D8 — part/subchapter chapter-fallback measurement (S-R5's open question)

Two scripts (scratchpad, not committed): `d8_part_subchapter_measure.py`
(row-level `chapter` field presence) and `d8_breadcrumb_structural.py`
(real breadcrumb JSON parsed structurally, not by regex-on-a-label). Same
12 lead states, same "genuine" bar (quote+idiom-or-colon-list) as D1/D3, so
the population is directly comparable to the existing 2,187/1,861 counts.

**Headline the manager asked for**: row-level `chapter` field is non-null
for **100% of genuine part hits (2,187/2,187) and 100% of genuine
subchapter hits (1,861/1,861)**. Taken alone this looks like a green light
for fallback (a). It is not the full picture — the row-level `chapter`
FIELD being populated is not the same claim as "the part/subchapter
genuinely nests inside that one chapter," which is what fallback (a)
actually needs to be sound. Re-measured structurally, from real breadcrumb
JSON (not the name alone, per the instruction):

- **`part`**: only **32.0% (700/2,187)** of genuine hits have breadcrumb
  confirming `chapter` as the IMMEDIATE parent of a `part` node (`title >
  chapter > part > section` — genuinely a subdivision of that one chapter,
  fallback (a)-safe). **67.9% (1,484/2,187)** have NO `part` node in
  breadcrumb at all (mostly UT, whose breadcrumb schema folds part-like
  grouping into a compound `chapter` field, e.g. `"81-8"`, instead of a
  separate level) — fallback (a)'s soundness is UNVERIFIABLE from this
  corpus's breadcrumb granularity for these rows, not confirmed either way.
- **`subchapter`**: **0% (0/1,861)** have a `subchapter` breadcrumb node
  ANYWHERE, in ANY of the 12 lead states — completely unverifiable
  structurally in this population.
- **The counter-example the manager asked me to watch for, found**: **3
  Maine rows** (`STATE_ME_T12_P13_C913_S10803`, `STATE_ME_T25_P6_C315_
  S2396-A`, `STATE_ME_T12_P11_C807_S9331`) have breadcrumb type sequence
  `title > part > chapter > section` — Maine's real statutory hierarchy
  nests `chapter` INSIDE `part`, the OPPOSITE direction fallback (a)
  assumes. A `"for purposes of this part"` definition in Maine spans
  MULTIPLE chapters; stamping `scope="chapter"`, `source_chapter=ctx.
  chapter` would UNDER-link every mention in a sibling chapter under the
  same part — a real zero-miss-bar violation for at least this state, not
  a hypothetical one. (3/2,187 = 0.14% of this SAMPLE's part hits, but this
  sample is only 12 of 51 US jurisdictions — Maine's own structure is a
  real, known, page-documented convention, so this is not noise to
  discount, only small in THIS measured population.)
- A crude first pass (label-regex cross-tab, not breadcrumb-structural)
  flagged 158 "(unit,title,label) -> multiple chapters" collisions before
  I re-checked structurally; ALL of those turned out to be MT/other states'
  own chapter-RELATIVE part numbering (e.g. MT's "Part 2" recurs under many
  different chapters because part numbers reset per chapter — different
  parts sharing a number, not one part spanning chapters). Flagging the
  false lead so nobody re-discovers it: the label alone is never a safe
  join key across chapters; only the full breadcrumb path is.

**Not picking, per the instruction.** Fallback (a) chapter: sound for the
32.0% of `part` hits breadcrumb can confirm, unverifiable for the rest,
and actively wrong (under-links) for at least Maine. Fallback (b)
law-wide: zero-miss-safe everywhere, unbounded over-link everywhere. This
does NOT kill both fallbacks (law-wide always remains safe), so this is
not an `ESCALATION:`-tagged hard stop per this sprint's own rule — it is
exactly the "report and let the manager rule" case D8 asked for. My own
read, offered as data context rather than a pick: the Maine counter-example
plus subchapter's 0% structural verification rate makes a UNIFORM
chapter-fallback hard to defend as sound across all 51 jurisdictions
without a per-state carve-out (e.g. "chapter-fallback everywhere except
ME's part-scoped rows, which get law-wide") — but that is the manager's
call, not mine.

### D9 — scope-string test amendments

Amended to the shipped vocabulary (local/chapter/subsection enforced;
law-wide unrestricted; any other literal string dead per S-R5):

- `"act"` -> `"law-wide"` (D3's own mapping, no ambiguity).
- `"article"`/`"title"` (residue kinds the manager already agreed to defer,
  pre-rebase escalation entry) -> `"law-wide"`, applying core's OWN AK-range
  fallback precedent rather than stamping a literal guaranteed to link
  nothing — 6 tests amended across the trigger-axis and body-axis files
  (renamed where the test name itself encoded the old scope string).
- `"part"`/`"subchapter"` -> **left unamended, literal strings kept,
  PENDING the manager's D8 ruling** — explicitly flagged in each affected
  test's own docstring/comment (5 tests: 2 trigger-axis mapping tests, 1
  bare-trigger test, 2 body-axis over-split tests) so nobody mistakes the
  current literal as a final answer. This is the "legitimate stop" the
  brief allowed for — D9 is NOT fully closed until D8 is ruled on.
- S-R7 (`scope_value` transient) — checked, nothing to fix: `grep -rn
  scope_value` across every test file this sprint owns returns zero hits.
  No test ever asserted a persisted `.scope_value` in the first place.
- Found and fixed a REAL bug in pass-1's own tests while re-running the
  suite (see D13): two pipeline-live tests read `a["object_entity_id"]`/
  `a["subject_entity_id"]` directly off `created_assertions` summary dicts,
  which per `pipeline.py`'s own `_create_assertion` only ever carry `{id,
  assertion_type, proposition, status, origin}` — a `KeyError` waiting to
  happen the moment Phase A lands and real assertions start getting
  created (currently masked because `created_assertions` is `[]` today, so
  the list comprehension's filter body never executes). Fixed both to
  fetch the persisted `Assertion` row by id instead, matching `test_
  definition_links_pipeline_live.py`'s own documented contract.

### D10 — core-overlap dedup: CONFIRMED, verified live, not deferred

Rather than wait for Phase A/B to construct a real two-rule overlap (our
own module doesn't exist yet), the new test (`test_us_scoped_inline_
pipeline_core_overlap_dedup.py`) registers its OWN second, throwaway
`ScopeTriggerRule` at test time — same `register_scope_trigger_rule`
pattern core's own `test_definition_links_rules_registry.py` already uses
directly in test bodies — gated on a nonce string embedded only in this
test's own synthetic row body, so it cannot affect or be affected by any
other test regardless of execution order (verified: full suite re-run
before/after, identical pass/fail counts elsewhere).

**Result: PASSES today**, live, on the real `run_definition_linking`
path. Core's proof rule and the throwaway rule both match `'As used in
this section, "Widget" means ...'`, both independently produce a
`DefinitionCandidate`, and the pipeline's Stage-2 `(article_id, sorted(
terms))` dedup key collapses them to exactly ONE `Definition` row, with
exactly ONE `USES_DEFINITION` assertion for the single in-article reuse.
**Verdict: the seam spec's dedup claim HOLDS**, proven, not assumed. This
test is a live proof today, not a Phase-B tripwire — it does not depend on
the Developer's own module existing at all.

### D11 — routed CLAUSE package: verified, effectively ~99% accurate

147-row stratified sample (min(3, available) per jurisdiction, seed
`20260804`, all 51 jurisdictions, reproducible), pulled from the REAL
parquet by `act_id` (0 not-found). First pass (`d11_verify_clause_
package.py`, the SAME "genuine" heuristic D1/D3/D8 used) measured only
**58.5% (86/147)** confirmed — misleadingly low. Manual review of the 61
flagged rows found the heuristic itself was the problem, not the package:
it required a QUOTED term immediately followed by one of 5 idiom words,
missing an entire, very common convention — `the term X means/shall
mean/does not include/refers to/shall be construed to mean/has the same
meaning as`, UNQUOTED (AL/AZ/CO/CT/HI/IA/ID/KS/KY/LA/MA/MI/ND/NE/NH/NJ/NM/
OK/OR/RI/TN/TX/VA/VT/WA/WI/WV/WY all hit this in the sample) — plus
Missouri's own house style, `"Term" , definition`, comma, no idiom
keyword at all. Broadened the heuristic (`d11_verify_clause_package_v2.py`,
same seed -> same 147 rows) to cover both, plus fixed two mechanical gaps
(only checking the FIRST trigger match per row, missing a genuine trigger
sitting right after an earlier bait phrase; not unescaping the literal
`\n` corpus artifact `ingest_us_statutes.py` itself already documents,
M14/I8) -- **79.6% (117/147) automated, then manually read every one of
the remaining 29** (curly-quote/mojibake quote variants, "shall be X as
defined in", intervening qualifier phrases breaking idiom adjacency, etc.
— every single one is a genuine definition on a plain read). **Net
verdict: 146/147 = ~99% accurate.** The one exception (`STATE_SD_T7_C18A_
S7-18A-38`, heading `"...Enforcement--Definition"`) is a legitimate F3
boundary case (S-R3: heading recognized as Definitions -> not ours,
regardless of trigger), not a wrong CLAUSE classification — arguably still
a defensible inclusion, just not this family's to capture. This is well
above any accuracy threshold that would warrant the "package untrustworthy"
escalation trigger — not escalated.

**Folded into the item list**: `STATE_MO_C44_S44.091` added to the fixture
(real, unmodified, 3-term row) — the comma-appositive convention found
during verification is a genuinely NEW body-shape D1's original 12-state
inventory missed, and MO is the single largest package contributor (456
rows) using it pervasively. New test:
`test_quote_comma_appositive_no_idiom_keyword_missouri` (body-axis file).
Did not fold in every other package row as a fixture — per the deliverable
and the package's own doc, this is a verification pass, not a
re-classification of all 2,659 rows.

### D12 — U4 denominator: designed, written into the contract

Full design + the signal-agnostic proof plan is in the sprint contract
(`2026-08-04-defs-us-scoped-inline.md`)'s new `## D12` section, not
duplicated here. Headline: sample BEFORE any trigger regex touches the
text (the step that actually breaks circularity), judge with an
INDEPENDENT semantic method (not a broader regex — D11's own experience
this pass is the argument: even a carefully broadened regex still needed
a manual pass to catch idiom variants a semantic reader would not miss),
cross-validate with a second judge, and PROVE non-circularity by measuring
divergence between the judge and this family's own trigger regex on the
same sample (perfect agreement would be the red flag, not the goal). Not
run — QA's job, design only, per the deliverable.

### D13 — RED re-proven, contract updated

`backend/.venv/bin/pytest backend/tests -q` (worktree root):

```
38 failed, 704 passed, 18 warnings in 18.52s
```

644 -> 704 passing confirms the PRE-EXISTING suite grew (core's own merge
added tests) and stayed fully green — none of the growth is from this
family. 38 failing, all from this family's own 5 test files (39 before
the `object_entity_id` fix flipped the D10 dedup test to passing on its
own merits): `ModuleNotFoundError: No module named 'app.definition_links.
rules.us_scoped_inline'` for every unit test (33 across trigger-axis/
body-axis/negative-controls), real `AssertionError`s against the
unmodified, current `run_definition_linking` for the 4 integration tests
in `pipeline_live.py` (a sample tail: `AssertionError: the real production
pipeline recognized ZERO definitions in a real Utah 'For purposes of this
section, "concurrence" means...' article -- got [] definitions from []
assertions`). Baseline-regression file (`pipeline_baseline_regression.py`)
stays green, unchanged, confirming U5's tripwire is intact.

**Major finding for the manager, not a doc/code disagreement but a
SEPARATE, real defect in core's shipped `resolve_unit_path`**: verified
live (`us_profile.resolve_unit_path`, direct execution against the real,
unmodified `STATE_ME_T38_C3_S464` fixture row's full text) that Maine's
authentic statutory formatting embeds bracketed legislative-history
annotations inline in the body — `[PL 1985, c. 698, §15 (NEW).]`,
`(AMD)`, `(AFF)` — and `resolve_unit_path`'s marker regex
(`\(([A-Za-z]+|\d+)\)`, no history-annotation awareness) mis-parses every
one of these as a real nested sub-article marker, producing a ~30-deep
garbage stack (`UnitStep(kind='sub', value='NEW')`, repeated) utterly
unrelated to the statute's real `"2-A."` subsection structure. This means
`"subsection"` scope — counted in S-R4's 82.0% shipped-and-enforced figure
— is UNRELIABLE for at least Maine (and plausibly other states using a
similar inline-annotation convention; not checked beyond the fixture's own
12 lead states, where this pattern is otherwise absent — checked: only
ME's two rows show it, 0/23 other fixture rows do). Out of this sprint's
remit to fix (`us_profile.py` is core's shared module, S-R2 forbids
editing it) — reported here, and the pre-existing pipeline-live subsection
test's docstring was corrected (it previously, incorrectly, still claimed
subsection is "not enforced today," stale post-merge) rather than silently
upgraded into a full live-enforcement proof that would have conflated this
separate core bug with this family's own correctness.

**Contract updated** (`## Next Steps`): Phase A and B are now COLLAPSED
into one step — verified live that `pipeline.py`'s `else:` branch already
calls `profile.extract_local_scope_definitions`, which already unions
every registered `ScopeTriggerRule` for the document's jurisdiction code,
so a new rule module needs no separate "register" or "wire into
pipeline.py" step at all, only to exist as a file in `rules/`. Also
corrected: `extract_local_scope_definitions` auto-defaults ONLY
`.source_article_number`, never `.source_chapter` — the module's own
adapter function must stamp `source_chapter=ctx.chapter` itself for a
`scope="chapter"` candidate, a requirement the pre-merge draft had located
in the wrong place (a pipeline.py edit that no longer needs to happen at
all). New `## D12` section added for the denominator design.

### Files changed this pass

- `backend/tests/fixtures/us_statutes/us_scoped_inline_rows.json` (+1 real
  row, `STATE_MO_C44_S44.091`)
- `backend/tests/fixtures/us_statutes/README.md` (+provenance section)
- `backend/tests/unit/test_us_scoped_inline_rules_trigger_axis.py` (scope-
  string amendments, docstring rewrite, still 298 lines)
- `backend/tests/unit/test_us_scoped_inline_rules_body_axis.py` (scope-
  string amendments, +1 new test, 289 lines)
- `backend/tests/integration/test_us_scoped_inline_pipeline_live.py`
  (`object_entity_id` bug fix x2, stale subsection docstring corrected,
  298 lines)
- `backend/tests/integration/test_us_scoped_inline_pipeline_core_overlap_dedup.py`
  (NEW, D10, 127 lines)
- `docs/sprint/sprints/2026-08-04-defs-us-scoped-inline.md` (Next Steps
  rewritten, new D12 section)

No production code touched (role boundary held — grep-verified: zero
non-test, non-doc files in `git diff --stat` against this pass's own
starting commit).

### Open items for the manager

1. **D8 ruling needed** to finish D9: chapter-fallback vs. law-wide-
   fallback for `part`/`subchapter` (or a per-state split, given Maine).
   5 tests currently pin the literal `"part"`/`"subchapter"` strings as a
   flagged placeholder, not a final answer.
2. **`resolve_unit_path`'s Maine defect** (D13) — a real, separate core
   bug, not this family's to fix, affecting the 82.0% "shipped and
   enforced" figure's real-world reliability for at least one state.

---

## 2026-08-04 — Manager: Planner pass 2 verified; ruling S-R9 (part/subchapter fallback)

### Handoff verification

`git diff --name-only origin/main...HEAD` → tests + docs only, **zero
production files**. Role separation held across both Planner passes.
Independently re-ran the suite: **38 failed, 704 passed** (pre-existing suite
green at 704, up from 644 pre-merge — core's own tests came in with the
rebase), so RED remains fully attributable to our tests. D10's dedup test
passes live (`1 passed`) — correct, it is a green pin on core's existing
behavior, not a RED item.

Credit where due: the Planner caught a latent bug in its OWN pass-1 tests —
two live-path tests read `a["object_entity_id"]` off `created_assertions`
summary dicts, which `pipeline.py` only populates with
`{id, assertion_type, proposition, status, origin}`. That would have thrown
`KeyError` the moment assertions started being created, i.e. it would have
masked a real green. Exactly the kind of thing the "prove it, don't assert it"
discipline is for.

### S-R9 — part/subchapter/residue fall back to `"law-wide"`, NOT to `"chapter"`

The Planner reported 3 Maine rows nesting `title > part > chapter > section`.
I verified this myself against `us_me_statutes.parquet` and it is far stronger
than reported: **12,543 Maine rows** have a `part` node ABOVE a `chapter` node
in their real breadcrumb, and a single Maine Part spans up to **106 distinct
chapters** (Part 2 → 106; Part 4 → 84; Part 9 → 61; Part 1 → 44).

That is decisive. Mapping a `part`-scoped definition to `scope="chapter"`
would link only the defining article's own chapter and silently MISS the other
105 chapters inside the same Part. Under-linking is disqualifying under the
director's absolute zero-miss bar (program decision 3). The 100% non-null
`chapter` field was a red herring — the field being present says nothing about
whether the chapter CONTAINS the part; here it is the other way round.

**Ruling: `part`, `subchapter`, and the residue kinds (`article`, `title`,
`paragraph`, `division`, `subdivision`, `subpart`, `act`) stamp
`scope="law-wide"`.** This follows core's own published precedent for exactly
this shape (seam v2 §1, AK multi-chapter ranges): an unrepresentable narrowing
falls back to law-wide — zero-miss-safe, with the precision cost recorded
rather than silently taken. Rejected alternative (a) `scope="chapter"`: proven
to under-link at scale. Rejected alternative (c) stamping the literal kind
(`"part"`): ruling S-R5 showed `_in_scope`'s generic branch is dead on the live
path, so it would link nothing at all — the worst outcome available.

**This stays a NAMED OPEN CONFLICT CLASS under P-R2**, not a settled question:
law-wide over-links beyond the declared scope, which is in real tension with
the director's "assertions only to mentions within the section they are
specified for." It affects `part` (2,187) + `subchapter` (1,861) = 13.9% of
genuine volume plus ~4.0% residue. Re-escalated with measured volume numbers
after QA's U4 sweep, together with the PA construction-clause pin. The
principled fix is core gaining a live above-article generic-unit path; that is
core's to build, not ours.

### Routed OUT to the program manager (not ours to fix)

The Planner found a genuine defect in core's SHIPPED `resolve_unit_path`: it
mis-parses Maine's inline legislative-history annotations (`(NEW)`, `(AMD)`,
`(AFF)`) as sub-article markers, producing garbage nesting. This degrades
subsection-scope enforcement — part of the "82% enforced" figure — for every
panel, not just ours. Per the sprint's boundary rule this is REPORTED, never
fixed here.

---

## 2026-08-04 — Manager: Developer handoff verified; ruling S-R10

### Verification (manager-run)

- `git diff --name-only origin/main...HEAD` → exactly ONE production file,
  `backend/app/definition_links/rules/us_scoped_inline.py`, **299 lines** (under
  the gate). Everything else in the diff is the Planner's own earlier commits.
  Zero test files touched by the Developer. Role separation held.
- Suite re-run by me: **5 failed, 737 passed** — matches the report.
- I did NOT accept the "all 5 are placeholder scope-string tests"
  characterization on trust: two of the five are named
  `..._numbered_elaboration_list_is_not_split...` and
  `..._shared_clause_own_numbered_list_not_split_tennessee`, which sound like
  splitting-behavior failures, not scope-string ones. Checked the actual
  assertions: both fail on `assert ... .scope == "part"` → `'law-wide' == 'part'`.
  Same class after all; the substantive splitting assertions above those lines
  PASS, so the rule's entry-splitting behavior is correct.
- Confirmed the 5 are legitimate amendments, not test-fitting: each carries an
  explicit `PENDING D8/S-R5 ruling ... placeholder` comment written BEFORE
  S-R9 landed. Amending them implements the ruling; it does not bend a test to
  match code. Planner-role work, correctly routed away from the Developer.
- Read the production file. `_SCOPE_BY_UNIT` implements S-R9 exactly. The
  precision gate is real: bare `In this <unit>` requires strict comma/colon
  adjacency, matching the measured ~21%-genuine rate, rather than being widened
  until negative controls happened to pass. `_extract` stamps
  `source_chapter=ctx.chapter` for chapter scope with a comment naming the exact
  trap I identified in S-R4 — a `"chapter"` candidate with `source_chapter=None`
  would silently match only articles whose chapter is also `None`.

Verdict: Developer handoff ACCEPTED.

Process credit, recorded per the program manager: a cross-session check-in
caught the Developer's `_MARKER`/`_MARKER_RE` typo — which broke pytest
COLLECTION for the entire suite, since `rules/__init__.py` auto-imports every
module — and the 309-line overage, mid-task after an API stall. Both were
verified independently and fixed before the handoff.

### S-R10 — subsection `scope_value` gets a REAL test, not a deferral

The program manager's lean was to record the unpinned `scope_value` derivation
as a named deferral until core's Maine annotation fix lands. **I am overruling
that**, because the risk is not cosmetic:

`us_scoped_inline._subsection_label` derives a label with its OWN regex
(`_SUBSECTION_LABEL_RE`), while `matcher._subsection_contains_offset` compares
that label against `profile.resolve_unit_path(article, char_offset)[0].value` —
a SECOND, INDEPENDENT derivation living in core. Nothing currently proves the
two agree. If they disagree, a subsection-scoped definition links NOTHING —
a silent under-link, which is precisely the failure mode the absolute zero-miss
bar exists to prevent, and precisely the failure mode that unit-green-but-
live-dead testing hides (the same shape as core's own C1 QA bounce).

Note the coverage gap this exposes: this sprint's U2 both-directions proofs
cover `local` and `chapter` only. Subsection enforcement is NOT proven on our
live path. Core proved the MECHANISM both directions; what is unproven is that
OUR rule's label matches what core's resolver returns.

The deferral argument — that the Maine fix will change nearest-marker edge
cases — argues against pinning an exact literal string, and I accept that. It
does not argue against pinning AGREEMENT. Planner pass 3 therefore writes a
live-path test asserting that a subsection-scoped definition links an in-
subsection mention and does NOT link an out-of-subsection one, without
hard-coding the label's literal value. That test should survive core's Maine
fix unchanged; if it fails now, we have found a real defect rather than
deferred one.

Model note: pass 3 is Sonnet/high, not Haiku — the 5 amendments are mechanical,
but S-R10's test is genuine live-path test design.

---

## 2026-08-04 — Planner (pass 3)

CodeGraph checked first (`codegraph explore` from `/Users/nerya/LexGraph` for
`_subsection_label`/`_subsection_contains_offset`/`resolve_unit_path`) --
confirmed against the branch's own on-disk source by direct read per the
manager's binding process note, no discrepancy.

### Task A — 5 placeholder scope assertions amended per S-R9

All 5 amended to `"law-wide"`, `PENDING D8/S-R5` comments replaced with a
short S-R9 citation (unrepresentable narrowing -> law-wide, zero-miss-safe,
precision cost recorded), matching the D9-pass precedent already set for
`"article"`/`"title"`. Two tests renamed (`..._maps_to_subchapter_scope` ->
`..._falls_back_to_law_wide_scope`, `..._maps_to_part_scope` -> same) since
the old names asserted the literal as fact; the other 3 kept their names
(never encoded the scope string). Module docstring's mapping table
(trigger-axis file) updated to mark `part`/`subchapter` RESOLVED rather than
PENDING, for consistency with the S-R9 ruling now landed. No other
assertion in any of the 5 tests touched -- the splitting/term assertions
(`len(matches) == 1`, term-set memberships, `definition_text` substring
checks) are byte-identical to before. `grep -n "PENDING D8"` across both
files now returns zero hits. Re-ran the full unit suite for both files
standalone: **28/28 passed**, confirming the amendments and nothing else
broke.

`trigger_axis.py` grew to 320 lines with the first draft of the new
docstrings/comments -- over the 300-line gate -- tightened the same
material (S-R9 reasoning kept, wording compressed) down to **297 lines**,
re-verified the 28/28 pass held after trimming. `body_axis.py`: **295
lines**, comment-only changes, no risk of drift.

### Task B — ruling S-R10: subsection-label agreement, LIVE-TESTED, FAILS

New file `backend/tests/integration/test_us_scoped_inline_pipeline_subsection_live.py`
(211 lines), two tests, both driving the real `ingest_us_statute_rows` ->
`run_definition_linking`. Row: the real, unmodified `STATE_OR_T22_C238_
S238.300` (Oregon -- deliberately NON-Maine, so the known Maine-annotation
defect cannot be blamed for the result). Its own real text defines
`"number of years of membership"` via `"(c) As used in this subsection, ...
means..."`, and NATURALLY (no invented prose) reuses the term twice more
later in that SAME `(c)` clause, and twice earlier in a DIFFERENT clause
(`(2)(a)(A)`/`(2)(a)(B)`) of the SAME article, before the definition even
appears -- real, both-directions material in one row, ground-truthed via
`re.finditer` against the real text in both tests, no hard-coded offsets or
label literals anywhere.

Design note on the two-test split: Stage 3's assertion dedup key is
`(subject, object, proposition)`, not per-mention, so a single ingest with
BOTH kinds of mention present at once cannot attribute a resulting (or
missing) `USES_DEFINITION` edge to either direction specifically. The
"different subsection" test therefore ingests the SAME real row's text
MECHANICALLY TRUNCATED right after the defining sentence ends -- every
remaining character is a real, verbatim substring of the vendored row nothing
invented -- which drops the two later in-subsection reuses while keeping the
two earlier out-of-subsection ones and the definition itself intact, so any
edge in that scenario is unambiguously attributable.

**Result, independently reproduced via `pytest backend/tests -q`: 1 failed,
743 passed** (742 + this file's 2 new tests, 1 of each). Broken down:

- `test_subsection_scoped_definition_does_not_link_a_mention_in_a_different_
  subsection` -- **PASSES**. Non-vacuous: ground-truthed 2 real
  out-of-subsection mentions exist in the truncated body before asserting.
- `test_subsection_scoped_definition_links_a_mention_inside_its_own_
  subsection` -- **FAILS**. `assert uses_edges` -> `assert []`. The real,
  unmodified Oregon definition is captured correctly (`scope ==
  "subsection"`), but its own later in-article, in-subsection reuse gets
  ZERO `USES_DEFINITION` edges. Exactly the silent under-link S-R10
  predicted.

**Root cause, isolated by direct execution (not guessed), and NOT
Maine-specific -- a plain format mismatch, general to every parenthetical-
style subsection label**: `us_scoped_inline._subsection_label`'s capturing
group `\([0-9A-Za-z]{1,3}\)` includes the literal parens in the returned
string (e.g. `"(c)"`). `us_profile.resolve_unit_path`'s marker regex
`\(([A-Za-z]+|\d+)\)` captures only the INSIDE content (e.g. `"c"`, no
parens) into its `UnitStep.value`. `matcher._value_matches` is a plain `==`
(no normalization). So `"(c)" == "c"` is `False` by construction, for EVERY
parenthetical-style subsection label, in EVERY jurisdiction, independent of
whether the nesting-depth algorithm itself is otherwise correct.

Verified live (scratch, not committed) that `resolve_unit_path` compounds
this: its "kind ladder" (`lower_alpha, digit, upper_alpha, ...`) predicts
the OUTERMOST marker is always `lower_alpha`; the Oregon row's real
outermost marker is `"(1)"` (digit), so it is pushed as an unrecognized
`"sub"` step at stack position 0 -- and `_marker_matches_kind` never
recognizes `"sub"` as replaceable, so position 0 stays frozen at `('sub',
'1')` for the REST of the document. Confirmed empirically: all 5 real
occurrences of "number of years of membership" in the row (2 out-of-
subsection, 1 defining, 2 in-subsection) resolve to the IDENTICAL
`path[0] == UnitStep(kind='sub', value='1')`, regardless of true position --
`"(c)"` never matches `"1"` either way. Two independent, compounding defects
in `us_profile.py` (core's shared module, out of this sprint's role/file
remit -- reported, not patched, per the brief).

**Per the brief: STOPPING here. Test written, run, failure verified and
root-caused; `us_scoped_inline.py` NOT touched.** `git diff HEAD --
backend/app/definition_links/rules/us_scoped_inline.py` is empty.

---

## 2026-08-04 — Manager: S-R10's test found a real defect; ESCALATED

Ruling S-R10 (pinning AGREEMENT rather than deferring) was the right call: the
test it mandated fails, and I reproduced the root cause myself rather than
taking the Planner's diagnosis on trust.

**Reproduced live** on the real vendored Oregon row `STATE_OR_T22_C238_S238.300`
(deliberately non-Maine, so the known annotation defect cannot confound it):

- our rule stamps `scope_value = '(c)'`
- `profile.resolve_unit_path(article, char_offset=...)` returns
  `[('sub', '1'), ('digit', '1'), ('upper_alpha', 'A')]` at the first mention
  and `[('sub','1'), ('digit','1'), ('upper_alpha','B')]` at the second
- `_subsection_contains_offset` compares `mention_path[0].value in allowed`
  → `'1' in ('(c)',)` → **False, always**

So a `scope="subsection"` definition links NOTHING on the US live path. Three
independent problems compound:

1. **Format**: our rule emits `'(c)'` with parens; `UnitStep.value` is bare
   (`'c'`). `matcher._value_matches` is a plain `==` with no normalization.
   Arguably ours to fix (the seam does say a rule stamps a bare label).
2. **Level semantics — the real one**: `_subsection_label` takes
   `matches[-1]`, the NEAREST-preceding (innermost) marker;
   `_subsection_contains_offset` compares `mention_path[0]`, the OUTERMOST step
   of a root-to-leaf path. These are different levels by construction, so they
   disagree for ANY nesting deeper than one level — fixing the parens alone
   would not help.
3. **Resolver bug (core's)**: `resolve_unit_path`'s outermost slot comes back
   as the unrecognized kind `'sub'` with value `'1'` when a document's real
   outermost marker is a digit — the near-universal US convention. Distinct
   from, and broader than, the already-routed Maine `(NEW)`/`(AMD)` defect.

Note how this got missed upstream: `_subsection_contains_offset` has an earlier
branch reading `getattr(article, "subsections", None)`, which core's own code
comments describe as existing only for `SimpleNamespace` test stubs — "a real
`MatcherArticle` never has it". Tests taking that branch go green while
production takes the `resolve_unit_path` branch. That is the same
unit-green-but-live-dead shape as core's own C1 QA bounce, recurring one level
down, and it is why S-R10 refused the deferral.

**Scope of impact**: `subsection` is 1,297 genuine hits = 4.5% of this family's
volume, and the mechanism is shared, so every panel stamping subsection scope
is affected. Under the absolute zero-miss bar a silent under-link is a U2/U4
gate failure on that slice.

Escalated to the program manager. Not fixed here: `us_profile.py`/`matcher.py`
are shared modules gate U3 forbids this sprint from touching, and the level-
semantics question is core's contract to state, not ours to pick.

---

## 2026-08-04 — Manager: ruling S-R11 (subsection interim), approved by the program manager

**S-R11 — `subsection` maps to `"local"` for the interim.** Approved exactly as
escalated: option (b) now, (a) — core's level-contract fix — in parallel.

Rationale, same shape as S-R9: an unrepresentable narrowing falls back to the
NARROWEST REPRESENTABLE enclosing unit. For part/subchapter that was
`law-wide`; for subsection the narrowest representable enclosing unit is
`local`, the owning article. Zero-miss-safe by construction (a subsection is
always inside its article), and the over-link is bounded by a single article —
far tighter than `law-wide`.

**Named conflict class #3**, re-escalated with volume numbers after the U4
sweep alongside S-R9's law-wide fallback and the PA construction-clause pin.
**Revert condition, explicit:** true subsection scope resumes the moment core's
level-contract fix lands.

**Revert must be self-alarming, not a calendar reminder.** S-R10's live-path
test is kept as the post-core flip target and marked
`pytest.mark.xfail(strict=True)`: it stays an expected-fail today, and the
moment core fixes the resolver it XPASSes — which under `strict=True` FAILS the
suite and forces us to flip the mapping back. A plain skip or a deleted test
would let the interim ossify silently, which is the failure mode this whole
escalation was about.

Core-owned halves routed out with our evidence: the level-semantics contract
(program manager's guidance to core: the trigger word names the level — US
drafting's "subsection" = outermost lettered unit, "paragraph" = digit level —
so containment compares at the trigger-named level, not always `path[0]`), the
digit-outermost `'sub'` mislabeling (RED from our Oregon row), and the
stub-branch QA-shape lesson.

Format alignment is ours: `_subsection_label` must emit BARE labels (`c`, not
`(c)`) to match `UnitStep.value`'s convention, so the post-core flip is
format-clean rather than needing a second fix.

---

## 2026-08-04 — Planner (pass 4)

Verified S-R11 against the actual commits before implementing (`git show
79ee374`/`34b576f` in full, not just the chat summary) -- both the escalation
and the ruling are recorded exactly as described, root-caused independently
by the manager on the same real Oregon row, extending my own pass-3 finding
with a third precise cause (innermost-vs-outermost level mismatch, not just
paren-format + the digit-`'sub'` bug). S-R11 itself looks sound: same
zero-miss-safe-narrowest-representable-unit logic as S-R9, self-alarming
revert designed in from the start. Nothing to escalate; implemented as ruled.

### Task 1 — pin the interim

Amended every test asserting `scope == "subsection"` outside the kept-as-is
S-R10 file (grep-verified, zero missed) to `"local"`, each with a comment
citing S-R11 and the revert condition:

- `test_us_scoped_inline_rules_body_axis.py`, 3 assertions --
  `test_bare_quote_means_subsection_scope_maine`,
  `test_bare_quote_means_subsection_scope_oregon`,
  `test_colon_then_lettered_list_oregon_capital_letters`. Names left
  unchanged (not asked for this pass); only the asserted value + a comment
  changed. No other assertion in these tests touched.
- `test_us_scoped_inline_pipeline_live.py`'s
  `test_a_scope_unit_not_yet_enforced_by_matcher_is_still_stamped_faithfully`
  -- docstring rewritten (the old "SHIPPED and live-enforced, S-R4" claim is
  now stale post-S-R10), assertion changed to `"local"`.
- `test_us_scoped_inline_rules_trigger_axis.py`'s module docstring mapping
  table updated for consistency (no test assertion in that file itself
  referenced `"subsection"`, only the docs).

Two of these files (`trigger_axis.py`, `body_axis.py`) went briefly over the
300-line gate while drafting the S-R11 prose; tightened back under (299/299)
without cutting any of the reasoning, re-verified after trimming.

### Task 2 — the revert, made self-alarming

`test_us_scoped_inline_pipeline_subsection_live.py` (pass 3's S-R10 file) is
KEPT UNCHANGED in its assertions -- still pins TRUE subsection behavior, not
the interim -- with `@pytest.mark.xfail(strict=True, reason=...)` added to
`test_subsection_scoped_definition_links_a_mention_inside_its_own_subsection`
(direction 1). `reason=` names S-R11, the two remaining core-owned causes
(innermost-vs-outermost level mismatch; `resolve_unit_path`'s digit-outermost
`'sub'` mislabeling), and the exact revert condition (core's level-contract
fix + the Developer flipping `_SCOPE_BY_UNIT["subsection"]` back).

**Direction 2 deliberately NOT marked xfail this pass**, and I want this
decision visible rather than silently made: `test_subsection_scoped_
definition_does_not_link_a_mention_in_a_different_subsection` PASSES today
(nothing links at all, for the wrong reason -- the same bug direction 1
exposes). `pytest.mark.xfail(strict=True)` on an already-passing test
registers as XPASS, which strict mode turns into an immediate FAILURE -- so
marking it now, before the Developer's production-side S-R11 change lands,
would break the suite today for a reason unrelated to S-R11 itself. The real
risk is forward-looking, and I'm flagging it explicitly (also in the test
file's own docstring) so it doesn't quietly slip through: once `_SCOPE_BY_
UNIT["subsection"]` actually becomes `"local"` in production, a `"local"`-
scoped definition legitimately over-links across its WHOLE owning article
(S-R11's own accepted tradeoff), so direction 2's "does not link a different
subsection" claim stops holding and this test needs ITS OWN `xfail(strict=
True)` at that point -- a follow-up for whoever lands that change, not
something I could safely do today.

### Task 3 — noted, not acted on

`scope_value` continues being stamped by the pure rule function regardless
of the interim mapping (verified: `_subsection_label` is still called
unconditionally when `scope == "subsection"` inside `_leading_events`/
`_embedded_entries`, upstream of the `_SCOPE_BY_UNIT` lookup that will decide
the FINAL `.scope` string) -- no test written asserting it goes unused,
per the instruction.

### Real suite tail -- does NOT match the DoD's "0 failures" expectation

`backend/.venv/bin/pytest backend/tests -q`, reproduced twice, stable:

```
FAILED backend/tests/integration/test_us_scoped_inline_pipeline_live.py::test_a_scope_unit_not_yet_enforced_by_matcher_is_still_stamped_faithfully
FAILED backend/tests/unit/test_us_scoped_inline_rules_body_axis.py::test_bare_quote_means_subsection_scope_maine
FAILED backend/tests/unit/test_us_scoped_inline_rules_body_axis.py::test_bare_quote_means_subsection_scope_oregon
FAILED backend/tests/unit/test_us_scoped_inline_rules_body_axis.py::test_colon_then_lettered_list_oregon_capital_letters
4 failed, 739 passed, 1 xfailed, 18 warnings in 12.48s
```

**Why, precisely**: `backend/app/definition_links/rules/us_scoped_inline.py`
(verified: `git diff 34b576f -- ...us_scoped_inline.py` is empty) still maps
`"subsection": "subsection"` in its own `_SCOPE_BY_UNIT` dict -- I amended
the TESTS to expect the ruled interim target (`"local"`) exactly as
instruction 1 asked, but the PRODUCTION mapping itself is the Developer's
change (point 3's preview: "the Developer will also normalize
`_subsection_label`..."), not mine to make (reiterated twice as a hard
constraint in the manager's message). These 4 failures are the identical
RED-pins-ahead-of-implementation shape this sprint has used throughout
(pass 1's 37 RED tests before the rule module existed at all) -- not a
mistake, and not something I can resolve without touching production code.
**Next step for the suite to reach 0 failures**: a Developer pass that maps
`_SCOPE_BY_UNIT["subsection"] -> "local"` and normalizes `_subsection_label`
to bare-label format (point 3), after which these 4 go green and the xfail
stays exactly as designed until core's fix lands.

### Verification

`git diff --name-only origin/main...HEAD` shows no file beyond this sprint's
own test/doc set; `git diff 34b576f -- .../us_scoped_inline.py` is empty
(zero production changes this pass). All 4 touched test files are
<=299 lines.

---

## 2026-08-04 — Planner (pass 5)

Confirmed the Developer's `23cbbdc` landed exactly as described before
touching anything: `_SCOPE_BY_UNIT["subsection"] -> "local"`,
`_subsection_label` now `.strip("().")` (bare labels), the 3 `scope_value`
stamping sites re-gated on the trigger's unit word. Re-ran the suite myself
rather than trusting the report: **1 failed, 742 passed, 1 xfailed**,
matching exactly -- the sole failure is direction 2
(`test_subsection_scoped_definition_does_not_link_a_mention_in_a_different_
subsection`), confirming pass 4's own flagged forward risk landed precisely
as predicted.

Skipped the suggested `git fetch && git reset --hard` -- checked first and
it was unnecessary: local `HEAD` already equalled `origin/claude/defs-us-
scoped-inline` at `23cbbdc` with a clean working tree, so a hard reset would
have been a no-op at best; ran a plain `git fetch` to confirm instead of the
destructive form.

### The marker

Added `@pytest.mark.xfail(strict=True, reason=...)` to direction 2 in
`test_us_scoped_inline_pipeline_subsection_live.py`, test body and
assertions byte-for-byte unchanged. `reason=` names: S-R11's interim
mapping as the cause (not a defect -- `"local"` legitimately over-links
across the whole owning article, the ruled tradeoff); that this differs
from direction 1's cause (core's still-broken `resolve_unit_path`, a real
defect) even though both share one revert; and the shared revert condition
(core's level-contract fix + `_SCOPE_BY_UNIT["subsection"]` restored ->
both markers come off together). Also updated the module docstring's
pass-4-era "direction 2 deliberately left unmarked" paragraph, since it was
now stale and would have misled the next reader -- replaced with a short
two-cause summary. File: 280 lines.

No production file touched (`git diff 23cbbdc -- .../us_scoped_inline.py`
empty).

### Suite tail

```
742 passed, 2 xfailed, 18 warnings in 13.04s
```

0 failed / 742 passed / 2 xfailed -- an internally consistent, correct
result (742 + 2 = 744, matching the pre-marker "1 failed, 742 passed, 1
xfailed" baseline with the 1 failure moved into the xfailed bucket). The
DoD's stated "743 passed" appears to be a minor arithmetic slip against the
manager's own reported starting tally; reporting the real, reproduced
number rather than the target figure.

---

## 2026-08-04 — QA (cycle 1, independent verification pass)

Workspace verified at `6cb5eef`. Read the contract (gates U1-U6), the full
log (S-R1..S-R11), and `us_scoped_inline.py` (read-only) before starting.
Zero implementation edits made -- `git diff --name-only origin/main...HEAD`
under `backend/app/` shows only `us_scoped_inline.py`, and that file's own
diff against this cycle's starting commit is empty (`git status --short`:
only 2 new untracked test/fixture files added by this cycle).

### U4 -- denominator audited, then independently re-executed (P-R7)

**Audit of D12's design**: sound. Sampling (pure `random.Random` draw over
`sorted(act_id)`-ordered rows, zero regex/keyword touch at draw time) and
judging (plain-language prompt, never given the trigger vocabulary) are
correctly separated, and D12's own honesty caveat (a sample bounds a rate,
it does not prove literal zero) is accurate. Adopted the design; did NOT
reuse the Planner's own D1 population (regex-built, correctly D12's own
target for what NOT to use as a denominator).

**Independent execution**: stratified random sample, N=10/jurisdiction, all
53 jurisdictions, 530 rows, seed `20260804`, drawn fresh from the real
parquet (script `qa_u4_sample.py`, scratchpad-only, grep-audited for zero
overlap with this family's trigger vocabulary in the actual sampling logic
-- the only vocabulary-adjacent text is prose comments). Reduced from D12's
suggested 200-300/jurisdiction for single-session judging capacity --
disclosed, not hidden; widens this sweep's confidence interval versus a
larger sample.

Judged by 7 independent parallel agent readers (6 primary batches, ~88-89
rows each, plus a 60-row cross-validation subsample judged blind by an
8th... 7th independent reader), each given ONLY the plain-language D12
prompt (term/scope/idiom vocabulary never mentioned). Cross-validation
agreement: **58/60 = 96.7%** (2 disagreements, both genuinely
borderline calls, not judge errors -- reasonable reliability for this
method). Aggregate: 82/530 batch positives (15.5%), 9/60 crossval
positives (15.0%) -- consistent rates across independent judge pools.

**Divergence proof (non-circularity)**: this family's own trigger regex,
run over the SAME 530 rows: 91.7% raw agreement with the judges, but the
INTERESTING cells are the disagreements -- 78.8% precision (14/66 regex
hits are bait the judges rejected) and only **63.4% recall** (the regex
never even fires on 30 of the 82 judge-confirmed genuine definitions).
Neither direction is empty and neither is near-total -- exactly the
"genuinely disagrees both ways" signature D12 said would prove
independence; perfect agreement would have been the red flag.

**Triage of the 82 judge-positives** (full untruncated text re-fetched from
parquet; routed through the REAL `is_definitions_heading` +
`derive_heading_from_body` rescue logic, then the real
`extract_us_scoped_inline_definitions`):

| Bucket | Count |
|---|---|
| F3_NOT_OURS (heading recognized, S-R3 boundary) | 18 |
| OUT_OF_FAMILY_NO_TRIGGER (no scope-unit trigger at all, not this family's remit) | 25 |
| CAPTURED | 17 |
| **CANDIDATE_MISS** | **22** |

**Manual read of all 22 CANDIDATE_MISS rows** (full text, trigger-match
context, rule output) found **12 rows are CONFIRMED real misses squarely
WITHIN this family's own already-claimed vocabulary** -- a recognized
STRONG trigger, a quoted term, a recognized idiom or colon-list, present in
the real text, yet the rule returns nothing -- across 8 distinct,
empirically isolated root causes (each verified by direct interactive
reproduction against the real, unmodified `extract_us_scoped_inline_
definitions`, not inferred from regex reading alone):

1. **Unmarked colon-then-quoted-list** (no parenthesized marker before
   each entry) -- `_leading_events` routes every colon-triggered event to
   `_multi_entries`, which ONLY recognizes marker-prefixed entries;
   `_single_entry` is never tried as a fallback. Loses the ENTIRE block,
   not just under-splits. Confirmed: `STATE_IL_C20_A2105_S2105-370` (2
   terms), `STATE_VA_T58.1_SI_C3_A10_S58.1-405.1` (7 terms). Most severe
   class found.
2. **Period-style list markers** ("1." "2." not "(1)" "(2)") --
   `_MARKER_RE` requires literal parens. Confirmed:
   `STATE_FL_TXVIII_C253_S253.04`.
3. **Chained parenthetical unit qualifiers** after the trigger's unit word
   (`this subsection (1)(a)(I)(A)`) -- `_UNIT_TAIL`'s optional qualifier
   group consumes only the first parenthetical. Confirmed:
   `STATE_CO_T39_A27_P1_S39-27-102`.
4. **Intervening secondary citation clause** between the unit word and the
   definiendum (`as used in this section AND [citation], the term X
   means`) -- `_STRONG_CONNECTOR_RE` has zero tolerance for inserted text.
   Confirmed on THREE independent rows:
   `STATE_DE_T6_C15_SIX_S15-901`, `STATE_OH_T17_C1707_S1707.47`,
   `STATE_OR_T62_C835_S835.200`.
5. **"the term:" with no space before the colon** breaks colon detection
   (the `the term\s+` connector alternative requires trailing whitespace
   before it can even try to reach a colon). Confirmed:
   `STATE_DC_T47_C20_S47-2002.01`.
6. **Connector vocabulary too narrow for "shall have (the following)
   meaning(s)"** -- only "(the following terms) mean/means" is recognized.
   Confirmed: `STATE_NY_ARPP_A8_S280-D` ("shall have the following
   meanings"), `STATE_MS_T27_C29_S51-5` ("shall have meanings as
   follows").
7. **Plural "have the same meaning as"** not recognized (only singular
   "has..."). Confirmed: `STATE_TN_T55_C9_S55-9-414`.
8. **Bare copula "is"** (without "defined as") not a recognized idiom.
   Confirmed: `STATE_ND_T50_C50-25.1_S50-25.1-09.1`.

Each of the 6 distinct root causes above (not counting the 2 duplicate-
class rows OH/OR and FL) is now pinned as a RED test with REAL,
unmodified, byte-verified corpus text: `backend/tests/unit/
test_us_scoped_inline_qa_cycle1_missed_conventions.py` (187 lines, 6
tests, all FAIL today against the unmodified rule) +
`backend/tests/fixtures/us_statutes/qa_cycle1_missed_conventions_rows.json`
(6 real rows, 6/6 byte-verified against the live parquet at fetch time).
Per QA's role boundary: tests only, `us_scoped_inline.py` untouched.

**Remaining 10 of the 22 CANDIDATE_MISS rows** (12 confirmed-bug rows
above + these 10 = 22, arithmetic checked), not pinned as RED (not
in-vocabulary bugs, reported for the manager's routing/ruling instead):

- **5 rows, unquoted term + otherwise-recognized idiom** (`AZ_T11_C3_A12_
  S600`, `ID_T6_C22_S6-2202`, `MA_PIII_TII_C231_S85Z`, `SD_T32_C9_
  S32-9-17.2`'s embedded-trigger variant, `MI_C123_...S123.1281`) -- the
  rule requires a quoted term BY DESIGN (matches the documented precision
  gate and the Planner's own negative-control precedent). This is a real,
  measured recall cost from a deliberate precision tradeoff, not a bug --
  a recall-vs-precision question, reported rather than settled here
  (P-R2). Note: `NY_ARPP_A8_S280-D` (already counted above under bug #6,
  the "shall have the following meanings" connector gap) ALSO
  independently exhibits this same unquoted-labeled-paragraph convention
  as a second, compounding issue on the same row -- not double-counted in
  the 22-row total, flagged here so the two causes aren't conflated.
- **4 rows, a genuinely different, unrecognized idiom**: "referred to in
  this `<unit>` as the 'X'" (content-then-term naming/aliasing, the
  REVERSE of "X means Y") -- `STATE_CO_T24_A34_P1_S24-34-108` ("program"),
  `STATE_LA_Crevised-statutes_T33_S9038.71` (3 terms: Baker/district/
  property), `STATE_ME_T20-A_P5_C417-A_S11424` ("capital reserve
  requirement"), `STATE_RI_T16_C16-59_S16-59-1` ("the council"). A U1
  convention-inventory gap, not a vocabulary typo -- would need new
  parsing logic (reversed clause order), not a regex tweak.
- **1 row, `USC_T15_C22_S1127`** (federal Lanham Act, "Construction and
  definitions; intent of chapter") -- a single "In the construction of
  this chapter, unless the contrary is plainly apparent..." preamble
  governs a long list of terms with NO per-entry trigger repetition;
  "in the construction of this X" does not match the bare-`in`
  vocabulary's "in this X" pattern. Also a live routing question: this
  heading arguably should resolve to F3 (`is_definitions_heading`) and
  currently does not -- flagged for the manager to route (core's
  `sections.py`/`us_profile.py`, not this family's file).

**U4 VERDICT: FAIL.** Proving check: 12 confirmed misses (8 distinct root
causes, empirically reproduced via direct interactive execution of the
real, unmodified `extract_us_scoped_inline_definitions` against real,
byte-verified corpus text) inside this family's own already-claimed
vocabulary, found via a P-R7-compliant, signal-agnostic random sample
across all 53 jurisdictions -- not synthetic edge cases. 6 are pinned as
committed RED tests. Per the QA role boundary, not fixed here.

### U6 -- full-corpus (all 53 jurisdictions, 2,038,135 rows scanned) per-slice before/after

Script `qa_u6_full_corpus.py` (scratchpad): independent "genuine" heuristic
(D1/D3-style -- trigger regex hit + adjacent quote-then-idiom or a nearby
colon; NOT the production rule's own buggy splitting logic, to avoid
hiding the misses just found) extended from the Planner's 12-lead-state
scan to the full corpus. 271.7s wall time.

**Genuine trigger volume by scope-unit word, full 53-jurisdiction corpus**
(258,958 total genuine hits -- proportions broadly match the Planner's
12-state D1/D3 figures, refined at full scale):

| Unit | Hits | % | Maps to |
|---|---|---|---|
| section | 123,393 | 47.6% | local |
| chapter | 50,165 | 19.4% | chapter |
| subsection | 21,945 | 8.5% | local (S-R11 interim) |
| article | 13,748 | 5.3% | law-wide |
| part | 10,665 | 4.1% | law-wide |
| act | 10,628 | 4.1% | law-wide |
| subchapter | 9,350 | 3.6% | law-wide |
| paragraph | 8,393 | 3.2% | law-wide |
| subdivision | 6,936 | 2.7% | law-wide |
| title | 1,751 | 0.7% | law-wide |
| division | 1,383 | 0.5% | law-wide |
| subpart | 601 | 0.2% | law-wide |

**AFTER: rule's own candidate output, tallied by persisted `.scope`**
(280,312 total candidates -- NOT directly comparable 1:1 to the genuine-hit
table above: one trigger can yield multiple candidates via a list, and
some genuine hits are multi-counted per entry; reported as volume/scale,
not a row-level recall percentage, which the 530-row sample already
measured more precisely at 63.4%):

| Scope (after) | Candidates | % of captured |
|---|---|---|
| local | 129,528 | 46.2% |
| law-wide | 75,647 | 27.0% |
| chapter | 75,137 | 26.8% |

**Before, all slices: 0** (uncontested -- `pipeline.py`'s `else:` branch
called Hebrew-only extractors for every US article pre-sprint, re-verified
architecture fact, not re-derived).

**Per-slice honesty, as the brief required (never one headline number)**:

- **section -> local**: ~53.8% of genuine family volume (Planner's
  12-state figure; 47.6% at full 53-state scale) -- fully live, correctly
  scoped, U2 both-directions PROVEN on the real pipeline
  (`test_us_scoped_inline_pipeline_live.py`).
- **chapter -> chapter**: ~23.7% (19.4% full-scale) -- fully live,
  correctly scoped, U2 both-directions PROVEN live.
- **subsection -> local (S-R11 interim)**: ~4.5% (8.5% full-scale, LARGER
  than the Planner's 12-state figure -- subsection usage is more common
  outside the original lead states) -- captured, but OVER-LINKED to the
  whole owning article. `test_us_scoped_inline_pipeline_subsection_live.py`
  keeps TRUE subsection behavior pinned `xfail(strict=True)`; I
  independently re-verified this self-alarming mechanism actually works
  (see Mutation section below) rather than trusting the design description.
- **part/subchapter -> law-wide (S-R9)**: ~13.9% (7.7% full-scale) +
  ~4.0% residue (article/act/paragraph/subdivision/title/division/subpart,
  ~20.4% full-scale) -- captured, OVER-LINKED to the entire ingested
  Document.

**Over-link cost, quantified (the number the manager re-escalates under
P-R2)**: `ingest_us_statute_rows` (`ingest_us_statutes.py:164`) ingests
whatever `rows` the caller batches into ONE `Document`; `scope="law-wide"`
is unrestricted (`matcher._in_scope`), so the over-link exposure is bounded
by the Document's article count -- in practice however the caller batches
rows in production, but AT LEAST the corpus's own `title_number` grouping
(a reasonable lower-bound proxy for a sane batching granularity). Measured
directly from the real corpus (`qa_overlink_cost.py`): mean **977.6** rows
per (jurisdiction, title), median 324, up to **122,535** rows in the
largest single title (TX). Against the REJECTED chapter-fallback's
narrower unit (mean 40.1 rows/chapter, median 13): **law-wide over-links
~24.4x more articles on average than a chapter-scoped fallback would
have** -- and chapter-fallback was itself already proven unsound (Maine:
one Part spans 106 chapters, S-R9). **Caveat, disclosed not hidden**:
36.8% of ALL corpus rows (750,594) have a NULL `title_number` (entirely
null for FL/IA/IL/KS/KY/MA/MI/MN/MO/NC/NH/NM/PR/TX/WI/WV; 70% null for CA;
93% for NE), so for those jurisdictions the true production batching
granularity -- and therefore the true over-link exposure, which could be
the ENTIRE STATE CODE (up to 161,429 rows for CA, 122,535 for TX) if
production batches whole-state rather than per-title -- is NOT
determinable from the corpus data alone. Could not verify beyond this.

For `subsection -> local` (S-R11), the over-link is bounded by definition
to the single owning article (S-R11's own accepted tradeoff, self-
alarmed) -- categorically smaller than the law-wide slice, not separately
quantified in article-count terms this cycle (would need a per-article
subsection-count distribution; flagged as unverified, not fabricated).

**U6 VERDICT: PASS-WITH-CAVEAT.** Proving check: full 2,038,135-row
53-jurisdiction sweep (real command + output above), per-slice breakdown
with both the Planner's 12-state figures and this cycle's independent
full-scale figures shown side by side, over-link multiplier measured
directly from real corpus title/chapter grouping. Caveat: the true
over-link ceiling for the 36.8%-of-corpus null-`title_number` states is
unverified and could be substantially larger than the measured 24.4x.

### U1 -- convention-variant hunt: 2 new gaps found beyond U4's bug list

Beyond the 8 in-vocabulary bug classes above (which ARE U1 findings too --
a rule that silently drops an entire unmarked colon-list is a convention
the inventory should have caught), two further real, distinct SHAPES were
found in the 530-row sample that the vocabulary was never designed to
recognize at all (not vocabulary bugs, feature gaps):

1. "Referred to in this `<unit>` as the 'X'" aliasing/naming (4 rows,
   listed above under U4's routed-out findings).
2. "In the construction of this `<unit>`, unless..." single-preamble-
   governs-a-whole-list shape (USC Lanham Act, listed above).

### U2 -- verified, not assumed

Both directions LIVE-PROVEN for `local` and `chapter` only, exactly as the
brief said to expect: read `test_us_scoped_inline_pipeline_live.py` in
full -- both scenarios construct a real defining row plus a synthetic
in-scope AND out-of-scope sibling, assert the `USES_DEFINITION` edge
target set directly against persisted `Assertion.subject_entity_id`/
`object_entity_id` (not the summary dict). `subsection` is xfailed by
design (S-R10/S-R11); independently re-verified the xfail mechanism itself
works (see Mutation section).

### U3 -- zero edits to shared modules

`git diff --name-only origin/main...HEAD` (full command output, this
cycle): only `backend/app/definition_links/rules/us_scoped_inline.py`
under `backend/app/` -- confirmed clean, matches every prior handoff
verification this sprint.

### U5 -- baseline states hold, full suite green modulo this cycle's own RED

`backend/.venv/bin/pytest backend/tests -q` before adding any QA test:
**742 passed, 2 xfailed** (matches the sprint's stated starting state
exactly). After adding the 6 QA RED tests: **6 failed, 742 passed, 2
xfailed** -- the 6 failures are 100% attributable to this cycle's own new
file; nothing pre-existing regressed.

### Mutation rigor on the load-bearing greens

Scratch copy at `/private/tmp/.../scratchpad/mutation_copy` (full repo
copy, own venv -- verified the venv's editable-install finder maps `app`
to the ORIGINAL worktree's absolute path, NOT the copy; pytest's own
`pythonpath = ["."]` ini option overrides this for test runs, but a bare
`python -c` does not -- this cost real debugging time before I trusted the
mutation results; flagging so a future QA cycle doesn't repeat it).

| Test | Mutation | Result |
|---|---|---|
| `test_local_scope_links_a_mention_within_the_same_article_only` | `_SCOPE_BY_UNIT["section"]` -> `"law-wide"` | **CAUGHT** (real AssertionError, `'law-wide' == 'local'`) |
| `test_chapter_scope_links_a_sibling_article_in_the_same_chapter_but_not_a_different_one` | `_extract`'s `candidate.source_chapter = ctx.chapter` stamping removed | **CAUGHT** (same-chapter sibling stopped linking) |
| `test_core_proof_rule_and_a_second_overlapping_rule_dedupe_to_one_definition` | pipeline.py's dedup lookup forced to always `None` (scratch-copy-only edit, never touched the real repo) | **CAUGHT** (3 Definition rows instead of 1) |
| `test_subsection_scoped_definition_does_not_link_a_mention_in_a_different_subsection` (xfail mechanism) | Simulated the post-core-fix revert: `_SCOPE_BY_UNIT["subsection"]` flipped back to `"subsection"` (mapping only, core's resolver bug NOT fixed in the scratch copy) | **CONFIRMED WORKING**: direction 2 correctly XPASSes, `strict=True` correctly turns that into a suite FAILURE -- the self-alarming revert design is real, not just described |
| `test_bare_in_this_section_mid_sentence_prose_yields_nothing` (negative control) | Removed the bare-`in` strict comma/colon adjacency gate entirely | **NOT CAUGHT** by the negative-control suite (still 6/6 pass) -- but a targeted synthetic probe confirms the gate DOES do real work (`'Nothing in this section "widget" means...'` becomes a false positive once the gate is removed); the *committed* fixture row this test uses just doesn't happen to have a quote immediately after "in this section", so the downstream quote-match requirement redundantly protects it. **Finding: no committed test isolates the adjacency gate itself** -- a regression there could ship silently as long as no fixture row happens to pair a bare "in this `<unit>`" with a coincidental nearby quote. |
| `test_references_to_term_shall_include_is_excluded_by_design` (negative control) | Widened `_MARKER_QUOTE_RE`'s marker-to-quote gap from immediate to <=20 chars | **NOT CAUGHT** by the negative-control OR body-axis suite (42/42 unchanged) -- the PA row is independently protected by the idiom-vocabulary gate ("shall include" is not a recognized idiom), not by the marker-adjacency mechanism this test's own docstring credits. A fully UNBOUNDED gap (500 chars) IS caught, by the ROMAN-NUMERAL test (`test_nested_roman_numeral_subclauses_stay_inside_their_own_entry`) -- so there is real protection somewhere in the suite, just not from the test that documents itself as testing this exact mechanism, and not at moderate gap distances. |

### Fixture byte-checks

`backend/tests/fixtures/us_statutes/us_scoped_inline_rows.json`: **26/26**
rows byte-identical (`section_title` + `text`) against the live parquet
(count grew from the Planner's own last-verified 25 -- the Planner pass-2
addition of `STATE_MO_C44_S44.091` is included and verified). This cycle's
own new fixture, `qa_cycle1_missed_conventions_rows.json`: **6/6**
byte-identical (verified twice -- once implicitly at fetch time by reading
directly from the parquet, once independently re-checked afterward as a
separate script run). 32/32 real rows byte-verified in total this cycle.

### False-positive rate

Ran the real rule against the FULL (untruncated) text of all 530
trigger-blind sample rows: fires (>=1 candidate) on 26/530 rows. Of those,
**initially 4 looked like false positives** (rule fired, judge said
NEGATIVE) -- direct investigation of all 4 found EVERY one is actually a
methodology artifact, not a rule defect: the definition sits PAST the
4000-char cap I imposed on the judges' sample text (`STATE_AZ_T15_C9_A1_
S910`'s "state aid" definition at offset 15,736 of a 15,807-char row;
similarly for `STATE_AZ_T20_C11_A1_S2108`, `STATE_MO_C260_S260.925`,
`STATE_OK_T18_S18-1142`) -- the judges never saw that part of the text, so
their NEGATIVE call was correct given what they were shown, and the rule
was RIGHT to fire. **Corrected false-positive rate: 0/26 = 0%** on this
sample (small N, wide confidence interval, but a genuinely strong result,
and I would rather report a self-caught methodology bug than an inflated
15.4% headline). **Residual, disclosed limitation**: this same 4000-char
cap means a genuine definition sitting past the cap, in a row whose VISIBLE
portion has no definition AND that the rule (bug included) ALSO fails to
capture, would be invisible to BOTH the judges and this false-positive
check -- 47/530 (8.9%) sample rows were truncated; not re-verified against
full text by a fresh judging pass this cycle (would require re-dispatching
judge agents; flagged as unverified, not silently assumed clean).
Separately, the mutation-rigor section above found the strict bare-`in`
adjacency gate DOES hold precision when actually exercised (confirmed by
direct synthetic probe), consistent with this 0% measured rate.

### What I could NOT verify

- The true over-link ceiling for the 36.8%-of-corpus null-`title_number`
  jurisdictions (could be much larger than the measured 24.4x if
  production batches whole-state).
- Whether a genuine definition hides past the 4000-char sample cap in any
  of the 47 truncated, judge-NEGATIVE rows that the rule ALSO fails to
  capture (the one blind spot the false-positive re-check cannot close).
- `subsection -> local`'s over-link cost in article-count terms (would
  need a per-article subsection-count distribution; not measured).
- Whether the "referred to in this `<unit>` as the 'X'" aliasing shape or
  the unquoted-term precision tradeoff should be captured -- reported for
  the manager's ruling (P-R2-style), not decided here.
- GA/MD/NE/MS (F2's assigned states) were not independently re-audited for
  a reverse F1/F2 boundary conflict this cycle (the Planner flagged the
  same gap in pass 1 and it was never closed).

### Per-gate verdicts (summary)

- **U1**: FAIL-WITH-FINDINGS -- 8 confirmed in-vocabulary bugs (6 RED-test-
  pinned) + 2 unrecognized convention shapes, found via a P-R7-compliant
  sweep, not synthetic invention.
- **U2**: PASS for `local`/`chapter` (both directions, live, proven by
  reading the real assertions in `test_us_scoped_inline_pipeline_live.py`
  and confirming the mutation-caught results above); `subsection` remains
  correctly xfailed (verified the xfail mechanism itself is real, not
  just documented).
- **U3**: PASS -- `git diff --name-only origin/main...HEAD` output pasted
  above, only one production file touched.
- **U4**: **FAIL** -- 12 confirmed misses in-family, P-R7-compliant
  denominator independently built and executed (not merely adopted),
  divergence proven non-circular (63.4% recall / 78.8% precision vs. the
  family's own regex), cross-validated at 96.7% agreement.
- **U5**: PASS -- 742 passed/2 xfailed baseline reproduced exactly before
  adding any QA test; the only new failures are this cycle's own 6 RED
  tests.
- **U6**: PASS-WITH-CAVEAT -- full 53-jurisdiction, 2,038,135-row sweep,
  per-slice breakdown, over-link cost quantified at ~24.4x for the
  measurable majority of the corpus, with the null-`title_number`
  36.8% explicitly flagged as unverified rather than assumed.

No `ESCALATION:` filed this cycle -- every finding above is either
classifiable as a confirmed in-family miss (RED-test-provable, reported
per the QA role boundary) or an already-named P-R2 conflict class the
manager already owns (unquoted-term precision tradeoff, the aliasing
idiom, the law-wide/subsection over-link cost) -- nothing here needed a
NEW recall-vs-precision judgment call from QA, or touches a shared module.

Commit: test files + this log entry only, no implementation touched.

---

## 2026-08-04 — Manager: QA cycle 1 verdict BOUNCE; ruling S-R12 (M-D3)

### QA verification (manager-run)

- Role boundary held: QA's diff since `6cb5eef` is two test/fixture files plus
  the log — zero implementation. U3 holds: the only file under `backend/app/`
  in the whole sprint diff is `rules/us_scoped_inline.py`.
- Suite reproduced: **6 failed, 742 passed, 2 xfailed**.
- I did NOT take the "12 confirmed misses" claim on trust. I pulled all 6 QA
  fixture rows from the live parquet and compared `section_title` + `text`:
  **6/6 byte-verbatim real**. I then ran the rule over each: it captures
  **ZERO** candidates from every one. These are genuine misses in conventions
  this sprint already claims to support, not testing artifacts.

**Verdict: U4 FAILS. Sprint bounces to a Developer fix cycle.** `qa_cycles: 1`
(safety valve is 5). Under the director's absolute zero-miss bar a confirmed
in-vocabulary miss is disqualifying — these are not deferrable.

The 8 root causes QA proved: unmarked colon-then-quoted-list (worst — IL 2
terms, VA 7 terms, all lost); period-style list markers (`1.` not `(1)`, FL);
chained parenthetical unit qualifiers (CO); an intervening citation clause
breaking recognition (DE/OH/OR — 3 independent rows); `the term:` with no space
(DC); `shall have the following meaning(s)` (NY/MS); plural `have the same
meaning as` (TN); bare copula `is` (ND).

Credit: QA's mutation testing found two gates (bare-`in` adjacency,
marker→quote adjacency) that survive weaker mutations because redundant
downstream checks mask the mechanism the tests claim to protect. That is
exactly the "green for the wrong reason" class this sprint has been bitten by
twice. Also honest: QA self-corrected an initial 15.4% false-positive
measurement to 0/26 after finding the 4 apparent FPs were its own 4000-char
sampling-cap artifact.

### S-R12 — M-D3 erratum: real risk, currently DORMANT for us; binding for cycle 2

Core's M-D3 erratum: the English-word→marker-kind table
(`subsection`→outermost `lower_alpha`, `paragraph`→`digit`) is
ILLUSTRATIVE-FEDERAL-ONLY. Real conventions diverge three ways — federal/TN/VT/TX
`lower_alpha`-outermost, Oregon and most sampled states `digit`-outermost
(Oregon's `paragraph` designator is `lower_alpha`, NOT digit), Ohio
`upper_alpha`-outermost. A rule declaring kind from the table mis-scopes
SILENTLY.

Assessed against our actual code: **this rule declares no marker kind at all.**
`_subsection_label` OBSERVES the nearest preceding marker whatever its shape
(`_SUBSECTION_LABEL_RE` matches digit, lettered and dotted forms alike) rather
than declaring a kind from a table. So the erratum's failure mode does not bite
us today, for two independent reasons: we never declare a kind, and under S-R11
`subsection` maps to `"local"`, so no kind-based matching happens at all.

It becomes LIVE at the post-core revert, when true subsection scope returns and
our label must agree with core's resolver per state. **Binding checklist item
for QA cycle 2** (recorded now so it cannot slip between cycles): verify, per
state and from that state's OWN real marker shapes, that our derived label
agrees with core's resolved unit for all 12+ states we stamp levels for —
evidence-based, never table-copied.

### Sprint state at manager clean-exit

Phase: Developer fix cycle 2 (not started). Nothing is blocked on a decision.

---

## 2026-08-04 — Manager (phase 2, fresh context): fix cycle 2 launched; ruling S-R13

### Inherited state VERIFIED, not assumed

- `origin/claude/defs-us-scoped-inline` == local `b8cf5e8`; worktree clean.
- Suite re-run by me in the sprint worktree: **6 failed, 742 passed, 2 xfailed**
  — the 6 are exactly QA cycle 1's `test_us_scoped_inline_qa_cycle1_missed_
  conventions.py` tests. RED-provenance for the Developer respawn confirmed
  live, not taken from the handoff note.
- `us_scoped_inline.py` read in full: 298 lines, at the style-gate ceiling.

### S-R13 — RED-provenance is INCOMPLETE for 3 of the 8 root causes; a
Planner pass closes it, running concurrently with the Developer

QA cycle 1 proved 8 root causes but pinned only 6 (one row per class, the
other 6 rows documented in prose). Three whole root causes therefore have NO
committed test: period-style markers (`1.`, FL), `the term:` with no space
(DC), and `shall have the following meaning(s)` (NY/MS). Under the director's
absolute zero-miss bar, "the Developer says it works and QA will re-derive it
next cycle" is weaker than a pin — and this sprint has already been bitten
twice by greens that held for the wrong reason. A fix with no committed pin
can regress silently after this sprint closes.

The predecessor's "zero test edits" instruction fences the DEVELOPER, not the
panel. So: **Planner pass 6 (Sonnet/high) authors the 3 missing RED pins**
from real, byte-verified corpus rows, plus Task 2 below.

**Concurrency design (deliberate, and why it still satisfies red-before-green):**
Planner and Developer run at the SAME time in SEPARATE worktrees with
disjoint write sets (Planner `backend/tests/**` only; Developer
`backend/app/definition_links/rules/**` only — no file can conflict). The
Planner authors against the UNMODIFIED rule and cannot see the fix, so the
tests are independent of the implementation in the way red-before-green
actually cares about. Provenance is preserved by ME, not by ordering: I run
the Planner's new tests against the pre-fix tree (`b8cf5e8`) and confirm RED
before merging either branch. If a "RED" pin passes pre-fix, it pins nothing
and goes back.

**Task 2 (same Planner pass): tighten the two gates QA proved are green for
the wrong reason.** QA's mutation testing showed (a) the bare-`in` strict
comma/colon adjacency gate can be REMOVED entirely with negative controls
still 6/6 green, and (b) `_MARKER_QUOTE_RE`'s marker→quote adjacency can be
widened to ≤20 chars with 42/42 green — in both cases a redundant downstream
check (the quote-match requirement; the idiom-vocabulary gate) masks the
mechanism the test's own docstring credits. My predecessor's carry-forward
routed this to QA cycle 2; I am routing it to the Planner instead, because
"tighten a pin" is test authorship, and because a committed isolating test is
worth more than a QA note that expires with the cycle. QA cycle 2 still
verifies the result independently.

### Developer fence (unchanged from S-R2/U3, restated for the cycle)

Write set: `rules/us_scoped_inline.py` + AT MOST ONE new **non-registering**
helper module in `rules/` (the sanctioned 300-line overflow — no
`register_*` call means zero new dispatch surface; `rules/__init__.py`
auto-imports every sibling, so the helper must be import-safe and must not
import `us_scoped_inline`). Zero test edits. `_SCOPE_BY_UNIT["subsection"]`
stays `"local"` (S-R11) — flipping it XPASSes a strict xfail and fails the
suite; that revert is core's.

**D-Q1 made blocking on root cause 8.** The bare-copula `is` widening is the
most FP-prone change in the list (`"X" is` is everywhere in ordinary
statutory prose). The Developer must measure its false-positive surface on
the real corpus — candidate delta with the idiom on vs. off across ≥8 states,
plus a hand-classified random sample of ≥30 NEW candidates — and narrow with
data if the FP class is material. A recall-vs-precision conflict it cannot
settle from evidence escalates with numbers rather than being decided
silently (P-R2/D-Q1).

### Named conflict classes carried, NOT resolved this cycle

S-R9 law-wide fallback; S-R11 subsection interim; the PA construction-clause
pin. Queued for post-U4 re-escalation to the program manager. Two items
already routed upstream (core's resolver defects; GA/MD/NE/MS reverse-boundary
re-verification with the preamble panel) are not this panel's.

### Manager check: the 6 UNPINNED miss rows are real too (not taken on prose)

My predecessor byte-verified QA's 6 PINNED fixture rows. The other 6 confirmed
misses live only in QA's prose, and the Developer is being asked to fix them,
so I verified them myself before the cycle ran — pulled each from the live
parquet and ran the real, unmodified `extract_us_scoped_inline_definitions`
over the full untruncated text (`si_cycle2_mgr_verify_unpinned.py`,
scratchpad):

| act_id | text len | candidates today |
|---|---|---|
| `STATE_FL_TXVIII_C253_S253.04` | 5547 | **0** |
| `STATE_DC_T47_C20_S47-2002.01` | 4598 | **0** |
| `STATE_NY_ARPP_A8_S280-D` | 3181 | **0** |
| `STATE_MS_T27_C29_S51-5` | 1418 | **0** |
| `STATE_OH_T17_C1707_S1707.47` | 3343 | **0** |
| `STATE_OR_T62_C835_S835.200` | 1406 | **0** |

All 6 rows exist, all 6 yield nothing. Combined with the predecessor's 6/6
byte-verification of the pinned rows, **all 12 confirmed misses are real** —
the Developer is not chasing a phantom on any of the 8 root causes.

---

## 2026-08-04 — Manager: Developer fix cycle 2 verified + ACCEPTED; D-Q1 endorsed

Branch `claude/defs-us-scoped-inline-dev` @ `cfedc98`, clean tree. Everything
below I ran myself; nothing is taken from the Developer's report.

### Fence and overflow sanction — verified mechanically

- `git diff --name-only origin/main...HEAD -- backend/app/` → exactly TWO
  files: `rules/us_scoped_inline.py` (263 lines) and the new
  `rules/us_scoped_inline_shapes.py` (217). Both under the 300-line gate.
  Zero test edits; zero shared-module edits. **U3 holds.**
- The overflow sanction was conditional on the helper adding no dispatch
  surface, so I checked it rather than reading the docstring's promise:
  no executable `register_*` call, no `registry` import at all, no
  back-import of `us_scoped_inline`. The single registration in the whole
  sprint is still `us_scoped_inline.py`'s one line. **Sanction satisfied.**

### Suite

`backend/.venv/bin/pytest backend/tests -q` → **748 passed, 2 xfailed, 0
failed.** The 6 QA cycle-1 REDs are green; the 2 strict xfails are still
xfailed, so the S-R11 revert tripwire is intact and `_SCOPE_BY_UNIT
["subsection"]` was not touched.

### The two load-bearing precision gates — read, not assumed

QA cycle 1 proved these two survive weak mutations, so a green suite is not
evidence about them. I diffed them by hand:

- `_BARE_CONNECTOR_RE` is **byte-identical** to its pre-cycle definition
  (`r"\s*(?:(?P<colon>:)|(?P<comma>,))?\s*"`), merely relocated to the helper.
- `_MARKER_QUOTE_RE`'s adjacency half (`\s*["“]`) is **unchanged**. Only
  `_MARKER_RE`'s marker SYNTAX widened, to admit period-style `1.`
  (`(?<!\d)[0-9]{1,3}\.`). Wider marker vocabulary, identical gap tolerance —
  which is exactly the distinction the gate protects.

One genuine widening I want on the record because it is easy to miss:
`_UNIT_TAIL` went from one optional parenthetical (`?`) to a chain (`*`), and
that applies to the bare-`in` trigger as well as the strong ones. Bounded
(≤12 chars per group) and still behind the strict adjacency gate, so I accept
it — but it IS new trigger surface, and QA should treat it as such.

### The 12 confirmed misses — re-run by me on the shipped code

The 6 pinned rows are covered by the now-green tests. For the 6 unpinned rows
I re-ran my own pre-cycle script against the shipped module:

| act_id | before | after |
|---|---|---|
| `STATE_FL_TXVIII_C253_S253.04` | 0 | 2 — Seagrass, Seagrass scarring |
| `STATE_DC_T47_C20_S47-2002.01` | 0 | 4 — incl. Street vendor, MST |
| `STATE_MS_T27_C29_S51-5` | 0 | 3 — incl. Motor vehicle, Public highway |
| `STATE_OH_T17_C1707_S1707.47` | 0 | 3 — Claimant, Final order, Victim |
| `STATE_OR_T62_C835_S835.200` | 0 | 1 — seaplane |
| `STATE_NY_ARPP_A8_S280-D` | 0 | **0** — routed out, see below |

**11 of 12 fixed.** NY is empty BY SCOPE, not by defect (below).

### D-Q1 — ENDORSED, after my own deep-verification

The Developer measured the bare-copula `is` widening over 589,406 rows / 10
states: 846 extra candidates, 0/40 hand-classified false positives, and
shipped it unnarrowed. It also disclosed honestly that 27 of those 40 were
judged from a preview rather than the full row — so the endorsement rests on
a sample whose weaker half was self-declared.

I therefore picked **5 rows myself**, weighted toward the shapes that look
most FP-prone in preview, and judged each against the FULL untruncated
corpus text:

- `STATE_CA_Cpen_P1_T7_C6_S139` — `As used in this section, "a credible
  threat" is a threat made with the intent and the apparent ability…` —
  **genuine.**
- `STATE_OH_T3_C307_S307.692` — `As used in this section, "promotion of
  tourism" is the encouragement through advertising…` — **genuine.**
- `STATE_MI_…_S168.4` — `"Village" is defined in section 9.` — **genuine**
  pointer definition (D-MT-E1 requires capturing these).
- `STATE_GA_T14_C3_S14-3-140` — `"Notice" is described in Code Section
  14-3-141.` — **genuine** pointer.
- `STATE_TX_Ced_C48_S48.2551` — the riskiest shape in the whole sample, a
  single-letter term `"E"`. Full text shows a statutory formula-variable
  block: `(1) "DPV" is… (2) "E" is… (3) "MCR" is… (4) "PYDPV" is… (5) "PYMCR"
  is…`. These are real defined terms for the section's tax formula —
  **genuine, correctly captured.**

**5/5 genuine on my independent picks; 0/45 measured FPs in total.** No
material false-positive class exists to escalate under D-Q1, so the
unnarrowed ship is within policy and the recall argument for rejecting an
article-restriction stands. **Endorsed.**

### Two findings of my own, carried to QA cycle 2

**Finding A — duplicated candidates from duplicated corpus text.** While
reading the GA row I noticed every entry is emitted TWICE, because the corpus
`text` itself repeats each sentence verbatim (`(32) "Notice" is described in
Code Section 14-3-141 . (32) "Notice" is described in Code Section 14-3-141 .`).
A corpus data-quality artifact, not a rule bug — the rule faithfully extracts
what is there. But it raises two questions this cycle must not wave through:
(i) does the live pipeline's dedup collapse same-rule duplicate candidates
into ONE `Definition` row? The existing dedup test covers cross-RULE overlap,
which is a different path. (ii) does this duplication **inflate the +8,899
corpus candidate delta** that QA is being asked to sample for precision — i.e.
is part of the headline improvement double-counted rather than new capture?
A measured improvement that silently counts the same definition twice is
exactly the kind of number this program has committed to not shipping.

**Finding B — single-character defined terms.** `"E"` is a genuine definition,
but a one-letter term with `\b`-bounded literal matching is a downstream
precision hazard wherever it is in scope. Not this cycle's defect and not
this family's file; recorded as an observation for the program.

### Routed OUT (not ours to fix)

`STATE_NY_ARPP_A8_S280-D` still captures zero. Cause is the **unquoted
lettered-paragraph** convention: the rule requires a quoted term by design,
a deliberate precision gate this panel did not invent and must not quietly
relax. That shape belongs to the **markers panel's unquoted-term family**.
Reported to the program manager as a routing item so it is owned rather than
orphaned.

**Verdict: Developer handoff ACCEPTED.**

### Finding A refined by me (half resolved, half now binding on QA)

I chased my own duplicate-candidate finding rather than handing QA a vague
worry. `pipeline.py:234-269`, read directly:

- **(i) RESOLVED — no over-persistence.** Definition rows are deduped on
  `(owning_article.id, tuple(sorted(candidate.terms)))`, and the map is
  updated inside the loop, so two identical candidates produced from
  duplicated corpus text collapse to ONE `Definition` row on the live path.
  The GA duplication does NOT create duplicate definitions. Good news, and
  it means the existing cross-rule dedup test's gap is narrower than I feared.
- **(ii) STILL OPEN, and now a binding QA instruction.** The `+8,899`
  before/after figure is a **candidate** count, and candidate counts are
  exactly what corpus text duplication inflates — the dedup above happens
  downstream of it. So part of that headline is plausibly the same definition
  counted twice, not new capture. **QA cycle 2 must report the delta as
  distinct `(row, sorted-terms)` pairs, not raw candidates**, and say how much
  the two figures differ. Under this program's honesty standard we do not
  ship an improvement number that silently double-counts.

---

## 2026-08-04 — Manager: core dispatch merged; ruling S-R14 (the revert needs
MORE than the mapping flip — proven, not argued)

Program manager's sequencing note: dispatch merged to main @ `8524067`; run the
revert cycle; step (1) is "rebase and CONFIRM the tripwires fire — if they
don't, that's a finding, investigate before anything else."

**They did not fire. I investigated before doing anything else, and the
investigation changed the shape of the revert.**

### Why the tripwires were silent (benign, and the design is fine)

Merged `origin/main` into a scratch worktree I control, refreshed the venv,
ran the two tripwires: **`2 xfailed`** — no alarm.

Applying P-R10 (before claiming X is broken, explain why everything
downstream of X is not already visibly broken): both tests assert
`definition_row.scope == "subsection"` BEFORE they assert any linking
behavior. While `_SCOPE_BY_UNIT["subsection"]` is still `"local"`, that first
assertion fails, so the test fails for the interim's own reason and the xfail
holds. The tripwire is gated on **our** revert, not on core's merge — which is
exactly what both `reason=` strings already say ("once core lands its fix
**AND** the Developer reverts `_SCOPE_BY_UNIT['subsection']`"). So: **not a
defect, and not a broken alarm** — the expectation that a rebase alone would
fire it was simply mis-stated. Recorded rather than quietly corrected, because
had I taken it at face value I would have gone hunting for a phantom defect in
core's freshly-merged fix.

### The real finding: flipping the mapping ALONE ships a SILENT UNDER-LINK

I flipped `_SCOPE_BY_UNIT["subsection"] → "subsection"` in the scratch tree
(probe only, never the real branch) and re-ran:

- **Direction 2 XPASSED → suite FAILURE.** The alarm fires, and core's
  level-contract fix is confirmed **live and reachable from our path**: an
  out-of-subsection mention is correctly NOT linked.
- **Direction 1 STILL xfailed.** A mention truly INSIDE the defining
  subsection got no edge at all.

Direction 1 is the under-link direction. Under the director's absolute
zero-miss bar that is disqualifying — and it is strictly worse than the
interim, which over-links (a precision cost) rather than under-linking (a
miss). **So the ordered step "restore the mapping" is, on its own, not a
revert but a regression.**

### Root cause, measured on the real Oregon row (not inferred)

`STATE_OR_T22_C238_S238.300`, real offsets, core's own resolver:

| offset | what | core's `resolve_unit_path` |
|---|---|---|
| 3405 | the trigger | `[digit 1, lower_alpha b, upper_alpha B, lower_roman c]` |
| 4466 | in-subsection mention | `[digit 1, lower_alpha b, upper_alpha B, lower_roman c]` |
| 2046 / 2344 | out-of-subsection mentions | `[digit 1]` |

Our `_subsection_label` returns `'c'`. Core's outermost step is `'1'`, so
outermost-comparison can never match — the innermost-vs-outermost mismatch
S-R10 identified, still live.

**And the obvious fix is a trap.** Deriving a kind from our label's SHAPE
(`'c'` → `lower_alpha`) DISAGREES with core, which classifies that very marker
as **`lower_roman`** — because kind follows LADDER DEPTH, not glyph shape
(`c` is a roman-numeral character, and at depth 3 the rung is `lower_roman`).
A shape-derived declaration would silently mis-scope. This is M-D3's erratum
biting exactly where S-R12 predicted, and it is why "never table-copied" is
not enough: a per-state table would ALSO have been wrong here, because the
divergence is per-DEPTH within a single row.

### S-R14 — the revert derives from CORE's resolver, not from a second
derivation of our own. Validated end-to-end.

The whole S-R10/S-R11 family of defects exists because two independent
derivations of a subsection label were compared against each other. The fix is
to stop having two. Our rule already has the body and the trigger offset, and
`resolve_unit_path` needs nothing else — so the rule asks CORE for the unit
step open at the trigger and stamps **both** `scope_value` and
`scope_unit_kind` from it.

I probed this in the scratch tree (one derivation, innermost open step):

**Both tripwires XPASS → suite FAILURE — the alarm firing correctly, with
direction 1 now genuinely linking and direction 2 genuinely not.**

This also answers S-R12 more strongly than a per-state table ever could: we
consult no English-word→kind table at all, and core's 3-ladder resolver
already selects its ladder from each state's OWN first marker. Per-state
correctness is inherited from core's measured ladders instead of re-asserted
by us.

**Honest limit of what I proved.** My probe validates the MECHANISM on one
real row. It takes the INNERMOST open step (`path[-1]`), and whether
"innermost" is the right level for every state and every trigger phrasing is
NOT proven — a trigger deep inside `(1)(a)(i)` saying "this subsection" may
well mean `(1)`. That level-selection policy is exactly the per-state
measurement S-R12 demands, and it stays the Planner's job. I am handing the
panel a validated mechanism and an open, named policy question — not a
finished answer.

### Seam gap, recorded for the program manager (not ours to fix)

`us_profile.extract_local_scope_definitions` still builds
`RuleContext(..., unit_path=())` — hardcoded empty on `origin/main`. A
`ScopeTriggerRule` therefore gets NO unit-path context from the seam, which is
why our rule must import `resolve_unit_path` directly. That works and stays
inside our fence, but it is a rule→`us_profile` dependency the seam was
presumably meant to remove. Routed up as a core seam observation.

---

## 2026-08-04 — Manager: Planner pass 6 verified + ACCEPTED; rebased onto main;
ruling S-R15 (level-selection policy) + a NEW conflict class routed up

### Planner pass 6 — verified by mutation, not by reading the claims

Branch `claude/defs-us-scoped-inline-plan6` @ `e78a5eb`.

- **Fence holds**: `git diff --name-only b8cf5e8..plan6` under `backend/app/`
  is EMPTY. Tests and fixtures only. Both touched test files under the
  300-line gate (209 / 252).
- **Task 1 RED-provenance, proven on BOTH trees by me** (S-R13's whole point):
  the 4 new pins FAIL against the pre-fix rule (`4 failed`, real
  `AssertionError`s) and PASS against the shipped fix (`4 passed`). Authored
  in a worktree that never saw the Developer's branch, so the independence is
  structural, not promised.
- **Task 2 is the part I refused to take on trust**, because "this test
  protects mechanism X" is exactly the claim QA cycle 1 disproved twice. I
  re-ran both mutations myself in a scratch tree:
  - Removing the bare-`in` strict comma/colon adjacency gate →
    **1 failed, 7 passed**, and the one failure is
    `test_bare_in_strict_comma_or_colon_adjacency_gate_is_load_bearing`.
    (Cycle 1: the same mutation left the negative controls 6/6 green.)
  - Widening `_MARKER_QUOTE_RE`'s gap to ≤20 chars →
    **1 failed, 7 passed**, the failure being
    `test_marker_quote_adjacency_gate_is_load_bearing_alabama`.
  Precise isolation in both directions: the right test fires, the others do
  not. **The masking gap QA cycle 1 found is genuinely closed.**
- Good judgment recorded: the Planner declined to pin `STATE_NY_ARPP_A8_S280-D`
  after verifying the row contains ZERO quote characters — a NY pin would have
  stayed red forever, since the row's convention is the deliberately-excluded
  unquoted shape, not the connector gap. It chose OR over OH for the bonus pin
  because OR's citation nests a parenthetical (a structurally different stress)
  while OH duplicates DE's shape. Both calls are right.

**Verdict: Planner pass 6 ACCEPTED.** Merged; sprint suite 754 passed / 2
xfailed.

### Rebased onto `origin/main` (core dispatch @ `8524067`)

Probed the rebase on a throwaway branch first (clean, 24/24), then rebased for
real: clean, `origin/main` is now an ancestor. Venv refreshed.
**Suite: 824 passed, 2 xfailed, 0 failed** — our family rules and core's newly
merged dispatch work coexist with nothing broken on either side. The two
xfails remain correctly silent (our mapping is still the S-R11 interim; see
S-R14 for why that is the expected state, not a missed alarm).

### S-R15 — the level-selection policy is a NAMED OPEN QUESTION, not a
Developer's judgment call

S-R14 proved the MECHANISM (derive `scope_value` + `scope_unit_kind` from
core's own resolver at the trigger offset). It does NOT settle WHICH step of
the returned path to use. My probe took the innermost open step and both
directions passed on the Oregon row — but a trigger sitting deep inside
`(1)(a)(i)` that says "this subsection" may well mean `(1)`, and the M-D3
erratum exists precisely because that mapping differs per state.

This is a recall-vs-precision conflict class, so per D-Q1 it does not get
decided quietly by whoever writes the code:

- **Interim, binding**: innermost open step at the trigger offset — the only
  option with live-path evidence behind it today.
- **The Developer must factor level-selection into ONE swappable decision
  point**, so changing the policy is a one-line change and never a redesign.
- **The Planner measures it per state from real rows** and escalates with data
  if the measurement contradicts the interim. Note the direction of risk:
  choosing too NARROW a level under-links (a zero-miss violation), choosing
  too BROAD over-links (a precision cost). Under the director's absolute
  zero-miss bar those are not symmetric, and the measurement should say so.

### NEW conflict class, routed UP (not resolved here) — the `(N) LABEL. "X"`
convention

While building the gate-(b) isolation test the Planner hit a real row,
`STATE_AL_T13A_C11_S13A-11-1` — `(1) OBSTRUCT. To "obstruct" means…` — and a
full-corpus scan found **tens of thousands** of hits for that shape: a marker,
then a short unquoted label, THEN the quoted term. Our entry splitter requires
the marker to be immediately followed by a quote, so every one of these is
currently lost.

This is important and I am explicitly NOT letting it be settled inside this
panel, for two reasons:

1. **It is in direct tension with the gate we just pinned as load-bearing.**
   Widening `_MARKER_QUOTE_RE` to admit an intervening label is precisely the
   mutation `test_marker_quote_adjacency_gate_is_load_bearing_alabama` now
   fails on — by design. Recall and precision point opposite ways here, at
   scale. That is a textbook D-Q1 escalation with data, not a regex tweak.
2. **Ownership is genuinely unclear** between this family (it is our
   entry-splitting mechanism) and the markers panel (entry-marker shape is
   their remit, and their unquoted-term family is adjacent).

Routed to the program manager with the act_id, the shape, and the measured
scale. Not in this sprint's 8 root causes; not silently absorbed.

---

## 2026-08-04 — Manager: program rulings actioned (force-push, S-R14 endorsed,
AL class sent to measurement)

### 1. Branch rewrite published, backup made durable FIRST

Program manager authorized the force-push with conditions; executed in the
required order and verified rather than assumed:

1. Confirmed the backup tag actually covers the old remote line —
   `git merge-base --is-ancestor b8cf5e8 si-prerebase-backup` → true.
2. Pushed `si-prerebase-backup` to origin **before** any rewrite.
3. Force-pushed with **`--force-with-lease=…:b8cf5e8`** rather than a bare
   `--force`, so the push would have been REJECTED had origin moved off the
   value I reasoned about. Result: `+ b8cf5e8...0ad2243 (forced update)`.
4. Verified with `ls-remote`: remote head `0ad22434998a…` == local HEAD;
   remote tag at `493732e…`.

### 2. S-R14 ENDORSED at program level — recorded as a PRINCIPLE

The program manager endorsed single-source derivation and named it the same
reuse-don't-parallel principle behind core's own C1 fix, noting that our
Oregon depth-vs-glyph proof shows the M-D3 erratum's per-STATE framing was
itself insufficient: kind is per-DEPTH, so no per-state table could have been
right. S-R15's treatment of level selection as a named open question with one
swappable decision point was endorsed as-is. No change to the briefs already
running.

The core-seam observation (`RuleContext.unit_path` hardcoded `()` on main, so
rules must import `resolve_unit_path` directly) is recorded in the S-R14
section above and has been added to the program-close list as a seam-threading
cleanup candidate.

### 3. The AL `(N) LABEL. "X"` class: MEASURE FIRST — routed to a scout, not
to the director

Program ruling: "tens of thousands" is an ESTIMATE, and the director gets real
numbers. Correct, and my own routing entry above should have said measured
rather than repeating the scan's estimate — recorded as a correction to myself.

Spawned a measurement analyst (Sonnet/high, own worktree + venv,
`claude/defs-us-scoped-inline-scout1`) with a read-only fence — no production
code, no tests — required to deliver:

- **(a) a P-R7-compliant count** that does NOT build its population from our
  own marker/trigger vocabulary, reporting raw hits vs. DISTINCT rows
  separately (a single row can hold dozens of entries; conflating the two is
  how a scary headline gets manufactured), and — the number that actually
  matters — the **genuine un-rescued residue** after running the real
  `is_definitions_heading`/`derive_heading_from_body` logic, since a
  heading-recognized row is boundary S-R3's, not our miss.
- **(b) a hand-judged ≥40-row sample** answering whether the LABEL or the
  quoted term is the real definiendum (they coincide in the Alabama row —
  do they always?), what a wrong capture would COST (a bogus term that then
  matches across its whole scope is far worse than one that matches nothing),
  and how many hits are genuine definitions at all rather than penalty
  schedules or cross-reference lists wearing the same shape.
- **(c) the inherited trade stated plainly**, quantified both directions.
- **(d) a JOINT OWNERSHIP proposal** written for a manager with none of our
  context, with reproducible act_ids — routed to the markers panel THROUGH the
  program manager, who brokers. The scout was explicitly told not to contact
  that panel and not to decide ownership itself.

It was also told that a deflating result is a GOOD outcome: if the residue is
small, or these rows are already captured elsewhere, that finding is worth more
than a dramatic number.

**Standing tension both panels would inherit, restated so it cannot be lost:**
the fix for this class is to let a label sit between the marker and the quote —
which is *precisely* the mutation `test_marker_quote_adjacency_gate_is_load_
bearing_alabama` now fails on by design, and precisely the gate QA cycle-1
mutation testing proved was doing real work. Nobody should widen that regex
without the measurement in hand.

---

## 2026-08-04 — Manager: Developer cycle 3 (the subsection revert) verified +
ACCEPTED; S-R16 (period-style degrade routed to core with evidence)

Branch `claude/defs-us-scoped-inline-dev3` @ `ef93457`, clean tree. Merged.

### Fence — and a false alarm I chased down rather than reported

`git diff --name-only claude/defs-us-scoped-inline..HEAD` listed the sprint
LOG alongside the two rule files, which would have been a fence breach. It is
not: that is a two-dot artifact. The three-dot diff against the real
merge-base (`493ef78`) shows **docs/ untouched, zero lines** — the worktree was
simply branched before my last two log commits. **Fence held exactly: two
rule files, nothing else.** Recorded because "the Developer edited the log"
would have been a false accusation, and the two-dot/three-dot distinction is
the kind of thing that produces one.

Line counts 292 / 270 — both under the 300 gate, but with little headroom left.

### The risk hunk, read in full (not skimmed)

- `_event_scope` short-circuits `unit == "subsection"` to
  `_resolve_subsection_scope`; every other unit returns
  `(_SCOPE_BY_UNIT[unit], None, None)`.
- `_resolve_subsection_scope` returns `("local", None, None)` on an empty path
  and `("subsection", step.value, step.kind)` otherwise. **The degrade path
  cannot stamp a kind without a value** — the specific failure the program
  manager asked me to confirm. Value and kind are drawn from the SAME step or
  are both `None`; there is no code path that pairs one with the other's
  absence.
- `_subsection_scope_level(path) -> path[-1]` is the single S-R15 decision
  point, docstring citing the ruling. Genuinely one line to change.
- The old `_subsection_label` and its regex are gone — the second derivation
  that caused this whole defect family no longer exists in the tree.

### Closed the Developer's own open gap: the failure set IS complete

The Developer flagged that it could not verify the 4-failure set. I enumerated
it: exactly **2 tripwire XPASSes + 4 stale S-R11 pins**, and the 4 are
precisely the ones named in Planner pass 7's Task B
(`body_axis` ×3 + `pipeline_live` ×1). Nothing else regressed; nothing is
missing from the Planner's worklist.

### Maine: the fixture row does NOT degrade — a trap avoided

`test_bare_quote_means_subsection_scope_maine` now fails with
`assert 'subsection' == 'local'`, i.e. the rule stamps **subsection** on that
row. So the 81% Maine degrade rate is a CORPUS-WIDE rate, not a property of
this fixture, and restoring that assertion to `"subsection"` is correct.
**But** the Planner must not stop at the scope string: a subsection scope that
resolves is only worth pinning if it actually LINKS. Pinning
`scope == "subsection"` while the definition links nothing would be a silent
under-link wearing a green test — the exact shape S-R10 exists to catch.

### Trap recorded: `_SCOPE_BY_UNIT["subsection"]`'s VALUE is now dead code

The dict's KEYS still feed `_UNIT_ALT` (so the entry must stay), but
`_event_scope` short-circuits before ever reading the `"subsection"` VALUE.
Editing it now does nothing — a silent no-op waiting for a future reader who
assumes otherwise. Not a defect today; flagged for a comment or an explicit
sentinel. QA cycle 2 should confirm no test asserts on it.

### S-R16 — the period-style degrade is a CORE resolver coverage gap, measured

The Developer measured the `"local"` degrade rate (18 states): **Maine 81.0%
(1,068/1,318)**, AZ 69.6%, VA 33.3%, overall 12.4%. Cause: core's
`_US_UNIT_MARKER_RE` recognizes PARENTHESIZED markers only, so Maine's `2-A.`
and Florida's `1.` numbering is invisible to `resolve_unit_path`, which returns
an empty path and triggers our zero-miss degrade.

**Nothing is LOST by this** — the degrade links at article granularity (the
recorded S-R9-style precision cost), it does not drop definitions. But under
the director's absolute zero-miss bar it is a **named, measured limitation**
until core extends the ladder vocabulary, and it is core's to fix, not ours.

Binding on QA cycle 2: quantify it cleanly — extend toward the 53-state census
if cheap, otherwise sample the high-degrade states' actual marker shapes to
confirm the period-style diagnosis rather than assuming it explains all three.
It then goes up as a routed core item at the same evidence standard as our
S-R3/S-R10 escalations.

---

## 2026-08-04 — Manager: AL `(N) LABEL. "X"` class — premise DEFLATED
(independently verified); S-R17 records it as a bounded, gated item

The scout's census deflated the escalation I routed up. Program ruling: this
proceeds as a **bounded additive item**, not an emergency and not a widening.
I verified the load-bearing claims against the real corpus myself before
accepting the deflation — a deflating number deserves the same scrutiny as an
alarming one, since accepting it is what closes the escalation.

### The motivating row was never our miss — confirmed

`STATE_AL_T13A_C11_S13A-11-1`, the row this entire escalation was built on:
`section_title` is **`'Section 13A-11-1 Definitions'`**, and the REAL
`is_definitions_heading` returns **True**. It is F3-rescued today. My own
earlier routing entry treated it as an uncaptured miss; it never was. Recorded
as a correction to myself — the second time this cycle that a scary framing of
mine did not survive measurement.

### Ran all 8 of the scout's named reproduction rows through the real
heading logic + the real rule

| act_id | F3-rescued? | our rule |
|---|---|---|
| `STATE_AL_T13A_C11_S13A-11-1` (motivating) | **YES** | 0 |
| `STATE_AL_T16_C25_S16-25-1` (divergence) | **YES** | 0 |
| `STATE_NC_C135_S135-48-1` (divergence) | **YES** | 0 |
| `STATE_AL_T1_C1_S1-1-1` (clean miss) | no | 0 |
| `STATE_CA_Chsc_D5_P3_C6_A4_S5470` (clean miss) | no | 0 |
| `USC_T23_C1_S139` ("In general" decoy) | no | 0 |
| `STATE_AR_T1_C4_S1-4-134` (spurious) | no | 0 |
| `STATE_FL_TXXIX_C381_S381.922` (spurious) | no | 0 |

**3 of 8 are F3-rescued and were never ours.** Of the 5 genuinely un-rescued,
only **2 are clean captures we would want** — the other 3 are one "In general"
decoy and two spurious nicknames. That independently corroborates the scout's
~30%-wrong-within-the-residue finding using its OWN exemplars, by a different
method than its hand sample.

The Florida row is the argument in one line:
`381.922 William G. "Bill" Bankhead, Jr., and David Coley Cancer Research
Program.` A naive capture takes **"Bill"** as a defined term — which then
matches "bill" across its entire scope. That is not a small precision cost;
it is the poisoning failure mode, from a legislative honorific.

### S-R17 — recorded as a NAMED, GATED item; NOT worked this cycle

Residue is **714 rows / 2,276 occurrences ≈ 0.03% of corpus** — hundreds, not
tens of thousands. 9 jurisdictions have zero hits; federal alone is 62% of
occurrences.

Ownership split (program ruling, director may veto):

- **Ours — the code**: a NEW, SEPARATE marker+label+quote adjacency pattern.
  `_MARKER_QUOTE_RE` and `test_marker_quote_adjacency_gate_is_load_bearing_
  alabama` stay **byte-untouched** — this is additive, so the gate we just
  proved load-bearing is never reopened, and the PA construction-clause FP
  cannot return through it. Plus the term-selection rule: **prefer the QUOTED
  string over the label** whenever both exist (the quote was the more reliable
  string in every genuine-divergent case measured).
- **Markers panel — the classification**: is a `(N) LABEL.` token an
  entry boundary or a generic structural sub-header, including the
  boilerplate blocklist ("in general", "en general", "generally",
  "definitions", …). The nested-boilerplate trap is real and systematic:
  "in general"/"en general" is the captured label in 144/3,963 occurrences
  across 94 rows.

**Gated on the markers panel's classification piece. Planner pass 7 and QA
cycle 2 are explicitly NOT blocked on it.**

### Binding caveat for QA cycle 2

The scout's numbers came from **single-pass hand judgment**, not the 7-reader
cross-validated rigor of QA cycle 1's sample, and its census is heuristic and
not proven complete. **Treat every percentage above as DIRECTIONAL.** QA
re-derives independently anything it actually relies on — and in particular
must not quote the 92.7%/30%/18%/12% splits as measured facts without
re-deriving them. The residue COUNT (714 rows) is the figure most worth
re-checking, since the ownership split is sized against it.

---

## 2026-08-04 — Manager: S-R15 verification + VERDICT (lean: OPTION B,
outermost) — with one consequence nobody has priced in yet

Time-boxed verification of Planner pass 7's escalation. I did NOT re-derive
the 19.4% aggregate (QA cycle 2's job by ruling); I verified the load-bearing
pieces and the semantics.

### (a) The SC counterexample — reproduced EXACTLY, end-to-end

I did not run the Planner's script. I built an INDEPENDENT harness driving the
REAL merged `matcher._subsection_contains_offset` with a real `USProfile`, and
got:

`STATE_SC_T12_C6_A9_S12-6-1170` — trigger path `[(upper_alpha 'A'), (digit '2')]`
- shipped INNERMOST stamps `value='2' kind='digit'` → **links 0 of 4** genuine reuses
- OUTERMOST would stamp `value='A' kind='upper_alpha'` → **links 4 of 4**

Total silent under-link on a clean, correctly-resolved, non-period-style row.
Confirmed.

**P-R10 probe sanity (the check that makes the above trustworthy):** the same
harness, run against Oregon — S-R14's OWN validation row, whose behavior is
already established — reproduces the known result (innermost links the 4466
mention, which is why direction 1 passes today). A harness that could not
reproduce a known number would make the SC figure worthless. It reproduces.
Oregon additionally shows innermost **1/4** vs outermost **3/4**, so the
under-link reproduces on S-R14's own state, exactly as escalated.

### (b) The semantic argument — TESTED against the drafters' own words, and
it holds overwhelmingly but is NOT airtight

I tested it independently of our extractor AND of core's resolver, by counting
how the statutes describe their own hierarchy in cross-references (53 files):

| supports "subsection = top level under section" | count |
|---|---|
| `subsection (X) of this section` | 156,496 |
| `paragraph (X) of this subsection` | 39,626 |
| `subdivision (X) of this subsection` | 6,721 |
| `subparagraph (X) of this subsection` | 100 |

**202,943 supporting occurrences across 48 of 53 jurisdictions.**

**Answer to the question that would break the argument: YES, such states
exist — but at trace volume.** `subsection (X) of this subdivision` / `of this
paragraph` occurs **12 times total** — SD 6, NY 3, VT 2, federal 1 — i.e.
**0.006%**. And they are not all noise: South Dakota genuinely nests
subsection UNDER subdivision (`STATE_SD_T58_C5A_S58-5A-4`: "the information
required by subsection (a) of this subdivision"), and Vermont likewise
(`STATE_VT_T24_C60_S1992`: "Notwithstanding subsection (A) of this
subdivision (2)").

So the honest formulation is **not** "option B is definitionally correct
everywhere" but: *in 48 of 53 jurisdictions the drafters' own words put
"subsection" at the top level, and the handful of inverted conventions are
identifiable by name.* The over-linking risk is not definitionally empty — it
is empirically ~0.006% and concentrated in three named states. I would rather
hand the director that than a cleaner claim that does not survive contact with
South Dakota.

Oregon proves the point from inside a single row: the same statute says
"paragraph (b) of this subsection" AND "subsection (1) of this section" AND
"for the purposes of this subparagraph" — section ⊃ subsection ⊃ paragraph ⊃
subparagraph, stated by the drafter. Our innermost interim pins that
definition to the PARAGRAPH, which the statute's own vocabulary contradicts.

### THE CONSEQUENCE NOBODY HAS PRICED IN: option B breaks the Oregon
direction-2 test, and that test is semantically WRONG

Reading the raw Oregon markers, the definition at `(c)` (offset 3401) sits
inside top-level subsection **`(2)`** (offset 1262). The mentions the
direction-2 test calls "a DIFFERENT subsection" — offsets 2046/2344, in
`(2)(a)(A)`/`(2)(a)(B)` — are in the **SAME subsection (2)**, merely a
different PARAGRAPH.

So `test_subsection_scoped_definition_does_not_link_a_mention_in_a_different_
subsection` encodes the innermost/paragraph reading as ground truth. Under
option B those mentions SHOULD link, and that test will fail — correctly.
**Adopting B means RE-AUTHORING that test, not preserving it.** It is a test
the Planner just restored, so this must not be discovered by QA later.

**And a second trap on the same row:** core's resolver returns top-level
`digit '1'` for that trigger, but ground truth is `(2)` — it latched onto the
CITATION "under subsection (1) of this section" (offset 1752) instead of the
structural `(2)`. That is exactly the pin-cite corruption class routed to core.
On Oregon, outermost therefore reaches the semantically right answer **for the
wrong reason** (definition and mentions share the same bogus `'1'`). QA must
not certify any row whose path is corrupted this way.

### (c) VERDICT — lean OPTION B (outermost), conditional

1. **Adopt B as a MEASURED default, not a claimed universal** — 48/53 by the
   drafters' own vocabulary, with SD/NY/VT named as known inverted
   conventions carrying ~0.006% of cross-reference usage.
2. **Re-author the Oregon direction-2 test** as part of adopting B. Its
   current assertion is semantically wrong under B.
3. **Keep S-R15's swappable decision point** (already one line). Triggers
   naming deeper units ("this paragraph") route through the declared-kind
   matcher, which core already supports — option C's territory, not a reason
   to reject B.
4. **Not re-derived by me, deliberately**: the 19.4% / 1,254-of-6,472
   aggregate. QA cycle 2 owns it. My verification covers the counterexample,
   the harness sanity, and the semantics.

Direction-of-risk note for the director: under innermost, the failure is a
SILENT UNDER-LINK (a miss — disqualifying under the absolute zero-miss bar).
Under outermost, the failure is an over-link (a precision cost) bounded to one
top-level subsection and, per the vocabulary census, empirically rare. Those
are not symmetric.

---

## 2026-08-05 — Manager: D-S15 adopted; pass 7 merged; a MIS-AUTHORED test
caught before it reached the Developer

Director ruling **D-S15** (program doc, main @ `5190e84`): OUTERMOST default —
my lean, adopted on the verified data. Conditions 1-4 recorded and carried.

### Planner pass 7 verified + merged

Fence held (zero `backend/app/` edits, checked); all six touched/created files
under the 300-line gate. Merged. Sprint suite: **831 passed, 1 failed.**

Note for the record: pass 7's "12 expected REDs" were red against ITS OWN
pre-revert worktree. On the sprint branch — which already carries Developer
cycle 3's revert — eleven of them are GREEN. That is red-before-green working
across concurrent worktrees exactly as S-R13 designed, not a discrepancy.

### The one remaining RED is MIS-AUTHORED — and D-S15 would NOT have fixed it

`test_subsection_scope_does_not_link_a_different_subsection_south_carolina`
(row `STATE_SC_T14_C7_A7_S14-7-845`) asserts that a mention of "school
employee" sits in subsection **(A)**, "a DIFFERENT subsection than the one
defining it", and must not link.

I checked the row's own text rather than the docstring:

- `(A)` begins at offset **0**; `(B)` begins at offset **307**; `(C)` at 1197.
- The definition's trigger is at **709** — inside **(B)**
  (`For purposes of this subsection, a "school employee" is a person employed
  as a teacher…`).
- The mention the test calls "in subsection (A)" is at offset **334** — which
  is 27 characters AFTER `(B)` starts. It is the phrase "school employee" in
  (B)'s own opening clause: `(B) If a public or private school employee, a
  person…`.

**The mention is in the SAME subsection as the definition.** It SHOULD link.
The test asserts the opposite, so its factual premise is simply wrong.

Two things make this worth stopping for:

1. **D-S15 will not fix it.** This row is single-level — `(A)/(B)/(C)` with no
   nesting — so innermost and outermost are THE SAME STEP. I verified both
   policies against the real matcher on this row and they are identical. A
   Developer handed this as a target would have chased a failure the ruling
   cannot address.
2. **"Fixing" it would mean deliberately introducing an under-link** — teaching
   the rule not to link a mention sitting inside its own definition's
   subsection. That is precisely the silent-miss failure mode this whole
   escalation exists to eliminate, and it would have arrived wearing a green
   test.

Routed to Planner pass 8 for re-authoring, NOT to the Developer.

### Pass 8 / cycle 4 launched concurrently (S-R13 pattern, disjoint write sets)

- **Planner pass 8** (tests only): re-author the Oregon direction-2 test to
  D-S15 semantics (per condition 2), re-author the mis-authored SC test above,
  add RED pins for outermost semantics on rows that are genuinely MULTI-level
  (a single-level row cannot distinguish the policies and must not be used to
  pin one), and — per condition 2's second half — select fixture rows that are
  NOT corrupted by the pin-cite defect, since that defect is core follow-on and
  must not be silently baked into our pins.
- **Developer cycle 4** (rules only): the stamping-side change —
  `_subsection_scope_level` returns the subsection-level step (outermost)
  rather than `path[-1]`. Condition 3 preserved: the matcher keeps exact
  declared-kind matching, so deeper trigger vocabularies still work; the
  decision point stays swappable.
- **Condition 1** (SD/VT/NY inverted conventions) enters the ledger as a named
  follow-up: per-state override vs. accepted trace-volume over-link, to be
  enumerated either way, never buried.

---

## 2026-08-05 — Manager: D-S15 IMPLEMENTED and verified; QA cycle-2 hold LIFTED

Both concurrent branches verified and merged. Sprint suite: **839 passed, 0
failed, 0 xfailed.**

### RED-provenance, verified in the correct order

The provenance question here is subtle, because each agent's worktree lacked
the other's change. I resolved it by checking the RED side against the
PRE-CHANGE tree explicitly rather than against either agent's own report:

- Reset a worktree I control to `3f41093` (sprint head BEFORE dev4's change),
  applied ONLY plan8's test files, and ran the new pins: **4 failed** — the two
  SC pins and the two Washington pins. Genuine RED, authored in a worktree that
  never contained the implementation.
- Merged dev4 + plan8: **839 passed, 0 failed.** RED → GREEN across
  independently-authored branches.

### Independent verification of the semantics (my own harness, real matcher)

Re-ran the harness I built for the S-R15 verdict against the merged tree:

| row | before (innermost) | after (D-S15 outermost) |
|---|---|---|
| `STATE_SC_T12_C6_A9_S12-6-1170` | stamps `('2', digit)`, links **0/4** | stamps `('A', upper_alpha)`, links **4/4** |
| `STATE_OR_T22_C238_S238.300` | stamps `('c', lower_roman)`, links **1/4** | stamps `('1', digit)`, links **3/4** |

The shipped behavior now matches, byte for byte, what I independently computed
as "outermost" before the change existed. That is the check I actually trust.

### Both fences held

dev4: only the two rule files. plan8: only `backend/tests/**`. Verified by
diff, not by report.

### Judgment calls by the agents that I endorse

- **plan8 REMOVED the Oregon direction-2 test rather than flipping it**, with
  byte-verified evidence that core's resolver latches onto the citation
  `"under subsection (1) of this section"`. Flipping it would have produced a
  green test passing FOR THE WRONG REASON — a core defect baked into our
  suite as an assertion. Removing it and pointing the docstring at the
  replacement file is the right call and exactly D-S15 condition 2's intent.
- **plan8 built a TESTABLE ledger for SD/NY/VT** (3 byte-verified rows,
  including a newly-found NY one) rather than a docstring. Condition 1 said
  "enumerated either way, never buried"; a test cannot rot silently the way a
  comment can.
- **dev4 verified the degrade is policy-independent** — 12.97% identical under
  both policies across 9,485 real triggers / 15 states, structurally
  guaranteed because the empty-path check precedes the level choice. It
  measured this instead of asserting it, which is why I believe it.

### NEW coverage gap found by dev4, routed to QA cycle 2

**No pytest test exercises the empty-path `"local"` degrade branch on a real
state row.** The two tests that cite Maine/Florida as motivation both resolve
NON-empty paths, so the branch S-R14/S-R16 rely on is unpinned. That is a
green-for-the-wrong-reason shape — the third this sprint has found — and it
goes on the cycle-2 checklist.

### QA cycle 2 hold LIFTED

Checklist re-pointed at **D-S15**, not the interim. The 19.4% under-link
figure is now the BEFORE-number of an implemented fix, and QA re-derives both
sides.

---

## 2026-08-05 — Manager: QA cycle 2 BOUNCE verified + accepted; cycle 3 planned
to converge (qa_cycles 2 of 5)

### QA cycle 2 verified (not taken on its report)

Branch `claude/defs-us-scoped-inline-qa2` @ `162f987`, merged at sprint
`ce37b86`. Fence held: `git diff --name-only 8a2b239..HEAD | grep backend/app/`
is EMPTY — tests and fixtures only. Suite reproduces **6 failed, 848 passed**.

I spot-checked 3 of the 6 pinned rows against the live parquet myself
(`STATE_GA_T10_C12_S10-12-16`, `USC_T18_C83_S1716E`,
`STATE_ME_T20-A_P7_C606-B_S15671-A`): **3/3 byte-identical** on both
`section_title` and `text`, and **3/3 yield ZERO captures** from the real rule.
The bounce is genuine — these are real in-vocabulary misses, not artifacts.

**Verdict: U4 FAILS again. Bounce accepted.** Under the absolute zero-miss bar
a confirmed in-vocabulary miss is disqualifying.

### What QA got right, recorded because it is the standard

- Caught its OWN methodology error mid-cycle (F3-filtering) and disclosed the
  resulting population discrepancy rather than quietly shipping the newer
  number.
- Refined its own 962-vs-1,924 no-reuse figure rather than leaving the looser
  one standing.
- Ran the gate mutations on a scratch copy OUTSIDE the repo, and applied the
  corruption guard when selecting item 12's replacement row.
- **S-R12 is now CLOSED with a real result**: 34,972 events, **zero
  disagreements** between our stamped pair and core's resolver. That is the
  binding item carried across three cycles, and single-source derivation
  (S-R14) is why it came back clean — two derivations could never have.
- **D-S15 confirmed live at full corpus**: 4,034 recovered, 143 regressed,
  1,924 genuine under-links remaining. The director's ruling is measurably
  correct AND the residue is honestly reported.
- **U6's honest number is 314,139 distinct, not 359,437 raw** — the dedup
  correction I flagged in Finding A is now measured, and the gap (45,298) is
  exactly the inflation I predicted from repeated corpus text.

### Cycle 3 launched — three concurrent workstreams, disjoint write sets

1. **Developer cycle 5** (rules only): the 6 new findings. Briefed that the
   bare-`in` adjacency gate and `_MARKER_QUOTE_RE` are load-bearing with
   isolating tests, and that a green suite is NOT evidence he left them intact.
   Will likely need a SECOND non-registering helper module — both rule files
   are within 8 lines of the 300 gate.
2. **Planner pass 9** (tests only): re-author the PA construction-clause pin.
   **This is the subtle one.** That row is protected TODAY only because
   `shall include` is absent from the idiom vocabulary. D-INCLUDES puts it IN,
   so the row's protection transfers entirely to the new targeted guard — and a
   test that passes for a reason that has ceased to exist is the exact
   green-for-the-wrong-reason class this sprint has hit THREE times (QA cycle
   1's two masked gates; my mis-authored-SC-test catch). The pin must assert
   the GUARD, proven by mutation. The Planner is also told to go hunting for
   OTHER negative controls whose protection evaporates under D-INCLUDES —
   finding one would be a valuable result.
3. **Reconciliation analyst** (read-only): the two disputed populations.

### Both reconciliations ordered as DISPUTED, not as corrections

Per program ruling, neither number is load-bearing until reconciled, and the
analyst is explicitly told that finding BOTH prior numbers wrong is a good
outcome:

- **D-S15 before-figure**: Planner pass 7's 1,254/6,472 (19.4%) vs QA's
  15,282/44.3%. The F3-filtering explanation is a **hypothesis to prove, not
  assume**; the gap must be attributed to specific quantified causes, not
  hand-waved, and the winning population defined reproducibly.
- **S-R17 residue**: 714 vs 167, where QA's own spot-check found its number
  ~50% contaminated by USC quoted-bill-text artifacts. A fresh
  contamination-aware census is ordered, with the contamination class
  characterized before it is excluded. The program will size an ownership
  split against this figure, so its uncertainty must be stated.

Both carry P-R10 probe sanity: the harness must reproduce the known SC result
(0-of-4 innermost, 4-of-4 outermost) before any aggregate built on it is
trusted.

---

## 2026-08-05 — Manager: Planner pass 9 verified + ACCEPTED; its side-finding
routed to the live Developer as a false-positive risk

Branch `claude/defs-us-scoped-inline-plan9` @ `41b6e06`. Harness note: role
agents now deliver reports to me directly; this is the first report on the new
channel.

### Verified

- **Fence holds**: only `test_us_scoped_inline_rules_negative_controls.py`;
  zero `backend/app/` edits.
- **299 lines** — under the gate, but at the ceiling.
- **Suite 7 failed / 847 passed** vs 6/848 before: exactly **+1 RED**, total
  test count unchanged at 854. The always-green negative control was replaced
  by a currently-RED guard-isolation test. Reproduced by me.

### Why this re-author mattered

The PA row was protected ONLY because `shall include` was absent from the
idiom vocabulary. D-INCLUDES puts it in, so that protection evaporates and
transfers entirely to the new targeted guard. A test that keeps passing for a
reason that has ceased to exist is the green-for-the-wrong-reason class this
sprint has now hit four times. The pin now asserts the GUARD.

The Planner also found the row was **independently** blocked by
marker-adjacency, not idiom-absence alone — so its simulation had to widen BOTH
`_IDIOM_RE` and `_MARKER_QUOTE_RE` to make the row reachable before the guard
could be shown to be load-bearing. Mutation evidence on a scratch copy OUTSIDE
the repo: guard-absent → row captured (FAILS); guard-present → suppressed,
while the real unmodified positive row `STATE_NY_ARSS_A2_T9_S89-H` stays
captured. That last check is what proves the guard is NARROW rather than a
blanket suppression of the includes family — exactly what D-INCLUDES rejected.
It also deliberately reproduced the documented venv trap to confirm which tree
its mutated code was imported from, rather than assuming.

### The side-finding — verified by me, and routed to the LIVE Developer

`STATE_PA_T15_C17_S1748` and `STATE_PA_T15_C57_S5748`:

> "(a) General rule.--Except as provided in subsection (b), for the purposes of
> this subchapter, **references to "the corporation" include** all constituent
> corporations absorbed in a consolidation, merger or division, …"

I ran the real rule on both: **0 captures today**. They are invisible only
because `_STRONG_CONNECTOR_RE` refuses a `references to ` filler between the
unit word and the quote. **This needs no D-INCLUDES** — bare `include` is
already a recognized idiom.

That makes it a live risk in cycle 5's finding 5, which widens exactly that
connector for the "unless the context otherwise indicates" shape. A generic
widening would capture "the corporation" as a defined term — an extremely
common phrase — reproducing the poisoning failure mode we rejected in the
"Bill" legislative-honorific case, and breaking cycle 2's measured 0-FP result.

Messaged the Developer mid-flight with the two act_ids, a requirement to prove
both still yield ZERO in its report, the note that this is a THIRD distinct
code path (STRONG connector / `_single_entry`, no marker) so one guard may need
to sit in two places, and instructions to escalate with numbers rather than
trade recall for precision on its own authority (D-Q1).

### Carried to QA cycle 3

- **The pin is a SIMULATION.** It monkeypatches `_IDIOM_RE`/`_MARKER_QUOTE_RE`
  to stand in for D-INCLUDES, and the Planner's guard regex is its OWN design,
  not the Developer's. Once the real implementation lands, QA must re-verify
  the test still isolates the REAL guard — a simulation that drifts from the
  shipped mechanism is the same trap one level up.
- **Honest gap named by the Planner**: only the row's FIRST clause is
  guard-isolated; the second ("serving at the request of the corporation")
  never becomes its own entry under the minimal widening, so its silence rests
  on the plain sanity assertion. If the Developer's entry-splitting learns to
  split it, it needs its own probe.
- The Planner checked every other negative control for idiom-absence
  dependence and found none — a clean negative result, recorded so cycle 3
  need not redo it.

---

## 2026-08-05 — Manager: Developer cycle 5 verified + ACCEPTED; two escalations
RULED; one NEW defect class escalated upward

Branch `claude/defs-us-scoped-inline-dev5` @ `e93b52c`, merged with pass 9 at
sprint `57a8068`. Suite: **2 failed, 852 passed** — all 6 QA cycle-2 REDs
GREEN; the 2 failures are Escalation 1, not defects.

### Verified by me, not accepted on report

- **Fence**: three rule files only. The new `us_scoped_inline_entries.py` (229
  lines) has no `register_*` call and no registry import — sanctioned-overflow
  conditions met. Line counts 296 / 238 / 229, all under gate.
- **Both load-bearing precision gates**: I diffed them against `ce37b86`
  myself. `_leading_events` **byte-identical**; `_MARKER_RE`/`_MARKER_QUOTE_RE`
  **byte-identical**. The Developer's claim holds under independent check —
  which matters because a green suite is not evidence here, as QA proved twice.
- **Pass 9's guard pin went GREEN against the Developer's REAL guard.** That
  empirically closes the Planner's own honest gap #3 (its pin was built on a
  simulated guard of its own design). The simulation did not drift from the
  shipped mechanism.
- The Developer answered my time-sensitive PA warning directly:
  `STATE_PA_T15_C17_S1748` / `S5748` both **OLD=[] NEW=[]**, because finding
  5's tolerance is anchored to the literal "unless the context" phrase rather
  than generic filler. The false-positive risk I routed did not materialize.

### ESCALATION 1 — RULED: option (a), the Planner repairs it

Two coupling tests use `shall include` as their synthetic example of an
"unrecognized idiom". D-INCLUDES made it recognized, so the example is stale
and both fail. The general coupling claim they pin is still true; only the
vocabulary example died. The Developer correctly did NOT touch them (hard
fence) and correctly refused to guess.

Ruling: **(a)** — Planner pass 10 repairs them. Role separation holds, and this
is the same D-INCLUDES collision class as the PA pin, just a second casualty.
I additionally required the repaired tests to be **rot-resistant**: they must
fail loudly if their new placeholder idiom ever becomes recognized, and the
Planner must PROVE the placeholder is unrecognized against the shipped
`_IDIOM_RE` rather than assuming. The vocabulary grew twice this sprint;
intuition about what is "obviously unrecognized" is exactly what rotted here.

### ESCALATION 2 — RULED: SHIP finding 4, PIN the regression, ESCALATE the
root cause upward

Georgia "Code section": **3,605 distinct terms gained across 1,527 rows vs 116
lost across 12 rows** (31:1). Reverting is not an option — finding 4 is a
mandatory QA cycle-2 RED.

But 116 lost terms are a real, measured, NEW miss under the absolute zero-miss
bar, and "net positive" does not make a miss disappear. So: ship, and Planner
pass 10 pins the clearest affected row as a **self-alarming** regression
tripwire (the S-R11 `xfail(strict=True)` pattern is the precedent) so it cannot
dissolve into a merged branch.

**The part that goes upward**: the Developer reports the root cause is
PRE-EXISTING — a mid-document carve-out clause (`For purposes of this …, the
term shall not mean/include X`) creates a spurious trigger event that TRUNCATES
an earlier, correctly-spanning trigger's region — and reproduces on unmodified
code with plain `"section"` wording. If true, this is not a Georgia footnote
but a **program-wide zero-miss class** that predates this sprint and affects
every state, and it needs a decision above this panel. I have told pass 10 to
VERIFY that claim rather than accept it, and to probe multi-state scale, since
it is the load-bearing premise of the escalation.

### NEW false-positive class — reported, not hidden, routed to QA cycle 3

The Developer's own 36-row hand sample found **1 likely false positive**
(≈2.8%, versus cycle 2's measured 0%): `STATE_NE_C48_S48-101`, terms
`('arising out of employment', 'in the course of employment')`, where the
captured "definition" is **judicial case-annotation commentary**, not the
legislature's own defining clause. Mechanism: finding 3's new `and`
chain-separator joins the two quotes, then the PRE-EXISTING bare-comma-fallback
idiom (the D11/Missouri convention) accepts the following commentary as a
definition.

This is a genuinely new FP surface created by an interaction — chain-widening ×
pre-existing comma-fallback — not by either mechanism alone. Credit where due:
the Developer reported it against its own interest rather than letting a 36/36
number stand. QA cycle 3 must MEASURE this class rather than accept 1/36 as
its size; it is a D-Q1 recall-vs-precision item and does not get settled inside
the panel.

---

## 2026-08-05 — Manager: reconciliations integrated; delivery contract made
VERIFIABLE after an agent correctly refused an unverifiable instruction

### Process fix — the refusal was right, so I changed the mechanism

The reconciliation analyst REFUSED my chat instruction to route its report to a
raw agent id, treating it as a possible lure. It was wrong that the id was
malformed; it was **right to refuse an unverifiable delivery address supplied
only in chat**. A second panel hit the same refusal independently.

That is the instinct this program wants, so the durable fix is mine, not
theirs: the delivery contract is now a **committed artifact** —
`docs/sprint/sprints/2026-08-04-defs-us-scoped-inline.md`, section "Report
delivery contract", naming the manager id in reviewable sprint history
alongside the gates agents were already briefed against. Every future brief
points there, and agents are told: if the committed id and the briefed id
DISAGREE, do not send — report the discrepancy. Asking an agent to trust
harder was the wrong answer; giving it something checkable is the right one.

Also fixed pre-existing contract-lint failures found while doing this
(non-ISO timestamps, `total_items: 0` under `status: in_progress`,
`qa_cycles` stale at 1). **`contract_lint.sh` now PASSES at 320 lines** — these
would have blocked sprint close.

### Reconciliation 1 — the D-S15 before-figure

QA cycle 2's **15,282 / 44.3%** reproduces as the correct BEFORE figure. Pass
7's **6,472 / 19.4%** does NOT hold as an innermost measurement — high
confidence it was outermost-scored over roughly half its population, though the
script was not preserved, so the MECHANISM is a hypothesis while the DIRECTION
is solid. Recorded that way deliberately rather than as a clean story.

**Clean decision-number going forward: D-S15 rescue set = 2,937 of 12,634
(23.2%).** That is what should be quoted; the 19.4% is retired and the 44.3%
is a population figure, not the rescue rate.

### Reconciliation 2 — S-R17 residue, and a scope caveat that gates the split

Residue = **2,306 rows / 4,042 (row,term) pairs**, **superseding BOTH 714 and
167** — both were too low, in the same direction, for the same reason
(narrower detection vocabularies). 35/35 hand-sampled genuine; the USC
quoted-bill contamination class was characterized and excluded by a scoped
per-line detector; calibrated against all 8 of the exemplars I had verified by
hand, including the "Bill" poisoning rows.

**But the number is broader than the question it would answer.** The 2,306
spans IL's embedded-caption shape and marker-chains, while the markers-panel
ownership split was scoped to the AL numbered-list shape. **An ownership split
priced against the wrong population is worse than one priced against an
acknowledged-uncertain number.** Ordered a narrow-slice re-tabulation: the AL
shape alone, with the other shapes counted SEPARATELY rather than merged back
into one headline, and each shape stating whether the hand-sample evidence
actually covers it (the 35/35 was drawn from the combined population and may
not speak to every slice equally).

Three successive attempts at this residue have now been overturned. Nothing
sizes the split until the narrow slice lands.

---

## 2026-08-05 — Manager: S-R17 narrow slice lands; the split should be priced
at 1,675 rows, and 27% of the residue may not belong in this class at all

### The three shapes, separately counted (sum 2,306, overlap 6 rows)

| shape | rows | (row,term) pairs | hand-sample coverage |
|---|---|---|---|
| **NARROW — the AL `(N) LABEL. "X" means` shape the split was scoped to** | **1,675** | **3,394** | good (24/35 sampled) |
| IL embedded-caption | 618 | 621 | good (9/35) |
| marker-chain (`(1) (A) "Term" means`) | 19 | 31 | **THIN (2/35)** |

**Price the markers-panel ownership split at 1,675 rows / 3,394 pairs.** Both
superseded figures stay superseded: the narrow slice alone is still 2.3-4.8x
larger than either 714 or 167, so no prior number survives even after the
re-cut removes the broader shapes.

### The finding I care most about: 27% of the residue may be a PARSING
ARTIFACT, not a drafting convention

The IL embedded-caption bucket (618 rows, 26.8% of the residue) is described as
a **citation-number-tail artifact** — the "marker" is `340.` extracted out of a
section number like `3.340.`, in single-definition sections with **no real
list**. If that holds, these rows are not instances of the `(N) LABEL.`
convention at all; our detector is seeing a fragment of a citation as a list
marker. Capturing them through a numbered-list rule would be building on a
misparse, and they likely need a different mechanism entirely.

Also: this shape is **not IL-exclusive** — IL is 477 of 618 (77%), with
AZ/CO/FL/ID/KS/MO/NJ/NY making up the rest. Any routing decision framed as
"an Illinois quirk" would be wrong.

**Recommendation upward**: size the split on the narrow 1,675 only; route the
IL-caption bucket for a *shape validity* check before anyone prices it; treat
the 19-row marker-chain bucket as too thin and too fuzzy at its boundary to
price at all this cycle (its own analyst flagged lower precision confidence and
one boundary case that could sit in either bucket).

### A methodology correction that explains the whole 714 / 167 / 2,306 mess

Checking only the heading-rescue path left **33% false positives** — 1,145 of
6,097 clean-hit rows were ALREADY captured today by the real extractor via an
unrelated trigger *elsewhere in the same body*. The analyst caught this
mid-build and corrected by checking BOTH real capture paths.

That single omission is enough to explain why three successive attempts at this
number disagreed, and it generalizes: **"is this row already captured?" is not
answered by the heading gate alone.** Any future miss census in this program
must check every live capture path, not just the obvious one. Recorded as a
standing methodology note.

### Reconciliation 1 closed with a sharper cause than the standing hypothesis

The F3-filtering explanation — the program's standing hypothesis — accounts for
only ~11% of candidate volume (17,337 naive → 15,427 gated). Real, but NOT the
dominant cause. Pass 7's 19.4% sits almost exactly on the measured OUTERMOST
rates (18.6-19.7%) with counts within 1-2.5% of half the distinct-outer
figures: high confidence it was outermost-scored and mislabeled, medium
confidence on the half-corpus mechanism (script not preserved). Good discipline
by the analyst: it declined to promote a plausible mechanism to a certain one.

### Honest limit of my own delivery fix, raised by the analyst and accepted

It verified the committed delivery contract, then noted that a git-branch
artifact is **corroboration, not an out-of-band root of trust** — a branch is
writable by whoever can write the branch. That is correct and I am recording it
rather than letting my fix look stronger than it is: committing the id defeats
a chat-only lure, not an attacker who already controls the branch. Treating it
as corroboration while keeping the plain-text return as the authoritative
channel is exactly the right posture.

---

## 2026-08-05 — Manager: S-R17 split handed to the markers panel directly

Program confirmed my recommendation. Coordinated peer-to-peer with the markers
phase-3 manager (`a5c69b8e918e550cf`) rather than through the program manager.

Handed over: **1,675 rows / 3,394 (row,term) pairs** as the sole pricing basis;
the IL embedded-caption bucket (618) excluded pending a shape-validity check,
with the citation-tail-misparse reasoning spelled out and the "not an Illinois
quirk" correction stated explicitly (477/618 IL, eight other states); the 19-row
marker-chain bucket left unpriced on its analyst's own thin-coverage flag.

Written for a manager with none of my context, so it carries the things that
are easy to lose in a handoff and expensive to rediscover:

- **The inherited tension, with the escalation path named.** `_MARKER_QUOTE_RE`
  and `test_marker_quote_adjacency_gate_is_load_bearing_alabama` stay
  byte-untouched; the work is additive for exactly that reason. If their
  classification piece ever implies widening that gate, they escalate — it is a
  D-Q1 director call, not a regex tweak.
- **The "in general" poisoning trap** in their half (144/3,963 occurrences,
  94 rows), stated as a poisoning mode rather than a precision cost.
- **Eight reproducible act_ids I verified personally**, labelled by what each
  one demonstrates — including the three that are ALREADY F3-rescued and
  therefore nobody's miss (among them `STATE_AL_T13A_C11_S13A-11-1`, the row
  that motivated the entire item), and the `William G. "Bill" Bankhead, Jr.`
  row where a naive capture takes "Bill" as a defined term.
- **The dual-path methodology note as program law**, since it will bite any
  census they run: checking only heading-rescue left 33% false positives here
  (1,145 of 6,097 rows already captured via an unrelated trigger elsewhere in
  the same body).
- **Verify-me-first instructions** pointing at the committed delivery contract,
  including its honest limit — corroboration against a chat-only lure, not
  proof against a branch-writer.

Offered a re-cut on request rather than a re-census; the artifacts exist and a
different slice is cheap.

---

## 2026-08-05 — Manager: Planner pass 10 ACCEPTED; ESCALATING the truncation
class upward — it is program-wide, not a Georgia footnote

Branch `claude/defs-us-scoped-inline-plan10` @ `12f9adf`, merged at sprint
`decc49d`. **Suite: 854 passed, 1 xfailed, 0 failed.** Fence verified: `git
diff --stat 57a8068..HEAD -- backend/app/` is EMPTY. Both files under gate
(145 / 247).

### Task 1 — the vocabulary-rot problem is now structurally closed

Placeholder swapped to `denotes`, proven unrecognized by running
`_IDIOM_RE.match` against the SHIPPED regex rather than assuming, and checked
for prefix/word overlap with every current alternative — the near-miss-of-a-
recognized-family trap that sank `shall include`.

The part that matters more than the swap: `_assert_idiom_is_unrecognized` is a
precondition guard both tests call FIRST, so if the placeholder is ever
recognized the tests fail LOUDLY with a message naming the exact remedy,
instead of silently pinning nothing. The Planner verified this live by
monkeypatching `denotes` INTO the vocabulary and confirming the guard fires.
This is the fourth vocabulary-accident-protected test this sprint; it is the
first one that cannot rot silently.

### Task 2 — the pre-existing claim VERIFIED by me independently

I did not take it on the Planner's word, because it is the premise of an
escalation. `git show 9c47af7:…/us_scoped_inline.py` and `fcd2746` both
contain, at line 271, the exact truncation mechanism:

    region_end = events[i + 1].start if i + 1 < len(events) else len(body)

**Byte-present in the rule's original authorship commit**, before any fix
cycle in this sprint. Georgia's "Code section" widening only widened which
phrases can fire a second trigger event; it did not create the mechanism.

The Planner further reproduced term loss on the pinned row with the "Code "
tolerance reverted in-memory — a plain `for purposes of this chapter` sentence
later in the same body fires the second event, and `"chapter"` has been in
`_UNIT_ALT` since day one. **37 distinct terms recoverable vs 9 captured
today: 28 lost on one row.**

Pinned as `xfail(strict=True)` (the S-R11 tripwire precedent) asserting the
CORRECT behavior, verified to XFAIL today and XPASS under a simulated fix —
so it converts into a loud suite failure the moment anyone fixes the
underlying defect. Row byte-verified twice, sha256 recorded.

### ESCALATION — this leaves the panel

**The structural precondition (`_STRONG_TRIGGER_RE` firing 2+ times in one
body) is present in 38,431 rows — 1.89% of the corpus — across ALL 53 of 53
jurisdictions**, from 0.16% (MD) to 10.66% (TN), 9.47% (AR), 9.42% (GA),
9.29% (MA).

A 75-row deeper sample across the 5 highest-density states found **2 rows with
real measured term loss, in CA and GA — two different states**, ≈2.7% actual
loss within the at-risk population, extrapolating to **on the order of 1,000+
affected rows program-wide**.

Three things I want stated precisely rather than dramatically:

1. **The 1,000+ is an extrapolation from 75 rows, not a count.** The Planner
   said so unprompted, in its report AND in the pinned test's own docstring. A
   fix decision should commission an exact sweep; this number is sized to
   answer "is this a footnote or a class?", nothing finer.
2. **The confirmed part needs no extrapolation**: the mechanism predates this
   sprint (verified by me at two commits), the precondition exists in all 53
   jurisdictions (full-corpus scan), and real loss is measured OUTSIDE Georgia.
3. **It is not this panel's to fix.** The fix means distinguishing a
   list-introducing trigger from a mid-document carve-out or cross-reference —
   an architecture-level change to trigger-event region splitting that would
   affect every family panel built on this rule shape, and it predates our
   sprint. ESCALATION 2's ruling anticipated exactly this outcome; pass 10's
   job was to supply the verification and scale, which it has.

Meanwhile nothing is lost silently: the tripwire is committed and
self-alarming, and the accepted-for-now tradeoff remains 3,605 terms gained
vs 116 lost on the Georgia change that surfaced it.

---

## 2026-08-05 — Manager: truncation-class escalation RULED and disposed

Program disposition, recorded so it survives a seat handover:

1. **The CLASS** goes on the D-CERT worklist as a NAMED, VERIFIED,
   SELF-ALARMING-PINNED zero-miss class. Our `xfail(strict=True)` tripwire is
   the containment. The exact sweep pass 10 recommended is **commissioned as
   part of the US certification build** rather than as a separate scout — the
   certification needs that population regardless, so the count arrives without
   a duplicate census.
2. **The FIX** — distinguishing list-introducing triggers from mid-document
   carve-outs in trigger-event region splitting — goes to the
   **core-follow-on-3 accumulator** as a cross-panel architecture item,
   carrying our two-commit mechanism proof, the 38,431-row precondition census,
   the CA/GA measured-loss evidence, and the 37-vs-9 exemplar row. **Not this
   cycle's work.** The stated reason is worth keeping: an architecture change to
   region splitting mid-merge-queue is the correct-in-isolation /
   wrong-in-composition trap this program keeps catching — and nothing is lost
   silently meanwhile, because the pin fails loudly the moment anyone fixes it.
3. **The class appears in the director's certification residual enumeration
   with our data attached.** It is not quietly parked, which was the outcome
   ruling S-R16 and this escalation were both designed to prevent.

Recorded as the thing that made this decidable in one round rather than two:
the escalation carried a two-commit proof of the mechanism, a full-corpus
precondition census, measured loss OUTSIDE the motivating state, and an honest
extrapolation-vs-count boundary. A conclusion of the same shape without those
four would have earned another round of questions, and deserved to.

### Remaining panel scope

Unchanged: the two in-flight re-cuts for the markers panel (IL shape-validity
three-way split; the "in general" per-jurisdiction label VOCABULARY), then
**QA cycle 3 from this sprint's first fully-green suite** — 854 passed,
1 xfailed, 0 failed.

---

## 2026-08-05 — Manager: IL check RESOLVED; and a provenance error of mine,
recorded rather than quietly fixed

### Re-cut 1 — the citation-tail-misparse hypothesis CONFIRMED as dominant

45-row stratified sample: **41 (91%) are citation-tail misparses** — genuine
single-definition sections where the "marker" is a fragment of the section's
OWN citation number. These are not instances of the `(N) LABEL.` convention,
and holding them out of the markers-panel split was correct: folding them in
would have scored that panel against a target that should not exist.

Exact spread: **IL 477, ID 66, MO 43, AZ 12, NY 9, KS 6, CO 3, FL 1, NJ 1**
(= 618). **ID and MO are ~18% between them** — substantial, not noise. The
"Illinois quirk" framing would have left two states' worth of the shape
unexamined, which is why I asked for the spread re-confirmed rather than
assumed.

The 9% remainder is not rounding error and I am not discarding it: 2 rows are
cross-citation contamination, and **2 NY rows look GENUINE** — real lettered
markers with "Definitions"/"the following terms" language, mis-bucketed by
marker misattribution. Conceptually those belong in the NARROW bucket, so
**1,675 may be marginally undercounted, order ~25-60 rows corpus-wide with
wide uncertainty** (extrapolated from 2 sampled rows — a direction, not a
count). It does not move the sizing decision; I have told the markers manager
that the error bar leans UP rather than being symmetric, because a partner
planning against a number deserves to know which way it will drift.

### My error: I stripped provenance in a handover, and an agent caught it

I asked the reconciliation analyst for the "in general" per-jurisdiction
breakdown. **Those figures were never its work** — they came from the original
AL-class scout (`aa02b1af67484dda8`, scripts `si_cycle2_scout1_*`). The analyst
**correctly REFUSED**: it could not verify numbers it had no artifacts for, and
read the mismatch as possible fabrication. Its instinct was right and my
attribution was wrong. Re-ordered from the agent that actually holds the
artifacts.

Recording it rather than silently re-routing, for two reasons. First, it is an
unusually literal instance of the thing I had just written into this log —
"numbers travel across handovers with their provenance stripped; the label on
the jar is what rots." I stripped a label and the figure nearly acquired a
false origin, one hop after saying so. Second, the mechanism that protected the
data was **an agent declining to confirm something it could not verify** — the
same instinct as the Developer that refused an unverifiable delivery
instruction, and the analyst that refused a raw-id redirect, arriving from a
third direction. Three refusals this program, three times correct. That is a
pattern worth naming rather than praising case by case: agents that verify
before confirming have caught more real problems here than any process I have
written.

Also told the scout its own data's true provenance, so a stray reference to it
belonging to a reconciliation analyst does not confuse it later.
