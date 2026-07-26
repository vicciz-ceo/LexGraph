// UI1 — assertion card (spec §5, §14, gate G11). Import-failure RED
// (documented exception) until Developer track UI1 creates
// `../AssertionCard`.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssertionCard } from "../AssertionCard";

const baseAssertion = {
  id: "a1",
  proposition: "Clause 8.4 creates a limited exception to the notification obligation in Clause 8.2.",
  status: "proposed",
  origin: "user_suggested",
  confidence: null,
  evidenceStatus: "unsupported",
  evidenceCount: 0,
  ratingSummary: { count: 12, average: 3.8, median: 4, distribution: { "1": 1, "2": 1, "3": 2, "4": 5, "5": 3 } },
  currentUserRating: 4,
};

describe("AssertionCard", () => {
  it("shows assertion status, origin, and evidence status separately", () => {
    render(<AssertionCard assertion={baseAssertion} />);
    expect(screen.getByText(/proposed/i)).toBeInTheDocument();
    expect(screen.getByText(/user suggested/i)).toBeInTheDocument();
    expect(screen.getByText(/unsupported|awaiting evidence/i)).toBeInTheDocument();
  });

  it("shows model confidence as 'not applicable' when null", () => {
    render(<AssertionCard assertion={baseAssertion} />);
    expect(screen.getByText(/not applicable/i)).toBeInTheDocument();
  });

  it("shows 'your rating' and 'team rating' as distinct labeled values", () => {
    render(<AssertionCard assertion={baseAssertion} />);
    expect(screen.getByText(/your rating/i)).toBeInTheDocument();
    expect(screen.getByText(/team rating/i)).toBeInTheDocument();
  });

  it("includes an embedded rating widget", () => {
    render(<AssertionCard assertion={baseAssertion} />);
    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
  });

  it("renders the proposition text unescaped as authored (not HTML-injected)", () => {
    render(
      <AssertionCard
        assertion={{ ...baseAssertion, proposition: "<script>alert(1)</script>Safe text." }}
      />
    );
    expect(screen.getByText(/Safe text\./)).toBeInTheDocument();
    expect(document.querySelector("script")).not.toBeInTheDocument();
  });

  it("includes explanatory text that ratings are opinions, not legal conclusions", () => {
    render(<AssertionCard assertion={baseAssertion} />);
    expect(
      screen.getByText(/individual.*opinion|not.*legal conclusion/i)
    ).toBeInTheDocument();
  });
});
