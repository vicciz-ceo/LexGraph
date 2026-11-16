// The one-time display of a sign-in token the API just returned
// (backend/app/auth.py: a token is returned exactly once, when it is
// issued). The admin console shows it for an account it created or rotated.
// The app shell shows it for a rotation of your own token, which the session
// keeps until you click Done, whatever page you are on by the time the
// answer arrives (review identity:2); the sign-in page shows it if you were
// signed out before that (`signedOut`).

import { useState } from "react";

import "../styles/pages/admin.css";

import type { IssuedSignIn } from "../api/types";
import { Icon } from "./icons";

export interface IssuedTokenCalloutProps {
  account: IssuedSignIn;
  reason: "created" | "rotated";
  /** The signed-in user's own token: this browser already signs in with it. */
  self?: boolean;
  /** With `self`: the user is signed out, so this browser does not use it. */
  signedOut?: boolean;
  onDone: () => void;
}

/** Render it with `key` = the token, so the copy state starts over for each one. */
export function IssuedTokenCallout({
  account,
  reason,
  self = false,
  signedOut = false,
  onDone,
}: IssuedTokenCalloutProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const token = account.sign_in_token;

  async function copy() {
    try {
      if (!navigator.clipboard) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(token);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  }

  return (
    <section className="adm-issued" role="status" aria-label="New sign-in token">
      <p className="adm-issued__title">
        <Icon name="warning" size={18} />
        {reason === "created" ? "Account created. " : "New token issued. "}
        Sign-in token for {account.display_name}:
      </p>
      <div className="adm-issued__row">
        <code className="mono adm-issued__token">{token}</code>
        <button type="button" className="btn btn--sm btn--secondary" onClick={() => void copy()}>
          {copyState === "copied" ? (
            <>
              <Icon name="check" size={16} /> Copied
            </>
          ) : (
            "Copy token"
          )}
        </button>
      </div>
      {copyState === "failed" && (
        <p className="adm-add__error">Copy failed — select the token and copy it manually.</p>
      )}
      {self ? (
        <p className="adm-issued__warning">
          Shown only once: copy it now and keep it private. You need it to sign in
          {signedOut ? " again" : " on another device or after signing out"}. Only a hash is
          stored, so it cannot be shown again, and anyone who has it can sign in as you.
        </p>
      ) : (
        <p className="adm-issued__warning">
          Shown only once: copy it now and give it to {account.display_name} privately.
          Only a hash is stored, so it cannot be shown again, and anyone who has it can
          sign in as this account.
        </p>
      )}
      {reason === "rotated" && !self && (
        <p className="muted adm-issued__hint">The previous token no longer works.</p>
      )}
      {self && !signedOut && (
        <p className="muted adm-issued__hint">
          This is your own account: this browser now signs in with the new token, and the
          previous one no longer works anywhere.
        </p>
      )}
      {self && signedOut && (
        <p className="muted adm-issued__hint">
          This is your own new token. You are signed out, so this browser does not use it:
          sign in with it below. The previous token no longer works anywhere.
        </p>
      )}
      {reason === "created" && (
        <p className="muted adm-issued__hint">
          {account.email} was pre-filled into the Members & roles add-member field so you
          can grant it a role next.
        </p>
      )}
      <button type="button" className="btn btn--sm btn--primary" onClick={onDone}>
        Done, I have saved the token
      </button>
    </section>
  );
}
