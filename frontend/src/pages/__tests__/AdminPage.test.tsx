// AdminPage — matter administration: member roster + role management,
// add-by-email flow, and the read-only review-policy reference.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MatterMember, MatterRoleName, UserInfo } from "../../api/types";

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
      // B2/UI1 (sprint 2026-07-31-admin-provisioning): not on the real
      // client.ts's declared `Api` type yet (Developer work) -- accessed
      // below via `mockedUsersApi`, a narrow cast, so referencing them
      // here doesn't block `npm run typecheck` while they're still RED.
      listUsers: vi.fn(),
      createUser: vi.fn(),
    },
  };
});

import { ApiError, api } from "../../api/client";
import { AdminPage } from "../AdminPage";

const mockedApi = vi.mocked(api);
// B2/UI1: `api.listUsers`/`api.createUser` don't exist on the real
// `client.ts` module's exported type yet (adding them is Developer work
// per the sprint contract) -- this cast isolates the two new mock
// symbols so the rest of the file keeps full type-checking against the
// real `Api` shape.
const mockedUsersApi = api as unknown as {
  listUsers: ReturnType<typeof vi.fn>;
  createUser: ReturnType<typeof vi.fn>;
};

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

// B2 response shape pin (backend/tests/integration/test_users_api.py):
// GET /api/v1/users returns a bare array of {id, email, display_name}.
const accounts: UserInfo[] = [
  { id: "u-admin", email: "ada@firm.example", display_name: "Ada Stern" },
  { id: "u-2", email: "boaz@firm.example", display_name: "Boaz Levi" },
  { id: "u-9", email: "dana@firm.example", display_name: "Dana Cohen" },
];

const createdAccount: UserInfo = {
  id: "new-user-123",
  email: "erez@firm.example",
  display_name: "Erez Katz",
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.role = "admin";
  // Backend GET /matters/{id}/members returns a bare JSON array (see
  // backend/app/routers/workspace.py::list_members), not { items: [...] }.
  mockedApi.listMatterMembers.mockResolvedValue(roster);
  mockedApi.setMatterMemberRole.mockResolvedValue(roster[1]);
  mockedApi.addMatterMember.mockResolvedValue(roster[2]);
  mockedApi.removeMatterMember.mockResolvedValue(undefined);
  mockedUsersApi.listUsers.mockResolvedValue(accounts);
  mockedUsersApi.createUser.mockResolvedValue(createdAccount);
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

  // --- User accounts (B2/UI1, sprint 2026-07-31-admin-provisioning) -------
  //
  // A new tab on this same page: lists global accounts via api.listUsers
  // and creates one via api.createUser, surfacing the returned sign-in id
  // (R3: the id IS the credential) so the admin can hand it over. Gated
  // the same way the existing mutating members controls are (canManage =
  // session.role === "admin") -- App.tsx's own route gate is the outer
  // layer, this is defense in depth for when AdminPage renders directly.

  describe("User accounts", () => {
    it("lists accounts via api.listUsers on the User accounts tab", async () => {
      await renderPage();

      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));

      await waitFor(() => expect(mockedUsersApi.listUsers).toHaveBeenCalledTimes(1));
      expect(await screen.findByText("Dana Cohen")).toBeInTheDocument();
      expect(screen.getByText("dana@firm.example")).toBeInTheDocument();
    });

    it("creates an account and shows the returned sign-in id so the admin can copy it", async () => {
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      fireEvent.change(screen.getByLabelText(/email for the new account/i), {
        target: { value: "erez@firm.example" },
      });
      fireEvent.change(screen.getByLabelText(/display name for the new account/i), {
        target: { value: "Erez Katz" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create account" }));

      await waitFor(() =>
        expect(mockedUsersApi.createUser).toHaveBeenCalledWith(
          "erez@firm.example",
          "Erez Katz",
        ),
      );
      // The id is the sign-in credential (R3) -- it must render, not just
      // exist in a success toast that vanishes.
      expect(await screen.findByText("new-user-123")).toBeInTheDocument();
    });

    it("pre-fills the new account's email into the existing add-member form", async () => {
      // One wiring assertion between the new create-account flow and the
      // already-tested add-by-email flow (see "adds a member by email
      // with the chosen role" above) -- not re-testing that flow deeply.
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      fireEvent.change(screen.getByLabelText(/email for the new account/i), {
        target: { value: "erez@firm.example" },
      });
      fireEvent.change(screen.getByLabelText(/display name for the new account/i), {
        target: { value: "Erez Katz" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create account" }));
      await screen.findByText("new-user-123");

      fireEvent.click(screen.getByRole("tab", { name: "Members & roles" }));

      expect(screen.getByLabelText("Email of the account to add")).toHaveValue(
        "erez@firm.example",
      );
    });

    it("does not render the User accounts tab (or fetch accounts) for non-admin roles", async () => {
      mocks.role = "reviewer";
      await renderPage();

      expect(
        screen.queryByRole("tab", { name: "User accounts" }),
      ).not.toBeInTheDocument();
      expect(mockedUsersApi.listUsers).not.toHaveBeenCalled();
    });
  });
});
