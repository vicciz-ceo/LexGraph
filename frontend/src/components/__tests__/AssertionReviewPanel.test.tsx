// UI3 — reviewer panel: accept/reject/dispute/request-revision, gate G11.
// Import-failure RED (documented exception) until Developer track UI3
// creates `../AssertionReviewPanel`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionReviewPanel } from "../AssertionReviewPanel";

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
