// Session state: who is signed in and which matter is active. Role comes
// from the matter membership, so permission-driven UI (review buttons,
// admin nav) reads session.role.
//
// The stored credential is the user's secret sign-in token
// (backend/app/auth.py). "My id" is always GET /me's PUBLIC user.id
// (session.user.id), never the token. The localStorage key predates sign-in
// tokens; a value saved then (the user id) keeps working as a legacy token
// on an upgraded backend until an admin rotates it.

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import {
  ApiError,
  api,
  getStoredMatterId,
  getToken,
  setStoredMatterId,
  setToken,
} from "../api/client";
import type { MatterMembership, MatterRoleName, UserInfo } from "../api/types";

export interface Session {
  user: UserInfo;
  matters: MatterMembership[];
  currentMatter: MatterMembership | null;
  role: MatterRoleName | null;
}

/** Why a saved sign-in could not be restored (shown on the sign-in page). */
export interface SessionNotice {
  kind: "token_rejected" | "server_unreachable";
  message: string;
}

export const TOKEN_REJECTED_NOTICE =
  "Your saved sign-in token is no longer valid (it may have been rotated). " +
  "Enter your current sign-in token.";
export const SERVER_UNREACHABLE_NOTICE =
  "Could not reach the LexGraph server to restore your session. " +
  "Your saved sign-in token was kept.";

interface SessionContextValue {
  /** undefined = restoring from storage; null = signed out */
  session: Session | null | undefined;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  selectMatter: (matterId: string) => void;
  refresh: () => Promise<void>;
  /** Set when restoring the saved sign-in failed; null otherwise. */
  notice?: SessionNotice | null;
  /** Try restoring the saved sign-in again (after a connectivity failure). */
  retryRestore?: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function buildSession(user: UserInfo, matters: MatterMembership[]): Session {
  const storedId = getStoredMatterId();
  const currentMatter =
    matters.find((m) => m.id === storedId) ?? matters[0] ?? null;
  if (currentMatter) setStoredMatterId(currentMatter.id);
  return { user, matters, currentMatter, role: currentMatter?.role ?? null };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [notice, setNotice] = useState<SessionNotice | null>(null);

  const load = useCallback(async () => {
    const me = await api.me();
    setSession(buildSession(me.user, me.matters));
  }, []);

  const restore = useCallback(() => {
    if (!getToken()) {
      setSession(null);
      return;
    }
    setSession(undefined);
    load().then(
      () => setNotice(null),
      (error: unknown) => {
        if (error instanceof ApiError && error.status < 500) {
          // The server answered and rejected the saved token (rotated,
          // revoked or unknown): drop it.
          setToken(null);
          setNotice({ kind: "token_rejected", message: TOKEN_REJECTED_NOTICE });
        } else {
          // Network failure or 5xx: keep the token, it may still be valid.
          setNotice({ kind: "server_unreachable", message: SERVER_UNREACHABLE_NOTICE });
        }
        setSession(null);
      },
    );
  }, [load]);

  useEffect(() => {
    restore();
  }, [restore]);

  const signIn = useCallback(
    async (token: string) => {
      setToken(token.trim());
      try {
        await load();
        setNotice(null);
      } catch (error) {
        setToken(null);
        throw error;
      }
    },
    [load],
  );

  const signOut = useCallback(() => {
    setToken(null);
    setStoredMatterId(null);
    setNotice(null);
    setSession(null);
  }, []);

  const selectMatter = useCallback((matterId: string) => {
    setSession((current) => {
      if (!current) return current;
      const matter = current.matters.find((m) => m.id === matterId) ?? null;
      setStoredMatterId(matter?.id ?? null);
      return { ...current, currentMatter: matter, role: matter?.role ?? null };
    });
  }, []);

  return (
    <SessionContext.Provider
      value={{
        session,
        signIn,
        signOut,
        selectMatter,
        refresh: load,
        notice,
        retryRestore: restore,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
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
