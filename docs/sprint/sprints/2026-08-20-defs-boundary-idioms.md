---
id: "2026-08-20-defs-boundary-idioms"
status: planned
current_role: developer
branch: claude/defs-boundary-idioms
locked_by: "claude-code:planner"
locked_at: "2026-08-21T14:38:00Z"
last_agent: "claude-code:manager"
last_updated: "2026-08-21T14:38:00Z"
program: "2026-08-04-definition-completeness"
evaluator: custom
evaluator_command: "PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python -m pytest backend/tests -q -p no:randomly && npm --prefix frontend run test -- --run && npm --prefix frontend run typecheck"
total_items: 3
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
lint: "PASS 172 2026-08-21T14:38:04Z"
previous_sprint: "2026-08-12-defs-b1-refers-to"
prd_sections: []
design_sections:
  - docs/sprint/programs/2026-08-04-definition-completeness.md
---

# Sprint: boundary-idiom widening — recover the 41 ceiling-tripped losses (issue #27)

## Mandate

GitHub issue #27. Forty-one (row, term) anchors produce no definition at all:
each is the LAST entry in its section with zero hard-stops found, because the
NEXT term's defining idiom (e.g. "shall include") is not in `_TIGHT_IDIOM_RE`
(`backend/app/definition_links/rules/us_markers_boundary.py:295` — currently
means | shall mean | has the meaning). With no boundary, capture runs to
end-of-text, exceeds `MAX_CLEAN_DEFINITION_LENGTH` (3,000 chars, line ~497),
and is correctly dropped by `close_entries` (~lines 640-693). The issue
owner's adjudication: all 41 are genuine runaway captures; the ceiling works;
the recovery path is idiom-vocabulary widening so a genuine closing boundary
is recognized. Raising the ceiling and scoping the guard are BOTH ruled out
(FX7 ruling, sprint 2026-08-10-green-the-suite: any guard-scoping broad
enough to recover the 41 flips the safety test RED — proven by QA).

Known examples: `USC_T5_C75_S7511` "furlough" (real def ~135 chars, captured
3,017), `STATE_NJ_T27_C1A_S1A-3.1` "Department" (real def one sentence,
captured 10,319). 2026-08-11 manager triage of all 66 affected rows:
41 ceiling-tripped / 25 present-but-shorter / 0 discriminator errors;
uncapped lengths min 3,017 / median 4,342 / max 11,730.

Director decisions taken: idiom list must be DERIVED from the 41 rows' actual
next-entry verbs (Planner enumerates the evidence; no guessed vocabulary).
Issue #26 stays deferred to its own sprint.

**AMENDED 2026-08-21 (director ruling, after the gate-2 footprint
investigation — see `2026-08-20-defs-boundary-idioms-scripts/investigation.md`):**
the widening's 130 collateral anchor losses trace to the pre-existing
fallback-suppression guard (`us_profile.py` ~2551: `if not candidates and
heading_was_derived`) — fallback definitions vanish the moment the primary
engine finds its first entry. Ruling: (a) fix that guard IN THIS SPRINT
(merge, don't suppress — Item 2); (b) also fix the ~9 degraded re-boundings
(investigation Q3: the "active efforts"-shape displacement family and the
NY "General service lamp" corruption — Item 3); (c) ONE combined
certification run ships only with ZERO genuine losses. Vocabulary itself is
vindicated: additions sample 80/80 genuine, re-boundings 97.6% improving.

## Acceptance gates (manager-defined, director-approved 2026-08-20)

1. **Recovery with correct text.** The 41 ceiling-tripped anchors are
   captured with text bounded at the true end of each definition. Any
   unrecoverable one is individually adjudicated with a stated reason —
   never silently skipped.
2. **Certified by execution (P-R11).** One full all-53 run; 100%
   anchor-granularity adjudication of the ACTUAL delta; measurement runs
   under the corrected convention — `--current` on BOTH sides of
   `measure_actual_production.py` (see Known traps).
3. **No collateral damage.** No existing correct capture is split by an
   idiom occurring INSIDE a definition body; every ADDED anchor in the delta
   is adjudicated genuine; P-R15 deletion-side screen clean. AMENDED
   2026-08-21: the combined run must show ZERO genuine anchor losses (100%
   of removals adjudicated; the 4 investigation-classified phantom removals
   are acceptable); the itemized degraded re-boundings (investigation Q3)
   must be fixed — no displacement or corruption ships. Additions and
   re-boundings are adjudicated by stratified sampling plus full-population
   structural checks per the investigation's methodology.
4. **The ceiling guard still works.** FX7 safety test
   (`backend/tests/integration/test_us_markers_fx7_ceiling_known_closed_scope.py`)
   stays GREEN — genuinely unbounded runaways are still dropped.
5. **No regression.** Full backend/frontend/lint green, explicitly including
   the boundary-engine guard estate: 16 c5guard class-B tests, the 5
   discriminator safety guards, the SC #28 run-membership test, the NV #25
   exclusion-bridge tests, and the module-docstring-pinned fixtures (AZ
   qualified actuary, UT Insolvent, VA sell, NV UCC, FED new drug).
6. **Red before green.** RED tests reproducing representative losses +
   novel structural controls (M-R107 — no jurisdiction/term/section keying;
   controls use unseen identifiers).
7. **Bounded.** AMENDED 2026-08-21: `git diff -- backend/app/` may touch
   `us_markers_boundary.py` AND the fallback-suppression guard site in
   `us_profile.py` (the `if not candidates and heading_was_derived` dispatch
   at ~2551 and, if the Item-3 diagnosis requires it, the term-set dedup it
   feeds — the Planner names the exact seam; anything beyond these escalates
   to the manager for a deliberate bound extension). Still forbidden:
   `_citation_or_xref_context`, `_extract_inline_quoted_definitions`'s own
   internals, and any B1 module.

## Rulings in force

P-R11, P-R12, P-R15, M-R107, D-RECALL-FP, D-MAP (see program doc and
handoff). FX7 prior ruling: ceiling-scoping not buildable as framed —
recovery goes through idiom vocabulary only.

## Known traps (do not rediscover)

- **Harness flags are part of the certificate**: `measure_actual_production.py`
  gates `recognized_by_registered_rule` on `--current`; production computes it
  unconditionally. Baseline runs MUST pass `--current` too, or the diff
  manufactures phantom deltas (proven in the #19 sprint — see
  `docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/investigation.md`;
  reusable corrected runner: that sprint's `run_gate2.sh`).
- "shall include" (and kin) commonly appear INSIDE definition bodies
  ("'X' means ... and 'Y' shall include ...") — this is exactly why the gate
  was kept tight. New idioms create new `starts` entries corpus-wide.
- `extract_quote_anchored_entries` returns (term, definition_text) tuples;
  a try/except-swallowing probe once manufactured a false "66/66
  discriminator errors" catastrophe — never swallow exceptions in probes.
- `qa_g7_common.INTEGRATION_SHA` re-pin + evidence regeneration whenever
  `backend/app` moves.
- Worktree venv: main checkout's venv with `PYTHONPATH=.:backend` from the
  worktree root; no `git stash`; raw-vs-ingest (escaped-\n) on raw parquet.

## Next Steps

### Item 1 — widen `_TIGHT_IDIOM_RE` to recover ceiling-tripped last entries (issue #27)

**Code already landed at `a51b1de`** (Developer pass, 2026-08-21). Gate-2
STOP-and-escalate on the widening's own collateral footprint (7,584
anchors) triggered the investigation and this amendment (Items 2-3,
below) — see the log doc's Developer-pass/Escalations sections and
`2026-08-20-defs-boundary-idioms-scripts/investigation.md`.

In `backend/app/definition_links/rules/us_markers_boundary.py`'s
`_TIGHT_IDIOM_RE` (line ~295) ONLY, add `shall include` and generalize
`has the meaning` to `has the (?:following |same )?meaning` (still
matches plain "has the meaning" unchanged). Do NOT touch `_TIGHT_IDIOM_
WITH_RELATIVE_QUALIFIER_RE` or `_EXCLUSION_CLAUSE_BRIDGE_RE` — no
evidence requires it. No other file. Full evidence, collateral-risk
sweep, and gate-2 commands: log doc.

RED tests to turn GREEN (all committed, all proven RED-for-cause and
GREEN under a monkeypatched widened regex this pass — log doc has the
proof runs): `test_us_markers_boundary_idioms_nj_department_recovery.py`,
`test_us_markers_boundary_idioms_nj_public_body_recovery.py`,
`test_us_markers_boundary_idioms_structural_controls.py`, and the
re-pinned `test_us_markers_c5guard_nj.py::test_c5_guard_state_nj_t48_c10_s10_3`.
Full suite verified: exactly these 8 RED pre-fix, all GREEN post-fix,
zero other regressions.

Adjudication (gate 1): live loss set is larger than the stale 41 (118
real losses — log doc). This item recovers the "shall include"/"has the
(following|same) meaning" subset only. `USC_T5_C75_S7511` "furlough" and
the rest are a DIFFERENT defect family (marker boundary, not idiom
vocabulary) — tracked, not silently dropped — log doc "Adjudication of
the unrecovered remainder".

### Item 2 — fix the fallback-suppression guard: merge, don't suppress

`backend/app/definition_links/us_profile.py`,
`USProfile.extract_definitions_from_section`'s guard (~line 2551): replace
`if not candidates and heading_was_derived: candidates = _extract_inline_
quoted_definitions(...)` with an always-run-when-`heading_was_derived`
merge — admit a fallback candidate only when its term does not collide
with any primary-engine term on that row, AND it fails a narrow
implausible-capture rejection (a bare stopword term from {for/and/or/the/
a/an/of/in/to/with/by}, or a term/definition_text starting with a
4-digit-year+dash amendment-caption shape, `^\d{4}[—–-]`). Design chosen
over unfiltered full union (strictly dominated: same additions, PLUS
reintroduces Item-3-shape same-term collisions site-wide) after measuring
footprint on the 130 losses + a seeded 200-row sample; full rationale and
numbers: log doc "Planner pass 2, Item 2 design".

RED tests (committed, RED-for-cause, GREEN under this pass's monkeypatched
simulation): `test_us_markers_fallback_guard_recovery.py` (FED 12889/WA
717/OH 3296/NY 1978), `test_us_markers_fallback_guard_phantom_negative_
control.py` (FED 4978, dual-purpose), `test_us_markers_fallback_guard_
structural_controls.py` (M-R107 synthetic). Stale pin re-pointed:
`test_us_body_preamble_g8_local_scope_dispatch_red.py`.

### Item 3 — fix the same-term-collision dedup ordering (degraded re-boundings)

`backend/app/definition_links/rules/us_markers_boundary.py`,
`extract_quote_anchored_entries`: after building `starts` (before
`close_entries`), classify each occurrence old-idiom (means/shall mean/
bare has-the-meaning, or bridged) vs new-idiom-only (shall include/
following meaning/same meaning); group by exact `term`; when a term has
both classes, drop the new-idiom-only occurrence(s), keeping the
pre-existing one(s) unchanged. Covers BOTH investigation-named shapes
(displacement family AND the list-introducer corruption) — one mechanism,
diagnosed this pass. Full diagnosis (incl. a correction to the NY row's
own characterization): log doc "Planner pass 2, Item 3 design".

RED tests (committed, RED-for-cause, GREEN under simulation):
`test_us_markers_dedup_swap_hazard_recovery.py` (WA "active efforts" RED;
NY "General service lamp" kept as a verified regression pin, NOT
reproducible at persistence altitude for this specific row — see its own
docstring), `test_us_markers_dedup_swap_hazard_structural_controls.py`
(M-R107 synthetic, both shapes).

## Dev Complete

_None._

## Completed

_None._

## Context Dump

Pass 2 (amendment) complete (2026-08-21). Items 2-3 defined + specced; 18
RED tests committed (8 RED-for-cause, 10 sanity/regression/negative-
control, all GREEN today and proven GREEN under a monkeypatched
simulation of both specs — see the Planner's completion report for the
script). One new stale pin found + re-pointed (G8 local-scope dispatch —
Item 2's merge surfaces a harmless extra section-candidate pipeline.py's
OWN existing inner dedup already discards). Finding worth director
attention: NY "General service lamp" does not reproduce investigation.md's
claimed corruption at persistence altitude for this row (baseline wins the
dedup there); demoted to a regression pin, general mechanism still proven
via WA + synthetic controls. Full suite: 1379 passed / 8 RED (mine) / 1
pre-existing unrelated failure (G7 SHA pin, Developer/QA territory per log
doc). Developer: read log doc "Planner pass 2" before coding.
