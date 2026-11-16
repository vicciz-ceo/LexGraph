// AdminPage — matter administration: member roster + role management,
// add-by-email flow, and the read-only review-policy reference.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  IssuedSignIn,
  MatterMember,
  MatterRoleName,
  UserAccount,
} from "../../api/types";

const mocks = vi.hoisted(() => ({
  role: "admin" as MatterRoleName,
  signIn: vi.fn(),
  refreshSession: vi.fn(),
}));

vi.mock("../../app/session", () => ({
  useSession: () => ({ signIn: mocks.signIn, refresh: mocks.refreshSession }),
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
      rotateSignInToken: vi.fn(),
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
  rotateSignInToken: ReturnType<typeof vi.fn>;
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
// GET /api/v1/users returns a bare array of
// {id, email, display_name, sign_in_status} — never a token or hash.
const accounts: UserAccount[] = [
  { id: "u-admin", email: "ada@firm.example", display_name: "Ada Stern", sign_in_status: "active" },
  { id: "u-2", email: "boaz@firm.example", display_name: "Boaz Levi", sign_in_status: "legacy" },
  { id: "u-9", email: "dana@firm.example", display_name: "Dana Cohen", sign_in_status: "none" },
];

// POST /api/v1/users returns the new account plus its one-time token.
const createdAccount: IssuedSignIn = {
  id: "new-user-123",
  email: "erez@firm.example",
  display_name: "Erez Katz",
  sign_in_status: "active",
  sign_in_token: "tok-erez-0123456789abcdefghijklmnopqrstuvwx",
};

function rotated(account: UserAccount, token: string): IssuedSignIn {
  return { ...account, sign_in_status: "active", sign_in_token: token };
}

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
  mockedUsersApi.rotateSignInToken.mockImplementation(async (id: string) =>
    rotated(accounts.find((a) => a.id === id)!, `tok-rotated-${id}-abcdefghijklmnopqrstuvwxyz`),
  );
  mocks.signIn.mockResolvedValue(undefined);
  mocks.refreshSession.mockResolvedValue(undefined);
  window.location.hash = "#/admin";
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

  // --- Changing your own membership (finding ui:19) -------------------------
  //
  // A successful change to your own membership always costs you the admin
  // role on this matter: the page refreshes the session (GET /me) so the
  // role-gated chrome follows, and leaves /admin instead of re-fetching a
  // roster you may no longer be allowed to see (after a self-removal that
  // re-fetch 403'd and reported the success as an error).

  it("demoting yourself refreshes the session and leaves the admin page", async () => {
    await renderPage();

    fireEvent.change(screen.getByLabelText("Role for Ada Stern"), {
      target: { value: "viewer" },
    });

    await waitFor(() => expect(mocks.refreshSession).toHaveBeenCalledTimes(1));
    expect(mockedApi.setMatterMemberRole).toHaveBeenCalledWith("m-1", "u-admin", "viewer");
    await waitFor(() => expect(window.location.hash).toBe("#/review"));
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
  });

  it("removing yourself refreshes the session without a false error or roster re-fetch", async () => {
    mockedApi.listMatterMembers
      .mockResolvedValueOnce(roster)
      .mockRejectedValue(new ApiError(403, "no access to matter"));
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Remove Ada Stern" }));

    await waitFor(() => expect(mocks.refreshSession).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(window.location.hash).toBe("#/review"));
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/no longer permits/i)).not.toBeInTheDocument();
  });

  it("changing someone else does not touch the session", async () => {
    await renderPage();

    fireEvent.change(screen.getByLabelText("Role for Boaz Levi"), {
      target: { value: "viewer" },
    });

    await waitFor(() => expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(2));
    expect(mocks.refreshSession).not.toHaveBeenCalled();
    expect(window.location.hash).toBe("#/admin");
  });

  it("a refused change to yourself (last admin) keeps the session as it is", async () => {
    mockedApi.removeMatterMember.mockRejectedValue(
      new ApiError(409, "a matter must keep at least one admin"),
    );
    await renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Remove Ada Stern" }));

    expect(await screen.findByText("a matter must keep at least one admin")).toBeInTheDocument();
    expect(mocks.refreshSession).not.toHaveBeenCalled();
    expect(window.location.hash).toBe("#/admin");
  });

  it("asks for a reload when the session cannot be refreshed after changing yourself", async () => {
    mocks.refreshSession.mockRejectedValue(new TypeError("fetch failed"));
    await renderPage();

    fireEvent.change(screen.getByLabelText("Role for Ada Stern"), {
      target: { value: "viewer" },
    });

    expect(
      await screen.findByText("Your access to this matter changed. Reload the page to continue."),
    ).toBeInTheDocument();
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
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

    // Accounts are created in-app (User accounts tab), not via seed or DB.
    expect(
      await screen.findByText(
        "No user account with that email — create it first under User accounts.",
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
    // A new revision leaves a revision-requested assertion there; only
    // submitting it again returns it to proposed (ui:34).
    expect(
      screen.getByText(/resubmits it, which returns it to proposed/),
    ).toBeInTheDocument();
    // Reference content is static — no extra API traffic.
    expect(mockedApi.listMatterMembers).toHaveBeenCalledTimes(1);
  });

  it("says that a revision-requested assertion returns to review when resubmitted (ui:34)", async () => {
    await renderPage();

    fireEvent.click(screen.getByRole("tab", { name: "Review policy" }));

    // Saving a new revision keeps it "Revision requested"; only submitting
    // it for review again makes it proposed (backend/app/routers/assertions.py).
    expect(screen.getByText(/revises it and resubmits it/i)).toBeInTheDocument();
    expect(screen.queryByText(/a new revision returns it to proposed/i)).not.toBeInTheDocument();
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
  // and creates one via api.createUser. Re-pointed 2026-11-16 (findings
  // api:2/ui:0): the user id is public, so the page surfaces the one-time
  // SIGN-IN TOKEN the API returns (with copy + warning), not the id, and
  // offers per-account token rotation with a legacy badge. Gated the same
  // way the existing mutating members controls are (canManage =
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

    it("creates an account and shows its one-time sign-in token with a copy button and warning", async () => {
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
      // The token is the credential -- it must render (not vanish in a
      // toast), with the shown-once warning and a copy affordance.
      const callout = await screen.findByRole("status", { name: "New sign-in token" });
      expect(callout).toHaveTextContent(createdAccount.sign_in_token);
      expect(callout).toHaveTextContent(/shown only once/i);
      expect(callout).toHaveTextContent("Sign-in token for Erez Katz");
      expect(screen.getByRole("button", { name: "Copy token" })).toBeInTheDocument();
      // The public id is not presented as the credential.
      expect(callout).not.toHaveTextContent("new-user-123");
    });

    it("forgets the token once the admin clicks Done", async () => {
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
      await screen.findByText(createdAccount.sign_in_token);

      fireEvent.click(screen.getByRole("button", { name: /done, i have saved the token/i }));

      expect(screen.queryByText(createdAccount.sign_in_token)).not.toBeInTheDocument();
      expect(document.body).not.toHaveTextContent(createdAccount.sign_in_token);
    });

    it("copies the token to the clipboard", async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText },
        configurable: true,
      });
      try {
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
        await screen.findByText(createdAccount.sign_in_token);

        fireEvent.click(screen.getByRole("button", { name: "Copy token" }));

        await waitFor(() => expect(writeText).toHaveBeenCalledWith(createdAccount.sign_in_token));
        expect(await screen.findByRole("button", { name: /copied/i })).toBeInTheDocument();
      } finally {
        Reflect.deleteProperty(navigator, "clipboard");
      }
    });

    it("asks to copy manually when the clipboard is unavailable", async () => {
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
      await screen.findByText(createdAccount.sign_in_token);

      fireEvent.click(screen.getByRole("button", { name: "Copy token" }));

      expect(await screen.findByText(/copy failed/i)).toBeInTheDocument();
    });

    it("badges each account's sign-in status and flags legacy sign-ins", async () => {
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      expect(screen.getByText("Active")).toBeInTheDocument();
      expect(screen.getByText("Legacy sign-in")).toBeInTheDocument();
      expect(screen.getByText("No token")).toBeInTheDocument();
      expect(screen.getByRole("note")).toHaveTextContent(
        /1 account still signs in with its public user id/,
      );
      expect(
        screen.getByRole("button", { name: "Rotate sign-in token for Boaz Levi" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Issue sign-in token for Dana Cohen" }),
      ).toBeInTheDocument();
    });

    it("rotates a token after confirmation, shows the new token once, and reloads the list", async () => {
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      fireEvent.click(screen.getByRole("button", { name: "Rotate sign-in token for Boaz Levi" }));
      expect(screen.getByText("Current token stops working.")).toBeInTheDocument();
      expect(mockedUsersApi.rotateSignInToken).not.toHaveBeenCalled();
      fireEvent.click(
        screen.getByRole("button", { name: "Confirm new sign-in token for Boaz Levi" }),
      );

      await waitFor(() => expect(mockedUsersApi.rotateSignInToken).toHaveBeenCalledWith("u-2"));
      const callout = await screen.findByRole("status", { name: "New sign-in token" });
      expect(callout).toHaveTextContent("tok-rotated-u-2-");
      expect(callout).toHaveTextContent(/previous token no longer works/i);
      await waitFor(() => expect(mockedUsersApi.listUsers).toHaveBeenCalledTimes(2));
      // Someone else's token: this browser's session is untouched.
      expect(mocks.signIn).not.toHaveBeenCalled();
    });

    it("cancelling the confirmation does not rotate", async () => {
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      fireEvent.click(screen.getByRole("button", { name: "Rotate sign-in token for Boaz Levi" }));
      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(mockedUsersApi.rotateSignInToken).not.toHaveBeenCalled();
      expect(
        screen.getByRole("button", { name: "Rotate sign-in token for Boaz Levi" }),
      ).toBeInTheDocument();
    });

    it("rotating your own token switches this session to the new token", async () => {
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      fireEvent.click(screen.getByRole("button", { name: "Rotate sign-in token for Ada Stern" }));
      fireEvent.click(
        screen.getByRole("button", { name: "Confirm new sign-in token for Ada Stern" }),
      );

      await waitFor(() =>
        expect(mocks.signIn).toHaveBeenCalledWith(
          "tok-rotated-u-admin-abcdefghijklmnopqrstuvwxyz",
        ),
      );
      expect(await screen.findByText(/this browser now signs in with the new token/i)).toBeInTheDocument();
    });

    it("surfaces a refused rotation without showing a token", async () => {
      mockedUsersApi.rotateSignInToken.mockRejectedValueOnce(
        new ApiError(
          403,
          "rotating this account's sign-in token requires the admin role on every matter it belongs to",
        ),
      );
      await renderPage();
      fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
      await screen.findByText("Dana Cohen");

      fireEvent.click(screen.getByRole("button", { name: "Rotate sign-in token for Boaz Levi" }));
      fireEvent.click(
        screen.getByRole("button", { name: "Confirm new sign-in token for Boaz Levi" }),
      );

      expect(await screen.findByText(/requires the admin role on every matter/)).toBeInTheDocument();
      expect(screen.queryByRole("status", { name: "New sign-in token" })).not.toBeInTheDocument();
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
      await screen.findByText(createdAccount.sign_in_token);

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
