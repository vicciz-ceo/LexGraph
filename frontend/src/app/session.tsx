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
//
// Each tab keeps its own matter (review identity:0). All tabs of the browser
// share localStorage, so the saved matter (`lexgraph.matter`) is only where a
// new tab, a reload or a sign-in starts. A re-read of /me keeps the matter
// this tab shows, with its fresh role, and moves to the saved matter (else
// the first) only when this tab's matter is no longer one of the user's. The
// saved matter is written when the user picks a matter, on sign-in and
// restore, and on that move: never by a re-read that kept the tab's matter,
// so it cannot overwrite another tab's choice.
//
// The other tabs share the saved token too (review identity:1). When another
// tab removes it (signing out, or a token the server refused), this tab
// signs out at once, and the sign-in page says which of the two it was; when
// another tab saves a different token (rotating your own token, signing in),
// this tab re-reads /me with it, or, if signed out here, follows that sign-in
// once /me accepts the token. A missed `storage` event is caught by the next
// re-read: a session shown with no saved token is signed out.
//
// Rotating your own token runs here, not in the admin page (review
// identity:2): the new token is adopted the moment the server answers,
// whatever page is open, and kept in `issuedOwnToken` so that it is shown
// once, until the user says it is saved. From the server's commit until
// that answer the old token is refused: such a 401, in this tab or in
// another, signs out only if the rotation fails.

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
import type { IssuedSignIn, MatterMembership, MatterRoleName, Me, UserInfo } from "../api/types";

export interface Session {
  user: UserInfo;
  matters: MatterMembership[];
  currentMatter: MatterMembership | null;
  role: MatterRoleName | null;
}

/** Why the user is on the sign-in page although a token had been saved:
 * the server refused it (here or in another tab), or another tab signed out. */
export interface SessionNotice {
  kind: "token_rejected" | "signed_out_elsewhere";
  message: string;
}

const TOKEN_REJECTED_NOTICE =
  "Your saved sign-in token is no longer valid (it may have been rotated). " +
  "Enter your current sign-in token.";
const SIGNED_OUT_ELSEWHERE_NOTICE =
  "You were signed out in another tab or window. Enter your sign-in token to sign in again.";

const REJECTED: SessionNotice = { kind: "token_rejected", message: TOKEN_REJECTED_NOTICE };
const ELSEWHERE: SessionNotice = { kind: "signed_out_elsewhere", message: SIGNED_OUT_ELSEWHERE_NOTICE };

/** Focus/visibility/interval re-reads of /me happen at most this often. */
const RECHECK_MIN_GAP_MS = 5_000;
/** Background re-read of /me while signed in (or retrying a restore). */
const RECHECK_INTERVAL_MS = 60_000;
/** A 401 on a background re-read is confirmed by another GET /me this much later. */
const UNAUTHORIZED_CONFIRM_MS = 1_000;

/** Why a tab last removed the saved token, for the other tabs' notice. */
const SIGN_OUT_REASON_KEY = "lexgraph.sign-out-reason";
type SignOutReason = "signed_out" | "token_rejected";

function readSignOutReason(): SignOutReason | null {
  try {
    const value = window.localStorage.getItem(SIGN_OUT_REASON_KEY);
    return value === "signed_out" || value === "token_rejected" ? value : null;
  } catch {
    return null;
  }
}

function writeSignOutReason(reason: SignOutReason | null): void {
  try {
    if (reason === null) window.localStorage.removeItem(SIGN_OUT_REASON_KEY);
    else window.localStorage.setItem(SIGN_OUT_REASON_KEY, reason);
  } catch {
    // The other tabs then show the neutral notice.
  }
}

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
  /** Replace the signed-in user's own sign-in token. This browser switches
   * to the new token as soon as the server answers, whatever page is open,
   * and the session keeps it in `issuedOwnToken`. Rejects, changing
   * nothing, when the server refuses or cannot be reached; while a rotation
   * is on its way, calling again returns that one. */
  rotateOwnToken?: () => Promise<IssuedSignIn>;
  /** The token your own last rotation issued, until acknowledged (it is
   * shown exactly once); null otherwise. */
  issuedOwnToken?: IssuedSignIn | null;
  /** The user saved `issuedOwnToken`: stop showing it. */
  acknowledgeIssuedOwnToken?: () => void;
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

/** The session for a GET /me answer. `tabMatterId` is the matter this tab
 * shows (null on restore and sign-in): it is kept, with its fresh role, while
 * the user still belongs to it. Otherwise the saved matter, else the first
 * one; `moved` says so, and the caller then saves it. */
function buildSession(
  user: UserInfo,
  matters: MatterMembership[],
  tabMatterId: string | null,
): { session: Session; moved: boolean } {
  const kept = tabMatterId === null ? undefined : matters.find((m) => m.id === tabMatterId);
  if (kept) {
    return { session: { user, matters, currentMatter: kept, role: kept.role }, moved: false };
  }
  const storedId = getStoredMatterId();
  const currentMatter = matters.find((m) => m.id === storedId) ?? matters[0] ?? null;
  return {
    session: { user, matters, currentMatter, role: currentMatter?.role ?? null },
    moved: true,
  };
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
  const [issuedOwnToken, setIssuedOwnToken] = useState<IssuedSignIn | null>(null);

  // Bumped by every restore, sign-in, sign-out and token switch: an answer
  // to a request that started before the latest of those is stale and ignored.
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
  // The session as last set, at once (the state only follows on the next
  // render). Every change goes through commit().
  const sessionRef = useRef<Session | null | undefined>(undefined);
  // The saved token as this tab last read or wrote it: another value in
  // localStorage means another tab changed it.
  const knownTokenRef = useRef<string | null>(null);
  // Your own token rotation while its answer is on its way.
  const ownRotationRef = useRef<Promise<IssuedSignIn> | null>(null);
  const restoreErrorRef = useRef(restoreError);
  restoreErrorRef.current = restoreError;

  const commit = useCallback((next: Session | null | undefined) => {
    sessionRef.current = next;
    setSession(next);
  }, []);

  /** Save or remove the token; a removal says why, for the other tabs. */
  const saveToken = useCallback((token: string | null, reason: SignOutReason | null = null) => {
    // The reason first: another tab reads it when it hears about the token.
    writeSignOutReason(token === null ? reason : null);
    setToken(token);
    knownTokenRef.current = token;
  }, []);

  /** Show the sign-in page, with `why` when there is one. */
  const leave = useCallback(
    (why: SessionNotice | null) => {
      epochRef.current += 1;
      setRestoreError(null);
      setNotice(why);
      setIssuedOwnToken(null);
      commit(null);
    },
    [commit],
  );

  const apply = useCallback(
    (me: Me) => {
      lastCheckRef.current = Date.now();
      const current = sessionRef.current;
      // Another account (signed in from another tab) starts like a sign-in.
      const sameUser = current?.user.id === me.user.id;
      const tabMatterId = sameUser ? (current?.currentMatter?.id ?? null) : null;
      const { session: next, moved } = buildSession(me.user, me.matters, tabMatterId);
      if (moved && next.currentMatter) setStoredMatterId(next.currentMatter.id);
      if (!sameUser) setIssuedOwnToken(null);
      // Keep the same object when nothing changed, so consumers do not re-render.
      if (current && sameSession(current, next)) return;
      commit(next);
    },
    [commit],
  );

  const signOutRejected = useCallback(() => {
    saveToken(null, "token_rejected");
    leave(REJECTED);
  }, [leave, saveToken]);

  /** Another tab removed the saved token: leave too, saying why. */
  const signedOutElsewhere = useCallback(() => {
    knownTokenRef.current = getToken();
    if (sessionRef.current === null) return;
    const reason = readSignOutReason();
    const rotation = ownRotationRef.current;
    if (rotation && reason === "token_rejected") {
      // That tab saw the old token refused while this one is still waiting
      // for the new token it asked for: decide once the rotation settles.
      void rotation.then(
        () => undefined,
        () => {
          if (getToken() === null && sessionRef.current) leave(REJECTED);
        },
      );
      return;
    }
    leave(reason === "token_rejected" ? REJECTED : ELSEWHERE);
  }, [leave]);

  const restore = useCallback(async () => {
    for (;;) {
      const epoch = ++epochRef.current;
      const token = getToken();
      knownTokenRef.current = token;
      if (!token) {
        setRestoreError(null);
        commit(null);
        return;
      }
      restoringRef.current += 1;
      commit(undefined);
      try {
        const me = readMe(await api.me());
        if (epoch !== epochRef.current) return;
        setNotice(null);
        setRestoreError(null);
        apply(me);
        return;
      } catch (error) {
        if (epoch !== epochRef.current) return;
        if (isUnauthorized(error)) {
          // Another tab saved another token meanwhile: check that one, as a
          // reload would.
          if (getToken() !== token) continue;
          signOutRejected();
        } else {
          // Keep the token: nothing says it is invalid (ui:18).
          lastCheckRef.current = Date.now();
          setRestoreError(describeFailure(error));
        }
        return;
      } finally {
        restoringRef.current -= 1;
      }
    }
  }, [apply, commit, signOutRejected]);

  useEffect(() => {
    void restore();
  }, [restore]);

  const signIn = useCallback(
    async (token: string) => {
      const epoch = ++epochRef.current;
      const value = token.trim();
      saveToken(value);
      try {
        const me = readMe(await api.me());
        if (epoch !== epochRef.current) return;
        setNotice(null);
        setRestoreError(null);
        apply(me);
      } catch (error) {
        // Unless another tab saved a token meanwhile: that one is not ours to drop.
        if (epoch === epochRef.current && getToken() === value) saveToken(null);
        throw error;
      }
    },
    [apply, saveToken],
  );

  const signOut = useCallback(() => {
    saveToken(null, "signed_out");
    setStoredMatterId(null);
    leave(null);
  }, [leave, saveToken]);

  /** A background /me answered 401: sign out only if it still does a moment
   * later with the same token. */
  const confirmUnauthorized = useCallback(
    (token: string, epoch: number) => {
      if (confirmPendingRef.current) return;
      confirmPendingRef.current = true;
      const timer = window.setTimeout(async () => {
        timersRef.current.delete(timer);
        try {
          // Rotating your own token: the server refuses the old one from its
          // commit until this browser has the new one (identity:2).
          const rotation = ownRotationRef.current;
          if (rotation) await rotation.catch(() => undefined);
          if (epoch !== epochRef.current) return;
          const now = getToken();
          if (now === null) {
            signedOutElsewhere();
            return;
          }
          // Another tab saved a new token: that change is re-read on its own.
          if (now !== token) return;
          const me = readMe(await api.me());
          if (epoch === epochRef.current && getToken() === token) apply(me);
        } catch (error) {
          if (epoch !== epochRef.current) return;
          const now = getToken();
          if (now === null) signedOutElsewhere();
          else if (now === token && isUnauthorized(error)) signOutRejected();
        } finally {
          confirmPendingRef.current = false;
        }
      }, UNAUTHORIZED_CONFIRM_MS);
      timersRef.current.add(timer);
    },
    [apply, signOutRejected, signedOutElsewhere],
  );

  /** Re-read /me for the signed-in session. */
  const recheck = useCallback(async () => {
    if (!sessionRef.current) return;
    const token = getToken();
    if (!token) {
      // Removed by another tab, whose storage event this tab missed.
      signedOutElsewhere();
      return;
    }
    knownTokenRef.current = token;
    const epoch = epochRef.current;
    const seq = ++recheckSeqRef.current;
    lastCheckRef.current = Date.now();
    let me: Me;
    try {
      me = readMe(await api.me());
    } catch (error) {
      if (epoch !== epochRef.current) return;
      const now = getToken();
      if (now === null) {
        signedOutElsewhere();
        return;
      }
      // Another tab saved a new token: that change is re-read on its own.
      if (now !== token) return;
      if (isUnauthorized(error)) {
        confirmUnauthorized(token, epoch);
        return;
      }
      throw error;
    }
    if (epoch === epochRef.current && getToken() === token && seq === recheckSeqRef.current) {
      apply(me);
    }
  }, [apply, confirmUnauthorized, signedOutElsewhere]);

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

  /** Another tab saved a token while this one is signed out, restoring or
   * retrying: follow that sign-in, but only once /me accepts the token. Any
   * other answer leaves this tab as it is: the other tab may still be
   * checking what was typed into its sign-in form, and that token is its own. */
  const followSignIn = useCallback(
    async (token: string) => {
      const epoch = epochRef.current;
      let me: Me;
      try {
        me = readMe(await api.me());
      } catch {
        return;
      }
      if (epoch !== epochRef.current || getToken() !== token || sessionRef.current) return;
      epochRef.current += 1;
      setNotice(null);
      setRestoreError(null);
      apply(me);
    },
    [apply],
  );

  /** localStorage changed in another tab (a `storage` event). */
  const syncStoredToken = useCallback(() => {
    const token = getToken();
    if (token === knownTokenRef.current) return;
    knownTokenRef.current = token;
    if (token === null) signedOutElsewhere();
    else if (sessionRef.current) recheckInBackground(true);
    else void followSignIn(token);
  }, [followSignIn, recheckInBackground, signedOutElsewhere]);

  useEffect(() => {
    const onFocus = () => recheckInBackground(false);
    const onVisibility = () => {
      if (document.visibilityState === "visible") recheckInBackground(false);
    };
    const onOnline = () => recheckInBackground(true);
    // Only the saved token matters here: another tab's matter is its own.
    const onStorage = () => syncStoredToken();
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("online", onOnline);
    window.addEventListener("storage", onStorage);
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
      window.removeEventListener("storage", onStorage);
      window.clearInterval(interval);
      unsubscribe();
      for (const timer of timers) window.clearTimeout(timer);
      timers.clear();
    };
  }, [recheckInBackground, syncStoredToken]);

  const selectMatter = useCallback(
    (matterId: string) => {
      const current = sessionRef.current;
      if (!current) return;
      const matter = current.matters.find((m) => m.id === matterId) ?? null;
      // This tab's choice, and where a new tab, a reload or a sign-in starts.
      setStoredMatterId(matter?.id ?? null);
      commit({ ...current, currentMatter: matter, role: matter?.role ?? null });
    },
    [commit],
  );

  const rotateOwnToken = useCallback((): Promise<IssuedSignIn> => {
    if (ownRotationRef.current) return ownRotationRef.current;
    const current = sessionRef.current;
    if (!current) return Promise.reject(new Error("Sign in to rotate your sign-in token."));
    const userId = current.user.id;
    const rotation = api.rotateSignInToken(userId).then((issued) => {
      if (typeof issued?.sign_in_token !== "string" || issued.sign_in_token === "") {
        throw new Error("The server's answer carried no sign-in token.");
      }
      // The server has replaced the token, so the old one is refused from now
      // on, in this browser too: switch at once, whatever page is open. Not
      // if this tab was signed out, or another account signed in here,
      // meanwhile: then the token is neither used nor shown.
      if (sessionRef.current?.user.id === userId) {
        epochRef.current += 1;
        saveToken(issued.sign_in_token);
        setIssuedOwnToken(issued);
        recheckInBackground(true);
      }
      return issued;
    });
    ownRotationRef.current = rotation;
    // Registered first, so it runs before anyone waiting on the rotation.
    const settled = () => {
      if (ownRotationRef.current === rotation) ownRotationRef.current = null;
    };
    rotation.then(settled, settled);
    return rotation;
  }, [recheckInBackground, saveToken]);

  const acknowledgeIssuedOwnToken = useCallback(() => setIssuedOwnToken(null), []);

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
      rotateOwnToken,
      issuedOwnToken,
      acknowledgeIssuedOwnToken,
    }),
    [
      session,
      signIn,
      signOut,
      selectMatter,
      recheck,
      notice,
      restoreError,
      restore,
      rotateOwnToken,
      issuedOwnToken,
      acknowledgeIssuedOwnToken,
    ],
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
