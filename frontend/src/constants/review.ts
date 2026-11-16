// Review decision rules and copy shared by the review surfaces: the Review
// Queue and the assertion detail page (through AssertionReviewPanel) and the
// Contested page. They mirror the API's rules (backend/app/routers/review.py,
// spec addendum "Review decision rules (2026-11-16)") so the UI only offers
// decisions the API will record and only sends text it will accept.
//
// Kept out of api/client.ts on purpose: page tests mock that module with a
// factory that returns only { ApiError, api }.

/**
 * Statuses a review decision can be recorded from. A draft has not been
 * submitted for review, a withdrawn assertion was retracted by its author and
 * a superseded one is terminal; the API refuses decisions on them with 409.
 */
export const DECIDABLE_STATUSES: readonly string[] = [
  "proposed",
  "revision_requested",
  "disputed",
  "accepted",
  "rejected",
];

/**
 * Whether a decision that moves an assertion to `target` can be recorded
 * while it is in `status`. Repeating the current status is refused too.
 */
export function canDecide(status: string, target: string): boolean {
  return DECIDABLE_STATUSES.includes(status) && status !== target;
}

/** Longest review text (acceptance justification, revision comment) the API stores. */
export const REVIEW_TEXT_MAX_LENGTH = 100_000;

/**
 * The problem with sending `text` as a required review text, or null when it
 * can be sent. The UI sends the trimmed text; the API refuses it with 422 when
 * it is blank or longer than REVIEW_TEXT_MAX_LENGTH characters. Blank text is
 * reported as "required" so a form can say why its Confirm is disabled.
 */
export function reviewTextProblem(text: string): "required" | "too_long" | null {
  const trimmed = text.trim();
  if (trimmed === "") return "required";
  // The API counts characters (code points); a UTF-16 length within the
  // limit is always within it, so only count when it might not be.
  if (trimmed.length > REVIEW_TEXT_MAX_LENGTH && Array.from(trimmed).length > REVIEW_TEXT_MAX_LENGTH) {
    return "too_long";
  }
  return null;
}

/** Inline message for review text over the length limit. */
export function reviewTextTooLongMessage(text: string): string {
  const length = Array.from(text.trim()).length;
  return (
    `This text is ${length.toLocaleString("en-US")} characters long; ` +
    `the limit is ${REVIEW_TEXT_MAX_LENGTH.toLocaleString("en-US")}.`
  );
}

/**
 * Notice for a decision the API refused with 409: the assertion was edited,
 * withdrawn or decided by someone else after the page loaded it. The page
 * reloads it, so the reviewer sees the current version before deciding again.
 */
export const REVIEW_CONFLICT_MESSAGE =
  "Your decision was not recorded: this assertion changed after you opened it " +
  "(it was edited, withdrawn or decided by someone else). The current version is " +
  "now shown; review it before deciding.";

/** REVIEW_CONFLICT_MESSAGE followed by the API's own reason, when it gave one. */
export function reviewConflictNotice(detail: string): string {
  const reason = detail.trim().replace(/\.+$/, "");
  return reason ? `${REVIEW_CONFLICT_MESSAGE} Reason: ${reason}.` : REVIEW_CONFLICT_MESSAGE;
}
