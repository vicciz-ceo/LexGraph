#!/usr/bin/env bash
# Item 5 (gates 5-6) all-53 certification run for sprint
# 2026-08-23-defs-debt-31. Recipe adapted VERBATIM from the corrected
# pattern in docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/
# run_gate2.sh (per this sprint's own contract instruction: "Use the
# corrected runner pattern... --current on BOTH baseline and current
# sides -- flag asymmetry manufactures phantom deltas"). Only the
# baseline SHA and output paths change.
set -euo pipefail
REPO=$(git rev-parse --show-toplevel); cd "$REPO"
BASE_SHA=8850401   # main, per this sprint's own contract
git cat-file -e "${BASE_SHA}^{commit}"

PY=/Users/nerya/LexGraph/backend/.venv/bin/python
MEASURE=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/measure_actual_production.py
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad

RUN=docs/sprint/sprints/2026-08-23-defs-debt-31-scripts/gate5-run
mkdir -p "$RUN/current" "$RUN/baseline-src" "$RUN/baseline"
printf 'artifacts: %s\n' "$RUN"

if [ ! -d "$RUN/baseline-src/backend" ]; then
  git archive "$BASE_SHA" | tar -x -C "$RUN/baseline-src"
fi

if [ ! -f "$RUN/current/summary.json" ]; then
  echo "=== running CURRENT (this worktree, Items 1-4 landed) ==="
  PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$REPO" \
    --out "$RUN/current" --current
else
  echo "=== CURRENT already done, skipping ==="
fi

if [ ! -f "$RUN/baseline/summary.json" ]; then
  echo "=== running BASELINE (archived $BASE_SHA, --current on both sides) ==="
  PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$RUN/baseline-src" \
    --out "$RUN/baseline" --current
else
  echo "=== BASELINE already done, skipping ==="
fi

echo "=== current/summary.json ==="
cat "$RUN/current/summary.json"
echo "=== baseline/summary.json ==="
cat "$RUN/baseline/summary.json"
echo "GATE5_RUN_COMPLETE"
