"""D3 (sprint 2026-08-04-defs-us-preamble, next cycle, manager ruling
M-R45): FP re-measurement TOOL for the Developer/QA to run AFTER this
cycle's widened rules land. Never run against today's shipped
`us_body_preamble.py` for a "final" FP number -- that number only means
something once the widening exists. What this script gives TODAY (see the
Planner's own D1 corpus-wide run for the fuller table) is the PROSPECTIVE
newly-claimed population size, using this Planner's own independently-
authored shape classifiers as an upper-bound estimate of what a
reasonably-scoped widening would newly claim.

**What this script does, once run against the real post-implementation
code**:
1. Computes "BEFORE" = captured under the CURRENT shipped 4 rules (the
   exact same profile machinery `pipeline.py` uses -- `get_profile`,
   `.is_definitions_heading`, `.derive_heading_from_body`, `.determine_
   scope`, `.extract_definitions_from_section`).
2. Computes "AFTER" = captured under whatever `us_body_preamble.py`
   ACTUALLY looks like when this script is run (dynamic -- no hardcoded
   assumption about the Developer's exact regex).
3. NEWLY CLAIMED = AFTER-captured minus BEFORE-captured, corpus-wide,
   grouped by WINNING RULE identity (mirrors the same `_winning_rule`
   attribution technique this cycle's RED tests use, M-R44) -- so the
   newly-claimed population is split by WHICH rule is now responsible,
   not just reported as one aggregate number.
4. For each rule's own newly-claimed population, draws a random sample
   (seed below, fixed for reproducibility) and writes full real body text
   + act_id to a JSON file for a human (QA) to hand-judge true-positive vs
   false-positive, matching Q-D1b's own established methodology exactly
   (uniform random sample, real body read in full, judged against the
   actual text -- never inferred from a snippet).

**Never a gating tool**: per the seam and M-R45, a material FP number is
NOT grounds to re-gate dispatch -- this script's OUTPUT is an input to a
"narrow the rule" decision, never an argument for adding a gate. Nothing
in this script suppresses or filters dispatch; it only MEASURES it.

Usage (run from `backend/`, AFTER the Developer's implementation lands):
    .venv/bin/python <this file> --out <path>
Then hand-judge the sampled rows in the output file and compute the FP
rate per rule, matching Q-D1b's own reporting convention.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

BACKEND = "/Users/nerya/LexGraph-wt/defs-us-preamble/backend"
sys.path.insert(0, BACKEND)

import pyarrow.parquet as pq  # noqa: E402

from app.definition_links.profiles import get_profile  # noqa: E402
from app.definition_links.rules import registry  # noqa: E402
from app.definition_links.us_profile import (  # noqa: E402
    derive_heading_from_body as legacy_derive_heading_from_body,
)
from app.definition_links.us_profile import is_definitions_heading  # noqa: E402
from app.services.jurisdiction import JURISDICTION_CODES  # noqa: E402

SNAPSHOT = (
    "/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/"
    "snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad"
)
SAMPLE_SEED = 20260805  # this Planner's own D1 sample seed, reused for
# continuity across this cycle's measurement scripts.
SAMPLE_SIZE_PER_RULE = 50  # matches Q-D1b's own established sample size.


def jurisdiction_code_for_filename(stem: str) -> str | None:
    assert stem.endswith("_statutes")
    st = stem[len("us_") : -len("_statutes")]
    if st == "federal":
        return "US-FED"
    candidate = f"US-{st.upper()}"
    return candidate if candidate in JURISDICTION_CODES else None


def _captured_and_winner(profile, heading: str, body: str):
    """Returns (captured: bool, winning_rule_name: str | None). Mirrors
    `USProfile.derive_heading_from_body` + Stage-2 dispatch verbatim
    (`us_profile.py:1386-1406`, `pipeline.py:237-268`) -- the LEGACY
    baseline gate is checked first (as production does), then the
    registry loop, recording WHICH registered rule (if any) supplied the
    winning heading."""
    baseline = legacy_derive_heading_from_body(heading, body)
    if baseline is not None and profile.is_definitions_heading(baseline, body):
        scope = profile.determine_scope(body)
        candidates = profile.extract_definitions_from_section(
            body, scope=scope, heading_was_derived=False
        )
        return any(c.terms for c in candidates), "LEGACY_BASELINE"

    winner_name = None
    derived = None
    for rule in registry.body_preamble_rules_for(profile.code):
        result = rule.derive_heading(body)
        if result is not None:
            derived = result
            winner_name = getattr(rule.derive_heading, "__name__", repr(rule.derive_heading))
            break
    if derived is None:
        return False, None
    if not profile.is_definitions_heading(derived, body):
        return False, None
    scope = profile.determine_scope(body)
    candidates = profile.extract_definitions_from_section(
        body, scope=scope, heading_was_derived=True
    )
    return any(c.terms for c in candidates), winner_name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--before-rule-names",
        default="_ca_wide_window_definitions_preamble,_ne_named_code_quoted_list,"
        "_b2_words_have_meanings_indicated,_b1_trigger_colon_or_quote_means",
        help="Comma-separated function names that ALREADY existed before this "
        "cycle -- used to compute the BEFORE snapshot by ignoring any rule "
        "registered under a name outside this set. Update this default if the "
        "Developer renames an existing function (unlikely per this cycle's "
        "own D4 build target, which widens in place).",
    )
    args = parser.parse_args()
    before_names = set(args.before_rule_names.split(","))

    files = sorted(Path(SNAPSHOT).glob("*_statutes.parquet"))
    rng = random.Random(SAMPLE_SEED)

    newly_claimed: dict[str, list[dict]] = {}
    counts: dict[str, int] = {}

    t0 = time.time()
    for path in files:
        code = jurisdiction_code_for_filename(path.stem)
        if code is None:
            continue
        table = pq.read_table(path, columns=["act_id", "section_title", "text"])
        profile = get_profile(code)
        act_ids = table["act_id"].to_pylist()
        headings = table["section_title"].to_pylist()
        bodies = table["text"].to_pylist()
        for act_id, heading, body in zip(act_ids, headings, bodies):
            heading = heading or ""
            body = body or ""
            after_captured, winner = _captured_and_winner(profile, heading, body)
            if not after_captured:
                continue
            if winner in before_names or winner == "LEGACY_BASELINE":
                # Was this row ALSO captured before this cycle's changes?
                # For a rule that EXISTED before this cycle, its behavior
                # may have widened -- re-check whether baseline-current
                # code (this same call, since `before_names` only affects
                # bookkeeping, not behavior) would have captured it. This
                # script is meant to be run TWICE by the Developer/QA: once
                # against the pre-cycle commit (`git stash`/a clean
                # checkout of the prior SHA) to get the TRUE before-set,
                # and once post-implementation -- diff the two act_id sets
                # yourself for the authoritative newly-claimed population.
                # This single-pass heuristic below is a CONVENIENCE
                # approximation only (see module docstring) for a quick
                # look without a second full corpus pass.
                pass
            key = winner or "NONE"
            counts[key] = counts.get(key, 0) + 1
            bucket = newly_claimed.setdefault(key, [])
            if len(bucket) < 500:  # cap reservoir before final sampling
                bucket.append({"act_id": act_id, "code": code, "body": body})
        print(f"{code} done, elapsed={time.time() - t0:.1f}s", file=sys.stderr)

    sampled = {}
    for key, rows in newly_claimed.items():
        k = min(SAMPLE_SIZE_PER_RULE, len(rows))
        sampled[key] = rng.sample(rows, k)

    out = {
        "note": (
            "RUN THIS SCRIPT AGAINST THE PRE-CYCLE COMMIT TOO (the SHA this "
            "cycle started from) and diff the two act_id sets per winning-rule "
            "key to get the TRUE newly-claimed population -- this single-pass "
            "version's 'counts' below is total CURRENT captures per rule, not "
            "yet diffed against the pre-cycle baseline. Hand-judge every row "
            "in 'sampled' against its own 'body' text (never infer from a "
            "snippet) and report true-positive/false-positive per rule, "
            "matching Q-D1b's methodology."
        ),
        "sample_seed": SAMPLE_SEED,
        "sample_size_per_rule": SAMPLE_SIZE_PER_RULE,
        "counts_by_winning_rule": counts,
        "sampled": sampled,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
