// Assertion-type controlled vocabulary: a TypeScript mirror of
// ALLOWED_ASSERTION_TYPES in backend/app/services/validation.py, in the
// same order. The backend stays the enforcement point; the drift guard
// backend/tests/integration/test_suggest_ui_contract.py parses this file
// and fails when the two lists differ.
//
// Spec §7: an assertion type must come from this vocabulary or be
// explicitly marked as a proposed new type (the API's
// `assertion_type_is_proposed_new` flag).

export const ASSERTION_TYPES: readonly string[] = [
  "INTERPRETS",
  "CREATES_EXCEPTION_TO",
  "CONFLICTS_WITH",
  "MODIFIES",
  "APPLIES_TO",
  "RELEVANT_TO",
  "WEAKENS",
  "SUPPORTS",
  "SURVIVES_TERMINATION",
  "DISTINGUISHABLE_FROM",
  "USES_DEFINITION",
  "DERIVES_FROM_LAW",
];

/** Longest proposed type name the form accepts (the column holds 255). */
export const NEW_ASSERTION_TYPE_MAX_LENGTH = 100;

export function isRecognizedAssertionType(value: string): boolean {
  return ASSERTION_TYPES.includes(value);
}

/** Canonical spelling of a typed type name: "cancelled by" and
 * "Cancelled-By" both become "CANCELLED_BY", the shape of the controlled
 * vocabulary. Letters of any script and digits are kept; every other run
 * of characters becomes one underscore. */
export function normalizeAssertionType(raw: string): string {
  return raw
    .trim()
    .toUpperCase()
    .replace(/[^\p{L}\p{N}]+/gu, "_")
    .replace(/^_+|_+$/g, "");
}

/** "CREATES_EXCEPTION_TO" -> "Creates exception to". */
export function assertionTypeLabel(type: string): string {
  const words = type.toLowerCase().split("_").filter(Boolean).join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
