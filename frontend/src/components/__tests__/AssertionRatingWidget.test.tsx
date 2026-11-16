// UI1 — accessible 1-5 rating widget (spec §5, gate G11).
//
// Import-failure RED (documented exception, Planner brief §4): the
// component module does not exist yet — only a Developer track (UI1)
// creates `../AssertionRatingWidget`. Vitest reports this file as a
// module-resolution failure, not an assertion failure; that is the
// accepted RED shape for frontend component files ONLY.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { createRoot } from "react-dom/client";
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

it("retains the saved rationale when changing only the strength", async () => {
  const onSave = vi.fn();
  render(<AssertionRatingWidget currentUserRating={3} currentRationale="Exact source supports the claim." onSave={onSave} onRemove={vi.fn()} />);
  expect(screen.getByLabelText("Rationale (optional)")).toHaveValue("Exact source supports the claim.");
  fireEvent.click(screen.getByRole("radio", { name: "4 - Strong" }));
  fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
  // The untouched rationale is left out, so the API keeps the stored text
  // byte for byte (spec §13; review listing:0), and the box still shows it.
  expect(onSave.mock.calls[0][0]).toStrictEqual({ strength: 4 });
  expect(screen.getByLabelText("Rationale (optional)")).toHaveValue("Exact source supports the claim.");
});

// Review listing:0: PUT .../rating with `rationale: ""` removes the stored
// rationale and an omitted one keeps it (spec §13). The widget sends the box
// only when the user edited it, so a save from an editor that was not
// prefilled with the stored text (a failed load, a stale tab) cannot erase it.
describe("AssertionRatingWidget rationale (listing:0)", () => {
  function saved(onSave: ReturnType<typeof vi.fn>, call = 0) {
    return onSave.mock.calls[call][0] as Record<string, unknown>;
  }

  it("leaves the rationale out of a save when the prefilled box was not edited", () => {
    const onSave = vi.fn();
    render(<AssertionRatingWidget currentUserRating={3} currentRationale="Exact source." onSave={onSave} onRemove={vi.fn()} />);
    fireEvent.click(screen.getByRole("radio", { name: "4 - Strong" }));
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(saved(onSave)).toStrictEqual({ strength: 4 });
  });

  it("leaves the rationale out when the box of a new rating was never touched", () => {
    const onSave = vi.fn();
    render(<AssertionRatingWidget currentUserRating={null} onSave={onSave} onRemove={vi.fn()} />);
    fireEvent.click(screen.getByRole("radio", { name: "2 - Weak" }));
    fireEvent.click(screen.getByRole("button", { name: "Save rating" }));
    expect(saved(onSave)).toStrictEqual({ strength: 2 });
  });

  it("sends a box the user emptied as an empty rationale, which removes it", () => {
    const onSave = vi.fn();
    render(<AssertionRatingWidget currentUserRating={3} currentRationale="Exact source." onSave={onSave} onRemove={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Rationale (optional)"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(saved(onSave)).toStrictEqual({ strength: 3, rationale: "" });
  });

  it("sends the box again only after a new edit, once a save went through", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<AssertionRatingWidget currentUserRating={3} currentRationale="" onSave={onSave} onRemove={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Rationale (optional)"), { target: { value: "Clause 8.2." } });
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(await screen.findByText("Rating updated.")).toBeInTheDocument();
    expect(saved(onSave)).toStrictEqual({ strength: 3, rationale: "Clause 8.2." });

    fireEvent.click(screen.getByRole("radio", { name: "5 - Very strong" }));
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(saved(onSave, 1)).toStrictEqual({ strength: 5 });
  });

  it("keeps trying to send an edit whose save failed", async () => {
    const onSave = vi.fn().mockRejectedValueOnce(new Error("network error")).mockResolvedValue(undefined);
    render(<AssertionRatingWidget currentUserRating={3} currentRationale="" onSave={onSave} onRemove={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Rationale (optional)"), { target: { value: "Clause 8.2." } });
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(await screen.findByText(/Failed to save rating/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(saved(onSave, 1)).toStrictEqual({ strength: 3, rationale: "Clause 8.2." });
  });

  it("follows a newly loaded rationale and forgets an edit made against the old one", () => {
    const onSave = vi.fn();
    const { rerender } = render(
      <AssertionRatingWidget currentUserRating={3} currentRationale="Old text." onSave={onSave} onRemove={vi.fn()} />,
    );
    fireEvent.change(screen.getByLabelText("Rationale (optional)"), { target: { value: "Draft." } });
    rerender(
      <AssertionRatingWidget currentUserRating={4} currentRationale="Saved elsewhere." onSave={onSave} onRemove={vi.fn()} />,
    );
    expect(screen.getByLabelText("Rationale (optional)")).toHaveValue("Saved elsewhere.");
    fireEvent.click(screen.getByRole("button", { name: "Update rating" }));
    expect(saved(onSave)).toStrictEqual({ strength: 4 });
  });
});

// XREQ-96: "saves a strength rating against the current revision" on the
// detail page failed now and then. The widget re-syncs its selection from
// its props in an effect, and React runs a mount's effects in a later task
// when the mount was not urgent (data that arrived). A click landing in
// between (the order of those tasks varies under load) was undone by that
// late effect: the selection fell back to the props, Save stayed disabled
// and nothing was saved. React's scheduler runs a mount's effects in the
// same task unless the render outlasts its time slice, as the large detail
// page can under load. Rendering outside act() next to a slow sibling and
// clicking from a MutationObserver reproduces that order deterministically.
// (jsdom keeps an earlier test's click as window.event, which would make
// React treat this mount as urgent and run its effects at once; the stub
// hides it while mounting.)
function SlowSibling(): null {
  const end = performance.now() + 20;
  while (performance.now() < end) {
    // A render longer than the scheduler's time slice (5 ms).
  }
  return null;
}

describe("AssertionRatingWidget mounted by data that just arrived", () => {
  it("keeps a selection made before its mount effects have run", async () => {
    const reactGlobal = globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean };
    const previous = reactGlobal.IS_REACT_ACT_ENVIRONMENT;
    reactGlobal.IS_REACT_ACT_ENVIRONMENT = false;
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    const noEvent = vi.spyOn(window, "event", "get").mockReturnValue(undefined);
    try {
      const clicked = new Promise<void>((resolve) => {
        const observer = new MutationObserver(() => {
          const radio = container.querySelector<HTMLElement>('[aria-label="4 - Strong"]');
          if (!radio) return;
          observer.disconnect();
          noEvent.mockRestore();
          radio.click(); // before the scheduled mount effects
          resolve();
        });
        observer.observe(container, { childList: true, subtree: true });
      });
      root.render(
        <>
          <SlowSibling />
          <AssertionRatingWidget currentUserRating={null} onSave={vi.fn()} onRemove={vi.fn()} />
        </>,
      );
      await clicked;
      await new Promise((resolve) => setTimeout(resolve, 50));

      const strong = container.querySelector('[aria-label="4 - Strong"]');
      expect(strong).toHaveAttribute("aria-checked", "true");
      expect(within(container).getByRole("button", { name: "Save rating" })).toBeEnabled();
    } finally {
      noEvent.mockRestore();
      root.unmount();
      container.remove();
      reactGlobal.IS_REACT_ACT_ENVIRONMENT = previous;
    }
  });
});
