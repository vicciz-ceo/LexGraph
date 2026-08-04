---
id: "2026-08-04-defs-core-scope"
status: dev-complete
current_role: qa
branch: claude/defs-core-scope
worktree: /Users/nerya/LexGraph-wt/defs-core-scope
locked_by: null
locked_at: null
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04T09:48:54Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 9
lint: PASS
completed_items: 0
dev_complete_items: 9
qa_cycles: 0
previous_sprint: "2026-08-02-us-state-law"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
  - docs/sprint/programs/2026-08-04-definition-completeness-recon.md
---

# Sprint: Core scope seam — scoped definitions + rule registry

**Program role: CRITICAL PATH.** Every other program sprint builds behind this
sprint's seam and merges after it. The Planner must publish the seam spec (a
`## Seam spec (published)` section in this contract, committed and pushed on
the sprint branch) as its FIRST deliverable so family panels can plan against
it before this sprint's code lands.

## Mandate

From the program (read `design_sections` first — do not re-derive recon):
make scope a first-class, profile-dispatched concept so that a definition
declared for a specific article/subsection/chapter creates USES_DEFINITION
assertions ONLY for mentions within that scope, in every jurisdiction; and
give per-jurisdiction convention rules a registry seam so family sprints ship
rules as NEW modules without editing shared files.

Recon facts to build on (dossier §1): enforcement already exists and works
(`matcher._in_scope`, matcher.py:104-110; `Definition.scope`,
definition.py:35); production of scoped rows is Hebrew-only
(`_CHAPTER_SCOPE_TRIGGERS` pipeline.py:62-68; `_LOCAL_TRIGGER_RE`/`_ADHOC_RE`
extract.py:28-33); US fallback extraction lives inline in pipeline.py
(:106-289), not in USProfile.

## Acceptance gates (program manager-defined)

- **C1 — Scope is enforced everywhere, at every granularity.** A definition
  scoped to an article, subsection, chapter/part/siman creates assertions
  only for mentions within that scope — proven live-path in BOTH directions
  (in-scope mention links; out-of-scope mention does not), for IL AND US test
  cases. Subsection granularity is new design work: mentions must be
  scope-checked below article level.
- **C2 — Scope triggers dispatch through the profile.** No Hebrew-only (or
  English-only) scope literals in shared pipeline/matcher/extract code;
  English triggers ("As used in this section/subsection/chapter", "For
  purposes of this section/part") produce correctly-scoped definitions.
- **C3 — Extraction lives behind the seam.** The inline-quote fallback,
  body-heading derivation, and preamble detection move from pipeline.py into
  profile-owned code; pipeline.py retains no jurisdiction-specific literals.
- **C4 — Rule registry.** A new convention rule ships as a new module plus a
  registration, with zero edits to shared modules; the seam interface is
  documented in this contract for the family sprints.
- **C5 — Nothing regresses.** All existing IL tests green unchanged (prior
  R2: editing one is a planning bug — escalate); US baseline states
  (IN/CO/KY/LA/DE/ID/NJ/MI/MT/ND/NY/OK) capture rates do not drop.

## Standing constraints

All program standing constraints apply (program doc §Standing constraints):
CodeGraph first for all code work; red-before-green with live-path RED tests;
Planner owns tests; QA independent; absolute zero-miss bar (director
decision 3); zero-miss vs false-positive conflicts escalate (P-R2), never
silently resolved.

## Next Steps

- [x] **I1 (DEV COMPLETE — manager-verified, pending QA) — `UnitPath` model + `_in_scope` prefix-matching + narrowest-governs precedence (C1).**
  `UnitStep`/`UnitPath` in `extract.py`; `Article.unit_path`; `profile.resolve_unit_path(article, char_offset=None)`.
  RED: `backend/tests/unit/test_definition_links_matcher.py::test_link_articles_to_definitions_respects_subsection_scope_isolation`,
  `::test_link_articles_to_definitions_respects_generic_scope_unit_containment`,
  `::test_link_articles_to_definitions_respects_enumerated_local_scope`;
  `backend/tests/unit/test_definition_links_profiles.py::test_il_profile_resolve_unit_path_returns_the_articles_own_base_path`,
  `::test_il_profile_resolve_unit_path_extends_to_sub_article_granularity_given_a_char_offset`.
  Live call-site: `backend/tests/integration/test_definition_links_pipeline_scope_seam.py::test_a_registered_scope_trigger_rule_is_reached_by_the_real_pipeline`
  (exercises scope production end-to-end; a dedicated live-path test for
  precedence/tie-pinning per M10 obligation (a) is NOT YET authored --
  open item, see report).
- [x] **I2 (DEV COMPLETE — manager-verified, pending QA) — Profile-dispatched scope determination + extraction seam (C2, C3).**
  `profile.determine_scope`, `profile.extract_local_scope_definitions`,
  `profile.derive_heading_from_body`, `profile.extract_definitions_from_section(..., heading_was_derived=)`.
  RED: `test_definition_links_profiles.py::test_il_profile_determine_scope_matches_todays_chapter_scope_triggers`,
  `::test_il_profile_extract_local_scope_definitions_matches_todays_extract_local_and_adhoc`,
  `::test_il_profile_derive_heading_from_body_is_trivially_none`,
  `::test_il_profile_extract_definitions_from_section_accepts_the_new_heading_was_derived_kwarg`.
  Live call-site: `test_definition_links_pipeline_scope_seam.py::test_a_registered_scope_trigger_rule_is_reached_by_the_real_pipeline`.
- [x] **I3 (DEV COMPLETE — manager-verified, pending QA) — `pipeline.py` retains no jurisdiction-specific literals (C3).**
  Delete `_CHAPTER_SCOPE_TRIGGERS`/`_determine_scope`/`_is_placeholder_heading`/
  `_derive_heading_from_body`/`_extract_inline_quoted_definitions` (+regexes)
  from `pipeline.py`; delete its direct calls to `extract_local_definitions`/
  `extract_adhoc_definitions`. **No dedicated RED test authored** (a
  structural absence-of-symbol test was considered and rejected as
  low-value churn — I1/I2's live-path tests already fail today BECAUSE
  the seam doesn't exist; once I1/I2 land, this item's completion is
  verified by code review + the stale-pin sweep, not a new test).
- [x] **I4 (DEV COMPLETE — manager-verified, pending QA) — Rule registry: 6 kinds, auto-discovery, registration (C4).**
  `app/definition_links/rules/{__init__.py,registry.py}`.
  RED: `backend/tests/unit/test_definition_links_rules_registry.py` (10 tests, all `ImportError` today).
  Live call-site: `test_definition_links_pipeline_scope_seam.py::test_a_registered_scope_trigger_rule_is_reached_by_the_real_pipeline`.
- [x] **I5 (DEV COMPLETE — manager-verified, QA verified GREEN, no further
  Developer work needed) — M8(a): `sections.parse_articles` bare-`@` marker
  loses articles/definitions.**
  RED: `backend/tests/unit/test_definition_links_sections.py::test_parse_articles_does_not_silently_merge_a_bare_at_marker_section_into_its_neighbor`,
  `::test_parse_articles_does_not_return_zero_articles_for_a_document_using_only_bare_at_markers`.
  **RETARGETED (resolves ESCALATION E-3 in -log.md, Round 15):** the corpus
  measurement behind M8(a) ("124/6,133 IL laws affected, 12 with unambiguous
  definitions") does not hold up — re-measured against the real 6,133-law
  corpus, all 331 real bare-`@` occurrences are followed by wiki table/markup
  and **zero** are followed by a definitions heading, so the original live
  test's fixture (`@` / heading line / `:-` entry) pinned a shape that does
  not exist. The already-merged fix itself (a bare `@` starts its OWN
  section, preventing 331 real table bodies from being silently concatenated
  into a preceding article) is unaffected and still correct — only the
  "definitions get CAPTURED from a bare-`@` section" claim was wrong.
  Live call-site RETARGETED from capture to **reachability**:
  `test_definition_links_pipeline_scope_seam.py::test_run_definition_linking_reaches_a_bare_at_markers_section_body_without_dropping_it_live`
  — a vendored, byte-for-byte real excerpt of
  `רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות.wiki`
  (`backend/tests/fixtures/wiki_laws/רשימת הזכויות לפי חוק לקידום התחרות ולצמצום הריכוזיות_excerpt.wiki`,
  source lines 9-13 + 102-119) pins that this real bare-`@` document's body
  (including the line 116-119 `::-`/"בפרט זה" nested entries) survives
  ingestion as a genuine `Article` and reaches the real
  `run_definition_linking` -> Stage 2 extraction call, rather than being
  silently dropped (this real document's own failure mode pre-fix: TOTAL
  document loss, since it contains no other `@ N.` marker at all).
  **Deliberately NOT pinned:** capture of the four `::-` nested definitions
  ("סיווג"/"צד קשור"/"קטגוריה"/"שליטה") as `Definition` rows — that
  double-colon-nested, "בפרט זה"-triggered idiom is a previously-
  uninventoried Hebrew scope-trigger variant outside core's
  `_LOCAL_TRIGGER_RE` ("לענין זה,"/"בסעיף זה," only); whether/how to capture
  it is the IL panel's contractual territory. **Ran GREEN immediately** —
  the merged I5 half already delivers reachability; no Developer work
  required for this retarget.
- [x] **I6 (DEV COMPLETE — manager-verified, pending QA) — M8(b): `us_profile.find_term_uses` case-insensitive word-boundary matching.**
  RED: `backend/tests/unit/test_definition_links_us_profile.py::test_us_profile_find_term_uses_matches_a_lowercase_mention_of_a_capitalized_defined_term`.
  Guard/proof (already green, must STAY green): `::test_us_profile_find_term_uses_case_insensitive_match_still_respects_word_boundaries`,
  `::test_il_hebrew_find_term_uses_is_unaffected_by_the_m8b_case_fold_fix`
  (full IL suite passing unchanged is the binding proof per the ruling —
  see report's RED run tail: 644 passed / 0 IL regressions).
  **Corpus-wide FP-exposure measurement not produced** (no local corpus
  access this worktree — see seam spec M8(b) section); flagged for
  whichever panel/session has corpus access.
  No live DB-backed call-site test authored for I6 specifically (M8(b) is
  a pure-function fix with no new dispatcher branch) — the unit-level RED
  above is the wiring gate's minimum for a non-dispatcher bug fix.
- [x] **I7 (DEV COMPLETE — manager-verified, pending QA) — M12: `find_citations` decimal-truncation + state-code baseline fix, `CitationRule` kind.**
  RED: `backend/tests/unit/test_definition_links_us_profile.py::test_us_profile_find_citations_does_not_truncate_a_decimal_section_number`,
  `::test_us_profile_find_citations_recognizes_a_state_code_citation_shape`,
  `::test_us_profile_find_citations_still_detects_the_six_term_parent_clause_citation`;
  `backend/tests/unit/test_definition_links_rules_registry.py::test_citation_rule_registers_and_looks_up`.
  Guard (already green): `::test_il_hebrew_find_citations_is_unaffected_by_the_m12_baseline_fix`.
  Expected values verified identical to `claude/defs-us-multiterm@f1011f0`'s
  `test_definition_links_e1_pointer_reference_capture.py::test_or_enforcement_officer_state_code_citation_is_invisible_today`,
  `::test_tx_governmental_body_section_citation_is_truncated_to_a_wrong_target`,
  `::test_tx_parent_clause_2001_003_citation_is_truncated_to_a_wrong_target`
  (read-only fetch; core's fix is expected to turn all three green too — QA
  should check this at program-close integration, not rediscover it).
  **Stage C closed the deferred set**: `_TRIGGER_PHRASES` additions now RED at
  `test_definition_links_us_profile.py::test_us_profile_detect_cross_law_derivations_recognizes_the_has_the_meaning_given_that_term_in_idiom`,
  `::test_us_profile_detect_cross_law_derivations_recognizes_the_has_the_meaning_assigned_by_idiom`,
  `::test_us_profile_detect_cross_law_derivations_recognizes_the_have_the_meanings_assigned_by_idiom`;
  the internal-same-law pointer emission path (v2.1 §4) end-to-end at
  `test_definition_links_pipeline_scope_seam.py::test_a_whole_definition_pointer_to_an_internal_same_law_article_emits_a_derives_from_law_edge_to_that_article`.
- [x] **I8 (DEV COMPLETE — manager-verified, pending QA) — M14: NY `text` stores literal `\n` (never a real newline,
  40,102/40,102 rows) -- `_split_into_numbered_blocks`'s `text.split("\n")`
  never fires, so 1,479/1,479 heading-recognized NY Definitions sections
  yield zero candidates.** Acceptance: a real NY numbered-entry body's
  literal-`\n` text yields its real defined terms by Stage 2. Layer:
  Planner leans **ingest** (Hebrew untouched by construction; see -log.md).
  RED + live call-site (one layer-agnostic test, chains real
  `ingest_us_statute_rows` -> `normalize_for_parsing` -> `get_profile
  ("US-NY").extract_definitions_from_section`):
  `backend/tests/integration/test_ingest_us_statutes_ny_newline_defect.py::test_real_ny_row_with_literal_backslash_n_yields_its_definitions_via_the_live_pipeline`.
  Fixture: `backend/tests/fixtures/us_statutes/ny_m14_newline_defect_row.json`.
- [x] **I9 (DEV COMPLETE — manager-verified, pending QA) — M15: `pipeline.py` calls the bare `normalize_for_parsing`, not
  `profile.normalize_for_parsing` — dead dispatch (AK cp1252-mojibake family
  needs it live).** Acceptance: `run_definition_linking` resolves each
  article's document profile and calls THAT profile's `normalize_for_parsing`
  before extraction; a `USProfile.normalize_for_parsing` override changes
  live extraction; `HebrewProfile`'s passthrough stays byte-identical
  (implementer: keep it a pure delegate to `normalize.normalize_for_parsing`).
  RED + live call-site, all three in
  `backend/tests/integration/test_definition_links_pipeline_normalize_dispatch.py`:
  `::test_live_pipeline_dispatches_normalize_for_parsing_through_each_documents_own_profile`,
  `::test_overriding_us_profile_normalize_for_parsing_changes_what_the_live_pipeline_extracts`,
  `::test_live_pipeline_hebrew_normalization_stays_byte_identical_through_the_passthrough`.

**Closed by Stage C, previously "Explicitly OPEN":** M9 enumerated-scope
live-path proof — RED at
`test_definition_links_pipeline_scope_seam.py::test_an_enumerated_local_scope_links_every_member_article_and_excludes_a_non_member_live`.
M10 tie-pinning live-path test (obligation (a)) — the previous attempt was
honestly REMOVED (it constructed only one Definition row, so it passed for
the wrong reason); this pass built a genuine tie using the spec's own named
instance (v2.1 §1, "a local def and a set-valued local def covering the same
article are rank-EQUAL"): two DISTINCT Definition rows (different owning
articles) both scope-containing the same target article — RED at
`test_definition_links_pipeline_scope_seam.py::test_two_same_rank_local_scoped_definitions_that_tie_both_get_a_uses_definition_assertion_live`.
`StructuralUnitRule` US-side (parquet) data availability — **RESOLVED, not
unresolved** (manager Round 9, verified against a real parquet file, not
docs): `backend/tests/fixtures/us_statutes/de_sample_rows.parquet` carries
`breadcrumb`, `display_path`, `chapter`, `chapter_name`, `title_number`,
`section_number`, `subsection_count` — US-side structural unit data IS
reachable; no ingest-contract escalation needed. Sub-article
`USES_DEFINITION` anchoring is NO LONGER open — D-ANCHOR (Option C) is now
the director's FINAL ruling (not provisional) and IS pinned:
`test_definition_links_pipeline_scope_seam.py::test_a_mention_inside_a_specific_subsection_resolves_to_the_correct_unit_path_live`,
via a retrieval-seam helper (`pipeline.get_mention_unit_paths`) rather
than any storage-shape assertion, per the binding test-shape constraint.
Deep-nesting (no depth cap) and the no-bare-sub-unit-without-its-parent
invariant are pinned at
`test_definition_links_profiles.py::test_resolve_unit_path_supports_genuinely_deep_nesting_not_hard_coded_to_two_or_three_levels`,
`::test_resolve_unit_path_never_represents_a_sub_unit_without_its_rooting_article`.

**Deliberate gap, recorded for QA (I3, ruling M13):** the grep-shaped guard
that pipeline.py retains no jurisdiction-specific literals is now pinned at
`test_definition_links_pipeline_no_jurisdiction_literals.py::test_pipeline_module_defines_none_of_the_deleted_jurisdiction_specific_symbols`,
`::test_pipeline_module_contains_no_hebrew_scope_trigger_literals`,
`::test_pipeline_module_no_longer_references_the_hebrew_only_extraction_functions_directly`
— a mechanical AST/source-substring check (no behavioral assertion), by
design: I1/I2's own live-path tests prove the seam is REACHED, this file
proves the OLD literals are GONE.

## Dev Complete

- **I4 — Rule registry** (`4143487`). `app/definition_links/rules/{__init__.py,registry.py}`.
- **I5 — M8(a) bare-`@` articles** (`feea0d1`). `sections.py` `_BARE_ARTICLE_MARKER_RE`.
- **I6 — M8(b) case-folded term matching** (`9e5dc36`). `us_profile.py` — `re.IGNORECASE` added to the existing `\b`-anchored pattern only.

Merged to sprint branch as `c641df3` (`--no-ff`, pre-checked clean).
Manager verification: diff production-only + zero test edits; risk grep 0;
combined-tree evaluator **656 passed / 26 failed / 0 errors** backend,
**165 passed** frontend. Baseline 644 never dropped.

## Completed

_None._

## Context Dump

FULLY GREEN @ `e5fb8f9`: backend 686 passed/0 failed, frontend 165, tsc clean. All 9 items Dev Complete, manager-verified (diff + own suite run); NONE QA-verified. Next role = QA.
QA brief MUST carry: per-item proving `file::test` map (in each Next Steps entry); **P-R7** build zero-miss ground truth INDEPENDENT of the capture mechanism's signals + check denominators aren't derived from code under test; **D-ANCHOR** assert sub-article anchoring via `get_mention_unit_paths` retrieval seam, NEVER storage shape (column name/type/`subject_entity_type` deliberately unpinned — recorded gaps, not oversights).
Residuals to verify, not inherit: CA 21 rows newly newline-unescaped (CA not in guard set); NY 40,102/40,102; AK mojibake is a DIFFERENT byte family from I9's real-Unicode curly-quote collapse — check both pins.
Process: never `git stash` (stack SHARED across worktrees, concurrent writers); QA commits touch ONLY test+contract files; merges manager-owned; never push main; no PR.
Worktrees: sprint + dev1-dev4 under /Users/nerya/LexGraph-wt/, each with its OWN venv (main checkout's venv imports wrong code).
Routed AWAY from core: `::-`/`בפרט זה` capture → IL panel. Corrected fact for IL's I4 sweep: bare-`@` = 42 files/331 occurrences, ALL table-shaped (not "124 laws").
Full panel history (16 rounds, rulings M1-M15, E-1..E-3) in `-log.md` — do not auto-load.

## Seam spec (published)

**Moved to `docs/sprint/sprints/2026-08-04-defs-core-scope-seam.md`** (contract
line budget). That file holds all six published versions verbatim; **v2.4 is
AUTHORITATIVE and final** — where an earlier version disagrees, v2.4 wins.

Family panels: read the seam doc, not this contract, for the interface.
Key supersessions to be aware of: the `register_scope_unit_kind`/`rank_for`
rank registry was WITHDRAWN (v2.2; a pinned test asserts its absence), scope
containment is prefix-matching over a `UnitPath` with narrowest-governs =
longest-matching-prefix, and `find_citations` IS rule-extensible (v2.3).

## Stale-pin sweep

Swept `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/e2e/`
for every symbol this sprint deletes/renames/changes the signature of:
`_determine_scope`, `_CHAPTER_SCOPE_TRIGGERS`, `_is_placeholder_heading`,
`_derive_heading_from_body`, `_extract_inline_quoted_definitions`,
`link_articles_to_definitions`, `find_term_uses`, `find_citations`,
`extract_local_definitions`/`extract_adhoc_definitions`.

Result: **none need editing.**

- `_determine_scope` / `_CHAPTER_SCOPE_TRIGGERS` / `_is_placeholder_heading`
  / `_derive_heading_from_body` / `_extract_inline_quoted_definitions` —
  0 references anywhere under `backend/tests/`; all 5 live ONLY in
  `pipeline.py` today (confirmed via `grep -rln` across `backend/tests`
  and `backend/app`). Deleting them from `pipeline.py` breaks no test.
- `link_articles_to_definitions` — every caller (`test_definition_links_
  matcher.py`, `test_us_profile_definitions_section_end_to_end.py`,
  `pipeline.py`) calls it with its EXISTING signature
  (`(definitions, articles[, profile=...])`); this sprint's new behavior
  is reached by reading additional attributes off the SAME positional
  arguments (`.unit_path` etc.), not by adding/renaming parameters — no
  call site needs updating.
- `find_term_uses` (`us_profile.py`'s, the one M8(b) modifies) — every
  existing caller asserts either membership (`any(... in ...)`) or an
  exact-case match that a case-INSENSITIVE superset still satisfies
  (case-folding only ADDS matches, never removes one that matched
  before). Empirically confirmed, not just reasoned: the full suite run
  below shows 644 passed = 641 baseline + exactly 3 new PASSING guard
  tests this sprint added, 0 previously-passing tests newly failing.
- `find_citations` — existing assertions use substring membership
  (`expected_substring in c`) against patterns the decimal-truncation/
  state-code fixes don't touch (no existing test's expected substring
  contains a decimal section number or a state-code citation). Same
  empirical confirmation as above.
- `extract_local_definitions` / `extract_adhoc_definitions` — NOT
  deleted or changed (seam spec: they become IL's own registered
  `ScopeTriggerRule` bodies, called the same way internally); their own
  direct unit tests (`test_definition_links_extract.py`) are untouched,
  confirmed via the full run below (that file's tests are among the 644
  passing, unmodified).

Full backend suite (`backend/.venv/bin/pytest backend/tests -q
--continue-on-collection-errors`, this worktree, this commit):
**644 passed, 20 failed (this sprint's genuine RED, +3 from the v2.4
dossier-alignment/D-ANCHOR pass: deep-nesting, the no-bare-sub-unit
invariant, and sub-article anchoring), 1 collection error (this sprint's
registry module, genuine RED), 18 warnings, ~15.9s.**
0 previously-passing tests now fail — C5 confirmed empirically, not
merely argued. Frontend/typecheck not re-run this pass (no frontend file
touched this sprint; `git diff --name-only` confirms zero `frontend/`
paths in this sprint's changes).

**Stage C update.** The collection error above is FIXED (deliverable 1: the
module-level import in `test_definition_links_rules_registry.py` moved
inside each test body) — the contract's own plain evaluator command
(`pytest backend/tests -q`, no extra flags) now runs to completion with no
`--continue-on-collection-errors` needed. After Stage C's 7 new RED tests
(M9 live proof, M10 tie, pointer emission, 3 `_TRIGGER_PHRASES` idioms, I3
guard ×3 — the collection-error fix and D-ANCHOR/deep-nesting/invariant
tests were already in place at Stage C's start): `backend/.venv/bin/pytest
backend/tests -q` → **644 passed, 38 failed, 0 errors, 18 warnings, ~13-17s**.
644 unchanged throughout every Stage C commit (verified after each one).


---
