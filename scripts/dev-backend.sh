#!/bin/sh
# Serve the LexGraph API for the frontend dev server: the "backend" entry of
# .claude/launch.json, also usable by hand from any directory.
#
# Usage: scripts/dev-backend.sh [--port PORT]   (default: $PORT, else 8000)
#
# Serves backend/dev.db, the database README.md and scripts/demo.sh use, on
# 127.0.0.1:8000 by default, where frontend/vite.config.ts proxies /api.
# When backend/dev.db does not exist yet, the demo workspace is seeded into it
# first, as scripts/demo.sh does (sign in as admin, reviewer, contributor or
# viewer). An existing database is served as it is and never replaced.
set -eu
port=${PORT:-8000}
case "${1:-}" in
  --port) port=${2:?"--port needs a value"} ;;
  "") ;;
  *) echo "usage: scripts/dev-backend.sh [--port PORT]" >&2; exit 2 ;;
esac
cd "$(dirname "$0")/../backend"
backend=$(pwd)

if [ ! -x .venv/bin/python ]; then
  echo "dev-backend: no backend virtualenv ($backend/.venv). Create it with:" >&2
  echo "  (cd \"$backend\" && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]')" >&2
  exit 1
fi

if [ ! -e dev.db ]; then
  echo "dev-backend: $backend/dev.db does not exist; seeding the demo workspace into it"
  # The file is this run's own: a failed or interrupted seed removes it, so the
  # next start seeds again instead of serving a half-seeded workspace.
  trap 'rm -f dev.db dev.db-journal dev.db-wal dev.db-shm' EXIT
  trap 'exit 1' HUP INT TERM
  .venv/bin/python -m app.seed_demo --db dev.db
  trap - EXIT HUP INT TERM
fi

# A file without the LexGraph schema, such as the empty file a server started
# before seeding leaves behind, would answer every API call with an error.
if ! .venv/bin/python - 2>/dev/null <<'EOF'
import sqlite3
import sys

db = sqlite3.connect("file:dev.db?mode=ro", uri=True)
found = db.execute("select 1 from sqlite_master where type = 'table' and name = 'assertions'").fetchone()
sys.exit(found is None)
EOF
then
  echo "dev-backend: $backend/dev.db is not an initialized LexGraph database. Move it aside" >&2
  echo "to have the demo workspace seeded, or serve your own database by hand (README.md)." >&2
  exit 1
fi

LEXGRAPH_DATABASE_URL="sqlite:///$backend/dev.db"
export LEXGRAPH_DATABASE_URL
echo "dev-backend: serving $LEXGRAPH_DATABASE_URL on http://127.0.0.1:$port"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$port"
