# Provisional M-R122 full-prototype source-truth contract

Production is read-only at this checkpoint. M-R122 supersedes M-R121's
unexecuted 556-key projection after a full normalized runtime-prototype audit.
This is a Planner WIP handoff, not Developer authorization; the successor must
independently accept the source correction first.
The binding normalized/stripped B1 population remains
193,830 rows, SHA-256
`851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a`.

## Binding evidence

- `qa/mr122/mismatch_inventory.jsonl` classifies all 207 production-versus-
  M-R121 mismatches with raw-row hashes, excerpts, occurrence predicates, and
  source decisions; zero residual, SHA-256
  `707e6299a445a878e02302a0620735c87224804f5b7671321c87520106caad2c`.
- The old certificate wrongly removed 188 explicit definitions: 185 have
  direct post-quote relations and 3 have pre-quote alias relations. M-R121's
  own required semantics preserve them, so source evidence invalidates those
  keys. The remaining gap is one generic quote-direction defect: 14 missed
  removals and 5 false removals.
- `qa/mr121/expected_changed.jsonl` is the corrected certificate:
  **368 = 364 removals + 4 additions**, canonical SHA-256
  `49a9d3f71d124e19f085ded69d5fbaae269d8ecfc518cd8a9457a9d34e00933d`.
- The archived baseline has 592,694 records and byte SHA-256
  `f065d8ee838effaba250ea13fb9c234904b3a63985893f0a921d856bc396b3f8`;
  the comparison harness rejects any other baseline before comparison.
- Production checkpoint `c2a8717` emits 359 changes (355 removals, 4
  additions): exactly 14 corrected removals missing and 5 invalid removals
  extra. The corrected runtime prototype closes those 19 keys generically.

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
   legislative history are not substantive payload. A nearest prior straight
   quote opens a numbered continuation only when its physical-line prefix is
   whitespace-only and the following gap starts the numbered marker. A visibly
   closing quote never suppresses the next independent occurrence. Never infer
   validity from whole-row quote parity.
4. Preserve explicit direct post-quote relations, including dash/newline and
   colon/enumerated subject-before-`means`/`includes` shapes. Preserve bounded
   pre-quote alias/name introductions and jurisdiction-neutral forwarding
   introductions, including reciprocal `designated, respectively, as` lists.
   Do not use source, row, term, content, or jurisdiction exceptions.
5. Retain the plural-anaphora repair, bounded to the occurrences owned by its
   matched group. Deduplicate identical discovered groups in source order. It
   replaces each owned stale payload with the shared relation but never
   suppresses an independent substantive definition. For the two Indiana rows,
   emit `utility` and `works` once each with exactly
   `have the meaning set forth for those terms in section 8.1 of this chapter.`
6. Preserve first-wins tuple text and scope. This change classifies eligibility;
   it does not rewrite a retained baseline tuple or expand B1 dispatch.

## Exact Developer write set

The only authorized production file is:

- `backend/app/definition_links/rules/us_body_preamble_b1.py`

Change only `_quote_occurrences.continuation` and `_groups`: port the physical-
line-start opener check verbatim and source-order deduplicate identical groups.
Keep the module at or below 300 lines. `us_profile.py`, `pipeline.py`, registry
order, tests, ledgers, and docs are read-only for Developer. No identity
allowlist, term vocabulary, corpus/jurisdiction exception, global normalization
map, or dispatch expansion is authorized.

The continuation helper boundary is verbatim:

```python
previous = text.rfind('"', max(0, match.start() - 6000), match.start())
if previous < 0:
    return False
line_start = max(text.rfind("\n", 0, previous), text.rfind("\r", 0, previous)) + 1
if text[line_start:previous].strip():
    return False
return re.match(r'\s*\([A-Za-z0-9]+\)\s+', text[previous + 1 : match.start()]) is not None
```

At `_groups` return, iterate the existing group tuples in discovery order,
append only the first occurrence of each exact tuple to a list, and return that
list as a tuple. Do not alter matching, spans, or relationship text.

## Focused gates

Run from the repository root. At `c2a8717`, the pair is intentionally
**5 failed / 49 passed**:

```bash
PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/pytest -q \
  backend/tests/unit/test_mr121_b1_source_truth_red.py \
  backend/tests/integration/test_mr121_b1_source_truth_persistence_red.py
```

After the one-file implementation, require **54 passed**, then require the
legacy raw-source control and runtime prototype to remain green:

```bash
PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/pytest -q \
  backend/tests/unit/test_mr118_qa_raw_provenance.py \
  backend/tests/integration/test_mr118_qa_raw_provenance_persistence.py

PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python \
  docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/measure_mr110_candidate_stream.py \
  --self-check
```

Required results are **13 passed** and **86 passed**. Do not run the all-53
measurement until all three focused gates are green.

Planner's production-read-only corpus proof uses the same measurement command
below with `--prototype` added beside `--current`. That mode applies
`default_preserve_runtime_patch()` inside the persisted-record harness; it does
not modify `backend/app`. Developer acceptance omits `--prototype` and measures
the one-file production implementation.

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
The comparison must report exactly 368 changed, 364 removed, 4 added, zero
missing, zero extra, and equal actual/certificate hashes of
`49a9d3f71d124e19f085ded69d5fbaae269d8ecfc518cd8a9457a9d34e00933d`.
