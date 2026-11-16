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

/** Why a decision cannot be recorded on an assertion in a status that takes
 * none (the API's "cannot <verb> an assertion in status '<status>'"). */
const UNDECIDABLE_REASONS: Record<string, string> = {
  draft: "it is a draft that has not been submitted for review",
  withdrawn: "its author withdrew it",
  superseded: "it was superseded by another assertion",
};

/** The status a decision would repeat (the API's "assertion is already '<status>'"). */
const ALREADY_REASONS: Record<string, string> = {
  revision_requested: "a revision of it is already requested",
};

/**
 * The reason a review decision was refused with 409, in the words of the
 * review pages, from the API's `detail` (backend/app/routers/review.py). The
 * API names its own request fields and status values there ("assertion has
 * been modified since expected_revision_number"), which mean nothing to a
 * reviewer. A detail this does not know is kept as the API gave it.
 */
function conflictReason(detail: string): string {
  if (/\bmodified since expected_revision_number$/.test(detail)) return "it was edited";
  if (detail.startsWith("assertion was changed by another request")) {
    return "someone else changed it at the same moment";
  }
  const already = /^assertion is already '([a-z_]+)'$/.exec(detail);
  if (already) {
    const status = already[1];
    return ALREADY_REASONS[status] ?? `it is already ${status.replace(/_/g, " ")}`;
  }
  const undecidable = /^cannot .+ an assertion in status '([a-z_]+)'/.exec(detail);
  if (undecidable) {
    const status = undecidable[1];
    return UNDECIDABLE_REASONS[status] ?? `it is now ${status.replace(/_/g, " ")}`;
  }
  return detail;
}

/** The API's exact-duplicate 409 (services/duplicates.py). */
const DUPLICATE_DETAIL = /^duplicate: an identical proposition already exists in this matter(?: \((assertion [^)\s]+)\))?$/;

/**
 * Notice for a review decision the API refused with 409: REVIEW_CONFLICT_MESSAGE
 * and the reason in plain words. Reviving a rejected assertion is also refused
 * when an identical proposition went live meanwhile; that notice says so
 * instead, as nothing about this assertion changed.
 */
export function reviewConflictNotice(detail: string): string {
  const text = detail.trim().replace(/\.+$/, "");
  const duplicate = DUPLICATE_DETAIL.exec(text);
  if (duplicate) {
    const existing = duplicate[1] ? ` (${duplicate[1]})` : "";
    return (
      "Your decision was not recorded: an identical proposition is already live in this " +
      `matter${existing}, and this decision would make a second one live. The current ` +
      "version is now shown."
    );
  }
  return text ? `${REVIEW_CONFLICT_MESSAGE} Reason: ${conflictReason(text)}.` : REVIEW_CONFLICT_MESSAGE;
}

/**
 * Notice for an acceptance sent without a justification that the API refused
 * with 422 because the assertion has no supporting evidence: the page showed
 * evidence that was removed after it loaded. Adding or removing evidence
 * changes neither the revision nor `updated_at`, so `expected_revision_number`
 * cannot catch it. The page reloads the assertion and asks for the
 * justification such an acceptance needs (review fe-review-detail:2).
 */
export const REVIEW_EVIDENCE_REMOVED_MESSAGE =
  "Your decision was not recorded: this assertion no longer has supporting evidence " +
  "(it was removed after you opened it). The current version is now shown; record a " +
  "justification to accept it.";
