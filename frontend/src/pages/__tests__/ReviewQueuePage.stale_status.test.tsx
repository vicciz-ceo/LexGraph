// Acceptance run 2: a decision from a queue card that still shows a status
// another reviewer has replaced. A decision changes the status but creates no
// revision, so each card sends the status it shows (expected_status) with the
// revision; the API refuses a stale one with 409. The card then says the
// decision was not recorded because someone else already decided it, and the
// queue is read again, so the reviewer sees the current status.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api, ApiError } from "../../api/client";
import type { Assertion, AssertionListParams, AssertionStatus } from "../../api/types";
import { ReviewQueuePage } from "../ReviewQueuePage";

const hoisted = vi.hoisted(() => ({
  session: {
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
  },
}));

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

function card(id: string, status: AssertionStatus, proposition: string, created: string): Assertion {
  return {
    id,
    organization_id: "o1",
    repository_id: "r1",
    matter_id: "m1",
    assertion_type: "interpretation",
    proposition,
    proposition_raw: null,
    subject_entity: { type: "statute", id: "s1" },
    object_entity: null,
    origin: "user_suggested",
    status,
    standing: status,
    author_user_id: "u2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: created,
    updated_at: created,
    submitted_at: created,
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
  };
}

const PROPOSED = card("a1", "proposed", "The notice period runs from mailing.", "2026-07-30T09:00:00Z");
const RETURNED = card("a3", "revision_requested", "The deadline was tolled.", "2026-07-29T09:00:00Z");
const DISPUTED = card("a4", "disputed", "Service was completed on 12 March.", "2026-07-28T09:00:00Z");

const DECIDED_MEANWHILE = (status: string) =>
  `assertion status has changed since expected_status: it is now '${status}'`;

/** What the server holds; every read of the queue lists it by status. */
let server: Assertion[] = [];

function cardFor(proposition: string): HTMLElement {
  const article = screen.getByText(proposition).closest("article");
  if (!article) throw new Error(`no queue card shows "${proposition}"`);
  return article;
}

async function showAllOpen(user: ReturnType<typeof userEvent.setup>) {
  render(<ReviewQueuePage />);
  await screen.findByText(PROPOSED.proposition);
  await user.click(screen.getByRole("button", { name: "All open" }));
  await screen.findByText(DISPUTED.proposition);
  await waitFor(() => expect(screen.queryByText("Loading review queue…")).not.toBeInTheDocument());
}

beforeEach(() => {
  vi.clearAllMocks();
  server = [PROPOSED, RETURNED, DISPUTED];
  vi.mocked(api.listAssertions).mockImplementation(
    async (_matterId: string, params: AssertionListParams = {}) => {
      const items = server.filter((item) => item.status === params.status);
      return { items, total: items.length };
    },
  );
  vi.mocked(api.listMatterMembers).mockResolvedValue([]);
  vi.mocked(api.ratingSummary).mockRejectedValue(new Error("not needed"));
  for (const method of ["acceptAssertion", "rejectAssertion", "disputeAssertion", "requestRevision"] as const) {
    vi.mocked(api[method]).mockResolvedValue({} as never);
  }
});

describe("ReviewQueuePage decisions name the status on the card", () => {
  it("sends each card's status with Dispute, Reject and Accept", async () => {
    const user = userEvent.setup();
    await showAllOpen(user);

    await user.click(within(cardFor(PROPOSED.proposition)).getByRole("button", { name: "Dispute" }));
    await waitFor(() => expect(api.disputeAssertion).toHaveBeenCalledWith("a1", 1, "proposed"));
    await waitFor(() => expect(within(cardFor(RETURNED.proposition)).getByRole("button", { name: "Reject" })).toBeEnabled());

    await user.click(within(cardFor(RETURNED.proposition)).getByRole("button", { name: "Reject" }));
    await waitFor(() =>
      expect(api.rejectAssertion).toHaveBeenCalledWith("a3", 1, "revision_requested"),
    );
    await waitFor(() => expect(within(cardFor(DISPUTED.proposition)).getByRole("button", { name: "Accept" })).toBeEnabled());

    await user.click(within(cardFor(DISPUTED.proposition)).getByRole("button", { name: "Accept" }));
    await waitFor(() =>
      expect(api.acceptAssertion).toHaveBeenCalledWith("a4", undefined, 1, "disputed"),
    );
  });

  it("sends the card's status with a revision request", async () => {
    const user = userEvent.setup();
    await showAllOpen(user);
    const disputed = within(cardFor(DISPUTED.proposition));

    await user.click(disputed.getByRole("button", { name: "Request revision" }));
    await user.type(disputed.getByLabelText("Comment explaining the requested revision"), "Cite it.");
    await user.click(disputed.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(api.requestRevision).toHaveBeenCalledWith("a4", "Cite it.", 1, "disputed"),
    );
  });
});

describe("ReviewQueuePage decision on a card someone else decided meanwhile", () => {
  it("says it was not recorded because someone else already decided it, and drops the card", async () => {
    // Another reviewer accepted a1 after the queue was read: it left the queue.
    vi.mocked(api.disputeAssertion).mockImplementation(async () => {
      throw new ApiError(409, DECIDED_MEANWHILE("accepted"));
    });
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(PROPOSED.proposition);
    server = [{ ...PROPOSED, status: "accepted", standing: "accepted" }, RETURNED, DISPUTED];
    const reads = vi.mocked(api.listAssertions).mock.calls.length;

    await user.click(within(cardFor(PROPOSED.proposition)).getByRole("button", { name: "Dispute" }));

    expect(api.disputeAssertion).toHaveBeenCalledWith("a1", 1, "proposed");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/not recorded/);
    expect(alert).toHaveTextContent("Reason: someone else already decided it (it is now accepted).");
    expect(alert).not.toHaveTextContent("expected_status");
    await waitFor(() => expect(vi.mocked(api.listAssertions).mock.calls.length).toBeGreaterThan(reads));
    await waitFor(() => expect(screen.queryByText(PROPOSED.proposition)).not.toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent("someone else already decided it");
    expect(screen.getByText("Queue clear")).toBeInTheDocument();
  });

  it("shows the card's current status after the refusal, and the next decision names it", async () => {
    // Another reviewer disputed a1 meanwhile: it stays in the open queue.
    vi.mocked(api.rejectAssertion).mockImplementation(async (_id, _revision, status) => {
      if (status !== "disputed") throw new ApiError(409, DECIDED_MEANWHILE("disputed"));
      return {} as never;
    });
    const user = userEvent.setup();
    await showAllOpen(user);
    server = [{ ...PROPOSED, status: "disputed", standing: "disputed" }, RETURNED, DISPUTED];
    // Holds the re-read after the refusal.
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const listed = vi.mocked(api.listAssertions).getMockImplementation()!;
    vi.mocked(api.listAssertions).mockImplementation(async (matterId, params) => {
      await held;
      return listed(matterId, params);
    });

    await user.click(within(cardFor(PROPOSED.proposition)).getByRole("button", { name: "Reject" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Reason: someone else already decided it (it is now disputed).",
    );
    // No decision while the queue is read again: the card still reads Proposed.
    const stale = within(cardFor(PROPOSED.proposition));
    expect(stale.getByText("Proposed")).toBeInTheDocument();
    expect(stale.getByRole("button", { name: "Reject" })).toBeDisabled();

    release();
    const current = await waitFor(() => {
      const shown = within(cardFor(PROPOSED.proposition));
      expect(shown.getByText("Disputed")).toBeInTheDocument();
      return shown;
    });
    expect(current.queryByRole("button", { name: "Dispute" })).not.toBeInTheDocument();
    await waitFor(() => expect(current.getByRole("button", { name: "Reject" })).toBeEnabled());
    expect(screen.getByRole("alert")).toHaveTextContent("someone else already decided it");

    await user.click(current.getByRole("button", { name: "Reject" }));

    await waitFor(() => expect(api.rejectAssertion).toHaveBeenLastCalledWith("a1", 1, "disputed"));
    expect(api.rejectAssertion).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });
});
