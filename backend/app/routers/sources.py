"""Bounded, matter-authorized source discovery for people and local agents."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, func, select, union_all, literal
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.article import Article
from app.models.source_span import SourceSpan
from app.models.matter import Matter
from app.routers.assertions import get_session, get_current_user_id, _require_matter_member
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
                  offset: int = Query(0, ge=0), session: Session = Depends(get_session),
                  user_id: str = Depends(get_current_user_id)) -> dict:
    """Documents first, then each document's articles in natural number order."""
    matter = _matter(session, user_id, matter_id)
    in_scope = (Document.matter_id == matter_id, Document.repository_id == matter.repository_id)
    docs = select(literal("Document").label("type"), Document.id.label("id"), Document.title.label("label"),
                  literal(0).label("rank"), Document.title.label("document_title"),
                  Document.id.label("document_id"), literal(None, String).label("number")).where(*in_scope)
    article_label = Document.title + " / " + func.trim(Article.number + " " + func.coalesce(Article.heading, ""))
    articles = select(literal("Article"), Article.id, article_label, literal(1), Document.title, Document.id,
                      Article.number).join(Document, Article.document_id == Document.id).where(
        Article.matter_id == matter_id, *in_scope)
    rows = union_all(docs, articles).subquery()
    stmt = select(rows.c.type, rows.c.id, rows.c.label)
    if q.strip():
        stmt = stmt.where(contains_text(rows.c.label, q))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    order = (rows.c.rank, rows.c.document_title, rows.c.document_id, NaturalOrder(rows.c.number),
             rows.c.number, rows.c.id)
    items = session.execute(stmt.order_by(*order).limit(limit).offset(offset)).mappings().all()
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
        stmt = stmt.where(contains_text(SourceSpan.quote_text, q))
    if document_id:
        stmt = stmt.where(SourceSpan.document_id == document_id)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    items = [{"id": span.id, "document_id": span.document_id, "document_title": title,
              "quote_text": span.quote_text, "matter_id": span.matter_id}
             for span, title in session.execute(stmt.order_by(SourceSpan.id).limit(limit).offset(offset))]
    return {"items": items, "total": total}
