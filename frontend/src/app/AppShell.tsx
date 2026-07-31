// Application chrome: sidebar (brand, matter selector, nav, user block)
// + topbar (global assertion search, notifications, help), per the
// Consensus design's shared layout.

import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { api } from "../api/client";
import type { AppNotification } from "../api/types";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { Link, navigate, useHashLocation } from "./router";
import { useSession } from "./session";

const NOTIFICATION_POLL_MS = 30_000;

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  /** Prefix match so detail routes keep their section highlighted. */
  activePrefix: string;
  adminOnly?: boolean;
}

const WORKSPACE_NAV: NavItem[] = [
  { to: "/review", label: "Review Queue", icon: "flag", activePrefix: "/review" },
  { to: "/knowledge", label: "Knowledge Base", icon: "book", activePrefix: "/knowledge" },
  { to: "/suggest", label: "Suggest Assertion", icon: "add-comment", activePrefix: "/suggest" },
];

const OPERATIONS_NAV: NavItem[] = [
  { to: "/contested", label: "Contested", icon: "gavel", activePrefix: "/contested" },
  { to: "/analytics", label: "Analytics", icon: "analytics", activePrefix: "/analytics" },
  { to: "/admin", label: "Admin", icon: "settings", activePrefix: "/admin", adminOnly: true },
];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

function describeNotification(n: AppNotification): string {
  const label = n.event_type.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<AppNotification[]>([]);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      api
        .notifications()
        .then((res) => {
          if (!cancelled) setItems(res);
        })
        .catch(() => {
          /* notification polling is best-effort */
        });
    };
    poll();
    const timer = window.setInterval(poll, NOTIFICATION_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  const hasUnread = items.some((n) => !n.read);

  return (
    <div className="notifications" ref={containerRef}>
      <button
        type="button"
        className="topbar__action"
        aria-label={hasUnread ? "Notifications (unread)" : "Notifications"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="notifications" />
        {hasUnread && <span className="topbar__badge" />}
      </button>
      {open && (
        <div className="notifications__panel" role="dialog" aria-label="Notifications">
          <div className="notifications__header">Notifications</div>
          {items.length === 0 ? (
            <div className="notifications__empty">No notifications yet.</div>
          ) : (
            items.slice(0, 20).map((n) => (
              <div key={n.id} className="notifications__item">
                <div className="notifications__item-title">{describeNotification(n)}</div>
                <div className="notifications__item-time">
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { session, signOut, selectMatter } = useSession();
  const location = useHashLocation();
  const [search, setSearch] = useState("");

  if (!session) return null;

  const isAdmin = session.role === "admin";
  const navItems = [
    { section: "Workspace", items: WORKSPACE_NAV },
    {
      section: "Operations",
      items: OPERATIONS_NAV.filter((item) => !item.adminOnly || isAdmin),
    },
  ];

  const onSearch = (event: FormEvent) => {
    event.preventDefault();
    const q = search.trim();
    navigate(q ? `/knowledge?q=${encodeURIComponent(q)}` : "/knowledge");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__brand-mark" aria-hidden="true">
            <Icon name="link" size={18} />
          </span>
          LexGraph
        </div>

        <div className="sidebar__matter">
          <label className="sidebar__matter-label" htmlFor="matter-select">
            Matter
          </label>
          <select
            id="matter-select"
            className="select"
            value={session.currentMatter?.id ?? ""}
            onChange={(event) => selectMatter(event.target.value)}
          >
            {session.matters.map((matter) => (
              <option key={matter.id} value={matter.id}>
                {matter.name}
              </option>
            ))}
          </select>
        </div>

        <nav className="sidebar__nav" aria-label="Primary">
          {navItems.map(({ section, items }) => (
            <div key={section}>
              <div className="sidebar__section">{section}</div>
              {items.map((item) => {
                const active =
                  location.path === item.activePrefix ||
                  location.path.startsWith(`${item.activePrefix}/`) ||
                  (item.activePrefix === "/knowledge" &&
                    location.path.startsWith("/assertions/"));
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={
                      active ? "sidebar__link sidebar__link--active" : "sidebar__link"
                    }
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon name={item.icon} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar__footer">
          <Link to="/profile" className="avatar" aria-label="My profile">
            {initials(session.user.display_name) || "?"}
          </Link>
          <div className="sidebar__user">
            <div className="sidebar__user-name">{session.user.display_name}</div>
            <div className="sidebar__user-meta">
              {session.role ?? "no role"} · {session.user.email}
            </div>
          </div>
          <button
            type="button"
            className="topbar__action"
            aria-label="Sign out"
            onClick={signOut}
          >
            <Icon name="logout" />
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <form className="topbar__search" role="search" onSubmit={onSearch}>
            <Icon name="search" size={16} />
            <input
              type="search"
              placeholder="Search assertions…"
              aria-label="Search assertions"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </form>
          <div className="topbar__spacer" />
          <NotificationsBell />
          <a
            className="topbar__action"
            href="https://github.com/vicciz-ceo/LexGraph#readme"
            target="_blank"
            rel="noreferrer"
            aria-label="Help"
          >
            <Icon name="help" />
          </a>
        </header>
        <main className="page">
          <div className="page__inner">{children}</div>
        </main>
      </div>
    </div>
  );
}
