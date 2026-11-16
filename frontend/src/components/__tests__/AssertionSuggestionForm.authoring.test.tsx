// AssertionSuggestionForm — assertion-type picker and proposed new types
// (ui:21), the further-evidence note, the profile default jurisdiction
// (ui:20) and the similar-assertion warning (ui:5), at component level.

import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AssertionSuggestionForm } from "../AssertionSuggestionForm";

const prefill = {
  method: "graph_entities" as const,
  repositoryId: "r1",
  matterId: "m1",
  subjectEntityId: "e1",
  subjectEntityLabel: "Master Services Agreement",
};

describe("AssertionSuggestionForm authoring", () => {
  it("shows the subject's name instead of its id", () => {
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={vi.fn()} />);
    expect(screen.getByText("Master Services Agreement")).toHaveAttribute("title", "e1");
    expect(screen.queryByText("e1")).not.toBeInTheDocument();
  });

  it("submits a recognized type without the proposed-new flag", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={onSubmit} />);
    await user.selectOptions(screen.getByLabelText("Assertion type"), "SURVIVES_TERMINATION");
    expect(screen.getByRole("option", { name: "Survives termination (SURVIVES_TERMINATION)" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Proposition"), "Clause 8 survives termination.");
    await user.click(screen.getByRole("button", { name: /save as draft/i }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ assertionType: "SURVIVES_TERMINATION", assertionTypeIsProposedNew: false }),
    );
  });

  it("names a proposed new type, normalized, and flags it", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={onSubmit} />);
    await user.selectOptions(screen.getByLabelText("Assertion type"), "Propose a new type…");
    const name = screen.getByLabelText("New type name");
    expect(name).toHaveAttribute("maxlength", "100");
    await user.type(name, "  Cancelled-by ");
    expect(screen.getByText("Will be saved as CANCELLED_BY, marked as a proposed new type.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Proposition"), "Clause 9 is cancelled by clause 12.");
    await user.click(screen.getByRole("button", { name: /preview/i }));
    expect(within(screen.getByRole("region", { name: "Preview" })).getByText("Type: CANCELLED_BY (proposed new type)")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /save as draft/i }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ assertionType: "CANCELLED_BY", assertionTypeIsProposedNew: true }),
    );
  });

  it("does not flag a new-type name that is already in the vocabulary", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={onSubmit} />);
    await user.selectOptions(screen.getByLabelText("Assertion type"), "Propose a new type…");
    await user.type(screen.getByLabelText("New type name"), "applies to");
    expect(screen.getByText("APPLIES_TO is already a recognized type; it will be saved as APPLIES_TO.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Proposition"), "Clause 9 applies to subtenants.");
    await user.click(screen.getByRole("button", { name: /save as draft/i }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ assertionType: "APPLIES_TO", assertionTypeIsProposedNew: false }),
    );
  });

  it("explains the further-evidence note and previews it", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={onSubmit} />);
    expect(screen.getByLabelText("Further evidence needed")).toHaveAccessibleDescription(
      /Adds a note to the explanation, which is saved as the first comment/,
    );
    await user.click(screen.getByLabelText("Further evidence needed"));
    await user.click(screen.getByRole("button", { name: /preview/i }));
    expect(within(screen.getByRole("region", { name: "Preview" })).getByText(/^Further evidence needed: the author marked/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Proposition"), "Clause 9 needs support.");
    await user.click(screen.getByRole("button", { name: /save as draft/i }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ needsFurtherEvidence: true }));
  });

  it("starts from a valid default jurisdiction and says where it came from", () => {
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={vi.fn()} defaultJurisdiction="US-DE" />);
    const field = screen.getByLabelText("Jurisdiction");
    expect(field).toHaveValue("US-DE");
    expect(field).toHaveAccessibleDescription(/Pre-selected from the default in your profile/);
    fireEvent.change(field, { target: { value: "IL" } });
    expect(screen.queryByText(/Pre-selected from the default in your profile/)).not.toBeInTheDocument();
  });

  it("ignores a default jurisdiction outside the vocabulary", () => {
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={vi.fn()} defaultJurisdiction="EU" />);
    expect(screen.getByLabelText("Jurisdiction")).toHaveValue("");
  });

  it("quotes only matches whose text is known and counts the rest", () => {
    render(
      <AssertionSuggestionForm
        prefill={prefill}
        onSubmit={vi.fn()}
        similarAssertions={[
          { id: "s-1", proposition: "Clause 8 survives termination." },
          { id: "s-2", proposition: "" },
        ]}
        similarAssertionsTotal={5}
      />,
    );
    const warning = screen.getByRole("alert");
    expect(within(warning).getByRole("link", { name: "“Clause 8 survives termination.”" })).toHaveAttribute(
      "href",
      "#/assertions/s-1",
    );
    expect(warning).toHaveTextContent("…and 4 more.");
    expect(warning).not.toHaveTextContent('""');
    expect(warning).not.toHaveTextContent("s-2");
  });

  it("counts matches without quoting when no text is known", () => {
    render(
      <AssertionSuggestionForm prefill={prefill} onSubmit={vi.fn()} similarAssertions={[{ id: "s-2", proposition: "" }]} />,
    );
    const warning = screen.getByRole("alert");
    expect(warning).toHaveTextContent("1 existing assertion matched.");
    expect(warning).not.toHaveTextContent('""');
    expect(within(warning).queryByRole("link")).not.toBeInTheDocument();
  });
});
