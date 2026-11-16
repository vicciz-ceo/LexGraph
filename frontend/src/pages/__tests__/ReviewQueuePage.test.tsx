import { act, render, screen, waitFor, within } from "@testing-library/react";
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

/** Each status list is read newest first, one page of 50 at a time. */
const FIRST_PAGE = { sort: "-created_at", limit: 50, offset: 0 };

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
    // The newest page of the proposed inbox, and its total for the chip.
    expect(api.listAssertions).toHaveBeenCalledWith("m1", { status: "proposed", ...FIRST_PAGE });
    expect(api.listAssertions).toHaveBeenCalledWith("m1", { status: "proposed", limit: 1 });
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
      ...FIRST_PAGE,
    });
    expect(api.listAssertions).toHaveBeenCalledWith("m1", { status: "disputed", ...FIRST_PAGE });

    await user.click(screen.getByRole("button", { name: "AI-deduced" }));
    await waitFor(() =>
      expect(api.listAssertions).toHaveBeenCalledWith("m1", {
        status: "proposed",
        origin: "model_suggested",
        ...FIRST_PAGE,
      }),
    );
    expect(api.listAssertions).toHaveBeenCalledWith("m1", {
      status: "disputed",
      origin: "model_suggested",
      ...FIRST_PAGE,
    });
  });

  it("accepts an evidenced assertion without justification and reloads", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    const callsBefore = vi.mocked(api.listAssertions).mock.calls.length;

    // First card is the newest (a1, evidenced) — accept goes straight through.
    await user.click(screen.getAllByRole("button", { name: "Accept" })[0]);

    await waitFor(() => expect(api.acceptAssertion).toHaveBeenCalledWith("a1", undefined, 1));
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
        2,
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
        1,
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

// Review decisions from a queue card (spec addendum "Review decision rules
// (2026-11-16)"): ui:2 (revision on screen, 409), ui:8 (justification),
// ui:9 (status, double submit), ui:24 (per-card form ids).
describe("ReviewQueuePage review decisions", () => {
  function cardFor(proposition: string): HTMLElement {
    const card = screen.getByText(proposition).closest("article");
    if (!card) throw new Error(`no queue card shows "${proposition}"`);
    return card;
  }

  async function waitForReload(callsBefore: number) {
    await waitFor(() =>
      expect(vi.mocked(api.listAssertions).mock.calls.length).toBeGreaterThan(callsBefore),
    );
    await waitFor(() =>
      expect(screen.queryByText("Loading review queue…")).not.toBeInTheDocument(),
    );
  }

  it.each([
    ["Reject", "rejectAssertion"],
    ["Dispute", "disputeAssertion"],
  ] as const)("%s sends the revision shown on the card", async (buttonName, method) => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(userAssertion.proposition);

    await user.click(
      within(cardFor(userAssertion.proposition)).getByRole("button", { name: buttonName }),
    );

    // a2 is shown at revision 2.
    await waitFor(() => expect(api[method]).toHaveBeenCalledWith("a2", 2));
  });

  it("sends the trimmed revision comment with the revision shown on the card", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(userAssertion.proposition);
    const card = within(cardFor(userAssertion.proposition));

    await user.click(card.getByRole("button", { name: "Request revision" }));
    const confirm = card.getByRole("button", { name: "Confirm" });
    expect(confirm).toBeDisabled();
    await user.type(
      card.getByLabelText("Comment explaining the requested revision"),
      "  Cite the clause.  ",
    );
    await user.click(confirm);

    await waitFor(() =>
      expect(api.requestRevision).toHaveBeenCalledWith("a2", "Cite the clause.", 2),
    );
  });

  it("never sends a blank justification and sends the typed one trimmed", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(userAssertion.proposition);
    const card = within(cardFor(userAssertion.proposition));

    // a2 is unsupported: Accept opens the justification form.
    await user.click(card.getByRole("button", { name: "Accept" }));
    const textarea = card.getByLabelText("Justification for accepting without supporting evidence");
    const confirm = card.getByRole("button", { name: "Confirm" });

    await user.type(textarea, "   ");
    expect(confirm).toBeDisabled();
    await user.click(confirm);
    expect(api.acceptAssertion).not.toHaveBeenCalled();

    await user.type(textarea, "Counsel confirmed it.  ");
    await user.click(confirm);
    await waitFor(() =>
      expect(api.acceptAssertion).toHaveBeenCalledWith("a2", "Counsel confirmed it.", 2),
    );
  });

  it("explains a refusal because the card is stale (409), reloads the queue and keeps the notice", async () => {
    vi.mocked(api.acceptAssertion).mockRejectedValue(
      new ApiError(409, "assertion has been modified since expected_revision_number"),
    );
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    const callsBefore = vi.mocked(api.listAssertions).mock.calls.length;

    await user.click(
      within(cardFor(modelAssertion.proposition)).getByRole("button", { name: "Accept" }),
    );

    expect(await screen.findByText(/changed after you opened it/)).toBeInTheDocument();
    await waitForReload(callsBefore);
    expect(screen.getByText(modelAssertion.proposition)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/changed after you opened it/);
    expect(screen.getByRole("alert")).toHaveTextContent(/not recorded/);
    // In plain words, without the API's field name (acceptance run).
    expect(screen.getByRole("alert")).toHaveTextContent("Reason: it was edited.");
    expect(screen.getByRole("alert")).not.toHaveTextContent("expected_revision_number");
  });

  it("records one decision when Reject is double-clicked", async () => {
    vi.mocked(api.rejectAssertion).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);

    await user.dblClick(
      within(cardFor(modelAssertion.proposition)).getByRole("button", { name: "Reject" }),
    );

    expect(api.rejectAssertion).toHaveBeenCalledTimes(1);
  });

  it("disables the decisions on every card while one is being recorded", async () => {
    vi.mocked(api.rejectAssertion).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);

    await user.click(
      within(cardFor(modelAssertion.proposition)).getByRole("button", { name: "Reject" }),
    );

    const accepts = screen.getAllByRole("button", { name: "Accept" });
    expect(accepts).toHaveLength(2);
    for (const button of accepts) expect(button).toBeDisabled();
  });

  it("offers on each card only the decisions its status allows", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    await user.click(screen.getByRole("button", { name: "All open" }));
    await screen.findByText(revisionAssertion.proposition);

    const revisionCard = within(cardFor(revisionAssertion.proposition));
    expect(
      revisionCard.queryByRole("button", { name: "Request revision" }),
    ).not.toBeInTheDocument();
    expect(revisionCard.getByRole("button", { name: "Accept" })).toBeInTheDocument();

    const disputedCard = within(cardFor(disputedAssertion.proposition));
    expect(disputedCard.queryByRole("button", { name: "Dispute" })).not.toBeInTheDocument();
    expect(disputedCard.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("links each card's form label to that card's own textarea", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(userAssertion.proposition);
    const cards = [cardFor(modelAssertion.proposition), cardFor(userAssertion.proposition)];

    for (const card of cards) {
      await user.click(within(card).getByRole("button", { name: "Request revision" }));
    }
    for (const card of cards) {
      const label = within(card).getByText("Comment explaining the requested revision");
      expect(card).toContainElement((label as HTMLLabelElement).control as HTMLElement);
    }

    await user.click(within(cards[1]).getByText("Comment explaining the requested revision"));
    expect(within(cards[1]).getByRole("textbox")).toHaveFocus();
  });

  // Review fe-review-detail:2: removing evidence changes neither the revision
  // nor updated_at, so the card still reads "Evidenced" and its Accept is
  // sent without a justification; the API refuses it with 422.
  it("reloads a card whose evidence was removed meanwhile and asks for the justification (422)", async () => {
    vi.mocked(api.acceptAssertion).mockImplementation(async (_id, justification) => {
      if (!justification) {
        throw new ApiError(
          422,
          "unsupported assertion (no supporting evidence attached) cannot be accepted without a recorded acceptance_justification",
        );
      }
      return makeAssertion({ id: "a1", status: "accepted" });
    });
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    expect(within(cardFor(modelAssertion.proposition)).getByText("Evidenced")).toBeInTheDocument();
    // The supporting passage is removed: the next read of the queue shows it.
    const withoutEvidence = { ...modelAssertion, evidence_status: "awaiting_evidence" as const };
    vi.mocked(api.listAssertions).mockImplementation(
      async (_matterId: string, params: AssertionListParams = {}) =>
        params.status === "proposed"
          ? { items: [withoutEvidence, userAssertion], total: 2 }
          : { items: [], total: 0 },
    );
    const callsBefore = vi.mocked(api.listAssertions).mock.calls.length;

    await user.click(
      within(cardFor(modelAssertion.proposition)).getByRole("button", { name: "Accept" }),
    );

    await waitFor(() => expect(api.acceptAssertion).toHaveBeenCalledWith("a1", undefined, 1));
    await waitForReload(callsBefore);
    const card = within(cardFor(modelAssertion.proposition));
    expect(card.getByText("Awaiting evidence")).toBeInTheDocument();
    const textarea = card.getByLabelText("Justification for accepting without supporting evidence");
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/not recorded/);
    expect(alert).toHaveTextContent(/no longer has supporting evidence/);
    expect(alert).not.toHaveTextContent(/acceptance_justification/);

    await user.type(textarea, "  Counsel confirmed the clause.  ");
    await user.click(card.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(api.acceptAssertion).toHaveBeenLastCalledWith("a1", "Counsel confirmed the clause.", 1),
    );
    expect(api.acceptAssertion).toHaveBeenCalledTimes(2);
  });
});

// Review fe-review-detail:5 (ui:4 on the queue): a system_generated row comes
// from the definition-linking pipeline. The user the run is attributed to did
// not suggest it, and a row without evidence is "System-derived", as on the
// assertion page and in the Knowledge Base.
describe("ReviewQueuePage pipeline-generated assertions", () => {
  const pipelineRow = makeAssertion({
    id: "s1",
    origin: "system_generated",
    assertion_type: "USES_DEFINITION",
    evidence_status: "awaiting_evidence",
    author_user_id: "admin",
    confidence: 0.95,
    proposition: 'Article 796 uses the definition of "Branch office". (reviewed wording)',
  });

  beforeEach(() => {
    vi.mocked(api.listMatterMembers).mockResolvedValue([
      { user: { id: "admin", email: "ada@example.com", display_name: "Ada Admin" }, role: "admin" },
      { user: { id: "u2", email: "noa@example.com", display_name: "Noa Contributor" }, role: "contributor" },
    ]);
    vi.mocked(api.listAssertions).mockImplementation(
      async (_matterId: string, params: AssertionListParams = {}) =>
        params.status === "proposed"
          ? { items: [pipelineRow, awaitingEvidenceAssertion], total: 2 }
          : { items: [], total: 0 },
    );
  });

  function cardFor(proposition: string): HTMLElement {
    const card = screen.getByText(proposition).closest("article");
    if (!card) throw new Error(`no queue card shows "${proposition}"`);
    return card;
  }

  it("names the pipeline, and the user the run is attributed to only as that", async () => {
    render(<ReviewQueuePage />);
    await screen.findByText(pipelineRow.proposition);
    const card = within(cardFor(pipelineRow.proposition));

    expect(
      card.getByText(/^Generated by the definition-linking pipeline · run attributed to Ada Admin · /),
    ).toBeInTheDocument();
    expect(card.queryByText(/Suggested by/)).not.toBeInTheDocument();
    // Other cards keep their byline.
    expect(
      within(cardFor(awaitingEvidenceAssertion.proposition)).getByText(/^Suggested by Noa Contributor · /),
    ).toBeInTheDocument();
  });

  it("labels a pipeline row without evidence System-derived, and still asks for a justification to accept it", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(pipelineRow.proposition);
    const card = within(cardFor(pipelineRow.proposition));

    expect(card.getByText("System-derived")).toBeInTheDocument();
    expect(card.queryByText("Awaiting evidence")).not.toBeInTheDocument();
    // A colleague's row without evidence is still awaiting it.
    expect(
      within(cardFor(awaitingEvidenceAssertion.proposition)).getByText("Awaiting evidence"),
    ).toBeInTheDocument();

    await user.click(card.getByRole("button", { name: "Accept" }));
    expect(api.acceptAssertion).not.toHaveBeenCalled();
    expect(
      card.getByLabelText("Justification for accepting without supporting evidence"),
    ).toBeInTheDocument();
  });
});

// Acceptance run (release candidate): the queue re-read only after a decision
// or a filter change, so a proposal a contributor submitted while the queue
// was open appeared only after leaving the page and coming back, or a reload.
// Clicking the queue's own nav link changes nothing in the URL (AppShell
// signals a hashchange then), and returning to the tab or window is another
// natural moment to look again.
describe("ReviewQueuePage shows proposals submitted meanwhile", () => {
  const submitted = makeAssertion({
    id: "a9",
    created_at: "2026-08-01T09:00:00Z",
    proposition: "A proposal submitted while the queue was open.",
  });

  /** A contributor submits `submitted`: every later read of the proposed inbox lists it. */
  function submitMeanwhile() {
    const before = vi.mocked(api.listAssertions).getMockImplementation()!;
    vi.mocked(api.listAssertions).mockImplementation(async (matterId, params = {}) => {
      const page = await before(matterId, params);
      if (params.status !== "proposed") return page;
      return { items: params.limit === 1 ? page.items : [submitted, ...page.items], total: page.total + 1 };
    });
  }

  function cardFor(proposition: string): HTMLElement {
    const card = screen.getByText(proposition).closest("article");
    if (!card) throw new Error(`no queue card shows "${proposition}"`);
    return card;
  }

  const returns: [string, () => void][] = [
    ["its own nav link is clicked", () => window.dispatchEvent(new HashChangeEvent("hashchange"))],
    ["the window regains focus", () => window.dispatchEvent(new Event("focus"))],
    ["the tab is shown again", () => document.dispatchEvent(new Event("visibilitychange"))],
  ];

  it.each(returns)("re-reads the queue when %s", async (_when, comeBack) => {
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    expect(screen.queryByText(submitted.proposition)).not.toBeInTheDocument();
    submitMeanwhile();

    act(comeBack);

    expect(await screen.findByText(submitted.proposition)).toBeInTheDocument();
    expect(screen.getByText("3 pending")).toBeInTheDocument();
    expect(screen.getByText(modelAssertion.proposition)).toBeInTheDocument();
  });

  it("keeps an open decision form, and what was typed in it, through the re-read", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    const card = within(cardFor(modelAssertion.proposition));
    await user.click(card.getByRole("button", { name: "Request revision" }));
    await user.type(card.getByLabelText("Comment explaining the requested revision"), "Cite clause 8.4.");
    submitMeanwhile();

    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    expect(await screen.findByText(submitted.proposition)).toBeInTheDocument();
    const reread = within(cardFor(modelAssertion.proposition));
    expect(reread.getByLabelText("Comment explaining the requested revision")).toHaveValue("Cite clause 8.4.");
    await waitFor(() => expect(reread.getByRole("button", { name: "Confirm" })).toBeEnabled());
  });

  it("clears an earlier notice when its own nav link is clicked, and keeps it on returning to the tab", async () => {
    vi.mocked(api.rejectAssertion).mockRejectedValue(
      new ApiError(409, "assertion has been modified since expected_revision_number"),
    );
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText(modelAssertion.proposition);
    await user.click(within(cardFor(modelAssertion.proposition)).getByRole("button", { name: "Reject" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/not recorded/);
    await waitFor(() => expect(screen.queryByText("Loading review queue…")).not.toBeInTheDocument());

    const reads = vi.mocked(api.listAssertions).mock.calls.length;
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await waitFor(() => expect(vi.mocked(api.listAssertions).mock.calls.length).toBeGreaterThan(reads));
    expect(screen.getByRole("alert")).toHaveTextContent(/not recorded/);

    act(() => {
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });
});
