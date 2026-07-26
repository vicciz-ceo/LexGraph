// UI1 — team rating summary display, kept visually separate from model
// confidence (spec §5, gate G11). Import-failure RED (documented
// exception) until Developer track UI1 creates
// `../AssertionRatingDistribution`.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssertionRatingDistribution } from "../AssertionRatingDistribution";

const summary = {
  count: 12,
  average: 3.8,
  median: 4,
  distribution: { "1": 1, "2": 1, "3": 2, "4": 5, "5": 3 },
};

describe("AssertionRatingDistribution", () => {
  it("displays the team rating and count together", () => {
    render(<AssertionRatingDistribution summary={summary} modelConfidence={null} />);
    expect(screen.getByText(/team.*rating/i)).toBeInTheDocument();
    expect(screen.getByText(/3\.8/)).toBeInTheDocument();
    expect(screen.getByText(/12/)).toBeInTheDocument();
  });

  it("renders the 1-5 distribution", () => {
    render(<AssertionRatingDistribution summary={summary} modelConfidence={null} />);
    for (const bucket of ["1", "2", "3", "4", "5"]) {
      expect(screen.getByTestId(`rating-distribution-bucket-${bucket}`)).toBeInTheDocument();
    }
  });

  it("never merges the team rating and model confidence into one indicator", () => {
    render(<AssertionRatingDistribution summary={summary} modelConfidence={0.92} />);
    const teamRating = screen.getByTestId("team-rating-indicator");
    const confidence = screen.getByTestId("model-confidence-indicator");
    expect(teamRating).not.toBe(confidence);
    expect(teamRating).toHaveAttribute("data-metric", "team-rating");
    expect(confidence).toHaveAttribute("data-metric", "model-confidence");
  });

  it("renders nothing (no aggregate) when there are zero ratings", () => {
    render(
      <AssertionRatingDistribution
        summary={{ count: 0, average: null, median: null, distribution: {} }}
        modelConfidence={null}
      />
    );
    expect(screen.queryByTestId("team-rating-indicator")).not.toBeInTheDocument();
    expect(screen.getByText(/no ratings yet/i)).toBeInTheDocument();
  });

  it("rounds the displayed average to one decimal place without rounding the source value", () => {
    render(
      <AssertionRatingDistribution
        summary={{ ...summary, average: 3.8333333 }}
        modelConfidence={null}
      />
    );
    expect(screen.getByText("3.8")).toBeInTheDocument();
    expect(screen.queryByText("3.8333333")).not.toBeInTheDocument();
  });
});
