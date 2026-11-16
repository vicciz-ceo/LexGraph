// SuggestAssertionPage — page-level tests: initial render, submission
// mapping onto api.createAssertion, similar-assertion surfacing, error
// handling, and role gating. api + session are mocked; no network.

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "../../api/client";
import type { Assertion, AssertionDetail, RelatedMatch } from "../../api/types";
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
    body: unknown;
    constructor(status: number, detail: string, body: unknown = null) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
      this.body = body;
    }
  }
  return {
    api: { createAssertion: vi.fn(), sources: vi.fn(), getAssertion: vi.fn() },
    ApiError: MockApiError,
  };
});

// The real wire shape of POST /assertions (backend/app/routers/assertions.py).
type CreateAssertionResult = Assertion & {
  similar_assertions?: RelatedMatch[];
  similar_assertions_total?: number;
  similar_assertions_truncated?: boolean;
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
    subject_entity: { type: "Document", id: "ent-9" },
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

function match(id: string, overrides: Partial<RelatedMatch> = {}): RelatedMatch {
  return {
    assertion_id: id,
    match_kind: "same_subject_type_object",
    score: 0.95,
    proposition: `Existing claim ${id}`,
    status: "proposed",
    assertion_type: "APPLIES_TO",
    ...overrides,
  };
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await screen.findAllByRole("option", { name: "Lease" });
  await user.selectOptions(screen.getByLabelText("Subject source"), "ent-9");
  await user.selectOptions(screen.getByLabelText("Assertion type"), "APPLIES_TO");
  await user.type(screen.getByLabelText("Proposition"), "Section 12 applies to subtenants.");
}

async function saveDraft(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /save as draft/i }));
  await waitFor(() => expect(api.createAssertion).toHaveBeenCalledTimes(1));
  return vi.mocked(api.createAssertion).mock.calls[0][0] as Record<string, unknown>;
}

beforeEach(() => {
  sessionState.role = "contributor";
  window.location.hash = "#/suggest";
  window.localStorage.clear();
  vi.mocked(api.sources).mockReset();
  vi.mocked(api.sources).mockResolvedValue({ items: [
    { id: "ent-9", type: "Document", label: "Lease" },
    { id: "ent-3", type: "Article", label: "Section 12" },
  ], total: 2 });
  vi.mocked(api.getAssertion).mockReset();
  vi.mocked(api.getAssertion).mockRejectedValue(new ApiError(404, "assertion not found"));
  vi.mocked(api.createAssertion).mockReset();
  vi.mocked(api.createAssertion).mockResolvedValue(makeAssertion());
});

describe("SuggestAssertionPage", () => {
  it("renders the suggestion form and guidance rail for a contributor", async () => {
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
    await screen.findAllByRole("option", { name: "Lease" });
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
      subject_entity: { type: "Document", id: "ent-9" },
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
    await user.selectOptions(screen.getByLabelText("Object source (optional)"), "ent-3");
    await user.click(screen.getByRole("button", { name: /submit for review/i }));

    await waitFor(() => expect(api.createAssertion).toHaveBeenCalledTimes(1));
    expect(api.createAssertion).toHaveBeenCalledWith(
      expect.objectContaining({
        save_as: "proposed",
        subject_entity: { type: "Document", id: "ent-9" },
        object_entity: { type: "Article", id: "ent-3" },
      }),
    );
    await waitFor(() => expect(window.location.hash).toBe("#/assertions/a-77"));
  });

  it("stays on the page and surfaces similar assertions by their text, linked, never by id", async () => {
    vi.mocked(api.createAssertion).mockResolvedValue(
      makeAssertion({
        id: "a-2",
        similar_assertions: [
          match("a-1", { proposition: "Existing similar claim", status: "accepted", score: 0.91 }),
        ],
        similar_assertions_total: 1,
        similar_assertions_truncated: false,
      }),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    const notice = (await screen.findByText("Similar assertions already exist")).closest("section")!;
    // No auto-navigation away from the page.
    expect(window.location.hash).toBe("#/suggest");
    expect(within(notice).getByText("Existing similar claim")).toBeInTheDocument();
    expect(within(notice).getByText("Accepted")).toBeInTheDocument();
    expect(notice).not.toHaveTextContent("a-1");
    expect(screen.getByRole("link", { name: "View" })).toHaveAttribute("href", "#/assertions/a-1");
    // The matches feed the form's own similarity warning, quoted and linked.
    const warning = screen.getByRole("alert");
    expect(warning).toHaveTextContent("“Existing similar claim”");
    expect(warning).not.toHaveTextContent('""');
    expect(within(warning).getByRole("link", { name: /Existing similar claim/ })).toHaveAttribute(
      "href",
      "#/assertions/a-1",
    );
    expect(api.getAssertion).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /continue to your assertion/i }));
    expect(window.location.hash).toBe("#/assertions/a-2");
  });

  it("loads the text of matches an older backend sends without it, and never shows ids or empty quotes", async () => {
    vi.mocked(api.createAssertion).mockResolvedValue(
      makeAssertion({
        id: "a-2",
        similar_assertions: [
          { assertion_id: "a-1", match_kind: "same_subject_type_object", score: 0.95 },
          { assertion_id: "a-5", match_kind: "similar", score: 0.91 },
        ],
      }),
    );
    vi.mocked(api.getAssertion).mockImplementation(async (id: string) => {
      if (id === "a-1") {
        return { id: "a-1", proposition: "Clause 9 limits liability.", status: "proposed" } as AssertionDetail;
      }
      throw new ApiError(404, "assertion not found");
    });
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    const notice = (await screen.findByText("Similar assertions already exist")).closest("section")!;
    expect(within(notice).getByText("Clause 9 limits liability.")).toBeInTheDocument();
    expect(within(notice).getByText(/its text could not be loaded/)).toBeInTheDocument();
    expect(notice).not.toHaveTextContent("a-1");
    expect(notice).not.toHaveTextContent("a-5");
    const links = within(notice).getAllByRole("link", { name: "View" });
    expect(links.map((link) => link.getAttribute("href"))).toEqual(["#/assertions/a-1", "#/assertions/a-5"]);
    const warning = screen.getByRole("alert");
    expect(warning).toHaveTextContent("“Clause 9 limits liability.”");
    expect(warning).toHaveTextContent("and 1 more");
    expect(warning).not.toHaveTextContent('""');
  });

  it("lists at most 20 matches by score and says how many more exist", async () => {
    const many = Array.from({ length: 23 }, (_, index) =>
      match(`a-${String(index).padStart(2, "0")}`, { score: index / 100 }),
    );
    vi.mocked(api.createAssertion).mockResolvedValue(
      makeAssertion({ id: "a-new", similar_assertions: many, similar_assertions_total: 30 }),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    const notice = (await screen.findByText("Similar assertions already exist")).closest("section")!;
    const items = within(notice).getAllByRole("listitem");
    expect(items).toHaveLength(20);
    // Highest score first: a-22 (0.22) ... a-03 (0.03).
    expect(items[0]).toHaveTextContent("Existing claim a-22");
    expect(items[19]).toHaveTextContent("Existing claim a-03");
    expect(notice).toHaveTextContent("and 10 more similar assertions not listed here.");
    expect(screen.getByRole("alert")).toHaveTextContent("and 10 more");
  });

  it("caps an uncapped list from an older backend and counts the rest", async () => {
    const many = Array.from({ length: 23 }, (_, index) => match(`b-${index}`, { score: 0.9 }));
    vi.mocked(api.createAssertion).mockResolvedValue(
      makeAssertion({ similar_assertions: many }),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    const notice = (await screen.findByText("Similar assertions already exist")).closest("section")!;
    expect(within(notice).getAllByRole("listitem")).toHaveLength(20);
    expect(notice).toHaveTextContent("and 3 more similar assertions not listed here.");
  });

  it("starts a fresh suggestion from the similar-assertions notice", async () => {
    vi.mocked(api.createAssertion).mockResolvedValue(
      makeAssertion({ id: "a-2", similar_assertions: [match("a-1")] }),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));
    await screen.findByText("Similar assertions already exist");
    expect(screen.getByRole("button", { name: /save as draft/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /suggest another assertion/i }));

    expect(screen.queryByText("Similar assertions already exist")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Proposition")).toHaveValue("");
    expect(screen.getByRole("button", { name: /save as draft/i })).toBeDisabled(); // empty proposition
    await user.type(screen.getByLabelText("Proposition"), "Another claim.");
    expect(screen.getByRole("button", { name: /save as draft/i })).toBeEnabled();
  });

  it("explains an exact duplicate and links to the existing assertion", async () => {
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

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent(/already exists in this matter, so nothing was saved/);
    expect(banner).not.toHaveTextContent("duplicate:");
    expect(within(banner).getByRole("link", { name: "Open the existing assertion" })).toHaveAttribute(
      "href",
      "#/assertions/a-1",
    );
    expect(window.location.hash).toBe("#/suggest");
  });

  it("prefers a structured existing_assertion_id in the duplicate response", async () => {
    vi.mocked(api.createAssertion).mockRejectedValue(
      new ApiError(409, "duplicate: an identical proposition already exists in this matter", {
        detail: "duplicate: an identical proposition already exists in this matter",
        existing_assertion_id: "a-7",
      }),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    const link = await screen.findByRole("link", { name: "Open the existing assertion" });
    expect(link).toHaveAttribute("href", "#/assertions/a-7");
  });

  it("shows the backend validation message when the create is rejected", async () => {
    vi.mocked(api.createAssertion).mockRejectedValue(
      new ApiError(422, "Entity must exist in the selected matter"),
    );
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Entity must exist in the selected matter",
    );
    expect(window.location.hash).toBe("#/suggest");
  });

  it("blocks submission without a subject entity and never calls the API", async () => {
    const user = userEvent.setup();
    render(<SuggestAssertionPage />);

    await user.selectOptions(screen.getByLabelText("Assertion type"), "APPLIES_TO");
    await user.type(screen.getByLabelText("Proposition"), "Section 12 applies.");
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/subject/i);
    expect(api.createAssertion).not.toHaveBeenCalled();
  });

  it("hides the form from viewers and asks for the contributor role", () => {
    sessionState.role = "viewer";
    render(<SuggestAssertionPage />);

    expect(screen.getByText("Contributor role required")).toBeInTheDocument();
    expect(screen.queryByLabelText("Proposition")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save as draft/i })).not.toBeInTheDocument();
  });

  describe("assertion type", () => {
    it("is a select of the 12 recognized types plus a propose-new option", async () => {
      render(<SuggestAssertionPage />);
      await screen.findAllByRole("option", { name: "Lease" });
      const field = screen.getByLabelText("Assertion type") as HTMLSelectElement;
      expect(field.tagName).toBe("SELECT");
      const values = Array.from(field.options).map((option) => option.value);
      expect(values).toHaveLength(14);
      expect(values).toContain("INTERPRETS");
      expect(values).toContain("DERIVES_FROM_LAW");
      expect(screen.getByRole("option", { name: "Propose a new type…" })).toBeInTheDocument();
      expect(screen.queryByLabelText("New type name")).not.toBeInTheDocument();
    });

    it("sends a proposed new type, normalized, with the API's proposed-new flag", async () => {
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await screen.findAllByRole("option", { name: "Lease" });
      await user.selectOptions(screen.getByLabelText("Subject source"), "ent-9");
      await user.selectOptions(screen.getByLabelText("Assertion type"), "Propose a new type…");
      await user.type(screen.getByLabelText("New type name"), "cancelled by");
      expect(screen.getByText(/Will be saved as CANCELLED_BY, marked as a proposed new type/)).toBeInTheDocument();
      await user.type(screen.getByLabelText("Proposition"), "Clause 9 is cancelled by the 2024 amendment.");
      const body = await saveDraft(user);

      expect(body.assertion_type).toBe("CANCELLED_BY");
      expect(body.assertion_type_is_proposed_new).toBe(true);
    });

    it("sends a recognized name typed as a new type as that type, without the flag", async () => {
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await screen.findAllByRole("option", { name: "Lease" });
      await user.selectOptions(screen.getByLabelText("Subject source"), "ent-9");
      await user.selectOptions(screen.getByLabelText("Assertion type"), "Propose a new type…");
      await user.type(screen.getByLabelText("New type name"), "interprets");
      await user.type(screen.getByLabelText("Proposition"), "Clause 9 interprets clause 4.");
      const body = await saveDraft(user);

      expect(body.assertion_type).toBe("INTERPRETS");
      expect(body).not.toHaveProperty("assertion_type_is_proposed_new");
    });

    it("asks for a type when none is chosen or the new name is empty", async () => {
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await screen.findAllByRole("option", { name: "Lease" });
      await user.selectOptions(screen.getByLabelText("Subject source"), "ent-9");
      await user.type(screen.getByLabelText("Proposition"), "Clause 9 is cancelled.");
      await user.click(screen.getByRole("button", { name: /save as draft/i }));
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Select an assertion type, or name the new type you are proposing.",
      );

      await user.selectOptions(screen.getByLabelText("Assertion type"), "Propose a new type…");
      await user.type(screen.getByLabelText("New type name"), " - ");
      await user.click(screen.getByRole("button", { name: /save as draft/i }));
      expect(await screen.findByRole("alert")).toHaveTextContent(/Select an assertion type/);
      expect(api.createAssertion).not.toHaveBeenCalled();
    });
  });

  describe("further evidence needed", () => {
    it("records the flag as a note after the explanation", async () => {
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await fillRequiredFields(user);
      await user.type(screen.getByLabelText("Explanation or rationale"), "Clause 12 says so.");
      await user.click(screen.getByLabelText("Further evidence needed"));
      const body = await saveDraft(user);

      expect(body.explanation).toBe(
        "Clause 12 says so.\n\nFurther evidence needed: the author marked this assertion as needing more supporting evidence.",
      );
    });

    it("records the flag on its own when no explanation is written", async () => {
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await fillRequiredFields(user);
      await user.click(screen.getByLabelText("Further evidence needed"));
      const body = await saveDraft(user);

      expect(body.explanation).toBe(
        "Further evidence needed: the author marked this assertion as needing more supporting evidence.",
      );
    });
  });

  describe("profile default jurisdiction", () => {
    it("pre-selects the jurisdiction saved on the Profile page and submits it", async () => {
      window.localStorage.setItem("lexgraph:default-jurisdiction:user-1", "US-CA");
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      expect(screen.getByLabelText("Jurisdiction")).toHaveValue("US-CA");
      expect(screen.getByText(/Pre-selected from the default in your profile/)).toBeInTheDocument();
      await fillRequiredFields(user);
      const body = await saveDraft(user);
      expect(body.jurisdiction).toBe("US-CA");
    });

    it("sends no jurisdiction when the pre-selected one is cleared", async () => {
      window.localStorage.setItem("lexgraph:default-jurisdiction:user-1", "US-CA");
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await fillRequiredFields(user);
      await user.selectOptions(screen.getByLabelText("Jurisdiction"), "");
      const body = await saveDraft(user);
      expect(body.jurisdiction).toBeNull();
    });

    it("ignores a stored value outside the vocabulary and another user's default", async () => {
      window.localStorage.setItem("lexgraph:default-jurisdiction:user-1", "EU");
      window.localStorage.setItem("lexgraph:default-jurisdiction:user-2", "US-NY");
      render(<SuggestAssertionPage />);
      await screen.findAllByRole("option", { name: "Lease" });

      expect(screen.getByLabelText("Jurisdiction")).toHaveValue("");
      expect(screen.queryByText(/Pre-selected from the default in your profile/)).not.toBeInTheDocument();
    });
  });

  describe("deep links", () => {
    it("resolves a linked subject to its real type and submits that type", async () => {
      window.location.hash = "#/suggest?subject=ent-3";
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await waitFor(() => expect(screen.getByLabelText("Subject source")).toHaveValue("ent-3"));
      await user.selectOptions(screen.getByLabelText("Assertion type"), "APPLIES_TO");
      await user.type(screen.getByLabelText("Proposition"), "Section 12 applies to subtenants.");
      const body = await saveDraft(user);

      expect(body.subject_entity).toEqual({ type: "Article", id: "ent-3" });
    });

    it("finds a linked subject beyond the first page of sources", async () => {
      window.location.hash = "#/suggest?subject=ent-77";
      vi.mocked(api.sources).mockImplementation(async (_matter, _kind, _q = "", offset = 0) =>
        offset === 0
          ? { items: Array.from({ length: 50 }, (_, i) => ({ id: `ent-p${i}`, type: "Document", label: `Doc ${i}` })), total: 51 }
          : { items: [{ id: "ent-77", type: "Article", label: "Schedule 2 / 4 Notices" }], total: 51 },
      );
      render(<SuggestAssertionPage />);

      await waitFor(() => expect(screen.getByLabelText("Subject source")).toHaveValue("ent-77"));
      expect(screen.getByRole("option", { name: "Schedule 2 / 4 Notices" })).toBeInTheDocument();
    });

    it("uses the type a link states for entities the picker does not list", async () => {
      window.location.hash = "#/suggest?subject=def-1&subject_type=Definition";
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await waitFor(() => expect(screen.getByLabelText("Subject source")).toHaveValue("def-1"));
      expect(screen.getByRole("option", { name: "Definition from the link you followed" })).toBeInTheDocument();
      await user.selectOptions(screen.getByLabelText("Assertion type"), "USES_DEFINITION");
      await user.type(screen.getByLabelText("Proposition"), "Section 3 uses the defined term.");
      const body = await saveDraft(user);

      expect(body.subject_entity).toEqual({ type: "Definition", id: "def-1" });
    });

    it("resolves a linked assertion of this matter", async () => {
      window.location.hash = "#/suggest?subject=a-9";
      vi.mocked(api.getAssertion).mockResolvedValue({
        id: "a-9", matter_id: "matter-1", proposition: "Clause 4 binds the tenant.", status: "accepted",
      } as AssertionDetail);
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      await waitFor(() => expect(screen.getByLabelText("Subject source")).toHaveValue("a-9"));
      await user.selectOptions(screen.getByLabelText("Assertion type"), "WEAKENS");
      await user.type(screen.getByLabelText("Proposition"), "Clause 9 weakens that reading.");
      const body = await saveDraft(user);

      expect(body.subject_entity).toEqual({ type: "Assertion", id: "a-9" });
    });

    it("does not fill in a link it cannot resolve, and says so", async () => {
      window.location.hash = "#/suggest?subject=11111111-1111-4111-8111-111111111111";
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      expect(
        await screen.findByText(/The subject in the link you followed is not a document or article of this matter/),
      ).toBeInTheDocument();
      expect(screen.getByLabelText("Subject source")).toHaveValue("");
      await user.selectOptions(screen.getByLabelText("Assertion type"), "APPLIES_TO");
      await user.type(screen.getByLabelText("Proposition"), "Section 12 applies.");
      await user.click(screen.getByRole("button", { name: /save as draft/i }));
      expect(await screen.findByRole("alert")).toHaveTextContent(/subject/i);
      expect(api.createAssertion).not.toHaveBeenCalled();
    });
  });

  describe("matter without sources", () => {
    it("explains how sources get into the matter instead of showing a dead form", async () => {
      vi.mocked(api.sources).mockResolvedValue({ items: [], total: 0 });
      const user = userEvent.setup();
      render(<SuggestAssertionPage />);

      expect(await screen.findByRole("heading", { name: "This matter has no sources yet" })).toBeInTheDocument();
      expect(screen.getByText(/Getting sources\s+into a matter/)).toBeInTheDocument();
      expect(screen.getByText("matter-1")).toBeInTheDocument();
      expect(screen.getByText("repo-1")).toBeInTheDocument();
      expect(screen.queryByLabelText("Proposition")).not.toBeInTheDocument();

      vi.mocked(api.sources).mockResolvedValue({ items: [{ id: "ent-9", type: "Document", label: "Lease" }], total: 1 });
      await user.click(screen.getByRole("button", { name: "Check again" }));
      expect(await screen.findByLabelText("Proposition")).toBeInTheDocument();
    });
  });
});
