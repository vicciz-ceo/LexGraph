// Assertion detail — the full record for one assertion: proposition,
// entities, model provenance, evidence spans, discussion, revision
// activity, team ratings, and role-gated review actions.
//
// Domain rules honored here: user strength ratings (1-5, per revision),
// model confidence (0-1, model/system origins only), and review status
// are three separate indicators and are never merged.

import "../styles/pages/assertion-detail.css";

import { useCallback, useEffect, useState } from "react";
import type { ReactElement } from "react";

import { ApiError, api } from "../api/client";
import type {
  AssertionDetail,
  AssertionOrigin,
  EntityRef,
  EvidenceStatus,
  RatingSummary,
  RelatedMatch,
} from "../api/types";
import { Icon } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { AssertionRatingDistribution } from "../components/AssertionRatingDistribution";
import { AssertionRatingWidget } from "../components/AssertionRatingWidget";
import type { AssertionRatingWidgetSaveData } from "../components/AssertionRatingWidget";
import { AssertionReviewPanel } from "../components/AssertionReviewPanel";

const ORIGIN_CHIP: Record<AssertionOrigin, { className: string; label: string }> = {
  user_suggested: { className: "chip chip--user", label: "Colleague" },
  model_suggested: { className: "chip chip--model", label: "AI-deduced" },
  system_generated: { className: "chip chip--system", label: "System" },
};

const EVIDENCE_STATUS_BADGE: Record<EvidenceStatus, { className: string; label: string }> = {
  evidenced: { className: "badge badge--accepted", label: "Evidenced" },
  unsupported: { className: "badge badge--rejected", label: "Unsupported" },
  awaiting_evidence: { className: "badge badge--proposed", label: "Awaiting evidence" },
};

const STANDING_EXPLANATION: Record<string, string> = {
  proposed: "Not enough team ratings yet to derive a standing.",
  weak: "Derived from team strength ratings on the current revision: weak support.",
  probable: "Derived from team strength ratings on the current revision: probable support.",
  strong: "Derived from team strength ratings on the current revision: strong support.",
};

const MATCH_KIND_LABEL: Record<string, string> = {
  exact_proposition: "Exact proposition match",
  same_subject_type_object: "Same subject, type & object",
  similar: "Similar proposition",
};

function labelize(value: string): string {
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function fmtDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function initialsOf(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("") || "?"
  );
}

function evidenceRoleBadge(role: string): string {
  if (role === "supports") return "badge badge--accepted";
  if (role === "contradicts") return "badge badge--rejected";
  return "badge badge--neutral";
}

function EntityChip({ entity }: { entity: EntityRef }): ReactElement {
  return (
    <span className="adp-entity">
      <span className="adp-entity-type">{entity.type ?? "entity"}</span>
      <span className="mono">{entity.id ?? "unknown"}</span>
    </span>
  );
}

export function AssertionDetailPage({ assertionId }: { assertionId: string }) {
  const session = useActiveSession();
  const role = session.role;
  const canContribute = role === "contributor" || role === "reviewer" || role === "admin";
  const canReview = role === "reviewer" || role === "admin";

  const [detail, setDetail] = useState<AssertionDetail | null>(null);
  const [related, setRelated] = useState<RelatedMatch[]>([]);
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [commentDraft, setCommentDraft] = useState("");
  const [postingComment, setPostingComment] = useState(false);

  const refresh = useCallback(() => setReloadKey((key) => key + 1), []);

  // Hard reset when the target assertion (or active matter) changes.
  useEffect(() => {
    setDetail(null);
    setSummary(null);
    setRelated([]);
    setNotFound(false);
    setActionError(null);
    setLoading(true);
  }, [assertionId, session.currentMatter.id]);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    (async () => {
      try {
        const assertion = await api.getAssertion(assertionId);
        if (cancelled) return;
        const [rel, sum] = await Promise.all([
          api.relatedAssertions(assertionId).catch(() => [] as RelatedMatch[]),
          assertion.current_revision_number != null
            ? api
                .ratingSummary(assertionId, assertion.current_revision_number)
                .catch(() => null)
            : Promise.resolve(null),
        ]);
        if (cancelled) return;
        setDetail(assertion);
        setRelated(rel);
        setSummary(sum);
        setNotFound(false);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else {
          setError(err instanceof Error ? err.message : "Failed to load assertion.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [assertionId, session.currentMatter.id, reloadKey]);

  const nameFor = useCallback(
    (userId: string) => (userId === session.user.id ? session.user.display_name : userId),
    [session.user.id, session.user.display_name],
  );

  const handleSaveRating = async ({ strength, rationale }: AssertionRatingWidgetSaveData) => {
    if (!detail || detail.current_revision_number == null) return;
    await api.putRating(detail.id, detail.current_revision_number, strength, rationale);
    setSummary(await api.ratingSummary(detail.id, detail.current_revision_number));
  };

  const handleRemoveRating = async () => {
    if (!detail || detail.current_revision_number == null) return;
    await api.deleteRating(detail.id, detail.current_revision_number);
    setSummary(await api.ratingSummary(detail.id, detail.current_revision_number));
  };

  const runReview = async (action: () => Promise<unknown>) => {
    setActionError(null);
    try {
      await action();
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Review action failed.");
    }
  };

  const handlePostComment = async () => {
    if (!detail) return;
    const text = commentDraft.trim();
    if (!text) return;
    setPostingComment(true);
    setActionError(null);
    try {
      await api.addComment(detail.id, text);
      setCommentDraft("");
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to post comment.");
    } finally {
      setPostingComment(false);
    }
  };

  const backLink = (
    <Link to="/review" className="adp-back">
      <Icon name="arrow-back" size={16} />
      Back to Review Queue
    </Link>
  );

  if (notFound) {
    return (
      <div>
        {backLink}
        <div className="empty-state">
          <p className="empty-state__title">Assertion not found</p>
          <p>This assertion does not exist or is not part of the current matter.</p>
        </div>
      </div>
    );
  }

  if (!detail) {
    if (error) {
      return (
        <div>
          {backLink}
          <div className="error-banner" role="alert">
            {error}
          </div>
          <button type="button" className="btn btn--secondary" onClick={refresh}>
            Retry
          </button>
        </div>
      );
    }
    return <div className="loading">Loading assertion…</div>;
  }

  const origin = ORIGIN_CHIP[detail.origin];
  const evidenceStatus = EVIDENCE_STATUS_BADGE[detail.evidence_status];
  const showStanding = detail.standing !== detail.status;
  const isModelOrigin =
    detail.origin === "model_suggested" || detail.origin === "system_generated";
  const showRawProposition =
    detail.proposition_raw !== null && detail.proposition_raw !== detail.proposition;

  const effectiveWindow =
    detail.effective_from === null && detail.effective_to === null
      ? "—"
      : `${detail.effective_from ? fmtDate(detail.effective_from) : "…"} – ${
          detail.effective_to ? fmtDate(detail.effective_to) : "ongoing"
        }`;

  const distributionSummary = summary ??
    detail.ratings_summary ?? { count: 0, average: null, median: null, distribution: {} };

  const hasRatingsOnPriorRevision =
    summary !== null && summary.count === 0 && (detail.ratings_summary?.count ?? 0) > 0;

  const revisions = [...detail.revision_history].sort(
    (a, b) => b.revision_number - a.revision_number,
  );

  return (
    <div className="adp">
      {backLink}

      <header className="page-header adp-header">
        <div>
          <h1 className="page-header__title">Assertion</h1>
          <div className="adp-meta">
            <span className={`badge badge--${detail.status}`}>{labelize(detail.status)}</span>
            {showStanding && (
              <span className={`badge badge--${detail.standing}`}>
                {labelize(detail.standing)}
              </span>
            )}
            <span className={origin.className}>{origin.label}</span>
            <span className="mono">{detail.id}</span>
            <span className="muted">Created {fmtDate(detail.created_at)}</span>
            <span className="muted">Updated {fmtDate(detail.updated_at)}</span>
          </div>
        </div>
      </header>

      {loading && <div className="adp-refreshing muted">Refreshing…</div>}
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      {actionError && (
        <div className="error-banner" role="alert">
          {actionError}
        </div>
      )}

      <div className="adp-layout">
        <div className="adp-col adp-col--main">
          <section className="card">
            <div className="card__header">Proposition</div>
            <div className="card__body">
              <p className="adp-proposition">{detail.proposition}</p>
              {showRawProposition && (
                <details className="adp-raw">
                  <summary>Authored text</summary>
                  <p className="adp-raw-text">{detail.proposition_raw}</p>
                </details>
              )}
              <div className="adp-entities">
                <EntityChip entity={detail.subject_entity} />
                <span className="adp-relation">
                  {labelize(detail.assertion_type)}
                  <Icon name="chevron-right" size={14} />
                </span>
                {detail.object_entity && <EntityChip entity={detail.object_entity} />}
              </div>
              <dl className="adp-facts">
                <div className="adp-fact">
                  <dt>Jurisdiction</dt>
                  <dd>{detail.jurisdiction ?? "—"}</dd>
                </div>
                <div className="adp-fact">
                  <dt>Effective</dt>
                  <dd>{effectiveWindow}</dd>
                </div>
                {detail.current_revision_number != null && (
                  <div className="adp-fact">
                    <dt>Revision</dt>
                    <dd>v{detail.current_revision_number}</dd>
                  </div>
                )}
              </dl>
            </div>
          </section>

          {isModelOrigin && (
            <section className="card">
              <div className="card__header">Model provenance</div>
              <div className="card__body adp-provenance">
                <div className="adp-provenance-row">
                  <span className={origin.className}>{origin.label}</span>
                  <span className="adp-confidence">
                    Model confidence:{" "}
                    <strong>
                      {detail.confidence != null
                        ? `${Math.round(detail.confidence * 100)}%`
                        : "Not applicable"}
                    </strong>
                  </span>
                </div>
                <p className="adp-note">
                  Model confidence is reported by the extraction pipeline. It is independent
                  of team strength ratings and of the review status.
                </p>
              </div>
            </section>
          )}

          <section className="card">
            <div className="card__header">
              Evidence
              <span className={evidenceStatus.className}>{evidenceStatus.label}</span>
            </div>
            <div className="card__body">
              {detail.evidence.length === 0 ? (
                <p className="muted">No evidence spans are linked to this assertion.</p>
              ) : (
                <ul className="adp-evidence-list">
                  {detail.evidence.map((item) => (
                    <li key={item.id} className="adp-evidence">
                      <span className={evidenceRoleBadge(item.evidence_role)}>
                        {labelize(item.evidence_role)}
                      </span>
                      <span className="mono">{item.source_span_id}</span>
                      <span className="muted adp-evidence-by">
                        added by {nameFor(item.added_by_user_id)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="adp-note">Span text resolution is not yet available.</p>
            </div>
          </section>

          <section className="card">
            <div className="card__header">
              Comments
              <span className="muted adp-count">{detail.comments.length}</span>
            </div>
            <div className="card__body">
              {detail.comments.length === 0 ? (
                <p className="muted">No comments yet. Start the discussion on this assertion.</p>
              ) : (
                <ul className="adp-comment-list">
                  {detail.comments.map((comment) => (
                    <li key={comment.id} className="adp-comment">
                      <span className="avatar" aria-hidden="true">
                        {initialsOf(nameFor(comment.user_id))}
                      </span>
                      <div className="adp-comment-body">
                        <div className="adp-comment-meta">
                          <span className="adp-comment-author">{nameFor(comment.user_id)}</span>
                          <span className="muted">{fmtDateTime(comment.created_at)}</span>
                        </div>
                        {comment.deleted_at ? (
                          <p className="muted adp-comment-removed">[comment removed]</p>
                        ) : (
                          <p className="adp-comment-text">{comment.comment_text}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {canContribute && (
                <div className="field adp-comment-form">
                  <label htmlFor="adp-new-comment">Add a comment</label>
                  <textarea
                    id="adp-new-comment"
                    className="textarea"
                    value={commentDraft}
                    onChange={(event) => setCommentDraft(event.target.value)}
                  />
                  <button
                    type="button"
                    className="btn btn--primary btn--sm adp-comment-submit"
                    onClick={() => void handlePostComment()}
                    disabled={postingComment || commentDraft.trim() === ""}
                  >
                    Post comment
                  </button>
                </div>
              )}
            </div>
          </section>

          <section className="card">
            <div className="card__header">Activity</div>
            <div className="card__body">
              {revisions.length === 0 ? (
                <p className="muted">No revisions recorded yet.</p>
              ) : (
                <ol className="adp-timeline">
                  {revisions.map((revision) => (
                    <li key={revision.id} className="adp-timeline-item">
                      <div className="adp-timeline-title">
                        Revision {revision.revision_number}
                        {revision.revision_number === detail.current_revision_number && (
                          <span className="chip chip--tag">current</span>
                        )}
                      </div>
                      <div className="muted adp-timeline-meta">
                        {nameFor(revision.edited_by_user_id)} ·{" "}
                        {fmtDateTime(revision.created_at)}
                      </div>
                      {revision.revision_reason && (
                        <p className="adp-timeline-reason">{revision.revision_reason}</p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </section>
        </div>

        <div className="adp-col adp-col--side">
          <section className="card">
            <div className="card__header">Ratings</div>
            <div className="card__body">
              <AssertionRatingDistribution
                summary={distributionSummary}
                modelConfidence={null}
              />
              {distributionSummary.count > 0 && distributionSummary.median != null && (
                <p className="muted adp-stats">Median {distributionSummary.median}/5</p>
              )}
              {detail.status === "proposed" && (
                <div className="adp-standing">
                  <span className={`badge badge--${detail.standing}`}>
                    {labelize(detail.standing)}
                  </span>
                  <span className="adp-standing-note">
                    {STANDING_EXPLANATION[detail.standing] ??
                      "Standing is derived from team strength ratings."}
                  </span>
                </div>
              )}
              {canContribute && detail.current_revision_number != null && (
                <div className="adp-rating-widget">
                  <h3 className="adp-subhead">
                    Your rating (v{detail.current_revision_number})
                  </h3>
                  <AssertionRatingWidget
                    key={`${detail.id}:${detail.current_revision_number}`}
                    currentUserRating={summary?.current_user_rating?.strength ?? null}
                    onSave={handleSaveRating}
                    onRemove={handleRemoveRating}
                  />
                  <p className="adp-note">
                    Ratings inform standing only — they never change the review status.
                  </p>
                </div>
              )}
            </div>
          </section>

          {canReview && (
            <section className="card">
              <div className="card__header">Review</div>
              <div className="card__body">
                <AssertionReviewPanel
                  assertion={{
                    id: detail.id,
                    status: detail.status,
                    evidenceStatus: detail.evidence_status,
                    currentRevisionNumber: detail.current_revision_number ?? undefined,
                  }}
                  onAccept={(payload) =>
                    void runReview(() =>
                      api.acceptAssertion(detail.id, payload?.justification || undefined),
                    )
                  }
                  onReject={() => void runReview(() => api.rejectAssertion(detail.id))}
                  onDispute={() => void runReview(() => api.disputeAssertion(detail.id))}
                  onRequestRevision={(payload) =>
                    void runReview(() => api.requestRevision(detail.id, payload.comment))
                  }
                  hasRatingsOnPriorRevision={hasRatingsOnPriorRevision}
                />
              </div>
            </section>
          )}

          <section className="card">
            <div className="card__header">Related assertions</div>
            <div className="card__body">
              {related.length === 0 ? (
                <p className="muted">No related or duplicate assertions found.</p>
              ) : (
                <ul className="adp-related-list">
                  {related.map((match) => (
                    <li key={match.assertion_id} className="adp-related">
                      <Link
                        to={`/assertions/${match.assertion_id}`}
                        className="adp-related-link"
                      >
                        <span className="adp-related-kind">
                          {MATCH_KIND_LABEL[match.match_kind] ?? labelize(match.match_kind)}
                        </span>
                        <span className="mono">{match.assertion_id}</span>
                      </Link>
                      <span className="muted adp-related-score">
                        score {match.score.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
