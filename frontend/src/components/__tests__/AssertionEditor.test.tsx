import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AssertionEditor } from "../AssertionEditor";
import { api } from "../../api/client";
import type { AssertionDetail } from "../../api/types";
vi.mock("../../api/client", () => ({ api: { updateAssertion: vi.fn(), submitAssertion: vi.fn(), withdrawAssertion: vi.fn() } }));
const detail = { id: "a", proposition: "Sanitized", proposition_raw: "Original <term>", status: "proposed", current_revision_number: 3 } as AssertionDetail;
beforeEach(() => vi.resetAllMocks());
describe("AssertionEditor", () => {
  it("preserves authored text and sends the expected revision number", async () => {
    vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
    const onSaved = vi.fn();
    render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={onSaved} />);
    fireEvent.click(screen.getByText("Edit assertion"));
    expect(screen.getByLabelText("Proposition")).toHaveValue("Original <term>");
    fireEvent.change(screen.getByLabelText("Proposition"), { target: { value: "Revised claim" } });
    fireEvent.change(screen.getByLabelText("Reason for revision"), { target: { value: "Narrow the scope" } });
    fireEvent.click(screen.getByText("Save revision"));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(api.updateAssertion).toHaveBeenCalledWith("a", { proposition: "Revised claim", revision_reason: "Narrow the scope", expected_revision_number: 3 });
  });
  it("keeps unsaved text after a stale revision conflict", async () => {
    vi.mocked(api.updateAssertion).mockRejectedValue(new Error("assertion has been modified since expected_revision_number"));
    render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={vi.fn()} />);
    fireEvent.click(screen.getByText("Edit assertion"));
    fireEvent.change(screen.getByLabelText("Proposition"), { target: { value: "Keep my work" } });
    fireEvent.click(screen.getByText("Save revision"));
    expect(await screen.findByRole("alert")).toHaveTextContent("modified");
    expect(screen.getByLabelText("Proposition")).toHaveValue("Keep my work");
  });
  it("hides editing for another contributor and reviewed assertions of the author", () => {
    const { rerender } = render(<AssertionEditor detail={detail} canReview={false} isAuthor={false} onSaved={vi.fn()} />);
    expect(screen.queryByText("Edit assertion")).not.toBeInTheDocument();
    rerender(<AssertionEditor detail={{ ...detail, status: "accepted" }} canReview={false} isAuthor onSaved={vi.fn()} />);
    expect(screen.queryByText("Edit assertion")).not.toBeInTheDocument();
  });
  it("allows an author to resubmit a requested revision", async () => {
    vi.mocked(api.submitAssertion).mockResolvedValue({} as never);
    render(<AssertionEditor detail={{ ...detail, status: "revision_requested" }} canReview={false} isAuthor onSaved={vi.fn()} />);
    fireEvent.click(screen.getByText("Submit for review"));
    await waitFor(() => expect(api.submitAssertion).toHaveBeenCalledWith("a"));
    expect(await screen.findByRole("status")).toHaveTextContent("Submitted");
  });
});
