---
id: "2026-07-29-definition-links"
status: planned
current_role: developer
branch: sprint/2026-07-29-definition-links
locked_by: "claude-code:developer"
locked_at: 2026-07-29T13:59:14Z
last_agent: "claude-code:developer"
last_updated: 2026-07-29T14:24:42Z
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 10
completed_items: 0
dev_complete_items: 6
qa_cycles: 0
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

Solo mode (single Developer, sequential). Items DL1-DL9 below. All new code
lives under `backend/app/definition_links/` (new package) plus two new model
files; nothing in `app/enrich/` or existing routers is touched. RED tests for
every item already exist and are committed — Developer's job is to make them
pass without weakening any assertion.

**DL6 — Stage 4 cross-law derivation + Stage 5 guards + M7 bidi guard.**
`app/definition_links/derivation.py`: `TRIGGER_PHRASES`,
`detect_cross_law_derivations(text, *, source_term, known_law_titles=None)`
(M5: unresolved → `target_law_id=None`, raw text preserved),
`is_generic_law_reference(text, trigger_pos)`. `app/definition_links/guards.py`:
`is_plain_quotation`, `is_rejectable_term`, `resolve_law_title` (exact-match
only), `is_bidi_degraded` (M7).
Tests: `backend/.venv/bin/pytest backend/tests/unit/test_definition_links_derivation.py backend/tests/unit/test_definition_links_guards.py -v`

**DL7 — M4 article-aware wiki ingestion.**
`app/definition_links/ingest.py`: `ingest_wiki_law(session, *, repository_id,
matter_id, title, wiki_text) -> {"document_id", "article_ids",
"source_span_ids"}`. Creates one `Document`, one `Article` + backing
`SourceSpan` per parsed article (via DL3's `parse_articles`). Never imports
the POC's `build_assertions_db` module.
Tests: `backend/.venv/bin/pytest backend/tests/integration/test_definition_links_ingest.py -v`

**DL8 — Persistence pipeline (orchestration, M2/M5/M7 end-to-end).**
`app/definition_links/pipeline.py`: `run_definition_linking(session, *,
matter_id, triggered_by_user_id) -> {"created_assertions", "created_definitions",
"skipped_degraded_article_ids"}`. Reads Articles for the matter, runs
Stages 0/2-5 per article, writes real `Definition` + `Assertion` rows
(USES_DEFINITION conf ≥0.9; DERIVES_FROM_LAW conf ≥0.8 resolved, strictly
lower unresolved). Idempotent re-run. `UnknownMatterError` for bad matter_id.
Mirrors `app/enrich/pipeline.py::run_enrichment`'s shape/idempotency approach.
Tests: `backend/.venv/bin/pytest backend/tests/integration/test_definition_links_pipeline_live.py -v`

**DL9 — M6 CLI `link-definitions`.**
`app/definition_links/cli.py`: `main(argv) -> int`, invoked as
`python -m app.definition_links.cli --matter-id <id> --triggered-by-user-id
<id>` (parity with `app/enrich/cli.py`). Calls `run_definition_linking` on
the live path; created assertions visible via the EXISTING
`GET /api/v1/assertions` route — no new router this sprint (API route is
optional stretch, explicitly skipped; no frontend UI per M6).
Tests: `backend/.venv/bin/pytest backend/tests/integration/test_definition_links_cli.py -v`
Cross-cutting (satisfied only once the whole package exists):
`backend/.venv/bin/pytest backend/tests/unit/test_definition_links_no_network_dependencies.py -v`

Run the whole track together once DL1-DL9 land:
`backend/.venv/bin/pytest backend/tests/unit/test_definition_links_*.py backend/tests/integration/test_definition_links_*.py -v`

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

- DL10 — mcp pin repair (M8): backend/pyproject.toml @ 821a597; `-k "mcp"` →
  7 passed, 0 failed (manager-verified probe). mcp 2.0.0 → 1.29.0.
- DL1 — Schema + assertion-type vocabulary (M1, M2): `app/models/article.py`,
  `app/models/definition.py`, `app/models/__init__.py`,
  `app/services/validation.py` @ 10ab30f; test_definition_links_models.py +
  test_definition_links_assertion_vocabulary.py → 8 passed, 0 failed.
- DL2 — Stage 0 text normalization: `app/definition_links/normalize.py`
  @ 3f9b347; test_definition_links_normalize.py → 11 passed, 0 failed.
- DL3 — Stage 1 article/section parsing: `app/definition_links/sections.py`
  @ 99e2992; test_definition_links_sections.py → 8 passed, 0 failed.
- DL4 — Stage 2 term/definition extraction: `app/definition_links/extract.py`
  @ 7be404b; test_definition_links_extract.py → 10 passed, 0 failed.
- DL5 — Stage 3 term matching + article-linking:
  `app/definition_links/matcher.py` @ 507ce85;
  test_definition_links_matcher.py → 10 passed, 0 failed.

## Completed

## Evaluation Notes

## QA Notes

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
