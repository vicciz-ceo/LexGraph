// How the review surfaces present assertions written by LexGraph's
// deterministic definition-linking pipeline (origin system_generated,
// backend/app/definition_links). The pipeline derives them from the provision
// they link and stores them without evidence, under the user the run is
// attributed to (`--triggered-by-user-id`), who did not suggest them
// (findings ui:4, fe-review-detail:5). The assertion page, the Review Queue
// and Contested use these, so they cannot drift apart. Kept outside
// api/client.ts so page tests that mock the client module get the real values.

/** The evidence label of a pipeline assertion without evidence. */
export const SYSTEM_DERIVED_LABEL = "System-derived";

/**
 * Whether the assertion is shown as "System-derived" rather than "Awaiting
 * evidence": a system_generated assertion with no evidence attached. Once a
 * passage is attached its real evidence status is shown. Accepting it still
 * needs a justification, as for any assertion that is not evidenced.
 */
export function isSystemDerived(assertion: { origin: string; evidence_status: string }): boolean {
  return assertion.origin === "system_generated" && assertion.evidence_status === "awaiting_evidence";
}

/** What an empty evidence list says about a pipeline assertion. */
export const SYSTEM_DERIVED_NO_EVIDENCE =
  "No evidence spans are attached. LexGraph's definition-linking pipeline generated this " +
  "assertion automatically from the provision text it links; no person suggested it.";
