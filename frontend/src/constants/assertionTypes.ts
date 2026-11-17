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

/** Longest type name the API stores, in characters: the column's 255
 * (backend NEW_ASSERTION_TYPE_MAX_LENGTH). Upper case can make a name longer
 * than it was typed (ß becomes SS, ﬃ becomes FFI), so normalizeAssertionType
 * cuts a longer name here. */
export const ASSERTION_TYPE_STORED_MAX_LENGTH = 255;

export function isRecognizedAssertionType(value: string): boolean {
  return ASSERTION_TYPES.includes(value);
}

/** Canonical spelling of a typed type name: "cancelled by" and
 * "Cancelled-By" both become "CANCELLED_BY", the shape of the controlled
 * vocabulary. Letters of any script and digits are kept; every other run
 * of characters becomes one underscore. A name longer than the API stores
 * is cut at ASSERTION_TYPE_STORED_MAX_LENGTH characters. */
export function normalizeAssertionType(raw: string): string {
  const name = raw
    .trim()
    .toUpperCase()
    .replace(/[^\p{L}\p{N}]+/gu, "_")
    .replace(/^_+|_+$/g, "");
  const characters = Array.from(name); // code points, as the API counts them
  return characters.length <= ASSERTION_TYPE_STORED_MAX_LENGTH
    ? name
    : characters.slice(0, ASSERTION_TYPE_STORED_MAX_LENGTH).join("").replace(/_+$/, "");
}

/** "CREATES_EXCEPTION_TO" -> "Creates exception to". */
export function assertionTypeLabel(type: string): string {
  const words = type.toLowerCase().split("_").filter(Boolean).join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
