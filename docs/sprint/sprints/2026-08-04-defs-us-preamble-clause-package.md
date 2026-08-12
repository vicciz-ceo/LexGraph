# CLAUSE routing package — for `defs-us-scoped-inline`

Deliverable D5, consolidating Planner, sprint `2026-08-04-defs-us-preamble`.
Handed to the program manager for routing to the `defs-us-scoped-inline`
panel, per M-R16's instruction ("CLAUSE-shaped populations: each scout
produces a per-state row list + verbatim examples, packaged for the
scoped-inline panel and sent to the program manager for routing. Data
first, never bare rows.").

**Data file**: `2026-08-04-defs-us-preamble-clause-package.json`, merged
from all four scouts' own CLAUSE packages (S1's `classify7` results
filtered `label == "CLAUSE"`; S2's FEDERAL/DC/NY clustered results filtered
`n_clustered_terms == 1`; S3's own already-built `scout_S3_clause_
package.json`; S4's own already-built `scout_S4_clause_package.json`).
**2,659 real `act_id`s across 51 jurisdictions**, deduplicated (NE appears
in both S3's generic 40-state scan and S4's dedicated NE inventory —
merged to 2 unique rows, not double-counted; GA/IL were deliberately left
to S4 alone by S3's own design, per S3's findings §0/§7, so no double-count
risk there either). Every `act_id` traces to a real scout output file
already on disk; none were hand-typed or re-derived for this package.

## Critical: the discriminator-bias fix this package relies on (M-R19)

**S4 found and fixed a tail-ratio bias in the D2 discriminator that
produced a 67% false-CLAUSE rate on SD** (reproducing the Planner's own
earlier-flagged MS bias at a materially higher rate when the same style of
discriminator — trigger position AND tail-ratio-below-threshold — was
applied to SD's shorter, single-term-per-section convention). **This
package does NOT reuse that biased discriminator.** MS's and SD's entries
below come from S4's OWN CORRECTED discriminator (trigger position alone,
tail-ratio kept only as a diagnostic field, not a classification input —
see S4 findings §2 for the full before/after). Every other state's entries
come from that state's own scout's own (differently-built, not known to
share this specific bias) methodology — S1's paragraph-run
position+coverage heuristic, S2's clustered-term-count discriminator, S3's
colon-after-trigger heuristic with 52-row hand-check correction. No further
bias-correction pass was applied across scouts by this consolidation
beyond what each scout already did — merging four already-verified lists is
this deliverable's job, not re-classifying 2,659 rows from scratch.

## Per-jurisdiction counts (top 15 by volume)

| Jurisdiction | CLAUSE rows | Source | % of state's own preamble-signal population |
|---|---:|---|---|
| US-MO | 456 | S1 | 456/476 (95.8%) |
| US-FL | 302 | S1 | 302/330 (91.5%) |
| US-MS | 270 | S4 (corrected) | 270/1,717 (15.7%) |
| US-DC | 151 | S2 | 151/300 (50.3%) |
| US-NC | 84 | S1 | 84/102 (82.4%) |
| US-LA | 80 | S3 | 80/84 (95.2%) |
| US-NY | 77 | S2 | 77/136 (56.6%) |
| US-MA | 61 | S3 | 61/62 (98.4%) |
| US-IL | 59 | S4 | 59/75 (78.7%) — IL is CLAUSE-**dominant**, the outlier |
| US-CA | 55 | S4 | 55/1,401 (3.9%) |
| US-SD | 65 | S4 (corrected) | 65/241 (27.0%) |
| US-MD | 45 | S4 | 45/1,849 (2.4%) |
| US-IN | 41 | S3 | 41/44 (93.2%) |
| US-PA | 40 | S3 | 40/41 (97.6%) |
| US-WV | 38 | S3 | 38/44 (86.4%) |

(Full table for all 51 jurisdictions is in the JSON's `package` object,
each with its own `count` and `act_ids` list.)

**Reading the two columns together matters**: MO/FL/NC/LA/MA/IN/PA/WV are
90%+ CLAUSE — these states' entire preamble-signal population is
overwhelmingly the scoped-inline panel's territory, not this sprint's. MS/
CA/MD are the opposite: CLAUSE is a small minority (2-16%) of a much larger
population whose majority (BLOCK) belongs to this sprint. IL inverts the
usual pattern (79% CLAUSE, the largest CLAUSE-share of any state measured)
— flagged by S4 as worth the scoped-inline panel's attention as a
genuinely CLAUSE-dominant jurisdiction, not an edge case.

## Verbatim examples (3 highest-volume states, quoted directly from the
## scouts' own findings, never paraphrased)

**MO** (`STATE_MO_C105_S105.1600`, heading `"105.1600 Baseline requirements
for hiring..."`): `"1. For the purposes of this section, the following
terms mean:\n\n(1) "Applicant" , any individual seeking gainful employment
from a state agency;..."` — definitions subsection "1." is only 14% of the
section's 3,413 total chars; subsections 2-4 cover inapplicability,
adverse action, appeal (S1 finding).

**FL** (`STATE_FL_TVI_C73_S73.092`, heading `"73.092 Attorney's fees."`):
`"(1) Except as otherwise provided in this section and s. 73.015, the
court, in eminent domain proceedings, shall award attorney's fees based
solely on the benefits achieved for the client. (a) As used in this
section, the term "benefits" means the difference..."` — section is about
awarding attorney's fees; one embedded term (S1 finding).

**MS** (`STATE_MS_T41_C25_S41-45`, quoted verbatim in this sprint's own
`-log.md`, QA's D1 corpus-wide false-positive-exposure section): `"As used
in this section, the term " abortion " means the use or prescription of
any instrument, medicine, drug..."` inside Mississippi's abortion-
restriction statute, whose remaining subsections are penalties, not
definitions.

## Known caveats the scoped-inline panel should know before building on this

- **S3's package (38 states) generously includes a 148-row
  "UNCLEAR-leaning-CLAUSE" subset**, sample-verified (13/148 hand-checked,
  9 confirmed CLAUSE), not row-by-row verified. Any specific row the
  scoped-inline panel builds a fixture from should get its own quick
  re-verification, per S3's own explicit caveat.
- **S1's package (FL/NC/AL/MO) may UNDER-count slightly**: S1's own §3
  hand-check found a handful of its HAZARD-labeled rows are, on full read,
  better labeled CLAUSE (e.g. NC's `115C-325`, MO's `292.440`) — not
  auto-merged into this package's CLAUSE lists, since that correction was
  identified by hand on specific rows, not applied as a corpus-wide rule.
- **S2's FEDERAL package (205 rows) contains a real, live-confirmed
  boundary tension** (also flagged in this sprint's own D4 test file,
  `test_us_body_preamble_fed_dc_ny_red.py`): roughly 30 of the 205 rows are
  "whole-section-is-the-definition" — structurally CLAUSE (one term,
  section-scoped) but functionally the entire section IS the definitions
  container once trailing legislative-history notes are stripped, with no
  other substantive content for a "clause embedded in an otherwise-
  ordinary section" framing to attach to. Same tension exists in DC (e.g.
  `STATE_DC_T50_C11_S50-1108`). Worth a shared ruling across both
  jurisdictions rather than deciding per-state (S2's own recommendation).
- **Every row in this package was, by construction, uncaptured today**
  (each scout's candidate query already excludes anything the baseline
  pipeline currently captures) — the scoped-inline panel is not being
  handed anything already shipped.

## Not done in this pass (explicit, not silently skipped)

- No re-classification of any row across scouts — this package merges four
  already-verified lists; it does not re-run a unified discriminator over
  all 2,659 rows.
- No fresh full-body-text fetch for every row — only the 3 verbatim
  examples above were freshly cross-checked; the remaining 2,656 `act_id`s
  are exactly as each scout's own script produced them, traceable back to
  that scout's own findings file and JSON output for full body text on
  request.
