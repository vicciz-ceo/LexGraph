# Expansion-wave precision sample, round 2 — sprint 2026-08-20-defs-boundary-idioms

Read-only precision sampler pass, round 2. Quantifies the combined gate-2
certification delta (Developer pass, 2026-08-23: `d660849` baseline vs
`f267644` current, Items 1+2+3 all landed) that the Developer's
STOP-and-escalate flagged: 28,654 distinct anchors = 27,568 pure-added /
64 pure-removed / 1,022 both-removed-and-added. No `backend/`/`frontend/`
files edited; two full-corpus re-measurements were run in-process (git
`archive`, never `checkout`/`reset`/`switch`/`stash` in this worktree) to
get exact, reproducible mechanism attribution rather than estimating it.

Verified before starting: `git log --oneline -1` == `d8c16fd` on
`claude/defs-boundary-idioms`.

## Method

**Anchor semantics** (unchanged from `diff_gate2.py`): an anchor is
`(jurisdiction, source_file, source_row, term)`. "Pure added" = anchor has
an added-side record and no removed-side record for the same anchor;
symmetric for "pure removed"; "both" = anchor has both (a re-bounding, not
a term gain/loss).

**Task 1 (decomposition)** required attributing each of the 27,568
pure-added anchors to a mechanism. Two independent methods were run and
cross-validated against each other:

1. **Direct mechanism attribution** (`round2_mechanism_precise.py`): for
   every distinct source row touched by a pure-added anchor, called the
   REAL, unmodified `USProfile.extract_definitions_from_section(body,
   scope=scope, heading_was_derived=False)` to get `primary_terms` (this
   flag value skips BOTH of the method's own `if heading_was_derived:`
   blocks — the Item-2 merge and the B1-preamble post-processing — so the
   result is exactly "candidates" as they stand right before the merge
   would run; confirmed by reading `us_profile.py` ~2568-2650, the primary
   block-building loop itself does not otherwise depend on
   `heading_was_derived`), and separately called the real
   `_extract_inline_quoted_definitions(body, scope=scope)` for
   `fallback_terms`. Classification: `term in primary_terms` → mechanism
   **primary** (Item 1 / baseline); else `term in fallback_terms` →
   mechanism **fallback** (only exists because Item 2's merge admitted
   it); else → **other**.
2. **Independent full-corpus re-measurement** (`diff_item1_vs_baseline.py`
   + a fresh `git archive a51b1de` + `measure_actual_production_all_rows.py
   --current`, mirroring `run_gate2.sh`'s own pattern exactly): re-ran the
   ENTIRE 2,038,247-row corpus at `a51b1de` (Item 1 alone, no Items 2/3)
   against the same `d660849` baseline, independently reproducing the
   Developer's own historical 6,309/134/1,141 figures from scratch.

These two completely independent methods produced an **exact anchor-for-
anchor match**: the 6,309 anchors from method 2 are a byte-for-byte-key
match against method 1's 6,309 "primary"-classified anchors (verified by
set equality, not just count — see Results). Method 1's "other" bucket is
empty (0 anchors) — every one of the 27,568 pure additions is fully
explained by exactly one of the two mechanisms.

**Task 2 (population-(c) precision sample)**: population (c) = pure-added
anchors in jurisdictions OUTSIDE round 1's 16-jurisdiction census (US-WA,
US-VA, US-FED, US-UT, US-TX, US-SC, US-AZ, US-NJ, US-MI, US-ND, US-NY,
US-OK, US-NM, US-NV, US-OH, US-ME) — 13,530 anchors across 31
jurisdictions (`round2_census.py`). Deterministic stratified sample of 100:
proportional allocation by jurisdiction (largest-remainder rounding, same
method round 1 used), then `random.Random(f"{20260823}:{jurisdiction}")`
(seed = this pass's own run date, disclosed; distinct from round 1's
`20260822`/`20260820` seeds since the population differs) sampling
per-jurisdiction from a stable `(source_file, source_row, term)`-sorted
pool (`round2_sample_population_c.py`). Allocation (100 across 24
jurisdictions): US-MS 30, US-CA 17, US-GA 10, US-CO 5, US-HI 5, US-MD 5,
US-WI 4, US-LA 3, US-DE 2, US-IA 2, US-MN 2, US-NC 2, US-TN 2, US-AL 1,
US-CT 1, US-DC 1, US-ID 1, US-KS 1, US-KY 1, US-MO 1, US-MT 1, US-OR 1,
US-VT 1, US-WV 1 (7 jurisdictions round to 0: US-AR/FL/IN/PA/RI/SD/WY,
each under 1% of population (c)).

Every one of the 100 was fetched from the pinned snapshot
(`.../snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad`, same one
`run_gate2.sh` uses) and classified against real source-text context
(`round2_classify_population_c.py`), not a display preview: GENUINE (real
defined term, anchor correct — D-MAP altitude) / FALSE POSITIVE / AMBIGUOUS.
Each of the 100 was ALSO run through the REAL, shipped
`_is_implausible_fallback_capture` (imported directly from
`backend/app/definition_links/us_profile.py`, not re-implemented) and
`_extract_inline_quoted_definitions`, to confirm mechanism and shipped-
filter status directly rather than assuming them.

**Task 3 (64 removals)**: every removed anchor was checked two ways — the
REAL, shipped `_is_implausible_fallback_capture` function (not a
re-implementation of its rules) called on the removed candidate, AND
direct verification against the row's real source text
(`verify_removals.py`), per the brief's explicit instruction not to take
the programmatic shape-match on faith.

**Task 4 (re-bounding sample)**: seeded 30-item sample of the 1,022
both-anchors (`random.Random(20260823).sample(...)` over a stable
`(source_file, source_row, term)`-sorted pool — same method as the
Developer's own 15-item spot check, doubled), each checked for whether the
new definition_text is a proper prefix of the old (`round2_sample_both.py`).

## Results — Task 1: decomposition of the 27,568 pure additions

| Bucket | Count | Mechanism |
|---|---|---|
| (a) Item-1 idiom-widening | **6,309** | primary engine (`extract_quote_anchored_entries` via the widened `_TIGHT_IDIOM_RE`) — exact anchor-for-anchor match between the two independent methods |
| (b) fallback-merge wave, INSIDE round 1's 16 censused jurisdictions | **7,768** | Item 2's `_merge_fallback_candidates` |
| (c) fallback-merge wave, OUTSIDE round 1's 16 censused jurisdictions | **13,491** | Item 2's `_merge_fallback_candidates` |
| (d) anything else | **0** | — every anchor is exactly one of the above |
| **Total** | **27,568** | 6,309 + 7,768 + 13,491 = 27,568 ✓ |

### Full per-jurisdiction census (all 47 jurisdictions touched)

| Jurisdiction | In round-1 census? | (a) primary/Item-1 | (b)/(c) fallback | pure removed | both (re-bounded) | total pure_added |
|---|---|---|---|---|---|---|
| US-AL | no | 0 | 74 | 0 | 0 | 74 |
| US-AR | no | 0 | 38 | 0 | 0 | 38 |
| US-AZ | yes | 794 | 45 | 0 | 10 | 839 |
| US-CA | no | 0 | 2231 | 0 | 0 | 2231 |
| US-CO | no | 0 | 643 | 0 | 0 | 643 |
| US-CT | no | 0 | 199 | 0 | 0 | 199 |
| US-DC | no | 0 | 114 | 0 | 0 | 114 |
| US-DE | no | 0 | 222 | 0 | 0 | 222 |
| US-FED | yes | 438 | 4276 | 58 | 167 | 4714 |
| US-FL | no | 0 | 42 | 0 | 0 | 42 |
| US-GA | no | 0 | 1398 | 0 | 0 | 1398 |
| US-HI | no | 0 | 688 | 0 | 0 | 688 |
| US-IA | no | 0 | 296 | 5 | 0 | 296 |
| US-ID | no | 0 | 122 | 0 | 0 | 122 |
| US-IN | no | 0 | 31 | 0 | 0 | 31 |
| US-KS | no | 0 | 184 | 0 | 0 | 184 |
| US-KY | no | 0 | 113 | 0 | 0 | 113 |
| US-LA | no | 0 | 397 | 0 | 0 | 397 |
| US-MD | no | 0 | 710 | 0 | 0 | 710 |
| US-ME | yes | 595 | 211 | 0 | 188 | 806 |
| US-MI | yes | 34 | 104 | 0 | 14 | 138 |
| US-MN | no | 0 | 306 | 0 | 0 | 306 |
| US-MO | no | 0 | 94 | 0 | 0 | 94 |
| US-MS | no | 0 | 3996 | 0 | 0 | 3996 |
| US-MT | no | 0 | 94 | 0 | 0 | 94 |
| US-NC | no | 0 | 202 | 0 | 0 | 202 |
| US-ND | yes | 87 | 141 | 0 | 15 | 228 |
| US-NJ | yes | 186 | 179 | 0 | 101 | 365 |
| US-NM | yes | 24 | 84 | 0 | 6 | 108 |
| US-NV | yes | 6 | 293 | 0 | 2 | 299 |
| US-NY | yes | 366 | 839 | 0 | 164 | 1205 |
| US-OH | yes | 2170 | 570 | 0 | 57 | 2740 |
| US-OK | yes | 129 | 146 | 0 | 42 | 275 |
| US-OR | no | 0 | 133 | 0 | 0 | 133 |
| US-PA | no | 0 | 8 | 0 | 0 | 8 |
| US-RI | **no** | **39** | 0 | 0 | **3** | 39 |
| US-SC | yes | 112 | 124 | 1 | 8 | 236 |
| US-SD | no | 0 | 5 | 0 | 0 | 5 |
| US-TN | no | 0 | 312 | 0 | 0 | 312 |
| US-TX | yes | 3 | 58 | 0 | 0 | 61 |
| US-UT | yes | 141 | 147 | 0 | 2 | 288 |
| US-VA | yes | 352 | 228 | 0 | 211 | 580 |
| US-VT | no | 0 | 142 | 0 | 0 | 142 |
| US-WA | yes | 833 | 323 | 0 | 32 | 1156 |
| US-WI | no | 0 | 494 | 0 | 0 | 494 |
| US-WV | no | 0 | 175 | 0 | 0 | 175 |
| US-WY | no | 0 | 28 | 0 | 0 | 28 |
| **TOTAL** | | **6309** | **21259** | **64** | **1022** | **27568** |

Note: US-RI is a 17th jurisdiction Item 1's widening reaches (39 primary
additions + 3 re-boundings) that round 1's census never covered either —
a small, previously-unmeasured corner of population (a)/(d), not (c); it
contains zero fallback-mechanism anchors so it does not affect the
population-(c) sample's scope or size.

### Why the wave "exceeds" round 1's 8,708 — scope, not inflation

The Developer's escalation framed the wave as "roughly 2.4× the ruling's
~8,708 figure." Directly cross-diffing round 1's own raw evidence
(`run/design_b/expansion_wave.jsonl`, still on disk) against this pass's
precise in-16-jurisdiction fallback set term-for-term shows this is
**entirely a scope difference, not within-scope inflation**:

- **Scope (the whole story for the "excess" over 8,708):** 13,491 of the
  21,259-term fallback wave (63%) sit in 31 jurisdictions round 1's own
  census explicitly never measured (their report says so directly: "like
  the Planner's own sample, this reconstruction is bounded to the same 16
  jurisdictions"). This is the entire reason total-wave-vs-8,708 looks like
  inflation — it is coverage, not a bigger effect in the same population.
- **Within the 16 jurisdictions, the real shipped wave (7,768) is actually
  SMALLER than round 1's own reconstructed estimate (8,708 raw / 8,088 after
  de-duplicating round 1's own repeated keys), not larger.** Set-diffing
  round 1's 8,088 distinct-keyed terms against this pass's 7,768: **7,761
  terms match exactly** (96% of round 1's own set); only **7 anchors are
  new** relative to round 1 (all one row, `US-FED USC` row 1389 — a single
  row outside round 1's own 100-row recovery-exclusion set); **327 anchors
  round 1's reconstruction admitted are ABSENT from the real shipped
  output**. Checking those 327 against the REAL shipped
  `_is_implausible_fallback_capture`: **274/327 (84%) are rejected by the
  extended `Pub. L.`/`Subsec.\(` filter rule** — the director's ruling that
  extended the filter came AFTER round 1's own report shipped (round 1's
  reconstruction, correctly for its own scope, could only apply the
  original stopword/year-caption filter it knew about at the time). The
  remaining 53/327 are a residual reconstruction-fidelity gap between round
  1's isolated-function simulation and the full real `capture()` pipeline —
  directly confirmed for at least one case (`STATE_OH...S3302.03`
  `"instructional materials"` is already present in the TRUE baseline
  `d660849` records, so it was never a new addition at all; round 1's own
  100-row recovery-exclusion set did not happen to cover this row).
- **Net effect**: the wave is real, its total size (21,259) is dominated by
  jurisdictions never previously sampled, and within the originally-sampled
  jurisdictions the shipped code is measurably *more* conservative than
  round 1's own model of it, not less.

## Results — Task 2: precision sample of population (c)

**Confirmed: the shipped filter is already applied in these results.**
Every one of the 100 sampled anchors is a real, current `f267644` output
record (fetched from the actual gate-2 diff, not simulated), and running
the REAL `_is_implausible_fallback_capture` against all 100 confirms
**0/100 would be rejected** by the existing stopword/`^\d{4}[—–-]`/
`Pub. L.`/`Subsec.\(` rules — exactly as expected, since these are records
the shipped filter already let through.

**Counts: 99 GENUINE / 1 FALSE POSITIVE / 0 AMBIGUOUS.**

**FP rate: 1.0%** (1/100). **Wilson 95% interval: [0.2%, 5.4%].** This is
lower than round 1's own post-filter in-scope estimate (4/100, [1.6%,
9.8%]) — consistent (both intervals overlap heavily at this sample size)
but also expected, since the shipped filter's Pub.L./Subsec. rule (which
round 1 itself validated at 0% recall cost) removes the single largest
failure mode round 1 found (garbage term key, 5/100 in their sample) before
this population was even sampled.

### New structural FP shape found: bare single-letter fallback term

The one FALSE POSITIVE in the 100-sample (#44, US-IA
`STATE_IA_TIII_C97B_S97B.49B`, term `'e'`) is **not** either of round 1's
two known shapes (garbage term key / mis-paired quote in the sense of a
multi-word phrase) — it is a **quoted single-letter cross-reference token**
mistaken for a definiendum. Source: `"...for a member with membership and
prior service in a protection occupation described in paragraph "e",
subparagraph (2), eligible service includes membership and prior service as
a sheriff or deputy sheriff as defined in section 97B.49C."` — the quoted
`"e"` is a citation to subparagraph (e), not a term being defined; the
extractor paired it with the nearby `includes` idiom belonging to
"eligible service", a different phrase entirely.

**This shape was checked against the FULL 27,568-item population, not just
the 100-sample**, since a single hit in 100 is too thin to act on alone.
Scanning all pure-added anchors for a bare single-letter term (regex
`^[A-Za-z]$`) found **19 instances total, across 4 jurisdictions**
(US-IA 16, US-CA 1, US-OH 1, US-SC 1) — **and every one of the 19 was
individually verified against real source text to be a false positive**,
splitting into two related sub-mechanisms:

- **Lettered cross-reference citation** (14 of 19, all US-IA): the same
  `paragraph "x"` / `subparagraph "x"` citation pattern as #44, verified
  directly for 14/16 Iowa instances (e.g. `STATE_IA_TXII_C490_S490.1104`
  `'b'` → source has `"...paragraph "b", that the shareholders tender..."`).
- **Classification-letter label** (5 of 19: US-CA `'B'`, US-OH `'F'`,
  US-IA `'C'`/`'D'`, US-SC `'S'`): a real, recurring classification label
  (`class "B" violation`, an `"A"`–`"F"` school performance grade, an `"S"
  corporation`) mis-paired with a defining idiom belonging to unrelated,
  distant prose — the same root mechanism as round 1's "mis-paired quote"
  shape (e.g. `Crime Stoppers`, `Warning: Electric Fence.`), just
  manifesting on single-letter classification tokens instead of multi-word
  phrases. Verified directly against source for all 5 (e.g. CA `'B'`'s
  captured definition_text is a LATER, unrelated usage-context sentence
  about appeal rights, not the row's actual "class 'B' violations are..."
  definitional clause 4,000+ characters earlier).

**Zero genuine single-letter fallback terms were found anywhere in the
27,568-item population** — 19/19 checked are false positives.

**M-R107-compliant rule**: reject a fallback candidate whose (stripped)
term matches `^[A-Za-z]$` (a single letter). This is pure term-shape, no
jurisdiction/section/term keying. **In-sample collateral: zero** — since
0/19 single-letter terms in the full current-shipped population are
genuine, and the rule only fires inside `_merge_fallback_candidates` (never
touches Item 1's primary-engine terms), there is no measured recall cost
anywhere in the corpus's current output. This rule is a strict, additional
refinement in the same spirit as the existing stopword/caption/Pub.L. rules
— narrower and cheaper to state than the "mis-paired quote" failure mode
round 1 already showed is NOT closable by any term-shape rule (that
finding stands: 0/19 single-letter cases and round 1's own 4 multi-word
mis-paired-quote cases are the SAME underlying positional defect; only the
single-letter subset happens to be catchable by shape alone, because a
real English defined term is never literally one bare letter in this
corpus, whereas a real multi-word proper noun very much can be).

### Sample table (all 100)

| # | Jurisdiction | act_id (row) | Term | Classification | Note |
|---|---|---|---|---|---|
| 1 | US-AL | STATE_AL_T45_C4_S45-4-244.20 (709) | machines, | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 2 | US-CA | STATE_CA_Chsc_D20_C6.5_A6_S25160 (74925) | e-Manifest system | GENUINE | verified against source |
| 3 | US-CA | STATE_CA_Crtc_D1_P0.5_C2_S69.3 (36941) | land owned by the claimant | GENUINE | verified against source |
| 4 | US-CA | STATE_CA_Crtc_D2_P11_C6_A2_S24306 (75385) | distribution | GENUINE | verified against source |
| 5 | US-CA | STATE_CA_Cbpc_D2_C7.7_A1_S3501 (137452) | PA | GENUINE | verified against source |
| 6 | US-CA | STATE_CA_Cbpc_D7_P3_C1_A2_S17539.15 (62398) | sweepstakes sponsor | GENUINE | verified against source |
| 7 | US-CA | STATE_CA_Cgov_T2_D3_P2.8_C4_S12926 (47950) | genetic characteristics | GENUINE | verified against source |
| 8 | US-CA | STATE_CA_Cccp_P3_T10_C1_A1_S1300 (23396) | escheat | GENUINE | verified against source |
| 9 | US-CA | STATE_CA_Cprob_D6_P1_C11_S6380 (159895) | person authorized to act in connection with international... | GENUINE | verified against source |
| 10 | US-CA | STATE_CA_Cccp_P1_T2_C3_S170.9 (76949) | judge | GENUINE | verified against source |
| 11 | US-CA | STATE_CA_Cprc_D30_P3_C3_A1_S42041 (1209) | wholesaler | GENUINE | verified against source |
| 12 | US-CA | STATE_CA_Chsc_D104_P3_C12.5_S108945 (62061) | PFAS | GENUINE | verified against source |
| 13 | US-CA | STATE_CA_Crtc_D2_P11_C4_A1_S23701t (49653) | homeowners' association | GENUINE | verified against source |
| 14 | US-CA | STATE_CA_Chsc_D27_C1_A8_S44559.1 (96469) | financial institution | GENUINE | verified against source |
| 15 | US-CA | STATE_CA_Cprc_D3_C1_A2_S3113 (26179) | witnessing the operations remotely | GENUINE | verified against source |
| 16 | US-CA | STATE_CA_Cciv_D3_P4_T1.7_C1_A2_S1791.1 (27169) | implied warranty that goods are merchantable | GENUINE | verified against source |
| 17 | US-CA | STATE_CA_Cins_D2_P2_C1.5_A2_S10199.49 (140250) | policy year | GENUINE | verified against source |
| 18 | US-CA | STATE_CA_Cgov_T6.7_D1_C2_A10.5_S63049.71 (22507) | accelerator project | GENUINE | verified against source |
| 19 | US-CO | STATE_CO_T23_A1_S23-1-125 (201) | nonpublic institution of higher education | GENUINE | verified against source |
| 20 | US-CO | STATE_CO_T39_A22_P6_S39-22-604 (2390) | validated taxpayer identification number | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 21 | US-CO | STATE_CO_T24_A48.5_P1_S24-48.5-112 (6786) | tax credit | GENUINE | verified against source |
| 22 | US-CO | STATE_CO_T24_A75_P2_S24-75-232 (13951) | federal act | GENUINE | verified against source |
| 23 | US-CO | STATE_CO_T18_A1.3_P4_S18-1.3-407 (1518) | offender | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 24 | US-CT | STATE_CT_T38a_C700c_S38a-479iii (4254) | misfill | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 25 | US-DC | STATE_DC_T28_C_S28:7-102 (4606) | issuer | GENUINE | verified against source |
| 26 | US-DE | STATE_DE_T18_C23_S2304 (2969) | Military status | GENUINE | verified against source |
| 27 | US-DE | STATE_DE_T11_C5_SIII_S917 (16276) | dwelling | GENUINE | verified against source |
| 28 | US-GA | STATE_GA_T40_C1_S40-1-1 (1242) | Former military motor vehicle | GENUINE | verified against source |
| 29 | US-GA | STATE_GA_T35_C8_S35-8-2 (2014) | Detention facility | GENUINE | verified against source |
| 30 | US-GA | STATE_GA_T48_C8_S48-8-77 (149) | transportation equipment | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 31 | US-GA | STATE_GA_T31_C41_S31-41-3 (5638) | Renovation | GENUINE | verified against source |
| 32 | US-GA | STATE_GA_T40_C1_S40-1-1 (1242) | Pedestrian hybrid beacon | GENUINE | verified against source |
| 33 | US-GA | STATE_GA_T37_C3_S37-3-1 (3171) | Psychologist | GENUINE | verified against source |
| 34 | US-GA | STATE_GA_T14_C9_S14-9-101 (23528) | Foreign limited liability company | GENUINE | verified against source |
| 35 | US-GA | STATE_GA_T48_C5_S48-5-7-7 (446) | underlying land | GENUINE | verified against source |
| 36 | US-GA | STATE_GA_T21_C4_S21-4-3 (5556) | Legal sufficiency | GENUINE | verified against source |
| 37 | US-GA | STATE_GA_T27_C1_S27-1-2 (3882) | License | GENUINE | verified against source |
| 38 | US-HI | STATE_HI_D2_T24_C431_S431 (5) | pooled insurance | GENUINE | verified against source |
| 39 | US-HI | STATE_HI_D3_T30A_C560_S560 (106) | Guardian | GENUINE | verified against source |
| 40 | US-HI | STATE_HI_D2_T24_C431_S431 (5) | Text | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 41 | US-HI | STATE_HI_D2_T24_C431_S431 (5) | Policy | GENUINE | verified against source |
| 42 | US-HI | STATE_HI_D2_T24_C431_S431 (5) | Pet insurance | GENUINE | verified against source |
| 43 | US-IA | STATE_IA_TX_C422_S422.7 (668) | farm tenancy agreement | GENUINE | verified against source |
| 44 | US-IA | STATE_IA_TIII_C97B_S97B.49B (6682) | e | **FALSE POSITIVE** | bare single-letter cross-reference: quoted "e" is a citation to "paragraph 'e', subparagraph (2)", mis-paired with the nearby "includes" idiom belonging to a different clause; NOT a definiendum (see new-FP-shape discussion above) |
| 45 | US-ID | STATE_ID_T50_C30_S50-3007 (11103) | gross revenues, | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 46 | US-KS | STATE_KS_C65_A6_S65-694 (11208) | Eligible patient | GENUINE | verified against source |
| 47 | US-KY | STATE_KY_TL_C525_S525.135 (17214) | Physical infirmity | GENUINE | verified against source |
| 48 | US-LA | STATE_LA_Crevised-statutes_T47_S339 (5285) | remote seller | GENUINE | verified against source |
| 49 | US-LA | STATE_LA_Crevised-statutes_T23_S1036.2 (26540) | Volunteer reserve police officer | GENUINE | verified against source |
| 50 | US-LA | STATE_LA_Crevised-statutes_T14_S95 (6687) | retired assistant district attorney | GENUINE | verified against source |
| 51 | US-MD | STATE_MD_Agtp_T9_S1_S9-103.1 (4905) | eligible assessment | GENUINE | verified against source |
| 52 | US-MD | STATE_MD_Agen_T9_S17_S9-1701 (27908) | sell | GENUINE | verified against source |
| 53 | US-MD | STATE_MD_Agcl_T22_S1_S22-102 (6509) | give notice | GENUINE | verified against source |
| 54 | US-MD | STATE_MD_Agtg_T7_S3_S7-309 (6932) | spouse | GENUINE | verified against source |
| 55 | US-MD | STATE_MD_Agtr_T8_S7_S8-725 (33814) | commercial or industrial activity | GENUINE | verified against source |
| 56 | US-MN | STATE_MN_P59A_79A_C72A_S72A.42 (5836) | Qualified party | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 57 | US-MN | STATE_MN_P289A_295_C290_S290.92 (3733) | reportable payment | GENUINE | verified against source |
| 58 | US-MO | STATE_MO_C137_S137.016 (1850) | transient housing | GENUINE | verified against source |
| 59 | US-MS | STATE_MS_T63_C17_S33-1 (10848) | reading , | GENUINE | verified against source |
| 60 | US-MS | STATE_MS_T75_C12_S44-5 (77983) | commissioner | GENUINE | verified against source |
| 61 | US-MS | STATE_MS_T27_C33_S39-333 (82668) | receipts | GENUINE | verified against source |
| 62 | US-MS | STATE_MS_T27_C21_S115-5 (8701) | video lottery terminal | GENUINE | verified against source |
| 63 | US-MS | STATE_MS_T45_C6_S9-205 (37344) | disclose | GENUINE | verified against source |
| 64 | US-MS | STATE_MS_T71_C5_S5-11 (312) | American employer , | GENUINE | verified against source |
| 65 | US-MS | STATE_MS_T27_C3_S7-3 (21422) | Fiscal year | GENUINE | verified against source |
| 66 | US-MS | STATE_MS_T63_C5_S7-103 (140302) | highway | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 67 | US-MS | STATE_MS_T27_C4_S7-9 (1338) | amounts distributed in partial liquidation | GENUINE | verified against source |
| 68 | US-MS | STATE_MS_T43_C13_S13-121 (5832) | committee | GENUINE | verified against source |
| 69 | US-MS | STATE_MS_T43_C3_S21-105 (355) | dependent child | GENUINE | verified against source |
| 70 | US-MS | STATE_MS_T27_C53_S77-1 (62876) | mailing | GENUINE | verified against source |
| 71 | US-MS | STATE_MS_T41_C19_S137-3 (4610) | testing facility | GENUINE | verified against source |
| 72 | US-MS | STATE_MS_T71_C1_S5-11 (12446) | United States | GENUINE | verified start; next-entry bleed — a real, separate "'United States' includes the states, D.C., Puerto Rico and the Virgin Islands" clause elsewhere in the same row |
| 73 | US-MS | STATE_MS_T63_C27_S33-1 (39880) | reading , | GENUINE | verified against source |
| 74 | US-MS | STATE_MS_T19_C1_S31-5 (12067) | district | GENUINE | verified against source |
| 75 | US-MS | STATE_MS_T27_C31_S31-48 (103282) | business enterprise operating a motor vehicle production ... | GENUINE | verified against source |
| 76 | US-MS | STATE_MS_T25_C11_S11-103 (3203) | termination from service | GENUINE | verified against source |
| 77 | US-MS | STATE_MS_T21_C37_S38-3 (142508) | United States | GENUINE | verified against source |
| 78 | US-MS | STATE_MS_T43_C31_S33-703 (24248) | notes | GENUINE | verified against source |
| 79 | US-MS | STATE_MS_T43_C5_S13-117 (2572) | border city university-affiliated pediatric teaching hosp... | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 80 | US-MS | STATE_MS_T63_C5_S17-55 (8072) | franchise agreement | GENUINE | verified against source |
| 81 | US-MS | STATE_MS_T27_C55_S55-5 (19595) | gasoline | GENUINE | verified against source |
| 82 | US-MS | STATE_MS_T27_C33_S65-111 (34341) | medicines | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 83 | US-MS | STATE_MS_T41_C17_S73-5 (17833) | hospital facilities | GENUINE | verified against source |
| 84 | US-MS | STATE_MS_T69_C5_S45-5 (90472) | program, | GENUINE | verified against source |
| 85 | US-MS | STATE_MS_T27_C29_S55-505 (19051) | department | GENUINE | verified against source |
| 86 | US-MS | STATE_MS_T27_C53_S65-241 (47799) | motel | GENUINE | verified against source |
| 87 | US-MS | STATE_MS_T37_C5_S151-201 (26226) | ELL | GENUINE | verified against source |
| 88 | US-MS | STATE_MS_T41_C13_S29-105 (25354) | selling | GENUINE | verified against source |
| 89 | US-MT | STATE_MT_T72_C2_P7_S72-2-716 (3842) | surviving descendants | GENUINE | verified against source |
| 90 | US-NC | STATE_NC_C143_S143-138 (1153) | Family Care Home | GENUINE | verified against source |
| 91 | US-NC | STATE_NC_C135_S135-4 (1252) | full liability | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 92 | US-OR | STATE_OR_T8_C79_S79.0102 (2940) | accounting for, | GENUINE | verified against source |
| 93 | US-TN | STATE_TN_T10_C7_S10-7-504 (834) | government property | GENUINE | verified against source |
| 94 | US-TN | STATE_TN_T67_C6_S67-6-392 (29516) | detailing services | GENUINE | verified via def_preview (real definitions-list "means" clause elsewhere in row; the printed context above only showed the term's first, non-defining usage) |
| 95 | US-VT | STATE_VT_T30_C5_S248 (3288) | natural gas transmission line | GENUINE | verified against source |
| 96 | US-WI | STATE_WI_C281_S281.31 (5721) | navigable waters | GENUINE | verified via def_preview (same reason as #94) |
| 97 | US-WI | STATE_WI_C700_S700.41 (13630) | Obstruction | GENUINE | verified against source |
| 98 | US-WI | STATE_WI_C66_S66.1201 (6948) | housing authority | GENUINE | verified against source |
| 99 | US-WI | STATE_WI_C403_S403.405 (17290) | Responsibility | GENUINE | verified start; next-entry bleed (long capture, anchor correct) |
| 100 | US-WV | STATE_WV_C11_A15B_S17 (2914) | product | GENUINE | verified against source |

## Results — Task 3: all 64 pure removals, individually verified

**Verdict: all 64 phantom removals. Zero genuine losses.** This does
**not** contradict the Developer's own programmatic check — it independently
confirms it at a stronger evidence bar. Every one of the 64 was checked two
ways: (1) called the REAL, shipped `_is_implausible_fallback_capture`
directly (not a re-implementation) — 64/64 match; (2) fetched the row's
real source text from the pinned snapshot and inspected the term in
context. All 64 fall into exactly two shapes, both unambiguously garbage
on inspection:

- **Legislative-history amendment caption** (44/64, all US-FED): a
  quoted `"Subsec. (x)... Pub. L. NNN–NN, ..."` editorial-notes caption
  captured as if it were a quoted definiendum, e.g. `USC_T10_C384_S4841`'s
  removed term is literally `'Subsec. (e)(2). Pub. L. 105–261, §213(d),
  amended par. (2) generally. Prior to...'` — verified against source: this
  text is legislative-amendment history, never a definiendum.
- **Bare stopword term** (20/64: 13× `'for'` + 1× `'or'` in US-FED, 5×
  `'a'` in US-IA, 1× `'for'` in US-SC): verified against source in every
  case — e.g. `STATE_IA_TIII_C97B_S97B.49B`'s removed `'a'` is a stray
  list-marker letter inside ordinary prose (`"(1) (a) The seller shall
  obtain..."`), not a definiendum; the US-FED `'for'`/`'or'` instances are
  the same shape — a stray conjunction/preposition from ordinary prose,
  never a definiendum, recurring across 14 different US-FED rows.

Baseline (`d660849`, pre-fix) had admitted all 64 as junk via the OLD,
unconditional `if not candidates: candidates =
_extract_inline_quoted_definitions(...)` substitution (no filter existed
at all pre-fix); the shipped filter now correctly rejects them everywhere
this shape occurs corpus-wide, not only on the 4 rows investigation.md
originally named. No genuine loss is present in this set, singly or
otherwise.

### 64-removal table

| # | Jurisdiction | act_id (row) | Term (truncated) | Shipped filter rejects | Verdict |
|---|---|---|---|---|---|
| 1 | US-FED | USC_T10_C384_S4841 (11106) | Subsec. (e)(2). Pub. L. 105–261, §213(d), amended pa... | True | PHANTOM (garbage term key) |
| 2 | US-FED | USC_T49_C301_S30101 (1111) | National Highway Traffic Safety Administration Outre... | True | PHANTOM (garbage term key) |
| 3 | US-FED | USC_T26_C1_S46 (1115) | . Subsec. (a)(2)(F)(iii)(III). Pub. L. 97–448, §102... | True | PHANTOM (garbage term key) |
| 4 | US-FED | USC_T26_C1_S46 (1115) | for | True | PHANTOM (stopword) |
| 5 | US-FED | USC_T1_C1_S1 (11310) | Continental United States Pub. L. 86–70, §48, June ... | True | PHANTOM (garbage term key) |
| 6 | US-FED | USC_T20_C28_S1077 (11818) | . Statutory Notes and Related Subsidiaries Effecti... | True | PHANTOM (garbage term key) |
| 7 | US-FED | USC_T12_C16_S1811 (1260) | Short Title of 1990 Amendment Pub. L. 101–508, titl... | True | PHANTOM (garbage term key) |
| 8 | US-FED | USC_T10_C16_S333 (12650) | for | True | PHANTOM (stopword) |
| 9 | US-FED | USC_T10_C324_S4351 (1337) | . Subsec. (a)(4). Pub. L. 103–355, §3002(c), substi... | True | PHANTOM (garbage term key) |
| 10 | US-FED | USC_T10_C324_S4351 (1337) | for | True | PHANTOM (stopword) |
| 11 | US-FED | USC_T10_C87_S1746 (13804) | 2022—Subsec. (b)(2). Pub. L. 117–263, §832(a)(1)(A),... | True | PHANTOM (garbage term key) |
| 12 | US-FED | USC_T10_C2_S115a (13992) | for | True | PHANTOM (stopword) |
| 13 | US-FED | USC_T20_C28_S1090 (1508) | Pub. L. 105–244, §482(a)(2)(C), substituted | True | PHANTOM (garbage term key) |
| 14 | US-FED | USC_T21_C9_S301 (16237) | Pub. L. 113–54, title I, §101, Nov. 27, 2013, 127 St... | True | PHANTOM (garbage term key) |
| 15 | US-FED | USC_T28_C176_S3003 (17639) | or | True | PHANTOM (stopword) |
| 16 | US-FED | USC_T10_C20_S407 (18434) | . Subsec. (e). Pub. L. 112–81, §1092(a)(5), added s... | True | PHANTOM (garbage term key) |
| 17 | US-FED | USC_T10_C20_S407 (18434) | for | True | PHANTOM (stopword) |
| 18 | US-FED | USC_T11_C5_S559 (18593) | for | True | PHANTOM (stopword) |
| 19 | US-FED | USC_T18_C25_S474 (1988) | . Subsec. (b). Pub. L. 107–56, §374(e)(2), inserted... | True | PHANTOM (garbage term key) |
| 20 | US-FED | USC_T42_C129_S12594 (20991) | for | True | PHANTOM (stopword) |
| 21 | US-FED | USC_T49_C1_S101 (22756) | Defined Pub. L. 106–159, §2, Dec. 9, 1999, 113 Stat... | True | PHANTOM (garbage term key) |
| 22 | US-FED | USC_T49_C1_S101 (22756) | Pub. L. 102–240, §3, Dec. 18, 1991, 105 Stat. 1915, ... | True | PHANTOM (garbage term key) |
| 23 | US-FED | USC_T23_C1_S131 (2333) | for | True | PHANTOM (stopword) |
| 24 | US-FED | USC_T42_C69_S5301 (301) | Acquisition of Tenant-Occupied Foreclosed Dwelling o... | True | PHANTOM (garbage term key) |
| 25 | US-FED | USC_T50_C50_S3937 (30303) | and added subpars. (A) and (B). Subsec. (d). Pub. L... | True | PHANTOM (garbage term key) |
| 26 | US-FED | USC_T44_C13_S1307 (3377) | 1986—Subsec. (a). Pub. L. 99–272 amended subsec. (a)... | True | PHANTOM (garbage term key) |
| 27 | US-FED | USC_T18_C113_S2319A (34432) | 2006—Subsec. (e)(2). Pub. L. 109–181 added par. (2) ... | True | PHANTOM (garbage term key) |
| 28 | US-FED | USC_T19_C4_S1307 (35636) | 2000—Pub. L. 106–200 inserted at end | True | PHANTOM (garbage term key) |
| 29 | US-FED | USC_T16_C1_S460ttt (36151) | Definitions Pub. L. 109–382, §2, Dec. 1, 2006, 120 ... | True | PHANTOM (garbage term key) |
| 30 | US-FED | USC_T11_C5_S556 (37270) | for | True | PHANTOM (stopword) |
| 31 | US-FED | USC_T10_C159_S2662 (3770) | . Subsec. (f)(4). Pub. L. 111–383, §2811(f)(3)(C), ... | True | PHANTOM (garbage term key) |
| 32 | US-FED | USC_T10_C159_S2662 (3770) | . Subsec. (g)(4). Pub. L. 110–181, §2821(a)(3), add... | True | PHANTOM (garbage term key) |
| 33 | US-FED | USC_T16_C28_S1274 (386) | Pub. L. 111–11, title I, §1976(b), Mar. 30, 2009, 12... | True | PHANTOM (garbage term key) |
| 34 | US-FED | USC_T38_C51_S5103A (3965) | Subsec. (c). Pub. L. 112–154, §505(b), amended subse... | True | PHANTOM (garbage term key) |
| 35 | US-FED | USC_T38_C3_S303 (403) | Pub. L. 116–136, div. B, title X, §20003, Mar. 27, 2... | True | PHANTOM (garbage term key) |
| 36 | US-FED | USC_T28_C87_S1404 (40581) | . 1996—Subsec. (d). Pub. L. 104–317 amended subsec.... | True | PHANTOM (garbage term key) |
| 37 | US-FED | USC_T11_C5_S560 (41094) | for | True | PHANTOM (stopword) |
| 38 | US-FED | USC_T12_C14_S1782 (4353) | . Subsec. (h)(2). Pub. L. 98–369, §2809, in amendin... | True | PHANTOM (garbage term key) |
| 39 | US-FED | USC_T12_C14_S1782 (4353) | for | True | PHANTOM (stopword) |
| 40 | US-FED | USC_T10_C146_S2474 (4486) | Pub. L. 106–398, §1 [[div. A], title III, §341(c)(1)... | True | PHANTOM (garbage term key) |
| 41 | US-FED | USC_T15_C14B_S687 (4667) | 1999—Subsec. (i)(2). Pub. L. 106–9 inserted at end: | True | PHANTOM (garbage term key) |
| 42 | US-FED | USC_T12_C2_S84 (4978) | 2010—Subsec. (b)(1). Pub. L. 111–203, §610(a)(1), su... | True | PHANTOM (garbage term key) |
| 43 | US-FED | USC_T12_C2_S84 (4978) | for | True | PHANTOM (stopword) |
| 44 | US-FED | USC_T11_C3_S365 (5134) | , could not be executed because subsec. (p) was repe... | True | PHANTOM (garbage term key) |
| 45 | US-FED | USC_T10_C135_S2271 (5658) | [Pub. L. 115–31, div. N, title VI, §605(a), May 5, 2... | True | PHANTOM (garbage term key) |
| 46 | US-FED | USC_T10_C2_S113 (691) | U.S. Basing, Training, and Exercises in North Atlant... | True | PHANTOM (garbage term key) |
| 47 | US-FED | USC_T49_C301_S30120 (7199) | Pub. L. 106–414, §6(b), inserted at end | True | PHANTOM (garbage term key) |
| 48 | US-FED | USC_T10_C9_S221 (7273) | Budgeting of Department of Defense Relating to Opera... | True | PHANTOM (garbage term key) |
| 49 | US-FED | USC_T10_C9_S221 (7273) | Identification in President's Budget of NATO Costs ... | True | PHANTOM (garbage term key) |
| 50 | US-FED | USC_T10_C9_S221 (7273) | Inclusion of Aircraft Carrier Refueling Overhaul Bud... | True | PHANTOM (garbage term key) |
| 51 | US-FED | USC_T22_C78_S7107 (7935) | for | True | PHANTOM (stopword) |
| 52 | US-FED | USC_T38_C73_S7362 (8728) | Subsec. (b)(2). Pub. L. 111–163, §802(d), substituted | True | PHANTOM (garbage term key) |
| 53 | US-FED | USC_T38_C73_S7362 (8728) | before period at end. Subsec. (b). Pub. L. 111–163,... | True | PHANTOM (garbage term key) |
| 54 | US-FED | USC_T38_C73_S7362 (8728) | in introductory provisions. Subsec. (b)(1). Pub. L.... | True | PHANTOM (garbage term key) |
| 55 | US-FED | USC_T22_C32_S2381 (884) | Pub. L. 102–391, title V, §599E, Oct. 6, 1992, 106 S... | True | PHANTOM (garbage term key) |
| 56 | US-FED | USC_T7_C13_S343 (9384) | Subsec. (h)(2)(D). Pub. L. 115–334, §7612(a)(1), str... | True | PHANTOM (garbage term key) |
| 57 | US-FED | USC_T10_C50_S992 (9583) | Inclusion of Information on Free Credit Monitoring i... | True | PHANTOM (garbage term key) |
| 58 | US-FED | USC_T35_C1_S1 (9683) | . Statutory Notes and Related Subsidiaries Change ... | True | PHANTOM (garbage term key) |
| 59 | US-IA | STATE_IA_TVII_C256_S256.25A (10329) | a | True | PHANTOM (stopword) |
| 60 | US-IA | STATE_IA_TXIII_C527_S527.5 (1739) | a | True | PHANTOM (stopword) |
| 61 | US-IA | STATE_IA_TX_C423_S423.51 (23243) | a | True | PHANTOM (stopword) |
| 62 | US-IA | STATE_IA_TIX_C403_S403.19 (5153) | a | True | PHANTOM (stopword) |
| 63 | US-IA | STATE_IA_TX_C452A_S452A.33 (8423) | a | True | PHANTOM (stopword) |
| 64 | US-SC | STATE_SC_T58_C4_S58-4-10 (9131) | for | True | PHANTOM (stopword) |

## Results — Task 4: 30-item re-bounding spot check

**Verdict: 30/30 improving. Zero corrupted/displaced pairs.** 29/30 show
the simple shape (new definition_text is a proper prefix of old — a
tighter, correct boundary replacing a run-on capture that used to bleed
into the next entry). The one exception (#27, US-OH `Law enforcement
officer`) is a DIFFERENT but still-improving shape: new (201 chars) is
LONGER than old (141 chars) and is not a prefix of it — verified directly
against source (`STATE_OH_T29_C2911_S2911.01`): the true, complete
definition is `'"Law enforcement officer" has the same meaning as in
section 2901.01 of the Revised Code and also includes employees of the
department of rehabilitation and correction...'`; OLD captured only the
tail (`"employees of the department..."`), missing the true opening because
baseline could not recognize `"has the same meaning"` as a start-idiom
(only plain `"has the meaning"` was recognized pre-Item-1); NEW correctly
captures from the true start once Item 1's generalized `has the (following
|same) meaning` regex recognizes it. This is a genuine start-of-definition
recovery, not a displacement — confirms Item 1's OWN intended effect
reaching into a re-bounded (not just newly-added) anchor.

### Re-bounding sample table (30 items)

| # | Jurisdiction | act_id (row) | Term | Old len | New len | New is prefix of old | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | US-NY | row 30360 | board | 195 | 58 | True | IMPROVING (tighter boundary) |
| 2 | US-VA | row 12567 | Commission | 441 | 177 | True | IMPROVING (tighter boundary) |
| 3 | US-NY | row 317 | place of public assembly | 14213 | 859 | True | IMPROVING (tighter boundary) |
| 4 | US-VA | row 178 | ERISA | 163 | 99 | True | IMPROVING (tighter boundary) |
| 5 | US-FED | row 30097 | horseracing anti-doping and medication control program | 286 | 127 | True | IMPROVING (tighter boundary) |
| 6 | US-VA | row 1374 | Net bill | 212 | 124 | True | IMPROVING (tighter boundary) |
| 7 | US-ME | row 8679 | Director | 343 | 191 | True | IMPROVING (tighter boundary) |
| 8 | US-WA | row 20523 | children who are the subject of a dependency proceeding | 202 | 140 | True | IMPROVING (tighter boundary) |
| 9 | US-FED | row 4194 | child | 261 | 123 | True | IMPROVING (tighter boundary) |
| 10 | US-VA | row 32783 | Custody services | 144 | 77 | True | IMPROVING (tighter boundary) |
| 11 | US-ME | row 10304 | Cosmetic animal testing | 410 | 247 | True | IMPROVING (tighter boundary) |
| 12 | US-NY | row 21607 | Agency | 692 | 380 | True | IMPROVING (tighter boundary) |
| 13 | US-NY | row 20964 | sufficient proof of authority | 382 | 99 | True | IMPROVING (tighter boundary) |
| 14 | US-NY | row 3883 | Calculating person | 529 | 218 | True | IMPROVING (tighter boundary) |
| 15 | US-OK | row 21074 | eligible taxes | 1417 | 201 | True | IMPROVING (tighter boundary) |
| 16 | US-ME | row 5133 | Tangible benefits | 1413 | 1010 | True | IMPROVING (tighter boundary) |
| 17 | US-FED | row 36087 | Federal savings association | 276 | 128 | True | IMPROVING (tighter boundary) |
| 18 | US-NJ | row 471 | market risks | 19996 | 6013 | True | IMPROVING (tighter boundary) |
| 19 | US-VA | row 12567 | Domestic partnership | 735 | 258 | True | IMPROVING (tighter boundary) |
| 20 | US-OH | row 15488 | Commercial driver's license | 413 | 109 | True | IMPROVING (tighter boundary) |
| 21 | US-WA | row 32992 | Washington bank | 103 | 38 | True | IMPROVING (tighter boundary) |
| 22 | US-VA | row 5843 | notary | 179 | 142 | True | IMPROVING (tighter boundary) |
| 23 | US-FED | row 253 | financial institution | 272 | 193 | True | IMPROVING (tighter boundary) |
| 24 | US-NY | row 17368 | Urban area of the state | 781 | 173 | True | IMPROVING (tighter boundary) |
| 25 | US-OH | row 7417 | consumer goods | 139 | 50 | True | IMPROVING (tighter boundary) |
| 26 | US-NJ | row 23598 | Fund | 522 | 97 | True | IMPROVING (tighter boundary) |
| 27 | US-OH | row 3369 | Law enforcement officer | 141 | 201 | False | IMPROVING (recovers true start, verified against source — see above) |
| 28 | US-ME | row 11927 | Confirmatory adoption | 333 | 225 | True | IMPROVING (tighter boundary) |
| 29 | US-AZ | row 6600 | deficit groundwater | 4504 | 1256 | True | IMPROVING (tighter boundary) |
| 30 | US-VA | row 8411 | Rental in the Commonwealth | 232 | 96 | True | IMPROVING (tighter boundary) |

## Implications (evidence only — no decision)

- **The decomposition fully reconciles: 6,309 + 7,768 + 13,491 = 27,568,
  with zero unexplained residue.** Two independent measurement methods
  (direct per-anchor mechanism attribution on the shipped code, and a fresh
  full-corpus re-measurement at `a51b1de` alone) produce an exact
  anchor-for-anchor match on the 6,309 Item-1-attributable additions. The
  entire 27,568 splits cleanly into "found by the primary engine" (6,309)
  and "found only because Item 2's merge admitted it" (21,259) with no
  third category.
- **The wave's apparent 2.4× excess over round 1's 8,708 is a scope
  artifact, not a bigger effect than measured.** 13,491 of the 21,259-term
  fallback wave (63%) sit entirely outside the 16 jurisdictions round 1
  ever sampled — this is the whole story. Within those 16 jurisdictions,
  direct term-level comparison against round 1's own preserved raw
  evidence shows the real shipped wave (7,768) is smaller than round 1's
  own reconstruction (8,088 de-duplicated / 8,708 raw), not larger: 96% of
  round 1's own terms match exactly, and 84% of the terms round 1 had that
  this pass lacks are explained by the extended `Pub. L.`/`Subsec.\(`
  filter rule the director added AFTER round 1's report shipped (i.e., the
  shipped code is stricter than what round 1 modeled, in round 1's own
  favor).
- **Population (c) (the 13,530 previously-unmeasured, out-of-scope
  additions) measures at 1% FP with a wide-but-low Wilson interval ([0.2%,
  5.4%]) — at or below round 1's own post-filter, in-scope rate (4%,
  [1.6%, 9.8%]).** No evidence this out-of-scope population is riskier than
  the one round 1 already certified; if anything the point estimate is
  lower, though the intervals overlap enough that "materially different"
  is not established either way at n=100 each.
- **One new, narrow, fully-quantified structural FP shape was found and
  fully censused (not just sampled): bare single-letter fallback terms.**
  19 instances exist in the entire current 27,568-item population, spread
  across 4 jurisdictions; all 19 were individually verified against source
  text to be false positives (either a lettered cross-reference citation or
  a classification-letter label mis-paired with a distant idiom — never a
  real one-letter definiendum anywhere in this corpus). A single
  M-R107-compliant rule (reject a fallback term matching `^[A-Za-z]$`)
  would close 100% of this shape's *measured* incidence at zero measured
  collateral (0/19 genuine hits anywhere in the corpus's current output).
  The larger multi-word "mis-paired quote" failure mode round 1 already
  identified as unclosable by term-shape rules is independently confirmed
  unclosed by this pass too (this pass's own FP, and 4 of the single-letter
  FPs, are that same root mechanism; no new evidence changes round 1's own
  conclusion that fixing it needs positional/span tracking forbidden by
  the amended gate 7).
- **All 64 pure removals are phantom (verified against source text, not
  just the shape match); all 30 sampled re-boundings are improving
  (verified; one via a different but still-clearly-improving shape).**
  Neither population contributes a genuine loss or a corrupted/displaced
  anchor in the sampled/censused evidence gathered by this pass.

---

Reproduce: `PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python`
+ `round2_census.py` (buckets `run/compare/changed.jsonl` into pure_added/
pure_removed/both), `round2_mechanism_precise.py` (full 27,568-anchor
mechanism census — re-runs `_extract_inline_quoted_definitions` /
`extract_definitions_from_section` per touched row against the pinned
snapshot), `diff_item1_vs_baseline.py` (needs a fresh `git archive a51b1de`
+ `measure_actual_production_all_rows.py --current` re-run first, per
`run_gate2.sh`'s own pattern, against `run/item1-src` → `run/item1`),
`round2_sample_population_c.py` + `round2_classify_population_c.py`
(population-(c) sample), `verify_removals.py` (64 removals),
`round2_sample_both.py` (30-item re-bounding sample). All scripts in this
directory; raw outputs land under `run/item1/`, `run/item1-src/`, and
`run/round2/` (gitignored — regenerate as above).
