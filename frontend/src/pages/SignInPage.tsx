// Sign-in — the token-entry gate. The user enters the secret sign-in token
// their administrator gave them (backend/app/auth.py; it is NOT their user
// id, which is public); it is validated via GET /me through
// useSession().signIn. Rendered by App.tsx OUTSIDE the AppShell, so this
// page owns the full viewport: centered card over the design's blurred
// background blobs, no sidebar/topbar. The design's SSO button and
// password field are deliberately absent — nothing backs them.

import { useRef, useState } from "react";
import type { FormEvent } from "react";

import "../styles/pages/sign-in.css";

import { ApiError } from "../api/client";
import { Icon } from "../app/icons";
import { useSession } from "../app/session";

const UNKNOWN_TOKEN_MESSAGE =
  "Unknown sign-in token. Check it, or ask your administrator for a new one.";
const NETWORK_MESSAGE =
  "Could not reach the LexGraph server. Check that the backend is running.";

export function SignInPage() {
  const { signIn, notice, retryRestore } = useSession();
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
      // 4xx = the backend answered and rejected the token; anything else
      // (network failure, proxy/server 5xx) reads as connectivity.
      setError(
        err instanceof ApiError && err.status < 500
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
                {notice.kind === "server_unreachable" && retryRestore && (
                  <button
                    type="button"
                    className="btn btn--sm btn--secondary"
                    onClick={retryRestore}
                  >
                    Try again
                  </button>
                )}
              </div>
            )
          )}

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
