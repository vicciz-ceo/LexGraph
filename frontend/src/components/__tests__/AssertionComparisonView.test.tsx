// UI3 — side-by-side revision comparison (spec §3: "The user must be able
// to compare revisions"). Import-failure RED (documented exception) until
// Developer track UI3 creates `../AssertionComparisonView`.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssertionComparisonView } from "../AssertionComparisonView";

const left = { revisionNumber: 1, proposition: "Original proposition text.", editedBy: "Contributor A" };
const right = { revisionNumber: 2, proposition: "A materially edited proposition text.", editedBy: "Contributor A" };

describe("AssertionComparisonView", () => {
  it("renders both revisions side by side", () => {
    render(<AssertionComparisonView left={left} right={right} />);
    expect(screen.getByText("Original proposition text.")).toBeInTheDocument();
    expect(screen.getByText("A materially edited proposition text.")).toBeInTheDocument();
  });

  it("labels each side with its revision number", () => {
    render(<AssertionComparisonView left={left} right={right} />);
    expect(screen.getByText(/revision 1/i)).toBeInTheDocument();
    expect(screen.getByText(/revision 2/i)).toBeInTheDocument();
  });

  it("indicates which revision each rating applied to when ratings are passed in", () => {
    render(
      <AssertionComparisonView
        left={left}
        right={right}
        leftRatingSummary={{ count: 5, average: 3.0, median: 3, distribution: {} }}
        rightRatingSummary={{ count: 0, average: null, median: null, distribution: {} }}
      />
    );
    expect(screen.getByText(/not yet been rated/i)).toBeInTheDocument();
  });
});
