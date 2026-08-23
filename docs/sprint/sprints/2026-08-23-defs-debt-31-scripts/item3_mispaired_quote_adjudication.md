# Item 3 (issue #31 debt class 3, mis-paired-quote FP class) — adjudication

**Outcome: NO-CODE. Legitimate PASS per gate 3** ("evidence before code...
a no-code outcome is a legitimate PASS", matching the FX7-ceiling file's
own precedent). This document is the required "adjudicated evidence + a
recommendation" deliverable.

## What was investigated

Gate 3 explicitly reopens the question the prior sprint (2026-08-20-defs-
boundary-idioms) closed as "forbidden internals": since this sprint's own
seam is wider (`_extract_inline_quoted_definitions`'s internals are
explicitly in scope, gate 8), is a zero-genuine-loss positional/span-
tracking fix for mis-paired quotes *now* provable? The evidence test
file (`test_us_markers_defs_debt_31_mispaired_quote_evidence.py`)
reproduces the prior sprint's own finding — no term-key/payload-shape
signal separates a genuine capture from a mis-paired one of identical
shape — but leaves the *positional* question open, since that seam is
new.

This pass went further than the evidence file: it re-derived the exact
`definition_start`-to-idiom gap TEXT (not just length) for all 4 named
real mis-paired exemplars from `expansion_precision.md`
(`apprenticeship`, `Meeting Isotope Needs and Capturing Opportunities
for the Future`, `Crime Stoppers`, `Warning: Electric Fence.`) plus
several matched genuine pairs (`consumption`, `agency`, `anyone`), live
against the real corpus
(`/Users/nerya/.cache/huggingface/hub/datasets--vaquill--open-us-law/
snapshots/301000fc3465374ee0f23c3c6953a8a861e95cad`), to test a
candidate signal: does a genuine idiom pairing ever have a marker token
(`(N)`/`(A)`) or a real sentence-terminating period between the quote's
own close and its idiom, and does a mis-paired one always have one.

## Finding 1: the positional signal IS real in the sampled mis-pairs

All 4 named real mis-paired exemplars' own gap text (quote-close to
idiom-start), live-verified:

- `apprenticeship` (`USC_T20_C28_S1091`): gap = `');\xa01\n\n(C)
  includes '` — the idiom belongs to clause `(C)` of a DIFFERENT
  enumerated list, crossing a `;`+marker boundary.
- `Meeting Isotope Needs and Capturing Opportunities for the Future`
  (`USC_T42_C161_S18649`): gap = `'; and\n\n(ii) periodically update
  that report thereafter as needed.\n\n(B) Inclusions\n\nAn updated
  report under subparagraph (A) shall include '` — crosses TWO markers
  AND a genuine sentence-terminating period (`"...as needed."`).
- `Crime Stoppers` (`STATE_VA_T22.1_C14_A3_S22.1-280.2`): gap =
  `' program.\n\nThe governing board of any separate nonprofit school
  crime line corporation shall include '` — crosses a genuine sentence-
  terminating period + paragraph break, NO marker at all (pure
  sentence-boundary crossing).
- `Warning: Electric Fence.` (`STATE_WA_T35A_C21_S444`): gap = `'; (iii)
  The electric security alarm is 10 feet in height, or two feet higher
  than the perimeter barrier, fence, or wall, whichever is greater; and
  (iv) The electric security alarm includes '` — crosses two roman-
  numeral markers.

Matched genuine pairs checked (`consumption`, `agency`, `anyone`, all
`USC_T*`) all had short, clean, marker-free, period-free gaps (e.g.
`' means '`, `', with respect to a regulated substance, means '`).

This is a real, non-trivial signal: every sampled mis-pair crosses
either a marker token or a genuine sentence-terminating period between
the quote and its matched idiom; every sampled genuine pair does not.

## Finding 2: a naive implementation of that signal is unsafe — confirmed on real data, not speculated

Before treating Finding 1 as sufficient to ship, this pass searched for
the specific counter-example a marker-crossing rule would need to
survive: a GENUINE definition whose own gap legitimately contains a
marker token. A short scan of the real `us_federal_statutes.parquet`
file (first 6 non-empty rows reached, `USC_T16_C38_S1801`,
`USC_T15_C93_S6701`) already produced 8 such cases, e.g.:

```
USC_T15_C93_S6701: "...(8) NAIC.—The term 'NAIC' means the National
Association of Insurance Commissioners... (9) Person.—The term
'person' means..."
```

FED's own extremely common `"(N) Label.—The term 'X' means Y."`
numbered-definition-list convention means a marker token sits between
one entry's own content and the literal next entry's own idiom
CONSTANTLY — this is not a rare edge case, it is one of the dominant
real drafting shapes in the federal corpus. A rule that rejects "marker
token anywhere in the gap" would reject a large, unmeasured fraction of
this entire convention — a scale of collateral loss the director's own
D-INCLUDES ruling already measured and rejected for a structurally
similar (if less naive) general proximity tightening ("32-56% of true
definitions lost for no measured precision gain").

Distinguishing "a marker token that starts a NEW, unrelated clause"
(the mis-paired shape) from "a marker token that is itself part of the
SAME entry's own numbered-list convention" (the FED NAIC/Person shape)
is exactly the problem `us_markers_boundary._digit_paren_run_internal_
content_starts` already solves for the PRIMARY engine, at real cost (a
~100-line, multiply-corpus-corrected function with its own long list of
named regressions it had to be hardened against, per that module's own
docstring). Reusing or re-deriving that same class of machinery inside
`_extract_inline_quoted_definitions` to make a marker-crossing rejection
safe is a materially larger undertaking than this item's own "evidence
before code, scoped populations only" bound supports — it would need
the same kind of iterative, multi-round corpus-wide hardening
`_digit_paren_run_internal_content_starts` itself needed, not a single
regex check.

The sentence-terminating-period signal (the `Crime Stoppers` case, no
marker) was not separately stress-tested against a real-corpus false-
positive search this pass, given the marker-crossing half of the
candidate signal was already disproven at this scoped-population depth
— per the brief's own instruction ("do not iterate full all-53 runs to
explore — scoped populations first"), this pass stops here rather than
building out a second candidate signal only to need the same full-
corpus validation the marker signal already failed to clear cheaply.

## Recommendation

**No code this sprint.** The positional signal exists and is a
legitimate lead for a *future* sprint, but a safe implementation
requires the same order of dedicated, multi-round corpus-hardening
`_digit_paren_run_internal_content_starts` needed for the primary
engine's own digit-paren-run discrimination — not achievable within
this item's "scoped populations, not full all-53 runs" exploration
bound, and gate 3's own bar ("proves zero genuine anchor losses across
every reached population") is not met by a signal already disproven
on an 8-row scoped sample.

If a future sprint wants to pursue this: scope the fix to require BOTH
(a) a marker-crossing/sentence-boundary-crossing signal AND (b) the
crossed marker failing the SAME "is this a genuine new top-level entry"
discrimination `_digit_paren_run_internal_content_starts` already
performs (reused, not reinvented) — then validate with a FULL all-53
run before shipping, since gate 3's bar cannot be met by sampling alone
once a real, non-trivial false-positive class has already been found.

## Evidence test (stays GREEN, unchanged, no code required)

`backend/tests/integration/test_us_markers_defs_debt_31_mispaired_quote_
evidence.py` — 3 tests, GREEN both before and after this adjudication;
none call any code this item's own investigation touched. Confirmed via
scoped run:

```
PYTHONPATH=.:backend .../python -m pytest \
  backend/tests/integration/test_us_markers_defs_debt_31_mispaired_quote_evidence.py -q
```
