// Session state: who is signed in and which matter is active. Role comes
// from the matter membership, so permission-driven UI (review buttons,
// admin nav) reads session.role.
//
// The stored credential is the user's secret sign-in token
// (backend/app/auth.py). "My id" is always GET /me's PUBLIC user.id
// (session.user.id), never the token. The localStorage key predates sign-in
// tokens; a value saved then (the user id) keeps working as a legacy token
// on an upgraded backend until an admin rotates it.
//
// Only a 401 from GET /me signs the user out (finding ui:18):
// - On page load the saved token is checked with GET /me. A 401 drops it
//   and the sign-in page says why (`notice`). Anything else (no response,
//   a 5xx, a proxy's 404 or 429, a body that is not a session) keeps it:
//   `session` stays undefined and `restoreError` says what went wrong, so
//   App shows a retry screen instead of the sign-in form. That screen
//   retries on demand, when the browser comes back online, when the tab
//   regains focus and every minute.
// - While signed in, GET /me is read again (finding ui:19) after any
//   request the server refused (401/403, reported by the api client), when
//   the tab regains focus, and every minute, so a role changed or removed
//   by another admin reaches role-gated UI. A 401 there signs out only if a
//   second GET /me a moment later still answers 401 (so a token switch in
//   progress, e.g. rotating your own token, is not mistaken for a revoked
//   one); connectivity trouble leaves the session as it is. `refresh()`
//   re-reads /me on demand: the admin console calls it after you change
//   your own membership.

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { onAuthFailure } from "../api/authEvents";
import {
  ApiError,
  api,
  getStoredMatterId,
  getToken,
  setStoredMatterId,
  setToken,
} from "../api/client";
import type { MatterMembership, MatterRoleName, Me, UserInfo } from "../api/types";

export interface Session {
  user: UserInfo;
  matters: MatterMembership[];
  currentMatter: MatterMembership | null;
  role: MatterRoleName | null;
}

/** Why the user is on the sign-in page although a token had been saved. */
export interface SessionNotice {
  kind: "token_rejected";
  message: string;
}

const TOKEN_REJECTED_NOTICE =
  "Your saved sign-in token is no longer valid (it may have been rotated). " +
  "Enter your current sign-in token.";

/** Focus/visibility/interval re-reads of /me happen at most this often. */
const RECHECK_MIN_GAP_MS = 5_000;
/** Background re-read of /me while signed in (or retrying a restore). */
const RECHECK_INTERVAL_MS = 60_000;
/** A 401 on a background re-read is confirmed by another GET /me this much later. */
const UNAUTHORIZED_CONFIRM_MS = 1_000;

interface SessionContextValue {
  /** undefined = restoring from storage (or restoring failed: see
   * restoreError); null = signed out */
  session: Session | null | undefined;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  selectMatter: (matterId: string) => void;
  /** Re-read GET /me now. Rejects, keeping the session as it is, when the
   * server cannot be reached. */
  refresh: () => Promise<void>;
  /** Why the user was signed out (shown on the sign-in page); null otherwise. */
  notice?: SessionNotice | null;
  /** Set while a saved sign-in could not be checked (the token is kept and
   * App offers a retry); null otherwise. */
  restoreError?: string | null;
  /** Check the saved sign-in again. */
  retryRestore?: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

/** GET /me answered 2xx with something that is not a session (e.g. a static
 * host serving index.html for /api/v1/me). */
class UnexpectedResponse extends Error {}

function readMe(value: unknown): Me {
  const me = value as Partial<Me> | null;
  if (
    !me ||
    typeof me !== "object" ||
    !me.user ||
    typeof me.user.id !== "string" ||
    !Array.isArray(me.matters)
  ) {
    throw new UnexpectedResponse("unexpected GET /me response");
  }
  return me as Me;
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

function describeFailure(error: unknown): string {
  if (error instanceof ApiError) return `The server answered HTTP ${error.status}.`;
  if (error instanceof UnexpectedResponse) {
    return "The answer did not come from the LexGraph API (check the API address or proxy).";
  }
  return "No response from the server.";
}

function buildSession(user: UserInfo, matters: MatterMembership[]): Session {
  const storedId = getStoredMatterId();
  const currentMatter =
    matters.find((m) => m.id === storedId) ?? matters[0] ?? null;
  if (currentMatter) setStoredMatterId(currentMatter.id);
  return { user, matters, currentMatter, role: currentMatter?.role ?? null };
}

function sameSession(a: Session, b: Session): boolean {
  return (
    a.currentMatter?.id === b.currentMatter?.id &&
    JSON.stringify([a.user, a.matters]) === JSON.stringify([b.user, b.matters])
  );
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [notice, setNotice] = useState<SessionNotice | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  // Bumped by every restore, sign-in and sign-out: an answer to a request
  // that started before the latest of those is stale and ignored.
  const epochRef = useRef(0);
  // Orders /me re-reads: only the newest one may apply its answer.
  const recheckSeqRef = useRef(0);
  const recheckInFlightRef = useRef(false);
  const recheckAgainRef = useRef(false);
  // Restores in flight (auto-retries never stack on top of one).
  const restoringRef = useRef(0);
  const confirmPendingRef = useRef(false);
  const lastCheckRef = useRef(0);
  const timersRef = useRef(new Set<number>());
  const sessionRef = useRef(session);
  sessionRef.current = session;
  const restoreErrorRef = useRef(restoreError);
  restoreErrorRef.current = restoreError;

  const apply = useCallback((me: Me) => {
    lastCheckRef.current = Date.now();
    const next = buildSession(me.user, me.matters);
    // Keep the same object when nothing changed, so consumers do not re-render.
    setSession((current) => (current && sameSession(current, next) ? current : next));
  }, []);

  const signOutRejected = useCallback(() => {
    epochRef.current += 1;
    setToken(null);
    setRestoreError(null);
    setNotice({ kind: "token_rejected", message: TOKEN_REJECTED_NOTICE });
    setSession(null);
  }, []);

  const restore = useCallback(async () => {
    const epoch = ++epochRef.current;
    if (!getToken()) {
      setRestoreError(null);
      setSession(null);
      return;
    }
    restoringRef.current += 1;
    setSession(undefined);
    try {
      const me = readMe(await api.me());
      if (epoch !== epochRef.current) return;
      setNotice(null);
      setRestoreError(null);
      apply(me);
    } catch (error) {
      if (epoch !== epochRef.current) return;
      if (isUnauthorized(error)) {
        signOutRejected();
      } else {
        // Keep the token: nothing says it is invalid (ui:18).
        lastCheckRef.current = Date.now();
        setRestoreError(describeFailure(error));
      }
    } finally {
      restoringRef.current -= 1;
    }
  }, [apply, signOutRejected]);

  useEffect(() => {
    void restore();
  }, [restore]);

  const signIn = useCallback(
    async (token: string) => {
      const epoch = ++epochRef.current;
      setToken(token.trim());
      try {
        const me = readMe(await api.me());
        if (epoch !== epochRef.current) return;
        setNotice(null);
        setRestoreError(null);
        apply(me);
      } catch (error) {
        if (epoch === epochRef.current) setToken(null);
        throw error;
      }
    },
    [apply],
  );

  const signOut = useCallback(() => {
    epochRef.current += 1;
    setToken(null);
    setStoredMatterId(null);
    setNotice(null);
    setRestoreError(null);
    setSession(null);
  }, []);

  /** A background /me answered 401: sign out only if it still does a moment
   * later with the same token. */
  const confirmUnauthorized = useCallback(
    (token: string, epoch: number) => {
      if (confirmPendingRef.current) return;
      confirmPendingRef.current = true;
      const stillCurrent = () => epoch === epochRef.current && getToken() === token;
      const timer = window.setTimeout(async () => {
        timersRef.current.delete(timer);
        try {
          if (!stillCurrent()) return;
          const me = readMe(await api.me());
          if (stillCurrent()) apply(me);
        } catch (error) {
          if (stillCurrent() && isUnauthorized(error)) signOutRejected();
        } finally {
          confirmPendingRef.current = false;
        }
      }, UNAUTHORIZED_CONFIRM_MS);
      timersRef.current.add(timer);
    },
    [apply, signOutRejected],
  );

  /** Re-read /me for the signed-in session. */
  const recheck = useCallback(async () => {
    const token = getToken();
    if (!token || !sessionRef.current) return;
    const epoch = epochRef.current;
    const seq = ++recheckSeqRef.current;
    lastCheckRef.current = Date.now();
    const stillCurrent = () => epoch === epochRef.current && getToken() === token;
    let me: Me;
    try {
      me = readMe(await api.me());
    } catch (error) {
      if (!stillCurrent()) return;
      if (isUnauthorized(error)) {
        confirmUnauthorized(token, epoch);
        return;
      }
      throw error;
    }
    if (stillCurrent() && seq === recheckSeqRef.current) apply(me);
  }, [apply, confirmUnauthorized]);

  const recheckInBackground = useCallback(
    (force: boolean) => {
      const due = force || Date.now() - lastCheckRef.current >= RECHECK_MIN_GAP_MS;
      if (restoreErrorRef.current) {
        // The saved sign-in could not be checked yet: try again.
        if (due && restoringRef.current === 0) void restore();
        return;
      }
      if (!sessionRef.current || !due) return;
      if (recheckInFlightRef.current) {
        recheckAgainRef.current = true;
        return;
      }
      recheckInFlightRef.current = true;
      const run = (): Promise<void> =>
        recheck()
          .catch(() => {
            // Connectivity trouble: keep the session as it is (ui:18).
          })
          .then(() => {
            if (recheckAgainRef.current) {
              recheckAgainRef.current = false;
              return run();
            }
            recheckInFlightRef.current = false;
          });
      void run();
    },
    [recheck, restore],
  );

  useEffect(() => {
    const onFocus = () => recheckInBackground(false);
    const onVisibility = () => {
      if (document.visibilityState === "visible") recheckInBackground(false);
    };
    const onOnline = () => recheckInBackground(true);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("online", onOnline);
    const interval = window.setInterval(() => {
      if (document.visibilityState !== "hidden") recheckInBackground(false);
    }, RECHECK_INTERVAL_MS);
    // Answers to GET /me itself are handled where they are read.
    const unsubscribe = onAuthFailure((failure) => {
      if (failure.path !== "/me") recheckInBackground(true);
    });
    const timers = timersRef.current;
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("online", onOnline);
      window.clearInterval(interval);
      unsubscribe();
      for (const timer of timers) window.clearTimeout(timer);
      timers.clear();
    };
  }, [recheckInBackground]);

  const selectMatter = useCallback((matterId: string) => {
    setSession((current) => {
      if (!current) return current;
      const matter = current.matters.find((m) => m.id === matterId) ?? null;
      setStoredMatterId(matter?.id ?? null);
      return { ...current, currentMatter: matter, role: matter?.role ?? null };
    });
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      signIn,
      signOut,
      selectMatter,
      refresh: recheck,
      notice,
      restoreError,
      retryRestore: restore,
    }),
    [session, signIn, signOut, selectMatter, recheck, notice, restoreError, restore],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

/** For pages that render only when signed in with a matter selected. */
export function useActiveSession(): Session & { currentMatter: MatterMembership } {
  const { session } = useSession();
  if (!session?.currentMatter) {
    throw new Error("useActiveSession requires a signed-in session with a matter");
  }
  return session as Session & { currentMatter: MatterMembership };
}
