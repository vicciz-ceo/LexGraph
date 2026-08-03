# Repo Profile — LexGraph

Per-repo overlay for the sprint-harness skill (bootstrapped 2026-07-25 by the
manager; fresh greenfield repo). The Planner finalizes evaluator commands and
venv setup in its first pass and updates this file in the same commit.

```yaml
platform: claude-code
governance_skill: none
runbook_path: docs/RUNBOOK.md   # created post-2026-07-26 sprint; keep in sync when behavior changes
evaluator_default: custom
evaluator_commands:
  backend: "backend/.venv/bin/pytest backend/tests -v"
  frontend: "npm --prefix frontend run test -- --run"
  combined: "backend/.venv/bin/pytest backend/tests -v && npm --prefix frontend run test -- --run"
test_roots:
  - backend/tests/unit/
  - backend/tests/integration/
  - backend/tests/e2e/
  - "frontend/src/components/__tests__/*.test.tsx"
registries: []   # no shared sequence registries yet; add migration numbering here if Alembic is adopted
venv_setup: "cd backend && python3.13 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
gemma_local_spawning: false
notes: |
  Greenfield repo. Stack ruling (sprint contract, Manager rulings R1):
  FastAPI + SQLAlchemy 2 backend, React + TS + Vite frontend, SQLite for
  tests with Postgres-compatible schema, graph projection behind an
  interface with an in-memory adapter (no live Neo4j in this environment).
  Planner pass complete 2026-07-25: scaffolding + test roots above now
  exist and are verified collectible (126 backend tests, 39 FAILED +
  87 ERROR, both legitimate RED; 59 frontend tests, import-resolution RED
  per the documented frontend exception). python@3.12 is not installed in
  this environment (only python@3.13 via Homebrew) — venv built with
  python3.13; functionally compatible with the R1 pin, flagged as a minor
  deviation in the sprint contract.

  Update (2026-08-02, sprint 2026-08-02-us-state-law Planner, ruling R4):
  the 126/39-FAILED/87-ERROR snapshot above is from 2026-07-25 and is
  STALE — re-verified 2026-08-02: backend 504/504 passed, frontend
  151/151 passed (20 files), typecheck clean. Whatever fixed the
  pre-existing red landed in an intervening sprint and was never synced
  back here. Always re-verify locally rather than trusting this note's
  numbers going forward.
```

## Live environment

```yaml
live_environment:
  frontend_base_url: unknown   # local-only; no deployed services
  backend_base_url: unknown
  health_endpoints: []
  notes: |
    No deployed environment. All verification is local (pytest/vitest +
    local dev servers).
```
