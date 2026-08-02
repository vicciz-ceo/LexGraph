"""Jurisdiction-profile seam (sprint 2026-08-02-us-state-law, director
decision #1, item 2, gate G1; extended by item 3, gates G2-G4, to register
the `"US-*"`/`"US-FED"` profile family).

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

Item 3 (gates G2-G4) extends the Protocol with two more methods, needed
because the US profile has capabilities the Hebrew engine doesn't:

    .find_citations(text: str) -> list[str]
    .extract_definitions_from_section(text, *, scope) -> list[DefinitionCandidate]

`HebrewProfile` implements both WITHOUT changing any Hebrew behavior:
`find_citations` trivially returns `[]` (no citation grammar in scope for
Hebrew this sprint) and `extract_definitions_from_section` delegates to
the existing, unchanged `extract.extract_definitions_from_section`.

Deliberately OUT of scope for this item: `guards.is_bidi_degraded` (RTL-
bidi guarding stays Hebrew-only for this sprint).
"""

from __future__ import annotations

import re
from typing import Protocol

from app.definition_links import derivation, extract, matcher, normalize, sections
from app.definition_links.extract import DefinitionCandidate
from app.definition_links.us_profile import USProfile
from app.services.jurisdiction import JURISDICTION_CODES


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

    def find_citations(self, text: str) -> list[str]: ...

    def extract_definitions_from_section(
        self, text: str, *, scope: str
    ) -> list[DefinitionCandidate]: ...


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

    def find_citations(self, text: str) -> list[str]:
        # No citation grammar in scope for Hebrew this sprint (item 3's
        # docstring/README companion assertion) -- trivially empty.
        return []

    def extract_definitions_from_section(
        self, text: str, *, scope: str
    ) -> list[DefinitionCandidate]:
        return extract.extract_definitions_from_section(text, scope=scope)


# Registered profiles, keyed by jurisdiction code. `"IL"` is the Hebrew
# profile (item 2); every other code in `JURISDICTION_CODES`
# (`US-<postal>`, `US-DC`, `US-PR`, `US-FED`) shares ONE `USProfile`
# instance per code (item 3 -- see `us_profile.py`'s module docstring for
# why a single US-family profile serves all 53 non-`"IL"` codes rather than
# a per-state profile).
_REGISTRY: dict[str, JurisdictionProfile] = {"IL": HebrewProfile()}
_REGISTRY.update(
    {code: USProfile(code=code) for code in JURISDICTION_CODES if code != "IL"}
)


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
