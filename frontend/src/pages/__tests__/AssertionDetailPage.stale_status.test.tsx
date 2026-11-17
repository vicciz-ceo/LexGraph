// Acceptance run 2: a review decision from an assertion page that still shows
// a status another reviewer has replaced (proposed at revision 2, accepted
// meanwhile, still revision 2) overwrote that decision without a warning. A
// decision changes the status but creates no revision, so the page sends the
// status on screen (expected_status) with the revision; the API refuses a
// stale one with 409. The page then says the decision was not recorded
// because someone else already decided it, and shows the current status.

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssertionDetail, AssertionStatus, RatingSummary } from "../../api/types";

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
      getAssertion: vi.fn(),
      relatedAssertions: vi.fn(),
      ratingSummary: vi.fn(),
      listRatings: vi.fn(),
      history: vi.fn(),
      listMatterMembers: vi.fn(),
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      disputeAssertion: vi.fn(),
      requestRevision: vi.fn(),
      supersedeAssertion: vi.fn(),
    },
  };
});

vi.mock("../../app/session", () => {
  const session = {
    user: { id: "u-1", email: "ada@example.com", display_name: "Ada Lovelace" },
    currentMatter: {
      id: "m-1",
      name: "Acme acquisition",
      repository_id: "repo-1",
      organization_id: "org-1",
      role: "reviewer",
    },
    role: "reviewer",
    matters: [],
  };
  return {
    useActiveSession: () => session,
    useSession: () => ({ session, selectMatter: vi.fn() }),
  };
});

import { ApiError, api } from "../../api/client";
import { AssertionDetailPage } from "../AssertionDetailPage";

const mockedApi = vi.mocked(api);

const PROPOSITION = "Acme Corp must deliver audited financial statements by 31 March each year.";

function detailIn(status: AssertionStatus): AssertionDetail {
  return {
    id: "a-1",
    organization_id: "org-1",
    repository_id: "repo-1",
    matter_id: "m-1",
    assertion_type: "obligation",
    proposition: PROPOSITION,
    proposition_raw: null,
    subject_entity: { type: "Document", id: "doc-1" },
    object_entity: null,
    origin: "user_suggested",
    status,
    standing: status,
    author_user_id: "u-2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-10T09:00:00Z",
    submitted_at: "2026-07-02T10:00:00Z",
    reviewed_by: status === "proposed" ? null : "u-3",
    reviewed_at: status === "proposed" ? null : "2026-07-11T09:00:00Z",
    superseded_by_assertion_id: null,
    current_revision_number: 2,
    evidence_status: "evidenced",
    evidence: [],
    ratings_summary: null,
    comments: [],
    revision_history: [],
  };
}

const emptySummary: RatingSummary = {
  count: 0,
  average: null,
  median: null,
  distribution: {},
  assertion_id: "a-1",
  assertion_revision_id: "rev-2",
  current_user_rating: null,
  rationale_count: 0,
};

const DECIDED_MEANWHILE = (status: string) =>
  `assertion status has changed since expected_status: it is now '${status}'`;

function statusBadge(): string {
  return document.querySelector(".adp-meta .badge")?.textContent ?? "";
}

/** Holds every further GET /assertions/{id} until released with a record. */
function holdReread() {
  let release: (detail: AssertionDetail) => void = () => {};
  const held = new Promise<AssertionDetail>((resolve) => {
    release = resolve;
  });
  mockedApi.getAssertion.mockImplementation(() => held);
  return (detail: AssertionDetail) => release(detail);
}

async function renderShowing(status: AssertionStatus) {
  mockedApi.getAssertion.mockResolvedValue(detailIn(status));
  render(<AssertionDetailPage assertionId="a-1" />);
  await screen.findAllByText(PROPOSITION);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.relatedAssertions.mockResolvedValue([]);
  mockedApi.ratingSummary.mockResolvedValue(emptySummary);
  mockedApi.listRatings.mockResolvedValue([]);
  mockedApi.history.mockResolvedValue([]);
  mockedApi.listMatterMembers.mockResolvedValue([]);
  mockedApi.acceptAssertion.mockResolvedValue({} as never);
  mockedApi.rejectAssertion.mockResolvedValue({} as never);
  mockedApi.disputeAssertion.mockResolvedValue({} as never);
  mockedApi.requestRevision.mockResolvedValue({} as never);
  mockedApi.supersedeAssertion.mockResolvedValue({} as never);
});

describe("AssertionDetailPage decisions name the status on screen", () => {
  it.each([
    ["proposed", "Reject", "rejectAssertion"],
    ["accepted", "Dispute", "disputeAssertion"],
    ["disputed", "Reject", "rejectAssertion"],
    ["rejected", "Dispute", "disputeAssertion"],
  ] as const)("%s assertion: %s sends that status", async (status, button, method) => {
    await renderShowing(status);

    fireEvent.click(screen.getByRole("button", { name: button }));

    await waitFor(() => expect(mockedApi[method]).toHaveBeenCalledWith("a-1", 2, status));
  });

  it("sends the status with an acceptance", async () => {
    await renderShowing("revision_requested");

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1", undefined, 2, "revision_requested"),
    );
  });

  it("sends the status with a revision request", async () => {
    await renderShowing("disputed");

    fireEvent.click(screen.getByRole("button", { name: "Request revision" }));
    fireEvent.change(screen.getByLabelText("Comment explaining the requested revision"), {
      target: { value: "Cite the audit clause." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(mockedApi.requestRevision).toHaveBeenCalledWith("a-1", "Cite the audit clause.", 2, "disputed"),
    );
  });

  it("sends the status with a supersede", async () => {
    mockedApi.relatedAssertions.mockResolvedValue([
      { assertion_id: "a-9", match_kind: "similar", score: 0.8, proposition: "A newer reading.", status: "accepted" },
    ]);
    await renderShowing("accepted");

    fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
    fireEvent.click(await screen.findByLabelText("A newer reading."));
    fireEvent.click(screen.getByRole("button", { name: "Supersede with selected assertion" }));

    await waitFor(() =>
      expect(mockedApi.supersedeAssertion).toHaveBeenCalledWith("a-1", "a-9", 2, "accepted"),
    );
  });
});

describe("AssertionDetailPage decision on an assertion someone else decided meanwhile", () => {
  it("says it was not recorded because someone else already decided it, and shows the current status", async () => {
    // Accepted by another reviewer after this page loaded it as proposed.
    mockedApi.rejectAssertion.mockImplementation(async (_id, _revision, status) => {
      if (status !== "accepted") throw new ApiError(409, DECIDED_MEANWHILE("accepted"));
      return {} as never;
    });
    await renderShowing("proposed");
    expect(statusBadge()).toBe("Proposed");
    const release = holdReread();

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    expect(mockedApi.rejectAssertion).toHaveBeenCalledWith("a-1", 2, "proposed");
    const notice = await screen.findByText(/someone else already decided it/);
    expect(notice).toHaveTextContent(/not recorded/);
    expect(notice).toHaveTextContent("Reason: someone else already decided it (it is now accepted).");
    expect(notice).not.toHaveTextContent("expected_status");
    // Until the record read again is shown, no decision is offered against
    // the status still on screen.
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    expect(statusBadge()).toBe("Proposed");
    expect(screen.getByRole("button", { name: "Dispute" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Dispute" }));
    expect(mockedApi.disputeAssertion).not.toHaveBeenCalled();

    await act(async () => release(detailIn("accepted")));

    await waitFor(() => expect(statusBadge()).toBe("Accepted"));
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(screen.getByText(/someone else already decided it/)).toBeInTheDocument();
    expect(mockedApi.rejectAssertion).toHaveBeenCalledTimes(1);

    // Deciding again on what is now shown names the current status.
    mockedApi.getAssertion.mockResolvedValue(detailIn("rejected"));
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(mockedApi.rejectAssertion).toHaveBeenLastCalledWith("a-1", 2, "accepted"));
    await waitFor(() => expect(statusBadge()).toBe("Rejected"));
    expect(screen.queryByText(/not recorded/)).not.toBeInTheDocument();
  });

  it("refuses a supersede the same way and stops offering it once the record shows another status", async () => {
    mockedApi.relatedAssertions.mockResolvedValue([
      { assertion_id: "a-9", match_kind: "similar", score: 0.8, proposition: "A newer reading.", status: "accepted" },
    ]);
    mockedApi.supersedeAssertion.mockRejectedValue(new ApiError(409, DECIDED_MEANWHILE("disputed")));
    await renderShowing("accepted");
    mockedApi.getAssertion.mockResolvedValue(detailIn("disputed"));

    fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
    fireEvent.click(await screen.findByLabelText("A newer reading."));
    fireEvent.click(screen.getByRole("button", { name: "Supersede with selected assertion" }));

    await waitFor(() =>
      expect(mockedApi.supersedeAssertion).toHaveBeenCalledWith("a-1", "a-9", 2, "accepted"),
    );
    expect(await screen.findByText(/someone else already decided it/)).toHaveTextContent(
      "Reason: someone else already decided it (it is now disputed).",
    );
    await waitFor(() => expect(statusBadge()).toBe("Disputed"));
    expect(screen.queryByRole("button", { name: /Mark as superseded/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Supersede with selected assertion" })).not.toBeInTheDocument();
  });
});
