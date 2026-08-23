"""Sprint 2026-08-23-defs-debt-31, Item 4 (issue #31 debt class 4 -- "FX7
unrecovered remainder", ~100 of the 118 live-verified ceiling-tripped
losses the prior sprint's idiom widening did not reach). Gate 4: "Each of
the ~100 remainder rows is either recovered with correctly-bounded text or
individually adjudicated unrecoverable with a stated reason. ... silent
skips fail." Per-row recovery-or-adjudication is a Dev/QA-time PROCESS
deliverable (a ledger, cross-checked against the certification item's
actual delta per P-R11), not a single boolean this file can assert --
recovery and adjudicated-unrecoverable are EQUALLY legitimate per-row
outcomes, so (same reasoning as Item 3) this file asserts no required
extraction-code behavior and contains no RED test.

**Finding worth recording (see Item 1's own file for the full account)**:
the two real, exact rows the prior sprint's own evidence named as
FX7-remainder exemplars -- `USC_T5_C75_S7511` "furlough" (no-next-quoted-
term family) and the general citation-noise family -- were re-verified
live against this worktree's HEAD before this file was written.
`"furlough"` is NO LONGER a total ceiling-drop: the already-landed idiom
widening incidentally gave it a downstream boundary via a different,
newly-recognized entry, so it is now captured (bleeding, not absent) --
it has migrated INTO Item 1's own population and is used there instead.
No fresh corpus-wide re-census of "which ~100 rows are still genuinely
0%-recognized today" was run at planning altitude (P-R11: that census is
Dev/QA's job, run against the actual code, not a Planner-predicted
ledger) -- so the two structural controls below are M-R107 synthetic,
modeled precisely on the evidence's own documented mechanism for each
family, rather than re-deriving a fresh real exemplar."""
from __future__ import annotations

import re

# --- Family A: no-next-quoted-term (~60/118 per the prior sprint's own ----
# adjudication) -- modeled exactly on furlough's ORIGINAL documented shape:
# true boundary is a bare LETTER marker, with NO quote character anywhere
# in the remaining text for `_QUOTE_WITHIN_LOOKAHEAD_RE`-style recognition
# to ever find.

TEXT_NO_NEXT_QUOTED_TERM = (
    '"Wrenholt status" means the placement of an employee in a temporary '
    "capacity without regular duties or compensation because of a lapse "
    "in appropriated funding or other nondisciplinary cause.\n\n"
    "(b) This subchapter does not apply to an employee whose appointment "
    "is made by and with the advice and consent of a confirming body, or "
    "who holds a position excepted from the competitive service by "
    "statute or regulation, or who serves at the pleasure of an "
    "appointing authority without a fixed term of office."
)


def test_no_next_quoted_term_family_is_reproducible():
    """Structural fact about the fixture text itself (no production code
    called -- safe under any Dev/QA outcome, recovered or adjudicated):
    after the term's own definition ends, the remaining text contains
    ZERO quote characters -- the exact shape the evidence names ("no
    distinguishable next-quoted-term at all"), distinct from ordinary
    next-entry bleed (Item 1), where a later quote eventually IS found."""
    definition_end = TEXT_NO_NEXT_QUOTED_TERM.index("nondisciplinary cause.") + len(
        "nondisciplinary cause."
    )
    remainder = TEXT_NO_NEXT_QUOTED_TERM[definition_end:]
    assert not re.search(r'["“”]', remainder), (
        f"this family's defining shape is the ABSENCE of any quote in the "
        f"remaining text -- got a quote character in {remainder!r}"
    )
    assert re.search(r"\(b\)\s+[A-Z]", remainder), (
        "the remaining text must open on a bare letter-marker clause "
        "(furlough's own real shape), not some other structure"
    )


# --- Family B: citation-noise (~40/118) -- a quoted Act-name-like phrase --
# immediately followed by a P.L./Pub.L.-style citation, never a defining
# idiom (real evidence: `"Administrative Procedure Act," P.L.1968,
# c.410 (C.52:14B-1...)`).

TEXT_CITATION_NOISE = (
    "The board shall administer this chapter in a manner consistent with "
    'the "Uniform Records Retention Act," P.L.1974, c.212 '
    "(C.11:4B-3 et seq.), as amended from time to time."
)


def test_citation_noise_family_is_reproducible():
    """Structural fact about the fixture text: the quoted phrase is
    immediately followed by a `P.L.`-citation pattern, with NO defining
    idiom word anywhere between the quote and that citation -- the exact
    shape the evidence names ("citation noise... not a defining idiom"),
    distinct from the mis-paired-quote class (Item 3), where a REAL idiom
    (just the wrong one) does eventually follow."""
    quote_end = TEXT_CITATION_NOISE.index('Uniform Records Retention Act,"') + len(
        'Uniform Records Retention Act,"'
    )
    gap_to_citation = TEXT_CITATION_NOISE[quote_end : quote_end + 20]
    assert re.match(r"\s*P\.L\.\d{4}", gap_to_citation), (
        f"the quote must be immediately followed by a P.L.-citation shape "
        f"-- got {gap_to_citation!r}"
    )
    idiom_between = re.search(
        r"\b(?:means|shall mean|has the meaning|shall include|includes)\b",
        TEXT_CITATION_NOISE[quote_end : quote_end + 20],
        re.IGNORECASE,
    )
    assert idiom_between is None, (
        "this family's defining shape is that NO idiom word sits between "
        f"the quote and the citation -- got {idiom_between!r}"
    )
