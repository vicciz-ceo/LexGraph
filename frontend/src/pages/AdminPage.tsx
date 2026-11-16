// AdminPage — per-matter administration. Two sections behind a segmented
// control: "Members & roles" (roster from GET /matters/{id}/members with
// role changes, removal, and an add-by-email flow) and "Review policy"
// (a read-only reference describing the actual review pipeline — there
// are no votes, quorums, or configurable consensus rules to edit).
//
// App.tsx gates the /admin route to the admin role; the component still
// hides mutating controls for non-admins as defense in depth and surfaces
// ApiError 403/409 in a banner without breaking the roster table.
//
// User accounts tab: sign-in tokens (backend/app/auth.py) are secrets the
// API returns exactly once — on account creation and on rotation. This page
// shows such a token once, with a copy button and a warning, and forgets
// it when the admin clicks Done. User ids are public references, never
// credentials. Accounts still signing in with their public id (legacy,
// from the upgrade migration) get a badge and a rotate action.

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import "../styles/pages/admin.css";

import { ApiError, api } from "../api/client";
import type {
  IssuedSignIn,
  MatterMember,
  MatterRoleName,
  SignInStatus,
  UserAccount,
} from "../api/types";
import { Icon } from "../app/icons";
import { navigate } from "../app/router";
import { useActiveSession, useSession } from "../app/session";

const ROLE_OPTIONS: MatterRoleName[] = ["viewer", "contributor", "reviewer", "admin"];

const ROLE_LABELS: Record<MatterRoleName, string> = {
  viewer: "Viewer",
  contributor: "Contributor",
  reviewer: "Reviewer",
  admin: "Admin",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1][0] ?? "") : "";
  return (first + last).toUpperCase();
}

const ACCESS_CHANGED_MESSAGE =
  "Your access to this matter changed. Reload the page to continue.";

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "Your role on this matter no longer permits member management.";
  }
  if (error instanceof Error) return error.message;
  return "The action failed.";
}

/** User-accounts tab error copy — global (admin-on-any-matter), not
 * matter-scoped, so it doesn't reuse describeError's 403 copy above. The
 * backend's ApiError.message already carries the right detail text (409
 * duplicate email, 422 invalid email/blank name, 403 no admin role
 * anywhere). */
function describeAccountError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "The action failed.";
}

const SIGN_IN_BADGES: Record<SignInStatus, { label: string; className: string; title: string }> = {
  active: {
    label: "Active",
    className: "badge badge--accepted",
    title: "Signs in with a generated sign-in token.",
  },
  legacy: {
    label: "Legacy sign-in",
    className: "badge badge--pending",
    title:
      "Still signs in with its public user id, which other members can see. Rotate its token.",
  },
  none: {
    label: "No token",
    className: "badge badge--neutral",
    title: "Has no sign-in token yet, so it cannot sign in. Issue one.",
  },
};

/** A token the API just returned (shown once, then forgotten on Done). */
interface IssuedToken {
  account: IssuedSignIn;
  reason: "created" | "rotated";
  /** The signed-in admin rotated their own token. */
  self: boolean;
  /** Set when this browser could not switch to a self-rotated token. */
  sessionError?: boolean;
}

/** Allowed / not-allowed cell for the role capability matrix. */
function MatrixCell({ allowed }: { allowed: boolean }) {
  return (
    <td className="adm-matrix__cell">
      {allowed ? (
        <span role="img" aria-label="Allowed" className="adm-matrix__yes">
          <Icon name="check" size={16} />
        </span>
      ) : (
        <span aria-label="Not allowed" className="muted">
          —
        </span>
      )}
    </td>
  );
}

const PERMISSION_ROWS: { permission: string; from: MatterRoleName }[] = [
  { permission: "Read assertions, evidence spans & the matter graph", from: "viewer" },
  { permission: "Suggest assertions, rate strength (1–5), comment", from: "contributor" },
  {
    permission: "Review decisions: accept, reject, dispute, request revision, supersede",
    from: "reviewer",
  },
  { permission: "Manage matter members & roles", from: "admin" },
];

const ROLE_RANK: Record<MatterRoleName, number> = {
  viewer: 0,
  contributor: 1,
  reviewer: 2,
  admin: 3,
};

function ReviewPolicyPanel() {
  return (
    <div className="adm-policy">
      <section className="card">
        <header className="card__header">Review pipeline</header>
        <div className="card__body">
          <ol className="adm-pipeline">
            <li>
              <span className="badge badge--draft">Draft</span> The author composes the
              assertion and links evidence spans from the matter's sources.
            </li>
            <li>
              <span className="badge badge--proposed">Proposed</span> Submitting sends it to
              review. Colleagues rate its strength and comment while it waits.
            </li>
            <li>
              <span className="badge badge--accepted">Accepted</span>{" "}
              <span className="badge badge--rejected">Rejected</span> A reviewer or admin
              rules on it — always an explicit decision by a named person, never an
              automatic outcome.
            </li>
            <li>
              <span className="badge badge--revision_requested">Revision requested</span>{" "}
              The reviewer sends it back with a comment; once the author revises it and
              submits it for review again, it returns to proposed.
            </li>
            <li>
              <span className="badge badge--disputed">Disputed</span> A reviewer flags a
              disagreement; the assertion moves to the Contested queue for adjudication.
            </li>
            <li>
              <span className="badge badge--superseded">Superseded</span>{" "}
              <span className="badge badge--withdrawn">Withdrawn</span> An accepted
              assertion can later be superseded by a newer one; authors may withdraw
              their own before a ruling.
            </li>
          </ol>
        </div>
      </section>

      <section className="card">
        <header className="card__header">Ratings, confidence & status</header>
        <div className="card__body">
          <p>Three separate signals, never merged into one indicator:</p>
          <ul className="adm-bullets">
            <li>
              <strong>Strength ratings</strong> — colleagues rate each revision 1–5 with an
              optional rationale. While an assertion is proposed, the aggregate informs its
              derived standing (weak / probable / strong).
            </li>
            <li>
              <strong>Model confidence</strong> — a percentage reported only for AI-deduced
              assertions.
            </li>
            <li>
              <strong>Review status</strong> — the reviewer's decision in the pipeline
              above.
            </li>
          </ul>
          <p>
            Ratings never change review status, and there are no votes or quorums —
            acceptance is always a reviewer's ruling.
          </p>
        </div>
      </section>

      <section className="card">
        <header className="card__header">Unsupported evidence</header>
        <div className="card__body">
          <p>
            Every assertion carries an evidence status:{" "}
            <span className="badge badge--accepted">Evidenced</span>,{" "}
            <span className="badge badge--pending">Awaiting evidence</span> or{" "}
            <span className="badge badge--rejected">Unsupported</span>.
          </p>
          <p>
            Accepting an assertion that documentary evidence does not support requires the
            reviewer to record an acceptance justification. The justification is kept in
            the assertion's history.
          </p>
        </div>
      </section>

      <section className="card">
        <header className="card__header">Roles on a matter</header>
        <div className="card__body">
          <p className="muted">
            Roles are granted per matter, not globally — the same account can be a
            reviewer on one matter and a viewer on another.
          </p>
          <div className="table-wrap">
            <table className="table adm-matrix">
              <thead>
                <tr>
                  <th>Permission</th>
                  {ROLE_OPTIONS.map((role) => (
                    <th key={role} className="adm-matrix__role">
                      {ROLE_LABELS[role]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PERMISSION_ROWS.map((row) => (
                  <tr key={row.permission}>
                    <td>{row.permission}</td>
                    {ROLE_OPTIONS.map((role) => (
                      <MatrixCell
                        key={role}
                        allowed={ROLE_RANK[role] >= ROLE_RANK[row.from]}
                      />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

type AdminTab = "members" | "accounts" | "policy";

export function AdminPage() {
  const session = useActiveSession();
  const { signIn, refresh: refreshSession } = useSession();
  const matterId = session.currentMatter.id;
  const canManage = session.role === "admin";

  const [tab, setTab] = useState<AdminTab>("members");
  const [members, setMembers] = useState<MatterMember[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  /** Mutation error surfaced above the table (409 last-admin, 403, …). */
  const [banner, setBanner] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [addEmail, setAddEmail] = useState("");
  const [addRole, setAddRole] = useState<MatterRoleName>("contributor");
  const [addError, setAddError] = useState<string | null>(null);

  // --- User accounts tab (B2/UI1) ----------------------------------------
  const [accounts, setAccounts] = useState<UserAccount[] | null>(null);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [accountsReloadKey, setAccountsReloadKey] = useState(0);
  const [newAccountEmail, setNewAccountEmail] = useState("");
  const [newAccountName, setNewAccountName] = useState("");
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [issued, setIssued] = useState<IssuedToken | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  /** Account whose token rotation awaits confirmation. */
  const [pendingRotation, setPendingRotation] = useState<string | null>(null);
  const [rotateBusy, setRotateBusy] = useState(false);
  const [rotateError, setRotateError] = useState<string | null>(null);

  const aliveRef = useRef(true);
  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setMembers(null);
    setLoadError(null);
    setBanner(null);
    api.listMatterMembers(matterId).then(
      (res) => {
        if (!cancelled) setMembers(res);
      },
      (error: unknown) => {
        if (cancelled) return;
        setLoadError(
          error instanceof Error ? error.message : "Failed to load the member roster.",
        );
      },
    );
    return () => {
      cancelled = true;
    };
  }, [matterId, reloadKey]);

  /** Re-fetch the roster in place (no loading flash) after a mutation. */
  const refresh = useCallback(async () => {
    const res = await api.listMatterMembers(matterId);
    if (aliveRef.current) setMembers(res);
  }, [matterId]);

  // Accounts are global (not per-matter), so only fetch them once the
  // admin actually opens the tab -- and never for non-admins, who never
  // see the tab button in the first place (defense in depth).
  useEffect(() => {
    if (tab !== "accounts" || !canManage) return;
    let cancelled = false;
    setAccounts(null);
    setAccountsError(null);
    api.listUsers().then(
      (res) => {
        if (!cancelled) setAccounts(res);
      },
      (error: unknown) => {
        if (cancelled) return;
        setAccountsError(
          error instanceof Error ? error.message : "Failed to load user accounts.",
        );
      },
    );
    return () => {
      cancelled = true;
    };
  }, [tab, canManage, accountsReloadKey]);

  async function submitCreateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = newAccountEmail.trim();
    const displayName = newAccountName.trim();
    if (email === "" || displayName === "") return;
    setCreateBusy(true);
    setCreateError(null);
    try {
      const created = await api.createUser(email, displayName);
      if (!aliveRef.current) return;
      setIssued({ account: created, reason: "created", self: false });
      setCopyState("idle");
      setNewAccountEmail("");
      setNewAccountName("");
      // Wiring: hand the new account straight to the Members & roles tab's
      // add-by-email field so granting it a role is the very next step.
      setAddEmail(created.email);
      setAccountsReloadKey((k) => k + 1);
    } catch (error) {
      if (!aliveRef.current) return;
      setCreateError(describeAccountError(error));
    } finally {
      if (aliveRef.current) setCreateBusy(false);
    }
  }

  async function rotateToken(account: UserAccount) {
    setPendingRotation(null);
    setRotateBusy(true);
    setRotateError(null);
    try {
      const rotated = await api.rotateSignInToken(account.id);
      if (!aliveRef.current) return;
      const self = account.id === session.user.id;
      let sessionError = false;
      if (self) {
        // The old token stopped working, including in this browser: switch
        // the session to the new one so the admin stays signed in.
        try {
          await signIn(rotated.sign_in_token);
        } catch {
          sessionError = true;
        }
        if (!aliveRef.current) return;
      }
      setIssued({ account: rotated, reason: "rotated", self, sessionError });
      setCopyState("idle");
      setAccountsReloadKey((k) => k + 1);
    } catch (error) {
      if (!aliveRef.current) return;
      setRotateError(describeAccountError(error));
    } finally {
      if (aliveRef.current) setRotateBusy(false);
    }
  }

  async function copyIssuedToken(token: string) {
    try {
      if (!navigator.clipboard) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(token);
      if (aliveRef.current) setCopyState("copied");
    } catch {
      if (aliveRef.current) setCopyState("failed");
    }
  }

  /** `affectsSelf`: the mutation targets the signed-in admin's own membership. */
  async function runMutation(call: () => Promise<unknown>, affectsSelf = false) {
    setBusy(true);
    setBanner(null);
    try {
      await call();
      if (!aliveRef.current) return;
      if (affectsSelf) {
        // Changing your own role or membership succeeded, so you are no
        // longer an admin of this matter (finding ui:19): re-read the
        // session so role-gated UI everywhere follows, and leave this page.
        // Re-fetching the roster here would read the old matter, which you
        // may no longer see (a 403 reported as if the removal had failed).
        try {
          await refreshSession();
        } catch {
          if (aliveRef.current) setBanner(ACCESS_CHANGED_MESSAGE);
          return;
        }
        navigate("/review");
        return;
      }
      await refresh();
    } catch (error) {
      if (!aliveRef.current) return;
      setBanner(describeError(error));
    } finally {
      if (aliveRef.current) setBusy(false);
    }
  }

  function changeRole(member: MatterMember, role: MatterRoleName) {
    if (role === member.role) return;
    void runMutation(
      () => api.setMatterMemberRole(matterId, member.user.id, role),
      member.user.id === session.user.id,
    );
  }

  function removeMember(member: MatterMember) {
    void runMutation(
      () => api.removeMatterMember(matterId, member.user.id),
      member.user.id === session.user.id,
    );
  }

  async function submitAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = addEmail.trim();
    if (email === "") return;
    setBusy(true);
    setAddError(null);
    setBanner(null);
    try {
      await api.addMatterMember(matterId, email, addRole);
      if (!aliveRef.current) return;
      setAddEmail("");
      await refresh();
    } catch (error) {
      if (!aliveRef.current) return;
      setAddError(
        error instanceof ApiError && error.status === 404
          ? "No user account with that email — create it first under User accounts."
          : describeError(error),
      );
    } finally {
      if (aliveRef.current) setBusy(false);
    }
  }

  function renderMembersPanel() {
    if (loadError) {
      return (
        <div className="error-banner">
          {loadError}{" "}
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={() => setReloadKey((k) => k + 1)}
          >
            Retry
          </button>
        </div>
      );
    }
    if (members === null) {
      return <div className="loading">Loading members…</div>;
    }
    if (members.length === 0) {
      return (
        <div className="empty-state">
          <p className="empty-state__title">No members</p>
          <p>This matter has no member roster to show.</p>
        </div>
      );
    }
    return (
      <>
        {banner && <div className="error-banner">{banner}</div>}
        <div className="card">
          <div className="table-wrap">
            <table className="table adm-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th className="adm-role-col">Role in this matter</th>
                  {canManage && <th className="adm-actions-col" aria-label="Actions" />}
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.user.id}>
                    <td>
                      <div className="adm-member">
                        <span className="avatar">{initials(member.user.display_name)}</span>
                        <div className="adm-member__id">
                          <span className="adm-member__name">
                            {member.user.display_name}
                            {member.user.id === session.user.id && (
                              <span className="chip chip--tag adm-you">You</span>
                            )}
                          </span>
                          <span className="muted adm-member__email">{member.user.email}</span>
                        </div>
                      </div>
                    </td>
                    <td className="adm-role-col">
                      {canManage ? (
                        <select
                          className="select adm-role-select"
                          value={member.role}
                          disabled={busy}
                          aria-label={`Role for ${member.user.display_name}`}
                          onChange={(event) =>
                            changeRole(member, event.target.value as MatterRoleName)
                          }
                        >
                          {ROLE_OPTIONS.map((role) => (
                            <option key={role} value={role}>
                              {ROLE_LABELS[role]}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="adm-role-label">{ROLE_LABELS[member.role]}</span>
                      )}
                    </td>
                    {canManage && (
                      <td className="adm-actions-col">
                        <button
                          type="button"
                          className="btn btn--danger-outline btn--sm"
                          disabled={busy}
                          aria-label={`Remove ${member.user.display_name}`}
                          onClick={() => removeMember(member)}
                        >
                          Remove
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {canManage ? (
          <form className="card adm-add" onSubmit={(event) => void submitAdd(event)}>
            <header className="card__header">Add member</header>
            <div className="card__body">
              <p className="muted adm-add__hint">
                Grant an existing account a role on this matter.
              </p>
              <div className="adm-add__row">
                <input
                  className="input"
                  type="email"
                  placeholder="colleague@firm.example"
                  aria-label="Email of the account to add"
                  value={addEmail}
                  onChange={(event) => setAddEmail(event.target.value)}
                />
                <select
                  className="select"
                  aria-label="Role for the new member"
                  value={addRole}
                  onChange={(event) => setAddRole(event.target.value as MatterRoleName)}
                >
                  {ROLE_OPTIONS.map((role) => (
                    <option key={role} value={role}>
                      {ROLE_LABELS[role]}
                    </option>
                  ))}
                </select>
                <button
                  type="submit"
                  className="btn btn--primary"
                  disabled={busy || addEmail.trim() === ""}
                >
                  Add
                </button>
              </div>
              {addError && <p className="adm-add__error">{addError}</p>}
            </div>
          </form>
        ) : (
          <p className="adm-note">Matter admin role required to manage members.</p>
        )}
      </>
    );
  }

  function renderAccountsPanel() {
    // The one-time token stays visible while the account list reloads.
    return (
      <>
        {issued && renderIssuedToken(issued)}
        {renderAccountsList()}
      </>
    );
  }

  function renderAccountsList() {
    if (accountsError) {
      return (
        <div className="error-banner">
          {accountsError}{" "}
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={() => setAccountsReloadKey((k) => k + 1)}
          >
            Retry
          </button>
        </div>
      );
    }
    if (accounts === null) {
      return <div className="loading">Loading user accounts…</div>;
    }
    const legacyCount = accounts.filter((a) => a.sign_in_status === "legacy").length;
    return (
      <>
        {legacyCount > 0 && (
          <div className="adm-legacy-banner" role="note">
            <Icon name="warning" size={18} />
            <span>
              {legacyCount === 1
                ? "1 account still signs in with its public user id"
                : `${legacyCount} accounts still sign in with their public user id`}{" "}
              — a legacy credential that anyone who can see the id could use. Rotate
              each token and hand the new one to its owner.
            </span>
          </div>
        )}
        {rotateError && <div className="error-banner">{rotateError}</div>}
        <div className="card">
          <div className="table-wrap">
            <table className="table adm-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th className="adm-id-col">User id (public)</th>
                  <th className="adm-signin-col">Sign-in</th>
                  <th className="adm-token-col" aria-label="Sign-in token actions" />
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => {
                  const badge = SIGN_IN_BADGES[account.sign_in_status] ?? SIGN_IN_BADGES.none;
                  const verb = account.sign_in_status === "none" ? "Issue" : "Rotate";
                  return (
                    <tr key={account.id}>
                      <td>
                        <div className="adm-member">
                          <span className="avatar">{initials(account.display_name)}</span>
                          <div className="adm-member__id">
                            <span className="adm-member__name">
                              {account.display_name}
                              {account.id === session.user.id && (
                                <span className="chip chip--tag adm-you">You</span>
                              )}
                            </span>
                            <span className="muted adm-member__email">{account.email}</span>
                          </div>
                        </div>
                      </td>
                      <td className="mono adm-id-col">{account.id}</td>
                      <td className="adm-signin-col">
                        <span className={badge.className} title={badge.title}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="adm-token-col">
                        {pendingRotation === account.id ? (
                          <div className="adm-rotate-confirm">
                            {account.sign_in_status !== "none" && (
                              <span className="muted">Current token stops working.</span>
                            )}
                            <button
                              type="button"
                              className="btn btn--sm btn--primary"
                              disabled={rotateBusy}
                              aria-label={`Confirm new sign-in token for ${account.display_name}`}
                              onClick={() => void rotateToken(account)}
                            >
                              {verb}
                            </button>
                            <button
                              type="button"
                              className="btn btn--sm btn--ghost"
                              disabled={rotateBusy}
                              onClick={() => setPendingRotation(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn btn--sm btn--secondary"
                            disabled={rotateBusy}
                            aria-label={`${verb} sign-in token for ${account.display_name}`}
                            onClick={() => {
                              setRotateError(null);
                              setPendingRotation(account.id);
                            }}
                          >
                            {verb} token
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <form className="card adm-add" onSubmit={(event) => void submitCreateAccount(event)}>
          <header className="card__header">Create account</header>
          <div className="card__body">
            <p className="muted adm-add__hint">
              Creates the account and a one-time sign-in token to hand to its owner.
              User ids are public references; only the token signs in.
            </p>
            <div className="adm-add__row">
              <input
                className="input"
                type="email"
                placeholder="colleague@firm.example"
                aria-label="Email for the new account"
                value={newAccountEmail}
                onChange={(event) => setNewAccountEmail(event.target.value)}
              />
              <input
                className="input"
                type="text"
                placeholder="Full name"
                aria-label="Display name for the new account"
                value={newAccountName}
                onChange={(event) => setNewAccountName(event.target.value)}
              />
              <button
                type="submit"
                className="btn btn--primary"
                disabled={
                  createBusy ||
                  newAccountEmail.trim() === "" ||
                  newAccountName.trim() === ""
                }
              >
                Create account
              </button>
            </div>
            {createError && <p className="adm-add__error">{createError}</p>}
          </div>
        </form>
      </>
    );
  }

  /** The one-time display of a token the API just returned. */
  function renderIssuedToken({ account, reason, self, sessionError }: IssuedToken) {
    const token = account.sign_in_token;
    return (
      <section className="adm-issued" role="status" aria-label="New sign-in token">
        <p className="adm-issued__title">
          <Icon name="warning" size={18} />
          {reason === "created" ? "Account created. " : "New token issued. "}
          Sign-in token for {account.display_name}:
        </p>
        <div className="adm-issued__row">
          <code className="mono adm-issued__token">{token}</code>
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={() => void copyIssuedToken(token)}
          >
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
        <p className="adm-issued__warning">
          Shown only once: copy it now and give it to {account.display_name} privately.
          Only a hash is stored, so it cannot be shown again, and anyone who has it can
          sign in as this account.
        </p>
        {reason === "rotated" && !self && (
          <p className="muted adm-issued__hint">The previous token no longer works.</p>
        )}
        {self && !sessionError && (
          <p className="muted adm-issued__hint">
            This is your own account: this browser now signs in with the new token.
          </p>
        )}
        {self && sessionError && (
          <p className="adm-add__error">
            This browser could not switch to the new token. Copy it, then sign out and
            sign in with it.
          </p>
        )}
        {reason === "created" && (
          <p className="muted adm-issued__hint">
            {account.email} was pre-filled into the Members & roles add-member field
            so you can grant it a role next.
          </p>
        )}
        <button
          type="button"
          className="btn btn--sm btn--primary"
          onClick={() => {
            setIssued(null);
            setCopyState("idle");
          }}
        >
          Done, I have saved the token
        </button>
      </section>
    );
  }

  return (
    <div className="adm-page">
      <header className="page-header">
        <div>
          <h1 className="page-header__title">
            Matter administration
            {members !== null && (
              <span className="page-header__count">{members.length}</span>
            )}
          </h1>
          <p className="page-header__subtitle">
            Members, roles and review policy for {session.currentMatter.name}
            {members !== null &&
              ` · ${members.length} ${members.length === 1 ? "member" : "members"}`}
            .
          </p>
        </div>
      </header>

      <div className="adm-tabs" role="tablist" aria-label="Administration sections">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "members"}
          className={tab === "members" ? "adm-tab adm-tab--active" : "adm-tab"}
          onClick={() => setTab("members")}
        >
          Members & roles
        </button>
        {canManage && (
          <button
            type="button"
            role="tab"
            aria-selected={tab === "accounts"}
            className={tab === "accounts" ? "adm-tab adm-tab--active" : "adm-tab"}
            onClick={() => setTab("accounts")}
          >
            User accounts
          </button>
        )}
        <button
          type="button"
          role="tab"
          aria-selected={tab === "policy"}
          className={tab === "policy" ? "adm-tab adm-tab--active" : "adm-tab"}
          onClick={() => setTab("policy")}
        >
          Review policy
        </button>
      </div>

      {tab === "members" && renderMembersPanel()}
      {tab === "accounts" && canManage && renderAccountsPanel()}
      {tab === "policy" && <ReviewPolicyPanel />}
    </div>
  );
}
