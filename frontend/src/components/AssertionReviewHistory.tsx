// Review history for one assertion (spec §5 "Review history", finding
// ui:14), built from GET /assertions/{id}/history. Only review-workflow
// events are listed: decisions written by the review router, plus submit and
// withdraw events when the audit feed records them. Creation, revision,
// comment, evidence and rating rows are left out (rating rows carry other
// users' individual strengths). An event type this page does not know is
// skipped, so additive changes to the feed never break the card.

import type { ReactElement } from "react";

import type { HistoryEvent } from "../api/types";
import { Link } from "../app/router";

interface ReviewEventKind {
  label: string;
  /** Badge modifier (the status the event moves the assertion to). */
  badge: string;
}

export const REVIEW_EVENT_KINDS: Record<string, ReviewEventKind> = {
  "assertion.accept": { label: "Accepted", badge: "accepted" },
  "assertion.reject": { label: "Rejected", badge: "rejected" },
  "assertion.dispute": { label: "Marked disputed", badge: "disputed" },
  "assertion.request_revision": { label: "Revision requested", badge: "revision_requested" },
  "assertion.supersede": { label: "Superseded", badge: "superseded" },
  "assertion.submit": { label: "Submitted for review", badge: "proposed" },
  assertion_submitted: { label: "Submitted for review", badge: "proposed" },
  "assertion.withdraw": { label: "Withdrawn", badge: "withdrawn" },
  assertion_withdrawn: { label: "Withdrawn", badge: "withdrawn" },
};

const NOTE_LABELS: Record<string, string> = {
  acceptance_justification: "Justification",
  comment: "Comment",
};

const STATUS_WORD = /^[a-z_]+$/;

export interface ReviewNote {
  key: string;
  value: string;
}

/**
 * Split a decision's `new_value` ("accepted" or "accepted; key=free text")
 * into its note. Only the first "; " and the first "=" separate: the free
 * text may contain both.
 */
export function parseReviewNote(newValue: string | null | undefined): ReviewNote | null {
  if (!newValue) return null;
  const separator = newValue.indexOf("; ");
  if (separator < 0) return null;
  const rest = newValue.slice(separator + 2);
  const equals = rest.indexOf("=");
  if (equals <= 0) return rest.trim() ? { key: "note", value: rest } : null;
  return { key: rest.slice(0, equals), value: rest.slice(equals + 1) };
}

function labelize(value: string): string {
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export interface AssertionReviewHistoryProps {
  /** `null` when the history could not be loaded. */
  events: HistoryEvent[] | null;
  nameFor: (userId: string) => string;
  formatTime: (iso: string) => string;
  /** A system_generated assertion: the pipeline stored it as accepted. */
  systemGenerated?: boolean;
}

export function AssertionReviewHistory({
  events,
  nameFor,
  formatTime,
  systemGenerated = false,
}: AssertionReviewHistoryProps): ReactElement {
  const systemNote = systemGenerated ? (
    <p className="muted adp-review-system-note">
      The definition-linking pipeline stores the links it generates as accepted; that status is
      not a reviewer&apos;s decision.
    </p>
  ) : null;
  const decisions = (events ?? [])
    .filter((event) => REVIEW_EVENT_KINDS[event.event_type] !== undefined)
    .slice()
    .reverse();
  let body: ReactElement;
  if (events === null) {
    body = <p className="muted">Review history could not be loaded.</p>;
  } else if (decisions.length === 0) {
    body = <p className="muted">No review decisions recorded yet.</p>;
  } else {
    body = <ReviewEventList decisions={decisions} nameFor={nameFor} formatTime={formatTime} />;
  }
  return (
    <>
      {systemNote}
      {body}
    </>
  );
}

function ReviewEventList({
  decisions,
  nameFor,
  formatTime,
}: {
  decisions: HistoryEvent[];
  nameFor: (userId: string) => string;
  formatTime: (iso: string) => string;
}): ReactElement {
  return (
    <ol className="adp-review-history">
      {decisions.map((event) => {
        const kind = REVIEW_EVENT_KINDS[event.event_type];
        const note = parseReviewNote(event.new_value);
        const previous =
          event.previous_value && STATUS_WORD.test(event.previous_value) ? event.previous_value : null;
        return (
          <li key={event.id} className="adp-review-event">
            <div className="adp-review-event-title">
              <span className={`badge badge--${kind.badge}`}>{kind.label}</span>
              {event.assertion_revision_number != null && (
                <span className="muted">revision {event.assertion_revision_number}</span>
              )}
              {previous && <span className="muted">from {labelize(previous)}</span>}
            </div>
            <div className="muted adp-review-event-meta">
              {nameFor(event.actor_user_id)} · {formatTime(event.timestamp)}
            </div>
            {note && note.key === "superseded_by_assertion_id" ? (
              <p className="adp-review-event-note">
                Replaced by{" "}
                <Link to={`/assertions/${encodeURIComponent(note.value)}`}>the superseding assertion</Link>
              </p>
            ) : note ? (
              <p className="adp-review-event-note">
                {NOTE_LABELS[note.key] ?? labelize(note.key)}: {note.value}
              </p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
