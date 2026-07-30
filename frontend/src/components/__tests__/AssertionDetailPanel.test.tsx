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

// Sprint 2026-07-30-ratings-grade, item UI1 — standing (grade band)
// presentation on the overview tab, alongside the existing "Review
// status" / "Origin" / "Model confidence" / "Evidence status" indicators
// (each already its own `<li data-indicator="...">` -- spec §5: never
// visually merge separate indicators). `standing` is a new field on
// `AssertionDetailSummary` (alongside the unchanged `status`); pinned via
// a `data-indicator="standing"` sibling `<li>`, following that same
// existing convention. `AssertionDetailPanel` renders no such element
// today -- every test below is expected to fail on a null
// `querySelector` match, never an import/collection error.
describe("AssertionDetailPanel — standing (grade band presentation)", () => {
  it("shows 'proposed' as the standing until an outside rating grades it (gate G1)", () => {
    const { container } = render(
      <AssertionDetailPanel
        assertion={{ ...assertion, status: "proposed", standing: "proposed" }}
      />
    );
    const standing = container.querySelector('[data-indicator="standing"]');
    expect(standing).not.toBeNull();
    expect(standing).toHaveTextContent(/proposed/i);
  });

  it("shows the grade band once a non-author rating exists, not 'proposed' (gate G2)", () => {
    const { container } = render(
      <AssertionDetailPanel assertion={{ ...assertion, status: "proposed", standing: "weak" }} />
    );
    const standing = container.querySelector('[data-indicator="standing"]');
    expect(standing).toHaveTextContent(/weak/i);
    expect(standing).not.toHaveTextContent(/proposed/i);
  });

  it("shows the reviewer's decision as the standing once reviewed, never a grade band (gate G4)", () => {
    const { container } = render(
      <AssertionDetailPanel
        assertion={{ ...assertion, status: "rejected", standing: "rejected" }}
      />
    );
    const standing = container.querySelector('[data-indicator="standing"]');
    expect(standing).toHaveTextContent(/rejected/i);
    expect(standing).not.toHaveTextContent(/weak|probable|strong/i);
  });
});
