"""Rule: `בפרט זה -` ("for this item") item-scoped `::-` double-colon
nested-list definitions (sprint 2026-08-04-defs-il, program
2026-08-04-definition-completeness, item 9; a SIXTH missed class,
program manager ruling P-E3).

Unlike classes (a)/(b)/(c)/(paragraph), this is not a single-line
`TRIGGER, "term" - definition` sentence -- it is a PREAMBLE line ending
`בפרט זה -` (no quoted term of its own) followed by N separate `::-`-
marked entry lines, each its own `"term" - definition;` pair, exactly
like class (d)'s `::-` sub-shape but reached via the WIRED
`extract_local_scope_definitions` path (this trigger lives inside an
ORDINARY, non-הגדרות-headed article body -- reachable today only because
core's bare-`@` parser fix, M8(a), lets such an article's body be scanned
at all).

Detection: a line whose stripped text ends with `בפרט זה -` opens the
list; every immediately-following line that is either blank or `::-`-
marked is consumed (blank lines are skipped, not treated as the end of
the list); the first line that is neither ends the list. Each `::-`-
marked line is parsed with the same `"term" - definition` grammar as
every other quote-dash entry in this codebase.

Stamps the NEW generic kind `scope="item"` (below-article granularity,
per seam v2.4's `UnitPath` model -- a פרט/item sits BELOW the article,
like a paragraph, not above it like chapter/siman/chelek). `scope_value`
is best-effort `None` -- not required by this sprint's RED test.

CAPTURE ONLY -- same open containment question as the paragraph-scoped
class (escalation E7): `resolve_unit_path`'s only recognized IL
below-article marker (`סעיף קטן (X)`) does not occur anywhere in this
fixture's own numbered/colon-indented list convention.
"""

from __future__ import annotations

import re

from app.definition_links.extract import DefinitionCandidate
from app.definition_links.rules.registry import (
    RuleContext,
    ScopeTriggerRule,
    register_scope_trigger_rule,
)

_PREAMBLE_RE = re.compile(r"בפרט זה\s*-\s*$")
_ENTRY_LINE_RE = re.compile(r"^\s*::-\s*(.*)$")
_TERM_DASH_RE = re.compile(r'^"([^"]+)"\s*-\s*(.*)$')


def _extract(article_body: str, ctx: RuleContext) -> list[DefinitionCandidate]:
    lines = article_body.split("\n")
    n = len(lines)
    results: list[DefinitionCandidate] = []
    i = 0
    while i < n:
        if not _PREAMBLE_RE.search(lines[i].rstrip()):
            i += 1
            continue
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            entry_match = _ENTRY_LINE_RE.match(line)
            if not entry_match:
                break
            term_match = _TERM_DASH_RE.match(entry_match.group(1).strip())
            if term_match:
                term = term_match.group(1).strip()
                definition_text = term_match.group(2).strip().rstrip(";").strip()
                results.append(
                    DefinitionCandidate(
                        terms=(term,),
                        definition_text=definition_text,
                        scope="item",
                        scope_value=None,
                    )
                )
            i += 1
    return results


register_scope_trigger_rule(ScopeTriggerRule(jurisdiction_codes=("IL",), extract=_extract))
