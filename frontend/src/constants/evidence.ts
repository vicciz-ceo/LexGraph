// Evidence-role vocabulary (spec §2), shared by the detail page and the
// evidence selector. Kept outside api/client.ts so page tests that mock the
// client module still get the real values.

/** The roles POST /assertions/{id}/evidence accepts, in display order. */
export const EVIDENCE_ROLES = [
  "supports",
  "contradicts",
  "contextualizes",
  "qualifies",
  "primary_basis",
  "secondary_basis",
] as const;

export type EvidenceRole = (typeof EVIDENCE_ROLES)[number];

export const EVIDENCE_ROLE_LABELS: Record<EvidenceRole, string> = {
  supports: "Supports",
  contradicts: "Contradicts",
  contextualizes: "Contextualizes",
  qualifies: "Qualifies",
  primary_basis: "Primary basis",
  secondary_basis: "Secondary basis",
};

/** Roles that make an assertion "evidenced" (the backend's
 * SUPPORTING_EVIDENCE_ROLES); the other roles leave it "unsupported". */
export const SUPPORTING_EVIDENCE_ROLES: ReadonlySet<string> = new Set([
  "supports",
  "primary_basis",
  "secondary_basis",
]);

/** "Primary basis"; an unknown role is shown with its words spaced out. */
export function evidenceRoleLabel(role: string): string {
  const known = EVIDENCE_ROLE_LABELS[role as EvidenceRole];
  if (known) return known;
  const spaced = role.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** Statuses in which the author (with contributor membership) may still
 * change an assertion and its evidence (spec §12, the edit rule). */
export const UNREVIEWED_STATUSES: ReadonlySet<string> = new Set([
  "draft",
  "proposed",
  "revision_requested",
]);
