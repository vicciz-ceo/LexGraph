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
