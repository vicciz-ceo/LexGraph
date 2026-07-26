"""User-submitted assertion validation (Developer track B5).

Spec §7 / gate G10: propositions/rationales/comments must be sanitized so
raw HTML/scripts are stored/rendered as inert data, and submitted text
must never be treated as system/model instructions. The proposition must
be stored EXACTLY as authored (spec §2) — sanitization must not rewrite
legitimate text, only neutralize active markup.
"""

from __future__ import annotations

import re
import uuid as _uuid
from datetime import date, datetime
from html.parser import HTMLParser


class ValidationError(ValueError):
    """Raised when a user-submitted assertion payload fails validation."""


# --- Sanitization -----------------------------------------------------------
#
# Ruling R12 (2026-07-26): two rounds of regex patching (`_TAG_RE`, then an
# `_UNCLOSED_TAG_RE` bolt-on for the unclosed-tag bypass) each closed one
# hole while the naive "first `<` to the next `>`" model kept opening new
# ones -- and independently corrupted benign prose containing an unrelated
# `<` ... `>` pair (e.g. "amount is < $500 ... term is > 10 years"). A
# regex has no notion of "am I inside a tag": that has to be actual parser
# state. `sanitize_for_storage` now runs input through `html.parser
# .HTMLParser`, the same tokenizer class browsers' tag/attribute-name
# grammar is modeled on: it tracks state properly, so quoted attributes,
# mixed case, newlines between attributes, and the no-space-before-
# attribute evasion (`<img/onerror=...`) are all recognized as tag
# machinery and dropped, while an unrelated `<`/`>` pair in plain prose is
# just two characters of data. `<script>`/`<style>` element content is
# dropped with the tag (that content is code, never proposition text);
# every other tag is stripped while its surrounding text is preserved.
# Plain text with no markup at all is a byte-for-byte no-op (spec §2:
# "stored as authored") -- we never HTML-escape quotes/dashes/ampersands,
# since that would silently rewrite legitimate text rather than merely
# neutralizing active markup.
#
# One gap the stdlib tokenizer itself leaves: if a start tag never finds
# its closing `>` anywhere in the input (another well-known bypass -- just
# don't close your tag), `HTMLParser.close()` silently discards the entire
# abandoned tag *and* any text after it, with no callback at all (verified
# directly against the stdlib: `parser.rawdata` holds the unterminated
# fragment after `feed()`, and `close()` drops it with zero handle_data
# calls). Since the sanitized value must still preserve any legitimate
# sentence text an attacker's unclosed payload happens to be followed by,
# `_salvage_trailing_prose` inspects exactly that leftover, unparsed
# fragment: it drops the tag name plus the run of `name=value` attribute
# tokens immediately following it (the shape a live attribute like
# `onerror=` must take), and returns whatever text comes after the last
# recognizable attribute token untouched.
#
# Ruling R13 (2026-07-26): QA cycle 3 found two bypasses, both symptoms of
# the same root cause -- a single pass REMOVES markup but can LEAVE TEXT
# THAT IS STILL MARKUP:
#   (1) `HTMLParser` itself tokenizes `script`/`style`/`iframe`/`xmp`/
#       `noembed`/`noframes` (its `CDATA_CONTENT_ELEMENTS`) and `textarea`/
#       `title` (its `RCDATA_CONTENT_ELEMENTS`) as raw-text containers: once
#       inside one of these, the tokenizer does NOT recognize nested tags at
#       all -- it hands the entire contents back as one `handle_data` call,
#       literal `<script>...` and all. Suppressing only `script`/`style`
#       left the other four CDATA elements and both RCDATA elements as an
#       open pass-through: `<iframe><script>alert(1)</script></iframe>`
#       tokenizes as start-tag `iframe`, one data chunk containing the
#       literal text `<script>alert(1)</script>`, end-tag `iframe` -- and
#       since `_cdata_skip_depth` was never incremented for `iframe`, that
#       literal markup text was kept. Fix: suppress `handle_data` for the
#       parser's OWN raw-text element set, read from the installed
#       `HTMLParser` class itself rather than hardcoded, so it always
#       matches whatever this stdlib build actually tokenizes as raw-text.
#   (2) `_salvage_trailing_prose` resolves exactly ONE abandoned tag: it
#       strips the tag name plus one run of attribute tokens and returns
#       everything after that untouched -- but "everything after" can
#       itself contain a second, independent abandoned tag chained right
#       after the first (`<img ... onerror=alert(1) <svg onload=alert(2)
#       trailing`), which a single salvage pass leaves verbatim in the
#       "preserved" tail.
#   Both are instances of one general fact: no single fixed-shape pass over
#   attacker-controlled text can guarantee its OUTPUT contains no more
#   removable markup -- another wrapper tag, another chained abandoned tag,
#   etc. The general fix is a fixpoint: re-run the one-pass sanitizer on
#   its own output until it stops changing (each pass only ever
#   removes/neutralizes markup, never adds or reorders authored text, so
#   this converges and can only make the result MORE sanitized, never
#   less). `sanitize_for_storage` is now that fixpoint driver; the single
#   pass itself lives in `_sanitize_once`.
_CDATA_CONTENT_TAGS = frozenset(
    tag.lower()
    for tag in (
        *getattr(HTMLParser, "CDATA_CONTENT_ELEMENTS", ("script", "style")),
        *getattr(HTMLParser, "RCDATA_CONTENT_ELEMENTS", ()),
    )
)

_ABANDONED_TAG_OPEN_RE = re.compile(r"\A<[a-zA-Z][a-zA-Z0-9]*/?")
_ABANDONED_ATTR_RE = re.compile(r"""\s*[^\s=]+=(?:"[^"]*"|'[^']*'|[^\s]*)""")


def _salvage_trailing_prose(leftover: str) -> str:
    """Return the prose tail of an abandoned, never-closed tag fragment.

    `leftover` is whatever `HTMLParser` could not resolve into a complete
    tag because no `>` ever arrived. If it doesn't even look like a start
    tag opening (e.g. an unterminated comment/declaration/end-tag, or a
    bare trailing `<`), there is no attribute grammar to walk past, so it
    is dropped wholesale -- it is markup debris, not authored text.
    """
    match = _ABANDONED_TAG_OPEN_RE.match(leftover)
    if not match:
        return ""
    pos = match.end()
    while True:
        attr_match = _ABANDONED_ATTR_RE.match(leftover, pos)
        if not attr_match:
            break
        pos = attr_match.end()
    return leftover[pos:]


class _SanitizingParser(HTMLParser):
    """Collects only character data, dropping every tag it recognizes.

    `<script>`/`<style>` element content is suppressed along with their
    tags; every other tag's surrounding text is preserved. Character/
    entity references are reconstructed verbatim (never decoded) so
    output is never re-escaped or rewritten -- only markup is removed.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._chunks: list[str] = []
        self._cdata_skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _CDATA_CONTENT_TAGS:
            self._cdata_skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _CDATA_CONTENT_TAGS and self._cdata_skip_depth > 0:
            self._cdata_skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._cdata_skip_depth:
            self._chunks.append(data)

    def handle_entityref(self, name: str) -> None:
        if not self._cdata_skip_depth:
            self._chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._cdata_skip_depth:
            self._chunks.append(f"&#{name};")

    def get_text(self) -> str:
        return "".join(self._chunks)


def _sanitize_once(raw_text: str) -> str:
    """Run one pass of the parser-based tag/raw-text-element stripper.

    A single pass removes every tag `HTMLParser` recognizes as such, drops
    the contents of raw-text/RCDATA wrapper elements entirely, and salvages
    the prose tail of ONE trailing abandoned (never-closed) tag. It does
    NOT guarantee the output contains no more removable markup -- see
    `sanitize_for_storage`, which drives this to a fixpoint.
    """
    parser = _SanitizingParser()
    parser.feed(raw_text)
    leftover = parser.rawdata  # unresolved tail, if input ended mid-tag
    parser.close()
    text = parser.get_text()
    if _ABANDONED_TAG_OPEN_RE.match(leftover):
        text += _salvage_trailing_prose(leftover)
    return text


def sanitize_for_storage(raw_text: str) -> str:
    """Return `raw_text` with any active HTML/script content neutralized.

    Submitted text (including anything that reads like an instruction,
    e.g. "ignore previous instructions...") is data to be stored and
    rendered inertly — this function never interprets or acts on content,
    it only strips markup that a browser would otherwise execute/render.

    Ruling R13: one pass of `_sanitize_once` can leave behind text that is
    itself still markup (a raw-text wrapper's literal contents, or a second
    abandoned tag chained after the first one that got salvaged). Each pass
    only ever removes/neutralizes markup -- it never adds or reorders
    authored text -- so re-running it on its own output converges on a
    fixpoint that can only be more sanitized than any single pass, never
    less.

    Ruling R14: every pass that changes the text strictly shortens it (a
    pass that left the length unchanged would have to be a no-op, which is
    the convergence condition above), so convergence is guaranteed within
    `len(raw_text)` passes. The loop is bounded at `len(raw_text) + 2`
    iterations -- a termination guard derived from the input, not a
    security parameter. If the bound is ever hit without converging, that
    is a sign the fixpoint assumption itself has been violated, so this
    fails closed and returns "" rather than the last (possibly
    still-markup) output, the raw input, or raising.
    """
    if raw_text is None:
        return raw_text
    text = raw_text
    for _ in range(len(raw_text) + 2):
        sanitized = _sanitize_once(text)
        if sanitized == text:
            return sanitized
        text = sanitized
    return ""


# --- Presence / consistency checks ------------------------------------------


def validate_proposition_not_empty(proposition: str) -> None:
    if proposition is None or not proposition.strip():
        raise ValidationError("proposition cannot be empty")


def validate_effective_dates(
    effective_from: date | datetime | None, effective_to: date | datetime | None
) -> None:
    """Raise ValidationError if the date range is not logically consistent.

    Open-ended ranges (either or both bounds `None`) are always consistent.
    """
    if effective_from is not None and effective_to is not None and effective_to < effective_from:
        raise ValidationError("effective_to cannot be before effective_from")


# --- Assertion-type controlled vocabulary ------------------------------------
#
# Illustrative types drawn from spec §1's example propositions. Anything
# outside this vocabulary must be explicitly marked
# `assertion_type_is_proposed_new` by the submitter (spec §7) rather than
# silently accepted or silently rejected.

ALLOWED_ASSERTION_TYPES = frozenset(
    {
        "INTERPRETS",
        "CREATES_EXCEPTION_TO",
        "CONFLICTS_WITH",
        "MODIFIES",
        "APPLIES_TO",
        "RELEVANT_TO",
        "WEAKENS",
        "SUPPORTS",
        "SURVIVES_TERMINATION",
        "DISTINGUISHABLE_FROM",
    }
)


def validate_assertion_type(assertion_type: str, *, is_proposed_new: bool = False) -> None:
    """Raise ValidationError unless `assertion_type` is in the controlled
    vocabulary or has been explicitly marked as a proposed new type.
    """
    if assertion_type in ALLOWED_ASSERTION_TYPES:
        return
    if is_proposed_new:
        return
    raise ValidationError(
        f"assertion_type '{assertion_type}' is not in the controlled vocabulary; "
        "set assertion_type_is_proposed_new=true to submit it as a proposed new type"
    )


# --- Matter-scoped subject/object/evidence checks ---------------------------
#
# This schema (F1, frozen) has no generic entity/graph-node registry table
# — subject/object entities are opaque {type, id} references resolved
# against the graph, not against a local table. The one thing this backend
# *can* verify without such a registry is identifier shape: every
# matter-scoped row this system mints (documents, source spans, matters,
# users, assertions, ...) uses a canonical UUID primary key. An identifier
# that isn't a well-formed UUID cannot be resolved to any resource this
# system owns and is rejected as unauthorized/unscoped.


def validate_matter_scoped_entity_id(entity_id: str, *, label: str = "entity") -> None:
    try:
        _uuid.UUID(str(entity_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationError(
            f"{label} id '{entity_id}' is not a valid matter-scoped identifier"
        ) from exc


def validate_evidence_matter_scope(
    source_span_matter_id: str | None, assertion_matter_id: str
) -> None:
    """Raise ValidationError if a *resolved* source span belongs to a
    different matter than the assertion it would be attached to.

    Only called with a matter id when the source span was actually found —
    an unresolved/opaque span reference is not itself grounds for
    rejection here (existence-checking source spans is a separate,
    unstarted concern); this guards the tested matter-isolation gate
    (spec §7: "a user cannot attach evidence from another inaccessible
    matter").
    """
    if source_span_matter_id is not None and source_span_matter_id != assertion_matter_id:
        raise ValidationError("evidence source span belongs to an inaccessible matter")
