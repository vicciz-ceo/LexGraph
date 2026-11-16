// UI3 — side-by-side revision comparison (spec §3: "The user must be able
// to compare revisions"). Import-failure RED (documented exception) until
// Developer track UI3 creates `../AssertionComparisonView`.

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssertionComparisonView } from "../AssertionComparisonView";
import type { AssertionComparisonField } from "../AssertionComparisonView";

const left = { revisionNumber: 1, proposition: "Original proposition text.", editedBy: "Contributor A" };
const right = { revisionNumber: 2, proposition: "A materially edited proposition text.", editedBy: "Contributor A" };

describe("AssertionComparisonView", () => {
  it("renders both revisions side by side", () => {
    render(<AssertionComparisonView left={left} right={right} />);
    expect(screen.getByText("Original proposition text.")).toBeInTheDocument();
    expect(screen.getByText("A materially edited proposition text.")).toBeInTheDocument();
  });

  it("labels each side with its revision number", () => {
    render(<AssertionComparisonView left={left} right={right} />);
    expect(screen.getByText(/revision 1/i)).toBeInTheDocument();
    expect(screen.getByText(/revision 2/i)).toBeInTheDocument();
  });

  it("indicates which revision each rating applied to when ratings are passed in", () => {
    render(
      <AssertionComparisonView
        left={left}
        right={right}
        leftRatingSummary={{ count: 5, average: 3.0, median: 3, distribution: {} }}
        rightRatingSummary={{ count: 0, average: null, median: null, distribution: {} }}
      />
    );
    expect(screen.getByText(/not yet been rated/i)).toBeInTheDocument();
  });

  // Track A, item A7 (issue #2 / gate G1): the comparison view is a
  // diff/compare-classified read path, so each side must render the RAW
  // authored proposition -- byte-exact -- as a plain text node. RED against
  // the current component, which only knows about the (possibly lossy)
  // sanitized `proposition` field.
  it("renders the raw authored proposition byte-exact on each side", () => {
    const rawLeft = "Signatory: <Title> of the Company.";
    const rawRight = "Pre <img plaintail <b>Y</b> Z";
    render(
      <AssertionComparisonView
        left={{ revisionNumber: 1, proposition: "Signatory:  of the Company.", propositionRaw: rawLeft, editedBy: "Contributor A" }}
        right={{ revisionNumber: 2, proposition: "Pre Y Z", propositionRaw: rawRight, editedBy: "Contributor A" }}
      />
    );
    expect(screen.getByText(rawLeft)).toBeInTheDocument();
    expect(screen.getByText(rawRight)).toBeInTheDocument();
  });
});

// Findings ui:15 / pipeline:8: mounted under the detail page's Activity
// timeline. Spec §3 revisions also record type, subject, object,
// jurisdiction and effective dates, so a revision that changed only one of
// those must not look identical to the one before it.
describe("AssertionComparisonView field comparison", () => {
  function fields(overrides: Partial<Record<string, Partial<AssertionComparisonField>>> = {}): AssertionComparisonField[] {
    const base: AssertionComparisonField[] = [
      { key: "assertion_type", label: "Assertion type", value: "Applies to" },
      { key: "subject", label: "Subject", value: "Document 61c95f7e", identity: "Document:doc-1" },
      { key: "jurisdiction", label: "Jurisdiction", value: "—" },
    ];
    return base.map((field) => ({ ...field, ...(overrides[field.key] ?? {}) }));
  }

  it("marks the fields whose value changed and names them", () => {
    render(
      <AssertionComparisonView
        left={{ ...left, proposition: right.proposition, fields: fields() }}
        right={{ ...right, fields: fields({ jurisdiction: { value: "IL" } }) }}
      />,
    );
    expect(screen.getByText("Changed: jurisdiction.")).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /Jurisdiction/ });
    expect(within(row).getByText("Changed")).toBeInTheDocument();
    expect(within(row).getByText("IL")).toBeInTheDocument();
    expect(within(screen.getByRole("row", { name: /Assertion type/ })).queryByText("Changed")).not.toBeInTheDocument();
  });

  it("compares identities, not display text", () => {
    render(
      <AssertionComparisonView
        left={{ ...left, proposition: right.proposition, fields: fields() }}
        right={{ ...right, fields: fields({ subject: { identity: "Document:doc-2" } }) }}
      />,
    );
    // Same display text, different entity: still a change.
    expect(screen.getByText("Changed: subject.")).toBeInTheDocument();
  });

  it("says when nothing differs", () => {
    render(
      <AssertionComparisonView
        left={{ ...left, proposition: right.proposition, fields: fields() }}
        right={{ ...right, fields: fields() }}
      />,
    );
    expect(screen.getByText("No differences: the two revisions have the same text and fields.")).toBeInTheDocument();
    expect(screen.queryByText("Changed")).not.toBeInTheDocument();
  });

  it("shows each revision's reason and says when its ratings could not be loaded", () => {
    render(
      <AssertionComparisonView
        left={{ ...left, revisionReason: null }}
        right={{ ...right, revisionReason: "Narrowed the scope" }}
        leftRatingSummary={null}
        rightRatingSummary={{ count: 1, average: 4, median: 4, distribution: {} }}
      />,
    );
    expect(screen.getByText("Narrowed the scope")).toBeInTheDocument();
    expect(screen.getByText("Ratings could not be loaded.")).toBeInTheDocument();
    expect(screen.getByText("4.0 average from 1 rating for this revision.")).toBeInTheDocument();
  });
});
