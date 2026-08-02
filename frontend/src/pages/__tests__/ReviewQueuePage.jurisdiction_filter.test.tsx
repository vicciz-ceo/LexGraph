// RED tests for jurisdiction FILTERING on the Review Queue page (sprint
// 2026-08-02-us-state-law, director decision #4, gate G7: "review-queue
// filtering ... across every affected page").
//
// New file, additive only. Badges are NOT re-tested here: the Planner
// verified directly (`ReviewQueuePage.tsx:312-313`, per the recon dossier
// §3) that jurisdiction is ALREADY rendered as a chip per item -- the real
// gap is the FILTER control, which does not exist today.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Assertion, AssertionListParams } from "../../api/types";
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

vi.mock("../../api/client", () => ({
  api: {
    listAssertions: vi.fn(),
    listMatterMembers: vi.fn(),
    ratingSummary: vi.fn(),
    acceptAssertion: vi.fn(),
    rejectAssertion: vi.fn(),
    disputeAssertion: vi.fn(),
    requestRevision: vi.fn(),
  },
}));

import { api } from "../../api/client";

function makeAssertion(overrides: Partial<Assertion> = {}): Assertion {
  return {
    id: "a0",
    organization_id: "o1",
    repository_id: "r1",
    matter_id: "m1",
    assertion_type: "interpretation",
    proposition: "A proposition pending review.",
    proposition_raw: null,
    subject_entity: { type: "statute", id: "s1" },
    object_entity: null,
    origin: "user_suggested",
    status: "proposed",
    standing: "proposed",
    author_user_id: "u2",
    confidence: null,
    jurisdiction: "IL",
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

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listMatterMembers).mockResolvedValue([]);
  vi.mocked(api.listAssertions).mockImplementation(
    async (_matterId: string, _params: AssertionListParams = {}) => ({
      items: [makeAssertion()],
      total: 1,
    }),
  );
  vi.mocked(api.ratingSummary).mockResolvedValue({
    count: 0,
    average: null,
    median: null,
    distribution: {},
    assertion_id: "a0",
    assertion_revision_id: "rev-1",
    current_user_rating: null,
    rationale_count: 0,
  });
});

describe("ReviewQueuePage jurisdiction filter", () => {
  it("renders a Jurisdiction filter select", async () => {
    render(<ReviewQueuePage />);
    await screen.findByText("A proposition pending review.");
    expect(screen.getByLabelText("Jurisdiction")).toBeInTheDocument();
  });

  it("passes the selected jurisdiction through to every listAssertions call", async () => {
    const user = userEvent.setup();
    render(<ReviewQueuePage />);
    await screen.findByText("A proposition pending review.");

    vi.mocked(api.listAssertions).mockClear();
    await user.selectOptions(screen.getByLabelText("Jurisdiction"), "US-DE");

    await waitFor(() => expect(api.listAssertions).toHaveBeenCalled());
    for (const call of vi.mocked(api.listAssertions).mock.calls) {
      const params = call[1] as AssertionListParams;
      expect(params.jurisdiction).toBe("US-DE");
    }
  });
});
