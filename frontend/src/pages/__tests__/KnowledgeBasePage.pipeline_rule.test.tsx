// The Knowledge Base's Evidence cell follows the shared pipeline rule
// (constants/pipeline.ts: isSystemDerived and SYSTEM_DERIVED_LABEL), which the
// Review Queue, Contested and the assertion page use too, so the four surfaces
// cannot drift apart. The page kept its own copy of the predicate and the
// label: a change to the shared rule would have left the Knowledge Base
// behind. Here the shared rule is replaced by a different one, and the page
// must follow it, whatever origin and evidence status a row has.

import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssertionList, AssertionListItem } from "../../api/types";
import { KnowledgeBasePage } from "../KnowledgeBasePage";

vi.mock("../../constants/pipeline", () => ({
  SYSTEM_DERIVED_LABEL: "Derived (stand-in rule)",
  isSystemDerived: (assertion: { id?: string }) => assertion.id === "derived-by-the-rule",
  SYSTEM_DERIVED_NO_EVIDENCE: "",
}));

vi.mock("../../api/client", () => ({
  api: { listAssertions: vi.fn(), ratingSummary: vi.fn() },
}));

vi.mock("../../app/session", () => ({
  useActiveSession: () => ({
    user: { id: "u1", email: "dana@example.com", display_name: "Dana Levi" },
    currentMatter: { id: "m1", name: "Acme", repository_id: "r1", organization_id: "o1", role: "viewer" },
    role: "viewer",
    matters: [],
  }),
}));

import { api } from "../../api/client";

const listAssertions = api.listAssertions as unknown as ReturnType<typeof vi.fn>;

function row(id: string, proposition: string, overrides: Partial<AssertionListItem>): AssertionListItem {
  return {
    id,
    organization_id: "o1",
    repository_id: "r1",
    matter_id: "m1",
    assertion_type: "INTERPRETS",
    proposition,
    proposition_raw: null,
    subject_entity: { type: "Document", id: "d1" },
    object_entity: null,
    origin: "user_suggested",
    status: "accepted",
    standing: "accepted",
    author_user_id: "u2",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    submitted_at: "2026-07-02T10:00:00Z",
    reviewed_by: "u3",
    reviewed_at: "2026-07-03T10:00:00Z",
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    ratings_summary: null,
    current_user_rating: null,
    last_activity_at: "2026-07-21T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  window.location.hash = "";
  listAssertions.mockReset();
});

describe("KnowledgeBasePage Evidence cell", () => {
  it("asks the shared pipeline rule, as the Review Queue, Contested and the assertion page do", async () => {
    // The stand-in rule picks an evidenced colleague's row and passes over a
    // pipeline row without evidence, which the real rule labels the other way.
    const chosen = row("derived-by-the-rule", "Chosen by the rule.", {});
    const passedOver = row("pipeline-row", "Passed over by the rule.", {
      origin: "system_generated",
      evidence_status: "awaiting_evidence",
    });
    const page: AssertionList = { items: [chosen, passedOver], total: 2, limit: 50, offset: 0 };
    listAssertions.mockResolvedValue(page);

    render(<KnowledgeBasePage />);

    const chosenRow = (await screen.findByText(chosen.proposition)).closest("tr") as HTMLElement;
    expect(within(chosenRow).getByText("Derived (stand-in rule)")).toBeInTheDocument();
    expect(within(chosenRow).queryByText("Evidenced")).not.toBeInTheDocument();
    const passedOverRow = screen.getByText(passedOver.proposition).closest("tr") as HTMLElement;
    expect(within(passedOverRow).getByText("Awaiting evidence")).toBeInTheDocument();
    expect(within(passedOverRow).queryByText("System-derived")).not.toBeInTheDocument();
  });
});
