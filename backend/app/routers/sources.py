"""Bounded, matter-authorized source discovery for people and local agents."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, union_all, literal
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.article import Article
from app.models.source_span import SourceSpan
from app.models.matter import Matter
from app.routers.assertions import get_session, get_current_user_id, _require_matter_member

router = APIRouter(prefix="/api/v1/matters", tags=["sources"])


def _matter(session, user_id, matter_id):
    _require_matter_member(session, user_id, matter_id)
    matter = session.get(Matter, matter_id)
    if matter is None:
        raise HTTPException(404, "matter not found")
    return matter


@router.get("/{matter_id}/entities")
def list_entities(matter_id: str, q: str = "", limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0), session: Session = Depends(get_session),
                  user_id: str = Depends(get_current_user_id)) -> dict:
    matter = _matter(session, user_id, matter_id)
    docs = select(literal("Document").label("type"), Document.id.label("id"),
                  Document.title.label("label")).where(
        Document.matter_id == matter_id, Document.repository_id == matter.repository_id)
    articles = select(literal("Article").label("type"), Article.id.label("id"),
                      (Document.title + " / " + Article.number + " " + func.coalesce(Article.heading, "")).label("label")).join(
        Document, Article.document_id == Document.id).where(
            Article.matter_id == matter_id, Document.matter_id == matter_id,
            Document.repository_id == matter.repository_id)
    rows = union_all(docs, articles).subquery()
    stmt = select(rows)
    if q.strip():
        stmt = stmt.where(rows.c.label.icontains(q.strip(), autoescape=True))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = session.execute(stmt.order_by(rows.c.type, rows.c.label, rows.c.id).limit(limit).offset(offset)).mappings().all()
    return {"items": [dict(row) for row in items], "total": total}


@router.get("/{matter_id}/source-spans")
def list_spans(matter_id: str, q: str = "", document_id: str | None = None,
               limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
               session: Session = Depends(get_session), user_id: str = Depends(get_current_user_id)) -> dict:
    matter = _matter(session, user_id, matter_id)
    stmt = select(SourceSpan, Document.title).join(Document, SourceSpan.document_id == Document.id).where(
        SourceSpan.matter_id == matter_id, Document.matter_id == matter_id,
        Document.repository_id == matter.repository_id)
    if q.strip():
        stmt = stmt.where(SourceSpan.quote_text.icontains(q.strip(), autoescape=True))
    if document_id:
        stmt = stmt.where(SourceSpan.document_id == document_id)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = [{"id": span.id, "document_id": span.document_id, "document_title": title,
              "quote_text": span.quote_text, "matter_id": span.matter_id}
             for span, title in session.execute(stmt.order_by(SourceSpan.id).limit(limit).offset(offset))]
    return {"items": items, "total": total}
