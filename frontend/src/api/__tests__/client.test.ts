// The api client with only fetch stubbed.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { onAuthFailure } from "../authEvents";
import { ApiError, api } from "../client";

const fetchMock = vi.fn();

function reply(status: number, body: unknown = undefined) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => (body === undefined ? "" : JSON.stringify(body)),
  };
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("encodes the user id in the member endpoints' URL paths", async () => {
    // Accounts created before ids were restricted (finding api:24) can
    // have ids such as "who?me": unencoded, "?" started a query string and
    // the role change or removal hit the wrong path.
    fetchMock.mockResolvedValue(reply(204));

    await api.setMatterMemberRole("m-1", "who?me#x", "viewer");
    await api.removeMatterMember("m-1", "who?me#x");

    const paths = fetchMock.mock.calls.map(([url]) => new URL(url as string).pathname);
    expect(paths).toEqual([
      "/api/v1/matters/m-1/members/who%3Fme%23x",
      "/api/v1/matters/m-1/members/who%3Fme%23x",
    ]);
  });

  it("reports refused requests (401/403) so the session can re-check GET /me", async () => {
    const seen: unknown[] = [];
    const unsubscribe = onAuthFailure((failure) => seen.push(failure));
    fetchMock
      .mockResolvedValueOnce(reply(403, { detail: "no access to matter" }))
      .mockResolvedValueOnce(reply(401, { detail: "unknown sign-in token" }))
      .mockResolvedValueOnce(reply(404, { detail: "not found" }));
    try {
      await expect(api.listMatterMembers("m-1")).rejects.toBeInstanceOf(ApiError);
      await expect(api.me()).rejects.toBeInstanceOf(ApiError);
      await expect(api.getAssertion("a-1")).rejects.toBeInstanceOf(ApiError);
    } finally {
      unsubscribe();
    }

    expect(seen).toEqual([
      { status: 403, method: "GET", path: "/matters/m-1/members" },
      { status: 401, method: "GET", path: "/me" },
    ]);
  });

  it("reads the empty body of a 204, so the browser does not report the request as aborted", async () => {
    const text = vi.fn(async () => "");
    fetchMock.mockResolvedValue({ status: 204, ok: true, text });

    await expect(api.deleteComment("a-1", "c-1")).resolves.toBeUndefined();
    expect(text).toHaveBeenCalledTimes(1);
  });

  it("hands over how many related assertions the server found beyond the listed ones", async () => {
    const listed = [{ assertion_id: "a-2", match_kind: "similar", score: 0.7 }];
    fetchMock
      .mockResolvedValueOnce({
        ...reply(200, listed),
        headers: new Headers({ "X-Total-Count": "37" }),
      })
      .mockResolvedValueOnce(reply(200, listed));

    const capped = await api.relatedAssertions("a-1");
    expect(capped).toEqual(listed);
    expect(capped.total).toBe(37);

    // No header (an older server): no total, only the list.
    const plain = await api.relatedAssertions("a-1");
    expect(plain).toEqual(listed);
    expect(plain.total).toBeUndefined();
  });
});
