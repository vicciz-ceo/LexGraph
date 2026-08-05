"""Rule: `EntrySplitterRule`s for two class-(d) structural sub-shapes of a
recognized הגדרות/הגדרה section body that baseline `extract._split_into_
blocks` cannot turn into ANY block at all (sprint 2026-08-04-defs-il,
Phase D / D-1b bundle, contract item 5's `test_class_d_prose_body_
definitions_section_yields_zero_today` / `test_class_d_minimal_single_
sentence_variant_is_captured` / `test_class_d_variant_double_colon_entry_
list_under_a_trigger_preamble_is_captured`).

## Root cause (re-confirmed live this session, matches the Planner's and
manager's own prior positive-control transcripts, log entries "Planner
D-1b" / "M20")

`HebrewProfile.extract_definitions_from_section` (profiles.py:210, FROZEN)
unions baseline's own `extract._split_into_blocks(text)` output with every
registered `EntrySplitterRule`'s blocks, then hands EVERY block (baseline
or rule-contributed) to baseline's OWN, unchanged `extract._parse_block`.
`_split_into_blocks` requires a line matching `^\\s*:-` to start ANY
block -- a body with no such line produces ZERO blocks, so the per-block
parse loop never even runs, regardless of how well-formed the body's own
prose is. This is a missing-BLOCK gap, not a clause-parsing gap: baseline
`_parse_block` already correctly extracts a `"term" - definition` sentence
once it is HANDED one -- proven live, unaided, by simply registering a
probe splitter that returns the whole body as one block (see the sprint
log's Job-1 transcript for both this shape and the `::-` shape below).

## Two independent sub-shapes, two independent rules

1. `_split_marker_less_prose` -- a body with NO `:-`-prefixed line
   anywhere (the single-sentence minimal variant) -- returns the WHOLE
   body as one block, letting baseline's own `_parse_block` read its
   first line. Only the FIRST line's `"term" - definition` sentence is
   ever extracted this way (`_parse_block` never re-scans later lines for
   a second entry) -- deliberately narrow, matching exactly what this
   bundle's two RED tests need and what the Planner's own positive
   control proved, not a general multi-entry marker-less-prose parser
   (that is a materially bigger, unauthorized design -- ruling M7's own
   two-pass numbered-continuation guard is future work for a different,
   larger effort, not this bundle's job).
2. `_split_double_colon_dash_entries` -- a body whose real entries are
   marked `::-` (double colon-dash) rather than the single `:-` baseline
   requires (e.g. a `(א) בתקנות אלה -` preamble line followed by `::-`-
   marked entries) -- mirrors baseline's own `_split_into_blocks`
   algorithm exactly, keyed on `::-` instead of `:-`, EXCEPT continuation
   collection stops (flushing the current block, not accumulating) the
   moment a line drops back to a shallower marker depth (anything not
   itself `::`-prefixed) -- deliberately stricter than baseline's own
   "accumulate everything until the next top-level marker" rule, so a
   trailing single-colon closing sentence (e.g. this fixture's own
   `: (ב) בתקנות אלה תהא ...`) is never silently appended to the last
   nested entry's own definition text.

Both rules are pure block-producers -- neither parses a term or builds a
`DefinitionCandidate` itself; baseline's own frozen `_parse_block` (via
`HebrewProfile.extract_definitions_from_section`'s union loop) does that
work, unaided, for every block either rule contributes. This is why the
multi-quote entry inside sub-shape 2's own real fixture (`"מס שבח מקרקעין"
ו"זכות במקרקעין" - ...`) is captured correctly with no extra code here --
baseline's existing `_parse_terms_and_qualifier` already handles N>=1
quoted terms per block, unaided.

## Regression scan (this session, read-only, before committing)

Scanned every `*.wiki` fixture under `backend/tests/fixtures/wiki_laws/`
for a definitions-heading (`sections.is_definitions_heading`) article
whose body either has zero `:-`-prefixed lines or has any `::-`-prefixed
line: exactly 3 hits, all 3 this bundle's own target fixtures (the two
single-sentence ones plus the `::-` one) -- zero other fixture is
affected by either rule. (No IL `HeadingRule`/`BodyPreambleRule` is
registered anywhere in this codebase today, confirmed by grep, so
`is_definitions_section` reduces exactly to `sections.
is_definitions_heading`'s own baseline regex; every OTHER
definitions-heading fixture in the whole suite already has a `:-` line
and no `::-` line, so neither new rule changes its block set at all.)

## D-CERT fix (sprint 2026-08-05-defs-il-certification, C4 fix loop):
## the 'ltr' over-capture defect and the boundary rule that closes it

**The defect, re-confirmed live before this fix.** `HebrewProfile.
extract_definitions_from_section` (profiles.py, FROZEN) UNIONS baseline's
`extract._split_into_blocks(text)` blocks with every registered
`EntrySplitterRule`'s OWN blocks for the SAME `text` -- by design, for
zero-miss recall (see that method's own docstring). `_split_double_colon_
dash_entries` above was unconditionally scanning the WHOLE section text
for `::-`-prefixed lines, with no awareness that some of those lines
might ALREADY be sitting inside a `:-` block baseline itself opened and
is still accumulating. `צו המועצות המקומיות (מועצה מקומית תעשייתית
נאות חובב)` article 1 is exactly this: `:- "תחום המועצה" -` opens ONE
baseline block whose continuation is a run of `::-`-prefixed land-block
("גוש") rows -- baseline alone correctly treats the whole run as ONE
block/one candidate. But this rule ALSO walked the same text independent
of baseline's accumulation state and re-split each of those SAME `::-`
lines into its own top-level block, so `_parse_block` (baseline, frozen,
unaware it is being asked to parse the same content twice) ran a SECOND
time per line. Most re-parses correctly yield nothing (no quoted span in
a plain `גוש 39774 - ...` row). Eight of those rows happen to contain
`<span dir="ltr">NNNNNN_N</span>` markup -- an RTL-document typographic
wrapper, unrelated to legal drafting -- and `dir="ltr"` is itself a
`"..."`-quoted span indistinguishable, to `extract._QUOTE_RE`, from a
genuine defined term. Each such re-split line therefore manufactured a
spurious `DefinitionCandidate` whose only "term" is the literal string
`'ltr'` (one line alone -- five `<span dir="ltr">` tags before its first
real dash -- produced a single candidate carrying SEVEN `'ltr'` terms at
once). This is a duplicate-parse defect; the markup is only what makes
the duplicate visible, not the cause of it.

**The first attempt, and why a corpus-wide A/B (not any test) proved it
wrong.** The obviously "structural" idea tried first: a `::-` line is a
legitimate entry only when the section has NO `:-`-prefixed line
anywhere (baseline's `_split_into_blocks` never resets `current` back to
`None` once it sees its first `:-` line, so past that point every `::-`
line is already inside some baseline block by construction -- and this
is exactly `_split_marker_less_prose`'s own existing guard, sub-shape 1
above). It fixed the `'ltr'` fixture and kept every committed RED/control
green -- and it was still wrong. A corpus-wide A/B (comparing every
definitions-heading article's candidate set before/after, the same
measurement this fix's own verification section demands) found 33
articles changed, 112 candidates lost, only 8 containing `'ltr'`. The
other 104, across 32 real files (`חוק הגנת הצרכן`, `חוק ניירות ערך`, `חוק
עידוד התעשיה (מסים)`, `פקודת התעבורה`, +28 more), were GENUINE nested
sub-definitions: e.g. `חוק הגנת הצרכן` art.1 has `:- "נותן ערבות אחר" -
... לעניין הגדרה זו -` (ending "for purposes of this definition -", a
DASH, not the COMMA baseline's own `_NESTED_MARKER_RE` requires) followed
by three `::-` entries that are real, independent terms baseline itself
folds unparsed into `"נותן ערבות אחר"`'s own text for exactly that reason.
The buggy pre-fix splitter was, as a side effect, already recovering
these correctly -- so "no `:-` anywhere" is FALSE as a boundary: most
`::-`-under-`:-` runs corpus-wide are genuine, and נאות חובב's land-block
list is the OUTLIER. Shipping that guard would have been a silent
104-term precision-for-recall trade (P-R2: escalate, don't absorb) --
discarded, not shipped. Kept here, not deleted from history, as a
concrete instance of this sprint's own lesson: green tests are not proof
at corpus scale, including a Developer's own fix attempt.

**The rule actually shipped: reject a `::-` line only when EVERY quoted
span it would contribute is markup, not Hebrew legal-drafting text.**
`_is_markup_quote_only` (below) parses each candidate line's quoted
spans with the SAME pairing `extract._QUOTE_RE`/`_parse_terms_and_
qualifier` themselves use (open-quote...close-quote; checked at this
granularity, not per raw `"`, because a CLOSING quote is never itself
preceded by an `attr=` token -- only an OPENING quote can be), and
checks whether each span's opening quote is immediately preceded by an
HTML/wiki attribute-assignment token (`attr=`, or a `{{=}}`-escaped
`=`) -- the exact `_HTML_ATTR_RE` pattern `backend/tests/certification/
c1_denominator.py` already established and named `wiki_table_markup_
attribute` for the unrelated MediaWiki table-header case (this module's
own "Root cause" section already noted that shared lineage). A line is
rejected only when it has at least one quoted span AND every one is
markup-attribute-quoted; a genuine quote anywhere (even beside an
incidental markup one) keeps the line; no quote at all also keeps it
(harmless -- baseline's `_parse_block` already yields `[]` for it
unaided). General to any HTML/wiki attribute, not a `'ltr'` literal, and
it strips/rewrites nothing -- it only decides which blocks this rule
contributes to the union baseline already receives. Re-measured
corpus-wide after adopting it (sprint log, this date): exactly 1 article
changed (the target fixture), exactly 8 candidates lost, all 8
containing `'ltr'`, zero gained -- the 32-article false-positive
regression from the first attempt is completely gone.

**Alternatives rejected, and why:**

1. *Blacklist the literal string `'ltr'`.* Rejected per explicit
   instruction: value-shaped, not structural -- would not survive the
   next markup variant (`dir="rtl"`, any other quoted HTML attribute).
2. *Strip HTML tags/attributes before extraction.* Rejected: touches the
   normalization stage (frozen), and still leaves the union free to
   duplicate-parse the next non-HTML false-positive quote pattern.
3. *Filter candidates whose only term is `'ltr'` after the fact.*
   Rejected: `profiles.py`/`pipeline.py` are FROZEN for this fix, and
   it's the same value-shaped objection as (1), one layer downstream.
4. *The whole-text "no `:-` line anywhere" guard, or a positional
   variant of it (only suppress a `::-` line specifically AFTER the
   nearest preceding `:-` line).* See above -- empirically disproven by
   the corpus-wide A/B; narrowing a wrong boundary condition does not
   fix what makes it wrong (it misidentifies WHICH `::-` runs are
   genuine, not which `:-` line they happen to follow).
"""

from __future__ import annotations

import re

from app.definition_links.rules.registry import EntrySplitterRule, register_entry_splitter_rule

_TOP_LEVEL_ENTRY_RE = re.compile(r"^\s*:-\s?")
_DOUBLE_COLON_DASH_RE = re.compile(r"^\s*::-\s?")
_DOUBLE_COLON_RE = re.compile(r"^\s*::")

# D-CERT fix (see module docstring, "The rule actually shipped"): the SAME
# pattern `backend/tests/certification/c1_denominator.py` already established and
# named `wiki_table_markup_attribute` -- an HTML/wiki-template attribute-
# assignment token (`dir=`, `width=`, a `{{=}}`-escaped `=`) immediately
# before a `"` means that quote delimits an ATTRIBUTE VALUE, never Hebrew
# legal-drafting text. General to any attribute name, not a `'ltr'`
# literal.
_HTML_ATTR_RE = re.compile(r"[A-Za-z][A-Za-z-]*(?:=|\{\{=\}\})$")
# Mirrors `extract._QUOTE_RE` exactly (same OPEN..."..."...CLOSE pairing) --
# checked at this granularity, not per raw `"` character, because a
# CLOSING quote is never itself preceded by an `attr=` token (its own
# attribute VALUE text sits there instead, e.g. `dir="ltr` immediately
# before the closing `"`) -- only a span's OPENING quote can ever be.
_QUOTE_SPAN_RE = re.compile('"([^"]+)"')


def _is_markup_quote_only(line: str) -> bool:
    """True when `line` contains at least one quoted SPAN (the same
    granularity `_parse_terms_and_qualifier` uses to decide what counts as
    a "term") and EVERY such span's OPENING quote is immediately preceded
    by an HTML/wiki attribute-assignment token (see `_HTML_ATTR_RE`) --
    i.e., every quoted span on this line is a markup attribute value, none
    of them could possibly be a real legal-drafting term. A line with no
    quoted span at all returns `False` (nothing to reject; baseline
    `_parse_block` already produces `[]` for a quote-less block on its
    own, unaided)."""
    spans = list(_QUOTE_SPAN_RE.finditer(line))
    if not spans:
        return False
    return all(_HTML_ATTR_RE.search(line[: m.start()]) for m in spans)


def _split_marker_less_prose(text: str) -> list[str]:
    """Whole-body-as-one-block fallback, ONLY when no line anywhere in
    `text` starts a baseline `:-` block -- see module docstring sub-shape
    1. Returns `[]` (no extra block) whenever baseline would already have
    something to work with on its own, so this can never duplicate or
    interfere with an already-working `:-` section."""
    if any(_TOP_LEVEL_ENTRY_RE.match(line) for line in text.split("\n")):
        return []
    if not text.strip():
        return []
    return [text]


def _split_double_colon_dash_entries(text: str) -> list[str]:
    """Mirrors baseline `extract._split_into_blocks`, keyed on `::-`
    instead of `:-` -- see module docstring sub-shape 2 for why
    continuation collection stops at the first non-`::`-prefixed line
    instead of running to the next top-level marker.

    D-CERT fix (see module docstring, "The rule actually shipped"): a
    `::-` line whose only quote(s) are markup noise (`_is_markup_quote_only`) is
    NEVER treated as a new top-level entry -- it is handled exactly like
    any other line that fails BOTH double-colon patterns (closes out
    whatever was accumulating, contributes nothing itself). Every OTHER
    `::-` line (no quote at all, or at least one genuine quote) opens a
    block exactly as before -- corpus-wide re-verification (sprint log,
    this date) found zero genuine nested `::-` entry anywhere this filter
    rejects."""
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if _DOUBLE_COLON_DASH_RE.match(line):
            stripped_line = _DOUBLE_COLON_DASH_RE.sub("", line, count=1)
            if _is_markup_quote_only(stripped_line):
                if current is not None:
                    blocks.append(current)
                current = None
                continue
            if current is not None:
                blocks.append(current)
            current = [stripped_line]
        elif _DOUBLE_COLON_RE.match(line) and current is not None:
            current.append(line)
        else:
            if current is not None:
                blocks.append(current)
            current = None
    if current is not None:
        blocks.append(current)
    return ["\n".join(b) for b in blocks]


register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("IL",), split=_split_marker_less_prose)
)
register_entry_splitter_rule(
    EntrySplitterRule(jurisdiction_codes=("IL",), split=_split_double_colon_dash_entries)
)
