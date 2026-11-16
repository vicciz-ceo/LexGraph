// Readable handling of the API's 409 answers for assertion authoring
// (backend/app/routers/assertions.py). Errors are duck-typed (`status`,
// `message`, optional parsed `body`), so this works with the real ApiError
// and with the stand-ins page tests substitute for it.
//
// Two kinds of 409 reach the authoring UI:
// - exact duplicate: the detail reads "duplicate: an identical proposition
//   already exists in this matter (assertion <id>)" (create, edit, and
//   submitting a draft); docs/AGENT_GUIDE.md documents reading the id from it.
// - state conflict: the assertion changed since the page loaded it (a stale
//   expected_revision_number, or a status that no longer allows the action).

const DUPLICATE_PREFIX = "duplicate:";
const DUPLICATE_ID = /\(assertion ([^)\s]+)\)/;

export function httpStatusOf(error: unknown): number | null {
  if (error !== null && typeof error === "object" && "status" in error) {
    const status = (error as { status: unknown }).status;
    if (typeof status === "number") return status;
  }
  return null;
}

export interface DuplicateConflict {
  /** The assertion that already holds the proposition, when it could be read. */
  existingAssertionId: string | null;
}

/** The exact-duplicate 409, or null for any other error. A structured
 * `existing_assertion_id` in the response body wins over the id parsed
 * from the detail text. */
export function duplicateConflictOf(error: unknown): DuplicateConflict | null {
  if (httpStatusOf(error) !== 409) return null;
  const message = error instanceof Error ? error.message : "";
  const body = (error as { body?: unknown }).body;
  const structured =
    body !== null && typeof body === "object"
      ? (body as { existing_assertion_id?: unknown }).existing_assertion_id
      : undefined;
  const structuredId = typeof structured === "string" && structured !== "" ? structured : null;
  if (structuredId === null && !message.trim().toLowerCase().startsWith(DUPLICATE_PREFIX)) {
    return null;
  }
  return { existingAssertionId: structuredId ?? DUPLICATE_ID.exec(message)?.[1] ?? null };
}

/** A 409 that means "reload and look again" rather than a duplicate. */
export function isStateConflict(error: unknown): boolean {
  return httpStatusOf(error) === 409 && duplicateConflictOf(error) === null;
}
