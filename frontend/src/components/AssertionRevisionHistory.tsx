// UI3 — revision history + comparison entry point (spec §3).
// Local types only for this component (sprint ruling R7 — no shared types module).

import { useState } from "react";

export interface AssertionRevisionSummary {
  revisionNumber: number;
  proposition: string;
  editedBy: string;
  createdAt?: string;
  revisionReason?: string | null;
}

export interface AssertionRevisionHistoryProps {
  revisions: AssertionRevisionSummary[];
  onCompare: (leftRevisionNumber: number, rightRevisionNumber: number) => void;
}

export function AssertionRevisionHistory({ revisions, onCompare }: AssertionRevisionHistoryProps) {
  const [selected, setSelected] = useState<number[]>([]);

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
      <ul className="assertion-revision-list">
        {revisions.map((revision) => (
          <li key={revision.revisionNumber} className="assertion-revision-item">
            <label className="assertion-revision-select">
              <input
                type="checkbox"
                aria-label={`Select revision ${revision.revisionNumber} for comparison`}
                checked={selected.includes(revision.revisionNumber)}
                onChange={(event) => toggleSelect(revision.revisionNumber, event.target.checked)}
              />
            </label>
            <h4>Revision {revision.revisionNumber}</h4>
            <p className="assertion-revision-author">{revision.editedBy}</p>
            {revision.createdAt && (
              <p className="assertion-revision-date">{revision.createdAt}</p>
            )}
            <p className="assertion-revision-proposition">{revision.proposition}</p>
            {revision.revisionReason && (
              <p className="assertion-revision-reason">{revision.revisionReason}</p>
            )}
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={handleCompareClick}
        disabled={selected.length !== 2}
      >
        Compare
      </button>
    </div>
  );
}
