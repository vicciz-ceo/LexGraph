"""Live enrichment pipeline (Track B, item B2).

`run_enrichment` reads real `SourceSpan` rows already stored for a matter
(document acquisition is out of scope this sprint -- ruling R7), runs them
through an injected `Enricher` (`app/enrich/base.py`; default: the real,
built-in, fully offline `HeuristicEnricher` -- ruling R4), and writes each
candidate as a REAL `Assertion` / `AssertionRevision` / `AssertionEvidence`
row: origin `model_suggested`, status `draft`, never `accepted` -- the
existing review workflow (`app/routers/assertions.py`'s submit/accept
routes) owns every later status transition, this pipeline never touches
it.

Raw-fidelity mirror of `routers/assertions.py::create_assertion` (per the
Developer brief's hard rule): `proposition` is written through
`sanitize_for_storage(...)`, `proposition_raw` is the verbatim candidate
text the suggester produced -- never rewritten.

Idempotent: a source span that already backs a `model_suggested` assertion
in this matter is not suggested again on a re-run (`app/enrich/cli.py`'s
"idempotent re-run" requirement) -- tracked by the set of source-span ids
already attached as evidence to a `model_suggested` assertion in this
matter.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrich.base import Enricher
from app.enrich.suggester import HeuristicEnricher
from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.matter import Matter
from app.models.repository import Repository
from app.models.source_span import SourceSpan
from app.services.validation import sanitize_for_storage

_MODEL_ORIGIN = "model_suggested"
_MODEL_STATUS = "draft"
# Reserved for machine/rule-based extraction confidence (spec §2): this
# pipeline's own heuristic never derives it from a user rating.
_HEURISTIC_CONFIDENCE = 0.6


class UnknownMatterError(ValueError):
    """Raised when `run_enrichment` is asked to enrich a matter (or a
    matter with no resolvable repository) that does not exist.
    `app/enrich/cli.py::main` turns this into a clear non-zero exit.
    """


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_enrichment(
    session: Session,
    *,
    matter_id: str,
    triggered_by_user_id: str,
    enricher: Enricher | None = None,
) -> list[dict]:
    """Run one enrichment pass over `matter_id`'s existing source spans.

    Returns a list of `{"id", "assertion_type", "proposition", "status",
    "origin"}` summaries for every draft assertion newly created by this
    call (an idempotent re-run over unchanged spans returns `[]`).
    """
    matter = session.get(Matter, matter_id)
    if matter is None:
        raise UnknownMatterError(f"matter '{matter_id}' does not exist")
    repository = session.get(Repository, matter.repository_id)
    if repository is None:
        raise UnknownMatterError(
            f"matter '{matter_id}' has no resolvable repository '{matter.repository_id}'"
        )

    active_enricher: Enricher = enricher if enricher is not None else HeuristicEnricher()

    spans = (
        session.execute(select(SourceSpan).where(SourceSpan.matter_id == matter_id))
        .scalars()
        .all()
    )
    span_payloads = [{"id": s.id, "quote_text": s.quote_text} for s in spans]
    candidates = active_enricher.suggest(span_payloads)

    already_suggested_span_ids = set(
        session.execute(
            select(AssertionEvidence.source_span_id)
            .join(Assertion, Assertion.id == AssertionEvidence.assertion_id)
            .where(Assertion.matter_id == matter_id, Assertion.origin == _MODEL_ORIGIN)
        )
        .scalars()
        .all()
    )

    created: list[dict] = []
    now = _now()
    for candidate in candidates:
        evidence_span_ids = candidate.get("evidence_span_ids", [])
        new_span_ids = [sid for sid in evidence_span_ids if sid not in already_suggested_span_ids]
        if not new_span_ids:
            # Every evidence span behind this candidate was already
            # suggested on a previous run -- idempotent no-op.
            continue

        proposition_raw = candidate["proposition"]
        proposition = sanitize_for_storage(proposition_raw)

        assertion = Assertion(
            id=str(uuid.uuid4()),
            organization_id=repository.organization_id,
            repository_id=repository.id,
            matter_id=matter_id,
            assertion_type=candidate["assertion_type"],
            proposition=proposition,
            # No entity registry to resolve a subject against (see
            # validation.py's matter-scoped-entity-id note) -- the
            # evidence span itself is the most concrete, resolvable
            # subject a heuristic suggestion can point to.
            subject_entity_type="SourceSpan",
            subject_entity_id=new_span_ids[0],
            object_entity_type=None,
            object_entity_id=None,
            origin=_MODEL_ORIGIN,
            status=_MODEL_STATUS,
            author_user_id=triggered_by_user_id,
            confidence=_HEURISTIC_CONFIDENCE,
            jurisdiction=None,
            effective_from=None,
            effective_to=None,
            created_at=now,
            updated_at=now,
            submitted_at=None,
            reviewed_by=None,
            reviewed_at=None,
            superseded_by_assertion_id=None,
            current_revision_number=1,
        )
        session.add(assertion)

        revision = AssertionRevision(
            id=str(uuid.uuid4()),
            assertion_id=assertion.id,
            revision_number=1,
            proposition=assertion.proposition,
            # Verbatim candidate text -- never the (possibly lossy)
            # sanitized `proposition` column above (mirrors
            # routers/assertions.py::create_assertion).
            proposition_raw=proposition_raw,
            assertion_type=assertion.assertion_type,
            subject_entity_type=assertion.subject_entity_type,
            subject_entity_id=assertion.subject_entity_id,
            object_entity_type=assertion.object_entity_type,
            object_entity_id=assertion.object_entity_id,
            jurisdiction=assertion.jurisdiction,
            effective_from=assertion.effective_from,
            effective_to=assertion.effective_to,
            revision_reason="model-suggested (offline enrichment)",
            edited_by_user_id=triggered_by_user_id,
            created_at=now,
        )
        session.add(revision)

        for span_id in new_span_ids:
            session.add(
                AssertionEvidence(
                    id=str(uuid.uuid4()),
                    assertion_id=assertion.id,
                    source_span_id=span_id,
                    evidence_role="supports",
                    added_by_user_id=triggered_by_user_id,
                    created_at=now,
                )
            )
            already_suggested_span_ids.add(span_id)

        session.commit()
        session.refresh(assertion)
        created.append(
            {
                "id": assertion.id,
                "assertion_type": assertion.assertion_type,
                "proposition": assertion.proposition,
                "status": assertion.status,
                "origin": assertion.origin,
            }
        )

    return created
