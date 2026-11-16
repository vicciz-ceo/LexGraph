// AssertionDetailPage review actions (spec addendum "Review decision rules
// (2026-11-16)"): every decision carries the revision on screen and a 409 is
// explained and reloaded (ui:2), the justification is never blank (ui:8), and
// only decisions valid for the current status are offered, once (ui:9).

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssertionDetail, RatingSummary } from "../../api/types";

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
      // The detail page also loads the roster (names), the review history
      // and the rationales of the current revision when it mounts.
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
    // The page switches to an assertion's matter through selectMatter (ui:31).
    useSession: () => ({ session, selectMatter: vi.fn() }),
  };
});

import { ApiError, api } from "../../api/client";
import { AssertionDetailPage } from "../AssertionDetailPage";

const mockedApi = vi.mocked(api);

function makeDetail(overrides: Partial<AssertionDetail> = {}): AssertionDetail {
  return {
    id: "a-1",
    organization_id: "org-1",
    repository_id: "repo-1",
    matter_id: "m-1",
    assertion_type: "obligation",
    proposition: "Acme Corp must deliver audited financial statements by 31 March each year.",
    proposition_raw: null,
    subject_entity: { type: "Document", id: "doc-1" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u-2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-10T09:00:00Z",
    submitted_at: "2026-07-02T10:00:00Z",
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 2,
    evidence_status: "evidenced",
    evidence: [],
    ratings_summary: null,
    comments: [],
    revision_history: [],
    ...overrides,
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

const DECISIONS = ["Accept", "Reject", "Dispute", "Request revision"];

function decisionButtons(): string[] {
  return screen
    .queryAllByRole("button")
    .map((button) => button.textContent ?? "")
    .filter((label) => DECISIONS.includes(label));
}

async function renderPage(detail: AssertionDetail = makeDetail()) {
  mockedApi.getAssertion.mockResolvedValue(detail);
  render(<AssertionDetailPage assertionId="a-1" />);
  await screen.findAllByText(detail.proposition);
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
});

describe("AssertionDetailPage review actions", () => {
  it.each([
    ["Reject", "rejectAssertion"],
    ["Dispute", "disputeAssertion"],
  ] as const)("%s sends the revision on screen", async (buttonName, method) => {
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: buttonName }));

    await waitFor(() => expect(mockedApi[method]).toHaveBeenCalledWith("a-1", 2));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it("sends the trimmed revision comment with the revision on screen", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Request revision" }));
    fireEvent.change(screen.getByLabelText("Comment explaining the requested revision"), {
      target: { value: "  Cite the audit clause.  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(mockedApi.requestRevision).toHaveBeenCalledWith("a-1", "Cite the audit clause.", 2),
    );
  });

  it.each(["unsupported", "awaiting_evidence"] as const)(
    "never accepts an assertion with %s evidence on a blank justification, and sends the typed one trimmed",
    async (evidenceStatus) => {
      await renderPage(makeDetail({ evidence_status: evidenceStatus }));

      fireEvent.click(screen.getByRole("button", { name: "Accept" }));
      const textarea = screen.getByLabelText(
        "Justification for accepting without supporting evidence",
      );
      const confirm = screen.getByRole("button", { name: "Confirm" });
      fireEvent.change(textarea, { target: { value: "   " } });
      expect(confirm).toBeDisabled();
      fireEvent.click(confirm);
      expect(mockedApi.acceptAssertion).not.toHaveBeenCalled();

      fireEvent.change(textarea, { target: { value: " Admitted in the reply brief. " } });
      fireEvent.click(confirm);
      await waitFor(() =>
        expect(mockedApi.acceptAssertion).toHaveBeenCalledWith(
          "a-1",
          "Admitted in the reply brief.",
          2,
        ),
      );
    },
  );

  it("explains a refusal because the record is stale (409) and re-fetches it", async () => {
    mockedApi.rejectAssertion.mockRejectedValue(
      new ApiError(409, "assertion has been modified since expected_revision_number"),
    );
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    await waitFor(() => expect(mockedApi.rejectAssertion).toHaveBeenCalledWith("a-1", 2));
    expect(await screen.findByText(/changed after you opened it/)).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/not recorded/);
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it.each(["draft", "withdrawn", "superseded"] as const)(
    "offers no decision on a %s assertion",
    async (status) => {
      await renderPage(makeDetail({ status, standing: status }));

      expect(decisionButtons()).toEqual([]);
      expect(screen.getByText(/no review decision/i)).toBeInTheDocument();
    },
  );

  it("does not offer to accept an assertion that is already accepted", async () => {
    await renderPage(makeDetail({ status: "accepted", standing: "accepted" }));

    expect(decisionButtons()).toEqual(["Reject", "Dispute", "Request revision"]);
  });

  describe("supersede, the fifth decision", () => {
    async function chooseReplacement() {
      mockedApi.relatedAssertions.mockResolvedValue([
        {
          assertion_id: "a-9",
          match_kind: "similar",
          score: 0.8,
          proposition: "A newer accepted reading.",
          status: "accepted",
        },
      ]);
      await renderPage(makeDetail({ status: "accepted", standing: "accepted" }));
      fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
      fireEvent.click(await screen.findByLabelText("A newer accepted reading."));
      fireEvent.click(screen.getByRole("button", { name: "Supersede with selected assertion" }));
    }

    it("sends the revision on screen", async () => {
      mockedApi.supersedeAssertion.mockResolvedValue({} as never);
      await chooseReplacement();

      await waitFor(() =>
        expect(mockedApi.supersedeAssertion).toHaveBeenCalledWith("a-1", "a-9", 2),
      );
      await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    });

    it("explains a refusal because the record is stale (409) and re-fetches it", async () => {
      mockedApi.supersedeAssertion.mockRejectedValue(
        new ApiError(409, "assertion has been modified since expected_revision_number"),
      );
      await chooseReplacement();

      await waitFor(() =>
        expect(mockedApi.supersedeAssertion).toHaveBeenCalledWith("a-1", "a-9", 2),
      );
      expect(await screen.findByText(/changed after you opened it/)).toHaveTextContent(
        /not recorded/,
      );
      await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    });
  });

  it("records one decision when Reject is clicked again before the first one finishes", async () => {
    let finish: () => void = () => {};
    mockedApi.rejectAssertion.mockReturnValue(
      new Promise((resolve) => {
        finish = () => resolve({} as never);
      }),
    );
    await renderPage();
    const reject = screen.getByRole("button", { name: "Reject" });

    act(() => {
      reject.click();
      reject.click();
    });
    fireEvent.click(reject);

    expect(mockedApi.rejectAssertion).toHaveBeenCalledTimes(1);
    expect(reject).toBeDisabled();
    await act(async () => finish());
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });
});

// Review fe-review-detail:0: the decision is recorded before the page shows
// it. Until the re-read record is on screen the page still shows the old
// status, so the panel must stay disabled until then: a double-click must
// not send a second decision (which the API refuses with 409, shown as a
// false "not recorded" banner), and no other decision may be sent against a
// status the reviewer never saw.
describe("one decision until the page shows its result (fe-review-detail:0)", () => {
  /** Holds every further GET /assertions/{id} (the re-read after a decision). */
  function holdReread() {
    let release: (detail: AssertionDetail) => void = () => {};
    const held = new Promise<AssertionDetail>((resolve) => {
      release = resolve;
    });
    mockedApi.getAssertion.mockImplementation(() => held);
    return (detail: AssertionDetail) => release(detail);
  }

  /** The first call records the decision; a repeat is refused like the API does. */
  function refuseRepeat(method: "acceptAssertion" | "rejectAssertion", status: string) {
    let calls = 0;
    mockedApi[method].mockImplementation(async () => {
      calls += 1;
      if (calls > 1) throw new ApiError(409, `assertion is already '${status}'`);
      return {} as never;
    });
  }

  it("keeps Reject disabled after the decision is recorded, until the re-read record is shown", async () => {
    refuseRepeat("rejectAssertion", "rejected");
    await renderPage();
    const release = holdReread();

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    // The decision was recorded and the record is being read again.
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    await act(async () => {});

    // The second click of a double-click lands while the old status is shown.
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(mockedApi.rejectAssertion).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await act(async () => release(makeDetail({ status: "rejected", standing: "rejected" })));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Dispute" })).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mockedApi.rejectAssertion).toHaveBeenCalledTimes(1);
  });

  it("sends no other decision against the status on screen while the re-read is pending", async () => {
    await renderPage();
    const release = holdReread();

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    await act(async () => {});

    // The badge still reads Proposed: a Dispute now would apply to "rejected".
    expect(screen.getByRole("button", { name: "Dispute" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Dispute" }));
    expect(mockedApi.disputeAssertion).not.toHaveBeenCalled();

    await act(async () => release(makeDetail({ status: "rejected", standing: "rejected" })));
    await waitFor(() => expect(screen.getByRole("button", { name: "Dispute" })).toBeEnabled());
    expect(mockedApi.disputeAssertion).not.toHaveBeenCalled();
  });

  it("records one acceptance of an evidenced assertion on a double-click", async () => {
    refuseRepeat("acceptAssertion", "accepted");
    await renderPage();
    const release = holdReread();

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    expect(mockedApi.acceptAssertion).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await act(async () => release(makeDetail({ status: "accepted", standing: "accepted" })));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument(),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mockedApi.acceptAssertion).toHaveBeenCalledTimes(1);
  });

  it("offers no review decision after a supersede until the superseded record is shown", async () => {
    mockedApi.supersedeAssertion.mockResolvedValue({} as never);
    mockedApi.relatedAssertions.mockResolvedValue([
      {
        assertion_id: "a-9",
        match_kind: "similar",
        score: 0.8,
        proposition: "A newer accepted reading.",
        status: "accepted",
      },
    ]);
    await renderPage(makeDetail({ status: "accepted", standing: "accepted" }));
    const release = holdReread();

    fireEvent.click(screen.getByRole("button", { name: /Mark as superseded/ }));
    fireEvent.click(await screen.findByLabelText("A newer accepted reading."));
    fireEvent.click(screen.getByRole("button", { name: "Supersede with selected assertion" }));
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
    await act(async () => {});

    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(mockedApi.rejectAssertion).not.toHaveBeenCalled();

    await act(async () =>
      release(
        makeDetail({ status: "superseded", standing: "superseded", superseded_by_assertion_id: "a-9" }),
      ),
    );
    await waitFor(() => expect(decisionButtons()).toEqual([]));
    expect(screen.getByText(/no review decision/i)).toBeInTheDocument();
    expect(mockedApi.rejectAssertion).not.toHaveBeenCalled();
  });

  it("re-enables the decisions when one fails without changing anything", async () => {
    mockedApi.rejectAssertion.mockRejectedValue(new Error("network down"));
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("network down");
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(mockedApi.getAssertion).toHaveBeenCalledTimes(1);
  });
});

// Review fe-review-detail:2: removing evidence changes neither the revision
// nor updated_at, so an Accept sent without a justification from a page that
// still shows "Evidenced" is refused with 422. That is a stale view: the page
// says so, re-reads the record and asks for the justification.
describe("Accept refused because the evidence was removed meanwhile (fe-review-detail:2)", () => {
  const NO_EVIDENCE_REFUSAL =
    "unsupported assertion (no supporting evidence attached) cannot be accepted without a recorded acceptance_justification";
  const supporting = {
    id: "ev-1",
    assertion_id: "a-1",
    source_span_id: "span-1",
    quote_text: "The tenant must deliver statements by 31 March.",
    document_title: "Master Services Agreement",
    evidence_role: "supports",
    added_by_user_id: "u-2",
    created_at: "2026-07-01T10:05:00Z",
  };

  it("re-reads the record, says why nothing was recorded and opens the justification form", async () => {
    // Refused while no justification is sent, recorded once one is.
    mockedApi.acceptAssertion.mockImplementation(async (_id, justification) => {
      if (!justification) throw new ApiError(422, NO_EVIDENCE_REFUSAL);
      return {} as never;
    });
    await renderPage(makeDetail({ evidence_status: "evidenced", evidence: [supporting] }));
    expect(screen.getByText("Evidenced")).toBeInTheDocument();
    // Someone removes the passage; the next read shows it.
    mockedApi.getAssertion.mockResolvedValue(
      makeDetail({ evidence_status: "awaiting_evidence", evidence: [] }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1", undefined, 2));
    const textarea = await screen.findByLabelText(
      "Justification for accepting without supporting evidence",
    );
    expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Awaiting evidence")).toBeInTheDocument();
    expect(screen.queryByText("The tenant must deliver statements by 31 March.")).not.toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/not recorded/);
    expect(alert).toHaveTextContent(/no longer has supporting evidence/);
    expect(alert).not.toHaveTextContent(/acceptance_justification/);

    fireEvent.change(textarea, { target: { value: "  Admitted in the reply brief. " } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenLastCalledWith(
        "a-1",
        "Admitted in the reply brief.",
        2,
      ),
    );
    expect(mockedApi.acceptAssertion).toHaveBeenCalledTimes(2);
  });

  it("shows the API's reason, without asking again, for a refused acceptance that carried a justification", async () => {
    mockedApi.acceptAssertion.mockRejectedValue(new ApiError(422, NO_EVIDENCE_REFUSAL));
    await renderPage(makeDetail({ evidence_status: "awaiting_evidence" }));

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    fireEvent.change(
      screen.getByLabelText("Justification for accepting without supporting evidence"),
      { target: { value: "<b></b>" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(NO_EVIDENCE_REFUSAL);
    // The form keeps the typed text for another try.
    expect(
      screen.getByLabelText("Justification for accepting without supporting evidence"),
    ).toHaveValue("<b></b>");
  });
});
