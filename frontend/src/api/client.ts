// Thin typed client over the LexGraph REST API.
//
// Auth (backend/app/auth.py): the bearer token is the user's secret
// sign-in token, NOT the public user id (the signed-in user's id comes from
// GET /me). The token lives in localStorage so a reload keeps the session;
// there is no server-side session state. The key predates sign-in tokens:
// a value stored then (the user id) is accepted by an upgraded backend as a
// legacy token until an admin rotates it, so it needs no client migration.

import type {
  AppNotification,
  Assertion,
  AssertionComment,
  AssertionDetail,
  AssertionList,
  AssertionListParams,
  CreateAssertionResult,
  Evidence,
  HistoryEvent,
  IssuedSignIn,
  MatterGraph,
  MatterMember,
  MatterRoleName,
  Me,
  NotificationListParams,
  NotificationPreference,
  Rating,
  RatingSummary,
  RelatedMatch,
  RelatedMatchList,
  Revision,
  UserAccount,
  UserInfo,
} from "./types";
import type { AssertionStats, AssertionStatsParams } from "./types";
import { reportAuthFailure } from "./authEvents";

const TOKEN_KEY = "lexgraph.token";
const MATTER_KEY = "lexgraph.matter";

const API_BASE: string =
  (import.meta.env?.VITE_API_BASE as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
    /** The parsed error response body, for structured fields beside `detail`. */
    public body: unknown = null,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token === null) {
    window.localStorage.removeItem(TOKEN_KEY);
  } else {
    window.localStorage.setItem(TOKEN_KEY, token);
  }
}

export function getStoredMatterId(): string | null {
  return window.localStorage.getItem(MATTER_KEY);
}

export function setStoredMatterId(matterId: string | null): void {
  if (matterId === null) {
    window.localStorage.removeItem(MATTER_KEY);
  } else {
    window.localStorage.setItem(MATTER_KEY, matterId);
  }
}

function detailFromBody(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }
  return fallback;
}

type RequestOptions = { body?: unknown; query?: Record<string, unknown> };

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  return (await send(method, path, options)).payload as T;
}

/** A successful response's parsed body, with the response itself for its
 * headers; any other status throws ApiError. */
async function send(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<{ payload: unknown; response: Response }> {
  const url = new URL(API_BASE + path, window.location.origin);
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(url.toString(), {
    method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 204) return { payload: undefined, response };

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    // Lets the session re-check GET /me (authEvents.ts, ui:18/ui:19).
    if (response.status === 401 || response.status === 403) {
      reportAuthFailure({ status: response.status, method, path });
    }
    throw new ApiError(
      response.status,
      detailFromBody(payload, `${method} ${path} failed (${response.status})`),
      payload,
    );
  }

  return { payload, response };
}

/** The `expected_revision_number` field of a review decision, present only when known. */
function expectedRevision(
  expectedRevisionNumber: number | null | undefined,
): { expected_revision_number?: number } {
  return expectedRevisionNumber != null ? { expected_revision_number: expectedRevisionNumber } : {};
}

export const api = {
  // --- session / workspace ------------------------------------------------
  me: () => request<Me>("GET", "/me"),

  listMatterMembers: (matterId: string) =>
    request<MatterMember[]>("GET", `/matters/${matterId}/members`),

  setMatterMemberRole: (matterId: string, userId: string, role: MatterRoleName) =>
    request<MatterMember>("PUT", `/matters/${matterId}/members/${encodeURIComponent(userId)}`, {
      body: { role },
    }),

  addMatterMember: (matterId: string, email: string, role: MatterRoleName) =>
    request<MatterMember>("POST", `/matters/${matterId}/members`, {
      body: { email, role },
    }),

  removeMatterMember: (matterId: string, userId: string) =>
    request<void>("DELETE", `/matters/${matterId}/members/${encodeURIComponent(userId)}`),

  // --- user accounts (B2/UI1: admin-on-any-matter gate, backend/app/routers/users.py) ---
  listUsers: () => request<UserAccount[]>("GET", "/users"),

  /** The response carries the new account's sign-in token, shown once. */
  createUser: (email: string, displayName: string, id?: string) =>
    request<IssuedSignIn>("POST", "/users", {
      body: { email, display_name: displayName, ...(id ? { id } : {}) },
    }),

  /** Replace an account's sign-in token; the old one stops working. */
  rotateSignInToken: (userId: string) =>
    request<IssuedSignIn>("POST", `/users/${encodeURIComponent(userId)}/sign-in-token`),

  sources: (matterId: string, kind: "entities" | "source-spans", q = "", offset = 0) =>
    request<{ items: { id: string; type?: string; label?: string; document_title?: string; quote_text?: string }[]; total: number }>(
      "GET", `/matters/${matterId}/${kind}`, { query: { q, offset, limit: 50 } }),

  // --- assertions ---------------------------------------------------------
  listAssertions: (matterId: string, params: AssertionListParams = {}) =>
    request<AssertionList>("GET", "/assertions", {
      query: { matter_id: matterId, ...params },
    }),

  assertionStats: (matterId: string, params: AssertionStatsParams = {}) =>
    request<AssertionStats>("GET", `/matters/${matterId}/assertion-stats`, {
      query: { ...params },
    }),

  getAssertion: (id: string) => request<AssertionDetail>("GET", `/assertions/${id}`),

  createAssertion: (body: Record<string, unknown>) =>
    request<CreateAssertionResult>(
      "POST",
      "/assertions",
      { body },
    ),

  updateAssertion: (id: string, body: Record<string, unknown>) =>
    request<Assertion>("PATCH", `/assertions/${id}`, { body }),

  submitAssertion: (id: string) => request<Assertion>("POST", `/assertions/${id}/submit`),

  withdrawAssertion: (id: string) =>
    request<Assertion>("POST", `/assertions/${id}/withdraw`),

  /** The strongest matches (the server lists at most 20); the array's
   * `total` is every match it found (X-Total-Count), when it says. */
  relatedAssertions: async (id: string): Promise<RelatedMatchList> => {
    const { payload, response } = await send("GET", `/assertions/${id}/related`);
    const matches = (Array.isArray(payload) ? payload : []) as RelatedMatch[];
    const total = Number(response.headers?.get("X-Total-Count") ?? Number.NaN);
    // Not enumerable: the value still compares and spreads as a plain list.
    return Number.isInteger(total) && total >= matches.length
      ? Object.defineProperty(matches, "total", { value: total, enumerable: false })
      : matches;
  },

  // --- review (reviewer/admin) -------------------------------------------
  // `expectedRevisionNumber` is the revision the reviewer saw; when it is no
  // longer current the API refuses the decision with 409 and changes nothing.
  acceptAssertion: (
    id: string,
    acceptanceJustification?: string,
    expectedRevisionNumber?: number | null,
  ) =>
    request<Assertion>("POST", `/assertions/${id}/accept`, {
      body: {
        ...(acceptanceJustification
          ? { acceptance_justification: acceptanceJustification }
          : {}),
        ...expectedRevision(expectedRevisionNumber),
      },
    }),

  rejectAssertion: (id: string, expectedRevisionNumber?: number | null) =>
    request<Assertion>("POST", `/assertions/${id}/reject`, {
      body: expectedRevisionNumber != null ? expectedRevision(expectedRevisionNumber) : undefined,
    }),

  disputeAssertion: (id: string, expectedRevisionNumber?: number | null) =>
    request<Assertion>("POST", `/assertions/${id}/dispute`, {
      body: expectedRevisionNumber != null ? expectedRevision(expectedRevisionNumber) : undefined,
    }),

  requestRevision: (id: string, comment?: string, expectedRevisionNumber?: number | null) =>
    request<Assertion>("POST", `/assertions/${id}/request-revision`, {
      body: { ...(comment ? { comment } : {}), ...expectedRevision(expectedRevisionNumber) },
    }),

  supersedeAssertion: (
    id: string,
    supersededByAssertionId: string,
    expectedRevisionNumber?: number | null,
  ) =>
    request<Assertion>("POST", `/assertions/${id}/supersede`, {
      body: {
        superseded_by_assertion_id: supersededByAssertionId,
        ...expectedRevision(expectedRevisionNumber),
      },
    }),

  // --- evidence / revisions / comments / history --------------------------
  listEvidence: (id: string) => request<Evidence[]>("GET", `/assertions/${id}/evidence`),

  addEvidence: (id: string, sourceSpanId: string, evidenceRole: string) =>
    request<Evidence>("POST", `/assertions/${id}/evidence`, {
      body: { source_span_id: sourceSpanId, evidence_role: evidenceRole },
    }),

  removeEvidence: (id: string, evidenceId: string) =>
    request<void>("DELETE", `/assertions/${id}/evidence/${evidenceId}`),

  listRevisions: (id: string) => request<Revision[]>("GET", `/assertions/${id}/revisions`),

  createRevision: (id: string, body: Record<string, unknown>) =>
    request<Revision>("POST", `/assertions/${id}/revisions`, { body }),

  listComments: (id: string) =>
    request<AssertionComment[]>("GET", `/assertions/${id}/comments`),

  addComment: (id: string, commentText: string, parentCommentId?: string) =>
    request<AssertionComment>("POST", `/assertions/${id}/comments`, {
      body: { comment_text: commentText, parent_comment_id: parentCommentId ?? null },
    }),

  // Own comments only; needs assertion:comment (contributor, reviewer, admin).
  updateComment: (id: string, commentId: string, commentText: string) =>
    request<AssertionComment>("PATCH", `/assertions/${id}/comments/${commentId}`, {
      body: { comment_text: commentText },
    }),

  deleteComment: (id: string, commentId: string) =>
    request<void>("DELETE", `/assertions/${id}/comments/${commentId}`),

  history: (id: string) => request<HistoryEvent[]>("GET", `/assertions/${id}/history`),

  // --- ratings -------------------------------------------------------------
  putRating: (id: string, revision: number, strength: number, rationale: string) =>
    request<Rating>("PUT", `/assertions/${id}/revisions/${revision}/rating`, {
      body: { strength, rationale },
    }),

  deleteRating: (id: string, revision: number) =>
    request<void>("DELETE", `/assertions/${id}/revisions/${revision}/rating`),

  ratingSummary: (id: string, revision: number) =>
    request<RatingSummary>("GET", `/assertions/${id}/revisions/${revision}/ratings/summary`),

  listRatings: (id: string, revision: number) =>
    request<Rating[]>("GET", `/assertions/${id}/revisions/${revision}/ratings`),

  // --- graph / notifications ----------------------------------------------
  matterGraph: (matterId: string) =>
    request<MatterGraph>("GET", `/matters/${matterId}/graph`),

  notifications: (params: NotificationListParams = {}) =>
    request<AppNotification[]>("GET", "/notifications", { query: { ...params } }),

  unreadNotificationCount: () =>
    request<{ unread_count: number }>("GET", "/notifications/unread-count"),

  markNotificationRead: (id: string) =>
    request<AppNotification>("POST", `/notifications/${encodeURIComponent(id)}/read`),

  /** Notices created after `lastReadAt` (ISO) stay unread; omit it to mark all. */
  markAllNotificationsRead: (lastReadAt?: string) =>
    request<{ marked_read: number; unread_count: number }>("POST", "/notifications/read-all", {
      body: lastReadAt ? { last_read_at: lastReadAt } : {},
    }),

  notificationPreferences: () =>
    request<NotificationPreference[]>("GET", "/notifications/preferences"),

  updateNotificationPreferences: (preferences: Record<string, boolean>) =>
    request<NotificationPreference[]>("PUT", "/notifications/preferences", {
      body: { preferences },
    }),
};

export type Api = typeof api;
