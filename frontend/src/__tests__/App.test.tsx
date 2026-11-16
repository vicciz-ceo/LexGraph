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
// - review identity:0: a background re-check keeps the matter this tab shows
//   (another tab's choice is only where new tabs start), so a Suggest draft,
//   the admin console's add-member target and a one-time token survive it.
// - review identity:1: a sign-out or a refused token in another tab signs
//   this tab out with a message, instead of leaving it broken.
// - review identity:2: rotating your own token survives leaving the admin
//   page, and the new token is still shown once.
// - review identity:4: accounts whose id contains "/" are managed in-app.

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { reportAuthFailure } from "../api/authEvents";
import { SessionProvider, useSession } from "../app/session";

const TOKEN_KEY = "lexgraph.token";
const MATTER_KEY = "lexgraph.matter";

type Role = "viewer" | "contributor" | "reviewer" | "admin";

interface Matter {
  id: string;
  name: string;
  role: Role;
}

interface Person {
  id: string;
  email: string;
  display_name: string;
}

interface Member {
  user: Person;
  role: Role;
}

interface Account extends Person {
  sign_in_status: "active" | "legacy" | "none";
}

interface Reply {
  status: number;
  body?: unknown;
}

const ADA = { id: "u-ada", email: "ada@firm.example", display_name: "Ada Admin" };
const RIVA = { id: "u-riva", email: "riva@firm.example", display_name: "Riva Reviewer" };
/** An account created before ids were restricted (api:24), upgraded as legacy. */
const LEAD = { id: "team/lead", email: "lead@firm.example", display_name: "Team Lead" };

/** The signed-in user is always Ada; tests change what the server says about her. */
class FakeBackend {
  /** Every request fails without a response (server down / offline). */
  down = false;
  /** Force GET /me to answer this status. */
  meStatus: number | null = null;
  /** Member writes answer 403 (Ada lost the admin role elsewhere). */
  forbidMemberWrites = false;
  /** The sign-in tokens the server accepts; every one is Ada's. */
  tokens = new Set(["tok-ada"]);
  /** Hold the answers to POST /users/{id}/sign-in-token until released. As on
   * the real server, the rotation itself has taken effect by then. */
  holdRotations = false;
  matters: Matter[] = [{ id: "m-msa", name: "MSA", role: "admin" }];
  members: Record<string, Member[]> = {
    "m-msa": [
      { user: ADA, role: "admin" },
      { user: RIVA, role: "admin" },
    ],
  };
  accounts: Account[] = [
    { ...ADA, sign_in_status: "active" },
    { ...RIVA, sign_in_status: "active" },
  ];
  /** `path` as sent (still percent-encoded); routing uses it decoded, like the server. */
  calls: { method: string; path: string; auth?: string }[] = [];
  private held: (() => void)[] = [];
  private issued = 0;

  handle(
    method: string,
    path: string,
    body: Record<string, unknown> | undefined,
    auth: string | undefined,
  ): Reply | Promise<Reply> {
    if (this.down) throw new TypeError("Failed to fetch");
    const token = auth?.startsWith("Bearer ") ? auth.slice("Bearer ".length) : null;
    if (token === null) {
      return { status: 401, body: { detail: "missing or malformed Authorization header" } };
    }
    if (path === "/me" && this.meStatus !== null) {
      return { status: this.meStatus, body: { detail: "x" } };
    }
    if (!this.tokens.has(token)) return { status: 401, body: { detail: "unknown sign-in token" } };
    if (path === "/me") {
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
    if (path === "/users" && method === "GET") return { status: 200, body: this.accounts };
    if (path === "/users" && method === "POST") {
      const account: Account = {
        id: `u-${body!.email as string}`,
        email: body!.email as string,
        display_name: body!.display_name as string,
        sign_in_status: "active",
      };
      this.accounts.push(account);
      return { status: 201, body: { ...account, sign_in_token: `tok-created-${++this.issued}` } };
    }
    const rotation = path.match(/^\/users\/(.+)\/sign-in-token$/);
    if (rotation && method === "POST") {
      const account = this.accounts.find((a) => a.id === rotation[1]);
      if (!account) return { status: 404, body: { detail: "user not found" } };
      const fresh = `tok-new-${++this.issued}`;
      account.sign_in_status = "active";
      if (account.id === ADA.id) this.tokens = new Set([fresh]);
      const reply = { status: 200, body: { ...account, sign_in_token: fresh } };
      if (!this.holdRotations) return reply;
      return new Promise((resolve) => this.held.push(() => resolve(reply)));
    }

    const roster = path.match(/^\/matters\/([^/]+)\/members$/);
    if (roster && method === "GET") {
      if (!this.matters.some((m) => m.id === roster[1])) {
        return { status: 403, body: { detail: "no access to matter" } };
      }
      return { status: 200, body: this.members[roster[1]] ?? [] };
    }
    if (roster && method === "POST") {
      const account = this.accounts.find((a) => a.email === body!.email);
      if (!account) return { status: 404, body: { detail: "no user account with that email" } };
      const row: Member = {
        user: { id: account.id, email: account.email, display_name: account.display_name },
        role: body!.role as Role,
      };
      this.members[roster[1]] = [...(this.members[roster[1]] ?? []), row];
      return { status: 201, body: row };
    }
    // The member id may contain "/" (the server's `path` converter).
    const member = path.match(/^\/matters\/([^/]+)\/members\/(.+)$/);
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

  releaseRotations() {
    const held = this.held;
    this.held = [];
    for (const release of held) release();
  }

  count(path: string): number {
    return this.calls.filter((c) => c.path === path).length;
  }

  lastMeAuth(): string | undefined {
    const reads = this.calls.filter((c) => c.path === "/me");
    return reads[reads.length - 1]?.auth;
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
      const reply = await backend.handle(
        method,
        decodeURIComponent(path),
        init.body ? JSON.parse(String(init.body)) : undefined,
        headers.Authorization,
      );
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
    expect(screen.queryByText(/demo seed/i)).not.toBeInTheDocument();
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

// --- Several tabs of one browser --------------------------------------------
//
// Tabs share localStorage: the saved token and the matter a new tab opens on.
// "Another tab" here is what it leaves in localStorage, plus the `storage`
// event the browser sends this tab about it (jsdom sends none itself), or a
// second SessionProvider standing in for that tab.

/** A second tab of the same browser: its own SessionProvider, the same localStorage. */
function OtherTab() {
  const { session, signOut, refresh } = useSession();
  return (
    <section aria-label="Other tab">
      <span data-testid="other-tab-state">
        {session === undefined ? "restoring" : session === null ? "signed-out" : "signed-in"}
      </span>
      <button type="button" onClick={signOut}>
        Other tab: sign out
      </button>
      <button type="button" onClick={() => void refresh().catch(() => {})}>
        Other tab: re-check
      </button>
    </section>
  );
}

function renderAppWithOtherTab(options: Parameters<typeof renderApp>[0] = {}) {
  const { hash = "#/review", token = "tok-ada", matter = "m-msa" } = options;
  window.localStorage.clear();
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  if (matter) window.localStorage.setItem(MATTER_KEY, matter);
  window.location.hash = hash;
  return render(
    <>
      <App />
      <SessionProvider>
        <OtherTab />
      </SessionProvider>
    </>,
  );
}

/** The `storage` event the browser sends this tab when another tab changed a key. */
function storageEventFromAnotherTab(key = TOKEN_KEY) {
  act(() => {
    window.dispatchEvent(
      new StorageEvent("storage", {
        key,
        newValue: window.localStorage.getItem(key),
        storageArea: window.localStorage,
      }),
    );
  });
}

/** Let every answer already on its way reach the app. */
async function settle() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

const matterSelect = () => screen.getByRole("combobox", { name: "Matter" });

describe("each tab keeps its own matter (review identity:0)", () => {
  const TWO_MATTERS: Matter[] = [
    { id: "m-dpa", name: "DPA", role: "admin" },
    { id: "m-msa", name: "MSA", role: "admin" },
  ];

  async function suggestDraft() {
    backend.matters = TWO_MATTERS;
    renderApp({ hash: "#/suggest", matter: "m-msa" });
    const proposition = await screen.findByLabelText("Proposition");
    fireEvent.change(proposition, { target: { value: "Clause 9 survives termination." } });
    // Another tab of this browser switches to DPA, and Ada is made a
    // reviewer on MSA meanwhile (so the re-read below visibly lands).
    window.localStorage.setItem(MATTER_KEY, "m-dpa");
    backend.matters = [
      { id: "m-dpa", name: "DPA", role: "admin" },
      { id: "m-msa", name: "MSA", role: "reviewer" },
    ];
  }

  async function draftSurvived() {
    expect(await screen.findByText(/reviewer · ada@firm\.example/)).toBeInTheDocument();
    expect(matterSelect()).toHaveValue("m-msa");
    expect(screen.getByLabelText("Proposition")).toHaveValue("Clause 9 survives termination.");
    // The other tab's choice is still where a new tab starts.
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-dpa");
  }

  it("returning to the tab keeps its matter and the Suggest draft", async () => {
    await suggestDraft();

    refocusLater();

    await draftSurvived();
  });

  it("the once-a-minute re-check keeps them too", async () => {
    const setIntervalSpy = vi.spyOn(window, "setInterval");
    await suggestDraft();

    clockOffset += 61_000;
    act(() => {
      for (const [callback, delay] of setIntervalSpy.mock.calls) {
        if (delay === 60_000) (callback as () => void)();
      }
    });

    await draftSurvived();
  });

  it("the re-check after a refused request keeps them too", async () => {
    await suggestDraft();

    act(() => {
      // What the api client reports for any 401/403 answer.
      reportAuthFailure({ status: 403, method: "GET", path: "/matters/m-msa/source-spans" });
    });

    await draftSurvived();
  });

  it("Add member still grants the role on the matter this tab shows", async () => {
    backend.matters = TWO_MATTERS;
    backend.members["m-dpa"] = [{ user: ADA, role: "admin" }];
    renderApp({ hash: "#/admin", matter: "m-msa" });
    await screen.findByText("Riva Reviewer");
    fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
    await screen.findByRole("button", { name: "Rotate sign-in token for Riva Reviewer" });
    fireEvent.change(screen.getByLabelText(/email for the new account/i), {
      target: { value: "newbie@firm.example" },
    });
    fireEvent.change(screen.getByLabelText(/display name for the new account/i), {
      target: { value: "Newbie" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await screen.findByRole("status", { name: "New sign-in token" });
    fireEvent.click(screen.getByRole("tab", { name: "Members & roles" }));
    fireEvent.change(screen.getByLabelText("Role for the new member"), { target: { value: "admin" } });
    expect(screen.getByLabelText("Email of the account to add")).toHaveValue("newbie@firm.example");

    window.localStorage.setItem(MATTER_KEY, "m-dpa"); // another tab chose DPA
    refocusLater();
    await waitFor(() => expect(backend.count("/me")).toBe(2));
    await settle();
    expect(matterSelect()).toHaveValue("m-msa");
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() =>
      expect(backend.members["m-msa"].map((m) => [m.user.email, m.role])).toContainEqual([
        "newbie@firm.example",
        "admin",
      ]),
    );
    expect(backend.members["m-dpa"].some((m) => m.user.email === "newbie@firm.example")).toBe(false);
  });

  it("a token shown once stays on screen", async () => {
    backend.matters = [
      { id: "m-dpa", name: "DPA", role: "viewer" },
      { id: "m-msa", name: "MSA", role: "admin" },
    ];
    renderApp({ hash: "#/admin", matter: "m-msa" });
    await screen.findByText("Riva Reviewer");
    fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Rotate sign-in token for Riva Reviewer" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm new sign-in token for Riva Reviewer" }));
    const callout = await screen.findByRole("status", { name: "New sign-in token" });
    expect(callout).toHaveTextContent("tok-new-1");

    window.localStorage.setItem(MATTER_KEY, "m-dpa"); // where Ada is only a viewer
    refocusLater();
    await waitFor(() => expect(backend.count("/me")).toBe(2));
    await settle();

    expect(screen.getByRole("status", { name: "New sign-in token" })).toHaveTextContent("tok-new-1");
    expect(screen.queryByText("Not authorized")).not.toBeInTheDocument();
  });

  it("choosing another matter in this tab still switches it, and is where new tabs start", async () => {
    backend.matters = TWO_MATTERS;
    renderApp({ hash: "#/review", matter: "m-msa" });
    await primaryNav();

    fireEvent.change(matterSelect(), { target: { value: "m-dpa" } });

    expect(matterSelect()).toHaveValue("m-dpa");
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-dpa");
  });
});

describe("signing out in another tab (review identity:1)", () => {
  it("a sign-out there shows the sign-in page here, saying so", async () => {
    renderAppWithOtherTab();
    await primaryNav();
    await waitFor(() => expect(screen.getByTestId("other-tab-state")).toHaveTextContent("signed-in"));

    fireEvent.click(screen.getByRole("button", { name: "Other tab: sign out" }));
    storageEventFromAnotherTab();

    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/signed out in another tab/i);
    expect(screen.queryByRole("navigation", { name: "Primary" })).not.toBeInTheDocument();
    // Nothing went out without a token.
    expect(backend.calls.filter((c) => !c.auth)).toEqual([]);
  });

  it("a token refused there shows the sign-in page here with the rotation notice", async () => {
    renderAppWithOtherTab();
    await primaryNav();
    await waitFor(() => expect(screen.getByTestId("other-tab-state")).toHaveTextContent("signed-in"));

    backend.tokens.clear(); // an admin rotated Ada's token
    fireEvent.click(screen.getByRole("button", { name: "Other tab: re-check" }));
    await waitFor(
      () => expect(screen.getByTestId("other-tab-state")).toHaveTextContent("signed-out"),
      { timeout: 3_000 },
    );
    storageEventFromAnotherTab();

    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/no longer valid/i);
  });

  it("a request sent without the token another tab removed signs this tab out", async () => {
    renderApp({ hash: "#/review" });
    await primaryNav();

    window.localStorage.removeItem(TOKEN_KEY); // signed out elsewhere; the event was missed
    act(() => {
      window.location.hash = "#/knowledge";
    });

    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/signed out in another tab/i);
    expect(backend.count("/me")).toBe(1);
  });

  it("coming back to a tab whose token another tab removed signs it out", async () => {
    renderApp();
    await primaryNav();

    window.localStorage.removeItem(TOKEN_KEY);
    refocusLater();

    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/signed out in another tab/i);
  });

  it("when both tabs see the token refused, both sign out", async () => {
    renderAppWithOtherTab();
    await primaryNav();
    await waitFor(() => expect(screen.getByTestId("other-tab-state")).toHaveTextContent("signed-in"));

    backend.tokens.clear();
    refocusLater();

    expect(await screen.findByLabelText(/sign-in token/i, {}, { timeout: 4_000 })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/no longer valid/i);
    await waitFor(() => expect(screen.getByTestId("other-tab-state")).toHaveTextContent("signed-out"));
  });

  it("a token another tab stored (a rotation there) is checked here at once and kept", async () => {
    renderApp();
    await primaryNav();

    backend.tokens = new Set(["tok-ada-2"]);
    window.localStorage.setItem(TOKEN_KEY, "tok-ada-2");
    storageEventFromAnotherTab();

    await waitFor(() => expect(backend.lastMeAuth()).toBe("Bearer tok-ada-2"));
    await settle();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  });

  it("a sign-in in another tab carries over once its token works", async () => {
    renderApp({ token: "" });
    expect(await screen.findByLabelText(/sign-in token/i)).toBeInTheDocument();

    window.localStorage.setItem(TOKEN_KEY, "tok-typo"); // still being checked over there
    storageEventFromAnotherTab();
    await waitFor(() => expect(backend.lastMeAuth()).toBe("Bearer tok-typo"));
    await settle();
    expect(screen.getByLabelText(/sign-in token/i)).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-typo");

    window.localStorage.setItem(TOKEN_KEY, "tok-ada");
    storageEventFromAnotherTab();
    expect(await primaryNav()).toBeInTheDocument();
  });
});

describe("rotating your own token (review identity:2)", () => {
  async function startOwnRotation() {
    backend.holdRotations = true;
    renderApp({ hash: "#/admin" });
    await screen.findByText("Riva Reviewer");
    fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Rotate sign-in token for Ada Admin" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm new sign-in token for Ada Admin" }));
    await waitFor(() => expect(backend.count("/users/u-ada/sign-in-token")).toBe(1));
  }

  async function newTokenShownOnce() {
    const callout = await screen.findByRole("status", { name: "New sign-in token" });
    expect(callout).toHaveTextContent("tok-new-1");
    expect(callout).toHaveTextContent(/shown only once/i);
    expect(callout).toHaveTextContent(/this browser now signs in with the new token/i);
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1");
    return callout;
  }

  it("leaving the admin page before the answer still switches to the new token and shows it", async () => {
    await startOwnRotation();

    act(() => {
      window.location.hash = "#/review";
    });
    expect(await screen.findByRole("heading", { name: /review queue/i })).toBeInTheDocument();
    await act(async () => {
      backend.releaseRotations();
    });

    const callout = await newTokenShownOnce();
    refocusLater();
    await waitFor(() => expect(backend.lastMeAuth()).toBe("Bearer tok-new-1"));
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();

    fireEvent.click(within(callout).getByRole("button", { name: /done, i have saved the token/i }));
    expect(document.body).not.toHaveTextContent("tok-new-1");
  });

  it("the old token's 401 while the answer is on its way does not sign you out", async () => {
    await startOwnRotation();

    refocusLater(); // the server already refuses the old token
    await waitFor(() => expect(backend.count("/me")).toBe(2));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 1_300)); // past the 1 s confirmation
    });
    // Still signed in: no sign-in page (its field is labelled exactly so).
    expect(screen.queryByLabelText("Sign-in token")).not.toBeInTheDocument();

    await act(async () => {
      backend.releaseRotations();
    });

    await newTokenShownOnce();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.queryByText(/no longer valid/i)).not.toBeInTheDocument();
  });
});

describe("accounts whose id contains '/' (review identity:4)", () => {
  it("can be re-roled, rotated and removed from the admin console", async () => {
    backend.members["m-msa"].push({ user: LEAD, role: "reviewer" });
    backend.accounts.push({ ...LEAD, sign_in_status: "legacy" });
    renderApp({ hash: "#/admin" });
    await screen.findByText("Team Lead");

    fireEvent.change(screen.getByLabelText("Role for Team Lead"), { target: { value: "viewer" } });
    await waitFor(() => expect(backend.members["m-msa"].find((m) => m.user.id === LEAD.id)?.role).toBe("viewer"));

    fireEvent.click(screen.getByRole("tab", { name: "User accounts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Rotate sign-in token for Team Lead" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm new sign-in token for Team Lead" }));
    expect(await screen.findByRole("status", { name: "New sign-in token" })).toHaveTextContent(
      "Sign-in token for Team Lead",
    );

    fireEvent.click(screen.getByRole("tab", { name: "Members & roles" }));
    fireEvent.click(await screen.findByRole("button", { name: "Remove Team Lead" }));
    await waitFor(() => expect(screen.queryByText("Team Lead")).not.toBeInTheDocument());

    // Each id went out as one percent-encoded path segment.
    const writes = backend.calls.filter((c) => c.method !== "GET").map((c) => `${c.method} ${c.path}`);
    expect(writes).toEqual([
      "PUT /matters/m-msa/members/team%2Flead",
      "POST /users/team%2Flead/sign-in-token",
      "DELETE /matters/m-msa/members/team%2Flead",
    ]);
  });
});
