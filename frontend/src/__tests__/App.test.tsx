// App-level behaviour with the REAL SessionProvider, App, AppShell, pages and
// api client; only `fetch` is replaced, by a small in-memory backend.
//
// - ui:18: restoring a saved sign-in drops the token only on a real 401; on
//   a network error, 5xx or any other answer it keeps the token and shows a
//   retry screen. A live session is never signed out by connectivity trouble.
// - ui:19: the session re-reads GET /me after a refused request, when the
//   tab regains focus and every minute, and the admin console refreshes it
//   after you change your own membership, so role-gated UI follows the server.
// - ui:26: below 768px the sidebar is a drawer behind a menu button.
// - ui:27: a malformed percent-escape in the hash route does not blank the app.

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

const TOKEN_KEY = "lexgraph.token";
const MATTER_KEY = "lexgraph.matter";

type Role = "viewer" | "contributor" | "reviewer" | "admin";

interface Matter {
  id: string;
  name: string;
  role: Role;
}

interface Member {
  user: { id: string; email: string; display_name: string };
  role: Role;
}

interface Reply {
  status: number;
  body?: unknown;
}

const ADA = { id: "u-ada", email: "ada@firm.example", display_name: "Ada Admin" };
const RIVA = { id: "u-riva", email: "riva@firm.example", display_name: "Riva Reviewer" };

/** The signed-in user is always Ada; tests change what the server says about her. */
class FakeBackend {
  /** Every request fails without a response (server down / offline). */
  down = false;
  /** Force GET /me to answer this status. */
  meStatus: number | null = null;
  /** Member writes answer 403 (Ada lost the admin role elsewhere). */
  forbidMemberWrites = false;
  matters: Matter[] = [{ id: "m-msa", name: "MSA", role: "admin" }];
  members: Record<string, Member[]> = {
    "m-msa": [
      { user: ADA, role: "admin" },
      { user: RIVA, role: "admin" },
    ],
  };
  calls: { method: string; path: string; auth?: string }[] = [];

  handle(method: string, path: string, body: Record<string, unknown> | undefined): Reply {
    if (this.down) throw new TypeError("Failed to fetch");
    if (path === "/me") {
      if (this.meStatus !== null) return { status: this.meStatus, body: { detail: "x" } };
      return {
        status: 200,
        body: {
          user: ADA,
          matters: this.matters.map((m) => ({ ...m, repository_id: "r-1", organization_id: "o-1" })),
        },
      };
    }
    if (path === "/notifications") return { status: 200, body: [] };
    if (path === "/assertions" && method === "GET") return { status: 200, body: { items: [], total: 0 } };

    const roster = path.match(/^\/matters\/([^/]+)\/members$/);
    if (roster && method === "GET") {
      if (!this.matters.some((m) => m.id === roster[1])) {
        return { status: 403, body: { detail: "no access to matter" } };
      }
      return { status: 200, body: this.members[roster[1]] ?? [] };
    }
    const member = path.match(/^\/matters\/([^/]+)\/members\/([^/]+)$/);
    if (member) {
      if (this.forbidMemberWrites) return { status: 403, body: { detail: "matter admin role required" } };
      const [, matterId, userId] = member;
      const rows = this.members[matterId] ?? [];
      if (method === "PUT") {
        const row = rows.find((m) => m.user.id === userId)!;
        row.role = body!.role as Role;
        if (userId === ADA.id) {
          this.matters = this.matters.map((m) => (m.id === matterId ? { ...m, role: row.role } : m));
        }
        return { status: 200, body: row };
      }
      if (method === "DELETE") {
        this.members[matterId] = rows.filter((m) => m.user.id !== userId);
        if (userId === ADA.id) this.matters = this.matters.filter((m) => m.id !== matterId);
        return { status: 204 };
      }
    }
    return { status: 404, body: { detail: "not found" } };
  }

  count(path: string): number {
    return this.calls.filter((c) => c.path === path).length;
  }
}

let backend: FakeBackend;
let clockOffset = 0;

beforeEach(() => {
  backend = new FakeBackend();
  clockOffset = 0;
  const realNow = Date.now.bind(Date);
  vi.spyOn(Date, "now").mockImplementation(() => realNow() + clockOffset);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = new URL(input);
      const method = init.method ?? "GET";
      const path = url.pathname.replace(/^\/api\/v1/, "");
      const headers = (init.headers ?? {}) as Record<string, string>;
      backend.calls.push({ method, path, auth: headers.Authorization });
      const reply = backend.handle(method, path, init.body ? JSON.parse(String(init.body)) : undefined);
      return {
        status: reply.status,
        ok: reply.status >= 200 && reply.status < 300,
        text: async () => (reply.body === undefined ? "" : JSON.stringify(reply.body)),
      };
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function renderApp({ hash = "#/review", token = "tok-ada", matter = "m-msa" } = {}) {
  window.localStorage.clear();
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  if (matter) window.localStorage.setItem(MATTER_KEY, matter);
  window.location.hash = hash;
  return render(<App />);
}

const primaryNav = () => screen.findByRole("navigation", { name: "Primary" });

/** Let more than the re-check throttle pass, then bring the tab back. */
function refocusLater() {
  clockOffset += 10_000;
  act(() => {
    window.dispatchEvent(new Event("focus"));
  });
}

describe("restoring a saved sign-in (ui:18)", () => {
  it("keeps the saved token and offers a retry when the server cannot be reached", async () => {
    backend.down = true;
    renderApp();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not reach the lexgraph server/i);
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/sign-in token/i)).not.toBeInTheDocument();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-ada");
  });

  it.each([500, 502, 503, 504, 404, 429])(
    "keeps the saved token when GET /me answers %i",
    async (status) => {
      backend.meStatus = status;
      renderApp();

      expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveTextContent(String(status));
      expect(screen.queryByLabelText(/sign-in token/i)).not.toBeInTheDocument();
      expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-ada");
    },
  );

  it("Retry restores the session with the saved token once the server is back", async () => {
    backend.down = true;
    renderApp();
    const retry = await screen.findByRole("button", { name: "Retry" });

    backend.down = false;
    fireEvent.click(retry);

    expect(await primaryNav()).toBeInTheDocument();
    const meAuth = backend.calls.filter((c) => c.path === "/me").map((c) => c.auth);
    expect(new Set(meAuth)).toEqual(new Set(["Bearer tok-ada"]));
  });

  it("retries by itself when the browser comes back online", async () => {
    backend.down = true;
    renderApp();
    await screen.findByRole("button", { name: "Retry" });

    backend.down = false;
    act(() => {
      window.dispatchEvent(new Event("online"));
    });

    expect(await primaryNav()).toBeInTheDocument();
  });

  it("retries by itself when the tab regains focus", async () => {
    backend.down = true;
    renderApp();
    await screen.findByRole("button", { name: "Retry" });

    backend.down = false;
    refocusLater();

    expect(await primaryNav()).toBeInTheDocument();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-ada");
  });

  it("offers signing in with a different token, which forgets the saved one", async () => {
    backend.meStatus = 503;
    renderApp();

    fireEvent.click(await screen.findByRole("button", { name: "Sign in with a different token" }));

    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("signs out only when the server rejects the token (401), and says why", async () => {
    backend.meStatus = 401;
    renderApp();

    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/no longer valid/i);
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});

describe("a live session follows the server (ui:18, ui:19)", () => {
  it("stays signed in when a background re-check cannot reach the server", async () => {
    renderApp();
    await primaryNav();

    backend.down = true;
    refocusLater();

    await waitFor(() => expect(backend.count("/me")).toBe(2));
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-ada");
  });

  it("signs out with an explanation once the token really stopped working", async () => {
    renderApp();
    await primaryNav();

    backend.meStatus = 401;
    refocusLater();

    expect(await screen.findByLabelText(/sign-in token/i, {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/no longer valid/i);
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("re-reads /me when the tab regains focus, so a role change made elsewhere shows", async () => {
    renderApp();
    const nav = await primaryNav();
    expect(within(nav).getByRole("link", { name: /admin/i })).toBeInTheDocument();

    backend.matters = [{ id: "m-msa", name: "MSA", role: "viewer" }];
    refocusLater();

    expect(await screen.findByText(/viewer · ada@firm\.example/)).toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: /admin/i })).not.toBeInTheDocument();
  });

  it("re-reads /me after a refused request and re-gates the admin console", async () => {
    renderApp({ hash: "#/admin" });
    await screen.findByText("Riva Reviewer");

    // Another admin demoted Ada meanwhile: her next change is refused.
    backend.matters = [{ id: "m-msa", name: "MSA", role: "viewer" }];
    backend.forbidMemberWrites = true;
    fireEvent.change(screen.getByLabelText("Role for Riva Reviewer"), {
      target: { value: "reviewer" },
    });

    expect(await screen.findByText("Not authorized")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).queryByRole("link", { name: /admin/i })).not.toBeInTheDocument();
  });

  it("re-reads /me every minute", async () => {
    const setIntervalSpy = vi.spyOn(window, "setInterval");
    renderApp();
    await primaryNav();
    const minute = setIntervalSpy.mock.calls.find(([, delay]) => delay === 60_000);
    expect(minute).toBeDefined();

    backend.matters = [{ id: "m-msa", name: "MSA", role: "reviewer" }];
    clockOffset += 61_000;
    act(() => {
      (minute![0] as () => void)();
    });

    expect(await screen.findByText(/reviewer · ada@firm\.example/)).toBeInTheDocument();
  });
});

describe("changing your own membership in the admin console (ui:19)", () => {
  it("demoting yourself updates the role everywhere and leaves the admin page", async () => {
    renderApp({ hash: "#/admin" });
    await screen.findByText("Riva Reviewer");

    fireEvent.change(screen.getByLabelText("Role for Ada Admin"), { target: { value: "viewer" } });

    await waitFor(() => expect(window.location.hash).toBe("#/review"));
    expect(await screen.findByText(/viewer · ada@firm\.example/)).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).queryByRole("link", { name: /admin/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/no longer permits/i)).not.toBeInTheDocument();
  });

  it("removing yourself switches to a matter you still belong to, without a false error", async () => {
    backend.matters = [
      { id: "m-dpa", name: "DPA", role: "admin" },
      { id: "m-msa", name: "MSA", role: "admin" },
    ];
    backend.members["m-dpa"] = [{ user: ADA, role: "admin" }];
    renderApp({ hash: "#/admin", matter: "m-msa" });
    await screen.findByText("Riva Reviewer");

    fireEvent.click(screen.getByRole("button", { name: "Remove Ada Admin" }));

    await waitFor(() =>
      expect(screen.queryByRole("option", { name: "MSA" })).not.toBeInTheDocument(),
    );
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-dpa");
    await waitFor(() => expect(window.location.hash).toBe("#/review"));
    expect(screen.queryByText(/no longer permits/i)).not.toBeInTheDocument();
  });

  it("removing yourself from your only matter shows the no-access screen", async () => {
    renderApp({ hash: "#/admin" });
    await screen.findByText("Riva Reviewer");

    fireEvent.click(screen.getByRole("button", { name: "Remove Ada Admin" }));

    expect(await screen.findByText("No matter access")).toBeInTheDocument();
  });
});

describe("navigation on narrow viewports (ui:26)", () => {
  async function openDrawer() {
    renderApp();
    await primaryNav();
    const menu = screen.getByRole("button", { name: "Open navigation" });
    const drawer = document.getElementById("app-sidebar")!;
    fireEvent.click(menu);
    return { menu, drawer };
  }

  it("offers a menu button that opens the sidebar, with every navigation control, as a drawer", async () => {
    renderApp();
    await primaryNav();
    const menu = screen.getByRole("button", { name: "Open navigation" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveAttribute("aria-controls", "app-sidebar");
    const drawer = document.getElementById("app-sidebar")!;
    expect(drawer).not.toHaveClass("sidebar--open");
    expect(within(drawer).getByRole("combobox", { name: "Matter" })).toBeInTheDocument();
    expect(within(drawer).getByRole("link", { name: /knowledge base/i })).toBeInTheDocument();
    expect(within(drawer).getByRole("link", { name: "My profile" })).toBeInTheDocument();
    expect(within(drawer).getByRole("button", { name: "Sign out" })).toBeInTheDocument();

    fireEvent.click(menu);

    expect(menu).toHaveAttribute("aria-expanded", "true");
    expect(drawer).toHaveClass("sidebar--open");
    expect(within(drawer).getByRole("button", { name: "Close navigation" })).toHaveFocus();
  });

  it("closes on Escape and gives focus back to the menu button", async () => {
    const { menu, drawer } = await openDrawer();

    fireEvent.keyDown(document.activeElement!, { key: "Escape" });

    expect(drawer).not.toHaveClass("sidebar--open");
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveFocus();
  });

  it("closes with its close button and after following a link", async () => {
    const { menu, drawer } = await openDrawer();
    fireEvent.click(within(drawer).getByRole("button", { name: "Close navigation" }));
    expect(drawer).not.toHaveClass("sidebar--open");
    expect(menu).toHaveFocus();

    fireEvent.click(menu);
    fireEvent.click(within(drawer).getByRole("link", { name: /knowledge base/i }));
    expect(drawer).not.toHaveClass("sidebar--open");
  });

  it("closes when the backdrop is clicked", async () => {
    const { drawer } = await openDrawer();

    fireEvent.click(document.querySelector(".sidebar-backdrop")!);

    expect(drawer).not.toHaveClass("sidebar--open");
  });

  it("keeps keyboard focus inside the open drawer", async () => {
    const { drawer } = await openDrawer();
    const close = within(drawer).getByRole("button", { name: "Close navigation" });
    const signOut = within(drawer).getByRole("button", { name: "Sign out" });

    signOut.focus();
    fireEvent.keyDown(signOut, { key: "Tab" });
    expect(close).toHaveFocus();

    fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
    expect(signOut).toHaveFocus();
  });

  it("switching matters and signing out work from the drawer", async () => {
    backend.matters = [
      { id: "m-dpa", name: "DPA", role: "viewer" },
      { id: "m-msa", name: "MSA", role: "admin" },
    ];
    const { drawer } = await openDrawer();

    fireEvent.change(within(drawer).getByRole("combobox", { name: "Matter" }), {
      target: { value: "m-dpa" },
    });
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-dpa");
    expect(await screen.findByText(/viewer · ada@firm\.example/)).toBeInTheDocument();

    fireEvent.click(within(drawer).getByRole("button", { name: "Sign out" }));
    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
  });
});

describe("malformed links (ui:27)", () => {
  it("a malformed percent-escape in the hash route does not blank the app", async () => {
    renderApp({ hash: "#/assertions/%E0%A4%A" });

    expect(await primaryNav()).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /review queue/i })).toBeInTheDocument();
  });
});
