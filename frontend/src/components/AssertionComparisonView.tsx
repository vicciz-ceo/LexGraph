// UI3 — side-by-side revision comparison (spec §3: "The user must be able
// to compare revisions"). Local types only for this component (sprint
// ruling R7 — no shared types module).

export interface AssertionComparisonRevision {
  revisionNumber: number;
  proposition: string;
  editedBy: string;
}

export interface AssertionComparisonRatingSummary {
  count: number;
  average: number | null;
  median: number | null;
  distribution: Record<string, number>;
}

export interface AssertionComparisonViewProps {
  left: AssertionComparisonRevision;
  right: AssertionComparisonRevision;
  leftRatingSummary?: AssertionComparisonRatingSummary;
  rightRatingSummary?: AssertionComparisonRatingSummary;
}

function RevisionColumn({
  revision,
  ratingSummary,
}: {
  revision: AssertionComparisonRevision;
  ratingSummary?: AssertionComparisonRatingSummary;
}) {
  return (
    <div className="assertion-comparison-column">
      <h3>Revision {revision.revisionNumber}</h3>
      <p className="assertion-comparison-author">{revision.editedBy}</p>
      <p className="assertion-comparison-proposition">{revision.proposition}</p>
      {ratingSummary &&
        (ratingSummary.count > 0 ? (
          <p className="assertion-comparison-ratings">
            {ratingSummary.average !== null ? ratingSummary.average.toFixed(1) : "—"} average
            from {ratingSummary.count} ratings for this revision.
          </p>
        ) : (
          <p className="assertion-comparison-ratings">
            This revision has not yet been rated.
          </p>
        ))}
    </div>
  );
}

export function AssertionComparisonView({
  left,
  right,
  leftRatingSummary,
  rightRatingSummary,
}: AssertionComparisonViewProps) {
  return (
    <div className="assertion-comparison-view">
      <RevisionColumn revision={left} ratingSummary={leftRatingSummary} />
      <RevisionColumn revision={right} ratingSummary={rightRatingSummary} />
    </div>
  );
}
