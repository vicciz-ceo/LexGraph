"""Gate U4's "proven correctly-empty" classifier (sprint
2026-08-04-defs-us-markers, planner pass 2, priority 1, ruling U-R3).

Gate U4 is the director's absolute zero-miss bar: every Definitions-headed
section that extracted ZERO candidates must be EITHER captured or PROVEN
correctly-empty -- never silently written off. This module is the
"proven correctly-empty" half: an independent, callable classifier (not a
Developer's unverified prose claim) that QA and the pipeline can both
invoke against the same rule.

`classify_correctly_empty` is a PURE function of `body_text` alone. Its
caller is responsible for having already confirmed (a) the section's own
heading is a recognized Definitions heading (`sections.is_definitions_heading`
/ profile equivalent) and (b) extraction on this body already returned zero
candidates -- this function does not re-check either precondition, and its
result is meaningless if called outside that context.

Classification is applied in priority order (first match wins):

  1. TERMINAL_STATUS -- the entire (whitespace-stripped) body is exactly
     one terminal-status word/phrase (`Repealed.` / `Expired.` /
     `Reserved.` / `Renumbered.` / `Omitted.` / `Vacant.` /
     `Recodified as ...`), optionally bracket-wrapped, with an optional
     trailing period. The law itself says this section carries no
     operative text at all -- not a miss.

  2. CROSS_REFERENCE -- the entire (whitespace-stripped) body, after
     removing an optional trailing `History: ...` amendment-citation
     annotation, is NOTHING BUT a single short sentence stating that the
     definitions governing this text live in another citation.

  3. otherwise -- NOT correctly empty: `is_correctly_empty=False`,
     `reason=None`. A real miss.

The "entire body" requirement in rule 2 is load-bearing, not decorative:
an earlier design matched the cross-reference sentence anchored only at
the START of the body, and measured against the full real corpus that
naive rule misclassified self-referential preambles like "The definitions
set forth in this section apply throughout this chapter." (immediately
followed by real defined terms) as correctly-empty -- silently erasing
real law. The regex below therefore requires the ENTIRE remaining body to
be consumed by the cross-reference sentence (`re.fullmatch`, citation and
trailing clause both barred from crossing a line break or a `.`), so any
operative content following the citation sentence -- on the same line
(more sentences before the next period) or a later line -- breaks the
match and the section correctly falls through to "not correctly empty".
When in doubt, this module is biased toward MISS, never toward
correctly-empty: a false "miss" costs a look; a false "correctly empty"
silently drops real law from the corpus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

CorrectlyEmptyReason = Literal["terminal_status", "cross_reference"]


@dataclass(frozen=True)
class CorrectlyEmptyResult:
    """`classify_correctly_empty`'s output shape.

    `.reason` is `None` iff `.is_correctly_empty` is `False`.
    """

    is_correctly_empty: bool
    reason: CorrectlyEmptyReason | None


# Bare terminal-status words -- the ENTIRE stripped (and unwrapped) body
# must equal one of these, case-insensitively. `"Recodified as ..."` is
# open-ended (names the new citation) so it gets its own regex below
# rather than a fixed-word membership check.
_TERMINAL_STATUS_WORDS = frozenset(
    {"repealed", "expired", "reserved", "renumbered", "omitted", "vacant"}
)

# `"Recodified as <new citation>"` -- open-ended tail, so matched as a
# prefix regex rather than a fixed word.
_RECODIFIED_RE = re.compile(r"^recodified\s+as\s+\S.*\Z", re.IGNORECASE)

# A single optional trailing period, possibly preceded by whitespace
# (real DC rows carry a stray space before the final period, e.g.
# `"Recodified as § 2-381.01 ."`). Anchored with `\Z` (not `$`) so it
# only strips a period that is truly the body's last character.
_TRAILING_PERIOD_RE = re.compile(r"\s*\.\s*\Z")

# A trailing `History: ...` amendment-citation annotation (real WI rows) --
# further non-operative tail text that must be peeled off before checking
# whether the remainder is nothing but a cross-reference sentence.
_HISTORY_TAIL_RE = re.compile(r"\n\s*History:.*\Z", re.IGNORECASE | re.DOTALL)

# The genuine cross-reference sentence: "(the )?definition(s) (contained
# |set forth )?in <citation> (apply|shall apply|govern|are applicable)",
# followed by at most a short same-line trailing clause and one optional
# closing period -- then nothing else. `<citation>` is barred from
# crossing a line break (`[^\n]`); combined with `re.fullmatch` against
# the whole (History-stripped) body, this is what rejects a
# self-referential preamble followed by real definitions on a later line
# -- that content has nowhere to go and the match fails.
#
# BOUNCE CYCLE (ruling U-R7): a full-corpus adversarial sweep found 4 real
# WA rows the newline/period restrictions above let through -- all open
# with the textbook self-referential preamble "The definitions in this
# section apply throughout this chapter[,.:] ..." and then carry 2-12
# real `"Term" means ...` definitions, but ALL of it sits on ONE line (no
# `\n` anywhere), so `[^\n]` alone does not stop the match. Two distinct
# shapes, both real:
#
#   (a) `STATE_WA_T82_C23A_S010` / `STATE_WA_T18_C44_S011` /
#       `STATE_WA_T70A_C30_S010` -- the same line happens to contain a
#       SECOND, later "apply"/"applicable" occurrence (a genuine closing
#       cross-reference sentence, or an unrelated-content concatenation
#       artifact). The old citation group `[^\n]+?` is lazy but otherwise
#       unrestricted, so on backtracking it swallows the entire real
#       middle to reach that later trigger.
#   (b) `STATE_WA_T70_C28_S008` -- only ONE trigger occurrence; its real
#       entries are separated by `;`/`:`, not `.`, so the old trailing
#       clause's period-boundary heuristic never fires at all and it
#       swallows everything straight through to the body's own final
#       period.
#
# Bounding the citation/trailing spans to a line (shape a) is therefore
# NOT sufficient on its own for shape (b) -- a single-line body with only
# one trigger still needs a boundary inside that line. The fix used here
# instead relies on a stronger, corpus-wide invariant: a genuine citation
# or scope clause never contains a literal `"`, while every real
# definition entry in this corpus opens with a quoted term
# (`"Term" means ...`). Barring `"` from BOTH the citation span and the
# trailing clause means neither span can cross into or through real
# defining content to reach a later trigger (shape a) or swallow a
# semicolon/colon-separated real entry (shape b) -- regardless of
# newlines or periods. This is IN ADDITION TO, not instead of, the
# existing period-boundary refinement below (still needed for the
# genuine WI row's own abbreviation periods, which carry no quotes).
#
# The trailing clause needs one further refinement beyond the `"` bar:
# real citation scope clauses carry their own abbreviation periods (e.g.
# real WI row "...apply to chs. 851 to 882 ."), so a blanket "no periods"
# rule would wrongly reject that genuine row. A period is treated as a
# non-terminal abbreviation/citation continuation only when followed by a
# digit or a LOWERCASE letter (`chs. 851`, `ss. 851.01`); a period
# followed by an uppercase letter, a quote, an open paren, or the end of
# the body reads as a real sentence boundary and is left for the single
# closing `\.?` -- which is exactly what stops "...apply throughout this
# chapter. (1) "Right-of-way" means..." (paren after the period) and
# "...that law. As used in this article..." (capital letter after the
# period) from being swallowed. `(?-i: ...)` locally turns off this
# pattern's own case-insensitivity so "uppercase" here really means
# uppercase, not "any letter" under `re.IGNORECASE`.
_CROSS_REFERENCE_RE = re.compile(
    r"(?:the\s+)?definitions?\s+(?:contained\s+|set\s+forth\s+)?in\s+"
    r'[^"\n]+?\s+(?:apply|shall\s+apply|govern|are\s+applicable)\b'
    r'(?:[^".\n]|\.(?=\s*(?-i:[0-9a-z])))*\.?\s*\Z',
    re.IGNORECASE,
)


def _unwrap_terminal_candidate(stripped_body: str) -> str:
    """Peel one trailing period and one layer of `[...]` bracket-wrapping
    off `stripped_body`, in either order, for the terminal-status check.
    """
    candidate = _TRAILING_PERIOD_RE.sub("", stripped_body)
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = _TRAILING_PERIOD_RE.sub("", candidate[1:-1].strip())
    return candidate


def _is_terminal_status(stripped_body: str) -> bool:
    candidate = _unwrap_terminal_candidate(stripped_body)
    if candidate.casefold() in _TERMINAL_STATUS_WORDS:
        return True
    return bool(_RECODIFIED_RE.match(candidate))


def classify_correctly_empty(body_text: str) -> CorrectlyEmptyResult:
    """Classify a zero-candidate Definitions section's body.

    See the module docstring for the precondition this function assumes
    (caller has already confirmed a Definitions heading and zero extracted
    candidates) and the priority-ordered rules applied here.
    """
    stripped = body_text.strip()

    if _is_terminal_status(stripped):
        return CorrectlyEmptyResult(is_correctly_empty=True, reason="terminal_status")

    without_history = _HISTORY_TAIL_RE.sub("", stripped).strip()
    if _CROSS_REFERENCE_RE.fullmatch(without_history):
        return CorrectlyEmptyResult(is_correctly_empty=True, reason="cross_reference")

    return CorrectlyEmptyResult(is_correctly_empty=False, reason=None)
