"""RED (work-count) -- sprint 2026-08-10-core-g4-discriminator-perf.

**The defect** (sprint contract, mandate; `us_profile.py:1488-1509`):
`_citation_or_xref_context` probes up to five suffix regexes as
`PATTERN.search(body, 0, trimmed_end)` -- `pos` is the LITERAL constant `0`,
never a function of `token_start`. Since every probe pattern ends in `\\Z`
(anchored at `trimmed_end`, the `endpos` argument), each `.search()` call
must try matching at every start position in `[0, trimmed_end)` before it
can conclude no match exists, costing O(`trimmed_end`) -- i.e. O(document
position) -- per call, per token, regardless of how far back a real citation
or structural word could possibly be. Measured evidence in the sprint
contract: 6,800 `re.Pattern.search` calls costing 3.401 of 3.438 profiled
seconds on a 187KB real row.

**This test's shape** (work-count, the sprint's preferred RED shape --
deterministic, no wall-clock, cannot flake): it wraps each of the five
suffix-regex objects `_citation_or_xref_context` calls with a thin recorder
that forwards to the REAL `.search()` (so the real discriminator answer is
unchanged -- this is instrumentation, not a stub of an acceptance target;
`_citation_or_xref_context`/`_is_citation_or_xref_context` themselves are
called live, unpatched) and records the `(pos, endpos)` window each probe
actually used. It then asserts the window size (`endpos - pos`) stays
bounded by a small constant REGARDLESS of how far into the document the
token sits, and does not grow between a near token and a far token in the
same body. Today `pos` is always `0`, so the window equals `trimmed_end`
itself -- this must and does fail below. A Developer fix that bounds the
lookback (e.g. `search(body, max(0, trimmed_end - WINDOW), trimmed_end)`)
makes both assertions pass without touching what the discriminator decides.

**Self-mock ban compliance:** the five suffix-regex objects
(`_STRUCTURAL_UNIT_WORD_SUFFIX_RE` etc.) are NOT acceptance targets --
`_citation_or_xref_context`, `_is_citation_or_xref_context`, and
`resolve_unit_path` are (per the sprint brief) -- and none of those three is
patched, stubbed, or reimplemented anywhere in this file.

**Bound choice:** 4096 characters. Every real branch's own match span is
short (the longest, a full federal cite like `"47 United States Code,
Section 522(13)"`, is well under 100 chars); 4096 gives roughly 40x headroom
over that so any reasonable bounded-lookback implementation clears it
easily, while staying many orders of magnitude below the 100,000+ character
positions this test probes -- so it cannot pass by accident today.
"""

from __future__ import annotations

from app.definition_links import us_profile

_SUFFIX_RE_NAMES = (
    "_STRUCTURAL_UNIT_WORD_SUFFIX_RE",
    "_FULL_USC_CITATION_SUFFIX_RE",
    "_SECTION_CITATION_SUFFIX_RE",
    "_LONE_SECTION_CITATION_SUFFIX_RE",
    "_BARE_STATE_CODE_CITATION_SUFFIX_RE",
)

# Generous headroom over the longest real branch match (see module
# docstring); the probed positions below are 40x+ larger than this.
_MAX_SANE_WINDOW = 4096

# Plain lowercase filler with no digits, no structural-unit words, no "§",
# no "U.S.C.", and no ALL-CAPS runs -- guaranteed not to accidentally
# satisfy any of the five suffix regexes, so every probe genuinely scans
# to the left edge of its search window before giving up (the pathology
# this test targets).
_FILLER = "lorem ipsum dolor sit amet consectetur adipiscing elit "


def _safe_body(min_length: int) -> str:
    body = _FILLER * (min_length // len(_FILLER) + 1)
    return body[:min_length] + "(A) "


class _WindowRecorder:
    """Forwards to the real compiled pattern's `.search` -- the match
    decision is untouched -- while recording the `(pos, endpos)` args."""

    def __init__(self, pattern):
        self._pattern = pattern
        self.windows: list[tuple[int, int]] = []

    def search(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.search(string, pos, endpos)

    def match(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.match(string, pos, endpos)

    def fullmatch(self, string, pos=0, endpos=None):
        if endpos is None:
            endpos = len(string)
        self.windows.append((pos, endpos))
        return self._pattern.fullmatch(string, pos, endpos)


def _recorded_windows(body: str, token_start: int) -> list[tuple[int, int]]:
    """Call the REAL, unpatched `_citation_or_xref_context` for `token_start`
    in `body`, returning every `(pos, endpos)` window its suffix probes
    used."""
    originals = {name: getattr(us_profile, name) for name in _SUFFIX_RE_NAMES}
    recorders = {name: _WindowRecorder(pattern) for name, pattern in originals.items()}
    for name, recorder in recorders.items():
        setattr(us_profile, name, recorder)
    try:
        us_profile._citation_or_xref_context(body, token_start)
    finally:
        for name, pattern in originals.items():
            setattr(us_profile, name, pattern)
    return [window for recorder in recorders.values() for window in recorder.windows]


def test_citation_or_xref_context_probe_window_does_not_scale_with_token_position():
    """A token 175,000+ characters into a body with no matchable citation/
    structural-word context anywhere must not cause any suffix probe to
    search a window wider than `_MAX_SANE_WINDOW`. Today it does: `pos` is
    always `0`, so the window equals the full `trimmed_end` (~175,000+),
    thousands of times over budget."""
    body = _safe_body(177_600)
    token_start = len(body) - 4  # the trailing "(A) " token's "(" position

    windows = _recorded_windows(body, token_start)

    assert windows, "expected at least one suffix-regex probe to run"
    oversized = [w for w in windows if (w[1] - w[0]) > _MAX_SANE_WINDOW]
    assert not oversized, (
        f"G4 discriminator probe window scales with document position: "
        f"{len(oversized)} of {len(windows)} probe(s) searched a window wider "
        f"than {_MAX_SANE_WINDOW} chars (largest window={max(w[1] - w[0] for w in windows)}) "
        f"for a token at position {token_start} -- the lookback is unbounded."
    )


def test_citation_or_xref_context_probe_window_does_not_grow_between_a_near_and_far_token():
    """Same body, two token positions far apart (~10,000 vs ~170,000). If the
    lookback is truly bounded, the window recorded at the far position must
    not be meaningfully larger than at the near position -- proving the
    property is position-INDEPENDENCE, not merely 'small in one sample'.
    Today the far window is ~17x the near window (both equal their own
    `trimmed_end`), which this test rejects."""
    body = _safe_body(177_600)
    near_start = 10_000
    far_start = len(body) - 4

    near_windows = _recorded_windows(body, near_start)
    far_windows = _recorded_windows(body, far_start)

    assert near_windows, "expected at least one suffix-regex probe to run at near position"
    assert far_windows, "expected at least one suffix-regex probe to run at far position"

    near_max = max((w[1] - w[0] for w in near_windows), default=0)
    far_max = max((w[1] - w[0] for w in far_windows), default=0)

    assert far_max <= near_max + _MAX_SANE_WINDOW, (
        f"G4 discriminator probe window grows with document position: "
        f"near_start={near_start} -> max_window={near_max}; "
        f"far_start={far_start} -> max_window={far_max} -- a bounded lookback "
        f"would keep these within {_MAX_SANE_WINDOW} chars of each other."
    )
