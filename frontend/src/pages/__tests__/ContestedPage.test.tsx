// ContestedPage — disputed-assertion adjudication queue.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Assertion, Evidence, MatterRoleName, RatingSummary } from "../../api/types";

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

import { api } from "../../api/client";
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

    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", { status: "disputed" });
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
    expect(await screen.findByText("span-101")).toBeInTheDocument();
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

    await waitFor(() => expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1"));
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
      ),
    );
  });

  it("hides adjudication actions from contributors and shows the role note", async () => {
    mocks.role = "contributor";
    await renderQueue();

    fireEvent.click(screen.getAllByRole("button", { name: "Expand row" })[0]);
    await screen.findByText("span-101");

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
