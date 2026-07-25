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


class ValidationError(ValueError):
    """Raised when a user-submitted assertion payload fails validation."""


# --- Sanitization -----------------------------------------------------------
#
# `<script>`/`<style>` blocks are removed *with* their content (that
# content is code, never legitimate proposition text); every other tag is
# stripped while its inner text is preserved untouched, which is what lets
# an event-handler attribute like `onerror=` disappear along with the tag
# that carried it. Plain text with no markup at all must be a byte-for-
# byte no-op (spec §2: "stored as authored") — we never HTML-escape
# quotes/dashes/ampersands, since that would silently rewrite legitimate
# text rather than merely neutralizing active markup.

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_for_storage(raw_text: str) -> str:
    """Return `raw_text` with any active HTML/script content neutralized.

    Submitted text (including anything that reads like an instruction,
    e.g. "ignore previous instructions...") is data to be stored and
    rendered inertly — this function never interprets or acts on content,
    it only strips markup that a browser would otherwise execute/render.
    """
    if raw_text is None:
        return raw_text
    text = _SCRIPT_STYLE_RE.sub("", raw_text)
    text = _TAG_RE.sub("", text)
    return text


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
