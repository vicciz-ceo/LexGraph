import type { ReactElement } from "react";

import { AssertionRatingDistribution } from "./AssertionRatingDistribution";
import { AssertionRatingWidget } from "./AssertionRatingWidget";

// UI1 — assertion card (spec §5, §14). Displays status, origin, model
// confidence, and evidence status as distinct labeled values, and keeps
// "your rating" separate from "team rating" and from model confidence
// (spec §5: never merge the team rating and model confidence into one
// indicator). Types are local to this file (sprint ruling R7).

export interface AssertionCardRatingSummary {
  count: number;
  average: number | null;
  median: number | null;
  distribution: Record<string, number>;
}

export interface AssertionCardData {
  id: string;
  proposition: string;
  status: string;
  // Sprint 2026-07-30-ratings-grade, item UI1: derived standing (the
  // proposed-until-rated, then weak/probable/strong grade -- ruling R4).
  // Optional so existing callers/fixtures that only set `status` keep
  // working; falls back to `status` when absent.
  standing?: string;
  origin: string;
  confidence: number | null;
  evidenceStatus: string;
  evidenceCount: number;
  ratingSummary: AssertionCardRatingSummary;
  currentUserRating: number | null;
}

export interface AssertionCardProps {
  assertion: AssertionCardData;
  onRatingSave?: (data: { strength: number; rationale: string }) => void | Promise<void>;
  onRatingRemove?: () => void | Promise<void>;
}

const STRENGTH_LABELS: Record<number, string> = {
  1: "Very weak",
  2: "Weak",
  3: "Plausible or mixed",
  4: "Strong",
  5: "Very strong",
};

function humanize(value: string): string {
  return value
    .split("_")
    .map((word, index) =>
      index === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word
    )
    .join(" ");
}

function formatConfidence(confidence: number | null): string {
  if (confidence === null) {
    return "Not applicable";
  }
  return `${Math.round(confidence * 100)}%`;
}

function formatEvidenceStatus(evidenceStatus: string, evidenceCount: number): string {
  if (evidenceStatus === "unsupported" || evidenceStatus === "awaiting_evidence") {
    return humanize(evidenceStatus);
  }
  return `${evidenceCount} supporting span${evidenceCount === 1 ? "" : "s"}`;
}

export function AssertionCard({
  assertion,
  onRatingSave,
  onRatingRemove,
}: AssertionCardProps): ReactElement {
  const {
    proposition,
    status,
    standing,
    origin,
    confidence,
    evidenceStatus,
    evidenceCount,
    ratingSummary,
    currentUserRating,
  } = assertion;

  const yourRatingText =
    currentUserRating != null
      ? `Your rating: ${currentUserRating} — ${STRENGTH_LABELS[currentUserRating] ?? ""}`
      : "Your rating: not yet rated";

  return (
    <article className="assertion-card">
      <p className="assertion-card__proposition">{proposition}</p>

      <dl className="assertion-card__meta">
        <div className="assertion-card__meta-row">
          <dt>Status</dt>
          <dd>{humanize(status)}</dd>
        </div>
        {standing != null && (
          <div className="assertion-card__meta-row">
            <dt>Standing</dt>
            <dd data-testid="assertion-standing">{humanize(standing)}</dd>
          </div>
        )}
        <div className="assertion-card__meta-row">
          <dt>Origin</dt>
          <dd>{humanize(origin)}</dd>
        </div>
        <div className="assertion-card__meta-row">
          <dt>Model confidence</dt>
          <dd>{formatConfidence(confidence)}</dd>
        </div>
        <div className="assertion-card__meta-row">
          <dt>Evidence</dt>
          <dd>{formatEvidenceStatus(evidenceStatus, evidenceCount)}</dd>
        </div>
      </dl>

      <div className="assertion-card__your-rating">
        <span className="assertion-card__your-rating-label">{yourRatingText}</span>
        <AssertionRatingWidget
          currentUserRating={currentUserRating}
          onSave={onRatingSave ?? (() => {})}
          onRemove={onRatingRemove ?? (() => {})}
        />
      </div>

      <AssertionRatingDistribution summary={ratingSummary} modelConfidence={confidence} />

      <p className="assertion-card__disclaimer">
        Ratings reflect individual users&apos; opinions about assertion strength and do not
        constitute formal legal conclusions.
      </p>
    </article>
  );
}
