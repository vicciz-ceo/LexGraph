// Per-user preferences kept in this browser's localStorage.
//
// The default jurisdiction is chosen on the Profile page
// (pages/ProfilePage.tsx stores it under `lexgraph:default-jurisdiction:<userId>`)
// and read here, read-only, to pre-select the Suggest Assertion form's
// jurisdiction. ProfilePage's tests pin the same key on the writer side.

import { JURISDICTION_CODES } from "./jurisdictions";

export function defaultJurisdictionStorageKey(userId: string): string {
  return `lexgraph:default-jurisdiction:${userId}`;
}

/** The user's saved default jurisdiction, or "" when none is saved, storage
 * is unavailable, or the stored value is not in the controlled vocabulary
 * (the API would reject it). */
export function readDefaultJurisdiction(userId: string): string {
  try {
    const value = window.localStorage.getItem(defaultJurisdictionStorageKey(userId)) ?? "";
    return JURISDICTION_CODES.includes(value) ? value : "";
  } catch {
    return "";
  }
}
