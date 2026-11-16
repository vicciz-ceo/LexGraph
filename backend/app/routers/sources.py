"""Bounded, matter-authorized source discovery for people and local agents."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.article import Article
from app.models.source_span import SourceSpan
from app.models.matter import Matter
from app.routers.assertions import get_session, get_current_user_id, _require_matter_member
from app.services.paging import MAX_OFFSET
from app.services.text_search import NaturalOrder, contains_text

router = APIRouter(prefix="/api/v1/matters", tags=["sources"])


def _matter(session, user_id, matter_id):
    _require_matter_member(session, user_id, matter_id)
    matter = session.get(Matter, matter_id)
    if matter is None:
        raise HTTPException(404, "matter not found")
    return matter


@router.get("/{matter_id}/entities")
def list_entities(matter_id: str, q: str = "", limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0, le=MAX_OFFSET), session: Session = Depends(get_session),
                  user_id: str = Depends(get_current_user_id)) -> dict:
    """Documents first (by title), then each document's articles in natural number order.

    Articles are counted per document, and only documents overlapping the page
    are sorted, so the natural-order key is not computed for the whole matter."""
    matter = _matter(session, user_id, matter_id)
    in_scope = (Document.matter_id == matter_id, Document.repository_id == matter.repository_id)
    by_title = (Document.title, Document.id)
    label = Document.title + " / " + func.trim(Article.number + " " + func.coalesce(Article.heading, ""))
    documents = select(Document.id, Document.title).where(*in_scope)
    articles = select(Article.id, label).join(Document, Article.document_id == Document.id).where(
        Article.matter_id == matter_id, *in_scope)
    if q.strip():
        documents = documents.where(contains_text(Document.title, q))
        articles = articles.where(contains_text(label, q))
    matching = session.execute(documents.order_by(*by_title)).all()
    per_document = dict(session.execute(
        articles.with_only_columns(Article.document_id, func.count()).group_by(Article.document_id)).all())
    items = [{"type": "Document", "id": doc_id, "label": title} for doc_id, title in matching[offset:offset + limit]]
    skip = max(0, offset - len(matching))
    for doc_id in session.scalars(select(Document.id).where(*in_scope).order_by(*by_title)):
        if len(items) == limit:
            break
        count = per_document.get(doc_id, 0)
        if skip >= count:
            skip -= count
            continue
        page = articles.where(Article.document_id == doc_id).order_by(
            NaturalOrder(Article.number), Article.number, Article.id).offset(skip).limit(limit - len(items))
        items += [{"type": "Article", "id": art_id, "label": text} for art_id, text in session.execute(page)]
        skip = 0
    return {"items": items, "total": len(matching) + sum(per_document.values())}


@router.get("/{matter_id}/source-spans")
def list_spans(matter_id: str, q: str = "", document_id: str | None = None,
               limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=MAX_OFFSET),
               session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict:
    matter = _matter(session, user_id, matter_id)
    stmt = select(SourceSpan, Document.title).join(Document, SourceSpan.document_id == Document.id).where(
        SourceSpan.matter_id == matter_id, Document.matter_id == matter_id,
        Document.repository_id == matter.repository_id)
    if q.strip():
        stmt = stmt.where(contains_text(SourceSpan.quote_text, q))
    if document_id:
        stmt = stmt.where(SourceSpan.document_id == document_id)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = [{"id": span.id, "document_id": span.document_id, "document_title": title,
              "quote_text": span.quote_text, "matter_id": span.matter_id}
             for span, title in session.execute(stmt.order_by(SourceSpan.id).limit(limit).offset(offset))]
    return {"items": items, "total": total}
