// The api client reports every request the server refused for the
// caller's credential (401) or permission (403), so the SessionProvider
// can re-read GET /me instead of letting role-gated UI go stale: a token
// rotated or revoked elsewhere then signs the user out, and a role changed
// or removed by another admin reaches the chrome (findings ui:18, ui:19).
//
// A module of its own, not part of client.ts, because page tests replace
// "../../api/client" with a factory that only provides { ApiError, api }.

export interface AuthFailure {
  status: 401 | 403;
  method: string;
  /** API path without the base, e.g. "/me" or "/matters/m-1/members". */
  path: string;
}

type Listener = (failure: AuthFailure) => void;

const listeners = new Set<Listener>();

/** Subscribe; returns the unsubscribe function. */
export function onAuthFailure(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function reportAuthFailure(failure: AuthFailure): void {
  for (const listener of [...listeners]) {
    try {
      listener(failure);
    } catch {
      // A listener must never break the request that reported it.
    }
  }
}
