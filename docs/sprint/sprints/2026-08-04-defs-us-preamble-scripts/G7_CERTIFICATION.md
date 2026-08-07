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
Q-D3 reads only Q-D1/Q-D2 canonical artifacts and fails closed on identity,
census, sums, partitions, gates, tuple uniqueness, population/sample/ledger
hashes, and sample membership.

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
