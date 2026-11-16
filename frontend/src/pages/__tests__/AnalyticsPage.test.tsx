// AnalyticsPage — matter-scoped dashboard over server-side aggregates.
//
// The page is read-only (no review/rating/suggest actions), so there is no
// role-gated UI to cover; the tests instead verify that every displayed
// metric comes from GET /matters/{id}/assertion-stats (never from
// downloading the matter's assertions or one rating summary per assertion,
// audit finding ui:1), and that model confidence and strength ratings stay
// separate.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssertionStats, AssertionStatsParams } from "../../api/types";

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
      assertionStats: vi.fn(),
      listAssertions: vi.fn(),
      listMatterMembers: vi.fn(),
      ratingSummary: vi.fn(),
    },
  };
});

import { api } from "../../api/client";
import { AnalyticsPage } from "../AnalyticsPage";

const mockedApi = vi.mocked(api);

// The aggregates of a 6-assertion matter: total 6, accepted 2, rejected 1,
// open 3 (proposed + revision_requested + disputed), acceptance 2/3 ≈ 67%.
// Model confidence: mean(0.9, 0.7, 0.8) = 0.8 → 80%. Two assertions are
// rated (averages 4.0 and 3.0) → mean of averages 3.5.
const statsFixture: Omit<AssertionStats, "created_buckets"> = {
  matter_id: "m-1",
  total: 6,
  by_status: { accepted: 2, proposed: 1, rejected: 1, disputed: 1, revision_requested: 1 },
  by_origin: { user_suggested: 3, model_suggested: 3 },
  by_origin_status: {
    user_suggested: { accepted: 1, rejected: 1, revision_requested: 1 },
    model_suggested: { accepted: 1, proposed: 1, disputed: 1 },
  },
  by_type: { obligation: 3, definition: 2, fact: 1 },
  by_evidence_status: { evidenced: 6 },
  authors: [
    { user_id: "u-anna", total: 3, by_status: { accepted: 2, revision_requested: 1 } },
    { user_id: "u-boris", total: 2, by_status: { proposed: 1, rejected: 1 } },
    { user_id: "u-ghost", total: 1, by_status: { disputed: 1 } },
  ],
  confidence_by_origin: { model_suggested: { count: 3, average: 0.8 } },
  ratings: { rated_assertions: 2, ratings: 5, average_of_averages: 3.5 },
};

/** Weekly creation counts the fake server reports, oldest week first. */
const WEEKLY_COUNTS = [0, 0, 0, 1, 0, 1, 1, 3];

/** A stand-in for the stats endpoint: `stats`, plus one bucket per pair of
 * the edges the page sent. */
function serveStats(stats = statsFixture, counts = WEEKLY_COUNTS) {
  return async (_matterId: string, params: AssertionStatsParams = {}): Promise<AssertionStats> => {
    const edges = (params.created_bucket_edges ?? "").split(",").filter(Boolean);
    return {
      ...stats,
      created_buckets: edges.slice(0, -1).map((start, i) => ({
        start,
        end: edges[i + 1],
        count: counts[i] ?? 0,
      })),
    };
  };
}

function requestedEdges(): Date[] {
  const params = mockedApi.assertionStats.mock.calls[0][1] as AssertionStatsParams;
  return (params.created_bucket_edges ?? "").split(",").map((edge) => new Date(edge));
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.assertionStats.mockImplementation(serveStats());
  // Backend GET /matters/{id}/members returns a bare JSON array (see
  // backend/app/routers/workspace.py::list_members), not { items: [...] }.
  mockedApi.listMatterMembers.mockResolvedValue([
    {
      user: { id: "u-anna", email: "anna@example.com", display_name: "Anna Levi" },
      role: "contributor",
    },
    {
      user: { id: "u-boris", email: "boris@example.com", display_name: "Boris Katz" },
      role: "reviewer",
    },
  ]);
});

async function renderLoaded() {
  render(<AnalyticsPage />);
  await screen.findByTestId("ana-kpi-total");
}

describe("AnalyticsPage", () => {
  it("fetches the matter's aggregates and members and derives the KPI cards", async () => {
    await renderLoaded();

    expect(mockedApi.assertionStats).toHaveBeenCalledTimes(1);
    expect(mockedApi.assertionStats).toHaveBeenCalledWith("m-1", {
      created_bucket_edges: expect.any(String),
    });
    expect(mockedApi.listMatterMembers).toHaveBeenCalledWith("m-1");
    expect(screen.getByText(/Computed live from this matter/)).toBeInTheDocument();

    expect(screen.getByTestId("ana-kpi-total")).toHaveTextContent("6");
    expect(screen.getByTestId("ana-kpi-accepted")).toHaveTextContent("2");
    expect(screen.getByTestId("ana-kpi-open")).toHaveTextContent("3");
    expect(screen.getByTestId("ana-kpi-acceptance")).toHaveTextContent("67%");
  });

  it("never downloads the matter's assertions or one rating summary per assertion", async () => {
    // ui:1: a matter with 20,000 assertions used to download every one of
    // them (and 50 summaries) to compute these cards.
    mockedApi.assertionStats.mockImplementation(
      serveStats({
        ...statsFixture,
        total: 20_000,
        by_status: { accepted: 19_000, proposed: 1_000 },
        ratings: { rated_assertions: 1_234, ratings: 4_000, average_of_averages: 3.25 },
      }),
    );
    await renderLoaded();

    expect(screen.getByTestId("ana-kpi-total")).toHaveTextContent("20,000");
    expect(screen.getByTestId("ana-kpi-accepted")).toHaveTextContent("19,000");
    // The strength KPI covers every rated assertion, not the first 50.
    expect(screen.getByTestId("ana-kpi-strength")).toHaveTextContent("3.3 / 5");
    expect(screen.getByText("1–5 scale · 1,234 rated")).toBeInTheDocument();
    expect(mockedApi.listAssertions).not.toHaveBeenCalled();
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
    expect(mockedApi.assertionStats).toHaveBeenCalledTimes(1);
  });

  it("keeps strength ratings and model confidence as separate KPIs", async () => {
    await renderLoaded();

    // Avg strength rating = mean of per-assertion averages (4.0 and 3.0).
    expect(screen.getByTestId("ana-kpi-strength")).toHaveTextContent("3.5 / 5");
    expect(screen.getByText("1–5 scale · 2 rated")).toBeInTheDocument();
    // Avg model confidence = mean confidence of model_suggested only, as %.
    expect(screen.getByTestId("ana-kpi-confidence")).toHaveTextContent("80%");
    expect(screen.getByTestId("ana-kpi-confidence")).not.toHaveTextContent("/ 5");
    expect(screen.getByTestId("ana-kpi-strength")).not.toHaveTextContent("%");
    expect(screen.getByText("AI-deduced assertions only")).toBeInTheDocument();
  });

  it("asks for weekly creation counts bounded by local Mondays", async () => {
    await renderLoaded();

    // 8 weeks need 9 edges: each a local Monday midnight, 7 days apart,
    // the last one after now.
    const edges = requestedEdges();
    expect(edges).toHaveLength(9);
    for (const edge of edges) {
      expect(edge.getDay()).toBe(1);
      expect([edge.getHours(), edge.getMinutes(), edge.getSeconds()]).toEqual([0, 0, 0]);
    }
    for (let i = 1; i < edges.length; i++) {
      const gapDays = Math.round((edges[i].getTime() - edges[i - 1].getTime()) / 86_400_000);
      expect(gapDays).toBe(7);
    }
    const now = Date.now();
    expect(edges[7].getTime()).toBeLessThanOrEqual(now);
    expect(edges[8].getTime()).toBeGreaterThan(now);

    // The chart shows the server's counts, oldest week first.
    expect(
      screen.getByRole("img", {
        name: "Assertions created per week, oldest to newest: 0, 0, 0, 1, 0, 1, 1, 3",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/peak 3\/wk/)).toBeInTheDocument();
    const firstLabel = edges[0].toLocaleDateString("en-US", { month: "short", day: "numeric" });
    expect(screen.getByText(firstLabel)).toBeInTheDocument();
  });

  it("renders honestly aggregated charts from the aggregates", async () => {
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
    // Review activity chart is present.
    expect(screen.getByText("Review activity")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Assertions created per week/ }),
    ).toBeInTheDocument();
  });

  it("shows the six most common types, most common first", async () => {
    mockedApi.assertionStats.mockImplementation(
      serveStats({
        ...statsFixture,
        by_type: { a_type: 1, b_type: 9, c_type: 4, d_type: 4, e_type: 2, f_type: 7, g_type: 3 },
      }),
    );
    await renderLoaded();

    const names = screen
      .getAllByRole("img", { name: /^[a-g]_type: \d+$/ })
      .map((img) => img.getAttribute("aria-label"));
    expect(names).toEqual([
      "b_type: 9",
      "f_type: 7",
      "c_type: 4",
      "d_type: 4",
      "g_type: 3",
      "e_type: 2",
    ]);
  });

  it("resolves contributor names via the members map and falls back to the raw id", async () => {
    await renderLoaded();

    // u-anna authored 3, 2 of them accepted.
    const annaRow = (await screen.findByText("Anna Levi")).closest("tr");
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

  it("renders contributor display names from the bare members array (D2)", async () => {
    // Backend returns a bare array, not { items: [...] }. Before the fix,
    // res.items is undefined and the member lookup map stays empty, so
    // contributors fall back to raw user ids instead of display names.
    await renderLoaded();

    expect(await screen.findByText("Anna Levi")).toBeInTheDocument();
    expect(screen.getByText("Boris Katz")).toBeInTheDocument();
    expect(screen.queryByText("u-anna")).not.toBeInTheDocument();
  });

  it("lists at most eight contributors, most prolific first", async () => {
    mockedApi.assertionStats.mockImplementation(
      serveStats({
        ...statsFixture,
        authors: Array.from({ length: 10 }, (_, i) => ({
          user_id: `u-${i}`,
          total: 10 - i,
          by_status: { accepted: 1 },
        })),
      }),
    );
    await renderLoaded();

    const ids = screen.getAllByText(/^u-\d$/).map((cell) => cell.textContent);
    expect(ids).toEqual(["u-0", "u-1", "u-2", "u-3", "u-4", "u-5", "u-6", "u-7"]);
  });

  it("shows em-dashes when nothing is reviewed, rated, or AI-deduced", async () => {
    mockedApi.assertionStats.mockImplementation(
      serveStats({
        ...statsFixture,
        total: 1,
        by_status: { proposed: 1 },
        by_origin: { user_suggested: 1 },
        by_origin_status: { user_suggested: { proposed: 1 } },
        by_type: { obligation: 1 },
        authors: [{ user_id: "u-anna", total: 1, by_status: { proposed: 1 } }],
        confidence_by_origin: {},
        ratings: { rated_assertions: 0, ratings: 0, average_of_averages: null },
      }),
    );

    await renderLoaded();

    expect(screen.getByTestId("ana-kpi-acceptance")).toHaveTextContent("—");
    expect(screen.getByTestId("ana-kpi-strength")).toHaveTextContent("—");
    expect(screen.getByTestId("ana-kpi-confidence")).toHaveTextContent("—");
    expect(screen.getByText("no reviewed assertions yet")).toBeInTheDocument();
    expect(screen.getByText("no ratings yet")).toBeInTheDocument();
  });

  it("renders a friendly empty dashboard when the matter has no assertions", async () => {
    mockedApi.assertionStats.mockImplementation(
      serveStats(
        {
          ...statsFixture,
          total: 0,
          by_status: {},
          by_origin: {},
          by_origin_status: {},
          by_type: {},
          by_evidence_status: {},
          authors: [],
          confidence_by_origin: {},
          ratings: { rated_assertions: 0, ratings: 0, average_of_averages: null },
        },
        [],
      ),
    );
    render(<AnalyticsPage />);

    expect(await screen.findByText("No assertions yet")).toBeInTheDocument();
    expect(
      screen.getByText("Metrics appear once this matter has assertions to measure."),
    ).toBeInTheDocument();
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
  });

  it("shows an error banner with a retry control when the fetch fails", async () => {
    mockedApi.assertionStats.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<AnalyticsPage />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByTestId("ana-kpi-total")).toHaveTextContent("6");
    await waitFor(() => expect(mockedApi.assertionStats).toHaveBeenCalledTimes(2));
  });
});
