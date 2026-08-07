# Permanent G7 / D-PFP-400 certification

The one clean-checkout entrypoint is:

```sh
/Users/nerya/LexGraph/backend/.venv/bin/python \
  docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/run_g7_certification.py \
  --snapshot /Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad \
  --out /absolute/fresh-output-directory
```

The output directory is intentionally outside the repository.  It contains
`qd1_summary.json`, `qd2_summary.json`, `qd3_crosscheck.json`, the canonical
population stream, the 400-tuple sample, and the separate fallback byte ledger.
Never substitute `measure_fp_after_widening.py`: it remains approximate and
non-gating.

## Fixed inputs and fail-closed checks

The tools require snapshot `301000fc3465374ee0f23c3c6953a8a861e95cad`, exactly
53 `us_*_statutes.parquet` files, and exactly 2,038,247 parquet rows.  They also
require production integration `4fa9e7b368801757039091646e06a832620a3a2c` to be
an ancestor of `HEAD` and reject any later change under `backend/app`.

Q-D1 reads batches directly from the parquet files and calls the real production
normalization, profile, registry, extraction and first-wins persistence-dedup
seams.  BEFORE is the bare legacy heading/derivation/extraction path; AFTER is
the live profile and registry path.  It reports the binding row metrics by
jurisdiction and total; GA-after must be at least 2,794 and total `new_primary`
at least 23,617.  `new_fallback` is informational.

Q-D2 opens the files itself and builds the ratified broad quoted/unquoted
defining-verb denominator without importing Q-D1, its helpers, or its result.
It emits a temporary canonical candidate ledger keyed by stable
`(jurisdiction, source_file, source_row)` plus its count/hash. Q-D3 reads only
canonical artifacts and fails closed on candidate uniqueness/count/hash,
per-state and total sums, and `candidate_rows = already_captured + uncaptured`.
Quoted and unquoted components may overlap and are not a partition.

The Q-D1/Q-D2/Q-D3 `summary_hash` is SHA-256 over an explicit canonical
certification payload: every top-level field except `summary_hash` and
`run_metadata`. Runtime duration is diagnostic-only `run_metadata`, never
certifying. A QA rerun therefore must reproduce exact certification hashes
despite different elapsed durations; Q-D3 verifies Q-D1/Q-D2 with this same
explicit schema.

## D-PFP-400 sample allocation

The population is new AFTER definition tuples absent from BEFORE, keyed by
`(jurisdiction, source file, source row, term, definition_text, scope)` after
the live persistence first-wins `(article, sorted terms)` dedup rule.  Each
tuple has one `(jurisdiction, route, rule_family)` cell.

1. Rank every tuple with SHA-256 over the fixed snapshot id, integration SHA,
   and its canonical record.
2. Select a deterministic greedy set cover: at each step choose the first tuple
   covering the greatest number of still-uncovered labels across jurisdiction,
   route, and rule family; ties use the SHA rank then canonical tuple identity.
   This gives every non-empty label coverage without duplicate seats.
3. Allocate remaining seats across cells by proportional Hamilton allocation.
   Exhausted/undersized cells contribute all their remaining members; their
   unused share is redistributed by another deterministic Hamilton round.
4. Select each cell's lowest SHA-ranked remaining tuples.  The result is 400
   unique tuples, or the whole population if it is smaller.

Fresh QA must adjudicate every sample row against the source.  `false` means
the source does not genuinely define/forward the term, or the captured text is
not its defining statement.  Forwarding is genuine.  Boundary overrun of an
otherwise genuine definition belongs only in the informational fallback byte
ledger.  The sample starts `unreviewed`; this harness never claims P-FP PASS.
At 0 events in 400 the reported one-sided upper 95% bound is
`1 - 0.05^(1/400)` (about 0.75%), not a corpus-wide zero claim.

Q-D3 independently requires sample count `min(400, population_count)`, sample
uniqueness/membership and coverage of every non-empty jurisdiction, route, and
rule family. It requires the Planner's unreviewed ledger to be a one-to-one
immutable projection of the sample (including tuple/source/rule/route and
source-row hash) and byte-ledger count `min(50, fallback_population_count)`,
uniqueness, fallback-only population membership, and informational status.

## Exact clean-QA workflow

1. Run the entrypoint into a new outside-repository directory and compare its
   Q-D1/Q-D2/Q-D3 `summary_hash` values with committed compact evidence. Any
   mismatch fails; elapsed duration may differ only under `run_metadata`.
2. Copy the generated `dpfp400_adjudication_ledger.jsonl` to a QA-owned path.
   Do not overwrite Planner raw evidence. Retrieve each source row by its
   committed stable locator and source hash:

   ```sh
   /Users/nerya/LexGraph/backend/.venv/bin/python \
     docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/qa_retrieve_source.py \
     --snapshot /Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad \
     --source-file "$SOURCE_FILE" --source-row "$SOURCE_ROW" \
     --source-row-id "$SOURCE_ROW_ID" --source-row-sha256 "$SOURCE_ROW_SHA256"
   ```

3. QA preserves all immutable fields and sets each copied row to
   `qa_status: reviewed`, a nonempty `adjudicator`, and boolean
   `false_capture`/`ambiguous`. Boundary observations stay in the separately
   reported informational byte ledger.
4. Finalize the QA-owned copy (never the Planner ledger):

   ```sh
   /Users/nerya/LexGraph/backend/.venv/bin/python \
     docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/qa_finalize_adjudication.py \
     --sample /absolute/fresh-output-directory/dpfp400_sample.jsonl \
     --ledger /absolute/qa-owned-reviewed-ledger.jsonl \
     --verdict /absolute/qa-owned-dpfp400-verdict.json
   ```

The finalizer does not rewrite a ledger. It emits a canonical QA-owned verdict
with sample/ledger hashes, count, false/ambiguous counts and one-sided bound;
it exits 0/PASS only at zero false and zero ambiguous. Malformed, unreviewed,
identity-mismatched, false, or ambiguous ledgers fail closed. Planner leaves
its committed ledger unreviewed and makes no P-FP PASS claim.
