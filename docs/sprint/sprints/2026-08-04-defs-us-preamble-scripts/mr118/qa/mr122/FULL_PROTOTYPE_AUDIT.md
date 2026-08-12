# M-R122 full normalized runtime-prototype audit

Status: **PROVISIONAL PASS at Planner altitude; production remains read-only.** The
corrected runtime prototype was executed over the complete normalized B1
population and compared at persisted-record altitude with the reproducibly
archived `5753e11` baseline.

## Binding result

- Corpus: 53 files / 2,038,247 rows.
- B1 winners: 193,830 / `851e85dc…6af5a`.
- Archived baseline: 592,694 records / `f065d8ee…b3f8`.
- Corrected prototype: 592,334 records / `9e6e0196…2ca8`.
- Direction-aware delta: **368 = 364 removals + 4 additions**.
- Delta/certificate SHA-256: `49a9d3f71d124e19f085ded69d5fbaae269d8ecfc518cd8a9457a9d34e00933d`.
- Missing certified: 0. Extra actual: 0. `cmp -s`: 0.

The runtime proof uses production checkpoint `c2a8717`, planner prototype
`c65c57a8…d54e0f`, snapshot `301000fc…`, and archived baseline commit
`5753e118cc9311a09b367731594de0f0920dd2c1`. Exact machine-readable values
are in `full_prototype_summary.json`; the emitted delta is retained as
`full_prototype_changed.jsonl`.

## Why the 556 projection changed

The first full comparison of c2/prototype behavior with M-R121 exposed 207
keys. Raw-source adjudication closes every key:

| Family | Keys | Source decision |
|---|---:|---|
| Explicit post-quote relation | 185 | preserve; old removal invalid |
| Explicit pre-quote alias relation | 3 | preserve; old removal invalid |
| Closing quote hid nondefinition occurrence | 14 | remove after direction fix |
| Closing quote hid genuine definition | 5 | preserve after direction fix |

Thus 188 of the old 552 removals contradict M-R121's own direct/alias
preservation semantics. This is new raw-source evidence within the explicit
certificate-change exception; forcing 556 would knowingly delete definitions.
The corrected arithmetic is `556 - 188 = 368`.

`mismatch_inventory.jsonl` is the zero-residual source ledger. Every record
contains the full changed key, raw-row SHA, bounded source excerpt and hash,
old/corrected occurrence counts, deciding helper predicates, and direction on
both the production and certificate sides.

## Generic correction and controls

Only `backend/app/definition_links/rules/us_body_preamble_b1.py` is authorized
for the next Developer. A straight quote can open a numbered continuation only
when it is at physical line start (whitespace-only prefix since CR/LF) and its
following gap begins the marker. Visible content before the quote proves it is
a closer. The existing 6,000-character bounded lookback remains unchanged.

The same one-file port must source-order deduplicate exact `_groups()` tuples.
This second c2/prototype mismatch affects zero pinned-corpus keys: only the two
Indiana repair rows discover groups, one each. A novel dual-trigger law proves
that c2 otherwise emits each direct candidate twice.

Novel R8–R11 cases cover both directions and both altitudes: closing quote then
genuine definition, true line-start outer quotation fail-open, overlapping
trigger group uniqueness, and closing quote then questionnaire pseudo-entry.
At c2 the focused pair is 5 failed / 49 passed; under the prototype all six
direct/persistence suites are **86 passed**. No row IDs, terms, jurisdictions,
hashes, or exact corpus sentences occur in the correction logic.

## Reproduction

`measure_actual_production.py --current --prototype` applies
`default_preserve_runtime_patch()` inside the same persisted-record harness
used for production acceptance. The current run selects and hashes live B1
winners; the baseline invocation uses that exact `members.jsonl` against a
`git archive 5753e11` tree. The comparison refuses the baseline unless its
records hash is `f065d8ee…b3f8`, validates certificate count/directions/hash,
and fails on any missing or extra key. The complete shell recipe is in
`../../DEVELOPER_READY.md`.
