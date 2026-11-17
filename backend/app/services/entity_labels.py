"""Human-readable labels for the entities an assertion references (finding ui:30).

The assertion detail page names its subject and object instead of showing
their UUIDs. Only persisted entities of the assertion's own matter are
resolved; a legacy opaque reference (for example ``Provision``), a missing
row, or a row of another matter gets ``None``, so a label never crosses a
matter boundary. Labels mirror the source picker's wording
(``GET /matters/{id}/entities``): a document's title, and
``"<document title> / <number> <heading>"`` for an article.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.assertion import Assertion
from app.models.definition import Definition
from app.models.document import Document
from app.models.source_span import SourceSpan

# Quotes and propositions can be long (a span may hold a whole article).
MAX_LABEL_LENGTH = 240


def _shorten(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= MAX_LABEL_LENGTH:
        return text
    return text[: MAX_LABEL_LENGTH - 1].rstrip() + "…"


def _in_matter(row, matter_id: str):
    return row if row is not None and row.matter_id == matter_id else None


def _article_label(session: Session, article: Article, matter_id: str) -> str:
    heading = " ".join(part for part in (article.number, article.heading) if part)
    document = _in_matter(session.get(Document, article.document_id), matter_id)
    if document is None:
        return heading
    return f"{document.title} / {heading}" if heading else document.title


def entity_label(
    session: Session, matter_id: str, entity_type: str | None, entity_id: str | None
) -> str | None:
    """Return a short label for one referenced entity, or ``None``."""
    if not entity_type or not entity_id:
        return None
    label: str | None = None
    if entity_type == "Document":
        document = _in_matter(session.get(Document, entity_id), matter_id)
        label = document.title if document else None
    elif entity_type == "Article":
        article = _in_matter(session.get(Article, entity_id), matter_id)
        label = _article_label(session, article, matter_id) if article else None
    elif entity_type == "Definition":
        definition = _in_matter(session.get(Definition, entity_id), matter_id)
        if definition is not None:
            terms = ", ".join(f'"{term}"' for term in definition.terms or [])
            article = _in_matter(session.get(Article, definition.article_id), matter_id)
            where = _article_label(session, article, matter_id) if article else ""
            label = f"{terms} ({where})" if terms and where else (terms or where or None)
    elif entity_type == "SourceSpan":
        span = _in_matter(session.get(SourceSpan, entity_id), matter_id)
        label = span.quote_text if span else None
    elif entity_type == "Assertion":
        assertion = _in_matter(session.get(Assertion, entity_id), matter_id)
        label = assertion.proposition if assertion else None
    if not label or not label.strip():
        return None
    return _shorten(label)


def label_entities(session: Session, matter_id: str, serialized: dict) -> dict:
    """Add ``label`` to a serialized assertion's subject and object entities."""
    for key in ("subject_entity", "object_entity"):
        entity = serialized.get(key)
        if entity is not None:
            entity["label"] = entity_label(session, matter_id, entity.get("type"), entity.get("id"))
    return serialized
