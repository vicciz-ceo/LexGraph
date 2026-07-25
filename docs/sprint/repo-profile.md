# Repo Profile — LexGraph

Per-repo overlay for the sprint-harness skill (bootstrapped 2026-07-25 by the
manager; fresh greenfield repo). The Planner finalizes evaluator commands and
venv setup in its first pass and updates this file in the same commit.

```yaml
platform: claude-code
governance_skill: none
runbook_path: none   # create docs/RUNBOOK.md when first user-facing behavior ships
evaluator_default: custom
evaluator_commands:
  backend: "TBD-by-Planner"    # expected shape: .venv/bin/pytest backend/tests -v
  frontend: "TBD-by-Planner"   # expected shape: npm --prefix frontend run test -- --run
test_roots:
  - backend/tests/
  - "frontend/src/**/*.test.*"
  - e2e/
registries: []   # no shared sequence registries yet; add migration numbering here if Alembic is adopted
venv_setup: "TBD-by-Planner"   # expected shape: python3 -m venv .venv && .venv/bin/pip install -e 'backend[dev]'
gemma_local_spawning: false
notes: |
  Greenfield repo. Stack ruling (sprint contract, Manager rulings R1):
  FastAPI + SQLAlchemy 2 backend, React + TS + Vite frontend, SQLite for
  tests with Postgres-compatible schema, graph projection behind an
  interface with an in-memory adapter (no live Neo4j in this environment).
  Test roots above do not exist until the Planner scaffolds them — Phase 1
  test-root validation applies only from the first Developer spawn onward.
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
