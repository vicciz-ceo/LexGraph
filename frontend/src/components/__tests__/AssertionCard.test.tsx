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

// Sprint 2026-07-30-ratings-grade, item UI1 — standing (grade band)
// presentation. Mandate: "proposed" covers user-submitted and AI-deduced
// assertions until a NON-author user rates them; from the first such
// rating the assertion's *standing* is its grade, banded weak/probable/
// strong (ruling R4). Reviewer decisions (gate G4) take precedence over
// the grade presentation. `standing` is a new field (alongside the
// unchanged `status`) — pinned here via a dedicated
// `data-testid="assertion-standing"` element so these assertions can never
// coincidentally pass against unrelated text (e.g. the per-star
// "Strong"/"Weak" labels the rating widget already renders for
// `currentUserRating`). `currentUserRating` is set to `null` in every
// fixture below for that reason.
//
// `AssertionCard`/`AssertionCardData` do not have a `standing` field or a
// `data-testid="assertion-standing"` element today — every test below is
// expected to fail with "Unable to find an element by:
// [data-testid=assertion-standing]", never an import/collection error.
describe("AssertionCard — standing (grade band presentation)", () => {
  it("shows 'proposed' as the standing until an outside rating grades it (gate G1)", () => {
    render(
      <AssertionCard
        assertion={{
          ...baseAssertion,
          status: "proposed",
          standing: "proposed",
          currentUserRating: null,
        }}
      />
    );
    expect(screen.getByTestId("assertion-standing")).toHaveTextContent(/proposed/i);
  });

  it("shows the grade band once a non-author rating exists, not 'proposed' (gate G2)", () => {
    render(
      <AssertionCard
        assertion={{
          ...baseAssertion,
          status: "proposed",
          standing: "strong",
          currentUserRating: null,
        }}
      />
    );
    const standing = screen.getByTestId("assertion-standing");
    expect(standing).toHaveTextContent(/strong/i);
    expect(standing).not.toHaveTextContent(/proposed/i);
  });

  it("renders each grade band name correctly (weak / probable / strong, ruling R4)", () => {
    for (const band of ["weak", "probable", "strong"] as const) {
      const { unmount } = render(
        <AssertionCard
          assertion={{
            ...baseAssertion,
            status: "proposed",
            standing: band,
            currentUserRating: null,
          }}
        />
      );
      expect(screen.getByTestId("assertion-standing")).toHaveTextContent(new RegExp(band, "i"));
      unmount();
    }
  });

  it("shows the reviewer's decision as the standing once reviewed, never a grade band (gate G4)", () => {
    render(
      <AssertionCard
        assertion={{
          ...baseAssertion,
          status: "accepted",
          standing: "accepted",
          currentUserRating: null,
        }}
      />
    );
    const standing = screen.getByTestId("assertion-standing");
    expect(standing).toHaveTextContent(/accepted/i);
    expect(standing).not.toHaveTextContent(/weak|probable|strong/i);
  });
});
