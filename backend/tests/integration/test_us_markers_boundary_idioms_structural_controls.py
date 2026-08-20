"""RED + negative-control structural tests (sprint 2026-08-20-defs-
boundary-idioms, issue #27) for widening
`backend/app/definition_links/rules/us_markers_boundary.py`'s
`_TIGHT_IDIOM_RE` to recognize "shall include" and the "has the meaning"
family's "has the following meaning"/"has the same meaning" variants.

Per manager ruling M-R107: every fixture here is fully synthetic, built
from unseen identifiers (Greek-letter-style term names never used
elsewhere in the corpus or this test suite) -- no jurisdiction, term,
section number, date, or title is keyed on. This proves the GENERAL
mechanism, not a fact about any one real row (the real-row recovery is
covered separately by the companion NJ Department / NJ Public body /
NJ c5guard Pipeline tests in this sprint).

Mirrors `test_us_markers_fx7_ceiling_known_closed_scope.py`'s own style: a
long, ordinary-prose sentence containing no digits, parens, colons,
dashes, or quote characters, repeated well past `MAX_CLEAN_DEFINITION_
LENGTH` (3,000 chars), so the ceiling is exercised honestly and nothing in
the padding can accidentally fire a hard-stop of its own.
"""
from __future__ import annotations

from app.definition_links.rules.us_markers_boundary import (
    MAX_CLEAN_DEFINITION_LENGTH,
    extract_quote_anchored_entries,
)

_MARKER_FREE_SENTENCE = (
    "This clause continues at exceptional length purely as a matter of "
    "ordinary statutory drafting style, adding qualifying language after "
    "qualifying language without ever introducing a numbered or lettered "
    "sub item, a colon, or a dash, so nothing in this padding can ever be "
    "mistaken for a marker boundary. "
)
_LONG_MARKER_FREE_PADDING = _MARKER_FREE_SENTENCE * 30

assert len(_LONG_MARKER_FREE_PADDING) > MAX_CLEAN_DEFINITION_LENGTH, (
    "test padding must itself exceed the ceiling for any test below to be meaningful"
)


# --- RED: positive recovery, "shall include" -------------------------------


def test_red_shall_include_recovers_a_ceiling_tripped_last_entry():
    """A last-entry term ("Zylo") with no recognized next term today: the
    true next term ("Wroth") uses "shall include", not yet in
    `_TIGHT_IDIOM_RE`. Today "Zylo" runs to end-of-text (well past the
    ceiling) and is silently dropped. Once "shall include" is recognized,
    "Zylo" must be recovered bounded exactly at "Wroth"'s own quote, and
    "Wroth" itself must also be captured."""
    text = f'"Zylo" means {_LONG_MARKER_FREE_PADDING}"Wroth" shall include the second concept.'
    entries = dict(extract_quote_anchored_entries(text))

    assert "Zylo" in entries, (
        "'Zylo' is missing entirely -- still being ceiling-dropped. "
        "_TIGHT_IDIOM_RE must recognize 'shall include' so 'Wroth' becomes "
        "a real next `starts` entry and bounds 'Zylo' regardless of length."
    )
    assert entries["Zylo"] == _LONG_MARKER_FREE_PADDING.strip(), (
        f"'Zylo' must close exactly at 'Wroth''s own quote: got "
        f"{entries['Zylo'][:80]!r}...{entries['Zylo'][-80:]!r}"
    )
    assert entries.get("Wroth") == "the second concept.", (
        f"'Wroth' itself must also be captured with its own 'shall include' "
        f"idiom stripped: got {entries.get('Wroth')!r}"
    )


# --- RED: positive recovery, "has the meaning" family ----------------------


def test_red_has_the_following_meaning_recovers_a_ceiling_tripped_last_entry():
    """Same shape, but the true next term ("Quorlin") uses "has the
    following meaning" -- a variant of the already-recognized "has the
    meaning" with an inserted "following", not yet tolerated."""
    text = (
        f'"Yavren" means {_LONG_MARKER_FREE_PADDING}'
        f'"Quorlin" has the following meaning: the second concept.'
    )
    entries = dict(extract_quote_anchored_entries(text))

    assert "Yavren" in entries, (
        "'Yavren' is missing entirely -- still being ceiling-dropped. "
        "_TIGHT_IDIOM_RE must tolerate 'has the following meaning'."
    )
    assert entries["Yavren"] == _LONG_MARKER_FREE_PADDING.strip()
    assert entries.get("Quorlin") == "the second concept.", (
        f"'Quorlin' itself must also be captured: got {entries.get('Quorlin')!r}"
    )


def test_red_has_the_same_meaning_recovers_a_ceiling_tripped_last_entry():
    """Same shape again, with "has the same meaning" (an inserted "same")."""
    text = (
        f'"Brellick" means {_LONG_MARKER_FREE_PADDING}'
        f'"Tannery act" has the same meaning as that term is defined elsewhere.'
    )
    entries = dict(extract_quote_anchored_entries(text))

    assert "Brellick" in entries, (
        "'Brellick' is missing entirely -- still being ceiling-dropped. "
        "_TIGHT_IDIOM_RE must tolerate 'has the same meaning'."
    )
    assert entries["Brellick"] == _LONG_MARKER_FREE_PADDING.strip()
    assert entries.get("Tannery act") == "as that term is defined elsewhere.", (
        f"'Tannery act' itself must also be captured: got {entries.get('Tannery act')!r}"
    )


# --- Negative controls: GREEN today, MUST STAY GREEN after the widening ----


def test_negative_control_shall_include_in_ordinary_prose_does_not_rescue_the_ceiling():
    """A genuinely unbounded last entry ("Fenwick") whose OWN padding
    happens to contain the literal words "shall include" in ordinary
    prose -- NOT immediately after a closing quote. `_TIGHT_IDIOM_RE`'s
    tightness (`.match`, anchored right at the quote's own end, not
    `.search` anywhere in the text) means this must NOT be treated as a
    new entry and must NOT rescue "Fenwick" from the ceiling. GREEN today
    (the ceiling already drops this); MUST STAY GREEN after "shall
    include" is recognized -- the widening is a POSITIONAL idiom-adjacency
    fix, not a bare substring search, exactly the same design principle
    `_TIGHT_IDIOM_RE`'s own docstring already states for "means" ("an
    idiom found only because it happens to occur somewhere later in an
    unrelated sentence never qualifies")."""
    padding_with_prose_shall_include = (
        _LONG_MARKER_FREE_PADDING
        + "Any future regulation adopted under this section shall include "
        "reasonable notice to affected parties before taking effect. "
        + _LONG_MARKER_FREE_PADDING
    )
    text = f'"Fenwick" means {padding_with_prose_shall_include}'
    entries = dict(extract_quote_anchored_entries(text))

    assert "Fenwick" not in entries, (
        f"'Fenwick' must still be DROPPED by the ceiling -- 'shall include' "
        f"appearing in ordinary prose (not immediately after a closing "
        f"quote) must never be mistaken for a defining idiom. Got "
        f"{entries.get('Fenwick', '<absent>')[:120]!r}"
    )


def test_negative_control_loose_meaning_language_does_not_rescue_the_ceiling():
    """Same shape, with prose that uses the word "meaning" loosely (not
    the tight "has the (following/same) meaning" idiom shape) -- must not
    be mistaken for the widened idiom either. GREEN today; MUST STAY
    GREEN after the widening."""
    padding_with_loose_meaning = (
        _LONG_MARKER_FREE_PADDING
        + "The committee debated the practical meaning of this provision "
        "at considerable length without reaching a conclusion. "
        + _LONG_MARKER_FREE_PADDING
    )
    text = f'"Corvale" means {padding_with_loose_meaning}'
    entries = dict(extract_quote_anchored_entries(text))

    assert "Corvale" not in entries, (
        f"'Corvale' must still be DROPPED by the ceiling -- the word "
        f"'meaning' appearing loosely in prose must never be mistaken for "
        f"the tight 'has the (following/same) meaning' idiom. Got "
        f"{entries.get('Corvale', '<absent>')[:120]!r}"
    )


def test_shall_include_on_a_nested_nonquote_adjacent_mention_is_consistent_with_means():
    """Documents, rather than gates, a structural property found while
    building this sprint's negative controls: when a DIFFERENT quoted
    phrase sits mid-body immediately before the idiom (no ordinary-prose
    gap), the widened engine splits the OUTER entry there -- but this is
    NOT a new risk "shall include" introduces. The identical, ALREADY-
    RECOGNIZED "means" idiom does the exact same thing TODAY, unmodified
    by this sprint (verified directly below, current code, no monkeypatch)
    -- it is `_TIGHT_IDIOM_RE`'s own pre-existing, by-design tight-
    adjacency behavior (see this module's docstring: any quote immediately
    followed by a recognized idiom is always a new `starts` entry,
    regardless of surrounding prose). Widening the idiom VOCABULARY does
    not change WHERE that line is drawn, only which words sit on the
    recognized side of it. Real corpus evidence (this sprint's collateral
    sweep of the 21 jurisdictions `extract_quote_anchored_entries` is
    reachable for, see the log doc): the one real occurrence of a mid-body
    "shall include" following a nested quote (NJ "Board"/"Pipeline",
    `STATE_NJ_T48_C10_S10-3`) is verified NOT to corrupt anything, because
    baseline's own long-form capture wins that term's dedup ahead of this
    engine's shorter, split contribution (see this sprint's c5guard_nj
    re-pin) -- the identical protection "means" already relies on for any
    pre-existing occurrence of this shape corpus-wide."""
    outer_prefix = (
        '"Halvorne" means the main concept, which in turn includes a '
        'component known as "Sixthward permit" '
    )
    nested_tail = "an ancillary authorization process."

    # The OUTER term's own idiom is held constant ("means", already
    # recognized) -- only the NESTED quote's idiom varies. This pins the
    # ALREADY-RECOGNIZED "means" idiom's behavior in this exact shape --
    # true today, unmodified by this sprint, and stays true after (nothing
    # about widening `_TIGHT_IDIOM_RE`'s vocabulary changes how an
    # ALREADY-recognized idiom behaves). Once "shall include" is ALSO
    # recognized (this sprint's own RED tests above prove that
    # separately), the identical nested-quote shape with "shall include"
    # in place of "means" splits "Halvorne" the exact same way, at the
    # exact same position -- not a new or different risk, just the same
    # pre-existing tight-adjacency rule applied to one more idiom word.
    text_nested_means = outer_prefix + "means " + nested_tail
    entries_nested_means = dict(extract_quote_anchored_entries(text_nested_means))
    assert entries_nested_means.get("Halvorne") == (
        "the main concept, which in turn includes a component known as"
    ), (
        "sanity/documentation: the ALREADY-RECOGNIZED 'means' idiom splits "
        f"'Halvorne' at the nested quote in this shape, unmodified by this "
        f"sprint: got {entries_nested_means.get('Halvorne')!r}"
    )
    assert entries_nested_means.get("Sixthward permit") == nested_tail, (
        f"sanity: got {entries_nested_means.get('Sixthward permit')!r}"
    )
