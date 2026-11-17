// SessionProvider with the REAL api client (only fetch is stubbed): the
// stored value is the secret sign-in token sent as the bearer, while "my
// id" (session.user.id) always comes from GET /me (findings api:2/ui:0).
// Restoring drops the saved token only on a real 401; anything else keeps
// it and reports restoreError, leaving the session undefined (ui:18).

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionProvider, useSession } from "../session";

const TOKEN_KEY = "lexgraph.token";

function me(id: string, role = "viewer") {
  return {
    user: { id, email: `${id}@firm.example`, display_name: `User ${id}` },
    matters: [
      { id: "m-1", name: "Matter", repository_id: "r-1", organization_id: "o-1", role },
    ],
  };
}

function jsonResponse(status: number, body: unknown) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
}

const fetchMock = vi.fn();

function authHeaders(): (string | undefined)[] {
  return fetchMock.mock.calls.map(
    ([, init]) => (init as { headers: Record<string, string> }).headers["Authorization"],
  );
}

function Probe() {
  const { session, notice, restoreError, signIn, signOut, refresh, retryRestore } = useSession();
  return (
    <div>
      <span data-testid="state">
        {session === undefined ? "restoring" : session === null ? "signed-out" : "signed-in"}
      </span>
      <span data-testid="my-id">{session?.user.id ?? ""}</span>
      <span data-testid="role">{session?.role ?? ""}</span>
      <span data-testid="notice">{notice?.kind ?? ""}</span>
      <span data-testid="restore-error">{restoreError ?? ""}</span>
      <button type="button" onClick={() => void signIn("  tok-typed-in  ").catch(() => {})}>
        sign in
      </button>
      <button type="button" onClick={() => void retryRestore?.()}>
        retry
      </button>
      <button type="button" onClick={signOut}>
        sign out
      </button>
      <button
        type="button"
        onClick={() =>
          void refresh().then(
            () => document.body.setAttribute("data-refresh", "ok"),
            () => document.body.setAttribute("data-refresh", "failed"),
          )
        }
      >
        refresh
      </button>
    </div>
  );
}

function renderProvider() {
  return render(
    <SessionProvider>
      <Probe />
    </SessionProvider>,
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  window.localStorage.clear();
  document.body.removeAttribute("data-refresh");
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SessionProvider", () => {
  it("restores a value saved by the previous version (the old user id) as a legacy token", async () => {
    window.localStorage.setItem(TOKEN_KEY, "u-legacy");
    fetchMock.mockResolvedValue(jsonResponse(200, me("u-legacy")));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("signed-in"));
    expect(authHeaders()).toEqual(["Bearer u-legacy"]);
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("u-legacy");
  });

  it("exposes /me's public user id as my id, never the token", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok-secret-value");
    fetchMock.mockResolvedValue(jsonResponse(200, me("u-123")));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("my-id")).toHaveTextContent("u-123"));
    expect(document.body).not.toHaveTextContent("tok-secret-value");
  });

  it("signIn stores the trimmed token and sends it as the bearer", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, me("u-7")));
    renderProvider();
    expect(screen.getByTestId("state")).toHaveTextContent("signed-out");
    expect(fetchMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "sign in" }));

    await waitFor(() => expect(screen.getByTestId("my-id")).toHaveTextContent("u-7"));
    expect(authHeaders()).toEqual(["Bearer tok-typed-in"]);
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-typed-in");
  });

  it("does not keep a token the server rejects at sign-in", async () => {
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: "unknown sign-in token" }));
    renderProvider();

    fireEvent.click(screen.getByRole("button", { name: "sign in" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull());
    expect(screen.getByTestId("state")).toHaveTextContent("signed-out");
  });

  it("drops a saved token the server rejects (e.g. rotated) and says why", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok-rotated-away");
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: "unknown sign-in token" }));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("signed-out"));
    expect(screen.getByTestId("notice")).toHaveTextContent("token_rejected");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("keeps the saved token when the server is unreachable, stays signed in pending a retry, and retries", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok-still-valid");
    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed"));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("restore-error").textContent).not.toBe(""));
    // Not presented as signed out: no session yet, no sign-in form, no notice.
    expect(screen.getByTestId("state")).toHaveTextContent("restoring");
    expect(screen.getByTestId("notice").textContent).toBe("");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-still-valid");

    fetchMock.mockResolvedValue(jsonResponse(200, me("u-9")));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "retry" }));
    });

    await waitFor(() => expect(screen.getByTestId("my-id")).toHaveTextContent("u-9"));
    expect(screen.getByTestId("restore-error").textContent).toBe("");
    expect(authHeaders()).toEqual(["Bearer tok-still-valid", "Bearer tok-still-valid"]);
  });

  it.each([403, 404, 429, 500, 502, 503, 504])(
    "keeps the saved token when GET /me answers %i: only a 401 says the token is bad",
    async (status) => {
      window.localStorage.setItem(TOKEN_KEY, "tok-keep");
      fetchMock.mockResolvedValue(jsonResponse(status, { detail: "x" }));

      renderProvider();

      await waitFor(() => expect(screen.getByTestId("restore-error")).toHaveTextContent(String(status)));
      expect(screen.getByTestId("state")).toHaveTextContent("restoring");
      expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-keep");
    },
  );

  it("keeps the saved token when /me answers 200 with something that is not a session", async () => {
    // e.g. a static host answering the SPA's index.html for /api/v1/me
    window.localStorage.setItem(TOKEN_KEY, "tok-keep");
    fetchMock.mockResolvedValue(jsonResponse(200, "<!doctype html><html></html>"));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("restore-error").textContent).not.toBe(""));
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-keep");
  });

  it("a slow failing restore does not undo a sign-in made meanwhile", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok-old");
    const slow = deferred<unknown>();
    fetchMock.mockReturnValueOnce(slow.promise);
    fetchMock.mockResolvedValueOnce(jsonResponse(200, me("u-new")));
    renderProvider();

    fireEvent.click(screen.getByRole("button", { name: "sign in" }));
    await waitFor(() => expect(screen.getByTestId("my-id")).toHaveTextContent("u-new"));
    await act(async () => {
      slow.resolve(jsonResponse(401, { detail: "unknown sign-in token" }));
    });

    expect(screen.getByTestId("state")).toHaveTextContent("signed-in");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-typed-in");
    expect(screen.getByTestId("notice").textContent).toBe("");
  });

  it("refresh() re-reads /me and applies a changed role", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, me("u-1", "admin")));
    renderProvider();
    await waitFor(() => expect(screen.getByTestId("role")).toHaveTextContent("admin"));

    fetchMock.mockResolvedValueOnce(jsonResponse(200, me("u-1", "viewer")));
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    await waitFor(() => expect(screen.getByTestId("role")).toHaveTextContent("viewer"));
    expect(document.body.getAttribute("data-refresh")).toBe("ok");
  });

  it("refresh() keeps the session and reports failure when the server is unreachable", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, me("u-1", "admin")));
    renderProvider();
    await waitFor(() => expect(screen.getByTestId("role")).toHaveTextContent("admin"));

    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed"));
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    await waitFor(() => expect(document.body.getAttribute("data-refresh")).toBe("failed"));
    expect(screen.getByTestId("state")).toHaveTextContent("signed-in");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok");
  });

  it("a refresh that answers after sign-out does not bring the session back", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, me("u-1", "admin")));
    renderProvider();
    await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("signed-in"));

    const slow = deferred<unknown>();
    fetchMock.mockReturnValueOnce(slow.promise);
    fireEvent.click(screen.getByRole("button", { name: "refresh" }));
    fireEvent.click(screen.getByRole("button", { name: "sign out" }));
    await act(async () => {
      slow.resolve(jsonResponse(200, me("u-1", "admin")));
    });

    expect(screen.getByTestId("state")).toHaveTextContent("signed-out");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
