#!/usr/bin/env bash
# One-command demo: install what is missing, seed a demo workspace, and run the
# backend and the web app dev server until Ctrl-C. Sign in at the printed web
# address as admin, reviewer, contributor or viewer.
#
# Settings (environment variables):
#   BACKEND_PORT   API server port (default 8000)
#   FRONTEND_PORT  web app (Vite dev server) port (default 5173)
#   DEMO_DB        demo database file, relative to the repository root
#                  (default backend/dev.db)
#
# Safe to re-run. Each setup step checks its result rather than the existence
# of a directory, so the next run completes an interrupted one. It refuses to
# use a database that is not a demo workspace and never modifies one. It stops
# with an error if a port is taken or a server fails to start, and Ctrl-C (or
# SIGTERM) stops both servers.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)

BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
DEMO_DB=${DEMO_DB:-backend/dev.db}

BACKEND_PID=""
FRONTEND_PID=""
SEED_DIR=""

die() {
  echo "error: $*" >&2
  exit 1
}

alive() {
  [ -n "$1" ] && kill -0 "$1" 2>/dev/null
}

# Stop both servers (SIGTERM, then SIGKILL after 10 s) and remove a partial seed.
# shellcheck disable=SC2329 # run by the traps below
cleanup() {
  if alive "$FRONTEND_PID" || alive "$BACKEND_PID"; then
    echo "» Stopping the demo servers…"
    if alive "$FRONTEND_PID"; then kill -TERM "$FRONTEND_PID" 2>/dev/null || true; fi
    if alive "$BACKEND_PID"; then kill -TERM "$BACKEND_PID" 2>/dev/null || true; fi
    local i=0
    while [ "$i" -lt 100 ] && { alive "$FRONTEND_PID" || alive "$BACKEND_PID"; }; do
      sleep 0.1
      i=$((i + 1))
    done
    if alive "$FRONTEND_PID"; then kill -KILL "$FRONTEND_PID" 2>/dev/null || true; fi
    if alive "$BACKEND_PID"; then kill -KILL "$BACKEND_PID" 2>/dev/null || true; fi
  fi
  FRONTEND_PID=""
  BACKEND_PID=""
  if [ -n "$SEED_DIR" ]; then rm -rf "$SEED_DIR"; fi
  SEED_DIR=""
}

# shellcheck disable=SC2329 # run by the traps below
on_signal() {
  trap '' INT TERM HUP
  cleanup
  exit "$1"
}

trap cleanup EXIT
trap 'on_signal 130' INT
trap 'on_signal 143' TERM
trap 'on_signal 129' HUP

valid_port() {
  case $1 in '' | *[!0-9]*) return 1 ;; esac
  [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le 65535 ]
}

# Something accepts connections on this port, on either loopback address.
# (Vite binds "localhost", which is ::1 on some systems and 127.0.0.1 on others.)
port_in_use() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null || (exec 3<>"/dev/tcp/::1/$1") 2>/dev/null
}

valid_port "$BACKEND_PORT" || die "BACKEND_PORT must be a port number (1-65535), not '$BACKEND_PORT'"
valid_port "$FRONTEND_PORT" || die "FRONTEND_PORT must be a port number (1-65535), not '$FRONTEND_PORT'"
BACKEND_PORT=$((10#$BACKEND_PORT))
FRONTEND_PORT=$((10#$FRONTEND_PORT))
[ "$BACKEND_PORT" -ne "$FRONTEND_PORT" ] || die "BACKEND_PORT and FRONTEND_PORT must differ"
if port_in_use "$BACKEND_PORT"; then
  die "port $BACKEND_PORT is already in use, so the backend cannot start there. Stop the program using it, or choose another port: BACKEND_PORT=8001 ./scripts/demo.sh"
fi
if port_in_use "$FRONTEND_PORT"; then
  die "port $FRONTEND_PORT is already in use, so the web app cannot start there. Stop the program using it, or choose another port: FRONTEND_PORT=5174 ./scripts/demo.sh"
fi
command -v npm >/dev/null 2>&1 || die "npm was not found. Install Node.js 22.12 or later (it includes npm), then run this again."

case $DEMO_DB in
  /*) DB=$DEMO_DB ;;
  *) DB=$ROOT/$DEMO_DB ;;
esac
DB_DIR=$(dirname "$DB")
DB_NAME=$(basename "$DB")
[ -d "$DB_DIR" ] || die "the directory for DEMO_DB does not exist: $DB_DIR"

# --- Backend environment -----------------------------------------------------
# Ready when the demo's own modules import. That fails after an interrupted or
# outdated install, which the install below then completes.
BACKEND_MODULES='import app.main, app.migrate, app.seed_demo, fastapi.testclient, uvicorn'

backend_ready() {
  (cd backend && .venv/bin/python -c "$BACKEND_MODULES") >/dev/null 2>&1
}

if ! backend_ready; then
  echo "» Installing the backend into backend/.venv…"
  if ! backend/.venv/bin/python -m pip --version >/dev/null 2>&1; then
    [ ! -L backend/.venv ] || die "backend/.venv is a symbolic link to an environment without a working pip. Repair it or remove the link, then run this again."
    command -v python3 >/dev/null 2>&1 || die "python3 was not found. Install Python 3.12 or later, then run this again."
    rm -rf backend/.venv
    python3 -m venv backend/.venv
  fi
  (cd backend && .venv/bin/python -m pip install -e '.[dev]')
  if ! backend_ready; then
    (cd backend && .venv/bin/python -c "$BACKEND_MODULES") || true
    die "the backend in backend/.venv still cannot start after installing it (see the error above)."
  fi
fi

# --- Frontend dependencies -----------------------------------------------------
# npm writes node_modules/.package-lock.json only when an install completes, and
# `npm ls` fails when the installed tree no longer matches package.json. `npm ci`
# installs exactly the committed lockfile and never rewrites it.
frontend_ready() {
  [ -x frontend/node_modules/.bin/vite ] && [ -f frontend/node_modules/.package-lock.json ] &&
    npm --prefix frontend ls --all >/dev/null 2>&1
}

if ! frontend_ready; then
  echo "» Installing the frontend dependencies (npm ci)…"
  npm --prefix frontend ci
  frontend_ready || die "frontend/node_modules is still incomplete after npm ci."
fi

# --- Demo database -------------------------------------------------------------
# A demo workspace is one that has the seeder's demo users. Anything else (a
# workspace from app.bootstrap, another file) is refused and left untouched.
db_kind() {
  (cd backend && .venv/bin/python - "$DB" <<'PY'
import sqlite3
import sys
from pathlib import Path

from app.seed_demo import DEMO_USERS

try:
    uri = Path(sys.argv[1]).resolve().as_uri() + "?mode=ro"
    user_ids = {row[0] for row in sqlite3.connect(uri, uri=True).execute("SELECT id FROM users")}
except sqlite3.DatabaseError:
    print("foreign")
else:
    print("demo" if {user[0] for user in DEMO_USERS} <= user_ids else "other")
PY
  )
}

# Seed into a scratch directory next to the target and move the finished file
# into place, so an interrupted seed never leaves a half-built demo database.
seed_demo_db() {
  echo "» Seeding the demo workspace into $DEMO_DB…"
  SEED_DIR=$DB_DIR/.$DB_NAME.seeding
  mkdir "$SEED_DIR"
  (cd "$SEED_DIR" && PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}" \
    "$ROOT/backend/.venv/bin/python" -m app.seed_demo --db "$DB_NAME")
  mv "$SEED_DIR/$DB_NAME" "$DB"
  rm -rf "$SEED_DIR"
  SEED_DIR=""
}

rm -rf "$DB_DIR/.$DB_NAME.seeding" # left behind by a seed that was killed
if [ -f "$DB" ] && [ ! -s "$DB" ]; then
  echo "» $DEMO_DB is an empty file (no data); replacing it with the demo workspace."
  rm -f "$DB"
fi
if [ ! -e "$DB" ]; then
  seed_demo_db
else
  kind=$(db_kind)
  case $kind in
    demo)
      # A demo seeded by an older checkout lacks newer tables or columns, and the
      # server refuses to start on it. Upgrading is idempotent: a no-op when current.
      echo "» Upgrading the existing demo workspace in $DEMO_DB…"
      (cd backend && .venv/bin/python -m app.migrate --db "$DB")
      ;;
    other)
      die "$DEMO_DB is a LexGraph workspace but not the demo one: it has none of the demo users (admin, reviewer, contributor, viewer), so the demo sign-ins would fail. It was left untouched. Run the demo on its own file instead, for example DEMO_DB=backend/demo.db ./scripts/demo.sh, or serve this workspace as README.md \"Running the app\" describes."
      ;;
    *)
      die "$DEMO_DB is not a LexGraph database. It was left untouched. Move it away, or run the demo on another file, for example DEMO_DB=backend/demo.db ./scripts/demo.sh."
      ;;
  esac
fi

# --- Servers ---------------------------------------------------------------------
answers() {
  backend/.venv/bin/python -c '
import sys, urllib.request
urllib.request.build_opener(urllib.request.ProxyHandler({})).open(sys.argv[1], timeout=2).close()
' "$1" >/dev/null 2>&1
}

# wait_until_up PID URL NAME: until URL answers, failing if PID exits first.
wait_until_up() {
  local i=0
  while [ "$i" -lt 240 ]; do
    alive "$1" || die "the $3 exited while starting (its output is above)."
    if answers "$2"; then return 0; fi
    sleep 0.25
    i=$((i + 1))
  done
  die "the $3 did not answer $2 within 60 seconds."
}

echo "» Starting the backend on http://127.0.0.1:$BACKEND_PORT…"
(cd backend && LEXGRAPH_DATABASE_URL="sqlite:///$DB" \
  exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT") </dev/null &
BACKEND_PID=$!
wait_until_up "$BACKEND_PID" "http://127.0.0.1:$BACKEND_PORT/healthz" backend

echo "» Starting the web app on http://localhost:$FRONTEND_PORT…"
(cd frontend && LEXGRAPH_API_PROXY="http://127.0.0.1:$BACKEND_PORT" \
  exec ./node_modules/.bin/vite --port "$FRONTEND_PORT" --strictPort --clearScreen false) </dev/null &
FRONTEND_PID=$!
wait_until_up "$FRONTEND_PID" "http://localhost:$FRONTEND_PORT/" "web app"

cat <<EOF

» The LexGraph demo is running.
    Web app:   http://localhost:$FRONTEND_PORT  (sign in as admin, reviewer, contributor or viewer)
    API docs:  http://127.0.0.1:$BACKEND_PORT/docs
  Press Ctrl-C to stop both servers.

EOF

# Run until a server exits or a signal arrives. Waiting on a background sleep
# keeps the shell responsive: a trapped signal interrupts `wait` immediately.
while alive "$BACKEND_PID" && alive "$FRONTEND_PID"; do
  sleep 1 &
  wait "$!" || true
done
if alive "$BACKEND_PID"; then
  die "the web app stopped unexpectedly (its output is above); stopping the backend too."
fi
die "the backend stopped unexpectedly (its output is above); stopping the web app too."
