// UI3 — assertion discussion/comments (spec §9). Import-failure RED
// (documented exception) until Developer track UI3 creates
// `../AssertionComments`.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionComments } from "../AssertionComments";

const comments = [
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
  });

  it("lets a user add a new comment", () => {
    const onAdd = vi.fn();
    render(<AssertionComments comments={[]} currentUserId="u1" onAdd={onAdd} onEdit={vi.fn()} onDelete={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/add a comment/i), { target: { value: "New remark." } });
    fireEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(onAdd).toHaveBeenCalledWith("New remark.");
  });

  it("lets a user edit their own comment but not others", () => {
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByTestId("comment-c1")).toContainElement(screen.getByRole("button", { name: /edit/i }));
    expect(screen.queryByTestId("comment-c2-edit")).not.toBeInTheDocument();
  });

  it("lets a user delete their own comment", () => {
    const onDelete = vi.fn();
    render(<AssertionComments comments={comments} currentUserId="u1" onAdd={vi.fn()} onEdit={vi.fn()} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: /delete/i }));
    expect(onDelete).toHaveBeenCalledWith("c1");
  });
});
