// Helpers for the Suggest Assertion flow that are shared by the page and
// the form (kept out of api/client so page tests can mock the client).

import type { AssertionStatus, SimilarAssertionsPayload } from "../api/types";

/** The backend lists at most this many similar assertions; the page never
 * shows more, even when an older backend sends an uncapped list. */
export const SIMILAR_ASSERTIONS_DISPLAY_LIMIT = 20;

export interface SimilarAssertionMatch {
  id: string;
  /** Text of the existing assertion; "" until it is known (older backends
   * do not send it). Never rendered as empty quotes. */
  proposition: string;
  status: AssertionStatus | null;
  matchKind: string;
  score: number;
}

export interface SimilarAssertionsSummary {
  /** Top matches by score (desc), then id: at most the display limit. */
  items: SimilarAssertionMatch[];
  /** Every match, including those not listed. */
  total: number;
}

/** Normalize a create response's similar-assertion fields. Tolerates older
 * backends (no proposition/status, no total, no cap). */
export function summarizeSimilarAssertions(payload: SimilarAssertionsPayload): SimilarAssertionsSummary {
  const raw = Array.isArray(payload.similar_assertions) ? payload.similar_assertions : [];
  const seen = new Set<string>();
  const items: SimilarAssertionMatch[] = [];
  for (const match of raw) {
    const id = match && typeof match.assertion_id === "string" ? match.assertion_id : "";
    if (id === "" || seen.has(id)) continue;
    seen.add(id);
    items.push({
      id,
      proposition: typeof match.proposition === "string" ? match.proposition : "",
      status: match.status ?? null,
      matchKind: typeof match.match_kind === "string" ? match.match_kind : "similar",
      score: typeof match.score === "number" ? match.score : 0,
    });
  }
  items.sort((a, b) => b.score - a.score || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const reportedTotal =
    typeof payload.similar_assertions_total === "number" ? payload.similar_assertions_total : 0;
  return {
    items: items.slice(0, SIMILAR_ASSERTIONS_DISPLAY_LIMIT),
    total: Math.max(reportedTotal, items.length),
  };
}

/** Recorded in the explanation (stored as the assertion's first comment)
 * when the author ticks "Further evidence needed"; there is no separate
 * field for it in the API. */
export const FURTHER_EVIDENCE_NOTE =
  "Further evidence needed: the author marked this assertion as needing more supporting evidence.";

/** The explanation to send: the author's text, plus the further-evidence
 * note when it was requested; null when there is nothing to send. */
export function composeExplanation(explanation: string, needsFurtherEvidence: boolean): string | null {
  const parts = [explanation.trim(), needsFurtherEvidence ? FURTHER_EVIDENCE_NOTE : ""].filter(
    (part) => part !== "",
  );
  return parts.length > 0 ? parts.join("\n\n") : null;
}

/** Status labels for similar-assertion badges. */
export const STATUS_LABELS: Record<AssertionStatus, string> = {
  draft: "Draft",
  proposed: "Proposed",
  revision_requested: "Revision requested",
  accepted: "Accepted",
  rejected: "Rejected",
  disputed: "Disputed",
  superseded: "Superseded",
  withdrawn: "Withdrawn",
};
