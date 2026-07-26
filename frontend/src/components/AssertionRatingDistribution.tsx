import type { ReactElement } from "react";

// UI1 — team rating summary display (spec §4-5). Deliberately keeps the
// aggregate team rating and model confidence as two separate indicators
// (spec §5: "Never visually merge the team rating and model confidence
// into one indicator"). Types are local to this file (sprint ruling R7).

export interface AssertionRatingDistributionSummary {
  count: number;
  average: number | null;
  median: number | null;
  distribution: Record<string, number>;
}

export interface AssertionRatingDistributionProps {
  summary: AssertionRatingDistributionSummary;
  modelConfidence: number | null;
}

const BUCKETS = ["1", "2", "3", "4", "5"];

export function AssertionRatingDistribution({
  summary,
  modelConfidence,
}: AssertionRatingDistributionProps): ReactElement {
  const average = summary.average;
  const hasRatings = summary.count > 0 && average !== null;

  return (
    <div className="assertion-rating-distribution">
      {hasRatings && average !== null ? (
        <div
          className="assertion-rating-distribution__team-rating"
          data-testid="team-rating-indicator"
          data-metric="team-rating"
        >
          <span className="assertion-rating-distribution__label">Team rating</span>
          <span className="assertion-rating-distribution__value">
            <strong>{average.toFixed(1)}</strong>
            {"/5 based on "}
            {summary.count}
            {summary.count === 1 ? " rating" : " ratings"}
          </span>
          <ul
            className="assertion-rating-distribution__buckets"
            aria-label="Rating distribution, 1 to 5"
          >
            {BUCKETS.map((bucket) => (
              <li key={bucket} data-testid={`rating-distribution-bucket-${bucket}`}>
                <span className="assertion-rating-distribution__bucket-label">{bucket}</span>
                <span className="assertion-rating-distribution__bucket-count">
                  {summary.distribution[bucket] ?? 0}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="assertion-rating-distribution__empty">No ratings yet.</p>
      )}

      {modelConfidence !== null && (
        <div
          className="assertion-rating-distribution__model-confidence"
          data-testid="model-confidence-indicator"
          data-metric="model-confidence"
        >
          <span className="assertion-rating-distribution__label">Model confidence</span>
          <span className="assertion-rating-distribution__value">
            {Math.round(modelConfidence * 100)}%
          </span>
        </div>
      )}
    </div>
  );
}
