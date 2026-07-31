// AssertionDetailPage — full record view: load/render, rating + review +
// comment interactions, role gating, and 404/error states. The api module
// and session hook are mocked; no network, no timers.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AssertionDetail,
  MatterRoleName,
  Rating,
  RatingSummary,
  RelatedMatch,
} from "../../api/types";

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
      putRating: vi.fn(),
      deleteRating: vi.fn(),
      addComment: vi.fn(),
      acceptAssertion: vi.fn(),
      rejectAssertion: vi.fn(),
      disputeAssertion: vi.fn(),
      requestRevision: vi.fn(),
    },
  };
});

let role: MatterRoleName = "reviewer";

vi.mock("../../app/session", () => ({
  useActiveSession: () => ({
    user: { id: "u-1", email: "ada@example.com", display_name: "Ada Lovelace" },
    currentMatter: {
      id: "m-1",
      name: "Acme acquisition",
      repository_id: "repo-1",
      organization_id: "org-1",
      role,
    },
    role,
    matters: [],
  }),
}));

import { ApiError, api } from "../../api/client";
import { AssertionDetailPage } from "../AssertionDetailPage";

const mockedApi = vi.mocked(api);

const detailFixture: AssertionDetail = {
  id: "a-1",
  organization_id: "org-1",
  repository_id: "repo-1",
  matter_id: "m-1",
  assertion_type: "obligation",
  proposition: "Acme Corp must deliver audited financial statements by 31 March each year.",
  proposition_raw: "acme MUST deliver audited financials by 31 march!!",
  subject_entity: { type: "party", id: "acme-corp" },
  object_entity: { type: "document", id: "audited-financials" },
  origin: "model_suggested",
  status: "proposed",
  standing: "probable",
  author_user_id: "u-2",
  confidence: 0.82,
  jurisdiction: "US-DE",
  effective_from: "2026-01-01",
  effective_to: null,
  created_at: "2026-07-01T10:00:00Z",
  updated_at: "2026-07-10T09:00:00Z",
  submitted_at: "2026-07-02T10:00:00Z",
  reviewed_by: null,
  reviewed_at: null,
  superseded_by_assertion_id: null,
  current_revision_number: 2,
  evidence_status: "evidenced",
  evidence: [
    {
      id: "ev-1",
      assertion_id: "a-1",
      source_span_id: "span-123",
      evidence_role: "supports",
      added_by_user_id: "u-2",
      created_at: "2026-07-01T10:05:00Z",
    },
  ],
  ratings_summary: {
    assertion_id: "a-1",
    assertion_revision_id: "rev-2",
    average: 3.5,
    median: 4,
    count: 2,
    distribution: { "3": 1, "4": 1 },
  },
  comments: [
    {
      id: "c-1",
      assertion_id: "a-1",
      user_id: "u-2",
      parent_comment_id: null,
      comment_text: "Please double-check the deadline.",
      comment_text_raw: null,
      created_at: "2026-07-03T08:00:00Z",
      updated_at: null,
      deleted_at: null,
    },
  ],
  revision_history: [
    {
      id: "rev-2",
      assertion_id: "a-1",
      revision_number: 2,
      proposition: "Acme Corp must deliver audited financial statements by 31 March each year.",
      proposition_raw: null,
      assertion_type: "obligation",
      subject_entity: { type: "party", id: "acme-corp" },
      object_entity: null,
      jurisdiction: "US-DE",
      effective_from: null,
      effective_to: null,
      revision_reason: "Corrected the delivery deadline",
      edited_by_user_id: "u-2",
      created_at: "2026-07-05T12:00:00Z",
    },
  ],
};

const summaryFixture: RatingSummary = {
  count: 2,
  average: 3.5,
  median: 4,
  distribution: { "3": 1, "4": 1 },
  assertion_id: "a-1",
  assertion_revision_id: "rev-2",
  current_user_rating: null,
  rationale_count: 1,
};

const relatedFixture: RelatedMatch[] = [
  { assertion_id: "a-2", match_kind: "similar", score: 0.87 },
];

async function renderPage() {
  render(<AssertionDetailPage assertionId="a-1" />);
  await screen.findByText(detailFixture.proposition);
}

beforeEach(() => {
  vi.clearAllMocks();
  role = "reviewer";
  mockedApi.getAssertion.mockResolvedValue(detailFixture);
  mockedApi.relatedAssertions.mockResolvedValue(relatedFixture);
  mockedApi.ratingSummary.mockResolvedValue(summaryFixture);
  mockedApi.putRating.mockResolvedValue({} as Rating);
  mockedApi.deleteRating.mockResolvedValue(undefined);
  mockedApi.addComment.mockResolvedValue({} as never);
  mockedApi.acceptAssertion.mockResolvedValue({} as never);
  mockedApi.rejectAssertion.mockResolvedValue({} as never);
  mockedApi.disputeAssertion.mockResolvedValue({} as never);
  mockedApi.requestRevision.mockResolvedValue({} as never);
});

describe("AssertionDetailPage", () => {
  it("loads and renders the full assertion record", async () => {
    await renderPage();

    expect(mockedApi.getAssertion).toHaveBeenCalledWith("a-1");
    expect(mockedApi.relatedAssertions).toHaveBeenCalledWith("a-1");
    expect(mockedApi.ratingSummary).toHaveBeenCalledWith("a-1", 2);

    // Header: status badge, origin chip, id.
    expect(screen.getByText("Proposed")).toBeInTheDocument();
    expect(screen.getAllByText("AI-deduced").length).toBeGreaterThan(0);
    expect(screen.getByText("a-1")).toBeInTheDocument();

    // Model provenance shows confidence as a percentage (never merged
    // with ratings — it sits in its own card).
    expect(screen.getByText("82%")).toBeInTheDocument();

    // Evidence span, comment, revision reason, related match.
    expect(screen.getByText("span-123")).toBeInTheDocument();
    expect(screen.getByText("Span text resolution is not yet available.")).toBeInTheDocument();
    expect(screen.getByText("Please double-check the deadline.")).toBeInTheDocument();
    expect(screen.getByText("Corrected the delivery deadline")).toBeInTheDocument();
    expect(screen.getByText("Similar proposition")).toBeInTheDocument();

    // Team rating summary from the per-revision endpoint.
    expect(screen.getByTestId("team-rating-indicator")).toHaveTextContent("3.5");
  });

  it("saves a strength rating against the current revision", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("radio", { name: "4 - Strong" }));
    fireEvent.click(screen.getByRole("button", { name: "Save rating" }));

    await waitFor(() =>
      expect(mockedApi.putRating).toHaveBeenCalledWith("a-1", 2, 4, ""),
    );
    // Summary is refreshed after the save (initial load + post-save).
    await waitFor(() => expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(2));
    await screen.findByText("Rating saved.");
  });

  it("runs reviewer actions through the api and re-fetches the record", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(mockedApi.acceptAssertion).toHaveBeenCalledWith("a-1", undefined),
    );
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it("posts a comment and refreshes the record", async () => {
    await renderPage();

    fireEvent.change(screen.getByLabelText("Add a comment"), {
      target: { value: "Looks right to me." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Post comment" }));

    await waitFor(() =>
      expect(mockedApi.addComment).toHaveBeenCalledWith("a-1", "Looks right to me."),
    );
    await waitFor(() => expect(mockedApi.getAssertion).toHaveBeenCalledTimes(2));
  });

  it("hides rating, review, and comment actions from viewers", async () => {
    role = "viewer";
    await renderPage();

    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Add a comment")).not.toBeInTheDocument();
  });

  it("lets contributors rate and comment but not review", async () => {
    role = "contributor";
    await renderPage();

    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    expect(screen.getByLabelText("Add a comment")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Dispute" })).not.toBeInTheDocument();
  });

  it("shows an empty state when the assertion does not exist", async () => {
    mockedApi.getAssertion.mockRejectedValue(new ApiError(404, "Assertion not found"));
    render(<AssertionDetailPage assertionId="missing" />);

    expect(await screen.findByText("Assertion not found")).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });

  it("surfaces a load error with a retry action", async () => {
    mockedApi.getAssertion.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<AssertionDetailPage assertionId="a-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("backend unreachable");

    mockedApi.getAssertion.mockResolvedValue(detailFixture);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByText(detailFixture.proposition);
  });
});
