// UI3 — assertion discussion thread (spec §9).
// Local types only for this component (sprint ruling R7 — no shared types module).

import { useState } from "react";

export interface AssertionCommentItem {
  id: string;
  userId: string;
  authorName: string;
  commentText: string;
  isReviewer?: boolean;
  parentCommentId?: string | null;
  createdAt?: string;
  deletedAt?: string | null;
}

export interface AssertionCommentsProps {
  comments: AssertionCommentItem[];
  currentUserId: string;
  onAdd: (commentText: string) => void;
  onEdit: (commentId: string, commentText: string) => void;
  onDelete: (commentId: string) => void;
}

export function AssertionComments({
  comments,
  currentUserId,
  onAdd,
  onEdit,
  onDelete,
}: AssertionCommentsProps) {
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  function handlePost() {
    if (!draft.trim()) return;
    onAdd(draft);
    setDraft("");
  }

  function startEdit(comment: AssertionCommentItem) {
    setEditingId(comment.id);
    setEditText(comment.commentText);
  }

  function saveEdit(commentId: string) {
    onEdit(commentId, editText);
    setEditingId(null);
    setEditText("");
  }

  return (
    <div className="assertion-comments">
      <ul className="assertion-comments-list">
        {comments.map((comment) => {
          const isOwn = comment.userId === currentUserId;
          const isDeleted = Boolean(comment.deletedAt);
          const isEditing = editingId === comment.id;

          return (
            <li
              key={comment.id}
              data-testid={`comment-${comment.id}`}
              data-reviewer={comment.isReviewer ? "true" : "false"}
              data-parent={comment.parentCommentId ?? undefined}
              className={
                comment.isReviewer
                  ? "assertion-comment assertion-comment--reviewer"
                  : "assertion-comment"
              }
              style={comment.parentCommentId ? { marginLeft: "1.5rem" } : undefined}
            >
              <div className="assertion-comment-meta">
                <span className="assertion-comment-author">{comment.authorName}</span>
                {comment.isReviewer && (
                  <span className="assertion-comment-badge">Reviewer</span>
                )}
              </div>

              {isDeleted ? (
                <p className="assertion-comment-text assertion-comment-text--deleted">
                  This comment was deleted.
                </p>
              ) : isEditing ? (
                <div className="assertion-comment-edit-form">
                  <label htmlFor={`edit-comment-${comment.id}`}>Edit comment</label>
                  <textarea
                    id={`edit-comment-${comment.id}`}
                    value={editText}
                    onChange={(event) => setEditText(event.target.value)}
                  />
                  <button type="button" onClick={() => saveEdit(comment.id)}>
                    Save
                  </button>
                  <button type="button" onClick={() => setEditingId(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <p className="assertion-comment-text">{comment.commentText}</p>
              )}

              {!isDeleted && isOwn && !isEditing && (
                <div className="assertion-comment-actions">
                  <button type="button" onClick={() => startEdit(comment)}>
                    Edit
                  </button>
                  <button type="button" onClick={() => onDelete(comment.id)}>
                    Delete
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <div className="assertion-comment-form">
        <label htmlFor="assertion-new-comment">Add a comment</label>
        <textarea
          id="assertion-new-comment"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="button" onClick={handlePost}>
          Post
        </button>
      </div>
    </div>
  );
}
