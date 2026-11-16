// Revision history and comparison entry point (spec §3: "The interface must
// show a complete revision history"; "The user must be able to compare
// revisions"). Mounted as the assertion detail page's Activity timeline
// (findings ui:15, pipeline:8). Every revision's authored text stays
// visible; with two or more revisions, any two can be selected and
// compared.

import { useState } from "react";
import type { ReactNode } from "react";

export interface AssertionRevisionSummary {
  revisionNumber: number;
  proposition: string;
  // Track A, item A7 (issue #2 / gate G1): the raw, byte-exact authored
  // proposition for this revision. Optional so existing callers that
  // haven't wired it through yet keep working -- falls back to the
  // (possibly lossy, sanitized) `proposition` field when absent.
  propositionRaw?: string;
  editedBy: string;
  /** Display text for when the revision was recorded. */
  createdAt?: string;
  revisionReason?: string | null;
}

export interface AssertionRevisionHistoryProps {
  /** In display order (the detail page lists the newest first). */
  revisions: AssertionRevisionSummary[];
  onCompare: (leftRevisionNumber: number, rightRevisionNumber: number) => void;
  currentRevisionNumber?: number | null;
  /** Extra content under a revision, e.g. its ratings. */
  renderFooter?: (revisionNumber: number) => ReactNode;
}

function selectionHint(count: number): string {
  if (count === 0) return "Select two revisions to compare them field by field.";
  if (count === 1) return "Select one more revision to compare.";
  return "Two revisions selected.";
}

export function AssertionRevisionHistory({
  revisions,
  onCompare,
  currentRevisionNumber = null,
  renderFooter,
}: AssertionRevisionHistoryProps) {
  const [selected, setSelected] = useState<number[]>([]);
  const comparable = revisions.length >= 2;

  function toggleSelect(revisionNumber: number, checked: boolean) {
    setSelected((previous) => {
      if (checked) {
        return [...previous.filter((n) => n !== revisionNumber), revisionNumber].slice(-2);
      }
      return previous.filter((n) => n !== revisionNumber);
    });
  }

  function handleCompareClick() {
    if (selected.length !== 2) return;
    const [a, b] = [...selected].sort((x, y) => x - y);
    onCompare(a, b);
  }

  return (
    <div className="assertion-revision-history">
      <ol className="adp-timeline assertion-revision-list">
        {revisions.map((revision) => (
          <li key={revision.revisionNumber} className="adp-timeline-item assertion-revision-item">
            <div className="adp-timeline-title">
              {comparable && (
                <input
                  type="checkbox"
                  className="adp-compare-select"
                  aria-label={`Select revision ${revision.revisionNumber} for comparison`}
                  checked={selected.includes(revision.revisionNumber)}
                  onChange={(event) => toggleSelect(revision.revisionNumber, event.target.checked)}
                />
              )}
              <span>Revision {revision.revisionNumber}</span>
              {revision.revisionNumber === currentRevisionNumber && (
                <span className="chip chip--tag">current</span>
              )}
            </div>
            <div className="muted adp-timeline-meta assertion-revision-author">
              {revision.editedBy}
              {revision.createdAt ? ` · ${revision.createdAt}` : ""}
            </div>
            <p className="adp-timeline-text assertion-revision-proposition">
              {revision.propositionRaw ?? revision.proposition}
            </p>
            {revision.revisionReason && (
              <p className="adp-timeline-reason assertion-revision-reason">{revision.revisionReason}</p>
            )}
            {renderFooter?.(revision.revisionNumber)}
          </li>
        ))}
      </ol>
      {comparable && (
        <div className="adp-compare-controls">
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={handleCompareClick}
            disabled={selected.length !== 2}
          >
            Compare selected revisions
          </button>
          <span className="field__hint">{selectionHint(selected.length)}</span>
        </div>
      )}
    </div>
  );
}
