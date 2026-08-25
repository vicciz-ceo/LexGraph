#!/usr/bin/env bash
# INTEGRATION_SHA re-pin + G7 evidence regeneration for sprint
# 2026-08-23-defs-debt-31 (issue #31), Planner return-pass 2, qa-fail
# cycle 1. Follows the established recipe: commit 816f63d's original
# run_g7_repin.sh (sprint 2026-08-12-defs-b1-refers-to), reused verbatim in
# spirit by 8cfdb0f (2026-08-20-defs-boundary-idioms) and inline by 5b48795
# (this sprint's own return-pass 1, which re-pinned 79e34c8 -> 5d2093a
# without committing its own copy of this script). This copy re-pins
# 5d2093a -> 457045b (Items 6-7's qa-fail-cycle-1 fixes) and is committed
# BEFORE the long run starts (~50-60 min: Q-D1 ~51min, Q-D2 ~8min per the
# prior run's own elapsed numbers), per the machine-sleep relaunch
# discipline in the sprint log: the pin update lands first (already done in
# qa_g7_common.py), then this script is the single relaunch command if the
# session dies mid-run -- run_g7_certification.py has no internal
# checkpointing, so relaunch means a full idempotent re-run, not a resume.
set -euo pipefail
REPO=$(git rev-parse --show-toplevel); cd "$REPO"

PY=/Users/nerya/LexGraph/backend/.venv/bin/python
SCRIPTS=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad
OUT=docs/sprint/sprints/2026-08-23-defs-debt-31-scripts/g7-out
EVIDENCE="$SCRIPTS/g7-certification-evidence"

mkdir -p "$OUT"

echo "G7_REPIN_START $(date -u +%Y-%m-%dT%H:%M:%SZ)"

PYTHONPATH=.:backend "$PY" -u "$SCRIPTS/run_g7_certification.py" --snapshot "$SNAPSHOT" --out "$OUT"

PYTHONPATH=.:backend "$PY" - "$OUT" "$EVIDENCE" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, "docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts")
from qa_d1_measure import export_compact_evidence

out = Path(sys.argv[1])
evidence = Path(sys.argv[2])
export_compact_evidence(out, evidence)
print("EXPORT_COMPACT_EVIDENCE_DONE")
PYEOF

echo "G7_REPIN_COMPLETE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
