// ProfilePage — the signed-in user's activity within the current matter.
//
// Adapts the Consensus "My Profile & Activity" design to LexGraph's real
// model: no expertise chips, no vote weighting, no binary approve/reject.
// Stats and lists derive client-side from the matter's assertions filtered
// by author_user_id; "Awaiting my rating" uses the unrated_by_me filter.
// The three signals stay separate: 1-5 strength ratings, model confidence
// (percent, model_suggested only), and reviewer-gated status.

import { useEffect, useState } from "react";

import "../styles/pages/profile.css";

import { api } from "../api/client";
import type { AppNotification, Assertion, AssertionList } from "../api/types";
import { Icon } from "../app/icons";
import type { IconName } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";

function defaultJurisdictionKey(userId: string): string {
  return `lexgraph:default-jurisdiction:${userId}`;
}

const ORIGIN_CHIPS: Record<Assertion["origin"], { className: string; label: string }> = {
  user_suggested: { className: "chip chip--user", label: "Colleague" },
  model_suggested: { className: "chip chip--model", label: "AI-deduced" },
  system_generated: { className: "chip chip--system", label: "System" },
};

const STATUS_LABELS: Record<Assertion["status"], string> = {
  draft: "Draft",
  proposed: "Proposed",
  revision_requested: "Revision requested",
  accepted: "Accepted",
  rejected: "Rejected",
  disputed: "Disputed",
  superseded: "Superseded",
  withdrawn: "Withdrawn",
};

const STANDING_GRADES = ["weak", "probable", "strong"];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

function humanizeEvent(eventType: string): string {
  const label = eventType.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

interface StatCardProps {
  label: string;
  icon: IconName;
  value: string;
  caption: string;
  testId: string;
}

function StatCard({ label, icon, value, caption, testId }: StatCardProps) {
  return (
    <div className="card pf-stat">
      <div className="pf-stat__top">
        <span className="pf-stat__label">{label}</span>
        <Icon name={icon} size={18} />
      </div>
      <span className="pf-stat__value" data-testid={testId}>
        {value}
      </span>
      <span className="pf-stat__caption">{caption}</span>
    </div>
  );
}

type TabId = "awaiting" | "suggestions" | "notifications";

export function ProfilePage() {
  const session = useActiveSession();
  const matterId = session.currentMatter.id;
  const userId = session.user.id;
  const canRate =
    session.role === "contributor" ||
    session.role === "reviewer" ||
    session.role === "admin";

  const [defaultJurisdiction, setDefaultJurisdiction] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(defaultJurisdictionKey(userId)) ?? "";
  });

  const handleDefaultJurisdictionChange = (value: string) => {
    setDefaultJurisdiction(value);
    window.localStorage.setItem(defaultJurisdictionKey(userId), value);
  };

  const [matterAssertions, setMatterAssertions] = useState<Assertion[] | null>(null);
  const [awaiting, setAwaiting] = useState<AssertionList | null>(null);
  const [notifications, setNotifications] = useState<
    AppNotification[] | "error" | null
  >(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>(canRate ? "awaiting" : "suggestions");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setMatterAssertions(null);
    setAwaiting(null);
    setNotifications(null);
    setLoadError(null);
    setActiveTab(canRate ? "awaiting" : "suggestions");

    const loads: [Promise<AssertionList>, Promise<AssertionList>] = [
      api.listAssertions(matterId, {}),
      canRate
        ? api.listAssertions(matterId, { status: "proposed", unrated_by_me: true })
        : Promise.resolve({ items: [], total: 0 }),
    ];
    Promise.all(loads).then(
      ([all, unrated]) => {
        if (cancelled) return;
        setMatterAssertions(all.items);
        setAwaiting(unrated);
      },
      (error: unknown) => {
        if (cancelled) return;
        setLoadError(
          error instanceof Error ? error.message : "Failed to load your activity.",
        );
      },
    );

    api.notifications().then(
      (items) => {
        if (cancelled) return;
        setNotifications(
          [...items].sort((a, b) => b.created_at.localeCompare(a.created_at)),
        );
      },
      () => {
        if (!cancelled) setNotifications("error");
      },
    );

    return () => {
      cancelled = true;
    };
  }, [matterId, canRate, reloadKey]);

  const authored =
    matterAssertions === null
      ? null
      : matterAssertions
          .filter((a) => a.author_user_id === userId)
          .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  const acceptedCount = authored?.filter((a) => a.status === "accepted").length ?? 0;
  const rejectedCount = authored?.filter((a) => a.status === "rejected").length ?? 0;
  const decidedCount = acceptedCount + rejectedCount;
  const acceptancePct =
    decidedCount > 0 ? Math.round((acceptedCount / decidedCount) * 100) : null;

  function renderAwaiting() {
    if (awaiting === null) return null;
    if (awaiting.items.length === 0) {
      return (
        <div className="empty-state">
          <p className="empty-state__title">All caught up</p>
          <p>
            No proposed assertions are waiting for your rating in{" "}
            {session.currentMatter.name}.
          </p>
        </div>
      );
    }
    return (
      <ul className="pf-list">
        {awaiting.items.map((assertion) => {
          const origin = ORIGIN_CHIPS[assertion.origin];
          const metaParts = [
            assertion.assertion_type,
            assertion.jurisdiction,
            `submitted ${formatDate(assertion.submitted_at)}`,
          ].filter(Boolean) as string[];
          if (assertion.origin === "model_suggested" && assertion.confidence !== null) {
            metaParts.push(`model confidence ${Math.round(assertion.confidence * 100)}%`);
          }
          return (
            <li key={assertion.id} className="pf-item">
              <div className="pf-item__main">
                <Link to={`/assertions/${assertion.id}`} className="pf-item__prop">
                  {assertion.proposition}
                </Link>
                <div className="pf-item__meta">
                  <span className={origin.className}>{origin.label}</span>
                  <span className="pf-item__meta-text">{metaParts.join(" · ")}</span>
                </div>
              </div>
              <Link
                to={`/assertions/${assertion.id}`}
                className="btn btn--primary btn--sm pf-item__cta"
              >
                Rate
              </Link>
            </li>
          );
        })}
      </ul>
    );
  }

  function renderSuggestions() {
    if (authored === null) return null;
    if (authored.length === 0) {
      return (
        <div className="empty-state">
          <p className="empty-state__title">No suggestions yet</p>
          <p>Assertions you author in this matter appear here.</p>
          {canRate && (
            <p className="pf-empty-cta">
              <Link to="/suggest" className="btn btn--primary btn--sm">
                Suggest an assertion
              </Link>
            </p>
          )}
        </div>
      );
    }
    return (
      <ul className="pf-list">
        {authored.map((assertion) => {
          const showStanding =
            assertion.status === "proposed" &&
            STANDING_GRADES.includes(assertion.standing);
          return (
            <li key={assertion.id} className="pf-item">
              <div className="pf-item__main">
                <Link to={`/assertions/${assertion.id}`} className="pf-item__prop">
                  {assertion.proposition}
                </Link>
                <div className="pf-item__meta">
                  <span className={`badge badge--${assertion.status}`}>
                    {STATUS_LABELS[assertion.status]}
                  </span>
                  {showStanding && (
                    <span className={`badge badge--${assertion.standing}`}>
                      Standing: {assertion.standing}
                    </span>
                  )}
                  <span className="pf-item__meta-text">
                    {assertion.assertion_type} · updated {formatDate(assertion.updated_at)}
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    );
  }

  function renderNotifications() {
    return (
      <div className="card">
        <div className="card__body">
          {notifications === null ? (
            <p className="muted">Loading notifications…</p>
          ) : notifications === "error" ? (
            <p className="muted">Couldn't load notifications.</p>
          ) : notifications.length === 0 ? (
            <p className="muted">No notifications yet.</p>
          ) : (
            <ul className="pf-notifs">
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={n.read ? "pf-notif" : "pf-notif pf-notif--unread"}
                >
                  <span className="pf-notif__title">{humanizeEvent(n.event_type)}</span>
                  <span className="pf-notif__time">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="pf-note">
            In-app notifications are held in server memory and reset when the server
            restarts.
          </p>
        </div>
      </div>
    );
  }

  const loaded = authored !== null && awaiting !== null;

  const tabs: { id: TabId; label: string; count: number | null }[] = loaded
    ? [
        ...(canRate
          ? [{ id: "awaiting" as const, label: "Awaiting my rating", count: awaiting.total }]
          : []),
        { id: "suggestions" as const, label: "My suggestions", count: authored.length },
        {
          id: "notifications" as const,
          label: "Notifications",
          count: Array.isArray(notifications) ? notifications.length : null,
        },
      ]
    : [];

  return (
    <div className="pf-page">
      <header className="pf-header">
        <span className="avatar pf-avatar" aria-hidden="true">
          {initials(session.user.display_name) || "?"}
        </span>
        <div className="pf-identity">
          <h1 className="pf-name">
            {session.user.display_name}
            <span className="badge badge--neutral pf-role">
              {session.role ?? "no role"}
            </span>
          </h1>
          <p className="pf-subtitle">
            {session.user.email} · activity in {session.currentMatter.name}
          </p>
        </div>
      </header>

      {loadError ? (
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
      ) : !loaded ? (
        <div className="loading">Loading your activity…</div>
      ) : (
        <>
          <section className="pf-stats" aria-label="My activity in this matter">
            <StatCard
              label="My suggestions"
              icon="add-comment"
              value={String(authored.length)}
              caption="Assertions you authored"
              testId="pf-stat-suggestions"
            />
            <StatCard
              label="Accepted"
              icon="check"
              value={String(acceptedCount)}
              caption="Of your suggestions"
              testId="pf-stat-accepted"
            />
            <div className="card pf-stat">
              <div className="pf-stat__top">
                <span className="pf-stat__label">Suggestion acceptance</span>
                <Icon name="analytics" size={18} />
              </div>
              <div className="pf-stat__value-row">
                {acceptancePct !== null && (
                  <svg
                    className="pf-ring"
                    viewBox="0 0 36 36"
                    role="img"
                    aria-label={`Suggestion acceptance ${acceptancePct}%`}
                  >
                    <circle className="pf-ring__track" cx="18" cy="18" r="15.5" />
                    <circle
                      className="pf-ring__meter"
                      cx="18"
                      cy="18"
                      r="15.5"
                      pathLength={100}
                      strokeDasharray={`${acceptancePct} ${100 - acceptancePct}`}
                    />
                  </svg>
                )}
                <span className="pf-stat__value" data-testid="pf-stat-acceptance">
                  {acceptancePct === null ? "—" : `${acceptancePct}%`}
                </span>
              </div>
              <span className="pf-stat__caption">
                Accepted vs rejected of your suggestions
              </span>
            </div>
            {canRate && (
              <StatCard
                label="Awaiting my rating"
                icon="flag"
                value={String(awaiting.total)}
                caption="Proposed, not yet rated by you"
                testId="pf-stat-awaiting"
              />
            )}
          </section>

          <div className="pf-columns">
            <section className="pf-activity">
              <div className="pf-tabs" role="tablist" aria-label="My activity">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    id={`pf-tab-${tab.id}`}
                    aria-selected={activeTab === tab.id}
                    aria-controls="pf-panel"
                    className={activeTab === tab.id ? "pf-tab pf-tab--active" : "pf-tab"}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                    {tab.count !== null && (
                      <span className="pf-tab__count">{tab.count}</span>
                    )}
                  </button>
                ))}
              </div>
              <div
                className="pf-panel"
                role="tabpanel"
                id="pf-panel"
                aria-labelledby={`pf-tab-${activeTab}`}
              >
                {activeTab === "awaiting" && renderAwaiting()}
                {activeTab === "suggestions" && renderSuggestions()}
                {activeTab === "notifications" && renderNotifications()}
              </div>
            </section>

            <aside className="pf-side">
              <div className="card" data-testid="pf-jurisdiction-preference">
                <div className="card__header">Preferences</div>
                <div className="card__body">
                  <label htmlFor="pf-default-jurisdiction">Default jurisdiction</label>
                  <select
                    id="pf-default-jurisdiction"
                    className="select"
                    value={defaultJurisdiction}
                    onChange={(event) => handleDefaultJurisdictionChange(event.target.value)}
                  >
                    <option value="">No default</option>
                    {JURISDICTION_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <p className="pf-note">
                    Used to pre-select jurisdiction when suggesting new assertions.
                  </p>
                </div>
              </div>
              <div className="card" data-testid="pf-matters">
                <div className="card__header">My matters</div>
                <div className="card__body">
                  <ul className="pf-matters">
                    {session.matters.map((matter) => (
                      <li
                        key={matter.id}
                        className={
                          matter.id === matterId
                            ? "pf-matter pf-matter--current"
                            : "pf-matter"
                        }
                      >
                        <span className="pf-matter__name">
                          {matter.name}
                          {matter.id === matterId && (
                            <span className="pf-matter__current">Current</span>
                          )}
                        </span>
                        <span className="badge badge--neutral">{matter.role}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="pf-note">Switch the active matter from the sidebar.</p>
                </div>
              </div>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}
