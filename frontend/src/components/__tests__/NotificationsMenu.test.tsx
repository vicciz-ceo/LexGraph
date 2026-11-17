// The topbar notifications bell (findings ui:7, pipeline:9): the unread
// badge clears when notices are read, notices link to their assertion
// (switching matter when needed), "Mark all as read" marks what was shown,
// failures do not loop, and the settings view toggles event types.

import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AppNotification, NotificationPreference } from "../../api/types";

const mocks = vi.hoisted(() => ({ selectMatter: vi.fn() }));

vi.mock("../../app/session", () => {
  const acme = { id: "m-1", name: "Acme v. Zenith", repository_id: "r-1", organization_id: "o-1", role: "reviewer" };
  const harel = { id: "m-2", name: "Estate of Harel", repository_id: "r-1", organization_id: "o-1", role: "contributor" };
  const session = {
    user: { id: "u-me", email: "noa@example.com", display_name: "Noa Levi" },
    matters: [acme, harel],
    currentMatter: acme,
    role: "reviewer",
  };
  return { useSession: () => ({ session, selectMatter: mocks.selectMatter }) };
});

vi.mock("../../api/client", () => ({
  api: {
    notifications: vi.fn(),
    unreadNotificationCount: vi.fn(),
    markNotificationRead: vi.fn(),
    markAllNotificationsRead: vi.fn(),
    notificationPreferences: vi.fn(),
    updateNotificationPreferences: vi.fn(),
  },
}));

import { api } from "../../api/client";
import { NOTIFICATIONS_CHANGED_EVENT } from "../../constants/notifications";
import { NotificationsMenu } from "../NotificationsMenu";

const mockedApi = vi.mocked(api);

function notice(overrides: Partial<AppNotification> = {}): AppNotification {
  return {
    id: "n-1",
    event_type: "assertion_rejected",
    actor_user_id: "u-reviewer",
    recipient_user_id: "u-me",
    payload: { assertion_id: "a-1", matter_id: "m-1", previous_status: "proposed", status: "rejected" },
    assertion_id: "a-1",
    matter_id: "m-1",
    link: "/assertions/a-1",
    context: {
      proposition: "Termination requires 90 days' written notice.",
      assertion_status: "rejected",
      assertion_origin: "user_suggested",
      matter_name: "Acme v. Zenith",
      actor_display_name: "Riva Reviewer",
    },
    created_at: "2026-11-16T09:00:00+00:00",
    read: false,
    read_at: null,
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

function serve(items: AppNotification[], unread = items.filter((n) => !n.read).length) {
  mockedApi.notifications.mockResolvedValue(items);
  mockedApi.unreadNotificationCount.mockResolvedValue({ unread_count: unread });
}

const bell = () => screen.getByRole("button", { name: /^Notifications/ });

/** Let pending API promises (writes, the resync after them) settle inside act. */
async function settle() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

async function openPanel() {
  fireEvent.click(bell());
  return screen.findByRole("dialog", { name: "Notifications" });
}

beforeEach(() => {
  vi.clearAllMocks();
  window.location.hash = "";
  mockedApi.markNotificationRead.mockResolvedValue({} as AppNotification);
  mockedApi.markAllNotificationsRead.mockResolvedValue({ marked_read: 1, unread_count: 0 });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("NotificationsMenu", () => {
  it("shows the server's unread count and clears the badge when the notice is opened", async () => {
    serve([notice()]);
    render(<NotificationsMenu />);
    await waitFor(() => expect(bell()).toHaveAccessibleName("Notifications (1 unread)"));
    expect(mockedApi.notifications).toHaveBeenCalledWith({ limit: 20 });

    const panel = await openPanel();
    const link = within(panel).getByRole("link", { name: /Assertion rejected/ });
    expect(link).toHaveAttribute("href", "#/assertions/a-1");
    expect(link).toHaveTextContent("Termination requires 90 days' written notice.");
    expect(link).toHaveTextContent("Riva Reviewer · Acme v. Zenith");

    serve([notice({ read: true })], 0); // what the server reports afterwards
    fireEvent.click(link);

    expect(mockedApi.markNotificationRead).toHaveBeenCalledWith("n-1");
    expect(window.location.hash).toBe("#/assertions/a-1");
    expect(mocks.selectMatter).not.toHaveBeenCalled(); // already the current matter
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(bell()).toHaveAccessibleName("Notifications");
    await settle();
    expect(mockedApi.unreadNotificationCount).toHaveBeenCalledTimes(3); // mount, open, resync
    expect(bell()).toHaveAccessibleName("Notifications");
  });

  it("switches to the notice's matter before opening an assertion from another matter", async () => {
    serve([
      notice({
        id: "n-2",
        event_type: "assertion_submitted",
        matter_id: "m-2",
        assertion_id: "a-9",
        link: "/assertions/a-9",
        payload: { assertion_id: "a-9", matter_id: "m-2", previous_status: null, status: "proposed" },
      }),
    ]);
    render(<NotificationsMenu />);
    const panel = await openPanel();
    fireEvent.click(await within(panel).findByRole("link", { name: /submitted for review/ }));
    expect(mocks.selectMatter).toHaveBeenCalledWith("m-2");
    expect(window.location.hash).toBe("#/assertions/a-9");
    await settle();
  });

  it("renders a notice the user can no longer open as text with its own mark-read control", async () => {
    serve([notice({ link: null, context: null })]);
    render(<NotificationsMenu />);
    const panel = await openPanel();
    expect(await within(panel).findByText("Assertion rejected")).toBeInTheDocument();
    expect(within(panel).queryByRole("link")).not.toBeInTheDocument();

    serve([notice({ link: null, context: null, read: true })], 0);
    fireEvent.click(within(panel).getByRole("button", { name: "Mark read" }));
    expect(mockedApi.markNotificationRead).toHaveBeenCalledWith("n-1");
    expect(within(panel).queryByRole("button", { name: "Mark read" })).not.toBeInTheDocument();
    await settle();
    expect(within(panel).queryByRole("button", { name: "Mark read" })).not.toBeInTheDocument();
  });

  it("marks everything shown as read, bounded by the newest notice on screen", async () => {
    serve([
      notice({ id: "n-new", created_at: "2026-11-16T10:00:00+00:00" }),
      notice({ id: "n-old", created_at: "2026-11-16T08:00:00+00:00", event_type: "comment_added" }),
    ]);
    render(<NotificationsMenu />);
    const panel = await openPanel();
    await waitFor(() => expect(bell()).toHaveAccessibleName("Notifications (2 unread)"));

    serve([], 0);
    fireEvent.click(within(panel).getByRole("button", { name: "Mark all as read" }));
    expect(mockedApi.markAllNotificationsRead).toHaveBeenCalledWith("2026-11-16T10:00:00+00:00");
    expect(bell()).toHaveAccessibleName("Notifications");
    await settle();
    expect(bell()).toHaveAccessibleName("Notifications");
  });

  it("does not retry a failed write in a loop", async () => {
    serve([notice()]);
    mockedApi.markNotificationRead.mockRejectedValue(new Error("offline"));
    render(<NotificationsMenu />);
    const panel = await openPanel();
    await waitFor(() => expect(mockedApi.notifications).toHaveBeenCalledTimes(2)); // mount + open
    fireEvent.click(within(panel).getByRole("link", { name: /Assertion rejected/ }));

    await settle();
    await settle();
    expect(mockedApi.markNotificationRead).toHaveBeenCalledTimes(1);
    expect(mockedApi.notifications).toHaveBeenCalledTimes(3); // exactly one resync
    // The resync restored the server's truth: still unread.
    expect(bell()).toHaveAccessibleName("Notifications (1 unread)");
  });

  it("ignores a poll that started before the notice was marked read", async () => {
    serve([notice()]);
    render(<NotificationsMenu />);
    const panel = await openPanel();
    await within(panel).findByRole("link", { name: /Assertion rejected/ });

    // A poll is in flight, still carrying the old unread state...
    const stale = { list: deferred<AppNotification[]>(), count: deferred<{ unread_count: number }>() };
    mockedApi.notifications.mockReturnValueOnce(stale.list.promise);
    mockedApi.unreadNotificationCount.mockReturnValueOnce(stale.count.promise);
    act(() => {
      window.dispatchEvent(new CustomEvent(NOTIFICATIONS_CHANGED_EVENT, { detail: { source: "feed" } }));
    });

    // ...when the user reads the notice. The resync after the write answers
    // first (read), and only then does the stale poll come back (unread).
    const resync = { list: deferred<AppNotification[]>(), count: deferred<{ unread_count: number }>() };
    mockedApi.notifications.mockReturnValueOnce(resync.list.promise);
    mockedApi.unreadNotificationCount.mockReturnValueOnce(resync.count.promise);
    fireEvent.click(within(panel).getByRole("link", { name: /Assertion rejected/ }));
    await settle(); // the write resolves and the resync is sent
    expect(mockedApi.notifications).toHaveBeenCalledTimes(4); // mount, open, stale poll, resync

    await act(async () => {
      resync.list.resolve([notice({ read: true })]);
      resync.count.resolve({ unread_count: 0 });
    });
    expect(bell()).toHaveAccessibleName("Notifications");
    await act(async () => {
      stale.list.resolve([notice()]);
      stale.count.resolve({ unread_count: 1 });
    });
    expect(bell()).toHaveAccessibleName("Notifications"); // the stale answer is dropped
    expect(screen.queryByRole("dialog")).toBeNull(); // opening the notice closed the panel
  });

  it("re-fetches when another surface reports a change, and polls every 30 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    serve([]);
    render(<NotificationsMenu />);
    await waitFor(() => expect(mockedApi.notifications).toHaveBeenCalledTimes(1));

    await act(async () => {
      window.dispatchEvent(new CustomEvent(NOTIFICATIONS_CHANGED_EVENT, { detail: { source: "feed" } }));
    });
    expect(mockedApi.notifications).toHaveBeenCalledTimes(2);
    // Its own announcements do not make the bell re-fetch.
    await act(async () => {
      window.dispatchEvent(new CustomEvent(NOTIFICATIONS_CHANGED_EVENT, { detail: { source: "menu" } }));
    });
    expect(mockedApi.notifications).toHaveBeenCalledTimes(2);

    await act(async () => {
      vi.advanceTimersByTime(30_000);
    });
    expect(mockedApi.notifications).toHaveBeenCalledTimes(3);
  });

  it("closes on Escape and shows an empty state", async () => {
    serve([]);
    render(<NotificationsMenu />);
    const panel = await openPanel();
    expect(within(panel).getByText("No notifications yet.")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lets the user choose which events notify them, with ratings off by default", async () => {
    serve([]);
    const prefs: NotificationPreference[] = [
      { event_type: "assertion_submitted", enabled: true, default: true },
      { event_type: "comment_added", enabled: true, default: true },
      { event_type: "assertion_rated", enabled: false, default: false },
    ];
    mockedApi.notificationPreferences.mockResolvedValue(prefs);
    mockedApi.updateNotificationPreferences.mockResolvedValue(
      prefs.map((p) => (p.event_type === "assertion_rated" ? { ...p, enabled: true } : p)),
    );
    render(<NotificationsMenu />);
    const panel = await openPanel();
    fireEvent.click(within(panel).getByRole("button", { name: "Notification settings" }));

    const ratings = await within(panel).findByRole("checkbox", { name: /Every new rating of my assertions/ });
    expect(ratings).not.toBeChecked();
    expect(within(panel).getByRole("checkbox", { name: /submitted for review/ })).toBeChecked();

    fireEvent.click(ratings);
    expect(mockedApi.updateNotificationPreferences).toHaveBeenCalledWith({ assertion_rated: true });
    await settle();
    expect(ratings).toBeChecked();

    fireEvent.click(within(panel).getByRole("button", { name: "Back" }));
    expect(within(panel).getByText("No notifications yet.")).toBeInTheDocument();
  });

  it("restores a setting the server refused to save", async () => {
    serve([]);
    mockedApi.notificationPreferences.mockResolvedValue([
      { event_type: "comment_added", enabled: true, default: true },
    ]);
    mockedApi.updateNotificationPreferences.mockRejectedValue(new Error("nope"));
    render(<NotificationsMenu />);
    const panel = await openPanel();
    fireEvent.click(within(panel).getByRole("button", { name: "Notification settings" }));
    const box = await within(panel).findByRole("checkbox", { name: /A comment on an assertion I work on/ });

    fireEvent.click(box);
    expect(await within(panel).findByRole("alert")).toHaveTextContent("Couldn't save");
    expect(box).toBeChecked();
  });
});
