#!/usr/bin/env bash
# INTEGRATION_SHA re-pin + G7 evidence regeneration for sprint
# 2026-08-12-defs-b1-refers-to, per the trap named in the sprint contract
# and docs/sprint/sprints/2026-08-12-defs-b1-refers-to-log.md ("INTEGRATION_SHA
# re-pin trap"). Procedure follows the recorded precedent in commit b8d4c45
# ("fix(g7): re-pin INTEGRATION_SHA after the shared-extraction fix,
# regenerate evidence"): the pin must be updated FIRST (already done in
# qa_g7_common.py -> 86fccfb1d2d6e3bcf93899b67ac97b71ed30d425), then run
# run_g7_certification.py (Q-D1 -> independent Q-D2 -> Q-D3) into a scratch
# --out, then export_compact_evidence(out, evidence) writes the canonical
# compact evidence into the checked-in g7-certification-evidence/ dir.
set -euo pipefail
REPO=$(git rev-parse --show-toplevel); cd "$REPO"

PY=/Users/nerya/LexGraph/backend/.venv/bin/python
SCRIPTS=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad
OUT=docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/run/g7-out
EVIDENCE="$SCRIPTS/g7-certification-evidence"

mkdir -p "$OUT"

PYTHONPATH=.:backend "$PY" "$SCRIPTS/run_g7_certification.py" --snapshot "$SNAPSHOT" --out "$OUT"

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

echo "G7_REPIN_COMPLETE"
