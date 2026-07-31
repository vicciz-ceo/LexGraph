import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api, ApiError } from "../../api/client";
import type {
  Assertion,
  AssertionListParams,
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

const modelAssertion = makeAssertion({
  id: "a1",
  origin: "model_suggested",
  confidence: 0.87,
  standing: "probable",
  jurisdiction: "IL",
  created_at: "2026-07-30T09:00:00Z",
  proposition:
    "The 2024 amendment applies retroactively to leases signed before its effective date.",
});

const userAssertion = makeAssertion({
  id: "a2",
  origin: "user_suggested",
  evidence_status: "unsupported",
  current_revision_number: 2,
  created_at: "2026-07-28T09:00:00Z",
  proposition: "Clause 12 of the master lease survives early termination.",
});

const revisionAssertion = makeAssertion({
  id: "a3",
  status: "revision_requested",
  standing: "revision_requested",
  created_at: "2026-07-27T09:00:00Z",
  proposition: "The filing deadline was tolled during the stay.",
});

const disputedAssertion = makeAssertion({
  id: "a4",
  status: "disputed",
  standing: "disputed",
  created_at: "2026-07-26T09:00:00Z",
  proposition: "Service of process was completed on 12 March.",
});

const awaitingEvidenceAssertion = makeAssertion({
  id: "a5",
  origin: "user_suggested",
  evidence_status: "awaiting_evidence",
  current_revision_number: 1,
  created_at: "2026-07-29T09:00:00Z",
  proposition: "The notice period runs from the date of mailing, not receipt.",
});

const summaryA1: RatingSummary = {
  count: 5,
  average: 3.8,
  median: 4,
  distribution: { "1": 0, "2": 1, "3": 1, "4": 2, "5": 1 },
  assertion_id: "a1",
  assertion_revision_id: "rev-a1-1",
  current_user_rating: null,
  rationale_count: 2,
};

beforeEach(() => {
  vi.clearAllMocks();
  hoisted.session.role = "reviewer";
  hoisted.session.currentMatter.role = "reviewer";

  // Backend GET /matters/{id}/members returns a bare JSON array (see
  // backend/app/routers/workspace.py::list_members), not { items: [...] }.
  vi.mocked(api.listMatterMembers).mockResolvedValue([
    {
      user: { id: "u1", email: "ada@example.com", display_name: "Ada Reviewer" },
      role: "reviewer",
    },
    {
      user: { id: "u2", email: "noa@example.com", display_name: "Noa Contributor" },
      role: "contributor",
    },
  ]);

  vi.mocked(api.listAssertions).mockImplementation(
    async (_matterId: string, params: AssertionListParams = {}) => {
      if (params.status === "proposed") {
        let items = [modelAssertion, userAssertion];
        if (params.origin) items = items.filter((a) => a.origin === params.origin);
        return { items, total: items.length };
      }
      if (params.status === "revision_requested") {
        return { items: [revisionAssertion], total: 1 };
      }
      if (params.status === "disputed") {
        return { items: [disputedAssertion], total: 1 };
      }
      return { items: [], total: 0 };
    },
  );

  vi.mocked(api.ratingSummary).mockImplementation(async (id: string) =>
    id === "a1"
      ? summaryA1
      : {
          ...summaryA1,
          count: 0,
          average: null,
          median: null,
          distribution: {},
          assertion_id: id,
          rationale_count: 0,
        },
  );

  vi.mocked(api.acceptAssertion).mockResolvedValue(
    makeAssertion({ id: "a1", status: "accepted" }),
  );
  vi.mocked(api.rejectAssertion).mockResolvedValue(
    makeAssertion({ id: "a1", status: "rejected" }),
  );
});

describe("ReviewQueuePage", () => {
  it("loads the proposed queue with authors, indicators, and rating summaries", async () => {
    render(<ReviewQueuePage />);

    expect(await screen.findByText(modelAssertion.proposition)).toBeInTheDocument();
    expect(screen.getByText(userAssertion.proposition)).toBeInTheDocument();
    expect(api.listAssertions).toHaveBeenCalledWith("m1", { status: "proposed" });
    expect(api.listMatterMembers).toHaveBeenCalledWith("m1");

    // Pending chip reflects the full proposed inbox.
    expect(screen.getByText("2 pending")).toBeInTheDocument();

    // Author ids resolved to display names.
    expect(screen.getAllByText(/Suggested by Noa Contributor/)).toHaveLength(2);

    // Three separate indicators: model confidence, evidence status, status badge.
    expect(screen.getByText(/Model confidence 87%/)).toBeInTheDocument();
    expect(screen.getByText("Unsupported evidence")).toBeInTheDocument();
    expect(screen.getByText("probable standing")).toBeInTheDocument();

    // Rating summary fetched per current revision and rendered.
    expect(await screen.findByText("3.8")).toBeInTheDocument();
    expect(api.ratingSummary).toHaveBeenCalledWith("a1", 1);
    expect(api.ratingSummary).toHaveBeenCalledWith("a2", 2);
  });

  it("queries each open status for All open and applies the origin filter", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);

    await user.click(screen.getByRole("button", { name: "All open" }));
    expect(await screen.findByText(revisionAssertion.proposition)).toBeInTheDocument();
    expect(screen.getByText(disputedAssertion.proposition)).toBeInTheDocument();
    expect(api.listAssertions).toHaveBeenCalledWith("m1", {
      status: "revision_requested",
    });
    expect(api.listAssertions).toHaveBeenCalledWith("m1", { status: "disputed" });

    await user.click(screen.getByRole("button", { name: "AI-deduced" }));
    await waitFor(() =>
      expect(api.listAssertions).toHaveBeenCalledWith("m1", {
        status: "proposed",
        origin: "model_suggested",
      }),
    );
    expect(api.listAssertions).toHaveBeenCalledWith("m1", {
      status: "disputed",
      origin: "model_suggested",
    });
  });

  it("accepts an evidenced assertion without justification and reloads", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    const callsBefore = vi.mocked(api.listAssertions).mock.calls.length;

    // First card is the newest (a1, evidenced) — accept goes straight through.
    await user.click(screen.getAllByRole("button", { name: "Accept" })[0]);

    await waitFor(() => expect(api.acceptAssertion).toHaveBeenCalledWith("a1", undefined));
    await waitFor(() =>
      expect(vi.mocked(api.listAssertions).mock.calls.length).toBeGreaterThan(callsBefore),
    );
  });

  it("routes acceptance of unsupported assertions through the justification flow", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(userAssertion.proposition);

    // Second card is a2 (unsupported): Accept opens the justification form.
    await user.click(screen.getAllByRole("button", { name: "Accept" })[1]);
    expect(api.acceptAssertion).not.toHaveBeenCalled();

    const textarea = await screen.findByLabelText(
      "Justification for accepting without supporting evidence",
    );
    await user.type(textarea, "Counsel confirmed the clause against the executed original.");
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(api.acceptAssertion).toHaveBeenCalledWith(
        "a2",
        "Counsel confirmed the clause against the executed original.",
      ),
    );
  });

  it("resolves the author's display name from the bare members array (D2)", async () => {
    // Backend returns a bare array, not { items: [...] }. Before the fix,
    // res.items is undefined and the lookup silently fails, so the card
    // falls back to the raw author id instead of the display name.
    vi.mocked(api.listMatterMembers).mockResolvedValue([
      { user: { id: "admin", email: "a@x", display_name: "Ada Admin" }, role: "admin" },
    ]);
    vi.mocked(api.listAssertions).mockImplementation(
      async (_matterId: string, params: AssertionListParams = {}) => {
        if (params.status === "proposed") {
          const items = [makeAssertion({ id: "a9", author_user_id: "admin" })];
          return { items, total: items.length };
        }
        return { items: [], total: 0 };
      },
    );

    render(<ReviewQueuePage />);

    expect(await screen.findByText(/Suggested by Ada Admin/)).toBeInTheDocument();
    expect(screen.queryByText(/Suggested by admin\b/)).not.toBeInTheDocument();
  });

  it("opens the justification form before accepting an assertion awaiting evidence (D3)", async () => {
    // Backend requires an acceptance justification whenever there is no
    // supporting evidence — both "unsupported" and "awaiting_evidence".
    // Before the fix, only "unsupported" opens the pre-flight form and
    // "awaiting_evidence" fires acceptAssertion immediately.
    const user = userEvent.setup();
    vi.mocked(api.listAssertions).mockImplementation(
      async (_matterId: string, params: AssertionListParams = {}) => {
        if (params.status === "proposed") {
          return { items: [awaitingEvidenceAssertion], total: 1 };
        }
        return { items: [], total: 0 };
      },
    );

    render(<ReviewQueuePage />);
    await screen.findByText(awaitingEvidenceAssertion.proposition);

    await user.click(screen.getByRole("button", { name: "Accept" }));
    expect(api.acceptAssertion).not.toHaveBeenCalled();

    const textarea = await screen.findByLabelText(
      "Justification for accepting without supporting evidence",
    );
    await user.type(textarea, "Confirmed via opposing counsel's admission letter.");
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(api.acceptAssertion).toHaveBeenCalledWith(
        "a5",
        "Confirmed via opposing counsel's admission letter.",
      ),
    );
  });

  it("hides review actions from contributors and shows the reviewer note", async () => {
    hoisted.session.role = "contributor";
    hoisted.session.currentMatter.role = "contributor";
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);

    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(screen.getAllByText("Reviewer role required to decide.")).toHaveLength(2);
    // Read-only signal still present.
    expect(await screen.findByText("3.8")).toBeInTheDocument();
  });

  it("surfaces a friendly message when a review action returns 403", async () => {
    vi.mocked(api.rejectAssertion).mockRejectedValue(new ApiError(403, "Forbidden"));
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);

    await user.click(screen.getAllByRole("button", { name: "Reject" })[0]);

    expect(
      await screen.findByText(/does not permit review decisions/),
    ).toBeInTheDocument();
  });

  it("shows the empty state when nothing awaits review", async () => {
    vi.mocked(api.listAssertions).mockResolvedValue({ items: [], total: 0 });
    render(<ReviewQueuePage />);

    expect(await screen.findByText("Queue clear")).toBeInTheDocument();
    expect(screen.getByText("0 pending")).toBeInTheDocument();
    expect(api.ratingSummary).not.toHaveBeenCalled();
  });

  it("shows an error banner when the queue fails to load", async () => {
    vi.mocked(api.listAssertions).mockRejectedValue(new Error("network down"));
    render(<ReviewQueuePage />);

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("Couldn't load the review queue.");
    expect(banner).toHaveTextContent("network down");
  });
});
