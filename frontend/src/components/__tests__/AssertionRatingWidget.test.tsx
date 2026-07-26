// UI1 — accessible 1-5 rating widget (spec §5, gate G11).
//
// Import-failure RED (documented exception, Planner brief §4): the
// component module does not exist yet — only a Developer track (UI1)
// creates `../AssertionRatingWidget`. Vitest reports this file as a
// module-resolution failure, not an assertion failure; that is the
// accepted RED shape for frontend component files ONLY.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionRatingWidget } from "../AssertionRatingWidget";

describe("AssertionRatingWidget", () => {
  it("renders five selectable values with numeric and text labels", () => {
    render(<AssertionRatingWidget currentUserRating={null} onSave={vi.fn()} onRemove={vi.fn()} />);
    for (const value of [1, 2, 3, 4, 5]) {
      expect(screen.getByRole("radio", { name: new RegExp(String(value)) })).toBeInTheDocument();
    }
  });

  it("exposes a screen-reader label for each value", () => {
    render(<AssertionRatingWidget currentUserRating={null} onSave={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /1.*very weak/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /5.*very strong/i })).toBeInTheDocument();
  });

  it("supports keyboard navigation between values", async () => {
    render(<AssertionRatingWidget currentUserRating={null} onSave={vi.fn()} onRemove={vi.fn()} />);
    const group = screen.getByRole("radiogroup");
    group.focus();
    fireEvent.keyDown(group, { key: "ArrowRight" });
    expect(screen.getByRole("radio", { name: /1/ })).not.toHaveFocus();
  });

  it("shows a clearly visible selected state for the current user's rating", () => {
    render(<AssertionRatingWidget currentUserRating={4} onSave={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /4/, checked: true } as never)).toBeInTheDocument();
  });

  it("submits the selected strength and optional rationale on save", () => {
    const onSave = vi.fn();
    render(<AssertionRatingWidget currentUserRating={null} onSave={onSave} onRemove={vi.fn()} />);
    fireEvent.click(screen.getByRole("radio", { name: /3/ }));
    fireEvent.change(screen.getByLabelText(/rationale/i), { target: { value: "Plausible reading." } });
    fireEvent.click(screen.getByRole("button", { name: /save|update/i }));
    expect(onSave).toHaveBeenCalledWith({ strength: 3, rationale: "Plausible reading." });
  });

  it("offers a remove-rating action when the user already has a rating", () => {
    const onRemove = vi.fn();
    render(<AssertionRatingWidget currentUserRating={2} onSave={vi.fn()} onRemove={onRemove} />);
    fireEvent.click(screen.getByRole("button", { name: /remove/i }));
    expect(onRemove).toHaveBeenCalled();
  });

  it("shows success feedback after a save resolves", async () => {
    render(
      <AssertionRatingWidget
        currentUserRating={null}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onRemove={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("radio", { name: /5/ }));
    fireEvent.click(screen.getByRole("button", { name: /save|update/i }));
    expect(await screen.findByText(/saved|updated/i)).toBeInTheDocument();
  });

  it("shows error feedback when the save rejects", async () => {
    render(
      <AssertionRatingWidget
        currentUserRating={null}
        onSave={vi.fn().mockRejectedValue(new Error("network error"))}
        onRemove={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("radio", { name: /2/ }));
    fireEvent.click(screen.getByRole("button", { name: /save|update/i }));
    expect(await screen.findByText(/error|failed/i)).toBeInTheDocument();
  });
});
