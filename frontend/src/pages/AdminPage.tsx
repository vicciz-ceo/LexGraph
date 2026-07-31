// AdminPage — per-matter administration. Two sections behind a segmented
// control: "Members & roles" (roster from GET /matters/{id}/members with
// role changes, removal, and an add-by-email flow) and "Review policy"
// (a read-only reference describing the actual review pipeline — there
// are no votes, quorums, or configurable consensus rules to edit).
//
// App.tsx gates the /admin route to the admin role; the component still
// hides mutating controls for non-admins as defense in depth and surfaces
// ApiError 403/409 in a banner without breaking the roster table.

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import "../styles/pages/admin.css";

import { ApiError, api } from "../api/client";
import type { MatterMember, MatterRoleName } from "../api/types";
import { Icon } from "../app/icons";
import { useActiveSession } from "../app/session";

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

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "Your role on this matter no longer permits member management.";
  }
  if (error instanceof Error) return error.message;
  return "The action failed.";
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
              The reviewer sends it back with a comment; a new revision returns it to
              proposed.
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

type AdminTab = "members" | "policy";

export function AdminPage() {
  const session = useActiveSession();
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

  async function runMutation(call: () => Promise<unknown>) {
    setBusy(true);
    setBanner(null);
    try {
      await call();
      if (!aliveRef.current) return;
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
    void runMutation(() => api.setMatterMemberRole(matterId, member.user.id, role));
  }

  function removeMember(member: MatterMember) {
    void runMutation(() => api.removeMatterMember(matterId, member.user.id));
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
          ? "No user account with that email — accounts are provisioned via the seed or DB."
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

      {tab === "members" ? renderMembersPanel() : <ReviewPolicyPanel />}
    </div>
  );
}
