# Gate-2 delta investigation — sprint 2026-08-12-defs-b1-refers-to

Investigator pass, read-only. Diagnoses the gate-2 all-53 delta produced by
`run_gate2.sh` / `diff_gate2.py` (4,255 changed records: 3,542 added / 713
removed, 3,584 distinct (row, term) anchors). Does not fix, adjudicate, or
certify.

## Headline finding

**The reported gate-2 delta does not measure commit `86fccfb`'s effect.**
Of the 2,953 distinct (jurisdiction, source_file, source_row) rows touched
by the entire reported delta, running BOTH the pre-fix source
(`run/baseline-src`, commit `5c3e75130c9e1d26c8e3448dc85691d12478889c`) and
the post-fix source (this worktree, commit `86fccfb`) through the real
production calling convention (`measure_actual_production.py`'s
`--current` mode, which mirrors `pipeline.py`) produces **byte-identical
output for 2,952 of those 2,953 rows**. Exactly **one** row differs:
`US-IN us_in_statutes.parquet row 80161, term "loan"`.

The other 2,952 rows' apparent "changes" are a pre-existing artifact of
`measure_actual_production.py`'s `capture()` helper
(`docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/measure_actual_production.py:142-196`),
which is unrelated to `_POST_RELATION` or to this sprint's code change.
Full evidence and mechanism below (Q1).

Practical consequence: Q2's "additions genuineness" sample and Q3's
"removal-only records" are, empirically, sampling **the measurement
harness's own artifact**, not the refers-to widening's behavior. I still
answer both exactly as scoped (genuineness of what's in the delta; per-
record classification of the pure removals), and flag throughout which
records are/aren't attributable to the actual code change.

---

## Q1 — mechanism (the blocker)

### The real mechanism, precisely

`measure_actual_production.py::capture()` computes
`recognized_by_registered_rule` conditionally on its own CLI flag:

```
# measure_actual_production.py:151-153
recognized_by_registered_rule = bool(
    current and recognized and callable(rule_only) and rule_only(heading, body)
)
```

Real production, `backend/app/definition_links/pipeline.py:262-266`,
computes the **same** value **unconditionally** — there is no `current`-
flag equivalent in production at all:

```python
recognized_by_registered_rule = bool(
    is_definitions_section
    and callable(rule_only)
    and rule_only(art.heading, matcher_article.body)
)
```

`run_gate2.sh` invokes the "current" measurement with `--current`
(`recognized_by_registered_rule` gets its correct, always-on value) but
invokes "baseline" **without** `--current` (`recognized_by_registered_rule`
is forced `False`, a state that never occurs in real production, at any
commit). Downstream, `recognized_by_registered_rule` gates whether
`extract_local_scope_definitions`/`extract_definitions_from_section` run
with `heading_was_derived=True` (measure_actual_production.py:178-188,
mirroring pipeline.py:302-347) — which changes which extraction path runs,
which candidates get generated, and whether `preserve_substantive_b1_candidates`
(`backend/app/definition_links/rules/us_body_preamble_b1.py:283-290`) is
applied to them at all. This asymmetry is orthogonal to `_POST_RELATION`
and pre-dates this sprint (`heading_recognized_only_by_rule` /
`derive_body_preamble_match` already exist at the pre-fix `BASE_SHA`, per
`git grep` on `run/baseline-src`). The script's own docstring says it was
built to compare "production-vs-5753e11" — an older baseline commit that
plausibly lacked this API. Reused unmodified against this sprint's
`BASE_SHA` (which already has the API), `current=False` degrades to a
calling convention that **no version of real production ever executed**.

### Verification

1. **MI "both" cluster (671 anchors, 586 US-MI):** every single one
   (100%, all 671, all 9 affected jurisdictions: MI, NV, NJ, SC, UT, NM,
   OK, ND, WA, VA) matches the exact pattern `removed.scope == "law-wide"`
   / `added.scope == "local"`, with one text a strict prefix of the other.
   Running 5 hand-picked US-MI examples (rows 5, 33, 64, 71, 113) through
   the true `current=True` calling convention against **both** source
   trees gives byte-identical `local`-scope output in all 4 runs
   (pre-fix/post-fix × the "local" candidate). The `law-wide` text only
   appears under the crippled `current=False` convention, on both source
   trees identically. `_candidate_is_substantive`/`_POST_RELATION` never
   even run on this path for these rows (`b1_winner=False` throughout,
   because `is_definitions_heading` already recognizes the row directly —
   `derived` never becomes non-`None`).

2. **60-record Q2 stratified sample (see below):** all 60 reproduce
   byte-identically under `current=True` on the pre-fix source. None use
   "refers to"/"refer to" as their defining verb (see per-item verb
   check).

3. **Comprehensive check — every row touched by the reported delta:**
   Built the exact 2,953 unique `(jurisdiction, source_file, source_row)`
   set from `changed.jsonl`, ran `capture()`-equivalent logic in
   `current=True` mode against both source trees for every one of those
   rows (script: scratchpad `bulk_capture.py`). **2,952/2,953 rows are
   byte-identical.** The one exception:

### The one genuine effect of commit 86fccfb

`US-IN, us_in_statutes.parquet, row 80161` (`STATE_IN_T5_A28_C28_S5-28-28-3`,
heading `"Loan"`):

> Sec. 3. As used in this chapter, "loan":
> (1) refers to a loan made by the corporation, regardless of whether the
> loan is forgivable; and
> (2) includes a loan guarantee made by the corporation.

Traced to the exact statement. The candidate itself — `terms=('loan',)`,
`scope='chapter'`, `text='a loan guarantee made by the corporation...'`
(limb (2), via `_extract_inline_quoted_definitions`,
`backend/app/definition_links/us_profile.py:1077`) — is **identical** in
both source trees; construction of this candidate does not touch
`_POST_RELATION` at all. The only difference is
`_candidate_is_substantive(raw, candidate, groups)`
(`us_body_preamble_b1.py:264-280`): it returns `False` pre-fix and `True`
post-fix, for this exact candidate. Root cause: the "loan" term is quoted
once, immediately before the colon-list; `_candidate_is_substantive` scans
that quote's own tail in the raw text
(`tail = text[quote.end():quote.end()+_MAX_LOCAL]` = `":\n\n(1) refers to a
loan made by...; and\n\n(2) includes..."`), and line 274's
`_POST_RELATION.match(tail)` now matches `refers?\s+to` inside "(1) refers
to" — flipping the whole candidate from rejected to kept via the early
`return True` branch. Before the fix this same tail failed
`_POST_RELATION`, fell through to `_substantive(_bounded_payload(...))`,
and evaluated `False`. Because `extract_local_scope_definitions`/
`extract_definitions_from_section` both returned **zero** kept candidates
pre-fix, `derive_heading_from_body` (`us_profile.py:2687-2737`, its
`if not local_candidates and not section_candidates: return None` guard)
concluded the row wasn't a Definitions section **at all** pre-fix — this
row was a total miss, not just a missing "loan" term.

**Mechanism, one line, for a Planner's RED test:** widening
`_POST_RELATION` at `us_body_preamble_b1.py:75` to include `refers?\s+to`
changes `_candidate_is_substantive`'s verdict on a candidate whenever the
term's OWN quote occurrence in the raw source is followed (within
`_MAX_LOCAL=600` chars, before the first bounding `;`/`\n`) by a `refers
to`/`refer to` clause — this is a pure KEEP/DROP flip on `_candidate_is_
substantive`'s return value, never a change to any candidate's own
`definition_text`. It is a genuine, positive, single-anchor fix
(previously-total miss on IN row 80161, matching D-RECALL-FP). It is
**not** the mechanism behind the 671 "both" replace-cluster or any of the
other 2,951 rows in the reported delta — those are 100% the
`measure_actual_production.py` `current`-flag artifact described above,
verified identical with and without the fix.

**Faithfulness verdict, the 5 MI examples** (since they were the assigned
task; per the evidence above, none of the 5 are affected by 86fccfb —
both `law-wide` and `local` variants exist identically pre- and post-fix):

| row | term | law-wide (baseline harness artifact) | local (current harness artifact) | verdict |
|---|---|---|---|---|
| 5 | collateral source | full text incl. both "does not include" exclusions + a "for purposes of this section" timing clause | truncated at "...or medicare benefits", drops both exclusions | **law-wide is more faithful** — the "does not include" clauses are substantively part of the "means...but does not include..." definition; `local` loses real defining content. The trailing "for purposes of this section" sentence is arguably over-capture either way. |
| 33 | financial institution | same text + trailing period | same text, no trailing period | tie — cosmetic only |
| 64 | dB(A) | same text + trailing period | same text, no trailing period | tie — cosmetic only |
| 71 | veteran | same text + trailing period | same text, no trailing period | tie — cosmetic only |
| 113 | licensed health care professional | same text + trailing period | same text, no trailing period | tie — cosmetic only |

(A broader systematic check across all 671 "both" anchors: 463/671 are
period-only cosmetic diffs; 208/671 show real truncation like row 5 — e.g.
`US-MI row 10580 "LEIN"` truncates mid-abbreviation at "C.J.I.S", dropping
"policy council act, 1974 PA 163, MCL 28.211 to 28.215, or by the
department of state police" entirely; `US-MI row 10489 "school"` drops
enumerated items (b)(c)(d). This `local`-scope truncation defect is
**pre-existing** — byte-identical with and without the refers-to fix — and
is a separate, real product quality issue worth its own follow-up, but is
categorically not this sprint's delta.)

---

## Q2 — additions genuineness sample

**Sampling method (deterministic, reproducible):** stratified by
jurisdiction over the 2,871 pure-addition anchors (42 jurisdictions
present). Floor of 1 anchor per jurisdiction (42), remaining 18 slots
allocated by largest-remainder proportional to each jurisdiction's
addition volume (Hamilton apportionment). Within each jurisdiction,
`random.Random(20260812).sample()` over that jurisdiction's anchors sorted
by `(source_file, source_row, term)`. Named jurisdictions (IN, FL, NH, MO,
TN) all included; quotas: IN=2, FL=2, NH=2, MO=2, TN=2 (of 1184, 198, 183,
125, 80 respectively) plus 1 each from every other jurisdiction (AL, AR,
AZ, CO×2, CT×2, DC, DE, FED×2, HI, IA, ID, KS×2, KY×2, LA×2, ME, MI×2,
MT×2, NC×2, ND, NJ×2, NM, NV, OH, OK, OR, PA, PR, SC, SD×2, TX, UT, VA,
VT, WA, WI, WV×2, WY). Full 60-item list and per-item detail preserved in
the scratchpad artifacts referenced at the end of this document.

**Verb check first** (directly relevant given Q1): for every one of the
60 sampled rows, I located the term's defining clause in the raw statute
text. **Zero of 60 use "refers to"/"refer to" as the defining verb.**
Verbs actually present: `means` (33), `includes`/`shall include` (16),
`shall mean` (5), `has the meaning set forth/given` (4), `as used in ...
shall mean` (2). This is fully consistent with Q1: none of these 60 rows'
capture depends on the widened `_POST_RELATION`; all reproduce
byte-identically under the pre-fix source run in the true production
calling convention. The 60-sample therefore judges general capture
quality of this jurisdiction/row population, not the refers-to widening's
own precision — that population, per the corpus-wide check in Q1, is
exactly one row (IN "loan", itself judged GENUINE below).

**Classification** (GENUINE / FALSE POSITIVE / AMBIGUOUS):

- **GENUINE: 57/60**
- **AMBIGUOUS: 3/60** — pure forwarding/circular references with no local
  substantive content:
  - `US-CT row 6835 "substantial subcontractor"` → `"means a substantial
    subcontractor, as defined in section 4a-100."` (circular; forwards
    entirely to another section)
  - `US-TN row 484 "employee"` → `"has the meaning set forth in
    § 8-42-101(3)."` (pure forward, zero local content)
  - `US-WI row 245 "Private school"` → `"has the meaning given in s.
    115.001 (3r)."` (pure forward)
- **FALSE POSITIVE: 0/60**

FP rate on this sample: **0%** (0/60). Given the verb-check finding above,
this number should be read as "this population of already-recognized
Definitions rows is captured cleanly," not as "the refers-to widening has
a 0% FP rate" — the sample structurally cannot speak to the latter, since
none of the 60 sampled records are refers-to-driven.

Representative GENUINE examples (verbatim, row ids):
- `US-AR row 20095 "person"`: `"any natural person, corporation, firm,
  partnership, limited partnership, trust, association, or any other
  legal or commercial entity."`
- `US-KY row 9116 "telehealth"`: `"the use of interactive audio, video, or
  other electronic media to deliver health care. It includes..."`
  (verified against raw source: `'For purposes of this section,
  "telehealth" means the use of interactive audio, video, or other
  electronic media to deliver health care.'`)
- `US-MO row 17819 "resident estate or trust"`: `"(1) The estate of a
  decedent who at his or her death was domiciled in this state; (2) A
  trust that: (a) Was created by will of a decedent..."`
- `US-OH row 10367 "unruly child"`: `"any of the following: (A) Any child
  who does not submit to the reasonable control of the child's parents,
  teachers, guardian, or custodian..."`

Representative AMBIGUOUS example:
- `US-CT row 6835 "substantial subcontractor"`: `"a substantial
  subcontractor, as defined in section 4a-100."` — accurately places
  WHERE the term is used/cross-referenced (consistent with D-MAP), but
  carries no substantive definitional content of its own.

The one truly refers-to-driven record found anywhere in this delta —
`US-IN row 80161 "loan"` (see Q1) — is **GENUINE**: "refers to" is a real
statutory defining verb there, one limb of a two-limb enumerated
definition ("(1) refers to a loan made by the corporation...; and (2)
includes a loan guarantee..."). The fix correctly turns a previously
**total miss** (row not recognized as Definitions at all) into a capture,
though only limb (2) is captured — limb (1)'s own "refers to" text is not
retained in the final record (a pre-existing, unrelated single-entry-per-
quote limitation of `_extract_inline_quoted_definitions`).

---

## Q3 — removal-only records

**42 pure-removed anchors, enumerated exactly** (source: `changed.jsonl`
anchors with `removed` set non-empty and `added` empty). All 42 fall into
one class: **phantom-removal**. None are genuine losses.

Verified two ways: (a) directly executing `capture()`-equivalent logic
under `current=True` on **both** source trees for the owning rows (US-MO
row 24, US-TN row 925) shows **zero** candidates for these specific terms
in either source tree — the malformed record only appears under the
broken `current=False` baseline convention, identically regardless of the
fix; (b) the comprehensive 2,953-row check (Q1) confirms every one of
these 42 anchors' owning rows is among the 2,952 byte-identical rows
(none is the one IN exception) — i.e. real production, before and after
86fccfb, has never produced any of these 42 records. (c) None of the 42
terms appear in `run/current/records.jsonl` at their own row (spot-checked
programmatically for all 42) — while every OTHER, genuine term at those
same rows (e.g. MO row 24's `Approved institution`, `CGPA`, `Department`,
etc.) is captured correctly. No collateral loss at these rows.

Two sub-clusters:

**US-TN row 925** (`STATE_TN_T63_C6_S63-6-204`, "practice of medicine" /
"Construction"), 18 anchors, each removed `definition_text` is literally
`";"` or `"; or"` (pure punctuation). Root cause confirmed from raw text:
the section lists prohibited professional-title *examples* inside a single
"practice of medicine" clause — `(A) "Doctor of medicine"; (B) "M.D.";
(C) "Doctor of osteopathy"; (D) "D.O."; ...` — under `current=False`'s
block-splitting path each lettered example becomes its own malformed
"term" whose captured "definition" is just the trailing separator
punctuation. These were never real per-term definitions; "practice of
medicine" is the one real defined term at this row, and it IS correctly
captured in `run/current` today.

| term | removed text | class |
|---|---|---|
| D.O. | `;` | phantom-removal |
| Doctor of medicine | `;` | phantom-removal |
| Doctor of osteopathy | `;` | phantom-removal |
| Family practice physician | `;` | phantom-removal |
| Internist | `;` | phantom-removal |
| M.D. | `;` | phantom-removal |
| Medical doctor | `;` | phantom-removal |
| Obstetrician | `;` | phantom-removal |
| Orthopedic surgeon | `;` | phantom-removal |
| Orthopedist | `;` | phantom-removal |
| Osteopathic medical physician | `;` | phantom-removal |
| Osteopathic surgeon | `; or` | phantom-removal |
| Otolaryngologist | `;` | phantom-removal |
| Otologist | `;` | phantom-removal |
| Otorhinolaryngologist | `;` | phantom-removal |
| Pediatrician | `;` | phantom-removal |
| Physician and surgeon | `;` | phantom-removal |
| Primary care physician | `;` | phantom-removal |
| Surgeon | `;` | phantom-removal |

**US-MO, 24 anchors across 15 rows**, each removed `definition_text`
starts mid-fragment with `":\n\n(a) ..."` or `",\n\n(a) ..."` — a shared-
list/colon-enumeration boundary artifact of the same `current=False`
block-path, where the captured "definition" text is a stray colon plus
the first lettered sub-item rather than the real definition. Every one of
these rows' OTHER, correctly-shaped terms is captured fine in
`run/current` (verified above); only the malformed record disappears.

| row | act_id | term | removed text (truncated) | class |
|---|---|---|---|---|
| 24 | STATE_MO_C173_S173.685 | Satisfactory academic progress | `:\n\n(a) For a student's grade-point average, a CGPA of at least two and one-ha…` | phantom-removal |
| 778 | STATE_MO_C361_S361.1100 | Virtual currency | `,\n\n(a) Any type of digital unit that is used as a medium of exchange or a for…` | phantom-removal |
| 2842 | STATE_MO_C143_S143.455 | Apportionable income | `:\n\n(a) All income that is apportionable under the Constitution of the United …` | phantom-removal |
| 2944 | STATE_MO_C137_S137.1050 | Initial credit year | `:\n\n(a) In the case of a taxpayer that meets all requirements of subdivision (…` | phantom-removal |
| 3258 | STATE_MO_C137_S137.1055 | Five percent county | `:\n\n(a) Any county with more than forty thousand but fewer than fifty thousand…` | phantom-removal |
| 3258 | STATE_MO_C137_S137.1055 | Zero percent county | `:\n\n(a) Any county with more than one hundred thousand but fewer than one hund…` | phantom-removal |
| 4286 | STATE_MO_C143_S143.436 | Member | `:\n\n(a) A shareholder of an S corporation;\n\n(b) A partner in a general partn…` | phantom-removal |
| 7830 | STATE_MO_C375_S375.345 | Counterparty exposure amount | `:\n\n(a) The amount of credit risk attributable to an over-the-counter derivati…` | phantom-removal |
| 7830 | STATE_MO_C375_S375.345 | Income generation transaction | `:\n\n(a) A derivative transaction involving the writing of covered call options…` | phantom-removal |
| 9648 | STATE_MO_C210_S210.1080 | Criminal background check | `:\n\n(a) A Federal Bureau of Investigation fingerprint check;\n\n(b) A search o…` | phantom-removal |
| 10803 | STATE_MO_C135_S135.1210 | Eligible taxpayer | `:\n\n(a) Any short line railroad company located wholly or partly in the state …` | phantom-removal |
| 11242 | STATE_MO_C143_S143.1100 | Business unit | `:\n\n(a) Any trade or business; and\n\n(b) Any line of business or function uni…` | phantom-removal |
| 11242 | STATE_MO_C143_S143.1100 | Deduction | `:\n\n(a) For individuals, an amount subtracted from the taxpayer's Missouri adj…` | phantom-removal |
| 11242 | STATE_MO_C143_S143.1100 | Eligible expenses | `:\n\n(a) Any amount for which a deduction is allowed to the taxpayer under Sect…` | phantom-removal |
| 11242 | STATE_MO_C143_S143.1100 | Eligible insourcing expenses | `:\n\n(a) Eligible expenses paid or incurred by the taxpayer in connection with …` | phantom-removal |
| 11876 | STATE_MO_C568_S568.040 | Arrearage | `:\n\n(a) The amount of moneys created by a failure to provide support to a chil…` | phantom-removal |
| 13564 | STATE_MO_C324_S324.009 | Nonresident military or law enforcement spouse | `:\n\n(a) A nonresident spouse of an active duty member of the Armed Forces of t…` | phantom-removal |
| 13770 | STATE_MO_C375_S375.936 | False statements and entries: | `(a) Knowingly filing with any supervisory or other public official, or knowingl…` | phantom-removal |
| 13770 | STATE_MO_C375_S375.936 | Rebates | `:\n\n(a) Except as otherwise expressly provided by law, knowingly permitting or…` | phantom-removal |
| 13770 | STATE_MO_C375_S375.936 | Unfair discrimination | `:\n\n(a) Making or permitting any unfair discrimination between individuals of …` | phantom-removal |
| 18790 | STATE_MO_C107_S107.170 | Contractor | `:\n\n(a) A person or business entity who:\n\na. Provides or arranges for constr…` | phantom-removal |
| 24022 | STATE_MO_C275_S275.357 | Net market price | `:\n\n(a) Except as provided in paragraph (b) of this subdivision, the sales pri…` | phantom-removal |
| 26131 | STATE_MO_C407_S407.3405 | News-gathering organization | `:\n\n(a) An employee of a newspaper, news publication, or news source, printed …` | phantom-removal |

**Genuine losses: 0 of 42.** No genuine-loss list to report — none found.

---

## Implications

The gate-2 delta as measured (4,255 records / 3,584 anchors) is **not
usable evidence of commit 86fccfb's effect** and should not be certified
on its own terms. It is >99.9% (2,952 of 2,953 rows touched) explained by
a pre-existing mismatch between `measure_actual_production.py`'s
`capture()` (`current`-flag-gated `recognized_by_registered_rule`) and
real `pipeline.py` (unconditional `recognized_by_registered_rule`), fully
orthogonal to `_POST_RELATION`/refers-to. This is not a new defect
introduced by this sprint — it is a latent flaw in a QA script inherited
from an earlier sprint (`docs/sprint/sprints/2026-08-04-defs-us-preamble-scripts/mr118/qa/measure_actual_production.py`)
and reused unmodified against a `BASE_SHA` its `current=False` fallback no
longer models correctly.

The actual, corpus-wide, code-verified effect of commit 86fccfb (widening
`_POST_RELATION` to include `refers?\s+to`) is: **one previously-total-miss
row now recognized** (`US-IN row 80161 STATE_IN_T5_A28_C28_S5-28-28-3
"loan"`), judged GENUINE, no false positives found anywhere in the
2,953-row footprint the reported delta touches, and zero genuine anchor
losses.

Tradeoffs for the Planner/Director to weigh:

1. **Certify as a no-risk change and move on.** The direct, targeted
   evidence (2,953/2,953 rows checked under the real calling convention,
   1 differs) is about as complete as a corpus check gets for this
   footprint. Residual risk: rows the reported delta never touched at all
   (i.e. rows where refers-to could matter but happened to already be
   captured/rejected identically both ways, outside this footprint) were
   not separately re-verified end-to-end — though by construction they
   cannot appear in `changed.jsonl` either way, so they're out of scope
   for "did 86fccfb change anything," not a gap in this analysis.
2. **Do not certify against `changed.jsonl` as-is.** Whatever ships as
   "the gate-2 ledger" for this sprint would, if taken literally,
   authorize 671 "replacements" and 42 "removals" that never happened and
   ~2,871 "additions" that already existed pre-fix — none of which are
   this sprint's doing. Certifying them under this sprint's name would
   misattribute a pre-existing (and separately real, e.g. the `local`-
   scope truncation defect noted in Q1) set of behaviors to this change.
3. **Recommended path:** re-run gate-2 with `measure_actual_production.py`
   invoked in `--current` mode on **both** sides (the pre-fix archived
   source with `--current`, not without it), or accept this
   investigation's targeted 2,953-row `current=True` comparison as the
   corrected ledger. Either way, the corrected, certifiable delta is the
   single US-IN "loan" row above — trivially small, easy to hand-verify,
   and does not require narrowing the `refers?\s+to` pattern.
4. The `local`-scope truncation issue found in passing (Q1, 208/671
   examples, e.g. MI "LEIN" cutting off mid-abbreviation, MI "school"
   dropping enumerated sub-items) is real but **pre-existing and
   unrelated to this sprint** — worth a separately-scoped follow-up, not
   a blocker here.

## Methodology / reproducibility notes

All working scripts and intermediate JSON (60-sample list + per-item raw
verb-check output, the 2,953-row `current=True` bulk comparison for both
source trees, the IN-row-80161 trace) were written to this session's
scratchpad directory (not committed, per role scope) rather than under
`docs/sprint/`. Key ad hoc scripts, all read-only against
`run/baseline-src` and this worktree's `backend/`:
- `bulk_capture.py` — mirrors `measure_actual_production.py::capture()`
  exactly (including the `current`-flag conditionals) against an
  arbitrary `(jurisdiction, source_file, source_row)` set and a chosen
  `current` value, for a given `--source-root`.
- `trace_loan3.py` — isolates `_extract_inline_quoted_definitions` output
  and `_candidate_is_substantive`'s verdict on it, for IN row 80161,
  against both source trees.
- `verb_check.py` — for the Q2 60-sample, locates the term's quoted
  occurrence in the raw parquet text and prints the defining clause that
  follows it.

All snapshot reads used `SNAPSHOT=/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad`,
the same corpus `run_gate2.sh` used. `PYTHONPATH=.:backend`,
`/Users/nerya/LexGraph/backend/.venv/bin/python` throughout, consistent
with the sprint's stated interpreter.
