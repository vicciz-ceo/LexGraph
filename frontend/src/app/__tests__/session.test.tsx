// SessionProvider with the REAL api client (only fetch is stubbed): the
// stored value is the secret sign-in token sent as the bearer, while "my
// id" (session.user.id) always comes from GET /me (findings api:2/ui:0).

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionProvider, useSession } from "../session";

const TOKEN_KEY = "lexgraph.token";

function me(id: string) {
  return {
    user: { id, email: `${id}@firm.example`, display_name: `User ${id}` },
    matters: [
      { id: "m-1", name: "Matter", repository_id: "r-1", organization_id: "o-1", role: "viewer" },
    ],
  };
}

function jsonResponse(status: number, body: unknown) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => JSON.stringify(body),
  };
}

const fetchMock = vi.fn();

function authHeaders(): (string | undefined)[] {
  return fetchMock.mock.calls.map(
    ([, init]) => (init as { headers: Record<string, string> }).headers["Authorization"],
  );
}

function Probe() {
  const { session, notice, signIn, retryRestore } = useSession();
  return (
    <div>
      <span data-testid="state">
        {session === undefined ? "restoring" : session === null ? "signed-out" : "signed-in"}
      </span>
      <span data-testid="my-id">{session?.user.id ?? ""}</span>
      <span data-testid="notice">{notice?.kind ?? ""}</span>
      <button type="button" onClick={() => void signIn("  tok-typed-in  ").catch(() => {})}>
        sign in
      </button>
      <button type="button" onClick={() => retryRestore?.()}>
        retry
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

beforeEach(() => {
  window.localStorage.clear();
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

  it("keeps the saved token when the server is unreachable, and can retry", async () => {
    window.localStorage.setItem(TOKEN_KEY, "tok-still-valid");
    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed"));

    renderProvider();

    await waitFor(() => expect(screen.getByTestId("notice")).toHaveTextContent("server_unreachable"));
    expect(screen.getByTestId("state")).toHaveTextContent("signed-out");
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("tok-still-valid");

    fetchMock.mockResolvedValue(jsonResponse(200, me("u-9")));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "retry" }));
    });

    await waitFor(() => expect(screen.getByTestId("my-id")).toHaveTextContent("u-9"));
    expect(screen.getByTestId("notice").textContent).toBe("");
    expect(authHeaders()).toEqual(["Bearer tok-still-valid", "Bearer tok-still-valid"]);
  });
});
