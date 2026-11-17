// Acceptance run 2: a ruling from a Contested drawer that still shows an
// assertion as disputed after another reviewer ruled on it. A decision changes
// the status but creates no revision, so every ruling sends the status the row
// shows (expected_status) with the revision; the API refuses a stale one with
// 409. The page then says the ruling was not recorded because someone else
// already decided it, and reads the queue again.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Assertion, AssertionListItem } from "../../api/types";

vi.mock("../../app/session", () => ({
  useActiveSession: () => {
    const matter = {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: "reviewer",
    };
    return {
      user: { id: "u-reviewer", email: "reviewer@example.com", display_name: "Rivka Stein" },
      matters: [matter],
      currentMatter: matter,
      role: "reviewer",
    };
  },
}));

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
      listAssertions: vi.fn(),
      ratingSummary: vi.fn(),
      listEvidence: vi.fn(),
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      requestRevision: vi.fn(),
    },
  };
});

import { ApiError, api } from "../../api/client";
import { ContestedPage } from "../ContestedPage";

const mockedApi = vi.mocked(api);

function row(overrides: Partial<Assertion>): AssertionListItem {
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
    status: "disputed",
    standing: "disputed",
    author_user_id: "u-author",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T09:00:00Z",
    updated_at: "2026-07-21T09:00:00Z",
    submitted_at: "2026-07-02T09:00:00Z",
    reviewed_by: "u-other",
    reviewed_at: "2026-07-20T10:00:00Z",
    superseded_by_assertion_id: null,
    current_revision_number: 2,
    evidence_status: "evidenced",
    ratings_summary: null,
    current_user_rating: null,
    ...overrides,
  };
}

const EVIDENCED = row({});
const UNSUPPORTED = row({
  id: "a-2",
  proposition: "Clause 14 caps liability at twice annual fees.",
  evidence_status: "unsupported",
  current_revision_number: 1,
});

const DECIDED_MEANWHILE = (status: string) =>
  `assertion status has changed since expected_status: it is now '${status}'`;

/** The disputed assertions the server lists. */
let disputed: AssertionListItem[] = [];

function rowFor(proposition: string): HTMLElement {
  const tableRow = screen.getByText(proposition).closest("tr");
  if (!tableRow) throw new Error(`no row shows "${proposition}"`);
  return tableRow;
}

async function openDrawer(proposition: string) {
  fireEvent.click(within(rowFor(proposition)).getByRole("button", { name: "Expand row" }));
  await screen.findByRole("button", { name: "Collapse row" });
}

beforeEach(() => {
  vi.clearAllMocks();
  disputed = [EVIDENCED, UNSUPPORTED];
  mockedApi.listAssertions.mockImplementation(async () => ({
    items: disputed,
    total: disputed.length,
  }));
  mockedApi.ratingSummary.mockRejectedValue(new Error("not needed"));
  mockedApi.listEvidence.mockResolvedValue([]);
  mockedApi.acceptAssertion.mockResolvedValue({} as never);
  mockedApi.rejectAssertion.mockResolvedValue({} as never);
  mockedApi.requestRevision.mockResolvedValue({} as never);
});

describe("ContestedPage rulings name the status the row shows", () => {
  it("sends disputed with a rejection and with an acceptance of an evidenced assertion", async () => {
    render(<ContestedPage />);
    await screen.findByText(EVIDENCED.proposition);

    await openDrawer(EVIDENCED.proposition);
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(mockedApi.rejectAssertion).toHaveBeenCalledWith("a-1", 2, "disputed"));
    await waitFor(() => expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2));

    await openDrawer(EVIDENCED.proposition);
    await waitFor(() => expect(screen.getByRole("button", { name: "Accept" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1", undefined, 2, "disputed"),
    );
  });

  it("sends disputed with a justified acceptance and with a revision request", async () => {
    render(<ContestedPage />);
    await screen.findByText(UNSUPPORTED.proposition);

    await openDrawer(UNSUPPORTED.proposition);
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    fireEvent.change(screen.getByLabelText("Acceptance justification"), {
      target: { value: "Confirmed in the board minutes." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm accept" }));
    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith(
        "a-2",
        "Confirmed in the board minutes.",
        1,
        "disputed",
      ),
    );
    await waitFor(() => expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2));

    await openDrawer(EVIDENCED.proposition);
    await waitFor(() => expect(screen.getByRole("button", { name: "Request revision" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Request revision" }));
    fireEvent.change(screen.getByLabelText("Comment explaining the requested revision"), {
      target: { value: "Please cite the amendment clause." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm request" }));
    await waitFor(() =>
      expect(mockedApi.requestRevision).toHaveBeenCalledWith(
        "a-1",
        "Please cite the amendment clause.",
        2,
        "disputed",
      ),
    );
  });
});

describe("ContestedPage ruling on an assertion someone else decided meanwhile", () => {
  it("says it was not recorded because someone else already decided it, and reads the queue again", async () => {
    // Another reviewer accepted a-1 after the queue was read: it is no longer disputed.
    mockedApi.rejectAssertion.mockRejectedValue(new ApiError(409, DECIDED_MEANWHILE("accepted")));
    render(<ContestedPage />);
    await screen.findByText(EVIDENCED.proposition);
    await openDrawer(EVIDENCED.proposition);
    disputed = [UNSUPPORTED];
    // Holds the re-read after the refusal.
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    mockedApi.listAssertions.mockImplementation(async () => {
      await held;
      return { items: disputed, total: disputed.length };
    });

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    expect(mockedApi.rejectAssertion).toHaveBeenCalledWith("a-1", 2, "disputed");
    const notice = await screen.findByRole("alert");
    expect(notice).toHaveTextContent(/not recorded/);
    expect(notice).toHaveTextContent("Reason: someone else already decided it (it is now accepted).");
    expect(notice).not.toHaveTextContent("expected_status");
    // While the queue is read again, a drawer opened meanwhile offers no ruling.
    await openDrawer(UNSUPPORTED.proposition);
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();

    release();

    await waitFor(() => expect(screen.queryByText(EVIDENCED.proposition)).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled());
    expect(screen.getByRole("alert")).toHaveTextContent("someone else already decided it");
    expect(mockedApi.rejectAssertion).toHaveBeenCalledTimes(1);
  });
});
