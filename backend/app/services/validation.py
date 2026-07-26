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
#
# Ruling R16 (2026-07-26): a post-launch audit found two further defects,
# both fixed here:
#   (a) `handle_entityref`/`handle_charref` used to re-emit `f"&{name};"`/
#       `f"&#{name};"` -- appending a `;` the author never typed (`R&D` ->
#       `R&D;`), and for a malformed numeric charref (`&#160a`, `&#5b`) the
#       stdlib hands back a `name` that carries the trailing text, so each
#       fixpoint pass made the string LONGER instead of shorter. That
#       breaks the very premise the old R14 paragraph relied on ("every
#       changing pass strictly shortens"), so the loop never converges,
#       burns O(n^2) CPU, hits the `len(raw_text) + 2` bound, and fails
#       closed -- silently destroying the entire document. The fix is to
#       never let the parser see an `&` at all: `_sanitize_once` shields
#       every `&` behind a private sentinel before `feed()` and restores
#       it in the collected text afterward. With no `&` visible,
#       `HTMLParser` can never produce an entity/charref callback, so
#       nothing is reconstructed and no `;` is ever inserted -- the growth
#       path is removed at the source rather than patched after the fact.
#   (b) Suppressing element CONTENT for every raw-text/RCDATA wrapper
#       (`title`/`textarea`/`xmp`/`iframe`/`noembed`/`noframes`) meant an
#       attacker's unclosed wrapper tag swallowed all authored prose that
#       followed it for the rest of the document. Content suppression now
#       applies only to `script`/`style` -- their payload is code, never
#       proposition text, so dropping it is correct. The other wrapper
#       tags are still stripped as tags, and the stdlib tokenizer still
#       hands back their contents as one literal (un-tokenized) data
#       chunk; any markup nested inside that chunk (e.g. `<title><img
#       onerror=...>`) is preserved as plain text on this pass, then
#       recognized and stripped as real markup by the existing FIXPOINT
#       driver (R13/R14) on the very next pass -- so nested payloads stay
#       fully neutralized without suppressing legitimate prose.
_CDATA_CONTENT_TAGS = frozenset({"script", "style"})

# No `\A` anchor: `re.Pattern.match(string, pos)` already only ever tries to
# match starting exactly at `pos` (it does not search forward), so `\A`
# added nothing at the default `pos=0` call sites below and would actively
# break the `pos > 0` lookups `_salvage_trailing_prose` now performs to
# find each subsequent tag opening in a chain.
#
# Tag-name character class matches `HTMLParser`'s own tolerant tag-name
# grammar (its `tagfind_tolerant`: a letter, then anything but whitespace/
# `/`/`>`) rather than only `[a-zA-Z0-9]`. A narrower class here would
# under-recognize a chained tag whose name contains e.g. `-`, `_`, or `:`
# (all valid per that grammar): `_salvage_trailing_prose` would stop the
# chain walk one tag early, leaving the rest of the chain embedded as
# ordinary text for a later `sanitize_for_storage` fixpoint pass to
# rediscover via the real `HTMLParser` tokenizer -- correct, but right
# back to one extra O(n) pass per such tag name, undermining R15's
# single-call goal.
_ABANDONED_TAG_OPEN_RE = re.compile(r"<[a-zA-Z][^\s/>]*/?")
_ABANDONED_ATTR_RE = re.compile(r"""\s*[^\s=]+=(?:"[^"]*"|'[^']*'|[^\s]*)""")


def _salvage_trailing_prose(leftover: str) -> str:
    """Return the prose tail past a run of abandoned, never-closed tags.

    `leftover` is whatever `HTMLParser` could not resolve into a complete
    tag because no `>` ever arrived. If it doesn't even look like a start
    tag opening (e.g. an unterminated comment/declaration/end-tag, or a
    bare trailing `<`), there is no attribute grammar to walk past, so it
    is dropped wholesale -- it is markup debris, not authored text.

    Ruling R15 (2026-07-26): a single abandoned tag can be immediately
    followed by another one (no `>` anywhere in the whole input), chained
    back-to-back -- e.g. `<img onerror=alert(1) <svg onload=alert(2)
    tail`. Rather than resolving only the first tag and leaving the rest
    of the chain for a later fixpoint pass (which made the driving loop
    in `sanitize_for_storage` do O(n) passes of O(n) work each for an
    n-tag chain), this walks the *whole* chain in one call: after each
    tag's attribute-token run, it checks whether the next non-whitespace
    content is itself another abandoned-tag opening and, if so, keeps
    going. Any whitespace between one tag's attributes and the next tag's
    `<` is genuine authored text (not attribute grammar), so it is kept
    -- exactly as it would have survived one gap-preserving pass at a
    time under the old per-tag algorithm, just computed in a single walk.
    """
    match = _ABANDONED_TAG_OPEN_RE.match(leftover)
    if not match:
        return ""
    pos = match.end()
    n = len(leftover)
    parts: list[str] = []
    while True:
        while True:
            attr_match = _ABANDONED_ATTR_RE.match(leftover, pos)
            if not attr_match:
                break
            pos = attr_match.end()
        gap_end = pos
        while gap_end < n and leftover[gap_end].isspace():
            gap_end += 1
        next_match = _ABANDONED_TAG_OPEN_RE.match(leftover, gap_end)
        if not next_match:
            break
        # `pos:gap_end` is the whitespace gap between this tag's last
        # attribute and the next chained tag's opening -- preserve it,
        # drop the tag opening itself, and keep walking the chain.
        parts.append(leftover[pos:gap_end])
        pos = next_match.end()
    parts.append(leftover[pos:])
    return "".join(parts)


class _SanitizingParser(HTMLParser):
    """Collects only character data, dropping every tag it recognizes.

    `<script>`/`<style>` element content is suppressed along with their
    tags; every other tag's surrounding text is preserved. The caller
    (`_sanitize_once`) shields every `&` from the input before `feed()`,
    so this parser is never fed a real entity/character reference and
    `handle_entityref`/`handle_charref` are never invoked -- nothing is
    reconstructed, so output is never re-escaped or rewritten, only
    markup is removed. `convert_charrefs=False` is kept regardless so
    `handle_data` always receives raw text unmodified.
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

    def get_text(self) -> str:
        return "".join(self._chunks)


# Sentinel used to shield `&` from the parser entirely (Ruling R16(a)): a
# NUL-bracketed marker that cannot collide with authored text because NUL
# bytes are stripped from the input first, immediately below. Any `&` is
# swapped for this sentinel before `feed()` and swapped back after the
# text is collected, so `HTMLParser` never sees an entity/character
# reference to reconstruct -- see `_sanitize_once`.
_AMPERSAND_SENTINEL = "\x00A\x00"


def _sanitize_once(raw_text: str) -> str:
    """Run one pass of the parser-based tag/raw-text-element stripper.

    A single pass removes every tag `HTMLParser` recognizes as such, drops
    the contents of `script`/`style` elements entirely, and salvages the
    prose tail past the trailing run of chained abandoned (never-closed)
    tags. It does NOT guarantee the output contains no more removable
    markup -- see `sanitize_for_storage`, which drives this to a fixpoint
    (e.g. for raw-text/RCDATA wrapper content revealed only after another
    pass, per Ruling R16(b)).

    Ruling R16(a): `&` is shielded from the parser before `feed()` (NUL
    bytes are stripped first so the sentinel is guaranteed unique) and
    restored in the collected text afterward, so the parser can never
    invoke an entity/charref callback and nothing is ever reconstructed.

    Ruling R17 (2026-07-25): `leftover = parser.rawdata` is a snapshot
    taken BEFORE `parser.close()` -- but `close()` itself is not a no-op
    for every shape of leftover. For a genuinely never-closed start tag
    (no raw-text/RCDATA wrapper involved), `close()` silently discards the
    dangling fragment with no `handle_data` call at all, which is exactly
    the gap `_salvage_trailing_prose` exists to patch. But when the
    leftover is actually the unflushed content of an unclosed raw-text/
    RCDATA wrapper (`<iframe>`, `<title>`, ...), `close()` DOES resolve
    it -- it flushes that same pending text through `handle_data` itself,
    so `parser.get_text()` already contains it. Running
    `_salvage_trailing_prose` over the pre-close snapshot in that case
    processes the same tail a second time: once via `close()`'s own flush,
    once via the salvage fallback -- duplicating authored trailing prose
    on each fixpoint pass, and compounding into exponential blowup or
    fail-closed document destruction when more than one such wrapper
    chains in one input. `close_emitted` distinguishes the two cases by
    comparing the collected text's length immediately before and after
    `close()`: only append the salvage fallback when `close()` itself
    emitted nothing (the genuine never-closed-tag case), never when it
    already flushed the tail on its own.
    """
    shielded = raw_text.replace("\x00", "").replace("&", _AMPERSAND_SENTINEL)
    parser = _SanitizingParser()
    parser.feed(shielded)
    leftover = parser.rawdata  # unresolved tail, if input ended mid-tag
    before = len(parser.get_text())
    parser.close()
    text = parser.get_text()
    close_emitted = len(text) > before
    if not close_emitted and _ABANDONED_TAG_OPEN_RE.match(leftover):
        text += _salvage_trailing_prose(leftover)
    return text.replace(_AMPERSAND_SENTINEL, "&")


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

    Ruling R14 (as corrected by R16(a)): R14 originally claimed every pass
    that changes the text strictly shortens it, guaranteeing convergence
    within `len(raw_text)` passes. That claim was FALSE for malformed
    numeric character references (e.g. `&#160a`): the old entity/charref
    reconstruction could hand back a string LONGER than its input, so a
    pass could change the text without shortening it, and the fixpoint
    would never converge. R16(a) removes that growth path at the source
    by shielding `&` from the parser entirely (see `_sanitize_once`), so
    every changing pass now only ever removes characters. The loop is
    still bounded at `len(raw_text) + 2` iterations -- not because a
    strict-shortening proof is assumed, but as a termination guard
    derived from the input: if the bound is ever hit without converging,
    that is a sign some fixpoint assumption has been violated, so this
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
