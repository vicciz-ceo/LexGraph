// RED tests for the jurisdiction PROFILE PREFERENCE (sprint
// 2026-08-02-us-state-law, director decision #4, gate G7: "profile
// preferences across every affected page").
//
// Design call (no backend user-preference mechanism exists anywhere in
// this codebase today -- `User` (`backend/app/models/user.py`) has only
// `id`/`email`/`display_name`, and the Planner found zero `localStorage`
// usage anywhere in `frontend/src` currently): this is scoped as a
// FRONTEND-ONLY preference, persisted to `localStorage` keyed by the
// signed-in user's id (`lexgraph:default-jurisdiction:<userId>`) -- no
// backend schema change. Stated here as the Planner's call, not a silent
// assumption, so the Developer doesn't have to re-derive it; a
// backend-persisted preference (synced across devices) is a reasonable
// future upgrade but out of scope for this sprint's minimal G7 pass.
//
// New file, additive only.

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AppNotification, Assertion, AssertionListParams } from "../../api/types";

vi.mock("../../app/session", () => ({
  useActiveSession: () => ({
    user: { id: "u-me", email: "noa@example.com", display_name: "Noa Levi" },
    matters: [
      {
        id: "m-1",
        name: "Acme v. Zenith",
        repository_id: "r-1",
        organization_id: "o-1",
        role: "reviewer",
      },
    ],
    currentMatter: {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: "reviewer",
    },
    role: "reviewer",
  }),
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

const PREFERENCE_KEY = "lexgraph:default-jurisdiction:u-me";

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  mockedApi.listAssertions.mockImplementation(
    async (_matterId: string, _params: AssertionListParams = {}) => ({ items: [], total: 0 }),
  );
  mockedApi.notifications.mockResolvedValue([] as AppNotification[]);
});

async function renderPage() {
  render(<ProfilePage />);
  await screen.findByTestId("pf-stat-suggestions");
}

describe("ProfilePage jurisdiction preference", () => {
  it("renders a Default jurisdiction preference control", async () => {
    await renderPage();
    expect(screen.getByLabelText(/default jurisdiction/i)).toBeInTheDocument();
  });

  it("persists the selected default jurisdiction to localStorage, keyed by user id", async () => {
    await renderPage();
    fireEvent.change(screen.getByLabelText(/default jurisdiction/i), {
      target: { value: "US-TX" },
    });
    expect(window.localStorage.getItem(PREFERENCE_KEY)).toBe("US-TX");
  });

  it("loads a previously-saved preference on mount", async () => {
    window.localStorage.setItem(PREFERENCE_KEY, "US-CA");
    await renderPage();
    expect(screen.getByLabelText(/default jurisdiction/i)).toHaveValue("US-CA");
  });
});
