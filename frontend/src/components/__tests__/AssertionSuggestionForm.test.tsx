// UI2 — suggest-assertion form, Method A (selected text) and Method B
// (graph entities) per spec §6, gate G11. Import-failure RED (documented
// exception) until Developer track UI2 creates
// `../AssertionSuggestionForm`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionSuggestionForm } from "../AssertionSuggestionForm";

const fromSelectedTextPrefill = {
  method: "selected_text" as const,
  repositoryId: "r1",
  matterId: "m1",
  documentVersionId: "d1",
  provisionId: "p1",
  sourceSpanId: "s1",
  quotation: "except where prohibited by law",
};

describe("AssertionSuggestionForm", () => {
  it("pre-populates repository/matter/document/provision/quotation from selected text", () => {
    render(<AssertionSuggestionForm prefill={fromSelectedTextPrefill} onSubmit={vi.fn()} />);
    expect(screen.getByText(/except where prohibited by law/)).toBeInTheDocument();
  });

  it("requires the user to enter a proposition before submit is enabled", () => {
    render(<AssertionSuggestionForm prefill={fromSelectedTextPrefill} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /submit for review/i })).toBeDisabled();
  });

  it("supports save as draft, submit for review, cancel, and preview actions", () => {
    render(<AssertionSuggestionForm prefill={fromSelectedTextPrefill} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /save as draft/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit for review/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /preview/i })).toBeInTheDocument();
  });

  it("supports adding multiple evidence spans with supporting/contradicting roles", () => {
    render(<AssertionSuggestionForm prefill={fromSelectedTextPrefill} onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add.*evidence/i }));
    expect(screen.getAllByLabelText(/evidence role/i).length).toBeGreaterThanOrEqual(1);
  });

  it("allows creating a standalone proposition without an object entity", () => {
    render(
      <AssertionSuggestionForm
        prefill={{ method: "graph_entities", repositoryId: "r1", matterId: "m1", subjectEntityId: "e1" }}
        onSubmit={vi.fn()}
      />
    );
    expect(screen.getByLabelText(/standalone proposition/i)).toBeInTheDocument();
  });

  it("warns (without blocking) when the proposition closely resembles an existing assertion", async () => {
    render(
      <AssertionSuggestionForm
        prefill={fromSelectedTextPrefill}
        onSubmit={vi.fn()}
        similarAssertions={[{ id: "existing-1", proposition: "A very similar proposition." }]}
      />
    );
    expect(await screen.findByText(/similar assertion/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/proposition/i), {
      target: { value: "A proposition that resembles existing assertions." },
    });
    expect(screen.getByRole("button", { name: /submit for review/i })).not.toBeDisabled();
  });

  it("submit stays disabled when proposition is empty even with similar assertions present", async () => {
    render(
      <AssertionSuggestionForm
        prefill={fromSelectedTextPrefill}
        onSubmit={vi.fn()}
        similarAssertions={[{ id: "existing-1", proposition: "A very similar proposition." }]}
      />
    );
    expect(await screen.findByText(/similar assertion/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit for review/i })).toBeDisabled();
  });

  it("submits the assertion type, proposition, evidence, and explanation on submit", () => {
    const onSubmit = vi.fn();
    render(<AssertionSuggestionForm prefill={fromSelectedTextPrefill} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/proposition/i), {
      target: { value: "Clause 8.4 creates a limited exception to Clause 8.2." },
    });
    fireEvent.click(screen.getByRole("button", { name: /^submit for review$/i }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        proposition: "Clause 8.4 creates a limited exception to Clause 8.2.",
        save_as: "proposed",
      })
    );
  });
});
