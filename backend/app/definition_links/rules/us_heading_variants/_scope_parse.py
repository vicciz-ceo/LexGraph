"""Cycle 5, item 14 -- pure, heading-text-only scope-VALUE extraction for
the two U2 rows measured as containment-mechanism-ready:
`chapter_range_scope_bounds` (AK's chapter-RANGE heading) and
`enumerated_local_scope_targets` (KY's enumerated-LOCAL heading). See
`test_definition_links_us_heading_variants_cycle5_scope_parse.py`'s module
docstring for the full behavioral spec, and the Planner's report for the
reported core-seam gap this deliberately does NOT attempt to close (no
`us_profile.determine_scope`/shared-module wiring -- out of this panel's
U3 write-set).
"""

from __future__ import annotations

import re

from app.definition_links.rules.us_heading_variants._shared import normalize_mojibake

_CHAPTER_NUM_RE = r"\d+(?:\.\d+)?"

# AK's own real drafting convention: "[General] definitions for AS X
# [dash] AS Y[.]" -- tolerant of the mojibake em-dash (normalized upstream
# by `normalize_mojibake`) as well as a real hyphen/en-dash/em-dash.
_CHAPTER_RANGE_RE = re.compile(
    rf"\bdefinitions?\s+for\s+AS\s+({_CHAPTER_NUM_RE})\s*[-–—]\s*AS\s+({_CHAPTER_NUM_RE})",
    re.IGNORECASE,
)


def chapter_range_scope_bounds(heading: str) -> tuple[str, str] | None:
    """Bare `(X, Y)` boundary strings, no "AS " prefix, no trailing
    punctuation. `None` for any heading not matching this shape."""
    m = _CHAPTER_RANGE_RE.search(normalize_mojibake(heading))
    return (m.group(1), m.group(2)) if m else None


# KY's own real drafting convention: "Definition[s] for section [and KRS N
# [and KRS M ...]]".
_LOCAL_SCOPE_TRIGGER_RE = re.compile(r"\bdefinitions?\s+for\s+section\b", re.IGNORECASE)
_ADDITIONAL_KRS_TARGET_RE = re.compile(r"\s+and\s+KRS\s+(\d+(?:\.\d+)?)", re.IGNORECASE)


def enumerated_local_scope_targets(heading: str) -> tuple[str, ...] | None:
    """A tuple of every ADDITIONAL article/section number named alongside
    the "for section" trigger via "and KRS N" -- empty tuple `()` when the
    heading says "for section" with no additional named target. `None`
    (not `()`) when the trigger phrase is absent entirely, so callers can
    distinguish "declares no extra scope members" from "isn't this
    shape"."""
    heading = normalize_mojibake(heading)
    m = _LOCAL_SCOPE_TRIGGER_RE.search(heading)
    if not m:
        return None
    targets: list[str] = []
    pos = m.end()
    while True:
        m2 = _ADDITIONAL_KRS_TARGET_RE.match(heading, pos)
        if not m2:
            break
        targets.append(m2.group(1))
        pos = m2.end()
    return tuple(targets)
