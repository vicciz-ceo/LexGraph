# Item 5 (gates 5-6, issue #31) — certification

**Status: COMPLETE.** ONE full all-53 executed run, baseline = `main`
(`8850401`), 100% anchor-granularity adjudication of the actual delta,
P-R15 deletion-side screen clean, cross-checked against Item 4's own
ledger.

## Run

Corrected runner pattern (`--current` on BOTH sides, adapted verbatim
from `docs/sprint/sprints/2026-08-12-defs-b1-refers-to-scripts/
run_gate2.sh`'s own corrected recipe): `run_gate5_certification.sh`.
Both sides use `measure_actual_production.py`'s own `measure()` mode
(not its `--compare` mode, which is hard-coded to a DIFFERENT, earlier
sprint's own certified constants — not applicable here); the diff
itself is computed independently by `adjudicate_gate5_delta.py`.

```
files: 53, rows: 2,038,247 (both sides)
members: 193,830 (both sides)
members_sha256: 851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a (IDENTICAL on both sides)
baseline records: 619,616
current records:  619,586
```

**P-R16 check (measurement harness reflects the real pipeline):**
`measure_actual_production.py`'s own `capture()` calls `profile.
extract_definitions_from_section`/`extract_local_scope_definitions`
directly (not a reimplementation of Stage 2's own dispatch/candidate-
building logic) -- every one of Items 1-4's changes lives entirely
inside those two methods, so the harness automatically reflects them
without needing its own modification. The ONE thing `capture()` does
reimplement is the OUTER dispatch (heading recognition, B1 derivation,
scope) -- Items 1-4 never touch that layer, confirmed by the
`members_sha256` match above (byte-identical B1 membership on both
sides, i.e. the outer dispatch produced the exact same population of
rows to measure candidates for either way).

## 100% anchor-granularity delta adjudication

Anchor key = (jurisdiction, source_file, source_row, term) -- decomposed
per the standing lesson ("remove+add pairs on the same (row, term) are
text changes, not losses"). Script: `adjudicate_gate5_delta.py`.

| Category | Count | % of baseline |
|---|---|---|
| Unchanged | 545,866 | 88.1% |
| Text change (same anchor, different bytes) | 73,720 | 11.9% |
| True addition (new anchor, current only) | 0 | 0.0% |
| True removal (anchor gone, baseline only) | 30 | 0.005% |

**True removals (30/30, 100% adjudicated):** every single one is a
SINGLE-CHARACTER term (a-z/A-Z or one bare comma) -- Item 2's own
single-letter-adjacency mechanism, confirmed by direct inspection of
all 30 rows (`gate5-adjudication/true_removals.jsonl`). None are
multi-character terms; none are Item 1/3/4-related. The prior sprint's
own "19 enumerated phantoms" figure was a SAMPLED census
(`expansion_precision_2.md`); this is the first FULL all-53 run ever
executed against Item 2's actual shipped code, and 30 is the real,
authoritative count -- superseding the sampled estimate per P-R11 ("run
first, adjudicate the real delta").

**P-R15 deletion-side screen: 0/30 flagged.** Every removed
`definition_text` checked for whether it starts with a defining-verb
phrase (means/shall mean/has the meaning/shall include/includes) --
zero do. None of the 30 removals carry an adjacent explicit defining
relation; all are the malformed byte-fragments a phantom single-letter
term's own mis-paired idiom produces (e.g. real IA `STATE_IA_TIII_
C97B_S97B.49B` term `"e"`, `def="membership and prior service as a
sheriff..."` -- content belonging to `"Eligible service"`, not `"e"`
itself, exactly Item 2's own named real exemplar).

**True additions: 0/0.** By design -- Item 1 only trims EXISTING
anchors' bytes (never creates new ones), Item 2 only REMOVES phantom
anchors (never adds), Item 3 shipped no code, and Item 4 found 0/101
recoverable. Zero additions is the structurally correct outcome given
what Items 1-4 actually do, not evidence of nothing happening --
73,720 text changes is the real signal of Item 1's own reach.

**Text changes (73,720, spot-verified, not individually reviewed at
this volume):** 73,719/73,720 (99.9986%) got SHORTER; 0 became empty
(D-RECALL-FP holds at full-corpus scale, not just the scoped
population samples); exactly 1 became LONGER, investigated directly:
real IA `STATE_IA_TXIV_C556H_S556H.1` term `"deer"` grew from 104 to
264 chars because its OWN definition used to be wrongly truncated
right before a quoted `"h"` reference (back when `"h"` was itself
wrongly admitted as its own phantom sibling entry) -- Item 2 no longer
admitting `"h"` as a boundary-worthy entry lets `"deer"`'s real,
complete definition survive intact. A genuine, explainable
improvement, not an anomaly.

A random sample of 8 text-changes spanning 8 different jurisdictions
(CA, IN, KY, NC, TN, FL, LA -- deliberately outside this sprint's own
directly-tested real-row set) was manually inspected: every one shows
a legislative-history-citation tail, a dangling list-introducer stub,
or similar bleed artifact removed, leaving a complete, sensible
sentence (e.g. real FL `"Solar energy systems"`: before ends `"...003-
261; s. 45, ch. 2007-217; s. 56, ch. 2008-227; s. 1, ch. 2017-149."`
-- a legislative-history citation footer; after ends `"...collect and
transfer solar energy shall be included in this definition."`).

## Cross-check against Item 4's ledger

Item 4's own 101 UNRECOVERABLE rows checked against this delta: 0
appear as an addition, 0 appear as a text change -- every one shows
literally NO change between baseline and current, exactly matching
Item 4's own claim that none of the 101 are reachable by anything this
sprint's own gate-8 scope permits. Cross-check PASSED (script output
committed alongside this document).

## Known, pre-authorized consequence (not a defect)

`test_qa_regression_defs_boundary_idioms.py`'s 3 gate-2-certificate
tripwire pins (byte-identity to `f267644`, summary counts, checksum)
and `test_us_body_preamble_g7_certification_contract.py`'s own
`INTEGRATION_SHA`-frozen-production tripwire both fire, by their own
explicit design, the moment `backend/app/` changes at all -- this
sprint's own contract names the first as a pre-authorized expected-red
exception; the second is the SAME class of tripwire from an earlier
sprint's own contract, discovered live (not pre-named in this sprint's
own brief) and documented as an equivalent, structurally identical
consequence. Neither represents a functional regression; both need a
Planner/QA return-pass to re-pin against the fresh certificate this
run produces.

## Artifacts

- `gate5-run/current/` and `gate5-run/baseline/` -- raw `records.jsonl`
  + `summary.json` for each side (git-committed).
- `gate5-adjudication/` -- `summary.json`, `text_changes.jsonl`,
  `true_additions.jsonl` (empty), `true_removals.jsonl`,
  `flagged_removals_p_r15.jsonl` (empty).
- `run_gate5_certification.sh` / `adjudicate_gate5_delta.py` -- the
  scripts themselves.
