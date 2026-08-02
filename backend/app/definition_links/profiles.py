"""Jurisdiction-profile seam (sprint 2026-08-02-us-state-law, director
decision #1, item 2, gate G1).

An ADDITIVE registry layer, NOT a rename/relocation of the existing
bare module-level functions in `sections.py`/`normalize.py`/`matcher.py`/
`derivation.py`. Those functions are imported directly by name across
~20 existing unit/integration test files and must keep working exactly
as they are (ruling R2) -- `HebrewProfile` (the `"IL"` profile) is a
THIN WRAPPER that delegates to those exact, unchanged functions.

Minimum surface a `JurisdictionProfile` exposes (mirrors the director's
own wording: "sections/matcher/derivation/normalize rules live" behind
the profile):

    .code: str
    .is_definitions_heading(heading: str) -> bool
    .normalize_for_parsing(text: str) -> str
    .find_term_uses(term: str, text: str) -> list[re.Match[str]]
    .detect_cross_law_derivations(text, *, source_term,
        known_law_titles=None) -> list

Each keeps the SAME parameter names/order/defaults as the module-level
function it wraps -- a drop-in replacement at a pipeline call site, not
a redesigned API.

Deliberately OUT of scope for this item: `guards.is_bidi_degraded` and
`extract.py`'s functions (RTL-bidi guarding and definition-block
extraction stay Hebrew-only/shared for this sprint), and any non-`"IL"`
profile (the US profile is a later item in this sprint, registered
separately once its module exists).
"""

from __future__ import annotations

import re
from typing import Protocol

from app.definition_links import derivation, matcher, normalize, sections


class JurisdictionProfile(Protocol):
    """Structural interface every registered profile satisfies."""

    code: str

    def is_definitions_heading(self, heading: str) -> bool: ...

    def normalize_for_parsing(self, text: str) -> str: ...

    def find_term_uses(self, term: str, text: str) -> list[re.Match[str]]: ...

    def detect_cross_law_derivations(
        self,
        text: str,
        *,
        source_term: str,
        known_law_titles: dict[str, str] | None = None,
    ) -> list: ...


class HebrewProfile:
    """The `"IL"` profile -- thin-wraps the existing, unchanged Hebrew
    module-level functions. No behavior of its own; every method is a
    straight pass-through so this profile is provably identical to
    calling `sections`/`normalize`/`matcher`/`derivation` directly.
    """

    code = "IL"

    def is_definitions_heading(self, heading: str) -> bool:
        return sections.is_definitions_heading(heading)

    def normalize_for_parsing(self, text: str) -> str:
        return normalize.normalize_for_parsing(text)

    def find_term_uses(self, term: str, text: str) -> list[re.Match[str]]:
        return matcher.find_term_uses(term, text)

    def detect_cross_law_derivations(
        self,
        text: str,
        *,
        source_term: str,
        known_law_titles: dict[str, str] | None = None,
    ) -> list:
        return derivation.detect_cross_law_derivations(
            text, source_term=source_term, known_law_titles=known_law_titles
        )


# Registered profiles, keyed by jurisdiction code. Only `"IL"` is
# registered by this item -- the US profile is added by a later item in
# this sprint, in its own module, via this same registry.
_REGISTRY: dict[str, JurisdictionProfile] = {
    "IL": HebrewProfile(),
}


def get_profile(code: str) -> JurisdictionProfile:
    """Look up the registered profile for `code`.

    Raises `ValueError` for a code with no registered profile -- never a
    fabricated fallback (matches this codebase's existing "no fabricated
    guess" discipline, e.g. `guards.resolve_law_title`).
    """
    try:
        return _REGISTRY[code]
    except KeyError:
        raise ValueError(f"No jurisdiction profile registered for code {code!r}") from None
