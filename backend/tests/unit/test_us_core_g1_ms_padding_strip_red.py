"""RED tests -- sprint 2026-08-05-defs-core-follow-on-2, gate G1 ("MS
padding strip", program doc `2026-08-04-definition-completeness.md`).

**The defect, byte-verified this pass (not merely relayed).**
`us_profile._leading_quote_candidate` (line 598) does:

    term_match = _LEADING_QUOTE_RE.match(block)
    term = term_match.group(1)          # <-- NO .strip()

while its sibling `_extract_inline_quoted_definitions` (line 551, the
placeholder-heading fallback) does:

    term = term_match.group(1).strip()  # <-- STRIPS

Both parse the SAME `_LEADING_QUOTE_RE = re.compile(r'^["“]([^”"]+)["”]')`
capture group; only one of the two call sites strips it. A real drafting
convention that pads the quote interior with whitespace (`"“ Conviction ”"`,
not `"“Conviction”"`) therefore comes back padded through the
PRIMARY path (`_split_into_numbered_blocks` + `_leading_quote_candidate`,
what every numbered/lettered-entry body -- the common case -- routes
through) but clean through the FALLBACK path.

**Real-row provenance.** `STATE_MS_T45_C10_S34-1` (Miss. Code Ann.
Section 45-34-1, the definitions section of MS's sex-offender-registration
chapter) is a REAL row whose 5 defined terms are ALL padded this way in the
source text: `"“ Conviction ”"`, `"“ Department ”"`,
`"“ Offender ”"`, `"“ Registrable offense ”"`,
`"“ Registrant ”"` -- independently pulled from the real
`us_ms_statutes.parquet` snapshot this pass (byte-identical `text` field,
1,015 chars) and vendored at `backend/tests/fixtures/us_statutes/
g1_ms_padded_terms_row.json`. First surfaced by the `2026-08-04-defs-us-
preamble` panel (manager ruling M-R32, commit `92c2b1f`/`bd4dde7`): that
panel could not fix `us_profile.py` (frozen to their own sprint's panel
fence) and instead added a TEST-SIDE `.strip()` workaround in their own 2
tests, explicitly routing the underlying defect here. This file is the
routed fix's RED, freshly authored against the real row (not a copy of
their workaround).

**Why this isn't exercised through the full pipeline.** `STATE_MS_T45_
C10_S34-1`'s real `section_title` ("Miss. Code Ann. § 45-34-1") is
recognized as a Definitions section ONLY via a registered `BodyPreambleRule`
(`rules/us_body_preamble.py`, the `2026-08-04-defs-us-preamble` panel's own
family module) -- confirmed this pass: on THIS branch (no such rule
registered), `USProfile("US-MS").is_definitions_heading(...)` is `False`
and `derive_heading_from_body(...)` is `None` for this row, so
`pipeline.py` would never reach `extract_definitions_from_section` for it
at all. Testing through `ingest_us_statute_rows` -> `run_definition_
linking` here would therefore RED for the wrong reason (a missing,
out-of-scope family rule, not this gate's padding defect). Both tests
below instead call `USProfile.extract_definitions_from_section` directly
on the body -- the exact function `pipeline.py` calls once a section IS
recognized (line ~263), and the literal function this gate names
(`_leading_quote_candidate`, its private helper) -- preceded by
`profile.normalize_for_parsing`, matching `pipeline.py`'s own Stage-0/
Stage-2 order (curly-quote collapse happens before extraction in
production; applying it here too keeps this test faithful even though it
does not affect padding either way).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.definition_links.us_profile import USProfile, find_term_uses

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "us_statutes"
    / "g1_ms_padded_terms_row.json"
)

EXPECTED_TERMS = {
    "Conviction",
    "Department",
    "Offender",
    "Registrable offense",
    "Registrant",
}


def _load_row() -> dict:
    rows = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 1
    return rows[0]


def _extract_ms_candidates():
    row = _load_row()
    assert row["act_id"] == "STATE_MS_T45_C10_S34-1"
    profile = USProfile(code="US-MS")
    normalized = profile.normalize_for_parsing(row["text"])
    return profile.extract_definitions_from_section(
        normalized, scope="chapter", heading_was_derived=True
    )


def test_ms_defined_terms_are_stripped_of_quote_interior_padding():
    """G1 item 1 (extraction). Today every one of the 5 real terms comes
    back with its literal leading/trailing space intact -- `(' Conviction
    ',)` etc., not `('Conviction',)` -- because `_leading_quote_candidate`
    never calls `.strip()` on the captured group. Fix: strip it there,
    consistent with `_extract_inline_quoted_definitions`'s own convention
    for the SAME regex capture group."""
    candidates = _extract_ms_candidates()
    assert len(candidates) == 5, f"expected 5 real MS terms, got {len(candidates)}"

    got_terms = {c.terms[0] for c in candidates}
    assert got_terms == EXPECTED_TERMS, (
        f"got {sorted(got_terms)!r} (raw, un-stripped) -- expected the "
        f"stripped set {sorted(EXPECTED_TERMS)!r}. Today's actual output "
        "pads every term with exactly one leading and trailing space "
        "(e.g. ' Registrant ' instead of 'Registrant'), because "
        "_leading_quote_candidate's `term = term_match.group(1)` line has "
        "no `.strip()`."
    )


def test_padded_term_silently_misses_a_mention_that_the_stripped_term_finds():
    """G1 item 2 (matching consequence, M-R32's named risk, direction
    proof). `find_term_uses` builds `re.compile(r"\\b" + re.escape(term) +
    r"\\b", ...)` -- since Python's `re.escape` does not escape a plain
    space (3.7+), a padded term's leading/trailing space becomes a LITERAL
    required space in the pattern, not merely a `\\b` boundary. That is
    satisfied by an ordinary space-separated mention (nothing regresses
    there -- see the second half of this test) but NOT by a mention that
    abuts punctuation with no space before it (an entirely ordinary English
    shape: "...a Registrant, upon conviction..."). This is the exact "real
    risk... silent under-linking" scenario the preamble panel's Planner
    named but explicitly left unproven for the general case (`-log.md`,
    2026-08-04 entry, M-R32 write-up: "fixture-specific luck... a mention
    directly abutting non-space punctuation would not match"). Proven here
    directly against the LIVE `find_term_uses` (not a stub), using the
    padded term AS ACTUALLY PRODUCED by today's live extractor above (not
    hand-typed), on a realistic (hand-authored, not corpus-sourced --
    the corpus row itself does not happen to contain a later mention of
    this term) illustrative "using" sentence, matching the style the
    preamble panel's own sibling MS test already uses for the same
    purpose.
    """
    candidates = _extract_ms_candidates()
    by_term = {c.terms[0]: c for c in candidates}
    padded_registrant = next(t for t in by_term if t.strip() == "Registrant")
    assert padded_registrant == " Registrant ", (
        f"today's live extractor produced {padded_registrant!r} -- if this "
        "changes, the test below needs to be re-pointed, not silently "
        "adjusted"
    )
    stripped_registrant = padded_registrant.strip()

    natural_mention = (
        "A Registrant who fails to comply with this chapter commits a violation."
    )
    abutting_mention = (
        "Any duty imposed on a Registrant, upon conviction of a subsequent "
        "offense, is not diminished."
    )

    # Non-regression half: an ordinary space-separated mention must keep
    # matching under EITHER term string -- this is what must NOT change
    # once the Developer's fix lands.
    assert len(find_term_uses(padded_registrant, natural_mention)) == 1
    assert len(find_term_uses(stripped_registrant, natural_mention)) == 1

    # Direction-proof half (the actual RED): a mention immediately
    # followed by a comma is missed by today's padded term, even though
    # the correctly-stripped term finds it -- proving the padding defect
    # is not cosmetic, it silently under-links real mentions.
    stripped_hits = find_term_uses(stripped_registrant, abutting_mention)
    assert len(stripped_hits) == 1, (
        f"sanity check failed: the STRIPPED term should find this ordinary "
        f"mention; got {len(stripped_hits)} matches"
    )
    padded_hits = find_term_uses(padded_registrant, abutting_mention)
    assert len(padded_hits) == 1, (
        f"today's PADDED term {padded_registrant!r} found "
        f"{len(padded_hits)} match(es) in {abutting_mention!r}, expected 1 "
        "(matching the stripped term) -- if this now passes, the padding "
        "under-linking risk M-R32 named is no longer real for this shape "
        "and this test's premise needs re-checking, not just its assertion "
        "flipped"
    )
