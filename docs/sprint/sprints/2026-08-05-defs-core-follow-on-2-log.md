# Sprint log: core follow-on 2 — Planner (G5, G6)

Worktree `/Users/nerya/LexGraph-wt/defs-core-follow-on-2-plan3`, branch
`claude/defs-core-follow-on-2-plan3`, forked from the sprint branch @
`8c49498`. This log covers gates **G5** (`RuleContext.unit_path`) and
**G6** (scope-VALUE seam) only — G1-G4/G7 are other Planners' write-set.

Role boundary held: this Planner wrote tests, the seam-doc v2.8 append,
and this item-definition log. No production `.py` file under
`backend/app/` was edited — a Developer implements against the items
below and the seam doc.

---

## G5 — RuleContext.unit_path

### Verification (byte-read, not assumed)

Both hardcode sites confirmed exactly as briefed:
`backend/app/definition_links/profiles.py:256`
(`HebrewProfile.extract_local_scope_definitions`) and
`backend/app/definition_links/us_profile.py:1421`
(`USProfile.extract_local_scope_definitions`) both build
`RuleContext(article_number=..., chapter=..., unit_path=())` with a
literal `()`.

**One correction to the gate's own one-line framing, reported honestly
because it changes the fix's shape (not its necessity).** `resolve_
unit_path(article, char_offset=None)` is DOCUMENTED and CONFIRMED (direct
read, `us_profile.py:1145-1211`: `if char_offset is None: return ()`) to
always return `()`. Both hardcode sites build their `RuleContext` ONCE,
BEFORE any rule has matched anything, scanning the WHOLE article body — no
match offset exists yet at that point. So a literal `unit_path=()` and a
"real" `resolve_unit_path(article, None)` are **behaviorally identical**
in this exact call shape; the hardcoded value was never factually wrong
for the field it occupies. The genuine gap: **no rule can ever obtain a
NON-empty unit path through `ctx` at all**, because a static, pre-match
field cannot represent "the path at the position where THIS rule's OWN
match lands" — only the rule itself, after it matches, knows that
position. Fixing this needs a bound RESOLVER a rule can call with its own
offset, not a differently-computed static value.

### Items

**G5-1.** `RuleContext` (`rules/registry.py`) gains one new, defaulted
field: `resolve_unit_path: Callable[[int], UnitPath] | None = None`.
Defaulted (not required) so the existing
`test_definition_links_rules_registry.py::
test_rule_context_carries_article_number_chapter_and_unit_path` (which
constructs `RuleContext(article_number=..., chapter=..., unit_path=(step,))`
with no 4th kwarg) keeps passing unchanged.
*Acceptance:* `RuleContext(article_number="1", chapter=None,
unit_path=())` still constructs with no error (regression guard); a
4-kwarg construction supplying `resolve_unit_path=` also succeeds.

**G5-2.** At both real construction sites
(`profiles.py:256`, `us_profile.py:1421`), `resolve_unit_path` is bound to
a closure over the SAME `article_body` string already passed to the rule,
calling the OWNING profile's own `resolve_unit_path` method (`self.
resolve_unit_path(<article-body-carrying stub>, char_offset)`) — zero
duplicated ladder/marker logic, plan1's G2/G4 changes to that method are
automatically picked up. `unit_path` itself is also computed via the same
bound resolver at `char_offset=None` (still legitimately `()`) instead of
a hand-typed literal, so a future change to `resolve_unit_path`'s
`None`-handling can never silently diverge from `ctx.unit_path`.
*Acceptance (RED, live path):*
`test_definition_links_g5_rule_context_unit_path.py::
test_g5_rule_context_delivers_a_real_nonempty_unit_path_to_a_scope_trigger_rule_us`
and `..._il` — a probe `ScopeTriggerRule` calls `ctx.resolve_unit_path
(offset)` at the offset of its OWN regex match and gets back a real,
non-empty `UnitPath`, equal to an independent direct call to `profile.
resolve_unit_path(article, offset)` for the same inputs.

**G5-3 (regression pin, already GREEN — included so it stays proven).**
`ctx.unit_path` for the whole-body call (no rule has matched anything
yet) stays legitimately `()` — `test_g5_rule_context_unit_path_field_
still_correctly_empty_for_the_whole_body_call` (passes today AND after
the fix; not a RED, a documented invariant).

### What must NOT change (G5)

- `resolve_unit_path`'s own internals/ladder logic — plan1's G2/G4
  territory; my tests assert EQUIVALENCE to a fresh direct call, never a
  pinned literal path value, specifically so plan1's legitimate changes
  cannot manufacture a false conflict here.
- No existing rule module's direct `resolve_unit_path` import is removed
  or deprecated — additive plumbing only (gate's own text).
- `extract_local_scope_definitions`'s own Protocol signature — unchanged.

---

## G6 — scope-VALUE seam

### Verification (byte-read, not assumed)

**Manager's "M9 already live" finding: RE-VERIFIED, HOLDS — see seam doc
v2.8 §0 for the full byte-verification** (`DefinitionCandidate`'s tuple
typing, `_value_matches`'s three call sites, `_subsection_contains_
offset`'s tuple normalization — all confirmed by direct read). This does
NOT need re-scoping.

**One correction to the brief's framing, also in v2.8 §0:** the value gap
is not confined to `"chapter"` — `determine_scope` has no `"local"` option
at all today, which blocks 4 of the 8 target rows (all KY) regardless of
the value question. The fix (below) closes both together.

**Panel evidence read directly** (not re-derived): `claude/defs-us-
headings-plan5@8cd3829` — `test_definition_links_us_heading_variants_
cycle5_scope_parse.py` (the genuinely-new heading-text parsing RED, held
by that panel, NOT rebuilt here — write-set fence respected) and
`test_definition_links_matcher_u2_scope_cycle5.py` (matcher-level
containment proof, already green, reused as evidence that containment
itself needs no new work). Full 10-row table read from `defs-us-headings-
log.md`'s 2026-08-04 "U2 gap" entry; NJ/UT re-fetched from the real
corpus this session and confirmed NOT scope-VALUE cases (see seam v2.8
§8) — this is how "10" in the manager's log becomes "8" in this gate's own
text; not a discrepancy, a documented narrowing.

### Items

**G6-1.** New `ScopeAssignment` frozen dataclass (`kind: str, value: str |
tuple[str, ...] | None`) in `rules/registry.py`.
*Acceptance:* importable as `registry.ScopeAssignment`; equality by value
(frozen dataclass default).

**G6-2.** `ScopeKindRule` gains one new, defaulted field: `detect_value:
Callable[[str], ScopeAssignment | tuple[ScopeAssignment, ...] | None] |
None = None`. Verified zero real consumers exist to break (`git grep
register_scope_kind_rule` across every remote branch's `rules/*.py`
matches only `registry.py` itself).
*Acceptance:* every existing `ScopeKindRule(jurisdiction_codes=...,
detect=...)` 2-kwarg construction across the existing suite
(`test_definition_links_rule_dispatch_scope_kind.py`,
`test_definition_links_rule_dispatch.py`) keeps passing unchanged.

**G6-3.** New `JurisdictionProfile.determine_scope_assignments(self,
body_text, *, scope, article_number, chapter) -> tuple[ScopeAssignment,
...]` on `USProfile`, `HebrewProfile`, and the `Protocol`. Dispatch
replays `determine_scope`'s own baseline-first/first-non-None-wins order
exactly (see seam v2.8 §3 for the precise algorithm) so the "winning
rule" can never drift from what `determine_scope` itself picked. Default
value for a rule that wins the kind but declines the value (or when
nothing registered fires): the article's own narrow, self-referential
identity (`chapter` for `"chapter"`, `article_number` for `"local"`,
`None` otherwise) — never a broadening default.
*Acceptance (RED, dispatch-proof, P-R8-shaped):*
`test_definition_links_g6_scope_value_seam.py`, 5 tests:
  - `test_g6_determine_scope_assignments_default_matches_todays_chapter_stamping_us`
    — baseline-only default.
  - `test_g6_scope_kind_rule_detect_value_overrides_the_chapter_value_with_an_enumerated_tuple_us`
    — AK-shaped 9-member chapter tuple override.
  - `test_g6_scope_kind_rule_detect_value_overrides_the_local_value_with_an_enumerated_tuple_il`
    — KY-shaped 2-member article tuple override, IL side (mechanism
    parity).
  - `test_g6_scope_kind_rule_declining_a_value_falls_back_to_the_narrow_default_never_broadens`
    — a rule wins the kind, declines the value, default is narrow not
    broad.
  - `test_g6_scope_kind_rule_can_supply_two_coequal_assignments_tn_dual_scope_shaped`
    — TN-shaped multi-assignment fan-out data shape.

**G6-4.** `pipeline.py`'s Definitions-SECTION stamping loop calls
`profile.determine_scope_assignments(...)` and fans out one
`DefinitionCandidate` copy per returned `ScopeAssignment`, routing
`.value` to `source_chapter`/`source_article_number`/`scope_value` by
`.kind` (existing `_in_scope` dispatch, unchanged). See seam v2.8 §4.
*Acceptance (RED, ONE live-path proof, real corpus words):*
`backend/tests/integration/test_definition_links_g6_scope_value_seam_live.py`:
  - `test_g6_ky_156_106_shaped_section_before_the_fix_wrongly_links_an_uninvolved_ky_article`
    — POSITIVE CONTROL (P-R10), **passes today** on unmodified `main`,
    documents the live bug (today's `"law-wide"` default over-links).
  - `test_g6_ky_156_106_shaped_section_after_the_fix_links_only_the_two_named_sections`
    — RED today (`ImportError: ScopeAssignment`); once G6-1..G6-4 land,
    must produce a `USES_DEFINITION` assertion linking KY article
    `161.605` and must NOT link the uninvolved `139.486`-shaped article,
    through the real `run_definition_linking` entry point.

### Row-by-row: the 8 U2 rows

Full table with per-row reasoning is in the seam doc, **v2.8 §8** (not
duplicated here to avoid the two copies drifting) — summary: all 8
expressible under this design; rows 2 (CT) and 8 (VA) additionally need
ordinary future rule-module work this sprint does not build (value
parsing for CT's prose scope; a `StructuralUnitRule` for VA's new
`"title"` kind) — flagged, not silently assumed away.

### What must NOT change (G6)

- `determine_scope`'s own signature, return type, or dispatch order —
  `determine_scope_assignments` is a sibling, not a replacement.
- `_in_scope` / `_value_matches` / `_subsection_contains_offset` — the M9
  tuple mechanism they already run is reused as-is, zero edits.
- Any existing `ScopeKindRule` registration/lookup test's assertions.
- `Definition`'s schema — no new column; `scope_value` stays transient
  (v2.5's ruling re-applied, not re-litigated — see seam v2.8 §6).
- The headings panel's own value-PARSING rule modules
  (`chapter_range_scope_bounds`, `enumerated_local_scope_targets`, etc.)
  — explicitly their later work, not built here.

---

## Full-suite state at handoff

`backend/.venv/bin/pytest tests/ -q` (this worktree, this branch):
**772 passed, 8 failed** — the 8 failures are exactly the RED tests listed
above (2 × G5 dispatch, 5 × G6 dispatch, 1 × G6 live-path); zero
collateral damage to the pre-existing suite. The 2 intentionally-GREEN
tests (G5's static-field invariant, G6's positive control) are included
in the 772 passed and are load-bearing regression guards, not filler.
