// Notification wording and the cross-surface "changed" signal, shared by
// the topbar bell and the Profile page's Notifications tab. Kept out of
// api/client.ts so page tests that mock the client keep working.

import type { AppNotification } from "../api/types";

/** Fired on window after a surface marks notifications read, so the
 * other surface (bell vs. Profile tab) re-fetches instead of disagreeing. */
export const NOTIFICATIONS_CHANGED_EVENT = "lexgraph:notifications-changed";

export function announceNotificationsChanged(source: string): void {
  window.dispatchEvent(new CustomEvent(NOTIFICATIONS_CHANGED_EVENT, { detail: { source } }));
}

/** Labels for the per-user switches (GET/PUT /notifications/preferences). */
export const NOTIFICATION_PREFERENCE_LABELS: Record<string, string> = {
  assertion_submitted: "An assertion is submitted for review (reviewers)",
  revision_requested: "A reviewer requests a revision of my assertion",
  assertion_accepted: "My assertion is accepted",
  assertion_rejected: "My assertion is rejected",
  assertion_disputed: "My assertion is disputed",
  assertion_superseded: "My assertion is superseded",
  revision_created: "A new revision of an assertion I work on",
  evidence_added: "Evidence added to an assertion I work on",
  comment_added: "A comment on an assertion I work on",
  assertion_rated: "Every new rating of my assertions",
};

function humanize(eventType: string): string {
  const label = eventType.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** One-line title for a notification; unknown event types are humanized. */
export function notificationTitle(n: AppNotification): string {
  const payload = n.payload ?? {};
  switch (n.event_type) {
    case "assertion_submitted":
      return payload.previous_status === "revision_requested"
        ? "Assertion resubmitted for review"
        : "Assertion submitted for review";
    case "revision_created": {
      const number = typeof payload.revision_number === "number" ? ` ${payload.revision_number}` : "";
      return payload.previous_status === "accepted" && payload.status === "proposed"
        ? `Revision${number} created, back in review`
        : `Revision${number} created`;
    }
    case "comment_added":
      return payload.parent_comment_id ? "Reply in a discussion" : "Comment added";
    case "assertion_rated":
      return typeof payload.strength === "number"
        ? `Rated ${payload.strength}/5`
        : "Assertion rated";
    default:
      return humanize(n.event_type);
  }
}

/** "Riva Reviewer · MSA matter" for the item's second line, when known. */
export function notificationByline(n: AppNotification): string {
  const parts = [n.context?.actor_display_name, n.context?.matter_name].filter(
    (part): part is string => Boolean(part),
  );
  return parts.join(" · ");
}
