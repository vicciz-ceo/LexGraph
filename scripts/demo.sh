#!/usr/bin/env bash
# One-command demo: set up (first run only), seed a demo workspace, and run
# backend + frontend dev servers. Sign in at http://localhost:5173 as
# admin / reviewer / contributor / viewer.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d backend/.venv ]; then
  echo "» Creating backend venv…"
  (cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')
fi

if [ ! -f backend/dev.db ]; then
  echo "» Seeding demo workspace (backend/dev.db)…"
  (cd backend && .venv/bin/python -m app.seed_demo --db dev.db)
fi

if [ ! -d frontend/node_modules ]; then
  echo "» Installing frontend dependencies…"
  npm --prefix frontend install
fi

echo "» Starting backend on :8000 and frontend on :5173…"
(cd backend && LEXGRAPH_DATABASE_URL=sqlite:///dev.db exec .venv/bin/uvicorn app.main:app --port 8000) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

npm --prefix frontend run dev
