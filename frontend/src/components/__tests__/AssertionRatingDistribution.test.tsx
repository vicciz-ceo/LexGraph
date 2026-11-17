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

  it("gives every bucket an accessible name, so a value and its count are never read as one number", () => {
    render(
      <AssertionRatingDistribution
        summary={{ count: 2, average: 5, median: 5, distribution: { "5": 2 } }}
        modelConfidence={null}
      />
    );
    expect(screen.getByTestId("rating-distribution-bucket-5")).toHaveAccessibleName(
      "5 (Very strong): 2 of 2 ratings"
    );
    expect(screen.getByTestId("rating-distribution-bucket-1")).toHaveAccessibleName(
      "1 (Very weak): 0 of 2 ratings"
    );
    // The compact layout used by the review queue and contested drawer adds no text.
    expect(screen.queryByText("Very strong")).not.toBeInTheDocument();
  });

  it("detailed layout names each strength and sizes each bar by its share", () => {
    const { container } = render(
      <AssertionRatingDistribution summary={summary} modelConfidence={null} detailed />
    );
    expect(screen.getByText("Plausible or mixed")).toBeInTheDocument();
    const fills = container.querySelectorAll<HTMLElement>(
      ".assertion-rating-distribution__bucket-fill"
    );
    // 1, 1, 2, 5, 3 of 12 ratings.
    expect(Array.from(fills, (fill) => fill.style.width)).toEqual([
      `${(1 / 12) * 100}%`,
      `${(1 / 12) * 100}%`,
      `${(2 / 12) * 100}%`,
      `${(5 / 12) * 100}%`,
      `${(3 / 12) * 100}%`,
    ]);
  });

  it("draws no bar for a bucket nobody chose", () => {
    const { container } = render(
      <AssertionRatingDistribution
        summary={{ count: 1, average: 4, median: 4, distribution: { "4": 1 } }}
        modelConfidence={null}
        detailed
      />
    );
    expect(container.querySelectorAll(".assertion-rating-distribution__bucket-fill")).toHaveLength(1);
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
