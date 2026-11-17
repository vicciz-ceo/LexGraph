// Sign-in — the token-entry gate. The user enters the secret sign-in token
// their administrator gave them (backend/app/auth.py; it is NOT their user
// id, which is public); it is validated via GET /me through
// useSession().signIn. Rendered by App.tsx OUTSIDE the AppShell, so this
// page owns the full viewport: centered card over the design's blurred
// background blobs, no sidebar/topbar. The design's SSO button and
// password field are deliberately absent — nothing backs them, and so are
// the design's demo-account quick-fill chips (sprint 2026-07-31-admin-
// provisioning, gate G3: no hardcoded demo accounts in the product).
//
// SessionRetryPage (same card) is shown instead when a saved sign-in could
// not be checked (no response, 5xx, ...): the token is kept, so the user is
// not presented as signed out (finding ui:18).
//
// `children` go above the form: App puts there the new token of your own
// rotation when you were signed out before saving it (review identity:2).

import { useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import "../styles/pages/sign-in.css";

import { ApiError } from "../api/client";
import { Icon } from "../app/icons";
import { useSession } from "../app/session";

const UNKNOWN_TOKEN_MESSAGE =
  "Unknown sign-in token. Check it, or ask your administrator for a new one.";
const NETWORK_MESSAGE =
  "Could not reach the LexGraph server. Check that the backend is running.";

export function SignInPage({ children }: { children?: ReactNode } = {}) {
  const { signIn, notice } = useSession();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [token, setToken] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = token.trim();
    if (!value || pending) return;
    setPending(true);
    setError(null);
    try {
      await signIn(value);
      // Success: SessionProvider now has a session and App unmounts this
      // page — no state to update here.
    } catch (err) {
      // Only a 401 says the token is unknown: GET /me answers nothing else
      // for a bad token. Anything else (no response, a 5xx, a misrouted
      // proxy's 404, a 429) reads as connectivity, as on restore (ui:18).
      setError(
        err instanceof ApiError && err.status === 401
          ? UNKNOWN_TOKEN_MESSAGE
          : NETWORK_MESSAGE,
      );
      setPending(false);
    }
  }

  return (
    <div className="signin">
      <div className="signin__blob signin__blob--primary" aria-hidden="true" />
      <div className="signin__blob signin__blob--tertiary" aria-hidden="true" />

      <main className="signin__content">
        <section className="signin__card" aria-labelledby="signin-title">
          <div className="signin__logo" aria-hidden="true">
            <Icon name="link" size={26} />
          </div>
          <h1 id="signin-title" className="signin__title">
            LexGraph
          </h1>
          <p className="signin__subtitle">
            Enter your sign-in token — accounts are provisioned by your administrator.
          </p>

          {error ? (
            <div className="error-banner" role="alert">
              {error}
            </div>
          ) : (
            notice && (
              <div className="signin__notice" role="status">
                <span>{notice.message}</span>
              </div>
            )
          )}

          {children}

          <form className="signin__form" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="signin-token">Sign-in token</label>
              <div className="signin__input-wrap">
                <Icon name="person" size={18} />
                <input
                  ref={inputRef}
                  id="signin-token"
                  className="input"
                  name="signInToken"
                  type="password"
                  autoComplete="current-password"
                  spellCheck={false}
                  autoFocus
                  placeholder="Paste your sign-in token"
                  aria-describedby="signin-token-hint"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
              </div>
              <p id="signin-token-hint" className="signin__hint">
                Your user id is not your sign-in token. Lost the token? An
                administrator can issue a new one.
              </p>
            </div>
            <button
              type="submit"
              className="btn btn--primary signin__submit"
              disabled={pending || token.trim() === ""}
            >
              {pending ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </section>
      </main>

      <span className="signin__env">
        <span className="signin__env-dot" aria-hidden="true" />
        Self-hosted · LexGraph
      </span>
    </div>
  );
}

/** A saved sign-in could not be checked: keep it and offer a retry. */
export function SessionRetryPage() {
  const { restoreError, retryRestore, signOut } = useSession();
  const [pending, setPending] = useState(false);

  async function retry() {
    if (!retryRestore || pending) return;
    setPending(true);
    try {
      await retryRestore();
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="signin">
      <div className="signin__blob signin__blob--primary" aria-hidden="true" />
      <div className="signin__blob signin__blob--tertiary" aria-hidden="true" />

      <main className="signin__content">
        <section className="signin__card" aria-labelledby="signin-retry-title">
          <div className="signin__logo" aria-hidden="true">
            <Icon name="link" size={26} />
          </div>
          <h1 id="signin-retry-title" className="signin__title">
            LexGraph
          </h1>
          <div className="error-banner signin__retry-alert" role="alert">
            <p>
              Could not reach the LexGraph server to restore your session. Check that
              the backend is running.
            </p>
            {restoreError && <p className="signin__retry-detail">{restoreError}</p>}
          </div>
          <p className="signin__subtitle">
            Your sign-in is still saved on this device: you will not need your token
            again once the server is back.
          </p>
          <div className="signin__actions">
            <button
              type="button"
              className="btn btn--primary signin__submit"
              disabled={pending}
              onClick={() => void retry()}
            >
              {pending ? "Retrying…" : "Retry"}
            </button>
            <button type="button" className="btn btn--ghost" onClick={signOut}>
              Sign in with a different token
            </button>
          </div>
        </section>
      </main>

      <span className="signin__env">
        <span className="signin__env-dot" aria-hidden="true" />
        Self-hosted · LexGraph
      </span>
    </div>
  );
}
