// ui:10: every Review Queue card reaches a final rating-summary state,
// including cards past the 30th and cards whose summary request fails, while
// at most 30 summary requests are in flight at once.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../../api/client";
import type { Assertion, AssertionListParams, RatingSummary } from "../../api/types";
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

const TOTAL = 38;

function makeAssertion(index: number, overrides: Partial<Assertion> = {}): Assertion {
  // Index 0 is the oldest; the page sorts newest first, so it renders last.
  return {
    id: `q${index}`,
    organization_id: "o1",
    repository_id: "r1",
    matter_id: "m1",
    assertion_type: "interpretation",
    proposition: `Queue proposition number ${index}`,
    proposition_raw: null,
    subject_entity: { type: "statute", id: "s1" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: index === 0 ? "strong" : "proposed",
    author_user_id: "u2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: new Date(Date.UTC(2026, 5, 1 + index, 10)).toISOString(),
    updated_at: "2026-07-28T10:00:00Z",
    submitted_at: "2026-07-28T10:00:00Z",
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    ...overrides,
  };
}

let queue: Assertion[] = [];

function summaryFor(id: string, overrides: Partial<RatingSummary> = {}): RatingSummary {
  const rated = id === "q0";
  return {
    count: rated ? 2 : 0,
    average: rated ? 4.5 : null,
    median: rated ? 4.5 : null,
    distribution: rated ? { "4": 1, "5": 1 } : {},
    assertion_id: id,
    assertion_revision_id: `rev-${id}-1`,
    current_user_rating: null,
    rationale_count: 0,
    ...overrides,
  };
}

function cards(): HTMLElement[] {
  return Array.from(document.querySelectorAll<HTMLElement>(".rq-card"));
}

beforeEach(() => {
  vi.clearAllMocks();
  queue = Array.from({ length: TOTAL }, (_, index) => makeAssertion(index));
  vi.mocked(api.listMatterMembers).mockResolvedValue([]);
  vi.mocked(api.listAssertions).mockImplementation(
    async (_matterId: string, params: AssertionListParams = {}) =>
      params.status === "proposed"
        ? { items: queue, total: queue.length }
        : { items: [], total: 0 },
  );
  vi.mocked(api.ratingSummary).mockImplementation(async (id: string) => summaryFor(id));
  vi.mocked(api.rejectAssertion).mockResolvedValue(makeAssertion(37, { status: "rejected" }));
});

describe("ReviewQueuePage with more than 30 queued assertions", () => {
  it("resolves the rating summary of every card, including those past the 30th", async () => {
    render(<ReviewQueuePage />);
    expect(await screen.findByText("Queue proposition number 0")).toBeInTheDocument();
    expect(cards()).toHaveLength(TOTAL);

    await waitFor(() => expect(screen.queryAllByText("Loading ratings…")).toHaveLength(0));

    // One summary request per card, not just for the first 30.
    expect(api.ratingSummary).toHaveBeenCalledTimes(TOTAL);
    // The oldest card renders last and is the rated one.
    const oldest = within(cards()[TOTAL - 1]);
    expect(oldest.getByText("Queue proposition number 0")).toBeInTheDocument();
    expect(oldest.getByText("4.5")).toBeInTheDocument();
    expect(oldest.getByText(/based on 2 ratings/)).toBeInTheDocument();
  });

  it("shows a final state, not a loading label, when a summary request fails", async () => {
    vi.mocked(api.ratingSummary).mockImplementation(async (id: string) => {
      if (id === `q${TOTAL - 1}` || id === "q0") throw new Error("boom");
      return summaryFor(id);
    });
    render(<ReviewQueuePage />);
    expect(await screen.findByText("Queue proposition number 0")).toBeInTheDocument();

    await waitFor(() => expect(screen.queryAllByText("Loading ratings…")).toHaveLength(0));
    // Newest card (first batch) and oldest card (second batch).
    for (const card of [cards()[0], cards()[TOTAL - 1]]) {
      expect(within(card).getByText(/Ratings unavailable/)).toBeInTheDocument();
    }
  });

  it("keeps at most 30 summary requests in flight and fills cards newest first", async () => {
    const pending: { id: string; resolve: (summary: RatingSummary) => void }[] = [];
    vi.mocked(api.ratingSummary).mockImplementation(
      (id: string) =>
        new Promise<RatingSummary>((resolve) => {
          pending.push({ id, resolve });
        }),
    );
    render(<ReviewQueuePage />);
    expect(await screen.findByText("Queue proposition number 0")).toBeInTheDocument();

    // First batch only: the 30 newest cards (q37 down to q8).
    await waitFor(() => expect(pending).toHaveLength(30));
    expect(pending[0].id).toBe(`q${TOTAL - 1}`);
    expect(pending[29].id).toBe(`q${TOTAL - 30}`);
    expect(screen.queryAllByText("Loading ratings…")).toHaveLength(TOTAL);

    for (const entry of pending.splice(0)) entry.resolve(summaryFor(entry.id));

    // Second batch: the remaining 8 (q7 down to q0).
    await waitFor(() => expect(pending).toHaveLength(TOTAL - 30));
    await waitFor(() =>
      expect(screen.queryAllByText("Loading ratings…")).toHaveLength(TOTAL - 30),
    );
    for (const entry of pending.splice(0)) entry.resolve(summaryFor(entry.id));
    await waitFor(() => expect(screen.queryAllByText("Loading ratings…")).toHaveLength(0));
    expect(api.ratingSummary).toHaveBeenCalledTimes(TOTAL);
  });

  it("keeps resolved summaries through a reload and never shows a previous revision's ratings", async () => {
    const user = userEvent.setup();
    queue = [makeAssertion(1), makeAssertion(0)];
    render(<ReviewQueuePage />);
    await waitFor(() => expect(screen.getByText("4.5")).toBeInTheDocument());

    // A decision on q1 reloads the queue; meanwhile q0 was revised (revision
    // 2), and its revision-2 summary has not arrived yet.
    let releaseRevisionTwo: (summary: RatingSummary) => void = () => {};
    vi.mocked(api.ratingSummary).mockImplementation((id: string, revision: number) =>
      id === "q0" && revision === 2
        ? new Promise<RatingSummary>((resolve) => {
            releaseRevisionTwo = resolve;
          })
        : Promise.resolve(summaryFor(id)),
    );
    vi.mocked(api.rejectAssertion).mockImplementation(async () => {
      queue = [makeAssertion(1), makeAssertion(0, { current_revision_number: 2 })];
      return makeAssertion(1, { status: "rejected" });
    });
    await user.click(within(cards()[0]).getByRole("button", { name: "Reject" }));

    await waitFor(() => expect(api.ratingSummary).toHaveBeenCalledWith("q0", 2));
    const revised = within(cards()[1]);
    expect(revised.getByText("Queue proposition number 0")).toBeInTheDocument();
    expect(revised.queryByText("4.5")).not.toBeInTheDocument();
    expect(revised.getByText("Loading ratings…")).toBeInTheDocument();
    // The unchanged card kept its summary through the reload.
    expect(within(cards()[0]).queryByText("Loading ratings…")).not.toBeInTheDocument();

    releaseRevisionTwo(summaryFor("q0", { count: 1, average: 2, median: 2, distribution: { "2": 1 } }));
    expect(await revised.findByText("2.0")).toBeInTheDocument();
  });
});
