// Assertion discussion/comments (spec §9): threads, reviewer badges, and —
// for members who may comment — posting, replying, and editing or deleting
// their own comments (findings ui:15, pipeline:8). Deleting now asks for
// confirmation first; it used to delete on the first click.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionComments } from "../AssertionComments";
import type { AssertionCommentItem } from "../AssertionComments";

const comments: AssertionCommentItem[] = [
  { id: "c1", userId: "u1", authorName: "Contributor A", commentText: "Worth a look.", isReviewer: false, createdAt: "2026-07-20T10:00:00Z" },
  { id: "c2", userId: "u2", authorName: "Reviewer B", commentText: "Agreed, needs more evidence.", isReviewer: true, createdAt: "2026-07-20T11:00:00Z" },
];

describe("AssertionComments", () => {
  it("lists comments with author and text", () => {
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText("Worth a look.")).toBeInTheDocument();
    expect(screen.getByText("Agreed, needs more evidence.")).toBeInTheDocument();
  });

  it("visually distinguishes reviewer comments", () => {
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />);
    const reviewerComment = screen.getByTestId("comment-c2");
    expect(reviewerComment).toHaveAttribute("data-reviewer", "true");
    expect(within(reviewerComment).getByText("Reviewer")).toBeInTheDocument();
    expect(within(screen.getByTestId("comment-c1")).queryByText("Reviewer")).not.toBeInTheDocument();
  });

  it("lets a user add a new comment", () => {
    const onAdd = vi.fn();
    render(<AssertionComments comments={[]} currentUserId="u1" onAdd={onAdd} onEdit={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/add a comment/i), { target: { value: "New remark." } });
    fireEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(onAdd).toHaveBeenCalledWith("New remark.");
  });

  it("keeps the draft and shows the reason when posting fails", async () => {
    const onAdd = vi.fn().mockRejectedValue(new Error("your role in this matter does not permit commenting"));
    render(<AssertionComments comments={[]} currentUserId="u1" onAdd={onAdd} onEdit={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Add a comment"), { target: { value: "Draft text" } });
    fireEvent.click(screen.getByRole("button", { name: "Post comment" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("does not permit commenting");
    expect(screen.getByLabelText("Add a comment")).toHaveValue("Draft text");
  });

  it("lets a user edit their own comment but not others", () => {
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByTestId("comment-c1")).toContainElement(screen.getByRole("button", { name: /edit/i }));
    expect(screen.queryByTestId("comment-c2-edit")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("comment-c2")).queryByRole("button", { name: /edit|delete/i })).not.toBeInTheDocument();
  });

  it("edits from the exact authored text and saves only a change", () => {
    const onEdit = vi.fn();
    render(
      <AssertionComments
        comments={[{ ...comments[0], commentText: "See  for details.", commentTextRaw: "See <Annex 2> for details." }]}
        currentUserId="u1"
        onAdd={vi.fn()}
        onEdit={onEdit}
        onDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    const box = screen.getByLabelText("Edit comment");
    expect(box).toHaveValue("See <Annex 2> for details.");
    expect(screen.getByRole("button", { name: "Save comment" })).toBeDisabled();

    fireEvent.change(box, { target: { value: "See <Annex 3> for details." } });
    fireEvent.click(screen.getByRole("button", { name: "Save comment" }));
    expect(onEdit).toHaveBeenCalledWith("c1", "See <Annex 3> for details.");
  });

  it("lets a user delete their own comment after confirming", () => {
    const onDelete = vi.fn();
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    expect(onDelete).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Delete comment" }));
    expect(onDelete).toHaveBeenCalledWith("c1");
  });

  it("can keep a comment it was about to delete", () => {
    const onDelete = vi.fn();
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    fireEvent.click(screen.getByRole("button", { name: "Keep comment" }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("replies to a comment when replies are offered", () => {
    const onReply = vi.fn();
    render(
      <AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} onReply={onReply} />,
    );
    fireEvent.click(within(screen.getByTestId("comment-c2")).getByRole("button", { name: "Reply" }));
    fireEvent.change(screen.getByLabelText("Reply to Reviewer B"), { target: { value: "  Will do.  " } });
    fireEvent.click(screen.getByRole("button", { name: "Post reply" }));
    expect(onReply).toHaveBeenCalledWith("c2", "Will do.");
  });

  it("offers no Reply without a reply handler", () => {
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Reply" })).not.toBeInTheDocument();
  });

  it("keeps an edit open with the reason when saving fails", async () => {
    const onEdit = vi.fn().mockRejectedValue(new Error("can only edit your own comment"));
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={onEdit} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByLabelText("Edit comment"), { target: { value: "Changed." } });
    fireEvent.click(screen.getByRole("button", { name: "Save comment" }));

    expect(await within(screen.getByTestId("comment-c1")).findByRole("alert")).toHaveTextContent(
      "can only edit your own comment",
    );
    expect(screen.getByLabelText("Edit comment")).toHaveValue("Changed.");
  });

  it("shows nesting: a reply sits under its parent, a removed parent keeps its place", () => {
    render(
      <AssertionComments
        comments={[
          { id: "p", userId: "u2", authorName: "Reviewer B", commentText: "", deletedAt: "2026-07-21T09:00:00Z" },
          { id: "x", userId: "u3", authorName: "Other C", commentText: "Separate point." },
          { id: "r", userId: "u1", authorName: "Contributor A", commentText: "Answering the removed one.", parentCommentId: "p" },
        ]}
        currentUserId="u1"
        onAdd={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onReply={vi.fn()}
      />,
    );
    const parent = screen.getByTestId("comment-p");
    expect(within(parent).getByText("[comment removed]")).toBeInTheDocument();
    expect(parent).toContainElement(screen.getByTestId("comment-r"));
    expect(screen.getAllByTestId(/^comment-/).map((node) => node.dataset.testid)).toEqual([
      "comment-p",
      "comment-r",
      "comment-x",
    ]);
  });

  it("never nests a comment under a parent listed after it", () => {
    render(
      <AssertionComments
        comments={[
          { id: "a", userId: "u2", authorName: "Reviewer B", commentText: "Points at b.", parentCommentId: "b" },
          { id: "b", userId: "u3", authorName: "Other C", commentText: "Points at a.", parentCommentId: "a" },
        ]}
        currentUserId="u1"
        onAdd={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    // A malformed cycle is still shown, once each.
    expect(screen.getByText("Points at b.")).toBeInTheDocument();
    expect(screen.getByText("Points at a.")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^comment-/)).toHaveLength(2);
  });

  it("is read-only for a member who may not comment, even on their own comment", () => {
    render(
      <AssertionComments comments={comments} currentUserId="u1" canComment={false} onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} onReply={vi.fn()} />,
    );
    expect(screen.getByText("Worth a look.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Add a comment")).not.toBeInTheDocument();
  });

  it("marks an edited comment and shows the time when a formatter is given", () => {
    render(
      <AssertionComments
        comments={[{ ...comments[0], updatedAt: "2026-07-20T12:00:00Z" }]}
        currentUserId="u9"
        onAdd={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        formatTime={(iso) => `at ${iso.slice(11, 16)}`}
      />,
    );
    expect(screen.getByText("(edited)")).toBeInTheDocument();
    expect(screen.getByText("at 10:00")).toBeInTheDocument();
  });

  it("does not call a just-created comment edited", () => {
    render(
      <AssertionComments
        comments={[{ ...comments[0], updatedAt: comments[0].createdAt }]}
        currentUserId="u9"
        onAdd={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.queryByText("(edited)")).not.toBeInTheDocument();
  });
});
