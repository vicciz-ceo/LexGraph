// UI3 — reviewer panel: accept/reject/dispute/request-revision (spec §10).
// Local types only for this component (sprint ruling R7 — no shared types
// module).

import { useState } from "react";

export interface AssertionReviewSummary {
  id: string;
  status: string;
  evidenceStatus: string;
  currentRevisionNumber?: number;
}

export interface AssertionReviewPanelProps {
  assertion: AssertionReviewSummary;
  onAccept: (payload?: { justification?: string }) => void;
  onReject: (payload?: { comment?: string }) => void;
  onDispute: (payload?: { comment?: string }) => void;
  onRequestRevision: (payload: { comment: string }) => void;
  /**
   * Revision-aware rating notice (spec §10): when the assertion currently
   * under review carries ratings that were recorded against a prior
   * revision, the reviewer must be told those ratings do not necessarily
   * reflect the current text.
   */
  hasRatingsOnPriorRevision?: boolean;
}

type PendingAction = "accept" | "requestRevision" | null;

export function AssertionReviewPanel({
  assertion,
  onAccept,
  onReject,
  onDispute,
  onRequestRevision,
  hasRatingsOnPriorRevision = false,
}: AssertionReviewPanelProps) {
  const [pending, setPending] = useState<PendingAction>(null);
  const [justification, setJustification] = useState("");
  const [comment, setComment] = useState("");

  const requiresJustification = assertion.evidenceStatus === "unsupported";

  function handleAcceptClick() {
    if (requiresJustification) {
      setPending("accept");
      return;
    }
    onAccept({});
  }

  function handleConfirmAccept() {
    onAccept({ justification });
    setPending(null);
    setJustification("");
  }

  function handleRequestRevisionClick() {
    setPending("requestRevision");
  }

  function handleConfirmRequestRevision() {
    if (!comment.trim()) return;
    onRequestRevision({ comment });
    setPending(null);
    setComment("");
  }

  function handleCancel() {
    setPending(null);
    setJustification("");
    setComment("");
  }

  return (
    <div className="assertion-review-panel">
      {hasRatingsOnPriorRevision && (
        <p className="assertion-review-revision-notice">
          Existing ratings were recorded against a prior revision of this assertion. The
          current revision has not yet been rated.
        </p>
      )}

      <div className="assertion-review-actions">
        <button type="button" onClick={handleAcceptClick}>
          Accept
        </button>
        <button type="button" onClick={() => onReject({})}>
          Reject
        </button>
        <button type="button" onClick={() => onDispute({})}>
          Dispute
        </button>
        <button type="button" onClick={handleRequestRevisionClick}>
          Request revision
        </button>
      </div>

      {pending === "accept" && (
        <div className="assertion-review-accept-form">
          <p className="assertion-review-accept-warning">
            This assertion is currently unsupported by documentary evidence. Record a
            justification to accept it anyway.
          </p>
          <label htmlFor="assertion-review-justification">
            Justification for accepting without supporting evidence
          </label>
          <textarea
            id="assertion-review-justification"
            value={justification}
            onChange={(event) => setJustification(event.target.value)}
          />
          <button type="button" onClick={handleConfirmAccept}>
            Confirm
          </button>
          <button type="button" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      )}

      {pending === "requestRevision" && (
        <div className="assertion-review-request-revision-form">
          <label htmlFor="assertion-review-revision-comment">
            Comment explaining the requested revision
          </label>
          <textarea
            id="assertion-review-revision-comment"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
          <button type="button" onClick={handleConfirmRequestRevision}>
            Confirm
          </button>
          <button type="button" onClick={handleCancel}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
