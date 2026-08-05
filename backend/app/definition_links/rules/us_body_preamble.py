"""US family-2 `BodyPreambleRule`s (sprint 2026-08-04-defs-us-preamble):
body preambles that introduce local definitions WITHOUT ever using the
literal word "Definitions" in the heading OR the body -- GA's `"As used in
this chapter, the term:"`, MD's `"In this section the following words have
the meanings indicated."`, NE's `"In the Nebraska Uniform Trust Code:"`,
and CA's wide-window `"...the following definitions apply:"` variant, among
others. See this sprint's `-log.md`, section `P-D4` for the build target
this file implements, and manager rulings M-R26/M-R27/M-R28 for the
dispatch contract these rules run under.

**Dispatch contract** (verified live by the manager, M-R26; NOT the shape
this module's own docstrings originally described in earlier sprint
attempts): `USProfile.derive_heading_from_body` tries the legacy, GATED
baseline first (`derive_heading_from_body` module function -- unaffected by
this file, and NEVER overridden once it returns non-`None`); only when the
baseline returns `None` does it fall through to
`registry.body_preamble_rules_for(self.code)`, trying each registered rule
IN REGISTRATION ORDER and returning the first non-`None` result (M-R27:
registration order, not filename-sort). `derive_heading` below receives
ONLY the article's body text -- never the heading -- and returns a
SYNTHESIZED heading string (there is no real "Definitions" substring to
extract from these bodies; unlike the legacy `_derive_heading_from_body`,
which slices a genuine matched span out of the body, these idioms never
contain the word "Definitions" at all, so a literal `"Definitions"` string
is returned instead -- it still satisfies `is_definitions_heading`'s
first-word rule, which is all the pipeline checks). Once a heading is
accepted, `pipeline.py`'s existing, UNEDITED `extract_definitions_from_
section` (falling back to `_extract_inline_quoted_definitions` when the
heading was body-derived) does the actual entry parsing -- this file's job
is recognition only, never extraction.

**`scope_unit_kind` -- not applicable here** (per the sprint brief's M-D3
erratum caveat): `BodyPreambleRule` (`registry.py`) has exactly two fields,
`jurisdiction_codes` and `derive_heading: Callable[[str], str | None]` --
there is no `scope_unit_kind` field on this dataclass, and `derive_heading`
returns only a heading string, never a scope/unit-kind value. Confirmed by
reading the dataclass definition directly, not inferred from the seam
doc's illustrative table -- nothing in this file declares or needs
`scope_unit_kind`.

**Registration order is precedence** (first-non-`None`-wins, M-R27):
precise, jurisdiction-scoped shapes are registered BEFORE the broad `US-*`
catch-alls, so a future broader rule can never silently starve a
state-specific one -- California's own wide-window variant and Nebraska's
"named code" idiom go first, then the two `US-*` idioms (B2 before B1,
narrower phrase before the more general trigger+colon shape).

**Hazard/false-positive discipline** (gate U5, this family's documented
known risk): the trigger vocabulary these rules key on ("As used in this
X", "For purposes of this X", "the term") is ALSO used, in the real
corpus, by pure forwarding references, exception/carve-out lists, and
ordinary administrative sentences that define nothing locally -- see
`test_us_body_preamble_hazard_catalogue_red.py` and `test_us_body_preamble_
negative_guard*.py`. Every rule below was verified, row-by-row, against
every real positive AND every real negative/hazard fixture row in this
sprint's `backend/tests/fixtures/us_statutes/` before being written here
(not merely reasoned about in prose) -- see the sprint log for the offset
measurements.
"""

from __future__ import annotations

import re

from app.definition_links.rules.registry import BodyPreambleRule, register_body_preamble_rule

# --- Rule 1: California, wide-window "...Definitions...apply/govern"  -----
#
# Same idiom the EXISTING legacy `us_profile._BODY_DEFINITIONS_PREAMBLE_RE`
# already targets (a literal "Definitions" followed, within a short bounded
# gap, by "apply(y/ies/ied)"/"govern"/"shall apply") -- CA's real corpus
# shape genuinely contains that word, it just fails the legacy regex's own
# 80-char prefix cap (CA's real prefix is 84 chars, confirmed live by this
# sprint's own `test_gate_b_prefix_cap_is_exactly_why_this_real_california_
# row_misses_today`). This is the SAME technique as the legacy baseline
# (slice a real matched span out of the body, ending in the word
# "Definitions", so it passes `is_definitions_heading`'s own last-word
# rule) -- just with the prefix cap widened. Scoped to `US-CA` only: this
# sprint measured CA's own 1,401-row population specifically (scout S4);
# widening this exact wide-window idiom to other states was never measured
# and is not claimed here.
_CA_DEFINITIONS_PREAMBLE_RE = re.compile(
    r"^.{0,200}?\bDefinitions?\b(?=.{0,120}?\b(?:appl(?:y|ies|ied)|govern|shall\s+apply)\b)",
    re.IGNORECASE | re.DOTALL,
)
_CA_SEARCH_WINDOW = 600


def _ca_wide_window_definitions_preamble(body: str) -> str | None:
    window = body[:_CA_SEARCH_WINDOW]
    match = _CA_DEFINITIONS_PREAMBLE_RE.match(window)
    return window[: match.end()] if match is not None else None


# Shape 7 (Q-D2, M-R40/M-R49): this exact idiom, verbatim, also appears in
# Indiana (`STATE_IN_T21_A44_C7_S21-44-7-1` and its versioned sibling) and
# Mississippi (Q-D2 independently named `STATE_MS_T17_C3_S17-103` as the
# same idiom) -- the regex itself needs no change, only the jurisdiction
# list. Manager ruling M-R49: ships as an EXPLICIT list (`US-CA`, `US-IN`,
# `US-MS`), NOT a blanket `US-*` -- a wildcard would make this rule (still
# registered FIRST, slot #1) capable of preempting NE's own narrower rule
# at slot #2 for any Nebraska row that also happens to contain this idiom,
# an open question this cycle deliberately did not resolve by assumption;
# the explicit list also claims 3.3x fewer rows than the blanket
# alternative (352-440 vs 1,173, D3's own measurement).
register_body_preamble_rule(
    BodyPreambleRule(
        jurisdiction_codes=("US-CA", "US-IN", "US-MS"),
        derive_heading=_ca_wide_window_definitions_preamble,
    )
)

# --- Rule 2: Nebraska, "In the <Named Code/Act>:" quoted list -------------
#
# NE's real convention (D1 finding, live-verified against
# `STATE_NE_C30_S30-3803`, the Nebraska Uniform Trust Code): `"In the
# <Named Code/Act>: (1) "Term", ... (2) "Term" means ..."` -- a preamble
# that never says "As used in"/"For purposes of this <unit>" at all (so
# neither idiom below reaches it), anchored at the START of the body
# (allowing one short leading parenthetical aside, e.g. `"(UTC 103) "`).
# Only fires when a quoted term appears shortly after the intro clause's
# own colon -- NE's OTHER, unquoted convention (`"For purposes of the
# <Act>: (1) Health insurance plan means ..."`, no quote marks anywhere)
# is a genuine, disclosed, cross-sprint dependency on
# `2026-08-04-defs-us-markers` (neither `extract_definitions_from_section`
# nor the inline-quote fallback can parse an unquoted entry today, verified
# live) -- this rule deliberately does NOT fire for that shape, since even
# a correct heading cannot make it extract. Scoped to `US-NE`: this exact
# "named code" phrasing was only measured on Nebraska this sprint.
_NE_NAMED_CODE_INTRO_RE = re.compile(
    r"^(?:\([^)]{0,40}\)\s*)?(?:In the|For purposes of the)\s+[^:\n]{1,100}:",
    re.IGNORECASE,
)
_NE_QUOTE_LOOKAHEAD = 40


def _ne_named_code_quoted_list(body: str) -> str | None:
    match = _NE_NAMED_CODE_INTRO_RE.match(body)
    if match is None:
        return None
    tail = body[match.end() : match.end() + _NE_QUOTE_LOOKAHEAD]
    return "Definitions" if re.search(r'["“]', tail) else None


register_body_preamble_rule(
    BodyPreambleRule(jurisdiction_codes=("US-NE",), derive_heading=_ne_named_code_quoted_list)
)

# --- Rule 2b: Named-Act "As used in the <Act/Code>" + quoted term + -------
# --- means/also means ------------------------------------------------------
#
# Q-D2 shape 5 (M-R40): "As used in the <Named Act>" -- the word "the", not
# "this" -- reaches neither B1's own trigger (which requires the literal
# word "this" right after "in"/"of") nor its quote-means branch. Real row
# `STATE_NM_C3_A32_S3-32-3`: `"As used in the Industrial Revenue Bond Act,
# "project" also means: A. any land..."`. Cross-confirmed by two
# independent methods this same cycle (Q-D2's P-R7 sweep and Q-D3's
# guarded-cluster cross-check) landing on the SAME real row. M-R40 ruled
# RECOGNITION ours, SCOPE (a Named-Act-bounded unit rather than "this
# <unit>") a core follow-on out of bounds here -- like every other rule in
# this file, this one only supplies a synthesized "Definitions" heading.
#
# Registered EARLY (right after NE, before B2/B1) per M-R27's own
# narrow-trigger-before-broad-catch-all precedence discipline -- checked
# against B1's own shape-2/3/6 widenings this same cycle and found disjoint
# ("the <Act>" vs "this <unit>" never overlap, D4's own overlap notes).
# `US-*`: measured hits span NM/NE/OK/AR/OH, not one state (D4).
_NAMED_ACT_TRIGGER_RE = re.compile(
    r"As used in the\s+(?:[A-Z][A-Za-z.'\-]*\s+){1,8}(?:Act|Code)\b,?\s*"
)
_NAMED_ACT_LOOKAHEAD = 60
_NAMED_ACT_QUOTE_MEANS_RE = re.compile(
    r'^["“][^"”]{1,150}["”]\s*(?:also\s+)?(?:means|shall mean)\b',
    re.IGNORECASE,
)


def _named_act_also_means_preamble(body: str) -> str | None:
    for trigger_match in _NAMED_ACT_TRIGGER_RE.finditer(body):
        after = body[trigger_match.end() : trigger_match.end() + _NAMED_ACT_LOOKAHEAD]
        if _NAMED_ACT_QUOTE_MEANS_RE.match(after):
            return "Definitions"
    return None


register_body_preamble_rule(
    BodyPreambleRule(jurisdiction_codes=("US-*",), derive_heading=_named_act_also_means_preamble)
)

# --- Rule 3: B2 -- "In this <unit>[,] the following word(s) have the -----
# --- meaning(s) indicated" -------------------------------------------------
#
# Scout S3's naming. MD's own dominant convention (D1: 3,327/39,552 real
# MD rows, 8.4%), also DE/LA/WV (a strict subset of B1's own state list,
# same shared numbered-list splitter downstream -- no new extraction logic
# needed). A fixed, specific phrase ("the following words have the
# meaning(s) indicated") with no real-world false-positive shown anywhere
# in this sprint's hazard/negative-guard catalogue -- registered before the
# broader B1 idiom below purely to keep precise-before-broad the rule
# (M-R27), not because an overlap was found.
_B2_WORDS_HAVE_MEANINGS_RE = re.compile(
    r"In this\s+[A-Za-z][A-Za-z0-9 .\-]{0,30}\s*,?\s*the following words?\s+have\s+the\s+meanings?"
    r"\s+indicated\s*[.:]",
    re.IGNORECASE,
)
_B2_SEARCH_WINDOW = 600

# Shape 8 (Q-D2): MS's REAL convention is not a same-slot word swap
# ("indicated" -> "ascribed") but a genuinely reordered sentence -- the
# subject ("the following words and phrases") and the "when used in this
# <unit>" clause come BEFORE "have the meaning(s)", and the closing phrase
# is "respectively ascribed to them" instead of "indicated":
# `STATE_MS_T27_C7_S19-3`, `"The following words and phrases when used in
# this article for the purpose of this article have the meanings
# respectively ascribed to them in this section, except ...:"`. Gap bounds
# (120 / 60 chars) are set above this one real row's own measured gaps (86
# / 13 chars) with margin, the same discipline B1's own `_COLON_WINDOW` was
# set under. The one-row result is fixture-only, not a corpus-wide uniqueness
# claim. M-R53's em-dash measurement is separately reconciled as 1,788
# whole-body rows / 984 operationally captured rows. Deliberately does NOT
# require an immediately-following
# colon (unlike the original B2 pattern above) -- the real row's own colon
# sits 129 chars after "ascribed to them", behind an "except in those
# instances..." carve-out clause, so anchoring on it would just reintroduce
# the same kind of prefix-cap miss CA's own wide-window rule was written to
# avoid.
_B2_WORDS_PHRASES_ASCRIBED_RE = re.compile(
    r"following words and phrases\b.{0,120}?\bhave\s+the\s+meanings?\b.{0,60}?"
    r"\bascribed\s+to\s+(?:them|it)\b",
    re.IGNORECASE | re.DOTALL,
)


def _b2_words_have_meanings_indicated(body: str) -> str | None:
    window = body[:_B2_SEARCH_WINDOW]
    if _B2_WORDS_HAVE_MEANINGS_RE.search(window) or _B2_WORDS_PHRASES_ASCRIBED_RE.search(window):
        return "Definitions"
    return None


register_body_preamble_rule(
    BodyPreambleRule(jurisdiction_codes=("US-*",), derive_heading=_b2_words_have_meanings_indicated)
)

from app.definition_links.rules.us_body_preamble_b1 import (
    _B1_COLON_WINDOW,
    _B1_FORWARDING_PHRASES,
    _B1_LOOKAHEAD,
    _B1_QUOTE_MEANS_RE,
    _B1_TRIGGER_RE,
    _b1_colon_list_branch,
    _b1_quote_means_branch,
    _b1_trigger_colon_or_quote_means,
)


register_body_preamble_rule(
    BodyPreambleRule(jurisdiction_codes=("US-*",), derive_heading=_b1_trigger_colon_or_quote_means)
)
