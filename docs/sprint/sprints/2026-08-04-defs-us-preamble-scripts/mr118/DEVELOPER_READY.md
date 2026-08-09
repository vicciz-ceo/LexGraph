# M-R121 Developer-ready uniform source-truth contract

Production is read-only at this checkpoint. M-R121 supersedes the M-R120
586-key proposal. The binding normalized/stripped B1 population remains
193,830 rows, SHA-256
`851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a`.

## Binding evidence

- `qa/mr121/source_adjudication.jsonl` contains 296 canonical audit records:
  124 disputed decisions, 92 archived-baseline closure changes, 64 bounded
  WIP-to-runtime changes, and 16 same-row adjustments outside the original
  dispute set. It has zero unclassified decisions or irreducible ambiguities;
  SHA-256 is
  `d62b2ab9daf0fc9f6eabd486921005bdd2e336855596478914f0ef22676b6d95`.
- `qa/mr121/state_closure_adjudication.jsonl` is the independent state-slice
  control: 97 records, zero ambiguity, SHA-256
  `1e766ce6d5f9a2d0d1feb22c872d640997aaee28456e0fb72cf0baa1a9b56d67`.
- `qa/mr121/cross_audit_reconciliation.jsonl` source-adjudicates all 13 keys
  behind the state-only 569 versus complete 556 projection; SHA-256 is
  `dc713847b410749a4e7dc8f2725b685e084b6e919e14c3b80fe405c244fb9f16`.
- `qa/mr121/expected_changed.jsonl` is the complete certificate:
  **556 = 552 removals + 4 additions**, canonical SHA-256
  `17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`.
  Two independent methods emitted byte-identical direction-aware ledgers.
- The archived baseline has 592,694 records and byte SHA-256
  `f065d8ee838effaba250ea13fb9c234904b3a63985893f0a921d856bc396b3f8`;
  the comparison harness rejects any other baseline before comparison.
- Current WIP is intentionally not certified: 534 changes (530 removals,
  4 additions), canonical SHA-256
  `a04b609544f4d48ad114d6442534ef5aa75c2ecd06fdca024afcc3a7bbb6634e`,
  with 43 required certificate keys missing and 21 actual extras.

## Required production semantics

1. Keep B1 winner membership and raw-source carriage unchanged. Evaluate every
   like-delimited raw quote occurrence for the emitted term. An exact occurrence
   owns its arbitrary local payload; any independent substantive occurrence
   preserves the tuple.
2. Terminal-punctuation/whitespace normalization may rescue a dotted emitted
   term only through an explicit direct, alias/name, or forwarding relation.
   When no exact occurrence exists, use the same normalized tolerant matching.
   Raw text with no valid like-delimited match fails open and preserves,
   including malformed or mixed delimiters.
3. Structural punctuation, markers, coordination, bare citations, and leading
   legislative history are not substantive payload. Bound quote-continuation
   detection to the numbered continuation it governs; do not infer validity
   from quote parity across the whole source row.
4. Preserve explicit direct post-quote relations, including dash/newline and
   colon/enumerated subject-before-`means`/`includes` shapes. Preserve bounded
   pre-quote alias/name introductions and jurisdiction-neutral forwarding
   introductions, including reciprocal `designated, respectively, as` lists.
   Do not use source, row, term, content, or jurisdiction exceptions.
5. Retain the plural-anaphora repair, bounded to the occurrences owned by its
   matched group. It replaces each owned stale payload with the shared relation
   but never suppresses an independent substantive definition. For the two
   Indiana rows, emit `utility` and `works` once each with exactly
   `have the meaning set forth for those terms in section 8.1 of this chapter.`
6. Preserve first-wins tuple text and scope. This change classifies eligibility;
   it does not rewrite a retained baseline tuple or expand B1 dispatch.

## Exact Developer write set

The only authorized production file is:

- `backend/app/definition_links/rules/us_body_preamble_b1.py`

Port the generic runtime prototype from `measure_mr110_candidate_stream.py`
into that file, retain the plural repair, and keep the module at or below 300
lines. `us_profile.py`, `pipeline.py`, registry order, tests, ledgers, and docs
are read-only for Developer. No identity allowlist, term vocabulary, corpus
exception, jurisdiction exception, global normalization map, or generic
dispatch expansion is authorized.

## Focused gates

Run from the repository root. Before implementation, the M-R121 pair is
intentionally **25 failed / 21 passed**:

```bash
PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/pytest -q \
  backend/tests/unit/test_mr121_b1_source_truth_red.py \
  backend/tests/integration/test_mr121_b1_source_truth_persistence_red.py
```

After the one-file implementation, require **46 passed**, then require the
legacy raw-source control and runtime prototype to remain green:

```bash
PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/pytest -q \
  backend/tests/unit/test_mr118_qa_raw_provenance.py \
  backend/tests/integration/test_mr118_qa_raw_provenance_persistence.py

PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python \
  docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/measure_mr110_candidate_stream.py \
  --self-check
```

Required results are **13 passed** and **78 passed**. Do not run the all-53
measurement until all three focused gates are green.

## Single all-53 acceptance run

After the focused gates pass, run current production once and compare it to the
pinned archived baseline and certificate:

```bash
(
set -euo pipefail

MR121_REPO=$(git rev-parse --show-toplevel)
cd "$MR121_REPO"
git cat-file -e '5753e11^{commit}'

MR121_PYTHON=/Users/nerya/LexGraph/backend/.venv/bin/python
MR121_MEASURE=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/measure_actual_production.py
MR121_CERT=docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/mr121/expected_changed.jsonl
MR121_SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad

MR121_RUN=$(mktemp -d /tmp/mr121-acceptance.XXXXXX)
MR121_CURRENT="$MR121_RUN/current"
MR121_BASELINE_SRC="$MR121_RUN/source-5753e11"
MR121_BASELINE_OUT="$MR121_RUN/baseline"
MR121_COMPARE="$MR121_RUN/compare"
mkdir -p "$MR121_CURRENT" "$MR121_BASELINE_SRC" \
  "$MR121_BASELINE_OUT" "$MR121_COMPARE"
printf 'M-R121 artifacts: %s\n' "$MR121_RUN"

git archive 5753e11 | tar -x -C "$MR121_BASELINE_SRC"

PYTHONPATH=.:backend "$MR121_PYTHON" "$MR121_MEASURE" \
  --snapshot "$MR121_SNAPSHOT" --source-root "$MR121_REPO" \
  --out "$MR121_CURRENT" --current

PYTHONPATH=.:backend "$MR121_PYTHON" "$MR121_MEASURE" \
  --snapshot "$MR121_SNAPSHOT" --source-root "$MR121_BASELINE_SRC" \
  --members "$MR121_CURRENT/members.jsonl" --out "$MR121_BASELINE_OUT"

MR121_BASELINE_COUNT=$(
  wc -l < "$MR121_BASELINE_OUT/records.jsonl" | tr -d '[:space:]'
)
MR121_BASELINE_SHA256=$(
  shasum -a 256 "$MR121_BASELINE_OUT/records.jsonl" | awk '{print $1}'
)
test "$MR121_BASELINE_COUNT" = 592694
test "$MR121_BASELINE_SHA256" = \
  f065d8ee838effaba250ea13fb9c234904b3a63985893f0a921d856bc396b3f8

PYTHONPATH=.:backend "$MR121_PYTHON" "$MR121_MEASURE" \
  --compare --out "$MR121_COMPARE" \
  --baseline "$MR121_BASELINE_OUT/records.jsonl" \
  --current-records "$MR121_CURRENT/records.jsonl" \
  --certified "$MR121_CERT"

cat "$MR121_CURRENT/summary.json"
cat "$MR121_BASELINE_OUT/summary.json"
cat "$MR121_COMPARE/summary.json"

rm -rf -- "$MR121_RUN"
)
```

The printed `MR121_RUN` directory retains all current, baseline, and comparison
artifacts if any check fails. Successful comparison displays all three
summaries, then removes only that explicit temporary root.
The current run must reproduce 193,830 members and the pinned membership hash.
The archived baseline run must reproduce 592,694 records and the pinned
`f065d8ee…b3f8` records hash before comparison; it must use the current run's
exact `members.jsonl`, not a separately selected population.
The comparison must report exactly 556 changed, 552 removed, 4 added, zero
missing, zero extra, and equal actual/certificate hashes of
`17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`.
