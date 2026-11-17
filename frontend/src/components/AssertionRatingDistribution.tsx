import type { ReactElement } from "react";

import { STRENGTH_LABELS } from "../constants/ratings";

// UI1 — team rating summary display (spec §4-5). Deliberately keeps the
// aggregate team rating and model confidence as two separate indicators
// (spec §5: "Never visually merge the team rating and model confidence
// into one indicator"). Types are local to this file (sprint ruling R7).
//
// Every bucket carries an accessible name ("5 (Very strong): 2 of 3
// ratings") so the value and its count are never read together as one
// number (finding ui:29). The `detailed` variant (assertion detail page)
// also prints each strength's name and a bar sized by its share.

export interface AssertionRatingDistributionSummary {
  count: number;
  average: number | null;
  median: number | null;
  distribution: Record<string, number>;
}

export interface AssertionRatingDistributionProps {
  summary: AssertionRatingDistributionSummary;
  modelConfidence: number | null;
  /** Show strength names and proportional bars (one row per bucket). */
  detailed?: boolean;
}

const BUCKETS = ["1", "2", "3", "4", "5"];

function bucketName(bucket: string, count: number, total: number): string {
  return `${bucket} (${STRENGTH_LABELS[Number(bucket)]}): ${count} of ${total} ${total === 1 ? "rating" : "ratings"}`;
}

export function AssertionRatingDistribution({
  summary,
  modelConfidence,
  detailed = false,
}: AssertionRatingDistributionProps): ReactElement {
  const average = summary.average;
  const hasRatings = summary.count > 0 && average !== null;

  return (
    <div
      className={
        detailed
          ? "assertion-rating-distribution assertion-rating-distribution--detailed"
          : "assertion-rating-distribution"
      }
    >
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
            {BUCKETS.map((bucket) => {
              const count = summary.distribution[bucket] ?? 0;
              const share = summary.count > 0 ? Math.min(1, count / summary.count) : 0;
              return (
                <li
                  key={bucket}
                  data-testid={`rating-distribution-bucket-${bucket}`}
                  aria-label={bucketName(bucket, count, summary.count)}
                  title={bucketName(bucket, count, summary.count)}
                >
                  <span className="assertion-rating-distribution__bucket-label">{bucket}</span>
                  {detailed && (
                    <>
                      <span className="assertion-rating-distribution__bucket-name">
                        {STRENGTH_LABELS[Number(bucket)]}
                      </span>
                      <span className="assertion-rating-distribution__bucket-bar" aria-hidden="true">
                        {count > 0 && (
                          <span
                            className="assertion-rating-distribution__bucket-fill"
                            style={{ width: `${share * 100}%` }}
                          />
                        )}
                      </span>
                    </>
                  )}
                  <span className="assertion-rating-distribution__bucket-count">{count}</span>
                </li>
              );
            })}
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
