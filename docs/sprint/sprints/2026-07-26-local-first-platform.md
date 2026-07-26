---
id: "2026-07-26-local-first-platform"
status: qa-fail
current_role: developer
branch: sprint/2026-07-26-local-first-platform
locked_by: "claude-code:developer"
locked_at: "2026-07-26T11:20:00Z"
last_agent: "claude-code:qa"
last_updated: "2026-07-26T13:35:00Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 17
completed_items: 16
dev_complete_items: 17
qa_cycles: 1
prd_sections:
  - docs/specs/collaborative-assertions.md
design_sections: []
previous_sprint: "2026-07-25-collaborative-assertions"
---

# Sprint: Local-first platform — authored-text fidelity, ingest pipeline, LexGraph MCP, packaging

Director mandate (2026-07-26): LexGraph is a three-part local-first open-source
system usable from Claude Code, Codex, Cursor, or Antigravity: (1) an
enrichment stage that suggests assertions from documents already stored in
the database (document acquisition/scraping is explicitly out of scope);
(2) the grading app (exists) that edits the database; (3) a LexGraph MCP
server that maps the database for agent sessions (CodeGraph-style: fewer
tokens, less time, better output). Everything local — no cloud deploy;
installable from a terminal. Also resolve GitHub issue #2 (store raw +
sanitized text separately), including its length-cap sub-item.

Director scope amendment (2026-07-26, mid-planning): scraping/document
acquisition is OUT of scope this sprint — no file-ingest CLI, no txt/md/html
parsing pipeline, no document-loader modules. Documents arrive in the
database by the existing means only (the current API/fixtures). Enrichment
is the only pipeline surface this sprint: it runs over documents already
stored in the local DB and suggests assertions as proposal drafts. See
ruling R7.

## Acceptance gates (manager-defined)

- G1 Fidelity (issue #2): text containing angle-bracket prose (`<Title>`,
  `<appendix A>`, `<img plaintail <b>Y</b> Z`) round-trips byte-exact through
  create → fetch → revision history → audit/diff paths. Raw stored alongside
  sanitized; `sanitize_for_storage` is not weakened in any way.
- G2 No XSS regression: the 17-shape hostile-input battery still yields no
  live markup on any rendering path; every read site explicitly classified
  raw-vs-sanitized, with tests pinning that HTML paths never receive raw.
- G3 Reversible migration; backfill (sanitized value copied into raw for
  historical rows) documented in a runbook entry.
- G4 Length cap: proposition / comment_text / rationale capped at 100,000
  chars (director may override), enforced at the API with a clear error.
- G5 Enrich command: a local CLI command runs the enrichment pass over
  documents already stored in the local DB; re-running it is idempotent (no
  duplicate suggestions); failures are reported clearly. Document
  acquisition/scraping is out of scope — documents enter the DB via
  existing APIs/fixtures only.
- G6 Suggest: an enrichment pass produces suggested assertions as proposal
  drafts with evidence linked to real document spans already stored in the
  DB; never auto-accepted; they enter the existing review workflow;
  authored text preserved byte-exact. Enricher pluggable; built-in enricher
  fully offline.
- G7 MCP: a local stdio MCP server exposes the graph against the local DB
  with no network: an explore-style tool returns assertions + evidence +
  relationships for a query in one bounded call, plus search/fetch tools.
  One documented command registers it in Claude Code; config snippets for
  Codex, Cursor, Antigravity.
- G8 Local-first install: a documented terminal sequence takes a fresh clone
  to a working system (DB init, backend, grading app, MCP) with zero cloud
  dependencies; the grading app edits the DB end-to-end locally (E2E proves
  seed a document via the existing API → enrich/suggest → review → grade).

## Manager rulings

- R1 Prior sprint advanced review→done: PR #1 was merged to main by the
  director (vicciz-ceo) — treated as explicit approval; the new mandate
  supersedes it.
- R2 Local-first default DB is SQLite (file on disk); schema stays
  Postgres-compatible (spec §11 authority unchanged for server deployments).
- R3 Length cap defaults to 100,000 characters per issue #2's
  recommendation; flagged to the director as a product decision.
- R4 Enrichment: heuristic/rule-based suggester in core (fully offline);
  LLM enrichers behind a pluggable interface, optional and off by default —
  preserves the no-cloud guarantee.
- R5 MCP v1 is read-only (explore/search/fetch); write/suggest tools are
  deferred pending director direction.
- R6 MCP implemented in Python with the official `mcp` SDK (stdio
  transport), living in the backend package so it reuses the SQLAlchemy
  models directly.
- R7 Director correction (2026-07-26): scraping/document acquisition
  removed from scope; enrichment operates only on documents already present
  in the DB. Any ingest-CLI work is out of scope.

## Next Steps

Planner pass complete 2026-07-26. 17 items across 4 tracks. Track A is
sequential and lands first (schema + fidelity); Tracks B/C/D are
parallel-eligible once Track A's schema item (A1) is dev-complete, since B2
writes propositions through the same revision-creation path A1/A2 touch.

### Track A — text fidelity, sanitizer pins, length cap (G1–G4) — sequential, FIRST

**DEV COMPLETE (all 9 items, Sonnet medium, solo) — see `## Dev Complete`
below for files/commits/results per item.** Item specs kept here as
reference for QA and for the Track B/C/D items below, which build on this
track's schema/routes.

**A1. Raw-text columns + reversible migration + backfill**
Add `proposition_raw` (assertion_revisions), `comment_text_raw`
(assertion_comments), `rationale_raw` (assertion_ratings) columns (ORM +
a hand-rolled reversible migration module, no Alembic — see Deviations).
Migration backfills sanitized value into raw for pre-existing rows;
downgrade drops the columns. Document the backfill in `docs/RUNBOOK.md`
(D1). Files: `backend/app/models/assertion_revision.py`,
`assertion_comment.py`, `assertion_rating.py`, new
`backend/app/migrations/add_raw_text_columns.py`.
Test: `backend/tests/integration/test_migration_raw_text_columns.py`.

**A2. Write paths (assertions) store raw + sanitized**
`POST /assertions`, `PATCH /assertions/{id}`, `POST
/assertions/{id}/revisions` store `body.proposition` verbatim into the new
revision's `proposition_raw`, sanitized value unchanged in `proposition`.
`GET /assertions/{id}` exposes the current revision's raw text as
`proposition_raw`. Files: `backend/app/routers/assertions.py`.
Test: `backend/tests/integration/test_assertion_raw_text_fidelity.py`.

**A3. Write paths (comments) store raw + sanitized**
Comment create/update store `comment_text_raw` verbatim; list/get expose
it. Files: `backend/app/routers/comments.py`.
Test: `backend/tests/integration/test_comment_raw_text_fidelity.py`.

**A4. Write paths (ratings) store raw + sanitized**
Rating PUT stores `rationale_raw` verbatim; get/list expose it (same
rationale-visibility permission gate as today). Files:
`backend/app/routers/ratings.py`.
Test: `backend/tests/integration/test_rating_raw_text_fidelity.py`.

**A5. G1 acceptance: named examples round-trip byte-exact**
The three issue-#2 example strings (`<Title>`, `<appendix A>`, `<img
plaintail <b>Y</b> Z`) round-trip byte-exact through create → fetch →
PATCH (new revision) → revision history, via the raw columns from
A2–A4. Depends on A1+A2. Test:
`backend/tests/integration/test_g1_fidelity_round_trip.py`.

**A6. Search reads raw, not sanitized (read-path classification)**
`GET /assertions?q=...` matches against the current revision's raw
proposition (joined), not the lossy sanitized column — so a search term
lost by the sanitizer (e.g. "appendix A") still finds the assertion. No
export/diff endpoint exists in this codebase to classify separately; audit
already stores only short status strings (spec §16), never proposition
text. Files: `backend/app/routers/assertions.py`.
Test: `backend/tests/integration/test_search_raw_text_classification.py`.

**A7. Frontend: revision history + comparison render raw as text nodes**
`AssertionRevisionHistory` and `AssertionComparisonView` render the raw
proposition (never `dangerouslySetInnerHTML` — plain JSX text nodes, which
neither component uses today) so angle-bracket prose is visible
byte-exact in the diff/compare surfaces. Files:
`frontend/src/components/AssertionRevisionHistory.tsx`,
`AssertionComparisonView.tsx`.
Tests (edited in place, new cases added):
`frontend/src/components/__tests__/AssertionRevisionHistory.test.tsx`,
`AssertionComparisonView.test.tsx`.

**A8. Length cap: 100,000 chars enforced at the API (G4)**
New `validate_text_length(text, *, label, max_length=100_000)` in
`app/services/validation.py`; called for proposition (create/patch/
revision-create), comment_text (create/update), rationale (rating put).
Rejects with a clear 422 detail; boundary (exactly 100,000) is accepted.
Files: `backend/app/services/validation.py`, `routers/assertions.py`,
`comments.py`, `ratings.py`. Tests:
`backend/tests/unit/test_validation_length_cap.py`,
`backend/tests/integration/test_length_cap_api.py`.

**A9. Stale-pin sweep: supersede the R18 "accepted limitation" framing**
`sanitize_for_storage` itself is UNCHANGED (still browser-faithful, still
lossy for tag-attribute-shaped prose) — the sweep does not weaken it. Only
the one test that treated the sanitized column as the sole fidelity story
is re-pointed to also assert byte-exact `proposition_raw`; see `## Stale-pin
sweep` below for the exact hit list.

### Track B — enrichment only (G5, G6) — parallel-eligible after A1

**B1. Enrichment CLI command**
`python -m app.enrich.cli --matter-id <id>` runs the enrichment pass over
documents/spans already in the DB (seeded via existing conftest
fixtures/API — no file parsing). Idempotent re-run (no duplicate draft
assertions for a span already suggested); clear non-zero-exit failure for
an unknown matter. Files: `backend/app/enrich/cli.py`.
Test: `backend/tests/integration/test_enrich_cli.py`.

**B2. Offline heuristic suggester + live pipeline**
`app/enrich/suggester.py`: pure heuristic function, span text → candidate
proposal(s) (type, proposition, evidence span). Live pipeline writes real
`Assertion`/`AssertionRevision`/`AssertionEvidence` rows (origin
`model_suggested`, status `draft`/`proposed`, never `accepted`) against
real spans, visible via the existing `GET /assertions` list. Files:
`backend/app/enrich/suggester.py`, `pipeline.py`. Tests:
`backend/tests/unit/test_enrichment_suggester.py`,
`backend/tests/integration/test_enrichment_pipeline_live.py`.

**B3. Pluggable enricher interface (R4 boundary seam)**
`app/enrich/base.py` defines the `Enricher` protocol; the pipeline accepts
an injected enricher (declared boundary seam — a fake enricher is allowed
here only), defaulting to the real built-in `HeuristicEnricher` when none
is given. Files: `backend/app/enrich/base.py`.
Test: `backend/tests/unit/test_enricher_interface.py`.

### Track C — LexGraph MCP (G7) — parallel-eligible after A1

**C1. MCP stdio server: explore/search/fetch tools, no network**
`app/mcp/server.py` (official `mcp` SDK, stdio transport) registers
`explore` (query → assertions + evidence + relationships in one bounded
call), `search`, `fetch` tools reading the local SQLAlchemy session
directly; zero network I/O. Files: `backend/app/mcp/server.py`,
`backend/pyproject.toml` (add `mcp` dependency).
Test: `backend/tests/integration/test_mcp_tools_live.py`.

**C2. MCP registration docs**
`docs/mcp-registration.md`: one command to register with Claude Code;
config snippets for Codex, Cursor, Antigravity.
Test: `backend/tests/unit/test_mcp_registration_docs.py`.

### Track D — local-first install + E2E (G8) — parallel-eligible after A1+B1

**D1. Local-first install runbook**
`docs/RUNBOOK.md`: DB init/migration (incl. A1's backfill note), backend
serve, grading-app serve, MCP registration (points to C2).
Test: `backend/tests/unit/test_local_first_runbook_docs.py`.

`[QA-FAIL: 2026-07-26, QA cycle 1]` `docs/RUNBOOK.md` line 6 states
"3. A Vue.js grading application" and line 126 frames the grading app as
a Vue project — this is factually wrong. `frontend/package.json` lists
`"react": "^18.3.1"`, `"react-dom": "^18.3.1"`, `"@vitejs/plugin-react"`,
and every component in `frontend/src/components/` is a `.tsx` React
component tested with `@testing-library/react`; there is no Vue dependency
anywhere in the repo. Expected: the intro must name the actual framework
(React, served via Vite) so a fresh-clone installer isn't misled about
what they're running. No test pin is possible for this — it is a
prose-only factual claim in a doc file, not behavior; `grep -n -i
"vue\|react" docs/RUNBOOK.md` confirms the sole hit is this one wrong
line. (The manager's own pre-handoff log entry at
`docs/sprint/sprints/2026-07-26-local-first-platform-log.md` already
flagged this identical defect before QA started — independently
reconfirmed here.) Every other command/path/env var in `docs/RUNBOOK.md`
and `docs/mcp-registration.md` was verified correct (see `## QA Notes`).

**D2. G8 E2E: seed → enrich → review → grade, fully local**
Seed a matter/document/source_span via existing fixtures, run the
enrichment pipeline (B2), submit for review, reviewer accepts via the
existing API, assert the accepted assertion appears in
`GET /matters/{id}/graph` — one process, one local SQLite file, no
network. Test: `backend/tests/e2e/test_local_first_platform_flow.py`.

**D3. Zero-network guardrail**
Static test asserting `app.enrich` and `app.mcp` import none of
`httpx`/`requests`/`urllib.request`/`aiohttp`/`socket`.
Test: `backend/tests/unit/test_no_network_dependencies.py`.

### Parallelization plan (write-sets, zero overlap)

- **Track A** (sequential, first): `backend/app/models/assertion_revision.py`,
  `assertion_comment.py`, `assertion_rating.py`; new
  `backend/app/migrations/`; `backend/app/routers/assertions.py`,
  `comments.py`, `ratings.py`; `backend/app/services/validation.py`;
  `frontend/src/components/AssertionRevisionHistory.tsx`,
  `AssertionComparisonView.tsx`. Owner of `proposition_raw`/
  `comment_text_raw`/`rationale_raw` persistence (new repository-level
  columns) and every write call-site listed above.
- **Track B** (after A1): new `backend/app/enrich/` package only
  (`cli.py`, `suggester.py`, `pipeline.py`, `base.py`). Owner of the new
  `run_enrichment(...)` dispatcher call-site and the `Enricher` protocol.
  Reads `app.routers.assertions`/`app.models` but does not edit them.
- **Track C** (after A1): new `backend/app/mcp/` package only
  (`server.py`); `backend/pyproject.toml` (dependency line only, additive).
  Owner of the `explore`/`search`/`fetch` tool registrations. Reads
  `app.models` but does not edit routers.
- **Track D** (after A1+B1): `docs/RUNBOOK.md`, `docs/mcp-registration.md`
  (new docs only); `backend/tests/e2e/test_local_first_platform_flow.py`
  (new test only, no app code). No shared file with A/B/C.

### Expected-RED census

| Test file | Expected failing | Failure mode |
|---|---|---|
| `integration/test_migration_raw_text_columns.py` | 2 | ModuleNotFoundError (`app.migrations`) |
| `integration/test_assertion_raw_text_fidelity.py` | 4 | KeyError/AssertionError (no `proposition_raw` key) |
| `integration/test_comment_raw_text_fidelity.py` | 2 | KeyError/AssertionError |
| `integration/test_rating_raw_text_fidelity.py` | 2 | KeyError/AssertionError |
| `integration/test_g1_fidelity_round_trip.py` | 3 | KeyError/AssertionError |
| `integration/test_search_raw_text_classification.py` | 1 | AssertionError (search misses raw-only match) |
| `AssertionRevisionHistory.test.tsx` (new cases) | 1 | AssertionError (raw text not in DOM) |
| `AssertionComparisonView.test.tsx` (new cases) | 1 | AssertionError |
| `unit/test_validation_length_cap.py` | 4 | ImportError (`validate_text_length`) |
| `integration/test_length_cap_api.py` | 6 | AssertionError (no 422 / no cap); +1 GREEN companion (at-cap accepted) stays green |
| `integration/test_hostile_input.py` (edited) | 1 | KeyError/AssertionError (`proposition_raw` missing) |
| `integration/test_enrich_cli.py` | 3 | ModuleNotFoundError (`app.enrich`) |
| `unit/test_enrichment_suggester.py` | 3 | ModuleNotFoundError |
| `integration/test_enrichment_pipeline_live.py` | 2 | ModuleNotFoundError |
| `unit/test_enricher_interface.py` | 3 | ModuleNotFoundError |
| `integration/test_mcp_tools_live.py` | 2 | ModuleNotFoundError (`app.mcp`) |
| `integration/test_mcp_search_fetch_tools.py` | 2 | ModuleNotFoundError (`app.mcp`) |
| `unit/test_mcp_registration_docs.py` | 1 | FileNotFoundError/AssertionError |
| `unit/test_local_first_runbook_docs.py` | 1 | FileNotFoundError/AssertionError |
| `e2e/test_local_first_platform_flow.py` | 1 | ModuleNotFoundError (`app.enrich`) |
| `unit/test_no_network_dependencies.py` | 2 | ModuleNotFoundError |

Census corrected by the manager 2026-07-26 from a measured full run
(`41 failed, 238 passed, 1 collection error` — reconciles exactly with the
table above; the length-cap unit file's 4 tests surface as 1 collection
ERROR until `validate_text_length` exists).

## Stale-pin sweep

`grep -riE "browser-faithful|accepted limitation|browser faithful"` across
`backend/tests/{unit,integration,e2e}` and `frontend/src/components/__tests__`
found exactly two hits, both from ruling R18 (2026-07-25 sprint):

- `backend/tests/unit/test_validation.py` — 3 pins on `sanitize_for_storage`
  directly (`test_sanitize_drops_text_parsed_as_tag_attributes_browser_faithful_*`).
  **Not re-pointed**: these test the pure sanitizer function, which issue #2
  explicitly requires stay unweakened; their assertions remain correct and
  unchanged. Docstrings amended in place to replace the stale "(proposed
  for a future sprint)" note with a pointer to this sprint's raw-storage
  resolution.
- `backend/tests/integration/test_hostile_input.py::test_proposition_text_parsed_as_tag_attributes_dropped_browser_faithful_via_real_api`
  — **re-pointed**: added `assert r.json()["proposition_raw"] == text`
  (byte-exact) alongside the existing (unchanged) sanitized-column
  assertion, since the raw column now supersedes "permanently lost" as the
  fidelity story for this shape. This is the one hit that changes behavior
  the Developer must satisfy (A2/A5).

No other hits for "single-column" storage assumptions or `r.json() ==`
exact-dict-equality patterns that would break from the new `_raw` response
keys (verified via `grep -rn "json() =="` across `backend/tests` — the only
hit is an unrelated empty-list assertion in `test_notifications.py`).

## Dev Complete

Developer pass (Track A solo, Sonnet medium), spawned on 017c9d7, all 9
items dev-complete:

- **A1** Raw-text columns + reversible migration + backfill. Files:
  `backend/app/models/assertion_revision.py`, `assertion_comment.py`,
  `assertion_rating.py`, `backend/app/migrations/__init__.py`,
  `add_raw_text_columns.py`. Commit `47507b3`. Result: `upgrade`/`downgrade`
  green (2/2); ORM columns added nullable, backfilled by the migration.
- **A2** Assertion write paths (create/patch/create-revision) store raw +
  sanitized. Files: `backend/app/routers/assertions.py`. Commit `d11324c`.
  Result: 4/4 green.
- **A3** Comment write paths store raw + sanitized. Files:
  `backend/app/routers/comments.py` (+ `assertions.py`'s embedded comment
  summary, for read-path consistency). Commit `b14abe3`. Result: 2/2 green.
- **A4** Rating write paths store raw + sanitized rationale, same
  rationale-visibility gate applied to `rationale_raw`. Files:
  `backend/app/routers/ratings.py`. Commit `820a4b4`. Result: 2/2 green.
- **A5** G1 named-example round-trip. No new code — green as a direct
  consequence of A1+A2 (verified, no commit of its own). Result: 3/3 green.
- **A6** Search matches the current revision's raw proposition, not the
  sanitized column. Files: `backend/app/routers/assertions.py`. Commit
  `c281ed6`. Result: 1/1 green.
- **A7** Frontend revision-history + comparison render
  `propositionRaw ?? proposition` as plain JSX text nodes (no
  `dangerouslySetInnerHTML` introduced). Files:
  `frontend/src/components/AssertionRevisionHistory.tsx`,
  `AssertionComparisonView.tsx`. Commit `cb2546b`. Result: 2/2 new cases
  green; full frontend suite 62/62 green.
- **A8** `validate_text_length(text, *, label, max_length=100_000)` added
  to `app/services/validation.py`; wired into every proposition/
  comment_text/rationale write path (create/patch/create-revision,
  comment create/update, rating put), checked against the raw submitted
  text before sanitization. `sanitize_for_storage` untouched. Files:
  `backend/app/services/validation.py`, `routers/assertions.py`,
  `comments.py`, `ratings.py`. Commit `a0bf1f6`. Result: unit 4/4, API
  6/6 (+1 at-cap companion stayed green) — 11/11.
- **A9** Stale-pin sweep. No code change: `sanitize_for_storage` is
  byte-identical to before this sprint; the Planner-edited
  `test_hostile_input.py` pin (which asserts `proposition_raw == text`
  alongside the unchanged sanitized-column assertion) went green as a
  direct consequence of A2's `proposition_raw` exposure on
  `_serialize_assertion`. Verified: full `test_hostile_input.py` 40/40
  green, including the 17-shape hostile battery and all 3
  `test_validation.py` browser-faithful pins untouched.

Parallel pass (devB enrichment / devC MCP, both Sonnet medium, spawned on
eb38032 in isolated worktrees; manager merged devC ff → a578477, devB
merge → c836154; entries applied by the manager per parallel-mode rule):

- **B1** Enrichment CLI (`python -m app.enrich.cli --matter-id <id>
  --triggered-by-user-id <id>`; reads `LEXGRAPH_DATABASE_URL`; non-zero
  exit + stderr on unknown matter). Files: `backend/app/enrich/cli.py`.
  Commit `9acd0f9`. Result: 3/3 green.
- **B2** Offline heuristic suggester + live pipeline: deterministic
  precision-first rule set → real Assertion/AssertionRevision/
  AssertionEvidence rows, origin `model_suggested`, status `draft`, never
  accepted; raw/sanitized split mirrors `routers/assertions.py`;
  idempotent re-runs. Files: `backend/app/enrich/suggester.py`,
  `pipeline.py`. Commit `be82651`. Result: 3/3 + 2/2 green.
- **B3** Pluggable `Enricher` protocol, default `HeuristicEnricher`
  (declared R4 boundary seam). Files: `backend/app/enrich/base.py`,
  `__init__.py`. Commit `e3598a8`. Result: 3/3 green.
- **C1** LexGraph MCP stdio server (`FastMCP`, tools explore/search/fetch,
  read-only per R5, zero network, bounded results, raw-text precedence,
  runnable `python -m app.mcp.server`). Files: `backend/app/mcp/__init__.py`,
  `server.py`. Commit `a578477`. Result: 4/4 green.

Developer pass (Track D solo, doc-only, Haiku low), spawned on 9b9c60b:

- **C2** MCP registration docs. Files: `docs/mcp-registration.md`. Commit
  `48caf40`. Result: 1/1 green. Covers Claude Code registration (`claude mcp
  add lexgraph`), plus config snippets for Codex, Cursor, and Antigravity.
- **D1** Local-first install runbook. Files: `docs/RUNBOOK.md`. Commit
  `48caf40`. Result: 1/1 green. Covers DB init/migration/backfill, backend
  serve, grading-app serve, MCP registration, E2E workflow, environment
  variables, and troubleshooting.
- **D2** Zero-network guardrail (no code). Test: `backend/tests/unit/test_no_network_dependencies.py`. Result: 2/2 green with no code — verified in full pass.
- **D3** Local-first E2E flow (no code). Test: `backend/tests/e2e/test_local_first_platform_flow.py`. Result: 1/1 green with no code — verified in full pass.

Developer-verified on the dev tree (48caf40): backend 283 passed /
0 failed; frontend 62 passed / 0 failed. Scoped doc tests 2/2 green
before commit; full pass confirms zero regressions across all 17
completed items (A1–A9, B1–B3, C1–C2, D1–D3).

Owned-file conditional grants (`backend/app/routers/history.py`,
`backend/app/models/repository.py`): not exercised. No Track A test reads
`GET /assertions/{id}/history` (audit-only, stores short status strings
per spec §16, never proposition text) or a repository-pattern write layer
(`app/models/repository.py` is the `Repository` ORM model, not a write
layer); every write path in this app goes directly through routers via
`Session`. Both files left untouched.

## Completed

QA cycle 1 (2026-07-26), 16/17 PASS — D1 bounced, see its `[QA-FAIL: ...]`
entry above. Verdict = PASS, probe = one live/independent check beyond the
item's own tests, regression = new QA test name (file:
`backend/tests/integration/test_qa_regression_local_first_platform.py`
unless noted).

- **A1** Raw-text columns + reversible migration + backfill. PASS — ran
  `upgrade()`/`downgrade()`/`upgrade()` myself against a throwaway file DB
  with a simulated pre-existing (pre-migration) row; backfill and column
  drop/restore verified byte-exact. Regression: none needed (G3 fully
  covers this).
- **A2** Assertion write paths store raw + sanitized. PASS — live API
  probe: create + PATCH with an `<appendix A>`-shaped proposition;
  `proposition_raw` byte-exact, sanitized column correctly altered.
  Regression: `test_proposition_raw_round_trips_unicode_emoji_and_crlf_byte_exact`.
- **A3** Comment write paths store raw + sanitized. PASS — live API probe:
  comment create + list expose `comment_text_raw` byte-exact. Regression:
  `test_comment_raw_round_trips_unicode_emoji_and_crlf_byte_exact`.
- **A4** Rating write paths store raw + sanitized rationale. PASS — live
  API probe of PUT rating plus the visibility gate (peer/rater/reviewer).
  Regression: `test_rating_list_nulls_rationale_for_unauthorized_peer_but_not_for_rater_or_reviewer`
  (closes a real coverage gap — no prior test exercised the unauthorized
  path for this gate).
- **A5** G1 named-example round trip. PASS — 3/3 green; confirmed the
  fixture strings are issue #2's exact quoted examples. Regression: n/a
  (covered by A2/A8 boundary regression).
- **A6** Search reads raw proposition, not sanitized. PASS — live API
  probe: `q=appendix A` (a sanitizer-dropped term) finds the assertion via
  the real endpoint. Regression: covered by
  `test_proposition_at_cap_boundary_containing_angle_brackets_round_trips_raw`.
- **A7** Frontend revision history + comparison render raw text nodes.
  PASS — scoped vitest run (9/9) via real React Testing Library render;
  `grep -rn dangerouslySetInnerHTML frontend/src` returns zero code hits
  (one unrelated comment string in a test file). Regression: none needed
  (component tests already exhaustive for this surface).
- **A8** Length cap (100,000 chars) enforced at the API. PASS — 11/11
  suite green. Regression:
  `test_proposition_at_cap_boundary_containing_angle_brackets_round_trips_raw`
  (boundary size composed with raw-fidelity in one case).
- **A9** Stale-pin sweep. PASS — `git show db203ce` on both edited test
  files confirms only the documented docstring updates + the one added
  `proposition_raw` assertion; the sanitized-column assertions and all 3
  `test_validation.py` browser-faithful pins are byte-identical to before.
  Regression: n/a (historical-diff verification, not new behavior).
- **B1** Enrichment CLI. PASS — ran the real CLI as a subprocess against a
  seeded SQLite file DB: run 1 creates 1 draft `model_suggested` assertion
  (confirmed via `GET /assertions`), run 2 is idempotent (0 created, DB
  still holds exactly 1), unknown matter exits 1 with a clear stderr
  message. Regression:
  `test_enrich_cli_on_matter_with_zero_spans_creates_nothing_and_exits_zero`.
- **B2** Offline heuristic suggester + live pipeline. PASS — same
  subprocess trace confirms real `Assertion`/`AssertionRevision`/
  `AssertionEvidence` rows, `origin=model_suggested`, `status=draft`,
  never `accepted`. Regression:
  `test_run_enrichment_on_matter_with_zero_spans_returns_empty_list`.
- **B3** Pluggable `Enricher` protocol. PASS — 3/3 green; read
  `pipeline.py`'s `enricher if enricher is not None else
  HeuristicEnricher()` wiring directly. Regression: n/a (interface-level,
  already exhaustive).
- **C1** LexGraph MCP stdio server. PASS — confirmed
  `test_mcp_tools_live.py`/`test_mcp_search_fetch_tools.py` dispatch
  through the real `server.call_tool(...)` (not raw functions); booted
  `python -m app.mcp.server` as a subprocess against a schema'd file DB
  with stdin held open — stayed alive the full 5s bound, no traceback, no
  crash. Regression: `test_mcp_fetch_of_nonexistent_assertion_id_does_not_crash`.
- **C2** MCP registration docs. PASS — content read in full: `claude mcp
  add` command matches `server.py`'s actual module path; Codex/Cursor/
  Antigravity snippets present; no factual defects found. Regression: n/a
  (doc-only, no behavior to pin).
- **D2** (G8 E2E: seed → enrich → review → grade;
  `backend/tests/e2e/test_local_first_platform_flow.py`, per this
  contract's Track D item list — labeled "D3" in `## Dev Complete`'s prose,
  see `## QA Notes`). PASS — 1/1 green; test body read in full and matches
  gate G8 exactly against the real API, one local SQLite file, no network.
  Regression: n/a (E2E-level, exhaustive by design).
- **D3** (zero-network guardrail;
  `backend/tests/unit/test_no_network_dependencies.py`, per this
  contract's Track D item list — labeled "D2" in `## Dev Complete`'s prose,
  see `## QA Notes`). PASS — manually grepped every import in `app/enrich/`
  and `app/mcp/`; zero network-capable modules, matching the AST-based
  test's verdict. Regression: n/a (static-analysis-level, exhaustive).

## Evaluation Notes

Track A (A1–A9), Developer solo pass, dev-complete 2026-07-26 (see `## Dev Complete` for per-item detail):

**Previous evaluation (Track A summary)**:

- Scoped RED confirmed before work started: 21 failed across the 8 Track A
  integration/hostile-input files + 4-test collection error in
  `test_validation_length_cap.py` — matched the contract's corrected
  census exactly.
- Per-item scoped runs, all green: A1 2/2, A2 4/4, A3 2/2, A4 2/2, A5 3/3,
  A6 1/1, A7 2/2 (+ full frontend suite), A8 11/11 (4 unit + 6 API + 1
  at-cap companion), A9 verified via full `test_hostile_input.py` 40/40
  (no code change required for A5 or A9 — both went green as direct
  consequences of A1/A2's `proposition_raw` plumbing).
- One full authoritative pass:
  `backend/.venv/bin/pytest backend/tests -v` → **20 failed, 263 passed**;
  `npm --prefix frontend run test -- --run` → **62 passed**. The 20
  backend failures reconcile exactly against the contract's expected
  Track B/C/D RED list (test_enrich_cli 3, test_enrichment_suggester 3,
  test_enrichment_pipeline_live 2, test_enricher_interface 3,
  test_mcp_tools_live 2, test_mcp_search_fetch_tools 2,
  test_mcp_registration_docs 1, test_local_first_runbook_docs 1,
  test_local_first_platform_flow 1, test_no_network_dependencies 2) — no
  failure outside that list. `test_validation_length_cap.py`'s collection
  error is gone.
- `sanitize_for_storage` is byte-identical to before this sprint (not
  edited); all 3 `test_validation.py` browser-faithful pins and the
  17-shape hostile battery in `test_hostile_input.py` remain green.
- No `dangerouslySetInnerHTML` introduced anywhere in the frontend diff.
- Conditional grants (`routers/history.py`, `models/repository.py`) not
  exercised/edited — no Track A test reads either surface; every write
  path goes directly through routers via `Session`.

Track D (C2+D1+D2+D3), Developer solo pass (doc-only items), dev-complete
2026-07-26. Summary counts only (see `## Dev Complete` for per-item detail):

- Scoped RED confirmed before work: 2 failed (doc-tests for C2, D1 only).
- Doc files written: `docs/mcp-registration.md` (covers Claude Code + 3
  client config snippets) and `docs/RUNBOOK.md` (fresh-clone to working
  local-first system in one doc: DB init/migration/backfill, backend serve,
  grading-app serve, MCP registration, E2E workflow, troubleshooting).
- Scoped run: C2+D1 both pass 1/1 each.
- D2 and D3 are verify-only (no code): `test_local_first_platform_flow` and
  `test_no_network_dependencies` are already green from prior dev work
  (B1/C1). Verified in full pass: both remain green.
- Full authoritative pass: backend 283/283 green, frontend 62/62 green. Zero
  regressions across all 17 completed items (A1–A9 from prior dev, B1–B3
  from prior devB/devC, C1 from prior devC, C2+D1+D2+D3 this pass).
- Deviations from brief: none.

## QA Notes

- 2026-07-26T13:35Z qa: Independent evaluator green — backend 283→290
  passed (7 new QA regressions), frontend 62/62, zero flakes. Live-path
  PASS: enrich CLI subprocess (idempotent, clean unknown-matter failure),
  MCP stdio boot (5s, stdin held open, no crash), FastMCP real
  `call_tool` dispatch confirmed, frontend raw-text rendering + zero
  `dangerouslySetInnerHTML`. Gate sweeps PASS: G1/G2 classification
  (JSON-only backend + 2 text-node React components), G3 migration
  round-trip (live, throwaway DB), G4 privacy (live — closed a real
  untested gap). D1 FAILED: `docs/RUNBOOK.md` calls the frontend
  "Vue.js" — it's React+Vite (manager's own pre-handoff log already
  flagged this). 16/17 PASS. Full transcript: see `-log.md`.

## Context Dump

- New sprint opened by manager 2026-07-26. Planner defines items + RED tests
  per the gates above. Issue #2 body is authoritative for G1–G4 detail:
  https://github.com/vicciz-ceo/LexGraph/issues/2
