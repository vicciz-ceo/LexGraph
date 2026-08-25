# Item 5/8 (gates 5-6, issue #31) — certification v2 (QA-fail cycle 1)

**Status: COMPLETE, WITH A DISCLOSED RESIDUAL GAP.** Fresh full all-53
executed run, baseline = `main` (`8850401`, unmoved, reused), current =
this branch's HEAD `457045b` (Items 6-7 QA-fail-cycle-1 fixes, including
the manager-authorized roman-numeral run-tracking extension). 100%
anchor-granularity adjudication of the actual delta, P-R15 deletion-side
screen clean, cross-checked against Item 4's own ledger. A residual
over-trim gap was found and diagnosed during this cycle's own
verification and is disclosed below (manager ruling: enumerate, do not
fix further this cycle).

## Why a v2 (relationship to the original certification)

QA bounced the original `item5_gate5_certification.md` (Items 1/2/5 —
see the contract's own QA bounce section) because Item 1's own trim
over-trimmed legitimate same-definition enumerated lists and Item 2 left
a named phantom admitted. This document re-certifies after landing (in
order): a run-aware letter-paren/digit-dot/digit-paren bleed-trim
discriminator (commit `b996350`), an orthogonal coordinated-clause
single-letter rejection signal (`5542bee`), a clause-boundary refinement
for the run tracker (`f3d38d2`), a digit-dot line-anchor position fix
plus a wider direct-evidence check (`54111be`), and a manager-authorized
roman-numeral vocabulary extension to the same run tracker (`457045b`).
The original `item5_gate5_certification.md`/`gate5-adjudication/` are
left untouched as historical record of the QA-bounced run; this v2
supersedes it for certification purposes.

## Run

`gate5-run/baseline/` **REUSED UNCHANGED** — `main`@`8850401` has not
moved since the original certification (verified: `git fetch origin
main` tip == `8850401`; `gate5-run/baseline-src/backend/app/
definition_links/us_profile.py` byte-identical to `git show
8850401:`same path`); its own `summary.json` (`files=53, rows=2038247,
members=193830, members_sha256=851e85d...`) is intact and its
provenance in `run_gate5_certification.sh` (`BASE_SHA=8850401`) matches.
Re-running it would reproduce byte-identical output at real cost, so it
was not re-run.

`gate5-run/current/` was re-run **five times** this cycle (once per
landed fix, since each one changes the shipped code the certification
must reflect) via `run_gate5_current_resumable.py` — a resumable,
per-jurisdiction-checkpointed driver written this cycle after the plain
`measure_actual_production.py --current` invocation (`run_gate5_
certification.sh`'s own recipe, which accumulates all 53 files in memory
and writes once at the very end) lost 100% of elapsed progress to
repeated machine-sleep interruptions. The resumable driver calls the
EXACT SAME functions (`capture`, `key`, `member`, `registered_b1_winner`,
`jurisdiction`, `write_jsonl`, `load_production` — imported from
`measure_actual_production.py`, never reimplemented, P-R16) with added
per-file checkpointing; its final output is assembled in the identical
sort order and format the original script produces.

**Final current-side run** (against HEAD `457045b`):

```
files: 53, rows: 2,038,247 (matches baseline)
members: 193,830 (matches baseline; members_sha256 851e85dc81d6f9657a80cd2ae6d94d2c6289068932d9274288a45c926236af5a — BYTE-IDENTICAL to baseline)
current records: 619,584 (baseline: 619,616)
records_sha256: 4cc9c28f4fd532b2d84814e298bdfad7b274869b6768b7aa83922ae97aae0475
```

**P-R16 check:** unchanged from the original certification's own
account — `measure_actual_production.py`'s `capture()` calls `profile.
extract_definitions_from_section`/`extract_local_scope_definitions`
directly; every one of Items 1-7's changes lives entirely inside those
two methods. `members_sha256` byte-identical to baseline confirms the
outer dispatch (heading recognition, B1 derivation, scope) — untouched
by any of this cycle's own fixes — produced the exact same population of
rows to measure candidates for, on both sides.

## 100% anchor-granularity delta adjudication

Anchor key = (jurisdiction, source_file, source_row, term), decomposed
per the standing lesson. Script: `adjudicate_gate5_delta_v2.py` (a
straight copy of Items 1-4's own `adjudicate_gate5_delta.py`, output
redirected to `gate5-adjudication-v2/` so the original QA-bounced run's
own evidence stays intact for comparison; `KNOWN_SINGLE_LETTER_PHANTOM_
TERMS` stays empty, per P-R11 never hand-authored before the run).

| Category | Count | % of baseline |
|---|---|---|
| Unchanged | 549,116 | 88.6% |
| Text change (same anchor, different bytes) | 70,468 | 11.4% |
| True addition (new anchor, current only) | 0 | 0.0% |
| True removal (anchor gone, baseline only) | 32 | 0.005% |

(For reference, the QA-bounced run's own numbers: unchanged 545,866 /
text-change 73,720 / addition 0 / removal 30. Every fix this cycle
landed shifted MORE anchors into "unchanged" — i.e. current now matches
baseline exactly where baseline already had no bleed to begin with —
and shrank the text-change count correspondingly, exactly the direction
gate 1 requires.)

**True removals (32/32, 100% adjudicated):** every one a SINGLE-CHARACTER
term, confirmed by direct inspection of all 32 rows
(`gate5-adjudication-v2/true_removals.jsonl`). The QA-bounced run's own
30 removals are ALL still present in this set (diffed directly, zero
missing) — Item 2's fix never un-removed anything. Two NEW removals
beyond the original 30, both live-verified against real source text:

- **CA `STATE_CA_Chsc_D2_C2.4_S1424` "B"** — the QA-named phantom itself
  (gate 2's own bounce exemplar). Gap to "shall include" is 16 chars
  (under the old 20-char-only threshold) but its own gap-prefix
  `" violation, and "` matches the new `_COORDINATED_CLAUSE_BEFORE_
  IDIOM_RE` signal — correctly rejected.
- **US-IA `STATE_IA_TX_C423_S423.3` "d"** — same sub-mechanism as the
  already-known IA citation-letter phantoms (`paragraph "d"`, gap 6
  chars, `", and includes "` — a lettered citation cross-reference
  mis-paired with a distant, unrelated idiom belonging to "food or food
  ingredients", NOT to "d" itself). Live-verified against the real row.

**P-R15 deletion-side screen: 0/32 flagged.** No removed `definition_
text` starts with a defining-verb phrase.

**True additions: 0/0.** Unchanged from the original certification's own
reasoning — none of Items 1-7 ever create a new anchor.

## Named exemplar verification (QA's own gate-1 bounce rows)

All three re-derived from the live pipeline against this exact
certified current-side data, all three now CORRECT full text:

- **CA `STATE_CA_Cgov_T2_D3_P1_C5.6_S11546.46` "Covered populations"**
  — 648 chars, full 8-item `(A)`-`(H)` list, byte-identical to the
  committed RED test's own `expected` string.
- **FL `STATE_FL_TX_C112_PI_S112.1816` "Cancer"** — 451 chars, full
  21-item `1.`-`21.` list (the committed RED test's own `expected`
  string is 461 chars because it retains the `"includes: "` idiom
  prefix a baseline-sourced capture keeps and a fallback-sourced one
  strips; byte-for-byte identical content once that 10-char prefix
  difference is accounted for — confirmed by direct string comparison,
  not assumed).
- **PR `STATE_PR_LEY_60_1963_ART422` "Agent"** — 1,320 chars, running
  all the way through `(1)…(a)-(e)…(2)…"…otherwise covered by this
  definition."` (baseline itself was 1,324 chars but carried a 4-char
  dangling `" (c)"` fragment bled in from the NEXT, unrelated entry —
  this capture is a genuine improvement over baseline, not merely a
  match to it).

## Additional verified-correct sample (manager requirement: AZ +
## ≥5 more of the 19-row roman-numeral population)

Per the manager's ruling, the sample below is drawn from the same
19-row population that justified the roman-numeral fix (`roman_numeral_
truncation_scan.jsonl`), each independently live-verified against real
source text (not just plausible-looking output):

| Jurisdiction | act_id | term | Verified result |
|---|---|---|---|
| AZ | `STATE_AZ_T28_C10_A10_S4653` | "unreasonable restriction" | 919 chars, full 6-item `(i)`-`(vi)` list, ends exactly before the row's own unrelated `"B. Prior express written consent…"` |
| CA | `STATE_CA_...S69959.5` (row 41256's own act) | "proportionate interest" | 533 chars, ends exactly before a SEPARATE, later `"proportionate interest"` quote+idiom occurrence — a distinct, later-scoped definition, not this one's own bleed |
| PA | (row 3552's own act) | "knowingly consents" | 1,353 chars, ends exactly before the row's own unrelated `"(b) Prohibition on sales.--…"` |
| MS | `STATE_MS_T75_C12_S55-5` | "gasoline" | 346 chars, ends exactly before a SEPARATE, later quoted term `"commercial gasoline"` |
| CO | (row 1164's own act) | "employee" | 624 chars, ends exactly before the row's own unrelated, separately-quoted `"(b) \"Erotic parlor\" means…"` |
| CO | (row 18290's own act) | "similar coverage" | 1,183 chars, ends exactly before the row's own unrelated `"(c) The lease shall provide for the payment…"` |
| CO | (row 10243's own act) | "fire occurring on private property" | 517 chars, ends exactly before the row's own unrelated `"(2) (a) An owner of private property…"` |

7 rows verified correct (AZ + 6 more), exceeding the "AZ plus at least 5
more" bar.

## Cross-check against Item 4's ledger

0/101 overlap (text_changes, true_additions, true_removals all 0) —
unchanged from the original certification; Item 4's 101 UNRECOVERABLE
rows remain completely unreached by anything Items 1-7 do, exactly as
gate 8's own ceiling-protection scope requires.

## Disclosed gap (manager hard-terminal-condition ruling — NOT fixed
## this cycle, enumerated instead)

While verifying the roman-numeral fix's own population (the 19 rows
above), a **structurally distinct 5th over-trim shape** surfaced. Per
the manager's explicit ruling this cycle ("if that cycle surfaces ANY
new defect shape... do NOT fix it... enumerate it... certify with the
disclosed-gap caveat"), it is recorded here, NOT patched.

**Root cause A — nested mixed-vocabulary enumeration** (the majority of
the residual population): this module's own letter-paren/roman-numeral
run tracker can hold only ONE active run/vocabulary at a time. A roman-
numeral list whose own item contains a NESTED sub-list — lettered
(`(A)`/`(B)`) or itself roman (`(I)`-`(VIII)`, case-folded to the same
tokens as the outer lowercase list) — causes the nested marker to
satisfy the tracker's OWN seed condition (token `"a"` or `"i"`),
hijacking the state machine and abandoning the outer run, which is never
resumed; the outer list's remaining members are then left unprotected
and fall through to the original, un-suppressed relaxed check. Confirmed
via direct real-source-text verification (not just plausible-looking
output) in:

- **PA `STATE_PA_T18_C63_S6306.1` / `STATE_PA_T18_C63_S6305` "Tobacco
  product."** — item `(iii)`'s own nested `(A)`/`(B)` list hijacks the
  tracker; `(iv)` (a genuine 4th list member: "Any component, part or
  accessory... under subparagraphs (i), (ii) and (iii)...") is orphaned
  and lost.
- **CA (row 41256's own act) "necessary equipment"** — same shape.
- **CA `STATE_CA_Cedc_T2_D4_P28_C10_A6_S52616.4` "direct support
  costs"** — item `(ii)`'s own nested `(I)`-`(V)` roman sub-list hijacks
  the tracker; `(iii)` ("Plant maintenance and operations costs...") is
  orphaned.
- **WY `STATE_WY_T35_C11_S35-11-525` "orphan landfill site"** — item
  `(i)`'s own nested `(A)`/`(B)` list hijacks the tracker; `(ii)`/`(iii)`
  are orphaned.
- **CT `STATE_CT_T38a_C701_S38a-686` "extraordinary life circumstance"**
  — item `(i)`'s own nested `(I)`-`(VIII)` roman sub-list hijacks the
  tracker; `(ii)` is orphaned.

**Root cause B — pre-existing-in-baseline bleed, unrelated to the
roman-numeral fix:** **MD `STATE_MD_Agps_T14_S3_S14-304` "Committee"**
over-captures into unrelated, later digit-paren subsections `(2)`/`(3)`
that merely MENTION "Committee" as a term-use, not as part of its own
definiens (the true definition is `(i)`/`(ii)` alone, ~300 chars).
Confirmed this predates EVERY fix this sprint has landed: baseline
(`main@8850401`, before ANY of Items 1-7 existed) already captures 1,901
chars — the entire remainder of the row. Each successive fix this cycle
happened to reduce the over-capture somewhat (1,901 → 730 → 903 chars)
without ever reaching the correct boundary; the roman-numeral fix's own
`(3)(i)…(ii)…` nested-roman sub-list (Root Cause A's own shape, layered
on top) is why it grew from 730 to 903 rather than shrinking further.

**Not further diagnosed** (flagged by the same heuristic scan or the
manual sample review, output does not obviously match the expected
shape, root cause not confirmed either way — listed for completeness,
not asserted as bugs): OR `STATE_OR_T23_C260_S260.266` "communication in
support of or in opposition to a clearly identified candidate" (33-char
capture; the row's own source text contains a literal `"(i) Intentionally
left blank —Ed."` placeholder, so a short capture may be genuinely
correct rather than under-trimmed — not resolved either way); a CO row's
own "Bona fide physician-patient relationship" (ends in a malformed
`"(a."` fragment — likely a further-undiagnosed compound section marker
shape, e.g. PA/CO-style `"(a.7)"` tokens neither this module's letter
nor digit-dot tracker recognizes at all); PA's own "evidence of imminent
danger" and "municipality" (each shows content past what looks like the
natural definitional boundary; not root-caused).

**Population scale:** the heuristic scan that found the original 19-row
population (`scan_roman_numeral_truncation.py`) re-run against this
CURRENT, fully-fixed delta finds 8 rows still matching its own coarse
"starts with a roman marker, baseline continues with another roman
marker at exactly that point" pattern — of which 1 (MS "gasoline") is a
CONFIRMED FALSE POSITIVE of that scan's own coarseness (independently
verified correct: the "next roman marker" it flags belongs to a
different, later quoted term, not a continuation of "gasoline"'s own
list). The other 7 are the Root-Cause-A rows named above. Root Cause B
(MD) and the "not further diagnosed" rows are NOT caught by this
specific scan pattern (their own shape differs) and were found instead
during the manual sample review — meaning the TRUE population of this
disclosed gap is not fully bounded by either method alone; a proper
full-corpus census (analogous to `measure_item6_item7_population.py`,
purpose-built for these specific shapes) was not run this cycle, per
the hard-terminal-condition instruction not to invest further.

**Recommendation for the next cycle:** the nested-mixed-vocabulary gap
(Root Cause A) needs the run tracker to support a STACK of active runs
(push a new run when a nested seed is found inside an already-active
run's own span, pop back to the outer run when the nested run's own
vocabulary is exhausted) rather than a single flat state — a genuine
design question, not a bounded vocabulary extension like this cycle's
own roman-numeral fix was. Root Cause B (MD) is unrelated to the run
tracker entirely and needs separate investigation into why baseline's
own unbounded fallback capture reaches so far past the row's own next
recognized entry in the first place.

## Known, pre-authorized consequence (not a defect)

Unchanged from the original certification: `test_qa_regression_defs_
boundary_idioms.py`'s gate-2-certificate tripwire and `test_us_body_
preamble_g7_certification_contract.py`'s `INTEGRATION_SHA`-frozen-
production tripwire both fire, by design, since `backend/app/` changed
again this cycle. A Planner/QA return-pass re-pins both against this
v2 certificate's own tip (`457045b` or whatever commit this document
ships alongside).

## Artifacts

- `gate5-run/current/` (this run, `457045b`) and `gate5-run/baseline/`
  (reused, `8850401`) — raw `records.jsonl`/`members.jsonl` (gitignored)
  + `summary.json` (committed) for each side.
- `gate5-adjudication-v2/` — `summary.json`, `text_changes.jsonl`,
  `true_additions.jsonl` (empty), `true_removals.jsonl`,
  `flagged_removals_p_r15.jsonl` (empty).
- `run_gate5_current_resumable.py` / `adjudicate_gate5_delta_v2.py` /
  `sample_and_verify_v2.py` / `crosscheck_item4_v2.py` /
  `scan_roman_numeral_truncation.py` (+ its own
  `roman_numeral_truncation_scan.jsonl` output) — the scripts and
  evidence this v2 certification is built from.
- `gate5-run/baseline-src/`, the original `item5_gate5_certification.md`
  and `gate5-adjudication/` — historical record of the QA-bounced run,
  left untouched.
