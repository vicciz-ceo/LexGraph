// Topbar global search → Knowledge Base (audit finding ui:22).
//
// Renders the real App (hash router + AppShell topbar + KnowledgeBasePage);
// only the session and the API client are mocked. The topbar search must find
// assertions in every status the viewer can see, and submitting the same
// query again must re-run it even though the URL does not change.

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Assertion } from "../../api/types";

vi.mock("../../api/client", () => ({
  api: {
    listAssertions: vi.fn(),
    notifications: vi.fn(),
  },
}));

const matter = {
  id: "m1",
  name: "Acme v. Beta Holdings",
  repository_id: "r1",
  organization_id: "o1",
  role: "viewer" as const,
};
const sessionFixture = {
  user: { id: "u1", email: "dana@example.com", display_name: "Dana Levi" },
  currentMatter: matter,
  role: "viewer" as const,
  matters: [matter],
};

vi.mock("../../app/session", () => ({
  SessionProvider: ({ children }: { children: unknown }) => children,
  useSession: () => ({
    session: sessionFixture,
    signIn: vi.fn(),
    signOut: vi.fn(),
    selectMatter: vi.fn(),
    refresh: vi.fn(),
  }),
  useActiveSession: () => sessionFixture,
}));

import { api } from "../../api/client";
import App from "../../App";

const mockedApi = api as unknown as {
  listAssertions: ReturnType<typeof vi.fn>;
  notifications: ReturnType<typeof vi.fn>;
};

const fee: Assertion = {
  id: "a1",
  organization_id: "o1",
  repository_id: "r1",
  matter_id: "m1",
  assertion_type: "obligation",
  proposition: "Termination for convenience requires payment of a termination fee.",
  proposition_raw: null,
  subject_entity: { type: "clause", id: "c-14" },
  object_entity: null,
  origin: "user_suggested",
  status: "revision_requested",
  standing: "revision_requested",
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
};

function topbarInput(): HTMLElement {
  return within(screen.getByRole("search")).getByRole("searchbox");
}

function inPageInput(): HTMLElement {
  const topbar = topbarInput();
  const boxes = screen.getAllByRole("searchbox").filter((el) => el !== topbar);
  expect(boxes).toHaveLength(1);
  return boxes[0];
}

/** Set the hash and let its (asynchronous) hashchange fire before anything
 * renders: in the app a page mounts in response to that event, never before. */
async function setHash(hash: string): Promise<void> {
  const target = hash === "" || hash === "#" ? "" : hash.startsWith("#") ? hash : `#${hash}`;
  if (window.location.hash === target) return;
  await new Promise<void>((resolve) => {
    window.addEventListener("hashchange", () => resolve(), { once: true });
    window.location.hash = hash;
  });
}

beforeEach(async () => {
  mockedApi.listAssertions.mockReset();
  mockedApi.notifications.mockReset();
  // A stand-in for the server: the revision-requested assertion matches any
  // search unless the request narrows the status to something else.
  mockedApi.listAssertions.mockImplementation(
    async (_matterId: string, params: { status?: string } = {}) =>
      !params.status || params.status === fee.status
        ? { items: [fee], total: 1 }
        : { items: [], total: 0 },
  );
  mockedApi.notifications.mockResolvedValue([]);
  // Another page that loads nothing for a viewer ("Not authorized"), so the
  // search below is entered from outside the Knowledge Base.
  await setHash("#/admin");
});

afterEach(async () => {
  cleanup();
  await setHash("");
});

describe("topbar global search", () => {
  it("entered from another page, searches every status in one request", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText("Not authorized")).toBeInTheDocument();

    await user.type(topbarInput(), "termination fee{Enter}");

    expect(await screen.findByText(fee.proposition)).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);
    expect(mockedApi.listAssertions.mock.calls[0][1]).toMatchObject({ q: "termination fee" });
    expect(mockedApi.listAssertions.mock.calls[0][1]).not.toHaveProperty("status");
  });

  it("from the Knowledge Base, searches every status, so a revision-requested assertion is found", async () => {
    await setHash("#/knowledge");
    const user = userEvent.setup();
    render(<App />);
    // The plain Knowledge Base is still the accepted catalog.
    expect(await screen.findByText("No assertions found")).toBeInTheDocument();
    expect(mockedApi.listAssertions).toHaveBeenCalledTimes(1);
    expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
      "m1",
      expect.objectContaining({ status: "accepted" }),
    );

    await user.type(topbarInput(), "termination fee{Enter}");

    await waitFor(() => expect(window.location.hash).toBe("#/knowledge?q=termination%20fee"));
    expect(await screen.findByText(fee.proposition)).toBeInTheDocument();
    const lastParams = mockedApi.listAssertions.mock.lastCall?.[1];
    expect(lastParams).toMatchObject({ q: "termination fee" });
    expect(lastParams).not.toHaveProperty("status");
    expect(screen.getByLabelText("Status")).toHaveValue("");
    expect(screen.getByText(/Results for/)).toHaveTextContent("across all statuses");
  });

  it("re-applies the query when the same search is submitted again", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(topbarInput(), "liability{Enter}");
    await waitFor(() => expect(inPageInput()).toHaveValue("liability"));
    await screen.findByText(fee.proposition);

    // The user narrows in-page: the URL (and the topbar box) still say "liability".
    await user.clear(inPageInput());
    await user.type(inPageInput(), "notify");
    await user.selectOptions(screen.getByLabelText("Status"), "accepted");
    await waitFor(() =>
      expect(mockedApi.listAssertions).toHaveBeenLastCalledWith(
        "m1",
        expect.objectContaining({ q: "notify", status: "accepted" }),
      ),
    );
    expect(window.location.hash).toBe("#/knowledge?q=liability");

    // Pressing Enter on the unchanged topbar query brings its search back.
    await user.type(topbarInput(), "{Enter}");
    await waitFor(() => expect(inPageInput()).toHaveValue("liability"));
    await waitFor(() => {
      const lastParams = mockedApi.listAssertions.mock.lastCall?.[1];
      expect(lastParams).toMatchObject({ q: "liability" });
      expect(lastParams).not.toHaveProperty("status");
    });
    expect(screen.getByText("“liability”")).toBeInTheDocument();
    expect(await screen.findByText(fee.proposition)).toBeInTheDocument();
  });

  it("re-runs an unchanged search instead of ignoring the submit", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.type(topbarInput(), "termination fee{Enter}");
    await screen.findByText(fee.proposition);
    const calls = mockedApi.listAssertions.mock.calls.length;

    await user.type(topbarInput(), "{Enter}");

    await waitFor(() =>
      expect(mockedApi.listAssertions.mock.calls.length).toBe(calls + 1),
    );
    expect(mockedApi.listAssertions.mock.lastCall?.[1]).toMatchObject({
      q: "termination fee",
    });
  });
});
