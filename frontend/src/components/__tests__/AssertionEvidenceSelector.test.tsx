// UI2 — evidence selector (add/remove supporting/contradicting spans,
// spec §6). Import-failure RED (documented exception) until Developer
// track UI2 creates `../AssertionEvidenceSelector`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionEvidenceSelector } from "../AssertionEvidenceSelector";
import type { AssertionEvidenceItem } from "../AssertionEvidenceSelector";

const evidence: AssertionEvidenceItem[] = [
  { id: "e1", sourceSpanId: "s1", evidenceRole: "supports", quote: "text A" },
  { id: "e2", sourceSpanId: "s2", evidenceRole: "contradicts", quote: "text B" },
];

describe("AssertionEvidenceSelector", () => {
  it("lists existing evidence with its role", () => {
    render(<AssertionEvidenceSelector evidence={evidence} onAdd={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByText(/text A/)).toBeInTheDocument();
    expect(screen.getByText(/supports/i)).toBeInTheDocument();
    expect(screen.getByText(/text B/)).toBeInTheDocument();
    expect(screen.getByText(/contradicts/i)).toBeInTheDocument();
  });

  it("supports adding supporting evidence", () => {
    const onAdd = vi.fn();
    render(<AssertionEvidenceSelector evidence={[]} onAdd={onAdd} onRemove={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add supporting evidence/i }));
    expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ evidenceRole: "supports" }));
  });

  it("supports adding contradicting evidence", () => {
    const onAdd = vi.fn();
    render(<AssertionEvidenceSelector evidence={[]} onAdd={onAdd} onRemove={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add contradicting evidence/i }));
    expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ evidenceRole: "contradicts" }));
  });

  it("supports removing an evidence entry", () => {
    const onRemove = vi.fn();
    render(<AssertionEvidenceSelector evidence={evidence} onAdd={vi.fn()} onRemove={onRemove} />);
    fireEvent.click(screen.getAllByRole("button", { name: /remove/i })[0]);
    expect(onRemove).toHaveBeenCalledWith("e1");
  });

  it("supports searching for source spans to attach", () => {
    render(<AssertionEvidenceSelector evidence={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/search/i), { target: { value: "notification" } });
    expect(screen.getByLabelText(/search/i)).toHaveValue("notification");
  });

  it("lets the user indicate that further evidence is needed", () => {
    render(<AssertionEvidenceSelector evidence={[]} onAdd={vi.fn()} onRemove={vi.fn()} />);
    expect(screen.getByLabelText(/further evidence needed/i)).toBeInTheDocument();
  });
});
