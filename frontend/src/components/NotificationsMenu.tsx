// In-app notifications (spec §15): the topbar bell (`NotificationsMenu`)
// and the Profile page's Notifications tab (`useNotificationFeed` and
// `NotificationFeed`).
//
// Each notice links to its assertion and shows its context (proposition,
// who acted, matter). Opening one marks it read and, when it belongs to
// another of the user's matters, switches to that matter first (the detail
// page only shows assertions of the current matter). "Mark all as read"
// marks everything up to the newest notice on screen: notices that arrived
// after it stay unread. Read state is stored server-side, so the badge
// stays cleared across reloads and devices. The bell's settings view sets
// which events notify the user. The bell shows the newest 20; the Profile
// tab lists every notice, 50 at a time, and both take the unread figure
// from the server, which counts notices not loaded yet.

import "../styles/notifications.css";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";

import { api } from "../api/client";
import { formatInstantDateTime, parseApiInstant } from "../api/datetime";
import type { AppNotification, NotificationPreference } from "../api/types";
import { Icon } from "../app/icons";
import { navigate } from "../app/router";
import { useSession } from "../app/session";
import {
  NOTIFICATION_PREFERENCE_LABELS,
  NOTIFICATIONS_CHANGED_EVENT,
  announceNotificationsChanged,
  notificationByline,
  notificationTitle,
} from "../constants/notifications";

const POLL_MS = 30_000;
const MENU_LIMIT = 20;
/** Notices per page on the Profile tab (the API's default page). */
const FEED_PAGE = 50;
/** The most notices one GET /notifications returns. */
const MAX_PAGE = 200;
const MENU_SOURCE = "menu";
const FEED_SOURCE = "feed";

function sourceOf(event: Event): string | undefined {
  return (event as CustomEvent<{ source?: string }>).detail?.source;
}

/** A click the app should handle itself; modified/middle clicks are left
 * to the browser (e.g. open in a new tab). */
function isPlainClick(event: ReactMouseEvent): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

function matterOf(n: AppNotification): string | null {
  if (n.matter_id) return n.matter_id;
  return typeof n.payload?.matter_id === "string" ? n.payload.matter_id : null;
}

/** Go to a notice's assertion, switching first to its matter when it is
 * another of the user's matters (the detail page only shows assertions of
 * the current matter). Navigates programmatically: the bell closes its
 * panel on open, and a link removed during its click would not navigate. */
function useOpenNotification() {
  const { session, selectMatter } = useSession();
  return useCallback(
    (n: AppNotification, event: ReactMouseEvent<HTMLAnchorElement>): boolean => {
      if (!n.link || !isPlainClick(event)) return false;
      event.preventDefault();
      const matterId = matterOf(n);
      if (
        session &&
        matterId &&
        session.currentMatter?.id !== matterId &&
        session.matters.some((m) => m.id === matterId)
      ) {
        selectMatter(matterId);
      }
      navigate(n.link);
      return true;
    },
    [session, selectMatter],
  );
}

interface NotificationListProps {
  items: AppNotification[];
  variant: "menu" | "page";
  onOpen: (n: AppNotification, event: ReactMouseEvent<HTMLAnchorElement>) => void;
  onMarkRead: (n: AppNotification) => void;
}

/** The notices themselves; shared by the bell panel and the Profile tab. */
export function NotificationList({ items, variant, onOpen, onMarkRead }: NotificationListProps) {
  const menu = variant === "menu";
  return (
    <ul className={menu ? "notif-list" : "pf-notifs"}>
      {items.map((n) => {
        const byline = notificationByline(n);
        const time = formatInstantDateTime(n.created_at);
        const rowClass = menu
          ? `notifications__item notif-row${n.read ? "" : " notif-row--unread"}`
          : `pf-notif notif-row${n.read ? "" : " pf-notif--unread notif-row--unread"}`;
        const content = (
          <>
            <span className={menu ? "notifications__item-title" : "pf-notif__title"}>
              {notificationTitle(n)}
            </span>
            {n.context?.proposition && (
              <span className="notif-row__context">{n.context.proposition}</span>
            )}
            {menu ? (
              <span className="notifications__item-time">
                {byline ? `${byline} · ${time}` : time}
              </span>
            ) : (
              byline && <span className="notif-row__byline">{byline}</span>
            )}
          </>
        );
        return (
          <li key={n.id} className={rowClass} data-unread={n.read ? undefined : "true"}>
            {n.link ? (
              <a
                className="notif-row__main notif-row__link"
                href={`#${n.link}`}
                onClick={(event) => {
                  onMarkRead(n);
                  onOpen(n, event);
                }}
              >
                {content}
              </a>
            ) : (
              <div className="notif-row__main">{content}</div>
            )}
            <span className="notif-row__side">
              {!menu && <span className="pf-notif__time">{time}</span>}
              {!n.read && !n.link && (
                <button
                  type="button"
                  className="btn btn--sm btn--secondary notif-row__mark"
                  onClick={() => onMarkRead(n)}
                >
                  Mark read
                </button>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Which events notify me: GET/PUT /notifications/preferences. */
export function NotificationPreferencesPanel() {
  const [prefs, setPrefs] = useState<NotificationPreference[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.notificationPreferences().then(
      (result) => {
        if (!cancelled) setPrefs(result);
      },
      () => {
        if (!cancelled) setError("Couldn't load notification settings.");
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = (eventType: string, enabled: boolean) => {
    const previous = prefs;
    setError(null);
    setPrefs((current) =>
      current?.map((p) => (p.event_type === eventType ? { ...p, enabled } : p)) ?? current,
    );
    api.updateNotificationPreferences({ [eventType]: enabled }).then(setPrefs, () => {
      setPrefs(previous);
      setError("Couldn't save that setting. Try again.");
    });
  };

  if (prefs === null) {
    return <p className="notif-prefs__status">{error ?? "Loading settings…"}</p>;
  }
  return (
    <div className="notif-prefs">
      <p className="notif-prefs__intro">Notify me when:</p>
      <ul className="notif-prefs__list">
        {prefs.map((p) => (
          <li key={p.event_type}>
            <label className="notif-prefs__option">
              <input
                type="checkbox"
                checked={p.enabled}
                onChange={(event) => toggle(p.event_type, event.target.checked)}
              />
              <span>
                {NOTIFICATION_PREFERENCE_LABELS[p.event_type] ?? p.event_type}
                {p.event_type === "assertion_rated" && !p.default && (
                  <span className="notif-prefs__hint"> (off by default)</span>
                )}
              </span>
            </label>
          </li>
        ))}
      </ul>
      {error && <p className="notif-prefs__error" role="alert">{error}</p>}
    </div>
  );
}

/** Topbar bell: unread badge, the newest notices, mark read, settings. */
export function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"feed" | "settings">("feed");
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mounted = useRef(false);
  // Bumped by every local change; a poll that started before one is stale
  // and must not bring an unread badge back.
  const generation = useRef(0);
  const openNotification = useOpenNotification();

  const load = useCallback(() => {
    const started = generation.current;
    api
      .notifications({ limit: MENU_LIMIT })
      .then((list) => {
        if (mounted.current && started === generation.current) setItems(list);
      })
      .catch(() => {
        /* notification polling is best-effort */
      });
    api
      .unreadNotificationCount()
      .then((count) => {
        if (mounted.current && started === generation.current) setUnread(count.unread_count);
      })
      .catch(() => {
        /* best-effort */
      });
  }, []);

  useEffect(() => {
    mounted.current = true;
    load();
    const timer = window.setInterval(load, POLL_MS);
    const onChanged = (event: Event) => {
      if (sourceOf(event) !== MENU_SOURCE) load();
    };
    window.addEventListener(NOTIFICATIONS_CHANGED_EVENT, onChanged);
    return () => {
      mounted.current = false;
      window.clearInterval(timer);
      window.removeEventListener(NOTIFICATIONS_CHANGED_EVENT, onChanged);
    };
  }, [load]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onClick);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // After a write: resync once (no retry loop), and tell the Profile tab.
  const settle = (write: Promise<unknown>) => {
    write
      .then(() => announceNotificationsChanged(MENU_SOURCE))
      .catch(() => undefined)
      .finally(load);
  };

  const markRead = (n: AppNotification) => {
    if (n.read) return;
    generation.current += 1;
    setItems((current) => current.map((x) => (x.id === n.id ? { ...x, read: true } : x)));
    setUnread((count) => Math.max(0, count - 1));
    settle(api.markNotificationRead(n.id));
  };

  const markAllRead = () => {
    if (items.length === 0) return;
    generation.current += 1;
    setItems((current) => current.map((x) => ({ ...x, read: true })));
    setUnread(0);
    settle(api.markAllNotificationsRead(items[0].created_at));
  };

  const onOpen = (n: AppNotification, event: ReactMouseEvent<HTMLAnchorElement>) => {
    if (openNotification(n, event)) setOpen(false);
  };

  return (
    <div className="notifications" ref={containerRef}>
      <button
        type="button"
        className="topbar__action"
        aria-label={unread > 0 ? `Notifications (${unread} unread)` : "Notifications"}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => {
          setOpen((value) => !value);
          setView("feed");
        }}
      >
        <Icon name="notifications" />
        {unread > 0 && <span className="topbar__badge" />}
      </button>
      {open && (
        <div className="notifications__panel" role="dialog" aria-label="Notifications">
          <div className="notifications__header notif-panel__header">
            <span>{view === "settings" ? "Notification settings" : "Notifications"}</span>
            <span className="notif-panel__actions">
              {view === "feed" ? (
                <>
                  <button
                    type="button"
                    className="notif-panel__text-button"
                    onClick={markAllRead}
                    disabled={unread === 0 && items.every((n) => n.read)}
                  >
                    Mark all as read
                  </button>
                  <button
                    type="button"
                    className="topbar__action notif-panel__icon-button"
                    aria-label="Notification settings"
                    onClick={() => setView("settings")}
                  >
                    <Icon name="settings" size={18} />
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="notif-panel__text-button"
                  onClick={() => setView("feed")}
                >
                  Back
                </button>
              )}
            </span>
          </div>
          {view === "settings" ? (
            <NotificationPreferencesPanel />
          ) : items.length === 0 ? (
            <div className="notifications__empty">No notifications yet.</div>
          ) : (
            <NotificationList items={items} variant="menu" onOpen={onOpen} onMarkRead={markRead} />
          )}
        </div>
      )}
    </div>
  );
}

/** Newest first, by instant: "…Z" and "+00:00" spellings do not compare as
 * strings. The sort is stable, so ties keep the server's order. */
function newestFirst(items: AppNotification[]): AppNotification[] {
  const at = (n: AppNotification) => parseApiInstant(n.created_at)?.getTime() ?? 0;
  return [...items].sort((a, b) => at(b) - at(a));
}

/** `first`, then the notices of `then` it does not hold: a notice that
 * arrives between two requests shifts the later page by one. */
function mergeNotices(first: AppNotification[], then: AppNotification[]): AppNotification[] {
  const held = new Set(first.map((n) => n.id));
  return [...first, ...then.filter((n) => !held.has(n.id))];
}

/** The newest notices again, down to `oldestId` (the oldest one listed; with
 * none, one page) or to the last one there is, in as few requests as
 * possible. Notices are never deleted, so this re-reads everything listed. */
async function readNewestThrough(oldestId: string | null, listed: number): Promise<AppNotification[]> {
  let items: AppNotification[] = [];
  for (;;) {
    const limit = Math.min(MAX_PAGE, Math.max(FEED_PAGE, listed - items.length));
    const page = await api.notifications({ limit, offset: items.length });
    items = mergeNotices(items, page);
    if (page.length < limit || oldestId === null || page.some((n) => n.id === oldestId)) return items;
  }
}

interface NotificationFeedState {
  /** Newest first; null until the first page arrives. */
  items: AppNotification[] | null;
  failed: boolean;
  /** The server's count of every unread notice, listed or not; null until known. */
  unread: number | null;
  /** The last page came back full, so older notices may follow. */
  hasMore: boolean;
  loadingMore: boolean;
  moreError: string | null;
}

export interface NotificationFeedModel extends NotificationFeedState {
  showMore: () => void;
  markRead: (n: AppNotification) => void;
  markAllRead: () => void;
}

const EMPTY_FEED: NotificationFeedState = {
  items: null,
  failed: false,
  unread: null,
  hasMore: false,
  loadingMore: false,
  moreError: null,
};

/** The Profile page's Notifications tab: every notice, FEED_PAGE at a time
 * with Show more, and the server's unread count (review
 * fe-shell-authoring:2). Kept by the page, not the tab, so it survives
 * switching tabs; `reloadKey` starts it over. Changes made in the bell
 * re-read everything listed, so the list never shrinks back to one page. */
export function useNotificationFeed(reloadKey: string): NotificationFeedModel {
  const [state, setState] = useState<NotificationFeedState>(EMPTY_FEED);
  const latest = useRef(state);
  latest.current = state;
  // Bumped when the feed starts over: answers for an earlier start are dropped.
  const generation = useRef(0);
  // Bumped by every local change of read state: an unread count requested
  // before one is stale.
  const countGeneration = useRef(0);

  const loadUnread = useCallback(() => {
    const started = generation.current;
    const counted = countGeneration.current;
    api.unreadNotificationCount().then(
      ({ unread_count }) => {
        if (generation.current === started && countGeneration.current === counted) {
          setState((s) => ({ ...s, unread: unread_count }));
        }
      },
      () => undefined,
    );
  }, []);

  const refresh = useCallback(() => {
    loadUnread();
    const listed = latest.current.items;
    if (listed === null) return; // the first page is on its way
    const started = generation.current;
    const oldest = listed.length > 0 ? listed[listed.length - 1].id : null;
    readNewestThrough(oldest, listed.length).then(
      (fresh) => {
        if (generation.current !== started) return;
        setState((s) => {
          if (s.items === null) return s;
          // Keeps whatever a Show more added meanwhile. Nothing older than
          // the oldest listed was read, so whether more follow is unchanged,
          // unless the list was empty.
          const items = newestFirst(mergeNotices(fresh, s.items));
          return { ...s, items, hasMore: oldest === null ? fresh.length >= FEED_PAGE : s.hasMore };
        });
      },
      () => undefined,
    );
  }, [loadUnread]);

  useEffect(() => {
    generation.current += 1;
    const started = generation.current;
    setState(EMPTY_FEED);
    api.notifications({ limit: FEED_PAGE, offset: 0 }).then(
      (page) => {
        if (generation.current !== started) return;
        setState((s) => ({ ...s, items: newestFirst(page), hasMore: page.length === FEED_PAGE }));
      },
      () => {
        if (generation.current === started) setState((s) => ({ ...s, failed: true }));
      },
    );
    loadUnread();
  }, [reloadKey, loadUnread]);

  useEffect(() => {
    const onChanged = (event: Event) => {
      if (sourceOf(event) !== FEED_SOURCE) refresh();
    };
    window.addEventListener(NOTIFICATIONS_CHANGED_EVENT, onChanged);
    return () => window.removeEventListener(NOTIFICATIONS_CHANGED_EVENT, onChanged);
  }, [refresh]);

  const showMore = () => {
    const listed = latest.current.items;
    if (listed === null || latest.current.loadingMore) return;
    const started = generation.current;
    setState((s) => ({ ...s, loadingMore: true, moreError: null }));
    api.notifications({ limit: FEED_PAGE, offset: listed.length }).then(
      (page) => {
        if (generation.current !== started) return;
        setState((s) => ({
          ...s,
          items: s.items === null ? s.items : newestFirst(mergeNotices(s.items, page)),
          hasMore: page.length === FEED_PAGE,
          loadingMore: false,
        }));
      },
      (error: unknown) => {
        if (generation.current !== started) return;
        setState((s) => ({
          ...s,
          loadingMore: false,
          moreError: error instanceof Error ? error.message : "the server did not respond",
        }));
      },
    );
  };

  const markRead = (n: AppNotification) => {
    if (n.read) return;
    countGeneration.current += 1;
    setState((s) => ({
      ...s,
      items: s.items?.map((x) => (x.id === n.id ? { ...x, read: true } : x)) ?? null,
      unread: s.unread === null ? null : Math.max(0, s.unread - 1),
    }));
    // Then the server's count, which also covers a notice read elsewhere.
    api
      .markNotificationRead(n.id)
      .then(() => announceNotificationsChanged(FEED_SOURCE))
      .catch(() => undefined)
      .finally(loadUnread);
  };

  const markAllRead = () => {
    const listed = latest.current.items;
    if (listed === null || listed.length === 0) return;
    countGeneration.current += 1;
    const counted = countGeneration.current;
    setState((s) => ({ ...s, items: s.items?.map((x) => ({ ...x, read: true })) ?? null, unread: 0 }));
    // Marks every unread notice up to the newest one listed, loaded or not.
    api.markAllNotificationsRead(listed[0].created_at).then(
      ({ unread_count }) => {
        announceNotificationsChanged(FEED_SOURCE);
        if (countGeneration.current === counted) setState((s) => ({ ...s, unread: unread_count }));
        // Notices newer than the list stayed unread: list them.
        if (unread_count > 0) refresh();
      },
      () => refresh(),
    );
  };

  return { ...state, showMore, markRead, markAllRead };
}

/** The Profile page's list of every notice (from `useNotificationFeed`),
 * with the same links and read actions as the bell; changes made here or in
 * the bell show up in both. */
export function NotificationFeed({ feed }: { feed: NotificationFeedModel }) {
  const openNotification = useOpenNotification();
  const items = feed.items ?? [];
  // The server's figure counts notices beyond the loaded ones too.
  const unread = feed.unread ?? items.filter((n) => !n.read).length;

  return (
    <div className="notif-feed">
      <div className="notif-feed__bar">
        <span className="notif-feed__count">
          {unread === 0 ? "All read" : `${unread.toLocaleString("en-US")} unread`}
        </span>
        <button
          type="button"
          className="btn btn--sm btn--secondary"
          onClick={feed.markAllRead}
          disabled={unread === 0 || items.length === 0}
        >
          Mark all as read
        </button>
      </div>
      <NotificationList
        items={items}
        variant="page"
        onOpen={(n, event) => {
          openNotification(n, event);
        }}
        onMarkRead={feed.markRead}
      />
      {feed.hasMore && (
        <div className="pf-more">
          <span className="pf-more__count">Showing the newest {items.length.toLocaleString("en-US")}</span>
          <button
            type="button"
            className="btn btn--sm btn--secondary"
            onClick={feed.showMore}
            disabled={feed.loadingMore}
          >
            {feed.loadingMore ? "Loading…" : "Show more"}
          </button>
          {feed.moreError !== null && (
            <span className="pf-more__error" role="alert">
              Couldn't load more: {feed.moreError}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
