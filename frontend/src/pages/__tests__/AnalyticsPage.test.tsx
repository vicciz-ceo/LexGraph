// AnalyticsPage — matter-scoped dashboard computed client-side.
//
// The page is read-only (no review/rating/suggest actions), so there is no
// role-gated UI to cover; the tests instead verify that every displayed
// metric is honestly derived from the single assertions fetch, that model
// confidence and strength ratings stay separate, and that the rating-summary
// N+1 is capped.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Assertion, RatingSummary } from "../../api/types";

vi.mock("../../app/session", () => ({
  useActiveSession: () => {
    const matter = {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: "contributor" as const,
    };
    return {
      user: { id: "u-anna", email: "anna@example.com", display_name: "Anna Levi" },
      matters: [matter],
      currentMatter: matter,
      role: "contributor" as const,
    };
  },
}));

vi.mock("../../api/client", () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      detail: string,
    ) {
      super(detail);
      this.name = "ApiError";
    }
  }
  return {
    ApiError,
    api: {
      listAssertions: vi.fn(),
      listMatterMembers: vi.fn(),
      ratingSummary: vi.fn(),
    },
  };
});

import { api } from "../../api/client";
import { AnalyticsPage } from "../AnalyticsPage";

const mockedApi = vi.mocked(api);

function daysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

function makeAssertion(overrides: Partial<Assertion> = {}): Assertion {
  return {
    id: "a-1",
    organization_id: "o-1",
    repository_id: "r-1",
    matter_id: "m-1",
    assertion_type: "obligation",
    proposition: "The 2021 lease amendment extends the term to 2030.",
    proposition_raw: null,
    subject_entity: { type: "document", id: "doc-1" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u-anna",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: daysAgo(2),
    updated_at: daysAgo(1),
    submitted_at: daysAgo(2),
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    ...overrides,
  };
}

function makeSummary(overrides: Partial<RatingSummary> = {}): RatingSummary {
  return {
    count: 0,
    average: null,
    median: null,
    distribution: {},
    assertion_id: "a-1",
    assertion_revision_id: "rev-1",
    current_user_rating: null,
    rationale_count: 0,
    ...overrides,
  };
}

// 6 assertions → total 6, accepted 2, rejected 1, open 3 (proposed +
// revision_requested + disputed), acceptance 2/3 ≈ 67%. Model confidence:
// mean(0.9, 0.7, 0.8) = 0.8 → 80%. a-4 has no current revision, so no
// rating-summary fetch for it.
const fixtures: Assertion[] = [
  makeAssertion({
    id: "a-1",
    status: "accepted",
    origin: "user_suggested",
    author_user_id: "u-anna",
    assertion_type: "obligation",
    current_revision_number: 2,
    created_at: daysAgo(2),
    reviewed_by: "u-boris",
    reviewed_at: daysAgo(1),
  }),
  makeAssertion({
    id: "a-2",
    status: "accepted",
    origin: "model_suggested",
    confidence: 0.9,
    author_user_id: "u-anna",
    assertion_type: "obligation",
    current_revision_number: 1,
    created_at: daysAgo(9),
    reviewed_by: "u-boris",
    reviewed_at: daysAgo(8),
  }),
  makeAssertion({
    id: "a-3",
    status: "proposed",
    origin: "model_suggested",
    confidence: 0.7,
    author_user_id: "u-boris",
    assertion_type: "definition",
    current_revision_number: 1,
    created_at: daysAgo(16),
  }),
  makeAssertion({
    id: "a-4",
    status: "rejected",
    origin: "user_suggested",
    author_user_id: "u-boris",
    assertion_type: "definition",
    current_revision_number: null,
    created_at: daysAgo(3),
    reviewed_by: "u-boris",
    reviewed_at: daysAgo(2),
  }),
  makeAssertion({
    id: "a-5",
    status: "disputed",
    origin: "model_suggested",
    confidence: 0.8,
    author_user_id: "u-ghost",
    assertion_type: "fact",
    current_revision_number: 1,
    created_at: daysAgo(30),
  }),
  makeAssertion({
    id: "a-6",
    status: "revision_requested",
    origin: "user_suggested",
    author_user_id: "u-anna",
    assertion_type: "obligation",
    current_revision_number: 1,
    created_at: daysAgo(1),
  }),
];

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.listAssertions.mockResolvedValue({ items: fixtures, total: fixtures.length });
  mockedApi.listMatterMembers.mockResolvedValue({
    items: [
      {
        user: { id: "u-anna", email: "anna@example.com", display_name: "Anna Levi" },
        role: "contributor",
      },
      {
        user: { id: "u-boris", email: "boris@example.com", display_name: "Boris Katz" },
        role: "reviewer",
      },
    ],
  });
  mockedApi.ratingSummary.mockImplementation(async (id: string) => {
    if (id === "a-1") {
      return makeSummary({
        assertion_id: "a-1",
        count: 3,
        average: 4.0,
        median: 4,
        distribution: { "4": 3 },
      });
    }
    if (id === "a-2") {
      return makeSummary({
        assertion_id: "a-2",
        count: 2,
        average: 3.0,
        median: 3,
        distribution: { "3": 2 },
      });
    }
    return makeSummary({ assertion_id: id });
  });
});

async function renderLoaded() {
  render(<AnalyticsPage />);
  await screen.findByTestId("ana-kpi-total");
}

describe("AnalyticsPage", () => {
  it("fetches the matter's assertions and members and derives the KPI cards", async () => {
    await renderLoaded();

    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {});
    expect(mockedApi.listMatterMembers).toHaveBeenCalledWith("m-1");
    expect(screen.getByText(/Computed live from this matter/)).toBeInTheDocument();

    expect(screen.getByTestId("ana-kpi-total")).toHaveTextContent("6");
    expect(screen.getByTestId("ana-kpi-accepted")).toHaveTextContent("2");
    expect(screen.getByTestId("ana-kpi-open")).toHaveTextContent("3");
    expect(screen.getByTestId("ana-kpi-acceptance")).toHaveTextContent("67%");
  });

  it("keeps strength ratings and model confidence as separate KPIs", async () => {
    await renderLoaded();

    // Avg strength rating = mean of per-assertion averages (4.0 and 3.0).
    await waitFor(() =>
      expect(screen.getByTestId("ana-kpi-strength")).toHaveTextContent("3.5 / 5"),
    );
    // Avg model confidence = mean confidence of model_suggested only, as %.
    expect(screen.getByTestId("ana-kpi-confidence")).toHaveTextContent("80%");
    expect(screen.getByTestId("ana-kpi-confidence")).not.toHaveTextContent("/ 5");
    expect(screen.getByTestId("ana-kpi-strength")).not.toHaveTextContent("%");
    expect(screen.getByText("AI-deduced assertions only")).toBeInTheDocument();
  });

  it("requests rating summaries only for assertions with a current revision", async () => {
    await renderLoaded();

    await waitFor(() => expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(5));
    expect(mockedApi.ratingSummary).toHaveBeenCalledWith("a-1", 2);
    expect(mockedApi.ratingSummary).toHaveBeenCalledWith("a-6", 1);
    expect(mockedApi.ratingSummary).not.toHaveBeenCalledWith("a-4", expect.anything());
  });

  it("caps rating-summary fetches at the first 50 rated assertions", async () => {
    const bulk = Array.from({ length: 55 }, (_, i) =>
      makeAssertion({ id: `bulk-${i}`, current_revision_number: 1 }),
    );
    mockedApi.listAssertions.mockResolvedValue({ items: bulk, total: bulk.length });

    await renderLoaded();

    await waitFor(() => expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(50));
    expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(50);
  });

  it("renders honestly aggregated charts from the fetched assertions", async () => {
    await renderLoaded();

    expect(
      screen.getByRole("img", {
        name: "Status mix: 2 accepted, 1 proposed, 1 disputed, 1 rejected, 1 other",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Acceptance by origin. Colleague-suggested: 1 accepted, 1 rejected. AI-deduced: 1 accepted, 0 rejected.",
      }),
    ).toBeInTheDocument();
    // Assertions by type — real counts per assertion_type.
    expect(screen.getByRole("img", { name: "obligation: 3" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "definition: 2" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "fact: 1" })).toBeInTheDocument();
    // Review activity chart is present (weekly buckets depend on "now").
    expect(screen.getByText("Review activity")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Assertions created per week/ }),
    ).toBeInTheDocument();
  });

  it("resolves contributor names via the members map and falls back to the raw id", async () => {
    await renderLoaded();

    // u-anna authored 3 (a-1, a-2, a-6), 2 of them accepted.
    const annaRow = screen.getByText("Anna Levi").closest("tr");
    expect(annaRow).not.toBeNull();
    const annaCells = within(annaRow as HTMLElement).getAllByRole("cell");
    expect(annaCells[1]).toHaveTextContent("3");
    expect(annaCells[2]).toHaveTextContent("2");

    // u-ghost is not a matter member — the raw user id is shown instead.
    const ghostRow = screen.getByText("u-ghost").closest("tr");
    expect(ghostRow).not.toBeNull();
    const ghostCells = within(ghostRow as HTMLElement).getAllByRole("cell");
    expect(ghostCells[1]).toHaveTextContent("1");
    expect(ghostCells[2]).toHaveTextContent("0");
  });

  it("shows em-dashes when nothing is reviewed, rated, or AI-deduced", async () => {
    mockedApi.listAssertions.mockResolvedValue({
      items: [
        makeAssertion({ id: "p-1", status: "proposed", origin: "user_suggested" }),
      ],
      total: 1,
    });

    await renderLoaded();
    // Let the (count 0) rating summary land before asserting.
    await waitFor(() => expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(1));

    expect(screen.getByTestId("ana-kpi-acceptance")).toHaveTextContent("—");
    expect(screen.getByTestId("ana-kpi-strength")).toHaveTextContent("—");
    expect(screen.getByTestId("ana-kpi-confidence")).toHaveTextContent("—");
    expect(screen.getByText("no reviewed assertions yet")).toBeInTheDocument();
    expect(screen.getByText("no ratings yet")).toBeInTheDocument();
  });

  it("renders a friendly empty dashboard when the matter has no assertions", async () => {
    mockedApi.listAssertions.mockResolvedValue({ items: [], total: 0 });
    render(<AnalyticsPage />);

    expect(await screen.findByText("No assertions yet")).toBeInTheDocument();
    expect(
      screen.getByText("Metrics appear once this matter has assertions to measure."),
    ).toBeInTheDocument();
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
  });

  it("shows an error banner with a retry control when the fetch fails", async () => {
    mockedApi.listAssertions.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<AnalyticsPage />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByTestId("ana-kpi-total")).toHaveTextContent("6");
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2);
  });
});
