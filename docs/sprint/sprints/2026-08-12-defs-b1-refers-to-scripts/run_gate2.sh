#!/usr/bin/env bash
# Gate-2 all-53 acceptance run for sprint 2026-08-12-defs-b1-refers-to.
# Recipe originally taken verbatim from
# docs/sprint/sprints/2026-08-12-defs-b1-refers-to-log.md (Planner pass,
# "Gate 2: executed all-53 acceptance run"), with the RUN artifacts
# directory pointed at this sprint's scripts dir instead of /tmp per the
# Developer brief's instruction to write all outputs there.
#
# CORRECTED per docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/
# investigation.md: the Planner's original recipe ran CURRENT with
# --current but BASELINE without it. measure_actual_production.py's
# capture() gates recognized_by_registered_rule on that flag, but real
# production (pipeline.py:262-266) computes it unconditionally -- the
# --current-less baseline invoked a calling convention no production
# commit ever executed, producing a 4,255-record artifact delta that
# investigation.md traced to exactly one real record. Both sides must now
# pass --current. The script's own CLI forbids --current together with
# --members ("current run needs no --members; baseline run requires it"),
# so the baseline side determines its own membership via --current's
# registered_b1_winner() path rather than being restricted to CURRENT's
# members.jsonl; the script's built-in EXPECTED_MEMBERS_HASH check (only
# enforced under --current) fails loudly if that membership ever diverges.
set -euo pipefail
REPO=$(git rev-parse --show-toplevel); cd "$REPO"
BASE_SHA=5c3e75130c9e1d26c8e3448dc85691d12478889c   # qa_g7_common.INTEGRATION_SHA, pre-fix
git cat-file -e "${BASE_SHA}^{commit}"

PY=/Users/nerya/LexGraph/backend/.venv/bin/python
MEASURE=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/measure_actual_production.py
SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad

RUN=docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/run
mkdir -p "$RUN/current" "$RUN/baseline-src" "$RUN/baseline" "$RUN/compare"
printf 'artifacts: %s\n' "$RUN"

git archive "$BASE_SHA" | tar -x -C "$RUN/baseline-src"

# CURRENT = post-fix working tree (commit 86fccfb already lands the fix)
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$REPO" \
  --out "$RUN/current" --current

# BASELINE = archived pre-fix source, real production calling convention
# (--current on both sides; membership is self-determined and expected to
# match CURRENT's, enforced by the script's own EXPECTED_MEMBERS_HASH gate)
PYTHONPATH=.:backend "$PY" "$MEASURE" --snapshot "$SNAPSHOT" --source-root "$RUN/baseline-src" \
  --out "$RUN/baseline" --current

echo "=== current/summary.json ==="
cat "$RUN/current/summary.json"
echo "=== baseline/summary.json ==="
cat "$RUN/baseline/summary.json"
echo "GATE2_RUN_COMPLETE"
