// RED tests for the jurisdiction PICKER (sprint 2026-08-02-us-state-law,
// director decision #4, gate G7: "Jurisdiction picker ... across every
// affected page"). New file (not an edit to the existing
// `AssertionSuggestionForm.test.tsx`, which has no jurisdiction coverage
// today -- ruling: additive test file, zero risk of colliding with an
// existing passing test).
//
// Today (recon dossier §3): `AssertionSuggestionForm.tsx:278-284` renders
// jurisdiction as a plain `<input type="text">` -- a free-text field with
// no controlled vocabulary at all. These tests are RED because there is no
// `<select>`/combobox for jurisdiction yet.

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AssertionSuggestionForm } from "../AssertionSuggestionForm";

const prefill = {
  method: "selected_text" as const,
  repositoryId: "r1",
  matterId: "m1",
  documentVersionId: "d1",
  provisionId: "p1",
  sourceSpanId: "s1",
  quotation: "except where prohibited by law",
};

describe("AssertionSuggestionForm jurisdiction picker", () => {
  it("renders jurisdiction as a controlled-vocabulary select, not a free-text input", () => {
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={vi.fn()} />);
    const field = screen.getByLabelText(/jurisdiction/i);
    expect(field.tagName).toBe("SELECT");
  });

  it("offers IL and every US state code as options, sourced from the shared constant", () => {
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={vi.fn()} />);
    const field = screen.getByLabelText(/jurisdiction/i) as HTMLSelectElement;
    const values = Array.from(field.options).map((o) => o.value);
    expect(values).toContain("IL");
    expect(values).toContain("US-DE");
    expect(values).toContain("US-FED");
    expect(values.length).toBeGreaterThanOrEqual(54);
  });

  it("lets the user pick a jurisdiction and submits it in the payload", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<AssertionSuggestionForm prefill={prefill} onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/proposition/i), "A qualifying proposition.");
    await user.selectOptions(screen.getByLabelText(/jurisdiction/i), "US-DE");
    await user.click(screen.getByRole("button", { name: /save as draft/i }));

    expect(onSubmit).toHaveBeenCalled();
    const submitted = onSubmit.mock.calls[0][0];
    expect(submitted.jurisdiction).toBe("US-DE");
  });
});
