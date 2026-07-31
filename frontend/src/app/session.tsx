// Session state: who is signed in (test-token seam — the token IS the
// user id) and which matter is active. Role comes from the matter
// membership, so permission-driven UI (review buttons, admin nav) reads
// session.role.

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import {
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

interface SessionContextValue {
  /** undefined = restoring from storage; null = signed out */
  session: Session | null | undefined;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  selectMatter: (matterId: string) => void;
  refresh: () => Promise<void>;
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

  const load = useCallback(async () => {
    const me = await api.me();
    setSession(buildSession(me.user, me.matters));
  }, []);

  useEffect(() => {
    if (!getToken()) {
      setSession(null);
      return;
    }
    load().catch(() => {
      // Stored token no longer resolves to a user — drop it.
      setToken(null);
      setSession(null);
    });
  }, [load]);

  const signIn = useCallback(
    async (token: string) => {
      setToken(token.trim());
      try {
        await load();
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
      value={{ session, signIn, signOut, selectMatter, refresh: load }}
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
