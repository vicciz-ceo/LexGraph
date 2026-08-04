---
id: "2026-08-04-defs-core-scope"
status: in-progress
current_role: developer
branch: claude/defs-core-scope
worktree: /Users/nerya/LexGraph-wt/defs-core-scope
locked_by: "claude-code:developer"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:planner"
last_updated: "2026-08-04"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 8
completed_items: 0
dev_complete_items: 3
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

- [ ] **I1 — `UnitPath` model + `_in_scope` prefix-matching + narrowest-governs precedence (C1).**
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
- [ ] **I2 — Profile-dispatched scope determination + extraction seam (C2, C3).**
  `profile.determine_scope`, `profile.extract_local_scope_definitions`,
  `profile.derive_heading_from_body`, `profile.extract_definitions_from_section(..., heading_was_derived=)`.
  RED: `test_definition_links_profiles.py::test_il_profile_determine_scope_matches_todays_chapter_scope_triggers`,
  `::test_il_profile_extract_local_scope_definitions_matches_todays_extract_local_and_adhoc`,
  `::test_il_profile_derive_heading_from_body_is_trivially_none`,
  `::test_il_profile_extract_definitions_from_section_accepts_the_new_heading_was_derived_kwarg`.
  Live call-site: `test_definition_links_pipeline_scope_seam.py::test_a_registered_scope_trigger_rule_is_reached_by_the_real_pipeline`.
- [ ] **I3 — `pipeline.py` retains no jurisdiction-specific literals (C3).**
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
- [x] **I5 (DEV COMPLETE — manager-verified, pending QA) — M8(a): `sections.parse_articles` bare-`@` marker loses articles/definitions.**
  RED: `backend/tests/unit/test_definition_links_sections.py::test_parse_articles_does_not_silently_merge_a_bare_at_marker_section_into_its_neighbor`,
  `::test_parse_articles_does_not_return_zero_articles_for_a_document_using_only_bare_at_markers`.
  Live call-site: `test_definition_links_pipeline_scope_seam.py::test_run_definition_linking_does_not_lose_a_definition_behind_a_bare_at_marker`.
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
- [ ] **I7 — M12: `find_citations` decimal-truncation + state-code baseline fix, `CitationRule` kind.**
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

New sprint. Planner starts here: read the program doc + recon dossier
(§1 code map has every file:line), then publish the seam spec before
authoring RED tests.

## Seam spec (published)

Stage A deliverable (Planner). This is a CONTRACT — build against it without
asking. It is STABLE once pushed; any later change is an escalation through
the sub-manager to the program manager. Rationale/transcripts live in the
panel log, not here.

### What lands in THIS sprint vs. what family panels build

**Done here (assume it, do not rebuild it):** C1 (subsection-granularity
enforcement), C2 (profile-dispatched scope triggers, mechanism + one proven
English example per granularity), C3 (pipeline.py has zero jurisdiction
literals), C4 (the rule registry itself, working end-to-end for both
jurisdictions). **Family panels build:** new rule MODULES registered into
the seam below — broader phrase/marker/heading coverage, not new mechanism.
No family panel edits `pipeline.py`, `matcher.py`, `profiles.py`, or
`extract.py`'s existing functions.

---

### Seam 1 — profile-dispatched scope + subsection granularity (C1, C2, C3)

**`JurisdictionProfile` Protocol (`profiles.py`) — methods added/changed:**

```python
def determine_scope(self, body_text: str) -> str: ...
# Replaces free function _determine_scope. Unchanged 2-way contract:
# scans body_text's first non-blank line for CHAPTER-scope trigger
# phrases; returns "chapter" or "law-wide". Used ONLY for the
# Definitions-SECTION path (a whole section's default scope).
# HebrewProfile: same Hebrew triggers as today, now sourced from a
# registered ScopeTriggerRule set (jurisdiction_codes=("IL",)), not a
# module-level tuple. USProfile: sourced from rules registered for
# "US-*"/exact US-<code>; core sprint registers one proof rule (see
# worked example) so the mechanism is live, not theoretical.

def extract_local_scope_definitions(
    self, article_body: str, *, article_number: str
) -> list[DefinitionCandidate]: ...
# NEW. Replaces pipeline.py's direct calls to extract_local_definitions/
# extract_adhoc_definitions. Runs every registered ScopeTriggerRule for
# this profile's code over an ORDINARY (non-Definitions-heading) article
# body; unions all candidates (zero-miss: rules never suppress each
# other). Each candidate's .scope is "local" (article-level) or
# "subsection" (see below), stamped by the RULE, not by this method.
# HebrewProfile: today's לענין זה/בסעיף זה/להלן behavior, unchanged,
# now reached via 2 pre-registered IL rules instead of a direct call.
# USProfile: unions whatever "US-*"/US-<code> rules are registered
# (initially the one proof rule below; family panels add more).

def split_into_subsections(self, article_body: str) -> list[Subsection]: ...
# NEW. Subsection is a new frozen dataclass in extract.py:
#   @dataclass(frozen=True)
#   class Subsection:
#       label: str   # e.g. "b", "2" — profile-normalized marker text
#       start: int   # char offset into article_body, inclusive
#       end: int     # char offset into article_body, exclusive
# Computed fresh every call (never persisted) from the SAME normalized
# body string extraction and matching both already use, so offsets never
# desync from a stored value. Exact marker regex per profile is THIS
# sprint's own Stage B work (IL: קטן/lettered markers; US: adapts
# us_profile.py's existing _MARKER_TOKEN_RE chain logic) — not something
# a family panel needs to implement. A family panel's OWN rule may call
# this method if its convention is subsection-scoped (see kind
# "scope_trigger" below); most won't need to.

def derive_heading_from_body(self, heading: str, body: str) -> str | None: ...
# NEW. Moves pipeline.py's _is_placeholder_heading/_derive_heading_from_body
# (and their regexes) verbatim into us_profile.py behind this method.
# HebrewProfile: always None (no placeholder-heading concept in IL data).

def extract_definitions_from_section(
    self, text: str, *, scope: str, heading_was_derived: bool = False
) -> list[DefinitionCandidate]: ...
# CHANGED signature (new kwarg, defaulted — existing call sites/tests
# unaffected). USProfile now owns its OWN fallback chain internally:
# try the "(N)"-block splitter first; if empty AND heading_was_derived,
# try the inline-quoted extractor (pipeline.py's old
# _extract_inline_quoted_definitions, moved verbatim into us_profile.py)
# — preserves the exact "zero-risk for the 7 already-working states"
# guarantee (recon §1), since heading_was_derived is False for them.
```

**Scope data contract:**

- `Definition.scope` / `DefinitionCandidate.scope`: still a plain string,
  now a 4-way value: `"chapter" | "local" | "subsection" | "law-wide"`.
  `"chapter"` and `"local"` are BYTE-IDENTICAL in meaning to today — no
  existing test's expected value changes. `"subsection"` is new and
  strictly narrower than `"local"` (same article, AND same subsection).
- Two INDEPENDENT scope-production paths, unchanged in shape:
  (a) Definitions-SECTION path → `profile.determine_scope` → `"chapter"`
  or `"law-wide"` only (a whole section's default). (b) ordinary-article
  path → `profile.extract_local_scope_definitions` → each candidate's own
  registered rule stamps `"local"` or `"subsection"` directly. A rule
  never sees/calls `determine_scope`; the two paths never mix.
- New fields, mirroring the existing (transient, in-memory-only)
  `.source_chapter`/`.source_article_number` on `DefinitionCandidate`:
  `source_subsection: str | None = None`. Comparison uses this string
  against a `Subsection.label` computed fresh at match time — never an
  offset comparison (offsets never leave `split_into_subsections`).
- New persisted column (provenance/display parity with `.scope`, mirrors
  how `.scope` is persisted even though chapter/article identity is only
  recoverable via `Definition.article_id`'s FK — subsection has no such
  FK path, so it must be its own column):
  `Definition.source_subsection: Mapped[str | None] = mapped_column(String(64), nullable=True)`.
  Migration module to mirror: `backend/app/migrations/add_raw_text_columns.py`
  (new sibling `add_definition_subsection_column.py`, same
  `upgrade(engine)`/`downgrade(engine)` raw-DDL shape, no backfill needed
  — nullable, no prior data to migrate).
- Enforcement (`matcher._in_scope`, internal — no public signature
  change to `link_articles_to_definitions`): gains a third branch,
  `"subsection"` → same-article AND the match's char offset falls inside
  the `Subsection` (from `profile.split_into_subsections(article.body)`,
  memoized per article) whose `.label == definition.source_subsection`.
  `"chapter"`/`"local"`/else branches: untouched.
- **Attribution fix (Stage 3, pipeline.py, internal — decided, not
  escalated):** today's `term_to_definition: dict[str, Definition]` flat
  map collapses ALL Definition rows sharing a bare term string into one
  entry per document — already a latent bug for chapter-scoped Hebrew
  dupes, made COMMON by subsection scoping (the same term name routinely
  redefined per-article/per-subsection in real US statutes). Fix: Stage 3
  re-resolves each edge's definition by re-checking scope against the
  edge's own `article_index`/`char_offset`, and creates ONE assertion per
  distinct in-scope Definition row when more than one legitimately
  matches (zero-miss bias, director decision 3) — no change to
  `ArticleUsesTermEdge`'s shape or `_create_assertion`'s dedup key.

---

### Seam 2 — per-jurisdiction rule registry (C4)

**Directory + auto-discovery (zero shared-file edits — stronger than an
append-only file, so no conflict story is needed at all):**

```
backend/app/definition_links/rules/
  __init__.py     # core-authored, stable forever: on import, does
                  # `for m in sorted(pkgutil.iter_modules(__path__))`
                  # then `import_module(f"{__name__}.{m.name}")` for
                  # each — every module below self-registers on import
                  # purely by EXISTING in this directory.
  registry.py     # core-authored, stable forever: dataclasses +
                  # register_*/*_for functions below.
  il_scope_triggers.py     # core-authored: today's לענין/להלן rules
  us_scope_trigger_proof.py  # core-authored: the one proof-of-mechanism rule
  <family-panel modules land here, one new file per panel, e.g.>
  us_scoped_inline.py           # defs-us-scoped-inline
  us_body_preamble.py           # defs-us-preamble
  us_entry_marker_variants.py   # defs-us-markers
  us_heading_variants.py        # defs-us-headings
  us_multiterm_shared_clause.py # defs-us-multiterm
  us_inline_parenthetical.py    # defs-us-multiterm (2nd module, same branch)
```

A family panel's ONLY change to the repo is ADDING its own new file here
plus its own test file(s) — file creation never conflicts in git, so 6
panels landing concurrently is inherently conflict-free.

**Rule kinds (recon §2's five gap classes) — one dataclass each, all in
`rules/registry.py`:**

```python
@dataclass(frozen=True)
class HeadingRule:
    jurisdiction_codes: tuple[str, ...]     # exact codes or "US-*" wildcard
    matches: Callable[[str], bool]          # heading text -> is-a-Definitions-heading

@dataclass(frozen=True)
class BodyPreambleRule:
    jurisdiction_codes: tuple[str, ...]
    derive_heading: Callable[[str], str | None]   # body text -> synthesized heading | None

@dataclass(frozen=True)
class EntrySplitterRule:
    jurisdiction_codes: tuple[str, ...]
    split: Callable[[str], list[str]]       # section body -> raw entry blocks

@dataclass(frozen=True)
class TermClauseRule:
    jurisdiction_codes: tuple[str, ...]
    parse: Callable[[str], list[DefinitionCandidate]]   # one entry block -> candidate(s)

@dataclass(frozen=True)
class ScopeTriggerRule:
    jurisdiction_codes: tuple[str, ...]
    extract: Callable[[str, str], list[DefinitionCandidate]]  # (article_body, article_number) -> local/subsection candidates
```

`jurisdiction_codes` matching: exact `JURISDICTION_CODES` entries, or the
literal `"US-*"` meaning every code with that prefix (never matches
`"IL"`). No other wildcard forms.

**Registration** (`rules/registry.py`, called at rule-module import time,
i.e. at the bottom of the family panel's own file — no other file is
touched):

```python
def register_heading_rule(rule: HeadingRule) -> None: ...
def register_body_preamble_rule(rule: BodyPreambleRule) -> None: ...
def register_entry_splitter_rule(rule: EntrySplitterRule) -> None: ...
def register_term_clause_rule(rule: TermClauseRule) -> None: ...
def register_scope_trigger_rule(rule: ScopeTriggerRule) -> None: ...
```

**Consumption contract — baseline-first, registry-second, per kind:**

- Detection kinds (`heading`, `body_preamble`, `entry_splitter` when it
  needs to pick ONE splitter): the profile's EXISTING baseline logic runs
  first (unchanged — this is what keeps the 7 already-working US states
  and all of IL byte-for-byte stable); only if baseline returns
  false/empty does the profile try registered rules for its code, IN
  FILENAME-SORT ORDER, using the FIRST one that returns a positive
  verdict. Two registered rules both matching the same input is not
  possible to observe from outside (only the first-in-order fires) — a
  family panel whose rule never fires because an earlier-sorted rule
  already claimed the input should rename its file or, if genuinely
  overlapping another family's convention, raise it as a panel question.
- Extraction/union kinds (`scope_trigger`, and `term_clause` applied to
  entry blocks): ALL matching registered rules run, every candidate they
  produce is kept (union, not first-wins) — zero-miss bias. Duplicate
  `Definition` rows are already deduped downstream by pipeline.py's
  existing `(article_id, sorted(terms))` key; nothing new to build.

**Worked example — `defs-us-scoped-inline` adding "As used in this
section, …" as a `scope_trigger` rule:**

```python
# backend/app/definition_links/rules/us_scoped_inline.py
"""Rule: 'As used in this section, "Term" means ...' local-scope trigger
(recon §2 family 1 — 0% captured, all US states affected)."""
import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import ScopeTriggerRule, register_scope_trigger_rule

_TRIGGER_RE = re.compile(
    r'As used in this section,\s*[“"]([^”"]+)[”"]\s*means\s+(.*?)(?=\.\s|$)',
    re.IGNORECASE | re.DOTALL,
)

def _extract(article_body: str, article_number: str) -> list[DefinitionCandidate]:
    return [
        DefinitionCandidate(
            terms=(m.group(1).strip(),),
            definition_text=m.group(2).strip(),
            scope="local",
            source_article_number=article_number,
        )
        for m in _TRIGGER_RE.finditer(article_body)
    ]

register_scope_trigger_rule(
    ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract)
)
```

That file alone (plus the panel's own tests) is the complete change —
`pipeline.py`, `matcher.py`, `profiles.py` need no edits.

---

### Deleted / emptied — do not build on these

- `pipeline.py`: `_CHAPTER_SCOPE_TRIGGERS`, `_determine_scope`,
  `_is_placeholder_heading`(+its 2 regexes), `_derive_heading_from_body`
  (+its 3 regexes), `_extract_inline_quoted_definitions` (+its 2 regexes)
  — all deleted from pipeline.py (moved into `us_profile.py` / behind the
  Protocol methods above). pipeline.py after this sprint calls only
  `profile.*` methods for anything jurisdiction-specific.
- `pipeline.py`'s direct calls to `extract_local_definitions`/
  `extract_adhoc_definitions` — deleted; replaced by
  `profile.extract_local_scope_definitions(...)`.
- `extract.py`'s `_LOCAL_TRIGGER_RE`/`_ADHOC_RE`/`extract_local_definitions`/
  `extract_adhoc_definitions` are **NOT deleted** — they become IL's own
  registered `ScopeTriggerRule` bodies (`rules/il_scope_triggers.py`
  wraps them), reachable ONLY via the registry+profile dispatch. Never
  call them directly from new code.

**New stable entry points:** the 5 Protocol methods above
(`determine_scope`, `extract_local_scope_definitions`,
`split_into_subsections`, `derive_heading_from_body`,
`extract_definitions_from_section`) and the 5 `register_*` functions in
`rules/registry.py`. That is the entire surface a family panel needs.

---

## Seam spec v2 (published) — supersedes v1 where noted below

v1 above is kept visible (panels that already read it need to see the
diff) but is **superseded on the six points listed here**; everything in
v1 NOT listed here (directory/auto-discovery mechanism, the 5
`register_*` functions' existence, `HeadingRule`/`BodyPreambleRule`/
`TermClauseRule`/`EntrySplitterRule` shapes, the attribution-fix
direction, `split_into_subsections`, `derive_heading_from_body`'s legacy
CA/IL/GA branch, `extract_definitions_from_section`'s fallback chain)
is UNCHANGED and still governs. v2 is itself now STABLE — same rule as
v1: any later change is an escalation through the sub-manager.

**What changed, in one line each:** (1) scope is a generic `(kind,
value)` pair with a registered specificity rank, not a closed 4-tier
enum; (2) narrowest-scope-governs precedence is now specified, including
the non-comparable case; (3) `ScopeTriggerRule.extract` takes a context
object, not two positional args; (4) `EntrySplitterRule` moves to the
union side (manager ruling M1, already in effect); (5) `BodyPreambleRule`
dispatch is ungated from `_is_placeholder_heading`; (6) rule modules'
authority is explicitly bounded — `find_term_uses`/`find_citations` are
never overridable by a rule.

### 1. Generic scope units (director E-1 ruling + manager ruling M4)

**Director ruling, binding:** narrowest scope governs — subsection >
article/local > chapter/part/subchapter/siman/etc. > law-wide. The
broader definition still fires wherever no narrower one was detected in
scope. Emit ONLY the governing definition's assertion(s). This also
authorizes the Stage-3 attribution fix flagged in Round 1 (below).

**Data shape** (new, in `extract.py` alongside `DefinitionCandidate`):

```python
@dataclass(frozen=True)
class ScopeUnit:
    kind: str           # e.g. "part", "subchapter", "siman", "chelek" —
                         # any string a rule module registers a rank for
    value: str | None    # concrete identifier (e.g. "II", "B"); never None
```

`Definition.scope` / `DefinitionCandidate.scope` **stays the kind
string, unchanged column, byte-identical for `"chapter"`/`"local"`/
`"law-wide"`** — this IS the `unit_kind`, nothing renamed. `"chapter"`
keeps its existing dedicated field (`.source_chapter`); `"local"` keeps
its existing dedicated field (`.source_article_number`); NEITHER of
those two fields changes shape or meaning. Every OTHER kind (including
v1's `"subsection"`, plus any new kind a family panel registers) uses
ONE new generic field instead of a dedicated one per kind:

- `DefinitionCandidate.scope_value: str | None = None` (transient,
  replaces v1's subsection-only `source_subsection` name — same idea,
  generalized).
- `Definition.scope_value: Mapped[str | None] = mapped_column(String(64), nullable=True)`
  (persisted; replaces v1's `source_subsection` column name — same
  migration-module precedent, `add_definition_subsection_column.py`
  renamed to `add_definition_scope_value_column.py`, same nullable/no-
  backfill shape).

**Specificity rank — the load-bearing piece** (`rules/registry.py`):

```python
def register_scope_unit_kind(kind: str, *, rank: int) -> None: ...
# Lower rank == narrower == governs. Core pre-registers the 4 existing
# kinds: subsection=0, local=10, chapter=20, law-wide=1000 (unreachable
# by design — law-wide never "governs over" anything, it only fires
# when NOTHING narrower matched). A family panel registering a NEW kind
# (e.g. "part") MUST call this once (its own rule module, its own
# import-time side effect — same zero-shared-edit mechanism as C4) and
# picks the rank from ITS OWN measurement of how that kind nests for the
# jurisdictions it targets. Uncertain nesting -> register at the SAME
# rank as the nearest known kind (safe default, see below — a tie never
# costs recall, only a possible duplicate-but-true assertion).

def rank_for(kind: str) -> int: ...   # KeyError on an unregistered kind
                                        # -- no fabricated guess (matches
                                        # this codebase's existing
                                        # resolve_law_title discipline).
```

**Containment (`_in_scope`, internal, generalized):** for kind
`"chapter"`/`"local"`, unchanged legacy comparison. For `"subsection"`,
v1's offset-based branch unchanged (now reading `.scope_value` instead
of the old `.source_subsection` name). For any OTHER registered kind:
does the owning article's `structural_units` tuple (see below) contain a
`ScopeUnit` with a matching `kind` AND `value == definition.scope_value`?

**`structural_units` — one new additive field, added ONCE by core, never
again by a family panel:** `sections.Article` / `pipeline.py`'s
`MatcherArticle` gains `structural_units: tuple[ScopeUnit, ...] = ()`
(default — every existing `Article(...)` construction site, including
every existing test, is unaffected). Core populates it for `"chapter"`
only (mirrors the existing `.chapter` field — `parse_articles` already
tracks chapter headings; this sprint additionally stamps
`ScopeUnit("chapter", article.chapter)` into the same tuple for
consistency with the generic path). **Populating it for a NEW kind
(part/subchapter/siman/chelek/...) is that kind's OWN family panel's
responsibility** — core provides the field and the generic comparison
logic, not a parser for every future structural axis; how a panel
detects "this article is inside Part II" from its own jurisdiction's raw
ingest data is a question for that panel to raise with the sub-manager
when it registers its kind, not something this seam can answer in
general.

**Precedence algorithm** (replaces v1's silent Stage-3 dict): for a
given mention (term, article, char_offset), collect every candidate
whose `_in_scope` check passes. If empty, no assertion. Otherwise, take
the MINIMUM `rank_for(candidate.scope)` among them; keep only candidates
at that minimum rank; emit ONE `USES_DEFINITION` assertion per
DISTINCT surviving `Definition` row (their `object_entity_id`s differ,
so `_create_assertion`'s existing dedup key needs no change).

**Non-comparable scopes (M4(c)) — resolved, not a recall/FP trade, not
escalated:** two candidates can tie at the SAME minimum rank with
DIFFERENT kinds (e.g. one `"chapter"`-scoped, one `"part"`-scoped, both
genuinely containing the mention, no registered order between them).
Resolution: **both survive, both get an assertion.** This is NOT a
recall-vs-precision trade — nothing is suppressed (recall) and nothing
is fabricated (each surviving assertion's scope claim is independently,
factually true: the mention genuinely sits inside both units). A trade
would exist only if keeping both risked a FALSE claim or dropping one
risked a miss; neither applies here, so this is a mechanism choice, not
an escalation-worthy conflict. Flagged prominently in the log/report so
the sub-manager can override if they read it differently.

**AK multi-chapter ranges — explicitly deferred, with the required
fallback (M4's closing instruction):** a scope trigger describing a
RANGE across multiple chapters (e.g. "chapters 5 to 9") is not given a
narrower unit this sprint — no rule this sprint parses a range into a
`ScopeUnit` (a range needs an interval, not a single `value` string,
which is a real extension but not this sprint's). Fallback: such a
candidate's scope stays `"law-wide"` until a future rule module adds a
dedicated range-aware kind. Zero-miss-safe (law-wide never narrows away
a legitimate match); the accepted cost is no PRECISION narrowing for
AK's ~10 known rows, recorded here, not silently dropped.

### 2. `ScopeTriggerRule.extract` — context object (manager ruling M5)

```python
@dataclass(frozen=True)
class RuleContext:
    article_number: str
    chapter: str | None
    structural_units: tuple[ScopeUnit, ...]

@dataclass(frozen=True)
class ScopeTriggerRule:
    jurisdiction_codes: tuple[str, ...]
    extract: Callable[[str, RuleContext], list[DefinitionCandidate]]
    # (article_body, context) -> candidates. The rule may stamp ANY scope
    # kind on a returned candidate (not just "local") by reading
    # context.chapter / context.structural_units -- e.g. a rule
    # detecting "For purposes of this part" stamps
    # scope="part", scope_value=<value from context.structural_units>.
```

**v2 worked example** (v1's is now stale — same rule, new signature):

```python
# backend/app/definition_links/rules/us_scoped_inline.py
import re
from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext, ScopeTriggerRule, register_scope_trigger_rule,
)

_TRIGGER_RE = re.compile(
    r'As used in this section,\s*[“"]([^”"]+)[”"]\s*means\s+(.*?)(?=\.\s|$)',
    re.IGNORECASE | re.DOTALL,
)

def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    return [
        DefinitionCandidate(
            terms=(m.group(1).strip(),), definition_text=m.group(2).strip(),
            scope="local", source_article_number=ctx.article_number,
        )
        for m in _TRIGGER_RE.finditer(article_body)
    ]

register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("US-*",), extract=_extract))
```

### 3. `EntrySplitterRule` moves to the union side (manager ruling M1)

Corrects v1 §2's consumption contract, which grouped `EntrySplitterRule`
with the first-wins detection kinds. It is now a union kind, same as
`ScopeTriggerRule`/`TermClauseRule`: ALL matching registered splitters
run, ALL their blocks are kept (a section body can legitimately mix two
marker conventions at once — recon §2 families 3 and 5 overlap in real
rows), deduped downstream by the existing `(article_id, sorted(terms))`
key. `HeadingRule` (boolean, first-positive-wins is already OR/union —
unchanged) and `BodyPreambleRule` (single-valued, first-non-None-wins,
deterministic filename-sort order — unchanged in mechanism, ungated
below) are the only remaining first-wins kinds.

### 4. `BodyPreambleRule` dispatch is ungated (manager ruling M6)

v1's `derive_heading_from_body` tried the legacy CA/IL/GA logic only
when `_is_placeholder_heading(heading)` was true, then returned. v2:
after the legacy branch (unchanged, still gated on
`_is_placeholder_heading` — this is what keeps CA/IL/GA and the 7
already-working states byte-identical), registered `BodyPreambleRule`s
are ALWAYS tried next if nothing was found yet — regardless of what
`_is_placeholder_heading` returned. Precision guard (stated so panels
can measure against it, not asserted as proof): baseline-first ordering
is unchanged, so no currently-working row's behavior can change; new
exposure is confined to rows where baseline finds NOTHING today, so any
new false-positive risk is additive-only, never a regression of a
working state. A panel shipping a `BodyPreambleRule` measures its own
corpus-wide FP exposure on that confined population and escalates with
data if material (director's standing policy) — this seam does not
pre-judge that measurement.

**Director-confirmed at program level (D-PREAMBLE-ALL): ungating stands,
with a scope mandate — ALL states researched AND coded (owned by the
preamble panel, not core).** Stated explicitly so this precision-guard
paragraph is never mistakable for a gating condition later: escalating a
measured FP number is NOT a request to re-gate `BodyPreambleRule`
dispatch behind `_is_placeholder_heading` — gating is off the table.
The resolution to a material exposure number is narrower/more precise
`BodyPreambleRule`s (or additional `HeadingRule`/`EntrySplitterRule`
coverage) achieving full per-state inventory, never suppressing dispatch
for states baseline already fails on. If a future reader is tempted to
read "escalate if material" as "gate if material" — it does not say
that and must not be implemented that way.

### 5. Rule-module authority is bounded (manager ruling M7)

Rule modules may ONLY affect the 5 registered kinds (heading,
body_preamble, entry_splitter, scope_trigger, term_clause). They CANNOT
override `find_term_uses` or `find_citations` — both stay fixed
`JurisdictionProfile`-CLASS methods (`USProfile`'s own English
word-boundary matcher / citation grammar), never a rule kind. A
jurisdiction needing different term-matching or citation grammar (e.g. a
future Spanish-language `PRProfile`) is a NEW PROFILE CLASS problem, not
a rule-module problem — a rule module cannot solve it, and a panel that
hits this wall should escalate for a new profile class rather than try
to route around it via a rule. PR ships as `USProfile`-hosted rule
modules for now (reversible: profiles resolve by code, rules register by
code-match, so a later dedicated `PRProfile` can inherit the same
registered rules unchanged) — this is the stated escape hatch.

### 6. Two new core-sprint items (manager ruling M8) — not family-panel work

- **M8(a):** `sections._ARTICLE_MARKER_RE` requires the literal `@ N.`
  shape; a bare `@` (no number/period) parses to zero articles for that
  whole document, silently dropping any definitions inside — 124/6,133
  IL laws affected, 12 with unambiguous definitions (measured by the IL
  panel on a named file). Core-sprint RED tests + fix, not a family item.
- **M8(b):** `us_profile.find_term_uses` is case-sensitive; real rows
  re-mention a capitalized defined term in lowercase later in the same
  law (`STATE_GA_T7_C8_S7-8-1` defines "Access area",
  `STATE_GA_T7_C8_S7-8-3` uses "access area", silently unlinked). Two
  binding constraints on the fix: (i) proof that case-folding does not
  disturb Hebrew is the FULL existing IL suite passing UNCHANGED — not
  an argument that Hebrew is caseless; (ii) case-insensitive matching is
  itself a recall/precision trade (a defined term that is also an
  ordinary lowercase word over-links) — measure the exposure, escalate
  with data. **Planner's measurement status, recorded honestly:** this
  worktree has no local copy of the real US/IL corpus (checked — not
  present under this worktree or any path this sprint is authorized to
  touch), so a corpus-wide FP-exposure count cannot be produced from
  here. The RED test below is built from the exact term/act-id facts
  already given in this ruling (not fabricated), and the fix is scoped
  narrowly (word-boundary literal-term case-fold only, no fuzzy
  matching) to keep plausible exposure low — but the actual corpus-wide
  measurement this ruling asks for needs a panel/session with corpus
  access. Flagged, not silently skipped.


---

## Seam spec v2.1 (published) — folds in M9, M10, M11, pointer definitions

Supersedes v2 §1's AK-range handling; adds three new pieces. Everything
else in v1/v2 not mentioned here is unchanged.

### 1. Enumerated / ranged scope units (manager ruling M9) — REVERSES v2's AK deferral

**v2's "AK ranges default to `law-wide`" is withdrawn — that was wrong,
not just conservative.** A law-wide stamp on a chapter-5-9-scoped
definition doesn't protect recall, it manufactures false
`USES_DEFINITION` assertions across every OTHER chapter of the law. A
silent broadening fallback is a false-positive generator, never an
acceptable default.

**Mechanism (M9, adopted as designed): `scope_value` (and the two legacy
dedicated fields `source_chapter`/`source_article_number`) may hold
EITHER a single string OR a tuple of strings, same kind, no new kind
needed.** SD's `"when used in § 3-14-3 or 3-14-4"` is
`scope="local", source_article_number=("3-14-3", "3-14-4")`. AK's
chapter range is `scope="chapter", source_chapter=("5","6","7","8","9")`
(a rule expands the range to its member values — a range is a compact
INPUT notation, not a new stored shape). `_in_scope`'s comparison
becomes: `expected in (actual if isinstance(actual, tuple) else (actual,))`
— for the ordinary scalar case this is exactly today's `==` check,
unchanged; the tuple case is purely additive. No new `register_scope_unit_kind`
call is needed for enumeration itself — "an enumerated scope inherits
the rank of its members" is automatic, because it's the SAME kind
string, just a wider value.

**Consequence for M4(c) (a `local` def and a set-valued `local` def
covering the same article are rank-EQUAL):** this is not a new case —
it is the ALREADY-PUBLISHED same-rank-tie resolution (§2 below), not a
second mechanism. No new escalation needed for this specific
consequence; it falls out of the M10 resolution automatically.

### 2. M4(c) ties — kept as behavior, reclassified as a named open conflict class (manager ruling M10)

**Correction accepted, recorded verbatim so the reasoning going forward
is right:** v2 justified "both survive" as "not a recall/precision
trade" because each surviving scope claim is independently true. That
framing was wrong. The assertion is `USES_DEFINITION` pointing at ONE
`Definition` row; a mention has exactly one meaning. When two
same-rank, different-kind (or, per M9, two same-rank enumerated)
definitions both survive, **one of the resulting assertions is factually
wrong — we just don't know which.** That is a real false-positive rate,
not a neutral duplicate.

**Behavior is UNCHANGED — both still survive, both still get an
assertion** — this is still the correct zero-miss-safe default under the
director's absolute bar (dropping either risks the real miss; keeping
both risks a bounded, known-shape false positive). What changes is how
it's recorded:

- This is now a **named, open conflict class** under the director's
  standing escalate-with-data policy, not a settled design decision.
- **Obligation (a), Planner/Stage B:** a RED→pinned test asserting the
  tie behavior explicitly (both `Definition` rows get a
  `USES_DEFINITION` assertion when scopes tie at the minimum rank) — so
  the behavior is deliberate and regression-guarded, not emergent. See
  `## Stale-pin sweep` / test list below.
- **Obligation (b), QA-time, NOT this Planner's Stage B work:** measure
  how often an equal-rank, different-kind (or enumerated-overlap) tie
  actually occurs on the full corpus once family panels' rules exist,
  and escalate with that number if material. Recorded here as a named
  gate for program-close integration QA (alongside M2's `BodyPreambleRule`
  shadowing gate) — not measured by this Planner, per the instruction not
  to spend Stage B time on it.

### 3. `StructuralUnitRule` — the missing rule kind that populates `structural_units` (manager ruling M11)

**Gap conceded exactly as raised:** v2 gave family panels a way to
register a NEW scope-unit KIND (`register_scope_unit_kind`) and a way to
STAMP a scope onto a definition (`RuleContext`/`ScopeTriggerRule`), but
no way to PUT the corresponding unit onto the owning ARTICLE — so
`part`/`subchapter`/`siman`/`chelek` enforcement had no data to compare
against. Fixed with a 6th rule kind:

```python
@dataclass(frozen=True)
class StructuralUnitRule:
    jurisdiction_codes: tuple[str, ...]
    derive: Callable[[StructuralContext], tuple[ScopeUnit, ...]]

@dataclass(frozen=True)
class StructuralContext:
    article_number: str
    heading_breadcrumbs: tuple[tuple[int, str], ...]
    # (depth, heading_text) pairs -- see input-availability note below.
```

`register_structural_unit_rule(rule: StructuralUnitRule) -> None` in
`rules/registry.py`, same import-time registration mechanism as the
other 5 kinds. Consumption: UNION across all matching rules (additive,
unlike `USES_DEFINITION` attribution — a document legitimately nests
inside a part AND a chapter simultaneously, both belong in the same
article's `structural_units` tuple). Core still owns stamping
`ScopeUnit("chapter", article.chapter)` itself, unconditionally, as
today; registered rules ADD to that set, never replace it.

**Input availability — verified for IL, NOT verified for US, said so
rather than guessed (per the explicit instruction):**

- **IL/wiki-sourced:** VERIFIED reachable. `sections.py`'s
  `_HEADING_BREAK_RE` already matches BOTH `==...==` (2-equals, chapter
  — currently captured into `.chapter`) AND `===...===` (3-equals,
  siman — currently matched, then DISCARDED: `parse_articles`'s
  `break_match.group(2)` is only stored when
  `len(break_match.group(1)) == 2`). Core's own, one-time,
  ONE-PLACE change: `sections.parse_articles` additionally accumulates
  EVERY heading-break line it already scans (any `=` depth, not just 2)
  into a generic `heading_breadcrumbs: tuple[tuple[int,str],...]` field
  on `Article`/`MatcherArticle` (default `()`, so every existing
  `Article(...)` construction site is unaffected — same additive-field
  safety as `structural_units`). This is a SINGLE shared-module edit,
  made ONCE by core, not per-kind — after it lands, an IL `siman`/`chelek`
  `StructuralUnitRule` reads `heading_breadcrumbs` for depth-3/whatever
  entries and never needs to touch `sections.py` again.
- **US/parquet-sourced: NOT verified this session.** Whether
  `ingest_us_statutes.py`'s parquet columns carry a usable part/
  subchapter/title breadcrumb per row was not inspected — flagging this
  explicitly rather than assuming it works, per the instruction. If the
  raw signal isn't in the ingested columns at all, `StructuralUnitRule`
  for `part`/`subchapter` cannot be satisfied from `run_definition_linking`
  alone and becomes an ingest-contract question for the sub-manager to
  route (a schema question for `ingest_us_statutes.py`, outside this
  sprint's module set) — **not resolved here, explicitly surfaced in the
  Stage B report instead of guessed at.**

### 4. Pointer definitions (director ruling, narrowed) — no persisted pointer field, ever

**Final design per the director's clarification — supersedes anything in
the earlier message that implied a stored pointer flag/column:**

- **No schema change.** No `is_pointer` column, no pointer-target column
  on `Definition`, no new `Assertion` field. A transient
  in-memory-only carrier on `DefinitionCandidate` is fine if the
  emission step needs one, but the preferred path needs none: Stage 4
  (`pipeline.py`'s existing loop, unconditionally re-running
  `profile.detect_cross_law_derivations`/`find_citations`-family logic
  over every candidate's OWN `definition_text`) already re-derives the
  target from the definition's stored text — a pointer-idiom candidate
  (`"has the meaning given [to] that term in <citation>"`) is captured
  as an ORDINARY `DefinitionCandidate` by whatever extraction rule
  recognizes the idiom (already-registered `_TRIGGER_PHRASES`
  machinery — `"has the meaning specified in"`/`"as defined in"` are
  already recognized; a family panel adds phrase variants the same way
  any other rule adds coverage), and Stage 4 finds the target itself,
  same as it already does for ordinary cross-law derivations. No new
  field is needed to carry a target from rule to pipeline.
- **Internal (same-law) targets — resolved through EXISTING machinery,
  no new assertion type, verified before deciding (per the explicit
  instruction to check first):** `Assertion.object_entity_type` is a
  free-text `String(255)` column (`backend/app/models/assertion.py:42`),
  already varying by assertion type across this codebase (`"Article"`
  for `USES_DEFINITION`'s subject, `"Document"` for `DERIVES_FROM_LAW`'s
  object today) — NOT a closed enum. The frontend renders
  `object_entity`/`subject_entity` generically via `EntityChip` with no
  assertion-type-specific branching found (`AssertionDetailPage.tsx:328`,
  `SuggestAssertionPage.tsx`'s type list is explicitly "guidance only —
  the backend remains the enforcement point"). Therefore: an internal
  pointer target reuses `DERIVES_FROM_LAW` UNCHANGED as an assertion
  type, with `object_entity_type="Article"` / `object_entity_id=<the
  target Article's row id, resolved the same way Stage 3 already
  resolves same-document article numbers>` instead of `"Document"` /
  a law id. **Not a new assertion type, not a new entity-type
  vocabulary concept, no frontend work required** — verified, not
  assumed, so this does not need the escalation the instruction offered
  as an out.
- **`_BESAIF_RE` (Hebrew, derivation.py:39) / `_SAME_LAW_RE` (US,
  us_profile.py:452) stay EXACTLY as they are for ordinary substantive
  definitions** that merely mention a same-law section in passing — that
  is correctly Stage-3/mention territory, unaffected by this. The NEW
  behavior applies ONLY when the trigger phrase's match consumes the
  candidate's ENTIRE definition_text (a whole-definition pointer, not an
  incidental same-law aside inside a longer substantive definition) —
  redirect to an Article-targeted `DERIVES_FROM_LAW` edge in that case
  instead of excluding it.
- **Pointer-ness has no flag anywhere. Consumers determine it by
  checking whether a `DERIVES_FROM_LAW` assertion exists with
  `subject_entity_id` equal to the `Definition`'s own id.** State this
  explicitly to the 4 panels consuming it so none of them invent their
  own marker field.
- **Correctly-empty reconciliation (markers panel):** pointer-idiom
  candidate extraction is ordinary candidate extraction, run
  independently of any "this section has no defining content, correctly
  empty" classifier a family panel builds. A non-empty pointer-idiom
  extraction result OVERRIDES a "correctly empty" verdict for that
  section — under the absolute zero-miss bar this is the only safe
  ordering. The markers panel's classifier must be written to check for
  a pointer-idiom match FIRST (or treat one as a veto), not the reverse.


---

## Seam spec v2.2 (published) — unified unit-path model; ONE item escalated, not decided

Director requirement (relayed): connections must be addressable at
sub-article granularity, recursively nested, and the SAME unit machinery
must serve scope containment and connection addressing. This section
unifies v2/v2.1's two half-machineries (`Subsection(label,start,end)` and
`ScopeUnit`/`structural_units`) into one. Per-jurisdiction "main unit"
VALUES are explicitly NOT guessed here — the mechanism is designed, the
data is left for the incoming 4-system research dossier.

### 1. `UnitPath` — one ordered path replaces `ScopeUnit` + `Subsection`

```python
@dataclass(frozen=True)
class UnitStep:
    kind: str    # "part" | "chapter" | "article" | "subsection" | "siman" | ...
                 # -- a LABEL for provenance/display only, see §3: kind no
                 # longer drives ranking.
    value: str   # concrete identifier at that step, e.g. "II", "5", "a"

UnitPath = tuple[UnitStep, ...]   # root-to-leaf, ordered. () means "law-wide".
```

Replaces `ScopeUnit` (v2 M4) and `Subsection` (v1) as separate types —
neither is a distinct concept anymore, both were "one step (or a
contiguous span, for the leaf) in a path from the law's root down to a
position." `Article.structural_units`/`.subsections` (v1/v2.1 fields) are
replaced by ONE field: `Article.unit_path: UnitPath` — the path from the
law's root down to (and including) this article's own step; a mention
found INSIDE the article additionally extends that path with however
many further steps (subsection, sub-subsection, ... — arbitrary depth,
not capped at one level) the position falls under, computed the same
"fresh every call, never persisted as raw offsets" way `Subsection` was
in v1 (only step `.value` LABELS are ever persisted, never char offsets).

### 2. Scope containment = prefix matching (replaces `_in_scope`'s branches)

**One predicate, not four special-cased branches:** a definition scoped
to `definition_path: UnitPath` governs a mention at `mention_path:
UnitPath` iff `mention_path[: len(definition_path)] == definition_path`
— `definition_path` is a PREFIX of `mention_path`. `law-wide` (`()`) is
the empty path — a prefix of everything, for free, no special case.
`"chapter"`/`"local"`/`"subsection"` (v1/v2) all become ordinary paths of
length 1/2/3+ under this one rule; nothing about today's IL behavior
changes VALUE-wise (a `"local"`-equivalent definition's path is still
exactly `[article:N]`), only the COMPARISON mechanism is now generic.

**M9 (enumerated/ranged scopes) under this model:** a definition's scope
is a SET of `UnitPath`s, not one — governs a mention iff ANY member path
is a prefix of `mention_path`. SD's `{3-14-3, 3-14-4}` is
`{(article:3-14-3,), (article:3-14-4,)}`; AK's chapter range is
`{(chapter:5,), (chapter:6,), ..., (chapter:9,)}`. Same mechanism as v2.1,
now expressed as paths instead of tuple-valued legacy fields.

### 3. "Narrowest governs" = longest matching prefix (mostly replaces M4(b)'s rank registry)

**Rank is now path DEPTH** (`len(matched_path)`), compared only ever
WITHIN one document's own hierarchy (this predicate is never evaluated
across two different laws, so no cross-jurisdiction rank calibration
question exists — a real simplification the message's lean predicted,
verified against how `_in_scope`/`link_articles_to_definitions` are
actually called: always per-document, per M9/M10's existing design).
`register_scope_unit_kind(kind, *, rank=...)` (v2 M4(b)) is WITHDRAWN —
`kind` strings are now provenance/display labels only, never inputs to a
ranking decision. `rank_for(kind)` is replaced by `len(path)` — no
registration call needed for a new kind's ranking at all (a strictly
larger simplification than "register a rank"; a family panel introducing
a new structural level just emits a longer path, and it is automatically
narrower).

**M10's tie class survives, now precisely stated as EQUAL-LENGTH,
DIFFERENT-CONTENT matching prefixes** (e.g. two length-1 paths,
`(part:II,)` and `(chapter:3,)`, both matching the same mention, from two
DIFFERENT definitions) — still resolved as "both survive, both get an
assertion," still the SAME named open conflict class under the director's
escalate-with-data policy (M10's obligations (a)/(b) are UNCHANGED by
this unification — the mechanism producing the tie changed, the
resolution and its recorded status did not).

### 4. `StructuralUnitRule` becomes the one "derive this article's `unit_path`" seam (replaces M11's split machinery)

```python
@dataclass(frozen=True)
class StructuralUnitRule:
    jurisdiction_codes: tuple[str, ...]
    derive: Callable[[StructuralContext], UnitPath]
    # Returns the FULL path down to (and including) this article's own
    # step -- e.g. IL: (chapter:"פרק ו", siman:"ב", article:"34"). Below-
    # article steps (subsection and deeper) are derived the SAME way, by
    # the SAME rule kind, called again with the article's OWN body text
    # to extend the path further per position -- one mechanism, both
    # above and below the article, exactly as required.
```

IL input-availability finding from v2.1 §3 stands UNCHANGED (verified:
`sections.py` already scans `===`-depth headings, just discards anything
past 2 equals-signs today — one core-owned, additive capture of ALL
depths makes the full path derivable). US input-availability: still
UNVERIFIED this session, still explicitly flagged, not guessed.

### 5. Per-jurisdiction "main unit" — mechanism only, values intentionally NOT set here

```python
class JurisdictionProfile(Protocol):
    ...
    main_unit_kind: str   # e.g. "article" -- the level at which an
                           # ordinary, otherwise-unscoped mention is
                           # addressed by default. A DECLARED PARAMETER,
                           # not derived from data in this sprint.
```

**Deliberately NOT populated with a researched value here.** Today's
byte-identical-for-IL guarantee (C5) is satisfied by setting
`HebrewProfile.main_unit_kind = "article"` (matches TODAY's `"local"`
granularity exactly, zero behavior change) — this is the ALREADY-PROVEN
value, not a guess about IL's "true" main unit; if the incoming research
dossier says otherwise for some other purpose, that is a data update to
this one field, not a mechanism change. `USProfile.main_unit_kind` is
LEFT UNSET/TBD pending the dossier — explicitly not guessed, per the
instruction.

### 6. ESCALATION — held, not decided: does a sub-article `USES_DEFINITION` mention anchor need a new persisted entity?

**This is the one fork this Planner will NOT decide unilaterally**, per
the message's own explicit instruction ("Do NOT build a new persisted
entity type on your own authority... escalate with the design in hand").

Today: `_create_assertion(assertion_type="USES_DEFINITION",
subject_entity_type="Article", subject_entity_id=using_article.id, ...)`
(`pipeline.py`) — the assertion's SUBJECT is the whole `Article` row.
Recursive sub-article addressing means a mention's TRUE location is
`(using_article.id, mention_unit_path)` — finer than the row itself.
Two options, both fully designed, neither built:

- **Option A — text/metadata carry, no schema change.** Keep
  `subject_entity_type="Article"` / `subject_entity_id=using_article.id`
  exactly as today (zero schema change, zero frontend impact — proven
  safe the same way the pointer-definition reuse was verified in v2.1
  §4). Encode the mention's unit path into the assertion's `proposition`
  text (already free-text) and/or a new but ADDITIVE, nullable text
  column on `Assertion` (e.g. `subject_unit_path: str | None`, a
  serialized path -- same migration precedent as every other additive
  column this sprint uses). A consumer that cares about sub-article
  precision reads that column; one that doesn't is completely
  unaffected. **My lean: this option**, because it is the ONLY one that
  provably stays inside "backend-only, gates C1-C5" without a new
  entity/table, and every other addition this sprint has made has held
  to exactly that additive-column discipline.
- **Option B — a new persisted sub-article entity** (e.g. a `Unit`/
  `Subsection` table, FK'd to `Article`, one row per addressable
  sub-article node), with `subject_entity_type="Unit"` /
  `subject_entity_id=<that row's id>`. Strictly more queryable/
  first-class (a UI could deep-link to "article 5(a)(2)" directly), but:
  a NEW table is a bigger schema commitment than this sprint's other
  additive columns; it very plausibly needs frontend work to be useful
  at all (an entity type the UI has never rendered); and it requires
  MATERIALIZING every mention's sub-article position as its OWN row at
  pipeline-run time, a new write-path shape, not merely a new column on
  an existing write.

**Escalating rather than choosing.** Both are internally consistent;
Option A is cheaper and provably in-scope, Option B is more capable and
plausibly out-of-scope for a backend-only sprint gated C1-C5. Holding
Stage B's live-path RED tests for sub-article `USES_DEFINITION`
ANCHORING specifically (not scope containment, which is unblocked and
proceeds under §§1-3 above) until this is answered — proceeding with
every other Stage B item in the meantime (M8(a)/M8(b), rule registry
existence, C2/C3 profile methods, C4 auto-discovery, scope-containment
prefix-matching tests) since none of those depend on the answer.


---

## Seam spec v2.3 (published) — find_citations rule kind (M12), both defects verified

Verified myself before writing anything (per instruction), `backend/.venv/bin/python`:

```
find_citations("as provided in Section 552.003 of this code") == ["Section 552"]   # wrong-target truncation, reproduced
find_citations("has the meaning given that term in ORS 153.005") == []             # state-code shape invisible, reproduced
```

Read (read-only, never checked out over this work) the multiterm panel's
existing pins at `claude/defs-us-multiterm@f1011f0`,
`backend/tests/unit/test_definition_links_e1_pointer_reference_capture.py`.
Matching their EXACT expected values below rather than growing a second,
possibly-divergent set — one fix should turn both green:

- `find_citations('“Enforcement officer”...ORS 153.005 (Definitions) .')
  == ["ORS 153.005"]` — their
  `test_or_enforcement_officer_state_code_citation_is_invisible_today`.
- `find_citations('"Governmental body"...Section 552.003.')
  == ["Section 552.003"]` (untruncated) — their
  `test_tx_governmental_body_section_citation_is_truncated_to_a_wrong_target`.
- Same shape for `Section 2001.003` (six-term TX parent clause) — their
  `test_tx_parent_clause_2001_003_citation_is_truncated_to_a_wrong_target`.
- **Third defect their file ALSO pins, not previously in this spec**:
  `_TRIGGER_PHRASES` (us_profile.py:443) is missing the three real idioms
  `"has the meaning given that term in"` / `"has the meaning assigned by"`
  / `"have the meanings assigned by"` — needed for
  `detect_cross_law_derivations` to fire at all on these rows (their
  `test_*_reference_edge_needs_both_*_and_iii_fixed`). This is a literal
  phrase-list addition to the EXISTING `_TRIGGER_PHRASES` tuple, not a new
  rule kind (M12 below is scoped to `find_citations`/`_CITATION_PATTERNS`
  specifically, per the instruction) — core fixes this alongside the other
  two as one baseline change; noted here so QA checks all three, not two.

### `find_citations` becomes rule-extensible (manager ruling M12 — reverses part of M7)

**M7's PR-profile paragraph is corrected, not left contradictory:**
~~"rule modules cannot override `find_term_uses`/`find_citations`... a
jurisdiction needing different citation grammar is a profile-class
problem, not a rule problem"~~ — **superseded for `find_citations` only**
(`find_term_uses` is UNCHANGED, still profile-class-only — no citation-
grammar-shaped defect has been found in it). `find_citations` is now a
32-jurisdiction concern (7,610 pointer definitions route through it) and
belongs behind the SAME shared-edit-avoidance mechanism as every other
per-jurisdiction convention, not hardcoded per-state inside `us_profile.py`
(the exact P-R1/M11 argument). **This also resolves the M7 limitation
raised for PR** — a Spanish citation grammar is now an ordinary registered
rule, not a wall requiring a new profile class. PR panel: the wall named
in M7 moved; a `CitationRule` (below) is your path now.

```python
@dataclass(frozen=True)
class CitationRule:
    jurisdiction_codes: tuple[str, ...]
    find: Callable[[str], list[str]]   # text -> matched citation substrings

def register_citation_rule(rule: CitationRule) -> None: ...
def citation_rules_for(code: str) -> list[CitationRule]: ...
```

**Consumption — baseline-first, then union (consistent with M1/M9's
union-side kinds):** `profile.find_citations(text)` runs its OWN baseline
`_CITATION_PATTERNS` first (fixed, see below), THEN unions in every
matching registered `CitationRule`'s output, same overlap-claiming
discipline `find_citations` already applies internally (a rule's match
overlapping an already-claimed span is discarded, not double-counted).
`HebrewProfile.find_citations` stays `[]` unless an IL rule is registered
— unchanged, C5-safe.

**Core fixes both verified baseline defects directly in
`_CITATION_PATTERNS`/`_SECTION_WORD_RE`, not via a rule module** (per the
instruction — these are bugs in the shared regex, not missing
jurisdiction-specific grammar): (1) decimal section numbers must not
truncate — `Section 552.003` must resolve to `Section 552.003`, whole,
verified via an EQUALITY assertion (not `in`) so a silent wrong-target
regression is caught, not just a miss; (2) a generic `<CODE> <n>.<n>`
state-code shape (covering `ORS 153.005` and similarly-shaped codes
out of the box) is added to baseline, WITH the rule kind above still
available for genuinely idiosyncratic grammars baseline can't
generalize to. Both are additive to `_CITATION_PATTERNS`'s existing
three patterns — no existing pattern's behavior changes (C5).

**RED tests:** authored in core-owned files only (`test_definition_links_
us_profile.py`, this sprint's own — see `## Stale-pin sweep` below for the
exact list), matching the multiterm panel's expected values verbatim so
one fix turns both sets green. Core's tests additionally cover what
theirs do not: `HebrewProfile.find_citations` stays `[]` (IL unaffected),
the `CitationRule`/registry mechanism itself, and the internal
same-law-target pointer-emission path (v2.1 §4).

---

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

## Seam spec v2.4 (published) — dossier-validated, D-ANCHOR final, model tightened

Research dossier read (`git show origin/main:docs/sprint/programs/2026-08-04-law-system-units.md`
@ `e3e7633`, read-only — main NOT merged into this branch, per instruction;
the program manager owns that merge). D-ANCHOR is now the director's FINAL
ruling (not provisional): row-level anchor + a structured sub-article
path, arbitrary depth; promoting sub-article units to first-class graph
entities is an explicit LATER-phase possibility, not this program.

### 1. One correction FROM the dossier: `UnitPath` is BELOW-article only

The dossier's own recommended model (§3): `article_row_id + ordered_unit_path[]`,
where the path is **only** the marker sequence BELOW the article
(`["a","1","A","i"]`-shaped) — container levels ABOVE the article
(חלק/פרק/סימן; US state title/division/chapter/part; US federal
title/chapter/subchapter) are **metadata on the article row, not schema-
level path components**, because they're sparse/inconsistent (Israel),
or vary 2-6 levels per state with no common template (US), and mixing
them into the same ordered array as sub-article marks would conflate two
structurally different things.

**Correction to v2.2 §1/§4**: `UnitPath`/`resolve_unit_path` is
re-scoped to the sub-article marker sequence ONLY. Chapter/part/siman-
level scoping keeps using v2's existing mechanism unchanged (the
`"chapter"` kind's dedicated `source_chapter` field; any other above-
article kind's generic `scope_value` field) — these were NEVER meant to
merge into the sub-article path, and the dossier's real, measured data
confirms keeping them separate is the right call, not merely convenient.
`resolve_unit_path(article, char_offset=None)` returns `()` (the article
itself, no sub-article marks) when called with no offset; given a
`char_offset`, it returns the marker path AT that position (e.g. `("a",)`,
`("a","1")`) — never chapter/part information, which callers read off
the article's own metadata fields instead.

### 2. Invariant, dossier-confirmed and pinned as a test: no bare sub-unit without its parent

**Convergent finding across all 4 systems (dossier §2): no system ever
cites a bare sub-unit without its parent article/section.** This
directly validates the row-anchor + path model — stated here as the
empirical basis for the design, not a preference. Pinned as an explicit
invariant test (see report): a `UnitPath` is only ever meaningful
relative to the article row it is resolved against; nothing in this
seam ever represents a sub-unit path without its rooting article.

### 3. Depth is NOT capped at 2-3 — the federal 8-level ladder is real

US federal citations run a real, at-scale, 8-level parenthetical ladder
(`(a)>(1)>(A)>(i)>(I)>(aa)>(AA)`, confirmed down to `(AA)`, 443 real
instances; 35.4% of all federal section citations go below section at
all). **Nothing in `UnitPath`/`resolve_unit_path`/the matcher's prefix-
matching comparison may hard-code a depth limit of 2 or 3** — a model
that quietly assumes shallow nesting passes every IL/PR-shaped test and
silently breaks on federal. Pinned as an explicit deep-nesting test (see
report) exercising genuinely 4+ level nesting, not just 1-2.

### 4. `main_unit_kind` populated from the dossier — not invented

Per-system main unit, taken verbatim from dossier §1 (not extrapolated
beyond what it states):

| Profile | `main_unit_kind` | Dossier basis |
|---|---|---|
| `HebrewProfile` (IL) | `"local"` (סעיף/article) | "Main unit: סעיף (article)" — matches TODAY's `"local"` granularity exactly, C5-safe, zero behavior change |
| `USProfile` (US-* incl. `US-FED`) | `"local"` (Section) | "Main unit: Section (formally, every state)" / federal "Section nominally" — the FORMAL main unit is Section for every US code including federal; the dossier's own de-facto-subsection nuance for coarse states/sections (GA/UT/OH/NC, huge federal definitions sections) is a DISTRIBUTION fact about where real citations land, not a different declared main unit — `main_unit_kind` stays `"local"`/Section for all US codes; deep sub-article paths are still fully addressable via `resolve_unit_path`, they just aren't the DECLARED default |
| PR (hosted under `USProfile` per M7, pending a dedicated `PRProfile`) | `"local"` (Artículo/Sección — the row itself) | "Artículo/Sección is the row/citable unit itself; no separate container rows" — PR's main unit IS the row, matching `"local"`'s existing meaning (the owning article/row) precisely |

No value was invented for a system the dossier doesn't cover; nothing
beyond §1's table was used.
