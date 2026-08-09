# M-R121 independent state and same-row closure audit v2

## Result

This corrected audit supersedes the 97-record v1 decision set documented in the sprint history. It preserves the same exact keys in the same order and changes exactly one decision: West Virginia power-of-attorney item (5) is fail-open preservation because its raw quote delimiters do not match.

The state/closure semantic slice contains 75 of 97 exact keys: 71 removals and 4 additions. The other 22 removal keys must be excluded.

Against the M-R120 586-key ledger, the corrected state audit drops 18 included removals and adds one newly exposed Hawaii removal:

`586 - 18 + 1 = 569`

This is the state-only M-R121 projection before the separate 13-key DC/federal reconciliation.

Canonical artifact: `state_closure_adjudication.jsonl`

- Records: 97
- Reviewed keys: 55, exactly matching the frozen review-input order
- Same-row closure keys: 42
- Exact key differences from state audit v1: 0
- Decision-record differences from state audit v1: 1
- Duplicate exact keys: 0
- Irreducible ambiguities: 0
- Canonical JSONL SHA-256: `1e766ce6d5f9a2d0d1feb22c872d640997aaee28456e0fb72cf0baa1a9b56d67`

## Uniform source rules

1. Exact-emitted matched occurrences own arbitrary local payload. A punctuation-normalized occurrence preserves only through an explicit `means`, `includes`, alias/name, or forwarding relation.
2. Explicit alias/designated-name and forwarding relationships are jurisdiction-neutral genuine semantics.
3. Raw malformed or mixed quote delimiters fail open before a removal may be justified.
4. With valid matched delimiters, prescribed forms, display labels, legends, title-use lists, and future-rulemaking term lists are removable pseudo-entries.
5. Direct colon/enumerated definitions are preserved.
6. Plural repair owns only its matched occurrences.

## Counts

| Audit slice | Preserve | Safe remove | Safe add | Included in semantic ledger | Total |
|---|---:|---:|---:|---:|---:|
| 55 reviewed keys | 20 | 33 | 2 | 35 | 55 |
| 42 closure keys | 2 | 38 | 2 | 40 | 42 |
| **Total** | **22** | **71** | **4** | **75** | **97** |

The reviewed-bucket split is:

| Source bucket | Preserve | Safe remove | Safe add | Total |
|---|---:|---:|---:|---:|
| `certified_missing` | 14 | 30 | 0 | 44 |
| `unexpected_actual` | 6 | 3 | 2 | 11 |

## The one v2 correction

Exact key: removed `US-WV`, `us_wv_statutes.parquet`, row `3459`, `STATE_WV_C49_A8_S4`, term beginning `This power of attorney is effective for a period not to exceed one year`.

The source is unquestionably a statutory form clause, but the exact raw occurrence opens with `“` (U+201C LEFT DOUBLE QUOTATION MARK) and closes with `"` (U+0022 QUOTATION MARK). Because there is no occurrence enclosed by like delimiters, the raw mixed-delimiter rule binds first and fails open:

- v1: `safe_remove`, `accept_runtime_removal`, included in expected ledger;
- v2: `preserve`, `reject_runtime_removal`, excluded from expected ledger.

The other five West Virginia form removals have valid structural evidence and remain safe removals.

## Preserved reviewed removals

The 20 reviewed removals rejected by v2 are:

- Four explicit aliases/designations: Arizona `American plan`, Colorado `Nebraska`, Louisiana `the state board`, and Louisiana `Notice of Installment Agreement Termination and Demand`.
- Ten explicit forwarding definitions: eight terms in Maryland § 22-102, Maryland `Contract for sale`, and North Carolina `Governmental plan`.
- Three repeated or normalized explicit definitions: Delaware `sexual assault.`, federal `Former DISC`, and Georgia `population bill.`.
- Two direct colon/enumerated Texas definitions: `Domestic use` and `first sale`.
- The West Virginia mixed-delimiter power-of-attorney item (5).

Colorado `Nebraska` remains preservation: the matched exact quote is governed by `The State of Colorado and the State of Nebraska are designated, respectively, as "Colorado" and "Nebraska".` This is an explicit alias/designated-name relation.

## Same-row closure

The 42 closure keys are unchanged from v1:

- 38 safe removals;
- 2 safe additions for the bounded Indiana `utility` repairs; and
- 2 preserved Maryland colon/enumerated definitions, `Consequential damages` and `Transfer`.

The Hawaii `Intoxicants and Narcotics: … physician.` form entry remains the one newly added safe removal.

## Delta from M-R120

M-R120 included 18 removals rejected by this corrected audit:

- 4 alias/designation removals;
- 10 forwarding-definition removals;
- Delaware `sexual assault.`;
- Maryland `Consequential damages`;
- Maryland `Transfer`; and
- West Virginia mixed-delimiter form item (5).

M-R121 adds one removal absent from M-R120: Hawaii `Intoxicants and Narcotics: … physician.`. Therefore the corrected state-only projection is 569.

There is no irreducible source ambiguity: the raw delimiter code points and the fail-open rule resolve the West Virginia case deterministically.
