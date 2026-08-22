# Expansion-wave precision sample — sprint 2026-08-20-defs-boundary-idioms

Read-only precision sampler pass. Quantifies Item 2 design (b)'s "expansion
wave" (log doc: "Planner pass 2, Item 2 design" — the 61/200-row seeded
sample, 122-new-term footprint on rows where the primary engine already
finds ≥1 entry). No `backend/`/`frontend/` files touched; all
pre-fix/post-fix/design-(b) comparisons run in-process by calling the real,
unmodified `extract_definitions_from_section` / `_extract_inline_quoted_
definitions` directly and applying design (b)'s merge/filter as a pure
function over their outputs — never `git checkout`/`reset`/`switch`/`stash`
in this worktree.

Verified before starting: `git log --oneline -1` == `326f898` on
`claude/defs-boundary-idioms`.

## Method

### 1. Reconstructing the expansion wave

Design (b)'s guard-site change (`us_profile.py` ~2551) is not yet landed in
code (only Item 1 is; Items 2–3 exist as RED tests/specs). Per the brief,
this pass reconstructs design (b) in-process rather than editing
`backend/`. Script: `measure_design_b_expansion_wave.py` (committed, this
directory).

**Key simplification, verified rather than assumed**: for the population
this task targets — rows where TODAY's (HEAD `326f898`, Item 1 landed,
Items 2–3 not) `extract_definitions_from_section` already returns ≥1
candidate — the existing guard's `if not candidates` branch is provably
False, so calling the REAL, unpatched `extract_definitions_from_section`
already returns exactly the primary engine's own candidates (the fallback
never fires for these rows in production today). So no class monkeypatch
is needed for this half; the script calls that real function to get
`primary_candidates`, separately calls the real, unmodified
`_extract_inline_quoted_definitions` to get the fallback's own candidates,
and applies design (b)'s merge/filter (`admit_fallback`, a pure function)
to decide what design (b) would newly admit. This is mechanically
equivalent to monkeypatching the guard and calling through it — for this
specific population the branch design (b) changes is never taken by
unpatched code, so calling around it is the same as calling through a
patch of it. The filter itself is design (b)'s own spec, exactly: reject a
fallback term that collides with any primary term on the row, or that is a
bare stopword (`for/and/or/the/a/an/of/in/to/with/by`) or begins with
`^\d{4}[—–-]` (a 4-digit year + dash amendment-caption shape).

**Scope**: the same 16 jurisdictions the Planner's own seeded sample used
("reachable through family-3/OH/ME": US-WA, US-VA, US-FED, US-UT, US-TX,
US-SC, US-AZ, US-NJ, US-MI, US-ND, US-NY, US-OK, US-NM, US-NV, US-OH,
US-ME) — not a different population, per the brief's "do not invent a
variant." Unlike the Planner's 200-row sample, this pass runs the **full**
row population within those 16 jurisdictions' files (683,393 rows) against
the pinned snapshot named in `run_gate2.sh`
(`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad`)
— a full census within the Planner's own scope, not a variant of the
mechanism, chosen so the later 100-item sample is a real draw rather than
a near-census of a 122-item population.

**Excluding the 130-loss recoveries**: rows in investigation.md's Q1 table
(134 removed terms → 100 distinct `(jurisdiction, source_row)` rows, all
`FALLBACK_SUPPRESSION`) are excluded from the wave population — design
(b)'s merge on those rows IS the 130-loss recovery, not new incremental
expansion, and the task's scope is the latter. Spot-verified directly (not
just trusted from investigation.md): patched
`us_profile._extract_inline_quoted_definitions` to return `[]` in the
archived pre-fix source (`run/baseline-src`, still on disk from the
Developer pass) so the old guard's substitution becomes a no-op, then
called `extract_definitions_from_section` on 6 of the 100 excluded rows
(FED 72, FED 12889, WA 717, OH 3296, NY 1978, OK 4467) — all 6 show
`BASELINE pre-fallback primary candidates = 0`, confirming these rows are
exactly the "all current primary entries are new-idiom-derived" population
investigation.md's Q1 measured at 100/100.

**Result** (`run/design_b/summary.json`, not committed — 29MB raw dump,
`.gitignore`d; regenerate via the committed script):

```
rows_scanned_16_jurisdictions:                683,393
rows_heading_was_derived:                      46,812
rows_primary_nonempty_today:                   45,283
rows_primary_nonempty_excluding_130_recovery:  45,183
rows_gaining_new_fallback_terms:                4,419
new_terms_total:                                8,708
by_jurisdiction: AZ 47 / FED 5,110 / ME 219 / MI 109 / ND 149 / NJ 181 /
  NM 85 / NV 294 / NY 859 / OH 594 / OK 149 / SC 131 / TX 62 / UT 155 /
  VA 233 / WA 331
```

**Correction to the Planner's own extrapolation.** The Planner's 200-row
seeded sample found 61/200 (30.5%) of eligible rows gaining terms and
extrapolated "~13,100 of ~42,974 rows" corpus-wide. This pass's full
16-jurisdiction census finds the TRUE rate is 4,419/45,183 = **9.8%** —
about **3.1× lower** than the Planner's sampled rate. The wave is real and
substantial (8,708 terms / 4,419 rows), but materially smaller than the
Planner's own extrapolation suggested; their 200-row sample happened to
over-represent term-gaining rows (plausibly because it was proportional
by jurisdiction rather than by row-count, and OH/AZ/UT/VA/WA/ME's dense
`"has the (same/following) meaning"` forwarding idiom — Item 1's own
target shape — clusters unevenly across a 200-row draw).

**Scope caveat**: like the Planner's own sample, this reconstruction is
bounded to the same 16 jurisdictions. Design (b)'s guard change is
jurisdiction-agnostic (fires whenever `heading_was_derived`, in any
`US-*` code) — a full 53-file gate-2-style run could in principle surface
additional expansion-wave rows outside these 16 (e.g. CA/IL/GA-style
wave-6 body-derived-heading rows whose primary candidates come from
baseline block-splitting or B1, not family-3). That run is out of this
task's scope (the brief names the 16-jurisdiction population explicitly);
this pass's 8,708/4,419 should be read as a rigorous measurement of that
named population, not a certified full-corpus number.

### 2. Precision sample

Deterministic stratified sample of 100 items from the 8,708-item wave:
proportional allocation by jurisdiction (largest-remainder rounding, same
method investigation.md's Q2/Q3 used), then `random.Random(f"{20260822}:
{jurisdiction}")` (seed = this pass's own run date, disclosed; distinct
from the Planner's 2026-08-20/21 seeds since the underlying population
also differs — a full census here, not their 200-row sample) sampling
per-jurisdiction from a stable pre-sort order. Script:
`sample_design_b_expansion_wave.py` (committed). Allocation: FED 59, ME 2,
MI 1, ND 2, NJ 2, NM 1, NV 3, NY 10, OH 7, OK 2, SC 1, TX 1, UT 2, VA 3,
WA 4 (AZ rounded to 0 — its population share, 47/8708, is below 1/100).

Each of the 100 items was classified against the row's real source text
(fetched from the pinned snapshot), not the display-truncated preview:
GENUINE (real defined term, anchor correct — D-MAP altitude: anchor
correctness is the bar, byte-perfection is not) / FALSE POSITIVE (not a
real defined term, or text substantively another entry's content) /
AMBIGUOUS. 58 of the 100 were verified directly against source text
(quoted below or in the script's evidence trail); the remaining 42 were
classified by a preview-pattern rule established and cross-checked against
those 58 direct verifications (a complete, well-formed clause = GENUINE;
a dangling next-entry lead-in fragment = GENUINE with a bleed defect; no
term in the entire 100-item sample showed a term-key shape resembling the
two confirmed false-positive patterns without being individually checked).

## Results

**Counts: 90 GENUINE / 9 FALSE POSITIVE / 1 AMBIGUOUS.**

**FP rate: 9.0%** (9/100; 9.09% if the denominator excludes the 1
AMBIGUOUS; 10.0% if AMBIGUOUS is folded into FALSE POSITIVE as a
conservative upper bound). **Rough 95% interval** (Wilson score, more
reliable than normal approximation at this n): **[4.8%, 16.2%]** for the
9% point estimate ([5.5%, 17.4%] if AMBIGUOUS is counted as FALSE
POSITIVE).

This is roughly double the Planner's own 20-item spot-check rate (1/20 =
5%, "one is an outright false positive with a garbage numeric term key")
— consistent within a wide interval, but this pass's deeper 100-item,
source-verified sample also surfaces a **second, distinct false-positive
failure mode** (mis-paired quote, below) the Planner's 20-item glance
never saw at all, having only observed the garbage-term-key shape.

### Sample table (all 100)

| # | Jurisdiction | act_id (row) | Term | Classification | Failure mode | Note |
|---|---|---|---|---|---|---|
| 1 | US-FED | USC_T19_C24_S3805 (130) | Panamanian article | GENUINE | next-entry bleed (short) | core def correct; trails into next entry's own lead-in |
| 2 | US-FED | USC_T19_C24_S3805 (130) | RVC | GENUINE | next-entry bleed (short) | |
| 3 | US-FED | USC_T19_C24_S3805 (130) | adjusted value | GENUINE | next-entry bleed (severe) | engulfs an ENTIRE separate term's complete definition before trailing off |
| 4 | US-FED | USC_T19_C24_S3805 (130) | applicable NTR (MFN) rate of duty | GENUINE | next-entry bleed (short) | |
| 5 | US-FED | USC_T19_C24_S3805 (130) | component of the good that determines the tariff classification... | GENUINE | next-entry bleed (severe) | engulfs a separate rule paragraph + a header + start of another definition |
| 6 | US-FED | USC_T19_C24_S3805 (130) | material | GENUINE | next-entry bleed (short) | |
| 7 | US-FED | USC_T19_C24_S3805 (130) | material produced in the territory of Oman or the United States... | GENUINE | next-entry bleed (moderate) | |
| 8 | US-FED | USC_T50_C44_S3024 (149) | International Mobile Subscriber Identity-catcher | GENUINE | clean | no trailing artifact |
| 9 | US-FED | USC_T49_C449_S44901 (286) | Administrator | GENUINE | next-entry bleed (short) | |
| 10 | US-FED | USC_T42_C8_S1437f (294) | affiliate of the purchaser | GENUINE | next-entry bleed (short) | |
| 11 | US-FED | USC_T15_C14A_S636 (443) | ".. Pub. L. 101–37, §7(a)(3), in subpar. (F)..." | FALSE POSITIVE | garbage term key | term is an Editorial-Notes amendment caption, not a definiendum |
| 12 | US-FED | USC_T10_C159_S2687 (492) | nonappropriated fund instrumentality | GENUINE | next-entry bleed (severe/unbounded) | runs into an embedded quoted Executive-Order-style Act text |
| 13 | US-FED | USC_T12_C17_S1851 (585) | sponsor | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 14 | US-FED | USC_T12_C13_S1715l (834) | going Federal rate | GENUINE | next-entry bleed (severe) | verified start; 20,282-char runaway |
| 15 | US-FED | USC_T38_C17_S1703 (930) | severe maternal morbidity | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 16 | US-FED | USC_T42_C152_S17013 (1408) | engineering integration costs | GENUINE | next-entry bleed (short) | pattern-consistent |
| 17 | US-FED | USC_T16_C55_S3503 (1731) | pilot project | GENUINE | next-entry bleed (short) | |
| 18 | US-FED | USC_T18_C47_S1030 (1935) | government entity | GENUINE | next-entry bleed (short) | pattern-consistent |
| 19 | US-FED | USC_T26_C1_S432 (1992) | ".. Subsec. (i)(9). Pub. L. 110–458..." | FALSE POSITIVE | garbage term key | Editorial-Notes amendment caption; 16,352-char runaway |
| 20 | US-FED | USC_T49_C447_S44701 (2046) | Flight Standards Evaluation Program | GENUINE | clean | |
| 21 | US-FED | USC_T49_C447_S44701 (2046) | Secretary | GENUINE | next-entry bleed (short) | |
| 22 | US-FED | USC_T49_C447_S44701 (2046) | U.S. Hazardous Materials Regulations | GENUINE | clean | |
| 23 | US-FED | USC_T20_C28_S1091 (2391) | apprenticeship | FALSE POSITIVE | other (mis-paired quote) | quote is a cross-reference parenthetical; idiom matched belongs to clause (C) of a DIFFERENT term's own list |
| 24 | US-FED | USC_T31_C5_S501 (2539) | inherently governmental function | GENUINE | next-entry bleed (short) | own multi-part (A)/(B)/(C) structure correctly captured; only trailing SEC. 6 boilerplate is bleed |
| 25 | US-FED | USC_T12_C47_S4713a (2595) | eligible community or economic development purpose | GENUINE | next-entry bleed (short) | pattern-consistent |
| 26 | US-FED | USC_T42_C8_S1437d (2623) | "Subsec. (q)(5) to (8). Pub. L. 105–276..." | FALSE POSITIVE | garbage term key | Pub. L. amendment caption; 37,561-char runaway |
| 27 | US-FED | USC_T15_C14A_S644 (2857) | Pilot Program | GENUINE | next-entry bleed (short) | verified |
| 28 | US-FED | USC_T42_C85_S7675 (3013) | consumption | GENUINE | next-entry bleed (short) | pattern-consistent |
| 29 | US-FED | USC_T15_C14B_S683 (3284) | prioritized payments | GENUINE | list-introducer stub | verified; trails into "As used in this subsection," |
| 30 | US-FED | USC_T42_C86_S7704 (3479) | Director | GENUINE | next-entry bleed (short) | pattern-consistent |
| 31 | US-FED | USC_T42_C7_S1395mm (4073) | new medicare enrollee | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 32 | US-FED | USC_T42_C7_S1382b (4355) | benefits under this subchapter | GENUINE | next-entry bleed (short) | pattern-consistent |
| 33 | US-FED | USC_T23_C5_S503 (4601) | volunteer participant | GENUINE | next-entry bleed (severe/unbounded) | verified start; swallows ~20 unrelated subsections (b)-(o) |
| 34 | US-FED | USC_T31_C33_S3332 (4841) | Executive agency | GENUINE | clean | |
| 35 | US-FED | USC_T15_C123_S9901 (6317) | qualified divestiture | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 36 | US-FED | USC_T42_C6A_S297n (6992) | migrant health center | GENUINE | next-entry bleed (short) | |
| 37 | US-FED | USC_T47_C5_S336 (7881) | eligible licensee or permittee | GENUINE | next-entry bleed (minor) | verified start; ends on a complete, correctly-bounded sentence |
| 38 | US-FED | USC_T5_C33_S3330d (8456) | military spouse | GENUINE | next-entry bleed (short) | pattern-consistent |
| 39 | US-FED | USC_T50_C44_S3232a (9606) | agency | GENUINE | next-entry bleed (short) | pattern-consistent |
| 40 | US-FED | USC_T17_C14_S1401 (10193) | anyone | GENUINE | next-entry bleed (severe) | verified; real "Rule of construction" broadening "anyone" to state actors |
| 41 | US-FED | USC_T23_C2_S217 (10254) | community | GENUINE | next-entry bleed (short) | pattern-consistent |
| 42 | US-FED | USC_T26_C11_S2056A (11129) | property | GENUINE | next-entry bleed (short) | pattern-consistent; real (if circular-looking) QDOT estate-tax def |
| 43 | US-FED | USC_T42_C85_S7413 (11988) | person | GENUINE | next-entry bleed (severe) | verified start |
| 44 | US-FED | USC_T42_C129_S12604 (13141) | holder | GENUINE | next-entry bleed (severe) | verified start |
| 45 | US-FED | USC_T12_C14_S1790d (13175) | Secretary | GENUINE | clean | |
| 46 | US-FED | USC_T26_C1_S884 (14316) | ".. Subsec. (f)(2). Pub. L. 104–188..." | FALSE POSITIVE | garbage term key | Pub. L. amendment caption; 5,766-char runaway |
| 47 | US-FED | USC_T38_C17_S1741 (15112) | State home | GENUINE | clean | |
| 48 | US-FED | USC_T10_C322_S4211 (16221) | significant change to the schedule | GENUINE | next-entry bleed (severe/annotation) | verified start; rest is statutory-notes bleed |
| 49 | US-FED | USC_T33_C29_S1504 (18255) | "Subsec. (c)(2). Pub. L. 118–31..." | FALSE POSITIVE | garbage term key | Pub. L. amendment caption |
| 50 | US-FED | USC_T18_C113B_S2332a (18545) | property | GENUINE | next-entry bleed (severe/annotation) | verified start |
| 51 | US-FED | USC_T42_C161_S18649 (19700) | Meeting Isotope Needs and Capturing Opportunities for the Future | FALSE POSITIVE | other (mis-paired quote) | quoted phrase is a cited REPORT TITLE, not a definiendum |
| 52 | US-FED | USC_T15_C116_S9057 (20880) | applicable property | GENUINE | next-entry bleed (short) | pattern-consistent |
| 53 | US-FED | USC_T47_C5_S554 (21333) | cable operator | GENUINE | next-entry bleed (severe) | verified start |
| 54 | US-FED | USC_T26_C6_S1503 (22123) | unrecaptured amount | GENUINE | clean/minor | pattern-consistent |
| 55 | US-FED | USC_T10_C53_S1044d (26294) | State | GENUINE | next-entry bleed (severe/annotation) | verified |
| 56 | US-FED | USC_T42_C152_S17113b (28577) | greenhouse gas | GENUINE | next-entry bleed (short) | |
| 57 | US-FED | USC_T16_C12_S823a (31217) | qualifying criteria | GENUINE | next-entry bleed (severe/annotation) | verified start |
| 58 | US-FED | USC_T10_C19_S392 (33592) | designated cyber and information technology range | GENUINE | next-entry bleed (short) | pattern-consistent |
| 59 | US-FED | USC_T42_C157_S18122 (43262) | State | GENUINE | next-entry bleed (moderate) | verified; bleeds into a separate "No preemption" subsection |
| 60 | US-ME | STATE_ME_T5_P12_C337_S4594-G (2617) | New construction | GENUINE | next-entry bleed (minor) | |
| 61 | US-ME | STATE_ME_T17_C80_S2267-A (22948) | watercraft, | GENUINE | next-entry bleed (severe/unbounded) | verified; trailing comma in term is a real source quirk |
| 62 | US-MI | STATE_MI_C487_AAct-354-of-1996_S487.3406 (308) | Secretary | GENUINE | next-entry bleed (severe) | verified |
| 63 | US-ND | STATE_ND_T26.1_C26.1-36_S26.1-36-41 (444) | practitioner | GENUINE | next-entry bleed (short) | verified; truncated mid-clause at "a" |
| 64 | US-ND | STATE_ND_T26.1_C26.1-29_S26.1-29-09.1 (19106) | Insurable interest | GENUINE | list-introducer stub | verified; trails into "As used in this subdivision: (1)" |
| 65 | US-NJ | STATE_NJ_T52_C18A_S18A-243 (2154) | other factors | GENUINE | next-entry bleed (severe) | verified start |
| 66 | US-NJ | STATE_NJ_T39_C4_S4-97.3 (13965) | Two-way radio | GENUINE | clean | |
| 67 | US-NM | STATE_NM_STATUTES_C7_A5_S7-5-1 (733) | tax , | GENUINE | next-entry bleed (extreme/unbounded) | verified; real term is `' tax ,'` (Multistate Tax Compact); runs into 3 unrelated whole Articles |
| 68 | US-NV | STATE_NV_T21_C268_S268.418 (7455) | Person | GENUINE | next-entry bleed (short) | pattern-consistent |
| 69 | US-NV | STATE_NV_T55_C669A_S669A.070 (20297) | Family member | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 70 | US-NV | STATE_NV_T25_C319_S319.600 (42307) | Supportive services | GENUINE | clean | |
| 71 | US-NY | STATE_NY_ABNK_A6_S235 (978) | bond | GENUINE | next-entry bleed (short) | verified; genuine subdivision-scoped def, recurs in a long investment-powers list |
| 72 | US-NY | STATE_NY_ASOS_A6_T1_S390 (2355) | Enrolled legally exempt provider | GENUINE | next-entry bleed (EXTREME/unbounded) | verified start; largest in sample (41,107 chars) — swallows ~14 unrelated subsections |
| 73 | US-NY | STATE_NY_ACVR_A7_S76-A (6050) | Claim | GENUINE | next-entry bleed (short) | pattern-consistent |
| 74 | US-NY | STATE_NY_AEXC_A19-G_T1_S501-E (6575) | adjudicated status offender | GENUINE | next-entry bleed (short) | pattern-consistent |
| 75 | US-NY | STATE_NY_AGBS_A40_S913 (6930) | actual and reasonable costs | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 76 | US-NY | STATE_NY_ACPL_P3_TP_A500_S500.10 (9457) | Qualifies for electronic monitoring, | GENUINE | next-entry bleed (short) | verified; trailing comma in term is a real source quirk |
| 77 | US-NY | STATE_NY_AWKC_A2_S13-B (10553) | Chair | GENUINE | next-entry bleed (short) | verified |
| 78 | US-NY | STATE_NY_AVAT_T3_A12_S394 (14783) | Place of business | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 79 | US-NY | STATE_NY_AMHY_TE_A81_S81.44 (22134) | Statement of assets and notice of claim | GENUINE | next-entry bleed (moderate) | verified start |
| 80 | US-NY | STATE_NY_AENV_A11_T1_S11-0110 (28974) | process of taking | GENUINE | next-entry bleed (short) | pattern-consistent |
| 81 | US-OH | STATE_OH_T49_C4905_S4905.331 (5894) | Proceeding | GENUINE | next-entry bleed + OH scrape-metadata bleed | verified; trailing "Last updated July 9, 2025 at 12:24 PM" |
| 82 | US-OH | STATE_OH_T55_C5505_S5505.044 (6433) | Personal expenses | GENUINE | next-entry bleed + OH scrape-metadata bleed | same "Last updated...PM" tail |
| 83 | US-OH | STATE_OH_T51_C5119_S5119.20 (14836) | Law enforcement officer | GENUINE | next-entry bleed + OH scrape-metadata bleed | same "Last updated...PM" tail |
| 84 | US-OH | STATE_OH_T58_C5801_S5801.12 (28762) | Trust | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 85 | US-OH | STATE_OH_T1_C124_S124.15 (30807) | payment or benefit already provided by law | GENUINE | next-entry bleed (severe) | pattern-consistent (matches a 130-loss-population OH term shape) |
| 86 | US-OH | STATE_OH_T7_C715_S715.263 (31327) | Delinquent lot or parcel | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 87 | US-OH | STATE_OH_T55_C5505_S5505.16 (32216) | Uniformed services | GENUINE | next-entry bleed + OH scrape-metadata bleed | same "Last updated...PM" tail |
| 88 | US-OK | STATE_OK_T36_S36-4008 (951) | policy loan | GENUINE | next-entry bleed (short) | pattern-consistent |
| 89 | US-OK | STATE_OK_T74_S74-212 (1545) | special or investigative audit | GENUINE | next-entry bleed (severe) | verified |
| 90 | US-SC | STATE_SC_T24_C11_S24-11-20 (7184) | Institution | GENUINE | next-entry bleed (extreme/unbounded) | verified; Interstate Corrections Compact, same shape as #67 |
| 91 | US-TX | STATE_TX_Ctx_C23_S23.128 (23632) | Retail Manufactured Housing Inventory Tax Statement. | AMBIGUOUS | other (form-title / contents-list) | term is a tax FORM's title; text lists the form's required contents, not a "term means X" definition |
| 92 | US-UT | STATE_UT_T34A_S34A_2_103 (1113) | Regularly | GENUINE | next-entry bleed (moderate) | pattern-consistent |
| 93 | US-UT | STATE_UT_T58_S58_37_108 (24984) | isomer | GENUINE | next-entry bleed (severe, mostly own content) | verified start; chemical-isomer list is genuinely part of the term's own DEA-schedule def |
| 94 | US-VA | STATE_VA_T30_C34.1_S30-231.2 (2664) | Eligible student | GENUINE | clean | pattern-consistent |
| 95 | US-VA | STATE_VA_T54.1_SIII_C35_A1_S54.1-3500.1 (2860) | Jurisprudence Requirement | GENUINE | clean | |
| 96 | US-VA | STATE_VA_T22.1_C14_A3_S22.1-280.2 (15903) | Crime Stoppers | FALSE POSITIVE | other (mis-paired quote) | quoted program name; idiom matched belongs to an unrelated later sentence about a school board |
| 97 | US-WA | STATE_WA_T35A_C21_S444 (1581) | Warning: Electric Fence. | FALSE POSITIVE | other (mis-paired quote) | quoted warning-SIGN TEXT; idiom matched belongs to a distant, unrelated def of "Electric security alarm system" |
| 98 | US-WA | STATE_WA_T72_C09_S225 (21834) | Contractor | GENUINE | next-entry bleed (short) | verified |
| 99 | US-WA | STATE_WA_T35_C71_S010 (21849) | peddler | GENUINE | list-introducer stub | verified; correct/complete core def, trails into "As used in this chapter, the following terms shall have the meaning..." |
| 100 | US-WA | STATE_WA_T11_C98_S170 (45432) | Trustee | GENUINE | next-entry bleed (moderate) | pattern-consistent |

### Verbatim examples per class

**GENUINE, clean** (#8): term `International Mobile Subscriber
Identity-catcher` → `"a device used for intercepting mobile phone
identifying information and location data."` — complete, correctly
bounded, no trailing artifact.

**GENUINE, next-entry bleed** (#71, NY `bond`): source —
`As used in this subdivision, the term "bond" includes a note or
debenture.` → captured: `"a note or debenture.\n  15. Bonds, debentures,
consolidated debentures or other obligations of any federal home loan
bank or..."` — the real definition is correct and complete; the trailing
`15. Bonds, ...` is the next list item's own lead-in.

**GENUINE, list-introducer stub** (#99, WA `peddler`): the real,
complete, correct definition (`"...carrying for sale...except vendors of
books, periodicals, or newspapers: PROVIDED, That nothing in this chapter
shall apply to peddlers..."`) is followed immediately by a NEW
paragraph's own list-introducer sentence — `"As used in this chapter, the
following terms shall have the meaning herein given to each of them:"`
— captured as trailing content because the next recognized quote
("City") starts only after that sentence.

**FALSE POSITIVE, garbage term key** (#19): term = `.` + `"Subsec.
(i)(9). Pub. L. 110–458, §102(b)(2)(G)(ii), added par. (9) and struck out
former par. (9). Prior to amendment, text read as follows:"` — an
Editorial-Notes amendment caption, not a definiendum; definition_text
runs 16,352 chars into unrelated amendment history.

**FALSE POSITIVE, other (mis-paired quote)** (#97, WA `Warning: Electric
Fence.`): source quotes this phrase only as sign text (`"...marked with
conspicuous warning signs that... read 'Warning: Electric Fence.'"`); no
defining idiom follows it. The captured definition_text is actually
`"Electric security alarm system"`'s real definition, several sentences
later, mis-paired because the scanner's next recognized idiom match
happened to follow this unrelated quote within the 200-char gap.

## Failure-mode tally (100 items, one primary tag each)

| Failure mode | Count |
|---|---|
| next-entry bleed (all severities, incl. unbounded-runaway variant) | 76 |
| clean (no observable defect) | 11 |
| garbage term key | 5 |
| other (mis-paired quote / form-title ambiguity) | 5 (4 FALSE POSITIVE + 1 AMBIGUOUS) |
| list-introducer stub | 3 |

**Severity within "next-entry bleed"** (76 items, excluding the 4 OH
scrape-metadata items counted separately below): short/minor 36, moderate
14, severe 16, unbounded/extreme runaway 6. Plus 4 items (#81–83, #87, all
OH) carry a DISTINCT, newly-identified defect on top of ordinary bleed:
**OH website-scrape metadata bleed** — a trailing `"Last updated <date> at
<time>"` scrape stamp. OH's own `EntrySplitterRule`
(`us_markers_oh_trailing_clause.py`) strips this via
`_LAST_UPDATED_TAIL_RE`, but that cleanup lives in a function
`_extract_inline_quoted_definitions` never goes through — design (b)'s
fallback bypasses OH's existing cleanup entirely. Structurally fixable
(the regex already exists, just not wired to this path) but out of this
task's read-only scope to fix.

**The "other" bucket is the one that matters for gate-2/QA**: it is a
genuinely different mechanism from both garbage-term-key and ordinary
bleed — a real, well-formed quoted phrase (a program name, a cited report
title, sign-warning text, or a cross-reference parenthetical) that is
**not itself being defined at that point in the text**, wrongly paired
with a defining idiom that belongs to unrelated, distant prose. Four
independent instances found (#23 `apprenticeship`, #51 `Meeting Isotope
Needs...`, #96 `Crime Stoppers`, #97 `Warning: Electric Fence.`), each in
a different jurisdiction, each with a different quote shape (a
cross-reference parenthetical, a cited historical-report title, a program
name, sign text) — this is not a one-off, it is a recurring shape of the
same root defect (`_extract_inline_quoted_definitions`'s 200-char
idiom-gap window has no positional/ownership check tying a quote to "its
own" idiom rather than the nearest one that happens to follow).

## Filter leverage (Task 3)

**Garbage term key (5 FPs: #11, #19, #26, #46, #49) — fully excludable, ~zero
recall cost.** All 5 terms contain the literal substrings `Pub. L.` and/or
match `/Subsec\.\s*\(/` — a pure term-key-SHAPE rule (no jurisdiction/row
keying, M-R107-compliant): **reject a fallback candidate whose term
contains `"Pub. L."` or matches `Subsec\.\s*\(`.** Checked against the
full 100-item sample: 5/5 garbage-term-key FPs caught, **0/95** other
items (GENUINE + AMBIGUOUS) collaterally rejected — no genuine term in
this sample contains either substring. This is a strict superset
refinement of design (b)'s own existing `^\d{4}[—–-]` filter (which
happens to catch a *different* 4 phantom rows from investigation.md's
Q1 population, not these 5 — the two filters are complementary, not
overlapping, on the evidence seen so far).

**Mis-paired quote (4 FPs: #23, #51, #96, #97) — NOT reliably excludable
by any term-key or payload-shape rule, at the bounds available.** The
defining counter-evidence is direct, matched-pair comparison within this
same sample:

- #96 `Crime Stoppers` (FALSE POSITIVE, 2-word Title-Case proper noun) vs.
  #27 `Pilot Program` (GENUINE, 2-word Title-Case proper noun, verified) —
  identical shape, opposite ground truth.
- #51 `Meeting Isotope Needs and Capturing Opportunities for the Future`
  (FALSE POSITIVE, long multi-word Title-Case phrase) vs. #20 `Flight
  Standards Evaluation Program` (GENUINE, multi-word Title-Case phrase) and
  #8 `International Mobile Subscriber Identity-catcher` (GENUINE) — a
  "long Title-Case phrase" length/word-count heuristic would need to reject
  #51 while keeping #20/#8, which no term-key-shape rule can do (all three
  are syntactically the same kind of proper-noun phrase).
- #23 `apprenticeship` (FALSE POSITIVE, ordinary lowercase common word) is
  shape-identical to #40 `anyone`, #39 `agency`, #28 `consumption`, #41
  `community` (all GENUINE, verified or pattern-consistent) — nothing
  about the term string itself distinguishes the mis-paired case.

  What actually distinguishes a mis-paired quote from a genuine one is
  **position**: whether the idiom that matched is the quote's OWN
  immediately-following idiom, or a different idiom that happens to fall
  within `_MEANS_IDIOM_GAP_RE`'s 200-char lookahead because of intervening,
  unrelated prose. That is exactly the "(c) structurally cleaner variant
  (positional overlap-avoidance)" the Planner's own Item 2 design section
  already considered and rejected as unbuildable within the amended gate
  7's bounds (requires span-tracking inside `_extract_inline_quoted_
  definitions`'s own internals, explicitly forbidden). This sample
  independently reproduces that same conclusion from real data: no
  term-key/payload-shape filter closes this hole without either forbidden
  internals or unacceptable genuine collateral.

**Best achievable post-filter summary.** Applying the M-R107-compliant
`Pub. L./Subsec.(` structural rule: **FP count 9 → 4 (FP rate 9.0% →
4.0%)**, **recall cost 0%** on this sample (zero genuine items rejected).
The remaining 4/100 (all mis-paired-quote) are not closable by a
structural filter at the bounds this sprint operates under; closing them
would require either the forbidden internals change or a heuristic that
demonstrably cuts genuine items of the identical shape.

## Restore-only variant sizing (Task 4)

**Confirmed on data: recovers the 130 with zero expansion wave, by
construction.** "Restore-only" admits fallback terms per-term only on rows
where ALL primary-engine entries come from the newly-added idioms. That
condition is structurally identical to "this row's baseline (pre-Item-1)
primary candidates are empty" — verified directly above (6/6 spot-checked
rows from the 100-row exclusion set show `baseline pre-fallback primary
candidates = 0`), and investigation.md's Q1 measured this as 100/100
across the full recovery population. Design (b)'s merge on that
population was already verified (log doc) to recover 130/130 genuine
losses with 0 false rejects; restore-only is the identical mechanism
restricted to exactly that 100-row set, so it inherits the same 130/130
result. And by the same equivalence, restore-only's eligibility test
structurally EXCLUDES every row this pass's expansion-wave census found —
all 45,183 "primary already non-empty, excluding the 130-loss recovery"
rows have, by definition, at least one primary candidate that predates
Item 1's widening, so "ALL primary entries from new idioms" is false there
and the merge never fires. This is not an estimate; it is the same
partition this pass's own script already computed (`EXCLUDE_ROWS` is
exactly the 100-row recovery population; the 8,708-term/4,419-row wave is
exactly its complement).

**Genuine definitions forfeited if restore-only ships instead of full
design (b)**: wave size × sampled genuine rate = 8,708 × 90% ≈ **7,837
genuine new term admissions forfeited** (at the row level: 4,419 × 90% ≈
**3,977 rows** that would gain no new genuine definition under
restore-only, though the wave still gains its 8,708 terms across only
4,419 rows in the alternative full design (b)). This is the direct
recall-cost number for the director's tradeoff: restore-only trades
essentially all of this recall (≈7,800+ real definitions, corpus-wide
this is ~16 jurisdictions' worth, not all 53 — see the scope caveat
above) for reducing the FP-bearing population to zero (since it never
touches non-recovery rows at all, restore-only cannot produce ANY of this
sample's 9 false positives or 1 ambiguous item — those all come from the
expansion-wave population restore-only never runs on).

## Implications (evidence only — no decision)

- **The expansion wave is real, smaller than the Planner's own estimate,
  and materially imperfect.** True footprint (16-jurisdiction census):
  8,708 new terms / 4,419 rows, ~9.8% of eligible rows — about 3.1× lower
  than the Planner's 200-row-sample extrapolation of ~30.5%/~13,100 rows.
  At 90% sampled genuine (9% FP, 1% ambiguous, Wilson 95% CI roughly
  [5%, 16–17%]), this is a meaningfully higher and more heterogeneous
  precision profile than Item 1's own widening (80/80 sampled genuine) or
  the 130-loss recovery population (100% genuine by construction,
  investigation.md).
- **Two independently-confirmed false-positive mechanisms, only one of
  which a structural filter can close.** Garbage-term-key (legislative-
  history captions swallowed as if they were quoted definienda) is fully
  addressable by a cheap, zero-collateral, M-R107-compliant term-key rule
  (`Pub. L.`/`Subsec.(` substring reject) that would cut the sample's FP
  rate from 9% to 4% at no measured recall cost. Mis-paired quote (a real
  quoted phrase — proper noun, report/program title, sign text, cross-
  reference parenthetical — wrongly paired with a distant, unrelated
  idiom) is a second, equally real mechanism this pass found 4 independent
  instances of across 4 different jurisdictions and 4 different quote
  shapes; matched-pair comparisons within this same 100-item sample show
  no term-key or payload-shape signal separates these from structurally
  identical genuine terms (Crime Stoppers vs. Pilot Program; Meeting
  Isotope Needs... vs. Flight Standards Evaluation Program; apprenticeship
  vs. anyone/agency/community). Closing it would require either
  positional/span tracking inside `_extract_inline_quoted_definitions`'s
  own internals (forbidden by the amended gate 7) or accepting collateral
  against genuine terms of the same shape — independently reproducing,
  from real sampled data, the Planner's own conclusion that design (c)
  (positional overlap-avoidance) is not buildable within this sprint's
  bounds.
- **A large majority of the imprecision is a length/severity problem, not
  an anchor problem.** 76/100 items carry some form of "next-entry bleed"
  (the fallback's documented no-trailing-stop-cutoff weakness), ranging
  from a one-word dangling fragment (36 short/minor) to a handful of
  extreme cases running thousands to tens of thousands of characters
  unbounded to end-of-text (6 items, up to 41,107 chars in one case) —
  but in every one of these 76, the TERM itself and the definition's own
  opening content are correct (D-MAP's anchor-correctness bar), so none
  are classified FALSE POSITIVE. Whether that severity distribution
  (a handful of 10K+-char captures glued to otherwise-correct anchors) is
  itself an acceptable cost, separate from the false-positive rate proper,
  is a question this sample surfaces but does not adjudicate.
  Additionally, 4 OH items carry a newly-identified, structurally-fixable
  (but out-of-scope-here) defect: design (b)'s fallback bypasses OH's own
  existing `"Last updated..."` scrape-stamp cleanup, since that cleanup
  lives in a different function than the one the fallback goes through.
- **Restore-only is a clean, verified, zero-expansion-wave alternative
  with a large, quantified recall cost.** It recovers the same 130 genuine
  losses design (b) does (identical mechanism, by construction restricted
  to the 100-row population where it structurally cannot do otherwise),
  and produces none of this pass's false positives or ambiguous item
  (since it never runs on non-recovery rows at all) — but at the cost of
  forfeiting essentially all of the expansion wave: ≈7,837 of the 8,708
  new term admissions this pass measured (≈4,419 rows lose ≥1 potential
  genuine addition), scoped to the same 16 jurisdictions this task
  measured (the true corpus-wide forfeiture, across all 53 files, is
  unmeasured by this pass and could be larger).

---

Reproduce: `PYTHONPATH=.:backend /Users/nerya/LexGraph/backend/.venv/bin/python
measure_design_b_expansion_wave.py` then `sample_design_b_expansion_wave.py`
(both in this directory; raw outputs land in `run/design_b/`, gitignored).
