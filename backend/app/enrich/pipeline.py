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
text the suggester produced -- never rewritten. As on that path, the
100,000-character cap is checked on the raw text before it is sanitized,
and a candidate whose text is empty once sanitized is not stored.

Enrichment's own output (audit findings review:16, pipeline:11). Agent
submissions (`POST /api/v1/agent/assertions`, the agent CLI, MCP) share the
origin `model_suggested`; what marks an enrichment row is its revision 1,
whose `revision_reason` is `ENRICHMENT_REVISION_REASON` -- written by this
pipeline, and only by it, since it first ran. (An agent row carries its
`assertion_agent_provenance` audit event instead.) Re-runs are keyed on that
output alone, so an agent or lawyer citing a span never stops the heuristic
from suggesting it:

* a candidate is skipped when every one of its spans is already evidence
  (or the recorded subject) of an enrichment row in the matter;
* enrichment never suggests a proposition it already suggested in the
  matter, whatever became of that suggestion (two spans with one text give
  one draft, also across runs and triggering users);
* and, like every creation path, it does not store an exact duplicate
  (spec section 8): a live assertion with the same proposition, or the
  triggering user's own draft, blocks the candidate.

These checks run against committed state under the assertion write lock
(`app.services.write_lock`), one batch of candidates at a time, so an
enrichment run cannot duplicate a concurrent API, agent or enrichment
writer.

The triggering user must exist and hold a suggesting role (contributor,
reviewer or admin) in the matter, as for any assertion author (audit finding
pipeline:6); `app/enrich/cli.py` reports a refusal and exits non-zero.

Audited (spec section 16, audit finding pipeline:3): each created
assertion gets the same `assertion_created` event as the REST creation
path, in the same transaction, naming revision 1 and the triggering user.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrich.base import Enricher
from app.enrich.suggester import HeuristicEnricher
from app.models.assertion import Assertion
from app.models.assertion_evidence import AssertionEvidence
from app.models.assertion_revision import AssertionRevision
from app.models.matter import Matter
from app.models.matter_role import MatterRole
from app.models.repository import Repository
from app.models.source_span import SourceSpan
from app.models.user import User
from app.services.audit import record_audit_event
from app.services.duplicates import blocks_exact_duplicate, normalize_proposition
from app.services.validation import ValidationError, sanitize_for_storage, validate_text_length
from app.services.write_lock import lock_assertion_writes

_MODEL_ORIGIN = "model_suggested"
_MODEL_STATUS = "draft"
# Reserved for machine/rule-based extraction confidence (spec §2): this
# pipeline's own heuristic never derives it from a user rating.
_HEURISTIC_CONFIDENCE = 0.6
#: revision_reason of revision 1 of every assertion this pipeline writes.
ENRICHMENT_REVISION_REASON = "model-suggested (offline enrichment)"
_SUGGESTING_ROLES = ("contributor", "reviewer", "admin")
# Candidates written per transaction: each batch re-reads the matter under
# the write lock, which other writers wait for meanwhile.
_WRITE_BATCH = 200


class EnrichmentRefused(ValueError):
    """`run_enrichment` cannot run for the given matter and user.
    `app/enrich/cli.py::main` turns this into a clear non-zero exit."""


class UnknownMatterError(EnrichmentRefused):
    """Raised when `run_enrichment` is asked to enrich a matter (or a
    matter with no resolvable repository) that does not exist.
    """


class UnknownUserError(EnrichmentRefused):
    """The triggering user does not exist."""


class UserNotPermittedError(EnrichmentRefused):
    """The triggering user has no suggesting role in the matter."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Candidate:
    assertion_type: str
    proposition_raw: str
    proposition: str
    key: str
    span_ids: list[str]


@dataclass
class _Suggested:
    """What enrichment already suggested in a matter: span ids and
    normalized propositions."""

    span_ids: set[str] = field(default_factory=set)
    keys: set[str] = field(default_factory=set)

    def new_span_ids(self, candidate: _Candidate) -> list[str]:
        if candidate.key in self.keys:
            return []
        return [span_id for span_id in candidate.span_ids if span_id not in self.span_ids]


def _chunks(items: Sequence[_Candidate], size: int) -> Iterator[Sequence[_Candidate]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _require_actor(session: Session, user_id: str, matter_id: str) -> None:
    if session.get(User, user_id) is None:
        raise UnknownUserError(f"user '{user_id}' does not exist")
    role = session.execute(
        select(MatterRole.role).where(MatterRole.user_id == user_id, MatterRole.matter_id == matter_id)
    ).scalars().first()
    if role not in _SUGGESTING_ROLES:
        raise UserNotPermittedError(
            f"user '{user_id}' has no contributor, reviewer or admin role in matter '{matter_id}'"
        )


def _prepare(candidates: list[dict], matter_span_ids: set[str]) -> list[_Candidate]:
    """Candidates that may be stored at all: evidence restricted to the
    matter's own spans, the API's length cap checked on the raw text before
    it is sanitized, and non-empty sanitized text."""
    prepared = []
    for candidate in candidates:
        span_ids = list(dict.fromkeys(
            span_id for span_id in candidate.get("evidence_span_ids", []) if span_id in matter_span_ids))
        proposition_raw = candidate.get("proposition")
        if not span_ids or not isinstance(proposition_raw, str):
            continue
        try:
            validate_text_length(proposition_raw, label="proposition")
        except ValidationError:
            continue
        proposition = sanitize_for_storage(proposition_raw)
        key = normalize_proposition(proposition)
        if not key:
            continue
        prepared.append(_Candidate(candidate["assertion_type"], proposition_raw, proposition, key, span_ids))
    return prepared


def _enrichment_rows(matter_id: str):
    """Criteria selecting this pipeline's rows (revision 1 joined to its
    assertion) in `matter_id`."""
    return (Assertion.matter_id == matter_id, Assertion.origin == _MODEL_ORIGIN,
            AssertionRevision.revision_number == 1,
            AssertionRevision.revision_reason == ENRICHMENT_REVISION_REASON)


def _already_suggested(session: Session, matter_id: str) -> _Suggested:
    """Enrichment's own output in the matter (see the module docstring): the
    proposition and subject span each row was suggested with (revision 1)
    and the spans it cites."""
    suggested = _Suggested()
    first_revisions = session.execute(
        select(AssertionRevision.proposition, AssertionRevision.subject_entity_type,
               AssertionRevision.subject_entity_id)
        .join(Assertion, Assertion.id == AssertionRevision.assertion_id)
        .where(*_enrichment_rows(matter_id))
    ).all()
    for proposition, subject_type, subject_id in first_revisions:
        suggested.keys.add(normalize_proposition(proposition))
        if subject_type == "SourceSpan":
            suggested.span_ids.add(subject_id)
    if first_revisions:
        suggested.span_ids.update(session.execute(
            select(AssertionEvidence.source_span_id)
            .join(Assertion, Assertion.id == AssertionEvidence.assertion_id)
            .join(AssertionRevision, AssertionRevision.assertion_id == Assertion.id)
            .where(*_enrichment_rows(matter_id))
        ).scalars())
    return suggested


def _blocking_keys(session: Session, matter_id: str, owner_user_id: str) -> set[str]:
    """Normalized propositions that block `owner_user_id`'s new assertions
    as exact duplicates (spec section 8)."""
    rows = session.execute(
        select(Assertion.proposition, Assertion.status, Assertion.author_user_id)
        .where(Assertion.matter_id == matter_id)
    )
    return {
        normalize_proposition(proposition)
        for proposition, status, author_user_id in rows
        if blocks_exact_duplicate(status, author_user_id, owner_user_id=owner_user_id)
    }


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
    _require_actor(session, triggered_by_user_id, matter_id)

    active_enricher: Enricher = enricher if enricher is not None else HeuristicEnricher()

    spans = (
        session.execute(select(SourceSpan).where(SourceSpan.matter_id == matter_id))
        .scalars()
        .all()
    )
    span_payloads = [{"id": s.id, "quote_text": s.quote_text} for s in spans]
    prepared = _prepare(active_enricher.suggest(span_payloads), {s.id for s in spans})

    # Cheap first pass on a snapshot: what enrichment already suggested stays
    # suggested, so this only drops candidates the locked pass would drop too
    # -- and keeps an idempotent re-run from taking the write lock at all.
    snapshot = _already_suggested(session, matter_id)
    pending = [candidate for candidate in prepared if snapshot.new_span_ids(candidate)]

    created: list[dict] = []
    for batch in _chunks(pending, _WRITE_BATCH):
        lock_assertion_writes(session, matter_id)
        suggested = _already_suggested(session, matter_id)
        blocking = _blocking_keys(session, matter_id, triggered_by_user_id)
        now = _now()
        written = []
        for candidate in batch:
            new_span_ids = suggested.new_span_ids(candidate)
            if not new_span_ids or candidate.key in blocking:
                continue
            written.append(_write(session, candidate, new_span_ids, repository, matter_id,
                                  triggered_by_user_id, now))
            suggested.span_ids.update(new_span_ids)
            suggested.keys.add(candidate.key)
            blocking.add(candidate.key)  # the new draft blocks its author's twins
        session.commit()
        created.extend(
            {
                "id": assertion.id,
                "assertion_type": assertion.assertion_type,
                "proposition": assertion.proposition,
                "status": assertion.status,
                "origin": assertion.origin,
            }
            for assertion in written
        )

    return created


def _write(session: Session, candidate: _Candidate, span_ids: list[str], repository: Repository,
           matter_id: str, triggered_by_user_id: str, now: datetime) -> Assertion:
    assertion = Assertion(
        id=str(uuid.uuid4()),
        organization_id=repository.organization_id,
        repository_id=repository.id,
        matter_id=matter_id,
        assertion_type=candidate.assertion_type,
        proposition=candidate.proposition,
        # No entity registry to resolve a subject against (see
        # validation.py's matter-scoped-entity-id note) -- the
        # evidence span itself is the most concrete, resolvable
        # subject a heuristic suggestion can point to.
        subject_entity_type="SourceSpan",
        subject_entity_id=span_ids[0],
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
        proposition_raw=candidate.proposition_raw,
        assertion_type=assertion.assertion_type,
        subject_entity_type=assertion.subject_entity_type,
        subject_entity_id=assertion.subject_entity_id,
        object_entity_type=assertion.object_entity_type,
        object_entity_id=assertion.object_entity_id,
        jurisdiction=assertion.jurisdiction,
        effective_from=assertion.effective_from,
        effective_to=assertion.effective_to,
        revision_reason=ENRICHMENT_REVISION_REASON,
        edited_by_user_id=triggered_by_user_id,
        created_at=now,
    )
    session.add(revision)

    for span_id in span_ids:
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

    record_audit_event(
        session,
        actor_user_id=triggered_by_user_id,
        event_type="assertion_created",
        repository_id=assertion.repository_id,
        matter_id=assertion.matter_id,
        assertion_id=assertion.id,
        assertion_revision_id=revision.id,
        new_value=assertion.status,
    )
    return assertion
