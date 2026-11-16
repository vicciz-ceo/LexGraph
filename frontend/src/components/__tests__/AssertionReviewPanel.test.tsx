// UI3 — reviewer panel: accept/reject/dispute/request-revision, gate G11.
// Import-failure RED (documented exception) until Developer track UI3
// creates `../AssertionReviewPanel`.

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionReviewPanel } from "../AssertionReviewPanel";
import type { AssertionReviewPanelProps } from "../AssertionReviewPanel";

describe("AssertionReviewPanel", () => {
  it("offers accept, reject, dispute, and request-revision actions", () => {
    render(
      <AssertionReviewPanel
        assertion={{ id: "a1", status: "proposed", evidenceStatus: "unsupported" }}
        onAccept={vi.fn()}
        onReject={vi.fn()}
        onDispute={vi.fn()}
        onRequestRevision={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /accept/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dispute/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /request revision/i })).toBeInTheDocument();
  });

  it("requires a recorded justification to accept an unsupported assertion", () => {
    render(
      <AssertionReviewPanel
        assertion={{ id: "a1", status: "proposed", evidenceStatus: "unsupported" }}
        onAccept={vi.fn()}
        onReject={vi.fn()}
        onDispute={vi.fn()}
        onRequestRevision={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /accept/i }));
    expect(screen.getByLabelText(/justification/i)).toBeInTheDocument();
  });

  it("calls onAccept with the justification once provided", () => {
    const onAccept = vi.fn();
    render(
      <AssertionReviewPanel
        assertion={{ id: "a1", status: "proposed", evidenceStatus: "unsupported" }}
        onAccept={onAccept}
        onReject={vi.fn()}
        onDispute={vi.fn()}
        onRequestRevision={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /accept/i }));
    fireEvent.change(screen.getByLabelText(/justification/i), {
      target: { value: "Accepted on independent legal knowledge." },
    });
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
    expect(onAccept).toHaveBeenCalledWith({ justification: "Accepted on independent legal knowledge." });
  });

  it("does not require justification to accept a supported assertion", () => {
    const onAccept = vi.fn();
    render(
      <AssertionReviewPanel
        assertion={{ id: "a1", status: "proposed", evidenceStatus: "supported" }}
        onAccept={onAccept}
        onReject={vi.fn()}
        onDispute={vi.fn()}
        onRequestRevision={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /accept/i }));
    expect(onAccept).toHaveBeenCalled();
  });

  it("requires a comment when requesting revision", () => {
    render(
      <AssertionReviewPanel
        assertion={{ id: "a1", status: "proposed", evidenceStatus: "supported" }}
        onAccept={vi.fn()}
        onReject={vi.fn()}
        onDispute={vi.fn()}
        onRequestRevision={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /request revision/i }));
    expect(screen.getByLabelText(/comment/i)).toBeInTheDocument();
  });
});

// Review decision rules mirrored from the API (spec addendum "Review decision
// rules (2026-11-16)"): ui:9 (status), ui:8 (justification), ui:24 (ids and
// the revision comment).
describe("AssertionReviewPanel decision rules", () => {
  function renderPanel(
    assertion: Partial<AssertionReviewPanelProps["assertion"]> = {},
    props: Partial<AssertionReviewPanelProps> = {},
  ) {
    const handlers = {
      onAccept: vi.fn(),
      onReject: vi.fn(),
      onDispute: vi.fn(),
      onRequestRevision: vi.fn(),
    };
    render(
      <AssertionReviewPanel
        assertion={{ id: "a1", status: "proposed", evidenceStatus: "supported", ...assertion }}
        {...handlers}
        {...props}
      />,
    );
    return { ...handlers, ...props };
  }

  const buttonLabels = () => screen.queryAllByRole("button").map((button) => button.textContent);

  it.each(["draft", "withdrawn", "superseded"])(
    "offers no decision on a %s assertion and says why",
    (status) => {
      renderPanel({ status });
      expect(buttonLabels()).toEqual([]);
      expect(screen.getByText(/no review decision/i)).toBeInTheDocument();
    },
  );

  it("tells the reviewer that a draft must be submitted first", () => {
    renderPanel({ status: "draft" });
    expect(screen.getByText(/submitted for review/i)).toBeInTheDocument();
  });

  it.each([
    ["proposed", ["Accept", "Reject", "Dispute", "Request revision"]],
    ["revision_requested", ["Accept", "Reject", "Dispute"]],
    ["disputed", ["Accept", "Reject", "Request revision"]],
    ["accepted", ["Reject", "Dispute", "Request revision"]],
    ["rejected", ["Accept", "Dispute", "Request revision"]],
  ])("offers only the decisions that change a %s assertion", (status, expected) => {
    renderPanel({ status });
    expect(buttonLabels()).toEqual(expected);
  });

  it("styles each decision by what it does, not by its position", () => {
    renderPanel({ status: "accepted" });
    expect(screen.getByRole("button", { name: "Reject" })).toHaveClass(
      "assertion-review-action--reject",
    );
    expect(screen.getByRole("button", { name: "Dispute" })).not.toHaveClass(
      "assertion-review-action--reject",
    );
  });

  it("disables every action while the parent reports a decision in flight", () => {
    renderPanel({ status: "proposed", evidenceStatus: "unsupported" }, { busy: true });
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  });

  it("records a decision once when it is activated again before the first one finishes", async () => {
    let finish: (recorded: boolean) => void = () => {};
    const onReject = vi.fn(
      () =>
        new Promise<boolean>((resolve) => {
          finish = resolve;
        }),
    );
    renderPanel({}, { onReject });
    const reject = screen.getByRole("button", { name: "Reject" });

    // Two activations in one tick, before React has re-rendered the
    // button as disabled: only a synchronous guard stops the second one.
    act(() => {
      reject.click();
      reject.click();
    });
    // And further clicks while the first decision is still being recorded.
    fireEvent.click(reject);

    expect(onReject).toHaveBeenCalledTimes(1);
    expect(reject).toBeDisabled();
    await act(async () => finish(true));
    expect(reject).toBeEnabled();
  });

  it("keeps Confirm disabled until the justification has text, and sends it trimmed", () => {
    const { onAccept } = renderPanel({ evidenceStatus: "unsupported" });
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    const confirm = screen.getByRole("button", { name: "Confirm" });
    const textarea = screen.getByLabelText(/justification/i);

    expect(confirm).toBeDisabled();
    fireEvent.change(textarea, { target: { value: "   \n\t  " } });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(onAccept).not.toHaveBeenCalled();

    fireEvent.change(textarea, { target: { value: "  Counsel confirmed the clause.  " } });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(onAccept).toHaveBeenCalledWith({ justification: "Counsel confirmed the clause." });
  });

  it("keeps Confirm disabled until the revision comment has text, says it is required, and sends it trimmed", () => {
    const { onRequestRevision } = renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Request revision" }));
    const confirm = screen.getByRole("button", { name: "Confirm" });
    const textarea = screen.getByLabelText(/comment/i);

    expect(textarea).toHaveAccessibleDescription(/required/i);
    expect(confirm).toBeDisabled();
    fireEvent.change(textarea, { target: { value: "    " } });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(onRequestRevision).not.toHaveBeenCalled();

    fireEvent.change(textarea, { target: { value: "\nPlease cite clause 8.4.\n" } });
    fireEvent.click(confirm);
    expect(onRequestRevision).toHaveBeenCalledWith({ comment: "Please cite clause 8.4." });
  });

  it("refuses review text over the 100,000-character limit before sending it", () => {
    const { onAccept } = renderPanel({ evidenceStatus: "unsupported" });
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    const confirm = screen.getByRole("button", { name: "Confirm" });
    const textarea = screen.getByLabelText(/justification/i);

    fireEvent.change(textarea, { target: { value: "x".repeat(100_001) } });
    expect(confirm).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("100,000");
    fireEvent.click(confirm);
    expect(onAccept).not.toHaveBeenCalled();

    fireEvent.change(textarea, { target: { value: "x".repeat(100_000) } });
    expect(confirm).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps the typed justification when the decision is not recorded, and closes once it is", async () => {
    const onAccept = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    renderPanel({ evidenceStatus: "unsupported" }, { onAccept });
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    fireEvent.change(screen.getByLabelText(/justification/i), {
      target: { value: "Counsel confirmed the clause." },
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    });
    expect(screen.getByLabelText(/justification/i)).toHaveValue("Counsel confirmed the clause.");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    });
    expect(onAccept).toHaveBeenCalledTimes(2);
    expect(screen.queryByLabelText(/justification/i)).not.toBeInTheDocument();
  });

  // Review fe-review-detail:2: the page showed supporting evidence that was
  // removed meanwhile, so the API asked for a justification after all.
  it("opens the justification form when an acceptance turns out to need one", async () => {
    const onAccept = vi
      .fn()
      .mockResolvedValueOnce("needs-justification")
      .mockResolvedValueOnce(true);
    renderPanel({ evidenceStatus: "evidenced" }, { onAccept });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    });
    expect(onAccept).toHaveBeenCalledWith({});
    const textarea = screen.getByLabelText(/justification/i);
    expect(screen.getByRole("button", { name: "Confirm" })).toBeDisabled();

    fireEvent.change(textarea, { target: { value: "  Counsel confirmed the clause.  " } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    });
    expect(onAccept).toHaveBeenLastCalledWith({ justification: "Counsel confirmed the clause." });
    expect(screen.queryByLabelText(/justification/i)).not.toBeInTheDocument();
  });

  it("gives every panel its own form ids, so each label points at its own textarea", () => {
    const props = {
      onAccept: vi.fn(),
      onReject: vi.fn(),
      onDispute: vi.fn(),
      onRequestRevision: vi.fn(),
    };
    const { container } = render(
      <>
        <AssertionReviewPanel
          assertion={{ id: "a1", status: "proposed", evidenceStatus: "unsupported" }}
          {...props}
        />
        <AssertionReviewPanel
          assertion={{ id: "a2", status: "proposed", evidenceStatus: "unsupported" }}
          {...props}
        />
      </>,
    );
    const panels = Array.from(container.querySelectorAll<HTMLElement>(".assertion-review-panel"));
    expect(panels).toHaveLength(2);

    for (const [buttonName, labelText] of [
      ["Request revision", "Comment explaining the requested revision"],
      ["Accept", "Justification for accepting without supporting evidence"],
    ]) {
      for (const panel of panels) {
        fireEvent.click(within(panel).getByRole("button", { name: buttonName }));
      }
      const ids = Array.from(container.querySelectorAll("[id]")).map((element) => element.id);
      expect(new Set(ids).size).toBe(ids.length);
      for (const panel of panels) {
        const label = within(panel).getByText(labelText) as HTMLLabelElement;
        expect(label.control).not.toBeNull();
        expect(panel).toContainElement(label.control as HTMLElement);
      }
      for (const panel of panels) {
        fireEvent.click(within(panel).getByRole("button", { name: "Cancel" }));
      }
    }
  });
});
