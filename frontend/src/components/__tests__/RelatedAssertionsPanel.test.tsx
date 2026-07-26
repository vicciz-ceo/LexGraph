// UI3 — duplicate/related-assertion surfacing (spec §8). Import-failure
// RED (documented exception) until Developer track UI3 creates
// `../RelatedAssertionsPanel`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RelatedAssertionsPanel } from "../RelatedAssertionsPanel";

const related = [
  { id: "r1", proposition: "A very similar proposition about Clause 8.4.", matchKind: "similar" },
  { id: "r2", proposition: "Clause 8.4 creates a limited exception to Clause 8.2.", matchKind: "exact_proposition" },
];

describe("RelatedAssertionsPanel", () => {
  it("lists related/duplicate candidates with their match kind", () => {
    render(<RelatedAssertionsPanel related={related} onOpen={vi.fn()} onRateInstead={vi.fn()} onMarkRelation={vi.fn()} />);
    expect(screen.getByText(/similar/i)).toBeInTheDocument();
    expect(screen.getByText(/exact/i)).toBeInTheDocument();
  });

  it("lets the user open an existing related assertion", () => {
    const onOpen = vi.fn();
    render(<RelatedAssertionsPanel related={related} onOpen={onOpen} onRateInstead={vi.fn()} onMarkRelation={vi.fn()} />);
    fireEvent.click(screen.getAllByRole("button", { name: /open/i })[0]);
    expect(onOpen).toHaveBeenCalledWith("r1");
  });

  it("lets the user rate the existing assertion instead of submitting a new one", () => {
    const onRateInstead = vi.fn();
    render(<RelatedAssertionsPanel related={related} onOpen={vi.fn()} onRateInstead={onRateInstead} onMarkRelation={vi.fn()} />);
    fireEvent.click(screen.getAllByRole("button", { name: /rate.*instead/i })[0]);
    expect(onRateInstead).toHaveBeenCalledWith("r1");
  });

  it("lets the user mark the new assertion as contradicting or qualifying a related one", () => {
    const onMarkRelation = vi.fn();
    render(<RelatedAssertionsPanel related={related} onOpen={vi.fn()} onRateInstead={vi.fn()} onMarkRelation={onMarkRelation} />);
    fireEvent.click(screen.getAllByRole("button", { name: /mark as contradicting/i })[0]);
    expect(onMarkRelation).toHaveBeenCalledWith("r1", "contradicts");
  });

  it("never auto-merges — no merge action is offered", () => {
    render(<RelatedAssertionsPanel related={related} onOpen={vi.fn()} onRateInstead={vi.fn()} onMarkRelation={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /^merge$/i })).not.toBeInTheDocument();
  });
});
