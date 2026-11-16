// Several tabs of one browser: SessionProviders that share one localStorage
// (jsdom's real one), each with the REAL api client; only fetch is stubbed,
// by a small server that knows which sign-in tokens it accepts.
//
// A browser tells the OTHER tabs about a localStorage change with a
// `storage` event. jsdom fires none between components of one document, so
// `deliverStorageEvent()` dispatches it where a browser would; every
// provider here receives it, and the one that made the change must ignore it.
//
// - review identity:0 / fe-shell-authoring:0: a background re-read of
//   GET /me keeps the matter THIS tab shows (with its fresh role). The
//   shared `lexgraph.matter` key only says where a new tab, a reload or a
//   sign-in starts, and a re-check that keeps its matter never writes it.
// - review identity:1 / fe-shell-authoring:3: signing out, or a token the
//   server refused, in one tab signs the other tabs out with a message; a
//   token another tab stored is re-read with GET /me.
// - review identity:2: rotating your own token runs in the session, so the
//   new token is adopted (and kept to be shown once) whatever page is open,
//   and the old token's 401s meanwhile do not sign you out. A sign-out, in
//   this tab or another, before the answer or before Done keeps the browser
//   signed out, but the tab that asked still shows the token until Done
//   (never in another account's session).

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { reportAuthFailure } from "../../api/authEvents";
import { SessionProvider, useSession } from "../session";

const TOKEN_KEY = "lexgraph.token";
const MATTER_KEY = "lexgraph.matter";

const USER = { id: "u-1", email: "u1@firm.example", display_name: "User One" };
const OTHER_USER = { id: "u-2", email: "u2@firm.example", display_name: "User Two" };

function membership(id: string, role: string) {
  return { id, name: `Matter ${id}`, repository_id: "r-1", organization_id: "o-1", role };
}

interface Reply {
  status: number;
  body?: unknown;
}

/** Accepts the tokens it issued; rotation commits before it answers. */
class Server {
  tokens = new Map<string, typeof USER>([["tok", USER]]);
  matters = [membership("m-a", "admin"), membership("m-b", "viewer")];
  /** Hold the answers to POST /users/{id}/sign-in-token until released. */
  holdRotations = false;
  rotationStatus = 200;
  issued = 0;
  calls: { method: string; path: string; auth?: string }[] = [];
  private held: (() => void)[] = [];

  async handle(method: string, path: string, auth: string | undefined): Promise<Reply> {
    const token = auth?.replace(/^Bearer /, "");
    if (!token) return { status: 401, body: { detail: "missing or malformed Authorization header" } };
    const user = this.tokens.get(token);
    if (!user) return { status: 401, body: { detail: "unknown sign-in token" } };
    if (method === "GET" && path === "/me") {
      return { status: 200, body: { user, matters: this.matters } };
    }
    if (method === "POST" && /^\/users\/.+\/sign-in-token$/.test(path)) {
      if (this.rotationStatus !== 200) {
        return { status: this.rotationStatus, body: { detail: "rotation refused" } };
      }
      const fresh = `tok-new-${++this.issued}`;
      for (const [known, owner] of [...this.tokens]) {
        if (owner.id === user.id) this.tokens.delete(known);
      }
      this.tokens.set(fresh, user);
      const reply = {
        status: 200,
        body: { ...user, sign_in_status: "active", sign_in_token: fresh },
      };
      if (!this.holdRotations) return reply;
      return new Promise((resolve) => this.held.push(() => resolve(reply)));
    }
    return { status: 404, body: { detail: "Not Found" } };
  }

  releaseRotations() {
    const held = this.held;
    this.held = [];
    for (const release of held) release();
  }

  count(method: string, path: string): number {
    return this.calls.filter((c) => c.method === method && c.path === path).length;
  }

  meAuths(): (string | undefined)[] {
    return this.calls.filter((c) => c.path === "/me").map((c) => c.auth);
  }
}

let server: Server;
let clockOffset = 0;

beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem(TOKEN_KEY, "tok");
  window.localStorage.setItem(MATTER_KEY, "m-a");
  server = new Server();
  clockOffset = 0;
  const realNow = Date.now.bind(Date);
  vi.spyOn(Date, "now").mockImplementation(() => realNow() + clockOffset);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init: RequestInit = {}) => {
      const url = new URL(input);
      const method = init.method ?? "GET";
      const path = decodeURIComponent(url.pathname.replace(/^\/api\/v1/, ""));
      const auth = (init.headers as Record<string, string> | undefined)?.Authorization;
      server.calls.push({ method, path, auth });
      const reply = await server.handle(method, path, auth);
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

function Tab({ name }: { name: string }) {
  const value = useSession();
  const { session, notice } = value;
  return (
    <section aria-label={name}>
      <span data-testid="state">
        {session === undefined ? "restoring" : session === null ? "signed-out" : "signed-in"}
      </span>
      <span data-testid="user">{session?.user.id ?? ""}</span>
      <span data-testid="matter">{session?.currentMatter?.id ?? ""}</span>
      <span data-testid="role">{session?.role ?? ""}</span>
      <span data-testid="notice">{notice?.kind ?? ""}</span>
      <span data-testid="notice-text">{notice?.message ?? ""}</span>
      <span data-testid="issued">{value.issuedOwnToken?.sign_in_token ?? ""}</span>
      <button type="button" onClick={() => value.selectMatter("m-b")}>
        pick B
      </button>
      <button type="button" onClick={value.signOut}>
        sign out
      </button>
      <button type="button" onClick={() => void value.refresh().catch(() => {})}>
        re-check
      </button>
      <button type="button" onClick={() => void value.signIn("tok").catch(() => {})}>
        sign in
      </button>
      <button type="button" onClick={() => void value.rotateOwnToken?.().catch(() => {})}>
        rotate my token
      </button>
      <button type="button" onClick={() => value.acknowledgeIssuedOwnToken?.()}>
        done
      </button>
      <button
        type="button"
        onClick={() => void value.signIn(value.issuedOwnToken?.sign_in_token ?? "").catch(() => {})}
      >
        sign in with the new token
      </button>
    </section>
  );
}

function renderTabs(...names: string[]) {
  return render(
    <>
      {names.map((name) => (
        <SessionProvider key={name}>
          <Tab name={name} />
        </SessionProvider>
      ))}
    </>,
  );
}

const tab = (name: string) => within(screen.getByRole("region", { name }));
const field = (name: string, testId: string) => tab(name).getByTestId(testId).textContent;
const click = (name: string, button: string) =>
  fireEvent.click(tab(name).getByRole("button", { name: button }));

async function signedIn(...names: string[]) {
  for (const name of names) {
    await waitFor(() => expect(field(name, "state")).toBe("signed-in"));
  }
}

/** Let every pending answer reach the providers. */
async function settle() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

/** More than the re-check throttle later, the user comes back to the tab(s). */
function refocusLater() {
  clockOffset += 10_000;
  act(() => {
    window.dispatchEvent(new Event("focus"));
  });
}

/** The `storage` event a browser sends the other tabs of a changed key. */
function deliverStorageEvent(key: string | null = TOKEN_KEY) {
  act(() => {
    window.dispatchEvent(
      new StorageEvent("storage", {
        key,
        newValue: key === null ? null : window.localStorage.getItem(key),
        storageArea: window.localStorage,
      }),
    );
  });
}

async function pastTheConfirmation() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 1_300));
  });
}

describe("each tab keeps its own matter (review identity:0)", () => {
  it("a focus re-check keeps the matter each tab shows, and the other tab's choice for new tabs", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    expect(field("tab 1", "matter")).toBe("m-a");

    click("tab 2", "pick B");
    expect(field("tab 2", "matter")).toBe("m-b");
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-b");

    refocusLater();
    await waitFor(() => expect(server.count("GET", "/me")).toBe(4));
    await settle();

    expect(field("tab 1", "matter")).toBe("m-a");
    expect(field("tab 1", "role")).toBe("admin");
    expect(field("tab 2", "matter")).toBe("m-b");
    expect(field("tab 2", "role")).toBe("viewer");
    // Tab 1's re-check kept its matter without overwriting tab 2's choice.
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-b");
  });

  it("the once-a-minute re-check keeps it too", async () => {
    const setIntervalSpy = vi.spyOn(window, "setInterval");
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    click("tab 2", "pick B");

    clockOffset += 61_000;
    act(() => {
      for (const [callback, delay] of setIntervalSpy.mock.calls) {
        if (delay === 60_000) (callback as () => void)();
      }
    });
    await waitFor(() => expect(server.count("GET", "/me")).toBe(4));
    await settle();

    expect(field("tab 1", "matter")).toBe("m-a");
    expect(field("tab 2", "matter")).toBe("m-b");
  });

  it("a re-check after a refused request keeps it too", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    click("tab 2", "pick B");

    act(() => {
      reportAuthFailure({ status: 403, method: "GET", path: "/matters/m-a/members" });
    });
    await waitFor(() => expect(server.count("GET", "/me")).toBe(4));
    await settle();

    expect(field("tab 1", "matter")).toBe("m-a");
    expect(field("tab 2", "matter")).toBe("m-b");
  });

  it("a re-check applies the fresh role on the tab's own matter", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    click("tab 2", "pick B");

    server.matters = [membership("m-a", "reviewer"), membership("m-b", "contributor")];
    refocusLater();

    await waitFor(() => expect(field("tab 1", "role")).toBe("reviewer"));
    expect(field("tab 1", "matter")).toBe("m-a");
    await waitFor(() => expect(field("tab 2", "role")).toBe("contributor"));
    expect(field("tab 2", "matter")).toBe("m-b");
  });

  it("a tab whose matter is gone moves to the saved choice, else the first matter, and saves it", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");
    // Another tab chose m-b, then this user lost m-a.
    window.localStorage.setItem(MATTER_KEY, "m-b");
    server.matters = [membership("m-b", "viewer"), membership("m-c", "admin")];
    refocusLater();
    await waitFor(() => expect(field("tab 1", "matter")).toBe("m-b"));
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-b");

    server.matters = [membership("m-c", "admin")];
    refocusLater();
    await waitFor(() => expect(field("tab 1", "matter")).toBe("m-c"));
    expect(field("tab 1", "role")).toBe("admin");
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-c");
  });

  it("a reload and a sign-in start from the saved matter", async () => {
    window.localStorage.setItem(MATTER_KEY, "m-b");
    renderTabs("tab 1");
    await signedIn("tab 1");
    expect(field("tab 1", "matter")).toBe("m-b");

    click("tab 1", "sign out");
    // Signing out forgets the matter: the next sign-in starts on the first one.
    click("tab 1", "sign in");
    await signedIn("tab 1");
    expect(field("tab 1", "matter")).toBe("m-a");
    expect(window.localStorage.getItem(MATTER_KEY)).toBe("m-a");
  });
});

describe("signing out and token changes reach the other tabs (review identity:1)", () => {
  it("signing out in one tab signs the others out at once, saying so, without a request", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    const requests = server.calls.length;

    click("tab 1", "sign out");
    deliverStorageEvent();

    expect(field("tab 2", "state")).toBe("signed-out");
    expect(field("tab 2", "notice")).toBe("signed_out_elsewhere");
    expect(field("tab 2", "notice-text")).toMatch(/signed out in another tab/i);
    // The tab that signed out shows no notice, and nobody sent a request.
    expect(field("tab 1", "state")).toBe("signed-out");
    expect(field("tab 1", "notice")).toBe("");
    expect(server.calls.length).toBe(requests);
  });

  it("a token the server refused in one tab signs the others out with the rotation notice", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");

    server.tokens.clear(); // an admin rotated this account's token elsewhere
    click("tab 1", "re-check");
    await waitFor(() => expect(field("tab 1", "state")).toBe("signed-out"), { timeout: 3_000 });
    expect(field("tab 1", "notice")).toBe("token_rejected");
    deliverStorageEvent();

    expect(field("tab 2", "state")).toBe("signed-out");
    expect(field("tab 2", "notice")).toBe("token_rejected");
    expect(field("tab 2", "notice-text")).toMatch(/no longer valid/i);
  });

  it("localStorage.clear() in another tab (a storage event without a key) signs out too", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");

    window.localStorage.clear();
    deliverStorageEvent(null);

    expect(field("tab 1", "state")).toBe("signed-out");
    expect(field("tab 1", "notice")).toBe("signed_out_elsewhere");
  });

  it("when both tabs notice the refused token, both sign out with the notice", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");

    server.tokens.clear();
    refocusLater(); // both re-check, both get 401, both confirm

    await waitFor(
      () => {
        expect(field("tab 1", "state")).toBe("signed-out");
        expect(field("tab 2", "state")).toBe("signed-out");
      },
      { timeout: 3_000 },
    );
    expect(field("tab 1", "notice")).toBe("token_rejected");
    expect(field("tab 2", "notice")).toBe("token_rejected");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("without the storage event, a request refused for want of a token signs the tab out", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");

    window.localStorage.removeItem(TOKEN_KEY); // another tab signed out; the event was missed
    act(() => {
      reportAuthFailure({ status: 401, method: "GET", path: "/assertions" });
    });

    await waitFor(() => expect(field("tab 1", "state")).toBe("signed-out"));
    expect(field("tab 1", "notice")).toBe("signed_out_elsewhere");
    expect(server.count("GET", "/me")).toBe(1); // nothing to re-read with
  });

  it("without the storage event, coming back to the tab signs it out too", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");

    window.localStorage.removeItem(TOKEN_KEY);
    refocusLater();

    await waitFor(() => expect(field("tab 1", "state")).toBe("signed-out"));
    expect(field("tab 1", "notice")).toBe("signed_out_elsewhere");
  });

  it("a token another tab stored (your own rotation there) is re-read, and the session kept", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");

    server.tokens = new Map([["tok-rotated", USER]]);
    window.localStorage.setItem(TOKEN_KEY, "tok-rotated");
    deliverStorageEvent();

    await waitFor(() => expect(server.meAuths()).toContain("Bearer tok-rotated"));
    await settle();
    expect(field("tab 1", "state")).toBe("signed-in");
    expect(field("tab 1", "notice")).toBe("");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-rotated");
  });

  it("a tab signed in as someone else in another tab follows, starting from the saved matter", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");

    server.tokens.set("tok-two", OTHER_USER);
    server.matters = [membership("m-a", "viewer"), membership("m-b", "admin")];
    window.localStorage.setItem(MATTER_KEY, "m-b");
    window.localStorage.setItem(TOKEN_KEY, "tok-two");
    deliverStorageEvent();

    await waitFor(() => expect(field("tab 1", "user")).toBe("u-2"));
    expect(field("tab 1", "matter")).toBe("m-b");
    expect(field("tab 1", "role")).toBe("admin");
  });

  it("a signed-out tab follows a sign-in made in another tab once that token works", async () => {
    window.localStorage.removeItem(TOKEN_KEY);
    renderTabs("tab 1");
    await waitFor(() => expect(field("tab 1", "state")).toBe("signed-out"));

    // The other tab's sign-in form stores what was typed before checking it.
    window.localStorage.setItem(TOKEN_KEY, "tok-typo");
    deliverStorageEvent();
    await waitFor(() => expect(server.meAuths()).toContain("Bearer tok-typo"));
    await settle();
    // Not followed, not flagged, and not removed from under the other tab.
    expect(field("tab 1", "state")).toBe("signed-out");
    expect(field("tab 1", "notice")).toBe("");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-typo");

    window.localStorage.setItem(TOKEN_KEY, "tok");
    deliverStorageEvent();
    await signedIn("tab 1");
    expect(field("tab 1", "matter")).toBe("m-a");
  });

  it("the tab that changed the token ignores the event about its own change", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");
    const requests = server.calls.length;

    deliverStorageEvent(); // nothing changed for this tab
    deliverStorageEvent(MATTER_KEY); // another tab's matter choice is not this tab's

    await settle();
    expect(field("tab 1", "state")).toBe("signed-in");
    expect(server.calls.length).toBe(requests);
  });
});

describe("rotating your own token (review identity:2)", () => {
  async function rotationStarted(name = "tab 1") {
    click(name, "rotate my token");
    await waitFor(() => expect(server.count("POST", "/users/u-1/sign-in-token")).toBe(1));
  }

  it("adopts the new token as soon as the server answers and keeps it to be shown once", async () => {
    server.holdRotations = true;
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();

    await act(async () => {
      server.releaseRotations();
    });

    await waitFor(() => expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1"));
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    expect(field("tab 1", "state")).toBe("signed-in");
    await waitFor(() => expect(server.meAuths().slice(-1)).toEqual(["Bearer tok-new-1"]));

    click("tab 1", "done");
    expect(field("tab 1", "issued")).toBe("");
    expect(field("tab 1", "state")).toBe("signed-in");
  });

  it("a 401 for the old token while the answer is on its way does not sign out", async () => {
    server.holdRotations = true;
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();

    refocusLater(); // the server already refuses the old token
    await waitFor(() => expect(server.count("GET", "/me")).toBe(2));
    await pastTheConfirmation();
    expect(field("tab 1", "state")).toBe("signed-in");

    await act(async () => {
      server.releaseRotations();
    });
    await waitFor(() => expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1"));
    await pastTheConfirmation();
    expect(field("tab 1", "state")).toBe("signed-in");
    expect(field("tab 1", "notice")).toBe("");
    expect(field("tab 1", "issued")).toBe("tok-new-1");
  });

  it("another tab refusing the old token meanwhile does not sign this one out; both end on the new token", async () => {
    server.holdRotations = true;
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    await rotationStarted("tab 1");

    click("tab 2", "re-check"); // 401, confirmed a second later: tab 2 signs out
    await waitFor(() => expect(field("tab 2", "state")).toBe("signed-out"), { timeout: 3_000 });
    deliverStorageEvent();
    expect(field("tab 1", "state")).toBe("signed-in");

    await act(async () => {
      server.releaseRotations();
    });
    await waitFor(() => expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1"));
    deliverStorageEvent();

    await signedIn("tab 2");
    expect(field("tab 1", "state")).toBe("signed-in");
    // Shown once, in the tab that asked for it.
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    expect(field("tab 2", "issued")).toBe("");
  });

  // The server has replaced the token before it answers: from then on the new
  // token is the account's only credential. A sign-out meanwhile keeps the
  // browser signed out (the token is not saved), but the token is still shown,
  // in the tab that asked for it, until Done: losing it would lock the user
  // out (a sole admin could only recover with the operator CLI).
  it("signing out while the answer is on its way stays signed out, and the new token is still shown", async () => {
    server.holdRotations = true;
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();

    click("tab 1", "sign out");
    await act(async () => {
      server.releaseRotations();
    });
    await settle();

    expect(field("tab 1", "state")).toBe("signed-out");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    expect(server.tokens.has("tok-new-1")).toBe(true);

    click("tab 1", "done");
    expect(field("tab 1", "issued")).toBe("");
    expect(field("tab 1", "state")).toBe("signed-out");
  });

  it("an explicit sign-out in another tab while the answer is on its way: every tab stays signed out, and the tab that asked shows the new token", async () => {
    server.holdRotations = true;
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    await rotationStarted("tab 1");

    click("tab 2", "sign out");
    deliverStorageEvent();
    expect(field("tab 1", "state")).toBe("signed-out");
    expect(field("tab 1", "notice")).toBe("signed_out_elsewhere");

    await act(async () => {
      server.releaseRotations();
    });
    await settle();
    deliverStorageEvent(); // nothing changed: no tab signs back in
    await settle();

    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(field("tab 1", "state")).toBe("signed-out");
    expect(field("tab 2", "state")).toBe("signed-out");
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    expect(field("tab 2", "issued")).toBe("");

    // Signing in with it works, and it stays on screen until Done.
    click("tab 1", "sign in with the new token");
    await signedIn("tab 1");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1");
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    deliverStorageEvent();
    await signedIn("tab 2");
    expect(field("tab 2", "issued")).toBe("");
    click("tab 1", "done");
    expect(field("tab 1", "issued")).toBe("");
  });

  it("a new token already shown is still shown after a sign-out in another tab, until Done", async () => {
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    await rotationStarted("tab 1");
    await waitFor(() => expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1"));
    deliverStorageEvent();
    await waitFor(() => expect(server.meAuths()).toContain("Bearer tok-new-1"));
    await settle();

    click("tab 2", "sign out"); // the user may not even have looked at tab 1 yet
    deliverStorageEvent();

    expect(field("tab 1", "state")).toBe("signed-out");
    expect(field("tab 2", "state")).toBe("signed-out");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    click("tab 1", "done");
    expect(field("tab 1", "issued")).toBe("");
  });

  it("another account signed in here meanwhile: the token is neither saved nor shown", async () => {
    server.holdRotations = true;
    server.tokens.set("tok-two", OTHER_USER);
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    await rotationStarted("tab 1");

    click("tab 2", "sign out");
    deliverStorageEvent();
    window.localStorage.setItem(TOKEN_KEY, "tok-two"); // tab 2 signs in as User Two
    deliverStorageEvent();
    await waitFor(() => expect(field("tab 1", "user")).toBe("u-2"));

    await act(async () => {
      server.releaseRotations();
    });
    await settle();

    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-two");
    expect(field("tab 1", "user")).toBe("u-2");
    expect(field("tab 1", "issued")).toBe("");
  });

  it("another account signed in and out again meanwhile: the answer is not shown on the sign-in page either", async () => {
    server.holdRotations = true;
    server.tokens.set("tok-two", OTHER_USER);
    renderTabs("tab 1", "tab 2");
    await signedIn("tab 1", "tab 2");
    await rotationStarted("tab 1");

    click("tab 2", "sign out");
    deliverStorageEvent();
    window.localStorage.setItem(TOKEN_KEY, "tok-two"); // User Two signs in in tab 2...
    deliverStorageEvent();
    await waitFor(() => expect(field("tab 1", "user")).toBe("u-2"));
    window.localStorage.removeItem(TOKEN_KEY); // ...and signs out again
    deliverStorageEvent();
    expect(field("tab 1", "state")).toBe("signed-out");

    await act(async () => {
      server.releaseRotations();
    });
    await settle();

    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(field("tab 1", "issued")).toBe("");
  });

  it("a new token shown while signed out is forgotten when another account signs in", async () => {
    server.holdRotations = true;
    server.tokens.set("tok-two", OTHER_USER);
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();
    click("tab 1", "sign out");
    await act(async () => {
      server.releaseRotations();
    });
    await settle();
    expect(field("tab 1", "issued")).toBe("tok-new-1");

    window.localStorage.setItem(TOKEN_KEY, "tok-two"); // User Two signs in in another tab
    deliverStorageEvent();

    await waitFor(() => expect(field("tab 1", "user")).toBe("u-2"));
    expect(field("tab 1", "issued")).toBe("");
  });

  it("a shown token the server then refuses (rotated again elsewhere) is no longer shown", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();
    await waitFor(() => expect(field("tab 1", "issued")).toBe("tok-new-1"));
    await settle();

    server.tokens = new Map([["tok-by-another-admin", USER]]);
    click("tab 1", "re-check");

    await waitFor(() => expect(field("tab 1", "state")).toBe("signed-out"), { timeout: 3_000 });
    expect(field("tab 1", "notice")).toBe("token_rejected");
    expect(field("tab 1", "issued")).toBe("");
  });

  it("signing out in this tab after the new token was shown keeps showing it until Done", async () => {
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();
    await waitFor(() => expect(field("tab 1", "issued")).toBe("tok-new-1"));

    click("tab 1", "sign out");

    expect(field("tab 1", "state")).toBe("signed-out");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(field("tab 1", "issued")).toBe("tok-new-1");
    click("tab 1", "done");
    expect(field("tab 1", "issued")).toBe("");
  });

  it("a refused rotation changes nothing", async () => {
    server.rotationStatus = 403;
    renderTabs("tab 1");
    await signedIn("tab 1");

    await rotationStarted();
    await settle();

    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok");
    expect(field("tab 1", "issued")).toBe("");
    expect(field("tab 1", "state")).toBe("signed-in");
  });

  it("asking again while a rotation is on its way does not rotate twice", async () => {
    server.holdRotations = true;
    renderTabs("tab 1");
    await signedIn("tab 1");
    await rotationStarted();

    click("tab 1", "rotate my token");
    await act(async () => {
      server.releaseRotations();
    });
    await waitFor(() => expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-new-1"));
    expect(server.count("POST", "/users/u-1/sign-in-token")).toBe(1);
  });
});
