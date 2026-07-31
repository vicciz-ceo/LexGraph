// ProfilePage — the signed-in user's activity in the current matter.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AppNotification,
  Assertion,
  AssertionListParams,
  MatterRoleName,
} from "../../api/types";

const mocks = vi.hoisted(() => ({
  role: "reviewer" as MatterRoleName,
}));

vi.mock("../../app/session", () => ({
  useActiveSession: () => {
    const current = {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: mocks.role,
    };
    const other = {
      id: "m-2",
      name: "Estate of Harel",
      repository_id: "r-2",
      organization_id: "o-1",
      role: "viewer" as MatterRoleName,
    };
    return {
      user: { id: "u-me", email: "noa@example.com", display_name: "Noa Levi" },
      matters: [current, other],
      currentMatter: current,
      role: mocks.role,
    };
  },
}));

vi.mock("../../api/client", () => ({
  api: {
    listAssertions: vi.fn(),
    notifications: vi.fn(),
  },
}));

import { api } from "../../api/client";
import { ProfilePage } from "../ProfilePage";

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
    status: "proposed",
    standing: "proposed",
    author_user_id: "u-me",
    confidence: null,
    jurisdiction: "IL",
    effective_from: null,
    effective_to: null,
    created_at: "2026-07-01T09:00:00Z",
    updated_at: "2026-07-20T09:00:00Z",
    submitted_at: "2026-07-02T09:00:00Z",
    reviewed_by: null,
    reviewed_at: null,
    superseded_by_assertion_id: null,
    current_revision_number: 1,
    evidence_status: "evidenced",
    ...overrides,
  };
}

// The matter's full assertion list: four authored by the signed-in user
// (one accepted, one rejected, one proposed, one draft) plus one authored
// by a colleague that must be excluded from the "my" stats and list.
const matterItems: Assertion[] = [
  makeAssertion({
    id: "a-mine-accepted",
    proposition: "The guarantee covers obligations incurred before closing.",
    status: "accepted",
    standing: "accepted",
    updated_at: "2026-07-25T09:00:00Z",
  }),
  makeAssertion({
    id: "a-mine-rejected",
    proposition: "Termination requires 90 days' written notice.",
    status: "rejected",
    standing: "rejected",
    updated_at: "2026-07-24T09:00:00Z",
  }),
  makeAssertion({
    id: "a-mine-proposed",
    proposition: "The 2021 lease amendment extends the term to 2030.",
    status: "proposed",
    standing: "probable",
    updated_at: "2026-07-23T09:00:00Z",
  }),
  makeAssertion({
    id: "a-mine-draft",
    proposition: "Renewal rent resets to fair market value.",
    status: "draft",
    standing: "draft",
    updated_at: "2026-07-22T09:00:00Z",
  }),
  makeAssertion({
    id: "a-other",
    proposition: "Signed by both parties on 2026-01-15.",
    status: "accepted",
    standing: "accepted",
    author_user_id: "u-other",
  }),
];

const awaitingItems: Assertion[] = [
  makeAssertion({
    id: "aw-1",
    proposition: "Clause 9 restricts assignment without consent.",
    origin: "model_suggested",
    confidence: 0.82,
    author_user_id: "u-other",
    submitted_at: "2026-07-05T09:00:00Z",
  }),
  makeAssertion({
    id: "aw-2",
    proposition: "The guarantee expires on 2027-03-01.",
    origin: "user_suggested",
    author_user_id: "u-other",
    jurisdiction: null,
  }),
];

// Out of chronological order on purpose — the page must sort newest first.
const notificationItems: AppNotification[] = [
  {
    id: "n-1",
    event_type: "assertion_accepted",
    actor_user_id: "u-reviewer",
    recipient_user_id: "u-me",
    payload: {},
    created_at: "2026-07-20T10:00:00Z",
    read: true,
  },
  {
    id: "n-2",
    event_type: "rating_added",
    actor_user_id: "u-other",
    recipient_user_id: "u-me",
    payload: {},
    created_at: "2026-07-25T10:00:00Z",
    read: false,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  mocks.role = "reviewer";
  mockedApi.listAssertions.mockImplementation(
    async (_matterId: string, params: AssertionListParams = {}) =>
      params.unrated_by_me
        ? { items: awaitingItems, total: 2 }
        : { items: matterItems, total: matterItems.length },
  );
  mockedApi.notifications.mockResolvedValue(notificationItems);
});

async function renderPage() {
  render(<ProfilePage />);
  await screen.findByTestId("pf-stat-suggestions");
}

describe("ProfilePage", () => {
  it("renders identity from the session and stats computed from the matter's assertions", async () => {
    await renderPage();

    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {});
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {
      status: "proposed",
      unrated_by_me: true,
    });

    // Identity header: name + role badge + email + matter scope.
    expect(screen.getByRole("heading", { name: /Noa Levi/ })).toBeInTheDocument();
    expect(screen.getByText(/noa@example\.com · activity in Acme v\. Zenith/)).toBeInTheDocument();

    // Stats: 4 authored, 1 accepted, 1/(1+1) = 50% acceptance, 2 awaiting.
    expect(screen.getByTestId("pf-stat-suggestions")).toHaveTextContent(/^4$/);
    expect(screen.getByTestId("pf-stat-accepted")).toHaveTextContent(/^1$/);
    expect(screen.getByTestId("pf-stat-acceptance")).toHaveTextContent(/^50%$/);
    expect(screen.getByTestId("pf-stat-awaiting")).toHaveTextContent(/^2$/);
  });

  it("defaults to the awaiting tab: origin chips, meta, and Rate links to the detail page", async () => {
    await renderPage();

    expect(screen.getByRole("tab", { name: /Awaiting my rating/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    const panel = screen.getByRole("tabpanel");
    expect(
      within(panel).getByText("Clause 9 restricts assignment without consent."),
    ).toBeInTheDocument();
    expect(within(panel).getByText("AI-deduced")).toBeInTheDocument();
    expect(within(panel).getByText("Colleague")).toBeInTheDocument();
    // Model confidence rendered as a percent, only for the model-suggested item.
    expect(within(panel).getByText(/model confidence 82%/)).toBeInTheDocument();

    const rateLinks = within(panel).getAllByRole("link", { name: "Rate" });
    expect(rateLinks).toHaveLength(2);
    expect(rateLinks[0]).toHaveAttribute("href", "#/assertions/aw-1");
  });

  it("shows my authored assertions with status and standing badges, excluding colleagues'", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));

    const panel = screen.getByRole("tabpanel");
    expect(within(panel).getByText("Accepted")).toBeInTheDocument();
    expect(within(panel).getByText("Rejected")).toBeInTheDocument();
    expect(within(panel).getByText("Proposed")).toBeInTheDocument();
    expect(within(panel).getByText("Draft")).toBeInTheDocument();
    // Standing grade shown only for the proposed assertion.
    expect(within(panel).getByText("Standing: probable")).toBeInTheDocument();
    // The colleague's assertion is not mine.
    expect(
      within(panel).queryByText("Signed by both parties on 2026-01-15."),
    ).not.toBeInTheDocument();
  });

  it("lists notifications newest first with humanized event types and the reset note", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("tab", { name: /Notifications/ }));

    const panel = screen.getByRole("tabpanel");
    const items = within(panel).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Rating added");
    expect(items[1]).toHaveTextContent("Assertion accepted");
    expect(within(panel).getByText(/reset when the server restarts/)).toBeInTheDocument();
  });

  it("hides rating work entirely from viewers and skips the unrated query", async () => {
    mocks.role = "viewer";
    await renderPage();

    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);
    expect(mockedApi.listAssertions).toHaveBeenCalledWith("m-1", {});

    expect(screen.queryByRole("tab", { name: /Awaiting my rating/ })).not.toBeInTheDocument();
    expect(screen.queryByTestId("pf-stat-awaiting")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Rate" })).not.toBeInTheDocument();

    // Falls back to the suggestions tab.
    expect(screen.getByRole("tab", { name: /My suggestions/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("renders empty states and an em-dash acceptance rate when I authored nothing", async () => {
    mockedApi.listAssertions.mockImplementation(
      async (_matterId: string, params: AssertionListParams = {}) =>
        params.unrated_by_me
          ? { items: [], total: 0 }
          : { items: [matterItems[4]], total: 1 },
    );
    await renderPage();

    expect(screen.getByTestId("pf-stat-suggestions")).toHaveTextContent(/^0$/);
    expect(screen.getByTestId("pf-stat-acceptance")).toHaveTextContent("—");
    expect(screen.getByText("All caught up")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /My suggestions/ }));
    expect(screen.getByText("No suggestions yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Suggest an assertion" })).toHaveAttribute(
      "href",
      "#/suggest",
    );
  });

  it("shows an error banner with a retry control when loading fails", async () => {
    mockedApi.listAssertions.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<ProfilePage />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByTestId("pf-stat-suggestions")).toBeInTheDocument();
  });

  it("lists my matters with roles and highlights the current one", async () => {
    await renderPage();

    const matters = screen.getByTestId("pf-matters");
    const currentRow = within(matters).getByText("Acme v. Zenith").closest("li");
    expect(currentRow).not.toBeNull();
    expect(currentRow).toHaveTextContent("Current");
    expect(currentRow).toHaveTextContent("reviewer");

    const otherRow = within(matters).getByText("Estate of Harel").closest("li");
    expect(otherRow).toHaveTextContent("viewer");
    expect(otherRow).not.toHaveTextContent("Current");
    expect(within(matters).getByText(/Switch the active matter/)).toBeInTheDocument();
  });
});
