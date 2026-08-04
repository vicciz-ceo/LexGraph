"""Stage 2 -- extract (term, definition) pairs (sprint
2026-07-29-definition-links, item DL4).

Inputs to every function here are ALREADY Stage 0/1 output (normalized,
wikilink-brackets-already-stripped-to-display-text plain text for one
section/article body) -- this module does no normalization or wikilink
handling of its own. See the review doc's "Deterministic definition-linking
design" Stage 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A top-level definition entry starts with `:-`. Continuation/list-item
# lines (`::`, or plain continuation text) belong to the current entry
# until the next `:-` line.
_ENTRY_START_RE = re.compile(r"^\s*:-\s?")

# Nested sub-definition marker (Stage 2's recursive case): `לעניין הגדרה
# זו, "X" - ...` appearing inside another definition's own body.
_NESTED_MARKER_RE = re.compile(r"לעניין הגדרה זו,\s*")

# `לענין זה,` / `בסעיף זה,` immediately preceding a quoted-term-dash
# definition (Stage 2's local-scoped-inside-an-ordinary-article case).
# Ends at end-of-line (these entries end with `.`, not `;`).
_LOCAL_TRIGGER_RE = re.compile(
    r'(?:לענין זה|בסעיף זה),\s*"([^"]+)"\s*-\s*(.*)$', re.MULTILINE
)

# Unquoted ad-hoc apposition definition: `(להלן - X)` / `(להלן: X)`.
_ADHOC_RE = re.compile(r"\(\s*להלן\s*[-:]\s*([^)]+?)\s*\)")

_QUOTE_RE = re.compile(r'"([^"]+)"')

# DL12 (cycle 2, G6, ruling M9(b)): a definitions-entry body that is SOLELY a
# parenthesized Knesset repeal/deletion marker (poc-run.md §8 Issue 2), e.g.
# `(((נמחקה);))`. Corpus-observed inflections (נמחקה/נמחק/נמחקו/בוטלה/בוטל/
# בוטלו) wrapped in exactly the corpus-observed punctuation variants
# (`);))`, `).))`, `)))`) -- anchored to the WHOLE body so a body that merely
# mentions one of these words as substantive prose is never blocked.
_REPEAL_MARKER_RE = re.compile(
    r"^\(\(\((?:נמחקה|נמחקו|נמחק|בוטלה|בוטלו|בוטל)\)[;.]?\)\)$"
)


def _is_pure_repeal_marker(body_text: str) -> bool:
    return bool(_REPEAL_MARKER_RE.match(body_text.strip()))


@dataclass
class DefinitionCandidate:
    """Stage 2's output shape -- one extracted (term(s), definition) pair.

    `.source_article_number` / `.source_chapter` are provenance fields left
    `None` here (a single section/article body has no way to know its own
    article number or chapter) -- `pipeline.py` fills them in before
    handing candidates to `matcher.link_articles_to_definitions`.
    """

    terms: tuple[str, ...]
    definition_text: str
    scope: str
    qualifier: str | None = None
    parent_term: str | None = None
    # `str | tuple[str, ...] | None`: sprint 2026-08-04-defs-core-scope
    # (seam v2.1, M9) widens these two legacy fields to also accept an
    # enumerated/ranged tuple of values (a definition scoped to more than
    # one article/chapter), not just one scalar -- existing callers
    # passing a bare string are completely unaffected.
    source_article_number: str | tuple[str, ...] | None = None
    source_chapter: str | tuple[str, ...] | None = None
    # NEW (seam v2, M4): the generic value field every scope kind OTHER
    # than the two legacy ones above (chapter/local) uses -- e.g.
    # "subsection" (v1), or any new kind a family panel registers
    # (part/siman/...). May also be a tuple for an enumerated value.
    scope_value: str | tuple[str, ...] | None = None
    # NEW (sprint 2026-08-04-defs-core-dispatch, items I9/I10/I11, manager
    # ruling M-D3, seam v2.7): additive, optional LEVEL narrowing for a
    # `scope="subsection"` definition -- names which `UnitStep.kind` (e.g.
    # `"digit"`, `"lower_alpha"`, `"upper_alpha"`) `scope_value` is meant
    # to be compared against, so `matcher._subsection_contains_offset` can
    # find that step in a mention's `UnitPath` instead of always comparing
    # the OUTERMOST step regardless of what level the rule actually meant.
    # `None` (the default) preserves today's outermost-step-comparison
    # fallback unchanged -- every existing caller/candidate is unaffected.
    scope_unit_kind: str | None = None


def _parse_terms_and_qualifier(header_prefix: str) -> tuple[list[str], str | None]:
    matches = list(_QUOTE_RE.finditer(header_prefix))
    terms = [m.group(1) for m in matches]
    if not matches:
        return [], None
    leftover = header_prefix[matches[-1].end() :]
    cleaned = re.sub(r"^[\s,]+", "", leftover).strip()
    qualifier = cleaned if cleaned and cleaned != "ו" else None
    return terms, qualifier


def _find_split_dash(line: str) -> int:
    """Return the index of the first standalone `-` outside any quoted
    span (preceded and followed by whitespace/start/end-of-string), or -1
    if none is found."""
    in_quote = False
    n = len(line)
    for i, ch in enumerate(line):
        if ch == '"':
            in_quote = not in_quote
        elif ch == "-" and not in_quote:
            before_ok = i == 0 or line[i - 1].isspace()
            after_ok = i == n - 1 or line[i + 1].isspace()
            if before_ok and after_ok:
                return i
    return -1


def _split_into_blocks(text: str) -> list[str]:
    lines = text.split("\n")
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if _ENTRY_START_RE.match(line):
            if current is not None:
                blocks.append(current)
            stripped_line = _ENTRY_START_RE.sub("", line, count=1)
            current = [stripped_line]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)
    return ["\n".join(b) for b in blocks]


def _parse_block(
    block_text: str, *, scope: str, parent_term: str | None
) -> list[DefinitionCandidate]:
    lines = block_text.split("\n")
    first_line = lines[0]
    rest_lines = lines[1:]

    dash_idx = _find_split_dash(first_line)
    if dash_idx == -1:
        return []

    header_prefix = first_line[:dash_idx].rstrip()
    first_line_tail = first_line[dash_idx + 1 :].lstrip()

    terms, qualifier = _parse_terms_and_qualifier(header_prefix)
    if not terms:
        return []

    body_lines = ([first_line_tail] if first_line_tail else []) + rest_lines
    body_text = "\n".join(body_lines).strip()

    nested_match = _NESTED_MARKER_RE.search(body_text)
    if nested_match:
        own_body = body_text[: nested_match.start()].rstrip()
        own_body = own_body.rstrip(";").rstrip()
        nested_tail = body_text[nested_match.end() :]
        nested_candidates = _parse_block(nested_tail, scope=scope, parent_term=terms[0])
        if _is_pure_repeal_marker(own_body):
            return nested_candidates
        own_candidate = DefinitionCandidate(
            terms=tuple(terms),
            definition_text=own_body,
            scope=scope,
            qualifier=qualifier,
            parent_term=parent_term,
        )
        return [own_candidate] + nested_candidates

    if _is_pure_repeal_marker(body_text):
        return []

    return [
        DefinitionCandidate(
            terms=tuple(terms),
            definition_text=body_text,
            scope=scope,
            qualifier=qualifier,
            parent_term=parent_term,
        )
    ]


def extract_definitions_from_section(text: str, *, scope: str) -> list[DefinitionCandidate]:
    """Extract every (term(s), definition) pair from a located הגדרות
    section's body (or any other body composed of `:-`-marked entries).

    Handles multi-term entries (one dash, N terms), qualifier-before-dash,
    list-form entries (spanning through `::`-indented sub-items to the
    next TOP-LEVEL `:-` entry -- not merely the first `;`), and recursive
    nested sub-definitions.
    """
    candidates: list[DefinitionCandidate] = []
    for block in _split_into_blocks(text):
        candidates.extend(_parse_block(block, scope=scope, parent_term=None))
    return candidates


def extract_local_definitions(article_body: str) -> list[DefinitionCandidate]:
    """Scan a (non-הגדרות) article body for `לענין זה,` / `בסעיף זה,`
    immediately preceding a quoted-term-dash-definition. Scope is always
    `"local"`.
    """
    candidates: list[DefinitionCandidate] = []
    for match in _LOCAL_TRIGGER_RE.finditer(article_body):
        term = match.group(1)
        definition_text = match.group(2).strip()
        candidates.append(
            DefinitionCandidate(
                terms=(term,),
                definition_text=definition_text,
                scope="local",
            )
        )
    return candidates


def extract_adhoc_definitions(text: str) -> list[DefinitionCandidate]:
    """Scan `text` for unquoted `(להלן - X)` apposition definitions,
    outside any הגדרות section. Requires the captured span to be <= 4
    tokens (higher false-positive risk otherwise). Scope is always
    `"local"`.
    """
    candidates: list[DefinitionCandidate] = []
    for match in _ADHOC_RE.finditer(text):
        term = match.group(1).strip()
        if term.startswith('"') and term.endswith('"') and len(term) >= 2:
            term = term[1:-1].strip()
        if not term or len(term.split()) > 4:
            continue
        candidates.append(
            DefinitionCandidate(terms=(term,), definition_text=term, scope="local")
        )
    return candidates
