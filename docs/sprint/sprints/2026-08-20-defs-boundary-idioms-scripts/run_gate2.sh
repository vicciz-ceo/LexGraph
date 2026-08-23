#!/usr/bin/env bash
# Gate-2 all-53 acceptance run for sprint 2026-08-20-defs-boundary-idioms
# (issue #27). Uses measure_actual_production_all_rows.py, a corrected copy
# of docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/
# measure_actual_production.py per this sprint's log doc §7: the original's
# --current branch bundles (a) matching production's unconditional
# recognized_by_registered_rule computation (the documented, general
# --current trap -- kept) with (b) restricting the whole measured
# population to B1-winner rows only, which would exclude this item's
# entire affected population (this item's family-3 widening touches rows
# recognized by BASELINE is_definitions_heading, not body-derived B1 rows).
# The corrected script drops (b): every corpus row is measured, capture()
# still runs with current=True on both sides (the real trap, preserved).
#
# Diffing uses diff_gate2.py (no hard-coded certified-ledger hash -- there
# is no pre-existing certificate for this item's delta; P-R11: run, then
# adjudicate).
set -euo pipefail
REPO=$(git rev-parse --show-toplevel); cd "$REPO"
BASE_SHA=d660849163df9c46aae97157424ba0bb5420ffce   # pre-fix commit, this branch

git cat-file -e "${BASE_SHA}^{commit}"

PY=/Users/nerya/LexGraph/backend/.venv/bin/python
SCRIPTS_DIR=docs/sprint/sprints/2026-08-20-defs-boundary-idioms-scripts
MEASURE="$SCRIPTS_DIR/measure_actual_production_all_rows.py"
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad

RUN="$SCRIPTS_DIR/run"
mkdir -p "$RUN/current" "$RUN/baseline-src" "$RUN/baseline" "$RUN/compare"
printf 'artifacts: %s\n' "$RUN"

git archive "$BASE_SHA" | tar -x -C "$RUN/baseline-src"

# CURRENT = post-fix working tree (this item's regex widening already lands)
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$REPO" \
  --out "$RUN/current" --current

# BASELINE = archived pre-fix source, real production calling convention
# (--current on both sides -- the real trap; population is now the full
# corpus, not just B1 winners, per the correction above)
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$RUN/baseline-src" \
  --out "$RUN/baseline" --current

echo "=== current/summary.json ==="
cat "$RUN/current/summary.json"
echo "=== baseline/summary.json ==="
cat "$RUN/baseline/summary.json"

PYTHONPATH=.:backend "$PY" "$SCRIPTS_DIR/diff_gate2.py"

echo "GATE2_RUN_COMPLETE"
