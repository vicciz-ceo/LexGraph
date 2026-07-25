// UI3 — assertion detail workspace with tabs (spec §5, §14, gate G11).
// Import-failure RED (documented exception) until Developer track UI3
// creates `../AssertionDetailPanel`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssertionDetailPanel } from "../AssertionDetailPanel";

const assertion = {
  id: "a1",
  proposition: "Clause 8.4 creates a limited exception to the notification obligation in Clause 8.2.",
  assertionType: "CREATES_EXCEPTION_TO",
  subjectEntity: { type: "Provision", id: "p1", label: "Clause 8.4" },
  objectEntity: { type: "Provision", id: "p2", label: "Clause 8.2" },
  author: "Contributor A",
  createdAt: "2026-07-20T10:00:00Z",
  currentRevisionNumber: 1,
  jurisdiction: null,
  effectiveFrom: null,
  effectiveTo: null,
  status: "proposed",
  origin: "user_suggested",
  confidence: null,
  evidenceStatus: "unsupported",
};

describe("AssertionDetailPanel", () => {
  it("renders the workspace tabs (overview, evidence, ratings, discussion, revision history, related, review history)", () => {
    render(<AssertionDetailPanel assertion={assertion} />);
    for (const tab of [
      "Overview",
      "Evidence",
      "Ratings",
      "Discussion",
      "Revision history",
      "Related assertions",
      "Review history",
    ]) {
      expect(screen.getByRole("tab", { name: tab })).toBeInTheDocument();
    }
  });

  it("shows proposition, subject, object, author, and jurisdiction on the overview tab", () => {
    render(<AssertionDetailPanel assertion={assertion} />);
    expect(screen.getByText(/Clause 8.4 creates a limited exception/)).toBeInTheDocument();
    expect(screen.getByText("Clause 8.4")).toBeInTheDocument();
    expect(screen.getByText("Clause 8.2")).toBeInTheDocument();
    expect(screen.getByText("Contributor A")).toBeInTheDocument();
  });

  it("switches to the ratings tab and shows aggregate, count, distribution, and current user rating", () => {
    render(
      <AssertionDetailPanel
        assertion={assertion}
        ratingSummary={{ count: 12, average: 3.8, median: 4, distribution: { "1": 1, "2": 1, "3": 2, "4": 5, "5": 3 } }}
        currentUserRating={4}
      />
    );
    fireEvent.click(screen.getByRole("tab", { name: "Ratings" }));
    expect(screen.getByText(/3\.8/)).toBeInTheDocument();
    expect(screen.getByText(/12/)).toBeInTheDocument();
  });

  it("includes explanatory text that ratings are individual opinions, not legal conclusions", () => {
    render(<AssertionDetailPanel assertion={assertion} />);
    expect(screen.getByText(/individual.*opinion|not.*legal conclusion/i)).toBeInTheDocument();
  });

  it("shows the revision history tab content when selected", () => {
    render(
      <AssertionDetailPanel
        assertion={assertion}
        revisions={[{ revisionNumber: 1, proposition: assertion.proposition, editedBy: "Contributor A" }]}
      />
    );
    fireEvent.click(screen.getByRole("tab", { name: "Revision history" }));
    expect(screen.getByText(/revision 1/i)).toBeInTheDocument();
  });
});
