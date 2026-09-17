"""Resolve persisted graph entities and evidence inside a matter."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.assertion import Assertion
from app.models.definition import Definition
from app.models.document import Document
from app.models.source_span import SourceSpan

ENTITY_MODELS = {"Document": Document, "Article": Article, "Definition": Definition,
                 "SourceSpan": SourceSpan, "Assertion": Assertion}


def validate_entity(session: Session, entity, matter_id: str, *, strict: bool = False) -> None:
    model = ENTITY_MODELS.get(entity.type)
    if model is None:
        if strict:
            raise HTTPException(422, "Use a persisted entity type: " + ", ".join(ENTITY_MODELS))
        return  # Legacy external graph references retain their existing UUID contract.
    row = session.get(model, entity.id)
    if row is None or row.matter_id != matter_id:
        raise HTTPException(422, "Entity must exist in the selected matter")


def validate_span(session: Session, span_id: str, matter_id: str, repository_id: str) -> SourceSpan:
    span = session.get(SourceSpan, span_id)
    doc = session.get(Document, span.document_id) if span else None
    if (span is None or span.matter_id != matter_id or doc is None
            or doc.matter_id != matter_id or doc.repository_id != repository_id):
        raise HTTPException(422, "Evidence must resolve to a document in the selected matter and repository")
    return span
