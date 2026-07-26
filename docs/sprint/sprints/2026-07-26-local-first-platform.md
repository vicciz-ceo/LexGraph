---
id: "2026-07-26-local-first-platform"
status: planning
current_role: planner
branch: sprint/2026-07-26-local-first-platform
locked_by: "claude-code:planner"
locked_at: "2026-07-26T08:51:30Z"
last_agent: "claude-code:manager"
last_updated: "2026-07-26T08:51:30Z"
lint: null
evaluator: custom
evaluator_command: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
total_items: 0
completed_items: 0
dev_complete_items: 0
qa_cycles: 0
prd_sections:
  - docs/specs/collaborative-assertions.md
design_sections: []
previous_sprint: "2026-07-25-collaborative-assertions"
---

# Sprint: Local-first platform — authored-text fidelity, ingest pipeline, LexGraph MCP, packaging

Director mandate (2026-07-26): LexGraph is a three-part local-first open-source
system usable from Claude Code, Codex, Cursor, or Antigravity: (1) a
scraping/enrichment stage that suggests assertions; (2) the grading app
(exists) that edits the database; (3) a LexGraph MCP server that maps the
database for agent sessions (CodeGraph-style: fewer tokens, less time, better
output). Everything local — no cloud deploy; installable from a terminal.
Also resolve GitHub issue #2 (store raw + sanitized text separately),
including its length-cap sub-item.

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
- G5 Ingest: a local CLI ingests a document file (txt/md/html at minimum)
  into documents + provision spans; re-ingesting the same file does not
  duplicate; failures reported clearly.
- G6 Suggest: an enrichment pass produces suggested assertions as proposal
  drafts with evidence linked to real ingested spans; never auto-accepted;
  they enter the existing review workflow; authored text preserved
  byte-exact. Enricher pluggable; built-in enricher fully offline.
- G7 MCP: a local stdio MCP server exposes the graph against the local DB
  with no network: an explore-style tool returns assertions + evidence +
  relationships for a query in one bounded call, plus search/fetch tools.
  One documented command registers it in Claude Code; config snippets for
  Codex, Cursor, Antigravity.
- G8 Local-first install: a documented terminal sequence takes a fresh clone
  to a working system (DB init, backend, grading app, MCP) with zero cloud
  dependencies; the grading app edits the DB end-to-end locally (E2E proves
  ingest → suggest → review → grade).

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

## Next Steps

(Planner fills.)

## Dev Complete

## Completed

## Evaluation Notes

## QA Notes

## Context Dump

- New sprint opened by manager 2026-07-26. Planner defines items + RED tests
  per the gates above. Issue #2 body is authoritative for G1–G4 detail:
  https://github.com/vicciz-ceo/LexGraph/issues/2
