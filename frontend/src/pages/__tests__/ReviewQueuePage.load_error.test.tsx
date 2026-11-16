// ui:23: a failed queue load is never presented as an empty ("Queue clear")
// queue, never keeps a pending count it can no longer vouch for, and can be
// retried in place.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../../api/client";
import type { Assertion, AssertionListParams } from "../../api/types";
import { ReviewQueuePage } from "../ReviewQueuePage";

const hoisted = vi.hoisted(() => {
  const matterOne = {
    id: "m1",
    name: "Hollow Oak v. Brightline",
    repository_id: "r1",
    organization_id: "o1",
    role: "reviewer",
  };
  const matterTwo = { ...matterOne, id: "m2", name: "Second Matter" };
  const session = {
    user: { id: "u1", email: "ada@example.com", display_name: "Ada Reviewer" },
    matters: [] as unknown[],
    currentMatter: matterOne,
    role: "reviewer",
  };
  return { session, matterOne, matterTwo };
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

function makeAssertion(overrides: Partial<Assertion> = {}): Assertion {
  return {
    id: "a0",
    organization_id: "o1",
    repository_id: "r1",
    matter_id: "m1",
    assertion_type: "interpretation",
    proposition: "Default proposition",
    proposition_raw: null,
    subject_entity: { type: "statute", id: "s1" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-28T10:00:00Z",
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

const first = makeAssertion({ id: "a1", proposition: "First open proposition." });
const second = makeAssertion({ id: "a2", proposition: "Second open proposition." });

/** While true every list call fails, like a 500 or a dropped connection. */
const failing = { value: false };

beforeEach(() => {
  vi.clearAllMocks();
  failing.value = false;
  hoisted.session.currentMatter = hoisted.matterOne;
  hoisted.session.role = "reviewer";

  vi.mocked(api.listMatterMembers).mockResolvedValue([]);
  vi.mocked(api.ratingSummary).mockRejectedValue(new Error("no summary"));
  vi.mocked(api.acceptAssertion).mockResolvedValue(
    makeAssertion({ id: "a1", status: "accepted" }),
  );
  vi.mocked(api.listAssertions).mockImplementation(
    async (_matterId: string, params: AssertionListParams = {}) => {
      if (failing.value) throw new Error("Internal Server Error");
      if (params.status === "proposed") return { items: [first, second], total: 2 };
      return { items: [], total: 0 };
    },
  );
});

describe("ReviewQueuePage when the queue cannot be loaded", () => {
  it("does not claim the queue is clear when the first load fails", async () => {
    failing.value = true;
    render(<ReviewQueuePage />);

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("Couldn't load the review queue.");
    expect(banner).toHaveTextContent("Internal Server Error");
    expect(screen.queryByText("Queue clear")).not.toBeInTheDocument();
    expect(screen.queryByText(/nothing awaiting review/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\d+ pending/)).not.toBeInTheDocument();
  });

  it("drops the cards and the pending count when a filter change fails", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(first.proposition);
    expect(screen.getByText("2 pending")).toBeInTheDocument();

    failing.value = true;
    await user.click(screen.getByRole("button", { name: "All open" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn't load the review queue.",
    );
    expect(screen.queryByText("Queue clear")).not.toBeInTheDocument();
    expect(screen.queryByText("2 pending")).not.toBeInTheDocument();
    expect(screen.queryByText(first.proposition)).not.toBeInTheDocument();
  });

  it("does not show another matter's pending count after a failed matter switch", async () => {
    const view = render(<ReviewQueuePage />);
    await screen.findByText(first.proposition);
    expect(screen.getByText("2 pending")).toBeInTheDocument();

    failing.value = true;
    hoisted.session.currentMatter = hoisted.matterTwo;
    view.rerender(<ReviewQueuePage />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/awaiting review in Second Matter/)).toBeInTheDocument();
    expect(screen.queryByText("2 pending")).not.toBeInTheDocument();
    expect(screen.queryByText("Queue clear")).not.toBeInTheDocument();
  });

  it("does not report a clear queue when the reload after a recorded decision fails", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(first.proposition);

    vi.mocked(api.acceptAssertion).mockImplementation(async () => {
      failing.value = true; // the decision is recorded; the reload that follows fails
      return makeAssertion({ id: "a1", status: "accepted" });
    });
    await user.click(screen.getAllByRole("button", { name: "Accept" })[0]);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn't load the review queue.",
    );
    expect(screen.queryByText("Queue clear")).not.toBeInTheDocument();
    expect(screen.queryByText(/\d+ pending/)).not.toBeInTheDocument();
  });

  it("offers Retry in the banner and recovers the queue in place", async () => {
    const user = userEvent.setup();
    failing.value = true;
    render(<ReviewQueuePage />);
    await screen.findByRole("alert");
    const callsBefore = vi.mocked(api.listAssertions).mock.calls.length;

    failing.value = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText(first.proposition)).toBeInTheDocument();
    expect(vi.mocked(api.listAssertions).mock.calls.length).toBeGreaterThan(callsBefore);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("2 pending")).toBeInTheDocument();
  });

  it("still shows the empty state when the queue really is empty", async () => {
    vi.mocked(api.listAssertions).mockResolvedValue({ items: [], total: 0 });
    render(<ReviewQueuePage />);

    expect(await screen.findByText("Queue clear")).toBeInTheDocument();
    expect(screen.getByText("0 pending")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await waitFor(() => expect(api.ratingSummary).not.toHaveBeenCalled());
  });
});
