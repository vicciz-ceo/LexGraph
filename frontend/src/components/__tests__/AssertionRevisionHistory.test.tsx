// UI3 — revision history + comparison entry point (spec §3). Import-
// failure RED (documented exception) until Developer track UI3 creates
// `../AssertionRevisionHistory`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionRevisionHistory } from "../AssertionRevisionHistory";

const revisions = [
  { revisionNumber: 1, proposition: "Original proposition.", editedBy: "Contributor A", createdAt: "2026-07-20T10:00:00Z", revisionReason: null },
  { revisionNumber: 2, proposition: "A materially different proposition.", editedBy: "Contributor A", createdAt: "2026-07-21T10:00:00Z", revisionReason: "Clarified scope" },
];

describe("AssertionRevisionHistory", () => {
  it("lists every revision with its number and author", () => {
    render(<AssertionRevisionHistory revisions={revisions} onCompare={vi.fn()} />);
    expect(screen.getByText(/revision 1/i)).toBeInTheDocument();
    expect(screen.getByText(/revision 2/i)).toBeInTheDocument();
  });

  it("keeps the original revision text visible", () => {
    render(<AssertionRevisionHistory revisions={revisions} onCompare={vi.fn()} />);
    expect(screen.getByText("Original proposition.")).toBeInTheDocument();
  });

  it("lets the user select two revisions to compare", () => {
    const onCompare = vi.fn();
    render(<AssertionRevisionHistory revisions={revisions} onCompare={onCompare} />);
    fireEvent.click(screen.getByLabelText(/select revision 1 for comparison/i));
    fireEvent.click(screen.getByLabelText(/select revision 2 for comparison/i));
    fireEvent.click(screen.getByRole("button", { name: /compare/i }));
    expect(onCompare).toHaveBeenCalledWith(1, 2);
  });

  it("shows the revision reason when present", () => {
    render(<AssertionRevisionHistory revisions={revisions} onCompare={vi.fn()} />);
    expect(screen.getByText("Clarified scope")).toBeInTheDocument();
  });

  // Track A, item A7 (issue #2 / gate G1): revision history is a
  // diff/compare-classified read path, so it must render the RAW authored
  // proposition -- byte-exact, including angle-bracket prose the sanitizer
  // legitimately alters -- as a plain text node (never
  // dangerouslySetInnerHTML). RED against the current component, which only
  // knows about the (possibly lossy) sanitized `proposition` field.
  it("renders the raw authored proposition byte-exact, preserving angle-bracket prose", () => {
    const rawText = "see <appendix A> for details, per Clause 9.1.";
    const revisionsWithRaw = [
      {
        revisionNumber: 1,
        proposition: "see  for details, per Clause 9.1.",
        propositionRaw: rawText,
        editedBy: "Contributor A",
      },
    ];
    render(<AssertionRevisionHistory revisions={revisionsWithRaw} onCompare={vi.fn()} />);
    expect(screen.getByText(rawText)).toBeInTheDocument();
  });
});
