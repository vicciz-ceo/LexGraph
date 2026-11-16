// Windowed reads of GET /assertions for the pages that list "the first N" of
// a result set and grow N with "Show more" (Review Queue, Contested).
//
// The endpoint pages with limit (1-500) and offset; a window larger than one
// request is read as consecutive pages. Every reload reads the whole window
// again from the start, so the cards on screen stay in step with the server:
// a decision that removes a card shifts every later offset by one.
//
// Imports only `api` from the client, so it also works against page tests'
// mocked client module.

import { api } from "./client";
import type { AssertionList, AssertionListItem, AssertionListParams } from "./types";

/** The largest page GET /assertions returns (backend LIST_MAX_LIMIT). */
export const LIST_PAGE_MAX = 500;

/**
 * The first `size` matches of `params` in the server's order, and how many
 * match in all. A server that ignores limit returns every match; the window
 * is still `size` rows.
 */
export async function listWindow(
  matterId: string,
  params: AssertionListParams,
  size: number,
): Promise<AssertionList> {
  const requests: Promise<AssertionList>[] = [];
  for (let offset = 0; offset < size; offset += LIST_PAGE_MAX) {
    requests.push(
      api.listAssertions(matterId, {
        ...params,
        limit: Math.min(LIST_PAGE_MAX, size - offset),
        offset,
      }),
    );
  }
  const pages = await Promise.all(requests);
  // A row created between two page requests shifts the later page by one.
  const seen = new Set<string>();
  const items: AssertionListItem[] = [];
  for (const page of pages) {
    for (const item of page.items) {
      if (!seen.has(item.id)) {
        seen.add(item.id);
        items.push(item);
      }
    }
  }
  return { items: items.slice(0, size), total: pages[0]?.total ?? items.length };
}
