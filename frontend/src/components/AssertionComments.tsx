// Assertion discussion thread (spec §9), mounted on the assertion detail
// page (findings ui:15, pipeline:8). Comments are shown as threads: a reply
// sits under the comment it answers, and a removed comment that still has
// replies keeps its place as "[comment removed]". Comments by reviewers and
// admins carry a badge. Members who may comment (assertion:comment:
// contributor, reviewer, admin) can post, reply, and edit or delete their
// own comments; viewers only read.
//
// Every action is handed to the caller, which talks to the API. An action
// that fails keeps its form open, with the typed text and the reason shown
// inside it.

import { useId, useMemo, useState } from "react";
import type { ReactElement } from "react";

export interface AssertionCommentItem {
  id: string;
  userId: string;
  authorName: string;
  commentText: string;
  /** The author's exact text, used to prefill an edit (else commentText). */
  commentTextRaw?: string | null;
  isReviewer?: boolean;
  /** Badge text for a reviewer comment (default "Reviewer"). */
  reviewerLabel?: string;
  parentCommentId?: string | null;
  createdAt?: string;
  updatedAt?: string | null;
  deletedAt?: string | null;
}

export interface AssertionCommentsProps {
  comments: AssertionCommentItem[];
  currentUserId: string;
  /** Whether the viewer may post, reply, edit and delete (default true). */
  canComment?: boolean;
  onAdd: (commentText: string) => void | Promise<void>;
  onEdit: (commentId: string, commentText: string) => void | Promise<void>;
  onDelete: (commentId: string) => void | Promise<void>;
  /** Offer "Reply" on live comments when given. */
  onReply?: (parentCommentId: string, commentText: string) => void | Promise<void>;
  /** Formats `createdAt` for display; without it no time is shown. */
  formatTime?: (iso: string) => string;
}

type Mode = "edit" | "reply" | "delete";

interface PendingAction {
  mode: Mode;
  text: string;
  error: string | null;
  busy: boolean;
}

interface ThreadNode {
  comment: AssertionCommentItem;
  replies: ThreadNode[];
}

/** Nesting beyond this depth is shown without further indentation. */
const MAX_INDENT_DEPTH = 4;

function initialsOf(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("") || "?"
  );
}

/**
 * Group comments into threads. A reply is attached to a parent listed before
 * it (replies are always created after their parent), so a malformed parent
 * link can never form a cycle; anything else is shown as a top-level comment.
 */
function buildThreads(comments: AssertionCommentItem[]): ThreadNode[] {
  const nodes = comments.map((comment) => ({ comment, replies: [] as ThreadNode[] }));
  const position = new Map<string, number>();
  comments.forEach((comment, index) => {
    if (!position.has(comment.id)) position.set(comment.id, index);
  });
  const roots: ThreadNode[] = [];
  nodes.forEach((node, index) => {
    const parentId = node.comment.parentCommentId;
    const parentIndex = parentId != null ? position.get(parentId) : undefined;
    if (parentIndex !== undefined && parentIndex < index) nodes[parentIndex].replies.push(node);
    else roots.push(node);
  });
  return roots;
}

function wasEdited(comment: AssertionCommentItem): boolean {
  if (!comment.updatedAt || !comment.createdAt || comment.deletedAt) return false;
  const created = Date.parse(comment.createdAt);
  const updated = Date.parse(comment.updatedAt);
  return !Number.isNaN(created) && !Number.isNaN(updated) && updated > created;
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

const FAILURE: Record<Mode, string> = {
  edit: "The comment could not be updated.",
  reply: "The reply could not be posted.",
  delete: "The comment could not be deleted.",
};

export function AssertionComments({
  comments,
  currentUserId,
  canComment = true,
  onAdd,
  onEdit,
  onDelete,
  onReply,
  formatTime,
}: AssertionCommentsProps): ReactElement {
  const baseId = useId();
  const threads = useMemo(() => buildThreads(comments), [comments]);
  const [draft, setDraft] = useState("");
  const [posting, setPosting] = useState(false);
  const [postError, setPostError] = useState<string | null>(null);
  // One open action (edit, reply or delete confirmation) per comment.
  const [pending, setPending] = useState<Record<string, PendingAction>>({});

  const open = (commentId: string, mode: Mode, text = "") =>
    setPending((current) => ({ ...current, [commentId]: { mode, text, error: null, busy: false } }));

  const close = (commentId: string) =>
    setPending((current) => {
      const next = { ...current };
      delete next[commentId];
      return next;
    });

  const patch = (commentId: string, changes: Partial<PendingAction>) =>
    setPending((current) =>
      current[commentId] ? { ...current, [commentId]: { ...current[commentId], ...changes } } : current,
    );

  async function run(commentId: string, mode: Mode, action: () => void | Promise<void>) {
    patch(commentId, { busy: true, error: null });
    try {
      await action();
      close(commentId);
    } catch (error) {
      patch(commentId, { busy: false, error: messageOf(error, FAILURE[mode]) });
    }
  }

  async function handlePost() {
    const text = draft.trim();
    if (!text || posting) return;
    setPosting(true);
    setPostError(null);
    try {
      await onAdd(text);
      setDraft("");
    } catch (error) {
      // The server's reason (blank or markup-only text, a viewer role) is
      // shown next to the form; the draft is kept for correction.
      setPostError(messageOf(error, "Failed to post comment."));
    } finally {
      setPosting(false);
    }
  }

  function renderPending(comment: AssertionCommentItem, action: PendingAction): ReactElement {
    const fieldId = `${baseId}-${action.mode}-${comment.id}`;
    const error = action.error && (
      <p className="adp-comment-error" role="alert">
        {action.error}
      </p>
    );
    if (action.mode === "delete") {
      return (
        <div className="adp-comment-confirm">
          <span>Delete this comment?</span>
          <button
            type="button"
            className="btn btn--danger btn--sm"
            disabled={action.busy}
            onClick={() => void run(comment.id, "delete", () => onDelete(comment.id))}
          >
            Delete comment
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={action.busy}
            onClick={() => close(comment.id)}
          >
            Keep comment
          </button>
          {error}
        </div>
      );
    }
    const editing = action.mode === "edit";
    const original = (comment.commentTextRaw ?? comment.commentText).trim();
    const text = action.text.trim();
    const canSave = text !== "" && (!editing || text !== original);
    return (
      <div className={editing ? "adp-comment-edit assertion-comment-edit-form" : "adp-comment-reply"}>
        <label htmlFor={fieldId}>{editing ? "Edit comment" : `Reply to ${comment.authorName}`}</label>
        <textarea
          id={fieldId}
          className="textarea"
          value={action.text}
          onChange={(event) => patch(comment.id, { text: event.target.value })}
        />
        {error}
        <div className="adp-comment-form-actions">
          <button
            type="button"
            className="btn btn--primary btn--sm"
            disabled={action.busy || !canSave}
            onClick={() =>
              void run(comment.id, action.mode, () =>
                editing ? onEdit(comment.id, text) : onReply?.(comment.id, text),
              )
            }
          >
            {editing ? "Save comment" : "Post reply"}
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={action.busy}
            onClick={() => close(comment.id)}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  function renderNode(node: ThreadNode, depth: number): ReactElement {
    const { comment } = node;
    const isDeleted = Boolean(comment.deletedAt);
    const isOwn = comment.userId === currentUserId;
    const action = pending[comment.id];
    const showActions = canComment && !isDeleted && !action;
    const className = comment.isReviewer
      ? "adp-comment assertion-comment assertion-comment--reviewer"
      : "adp-comment assertion-comment";
    return (
      <li
        key={comment.id}
        data-testid={`comment-${comment.id}`}
        data-reviewer={comment.isReviewer ? "true" : "false"}
        data-parent={comment.parentCommentId ?? undefined}
        className={className}
      >
        <span className="avatar" aria-hidden="true">
          {initialsOf(comment.authorName)}
        </span>
        <div className="adp-comment-body">
          <div className="adp-comment-meta assertion-comment-meta">
            <span className="adp-comment-author assertion-comment-author">{comment.authorName}</span>
            {comment.isReviewer && (
              <span className="badge badge--neutral adp-comment-role assertion-comment-badge">
                {comment.reviewerLabel ?? "Reviewer"}
              </span>
            )}
            {comment.createdAt && formatTime && (
              <span className="muted">{formatTime(comment.createdAt)}</span>
            )}
            {wasEdited(comment) && <span className="muted adp-comment-edited">(edited)</span>}
          </div>
          {isDeleted ? (
            <p className="muted adp-comment-removed">[comment removed]</p>
          ) : action?.mode === "edit" ? null : (
            <p className="adp-comment-text assertion-comment-text">{comment.commentText}</p>
          )}
          {showActions && (
            <div className="adp-comment-actions assertion-comment-actions">
              {onReply && (
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => open(comment.id, "reply")}>
                  Reply
                </button>
              )}
              {isOwn && (
                <>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => open(comment.id, "edit", comment.commentTextRaw ?? comment.commentText)}
                  >
                    Edit
                  </button>
                  <button type="button" className="btn btn--ghost btn--sm" onClick={() => open(comment.id, "delete")}>
                    Delete
                  </button>
                </>
              )}
            </div>
          )}
          {action && !isDeleted && renderPending(comment, action)}
          {node.replies.length > 0 && (
            <ul
              className={
                depth + 1 >= MAX_INDENT_DEPTH
                  ? "adp-comment-list adp-comment-replies adp-comment-replies--flat"
                  : "adp-comment-list adp-comment-replies"
              }
              aria-label={`Replies to ${comment.authorName}`}
            >
              {node.replies.map((reply) => renderNode(reply, depth + 1))}
            </ul>
          )}
        </div>
      </li>
    );
  }

  return (
    <div className="assertion-comments">
      {threads.length === 0 ? (
        <p className="muted">
          {canComment
            ? "No comments yet. Start the discussion on this assertion."
            : "No comments yet."}
        </p>
      ) : (
        <ul className="adp-comment-list assertion-comments-list">
          {threads.map((node) => renderNode(node, 0))}
        </ul>
      )}
      {canComment && (
        <div className="field adp-comment-form assertion-comment-form">
          <label htmlFor={`${baseId}-new`}>Add a comment</label>
          <textarea
            id={`${baseId}-new`}
            className="textarea"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          {postError && (
            <p className="adp-comment-error" role="alert">
              {postError}
            </p>
          )}
          <button
            type="button"
            className="btn btn--primary btn--sm adp-comment-submit"
            onClick={() => void handlePost()}
            disabled={posting || draft.trim() === ""}
          >
            Post comment
          </button>
        </div>
      )}
    </div>
  );
}
