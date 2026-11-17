// ContestedPage — disputed-assertion adjudication queue.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Assertion,
  AssertionListItem,
  Evidence,
  MatterRoleName,
  RatingSummary,
} from "../../api/types";

const mocks = vi.hoisted(() => ({
  role: "reviewer" as MatterRoleName,
}));

vi.mock("../../app/session", () => ({
  useActiveSession: () => {
    const matter = {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: mocks.role,
    };
    return {
      user: { id: "u-reviewer", email: "reviewer@example.com", display_name: "Rivka Stein" },
      matters: [matter],
      currentMatter: matter,
      role: mocks.role,
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

function makeAssertion(overrides: Partial<Assertion> = {}): Assertion {
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
    jurisdiction: "IL",
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T09:00:00Z",
    updated_at: "2026-07-21T09:00:00Z",
    submitted_at: "2026-07-02T09:00:00Z",
    reviewed_by: "u-reviewer",
    reviewed_at: "2026-07-20T10:00:00Z",
    superseded_by_assertion_id: null,
    current_revision_number: 2,
    evidence_status: "evidenced",
    ...overrides,
  };
}

const evidencedAssertion = makeAssertion();
const unsupportedAssertion = makeAssertion({
  id: "a-2",
  proposition: "Clause 14 caps liability at twice annual fees.",
  origin: "model_suggested",
  confidence: 0.82,
  evidence_status: "unsupported",
  current_revision_number: 1,
  jurisdiction: null,
});

function makeSummary(overrides: Partial<RatingSummary> = {}): RatingSummary {
  return {
    count: 4,
    average: 3.5,
    median: 3.5,
    distribution: { "2": 1, "3": 1, "4": 1, "5": 1 },
    assertion_id: "a-1",
    assertion_revision_id: "rev-2",
    current_user_rating: null,
    rationale_count: 2,
    ...overrides,
  };
}

const evidenceItems: Evidence[] = [
  {
    id: "ev-1",
    assertion_id: "a-1",
    source_span_id: "span-101",
    evidence_role: "supports",
    added_by_user_id: "u-author",
    created_at: "2026-07-03T09:00:00Z",
  },
  {
    id: "ev-2",
    assertion_id: "a-1",
    source_span_id: "span-102",
    evidence_role: "contradicts",
    added_by_user_id: "u-reviewer",
    created_at: "2026-07-04T09:00:00Z",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  mocks.role = "reviewer";
  mockedApi.listAssertions.mockResolvedValue({
    items: [evidencedAssertion, unsupportedAssertion],
    total: 2,
  });
  mockedApi.ratingSummary.mockImplementation(async (id: string) =>
    id === "a-1"
      ? makeSummary()
      : makeSummary({
          assertion_id: id,
          count: 0,
          average: null,
          median: null,
          distribution: {},
        }),
  );
  mockedApi.listEvidence.mockResolvedValue(evidenceItems);
  mockedApi.acceptAssertion.mockResolvedValue(makeAssertion({ status: "accepted" }));
  mockedApi.rejectAssertion.mockResolvedValue(makeAssertion({ status: "rejected" }));
  mockedApi.requestRevision.mockResolvedValue(
    makeAssertion({ status: "revision_requested" }),
  );
});

async function renderQueue() {
  render(<ContestedPage />);
  await screen.findByText("The 2021 lease amendment extends the term to 2030.");
}

describe("ContestedPage", () => {
  it("loads disputed assertions for the current matter and renders the queue", async () => {
    await renderQueue();

    // The first page of the matter's disputed assertions.
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {
      status: "disputed",
      limit: 50,
      offset: 0,
    });
    // Count chip in the header.
    expect(screen.getByText("2")).toBeInTheDocument();
    // Origin chips per domain vocabulary.
    expect(screen.getByText("Colleague")).toBeInTheDocument();
    expect(screen.getByText("AI-deduced")).toBeInTheDocument();
    // Evidence status chips.
    expect(screen.getByText("Evidenced")).toBeInTheDocument();
    expect(screen.getByText("Unsupported")).toBeInTheDocument();
    // Rating strength: summary text for the rated row, em-dash for the unrated one.
    expect(await screen.findByText("avg 3.5 · 4 ratings")).toBeInTheDocument();
    expect(await screen.findByText("—")).toBeInTheDocument();
    // Proposition links to the assertion detail route.
    expect(
      screen.getByRole("link", {
        name: "The 2021 lease amendment extends the term to 2030.",
      }),
    ).toHaveAttribute("href", "#/assertions/a-1");
  });

  it("expands a row into the drawer: evidence list and rating tiles", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);

    expect(mockedApi.listEvidence).toHaveBeenCalledWith("a-1");
    // The fixture spans are unresolvable in this matter; their ids are not shown.
    expect(await screen.findAllByText(/Source span unavailable/)).toHaveLength(2);
    expect(screen.queryByText(/span-101/)).not.toBeInTheDocument();
    expect(screen.getByText("supports")).toBeInTheDocument();
    expect(screen.getByText("contradicts")).toBeInTheDocument();
    expect(screen.getByText("Count")).toBeInTheDocument();
    expect(screen.getByText("Average")).toBeInTheDocument();
    expect(screen.getByText("Median")).toBeInTheDocument();
  });

  it("accepts an evidenced assertion directly and refreshes the queue", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1", undefined, 2, "disputed"),
    );
    await waitFor(() => expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2));
  });

  it("requires a justification before accepting an unsupported assertion", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[1]);
    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));

    // No API call yet — the inline justification confirm appears instead.
    expect(mockedApi.acceptAssertion).not.toHaveBeenCalled();
    const confirm = screen.getByRole("button", { name: "Confirm accept" });
    expect(confirm).toBeDisabled();

    // Model confidence stays a separate indicator in the drawer (0.82 → 82%).
    expect(screen.getByTestId("model-confidence-indicator")).toHaveTextContent("82%");

    fireEvent.change(screen.getByLabelText("Acceptance justification"), {
      target: { value: "Confirmed against the signed engagement letter." },
    });
    fireEvent.click(confirm);

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith(
        "a-2",
        "Confirmed against the signed engagement letter.",
        1,
        "disputed",
      ),
    );
  });

  it("requests a revision with a required comment", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Request revision" }));

    const confirm = screen.getByRole("button", { name: "Confirm request" });
    expect(confirm).toBeDisabled();
    expect(mockedApi.requestRevision).not.toHaveBeenCalled();

    fireEvent.change(
      screen.getByLabelText("Comment explaining the requested revision"),
      { target: { value: "Please cite the amendment clause." } },
    );
    fireEvent.click(confirm);

    await waitFor(() =>
      expect(mockedApi.requestRevision).toHaveBeenCalledWith(
        "a-1",
        "Please cite the amendment clause.",
        2,
        "disputed",
      ),
    );
  });

  it("hides adjudication actions from contributors and shows the role note", async () => {
    mocks.role = "contributor";
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    await screen.findAllByText(/Source span unavailable/);

    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Request revision" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Reviewer role required to adjudicate.")).toBeInTheDocument();
  });

  it("renders the empty state when nothing is disputed", async () => {
    mockedApi.listAssertions.mockResolvedValue({ items: [], total: 0 });
    render(<ContestedPage />);

    expect(await screen.findByText("No contested assertions")).toBeInTheDocument();
    expect(screen.getByText("Disputes land here for adjudication.")).toBeInTheDocument();
  });

  it("shows an error banner with a retry control when the list fails", async () => {
    mockedApi.listAssertions.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<ContestedPage />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByText("The 2021 lease amendment extends the term to 2030."),
    ).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2);
  });
});

// Rulings carry the revision on screen (ui:2) and mirror the API's rules for
// review text (ui:8); the drawer shows what the evidence says (ui:30).
describe("ContestedPage rulings and evidence", () => {
  it("rejects with the revision shown in the drawer", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Reject" }));

    await waitFor(() => expect(mockedApi.rejectAssertion).toHaveBeenCalledWith("a-1", 2, "disputed"));
  });

  it("explains a refusal because the drawer is stale (409) above the queue, and keeps it through the reload", async () => {
    mockedApi.acceptAssertion.mockRejectedValue(
      new ApiError(409, "assertion has been modified since expected_revision_number"),
    );
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));

    expect(await screen.findByText(/changed after you opened it/)).toBeInTheDocument();
    await waitFor(() => expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2));
    await screen.findByText("The 2021 lease amendment extends the term to 2030.");
    // The reload collapses the drawer; the notice lives above the queue.
    expect(screen.queryByRole("button", { name: "Collapse row" })).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/changed after you opened it/);
    expect(screen.getByRole("alert")).toHaveTextContent(/not recorded/);
    // In plain words, without the API's field name (acceptance run).
    expect(screen.getByRole("alert")).toHaveTextContent("Reason: it was edited.");
    expect(screen.getByRole("alert")).not.toHaveTextContent("expected_revision_number");

    // The next ruling starts without the old notice.
    mockedApi.rejectAssertion.mockReturnValue(new Promise(() => {}));
    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Reject" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows each evidence item's document and quoted text instead of its span id", async () => {
    mockedApi.listEvidence.mockResolvedValue([
      {
        ...evidenceItems[0],
        document_id: "doc-1",
        document_title: "Lease amendment (2021)",
        quote_text: "The term of the lease is extended to 31 December 2030.",
      },
      {
        ...evidenceItems[1],
        document_id: "doc-2",
        document_title: "Board minutes, 3 March 2021",
        quote_text: "The board did not approve any extension of the lease term.",
      },
    ]);
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);

    expect(
      await screen.findByText("The term of the lease is extended to 31 December 2030."),
    ).toBeInTheDocument();
    expect(screen.getByText("Lease amendment (2021)")).toBeInTheDocument();
    expect(
      screen.getByText("The board did not approve any extension of the lease term."),
    ).toBeInTheDocument();
    expect(screen.getByText("Board minutes, 3 March 2021")).toBeInTheDocument();
    expect(screen.queryByText("span-101")).not.toBeInTheDocument();
    expect(screen.queryByText("span-102")).not.toBeInTheDocument();
  });

  it("says when an evidence span cannot be resolved rather than showing a bare id", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);

    // The fixture spans carry no quote or document (unresolvable in this matter).
    expect(await screen.findAllByText(/could not be found in this matter/)).toHaveLength(2);
  });

  it("names evidence roles readably and marks every supporting role as supporting", async () => {
    mockedApi.listEvidence.mockResolvedValue([
      {
        ...evidenceItems[0],
        evidence_role: "primary_basis",
        document_title: "Lease amendment (2021)",
        quote_text: "The term of the lease is extended to 31 December 2030.",
      },
    ]);
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);

    expect(await screen.findByText("primary basis")).toHaveClass("badge--accepted");
  });

  it("keeps Confirm accept disabled for a justification over 100,000 characters", async () => {
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[1]);
    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));
    fireEvent.change(screen.getByLabelText("Acceptance justification"), {
      target: { value: "x".repeat(100_001) },
    });

    expect(screen.getByRole("button", { name: "Confirm accept" })).toBeDisabled();
    expect(screen.getByText(/100,000/)).toBeInTheDocument();
  });
});

// The paged list endpoint (lists package): each row's aggregate comes with
// the list item instead of one request per row, and the table lists 50
// disputed assertions at a time (XREQ-72/77).
describe("ContestedPage against the paged list", () => {
  function listed(index: number, overrides: Partial<AssertionListItem> = {}): AssertionListItem {
    return {
      ...makeAssertion({
        id: `d-${index}`,
        proposition: `Disputed proposition ${index}`,
        current_revision_number: 1,
      }),
      ratings_summary: null,
      current_user_rating: null,
      ...overrides,
    };
  }

  it("shows each row's embedded aggregate without a request per row", async () => {
    mockedApi.listAssertions.mockResolvedValue({
      items: [
        listed(1, {
          ratings_summary: {
            assertion_id: "d-1",
            assertion_revision_id: "rev-d-1",
            average: 3.5,
            median: 3.5,
            count: 4,
            distribution: { "2": 1, "3": 1, "4": 1, "5": 1 },
          },
        }),
        listed(2),
      ],
      total: 2,
    });
    render(<ContestedPage />);

    expect(await screen.findByText("avg 3.5 · 4 ratings")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    const tiles = within((await screen.findByText("Count")).closest(".ctd-tiles") as HTMLElement);
    expect(tiles.getByText("4")).toBeInTheDocument();
    expect(tiles.getAllByText("3.5")).toHaveLength(2); // average and median
    expect(mockedApi.ratingSummary).not.toHaveBeenCalled();
  });

  it("lists 50 disputed assertions at a time", async () => {
    const all = Array.from({ length: 70 }, (_, i) => listed(i));
    mockedApi.listAssertions.mockImplementation(async (_matterId, params = {}) => ({
      items: all.slice(params.offset ?? 0, (params.offset ?? 0) + (params.limit ?? all.length)),
      total: all.length,
    }));
    render(<ContestedPage />);

    await screen.findByText("Disputed proposition 0");
    expect(screen.getAllByRole("button", { name: "Expand row" })).toHaveLength(50);
    expect(screen.getByText("70")).toBeInTheDocument();
    expect(screen.getByText("Showing 50 of 70")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Show more" }));

    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Expand row" })).toHaveLength(70),
    );
    expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m-1", {
      status: "disputed",
      limit: 100,
      offset: 0,
    });
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
  });

  it("records one ruling when Reject is clicked twice before the first finishes", async () => {
    mockedApi.rejectAssertion.mockReturnValue(new Promise(() => {}));
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    const reject = await screen.findByRole("button", { name: "Reject" });
    reject.click();
    reject.click();

    expect(mockedApi.rejectAssertion).toHaveBeenCalledTimes(1);
  });
});

// Review fe-review-detail:2: removing evidence changes neither the revision
// nor updated_at, so a drawer that still shows the passage sends Accept
// without a justification and the API refuses it with 422.
describe("ContestedPage acceptance refused because the evidence was removed meanwhile", () => {
  it("reloads the row and its evidence, keeps the drawer open and asks for the justification", async () => {
    mockedApi.acceptAssertion.mockImplementation(async (_id, justification) => {
      if (!justification) {
        throw new ApiError(
          422,
          "unsupported assertion (no supporting evidence attached) cannot be accepted without a recorded acceptance_justification",
        );
      }
      return makeAssertion({ status: "accepted" });
    });
    await renderQueue();
    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    expect(await screen.findAllByText(/Source span unavailable/)).toHaveLength(2);
    // Both passages are removed: the next reads show it.
    mockedApi.listAssertions.mockResolvedValue({
      items: [{ ...evidencedAssertion, evidence_status: "awaiting_evidence" }, unsupportedAssertion],
      total: 2,
    });
    mockedApi.listEvidence.mockResolvedValue([]);

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1", undefined, 2, "disputed"),
    );
    const textarea = await screen.findByLabelText("Acceptance justification");
    await waitFor(() => expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2));
    expect(mockedApi.listEvidence).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("No evidence spans linked.")).toBeInTheDocument();
    expect(screen.queryByText(/Source span unavailable/)).not.toBeInTheDocument();
    expect(screen.getByText("Awaiting evidence")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Collapse row" })).toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/not recorded/);
    expect(alert).toHaveTextContent(/no longer has supporting evidence/);
    expect(alert).not.toHaveTextContent(/acceptance_justification/);

    fireEvent.change(textarea, { target: { value: "  Confirmed in the board minutes. " } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Confirm accept" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirm accept" }));

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenLastCalledWith(
        "a-1",
        "Confirmed in the board minutes.",
        2,
        "disputed",
      ),
    );
    expect(mockedApi.acceptAssertion).toHaveBeenCalledTimes(2);
  });
});

// Review fe-review-detail:5 (ui:4 on Contested): a system_generated row
// without evidence was derived by the definition-linking pipeline; it is not
// "awaiting evidence", as the assertion page and the Knowledge Base say.
describe("ContestedPage pipeline-generated assertions", () => {
  it("labels a pipeline row without evidence System-derived and says where it came from", async () => {
    mockedApi.listAssertions.mockResolvedValue({
      items: [
        makeAssertion({
          id: "s-1",
          origin: "system_generated",
          assertion_type: "USES_DEFINITION",
          proposition: 'Article 796 uses the definition of "Branch office".',
          evidence_status: "awaiting_evidence",
          author_user_id: "admin",
          confidence: 0.95,
          current_revision_number: 1,
        }),
        makeAssertion({ id: "a-5", evidence_status: "awaiting_evidence", proposition: "A colleague's reading." }),
      ],
      total: 2,
    });
    mockedApi.listEvidence.mockResolvedValue([]);
    render(<ContestedPage />);
    await screen.findByText('Article 796 uses the definition of "Branch office".');

    const pipelineRow = screen
      .getByText('Article 796 uses the definition of "Branch office".')
      .closest("tr") as HTMLElement;
    expect(within(pipelineRow).getByText("System-derived")).toBeInTheDocument();
    expect(within(pipelineRow).queryByText("Awaiting evidence")).not.toBeInTheDocument();
    const colleagueRow = screen.getByText("A colleague's reading.").closest("tr") as HTMLElement;
    expect(within(colleagueRow).getByText("Awaiting evidence")).toBeInTheDocument();

    fireEvent.click(within(pipelineRow).getByRole("button", { name: "Expand row" }));
    expect(
      await screen.findByText(/definition-linking pipeline generated this assertion automatically/),
    ).toBeInTheDocument();
    // Accepting it still needs a justification: it has no supporting evidence.
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(mockedApi.acceptAssertion).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Acceptance justification")).toBeInTheDocument();
  });
});
