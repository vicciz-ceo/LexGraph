// UI3 — assertion detail workspace with tabs (spec §5, §14). Local types
// only for this component (sprint ruling R7 — no shared types module); the
// shapes below intentionally line up structurally with the sibling UI3
// components so the same data can be passed through without adapters.

import { useState } from "react";

import { AssertionComments, type AssertionCommentItem } from "./AssertionComments";
import {
  AssertionRevisionHistory,
  type AssertionRevisionSummary,
} from "./AssertionRevisionHistory";
import {
  RelatedAssertionsPanel,
  type AssertionRelation,
  type RelatedAssertionItem,
} from "./RelatedAssertionsPanel";

export interface AssertionDetailEntityRef {
  type: string;
  id: string;
  label: string;
}

export interface AssertionDetailSummary {
  id: string;
  proposition: string;
  assertionType: string;
  subjectEntity?: AssertionDetailEntityRef | null;
  objectEntity?: AssertionDetailEntityRef | null;
  author: string;
  createdAt?: string;
  currentRevisionNumber?: number;
  jurisdiction?: string | null;
  effectiveFrom?: string | null;
  effectiveTo?: string | null;
  status: string;
  // Sprint 2026-07-30-ratings-grade, item UI1: derived standing (the
  // proposed-until-rated, then weak/probable/strong grade -- ruling R4).
  // Optional so existing callers/fixtures that only set `status` keep
  // working; falls back to `status` when absent.
  standing?: string;
  origin: string;
  confidence?: number | null;
  evidenceStatus: string;
}

export interface AssertionDetailRatingSummary {
  count: number;
  average: number | null;
  median: number | null;
  distribution: Record<string, number>;
}

export interface AssertionDetailEvidenceItem {
  id: string;
  label: string;
}

export interface AssertionDetailReviewHistoryItem {
  id: string;
  decision: string;
  reviewer: string;
  date?: string;
  comment?: string;
}

const TAB_LABELS = [
  "Overview",
  "Evidence",
  "Ratings",
  "Discussion",
  "Revision history",
  "Related assertions",
  "Review history",
] as const;

type TabLabel = (typeof TAB_LABELS)[number];

export interface AssertionDetailPanelProps {
  assertion: AssertionDetailSummary;
  ratingSummary?: AssertionDetailRatingSummary;
  currentUserRating?: number | null;
  revisions?: AssertionRevisionSummary[];
  supportingEvidence?: AssertionDetailEvidenceItem[];
  contradictingEvidence?: AssertionDetailEvidenceItem[];
  comments?: AssertionCommentItem[];
  currentUserId?: string;
  onAddComment?: (commentText: string) => void;
  onEditComment?: (commentId: string, commentText: string) => void;
  onDeleteComment?: (commentId: string) => void;
  related?: RelatedAssertionItem[];
  onOpenRelated?: (assertionId: string) => void;
  onRateInstead?: (assertionId: string) => void;
  onMarkRelation?: (assertionId: string, relation: AssertionRelation) => void;
  reviewHistory?: AssertionDetailReviewHistoryItem[];
  onCompareRevisions?: (leftRevisionNumber: number, rightRevisionNumber: number) => void;
}

const RATING_DISCLAIMER =
  "Ratings reflect users' individual opinions and do not constitute a formal legal conclusion.";

export function AssertionDetailPanel({
  assertion,
  ratingSummary,
  currentUserRating = null,
  revisions = [],
  supportingEvidence = [],
  contradictingEvidence = [],
  comments,
  currentUserId = "",
  onAddComment = () => {},
  onEditComment = () => {},
  onDeleteComment = () => {},
  related,
  onOpenRelated = () => {},
  onRateInstead = () => {},
  onMarkRelation = () => {},
  reviewHistory = [],
  onCompareRevisions = () => {},
}: AssertionDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabLabel>("Overview");

  return (
    <div className="assertion-detail-panel">
      <div role="tablist" aria-label="Assertion workspace">
        {TAB_LABELS.map((label) => (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={activeTab === label}
            onClick={() => setActiveTab(label)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "Overview" && (
        <div role="tabpanel" aria-label="Overview">
          <p className="assertion-detail-proposition">{assertion.proposition}</p>

          <dl className="assertion-detail-fields">
            <dt>Assertion type</dt>
            <dd>{assertion.assertionType}</dd>

            <dt>Subject</dt>
            <dd>{assertion.subjectEntity?.label ?? "—"}</dd>

            {assertion.objectEntity && (
              <>
                <dt>Object</dt>
                <dd>{assertion.objectEntity.label}</dd>
              </>
            )}

            <dt>Author</dt>
            <dd>{assertion.author}</dd>

            <dt>Created</dt>
            <dd>{assertion.createdAt ?? "—"}</dd>

            <dt>Current revision</dt>
            <dd>{assertion.currentRevisionNumber ?? "—"}</dd>

            <dt>Jurisdiction</dt>
            <dd>{assertion.jurisdiction ?? "Not specified"}</dd>

            <dt>Effective from</dt>
            <dd>{assertion.effectiveFrom ?? "—"}</dd>

            <dt>Effective to</dt>
            <dd>{assertion.effectiveTo ?? "—"}</dd>
          </dl>

          {/* Model confidence, review status, evidence status, and origin are
              deliberately rendered as separate indicators (spec §5: "Never
              visually merge the team rating and model confidence into one
              indicator"). */}
          <ul className="assertion-detail-status-indicators">
            <li data-indicator="model-confidence">
              Model confidence:{" "}
              {assertion.confidence === null || assertion.confidence === undefined
                ? "Not applicable"
                : assertion.confidence}
            </li>
            <li data-indicator="review-status">Review status: {assertion.status}</li>
            <li data-indicator="standing">Standing: {assertion.standing ?? assertion.status}</li>
            <li data-indicator="evidence-status">Evidence status: {assertion.evidenceStatus}</li>
            <li data-indicator="origin">Origin: {assertion.origin}</li>
          </ul>

          <p className="assertion-detail-rating-disclaimer">{RATING_DISCLAIMER}</p>
        </div>
      )}

      {activeTab === "Evidence" && (
        <div role="tabpanel" aria-label="Evidence">
          <section aria-label="Supporting evidence">
            <h3>Supporting evidence</h3>
            {supportingEvidence.length > 0 ? (
              <ul>
                {supportingEvidence.map((item) => (
                  <li key={item.id}>{item.label}</li>
                ))}
              </ul>
            ) : (
              <p>No supporting evidence attached.</p>
            )}
          </section>
          <section aria-label="Contradicting evidence">
            <h3>Contradicting evidence</h3>
            {contradictingEvidence.length > 0 ? (
              <ul>
                {contradictingEvidence.map((item) => (
                  <li key={item.id}>{item.label}</li>
                ))}
              </ul>
            ) : (
              <p>No contradicting evidence attached.</p>
            )}
          </section>
        </div>
      )}

      {activeTab === "Ratings" && (
        <div role="tabpanel" aria-label="Ratings">
          {ratingSummary && ratingSummary.count > 0 ? (
            <>
              <p className="assertion-detail-team-rating">
                Team strength rating: {ratingSummary.average !== null ? ratingSummary.average.toFixed(1) : "—"} out
                of 5 based on {ratingSummary.count} ratings
              </p>
              <p className="assertion-detail-median-rating">
                Median: {ratingSummary.median ?? "—"}
              </p>
              <ul className="assertion-detail-rating-distribution">
                {Object.entries(ratingSummary.distribution).map(([value, count]) => (
                  <li key={value}>
                    {value} stars: {count}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p>No ratings yet.</p>
          )}
          <p className="assertion-detail-your-rating">
            Your strength rating: {currentUserRating !== null ? currentUserRating : "Not yet rated"}
          </p>
          <p className="assertion-detail-rating-disclaimer">{RATING_DISCLAIMER}</p>
        </div>
      )}

      {activeTab === "Discussion" && (
        <div role="tabpanel" aria-label="Discussion">
          {comments ? (
            <AssertionComments
              comments={comments}
              currentUserId={currentUserId}
              onAdd={onAddComment}
              onEdit={onEditComment}
              onDelete={onDeleteComment}
            />
          ) : (
            <p>No discussion yet.</p>
          )}
        </div>
      )}

      {activeTab === "Revision history" && (
        <div role="tabpanel" aria-label="Revision history">
          <AssertionRevisionHistory revisions={revisions} onCompare={onCompareRevisions} />
        </div>
      )}

      {activeTab === "Related assertions" && (
        <div role="tabpanel" aria-label="Related assertions">
          {related && related.length > 0 ? (
            <RelatedAssertionsPanel
              related={related}
              onOpen={onOpenRelated}
              onRateInstead={onRateInstead}
              onMarkRelation={onMarkRelation}
            />
          ) : (
            <p>No related assertions found.</p>
          )}
        </div>
      )}

      {activeTab === "Review history" && (
        <div role="tabpanel" aria-label="Review history">
          {reviewHistory.length > 0 ? (
            <ul>
              {reviewHistory.map((entry) => (
                <li key={entry.id}>
                  {entry.decision} — {entry.reviewer}
                  {entry.date ? ` (${entry.date})` : ""}
                  {entry.comment ? `: ${entry.comment}` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p>No review history yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
