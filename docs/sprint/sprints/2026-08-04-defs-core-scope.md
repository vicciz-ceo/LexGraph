---
id: "2026-08-04-defs-core-scope"
status: planning
current_role: planner
branch: claude/defs-core-scope
worktree: /Users/nerya/LexGraph-wt/defs-core-scope
locked_by: "claude-code:planner"
locked_at: "2026-08-04T00:00:00Z"
last_agent: "claude-code:sprint-manager"
last_updated: "2026-08-04"
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

_Planner defines items._

## Dev Complete

_None._

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
