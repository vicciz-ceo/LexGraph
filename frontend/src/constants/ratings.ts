// Strength-rating vocabulary (spec §4), shared by the rating widget, the
// distribution and the rationale list. Kept outside api/client.ts so page
// tests that mock the client module still get the real labels.

export const STRENGTH_VALUES = [1, 2, 3, 4, 5] as const;

export const STRENGTH_LABELS: Record<number, string> = {
  1: "Very weak",
  2: "Weak",
  3: "Plausible or mixed",
  4: "Strong",
  5: "Very strong",
};

/** "4 — Strong"; an out-of-scale value is shown as the bare number. */
export function strengthLabel(strength: number): string {
  const label = STRENGTH_LABELS[strength];
  return label ? `${strength} — ${label}` : String(strength);
}
