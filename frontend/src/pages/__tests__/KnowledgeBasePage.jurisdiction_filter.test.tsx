// RED tests for jurisdiction FILTERING on the Knowledge Base page (sprint
// 2026-08-02-us-state-law, director decision #4, gate G7: "review-queue
// filtering ... across every affected page").
//
// New file, not an edit to the existing `KnowledgeBasePage.test.tsx` (zero
// jurisdiction-filter coverage there today -- confirmed by the Planner
// reading that file in full). Badges are NOT re-tested here: the Planner
// verified directly (`KnowledgeBasePage.tsx:389-392`) that jurisdiction is
// ALREADY rendered inline per row (`· IL`) -- G7's "visible on the items
// themselves" criterion is already met on this page; the only real gap is
// the FILTER control, which does not exist (no `JURISDICTION_OPTIONS`
// constant is referenced anywhere on this page, per the recon dossier §3).

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Assertion, RatingSummary } from "../../api/types";
import { KnowledgeBasePage } from "../KnowledgeBasePage";

vi.mock("../../api/client", () => ({
  api: {
    listAssertions: vi.fn(),
    ratingSummary: vi.fn(),
  },
}));

const sessionFixture = {
  user: { id: "u1", email: "dana@example.com", display_name: "Dana Levi" },
  currentMatter: {
    id: "m1",
    name: "Acme v. Beta Holdings",
    repository_id: "r1",
    organization_id: "o1",
    role: "viewer" as const,
  },
  role: "viewer" as const,
  matters: [],
};

vi.mock("../../app/session", () => ({
  useActiveSession: () => sessionFixture,
}));

import { api } from "../../api/client";

const mockedApi = api as unknown as {
  listAssertions: ReturnType<typeof vi.fn>;
  ratingSummary: ReturnType<typeof vi.fn>;
};

const ilAssertion: Assertion = {
  id: "a1",
  organization_id: "o1",
  repository_id: "r1",
  matter_id: "m1",
  assertion_type: "obligation",
  proposition: "Clause 8.2 requires notice to the supplier within 30 days.",
  proposition_raw: null,
  subject_entity: { type: "clause", id: "c-8.2" },
  object_entity: null,
  origin: "user_suggested",
  status: "accepted",
  standing: "accepted",
  author_user_id: "u2",
  confidence: null,
  jurisdiction: "IL",
  effective_from: null,
  effective_to: null,
  created_at: "2026-07-01T10:00:00Z",
  updated_at: "2026-07-20T10:00:00Z",
  submitted_at: "2026-07-02T10:00:00Z",
  reviewed_by: "u3",
  reviewed_at: "2026-07-03T10:00:00Z",
  superseded_by_assertion_id: null,
  current_revision_number: 3,
  evidence_status: "evidenced",
};

const summaryFixture: RatingSummary = {
  count: 12,
  average: 3.8,
  median: 4,
  distribution: { "1": 1, "2": 1, "3": 2, "4": 5, "5": 3 },
  assertion_id: "a1",
  assertion_revision_id: "rev-3",
  current_user_rating: null,
  rationale_count: 2,
};

beforeEach(() => {
  mockedApi.listAssertions.mockReset();
  mockedApi.ratingSummary.mockReset();
  mockedApi.listAssertions.mockResolvedValue({ items: [ilAssertion], total: 1 });
  mockedApi.ratingSummary.mockResolvedValue(summaryFixture);
});

describe("KnowledgeBasePage jurisdiction filter", () => {
  it("renders a Jurisdiction filter select", async () => {
    render(<KnowledgeBasePage />);
    await screen.findByText(ilAssertion.proposition);
    expect(screen.getByLabelText("Jurisdiction")).toBeInTheDocument();
  });

  it("refetches with the jurisdiction param when the filter changes", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(ilAssertion.proposition);

    await user.selectOptions(screen.getByLabelText("Jurisdiction"), "US-DE");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        status: "accepted",
        jurisdiction: "US-DE",
        sort: "-created_at",
      }),
    );
  });
});
