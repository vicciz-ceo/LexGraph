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

  // Findings ui:15 / pipeline:8: mounted as the detail page's Activity
  // timeline, which marks the current revision and shows each revision's
  // ratings below it.
  it("marks the current revision and renders the caller's footer per revision", () => {
    render(
      <AssertionRevisionHistory
        revisions={revisions}
        currentRevisionNumber={2}
        onCompare={vi.fn()}
        renderFooter={(n) => <button type="button">{`Ratings of ${n}`}</button>}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items[1]).toHaveTextContent("current");
    expect(items[0]).not.toHaveTextContent("current");
    expect(screen.getByRole("button", { name: "Ratings of 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ratings of 2" })).toBeInTheDocument();
  });

  it("enables Compare only with exactly two revisions selected, keeping the latest two", () => {
    const onCompare = vi.fn();
    render(
      <AssertionRevisionHistory
        revisions={[...revisions, { revisionNumber: 3, proposition: "Third.", editedBy: "Reviewer B" }]}
        onCompare={onCompare}
      />,
    );
    const compare = screen.getByRole("button", { name: "Compare selected revisions" });
    expect(compare).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Select revision 3 for comparison"));
    expect(compare).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Select revision 1 for comparison"));
    fireEvent.click(screen.getByLabelText("Select revision 2 for comparison"));
    // Selecting a third revision drops the first one selected.
    expect(screen.getByLabelText("Select revision 3 for comparison")).not.toBeChecked();
    fireEvent.click(compare);
    expect(onCompare).toHaveBeenCalledWith(1, 2);
  });

  it("offers no comparison for a single revision", () => {
    render(<AssertionRevisionHistory revisions={[revisions[0]]} onCompare={vi.fn()} />);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /compare/i })).not.toBeInTheDocument();
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
