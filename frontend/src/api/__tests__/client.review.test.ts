// Wire format of the review decision calls (ui:2): every decision can carry
// the revision the reviewer saw as `expected_revision_number`, sent only when
// it is known, so the API refuses a decision on a stale revision with 409.
// The real client module runs against a stubbed fetch.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../client";

type Call = { method: string; path: string; body: unknown };

let calls: Call[] = [];
let respond: () => Response = () => new Response("{}", { status: 200 });

beforeEach(() => {
  calls = [];
  respond = () => new Response("{}", { status: 200 });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({
        method: init.method ?? "GET",
        path: new URL(url).pathname,
        body: init.body === undefined ? undefined : JSON.parse(init.body as string),
      });
      return respond();
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("review decision requests", () => {
  it("sends expected_revision_number with every decision when it is known", async () => {
    await api.acceptAssertion("a1", undefined, 3);
    await api.acceptAssertion("a1", "Counsel confirmed it.", 3);
    await api.rejectAssertion("a1", 3);
    await api.disputeAssertion("a1", 3);
    await api.requestRevision("a1", "Cite clause 8.4.", 3);
    await api.supersedeAssertion("a1", "a2", 3);

    expect(calls).toEqual([
      { method: "POST", path: "/api/v1/assertions/a1/accept", body: { expected_revision_number: 3 } },
      {
        method: "POST",
        path: "/api/v1/assertions/a1/accept",
        body: { acceptance_justification: "Counsel confirmed it.", expected_revision_number: 3 },
      },
      { method: "POST", path: "/api/v1/assertions/a1/reject", body: { expected_revision_number: 3 } },
      { method: "POST", path: "/api/v1/assertions/a1/dispute", body: { expected_revision_number: 3 } },
      {
        method: "POST",
        path: "/api/v1/assertions/a1/request-revision",
        body: { comment: "Cite clause 8.4.", expected_revision_number: 3 },
      },
      {
        method: "POST",
        path: "/api/v1/assertions/a1/supersede",
        body: { superseded_by_assertion_id: "a2", expected_revision_number: 3 },
      },
    ]);
  });

  it("leaves expected_revision_number out when no revision is known", async () => {
    await api.acceptAssertion("a1");
    await api.acceptAssertion("a1", "Counsel confirmed it.", null);
    await api.rejectAssertion("a1");
    await api.disputeAssertion("a1", null);
    await api.requestRevision("a1", "Cite clause 8.4.");
    await api.supersedeAssertion("a1", "a2", null);

    expect(calls.map((call) => call.body)).toEqual([
      {},
      { acceptance_justification: "Counsel confirmed it." },
      undefined,
      undefined,
      { comment: "Cite clause 8.4." },
      { superseded_by_assertion_id: "a2" },
    ]);
  });

  it("surfaces a stale-revision refusal as ApiError 409 with the server's reason", async () => {
    respond = () =>
      new Response(
        JSON.stringify({ detail: "assertion has been modified since expected_revision_number" }),
        { status: 409 },
      );

    const error = await api.rejectAssertion("a1", 1).catch((err: unknown) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).message).toBe(
      "assertion has been modified since expected_revision_number",
    );
  });
});
