# M-R121 final independent audit and byte reconciliation

## Binding result

The independently composed M-R121 v2 ledger converges byte-for-byte with the separately generated reviewer v2 ledger.

- Final count: **556**
- Removals: **552**
- Additions: **4**
- Canonical SHA-256: **`17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`**
- Durable canonical artifact: `expected_changed.jsonl`
- Independent and reviewer builds: separately frozen before comparison
- `cmp -s` exit: **0**
- Bytes: **673,332** each
- Full direction-aware key-set differences: **0 independent-only, 0 reviewer-only**
- Canonical-line failures: 0
- Sort-order failures: 0
- Duplicate exact keys: 0
- Ambiguous decisions: 0
- Unclassified decisions: 0

The byte comparison was run only after the independent v2 artifact had been constructed and frozen.

## Durable audit artifacts

- `cross_audit_reconciliation.jsonl`: 13 exact source decisions; SHA-256 `dc713847b410749a4e7dc8f2725b685e084b6e919e14c3b80fe405c244fb9f16`.
- `state_closure_adjudication.jsonl`: corrected 97-key state/closure audit; SHA-256 `1e766ce6d5f9a2d0d1feb22c872d640997aaee28456e0fb72cf0baa1a9b56d67`.
- `STATE_CLOSURE_AUDIT.md`: state correction, counts, and 569-key state-only projection.
- `expected_changed.jsonl`: independently converged final 556-key ledger.
- `FINAL_AUDIT.md`: this report.

The v1 hashes remain below for audit history only; no v1 ledger is binding.

## Pinned source verification

All source inspection used snapshot `301000fc3465374ee0f23c3c6953a8a861e95cad`.

| Source | Row | Exact source-row ID | Section | Raw text SHA-256 |
|---|---:|---|---|---|
| `us_dc_statutes.parquet` | 2644 | `STATE_DC_T38_C28A_S38-2851.02` | § 38-2851.02 | `3f61536a870b00671c68ef3539e5f96ee991d48906846d32506ff47d1d4af147` |
| `us_federal_statutes.parquet` | 7066 | `USC_T42_C149_S16014` | 42 U.S.C. § 16014 | `a76a3e30336b6bf21b30a7cb99da74ecbe9fcbaaea6a31142fd482421890dfd0` |

For both rows, positional retrieval and exact `act_id` filtering returned the same raw text.

## The 13 exact adjudications

Every input key is a baseline `removed` record. Every M-R121 decision is `preserve`, with binding direction `drop_old_removal` and `expected_ledger=false`.

The DC source has two explicit shared forwarding introductions:

- `The following terms shall have the same meaning as provided in § 38-2901 :`
- `The following terms shall have the same meaning as provided in § 38-2905 :`

The federal source has one explicit alias-list introduction:

- `There is established in the Department 2 separate accounts, which shall be known as the—`

| # | Exact source-row ID | Exact term | Raw governing relation | Direction |
|---:|---|---|---|---|
| 1 | `STATE_DC_T38_C28A_S38-2851.02` | `Adult education` | same meaning as provided in § 38-2901 | removed → preserve; drop old removal |
| 2 | `STATE_DC_T38_C28A_S38-2851.02` | `Alternative program` | same meaning as provided in § 38-2901 | removed → preserve; drop old removal |
| 3 | `STATE_DC_T38_C28A_S38-2851.02` | `At-risk` | same meaning as provided in § 38-2901 | removed → preserve; drop old removal |
| 4 | `STATE_DC_T38_C28A_S38-2851.02` | `At-risk high school over-age supplement` | same meaning as provided in §§ 38-2901 and 38-2905 | removed → preserve; drop old removal |
| 5 | `STATE_DC_T38_C28A_S38-2851.02` | `Elementary ELL` | same meaning as provided in § 38-2901 | removed → preserve; drop old removal |
| 6 | `STATE_DC_T38_C28A_S38-2851.02` | `Level 1: Special Education` | same meaning as provided in § 38-2905 | removed → preserve; drop old removal |
| 7 | `STATE_DC_T38_C28A_S38-2851.02` | `Level 2: Special Education` | same meaning as provided in § 38-2905 | removed → preserve; drop old removal |
| 8 | `STATE_DC_T38_C28A_S38-2851.02` | `Level 3: Special Education` | same meaning as provided in § 38-2905 | removed → preserve; drop old removal |
| 9 | `STATE_DC_T38_C28A_S38-2851.02` | `Level 4: Special Education` | same meaning as provided in § 38-2905 | removed → preserve; drop old removal |
| 10 | `STATE_DC_T38_C28A_S38-2851.02` | `Limited English Proficient/Non-English Proficient` | same meaning as provided in §§ 38-2901 and 38-2905 | removed → preserve; drop old removal |
| 11 | `STATE_DC_T38_C28A_S38-2851.02` | `Special Education Level 2 ESY` | same meaning as provided in § 38-2905 | removed → preserve; drop old removal |
| 12 | `STATE_DC_T38_C28A_S38-2851.02` | `Special Education Level 3 ESY` | same meaning as provided in § 38-2905 | removed → preserve; drop old removal |
| 13 | `USC_T42_C149_S16014` | `Standby Support Program Account` | two separate accounts “shall be known as the—” | removed → preserve; drop old removal |

These decisions are jurisdiction-neutral applications of explicit forwarding and alias/name semantics. They use no identity-specific or content-vocabulary exception.

## State correction and the 569 projection

The original 570 state projection contained one stale decision. The West Virginia item-(5) term beginning `This power of attorney is effective for a period not to exceed one year` is form text, but its raw occurrence opens with `“` (U+201C) and closes with `"` (U+0022). It has no like-delimiter matched occurrence, so raw mixed-delimiter fail-open preservation binds before removal.

State audit v2 flips only that record:

- v1: safe removal, included;
- v2: preserve/reject runtime removal, excluded.

No exact key or ordering changed across the 97 state records. The corrected state-only projection is:

`586 - 18 rejected M-R120 removals + 1 new Hawaii removal = 569`

The 13 decisions above then produce:

`569 - 13 = 556`

## Colorado/West Virginia v1 swap resolution

The first frozen independent and reviewer ledgers both had 557 records but failed byte comparison:

| Artifact | Count | SHA-256 | Unique full key |
|---|---:|---|---|
| Independent v1 | 557 | `0bfa734850d863b3af7c4235d8b6ace4d2728af513702f251565fc1f47197d54` | included the West Virginia item-(5) removal |
| Reviewer v1 | 557 | `eb2a0d130dffb46d2f4cf71ba0dc6e3a9897d86e1aed1be36aa26f7bea0aa916` | included the Colorado `Nebraska` removal |

This was a one-for-one key-set mismatch, not a serialization or ordering mismatch.

Both unique removals are excluded in the corrected ledger:

- Colorado `Nebraska` is enclosed by matched straight quotes and governed by `The State of Colorado and the State of Nebraska are designated, respectively, as "Colorado" and "Nebraska".` Jurisdiction-neutral alias/designation semantics require preservation.
- The West Virginia form item has mixed U+201C/U+0022 delimiters, so raw evidence fails open and requires preservation.

The v2 result therefore has 556 records and converges exactly.

## Independent full-ledger construction

The independently composed ledger did not start from reviewer-v2 bytes. It used the pinned 636-record M-R118 direction-aware baseline, whose canonical identity projection has SHA-256 `3c633134831f226962b6f8ff73447e3d55aeb54bf0e2eb4a1c962b8c612c20ff`.

Baseline:

- 636 total = 634 removed + 2 added.

Drop 86 baseline removals:

- 57 previously audited source-preservation decisions;
- 16 baseline removals rejected by corrected state/closure semantics; and
- the 13 DC/federal removals adjudicated above.

Add 6 approved non-baseline changes from state audit v2:

- 4 removals; and
- 2 additions.

Arithmetic:

- Total: `636 - 86 + 6 = 556`
- Removals: `634 - 86 + 4 = 552`
- Additions: `2 + 2 = 4`

## Canonical byte contract and reciprocal comparison

Each final line contains exactly:

`change,jurisdiction,source_file,source_row,source_row_id,term,definition_text,scope`

Serialization is `json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":")) + LF`.

Ordering is:

`(jurisdiction, source_file, str(source_row), term, definition_text + NUL + scope, change)`

Independent-v2 and reviewer-v2 checks:

- 556/556 canonical lines;
- 556/556 correct sort positions;
- 556/556 unique full direction-aware keys;
- identical 673,332-byte files;
- identical SHA-256 `17530d3a4b6621f16b896c9ad21e8ab88df8c4dd273fcf0f2b5d204402a95e5a`;
- `cmp -s` exit 0; and
- zero full-key set differences.

## Final status

- Exact source decisions classified: 13/13
- Preserve/drop-removal decisions: 13
- Ambiguous: 0
- Unclassified: 0
- State audit v2 decision delta: exactly 1 of 97
- Production `backend/app` edits: none

The binding M-R121 expected changed ledger is the 556-record v2 artifact.
