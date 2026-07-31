// AdminPage — matter administration: member roster + role management,
// add-by-email flow, and the read-only review-policy reference.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MatterMember, MatterRoleName } from "../../api/types";

const mocks = vi.hoisted(() => ({
  role: "admin" as MatterRoleName,
}));

vi.mock("../../app/session", () => ({
  useActiveSession: () => {
    const matter = {
      id: "m-1",
      name: "Acme v. Zenith",
      repository_id: "r-1",
      organization_id: "o-1",
      role: mocks.role,
    };
    return {
      user: { id: "u-admin", email: "ada@firm.example", display_name: "Ada Stern" },
      matters: [matter],
      currentMatter: matter,
      role: mocks.role,
    };
  },
}));

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
      listMatterMembers: vi.fn(),
      setMatterMemberRole: vi.fn(),
      addMatterMember: vi.fn(),
      removeMatterMember: vi.fn(),
    },
  };
});

import { ApiError, api } from "../../api/client";
import { AdminPage } from "../AdminPage";

const mockedApi = vi.mocked(api);

const roster: MatterMember[] = [
  {
    user: { id: "u-admin", email: "ada@firm.example", display_name: "Ada Stern" },
    role: "admin",
  },
  {
    user: { id: "u-2", email: "boaz@firm.example", display_name: "Boaz Levi" },
    role: "contributor",
  },
  {
    user: { id: "u-3", email: "carmel@firm.example", display_name: "Carmel Noy" },
    role: "reviewer",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  mocks.role = "admin";
  // Backend GET /matters/{id}/members returns a bare JSON array (see
  // backend/app/routers/workspace.py::list_members), not { items: [...] }.
  mockedApi.listMatterMembers.mockResolvedValue(roster);
  mockedApi.setMatterMemberRole.mockResolvedValue(roster[1]);
  mockedApi.addMatterMember.mockResolvedValue(roster[2]);
  mockedApi.removeMatterMember.mockResolvedValue(undefined);
});

async function renderPage() {
  render(<AdminPage />);
  await screen.findByText("Boaz Levi");
}

describe("AdminPage", () => {
  it("loads the roster for the current matter and renders members with roles", async () => {
    await renderPage();

    expect(mockedApi.listMatterMembers).toHaveBeenCalledWith("m-1");
    // Header: matter name + member count.
    expect(screen.getByText(/3 members/)).toBeInTheDocument();
    // All three members with initials avatars, names, and emails.
    expect(screen.getByText("Ada Stern")).toBeInTheDocument();
    expect(screen.getByText("AS")).toBeInTheDocument();
    expect(screen.getByText("boaz@firm.example")).toBeInTheDocument();
    expect(screen.getByText("Carmel Noy")).toBeInTheDocument();
    // The signed-in admin's own row is marked.
    expect(screen.getByText("You")).toBeInTheDocument();
    // Role selects reflect each membership.
    expect(screen.getByLabelText("Role for Boaz Levi")).toHaveValue("contributor");
    expect(screen.getByLabelText("Role for Carmel Noy")).toHaveValue("reviewer");
  });

  it("renders the roster table when the API resolves a bare members array (D1)", async () => {
    // Pins the AdminPage crash fix: the backend returns a bare array, not
    // { items: [...] }. Before the fix this throws "Cannot read properties
    // of undefined (reading 'length')" and the roster never renders.
    await renderPage();

    expect(screen.getByText("Ada Stern")).toBeInTheDocument();
    expect(screen.getByText("Boaz Levi")).toBeInTheDocument();
    expect(screen.getByText("Carmel Noy")).toBeInTheDocument();
    expect(screen.getByLabelText("Role for Boaz Levi")).toBeInTheDocument();
    expect(screen.getByLabelText("Role for Carmel Noy")).toBeInTheDocument();
  });

  it("changes a member's role and refreshes the roster", async () => {
    await renderPage();

    fireEvent.change(screen.getByLabelText("Role for Boaz Levi"), {
      target: { value: "reviewer" },
    });

    await waitFor(() =>
      expect(mockedApi.setMatterMemberRole).toHaveBeenCalledWith("m-1", "u-2", "reviewer"),
    );
    await waitFor(() => expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(2));
  });

  it("surfaces the last-admin 409 in a banner without breaking the table", async () => {
    mockedApi.removeMatterMember.mockRejectedValue(
      new ApiError(409, "a matter must keep at least one admin"),
    );
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Remove Ada Stern" }));

    expect(
      await screen.findByText("a matter must keep at least one admin"),
    ).toBeInTheDocument();
    // Roster stays rendered and was not re-fetched after the failure.
    expect(screen.getByText("Boaz Levi")).toBeInTheDocument();
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
  });

  it("removes a member and refreshes the roster", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Remove Boaz Levi" }));

    await waitFor(() =>
      expect(mockedApi.removeMatterMember).toHaveBeenCalledWith("m-1", "u-2"),
    );
    await waitFor(() => expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(2));
  });

  it("adds a member by email with the chosen role", async () => {
    await renderPage();

    fireEvent.change(screen.getByLabelText("Email of the account to add"), {
      target: { value: "dana@firm.example" },
    });
    fireEvent.change(screen.getByLabelText("Role for the new member"), {
      target: { value: "reviewer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() =>
      expect(mockedApi.addMatterMember).toHaveBeenCalledWith(
        "m-1",
        "dana@firm.example",
        "reviewer",
      ),
    );
    await waitFor(() => expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(2));
    // Input clears on success.
    expect(screen.getByLabelText("Email of the account to add")).toHaveValue("");
  });

  it("explains a 404 when the email has no account", async () => {
    mockedApi.addMatterMember.mockRejectedValue(
      new ApiError(404, "no user account with that email"),
    );
    await renderPage();

    fireEvent.change(screen.getByLabelText("Email of the account to add"), {
      target: { value: "ghost@firm.example" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(
      await screen.findByText(
        "No user account with that email — accounts are provisioned via the seed or DB.",
      ),
    ).toBeInTheDocument();
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
  });

  it("hides management controls from non-admin roles", async () => {
    mocks.role = "reviewer";
    await renderPage();

    // Read-only roster: no role selects, no remove buttons, no add form.
    expect(screen.queryByLabelText("Role for Boaz Levi")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Remove/ })).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Email of the account to add"),
    ).not.toBeInTheDocument();
    // Roles still visible as text, plus the role note.
    expect(screen.getByText("Contributor")).toBeInTheDocument();
    expect(
      screen.getByText("Matter admin role required to manage members."),
    ).toBeInTheDocument();
  });

  it("renders the read-only review policy reference on the second tab", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("tab", { name: "Review policy" }));

    expect(
      screen.getByText(/Ratings never change review status/),
    ).toBeInTheDocument();
    expect(screen.getByText("Manage matter members & roles")).toBeInTheDocument();
    expect(
      screen.getByText(/record an acceptance justification/),
    ).toBeInTheDocument();
    // Reference content is static — no extra API traffic.
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
  });

  it("shows an error banner with retry when the roster fails to load", async () => {
    mockedApi.listMatterMembers.mockRejectedValueOnce(new Error("backend unreachable"));
    render(<AdminPage />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Boaz Levi")).toBeInTheDocument();
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(2);
  });
});
