// ProfilePage — the signed-in user's activity in the current matter.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AppNotification,
  Assertion,
  AssertionList,
  AssertionListParams,
  AssertionStats,
  AssertionStatsParams,
  MatterRoleName,
} from "../../api/types";

const mocks = vi.hoisted(() => ({
  role: "reviewer" as MatterRoleName,
  selectMatter: vi.fn(),
}));

vi.mock("../../app/session", () => {
  const useActiveSession = () => {
    const current = {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: mocks.role,
    };
    const other = {
      id: "m-2",
      name: "Estate of Harel",
      repository_id: "r-2",
      organization_id: "o-1",
      role: "viewer" as MatterRoleName,
    };
    return {
      user: { id: "u-me", email: "noa@example.com", display_name: "Noa Levi" },
      matters: [current, other],
      currentMatter: current,
      role: mocks.role,
    };
  };
  return {
    useActiveSession,
    // The notifications tab's links switch matter through useSession().
    useSession: () => ({ session: useActiveSession(), selectMatter: mocks.selectMatter }),
  };
});

vi.mock("../../api/client", () => ({
  api: {
    assertionStats: vi.fn(),
    listAssertions: vi.fn(),
    notifications: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
  },
}));

import { api } from "../../api/client";
import { ProfilePage } from "../ProfilePage";

const mockedApi = vi.mocked(api);

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
    author_user_id: "u-me",
    confidence: null,
    jurisdiction: "IL",
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T09:00:00Z",
    updated_at: "2026-07-20T09:00:00Z",
    submitted_at: "2026-07-02T09:00:00Z",
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    ...overrides,
  };
}

// The matter's full assertion list: four authored by the signed-in user
// (one accepted, one rejected, one proposed, one draft) plus one authored
// by a colleague that must be excluded from the "my" stats and list.
const matterItems: Assertion[] = [
  makeAssertion({
    id: "a-mine-accepted",
    proposition: "The guarantee covers obligations incurred before closing.",
    status: "accepted",
    standing: "accepted",
    updated_at: "2026-07-25T09:00:00Z",
  }),
  makeAssertion({
    id: "a-mine-rejected",
    proposition: "Termination requires 90 days' written notice.",
    status: "rejected",
    standing: "rejected",
    updated_at: "2026-07-24T09:00:00Z",
  }),
  makeAssertion({
    id: "a-mine-proposed",
    proposition: "The 2021 lease amendment extends the term to 2030.",
    status: "proposed",
    standing: "probable",
    updated_at: "2026-07-23T09:00:00Z",
  }),
  makeAssertion({
    id: "a-mine-draft",
    proposition: "Renewal rent resets to fair market value.",
    status: "draft",
    standing: "draft",
    updated_at: "2026-07-22T09:00:00Z",
  }),
  makeAssertion({
    id: "a-other",
    proposition: "Signed by both parties on 2026-01-15.",
    status: "accepted",
    standing: "accepted",
    author_user_id: "u-other",
  }),
];

const awaitingItems: Assertion[] = [
  makeAssertion({
    id: "aw-1",
    proposition: "Clause 9 restricts assignment without consent.",
    origin: "model_suggested",
    confidence: 0.82,
    author_user_id: "u-other",
    submitted_at: "2026-07-05T09:00:00Z",
  }),
  makeAssertion({
    id: "aw-2",
    proposition: "The guarantee expires on 2027-03-01.",
    origin: "user_suggested",
    author_user_id: "u-other",
    jurisdiction: null,
  }),
];

// Out of chronological order on purpose — the page must sort newest first.
const notificationItems: AppNotification[] = [
  {
    id: "n-1",
    event_type: "assertion_accepted",
    actor_user_id: "u-reviewer",
    recipient_user_id: "u-me",
    payload: {},
    created_at: "2026-07-20T10:00:00Z",
    read: true,
  },
  {
    id: "n-2",
    event_type: "rating_added",
    actor_user_id: "u-other",
    recipient_user_id: "u-me",
    payload: {},
    created_at: "2026-07-25T10:00:00Z",
    read: false,
  },
];

/** A stand-in for the server over `matter` (all of the matter's assertions)
 * and `unrated` (what unrated_by_me returns): it filters by author, sorts by
 * -updated_at and pages like GET /assertions, and aggregates like
 * GET /matters/{id}/assertion-stats. */
function serve(matter: Assertion[], unrated: Assertion[]) {
  mockedApi.listAssertions.mockImplementation(
    async (_matterId: string, params: AssertionListParams = {}): Promise<AssertionList> => {
      let rows = params.unrated_by_me ? unrated : matter;
      if (params.author_user_id) rows = rows.filter((a) => a.author_user_id === params.author_user_id);
      if (params.sort === "-updated_at") {
        rows = [...rows].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
      }
      const offset = params.offset ?? 0;
      const end = params.limit === undefined ? rows.length : offset + params.limit;
      return { items: rows.slice(offset, end), total: rows.length, limit: params.limit ?? null, offset };
    },
  );
  mockedApi.assertionStats.mockImplementation(
    async (_matterId: string, params: AssertionStatsParams = {}): Promise<AssertionStats> => {
      const rows = matter.filter(
        (a) => !params.author_user_id || a.author_user_id === params.author_user_id,
      );
      const byStatus: AssertionStats["by_status"] = {};
      for (const a of rows) byStatus[a.status] = (byStatus[a.status] ?? 0) + 1;
      return {
        matter_id: "m-1",
        total: rows.length,
        by_status: byStatus,
        by_origin: {},
        by_origin_status: {},
        by_type: {},
        by_evidence_status: {},
        authors: [],
        confidence_by_origin: {},
        ratings: { rated_assertions: 0, ratings: 0, average_of_averages: null },
        created_buckets: [],
      };
    },
  );
}

function mine(count: number): Assertion[] {
  return Array.from({ length: count }, (_, i) =>
    makeAssertion({
      id: `mine-${i}`,
      proposition: `My suggestion number ${i}.`,
      status: i % 3 === 0 ? "accepted" : "proposed",
      // Newest first is mine-0, mine-1, …
      updated_at: new Date(Date.UTC(2026, 6, 20) - i * 60_000).toISOString(),
    }),
  );
}

beforeEach(() => {
  // Reset, not just clear: a once-only rejection a test did not consume
  // must not leak into the next one.
  vi.resetAllMocks();
  mocks.role = "reviewer";
  window.location.hash = "";
  serve(matterItems, awaitingItems);
  mockedApi.notifications.mockResolvedValue(notificationItems);
});

async function renderPage() {
  render(<ProfilePage />);
  await screen.findByTestId("pf-stat-suggestions");
}

describe("ProfilePage", () => {
  it("renders identity from the session and stats from my aggregates in the matter", async () => {
    await renderPage();

    // ui:1: counts come from the stats endpoint filtered by author, and the
    // lists are bounded server pages; the matter is never downloaded.
    expect(mockedApi.assertionStats).toHaveBeenCalledWith("m-1", { author_user_id: "u-me" });
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {
      author_user_id: "u-me",
      sort: "-updated_at",
      limit: 50,
      offset: 0,
    });
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {
      status: "proposed",
      unrated_by_me: true,
      limit: 50,
      offset: 0,
    });
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2);

    // Identity header: name + role badge + email + matter scope.
    expect(screen.getByRole("heading", { name: /Noa Levi/ })).toBeInTheDocument();
    expect(screen.getByText(/noa@example\.com · activity in Acme v\. Zenith/)).toBeInTheDocument();

    // Stats: 4 authored, 1 accepted, 1/(1+1) = 50% acceptance, 2 awaiting.
    expect(screen.getByTestId("pf-stat-suggestions")).toHaveTextContent(/^4$/);
    expect(screen.getByTestId("pf-stat-accepted")).toHaveTextContent(/^1$/);
    expect(screen.getByTestId("pf-stat-acceptance")).toHaveTextContent(/^50%$/);
    expect(screen.getByTestId("pf-stat-awaiting")).toHaveTextContent(/^2$/);
  });

  it("defaults to the awaiting tab: origin chips, meta, and Rate links to the detail page", async () => {
    await renderPage();

    expect(screen.getByRole("tab", { name: /Awaiting my rating/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    const panel = screen.getByRole("tabpanel");
    expect(
      within(panel).getByText("Clause 9 restricts assignment without consent."),
    ).toBeInTheDocument();
    expect(within(panel).getByText("AI-deduced")).toBeInTheDocument();
    expect(within(panel).getByText("Colleague")).toBeInTheDocument();
    // Model confidence rendered as a percent, only for the model-suggested item.
    expect(within(panel).getByText(/model confidence 82%/)).toBeInTheDocument();

    const rateLinks = within(panel).getAllByRole("link", { name: "Rate" });
    expect(rateLinks).toHaveLength(2);
    expect(rateLinks[0]).toHaveAttribute("href", "#/assertions/aw-1");
  });

  it("shows my authored assertions with status and standing badges, excluding colleagues'", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));

    // The server filters by author and orders newest first.
    expect(mockedApi.listAssertions).toHaveBeenCalledWith(
      "m-1",
      expect.objectContaining({ author_user_id: "u-me", sort: "-updated_at" }),
    );
    const panel = screen.getByRole("tabpanel");
    expect(
      within(panel)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual([
      "The guarantee covers obligations incurred before closing.",
      "Termination requires 90 days' written notice.",
      "The 2021 lease amendment extends the term to 2030.",
      "Renewal rent resets to fair market value.",
    ]);
    expect(within(panel).getByText("Accepted")).toBeInTheDocument();
    expect(within(panel).getByText("Rejected")).toBeInTheDocument();
    expect(within(panel).getByText("Proposed")).toBeInTheDocument();
    expect(within(panel).getByText("Draft")).toBeInTheDocument();
    // Standing grade shown only for the proposed assertion.
    expect(within(panel).getByText("Standing: probable")).toBeInTheDocument();
    // The colleague's assertion is not mine.
    expect(
      within(panel).queryByText("Signed by both parties on 2026-01-15."),
    ).not.toBeInTheDocument();
  });

  it("lists notifications newest first with humanized event types and the storage note", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("tab", { name: /Notifications/ }));

    const panel = screen.getByRole("tabpanel");
    const items = within(panel).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Rating added");
    expect(items[1]).toHaveTextContent("Assertion accepted");
    // Notifications are stored server-side now (pipeline:9); the old
    // "reset when the server restarts" note is no longer true.
    expect(within(panel).getByText(/kept until you read them/)).toBeInTheDocument();
    expect(within(panel).queryByText(/reset when the server restarts/)).not.toBeInTheDocument();
  });

  it("links notifications to their assertion, marks them read and switches matter when needed", async () => {
    const context = {
      proposition: "Clause 9 restricts assignment without consent.",
      assertion_status: "rejected" as const,
      assertion_origin: "user_suggested" as const,
      matter_name: "Acme v. Zenith",
      actor_display_name: "Riva Reviewer",
    };
    mockedApi.notifications.mockResolvedValue([
      {
        id: "n-here",
        event_type: "assertion_rejected",
        actor_user_id: "u-reviewer",
        recipient_user_id: "u-me",
        payload: { assertion_id: "a-1", matter_id: "m-1" },
        assertion_id: "a-1",
        matter_id: "m-1",
        link: "/assertions/a-1",
        context,
        created_at: "2026-07-26T10:00:00Z",
        read: false,
      },
      {
        id: "n-there",
        event_type: "assertion_submitted",
        actor_user_id: "u-other",
        recipient_user_id: "u-me",
        payload: { assertion_id: "a-9", matter_id: "m-2" },
        assertion_id: "a-9",
        matter_id: "m-2",
        link: "/assertions/a-9",
        context: { ...context, matter_name: "Estate of Harel", actor_display_name: "Dan" },
        created_at: "2026-07-25T10:00:00Z",
        read: false,
      },
    ]);
    mockedApi.markNotificationRead.mockResolvedValue({} as AppNotification);
    mockedApi.markAllNotificationsRead.mockResolvedValue({ marked_read: 1, unread_count: 0 });
    await renderPage();
    fireEvent.click(screen.getByRole("tab", { name: /Notifications/ }));
    const panel = screen.getByRole("tabpanel");

    expect(within(panel).getByText("2 unread")).toBeInTheDocument();
    const here = within(panel).getByRole("link", { name: /Assertion rejected/ });
    expect(here).toHaveAttribute("href", "#/assertions/a-1");
    expect(here).toHaveTextContent("Clause 9 restricts assignment without consent.");
    expect(here).toHaveTextContent("Riva Reviewer · Acme v. Zenith");

    fireEvent.click(here);
    expect(mockedApi.markNotificationRead).toHaveBeenCalledWith("n-here");
    expect(mocks.selectMatter).not.toHaveBeenCalled();
    expect(window.location.hash).toBe("#/assertions/a-1");
    expect(within(panel).getByText("1 unread")).toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("link", { name: /submitted for review/ }));
    expect(mocks.selectMatter).toHaveBeenCalledWith("m-2");
    expect(window.location.hash).toBe("#/assertions/a-9");
    expect(within(panel).getByText("All read")).toBeInTheDocument();
  });

  it("marks everything shown as read in one call", async () => {
    mockedApi.markAllNotificationsRead.mockResolvedValue({ marked_read: 1, unread_count: 0 });
    await renderPage();
    fireEvent.click(screen.getByRole("tab", { name: /Notifications/ }));
    const panel = screen.getByRole("tabpanel");

    fireEvent.click(within(panel).getByRole("button", { name: "Mark all as read" }));
    // The newest notification shown bounds what is marked.
    expect(mockedApi.markAllNotificationsRead).toHaveBeenCalledWith("2026-07-25T10:00:00Z");
    expect(within(panel).getByText("All read")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "Mark all as read" })).toBeDisabled();
  });

  it("hides rating work entirely from viewers and skips the unrated query", async () => {
    mocks.role = "viewer";
    await renderPage();

    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {
      author_user_id: "u-me",
      sort: "-updated_at",
      limit: 50,
      offset: 0,
    });
    expect(mockedApi.assertionStats).toHaveBeenCalledTimes(1);

    expect(screen.queryByRole("tab", { name: /Awaiting my rating/ })).not.toBeInTheDocument();
    expect(screen.queryByTestId("pf-stat-awaiting")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Rate" })).not.toBeInTheDocument();

    // Falls back to the suggestions tab.
    expect(screen.getByRole("tab", { name: /My suggestions/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("renders empty states and an em-dash acceptance rate when I authored nothing", async () => {
    serve([matterItems[4]], []);
    await renderPage();

    expect(screen.getByTestId("pf-stat-suggestions")).toHaveTextContent(/^0$/);
    expect(screen.getByTestId("pf-stat-acceptance")).toHaveTextContent("—");
    expect(screen.getByText("All caught up")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));
    expect(screen.getByText("No suggestions yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Suggest an assertion" })).toHaveAttribute(
      "href",
      "#/suggest",
    );
  });

  it("shows an error banner with a retry control when loading fails", async () => {
    mockedApi.assertionStats.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<ProfilePage />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByTestId("pf-stat-suggestions")).toBeInTheDocument();
  });

  it("counts every suggestion of a large matter from the aggregates, listing 50 at a time", async () => {
    const authored = mine(4_321);
    serve([...authored, matterItems[4]], awaitingItems);
    await renderPage();

    expect(screen.getByTestId("pf-stat-suggestions")).toHaveTextContent(/^4,321$/);
    // mine-0, 3, 6, … are accepted: 1,441 of 4,321; nothing rejected.
    expect(screen.getByTestId("pf-stat-accepted")).toHaveTextContent(/^1,441$/);
    expect(screen.getByTestId("pf-stat-acceptance")).toHaveTextContent(/^100%$/);
    for (const [, params] of mockedApi.listAssertions.mock.calls) {
      expect(params?.limit).toBe(50);
    }

    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));
    expect(screen.getByRole("tab", { name: /My suggestions/ })).toHaveTextContent("4,321");
    const panel = screen.getByRole("tabpanel");
    expect(within(panel).getAllByRole("link")).toHaveLength(50);
    expect(within(panel).getByText("Showing 50 of 4,321")).toBeInTheDocument();
  });

  it("loads more of my suggestions on demand, 50 at a time", async () => {
    serve(mine(120), awaitingItems);
    await renderPage();
    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));
    const panel = () => screen.getByRole("tabpanel");
    expect(within(panel()).getAllByRole("link")).toHaveLength(50);

    fireEvent.click(within(panel()).getByRole("button", { name: "Show more" }));
    await waitFor(() => expect(within(panel()).getAllByRole("link")).toHaveLength(100));
    expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m-1", {
      author_user_id: "u-me",
      sort: "-updated_at",
      limit: 50,
      offset: 50,
    });
    expect(within(panel()).getByText("Showing 100 of 120")).toBeInTheDocument();

    fireEvent.click(within(panel()).getByRole("button", { name: "Show more" }));
    await waitFor(() => expect(within(panel()).getAllByRole("link")).toHaveLength(120));
    const links = within(panel()).getAllByRole("link");
    expect(links[0]).toHaveTextContent("My suggestion number 0.");
    expect(links[119]).toHaveTextContent("My suggestion number 119.");
    expect(within(panel()).queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
  });

  it("loads more of the proposed assertions awaiting my rating", async () => {
    const queue = Array.from({ length: 75 }, (_, i) =>
      makeAssertion({
        id: `queue-${i}`,
        proposition: `Awaiting number ${i}.`,
        author_user_id: "u-other",
      }),
    );
    serve(matterItems, queue);
    await renderPage();

    expect(screen.getByTestId("pf-stat-awaiting")).toHaveTextContent(/^75$/);
    const panel = () => screen.getByRole("tabpanel");
    expect(within(panel()).getAllByRole("link", { name: "Rate" })).toHaveLength(50);

    fireEvent.click(within(panel()).getByRole("button", { name: "Show more" }));
    await waitFor(() =>
      expect(within(panel()).getAllByRole("link", { name: "Rate" })).toHaveLength(75),
    );
    expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m-1", {
      status: "proposed",
      unrated_by_me: true,
      limit: 50,
      offset: 50,
    });
  });

  it("reports a failed Show more and keeps what is listed", async () => {
    serve(mine(60), awaitingItems);
    await renderPage();
    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));
    mockedApi.listAssertions.mockRejectedValueOnce(new Error("timed out"));

    fireEvent.click(screen.getByRole("button", { name: "Show more" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't load more: timed out");
    expect(within(screen.getByRole("tabpanel")).getAllByRole("link")).toHaveLength(50);
    expect(screen.getByRole("button", { name: "Show more" })).toBeEnabled();
  });

  it("lists my matters with roles and highlights the current one", async () => {
    await renderPage();

    const matters = screen.getByTestId("pf-matters");
    const currentRow = within(matters).getByText("Acme v. Zenith").closest("li");
    expect(currentRow).not.toBeNull();
    expect(currentRow).toHaveTextContent("Current");
    expect(currentRow).toHaveTextContent("reviewer");

    const otherRow = within(matters).getByText("Estate of Harel").closest("li");
    expect(otherRow).toHaveTextContent("viewer");
    expect(otherRow).not.toHaveTextContent("Current");
    expect(within(matters).getByText(/Switch the active matter/)).toBeInTheDocument();
  });
});

describe("ProfilePage in Asia/Tokyo", () => {
  // ui:3: an offset-less timestamp is UTC. Read as local time it showed
  // the UTC date and time as the viewer's (here a day early).
  beforeAll(() => {
    vi.stubEnv("TZ", "Asia/Tokyo");
  });
  afterAll(() => {
    vi.unstubAllEnvs();
  });

  it("shows local dates and times for offset-less instants", async () => {
    const naive = "2026-11-15T20:16:17.835814";
    serve(
      [makeAssertion({ id: "a-naive", proposition: "Mine, edited late UTC.", updated_at: naive })],
      [makeAssertion({ id: "aw-naive", author_user_id: "u-other", submitted_at: naive })],
    );
    mockedApi.notifications.mockResolvedValue([{ ...notificationItems[0], created_at: naive }]);
    await renderPage();

    // 20:16 UTC on Nov 15 is 05:16 on Nov 16 in Tokyo.
    expect(within(screen.getByRole("tabpanel")).getByText(/submitted Nov 16, 2026/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));
    expect(within(screen.getByRole("tabpanel")).getByText(/updated Nov 16, 2026/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Notifications/ }));
    expect(
      within(screen.getByRole("tabpanel")).getByText(
        new Date(Date.UTC(2026, 10, 15, 20, 16, 17, 835)).toLocaleString(),
      ),
    ).toBeInTheDocument();
  });
});
