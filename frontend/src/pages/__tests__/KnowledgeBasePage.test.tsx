// KnowledgeBasePage — accepted-assertion catalog + global search results.
// The api client and session are mocked; all data comes from fixtures.

import { render, screen, waitFor, within } from "@testing-library/react";
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

// Viewer role on purpose: this page is read-only for every role, so it must
// render fully (and show no review/rating actions) even for a viewer.
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

const a1: Assertion = {
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

const a2: Assertion = {
  ...a1,
  id: "a2",
  proposition: "Termination for convenience requires 60 days written notice.",
  origin: "model_suggested",
  author_user_id: "u4",
  confidence: 0.82,
  jurisdiction: null,
  current_revision_number: null,
  evidence_status: "awaiting_evidence",
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
  mockedApi.listAssertions.mockResolvedValue({ items: [a1, a2], total: 2 });
  mockedApi.ratingSummary.mockResolvedValue(summaryFixture);
});

describe("KnowledgeBasePage", () => {
  it("loads accepted assertions by default and renders the table", async () => {
    render(<KnowledgeBasePage />);

    expect(await screen.findByText(a1.proposition)).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m1", {
      status: "accepted",
      sort: "-created_at",
    });

    // Matter name in the subtitle; propositions link to the detail page.
    expect(screen.getByText(/Acme v\. Beta Holdings/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: a1.proposition })).toHaveAttribute(
      "href",
      "#/assertions/a1",
    );

    // Origin chips, evidence status, and model confidence stay separate
    // signals. Scoped to the table: the filter selects reuse these labels.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("Colleague")).toBeInTheDocument();
    expect(table.getByText("AI-deduced")).toBeInTheDocument();
    expect(table.getByText("Evidenced")).toBeInTheDocument();
    expect(table.getByText("Awaiting evidence")).toBeInTheDocument();
    expect(table.getByText(/82% model confidence/)).toBeInTheDocument();

    expect(screen.getByText("Showing 2 of 2 assertions")).toBeInTheDocument();

    // Read-only page: no review or rating actions for any role (viewer here).
    expect(
      screen.queryByRole("button", { name: /accept|reject|dispute|revision|rate/i }),
    ).not.toBeInTheDocument();
  });

  it("fetches a rating summary per row with a revision and renders it", async () => {
    render(<KnowledgeBasePage />);

    expect(await screen.findByText("avg 3.8 · 12 ratings")).toBeInTheDocument();
    // Only a1 has a current revision; a2 (no revision) must not be fetched.
    expect(mockedApi.ratingSummary).toHaveBeenCalledTimes(1);
    expect(mockedApi.ratingSummary).toHaveBeenCalledWith("a1", 3);

    const row2 = screen.getByText(a2.proposition).closest("tr");
    expect(row2).not.toBeNull();
    expect(within(row2 as HTMLElement).getByText("—")).toBeInTheDocument();

    // Legend keeps ratings distinct from review status and confidence.
    expect(
      screen.getByText(/independent of review status and model confidence/i),
    ).toBeInTheDocument();
  });

  it("refetches when status, origin, or sort change", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(a1.proposition);

    await user.selectOptions(screen.getByLabelText("Status"), "");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        sort: "-created_at",
      }),
    );

    await user.selectOptions(screen.getByLabelText("Origin"), "model_suggested");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        origin: "model_suggested",
        sort: "-created_at",
      }),
    );

    await user.selectOptions(screen.getByLabelText("Sort"), "proposition");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith("m1", {
        origin: "model_suggested",
        sort: "proposition",
      }),
    );
  });

  it("searches with a debounced q param", async () => {
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);
    await screen.findByText(a1.proposition);

    await user.type(screen.getByLabelText("Search assertions"), "notice");

    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
        "m1",
        expect.objectContaining({ q: "notice" }),
      ),
    );
  });

  it("reads ?q= from the hash and shows the results banner", async () => {
    window.location.hash = "#/knowledge?q=capacity";
    const view = render(<KnowledgeBasePage />);

    await screen.findByText(a1.proposition);
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m1", {
      q: "capacity",
      status: "accepted",
      sort: "-created_at",
    });
    expect(screen.getByText(/Results for/)).toBeInTheDocument();
    expect(screen.getByText("“capacity”")).toBeInTheDocument();
    expect(screen.getByLabelText("Search assertions")).toHaveValue("capacity");

    view.unmount();
    window.location.hash = "";
  });

  it("shows an empty state when nothing matches", async () => {
    mockedApi.listAssertions.mockResolvedValue({ items: [], total: 0 });
    render(<KnowledgeBasePage />);

    expect(await screen.findByText("No assertions found")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeDisabled();
  });

  it("shows an error banner and retries on demand", async () => {
    mockedApi.listAssertions
      .mockRejectedValueOnce(new Error("Matter unavailable"))
      .mockResolvedValueOnce({ items: [a1], total: 1 });
    const user = userEvent.setup();
    render(<KnowledgeBasePage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Matter unavailable");

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText(a1.proposition)).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(2);
  });

  it("exports the loaded rows as a client-side CSV", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn((_blob: Blob) => "blob:lexgraph");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    try {
      render(<KnowledgeBasePage />);
      await screen.findByText(a1.proposition);

      await user.click(screen.getByRole("button", { name: "Export CSV" }));

      expect(click).toHaveBeenCalledTimes(1);
      expect(createObjectURL).toHaveBeenCalledTimes(1);
      const blob = createObjectURL.mock.calls[0][0];
      // jsdom's Blob has no .text(); go through FileReader instead.
      const text = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(reader.error);
        reader.readAsText(blob);
      });
      expect(text).toContain(
        "Proposition,Type,Jurisdiction,Origin,Status,Standing,Evidence,Avg rating,Ratings,Updated",
      );
      expect(text).toContain(a1.proposition);
      expect(text).toContain("AI-deduced");
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:lexgraph");
    } finally {
      click.mockRestore();
    }
  });
});
