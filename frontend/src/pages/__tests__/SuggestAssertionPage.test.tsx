// SuggestAssertionPage — page-level tests: initial render, submission
// mapping onto api.createAssertion, similar-assertion surfacing, error
// handling, and role gating. api + session are mocked; no network.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../../api/client";
import type { Assertion } from "../../api/types";
import { SuggestAssertionPage } from "../SuggestAssertionPage";

const sessionState = vi.hoisted(() => ({
  role: "contributor" as "viewer" | "contributor" | "reviewer" | "admin",
}));

vi.mock("../../app/session", () => ({
  useActiveSession: () => ({
    user: { id: "user-1", email: "dana@example.com", display_name: "Dana Levi" },
    matters: [],
    currentMatter: {
      id: "matter-1",
      name: "Acme lease dispute",
      repository_id: "repo-1",
      organization_id: "org-1",
      role: sessionState.role,
    },
    role: sessionState.role,
  }),
}));

vi.mock("../../api/client", () => {
  class MockApiError extends Error {
    status: number;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
    }
  }
  return {
    api: { createAssertion: vi.fn() },
    ApiError: MockApiError,
  };
});

type CreateAssertionResult = Assertion & {
  similar_assertions?: { id: string; proposition: string }[];
};

function makeAssertion(overrides: Partial<CreateAssertionResult> = {}): CreateAssertionResult {
  return {
    id: "a-new",
    organization_id: "org-1",
    repository_id: "repo-1",
    matter_id: "matter-1",
    assertion_type: "APPLIES_TO",
    proposition: "Section 12 applies to subtenants.",
    proposition_raw: null,
    subject_entity: { type: "Entity", id: "ent-9" },
    object_entity: null,
    origin: "user_suggested",
    status: "draft",
    standing: "draft",
    author_user_id: "user-1",
    confidence: null,
    jurisdiction: null,
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-31T10:00:00Z",
    updated_at: "2026-07-31T10:00:00Z",
    submitted_at: null,
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "awaiting_evidence",
    ...overrides,
  };
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Subject entity ID"), "ent-9");
  await user.type(screen.getByLabelText("Assertion type"), "APPLIES_TO");
  await user.type(screen.getByLabelText("Proposition"), "Section 12 applies to subtenants.");
}

beforeEach(() => {
  sessionState.role = "contributor";
  window.location.hash = "#/suggest";
  vi.mocked(api.createAssertion).mockReset();
  vi.mocked(api.createAssertion).mockResolvedValue(makeAssertion());
});

describe("SuggestAssertionPage", () => {
  it("renders the suggestion form and guidance rail for a contributor", () => {
    render(<SuggestAssertionPage />);

    expect(
      screen.getByRole("heading", { name: "Suggest Assertion" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Acme lease dispute/)).toBeInTheDocument();
    expect(screen.getByLabelText("Proposition")).toBeInTheDocument();
    expect(screen.getByText("How suggestions work")).toBeInTheDocument();
    expect(screen.getByText("Writing a strong assertion")).toBeInTheDocument();
    // Matter context flows into the form's prefill.
    expect(screen.getByText("repo-1")).toBeInTheDocument();
    expect(screen.getByText("matter-1")).toBeInTheDocument();
  });

  it("maps a draft submission onto api.createAssertion and navigates to the new assertion", async () => {
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    await waitFor(() => expect(api.createAssertion).toHaveBeenCalledTimes(1));
    expect(api.createAssertion).toHaveBeenCalledWith({
      repository_id: "repo-1",
      matter_id: "matter-1",
      assertion_type: "APPLIES_TO",
      proposition: "Section 12 applies to subtenants.",
      subject_entity: { type: "Entity", id: "ent-9" },
      object_entity: null,
      jurisdiction: null,
      effective_from: null,
      effective_to: null,
      evidence: [],
      explanation: null,
      save_as: "draft",
    });
    await waitFor(() => expect(window.location.hash).toBe("#/assertions/a-new"));
  });

  it("submits for review with an object entity mapped as a second entity ref", async () => {
    vi.mocked(api.createAssertion).mockResolvedValue(makeAssertion({ id: "a-77" }));
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.type(screen.getByLabelText("Object entity ID"), "ent-3");
    await user.click(screen.getByRole("button", { name: /submit for review/i }));

    await waitFor(() => expect(api.createAssertion).toHaveBeenCalledTimes(1));
    expect(api.createAssertion).toHaveBeenCalledWith(
      expect.objectContaining({
        save_as: "proposed",
        subject_entity: { type: "Entity", id: "ent-9" },
        object_entity: { type: "Entity", id: "ent-3" },
      }),
    );
    await waitFor(() => expect(window.location.hash).toBe("#/assertions/a-77"));
  });

  it("stays on the page and surfaces similar assertions returned by the backend", async () => {
    vi.mocked(api.createAssertion).mockResolvedValue(
      makeAssertion({
        id: "a-2",
        similar_assertions: [{ id: "a-1", proposition: "Existing similar claim" }],
      }),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    expect(
      await screen.findByText("Similar assertions already exist"),
    ).toBeInTheDocument();
    // No auto-navigation away from the page.
    expect(window.location.hash).toBe("#/suggest");
    // The matches feed the form's own similarity warning.
    expect(screen.getByRole("alert")).toHaveTextContent("Existing similar claim");
    expect(screen.getByRole("link", { name: "View" })).toHaveAttribute(
      "href",
      "#/assertions/a-1",
    );

    await user.click(screen.getByRole("button", { name: /continue to your assertion/i }));
    expect(window.location.hash).toBe("#/assertions/a-2");
  });

  it("blocks submission without a subject entity and never calls the API", async () => {
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await user.type(screen.getByLabelText("Assertion type"), "APPLIES_TO");
    await user.type(screen.getByLabelText("Proposition"), "Section 12 applies.");
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/subject entity/i);
    expect(api.createAssertion).not.toHaveBeenCalled();
  });

  it("shows the backend validation message when the create is rejected", async () => {
    vi.mocked(api.createAssertion).mockRejectedValue(
      new ApiError(
        409,
        "duplicate: an identical proposition already exists in this matter (assertion a-1)",
      ),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /duplicate: an identical proposition already exists/,
    );
    expect(window.location.hash).toBe("#/suggest");
  });

  it("hides the form from viewers and asks for the contributor role", () => {
    sessionState.role = "viewer";
    render(<SuggestAssertionPage />);

    expect(screen.getByText("Contributor role required")).toBeInTheDocument();
    expect(screen.queryByLabelText("Proposition")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save as draft/i })).not.toBeInTheDocument();
  });

  it("prefills the subject entity from a deep-link query parameter", () => {
    window.location.hash = "#/suggest?subject=ent-42";
    render(<SuggestAssertionPage />);

    expect(screen.getByLabelText("Subject entity ID")).toHaveValue("ent-42");
  });
});
