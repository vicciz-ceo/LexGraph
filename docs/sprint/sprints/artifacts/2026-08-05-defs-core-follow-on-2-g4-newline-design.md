# G4 cross-newline Planner delivery

## Decision

Implement only a **`Section N` / lone `§ N` + parenthesized-token**
cross-line exception. Every broader form measured here has real
counterexamples.

For a parenthesized candidate separated from a `Section N` or lone `§ N`
suffix by an arbitrary `str.isspace()` gap containing CR or LF:

1. reject it when the right tail begins with a comma, or with zero or more
   parenthetical tokens followed by `of this act`;
2. otherwise accept it as a genuine marker.

Preserve current rejection for structural-word context, the full
`N U.S.C. § N` branch, the bare-state-code branch, and every period-style
candidate. Preserve every same-line decision and the existing chain
connector behavior.

This is the narrowest zero-error changed surface in the exhaustive audit:
613 occurrences = 607 genuine entries and 6 citation continuations, with
zero false accepts and zero false rejects. The proposal changes 585 actual
resolver paths; 22 accepted genuine tokens are immediate path no-ops.

Broader designs were rejected from evidence, not preference:

- bare state-code has 86 cases: 37 genuine entries but 49 nonstructural
  tokens, including Louisiana highway `LA N\n\nLa.` abbreviations, Kansas
  year/date labels, and table abbreviations;
- `Section`/`§` period style has 48 cases: 47 genuine entries but the real
  `COMMENTARY ON §704-400\n\nI.` non-operative heading;
- structural-word context has 3,056 cases and a blanket exception changes
  2,874 paths across 2,246 rows.

The 37 genuine bare-code and 47 genuine period cases are named recall debt.
They need separately measured operative-text corroborators; this release
must not trade the DC fix for known fabrications.

## Reproduction and exact population

Run from repository root:

```text
backend/.venv/bin/python docs/sprint/sprints/artifacts/measure_g4_newline_context.py \
  /Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad
```

- Exactly 53 `us_*_statutes.parquet` files; constitutions are excluded.
- Exactly 2,038,247 statute rows.
- Normalization is `text.replace("\\n", "\n")`, exactly the ingest
  transformation relevant to these predicates.
- The scan uses all four production citation suffix branches: full U.S.C.,
  `Section`, lone `§`, and bare state-code.
- It uses the exact production candidate union: parenthesized and
  paragraph-anchored period forms.
- The gap is arbitrary Python `str.isspace()` containing at least one CR or
  LF, including blank lines and multiple line breaks. The Arrow prefilter
  spells out all 29 Unicode characters for which `str.isspace()` is true;
  every emitted case is then revalidated with the production regex calls
  and exact production token offsets.

The adjacent full JSON records every occurrence's context offset, token
offset, gap bytes, branch, marker form, audit stratum, judgment/reason, and
current/proposed/blanket paths. The summary JSON asserts every denominator
and judgment total.

## Citation results and audit

| Production branch / token form | Occurrences |
|---|---:|
| lone `§` / parenthesized | 425 |
| `Section` / parenthesized | 188 |
| bare state-code / parenthesized | 16 |
| lone `§` / period | 18 |
| `Section` / period | 30 |
| bare state-code / period | 70 |
| full `N U.S.C. § N` / either | 0 |
| **Total / distinct rows** | **747 / 501** |

All 747 occurrences were hand-read in four mutually exclusive,
deterministic strata:

1. all 86 bare-state-code cases;
2. all remaining 48 period cases;
3. all 31 single-line-break `Section`/`§` parenthesized cases;
4. all 582 multiple-line-break `Section`/`§` parenthesized cases.

Final judgment is 691 genuine entries, 6 citation continuations, and 50
nonstructural tokens. The six continuations are occurrence-bound (not
row-bound): five NY `Section 112\n(1965),` / `§ N\n(a)...of this act`
forms and the OK blank-line `Section 112\n\n(1965),` duplicate. The 50
nonstructural cases are the 49 bare-code cases plus the HI commentary
heading. Per-case reasons remain in the full ledger.

The parenthesized changed surface was also checked by source family rather
than assuming marker shape proves structure: Arkansas act-history-to-body
transitions, Iowa definition-index nesting, AK land schedules, and all
remaining state residuals were read. No commentary/annotation false accept
survives in the 613-case surface.

Results:

- proposal direct decisions: 607 accept / 140 reject;
- changed surface: 607 genuine / 6 continuation, 0 false accept / 0 false
  reject;
- current → proposal: 585 actual path deltas, all on genuine entries;
- current → blanket citation exception: 673 path deltas across 489 rows;
- retained recall debt: 37 bare-code and 47 period genuine entries stay
  rejected.

## Structural results

The full production structural cross-line surface is 3,056 occurrences / 2,369
rows: 2,824 parenthesized and 232 period candidates. The proposal leaves it
unchanged and the simulator asserts **zero current → proposal path deltas**.
A blanket newline break changes 2,874 paths across 2,246 rows.

For continuity with the requested original predicate, the exact-one-LF,
horizontal-whitespace, parenthesized subset remains separately asserted at
1,221 occurrences / 835 rows (NY 1,216, DC 3, TN 2). Its exhaustive
classification is 16 genuine / 1,205 continuations:

- 1,159 are exhausted by closed right-side continuation syntax;
- all 62 residuals were hand-read (16 genuine / 46 continuation);
- the deterministic seed-20260805 stratified ledger contains 167 cases.

Those 16 genuine structural entries remain named recall debt; widening this
release is unsafe.

## REDs and controls

- Full DC row `STATE_DC_T4_C2_S4-204.52`, SHA-256
  `a28333a0...b6080b7`: unit and live persisted-assertion REDs require
  `digit:3` after `§ 4-204.53\n(3)` and currently get stale `digit:2`.
- Real AK `Section 32\n\n(F)` supplies the blank-line `Section`-word
  parenthesized RED and currently stays stale at `upper_alpha:E`.
- Real NY and OK year / `of this act` continuations fence both one-line and
  blank-line negatives.
- Real KS `BR\n\n12\n\n1972.` and HI
  `COMMENTARY ON §704-400\n\nI.` publicly fence the harmful bare-code and
  period expansions.
- Real NY `paragraph\n(c)` plus existing SC/TX/ME/OR tests retain the
  structural and same-line guards.

No test imports `_is_citation_or_xref_context` or otherwise freezes its old
private signature (`rg` sweep: zero test matches). The Developer may pass
token end/form into a revised internal decision without stale test pins.

## Developer write-set

Production write-set: `backend/app/definition_links/us_profile.py` only.
The Developer should:

- return explicit context identity (structural, full U.S.C., `Section`, lone
  `§`, or bare state-code) instead of one undifferentiated boolean;
- pass candidate start/end or form into the decision;
- recognize a cross-line gap with the same `str.isspace()` loop production
  already uses;
- make only `Section`/lone-`§` + parenthesized candidates eligible;
- apply the measured right-tail continuation grammar on that surface;
- preserve period, structural, bare-code, full-U.S.C., same-line, and chain
  behavior exactly.

No fixture, test, evidence, G7, or G8 file belongs in the Developer
write-set.
