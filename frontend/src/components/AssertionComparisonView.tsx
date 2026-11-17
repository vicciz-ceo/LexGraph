// Side-by-side revision comparison (spec §3: "The user must be able to
// compare revisions"), mounted under the assertion detail page's Activity
// timeline (findings ui:15, pipeline:8). One row per field, the authored
// text first; rows whose value differs between the two revisions are marked
// "Changed", so a revision that changed only, say, the jurisdiction does not
// look identical. Ratings stay with the revision they were given on.

export interface AssertionComparisonField {
  key: string;
  label: string;
  /** Display text. */
  value: string;
  /** What is compared, when the display text can hide a difference (two
   * unnamed entities, two instants on the same day). Defaults to `value`. */
  identity?: string;
}

export interface AssertionComparisonRevision {
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
  /** Further fields compared row by row, matched by `key`. */
  fields?: AssertionComparisonField[];
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
  /** `null`: the summary could not be loaded; omitted: not shown. */
  leftRatingSummary?: AssertionComparisonRatingSummary | null;
  rightRatingSummary?: AssertionComparisonRatingSummary | null;
}

interface ComparedRow {
  key: string;
  label: string;
  left: string;
  right: string;
  changed: boolean;
  block?: boolean;
}

function ratingText(summary: AssertionComparisonRatingSummary | null | undefined): string {
  if (summary === undefined) return "—";
  if (summary === null) return "Ratings could not be loaded.";
  if (summary.count === 0) return "This revision has not yet been rated.";
  const average = summary.average !== null ? summary.average.toFixed(1) : "—";
  return `${average} average from ${summary.count} ${
    summary.count === 1 ? "rating" : "ratings"
  } for this revision.`;
}

function comparedRows(left: AssertionComparisonRevision, right: AssertionComparisonRevision): ComparedRow[] {
  const leftText = left.propositionRaw ?? left.proposition;
  const rightText = right.propositionRaw ?? right.proposition;
  const rows: ComparedRow[] = [
    {
      key: "proposition",
      label: "Proposition",
      left: leftText,
      right: rightText,
      changed: leftText !== rightText,
      block: true,
    },
  ];
  const leftFields = new Map((left.fields ?? []).map((field) => [field.key, field]));
  const rightFields = new Map((right.fields ?? []).map((field) => [field.key, field]));
  const keys = [...leftFields.keys(), ...[...rightFields.keys()].filter((key) => !leftFields.has(key))];
  for (const key of keys) {
    const l = leftFields.get(key);
    const r = rightFields.get(key);
    rows.push({
      key,
      label: (l ?? r)?.label ?? key,
      left: l?.value ?? "—",
      right: r?.value ?? "—",
      changed: (l?.identity ?? l?.value) !== (r?.identity ?? r?.value),
    });
  }
  return rows;
}

export function AssertionComparisonView({
  left,
  right,
  leftRatingSummary,
  rightRatingSummary,
}: AssertionComparisonViewProps) {
  const rows = comparedRows(left, right);
  const changed = rows.filter((row) => row.changed);
  const showReasons = Boolean(left.revisionReason || right.revisionReason);
  const showRatings = leftRatingSummary !== undefined || rightRatingSummary !== undefined;
  return (
    <section className="assertion-comparison-view adp-compare" aria-label="Revision comparison">
      <p className="adp-compare-summary">
        {changed.length === 0
          ? "No differences: the two revisions have the same text and fields."
          : `Changed: ${changed.map((row) => row.label.toLowerCase()).join(", ")}.`}
      </p>
      <div className="adp-compare-scroll">
        <table className="adp-compare-table">
          <thead>
            <tr>
              <th scope="col">
                <span className="adp-sr-only">Field</span>
              </th>
              <th scope="col" className="assertion-comparison-column">
                Revision {left.revisionNumber}
              </th>
              <th scope="col" className="assertion-comparison-column">
                Revision {right.revisionNumber}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Edited by</th>
              {[left, right].map((revision) => (
                <td key={revision.revisionNumber} className="assertion-comparison-author">
                  <span className="adp-compare-editor">{revision.editedBy}</span>
                  {revision.createdAt && <span className="muted adp-compare-date">{revision.createdAt}</span>}
                </td>
              ))}
            </tr>
            {rows.map((row) => (
              <tr key={row.key} className={row.changed ? "adp-compare-row adp-compare-row--changed" : "adp-compare-row"}>
                <th scope="row">
                  {row.label}
                  {row.changed && <span className="badge badge--proposed adp-compare-changed">Changed</span>}
                </th>
                <td>
                  {row.block ? <p className="assertion-comparison-proposition">{row.left}</p> : row.left}
                </td>
                <td>
                  {row.block ? <p className="assertion-comparison-proposition">{row.right}</p> : row.right}
                </td>
              </tr>
            ))}
            {showReasons && (
              <tr>
                <th scope="row">Reason for revision</th>
                <td>{left.revisionReason || "—"}</td>
                <td>{right.revisionReason || "—"}</td>
              </tr>
            )}
            {showRatings && (
              <tr>
                <th scope="row">Team ratings</th>
                <td className="assertion-comparison-ratings">{ratingText(leftRatingSummary)}</td>
                <td className="assertion-comparison-ratings">{ratingText(rightRatingSummary)}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
