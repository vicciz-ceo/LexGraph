// The Review Queue against the paged list endpoint (lists package): cards
// show the rating aggregate embedded in each list item instead of one
// request per card (XREQ-72/77), the queue loads 50 cards at a time with
// "Show more", an unrated revision whose earlier revisions were rated tells
// the reviewer so (spec §10, ui:12 queue part, XREQ-45), and authors are
// never labelled by user id (ui:0).

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../../api/client";
import type {
  AssertionListItem,
  AssertionListParams,
  AssertionStatus,
  ListRatingsSummary,
  RatingSummary,
} from "../../api/types";
import { ReviewQueuePage } from "../ReviewQueuePage";

const hoisted = vi.hoisted(() => {
  const session = {
    user: { id: "u1", email: "ada@example.com", display_name: "Ada Reviewer" },
    matters: [] as unknown[],
    currentMatter: {
      id: "m1",
      name: "Hollow Oak v. Brightline",
      repository_id: "r1",
      organization_id: "o1",
      role: "reviewer",
    },
    role: "reviewer",
  };
  return { session };
});

vi.mock("../../app/session", () => ({
  useActiveSession: () => hoisted.session,
}));

vi.mock("../../api/client", () => {
  class MockApiError extends Error {
    status: number;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
    }
  }
  return {
    ApiError: MockApiError,
    api: {
      listAssertions: vi.fn(),
      listMatterMembers: vi.fn(),
      ratingSummary: vi.fn(),
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      disputeAssertion: vi.fn(),
      requestRevision: vi.fn(),
    },
  };
});

function rated(id: string, strengths: number[]): ListRatingsSummary {
  const distribution: Record<string, number> = {};
  for (const s of strengths) distribution[String(s)] = (distribution[String(s)] ?? 0) + 1;
  const average = strengths.reduce((a, b) => a + b, 0) / strengths.length;
  return {
    assertion_id: id,
    assertion_revision_id: `rev-${id}`,
    average,
    median: average,
    count: strengths.length,
    distribution,
  };
}

let serial = 0;

/** A GET /assertions item as the paged endpoint returns it. */
function item(overrides: Partial<AssertionListItem> = {}): AssertionListItem {
  serial += 1;
  return {
    id: `a${serial}`,
    organization_id: "o1",
    repository_id: "r1",
    matter_id: "m1",
    assertion_type: "interpretation",
    proposition: `Queued proposition ${serial}`,
    proposition_raw: null,
    subject_entity: { type: "Document", id: "d1" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: new Date(Date.UTC(2026, 6, 1, 0, serial)).toISOString(),
    updated_at: "2026-07-28T10:00:00Z",
    submitted_at: "2026-07-28T10:00:00Z",
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    ratings_summary: null,
    current_user_rating: null,
    last_activity_at: "2026-07-28T10:00:00Z",
    ...overrides,
  };
}

/** The matter's assertions; the fake endpoint filters, sorts and pages them. */
let rows: AssertionListItem[] = [];

function serve(_matterId: string, params: AssertionListParams = {}) {
  let matches = rows.filter(
    (row) =>
      (!params.status || row.status === params.status) &&
      (!params.origin || row.origin === params.origin),
  );
  if (params.sort === "-created_at") {
    matches = [...matches].sort((a, b) => b.created_at.localeCompare(a.created_at));
  }
  const offset = params.offset ?? 0;
  const page = params.limit === undefined ? matches.slice(offset) : matches.slice(offset, offset + params.limit);
  return Promise.resolve({ items: page, total: matches.length, limit: params.limit ?? null, offset });
}

function revisionSummary(id: string, overrides: Partial<RatingSummary> = {}): RatingSummary {
  return {
    count: 0,
    average: null,
    median: null,
    distribution: {},
    assertion_id: id,
    assertion_revision_id: `rev-${id}-2`,
    current_user_rating: null,
    rationale_count: 0,
    prior_revision_rating_count: 0,
    ...overrides,
  };
}

function cards(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>(".rq-card"));
}

function cardFor(proposition: string): HTMLElement {
  const card = screen.getByText(proposition).closest("article");
  if (!card) throw new Error(`no queue card shows "${proposition}"`);
  return card;
}

function many(count: number, status: AssertionStatus = "proposed"): AssertionListItem[] {
  return Array.from({ length: count }, () => item({ status, standing: status }));
}

beforeEach(() => {
  vi.clearAllMocks();
  serial = 0;
  rows = [];
  hoisted.session.role = "reviewer";
  vi.mocked(api.listMatterMembers).mockResolvedValue([
    { user: { id: "u1", email: "ada@example.com", display_name: "Ada Reviewer" }, role: "reviewer" },
    { user: { id: "u2", email: "noa@example.com", display_name: "Noa Contributor" }, role: "contributor" },
  ]);
  vi.mocked(api.listAssertions).mockImplementation(serve);
  vi.mocked(api.ratingSummary).mockImplementation(async (id: string) => revisionSummary(id));
  vi.mocked(api.rejectAssertion).mockImplementation(async (id: string) => {
    rows = rows.map((row) => (row.id === id ? { ...row, status: "rejected", standing: "rejected" } : row));
    return rows.find((row) => row.id === id)!;
  });
});

describe("ReviewQueuePage rating aggregates", () => {
  it("shows each card's embedded aggregate without a request per card", async () => {
    rows = [
      item({ proposition: "Rated twice.", ratings_summary: rated("a1", [4, 5]) }),
      item({ proposition: "Not rated yet." }),
    ];
    render(<ReviewQueuePage />);

    await screen.findByText("Rated twice.");
    const ratedCard = within(cardFor("Rated twice."));
    expect(ratedCard.getByText("4.5")).toBeInTheDocument();
    expect(ratedCard.getByText(/based on 2 ratings/)).toBeInTheDocument();
    expect(within(cardFor("Not rated yet.")).queryByText("Loading ratings…")).not.toBeInTheDocument();
    expect(api.ratingSummary).not.toHaveBeenCalled();
  });

  it("tells the reviewer when only an earlier revision of a card was rated", async () => {
    rows = [
      item({ proposition: "Revised after two ratings.", current_revision_number: 2 }),
      item({
        proposition: "Revised and rated again.",
        current_revision_number: 2,
        ratings_summary: rated("a2", [3]),
      }),
    ];
    vi.mocked(api.ratingSummary).mockImplementation(async (id: string) =>
      revisionSummary(id, { prior_revision_rating_count: 2 }),
    );
    render(<ReviewQueuePage />);

    await screen.findByText("Revised after two ratings.");
    const revised = within(cardFor("Revised after two ratings."));
    expect(
      await revised.findByText(/Existing ratings were recorded against a prior revision/),
    ).toBeInTheDocument();
    // Only the unrated revision needs its revision summary.
    expect(api.ratingSummary).toHaveBeenCalledTimes(1);
    expect(api.ratingSummary).toHaveBeenCalledWith("a1", 2);
    expect(
      within(cardFor("Revised and rated again.")).queryByText(/prior revision/),
    ).not.toBeInTheDocument();
  });
});

describe("ReviewQueuePage paging", () => {
  it("shows the newest 50 cards first and 50 more on request", async () => {
    const user = userEvent.setup();
    rows = many(120);
    render(<ReviewQueuePage />);

    await screen.findByText("Queued proposition 120");
    expect(cards()).toHaveLength(50);
    expect(screen.getByText("120 pending")).toBeInTheDocument();
    expect(screen.getByText("Showing the newest 50 of 120")).toBeInTheDocument();
    // The oldest shown is the 50th newest.
    expect(within(cards()[49]).getByText("Queued proposition 71")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Show more" }));

    await waitFor(() => expect(cards()).toHaveLength(100));
    expect(screen.getByText("Showing the newest 100 of 120")).toBeInTheDocument();
    expect(api.listAssertions).toHaveBeenCalledWith("m1", {
      status: "proposed",
      sort: "-created_at",
      limit: 100,
      offset: 0,
    });
  });

  it("keeps the cards it shows when a decision reloads the queue", async () => {
    const user = userEvent.setup();
    rows = many(120);
    render(<ReviewQueuePage />);
    await screen.findByText("Queued proposition 120");
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await waitFor(() => expect(cards()).toHaveLength(100));

    // A comment typed on another card survives the reload.
    const other = within(cardFor("Queued proposition 119"));
    await user.click(other.getByRole("button", { name: "Request revision" }));
    await user.type(other.getByLabelText("Comment explaining the requested revision"), "Cite it.");

    await user.click(within(cardFor("Queued proposition 120")).getByRole("button", { name: "Reject" }));

    await waitFor(() =>
      expect(screen.queryByText("Queued proposition 120")).not.toBeInTheDocument(),
    );
    expect(cards()).toHaveLength(100);
    expect(screen.getByText("Showing the newest 100 of 119")).toBeInTheDocument();
    expect(
      within(cardFor("Queued proposition 119")).getByLabelText(
        "Comment explaining the requested revision",
      ),
    ).toHaveValue("Cite it.");
  });

  it("merges the open statuses newest first before taking the first 50", async () => {
    const user = userEvent.setup();
    // Interleaved in time: proposed, then revision requested, then disputed.
    rows = Array.from({ length: 90 }, (_, i) => {
      const status = (["proposed", "revision_requested", "disputed"] as const)[i % 3];
      return item({ status, standing: status });
    });
    render(<ReviewQueuePage />);
    await screen.findByText("Queued proposition 88");

    await user.click(screen.getByRole("button", { name: "All open" }));

    await screen.findByText("Queued proposition 90");
    await waitFor(() => expect(cards()).toHaveLength(50));
    const shown = cards().map((card) => card.querySelector(".rq-card__proposition")!.textContent);
    expect(shown).toEqual(
      Array.from({ length: 50 }, (_, i) => `Queued proposition ${90 - i}`),
    );
    expect(screen.getByText("Showing the newest 50 of 90")).toBeInTheDocument();
  });

  it("starts over at 50 cards when the filter changes", async () => {
    const user = userEvent.setup();
    rows = many(120);
    render(<ReviewQueuePage />);
    await screen.findByText("Queued proposition 120");
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await waitFor(() => expect(cards()).toHaveLength(100));

    await user.click(screen.getByRole("button", { name: "Colleague" }));

    await waitFor(() =>
      expect(api.listAssertions).toHaveBeenCalledWith("m1", {
        status: "proposed",
        origin: "user_suggested",
        sort: "-created_at",
        limit: 50,
        offset: 0,
      }),
    );
    await waitFor(() => expect(cards()).toHaveLength(50));
  });
});

describe("ReviewQueuePage authors", () => {
  it("never labels an author by user id", async () => {
    rows = [
      item({ proposition: "By a former member.", author_user_id: "u-gone" }),
      item({ proposition: "By a current member.", author_user_id: "u2" }),
    ];
    render(<ReviewQueuePage />);
    await screen.findByText("By a former member.");

    expect(
      await within(cardFor("By a current member.")).findByText(/Suggested by Noa Contributor/),
    ).toBeInTheDocument();
    expect(within(cardFor("By a former member.")).getByText(/Suggested by Former member/)).toBeInTheDocument();
    expect(screen.queryByText(/u-gone/)).not.toBeInTheDocument();
  });

  it("uses a neutral label when the roster cannot be read", async () => {
    vi.mocked(api.listMatterMembers).mockRejectedValue(new Error("offline"));
    rows = [item({ proposition: "Someone's proposition.", author_user_id: "u2" })];
    render(<ReviewQueuePage />);

    expect(await screen.findByText(/Suggested by Team member/)).toBeInTheDocument();
    expect(screen.queryByText(/Suggested by u2/)).not.toBeInTheDocument();
  });
});
