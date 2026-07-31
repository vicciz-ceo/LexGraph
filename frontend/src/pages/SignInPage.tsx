// Sign-in — the token-entry gate for the backend's test-token auth seam
// (the bearer token IS the user id; validated via GET /me through
// useSession().signIn). Rendered by App.tsx OUTSIDE the AppShell, so this
// page owns the full viewport: centered card over the design's blurred
// background blobs, no sidebar/topbar. The design's SSO button and
// password field are deliberately absent — nothing backs them.

import { useRef, useState } from "react";
import type { FormEvent } from "react";

import "../styles/pages/sign-in.css";

import { ApiError } from "../api/client";
import { Icon } from "../app/icons";
import { useSession } from "../app/session";

const UNKNOWN_USER_MESSAGE =
  "Unknown user ID — accounts are provisioned by your administrator.";
const NETWORK_MESSAGE =
  "Could not reach the LexGraph server. Check that the backend is running.";

export function SignInPage() {
  const { signIn } = useSession();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [userId, setUserId] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = userId.trim();
    if (!token || pending) return;
    setPending(true);
    setError(null);
    try {
      await signIn(token);
      // Success: SessionProvider now has a session and App unmounts this
      // page — no state to update here.
    } catch (err) {
      // 4xx = the backend answered and rejected the id; anything else
      // (network failure, proxy/server 5xx) reads as connectivity.
      setError(
        err instanceof ApiError && err.status < 500
          ? UNKNOWN_USER_MESSAGE
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
            Enter your user ID — accounts are provisioned by your administrator.
          </p>

          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}

          <form className="signin__form" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="signin-user-id">User ID</label>
              <div className="signin__input-wrap">
                <Icon name="person" size={18} />
                <input
                  ref={inputRef}
                  id="signin-user-id"
                  className="input"
                  name="userId"
                  type="text"
                  autoComplete="off"
                  spellCheck={false}
                  autoFocus
                  placeholder="e.g. reviewer"
                  value={userId}
                  onChange={(event) => setUserId(event.target.value)}
                />
              </div>
            </div>
            <button
              type="submit"
              className="btn btn--primary signin__submit"
              disabled={pending || userId.trim() === ""}
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
