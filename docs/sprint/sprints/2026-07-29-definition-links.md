---
id: "2026-07-29-definition-links"
status: review
current_role: planner
branch: sprint/2026-07-29-definition-links
locked_by: "claude-code:qa"
locked_at: 2026-07-29T14:51:16Z
last_agent: "claude-code:qa"
last_updated: 2026-07-29T14:56:28Z
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 10
completed_items: 10
dev_complete_items: 0
qa_cycles: 2
prd_sections: []
design_sections: []
---

# Sprint: Definition-based article linking (2026-07-29)

Director mandate (verbatim intent): refine the LexGraph repo based on what was
done in the POC found in `/Users/nerya/AI for others` (subprojects:
AI-for-Lawyers, israeli-boi-directives, israeli-laws-wiki,
lexgraph-assertions-db); add **wholly deterministic** code that (a) connects
articles within a law via the definitions the law contains, and (b) connects
laws to each other when a definition is derived from another law. Research the
approach first, then execute. Broad mandate — manager proceeds autonomously,
gates reported to director.

## Draft acceptance gates (manager, pending recon refinement)

- G1: Given a law's text containing a definitions section, the system
  deterministically extracts each defined term and links every article in that
  law that uses the term to the definition — same input always yields the same
  links, no LLM/ML in the path.
- G2: When a definition explicitly derives from another law ("כהגדרתו
  בחוק..." / "as defined in..."), the system creates a law-to-law link that
  names both laws and the term.
- G3: POC learnings from AI-for-others are reflected in the repo (data model
  / parsing conventions), with the specifics enumerated by recon.
- G4: Full evaluator (backend pytest + frontend vitest) green.

## Manager rulings

- M1 (schema): director mandate requires article-level linking → ADDITIVE schema
  extension authorized: new `Article` + `Definition` tables; existing tables
  unchanged. "Frozen post-F1" yields to the explicit new mandate; reported to
  director as a deviation.
- M2 (representation): structure lives in `Article`/`Definition`; the LINKS are
  Assertions with new vocabulary entries (uses-definition, derives-from-law —
  exact names Planner's call, consistent with existing ALLOWED_ASSERTION_TYPES
  style), origin=system_generated, status=proposed, POC confidence tiering
  (structural ≥0.9 / prose-derived lower).
- M3 (fixtures): vendor a SMALL slice of israeli-laws-wiki (the edge-case files
  named in the review doc, trimmed if huge; target <500KB total) into
  backend/tests/fixtures/; never the full corpus; tests read fixtures offline.
- M4 (ingestion): never import from the POC path at runtime; port
  normalize_title/WIKILINK_RE *patterns* into repo code; new article-aware
  wiki-format parser lives in-repo.
- M5 (unresolved cross-law derivations): emit with target_law_id=null + raw
  matched string preserved, at reduced confidence — recorded exception to the
  POC drop-not-guess rule (string preserved, resolution not fabricated).
- M6 (surface): CLI `link-definitions` required (parity with enrich); API route
  optional stretch; NO frontend UI this sprint.
- M7 (degraded text): bidi-sanity guard required at linker input; degraded
  files are flagged + skipped, never auto-corrected.
- M8 (env repair): `mcp>=1.0` resolves to 2.0.0 which removed
  `mcp.server.fastmcp`, breaking 6 pre-existing tests (manager-verified at
  app/mcp/server.py:39). Ruled: minimal pin `mcp>=1.0,<2.0` as item DL10;
  mcp 2.x migration deferred to a future sprint. Supersedes Planner chip
  task_ad884976.

## Next Steps

(empty — all 10 items PASS as of QA cycle 2. Full QA-FAIL rationale for the
cycle-1 DL8 bounce: see 2026-07-29-definition-links-log.md.)

## Stale-pin sweep

Swept `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/e2e/`,
`frontend/src/components/__tests__/*.test.tsx` for strings this track's items
change (`ALLOWED_ASSERTION_TYPES` membership/count, model/table-count
assertions, fixture placeholder texts, `app/models/__init__.py::__all__`,
`Base.metadata`/`create_all` assumptions, entity_type enumerations in graph
projection tests, assertion-type `<select>` dropdowns in frontend forms).

Result: **none** — additive feature, no hits.
- No test anywhere asserts an exact `ALLOWED_ASSERTION_TYPES` count/set
  (`grep -rn "len(ALLOWED_ASSERTION_TYPES)\|ALLOWED_ASSERTION_TYPES =="` — 0
  hits), so adding `USES_DEFINITION`/`DERIVES_FROM_LAW` breaks nothing.
- No test asserts a fixed model/table count (`grep -rn "13 table\|model_count"`
  — 0 hits) — F1's own docstring narrative ("13 tables") is prose, not a
  test assertion.
- `tests/unit/test_graph_projection.py` uses opaque entity ids/types with no
  closed-set assertion — new "Article"/"Definition" entity types are inert
  to it.
- `frontend/src/components/AssertionSuggestionForm.tsx`'s `assertionType`
  field is free-text (`useState("")` + plain input), not an enumerated
  `<select>` — confirmed via source read, not just grep. The only
  hardcoded `<select>` in that file is unrelated (`evidence_role`:
  supports/contradicts). Matches M6 (no frontend UI this sprint): zero
  frontend files need touching.
- `tests/conftest.py` gained two new raw-SQL seed helpers (`seed_article`,
  `seed_definition`) — additive, no existing helper signature changed.

## Dev Complete

(empty — DL8 moved to Completed, QA cycle 2.)

## Completed

- DL10 — mcp pin repair (M8): backend/pyproject.toml @ 821a597; `-k "mcp"` →
  7 passed, 0 failed (QA-reverified independently: 7 passed). mcp 2.0.0 →
  1.29.0 confirmed at the INSTALLED-PACKAGE level
  (`importlib.metadata.version("mcp")`), not just pyproject.toml's text.
  QA confirmed the 6 formerly-failing tests
  (`test_mcp_search_fetch_tools.py` x2, `test_mcp_tools_live.py` x2,
  `test_qa_regression_local_first_platform.py` x1,
  `test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries`
  x1) pre-date this sprint (added in sprint/2026-07-26-local-first-platform,
  commits 42f1a05/236a6fa/e450010) — genuine RED provenance, not
  sprint-authored tests. PASS.
- DL1 — Schema + assertion-type vocabulary (M1, M2): `app/models/article.py`,
  `app/models/definition.py`, `app/models/__init__.py`,
  `app/services/validation.py` @ 10ab30f; test_definition_links_models.py +
  test_definition_links_assertion_vocabulary.py → 8 passed, 0 failed
  (QA-reverified). PASS.
- DL2 — Stage 0 text normalization: `app/definition_links/normalize.py`
  @ 3f9b347; test_definition_links_normalize.py → 11 passed, 0 failed
  (QA-reverified). PASS.
- DL3 — Stage 1 article/section parsing: `app/definition_links/sections.py`
  @ 99e2992; test_definition_links_sections.py → 8 passed, 0 failed
  (QA-reverified). PASS.
- DL4 — Stage 2 term/definition extraction: `app/definition_links/extract.py`
  @ 7be404b; test_definition_links_extract.py → 10 passed, 0 failed
  (QA-reverified). PASS.
- DL5 — Stage 3 term matching + article-linking:
  `app/definition_links/matcher.py` @ 507ce85;
  test_definition_links_matcher.py → 10 passed, 0 failed (QA-reverified).
  PASS.
- DL6 — Stage 4 cross-law derivation + Stage 5 guards + M7 bidi guard:
  `app/definition_links/derivation.py`, `app/definition_links/guards.py`
  @ 474e34d; test_definition_links_derivation.py +
  test_definition_links_guards.py → 20 passed, 0 failed (QA-reverified).
  PASS. (QA note, non-blocking: `guards.py`'s `is_plain_quotation`,
  `is_rejectable_term`, `resolve_law_title` are unit-tested but never
  imported/called by `extract.py`/`derivation.py`/`pipeline.py` — only
  `is_bidi_degraded` is wired in. No current test/fixture exercises a
  false-positive this would have caught; flagged for future-sprint
  follow-up, not a blocker this cycle.)
- DL7 — M4 article-aware wiki ingestion: `app/definition_links/ingest.py`
  @ 1799c8b; test_definition_links_ingest.py → 4 passed, 0 failed
  (QA-reverified). Live-path (c) confirmed: `ingest_wiki_law` persists
  real `Article`+`SourceSpan` ORM rows that `pipeline.py` subsequently
  reads via `select(Article)...`/`session.get(SourceSpan, ...)`. PASS.
- DL8 — Persistence pipeline idempotency-key fix (cycle 2 QA-reverified):
  `app/definition_links/pipeline.py` @ 2f27703. PASS — cycle-1 RED pin green.
  E2E probe: `חוק הגנת הפרטיות_excerpt.wiki` line 17's 3-term clause now
  persists 3 DERIVES_FROM_LAW edges (one per term, all → `חוק המחשבים`),
  idempotent under the new key (rerun: 0 new rows). Regression:
  `test_three_term_shared_derivation_clause_persists_three_resolved_edges`.
- DL9 — M6 CLI `link-definitions`: `app/definition_links/cli.py` @ 7cf2fe6;
  test_definition_links_cli.py + test_definition_links_no_network_dependencies.py
  → 5 passed, 0 failed (QA-reverified). Live-path (a) confirmed by source
  read: `cli.py::main` calls `run_definition_linking` directly (no
  subprocess/reimplementation). Live-path (b) confirmed: created
  `Assertion`/`Definition` rows are visible via the EXISTING
  `GET /api/v1/assertions` route (already exercised by this item's own
  tests). `docs/RUNBOOK.md` updated @ cabda01. PASS.

## Evaluation Notes

DL1-DL9 all Dev Complete. Scoped track (unit + integration
`test_definition_links_*`): 84 passed, 0 failed (matches the pre-verified
RED baseline count exactly — every formerly-RED test now green, none
weakened).

Full authoritative pass:
- `backend/.venv/bin/pytest backend/tests -v` → **374 passed, 0 failed**
  (includes the 84 definition-links tests plus the 6 previously-broken
  `mcp` tests, repaired by DL10's `mcp<2.0` pin).
- `npm --prefix frontend run test -- --run` → **62 passed** (11 test
  files), unchanged from baseline — no frontend files touched (M6: no
  frontend UI this sprint).

Deviations from brief: none. Escalations: none — no Planner test looked
wrong or under-specified; every pinned public API (module paths, function
signatures, return shapes) in the RED tests was implementable as written.

## QA Notes

- **2026-07-29T15:10Z QA cycle 1 (sonnet/high).** Independent evaluator
  pass (own numbers, not reused from Developer):
  `backend/.venv/bin/pytest backend/tests -v` → 374 passed, 0 failed;
  `npm --prefix frontend run test -- --run` → 62 passed (11 files), 0
  failed. No flakes.
  Per-item reverification (exact contract test commands): DL1 8p, DL2
  11p, DL3 8p, DL4 10p, DL5 10p, DL6 20p, DL7 4p, DL9 5p, DL10 7p — all
  match Dev Complete's claimed counts, 0 failed. DL8's own 8 tests also
  pass, but QA's own live-corpus probe + a new integration test exposed
  a spec violation not caught by the Developer's 8 tests (see below) →
  **DL8 FAIL**.
  Live-path traces: (a) PASS — `cli.py::main` calls
  `run_definition_linking` directly, confirmed by source read. (b) PASS
  — CLI-created `Assertion`/`Definition` rows visible via the existing
  `GET /api/v1/assertions` route (DL9's own tests already exercise this
  end-to-end; re-run and confirmed). (c) PASS — `ingest_wiki_law`
  persists real `Article`+`SourceSpan` rows that `pipeline.py` reads via
  `select(Article)...` / `session.get(SourceSpan, ...)`.
  Independent E2E probe (own script, scratch sqlite, real vendored
  fixtures, CLI invoked via subprocess): ingested 5 laws (24 articles) →
  `link-definitions` → 91 assertions / 92 definitions. G1 PASS (79
  USES_DEFINITION edges linking real articles to real extracted
  definitions, e.g. "נכס" §1→§2/§3/§7). G2 PASS ("חומר מחשב"/"מחשב"/"פלט"
  כהגדרתם [[בחוק המחשבים]] in חוק הגנת הפרטיות resolves DERIVES_FROM_LAW
  to the ingested `חוק המחשבים` document, naming both laws + term).
  Determinism PASS: 2 additional reruns produced byte-identical link sets
  and 0 new rows both times (91/92 → 91/92 → 91/92).
  **Manager-flagged edge (dual unresolved derivations, sprint log line
  14): CONFIRMED COLLAPSED.** `_create_assertion`'s idempotency key
  `(assertion_type, subject_entity_type, subject_entity_id,
  object_entity_type, object_entity_id)` omits the derivation's
  term/matched-text; two independently-unresolved `DERIVES_FROM_LAW`
  edges from the SAME Definition both key to `(..., Definition, <id>,
  None, None)` and collide — the second is silently dropped. Also
  reproduced on the REAL corpus in the RESOLVED-target variant: a
  single 3-term definition (`חוק הגנת הפרטיות_excerpt.wiki` line 17,
  "חומר מחשב"/"מחשב"/"פלט" all → `חוק המחשבים`) persists only 1
  DERIVES_FROM_LAW assertion instead of 3 (one per term, per the review
  doc's own worked example) — same root cause. `[QA-FAIL]` on DL8. RED
  test committed (never modifies implementation):
  `backend/tests/integration/test_definition_links_pipeline_dual_unresolved_derivation.py`
  — 1 failed as expected (proves the collapse; asserts the SPEC'D
  2-edge outcome, not a flip-to-red trap).
  Bug-fix pin check (DL10): the 6 formerly-failing mcp tests pre-date
  this sprint (git history: added in sprint/2026-07-26-local-first-platform
  @ 42f1a05/236a6fa/e450010) — genuine RED provenance — and now pass;
  `mcp` resolves to 1.29.0 (< 2.0) at the installed-package level.
  Regression tests added for every PASSED item (9 tests,
  `backend/tests/integration/test_qa_regression_definition_links.py`):
  DL1 nested-Definition ORM round trip, DL2 compound Stage-0
  normalization, DL5 three additional documented `מאגר מידע` surface
  forms, DL6 `כאמור בחוק` non-trigger, DL7 ingest-twice non-dedup, DL9
  missing-required-arg usage error, DL10 installed-package version
  check.
  Full suite with both new files: 384 collected, 383 passed, 1 failed
  (the intentional DL8 RED pin) — everything else green.
  Non-blocking observation (not a FAIL, no test currently exercises it):
  `guards.py`'s Stage 5.1/5.2 functions (`is_plain_quotation`,
  `is_rejectable_term`) and Stage 5.4's `resolve_law_title` are unit-
  tested but never imported by `extract.py`/`derivation.py`/
  `pipeline.py` — only `is_bidi_degraded` is wired into the live path.
  Deviations: none beyond the DL8 bounce. Escalations: none.
  Status set: qa-fail, current_role: developer, qa_cycles: 1.
- **2026-07-29T14:56:28Z QA cycle 2 (sonnet/high), DL8 re-verify only.**
  HEAD confirmed at 37208f7. Independent full evaluator (own numbers):
  `backend/.venv/bin/pytest backend/tests -v` → 384 passed, 0 failed;
  `npm --prefix frontend run test -- --run` → 62 passed (11 files), 0
  failed. No flakes.
  Commit 2f27703 confirmed: diff touches only `pipeline.py`, 2 lines
  added (deterministic `proposition` in both identity-key constructions).
  Cycle-1 RED pin (`test_definition_links_pipeline_dual_unresolved_derivation.py`)
  now green. E2E probe on real vendored fixtures: ingested
  `חוק המחשבים_stub.wiki` + `חוק הגנת הפרטיות_excerpt.wiki` into one
  matter — the 3-term shared clause at line 17 ("חומר מחשב"/"מחשב"/"פלט"
  כהגדרתם [[בחוק המחשבים]]) now persists exactly 3 `DERIVES_FROM_LAW`
  assertions, one per term, each naming its term and each resolving
  (`object_entity_type="Document"`) to the ingested `חוק המחשבים` row —
  confirms the cycle-1-corroborated resolved-target collapse is fixed.
  Idempotency: a second pipeline run over the same matter created 0 new
  assertions/definitions; persisted `(assertion_type, subject_entity_id,
  object_entity_id, proposition)` key sets identical across both runs.
  **DL8 PASS.** Regression test added:
  `test_three_term_shared_derivation_clause_persists_three_resolved_edges`
  in `test_qa_regression_definition_links.py` @ 69b1be6; full backend
  suite re-run with it included → 385 passed, 0 failed.
  DL8 moved Dev Complete → Completed (all 10 items now Completed).
  Deviations: none. Escalations: none.
  Status set: review, current_role: planner, qa_cycles: 2.

## Context Dump

Recon complete: see docs/sprint/sprints/2026-07-29-definition-links-review.md
(POC map, repo gaps, full deterministic algorithm, refinements R1-R9, open
questions — resolved by Manager rulings M1-M7 above).

**Planner pass complete (2026-07-29).** Venv built fresh inside this worktree
per repo-profile (`cd backend && python3.13 -m venv .venv && .venv/bin/pip
install -e '.[dev]'`); canary confirmed `import app` resolves to THIS
worktree's `backend/app/__init__.py`. Frontend `npm --prefix frontend
install` run (node_modules was missing).

**Fixtures vendored** (ruling M3, `backend/tests/fixtures/wiki_laws/`, 4
files + 2 synthetic, ~46KB total, well under the 500KB cap):
- `חוק להגנת רכוש מופקד.wiki` — full file (3.8KB), byte-identical copy from
  the POC corpus (`/Users/nerya/AI for others/israeli-laws-wiki/data/laws/`)
  — clean small example (M3).
- `חוק הגנת הפרטיות_excerpt.wiki` — curated excerpt (§1, §3 definitions incl.
  nested sub-def + cross-law derivation, §8 usage w/ construct-state/plural
  inflections + local scoped def) — NOT byte-identical to the source file
  (trimmed per M3), but every included line is a verbatim quote from it.
- `חוק העונשין_excerpt.wiki` — curated excerpt (§34כד chapter-scoped
  הגדרות incl. qualifier-before-dash + list-form; §35/§35א local scoped
  defs; §51א second chapter-scoped הגדרות) — trimmed per the review doc's
  explicit instruction (full file is 492KB).
- `חוק הבנקאות (שירות ללקוח)_excerpt.wiki` — curated excerpt (§1 definitions
  incl. the `חוק הבנקאות` ambiguous-law-name edge case; §3 unquoted `(להלן -
  X)`; §7ו curly-quote/en-dash normalization case).
- `חוק המחשבים_stub.wiki` — small SYNTHETIC stub (hand-authored, not from
  the POC corpus) used only to seed a second, resolvable target law for the
  cross-law-derivation-resolved integration test.
- `degraded_bidi_sample.wiki` — small SYNTHETIC scrambled-word-order fixture
  (hand-derived by reversing each line's word order from the already-
  vendored clean `חוק להגנת רכוש מופקד.wiki`) for the M7 bidi guard — NOT
  sourced from `israeli-boi-directives` (out of this sprint's read-only
  scope; the path granted was `israeli-laws-wiki` only).

**Design decisions made while authoring tests** (Planner's call per M2's
"exact names/columns Planner's call" precedent — none needed escalation):
- Assertion-type names: `USES_DEFINITION`, `DERIVES_FROM_LAW`.
- `Definition.terms` stored as a JSON list column (not a join table) — a
  deliberately minimal additive design for this sprint's scope.
- `articles.source_span_id` is NOT NULL (every ingested article always gets
  a backing `SourceSpan`, so `AssertionEvidence` needs no schema change).
- `DefinitionCandidate` carries `source_article_number`/`source_chapter` as
  provenance fields (`None` from extract.py itself; filled by pipeline.py)
  so `matcher.py` can enforce chapter/local scope isolation.
- Confidence tiering left as a RANGE, not a magic number: USES_DEFINITION
  ≥0.9; DERIVES_FROM_LAW resolved ≥0.8 and strictly greater than the
  unresolved case's confidence (M2's "structural ≥0.9 / prose-derived
  lower" gives the shape, not exact constants).
- A leading Hebrew prefix letter (Stage 3.1) is part of the MATCHED SPAN
  itself, not a separate lookbehind — `match.group(0)` for `במאגר המידע`
  is the full prefixed string.

**Caveat found in the real corpus, encoded into a test on purpose**:
`חוק העונשין` §34כד's list-form entry `"עובד הציבור" -` has every numbered
sub-item (1)-(11) ALREADY ending in its own `;` — the dossier's "no closing
`;` until the final item" description undersells the real trap: a naive
"stop at the first `;`" parser truncates at item (1). See
`test_extract_list_form_definition_spans_to_the_next_top_level_entry`.

**Pre-existing, OUT-OF-SCOPE environment anomaly found (not caused by this
sprint, not fixed by this sprint)**: `backend/pyproject.toml`'s `mcp>=1.0`
constraint resolves to `mcp==2.0.0` in a fresh venv, which removed
`mcp.server.fastmcp` — `app/mcp/server.py` (unrelated pre-existing module)
now fails to import. 6 pre-existing tests fail because of this
(`test_mcp_search_fetch_tools.py` x2, `test_mcp_tools_live.py` x2,
`test_qa_regression_local_first_platform.py` x1,
`test_no_network_dependencies.py::test_mcp_package_imports_no_network_libraries`
x1) — confirmed unrelated to definition-links (no file these tests touch
was changed by this track). Full-evaluator green will require someone to
pin `mcp` to a compatible 1.x range or update `app/mcp/server.py`'s import
— flagged for the Manager/director, out of this Planner's write-scope
(pyproject.toml/app/mcp are not test files).
