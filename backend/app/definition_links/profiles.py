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

# Importing the `rules` package triggers its own auto-discovery (sprint
# 2026-08-04-defs-core-scope, gate C4): every sibling module inside it
# (core-authored `il_scope_triggers.py`/`us_scope_trigger_proof.py`, plus
# whatever family panels add) self-registers its own rule(s) at ITS OWN
# import time. `profiles.py` is imported by essentially everything that
# touches definition-linking (`get_profile` is the universal entry
# point), so this is the one place that reliably fires the registration
# side effect before any profile method that consumes the registry runs.
from app.definition_links.rules import registry
from app.definition_links.us_profile import USProfile
from app.services.jurisdiction import JURISDICTION_CODES

# Sprint 2026-08-04-defs-core-scope, gate C2/C3: moved verbatim out of
# pipeline.py's `_CHAPTER_SCOPE_TRIGGERS` -- a הגדרות section is chapter-
# scoped only when its own opening line explicitly restricts it (e.g.
# "לענין עבירה -", "בסימן זה -"); otherwise it defaults to law-wide, even
# when the section itself happens to sit under a `==` chapter heading.
# Lives here (not pipeline.py) so C3's "pipeline.py retains no
# jurisdiction-specific literals" guard is satisfied by construction --
# this module already hosts `HebrewProfile`'s other Hebrew-aware behavior.
_IL_CHAPTER_SCOPE_TRIGGERS = (
    "לענין פרק זה",
    "לענין סימן זה",
    "לענין עבירה",
    "בפרק זה",
    "בסימן זה",
)

# Sprint 2026-08-04-defs-core-scope, seam spec v2.2/v2.4 -- IL's own
# sub-article marker: "סעיף קטן (<letter>)" ("subsection (X)"). Exact
# marker regex per profile is this sprint's own Stage B work (the seam
# spec's own words) -- IL's convention is a single, non-nested lettered
# marker (no federal-style multi-level ladder observed in the Hebrew
# corpus), so `resolve_unit_path` here returns at most ONE step deep.
_IL_SUBSECTION_MARKER_RE = re.compile(r"סעיף\s+קטן\s+\(([א-ת]+)\)")


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
        self, text: str, *, scope: str, heading_was_derived: bool = False
    ) -> list[DefinitionCandidate]: ...

    # --- Sprint 2026-08-04-defs-core-scope (gates C1-C3, seam spec) -----

    main_unit_kind: str

    def determine_scope(self, body_text: str) -> str: ...

    def extract_local_scope_definitions(
        self, article_body: str, *, article_number: str, chapter: str | None = None
    ) -> list[DefinitionCandidate]: ...

    def derive_heading_from_body(self, heading: str, body: str) -> str | None: ...

    def resolve_unit_path(self, article, char_offset: int | None = None): ...


class HebrewProfile:
    """The `"IL"` profile -- thin-wraps the existing, unchanged Hebrew
    module-level functions. No behavior of its own; every method is a
    straight pass-through so this profile is provably identical to
    calling `sections`/`normalize`/`matcher`/`derivation` directly.
    """

    code = "IL"
    # Sprint 2026-08-04-defs-core-scope, seam spec v2.4 §4 -- dossier
    # basis: "Main unit: סעיף (article)", matching TODAY's `"local"`
    # granularity exactly (C5: zero behavior change).
    main_unit_kind = "local"

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
        # No baseline citation grammar in scope for Hebrew this sprint
        # (item 3's docstring/README companion assertion) -- trivially
        # empty UNLESS an IL `CitationRule` is registered (v2.3 M12; none
        # is today, so this stays byte-identical to `[]`, C5-safe).
        results: list[tuple[int, str]] = []
        claimed: list[tuple[int, int]] = []
        for rule in registry.citation_rules_for(self.code):
            for citation in rule.find(text):
                idx = text.find(citation)
                if idx == -1:
                    continue
                span = (idx, idx + len(citation))
                if any(not (span[1] <= s or e <= span[0]) for s, e in claimed):
                    continue
                claimed.append(span)
                results.append((idx, citation))
        results.sort(key=lambda item: item[0])
        return [citation for _, citation in results]

    def extract_definitions_from_section(
        self, text: str, *, scope: str, heading_was_derived: bool = False
    ) -> list[DefinitionCandidate]:
        # `heading_was_derived` is a US-only fallback-chain gate (wave 6
        # placeholder-heading jurisdictions); IL has no such concept
        # (`derive_heading_from_body` below is trivially always `None`),
        # so this kwarg is accepted for Protocol-shape parity and simply
        # ignored -- behavior is IDENTICAL whether or not it is passed.
        return extract.extract_definitions_from_section(text, scope=scope)

    # --- Sprint 2026-08-04-defs-core-scope (gates C1-C3, seam spec) -----

    def determine_scope(self, body_text: str) -> str:
        """Replaces the free function `pipeline._determine_scope` -- same
        2-way contract (`"chapter"` / `"law-wide"`), IL's own trigger
        phrases byte-identical to today (C5)."""
        first_line = next((ln for ln in body_text.splitlines() if ln.strip()), "")
        if any(trigger in first_line for trigger in _IL_CHAPTER_SCOPE_TRIGGERS):
            return "chapter"
        return "law-wide"

    def extract_local_scope_definitions(
        self, article_body: str, *, article_number: str, chapter: str | None = None
    ) -> list[DefinitionCandidate]:
        """Replaces pipeline.py's direct calls to `extract.
        extract_local_definitions`/`extract_adhoc_definitions` -- reaches
        the SAME two functions, now via 2 pre-registered IL
        `ScopeTriggerRule`s (`rules/il_scope_triggers.py`) instead of a
        direct call, byte-identical behavior (C5). A rule that leaves
        `.source_article_number` unset (both IL rules always do -- they
        are inherently "local to the CURRENT article") gets it defaulted
        here to `article_number`, matching what pipeline.py used to stamp
        manually right after extraction.
        """
        ctx = registry.RuleContext(article_number=article_number, chapter=chapter, unit_path=())
        candidates: list[DefinitionCandidate] = []
        for rule in registry.scope_trigger_rules_for(self.code):
            for candidate in rule.extract(article_body, ctx):
                if candidate.source_article_number is None:
                    candidate.source_article_number = article_number
                candidates.append(candidate)
        return candidates

    def derive_heading_from_body(self, heading: str, body: str) -> str | None:
        """IL has no placeholder-heading concept (that is a US CA/IL
        [state]/GA-only wave-6 shape) -- always `None`, never invent a
        heading from Hebrew body text."""
        return None

    def resolve_unit_path(self, article, char_offset: int | None = None):
        """`char_offset=None` returns `()` (the article's own base path
        -- v2.4: `UnitPath` is BELOW-article only). Given an offset,
        returns the path to the nearest preceding `סעיף קטן (X)` marker
        that fully precedes it -- at most one step deep (IL's observed
        convention has no deeper nesting)."""
        if char_offset is None:
            return ()
        last_value: str | None = None
        for match in _IL_SUBSECTION_MARKER_RE.finditer(article.body):
            if match.end() <= char_offset:
                last_value = match.group(1)
            else:
                break
        if last_value is None:
            return ()
        return (registry.UnitStep(kind="subsection", value=last_value),)


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
