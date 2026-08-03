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

