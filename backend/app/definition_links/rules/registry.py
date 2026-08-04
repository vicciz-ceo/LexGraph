"""Per-jurisdiction rule registry (sprint 2026-08-04-defs-core-scope, gate
C4) -- the dataclasses and `register_*`/`*_for` functions that let a family
panel ship a new convention as a NEW MODULE in this package, with zero edits
to any shared file (`pipeline.py`, `matcher.py`, `profiles.py`, `extract.py`).

Shape pinned by `backend/tests/unit/test_definition_links_rules_registry.py`
against the sprint contract's `## Seam spec (published)` section, FINAL as
of v2.3 (v1's 4-tier scope enum and v2's `ScopeUnit`/hand-registered rank
were both superseded during Stage B by v2.2's unified `UnitPath` model --
this module targets v2.3, not the intermediate designs). In particular,
v2.2 WITHDRAWS v2's `register_scope_unit_kind`/`rank_for` pair entirely:
specificity is path length (`len(UnitPath)`), never a hand-registered
integer -- neither name is defined anywhere in this module, deliberately
(pinned by `test_rank_for_and_register_scope_unit_kind_no_longer_exist`).

Seven rule kinds, one frozen dataclass each, all with a
`jurisdiction_codes: tuple[str, ...]` field plus one kind-specific
callable: `HeadingRule`, `BodyPreambleRule`, `EntrySplitterRule`,
`TermClauseRule`, `ScopeTriggerRule`, `StructuralUnitRule` (v2.1/v2.2 M11),
and `CitationRule` (v2.3 M12). `jurisdiction_codes` matching (seam spec
Seam 2): an exact `app.services.jurisdiction.JURISDICTION_CODES` entry, or
the literal wildcard `"US-*"`, meaning every code with that prefix -- never
matches `"IL"`. No other wildcard form exists.

This module owns registration/lookup only. Consuming a kind's registered
rules (baseline-first-then-union/first-wins dispatch order, per kind) is
`profiles.py`'s job (seam spec Seam 1/2's "Consumption contract"), not
this module's -- a family panel's rule module only ever calls a
`register_*` function here at its own import time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.definition_links.extract import DefinitionCandidate

# --- Unit path (v2.2) -- replaces v1's `Subsection` and v2's `ScopeUnit` ---


@dataclass(frozen=True)
class UnitStep:
    """One step in a `UnitPath` -- a label/value pair, e.g.
    `UnitStep(kind="chapter", value="12")`. `kind` is a provenance/display
    label only (v2.2): it no longer drives ranking -- specificity is path
    length, compared by callers via plain `len(path)`.
    """

    kind: str
    value: str


# Root-to-leaf, ordered. `()` is the law-wide path -- a prefix of every
# path, for free, no special case needed by a comparing caller.
UnitPath = tuple[UnitStep, ...]


# --- Context objects (M5, M11) -- passed to a rule's callable instead of
# bare positional args, so future context growth is additive. ------------


@dataclass(frozen=True)
class RuleContext:
    """Passed to a `ScopeTriggerRule.extract` call (M5). `unit_path` is the
    v2.2 shape (replaces v2's `structural_units` field of the same role)."""

    article_number: str
    chapter: str | None
    unit_path: UnitPath


@dataclass(frozen=True)
class StructuralContext:
    """Passed to a `StructuralUnitRule.derive` call (M11). `heading_breadcrumbs`
    is an ordered `(depth, heading_text)` sequence -- see the seam spec's
    input-availability note for what each jurisdiction can populate here."""

    article_number: str
    heading_breadcrumbs: tuple[tuple[int, str], ...]


# --- The seven rule kinds -------------------------------------------------


@dataclass(frozen=True)
class HeadingRule:
    """Detection kind, first-positive-wins (tried only after the profile's
    own baseline heading detector returns false)."""

    jurisdiction_codes: tuple[str, ...]
    matches: Callable[[str], bool]


@dataclass(frozen=True)
class BodyPreambleRule:
    """Detection kind, first-non-None-wins, filename-sort order (tried
    after the profile's own baseline/legacy placeholder-heading logic)."""

    jurisdiction_codes: tuple[str, ...]
    derive_heading: Callable[[str], str | None]


@dataclass(frozen=True)
class EntrySplitterRule:
    """Union kind (M1 -- moved off the first-wins side): every matching
    splitter's blocks are kept, deduped downstream by the existing
    `(article_id, sorted(terms))` key."""

    jurisdiction_codes: tuple[str, ...]
    split: Callable[[str], list[str]]


@dataclass(frozen=True)
class TermClauseRule:
    """Union kind: every matching rule's candidates are kept for a given
    entry block."""

    jurisdiction_codes: tuple[str, ...]
    parse: Callable[[str], list[DefinitionCandidate]]


@dataclass(frozen=True)
class ScopeTriggerRule:
    """Union kind: every matching rule's candidates are kept (zero-miss --
    rules never suppress each other). `extract` receives a `RuleContext`
    (M5), not bare positional args."""

    jurisdiction_codes: tuple[str, ...]
    extract: Callable[[str, RuleContext], list[DefinitionCandidate]]


@dataclass(frozen=True)
class StructuralUnitRule:
    """Union kind (M11/v2.2) -- derives (part of) an article's `UnitPath`.
    A document legitimately nests inside more than one structural axis at
    once, so every matching rule's contribution is additive."""

    jurisdiction_codes: tuple[str, ...]
    derive: Callable[[StructuralContext], UnitPath]


@dataclass(frozen=True)
class CitationRule:
    """Union kind (v2.3 M12) -- `find_citations` becomes rule-extensible.
    The KIND only: this module registers/looks these up, it implements no
    citation behavior and `us_profile.find_citations` is unchanged by this
    sprint's I4 work."""

    jurisdiction_codes: tuple[str, ...]
    find: Callable[[str], list[str]]


# --- Registration + lookup, one pair per kind -----------------------------


def _matches(jurisdiction_codes: tuple[str, ...], code: str) -> bool:
    """Exact-code match, or the `"US-*"` wildcard matching any `"US-"`-
    prefixed code. No other wildcard form -- `"US-*"` never matches `"IL"`."""
    if code in jurisdiction_codes:
        return True
    return "US-*" in jurisdiction_codes and code.startswith("US-")


_heading_rules: list[HeadingRule] = []
_body_preamble_rules: list[BodyPreambleRule] = []
_entry_splitter_rules: list[EntrySplitterRule] = []
_term_clause_rules: list[TermClauseRule] = []
_scope_trigger_rules: list[ScopeTriggerRule] = []
_structural_unit_rules: list[StructuralUnitRule] = []
_citation_rules: list[CitationRule] = []


def register_heading_rule(rule: HeadingRule) -> None:
    _heading_rules.append(rule)


def heading_rules_for(code: str) -> list[HeadingRule]:
    return [r for r in _heading_rules if _matches(r.jurisdiction_codes, code)]


def register_body_preamble_rule(rule: BodyPreambleRule) -> None:
    _body_preamble_rules.append(rule)


def body_preamble_rules_for(code: str) -> list[BodyPreambleRule]:
    return [r for r in _body_preamble_rules if _matches(r.jurisdiction_codes, code)]


def register_entry_splitter_rule(rule: EntrySplitterRule) -> None:
    _entry_splitter_rules.append(rule)


def entry_splitter_rules_for(code: str) -> list[EntrySplitterRule]:
    return [r for r in _entry_splitter_rules if _matches(r.jurisdiction_codes, code)]


def register_term_clause_rule(rule: TermClauseRule) -> None:
    _term_clause_rules.append(rule)


def term_clause_rules_for(code: str) -> list[TermClauseRule]:
    return [r for r in _term_clause_rules if _matches(r.jurisdiction_codes, code)]


def register_scope_trigger_rule(rule: ScopeTriggerRule) -> None:
    _scope_trigger_rules.append(rule)


def scope_trigger_rules_for(code: str) -> list[ScopeTriggerRule]:
    return [r for r in _scope_trigger_rules if _matches(r.jurisdiction_codes, code)]


def register_structural_unit_rule(rule: StructuralUnitRule) -> None:
    _structural_unit_rules.append(rule)


def structural_unit_rules_for(code: str) -> list[StructuralUnitRule]:
    return [r for r in _structural_unit_rules if _matches(r.jurisdiction_codes, code)]


def register_citation_rule(rule: CitationRule) -> None:
    _citation_rules.append(rule)


def citation_rules_for(code: str) -> list[CitationRule]:
    return [r for r in _citation_rules if _matches(r.jurisdiction_codes, code)]
