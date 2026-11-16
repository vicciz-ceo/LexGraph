// Review history card (finding ui:14): decision notes are parsed from the
// audit feed's `new_value` ("<status>" or "<status>; <key>=<free text>").

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { HistoryEvent } from "../../api/types";
import { AssertionReviewHistory, parseReviewNote } from "../AssertionReviewHistory";

function event(overrides: Partial<HistoryEvent>): HistoryEvent {
  return {
    id: "h-1",
    event_type: "assertion.accept",
    actor_user_id: "u-3",
    timestamp: "2026-07-10T09:00:00Z",
    assertion_revision_number: 1,
    previous_value: "proposed",
    new_value: "accepted",
    correlation_id: null,
    ...overrides,
  };
}

describe("parseReviewNote", () => {
  it("returns nothing for a bare status", () => {
    expect(parseReviewNote("accepted")).toBeNull();
    expect(parseReviewNote(null)).toBeNull();
    expect(parseReviewNote("")).toBeNull();
  });

  it("splits on the first '; ' and the first '=' only", () => {
    expect(parseReviewNote("accepted; acceptance_justification=a=b; c=d")).toEqual({
      key: "acceptance_justification",
      value: "a=b; c=d",
    });
  });

  it("keeps a note without a key", () => {
    expect(parseReviewNote("disputed; see the thread")).toEqual({ key: "note", value: "see the thread" });
  });
});

describe("AssertionReviewHistory", () => {
  const nameFor = (id: string) => ({ "u-3": "Riva Reviewer" })[id] ?? "Former member";
  const formatTime = (iso: string) => iso.slice(0, 10);

  it("ignores event types it does not know, so additive feed changes cannot break it", () => {
    render(
      <AssertionReviewHistory
        events={[
          event({ id: "h-1", event_type: "assertion_created" }),
          event({ id: "h-2", event_type: "some_future_event", new_value: "x; y=z" }),
        ]}
        nameFor={nameFor}
        formatTime={formatTime}
      />,
    );

    expect(screen.getByText("No review decisions recorded yet.")).toBeInTheDocument();
  });

  it("lists submit and withdraw events when the feed records them", () => {
    render(
      <AssertionReviewHistory
        events={[
          event({ id: "h-1", event_type: "assertion_submitted", previous_value: "draft", new_value: "proposed" }),
          event({ id: "h-2", event_type: "assertion_withdrawn", new_value: "withdrawn", timestamp: "2026-07-11T09:00:00Z" }),
        ]}
        nameFor={nameFor}
        formatTime={formatTime}
      />,
    );

    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Withdrawn");
    expect(items[1]).toHaveTextContent("Submitted for review");
    expect(items[1]).toHaveTextContent("from Draft");
  });

  it("tolerates an event without a revision number", () => {
    render(
      <AssertionReviewHistory
        events={[event({ assertion_revision_number: null, actor_user_id: "u-9" })]}
        nameFor={nameFor}
        formatTime={formatTime}
      />,
    );

    expect(screen.getByText("Accepted")).toBeInTheDocument();
    expect(screen.queryByText(/revision/)).not.toBeInTheDocument();
    expect(screen.getByText("Former member · 2026-07-10")).toBeInTheDocument();
  });
});
