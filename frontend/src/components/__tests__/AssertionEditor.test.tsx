import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AssertionEditor } from "../AssertionEditor";
import { api } from "../../api/client";
import type { AssertionDetail } from "../../api/types";
vi.mock("../../api/client", () => ({ api: { updateAssertion: vi.fn(), submitAssertion: vi.fn(), withdrawAssertion: vi.fn() } }));

/** Shape of the client's ApiError (status + detail message). */
class HttpError extends Error {
  constructor(public status: number, detail: string) { super(detail); this.name = "ApiError"; }
}
const STALE = "assertion has been modified since expected_revision_number";

const detail = { id: "a", proposition: "Sanitized", proposition_raw: "Original <term>", status: "proposed", current_revision_number: 3 } as AssertionDetail;
const newer = { ...detail, proposition: "Reviewer text", proposition_raw: "Reviewer text", current_revision_number: 4 } as AssertionDetail;
beforeEach(() => vi.resetAllMocks());

function openEditor() {
  fireEvent.click(screen.getByText("Edit assertion"));
}
function typeText(value: string) {
  fireEvent.change(screen.getByLabelText("Proposition"), { target: { value } });
}

describe("AssertionEditor", () => {
  it("preserves authored text and sends the expected revision number", async () => {
    vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
    const onSaved = vi.fn();
    render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={onSaved} />);
    openEditor();
    expect(screen.getByLabelText("Proposition")).toHaveValue("Original <term>");
    typeText("Revised claim");
    fireEvent.change(screen.getByLabelText("Reason for revision"), { target: { value: "Narrow the scope" } });
    fireEvent.click(screen.getByText("Save revision"));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(api.updateAssertion).toHaveBeenCalledWith("a", { proposition: "Revised claim", revision_reason: "Narrow the scope", expected_revision_number: 3 });
  });

  describe("unchanged text (ui:11)", () => {
    it("keeps Save disabled until the proposition differs from the current revision", () => {
      render(<AssertionEditor detail={{ ...detail, status: "accepted" }} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      const save = screen.getByText("Save revision");
      expect(save).toBeDisabled();
      expect(screen.getByText("Change the proposition or another field to save a new revision.")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Reason for revision"), { target: { value: "Only a reason" } });
      expect(save).toBeDisabled();
      typeText("Original <term> (edited)");
      expect(save).toBeEnabled();
      typeText("Original <term>");
      expect(save).toBeDisabled();
      fireEvent.click(save);
      expect(api.updateAssertion).not.toHaveBeenCalled();
    });

    it("compares with the sanitized proposition when no raw text is stored", () => {
      render(<AssertionEditor detail={{ ...detail, proposition_raw: null }} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Sanitized");
      expect(screen.getByText("Save revision")).toBeDisabled();
      typeText("Sanitized, revised");
      expect(screen.getByText("Save revision")).toBeEnabled();
    });

    it("treats a line-ending-only difference as unchanged", () => {
      render(<AssertionEditor detail={{ ...detail, proposition_raw: "Line one\r\nLine two" }} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      typeText("Line one\nLine two");
      expect(screen.getByText("Save revision")).toBeDisabled();
    });
  });

  describe("reason for revision (review:9)", () => {
    it("starts empty for every edit and is cleared after a save", async () => {
      vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
      const { rerender } = render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      typeText("First edit");
      fireEvent.change(screen.getByLabelText("Reason for revision"), { target: { value: "FIRST EDIT REASON" } });
      fireEvent.click(screen.getByText("Save revision"));
      await screen.findByRole("status");
      rerender(<AssertionEditor detail={{ ...detail, proposition_raw: "First edit", current_revision_number: 4 }} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      expect(screen.getByLabelText("Reason for revision")).toHaveValue("");
      expect(screen.getByLabelText("Proposition")).toHaveValue("First edit");
      expect(screen.getByText("Save revision")).toBeDisabled();
    });

    it("is cleared when an edit is cancelled and reopened", () => {
      render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      fireEvent.change(screen.getByLabelText("Reason for revision"), { target: { value: "Abandoned" } });
      fireEvent.click(screen.getByText("Cancel edit"));
      openEditor();
      expect(screen.getByLabelText("Reason for revision")).toHaveValue("");
    });
  });

  describe("stale-revision conflict (ui:13)", () => {
    it("reloads the assertion, keeps the draft and explains the conflict readably", async () => {
      vi.mocked(api.updateAssertion).mockRejectedValue(new HttpError(409, STALE));
      const onSaved = vi.fn();
      render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={onSaved} />);
      openEditor();
      typeText("Keep my work");
      fireEvent.click(screen.getByText("Save revision"));
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent("changed after you started editing");
      expect(alert).not.toHaveTextContent("expected_revision_number");
      expect(onSaved).toHaveBeenCalledOnce();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Keep my work");
    });

    it("shows the newer revision and saves the draft on top of it", async () => {
      vi.mocked(api.updateAssertion).mockRejectedValueOnce(new HttpError(409, STALE)).mockResolvedValueOnce({} as never);
      const onSaved = vi.fn();
      const { rerender } = render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={onSaved} />);
      openEditor();
      typeText("Keep my work");
      fireEvent.change(screen.getByLabelText("Reason for revision"), { target: { value: "My reason" } });
      fireEvent.click(screen.getByText("Save revision"));
      await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
      // The page's refresh delivers the newer revision to the mounted editor.
      rerender(<AssertionEditor detail={newer} canReview isAuthor={false} onSaved={onSaved} />);
      const panel = screen.getByRole("alert");
      expect(panel).toHaveTextContent("A newer revision (v4) was saved while you were editing");
      expect(within(panel).getByText("Reviewer text")).toBeInTheDocument();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Keep my work");
      expect(screen.getByLabelText("Reason for revision")).toHaveValue("My reason");
      expect(screen.getByText("Save revision")).toBeDisabled();
      fireEvent.click(screen.getByText("Save my text as the next revision"));
      await waitFor(() => expect(api.updateAssertion).toHaveBeenCalledTimes(2));
      expect(api.updateAssertion).toHaveBeenLastCalledWith("a", { proposition: "Keep my work", revision_reason: "My reason", expected_revision_number: 4 });
      expect(await screen.findByRole("status")).toHaveTextContent("Revision saved");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(onSaved).toHaveBeenCalledTimes(2);
    });

    it("can discard the draft and start from the latest revision", async () => {
      vi.mocked(api.updateAssertion).mockRejectedValue(new HttpError(409, STALE));
      const { rerender } = render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      typeText("Keep my work");
      fireEvent.click(screen.getByText("Save revision"));
      await screen.findByRole("alert");
      rerender(<AssertionEditor detail={newer} canReview isAuthor={false} onSaved={vi.fn()} />);
      fireEvent.click(screen.getByText("Discard my text and start from the latest"));
      expect(screen.getByLabelText("Proposition")).toHaveValue("Reviewer text");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByText("Save revision")).toBeDisabled();
      typeText("Reviewer text, refined");
      expect(screen.getByText("Save revision")).toBeEnabled();
    });

    it("flags a newer revision loaded while editing, before any save", () => {
      const { rerender } = render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      typeText("Draft in progress");
      rerender(<AssertionEditor detail={newer} canReview isAuthor={false} onSaved={vi.fn()} />);
      expect(screen.getByRole("alert")).toHaveTextContent("A newer revision (v4)");
      expect(screen.getByText("Save revision")).toBeDisabled();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Draft in progress");
    });

    it("does not offer to save a draft identical to the newer revision", async () => {
      const { rerender } = render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={vi.fn()} />);
      openEditor();
      typeText("Reviewer text");
      rerender(<AssertionEditor detail={newer} canReview isAuthor={false} onSaved={vi.fn()} />);
      expect(screen.getByText("Save my text as the next revision")).toBeDisabled();
      expect(screen.getByRole("alert")).toHaveTextContent("nothing to save");
    });

    it("keeps the draft visible when the reloaded assertion can no longer be edited", () => {
      const { rerender } = render(<AssertionEditor detail={detail} canReview={false} isAuthor onSaved={vi.fn()} />);
      openEditor();
      typeText("Author draft");
      rerender(<AssertionEditor detail={{ ...newer, status: "accepted" }} canReview={false} isAuthor onSaved={vi.fn()} />);
      expect(screen.getByLabelText("Proposition")).toHaveValue("Author draft");
      expect(screen.getAllByRole("alert")[0]).toHaveTextContent("You can no longer edit this assertion");
      expect(screen.getByText("Save revision")).toBeDisabled();
      fireEvent.click(screen.getByText("Cancel edit"));
      expect(screen.queryByText("Edit assertion")).not.toBeInTheDocument();
    });
  });

  describe("other failures", () => {
    it("keeps the text and does not reload on a validation error", async () => {
      vi.mocked(api.updateAssertion).mockRejectedValue(new HttpError(422, "proposition exceeds the maximum length"));
      const onSaved = vi.fn();
      render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={onSaved} />);
      openEditor();
      typeText("Keep my work");
      fireEvent.click(screen.getByText("Save revision"));
      expect(await screen.findByRole("alert")).toHaveTextContent("proposition exceeds the maximum length");
      expect(onSaved).not.toHaveBeenCalled();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Keep my work");
    });

    it("links to the assertion that already holds the text on a duplicate conflict", async () => {
      vi.mocked(api.updateAssertion).mockRejectedValue(new HttpError(409, "duplicate: an identical proposition already exists in this matter (assertion other-1)"));
      const onSaved = vi.fn();
      render(<AssertionEditor detail={detail} canReview isAuthor={false} onSaved={onSaved} />);
      openEditor();
      typeText("Same as another assertion");
      fireEvent.click(screen.getByText("Save revision"));
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent("already states exactly this proposition");
      expect(within(alert).getByRole("link", { name: "Open the existing assertion" })).toHaveAttribute("href", "#/assertions/other-1");
      expect(onSaved).not.toHaveBeenCalled();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Same as another assertion");
    });

    it("explains a lost permission without reloading away the draft", async () => {
      vi.mocked(api.updateAssertion).mockRejectedValue(new HttpError(403, "Only the author of an unreviewed assertion or a reviewer may modify it"));
      const onSaved = vi.fn();
      render(<AssertionEditor detail={detail} canReview={false} isAuthor onSaved={onSaved} />);
      openEditor();
      typeText("Author draft");
      fireEvent.click(screen.getByText("Save revision"));
      expect(await screen.findByRole("alert")).toHaveTextContent("You can no longer edit this assertion");
      expect(onSaved).not.toHaveBeenCalled();
      expect(screen.getByLabelText("Proposition")).toHaveValue("Author draft");
    });

    it("reloads with a readable message when submitting an assertion that changed", async () => {
      vi.mocked(api.submitAssertion).mockRejectedValue(new HttpError(409, "cannot submit assertion in status 'withdrawn'"));
      const onSaved = vi.fn();
      render(<AssertionEditor detail={{ ...detail, status: "draft" }} canReview={false} isAuthor onSaved={onSaved} />);
      fireEvent.click(screen.getByText("Submit for review"));
      expect(await screen.findByRole("alert")).toHaveTextContent("changed after this page was loaded");
      expect(onSaved).toHaveBeenCalledOnce();
    });

    it("reloads when a submission is refused because the draft was withdrawn meanwhile", async () => {
      vi.mocked(api.submitAssertion).mockRejectedValue(new HttpError(403, "Only the author of an unreviewed assertion or a reviewer may modify it"));
      const onSaved = vi.fn();
      const { rerender } = render(<AssertionEditor detail={{ ...detail, status: "draft" }} canReview={false} isAuthor onSaved={onSaved} />);
      fireEvent.click(screen.getByText("Submit for review"));
      expect(await screen.findByRole("alert")).toHaveTextContent("The page now shows its current state");
      expect(onSaved).toHaveBeenCalledOnce();
      // The reloaded assertion is withdrawn: no actions, but the explanation stays.
      rerender(<AssertionEditor detail={{ ...detail, status: "withdrawn" }} canReview={false} isAuthor onSaved={onSaved} />);
      expect(screen.getByRole("alert")).toHaveTextContent("it may have been submitted, withdrawn or reviewed meanwhile");
      expect(screen.queryByText("Edit assertion")).not.toBeInTheDocument();
      expect(screen.queryByText("Submit for review")).not.toBeInTheDocument();
    });

    it("keeps the withdrawal confirmation after the page reloads the withdrawn assertion", async () => {
      vi.mocked(api.withdrawAssertion).mockResolvedValue({} as never);
      const { rerender } = render(<AssertionEditor detail={detail} canReview={false} isAuthor onSaved={vi.fn()} />);
      fireEvent.click(screen.getByText("Withdraw assertion"));
      expect(await screen.findByRole("status")).toHaveTextContent("Assertion withdrawn.");
      rerender(<AssertionEditor detail={{ ...detail, status: "withdrawn" }} canReview={false} isAuthor onSaved={vi.fn()} />);
      expect(screen.getByRole("status")).toHaveTextContent("Assertion withdrawn.");
      expect(screen.queryByText("Withdraw assertion")).not.toBeInTheDocument();
    });

    it("links to the live duplicate when a draft cannot be submitted", async () => {
      vi.mocked(api.submitAssertion).mockRejectedValue(new HttpError(409, "duplicate: an identical proposition already exists in this matter (assertion live-1)"));
      const onSaved = vi.fn();
      render(<AssertionEditor detail={{ ...detail, status: "draft" }} canReview={false} isAuthor onSaved={onSaved} />);
      fireEvent.click(screen.getByText("Submit for review"));
      const alert = await screen.findByRole("alert");
      expect(within(alert).getByRole("link", { name: "Open the existing assertion" })).toHaveAttribute("href", "#/assertions/live-1");
      expect(onSaved).not.toHaveBeenCalled();
    });
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

// XREQ-50 (ui:15): a revision records the type, jurisdiction and effective
// dates too (spec §3), and PATCH changes them; the editor offers them and
// sends only what the user changed.
describe("AssertionEditor fields besides the text", () => {
  const full = {
    ...detail,
    assertion_type: "INTERPRETS",
    jurisdiction: "IL",
    effective_from: "2026-01-01T00:00:00",
    effective_to: null,
  } as AssertionDetail;

  it("saves a jurisdiction change alone, with the text unchanged", async () => {
    vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
    render(<AssertionEditor detail={full} canReview isAuthor={false} onSaved={vi.fn()} />);
    openEditor();
    const save = screen.getByRole("button", { name: "Save revision" });
    expect(save).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Jurisdiction"), { target: { value: "US-CA" } });
    expect(save).toBeEnabled();
    fireEvent.click(save);

    await waitFor(() =>
      expect(api.updateAssertion).toHaveBeenCalledWith("a", {
        proposition: "Original <term>",
        jurisdiction: "US-CA",
        revision_reason: null,
        expected_revision_number: 3,
      }),
    );
  });

  it("clears a field with null and changes the type and dates", async () => {
    vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
    render(<AssertionEditor detail={full} canReview isAuthor={false} onSaved={vi.fn()} />);
    openEditor();
    expect(screen.getByLabelText("Effective from")).toHaveValue("2026-01-01");

    fireEvent.change(screen.getByLabelText("Assertion type"), { target: { value: "MODIFIES" } });
    fireEvent.change(screen.getByLabelText("Jurisdiction"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Effective to"), { target: { value: "2026-12-31" } });
    fireEvent.click(screen.getByRole("button", { name: "Save revision" }));

    await waitFor(() =>
      expect(api.updateAssertion).toHaveBeenCalledWith("a", {
        proposition: "Original <term>",
        assertion_type: "MODIFIES",
        jurisdiction: null,
        effective_to: "2026-12-31",
        revision_reason: null,
        expected_revision_number: 3,
      }),
    );
  });

  it("does not save an end date before the start date", () => {
    render(<AssertionEditor detail={full} canReview isAuthor={false} onSaved={vi.fn()} />);
    openEditor();

    fireEvent.change(screen.getByLabelText("Effective to"), { target: { value: "2025-06-30" } });

    expect(screen.getByRole("button", { name: "Save revision" })).toBeDisabled();
    expect(screen.getByText("The effective end date cannot be before the start date.")).toBeInTheDocument();
  });

  it("keeps a type outside the vocabulary selectable and unsent when left alone", async () => {
    vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
    render(
      <AssertionEditor detail={{ ...full, assertion_type: "CANCELLED_BY" }} canReview isAuthor={false} onSaved={vi.fn()} />,
    );
    openEditor();
    expect(screen.getByLabelText("Assertion type")).toHaveValue("CANCELLED_BY");

    typeText("Revised claim");
    fireEvent.click(screen.getByRole("button", { name: "Save revision" }));

    await waitFor(() => expect(api.updateAssertion).toHaveBeenCalled());
    expect(vi.mocked(api.updateAssertion).mock.calls[0][1]).not.toHaveProperty("assertion_type");
  });

  it("sends only the user's own changes over a newer revision", async () => {
    vi.mocked(api.updateAssertion).mockResolvedValue({} as never);
    const view = render(<AssertionEditor detail={full} canReview isAuthor={false} onSaved={vi.fn()} />);
    openEditor();
    fireEvent.change(screen.getByLabelText("Assertion type"), { target: { value: "MODIFIES" } });

    // Someone else saved revision 4 with another jurisdiction meanwhile.
    view.rerender(
      <AssertionEditor
        detail={{ ...full, jurisdiction: "US-NY", current_revision_number: 4 }}
        canReview
        isAuthor={false}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save my text as the next revision" }));

    await waitFor(() => expect(api.updateAssertion).toHaveBeenCalled());
    const body = vi.mocked(api.updateAssertion).mock.calls[0][1];
    expect(body).toMatchObject({ assertion_type: "MODIFIES", expected_revision_number: 4 });
    expect(body).not.toHaveProperty("jurisdiction");
  });
});
