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
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      disputeAssertion: vi.fn(),
      requestRevision: vi.fn(),
    },
  };
});

vi.mock("../../app/session", () => ({
  useActiveSession: () => ({
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
  }),
}));

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
