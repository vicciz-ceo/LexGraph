// ProfilePage — the signed-in user's activity within the current matter.
//
// Adapts the Consensus "My Profile & Activity" design to LexGraph's real
// model: no expertise chips, no vote weighting, no binary approve/reject.
// The counts come from the matter's assertion statistics filtered by
// author_user_id; "My suggestions" (author_user_id, newest first) and
// "Awaiting my rating" (status=proposed&unrated_by_me=true) are server pages
// of 50 with Show more. The whole matter is never downloaded (audit finding
// ui:1). The three signals stay separate: 1-5 strength ratings, model
// confidence (percent, model_suggested only), and reviewer-gated status.
//
// Assertions the definition-linking pipeline generated under the user's
// account (origin system_generated, when they ran it) are not their
// suggestions (ui:4): they are left out of the counts, the acceptance rate
// and the list, which reads the user's colleague and AI-deduced
// suggestions as two lists (the endpoint filters one origin at a time).

import { useEffect, useRef, useState } from "react";

import "../styles/pages/profile.css";

import { api } from "../api/client";
import { formatInstantDate, formatInstantDateTime, parseApiInstant } from "../api/datetime";
import { listWindow } from "../api/listWindow";
import type {
  AppNotification,
  Assertion,
  AssertionList,
  AssertionListItem,
  AssertionListParams,
  AssertionOrigin,
  AssertionStats,
} from "../api/types";
import { Icon } from "../app/icons";
import type { IconName } from "../app/icons";
import { Link } from "../app/router";
import { useActiveSession } from "../app/session";
import { NotificationFeed } from "../components/NotificationsMenu";
import { JURISDICTION_OPTIONS } from "../constants/jurisdictions";
import { defaultJurisdictionStorageKey, readDefaultJurisdiction } from "../constants/preferences";

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

/** Rows per list request. */
const LIST_PAGE = 50;

const AWAITING_PARAMS: AssertionListParams = { status: "proposed", unrated_by_me: true };

const EMPTY_LIST: AssertionList = { items: [], total: 0 };

/** What a user suggests; system_generated rows are the pipeline's. */
const SUGGESTION_ORIGINS: AssertionOrigin[] = ["user_suggested", "model_suggested"];

function lastUpdate(item: AssertionListItem): number {
  return parseApiInstant(item.updated_at)?.getTime() ?? 0;
}

/** The `size` most recently updated suggestions of `userId`, and how many
 * there are in all. */
async function loadSuggestions(
  matterId: string,
  userId: string,
  size: number,
): Promise<AssertionList> {
  const lists = await Promise.all(
    SUGGESTION_ORIGINS.map((origin) =>
      listWindow(matterId, { author_user_id: userId, origin, sort: "-updated_at" }, size),
    ),
  );
  const seen = new Set<string>();
  const items = lists
    .flatMap((list) => list.items)
    .filter((item) => !seen.has(item.id) && Boolean(seen.add(item.id)))
    .sort((a, b) => lastUpdate(b) - lastUpdate(a))
    .slice(0, size);
  return { items, total: lists.reduce((sum, list) => sum + list.total, 0) };
}

type ListId = "mine" | "awaiting";

function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

/** `prev` followed by the rows of `next` it does not already hold (a row
 * created between two pages shifts the second one). */
function appendPage(prev: AssertionList, next: AssertionList): AssertionList {
  const seen = new Set(prev.items.map((a) => a.id));
  return { ...next, items: [...prev.items, ...next.items.filter((a) => !seen.has(a.id))] };
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
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

  // Kept in this browser only; the Suggest form reads it back
  // (constants/preferences.ts). Unavailable storage just keeps no default.
  const [defaultJurisdiction, setDefaultJurisdiction] = useState<string>(() =>
    readDefaultJurisdiction(userId),
  );

  const handleDefaultJurisdictionChange = (value: string) => {
    setDefaultJurisdiction(value);
    try {
      window.localStorage.setItem(defaultJurisdictionStorageKey(userId), value);
    } catch {
      /* storage blocked: the choice lasts for this page only */
    }
  };

  const [stats, setStats] = useState<AssertionStats | null>(null);
  const [authored, setAuthored] = useState<AssertionList | null>(null);
  const [awaiting, setAwaiting] = useState<AssertionList | null>(null);
  const [notifications, setNotifications] = useState<
    AppNotification[] | "error" | null
  >(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>(canRate ? "awaiting" : "suggestions");
  const [reloadKey, setReloadKey] = useState(0);
  const [moreLoading, setMoreLoading] = useState<ListId | null>(null);
  const [moreError, setMoreError] = useState<{ list: ListId; message: string } | null>(null);
  // Bumped by every (re)load, so a Show more answer for an earlier matter or
  // user is dropped.
  const loadGeneration = useRef(0);

  useEffect(() => {
    let cancelled = false;
    loadGeneration.current += 1;
    setStats(null);
    setAuthored(null);
    setAwaiting(null);
    setNotifications(null);
    setLoadError(null);
    setMoreLoading(null);
    setMoreError(null);
    setActiveTab(canRate ? "awaiting" : "suggestions");

    const loads: [Promise<AssertionStats>, Promise<AssertionList>, Promise<AssertionList>] = [
      api.assertionStats(matterId, { author_user_id: userId }),
      loadSuggestions(matterId, userId, LIST_PAGE),
      canRate
        ? api.listAssertions(matterId, { ...AWAITING_PARAMS, limit: LIST_PAGE, offset: 0 })
        : Promise.resolve(EMPTY_LIST),
    ];
    Promise.all(loads).then(
      ([myStats, mine, unrated]) => {
        if (cancelled) return;
        setStats(myStats);
        setAuthored(mine);
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
        // Newest first, by instant: "…Z" and "+00:00" spellings do not
        // compare as strings.
        const at = (n: AppNotification) => parseApiInstant(n.created_at)?.getTime() ?? 0;
        setNotifications([...items].sort((a, b) => at(b) - at(a)));
      },
      () => {
        if (!cancelled) setNotifications("error");
      },
    );

    return () => {
      cancelled = true;
    };
  }, [matterId, userId, canRate, reloadKey]);

  const showMore = (list: ListId) => {
    const current = list === "mine" ? authored : awaiting;
    if (current === null || moreLoading !== null) return;
    const generation = loadGeneration.current;
    setMoreLoading(list);
    setMoreError(null);
    // My suggestions are re-read as a larger window (two lists merged);
    // the awaiting list appends its next page.
    const request =
      list === "mine"
        ? loadSuggestions(matterId, userId, current.items.length + LIST_PAGE)
        : api.listAssertions(matterId, {
            ...AWAITING_PARAMS,
            limit: LIST_PAGE,
            offset: current.items.length,
          });
    request.then(
      (next) => {
        if (loadGeneration.current !== generation) return;
        if (list === "mine") setAuthored(next);
        else setAwaiting((prev) => (prev === null ? prev : appendPage(prev, next)));
        setMoreLoading(null);
      },
      (error: unknown) => {
        if (loadGeneration.current !== generation) return;
        setMoreError({
          list,
          message: error instanceof Error ? error.message : "the server did not respond",
        });
        setMoreLoading(null);
      },
    );
  };

  // Without the pipeline output generated under this account.
  const pipelineCount = stats?.by_origin.system_generated ?? 0;
  const pipelineStatus = stats?.by_origin_status.system_generated ?? {};
  const authoredCount = Math.max(0, (stats?.total ?? 0) - pipelineCount);
  const acceptedCount = Math.max(
    0,
    (stats?.by_status.accepted ?? 0) - (pipelineStatus.accepted ?? 0),
  );
  const rejectedCount = Math.max(
    0,
    (stats?.by_status.rejected ?? 0) - (pipelineStatus.rejected ?? 0),
  );
  const decidedCount = acceptedCount + rejectedCount;
  const acceptancePct =
    decidedCount > 0 ? Math.round((acceptedCount / decidedCount) * 100) : null;

  function renderMore(list: ListId, shown: AssertionList) {
    if (shown.items.length >= shown.total) return null;
    return (
      <div className="pf-more">
        <span className="pf-more__count">
          Showing {formatCount(shown.items.length)} of {formatCount(shown.total)}
        </span>
        <button
          type="button"
          className="btn btn--sm btn--secondary"
          onClick={() => showMore(list)}
          disabled={moreLoading !== null}
        >
          {moreLoading === list ? "Loading…" : "Show more"}
        </button>
        {moreError?.list === list && (
          <span className="pf-more__error" role="alert">
            Couldn't load more: {moreError.message}
          </span>
        )}
      </div>
    );
  }

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
      <>
        <ul className="pf-list">
          {awaiting.items.map((assertion) => {
            const origin = ORIGIN_CHIPS[assertion.origin];
            const metaParts = [
              assertion.assertion_type,
              assertion.jurisdiction,
              `submitted ${formatInstantDate(assertion.submitted_at, "en-US")}`,
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
        {renderMore("awaiting", awaiting)}
      </>
    );
  }

  function renderSuggestions() {
    if (authored === null) return null;
    if (authored.items.length === 0) {
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
      <>
        <ul className="pf-list">
          {authored.items.map((assertion) => {
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
                      {assertion.assertion_type} · updated {formatInstantDate(assertion.updated_at, "en-US")}
                    </span>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
        {renderMore("mine", authored)}
      </>
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
            <NotificationFeed items={notifications} onItemsChange={setNotifications} />
          )}
          <p className="pf-note">
            Notifications are kept until you read them. Choose which events notify
            you from the bell's settings.
          </p>
        </div>
      </div>
    );
  }

  const loaded = stats !== null && authored !== null && awaiting !== null;

  const tabs: { id: TabId; label: string; count: number | null }[] = loaded
    ? [
        ...(canRate
          ? [{ id: "awaiting" as const, label: "Awaiting my rating", count: awaiting.total }]
          : []),
        { id: "suggestions" as const, label: "My suggestions", count: authored.total },
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
              value={formatCount(authoredCount)}
              caption="Assertions you authored"
              testId="pf-stat-suggestions"
            />
            <StatCard
              label="Accepted"
              icon="check"
              value={formatCount(acceptedCount)}
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
                value={formatCount(awaiting.total)}
                caption="Proposed, not yet rated by you"
                testId="pf-stat-awaiting"
              />
            )}
          </section>
          {pipelineCount > 0 && (
            <p className="pf-note pf-pipeline-note">
              {`${formatCount(pipelineCount)} ${
                pipelineCount === 1 ? "assertion" : "assertions"
              } generated by the definition-linking pipeline under your account ${
                pipelineCount === 1 ? "is" : "are"
              } not counted or listed as your suggestions.`}
            </p>
          )}

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
                      <span className="pf-tab__count">{formatCount(tab.count)}</span>
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
