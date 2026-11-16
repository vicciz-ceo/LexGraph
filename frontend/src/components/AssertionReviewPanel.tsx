// UI3 — reviewer panel: accept/reject/dispute/request-revision (spec §10).
// Local types only for this component (sprint ruling R7 — no shared types
// module).
//
// The panel offers only decisions the API records (spec addendum "Review
// decision rules (2026-11-16)"): none on a draft, withdrawn or superseded
// assertion, never the one that would repeat the current status, one at a
// time, and an acceptance without supporting evidence only with a written
// justification. When an acceptance turns out to need one (the evidence was
// removed after the page loaded), the page says so and the panel asks for it.

import "../styles/components/assertion-review-panel.css";

import { useId, useRef, useState } from "react";

import {
  DECIDABLE_STATUSES,
  canDecide,
  reviewTextProblem,
  reviewTextTooLongMessage,
} from "../constants/review";

export interface AssertionReviewSummary {
  id: string;
  status: string;
  evidenceStatus: string;
  currentRevisionNumber?: number;
}

/**
 * How a decision ended. `false` means it was not recorded (the caller reports
 * why); the panel then keeps the form and the text typed in it for another
 * try. "needs-justification" means an acceptance sent without a justification
 * was not recorded because the assertion has no supporting evidence after all
 * (it was removed after the page loaded it, review fe-review-detail:2); the
 * panel then opens the justification form. Anything else means it was recorded.
 */
export type ReviewDecisionOutcome = void | boolean | "needs-justification";

/**
 * What a decision handler returns: an outcome, or a promise of one that
 * settles once the decision has been sent. While the promise is pending the
 * panel's actions are disabled, so a decision is sent once; a page keeps them
 * disabled (`busy`) until it shows the decision's result.
 */
export type ReviewDecisionResult = ReviewDecisionOutcome | Promise<ReviewDecisionOutcome>;

export interface AssertionReviewPanelProps {
  assertion: AssertionReviewSummary;
  onAccept: (payload?: { justification?: string }) => ReviewDecisionResult;
  onReject: (payload?: { comment?: string }) => ReviewDecisionResult;
  onDispute: (payload?: { comment?: string }) => ReviewDecisionResult;
  onRequestRevision: (payload: { comment: string }) => ReviewDecisionResult;
  /**
   * Revision-aware rating notice (spec §10): when the assertion currently
   * under review carries ratings that were recorded against a prior
   * revision, the reviewer must be told those ratings do not necessarily
   * reflect the current text.
   */
  hasRatingsOnPriorRevision?: boolean;
  /**
   * True while the parent is recording a decision, and until it shows the
   * record re-read after one: every action is disabled.
   */
  busy?: boolean;
}

type PendingAction = "accept" | "requestRevision" | null;

const NO_DECISION_NOTES: Record<string, string> = {
  draft: "No review decision can be recorded on a draft. It must be submitted for review first.",
  withdrawn: "No review decision can be recorded: the author withdrew this assertion.",
  superseded:
    "No review decision can be recorded: this assertion has been superseded by another one.",
};

function noDecisionNote(status: string): string {
  return (
    NO_DECISION_NOTES[status] ??
    `No review decision can be recorded while this assertion is ${status.replace(/_/g, " ")}.`
  );
}

function isPromiseLike(value: unknown): value is PromiseLike<ReviewDecisionOutcome> {
  return typeof (value as PromiseLike<unknown> | null | undefined)?.then === "function";
}

export function AssertionReviewPanel({
  assertion,
  onAccept,
  onReject,
  onDispute,
  onRequestRevision,
  hasRatingsOnPriorRevision = false,
  busy = false,
}: AssertionReviewPanelProps) {
  const [pending, setPending] = useState<PendingAction>(null);
  const [justification, setJustification] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // Set synchronously when a decision is sent, so a second activation that
  // lands before React re-renders the disabled buttons is still ignored.
  const inFlight = useRef(false);
  // Unique per panel: the Review Queue renders one panel per card.
  const idBase = `assertion-review${useId()}`;

  const status = assertion.status;
  const requiresJustification = assertion.evidenceStatus === "unsupported";
  const disabled = busy || submitting;
  const justificationProblem = reviewTextProblem(justification);
  const commentProblem = reviewTextProblem(comment);

  function closeForm() {
    setPending(null);
    setJustification("");
    setComment("");
  }

  function decide(run: () => ReviewDecisionResult, onRecorded?: () => void) {
    if (busy || inFlight.current) return;
    inFlight.current = true;
    setSubmitting(true);
    const finish = (outcome: ReviewDecisionOutcome) => {
      inFlight.current = false;
      setSubmitting(false);
      if (outcome === "needs-justification") {
        setPending("accept");
      } else if (outcome !== false) {
        onRecorded?.();
      }
    };
    let outcome: ReviewDecisionResult;
    try {
      outcome = run();
    } catch (error) {
      finish(false);
      throw error;
    }
    if (isPromiseLike(outcome)) {
      outcome.then(finish, () => finish(false));
    } else {
      finish(outcome);
    }
  }

  function handleAcceptClick() {
    if (requiresJustification) {
      setPending("accept");
      return;
    }
    decide(() => onAccept({}));
  }

  function handleConfirmAccept() {
    if (justificationProblem !== null) return;
    const text = justification.trim();
    decide(() => onAccept({ justification: text }), closeForm);
  }

  function handleConfirmRequestRevision() {
    if (commentProblem !== null) return;
    const text = comment.trim();
    decide(() => onRequestRevision({ comment: text }), closeForm);
  }

  if (!DECIDABLE_STATUSES.includes(status)) {
    return (
      <div className="assertion-review-panel">
        <p className="assertion-review-unavailable">{noDecisionNote(status)}</p>
      </div>
    );
  }

  const canAccept = canDecide(status, "accepted");
  const canRequestRevision = canDecide(status, "revision_requested");
  const justificationId = `${idBase}justification`;
  const commentId = `${idBase}revision-comment`;

  return (
    <div className="assertion-review-panel">
      {hasRatingsOnPriorRevision && (
        <p className="assertion-review-revision-notice">
          Existing ratings were recorded against a prior revision of this assertion. The
          current revision has not yet been rated.
        </p>
      )}

      <div className="assertion-review-actions" role="group" aria-label="Review decision">
        {canAccept && (
          <button
            type="button"
            className="assertion-review-action assertion-review-action--accept"
            disabled={disabled}
            onClick={handleAcceptClick}
          >
            Accept
          </button>
        )}
        {canDecide(status, "rejected") && (
          <button
            type="button"
            className="assertion-review-action assertion-review-action--reject"
            disabled={disabled}
            onClick={() => decide(() => onReject({}))}
          >
            Reject
          </button>
        )}
        {canDecide(status, "disputed") && (
          <button
            type="button"
            className="assertion-review-action assertion-review-action--dispute"
            disabled={disabled}
            onClick={() => decide(() => onDispute({}))}
          >
            Dispute
          </button>
        )}
        {canRequestRevision && (
          <button
            type="button"
            className="assertion-review-action assertion-review-action--request-revision"
            disabled={disabled}
            onClick={() => setPending("requestRevision")}
          >
            Request revision
          </button>
        )}
      </div>

      {pending === "accept" && canAccept && (
        <div className="assertion-review-accept-form">
          <p className="assertion-review-accept-warning" id={`${justificationId}-hint`}>
            This assertion is currently unsupported by documentary evidence. Record a
            justification to accept it anyway. It is required and is kept in the
            assertion&apos;s history.
          </p>
          <label htmlFor={justificationId}>
            Justification for accepting without supporting evidence
          </label>
          <textarea
            id={justificationId}
            aria-describedby={`${justificationId}-hint`}
            value={justification}
            onChange={(event) => setJustification(event.target.value)}
          />
          {justificationProblem === "too_long" && (
            <p className="assertion-review-error" role="alert">
              {reviewTextTooLongMessage(justification)}
            </p>
          )}
          <button
            type="button"
            disabled={disabled || justificationProblem !== null}
            onClick={handleConfirmAccept}
          >
            Confirm
          </button>
          <button type="button" disabled={disabled} onClick={closeForm}>
            Cancel
          </button>
        </div>
      )}

      {pending === "requestRevision" && canRequestRevision && (
        <div className="assertion-review-request-revision-form">
          <label htmlFor={commentId}>Comment explaining the requested revision</label>
          <textarea
            id={commentId}
            aria-describedby={`${commentId}-hint`}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
          <p className="assertion-review-hint" id={`${commentId}-hint`}>
            Required. The comment is added to the assertion&apos;s discussion for its author.
          </p>
          {commentProblem === "too_long" && (
            <p className="assertion-review-error" role="alert">
              {reviewTextTooLongMessage(comment)}
            </p>
          )}
          <button
            type="button"
            disabled={disabled || commentProblem !== null}
            onClick={handleConfirmRequestRevision}
          >
            Confirm
          </button>
          <button type="button" disabled={disabled} onClick={closeForm}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
