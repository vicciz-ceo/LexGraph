// The "decision not recorded" notice reads as plain language (acceptance run,
// release candidate). It used to append the API's 409 detail verbatim, so a
// decision on an assertion edited meanwhile ended with "Reason: assertion has
// been modified since expected_revision_number." The details below are the
// ones backend/app/routers/review.py answers a decision with.

import { REVIEW_CONFLICT_MESSAGE, reviewConflictNotice } from "../review";

const API_DETAILS: Record<string, string> = {
  stale: "assertion has been modified since expected_revision_number",
  raced: "assertion was changed by another request; reload it and review the current revision",
  alreadyAccepted: "assertion is already 'accepted'",
  alreadyRevision: "assertion is already 'revision_requested'",
  withdrawn: "cannot accept an assertion in status 'withdrawn'",
  superseded: "cannot request revision of an assertion in status 'superseded'",
  draft: "cannot reject an assertion in status 'draft'; it must be submitted for review first",
  duplicate: "duplicate: an identical proposition already exists in this matter (assertion a-9)",
};

describe("reviewConflictNotice", () => {
  it("says why in plain words when the assertion was edited after the page loaded it", () => {
    expect(reviewConflictNotice(API_DETAILS.stale)).toBe(`${REVIEW_CONFLICT_MESSAGE} Reason: it was edited.`);
  });

  it.each([
    ["raced", "someone else changed it at the same moment"],
    ["alreadyAccepted", "it is already accepted"],
    ["alreadyRevision", "a revision of it is already requested"],
    ["withdrawn", "its author withdrew it"],
    ["superseded", "it was superseded by another assertion"],
    ["draft", "it is a draft that has not been submitted for review"],
  ])("names the reason for %s", (kind, reason) => {
    expect(reviewConflictNotice(API_DETAILS[kind])).toBe(`${REVIEW_CONFLICT_MESSAGE} Reason: ${reason}.`);
  });

  it("says that an identical proposition is live, not that this assertion changed", () => {
    const notice = reviewConflictNotice(API_DETAILS.duplicate);
    expect(notice).toMatch(/^Your decision was not recorded: /);
    expect(notice).toContain("an identical proposition is already live in this matter (assertion a-9)");
    expect(notice).not.toContain("changed after you opened it");
  });

  it("never shows an API field name, a status code word or the API's own tags", () => {
    for (const detail of Object.values(API_DETAILS)) {
      const notice = reviewConflictNotice(detail);
      expect(notice).not.toMatch(/\b[a-z]+_[a-z_]+\b/);
      expect(notice).not.toMatch(/'[a-z_]+'/);
      expect(notice).not.toContain("duplicate:");
      expect(notice).not.toMatch(/\breload it\b/);
    }
  });

  it("keeps the general message alone without a detail, and shows any other reason as given", () => {
    expect(reviewConflictNotice("")).toBe(REVIEW_CONFLICT_MESSAGE);
    expect(reviewConflictNotice("  the matter was archived.  ")).toBe(
      `${REVIEW_CONFLICT_MESSAGE} Reason: the matter was archived.`,
    );
  });
});
