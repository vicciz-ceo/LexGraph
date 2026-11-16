// Individual rating rationales for one revision (spec §5 "Individual rating
// rationales, subject to permissions", §10; finding ui:16). The permission
// stays server-side: GET .../ratings returns every rater's rationale to roles
// holding assertion:view_rating_rationales and `null` for other raters'
// rationale text to everyone else, so this list renders exactly the
// rationales the API returned. Ratings without a rationale are not listed,
// so a role limited to aggregates sees no other user's individual strength.

import type { ReactElement } from "react";

import type { Rating } from "../api/types";
import { strengthLabel } from "../constants/ratings";

export interface AssertionRatingRationalesProps {
  /** `null` when the list could not be loaded. */
  ratings: Rating[] | null;
  /** Ratings on the revision and how many of them carry a rationale. */
  ratingCount: number;
  rationaleCount: number | null;
  currentUserId: string;
  nameFor: (userId: string) => string;
  formatDate: (iso: string | null) => string;
}

export function AssertionRatingRationales({
  ratings,
  ratingCount,
  rationaleCount,
  currentUserId,
  nameFor,
  formatDate,
}: AssertionRatingRationalesProps): ReactElement | null {
  if (ratingCount === 0) return null;
  const withText = (ratings ?? []).filter((r) => r.rationale !== null && r.rationale.trim() !== "");
  const hidden = ratings !== null && rationaleCount !== null && withText.length < rationaleCount;
  return (
    <div className="adp-rationales">
      {rationaleCount !== null && (
        <p className="muted adp-rationale-count">
          {`${rationaleCount} of ${ratingCount} ${ratingCount === 1 ? "rating" : "ratings"} on this revision ${
            rationaleCount === 1 ? "includes" : "include"
          } a rationale.`}
        </p>
      )}
      {ratings === null ? (
        <p className="muted">Rating rationales could not be loaded.</p>
      ) : (
        withText.length > 0 && (
          <ul className="adp-rationale-list" aria-label="Rating rationales">
            {withText.map((r) => (
              <li key={r.id} className="adp-rationale">
                <div className="adp-rationale-meta">
                  <span className="adp-rationale-author">
                    {r.user_id === currentUserId ? `${nameFor(r.user_id)} (you)` : nameFor(r.user_id)}
                  </span>
                  <span className="muted">
                    {strengthLabel(r.strength)} · {formatDate(r.updated_at ?? r.created_at)}
                  </span>
                </div>
                <p className="adp-rationale-text">{r.rationale}</p>
              </li>
            ))}
          </ul>
        )
      )}
      {hidden && (
        <p className="muted adp-rationale-hidden">
          Other raters' rationales are visible to reviewers and admins.
        </p>
      )}
    </div>
  );
}
