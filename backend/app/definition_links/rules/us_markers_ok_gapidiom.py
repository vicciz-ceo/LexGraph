r"""Rule: OK's "gap-idiom" shape (sprint 2026-08-10-green-the-suite, item FX1)
-- a recurring cross-state family (NJ 15.4%, MI 13.7%, NY 8.8%, OK 8.4% of
each state's post-quote-engine residual) where a whole clause is interposed
between the quoted (or `the term "X"`) subject and its own defining verb:

    The term "person" as used in this act shall mean any individual,
    firm, partnership, corporation, or business entity of any kind or
    character, or the executor, administrator, trustee, receiver,
    assignee, or personal representative thereof.

(real row `STATE_OK_T47_S47-157.5`). `us_markers_boundary._TIGHT_IDIOM_RE`
deliberately requires the defining verb ESSENTIALLY IMMEDIATELY after the
quoted term's closing quote (by design -- see that module's own docstring:
this tightness is what rejects phantom matches like WA's nested `"motor
vehicle"`). The interposed "as used in this act" clause here is a 20+
character gap the tight gate correctly refuses to bridge unconditionally
-- bridging it corpus-wide would risk the exact false-positive class ruling
U-R1 exists to prevent (`us_markers_boundary.py`'s own SELL/`by any means`
example).

This is architecturally the SAME gap-idiom problem `us_markers_tn_idiom.py`
already solves for TN's "has the same meaning AS INTERPRETED BY" gap -- a
narrow, phrase-scoped rule that recognizes ONE specific, recurring
statutory idiom family (`"X" as used in this <act|chapter|section|title|
article> [,] <means|shall mean|has the meaning>`) rather than a further
loosening of the shared tight gate. Scoped to `US-OK` only (the state this
sprint's own corpus evidence confirms) -- not a blanket `"US-*"`, per this
package's own convention (see `us_markers_inline_quote.py`'s own
docstring) of scoping a new rule only to jurisdictions actually verified
against real vendored rows.

Registers an ADDITIONAL (union-kind) `EntrySplitterRule` for `US-OK` --
`us_markers_inline_quote.py`'s existing `US-OK` registration (calling the
shared engine's default `extract_quote_anchored_entries`) is untouched and
keeps producing whatever it already correctly produces; this module only
ADDS the gap-idiom shape's own entries, which the shared engine's tight
gate structurally cannot reach today.

Boundary-closing reuses `us_markers_boundary.py`'s own `compute_hard_stops`/
`close_entries` (the same marker hard-stop detection, `MAX_CLEAN_DEFINITION_
LENGTH` unbounded-only ceiling, and trailing-marker-chain strip the shared
engine's own default path uses) rather than a bespoke "stop at the next
gap-idiom match or end-of-text" scheme -- corpus self-verification (this
sprint's own required blast-radius measurement) caught two real defects in
an earlier, simpler draft of this rule that a bespoke scheme produced:
`STATE_OK_T21_S21-981`'s `"Consideration"` ran unbounded straight through
two entirely unrelated subsequent entries (`"gambling device"`, `"gambling
place"`) because no second gap-idiom match existed to close it and nothing
else was checked; `STATE_OK_T60_S60-175.3`'s `"Trustee's compensation,"`
swallowed the immediately-following `"Trustee's commission,"` entry (a
second real gap-idiom instance the earlier draft's regex missed entirely,
because the corpus's own `as used in this\n\nact` line break split what the
draft required to be a single literal space) AND the unrelated `"Trustee
advisor"` entry after it. Reusing the shared boundary-closing machinery
fixes both: `compute_hard_stops`'s digit-dot/letter-dot marker detection
correctly closes `"Consideration"` at the real `3.`-numbered next entry,
and the corrected `\s+` (not a literal space) between "this" and the
statutory referent lets `"Trustee's commission,"` register as its own
`starts` entry, which then closes `"Trustee's compensation,"` the same way
any two adjacent real entries close each other."""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule
from app.definition_links.rules.us_markers_boundary import (
    close_entries,
    compute_hard_stops,
    entries_to_quoted_blocks,
    trailing_stop_limit,
)

# `(?:the term\s+)?"X"` -- the definiendum, optionally preceded by "the
# term" (OK's own convention above; the bare-quote shape is tolerated too
# since the same idiom is plausible without that lead-in). The interposed
# clause is bounded to a SPECIFIC, recognizable statutory referent ("this
# act/chapter/section/title/article") -- not an unbounded lookahead to
# "means" anywhere later in the sentence, which is exactly the bug class
# `us_markers_boundary.py`'s own docstring warns against. `\s+` (not a
# literal space) between "this" and the referent tolerates the corpus's
# own paragraph-reconstruction line breaks (`as used in this\n\nact,`,
# confirmed live on `STATE_OK_T60_S60-175.3`'s `"Trustee's commission,"`).
_OK_GAP_IDIOM_RE = re.compile(
    r'(?:the\s+term\s+)?["“]([^"”]{1,200})["”]\s+'
    r"as used in this\s+(?:act|chapter|section|title|article)\b,?\s*"
    r"(?:shall mean|means|has the meaning)\b:?\s*",
    re.IGNORECASE,
)


def _split(text: str) -> list[str]:
    limit = trailing_stop_limit(text)
    starts: list[tuple[int, str, int]] = []
    for m in _OK_GAP_IDIOM_RE.finditer(text, 0, limit):
        # OK's own convention places a disambiguating comma INSIDE the
        # closing quote when a gap clause follows (`"Trustee's
        # compensation," as used in this act, means ...`) -- the same
        # artifact NV's UCC exclusion idiom exhibits (see `us_markers_
        # boundary.py`'s own `_EXCLUSION_CLAUSE_BRIDGE_RE` entry); always
        # stripped here since it is intrinsic to this rule's own idiom
        # shape, not a general per-jurisdiction toggle.
        term = m.group(1).strip().removesuffix(",").rstrip()
        if not term:
            continue
        starts.append((m.start(), term, m.end()))

    hard_stops, mn_subd_stops = compute_hard_stops(text, limit)
    entries = close_entries(text, limit, starts, hard_stops, mn_subd_stops)
    return entries_to_quoted_blocks(entries)


register_entry_splitter_rule(EntrySplitterRule(jurisdiction_codes=("US-OK",), split=_split))
