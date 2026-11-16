import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssertionListItem, AssertionListParams } from "../types";

vi.mock("../client", () => ({ api: { listAssertions: vi.fn() } }));

import { api } from "../client";
import { LIST_PAGE_MAX, listWindow } from "../listWindow";

const mockedList = vi.mocked(api.listAssertions);

function rowsUpTo(count: number): AssertionListItem[] {
  return Array.from({ length: count }, (_, i) => ({ id: `a${i}` }) as AssertionListItem);
}

let rows: AssertionListItem[] = [];

beforeEach(() => {
  vi.clearAllMocks();
  rows = rowsUpTo(1_234);
  mockedList.mockImplementation(async (_matterId: string, params: AssertionListParams = {}) => {
    const offset = params.offset ?? 0;
    const items =
      params.limit === undefined ? rows.slice(offset) : rows.slice(offset, offset + params.limit);
    return { items, total: rows.length };
  });
});

describe("listWindow", () => {
  it("reads a window that fits one request with one request", async () => {
    const page = await listWindow("m1", { status: "proposed" }, 50);

    expect(mockedList).toHaveBeenCalledTimes(1);
    expect(mockedList).toHaveBeenCalledWith("m1", { status: "proposed", limit: 50, offset: 0 });
    expect(page.items.map((item) => item.id)).toEqual(rows.slice(0, 50).map((item) => item.id));
    expect(page.total).toBe(1_234);
  });

  it("reads a larger window as consecutive pages of the endpoint's largest size", async () => {
    const page = await listWindow("m1", { status: "disputed" }, 1_100);

    expect(mockedList.mock.calls.map(([, params]) => [params?.offset, params?.limit])).toEqual([
      [0, LIST_PAGE_MAX],
      [500, LIST_PAGE_MAX],
      [1_000, 100],
    ]);
    expect(page.items).toHaveLength(1_100);
    expect(new Set(page.items.map((item) => item.id)).size).toBe(1_100);
  });

  it("lists a row once when an insert shifts a later page", async () => {
    mockedList.mockImplementation(async (_matterId: string, params: AssertionListParams = {}) => {
      // The second page starts one row early, as after a row was inserted.
      const offset = (params.offset ?? 0) === 0 ? 0 : (params.offset ?? 0) - 1;
      return { items: rows.slice(offset, offset + (params.limit ?? rows.length)), total: rows.length };
    });

    const page = await listWindow("m1", {}, 600);

    expect(page.items.filter((item) => item.id === "a499")).toHaveLength(1);
  });

  it("keeps the window when the server ignores limit", async () => {
    mockedList.mockResolvedValue({ items: rows, total: rows.length });

    const page = await listWindow("m1", {}, 50);

    expect(page.items).toHaveLength(50);
    expect(page.total).toBe(1_234);
  });
});
